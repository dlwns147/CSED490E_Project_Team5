"""HO3 (docs/prereg/PREREG_HO.md): a solution checker written from the problem text, as the free check on hard word problems.
For every freev row (run_nlopt.py mode freev: the program also prints its solution as one JSON object) that runs, prints a value and a
solution, the same model gets the problem text, that solution and the printed objective, and writes a program that tests every constraint
of the text on the solution and recomputes the objective. Passes = it prints `OK <objective>` and that objective matches the printed one
(run_nlopt tolerance). No labels anywhere.
usage: NLOPT_SET=bwor POC_BASE_URL=... python run_verify.py <model> <seed> [source arm, default freev]
       -> results/x3/verify_<model>_<set>[_<arm> if not freev]_s<seed>.jsonl (resumes)"""
import json, os, re, sys, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_nlopt import RES, _rows, correct, problems, value_of  # noqa: E402

ASK = """{q}

A program proposed this solution (decision variable values):
{sol}
and reported the objective value {obj}.

Do not solve the problem again. Write a Python 3 program that CHECKS this proposed solution: copy the values above into the program, test
every constraint stated in the problem text on them (using the numbers given in the text; allow a relative tolerance of 1e-6), and
recompute the objective value from the solution with the costs / profits given in the text. Print exactly one line: `OK <objective value>`
if every constraint holds, or `VIOLATION <short description of the first violated constraint>` otherwise. Only the Python standard library
is available. Give the program in a single ```python code block."""


def main():
    from llm import chat, last_block
    from sandbox import run_python
    m, seed = sys.argv[1], int(sys.argv[2])
    SET = os.environ.get("NLOPT_SET", "bwor")
    Q = {p["id"]: p for p in problems(SET)}
    arm = sys.argv[3] if len(sys.argv) > 3 else "freev"   # HO4: formxv (the library arm with the solution printed)
    src = {r["id"]: r for r in _rows(f"{RES}/opt_{m}_{SET}_{arm}_s{seed}.jsonl")}
    path = f"{RES}/verify_{m}_{SET}{'' if arm == 'freev' else '_' + arm}_s{seed}.jsonl"
    done = {r["id"] for r in _rows(path)}
    todo = [r for i, r in src.items() if i not in done and r.get("status") == "ok" and r.get("pred") not in (None, "NBS") and r.get("solution")]

    def one(r):
        q = ASK.format(q=Q[r["id"]]["q"], sol=r["solution"], obj=r["pred"])
        o = chat(q, max_tokens=8192, temperature=0.7, seed=seed * 1000 + zlib.crc32(r["id"].encode()) % 997 + 11)
        code = last_block(o["text"] or "", ("python", "py", "python3"))
        x = run_python(code, "", timeout=60) if code else None
        out = (x.stdout if x and x.status == "ok" else "") or ""
        line = next((l.strip() for l in reversed(out.strip().splitlines()) if re.match(r"\s*(OK|VIOLATION)\b", l)), "")
        v = value_of(line[2:]) if line.startswith("OK") else None
        passed = bool(line.startswith("OK") and v is not None and v != "NBS" and correct(v, str(r["pred"])))
        return {"id": r["id"], "passed": passed, "verdict": line[:300], "checker_value": v, "status": (x.status if x else "no_code"),
                "err": ((x.stderr or "")[-300:] if x else ""), "code": code, "out_tokens": o.get("out_tokens"), "finish": o.get("finish")}
    with ThreadPoolExecutor(48) as ex, open(path, "a") as f:
        for fu in as_completed([ex.submit(one, r) for r in todo]):
            f.write(json.dumps(fu.result()) + "\n"); f.flush()
    R = _rows(path)
    print(m, SET, seed, f"checked {len(R)}: passed {sum(r['passed'] for r in R)}, violation {sum(r['verdict'].startswith('VIOLATION') for r in R)}, "
          f"no verdict {sum(not r['verdict'] for r in R)}", flush=True)


if __name__ == "__main__":
    main()
