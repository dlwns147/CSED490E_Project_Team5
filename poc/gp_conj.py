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


def why_main():
    """Mechanism of CONJ-P1's failure (read after the result): for each bucket puzzle-seed with gold in both sets, a right count-1 program of the
    same puzzle from any stored test run is the reference; each non-gold shared grid is tested against each reference expression (sandboxed), and
    the expressions it breaks are the constraint both translators dropped. Writes results/gp_conj_why.jsonl."""
    import glob
    from concurrent.futures import ThreadPoolExecutor
    from sandbox import run_python
    from run_zebra import GP_SOLVE
    PZ, R, keys = rows("gp", "gridpuzzle")
    X = [x for x in map(json.loads, open(f"{RES}/gp_conj_s49.jsonl")) if x["gold_both"] and x["n_both"] >= 2]
    need = {x["id"] for x in X}
    ref = {}
    for f in sorted(glob.glob(f"{RES}/gp_*_gtr*_s*.jsonl")):
        if "_dev" in f or not re.search(r"_gtrt?_s\d+\.jsonl$", f):
            continue
        for ln in open(f):
            try:
                y = json.loads(ln)
            except ValueError:
                continue
            if y.get("id") in need and y.get("count") == 1 and y.get("exact") and y["id"] not in ref:
                ref[y["id"]] = y["code"]
    # GP_SOLVE up to the solver call, with each clue's allowed tuples kept instead of added; then each grid is tested clue by clue
    body = GP_SOLVE[:GP_SOLVE.index("s = cp_model.CpSolver()")].replace("    m.AddAllowedAssignments([v[_res(k)] for k in keys], ok)",
                                                                           "    _CL.append(([_res(k) for k in keys], set(ok)))")
    body = body.replace("for c in clues:", "_CL = []\nfor c in clues:")
    test = """
import sys
_nk = lambda x, vals: re.search(r"\\d[\\d:.]*", str(x).replace(",", "")).group() if all(re.search(r"\\d", str(y)) for y in vals) else re.sub(r"[^a-z0-9]", "", str(x).lower())
_ck = lambda a: re.sub(r"[^a-z0-9]", "", str(a).lower()).rstrip("s")
out = []
for G in GRIDS:   # G: {canonical category: [canonical values by position]}
    pos = {}
    for a, vals in groups.items():
        row = G.get(_ck(a))
        for x in vals:
            pos[a + ":" + x] = row.index(_nk(x, vals)) + 1 if row and _nk(x, vals) in row else None
    for k, x in enumerate(FIRST, 1):
        pos.setdefault(FNAME + ":" + str(x), k)
    out.append([i for i, (ks, ok) in enumerate(_CL) if tuple(pos.get(k) for k in ks) not in ok])
print(json.dumps(out))
"""
    def one(x):
        r = PZ[x["id"]]
        if x["id"] not in ref:
            return {**x, "ref": None}
        (first, fv), cats = r["cats"][0], sorted(r["cats"][1:], key=lambda t: t[0])
        ck = lambda a: re.sub(r"[^a-z0-9]", "", str(a).lower()).rstrip("s")
        cs = sorted((ck(a) for a, _ in r["cats"][1:]))
        gold = canon(r["gold"], r)
        sib = [g for g in x["both"] if tuple(map(tuple, g)) != gold]
        grids = [{c: list(g[k]) for k, c in enumerate(cs)} for g in sib]
        solve = body.replace("__FIRST__", json.dumps(fv)).replace("__FNAME__", json.dumps(first))
        res = run_python(ref[x["id"]] + "\n" + solve + "\nGRIDS = " + json.dumps(grids) + "\n" + test, "", timeout=120, mem_bytes=4 << 30)
        try:
            v = json.loads(res.stdout.strip().splitlines()[-1])
        except (AttributeError, IndexError, ValueError):
            return {**x, "ref": "fail", "err": (res.stderr or "")[-300:]}
        return {**x, "ref": ref[x["id"]], "broken": v}
    with ThreadPoolExecutor(int(os.environ.get("NW", "4"))) as ex, open(f"{RES}/gp_conj_why.jsonl", "w") as f:
        for row in ex.map(one, X):
            f.write(json.dumps(row) + "\n")
    print("why rows", len(X), "with a reference", sum(x["id"] in ref for x in X), flush=True)


