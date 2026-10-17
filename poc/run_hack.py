"""PoC #2 — can an LLM find an input that breaks a subtly-wrong solution?

Strategies (each sampled K times per item):
  blind   : problem only (no buggy code) -> "write a tricky edge-case input"   [does seeing the code matter?]
  direct  : problem + buggy code -> one breaking input
  bugfirst: problem + buggy code -> explain the bug first, then one breaking input
  stress  : problem + buggy code -> random small-input generator; we run it G times and compare
            buggy vs reference outputs (reference = oracle; upper bound for a generator strategy)

An input counts as a HACK iff all 3 reference solutions run cleanly and agree on it (validity proxy)
AND the buggy solution's output differs (strict WA). Crashes/TLE of the buggy code are logged separately.
"""
import argparse
import json
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from llm import chat_many, last_block  # noqa: E402
from sandbox import run_python, same_output  # noqa: E402

PROBLEM = "## Problem\n{desc}\n"
CODE = "## Submitted solution (Python 3)\nThis solution passes the sample tests but is WRONG on some input.\n```python\n{code}\n```\n"
FMT_INPUT = ("Output exactly one COMPLETE test input that satisfies all constraints and the exact format of the Input "
             "section (including the first line with the number of test cases, if the format has one). Keep it small "
             "(a human should be able to verify it by hand). Put the raw input, exactly as it would be fed to stdin, "
             "in a single final code block:\n```input\n...\n```")
PROMPTS = {
    "blind": PROBLEM + "\nMany submissions to this problem are wrong. Write a tricky test input that is likely to "
             "break incorrect solutions (edge cases, boundary values, special structures). Think briefly first. " + FMT_INPUT,
    "direct": PROBLEM + "\n" + CODE + "\nFind a test input on which this solution prints a wrong answer. " + FMT_INPUT,
    "bugfirst": PROBLEM + "\n" + CODE + "\nFirst, compare the solution against the problem statement and explain "
                "precisely what the bug is (a few sentences). Then construct the smallest input that triggers it and "
                "say what the correct answer and the buggy output would be. " + FMT_INPUT,
    "stress": PROBLEM + "\n" + CODE + "\nWe will stress-test this solution against a correct one. Write a Python 3 "
              "program that prints ONE random, valid, SMALL, COMPLETE test input to stdout, exactly in the format of the "
              "Input section (including the first line with the number of test cases t, if the format has one — use a "
              "small t) and respecting every constraint (e.g. a tree must really be a tree); prefer tiny sizes so many cases can be tried, but bias the randomness toward "
              "the situations where you suspect this solution is wrong). Use the `random` module but do NOT seed it "
              "(we seed it). No input is read. Put the program in a single final ```python code block.",
    # control: same generator task but WITHOUT the buggy code -> isolates the value of reading the code
    "stress_blind": PROBLEM + "\nMany submissions to this problem are wrong. We will stress-test submissions against a "
                    "correct solution. Write a Python 3 program that prints ONE random, valid, SMALL, COMPLETE test input "
                    "to stdout, exactly in the format of the Input section (including the first line with the number of "
                    "test cases t, if the format has one — use a small t) and respecting every constraint (e.g. a tree "
                    "must really be a tree); prefer tiny sizes so many cases can be tried, but bias the randomness toward "
                    "tricky situations (edge cases, boundary values, special structures). Use the `random` module but do "
                    "NOT seed it (we seed it). No input is read. Put the program in a single final ```python code block.",
}


def extract_input(text):
    """Prefer an explicitly labelled ```input block (models often append an ``` expected-output block after it)."""
    return last_block(text, ("input",)) or last_block(text)


def check_input(item, inp, cache):
    """-> 'hack' | 'buggy_crash' | 'invalid' | 'same'"""
    if inp is None or not inp.strip():
        return "invalid"
    if not inp.endswith("\n"):
        inp += "\n"
    if inp in cache:
        return cache[inp]
    tl = item["time_limit"]
    b = run_python(item["wrong"]["code"], inp, timeout=tl)
    r0 = run_python(item["refs"][0], inp, timeout=tl)
    if r0.status != "ok":
        v = "invalid"
    elif b.status == "ok" and same_output(b.stdout, r0.stdout):
        v = "same"  # cheap path: skip remaining refs
    else:
        rs = [run_python(c, inp, timeout=tl) for c in item["refs"][1:]]
        if any(r.status != "ok" or not same_output(r.stdout, r0.stdout) for r in rs):
            v = "invalid"
        else:
            v = "hack" if b.status == "ok" else "buggy_crash"
    cache[inp] = v
    return v


