"""LCM diagnostic (PREREG_LCM addendum LCM-3): the planner's stop patterns on one cell (LCM-2, k = 30, the first draw, fitted on half 0, run on
half 1): how often each, its posterior of the returned answer and how often that answer is right.
usage: python3.11 poc/lcm_patterns.py <task> <gen> <peer> <set>"""
import collections, os, random, sys, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lcm
task, gen, peer, sset = sys.argv[1:5]
Q = lcm.load(task, gen, peer, sset); ids = sorted(Q)
half = {h: [i for i in ids if zlib.crc32(i.encode()) % 2 == h] for h in (0, 1)}
lab = set(random.Random(97 * 0 + 7 * 30 + 0).sample(half[0], 30))
M, bic = lcm.fit_best({i: Q[i] for i in half[0]}, lab, seed=0, dep="labels")
Pl = lcm.Planner(M)
names = ["N", "P", "SB", "T", "T2"]
stat = collections.defaultdict(lambda: [0, 0.0, 0, 0])
for i in half[1]:
    for s in (1, 2, 3):
        sc = lcm.seed_calls(Q[i], s)
        pat, keys = (None,) * 5, {}
        while True:
            Pl.value(pat); kind, arg = Pl.act[pat]
            if kind == "stop":
                p = Pl.right_prob(pat).get(arg, 0.0) if arg is not None else 0.0
                k = next((k for k, g in keys.items() if g == arg), None)
                right = k is not None and any(o for kk, c, o, t in sc if kk == k)
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
        sig = " ".join(f"{n}:{'-' if e is None else ('X' if e[0] == 'X' else chr(65 + e[0])) + ('+' if e[1] else '!')}" for n, e in zip(names, pat)) + f" -> {chr(65 + arg) if arg is not None else '-'}"
        st = stat[sig]; st[0] += 1; st[1] += p; st[2] += right
tot = sum(v[0] for v in stat.values())
print(f"{task} {sset} {gen}<-{peer}: K {M.K}; th0 {M.th0[0]} th1 {M.th1[0]} phi {M.phi[0]}; {tot} question-seeds")
for sig, (n, ps, r, _) in sorted(stat.items(), key=lambda kv: -kv[1][0])[:18]:
    print(f"  {n:5d} ({100*n/tot:4.1f}%)  posterior {ps/n:.3f}  right {r/n:.3f}   {sig}")
