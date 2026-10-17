"""B2 (docs/prereg/PREREG_B2.md) training-data builder.
  sdft:    reproduce E4 arm A's 600 teacher examples (same selection as sft_lora.py: hull excluded, Random(0), 200 per K), let the base
           student (no thinking) rewrite each teacher program in its own style (SDFT, Yang et al. 2024), verify each rewrite on all 8
           variants of its training instance, keep verified rewrites, otherwise the teacher program -> results/b2_data_sdft.jsonl
  selfsft: the student's own verified no-thinking programs on the same 4 tasks / K0,K4,K8 training prompts, 200 per K, Random(0)
           -> results/b2_data_selfsft.jsonl
usage: POC_BASE_URL=... python b2_data.py sdft|selfsft"""
import json, os, random, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import chat, last_block  # noqa: E402
from run_geo import answer, base_instance, render, variants  # noqa: E402
from sandbox import run_python  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root (was hard-coded)
RES = f"{ROOT}/results"


def teacher_selection():   # identical to sft_lora.py (arm mixed, EXCLUDE=hull, no E5_EXTRA)
    rng = random.Random(0)
    def load(k):
        rows = [json.loads(l) for l in open(f"{RES}/geocross_T_geox8b_train_k{k}_think.jsonl")]
        return [r for r in rows if r["class"] == "correct_all" and r.get("code") and r.get("prompt") and r["task"] != "hull"]
    pools = {k: load(k) for k in (0, 4, 8)}
    return sum((rng.sample(pools[k], min(200, len(pools[k]))) for k in (0, 4, 8)), [])


def verify(task, n, inst, code):
    rng = random.Random(f"train-{task}-{n}-{inst}")
    V = variants(task, base_instance(task, n, rng), rng)
    for x in V.values():
        r = run_python(code, render(task, x)[1], timeout=10)
        out = (r.stdout.strip().split() or [None])[-1] if r.status == "ok" else None
        if out is None or out.lower() != answer(task, x):
            return False
    return True


def sdft():
    data = teacher_selection()
    def one(j):
        r = data[j]
        p = (r["prompt"] + "\n\nA reference solution:\n```python\n" + r["code"].strip() + "\n```\nRewrite this reference solution as your own "
             "program, in your own words and style; keep it correct. Give the complete program in a single ```python code block.")
        o = chat(p, think=False, max_tokens=4096, temperature=0.7, seed=1000 + j)
        code = last_block(o["text"], ("python", "py", "python3"))
        good = bool(code) and verify(r["task"], r["n"], r["inst"], code)
        return {"task": r["task"], "n": r["n"], "inst": r["inst"], "prompt": r["prompt"], "code": code if good else r["code"],
                "rewritten": good, "out_tokens": o["out_tokens"], "teacher_code": r["code"]}
    with ThreadPoolExecutor(64) as ex:
        out = list(ex.map(one, range(len(data))))
    with open(f"{RES}/b2_data_sdft.jsonl", "w") as f:
        for r in out:
            f.write(json.dumps(r) + "\n")
    print("sdft:", len(out), "examples; verified rewrites used:", sum(r["rewritten"] for r in out),
          "; mean rewrite tokens", sum(r["out_tokens"] for r in out) / len(out))


def selfsft():
    rng = random.Random(0); out = []
    for k in (0, 4, 8):
        rows = [json.loads(l) for l in open(f"{RES}/geocross_S2_B2_geox8b_train_k{k}_nothink.jsonl")]
        pool = [r for r in rows if r["class"] == "correct_all" and r.get("code") and r.get("prompt")]
        print(f"K{k}: {len(pool)} verified of {len(rows)}", {t: sum(r['task'] == t for r in pool) for t in ('area2', 'pip', 'segs', 'close')})
        out += rng.sample(pool, min(200, len(pool)))
    with open(f"{RES}/b2_data_selfsft.jsonl", "w") as f:
        for r in out:
            f.write(json.dumps({"task": r["task"], "n": r["n"], "inst": r["inst"], "prompt": r["prompt"], "code": r["code"]}) + "\n")
    print("selfsft:", len(out), "examples")


if __name__ == "__main__":
    {"sdft": sdft, "selfsft": selfsft}[sys.argv[1]]()
