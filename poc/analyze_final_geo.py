"""Final geometry table (n=300 per run, --stdlib): greedy base/task-matched, sampled base (3 seeds) vs task-matched vs K=8 distractors,
MR-select k=3 and plain vote, paired cluster bootstrap CIs over instances."""
import json, os, subprocess, sys
import numpy as np
RES = "/NAS/SJ/POSTECH/nlp/results"
L = lambda t: {(r["task"], r["n"], r["inst"]): r["class"] == "correct_all" for r in map(json.loads, open(f"{RES}/geocross_{t}.jsonl"))} if os.path.exists(f"{RES}/geocross_{t}.jsonl") else None
rng = np.random.default_rng(0)
def ci(a, b):
    k = sorted(set(a) & set(b)); d = np.array([a[x] - b[x] for x in k], float)
    bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(5000)]
    return f"{100*d.mean():+.1f} [{100*np.percentile(bs,2.5):+.1f}, {100*np.percentile(bs,97.5):+.1f}]"
for m in ["8b", "14b", "32b"]:
    g_b, g_p = L(f"F_geox{m}_base"), L(f"F_geox{m}_pt")
    sb = [L(f"F_geox{m}_base_t07s{s}") for s in (1, 2, 3)]; sp, sd8 = L(f"F_geox{m}_pt_t07s1"), L(f"F_geox{m}_dis8_t07s1")
    pct = lambda d: f"{100*np.mean(list(d.values())):.1f}" if d else "-"
    out = [f"greedy base {pct(g_b)} pt {pct(g_p)}", f"sampled base {'/'.join(pct(d) for d in sb if d)} pt {pct(sp)} dis8 {pct(sd8)}"]
    if sb[0] and sp: out.append(f"pt−base(s1) {ci(sp, sb[0])}")
    if sd8 and sp: out.append(f"dis8−pt {ci(sd8, sp)}")
    if all(sb):
        env = dict(os.environ, MR_PREFIX="F_geox")
        for mode in ([], ["nomr"]):
            r = subprocess.run([sys.executable, f"{os.path.dirname(__file__)}/mr_select.py", m, "1", "base@1,base@2,base@3"] + mode, capture_output=True, text=True, env=env)
            v = r.stdout.split("MR-select ")[1].split("/")[0] if "MR-select" in r.stdout else "?"
            out.append(f"{'vote' if mode else 'MR'} k=3 {100*int(v)/len(sb[0]):.1f}" if v != "?" else "MR ?")
    print(m, " | ".join(out))
