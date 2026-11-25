"""CLEAN (PREREG_DIFF, 2026-11-25): OptiMind's expert-cleaned OptMATH / IndustryOR / Mamo-Complex; arms graded by each row's stored
run_nlopt.correct (one reader). ours = gpt-oss-120b medium thinking, corrected prompt, seeds 1-2 (mean). usage: python wp_clean.py"""
import json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wp_plan as W
U = lambda ok, t: 100 * ok - 0.5 * t / 1000
SETS = ("optc", "indc", "mamoc")
M = "thinkfreenE" if os.environ.get("WP_ENVFIX") else "thinkfreen"   # REGRADE (PREREG_DIFF): our CP-SAT rows re-run in the corrected environment (poc/wp_env_regrade.py)


def ci(d, n=4000):
    rng = random.Random(1); b = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(n))
    return f"{sum(d)/len(d):+.2f} [{b[100]:+.2f}, {b[3899]:+.2f}]"


def arms(st):
    P = None
    L = lambda f: {json.loads(l)["id"]: json.loads(l) for l in open(f"{W.R3}/{f}")} if os.path.exists(f"{W.R3}/{f}") else None
    os.environ["NLOPT_SET"] = st
    import run_nlopt as RN
    P = {p["id"]: p for p in RN.problems(st)}
    tk = lambda r: int(r.get("out_tokens") or 0)
    A = {}
    for name, files in (("OptiMind-SFT", [f"opt_optimind_{st}_gurobi_s1.jsonl"]), ("SIRL-32B", [f"opt_sirl32_{st}_copt_s1.jsonl"]),
                        ("gpt-oss-20b one program", [f"opt_oss20_{st}_{M}_s1.jsonl"]),
                        ("ours: gpt-oss-120b one program", [f"opt_oss120_{st}_{M}_s{s}.jsonl" for s in (1, 2)])):
        Z = [L(f) for f in files]
        if all(Z):
            A[name] = {i: (sum(bool(z[i]["correct"]) for z in Z) / len(Z), sum(tk(z[i]) for z in Z) / len(Z)) for i in P if all(i in z for z in Z)}
    Z = [L(f"opt_oss20_{st}_freev_s{s}.jsonl") for s in (1, 2, 3)]
    if all(Z):
        A["cheap plurality (3 x gpt-oss-20b)"] = {}
        for i in P:
            rows = [z[i] for z in Z if i in z]
            C = W.classes(rows); v = C[0]["v"] if C else None
            A["cheap plurality (3 x gpt-oss-20b)"][i] = (float(v is not None and RN.correct(v, P[i]["gold"])), sum(tk(r) for r in rows))
    return P, A


if __name__ == "__main__":
    pool = {}
    for st in SETS:
        P, A = arms(st)
        for name, v in A.items():
            n = len(v)
            print(f"{st:6s} {name:34s} n={n} accuracy {100*sum(x for x, _ in v.values())/n:5.1f}%  tokens {sum(t for _, t in v.values())/n/1000:5.2f}k  "
                  f"utility {sum(U(*x) for x in v.values())/n:6.2f}")
            pool.setdefault(name, {}).update({(st, i): x for i, x in v.items()})
    o = pool.get("ours: gpt-oss-120b one program", {})
    for name, v in pool.items():
        if name.startswith("ours") or not o:
            continue
        for st in SETS + ("all",):
            ids = [k for k in o if k in v and (st == "all" or k[0] == st)]
            if not ids:
                continue
            print(f"{st:6s} ours − {name:34s} accuracy {ci([100*(o[k][0]-v[k][0]) for k in ids])}  ktok {ci([(o[k][1]-v[k][1])/1000 for k in ids])}  "
                  f"utility {ci([U(*o[k])-U(*v[k]) for k in ids])}")
