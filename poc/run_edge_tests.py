"""HO-G-E (docs/prereg/PREREG_HOGC.md, addendum): edge-case tests written by the model ONCE PER TASK from the problem statement (no answers).
For each held-out geometry task the model sees the statement of one instance and writes 3-6 small test cases (stdin + expected output) for
the special cases the statement names or implies; poc/analyze_hogc.py --edge then accepts a fact program only if it passes MR and these tests.
usage: POC_BASE_URL=... python run_edge_tests.py --model_tag SL_HOGCE_<m>_s<seed> --seed <seed> [--max_tokens N]
       -> results/edgetests_<tag>.jsonl (one row per task; rerun skips finished tasks)"""
import argparse, json, os, random, re, sys, zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import chat  # noqa: E402
from run_geo import base_instance, render, variants  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = f"{ROOT}/results"
TASKS = {"overlap": 8, "convex": 8, "tri": 10, "clip": 6}   # the smaller HO-G size of each task

ASK = """{q}

Do not solve this instance. Instead, write test cases for a program that must solve this problem for ANY input in this stdin format: {fmt}.
Write 3 to 6 SMALL test cases (at most 6 points or vertices each, small integer coordinates) that check the special cases this problem
statement names or implies (for example collinear points, points exactly on an edge or at a vertex, duplicate points, shapes that only
touch), plus one ordinary case. Work out each expected output carefully by hand, following the rules in the statement exactly.
Reply with only a JSON list in a ```json code block: [{{"stdin": "<the exact stdin text>", "expected": "<the exact expected output>"}}, ...]"""


def parse(text):
    blocks = re.findall(r"```(?:json)?[ \t]*\n(.*?)```", text or "", flags=re.S)
    for b in reversed(blocks or [text or ""]):
        try:
            L = json.loads(b)
        except ValueError:
            continue
        if isinstance(L, list):
            return [{"stdin": t["stdin"], "expected": str(t["expected"]).strip()} for t in L
                    if isinstance(t, dict) and isinstance(t.get("stdin"), str) and str(t.get("expected", "")).strip()]
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_tag", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--max_tokens", type=int, default=4096)
    a = ap.parse_args()
    path = f"{RES}/edgetests_{a.model_tag}.jsonl"
    done = {json.loads(l)["task"] for l in open(path)} if os.path.exists(path) else set()
    with open(path, "a") as f:
        for task, n in TASKS.items():
            if task in done:
                continue
            rng = random.Random(f"{task}-{n}-0")
            q, _, fmt = render(task, variants(task, base_instance(task, n, rng), rng)["identity"])
            o = chat(ASK.format(q=q, fmt=fmt), think=False, max_tokens=a.max_tokens, temperature=0.7,
                     seed=a.seed * 1000 + zlib.crc32(task.encode()) % 997)
            tests = parse(o["text"])
            f.write(json.dumps({"task": task, "seed": a.seed, "n": n, "inst": 0, "tests": tests, "n_tests": len(tests),
                                "raw": (o["text"] or "")[-6000:], "out_tokens": o.get("out_tokens"), "finish": o.get("finish")}) + "\n")
            f.flush()
            print(a.model_tag, task, len(tests), "tests", o.get("out_tokens"), "tokens", o.get("finish"), flush=True)


if __name__ == "__main__":
    main()
