"""
Generate the article cover image from the dataset itself.

Every dot is one trend-day: columns are collection days, rows are rank slots.
A filled dot recurred the following day; a pale dot faded. The newest column is
unlabelled by construction, so it is drawn as an outline — which is precisely the
question the project asks, rendered as the picture.

Run:  python src/make_cover.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
# Palette, fonts and the name come from the brand module — see docs/BRAND.md.
from brand import ACCENT, FADED, INK, INK_SOFT, NAME, SURFACE, UNKNOWN, pick_font  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "tech_trends.parquet"
OUT = ROOT / "outputs"

TITLE = NAME
SUBTITLE = "Which technology trends are still here tomorrow?"


SIZES = {                    # name: (inches, dpi, days shown) -> pixel size
    "cover_medium":   ((14.00, 7.00), 100, None),   # 1400 x 700  — article header
    "cover_linkedin": ((12.00, 6.27), 100, None),   # 1200 x 627  — link preview
    "cover_square":   (( 8.00, 8.00), 100, 22),     # 800 x 800   — avatar / card
}


def load_grid(max_days: int | None = None) -> pd.DataFrame:
    df = pd.read_parquet(DATA)[["date", "rank", "recurred_next_day"]].copy()
    if max_days:                                  # narrow formats need fewer columns to breathe
        keep = sorted(df["date"].unique())[-max_days:]
        df = df[df["date"].isin(keep)]
    return df


def draw(grid: pd.DataFrame, figsize: tuple[float, float], square: bool = False) -> plt.Figure:
    font = pick_font()
    fig = plt.figure(figsize=figsize, facecolor=SURFACE)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_facecolor(SURFACE); ax.axis("off")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)

    days = sorted(grid["date"].unique())
    x_of = {d: i for i, d in enumerate(days)}
    n_days, n_ranks = len(days), int(grid["rank"].max())

    # Plot area: full-bleed horizontally with generous margins, sitting below the type.
    left, right = 0.075, 0.925
    if square:
        bottom, top, title_y, sub_y = 0.255, 0.66, 0.855, 0.795
        title_size, sub_size, cap_size, dot = 34, 13.5, 8.5, 46
        caption = (f"One dot per trending topic per day  ·  {len(grid):,} trend-days\n"
                   "filled = still trending tomorrow  ·  outlined = not yet known")
    else:
        bottom, top, title_y, sub_y = 0.25, 0.645, 0.83, 0.77
        title_size, sub_size, cap_size, dot = 42, 16, 10, 28
        caption = (f"Each dot is one trending topic on one day  ·  {len(grid):,} trend-days  ·  "
                   "filled = still trending tomorrow  ·  outlined = not yet known")

    def px(i): return left + (right - left) * (i / max(n_days - 1, 1))
    def py(r): return top - (top - bottom) * ((r - 1) / max(n_ranks - 1, 1))

    latest = days[-1]
    for row in grid.itertuples():
        x, y = px(x_of[row.date]), py(row.rank)
        if row.date == latest or pd.isna(row.recurred_next_day):
            ax.scatter(x, y, s=dot, facecolors="none", edgecolors=UNKNOWN, linewidths=0.9, zorder=3)
        elif int(row.recurred_next_day) == 1:
            ax.scatter(x, y, s=dot, color=ACCENT, linewidths=0, zorder=3)
        else:
            ax.scatter(x, y, s=dot, color=FADED, linewidths=0, zorder=2)

    # Type block. Left-aligned, generous whitespace, nothing centred.
    ax.text(left, title_y, TITLE, color=INK, fontsize=title_size, fontweight="bold",
            va="baseline", ha="left", family=font)
    ax.text(left, sub_y, SUBTITLE, color=INK_SOFT, fontsize=sub_size,
            va="top", ha="left", family=font)

    # One quiet caption carries the encoding, so colour is never the only cue.
    ax.text(left, bottom - 0.075, caption, color=INK_SOFT, fontsize=cap_size,
            va="top", ha="left", family=font, linespacing=1.6)
    return fig


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for name, (figsize, dpi, max_days) in SIZES.items():
        fig = draw(load_grid(max_days), figsize, square=name.endswith("square"))
        path = OUT / f"{name}.png"
        fig.savefig(path, dpi=dpi, facecolor=SURFACE)
        plt.close(fig)
        print(f"{path.name}: {int(figsize[0]*dpi)} x {int(figsize[1]*dpi)}")
