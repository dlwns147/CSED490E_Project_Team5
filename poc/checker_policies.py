"""PoC #6c — grading POLICIES built from imperfect LLM checkers (no new generations; reuses checker2 outputs).

  exact            : exact match only
  best_checker     : checker with fewest selection-set errors (= run_checker2 'selected')
  per_problem      : per problem, use whichever of {exact, best checker} has fewer selection-set errors (ties -> exact)
  or_rule          : accept if exact match OR best checker accepts (a checker can only rescue, never newly reject)
  or_per_problem   : per problem, choose between exact and or_rule on the selection set
Selection set = even-indexed labelled solutions, test set = odd-indexed (same split as run_checker2).
"""
import json
import sys

import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root (was hard-coded)
sys.path.insert(0, f"{ROOT}/poc")
from run_checker import collect_outputs, exact_verdicts, load_items, run_checker  # noqa: E402
from run_checker2 import score  # noqa: E402

tag = sys.argv[1]
RES = f"{ROOT}/results"
items = load_items(60)
outs_all = collect_outputs(items)
codes = {}
for g in map(json.loads, open(f"{RES}/checker2_gen_{tag}.jsonl")):
    if g["kind"] == "gen" and g["code"]:
        codes.setdefault(g["name"], []).append(g["code"])


def or_verdicts(a, b):
    return {k: [[("x" if x == "x" else (x is True or y is True)) for x, y in zip(ra, rb)] for ra, rb in zip(a[k], b[k])]
            for k in ("cor", "inc")}


tot = {p: [0, 0, 0] for p in ("exact", "best_checker", "per_problem", "or_rule", "or_per_problem")}
for it in items:
    outs = outs_all[it["name"]]
    cs, ins = range(0, len(it["cor"]), 2), range(0, len(it["inc"]), 2)
    ct, itest = range(1, len(it["cor"]), 2), range(1, len(it["inc"]), 2)
    ex = exact_verdicts(it, outs)
    cands = [v for v in (run_checker(c, it, outs) for c in codes.get(it["name"], [])) if v]
    if not cands:
        best = ex
    else:
        best = min(cands, key=lambda v: sum(score(v, cs, ins)[:2]))
    orv = or_verdicts(ex, best)
    sel = lambda v: sum(score(v, cs, ins)[:2])  # noqa: E731
    pols = {"exact": ex, "best_checker": best,
            "per_problem": best if sel(best) < sel(ex) else ex,
            "or_rule": orv,
            "or_per_problem": orv if sel(orv) < sel(ex) else ex}
    for p, v in pols.items():
        fr, miss, n = score(v, ct, itest)
        tot[p][0] += fr; tot[p][1] += miss; tot[p][2] += n
print(f"{tag}: held-out TEST set, {len(items)} multi-answer problems")
for p, (fr, miss, n) in tot.items():
    print(f"  {p:15s} errors {fr + miss:4d}/{n}  (false rejects {fr}, misses {miss})")
