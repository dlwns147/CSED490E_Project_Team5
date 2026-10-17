"""M5 analysis (results/PREREG_M5.md): voting over the M4 draft (no helpers), the M4 rewrite (with helpers) and one all-helpers sample.
Packaging-free: programs run with the offered (fixed) K8 toolbox pre-defined (drafts have no helpers and run as they are).
usage: python analyze_m5.py"""
import json, os, random, re, sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geo_distractors import toolbox  # noqa: E402
from run_geo import answer, base_instance, render, variants  # noqa: E402
from run_geo_mr import MR, expected_rel  # noqa: E402
from sandbox import run_python  # noqa: E402
from steer_filter import fix_tb  # noqa: E402

RES = "/NAS/SJ/POSTECH/nlp/results"
K8TAG = {"core": "S2_C1_geox{m}_dis8", "del": "S2_MX_geox{m}_del_k8", "lat": "S2_MX_geox{m}_lat_k8"}


def load(tag):
    p = f"{RES}/geocross_{tag}.jsonl"
    return {(r["task"], r["n"], r["inst"]): r for r in map(json.loads, open(p))} if os.path.exists(p) else {}


def run_all(code, pre, task, V):   # outputs on every variant (None on failure)
    out = {}
    for vn, x in V.items():
        if not code:
            out[vn] = None; continue
        r = run_python(pre + code, render(task, x)[1], timeout=10)
        out[vn] = (r.stdout.strip().split() or [None])[-1].lower() if r.status == "ok" and r.stdout.strip() else None
    return out


def correct(outs, task, V):
    return all(outs[vn] is not None and outs[vn] == answer(task, x) for vn, x in V.items())


def consistent(outs, task):
    b = outs.get("identity")
    return b is not None and all(outs[v] == expected_rel(task, v, b) for v in MR if not (task == "lattice" and v == "scale"))


def one(args):
    m, g, sd, key, row, k8 = args
    task, n, inst = key
    rng = random.Random(f"{task}-{n}-{inst}")
    V = variants(task, base_instance(task, n, rng), rng)
    tb, _ = toolbox(task, 8, "related", random.Random(f"{task}-{n}-{inst}-tb"))
    pre = "\n".join(re.findall(r"```python\n(.*?)```", fix_tb(task, tb), re.S)) + "\n"
    od, orw, ok8 = run_all(row.get("draft_code"), "", task, V), run_all(row.get("code"), pre, task, V), run_all(k8.get("code") if k8 else None, pre, task, V)
    cd, crw, ck8 = correct(od, task, V), correct(orw, task, V), correct(ok8, task, V)
    ids = [("draft", od["identity"], cd), ("rewrite", orw["identity"], crw), ("k8", ok8["identity"], ck8)]
    valid = [x for x in ids if x[1] is not None]
    cnt = Counter(o for _, o, _ in valid)
    if valid and cnt.most_common(1)[0][1] >= 2:
        vote = cnt.most_common(1)[0][0]; v1 = next(c for _, o, c in valid if o == vote)
    else:
        v1 = crw
    if od["identity"] is not None and od["identity"] == orw["identity"]:
        v2 = crw
    else:
        sd_, sr = consistent(od, task), consistent(orw, task)
        v2 = cd if (sd_ and not sr) else crw
    return m, g, task, cd, crw, ck8, v1, v2, row.get("out_tokens") or 0, (k8.get("out_tokens") or 0) if k8 else 0


if __name__ == "__main__":
    jobs = []
    for m in ("8b", "32b"):
        for g in ("core", "del", "lat"):
            for sd in (1, 2):
                R = load(f"S2_M5_geox{m}_{g}_m4_t07s{sd}"); K = load(K8TAG[g].format(m=m) + f"_t07s{sd}")
                jobs += [(m, g, sd, k, r, K.get(k)) for k, r in R.items()]
    with ThreadPoolExecutor(24) as ex:
        res = list(ex.map(one, jobs))
    for m in ("8b", "32b"):
        X = [r for r in res if r[0] == m]
        if not X:
            continue
        n = len(X)
        for g in ("core", "del", "lat"):
            Y = [r for r in X if r[1] == g]
            if Y:
                print(f"{m} {g:4s} n={len(Y)}: draft {sum(r[3] for r in Y)} | rewrite (M4) {sum(r[4] for r in Y)} | K8 sample {sum(r[5] for r in Y)} | "
                      f"V1 vote {sum(r[6] for r in Y)} | V2 {sum(r[7] for r in Y)}")
        tm4 = sum(r[8] for r in X) / n; tk8 = sum(r[9] for r in X) / n
        print(f"{m} POOLED n={n}: draft {100 * sum(r[3] for r in X) / n:.1f}% | M4 rewrite {100 * sum(r[4] for r in X) / n:.1f}% @ {tm4:.0f} tok | "
              f"V1 {100 * sum(r[6] for r in X) / n:.1f}% @ {tm4 + tk8:.0f} tok | V2 {100 * sum(r[7] for r in X) / n:.1f}% @ {tm4:.0f} tok + checks")
