"""PREREG_CONJ: conjoin the two translations the ladder already paid for. When both the trained quick translation (`lf`) and the thinking
translation (`gtrt`) allow two or more solutions, each one usually misses or weakens a clue rather than misreads one (idea 35: 155 of 170
several-solution thinking translations have no misread clue), so the right grid is in both solution sets. Two translators weaken different clues,
so the grids both allow may be exactly one: that grid is accepted with no new tokens, in place of the thinking step (the ladder's costliest step,
which fails mostly at search on large grids, idea 34). The puzzle's one-solution guarantee is the free check, as for every other step.

Usage:  sbatch -p cpu-max16,cpu-max10,cpu-max24 -q nogpu --gres=none poc/slurm/job.sh '$P poc/gp_conj.py run'
          lists up to CAP solutions of every count-2 lf and gtrt program of seeds 4-9 under GP_SOLVE (sandboxed), and writes
          results/{gp,lgp}_conj_s49.jsonl: per puzzle-seed with both steps at count 2, each set's size (-1 above CAP), whether gold is in it,
          and the grids in both sets (canonical: the puzzle's own category and value names, compared as gp_score compares them).
        python poc/gp_conj.py eval    ladder lf -> gtrt -> (both allow exactly one grid: accept it) -> think, minus the ladder without that step.
"""
import json
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
SD = [4, 5, 6, 7, 8, 9]
CAP = 20000
U = lambda e, t: 100 * e - 0.5 * t / 1000


def canon(g, r):
    """The grid as a tuple over the puzzle's categories of normalised values (gp_score's normalisation); None if a category is missing."""
    ck = lambda a: re.sub(r"[^a-z0-9]", "", str(a).lower()).rstrip("s")
    num = lambda x: re.search(r"\d[\d:.]*", str(x).replace(",", ""))
    vk = lambda x, vals: num(x).group() if vals and all(num(y) for y in vals) and num(x) else re.sub(r"[^a-z0-9]", "", str(x).lower())
    got = {ck(k): v for k, v in g.items() if isinstance(v, list)}
    out = []
    for a, vals in sorted(r["cats"][1:], key=lambda t: ck(t[0])):
        if ck(a) not in got:
            return None
        out.append(tuple(vk(x, vals) for x in got[ck(a)]))
    return tuple(out)


def rows(s, src):
    from grid_score import score
    data = os.environ.get("POC_DATA", os.path.join(RES, "..", "..", "nlp_data"))
    PZ = {r["id"]: r for r in map(json.loads, open(os.path.join(data, src, "grid.jsonl")))}
    R = {}
    for arm, tags in [("gtrt", ["q8b"]), ("think", ["q8b"]), ("lf", ["q8bgrllf0", "q8bgrllf1"])]:
        for tag in tags:
            for sd in SD:
                f = os.path.join(RES, f"{s}_{tag}_{'gtr' if arm == 'lf' else arm}_s{sd}.jsonl")
                for x in map(json.loads, open(f)) if os.path.exists(f) else []:
                    R[(arm, x["id"], sd)] = {**x, "exact": score(x.get("grid"), PZ[x["id"]])[0]}
    keys = sorted({(i, sd) for (_, i, sd) in R if all((a, i, sd) in R for a in ["lf", "gtrt", "think"])})
    return PZ, R, keys


