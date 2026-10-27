"""IF-1 (docs/prereg/PREREG_IF.md): instruction following, where thinking can hurt. Per prompt and seed, all arms against one server:
  cheap  N = non-thinking response; C = the model's own checker, written from the instruction alone (non-thinking: a Python function
         check(response) -> list of violated requirements, standard library only), run in the sandbox on N; R = one non-thinking
         rewrite of N given C's violations (DVR-style refine, only where C fails on N), checked by C; S = self-selective reasoning
         (Li et al. 2025 style): the model answers yes / no to "would thinking first help you follow every requirement?"
  think  T = thinking response (16k cap)
  sb     SB = thinking cut at 2,000 tokens (budget forcing), then the response
  check  C (the same seed's) run on T and SB
Benchmarks: ifeval (541 prompts, google/IFEval) and ifbench (300, allenai/IFBench test), data and official graders in $POC_DATA/ifeval.
Scoring is offline (poc/grade_if.py, official strict grader; poc/analyze_if.py, the policies). Rows resume.
usage: python run_if.py <ifeval|ifbench> <tag> <seed>     (IF_SUBSET=i/k: prompts i, i+k, ... only — the smoke)"""
import json, os, sys, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import chat, last_block  # noqa: E402
from run_geo_cross import budget_chat  # noqa: E402
from run_nlopt import _rows  # noqa: E402
from sandbox import run_python  # noqa: E402

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "if")
DATA = os.path.join(os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data"), "ifeval")
FILES = {"ifeval": "ifeval_input_data.jsonl", "ifbench": "IFBench_test.jsonl"}

CHECKER = """Below is an instruction that a response must follow. Write a Python function `check(response: str) -> list` that returns a \
list of short strings, one for each requirement of the instruction that the response violates, and [] when every requirement is met. \
Check only requirements that code can verify exactly (format, length, counts of words / sentences / paragraphs / letters, punctuation, \
sections, keywords, start or end phrases, letter case, repetition); ignore content quality. Use only the Python standard library. \
Return only the code, in one ```python block.

Instruction:
{q}"""
RUNNER = """

import json as _json, sys as _sys
_r = _sys.stdin.read()
try:
    _v = check(_r)
except Exception as _e:
    print(_json.dumps({"error": repr(_e)[:200]}))
else:
    print(_json.dumps({"violations": [str(_x)[:200] for _x in (_v or [])]}))
"""
REWRITE = """{q}

Your response:
{a}

A check of your response found these problems:
{v}

Rewrite the response so that it follows every requirement of the instruction. Output only the new response."""
SELECT = """Here is an instruction. Before answering it, decide: would thinking step by step first help you follow all of its \
requirements? Answer with one word, yes or no.

Instruction:
{q}"""


def check(code, response):
    """'pass' / 'fail' (with the violations) / 'error' (no checker, it crashed, timed out or printed nothing usable)"""
    if not code:
        return "error", []
    r = run_python(code + RUNNER, response or "", timeout=10, mem_bytes=1 << 30)
    try:
        o = json.loads((r.stdout or "").strip().splitlines()[-1])
    except (ValueError, IndexError):
        return "error", []
    if "violations" not in o:
        return "error", []
    return ("fail" if o["violations"] else "pass"), o["violations"]


def main():
    bench, tag, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
    P = [json.loads(l) for l in open(os.path.join(DATA, FILES[bench]))]
    for p in P:
        p["id"] = str(p["key"])
    if os.environ.get("IF_SUBSET"):
        i, k = map(int, os.environ["IF_SUBSET"].split("/")); P = P[i::k]
    os.makedirs(RES, exist_ok=True)
    path = {a: f"{RES}/{bench}_{tag}_{a}_s{seed}.jsonl" for a in ("cheap", "think", "sb", "check")}
    done = {a: {r["id"] for r in _rows(f)} for a, f in path.items()}
    sd = lambda p: seed * 1000 + zlib.crc32(p["id"].encode()) % 997

    def cheap(p):
        q, s = p["prompt"], sd(p)
        n = chat(q, think=False, max_tokens=4096, temperature=0.7, seed=s)
        c = chat(CHECKER.format(q=q), think=False, max_tokens=2048, temperature=0.7, seed=s)
        code = last_block(c["text"] or "", ("python", "py", "python3"))
        cn, vn = check(code, n["text"])
        row = {"id": p["id"], "n_text": n["text"], "n_tok": n["out_tokens"], "n_finish": n["finish"], "c_code": code, "c_tok": c["out_tokens"],
               "c_n": cn, "v_n": vn}
        if cn == "fail":
            r = chat(REWRITE.format(q=q, a=n["text"], v="\n".join(f"- {x}" for x in vn)), think=False, max_tokens=4096, temperature=0.7, seed=s)
            row.update(r_text=r["text"], r_tok=r["out_tokens"], r_finish=r["finish"], c_r=check(code, r["text"])[0])
        d = chat(SELECT.format(q=q), think=False, max_tokens=8, temperature=0.7, seed=s)
        row.update(s_ans=(d["text"] or "").strip().lower()[:20], s_tok=d["out_tokens"])
        return "cheap", row

    def think(p):
        o = chat(p["prompt"], think=True, max_tokens=16000, temperature=0.7, seed=sd(p))
        return "think", {"id": p["id"], "text": o["text"], "out_tokens": o["out_tokens"], "finish": o["finish"]}

    def sb(p):
        o = budget_chat(p["prompt"], 2000, max_tokens=4096, temperature=0.7, seed=sd(p), cut_note="I will now write the response.")
        return "sb", {"id": p["id"], "text": o["text"], "out_tokens": o["out_tokens"], "think_tokens": o["think_tokens"], "finish": o["finish"]}

    jobs = [(f, p) for p in P for a, f in (("cheap", cheap), ("think", think), ("sb", sb)) if p["id"] not in done[a]]
    out = {a: open(f, "a") for a, f in path.items()}
    with ThreadPoolExecutor(64) as ex:
        for fu in as_completed([ex.submit(f, p) for f, p in jobs]):
            try:
                a, row = fu.result()
                out[a].write(json.dumps(row) + "\n"); out[a].flush()
            except Exception as e:   # as run_form: one failed request must not stop the other rows
                print(bench, tag, seed, "request failed, no row:", repr(e)[:200], flush=True)
    C = {r["id"]: r for r in _rows(path["cheap"])}
    T = {r["id"]: r for r in _rows(path["think"])}
    SB = {r["id"]: r for r in _rows(path["sb"])}
    for i in sorted(set(C) & set(T) & set(SB) - done["check"]):   # the same checker on the thinking arms
        out["check"].write(json.dumps({"id": i, "c_t": check(C[i]["c_code"], T[i]["text"])[0], "c_sb": check(C[i]["c_code"], SB[i]["text"])[0]}) + "\n")
    for f in out.values():
        f.close()
    rows = _rows(path["cheap"])
    print(bench, tag, seed, f"cheap {len(rows)} think {len(T)} sb {len(SB)}; checker on N:",
          {k: sum(r["c_n"] == k for r in rows) for k in ("pass", "fail", "error")}, flush=True)


if __name__ == "__main__":
    main()