def distinct_closure(code, values):
    """The implicature the mechanism run found both translators drop: entities a disjunctive or negative clue names, and that no reading of the
    clue equates, are different entities ("X is either A or B" -> A != B; "of A and B, one is C and the other D" -> A != B, C != D; "neither A nor
    B is C" -> A != B). Applied to expressions that are an `or`, an `in`, an exclusive or, or an `and` of `!=`; entities are p['...'] keys and
    numbers of the first category. Returns the extra expressions (pure text transformation, nothing is executed)."""
    import ast
    import itertools
    m = None
    for n in ast.parse(code).body:
        if isinstance(n, ast.Assign) and any(isinstance(a, ast.Name) and a.id == "clues" for a in n.targets) and isinstance(n.value, ast.List):
            m = n.value
    if m is None:
        return []
    ent = lambda t: ("k", t.slice.value) if isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant) and isinstance(t.slice.value, str) else \
        ("n", t.value) if isinstance(t, ast.Constant) and isinstance(t.value, (int, float)) and t.value in values else None
    out = []
    for e in m.elts:
        if not (isinstance(e, ast.Constant) and isinstance(e.value, str)):
            continue
        try:
            t = ast.parse(e.value, mode="eval").body
        except SyntaxError:
            continue
        cmp = [c for c in ast.walk(t) if isinstance(c, ast.Compare)]
        xor = any(isinstance(c.ops[0], ast.NotEq) and all(isinstance(x, ast.Compare) for x in [c.left] + c.comparators) for c in cmp) or \
            any(isinstance(b, ast.BinOp) and isinstance(b.op, ast.BitXor) for b in ast.walk(t))
        neg = isinstance(t, ast.BoolOp) and isinstance(t.op, ast.And) and all(isinstance(v, ast.Compare) and isinstance(v.ops[0], ast.NotEq) for v in t.values)
        if not (xor or neg or (isinstance(t, ast.BoolOp) and isinstance(t.op, ast.Or)) or (isinstance(t, ast.Compare) and isinstance(t.ops[0], ast.In))):
            continue
        E, eq = set(), set()
        for c in cmp:
            for x in [c.left] + c.comparators:
                for y in ([x] + (list(x.elts) if isinstance(x, (ast.Tuple, ast.List, ast.Set)) else [])):
                    if ent(y):
                        E.add(ent(y))
            if isinstance(c.ops[0], (ast.Eq, ast.In)):
                L = [ent(c.left)]
                R = [ent(y) for y in (c.comparators[0].elts if isinstance(c.comparators[0], (ast.Tuple, ast.List, ast.Set)) else [c.comparators[0]])]
                eq |= {frozenset((a, b)) for a in L for b in R if a and b}
        for a, b in itertools.combinations(sorted(E, key=str), 2):
            if frozenset((a, b)) in eq or (a[0] == "n" and b[0] == "n") or (a[0] == b[0] == "k" and a[1].split(":")[0] == b[1].split(":")[0]):
                continue
            s = lambda z: f"p[{z[1]!r}]" if z[0] == "k" else repr(z[1])
            out.append(f"{s(a)} != {s(b)}")
    return sorted(set(out))


