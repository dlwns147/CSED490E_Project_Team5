"""U1-MINED (docs/prereg/PREREG_U1.md): optimization suite, X-first-then-think for X = hand-written fact, retrieved documentation
(DECOR arm = BM25 top-3), mined fact (the model's own feasible program for the most similar other problem type). Cure seeds 1-3."""
import json, os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_argv, sys.argv = sys.argv, sys.argv[:1]
import analyze_u1 as U  # noqa: E402
sys.argv = _argv


def rows(m, arm):
    f = f"{U.RES}/co_S2_U1_{m}_co_{arm}.jsonl"
    return {r["key"]: r for r in map(json.loads, open(f))} if os.path.exists(f) else None


for m in sys.argv[1:] or ["q32b", "q8b", "q36"]:
    print(f"=== {m} (optimization suite, 100 items per cure seed)")
    for sd in (1, 2, 3):
        T = rows("q36d" if m == "q36" else m, f"think_s{sd}")
        out = []; byprob = defaultdict(lambda: defaultdict(int))
        for name, arm in (("hand fact", f"fact_s{sd}"), ("retrieved", f"decor_s{sd}"), ("mined", f"mined_s{sd}")):
            C = rows(m, arm)
            if not (C and T):
                out.append(f"{name} missing"); continue
            ks = [k for k in C if k in T]
            a = sum(U.ok("co", C[k]) for k in ks); ff = ft = 0
            for k in ks:
                p = U.check("co", C[k]); ff += U.ok("co", C[k]) if p else U.ok("co", T[k])
                ft += (C[k].get("out_tokens") or 0) + (0 if p else (T[k].get("out_tokens") or 0))
                byprob[k.rsplit("-", 2)[0]][name] += U.ok("co", C[k])
            out.append(f"{name}: alone {100 * a / len(ks):.0f}%, first-then-think {100 * ff / len(ks):.0f}% @ {ft / len(ks) / 1000:.1f}k")
        print(f"  cure s{sd}: " + " | ".join(out))
        if sd == 1:
            print("    alone, by problem (hand / retrieved / mined):", {p: f"{v['hand fact']}/{v['retrieved']}/{v['mined']}" for p, v in byprob.items()})