def run_main():
    from concurrent.futures import ThreadPoolExecutor
    from sandbox import run_python
    from run_zebra import GP_SOLVE
    for s, src in [("gp", "gridpuzzle"), ("lgp", "lgp")]:
        PZ, R, keys = rows(s, src)
        todo = [(i, sd) for i, sd in keys if R[("lf", i, sd)]["count"] >= 2 and R[("gtrt", i, sd)]["count"] >= 2]

        def sols(x, r):
            (first, fv) = r["cats"][0]
            solve = GP_SOLVE.replace("__FIRST__", json.dumps(fv)).replace("__FNAME__", json.dumps(first))
            solve = solve.replace("if len(self.s) >= 2:", f"if len(self.s) > {CAP}:").replace('print(json.dumps({"count": len(cb.s), "grid": g}))', "")
            solve += "\ngs = [{a: [x for _, x in sorted((t[f'{a}:{x}'], x) for x in vals)] for a, vals in groups.items()} for t in cb.s]\nprint(json.dumps({'count': len(cb.s), 'grids': gs}))\n"
            res = run_python(x["code"] + "\n" + solve, "", timeout=300, mem_bytes=8 << 30)
            try:
                out = json.loads(res.stdout.strip().splitlines()[-1])
            except (AttributeError, IndexError, ValueError):
                return None
            if out["count"] > CAP:
                return None
            c = {canon(g, r) for g in out["grids"]}
            return None if None in c else c

        def one(k):
            i, sd = k
            r = PZ[i]
            gold = canon(r["gold"], r)
            a, b = sols(R[("lf", i, sd)], r), sols(R[("gtrt", i, sd)], r)
            both = a & b if a is not None and b is not None else None
            return {"id": i, "seed": sd, "size": r.get("size", R[("lf", i, sd)]["size"]), "n_lf": -1 if a is None else len(a), "n_gtrt": -1 if b is None else len(b),
                    "gold_lf": a is not None and gold in a, "gold_gtrt": b is not None and gold in b, "n_both": -1 if both is None else len(both),
                    "gold_both": both is not None and gold in both, "both": [list(map(list, g)) for g in both][:16] if both else []}

        with ThreadPoolExecutor(int(os.environ.get("NW", "8"))) as ex, open(f"{RES}/{s}_conj_s49.jsonl", "w") as f:
            out = []
            for row in ex.map(one, todo):
                out.append(row); f.write(json.dumps(row) + "\n"); f.flush()
        print(s, f"puzzle-seeds with both at count 2: {len(out)}; exactly one shared grid {sum(x['n_both'] == 1 for x in out)}, "
                 f"of them right {sum(x['n_both'] == 1 and x['gold_both'] for x in out)}; above cap lf {sum(x['n_lf'] < 0 for x in out)} gtrt {sum(x['n_gtrt'] < 0 for x in out)}", flush=True)


def eval_main():
    for s, src in [("gp", "gridpuzzle"), ("lgp", "lgp")]:
        PZ, R, keys = rows(s, src)
        C = {(x["id"], x["seed"]): x for x in map(json.loads, open(f"{RES}/{s}_conj_s49.jsonl"))}

        def lad(i, sd, conj):
            tok = 0
            for arm in ["lf", "gtrt"]:
                r = R[(arm, i, sd)]; tok += r["tokens"]
                if r["count"] == 1:
                    return r["exact"], tok, arm
            c = C.get((i, sd))
            if conj and c and c["n_both"] == 1:
                return c["gold_both"], tok, "conj"
            r = R[("think", i, sd)]
            return r["exact"], tok + r["tokens"], "think"

        miss = [k for k in keys if R[("lf",) + k]["count"] >= 2 and R[("gtrt",) + k]["count"] >= 2 and k not in C]
        assert not miss, f"{len(miss)} puzzle-seeds with both at count 2 have no conj row"
        ids = sorted({i for i, _ in keys})
        per = {}
        for i in ids:
            ks = [k for k in keys if k[0] == i]
            per[i] = [sum(U(*lad(*k, c)[:2]) for k in ks) / len(ks) for c in (False, True)]
        for c, name in [(False, "ladder lf -> gtrt -> think"), (True, "same with the conjunction step")]:
            L = [lad(*k, c) for k in keys]
            print(f"{s} {name}: {100 * sum(e for e, _, _ in L) / len(L):.1f}% at {sum(t for _, t, _ in L) / len(L) / 1000:.2f} ktok, "
                  f"utility {sum(U(e, t) for e, t, _ in L) / len(L):.1f}  ({len(L)} puzzle-seeds)")
        acc = [(lad(*k, True)[0], R[("think",) + k]["exact"]) for k in keys if lad(*k, True)[2] == "conj"]
        X = list(C.values())
        print(f"  both at count 2: {len(X)}; gold in lf set {sum(x['gold_lf'] for x in X)}, in gtrt set {sum(x['gold_gtrt'] for x in X)}, in both {sum(x['gold_both'] for x in X)}; "
              f"above cap lf {sum(x['n_lf'] < 0 for x in X)}, gtrt {sum(x['n_gtrt'] < 0 for x in X)}; shared grids 0: {sum(x['n_both'] == 0 for x in X)}, "
              f"1: {sum(x['n_both'] == 1 for x in X)}, 2+: {sum(x['n_both'] >= 2 for x in X)}")
        if acc:
            print(f"  CONJ-P2 precision of the accepted grid: {sum(a for a, _ in acc)}/{len(acc)}; thinking right on the same puzzle-seeds {sum(b for _, b in acc)}")
        rng = random.Random(0)
        d = [per[i][1] - per[i][0] for i in ids]
        bs = sorted(sum(d[rng.randrange(len(d))] for _ in d) / len(d) for _ in range(10000))
        print(f"  CONJ-P1 with - without: {sum(d) / len(d):+.1f} [{bs[250]:+.1f}, {bs[9749]:+.1f}] over {len(ids)} puzzles")


if __name__ == "__main__":
    run_main() if sys.argv[1] == "run" else eval_main()
