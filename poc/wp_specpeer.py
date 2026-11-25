"""SPEC-PEER (PREREG_DIFF, 2026-11-25; offline): SIRL-32B + one cheap gpt-oss-20b freev program (seed 1); agree -> answer, else one
gpt-oss-120b thinking program (thinkfreen, seed 1 / seed 2, mean). Compared with ours-one (always think), paired by problem.
usage: python wp_specpeer.py <set> [...]"""
import json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wp_plan as W
U = lambda ok, t: 100 * ok - 0.5 * t / 1000
L = lambda f: {json.loads(l)["id"]: json.loads(l) for l in open(f"{W.R3}/{f}")}
for st in sys.argv[1:]:
    os.environ["NLOPT_SET"] = st
    import run_nlopt as RN
    P = {p["id"]: p for p in RN.problems()}
    S, C1 = L(f"opt_sirl32_{st}_copt_s1.jsonl"), L(f"opt_oss20_{st}_freev_s1.jsonl")
    T = [L(f"opt_oss120_{st}_thinkfreen_s{s}.jsonl") for s in (1, 2)]
    tok = lambda r: int(r.get("out_tokens") or 0)
    casc, one, esc = {}, {}, 0
    for i in P:
        a, b = W.val(S[i]), W.val(C1[i])
        agree = a is not None and b is not None and RN.correct(a, str(b))
        esc += not agree
        cs = []
        for t in T:
            ok = RN.correct(a, P[i]["gold"]) if agree else bool(t[i]["correct"])
            cs.append((ok, tok(S[i]) + tok(C1[i]) + (0 if agree else tok(t[i]))))
        casc[i] = (sum(o for o, _ in cs) / 2, sum(k for _, k in cs) / 2)
        one[i] = (sum(bool(t[i]["correct"]) for t in T) / 2, sum(tok(t[i]) for t in T) / 2)
    ids = sorted(P)
    for name, v in (("ours-one (always think)", one), ("SPEC-PEER cascade", casc)):
        print(f"{st:8s} {name:24s} accuracy {100*sum(v[i][0] for i in ids)/len(ids):5.1f}%  tokens {sum(v[i][1] for i in ids)/len(ids)/1000:.2f}k  "
              f"utility {sum(U(*v[i]) for i in ids)/len(ids):6.2f}")
    d = [U(*casc[i]) - U(*one[i]) for i in ids]; rng = random.Random(1); bs = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(4000))
    print(f"{st:8s} cascade − ours-one: {sum(d)/len(d):+.2f} [{bs[100]:+.2f}, {bs[3899]:+.2f}]  escalated {esc} of {len(ids)}")
