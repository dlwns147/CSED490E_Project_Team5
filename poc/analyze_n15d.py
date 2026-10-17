"""N15d (results/PREREG_N15.md): per-instance library portfolio: keep the feasible plan with the best objective among the libraries
run on that instance (no reference used). usage: python analyze_n15d.py"""
import json, os

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
opt = lambda r: r["status"] == "ok" and r["feasible"] and r["gap"] == 0


def load(m, L):
    out = {}
    for sd in (1, 2, 3):
        f = f"{RES}/co_S2_N15_{m}_{L}_s{sd}.jsonl"
        if os.path.exists(f):
            for r in map(json.loads, open(f)):
                out[(r["key"], sd)] = r
    return out


for m in ("q32b", "oss20", "q36", "oss120"):
    D = {L: load(m, L) for L in ("free", "cpsat", "routing", "mip", "none")}
    keys = sorted(D["free"])
    line = []
    for name, libs in (("free", ["free"]), ("free+mip", ["free", "mip"]), ("free+none", ["free", "none"]),
                       ("all four", ["cpsat", "routing", "mip", "none"]), ("all + free", ["free", "cpsat", "routing", "mip", "none"])):
        s = t = 0
        for k in keys:
            rs = [D[L][k] for L in libs if k in D[L]]
            t += sum(r["out_tokens"] for r in rs)
            sign = -1 if k[0].startswith("knapsack") else 1
            feas = [r for r in rs if r["status"] == "ok" and r["feasible"]]
            if feas:
                s += opt(min(feas, key=lambda r: sign * r["value"]))
        line.append(f"{name} {100 * s / len(keys):.1f}% @ {t / len(keys) / 1000:.1f}k")
    print(m + ": " + " | ".join(line))
