# E-Commerce Analytics Platform

**End-to-end enterprise analytics system** — synthetic dataset generation, ETL pipeline, star-schema database, advanced SQL analysis, Python ML (KMeans segmentation, sales forecasting), Power BI dashboards, Tableau stories, and a McKinsey-grade consulting report.

```
Revenue: $17.8M  |  Profit: $4.3M  |  Margin: 24.0%  |  Customers: 2,000  |  Orders: 12,000
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  run_all.py  (Master Orchestrator)                               │
├──────────┬──────────┬──────────┬──────────┬──────────────────────┤
│  data/   │  sql/    │ scripts/ │analytics/│  power_bi/ + tableau/│
│ generate │  schema  │  ETL     │  Python  │  exports + DAX       │
├──────────┴──────────┴──────────┴──────────┴──────────────────────┤
│  ECommerce_Consulting_Report.docx  (760 KB, 12 embedded charts)  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

```bash
# Full pipeline: data → ETL → analytics → exports → report
python run_all.py

# Individual steps
python run_all.py --step=data       # generate synthetic dataset only
python run_all.py --step=etl        # clean + transform + SQL load script
python run_all.py --step=analytics  # EDA, KMeans, forecasting, insights
python run_all.py --step=powerbi    # star-schema CSV exports
python run_all.py --step=tableau    # geo + trend + customer exports
```

---

## Project Structure

```
E-COMMERCE ANALYTICS PLATFORM/
│
├── data/
│   ├── raw/              # Generated CSVs (customers, orders, order_items, products, returns)
│   ├── processed/        # Cleaned + transformed datasets (ETL output)
│   └── exports/          # Final outputs
│       ├── powerbi/      # Star-schema CSVs for Power BI import
│       ├── tableau/      # Aggregated exports (geo, trend, customer profiles)
│       └── images/       # 12 consulting-grade chart PNGs
│
├── sql/
│   ├── schema.sql              # Star schema (dimension + fact tables, indexes, MV)
│   ├── dim_date_populate.sql   # Date dimension population script
│   ├── analysis_queries.sql    # 12 advanced SQL queries (CLV, cohort, window fns, CTEs)
│   └── load_data.sql           # Auto-generated PostgreSQL INSERT script
│
├── scripts/
│   ├── generate_data.py          # S-tier synthetic data generator (Pareto, seasonality, patterns)
│   ├── etl_pipeline.py           # Extract → Transform → Load (clean, validate, merge)
│   ├── generate_charts.py        # 12 consulting-grade matplotlib/seaborn charts
│   ├── generate_consulting_report.py  # McKinsey-grade Word report with embedded charts
│   ├── export_for_powerbi.py     # Star-schema CSVs for Power BI
│   └── export_for_tableau.py     # Aggregated CSVs for Tableau
│
├── analytics/
│   └── python_analytics.py       # Full Python analytics suite
│
├── power_bi/
│   └── dax_measures.txt          # 20+ DAX measures (KPI, time intelligence, rankings)
│
├── run_all.py                    # Master orchestrator
├── ECommerce_Consulting_Report.docx  # 16-section consulting report (760 KB)
└── README.md
```

---

## Dataset Design

5 tables, **synthetically generated but behaviorally realistic**:

| Table | Rows | Key Features | Data Quality Quirks |
|-------|------|-------------|---------------------|
| `customers` | 2,000 | Pareto-skewed value scores, Indian names/cities | 15.4% missing signup dates, mixed date formats |
| `products` | 500 | 5 categories, 25 sub-categories, 25 brands, price clusters | 2% loss-leader SKUs (cost > price) |
| `orders` | 12,000 | Seasonality (Q4 +45%), regional dynamics | 0.9% future-dated orders |
| `order_items` | 25,266 | Region-aware discount logic, COD return multiplier | — |
| `returns` | 3,569 | Category-specific reason distributions | — |

### Embedded Business Patterns

- **Pareto**: Top 15% of customers weighted for 80% of revenue
- **Seasonality**: Q4 holiday surge (+45%), Diwali peak (Oct/Nov), Feb lull (−25%)
- **Regional dynamics**: West discount factor 1.3x (aggressive), South growth factor 1.25x
- **Discount erosion**: Margin drops from 42.7% (0% disc) to −6.5% (30%+)
- **COD return multiplier**: 2.2x higher return probability vs prepaid
- **Category economics**: Electronics (high revenue, high returns), Books (low revenue, low returns)

---

## ETL Pipeline

```
Extract ──→ Transform ──→ Load
   │            │              │
   │      Remove dupes     SQL INSERT
   │      Fix dates        script for
   │      Handle nulls     PostgreSQL
   │      Calculate fields
   │      Mark returns
   │
   └─→ 25,228 fact rows, $17.8M revenue
