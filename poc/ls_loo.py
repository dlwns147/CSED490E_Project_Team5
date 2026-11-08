"""Idea 19, offline: re-solve AR-LSAT declarations that allow no arrangement with each rule left out in turn.

Usage: python poc/ls_loo.py results/ls_q8b_dev_trs_s1.jsonl results/ls_loo_dev_trs_s1.jsonl
Decision rule (docs/notes/IDEAS_COMPUTATION.md row 19): accept a mark only if every left-out set that allows arrangements
gives exactly one mark and all give the same one. No model call; the recorded final-round program is re-run.
"""
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sandbox import run_python  # noqa: E402

LOO_SOLVE = """
import json, time
_t = time.time()
def _holds(f, a):
    try:
        return bool(f(a))
    except Exception:
        return False
_by = {i: [] for i in range(len(RULES))}
for _a in arrangements():
    if _holds(CONDITION, _a):
        _f = [i for i, f in enumerate(RULES) if not _holds(f, _a)]
        if len(_f) == 1:
            _by[_f[0]].append(_a)
    if time.time() - _t > 100:
        raise SystemExit("enumeration took over 100 s")
_k = {"could": "cannot", "cannot": "could", "must": "could_false", "could_false": "must"}[KIND] if globals().get("EXCEPT") else KIND
_out = {}
for i, ok in _by.items():
    if not ok:
        continue
    _n = {L: sum(_holds(OPTIONS[L], a) for a in ok) for L in "ABCDE"}
    _q = {"could": lambda n: n > 0, "must": lambda n: n == len(ok), "cannot": lambda n: n == 0, "could_false": lambda n: n < len(ok)}[_k]
    _out[i] = {"allowed": len(ok), "marks": sorted(L for L in "ABCDE" if _q(_n[L]))}
print(json.dumps({"rules": len(RULES), "loo": _out}))
"""


def one(r):
    res = run_python(r["code"] + "\n" + LOO_SOLVE, "", timeout=120, mem_bytes=4 << 30)
    row = {"id": r["id"], "gold": r["gold"]}
    try:
        out = json.loads(res.stdout.strip().splitlines()[-1])
    except Exception:
        return {**row, "err": (res.stderr or res.status)[-200:]}
    marks = [tuple(v["marks"]) for v in out["loo"].values()]
    pick = marks[0][0] if marks and all(len(m) == 1 for m in marks) and len(set(marks)) == 1 else None
    return {**row, **out, "pick": pick, "exact": pick == r["gold"] if pick else None}


def main():
    src, dst = sys.argv[1], sys.argv[2]
    R = [json.loads(l) for l in open(src)]
    R = [r for r in R if r.get("code") and r["hist"] and r["hist"][-1].get("allowed") == 0]
    with ThreadPoolExecutor(int(os.environ.get("LOO_WORKERS", 16))) as ex, open(dst, "w") as f:
        for row in ex.map(one, R):
            f.write(json.dumps(row) + "\n")
    rows = [json.loads(l) for l in open(dst)]
    acc = [x for x in rows if x.get("pick")]
    print(f"zero-allowed {len(rows)}, errors {sum('err' in x for x in rows)}, accepted {len(acc)}, right {sum(x['exact'] for x in acc)}")


if __name__ == "__main__":
    main()
