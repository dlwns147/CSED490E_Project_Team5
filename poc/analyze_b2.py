"""B2 analysis (results/PREREG_B2.md): forgetting-mitigation baselines vs E4 self-replay, same evaluation cells as E4.
% correct on all 8 variants (k of n); paired 95% bootstrap CIs vs E4-B (self-replay) and vs the base model.
usage: python analyze_b2.py"""
import json, os, random

RES = "/NAS/SJ/POSTECH/nlp/results"
CELLS = ("hull_k0", "hull_k8", "trained_k8", "diam", "delfixed")
ARMS = [("E4 A: no replay", "S2_E4_A"), ("B2 A' (A retrained)", "S2_B2_Aprime"), ("WiSE-FT alpha 0.25", "S2_B2_wise0.25"),
        ("WiSE-FT alpha 0.5", "S2_B2_wise0.5"), ("WiSE-FT alpha 0.75", "S2_B2_wise0.75"), ("SDFT rewrite", "S2_B2_sdft"),
        ("self-SFT (RFT)", "S2_B2_selfsft"), ("E4 C: teacher replay", "S2_E4_C"), ("E4 B: SELF-REPLAY", "S2_E4_B")]


def rows(tag, tasks=None, seed=None):
    p = f"{RES}/geocross_{tag}.jsonl"
    if not os.path.exists(p):
        return {}
    return {(r["task"], r["n"], r["inst"], seed): r for r in map(json.loads, open(p)) if tasks is None or r["task"] in tasks}


def base(cell):
    return {"hull_k0": lambda: {**rows("S2_C1_geox8b_dis0_t07s1", {"hull"}, 1), **rows("S2_C1_geox8b_dis0_t07s2", {"hull"}, 2)},
            "hull_k8": lambda: {**rows("S2_C1_geox8b_dis8_t07s1", {"hull"}, 1), **rows("S2_C1_geox8b_dis8_t07s2", {"hull"}, 2)},
            "trained_k8": lambda: rows("S2_C1_geox8b_dis8_t07s1", {"area2", "pip", "segs", "close"}, 1),
            "diam": lambda: rows("S2_E2_geox8b_diam_k0_t07s1", None, 1),
            "delfixed": lambda: rows("S2_E2_geox8b_del_fixed_t07s1", None, 1)}[cell]()


def arm(prefix, cell):
    if cell in ("hull_k0", "hull_k8"):
        return {**rows(f"{prefix}_{cell}_s1", None, 1), **rows(f"{prefix}_{cell}_s2", None, 2)}
    return rows(f"{prefix}_{cell}_s1", None, 1)


ok = lambda r: r["class"] == "correct_all"


def diff(x, y, B=10000):
    ks = sorted(set(x) & set(y)); d = [ok(y[k]) - ok(x[k]) for k in ks]; rng = random.Random(0); n = len(d)
    if not n:
        return None
    bs = sorted(sum(d[rng.randrange(n)] for _ in range(n)) / n for _ in range(B))
    return 100 * sum(d) / n, 100 * bs[int(.025 * B)], 100 * bs[int(.975 * B)]


print(f"{'arm':24s} " + " ".join(f"{c:>12s}" for c in CELLS))
print(f"{'base Qwen3-8B':24s} " + " ".join(f"{sum(map(ok, base(c).values())):5d}/{len(base(c)):<6d}" for c in CELLS))
for name, pre in ARMS:
    cells = [arm(pre, c) for c in CELLS]
    if not any(cells):
        print(f"{name:24s} (missing)"); continue
    print(f"{name:24s} " + " ".join(f"{sum(map(ok, x.values())):5d}/{len(x):<6d}" if x else f"{'-':>12s}" for x in cells))
selfrep = {c: arm("S2_E4_B", c) for c in CELLS}
print("\npaired difference vs E4 B (self-replay), points [95% CI]:")
for name, pre in ARMS[:-1]:
    out = []
    for c in CELLS:
        x = arm(pre, c)
        d = diff(selfrep[c], x) if x else None
        out.append(f"{c} {d[0]:+.1f} [{d[1]:+.1f},{d[2]:+.1f}]" if d else f"{c} -")
    print(f"  {name:24s} " + " | ".join(out))