def dclc_main():
    """PREREG_GPF part 2 (DCLC): on the held-out ladders H1-H4 (quick gtr -> gtrt -> think, closure on any step with two or more solutions), a
    one-solution quick program whose closure leaves no solution is treated as a failed step (results/<s>_dcl1_<H>.jsonl from `dcl1`)."""
    out = {}
    for s in ["gp", "lgp"]:
        per, flags = {}, []
        for h in ["H1", "H2", "H3", "H4"]:
            PZ, R, F, keys = dcl_rows(s, "gridpuzzle" if s == "gp" else s, h)
            C = {(x["arm"], x["tag"], x["file_seed"], x["id"]): x for x in map(json.loads, open(f"{RES}/{s}_dcl_{h}.jsonl"))}
            C1 = {(x["arm"], x["tag"], x["file_seed"], x["id"]): x for x in map(json.loads, open(f"{RES}/{s}_dcl1_{h}.jsonl"))}

            def lad(i, sd, chk):
                tok = 0
                for a in ["gtr", "gtrt"]:
                    r = R[(a, i, sd)]; tok += r["tokens"]
                    cnt, ex = r["count"], r["exact"]
                    if cnt >= 2:
                        c = C[(a,) + F[(a, i, sd)] + (i,)]
                        cnt, ex = c["count"], c["exact"]
                    elif chk and cnt == 1 and a == "gtr" and C1.get((a,) + F[(a, i, sd)] + (i,), {}).get("count") == 0:
                        cnt = 0
                    if cnt == 1:
                        return ex, tok
                r = R[("think", i, sd)]
                return r["exact"], tok + r["tokens"]
            L0, L1 = [lad(*k, False) for k in keys], [lad(*k, True) for k in keys]
            fl = [R[("gtr",) + k]["exact"] for k in keys if R[("gtr",) + k]["count"] == 1 and C1.get(("gtr",) + F[("gtr",) + k] + (k[0],), {}).get("count") == 0]
            flags += fl
            d = {}
            for k, a, b in zip(keys, L0, L1):
                d.setdefault(k[0], []).append(U(*b) - U(*a))
            for i, v in d.items():
                per.setdefault(i, []).append(sum(v) / len(v))
            rng = random.Random(0)
            dv = [sum(v) / len(v) for v in d.values()]
            bs = sorted(sum(dv[rng.randrange(len(dv))] for _ in dv) / len(dv) for _ in range(10000))
            print(f"{h} {s}: no check {100 * sum(e for e, _ in L0) / len(L0):.1f}% at {sum(t for _, t in L0) / len(L0) / 1000:.2f}k, "
                  f"check {100 * sum(e for e, _ in L1) / len(L1):.1f}% at {sum(t for _, t in L1) / len(L1) / 1000:.2f}k; flags {len(fl)} "
                  f"({len(fl) - sum(fl)} wrong); check - no check {sum(dv) / len(dv):+.2f} [{bs[250]:+.2f}, {bs[9749]:+.2f}]")
        dv = [sum(v) / len(v) for v in per.values()]   # each puzzle's mean over the model-seeds that ran it
        rng = random.Random(0)
        bs = sorted(sum(dv[rng.randrange(len(dv))] for _ in dv) / len(dv) for _ in range(10000))
        out[s] = (sum(dv) / len(dv), bs[250], bs[9749])
        print(f"   {s} pooled H1-H4 ({len(dv)} puzzles): check - no check {out[s][0]:+.2f} [{out[s][1]:+.2f}, {out[s][2]:+.2f}]; "
              f"flags {len(flags)}, wrong {len(flags) - sum(flags)}")
    print(f"DCLC-P1 (GridPuzzle lower bound > 0): {out['gp'][1] > 0}; DCLC-P2 (Mitra-Baral lower bound > -1.0): {out['lgp'][1] > -1.0}")


