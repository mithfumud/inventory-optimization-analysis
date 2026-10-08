"""
clean_data.py

Applies the approved data cleaning plan to the five raw CSV files and saves
cleaned copies to data/cleaned/. Raw files in data/raw/ are only read, never
written. No rows are removed.

Run from the project root:

    python scripts/clean_data.py

Approved actions:
    All tables  Trim leading/trailing spaces, collapse repeated inner spaces,
                upper-case ID columns.
    products    Prices to 2 decimals; add has_sales_2025 (Yes/No).
    stores      Text standardization only.
    suppliers   lead_time_days as whole numbers; on_time_delivery_rate kept as
                a 0-1 fraction rounded to 3 decimals.
    sales       order_date as YYYY-MM-DD; quantity as whole numbers; revenue to
                2 decimals; add possible_repeat_purchase (Yes/No).
    inventory   Stock and age as whole numbers; add stock_status
                (In Stock / Out of Stock).

Assumptions (documented, not applied to the data):
    - inventory.csv is a snapshot as of 2025-12-31.
    - inventory_age_days on Out of Stock rows is kept but should be excluded
      from average-age calculations.
"""

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "data" / "raw"
CLEAN_DIR = PROJECT_DIR / "data" / "cleaned"
SUMMARY_PATH = PROJECT_DIR / "documentation" / "cleaning_summary.csv"

TABLES = ["products", "stores", "suppliers", "sales", "inventory"]
ID_COLUMNS = ["product_id", "store_id", "supplier_id", "order_id"]

MONEY_COLUMNS = {
    "products": ["unit_cost", "selling_price"],
    "sales": ["revenue"],
}
WHOLE_NUMBER_COLUMNS = {
    "suppliers": ["lead_time_days"],
    "sales": ["quantity"],
    "inventory": ["current_stock", "inventory_age_days"],
}

