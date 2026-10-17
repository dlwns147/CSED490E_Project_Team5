"""VIEWS (results/PREREG_VIEWS.md): error correlation between two views of the same model vs the leak of their agreement check.
Settings (model, task family, view A, view B): same-view pairs (seed s vs s+1) and different-view pairs, from stored runs:
X1 competition math (text / program), X3 verbal optimization (mip / cpsat / text), N12 geometry (K8 toolbox / no helpers), N15
optimization libraries (free / mip / none). Per setting: error kappa (Cohen's kappa on the two views' "wrong" indicators), leak
lambda = P(A wrong | A and B give the same answer), catch = P(A and B disagree | A wrong), false alarm = P(disagree | A right).
usage: python analyze_views.py"""
import json, os, random, sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")


def kappa(a, b):   # a, b: lists of 0/1 "wrong"
    n = len(a); po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def stats(rows):   # rows: (wrongA, wrongB, agree)
    wa = [r[0] for r in rows]; wb = [r[1] for r in rows]
    ag = [r for r in rows if r[2]]
    lam = sum(r[0] for r in ag) / len(ag) if ag else float("nan")
    wr = [r for r in rows if r[0]]; rt = [r for r in rows if not r[0]]
    return {"n": len(rows), "errA": sum(wa) / len(rows), "errB": sum(wb) / len(rows), "kappa": kappa(wa, wb), "leak": lam,
            "catch": sum(not r[2] for r in wr) / len(wr) if wr else float("nan"),
            "fa": sum(not r[2] for r in rt) / len(rt) if rt else float("nan"), "p_agree": len(ag) / len(rows)}


S = {}   # (family, model, pair, kind) -> rows


def add(key, rows):
    if rows:
        S[key] = rows


# ---- X1 competition math
from run_math import same as math_same  # noqa: E402
for m in ("oss20", "q32b", "q36"):
    def L(mode, sd):
        f = f"{RES}/x1/math_{m}_{mode}_s{sd}.jsonl"
        return {r["id"]: r for r in map(json.loads, open(f))} if os.path.exists(f) else None
    D = {(md, sd): L(md, sd) for md in ("text", "prog") for sd in (1, 2, 3)}
    if any(v is None for v in D.values()):
        continue
    for fam, pick in (("math500", lambda r: r["src"] == "math500"), ("aime", lambda r: r["src"] != "math500")):
        for (a, b, kind) in (("text", "prog", "diff"), ("text", "text", "same"), ("prog", "prog", "same")):
            rows = []
            for sd in (1, 2, 3):
                sd2 = sd % 3 + 1 if a == b else sd
                for i, ra in D[(a, sd)].items():
                    if not pick(ra):
                        continue
                    rb = D[(b, sd2)][i]
                    ag = bool(ra["cands"]) and bool(rb["cands"]) and math_same(ra["cands"], rb["cands"])
                    rows.append((not ra["correct"], not rb["correct"], ag))
            add((f"math-{fam}", m, f"{a}-{b}", kind), rows)
# ---- X3 verbal optimization
for m in ("oss20", "q32b"):
    def L(mode, sd):
        f = f"{RES}/x3/opt_{m}_{mode}_s{sd}.jsonl"
        return {r["id"]: r for r in map(json.loads, open(f))} if os.path.exists(f) else None
    D = {(md, sd): L(md, sd) for md in ("mip", "cpsat", "text") for sd in (1, 2, 3)}
    if any(v is None for v in D.values()):
        continue
    def same_v(x, y):
        if x is None or y is None:
            return False
        if "NBS" in (x, y):
            return x == y
        return abs(x - y) <= max(1e-2, 1e-3 * abs(y))
    for fam in ("nl4opt", "industryor"):
        for (a, b, kind) in (("mip", "cpsat", "diff"), ("mip", "text", "diff"), ("mip", "mip", "same"), ("text", "text", "same")):
            rows = []
            for sd in (1, 2, 3):
                sd2 = sd % 3 + 1 if a == b else sd
                for i, ra in D[(a, sd)].items():
                    if not i.startswith(fam):
                        continue
                    rb = D[(b, sd2)][i]
                    rows.append((not ra["correct"], not rb["correct"], same_v(ra["pred"], rb["pred"])))
            add((f"wordopt-{fam}", m, f"{a}-{b}", kind), rows)
# ---- N12 geometry (K8 toolbox vs no helpers)
import analyze_n12 as G  # noqa: E402
for m, pre in (("q32b", "S2_N10"), ("q8b", "S2_N10q8")):
    G.PRE = pre
    try:
        D = {(arm, sd): G.rows_of("geo", f"{arm}_s{sd}") for arm in ("k8", "none") for sd in (1, 2, 3)}
    except FileNotFoundError:
        continue
    for (a, b, kind) in (("k8", "none", "diff"), ("k8", "k8", "same"), ("none", "none", "same")):
        rows = []
        for sd in (1, 2, 3):
            sd2 = sd % 3 + 1 if a == b else sd
            for k, ra in D[(a, sd)].items():
                rb = D[(b, sd2)].get(k)
                if rb is None:
                    continue
                oa, ob = G.geo_out(ra), G.geo_out(rb)
                rows.append((ra["class"] != "correct_all", rb["class"] != "correct_all", oa is not None and oa == ob))
        add(("geometry", m, f"{a}-{b}", kind), rows)
