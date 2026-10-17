"""PoC #6 — LLM-written special checkers for multi-answer problems, and how much exact-match grading distorts scores.

Problems whose statement admits several correct outputs ("print any of them") need a special checker.
Ground truth comes from CodeContests labels: `solutions` are accepted (a checker must accept their outputs on every
test), `incorrect_solutions` are rejected by the real Codeforces checker (a checker should reject them on >=1 test).

Stages
  1. run up to N_COR correct / N_INC incorrect Python-3 solutions on up to N_TESTS tests, cache outputs
  2. exact-match baseline: false-reject rate (FRR) on correct solutions  -> grading distortion, no LLM needed
  3. LLM writes `check(inp, ref_out, out) -> bool` (K samples); measure FRR on correct, recall on incorrect
  4. re-grade the solver's own PoC-#1 solutions: exact match vs LLM checker
"""
import argparse
import glob
import json
import os
import random
import re
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from llm import chat_many, last_block  # noqa: E402
from run_perturb import MULTI_RE  # noqa: E402
from sandbox import run_many, run_python, same_output  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root (was hard-coded)
RES = f"{ROOT}/results"
N_COR, N_INC, N_TESTS = 5, 10, 40
CACHE = f"{RES}/checker_outputs.json"

PROMPT = """Below is a competitive-programming problem whose answer is NOT unique (several different outputs can be correct).
Write a Python 3 *checker* for it: a function

    def check(inp: str, ref_out: str, out: str) -> bool

that returns True iff `out` (a contestant's output) is a correct answer for the test input `inp`.
`inp` is the ENTIRE input file exactly as described in the Input section — if the format starts with a number of test
cases t, `inp` contains all t test cases and `out`/`ref_out` contain the answers to all of them, in order; you must
check every test case. `ref_out` is the jury's output for the same file; it is ONE correct answer, and a correct
`out` may differ from it.
Requirements:
- Parse `inp` according to the Input section, and `out` robustly (whitespace-insensitive; YES/NO may be any case).
- Verify `out` fully against the statement: format, every constraint on the constructed answer, and — if the problem
  asks for an optimum or a count — that its value equals the value implied by `ref_out`. If the answer can be
  "impossible" (e.g. -1 / NO), accept it only when `ref_out` says so too.
- Malformed output must return False, never raise.
- No input()/print()/sys.stdin and no code that runs at import time; define only the function (helpers allowed).
  Standard library only.
Give the code in a single final ```python block.

## Problem
{desc}"""

# the checker source is embedded as a string literal and exec'd with stdin emptied, so a checker that reads stdin
# or runs code at import time cannot swallow the harness's JSON payload (v1 harness bug)
WRAP_TMPL = """
import json as _j, sys as _s, io as _io
_payload = _j.loads(_s.stdin.read())
_s.stdin = _io.StringIO("")
_g = {{"__name__": "checker"}}
try:
    exec(compile({src!r}, "checker.py", "exec"), _g)
    _chk = _g["check"]
except BaseException:
    _chk = None
_res = []
for _a, _b, _c in _payload:
    try:
        _res.append(bool(_chk(_a, _b, _c)) if _chk else None)
    except BaseException:
        _res.append(None)
_s.stdout = _s.__stdout__
print(_j.dumps(_res))
"""


def wrapped(src):
    return WRAP_TMPL.format(src=src)


def load_items(max_items):
    df = pd.concat([pd.read_parquet(glob.glob(f"{ROOT}/data/code_contests/data/{s}-*.parquet")[0])
                    for s in ("test", "valid")])
    df = df[df.description.str.contains(MULTI_RE, case=False, regex=True)]
    items = []
    for _, r in df.iterrows():
        cor = [c for c, l in zip(r.solutions["solution"], r.solutions["language"]) if l == 3]
        inc = [c for c, l in zip(r.incorrect_solutions["solution"], r.incorrect_solutions["language"]) if l == 3]
        if len(cor) < 2 or len(inc) < 2:
            continue
        ts = [(i, o) for k in ("public_tests", "private_tests") for i, o in zip(r[k]["input"], r[k]["output"])]
        ts += list(zip(r.generated_tests["input"], r.generated_tests["output"]))
        ts = [t for t in ts if len(t[0]) < 100_000][:N_TESTS]
        rng = random.Random(r["name"])
        rng.shuffle(cor); rng.shuffle(inc)
        tl = min(6.0, max(2.0, 3 * (r.time_limit["seconds"] + r.time_limit["nanos"] / 1e9)))
        items.append(dict(name=r["name"], rating=int(r.cf_rating), desc=r.description, tests=ts, tl=tl,
                          cor=cor[:N_COR], inc=inc[:N_INC]))
    return items[:max_items]


