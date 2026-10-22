"""HO-P (docs/prereg/PREREG_MODEL.md, addendum): the k-label pilot of analyze_policy_model.py on the held-out cells. Per model x seed x
held-out benchmark (the recipe's arm: OptMATH mips / thinks, OptiBench / BWOR / LogiOR formx / thinkfree, geometry fact / think):
CHEAP, FF, FFR (the next seed's cheap program as the second sample), THINK; pilot = pick the best policy on k random labelled items.
usage: python analyze_hop.py"""
import os, random, sys, types
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.modules.setdefault("analyze_u1", types.ModuleType("analyze_u1"))   # policies() needs none of it; its import needs ortools
from analyze_policy_model import policies  # noqa: E402
from analyze_ho import ag, ok_  # noqa: E402
from run_nlopt import RES as XRES, _rows  # noqa: E402

WORDS = [("optmath", "mips", "thinks"), ("optibench", "formx", "thinkfree"), ("bwor", "formx", "thinkfree"), ("logior", "formx", "thinkfree")]


def cells():
    import analyze_n10 as N
    from analyze_hogc import agree, load, ok, tok
    for m in ("oss20", "q14a", "q8b"):
        for b, a, th in WORDS:
            for s in (1, 2, 3):
                F, F2, T = ({r["id"]: r for r in _rows(f"{XRES}/opt_{m}_{b}_{x}_s{y}.jsonl")} for x, y in ((a, s), (a, s % 3 + 1), (th, s)))
                yield (m, b, s), [dict(f_ok=bool(f["correct"]), f_pass=ok_(f), f_tok=f["out_tokens"] or 0,
                                       agree=ok_(f) and ok_(F2[i]) and ag(f["pred"], F2[i]["pred"]), f2_tok=F2[i]["out_tokens"] or 0,
                                       t_ok=bool(T[i]["correct"]), t_tok=T[i]["out_tokens"] or 0) for i, f in F.items() if i in T and i in F2]
        for s in (1, 2, 3):
            F, F2, T = load(f"S2_HOG_{m}_geo_fact_s{s}"), load(f"S2_HOG_{m}_geo_fact_s{s % 3 + 1}"), load(f"S2_HOG_{m}_geo_think_s{s}")
            yield (m, "geometry", s), [dict(f_ok=ok(f), f_pass=N.geo_check(f)[0], f_tok=tok(f),
                                            agree=N.geo_check(f)[0] and N.geo_check(F2[k])[0] and agree(f, F2[k]), f2_tok=tok(F2[k]),
                                            t_ok=ok(T[k]), t_tok=tok(T[k])) for k, f in F.items() if k in T and k in F2]


def main():
    C = list(cells()); rng = random.Random(0)
    print(f"{len(C)} cells")
    for lam in (0.0, 0.5, 2.0):
        util = lambda P: {p: a - lam * t for p, (a, t) in P.items()}
        best_count = defaultdict(int); reg = defaultdict(list); sub = defaultdict(list)
        for name, items in C:
            U_full = util(policies(items)); best = max(U_full, key=U_full.get); best_count[best] += 1
            for k in (10, 30, 100):
                r = []
                for _ in range(1000):
                    U_p = util(policies(rng.sample(items, min(k, len(items))))); r.append(U_full[best] - U_full[max(U_p, key=U_p.get)])
                reg[k].append(sum(r) / len(r))
                if k == 30 and name[0] == "q8b" and name[1] in ("geometry", "bwor"):
                    sub["pilot"].append(sum(r) / len(r)); sub["FF"].append(U_full[best] - U_full["FF"])
        fixed = {p: sum(max(util(policies(it)).values()) - util(policies(it))[p] for _, it in C) / len(C) for p in ("CHEAP", "FF", "FFR", "THINK")}
        print(f"lambda {lam}: best policy counts {dict(best_count)} | mean regret of a pilot pick: "
              + ", ".join(f"k={k} {sum(v) / len(v):.2f}" for k, v in reg.items())
              + " | regret of always using one policy: " + ", ".join(f"{p} {v:.2f}" for p, v in fixed.items())
              + f" | Qwen3-8B geometry + BWOR (6 cells): k=30 pilot {sum(sub['pilot']) / 6:.2f}, always FF {sum(sub['FF']) / 6:.2f}")
    print("\nper cell (lambda 0.5): CHEAP / FF / FFR / THINK accuracy @ tokens(k)")
    for name, items in C:
        P = policies(items)
        print(f"  {' '.join(map(str, name)):20} n={len(items):3d} " + " | ".join(f"{p} {a:.1f}@{t:.1f}" for p, (a, t) in P.items()))


if __name__ == "__main__":
    main()