import analyze_n10 as A10  # noqa: E402
json.dump(A10.CACHE, open(A10.CACHE_F, "w"))
# ---- N15 optimization libraries
for m in ("q32b", "oss20", "q36", "oss120"):
    def L(lib, sd):
        f = f"{RES}/co_S2_N15_{m}_{lib}_s{sd}.jsonl"
        return {r["key"]: r for r in map(json.loads, open(f))} if os.path.exists(f) else None
    D = {(lib, sd): L(lib, sd) for lib in ("free", "mip", "none") for sd in (1, 2, 3)}
    if any(v is None for v in D.values()):
        continue
    opt = lambda r: r["status"] == "ok" and r["feasible"] and r["gap"] == 0
    val = lambda r: r["value"] if r["status"] == "ok" and r["feasible"] else None
    for (a, b, kind) in (("free", "mip", "diff"), ("free", "none", "diff"), ("free", "free", "same"), ("mip", "mip", "same")):
        rows = []
        for sd in (1, 2, 3):
            sd2 = sd % 3 + 1 if a == b else sd
            for k, ra in D[(a, sd)].items():
                rb = D[(b, sd2)][k]
                rows.append((not opt(ra), not opt(rb), val(ra) is not None and val(ra) == val(rb)))
        add(("optlib", m, f"{a}-{b}", kind), rows)

# ---- report and tests
T = {k: stats(v) for k, v in S.items()}
print(f"{'family':18s} {'model':6s} {'pair':12s} kind     n  errA  errB  kappa  leak  catch   FA")
for k, s in sorted(T.items()):
    print(f"{k[0]:18s} {k[1]:6s} {k[2]:12s} {k[3]:5s} {s['n']:5d} {s['errA']:.2f}  {s['errB']:.2f}  {s['kappa']:.2f}  {s['leak']:.3f} {s['catch']:.2f}  {s['fa']:.2f}")


def spearman(x, y):
    def rank(v):
        o = sorted(range(len(v)), key=lambda i: v[i]); r = [0] * len(v)
        for pos, i in enumerate(o):
            r[i] = pos
        return r
    rx, ry = rank(x), rank(y); n = len(x)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else float("nan")


V = [s for s in T.values() if s["leak"] == s["leak"] and s["kappa"] == s["kappa"]]
print(f"\nP1: {len(V)} settings; Spearman(kappa, leak) = {spearman([s['kappa'] for s in V], [s['leak'] for s in V]):.2f} (prediction >= 0.7); "
      f"Spearman(kappa, catch) = {spearman([s['kappa'] for s in V], [s['catch'] for s in V]):.2f} (prediction <= -0.6)")
# P2: leak from kappa and the error rates through one fitted collision rate r (same wrong answer | both wrong), fit on half, test on half
def pred(s, r):
    pa, pb, kp = s["errA"], s["errB"], s["kappa"]
    pe = pa * pb + (1 - pa) * (1 - pb); po = kp * (1 - pe) + pe
    pww = max(0.0, (po - 1 + pa + pb) / 2); prr = max(0.0, 1 - pa - pb + pww)
    return pww * r / (prr + pww * r) if prr + pww * r > 0 else 0.0
keys = sorted(T); random.Random(0).shuffle(keys)
fit, test = [k for k in keys[: len(keys) // 2] if k in T], keys[len(keys) // 2:]
rs = [i / 100 for i in range(1, 101)]
r_best = min(rs, key=lambda r: sum(abs(pred(T[k], r) - T[k]["leak"]) for k in fit if T[k]["leak"] == T[k]["leak"]))
mae = [abs(pred(T[k], r_best) - T[k]["leak"]) for k in test if T[k]["leak"] == T[k]["leak"]]
print(f"P2: fitted collision rate r = {r_best:.2f}; held-out MAE of the leak = {100 * sum(mae) / len(mae):.1f} points over {len(mae)} settings (prediction <= 5)")
# P3: same-view kappa > different-view kappa per (family, model) cell
cells = defaultdict(lambda: {"same": [], "diff": []})
for k, s in T.items():
    cells[(k[0], k[1])][k[3]].append(s["kappa"])
win = [max(c["same"]) > max(c["diff"]) for c in cells.values() if c["same"] and c["diff"]]
win_min = [min(c["same"]) > max(c["diff"]) for c in cells.values() if c["same"] and c["diff"]]
print(f"P3: cells where the most correlated same-view pair beats every different-view pair: {sum(win)}/{len(win)}; where every same-view pair does: "
      f"{sum(win_min)}/{len(win_min)} (prediction >= 80%)")
