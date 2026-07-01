"""
Export datasets optimized for Power BI consumption.
Run this after ETL pipeline to generate clean .csv files for Power BI import.

Usage:
  python scripts/export_for_powerbi.py

Import into Power BI:
  1. Get Data → Folder → point to data/exports/powerbi/
  2. Create relationships (Star Schema)
  3. Create DAX measures (see below)
"""
import pandas as pd
import numpy as np
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
PBI_DIR = os.path.join(BASE_DIR, "data", "exports", "powerbi")
os.makedirs(PBI_DIR, exist_ok=True)


def load_and_build():
    customers   = pd.read_csv(os.path.join(RAW_DIR, "customers.csv"))
    orders      = pd.read_csv(os.path.join(RAW_DIR, "orders.csv"))
    order_items = pd.read_csv(os.path.join(RAW_DIR, "order_items.csv"))
    products    = pd.read_csv(os.path.join(RAW_DIR, "products.csv"))
    returns     = pd.read_csv(os.path.join(RAW_DIR, "returns.csv"))

    orders["order_date"]    = pd.to_datetime(orders["order_date"], errors="coerce")
    orders["shipping_date"] = pd.to_datetime(orders["shipping_date"], errors="coerce")

    # ── Dim Date ────────────────────────────────────────────────
    dates = pd.date_range(
        orders["order_date"].min(),
        max(orders["order_date"].max(), orders["shipping_date"].max()),
        freq="D"
    )
    dim_date = pd.DataFrame({
        "Date": dates,
        "Year": dates.year,
        "Quarter": dates.quarter,
        "Month": dates.month,
        "MonthName": dates.strftime("%b"),
        "Week": dates.isocalendar().week.astype(int),
        "DayOfWeek": dates.dayofweek,
        "DayName": dates.strftime("%A"),
        "IsWeekend": dates.dayofweek >= 5,
    })
    dim_date["MonthYear"] = dim_date["Date"].dt.strftime("%Y-%m")
    dim_date["QuarterLabel"] = "Q" + dim_date["Quarter"].astype(str) + " " + dim_date["Year"].astype(str)
    dim_date.to_csv(os.path.join(PBI_DIR, "dim_date.csv"), index=False)
    print(f"  dim_date: {len(dim_date)} rows")

    # ── Dim Customers ──────────────────────────────────────────
    dim_customer = customers.copy()
    dim_customer["signup_date"] = pd.to_datetime(dim_customer["signup_date"], errors="coerce")
    dim_customer["signup_date"] = dim_customer["signup_date"].dt.strftime("%Y-%m-%d")
    dim_customer.to_csv(os.path.join(PBI_DIR, "dim_customers.csv"), index=False)
    print(f"  dim_customers: {len(dim_customer)} rows")

    # ── Dim Products ──────────────────────────────────────────────
    dim_product = products.copy()
    dim_product["unit_margin_pct"] = round(
        (dim_product["selling_price"] - dim_product["cost_price"])
        / dim_product["selling_price"] * 100, 2
    )
    dim_product.to_csv(os.path.join(PBI_DIR, "dim_products.csv"), index=False)
    print(f"  dim_products: {len(dim_product)} rows")

    # ── Fact Sales ─────────────────────────────────────────────
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
    fact["discount_impact"] = fact["discount"] * fact["revenue"] / 100
    fact["is_return"] = fact.set_index(["order_id", "product_id"]).index.isin(
        returns.set_index(["order_id", "product_id"]).index
    )
    fact["margin_pct"] = round(fact["profit"] / fact["revenue"] * 100, 2)
    fact["order_date"] = pd.to_datetime(fact["order_date"])

    fact.to_csv(os.path.join(PBI_DIR, "fact_sales.csv"), index=False)
    print(f"  fact_sales: {len(fact)} rows")

    returns.to_csv(os.path.join(PBI_DIR, "returns.csv"), index=False)
    print(f"  returns: {len(returns)} rows")
    print(f"\nDone. Exports saved to: {PBI_DIR}")


if __name__ == "__main__":
    print("Exporting Power BI datasets...")
    load_and_build()
