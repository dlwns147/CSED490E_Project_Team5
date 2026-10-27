"""HO-32 (docs/prereg/PREREG_HO.md, addendum): the final recipe on a larger hybrid model (Qwen3-32B-AWQ, tag q32b). Per held-out word
benchmark (OptiBench on the HO-TF third), seeds 1-3, the six check-matched policies of HO-CM (tokens of every step counted; a visible
failure = no value, crash or 'No Best Solution'):
  T (one think, formxt), T->T (on T's visible failure, the next seed's think), FF+F (library program, think on its visible failure),
  SB+F (2,000-token think first, formxtb2000), SB->T->T, FF+SB+F; utility = accuracy - 0.5 x ktokens per problem.
32-P1: SB->T->T within 1.0 utility point of the best of the six in >= 3 of the 4 cells. 32-P2: T->T - T >= +2 points in >= 3 of 4.
32-P3 (label-free signal): pooled over the cells, passing library programs whose value matches the same seed's passing short-think
program are right >= 30 points more often than those that print a different value (also shown: the short think fails visibly).
HO-SEED: --native = the short think is the model's own trained budget (formxnb2048) instead of the forced cut (formxtb2000).
HO-4K (PREREG_HO.md): --b4k = per cell, SB->T->T with a 4,000-token first think (formxtb4000) against the 2,000-token one (formxtb2000),
same T / T2 rows: utility gap, paired accuracy difference (95% CI over problems), tokens, and how often the short think fails visibly.
usage: python analyze_ho32.py [--native | --b4k] [model ...]   (default q32b)"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_ho3 import ci, ok_  # noqa: E402
from run_nlopt import RES, _rows, correct  # noqa: E402

g = lambda r: r.get("out_tokens") or 0
POL = ("T", "T->T", "FF+F", "SB+F", "SB->T->T", "FF+SB+F")
LAM = 0.5
SB_ARM = "formxnb2048" if "--native" in sys.argv else "formxtb2000"


def cell(m, b):
    per, tok, n, agree, diag = {}, dict.fromkeys(POL, 0), 0, [], []
    for s in (1, 2, 3):
        F, S, T, T2 = ({r["id"]: r for r in _rows(f"{RES}/opt_{m}_{b}_{a}_s{x}.jsonl")}
                       for a, x in (("formx", s), (SB_ARM, s), ("formxt", s), ("formxt", s % 3 + 1)))
        for i, f in F.items():   # 32-P3 uses the two cheap arms only
            if ok_(f) and i in S:
                sb = S[i]
                agree.append((bool(f["correct"]), "fails" if not ok_(sb) else "agree" if correct(f["pred"], str(sb["pred"])) else "differs"))
        for i, t in T.items():
            if i not in F or i not in S or i not in T2:
                continue
            f, sb, t2 = F[i], S[i], T2[i]; n += 1
            diag.append(((sb.get("think_tokens") or 0) > 2048, t.get("finish") == "length", not ok_(sb)))
            tt = (t["correct"], g(t)) if ok_(t) else (t2["correct"], g(t) + g(t2))
            res = {"T": (t["correct"], g(t)), "T->T": tt,
                   "FF+F": (f["correct"], g(f)) if ok_(f) else (t["correct"], g(f) + g(t)),
                   "SB+F": (sb["correct"], g(sb)) if ok_(sb) else (t["correct"], g(sb) + g(t)),
                   "SB->T->T": (sb["correct"], g(sb)) if ok_(sb) else (tt[0], g(sb) + tt[1]),
                   "FF+SB+F": (f["correct"], g(f)) if ok_(f) else (sb["correct"], g(f) + g(sb)) if ok_(sb) else (t["correct"], g(f) + g(sb) + g(t))}
            per.setdefault(i, []).append({k: bool(v[0]) for k, v in res.items()})
            for k, v in res.items():
                tok[k] += v[1]
    return per, tok, n, agree, diag


def b4k(models):
    global SB_ARM
    p1 = p3 = cells = 0; gains = []
    for m in models:
        for b in ("optibench", "bwor", "logior", "optmath"):
            R = {}
            for B in (2000, 4000):
                SB_ARM = f"formxtb{B}"; R[B] = cell(m, b)
            (per2, tok2, n2, _, d2), (per4, tok4, n4, _, d4) = R[2000], R[4000]
            if not n2 or n2 != n4:
                print(f"=== {m} {b}: rows 2k {n2} / 4k {n4}, skipped"); continue
            cells += 1
            u = {B: 100 * sum(x["SB->T->T"] for v in P.values() for x in v) / n - LAM * T["SB->T->T"] / n / 1000
                 for B, (P, T, n) in ((2000, (per2, tok2, n2)), (4000, (per4, tok4, n4)))}
            mu, lo, hi = ci({i: sum(y["SB->T->T"] - x["SB->T->T"] for x, y in zip(per2[i], per4[i])) / len(per2[i]) for i in per2})
            esc = {B: 100 * sum(d[2] for d in D) / len(D) for B, D in ((2000, d2), (4000, d4))}
            gains.append(u[4000] - u[2000]); p1 += u[4000] >= u[2000]; p3 += esc[4000] < esc[2000]
            print(f"=== {m} {b} ({len(per2)} problems, {n2} rows): SB->T->T utility 2k {u[2000]:.1f} / 4k {u[4000]:.1f} ({u[4000] - u[2000]:+.2f}); "
                  f"accuracy 4k - 2k {mu:+.1f} [{lo:+.1f}, {hi:+.1f}]; tokens 4k {tok4['SB->T->T'] / n4 / 1000:.2f}k / 2k {tok2['SB->T->T'] / n2 / 1000:.2f}k "
                  f"({100 * tok4['SB->T->T'] / tok2['SB->T->T']:.0f}%); short think fails visibly 2k {esc[2000]:.1f}% / 4k {esc[4000]:.1f}%")
    print(f"*** 4K-P1 mean utility gain {sum(gains) / max(1, len(gains)):+.2f}; 4K-P2 {p1}/{cells} cells with 4k utility >= 2k; "
          f"4K-P3 {p3}/{cells} cells where the 4k think fails visibly less often")


def main():
    if "--b4k" in sys.argv:
        return b4k([a for a in sys.argv[1:] if not a.startswith("--")] or ["q14a", "q35", "q32b"])
    for m in [a for a in sys.argv[1:] if not a.startswith("--")] or ["q32b"]:
        p1 = p2 = cells = 0; pooled = []
        for b in ("optibench", "bwor", "logior", "optmath"):
            per, tok, n, agree, diag = cell(m, b)
            pooled += agree
            if not n:
                print(f"=== {m} {b}: no rows"); continue
            cells += 1
            acc = {k: 100 * sum(x[k] for v in per.values() for x in v) / n for k in POL}
            kt = {k: tok[k] / n / 1000 for k in POL}
            u = {k: acc[k] - LAM * kt[k] for k in POL}
            best = max(u, key=u.get)
            print(f"=== {m} {b} ({len(per)} problems, {n} rows; best utility {best} {u[best]:.1f}; short think past 2,048 tokens "
                  f"{100 * sum(d[0] for d in diag) / n:.0f}%, full think at its cap {100 * sum(d[1] for d in diag) / n:.0f}%)")
            print("  " + " | ".join(f"{k} {acc[k]:.1f}% @ {kt[k]:.2f}k u {u[k]:.1f}" for k in POL))
            mu, lo, hi = ci({i: sum(x["T->T"] - x["T"] for x in v) / len(v) for i, v in per.items()})
            print(f"  32-P1 SB->T->T utility gap to the best {u['SB->T->T'] - u[best]:+.2f}; 32-P2 T->T - T {mu:+.1f} [{lo:+.1f}, {hi:+.1f}]")
            for k in ("FF+F", "SB+F", "SB->T->T", "FF+SB+F"):
                mu_, lo_, hi_ = ci({i: sum(x[k] - x["T->T"] for x in v) / len(v) for i, v in per.items()})
                print(f"  {k} - T->T {mu_:+.1f} [{lo_:+.1f}, {hi_:+.1f}] at {100 * tok[k] / tok['T->T']:.0f}% of its tokens")
            p1 += u["SB->T->T"] >= u[best] - 1.0; p2 += mu >= 2.0
            right = {c: [r for r, k in agree if k == c] for c in ("agree", "differs", "fails")}
            print("  agreement (this cell): " + ", ".join(f"{c} {100 * sum(v) / max(1, len(v)):.0f}% right (n={len(v)})" for c, v in right.items()))
        right = {c: [r for r, k in pooled if k == c] for c in ("agree", "differs", "fails")}
        pct = {c: 100 * sum(v) / max(1, len(v)) for c, v in right.items()}
        dis = right["differs"] + right["fails"]
        print(f"*** {m}: 32-P1 {p1}/{cells} cells; 32-P2 {p2}/{cells} cells; 32-P3 pooled: agree {pct['agree']:.1f}% (n={len(right['agree'])}) vs "
              f"differ {pct['differs']:.1f}% (n={len(right['differs'])}) -> gap {pct['agree'] - pct['differs']:+.1f}; "
              f"vs differ or short think fails {100 * sum(dis) / max(1, len(dis)):.1f}% (n={len(dis)}); short think fails {pct['fails']:.1f}% (n={len(right['fails'])})")


if __name__ == "__main__":
    main()
