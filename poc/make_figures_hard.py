"""Figures for the hard-benchmark track of PROPOSAL.md (same style as make_figures.py). Run: /opt/conda/bin/python poc/make_figures_hard.py
Numbers are the recorded results: PREREG_H2C.md (Part B), PREREG_N.md (N2, N2b, N3, N4), PREREG_H3.md (H3b / H3c), PREREG_H4.md (H4, H4b).
fig9: contest geometry cost-accuracy frontier; fig10: routing facts compose; fig11: helpers on real problems."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_figures_style as st  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

# ---------- Fig 9: contest geometry, accuracy vs output tokens per problem ----------
F9 = {   # model: [(label, tokens per problem, % solved)]
    "Qwen3-32B": [("no-think", 0.70, 12.1), ("+ 1 repair", 1.49, 18.0), ("x3 + example check", 2.11, 21.2), ("think-1,024", 2.94, 21.8),
                  ("cascade", 3.24, 23.8), ("repair, then escalate", 3.75, 24.9), ("think-1,024 x3 + check", 8.82, 30.2),
                  ("full thinking", 13.71, 29.9)],
    "gpt-oss-20b": [("low", 1.51, 37.7), ("low + 1 repair", 2.30, 44.9), ("low x3 + check", 4.54, 47.9), ("repair, then escalate", 7.29, 51.6),
                    ("cascade to medium", 7.51, 50.3), ("medium", 8.74, 47.1), ("medium x3 + MBR-exec", 26.23, 57.2)],
    "gpt-oss-120b": [("low", 3.25, 46.1), ("low + 1 repair", 4.64, 53.1), ("medium", 6.75, 56.8), ("cascade to medium", 7.02, 56.4),
                     ("repair, then escalate", 7.63, 57.7), ("low x3 + MBR-exec", 9.74, 54.3), ("medium x3 + MBR-exec", 20.26, 62.4),
                     ("high (64k cap, 1 seed)", 29.91, 66.2)],
}
fig, ax = st.new(w=8.4, h=5.0, top=0.74, left=0.11)
for (m, pts), c in zip(F9.items(), (st.S1, st.S2, st.S3)):
    pts = sorted(pts, key=lambda p: p[1])
    xs, ys = [p[1] for p in pts], [p[2] for p in pts]
    best, fx, fy = -1, [], []
    for x, y in zip(xs, ys):   # Pareto frontier (more accuracy for more tokens)
        if y > best:
            best = y; fx.append(x); fy.append(y)
    ax.plot(fx, fy, color=c, lw=1.6, zorder=2)
    for lab, x, y in pts:
        st.dot(ax, x, y, c, size=55, label=m if lab == pts[0][0] else None)
    OFF = {("Qwen3-32B", "no-think"): (6, 4), ("Qwen3-32B", "+ 1 repair"): (5, -12), ("Qwen3-32B", "think-1,024 x3 + check"): (-95, 9),
           ("Qwen3-32B", "full thinking"): (4, -13), ("gpt-oss-20b", "low"): (6, -4), ("gpt-oss-20b", "low + 1 repair"): (-40, 8),
           ("gpt-oss-20b", "low x3 + check"): (4, -13), ("gpt-oss-20b", "medium"): (5, -12), ("gpt-oss-20b", "medium x3 + MBR-exec"): (-75, -15),
           ("gpt-oss-120b", "low"): (5, -12), ("gpt-oss-120b", "low + 1 repair"): (-45, 8), ("gpt-oss-120b", "medium"): (-30, 8),
           ("gpt-oss-120b", "medium x3 + MBR-exec"): (-85, 8), ("gpt-oss-120b", "high (64k cap, 1 seed)"): (-95, 8)}
    for lab, x, y in pts:
        if (m, lab) in OFF:
            ax.annotate(lab, (x, y), textcoords="offset points", xytext=OFF[(m, lab)], fontsize=8, color=st.INK2)
ax.set_xscale("log"); ax.set_xlim(0.6, 40); ax.set_ylim(8, 70); ax.set_xlabel("output tokens per problem (thousands, log scale; all samples and repairs counted)")
ax.set_ylabel("% of 311 problems solved")
ax.set_xticks([0.7, 1, 2, 4, 8, 16, 30]); ax.set_xticklabels(["0.7", "1", "2", "4", "8", "16", "30"])
st.legend_top(ax, 3)
st.finish(ax, "Real contest geometry: which cheap fix pays", "311 Codeforces geometry problems with official tests; line = best accuracy at each cost",
          "fig9_contest_frontier.png")

# ---------- Fig 10: routing facts compose ----------
ARMS = ["none", "documentation\nsnippet", "robust\nsnippet", "file reader", "reader +\ndocs", "reader +\nrobust"]
F10 = {   # % feasible of 56, mean of 2 seeds (float reader; H3b)
    "Qwen3-32B no-think": [0, 0.9, 0.9, 0, 4.5, 2.7],
    "gpt-oss-20b low": [0, 16.1, 15.2, 1.8, 25.0, 43.8],
    "gpt-oss-120b low": [6.3, 34.8, 29.5, 17.9, 86.6, 100.0],
}
fig, ax = st.new(w=8.6, h=4.8, top=0.72, left=0.09)
x = np.arange(len(ARMS)); w = 0.26
for i, ((m, v), c) in enumerate(zip(F10.items(), (st.S1, st.S2, st.S3))):
    ax.bar(x + (i - 1) * w, v, w * 0.92, color=c, label=m, zorder=3)
ax.set_xticks(x); ax.set_xticklabels(ARMS, fontsize=9); ax.set_ylabel("% of 56 Solomon instances feasible"); ax.set_ylim(0, 105)
st.legend_top(ax, 3)
st.finish(ax, "Routing at benchmark scale: the facts only work together", "file layout + integers for OR-Tools + a first solution for tight "
          "windows; Solomon VRPTW, 100 customers", "fig10_routing_facts.png", ygrid=True)

# ---------- Fig 11: helpers on real problems ----------
ROWS = [("Qwen3-32B no-think, 8 related helpers", 12.1, 13.7), ("gpt-oss-20b low, 8 related helpers", 37.7, 33.4),
        ("gpt-oss-20b low, 6 unrelated helpers", 37.7, None), ("gpt-oss-20b low, related + 'most not needed'", 37.7, None),
        ("gpt-oss-120b low, 8 related helpers", 46.1, None)]
H4B = {}   # filled from PREREG_H4.md results when available (see below)
if os.environ.get("H4B"):
    for k, v in zip((2, 3, 4), map(float, os.environ["H4B"].split(","))):
        H4B[k] = v
fig, ax = st.new(w=8.6, h=4.4, top=0.70, left=0.40)
for i, (lab, base, val) in enumerate(ROWS):
    val = H4B.get(i, val)
    if val is None:
        continue
    y = len(ROWS) - 1 - i
    ax.plot([base, val], [y, y], color=st.MUTED, lw=2, zorder=2)
    st.dot(ax, base, y, st.MUTED, size=55, label="no helpers" if i == 0 else None)
    st.dot(ax, val, y, st.S2, size=70, label="with helpers" if i == 0 else None)
ax.set_yticks(range(len(ROWS))); ax.set_yticklabels([r[0] for r in ROWS][::-1], fontsize=9)
ax.set_xlabel("% of 311 problems solved (3 seeds)")
st.legend_top(ax, 2)
st.finish(ax, "Unneeded helpers on real problems", "only gpt-oss-20b at low effort loses (8 related: p = 0.001); any toolbox shortens its reasoning",
          "fig11_helpers_real.png", ygrid=False)
print("figures written to", st.OUT)

# ---------- Fig 12: verify once, reuse: cost curve on 48 held-out Solomon instances (PREREG_V.md V1c) ----------
K = [1, 2, 4, 8, 16, 32, 64]
F12 = {   # pool: (curve % at k, tokens per candidate (k), per-instance % and tokens per instance on the 48 test instances)
    "gpt-oss-120b + docs": ([35, 59, 82, 94, 94], 1.694, 37.5, 1.661),
    "gpt-oss-120b, no facts": ([6, 11, 23, 48, 94], 1.777, 7.3, 1.781),
    "gpt-oss-20b + docs": ([8, 15, 27, 48, 74, 91, 94], 1.608, 18.8, 1.582),
    "gpt-oss-20b, no facts": ([1, 3, 6, 11, 23, 46, 94], 1.675, 0.0, 1.690),
    "Qwen3.8 + reader + robust": ([72, 94, 100, 100, 100], 1.311, 82.3, 1.470),
    "Qwen3-32B + docs": ([0, 0, 1, 1, 2, 5, 10], 1.390, 1.0, 1.375),
}
fig, ax = st.new(w=8.6, h=5.2, top=0.72, left=0.10)
fig.subplots_adjust(bottom=0.18)
cols = [st.S1, st.S1, st.S2, st.S2, st.S3, st.MUTED]
for (lab, (ys, tk, pi, ti)), c, dash in zip(F12.items(), cols, ["-", "--", "-", "--", "-", ":"]):
    xs = [k * tk for k in K[:len(ys)]]
    ax.plot(xs, ys, color=c, lw=1.8, ls=dash, label=lab, zorder=2)
    ax.scatter([48 * ti], [pi], s=60, facecolor=st.SURFACE, edgecolor=c, linewidth=1.8, zorder=3)
ax.set_xscale("log"); ax.set_xlim(1, 130)
ax.set_xticks([1, 2, 4, 8, 16, 32, 64, 128]); ax.set_xticklabels(["1", "2", "4", "8", "16", "32", "64", "128"])
ax.set_xlabel("total output tokens for the 48 instances (thousands, log scale)\n"
              "lines: one program chosen from k candidates and reused;  circles: a new program per instance", fontsize=9)
ax.set_ylabel("% of 48 held-out instances feasible"); ax.set_ylim(-3, 104)
st.legend_top(ax, 3)
st.finish(ax, "Verify once, reuse: one checked program beats a program per instance",
          "48 held-out Solomon instances; facts make working candidates more common, so reuse gets cheaper",
          "fig12_reuse_cost.png")
print("fig12 written")
