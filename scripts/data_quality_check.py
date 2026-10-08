"""
data_quality_check.py

Checks the five raw CSV files in data/raw/ for data quality problems and
writes a report. The data itself is never modified.

Run from the project root:

    python scripts/data_quality_check.py

Output:
    - A summary and list of flagged issues printed to the console
    - The full report (every check, passed or flagged) saved to
      documentation/data_quality_report.csv

Severity levels:
    Critical  Breaks joins or totals (missing/duplicate keys, broken links).
    High      Wrong values that would distort metrics.
    Medium    Suspicious values or rule breaks that need a human to review.
    Low       Informational; often legitimate but worth knowing about.
"""

from pathlib import Path

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "data" / "raw"
REPORT_PATH = PROJECT_DIR / "documentation" / "data_quality_report.csv"

# ---------------------------------------------------------------------------
# Expected structure of the data (the "rules" we check against)
# ---------------------------------------------------------------------------

EXPECTED_COLUMNS = {
    "products": ["product_id", "product_name", "category", "unit_cost", "selling_price"],
    "stores": ["store_id", "store_name", "city", "region"],
    "suppliers": ["supplier_id", "supplier_name", "product_id", "lead_time_days", "on_time_delivery_rate"],
    "sales": ["order_id", "order_date", "product_id", "store_id", "quantity", "revenue"],
    "inventory": ["product_id", "store_id", "current_stock", "inventory_age_days"],
}

PRIMARY_KEYS = {
    "products": ["product_id"],
    "stores": ["store_id"],
    "suppliers": ["supplier_id", "product_id"],
    "sales": ["order_id"],
    "inventory": ["product_id", "store_id"],
}

# (child table, child column, parent table, parent column)
FOREIGN_KEYS = [
    ("sales", "product_id", "products", "product_id"),
    ("sales", "store_id", "stores", "store_id"),
    ("inventory", "product_id", "products", "product_id"),
    ("inventory", "store_id", "stores", "store_id"),
    ("suppliers", "product_id", "products", "product_id"),
]

# (table, column, minimum allowed, maximum allowed, must be whole number, severity)
NUMERIC_RULES = [
    ("products", "unit_cost", 0.01, None, False, "High"),
    ("products", "selling_price", 0.01, None, False, "High"),
    ("suppliers", "lead_time_days", 1, None, True, "High"),
    ("suppliers", "on_time_delivery_rate", 0, 1, False, "High"),
    ("sales", "quantity", 1, None, True, "Critical"),
    ("sales", "revenue", 0.01, None, False, "Critical"),
    ("inventory", "current_stock", 0, None, True, "High"),
    ("inventory", "inventory_age_days", 0, None, True, "Medium"),
]

DATE_COLUMNS = [("sales", "order_date")]
DATE_FORMAT = "%Y-%m-%d"
EXPECTED_PERIOD = ("2025-01-01", "2025-12-31")

EXPECTED_VALUES = {
    ("products", "category"): {
        "Electronics", "Home & Kitchen", "Apparel", "Grocery",
        "Beauty & Personal Care", "Sports & Fitness", "Toys & Games", "Stationery",
    },
    ("stores", "region"): {"North", "South", "East", "West", "Central"},
}

ID_PATTERNS = {
    ("products", "product_id"): r"P\d{4}",
    ("stores", "store_id"): r"S\d{3}",
    ("suppliers", "supplier_id"): r"SUP\d{3}",
    ("sales", "order_id"): r"ORD\d{6}",
}

SEVERITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}

# ---------------------------------------------------------------------------
# Report helper
# ---------------------------------------------------------------------------

results = []


def record(dataset, column, check, issue, severity, mask, values=None):
    """
    Add one check result to the report.

    mask:   True/False per row, True = row has the problem.
    values: optional Series used to show up to 3 example bad values.
    """
    affected = int(mask.sum())
    examples = ""
    if affected and values is not None:
        examples = ", ".join(map(str, values[mask].dropna().unique()[:3]))

    results.append({
        "dataset": dataset,
        "column": column,
        "check": check,
        "issue": issue,
        "affected_rows": affected,
        "severity": severity,
        "status": "FLAG" if affected else "PASS",
        "examples": examples,
    })


def to_number(series):
    """Convert text to numbers; anything that isn't a number becomes NaN."""
    return pd.to_numeric(series.str.strip(), errors="coerce")


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def load_tables():
    """Read every column as text so nothing gets silently converted."""
    tables = {}
    for name in EXPECTED_COLUMNS:
        path = RAW_DIR / f"{name}.csv"
        if not path.exists():
            raise FileNotFoundError(f"{path} not found. Run scripts/generate_data.py first.")
        tables[name] = pd.read_csv(path, dtype=str)
    return tables


