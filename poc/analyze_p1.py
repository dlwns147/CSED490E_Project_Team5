"""P1 (results/PREREG_P1.md): prompt rewording on contest geometry: accuracy, tokens, cap hits, no-code rate and per-problem agreement
with the original template (vs the seed-to-seed agreement of the original). usage: CC_SET=full python analyze_p1.py"""
import json, os, statistics as st, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("CC_SET", "full")
from run_cc import RES  # noqa: E402

load = lambda t, s: {r["name"]: r for r in map(json.loads, open(f"{RES}/cc_full_{t}_s{s}.jsonl"))} if os.path.exists(f"{RES}/cc_full_{t}_s{s}.jsonl") else None
for orig, paras in (("oss120_low", ("oss120_low_para1", "oss120_low_para2")), ("q36_plain", ("q36_para1", "q36_para2"))):
    O = {sd: load(orig, sd) for sd in (1, 2, 3)}
    def prof(D):
        rows = [r for sd in D if D[sd] for r in D[sd].values()]
        t = sorted(r.get("out_tokens") or 0 for r in rows)
        return (f"{100 * sum(r['passed_all'] for r in rows) / len(rows):5.1f}% @ {st.mean(t) / 1000:.1f}k (p90 {t[int(.9 * len(t))] / 1000:.1f}k), "
                f"caps {sum(r.get('finish') == 'length' for r in rows)}, no code {sum(not r['code'] for r in rows)}, n {len(rows)}")
    base_agree = sum(O[1][n]["passed_all"] == O[2][n]["passed_all"] for n in O[1]) / len(O[1])
    print(f"{orig}: original {prof(O)}; seed 1 vs 2 agreement {100 * base_agree:.1f}%")
    for p in paras:
        D = {sd: load(p, sd) for sd in (1, 2, 3)}
        if not all(D.values()):
            print(f"  {p}: incomplete"); continue
        agree = sum(D[sd][n]["passed_all"] == O[sd][n]["passed_all"] for sd in (1, 2, 3) for n in D[sd]) / sum(len(D[sd]) for sd in (1, 2, 3))
        per = [round(100 * sum(r["passed_all"] for r in D[sd].values()) / len(D[sd]), 1) for sd in (1, 2, 3)]
        print(f"  {p}: {prof(D)}; per seed {per}; agreement with the original (same seed) {100 * agree:.1f}%")
