"""PREREG_SPEC (2026-11-21): check-and-escalate on top of a specialist (LLMOPT-14B), offline on stored rows.
SPEC = LLMOPT alone; FULL = our method for gpt-oss-20b (T>CASCR); SPEC+C = LLMOPT's answer kept when gpt-oss-20b's quick program prints the
same value, else gpt-oss-20b thinking; SPEC+C8 = the same with Qwen3-8B as check and escalation. Utility at rate 0.5 (and a sensitivity
grid), clustered bootstrap by problem, Holm over S-1 (both checkers) and S-2.
usage: [OR_CLEAN=1] python3 poc/analyze_spec.py"""
import os
import sys

sys.argv = [sys.argv[0], "--nopool"] + sys.argv[1:]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_claims as C  # noqa: E402
import analyze_frontier as F  # noqa: E402

SETS = ("x3", "optmath", "optibench", "bwor", "logior")


def rows(checker):
    """per (problem, seed): {arm: (right, out_tokens, size_tokens, input_tokens)} with the checker model's quick program and thinking"""
    R = F.load(f"{F.X3}/llmopt_llm14_s{{s}}.jsonl"); R.update(F.load(f"{F.X3}/llmopt_llm14_rerun_s{{s}}.jsonl"))
    w = F.ACTIVE[checker] / 8; ws = 14 / 8
    out = []
    for st in SETS:
        ft, fo, fk = F.files(checker, st)
        O, K = F.load(fo, {st}), F.load(fk, {st})
        full = {k: a for k, _, a in F.items("oss20", st)}
        for k, r in R.items():
            if F.setof(k[0]) != st or k not in O or k not in K or k not in full or "T>CASCR" not in full[k]:
                continue
            g = F.gold_of(k[0], r["gold"])
            if g is None:
                continue
            lt, ot, th = r["tokens"], O[k]["out_tokens"], K[k]["out_tokens"]
            a = {"SPEC": (F.correct(r["pred"], g), lt, lt * ws, F.qtok(k[0]) * max(1, len(r.get("rounds") or [1]))),
                 "FULL": full[k]["T>CASCR"]}
            acc = r["pred"] not in (None, "NBS") and F.agree(r["pred"], O[k]["pred"])
            ok = F.correct(r["pred"], g) if acc else F.correct(K[k]["pred"], g)
            a["SPEC+C"] = (ok, lt + ot + (0 if acc else th), lt * ws + (ot + (0 if acc else th)) * w, a["SPEC"][3] + F.qtok(k[0]) * (1 if acc else 2))
            a["accepted"] = acc
            out.append((k, st, a))
    return out


def main():
    u = lambda x, r=0.5, v="out": F.util(x, r, v)
    print(f"labels: {'expert-audited (OR_CLEAN=1)' if F.CLEAN else 'raw'}")
    claims = []
    for chk, name in (("oss20", "SPEC+C"), ("q8b", "SPEC+C8")):
        X = rows(chk); n = len(X)
        acc = lambda arm: 100 * sum(a[arm][0] for _, _, a in X) / n
        kt = lambda arm: sum(a[arm][1] for _, _, a in X) / n / 1000
        print(f"\n== checker {chk} ({name}), held-out pool n={n}: accepted {100 * sum(a['accepted'] for _, _, a in X) / n:.0f}%")
        for arm in ("SPEC", "SPEC+C", "FULL"):
            print(f"   {arm if arm != 'SPEC+C' else name:8s} {acc(arm):5.1f}% @ {kt(arm):5.2f}k  U {sum(u(a[arm]) for _, _, a in X) / n:6.1f}")
        claims.append((f"S-1 {name} - SPEC", [(k[0], u(a["SPEC+C"]) - u(a["SPEC"])) for k, _, a in X]))
        if chk == "oss20":
            claims.append((f"S-2 {name} - FULL (gpt-oss-20b)", [(k[0], u(a["SPEC+C"]) - u(a["FULL"])) for k, _, a in X]))
        for st in SETS:
            d = [(k[0], u(a["SPEC+C"]) - u(a["SPEC"])) for k, s, a in X if s == st]
            mu, lo, hi, _ = C.test(d)
            print(f"   S-3 {st:9s} {name} - SPEC {mu:+5.1f} [{lo:+5.1f}, {hi:+5.1f}]  (n={len(d)})")
        sens = []
        for v in ("out", "size", "in+out"):
            for r in (0.25, 1.0, 2.0):
                mu, lo, hi, _ = C.test([(k[0], u(a["SPEC+C"], r, v) - u(a["SPEC"], r, v)) for k, _, a in X])
                sens.append(f"{v}@{r}:{mu:+.1f}[{lo:+.1f},{hi:+.1f}]")
        print("   sensitivity S-1: " + " ".join(sens))
    res = [(nm, len(d)) + C.test(d) for nm, d in claims]
    order = sorted(range(len(res)), key=lambda i: res[i][5]); n = len(res); adj = [0.0] * n; run = 0.0
    for r_, i in enumerate(order):
        run = max(run, min(1.0, (n - r_) * res[i][5])); adj[i] = run
    print("\nregistered tests (one-sided, Holm):")
    for (nm, k, mu, lo, hi, p), pa in zip(res, adj):
        print(f"  {nm:32s} n={k:5d} {mu:+6.1f} [{lo:+6.1f}, {hi:+6.1f}]  Holm p={pa:.4f}  {'HOLDS' if pa < 0.05 else 'not shown'}")


if __name__ == "__main__":
    main()
