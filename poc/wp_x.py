"""CLEAN-X (PREREG_DIFF, 2026-11-25): OptiMind-SFT against ours-one (corrected environment) and SIRL on the nine other word-problem sets, one reader
(each row's stored run_nlopt.correct). ours-one = seeds 1-2 mean where stored, else seed 1. usage: python wp_x.py"""
import json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wp_plan as W
U = lambda ok, t: 100 * ok - 0.5 * t / 1000
SETS = ("optnew", "optmath", "omtf", "omtf2", "bwor", "logior", "optibench", "easyc", "nl4c")


def ci(d, n=4000):
    rng = random.Random(1); b = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(n))
    return f"{sum(d)/len(d):+.2f} [{b[100]:+.2f}, {b[3899]:+.2f}]"


L = lambda f: {json.loads(l)["id"]: json.loads(l) for l in open(f"{W.R3}/{f}")} if os.path.exists(f"{W.R3}/{f}") else None
tk = lambda r: int(r.get("out_tokens") or 0)
for st in SETS:
    os.environ["NLOPT_SET"] = st
    import run_nlopt as RN
    ids = [p["id"] for p in RN.problems(st)]
    A = {}
    O = [z for z in (L(f"opt_oss120_{st}_thinkfreenE_s{s}.jsonl") for s in (1, 2)) if z]
    for name, Z in (("OptiMind-SFT", [L(f"opt_optimind_{st}_gurobi_s1.jsonl")]), ("SIRL-32B", [L(f"opt_sirl32_{st}_copt_s1.jsonl")]), ("ours-one", O)):
        Z = [z for z in Z if z]
        if Z and all(i in z for z in Z for i in ids):
            A[name] = {i: (sum(bool(z[i]["correct"]) for z in Z) / len(Z), sum(tk(z[i]) for z in Z) / len(Z)) for i in ids}
            zero = sum(1 for z in Z for i in ids if not tk(z[i]))
            print(f"{st:10s} {name:14s} n={len(ids)} seeds {len(Z)} accuracy {100*sum(x for x, _ in A[name].values())/len(ids):5.1f}%  tokens {sum(t for _, t in A[name].values())/len(ids)/1000:5.2f}k  "
                  f"utility {sum(U(*x) for x in A[name].values())/len(ids):6.2f}" + (f"  ZERO-TOKEN ROWS {zero}" if zero else ""))
    if "OptiMind-SFT" in A and "ours-one" in A:
        for lab, f in (("accuracy", lambda a, b: 100 * (a[0] - b[0])), ("ktok", lambda a, b: (a[1] - b[1]) / 1000), ("utility", lambda a, b: U(*a) - U(*b))):
            print(f"{st:10s}   ours − OptiMind {lab}: {ci([f(A['ours-one'][i], A['OptiMind-SFT'][i]) for i in ids])}")
