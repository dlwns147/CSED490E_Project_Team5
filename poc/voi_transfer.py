"""PREREG_VOI amendment 7 (2026-11-22): fit on Project Euler dev (labelled or not), act on fresh Project Euler 943-992.
usage: python3 poc/voi_transfer.py"""
import math
import sys
from collections import defaultdict
sys.argv = [sys.argv[0], "eulert"]
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import voi  # noqa: E402

Pd, srcs = voi.load_euler("euler"); Pt, srcs_t = voi.load_euler("eulert")
assert srcs == srcs_t
dev = sorted(i for i in Pd if all(len(Pd[i].get(s, [])) for s in srcs)); tst = sorted(i for i in Pt if all(len(Pt[i].get(s, [])) for s in srcs))
probs = [[(s, k, ck, t) for s in srcs for k, t, ok, ck in Pd[i][s]] for i in dev]
labs = ["GOLD" if any(ok for s in srcs for _, _, ok, _ in Pd[i][s]) else None for i in dev]
best = None
for D in range(1, voi.DMAX + 1):
    m = voi.Model(srcs, D); ll = m.fit(probs)
    bic = -2 * ll + (len(srcs) * D * 4 + D) * math.log(len(probs))
    if best is None or bic < best[0]:
        best = (bic, D, m)
lf = best[2]; ss = voi.Model(srcs, best[1]); ss.fit(probs, labels=labs)
cost = {s: sum(t for i in dev for _, t, _, _ in Pd[i][s]) / sum(len(Pd[i][s]) for i in dev) for s in srcs}
cands = [[(a, "last")] for a in srcs] + [[(a, "any"), (b, "last")] for a in srcs for b in srcs if a != b] + \
        [[(a, None), (b, "agree"), (c, "last")] for a in srcs for b in srcs if a != b for c in srcs]
lad = max(cands, key=lambda st: sum(voi.U(*voi.ladder(Pd[i], st)) for i in dev))
sing = max(srcs, key=lambda s: sum(voi.U(*voi.base_single(Pd[i], s)) for i in dev))
th = max([s for s in srcs if "think" in s], key=lambda s: sum(voi.U(*voi.base_sc(Pd[i], s)) for i in dev))
R = defaultdict(dict)
for i in tst:
    R["VOI-transfer (labelled dev)"][i] = voi.run_voi(ss, Pt[i], cost)[:2]
    R["VOI-transfer (label-free dev)"][i] = voi.run_voi(lf, Pt[i], cost)[:2]
    R[f"best single on dev: {sing}"][i] = voi.base_single(Pt[i], sing)
    R[f"SC@3 {th}"][i] = voi.base_sc(Pt[i], th)
    R["label-fitted ladder (dev labels)"][i] = voi.ladder(Pt[i], lad)
print(f"fit on {len(dev)} dev problems (D={best[1]}), act on {len(tst)} fresh; ladder {lad}")
for a, r in R.items():
    print(f"  {a:42s} {100 * sum(v[0] for v in r.values()) / len(r):5.1f}%  {sum(v[1] for v in r.values()) / len(r) / 1000:6.2f}k  "
          f"U {sum(voi.U(*v) for v in r.values()) / len(r):6.2f}")
for a in list(R)[2:]:
    for b in ("VOI-transfer (labelled dev)", "VOI-transfer (label-free dev)"):
        mu, lo, hi, p = voi.boot({i: voi.U(*R[b][i]) - voi.U(*R[a][i]) for i in tst})
        print(f"  {b} - {a}: {mu:+.2f} [{lo:+.2f}, {hi:+.2f}] p={p:.4f}")