def check_columns(tables):
    """Every expected column must be present. Returns False if any are missing."""
    all_present = True
    for name, expected in EXPECTED_COLUMNS.items():
        for col in expected:
            missing = col not in tables[name].columns
            all_present &= not missing
            record(name, col, "Column exists", "Expected column is missing from the file",
                   "Critical", pd.Series([missing]))
    return all_present


def check_missing_values(tables):
    key_columns = {(t, c) for t, cols in PRIMARY_KEYS.items() for c in cols}
    key_columns |= {(child, col) for child, col, _, _ in FOREIGN_KEYS}

    for name, df in tables.items():
        for col in df.columns:
            missing = df[col].isna() | (df[col].str.strip() == "")
            severity = "Critical" if (name, col) in key_columns else "High"
            record(name, col, "Missing values", "Value is blank or null", severity, missing)


def check_extra_spaces(tables):
    numeric_or_date = {(t, c) for t, c, *_ in NUMERIC_RULES} | set(DATE_COLUMNS)

    for name, df in tables.items():
        for col in df.columns:
            if (name, col) in numeric_or_date:
                continue
            s = df[col]
            has_spaces = s.notna() & (s != s.str.strip())
            record(name, col, "Extra spaces", "Text has leading or trailing spaces",
                   "Medium", has_spaces, s)


def check_primary_keys(tables):
    for name, keys in PRIMARY_KEYS.items():
        df = tables[name]
        duplicated = df.duplicated(subset=keys, keep=False)
        label = " + ".join(keys)
        record(name, label, "Duplicate primary key",
               f"Same {label} appears on more than one row", "Critical",
               duplicated, df[keys].astype(str).agg(" | ".join, axis=1))


def check_id_formats(tables):
    for (name, col), pattern in ID_PATTERNS.items():
        s = tables[name][col]
        bad = s.notna() & ~s.str.fullmatch(pattern, na=False)
        record(name, col, "ID format", f"ID does not match expected pattern {pattern}",
               "Medium", bad, s)


def check_numeric_columns(tables):
    for name, col, minimum, maximum, whole_number, severity in NUMERIC_RULES:
        raw = tables[name][col]
        values = to_number(raw)

        not_numeric = raw.notna() & values.isna()
        record(name, col, "Invalid number", "Value is not a number", "High", not_numeric, raw)

        too_low = values < minimum
        issue = "Negative value" if minimum == 0 else "Zero or negative value"
        record(name, col, "Out of range", issue, severity, too_low, raw)

        if maximum is not None:
            too_high = values > maximum
            record(name, col, "Out of range", f"Value above maximum of {maximum}",
                   severity, too_high, raw)

        if whole_number:
            not_whole = values.notna() & (values % 1 != 0)
            record(name, col, "Not a whole number", "Value should be a whole number",
                   severity, not_whole, raw)


def check_dates(tables):
    start, end = (pd.Timestamp(d) for d in EXPECTED_PERIOD)
    today = pd.Timestamp.today().normalize()

    for name, col in DATE_COLUMNS:
        raw = tables[name][col]
        dates = pd.to_datetime(raw.str.strip(), format=DATE_FORMAT, errors="coerce")

        invalid = raw.notna() & dates.isna()
        record(name, col, "Invalid date", "Not a real date in YYYY-MM-DD format",
               "High", invalid, raw)

        future = dates > today
        record(name, col, "Future date", "Date is after today", "High", future, raw)

        outside = dates.notna() & ~dates.between(start, end)
        record(name, col, "Date outside period",
               f"Date is outside {EXPECTED_PERIOD[0]} to {EXPECTED_PERIOD[1]}",
               "Medium", outside, raw)


def check_categories(tables):
    for (name, col), allowed in EXPECTED_VALUES.items():
        s = tables[name][col]
        unexpected = s.notna() & ~s.isin(allowed)
        record(name, col, "Unexpected category",
               f"Value is not one of the {len(allowed)} expected values", "Medium",
               unexpected, s)


def check_foreign_keys(tables):
    for child, col, parent, parent_col in FOREIGN_KEYS:
        s = tables[child][col]
        orphan = s.notna() & ~s.isin(tables[parent][parent_col])
        record(child, col, "Broken foreign key",
               f"{col} does not exist in {parent}.csv", "Critical", orphan, s)


