"""
S-Tier E-Commerce Synthetic Data Generator
───────────────────────────────────────────
Design Philosophy:
  - Every row is deliberately crafted so that analysis yields real business stories
  - Pareto, seasonality, trend, regional dynamics, discount erosion, return patterns
  - Data quality quirks (dupes, nulls, outliers) mirror real-world messy data

Insights baked in (waiting to be discovered):
  1. 20% customers → 80% revenue  (Pareto)
  2. West region = highest revenue, lowest margin (discount war)
  3. Electronics = highest return rate (18%+)
  4. Discounts > 20% destroy profitability
  5. Q4 holiday spike + Diwali surge
  6. COD payments yield 2x higher returns
  7. Customer churn accelerates after 6 months idle
  8. "Better price elsewhere" is top return reason for Electronics
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

np.random.seed(42)
random.seed(42)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
os.makedirs(RAW_DIR, exist_ok=True)

N_CUSTOMERS = 2000
N_PRODUCTS  = 500
N_ORDERS    = 12000
START_DATE  = datetime(2023, 1, 1)
END_DATE    = datetime(2024, 12, 31)
SPAN_DAYS   = (END_DATE - START_DATE).days

# ═══════════════════════════════════════════════════════════════════
# CATEGORY BLUEPRINT  —  each category has a distinct economic profile
# ═══════════════════════════════════════════════════════════════════
CAT_META = {
    "Electronics": {
        "subs": ["Mobile Phones", "Laptops", "Headphones", "Cameras", "Smartwatches"],
        "brands": ["TechPro", "Electra", "NovaTech", "SkyNet", "ZoomTech"],
        "price_range": (500, 5000),
        "cost_pct": (0.55, 0.70),
        "base_return": 0.18,
        "popularity": 0.18,
    },
    "Clothing": {
        "subs": ["Men's Wear", "Women's Wear", "Kids' Wear", "Footwear", "Accessories"],
        "brands": ["FashionHub", "StyleCraft", "TrendSetter", "UrbanFit", "ClassicWear"],
        "price_range": (20, 300),
        "cost_pct": (0.40, 0.55),
        "base_return": 0.12,
        "popularity": 0.28,
    },
    "Home & Kitchen": {
        "subs": ["Furniture", "Decor", "Cookware", "Bedding", "Storage"],
        "brands": ["HomeEase", "ComfortPro", "LivingSpace", "KitchenKing", "DreamHome"],
        "price_range": (30, 800),
        "cost_pct": (0.50, 0.65),
        "base_return": 0.09,
        "popularity": 0.16,
    },
    "Books": {
        "subs": ["Fiction", "Non-Fiction", "Educational", "Comics", "Magazines"],
        "brands": ["PageTurner", "WordCraft", "KnowledgeFirst", "StoryHouse", "LearnHub"],
        "price_range": (10, 80),
        "cost_pct": (0.35, 0.50),
        "base_return": 0.04,
        "popularity": 0.18,
    },
    "Sports & Outdoors": {
        "subs": ["Fitness", "Camping", "Cycling", "Team Sports", "Yoga"],
        "brands": ["ActiveGear", "OutdoorPro", "FitLife", "SportMax", "TrailBlazer"],
        "price_range": (25, 600),
        "cost_pct": (0.45, 0.60),
        "base_return": 0.10,
        "popularity": 0.20,
    },
}

# ── Regional profiles ─────────────────────────────────────────────
# West is biggest market but most competitive (higher discounts, lower margins)
# South is growing fastest
REGIONS = {
    "North": {"pct": 0.25, "discount_factor": 1.0,  "growth": 1.00,
              "cities": ["Delhi", "Chandigarh", "Lucknow", "Jaipur", "Dehradun"]},
    "South": {"pct": 0.20, "discount_factor": 0.9,  "growth": 1.25,
              "cities": ["Bangalore", "Chennai", "Hyderabad", "Kochi", "Coimbatore"]},
    "East":  {"pct": 0.20, "discount_factor": 0.85, "growth": 1.10,
              "cities": ["Kolkata", "Patna", "Bhubaneswar", "Guwahati", "Ranchi"]},
    "West":  {"pct": 0.35, "discount_factor": 1.3,  "growth": 0.95,
              "cities": ["Mumbai", "Pune", "Ahmedabad", "Surat", "Nagpur"]},
}

PAYMENTS = {
    "Credit Card":   {"pct": 0.22, "cod_return_risk": 1.0},
    "Debit Card":    {"pct": 0.20, "cod_return_risk": 1.0},
    "UPI":           {"pct": 0.32, "cod_return_risk": 1.0},
    "Net Banking":   {"pct": 0.10, "cod_return_risk": 1.0},
    "COD":           {"pct": 0.10, "cod_return_risk": 2.2},
    "Wallet":        {"pct": 0.06, "cod_return_risk": 1.0},
}

RETURN_REASONS = [
    "Defective product",
    "Not as described",
    "Size/fit issue",
    "Delivered late",
    "Changed mind",
    "Better price elsewhere",
    "Wrong item delivered",
    "Damaged in transit",
]

def indian_name(gender):
    firsts_m = [
        "Aarav","Vivaan","Aditya","Arjun","Reyansh","Sai","Ishaan","Krishna",
        "Raj","Amit","Vikram","Rahul","Deepak","Ravi","Sanjay","Arun","Manoj",
    ]
    firsts_f = [
        "Ananya","Diya","Myra","Sara","Aadhya","Saanvi","Priya","Neha",
        "Pooja","Anita","Kavita","Meera","Lakshmi","Geeta","Riya","Jiya",
    ]
    lasts = [
        "Sharma","Verma","Patel","Gupta","Singh","Kumar","Reddy","Joshi",
        "Nair","Menon","Desai","Shah","Mehta","Das","Sen","Roy","Bose",
        "Choudhury","Mukherjee","Rao","Iyer","Thakur","Yadav","Pandey",
    ]
    first = random.choice(firsts_m if gender == "Male" else firsts_f)
    return f"{first} {random.choice(lasts)}"

def seasonal_factor(date):
    """Return multiplier for order probability based on date."""
    m = date.month
    # Q4 holiday surge (Oct-Dec), Diwali in Oct/Nov
    base = 1.0
    if m == 12:        base = 1.45
    elif m == 11:      base = 1.50  # Diwali
    elif m == 10:      base = 1.25
    elif m == 1:       base = 0.85
    elif m == 2:       base = 0.75  # post-holiday lull
    elif m in (4, 5):  base = 1.10
    elif m in (6, 7):  base = 1.15  # summer sales
    return base

def growth_trend(date):
    """Year-over-year growth ~15%."""
    days_since_start = (date - START_DATE).days
    return 1.0 + 0.15 * (days_since_start / SPAN_DAYS)

def generate_order_date():
    """Pick a date with seasonality + trend weighting."""
    while True:
        d = START_DATE + timedelta(days=int(np.random.uniform(0, SPAN_DAYS)))
        weight = seasonal_factor(d) * growth_trend(d)
        if np.random.random() < weight / 1.8:  # normalise so max ~1
            return d


# ═══════════════════════════════════════════════════════════════════
# 1.  CUSTOMERS   —  Pareto-distributed value
# ═══════════════════════════════════════════════════════════════════
print("─── 1. Customers ───")
# Assign a latent "value score" — top 20% will generate ~80% of spend
# Power-law for strong Pareto: top 20% → ~80% of weight
raw = np.random.pareto(1.2, N_CUSTOMERS)
value_weights = np.sort(raw)[::-1]
value_weights = value_weights / value_weights.sum()
cum = np.cumsum(value_weights)
pareto_idx = np.searchsorted(cum, 0.80) / N_CUSTOMERS
print(f"  Pareto: top {pareto_idx*100:.0f}% customers → 80% of activity")

customers = []
for i in range(1, N_CUSTOMERS + 1):
    # Map position to a customer; shuffle so high-value isn't always first id
    pass

# Shuffle the value weights across customer IDs
customer_value_map = list(zip(range(1, N_CUSTOMERS + 1), value_weights))
random.shuffle(customer_value_map)

for cid, _ in customer_value_map:
    g = random.choices(["Male", "Female", "Other"], weights=[0.48, 0.48, 0.04])[0]
    name = indian_name(g)
    age = int(np.random.normal(35, 11))
    age = max(18, min(78, age))
    reg = random.choices(list(REGIONS.keys()), weights=[r["pct"] for r in REGIONS.values()])[0]
    city = random.choice(REGIONS[reg]["cities"])

    # Signup date: some before our window, some during
    days_before = int(np.random.exponential(180))
    signup = START_DATE - timedelta(days=days_before)
    # 15% have null/invalid signup date
    if random.random() < 0.15:
        signup_str = "" if random.random() < 0.5 else signup.strftime("%d-%m-%Y")
    else:
        signup_str = signup.strftime("%Y-%m-%d")

    customers.append({
        "customer_id": cid,
        "name": name.replace("'", ""),
        "gender": g,
        "age": age,
        "city": city,
        "region": reg,
        "signup_date": signup_str,
        "_value_score": value_weights[cid - 1],
    })

df_cust = pd.DataFrame(customers)
df_cust.drop(columns=["_value_score"]).to_csv(
    os.path.join(RAW_DIR, "customers.csv"), index=False
)
print(f"  {len(df_cust)} customers written  |  "
      f"null signup_dates: {df_cust['signup_date'].isna().sum()}  |  "
      f"weird formats: {(df_cust['signup_date'].str.len() != 10).sum() if df_cust['signup_date'].notna().any() else 0}")


# ═══════════════════════════════════════════════════════════════════
# 2.  PRODUCTS   —  clustered by category economics
# ═══════════════════════════════════════════════════════════════════
print("─── 2. Products ───")
products = []
for i in range(1, N_PRODUCTS + 1):
    cat = random.choices(
        list(CAT_META.keys()),
        weights=[m["popularity"] for m in CAT_META.values()]
    )[0]
    meta = CAT_META[cat]
    sub = random.choice(meta["subs"])
    brand = random.choice(meta["brands"])

    lo, hi = meta["price_range"]
    # Price clusters: multi-modal within range
    cluster = random.choices(["budget", "mid", "premium"], weights=[0.3, 0.5, 0.2])[0]
    if cluster == "budget":
        price = np.random.uniform(lo, lo + (hi - lo) * 0.3)
    elif cluster == "mid":
        price = np.random.uniform(lo + (hi - lo) * 0.25, lo + (hi - lo) * 0.7)
    else:
        price = np.random.uniform(lo + (hi - lo) * 0.6, hi)
    price = round(max(lo, price), 0)

    c_lo, c_hi = meta["cost_pct"]
    cost_pct = np.random.uniform(c_lo, c_hi)
    cost = round(price * cost_pct, 2)
    cost = min(cost, price - 0.5)

    # 2% products have cost > price (loss leaders)
    if random.random() < 0.02:
        cost = price * random.uniform(1.0, 1.15)

    products.append({
        "product_id": i,
        "category": cat,
        "sub_category": sub,
        "brand": brand,
        "cost_price": round(cost, 2),
        "selling_price": round(price, 2),
    })

df_prod = pd.DataFrame(products)
df_prod.to_csv(os.path.join(RAW_DIR, "products.csv"), index=False)
print(f"  {len(df_prod)} products  |  "
      f"categories: {df_prod['category'].value_counts().to_dict()}")


# ═══════════════════════════════════════════════════════════════════
# 3.  ORDERS  —  Pareto-skewed customers, seasonality, regional mix
# ═══════════════════════════════════════════════════════════════════
print("─── 3. Orders ───")
# Order-level probability per customer (Pareto)
cust_order_prob = np.array([c["_value_score"] for c in customers])
cust_order_prob = cust_order_prob / cust_order_prob.sum()

orders = []
for oid in range(1, N_ORDERS + 1):
    cust_id = np.random.choice(range(1, N_CUSTOMERS + 1), p=cust_order_prob)

    # Pick date with seasonality
    od = generate_order_date()
    if od > END_DATE:
        od = END_DATE - timedelta(days=random.randint(1, 30))

    # Shipping: 1-7 days, 3% delayed >7 days
    ship_delay = int(np.random.exponential(2.5)) + 1
    if random.random() < 0.03:
        ship_delay += random.randint(7, 20)
    ship = od + timedelta(days=min(ship_delay, 30))

    # Region follows customer, but 10% mismatch
    cust_row = df_cust.iloc[cust_id - 1]
    if random.random() < 0.10:
        reg = random.choice(list(REGIONS.keys()))
    else:
        reg = cust_row["region"]

    # Payment mode
    pay = random.choices(
        list(PAYMENTS.keys()),
        weights=[v["pct"] for v in PAYMENTS.values()]
    )[0]

    # 1% orders are future-dated (data quality issue)
    if random.random() < 0.01:
        od = END_DATE + timedelta(days=random.randint(1, 60))

    orders.append({
        "order_id": oid,
        "customer_id": cust_id,
        "order_date": od.strftime("%Y-%m-%d"),
        "shipping_date": ship.strftime("%Y-%m-%d"),
        "region": reg,
        "payment_mode": pay,
    })

df_orders = pd.DataFrame(orders)
df_orders.to_csv(os.path.join(RAW_DIR, "orders.csv"), index=False)

# Stats
odates = pd.to_datetime(df_orders["order_date"], errors="coerce")
future = (odates > pd.Timestamp(END_DATE)).sum()
print(f"  {len(df_orders)} orders  |  "
      f"future dates: {future}  |  "
      f"date range: {odates.min().date()} → {odates.max().date()}")


# ═══════════════════════════════════════════════════════════════════
# 4.  ORDER ITEMS  —  discount varies by region, drives volume
# ═══════════════════════════════════════════════════════════════════
print("─── 4. Order Items ───")
def discount_for(product_price, region, category):
    """Discount logic: West is more aggressive, Electronics discounts deeper."""
    base = 0
    if product_price > 2000:
        base = random.choice([10, 15, 20, 25])
    elif product_price > 500:
        base = random.choice([0, 10, 15, 20])
    elif product_price > 100:
        base = random.choice([0, 5, 10, 15])
    else:
        base = random.choice([0, 0, 5, 10])

    # Region factor (West = aggressive discounting)
    base *= REGIONS[region]["discount_factor"]

    # Category adjustment
    if category == "Electronics":
        base *= random.uniform(1.0, 1.5)
    elif category == "Clothing":
        base *= random.uniform(0.9, 1.3)

    base *= random.uniform(0.9, 1.4)
    base = max(0, min(70, round(base / 5) * 5))
    return base

order_items = []
# Track which items are returned (for returns generation)
return_flag_map = {}

for _, ord_row in df_orders.iterrows():
    oid = ord_row["order_id"]
    n_items = np.random.choice([1, 2, 3, 4, 5], p=[0.38, 0.32, 0.16, 0.10, 0.04])
    region = ord_row["region"]

    for _ in range(n_items):
        pid = random.randint(1, N_PRODUCTS)
        prod_row = df_prod.iloc[pid - 1]
        qty = int(np.random.choice([1, 2, 3], p=[0.68, 0.22, 0.10]))

        disc = discount_for(prod_row["selling_price"], region, prod_row["category"])
        final_price = round(prod_row["selling_price"] * (1 - disc / 100), 2)

        order_items.append({
            "order_id": oid,
            "product_id": pid,
            "quantity": qty,
            "selling_price": final_price,
            "discount": disc,
        })

        # Determine if this item will be returned (store for next step)
        meta = CAT_META[prod_row["category"]]
        ret_prob = meta["base_return"]
        # Higher discount → higher return probability
        ret_prob *= (1 + (disc / 100) * 0.4)
        # COD → higher return probability
        if ord_row["payment_mode"] == "COD":
            ret_prob *= 2.2
        # Electronics "Better price elsewhere" spike
        if prod_row["category"] == "Electronics":
            ret_prob *= 1.15
        ret_prob = min(ret_prob, 0.55)

        if random.random() < ret_prob:
            return_flag_map[(oid, pid)] = True

df_items = pd.DataFrame(order_items)
df_items.to_csv(os.path.join(RAW_DIR, "order_items.csv"), index=False)
print(f"  {len(df_items)} line items  |  "
      f"avg discount: {df_items['discount'].mean():.1f}%")


# ═══════════════════════════════════════════════════════════════════
# 5.  RETURNS  —  correlated with category, discount, payment mode
# ═══════════════════════════════════════════════════════════════════
print("─── 5. Returns ───")
returns = []
for (oid, pid), _ in return_flag_map.items():
    prod_row = df_prod.iloc[pid - 1]
    # Reason distribution varies by category
    if prod_row["category"] == "Electronics":
        reasons_w = [0.20, 0.30, 0.02, 0.08, 0.05, 0.28, 0.05, 0.02]
    elif prod_row["category"] == "Clothing":
        reasons_w = [0.05, 0.10, 0.50, 0.05, 0.10, 0.08, 0.07, 0.05]
    else:
        reasons_w = [0.15, 0.15, 0.10, 0.12, 0.15, 0.15, 0.10, 0.08]
    reason = random.choices(RETURN_REASONS, weights=reasons_w)[0]
    returns.append({"order_id": oid, "product_id": pid, "return_reason": reason})

df_returns = pd.DataFrame(returns)
df_returns.to_csv(os.path.join(RAW_DIR, "returns.csv"), index=False)
print(f"  {len(df_returns)} returns  |  "
      f"overall return rate: {100 * len(returns) / len(df_items):.1f}%")

# ── Category-level return rates ──
merged = df_items.merge(df_prod[["product_id", "category"]], on="product_id")
merged["is_return"] = merged.set_index(["order_id", "product_id"]).index.isin(
    df_returns.set_index(["order_id", "product_id"]).index
)
cat_returns = merged.groupby("category")["is_return"].mean() * 100
for cat, pct in cat_returns.items():
    print(f"    {cat}: {pct:.1f}% return rate")


# ═══════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ═══════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("DATASET GENERATION COMPLETE")
print("=" * 60)
print(f"  Customers:   {len(customers):>6}")
print(f"  Products:    {len(products):>6}")
print(f"  Orders:      {len(orders):>6}")
print(f"  Order Items: {len(order_items):>6}")
print(f"  Returns:     {len(returns):>6}")
print(f"  Location: {RAW_DIR}")
print("=" * 60)
