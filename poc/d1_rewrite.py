"""D1b' (results/PREREG_D1.md): base Qwen3-8B (no-think) adds explanatory comments to each teacher program without changing its logic;
the rewrite is kept only if it still passes all of the problem's kept tests. -> results/h2/d1b_E.jsonl
usage: CC_SET=full POC_BASE_URL=... python d1_rewrite.py"""
import json, os, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import chat, last_block  # noqa: E402
from run_cc import PFILE, RES, VFILE, tests_of, tok_eq  # noqa: E402
from sandbox import run_python  # noqa: E402

P = {p["name"]: p for p in json.load(open(PFILE))}; V = json.load(open(VFILE))
TRAIN = json.load(open(f"{RES}/d1_split.json"))["train"]
name_of = {P[n]["description"].strip(): n for n in TRAIN}   # exact statement of a train problem (prefixes collided: 1030_D)
ASK = ("{prompt}\n\nHere is a correct solution:\n```python\n{code}\n```\n\nRewrite this solution with explanatory comments: before every step, "
       "write a comment that explains what the step does and why (the reasoning behind it). Do NOT change the logic, the input/output or "
       "any computation. Give the complete program in a single ```python code block.")


def ok(code, n):
    for t in tests_of(P[n]):
        r = run_python(code, t["input"], timeout=10)
        if r.status != "ok" or not tok_eq(r.stdout, t["output"], V[n]["tol"]):
            return False
    return True


def one(r):
    n = name_of[r["prompt"].split("\n\nWrite a Python 3 program that reads the input")[0].strip()]
    o = chat(ASK.replace("{prompt}", r["prompt"]).replace("{code}", r["code"]), max_tokens=4000, temperature=0.3, seed=11)
    new = last_block(o["text"] or "", ("python", "py"))
    keep = bool(new) and ok(new, n)
    return {**r, "code": new if keep else r["code"], "rewritten": keep}


rows = [json.loads(l) for l in open(f"{RES}/d1_train_A.jsonl")]
with ThreadPoolExecutor(16) as ex:
    out = list(ex.map(one, rows))
with open(f"{RES}/d1b_E.jsonl", "w") as f:
    for r in out:
        f.write(json.dumps(r) + "\n")
print(f"rewritten and verified {sum(r['rewritten'] for r in out)} of {len(out)}")
