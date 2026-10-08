# Inventory Optimization & Performance Analysis

## What this project is about

I built this project to look at a common retail operations problem: **how do you know when inventory is in a healthy position, and where are you likely to have stock sitting in the wrong place?**

Using sales, inventory, product, store, and supplier data, I looked for signs of:

- stockouts
- excess inventory
- slow-moving products
- high-demand products with low stock coverage
- differences in product, category, and store performance

The project covers the analysis from raw data all the way to a Power BI dashboard.

> **Note:** Urban Retail Co. and all data used in this project are fictional/synthetic and were created for portfolio purposes.

---

## The problem

A retail business has to balance two problems at the same time:

**Too little inventory** can lead to stockouts and missed sales.

**Too much inventory** ties up money in products that may not be moving.

The goal of this analysis was to identify where these problems might be happening and turn the findings into something that could help an inventory or operations team decide where to look first.

---

## Data

I created a synthetic dataset covering 2025 sales and a current inventory snapshot.

| Dataset | Records | What it contains |
|---|---:|---|
| Products | 1,000 | Product, category and pricing information |
| Stores | 26 | Store, city and region information |
| Suppliers | 1,262 | Product-supplier relationships |
| Sales | 60,000 | 2025 sales transactions |
| Inventory | 19,038 | Current stock and inventory age |

The raw data is kept in `data/raw/`, while the cleaned versions are in `data/cleaned/`.

---

## How I approached it

### 1. Data quality and cleaning

Before doing any analysis, I checked the raw data for things such as:

- missing values
- duplicate records
- invalid numeric values
- referential integrity
- invalid inventory values
- consistency between sales and inventory

I kept the raw data unchanged and created separate cleaned datasets.

I also added a few fields that were useful for the analysis:

- `has_sales_2025` — identifies products with no sales during 2025
- `possible_repeat_purchase` — flags sales records that may represent repeated purchases
- `stock_status` — identifies whether an inventory record is currently in stock or out of stock

The validation process included **111 checks**, with **109 passed** and **2 low-severity flags** requiring review.

---

## SQL analysis

I loaded the cleaned data into PostgreSQL and used SQL to answer the main business questions.

The analysis covers:

1. Overall KPIs
2. Revenue by category
3. Current inventory position and stockout rate
4. Average inventory age
5. Inventory age bands
6. High-demand, low-stock products
7. Potential excess inventory
8. Potential excess inventory by product
9. Products with no sales
10. Top products by revenue
11. Revenue by store
12. Regional performance
13. Store performance

The SQL queries used for the analysis are available in:

`sql/02_analysis_queries.sql`

---

## Power BI dashboard

I used Power BI to turn the SQL analysis into three dashboard pages.

### Executive Overview

A high-level view of:

- revenue
- units sold
- orders
- current inventory
- stockout rate
- monthly revenue trend
- inventory status
- revenue by category

### Inventory Health & Risk

Focused on where inventory problems may exist:

- inventory ageing
- stockout records
- inventory status
- high-demand products with low stock coverage

### Product & Store Performance

Focused on differences across:

- top products
- stores
- regions
- store-level performance

The Power BI file is available in:

`powerbi/inventory_optimization_dashboard.pbix`

---

## What I found

A few findings stood out from the analysis:

### Stock availability

The current inventory snapshot has a **9.03% stockout rate**, representing **1,720 out-of-stock inventory records**.

This gives the business a starting point for investigating where availability may be a problem.

### Potential excess inventory

Using a screening rule based on sales volume and months of stock, **102 SKUs** were flagged as potential excess inventory.

Together, these represented:

- **12,760 potential excess units**
- approximately **₹57.35 lakh of inventory value**

This should be treated as a **screening indicator**, not as guaranteed savings. The next step would be to investigate these products individually before taking action.

### Products with no sales

Six products had no recorded sales during 2025:

`P0003, P0213, P0495, P0750, P0803, P0896`

These products would be worth reviewing to understand whether they are genuinely inactive, newly introduced, or simply not selling.

### High demand, low stock

Several products had strong 2025 sales but less than one month of current stock coverage.

For example:

| Product | Units Sold | Current Stock | Months of Stock |
|---|---:|---:|---:|
| P0183 | 2,173 | 27 | 0.15 |
| P0961 | 2,163 | 19 | 0.11 |
| P0629 | 1,951 | 27 | 0.17 |
| P0470 | 1,523 | 12 | 0.09 |
| P0659 | 1,444 | 21 | 0.17 |

These are the types of products I would prioritize for a replenishment or allocation review.

---

## Tools used

- **Python / Pandas** — data generation, validation and cleaning
- **PostgreSQL** — data storage and SQL analysis
- **SQL** — KPI calculation and business analysis
- **Power BI** — dashboarding and visualization
- **Excel** — supporting data validation / review

---

## Project structure

```text
inventory-optimization-analysis/
│
├── data/
│   ├── raw/
│   └── cleaned/
│
├── documentation/
│   ├── cleaning_summary.csv
│   ├── data_dictionary.md
│   └── data_quality_report.csv
│
├── powerbi/
│   └── inventory_optimization_dashboard.pbix
│
├── scripts/
│   ├── clean_data.py
│   ├── data_quality_check.py
│   └── generate_data.py
│
├── sql/
│   ├── 01_create_tables.sql
│   └── 02_analysis_queries.sql
│
├── README.md
└── .gitignore
