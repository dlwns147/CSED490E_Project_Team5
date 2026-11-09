"""Idea 24, offline: is every clue of an accepted (count-1) ZebraLogic translation necessary?

Usage: python poc/zl_min.py results/zl_q8bf_trf_s1.jsonl [...]   -> results/zlmin_<same name>.jsonl
ZebraLogic's generator drops clues until none can go without losing uniqueness (2502.01100 section 2), so a faithful
one-to-one translation has no redundant clue. Flag R: some clue can be left out with the count staying 1.
Flag N: the number of clue expressions differs from the puzzle's numbered clues. No model call; the recorded program is re-run.
Decision rule: docs/notes/IDEAS_COMPUTATION.md row 24.
"""
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sandbox import run_python  # noqa: E402

MIN_SOLVE = """
import ast, itertools, json
from ortools.sat.python import cp_model
n = max(len(x) for x in groups.values())
def _count(cl):
    m, v = cp_model.CpModel(), {}
    for a, vals in groups.items():
        for x in vals:
            v[f"{a}:{x}"] = m.NewIntVar(1, n, f"{a}:{x}")
        m.AddAllDifferent([v[f"{a}:{x}"] for x in vals])
    for c in cl:
        keys = sorted({t.slice.value for t in ast.walk(ast.parse(c, mode="eval")) if isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant)})
        code = compile(c, "clue", "eval")
        ok = [t for t in itertools.product(range(1, n + 1), repeat=len(keys)) if eval(code, {"abs": abs, "min": min, "max": max}, {"p": dict(zip(keys, t))})]
        m.AddAllowedAssignments([v[k] for k in keys], ok)
    class _C(cp_model.CpSolverSolutionCallback):
        def __init__(self):
            super().__init__(); self.k = 0
        def on_solution_callback(self):
            self.k += 1
            if self.k >= 2:
                self.StopSearch()
    s = cp_model.CpSolver(); s.parameters.enumerate_all_solutions = True; s.parameters.num_workers = 1
    cb = _C(); s.Solve(m, cb)
    return cb.k
print(json.dumps({"count": _count(clues), "exprs": len(clues), "redundant": [i for i in range(len(clues)) if _count(clues[:i] + clues[i + 1:]) == 1]}))
"""


def n_clues(puzzle):
    return len(re.findall(r"^\d+\. ", puzzle.split("## Clues:")[-1], flags=re.M))


def main():
    P = {r["id"]: r for r in map(json.loads, open(os.path.join(os.environ.get("POC_DATA", "/NAS/SJ/POSTECH/nlp_data"), "zebralogic", "grid.jsonl")))}
    for src in sys.argv[1:]:
        R = [r for r in map(json.loads, open(src)) if r.get("count") == 1 and r.get("code")]

        def one(r):
            res = run_python(r["code"] + "\n" + MIN_SOLVE, "", timeout=120, mem_bytes=4 << 30)
            row = {"id": r["id"], "seed": r["seed"], "exact": r["exact"], "clues": n_clues(P[r["id"]]["puzzle"])}
            try:
                return {**row, **json.loads(res.stdout.strip().splitlines()[-1])}
            except Exception:
                return {**row, "err": (res.stderr or res.status)[-200:]}

        dst = os.path.join(os.path.dirname(src), "zlmin_" + os.path.basename(src))
        with ThreadPoolExecutor(int(os.environ.get("MIN_WORKERS", 4))) as ex, open(dst, "w") as f:
            for row in ex.map(one, R):
                f.write(json.dumps(row) + "\n")
        print(dst, len(R))


if __name__ == "__main__":
    main()
