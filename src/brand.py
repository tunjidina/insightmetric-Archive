"""
InsightMetric brand constants — the single source of truth in code.

docs/BRAND.md is the human-readable specification; this module is the machine-readable
half of it. Anything that renders the name, the tagline, the description or the palette
imports from here rather than hard-coding a string, so the brand can only drift in one
place.

Run:  python src/brand.py     # print the approved strings for copy-paste
"""
from __future__ import annotations

# --- identity ---------------------------------------------------------------
NAME = "InsightMetric"                       # singular; never "InsightMetrics"
TAGLINE = "Tech Trends, Minus the Noise."    # always with the full stop

SHORT_DESCRIPTION = (
    "InsightMetric is a daily tech-trend intelligence system that collects signals from "
    "news, open-source releases and community activity, clusters them into clean topics, "
    "and predicts which ones will recur tomorrow — using simple, transparent models and "
    "reproducible pipelines."
)

# GitHub's About field is capped at 350 characters, so it gets its own cut.
GITHUB_ABOUT = (
    "Tech Trends, Minus the Noise. A daily tech-trend intelligence system: collects signals "
    "from news, open-source releases and community activity, clusters them into clean topics, "
    "and predicts which recur tomorrow. Transparent models, reproducible pipelines, no API keys."
)

# --- palette ----------------------------------------------------------------
# Monochrome plus one accent. Every colour in the project comes from this list.
SURFACE = "#fcfcfb"      # page / chart background
INK = "#0b0b0b"          # primary text
INK_SOFT = "#52514e"     # secondary text
ACCENT = "#2a78d6"       # the single accent — signal, emphasis, series one
FADED = "#dcdbd7"        # structure, landmass, "did not recur"
UNKNOWN = "#b9b8b3"      # not yet observable, tertiary text

# The one permitted second hue, for encodings with exactly two opposed sides: two peer
# categories compared, or a positive-versus-negative coefficient. Blue against orange is
# the standard pair that survives the common forms of colour blindness. It is NOT a second
# brand colour and never appears in the logo, in a heading, or as decoration.
CONTRAST = "#d1682a"

# Dark-mode counterparts. Only the neutrals move; the accent is fixed, which is what
# makes it read as the brand colour rather than as a theme colour.
SURFACE_DARK = "#101113"
INK_DARK = "#f2f1ee"
INK_SOFT_DARK = "#b9b8b3"

PALETTE = {
    "surface": SURFACE, "ink": INK, "ink_soft": INK_SOFT,
    "accent": ACCENT, "contrast": CONTRAST, "faded": FADED, "unknown": UNKNOWN,
    "surface_dark": SURFACE_DARK, "ink_dark": INK_DARK, "ink_soft_dark": INK_SOFT_DARK,
}

# --- typography -------------------------------------------------------------
# Preferred faces in order; the renderer falls back to whatever the machine has, so a
# fresh clone still produces sensible output.
FONT_STACK = ["TeX Gyre Heros", "Helvetica Neue", "Helvetica", "Liberation Sans",
              "Carlito", "Poppins", "DejaVu Sans"]

# --- the five domains on the Signal Map -------------------------------------
# Node positions are chosen for visual balance across the map, not as a claim about
# where any of this work happens. Order fixes the reading order in the legend.
DOMAINS = [
    ("AI",               -122.4,  37.8),
    ("Cloud",              -6.3,  53.3),
    ("Cybersecurity",      34.8,  32.1),
    ("Developer Tools",    77.6,  12.9),
    ("Open Source",       139.7,  35.7),
]


def pick_font() -> str:
    """First available face from FONT_STACK, for matplotlib rendering."""
    from matplotlib import font_manager
    available = {f.name for f in font_manager.fontManager.ttflist}
    return next((f for f in FONT_STACK if f in available), "sans-serif")


if __name__ == "__main__":
    print(f"Name:      {NAME}")
    print(f"Tagline:   {TAGLINE}")
    print(f"\nShort description ({len(SHORT_DESCRIPTION)} chars):\n{SHORT_DESCRIPTION}")
    print(f"\nGitHub About ({len(GITHUB_ABOUT)} chars, limit 350):\n{GITHUB_ABOUT}")
    print("\nPalette:")
    for k, v in PALETTE.items():
        print(f"  {k:<14} {v}")
    print("\nSignal Map nodes:")
    for name, lon, lat in DOMAINS:
        print(f"  {name:<16} {lon:>8.1f}, {lat:>5.1f}")
