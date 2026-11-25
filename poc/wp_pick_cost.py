"""PICK-COST (PREREG_DIFF, 2026-11-25): PICK with the probe's tokens charged. usage: python wp_pick_cost.py <set> ..."""
import os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wp_pick as K
import wp_plan as W
U = lambda ok, t: 100 * ok - 0.5 * t / 1000
M, D = (10, 20, 30, 50), 300
out = {m: {"gain": [], "right": []} for m in M}
for st in sys.argv[1:]:
    P, RN, A, ids = K.load(st); arms = list(A); V = {a: {} for a in arms}
    for i in ids:
        reps = []
        for a in arms:
            v = W.val(A[a][i])
            if v is None:
                V[a][i] = None; continue
            for k, r in enumerate(reps):
                if RN.correct(v, str(r)):
                    V[a][i] = k; break
            else:
                reps.append(v); V[a][i] = len(reps) - 1
    tk = {a: {i: int(A[a][i].get("out_tokens") or 0) for i in ids} for a in arms}
    ok = {a: {i: bool(A[a][i]["correct"]) for i in ids} for a in arms}
    util = {a: sum(U(ok[a][i], tk[a][i]) for i in ids) / len(ids) for a in arms}
    best = max(util, key=util.get); line = []
    for m in M:
        if m > len(ids):
            continue
        rng = random.Random(1); g, r = [], 0
        for _ in range(D):
            pr = rng.sample(ids, m); est = K.em(V, pr, arms)
            mt = {a: sum(tk[a][i] for i in pr) / m / 1000 for a in arms}
            pick = max(arms, key=lambda a: 100 * est[a] - 0.5 * mt[a]); r += (pick == best)
            s = set(pr); tot = sum(U(ok[pick][i], (sum(tk[a][i] for a in arms) if i in s else tk[pick][i])) for i in ids)
            g.append(tot / len(ids) - util["ours-one"])
        out[m]["gain"].append(sum(g) / D); out[m]["right"].append(r / D)
        line.append(f"m={m}: pick=best {100*r/D:.0f}%  net {sum(g)/D:+.2f}")
    print(f"{st:9s} N={len(ids)} best {best} (free-probe gain {util[best]-util['ours-one']:+.2f})  " + "; ".join(line))
for m in M:
    if out[m]["gain"]:
        print(f"m={m}: mean over {len(out[m]['gain'])} sets of (PICK-COST − always-ours) {sum(out[m]['gain'])/len(out[m]['gain']):+.2f}; "
              f"lowest pick=best share {100*min(out[m]['right']):.0f}%")