PRIMARY_KEYS = {
    "products": ["product_id"],
    "stores": ["store_id"],
    "suppliers": ["supplier_id", "product_id"],
    "sales": ["order_id"],
    "inventory": ["product_id", "store_id"],
}
FOREIGN_KEYS = [
    ("sales", "product_id", "products", "product_id"),
    ("sales", "store_id", "stores", "store_id"),
    ("inventory", "product_id", "products", "product_id"),
    ("inventory", "store_id", "stores", "store_id"),
    ("suppliers", "product_id", "products", "product_id"),
]
REPEAT_PURCHASE_COLUMNS = ["order_date", "product_id", "store_id", "quantity", "revenue"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def file_hash(path):
    return hashlib.md5(path.read_bytes()).hexdigest()


def count_changed(before, after):
    """Number of values whose text differs between two versions of the data."""
    before = before.astype(str)
    after = after.astype(str)
    return int((before != after).to_numpy().sum())


def load_raw():
    """Read every column as text so each conversion below is deliberate."""
    return {name: pd.read_csv(RAW_DIR / f"{name}.csv", dtype=str) for name in TABLES}


# ---------------------------------------------------------------------------
# Cleaning steps
# ---------------------------------------------------------------------------

def standardize_text(df, log):
    before = df.copy()
    for col in df.columns:
        df[col] = df[col].str.strip().str.replace(r"\s+", " ", regex=True)
    for col in df.columns.intersection(ID_COLUMNS):
        df[col] = df[col].str.upper()
    log.append(f"Trimmed whitespace and standardized ID case ({count_changed(before, df):,} values changed)")


def format_money(df, columns, log):
    before = df[columns].copy()
    for col in columns:
        df[col] = pd.to_numeric(df[col], errors="raise").round(2).map("{:.2f}".format)
    log.append(f"Formatted {', '.join(columns)} to 2 decimal places "
               f"({count_changed(before, df[columns]):,} values reformatted, amounts unchanged)")


def format_whole_numbers(df, columns, log):
    before = df[columns].copy()
    for col in columns:
        values = pd.to_numeric(df[col], errors="raise")
        if (values % 1 != 0).any():
            raise ValueError(f"{col} contains non-whole numbers; check the data quality report.")
        df[col] = values.astype("int64")
    log.append(f"Stored {', '.join(columns)} as whole numbers "
               f"({count_changed(before, df[columns]):,} values changed)")


def clean_products(products, sales, log):
    standardize_text(products, log)
    format_money(products, MONEY_COLUMNS["products"], log)
    products["has_sales_2025"] = np.where(products["product_id"].isin(sales["product_id"]), "Yes", "No")
    n_no = (products["has_sales_2025"] == "No").sum()
    log.append(f"Added has_sales_2025 flag ({n_no} products marked No, all kept)")
    return products


def clean_stores(stores, log):
    standardize_text(stores, log)
    return stores


def clean_suppliers(suppliers, log):
    standardize_text(suppliers, log)
    format_whole_numbers(suppliers, WHOLE_NUMBER_COLUMNS["suppliers"], log)

    before = suppliers[["on_time_delivery_rate"]].copy()
    suppliers["on_time_delivery_rate"] = pd.to_numeric(
        suppliers["on_time_delivery_rate"], errors="raise"
    ).round(3)
    log.append("Kept on_time_delivery_rate as a 0-1 fraction rounded to 3 decimals "
               f"({count_changed(before, suppliers[['on_time_delivery_rate']]):,} values changed)")
    return suppliers


def clean_sales(sales, log):
    standardize_text(sales, log)

    before = sales[["order_date"]].copy()
    dates = pd.to_datetime(sales["order_date"], format="%Y-%m-%d", errors="raise")
    sales["order_date"] = dates.dt.strftime("%Y-%m-%d")
    log.append(f"Validated order_date as YYYY-MM-DD dates ({count_changed(before, sales[['order_date']]):,} values changed)")

    format_whole_numbers(sales, WHOLE_NUMBER_COLUMNS["sales"], log)
    format_money(sales, MONEY_COLUMNS["sales"], log)

    repeat = sales.duplicated(subset=REPEAT_PURCHASE_COLUMNS, keep=False)
    sales["possible_repeat_purchase"] = np.where(repeat, "Yes", "No")
    log.append(f"Added possible_repeat_purchase flag ({repeat.sum()} rows marked Yes, all kept)")
    return sales


def clean_inventory(inventory, log):
    standardize_text(inventory, log)
    format_whole_numbers(inventory, WHOLE_NUMBER_COLUMNS["inventory"], log)

    inventory["stock_status"] = np.where(inventory["current_stock"] == 0, "Out of Stock", "In Stock")
    n_out = (inventory["stock_status"] == "Out of Stock").sum()
    log.append(f"Added stock_status flag ({n_out:,} rows Out of Stock, zeros kept as 0)")
    return inventory


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate(raw, clean):
    """Return a list of problems. An empty list means everything passed."""
    problems = []

    for name in TABLES:
        if len(raw[name]) != len(clean[name]):
            problems.append(f"{name}: row count changed {len(raw[name])} -> {len(clean[name])}")
        missing_cols = set(raw[name].columns) - set(clean[name].columns)
        if missing_cols:
            problems.append(f"{name}: original columns missing {sorted(missing_cols)}")

    for name, keys in PRIMARY_KEYS.items():
        dupes = clean[name].duplicated(subset=keys).sum()
        nulls = clean[name][keys].isna().any(axis=1).sum()
        if dupes or nulls:
            problems.append(f"{name}: primary key {keys} has {dupes} duplicates and {nulls} blanks")

    for child, col, parent, parent_col in FOREIGN_KEYS:
        orphans = (~clean[child][col].isin(clean[parent][parent_col])).sum()
        if orphans:
            problems.append(f"{child}.{col}: {orphans} values not found in {parent}.{parent_col}")

    totals = [
        ("sales", "revenue"),
        ("sales", "quantity"),
        ("inventory", "current_stock"),
        ("inventory", "inventory_age_days"),
        ("products", "unit_cost"),
        ("products", "selling_price"),
    ]
    for name, col in totals:
        before = pd.to_numeric(raw[name][col]).sum()
        after = pd.to_numeric(clean[name][col]).sum()
        if round(before, 2) != round(after, 2):
            problems.append(f"{name}.{col}: total changed {before:,.2f} -> {after:,.2f}")

    return problems


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    raw_hashes_before = {name: file_hash(RAW_DIR / f"{name}.csv") for name in TABLES}

    raw = load_raw()
    working = {name: df.copy() for name, df in raw.items()}
    logs = {name: [] for name in TABLES}

    clean = {}
    clean["sales"] = clean_sales(working["sales"], logs["sales"])
    clean["products"] = clean_products(working["products"], clean["sales"], logs["products"])
    clean["stores"] = clean_stores(working["stores"], logs["stores"])
    clean["suppliers"] = clean_suppliers(working["suppliers"], logs["suppliers"])
    clean["inventory"] = clean_inventory(working["inventory"], logs["inventory"])

    problems = validate(raw, clean)
    if problems:
        raise SystemExit("Validation failed; no files written:\n  " + "\n  ".join(problems))

    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    for name in TABLES:
        clean[name].to_csv(CLEAN_DIR / f"{name}_cleaned.csv", index=False, encoding="utf-8")

    raw_hashes_after = {name: file_hash(RAW_DIR / f"{name}.csv") for name in TABLES}
    if raw_hashes_before != raw_hashes_after:
        raise SystemExit("A raw file changed during cleaning. Investigate before using the output.")

    summary = pd.DataFrame([
        {
            "Dataset": name,
            "Rows Before": len(raw[name]),
            "Rows After": len(clean[name]),
            "Columns Before": raw[name].shape[1],
            "Columns After": clean[name].shape[1],
            "Changes Made": "; ".join(logs[name]),
        }
        for name in TABLES
    ])
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(SUMMARY_PATH, index=False)

    print("Validation passed: row counts, totals, primary keys and foreign keys all OK.")
    print("Raw files unchanged (verified by file fingerprint).\n")
    for name in TABLES:
        print(f"Saved {CLEAN_DIR / f'{name}_cleaned.csv'}")
    print(f"Saved {SUMMARY_PATH}\n")

    for _, row in summary.iterrows():
        print(f"{row['Dataset']}: {row['Rows Before']:,} -> {row['Rows After']:,} rows, "
              f"{row['Columns Before']} -> {row['Columns After']} columns")
        for change in row["Changes Made"].split("; "):
            print(f"    - {change}")


if __name__ == "__main__":
    main()
