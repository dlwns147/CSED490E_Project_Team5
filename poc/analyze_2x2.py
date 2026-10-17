"""Rewriter x solver 2x2 on newer problems: does each solver do better on its OWN rewrites (self-paraphrase effect)?"""
import json
import sys
from collections import defaultdict

import numpy as np

import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root (was hard-coded)
sys.path.insert(0, f"{ROOT}/poc")
from analyze import _contains_seq  # noqa: E402
from run_perturb import load  # noqa: E402

RES = f"{ROOT}/results"
items = {it["name"]: it for it in load(1200, 10**9, "eval", True)}
rwQ = json.load(open(f"{RES}/perturb_rewrites.json")); rwL = json.load(open(f"{RES}/perturb_rewrites_llama.json"))


def valid(rw, n):
    t = rw.get(f"{n}|story")
    return bool(t) and _contains_seq(t.split(), items[n]["tests"][0][0].split())


def acc(tag, version):
    d = defaultdict(list)
    for r in map(json.loads, open(f"{RES}/perturb_{tag}.jsonl")):
        if r["version"] == version:
            d[r["name"]].append(r["verdict"] == "ac")
    return {k: np.mean(v) for k, v in d.items()}


cells = {
    ("Qwen", "orig"): [acc("qwen3-8b", "orig"), acc("rwllama_eval", "orig")],
    ("Qwen", "rwQwen"): [acc("qwen3-8b", "story")],
    ("Qwen", "rwLlama"): [acc("rwllama_eval", "story")],
    ("Llama", "orig"): [acc("rwQ_solL_eval", "orig"), acc("rwL_solL_eval", "orig")],
    ("Llama", "rwQwen"): [acc("rwQ_solL_eval", "story")],
    ("Llama", "rwLlama"): [acc("rwL_solL_eval", "story")],
}
names = [n for n in items if valid(rwQ, n) and valid(rwL, n)
         and all(any(n in d for d in ds) for ds in cells.values())]
M = {k: np.array([np.mean([d[n] for d in ds if n in d]) for n in names]) for k, ds in cells.items()}
print(f"newer problems valid for both rewriters and present in all cells: n={len(names)}")
for s in ("Qwen", "Llama"):
    print(f"  solver {s:5s}: orig {M[(s, 'orig')].mean():.3f}  Qwen-rewrite {M[(s, 'rwQwen')].mean():.3f}  "
          f"Llama-rewrite {M[(s, 'rwLlama')].mean():.3f}")
rng = np.random.default_rng(0)
inter = (M[("Qwen", "rwQwen")] - M[("Qwen", "rwLlama")]) - (M[("Llama", "rwQwen")] - M[("Llama", "rwLlama")])
own = {"Qwen": M[("Qwen", "rwQwen")] - M[("Qwen", "rwLlama")], "Llama": M[("Llama", "rwLlama")] - M[("Llama", "rwQwen")]}
for k, v in list(own.items()) + [("interaction (self-paraphrase)", inter)]:
    b = rng.choice(v, (4000, len(v))).mean(1)
    print(f"  {k:30s} own-minus-other {v.mean():+.3f} [{np.percentile(b, 2.5):+.3f},{np.percentile(b, 97.5):+.3f}]")
