"""
ETL Pipeline: Extract → Transform → Load
Step 1: Extract CSV files from data/raw/
Step 2: Transform (clean, validate, calculate fields)
Step 3: Load into SQL database (via SQL dump or direct connection)
"""
import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
PROC_DIR = os.path.join(BASE_DIR, "data", "processed")
os.makedirs(PROC_DIR, exist_ok=True)


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


# ═════════════════════════════════════════════════════════════════════
# STEP 1: EXTRACT
# ═════════════════════════════════════════════════════════════════════
def extract():
    log("Extracting raw CSVs...")
    customers   = pd.read_csv(os.path.join(RAW_DIR, "customers.csv"))
    orders      = pd.read_csv(os.path.join(RAW_DIR, "orders.csv"))
    order_items = pd.read_csv(os.path.join(RAW_DIR, "order_items.csv"))
    products    = pd.read_csv(os.path.join(RAW_DIR, "products.csv"))
    returns     = pd.read_csv(os.path.join(RAW_DIR, "returns.csv"))
    log(f"  Loaded {len(customers)} customers, {len(orders)} orders, "
         f"{len(order_items)} items, {len(products)} products, {len(returns)} returns")
    return customers, orders, order_items, products, returns


# ═════════════════════════════════════════════════════════════════════
# STEP 2: TRANSFORM
# ═════════════════════════════════════════════════════════════════════
def transform(customers, orders, order_items, products, returns):
    log("Transforming data...")

    # ── Customers ────────────────────────────────────────────────
    c = customers.copy()
    c.drop_duplicates(subset="customer_id", inplace=True)
    c["age"] = c["age"].fillna(c["age"].median()).astype(int)
    c["gender"] = c["gender"].fillna("Unknown")
    c["signup_date"] = pd.to_datetime(c["signup_date"], errors="coerce")
    # fix any future dates
    c.loc[c["signup_date"] > datetime.today(), "signup_date"] = datetime.today()
    log(f"  Customers: {c.shape} | dupes removed, dates fixed")

    # ── Products ─────────────────────────────────────────────────
    p = products.copy()
    p.drop_duplicates(subset="product_id", inplace=True)
    p["cost_price"] = p["cost_price"].clip(lower=0)
    p["selling_price"] = p["selling_price"].clip(lower=0)
    # ensure cost < selling_price
    mask = p["cost_price"] >= p["selling_price"]
    p.loc[mask, "cost_price"] = p.loc[mask, "selling_price"] * 0.7
    log(f"  Products: {p.shape} | prices validated")

    # ── Orders ───────────────────────────────────────────────────
    o = orders.copy()
    o.drop_duplicates(subset="order_id", inplace=True)
    o["order_date"] = pd.to_datetime(o["order_date"], errors="coerce")
    o["shipping_date"] = pd.to_datetime(o["shipping_date"], errors="coerce")
    # fix shipping before order
    mask = o["shipping_date"] < o["order_date"]
    o.loc[mask, "shipping_date"] = o.loc[mask, "order_date"] + pd.Timedelta(days=1)
    o["region"] = o["region"].fillna("Unknown")
    o["payment_mode"] = o["payment_mode"].fillna("Unknown")
    log(f"  Orders: {o.shape} | dates fixed, missing filled")

    # ── Order Items ──────────────────────────────────────────────
    oi = order_items.copy()
    oi["quantity"] = oi["quantity"].clip(lower=1)
    oi["selling_price"] = oi["selling_price"].clip(lower=0)
    oi["discount"] = oi["discount"].clip(lower=0, upper=100)
    log(f"  Order Items: {oi.shape} | clipped negatives")

    # ── Returns ──────────────────────────────────────────────────
    r = returns.copy()
    r.drop_duplicates(subset=["order_id", "product_id"], inplace=True)
    r["return_reason"] = r["return_reason"].fillna("Not specified")
    log(f"  Returns: {r.shape} | deduplicated")

    # ── Merge into Fact Table ────────────────────────────────────
    log("  Building fact_sales...")
    fact = oi.merge(o[["order_id", "customer_id", "order_date", "shipping_date",
                        "region", "payment_mode"]], on="order_id", how="left")
    fact = fact.merge(p[["product_id", "cost_price", "category", "sub_category",
                          "brand"]], on="product_id", how="left")
    fact = fact.merge(c[["customer_id", "name", "gender", "age", "city"]],
                      on="customer_id", how="left")

    # Calculated fields
    fact["revenue"] = fact["quantity"] * fact["selling_price"]
    fact["profit"]  = (fact["quantity"] * fact["selling_price"]
                       ) - (fact["quantity"] * fact["cost_price"])
    fact["discount_impact"] = fact["discount"] * fact["revenue"] / 100

    # Mark returns
    fact["is_return"] = fact.set_index(["order_id", "product_id"]).index.isin(
        r.set_index(["order_id", "product_id"]).index
    )

    # Drop duplicate columns from merges
    dup_cols = [c for c in fact.columns if c.endswith(("_x", "_y")) and c[:-2] in fact.columns]
    # Keep _x versions, drop _y
    drop_y = [c for c in fact.columns if c.endswith("_y")]
    fact.drop(columns=drop_y, inplace=True, errors="ignore")
    # Rename _x to original
    for c in [c for c in fact.columns if c.endswith("_x")]:
        fact.rename(columns={c: c[:-2]}, inplace=True)

    # Drop duplicates
    fact.drop_duplicates(subset=["order_id", "product_id"], inplace=True)

    log(f"  Fact table: {fact.shape} rows, {fact['revenue'].sum():,.0f} total revenue")

    # ── Export transformed files ─────────────────────────────────
    c.to_csv(os.path.join(PROC_DIR, "dim_customers.csv"), index=False)
    p.to_csv(os.path.join(PROC_DIR, "dim_products.csv"), index=False)
    o.to_csv(os.path.join(PROC_DIR, "dim_orders.csv"), index=False)
    r.to_csv(os.path.join(PROC_DIR, "dim_returns.csv"), index=False)
    fact.to_csv(os.path.join(PROC_DIR, "fact_sales.csv"), index=False)
    log("  Transformed CSVs saved to data/processed/")

    return c, p, o, oi, r, fact


