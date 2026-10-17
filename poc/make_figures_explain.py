"""Explanatory figures for the compact PROPOSAL.md (same style as make_figures.py). Run: /opt/conda/bin/python poc/make_figures_explain.py
Numbers are the recorded results (3 seeds unless noted): docs/notes/CHECKS.md, PREREG_N.md (N2, N8, N13), PREREG_N10.md (N12),
PREREG_N14.md (N14c), PREREG_N15.md (N15d). fig0: which fix for which situation; fig13: checks leak; fig14: when to pay for reasoning;
fig15: agreement gate; fig16: adapting a verified program; fig17: solver-library portfolio."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_figures_style as st  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

# ---------- fig0: which fix for which situation (the failure -> fix map as a picture) ----------
fig, ax = plt.subplots(figsize=(9.6, 5.4))
fig.subplots_adjust(left=0.02, right=0.98, top=0.80, bottom=0.03)
ax.set_xlim(0, 100); ax.set_ylim(0, 60); ax.axis("off")


def box(x, y, w, h, text, fill, ink=st.INK, weight="normal"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.5", fc=fill, ec=st.GRID, lw=1.2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=9.5, color=ink, weight=weight, linespacing=1.35)


def arrow(x0, y0, x1, y1, label=None):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=12, lw=1.2, color=st.INK2))
    if label:
        ax.text((x0 + x1) / 2, (y0 + y1) / 2 + 1.2, label, ha="center", va="bottom", fontsize=8.5, color=st.INK2)


LIGHT = "#eef3fb"   # pale tint of S1 for question boxes
ANS = "#ffffff"
box(1, 24, 17, 12, "LLM writes a\nprogram for a\ngeometry or\noptimization task", LIGHT, weight="semibold")
box(25, 44, 22, 10, "Same problem, many\ninstances?", LIGHT)
box(25, 25, 22, 10, "Calls a solver\nlibrary (OR-Tools)?", LIGHT)
box(25, 6, 22, 10, "One-off hard problem", LIGHT)
box(56, 44, 42, 10, "Write once, check on a few instances, reuse\n7% -> 94% feasible on new routing instances (R2)", ANS)
box(56, 25, 42, 10, "Give the exact facts as code (snippet, input reader)\nfull manual .07, 5 exact lines .77-.90 (R1)", ANS)
box(56, 6, 42, 10, "Cheap program + a check; reason more only\nwhen it fails (R3): 98% of the result, 2/3 of the tokens", ANS)
arrow(18, 33, 25, 49); arrow(18, 30, 25, 30); arrow(18, 27, 25, 11)
arrow(47, 49, 56, 49, "yes"); arrow(47, 30, 56, 30, "yes"); arrow(47, 11, 56, 11)
st.finish(ax, "Which fix for which situation", "the project's answer in one picture; every number is measured with exact answers",
          "fig0_fix_flow.png", ygrid=False)

# ---------- fig13: cheap checks never reject a correct program, but accept many wrong ones ----------
ROWS = [("Contest geometry: statement's examples\n(gpt-oss-120b low)", 24), ("Contest geometry: statement's examples\n(gpt-oss-120b medium)", 37),
        ("Generated geometry: symmetry check\n(Qwen3-32B with helpers)", 29), ("Optimization, solver programs:\nfeasibility (gpt-oss-120b)", 20),
        ("Optimization, plain-Python programs:\nfeasibility (gpt-oss-120b)", 79)]
fig, ax = st.new(w=8.6, h=4.6, top=0.74, left=0.38)
ys = list(range(len(ROWS)))[::-1]
ax.barh(ys, [r[1] for r in ROWS], height=0.55, color=st.S1, zorder=3)
for y, (_, v) in zip(ys, ROWS):
    ax.text(v + 1.2, y, f"{v}%", va="center", fontsize=10, color=st.INK)
ax.set_yticks(ys); ax.set_yticklabels([r[0] for r in ROWS], fontsize=9)
ax.set_xlim(0, 100); ax.set_xlabel("% of wrong programs that pass the check")
ax.grid(axis="y", visible=False)
st.finish(ax, "Checking the output is not enough", "no check ever rejected a correct program, but each lets through a quarter to four fifths of the wrong ones",
          "fig13_checks_leak.png", ygrid=False)

# ---------- fig14: when to pay for reasoning (gpt-oss-120b, 311 contest problems, 3 seeds) ----------
PTS = [("low effort", 3.2, 46.1), ("low + 1 repair", 4.6, 53.1), ("medium", 6.8, 56.8),
       ("medium, high if the\nexamples fail", 20.2, 65.0), ("... or a brute-force\ncheck disagrees", 24.7, 66.3), ("always high", 30.1, 66.2)]
fig, ax = st.new(w=8.4, h=4.8, top=0.76, left=0.11)
ax.plot([p[1] for p in PTS[:5]], [p[2] for p in PTS[:5]], color=st.S1, lw=2, zorder=2)
for lab, x, y in PTS:
    st.dot(ax, x, y, st.S2 if lab == "always high" else st.S1, size=70)
    dx, dy, ha = {"always high": (0, -26, "center"), "medium, high if the\nexamples fail": (-10, -34, "right"),
                  "... or a brute-force\ncheck disagrees": (-8, 10, "right")}.get(lab, (6, -14, "left"))
    ax.annotate(lab, (x, y), textcoords="offset points", xytext=(dx, dy), fontsize=8.5, color=st.INK2, ha=ha)
ax.set_xscale("log"); ax.set_xticks([3, 5, 7, 10, 20, 30]); ax.set_xticklabels(["3k", "5k", "7k", "10k", "20k", "30k"])
ax.set_xlabel("output tokens per problem (log scale)"); ax.set_ylabel("% of 311 problems solved"); ax.set_ylim(40, 72)
st.finish(ax, "Pay for reasoning only when a cheap check fails", "gpt-oss-120b on real Codeforces geometry, 3 seeds; orange = always the most expensive setting",
          "fig14_reasoning_policies.png")

# ---------- fig15: agreement gate (Qwen3-32B, generated tasks, 3 seeds) ----------
PANELS = [("Geometry (13 tasks)", [("no helpers, no reasoning", 0.4, 80.6), ("always reason", 5.9, 97.8), ("reason only if two\ncheap programs disagree", 4.3, 99.1)]),
          ("Optimization (8 problems)", [("exact snippets, no reasoning", 0.5, 70.3), ("always reason", 6.2, 67.3), ("reason only if two\ncheap programs disagree", 5.6, 82.7)])]
fig, axes = plt.subplots(1, 2, figsize=(9.6, 4.6), sharey=True)
fig.subplots_adjust(left=0.08, right=0.97, top=0.72, bottom=0.15, wspace=0.08)
for ax, (name, pts) in zip(axes, PANELS):
    for (lab, x, y), c in zip(pts, (st.MUTED, st.S2, st.S1)):
        st.dot(ax, x, y, c, size=80, label=({"no helpers, no reasoning": "cheap default (no helpers / exact snippets)"}.get(lab, lab.replace("\n", " "))) if ax is axes[0] else None)
        ax.annotate(f"{y:.0f}%", (x, y), textcoords="offset points", xytext=(8, -4), fontsize=9.5, color=st.INK)
    ax.set_title(name, fontsize=10.5, color=st.INK2, loc="left"); ax.set_xlim(0, 7.5); ax.set_ylim(60, 104)
    ax.set_xlabel("output tokens per item (thousands)"); ax.set_axisbelow(True)
axes[0].set_ylabel("% correct (geometry) / optimal (optimization)")
axes[0].legend(loc="lower left", bbox_to_anchor=(0, 1.08), ncol=3, fontsize=9, handletextpad=0.3, columnspacing=1.2, borderaxespad=0)
fig.text(0.02, 0.97, "A second opinion decides when to reason", fontsize=14, weight="semibold", color=st.INK, va="top")
fig.text(0.02, 0.905, "Qwen3-32B writes one program with and one without the extra tools; it reasons only when their answers differ (3 seeds)",
         fontsize=10.5, color=st.INK2, va="top")
fig.savefig(os.path.join(st.OUT, "fig15_agreement_gate.png"), dpi=200); plt.close(fig)

# ---------- fig16: adapting a verified program to a new rule (job-shop + release dates, 120 runs per cell) ----------
MOD = [("Qwen3-32B", 12, 50, 82), ("Qwen3.6-35B-A3B", 83, 120, None), ("gpt-oss-20b", 92, 120, None), ("gpt-oss-120b", 103, 120, None)]
fig, ax = st.new(w=8.4, h=4.4, top=0.72, left=0.2)
for i, (m, s, a, mm) in enumerate(MOD):
    y = len(MOD) - 1 - i
    ax.plot([100 * s / 120, 100 * a / 120], [y, y], color=st.GRID, lw=3, zorder=1)
    st.dot(ax, 100 * s / 120, y, st.MUTED, size=70, label="written from scratch" if i == 0 else None)
    st.dot(ax, 100 * a / 120, y, st.S1, size=80, label="verified program, adapted" if i == 0 else None)
    if mm:
        st.dot(ax, 100 * mm / 120, y, st.S2, size=80, label="adapted, 'change as few lines as possible'")
        ax.annotate(f"{100 * a / 120:.0f}%", (100 * a / 120, y), textcoords="offset points", xytext=(0, 9), ha="center", fontsize=9, color=st.INK)
    ax.annotate(f"{100 * s / 120:.0f}%", (100 * s / 120, y), textcoords="offset points", xytext=(0, 9), ha="center", fontsize=9, color=st.INK2)
    ax.annotate(f"{100 * (mm or a) / 120:.0f}%", (100 * (mm or a) / 120, y), textcoords="offset points", xytext=(0, 9), ha="center", fontsize=9, color=st.INK)
ax.set_yticks(range(len(MOD))); ax.set_yticklabels([m[0] for m in MOD][::-1]); ax.set_xlim(0, 108)
ax.set_xlabel("% of runs giving a feasible schedule (job-shop with a new rule: release dates)"); ax.grid(axis="y", visible=False)
st.legend_top(ax, 2)
st.finish(ax, "Adapt a program that already works", "when the problem gains a rule, editing the verified program beats starting over (3 seeds)",
          "fig16_adapt_verified.png", ygrid=False)

# ---------- fig17: solver-library portfolio (8 optimization problems, 3 seeds) ----------
LIB = [("Qwen3-32B", 40.7, 50.0, 66.0), ("gpt-oss-20b", 72.0, 72.3, 84.7), ("Qwen3.6-35B-A3B", 55.0, 60.3, 78.3), ("gpt-oss-120b", 81.7, 81.7, 93.3)]
fig, ax = st.new(w=8.4, h=4.4, top=0.72, left=0.2)
for i, (m, free, best, port) in enumerate(LIB):
    y = len(LIB) - 1 - i
    ax.plot([free, port], [y, y], color=st.GRID, lw=3, zorder=1)
    st.dot(ax, free, y, st.MUTED, size=70, label="model's own choice of library" if i == 0 else None)
    st.dot(ax, best, y, st.S2, size=70, label="best single library (in hindsight)" if i == 0 else None)
    st.dot(ax, port, y, st.S1, size=80, label="all libraries, keep the best feasible plan" if i == 0 else None)
    ax.annotate(f"{port:.0f}%", (port, y), textcoords="offset points", xytext=(9, -4), fontsize=9.5, color=st.INK)
ax.set_yticks(range(len(LIB))); ax.set_yticklabels([m[0] for m in LIB][::-1]); ax.set_xlim(30, 100)
ax.set_xlabel("% of instances solved optimally"); ax.grid(axis="y", visible=False)
st.legend_top(ax, 2)
st.finish(ax, "The solver library is a tool choice too", "models pick a library by habit; trying all of them (≈4× tokens) beats any single one (gpt-oss: own choice = best single)",
          "fig17_library_portfolio.png", ygrid=False)
print("written to", st.OUT)
