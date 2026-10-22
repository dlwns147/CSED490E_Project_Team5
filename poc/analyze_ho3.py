"""HO3 (docs/prereg/PREREG_HO.md): a solution checker as the free check on BWOR / LogiOR. Per model and benchmark, seed means:
FF (freev program; think if it fails, prints nothing or 'No Best Solution'), FF-V (also think unless the checker written from the text
passes the printed solution; a program that prints a value but no solution gets no checker and is escalated), THINK (stored thinkfree
rows). Paired bootstrap 95% intervals over problems vs THINK; tokens = cheap program + checker (where written) + thinking where escalated.
P1 note (labels used only here): share of running-but-wrong freev programs the checker flags, and of right ones it flags.
usage: python analyze_ho3.py [model ...]"""
import json, os, random, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_nlopt import RES, _rows  # noqa: E402

ok_ = lambda r: r.get("status") == "ok" and r.get("pred") not in (None, "NBS")


def ci(d, B=2000):
    ids = sorted(d); n = len(ids); rng = random.Random(0)
    bs = sorted(sum(d[rng.choice(ids)] for _ in range(n)) / n for _ in range(B))
    return 100 * sum(d.values()) / n, 100 * bs[int(.025 * B)], 100 * bs[int(.975 * B) - 1]


def main():
    for m in sys.argv[1:] or ["oss20", "q14a", "q8b"]:
        for bench in ("bwor", "logior"):
            per, tok, flag = {}, Counter(), Counter()
            for s in (1, 2, 3):
                F = {r["id"]: r for r in _rows(f"{RES}/opt_{m}_{bench}_freev_s{s}.jsonl")}
                V = {r["id"]: r for r in _rows(f"{RES}/verify_{m}_{bench}_s{s}.jsonl")}
                T = {r["id"]: r for r in _rows(f"{RES}/opt_{m}_{bench}_thinkfree_s{s}.jsonl")}
                for i, f in F.items():
                    if i not in T:
                        continue
                    t = T[i]; v = V.get(i); runs = ok_(f); vpass = bool(runs and v and v["passed"])
                    tf, tt, tv = f.get("out_tokens") or 0, t.get("out_tokens") or 0, (v.get("out_tokens") or 0) if v else 0
                    ff = f["correct"] if runs else t["correct"]; ffv = f["correct"] if vpass else t["correct"]
                    per.setdefault(i, []).append((ff - t["correct"], ffv - t["correct"], ff, ffv, t["correct"]))
                    tok["FF"] += tf + (0 if runs else tt); tok["FF-V"] += tf + tv + (0 if vpass else tt); tok["THINK"] += tt; tok["n"] += 1
                    if runs:
                        k = "right" if f["correct"] else "wrong"
                        flag[(k, "n")] += 1; flag[(k, "flag")] += not vpass; flag[(k, "nosol")] += not f.get("solution")
            if not per:
                print(f"=== {m} {bench}: no rows yet"); continue
            n = tok["n"]
            acc = {k: 100 * sum(x[j] for v in per.values() for x in v) / n for j, k in ((2, "FF"), (3, "FF-V"), (4, "THINK"))}
            print(f"=== {m} {bench} ({len(per)} problems, {n} rows): " + " | ".join(f"{k} {acc[k]:.1f}% @ {tok[k] / n / 1000:.2f}k" for k in ("FF", "FF-V", "THINK")))
            for j, k in ((0, "FF"), (1, "FF-V")):
                mu, lo, hi = ci({i: sum(x[j] for x in v) / len(v) for i, v in per.items()})
                print(f"  {k:5s} - THINK {mu:+.1f} points, 95% CI [{lo:+.1f}, {hi:+.1f}], at {100 * tok[k] / max(1, tok['THINK']):.0f}% of THINK's tokens")
            print(f"  checker flags {flag[('wrong', 'flag')]}/{flag[('wrong', 'n')]} running-but-wrong and {flag[('right', 'flag')]}/{flag[('right', 'n')]} right "
                  f"programs (no solution printed: {flag[('wrong', 'nosol')]} / {flag[('right', 'nosol')]})")


if __name__ == "__main__":
    main()
