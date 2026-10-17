"""B3 analysis (docs/prereg/PREREG_B3.md): scope sentence, System 2 Attention and DRAFT-style docs vs the measured references.
usage: python analyze_b3.py"""
import json, os, random, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
RES = "/NAS/SJ/POSTECH/nlp/results"
src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "analyze_e2.py")).read().split("\nfor m in MODELS")[0]
NS = {"__file__": os.path.join(os.path.dirname(os.path.abspath(__file__)), "analyze_e2.py")}
exec(src, NS)
pattern = NS["pattern"]


def load(tag, seeds=(1, 2)):
    out = {}
    for sd in seeds:
        p = f"{RES}/geocross_{tag}_t07s{sd}.jsonl"
        if os.path.exists(p):
            for r in map(json.loads, open(p)):
                out[(r["task"], r["n"], r["inst"], sd)] = r
    return out


ok = lambda r: r["class"] == "correct_all"


def diff(a, b, B=10000):
    ks = sorted(set(a) & set(b)); d = [ok(b[k]) - ok(a[k]) for k in ks]; rng = random.Random(0); n = len(d)
    bs = sorted(sum(d[rng.randrange(n)] for _ in range(n)) / n for _ in range(B))
    return 100 * sum(d) / n, 100 * bs[int(.025 * B)], 100 * bs[int(.975 * B)]


def line(name, R, ref=None):
    k = sum(map(ok, R.values())); tok = sum(r.get("out_tokens") or 0 for r in R.values()) / max(1, len(R))
    use = sum(bool(r.get("distractors_called")) for r in R.values())
    s = f"  {name:22s} {k:4d}/{len(R):<4d} ({100 * k / max(1, len(R)):5.1f}%)  tokens {tok:6.0f}  programs calling an extra helper {use}"
    if ref is not None:
        d = diff(ref, R); s += f"   vs K8 {d[0]:+.1f} [{d[1]:+.1f}, {d[2]:+.1f}]"
    return s, k


for m in ("8b", "32b"):
    print(f"\n=== F1, Qwen3-{m}, 5 core tasks (2 seeds x 300)")
    K0, K8 = load(f"S2_C1_geox{m}_dis0"), load(f"S2_C1_geox{m}_dis8")
    out = {}
    for name, R in (("K0 (needed helpers)", K0), ("K8", K8), ("K8 + scope sentence", load(f"S2_B3_geox{m}_k8scope")),
                    ("K8 + S2A", load(f"S2_B3_geox{m}_k8s2a"))):
        s, k = line(name, R, None if name.startswith("K0") or name == "K8" else K8); out[name] = (k, len(R)); print(s)
    k0, k8 = out["K0 (needed helpers)"][0], out["K8"][0]
    for name in ("K8 + scope sentence", "K8 + S2A"):
        print(f"  recovery of the K8 harm by {name}: {(out[name][0] - k8) / max(1, k0 - k8):.2f}")
    if m == "32b":
        print("\n=== F1 format channel, Qwen3-32B, diameter (2 seeds x 60)")
        for name, tag in (("no toolbox", "S2_E2_geox32b_diam_k0"), ("LOW", "S2_E2_geox32b_diam_low"), ("LOW + scope", "S2_B3_geox32b_diamlowscope"),
                          ("LOW + S2A", "S2_B3_geox32b_diamlows2a")):
            R = load(tag); s, _ = line(name, R)
            fmt = sum(pattern(r).startswith("input format") for r in R.values() if not ok(r))
            print(s + f"  | count-line failures {fmt}")
print("\n=== F2 delaunay, seed 1 (60 programs per cell)")
for m in ("8b", "32b"):
    docs = json.load(open(f"{RES}/draft_docs_{m}.json"))
    for name, tag in (("signed (terse)", f"S2_E2_geox{m}_del_signed"), ("hand-written warning", f"S2_E2_geox{m}_del_doc"),
                      ("fixed helper", f"S2_E2_geox{m}_del_fixed")):
        R = load(tag, (1,)); s, _ = line(f"{m} {name}", R); print(s)
    pooled = {}
    for j in range(3):
        R = load(f"S2_B3_geox{m}_deldraft{j + 1}", (1,)); pooled.update({k + (j,): v for k, v in R.items()})
        s, _ = line(f"{m} DRAFT doc {j + 1}", R)
        orient = sum(pattern(r).startswith("orientation") for r in R.values() if not ok(r))
        print(s + f"  | orientation-only failures {orient} | doc: {docs[j]['doc'][:110]}")
    print(f"  {m} DRAFT pooled: {sum(map(ok, pooled.values()))}/{len(pooled)}; doc-writing tokens {sum(d['tokens'] for d in docs) / len(docs):.0f} per doc")
