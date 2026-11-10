"""Idea 35, offline: which clue forms does Qwen3-8B misread when it translates a grid puzzle? No model call, no solver.

Usage: python poc/gp_misread.py [tag q8b] [--dev]
For every final program of the translation arms (results/{gp,lgp}_<tag>[_dev]_{gtr,gtrt}_s{1,2,3}.jsonl), each clue expression is evaluated on the
true grid with the program interface of GP_SOLVE (run_zebra.py: p holds the first category's numbers, at(), V(), names matched on format).
An expression false on the true grid is a misreading (a right translation holds on it). Each expression is assigned to the puzzle clue whose text
names most of its values; a clue with no expression is an omission. Error kind of a false expression: "direction" if it holds once two of its
values swap places (e.g. "4 more than" written the other way), "position" if it holds with p as positions 1..n instead of the numbers,
"other" otherwise. Clue forms are read off the clue text (descriptive only; no rule is built on them).
Model-written expressions run only in a subprocess with python -I (host rule), one per program, 60 s each.
"""
import ast
import collections
import json
import os
import re
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
RES = os.path.join(ROOT, "results")
DATA = os.environ.get("NLP_DATA", os.path.join(ROOT, "..", "nlp_data"))
SRC = open(os.path.join(ROOT, "poc", "run_zebra.py")).read()
G = next(n.value.value for n in ast.parse(SRC).body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "GP_SOLVE")
# the program interface of GP_SOLVE without the solver: names, at(), V(), the string-to-position rewrite
EVAL = "import ast, itertools, json, re\n" + G[G.index("FIRST, FNAME"):G.index("m, v = cp_model.CpModel(), {}")] + """
v = {}
for a, vals in groups.items():
    assert len(vals) == n, "size"
    for x in vals:
        v[f"{a}:{x}"] = None
for k, x in enumerate(FIRST, 1):
    v.setdefault(FNAME + ":" + str(x), None)
""" + G[G.index("_al = {"):G.index("for c in clues:")] + """
def _gpos(k):
    a, x = k.split(":", 1)
    if a == FNAME and x in [str(y) for y in FIRST]:
        return [str(y) for y in FIRST].index(x) + 1
    return GOLDV.get(_nv(x))
out = []
for c in clues:
    try:
        c2 = ast.unparse(ast.fix_missing_locations(_S().visit(ast.parse(c, mode="eval"))))
        keys = sorted({t.slice.value for t in ast.walk(ast.parse(c2, mode="eval")) if isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant) and isinstance(t.slice.value, str) and ":" in t.slice.value})
        rk = [_res(k) for k in keys]
        if not keys or not all(rk):
            out.append({"err": "name"}); continue
        pos = [_gpos(k) for k in rk]
        if None in pos:
            out.append({"err": "gold", "keys": rk}); continue
        code = compile(c2, "clue", "eval")
        val = lambda P: bool(eval(code, {"abs": abs, "min": min, "max": max, "V": V, "at": at}, {"p": dict(zip(keys, P))}))
        h = val([VALUES[q - 1] for q in pos])
        sw = any(val([VALUES[q - 1] for q in (pos[:i] + [pos[j]] + pos[i + 1:j] + [pos[i]] + pos[j + 1:])])
                 for i in range(len(pos)) for j in range(i + 1, len(pos)) if pos[i] != pos[j]) if not h else False
        fr = [i for i, k in enumerate(rk) if not (k.split(":", 1)[0] == FNAME and k.split(":", 1)[1] in [str(y) for y in FIRST])]
        tab = None
        if len(fr) <= 5:   # truth table over the non-first-category values (first-category names are fixed positions in GP_SOLVE)
            tab = []
            for t in itertools.product(range(1, n + 1), repeat=len(fr)):
                q = list(pos)
                for i, x in zip(fr, t):
                    q[i] = x
                if val([VALUES[x - 1] for x in q]):
                    tab.append(t)
        out.append({"free": [rk[i] for i in fr], "tab": tab, "keys": rk, "holds": h, "swap": sw, "pos": (not h) and val(pos), "consts": [t.value for t in ast.walk(ast.parse(c2, mode="eval")) if isinstance(t, ast.Constant) and isinstance(t.value, (int, float))]})
    except Exception as e:
        out.append({"err": type(e).__name__})
print(json.dumps(out))
"""
NUM = r"(\d+|one|two|three|four|five|six|seven|eight|nine|ten|twice|half)"


