"""Idea 27, offline: compose the ladder and evaluate GP-P1..P5 as written in docs/prereg/PREREG_GP.md. No model call.

Usage: python poc/gp_eval.py [tag q8b] [--check checkt]
With --check, PREREG_GC: a count-1 step whose grid the checker flags (results/{gp,lgp}_<tag>_<check>.jsonl, poc/gp_check.py) goes on to the next step,
and the check's tokens are paid on every count-1 step; the plain ladder is printed beside it.
Reads results/{gp,lgp}_<tag>_{gtr,gtrt,think}_s{1,2,3}.jsonl. Ladder: gtr; if its count is not 1, gtrt; if not 1, think; every step paid.
Utility per puzzle = 100*right - 0.5*ktok. Intervals: bootstrap over puzzles (10,000 draws, 95%), each puzzle's mean over seeds.
Only puzzle-seeds present in all three arms are used (the count is printed), so a partial run reads as partial.
"""
import json
import os
import random
import sys

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
ARMS = ["gtr", "gtrt", "think"]
BIG = {"4*5", "4*6"}
SMALL = {"3*4", "3*5"}


def load(s, tag):
    R = {}
    for arm in ARMS:
        for sd in [1, 2, 3]:
            f = os.path.join(RES, f"{s}_{tag}_{arm}_s{sd}.jsonl")
            if os.path.exists(f):
                for r in map(json.loads, open(f)):
                    R[(arm, r["id"], sd)] = r
    keys = sorted({(i, sd) for (_, i, sd) in R if all((a, i, sd) in R for a in ARMS)})
    return R, keys


def ladder(R, i, sd, C=None):
    tok = 0
    for arm in ["gtr", "gtrt"]:
        r = R[(arm, i, sd)]
        tok += r["tokens"]
        if r["count"] == 1:
            c = C[(arm, i, sd)] if C is not None else None   # a missing check row raises: the check must cover every count-1 step
            tok += c["tokens"] if c else 0
            if not (c and c["violated"]):
                return r["exact"], tok, arm
    r = R[("think", i, sd)]
    return r["exact"], tok + r["tokens"], "think"


def boot(per, f, n=10000, seed=0):
    """per: {puzzle: value or list}; f(list of puzzle values) -> number. Returns point, lo, hi."""
    ids = sorted(per)
    rng = random.Random(seed)
    pt = f([per[i] for i in ids])
    xs = sorted(f([per[rng.choice(ids)] for _ in ids]) for _ in range(n))
    return pt, xs[int(0.025 * n)], xs[int(0.975 * n) - 1]


