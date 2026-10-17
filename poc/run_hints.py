"""PoC F — progressive hints: can a tutor LLM help a weaker student solve algorithmic problems without giving the answer away?

tutor  (Qwen3-8B, :8000) sees problem + a reference solution and writes 3 hint levels (no code):
       L1 = key observation, L2 = approach/algorithm, L3 = detailed plan.
student (Qwen3-1.7B, :8001) solves the problem with hints up to level L (L = 0..3), K samples each.
controls: PLACEBO = the 3 hints written for a DIFFERENT problem; FULL = the reference solution itself.
metrics: student pass@1 per condition (graded on the CodeContests tests); leakage = code in hints,
         and similarity of the student's program to the reference solution (difflib ratio).
"""
import argparse
import difflib
import glob
import json
import os
import random
import re
import sys
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from openai import OpenAI

sys.path.insert(0, os.path.dirname(__file__))
from llm import chat_msgs, last_block  # noqa: E402
from run_perturb import MULTI_RE, judge  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root (was hard-coded)
RES = f"{ROOT}/results"
TUTOR = OpenAI(base_url=os.environ.get("TUTOR_URL", "http://127.0.0.1:8000/v1"), api_key="none", timeout=3600)
STUDENT = OpenAI(base_url=os.environ.get("STUDENT_URL", "http://127.0.0.1:8001/v1"), api_key="none", timeout=3600)

TUTOR_PROMPT = """You are a tutor for competitive programming. Below is a problem and a correct reference solution.
Write three progressive hints for a student who is stuck. Rules: NO code, NO pseudo-code, do not state the final
formula or the full algorithm in hints 1-2. Hint 1: the key observation. Hint 2: which approach/algorithm to use.
Hint 3: a step-by-step plan in words (still no code). Format exactly:
HINT 1: ...
HINT 2: ...
HINT 3: ...

## Problem
{desc}

## Reference solution (for you only)
```python
{sol}
```"""

SOLVE = ("Solve the following competitive-programming problem in Python 3. Read from standard input and write to "
         "standard output. Give the complete program in a single final ```python code block.\n\n{desc}{extra}")


def load_items(n, max_rating=1300):
    files = sorted(glob.glob(f"{ROOT}/data/code_contests/data/train-*.parquet"))
    df = pd.concat([pd.read_parquet(f) for f in files])
    df = df[(df.source == 2) & (df.cf_rating > 0) & (df.cf_rating <= max_rating)]
    df = df[~df.description.str.contains(MULTI_RE, case=False, regex=True)]
    items = []
    for _, r in df.iterrows():
        sols = [c for c, l in zip(r.solutions["solution"], r.solutions["language"]) if l == 3]
        ts = [(i, o) for k in ("public_tests", "private_tests") for i, o in zip(r[k]["input"], r[k]["output"])]
        ts += list(zip(r.generated_tests["input"], r.generated_tests["output"]))[:30]
        if not sols or len(ts) < 3:
            continue
        sol = min(sols, key=len)  # shortest accepted solution = clearest reference
        tl = min(6.0, max(2.0, 3 * (r.time_limit["seconds"] + r.time_limit["nanos"] / 1e9)))
        items.append(dict(name=r["name"], rating=int(r.cf_rating), desc=r.description, sol=sol, tests=ts, tl=tl))
    random.Random(1).shuffle(items)
    return items[:n]


def ask(client, prompt, think, max_tokens, seed):
    return chat_msgs([{"role": "user", "content": prompt}], think=think, max_tokens=max_tokens, seed=seed, client_=client)


