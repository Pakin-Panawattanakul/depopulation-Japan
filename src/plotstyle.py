"""Shared matplotlib style (reference palette from the dataviz skill, light mode).

Categorical slots are assigned in fixed order. Only the first three are used in charts
where every series can sit next to every other (scatter, multi-line), because only those
three stay distinguishable for colour-blind readers in all pairings.
"""

from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

from estat import ROOT

FIG_DIR = ROOT / "reports" / "figures"

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
NEUTRAL_MID = "#f0efec"
BLUE_RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
RED_RAMP = ["#fbdada", "#f4a9a9", "#ec7a7a", "#e34948", "#c23736", "#9a2a29", "#701d1d"]

# Diverging: red = decline, gray = no change, blue = growth.
DIVERGING = LinearSegmentedColormap.from_list("decline_growth", RED_RAMP[::-1][1:] + [NEUTRAL_MID] + BLUE_RAMP[1:])


def apply() -> None:
    mpl.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "font.family": "sans-serif", "font.size": 10,
        "font.sans-serif": ["Noto Sans CJK JP", "IPAexGothic", "DejaVu Sans"],
        "text.color": INK, "axes.labelcolor": INK_2, "xtick.color": MUTED, "ytick.color": MUTED,
        "axes.edgecolor": BASELINE, "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
        "axes.titlesize": 12, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "lines.linewidth": 2, "lines.markersize": 4, "legend.frameon": False,
        "figure.dpi": 110, "savefig.dpi": 160, "savefig.bbox": "tight",
    })


def save(fig, name: str) -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_DIR / f"{name}.png")
    plt.close(fig)
    print(f"  saved reports/figures/{name}.png")
