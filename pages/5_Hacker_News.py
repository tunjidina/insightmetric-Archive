"""
Hacker News page: trending stories by engagement, cross-story themes, and how a
theme's engagement moved over the collected days. Data comes from
src/hn_trending.py (hn_stories.parquet, hn_trending.parquet).
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import settings  # noqa: E402

settings.page_config("Hacker News")
settings.brand_sidebar()
settings.render_theme_toggle()

STORIES = ROOT / "data" / "hn_stories.parquet"
THEMES = ROOT / "data" / "hn_trending.parquet"

settings.header("Hacker News Trending", "Front-page stories ranked by engagement (points + ½ comments + 5 × points-per-hour) and the keywords that span several stories at once.")

if not STORIES.exists():
    st.info("No Hacker News log yet. Run `python src/hn_trending.py` or the live collector to create data/hn_stories.parquet.")
    st.stop()


@st.cache_data
def load():
    stories = pd.read_parquet(STORIES); stories["date"] = pd.to_datetime(stories["date"])
    themes = pd.read_parquet(THEMES) if THEMES.exists() else pd.DataFrame()
    if len(themes):
        themes["date"] = pd.to_datetime(themes["date"])
    return stories, themes


stories, themes = load()
days = sorted(stories["date"].dt.date.unique(), reverse=True)
day = st.sidebar.selectbox("Day", days, index=0, format_func=lambda d: d.strftime("%a %d %b %Y"))
today = stories[stories["date"].dt.date == day].sort_values("score", ascending=False)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Front-page stories", len(today))
m2.metric("Total points", int(today["points"].sum()))
m3.metric("Total comments", int(today["comments"].sum()))
fastest = today.sort_values("points_per_hour", ascending=False).head(1)
m4.metric("Fastest riser", f"{fastest['points_per_hour'].iloc[0]:.0f} pts/h" if len(fastest) else "n/a",
          fastest["title"].iloc[0][:40] + "…" if len(fastest) else None, delta_color="off")

# ---- stories ------------------------------------------------------------------------
st.subheader(f"Trending stories · {day.strftime('%d %B %Y')}")
st.dataframe(
    today[["score", "points", "comments", "points_per_hour", "age_hours", "title", "comments_url"]],
    hide_index=True, width="stretch",
    column_config={"comments_url": st.column_config.LinkColumn("discussion", display_text="HN thread"),
                   "points_per_hour": st.column_config.NumberColumn("pts / hour", format="%.1f"),
                   "age_hours": st.column_config.NumberColumn("age (h)", format="%.1f")},
)

# ---- points vs comments scatter: what is discussed vs what is merely upvoted -----------------
col_a, col_b = st.columns(2)
with col_a:
    st.subheader("Upvoted vs discussed")
    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.scatter(today["points"], today["comments"], s=30 + 3 * today["points_per_hour"].fillna(0), color=settings.accent(), alpha=0.75)
    for r in today.head(6).itertuples():
        ax.annotate(r.title[:28] + ("…" if len(r.title) > 28 else ""), (r.points, r.comments), fontsize=7,
                    xytext=(4, 4), textcoords="offset points", color=settings.TEXT[settings.current_theme()])
    ax.set_xlabel("points"); ax.set_ylabel("comments"); ax.grid(alpha=0.2)
    settings.style_figure(fig, ax); fig.tight_layout()
    st.pyplot(fig, width="stretch")
    st.caption("Marker size = points per hour. Stories far above the diagonal are being argued about; far below, quietly upvoted.")
with col_b:
    st.subheader("Cross-story themes")
    th = themes[themes["date"].dt.date == day].sort_values("score", ascending=False) if len(themes) else pd.DataFrame()
    if len(th):
        st.dataframe(th[["keyword", "stories", "total_points", "total_comments", "top_story"]], hide_index=True, width="stretch")
    else:
        st.caption("No keyword spanned two or more front-page stories on this day.")

# ---- theme history --------------------------------------------------------------------
if len(themes) and themes["date"].nunique() > 1:
    st.subheader("Theme history")
    options = themes.groupby("keyword")["score"].sum().sort_values(ascending=False).head(25).index.tolist()
    pick = st.multiselect("Keywords", options, default=options[:5])
    if pick:
        hist = themes[themes["keyword"].isin(pick)].pivot_table(index="date", columns="keyword", values="total_points", aggfunc="sum").fillna(0)
        st.line_chart(hist, height=300)
        st.caption("Total front-page points carried by each keyword, per collection day.")
