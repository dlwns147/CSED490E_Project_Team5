"""HO-G-R (docs/prereg/PREREG_HOGC.md, addendum): one cheap repair turn (no thinking) on a visible failure of a held-out geometry fact
program, before thinking. For each stored HO-G fact row that fails the free check (analyze_n10.geo_check: crash, timeout, no output, or
outputs that disagree across the transformed copies of its own input), the same model gets the task statement, its program and the
evidence, and writes a corrected program; it is graded on the 8 variants (labels only for scoring) and re-checked with the same free check.
usage: POC_BASE_URL=... python run_geo_repair.py <model> <seed>   -> results/georepair_<model>_s<seed>.jsonl (resumes)"""
import json, os, random, re, sys, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_n10 as N  # noqa: E402
from run_geo import answer, base_instance, render, variants  # noqa: E402
from run_geo_mr import MR, REL, expected_rel, run_out  # noqa: E402

RES = N.RES

FIX = """{q}

Write a Python 3 program that solves this problem for any input in this stdin format: {fmt}. Print only the answer. Only the Python standard
library is available.

Your previous program:
```python
{code}
```
{evidence}

Write the corrected complete program in a single ```python code block."""


def evidence(r, V):
    ok, sig = N.geo_check(r)
    if sig.startswith("exc:") or sig in ("timeout", "no_output"):
        from sandbox import run_python
        x = run_python(r["code"], render(r["task"], V["identity"])[1], timeout=10)
        tail = "\n".join((x.stderr or "").strip().splitlines()[-4:]) or {"timeout": "it did not finish within 10 seconds",
                                                                        "no_output": "it printed nothing"}.get(sig, sig)
        return f"Running it on the given input failed:\n```\n{tail}\n```"
    base = run_out(r["code"], r["task"], V["identity"])
    for v in MR:
        if r["task"] == "lattice" and v == "scale":
            continue
        o = run_out(r["code"], r["task"], V[v])
        exp = expected_rel(r["task"], v, base)
        if o != exp:
            return (f"On the given input it printed {base}. On {REL[v]}, it printed {o}, but the answer there must be {exp} "
                    f"(the same geometry gives the same answer). Find the bug that makes the answer depend on position, orientation or order.")
    return "Its outputs on transformed copies of the input do not agree."


def main():
    from llm import chat, last_block
    m, seed = sys.argv[1], int(sys.argv[2])
    F = [json.loads(l) for l in open(f"{RES}/geocross_S2_HOG_{m}_geo_fact_s{seed}.jsonl")]
    path = f"{RES}/georepair_{m}_s{seed}.jsonl"
    done = {(r["task"], r["n"], r["inst"]) for r in map(json.loads, open(path))} if os.path.exists(path) else set()
    todo = [r for r in F if r.get("code") and (r["task"], r["n"], r["inst"]) not in done and not N.geo_check(r)[0]]

    def one(r):
        rng = random.Random(f"{r['task']}-{r['n']}-{r['inst']}")
        V = variants(r["task"], base_instance(r["task"], r["n"], rng), rng)
        q, _, fmt = render(r["task"], V["identity"])
        ev = evidence(r, V)
        o = chat(FIX.format(q=q, fmt=fmt, code=r["code"].strip(), evidence=ev), max_tokens=4096, temperature=0.7,
                 seed=seed * 1000 + zlib.crc32(f"{r['task']}-{r['n']}-{r['inst']}".encode()) % 997 + 31)
        code = last_block(o["text"] or "", ("python", "py", "python3"))
        res = {}
        for vname, x in V.items():
            out = run_out(code, r["task"], x) if code else None
            res[vname] = None if out is None and vname == "identity" else (out is not None and out == answer(r["task"], x))
        row = {"task": r["task"], "n": r["n"], "inst": r["inst"], "code": code, "evidence": ev[:400], "per_variant": res,
               "out_tokens": o.get("out_tokens"), "finish": o.get("finish")}
        from run_geo_cross import classify
        row["class"] = classify(res)
        row["passes_check"] = bool(code) and N.geo_check(row)[0]
        return row
    with ThreadPoolExecutor(32) as ex, open(path, "a") as f:
        for fu in as_completed([ex.submit(one, r) for r in todo]):
            f.write(json.dumps(fu.result()) + "\n"); f.flush()
    json.dump(N.CACHE, open(N.CACHE_F, "w"))
    R = [json.loads(l) for l in open(path)]
    print(m, seed, f"repaired {len(R)}: pass the check {sum(r['passes_check'] for r in R)}, right on all 8 {sum(r['class'] == 'correct_all' for r in R)}", flush=True)


if __name__ == "__main__":
    main()
