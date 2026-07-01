"""
Generate consulting-grade charts embedded in the Word report.
All charts are saved as PNG images at 200 DPI.
"""
import pandas as pd
import numpy as np
import os, json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.colors import LinearSegmentedColormap
import seaborn as sns

sns.set_theme(style="whitegrid", font_scale=0.85, palette="Blues_d")
DARK_BLUE = "#0D233F"
MID_BLUE  = "#1B4F8A"
ACCENT    = "#007BC0"
RED       = "#C0392B"
GREEN     = "#1E8445"
GOLD      = "#D4A017"
GREY      = "#7F8C8D"
LIGHT_BG  = "#EBF5FB"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR  = os.path.join(BASE_DIR, "data", "raw")
IMG_DIR  = os.path.join(BASE_DIR, "data", "exports", "images")
RESULTS_PATH = os.path.join(BASE_DIR, "data", "exports", "analytics_results.json")
os.makedirs(IMG_DIR, exist_ok=True)

with open(RESULTS_PATH) as f:
    R = json.load(f)

customers = pd.read_csv(os.path.join(RAW_DIR, "customers.csv"))
orders    = pd.read_csv(os.path.join(RAW_DIR, "orders.csv"))
items     = pd.read_csv(os.path.join(RAW_DIR, "order_items.csv"))
products  = pd.read_csv(os.path.join(RAW_DIR, "products.csv"))
returns   = pd.read_csv(os.path.join(RAW_DIR, "returns.csv"))

# Build fact
orders["order_date"] = pd.to_datetime(orders["order_date"], errors="coerce")
fact = items.merge(orders[["order_id","customer_id","order_date","region","payment_mode"]], on="order_id")
fact = fact.merge(products[["product_id","category","sub_category","brand","cost_price"]], on="product_id")
fact["revenue"] = fact["quantity"] * fact["selling_price"]
fact["cost_total"] = fact["quantity"] * fact["cost_price"]
fact["profit"] = fact["revenue"] - fact["cost_total"]
fact["is_return"] = fact.set_index(["order_id","product_id"]).index.isin(
    returns.set_index(["order_id","product_id"]).index
)
fact["margin_pct"] = (fact["profit"] / fact["revenue"] * 100).round(2)

O = R["eda"]["overview"]
total_rev, total_profit = O["revenue"], O["profit"]
margin, total_orders, aov = O["margin_pct"], O["orders"], O["aov"]
return_rate = O["return_rate_pct"]

# ══════════════════════════════════════════════════════════════════
# CHART 1: EXECUTIVE KPI DASHBOARD
# ══════════════════════════════════════════════════════════════════
print("  Chart 1: KPI Dashboard")
fig, axes = plt.subplots(1, 5, figsize=(12, 2.8))
kpis = [
    ("Revenue", f"${total_rev/1e6:.1f}M", MID_BLUE),
    ("Profit",  f"${total_profit/1e6:.1f}M", GREEN),
    ("Margin",  f"{margin:.1f}%", ACCENT),
    ("Orders",  f"{total_orders:,}", DARK_BLUE),
    ("AOV",     f"${aov:.0f}", GOLD),
]
for ax, (label, val, color) in zip(axes, kpis):
    ax.text(0.5, 0.65, val, fontsize=24, fontweight="bold", color=color,
            ha="center", va="center", transform=ax.transAxes)
    ax.text(0.5, 0.22, label, fontsize=11, color=GREY,
            ha="center", va="center", transform=ax.transAxes)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.axis("off")
    # accent line
    ax.axhline(0.85, xmin=0.2, xmax=0.8, color=color, linewidth=2)
plt.tight_layout(pad=1.5)
fig.savefig(os.path.join(IMG_DIR, "01_kpi_dashboard.png"), dpi=200, bbox_inches="tight")
plt.close(fig)

# ══════════════════════════════════════════════════════════════════
# CHART 2: REVENUE BY CATEGORY (BAR)
# ══════════════════════════════════════════════════════════════════
print("  Chart 2: Revenue by Category")
cat_data = pd.DataFrame(R["eda"]["by_category"]).sort_values("revenue", ascending=True)
fig, ax = plt.subplots(figsize=(8, 3.5))
colors = [RED if c == "Electronics" else MID_BLUE for c in cat_data["category"]]
bars = ax.barh(cat_data["category"], cat_data["revenue"] / 1e6, color=colors, height=0.55, edgecolor="white")
for bar, rev, margin_val, ret in zip(bars, cat_data["revenue"], cat_data["margin"], cat_data["return_rate"]):
    ax.text(bar.get_width() + 0.15, bar.get_y() + bar.get_height()/2,
            f"${rev/1e6:.1f}M  |  Margin: {margin_val:.1f}%  |  Returns: {ret:.1f}%",
            va="center", fontsize=8, color=GREY)
