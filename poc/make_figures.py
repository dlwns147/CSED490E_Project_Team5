"""Figures for PROPOSAL.md (static PNG, light surface). Run with a Python that has matplotlib:
    /opt/conda/bin/python poc/make_figures.py
Numbers are the pilot results recorded in docs/FINDINGS.md; the CO distractor CIs are recomputed from results/co_D_*.jsonl.
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


# ---------- Fig 1: environment fact ----------
fig, ax = new(h=3.8, top=0.66)
rows = [("Llama-3.1-8B", 83, 99), ("Qwen3-14B", 79, 100)]
for i, (m, a, b) in enumerate(rows):
    ax.plot([a, b], [i, i], color=GRID, linewidth=3, solid_capstyle="round", zorder=1)
    dot(ax, a, i, MUTED, size=90, label="without the stdlib sentence" if i == 0 else None)
    dot(ax, b, i, S1, size=90, label="with it" if i == 0 else None)
    ax.text(a - 1.2, i, f"{a}", ha="right", va="center", color=INK2)
    ax.text(b + 1.2, i, f"{b}", ha="left", va="center", color=INK, weight="semibold")
ax.set_yticks(range(len(rows)), [r[0] for r in rows]); ax.set_ylim(-0.6, 1.6)
ax.set_xlim(70, 105); ax.set_xlabel("programs correct on all 8 variants (of 100)")
ax.grid(axis="y", visible=False)
legend_top(ax, 2)
finish(ax, "T1 · One environment sentence closes most of the gap",
       "Geometry, greedy decoding. Failures without it were imports of an uninstalled library (shapely).", "fig1_environment_fact.png")

# ---------- Fig 2: distractor dose-response ----------
fig, ax = new(h=5.0)
K = [0, 2, 4, 8]
# packaging-free (offered toolbox pre-defined; poc/rescore_figs.py). As measured: 8B 98.0/87.0/81.0/74.5, U 91.0;
# 14B 84.5/83.0/73.5/75.0, U 77.5; 32B 95.5/83.5/76.0/75.5, U 91.0 (results/geocross_geox<m>_dis{0,2,4,8,U8}_t07s{1,2}.jsonl)
dose = {"Qwen3-8B": ([98.0, 87.0, 82.0, 74.5], 93.5), "Qwen3-14B": ([84.5, 83.0, 76.0, 81.0], 86.0),
        "Qwen3-32B": ([95.5, 83.5, 76.5, 79.0], 92.0)}
for (m, (ys, unrel)), c, dx in zip(dose.items(), [S1, S2, S3], [-0.22, 0.0, 0.22]):
    xs = [k + dx / 2 for k in K]   # small dodge so coinciding points (14B / 32B at K = 2, 4) stay visible
    ax.plot(xs, ys, color=c, linewidth=2, solid_joinstyle="round", solid_capstyle="round", zorder=2, label=m)
    dot(ax, xs, ys, c)
    ax.scatter([6 + dx], [unrel], s=70, facecolor=SURFACE, edgecolor=c, linewidth=2, zorder=3)
ax.text(6, 99.5, "6 unrelated helpers\n(hollow markers)", ha="center", va="bottom", fontsize=9, color=INK2)
ax.set_xticks([0, 2, 4, 6, 8], ["0", "2", "4", "", "8"]); ax.set_xlim(-0.5, 8.6); ax.set_ylim(70, 104)
ax.set_xlabel("number of correct-but-unneeded related helpers in the prompt (K)")
ax.set_ylabel("correct on all 8 variants (%)")
legend_top(ax, 3)
finish(ax, "T2 · Plausible extra helpers hurt geometry code (8B, 32B; 14B less)",
       "n = 100 programs × 2 seeds per point, T = 0.7, offered helpers pre-defined (copy failures do not count).\n"
       "Unrelated helpers barely hurt. 14B's K = 0 is lowered by misuse of a needed helper's signature.",
       "fig2_distractor_dose.png")

# ---------- Fig 3: mechanism (copy vs prelude) ----------
fig, ax = new(h=4.2)
mech = {"copy-in": [(-14.3, -20.3, -8.7), (-15.7, -21.3, -10.3), (-15.7, -21.3, -10.3)],
        "pre-defined (prelude)": [(-12.3, -17.7, -6.7), (-1.3, -6.7, 4.0), (-15.0, -20.0, -10.0)]}
for j, ((lab, vals), c) in enumerate(zip(mech.items(), [S1, S2])):
    for i, (v, lo, hi) in enumerate(vals):
        y = i + (0.14 if j == 0 else -0.14)
        ax.plot([lo, hi], [y, y], color=c, linewidth=2, solid_capstyle="round", zorder=2)
        dot(ax, v, y, c, label=lab if i == 0 else None)
        ax.text(hi + 0.6, y, f"{v:+.1f}", va="center", fontsize=9.5, color=INK2)
ax.axvline(0, color=INK2, linewidth=1, zorder=1)
ax.set_yticks(range(3), [MODELS[0], MODELS[1] + "*", MODELS[2]]); ax.invert_yaxis()
ax.set_xlim(-25, 8); ax.set_xlabel("change from 8 extra helpers, percentage points (95% CI)")
ax.grid(axis="y", visible=False)
legend_top(ax, 2)
finish(ax, "T2 · The harm is semantic, not packaging",
       "Same loss when helpers are pre-defined (8B, 32B). *14B baseline floored by helper-signature misuse.", "fig3_mechanism.png")

# ---------- Fig 4: domain contrast ----------
rng = np.random.default_rng(0)


def co_delta(m):
    ok = lambda r: bool(r["feasible"] and r["gap"] is not None and r["gap"] <= 1)
    L = lambda t: [{r["key"]: ok(r) for r in map(json.loads, open(os.path.join(ROOT, "results", f"co_D_co{m}_{t}_s{s}.jsonl")))} for s in (1, 2)]
    a, b = L("x8"), L("x0")
    keys = sorted(a[0])
    d = np.array([np.mean([x[k] for x in a]) - np.mean([x[k] for x in b]) for k in keys]) * 100
    bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(4000)]
    return d.mean(), np.percentile(bs, 2.5), np.percentile(bs, 97.5)


# geometry: K0 -> K8 related helpers, packaging-free (= fig 7 rows; F_geox<m>_dis{0,8}_t07s1). Was K8 minus the task-matched predicates
# arm (-17.7 / -29.0 / -17.0), a different prompt. Optimization is computed from results/co_D_*.jsonl (no helpers to copy there).
geo = [(-14.3, -20.0, -8.7), (-7.7, -12.7, -3.0), (-13.3, -18.7, -8.0)]
try:
    co = [co_delta(m) for m in ("8b", "14b", "32b")]
except FileNotFoundError:
    co = [(0.0, -1.8, 1.8), (-2.4, -5.4, 0.0), (0.0, -3.0, 3.0)]
fig, ax = new(h=4.6, top=0.66)
for j, ((lab, vals), c) in enumerate(zip({"geometry: +8 related helpers (n = 300), helpers pre-defined": geo,
                                          "optimization: +8 unneeded OR-Tools lines (84 × 2)": co}.items(), [S1, S2])):
    for i, (v, lo, hi) in enumerate(vals):
        y = i + (0.14 if j == 0 else -0.14)
        ax.plot([lo, hi], [y, y], color=c, linewidth=2, solid_capstyle="round", zorder=2)
        dot(ax, v, y, c, label=lab if i == 0 else None)
        ax.text(hi + 0.6, y, f"{v:+.1f}", va="center", fontsize=9.5, color=INK2)
ax.axvline(0, color=INK2, linewidth=1, zorder=1)
ax.set_yticks(range(3), MODELS); ax.invert_yaxis(); ax.set_xlim(-24, 8)
ax.set_xlabel("change in accuracy, percentage points (95% CI)")
ax.grid(axis="y", visible=False)
legend_top(ax, 1)
finish(ax, "T3 · Extra material hurts geometry code but not optimization code",
       "Geometry helpers are embedded in the program; extra solver documentation is ignored.\n"
       "Geometry scored with the offered helpers pre-defined, so copy failures do not count.", "fig4_domain_contrast.png")

# ---------- Fig 5: CO documentation ----------
fig, ax = new(w=8.6, h=4.8, top=0.70, left=0.11)
co_doc = {"no doc": [.255, .607, .701], "full cheat sheet": [.349, .810, .926], "problem-specific snippet": [.710, .959, .970]}
best3 = [.718, 1.000, 1.000]
x = np.arange(3); w = 0.22
for j, ((lab, vals), c) in enumerate(zip(co_doc.items(), [MUTED, S2, S1])):
    xs = x + (j - 1) * (w + 0.02)
    ax.bar(xs, vals, width=w, color=c, label=lab, zorder=2)
    if j == 2:
        for xi, v, b in zip(xs, vals, best3):
            ax.text(xi, max(v, b) + 0.025, f"{v:.2f}", ha="center", va="bottom", fontsize=9.5, color=INK)
ax.scatter(x + (w + 0.02), best3, marker="_", s=260, color=INK, linewidth=2, zorder=3, label="snippet + best-of-3")
ax.set_xticks(x, MODELS); ax.set_ylim(0, 1.12); ax.set_ylabel("share within 1% of optimum")
ax.grid(axis="x", visible=False)
legend_top(ax, 4)
finish(ax, "T4 · State the problem-specific pattern, not the whole manual",
       "Optimization, 252 instances × 3 seeds. Snippet − full sheet: +.36 / +.15 / +.04 (CIs exclude 0).", "fig5_co_docs.png")

# ---------- Fig 6: verified sampling ----------
fig, ax = new(h=4.8, top=0.62)
conds = [("one tool-free sample (mean of 3)", [91.8, 96.2, 84.4], MUTED),
         ("one sample with hand-picked helpers", [95.0, 97.0, 93.3], S2),
         ("3 tool-free samples + metamorphic check", [98.7, 97.7, 94.3], S1)]
for i in range(3):
    vals = [c[1][i] for c in conds]
    ax.plot([min(vals), max(vals)], [i, i], color=GRID, linewidth=3, solid_capstyle="round", zorder=1)
for lab, vals, c in conds:
    dot(ax, vals, range(3), c, size=90, label=lab)
for i, v in enumerate(conds[2][1]):
    ax.text(v + 0.5, i, f"{v:.1f}", va="center", color=INK, weight="semibold", fontsize=10)
ax.set_yticks(range(3), MODELS); ax.invert_yaxis(); ax.set_xlim(82, 102)
ax.set_xlabel("correct on all 8 variants (%), n = 300 per condition")
ax.grid(axis="y", visible=False)
legend_top(ax, 1)
finish(ax, "T5 · Sampling plus a label-free check matches hand-picked tools",
       "Geometry with the stdlib sentence. No knowledge of the task is needed for the sampling route.", "fig6_verified_sampling.png")

# ---------- Fig 7: distractor harm by model and mode ----------
fig, ax = new(h=7.0, top=0.76, left=0.32)
# K0 -> K8 delta, packaging-free (offered helpers pre-defined), paired cluster-bootstrap 95% CI over instances
# (poc/rescore_figs.py -> results/figs_packaging_free.json). As measured, 1.7B / Llama-8B / 8B / 14B / 32B / Llama-70B / 1.7B thinking were
# -35.7 / -39.3 / -14.3 / -15.7 / -15.7 / -0.8 / -4.3; the other rows have no copy failures (unchanged).
rows7 = [("Qwen3-1.7B", 0.3, -7.0, 7.7, 0), ("Llama-3.1-8B", -35.2, -40.3, -30.2, 0), ("Qwen3-8B", -14.3, -20.0, -8.7, 0),
         ("Qwen3-14B", -7.7, -12.7, -3.0, 0), ("Qwen3-32B", -13.3, -18.7, -8.0, 0), ("Llama-3.3-70B", 0.8, -2.8, 4.1, 0),
         ("Qwen3-1.7B, thinking", -4.7, -10.0, 0.7, 1), ("Qwen3-8B, thinking", -1.5, -4.5, 1.5, 1), ("Qwen3-14B, thinking", -0.5, -2.5, 1.0, 1),
         ("Qwen3-32B, thinking", -3.0, -5.5, -1.0, 1), ("R1-Distill-Llama-70B", 0.0, -3.0, 3.0, 1),
         ("gpt-oss-20b, low effort", -0.7, -2.0, 0.7, 1), ("gpt-oss-20b, medium effort", 0.0, -1.2, 1.2, 1),
         ("gpt-oss-120b, low effort", -0.7, -2.3, 1.0, 1), ("gpt-oss-120b, medium effort", 0.0, -1.0, 1.0, 1)]
seen = set()
for i, (lab, v, lo, hi, mode) in enumerate(rows7):
    c = S1 if mode == 0 else S2
    ax.plot([lo, hi], [i, i], color=c, linewidth=2, solid_capstyle="round", zorder=2)
    name = "standard generation" if mode == 0 else "reasoning (thinking / R1 / gpt-oss)"
    dot(ax, v, i, c, label=None if name in seen else name); seen.add(name)
    ax.text((hi if hi < -2.5 else max(hi, 0)) + 0.8, i, f"{v:+.1f}", va="center", fontsize=9.5, color=INK2)
# Qwen3-1.7B: the pooled ~0 is the sum of opposite per-task effects (correct of 60, K0 -> K8, packaging-free)
ax.text(-42.5, 0.1, "≈ 0 hides opposite task effects (of 60):\nhull 49→17, area2 60→43, close 29→57, segs 1→18",
        ha="left", va="center", fontsize=8, color=INK2, linespacing=1.25)
ax.axvline(0, color=INK2, linewidth=1, zorder=1)
ax.set_yticks(range(len(rows7)), [r[0] for r in rows7]); ax.invert_yaxis(); ax.set_xlim(-43, 13)
ax.set_xlabel("change from 8 plausible extra helpers, percentage points (95% CI)")
ax.grid(axis="y", visible=False)
legend_top(ax, 2)
finish(ax, "T2 · Robustness to plausible helpers comes with reasoning or scale",
       "Geometry, K = 0 vs 8 related helpers, 100–900 paired programs per row. All rows scored with the\n"
       "offered helpers pre-defined (copy failures removed). gpt-oss at low/medium effort only; at high effort\n"
       "gpt-oss-20b hits the 24k-token cap in 24–27% of programs.",
       "fig7_distractor_by_model.png")

# ---------- Fig 8: fixes when a broad toolbox is present ----------
fig, ax = new(h=4.8, top=0.62)
# packaging-free (poc/rescore_figs.py). Sources: F_geox<m>_dis8_t07s{1,2,3} (one sample = mean of 3 seeds; 3 samples + check = MR-select over
# them), F_geox<m>_dis0_t07s1 (needed helpers only, same "should use" header), T_geox<m>_dis8 seeds 1-2 (thinking, n = 100 each).
# As measured: 77.1 / 70.9 / 75.0, 81.3 / 84.3 / 84.0; "needed helpers only" was the task-matched predicates arm F_geox<m>_pt_t07s1
# (95.0 / 97.0 / 93.3), a different prompt header than the K = 8 arms.
conds8 = [("8 extra helpers, one sample", [77.4, 78.7, 76.7], MUTED),
          ("8 extra helpers, 3 samples + check", [81.7, 86.7, 85.0], S3),
          ("needed helpers only (K = 0), one sample", [91.7, 83.7, 92.0], S2),
          ("8 extra helpers, thinking", [97.0, 99.0, 97.0], S1)]
for i in range(3):
    vals = [c[1][i] for c in conds8]
    ax.plot([min(vals), max(vals)], [i, i], color=GRID, linewidth=3, solid_capstyle="round", zorder=1)
for lab, vals, c in conds8:
    dot(ax, vals, range(3), c, size=90, label=lab)
ax.set_yticks(range(3), MODELS); ax.invert_yaxis(); ax.set_xlim(72, 101)
ax.set_xlabel("correct on all 8 variants (%)")
ax.grid(axis="y", visible=False)
legend_top(ax, 2)
finish(ax, "Which fix when the toolbox is broad?",
       "Geometry, Qwen3, helpers pre-defined (copy failures do not count).\n"
       "3 samples + check recover part of the loss (all of it at 14B, whose K = 0 is lowered by helper misuse);\n"
       "thinking beats even the trimmed toolbox.",
       "fig8_fixes_under_distractors.png")

print("wrote", sorted(os.listdir(OUT)))
