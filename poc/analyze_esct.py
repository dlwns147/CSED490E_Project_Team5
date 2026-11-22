"""PREREG_ESCT (2026-11-21): retry after a visibly failed think — same model (RS: its next seed's think) or the other family (RX: its
think, same seed) — on top of PREREG_TYPED J's full method. Held-out pool, utility at rate 0.5, clustered by problem, Holm over E-1, E-2,
E-3 (both directions). usage: [OR_CLEAN=1] python3 poc/analyze_esct.py"""
import os
import sys

sys.argv = [sys.argv[0], "--nopool"] + sys.argv[1:]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_claims as C  # noqa: E402
import analyze_frontier as F  # noqa: E402

SETS = ("x3", "optmath", "optibench", "bwor", "logior")
u = lambda x: F.util(x, 0.5, "out")


def main():
    print(f"labels: {'expert-audited' if F.CLEAN else 'raw'}")
    tests = []
    for m in ("q8b", "oss20"):
        X = [(k, a) for st in SETS for k, _, a in F.items(m, st) if "T>CASCR+RS" in a]
        n = len(X)
        for arm in ("T>CASCR", "T>CASCR+RS", "T>CASCR+RX"):
            print(f"  {m:5s} {arm:12s} {100 * sum(a[arm][0] for _, a in X) / n:5.1f}% @ {sum(a[arm][1] for _, a in X) / n / 1000:5.2f}k  (n={n})")
        d = lambda A, B: [(k[0], u(a[A]) - u(a[B])) for k, a in X]
        if m == "q8b":
            tests += [("E-1 q8b J+RX - J", d("T>CASCR+RX", "T>CASCR")), ("E-3 q8b J+RX - J+RS", d("T>CASCR+RX", "T>CASCR+RS"))]
        else:
            tests += [("E-2 oss20 J+RS - J", d("T>CASCR+RS", "T>CASCR")), ("E-3 oss20 J+RS - J+RX", d("T>CASCR+RS", "T>CASCR+RX"))]
    res = [(k,) + C.test(dd) for k, dd in tests]
    order = sorted(range(len(res)), key=lambda i: res[i][4]); adj = [0.0] * len(res); run = 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (len(res) - r) * res[i][4])); adj[i] = run
    for (k, mu, lo, hi, p), pa in zip(res, adj):
        print(f"  {k:24s} {mu:+6.2f} [{lo:+6.2f}, {hi:+6.2f}]  Holm p={pa:.4f}  {'HOLDS' if pa < 0.05 else 'not shown'}")


if __name__ == "__main__":
    main()