def mean(v):
    return sum(v) / len(v) if v else float("nan")


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "q8b"
    chk = sys.argv[sys.argv.index("--check") + 1] if "--check" in sys.argv else None
    out = {}
    for s in ["gp", "lgp"]:
        R, keys = load(s, tag)
        if not keys:
            print(s, "no complete puzzle-seeds yet")
            continue
        ids = sorted({i for i, _ in keys})
        print(f"== {s}: {len(keys)} puzzle-seeds, {len(ids)} puzzles (means below: over puzzles, each puzzle's mean over seeds)")

        def pm(f):
            return mean([mean([f(i, sd) for j, sd in keys if j == i]) for i in ids])
        for arm in ARMS:
            print(f"  {arm:5s} acc {100 * pm(lambda i, sd: R[(arm, i, sd)]['exact']):5.1f}  ktok {pm(lambda i, sd: R[(arm, i, sd)]['tokens']) / 1000:5.1f}  "
                  f"util {pm(lambda i, sd: 100 * R[(arm, i, sd)]['exact'] - 0.5 * R[(arm, i, sd)]['tokens'] / 1000):5.1f}")
        lad = {(i, sd): ladder(R, i, sd) for i, sd in keys}
        if chk:
            C = {(r["tr"], r["id"], r["seed"]): r for r in map(json.loads, open(os.path.join(RES, f"{s}_{tag}_{chk}.jsonl")))}
            plain = lad
            lad = {(i, sd): ladder(R, i, sd, C) for i, sd in keys}
            dp = {i: mean([100 * lad[(i, sd)][0] - 0.5 * lad[(i, sd)][1] / 1000 - (100 * plain[(i, sd)][0] - 0.5 * plain[(i, sd)][1] / 1000) for j, sd in keys if j == i]) for i in ids}
            b = boot(dp, mean)
            Ck = [r for r in C.values() if (r["id"], r["seed"]) in set(keys)]
            acc = [r for r in Ck if not r["violated"]]
            print(f"  GC: checked ladder minus plain ladder, utility {b[0]:+.1f} [{b[1]:+.1f}, {b[2]:+.1f}]; unflagged count-1 precision "
                  f"{sum(r['exact'] for r in acc)}/{len(acc)} = {100 * mean([r['exact'] for r in acc]):.1f}%; wrong flagged "
                  f"{sum(bool(r['violated']) for r in Ck if not r['exact'])}/{sum(not r['exact'] for r in Ck)}, right flagged "
                  f"{sum(bool(r['violated']) for r in Ck if r['exact'])}/{sum(r['exact'] for r in Ck)}. Rows below use the checked ladder.")
        print(f"  ladder acc {100 * pm(lambda i, sd: lad[(i, sd)][0]):5.1f}  ktok {pm(lambda i, sd: lad[(i, sd)][1]) / 1000:5.1f}  "
              f"util {pm(lambda i, sd: 100 * lad[(i, sd)][0] - 0.5 * lad[(i, sd)][1] / 1000):5.1f}  "
              f"stops: " + ", ".join(f"{a} {sum(x[2] == a for x in lad.values())}" for a in ARMS))
        # GP-P2: count-1 precision of each translation arm over all its runs
        for arm in ["gtr", "gtrt"]:
            one = [R[(arm, i, sd)] for i, sd in keys if R[(arm, i, sd)]["count"] == 1]
            p = sum(r["exact"] for r in one) / len(one) if one else float("nan")
            print(f"  P2 {arm}: count-1 precision {sum(r['exact'] for r in one)}/{len(one)} = {100 * p:.1f}%  -> {'holds' if p >= 0.95 else 'fails'}")
            out[f"{s}_P2_{arm}"] = p
        # utility and accuracy differences, ladder minus think, per puzzle averaged over seeds
        du = {i: mean([100 * lad[(i, sd)][0] - 0.5 * lad[(i, sd)][1] / 1000 - (100 * R[("think", i, sd)]["exact"] - 0.5 * R[("think", i, sd)]["tokens"] / 1000)
                       for j, sd in keys if j == i]) for i in ids}
        da = {i: mean([100 * (lad[(i, sd)][0] - R[("think", i, sd)]["exact"]) for j, sd in keys if j == i]) for i in ids}
        u = boot(du, mean)
        a = boot(da, mean)
        print(f"  ladder - think: utility {u[0]:+.1f} [{u[1]:+.1f}, {u[2]:+.1f}]  accuracy {a[0]:+.1f} [{a[1]:+.1f}, {a[2]:+.1f}] points")
        if s == "gp":
            print(f"  P1: {'holds' if u[1] > 0 else 'fails'}")
            # GP-P3: p - A on accepted puzzle-seeds (a translation arm stopped the ladder), big grids minus small grids
            edge = {}
            for i, sd in keys:
                if lad[(i, sd)][2] != "think":
                    edge.setdefault(i, []).append(lad[(i, sd)][0] - R[("think", i, sd)]["exact"])
            size = {i: R[("think", i, sd)]["size"] for i, sd in keys}

            def gap(vals_by_puzzle):
                b = [x for i, v in vals_by_puzzle for x in v if size[i] in BIG]
                sm = [x for i, v in vals_by_puzzle for x in v if size[i] in SMALL]
                return 100 * (mean(b) - mean(sm))

            per = {i: (i, v) for i, v in edge.items()}
            g = boot(per, gap)
            for grp, S in [("4x5, 4x6", BIG), ("3x4, 3x5", SMALL)]:
                v = [x for i, w in edge.items() if size[i] in S for x in w]
                print(f"  p - A on {grp}: {100 * mean(v):+.1f} points over {len(v)} accepted puzzle-seeds")
            print(f"  P3: big minus small {g[0]:+.1f} [{g[1]:+.1f}, {g[2]:+.1f}] -> {'holds' if g[1] > 0 else 'fails'}")
            for sz in sorted({size[i] for i in ids}):
                k = [(i, sd) for i, sd in keys if size[i] == sz]
                print(f"    {sz}: think {100 * mean([R[('think', i, sd)]['exact'] for i, sd in k]):5.1f}%  ladder {100 * mean([lad[x][0] for x in k]):5.1f}%  "
                      f"translation stops {sum(lad[x][2] != 'think' for x in k)}/{len(k)}  util ladder-think "
                      f"{mean([100 * lad[x][0] - 0.5 * lad[x][1] / 1000 - 100 * R[('think',) + x]['exact'] + 0.5 * R[('think',) + x]['tokens'] / 1000 for x in k]):+.1f}")
        else:
            print(f"  P4: accuracy lower bound {a[1]:+.1f} {'>' if a[1] > -2 else '<='} -2, utility lower bound {u[1]:+.1f} -> "
                  f"{'holds' if a[1] > -2 and u[1] > 0 else 'fails'}")
            print(f"  P5: ladder accuracy {100 * pm(lambda i, sd: lad[(i, sd)][0]):.1f}% (Ishay et al. GPT-4 92%, Logicia 71%)")


if __name__ == "__main__":
    main()
