"""Analysis for docs/prereg/PREREG_M2_M4.md: M4 (algorithm first), M4-free (no keep-the-algorithm instruction), M3 (per-helper probe), M2 (probe
sentence), against all helpers (K8), no helpers, needed-only (K0) and think-1,024; TroVE-style majority over modes computed offline.
Accuracy = correct on all 8 variants (k of n, 2 seeds pooled); tokens = output tokens per instance incl. drafts / probes.
usage: python analyze_mx.py"""
import json, os, random, sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_geo import base_instance, render, variants  # noqa: E402
from sandbox import run_python  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root (was hard-coded)
RES = f"{ROOT}/results"


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
    ks = sorted(set(a) & set(b)); d = [ok(b[k]) - ok(a[k]) for k in ks]
    if not d:
        return None
    rng = random.Random(0); n = len(d); bs = sorted(sum(d[rng.randrange(n)] for _ in range(n)) / n for _ in range(B))
    return 100 * sum(d) / n, 100 * bs[int(.025 * B)], 100 * bs[int(.975 * B)]


def tags(m, g):
    if g == "core":
        return {"K8 (all helpers)": f"S2_C1_geox{m}_dis8", "no helpers": f"S2_MX_geox{m}_core_bare", "K0 (needed only)": f"S2_C1_geox{m}_dis0",
                "think-1024": f"S2_MX_geox{m}_core_think1024", "M4-free": f"S2_MX_geox{m}_core_m4free", "M4": f"S2_MX_geox{m}_core_m4",
                "M3": f"S2_MX_geox{m}_core_m3"}
    if g == "del":
        return {"K8 (all helpers)": f"S2_MX_geox{m}_del_k8", "no helpers": f"S2_E2_geox{m}_del_none", "K0 (needed only)": f"S2_E2_geox{m}_del_fixed",
                "think-1024": f"S2_MX_geox{m}_del_think1024", "M4-free": f"S2_MX_geox{m}_del_m4free", "M4": f"S2_MX_geox{m}_del_m4",
                "M3": f"S2_MX_geox{m}_del_m3"}
    return {"K8 (all helpers)": f"S2_MX_geox{m}_lat_k8", "no helpers": f"S2_MX_geox{m}_lat_bare", "K0 (needed only)": f"S2_MX_geox{m}_lat_k0",
            "think-1024": f"S2_MX_geox{m}_lat_think1024", "M4-free": f"S2_MX_geox{m}_lat_m4free", "M4": f"S2_MX_geox{m}_lat_m4",
            "M3": f"S2_MX_geox{m}_lat_m3"}


def out1(code, task, n, inst):
    if not code:
        return None
    rng = random.Random(f"{task}-{n}-{inst}")
    x = variants(task, base_instance(task, n, rng), rng)["identity"]
    r = run_python(code, render(task, x)[1], timeout=10)
    return (r.stdout.strip().split() or [None])[-1] if r.status == "ok" and r.stdout.strip() else None


def trove(K8, bare):   # majority answer on the given input over the 4 samples of the two modes (K8 s1, s2; no helpers s1, s2)
    keys = sorted({k[:3] for k in K8} & {k[:3] for k in bare})
    def one(k):
        c = [d.get(k + (sd,)) for d in (K8, bare) for sd in (1, 2)]
        c = [r for r in c if r]
        outs = [(r, out1(r.get("code"), *k)) for r in c]
        valid = [(r, o) for r, o in outs if o is not None]
        if not valid:
            return False
        vote = Counter(o for _, o in valid).most_common(1)[0][0]
        return ok(next(r for r, o in valid if o == vote))
    with ThreadPoolExecutor(24) as ex:
        res = list(ex.map(one, keys))
    return sum(res), len(res)


def m3_tokens(m, g):
    tot = n = 0
    for sd in (1, 2):
        p = f"{RES}/m3_probe_{m}_{g}_s{sd}.json"
        if os.path.exists(p):
            for r in json.load(open(p)):
                tot += r["probe_tokens"]; n += 1
    return tot / n if n else 0


for m in ("8b", "32b"):
    pooled = Counter(); pooled_n = Counter(); pooled_tok = Counter()
    for g in ("core", "del", "lat"):
        T = tags(m, g); D = {k: load(v) for k, v in T.items()}
        print(f"\n=== Qwen3-{m} {g}")
        for name, R in D.items():
            if not R:
                print(f"  {name:18s} (missing)"); continue
            tok = sum((r.get("out_tokens") or 0) for r in R.values()) / len(R)
            if name == "M3":
                tok += m3_tokens(m, g) + sum((r.get("out_tokens") or 0) for r in D["no helpers"].values()) / max(1, len(D["no helpers"]))
            k = sum(map(ok, R.values()))
            line = f"  {name:18s} {k:4d}/{len(R):<4d} ({100 * k / len(R):5.1f}%) @ {tok:6.0f} tok"
            for ref in ("K8 (all helpers)", "no helpers"):
                if name not in (ref,) and D[ref]:
                    d = diff(D[ref], R); line += f" | vs {ref.split(' (')[0]} {d[0]:+.1f} [{d[1]:+.1f},{d[2]:+.1f}]" if d else ""
            print(line)
            pooled[name] += k; pooled_n[name] += len(R); pooled_tok[name] += tok * len(R)
        if D["K8 (all helpers)"] and D["no helpers"]:
            k, n = trove(D["K8 (all helpers)"], D["no helpers"]); print(f"  TroVE-style mode majority (4 samples, per instance): {k}/{n} ({100 * k / n:.1f}%)")
        if m == "8b":
            for sd in (1, 2):
                p = f"{RES}/m3_probe_{m}_{g}_s{sd}.json"
                if os.path.exists(p):
                    P = json.load(open(p)); print(f"  M3 s{sd}: kept {sum(len(r['kept']) for r in P) / len(P):.1f} of {sum(len(r['items']) for r in P) / len(P):.1f} helpers;"
                                                   f" MR-select over draft + per-helper programs {sum(r['mrselect_ok'] for r in P)}/{len(P)}")
    print(f"\n=== Qwen3-{m} pooled over the 7 tasks")
    for name in pooled:
        print(f"  {name:18s} {100 * pooled[name] / pooled_n[name]:5.1f}% @ {pooled_tok[name] / pooled_n[name]:6.0f} tok  (n={pooled_n[name]})")
    print(f"\n=== M2 (probe sentence), Qwen3-{m}")
    for g, refs in (("delaunay", (f"S2_E2_geox{m}_del_signed", f"S2_E2_geox{m}_del_doc", f"S2_MX_geox{m}_del_m2", f"S2_E2_geox{m}_del_fixed")),
                    ("lattice", (f"S2_MX_geox{m}_lat_k0signed", f"S2_MX_geox{m}_lat_k0doc", f"S2_MX_geox{m}_lat_m2", f"S2_MX_geox{m}_lat_k0"))):
        Rs = [load(t) for t in refs]
        print(f"  {g:9s} " + " | ".join(f"{lab} {sum(map(ok, R.values()))}/{len(R)}" for lab, R in zip(("terse", "hand warning", "PROBE", "fixed"), Rs)))