ax.set_xlabel("Revenue ($M)", fontsize=10, color=GREY)
ax.set_title("Revenue & Margin by Category", fontsize=13, fontweight="bold", color=DARK_BLUE, pad=12)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
ax.tick_params(colors=GREY, labelsize=9)
plt.tight_layout()
fig.savefig(os.path.join(IMG_DIR, "02_revenue_by_category.png"), dpi=200, bbox_inches="tight")
plt.close(fig)

# ══════════════════════════════════════════════════════════════════
# CHART 3: REGIONAL ANALYSIS (DUAL BAR — REVENUE + MARGIN)
# ══════════════════════════════════════════════════════════════════
print("  Chart 3: Regional Analysis")
reg_data = pd.DataFrame(R["eda"]["by_region"]).sort_values("revenue")
fig, ax1 = plt.subplots(figsize=(7, 3.5))
ax2 = ax1.twinx()
x = np.arange(len(reg_data))
w = 0.35
bars1 = ax1.bar(x - w/2, reg_data["revenue"]/1e6, w, color=MID_BLUE, edgecolor="white", label="Revenue ($M)")
bars2 = ax2.bar(x + w/2, reg_data["margin"], w, color=GREEN, edgecolor="white", label="Margin (%)")
ax1.set_xticks(x); ax1.set_xticklabels(reg_data["region"])
ax1.set_ylabel("Revenue ($M)", fontsize=10, color=MID_BLUE)
ax2.set_ylabel("Margin (%)", fontsize=10, color=GREEN)
ax1.set_title("Revenue vs Margin by Region", fontsize=13, fontweight="bold", color=DARK_BLUE, pad=12)
for i, (_, r) in enumerate(reg_data.iterrows()):
    ax1.text(i - 0.25, r["revenue"]/1e6 + 0.1, f"${r['revenue']/1e6:.1f}M", fontsize=8, color=MID_BLUE)
    ax2.text(i + 0.1, r["margin"] + 0.3, f"{r['margin']:.1f}%", fontsize=8, color=GREEN)
    if r["region"] == "West":
        ax1.text(i, -0.55, "! HIGH VOLUME\nLOW MARGIN", fontsize=6.5, color=RED,
                 ha="center", fontweight="bold")
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=8)
ax1.spines["top"].set_visible(False); ax2.spines["top"].set_visible(False)
ax1.tick_params(colors=GREY, labelsize=9)
plt.tight_layout()
fig.savefig(os.path.join(IMG_DIR, "03_regional_analysis.png"), dpi=200, bbox_inches="tight")
plt.close(fig)

# ══════════════════════════════════════════════════════════════════
# CHART 4: DISCOUNT VS MARGIN EROSION
# ══════════════════════════════════════════════════════════════════
print("  Chart 4: Discount Margin Erosion")
disc_data = pd.DataFrame(R["eda"]["by_discount"])
bands = disc_data["disc_band"].tolist()
margins = disc_data["margin"].tolist()
revs = disc_data["revenue"].tolist()
colors_bar = ["#1E8445" if m > 30 else "#52BE80" if m > 20 else "#F4D03F" if m > 10 else "#E67E22" if m > 0 else "#C0392B" for m in margins]
fig, ax = plt.subplots(figsize=(8, 3.5))
bars = ax.bar(bands, margins, color=colors_bar, edgecolor="white", width=0.6)
for bar, m, r in zip(bars, margins, revs):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.8,
            f"{m:.1f}%\n${r/1e6:.1f}M", ha="center", fontsize=8, color=GREY, fontweight="bold")
ax.axhline(y=0, color=RED, linewidth=1.2, linestyle="--", alpha=0.5)
ax.set_ylabel("Profit Margin (%)", fontsize=10, color=GREY)
ax.set_xlabel("Discount Band", fontsize=10, color=GREY)
ax.set_title("Discount Depth Destroys Profitability", fontsize=13, fontweight="bold", color=DARK_BLUE, pad=12)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
ax.tick_params(colors=GREY, labelsize=9)
plt.tight_layout()
fig.savefig(os.path.join(IMG_DIR, "04_discount_erosion.png"), dpi=200, bbox_inches="tight")
plt.close(fig)

