"""E2 analysis (pre-registered in results/PREREG_E2.md): F2 replication on delaunay (in_circle helper: signed / doc / fixed / none) and
F1 replication on diameter (K0 / HIGH = convex_hull+polar_sort / LOW = point_in_polygon+segments_intersect), seeds pooled.
Per cell: correct on all 8 variants (k of n), mean output tokens; paired differences with 95% bootstrap CIs over (instance, seed);
failure patterns; route switch (HIGH programs that call convex_hull / polar_sort).
usage: python analyze_e2.py [models, default 8b,32b,oss20low]"""
import json, os, random, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
RES = "/NAS/SJ/POSTECH/nlp/results"
MODELS = (sys.argv[1] if len(sys.argv) > 1 else "8b,32b,oss20low").split(",")
OK_VARIANTS = ("identity", "translate", "rot90", "scale", "big")


def load(m, cond):
    rows = {}
    for sd in (1, 2):
        p = f"{RES}/geocross_S2_E2_geox{m}_{cond}_t07s{sd}.jsonl"
        if os.path.exists(p):
            for r in map(json.loads, open(p)):
                rows[(r["task"], r["n"], r["inst"], sd)] = r
    return rows


def ok(r):
    return r["class"] == "correct_all"


def diff_ci(a, b, B=10000, seed=0):   # paired: mean(b) - mean(a) over shared keys, percentage points
    keys = sorted(set(a) & set(b))
    d = [ok(b[k]) - ok(a[k]) for k in keys]
    rng = random.Random(seed); n = len(d)
    bs = sorted(sum(d[rng.randrange(n)] for _ in range(n)) / n for _ in range(B))
    return 100 * sum(d) / n, 100 * bs[int(0.025 * B)], 100 * bs[int(0.975 * B)], n


def skips_count_line(r):   # input-format counterfactual: correct on identity once the first line (n) is removed from stdin?
    if not r.get("code"):
        return False
    import run_geo as G
    from sandbox import run_python
    rng = random.Random(f"{r['task']}-{r['n']}-{r['inst']}")
    x = G.variants(r["task"], G.base_instance(r["task"], r["n"], rng), rng)["identity"]
    _, stdin, _ = G.render(r["task"], x)
    o = run_python(r["code"], stdin.split("\n", 1)[1], timeout=10)
    out = (o.stdout.strip().split() or [None])[-1] if o.status == "ok" else None
    return out is not None and out.lower() == G.answer(r["task"], x)


def pattern(r):
    if ok(r):
        return "correct"
    pv = r["per_variant"]
    if pv.get("identity") is None:
        return "input format: skips the count line" if skips_count_line(r) else "no output / crash"
    if all(pv.get(v) for v in OK_VARIANTS) and (pv.get("mirror") is False or pv.get("permute") is False):
        return "orientation (mirror/permute only)" if pv.get("degen") is not False else "orientation + degen"
    if all(pv.get(v) for v in OK_VARIANTS + ("mirror", "permute")) and pv.get("degen") is False:
        return "degenerate only"
    if pv.get("identity") is False:
        return "wrong on identity"
    return "other variant pattern"


def cell(m, cond):
    R = load(m, cond)
    if not R:
        return R, "   (missing)"
    k = sum(map(ok, R.values())); tok = sum(r.get("out_tokens") or 0 for r in R.values()) / len(R)
    return R, f"{k:3d}/{len(R)} ({100 * k / len(R):5.1f}%)  tokens {tok:6.0f}"


for m in MODELS:
    print(f"\n=== {m} ===")
    C = {}
    for cond in ("del_none", "del_signed", "del_doc", "del_fixed", "diam_k0", "diam_high", "diam_low"):
        C[cond], line = cell(m, cond)
        print(f"{cond:11s} {line}")
    if all(C[c] for c in ("del_signed", "del_fixed", "del_doc")):
        d, lo, hi, n = diff_ci(C["del_signed"], C["del_fixed"]); print(f"F2-P1 fixed - signed: {d:+.1f} [{lo:+.1f}, {hi:+.1f}] (n={n})")
        d2, lo2, hi2, _ = diff_ci(C["del_signed"], C["del_doc"]); print(f"F2-P3 doc - signed: {d2:+.1f} [{lo2:+.1f}, {hi2:+.1f}]  "
                                                                       f"(share of the signed->fixed gap recovered: {d2 / d if d else float('nan'):.2f})")
        d3, lo3, hi3, _ = diff_ci(C["del_signed"], C["del_none"]); print(f"     none - signed: {d3:+.1f} [{lo3:+.1f}, {hi3:+.1f}]")
        for cond in ("del_signed", "del_doc", "del_fixed", "del_none"):
            pat = Counter(pattern(r) for r in C[cond].values() if not ok(r))
            nf = sum(pat.values())
            print(f"  failures {cond:10s} n={nf}: " + ", ".join(f"{p} {c}" for p, c in pat.most_common())
                  + (f" | orientation share {sum(c for p, c in pat.items() if p.startswith('orientation')) / nf:.2f}" if nf else ""))
    if all(C[c] for c in ("diam_k0", "diam_high", "diam_low")):
        d, lo, hi, n = diff_ci(C["diam_low"], C["diam_high"]); print(f"F1-P1 HIGH - LOW: {d:+.1f} [{lo:+.1f}, {hi:+.1f}] (n={n})")
        d4, lo4, hi4, _ = diff_ci(C["diam_k0"], C["diam_high"]); print(f"F1-P4 HIGH - K0: {d4:+.1f} [{lo4:+.1f}, {hi4:+.1f}]")
        d5, lo5, hi5, _ = diff_ci(C["diam_k0"], C["diam_low"]); print(f"      LOW - K0: {d5:+.1f} [{lo5:+.1f}, {hi5:+.1f}]")
        H = C["diam_high"].values()
        route = [r for r in H if {"convex_hull", "polar_sort"} & set(r.get("distractors_called") or [])]
        rest = [r for r in H if r not in route]
        print(f"F1-P2 HIGH programs calling convex_hull/polar_sort: {len(route)}/{len(H)} ({100 * len(route) / len(H):.0f}%)")
        if route and rest:
            print(f"F1-P3 correct | route {sum(map(ok, route))}/{len(route)} ({100 * sum(map(ok, route)) / len(route):.0f}%)  vs  "
                  f"no route {sum(map(ok, rest))}/{len(rest)} ({100 * sum(map(ok, rest)) / len(rest):.0f}%)")
        for cond in ("diam_k0", "diam_high", "diam_low"):
            pat = Counter(pattern(r) for r in C[cond].values() if not ok(r))
            print(f"  failures {cond:10s}: " + ", ".join(f"{p} {c}" for p, c in pat.most_common()))
