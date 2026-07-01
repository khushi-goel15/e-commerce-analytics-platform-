-- ═══════════════════════════════════════════════════════════════════
-- E-COMMERCE ANALYTICS PLATFORM — Star Schema
-- Target: PostgreSQL / MySQL
-- ═══════════════════════════════════════════════════════════════════

-- ── 1. DIMENSION TABLES ──────────────────────────────────────────

CREATE TABLE dim_customers (
    customer_id     INT PRIMARY KEY,
    name            VARCHAR(100),
    gender          VARCHAR(10),
    age             INT,
    city            VARCHAR(50),
    region          VARCHAR(20),
    signup_date     DATE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE dim_products (
    product_id      INT PRIMARY KEY,
    category        VARCHAR(50),
    sub_category    VARCHAR(50),
    brand           VARCHAR(50),
    cost_price      NUMERIC(10,2),
    selling_price   NUMERIC(10,2),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE dim_date (
    date_key        DATE PRIMARY KEY,
    year            INT,
    quarter         INT,
    month           INT,
    month_name      VARCHAR(20),
    week            INT,
    day_of_week     INT,
    day_name        VARCHAR(20),
    is_weekend      BOOLEAN
);

CREATE TABLE dim_region (
    region_id       SERIAL PRIMARY KEY,
    region          VARCHAR(50),
    city            VARCHAR(50),
    state           VARCHAR(50),
    zone            VARCHAR(20)
);

-- ── 2. FACT TABLE ───────────────────────────────────────────────

CREATE TABLE fact_sales (
    sale_id         BIGSERIAL PRIMARY KEY,
    order_id        INT NOT NULL,
    customer_id     INT NOT NULL REFERENCES dim_customers(customer_id),
    product_id      INT NOT NULL REFERENCES dim_products(product_id),
    date_key        DATE NOT NULL REFERENCES dim_date(date_key),
    region_id       INT REFERENCES dim_region(region_id),
    quantity        INT NOT NULL,
    selling_price   NUMERIC(10,2) NOT NULL,
    discount        NUMERIC(5,2) DEFAULT 0,
    cost_price      NUMERIC(10,2),
    revenue         NUMERIC(12,2) GENERATED ALWAYS AS (quantity * selling_price) STORED,
    profit          NUMERIC(12,2) GENERATED ALWAYS AS ((quantity * selling_price) - (quantity * cost_price)) STORED,
    is_return       BOOLEAN DEFAULT FALSE,
    payment_mode    VARCHAR(30),
    order_date      DATE,
    shipping_date   DATE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ── 3. INDEXES ──────────────────────────────────────────────────

CREATE INDEX idx_fact_sales_customer ON fact_sales(customer_id);
CREATE INDEX idx_fact_sales_product  ON fact_sales(product_id);
CREATE INDEX idx_fact_sales_date     ON fact_sales(date_key);
CREATE INDEX idx_fact_sales_region   ON fact_sales(region_id);
CREATE INDEX idx_fact_sales_order    ON fact_sales(order_id);

-- ── 4. MATERIALIZED VIEW — Daily Aggregates ────────────────────

CREATE MATERIALIZED VIEW mv_daily_sales AS
SELECT
    fs.date_key,
    dp.category,
    dp.sub_category,
    dp.brand,
    dc.region,
    COUNT(DISTINCT fs.order_id)              AS orders,
    COUNT(DISTINCT fs.customer_id)           AS customers,
    SUM(fs.quantity)                         AS units_sold,
    SUM(fs.revenue)                          AS revenue,
    SUM(fs.profit)                           AS profit,
    SUM(fs.quantity * fs.cost_price)         AS total_cost,
    ROUND(
        SUM(fs.profit) * 100.0 / NULLIF(SUM(fs.revenue), 0), 2
    )                                        AS profit_margin_pct,
    SUM(CASE WHEN fs.is_return THEN 1 ELSE 0 END) AS returns_count
FROM fact_sales fs
JOIN dim_products dp  ON fs.product_id  = dp.product_id
JOIN dim_customers dc ON fs.customer_id = dc.customer_id
GROUP BY fs.date_key, dp.category, dp.sub_category, dp.brand, dc.region;

-- ── 5. STAGING TABLES (for ETL landing) ────────────────────────

CREATE TABLE stage_customers (
    customer_id INT,
    name        VARCHAR(100),
    gender      VARCHAR(10),
    age         INT,
    city        VARCHAR(50),
    region      VARCHAR(20),
    signup_date VARCHAR(20)
);

CREATE TABLE stage_orders (
    order_id      INT,
    customer_id   INT,
    order_date    VARCHAR(20),
    shipping_date VARCHAR(20),
    region        VARCHAR(20),
    payment_mode  VARCHAR(30)
);

CREATE TABLE stage_order_items (
    order_id      INT,
    product_id    INT,
    quantity      INT,
    selling_price NUMERIC(10,2),
    discount      NUMERIC(5,2)
);

CREATE TABLE stage_products (
    product_id    INT,
    category      VARCHAR(50),
    sub_category  VARCHAR(50),
    brand         VARCHAR(50),
    cost_price    NUMERIC(10,2),
    selling_price NUMERIC(10,2)
);

CREATE TABLE stage_returns (
    order_id      INT,
    product_id    INT,
    return_reason VARCHAR(200)
);