# ══════════════════════════════════════════════════════════════════
# CHART 5: PARETO CURVE — CUSTOMER CONCENTRATION
# ══════════════════════════════════════════════════════════════════
print("  Chart 5: Pareto Curve")
cust_rev = fact.groupby("customer_id")["revenue"].sum().sort_values(ascending=False)
cum_share = np.cumsum(cust_rev.values) / cust_rev.sum()
x = np.arange(1, len(cum_share) + 1) / len(cum_share) * 100
fig, ax = plt.subplots(figsize=(7, 3.5))
ax.fill_between(x, cum_share * 100, alpha=0.15, color=MID_BLUE)
ax.plot(x, cum_share * 100, color=MID_BLUE, linewidth=2)
ax.axhline(y=80, color=RED, linestyle="--", alpha=0.6, linewidth=1)
ax.axvline(x=20, color=RED, linestyle="--", alpha=0.6, linewidth=1)
ax.text(22, 82, "80% revenue", fontsize=9, color=RED, fontweight="bold")
ax.text(5, 50, "20% of customers", fontsize=9, color=RED, fontweight="bold", rotation=90)
ax.fill_between(x[:int(len(x)*0.2)], cum_share[:int(len(cum_share)*0.2)] * 100,
                alpha=0.25, color=GOLD, label="Top 20% of customers")
ax.set_xlabel("Customers (%)", fontsize=10, color=GREY)
ax.set_ylabel("Cumulative Revenue (%)", fontsize=10, color=GREY)
ax.set_title("Pareto: 20% of Customers Drive 80.7% of Revenue", fontsize=13, fontweight="bold", color=DARK_BLUE, pad=12)
ax.set_xlim(0, 100); ax.set_ylim(0, 100)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
ax.legend(fontsize=9)
ax.tick_params(colors=GREY, labelsize=9)
plt.tight_layout()
fig.savefig(os.path.join(IMG_DIR, "05_pareto_curve.png"), dpi=200, bbox_inches="tight")
plt.close(fig)

# ══════════════════════════════════════════════════════════════════
# CHART 6: MONTHLY SALES TREND
# ══════════════════════════════════════════════════════════════════
print("  Chart 6: Monthly Sales Trend")
daily = fact.groupby(fact["order_date"].dt.to_period("M")).agg(
    revenue=("revenue", "sum"), profit=("profit", "sum")
).reset_index()
daily["month"] = daily["order_date"].astype(str)
fig, ax = plt.subplots(figsize=(9, 3.5))
x_idx = np.arange(len(daily))
ax.fill_between(x_idx, daily["revenue"]/1e6, alpha=0.15, color=MID_BLUE)
ax.plot(x_idx, daily["revenue"]/1e6, color=MID_BLUE, linewidth=1.8, marker="o", markersize=4, label="Revenue")
ax.fill_between(x_idx, daily["profit"]/1e6, alpha=0.12, color=GREEN)
ax.plot(x_idx, daily["profit"]/1e6, color=GREEN, linewidth=1.8, marker="s", markersize=4, label="Profit")
# Annotate peaks
peak_idx = daily["revenue"].idxmax()
low_idx = daily["revenue"].idxmin()
ax.annotate(f"Peak: ${daily.loc[peak_idx,'revenue']/1e6:.1f}M",
            xy=(peak_idx, daily.loc[peak_idx,"revenue"]/1e6),
            xytext=(peak_idx+1, daily.loc[peak_idx,"revenue"]/1e6 + 0.15),
            fontsize=8, color=MID_BLUE, arrowprops=dict(arrowstyle="->", color=MID_BLUE))
ax.annotate(f"Low: ${daily.loc[low_idx,'revenue']/1e6:.1f}M  (Feb lull)",
            xy=(low_idx, daily.loc[low_idx,"revenue"]/1e6),
            xytext=(low_idx, daily.loc[low_idx,"revenue"]/1e6 - 0.25),
            fontsize=8, color=RED, arrowprops=dict(arrowstyle="->", color=RED))
ax.set_xticks(x_idx[::3]); ax.set_xticklabels(daily["month"][::3], rotation=45, fontsize=7)
ax.set_ylabel("Revenue / Profit ($M)", fontsize=10, color=GREY)
ax.set_title("Monthly Revenue & Profit Trend", fontsize=13, fontweight="bold", color=DARK_BLUE, pad=12)
ax.legend(fontsize=9)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
ax.tick_params(colors=GREY)
plt.tight_layout()
fig.savefig(os.path.join(IMG_DIR, "06_monthly_trend.png"), dpi=200, bbox_inches="tight")
plt.close(fig)

