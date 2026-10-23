"""HO-L (docs/prereg/PREREG_MODEL.md, addendum): a label-free pilot. On k random items of a held-out cell (the 45 HO-P cells), estimate the
accuracy of the cheap program F and of thinking T on the items F's free check passes from the agreement of F, a second cheap sample F2
and T (triplet method: P(X = Y) = a_X a_Y when wrong answers rarely coincide), and choose FF or THINK by the estimated utility; compared
with the labelled pilot on {FF, THINK}, always FF and always THINK (regret against the better of the two on the full cell, lambda 0.5).
usage: python analyze_hol.py"""
import os, random, sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_ho import ag, ok_  # noqa: E402
from analyze_hop import WORDS  # noqa: E402
from run_nlopt import RES as XRES, _rows  # noqa: E402

LAM = 0.5


def cells(models=("oss20", "q14a", "q8b")):
    import analyze_n10 as N
    from analyze_hogc import load, ok, outs, same, tok
    pa = lambda r: r["pred"] if ok_(r) else None
    for m in models:
        for b, a, th in WORDS:
            for s in (1, 2, 3):
                F, F2, T = ({r["id"]: r for r in _rows(f"{XRES}/opt_{m}_{b}_{x}_s{y}.jsonl")} for x, y in ((a, s), (a, s % 3 + 1), (th, s)))
                eq = lambda x, y: x is not None and y is not None and ag(x, y)
                yield (m, b, s), [dict(f_pass=ok_(f), f_ok=bool(f["correct"]), t_ok=bool(T[i]["correct"]), f_tok=f["out_tokens"] or 0,
                                       t_tok=T[i]["out_tokens"] or 0, ft=eq(pa(f), pa(T[i])), ff2=eq(pa(f), pa(F2[i])), f2t=eq(pa(F2[i]), pa(T[i])))
                                  for i, f in F.items() if i in T and i in F2]
        for s in (1, 2, 3):
            F, F2, T = load(f"S2_HOG_{m}_geo_fact_s{s}"), load(f"S2_HOG_{m}_geo_fact_s{s % 3 + 1}"), load(f"S2_HOG_{m}_geo_think_s{s}")
            o = lambda r: (lambda v: v if v and None not in v else None)(outs(r))
            eq = lambda x, y: x is not None and y is not None and all(same(p, q) for p, q in zip(x, y))
            yield (m, "geometry", s), [dict(f_pass=N.geo_check(f)[0], f_ok=ok(f), t_ok=ok(T[k]), f_tok=tok(f), t_tok=tok(T[k]),
                                            ft=eq(o(f), o(T[k])), ff2=eq(o(f), o(F2[k])), f2t=eq(o(F2[k]), o(T[k])))
                                       for k, f in F.items() if k in T and k in F2]


def util(items):
    n = len(items)
    ff = sum((it["f_ok"] if it["f_pass"] else it["t_ok"]) for it in items) / n; th = sum(it["t_ok"] for it in items) / n
    tff = sum(it["f_tok"] + (0 if it["f_pass"] else it["t_tok"]) for it in items) / n; tth = sum(it["t_tok"] for it in items) / n
    return {"FF": 100 * ff - LAM * tff / 1000, "THINK": 100 * th - LAM * tth / 1000}


def label_free(items):
    P = [it for it in items if it["f_pass"]]
    if not P:
        return "THINK"
    A = {k: sum(it[k] for it in P) / len(P) for k in ("ft", "ff2", "f2t")}
    if min(A.values()) == 0:
        return "FF"
    aF = min(1.0, (A["ff2"] * A["ft"] / A["f2t"]) ** .5); aT = min(1.0, (A["ft"] * A["f2t"] / A["ff2"]) ** .5)
    n = len(items); tff = sum(it["f_tok"] + (0 if it["f_pass"] else it["t_tok"]) for it in items) / n; tth = sum(it["t_tok"] for it in items) / n
    return "FF" if 100 * len(P) / n * (aF - aT) + LAM * (tth - tff) / 1000 >= 0 else "THINK"


def main():
    C = list(cells(sys.argv[1:] or ("oss20", "q14a", "q8b"))); rng = random.Random(0)
    reg = defaultdict(list); picks = {}
    for name, items in C:
        U = util(items); best = max(U.values())
        r, nff = defaultdict(float), 0
        for _ in range(1000):
            pilot = rng.sample(items, min(30, len(items)))
            lf = label_free(pilot); Up = util(pilot); lab = max(Up, key=Up.get)
            r["label-free"] += (best - U[lf]) / 1000; r["labelled"] += (best - U[lab]) / 1000; nff += lf == "FF"
        r["always FF"], r["always THINK"] = best - U["FF"], best - U["THINK"]
        for k, v in r.items():
            reg[k].append(v)
        picks[name] = (nff / 1000, r["label-free"], r["labelled"], U["FF"] - U["THINK"])
    print(f"{len(C)} cells, lambda {LAM}, k = 30: mean regret " + ", ".join(f"{k} {sum(v) / len(v):.2f}" for k, v in reg.items()))
    for grp in (("q8b", "geometry"), ("q8b", "bwor")):
        g = [v for k, v in picks.items() if k[:2] == grp]
        print(f"  {' '.join(grp)}: label-free keeps FF in {100 * sum(x[0] for x in g) / len(g):.0f}% of pilots, regret {sum(x[1] for x in g) / len(g):.2f} "
              f"(labelled {sum(x[2] for x in g) / len(g):.2f})")
    print("per cell: share of pilots keeping FF | regret label-free / labelled | full-cell U(FF) - U(THINK)")
    for k, (f, a, b, d) in picks.items():
        print(f"  {' '.join(map(str, k)):20} {100 * f:4.0f}% | {a:5.2f} / {b:5.2f} | {d:+6.1f}")


if __name__ == "__main__":
    main()