# ═════════════════════════════════════════════════════════════════════
# STEP 3: LOAD (generate SQL INSERT statements for direct DB loading)
# ═════════════════════════════════════════════════════════════════════
def load(fact, customers, products, returns):
    log("Generating SQL load script...")

    sql_path = os.path.join(BASE_DIR, "sql", "load_data.sql")
    with open(sql_path, "w", encoding="utf-8") as f:
        f.write("-- ═══════════════════════════════════════════════════\n")
        f.write("-- AUTO-GENERATED LOAD SCRIPT\n")
        f.write("-- ═══════════════════════════════════════════════════\n\n")
        f.write("BEGIN;\n\n")

        # dim_customers
        f.write("-- dim_customers\n")
        for _, row in customers.iterrows():
            sd = row["signup_date"]
            sd_str = sd.strftime("%Y-%m-%d") if pd.notna(sd) else "NULL"
            name = row["name"].replace("'", "''")
            f.write(
                f"INSERT INTO dim_customers VALUES ({row['customer_id']}, "
                f"'{name}', '{row['gender']}', {row['age']}, "
                f"'{row['city']}', '{row['region']}', {sd_str});\n"
            )

        f.write("\n")

        # dim_products
        f.write("-- dim_products\n")
        for _, row in products.iterrows():
            brand = row["brand"].replace("'", "''")
            f.write(
                f"INSERT INTO dim_products VALUES ({row['product_id']}, "
                f"'{row['category']}', '{row['sub_category']}', "
                f"'{brand}', {row['cost_price']}, {row['selling_price']});\n"
            )

        f.write("\n")

        # fact_sales
        f.write("-- fact_sales\n")
        chunk_size = 500
        for start in range(0, len(fact), chunk_size):
            chunk = fact.iloc[start:start + chunk_size]
            for _, row in chunk.iterrows():
                od = row["order_date"]
                sd = row["shipping_date"]
                od_str = od.strftime("%Y-%m-%d") if pd.notna(od) else "NULL"
                sd_str = sd.strftime("%Y-%m-%d") if pd.notna(sd) else "NULL"
                f.write(
                    f"INSERT INTO fact_sales (order_id, customer_id, product_id, "
                    f"date_key, quantity, selling_price, discount, cost_price, "
                    f"revenue, profit, is_return, payment_mode, order_date, shipping_date) "
                    f"VALUES ({row['order_id']}, {row['customer_id']}, "
                    f"{row['product_id']}, '{od_str}', {row['quantity']}, "
                    f"{row['selling_price']}, {row['discount']}, {row['cost_price']}, "
                    f"{row['revenue']}, {row['profit']}, "
                    f"{'TRUE' if row['is_return'] else 'FALSE'}, "
                    f"'{row['payment_mode']}', '{od_str}', '{sd_str}');\n"
                )
            f.write(f"-- loaded chunk {start}-{start + len(chunk)}\n")

        f.write("\nCOMMIT;\n")

    log(f"  SQL load script written to: {sql_path}")
    log("  Run with: psql -d ecommerce -f sql/load_data.sql")


# ═════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    log("=== ETL PIPELINE START ===")
    customers, orders, order_items, products, returns = extract()
    c, p, o, oi, r, fact = transform(customers, orders, order_items, products, returns)
    load(fact, c, p, r)
    log("=== ETL PIPELINE COMPLETE ===")
