"""Offline G2 solution arms (no new generations).
S3 metamorphic VOTING for direct answers: majority of the normalised answers over the 7 equivalent variants
   (ties -> identity's answer); accuracy of the voted answer vs. plain identity accuracy.
S2 input CANONICALISATION wrapper for code: re-run the stored cross-variant programs on every variant after translating
   the input so that min x = min y = 0 (system-level, label-free); compare correct-on-all-variants rates."""
import json, random, sys, glob
from collections import Counter, defaultdict
import numpy as np
sys.path.insert(0, "/NAS/SJ/POSTECH/nlp/poc")
from run_geo import answer, base_instance, render, variants
from sandbox import run_python
RES = "/NAS/SJ/POSTECH/nlp/results"
INV = ["identity", "translate", "rot90", "mirror", "permute", "scale", "big"]

def norm(task, v, p):
    if p is None: return None
    if v == "scale" and task in ("area2", "close"):
        try:
            x = int(p); return str(x // 9) if x % 9 == 0 else None
        except ValueError: return None
    return p

print("S3 metamorphic voting for DIRECT answers (identity-instance accuracy: single answer -> majority over 7 variants)")
for tag in ["geo8b_direct", "geo32b_direct", "geollama8b_direct", "geo8b_direct_canon"]:
    rows = [json.loads(l) for l in open(f"{RES}/geo_{tag}.jsonl")]
    inst = defaultdict(dict)
    for r in rows: inst[(r["task"], r["n"], r["inst"])][r["variant"]] = r
    single, voted = [], []
    for (t, n, i), d in inst.items():
        if not all(v in d for v in INV): continue
        gold = d["identity"]["gold"]
        votes = Counter(x for x in (norm(t, v, d[v]["pred"]) for v in INV) if x is not None)
        top = votes.most_common()
        pick = d["identity"]["pred"] if not top or (len(top) > 1 and top[0][1] == top[1][1]) else top[0][0]
        single.append(d["identity"]["pred"] == gold); voted.append(pick == gold)
    print(f"  {tag:22s} single {np.mean(single):.3f} -> voted {np.mean(voted):.3f}")

def canon(task, x):
    pts = []
    for k, v in x.items():
        if k == "S": pts += [p for s in v for p in s]
        elif k == "q": pts.append(v)
        else: pts += list(v)
    mx, my = min(p[0] for p in pts), min(p[1] for p in pts)
    f = lambda p: (p[0] - mx, p[1] - my)
    out = {}
    for k, v in x.items():
        out[k] = [(f(a), f(b)) for a, b in v] if k == "S" else (f(v) if k == "q" else [f(p) for p in v])
    return out

def run_out(code, task, x):
    _, stdin, _ = render(task, x)
    r = run_python(code, stdin, timeout=10)
    return (r.stdout.strip().split() or [None])[-1].lower() if r.status == "ok" and r.stdout.strip() else None

print("\nS2 input canonicalisation wrapper for CODE (programs correct on all 8 variants)")
from concurrent.futures import ThreadPoolExecutor
for f in ["geox8b", "geox32b", "geoxllama8b", "geox8b_robust", "geox32b_robust"]:
    rows = [json.loads(l) for l in open(f"{RES}/geocross_{f}.jsonl")]
    def ev(r):
        rng = random.Random(f"{r['task']}-{r['n']}-{r['inst']}")
        V = variants(r["task"], base_instance(r["task"], r["n"], rng), rng)
        if not r["code"]: return False, False
        plain = all(run_out(r["code"], r["task"], x) == answer(r["task"], x) for x in V.values())
        wrapped = all(run_out(r["code"], r["task"], canon(r["task"], x)) == answer(r["task"], x) for x in V.values())
        return plain, wrapped
    with ThreadPoolExecutor(32) as ex: R = list(ex.map(ev, rows))
    print(f"  {f:16s} plain {np.mean([a for a,_ in R]):.2f} -> canonicalised {np.mean([b for _,b in R]):.2f}   "
          + " ".join(f"{t}:{np.mean([a for (a,_),r in zip(R,rows) if r['task']==t]):.2f}->{np.mean([b for (_,b),r in zip(R,rows) if r['task']==t]):.2f}" for t in ["pip","segs"]))
