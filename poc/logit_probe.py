"""Logit-level probe of the distractor mechanism (teacher-forced scoring, no sampling).
For hull instances, score fixed reference programs under different prompts and compare the per-token log-probability:
  P_mono   : textbook monotone chain using orient (correct)
  P_graham : Graham scan built on the offered polar_sort (the distractor-induced algorithm)
  P_colpass: monotone chain + a spurious "remove collinear points" pass that uses on_segment (over-engineering seen in failures)
Prompts: K=0 (only the needed orient), K=8 related helpers ("should use" header), K=8 with the "most are NOT needed" header.
Hypothesis (off-idiom drift): extra helpers raise the model's probability of the helper-based algorithms and lower the textbook one.
Uses vLLM's completions endpoint with prompt_logprobs (Qwen3 chat format, empty think block = no-think).
usage: POC_BASE_URL=... python logit_probe.py <model_tag>"""
import json, os, random, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import client  # noqa: E402
import geo_distractors as D  # noqa: E402
import run_geo as G  # noqa: E402

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
READ = '''import sys
data = sys.stdin.read().split()
n = int(data[0])
pts = [(int(data[1 + 2 * i]), int(data[2 + 2 * i])) for i in range(n)]
'''
ORIENT = "def orient(a, b, c):\n    return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])\n\n"
PROGRAMS = {
    "P_mono": ORIENT + '''##SPLIT##def hull(points):
    points = sorted(set(points))
    if len(points) <= 2:
        return points
    lower, upper = [], []
    for p in points:
        while len(lower) >= 2 and orient(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(points):
        while len(upper) >= 2 and orient(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]

''' + READ + "print(len(hull(pts)))\n",
    "P_graham": ORIENT + D.RELATED["dist2"] + "\n" + D.RELATED["polar_sort"] + '''
##SPLIT##def hull(points):
    points = list(set(points))
    if len(points) <= 2:
        return points
    start = min(points, key=lambda p: (p[1], p[0]))
    rest = polar_sort([p for p in points if p != start], start)
    stack = [start]
    for p in rest:
        while len(stack) >= 2 and orient(stack[-2], stack[-1], p) <= 0:
            stack.pop()
        stack.append(p)
    return stack

''' + READ + "print(len(hull(pts)))\n",
    "P_colpass": ORIENT + D.RELATED["on_segment"] + '''
##SPLIT##def hull(points):
    points = sorted(set(points))
    if len(points) <= 2:
        return points
    lower, upper = [], []
    for p in points:
        while len(lower) >= 2 and orient(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(points):
        while len(upper) >= 2 and orient(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    h = lower[:-1] + upper[:-1]
    # remove collinear points that lie on hull edges
    result = []
    for i in range(len(h)):
        a, b = h[i - 1], h[(i + 1) % len(h)]
        if not on_segment(a, b, h[i]):
            result.append(h[i])
    return result

''' + READ + "print(len(result_or(hull(pts))))\n".replace("result_or(", "(")}


def prompt_text(q, fmt, tb):
    return (f"{q}\n\nDo not compute the answer by hand. Write a Python 3 program that solves this problem for any input in the "
            f"following stdin format: {fmt}. Print only the answer. Give the program in a single ```python code block. Only the "
            f"Python standard library is available (no third-party packages such as shapely or numpy).\n\n{tb}")


def score(prefix, completion):
    """sum and count of log-probs of `completion` tokens given `prefix` (teacher forcing)"""
    def plp(text):
        r = client.completions.create(model="local", prompt=text, max_tokens=1, temperature=0,
                                      extra_body={"prompt_logprobs": 0})
        return r.choices[0].prompt_logprobs
    full, pre = plp(prefix + completion), plp(prefix)
    lps = []
    for d in full[len(pre):]:
        if d:
            v = next(iter(d.values()))
            lps.append(v["logprob"] if isinstance(v, dict) else v.logprob)
    return sum(lps), len(lps)


def main():
    tag = sys.argv[1]
    out = []
    for n in (10, 20):
        for i in range(10):
            rng = random.Random(f"hull-{n}-{i}")
            V = G.variants("hull", G.base_instance("hull", n, rng), rng)
            q, _, fmt = G.render("hull", V["identity"])
            tb0, _ = D.toolbox("hull", 0, "related", random.Random(f"hull-{n}-{i}-tb"))
            tb8, _ = D.toolbox("hull", 8, "related", random.Random(f"hull-{n}-{i}-tb"))
            tb8may, _ = D.toolbox("hull", 8, "related", random.Random(f"hull-{n}-{i}-tb"), "may")
            for cond, tb in [("K0", tb0), ("K8", tb8), ("K8may", tb8may)]:
                head = f"<|im_start|>user\n{prompt_text(q, fmt, tb)}<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n```python\n"
                for name, prog in PROGRAMS.items():
                    helpers_txt, algo_txt = prog.split("##SPLIT##")
                    s, k = score(head + helpers_txt, algo_txt + "```")   # log-prob of the ALGORITHM part only
                    sh, kh = score(head, helpers_txt)                       # log-prob of writing/copying the helper definitions
                    out.append({"n": n, "inst": i, "cond": cond, "prog": name, "sum_lp": s, "ntok": k, "mean_lp": s / max(1, k),
                                "sum_lp_helpers": sh, "ntok_helpers": kh, "sum_lp_full": s + sh})
    json.dump(out, open(f"{RES}/logit_probe_{tag}.json", "w"))
    import numpy as np
    for name in PROGRAMS:
        row = []
        for cond in ("K0", "K8", "K8may"):
            v = [o["sum_lp"] for o in out if o["prog"] == name and o["cond"] == cond]
            row.append(f"{cond} {np.mean(v):8.1f}")
        d8 = [a["sum_lp"] - b["sum_lp"] for a in out for b in out if a["prog"] == b["prog"] == name and a["cond"] == "K8" and b["cond"] == "K0"
              and (a["n"], a["inst"]) == (b["n"], b["inst"])]
        print(f"{tag} {name:10s} algorithm-part log-prob: " + " | ".join(row) + f" | K8-K0 {np.mean(d8):+7.1f} nats (per-instance mean)")
    # preference shift on WHOLE programs (what the model would write from scratch, helper copying included): log-odds vs the monotone chain
    for key, lab in (("sum_lp_full", "whole program"), ("sum_lp", "algorithm part")):
        for alt in ("P_graham", "P_colpass"):
            row = []
            for cond in ("K0", "K8", "K8may"):
                lo = [a[key] - b[key] for a in out for b in out if a["prog"] == alt and b["prog"] == "P_mono" and a["cond"] == b["cond"] == cond
                      and (a["n"], a["inst"]) == (b["n"], b["inst"])]
                row.append(f"{cond} {np.mean(lo):+7.1f}")
            print(f"{tag} log-odds {alt} vs P_mono [{lab}]: " + " | ".join(row) + " nats")


if __name__ == "__main__":
    main()
