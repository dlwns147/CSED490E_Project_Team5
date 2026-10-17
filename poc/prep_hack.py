"""Build the PoC-#2 benchmark: (problem, reference solutions, subtly-wrong solution) triples.

Selection, per CodeContests problem (test+valid splits):
  * >=3 Python-3 reference solutions that pass every kept test and AGREE with each other
    (problems whose references disagree probably need a special checker -> dropped).
  * one "subtle" wrong Python-3 solution: passes all public tests, gets WRONG ANSWER
    (not TLE/RE) on at least one private/generated test. We keep the known breaking test
    as an oracle, so every item is provably hackable.
"""
import glob
import json
import random
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from sandbox import run_python, same_output  # noqa: E402

PY3 = 3
N_GEN = 30         # generated tests kept per problem
MAX_REF = 4        # reference candidates tried
MAX_WRONG = 12     # wrong candidates tried
rng = random.Random(0)


def tests_of(r):
    ts = []
    for k in ("public_tests", "private_tests"):
        ts += [(k, i, o) for i, o in zip(r[k]["input"], r[k]["output"])]
    g = r["generated_tests"]
    ts += [("generated_tests", i, o) for i, o in list(zip(g["input"], g["output"]))[:N_GEN]]
    return [t for t in ts if len(t[1]) < 200_000]


def run_suite(code, tests, tl, stop_on_fail=True):
    """Return list of (kind, verdict) where verdict in ok/wa/re/tle; stops at first fail."""
    res = []
    for kind, inp, out in tests:
        r = run_python(code, inp, timeout=tl)
        v = "ok" if r.status == "ok" and same_output(r.stdout, out) else ("wa" if r.status == "ok" else r.status)
        res.append((kind, v, r.stdout))
        if v != "ok" and stop_on_fail:
            break
    return res


def process(r):
    tl = min(6.0, max(2.0, 3 * (r["time_limit"]["seconds"] + r["time_limit"]["nanos"] / 1e9)))
    tests = tests_of(r)
    sols = [c for c, l in zip(r["solutions"]["solution"], r["solutions"]["language"]) if l == PY3]
    bads = [c for c, l in zip(r["incorrect_solutions"]["solution"], r["incorrect_solutions"]["language"]) if l == PY3]
    if len(sols) < 3 or not bads or len(tests) < 5:
        return None
    rng_l = random.Random(r["name"])
    rng_l.shuffle(sols); rng_l.shuffle(bads)
    refs = []
    for c in sols[:MAX_REF]:
        rs = run_suite(c, tests, tl)
        if len(rs) == len(tests) and all(v == "ok" for _, v, _ in rs):
            refs.append(c)
        if len(refs) == 3:
            break
    if len(refs) < 3:
        return None
    wrong = None
    for c in bads[:MAX_WRONG]:
        rs = run_suite(c, tests, tl)
        fail = [x for x in rs if x[1] != "ok"]
        if not fail:
            continue
        kind, v, _ = fail[0]
        if kind != "public_tests" and v == "wa":
            idx = len(rs) - 1
            wrong = dict(code=c, breaking_input=tests[idx][1], breaking_output=tests[idx][2],
                         n_tests_passed=idx)
            break
    if wrong is None:
        return None
    return dict(name=r["name"], description=r["description"], cf_rating=int(r["cf_rating"]),
                cf_tags=list(r["cf_tags"]), time_limit=tl, refs=refs, wrong=wrong,
                public_tests=[{"input": i, "output": o} for i, o in zip(r["public_tests"]["input"], r["public_tests"]["output"])])


import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root (was hard-coded)
if __name__ == "__main__":
    rows = []
    for sp in ("test", "valid"):
        df = pd.read_parquet(glob.glob(f"{ROOT}/data/code_contests/data/{sp}-*.parquet")[0])
        rows += [r for _, r in df.iterrows()]
    print("problems:", len(rows), flush=True)
    out = []
    with ThreadPoolExecutor(40) as ex:
        for k, item in enumerate(ex.map(process, rows)):
            if item:
                out.append(item)
            if k % 25 == 0:
                print(k, len(out), flush=True)
    with open(f"{ROOT}/data/hack_bench.jsonl", "w") as f:
        for it in out:
            f.write(json.dumps(it) + "\n")
    print("kept", len(out), "ratings", np.percentile([o["cf_rating"] for o in out], [10, 50, 90]))
