"""
Generate the InsightMetric "Signal Map" logo.

A dot-matrix world map in the neutral tone, with five accent nodes for the domains the
project watches — AI, Cloud, Cybersecurity, Developer Tools, Open Source — each ringed by
two fading pulses. Monochrome plus the single accent, per docs/BRAND.md.

The mark reduces in one step: below roughly 64px a world map is illegible, so the small
sizes drop to a single pulse node, which is the map's atomic element.

Assets are drawn on a transparent background so one file serves both the light and the
dark theme. The social preview is the exception — GitHub composites it on white, so it is
drawn on SURFACE.

Run:  python src/make_logo.py
Out:  outputs/logo.{svg,png}            horizontal lockup: mark, wordmark, tagline
      outputs/logo_wordmark.{svg,png}   lockup without the tagline, for tight spaces
      outputs/logo_mark.{svg,png}       the Signal Map alone
      outputs/logo_compact.{svg,png}    node + wordmark, for small heights (app sidebar)
      outputs/logo_avatar.{svg,png}     square pulse node, for avatars
      outputs/favicon.png               64x64 pulse node
      outputs/logo_social.png           1280x640 repository social preview
      outputs/*_dark.{svg,png}          the same lockups with dark-theme ink
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from brand import (  # noqa: E402
    ACCENT,
    DOMAINS,
    INK,
    INK_DARK,
    INK_SOFT,
    INK_SOFT_DARK,
    NAME,
    SURFACE,
    TAGLINE,
    UNKNOWN,
    pick_font,
)
from world import land_dots  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"

# Drawn extent. Cropping Antarctica and the empty Pacific edge puts the landmass in the
# middle of the frame and gives the mark its proportion.
LON = (-168, 178)
LAT = (-56, 80)
ASPECT = (LON[1] - LON[0]) / (LAT[1] - LAT[0])     # ~2.54:1

# Keep text as vector outlines so the SVG renders identically without the font installed.
matplotlib.rcParams["svg.fonttype"] = "path"


# ---------------------------------------------------------------------------
# drawing primitives
# ---------------------------------------------------------------------------
def draw_map(ax, dot_size: float, node_size: float, pulses: bool = True) -> None:
    """Draw the Signal Map into an existing axes, in lon/lat coordinates."""
    dots = land_dots(step=3.0, lon_range=LON, lat_range=LAT)
    ax.scatter([d[0] for d in dots], [d[1] for d in dots],
               s=dot_size, color=UNKNOWN, linewidths=0, zorder=2)
    for _name, lon, lat in DOMAINS:
        draw_node(ax, lon, lat, node_size, pulses=pulses)
    ax.set_xlim(*LON)
    ax.set_ylim(*LAT)
    ax.set_aspect("equal")
    ax.axis("off")


def draw_node(ax, x: float, y: float, size: float, pulses: bool = True) -> None:
    """One signal node: a filled dot inside two fading rings."""
    if pulses:
        for scale, alpha, lw in ((3.6, 0.55, 1.3), (7.2, 0.26, 1.1)):
            ax.scatter([x], [y], s=size * scale, facecolors="none", edgecolors=ACCENT,
                       alpha=alpha, linewidths=lw, zorder=3)
    # A halo in the surface colour lifts the node clear of the dots behind it.
    ax.scatter([x], [y], s=size * 2.1, color=SURFACE, linewidths=0, zorder=4)
    ax.scatter([x], [y], s=size, color=ACCENT, linewidths=0, zorder=5)


def _figure(w: float, h: float, background: str | None):
    fig = plt.figure(figsize=(w, h))
    if background:
        fig.patch.set_facecolor(background)
    else:
        fig.patch.set_alpha(0.0)
    return fig


def _save(fig, stem: str, dpi: int, formats: tuple[str, ...], background: str | None) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for ext in formats:
        path = OUT / f"{stem}.{ext}"
        fig.savefig(path, dpi=dpi, transparent=background is None,
                    facecolor=background or "none")
        print(f"  wrote {path.relative_to(ROOT)}")
    plt.close(fig)


# ---------------------------------------------------------------------------
# assets
# ---------------------------------------------------------------------------
def mark(stem: str = "logo_mark", width: float = 9.0, dpi: int = 100,
         background: str | None = None, formats: tuple[str, ...] = ("svg", "png")) -> None:
    """The Signal Map alone, at its natural proportion with an even margin."""
    pad = 0.04
    height = width / ASPECT * (1 + 2 * pad) / (1 + 2 * pad)
    fig = _figure(width, height + 2 * pad * width / ASPECT, background)
    ax = fig.add_axes([pad, pad, 1 - 2 * pad, 1 - 2 * pad])
    scale = width / 9.0
    draw_map(ax, dot_size=11 * scale ** 2, node_size=110 * scale ** 2)
    _save(fig, stem, dpi, formats, background)


def avatar(stem: str = "logo_avatar", size: float = 5.12, dpi: int = 100,
           background: str | None = None, formats: tuple[str, ...] = ("svg", "png")) -> None:
    """Square reduction: a single pulse node. Legible down to 16px, unlike the map."""
    fig = _figure(size, size, background)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(-1, 1)
    ax.set_ylim(-1, 1)
    ax.set_aspect("equal")
    ax.axis("off")
    # Circles in data coordinates, so the proportions hold at every output size.
    for radius, alpha, lw in ((0.50, 0.55, 0.055), (0.80, 0.26, 0.045)):
        ax.add_patch(plt.Circle((0, 0), radius, fill=False, edgecolor=ACCENT, alpha=alpha,
                                linewidth=lw * size * dpi / 4.0, zorder=2))
    ax.add_patch(plt.Circle((0, 0), 0.24, color=ACCENT, linewidth=0, zorder=3))
    _save(fig, stem, dpi, formats, background)


def compact(stem: str = "logo_compact", width: float = 6.0, dpi: int = 200,
            background: str | None = None, formats: tuple[str, ...] = ("svg", "png"),
            ink: str = INK) -> None:
    """Pulse node plus wordmark, no map — the lockup for small heights.

    Streamlit renders a sidebar logo at roughly 24px tall, well under the size at which the
    map is legible, so the reduction rule applies: drop to the node.
    """
    font = pick_font()
    height = width * 0.20
    fig = _figure(width, height, background)

    ax = fig.add_axes([0.005, 0.02, height / width * 0.96, 0.96])
    ax.set_xlim(-1, 1)
    ax.set_ylim(-1, 1)
    ax.set_aspect("equal")
    ax.axis("off")
    for radius, alpha, lw in ((0.50, 0.55, 0.055), (0.80, 0.26, 0.045)):
        ax.add_patch(plt.Circle((0, 0), radius, fill=False, edgecolor=ACCENT, alpha=alpha,
                                linewidth=lw * height * dpi / 4.0, zorder=2))
    ax.add_patch(plt.Circle((0, 0), 0.24, color=ACCENT, linewidth=0, zorder=3))

    fig.text(0.235, 0.50, NAME, ha="left", va="center",
             fontsize=42, fontname=font, color=ink, fontweight="medium")
    _save(fig, stem, dpi, formats, background)


def lockup(stem: str = "logo", width: float = 13.2, dpi: int = 100,
           background: str | None = None, formats: tuple[str, ...] = ("svg", "png"),
           tagline: bool = True, ink: str = INK, ink_soft: str = INK_SOFT) -> None:
    """Horizontal lockup: mark on the left, wordmark and tagline on the right."""
    font = pick_font()
    height = width * 0.215
    fig = _figure(width, height, background)

    # Sized so the map's own aspect fills the box exactly — no invisible padding.
    map_w = 0.315
    map_h = (map_w * width / ASPECT) / height
    fig.add_axes([0.015, (1 - map_h) / 2, map_w, map_h])
    draw_map(fig.axes[0], dot_size=6.0, node_size=58)

    x = 0.345
    fig.text(x, 0.635 if tagline else 0.50, NAME, ha="left", va="center",
             fontsize=66, fontname=font, color=ink, fontweight="medium")
    if tagline:
        # A short accent rule ties the tagline back to the nodes.
        fig.add_artist(plt.Line2D([x, x + 0.030], [0.255, 0.255],
                                  color=ACCENT, linewidth=2.6, solid_capstyle="butt"))
        fig.text(x + 0.048, 0.25, TAGLINE.upper(), ha="left", va="center",
                 fontsize=21, fontname=font, color=ink_soft)
    _save(fig, stem, dpi, formats, background)


def social(stem: str = "logo_social", dpi: int = 100) -> None:
    """1280x640 preview card on the light surface, for the repository settings."""
    font = pick_font()
    w, h = 12.8, 6.4
    fig = _figure(w, h, SURFACE)
    map_w = 0.52
    map_h = (map_w * w / ASPECT) / h
    fig.add_axes([(1 - map_w) / 2, 0.50, map_w, map_h])
    draw_map(fig.axes[0], dot_size=8.0, node_size=88)
    fig.text(0.5, 0.30, NAME, ha="center", va="center",
             fontsize=58, fontname=font, color=INK, fontweight="medium")
    fig.text(0.5, 0.185, TAGLINE.upper(), ha="center", va="center",
             fontsize=19, fontname=font, color=INK_SOFT)
    _save(fig, stem, dpi, ("png",), SURFACE)


if __name__ == "__main__":
    print(f"Rendering the Signal Map with {pick_font()}")
    lockup()
    lockup(stem="logo_wordmark", tagline=False, width=11.4)
    mark()
    compact()
    avatar()
    # Dark-theme type. The mark and the accent are unchanged; only the ink moves.
    lockup(stem="logo_dark", ink=INK_DARK, ink_soft=INK_SOFT_DARK)
    lockup(stem="logo_wordmark_dark", tagline=False, width=11.4, ink=INK_DARK)
    compact(stem="logo_compact_dark", ink=INK_DARK)
    avatar(stem="favicon", size=0.64, dpi=100, formats=("png",))
    social()
    print("Done.")
