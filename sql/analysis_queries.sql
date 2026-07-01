-- ═══════════════════════════════════════════════════════════════════
-- ADVANCED SQL ANALYSIS — E-Commerce Analytics Platform
-- ═══════════════════════════════════════════════════════════════════

-- ── 1. REVENUE BY REGION ─────────────────────────────────────────
SELECT
    dc.region,
    COUNT(DISTINCT fs.order_id)            AS total_orders,
    SUM(fs.revenue)                         AS total_revenue,
    SUM(fs.profit)                          AS total_profit,
    ROUND((SUM(fs.profit) * 100.0 / NULLIF(SUM(fs.revenue), 0)), 2) AS margin_pct,
    ROUND(AVG(fs.revenue), 2)               AS avg_order_value
FROM fact_sales fs
JOIN dim_customers dc ON fs.customer_id = dc.customer_id
GROUP BY dc.region
ORDER BY total_revenue DESC;

-- ── 2. MONTHLY SALES TREND ───────────────────────────────────────
SELECT
    dd.year,
    dd.month,
    dd.month_name,
    COUNT(DISTINCT fs.order_id)            AS orders,
    SUM(fs.revenue)                         AS revenue,
    SUM(fs.profit)                          AS profit,
    ROUND((SUM(fs.profit) * 100.0 / NULLIF(SUM(fs.revenue), 0)), 2) AS margin_pct,
    LAG(SUM(fs.revenue)) OVER (ORDER BY dd.year, dd.month) AS prev_month_revenue,
    ROUND(
        (SUM(fs.revenue) - LAG(SUM(fs.revenue)) OVER (ORDER BY dd.year, dd.month))
        * 100.0 / NULLIF(LAG(SUM(fs.revenue)) OVER (ORDER BY dd.year, dd.month), 0), 2
    ) AS revenue_mom_change_pct
FROM fact_sales fs
JOIN dim_date dd ON fs.date_key = dd.date_key
GROUP BY dd.year, dd.month, dd.month_name
ORDER BY dd.year, dd.month;

-- ── 3. TOP 10 PRODUCTS BY PROFIT ─────────────────────────────────
SELECT
    dp.product_id,
    dp.category,
    dp.sub_category,
    dp.brand,
    SUM(fs.quantity)                        AS units_sold,
    SUM(fs.revenue)                         AS total_revenue,
    SUM(fs.profit)                          AS total_profit,
    ROUND(AVG(fs.profit * 1.0 / NULLIF(fs.revenue, 0)) * 100, 2) AS avg_margin_pct,
    RANK() OVER (ORDER BY SUM(fs.profit) DESC) AS profit_rank
FROM fact_sales fs
JOIN dim_products dp ON fs.product_id = dp.product_id
GROUP BY dp.product_id, dp.category, dp.sub_category, dp.brand
ORDER BY total_profit DESC
LIMIT 10;

-- ── 4. CUSTOMER LIFETIME VALUE (CLV) ─────────────────────────────
WITH customer_metrics AS (
    SELECT
        fs.customer_id,
        dc.name,
        dc.region,
        COUNT(DISTINCT fs.order_id)            AS total_orders,
        SUM(fs.revenue)                         AS total_revenue,
        SUM(fs.profit)                          AS total_profit,
        MIN(fs.order_date)                      AS first_order,
        MAX(fs.order_date)                      AS last_order,
        (MAX(fs.order_date) - MIN(fs.order_date)) AS customer_lifetime_days
    FROM fact_sales fs
    JOIN dim_customers dc ON fs.customer_id = dc.customer_id
    GROUP BY fs.customer_id, dc.name, dc.region
)
SELECT
    customer_id,
    name,
    region,
    total_orders,
    ROUND(total_revenue, 2)                    AS total_revenue,
    ROUND(total_profit, 2)                     AS total_profit,
    ROUND(total_revenue / NULLIF(total_orders, 0), 2) AS aov,
    CASE
        WHEN customer_lifetime_days = 0 THEN total_revenue
        ELSE ROUND(total_revenue * 365.0 / customer_lifetime_days, 2)
    END                                         AS annual_value,
    CASE
        WHEN total_orders >= 5 THEN 'Platinum'
        WHEN total_orders >= 3 THEN 'Gold'
        WHEN total_orders >= 2 THEN 'Silver'
        ELSE 'Bronze'
    END                                         AS customer_tier,
    CASE
        WHEN total_revenue >= 50000 THEN 'High'
        WHEN total_revenue >= 10000 THEN 'Medium'
        ELSE 'Low'
    END                                         AS value_segment,
    ROUND(total_revenue * 1.0 / NULLIF(total_orders, 0), 2) AS avg_revenue_per_order
