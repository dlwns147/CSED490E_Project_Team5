"""Report-level standing of the final word-problem method (2026-11-22, descriptive): final arm (Qwen3-8B: ESCT hand-off + ADJ; gpt-oss-20b:
ESCT own retry) against thinking (held-out pool) and against the official LLMOPT-14B per held-out set. usage: [OR_CLEAN=1] python3 poc/analyze_final_wp.py"""
import os, sys
sys.argv = [sys.argv[0], "--nopool"]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_claims as C, analyze_frontier as F
SETS = ("x3", "optmath", "optibench", "bwor", "logior")
FINAL = {"q8b": ("T>CASCR+RX", True), "oss20": ("T>CASCR+RS", False)}
u = lambda x: F.util(x, 0.5, "out")
L = C.llmopt()
for m, (arm, adj) in FINAL.items():
    os.environ.pop("SOL2_ADJ", None)
    if adj: os.environ["SOL2_ADJ"] = "1"
    X = [(st, k, a) for st in SETS for k, _, a in F.items(m, st) if arm in a and "THINK" in a]
    n = len(X)
    fa = sum(a[arm][0] for _, _, a in X) / n * 100; ft = sum(a[arm][1] for _, _, a in X) / n / 1000
    ta = sum(a["THINK"][0] for _, _, a in X) / n * 100; tt = sum(a["THINK"][1] for _, _, a in X) / n / 1000
    d = C.test([(k[0], u(a[arm]) - u(a["THINK"])) for _, k, a in X])
    print(f"{m} {'raw' if not F.CLEAN else 'audited'}: final {fa:.1f}% @ {ft:.2f}k, thinking {ta:.1f}% @ {tt:.2f}k, final - thinking {d[0]:+.2f} [{d[1]:+.2f}, {d[2]:+.2f}] (n={n})")
    for st in SETS:
        Y = [(k, a) for s2, k, a in X if s2 == st and k in L]
        if Y:
            d = C.test([(k[0], u(a[arm]) - u(L[k])) for k, a in Y])
            print(f"   {st:9s} final - LLMOPT {d[0]:+6.2f} [{d[1]:+6.2f}, {d[2]:+6.2f}] (n={len(Y)})")
