"""
GitHub releases page: the structured release log kept by src/github_releases.py.

Shows recent releases across the watchlist, release cadence per repository,
and lets you filter by repository and release kind.
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

settings.page_config("Releases")
settings.brand_sidebar()
settings.render_theme_toggle()

RELEASES = ROOT / "data" / "releases.parquet"

settings.header("GitHub Releases", "Releases from the watched repositories (src/github_releases.py). Non-pre-release entries also feed the Daily Trends page as a 'github' source.")

if not RELEASES.exists():
    st.info("No release log yet. Run `python src/github_releases.py` (or the live collector with INCLUDE_GITHUB = True) to create data/releases.parquet.")
    st.stop()


@st.cache_data
def load() -> pd.DataFrame:
    df = pd.read_parquet(RELEASES)
    df["published_at"] = pd.to_datetime(df["published_at"], utc=True)
    df["release_date"] = pd.to_datetime(df["release_date"])
    return df.sort_values("published_at", ascending=False)


df = load()

# ---- filters ---------------------------------------------------------------------
f1, f2, f3 = st.columns([2, 1, 1])
repos = f1.multiselect("Repositories", sorted(df["repo"].unique()), default=sorted(df["repo"].unique()))
kinds = f2.multiselect("Kind", ["major", "minor", "patch", "other"], default=["major", "minor", "patch", "other"])
show_pre = f3.toggle("Include pre-releases", value=False)
view = df[df["repo"].isin(repos) & df["kind"].isin(kinds)]
if not show_pre:
    view = view[~view["is_prerelease"]]

# ---- headline metrics -----------------------------------------------------------
last7 = view[view["release_date"] >= view["release_date"].max() - pd.Timedelta(days=7)] if len(view) else view
m1, m2, m3, m4 = st.columns(4)
m1.metric("Releases logged", len(view))
m2.metric("Repos active in last 7 days", last7["repo"].nunique())
m3.metric("Major releases", int((view["kind"] == "major").sum()))
m4.metric("Latest", view["release_date"].max().strftime("%d %b %Y") if len(view) else "n/a")

# ---- recent releases table -----------------------------------------------------------
st.subheader("Recent releases")
st.dataframe(
    view[["release_date", "repo", "tag", "kind", "is_prerelease", "notes_length", "url"]].head(50),
    hide_index=True, width="stretch",
    column_config={"url": st.column_config.LinkColumn("release", display_text="open"),
                   "release_date": st.column_config.DateColumn("date", format="DD MMM YYYY")},
)

# ---- cadence chart --------------------------------------------------------------------
st.subheader("Release cadence by repository")
if len(view):
    cadence = view.groupby(["repo", "kind"]).size().unstack(fill_value=0).reindex(columns=["major", "minor", "patch", "other"], fill_value=0)
    cadence = cadence.loc[cadence.sum(axis=1).sort_values().index]
    fig, ax = plt.subplots(figsize=(9, max(3, 0.4 * len(cadence))))
    left = pd.Series(0, index=cadence.index)
    colours = {"major": brand.CONTRAST, "minor": settings.accent(),
               "patch": brand.UNKNOWN, "other": brand.FADED}
    for kind in cadence.columns:
        ax.barh(cadence.index, cadence[kind], left=left, color=colours[kind], label=kind)
        left = left + cadence[kind]
    ax.set_xlabel("releases in log"); ax.legend(frameon=False, labelcolor=settings.TEXT[settings.current_theme()])
    settings.style_figure(fig, ax); fig.tight_layout()
    st.pyplot(fig, width="stretch")
    st.caption("The Atom feeds expose roughly the ten most recent releases per repository, so the log deepens over time as the collector runs daily.")