def close_main():
    """Exploratory (PREREG_CONJ, mechanism): every lf and gtrt program of seeds 4-9, re-counted with distinct_closure's expressions added
    (sandboxed, GP_SOLVE unchanged). Writes results/{gp,lgp}_conj_close.jsonl: arm, id, seed, count and exactness before and after."""
    from concurrent.futures import ThreadPoolExecutor
    from sandbox import run_python
    from run_zebra import GP_SOLVE, gp_score
    for s, src in [("gp", "gridpuzzle"), ("lgp", "lgp")]:
        PZ, R, keys = rows(s, src)
        todo = [(a, i, sd) for i, sd in keys for a in ["lf", "gtrt"]]

        def one(k):
            a, i, sd = k
            x, r = R[k], PZ[i]
            (first, fv) = r["cats"][0]
            row = {"arm": a, "id": i, "seed": sd, "count0": x["count"], "exact0": x["exact"]}
            vm = re.search(r"^VALUES\s*=\s*(\[[^\]]*\])", x.get("code") or "", re.M)
            try:
                values = set(json.loads(vm.group(1))) if vm else set()
                extra = distinct_closure(x["code"], values)
            except Exception:
                extra = None
            if not extra:
                return {**row, "n_extra": 0 if extra == [] else -1, "count": x["count"], "exact": x["exact"]}
            solve = GP_SOLVE.replace("__FIRST__", json.dumps(fv)).replace("__FNAME__", json.dumps(first))
            res = run_python(x["code"] + "\nclues = list(clues) + " + json.dumps(extra) + "\n" + solve, "", timeout=60, mem_bytes=4 << 30)
            try:
                out = json.loads(res.stdout.strip().splitlines()[-1])
            except (AttributeError, IndexError, ValueError):
                out = {"count": -1, "grid": {}}
            return {**row, "n_extra": len(extra), "extra": extra, "count": out["count"], "exact": out["count"] == 1 and gp_score(out["grid"], r)[0]}

        with ThreadPoolExecutor(int(os.environ.get("NW", "4"))) as ex, open(f"{RES}/{s}_conj_close.jsonl", "w") as f:
            for row in ex.map(one, todo):
                f.write(json.dumps(row) + "\n")
        print(s, "closure rows", len(todo), flush=True)


# PREREG_DCL held-out ladders: quick gtr -> gtrt -> think; (tag, seed) per step, None = the puzzle-seed's own seed
DCL = {"H1": (["gp", "lgp"], [1, 2, 3], ("q8b", None), ("q8b", None), ("q8b", None)),
       "H2": (["gp", "lgp"], [1, 2, 3, 4, 5, 6], ("q32a", None), ("q32a", None), ("q32a", None)),
       "H3": (["gp", "lgp"], [1, 2, 3, 4, 5, 6], ("oss20", None), ("oss20", None), ("oss20", None)),
       "H4": (["gp", "lgp"], [1, 2, 3, 4, 5, 6], ("oss120", None), ("oss120", None), ("oss120", None)),
       "H5": (["gp"], [1, 2, 3], ("q8bh_dev", None), ("q8bh_dev", 1), ("q8b_dev", 1)),
       # PREREG_PEERT: closure rows for gpt-oss-20b's quick translations of seeds 7-9 (only its gtr rows are used)
       "P79": (["gp", "lgp"], [7, 8, 9], ("oss20", None), ("q8b", None), ("q8b", None)),
       "Q79": (["gp", "lgp"], [7, 8, 9], ("oss120", None), ("q8b", None), ("q8b", None))}   # PREREG_PEERT addendum A


def dcl_rows(s, src, h):
    from grid_score import score
    data = os.environ.get("POC_DATA", os.path.join(RES, "..", "..", "nlp_data"))
    PZ = {r["id"]: r for r in map(json.loads, open(os.path.join(data, src, "grid.jsonl")))}
    _, seeds, *steps = DCL[h]
    R, F = {}, {}
    for arm, (tag, fix) in zip(["gtr", "gtrt", "think"], steps):
        p2 = os.path.join(RES, f"{s}_{tag}_score2.json")   # rows written before grids were kept: scoring v2 from poc/gp_rescore.py
        S2 = json.load(open(p2)) if os.path.exists(p2) else {}
        for sd in seeds:
            f = os.path.join(RES, f"{s}_{tag}_{arm}_s{fix or sd}.jsonl")
            for x in map(json.loads, open(f)) if os.path.exists(f) else []:
                k2 = f"{arm}|{x['id']}|{fix or sd}"
                if "grid" not in x and k2 not in S2:
                    continue
                R[(arm, x["id"], sd)] = {**x, "exact": S2[k2][0] if "grid" not in x else score(x.get("grid"), PZ[x["id"]])[0]}
                F[(arm, x["id"], sd)] = (tag, fix or sd)
    keys = sorted({(i, sd) for (_, i, sd) in R if all((a, i, sd) in R for a in ["gtr", "gtrt", "think"])})
    return PZ, R, F, keys


