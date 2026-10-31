"""LCM diagnostic (PREREG_LCM, reported item: calibration): fit on one half (k = 30 labels, the first draw), run the planner on the
other half and compare, at every stop, the posterior that the returned answer is right with whether it is; also the fitted classes.
usage: python lcm_calib.py <task> <gen> <peer> <set> [lcm|lcm2|lcm3]"""
import json, os, random, sys, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lcm  # noqa: E402

task, gen, peer, sset = sys.argv[1:5]
var = sys.argv[5] if len(sys.argv) > 5 else "lcm"
dep = "labels" if var == "lcm2" else None   # lcm3: per-class dependence from the labelled questions, three levels, K up to 5
Q = lcm.load(task, gen, peer, sset)
ids = sorted(Q)
half = {h: [i for i in ids if zlib.crc32(i.encode()) % 2 == h] for h in (0, 1)}
rng = random.Random(97 * 0 + 7 * 30 + 0)
lab = set(rng.sample(half[0], 30))
M, bic = lcm.fit_best({i: Q[i] for i in half[0]}, lab, seed=0, dep=dep, levels=3 if var == "lcm3" else 2,
                      Ks=(1, 2, 3, 4, 5) if var == "lcm3" else (1, 2, 3))
print(f"{task} {sset} {gen}<-{peer} ({sys.argv[5] if len(sys.argv) > 5 else 'lcm'}): K {M.K}, pi {[round(x, 2) for x in M.pi]}, th0 {M.th0}, "
      f"th1 {M.th1}, phi {M.phi}")
if var == "lcm3":
    print(f"   th2 {M.th2}")
for t in lcm.TYPES:
    print(f"   a[{t}] {[round(x, 2) for x in M.a[t]]}  x[{t}] {[round(x, 2) for x in M.x[t]]}")
Pl = lcm.Planner(M)
rows = []
for i in half[1]:
    for s in (1, 2, 3):
        sc = lcm.seed_calls(Q[i], s)
        pat, keys = (None,) * 5, {}
        right, tok, made = Pl.run(sc)
        # the posterior of the returned answer: replay to the stopping pattern
        pat = (None,) * 5; keys = {}
        while True:
            Pl.value(pat); kind, arg = Pl.act[pat]
            if kind == "stop":
                p = Pl.right_prob(pat).get(arg, 0.0) if arg is not None else 0.0
                break
            j = arg; k, chk, ok, t = sc[j]
            e = ("X", chk) if k is None else (keys.setdefault(k, len(keys)), chk)
            raw = list(pat); raw[j] = e
            order = []
            for x in raw:
                if x is not None and x[0] != "X" and x[0] not in order:
                    order.append(x[0])
            remap = {g: n for n, g in enumerate(order)}
            keys = {kk: remap[g] for kk, g in keys.items() if g in remap}
            pat = tuple(None if x is None else x if x[0] == "X" else (remap[x[0]], x[1]) for x in raw)
        rows.append((p, right, len(made)))
rows.sort()
n = len(rows)
print(f"   {n} question-seeds: mean posterior of the returned answer {sum(p for p, _, _ in rows) / n:.3f}, realised right "
      f"{sum(r for _, r, _ in rows) / n:.3f}, calls per question-seed {sum(c for _, _, c in rows) / n:.2f}")
for b in range(5):
    seg = rows[b * n // 5:(b + 1) * n // 5]
    print(f"   quintile {b + 1}: posterior {sum(p for p, _, _ in seg) / len(seg):.3f}, right {sum(r for _, r, _ in seg) / len(seg):.3f}")
