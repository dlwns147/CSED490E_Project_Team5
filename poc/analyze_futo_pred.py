# Committed copy of results/tmp_futo_pred.py (CRITIQUE PLAN P5, 2026-11-20); run from the repo root: python3 poc/analyze_futo_pred.py <model tags>
"""PREREG_FUTO F-2: blind hybrid estimate of each ladder's accuracy term, against both thinking settings (medium M, high H); reads only id,
count, ans, tokens (`exact` dropped). Ladder: trc -> trct -> think, accept at count 1. Third: the other gpt-oss model's trc (count 1)."""
import json, sys
def L(tag, arm):
    out = {}
    for n in (5, 7, 9):
        for l in open(f"results/futo_{tag}_{arm}_s1_test_{n}.jsonl"):
            x = json.loads(l); out[x["id"]] = {k: x.get(k) for k in ("id", "n", "count", "ans", "tokens")}
    return out
key = lambda g: json.dumps(g) if g else None
for main, third in [(m, {"oss20": "oss120", "oss120": "oss20", "q32": "oss20"}[m]) for m in sys.argv[1:]]:
    trc, trct, X = L(main, "trc"), L(main, "trct"), L(third, "trc")
    for tset in (("",) if main == "q32" else ("M", "H")):
        T = L(main + tset, "think"); n = len(T); acc = cov = 0; H = A = dt = 0.0
        for i, th in T.items():
            tok, got = 0, None
            for r in (trc[i], trct[i]):
                tok += r["tokens"]
                if r["count"] == 1 and r["ans"]:
                    got = r; break
            dt += (tok + (0 if got else th["tokens"]) - th["tokens"]) / 1000
            if not got: continue
            acc += 1; a, t = key(got["ans"]), key(th["ans"]); x = X[i]; xp = key(x["ans"]) if x["count"] == 1 else None
            A += t != a
            if xp: cov += 1; H += (a == xp) - (t == xp)
            else: H += t != a
        print(f"{main} vs thinking-{tset}: accepted {acc/n:.2f}, third covers {cov/max(1,acc):.0%} | predicted accuracy term {100*H/n:+.1f} (rule A {100*A/n:+.1f}) | token term {-0.5*dt/n:+.2f}")
