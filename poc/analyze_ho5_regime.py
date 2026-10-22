"""HO5 (docs/prereg/PREREG_HO.md): the label-free regime call — among cheap programs (arm freev) that run and print a value, the share
that agree with a second cheap program of the next seed; ≥ 85% → easy regime (plain recipe), < 85% → hard regime (add the solution
checker). Reads no labels. usage: python analyze_ho5_regime.py <set> [arm]"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_nlopt import RES, _rows  # noqa: E402

ok_ = lambda r: r.get("status") == "ok" and r.get("pred") not in (None, "NBS")
same = lambda a, b: abs(float(a) - float(b)) <= max(1e-2, 1e-3 * abs(float(b)))

SET = sys.argv[1]; ARM = sys.argv[2] if len(sys.argv) > 2 else "freev"
for m in ("oss20", "q14a", "q8b"):
    agree = pairs = run = n = 0
    for s in (1, 2, 3):
        F, G = ({r["id"]: r for r in _rows(f"{RES}/opt_{m}_{SET}_{ARM}_s{k}.jsonl")} for k in (s, s % 3 + 1))
        for i, f in F.items():
            n += 1; run += ok_(f)
            if ok_(f) and i in G and ok_(G[i]):
                pairs += 1; agree += same(f["pred"], G[i]["pred"])
    if n:
        a = 100 * agree / max(1, pairs)
        print(f"{SET} {m:5s} rows {n}, run and print a value {100 * run / n:.0f}%, two-program agreement {a:.0f}% ({pairs} pairs) -> "
              f"{'easy: plain recipe' if a >= 85 else 'hard: add the solution checker'}")
