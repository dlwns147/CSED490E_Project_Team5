"""SIRL-B / ORLM-B comparison table (PREREG_DIFF, 2026-11-25): per set, accuracy · tokens · utility of SIRL-32B-COPT, ORLM-8B, the cheap
plurality (3 x gpt-oss-20b freev) and our corrected one-program recipe (gpt-oss-120b medium thinking, thinkfreen, seed mean), and the
paired difference ours-one − SIRL (problem-level bootstrap, 95%). SIRL / ORLM / ours-one are graded by each row's stored
run_nlopt.correct (a printed "No Best Solution" counts on BWOR's two infeasible problems); the cheap plurality keeps wp_plan's convention
(numeric classes only), as in every earlier word-problem table. usage: python wp_sirl_compare.py <set> [<set> ...]"""
import json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wp_plan as W
U = lambda ok, t: 100 * ok - 0.5 * t / 1000


def rows(f):
    p = f"{W.R3}/{f}"
    return {json.loads(l)["id"]: json.loads(l) for l in open(p)} if os.path.exists(p) else None


for st in sys.argv[1:]:
    os.environ["WP_MODE"] = "thinkfreen"; P, G, RN = W.pool("oss120", st)
    os.environ["WP_MODE"] = "freev"; _, GC, _ = W.pool("oss20", st)
    right = lambda i, v: v is not None and RN.correct(v, P[i]["gold"])
    A = {}
    for name, f in (("SIRL-32B", f"opt_sirl32_{st}_copt_s1.jsonl"), ("ORLM-8B", f"opt_orlm8_{st}_copt_s1.jsonl")):
        Z = rows(f)
        if Z:
            A[name] = {i: (bool(Z[i]["correct"]), int(Z[i]["out_tokens"] or 0)) for i in P}
    if GC:
        A["cheap plurality"] = {}
        for i in P:
            C = W.classes(GC.get(i, [])); A["cheap plurality"][i] = (right(i, C[0]["v"] if C else None), sum(int(r.get("out_tokens") or 0) for r in GC.get(i, [])))
    A["ours: one thinking program"] = {i: (sum(bool(r["correct"]) for r in G[i]) / len(G[i]), sum(int(r.get("out_tokens") or 0) for r in G[i]) / len(G[i])) for i in P}
    ids = sorted(P)
    for name, v in A.items():
        print(f"{st:8s} {name:28s} n={len(ids)} accuracy {100*sum(v[i][0] for i in ids)/len(ids):5.1f}%  tokens {sum(v[i][1] for i in ids)/len(ids)/1000:.2f}k  "
              f"utility {sum(U(*v[i]) for i in ids)/len(ids):6.2f}")
    if "SIRL-32B" in A:
        o = A["ours: one thinking program"]; s = A["SIRL-32B"]
        for lab, f in (("utility", lambda i: U(*o[i]) - U(*s[i])), ("accuracy", lambda i: 100 * (o[i][0] - s[i][0])), ("ktok", lambda i: (o[i][1] - s[i][1]) / 1000)):
            d = [f(i) for i in ids]; rng = random.Random(1); bs = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(4000))
            print(f"{st:8s} ours-one − SIRL {lab}: {sum(d)/len(d):+.2f} [{bs[100]:+.2f}, {bs[3899]:+.2f}]")
