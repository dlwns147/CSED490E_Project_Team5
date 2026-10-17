"""N15f (results/PREREG_N15.md): library fallback cascade (first feasible plan wins; no reference used).
usage: python analyze_n15f.py"""
import json, os, statistics as st

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
opt = lambda r: r["status"] == "ok" and r["feasible"] and r["gap"] == 0
feas = lambda r: r["status"] == "ok" and r["feasible"]
print("synthetic (8 problems, seeds 1-2): optimal % @ tokens per instance")
for m in ("q32b", "oss20", "q36", "oss120"):
    D = {L: {(r["key"], sd): r for sd in (1, 2) for r in map(json.loads, open(f"{RES}/co_S2_N15_{m}_{L}_s{sd}.jsonl"))} for L in ("free", "cpsat", "routing", "mip", "none")}
    keys = sorted(D["free"]); s = t = 0
    for k in keys:
        for L in ("free", "cpsat", "mip", "none"):
            r = D[L][k]; t += r["out_tokens"]
            if feas(r):
                s += opt(r); break
    print(f"  {m}: cascade free -> CP-SAT -> MIP -> none {100 * s / len(keys):.1f}% @ {t / len(keys) / 1000:.1f}k")
H5 = f"{RES}/h5"; REF = {n: v["makespan"] for n, v in json.load(open(f"{H5}/ref.json")).items()}
print("job-shop (la01-la40, seeds 1-2): feasible, within 5%, tokens per instance")
for m in ("q32b", "q36", "oss20_low", "oss120_low"):
    D = {c: {(r["name"], sd): r for sd in (1, 2) for r in map(json.loads, open(f"{H5}/sol_{m}_{c}_s{sd}.jsonl"))} for c in ("plain", "none")}
    f = w5 = t = 0
    for k in D["plain"]:
        for c in ("plain", "none"):
            r = D[c][k]; t += r["out_tokens"] or 0
            if r["feasible"]:
                f += 1; w5 += r["makespan"] <= 1.05 * REF[k[0]]; break
    print(f"  {m}: cascade default -> none: feasible {f}/80, within 5% {w5}, tokens {t / 80 / 1000:.1f}k")
