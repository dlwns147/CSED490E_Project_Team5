"""V1A (docs/prereg/PREREG_V.md): label-free reuse on the synthetic tasks: candidates scored by agreement with a model-written brute-force
oracle on the 5 validation instances (all 8 variants); the best candidate is reused on the 55 test instances.
usage: POC_BASE_URL=... python reuse_oracle_geo.py <8b|32b>"""
import json, os, random, re, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_m5 import correct, run_all  # noqa: E402
from geo_distractors import RELATED, render_names  # noqa: E402
from llm import chat, last_block  # noqa: E402
from run_geo import answer, base_instance, render, variants  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root (was hard-coded)
RES = f"{ROOT}/results"
PRE = "\n".join(re.findall(r"```python\n(.*?)```", render_names(list(RELATED)), re.S)) + "\n"
m = sys.argv[1]


def V_of(task, n, inst):
    rng = random.Random(f"{task}-{n}-{inst}")
    return variants(task, base_instance(task, n, rng), rng)


rows = [r for sd in (1, 2) for r in map(json.loads, open(f"{RES}/geocross_S2_C1_geox{m}_dis8_t07s{sd}.jsonl"))]
out = {}
for task in ("hull", "area2", "pip", "segs", "close"):
    R = [r for r in rows if r["task"] == task]
    n0 = min(r["n"] for r in R); val = [(n0, i) for i in range(5)]
    test = sorted({(r["n"], r["inst"]) for r in R} - set(val))
    cands = [r for r in R if (r["n"], r["inst"]) in val and r.get("code")]
    q, _, fmt = render(task, V_of(task, *val[0])["identity"])
    o = chat(f"{q}\n\nWrite a SLOW but obviously correct brute-force Python 3 program that solves this problem for any input in the stdin "
             f"format: {fmt}. Inputs are small (at most 20 points), so prefer exhaustive enumeration and direct checks over clever algorithms. "
             f"Print only the answer. Only the Python standard library is available. Give the program in a single ```python code block.",
             max_tokens=3000, temperature=0.7, seed=17)
    oracle = last_block(o["text"] or "", ("python", "py")) or ""
    VV = [V_of(task, *ni) for ni in val]
    oo = [run_all(oracle, "", task, V) for V in VV]
    oracle_ok = sum(correct(x, task, V) for x, V in zip(oo, VV))

    def agree(c):
        cc = [run_all(c["code"], PRE, task, V) for V in VV]
        return sum(a[v] is not None and a[v] == b[v] for a, b in zip(cc, oo) for v in a)
    with ThreadPoolExecutor(10) as ex:
        sc = list(ex.map(agree, cands))
    best = cands[max(range(len(cands)), key=lambda k: sc[k])]
    with ThreadPoolExecutor(16) as ex:
        ok = list(ex.map(lambda ni: correct(run_all(best["code"], PRE, task, V_of(task, *ni)), task, V_of(task, *ni)), test))
    out[task] = {"oracle_correct_val": oracle_ok, "agreement": sorted(sc, reverse=True), "reuse": 100 * sum(ok) / len(test),
                 "oracle_tokens": o.get("out_tokens")}
    print(f"Qwen3-{m} {task}: oracle correct on {oracle_ok}/5 validation instances | agreement scores {sorted(sc, reverse=True)[:5]} (max 40) | "
          f"oracle-selected reuse {out[task]['reuse']:.0f}% on {len(test)} test | oracle tokens {o.get('out_tokens')}", flush=True)
json.dump(out, open(f"{RES}/reuse_v1a_{m}.json", "w"), indent=1)
