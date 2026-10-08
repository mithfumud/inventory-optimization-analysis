-- Inventory Optimization & Performance Analysis
-- Analysis queries for the retail_inventory database (PostgreSQL)


-- Overall KPIs
-- each sales row is one order line, so total_orders = number of rows
WITH sales_2025 AS (
    SELECT
        SUM(revenue)               AS total_revenue,
        SUM(quantity)              AS total_units_sold,
        COUNT(order_id)            AS total_orders,
        COUNT(DISTINCT product_id) AS products_with_sales
    FROM sales
    WHERE order_date >= DATE '2025-01-01'
      AND order_date <  DATE '2026-01-01'
),
catalogue AS (
    SELECT COUNT(*) AS total_products
    FROM products
)
SELECT
    ROUND(s.total_revenue, 2)                  AS total_revenue,
    s.total_units_sold,
    s.total_orders,
    ROUND(s.total_revenue / s.total_orders, 2) AS avg_revenue_per_order,
    s.products_with_sales,
    c.total_products
FROM sales_2025 s
CROSS JOIN catalogue c;


-- Revenue by category
SELECT
    p.category,
    SUM(s.quantity) AS units_sold,
    ROUND(SUM(s.revenue), 2) AS revenue,
    ROUND(100.0 * SUM(s.revenue) / SUM(SUM(s.revenue)) OVER (), 2) AS pct_of_total_revenue
FROM sales s
JOIN products p ON p.product_id = s.product_id
WHERE s.order_date >= DATE '2025-01-01'
  AND s.order_date <  DATE '2026-01-01'
GROUP BY p.category
ORDER BY revenue DESC;


-- Current inventory position / stockout rate
-- stockout rate here is a snapshot (share of product-store rows at zero stock),
-- not a count of stockout events during the year
SELECT
    SUM(i.current_stock) AS total_inventory_units,
    COUNT(*) AS inventory_records,
    COUNT(*) FILTER (WHERE i.stock_status = 'Out of Stock') AS out_of_stock_records,
    ROUND(100.0 * COUNT(*) FILTER (WHERE i.stock_status = 'Out of Stock') / COUNT(*), 2)
        AS current_stockout_rate_pct,
    ROUND(SUM(i.current_stock * p.unit_cost), 2) AS inventory_value_at_cost
FROM inventory i
JOIN products p ON p.product_id = i.product_id;


-- Average inventory age
-- out-of-stock rows are excluded since there's no stock left to age
SELECT
    COUNT(*) AS in_stock_records,
    ROUND(AVG(inventory_age_days), 1) AS avg_inventory_age_days,
    COUNT(*) FILTER (WHERE inventory_age_days > 180) AS records_older_than_180_days,
    COUNT(*) FILTER (WHERE inventory_age_days > 365) AS records_older_than_365_days
FROM inventory
WHERE stock_status = 'In Stock';


-- Inventory age bands (in-stock rows only)
WITH aged_stock AS (
    SELECT
        i.current_stock,
        i.current_stock * p.unit_cost AS stock_value,
        CASE
            WHEN i.inventory_age_days <= 90  THEN '1. 0-90 days'
            WHEN i.inventory_age_days <= 180 THEN '2. 91-180 days'
            WHEN i.inventory_age_days <= 365 THEN '3. 181-365 days'
            ELSE '4. Over 365 days'
        END AS age_band
    FROM inventory i
    JOIN products p ON p.product_id = i.product_id
    WHERE i.stock_status = 'In Stock'
)
SELECT
    age_band,
    COUNT(*) AS inventory_records,
    SUM(current_stock) AS units,
    ROUND(SUM(stock_value), 2) AS stock_value_at_cost,
    ROUND(100.0 * SUM(stock_value) / SUM(SUM(stock_value)) OVER (), 2) AS pct_of_stock_value
FROM aged_stock
GROUP BY age_band
ORDER BY age_band;