def form(t):
    """Descriptive clue form, first match in this order."""
    s = t.lower()
    if re.search(r"all different|\bwere all\b|\bare all\b", s):
        return "all different"
    if re.match(r"of (the )?.+ and .+, one", s) or re.search(r"\bone (is|was) .+ and the other\b", s):
        return "one of a pair"
    if re.search(r"\beither\b", s):
        return "either-or"
    if re.search(NUM + r"\b[^.,;]*\b(more|less|fewer|higher|lower|after|before|later|earlier|longer|shorter|older|younger|bigger|smaller|larger|greater|than)\b", s) and re.search(r"\bthan\b|\bafter\b|\bbefore\b", s):
        return "numeric difference"
    if re.search(r"\bthan\b|\bafter\b|\bbefore\b|\bearlier\b|\blater\b", s):
        return "order"
    if re.search(r"\bnot\b|n't\b|\bneither\b|\bnor\b", s):
        return "negation"
    return "equality"


def lit(x):
    return ast.literal_eval(x) if isinstance(x, str) else x


def clues_of(p):
    t = p["puzzle"].split("Clues:")[1].split("While answering")[0]
    return re.findall(r"^\s*\d+\.\s*(.+)$", t, re.M)


def nv(x):
    return re.search(r"\d[\d:.]*", str(x).replace(",", "")).group() if re.search(r"\d", str(x)) else re.sub(r"[^a-z0-9]", "", str(x).lower())


def mentions(text, cats):
    """Values named in a clue, as normalized strings (first-category numbers only with their digits)."""
    low = re.sub(r"[^a-z0-9 ]", " ", text.lower().replace(",", ""))
    hit = set()
    for _, vals in cats:
        for x in vals:
            w = re.sub(r"[^a-z0-9 ]", " ", str(x).lower().replace(",", "")).split()
            if w and re.search(r"\b" + r"\s+".join(map(re.escape, w)) + r"\b", low):
                hit.add(nv(x))
    return hit


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "q8b"
    dev = "_dev" if "--dev" in sys.argv else ""
    P = {r["id"]: r for s in ["gridpuzzle", "lgp"] for r in map(json.loads, open(os.path.join(DATA, s, "grid.jsonl")))}
    rows = []
    cache = os.path.join(RES, f"misread_{tag}{dev}.jsonl")
    done = {(r["set"], r["arm"], r["seed"], r["id"]) for r in map(json.loads, open(cache))} if os.path.exists(cache) else set()
    with open(cache, "a") as fo:
        for s in ["gp", "lgp"]:
            for arm in ["gtr", "gtrt"]:
                for sd in [1, 2, 3]:
                    f = os.path.join(RES, f"{s}_{tag}{dev}_{arm}_s{sd}.jsonl")
                    if not os.path.exists(f):
                        continue
                    for r in map(json.loads, open(f)):
                        if (s, arm, sd, r["id"]) in done or not r.get("code"):
                            continue
                        p = P[r["id"]]
                        cats = lit(p["cats"])
                        gold = lit(p["gold"])
                        gv, dup = {}, set()   # value -> true position; a value name shared by two categories is left out
                        for a, vals in gold.items():
                            for k, x in enumerate(vals, 1):
                                if nv(x) in gv:
                                    dup.add(nv(x))
                                gv[nv(x)] = k
                        for d in dup:
                            gv.pop(d)
                        prog = (r["code"] + f"\nGOLDV = {json.dumps(gv)}\n"
                                + EVAL.replace("__FIRST__", json.dumps(cats[0][1])).replace("__FNAME__", json.dumps(cats[0][0])))
                        try:
                            o = subprocess.run([sys.executable, "-I", "-c", prog], capture_output=True, text=True, timeout=60)
                            ev = json.loads(o.stdout.strip().splitlines()[-1])
                        except Exception:
                            ev = None
                        row = {"set": s, "arm": arm, "seed": sd, "id": r["id"], "size": r["size"], "count": r["count"], "exact": r["exact"], "ev": ev}
                        fo.write(json.dumps(row) + "\n")
                        rows.append(row)
    rows = list(map(json.loads, open(cache)))
    report(rows, P)
    weak(rows, P)


