"""Illustration for slide 2 of PROPOSAL_slides.pptx: one polygon, moved, turned and flipped (same area). Run: /opt/conda/bin/python poc/make_slide2_shapes.py"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "figs", "slide2_shapes.png")
P = [(0, 0), (4, 0), (4, 1), (2, 1), (2, 3), (3, 3), (3, 4), (0, 4)]       # 8 vertices, asymmetric
V = [P, [(x + 2.5, y + 2) for x, y in P], [(-y, x) for x, y in P], [(-x, y) for x, y in P]]
fig, axes = plt.subplots(1, 4, figsize=(8.8, 1.9))
fig.subplots_adjust(left=0.01, right=0.99, top=0.98, bottom=0.02, wspace=0.12)
for ax, pts in zip(axes, V):
    ax.set_xlim(-5, 7.5); ax.set_ylim(-1, 6.5); ax.set_aspect("equal")
    for t in range(-5, 8):
        ax.axvline(t, color="#eeeeee", lw=0.6, zorder=0)
    for t in range(-1, 7):
        ax.axhline(t, color="#eeeeee", lw=0.6, zorder=0)
    ax.axhline(0, color="#bfbfbf", lw=0.8); ax.axvline(0, color="#bfbfbf", lw=0.8)
    ax.add_patch(Polygon(pts, closed=True, fc="#cfe0f5", ec="#4472c4", lw=2))
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_color("#d9d9d9")
fig.savefig(OUT, dpi=220, facecolor="white"); print(OUT)