-- High demand, low stock
-- months_of_stock = current_stock / (units_sold_2025 / 12)
-- flags low coverage for review, doesn't mean these products will definitely stock out
WITH product_sales AS (
    SELECT
        product_id,
        SUM(quantity) AS units_sold_2025,
        SUM(revenue)  AS revenue_2025
    FROM sales
    WHERE order_date >= DATE '2025-01-01'
      AND order_date <  DATE '2026-01-01'
    GROUP BY product_id
),
product_stock AS (
    SELECT product_id, SUM(current_stock) AS current_stock
    FROM inventory
    GROUP BY product_id
),
coverage AS (
    SELECT
        p.product_id,
        p.product_name,
        p.category,
        ps.units_sold_2025,
        ps.revenue_2025,
        COALESCE(st.current_stock, 0) AS current_stock,
        ps.units_sold_2025 / 12.0 AS avg_monthly_demand,
        COALESCE(st.current_stock, 0) / (ps.units_sold_2025 / 12.0) AS months_of_stock
    FROM products p
    JOIN product_sales ps ON ps.product_id = p.product_id
    LEFT JOIN product_stock st ON st.product_id = p.product_id
)
SELECT
    product_id,
    product_name,
    category,
    units_sold_2025,
    ROUND(avg_monthly_demand, 1) AS avg_monthly_demand,
    current_stock,
    ROUND(months_of_stock, 2) AS months_of_stock,
    ROUND(revenue_2025, 2) AS revenue_2025
FROM coverage
WHERE units_sold_2025 >= 500
  AND months_of_stock < 1
ORDER BY months_of_stock, units_sold_2025 DESC;


-- Potential excess inventory
-- screening rule: at least 24 units sold in 2025 and more than 6 months of stock.
-- this is an estimate of stock to review, not guaranteed savings
-- (zero-sales products are covered separately below)
WITH product_sales AS (
    SELECT product_id, SUM(quantity) AS units_sold_2025
    FROM sales
    WHERE order_date >= DATE '2025-01-01'
      AND order_date <  DATE '2026-01-01'
    GROUP BY product_id
),
product_stock AS (
    SELECT product_id, SUM(current_stock) AS current_stock
    FROM inventory
    GROUP BY product_id
),
excess_screen AS (
    SELECT
        p.product_id,
        st.current_stock,
        st.current_stock * p.unit_cost AS inventory_value
    FROM products p
    JOIN product_sales ps ON ps.product_id = p.product_id
    JOIN product_stock st ON st.product_id = p.product_id
    WHERE ps.units_sold_2025 >= 24
      AND st.current_stock / (ps.units_sold_2025 / 12.0) > 6
)
SELECT
    COUNT(*) AS potential_excess_skus,
    SUM(current_stock) AS potential_excess_units,
    ROUND(SUM(inventory_value), 2) AS potential_excess_inventory_value
FROM excess_screen;


-- Potential excess inventory by product (same rule as above)
WITH product_sales AS (
    SELECT product_id, SUM(quantity) AS units_sold_2025
    FROM sales
    WHERE order_date >= DATE '2025-01-01'
      AND order_date <  DATE '2026-01-01'
    GROUP BY product_id
),
product_stock AS (
    SELECT product_id, SUM(current_stock) AS current_stock
    FROM inventory
    GROUP BY product_id
)
SELECT
    p.product_id,
    p.product_name,
    p.category,
    ps.units_sold_2025,
    st.current_stock,
    ROUND(st.current_stock / (ps.units_sold_2025 / 12.0), 1) AS months_of_stock,
    ROUND(st.current_stock * p.unit_cost, 2) AS inventory_value
FROM products p
JOIN product_sales ps ON ps.product_id = p.product_id
JOIN product_stock st ON st.product_id = p.product_id
WHERE ps.units_sold_2025 >= 24
  AND st.current_stock / (ps.units_sold_2025 / 12.0) > 6