FROM customer_metrics
ORDER BY total_revenue DESC
LIMIT 20;

-- ── 5. REPEAT PURCHASE RATE ─────────────────────────────────────
WITH order_counts AS (
    SELECT
        customer_id,
        COUNT(DISTINCT order_id) AS order_count
    FROM fact_sales
    GROUP BY customer_id
)
SELECT
    CASE
        WHEN order_count = 1 THEN '1 order'
        WHEN order_count = 2 THEN '2 orders'
        WHEN order_count BETWEEN 3 AND 4 THEN '3-4 orders'
        WHEN order_count BETWEEN 5 AND 9 THEN '5-9 orders'
        ELSE '10+ orders'
    END                             AS order_frequency,
    COUNT(*)                         AS customer_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS pct_of_customers,
    ROUND(
        SUM(COUNT(*)) OVER (ORDER BY MAX(order_count) DESC), 2
    ) AS cumulative_customers_desc
FROM order_counts
GROUP BY order_frequency
ORDER BY MIN(order_count);

-- ── 6. RETURN RATE BY CATEGORY ──────────────────────────────────
SELECT
    dp.category,
    COUNT(DISTINCT fs.order_id)                     AS total_orders,
    SUM(fs.quantity)                                AS units_sold,
    SUM(CASE WHEN fs.is_return THEN 1 ELSE 0 END)   AS return_units,
    ROUND(
        SUM(CASE WHEN fs.is_return THEN 1 ELSE 0 END) * 100.0
        / NULLIF(SUM(fs.quantity), 0), 2
    )                                               AS return_rate_pct,
    SUM(CASE WHEN fs.is_return THEN fs.revenue ELSE 0 END) AS return_revenue_loss
FROM fact_sales fs
JOIN dim_products dp ON fs.product_id = dp.product_id
GROUP BY dp.category
ORDER BY return_rate_pct DESC;

-- ── 7. PROFIT MARGIN BY PRODUCT ─────────────────────────────────
SELECT
    dp.product_id,
    dp.category,
    dp.sub_category,
    dp.brand,
    dp.cost_price,
    dp.selling_price,
    ROUND((dp.selling_price - dp.cost_price) * 100.0 / dp.selling_price, 2) AS unit_margin_pct,
    SUM(fs.quantity)                        AS units_sold,
    SUM(fs.revenue)                         AS total_revenue,
    SUM(fs.profit)                          AS total_profit,
    ROUND(SUM(fs.profit) * 100.0 / NULLIF(SUM(fs.revenue), 0), 2) AS realized_margin_pct
FROM fact_sales fs
JOIN dim_products dp ON fs.product_id = dp.product_id
GROUP BY dp.product_id, dp.category, dp.sub_category, dp.brand,
         dp.cost_price, dp.selling_price
HAVING SUM(fs.revenue) > 0
ORDER BY realized_margin_pct ASC
LIMIT 20;

