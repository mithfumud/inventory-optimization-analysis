"""
generate_data.py

Generates a reproducible synthetic retail dataset for the fictional company
Urban Retail Co. and saves five CSV files to data/raw/:

    products.csv, stores.csv, suppliers.csv, sales.csv, inventory.csv

Run from the project root:

    python scripts/generate_data.py
"""

from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

SEED = 42
N_PRODUCTS = 1_000
N_SUPPLIERS = 40
N_SALES = 60_000
START_DATE = "2025-01-01"
END_DATE = "2025-12-31"

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

rng = np.random.default_rng(SEED)

# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

# product_share:  fraction of the catalogue in this category (sums to 1.0)
# margin_range:   profit margin as a fraction of selling price
# demand_weight:  how often products in this category get bought
# extra_qty:      average number of extra units per order (on top of 1)
# items:          item type -> (min price, max price) in INR
CATEGORIES = {
    "Electronics": {
        "product_share": 0.12,
        "margin_range": (0.12, 0.28),
        "demand_weight": 0.8,
        "extra_qty": 0.15,
        "items": {
            "Wireless Earbuds": (999, 4999),
            "Bluetooth Speaker": (1499, 7999),
            "Smartwatch": (1999, 14999),
            "Power Bank": (699, 2999),
            "LED Monitor": (7999, 24999),
            "Wireless Mouse": (399, 1499),
            "Mechanical Keyboard": (1999, 7999),
            "Headphones": (999, 9999),
            "Smart Bulb": (399, 1299),
            "USB Charger": (299, 1299),
        },
    },
    "Home & Kitchen": {
        "product_share": 0.15,
        "margin_range": (0.25, 0.45),
        "demand_weight": 1.0,
        "extra_qty": 0.4,
        "items": {
            "Non-Stick Pan": (599, 2499),
            "Pressure Cooker": (1199, 3999),
            "Water Bottle": (199, 899),
            "Dinner Set": (999, 4999),
            "Mixer Grinder": (2499, 7999),
            "Bedsheet Set": (699, 2999),
            "Storage Container Set": (299, 1499),
            "Electric Kettle": (799, 2499),
            "Wall Clock": (399, 1999),
            "Cushion Cover": (199, 799),
        },
    },
    "Apparel": {
        "product_share": 0.18,
        "margin_range": (0.40, 0.60),
        "demand_weight": 1.2,
        "extra_qty": 0.5,
        "items": {
            "Cotton T-Shirt": (299, 999),
            "Denim Jeans": (999, 2999),
            "Kurta": (599, 2499),
            "Hoodie": (899, 2999),
            "Formal Shirt": (799, 2499),
            "Track Pants": (499, 1499),
            "Saree": (999, 5999),
            "Jacket": (1499, 4999),
            "Socks Pack": (149, 499),
            "Leggings": (299, 899),
        },
    },
    "Grocery": {
        "product_share": 0.15,
        "margin_range": (0.08, 0.20),
        "demand_weight": 2.2,
        "extra_qty": 1.8,
        "items": {
            "Basmati Rice 5kg": (499, 999),
            "Sunflower Oil 1L": (139, 219),
            "Green Tea": (149, 449),
            "Instant Coffee": (199, 699),
            "Whole Wheat Atta 5kg": (229, 399),
            "Mixed Dry Fruits": (399, 1199),
            "Breakfast Cereal": (149, 449),
            "Masala Noodles Pack": (49, 149),
            "Organic Honey": (199, 599),
            "Tomato Ketchup": (99, 199),
        },
    },
    "Beauty & Personal Care": {
        "product_share": 0.13,
        "margin_range": (0.35, 0.55),
        "demand_weight": 1.4,
        "extra_qty": 0.7,
        "items": {
            "Face Wash": (149, 499),
            "Shampoo": (199, 699),
            "Moisturizer": (249, 899),
            "Sunscreen": (299, 799),
            "Perfume": (499, 2999),
            "Lipstick": (199, 999),
            "Hair Oil": (99, 399),
            "Body Lotion": (199, 599),
            "Beard Trimmer": (999, 2999),
            "Toothpaste Pack": (99, 299),
        },
    },
    "Sports & Fitness": {
        "product_share": 0.09,
        "margin_range": (0.25, 0.45),
        "demand_weight": 0.6,
        "extra_qty": 0.2,
        "items": {
            "Yoga Mat": (499, 1999),
            "Dumbbell Set": (999, 4999),
            "Cricket Bat": (999, 6999),
            "Football": (499, 1999),
            "Badminton Racket": (599, 3999),
            "Skipping Rope": (149, 599),
            "Gym Gloves": (299, 999),
            "Cycling Helmet": (999, 3499),
            "Resistance Bands": (299, 1299),
            "Sports Shoes": (1499, 5999),
        },
    },
    "Toys & Games": {
        "product_share": 0.08,
        "margin_range": (0.30, 0.50),
        "demand_weight": 0.5,
        "extra_qty": 0.3,
        "items": {
            "Building Blocks": (499, 2999),
            "Remote Control Car": (999, 3999),
            "Board Game": (399, 1999),
            "Jigsaw Puzzle": (299, 999),
            "Soft Toy": (299, 1499),
            "Action Figure": (399, 1499),
            "Doll House": (1499, 4999),
            "Art & Craft Kit": (299, 1199),
            "Toy Train Set": (799, 2999),
            "Puzzle Cube": (149, 599),
        },
    },
    "Stationery": {
        "product_share": 0.10,
        "margin_range": (0.30, 0.50),
        "demand_weight": 0.9,
        "extra_qty": 1.2,
        "items": {
            "Notebook Pack": (99, 399),
            "Gel Pen Set": (49, 249),
            "Sketch Pens": (49, 199),
            "Geometry Box": (99, 349),
            "School Backpack": (599, 2499),
            "Desk Organizer": (299, 999),
            "Sticky Notes": (49, 199),
            "Water Colours": (99, 499),
            "File Folder Set": (99, 399),
            "Scientific Calculator": (499, 1499),
        },
    },
}

