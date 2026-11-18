"""Futoshiki (Reasoning Gym generator, difficulty 3, every kept puzzle checked to have exactly one solution): headroom pilot and, later,
the ladder (host/LOOP.md E3, 11-18).

usage: run_futo.py <tag> <arm think|trc|trct> <seed> <file under nlp_data/futo> [--rounds 3]
writes results/futo_<tag>_<arm>_s<seed>_<file stem>.jsonl; prints no accuracy (blind until the prediction is logged).
- think: the puzzle as given (Reasoning Gym's own prompt); the answer grid is read from the last n lines that hold n digits.
- trc / trct: translate into `N`, `GIVEN` {(row, col): value} and `LESS` [((r1, c1), (r2, c2)), ...] meaning cell 1 < cell 2 (0-based);
  a backtracking solver counts solutions (up to 2); label-free feedback on 0 / 2+ / crash.
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
TR = ("{q}\n\nDo not solve the puzzle. Translate it. Give one ```python block that defines `N` (the board size), `GIVEN`, a dict mapping "
      "(row, col) to the given value, and `LESS`, a list of pairs ((r1, c1), (r2, c2)) meaning the value at (r1, c1) is smaller than the value "
      "at (r2, c2). Rows and columns count from 0, top-left first. Write every inequality sign of the picture as one pair, oriented by the "
      "sign: `a < b` and `a > b` between horizontal neighbours, `∧` (the upper cell is smaller) and `∨` (the upper cell is larger) between "
      "vertical neighbours.")
SOLVE = """
import json as _js
_g = [[GIVEN.get((r, c), 0) for c in range(N)] for r in range(N)]
_rel = {}
for (_a, _b) in LESS:
    _rel.setdefault(tuple(_a), []).append((tuple(_b), '<')); _rel.setdefault(tuple(_b), []).append((tuple(_a), '>'))
_cells = [(r, c) for r in range(N) for c in range(N) if _g[r][c] == 0]
_out = []
def _ok(r, c, v):
    if v in _g[r] or any(_g[i][c] == v for i in range(N)): return False
    for (p, q), s in _rel.get((r, c), []):
        w = _g[p][q]
        if w and not (v < w if s == '<' else v > w): return False
    return True
def _go(k):
    if len(_out) >= 2: return
    if k == len(_cells): _out.append([row[:] for row in _g]); return
    r, c = _cells[k]
    for v in range(1, N + 1):
        if _ok(r, c, v):
            _g[r][c] = v; _go(k + 1); _g[r][c] = 0
_bad = [(r, c) for (r, c), v in GIVEN.items() if not (0 <= r < N and 0 <= c < N and 1 <= v <= N)]
if not _bad: _go(0)
print(_js.dumps({"count": len(_out) if not _bad else -1, "grid": _out[0] if _out else None}))
"""


def grid(text, n):
    """the last n lines of the text that hold exactly n digits 1..n, as a list of rows, or None"""
    rows = [list(map(int, re.findall(r"\d", l))) for l in (text or "").splitlines()]
    rows = [r for r in rows if len(r) == n and all(1 <= v <= n for v in r)]
    return rows[-n:] if len(rows) >= n else None


def main():
    tag, arm, seed, fname = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    rounds = int(sys.argv[sys.argv.index("--rounds") + 1]) if "--rounds" in sys.argv else 3
    mt = 30000 if arm == "think" else 16000 if arm == "trct" else 4096
    P = [json.loads(l) for l in open(os.path.join(os.environ["POC_DATA"], "futo", fname))]

    def run(r):
        sd = seed * 10007 + int(r["id"].rsplit("-", 1)[1]) + 1000 * r["n"]
        row = {"id": r["id"], "n": r["n"], "arm": arm, "seed": seed}
        if arm == "think":
            o = chat_msgs([{"role": "user", "content": r["question"]}], think=True, max_tokens=mt, temperature=0.7, seed=sd)
            g = grid(o["text"], r["n"])
            return {**row, "ans": g, "exact": g == r["solution"], "tokens": o["out_tokens"], "finish": o["finish"], "text": (o["text"] or "")[-800:]}
        msgs, tok, hist, out, code = [{"role": "user", "content": TR.format(q=r["question"])}], 0, [], {"count": -1, "grid": None}, None
        for rnd in range(rounds):
            try:
                o = chat_msgs(msgs, think=arm == "trct", max_tokens=mt, temperature=0.7, seed=sd + rnd)
            except Exception as e:
                if rnd == 0:
                    raise
                hist.append({"count": None, "tokens": 0, "err": repr(e)[:300]}); break
            tok += o["out_tokens"]
            code = last_block(o["text"], ("python", "py", "python3"))
            res = run_python(code + "\n" + SOLVE, "", timeout=120, mem_bytes=2 << 30) if code else None
            try:
                out = json.loads(res.stdout.strip().splitlines()[-1])
            except (AttributeError, IndexError, ValueError):
                out = {"count": -1, "grid": None}
            hist.append({"count": out["count"], "tokens": o["out_tokens"], "finish": o["finish"], "err": (res.stderr[-300:] if res else "no code")})
            if out["count"] == 1:
                break
            fb = {-1: f"it failed to run or gave cells outside the board: {(res.stderr[-600:] if res else 'no python block')}",
                  0: "no filling of the board satisfies GIVEN and LESS as you wrote them, so one entry is wrong",
                  2: "more than one filling satisfies GIVEN and LESS as you wrote them, so a given value or an inequality is missing"}[min(out["count"], 2) if out["count"] >= 0 else -1]
            msgs += [{"role": "assistant", "content": o["text"] or "(empty)"},
                     {"role": "user", "content": f"The puzzle has exactly one solution, but {fb}. Compare each entry with the picture and give the complete corrected ```python block."}]
        return {**row, "count": out["count"], "ans": out["grid"], "exact": out["count"] == 1 and out["grid"] == r["solution"], "tokens": tok,
                "rounds": len(hist), "hist": hist, "code": code}

    path = f"{RES}/futo_{tag}_{arm}_s{seed}_{fname.rsplit('.', 1)[0]}.jsonl"
    rows = []
    with ThreadPoolExecutor(32) as ex, open(path, "w") as f:
        for x in ex.map(run, P):
            rows.append(x); f.write(json.dumps(x) + "\n"); f.flush()
    extra = f" count=1 {sum(x.get('count') == 1 for x in rows)}" if arm != "think" else f" parsed {sum(x['ans'] is not None for x in rows)} capped {sum(x['finish'] == 'length' for x in rows)}"
    print(tag, arm, seed, fname, f"{len(rows)} rows, tokens {sum(x['tokens'] for x in rows) / len(rows):.0f}{extra}", flush=True)


if __name__ == "__main__":
    main()