def dcl_main():
    from concurrent.futures import ThreadPoolExecutor
    from sandbox import run_python
    from run_zebra import GP_SOLVE, gp_score
    for h, (sets, *_) in DCL.items():
        if len(sys.argv) > 2 and h not in sys.argv[2].split(","):
            continue
        for s in sets:
            PZ, R, F, keys = dcl_rows(s, "gridpuzzle" if s == "gp" else s, h)
            c1 = sys.argv[1] == "dcl1"   # PREREG_GPF part 2 (DCLC): the one-solution quick programs instead
            todo = sorted({(a,) + F[(a,) + k] + (k[0],) for k in keys for a in ["gtr", "gtrt"]
                           if (a == "gtr" and R[(a,) + k]["count"] == 1 if c1 else R[(a,) + k]["count"] >= 2)})

            def one(t):
                a, tag, sd, i = t
                x = next(R[(a, i, s2)] for s2 in DCL[h][1] if F.get((a, i, s2)) == (tag, sd))
                r = PZ[i]
                (first, fv) = r["cats"][0]
                vm = re.search(r"^VALUES\s*=\s*(\[[^\]]*\])", x.get("code") or "", re.M)
                try:
                    extra = distinct_closure(x["code"], set(json.loads(vm.group(1))) if vm else set())
                except Exception:
                    extra = None
                row = {"arm": a, "tag": tag, "file_seed": sd, "id": i, "n_extra": -1 if extra is None else len(extra)}
                if not extra:
                    return {**row, "count": x["count"], "exact": False}
                solve = GP_SOLVE.replace("__FIRST__", json.dumps(fv)).replace("__FNAME__", json.dumps(first))
                res = run_python(x["code"] + "\nclues = list(clues) + " + json.dumps(extra) + "\n" + solve, "", timeout=60, mem_bytes=4 << 30)
                try:
                    out = json.loads(res.stdout.strip().splitlines()[-1])
                except (AttributeError, IndexError, ValueError):
                    out = {"count": -1, "grid": {}}
                return {**row, "count": out["count"], "exact": out["count"] == 1 and gp_score(out["grid"], r)[0]}

            with ThreadPoolExecutor(int(os.environ.get("NW", "4"))) as ex, open(f"{RES}/{s}_dcl{'1' if c1 else ''}_{h}.jsonl", "w") as f:
                for row in ex.map(one, todo):
                    f.write(json.dumps(row) + "\n")
            print(h, s, "closure rows", len(todo), flush=True)


def dcleval_main():
    for h, (sets, *_) in DCL.items():
        for s in sets:
            PZ, R, F, keys = dcl_rows(s, "gridpuzzle" if s == "gp" else s, h)
            if not keys:
                print(h, s, "no scored puzzle-seeds (rows without grids need poc/gp_rescore.py)")
                continue
            C = {(x["arm"], x["tag"], x["file_seed"], x["id"]): x for x in map(json.loads, open(f"{RES}/{s}_dcl_{h}.jsonl"))}

            def lad(i, sd, cl):
                tok = 0
                for a in ["gtr", "gtrt"]:
                    r = R[(a, i, sd)]; tok += r["tokens"]
                    cnt, ex = r["count"], r["exact"]
                    if cl and cnt >= 2:
                        c = C[(a,) + F[(a, i, sd)] + (i,)]
                        cnt, ex = c["count"], c["exact"]
                    if cnt == 1:
                        return ex, tok
                r = R[("think", i, sd)]
                return r["exact"], tok + r["tokens"]

            ids = sorted({i for i, _ in keys})
            out = []
            for name, f in [("plain ladder", lambda k: lad(*k, False)), ("closure ladder", lambda k: lad(*k, True)),
                            ("thinking", lambda k: (R[("think",) + k]["exact"], R[("think",) + k]["tokens"]))]:
                L = [f(k) for k in keys]
                out.append(f"{name} {100 * sum(e for e, _ in L) / len(L):.1f}% at {sum(t for _, t in L) / len(L) / 1000:.2f} ktok, U {sum(U(*x) for x in L) / len(L):.1f}")
            X = [c for c in C.values() if c["count"] == 1]
            print(f"{h} {s} ({len(keys)} puzzle-seeds, {len(ids)} puzzles): " + "; ".join(out))
            print(f"   DCL-P3 count-2 programs settled by the closure: {sum(c['exact'] for c in X)}/{len(X)} right (of {len(C)} count-2 programs)")
            rng = random.Random(0)
            for name, b in [("closure - plain", False), ("closure - thinking", True)]:
                d = []
                for i in ids:
                    ks = [k for k in keys if k[0] == i]
                    base = [(R[("think",) + k]["exact"], R[("think",) + k]["tokens"]) if b else lad(*k, False) for k in ks]
                    d.append(sum(U(*lad(*k, True)) - U(*y) for k, y in zip(ks, base)) / len(ks))
                bs = sorted(sum(d[rng.randrange(len(d))] for _ in d) / len(d) for _ in range(10000))
                print(f"   {name}: {sum(d) / len(d):+.1f} [{bs[250]:+.1f}, {bs[9749]:+.1f}]")


