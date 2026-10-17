"""T2 — can LLMs find inputs that break LLM-written GEOMETRY code? (degeneracy-targeted counterexamples)

Targets: real buggy programs harvested from the cross-variant runs (geocross_*.jsonl): programs that are correct on
the identity instance but fail some semantics-preserving variant (classes degen_only / transform_only / big_only /
degen+big). Oracle: exact integer geometry (run_geo.answer). An input BREAKS a program if it is valid (simple polygon,
query not on the boundary, ...) and the program's output differs from the exact answer (or it crashes).
Strategies (each gets up to B=50 inputs):
  rand        : non-LLM random instances (as in G2)
  rand_degen  : non-LLM, degeneracy-biased: random instance + one of {collinear, duplicate, vertex-ray, touching,
                huge offset, rot90/mirror} (the cheap structured baseline)
  llm_blind   : LLM writes a random input generator from the problem statement only
  llm_code    : LLM sees the buggy program and writes a generator targeting its bug
"""
import argparse
import glob
import json
import os
import random
import re
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
from llm import chat, last_block  # noqa: E402
from run_geo import answer, base_instance, on_seg, orient, pip, render, variants  # noqa: E402
from sandbox import run_python  # noqa: E402

RES = "/NAS/SJ/POSTECH/nlp/results"
B = 50
SIZES = {"hull": 10, "area2": 8, "pip": 8, "segs": 6, "close": 10}
FMT = {
    "hull": "first line n, then n lines `x y` (integer points)",
    "close": "first line n (n >= 2), then n lines `x y` (integer points)",
    "area2": "first line n, then n lines `x y`: the vertices of a SIMPLE polygon in order",
    "pip": "first line n, then n lines `x y`: a SIMPLE polygon in order, then a line `qx qy`: a query point NOT on the polygon boundary",
    "segs": "first line m, then m lines `x1 y1 x2 y2` (segments with distinct endpoints)",
}
DESC = {
    "hull": "count the vertices of the convex hull (points on hull edges do not count; duplicates count once)",
    "area2": "print twice the area of a simple polygon",
    "pip": "print yes if the query point is strictly inside the polygon, else no",
    "segs": "count the pairs of segments that intersect (touching counts)",
    "close": "print the squared distance of the closest pair of points",
}


def parse(task, text):
    nums = [int(t) for t in re.findall(r"-?\d+", text)]
    try:
        if task in ("hull", "close", "area2", "pip"):
            n = nums[0]
            pts = [(nums[1 + 2 * i], nums[2 + 2 * i]) for i in range(n)]
            if task in ("hull", "close"):
                return {"P": pts} if n >= (2 if task == "close" else 1) else None
            x = {"poly": pts}
            if task == "pip":
                x["q"] = (nums[1 + 2 * n], nums[2 + 2 * n])
            return x
        m = nums[0]
        return {"S": [((nums[1 + 4 * i], nums[2 + 4 * i]), (nums[3 + 4 * i], nums[4 + 4 * i])) for i in range(m)]}
    except (IndexError, ValueError):
        return None


