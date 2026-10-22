"""HO6 (docs/prereg/PREREG_HO.md): one cheap repair before thinking. Per model and benchmark (BWOR, LogiOR), seed means:
FF-V (HO3: freev if it passes the free check and the checker, else THINK) and FF-R (else the repaired program if it runs and prints a value,
else THINK), vs THINK (stored thinkfree rows); paired bootstrap 95% intervals over problems; tokens = freev + checker (where written) +
repair (where written) + thinking where escalated. P1 note: share of escalated items whose repair runs and prints a value, and of those right.
usage: python analyze_ho6.py [model ...]"""
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
        for bench in ("bwor", "logior"):
            per, tok, st = {}, Counter(), Counter()
            for s in (1, 2, 3):
                F = {r["id"]: r for r in _rows(f"{RES}/opt_{m}_{bench}_freev_s{s}.jsonl")}
                V = {r["id"]: r for r in _rows(f"{RES}/verify_{m}_{bench}_s{s}.jsonl")}
                Rp = {r["id"]: r for r in _rows(f"{RES}/repair_{m}_{bench}_s{s}.jsonl")}
                T = {r["id"]: r for r in _rows(f"{RES}/opt_{m}_{bench}_thinkfree_s{s}.jsonl")}
                for i, f in F.items():
                    if i not in T:
                        continue
                    t, v, rp = T[i], V.get(i), Rp.get(i)
                    keep = ok_(f) and bool(v and v["passed"])
                    tf, tt, tv, tr = f.get("out_tokens") or 0, t.get("out_tokens") or 0, (v or {}).get("out_tokens") or 0, (rp or {}).get("out_tokens") or 0
                    use_r = (not keep) and bool(rp and ok_(rp))
                    ffv = f["correct"] if keep else t["correct"]
                    ffr = f["correct"] if keep else (rp["correct"] if use_r else t["correct"])
                    per.setdefault(i, []).append((ffv - t["correct"], ffr - t["correct"], ffv, ffr, t["correct"]))
                    tok["FF-V"] += tf + tv + (0 if keep else tt); tok["THINK"] += tt; tok["n"] += 1
                    tok["FF-R"] += tf + tv + (0 if keep else tr) + (0 if keep or use_r else tt)
                    if not keep:
                        st["escalated"] += 1; st["repaired"] += bool(rp); st["runs"] += use_r; st["right"] += bool(use_r and rp["correct"])
            if not per:
                print(f"=== {m} {bench}: no rows"); continue
            n = tok["n"]
            acc = {k: 100 * sum(x[j] for v in per.values() for x in v) / n for j, k in ((2, "FF-V"), (3, "FF-R"), (4, "THINK"))}
            print(f"=== {m} {bench}: " + " | ".join(f"{k} {acc[k]:.1f}% @ {tok[k] / n / 1000:.2f}k ({100 * tok[k] / tok['THINK']:.0f}%)" for k in ("FF-V", "FF-R", "THINK")))
            for j, k in ((0, "FF-V"), (1, "FF-R")):
                mu, lo, hi = ci({i: sum(x[j] for x in v) / len(v) for i, v in per.items()})
                print(f"  {k} - THINK {mu:+.1f} [{lo:+.1f}, {hi:+.1f}]")
            print(f"  escalated {st['escalated']}, repair written {st['repaired']}, repaired program runs and prints a value {st['runs']} "
                  f"({100 * st['runs'] / max(1, st['escalated']):.0f}%), of which right {st['right']} ({100 * st['right'] / max(1, st['runs']):.0f}%)")


if __name__ == "__main__":
    main()
