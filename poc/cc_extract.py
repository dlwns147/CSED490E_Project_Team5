"""Extract every Codeforces geometry-tagged problem of CodeContests (train + valid + test) into results/h2/cc_geometry_full.json,
in the schema of cc_geometry_local.json. Generated tests are cut to the first 60: run_cc evaluates on the first 30 (MAX_GEN); 30-59 are inputs for label-free selection.
usage: python -I cc_extract.py <parquet_dir> [<parquet_dir> ...]"""
import glob, json, sys

import pandas as pd

import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root (was hard-coded)
OUT = f"{ROOT}/results/h2/cc_geometry_full.json"
MAX_GEN = 60
CPP, PY3 = 2, 3   # CodeContests language codes


def tests(t, kind, cap=None):
    pairs = list(zip(t["input"], t["output"]))[:cap]
    return [{"input": i, "output": o, "kind": kind} for i, o in pairs]


rows, seen = [], set()
for d in sys.argv[1:]:
    for f in sorted(glob.glob(f"{d}/*.parquet")):
        split = f.split("/")[-1].split("-")[0]
        df = pd.read_parquet(f)
        for _, r in df[df["cf_tags"].apply(lambda t: any("geometry" in x for x in t))].iterrows():
            if r["name"] in seen:
                continue
            seen.add(r["name"])
            sol = r["solutions"]
            src = lambda lang, k: [s for s, l in zip(sol["solution"], sol["language"]) if int(l) == lang][:k]
            rows.append({"name": r["name"], "rating": int(r["cf_rating"]), "time_limit": int(r["time_limit"]["seconds"] or 0) if r["time_limit"] is not None else 0,
                         "description": r["description"],
                         "tests": tests(r["public_tests"], "public") + tests(r["private_tests"], "private") + tests(r["generated_tests"], "generated", MAX_GEN),
                         "py3": src(PY3, 5), "cpp": src(CPP, 5), "tags": list(r["cf_tags"]), "split": split})
json.dump(rows, open(OUT, "w"))
print(f"{len(rows)} geometry problems -> {OUT}; splits:", {s: sum(r['split'] == s for r in rows) for s in ('train', 'valid', 'test')},
      "with a C++ reference:", sum(bool(r["cpp"]) for r in rows), "rated:", sum(r["rating"] > 0 for r in rows))
