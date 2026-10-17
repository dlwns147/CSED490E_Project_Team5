"""Illustration for slide 5: the real 10-point instance (hull task, inst 1) and its convex hull (6 corners).
Run: /opt/conda/bin/python poc/make_slide5_hull.py"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "figs", "slide5_hull.png")
P = [(20, -40), (-26, -18), (-18, -12), (-50, 38), (-18, 42), (58, 16), (-30, -26), (6, 58), (52, -36), (50, 14)]


def hull(pts):
    pts = sorted(set(pts))
    cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]


H = hull(P)
fig, ax = plt.subplots(figsize=(3.6, 3.6))
fig.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02)
ax.fill([p[0] for p in H], [p[1] for p in H], color="#e2f0d9", zorder=1)
ax.plot([p[0] for p in H + H[:1]], [p[1] for p in H + H[:1]], color="#70ad47", lw=2.5, zorder=2)
ax.scatter([p[0] for p in P], [p[1] for p in P], s=45, color="#404040", zorder=3)
ax.scatter([p[0] for p in H], [p[1] for p in H], s=110, facecolor="none", edgecolor="#38761d", lw=2, zorder=4)
ax.set_aspect("equal"); ax.axis("off")
fig.savefig(OUT, dpi=220, facecolor="white"); print(OUT, len(H), "corners")
