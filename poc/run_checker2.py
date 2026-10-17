"""PoC #6b — can small-model checkers be made better than exact match?  (prompt v2 + selection + repair)

Per multi-answer problem, labelled solutions are split by index: even -> SELECTION set, odd -> TEST set.
  1. generate K checkers with an improved prompt ("validate, don't re-solve"; token-stream parsing)
  2. score each on the selection set (false rejects of accepted + misses of rejected solutions)
  3. pick the best; if it still errs on the selection set, one REPAIR round with a concrete misjudged example
  4. report on the held-out TEST set: exact match vs. average checker vs. selected vs. selected+repaired
"""
import argparse
import json
import os
import random
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from llm import chat_many, last_block  # noqa: E402
from run_checker import collect_outputs, exact_verdicts, load_items, run_checker  # noqa: E402

RES = "/NAS/SJ/POSTECH/nlp/results"

PROMPT_V2 = """Below is a competitive-programming problem whose answer is NOT unique (several different outputs can be correct).
Write a Python 3 *checker*:

    def check(inp: str, ref_out: str, out: str) -> bool

It returns True iff `out` (a contestant's output) is a correct answer for the test input `inp`.
- `inp` is the ENTIRE input file as described in the Input section; if it starts with a number of test cases t, it
  contains all t cases, and `out` / `ref_out` contain all t answers in order. Check every case.
- `ref_out` is the jury's output: ONE correct answer. A correct `out` may differ from it.

How to write a good checker (important):
1. Do NOT re-solve the problem and do NOT compare `out` with `ref_out` literally. Read from `ref_out` only what is
   unique — e.g. the optimal value / minimum number of operations / whether an answer exists ("-1", "NO") — and
   require `out` to match that, then VERIFY `out`'s construction (sequence, permutation, operations, chosen indices…)
   directly against the statement's conditions, e.g. by simulating it.
2. Parse `inp`, `ref_out` and `out` as whitespace-separated TOKEN streams and consume tokens per test case according
   to the format (this handles empty lines, e.g. an answer "0" followed by an empty list). Compare words like YES/NO
   case-insensitively.
3. Any malformed `out` (missing/extra tokens, non-integers, out-of-range values) -> return False. Never raise.
4. Define only the function and helpers; no input()/print()/sys.stdin, no code at import time. Standard library only.
Give the code in a single final ```python block.

## Problem
{desc}"""

REPAIR = """Your checker below misjudged a test.

## Problem
{desc}

## Your checker
```python
{code}
```

## Misjudged case
Input file:
```
{inp}
```
Jury output (one correct answer):
```
{ref}
```
Contestant output:
```
{out}
```
This contestant output is {truth} (it comes from a solution the official judge {verdict}), but your checker returned {got}.
Find the bug in your checker and give the complete corrected `check` function in a single final ```python block.
Remember: do not re-solve the problem; take only the unique quantity from the jury output and verify the contestant's
construction directly; parse token streams; never raise."""


def score(v, cor_idx, inc_idx):
    """errors on a subset: accepted solution rejected on any test, or rejected solution accepted on all tests."""
    fr = sum(any(x is not True for x in v["cor"][i]) for i in cor_idx if "x" not in v["cor"][i])
    miss = sum(all(x is True for x in v["inc"][i]) for i in inc_idx if "x" not in v["inc"][i])
    n = sum("x" not in v["cor"][i] for i in cor_idx) + sum("x" not in v["inc"][i] for i in inc_idx)
    return fr, miss, n


