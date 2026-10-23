"""Report figure (docs/REPORT.md §5): on each held-out benchmark, accuracy vs output tokens per problem of always thinking and of the
recipe (fact first, think only when the free check fails), one panel per 24 GB model, computed from the stored rows (seed means);
the fourth panel is Qwen3.5-9B, a model the recipe was never developed with (HO-N; OptMATH with the library, thinking at 32k).
Always thinking is given the same fact as the recipe (HO-TF / HO-TF2: formxt, thinkfact; OptiBench on the HO-TF third).
Fact per benchmark: OptMATH the mined usage example (mips), OptiBench / BWOR / LogiOR the label-free library (formx), geometry the needed
helpers + hint. usage: python make_figure_heldout.py   -> figs/fig23_heldout.png (+ prints the numbers)"""
import hashlib, json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
X3, RES = f"{ROOT}/results/x3", f"{ROOT}/results"
MODELS = (("oss20", "gpt-oss-20b"), ("q14a", "Qwen3-14B-AWQ"), ("q8b", "Qwen3-8B"), ("q35", "Qwen3.5-9B (never used in development)"))
OPT = (("optmath", "OptMATH", "mips", "thinks"), ("optibench", "OptiBench", "formx", "formxt"), ("bwor", "BWOR", "formx", "formxt"),
       ("logior", "LogiOR", "formx", "formxt"))
OPT_NEW = (("optmath", "OptMATH", "formx", "formxt"),) + OPT[1:]   # no mined example: the model has no development runs
BLUE, ORANGE, INK, MUTED, SURFACE = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#fcfcfb"
# label placement where pairs crowd: (anchor point, dx, dy, ha); default = above-left of the recipe's point
LABEL = {("q14a", "OptMATH"): ("ff", -6, -12, "right"), ("q14a", "BWOR"): ("ff", -7, -3, "right"), ("q14a", "LogiOR"): ("ff", 3, -12, "left"), ("q8b", "geometry"): ("ff", -6, -12, "right"),
         ("q8b", "BWOR"): ("think", 7, -3, "left"), ("q8b", "LogiOR"): ("think", 7, -3, "left"), ("q8b", "OptMATH"): ("think", 7, -3, "left"),
         ("q35", "BWOR"): ("ff", -7, -7, "right"), ("q35", "LogiOR"): ("ff", 2, 7, "left")}


def rows(path):
    return {r["id"]: r for r in map(json.loads, open(path))} if os.path.exists(path) else None


def opt_cell(m, bench, cheap, think):
    ok_ = lambda r: r["status"] == "ok" and r.get("pred") not in (None, "NBS")
    acc_ff = acc_t = tok_ff = tok_t = n = 0
    for s in (1, 2, 3):
        F, T = rows(f"{X3}/opt_{m}_{bench}_{cheap}_s{s}.jsonl"), rows(f"{X3}/opt_{m}_{bench}_{think}_s{s}.jsonl")
        for i, f in F.items():
            if i in T:
                t = T[i]; n += 1; esc = not ok_(f)
                acc_ff += t["correct"] if esc else f["correct"]; acc_t += t["correct"]
                tok_ff += (f["out_tokens"] or 0) + ((t["out_tokens"] or 0) if esc else 0); tok_t += t["out_tokens"] or 0
    return 100 * acc_ff / n, tok_ff / n / 1000, 100 * acc_t / n, tok_t / n / 1000


def geo_cell(m):
    C = json.load(open(f"{RES}/n10_check_cache.json"))
    mr = lambda r: bool(r.get("code")) and C[hashlib.md5(f"{r['task']}-{r['n']}-{r['inst']}|{r['code']}".encode()).hexdigest()][0]
    ok = lambda r: r["class"] == "correct_all"; tok = lambda r: (r.get("out_tokens") or 0) + (r.get("think_tokens") or 0)
    acc_ff = acc_t = tok_ff = tok_t = n = 0
    for s in (1, 2, 3):
        load = lambda a: {(r["task"], r["n"], r["inst"]): r for r in map(json.loads, open(f"{RES}/geocross_S2_HOG_{m}_geo_{a}_s{s}.jsonl"))}
        F, T = load("fact"), load("thinkfact")
        for k, f in F.items():
            t = T[k]; n += 1; p = mr(f)
            acc_ff += ok(f) if p else ok(t); acc_t += ok(t); tok_ff += tok(f) + (0 if p else tok(t)); tok_t += tok(t)
    return 100 * acc_ff / n, tok_ff / n / 1000, 100 * acc_t / n, tok_t / n / 1000


def main():
    plt.rcParams.update({"font.size": 9, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "xtick.color": MUTED, "ytick.color": MUTED})
    fig, axes = plt.subplots(1, 4, figsize=(16, 4.8), sharey=True, facecolor=SURFACE)
    for ax, (m, name) in zip(axes, MODELS):
        cells = [(label, *opt_cell(m, b, c, t)) for b, label, c, t in (OPT if m != "q35" else OPT_NEW)] + [("geometry", *geo_cell(m))]
        ax.set_facecolor(SURFACE)
        for label, aff, tff, at, tt in cells:
            print(f"{name:14s} {label:10s} recipe {aff:5.1f}% @ {tff:5.2f}k | always think {at:5.1f}% @ {tt:5.2f}k")
            ax.plot([tt, tff], [at, aff], color=MUTED, lw=1, alpha=.6, zorder=1)
            ax.scatter([tt], [at], s=46, color=ORANGE, edgecolor=SURFACE, linewidth=2, zorder=3)
            ax.scatter([tff], [aff], s=46, color=BLUE, edgecolor=SURFACE, linewidth=2, zorder=3)
            where, dx, dy, ha = LABEL.get((m, label), ("ff", -6, 5, "right"))
            ax.annotate(label, (tff, aff) if where == "ff" else (tt, at), xytext=(dx, dy), textcoords="offset points", ha=ha, fontsize=8, color=MUTED)
        ax.set_xscale("log"); ax.set_xlim(0.6, 32); ax.set_ylim(0, 105)
        ax.set_xticks([1, 2, 4, 8, 16, 32]); ax.set_xticklabels(["1k", "2k", "4k", "8k", "16k", "32k"])
        ax.set_title(name, color=INK, fontsize=10, loc="left")
        ax.set_xlabel("output tokens per problem (log scale)")
        ax.grid(axis="y", color="#e4e3df", lw=.6); ax.set_axisbelow(True)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
    axes[0].set_ylabel("solved (%)")
    handles = [plt.Line2D([], [], marker="o", ls="", color=BLUE, label="fact first, think only when the free check fails"),
               plt.Line2D([], [], marker="o", ls="", color=ORANGE, label="always think, with the same fact")]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.005, 0.955), frameon=False, ncol=2, fontsize=9)
    fig.suptitle("Held-out benchmarks: the recipe vs always thinking with the same fact (3 seeds; left of its pair = cheaper, above = more accurate)",
                 x=0.01, ha="left", fontsize=10, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    out = f"{ROOT}/figs/fig23_heldout.png"
    fig.savefig(out, dpi=200, facecolor=SURFACE); print("wrote", out)


if __name__ == "__main__":
    main()
