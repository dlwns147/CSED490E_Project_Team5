"""PL2 (docs/prereg/PREREG_PROOF.md, addendum): the 30-label pilot for the proof budget split FF(a, j) on the PL1 attempts.
usage: python analyze_pl2.py cheap_tag:think_tag ..."""
import json, os, random, sys
from collections import defaultdict

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "x4")
LAM = 0.5


def load(tag):
    by = defaultdict(list)
    for l in open(f"{RES}/lean_{tag}_test.jsonl"):
        r = json.loads(l); by[r["name"]].append((bool(r["ok"]), r.get("out_tokens") or 0))
    return by


def main():
    rng = random.Random(0)
    for pair in sys.argv[1:]:
        c, th = pair.split(":")
        C, T = load(c), load(th); names = sorted(set(C) & set(T))
        nC, nT = min(len(C[s]) for s in names), min(len(T[s]) for s in names)
        grid = [(a, j) for a in range(nC + 1) for j in range(nT + 1) if a + j > 0]
        U = {s: defaultdict(float) for s in names}   # per statement expected utility of each policy over 50 random orders
        for s in names:
            for _ in range(50):
                cs, ts = rng.sample(C[s], nC), rng.sample(T[s], nT)
                for a, j in grid:
                    t = 0; ok = 0
                    for o, tk in cs[:a] + ts[:j]:
                        t += tk
                        if o:
                            ok = 1; break
                    U[s][(a, j)] += (100 * ok - LAM * t / 1000) / 50
        full = {g: sum(U[s][g] for s in names) / len(names) for g in grid}
        best = max(full, key=full.get)
        reg, cheap8 = [], 0
        for _ in range(300):
            pil = rng.sample(names, 30)
            pick = max(grid, key=lambda g: sum(U[s][g] for s in pil))
            reg.append(full[best] - full[pick]); cheap8 += pick[0] >= 8
        print(f"=== {pair}: best fixed FF{best} utility {full[best]:.1f} (CHEAP×{nC} {full[(nC, 0)]:.1f}, THINK×{nT} {full[(0, nT)]:.1f}); "
              f"30-label pilot regret {sum(reg) / len(reg):.2f} (90th pct {sorted(reg)[269]:.2f}); picks with ≥ 8 cheap attempts {100 * cheap8 / 300:.0f}%")


if __name__ == "__main__":
    main()
