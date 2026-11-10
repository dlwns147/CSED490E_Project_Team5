"""Idea 38, offline: choose one reading per clue so that the whole program has exactly one solution (joint choice), on the readings gts sampled.

Usage (container, CPU): $P poc/gp_joint.py [tag q8bh] [--dev]
Reads results/{gp,lgp}_<tag>[_dev]_gts_s{1,2,3}.jsonl (arm gts, run_zebra.py: the per-clue search of Schrader et al. 2512.17093, greedy fewest
solutions) and writes the same rows as arm gtsj (results/{gp,lgp}_<tag>[_dev]_gtsj_s{sd}.jsonl): same tokens (no model call), count / exact / grid
from the joint choice. No new sample is drawn.

Readings of clue j = every expression list gts sampled for it (all its steps, back steps included), merged when their truth tables are equal; a
reading's vote is how many samples gave it. A clue may also be left out ("skip"), as gts does when nothing fits.
Choice (derived from the puzzle's two guarantees, every clue holds and exactly one grid fits them): among selections with exactly one solution,
first the fewest skips, then the largest product of vote shares (each clue's samples treated as draws from the model's reading distribution).
Search: CP-SAT picks the best selection S with a solution x; a second model asks for another solution x' of S; if one exists, the cut "some selected
reading rules out x or x'" removes every selection that keeps both (each such selection has two solutions), and the loop repeats (at most 300 rounds).
Also per run, the ceiling: the same search over gold-true readings only (does a selection exist whose one solution is gold).
"""
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
from run_zebra import GP_SOLVE, RES, gp_score  # noqa: E402
from sandbox import run_python  # noqa: E402

JOINT = GP_SOLVE[:GP_SOLVE.index("for c in clues:")] + """
import math
def _tab(c):
    c = ast.unparse(ast.fix_missing_locations(_S().visit(ast.parse(c, mode="eval"))))
    keys = sorted({t.slice.value for t in ast.walk(ast.parse(c, mode="eval")) if isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant) and isinstance(t.slice.value, str) and ":" in t.slice.value})
    assert keys and all(_res(k) for k in keys)
    code = compile(c, "clue", "eval")
    ok = [t for t in itertools.product(range(1, n + 1), repeat=len(keys)) if eval(code, {"abs": abs, "min": min, "max": max, "V": V, "at": at}, {"p": dict(zip(keys, (VALUES[k - 1] for k in t)))})]
    return tuple(_res(k) for k in keys), tuple(ok)
R = []   # per clue: [[votes, tables], ...]
for cs in CANDS:
    rd = {}
    for nw in cs:
        try:
            tabs = [_tab(c) for c in nw]
        except Exception:
            continue
        sig = tuple(sorted(tabs))
        rd.setdefault(sig, [0, tabs])[0] += 1
    R.append(list(rd.values()))
holds = lambda tabs, x: all(tuple(x[k] for k in ks) in set(ok) for ks, ok in tabs)
GX = None
if GOLDV is not None:
    GX = {}
    for k in v:
        a, y = k.split(":", 1)
        GX[k] = [str(z) for z in FIRST].index(y) + 1 if a == FNAME and y in [str(z) for z in FIRST] else GOLDV.get(_nv(y))
    if None in GX.values():
        GX = None
def search(R):
    cuts, it = [], 0
    while it < 300:
        it += 1
        M, X = cp_model.CpModel(), {}
        for a, vals in groups.items():
            for y in vals:
                X[f"{a}:{y}"] = M.NewIntVar(1, n, f"{a}:{y}")
            M.AddAllDifferent([X[f"{a}:{y}"] for y in vals])
        for k, y in enumerate(FIRST, 1):
            X.setdefault(FNAME + ":" + str(y), M.NewConstant(k))
        B, obj = [], []
        for j, rs in enumerate(R):
            bj = [M.NewBoolVar(f"b{j}_{c}") for c in range(len(rs) + 1)]   # last = skip
            M.AddExactlyOne(bj)
            tot = sum(r[0] for r in rs)
            for c, (w, tabs) in enumerate(rs):
                for ks, ok in tabs:
                    full = itertools.product(range(1, n + 1), repeat=len(ks))
                    M.AddAllowedAssignments([X[k] for k in ks] + [bj[c]], [t + (1,) for t in ok] + [t + (0,) for t in full])
                obj.append((10 ** 6 + round(1000 * math.log(w / tot))) * bj[c])
            B.append(bj)
        for cut in cuts:
            M.AddBoolOr([B[j][c] for j, c in cut])
        M.Maximize(sum(obj))
        s = cp_model.CpSolver(); s.parameters.num_workers = 1; s.parameters.max_time_in_seconds = 30
        st = s.Solve(M)
        if st not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return 0, None, it, None
        sel = [next(c for c, b in enumerate(bj) if s.Value(b)) for bj in B]
        x = {k: s.Value(X[k]) for k in X}
        for j, c in enumerate(sel):
            M.Add(B[j][c] == 1)
        e = []
        for k in X:
            if not (k.split(":", 1)[0] == FNAME and k.split(":", 1)[1] in [str(z) for z in FIRST]):
                d = M.NewBoolVar(""); M.Add(X[k] != x[k]).OnlyEnforceIf(d); e.append(d)
        M.AddBoolOr(e)
        M.ClearObjective()
        s2 = cp_model.CpSolver(); s2.parameters.num_workers = 1; s2.parameters.max_time_in_seconds = 30
        if s2.Solve(M) not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return 1, x, it, sel
        x2 = {k: s2.Value(X[k]) for k in X}
        cut = [(j, c) for j, rs in enumerate(R) for c, (w, tabs) in enumerate(rs) if not (holds(tabs, x) and holds(tabs, x2))]
        if not cut:
            return 2, x, it, sel
        cuts.append(cut)
    return 2, None, it, None
cnt, x, it, sel = search(R)
g = {}
if cnt == 1:
    for a, vals in groups.items():
        row = [None] * n
        for y in vals:
            row[x[f"{a}:{y}"] - 1] = y
        g[a] = row
skips = sum(c == len(R[j]) for j, c in enumerate(sel)) if sel else None
ceil = None
if GX is not None:
    c2, x2, _, _ = search([[r for r in rs if holds(r[1], GX)] for rs in R])
    ceil = c2 == 1 and all(x2[k] == GX[k] for k in GX)
print(json.dumps({"count": cnt, "grid": g, "iters": it, "skips": skips, "nread": [len(rs) for rs in R], "ceiling": ceil}))
"""