def check_relationships(tables):
    products = tables["products"]
    sales = tables["sales"]
    inventory = tables["inventory"]
    suppliers = tables["suppliers"]

    sale_pairs = pd.MultiIndex.from_frame(sales[["product_id", "store_id"]])
    stock_pairs = pd.MultiIndex.from_frame(inventory[["product_id", "store_id"]])
    not_stocked = pd.Series(~sale_pairs.isin(stock_pairs), index=sales.index)
    record("sales", "product_id + store_id", "Sale without inventory record",
           "Product was sold at a store that has no inventory row for it", "Medium",
           not_stocked, sales["product_id"] + " @ " + sales["store_id"])

    no_supplier = ~products["product_id"].isin(suppliers["product_id"])
    record("products", "product_id", "Product without supplier",
           "Product has no supplier in suppliers.csv", "Medium",
           no_supplier, products["product_id"])

    no_sales = ~products["product_id"].isin(sales["product_id"])
    record("products", "product_id", "Product without sales",
           "Product has no sales in sales.csv (possible dead stock)", "Low",
           no_sales, products["product_id"])

    names_per_id = suppliers.groupby("supplier_id")["supplier_name"].transform("nunique")
    record("suppliers", "supplier_name", "Inconsistent supplier name",
           "Same supplier_id has different supplier_name values", "Medium",
           names_per_id > 1, suppliers["supplier_id"])


def check_business_rules(tables):
    products = tables["products"]
    cost = to_number(products["unit_cost"])
    price = to_number(products["selling_price"])
    record("products", "selling_price", "Price below cost",
           "Selling price is lower than unit cost", "Medium",
           price < cost, products["product_id"])

    sales = tables["sales"]
    list_price = sales["product_id"].map(dict(zip(products["product_id"], price)))
    max_revenue = to_number(sales["quantity"]) * list_price
    too_much = to_number(sales["revenue"]) > max_revenue + 0.01
    record("sales", "revenue", "Revenue above list price",
           "Revenue is higher than quantity x selling_price", "Medium",
           too_much, sales["order_id"])


def check_duplicate_sales(tables):
    sales = tables["sales"]

    exact = sales.duplicated(keep=False)
    record("sales", "(all columns)", "Exact duplicate row",
           "Entire row appears more than once", "High", exact, sales["order_id"])

    detail_cols = ["order_date", "product_id", "store_id", "quantity", "revenue"]
    possible = sales.duplicated(subset=detail_cols, keep=False)
    record("sales", "(order details)", "Possible duplicate sale",
           "Same date/product/store/quantity/revenue as another order "
           "(may be a genuine repeat purchase)", "Low", possible, sales["order_id"])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_report():
    report = pd.DataFrame(results)
    report["_flag_first"] = report["status"].ne("FLAG")
    report["_severity"] = report["severity"].map(SEVERITY_ORDER)
    report = report.sort_values(["_flag_first", "_severity", "dataset", "column"])
    return report.drop(columns=["_flag_first", "_severity"]).reset_index(drop=True)


def print_report(report, tables):
    print("=" * 80)
    print("DATA QUALITY REPORT - Urban Retail Co. raw data")
    print("=" * 80)
    for name, df in tables.items():
        print(f"  {name + '.csv':<16} {len(df):>7,} rows")

    flagged = report[report["status"] == "FLAG"]
    print(f"\nChecks run: {len(report)}   Passed: {len(report) - len(flagged)}   Flagged: {len(flagged)}")

    if flagged.empty:
        print("\nNo issues found.")
    else:
        print("\nFlagged issues by severity:")
        for severity, count in flagged["severity"].value_counts().reindex(SEVERITY_ORDER).dropna().items():
            print(f"  {severity:<9} {int(count)}")

        print("\nFLAGGED ISSUES")
        columns = ["dataset", "column", "issue", "affected_rows", "severity", "examples"]
        with pd.option_context("display.width", 200, "display.max_colwidth", 60):
            print(flagged[columns].to_string(index=False))

    print(f"\nFull report saved to: {REPORT_PATH}")


def main():
    tables = load_tables()

    if check_columns(tables):
        check_missing_values(tables)
        check_extra_spaces(tables)
        check_primary_keys(tables)
        check_id_formats(tables)
        check_numeric_columns(tables)
        check_dates(tables)
        check_categories(tables)
        check_foreign_keys(tables)
        check_relationships(tables)
        check_business_rules(tables)
        check_duplicate_sales(tables)
    else:
        print("Some expected columns are missing; fix the file structure before other checks can run.")

    report = build_report()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(REPORT_PATH, index=False)
    print_report(report, tables)


if __name__ == "__main__":
    main()