def peert_main():
    """PREREG_PEERT: ladder lf -> gpt-oss-20b quick translation -> gtrt -> think, minus lf -> gtrt -> think; closure on every step with two or
    more solutions (lf / gtrt: results/<s>_conj_close.jsonl, the peer: results/<s>_dcl_P79.jsonl); seeds 7-9 (decides) or --seeds 4,5,6."""
    from grid_score import score
    sds = [int(x) for x in (sys.argv[sys.argv.index("--seeds") + 1] if "--seeds" in sys.argv else "7,8,9").split(",")]
    for s, src in [("gp", "gridpuzzle"), ("lgp", "lgp")]:
        PZ, R, keys = rows(s, src)
        C = {(x["arm"], x["id"], x["seed"]): x for x in map(json.loads, open(f"{RES}/{s}_conj_close.jsonl"))}
        tag = sys.argv[sys.argv.index("--peer") + 1] if "--peer" in sys.argv else "oss20"   # addendum A: --peer oss120
        p2 = f"{RES}/{s}_{tag}_score2.json"
        S2 = json.load(open(p2)) if os.path.exists(p2) else {}
        P = {}
        for sd in sds:
            f = f"{RES}/{s}_{tag}_gtr_s{sd}.jsonl"
            for x in map(json.loads, open(f)) if os.path.exists(f) else []:
                if "grid" in x or f"gtr|{x['id']}|{sd}" in S2:
                    P[(x["id"], sd)] = {**x, "exact": score(x["grid"], PZ[x["id"]])[0] if "grid" in x else S2[f"gtr|{x['id']}|{sd}"][0]}
        D = {}
        for h in ["P79", "H3", "Q79", "H4"]:
            f = f"{RES}/{s}_dcl_{h}.jsonl"
            for x in map(json.loads, open(f)) if os.path.exists(f) else []:
                if x["arm"] == "gtr" and x["tag"] == tag:
                    D[(x["id"], x["file_seed"])] = x
        ks = [k for k in keys if k[1] in sds and k in P]

        def step(r, c):
            return (c["count"], c["exact"]) if r["count"] >= 2 and c else (r["count"], r["exact"])

        def lad(i, sd, peer):
            tok = 0
            for a in ["lf", "peer", "gtrt"]:
                if a == "peer" and not peer:
                    continue
                r = P[(i, sd)] if a == "peer" else R[(a, i, sd)]
                tok += r["tokens"]
                cnt, ex = step(r, D.get((i, sd)) if a == "peer" else C.get((a, i, sd)))
                if cnt == 1:
                    return ex, tok, a
            r = R[("think", i, sd)]
            return r["exact"], tok + r["tokens"], "think"

        ids = sorted({i for i, _ in ks})
        for peer in (False, True):
            L = [lad(*k, peer) for k in ks]
            acc = [e for e, _, a in L if a == "peer"]
            print(f"{s} {'with the peer step' if peer else 'lf -> gtrt -> think'} ({len(ks)} puzzle-seeds, seeds {sds}): "
                  f"{100 * sum(e for e, _, _ in L) / len(L):.1f}% at {sum(t for _, t, _ in L) / len(L) / 1000:.2f} ktok, U {sum(U(e, t) for e, t, _ in L) / len(L):.1f}"
                  + (f"; PEERT-P2 peer accepted {sum(acc)}/{len(acc)} right" if peer else ""))
        rng = random.Random(0)
        d = []
        for i in ids:
            kk = [k for k in ks if k[0] == i]
            d.append(sum(U(*lad(*k, True)[:2]) - U(*lad(*k, False)[:2]) for k in kk) / len(kk))
        bs = sorted(sum(d[rng.randrange(len(d))] for _ in d) / len(d) for _ in range(10000))
        print(f"   PEERT-P1 with - without: {sum(d) / len(d):+.1f} [{bs[250]:+.1f}, {bs[9749]:+.1f}] over {len(ids)} puzzles")