def collect_outputs(items):
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    for it in items:
        if it["name"] in cache:
            continue
        t0 = time.time()
        jobs, keys = [], []
        for kind in ("cor", "inc"):
            for si, code in enumerate(it[kind]):
                for ti, (inp, _) in enumerate(it["tests"]):
                    jobs.append((code, inp, it["tl"])); keys.append((kind, si, ti))
        res = run_many(jobs, workers=24)
        out = {"cor": [[None] * len(it["tests"]) for _ in it["cor"]], "inc": [[None] * len(it["tests"]) for _ in it["inc"]]}
        for (kind, si, ti), r in zip(keys, res):
            out[kind][si][ti] = r.stdout if r.status == "ok" else f"__{r.status}__"
        cache[it["name"]] = out
        json.dump(cache, open(CACHE, "w"))
        print(f"outputs {it['name']}: {len(jobs)} runs {time.time() - t0:.0f}s", flush=True)
    return cache


def run_checker(code, it, outs):
    """-> dict kind -> per-solution list of per-test verdicts (True/False/None=checker error, 'x'=solution crashed)."""
    triples, keys = [], []
    for kind in ("cor", "inc"):
        for si, row in enumerate(outs[kind]):
            for ti, o in enumerate(row):
                if o is not None and not o.startswith("__"):
                    triples.append([it["tests"][ti][0], it["tests"][ti][1], o]); keys.append((kind, si, ti))
    verdict = {k: [["x"] * len(it["tests"]) for _ in outs[k]] for k in ("cor", "inc")}
    # small batches: a slow checker then times out (verdict None) on 20 cases, not on the whole problem (v2 bug)
    B = 20
    for s in range(0, len(triples), B):
        r = run_python(wrapped(code), json.dumps(triples[s:s + B]), timeout=40, mem_bytes=2 << 30)
        try:
            vs = json.loads(r.stdout.strip().splitlines()[-1]) if r.status == "ok" else [None] * len(triples[s:s + B])
        except Exception:
            vs = [None] * len(triples[s:s + B])
        for (kind, si, ti), v in zip(keys[s:s + B], vs):
            verdict[kind][si][ti] = v
    return verdict


def summarize(verdict_fn, items, outs_all):
    """Solution-level: correct solution falsely rejected if any test rejects; incorrect caught if any test rejects.
    Incorrect solutions that crash/TLE on some test are 'caught' by the judge anyway -> excluded from recall."""
    fr, n_c, caught, n_i = 0, 0, 0, 0
    global LAST_ERR
    LAST_ERR = [0, 0]  # [correct solutions rejected only through errors/timeouts, correct solutions rejected by a False]
    for it in items:
        outs = outs_all[it["name"]]
        v = verdict_fn(it, outs)
        if v is None:
            continue
        for si, row in enumerate(v["cor"]):
            if any(x == "x" for x in row):
                continue  # correct solution crashed/TLE under our limits -> unusable
            n_c += 1; fr += any(x is not True for x in row)
            if any(x is False for x in row):
                LAST_ERR[1] += 1
            elif any(x is None for x in row):
                LAST_ERR[0] += 1
        for si, row in enumerate(v["inc"]):
            if any(x == "x" for x in row):
                continue
            n_i += 1; caught += any(x is not True for x in row)
    return fr, n_c, caught, n_i


