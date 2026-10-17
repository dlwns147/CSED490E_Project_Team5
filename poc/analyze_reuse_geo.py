"""V1G (docs/prereg/PREREG_V.md): verify once, reuse on the synthetic geometry tasks under 8 related helpers. Candidates = K8 programs for the
5 validation instances (n = 10, inst 0-4, seeds 1-2); label-free selection by metamorphic consistency on those; the chosen program runs on
the other 55 instances (correct on all 8 variants); helpers pre-defined.
usage: python analyze_reuse_geo.py"""
import json, os, re, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_m5 import consistent, correct, run_all  # noqa: E402
from geo_distractors import RELATED, render_names  # noqa: E402
from run_geo import base_instance, variants  # noqa: E402
import random  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root (was hard-coded)
RES = f"{ROOT}/results"
PRE = "\n".join(re.findall(r"```python\n(.*?)```", render_names(list(RELATED)), re.S)) + "\n"


def V_of(task, n, inst):
    rng = random.Random(f"{task}-{n}-{inst}")
    return variants(task, base_instance(task, n, rng), rng)


for m in ("8b", "32b"):
    rows = [r for sd in (1, 2) for r in map(json.loads, open(f"{RES}/geocross_S2_C1_geox{m}_dis8_t07s{sd}.jsonl"))]
    for task in ("hull", "area2", "pip", "segs", "close"):
        R = [r for r in rows if r["task"] == task]
        n0 = min(r["n"] for r in R); n1 = max(r["n"] for r in R)
        val = [(n0, i) for i in range(5)] if not os.environ.get("VAL_MIX") else [(n0, 0), (n0, 1), (n0, 2), (n1, 0), (n1, 1)]   # V1G-mix
        test = sorted({(r["n"], r["inst"]) for r in R} - set(val))
        cands = [r for r in R if r["n"] == n0 and r["inst"] < 5 and r.get("code")]   # candidates: the first 5 smallest-n instances
        def score(c):   # (label-free metamorphic consistency, labelled correctness) on the 5 validation instances
            outs = [(run_all(c["code"], PRE, task, V_of(task, n, i)), V_of(task, n, i)) for n, i in val]
            return sum(consistent(o, task) for o, _ in outs), sum(correct(o, task, v) for o, v in outs)
        with ThreadPoolExecutor(10) as ex:
            sc = list(ex.map(score, cands))
        n_correct_cands = sum(r["class"] == "correct_all" for r in cands)
        per = sum(r["class"] == "correct_all" for r in R if (r["n"], r["inst"]) in set(test)) / max(1, sum((r["n"], r["inst"]) in set(test) for r in R))
        res = {}
        tb = {}
        if os.environ.get("TIEBREAK"):   # V1G-tb: MBR-exec among the candidates tied on the labelled score, on 10 fresh unlabelled inputs
            top = max(sc[k][1] for k in range(len(cands))); tied = [k for k in range(len(cands)) if sc[k][1] == top]
            fresh = [V_of(task, n1, 100 + j)["identity"] for j in range(10)]
            from run_geo import render
            from sandbox import run_python
            outs = {k: [(lambda r: r.stdout.strip() if r.status == "ok" else None)(run_python(PRE + cands[k]["code"], render(task, x)[1], timeout=10)) for x in fresh] for k in tied}
            for k in tied:
                tb[k] = sum(a is not None and a == b for j in tied if j != k for a, b in zip(outs[k], outs[j]))
        sels = (("MR-consistency (label-free)", lambda k: sc[k][0]), ("5 labelled instances", lambda k: (sc[k][1], tb.get(k, 0))))
        for sel, key in sels:
            best = cands[max(range(len(cands)), key=key)]
            with ThreadPoolExecutor(16) as ex:
                ok = list(ex.map(lambda ni: correct(run_all(best["code"], PRE, task, V_of(task, *ni)), task, V_of(task, *ni)), test))
            res[sel] = 100 * sum(ok) / len(test)
        print(f"Qwen3-{m} {task}: per-instance K8 {100 * per:.0f}% | candidates {len(cands)} (correct {n_correct_cands}), (consistent, correct) on validation "
              f"{sorted(sc, reverse=True)[:5]} | reused on {len(test)} test: " + "; ".join(f"{k} {v:.0f}%" for k, v in res.items()), flush=True)