def run_stress(item, gen_code, n_gen, cache):
    if not gen_code:
        return {"verdict": "invalid", "n_valid": 0, "first_hit": None}
    n_valid, verdict, first = 0, "same", None
    for s in range(n_gen):
        g = run_python(f"import random as _r\n_r.seed({s})\n" + gen_code, "", timeout=5)
        if g.status != "ok":
            continue
        v = check_input(item, g.stdout, cache)
        if v in ("same", "hack", "buggy_crash"):
            n_valid += 1
        if v == "hack":
            verdict, first = "hack", s + 1
            break
        if v == "buggy_crash" and verdict == "same":
            verdict = "buggy_crash"
    if n_valid == 0:
        verdict = "invalid"
    return {"verdict": verdict, "n_valid": n_valid, "first_hit": first}


def placebo_codes(items):
    """A DIFFERENT wrong Python-3 solution of the same problem, shown instead of the target (placebo control):
    if the model really uses the code, showing unrelated buggy code should not help as much as the target's."""
    import glob
    import pandas as pd
    want = {it["name"]: it["wrong"]["code"] for it in items}
    out = {}
    for f in glob.glob("/NAS/SJ/POSTECH/nlp/data/code_contests/data/[tv][ea]*-*.parquet"):
        df = pd.read_parquet(f, columns=["name", "incorrect_solutions"])
        for _, r in df[df.name.isin(want)].iterrows():
            cands = sorted({c for c, l in zip(r.incorrect_solutions["solution"], r.incorrect_solutions["language"])
                            if l == 3 and c.strip() != want[r["name"]].strip()})
            if cands:
                out[r["name"]] = random.Random(r["name"]).choice(cands)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", default="/NAS/SJ/POSTECH/nlp/data/hack_bench.jsonl")
    ap.add_argument("--model_tag", required=True)
    ap.add_argument("--n_items", type=int, default=40)
    ap.add_argument("--k", type=int, default=2)
    ap.add_argument("--strategies", default="blind,direct,bugfirst,stress")
    ap.add_argument("--n_gen", type=int, default=100)
    ap.add_argument("--max_tokens", type=int, default=1536)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--think", action="store_true")
    a = ap.parse_args()

    items = [json.loads(l) for l in open(a.bench)]
    random.Random(0).shuffle(items)
    items = items[: a.n_items]
    placebo = placebo_codes(items) if "placebo" in a.strategies else {}
    out_path = f"/NAS/SJ/POSTECH/nlp/results/hack_{a.model_tag}.jsonl"
    done = set()
    if os.path.exists(out_path):
        done = {(d["name"], d["strategy"], d["sample"]) for d in map(json.loads, open(out_path))}
    jobs = [(it, s, j) for it in items for s in a.strategies.split(",") for j in range(a.k)
            if (it["name"], s, j) not in done and not (s.endswith("_placebo") and it["name"] not in placebo)]
    print(f"{len(items)} items, {len(jobs)} generations to run", flush=True)
    caches = {it["name"]: {} for it in items}
    B = a.workers * 2
    for i in range(0, len(jobs), B):
        chunk = jobs[i:i + B]
        t0 = time.time()
        prompts = [(PROMPTS[s.removesuffix("_placebo")].format(
                        desc=it["description"],
                        code=placebo.get(it["name"], it["wrong"]["code"]) if s.endswith("_placebo") else it["wrong"]["code"]),
                    {"seed": 1000 * j + 7}) for it, s, j in chunk]
        outs = chat_many(prompts, workers=a.workers, max_tokens=a.max_tokens, think=a.think)
        def judge(job_out):
            (it, s, j), o = job_out
            if s.startswith("stress"):
                return run_stress(it, last_block(o["text"], ("python", "py", "python3")), a.n_gen, caches[it["name"]])
            return {"verdict": check_input(it, extract_input(o["text"]), caches[it["name"]])}

        # verification runs many sandboxed programs per job; do jobs in parallel (was serial -> LLM idle ~70% of a chunk)
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(int(os.environ.get("POC_VERIFY_THREADS", "16"))) as ex:
            results = list(ex.map(judge, zip(chunk, outs)))
        with open(out_path, "a") as f:
            for ((it, s, j), o), res in zip(zip(chunk, outs), results):
                f.write(json.dumps({"name": it["name"], "rating": it["cf_rating"], "strategy": s, "sample": j,
                                    **res, "finish": o["finish"], "out_tokens": o["out_tokens"],
                                    "in_tokens": o["in_tokens"], "response": o["text"]}) + "\n")
        print(f"[{i + len(chunk)}/{len(jobs)}] {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
