"""HO-G (docs/prereg/PREREG_HOG.md): the recipe on four held-out geometry tasks (overlap, convex, tri, clip). Correct = right on all 8
variants. Free check = analyze_n10.geo_check (runs + consistent metamorphic outputs; no answers). Policies per seed: BASE, FACT, THINK,
FF (fact; think only if the fact program fails the check); accuracy @ mean output tokens; utility = accuracy - 0.5 x ktokens.
usage: python analyze_hog.py [model ...]"""
import json, os, sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_n10 as N  # noqa: E402

RES = N.RES


def load(m, arm, s):
    f = f"{RES}/geocross_S2_HOG_{m}_geo_{arm}_s{s}.jsonl"
    return {(r["task"], r["n"], r["inst"]): r for r in map(json.loads, open(f))} if os.path.exists(f) else None


for m in sys.argv[1:] or ["oss20", "q14a", "q8b"]:
    D = {(a, s): load(m, a, s) for a in ("base", "fact", "think") for s in (1, 2, 3)}
    if any(v is None for v in D.values()):
        print(m, "incomplete"); continue
    rows = [r for (a, s), X in D.items() if a == "fact" for r in X.values()]
    with ThreadPoolExecutor(16) as ex:
        list(ex.map(N.geo_check, rows))
    json.dump(N.CACHE, open(N.CACHE_F, "w"))
    ok = lambda r: r["class"] == "correct_all"
    tok = lambda r: (r.get("out_tokens") or 0) + (r.get("think_tokens") or 0)
    print(f"=== {m}")
    per = {}
    for s in (1, 2, 3):
        B, F, T = D[("base", s)], D[("fact", s)], D[("think", s)]
        keys = [k for k in F if k in B and k in T]; n = len(keys)
        P = {"BASE": (sum(ok(B[k]) for k in keys), sum(tok(B[k]) for k in keys)), "FACT": (sum(ok(F[k]) for k in keys), sum(tok(F[k]) for k in keys)),
             "THINK": (sum(ok(T[k]) for k in keys), sum(tok(T[k]) for k in keys))}
        a = t = 0
        for k in keys:
            passed = N.geo_check(F[k])[0]; t += tok(F[k])
            if passed:
                a += ok(F[k])
            else:
                a += ok(T[k]); t += tok(T[k])
        P["FF"] = (a, t)
        for p, (a_, t_) in P.items():
            per.setdefault(p, []).append((100 * a_ / n, t_ / n / 1000))
        if s == 1:
            byt = Counter(); tot = Counter()
            for k in keys:
                tot[k[0]] += 1; byt[k[0]] += ok(F[k]) if N.geo_check(F[k])[0] else ok(T[k])
            print("  FF by task (seed 1): " + ", ".join(f"{t_} {100 * byt[t_] / tot[t_]:.0f}%" for t_ in tot))
    for p, L in per.items():
        acc = sum(x for x, _ in L) / 3; tk = sum(y for _, y in L) / 3
        print(f"  {p:6s} {acc:5.1f}% @ {tk:.2f}k  (seeds " + " / ".join(f"{x:.1f}" for x, _ in L) + f") utility {acc - 0.5 * tk:.1f}")
