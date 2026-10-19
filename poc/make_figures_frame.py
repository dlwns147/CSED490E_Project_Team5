"""Figures for the reframed PROPOSAL.md (solving computational math accurately and cheaply). Run: python poc/make_figures_frame.py
fig18: the recipe; fig19: cost vs accuracy of compute-allocation policies (docs/prereg/PREREG_U1.md, results/u1r_all_cure1.log:
3 models x geometry + optimization suites, 624 items, cure seed 1; first-program tokens from the S2_U1 base_s1 runs);
fig20: gain of one API fact by model size (docs/prereg/PREREG_SIZE.md, X6 = NL4OPT + IndustryOR, 345 problems x 3 seeds);
fig21: results at a glance (numbers from PROPOSAL.md sections 3, 4 and 7);
fig22: newer results (docs/prereg/PREREG_X7.md held-out MAMO, PREREG_MODEL.md policy choice, PREREG_PROOF.md Lean proofs)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_figures_style as st  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

# ---------- fig18: the recipe ----------
fig, ax = plt.subplots(figsize=(10, 3.9))
fig.subplots_adjust(left=0.01, right=0.99, top=0.80, bottom=0.02)
ax.set_xlim(0, 100); ax.set_ylim(0, 40); ax.axis("off")


def box(x, y, w, h, text, fill, weight="normal", size=10):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.5", fc=fill, ec=st.GRID, lw=1.2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size, color=st.INK, weight=weight, linespacing=1.35)


def arrow(x0, y0, x1, y1, label=None, dy=1.0):
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=12, lw=1.3, color=st.INK2))
    if label:
        ax.text((x0 + x1) / 2, (y0 + y1) / 2 + dy, label, ha="center", va="bottom", fontsize=9, color=st.INK2)


box(1, 21, 15, 12, "1. Write\na program", "#eef3fb", "semibold", 10.5)
box(21, 21, 19, 12, "2. Add the\nmissing fact", "#eef3fb", "semibold", 10.5)
box(45, 21, 19, 12, "3. Run a\nfree check", "#eef3fb", "semibold", 10.5)
ax.text(8.5, 18.6, "not a text answer", ha="center", va="top", fontsize=8.8, color=st.INK2)
ax.text(30.5, 18.6, "e.g. 5 lines of exact\nlibrary usage", ha="center", va="top", fontsize=8.8, color=st.INK2)
ax.text(54.5, 18.6, "the statement's examples,\nor two versions agree", ha="center", va="top", fontsize=8.8, color=st.INK2)
box(71, 27.5, 27, 7, "pass → done (cheap)", "#e3f4ec", size=10.5)
box(71, 15.5, 27, 9, "fail → 4. think harder,\nonly for this problem", "#fde8df", size=10.5)
arrow(16.6, 27, 20.4, 27); arrow(40.6, 27, 44.4, 27)
arrow(64.6, 28.5, 70.4, 31); arrow(64.6, 25.5, 70.4, 20.5)
box(1, 1.5, 97, 6.5, "5. The same problem again with new data (tomorrow's deliveries)?  Reuse the program that already passed the check", "#f3f2ee", size=10)
fig.text(0.02, 0.97, "The recipe: cheap steps first, expensive thinking only where a check fails", fontsize=14, weight="semibold", color=st.INK, va="top")
fig.text(0.02, 0.89, "Each step is a measured result (Section 3); together they give the best accuracy per token (Section 4)", fontsize=10.5, color=st.INK2, va="top")
fig.savefig(os.path.join(st.OUT, "fig18_recipe.png"), dpi=200); plt.close(fig)

# ---------- fig19: cost vs accuracy of compute-allocation policies ----------
P = [  # label, accuracy %, output tokens per problem (k), colour, label position (dx, dy, alignment)
    ("first program, no help", 63.3, 0.71, st.MUTED, (0.12, -0.5, "left")),
    ("always add the fact", 79.3, 0.44, st.S3, (0.12, -0.5, "left")),
    ("think on the hardest-looking problems", 73.9, 4.09, st.MUTED, (-0.12, -0.5, "right")),
    ("think when the check fails", 77.1, 4.22, st.MUTED, (-0.12, -0.5, "right")),
    ("fix chosen by failure type", 82.5, 4.18, st.S2, (-0.12, -0.5, "right")),
    ("retrieved fact first, then think on failure", 84.1, 3.35, st.S1, (-0.12, -0.5, "right")),
    ("fact first, then think on failure", 87.2, 2.51, st.S1, (0.12, -0.5, "left")),
]
fig, ax = st.new(w=8.6, h=5.0, top=0.78, left=0.11)
for lab, y, x, c, (dx, dy, ha) in P:
    st.dot(ax, x, y, c, size=150 if lab.startswith("fact first") else 80)
    ax.text(x + dx, y + dy, lab, fontsize=9.5, color=st.INK if lab.startswith("fact first") else st.INK2, ha=ha,
            weight="semibold" if lab.startswith("fact first") else "normal")
ax.set_xlim(0, 4.9); ax.set_ylim(58, 92)
ax.set_xlabel("output tokens per problem (thousands)"); ax.set_ylabel("problems solved (%)")
st.finish(ax, "Facts first, think only on failure: most accurate and cheaper",
          "Qwen3-8B, Qwen3-32B, Qwen3.6 on geometry + optimization (624 problems); same ranking on 3 seeds", "fig19_cost_accuracy.png")

# ---------- fig20: one fact helps small models most ----------
M = ["Qwen3-1.7B", "Qwen3-4B", "Qwen3-8B", "Qwen3-14B\n(4-bit)", "Qwen3-32B\n(4-bit)"]
NOFACT = [0.1, 14.7, 34.3, 58.1, 65.4]
FACT = [44.5, 46.0, 51.7, 66.0, 66.2]
fig, ax = st.new(w=8.6, h=4.8, top=0.74, left=0.10)
xs = range(len(M)); w = 0.36
ax.bar([x - w / 2 for x in xs], NOFACT, w, color=st.MUTED, label="program only")
ax.bar([x + w / 2 for x in xs], FACT, w, color=st.S1, label="program + 6 lines of exact solver usage")
for x, a, b in zip(xs, NOFACT, FACT):
    ax.text(x + w / 2, b + 1.5, f"+{b - a:.0f}", ha="center", fontsize=10, weight="semibold", color=st.S1)
ax.set_xticks(list(xs)); ax.set_xticklabels(M); ax.set_ylim(0, 80); ax.set_ylabel("word problems solved (%)")
ax.axvspan(-0.5, 3.5, color="#eef3fb", zorder=0)
ax.text(1.5, 74, "fits one 24 GB GPU (e.g. RTX 3090)", ha="center", fontsize=9.5, color=st.INK2)
st.legend_top(ax, 2)
st.finish(ax, "The smaller the model, the more one fact helps", "NL4OPT + IndustryOR word problems → optimization programs (345 problems × 3 seeds)",
          "fig20_fact_by_size.png", ygrid=True)
print("wrote fig18_recipe.png, fig19_cost_accuracy.png, fig20_fact_by_size.png")

# ---------- fig21: results at a glance ----------
GREY, BLUE, RED = st.MUTED, st.S1, "#c0392b"
PANELS = [  # title, subtitle, rows: (label, value for the bar, shown text, colour)
    ("Add the missing fact", "delivery routing (CVRP), Qwen3-32B: % optimal", [
        ("task only", 23, "23%", GREY), ("think longer", 3, "3%", RED), ("+ whole manual", 7, "7%", RED),
        ("+ 5 exact lines", 83, "77–90%", BLUE)]),
    ("Small models gain the most", "word problems → solver programs: % solved", [
        ("Qwen3-1.7B", 0.1, "0%", GREY), ("Qwen3-1.7B + fact", 44.5, "45%", BLUE),
        ("Qwen3-32B", 65.4, "65%", GREY), ("Qwen3-32B + fact", 66.2, "66%", BLUE)]),
    ("Compare two versions", "geometry, Qwen3-32B: % right · tokens per problem", [
        ("with 8 unneeded tools", 59, "59% · 0.6k", RED), ("always think", 98, "98% · 5.9k", GREY),
        ("think only if they differ", 99, "99% · 4.3k", BLUE)]),
    ("Think only on a failed check", "311 contest problems, gpt-oss-120b", [
        ("always high effort", 66.2, "66.2% · 30.1k", GREY), ("high only on failure", 66.3, "66.3% · 24.7k", BLUE)]),
    ("Reuse a checked program", "48 days of delivery routing, gpt-oss-120b: % valid · tokens in total", [
        ("new program every day", 7, "7% · 86k", GREY), ("own notes (Dyn. Cheatsheet)", 36, "31–40%", GREY),
        ("reuse one checked program", 94, "94% · 28k", BLUE)]),
    ("All together", "3 models, 624 problems: % solved · tokens per problem", [
        ("think on hardest (Snell)", 74, "74% · 4.1k", GREY), ("fix by failure type", 83, "83% · 4.2k", GREY),
        ("fact first, think on failure", 87, "87% · 2.5k", BLUE)]),
]
fig, ax = plt.subplots(figsize=(16, 7.2))
fig.subplots_adjust(left=0.005, right=0.995, top=0.865, bottom=0.01)
ax.set_xlim(0, 160); ax.set_ylim(11, 76); ax.axis("off")
for k, (title, sub, rows) in enumerate(PANELS):
    x0, top = 1 + (k % 3) * 53, 75 - (k // 3) * 38
    ax.text(x0, top, title, fontsize=14, weight="semibold", color=st.INK, va="top")
    ax.text(x0, top - 3.6, sub, fontsize=10, color=st.INK2, va="top")
    for r, (lab, v, shown, col) in enumerate(rows):
        y = top - 10.5 - r * 5.6
        ax.text(x0 + 18, y, lab, fontsize=11, color=st.INK2, ha="right", va="center")
        ax.add_patch(plt.Rectangle((x0 + 19, y - 1.8), max(0.3, 0.21 * v), 3.6, color=col, lw=0))
        ax.text(x0 + 19.8 + 0.21 * v, y, shown, fontsize=11.5, weight="semibold", va="center", color=col if col != GREY else st.INK2)
fig.text(0.006, 0.975, "Results at a glance: the same or better accuracy for fewer tokens", fontsize=17, weight="semibold", color=st.INK, va="top")
fig.text(0.006, 0.93, "blue = the better way;  grey = the usual way or a published method;  red = makes it worse", fontsize=11.5, color=st.INK2, va="top")
fig.savefig(os.path.join(st.OUT, "fig21_results_glance.png"), dpi=200); plt.close(fig)
print("wrote fig21_results_glance.png")

# ---------- fig22: newer results (automatic facts on a held-out benchmark, choosing the policy, proofs) ----------
NEW = [
    ("Facts found automatically", "held-out MAMO (863 word problems), gpt-oss-20b: % solved", [
        ("no fact", 73.2, "73%", GREY), ("hand-written fact", 78.9, "79%", GREY),
        ("model's own program", 78.8, "79% (no human)", BLUE)]),
    ("Choosing the policy", "63 settings: points lost vs each one's best policy (lower is better)", [
        ("always think", 84, "8.4", GREY), ("fact first, think on failure", 14, "1.4", BLUE),
        ("best of 4 on 30 labelled", 6, "0.6", BLUE)]),
    ("Proofs need a specialized model", "Lean proofs (miniF2F, 244), 8 tries: % proved", [
        ("Qwen3-32B", 12.7, "13%", GREY), ("gpt-oss-20b", 27.0, "27%", GREY),
        ("Qwen3.6-35B", 54.5, "55%", GREY), ("Goedel-Prover-V2-8B", 73.8, "74%", BLUE)]),
]
fig, ax = plt.subplots(figsize=(16, 4.7))
fig.subplots_adjust(left=0.005, right=0.995, top=0.81, bottom=0.01)
ax.set_xlim(0, 160); ax.set_ylim(43.5, 76); ax.axis("off")
for k, (title, sub, rows) in enumerate(NEW):
    x0, top = 1 + k * 53, 75
    ax.text(x0, top, title, fontsize=14, weight="semibold", color=st.INK, va="top")
    ax.text(x0, top - 3.6, sub, fontsize=10, color=st.INK2, va="top")
    for r, (lab, v, shown, col) in enumerate(rows):
        y = top - 10.5 - r * 5.6
        ax.text(x0 + 18, y, lab, fontsize=11, color=st.INK2, ha="right", va="center")
        ax.add_patch(plt.Rectangle((x0 + 19, y - 1.8), max(0.3, 0.21 * v), 3.6, color=col, lw=0))
        ax.text(x0 + 19.8 + 0.21 * v, y, shown, fontsize=11.5, weight="semibold", va="center", color=col if col != GREY else st.INK2)
fig.text(0.006, 0.97, "New results: facts without a human, a policy from 30 labels, and where proofs need another tool", fontsize=17, weight="semibold", color=st.INK, va="top")
fig.text(0.006, 0.885, "blue = our recipe or the tool that works;  grey = the alternatives", fontsize=11.5, color=st.INK2, va="top")
fig.savefig(os.path.join(st.OUT, "fig22_new_results.png"), dpi=200); plt.close(fig)
print("wrote fig22_new_results.png")
