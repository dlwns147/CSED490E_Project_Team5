"""PoC #1 rewriter-control analysis: story(Llama-rewritten) - orig, newer (eval) vs older (train), strict I/O filter."""
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
rng = np.random.default_rng(0)


def diffs(src):
    items = {it["name"]: it for it in load(1200, 10**9, src, True)}
    rwf = f"{RES}/perturb_rewrites_llama.json" if src == "eval" else f"{RES}/perturb_rewrites_{src}_llama.json"
    rw = json.load(open(rwf))
    by = defaultdict(lambda: defaultdict(list))
    for r in map(json.loads, open(f"{RES}/perturb_rwllama_{src}.jsonl")):
        by[r["version"]][r["name"]].append(r["verdict"] == "ac")
    ok = [n for n in by["orig"] if n in by["story"] and rw.get(f"{n}|story")
          and _contains_seq(rw[f"{n}|story"].split(), items[n]["tests"][0][0].split())]
    o = np.array([np.mean(by["orig"][n]) for n in ok]); s = np.array([np.mean(by["story"][n]) for n in ok])
    return o, s, len(by["orig"])


def ci(x):
    b = rng.choice(x, (4000, len(x))).mean(1)
    return np.percentile(b, [2.5, 97.5])


res = {}
for src in sys.argv[1:] or ["eval", "train"]:
    try:
        o, s, n_all = diffs(src)
    except FileNotFoundError:
        continue
    d = s - o
    res[src] = d
    lo, hi = ci(d)
    print(f"{src:5s} n={len(d)} (of {n_all}; io-broken excluded)  orig {o.mean():.3f}  story(Llama) {s.mean():.3f}  "
          f"story-orig {d.mean():+.3f} [{lo:+.3f},{hi:+.3f}]")
if len(res) == 2:
    a, b = res["eval"], res["train"]
    bs = [rng.choice(a, len(a)).mean() - rng.choice(b, len(b)).mean() for _ in range(4000)]
    print(f"DiD (newer - older) = {a.mean() - b.mean():+.3f} [{np.percentile(bs, 2.5):+.3f},{np.percentile(bs, 97.5):+.3f}]")
