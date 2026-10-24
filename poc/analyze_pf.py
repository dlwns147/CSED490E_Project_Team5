"""PF (docs/prereg/PREREG_PROOF.md, addendum): the recipe on miniF2F where the check (the Lean compiler) is sound. From the stored phase-1
attempts (8 per statement and mode), per model: CHEAP×k, THINK×j and FF(a, j) = up to a cheap attempts, then up to j thinking attempts,
each stopping at the first attempt that compiles; attempts in a random order, averaged over 200 orders; tokens = all attempts made.
PL1: `python analyze_pf.py oss20:oss20_medium oss120:oss120_medium` uses every stored attempt (e.g. 32 cheap, 8 thinking; 100 orders).
usage: python analyze_pf.py [cheap_tag:think_tag ...]"""
import json, os, random, sys
from collections import defaultdict

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "x4")
PAIRS = (("gpt-oss-20b", "oss20", "oss20_medium"), ("Qwen3.6-35B-A3B", "q36", "q36_think"))


def load(tag):
    by = defaultdict(list)
    for l in open(f"{RES}/lean_{tag}_test.jsonl"):
        r = json.loads(l); by[r["name"]].append((bool(r["ok"]), r.get("out_tokens") or 0))
    return by


def run(seq):
    """attempts in order until one compiles: (solved, tokens)"""
    t = 0
    for ok, tk in seq:
        t += tk
        if ok:
            return 1, t
    return 0, t


def main():
    rng = random.Random(0)
    pairs = [(a.replace(":", " / "), *a.split(":")) for a in sys.argv[1:]] or PAIRS
    for name, c, th in pairs:
        C, T = load(c), load(th); names = sorted(set(C) & set(T)); n_ord = 200 if len(sys.argv) == 1 else 100
        nC, nT = min(len(C[s]) for s in names), min(len(T[s]) for s in names)
        res = defaultdict(lambda: [0.0, 0.0])
        for _ in range(n_ord):
            for s in names:
                cs, ts = rng.sample(C[s], nC), rng.sample(T[s], nT)
                for a in range(nC + 1):
                    for j in range(nT + 1):
                        if a == 0 and j == 0:
                            continue
                        ok, tk = run(cs[:a] + ts[:j])
                        res[(a, j)][0] += ok / n_ord; res[(a, j)][1] += tk / n_ord
        th8 = res[(0, nT)]; ch8 = res[(8, 0)]; chN = res[(nC, 0)]
        print(f"=== {name} ({len(names)} statements, {nC} cheap / {nT} thinking attempts): CHEAP×8 {ch8[0]:.1f} @ {ch8[1] / len(names) / 1000:.2f}k | "
              f"CHEAP×{nC} {chN[0]:.1f} @ {chN[1] / len(names) / 1000:.2f}k | THINK×{nT} {th8[0]:.1f} @ {th8[1] / len(names) / 1000:.2f}k | "
              f"FF(1,{nT}) {res[(1, nT)][0]:.1f} @ {res[(1, nT)][1] / len(names) / 1000:.2f}k ({100 * res[(1, nT)][1] / th8[1]:.0f}% of THINK) | "
              f"FF({nC},{nT}) {res[(nC, nT)][0]:.1f} @ {res[(nC, nT)][1] / len(names) / 1000:.2f}k")
        cheap_best = max(v[0] for k, v in res.items() if k[1] == 0 and v[1] <= th8[1])
        best = max(((v[0], k) for k, v in res.items() if v[1] <= th8[1]), key=lambda x: x[0])
        print(f"  best within THINK's budget: FF{best[1]} {best[0]:.1f} solved ({best[0] - th8[0]:+.1f} vs THINK; best cheap-only {cheap_best:.1f}) "
              f"@ {res[best[1]][1] / len(names) / 1000:.2f}k")
        for budget in (2, 4, 8, 16, 32):   # the frontier: best solved at <= budget k tokens per statement
            cand = [(v[0], k, v[1]) for k, v in res.items() if v[1] / len(names) / 1000 <= budget]
            if cand:
                b = max(cand)
                print(f"  ≤ {budget:2d}k tokens/statement: best {b[0]:.1f} solved with {'CHEAP×%d' % b[1][0] if b[1][1] == 0 else 'THINK×%d' % b[1][1] if b[1][0] == 0 else 'FF%s' % (b[1],)}")


if __name__ == "__main__":
    main()
