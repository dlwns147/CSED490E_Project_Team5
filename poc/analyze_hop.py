"""HO-P (docs/prereg/PREREG_MODEL.md, addendum): the k-label pilot of analyze_policy_model.py on the held-out cells. Per model x seed x
held-out benchmark (the recipe's arm: OptMATH mips / thinks, OptiBench / BWOR / LogiOR formx / thinkfree, geometry fact / think):
CHEAP, FF, FFR (the next seed's cheap program as the second sample), THINK; pilot = pick the best policy on k random labelled items.
HO-N (PREREG_HON.md): `python analyze_hop.py q35` runs the same pilot on that model's cells (OptMATH with the library arm formx /
thinkfree: the mined-example arm needs the model's own runs on NL4OPT / IndustryOR, which it does not have).
HO-R (PREREG_HON.md): --repair adds FF-R0 (on a visible failure one cheap repair, results/x3/repair_<m>_<set>_<arm>_s<seed>.jsonl; if it
runs and prints a value it is the answer, else think); on geometry FF-R0 = FF (repair stays out there, HO-G-R).
HO-P2 (PREREG_MODEL.md): --fair uses the thinking arm given the same fact (formxt on OptiBench's HO-TF third / BWOR / LogiOR, thinkfact
on geometry; OptMATH unchanged for the development models, formxt for Qwen3.5-9B) as THINK and as every escalation.
HO-P3 (PREREG_MODEL.md): --gate adds FF-R+F (a passing program is the answer only if the 2k-token thinking-mode review says CORRECT,
results/x3/review_<m>_<set>_<arm>_s<seed>.jsonl, else THINK; review tokens counted) and keeps only cells with review rows for all 3 seeds;
it also prints the realized utility of the pilot with vs without the gate.
usage: python analyze_hop.py [--repair] [--fair] [--gate] [model ...]"""
import os, random, sys, types
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.modules.setdefault("analyze_u1", types.ModuleType("analyze_u1"))   # policies() needs none of it; its import needs ortools
from analyze_policy_model import policies as policies4  # noqa: E402
from analyze_ho import ag, ok_  # noqa: E402
from run_nlopt import RES as XRES, _rows  # noqa: E402

WORDS = [("optmath", "mips", "thinks"), ("optibench", "formx", "thinkfree"), ("bwor", "formx", "thinkfree"), ("logior", "formx", "thinkfree")]
WORDS_NEW = [("optmath", "formx", "thinkfree")] + WORDS[1:]   # a model never run on the development word problems (HO-N)
REPAIR = "--repair" in sys.argv
GATE = "--gate" in sys.argv
if "--fair" in sys.argv:
    WORDS = [("optmath", "mips", "thinks")] + [(b, "formx", "formxt") for b in ("optibench", "bwor", "logior")]
    WORDS_NEW = [("optmath", "formx", "formxt")] + WORDS[1:]
GEO_THINK = "thinkfact" if "--fair" in sys.argv else "think"


def policies(items):
    out = policies4(items)
    if REPAIR:
        n = len(items); a = t = 0
        for it in items:
            r = it.get("r")   # (repaired program runs, right, tokens) or None; geometry rows carry none: FF-R0 = FF
            if it["f_pass"]:
                a += it["f_ok"]; t += it["f_tok"]
            elif r and r[0]:
                a += r[1]; t += it["f_tok"] + r[2]
            else:
                a += it["t_ok"]; t += it["f_tok"] + (r[2] if r else 0) + it["t_tok"]
        out["FF-R0"] = (100 * a / n, t / n / 1000)
    if GATE:
        n = len(items); a = t = 0
        for it in items:
            v = it.get("v")   # (review says CORRECT, review tokens) or None (no review row: escalate)
            acc = it["f_pass"] and bool(v and v[0])
            a += it["f_ok"] if acc else it["t_ok"]
            t += it["f_tok"] + (v[1] if it["f_pass"] and v else 0) + (0 if acc else it["t_tok"])
        out["FF-R+F"] = (100 * a / n, t / n / 1000)
    return out