def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    tag = a[0] if a else "q8bh"
    dev = "_dev" if "--dev" in sys.argv else ""
    data = os.environ["POC_DATA"]
    P = {r["id"]: r for s in ["gridpuzzle", "lgp"] for r in map(json.loads, open(os.path.join(data, s, "grid.jsonl")))}
    nv = lambda x: __import__("re").search(r"\d[\d:.]*", str(x).replace(",", "")).group() if __import__("re").search(r"\d", str(x)) else __import__("re").sub(r"[^a-z0-9]", "", str(x).lower())
    for s in ["gp", "lgp"]:
        for sd in [1, 2, 3]:
            f = os.path.join(RES, f"{s}_{tag}{dev}_gts_s{sd}.jsonl")
            if not os.path.exists(f):
                continue

            def one(r):
                p = P[r["id"]]
                row = {k: r[k] for k in ["id", "size", "seed", "tokens"]}
                row["arm"], row["gts"] = "gtsj", {"count": r["count"], "exact": r["exact"]}
                if not r.get("code"):
                    return {**row, "count": -1, "exact": False, "cell_acc": 0.0}
                CANDS = {}
                for st in r["steps"]:
                    CANDS.setdefault(st["clue"], []).extend(nw for _, nw in st["cands"] if nw)
                gv, dup = {}, set()   # value -> true position; a value name shared by two categories is left out (as in gp_misread.py)
                for vals in p["gold"].values():
                    for k, x in enumerate(vals, 1):
                        if nv(x) in gv:
                            dup.add(nv(x))
                        gv[nv(x)] = k
                for d in dup:
                    gv.pop(d)
                first, fv = p["cats"][0]
                prog = (r["code"][:r["code"].rindex("\nclues = ")] + f"\nCANDS = {json.dumps([CANDS[j] for j in sorted(CANDS)])}\nGOLDV = {json.dumps(gv)}\n"
                        + JOINT.replace("__FIRST__", json.dumps(fv)).replace("__FNAME__", json.dumps(first)))
                res = run_python(prog, "", timeout=900, mem_bytes=4 << 30)
                try:
                    o = json.loads(res.stdout.strip().splitlines()[-1])
                except (AttributeError, IndexError, ValueError):
                    o = {"count": -1, "grid": {}, "err": (res.stderr or "")[-300:]}
                ex, ca = gp_score(o["grid"], p)
                return {**row, "exact": ex, "cell_acc": ca, **o}
            with ThreadPoolExecutor(4) as ex:   # 4 CPUs per job; each program runs one CP-SAT worker
                out = list(ex.map(one, map(json.loads, open(f))))
            with open(os.path.join(RES, f"{s}_{tag}{dev}_gtsj_s{sd}.jsonl"), "w") as fo:
                fo.writelines(json.dumps(x) + "\n" for x in out)
            print(s, sd, "gts", sum(x["gts"]["exact"] for x in out), "gtsj", sum(x["exact"] for x in out), "count-1", sum(x["count"] == 1 for x in out),
                  "ceiling", sum(bool(x.get("ceiling")) for x in out), "of", len(out), flush=True)


if __name__ == "__main__":
    main()
