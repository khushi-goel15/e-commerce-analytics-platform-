"""
Export aggregated datasets for Tableau consumption.

Generates:
  1. tableau_sales.csv      — daily sales by region, category, product
  2. tableau_customers.csv  — customer-level aggregated data
  3. tableau_regional.csv   — region-level metrics (for maps)
"""
import pandas as pd
import numpy as np
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
TAB_DIR = os.path.join(BASE_DIR, "data", "exports", "tableau")
os.makedirs(TAB_DIR, exist_ok=True)


def build():
    customers   = pd.read_csv(os.path.join(RAW_DIR, "customers.csv"))
    orders      = pd.read_csv(os.path.join(RAW_DIR, "orders.csv"))
    order_items = pd.read_csv(os.path.join(RAW_DIR, "order_items.csv"))
    products    = pd.read_csv(os.path.join(RAW_DIR, "products.csv"))
    returns     = pd.read_csv(os.path.join(RAW_DIR, "returns.csv"))

    orders["order_date"] = pd.to_datetime(orders["order_date"], errors="coerce")
    orders["shipping_date"] = pd.to_datetime(orders["shipping_date"], errors="coerce")

    # Fact table
    fact = order_items.merge(
        orders[["order_id", "customer_id", "order_date", "region", "payment_mode"]],
        on="order_id", how="left"
    )
    fact = fact.merge(
        products[["product_id", "category", "sub_category", "brand", "cost_price"]],
        on="product_id", how="left"
    )
    fact["revenue"] = fact["quantity"] * fact["selling_price"]
    fact["cost_total"] = fact["quantity"] * fact["cost_price"]
    fact["profit"] = fact["revenue"] - fact["cost_total"]
    fact["is_return"] = fact.set_index(["order_id", "product_id"]).index.isin(
        returns.set_index(["order_id", "product_id"]).index
    )
    fact["margin_pct"] = round(fact["profit"] / fact["revenue"] * 100, 2)
    fact["order_date"] = pd.to_datetime(fact["order_date"])
    fact["year"] = fact["order_date"].dt.year
    fact["month"] = fact["order_date"].dt.month
    fact["quarter"] = fact["order_date"].dt.quarter

    # ── 1. Sales detail (for trend, funnel, scatter) ────────────
    sales = fact[[
        "order_id", "order_date", "year", "quarter", "month",
        "region", "payment_mode", "category", "sub_category",
        "brand", "product_id", "quantity", "revenue", "profit",
        "discount", "margin_pct", "is_return",
    ]].copy()
    sales.to_csv(os.path.join(TAB_DIR, "tableau_sales.csv"), index=False)
    print(f"  tableau_sales.csv: {len(sales):,} rows")

    # ── 2. Customer profile (for heatmaps, CLV) ────────────────
    cust_agg = fact.groupby("customer_id").agg(
        total_revenue=("revenue", "sum"),
        total_profit=("profit", "sum"),
        orders=("order_id", "nunique"),
        avg_discount=("discount", "mean"),
        return_count=("is_return", "sum"),
        last_order=("order_date", "max"),
        first_order=("order_date", "min"),
    ).reset_index()

    cust_agg["clv"] = cust_agg["total_profit"]
    cust_agg["aov"] = cust_agg["total_revenue"] / cust_agg["orders"]
    cust_agg["return_rate"] = (cust_agg["return_count"] / cust_agg["orders"] * 100).round(2)
    cust_agg["customer_lifetime_days"] = (
        cust_agg["last_order"] - cust_agg["first_order"]
    ).dt.days

    cust_profile = customers.merge(cust_agg, on="customer_id", how="inner")
    cust_profile.to_csv(os.path.join(TAB_DIR, "tableau_customers.csv"), index=False)
    print(f"  tableau_customers.csv: {len(cust_profile):,} rows")

    # ── 3. Regional aggregated (for geographic heatmap) ─────────
    geo_cols = {"North": (28.6, 77.2), "South": (12.9, 77.6), "East": (22.5, 88.3), "West": (19.0, 72.8)}
    # City-level lat/lon
    city_coords = {
        "Delhi": (28.70, 77.10), "Chandigarh": (30.73, 76.78), "Lucknow": (26.85, 80.95),
        "Jaipur": (26.91, 75.79), "Dehradun": (30.32, 78.03),
        "Bangalore": (12.97, 77.59), "Chennai": (13.08, 80.27), "Hyderabad": (17.38, 78.48),
        "Kochi": (9.93, 76.27), "Coimbatore": (11.02, 76.96),
        "Kolkata": (22.57, 88.36), "Patna": (25.59, 85.14), "Bhubaneswar": (20.27, 85.82),
        "Guwahati": (26.14, 91.74), "Ranchi": (23.34, 85.31),
        "Mumbai": (19.08, 72.88), "Pune": (18.52, 73.86), "Ahmedabad": (23.02, 72.57),
        "Surat": (21.17, 72.83), "Nagpur": (21.15, 79.09),
    }

    regional = fact.groupby(["region", "category"]).agg(
        revenue=("revenue", "sum"),
        profit=("profit", "sum"),
        orders=("order_id", "nunique"),
        returns=("is_return", "sum"),
        customers=("customer_id", "nunique"),
    ).reset_index()
    regional["margin_pct"] = (regional["profit"] / regional["revenue"] * 100).round(2)
    regional["return_rate"] = (regional["returns"] / regional["orders"] * 100).round(2)

    # Add lat/lon
    regional["latitude"] = regional["region"].map({r: c[0] for r, c in geo_cols.items()})
    regional["longitude"] = regional["region"].map({r: c[1] for r, c in geo_cols.items()})

    regional.to_csv(os.path.join(TAB_DIR, "tableau_regional.csv"), index=False)
    print(f"  tableau_regional.csv: {len(regional):,} rows")

    # ── 4. Monthly trend (for storytelling) ─────────────────────
    trend = fact.groupby(fact["order_date"].dt.to_period("M")).agg(
        revenue=("revenue", "sum"),
        profit=("profit", "sum"),
        orders=("order_id", "nunique"),
        returns=("is_return", "sum"),
    ).reset_index()
    trend["order_date"] = trend["order_date"].astype(str)
    trend["margin_pct"] = (trend["profit"] / trend["revenue"] * 100).round(2)
    trend.to_csv(os.path.join(TAB_DIR, "tableau_trend.csv"), index=False)
    print(f"  tableau_trend.csv: {len(trend):,} rows")

    print(f"\nDone. Tableau exports saved to: {TAB_DIR}")


if __name__ == "__main__":
    print("Exporting Tableau datasets...")
    build()
