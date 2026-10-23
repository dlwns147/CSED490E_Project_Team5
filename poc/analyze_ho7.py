"""HO7 (docs/prereg/PREREG_HO.md): one cheap repair on a visible failure, no checker. Per model: OptiBench (cheap arm formx, the label-free
library) and OptMATH (cheap arm free). FF (think on a visible failure), FF-R0 (on a visible failure, the repaired program if it runs and
prints a value, else think), THINK (thinkfree rows); seed means, paired bootstrap 95% intervals over problems, token shares.
HO-N3 (PREREG_HON.md): HO7_CELLS=optibench:formx,bwor:formx,logior:formx,optmath:formx python analyze_ho7.py q35 (+ FF-R0 - FF).
usage: python analyze_ho7.py [model ...]"""
import os, random, sys
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
        cells = [tuple(c.split(":")) for c in os.environ.get("HO7_CELLS", "optibench:formx,optmath:free").split(",")]
        for bench, arm in cells:
            per, tok, st = {}, Counter(), Counter()
            for s in (1, 2, 3):
                F = {r["id"]: r for r in _rows(f"{RES}/opt_{m}_{bench}_{arm}_s{s}.jsonl")}
                R = {r["id"]: r for r in _rows(f"{RES}/repair_{m}_{bench}_{arm}_s{s}.jsonl")}
                T = {r["id"]: r for r in _rows(f"{RES}/opt_{m}_{bench}_thinkfree_s{s}.jsonl")}
                for i, f in F.items():
                    if i not in T:
                        continue
                    t, rp = T[i], R.get(i); vis = not ok_(f); use_r = vis and bool(rp and ok_(rp))
                    tf, tt, tr = f.get("out_tokens") or 0, t.get("out_tokens") or 0, (rp or {}).get("out_tokens") or 0
                    ff = t["correct"] if vis else f["correct"]; ffr = (rp["correct"] if use_r else t["correct"]) if vis else f["correct"]
                    per.setdefault(i, []).append((ff - t["correct"], ffr - t["correct"], ff, ffr, t["correct"]))
                    tok["FF"] += tf + (tt if vis else 0); tok["FF-R0"] += tf + (tr if vis else 0) + (tt if vis and not use_r else 0); tok["THINK"] += tt
                    tok["n"] += 1
                    if vis:
                        st["vis"] += 1; st["rep"] += bool(rp); st["runs"] += use_r; st["right"] += bool(use_r and rp["correct"]); st["think_right"] += bool(use_r and t["correct"])
            if not per:
                print(f"=== {m} {bench}: no rows"); continue
            n = tok["n"]
            acc = {k: 100 * sum(x[j] for v in per.values() for x in v) / n for j, k in ((2, "FF"), (3, "FF-R0"), (4, "THINK"))}
            print(f"=== {m} {bench} ({arm}): " + " | ".join(f"{k} {acc[k]:.1f}% @ {tok[k] / n / 1000:.2f}k ({100 * tok[k] / tok['THINK']:.0f}%)" for k in ("FF", "FF-R0", "THINK"))
                  + f" | FF-R0 tokens = {100 * tok['FF-R0'] / max(1, tok['FF']):.0f}% of FF's")
            for j, k in ((0, "FF"), (1, "FF-R0")):
                mu, lo, hi = ci({i: sum(x[j] for x in v) / len(v) for i, v in per.items()})
                print(f"  {k} - THINK {mu:+.1f} [{lo:+.1f}, {hi:+.1f}]")
            mu, lo, hi = ci({i: sum(x[1] - x[0] for x in v) / len(v) for i, v in per.items()})
            print(f"  FF-R0 - FF {mu:+.1f} [{lo:+.1f}, {hi:+.1f}]")
            print(f"  visible failures {st['vis']}, repaired program runs {st['runs']} ({100 * st['runs'] / max(1, st['vis']):.0f}%), right {st['right']} "
                  f"(thinking right on the same items {st['think_right']})")


if __name__ == "__main__":
    main()