# ══════════════════════════════════════════════════════════════════
# CHART 7: RETURN RATE BY CATEGORY
# ══════════════════════════════════════════════════════════════════
print("  Chart 7: Return Rate by Category")
cat_data_sorted = cat_data.sort_values("return_rate")
fig, ax = plt.subplots(figsize=(7, 3))
colors_ret = [RED if r > 20 else GOLD if r > 10 else GREEN for r in cat_data_sorted["return_rate"]]
bars = ax.barh(cat_data_sorted["category"], cat_data_sorted["return_rate"], color=colors_ret, height=0.5, edgecolor="white")
for bar, v in zip(bars, cat_data_sorted["return_rate"]):
    ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2, f"{v:.1f}%", va="center", fontsize=9, fontweight="bold", color=GREY)
ax.axvline(x=10, color=GREY, linestyle="--", alpha=0.5, linewidth=1, label="Industry Benchmark (10%)")
ax.set_xlabel("Return Rate (%)", fontsize=10, color=GREY)
ax.set_title("Return Rate by Category", fontsize=13, fontweight="bold", color=DARK_BLUE, pad=12)
ax.legend(fontsize=8)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
ax.tick_params(colors=GREY, labelsize=9)
plt.tight_layout()
fig.savefig(os.path.join(IMG_DIR, "07_return_rate.png"), dpi=200, bbox_inches="tight")
plt.close(fig)