BRANDS = [
    "Nova", "Zenith", "UrbanEdge", "Kosmo", "Aura", "Trivo", "Pristine",
    "Vista", "Lumo", "Orbit", "Bloom", "Indus", "Sapphire", "Everyday", "Kriti",
]

# Hidden demand tiers: share of products, and how strongly they sell.
DEMAND_TIERS = {
    "high": {"share": 0.15, "multiplier": 4.0},
    "regular": {"share": 0.60, "multiplier": 1.0},
    "slow": {"share": 0.25, "multiplier": 0.15},
}

# (area, city, region, format)
STORE_LIST = [
    ("Connaught Place", "New Delhi", "North", "Flagship"),
    ("Saket", "New Delhi", "North", "Standard"),
    ("Cyber Hub", "Gurugram", "North", "Standard"),
    ("Sector 18", "Noida", "North", "Express"),
    ("MI Road", "Jaipur", "North", "Standard"),
    ("Hazratganj", "Lucknow", "North", "Standard"),
    ("Sector 17", "Chandigarh", "North", "Express"),
    ("Andheri", "Mumbai", "West", "Flagship"),
    ("Lower Parel", "Mumbai", "West", "Standard"),
    ("Koregaon Park", "Pune", "West", "Standard"),
    ("SG Highway", "Ahmedabad", "West", "Standard"),
    ("Adajan", "Surat", "West", "Express"),
    ("Koramangala", "Bengaluru", "South", "Flagship"),
    ("Whitefield", "Bengaluru", "South", "Standard"),
    ("T Nagar", "Chennai", "South", "Standard"),
    ("Banjara Hills", "Hyderabad", "South", "Standard"),
    ("Edappally", "Kochi", "South", "Express"),
    ("RS Puram", "Coimbatore", "South", "Express"),
    ("Salt Lake", "Kolkata", "East", "Flagship"),
    ("Park Street", "Kolkata", "East", "Standard"),
    ("Saheed Nagar", "Bhubaneswar", "East", "Express"),
    ("Boring Road", "Patna", "East", "Express"),
    ("GS Road", "Guwahati", "East", "Express"),
    ("Vijay Nagar", "Indore", "Central", "Standard"),
    ("MP Nagar", "Bhopal", "Central", "Express"),
    ("Sitabuldi", "Nagpur", "Central", "Express"),
]

