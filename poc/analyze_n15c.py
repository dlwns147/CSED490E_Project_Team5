"""N15c (results/PREREG_N15.md): library tournament. Per model and problem: every library on the probe instances (instance 0 of each
size, seed 1); keep the one with the most feasible plans, ties by the better mean objective rank on the probes (no reference used);
commit to it on the problem's other items (both seeds). Probe tokens charged to the problem's committed items.
usage: python analyze_n15c.py"""
import json, os
from collections import defaultdict

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
PROBS = ["knapsack", "tsp", "color", "sched", "binpack", "vcover", "cvrp", "vrptw"]
LIBS = ["cpsat", "routing", "mip", "none"]
opt = lambda r: r["status"] == "ok" and r["feasible"] and r["gap"] == 0


def load(m, L):
    out = {}
    for sd in (1, 2):
        f = f"{RES}/co_S2_N15_{m}_{L}_s{sd}.jsonl"
        if L == "default" and sd == 1 and not os.path.exists(f):
            f = {"q32b": f"{RES}/co_S2_N10_co_nodoc_s1.jsonl", "oss20": f"{RES}/co_S2_N10m2_co_nodoc_s1.jsonl", "q36": f"{RES}/co_S2_N10m3_co_nodoc_s1.jsonl"}.get(m, f)
        if os.path.exists(f):
            for r in map(json.loads, open(f)):
                out[(r["key"], sd)] = r
    return out


pooled = defaultdict(lambda: [0, 0, 0])
for m in ("q32b", "oss20", "q36", "oss120"):
    D = {L: load(m, L) for L in LIBS + ["free", "default"]}
    acc = defaultdict(lambda: [0, 0, 0]); picks = {}
    for p in PROBS:
        libs = [L for L in LIBS if any(k[0].startswith(p + "-") for k in D[L])]
        probe = sorted({k for k in D["free"] if k[0].startswith(p + "-") and k[0].endswith("-0") and k[1] == 1})
        commit = sorted(k for k in D["free"] if k[0].startswith(p + "-") and not k[0].endswith("-0"))
        sign = -1 if p == "knapsack" else 1
        def rank_score(L):
            feas = sum(bool(D[L][k]["feasible"]) for k in probe)
            rk = 0
            for k in probe:   # objective rank among the libraries feasible on this probe (lower is better)
                vals = sorted(sign * D[x][k]["value"] for x in libs if D[x][k]["feasible"])
                rk += vals.index(sign * D[L][k]["value"]) if D[L][k]["feasible"] else len(libs)
            return (feas, -rk)
        best = max(libs, key=rank_score); picks[p] = best
        probe_tok = sum(D[L][k]["out_tokens"] for L in libs for k in probe)
        hind = max(libs, key=lambda L: sum(opt(D[L][k]) for k in commit))
        for name, L in (("tournament", best), ("free choice", "free"), ("default", "default"), ("best library (hindsight)", hind)):
            a = acc[name]; a[0] += sum(opt(D[L][k]) for k in commit); a[1] += sum(D[L][k]["out_tokens"] for k in commit) + (probe_tok if name == "tournament" else 0); a[2] += len(commit)
    print(f"{m}: picks {picks}")
    for name, (s, t, n) in acc.items():
        print(f"   {name:26s} {100 * s / n:5.1f}% @ {t / n / 1000:4.1f}k tokens per item (n = {n})")
        pooled[name][0] += s; pooled[name][1] += t; pooled[name][2] += n
print("pooled:", {k: f"{100 * s / n:.1f}% @ {t / n / 1000:.1f}k" for k, (s, t, n) in pooled.items()})
