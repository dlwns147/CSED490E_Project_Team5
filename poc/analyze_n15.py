"""N15 (docs/prereg/PREREG_N15.md): which OR-Tools solver library should solver code use? Per model: optimal (feasible) counts per problem
and condition (seeds 1-2 pooled), output tokens, the library actually imported under free choice, and the four predictions.
usage: python analyze_n15.py"""
import json, os
from collections import Counter

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
PROBS = ["knapsack", "tsp", "color", "sched", "binpack", "vcover", "cvrp", "vrptw"]
ROUT = {"tsp", "cvrp", "vrptw"}
MODELS = {"q32b": "S2_N10", "oss20": "S2_N10m2", "q36": "S2_N10m3", "oss120": None}
LIBS = ["free", "cpsat", "routing", "mip", "none", "default"]
opt = lambda r: r["status"] == "ok" and r["feasible"] and r["gap"] == 0


def lib_of(code):
    if not code:
        return "no code"
    u = [n for n, k in (("cpsat", "cp_model"), ("routing", "pywrapcp"), ("mip", "pywraplp")) if k in code]
    return "+".join(u) if u else "none"


def files(m, L, sd):
    if L == "default" and sd == 1 and MODELS[m]:
        return f"{RES}/co_{MODELS[m]}_co_nodoc_s1.jsonl"
    return f"{RES}/co_S2_N15_{m}_{L}_s{sd}.jsonl"


for m in MODELS:
    T = {}
    for L in LIBS:
        rows = [r for sd in (1, 2, 3) if os.path.exists(files(m, L, sd)) for r in map(json.loads, open(files(m, L, sd)))]
        if rows:
            T[L] = rows
    if "free" not in T:
        continue
    print(f"\n=== {m} (optimal of runs per problem, seeds pooled; tokens = mean output tokens)")
    print("  " + "condition".ljust(9) + "".join(p[:7].rjust(9) for p in PROBS) + "   total   tokens")
    best = {}
    for L, rows in T.items():
        cells, tot, n = [], 0, 0
        for p in PROBS:
            R = [r for r in rows if r["prob"] == p]
            if R:
                k = sum(map(opt, R)); cells.append(f"{k}/{len(R)}".rjust(9)); tot += k; n += len(R)
                if L not in ("free", "default"):
                    best.setdefault(p, []).append((k / len(R), L))
            else:
                cells.append("-".rjust(9))
        print("  " + L.ljust(9) + "".join(cells) + f"  {100 * tot / n:5.1f}%  {sum(r['out_tokens'] for r in rows) / len(rows) / 1000:5.1f}k")
    used = Counter((r["prob"], lib_of(r.get("code"))) for r in T["free"])
    print("  free choice imports:", {p: dict((l, c) for (q, l), c in used.items() if q == p) for p in PROBS})
    fr = {p: sum(opt(r) for r in T["free"] if r["prob"] == p) / sum(r["prob"] == p for r in T["free"]) for p in PROBS}
    p1 = sum(max(best[p])[0] - fr[p] >= 0.10 for p in PROBS)
    weakest_mip = sum(1 for p in PROBS if [l for a, l in sorted(best[p]) if l != "none"][:1] == ["mip"])
    top = {p: max(best[p])[1] for p in PROBS}
    picks_best = sum(1 for p in PROBS if Counter(lib_of(r.get("code")) for r in T["free"] if r["prob"] == p).most_common(1)[0][0] == top[p])
    p4 = {p: (sum(opt(r) for r in T.get("cpsat", []) if r["prob"] == p), sum(opt(r) for r in T.get("routing", []) if r["prob"] == p)) for p in ("cvrp", "vrptw")}
    print(f"  P1: best forced library beats free choice by >= 10 points on {p1} / 8 problems (prediction: >= 2)")
    print(f"  P2: MIP is the weakest library (among cpsat / routing / mip) on {weakest_mip} / 8 problems (prediction: >= 5)")
    print(f"  P3: free choice's most-used library = the best forced library on {picks_best} / 8 problems (prediction: <= 60%, i.e. <= 4)")
    print(f"  P4: CP-SAT vs routing optimal on cvrp / vrptw: {p4}")
