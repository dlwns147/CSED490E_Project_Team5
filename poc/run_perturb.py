"""PoC #1 — does solving survive a surface rewrite of the problem statement?

For easy CodeContests problems (cf_rating <= MAX_RATING) we create:
  orig    : original statement
  story   : same task, I/O format and constraints, but a completely different story/characters/names
  formal  : story stripped -> terse formal spec (definitions + I/O format + constraints only)
Rewrites are produced by an LLM (REWRITER) and are I/O-preserving, so the original tests stay valid.
Each version is solved K times by the solver model; a solution passes iff it passes all kept tests.
A drop orig -> story at equal difficulty hints at surface-form reliance / memorisation.
"""
import argparse
import glob
import json
import os
import random
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from llm import chat_many, last_block  # noqa: E402
from sandbox import run_python, same_output  # noqa: E402

RES = "/NAS/SJ/POSTECH/nlp/results"
REWRITE = {
    "story": ("Rewrite the following competitive-programming problem with a COMPLETELY different story, setting, "
              "characters and object names (e.g. move it to a different domain), while keeping the underlying "
              "mathematical task, every constraint, the exact input format and the exact output format IDENTICAL "
              "(keep the very same letters/symbols/strings that appear in the input and output, e.g. if the input uses "
              "characters 'A' and 'B', the new statement must use 'A' and 'B' too). "
              "Keep the example(s) with the same numbers. Do not add hints or solution ideas. Output only the new "
              "statement inside a single ```text code block.\n\n## Original problem\n{desc}"),
    "formal": ("Rewrite the following competitive-programming problem as a terse, formal specification: remove the "
               "story entirely and state only the mathematical definitions, the exact input format, the exact output "
               "format, constraints and the example(s) (same numbers). Do not add hints or solution ideas. Output only "
               "the new statement inside a single ```text code block.\n\n## Original problem\n{desc}"),
}
SOLVE = ("Solve the following competitive-programming problem in Python 3. Read from standard input and write to "
         "standard output. Think briefly about the algorithm and its complexity first, then give the complete program "
         "in a single final ```python code block.\n\n{desc}")


MULTI_RE = r"any of them|print any|multiple (?:possible )?(?:answers|solutions)|any (?:valid|correct) answer"


def load(max_rating, n, source="eval", exclude_multi=False):
    """source='eval': CodeContests test+valid; 'train': the downloaded train shards (Codeforces only).
    exclude_multi drops problems whose statement admits several correct outputs (exact-match judge invalid)."""
    pats = ["test", "valid"] if source == "eval" else ["train"]
    files = [f for p in pats for f in sorted(glob.glob(f"/NAS/SJ/POSTECH/nlp/data/code_contests/data/{p}-*.parquet"))]
    df = pd.concat([pd.read_parquet(f) for f in files])
    df = df[(df.cf_rating <= max_rating) & (df.cf_rating > 0) & (df.source == 2)]
    df = df[df.generated_tests.apply(lambda g: len(g["input"]) > 0)]
    if exclude_multi:
        df = df[~df.description.str.contains(MULTI_RE, case=False, regex=True)]
    items = []
    for _, r in df.iterrows():
        ts = [(i, o) for k in ("public_tests", "private_tests") for i, o in zip(r[k]["input"], r[k]["output"])]
        ts += list(zip(r["generated_tests"]["input"], r["generated_tests"]["output"]))[:30]
        tl = min(6.0, max(2.0, 3 * (r["time_limit"]["seconds"] + r["time_limit"]["nanos"] / 1e9)))
        items.append(dict(name=r["name"], rating=int(r["cf_rating"]), desc=r["description"], tests=ts, tl=tl,
                          tags=list(r["cf_tags"])))
    random.Random(0).shuffle(items)
    return items[:n]


def judge(code, item):
    if not code:
        return "no_code"
    for i, o in item["tests"]:
        r = run_python(code, i, timeout=item["tl"])
        if r.status != "ok":
            return r.status
        if not same_output(r.stdout, o):
            return "wa"
    return "ac"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_tag", required=True)
    ap.add_argument("--n_items", type=int, default=60)
    ap.add_argument("--max_rating", type=int, default=1200)
    ap.add_argument("--k", type=int, default=2)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--max_tokens", type=int, default=2048)
    ap.add_argument("--source", default="eval", choices=["eval", "train"])
    ap.add_argument("--exclude_multi", action="store_true")
    ap.add_argument("--versions", default="orig,story,formal")
    # control for the self-paraphrase confound: rewrite with a DIFFERENT model than the solver
    ap.add_argument("--rewriter_url", default=None)
    ap.add_argument("--rw_suffix", default="")
    a = ap.parse_args()
    items = load(a.max_rating, a.n_items, a.source, a.exclude_multi)

    # 1) rewrites (cached, generated once with temperature 0 by whatever model is being served first)
    rw_path = f"{RES}/perturb_rewrites.json" if a.source == "eval" else f"{RES}/perturb_rewrites_{a.source}.json"
    if a.rw_suffix:
        rw_path = rw_path.replace(".json", f"{a.rw_suffix}.json")
    rw = json.load(open(rw_path)) if os.path.exists(rw_path) else {}
    want = a.versions.split(",")
    todo = [(it, v) for it in items for v in REWRITE if v in want and f"{it['name']}|{v}" not in rw]
    if todo:
        print("rewriting", len(todo), flush=True)
        import llm
        solver_client = llm.client
        if a.rewriter_url:
            from openai import OpenAI
            llm.client = OpenAI(base_url=a.rewriter_url, api_key="none", timeout=3600)
        outs = chat_many([(REWRITE[v].format(desc=it["desc"]), {}) for it, v in todo], workers=a.workers,
                         temperature=0.0, max_tokens=2048)
        for (it, v), o in zip(todo, outs):
            rw[f"{it['name']}|{v}"] = last_block(o["text"]) if o["finish"] == "stop" else None
        llm.client = solver_client
        json.dump(rw, open(rw_path, "w"), indent=1)

    # 2) solve every version K times
    out_path = f"{RES}/perturb_{a.model_tag}.jsonl"
    done = {(d["name"], d["version"], d["sample"]) for d in map(json.loads, open(out_path))} if os.path.exists(out_path) else set()
    jobs = []
    for it in items:
        vers = {"orig": it["desc"], **{v: rw.get(f"{it['name']}|{v}") for v in REWRITE}}
        vers = {v: d for v, d in vers.items() if v in want}
        if any(t is None for t in vers.values()):
            continue  # keep the comparison paired
        jobs += [(it, v, d, j) for v, d in vers.items() for j in range(a.k) if (it["name"], v, j) not in done]
    print(len(jobs), "solve generations", flush=True)
    B = a.workers * 2
    for s in range(0, len(jobs), B):
        chunk, t0 = jobs[s:s + B], time.time()
        outs = chat_many([(SOLVE.format(desc=d), {"seed": 100 * j + 1}) for _, _, d, j in chunk],
                         workers=a.workers, max_tokens=a.max_tokens)
        with open(out_path, "a") as f:
            for (it, v, _, j), o in zip(chunk, outs):
                code = last_block(o["text"], ("python", "py", "python3"))
                f.write(json.dumps({"name": it["name"], "rating": it["rating"], "version": v, "sample": j,
                                    "verdict": judge(code, it), "finish": o["finish"],
                                    "out_tokens": o["out_tokens"], "response": o["text"]}) + "\n")
        print(f"[{s + len(chunk)}/{len(jobs)}] {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