def simple_polygon(P):
    n = len(P)
    if n < 3 or len(set(P)) != n:
        return False
    E = [(P[i], P[(i + 1) % n]) for i in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if j == i + 1 or (i == 0 and j == n - 1):
                continue
            (a, b), (c, d) = E[i], E[j]
            d1, d2, d3, d4 = orient(c, d, a), orient(c, d, b), orient(a, b, c), orient(a, b, d)
            if (d1 * d2 < 0 and d3 * d4 < 0) or on_seg(c, d, a) or on_seg(c, d, b) or on_seg(a, b, c) or on_seg(a, b, d):
                return False
    return sum(P[i][0] * P[(i + 1) % n][1] - P[(i + 1) % n][0] * P[i][1] for i in range(n)) != 0


def valid(task, x):
    if x is None:
        return False
    if task in ("area2", "pip"):
        if not simple_polygon([tuple(p) for p in x["poly"]]) or len(x["poly"]) > 60:
            return False
        if task == "pip" and pip([tuple(p) for p in x["poly"]], tuple(x["q"])) == "boundary":
            return False
    if task == "segs" and (len(x["S"]) > 60 or any(a == b for a, b in x["S"])):
        return False
    if task in ("hull", "close") and len(x["P"]) > 200:
        return False
    return True


def breaks(task, code, x):
    _, stdin, _ = render(task, x)
    r = run_python(code, stdin, timeout=10)
    out = (r.stdout.strip().split() or [None])[-1] if r.status == "ok" else None
    return out is None or out.lower() != answer(task, x)


def degen_candidates(task, rng):
    for k in range(B):
        inst = base_instance(task, SIZES[task], random.Random(rng.random()))
        V = variants(task, inst, random.Random(rng.random()))
        yield V[rng.choice(["degen", "degen", "degen", "big", "rot90", "mirror", "scale"])]


def rand_candidates(task, rng):
    for k in range(B):
        yield base_instance(task, SIZES[task], random.Random(rng.random()))


def llm_candidates(task, gen_code):
    if not gen_code:
        return
    for s in range(B):
        g = run_python(f"import random as _r\n_r.seed({s})\n" + gen_code, "", timeout=5)
        yield parse(task, g.stdout) if g.status == "ok" else None


def harvest():
    T = []
    for f in sorted(glob.glob(f"{RES}/geocross_*.jsonl")):
        for r in map(json.loads, open(f)):
            if r["class"] in ("degen_only", "transform_only", "big_only", "degen+big") and r.get("code"):
                T.append({"src": os.path.basename(f)[9:-6], "task": r["task"], "n": r["n"], "inst": r["inst"],
                          "class": r["class"], "code": r["code"]})
    return T


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_tag", required=True)
    ap.add_argument("--strategies", default="rand,rand_degen,llm_blind,llm_code")
    ap.add_argument("--pools", default="", help="comma list of geopool tags; use their SUBTLE programs as targets")
    a = ap.parse_args()
    if a.pools:
        targets = []
        for tag in a.pools.split(","):
            for i, p in enumerate(json.load(open(f"{RES}/geopool_{tag}.json"))):
                if p["rand_fail"] <= 0.05 and p["degen_fail"] > 0:
                    targets.append({"src": tag, "task": p["task"], "n": 0, "inst": i, "class": "subtle", "code": p["code"]})
    else:
        targets = harvest()
    print(len(targets), "target programs", flush=True)

    def run(job):
        t, strat = job
        task, code = t["task"], t["code"]
        rng = random.Random(f"{t['src']}-{t['task']}-{t['n']}-{t['inst']}-{strat}")
        gen_code = None
        if strat.startswith("llm"):
            shown = (f"\n\nHere is a program that is believed to be WRONG on some valid inputs:\n```python\n{code}\n```\n"
                     f"Write the generator so that it is likely to produce inputs on which THIS program fails."
                     if strat == "llm_code" else
                     "\n\nMany programs for this task are wrong on tricky inputs. Write the generator so that it is likely "
                     "to produce inputs that break incorrect programs.")
            o = chat(f"Task: {DESC[task]}. Input format: {FMT[task]}.{shown}\n\nWrite a Python 3 program that prints ONE "
                     f"random VALID input in exactly this format (small sizes are fine). Use the `random` module but do "
                     f"NOT seed it. No input is read. Give it in a single ```python code block.", max_tokens=2048,
                     temperature=0.0)
            gen_code = last_block(o["text"], ("python", "py", "python3"))
        cands = {"rand": lambda: rand_candidates(task, rng), "rand_degen": lambda: degen_candidates(task, rng),
                 "llm_blind": lambda: llm_candidates(task, gen_code), "llm_code": lambda: llm_candidates(task, gen_code)}[strat]()
        n_valid, first = 0, None
        for k, x in enumerate(cands):
            if not valid(task, x):
                continue
            n_valid += 1
            if breaks(task, code, x):
                first = k + 1
                break
        return {**{k: t[k] for k in ("src", "task", "n", "inst", "class")}, "strategy": strat,
                "broken": first is not None, "first_hit": first, "n_valid": n_valid}
    jobs = [(t, s) for t in targets for s in a.strategies.split(",")]
    with ThreadPoolExecutor(32) as ex, open(f"{RES}/geohack_{a.model_tag}.jsonl", "w") as f:
        for r in ex.map(run, jobs):
            f.write(json.dumps(r) + "\n"); f.flush()
    import numpy as np
    rows = [json.loads(l) for l in open(f"{RES}/geohack_{a.model_tag}.jsonl")]
    for s in a.strategies.split(","):
        rs = [r for r in rows if r["strategy"] == s]
        print(f"{s:11s} broken {np.mean([r['broken'] for r in rs]):.2f}  (n={len(rs)})  median first hit "
              f"{np.median([r['first_hit'] for r in rs if r['broken']]) if any(r['broken'] for r in rs) else float('nan')}"
              f"  valid inputs/50 {np.mean([r['n_valid'] for r in rs]):.1f}")


if __name__ == "__main__":
    main()
