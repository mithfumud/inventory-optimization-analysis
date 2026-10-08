-- =============================================================================
-- 01_create_tables.sql
-- Urban Retail Co. - Inventory Optimization & Performance Analysis
--
-- Creates the five tables of the retail_inventory database, plus indexes.
-- This script only creates structure; it does not load any data.
--
-- How to run (while connected to the retail_inventory database):
--   psql:     psql -U postgres -d retail_inventory -f sql/01_create_tables.sql
--   pgAdmin:  open the Query Tool on retail_inventory, paste this file, run it.
--
-- Safe to re-run:
--   - Everything is inside one transaction: if any statement fails, nothing
--     is created and the database is left exactly as it was.
--   - IF NOT EXISTS skips objects that already exist instead of failing.
--     Note: it will NOT update an existing table whose definition differs.
--
-- Creation order matters: a foreign key can only reference a table that
-- already exists, so the parent tables (products, stores) come first.
-- =============================================================================

BEGIN;


-- -----------------------------------------------------------------------------
-- 1. products
-- The product catalogue: one row per product.
-- Parent table for product_suppliers, sales and inventory.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS products (
    product_id      VARCHAR(10)    NOT NULL PRIMARY KEY,  -- e.g. 'P0001'
    product_name    VARCHAR(100)   NOT NULL,
    category        VARCHAR(50)    NOT NULL,
    unit_cost       NUMERIC(10,2)  NOT NULL,              -- INR paid to the supplier per unit
    selling_price   NUMERIC(10,2)  NOT NULL,              -- INR list price per unit, before discount
    has_sales_2025  BOOLEAN        NOT NULL               -- FALSE = no sales in 2025 (dead stock)
);


-- -----------------------------------------------------------------------------
-- 2. stores
-- The Urban Retail Co. store network: one row per store.
-- Parent table for sales and inventory.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stores (
    store_id    VARCHAR(10)   NOT NULL PRIMARY KEY,  -- e.g. 'S001'
    store_name  VARCHAR(100)  NOT NULL,
    city        VARCHAR(50)   NOT NULL,              -- not unique: some cities have 2 stores
    region      VARCHAR(20)   NOT NULL,

    -- Only the five known regions are allowed; blocks typos such as 'north'.
    CONSTRAINT chk_stores_region
        CHECK (region IN ('North', 'South', 'East', 'West', 'Central'))
);


-- -----------------------------------------------------------------------------
-- 3. product_suppliers
-- Which supplier provides which product: one row per supplier-product pair.
-- A supplier serves many products, and some products have two suppliers,
-- so neither ID is unique on its own; only the pair is.
--
-- supplier_id is NOT a foreign key: there is no separate suppliers table.
-- WARNING for analysis: joining sales directly to this table duplicates sales
-- rows for products with two suppliers. Aggregate per product first.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS product_suppliers (
    supplier_id            VARCHAR(10)   NOT NULL,  -- e.g. 'SUP001'
    supplier_name          VARCHAR(100)  NOT NULL,
    product_id             VARCHAR(10)   NOT NULL,
    lead_time_days         INTEGER       NOT NULL,  -- days from purchase order to delivery
    on_time_delivery_rate  NUMERIC(4,3)  NOT NULL,  -- fraction 0-1, e.g. 0.840 = 84%

    -- Composite primary key: each supplier-product pair appears only once.
    CONSTRAINT pk_product_suppliers
        PRIMARY KEY (supplier_id, product_id),

    -- Every product_id must exist in products.
    CONSTRAINT fk_product_suppliers_product
        FOREIGN KEY (product_id) REFERENCES products (product_id),

    CONSTRAINT chk_product_suppliers_lead_time
        CHECK (lead_time_days >= 0),

    -- Stored as a fraction, so it must be between 0 (0%) and 1 (100%).
    CONSTRAINT chk_product_suppliers_on_time_rate
        CHECK (on_time_delivery_rate BETWEEN 0 AND 1)
);


-- -----------------------------------------------------------------------------
-- 4. sales
-- Every sales transaction in 2025: one row per order line
-- (one product, at one store, on one date).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sales (
    order_id                  VARCHAR(12)    NOT NULL PRIMARY KEY,  -- e.g. 'ORD000001'
    order_date                DATE           NOT NULL,
    product_id                VARCHAR(10)    NOT NULL,
    store_id                  VARCHAR(10)    NOT NULL,
    quantity                  INTEGER        NOT NULL,              -- units sold
    revenue                   NUMERIC(10,2)  NOT NULL,              -- INR received, AFTER discount
    possible_repeat_purchase  BOOLEAN        NOT NULL,              -- TRUE = looks like another order; kept as legitimate

    -- Every sale must point to a real product and a real store.
    -- Default behaviour also blocks deleting a product or store that has sales.
    CONSTRAINT fk_sales_product
        FOREIGN KEY (product_id) REFERENCES products (product_id),

    CONSTRAINT fk_sales_store
        FOREIGN KEY (store_id) REFERENCES stores (store_id),

    CONSTRAINT chk_sales_quantity
        CHECK (quantity > 0),

    CONSTRAINT chk_sales_revenue
        CHECK (revenue > 0)
);


-- -----------------------------------------------------------------------------
-- 5. inventory
-- Current stock snapshot (assumed as of 2025-12-31):
-- one row per product per store that carries it.
-- When averaging inventory_age_days, exclude 'Out of Stock' rows.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS inventory (
    product_id          VARCHAR(10)  NOT NULL,
    store_id            VARCHAR(10)  NOT NULL,
    current_stock       INTEGER      NOT NULL,  -- units on hand; 0 = stockout (real value, not missing)
    inventory_age_days  INTEGER      NOT NULL,  -- average days the stock has been held
    stock_status        VARCHAR(12)  NOT NULL,  -- 'In Stock' or 'Out of Stock'

    -- Composite primary key: each product appears once per store.
    CONSTRAINT pk_inventory
        PRIMARY KEY (product_id, store_id),

    CONSTRAINT fk_inventory_product
        FOREIGN KEY (product_id) REFERENCES products (product_id),

    CONSTRAINT fk_inventory_store
        FOREIGN KEY (store_id) REFERENCES stores (store_id),

    -- Zero is allowed (stockout); negative stock is not.
    CONSTRAINT chk_inventory_current_stock
        CHECK (current_stock >= 0),

    CONSTRAINT chk_inventory_age
        CHECK (inventory_age_days >= 0),

    CONSTRAINT chk_inventory_stock_status
        CHECK (stock_status IN ('In Stock', 'Out of Stock'))
);


-- -----------------------------------------------------------------------------
-- Indexes
-- PostgreSQL indexes primary keys automatically, but not foreign keys.
-- These speed up the most common joins and date filters on sales.
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_sales_product_id ON sales (product_id);
CREATE INDEX IF NOT EXISTS idx_sales_store_id   ON sales (store_id);
CREATE INDEX IF NOT EXISTS idx_sales_order_date ON sales (order_date);


COMMIT;
