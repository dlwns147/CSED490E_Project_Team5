"""PREREG_ADJ (2026-11-22): the escalation's thinking call gets the two disagreeing programs as evidence (SOL-2) — on top of
PREREG_ESCT's final method (Qwen3-8B: hand-off retry to gpt-oss-20b; gpt-oss-20b: own retry). Held-out pool, utility at rate 0.5 (output
tokens), clustered by problem, Holm over the two models. usage: [OR_CLEAN=1] python3 poc/analyze_adj.py"""
import os
import sys

sys.argv = [sys.argv[0], "--nopool"] + sys.argv[1:]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_claims as C  # noqa: E402
import analyze_frontier as F  # noqa: E402

SETS = ("x3", "optmath", "optibench", "bwor", "logior")
FINAL = {"q8b": "T>CASCR+RX", "oss20": "T>CASCR+RS"}
u = lambda x: F.util(x, 0.5, "out")


def rows(m, adj):
    os.environ.pop("SOL2_ADJ", None)
    if adj:
        os.environ["SOL2_ADJ"] = "1"
    return {k: a[FINAL[m]] for st in SETS for k, _, a in F.items(m, st) if FINAL[m] in a}


def main():
    print(f"labels: {'expert-audited' if F.CLEAN else 'raw'}")
    tests = []
    for m in ("q8b", "oss20"):
        B, A = rows(m, False), rows(m, True)
        ks = sorted(set(A) & set(B)); n = len(ks)
        for nm, R in (("ESCT final", B), ("ADJ final", A)):
            print(f"  {m:5s} {nm:11s} {100 * sum(R[k][0] for k in ks) / n:5.1f}% @ {sum(R[k][1] for k in ks) / n / 1000:5.2f}k  (n={n})")
        tests.append((f"ADJ-{m} ADJ - ESCT", [(k[0], u(A[k]) - u(B[k])) for k in ks]))
    res = [(k,) + C.test(dd) for k, dd in tests]
    order = sorted(range(len(res)), key=lambda i: res[i][4]); adj = [0.0] * len(res); run = 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (len(res) - r) * res[i][4])); adj[i] = run
    for (k, mu, lo, hi, p), pa in zip(res, adj):
        print(f"  {k:22s} {mu:+6.2f} [{lo:+6.2f}, {hi:+6.2f}]  Holm p={pa:.4f}  {'HOLDS' if pa < 0.05 else 'not shown'}")


if __name__ == "__main__":
    main()
