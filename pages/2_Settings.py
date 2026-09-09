"""
Settings page: choose which categories the Daily Trends and Weekly Summary pages show.

The selection applies immediately for this session; "Save as default" writes
settings.json so it is remembered next time the app starts.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import settings  # noqa: E402
from features import CATEGORIES  # noqa: E402

settings.page_config("Settings")
settings.header("Settings", "Choose the categories shown on the other pages. Changes apply straight away; save to keep them between restarts.")

settings.brand_sidebar()
settings.render_theme_toggle()
current = settings.selected_categories()

# Row counts per category help the reader see what each choice includes/excludes.
counts = pd.read_parquet(ROOT / "data" / "tech_trends.parquet")["category"].value_counts()

st.subheader("Categories")
b1, b2, _ = st.columns([1, 1, 6])
if b1.button("Select all", width="stretch"):
    st.session_state[settings.KEY] = list(CATEGORIES)
    st.rerun()
if b2.button("Clear", width="stretch"):
    st.session_state[settings.KEY] = []
    st.rerun()

chosen = st.multiselect(
    "Shown categories",
    options=list(CATEGORIES),
    default=current,
    format_func=lambda c: f"{c}  ({int(counts.get(c, 0))} rows)",
)
if chosen != current:
    st.session_state[settings.KEY] = chosen
    st.rerun()

if not chosen:
    st.warning("No categories selected: the Daily Trends and Weekly Summary pages will be empty until you pick at least one.")
else:
    st.success(f"Showing {len(chosen)} of {len(CATEGORIES)} categories on the other pages.")

if settings.DEPLOYED:
    st.info("Hosted version: category choices last for your browser session. Theme follows your Streamlit menu (top right).")
    st.stop()

st.subheader("Appearance")
theme_choice = st.radio("Theme", ["light", "dark"], index=0 if st.session_state[settings.THEME_KEY] == "light" else 1,
                        horizontal=True, format_func=str.title)
if theme_choice != st.session_state[settings.THEME_KEY]:
    st.session_state[settings.THEME_KEY] = theme_choice
    settings._write(theme=theme_choice)
    settings.apply_theme(theme_choice)
st.caption("The same toggle is in the sidebar of every page. The choice is saved to settings.json immediately.")

st.subheader("Persistence")
c1, c2, _ = st.columns([1.2, 1.2, 5])
if c1.button("Save as default", type="primary", width="stretch", disabled=not chosen):
    settings.save(chosen)
    st.toast("Saved to settings.json")
if c2.button("Reset to all", width="stretch"):
    settings.reset_saved()
    st.session_state[settings.KEY] = list(CATEGORIES)
    st.rerun()

saved = settings.load_saved()
st.caption(
    "Saved default: " + (", ".join(saved) if len(saved) < len(CATEGORIES) else "all categories")
    + f"  ·  file: `{settings.SETTINGS_PATH.name}`" + ("" if settings.SETTINGS_PATH.exists() else " (not created yet)")
)
