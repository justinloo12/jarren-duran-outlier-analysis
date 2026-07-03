"""Shared visual style for all figures — one cohesive, sleek look.

Import `apply()` once, then use `style(ax)` / `titled(ax, ...)` / the palette
so every chart shares fonts, colors, spacing, and de-cluttered axes.
"""
from __future__ import annotations

import matplotlib as mpl

# palette (Red Sox-informed, muted)
NAVY = "#0C2340"
RED = "#BD3039"
GREEN = "#2E7D32"
AMBER = "#C8892F"
TEAL = "#2A7DA3"
GREY = "#9AA0A6"
MUTED = "#5B6472"
TEXT = "#20232A"
GRID = "#EAEDF1"
SPINE = "#CBD1DA"
FAINT = "#F4F5F7"


def apply():
    mpl.rcParams.update({
        "figure.dpi": 150, "savefig.dpi": 150,
        "figure.facecolor": "white", "savefig.facecolor": "white",
        "savefig.bbox": "tight", "savefig.pad_inches": 0.28,
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
        "font.size": 11, "text.color": TEXT,
        "axes.facecolor": "white", "axes.edgecolor": SPINE, "axes.linewidth": 1.0,
        "axes.axisbelow": True, "axes.labelcolor": MUTED, "axes.labelsize": 11,
        "axes.titlesize": 14, "axes.titleweight": "bold", "axes.titlecolor": NAVY,
        "grid.color": GRID, "grid.linewidth": 1.0,
        "xtick.color": MUTED, "ytick.color": MUTED,
        "xtick.labelsize": 10, "ytick.labelsize": 10,
        "legend.frameon": False, "legend.fontsize": 9.5,
        "legend.handlelength": 1.4, "legend.handletextpad": 0.6,
        "legend.columnspacing": 1.2,
    })


def style(ax, grid_axis="y"):
    """Despine, soft grid on one axis only, no tick marks."""
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(SPINE)
    ax.spines["bottom"].set_color(SPINE)
    ax.grid(False)
    ax.grid(axis=grid_axis, color=GRID, linewidth=1.0)
    ax.tick_params(length=0)
    return ax


def titled(ax, title, subtitle=None):
    """Bold left title with an optional thin grey subtitle beneath it."""
    ax.set_title(title, loc="left", pad=26 if subtitle else 12)
    if subtitle:
        ax.text(0.0, 1.016, subtitle, transform=ax.transAxes, fontsize=9.8,
                color=MUTED, ha="left", va="bottom")
