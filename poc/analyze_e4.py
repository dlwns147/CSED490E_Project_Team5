"""E4 analysis (pre-registered in docs/prereg/PREREG_E4_REPLAY.md): leave-hull-out LoRA arms A (no replay), B (self-replay), C (teacher replay)
vs the base Qwen3-8B on the same prompts (base = C1 / E2 runs on the same stack). % correct on all 8 variants, k of n, paired 95% bootstrap
CIs over (instance, seed). Also: hull programs by algorithm family (monotone chain vs others) via the stored code is NOT used; we report
behavioural classes only.
usage: python analyze_e4.py [arms, default A,B,C]"""
import json, os, random, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root (was hard-coded)
RES = f"{ROOT}/results"
ARMS = (sys.argv[1] if len(sys.argv) > 1 else "A,B,C").split(",")


def rows(tag, tasks=None, seed=None):
    p = f"{RES}/geocross_{tag}.jsonl"
    if not os.path.exists(p):
        return {}
    return {(r["task"], r["n"], r["inst"], seed): r for r in map(json.loads, open(p)) if tasks is None or r["task"] in tasks}


def base(cell):
    if cell == "hull_k0":
        return {**rows("S2_C1_geox8b_dis0_t07s1", {"hull"}, 1), **rows("S2_C1_geox8b_dis0_t07s2", {"hull"}, 2)}
    if cell == "hull_k8":
        return {**rows("S2_C1_geox8b_dis8_t07s1", {"hull"}, 1), **rows("S2_C1_geox8b_dis8_t07s2", {"hull"}, 2)}
    if cell == "trained_k8":
        return rows("S2_C1_geox8b_dis8_t07s1", {"area2", "pip", "segs", "close"}, 1)
    if cell == "diam":
        return rows("S2_E2_geox8b_diam_k0_t07s1", None, 1)
    if cell == "delfixed":
        return rows("S2_E2_geox8b_del_fixed_t07s1", None, 1)


def arm(a, cell):
    if cell in ("hull_k0", "hull_k8"):
        return {**rows(f"S2_E4_{a}_{cell}_s1", None, 1), **rows(f"S2_E4_{a}_{cell}_s2", None, 2)}
    return rows(f"S2_E4_{a}_{cell}_s1", None, 1)


def ok(r):
    return r["class"] == "correct_all"


def diff(x, y, B=10000):
    ks = sorted(set(x) & set(y)); d = [ok(y[k]) - ok(x[k]) for k in ks]; rng = random.Random(0); n = len(d)
    if not n:
        return None
    bs = sorted(sum(d[rng.randrange(n)] for _ in range(n)) / n for _ in range(B))
    return 100 * sum(d) / n, 100 * bs[int(.025 * B)], 100 * bs[int(.975 * B)]


CELLS = ("hull_k0", "hull_k8", "trained_k8", "diam", "delfixed")
print(f"{'cell':11s} {'base':>12s} " + " ".join(f"{a:>26s}" for a in ARMS))
for c in CELLS:
    b = base(c)
    line = f"{c:11s} {sum(map(ok, b.values())):4d}/{len(b):<4d}({100 * sum(map(ok, b.values())) / max(1, len(b)):3.0f}%)"
    for a in ARMS:
        x = arm(a, c)
        if not x:
            line += f" {'(missing)':>26s}"; continue
        d = diff(b, x)
        line += f"   {sum(map(ok, x.values())):3d}/{len(x):<3d} {d[0]:+6.1f} [{d[1]:+6.1f},{d[2]:+6.1f}]"
    print(line)
for a1, a2 in (("A", "B"), ("C", "B"), ("A", "C")):
    if a1 in ARMS and a2 in ARMS:
        for c in CELLS:
            x, y = arm(a1, c), arm(a2, c)
            if x and y:
                d = diff(x, y); print(f"{a2} - {a1} {c:11s} {d[0]:+6.1f} [{d[1]:+6.1f}, {d[2]:+6.1f}]")