```

**Calculated fields:** `revenue`, `profit`, `discount_impact`, `is_return`, `margin_pct`

---

## Database: Star Schema

```
dim_customers ───┐
                  │
dim_products ─────┤─── fact_sales
                  │
dim_date ─────────┘
                  │
dim_region ───────┘
```

- **Materialized view**: `mv_daily_sales` pre-aggregates by date, category, brand, region
- **Indexes**: customer_id, product_id, date_key, region_id, order_id
- **12 SQL queries** include: CLV tiering, cohort retention, LEAD/LAG window functions, discount band P&L

---

## Python Analytics

### EDA & Correlation

| Insight | Value |
|---------|-------|
| Revenue-Profit correlation | 0.604 (strong positive) |
| Discount-Profit correlation | −0.010 (near zero) |
| Discount-Revenue correlation | 0.431 (moderate) |

### Customer Segmentation (RFM + KMeans)

| Segment | Count | Avg Revenue | Avg Orders | Strategy |
|---------|-------|-------------|------------|----------|
| High Value | 501 | $31,999 | 21.1 | Retain & Grow |
| At Risk | 781 | $2,271 | 1.8 | Re-engage / Win-back |

- Optimal k=2, silhouette score: 0.424
- Revenue at risk from At-Risk segment: **$1.77M**

### Sales Forecasting (Seasonal Naive)

- MAE: ~$16,719 on test set
- Next 90-day forecast: **~$2.03M**
- Weekly seasonality captured; monthly patterns need longer history

---

## Power BI Integration

**Exports:** `data/exports/powerbi/` — star-schema CSV files ready for import

**20+ DAX measures** in `power_bi/dax_measures.txt`:

```dax
Total Revenue     = SUM(fact_sales[revenue])
Profit Margin %   = DIVIDE([Total Profit], [Total Revenue], 0)
Revenue MoM %     = DIVIDE([Total Revenue] - [Revenue Prev Month], [Revenue Prev Month], 0)
CLV               = DIVIDE([Total Profit], DISTINCTCOUNT(fact_sales[customer_id]), 0)
Customer Segment  = SWITCH(TRUE(), RevenuePerCust >= 50000, "Platinum", ...)
```

**Dashboard Layout (5 pages):** Executive → Sales Analysis → Customer Analytics → Product Analytics → Returns

---

## Tableau Integration

**Exports:** `data/exports/tableau/`

| File | Rows | Purpose |
|------|------|---------|
| `tableau_sales.csv` | 25,266 | Daily sales detail for trend/funnel/scatter |
| `tableau_customers.csv` | 1,282 | Customer-level CLV, AOV, return rate |
| `tableau_regional.csv` | 20 | Region×category with lat/lon for heatmaps |
| `tableau_trend.csv` | 26 | Monthly aggregates for storytelling |

**Tableau Story:** Geographic heatmap → Trend storytelling → Product performance funnel

---

## Key Discovered Insights

| # | Insight | Metric | Revenue Impact |
|---|---------|--------|----------------|
| 1 | Pareto customer concentration | Top 20% → 80.7% revenue | ~$3.6M at risk from churn |
| 2 | Electronics margin trap | 16.1% margin on 68% revenue | $1.2M returns leakage |
| 3 | Discount death spiral | 30%+ disc → −6.5% margin | $654K profit destroyed |
| 4 | West region bleed | 18.3% margin vs 27.9% East | $1.4M forgone profit |
| 5 | COD return epidemic | 27.2% vs 12.6% prepaid | $425K annual cost |

---

## Consulting Report

The `ECommerce_Consulting_Report.docx` (760 KB) is a **16-section McKinsey-grade deliverable** with 12 embedded charts:

1. Executive Summary (5 insights, metric/comparison/action format)
2. Business Problem Statement
3. Dataset Overview
4. KPI Framework (current vs target)
5. Exploratory Data Analysis (insight-driven)
6. Advanced Analytics (KMeans + forecasting)
7. Model Performance
8. Explainability & Key Drivers (correlation narrative)
9. Segmentation Analysis (customer/product/region)
10. SQL Analytics (4 high-impact queries)
11. Key Business Insights (8 insights with risk quantification)
12. Strategic Recommendations (8 initiatives, HIGH/MEDIUM/LOW)
13. ROI & Financial Impact ($2.8M year-1 net)
14. Deployment Roadmap (3 phases)
15. Limitations & Future Work
16. Conclusion

---

## Requirements

- Python 3.10+
- `pandas`, `numpy`, `scikit-learn`, `statsmodels`
- `python-docx`, `matplotlib`, `seaborn`
- (Optional) PostgreSQL for SQL queries

---

## License

MIT — built as a portfolio / learning project.
