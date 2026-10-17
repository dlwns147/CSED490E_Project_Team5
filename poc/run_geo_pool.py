"""T2 target pool: sample many LLM-written programs per geometry task, keep the SUBTLY wrong ones
(fail <=5% of random instances, but >0 of degeneracy-biased instances). Output: results/geopool_<tag>.json"""
import argparse
import json
import os
import random
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
from llm import chat, last_block  # noqa: E402
from run_geo import base_instance, render, variants  # noqa: E402
from run_geo_hack import breaks, degen_candidates, rand_candidates, valid  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root (was hard-coded)
RES = f"{ROOT}/results"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_tag", required=True)
    ap.add_argument("--k", type=int, default=24)
    a = ap.parse_args()
    tasks = {"pip": 8, "segs": 6, "hull": 10, "area2": 8, "close": 10}
    jobs = [(t, n, s) for t, n in tasks.items() for s in range(a.k)]

    def gen(job):
        task, n, s = job
        inst = base_instance(task, n, random.Random(f"pool-{task}-{s}"))
        q, _, fmt = render(task, variants(task, inst, random.Random(s))["identity"])
        o = chat(f"{q}\n\nDo not compute the answer by hand. Write a Python 3 program that solves this problem for any "
                 f"input in the following stdin format: {fmt}. Print only the answer. Give the program in a single "
                 f"```python code block.", max_tokens=2048, temperature=0.8, seed=1000 + s)
        code = last_block(o["text"], ("python", "py", "python3"))
        if not code:
            return None
        rf = [breaks(task, code, x) for x in rand_candidates(task, random.Random(7)) if valid(task, x)]
        df = [breaks(task, code, x) for x in degen_candidates(task, random.Random(8)) if valid(task, x)]
        return {"task": task, "seed": s, "code": code, "rand_fail": sum(rf) / max(1, len(rf)),
                "degen_fail": sum(df) / max(1, len(df))}
    with ThreadPoolExecutor(48) as ex:
        progs = [p for p in ex.map(gen, jobs) if p]
    json.dump(progs, open(f"{RES}/geopool_{a.model_tag}.json", "w"))
    from collections import Counter
    sub = [p for p in progs if p["rand_fail"] <= 0.05 and p["degen_fail"] > 0]
    print(a.model_tag, "programs", len(progs), "| correct-looking (rand_fail==0 & degen_fail==0)",
          sum(p["rand_fail"] == 0 and p["degen_fail"] == 0 for p in progs), "| SUBTLE", len(sub), Counter(p["task"] for p in sub))


if __name__ == "__main__":
    main()
