"""PREREG_DIFF SOLVER (2026-11-26): MathConstruct instances no run has seen ("mcong").
Draws variations 5–7 of every problem with the benchmark's own generator (generate_multiple is prefix-stable, so these follow the
v0–v3 already in $POC_DATA/construct/instances.jsonl) and drops any statement equal to an earlier instance or to the published one (mcon).
usage: python poc/mc_newvar.py -> $POC_DATA/construct/instances_g.jsonl"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import run_compute as RC
pub = {p["problem"].split("\n\nFormat your reply as follows:\n")[0] for p in RC.mcon_problems()}
from math_construct.problems import get_all_problem_classes
base = os.path.join(os.path.dirname(RC.DATA), "construct")
seen = {json.loads(l)["statement"] for l in open(f"{base}/instances.jsonl")} | pub
rows = []
for c in sorted(get_all_problem_classes(), key=lambda c: c.config.name):
    try:
        V = c.generate_multiple(8, include_original=True)[1:]
    except Exception as e:
        print("skip", c.config.name, repr(e)[:80]); continue
    for v, p in enumerate(V):
        if v < 4 or str(p) in seen:
            continue
        seen.add(str(p))
        rows.append({"id": f"{c.config.name}__g{v}", "name": c.config.name, "v": v, "statement": str(p), "formatting": p.get_formatting(),
                     "params": json.loads(json.dumps(p.to_json()["param_values"], default=str))})
with open(f"{base}/instances_g.jsonl", "w") as f:
    for r in rows:
        f.write(json.dumps(r) + "\n")
print(len(rows), "instances of", len({r["name"] for r in rows}), "problems")
