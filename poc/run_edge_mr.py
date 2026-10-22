"""HO-G-M (docs/prereg/PREREG_HOGC.md, addendum): metamorphic relations written by the model ONCE PER TASK from the problem statement.
Unlike HO-G-E's edge-case tests, a relation needs no hand-computed answer: `transform(stdin) -> stdin` applies a change whose effect the
statement fixes, `expect(old_answer) -> new_answer` states that effect from the old answer alone. poc/analyze_hogc.py --mr runs them.
usage: POC_BASE_URL=... python run_edge_mr.py --model_tag SL_HOGCM_<m>_s<seed> --seed <seed> [--max_tokens N]
       -> results/edgemr_<tag>.jsonl (one row per task; rerun skips finished tasks)"""
import argparse, json, os, random, sys, zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import chat, last_block  # noqa: E402
from run_geo import base_instance, render, variants  # noqa: E402
from sandbox import run_python  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = f"{ROOT}/results"
TASKS = {"overlap": 8, "convex": 8, "tri": 10, "clip": 6}   # the smaller HO-G size of each task

ASK = """{q}

Do not solve this instance. We will test a program that must solve this problem for ANY input in this stdin format: {fmt}.
Write Python code that defines a list RELATIONS of 2 to 4 pairs (transform, expect):
- transform(stdin_text) -> str returns a new valid input in the same format, obtained by a change whose effect on the answer is fixed by
  the rules of this statement. Prefer changes that exercise the special cases the statement names or implies (for example collinear
  points, a point exactly on an edge or at a vertex, a duplicate point, shapes that only touch).
- expect(old_answer) -> str returns the answer for the new input computed ONLY from the old answer string (for example `lambda a: a` when
  the change must not alter the answer).
Do not compute the answer of any input yourself. Use only the Python standard library. Reply with only the code in a ```python block."""

DRIVER = "\n\nimport sys as _s, json as _j\n_x = _s.stdin.read()\n_o = []\nfor _t, _e in RELATIONS:\n    try:\n        _o.append(_t(_x))\n    except Exception:\n        _o.append(None)\nprint(_j.dumps(_o))\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_tag", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--max_tokens", type=int, default=4096)
    a = ap.parse_args()
    path = f"{RES}/edgemr_{a.model_tag}.jsonl"
    done = {json.loads(l)["task"] for l in open(path)} if os.path.exists(path) else set()
    with open(path, "a") as f:
        for task, n in TASKS.items():
            if task in done:
                continue
            rng = random.Random(f"{task}-{n}-0")
            q, stdin, fmt = render(task, variants(task, base_instance(task, n, rng), rng)["identity"])
            o = chat(ASK.format(q=q, fmt=fmt), think=False, max_tokens=a.max_tokens, temperature=0.7,
                     seed=a.seed * 1000 + zlib.crc32(task.encode()) % 997)
            code = last_block(o["text"] or "", ("python", "py", "python3"))
            n_rel, ok = 0, False
            if code:   # does it define RELATIONS that transform a real input of this task? (sandboxed; no answers involved)
                x = run_python(code + DRIVER, stdin, timeout=10)
                try:
                    outs = json.loads(x.stdout.strip().splitlines()[-1]) if x.status == "ok" and x.stdout.strip() else []
                except ValueError:
                    outs = []
                n_rel, ok = len(outs), any(isinstance(y, str) and y.strip() for y in outs)
            f.write(json.dumps({"task": task, "seed": a.seed, "code": code, "n_relations": n_rel, "runs": ok, "raw": (o["text"] or "")[-6000:],
                                "out_tokens": o.get("out_tokens"), "finish": o.get("finish")}) + "\n")
            f.flush()
            print(a.model_tag, task, n_rel, "relations", "runs" if ok else "BROKEN", o.get("out_tokens"), "tokens", flush=True)


if __name__ == "__main__":
    main()
