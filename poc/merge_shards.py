"""Append the rows of NLOPT_SHARD shard files (run_nlopt.py) to their main results file, skipping ids it already has, then remove the shards.
usage: python merge_shards.py results/x3/opt_<tag>_<mode>_s<seed>.jsonl ..."""
import glob, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_nlopt import _rows  # noqa: E402

for path in sys.argv[1:]:
    have = {r["id"] for r in _rows(path)}
    shards = sorted(glob.glob(path[:-len(".jsonl")] + ".shard*of*.jsonl"))
    new = [r for s in shards for r in _rows(s) if r["id"] not in have and not have.add(r["id"])]
    with open(path, "a") as f:
        for r in new:
            f.write(json.dumps(r) + "\n")
    for s in shards:
        os.remove(s)
    print(path, f"+{len(new)} rows from {len(shards)} shards -> {len(have)}")
