"""N14 (results/PREREG_N14.md): adapting a verified source program to a problem with one more rule, vs writing from scratch.
Pooled over seeds 1-3: optimal / feasible rate and mean output tokens per (model, destination, condition); paired sign test good vs
scratch on (instance, seed). usage: python analyze_n14.py"""
import json, math, os

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
MODELS = {"q32b": "S2_N10", "q36": "S2_N10m3", "oss20": "S2_N10m2"}
opt = lambda r: r["status"] == "ok" and r["feasible"] and r["gap"] == 0


def rows(path, dst):
    return {r["key"]: r for r in map(json.loads, open(path)) if r["prob"] == dst} if os.path.exists(path) else None


for m, pre in MODELS.items():
    for dst in ("cvrp", "vrptw"):
        conds = {"scratch (sheet)": [rows(f"{RES}/co_{pre}_co_doc_s{sd}.jsonl", dst) for sd in (1, 2, 3)],
                 "exact snippet (ref., seed 1)": [rows(f"{RES}/co_{pre}_co_snippet_s1.jsonl", dst)],
                 "adapt verified related": [rows(f"{RES}/co_S2_N14_{m}_{dst}_good_s{sd}.jsonl", dst) for sd in (1, 2, 3)],
                 "adapt failing related": [rows(f"{RES}/co_S2_N14_{m}_{dst}_bad_s{sd}.jsonl", dst) for sd in (1, 2, 3)],
                 "adapt verified unrelated": [rows(f"{RES}/co_S2_N14_{m}_{dst}_unrel_s{sd}.jsonl", dst) for sd in (1, 2, 3)]}
        if any(R is None for R in conds["adapt verified related"]):
            continue
        out = []
        for name, Rs in conds.items():
            Rs = [R for R in Rs if R]
            if not Rs:
                continue
            allr = [r for R in Rs for r in R.values()]
            out.append(f"{name} {sum(map(opt, allr))}/{len(allr)} opt, {sum(bool(r['feasible']) for r in allr)} feas @ {sum(r['out_tokens'] for r in allr) / len(allr) / 1000:.1f}k")
        S, G = conds["scratch (sheet)"], conds["adapt verified related"]
        w = sum(opt(G[i][k]) and not opt(S[i][k]) for i in range(3) for k in G[i]); l = sum(opt(S[i][k]) and not opt(G[i][k]) for i in range(3) for k in G[i])
        p = min(1, 2 * sum(math.comb(w + l, j) for j in range(min(w, l) + 1)) / 2 ** (w + l)) if w + l else 1
        print(f"{m} {dst}: " + " | ".join(out) + f" | good vs scratch {w}:{l} p={p:.3g}", flush=True)