def first_misjudged(v, it, outs, cor_idx, inc_idx):
    for i in cor_idx:
        row = v["cor"][i]
        if "x" in row:
            continue
        for ti, x in enumerate(row):
            if x is not True:
                return ti, outs["cor"][i][ti], "CORRECT", "accepted", "False" if x is False else "an error/exception"
    for i in inc_idx:
        row = v["inc"][i]
        if "x" in row or not all(x is True for x in row):
            continue
        # accepted on every test we have, but officially wrong: show the test where it differs from the jury most visibly
        ti = next((t for t, o in enumerate(outs["inc"][i]) if o.split() != it["tests"][t][1].split()), 0)
        return ti, outs["inc"][i][ti], "WRONG", "rejected", "True"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_tag", required=True)
    ap.add_argument("--k", type=int, default=4)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--think", action="store_true")
    ap.add_argument("--max_tokens", type=int, default=3072)
    a = ap.parse_args()
    items = load_items(60)
    outs_all = collect_outputs(items)
    gen_path = f"{RES}/checker2_gen_{a.model_tag}.jsonl"
    gens = [json.loads(l) for l in open(gen_path)] if os.path.exists(gen_path) else []
    have = {(g["name"], g["kind"], g["j"]) for g in gens}
    jobs = [(it, j) for it in items for j in range(a.k) if (it["name"], "gen", j) not in have]
    # generate in chunks and append after each, so a server restart loses at most one chunk
    for s0 in range(0, len(jobs), a.workers):
        chunk = jobs[s0:s0 + a.workers]
        outs = chat_many([(PROMPT_V2.format(desc=it["desc"]), {"seed": 97 * j + 3}) for it, j in chunk],
                         workers=a.workers, max_tokens=a.max_tokens, think=a.think)
        with open(gen_path, "a") as f:
            for (it, j), o in zip(chunk, outs):
                f.write(json.dumps({"name": it["name"], "kind": "gen", "j": j,
                                    "code": last_block(o["text"], ("python", "py", "python3"))}) + "\n")
        print(f"[checkers {s0 + len(chunk)}/{len(jobs)}]", flush=True)
    if jobs:
        gens = [json.loads(l) for l in open(gen_path)]
    codes = {(g["name"], g["kind"], g["j"]): g["code"] for g in gens}

    rows, repair_jobs = [], []
    for it in items:
        outs = outs_all[it["name"]]
        cs, ins = range(0, len(it["cor"]), 2), range(0, len(it["inc"]), 2)
        ct, itest = range(1, len(it["cor"]), 2), range(1, len(it["inc"]), 2)
        ex = exact_verdicts(it, outs)
        cand = []
        for j in range(a.k):
            c = codes.get((it["name"], "gen", j))
            v = run_checker(c, it, outs) if c else None
            if v is None:
                continue
            fr, miss, n = score(v, cs, ins)
            cand.append((fr + miss, j, v))
        if not cand:
            continue
        cand.sort(key=lambda t: (t[0], t[1]))
        best_err, best_j, best_v = cand[0]
        row = {"name": it["name"], "exact": score(ex, ct, itest),
               "avg": [score(v, ct, itest) for _, _, v in cand], "sel": score(best_v, ct, itest),
               "sel_sel_err": best_err, "best_j": best_j}
        rows.append(row)
        if best_err > 0:
            m = first_misjudged(best_v, it, outs, cs, ins)
            if m:
                ti, o, truth, verdict, got = m
                repair_jobs.append((it, row, REPAIR.format(desc=it["desc"], code=codes[(it["name"], "gen", best_j)],
                                                          inp=it["tests"][ti][0][:3000], ref=it["tests"][ti][1][:2000],
                                                          out=o[:2000], truth=truth, verdict=verdict, got=got)))
    # repair round (cached)
    todo = [(it, row, p) for it, row, p in repair_jobs if (it["name"], "repair", 0) not in codes]
    if todo:
        outs = chat_many([(p, {"seed": 11}) for _, _, p in todo], workers=a.workers, max_tokens=a.max_tokens, think=a.think)
        with open(gen_path, "a") as f:
            for (it, _, _), o in zip(todo, outs):
                c = last_block(o["text"], ("python", "py", "python3"))
                codes[(it["name"], "repair", 0)] = c
                f.write(json.dumps({"name": it["name"], "kind": "repair", "j": 0, "code": c}) + "\n")
    for it, row, _ in repair_jobs:
        c = codes.get((it["name"], "repair", 0))
        if not c:
            continue
        outs = outs_all[it["name"]]
        cs, ins = range(0, len(it["cor"]), 2), range(0, len(it["inc"]), 2)
        v = run_checker(c, it, outs)
        fr, miss, _ = score(v, cs, ins)
        if fr + miss < row["sel_sel_err"]:  # keep the repair only if it helps on the SELECTION set
            row["rep"] = score(v, range(1, len(it["cor"]), 2), range(1, len(it["inc"]), 2))
    json.dump(rows, open(f"{RES}/checker2_rows_{a.model_tag}.json", "w"))

    def agg(key):
        fr = miss = n = 0
        for r in rows:
            s = r.get(key) or r["sel"] if key == "rep" else r[key]
            if key == "avg":
                s = tuple(np.mean([x[i] for x in r["avg"]]) for i in range(3))
            fr += s[0]; miss += s[1]; n += s[2]
        return fr, miss, n
    print(f"{len(rows)} problems; held-out TEST set (odd-indexed labelled solutions)")
    for key, lab in [("exact", "exact match"), ("avg", f"avg of {a.k} v2 checkers"), ("sel", "selected on selection set"),
                     ("rep", "selected + 1 repair round")]:
        fr, miss, n = agg(key)
        print(f"  {lab:28s} errors {fr + miss:6.1f} / {n:5.1f} solutions  (false rejects {fr:.1f}, misses {miss:.1f})")
    nrep = sum("rep" in r for r in rows)
    print(f"  repairs attempted {len(repair_jobs)}, kept (improved selection error) {nrep}")
    perfect = sum(((r.get("rep") or r["sel"])[0] + (r.get("rep") or r["sel"])[1]) == 0 for r in rows)
    print(f"  problems where the final checker makes 0 test-set errors: {perfect}/{len(rows)}")


if __name__ == "__main__":
    main()
