"""Task 2 probe: grouped bars to SVG, deterministic, no network.

Run through probe/chart.sh, which blocks sockets before importing matplotlib
and renders twice so the two SVG hashes can be compared.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib import font_manager

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"
OUT = ROOT / "probe" / "out"

INK = "#000000"
GREY_1 = "#4D4D4D"
GREY_3 = "#A8A8A8"
ACCENT = "#2F3E5C"

CATEGORIES = ["Alder", "Birch", "Cedar"]
SERIES = [
    ("Samples recorded", [72, 64, 58], GREY_3),
    ("Not recorded", [28, 36, 42], ACCENT),
]


def register_fonts() -> None:
    for path in sorted(FONTS.glob("Spectral-*.ttf")):
        font_manager.fontManager.addfont(str(path))


def build() -> Path:
    register_fonts()
    plt.rcParams.update(
        {
            "font.family": "Spectral",
            "font.size": 8,
            "svg.fonttype": "none",
            "svg.hashsalt": "bookify-probe-v1",
            "axes.edgecolor": INK,
            "axes.linewidth": 0.5,
            "text.color": INK,
        }
    )

    width = 0.34
    fig, ax = plt.subplots(figsize=(4.4, 2.4))
    for index, (label, values, colour) in enumerate(SERIES):
        offsets = [i + (index - 0.5) * width for i in range(len(CATEGORIES))]
        bars = ax.bar(offsets, values, width=width, color=colour, edgecolor="none", label=label)
        for bar, value in zip(bars, values):
            ax.annotate(
                f"{value}",
                (bar.get_x() + bar.get_width() / 2, value),
                xytext=(0, 2),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=6.5,
                color=GREY_1 if colour == GREY_3 else INK,
            )

    ax.set_xticks(range(len(CATEGORIES)), CATEGORIES)
    ax.set_ylim(0, 105)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_ylabel("Percent")
    ax.yaxis.grid(True, color=GREY_3, linewidth=0.3, alpha=0.7)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.legend(frameon=False, loc="upper right", fontsize=7, handlelength=0.8)

    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "chart.svg"
    fig.savefig(target, format="svg", metadata={"Date": None}, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return target


if __name__ == "__main__":
    path = build()
    print(f"wrote {path}")
    print(f"python: {sys.version.split()[0]}")
    print(f"matplotlib: {matplotlib.__version__}")
