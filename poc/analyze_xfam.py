"""Cross-family recipe check (X_ tags): geometry greedy base/pt, sampled base x3 → MR-select k=3, K=0 vs K=8 toolbox; CO no doc/full/scoped."""
import json, os, subprocess, sys
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root (was hard-coded)
R = f"{ROOT}/results"
rng = np.random.default_rng(0)
G = lambda t: {(r["task"], r["n"], r["inst"]): r["class"] == "correct_all" for r in map(json.loads, open(f"{R}/geocross_{t}.jsonl"))} if os.path.exists(f"{R}/geocross_{t}.jsonl") else None
ok = lambda r: bool(r["feasible"] and r["gap"] is not None and r["gap"] <= 1)
def ci(a, b):
    k = sorted(set(a) & set(b)); d = np.array([a[x] - b[x] for x in k], float)
    bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(4000)]
    return f"{100*d.mean():+.1f} [{100*np.percentile(bs,2.5):+.1f},{100*np.percentile(bs,97.5):+.1f}]"
for m in sys.argv[1:] or ["llama70", "granite8", "gemma27"]:
    pc = lambda d: f"{100*np.mean(list(d.values())):.1f}" if d else "-"
    gb, gp, d0, d8 = G(f"X_geox{m}_base"), G(f"X_geox{m}_pt"), G(f"X_geox{m}_dis0_t07s1"), G(f"X_geox{m}_dis8_t07s1")
    sb = [G(f"X_geox{m}_base_t07s{s}") for s in (1, 2, 3)]
    out = [f"greedy base {pc(gb)} pt {pc(gp)}", f"samples {'/'.join(pc(x) for x in sb if x)}", f"K0 {pc(d0)} K8 {pc(d8)}" + (f" Δ {ci(d8, d0)}" if d0 and d8 else "")]
    if all(sb):
        for mode in ([], ["nomr"]):
            r = subprocess.run([sys.executable, f"{os.path.dirname(__file__)}/mr_select.py", m, "1", "base@1,base@2,base@3"] + mode,
                               capture_output=True, text=True, env=dict(os.environ, MR_PREFIX="X_geox"))
            v = r.stdout.split("MR-select ")[1].split("/")[0] if "MR-select" in r.stdout else None
            out.append(f"{'vote' if mode else 'MR'}k3 {100*int(v)/len(sb[0]):.1f}" if v else "MR ?")
    co = []
    for a in ["nodoc", "doc", "doctask"]:
        f = f"{R}/co_X_co{m}_{a}.jsonl"
        if os.path.exists(f):
            rs = [json.loads(l) for l in open(f)]; co.append(f"{a} {np.mean([ok(r) for r in rs]):.2f}")
    print(m, " | ".join(out + co))
