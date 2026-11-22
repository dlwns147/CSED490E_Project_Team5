# Committed copy of results/tmp_futo_pot.py (CRITIQUE PLAN P5, 2026-11-20); run from the repo root: python3 poc/analyze_futo_pot.py <model tags>
"""PREREG_FUTO F-5: ladder (as tmp_futo_score) vs program-of-thought (`pot`, medium effort), paired over the 300 test puzzles."""
import json, os, random, sys
POT_SUFFIX = os.environ.get("POT_SUFFIX", "2")
from collections import defaultdict
U = lambda ok, t: 100 * ok - 0.5 * t / 1000
L = lambda tag, arm: {x["id"]: x for n in (5, 7, 9) for x in map(json.loads, open(f"results/futo_{tag}_{arm}_s1_test_{n}.jsonl"))}
for main in sys.argv[1:]:
    trc, trct, TH, P = L(main, "trc"), L(main, "trct"), L(main + "M", "think"), L(main + "M" + sys.argv[0][-0:] * 0 + POT_SUFFIX, "pot")
    d = []; lad = []; byn = defaultdict(lambda: [0, 0, 0])
    for i, t in TH.items():
        tok, got = 0, None
        for r in (trc[i], trct[i]):
            tok += r["tokens"]
            if r["count"] == 1 and r["ans"]:
                got = r; break
        ok = got["exact"] if got else t["exact"]; tok += 0 if got else t["tokens"]; p = P[i]
        d.append(U(ok, tok) - U(p["exact"], p["tokens"])); lad.append((ok, tok)); b = byn[t["n"]]; b[0] += 1; b[1] += ok; b[2] += p["exact"]
    n = len(d); random.seed(0); bs = sorted(sum(random.choice(d) for _ in range(n)) / n for _ in range(4000))
    pv = list(P.values())
    print(f"{main}: program-of-thought {sum(r['exact'] for r in pv)/n:.1%} at {sum(r['tokens'] for r in pv)/n/1000:.1f}k (ran {sum(r['ran'] for r in pv)}, capped {sum(r['finish']=='length' for r in pv)}) | ladder {sum(o for o,_ in lad)/n:.1%} at {sum(t for _,t in lad)/n/1000:.1f}k | ladder - PoT {sum(d)/n:+.1f} [{bs[100]:+.1f}, {bs[3899]:+.1f}]")
    print("   by size (ladder / PoT): " + "; ".join(f"{k}x{k}: {v[1]} / {v[2]}" for k, v in sorted(byn.items())))
