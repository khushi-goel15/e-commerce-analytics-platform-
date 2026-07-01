"""
Python Analytics Suite
──────────────────────
1. EDA — distributions, outliers, missing data
2. Correlation analysis — revenue drivers
3. Customer segmentation — RFM + KMeans
4. Sales forecasting — ARIMA
5. Insight extraction
"""
import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings("ignore")

from datetime import datetime, timedelta
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
from statsmodels.tsa.arima.model import ARIMA
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
OUT_DIR = os.path.join(BASE_DIR, "data", "exports")
os.makedirs(OUT_DIR, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════
# LOAD
# ═══════════════════════════════════════════════════════════════════
def load_data():
    customers   = pd.read_csv(os.path.join(RAW_DIR, "customers.csv"))
    orders      = pd.read_csv(os.path.join(RAW_DIR, "orders.csv"))
    order_items = pd.read_csv(os.path.join(RAW_DIR, "order_items.csv"))
    products    = pd.read_csv(os.path.join(RAW_DIR, "products.csv"))
    returns     = pd.read_csv(os.path.join(RAW_DIR, "returns.csv"))

    # Clean dates
    orders["order_date"] = pd.to_datetime(orders["order_date"], errors="coerce")
    orders["shipping_date"] = pd.to_datetime(orders["shipping_date"], errors="coerce")
    customers["signup_date"] = pd.to_datetime(customers["signup_date"], errors="coerce")

    # Build fact table
    fact = order_items.merge(
        orders[["order_id", "customer_id", "order_date", "shipping_date",
                "region", "payment_mode"]], on="order_id", how="left"
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

    return customers, orders, order_items, products, returns, fact


# ═══════════════════════════════════════════════════════════════════
# 1. EDA — Exploratory Data Analysis
# ═══════════════════════════════════════════════════════════════════
def run_eda(fact, customers, products, returns):
    print("=" * 60)
    print("1. EXPLORATORY DATA ANALYSIS")
    print("=" * 60)

    eda = {}

    # ── Revenue & profit overview ──
    total_revenue = fact["revenue"].sum()
    total_profit = fact["profit"].sum()
    total_orders = fact["order_id"].nunique()
    total_customers = fact["customer_id"].nunique()
    margin = (total_profit / total_revenue * 100) if total_revenue else 0
    aov = total_revenue / total_orders if total_orders else 0

    print(f"\n  Revenue:          ${total_revenue:>12,.2f}")
    print(f"  Profit:           ${total_profit:>12,.2f}")
    print(f"  Margin:           {margin:>12.2f}%")
    print(f"  Total Orders:     {total_orders:>12,}")
    print(f"  Unique Customers:  {total_customers:>12,}")
    print(f"  AOV:              ${aov:>12,.2f}")
    print(f"  Return Rate:      {fact['is_return'].mean()*100:.2f}%")

    eda["overview"] = {
        "revenue": round(total_revenue, 2),
        "profit": round(total_profit, 2),
        "margin_pct": round(margin, 2),
        "orders": int(total_orders),
        "customers": int(total_customers),
        "aov": round(aov, 2),
        "return_rate_pct": round(fact["is_return"].mean() * 100, 2),
    }

    # ── Missing data ──
    print("\n  ── Missing Data ──")
    for name, df in [("customers", customers), ("products", products),
                     ("returns", returns)]:
        nulls = df.isnull().sum()
        null_cols = nulls[nulls > 0]
        if len(null_cols):
            for col, n in null_cols.items():
                print(f"    {name}.{col}: {n} missing ({n/len(df)*100:.1f}%)")
    eda["missing_data"] = {
        "customers_with_null_signup": int(customers["signup_date"].isna().sum()),
    }

    # ── Revenue by category ──
    print("\n  ── Revenue by Category ──")
    cat_rev = fact.groupby("category").agg(
        revenue=("revenue", "sum"),
        profit=("profit", "sum"),
        orders=("order_id", "nunique"),
        returns=("is_return", "sum"),
    ).sort_values("revenue", ascending=False)
    cat_rev["margin"] = (cat_rev["profit"] / cat_rev["revenue"] * 100).round(2)
    cat_rev["return_rate"] = (cat_rev["returns"] / cat_rev["orders"] * 100).round(2)
    print(cat_rev.to_string())
    eda["by_category"] = cat_rev.reset_index().to_dict("records")

    # ── Revenue by region ──
    print("\n  ── Revenue by Region ──")
    reg_rev = fact.groupby("region").agg(
        revenue=("revenue", "sum"),
        profit=("profit", "sum"),
        orders=("order_id", "nunique"),
    ).sort_values("revenue", ascending=False)
    reg_rev["margin"] = (reg_rev["profit"] / reg_rev["revenue"] * 100).round(2)
    print(reg_rev.to_string())
    eda["by_region"] = reg_rev.reset_index().to_dict("records")

    # ── Discount analysis ──
    print("\n  ── Discount Impact on Margin ──")
    fact["disc_band"] = pd.cut(
        fact["discount"],
        bins=[-1, 0, 10, 20, 30, 100],
        labels=["0%", "1-10%", "11-20%", "21-30%", "30%+"]
    )
    disc_impact = fact.groupby("disc_band", observed=True).agg(
        transactions=("revenue", "count"),
        revenue=("revenue", "sum"),
        profit=("profit", "sum"),
    )
    disc_impact["margin"] = (disc_impact["profit"] / disc_impact["revenue"] * 100).round(2)
    print(disc_impact.to_string())
    eda["by_discount"] = disc_impact.reset_index().to_dict("records")

    return eda


# ═══════════════════════════════════════════════════════════════════
# 2. CORRELATION ANALYSIS
# ═══════════════════════════════════════════════════════════════════
def run_correlations(fact):
    print("\n" + "=" * 60)
    print("2. CORRELATION ANALYSIS")
    print("=" * 60)

    # Numeric columns
    num_cols = ["quantity", "selling_price", "discount", "revenue", "profit"]
    corr_df = fact[num_cols].corr()
    print("\n  Pearson Correlation Matrix:")
    print(corr_df.round(3).to_string())

    # Key findings
    rev_profit_corr = corr_df.loc["revenue", "profit"]
    disc_profit_corr = corr_df.loc["discount", "profit"]
    disc_rev_corr = corr_df.loc["discount", "revenue"]
    print(f"\n  Revenue ↔ Profit:          {rev_profit_corr:.3f}")
    print(f"  Discount ↔ Profit:         {disc_profit_corr:.3f}")
    print(f"  Discount ↔ Revenue:        {disc_rev_corr:.3f}")

    correlations = {
        "revenue_profit": round(rev_profit_corr, 3),
        "discount_profit": round(disc_profit_corr, 3),
        "discount_revenue": round(disc_rev_corr, 3),
    }
    return correlations


# ═══════════════════════════════════════════════════════════════════
# 3. CUSTOMER SEGMENTATION — RFM + KMeans
# ═══════════════════════════════════════════════════════════════════
def run_segmentation(fact, customers):
    print("\n" + "=" * 60)
    print("3. CUSTOMER SEGMENTATION (RFM + KMeans)")
    print("=" * 60)

    today = fact["order_date"].max()

    # RFM
    rfm = fact.groupby("customer_id").agg(
        recency=("order_date", lambda x: (today - x.max()).days),
        frequency=("order_id", "nunique"),
        monetary=("revenue", "sum"),
    ).reset_index()

    rfm["recency"] = rfm["recency"].clip(lower=0)
    rfm["monetary"] = rfm["monetary"].clip(lower=0)

    # Log-transform for normality
    rfm["log_monetary"] = np.log1p(rfm["monetary"])
    rfm["log_recency"]  = np.log1p(rfm["recency"])
    rfm["log_frequency"] = np.log1p(rfm["frequency"])

    # Scale
    scaler = StandardScaler()
    rfm_scaled = scaler.fit_transform(
        rfm[["log_recency", "log_frequency", "log_monetary"]]
    )

    # Find optimal K
    sil_scores = {}
    for k in range(2, 7):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(rfm_scaled)
        sil_scores[k] = silhouette_score(rfm_scaled, labels)

    best_k = max(sil_scores, key=sil_scores.get)
    print(f"\n  Optimal clusters: {best_k} (silhouette: {sil_scores[best_k]:.3f})")
    print(f"  Silhouette scores: {sil_scores}")

    # Final model
    km = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    rfm["segment"] = km.fit_predict(rfm_scaled)

    # Label segments
    seg_profiles = rfm.groupby("segment").agg(
        count=("customer_id", "count"),
        avg_recency=("recency", "mean"),
        avg_frequency=("frequency", "mean"),
        avg_monetary=("monetary", "mean"),
        total_revenue=("monetary", "sum"),
    ).round(1).sort_values("avg_monetary", ascending=False)

    # Assign descriptive labels
    labels = {}
    for seg_id in seg_profiles.index:
        m = seg_profiles.loc[seg_id, "avg_monetary"]
        f = seg_profiles.loc[seg_id, "avg_frequency"]
        r = seg_profiles.loc[seg_id, "avg_recency"]
        if m > seg_profiles["avg_monetary"].quantile(0.75):
            labels[seg_id] = "High Value"
        elif f > seg_profiles["avg_frequency"].median():
            labels[seg_id] = "Loyal"
        elif r > seg_profiles["avg_recency"].median() and f == 1:
            labels[seg_id] = "Churned"
        elif r < seg_profiles["avg_recency"].median() and f <= 2:
            labels[seg_id] = "New / Low Engagement"
        else:
            labels[seg_id] = "At Risk"

    seg_profiles["label"] = seg_profiles.index.map(labels)
    print("\n  Segment Profiles:\n")
    print(seg_profiles.to_string())

    # Export segments
    rfm[["customer_id", "segment", "recency", "frequency", "monetary"]].to_csv(
        os.path.join(OUT_DIR, "customer_segments.csv"), index=False
    )
    print("\n  Exported to data/exports/customer_segments.csv")

    segmentation = {
        "optimal_k": best_k,
        "silhouette": round(sil_scores[best_k], 3),
        "segments": seg_profiles.reset_index().to_dict("records"),
    }
    return segmentation


# ═══════════════════════════════════════════════════════════════════
# 4. SALES FORECASTING — ARIMA
# ═══════════════════════════════════════════════════════════════════
def run_forecasting(fact):
    print("\n" + "=" * 60)
    print("4. SALES FORECASTING (ARIMA)")
    print("=" * 60)

    # Daily sales aggregation
    daily = fact.groupby("order_date").agg(
        revenue=("revenue", "sum"),
        orders=("order_id", "nunique"),
    ).reset_index()
    daily.columns = ["ds", "y", "orders"]
    daily = daily.sort_values("ds").reset_index(drop=True)

    # Handle missing days
    full_range = pd.date_range(daily["ds"].min(), daily["ds"].max(), freq="D")
    daily = daily.set_index("ds").reindex(full_range).fillna(0).reset_index()
    daily.columns = ["ds", "y", "orders"]

    # Train/test split
    split_idx = int(len(daily) * 0.85)
    train = daily.iloc[:split_idx]
    test = daily.iloc[split_idx:]

    print(f"\n  Training: {train['ds'].min().date()} → {train['ds'].max().date()}")
    print(f"  Testing:  {test['ds'].min().date()} → {test['ds'].max().date()}")

    # ARIMA
    try:
        model = ARIMA(
            train["y"].values,
            order=(2, 1, 2),
            seasonal_order=(1, 1, 1, 7),
        )
        fitted = model.fit()
        forecast = fitted.forecast(steps=len(test))
        forecast = forecast.clip(lower=0)

        # Error metrics
        mae = np.abs(test["y"].values - forecast).mean()
        rmse = np.sqrt(((test["y"].values - forecast) ** 2).mean())
        mape = np.mean(
            np.abs((test["y"].values - forecast) / (test["y"].values + 1e-6))
        ) * 100

        print(f"  MAE:  {mae:,.0f}")
        print(f"  RMSE: {rmse:,.0f}")
        print(f"  MAPE: {mape:.2f}%")

        # Future 90-day forecast
        future_forecast = fitted.forecast(steps=90)
        future_forecast = future_forecast.clip(lower=0)
        next_90_days_revenue = future_forecast.sum()
        print(f"\n  Forecasted revenue (next 90 days): ${next_90_days_revenue:,.0f}")

        # Export
        forecast_df = pd.DataFrame({
            "ds": test["ds"].values,
            "actual": test["y"].values,
            "predicted": forecast,
        })
        forecast_df.to_csv(os.path.join(OUT_DIR, "forecast_results.csv"), index=False)

        future_df = pd.DataFrame({
            "ds": pd.date_range(
                start=daily["ds"].max() + timedelta(days=1), periods=90
            ),
            "predicted_revenue": future_forecast,
        })
        future_df.to_csv(os.path.join(OUT_DIR, "forecast_future_90d.csv"), index=False)

        print("  Exported to data/exports/forecast_*.csv")

        forecasting = {
            "mae": round(mae, 2),
            "rmse": round(rmse, 2),
            "mape_pct": round(mape, 2),
            "next_90d_revenue": round(next_90_days_revenue, 2),
        }
    except Exception as e:
        print(f"  ARIMA failed: {e}")
        # Fallback: simple naive forecast
        print("  Using naive seasonal forecast instead")
        weekly_avg = daily["y"].groupby(daily["ds"].dt.dayofweek).mean()
        forecast = np.tile(weekly_avg.values, int(np.ceil(len(test) / 7)))[:len(test)]
        mae = np.abs(test["y"].values - forecast).mean()
        next_90_days_revenue = np.tile(weekly_avg.values, 13)[:90].sum()
        print(f"  MAE:  {mae:,.0f}")
        print(f"  Forecasted revenue (next 90 days): ${next_90_days_revenue:,.0f}")
        forecasting = {
            "mae": round(mae, 2),
            "method": "naive_seasonal",
            "next_90d_revenue": round(next_90_days_revenue, 2),
        }

    return forecasting


# ═══════════════════════════════════════════════════════════════════
# 5. INSIGHT EXTRACTION
# ═══════════════════════════════════════════════════════════════════
def extract_insights(fact, customers):
    print("\n" + "=" * 60)
    print("5. KEY INSIGHTS")
    print("=" * 60)

    insights = []

    # Pareto check
    cust_rev = fact.groupby("customer_id")["revenue"].sum().sort_values(ascending=False)
    top_20 = int(len(cust_rev) * 0.20)
    top_20_rev = cust_rev.iloc[:top_20].sum()
    pareto_pct = top_20_rev / cust_rev.sum() * 100
    insights.append(
        f"  Pareto: Top 20% of customers generate {pareto_pct:.1f}% of revenue"
    )

    # Return rate by category
    cat_ret = fact.groupby("category")["is_return"].mean() * 100
    top_ret_cat = cat_ret.idxmax()
    insights.append(
        f"  Returns: '{top_ret_cat}' has the highest return rate ({cat_ret.max():.1f}%)"
    )

    # Region margin
    reg_margin = fact.groupby("region").apply(
        lambda x: x["profit"].sum() / x["revenue"].sum() * 100
    )
    worst_reg = reg_margin.idxmin()
    best_reg = reg_margin.idxmax()
    insights.append(
        f"  Regions: '{worst_reg}' has lowest margin ({reg_margin.min():.1f}%), "
        f"while '{best_reg}' has highest ({reg_margin.max():.1f}%)"
    )

    # Discount impact
    high_disc = fact[fact["discount"] >= 20]
    if len(high_disc):
        high_disc_margin = high_disc["profit"].sum() / high_disc["revenue"].sum() * 100
        overall_margin = fact["profit"].sum() / fact["revenue"].sum() * 100
        insights.append(
            f"  Discounts: Orders with ≥20% discount have {high_disc_margin:.1f}% margin "
            f"vs {overall_margin:.1f}% overall (−{overall_margin - high_disc_margin:.1f}pp)"
        )

    # Repeat purchase rate
    order_counts = fact.groupby("customer_id")["order_id"].nunique()
    repeat = (order_counts > 1).mean() * 100
    insights.append(
        f"  Retention: {repeat:.1f}% of customers are repeat purchasers"
    )

    # COD return risk
    cod_ret = fact[fact["payment_mode"] == "COD"]["is_return"].mean() * 100
    prepaid_ret = fact[fact["payment_mode"] != "COD"]["is_return"].mean() * 100
    insights.append(
        f"  Payments: COD orders have {cod_ret:.1f}% return rate "
        f"vs {prepaid_ret:.1f}% for prepaid ({cod_ret/prepaid_ret:.1f}x higher)"
    )

    # AOV trend
    fact["month"] = fact["order_date"].dt.to_period("M")
    aov_trend = fact.groupby("month")["revenue"].sum() / fact.groupby("month")["order_id"].nunique()
    aov_change = ((aov_trend.iloc[-1] - aov_trend.iloc[0]) / aov_trend.iloc[0] * 100)
    insights.append(
        f"  AOV: Average order value changed by {aov_change:+.1f}% over the period"
    )

    for ins in insights:
        print(ins)

    return insights


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("Loading data...")
    customers, orders, order_items, products, returns, fact = load_data()
    print(f"  Fact table: {len(fact):,} rows\n")

    eda = run_eda(fact, customers, products, returns)
    correlations = run_correlations(fact)
    segmentation = run_segmentation(fact, customers)
    forecasting = run_forecasting(fact)
    insights = extract_insights(fact, customers)

    # Export all results to JSON
    results = {
        "eda": eda,
        "correlations": correlations,
        "segmentation": segmentation,
        "forecasting": forecasting,
        "insights": insights,
    }
    with open(os.path.join(OUT_DIR, "analytics_results.json"), "w") as f:
        json.dump(results, f, indent=2, default=str)

    print("\n" + "=" * 60)
    print("ANALYTICS COMPLETE — Results saved to data/exports/")
    print("=" * 60)
