"""M1 (docs/prereg/PREREG_M1.md): steering-score filter for offered helpers.
For each instance: P0 = the model's draft program written with NO helpers (stored bare run); for every helper h in the offered K-toolbox,
shift(h) = mean token log-prob of P0 under the prompt offering only h (+ deps) minus under the bare prompt (teacher-forced prefill).
Writes scores and, for each tau, a keep-JSON {task-n-inst: [helpers with shift >= -tau]} for run_geo_cross.py --keep_json.
usage: POC_BASE_URL=... python steer_filter.py <draft_tag> <out_tag> <tasks> <n_inst> [inst_prefix] [K=8]"""
import json, os, random, re, sys
from concurrent.futures import ThreadPoolExecutor

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geo_distractors import INCIRCLE_VARIANTS, render_names, toolbox, with_deps  # noqa: E402
from llm import BASE_URL, client  # noqa: E402
from run_geo import base_instance, render, variants  # noqa: E402

RES = "/NAS/SJ/POSTECH/nlp/results"
SIZES = {"hull": (10, 20), "area2": (8, 14), "pip": (8, 14), "segs": (6, 10), "close": (10, 20), "delaunay": (8, 12), "lattice": (8, 14)}
TAUS = (0.005, 0.01, 0.02, 0.05)
ABS_SIG = "def polygon_area2(poly):        # twice the signed area (shoelace, exact)\n    return sum("


def fix_tb(task, tb):   # the same replacements the test runs use: orientation-free in_circle (delaunay), non-negative area (lattice)
    if task == "delaunay" and INCIRCLE_VARIANTS["signed"] in tb:
        tb = tb.replace(INCIRCLE_VARIANTS["signed"], INCIRCLE_VARIANTS["fixed"])
    if task == "lattice" and ABS_SIG in tb:
        tb = tb.replace(ABS_SIG, "def polygon_area2(poly):        # twice the area (shoelace, exact, always >= 0)\n    return abs(sum(")
        tb = tb.replace("for i in range(len(poly)))\n", "for i in range(len(poly))))\n", 1)
    return tb


def prompt_txt(q, fmt, tb):   # identical to run_geo_cross.py prompt_variant 0 with --stdlib
    return (f"{q}\n\nDo not compute the answer by hand. Write a Python 3 program that solves this problem for any input in the following "
            f"stdin format: {fmt}. Print only the answer. Give the program in a single ```python code block. Only the Python standard library "
            f"is available (no third-party packages such as shapely or numpy)." + ("\n\n" + tb if tb else ""))


def tokens(text):
    r = requests.post(BASE_URL.rsplit("/v1", 1)[0] + "/tokenize", json={"model": "local", "prompt": text, "add_special_tokens": False}, timeout=600)
    return r.json()["tokens"]


def mean_lp(prompt, code):   # mean log-prob of the program tokens given the prompt (teacher forcing via prompt_logprobs)
    head = f"<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
    full = head + "```python\n" + code.strip() + "\n```"
    ids, n_pre = tokens(full), len(tokens(head))
    r = client.completions.create(model="local", prompt=full, max_tokens=1, temperature=0, extra_body={"prompt_logprobs": 1})
    plp = r.choices[0].prompt_logprobs
    vals = []
    for pos in range(n_pre, min(len(ids), len(plp))):
        d = plp[pos]
        if not d:
            continue
        ent = d.get(str(ids[pos])) if isinstance(d, dict) else None
        if ent is None and isinstance(d, dict):
            ent = d.get(ids[pos])
        if ent is not None:
            vals.append(ent["logprob"] if isinstance(ent, dict) else ent.logprob)
    return sum(vals) / max(1, len(vals))


def main():
    draft_tag, out_tag, tasks, n_inst = sys.argv[1], sys.argv[2], sys.argv[3].split(","), int(sys.argv[4])
    prefix = sys.argv[5] if len(sys.argv) > 5 else ""
    K = int(sys.argv[6]) if len(sys.argv) > 6 else 8
    drafts = {(r["task"], r["n"], r["inst"]): r for r in map(json.loads, open(f"{RES}/geocross_{draft_tag}.jsonl"))}
    jobs = [(t, n, i) for t in tasks for n in SIZES[t] for i in range(n_inst)]

    def one(job):
        task, n, i = job
        rng = random.Random(f"{prefix}{task}-{n}-{i}")
        V = variants(task, base_instance(task, n, rng), rng)
        q, _, fmt = render(task, V["identity"])
        tb, _ = toolbox(task, K, "related", random.Random(f"{prefix}{task}-{n}-{i}-tb"))
        items = re.findall(r"^def (\w+)\(", tb, re.M)
        d = drafts.get(job, {}).get("code")
        if not d:
            return f"{task}-{n}-{i}", None, items
        base = mean_lp(prompt_txt(q, fmt, ""), d)
        sc = {h: mean_lp(prompt_txt(q, fmt, fix_tb(task, render_names(with_deps([h])))), d) - base for h in items}
        return f"{task}-{n}-{i}", sc, items

    with ThreadPoolExecutor(32) as ex:
        res = list(ex.map(one, jobs))
    json.dump({k: {"scores": sc, "items": it} for k, sc, it in res}, open(f"{RES}/m1_scores_{out_tag}.json", "w"))
    for tau in TAUS:   # no draft -> keep everything (fallback)
        keep = {k: (it if sc is None else [h for h in it if sc[h] >= -tau]) for k, sc, it in res}
        json.dump(keep, open(f"{RES}/m1_keep_{out_tag}_tau{tau}.json", "w"))
        print(f"tau {tau}: mean helpers kept {sum(len(v) for v in keep.values()) / len(keep):.2f} of {sum(len(it) for _, _, it in res) / len(res):.2f}")


if __name__ == "__main__":
    main()
