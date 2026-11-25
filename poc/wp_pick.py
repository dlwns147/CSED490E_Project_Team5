"""PICK (PREREG_DIFF, 2026-11-25): label-free choice of the arm per word-problem set by one-coin Dawid-Skene EM on answer agreement.
Arms: SIRL-32B s1, gpt-oss-120b thinking (thinkfreen s1), gpt-oss-20b freev s1 (if stored), ORLM-8B s1. usage: python wp_pick.py <set> ..."""
import json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wp_plan as W
U = lambda ok, t: 100 * ok - 0.5 * t / 1000


def load(st):
    P, _, RN = W.pool("oss120", st)
    arms = {}
    for name, f in (("SIRL-32B", f"opt_sirl32_{st}_copt_s1.jsonl"), ("ours-one", f"opt_oss120_{st}_thinkfreen_s1.jsonl"),
                    ("oss20-freev", f"opt_oss20_{st}_freev_s1.jsonl"), ("ORLM-8B", f"opt_orlm8_{st}_copt_s1.jsonl")):
        p = f"{W.R3}/{f}"
        if os.path.exists(p):
            arms[name] = {json.loads(l)["id"]: json.loads(l) for l in open(p)}
    ids = [i for i in P if all(i in a for a in arms.values())]
    return P, RN, arms, ids


def em(val, ids, arms, iters=200):
    """val[arm][i] = class label (int) or None; one-coin model: arm a right w.p. c_a, else uniform over the other classes of the item (+1 unseen)"""
    c = {a: 0.6 for a in arms}; post = {}
    for _ in range(iters):
        for i in ids:
            cl = sorted({val[a][i] for a in arms if val[a][i] is not None}); K = len(cl) + 1
            lp = {}
            for t in cl:
                s = 0.0
                for a in arms:
                    v = val[a][i]
                    if v is None:
                        continue
                    s += math.log(max(1e-9, c[a])) if v == t else math.log(max(1e-9, (1 - c[a]) / max(1, K - 1)))
                lp[t] = s
            m = max(lp.values()) if lp else 0
            z = sum(math.exp(x - m) for x in lp.values()) if lp else 1
            post[i] = {t: math.exp(x - m) / z for t, x in lp.items()}
        new = {}
        for a in arms:
            num = den = 0.0
            for i in ids:
                v = val[a][i]
                if v is not None:
                    num += post[i].get(v, 0.0); den += 1
            new[a] = num / max(1, len(ids))   # a missing value is a wrong answer for the arm's accuracy
        if max(abs(new[a] - c[a]) for a in arms) < 1e-6:
            c = new; break
        c = new
    return c


if __name__ == "__main__":
    tot = {}
    for st in sys.argv[1:]:
        P, RN, A, ids = load(st); arms = list(A)
        val = {a: {} for a in arms}
        for i in ids:
            rows = {a: W.val(A[a][i]) for a in arms}; reps = []
            for a in arms:
                v = rows[a]
                if v is None:
                    val[a][i] = None; continue
                for k, r in enumerate(reps):
                    if RN.correct(v, str(r)):
                        val[a][i] = k; break
                else:
                    reps.append(v); val[a][i] = len(reps) - 1
        est = em(val, ids, arms)
        mt = {a: sum(int(A[a][i].get("out_tokens") or 0) for i in ids) / len(ids) / 1000 for a in arms}
        acc = {a: sum(bool(A[a][i]["correct"]) for i in ids) / len(ids) for a in arms}
        util = {a: 100 * acc[a] - 0.5 * mt[a] for a in arms}
        eu = {a: 100 * est[a] - 0.5 * mt[a] for a in arms}
        pick = max(eu, key=eu.get); best = max(util, key=util.get)
        print(f"{st}: n={len(ids)} est acc {{{', '.join(f'{a} {est[a]:.2f}' for a in arms)}}}  true {{{', '.join(f'{a} {acc[a]:.2f}' for a in arms)}}}  "
              f"PICK {pick} ({util[pick]:.2f})  oracle {best} ({util[best]:.2f})  ours-one {util['ours-one']:.2f}  SIRL {util['SIRL-32B']:.2f}")
        for k, v in (("pick", util[pick]), ("ours", util["ours-one"]), ("sirl", util["SIRL-32B"]), ("oracle", util[best])):
            tot.setdefault(k, []).append(v)
    print("mean over sets:", {k: round(sum(v) / len(v), 2) for k, v in tot.items()})