def peertrip_main():
    """PREREG_PEERT addendum B: trip planning, ladder main trc -> peer trc -> main trct -> main think minus main trc -> trct -> think
    (results/np_<tag>_<arm>_s<seed>.jsonl; no closure). usage: peertrip [--main q32] [--peer oss120] [--seeds 4,5,6]"""
    arg = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
    main, peer, sds = arg("--main", "q32"), arg("--peer", "oss120"), [int(x) for x in arg("--seeds", "4,5,6").split(",")]
    L = lambda tag, arm, sd: {x["id"]: x for x in map(json.loads, open(f"{RES}/np_{tag}_{arm}_s{sd}.jsonl"))} if os.path.exists(f"{RES}/np_{tag}_{arm}_s{sd}.jsonl") else {}
    res = []
    for sd in sds:
        M = {a: L(main, a, sd) for a in ["trc", "trct", "think"]}
        P = L(peer, "trc", sd)
        for i in M["think"]:
            if not all(i in M[a] for a in M) or i not in P:
                continue

            def lad(pe):
                tok = 0
                for a in (["trc", "peer", "trct"] if pe else ["trc", "trct"]):
                    r = P[i] if a == "peer" else M[a][i]
                    tok += r["tokens"]
                    if r["count"] == 1:
                        return r["exact"], tok
                r = M["think"][i]
                return r["exact"], tok + r["tokens"]
            res.append((i, lad(False), lad(True), (M["think"][i]["exact"], M["think"][i]["tokens"])))
    ids = sorted({i for i, *_ in res})
    for k, name in [(1, "without the peer"), (2, "with the peer"), (3, "thinking only")]:
        print(f"trips {main} <- {peer}, seeds {sds}, {name}: {100 * sum(r[k][0] for r in res) / len(res):.1f}% at {sum(r[k][1] for r in res) / len(res) / 1000:.2f} ktok ({len(res)} problem-seeds)")
    rng = random.Random(0)
    for a, b, name in [(2, 1, "PEERT-B1 with - without"), (2, 3, "with the peer - thinking")]:
        d = [sum(U(*r[a]) - U(*r[b]) for r in res if r[0] == i) / sum(r[0] == i for r in res) for i in ids]
        bs = sorted(sum(d[rng.randrange(len(d))] for _ in d) / len(d) for _ in range(10000))
        print(f"   {name}: {sum(d) / len(d):+.1f} [{bs[250]:+.1f}, {bs[9749]:+.1f}] over {len(ids)} problems")


if __name__ == "__main__":
    {"run": run_main, "why": why_main, "close": close_main, "dcl": dcl_main, "dcleval": dcleval_main, "peert": peert_main, "peertrip": peertrip_main, "dcl1": dcl_main, "dclc": dclc_main}.get(sys.argv[1], eval_main)()
