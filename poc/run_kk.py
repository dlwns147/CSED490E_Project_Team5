"""Knights and Knaves (Xie et al. 2410.23123; 700 test puzzles, 2-8 inhabitants, exactly one solution each): a new domain for the ladder
and a prospective test of the label-free gain estimate (host/exp_log.txt, 11-18).

usage: run_kk.py <tag> <arm think|trc|trct> <seed> [--people 2,3,...]
writes results/kk_<tag>_<arm>_s<seed>.jsonl. Rows keep `exact` for the later scoring, but the run prints no accuracy, so the label-free
prediction can be fixed before anyone reads a score.
- think: the puzzle, answer as JSON on the last line.
- trc / trct: translate into `NAMES` and `ok(k)` without / with thinking; every assignment is enumerated and the consistent ones counted;
  up to --rounds 3, with label-free feedback (failed to run / no assignment / several assignments).
Data: nlp_data/kk_dl/people<n>.jsonl (HF K-and-K/knights-and-knaves, test split).
"""
import ast
import itertools  # noqa: F401  (used in the sandboxed harness text)
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
from llm import chat_msgs, last_block  # noqa: E402
from sandbox import run_python  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = f"{ROOT}/results"
FMT = ("{q}\n\nWho is a knight and who is a knave? On the last line give the answer as JSON: "
       "{{\"<name>\": \"knight\" or \"knave\", ...}} for every inhabitant.")
TR = ("{q}\n\nDo not solve the puzzle. Translate it. Give one ```python block that defines `NAMES`, the inhabitants' names in the order "
      "given, and `ok(k)`: given a dict `k` that maps each name to True (knight) or False (knave), return True exactly when every statement "
      "is consistent with its speaker: a knight's statement is true and a knave's statement is false. Write one condition per statement, "
      "for example `k['Ann'] == (k['Bob'] or not k['Cy'])` for \"Ann said: Bob is a knight or Cy is a knave\".")
SOLVE = """
import itertools as _it, json as _js
_sols = []
for _v in _it.product([True, False], repeat=len(NAMES)):
    _k = dict(zip(NAMES, _v))
    if ok(_k):
        _sols.append(_k)
        if len(_sols) > 1:
            break
print(_js.dumps({"count": len(_sols), "sol": _sols[0] if _sols else None}))
"""


def answer(text, names):
    """{name: True if knight} from the last JSON object in the text, else from 'X is a knight/knave' sentences; None if incomplete"""
    for m in reversed(re.findall(r"\{[^{}]*\}", text or "")):
        try:
            d = json.loads(m)
        except ValueError:
            continue
        a = {n: str(d.get(n, "")).strip().lower() for n in names}
        if all(v in ("knight", "knave") for v in a.values()):
            return {n: v == "knight" for n, v in a.items()}
    a = {}
    for n, v in re.findall(r"\b(" + "|".join(map(re.escape, names)) + r")\b[^.\n]{0,20}?\bis an? (knight|knave)", text or ""):
        a[n] = v == "knight"
    return a if len(a) == len(names) else None


def main():
    tag, arm, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
    opt = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
    people = [int(x) for x in opt("--people", "2,3,4,5,6,7,8").split(",")]
    rounds = int(opt("--rounds", 3))
    mt = int(opt("--max_tokens", 30000 if arm == "think" else 16000 if arm == "trct" else 4096))
    P = []
    for n in people:
        for r in map(json.loads, open(os.path.join(os.environ["POC_DATA"], "kk_dl", f"people{n}.jsonl"))):
            names = ast.literal_eval(r["names"]) if isinstance(r["names"], str) else r["names"]
            sol = ast.literal_eval(r["solution"]) if isinstance(r["solution"], str) else r["solution"]
            P.append({"id": f"kk{n}-{r['index']}", "n": n, "quiz": r["quiz"], "names": names, "gold": dict(zip(names, sol))})

    def run(r):
        sd = seed * 10007 + r["n"] * 1000 + int(r["id"].rsplit("-", 1)[1])
        row = {"id": r["id"], "n": r["n"], "arm": arm, "seed": seed}
        if arm == "think":
            o = chat_msgs([{"role": "user", "content": FMT.format(q=r["quiz"])}], think=True, max_tokens=mt, temperature=0.7, seed=sd)
            a = answer(o["text"], r["names"])
            return {**row, "ans": a, "exact": a == r["gold"], "tokens": o["out_tokens"], "finish": o["finish"], "text": (o["text"] or "")[-600:]}
        msgs, tok, hist, out, code = [{"role": "user", "content": TR.format(q=r["quiz"])}], 0, [], {"count": -1, "sol": None}, None
        for rnd in range(rounds):
            try:
                o = chat_msgs(msgs, think=arm == "trct", max_tokens=mt, temperature=0.7, seed=sd + rnd)
            except Exception as e:
                if rnd == 0:
                    raise
                hist.append({"count": None, "tokens": 0, "err": repr(e)[:300]})
                break
            tok += o["out_tokens"]
            code = last_block(o["text"], ("python", "py", "python3"))
            res = run_python(code + "\n" + SOLVE, "", timeout=60, mem_bytes=2 << 30) if code else None
            try:
                out = json.loads(res.stdout.strip().splitlines()[-1])
            except (AttributeError, IndexError, ValueError):
                out = {"count": -1, "sol": None}
            hist.append({"count": out["count"], "tokens": o["out_tokens"], "finish": o["finish"], "err": (res.stderr[-300:] if res else "no code")})
            if out["count"] == 1:
                break
            fb = {-1: f"it failed to run: {(res.stderr[-600:] if res else 'no python block')}",
                  0: "no assignment of knights and knaves satisfies `ok` as you wrote it, so one condition is wrong",
                  2: "more than one assignment satisfies `ok` as you wrote it, so a condition is missing or too weak"}[min(out["count"], 2) if out["count"] >= 0 else -1]
            msgs += [{"role": "assistant", "content": o["text"] or "(empty)"},
                     {"role": "user", "content": f"The puzzle has exactly one solution, but {fb}. Compare each condition with the statements and give the complete corrected ```python block."}]
        a = {n: bool(out["sol"][n]) for n in r["names"]} if out.get("sol") and all(n in out["sol"] for n in r["names"]) else None
        return {**row, "count": out["count"], "ans": a, "exact": out["count"] == 1 and a == r["gold"], "tokens": tok, "rounds": len(hist), "hist": hist, "code": code}

    path = f"{RES}/kk_{tag}_{arm}_s{seed}.jsonl"
    rows = []
    with ThreadPoolExecutor(32) as ex, open(path, "w") as f:
        for x in ex.map(run, P):
            rows.append(x); f.write(json.dumps(x) + "\n"); f.flush()
    extra = f" count=1 {sum(x.get('count') == 1 for x in rows)}" if arm != "think" else f" parsed {sum(x['ans'] is not None for x in rows)} capped {sum(x['finish'] == 'length' for x in rows)}"
    print(tag, arm, seed, f"{len(rows)} rows, tokens {sum(x['tokens'] for x in rows) / len(rows):.0f}{extra}", flush=True)   # no accuracy: kept blind


if __name__ == "__main__":
    main()
