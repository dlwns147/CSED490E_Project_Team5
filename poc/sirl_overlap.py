"""Overlap audit (PREREG_DIFF, 2026-11-25): 13-gram overlap of our word-problem sets with the training sample SIRL publishes in its repo\n(SIRLTrain/trainset, ~4.2k rows, described there as a lightweight example set, not the full training data). Run on the repo clone\n($POC_DATA/optmath_train/sirl_dl/repo/SIRLTrain); needs pyarrow."""
import json, re
import pyarrow.parquet as pq
from collections import Counter
T = []
for f in ("train", "test"):
    T += [r["en_question"] for r in pq.read_table(f"trainset/gurobi_examples_OR_{f}.parquet").to_pylist()]
toks = lambda t: re.findall(r"[a-z0-9]+", t.lower())
def grams(t, n=13):
    w = toks(t); return {" ".join(w[k:k + n]) for k in range(len(w) - n + 1)}
idx = {}
for k, t in enumerate(T):
    for g in grams(t): idx.setdefault(g, []).append(k)
base = "/home1/leesangjun/SJ/POSTECH/nlp_data/optmath_train/"
sets = {"omtf": [json.loads(l)["q"] for l in open(base + "omtf_items.jsonl")], "omtf2": [json.loads(l)["q"] for l in open(base + "omtf2_items.jsonl")],
        "train8000(OptMATH-Train, control)": [json.loads(l)["q"] for l in open(base + "wp_train_items.jsonl")][:600]}
rd = lambda f: [json.loads(l) for l in open(f)]
R = "/home1/leesangjun/SJ/POSTECH/nlp_data/optmath_train/sirl_dl/repo/test_data/"
sets["OptiBench(control)"] = [r["question"] if "question" in r else r["en_question"] for r in rd(R + "OptiBench.jsonl")]
sets["OptMATH_Bench_193"] = [r["en_question"] for r in rd(R + "OptMATH_Bench_193.jsonl")]
for s, Q in sets.items():
    hit = []; best = []
    for q in Q:
        g = grams(q); c = Counter(k for x in g for k in idx.get(x, []))
        m = max(c.values()) if c else 0; hit.append(bool(c)); best.append(m / max(1, len(g)))
    ex = sum(b >= 0.5 for b in best); n10 = sum(b >= 0.1 for b in best)
    print(f"{s}: n={len(Q)}  any shared 13-gram {sum(hit)}  one training item covers >=10% of the item's 13-grams: {n10}  >=50%: {ex}")
    if s in ("omtf", "omtf2"):
        for q, b in sorted(zip(Q, best), key=lambda z: -z[1])[:2]: print("    top coverage %.2f:" % b, q[:120].replace("\n", " "))
