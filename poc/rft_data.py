"""RFT-C data (PREREG_DIFF, 2026-11-26): problem-level split of the 95 mcong problems and training instances for the training half.
Split: a problem is TRAIN if crc32(name) is even, else HELD-OUT (fixed before any training row). Training instances: the benchmark's own generator,
variations 8..40 of TRAIN problems only (generate_multiple is prefix-stable, so v0..v7 are the instances any evaluation has used), with every statement
equal to an earlier instance (instances.jsonl, instances_g.jsonl, the published mcon) dropped; at most 12 per problem.
usage: python poc/rft_data.py -> $POC_DATA/construct/rft_split.json, $POC_DATA/construct/instances_rft.jsonl"""
import json, os, sys, zlib
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import run_compute as RC
sys.path[:0] = [os.path.join(RC.MC, "src"), os.path.join(os.path.dirname(RC.MC), "pylib")]
from loguru import logger
logger.remove()
from math_construct.problems import get_all_problem_classes
base = os.path.join(os.path.dirname(RC.DATA), "construct")
G = [json.loads(l) for l in open(f"{base}/instances_g.jsonl")]; names = sorted({r["name"] for r in G})
train = [n for n in names if zlib.crc32(n.encode()) % 2 == 0]; held = [n for n in names if n not in train]
pub = {p["problem"].split("\n\nFormat your reply as follows:\n")[0] for p in RC.mcon_problems()}
seen = {json.loads(l)["statement"] for l in open(f"{base}/instances.jsonl")} | {r["statement"] for r in G} | pub
rows = []
for c in sorted(get_all_problem_classes(), key=lambda c: c.config.name):
    if c.config.name not in train:
        continue
    k = 0
    for v, p in enumerate(c.generate_multiple(40, include_original=True)[1:]):
        if v < 8 or str(p) in seen or k >= 12:
            continue
        seen.add(str(p)); k += 1
        rows.append({"id": f"{c.config.name}__r{v}", "name": c.config.name, "v": v, "statement": str(p), "formatting": p.get_formatting(),
                     "params": json.loads(json.dumps(p.to_json()["param_values"], default=str))})
json.dump({"train": train, "heldout": held}, open(f"{base}/rft_split.json", "w"), indent=0)
with open(f"{base}/instances_rft.jsonl", "w") as f:
    for r in rows:
        f.write(json.dumps(r) + "\n")
print(f"train problems {len(train)}, held-out {len(held)}; training instances {len(rows)} from {len({r['name'] for r in rows})} problems; "
      f"held-out mcong instances {sum(r['name'] in held for r in G)}, train-problem mcong instances {sum(r['name'] in train for r in G)}")
