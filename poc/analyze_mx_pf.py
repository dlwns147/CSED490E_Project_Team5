"""Packaging-free summary for PREREG_M2_M4: every condition re-scored with its offered (fixed) toolbox pre-defined for crashed programs
(K = 8 for K8-type conditions incl. M3 / M4 / think; K = 0 for needed-only; none for no-helper runs). Pooled over 2 seeds."""
import json, os, random, re, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, "/NAS/SJ/POSTECH/nlp/poc")
from geo_distractors import toolbox  # noqa: E402
from run_geo import answer, base_instance, render, variants  # noqa: E402
from run_geo_cross import classify  # noqa: E402
from sandbox import run_python  # noqa: E402
from steer_filter import fix_tb  # noqa: E402
from analyze_mx import tags  # noqa: E402

RES = "/NAS/SJ/POSTECH/nlp/results"


def pf_ok(r, K):
    if r["class"] == "correct_all":
        return True
    if r["class"] != "crash" or not r.get("code") or K is None:
        return False
    rng = random.Random(f"{r['task']}-{r['n']}-{r['inst']}")
    V = variants(r["task"], base_instance(r["task"], r["n"], rng), rng)
    tb, _ = toolbox(r["task"], K, "related", random.Random(f"{r['task']}-{r['n']}-{r['inst']}-tb"))
    pre = "\n".join(re.findall(r"```python\n(.*?)```", fix_tb(r["task"], tb), re.S)) + "\n"
    res = {}
    for vn, x in V.items():
        o = run_python(pre + r["code"], render(r["task"], x)[1], timeout=10)
        out = (o.stdout.strip().split() or [None])[-1] if o.status == "ok" else None
        res[vn] = None if out is None and vn == "identity" else (out is not None and out.lower() == answer(r["task"], x))
    return classify(res) == "correct_all"


def rows(tag):
    out = []
    for sd in (1, 2):
        p = f"{RES}/geocross_{tag}_t07s{sd}.jsonl"
        if os.path.exists(p):
            out += [json.loads(l) for l in open(p)]
    return out


KOF = {"K8 (all helpers)": 8, "no helpers": None, "K0 (needed only)": 0, "think-1024": 8, "M4-free": 8, "M4": 8, "M3": 8}
for m in ("8b", "32b"):
    tot = {}
    for g in ("core", "del", "lat"):
        line = f"{m} {g:4s}"
        for name, tag in tags(m, g).items():
            R = rows(tag)
            if not R:
                continue
            with ThreadPoolExecutor(24) as ex:
                k = sum(ex.map(lambda r: pf_ok(r, KOF[name]), R))
            line += f" | {name.split(' (')[0]} {k}/{len(R)}"
            a, b = tot.get(name, (0, 0)); tot[name] = (a + k, b + len(R))
        print(line)
    print(f"{m} POOLED packaging-free: " + " | ".join(f"{n.split(' (')[0]} {100 * a / b:.1f}%" for n, (a, b) in tot.items()))