def exact_verdicts(it, outs):
    return {k: [[("x" if (o is None or o.startswith("__")) else same_output(o, it["tests"][ti][1]))
                 for ti, o in enumerate(row)] for row in outs[k]] for k in ("cor", "inc")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_tag", required=True)
    ap.add_argument("--n_items", type=int, default=60)
    ap.add_argument("--k", type=int, default=2)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--skip_llm", action="store_true")
    ap.add_argument("--skip_regrade", action="store_true")
    a = ap.parse_args()
    items = load_items(a.n_items)
    print(len(items), "multi-answer problems", flush=True)
    outs_all = collect_outputs(items)

    fr, n_c, caught, n_i = summarize(exact_verdicts, items, outs_all)
    print(f"EXACT MATCH: false-reject {fr}/{n_c} correct solutions ({fr / max(1, n_c):.3f}); "
          f"catches {caught}/{n_i} incorrect ({caught / max(1, n_i):.3f})", flush=True)
    if a.skip_llm:
        return

    gen_path = f"{RES}/checker_gen_{a.model_tag}.jsonl"
    done = {(d["name"], d["sample"]) for d in map(json.loads, open(gen_path))} if os.path.exists(gen_path) else set()
    jobs = [(it, j) for it in items for j in range(a.k) if (it["name"], j) not in done]
    for s in range(0, len(jobs), a.workers * 2):
        chunk = jobs[s:s + a.workers * 2]
        outs = chat_many([(PROMPT.format(desc=it["desc"]), {"seed": 31 * j + 5}) for it, j in chunk],
                         workers=a.workers, max_tokens=2048)
        with open(gen_path, "a") as f:
            for (it, j), o in zip(chunk, outs):
                f.write(json.dumps({"name": it["name"], "sample": j, "code": last_block(o["text"], ("python", "py", "python3")),
                                    "finish": o["finish"], "out_tokens": o["out_tokens"]}) + "\n")
        print(f"[checkers {s + len(chunk)}/{len(jobs)}]", flush=True)

    gens = [json.loads(l) for l in open(gen_path)]
    by = {}
    for g in gens:
        by.setdefault(g["sample"], {})[g["name"]] = g["code"]
    per_sample = []
    verd_store = {}
    for j, codes in sorted(by.items()):
        def fn(it, outs, codes=codes, j=j):
            c = codes.get(it["name"])
            if not c:
                return {k: [[False] * len(it["tests"]) for _ in outs[k]] for k in ("cor", "inc")}
            v = run_checker(c, it, outs)
            verd_store[(it["name"], j)] = v
            return v
        fr, n_c, caught, n_i = summarize(fn, items, outs_all)
        per_sample.append((fr / max(1, n_c), caught / max(1, n_i)))
        print(f"LLM CHECKER sample {j}: false-reject {fr}/{n_c} ({fr / max(1, n_c):.3f}) "
              f"[by explicit False {LAST_ERR[1]}, only via error/timeout {LAST_ERR[0]}]; "
              f"catches {caught}/{n_i} incorrect ({caught / max(1, n_i):.3f})", flush=True)
    # per-problem: does a checker exist that is perfect on this problem's labelled solutions?
    perfect = 0
    for it in items:
        ok = False
        for j in by:
            v = verd_store.get((it["name"], j))
            if v is None:
                continue
            cor_ok = all(all(x is True for x in row) for row in v["cor"] if "x" not in row)
            inc_ok = all(any(x is not True for x in row) for row in v["inc"] if "x" not in row)
            ok |= cor_ok and inc_ok
        perfect += ok
    print(f"problems with >=1 checker perfect on all labelled solutions: {perfect}/{len(items)}", flush=True)
    json.dump({f"{n}|{j}": v for (n, j), v in verd_store.items()}, open(f"{RES}/checker_verdicts_{a.model_tag}.json", "w"))

    # 4) re-grade the solver's own PoC-#1 'orig' solutions on multi-answer problems
    pert = f"{RES}/perturb_{a.model_tag}.jsonl"
    if os.path.exists(pert) and not a.skip_regrade:
        names = {it["name"]: it for it in items}
        rows = [d for d in map(json.loads, open(pert)) if d["version"] == "orig" and d["name"] in names]
        ex, ck, n = 0, 0, 0
        for d in rows:
            it = names[d["name"]]
            code = last_block(d["response"], ("python", "py", "python3"))
            if not code:
                continue
            outs = [run_python(code, i, timeout=it["tl"]) for i, _ in it["tests"]]
            if any(o.status != "ok" for o in outs):
                n += 1; continue
            n += 1
            ex += all(same_output(o.stdout, t[1]) for o, t in zip(outs, it["tests"]))
            c = by.get(0, {}).get(d["name"])
            if c:
                tri = [[t[0], t[1], o.stdout] for o, t in zip(outs, it["tests"])]
                r = run_python(wrapped(c), json.dumps(tri), timeout=120, mem_bytes=2 << 30)
                try:
                    ck += r.status == "ok" and all(v is True for v in json.loads(r.stdout.strip().splitlines()[-1]))
                except Exception:
                    pass
        print(f"RE-GRADE solver solutions (PoC #1 orig, multi-answer, n={n}): exact-match pass {ex}, "
              f"LLM-checker(sample0) pass {ck}", flush=True)


if __name__ == "__main__":
    main()
