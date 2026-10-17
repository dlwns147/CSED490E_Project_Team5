"""Final CO table (252 instances): within-1% per arm (3 seeds), paired CI scoped−full / scoped−none, verified best-of-3 (feasible + best objective)."""
import json, os
import numpy as np
RES = "/NAS/SJ/POSTECH/nlp/results"
rng = np.random.default_rng(0)
def L(t):
    f = f"{RES}/co_{t}.jsonl"
    return {r["key"]: r for r in map(json.loads, open(f))} if os.path.exists(f) else None
ok = lambda r: bool(r["feasible"] and r["gap"] is not None and r["gap"] <= 1)
def ci(A, B):
    k = sorted(set(A[0]) & set(B[0])); d = np.array([np.mean([ok(a[x]) for a in A]) - np.mean([ok(b[x]) for b in B]) for x in k])
    bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(5000)]
    return f"{d.mean():+.3f} [{np.percentile(bs,2.5):+.3f}, {np.percentile(bs,97.5):+.3f}]"
def best3(S):
    res = []
    for k in S[0]:
        c = [s[k] for s in S if s[k]["feasible"]]
        if not c: res.append(False); continue
        b = max(c, key=lambda r: r["value"]) if k.startswith("knapsack") else min(c, key=lambda r: r["value"])
        res.append(ok(b))
    return np.mean(res)
for m in ["8b", "14b", "32b"]:
    D = {a: [d for d in (L(f"F_co{m}_{a}_s{s}") for s in (1, 2, 3)) if d] for a in ["nodoc", "doc", "doctask"]}
    if not all(len(v) == 3 for v in D.values()): print(m, "incomplete", {a: len(v) for a, v in D.items()}); continue
    row = " | ".join(f"{a} {np.mean([np.mean([ok(r) for r in s.values()]) for s in D[a]]):.3f} best3 {best3(D[a]):.3f}" for a in D)
    print(m, row, "| scoped−full", ci(D["doctask"], D["doc"]), "| scoped−none", ci(D["doctask"], D["nodoc"]))