# traffic: relative number of orders; assortment: share of catalogue carried
STORE_FORMATS = {
    "Flagship": {"traffic": 2.0, "assortment": 0.95},
    "Standard": {"traffic": 1.0, "assortment": 0.75},
    "Express": {"traffic": 0.5, "assortment": 0.50},
}

SUPPLIER_PREFIXES = [
    "Shree", "Apex", "Bharat", "Global", "Sunrise", "Metro", "Vardhman",
    "Elite", "Royal", "National", "Om Sai", "Galaxy", "Pioneer", "Reliable",
    "Ganga", "Deccan",
]
SUPPLIER_SUFFIXES = [
    "Traders", "Distributors", "Enterprises", "Wholesale", "Supply Co.",
    "Imports", "Agencies", "Logistics",
]

# Hidden supplier quality tiers.
SUPPLIER_TIERS = {
    "excellent": {"share": 0.25, "on_time": (0.92, 0.98), "lead_time": (3, 7)},
    "average": {"share": 0.50, "on_time": (0.80, 0.90), "lead_time": (6, 12)},
    "poor": {"share": 0.25, "on_time": (0.60, 0.78), "lead_time": (10, 21)},
}

# Festive season (Oct-Dec) gets more orders; Feb and Jul are quieter.
MONTH_FACTOR = {
    1: 0.85, 2: 0.80, 3: 0.90, 4: 0.90, 5: 0.95, 6: 0.90,
    7: 0.85, 8: 1.00, 9: 1.00, 10: 1.35, 11: 1.40, 12: 1.25,
}
WEEKEND_FACTOR = 1.3

DISCOUNTS = [0.00, 0.05, 0.10, 0.20]
DISCOUNT_PROBS = [0.60, 0.20, 0.15, 0.05]

CATEGORY_NAMES = list(CATEGORIES)


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

def generate_products():
    """Return the products table plus the hidden demand tier of each product."""
    shares = [CATEGORIES[c]["product_share"] for c in CATEGORY_NAMES]
    categories = rng.choice(CATEGORY_NAMES, size=N_PRODUCTS, p=shares)

    rows = []
    for i, category in enumerate(categories, start=1):
        info = CATEGORIES[category]
        item = rng.choice(list(info["items"]))
        low, high = info["items"][item]

        # Round to a "retail looking" price like 499 or 1,299.
        price = rng.uniform(low, high)
        price = max(round(price / 10) * 10 - 1, 9)

        margin = rng.uniform(*info["margin_range"])
        unit_cost = round(price * (1 - margin), 2)

        brand = rng.choice(BRANDS)
        model = f"{rng.choice(list('ABCDEFGHKLMNPRSTVXZ'))}{rng.integers(10, 1000)}"

        rows.append({
            "product_id": f"P{i:04d}",
            "product_name": f"{brand} {item} {model}",
            "category": category,
            "unit_cost": unit_cost,
            "selling_price": float(price),
        })

    products = pd.DataFrame(rows)

    tier_names = list(DEMAND_TIERS)
    tier_shares = [DEMAND_TIERS[t]["share"] for t in tier_names]
    demand_tier = rng.choice(tier_names, size=N_PRODUCTS, p=tier_shares)

    return products, demand_tier


def product_popularity(products, demand_tier):
    """Relative chance of each product being picked in an order."""
    category_weight = products["category"].map(
        lambda c: CATEGORIES[c]["demand_weight"]
    ).to_numpy()
    tier_weight = np.array([DEMAND_TIERS[t]["multiplier"] for t in demand_tier])

    # Cheaper items sell a bit more often than expensive ones in the same category.
    category_median = products.groupby("category")["selling_price"].transform("median")
    price_weight = (category_median / products["selling_price"]).to_numpy() ** 0.3

    noise = rng.lognormal(mean=0, sigma=0.35, size=len(products))
    return category_weight * tier_weight * price_weight * noise


def generate_stores():
    """Return the stores table plus each store's format."""
    stores = pd.DataFrame(STORE_LIST, columns=["area", "city", "region", "format"])
    stores.insert(0, "store_id", [f"S{i:03d}" for i in range(1, len(stores) + 1)])
    stores["store_name"] = "Urban Retail - " + stores["area"]

    store_format = stores["format"].to_numpy()
    stores = stores[["store_id", "store_name", "city", "region"]]
    return stores, store_format


