"""PF (docs/prereg/PREREG_PROOF.md, addendum): the recipe on miniF2F where the check (the Lean compiler) is sound. From the stored phase-1
attempts (8 per statement and mode), per model: CHEAP×k, THINK×j and FF(a, j) = up to a cheap attempts, then up to j thinking attempts,
each stopping at the first attempt that compiles; attempts in a random order, averaged over 200 orders; tokens = all attempts made.
usage: python analyze_pf.py"""
import json, os, random
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
    for name, c, th in PAIRS:
        C, T = load(c), load(th); names = sorted(set(C) & set(T)); n_ord = 200
        res = defaultdict(lambda: [0.0, 0.0])
        for _ in range(n_ord):
            for s in names:
                cs, ts = rng.sample(C[s], len(C[s])), rng.sample(T[s], len(T[s]))
                for a in range(9):
                    for j in range(9):
                        if a == 0 and j == 0:
                            continue
                        ok, tk = run(cs[:a] + ts[:j])
                        res[(a, j)][0] += ok / n_ord; res[(a, j)][1] += tk / n_ord
        th8 = res[(0, 8)]; ch8 = res[(8, 0)]
        print(f"=== {name} ({len(names)} statements): CHEAP×8 {ch8[0]:.1f} solved @ {ch8[1] / len(names) / 1000:.2f}k | THINK×8 {th8[0]:.1f} @ "
              f"{th8[1] / len(names) / 1000:.2f}k | FF(1,8) {res[(1, 8)][0]:.1f} @ {res[(1, 8)][1] / len(names) / 1000:.2f}k "
              f"({100 * res[(1, 8)][1] / th8[1]:.0f}% of THINK×8) | FF(8,8) {res[(8, 8)][0]:.1f} @ {res[(8, 8)][1] / len(names) / 1000:.2f}k")
        best = max(((v[0], k) for k, v in res.items() if v[1] <= th8[1]), key=lambda x: x[0])
        print(f"  best within THINK×8's budget: FF{best[1]} {best[0]:.1f} solved ({best[0] - th8[0]:+.1f}) @ {res[best[1]][1] / len(names) / 1000:.2f}k")
        for budget in (2, 4, 8, 16, 32):   # the frontier: best solved at <= budget k tokens per statement
            cand = [(v[0], k, v[1]) for k, v in res.items() if v[1] / len(names) / 1000 <= budget]
            if cand:
                b = max(cand)
                print(f"  ≤ {budget:2d}k tokens/statement: best {b[0]:.1f} solved with {'CHEAP×%d' % b[1][0] if b[1][1] == 0 else 'THINK×%d' % b[1][1] if b[1][0] == 0 else 'FF%s' % (b[1],)}")


if __name__ == "__main__":
    main()
