"""
Weekly trend summary page (Streamlit multipage: lives in pages/ next to Daily_Trends.py).

Groups the daily dataset into ISO weeks and shows, for a chosen week:
persistence leaders, category mix, daily sentiment, the weekly keyword cloud,
and a downloadable per-topic summary table.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from wordcloud import WordCloud

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import settings  # noqa: E402

DATA_PATH = ROOT / "data" / "tech_trends.parquet"
settings.page_config("Weekly Summary")


@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_parquet(DATA_PATH)
    iso = df["date"].dt.isocalendar()
    df["week"] = iso["year"].astype(str) + "-W" + iso["week"].astype(str).str.zfill(2)
    df["week_start"] = df["date"] - pd.to_timedelta(df["date"].dt.weekday, unit="D")
    return df


def weekly_topic_summary(week_df: pd.DataFrame) -> pd.DataFrame:
    """One row per topic: how many days it trended, best rank, coverage, sentiment."""
    g = week_df.groupby(["topic", "category"], observed=True)
    out = g.agg(
        days_trending=("date", "nunique"),
        best_rank=("rank", "min"),
        avg_sources=("source_count", "mean"),
        total_keyword_mentions=("keyword_frequency", "sum"),
        avg_sentiment=("sentiment_score", "mean"),
        recurrence_rate=("recurred_next_day", lambda s: s.dropna().astype(float).mean()),
    ).reset_index()
    out["avg_sources"] = out["avg_sources"].round(2)
    out["avg_sentiment"] = out["avg_sentiment"].round(3)
    out["recurrence_rate"] = out["recurrence_rate"].round(2)
    return out.sort_values(["days_trending", "total_keyword_mentions"], ascending=False).reset_index(drop=True)


df = load_data()

settings.header("Weekly Trend Summary", "The same dataset rolled up to ISO weeks: which topics persisted, how the category mix shifted, and how sentiment moved day by day.")

# ---- sidebar: theme + week selector ---------------------------------------------
settings.brand_sidebar()
settings.render_theme_toggle()
weeks = df.drop_duplicates("week").sort_values("week_start", ascending=False)
week_labels = {
    r.week: f"{r.week}  ({r.week_start.strftime('%d %b')} – {(r.week_start + pd.Timedelta(days=6)).strftime('%d %b %Y')})"
    for r in weeks.itertuples()
}
week = st.sidebar.selectbox("Week", list(week_labels), index=0, format_func=week_labels.get)
wk_all = df[df["week"] == week]
prev_week = weeks[weeks["week_start"] < wk_all["week_start"].iloc[0]]["week"].head(1)
cats = settings.selected_categories()
wk = wk_all[wk_all["category"].astype(str).isin(cats)]
prev = df[(df["week"] == prev_week.iloc[0]) & df["category"].astype(str).isin(cats)] if len(prev_week) else pd.DataFrame()
settings.filter_banner(len(wk_all), len(wk))
if wk.empty:
    st.warning("No trends match the selected categories for this week. Adjust them on the Settings page.")
    st.stop()

summary = weekly_topic_summary(wk)
st.sidebar.markdown("---")
st.sidebar.download_button(
    "Download weekly summary (CSV)",
    data=summary.to_csv(index=False).encode("utf-8"),
    file_name=f"tech_trends_weekly_{week}.csv",
    mime="text/csv",
)

# ---- headline metrics (with week-on-week deltas where a previous week exists) ---------
def delta(cur: float, prv: float | None, fmt: str) -> str | None:
    return None if prv is None else fmt.format(cur - prv)

n_days = wk["date"].nunique()
n_topics = wk["topic"].nunique()
avg_sent = wk["sentiment_score"].mean()
persist = (summary["days_trending"] >= 3).sum()
p_topics = prev["topic"].nunique() if len(prev) else None
p_sent = prev["sentiment_score"].mean() if len(prev) else None
p_persist = (weekly_topic_summary(prev)["days_trending"] >= 3).sum() if len(prev) else None

partial = n_days < 7
if partial:
    st.info(f"Partial week: {n_days} of 7 days collected so far. Week-on-week deltas are hidden until the week is complete.")
    p_topics = p_sent = p_persist = None

c1, c2, c3, c4 = st.columns(4)
c1.metric("Days collected", n_days)
c2.metric("Distinct topics", n_topics, delta(n_topics, p_topics, "{:+d} vs prior week"))
c3.metric("Avg sentiment", f"{avg_sent:+.2f}", delta(avg_sent, p_sent, "{:+.2f} vs prior week"))
c4.metric("Topics trending 3+ days", int(persist), delta(int(persist), p_persist, "{:+d} vs prior week"))

# ---- persistence leaders ------------------------------------------------------
st.subheader("Most persistent topics this week")
top = summary.head(10)
fig, ax = plt.subplots(figsize=(8, 4))
ax.barh(top["topic"][::-1], top["days_trending"][::-1], color=settings.accent())
ax.set(xlabel="days in the top-10 this week", xlim=(0, 7))
for i, v in enumerate(top["days_trending"][::-1]):
    ax.text(v + 0.1, i, str(v), va="center", fontsize=9, color=settings.TEXT[settings.current_theme()])
settings.style_figure(fig, ax)
fig.tight_layout()
st.pyplot(fig, width="stretch")

# ---- category mix + daily sentiment ----------------------------------------------
col_a, col_b = st.columns(2)
with col_a:
    st.subheader("Category mix (trend-days)")
    mix = wk["category"].value_counts()
    if len(prev):
        prev_mix = prev["category"].value_counts()
        mix_df = pd.DataFrame({"this week": mix, "prior week": prev_mix}).fillna(0).astype(int)
        st.bar_chart(mix_df, height=320)
    else:
        st.bar_chart(mix, height=320)
with col_b:
    st.subheader("Average sentiment by day")
    daily = wk.groupby(wk["date"].dt.date)["sentiment_score"].mean()
    daily.index = [d.strftime("%a %d") for d in daily.index]
    st.line_chart(daily, height=320)

# ---- weekly keyword cloud ---------------------------------------------------------
st.subheader("Keyword cloud for the week")
weights: dict[str, int] = {}
for kws, freq in zip(wk["keywords"], wk["keyword_frequency"]):
    for kw in kws.split("|"):
        weights[kw] = weights.get(kw, 0) + int(freq)
wc = WordCloud(width=1200, height=350, **settings.wordcloud_kwargs()).generate_from_frequencies(weights)
fig2, ax2 = plt.subplots(figsize=(12, 3.5))
ax2.imshow(wc, interpolation="bilinear"); ax2.axis("off")
settings.style_figure(fig2, ax2)
st.pyplot(fig2, width="stretch")

# ---- summary table -------------------------------------------------------------
st.subheader("Per-topic summary")
st.dataframe(summary, hide_index=True, width="stretch")
