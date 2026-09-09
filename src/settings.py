"""
User settings and branding shared across Streamlit pages.

Two jobs: the category filter and theme (saved to settings.json in the project root so
they persist across restarts), and the branded page chrome — title, favicon, sidebar
logo, header — so that every page is branded identically without repeating itself.

Brand values are imported from brand.py; see docs/BRAND.md.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import streamlit as st
from streamlit import config as st_config

from brand import ACCENT as BRAND_ACCENT
from brand import INK, INK_DARK, NAME, TAGLINE, UNKNOWN
from features import CATEGORIES

ROOT = Path(__file__).resolve().parents[1]
SETTINGS_PATH = ROOT / "settings.json"
ASSETS = ROOT / "outputs"
DEPLOYED = os.environ.get("DEPLOYED") == "1"   # hosted, multi-user: no file persistence, no server-level theme switch
KEY = "selected_categories"
THEME_KEY = "theme"          # "light" | "dark"

# The accent is fixed across themes on purpose — that is what makes it read as the brand
# colour rather than as a theme colour. Only the neutrals move.
ACCENT = {"light": BRAND_ACCENT, "dark": BRAND_ACCENT}
TEXT = {"light": INK, "dark": INK_DARK}


# ---------------------------------------------------------------------------
# persistence
# ---------------------------------------------------------------------------
def _read() -> dict:
    try:
        return json.loads(SETTINGS_PATH.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _write(**updates) -> None:
    if DEPLOYED:
        return                                   # nothing persists on a shared, ephemeral host
    data = _read(); data.update(updates)
    SETTINGS_PATH.write_text(json.dumps(data, indent=2))


def load_saved() -> list[str]:
    """Categories saved to disk, or all categories if nothing is saved."""
    saved = [c for c in _read().get(KEY, []) if c in CATEGORIES]
    return saved or list(CATEGORIES)


def save(categories: list[str]) -> None:
    _write(**{KEY: categories})


def reset_saved() -> None:
    data = _read(); data.pop(KEY, None)
    SETTINGS_PATH.write_text(json.dumps(data, indent=2)) if data else SETTINGS_PATH.unlink(missing_ok=True)


def saved_theme() -> str:
    return _read().get(THEME_KEY, "light")


# ---------------------------------------------------------------------------
# categories
# ---------------------------------------------------------------------------
def selected_categories() -> list[str]:
    """Current selection: session state first, then the saved file, then all."""
    if KEY not in st.session_state:
        st.session_state[KEY] = load_saved()
    return st.session_state[KEY]


def filter_banner(n_rows_before: int, n_rows_after: int) -> None:
    """Small caption on data pages showing whether a category filter is active."""
    sel = selected_categories()
    if len(sel) < len(CATEGORIES):
        st.caption(
            f"Category filter active: {', '.join(sel)} · showing {n_rows_after} of {n_rows_before} rows. "
            "Change it on the Settings page."
        )


# ---------------------------------------------------------------------------
# theme
# ---------------------------------------------------------------------------
def current_theme() -> str:
    return st_config.get_option("theme.base") or "light"


def apply_theme(theme: str) -> None:
    """Switch Streamlit's base theme at runtime. Streamlit reads theme.base on
    every rerun, so setting the option and rerunning is enough. Note this is a
    server-level option: in a multi-user deployment all sessions would switch."""
    if current_theme() != theme:
        st_config.set_option("theme.base", theme)
        st.rerun()


def render_theme_toggle() -> str:
    """Sidebar toggle; call once per page. Applies the saved theme on first load.
    Hidden when deployed: theme.base is server-wide, so one visitor's toggle would
    switch everyone. Visitors use Streamlit's own menu (top right) instead."""
    if DEPLOYED:
        st.session_state.setdefault(THEME_KEY, "light")
        return "light"
    if THEME_KEY not in st.session_state:
        st.session_state[THEME_KEY] = saved_theme()
        apply_theme(st.session_state[THEME_KEY])
    dark = st.sidebar.toggle("Dark mode", value=st.session_state[THEME_KEY] == "dark")
    want = "dark" if dark else "light"
    if want != st.session_state[THEME_KEY]:
        st.session_state[THEME_KEY] = want
        _write(**{THEME_KEY: want})
        apply_theme(want)
    return want


def accent() -> str:
    return ACCENT[current_theme()]


def style_figure(fig, *axes) -> None:
    """Make a matplotlib figure sit naturally on either theme: transparent
    background, theme-coloured text and spines."""
    colour = TEXT[current_theme()]
    fig.patch.set_alpha(0)
    for ax in axes:
        ax.set_facecolor("none")
        ax.tick_params(colors=colour, labelcolor=colour)
        ax.xaxis.label.set_color(colour); ax.yaxis.label.set_color(colour); ax.title.set_color(colour)
        for spine in ax.spines.values():
            spine.set_edgecolor(colour)


def brand_colormap():
    """A single-hue ramp from the neutral to the accent — the palette, as a colormap.
    Charts that need a gradient use this rather than viridis, which would introduce
    colours the brand does not have."""
    from matplotlib.colors import LinearSegmentedColormap
    return LinearSegmentedColormap.from_list("insightmetric", [UNKNOWN, BRAND_ACCENT])


def wordcloud_kwargs() -> dict:
    """Transparent background so the cloud matches the page, in the brand ramp."""
    return {"mode": "RGBA", "background_color": None, "colormap": brand_colormap()}


# ---------------------------------------------------------------------------
# branded page chrome
# ---------------------------------------------------------------------------
def page_config(page: str | None = None, icon: str = "📈") -> None:
    """st.set_page_config with the brand's title format and favicon.

    Titles read "<Page> · InsightMetric", or just the name on the main page. The
    favicon is the generated pulse node when it has been rendered, and the emoji
    otherwise, so the app still starts on a clone that has not run make_logo.py.
    """
    favicon = ASSETS / "favicon.png"
    st.set_page_config(
        page_title=f"{page} · {NAME}" if page else NAME,
        page_icon=str(favicon) if favicon.exists() else icon,
        layout="wide",
    )


def brand_sidebar() -> None:
    """Put the lockup at the top of the sidebar, in the ink for the current theme.

    Streamlit renders this at roughly 24px tall, far below the size at which the Signal
    Map is legible, so this is the compact lockup — pulse node plus wordmark. Silently
    skipped if the assets have not been generated yet.
    """
    suffix = "_dark" if current_theme() == "dark" else ""
    logo, icon = ASSETS / f"logo_compact{suffix}.png", ASSETS / "logo_avatar.png"
    if logo.exists():
        st.logo(str(logo), icon_image=str(icon) if icon.exists() else None)


def header(title: str, caption: str, tagline: bool = False) -> None:
    """Page heading. The tagline appears once per session, on the main page only."""
    st.title(title)
    if tagline:
        st.caption(f"**{TAGLINE}**")
    st.caption(caption)
