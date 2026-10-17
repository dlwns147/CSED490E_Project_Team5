"""Re-judge saved single-input responses (no regeneration) after a parsing fix."""
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from run_hack import check_input, extract_input
tag = sys.argv[1]
path = f"/NAS/SJ/POSTECH/nlp/results/hack_{tag}.jsonl"
items = {json.loads(l)["name"]: json.loads(l) for l in open("/NAS/SJ/POSTECH/nlp/data/hack_bench.jsonl")}
rows, changed, caches = [json.loads(l) for l in open(path)], 0, {}
for r in rows:
    if not r["strategy"].startswith("stress"):
        v = check_input(items[r["name"]], extract_input(r["response"]), caches.setdefault(r["name"], {}))
        changed += v != r["verdict"]
        r["verdict"] = v
open(path, "w").write("".join(json.dumps(r) + "\n" for r in rows))
print("rescored", len(rows), "changed", changed)