# ══════════════════════════════════════════════════════════════════
# CHART 8: CUSTOMER SEGMENTATION COMPARISON
# ══════════════════════════════════════════════════════════════════
print("  Chart 8: Customer Segmentation")
segs = R["segmentation"]["segments"]
if len(segs) >= 2:
    labels = [s["label"] for s in segs[:2]]
    counts = [s["count"] for s in segs[:2]]
    avg_mons = [s["avg_monetary"] for s in segs[:2]]
    avg_freqs = [s["avg_frequency"] for s in segs[:2]]

    fig, axes = plt.subplots(1, 3, figsize=(10, 3.2))
    # Pie
    colors_seg = [MID_BLUE, "#E8E8E8"]
    wedges, texts, autotexts = axes[0].pie(counts, labels=labels, autopct="%1.0f%%",
                                            colors=colors_seg, startangle=90,
                                            textprops={"fontsize": 8, "color": DARK_BLUE})
    axes[0].set_title("Customer Count", fontsize=10, fontweight="bold", color=DARK_BLUE)
    # Monetary bar
    axes[1].bar(["High Value", "At Risk"], [avg_mons[0], avg_mons[1]],
                color=[MID_BLUE, "#E8E8E8"], edgecolor="white", width=0.5)
    axes[1].text(0, avg_mons[0]+500, f"${avg_mons[0]:,.0f}", ha="center", fontsize=9, fontweight="bold", color=MID_BLUE)
    axes[1].text(1, avg_mons[1]+200, f"${avg_mons[1]:,.0f}", ha="center", fontsize=9, fontweight="bold", color=GREY)
    axes[1].set_title("Avg Revenue / Customer", fontsize=10, fontweight="bold", color=DARK_BLUE)
    axes[1].spines["top"].set_visible(False); axes[1].spines["right"].set_visible(False)
    axes[1].tick_params(colors=GREY, labelsize=8)
    # Frequency bar
    axes[2].bar(["High Value", "At Risk"], [avg_freqs[0], avg_freqs[1]],
                color=[MID_BLUE, "#E8E8E8"], edgecolor="white", width=0.5)
    axes[2].text(0, avg_freqs[0]+0.3, f"{avg_freqs[0]:.0f}x", ha="center", fontsize=9, fontweight="bold", color=MID_BLUE)
    axes[2].text(1, avg_freqs[1]+0.1, f"{avg_freqs[1]:.1f}x", ha="center", fontsize=9, fontweight="bold", color=GREY)
    axes[2].set_title("Avg Orders / Customer", fontsize=10, fontweight="bold", color=DARK_BLUE)
    axes[2].spines["top"].set_visible(False); axes[2].spines["right"].set_visible(False)
    axes[2].tick_params(colors=GREY, labelsize=8)
    plt.tight_layout()
    fig.savefig(os.path.join(IMG_DIR, "08_customer_segments.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)

# ══════════════════════════════════════════════════════════════════
# CHART 9: RETURN REASON BREAKDOWN (PIE)
# ══════════════════════════════════════════════════════════════════
print("  Chart 9: Return Reasons")
ret_reasons = returns["return_reason"].value_counts()
fig, ax = plt.subplots(figsize=(6, 3.5))
colors_pie = [MID_BLUE, ACCENT, "#5DADE2", GREEN, GOLD, "#E67E22", RED, "#8E44AD"]
wedges, texts, autotexts = ax.pie(
    ret_reasons.values, labels=ret_reasons.index, autopct="%1.1f%%",
    colors=colors_pie[:len(ret_reasons)], startangle=90,
    textprops={"fontsize": 7}
)
ax.set_title("Return Reasons Distribution", fontsize=12, fontweight="bold", color=DARK_BLUE, pad=12)
plt.tight_layout()
fig.savefig(os.path.join(IMG_DIR, "09_return_reasons.png"), dpi=200, bbox_inches="tight")
plt.close(fig)

# ══════════════════════════════════════════════════════════════════
# CHART 10: AOV & ORDER FREQUENCY BY REGION
# ══════════════════════════════════════════════════════════════════
print("  Chart 10: AOV by Region")
reg_aov = fact.groupby("region").agg(
    revenue=("revenue", "sum"), orders=("order_id", "nunique")
).reset_index()
reg_aov["aov"] = reg_aov["revenue"] / reg_aov["orders"]
fig, ax = plt.subplots(figsize=(6, 3))
bars = ax.bar(reg_aov["region"], reg_aov["aov"], color=[MID_BLUE, ACCENT, GREEN, GOLD], edgecolor="white", width=0.5)
for bar, v in zip(bars, reg_aov["aov"]):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 10, f"${v:,.0f}", ha="center", fontsize=9, fontweight="bold", color=GREY)
ax.set_ylabel("Average Order Value ($)", fontsize=10, color=GREY)
ax.set_title("Average Order Value by Region", fontsize=12, fontweight="bold", color=DARK_BLUE, pad=12)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
ax.tick_params(colors=GREY, labelsize=9)
plt.tight_layout()
fig.savefig(os.path.join(IMG_DIR, "10_aov_by_region.png"), dpi=200, bbox_inches="tight")
plt.close(fig)

# ══════════════════════════════════════════════════════════════════
# CHART 11: PAYMENT MODE ANALYSIS
# ══════════════════════════════════════════════════════════════════
print("  Chart 11: Payment Mode Analysis")
pay_ret = fact.groupby("payment_mode")["is_return"].mean().sort_values() * 100
pay_orders = fact.groupby("payment_mode")["order_id"].nunique().sort_index()
fig, ax = plt.subplots(figsize=(6.5, 3))
colors_pay = [RED if p == "COD" else MID_BLUE for p in pay_ret.index]
bars = ax.barh(pay_ret.index, pay_ret.values, color=colors_pay, height=0.5, edgecolor="white")
for bar, v, p in zip(bars, pay_ret.values, pay_ret.index):
    label = f"{v:.1f}%" if v > 15 else f"{v:.1f}%"
    ax.text(bar.get_width() + 0.15, bar.get_y() + bar.get_height()/2, label, va="center", fontsize=9, fontweight="bold", color=GREY)
ax.set_xlabel("Return Rate (%)", fontsize=10, color=GREY)
ax.set_title("Return Rate by Payment Mode", fontsize=12, fontweight="bold", color=DARK_BLUE, pad=12)
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
ax.tick_params(colors=GREY, labelsize=9)
plt.tight_layout()
fig.savefig(os.path.join(IMG_DIR, "11_payment_analysis.png"), dpi=200, bbox_inches="tight")
plt.close(fig)

# ══════════════════════════════════════════════════════════════════
# CHART 12: CORRELATION HEATMAP
# ══════════════════════════════════════════════════════════════════
print("  Chart 12: Correlation Heatmap")
num_cols = ["quantity", "selling_price", "discount", "revenue", "profit"]
corr_matrix = fact[num_cols].corr()
fig, ax = plt.subplots(figsize=(5, 4))
sns.heatmap(corr_matrix, annot=True, fmt=".3f", cmap="Blues", center=0,
            linewidths=0.5, cbar_kws={"shrink": 0.7}, ax=ax,
            annot_kws={"fontsize": 8})
ax.set_title("Feature Correlation Matrix", fontsize=12, fontweight="bold", color=DARK_BLUE, pad=12)
ax.tick_params(colors=GREY, labelsize=8)
plt.tight_layout()
fig.savefig(os.path.join(IMG_DIR, "12_correlation_heatmap.png"), dpi=200, bbox_inches="tight")
plt.close(fig)

print(f"\nAll charts saved to: {IMG_DIR}")
