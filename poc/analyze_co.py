"""CO1 summaries. usage: analyze_co.py <tag> [...]  — per problem x size x arm: feasibility, mean gap, within-1%, vs greedy."""
import json
import sys
from collections import defaultdict

import numpy as np

import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root (was hard-coded)
RES = f"{ROOT}/results"
refs = json.load(open(f"{RES}/co_refs.json"))
for tag in sys.argv[1:]:
    rows = [json.loads(l) for l in open(f"{RES}/co_{tag}.jsonl")]
    print(f"== {tag}  ({len(rows)} runs)")
    by = defaultdict(list)
    for r in rows:
        by[(r["prob"], r["n"], r["arm"])].append(r)
    print(f"  {'prob':9s} {'n':>3s} {'arm':9s} {'feas':>5s} {'gap%':>6s} {'<=1%':>5s} {'beats greedy':>12s}  status")
    for (p, n, arm), rs in sorted(by.items()):
        gaps = [r["gap"] for r in rs if r["feasible"]]
        beat = []
        for r in rs:
            g = refs[r["key"]]["greedy"]
            if r["feasible"]:
                beat.append(r["value"] > g if p == "knapsack" else r["value"] < g)
            else:
                beat.append(False)
        st = defaultdict(int)
        for r in rs:
            st[r["status"]] += 1
        print(f"  {p:9s} {n:3d} {arm:9s} {np.mean([r['feasible'] for r in rs]):5.2f} "
              f"{(np.mean(gaps) if gaps else float('nan')):6.1f} {np.mean([r['feasible'] and r['gap'] <= 1 for r in rs]):5.2f} "
              f"{np.mean(beat):12.2f}  {dict(st)}")
