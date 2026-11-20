"""Word-problem claim list with one Holm correction (CRITIQUE PLAN P4, 2026-11-20). Each claim is a held-out-problem test of utility at
rate 0.5 (paired by problem x seed, 3 seeds), pool-free own programs (analyze_frontier --nopool), one-sided H1: method better.
  W1 full - cascade, MAMO ComplexLP (SIRL-corrected labels)            Qwen3-8B, gpt-oss-20b
  W2 full - thinking, five held-out sets pooled                          Qwen3-8B, gpt-oss-20b
  W3 full - LLMOPT-14B (official checkpoint), each held-out set          Qwen3-8B, gpt-oss-20b   (when results/x3/llmopt_llm14_s*.jsonl exist)
  W4 typed -> own - own, unseen OptMATH (93)                              Qwen3-8B, gpt-oss-20b
p = share of cluster-bootstrap means <= 0 (one-sided; problems resampled with their seeds); Holm over every claim present.  usage: python3 poc/analyze_claims.py [--boot 4000]
"""
import json
import os
import sys

import numpy as np

sys.argv = [sys.argv[0], "--nopool"] + sys.argv[1:]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_frontier as F  # noqa: E402

BOOT = int(sys.argv[sys.argv.index("--boot") + 1]) if "--boot" in sys.argv else 4000


def test(d):
    """cluster bootstrap over problems (the 3 seeds of a problem are resampled together; rows are (problem id, value))"""
    by = {}
    for i, v in d:
        by.setdefault(i, []).append(v)
    S = np.array([sum(v) for v in by.values()], float); N = np.array([len(v) for v in by.values()], float)
    rng = np.random.default_rng(0); ix = rng.integers(0, len(S), (BOOT, len(S)))
    bs = S[ix].sum(1) / N[ix].sum(1)
    return S.sum() / N.sum(), np.quantile(bs, 0.025), np.quantile(bs, 0.975), max((bs <= 0).mean(), 1 / BOOT)


def llmopt():
    R = F.load(f"{F.X3}/llmopt_llm14_s{{s}}.jsonl")
    R.update(F.load(f"{F.X3}/llmopt_llm14_rerun_s{{s}}.jsonl"))   # rows rerun after the 11-21 18:36 sandbox change replace the originals
    out = {}
    for k, r in R.items():
        g = F.gold_of(k[0], r["gold"])
        if g is not None:
            out[k] = (F.correct(r["pred"], g), r["tokens"], r["tokens"] * 14 / 8, r.get("in_tokens", 0))
    return out


def main():
    claims = []
    L = llmopt()
    for m in ("q8b", "oss20"):
        u = lambda x: F.util(x, 0.5, "out")
        rows = F.items(m, "mamo_complex")
        claims.append((f"W1 {m} full - cascade, MAMO ComplexLP", [(k[0], u(a["T>CASC"]) - u(a["CASC"])) for k, _, a in rows if "T>CASC" in a]))
        pooled = [r for st in ("x3", "optmath", "optibench", "bwor", "logior") for r in F.items(m, st)]
        claims.append((f"W2 {m} full - thinking, held-out pooled", [(k[0], u(a["T>CASC"]) - u(a["THINK"])) for k, _, a in pooled if "T>CASC" in a]))
        if L:
            for st in ("x3", "optmath", "optibench", "bwor", "logior"):
                d = [(k[0], u(a["T>CASC"]) - u(L[k])) for k, _, a in F.items(m, st) if "T>CASC" in a and k in L]
                if d:
                    claims.append((f"W3 {m} full - LLMOPT-14B, {st}", d))
        for st in ("optibench",):   # addendum J-1: full method with the repair turn vs LLMOPT
            d = [(k[0], u(a["T>CASCR"]) - u(L[k])) for k, _, a in F.items(m, st) if "T>CASCR" in a and k in L]
            if d and L:
                claims.append((f"J-1 {m} full+repair - LLMOPT-14B, {st}", d))
        d = [(k[0], u(a["T>CASCR"]) - u(a["T>CASC"])) for k, _, a in pooled if "T>CASCR" in a]
        if d:
            claims.append((f"J-2 {m} full+repair - full, held-out pooled", d))
        rows = F.items(m, "optnew")
        claims.append((f"W4 {m} typed>own - own, unseen OptMATH", [(k[0], u(a["T>OWN"]) - u(a["OWN"])) for k, _, a in rows]))
    for fam, sel in (("W (report claims)", lambda n: not n.startswith("J-")), ("J (PREREG_TYPED addendum J)", lambda n: n.startswith("J-"))):
        res = [(name, len(d)) + test(d) for name, d in claims if sel(name)]
        if not res:
            continue
        order = sorted(range(len(res)), key=lambda i: res[i][5]); n = len(res); adj = [0.0] * n; run = 0.0
        for r, i in enumerate(order):   # Holm step-down within the family
            run = max(run, min(1.0, (n - r) * res[i][5])); adj[i] = run
        print(f"{fam}: {n} claims, Holm-adjusted one-sided p (utility at rate 0.5, pool-free own programs)")
        for (name, k, mu, lo, hi, p), pa in zip(res, adj):
            print(f"  {name:45s} n={k:5d} {mu:+6.1f} [{lo:+6.1f}, {hi:+6.1f}]  p={p:.4f}  Holm p={pa:.4f}  {'HOLDS' if pa < 0.05 else 'not shown'}")

if __name__ == "__main__":
    main()