def generate_assortment(store_format, demand_tier):
    """
    Boolean matrix [store, product]: True if the store carries the product.
    High-demand products are carried everywhere.
    """
    n_stores = len(store_format)
    carry_prob = np.array([STORE_FORMATS[f]["assortment"] for f in store_format])
    carried = rng.random((n_stores, N_PRODUCTS)) < carry_prob[:, None]
    carried[:, demand_tier == "high"] = True
    return carried


def generate_suppliers(products):
    """One row per supplier-product pair. Each supplier specialises in one category."""
    all_names = [f"{p} {s}" for p in SUPPLIER_PREFIXES for s in SUPPLIER_SUFFIXES]
    names = rng.choice(all_names, size=N_SUPPLIERS, replace=False)

    tier_names = list(SUPPLIER_TIERS)
    tier_shares = [SUPPLIER_TIERS[t]["share"] for t in tier_names]

    suppliers = pd.DataFrame({
        "supplier_id": [f"SUP{i:03d}" for i in range(1, N_SUPPLIERS + 1)],
        "supplier_name": names,
        # Cycling through categories gives every category 5 suppliers.
        "category": [CATEGORY_NAMES[i % len(CATEGORY_NAMES)] for i in range(N_SUPPLIERS)],
        "tier": rng.choice(tier_names, size=N_SUPPLIERS, p=tier_shares),
    })
    suppliers["base_on_time"] = [
        rng.uniform(*SUPPLIER_TIERS[t]["on_time"]) for t in suppliers["tier"]
    ]
    suppliers["base_lead_time"] = [
        rng.integers(SUPPLIER_TIERS[t]["lead_time"][0], SUPPLIER_TIERS[t]["lead_time"][1] + 1)
        for t in suppliers["tier"]
    ]

    rows = []
    for product_id, category in zip(products["product_id"], products["category"]):
        candidates = suppliers[suppliers["category"] == category]
        # About 25% of products have a backup supplier.
        n_suppliers = 2 if rng.random() < 0.25 else 1
        chosen = candidates.sample(n=n_suppliers, random_state=rng)

        for _, sup in chosen.iterrows():
            lead_time = max(1, sup["base_lead_time"] + rng.integers(-1, 3))
            on_time = np.clip(sup["base_on_time"] + rng.normal(0, 0.02), 0.50, 0.99)
            rows.append({
                "supplier_id": sup["supplier_id"],
                "supplier_name": sup["supplier_name"],
                "product_id": product_id,
                "lead_time_days": int(lead_time),
                "on_time_delivery_rate": round(float(on_time), 3),
            })

    return pd.DataFrame(rows).sort_values(["supplier_id", "product_id"], ignore_index=True)


def generate_sales(products, popularity, demand_tier, store_ids, store_format, carried):
    """
    Return the sales table plus expected annual units for every [store, product].
    The expected units are later used to set realistic inventory levels.
    """
    n_stores = len(store_ids)
    category_index = products["category"].map(CATEGORY_NAMES.index).to_numpy()

    # Some stores sell more of certain categories than others.
    affinity = rng.uniform(0.7, 1.3, size=(n_stores, len(CATEGORY_NAMES)))

    traffic = np.array([STORE_FORMATS[f]["traffic"] for f in store_format])
    traffic = traffic * rng.uniform(0.85, 1.15, size=n_stores)
    orders_per_store = rng.multinomial(N_SALES, traffic / traffic.sum())

    extra_qty = products["category"].map(lambda c: CATEGORIES[c]["extra_qty"]).to_numpy()
    extra_qty = extra_qty * np.where(demand_tier == "high", 1.3, 1.0)

    expected_units = np.zeros((n_stores, N_PRODUCTS))
    chunks = []
    for s in range(n_stores):
        weights = popularity * affinity[s, category_index] * carried[s]
        probs = weights / weights.sum()

        product_idx = rng.choice(N_PRODUCTS, size=orders_per_store[s], p=probs)
        chunks.append(pd.DataFrame({"product_idx": product_idx, "store_id": store_ids[s]}))

        expected_units[s] = orders_per_store[s] * probs * (1 + extra_qty)

    sales = pd.concat(chunks, ignore_index=True)

    dates = pd.date_range(START_DATE, END_DATE, freq="D")
    day_weight = dates.month.map(MONTH_FACTOR).to_numpy() * np.where(
        dates.dayofweek >= 5, WEEKEND_FACTOR, 1.0
    )
    sales["order_date"] = rng.choice(dates.to_numpy(), size=len(sales), p=day_weight / day_weight.sum())

    idx = sales["product_idx"].to_numpy()
    sales["product_id"] = products["product_id"].to_numpy()[idx]
    sales["quantity"] = 1 + rng.poisson(extra_qty[idx])

    discount = rng.choice(DISCOUNTS, size=len(sales), p=DISCOUNT_PROBS)
    price = products["selling_price"].to_numpy()[idx]
    sales["revenue"] = np.round(sales["quantity"] * price * (1 - discount), 2)

    sales = sales.sort_values(["order_date", "store_id"], ignore_index=True)
    sales["order_id"] = [f"ORD{i:06d}" for i in range(1, len(sales) + 1)]
    sales["order_date"] = sales["order_date"].dt.strftime("%Y-%m-%d")

    sales = sales[["order_id", "order_date", "product_id", "store_id", "quantity", "revenue"]]
    return sales, expected_units


