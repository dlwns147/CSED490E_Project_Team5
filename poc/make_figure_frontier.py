"""Report figure (docs/REPORT.md §5.6b): accuracy vs output tokens per problem of five policies, every one given the same fact, on each
held-out benchmark (columns) for the four hybrid-thinking models (rows), from the stored rows (seed means; 3 seeds):
  one think (formxt / thinkfact), think + retry on a visible failure (T->T: the next seed's think), non-thinking program first (FF+F, the
  original recipe), short think first (SB+F: 2,000-token think, full think on its visible failure), short think -> think -> retry (SB->T->T).
OptiBench on the HO-TF third; OptMATH with the label-free library for every model; geometry: the helpers + hint fact, visible failure = the
metamorphic check fails (needs Python >= 3.10). usage: python make_figure_frontier.py   -> figs/fig24_frontier.png (+ prints the numbers)"""
import json, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
X3 = f"{ROOT}/results/x3"
MODELS = (("q14a", "Qwen3-14B-AWQ"), ("q8b", "Qwen3-8B"), ("n3n", "Nemotron-3-Nano (new family)"), ("q35", "Qwen3.5-9B"))
BENCH = (("optibench", "OptiBench"), ("bwor", "BWOR"), ("logior", "LogiOR"), ("optmath", "OptMATH"), ("geometry", "geometry"))
POL = (("T", "one think", "#8a8985", "o"), ("T->T", "think, retry on a visible failure", "#0b0b0b", "s"),
       ("FF+F", "non-thinking program first", "#2a78d6", "^"), ("SB+F", "short think first", "#eb6834", "D"),
       ("SB->T->T", "short think, think, retry", "#1f9e89", "*"))
SURFACE, INK, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1"


def rows(path):
    return {r["id"]: r for r in map(json.loads, open(path))} if os.path.exists(path) else {}


def combine(items):
    """items: per row (f_pass, f_ok, f_tok, sb_pass, sb_ok, sb_tok, t_pass, t_ok, t_tok, t2_ok, t2_tok) -> {policy: (acc %, ktokens)}"""
    acc, tok = {p[0]: 0 for p in POL}, {p[0]: 0 for p in POL}
    for fp, fo, ft, sp, so, st, tp, to, tt, t2o, t2t in items:
        rt = (to, tt) if tp else (t2o, tt + t2t)
        for k, (a, t) in {"T": (to, tt), "T->T": rt, "FF+F": (fo, ft) if fp else (to, ft + tt),
                          "SB+F": (so, st) if sp else (to, st + tt), "SB->T->T": (so, st) if sp else (rt[0], st + rt[1])}.items():
            acc[k] += a; tok[k] += t
    n = len(items)
    return {k: (100 * acc[k] / n, tok[k] / n / 1000) for k in acc}, n


def word(m, b):
    ok_ = lambda r: r.get("status") == "ok" and r.get("pred") not in (None, "NBS")
    g = lambda r: r.get("out_tokens") or 0
    items = []
    for s in (1, 2, 3):
        F, S, T, T2 = (rows(f"{X3}/opt_{m}_{b}_{a}_s{x}.jsonl") for a, x in (("formx", s), ("formxtb2000", s), ("formxt", s), ("formxt", s % 3 + 1)))
        for i, t in T.items():
            if i in F and i in S and i in T2:
                f, sb, t2 = F[i], S[i], T2[i]
                items.append((ok_(f), bool(f["correct"]), g(f), ok_(sb), bool(sb["correct"]), g(sb), ok_(t), bool(t["correct"]), g(t),
                              bool(t2["correct"]), g(t2)))
    return combine(items) if items else (None, 0)


def geometry(m):
    import analyze_n10 as N
    from analyze_hogc import load, ok, tok
    items = []
    for s in (1, 2, 3):
        F, S, T, T2 = (load(f"S2_HOG_{m}_geo_{a}_s{x}") or {} for a, x in (("fact", s), ("thinkfactb2000", s), ("thinkfact", s), ("thinkfact", s % 3 + 1)))
        for k, t in T.items():
            if k in F and k in S and k in T2:
                f, sb, t2 = F[k], S[k], T2[k]
                items.append((N.geo_check(f)[0], ok(f), tok(f), N.geo_check(sb)[0], ok(sb), tok(sb), N.geo_check(t)[0], ok(t), tok(t), ok(t2), tok(t2)))
    return combine(items) if items else (None, 0)


def main():
    fig, axes = plt.subplots(len(MODELS), len(BENCH), figsize=(16, 12.5), facecolor=SURFACE)
    for r, (m, mname) in enumerate(MODELS):
        for c, (b, bname) in enumerate(BENCH):
            ax = axes[r][c]; ax.set_facecolor(SURFACE)
            res, n = geometry(m) if b == "geometry" else word(m, b)
            if not res:
                ax.text(0.5, 0.5, "not run", ha="center", va="center", color=MUTED, transform=ax.transAxes); ax.set_xticks([]); ax.set_yticks([])
                continue
            print(f"{mname:28s} {bname:9s} n={n:4d} " + " | ".join(f"{k} {a:.1f}% @ {t:.2f}k" for k, (a, t) in res.items()))
            ax.plot([res["T"][1], res["T->T"][1]], [res["T"][0], res["T->T"][0]], color="#b5b4af", lw=1.5, zorder=1)
            ax.plot([res["SB+F"][1], res["SB->T->T"][1]], [res["SB+F"][0], res["SB->T->T"][0]], color="#f2b49a", lw=1.5, zorder=1)
            for k, lab, col, mk in POL:
                a, t = res[k]
                ax.scatter([t], [a], s=110 if mk == "*" else 58, marker=mk, color=col, edgecolor=SURFACE, linewidth=1.5, zorder=3)
            ax.grid(color=GRID, lw=0.8); ax.set_axisbelow(True)
            for sp in ("top", "right"):
                ax.spines[sp].set_visible(False)
            for sp in ("left", "bottom"):
                ax.spines[sp].set_color(MUTED)
            ax.tick_params(colors=MUTED, labelsize=8)
            if r == 0:
                ax.set_title(bname, fontsize=11, color=INK)
            if c == 0:
                ax.set_ylabel(f"{mname}\naccuracy (%)", fontsize=9, color=INK)
            if r == len(MODELS) - 1:
                ax.set_xlabel("output tokens per problem (k)", fontsize=8.5, color=MUTED)
    handles = [plt.Line2D([], [], marker=mk, color=col, linestyle="", markersize=10 if mk == "*" else 7, label=lab) for _, lab, col, mk in POL]
    fig.legend(handles=handles, loc="upper center", ncol=5, frameon=False, fontsize=10, bbox_to_anchor=(0.5, 0.995))
    fig.suptitle("Every policy is given the same fact; the retry and the short think use the same free check", y=0.955, fontsize=10.5, color=MUTED)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    os.makedirs(f"{ROOT}/figs", exist_ok=True)
    fig.savefig(f"{ROOT}/figs/fig24_frontier.png", dpi=150, facecolor=SURFACE)
    print("wrote figs/fig24_frontier.png")


if __name__ == "__main__":
    main()
