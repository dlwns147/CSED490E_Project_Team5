"""Idea 27, offline: compose the ladder and evaluate GP-P1..P5 as written in docs/prereg/PREREG_GP.md. No model call.

Usage: python poc/gp_eval.py [tag q8b] [--check checkt] [--score2]
--score2 (any mode that uses load()): exact from scoring v2, poc/grid_score.py.
With --check, PREREG_GC: a count-1 step whose grid the checker flags (results/{gp,lgp}_<tag>_<check>.jsonl, poc/gp_check.py) goes on to the next step,
and the check's tokens are paid on every count-1 step; the plain ladder is printed beside it.
Reads results/{gp,lgp}_<tag>_{gtr,gtrt,think}_s{1,2,3}.jsonl. Ladder: gtr; if its count is not 1, gtrt; if not 1, think; every step paid.
Utility per puzzle = 100*right - 0.5*ktok. Intervals: bootstrap over puzzles (10,000 draws, 95%), each puzzle's mean over seeds.
Only puzzle-seeds present in all three arms are used (the count is printed), so a partial run reads as partial.

python poc/gp_eval.py --loc [tag q8bl] [think tag q8b]: idea 33 on dev, localized feedback (gtrl, gtrtl) minus generic (gtr, gtrt), ladder utility
per puzzle-seed. Step 1: gtrl vs gtr (seeds 1-3), later steps from seed-1 gtrt and think. Step 2: gtrtl vs gtrt (seed 1), step 1 from seed-1 gtr.
Both: gtrl+gtrtl vs gtr+gtrt. With --test (PREREG_GP addendum GP-LOC; also with --gts): the test split, generic arms and think from the q8b test runs of the same seed. Rule (docs/notes/IDEAS_COMPUTATION.md row 33): a step's localized arm passes if its point estimate pooled over
both sets is above 0.

python poc/gp_eval.py --thinkf: idea 34, thinking given a right translation vs plain thinking (see thinkf()).

python poc/gp_eval.py --gts [tag q8bh] [think tag q8b]: idea 38 on dev, the per-clue search of Schrader et al. (gts) as the middle step in place
of gtrt (--joint: gtsj, poc/gp_joint.py): ladder gtr (same seed) -> gts (same seed) -> think (seed 1) minus gtr -> gtrt (seed 1) -> think, per puzzle-seed (seeds 1-3).
Rule (docs/notes/IDEAS_COMPUTATION.md row 38): pooled over both sets, point estimate above 0 -> gts replaces gtrt in a test prereg.
python poc/gp_eval.py --np [tag q32]: PREREG_NP (with addendum NP-DAY), see np_main().
python poc/gp_eval.py --zl <tag> [...] [--score2]: PREREG_ZL ladder against thinking, see zl_main().
python poc/gp_eval.py --mot <tag>: PREREG_MOT, the ladder against an agreement cascade, see mot_main().
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
    if "--score2" in sys.argv:   # scoring v2 (poc/grid_score.py, poc/gp_rescore.py): exact from results/<s>_<tag>_score2.json
        S2 = json.load(open(os.path.join(RES, f"{s}_{tag}_score2.json")))
        for (arm, i, sd), r in R.items():
            R[(arm, i, sd)] = {**r, "exact": S2[f"{arm}|{i}|{sd}"][0]}
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
            if "--score2" in sys.argv:   # a checked program is right when its own row is, under scoring v2
                C = {k: {**r, "exact": R[(k[0], k[1], k[2])]["exact"]} for k, r in C.items()}
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


def loc_main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    g = "--gts" in sys.argv
    mid = "gtsj" if "--joint" in sys.argv else "gts"   # --joint: idea 38's joint choice (poc/gp_joint.py) in place of gts
    tag, ttag = (a + ["q8bh" if g else "q8bl", "q8b"][len(a):])[:2]
    CMP = ([(mid, lambda sd: ([("gtr", sd), (mid, sd), ("think", 1)], [("gtr", sd), ("gtrt", 1), ("think", 1)], [1, 2, 3]))] if g else
           [("step 1", lambda sd: ([("gtrl", sd), ("gtrt", 1), ("think", 1)], [("gtr", sd), ("gtrt", 1), ("think", 1)], [1, 2, 3])),
            ("step 2", lambda sd: ([("gtr", 1), ("gtrtl", 1), ("think", 1)], [("gtr", 1), ("gtrt", 1), ("think", 1)], [1])),
            ("both", lambda sd: ([("gtrl", sd), ("gtrtl", 1), ("think", 1)], [("gtr", sd), ("gtrt", 1), ("think", 1)], [1, 2, 3]))])
    SHOW = [("gtr", [1, 2, 3]), (mid, [1, 2, 3]), ("gtrt", [1])] if g else [("gtr", [1, 2, 3]), ("gtrl", [1, 2, 3]), ("gtrt", [1]), ("gtrtl", [1])]
    dv, src = "_dev", lambda arm: tag
    if "--test" in sys.argv:   # PREREG_GP addendum GP-LOC: test split; the generic arms and think are the q8b test runs, seeds 1-3
        dv, src = "", lambda arm: tag if arm in ("gtrl", "gtrtl", "gts", "gtsj") else ttag
        CMP = ([(mid, lambda sd: ([("gtr", sd), (mid, sd), ("think", sd)], [("gtr", sd), ("gtrt", sd), ("think", sd)], [1, 2, 3]))] if g else
               [("step 1", lambda sd: ([("gtrl", sd), ("gtrt", sd), ("think", sd)], [("gtr", sd), ("gtrt", sd), ("think", sd)], [1, 2, 3])),
                ("step 2", lambda sd: ([("gtr", 1), ("gtrtl", 1), ("think", 1)], [("gtr", 1), ("gtrt", 1), ("think", 1)], [1]))])
        SHOW = [("gtr", [1, 2, 3]), (mid, [1, 2, 3]), ("gtrt", [1, 2, 3])] if g else [("gtr", [1, 2, 3]), ("gtrl", [1, 2, 3]), ("gtrt", [1, 2, 3]), ("gtrtl", [1])]
    pooled = {k: [] for k, _ in CMP}
    for s in ["gp", "lgp"]:
        R = {}
        for arm, t, seeds in [(x, src(x), sds) for x, sds in SHOW] + [("think", ttag, [1, 2, 3] if dv == "" else [1])]:
            for sd in seeds:
                f = os.path.join(RES, f"{s}_{t}{dv}_{arm}_s{sd}.jsonl")
                if os.path.exists(f):
                    for r in map(json.loads, open(f)):
                        R[(arm, r["id"], sd)] = r

        def lad(steps):   # steps: [(arm, seed), (arm, seed), ("think", 1)]; returns utility, or None if a run is missing
            tok = 0
            for k, (arm, sd) in enumerate(steps):
                r = R.get((arm, i, sd))
                if r is None:
                    return None
                tok += r["tokens"]
                if r.get("count") == 1 or k == len(steps) - 1:
                    return 100 * r["exact"] - 0.5 * tok / 1000
        ids = sorted({i for (_, i, _) in R})
        print(f"== {s} {'dev' if dv else 'test'}: {len(ids)} puzzles")
        for arm, seeds in SHOW + [("think", [1, 2, 3] if dv == "" else [1])]:
            rs = [R[(arm, i, sd)] for i in ids for sd in seeds if (arm, i, sd) in R]
            one = [r for r in rs if r.get("count") == 1]
            print(f"  {arm:6s} runs {len(rs):3d}  acc {100 * mean([r['exact'] for r in rs]):5.1f}  count-1 {len(one):3d}, precision "
                  f"{sum(r['exact'] for r in one)}/{len(one)}  rounds {mean([r.get('rounds', 0) for r in rs]):.2f}  ktok {mean([r['tokens'] for r in rs]) / 1000:5.1f}")
        for name, cmp in CMP:
            per = {}
            for i in ids:
                for sd in cmp(1)[2]:
                    L, G = lad(cmp(sd)[0]), lad(cmp(sd)[1])
                    if L is not None and G is not None:
                        per.setdefault(i, []).append(L - G)
                        pooled[name].append((s, i, L - G))
            n = sum(len(v) for v in per.values())
            if per:
                b = boot({i: mean(v) for i, v in per.items()}, mean)
                print(f"  {name}: {mid + ' minus gtrt' if g else 'localized minus generic'} ladder utility {b[0]:+.1f} [{b[1]:+.1f}, {b[2]:+.1f}] over {n} puzzle-seeds")
    for name, v in pooled.items():
        if v:
            per = {}
            for s, i, d in v:
                per.setdefault((s, i), []).append(d)
            b = boot({k: mean(x) for k, x in per.items()}, mean)
            print(f"POOLED {name}: {b[0]:+.2f} [{b[1]:+.2f}, {b[2]:+.2f}] over {len(v)} puzzle-seeds -> " + (
                  ("replaces the generic arm (interval above 0)" if b[1] > 0 else "generic arm stays") if not dv else
                  ("passes (pre-register on test)" if b[0] > 0 else "killed")) + ("" if name != "both" else " (reported)"))


def zl_am():
    """PREREG_ZL addendum ZL-AM: python poc/gp_eval.py --zlam [tag q32am]. Ladder tr -> trt -> think on Amonkar et al.'s 100 ZebraLogic puzzles,
    each step paid; strata by search space (n!)^m (small < 1e3, medium < 1e6, large < 1e10, x-large); bootstrap over puzzles."""
    import math
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    tag = a[0] if a else "q32am"
    R = {}
    for arm in ["tr", "trt", "think"]:
        for sd in [1, 2, 3]:
            f = os.path.join(RES, f"zl_{tag}_{arm}_s{sd}.jsonl")
            if os.path.exists(f):
                for r in map(json.loads, open(f)):
                    R[(arm, r["id"], sd)] = r
    keys = sorted({(i, sd) for (_, i, sd) in R if all((x, i, sd) in R for x in ["tr", "trt", "think"])})
    def stratum(size):
        n, m = map(int, size.lower().replace("*", "x").split("x"))
        v = math.factorial(n) ** m
        return "small" if v < 1e3 else "medium" if v < 1e6 else "large" if v < 1e10 else "x-large"
    lad, thk, ids = {}, {}, {}
    for i, sd in keys:
        tok = 0
        for arm in ["tr", "trt"]:
            r = R[(arm, i, sd)]; tok += r["tokens"]
            if r["count"] == 1:
                ex = r["exact"]; break
        else:
            r = R[("think", i, sd)]; tok += r["tokens"]; ex = r["exact"]
        t = R[("think", i, sd)]
        lad.setdefault(i, []).append((ex, tok)); thk.setdefault(i, []).append((t["exact"], t["tokens"])); ids[i] = stratum(t["size"])
    print(f"== ZL-AM {tag}: {len(keys)} puzzle-seeds, {len(ids)} puzzles")
    for arm in ["tr", "trt", "think"]:
        rs = [R[(arm, i, sd)] for i, sd in keys]
        one = [r for r in rs if r.get("count") == 1]
        print(f"  {arm:6s} acc {100 * mean([r['exact'] for r in rs]):5.1f}  ktok {mean([r['tokens'] for r in rs]) / 1000:5.1f}" + (f"  count-1 precision {sum(r['exact'] for r in one)}/{len(one)}" if arm != "think" else ""))
    for name, sel in [("all", lambda s_: True), ("large + x-large", lambda s_: s_ in ("large", "x-large"))] + [(k, (lambda k: lambda s_: s_ == k)(k)) for k in ["small", "medium", "large", "x-large"]]:
        P = [i for i in ids if sel(ids[i])]
        if not P:
            continue
        acc = lambda D: {i: mean([100 * e for e, _ in D[i]]) for i in P}
        utl = lambda D: {i: mean([100 * e - 0.5 * k / 1000 for e, k in D[i]]) for i in P}
        la, ta, lu, tu = acc(lad), acc(thk), utl(lad), utl(thk)
        da = boot({i: la[i] - ta[i] for i in P}, mean); du = boot({i: lu[i] - tu[i] for i in P}, mean)
        print(f"  {name:16s} ({len(P):3d} puzzles): ladder {mean(list(la.values())):5.1f}  think {mean(list(ta.values())):5.1f}  "
              f"acc diff {da[0]:+.1f} [{da[1]:+.1f}, {da[2]:+.1f}]  utility diff {du[0]:+.1f} [{du[1]:+.1f}, {du[2]:+.1f}]")


def thinkf():
    """idea 34 (docs/notes/IDEAS_COMPUTATION.md row 34): thinking given a right translation (q8bf thinkf) vs plain thinking (q8b think), paired by
    puzzle-seed on GridPuzzle test. Rule: on 4x5 and 4x6, share of thinking's errors removed = (acc thinkf - acc think) / (1 - acc think), bootstrap over
    puzzles; upper bound < 0.5 -> search is the main cause; lower bound > 0.5 -> reading is; otherwise inconclusive."""
    F, T = {}, {}
    for sd in [1, 2, 3]:
        for r in map(json.loads, open(os.path.join(RES, f"gp_q8bf_thinkf_s{sd}.jsonl"))):
            F[(r["id"], sd)] = r
        for r in map(json.loads, open(os.path.join(RES, f"gp_q8b_think_s{sd}.jsonl"))):
            T[(r["id"], sd)] = r
    keys = [k for k in F if k in T]
    print(f"thinkf vs think: {len(keys)} puzzle-seeds, {len({i for i, _ in keys})} puzzles")
    for name, sizes in [("4x5, 4x6", BIG), ("3x4, 3x5", SMALL), ("4x4", {"4*4"}), ("all", None)]:
        per = {}
        for i, sd in keys:
            if sizes is None or F[(i, sd)]["size"] in sizes:
                per.setdefault(i, []).append((F[(i, sd)]["exact"], T[(i, sd)]["exact"], F[(i, sd)]["tokens"], T[(i, sd)]["tokens"]))
        if not per:
            continue
        af = lambda v: mean([x[0] for p in v for x in p])
        at = lambda v: mean([x[1] for p in v for x in p])
        share = boot(per, lambda v: (af(v) - at(v)) / max(1e-9, 1 - at(v)))
        print(f"  {name:9s} {len(per):3d} puzzles  thinkf {100 * af(list(per.values())):5.1f}%  think {100 * at(list(per.values())):5.1f}%  "
              f"ktok {mean([x[2] for p in per.values() for x in p]) / 1000:.1f} vs {mean([x[3] for p in per.values() for x in p]) / 1000:.1f}  "
              f"share of errors removed {share[0]:+.2f} [{share[1]:+.2f}, {share[2]:+.2f}]")


def np_main():
    """PREREG_NP + addendum NP-DAY: python poc/gp_eval.py --np [tag q32]. NaturalPlan trips (Amonkar et al.'s 100), ladder trc -> trct -> think, every
    step paid; right = the gold plan; "valid" = a plan meeting every annotated constraint (Amonkar et al.'s metric, poc/np_uniq.py cover reading).
    NP-P1 count-1 precision of trc and trct passes pooled >= 95%; NP-P2 ladder - think utility, interval above 0; NP-P3 on 7-10 cities ladder - think
    accuracy, lower bound above 0; NP-P4 trct alone (count 1 gives its plan, otherwise wrong) at most think + 2 points. Bootstrap over trips."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from np_uniq import valid_plans
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    tag = a[0] if a else "q32"
    V = valid_plans(os.path.join(os.environ.get("POC_DATA", os.path.join(RES, "..", "..", "nlp_data")), "naturalplan_dl", "a_trip_planning_100_constraints.json"))
    A = ["trc", "trct", "think"]
    R = {}
    for arm in A:
        for sd in [1, 2, 3]:
            f = os.path.join(RES, f"np_{tag}_{arm}_s{sd}.jsonl")
            if os.path.exists(f):
                for r in map(json.loads, open(f)):
                    R[(arm, r["id"], sd)] = r
    keys = sorted({(i, sd) for (_, i, sd) in R if all((x, i, sd) in R for x in A)})
    val = lambda r, pl: tuple(map(tuple, pl)) in V.get(r["id"], set()) if pl else False
    lad, thk, alone, nc = {}, {}, {}, {}
    passes = []
    for i, sd in keys:
        tok = 0
        for arm in ["trc", "trct"]:
            r = R[(arm, i, sd)]; tok += r["tokens"]
            if r["count"] == 1:
                passes.append(r["exact"]); ex, va = r["exact"], val(r, r["plan"]); break
        else:
            r = R[("think", i, sd)]; tok += r["tokens"]; ex, va = r["exact"], val(r, r["plan"])
        t, c = R[("think", i, sd)], R[("trct", i, sd)]
        lad.setdefault(i, []).append((ex, tok, va)); thk.setdefault(i, []).append((t["exact"], t["tokens"], val(t, t["plan"])))
        alone.setdefault(i, []).append((c["exact"] and c["count"] == 1, c["tokens"], c["count"] == 1 and val(c, c["plan"])))
        nc[i] = t["ncity"]
    print(f"== NP {tag}: {len(keys)} trip-seeds, {len(nc)} trips")
    for arm in A:
        rs = [R[(arm, i, sd)] for i, sd in keys]
        one = [r for r in rs if r.get("count") == 1]
        print(f"  {arm:6s} acc {100 * mean([r['exact'] for r in rs]):5.1f}  ktok {mean([r['tokens'] for r in rs]) / 1000:5.1f}" +
              (f"  count-1 {len(one)}, precision {sum(r['exact'] for r in one)}/{len(one)}" if arm != "think" else ""))
    print(f"  NP-P1 count-1 precision, trc + trct passes on the ladder: {sum(passes)}/{len(passes)} = {100 * mean(passes):.1f}% (holds if >= 95)")
    # addendum NP-DP, reported rows: D&P-3 (count-1 trct plans of the three seeds, majority, else think seed 1) and SC-3 (majority of three think plans),
    # each paying all its runs; on trips with all three seeds of every arm, against the ladder averaged over seeds
    full = [i for i in nc if all((x, i, sd) in R for x in A for sd in [1, 2, 3])]
    def vote(plans):
        c = {}
        for p in plans:
            c[p] = c.get(p, 0) + 1
        return max(c, key=lambda p: (c[p], -plans.index(p))) if c else None
    gold = {i: next(tuple(map(tuple, R[(x, i, sd)]["plan"])) for x in A for sd in [1, 2, 3]
                    if R[(x, i, sd)]["exact"] and R[(x, i, sd)]["plan"]) if any(R[(x, i, sd)]["exact"] for x in A for sd in [1, 2, 3]) else None
            for i in full}
    dp, sc = {}, {}
    for i in full:
        t = [R[("trct", i, sd)] for sd in [1, 2, 3]]
        v = vote([tuple(map(tuple, r["plan"])) for r in t if r["count"] == 1 and r["plan"]])
        tok = sum(r["tokens"] for r in t)
        if v is None:
            r1 = R[("think", i, 1)]; ok = r1["exact"]; tok += r1["tokens"]
        else:
            ok = gold[i] is not None and v == gold[i]
        dp[i] = (ok, tok)
        th = [R[("think", i, sd)] for sd in [1, 2, 3]]
        v = vote([tuple(map(tuple, r["plan"])) for r in th if r["plan"]])
        sc[i] = (v is not None and gold[i] is not None and v == gold[i], sum(r["tokens"] for r in th))
    if full:
        u = lambda D: {i: (100 * D[i][0] - 0.5 * D[i][1] / 1000) if isinstance(D[i], tuple) else mean([100 * x[0] - 0.5 * x[1] / 1000 for x in D[i]]) for i in full}
        a_ = lambda D: mean([100 * D[i][0] if isinstance(D[i], tuple) else mean([100 * x[0] for x in D[i]]) for i in full])
        k_ = lambda D: mean([D[i][1] if isinstance(D[i], tuple) else mean([x[1] for x in D[i]]) for i in full]) / 1000
        ul = u(lad)
        print(f"  NP-DP reported rows on {len(full)} trips with every seed: ladder {a_(lad):5.1f}% {k_(lad):5.1f} ktok, think {a_(thk):5.1f}% {k_(thk):5.1f} ktok")
        for name, D in [("D&P-3", dp), ("SC-3", sc)]:
            ud = u(D); d = boot({i: ul[i] - ud[i] for i in full}, mean)
            print(f"    {name:5s} {a_(D):5.1f}% {k_(D):5.1f} ktok   ladder - {name} utility {d[0]:+.1f} [{d[1]:+.1f}, {d[2]:+.1f}]")
    # exploratory, after the registered reading (2026-11-10 21:xx): where the ladder's gain comes from, all from stored rounds (hist[0] = a 1-round run)
    #   r1: trct's first round alone vs think; L1: trc -> trct -> think with first rounds only (no count feedback, escalate at once); noq: trct -> think (no trc)
    r1a, L1, NQ, LL = {}, {}, {}, {}
    for i, sd in keys:
        h = {x: R[(x, i, sd)]["hist"][0] for x in ["trc", "trct"]}; t = R[("think", i, sd)]
        r1a.setdefault(i, []).append(100 * (h["trct"]["count"] == 1 and h["trct"]["exact"]) - 100 * t["exact"])
        tok = 0
        for x in ["trc", "trct"]:
            tok += h[x]["tokens"]
            if h[x]["count"] == 1:
                ok = h[x]["exact"]; break
        else:
            tok += t["tokens"]; ok = t["exact"]
        L1.setdefault(i, []).append(100 * ok - 0.5 * tok / 1000)
        c = R[("trct", i, sd)]
        ok, tok = (c["exact"], c["tokens"]) if c["count"] == 1 else (t["exact"], c["tokens"] + t["tokens"])
        NQ.setdefault(i, []).append(100 * ok - 0.5 * tok / 1000)
    for i in nc:
        LL[i] = mean([100 * x[0] - 0.5 * x[1] / 1000 for x in lad[i]])
    for name, D in [("trct round 1 alone - think, accuracy", {i: mean(v) for i, v in r1a.items()}),
                    ("ladder - L1 (first rounds only), utility", {i: LL[i] - mean(L1[i]) for i in nc}),
                    ("ladder - (trct -> think, no trc), utility", {i: LL[i] - mean(NQ[i]) for i in nc})]:
        d = boot(D, mean)
        print(f"  exploratory {name}: {d[0]:+.1f} [{d[1]:+.1f}, {d[2]:+.1f}]")
    # PREREG_NPC (--check checkt): a count-1 step whose plan the model flags goes on down the ladder; the check's tokens are paid on every count-1
    # step reached. Also the ceiling of the registration: a perfect check at the real check's mean tokens.
    ca = sys.argv[sys.argv.index("--check") + 1] if "--check" in sys.argv else None
    if ca:
        C = {(x["tr"], x["id"], x["seed"]): x for x in map(json.loads, open(os.path.join(RES, f"np_{tag}_{ca}.jsonl")))}
        kc = mean([x["tokens"] for x in C.values()])
        CL, CA, PF, kept, miss = {}, {}, {}, [], 0
        for i, sd in keys:
            def run(perfect):
                tok = 0
                for arm in ["trc", "trct"]:
                    r = R[(arm, i, sd)]; tok += r["tokens"]
                    if r["count"] == 1:
                        c = C.get((arm, i, sd))
                        tok += kc if perfect else (c["tokens"] if c else 0)
                        flag = (not r["exact"]) if perfect else bool(c and c["violated"])
                        if not flag:
                            return r["exact"], tok, True
                t = R[("think", i, sd)]
                return t["exact"], tok + t["tokens"], False
            ex, tok, gate = run(False)
            if gate:
                kept.append(ex)
            miss += any(R[(a_r, i, sd)]["count"] == 1 and (a_r, i, sd) not in C for a_r in ["trc", "trct"])
            CA.setdefault(i, []).append((ex, tok)); CL.setdefault(i, []).append(100 * ex - 0.5 * tok / 1000); PF.setdefault(i, []).append(100 * run(True)[0] - 0.5 * run(True)[1] / 1000)
        W = [x for x in C.values() if not x["exact"]]
        print(f"  NPC {ca}: {len(C)} checks, {kc / 1000:.2f} ktok each; wrong plans flagged {sum(bool(x['violated']) for x in W)}/{len(W)}, right plans flagged "
              f"{sum(bool(x['violated']) for x in C.values() if x['exact'])}/{len(C) - len(W)}, unparsed {sum(x['violated'] is None for x in C.values())}"
              + (f"; {miss} count-1 steps without a check row" if miss else ""))
        # addendum NPC-T: wrong plans by error type; "overlap only" = the plan's one break is a dated event overlapping, not inside, its stay
        from np_uniq import error_types
        ET = error_types(os.path.join(os.environ.get("POC_DATA", os.path.join(RES, "..", "..", "nlp_data")), "naturalplan_dl", "a_trip_planning_100_constraints.json"))
        ov = [x for x in W if ET[x["id"]](R[(x["tr"], x["id"], x["seed"])]["plan"]) == frozenset(["event_overlap_only"])]
        print(f"  NPC-T wrong plans flagged: overlap only {sum(bool(x['violated']) for x in ov)}/{len(ov)}, other {sum(bool(x['violated']) for x in W if x not in ov)}/{len(W) - len(ov)}")
        print(f"  NPC-P1 unflagged count-1 precision on the checked ladder: {sum(kept)}/{len(kept)} = {100 * mean(kept):.1f}% (holds if >= 95)")
        ut = lambda D: {i: mean(D[i]) for i in nc}
        cl, th = ut(CL), {i: mean([100 * x[0] - 0.5 * x[1] / 1000 for x in thk[i]]) for i in nc}
        print(f"  checked ladder {mean([100 * x[0] for v in CA.values() for x in v]):.1f}% {mean([x[1] for v in CA.values() for x in v]) / 1000:.1f} ktok")
        for name, D in [("NPC-P2 checked - plain ladder", {i: cl[i] - LL[i] for i in nc}), ("NPC-P3 checked ladder - think", {i: cl[i] - th[i] for i in nc}),
                        ("ceiling: perfect check - plain ladder", {i: mean(PF[i]) - LL[i] for i in nc})]:
            d = boot(D, mean)
            print(f"  {name}, utility: {d[0]:+.1f} [{d[1]:+.1f}, {d[2]:+.1f}]")
    strata =[("all", 3, 10), ("3-4", 3, 4), ("5-6", 5, 6), ("7-8", 7, 8), ("9-10", 9, 10), ("7-10", 7, 10)]
    for name, lo, hi in strata:
        P = [i for i in nc if lo <= nc[i] <= hi]
        if not P:
            continue
        acc = lambda D, j=0: {i: mean([100 * x[j] for x in D[i]]) for i in P}
        utl = lambda D: {i: mean([100 * x[0] - 0.5 * x[1] / 1000 for x in D[i]]) for i in P}
        la, ta, ca = acc(lad), acc(thk), acc(alone)
        da = boot({i: la[i] - ta[i] for i in P}, mean); du = boot({i: utl(lad)[i] - utl(thk)[i] for i in P}, mean)
        d4 = boot({i: ca[i] - ta[i] for i in P}, mean)
        kt = lambda D: mean([x[1] for i in P for x in D[i]]) / 1000
        print(f"  {name:5s} ({len(P):3d} trips) ladder {mean(list(la.values())):5.1f}% {kt(lad):5.1f} ktok (valid {mean(list(acc(lad, 2).values())):5.1f})  "
              f"think {mean(list(ta.values())):5.1f}% {kt(thk):5.1f} ktok (valid {mean(list(acc(thk, 2).values())):5.1f})  trct alone {mean(list(ca.values())):5.1f}%\n"
              f"        acc diff {da[0]:+.1f} [{da[1]:+.1f}, {da[2]:+.1f}]  utility diff {du[0]:+.1f} [{du[1]:+.1f}, {du[2]:+.1f}]  "
              f"trct alone - think {d4[0]:+.1f} [{d4[1]:+.1f}, {d4[2]:+.1f}]")


def zl_main():
    """ZebraLogic ladder trf -> trt -> think against think (PREREG_ZL), several tags pooled as one puzzle set (q8bh q8bf = Qwen3-8B's 750 unseen puzzles).
    usage: python poc/gp_eval.py --zl <tag> [<tag> ...] [--score2]"""
    tags = [a for a in sys.argv[sys.argv.index("--zl") + 1:] if not a.startswith("--")]
    U = lambda ok, t: 100 * ok - 0.5 * t / 1000
    R = {}
    for tag in tags:
        S2 = json.load(open(os.path.join(RES, f"zl_{tag}_score2.json"))) if "--score2" in sys.argv else {}
        for arm in ["trf", "trt", "think"]:
            for sd in [1, 2, 3]:
                f = os.path.join(RES, f"zl_{tag}_{arm}_s{sd}.jsonl")
                for r in map(json.loads, open(f)) if os.path.exists(f) else []:
                    R[(arm, r["id"], sd)] = {**r, "exact": S2[f"{arm}|{r['id']}|{sd}"][0]} if S2 else r
    keys = sorted({(i, sd) for (_, i, sd) in R if all((a, i, sd) in R for a in ["trf", "trt", "think"])})
    ids = sorted({i for i, _ in keys})

    def lad(i, sd):
        tok = 0
        for arm in ["trf", "trt"]:
            r = R[(arm, i, sd)]; tok += r["tokens"]
            if r["count"] == 1:
                return r["exact"], tok
        r = R[("think", i, sd)]; return r["exact"], tok + r["tokens"]
    th = lambda i, sd: (R[("think", i, sd)]["exact"], R[("think", i, sd)]["tokens"])
    f = lambda v: mean([mean(x) for x in v])
    per = lambda g: {i: [g(i, sd) for j, sd in keys if j == i] for i in ids}
    acc = lambda g: 100 * f(list(per(lambda i, sd: g(i, sd)[0]).values()))
    du = boot(per(lambda i, sd: U(*lad(i, sd)) - U(*th(i, sd))), f)
    da = boot(per(lambda i, sd: 100 * (lad(i, sd)[0] - th(i, sd)[0])), f)
    one = [R[(a, i, sd)] for a in ["trf", "trt"] for i, sd in keys if R[(a, i, sd)]["count"] == 1]
    print(f"== ZL {'+'.join(tags)}{' (scoring v2)' if '--score2' in sys.argv else ''}: {len(keys)} puzzle-seeds, {len(ids)} puzzles; ladder {acc(lad):.1f}%, "
          f"think {acc(th):.1f}%; ladder - think utility {du[0]:+.1f} [{du[1]:+.1f}, {du[2]:+.1f}], accuracy {da[0]:+.1f} [{da[1]:+.1f}, {da[2]:+.1f}]; "
          f"count-1 precision {sum(r['exact'] for r in one)}/{len(one)}")


def mot_main():
    """PREREG_MOT: the plain ladder against the MoT agreement cascade (Yue et al. 2310.03094; 3 direct + 3 one-round gtr samples) and a 3-program vote,
    each escalating to think when the top answer's share is below tau. Replicate k: samples of seeds 10k+1..10k+3, think and ladder of seed k.
    usage: python poc/gp_eval.py --mot <tag> --score2   (reads results/{gp,lgp}_<tag>_{gtr,direct}_s1[1-3]|s2[1-3]|s3[1-3].jsonl; --score2 for the ladder)"""
    import re
    tag = sys.argv[sys.argv.index("--mot") + 1]
    U = lambda ok, t: 100 * ok - 0.5 * t / 1000

    from grid_score import match

    def canon(g, r):   # scoring v2 (poc/grid_score.py, PREREG_MOT addendum): the listed value each cell names, as a hashable answer; None for no answer
        if not isinstance(g, dict) or not g:
            return None
        ck = lambda a: re.sub(r"[^a-z0-9]", "", str(a).lower()).rstrip("s")
        got = {ck(k): v for k, v in g.items() if isinstance(v, list)}
        return tuple((ck(a), tuple(match(x, vals) for x in (got.get(ck(a)) or []))) for a, vals in r["cats"][1:])
    data = os.environ.get("POC_DATA", os.path.join(RES, "..", "..", "nlp_data"))
    res, curves = {}, {}
    for s, src in [("gp", "gridpuzzle"), ("lgp", "lgp")]:
        PZ = {r["id"]: r for r in map(json.loads, open(os.path.join(data, src, "grid.jsonl")))}
        R, keys = load(s, tag)
        S = {}
        for arm in ["gtr", "direct"]:
            for sd in [10 * k + j for k in [1, 2, 3] for j in [1, 2, 3]]:
                f = os.path.join(RES, f"{s}_{tag}_{arm}_s{sd}.jsonl")
                for x in map(json.loads, open(f)) if os.path.exists(f) else []:
                    S[(arm, x["id"], sd)] = x
        gold = {i: canon(PZ[i]["gold"], PZ[i]) for i in PZ}
        ks = [(i, k) for i, k in keys if all((a, i, 10 * k + j) in S for a in ["gtr", "direct"] for j in [1, 2, 3])]
        ids = sorted({i for i, _ in ks})
        if not ids:
            print(s, "no complete replicates yet"); continue

        def samples(i, k, arms):
            out = []
            for a in arms:
                for j in [1, 2, 3]:
                    x = S[(a, i, 10 * k + j)]
                    g = x["hist"][0].get("grid") if a == "gtr" else x.get("grid")
                    ok = a == "direct" or x["hist"][0]["count"] >= 1
                    out.append((canon(g, PZ[i]) if ok else None, x["tokens"]))
            return out

        def cascade(i, k, arms, tau):
            sm = samples(i, k, arms); tok = sum(t for _, t in sm)
            votes = {}
            for a, _ in sm:
                if a is not None:
                    votes[a] = votes.get(a, 0) + 1
            if votes:
                a, c = max(votes.items(), key=lambda kv: kv[1])
                if c / len(sm) >= tau - 1e-9:
                    return U(a == gold[i], tok), True, a == gold[i], c >= 1 and sum(1 for b, _ in sm[-3:] if b == a and a != gold[i]) >= 2
            r = R[("think", i, k)]
            return U(r["exact"], tok + r["tokens"]), False, None, False
        lad = lambda i, k: U(*ladder(R, i, k)[:2])
        dacc = {i: mean([100 * S[("direct", i, 10 * k + j)]["exact"] for ii, k in ks if ii == i for j in [1, 2, 3]]) for i in ids}
        dtok = mean([S[("direct", i, 10 * k + j)]["tokens"] for i, k in ks for j in [1, 2, 3]]) / 1000
        print(f"== {s} {tag}: {len(ids)} puzzles, {len(ks)} puzzle-replicates; direct (no thinking) {mean(list(dacc.values())):.1f}% at {dtok:.2f} ktok")
        for name, arms, n in [("MoT CoT+PoT", ["direct", "gtr"], 6), ("PoT vote", ["gtr"], 3)]:
            for c in range(1, n + 1):
                tau = c / n
                per = {i: [lad(i, k) - cascade(i, k, arms, tau)[0] for ii, k in ks if ii == i] for i in ids}
                acc = [cascade(i, k, arms, tau) for i, k in ks]
                cov = mean([a[1] for a in acc]); prec = mean([a[2] for a in acc if a[1]]) if any(a[1] for a in acc) else float("nan")
                corr = sum(a[3] for a in acc)
                pt, lo, hi = boot(per, lambda v: mean([mean(x) for x in v]))
                curves[(s, name, c)] = pt; res[(s, name, c)] = (pt, lo, hi)
                print(f"  {name:11s} tau {c}/{n}: ladder - cascade {pt:+5.1f} [{lo:+5.1f}, {hi:+5.1f}]  coverage {cov:.2f}  precision {100 * prec:5.1f}%  "
                      f"accepted wrong with 2+ programs sharing it {corr}")
    for name, n in [("MoT CoT+PoT", 6), ("PoT vote", 3)]:
        for s, o in [("gp", "lgp"), ("lgp", "gp")]:
            if (s, name, 1) not in res:
                continue
            c = min(range(1, n + 1), key=lambda c: res[(s, name, c)][0])   # oracle: tau where the cascade does best against the ladder
            line = f"  {s} {name}: best tau {c}/{n} on this set: {res[(s, name, c)][0]:+.1f} [{res[(s, name, c)][1]:+.1f}, {res[(s, name, c)][2]:+.1f}]"
            if (o, name, 1) in res:
                co = min(range(1, n + 1), key=lambda c: res[(o, name, c)][0])
                line += f"; tau {co}/{n} picked on {o}: {res[(s, name, co)][0]:+.1f} [{res[(s, name, co)][1]:+.1f}, {res[(s, name, co)][2]:+.1f}]"
            print(line)


if __name__ == "__main__":
    mot_main() if "--mot" in sys.argv else zl_main() if "--zl" in sys.argv else np_main() if "--np" in sys.argv else thinkf() if "--thinkf" in sys.argv else zl_am() if "--zlam" in sys.argv else loc_main() if "--loc" in sys.argv or "--gts" in sys.argv else main()