-- ── 8. COHORT ANALYSIS ──────────────────────────────────────────
WITH customer_first_order AS (
    SELECT
        customer_id,
        MIN(order_date) AS first_order_date,
        TO_CHAR(MIN(order_date), 'YYYY-MM') AS cohort_month
    FROM fact_sales
    GROUP BY customer_id
),
monthly_activity AS (
    SELECT
        cfo.customer_id,
        cfo.cohort_month,
        TO_CHAR(fs.order_date, 'YYYY-MM') AS activity_month,
        EXTRACT(YEAR FROM AGE(fs.order_date, cfo.first_order_date)) * 12
        + EXTRACT(MONTH FROM AGE(fs.order_date, cfo.first_order_date)) AS month_offset
    FROM fact_sales fs
    JOIN customer_first_order cfo ON fs.customer_id = cfo.customer_id
),
cohort_size AS (
    SELECT
        cohort_month,
        COUNT(DISTINCT customer_id) AS size
    FROM customer_first_order
    GROUP BY cohort_month
),
cohort_retention AS (
    SELECT
        ma.cohort_month,
        ma.month_offset,
        COUNT(DISTINCT ma.customer_id) AS active_customers,
        cs.size AS cohort_size
    FROM monthly_activity ma
    JOIN cohort_size cs ON ma.cohort_month = cs.cohort_month
    GROUP BY ma.cohort_month, ma.month_offset, cs.size
)
SELECT
    cohort_month,
    month_offset,
    active_customers,
    cohort_size,
    ROUND(active_customers * 100.0 / cohort_size, 2) AS retention_pct
FROM cohort_retention
WHERE month_offset <= 12
ORDER BY cohort_month, month_offset;

-- ── 9. WINDOW FUNCTIONS — LEAD customers next purchase ──────────
SELECT
    fs.customer_id,
    dc.name,
    fs.order_id,
    fs.order_date,
    LEAD(fs.order_date) OVER (
        PARTITION BY fs.customer_id ORDER BY fs.order_date
    ) AS next_order_date,
    ROUND(
        LEAD(fs.order_date) OVER (PARTITION BY fs.customer_id ORDER BY fs.order_date)
        - fs.order_date
    ) AS days_between_orders,
    SUM(fs.revenue) OVER (
        PARTITION BY fs.customer_id ORDER BY fs.order_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS running_total_revenue
FROM fact_sales fs
JOIN dim_customers dc ON fs.customer_id = dc.customer_id
ORDER BY fs.customer_id, fs.order_date
LIMIT 50;

-- ── 10. DISCOUNT IMPACT ANALYSIS ─────────────────────────────────
SELECT
    CASE
        WHEN fs.discount = 0 THEN '0%'
        WHEN fs.discount BETWEEN 1 AND 10 THEN '1-10%'
        WHEN fs.discount BETWEEN 11 AND 20 THEN '11-20%'
        WHEN fs.discount BETWEEN 21 AND 30 THEN '21-30%'
        ELSE '30%+'
    END AS discount_band,
    COUNT(*) AS transactions,
    SUM(fs.revenue) AS total_revenue,
    SUM(fs.profit) AS total_profit,
    ROUND(SUM(fs.profit) * 100.0 / NULLIF(SUM(fs.revenue), 0), 2) AS margin_pct,
    ROUND(AVG(fs.discount), 2) AS avg_discount_pct
FROM fact_sales fs
GROUP BY discount_band
ORDER BY MIN(fs.discount);

-- ── 11. PAYMENT MODE ANALYSIS ────────────────────────────────────
SELECT
    fs.payment_mode,
    COUNT(DISTINCT fs.order_id) AS orders,
    SUM(fs.revenue) AS revenue,
    SUM(fs.profit) AS profit,
    ROUND(AVG(fs.revenue), 2) AS avg_order_value,
    COUNT(*) AS transactions
FROM fact_sales fs
GROUP BY fs.payment_mode
ORDER BY revenue DESC;

-- ── 12. TOP 10 LOSS-MAKING PRODUCTS ──────────────────────────────
SELECT
    dp.product_id,
    dp.category,
    dp.sub_category,
    dp.brand,
    SUM(fs.quantity) AS units_sold,
    SUM(fs.revenue) AS total_revenue,
    SUM(fs.profit) AS total_profit
FROM fact_sales fs
JOIN dim_products dp ON fs.product_id = dp.product_id
GROUP BY dp.product_id, dp.category, dp.sub_category, dp.brand
ORDER BY total_profit ASC
LIMIT 10;
