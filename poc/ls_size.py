"""Idea 26, offline: how much search does the solver do on an AR-LSAT question? Recount the model's candidate arrangements.

Usage: python poc/ls_size.py results/ls_oss20_trs_s1.jsonl [...]   -> results/lssize_<same name>.jsonl
Search size = the number of arrangements the recorded final program's arrangements() yields (cap 10^7). No model call.
Decision rule: docs/notes/IDEAS_COMPUTATION.md row 26.
"""
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sandbox import run_python  # noqa: E402

SIZE = """
import json, time
_t, _n = time.time(), 0
for _a in arrangements():
    _n += 1
    if _n >= 10 ** 7 or time.time() - _t > 100:
        break
print(json.dumps({"candidates": _n, "rules": len(RULES)}))
"""


def main():
    for src in sys.argv[1:]:
        R = [r for r in map(json.loads, open(src)) if r.get("code")]

        def one(r):
            res = run_python(r["code"] + "\n" + SIZE, "", timeout=120, mem_bytes=4 << 30)
            row = {"id": r["id"], "seed": r["seed"], "count": r["count"], "exact": r["exact"]}
            try:
                return {**row, **json.loads(res.stdout.strip().splitlines()[-1])}
            except Exception:
                return {**row, "err": (res.stderr or res.status)[-200:]}

        dst = os.path.join(os.path.dirname(src), "lssize_" + os.path.basename(src))
        with ThreadPoolExecutor(int(os.environ.get("SIZE_WORKERS", 4))) as ex, open(dst, "w") as f:
            for row in ex.map(one, R):
                f.write(json.dumps(row) + "\n")
        print(dst, len(R))


if __name__ == "__main__":
    main()
