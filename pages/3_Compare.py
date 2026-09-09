"""
Category comparison page: AI vs Cybersecurity by default, any two categories on request.

Three panels over the full history: how often each category trended, how it
was covered (sentiment), and how sticky it was (recurrence rate), plus a
side-by-side summary table.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import brand  # noqa: E402
import settings  # noqa: E402
from features import CATEGORIES  # noqa: E402

settings.page_config("Compare")
settings.brand_sidebar()
settings.render_theme_toggle()

COLOURS = {"a": brand.ACCENT, "b": brand.CONTRAST}   # the palette's two-sided pair; see docs/BRAND.md
ROLL = 7                                         # rolling window in days


@st.cache_data
def load_data() -> pd.DataFrame:
    return pd.read_parquet(ROOT / "data" / "tech_trends.parquet")


def daily_series(df: pd.DataFrame, category: str) -> pd.DataFrame:
    """Per-day count, mean sentiment and recurrence rate for one category,
    reindexed to every collected day so gaps show as zeros / NaN."""
    days = pd.Index(sorted(df["date"].unique()), name="date")
    sub = df[df["category"].astype(str) == category]
    g = sub.groupby("date")
    out = pd.DataFrame({
        "trend_days": g.size().reindex(days, fill_value=0),
        "sentiment": g["sentiment_score"].mean().reindex(days),
        "recurrence": g["recurred_next_day"].apply(lambda s: s.dropna().astype(float).mean()).reindex(days),
    })
    out["trend_days_roll"] = out["trend_days"].rolling(ROLL, min_periods=1).mean()
    out["sentiment_roll"] = out["sentiment"].rolling(ROLL, min_periods=1).mean()
    out["recurrence_roll"] = out["recurrence"].rolling(ROLL, min_periods=1).mean()
    return out


def summary_row(df: pd.DataFrame, category: str) -> dict:
    sub = df[df["category"].astype(str) == category]
    lab = sub["recurred_next_day"].dropna().astype(float)
    return {
        "category": category,
        "trend-days": len(sub),
        "distinct topics": sub["topic"].nunique(),
        "days present": sub["date"].nunique(),
        "avg rank": round(sub["rank"].mean(), 2),
        "avg sources": round(sub["source_count"].mean(), 2),
        "avg sentiment": round(sub["sentiment_score"].mean(), 3),
        "share negative": f"{(sub['sentiment_score'] < -0.3).mean():.0%}",
        "recurrence rate": f"{lab.mean():.0%}" if len(lab) else "n/a",
    }


df = load_data()

settings.header("Category Comparison", "Two categories side by side over the whole history: volume, tone and persistence. Defaults to AI vs Cybersecurity.")

c1, c2, _ = st.columns([1, 1, 3])
cat_a = c1.selectbox("Category A", CATEGORIES, index=CATEGORIES.index("AI"))
cat_b = c2.selectbox("Category B", CATEGORIES, index=CATEGORIES.index("Cybersecurity"))
if cat_a == cat_b:
    st.warning("Pick two different categories.")
    st.stop()

a, b = daily_series(df, cat_a), daily_series(df, cat_b)

# ---- headline deltas -----------------------------------------------------------
ra, rb = summary_row(df, cat_a), summary_row(df, cat_b)
m1, m2, m3 = st.columns(3)
m1.metric(f"Trend-days · {cat_a} vs {cat_b}", f"{ra['trend-days']} vs {rb['trend-days']}", f"{ra['trend-days'] - rb['trend-days']:+d}")
m2.metric("Avg sentiment", f"{ra['avg sentiment']:+.2f} vs {rb['avg sentiment']:+.2f}", f"{ra['avg sentiment'] - rb['avg sentiment']:+.2f}")
m3.metric("Recurrence rate", f"{ra['recurrence rate']} vs {rb['recurrence rate']}")

# ---- three-panel chart ------------------------------------------------------------
fig, axes = plt.subplots(3, 1, figsize=(11, 8.5), sharex=True)
panels = [
    ("trend_days", "trend_days_roll", "Trend-days per day", "count"),
    ("sentiment", "sentiment_roll", "Average sentiment", "VADER compound"),
    ("recurrence", "recurrence_roll", "Recurrence rate (share back next day)", "rate"),
]
for ax, (raw, roll, title, ylabel) in zip(axes, panels):
    for series, cat, key in ((a, cat_a, "a"), (b, cat_b, "b")):
        ax.plot(series.index, series[raw], color=COLOURS[key], alpha=0.25, lw=1)
        ax.plot(series.index, series[roll], color=COLOURS[key], lw=2.2, label=f"{cat} ({ROLL}-day mean)")
    ax.set_title(title, loc="left", fontsize=11)
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.2)
    if raw != "trend_days":
        ax.axhline(0 if raw == "sentiment" else 0.5, color="grey", lw=0.8, ls="--")
axes[0].legend(loc="upper left", frameon=False, labelcolor=settings.TEXT[settings.current_theme()])
axes[-1].set_xlabel("date")
fig.autofmt_xdate()
settings.style_figure(fig, *axes)
fig.tight_layout()
st.pyplot(fig, width="stretch")
st.caption(f"Faint lines are daily values; bold lines are {ROLL}-day rolling means. Recurrence is undefined on the latest day (label not yet known).")

# ---- summary table ------------------------------------------------------------------
st.subheader("Side by side")
side = pd.DataFrame([ra, rb]).set_index("category").T.rename_axis("metric").astype(str)  # mixed types -> str for Arrow
st.dataframe(side, width="stretch")

# ---- top topics per category ----------------------------------------------------------
st.subheader("Most persistent topics")
t1, t2 = st.columns(2)
for col, cat in ((t1, cat_a), (t2, cat_b)):
    top = (df[df["category"].astype(str) == cat].groupby("topic")
           .agg(days=("date", "nunique"), avg_sentiment=("sentiment_score", "mean"), avg_sources=("source_count", "mean"))
           .sort_values("days", ascending=False).head(5).round(2))
    col.markdown(f"**{cat}**")
    col.dataframe(top, width="stretch")
