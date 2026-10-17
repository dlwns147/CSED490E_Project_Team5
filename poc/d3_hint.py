"""D3 (docs/prereg/PREREG_D1.md): the base student writes its own solution with the teacher's program as a hint; kept if verified.
-> results/h2/d3_hinted.jsonl, results/h2/d3_D3.jsonl (= hinted + D2-S)
usage: CC_SET=full POC_BASE_URL=... python d3_hint.py"""
import difflib, json, os, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import chat, last_block  # noqa: E402
from run_cc import PFILE, RES, VFILE, tests_of, tok_eq  # noqa: E402
from sandbox import run_python  # noqa: E402

P = {p["name"]: p for p in json.load(open(PFILE))}; V = json.load(open(VFILE))
TRAIN = json.load(open(f"{RES}/d1_split.json"))["train"]
name_of = {P[n]["description"].strip(): n for n in TRAIN}
SEP = "\n\nWrite a Python 3 program that reads the input"
HINT = ("{prompt}\n\nA correct solution written by another programmer, for reference:\n```python\n{code}\n```\n\n"
        "Now write YOUR OWN complete solution in your usual style: explain each step in a comment before writing it. "
        "Give the program in a single ```python code block.")


def ok(code, n):
    for t in tests_of(P[n]):
        r = run_python(code, t["input"], timeout=10)
        if r.status != "ok" or not tok_eq(r.stdout, t["output"], V[n]["tol"]):
            return False
    return True


A = [json.loads(l) for l in open(f"{RES}/d1_train_A.jsonl")]
first = {}
for r in A:   # one teacher program per problem as the hint
    first.setdefault(r["prompt"], r)


def one(item):
    prompt, r = item; n = name_of[prompt.split(SEP)[0].strip()]; out = []
    for s in (1, 2):
        o = chat(HINT.replace("{prompt}", prompt).replace("{code}", r["code"]), max_tokens=4000, temperature=0.7, seed=500 + s)
        c = last_block(o["text"] or "", ("python", "py"))
        if c and ok(c, n):
            out.append({"prompt": prompt, "code": c, "task": "cc", "sim": difflib.SequenceMatcher(None, c, r["code"]).ratio(),
                        "comments": sum(x.strip().startswith("#") for x in c.splitlines())})
    return out


with ThreadPoolExecutor(16) as ex:
    res = [x for xs in ex.map(one, list(first.items())) for x in xs]
open(f"{RES}/d3_hinted.jsonl", "w").write("".join(json.dumps(x) + "\n" for x in res))
S = [json.loads(l) for l in open(f"{RES}/d2_S.jsonl")]
open(f"{RES}/d3_D3.jsonl", "w").write("".join(json.dumps(x) + "\n" for x in res + S))
import statistics as st
print(f"hinted verified {len(res)} examples on {len({x['prompt'] for x in res})} problems; median comments "
      f"{st.median(x['comments'] for x in res) if res else 0}; median similarity {st.median(x['sim'] for x in res) if res else 0:.2f}; D3 total {len(res) + len(S)}")