def generate_inventory(products, demand_tier, store_ids, carried, expected_units):
    """
    Current stock for every product a store carries.

    Stock is normally sized as "days of cover" of expected demand, with two
    deliberate problem groups mixed in:
      - overstock:     slow movers with lots of old stock
      - stockout risk: high-demand items with very little stock
    """
    overstock = (demand_tier == "slow") & (rng.random(N_PRODUCTS) < 0.40)
    stockout_risk = (demand_tier == "high") & (rng.random(N_PRODUCTS) < 0.40)

    store_idx, product_idx = np.nonzero(carried)
    n_rows = len(store_idx)

    tier = demand_tier[product_idx]
    is_overstock = overstock[product_idx]
    is_stockout = stockout_risk[product_idx]
    daily_demand = expected_units[store_idx, product_idx] / 365

    # Normal stock: roughly 20-90 days of demand, with at least one unit on the
    # shelf, except for a few random rows that have just sold out.
    days_of_cover = rng.uniform(20, 90, size=n_rows)
    stock = np.maximum(1, rng.poisson(daily_demand * days_of_cover))
    stock = np.where(rng.random(n_rows) < 0.03, 0, stock)

    stock = np.where(is_overstock, rng.integers(30, 151, size=n_rows), stock)
    stockout_stock = rng.poisson(daily_demand * rng.uniform(1, 7, size=n_rows))
    stock = np.where(is_stockout, stockout_stock, stock)

    # Fresh stock for fast movers, older stock for slow movers.
    age = np.select(
        [tier == "high", tier == "regular"],
        [rng.integers(5, 46, size=n_rows), rng.integers(15, 121, size=n_rows)],
        default=rng.integers(60, 271, size=n_rows),
    )
    age = np.where(is_overstock, rng.integers(180, 541, size=n_rows), age)
    age = np.where(is_stockout, rng.integers(1, 21, size=n_rows), age)

    inventory = pd.DataFrame({
        "product_id": products["product_id"].to_numpy()[product_idx],
        "store_id": np.asarray(store_ids)[store_idx],
        "current_stock": stock.astype(int),
        "inventory_age_days": age.astype(int),
    })
    return inventory.sort_values(["product_id", "store_id"], ignore_index=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    products, demand_tier = generate_products()
    popularity = product_popularity(products, demand_tier)

    stores, store_format = generate_stores()
    store_ids = stores["store_id"].to_numpy()
    carried = generate_assortment(store_format, demand_tier)

    suppliers = generate_suppliers(products)
    sales, expected_units = generate_sales(
        products, popularity, demand_tier, store_ids, store_format, carried
    )
    inventory = generate_inventory(products, demand_tier, store_ids, carried, expected_units)

    tables = {
        "products": products,
        "stores": stores,
        "suppliers": suppliers,
        "sales": sales,
        "inventory": inventory,
    }
    for name, df in tables.items():
        path = OUTPUT_DIR / f"{name}.csv"
        df.to_csv(path, index=False)
        print(f"Saved {name + '.csv':<16} {len(df):>7,} rows  ->  {path}")


if __name__ == "__main__":
    main()
