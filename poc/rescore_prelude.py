"""Packaging-free re-score (review item 2 follow-up, CPU): re-run stored programs with the offered toolbox code PRE-DEFINED before them
(the model's own definitions come later and override). Programs that only crashed because they called a helper without copying it
(NameError) are then scored on their logic. usage: rescore_prelude.py <geocross-tag> <K> [tasks]"""
import json, random, re, sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root (was hard-coded)
sys.path.insert(0, f"{ROOT}/poc")
from geo_distractors import toolbox  # noqa: E402
from run_geo import answer, base_instance, render, variants  # noqa: E402
from run_geo_cross import classify  # noqa: E402
from sandbox import run_python  # noqa: E402

tag, K = sys.argv[1], int(sys.argv[2])
rows = [json.loads(l) for l in open(f"{ROOT}/results/geocross_{tag}.jsonl")]


def rescore(r):
    if r["class"] != "crash" or not r.get("code"):
        return r["class"], r["class"]
    rng = random.Random(f"{r['task']}-{r['n']}-{r['inst']}")
    V = variants(r["task"], base_instance(r["task"], r["n"], rng), rng)
    tb, _ = toolbox(r["task"], K, "related", random.Random(f"{r['task']}-{r['n']}-{r['inst']}-tb"))
    pre = "\n".join(re.findall(r"```python\n(.*?)```", tb, re.S)) + "\n"
    res = {}
    for vn, x in V.items():
        _, stdin, _ = render(r["task"], x)
        o = run_python(pre + r["code"], stdin, timeout=10)
        out = (o.stdout.strip().split() or [None])[-1] if o.status == "ok" else None
        res[vn] = None if out is None and vn == "identity" else (out is not None and out.lower() == answer(r["task"], x))
    return r["class"], classify(res)


with ThreadPoolExecutor(32) as ex:
    pairs = list(ex.map(rescore, rows))
before = sum(a == "correct_all" for a, _ in pairs); after = sum(b == "correct_all" for _, b in pairs)
print(f"{tag}: correct {before} -> {after} of {len(rows)} with helpers pre-defined | crashes {sum(a == 'crash' for a, _ in pairs)} -> "
      f"{sum(b == 'crash' for _, b in pairs)} | rescued crashes now: {dict(Counter(b for a, b in pairs if a == 'crash'))}")
