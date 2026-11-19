"""Futoshiki (Reasoning Gym generator, difficulty 3, every kept puzzle checked to have exactly one solution): headroom pilot and, later,
the ladder (host/LOOP.md E3, 11-18).

usage: run_futo.py <tag> <arm think|trc|trct> <seed> <file under nlp_data/futo> [--rounds 3]
writes results/futo_<tag>_<arm>_s<seed>_<file stem>.jsonl; prints no accuracy (blind until the prediction is logged).
- think: the puzzle as given (Reasoning Gym's own prompt); the answer grid is read from the last n lines that hold n digits.
- trc / trct: translate into `N`, `GIVEN` {(row, col): value} and `LESS` [((r1, c1), (r2, c2)), ...] meaning cell 1 < cell 2 (0-based);
  CP-SAT counts solutions (up to 2; replaced the 11-18 backtracking harness, which timed out on wrong 7x7/9x9 translations); label-free feedback on 0 / 2+ / crash.
"""
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
POT = ("{q}\n\nWrite one complete ```python program that solves this puzzle by search and prints the solved grid, one row per line, "
       "numbers separated by spaces. Use only the Python standard library or OR-Tools (`ortools`). Do not solve it by hand; the program's "
       "output is your answer.")   # program-of-thought baseline (PAL/PoT), 11-19
TR = ("{q}\n\nDo not solve the puzzle. Translate it. Give one ```python block that defines `N` (the board size), `GIVEN`, a dict mapping "
      "(row, col) to the given value, and `LESS`, a list of pairs ((r1, c1), (r2, c2)) meaning the value at (r1, c1) is smaller than the value "
      "at (r2, c2). Rows and columns count from 0, top-left first. Write every inequality sign of the picture as one pair, oriented by the "
      "sign: `a < b` and `a > b` between horizontal neighbours, `∧` (the upper cell is smaller) and `∨` (the upper cell is larger) between "
      "vertical neighbours. You may also copy the picture into a string and write code that builds GIVEN and LESS from it.")
SOLVE = """
import json as _js
from ortools.sat.python import cp_model as _cp
_m = _cp.CpModel()
_x = {(r, c): _m.NewIntVar(1, N, f"x{r}_{c}") for r in range(N) for c in range(N)}
_bad = [k for k, v in GIVEN.items() if tuple(k) not in _x or not (1 <= v <= N)] + [p for p in LESS if tuple(p[0]) not in _x or tuple(p[1]) not in _x]
if not _bad:
    for r in range(N): _m.AddAllDifferent([_x[(r, c)] for c in range(N)])
    for c in range(N): _m.AddAllDifferent([_x[(r, c)] for r in range(N)])
    for k, v in GIVEN.items(): _m.Add(_x[tuple(k)] == v)
    for a, b in LESS: _m.Add(_x[tuple(a)] < _x[tuple(b)])
    class _C(_cp.CpSolverSolutionCallback):
        def __init__(s): super().__init__(); s.sols = []
        def on_solution_callback(s):
            s.sols.append([[s.Value(_x[(r, c)]) for c in range(N)] for r in range(N)])
            if len(s.sols) >= 2: s.StopSearch()
    _s = _cp.CpSolver(); _s.parameters.enumerate_all_solutions = True; _s.parameters.max_time_in_seconds = 60; _cb = _C(); _s.Solve(_m, _cb)
    _out = {"count": len(_cb.sols), "grid": _cb.sols[0] if _cb.sols else None}
    if len(_cb.sols) == 0:   # 11-19 (core feedback): which givens / inequalities cannot hold together, via assumption literals
        _m2 = _cp.CpModel(); _y = {(r, c): _m2.NewIntVar(1, N, f"y{r}_{c}") for r in range(N) for c in range(N)}
        for r in range(N): _m2.AddAllDifferent([_y[(r, c)] for c in range(N)])
        for c in range(N): _m2.AddAllDifferent([_y[(r, c)] for r in range(N)])
        _lits, _names = [], []
        for k, v in GIVEN.items():
            _l = _m2.NewBoolVar(""); _m2.Add(_y[tuple(k)] == v).OnlyEnforceIf(_l); _lits.append(_l); _names.append(f"GIVEN[{tuple(k)}] = {v}")
        for a, b in LESS:
            _l = _m2.NewBoolVar(""); _m2.Add(_y[tuple(a)] < _y[tuple(b)]).OnlyEnforceIf(_l); _lits.append(_l); _names.append(f"{tuple(a)} < {tuple(b)}")
        _m2.AddAssumptions(_lits); _s2 = _cp.CpSolver(); _s2.parameters.max_time_in_seconds = 30; _s2.parameters.num_workers = 1
        if _s2.Solve(_m2) == _cp.INFEASIBLE:
            _idx = {l.Index(): i for i, l in enumerate(_lits)}
            _out["core"] = [_names[_idx[i]] for i in _s2.SufficientAssumptionsForInfeasibility() if i in _idx][:12]
    if len(_cb.sols) == 2:
        _out["differ"] = [(r, c) for r in range(N) for c in range(N) if _cb.sols[0][r][c] != _cb.sols[1][r][c]][:12]
    print(_js.dumps(_out))
else:
    print(_js.dumps({"count": -1, "grid": None}))
"""


def grid(text, n):
    """the last n lines of the text that hold exactly n digits 1..n, as a list of rows, or None"""
    rows = [list(map(int, re.findall(r"\d", l))) for l in (text or "").splitlines()]
    rows = [r for r in rows if len(r) == n and all(1 <= v <= n for v in r)]
    return rows[-n:] if len(rows) >= n else None


