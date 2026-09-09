"""
InsightMetric - Daily Trends page.

Tech Trends, Minus the Noise.

Run:  streamlit run Daily_Trends.py
Requires data/tech_trends.parquet (src/collect.py) and models/recurrence_model.joblib (src/train.py).
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from wordcloud import WordCloud

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
import settings  # noqa: E402
from features import FEATURES, build_features  # noqa: E402

DATA_PATH = ROOT / "data" / "tech_trends.parquet"
MODEL_PATH = ROOT / "models" / "recurrence_model.joblib"

settings.page_config()


@st.cache_data
def load_data() -> pd.DataFrame:
    return pd.read_parquet(DATA_PATH)


@st.cache_resource
def load_model():
    return joblib.load(MODEL_PATH)


def badge(p: float) -> str:
    """Traffic-light badge from the recurrence probability."""
    if p >= 0.65:
        return f"🟢 Likely back tomorrow ({p:.0%})"
    if p >= 0.45:
        return f"🟡 Toss-up ({p:.0%})"
    return f"🔴 Likely to fade ({p:.0%})"


df = load_data()
model = load_model()

settings.header(
    "Daily Trends",
    "Topics collected by a lightweight data agent, with a micro-model that predicts which ones will still be trending tomorrow.",
    tagline=True,
)

# ---- sidebar: theme + day selector ----------------------------------------------
settings.brand_sidebar()
settings.render_theme_toggle()
days = sorted(df["date"].dt.date.unique(), reverse=True)
day = st.sidebar.selectbox("Day", days, index=0, format_func=lambda d: d.strftime("%a %d %b %Y"))
st.sidebar.markdown("---")
st.sidebar.download_button(
    "Download full dataset (CSV)",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name="tech_trends.csv",
    mime="text/csv",
)
st.sidebar.download_button(
    "Download full dataset (Parquet)",
    data=DATA_PATH.read_bytes(),
    file_name="tech_trends.parquet",
    mime="application/octet-stream",
)

# ---- score the selected day ----------------------------------------------------
feat = build_features(df)                       # features need history for days_seen_before
today = feat[feat["date"].dt.date == day].copy()
today["p_recur"] = model.predict_proba(today[FEATURES])[:, 1]
n_all = len(today)
today = today[today["category"].astype(str).isin(settings.selected_categories())].sort_values("rank")
settings.filter_banner(n_all, len(today))
if today.empty:
    st.warning("No trends match the selected categories. Adjust them on the Settings page.")
    st.stop()

# ---- headline metrics ---------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Trends today", len(today))
c2.metric("Avg sentiment", f"{today['sentiment_score'].mean():+.2f}")
c3.metric("Avg sources per trend", f"{today['source_count'].mean():.1f}")
c4.metric("Predicted to recur", int((today["p_recur"] >= 0.5).sum()))

# ---- today's trends with prediction badge ----------------------------------------
st.subheader(f"Trends for {day.strftime('%d %B %Y')}")
for _, r in today.iterrows():
    with st.container(border=True):
        left, right = st.columns([3, 1])
        left.markdown(f"**#{r['rank']} {r['topic']}** &nbsp; `{r['category']}`")
        left.write(r["description"])
        hn = f" · HN: {int(r['hn_points'])} pts" if r.get("hn_points", 0) else ""
        left.caption(f"Sources: {r['sources'].replace('|', ', ')} · Keywords: {r['keywords'].replace('|', ', ')}{hn}")
        right.markdown(f"### {badge(r['p_recur'])}")
        if pd.notna(r["recurred_next_day"]):
            right.caption("Actual: " + ("recurred ✅" if r["recurred_next_day"] == 1 else "faded ❌"))

# ---- sentiment bars + keyword cloud ----------------------------------------------
col_a, col_b = st.columns(2)
with col_a:
    st.subheader("Sentiment by trend")
    chart = today.set_index("topic")["sentiment_score"].sort_values()
    st.bar_chart(chart, horizontal=True, height=380)
with col_b:
    st.subheader("Keyword cloud")
    weights = {}
    for kws, freq in zip(today["keywords"], today["keyword_frequency"]):
        for kw in kws.split("|"):
            weights[kw] = weights.get(kw, 0) + int(freq)
    wc = WordCloud(width=800, height=380, **settings.wordcloud_kwargs()).generate_from_frequencies(weights)
    fig, ax = plt.subplots(figsize=(8, 3.8))
    ax.imshow(wc, interpolation="bilinear"); ax.axis("off")
    settings.style_figure(fig, ax)
    st.pyplot(fig, width="stretch")

# ---- raw table ------------------------------------------------------------------
with st.expander("Show today's rows"):
    st.dataframe(
        today[["rank", "topic", "category", "sentiment_score", "keyword_frequency", "source_count", "p_recur", "recurred_next_day"]]
        .rename(columns={"p_recur": "P(recur tomorrow)"}),
        hide_index=True, width="stretch",
    )