ORDER BY inventory_value DESC;


-- Products with no sales in 2025
WITH product_sales AS (
    SELECT product_id, COUNT(*) AS orders_2025
    FROM sales
    WHERE order_date >= DATE '2025-01-01'
      AND order_date <  DATE '2026-01-01'
    GROUP BY product_id
),
product_stock AS (
    SELECT
        product_id,
        COUNT(*) AS stores_stocking,
        SUM(current_stock) AS current_stock,
        ROUND(AVG(inventory_age_days) FILTER (WHERE stock_status = 'In Stock'), 0) AS avg_inventory_age_days
    FROM inventory
    GROUP BY product_id
)
SELECT
    p.product_id,
    p.product_name,
    p.category,
    COALESCE(st.stores_stocking, 0) AS stores_stocking,
    COALESCE(st.current_stock, 0) AS current_stock,
    st.avg_inventory_age_days,
    ROUND(COALESCE(st.current_stock, 0) * p.unit_cost, 2) AS inventory_value
FROM products p
LEFT JOIN product_sales ps ON ps.product_id = p.product_id
LEFT JOIN product_stock st ON st.product_id = p.product_id
WHERE ps.product_id IS NULL
ORDER BY inventory_value DESC;


-- Top 10 products by revenue
SELECT
    p.product_id,
    p.product_name,
    p.category,
    SUM(s.quantity) AS units_sold,
    ROUND(SUM(s.revenue), 2) AS revenue
FROM sales s
JOIN products p ON p.product_id = s.product_id
WHERE s.order_date >= DATE '2025-01-01'
  AND s.order_date <  DATE '2026-01-01'
GROUP BY p.product_id, p.product_name, p.category
ORDER BY revenue DESC, p.product_id
LIMIT 10;


-- Revenue by store
SELECT
    st.store_id,
    st.store_name,
    st.city,
    st.region,
    ROUND(SUM(s.revenue), 2) AS revenue,
    ROUND(100.0 * SUM(s.revenue) / SUM(SUM(s.revenue)) OVER (), 2) AS pct_of_total_revenue
FROM sales s
JOIN stores st ON st.store_id = s.store_id
WHERE s.order_date >= DATE '2025-01-01'
  AND s.order_date <  DATE '2026-01-01'
GROUP BY st.store_id, st.store_name, st.city, st.region
ORDER BY revenue DESC;


-- Regional performance
SELECT
    st.region,
    COUNT(DISTINCT st.store_id) AS stores,
    SUM(s.quantity) AS units_sold,
    ROUND(SUM(s.revenue), 2) AS revenue,
    ROUND(SUM(s.revenue) / COUNT(DISTINCT st.store_id), 2) AS revenue_per_store,
    ROUND(100.0 * SUM(s.revenue) / SUM(SUM(s.revenue)) OVER (), 2) AS pct_of_total_revenue
FROM sales s
JOIN stores st ON st.store_id = s.store_id
WHERE s.order_date >= DATE '2025-01-01'
  AND s.order_date <  DATE '2026-01-01'
GROUP BY st.region
ORDER BY revenue DESC;


-- Store performance
SELECT
    st.store_id,
    st.store_name,
    st.city,
    st.region,
    COUNT(s.order_id) AS orders,
    SUM(s.quantity) AS units_sold,
    ROUND(SUM(s.revenue), 2) AS revenue,
    ROUND(SUM(s.revenue) / COUNT(s.order_id), 2) AS avg_revenue_per_order,
    RANK() OVER (PARTITION BY st.region ORDER BY SUM(s.revenue) DESC) AS rank_in_region
FROM sales s
JOIN stores st ON st.store_id = s.store_id
WHERE s.order_date >= DATE '2025-01-01'
  AND s.order_date <  DATE '2026-01-01'
GROUP BY st.store_id, st.store_name, st.city, st.region
ORDER BY revenue DESC;
