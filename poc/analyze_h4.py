"""H4 (results/PREREG_H4.md): 8 related helpers on the full contest-geometry set, paired with the no-helper runs (same problem, seed).
Helper use = the program defines or calls one of the offered helper names. usage: CC_SET=full python analyze_h4.py"""
import json, os, re, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geo_distractors import RELATED  # noqa: E402

RES = "/NAS/SJ/POSTECH/nlp/results/h2"
NAMES = list(RELATED)
uses = lambda code: bool(code) and any(re.search(rf"\b{n}\s*\(", code) for n in NAMES)
from math import comb


def sign_p(a, b):   # two-sided exact sign test on discordant pairs
    n, k = a + b, min(a, b)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n) if n else 1.0


PAIRS = (("q32b_plain", "q32b_k8"), ("oss20_low", "oss20_low_k8"), ("oss20_low", "oss20_low_k8u"), ("oss20_low", "oss20_low_k8may"),
         ("oss20_low_k8", "oss20_low_k8may"), ("oss120_low", "oss120_low_k8"))
for base, k8 in PAIRS:
    if not all(os.path.exists(f"{RES}/cc_full_{t}_s{sd}.jsonl") for t in (base, k8) for sd in (1, 2, 3)):
        continue
    lost = gained = n = sb = sk = 0; tb = tk = 0; use = 0; lost_use = 0; nocode_b = nocode_k = 0; why = Counter()
    for sd in (1, 2, 3):
        B = {r["name"]: r for r in map(json.loads, open(f"{RES}/cc_full_{base}_s{sd}.jsonl"))}
        K = {r["name"]: r for r in map(json.loads, open(f"{RES}/cc_full_{k8}_s{sd}.jsonl"))}
        for nm in B:
            b, k = B[nm], K[nm]; n += 1
            sb += b["passed_all"]; sk += k["passed_all"]; tb += b.get("out_tokens") or 0; tk += k.get("out_tokens") or 0
            u = uses(k["code"]); use += u
            nocode_b += not b["code"]; nocode_k += not k["code"]
            if b["passed_all"] and not k["passed_all"]:
                lost += 1; lost_use += u
                why["no code" if not k["code"] else ("calls helper" if u else "no helper used")] += 1
            if k["passed_all"] and not b["passed_all"]:
                gained += 1
    print(f"{base} vs {k8} (n={n}): no helpers {100 * sb / n:.1f}% @ {tb / n:.0f} tok | 8 helpers {100 * sk / n:.1f}% @ {tk / n:.0f} tok | "
          f"lost {lost}, gained {gained} (sign p = {sign_p(lost, gained):.3f}) | helper use {100 * use / n:.0f}% of programs | no code {nocode_b} -> {nocode_k} | lost: {dict(why)}")
