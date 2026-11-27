"""CONF-MC scorer (PREREG_DIFF, 2026-11-27): DeepConf-style selection between two OWN-E attempts on MathConstruct (seeds 5, 6) and the AUROC of
free per-attempt signals for right vs wrong constructions. Arms per instance (both orders averaged): ONE, CONF-TAIL / CONF-LOW / CONF-MEAN (keep the
attempt with the higher confidence), SHORT (the attempt with fewer tokens), ORACLE2. Clustered by problem. usage: python conf_mc_score.py [seedA seedB]"""
import json, os, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import tir_score as S
R = S.R; U = S.U


def main(a=5, b=6):
    L = lambda s: {z["id"]: z for z in map(json.loads, open(f"{R}/tirsublp_OWN_mcong_medium_s{s}.jsonl"))}
    A, B = L(a), L(b); ks = sorted(set(A) & set(B)); X = [z for k in ks for z in (A[k], B[k])]
    print(f"{len(ks)} instances, {len({k.split('__')[0] for k in ks})} problems; right {sum(z['correct'] for z in X)} of {len(X)} attempts")
    def auroc(f):
        P = [f(z) for z in X if z["correct"] and f(z) is not None]; N = [f(z) for z in X if not z["correct"] and f(z) is not None]
        return sum((p > n) + 0.5 * (p == n) for p in P for n in N) / max(1, len(P) * len(N))
    for name, f in (("tail confidence", lambda z: (z.get("lp") or {}).get("tail_conf")), ("lowest-group confidence", lambda z: (z.get("lp") or {}).get("lowest_group_conf")),
                    ("mean confidence", lambda z: (z.get("lp") or {}).get("mean_conf")), ("mean log-prob", lambda z: (z.get("lp") or {}).get("mean_lp")),
                    ("fewer tokens", lambda z: -z["out_tokens"]), ("fewer tool calls", lambda z: -z["calls"])):
        print(f"   AUROC right vs wrong, {name}: {auroc(f):.3f}")
    c = lambda z: float(bool(z["correct"])); t = lambda z: z["out_tokens"]; arms = collections.defaultdict(dict)
    pick = lambda key, x, y: y if ((y.get("lp") or {}).get(key) or -1e9) > ((x.get("lp") or {}).get(key) or -1e9) else x
    for k in ks:
        v = collections.defaultdict(list)
        for x, y in ((A[k], B[k]), (B[k], A[k])):
            v["ONE"].append((c(x), t(x))); v["ORACLE2"].append((max(c(x), c(y)), t(x) + t(y)))
            for arm, key in (("CONF-TAIL", "tail_conf"), ("CONF-LOW", "lowest_group_conf"), ("CONF-MEAN", "mean_conf")):
                v[arm].append((c(pick(key, x, y)), t(x) + t(y)))
            v["SHORT"].append((c(y if t(y) < t(x) else x), t(x) + t(y)))
        for arm, w in v.items():
            arms[arm][k] = (sum(p for p, _ in w) / len(w), sum(q for _, q in w) / len(w))
    key = [k.split("__")[0] for k in ks]; one = sum(arms["ONE"][k][0] for k in ks); orc = sum(arms["ORACLE2"][k][0] for k in ks)
    for arm, d in arms.items():
        print(f"   {arm:9s} {100*sum(d[k][0] for k in ks)/len(ks):.1f}% @ {sum(d[k][1] for k in ks)/len(ks)/1000:.2f}k utility {sum(U(*d[k]) for k in ks)/len(ks):.2f}"
              + (f"  share of the room {(sum(d[k][0] for k in ks)-one)/max(1e-9, orc-one):.2f}" if arm not in ("ONE", "ORACLE2") else ""))
    for x, y in (("CONF-TAIL", "ONE"), ("CONF-TAIL", "SHORT"), ("CONF-LOW", "ONE")):
        print(f"   {x} − {y}: accuracy {S.ci([100*(arms[x][k][0]-arms[y][k][0]) for k in ks], key)} utility {S.ci([U(*arms[x][k])-U(*arms[y][k]) for k in ks], key)}")


if __name__ == "__main__":
    main(*[int(x) for x in sys.argv[1:3]])
