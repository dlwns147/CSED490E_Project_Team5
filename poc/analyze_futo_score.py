# Committed copy of results/tmp_futo_score.py (CRITIQUE PLAN P5, 2026-11-21); run from the repo root: python3 poc/analyze_futo_score.py <model tags>
"""PREREG_FUTO scoring (only after the F-2 prediction is logged): per model, both thinking settings, the ladder (trc -> trct -> the
better thinking setting by utility), measured accuracy term, dU with paired bootstrap; by size."""
import json, random, sys
from collections import defaultdict
U = lambda ok, t: 100 * ok - 0.5 * t / 1000
def L(tag, arm):
    return {x["id"]: x for n in (5, 7, 9) for x in map(json.loads, open(f"results/futo_{tag}_{arm}_s1_test_{n}.jsonl"))}
for main in sys.argv[1:]:
    trc, trct = L(main, "trc"), L(main, "trct"); TH = {s: L(main + s, "think") for s in (("",) if main == "q32" else ("M", "H"))}
    for s, T in TH.items():
        print(f"{main} thinking-{s}: {sum(r['exact'] for r in T.values())/len(T):.1%} at {sum(r['tokens'] for r in T.values())/len(T)/1000:.1f}k, capped {sum(r['finish']=='length' for r in T.values())}, utility {sum(U(r['exact'], r['tokens']) for r in T.values())/len(T):.1f}")
    best = max(TH, key=lambda s: sum(U(r["exact"], r["tokens"]) for r in TH[s].values()))
    T = TH[best]; d = []; byn = defaultdict(lambda: [0, 0, 0]); lad_ok = lad_tok = 0
    for i, t in T.items():
        tok, got = 0, None
        for r in (trc[i], trct[i]):
            tok += r["tokens"]
            if r["count"] == 1 and r["ans"]:
                got = r; break
        ok = got["exact"] if got else t["exact"]; tok += 0 if got else t["tokens"]
        d.append(U(ok, tok) - U(t["exact"], t["tokens"])); lad_ok += ok; lad_tok += tok
        b = byn[t["n"]]; b[0] += 1; b[1] += ok; b[2] += t["exact"]
    n = len(d); random.seed(0); bs = sorted(sum(random.choice(d) for _ in range(n)) / n for _ in range(4000))
    print(f"{main}: baseline thinking-{best}; ladder {lad_ok/n:.1%} at {lad_tok/n/1000:.1f}k | measured accuracy term {100*(lad_ok - sum(r['exact'] for r in T.values()))/n:+.1f} | dU {sum(d)/n:+.1f} [{bs[100]:+.1f}, {bs[3899]:+.1f}]")
    print("   by size: " + "; ".join(f"{k}x{k}: ladder {v[1]}/{v[0]}, thinking {v[2]}/{v[0]}" for k, v in sorted(byn.items())))