def report(rows, P):
    for s in ["gp", "lgp"]:
        for arm in ["gtr", "gtrt"]:
            R = [r for r in rows if r["set"] == s and r["arm"] == arm]
            if not R:
                continue
            ok = [r for r in R if r["ev"] is not None]
            st = collections.defaultdict(collections.Counter)
            kinds = collections.Counter()
            prog = collections.Counter()
            for r in ok:
                p = P[r["id"]]
                cats = lit(p["cats"])
                cl = clues_of(p)
                men = [mentions(t, cats) for t in cl]
                asg = collections.defaultdict(list)
                for e in r["ev"]:
                    if "holds" not in e:
                        continue
                    ks = {nv(k.split(":", 1)[1]) for k in e["keys"]}
                    sc = [len(ks & m) for m in men]
                    if max(sc) > 0:
                        asg[sc.index(max(sc))].append(e)
                nfalse = 0
                for j, t in enumerate(cl):
                    f = form(t)
                    st[f]["clues"] += 1
                    es = asg.get(j, [])
                    if not es:
                        st[f]["omitted"] += 1
                        continue
                    bad = [e for e in es if not e["holds"]]
                    if bad:
                        st[f]["false"] += 1
                        nfalse += 1
                        k = "direction" if any(e["swap"] for e in bad) else "position" if any(e["pos"] for e in bad) else "other"
                        st[f][k] += 1
                        kinds[k] += 1
                prog[(r["count"], r["exact"], nfalse > 0)] += 1
            print(f"== {s} {arm}: {len(R)} programs, {len(ok)} evaluated")
            print("   final count, exact, has a false expression: " + ", ".join(f"{k}: {v}" for k, v in sorted(prog.items(), key=str)))
            print(f"   {'clue form':20s} {'clues':>6s} {'false %':>8s} {'omitted %':>10s}  direction / position / other")
            for f, c in sorted(st.items(), key=lambda x: -x[1]["clues"]):
                print(f"   {f:20s} {c['clues']:6d} {100 * c['false'] / c['clues']:8.1f} {100 * c['omitted'] / c['clues']:10.1f}  {c['direction']} / {c['position']} / {c['other']}")


def weak(rows, P):
    """Clue-level strength against a right translation of the same puzzle (a count-1 exact program from any arm or seed, gtrt first):
    a clue is weak when the program's expressions for it allow an assignment of their values that the right program's expressions for the
    clue rule out (positions 1..n, values of one category all different). Only truth tables of the expressions are used here."""
    def canon(r):
        p = P[r["id"]]
        cl = clues_of(p)
        men = [mentions(t, lit(p["cats"])) for t in cl]
        asg = collections.defaultdict(list)
        for e in r["ev"]:
            if "holds" not in e:
                continue
            ks = {nv(k.split(":", 1)[1]) for k in e["keys"]}
            sc = [len(ks & m) for m in men]
            if max(sc) > 0:
                asg[sc.index(max(sc))].append(e)
        return cl, asg
    ref = {}
    for r in sorted(rows, key=lambda r: r["arm"] != "gtrt"):
        if r["count"] == 1 and r["exact"] and r["ev"] and r["id"] not in ref:
            ref[r["id"]] = r
    import itertools
    for s in ["gp", "lgp"]:
        for arm in ["gtr", "gtrt"]:
            st = collections.defaultdict(collections.Counter)
            prog = collections.Counter()
            for r in rows:
                if r["set"] != s or r["arm"] != arm or not r["ev"] or r["id"] not in ref or r is ref[r["id"]]:
                    continue
                p = P[r["id"]]
                n = len(lit(p["cats"])[0][1])
                catof = {nv(x): a for a, vals in lit(p["gold"]).items() for x in vals}
                cl, A = canon(r)
                _, B = canon(ref[r["id"]])
                nweak = nfalse = 0
                for j, t in enumerate(cl):
                    f = form(t)
                    ea, eb = A.get(j, []), B.get(j, [])
                    if any(not e["holds"] for e in ea):
                        nfalse += 1
                        continue
                    if not eb:
                        continue
                    st[f]["clues"] += 1
                    if not ea:
                        st[f]["omitted"] += 1
                        nweak += 1
                        continue
                    if any(e["tab"] is None for e in ea + eb):
                        st[f]["skipped"] += 1
                        continue
                    U = sorted({nv(k.split(":", 1)[1]) for e in ea + eb for k in e["free"]})
                    if any(u not in catof for u in U) or len(U) > 7:
                        st[f]["skipped"] += 1
                        continue
                    sat = lambda E, q: all(tuple(q[nv(k.split(":", 1)[1])] for k in e["free"]) in {tuple(x) for x in e["tab"]} for e in E)
                    w = False
                    for t2 in itertools.product(range(1, n + 1), repeat=len(U)):
                        q = dict(zip(U, t2))
                        if any(q[a] == q[b] and catof[a] == catof[b] for a, b in itertools.combinations(U, 2)):
                            continue
                        if sat(ea, q) and not sat(eb, q):
                            w = True
                            break
                    st[f]["weak"] += w
                    nweak += w
                prog[(r["count"], r["exact"], "false" if nfalse else "weak" if nweak else "neither")] += 1
            print(f"== {s} {arm}: clues judged against a right translation of the same puzzle")
            print("   final count, exact, cause: " + ", ".join(f"{k}: {v}" for k, v in sorted(prog.items(), key=str)))
            print(f"   {'clue form':20s} {'clues':>6s} {'weak %':>7s} {'omitted %':>10s} {'skipped':>8s}")
            for f, c in sorted(st.items(), key=lambda x: -x[1]["clues"]):
                print(f"   {f:20s} {c['clues']:6d} {100 * c['weak'] / c['clues']:7.1f} {100 * c['omitted'] / c['clues']:10.1f} {c['skipped']:8d}")


if __name__ == "__main__":
    main()
