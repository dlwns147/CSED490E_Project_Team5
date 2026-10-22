"""HO-G-R (docs/prereg/PREREG_HOGC.md, addendum): one cheap repair on a visible failure, before thinking, on held-out geometry.
FF (fact; think if it fails the free check), FF-RG (else the repaired program if it passes the same check, else think), THINK; seed means,
paired bootstrap 95% intervals over the 96 items, output tokens (fact + repair where written + thinking where escalated).
usage: python analyze_hogr.py [model ...]   (reads results/n10_check_cache.json; run where the cache is current)"""
import json, os, random, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_n10 as N  # noqa: E402

RES = N.RES
ok = lambda r: r["class"] == "correct_all"
tok = lambda r: (r.get("out_tokens") or 0) + (r.get("think_tokens") or 0)
key = lambda r: (r["task"], r["n"], r["inst"])


def main():
    for m in sys.argv[1:] or ["oss20", "q14a", "q8b"]:
        per, t, st = {}, Counter(), Counter()
        for s in (1, 2, 3):
            F = {key(r): r for r in map(json.loads, open(f"{RES}/geocross_S2_HOG_{m}_geo_fact_s{s}.jsonl"))}
            T = {key(r): r for r in map(json.loads, open(f"{RES}/geocross_S2_HOG_{m}_geo_think_s{s}.jsonl"))}
            p = f"{RES}/georepair_{m}_s{s}.jsonl"
            R = {key(r): r for r in map(json.loads, open(p))} if os.path.exists(p) else {}
            for k, f in F.items():
                th = T[k]; passes = N.geo_check(f)[0]; rp = R.get(k); use = (not passes) and bool(rp and rp["passes_check"])
                ff = ok(f) if passes else ok(th); fr = ok(f) if passes else (ok(rp) if use else ok(th))
                per.setdefault(k, []).append((ff - ok(th), fr - ok(th), ff, fr, ok(th)))
                t["FF"] += tok(f) + (0 if passes else tok(th)); t["THINK"] += tok(th); t["n"] += 1
                t["FF-RG"] += tok(f) + (0 if passes else (rp or {}).get("out_tokens") or 0) + (0 if passes or use else tok(th))
                if not passes:
                    st["esc"] += 1; st["rep"] += bool(rp); st["pass"] += use; st["right"] += bool(use and ok(rp)); st["think_right"] += bool(use and ok(th))
        n = t["n"]
        acc = {k: 100 * sum(x[j] for v in per.values() for x in v) / n for j, k in ((2, "FF"), (3, "FF-RG"), (4, "THINK"))}
        print(f"=== {m}: " + " | ".join(f"{k} {acc[k]:.1f}% @ {t[k] / n / 1000:.2f}k ({100 * t[k] / t['THINK']:.0f}%)" for k in ("FF", "FF-RG", "THINK"))
              + f" | FF-RG tokens = {100 * t['FF-RG'] / t['FF']:.0f}% of FF's")
        rng = random.Random(0); ids = sorted(per)
        for j, name in ((0, "FF"), (1, "FF-RG")):
            d = {i: sum(x[j] for x in per[i]) / len(per[i]) for i in ids}
            bs = sorted(sum(d[rng.choice(ids)] for _ in ids) / len(ids) for _ in range(2000))
            print(f"  {name} - THINK {100 * sum(d.values()) / len(ids):+.1f} [{100 * bs[50]:+.1f}, {100 * bs[1949]:+.1f}]")
        print(f"  escalated {st['esc']}, repaired {st['rep']}, repaired passes the check {st['pass']} ({100 * st['pass'] / max(1, st['esc']):.0f}%), "
              f"right {st['right']} (thinking right on those items {st['think_right']})")


if __name__ == "__main__":
    main()
