"""Packaging-free re-score with the task's helper fixes applied (delaunay: orientation-free in_circle; lattice: non-negative area), for runs
whose toolbox was built with --incircle fixed / --area_helper abs. Crashed programs are re-run on all 8 variants with the offered (fixed)
toolbox pre-defined in front of them. usage: python rescore_pf2.py <K> <tag> [<tag> ...]   (tag incl. _t07sN)"""
import json, random, re, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, "/NAS/SJ/POSTECH/nlp/poc")
from geo_distractors import toolbox  # noqa: E402
from run_geo import answer, base_instance, render, variants  # noqa: E402
from run_geo_cross import classify  # noqa: E402
from sandbox import run_python  # noqa: E402
from steer_filter import fix_tb  # noqa: E402

K = int(sys.argv[1])


def rescore(r):
    if r["class"] != "crash" or not r.get("code"):
        return r["class"]
    rng = random.Random(f"{r['task']}-{r['n']}-{r['inst']}")
    V = variants(r["task"], base_instance(r["task"], r["n"], rng), rng)
    tb, _ = toolbox(r["task"], K, "related", random.Random(f"{r['task']}-{r['n']}-{r['inst']}-tb"))
    pre = "\n".join(re.findall(r"```python\n(.*?)```", fix_tb(r["task"], tb), re.S)) + "\n"
    res = {}
    for vn, x in V.items():
        o = run_python(pre + r["code"], render(r["task"], x)[1], timeout=10)
        out = (o.stdout.strip().split() or [None])[-1] if o.status == "ok" else None
        res[vn] = None if out is None and vn == "identity" else (out is not None and out.lower() == answer(r["task"], x))
    return classify(res)


for tag in sys.argv[2:]:
    rows = [json.loads(l) for l in open(f"/NAS/SJ/POSTECH/nlp/results/geocross_{tag}.jsonl")]
    with ThreadPoolExecutor(24) as ex:
        new = list(ex.map(rescore, rows))
    a = sum(r["class"] == "correct_all" for r in rows); b = sum(c == "correct_all" for c in new)
    print(f"{tag}: {a} -> {b} packaging-free (of {len(rows)})")