def main():
    tag, arm, seed, fname = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    rounds = int(sys.argv[sys.argv.index("--rounds") + 1]) if "--rounds" in sys.argv else 3
    mt = 30000 if arm in ("think", "trct", "trctc", "pot") else 4096   # trct: 16k ran out on every gpt-oss-20b pilot round (11-18)
    P = [json.loads(l) for l in open(os.path.join(os.environ["POC_DATA"], "futo", fname))]

    def run(r):
        sd = seed * 10007 + int(r["id"].rsplit("-", 1)[1]) + 1000 * r["n"]
        row = {"id": r["id"], "n": r["n"], "arm": arm, "seed": seed}
        if arm == "pot":   # PREREG_FUTO F-5: the model writes the whole solver; its printed grid is the answer, no check
            o = chat_msgs([{"role": "user", "content": POT.format(q=r["question"])}], think=True, max_tokens=mt, temperature=0.7, seed=sd)
            code = last_block(o["text"], ("python", "py", "python3")) or last_block(o["text"], ("",))   # tagged first: an untagged answer grid is not code (11-19)
            res = run_python(code, "", timeout=120, mem_bytes=2 << 30) if code else None
            g = grid(res.stdout if res else "", r["n"])
            if g is None and res:   # e.g. a printed list of lists on one line: take the last n*n numbers 1..n
                v = [int(x) for x in re.findall(r"\d+", res.stdout)]
                n = r["n"]
                if len(v) >= n * n and all(1 <= x <= n for x in v[-n * n:]):
                    g = [v[-n * n:][k * n:(k + 1) * n] for k in range(n)]
            return {**row, "ans": g, "exact": g == r["solution"], "tokens": o["out_tokens"], "finish": o["finish"], "ran": bool(res and res.stdout), "stdout": (res.stdout[-400:] if res else ""),
                    "err": (res.stderr[-300:] if res else "no code"), "text": (o["text"] or "")[-600:]}
        if arm == "think":
            o = chat_msgs([{"role": "user", "content": r["question"]}], think=True, max_tokens=mt, temperature=0.7, seed=sd)
            g = grid(o["text"], r["n"])
            return {**row, "ans": g, "exact": g == r["solution"], "tokens": o["out_tokens"], "finish": o["finish"], "text": (o["text"] or "")[-800:]}
        msgs, tok, hist, out, code = [{"role": "user", "content": TR.format(q=r["question"])}], 0, [], {"count": -1, "grid": None}, None
        for rnd in range(rounds):
            try:
                o = chat_msgs(msgs, think=arm in ("trct", "trctc"), max_tokens=mt, temperature=0.7, seed=sd + rnd)
            except Exception as e:
                if rnd == 0:
                    raise
                hist.append({"count": None, "tokens": 0, "err": repr(e)[:300]}); break
            tok += o["out_tokens"]
            code = last_block(o["text"], ("python", "py", "python3")) or last_block(o["text"], ("",))
            res = run_python(code + "\n" + SOLVE, "", timeout=120, mem_bytes=2 << 30) if code else None
            try:
                out = json.loads(res.stdout.strip().splitlines()[-1])
            except (AttributeError, IndexError, ValueError):
                out = {"count": -1, "grid": None}
            hist.append({"count": out["count"], "tokens": o["out_tokens"], "finish": o["finish"], "err": (res.stderr[-300:] if res else "no code"), "text": (o["text"] or "")[-600:], "core": out.get("core"), "differ": out.get("differ")})
            if out["count"] == 1:
                break
            if arm == "trctc" and out.get("core"):   # core feedback: name the entries that cannot all hold together
                fb0 = "these entries cannot all hold together, so at least one of them is misread from the picture: " + "; ".join(out["core"])
            elif arm == "trctc" and out.get("differ"):
                fb0 = "these cells are not pinned down, so a given value or an inequality next to them is missing: " + ", ".join(map(str, out["differ"]))
            else:
                fb0 = None
            fb = {-1: f"it failed to run or gave cells outside the board: {(res.stderr[-600:] if res else 'no python block')}",
                  0: "no filling of the board satisfies GIVEN and LESS as you wrote them, so one entry is wrong",
                  2: "more than one filling satisfies GIVEN and LESS as you wrote them, so a given value or an inequality is missing"}[min(out["count"], 2) if out["count"] >= 0 else -1]
            if fb0:
                fb = fb0
            msgs += [{"role": "assistant", "content": o["text"] or "(empty)"},
                     {"role": "user", "content": f"The puzzle has exactly one solution, but {fb}. Compare each entry with the picture and give the complete corrected ```python block."}]
        return {**row, "count": out["count"], "ans": out["grid"], "exact": out["count"] == 1 and out["grid"] == r["solution"], "tokens": tok,
                "rounds": len(hist), "hist": hist, "code": code}

    path = f"{RES}/futo_{tag}_{arm}_s{seed}_{fname.rsplit('.', 1)[0]}.jsonl"
    rows = []
    if "--resume" in sys.argv and os.path.exists(path):   # keep the rows already written (a run moved to another GPU), run the rest
        rows = [json.loads(l) for l in open(path)]
        P = [r for r in P if r["id"] not in {x["id"] for x in rows}]
    with ThreadPoolExecutor(32) as ex, open(path, "a" if rows else "w") as f:
        for x in ex.map(run, P):
            rows.append(x); f.write(json.dumps(x) + "\n"); f.flush()
    extra = f" count=1 {sum(x.get('count') == 1 for x in rows)}" if arm not in ("think", "pot") else f" parsed {sum(x['ans'] is not None for x in rows)} capped {sum(x['finish'] == 'length' for x in rows)}"
    print(tag, arm, seed, fname, f"{len(rows)} rows, tokens {sum(x['tokens'] for x in rows) / len(rows):.0f}{extra}", flush=True)


if __name__ == "__main__":
    main()