def parse_hints(t):
    hs = {}
    for k in (1, 2, 3):
        m = re.search(rf"HINT {k}\s*[:.]\s*(.*?)(?=HINT {k + 1}\s*[:.]|\Z)", t, flags=re.S)
        hs[k] = m.group(1).strip() if m else ""
    return hs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n_items", type=int, default=80)
    ap.add_argument("--k", type=int, default=4)
    ap.add_argument("--tag", default="t8b_s17b")
    ap.add_argument("--tutor_think", action="store_true")
    ap.add_argument("--hints_from", default=None, help="reuse the hints of another tag (same tutor, different student)")
    a = ap.parse_args()
    items = load_items(a.n_items)
    out = f"{RES}/hints_{a.tag}.json"
    st = json.load(open(out)) if os.path.exists(out) else {"hints": {}, "runs": []}

    # 1) tutor writes hints (or reuse another run's hints so different students see identical hints)
    if a.hints_from and not st["hints"]:
        st["hints"] = json.load(open(f"{RES}/hints_{a.hints_from}.json"))["hints"]
    todo = [it for it in items if it["name"] not in st["hints"]]
    with ThreadPoolExecutor(32) as ex:
        res = list(ex.map(lambda it: ask(TUTOR, TUTOR_PROMPT.format(desc=it["desc"], sol=it["sol"]), a.tutor_think,
                                         6000 if a.tutor_think else 1200, 7), todo))
    for it, o in zip(todo, res):
        st["hints"][it["name"]] = parse_hints(o["text"])
    json.dump(st, open(out, "w"))

    # 2) student solves under each condition
    names = [it["name"] for it in items]
    placebo_of = {n: names[(i + 1) % len(names)] for i, n in enumerate(names)}

    def extra(it, cond):
        if cond == "L0":
            return ""
        if cond == "FULL":
            return f"\n\n## A correct solution you may use\n```python\n{it['sol']}\n```"
        src = st["hints"][placebo_of[it["name"]]] if cond == "PLACEBO" else st["hints"][it["name"]]
        lv = 3 if cond == "PLACEBO" else int(cond[1])
        return "\n\n## Hints\n" + "\n".join(f"Hint {k}: {src[k]}" for k in range(1, lv + 1) if src.get(k))

    conds = ["L0", "L1", "L2", "L3", "PLACEBO", "FULL"]
    done = {(r["name"], r["cond"], r["j"]) for r in st["runs"]}
    jobs = [(it, c, j) for it in items for c in conds for j in range(a.k) if (it["name"], c, j) not in done]

    def run(job):
        it, c, j = job
        o = ask(STUDENT, SOLVE.format(desc=it["desc"], extra=extra(it, c)), False, 2048, 100 * j + 3)
        code = last_block(o["text"], ("python", "py", "python3"))
        sim = difflib.SequenceMatcher(None, code or "", it["sol"]).ratio() if code else 0.0
        return {"name": it["name"], "rating": it["rating"], "cond": c, "j": j, "verdict": judge(code, it), "sim_to_ref": sim}
    with ThreadPoolExecutor(64) as ex:
        for r in ex.map(run, jobs):
            st["runs"].append(r)
    json.dump(st, open(out, "w"))

    # 3) summary
    import numpy as np
    from collections import defaultdict
    by = defaultdict(lambda: defaultdict(list))
    for r in st["runs"]:
        by[r["cond"]][r["name"]].append(r)
    code_in_hints = np.mean([bool(re.search(r"```|def |for \w+ in range|print\(", " ".join(h.values())))
                             for h in st["hints"].values()])
    print(f"{a.tag}: {len(items)} problems, k={a.k}; hints containing code-like text: {code_in_hints:.2f}")
    base = {n: np.mean([x["verdict"] == "ac" for x in v]) for n, v in by["L0"].items()}
    for c in conds:
        per = {n: np.mean([x["verdict"] == "ac" for x in v]) for n, v in by[c].items()}
        sim = np.mean([x["sim_to_ref"] for v in by[c].values() for x in v])
        hard = [n for n in per if base.get(n, 1) < 0.5]
        own = {n: np.mean([x["verdict"] == "ac" and x["sim_to_ref"] < 0.5 for x in v]) for n, v in by[c].items()}
        print(f"  {c:8s} pass@1 {np.mean(list(per.values())):.3f}  on problems the student fails alone (n={len(hard)}): "
              f"{np.mean([per[n] for n in hard]) if hard else float('nan'):.3f}   code-similarity to reference {sim:.2f}"
              f"   leakage-adjusted pass@1 (solve AND sim<0.5) {np.mean(list(own.values())):.3f}")


if __name__ == "__main__":
    main()
