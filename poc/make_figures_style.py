"""Shared style for make_figures*.py (extracted from make_figures.py; importing it draws nothing).
Original docstring:
    /opt/conda/bin/python poc/make_figures.py
Numbers are the pilot results recorded in results/FINDINGS.md; the CO distractor CIs are recomputed from results/co_D_*.jsonl.
Fig 2, 4 (geometry), 7 and 8 numbers come from results/figs_packaging_free.json (poc/rescore_figs.py: packaging-free re-scoring,
paired CIs, MR-select); that script also audits figs 1, 3, 5, 6 against the stored runs."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "figs")
os.makedirs(OUT, exist_ok=True)

# reference palette (dataviz skill, light mode): first three categorical slots validate all-pairs
SURFACE, INK, INK2, GRID, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df", "#a9a8a2"
S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"   # blue, orange, aqua
MODELS = ["Qwen3-8B", "Qwen3-14B", "Qwen3-32B"]

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": "DejaVu Sans", "font.size": 11, "text.color": INK,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "axes.linewidth": 1,
    "xtick.color": INK2, "ytick.color": INK2, "xtick.major.size": 0, "ytick.major.size": 0,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 1, "grid.linestyle": "-",
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False,
})


def finish(ax, title, subtitle, fname, ygrid=True):
    ax.set_axisbelow(True)
    if not ygrid:
        ax.grid(axis="y", visible=False)
    ax.figure.text(0.02, 0.97, title, fontsize=14, weight="semibold", color=INK, va="top")
    ax.figure.text(0.02, 0.905, subtitle, fontsize=10.5, color=INK2, va="top")
    ax.figure.savefig(os.path.join(OUT, fname), dpi=200)
    plt.close(ax.figure)


def new(w=8, h=4.6, top=0.72, left=0.16):
    fig, ax = plt.subplots(figsize=(w, h))
    fig.subplots_adjust(left=left, right=0.95, top=top, bottom=0.14)
    return fig, ax


def legend_top(ax, ncol):
    """legend in its own band above the plot (never over the data)"""
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.02), ncol=ncol, fontsize=9.5, handletextpad=0.4, columnspacing=1.4, borderaxespad=0)


def dot(ax, x, y, color, size=70, **kw):
    ax.scatter(x, y, s=size, color=color, edgecolor=SURFACE, linewidth=2, zorder=3, **kw)


