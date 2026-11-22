"""PREREG_FRESH (2026-11-22): the final word-problem method (PREREG_ESCT) vs the official LLMOPT-14B on 300 fresh OptMATH-Train
problems (set omtf). Utility at 0.5 per ktok, clustered by problem, Holm over the two models. usage: python3 poc/analyze_fresh.py"""
import os
import sys

sys.argv = [sys.argv[0], "--nopool"] + sys.argv[1:]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_claims as C  # noqa: E402
import analyze_frontier as F  # noqa: E402

FINAL = {"q8b": "T>CASCR+RX", "oss20": "T>CASCR+RS"}
u = lambda x: F.util(x, 0.5, "out")


def llmopt():
    R = F.load(f"{F.X3}/llmopt_llm14f_s{{s}}.jsonl", {"omtf"})
    return {k: (F.correct(r["pred"], r["gold"]), r["tokens"], r["tokens"] * 14 / 8, r.get("in_tokens", 0)) for k, r in R.items()}


def main():
    L = llmopt(); tests = []
    for m in ("q8b", "oss20"):
        for adj in ((False, True) if os.environ.get("FRESH_ADJ") else (False,)):
            os.environ.pop("SOL2_ADJ", None)
            if adj:
                os.environ["SOL2_ADJ"] = "1"
            A = {k: a[FINAL[m]] for k, _, a in F.items(m, "omtf") if FINAL[m] in a}
            ks = sorted(set(A) & set(L)); n = len(ks)
            if not n:
                print(m, "no paired rows yet"); continue
            for nm, R in ((f"FULL{'+ADJ' if adj else ''}", A), ("LLMOPT", L)):
                print(f"  {m:5s} {nm:9s} {100 * sum(R[k][0] for k in ks) / n:5.1f}% @ {sum(R[k][1] for k in ks) / n / 1000:5.2f}k"
                      f"  size-cost {sum(R[k][2] for k in ks) / n / 1000:5.2f}k  (n={n})")
            d = [(k[0], u(A[k]) - u(L[k])) for k in ks]
            if adj:
                print("  ", m, "FULL+ADJ - LLMOPT (descriptive) %+.2f [%+.2f, %+.2f]" % C.test(d)[:3])
            else:
                tests.append((f"FRESH-{m} FULL - LLMOPT", d))
    res = [(k,) + C.test(dd) for k, dd in tests]
    order = sorted(range(len(res)), key=lambda i: res[i][4]); adj = [0.0] * len(res); run = 0.0
    for r, i in enumerate(order):
        run = max(run, min(1.0, (len(res) - r) * res[i][4])); adj[i] = run
    for (k, mu, lo, hi, p), pa in zip(res, adj):
        print(f"  {k:24s} {mu:+6.2f} [{lo:+6.2f}, {hi:+6.2f}]  Holm p={pa:.4f}  {'HOLDS' if pa < 0.05 else 'not shown'}")


if __name__ == "__main__":
    main()