def cells(models=("oss20", "q14a", "q8b")):
    import analyze_n10 as N
    from analyze_hogc import agree, load, ok, tok
    for m in models:
        for b, a, th in (WORDS if m in ("oss20", "q14a", "q8b") else WORDS_NEW):
            for s in (1, 2, 3):
                F, F2, T = ({r["id"]: r for r in _rows(f"{XRES}/opt_{m}_{b}_{x}_s{y}.jsonl")} for x, y in ((a, s), (a, s % 3 + 1), (th, s)))
                R = {r["id"]: (ok_(r), bool(r["correct"]), r.get("out_tokens") or 0) for r in _rows(f"{XRES}/repair_{m}_{b}_{a}_s{s}.jsonl")}
                V = {r["id"]: (bool(r["accept"]), r.get("out_tokens") or 0) for r in _rows(f"{XRES}/review_{m}_{b}_{a}_s{s}.jsonl")}
                if GATE and not all(os.path.exists(f"{XRES}/review_{m}_{b}_{a}_s{x}.jsonl") for x in (1, 2, 3)):
                    continue
                yield (m, b, s), [dict(v=V.get(i), f_ok=bool(f["correct"]), f_pass=ok_(f), f_tok=f["out_tokens"] or 0,
                                       agree=ok_(f) and ok_(F2[i]) and ag(f["pred"], F2[i]["pred"]), f2_tok=F2[i]["out_tokens"] or 0,
                                       t_ok=bool(T[i]["correct"]), t_tok=T[i]["out_tokens"] or 0, r=R.get(i)) for i, f in F.items() if i in T and i in F2]
        for s in (1, 2, 3):
            if GATE and not all(os.path.exists(f"{XRES}/review_{m}_geo_fact_s{x}.jsonl") for x in (1, 2, 3)):
                continue
            V = {r["id"]: (bool(r["accept"]), r.get("out_tokens") or 0) for r in _rows(f"{XRES}/review_{m}_geo_fact_s{s}.jsonl")}
            F, F2, T = load(f"S2_HOG_{m}_geo_fact_s{s}"), load(f"S2_HOG_{m}_geo_fact_s{s % 3 + 1}"), load(f"S2_HOG_{m}_geo_{GEO_THINK}_s{s}")
            yield (m, "geometry", s), [dict(v=V.get("|".join(map(str, k))), f_ok=ok(f), f_pass=N.geo_check(f)[0], f_tok=tok(f),
                                            agree=N.geo_check(f)[0] and N.geo_check(F2[k])[0] and agree(f, F2[k]), f2_tok=tok(F2[k]),
                                            t_ok=ok(T[k]), t_tok=tok(T[k])) for k, f in F.items() if k in T and k in F2]


def main():
    C = list(cells([a for a in sys.argv[1:] if not a.startswith("--")] or ("oss20", "q14a", "q8b"))); rng = random.Random(0)
    print(f"{len(C)} cells")
    for lam in (0.0, 0.5, 2.0):
        util = lambda P: {p: a - lam * t for p, (a, t) in P.items()}
        best_count = defaultdict(int); reg = defaultdict(list); sub = defaultdict(list)
        for name, items in C:
            U_full = util(policies(items)); best = max(U_full, key=U_full.get); best_count[best] += 1
            for k in (10, 30, 100):
                r = []
                g = []
                for _ in range(1000):
                    U_p = util(policies(rng.sample(items, min(k, len(items))))); r.append(U_full[best] - U_full[max(U_p, key=U_p.get)])
                    if GATE and k == 30:   # HO-P3: the same sample's pick without the gate
                        U5 = {q: u for q, u in U_p.items() if q != "FF-R+F"}; g.append(U_full[max(U_p, key=U_p.get)] - U_full[max(U5, key=U5.get)])
                reg[k].append(sum(r) / len(r))
                if g:
                    sub["gain6"].append(sum(g) / len(g)); sub["best6-5"].append(U_full[best] - max(u for q, u in U_full.items() if q != "FF-R+F"))
                if k == 30 and name[0] == "q8b" and name[1] in ("geometry", "bwor"):
                    sub["pilot"].append(sum(r) / len(r)); sub["FF"].append(U_full[best] - U_full["FF"])
        fixed = {p: sum(max(util(policies(it)).values()) - util(policies(it))[p] for _, it in C) / len(C) for p in policies(C[0][1])}
        if REPAIR:
            W = [it for nm, it in C if nm[1] != "geometry"]
            print(f"  word cells ({len(W)}): always FF {sum(max(util(policies(it)).values()) - util(policies(it))['FF'] for it in W) / len(W):.2f}, "
                  f"always FF-R0 {sum(max(util(policies(it)).values()) - util(policies(it))['FF-R0'] for it in W) / len(W):.2f}")
        if GATE:
            print(f"  HO-P3: 30-label pilot with the gate - without it: {sum(sub['gain6']) / len(C):+.2f} (cells where it is worse: "
                  f"{sum(x < 0 for x in sub['gain6'])}); best of six - best of five: {sum(sub['best6-5']) / len(C):+.2f}")
        print(f"lambda {lam}: best policy counts {dict(best_count)} | mean regret of a pilot pick: "
              + ", ".join(f"k={k} {sum(v) / len(v):.2f}" for k, v in reg.items())
              + " | regret of always using one policy: " + ", ".join(f"{p} {v:.2f}" for p, v in fixed.items())
              + (f" | Qwen3-8B geometry + BWOR (6 cells): k=30 pilot {sum(sub['pilot']) / 6:.2f}, always FF {sum(sub['FF']) / 6:.2f}" if sub["pilot"] else ""))
    print("\nper cell (lambda 0.5): CHEAP / FF / FFR / THINK accuracy @ tokens(k)")
    for name, items in C:
        P = policies(items)
        print(f"  {' '.join(map(str, name)):20} n={len(items):3d} " + " | ".join(f"{p} {a:.1f}@{t:.1f}" for p, (a, t) in P.items()))


if __name__ == "__main__":
    main()
