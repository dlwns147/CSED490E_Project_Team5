"""T1 summaries: per problem x arm — feasible rate, optimal rate, and invariance:
  consistent      = all variants feasible and the normalised objective identical across variants
  violation|base-optimal = among instances whose identity answer is optimal, share where some variant is NOT optimal
usage: analyze_cometa.py <tag>"""
import json
import sys
from collections import defaultdict

import numpy as np

import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root (was hard-coded)
rows = [json.loads(l) for l in open(f"{ROOT}/results/cometa_{sys.argv[1]}.jsonl")]
inst = defaultdict(dict)
for r in rows:
    inst[(r["prob"], r["n"], r["inst"], r["arm"])][r["variant"]] = r
print(f"{'prob':9s} {'n':>3s} {'arm':9s} {'feas':>5s} {'opt':>5s} {'consistent':>10s} {'viol|base-opt':>13s}  per-variant optimal rate")
agg = defaultdict(list)
for key in sorted({(p, n, a) for (p, n, i, a) in inst}):
    p, n, a = key
    ds = [d for (pp, nn, i, aa), d in inst.items() if (pp, nn, aa) == key]
    feas = np.mean([r["feasible"] for d in ds for r in d.values()])
    opt = np.mean([r["optimal"] for d in ds for r in d.values()])
    cons = np.mean([all(r["feasible"] for r in d.values()) and len({r["norm_value"] for r in d.values()}) == 1 for d in ds])
    base = [d for d in ds if d.get("identity", {}).get("optimal")]
    viol = np.mean([not all(r["optimal"] for r in d.values()) for d in base]) if base else float("nan")
    vnames = sorted({v for d in ds for v in d})
    pv = " ".join(f"{v[:7]}={np.mean([d[v]['optimal'] for d in ds if v in d]):.2f}" for v in vnames)
    print(f"{p:9s} {n:3d} {a:9s} {feas:5.2f} {opt:5.2f} {cons:10.2f} {viol:13.2f}  {pv}  (base-opt n={len(base)})")
    agg[a].append(cons)
print("mean consistency by arm:", {a: round(float(np.mean(v)), 2) for a, v in agg.items()})
