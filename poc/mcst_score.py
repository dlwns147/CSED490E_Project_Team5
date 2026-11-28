"""MCST scorer (PREREG_DIFF addendum MCST, 2026-11-28). Arms: PAPER (authors' harness, results/x44/mcst_paper/tools.json), TIR (s1), ONE (OWN-EF, s1 and s2
averaged), GJ (OWN-EF-GJ, tau 7,536 fixed, both orders averaged; second attempt and judge charged only when the gate opens). Utility = 100·correct − 0.5·ktok,
paired bootstrap clustered by problem type. Reports all 329 (decisions) and the 320 without the 9 low_autocorrelation SAT instances whose reference
solutions the verifier rejects; SAT / UNSAT splits, claims, tokens, calls, finish reasons, the gate rate, the judge's within-pair rate, the tau curve.
usage: python mcst_score.py   (GPU-server container, after poc/mcst_grade.py has written the .graded files)"""
import collections, json, os, statistics, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import tir_score as S
D = S.R + "/"; U = S.U; TAU = int(os.environ.get("TAU", 7536))
P = {p["name"]: p for p in map(json.loads, open(os.environ.get("MCST_DATA", "/dev/shm/sj_nlp/mcst/Math-Constraint/mathconstraint/problems.jsonl")))}
BAD = set(json.load(open("/dev/shm/sj_nlp/mcst/ref_fail.json"))) if os.path.exists("/dev/shm/sj_nlp/mcst/ref_fail.json") else set()


def rows(arm, seed):
    f = D + f"mcst_{arm}_s{seed}"
    if not os.path.exists(f + ".graded.jsonl"):
        return None
    Z = {z["id"]: z for z in map(json.loads, open(f + ".jsonl"))}; G = {g["id"]: g for g in map(json.loads, open(f + ".graded.jsonl"))}
    return {k: {**Z[k], **G[k]} for k in G}


def paper():
    f = D + "mcst_paper/tools.json"
    if not os.path.exists(f):
        return None
    out = {}
    for r in json.load(open(f))["results"]:
        sat = r.get("submitted_satisfiable"); sat = None if sat in (None, "None") else str(sat) == "True"
        out[r["problem_name"]] = {"correct": str(r["correct"]) == "True", "out_tokens": int(r.get("completion_tokens") or 0), "claim": sat, "calls": int(r.get("n_execute_python") or 0),
                                  "finish": r.get("failure_bucket")}
    return out


SA, SB = (int(x) for x in os.environ.get("MSEEDS", "1,2").split(","))      # MCST-C: MSEEDS=3,4
A, B, T, PA = rows("OWNEF", SA), rows("OWNEF", SB), rows("TIR", 1), paper()
T2 = rows("TIR2", 1)       # amendment 12:32 UTC: TIR with the raw message kept; TIR2_len = the lenient reading (last list / UNSATISFIABLE in the message)
JF = D + f"mcst_judge_s{SA}_{SB}.jsonl"; J = {z["id"]: z for z in map(json.loads, open(JF))} if os.path.exists(JF) else None
c = lambda z: float(bool(z["correct"]))
arms = {}
if A and B:
    arms["ONE"] = {k: ((c(A[k]) + c(B[k])) / 2, (A[k]["out_tokens"] + B[k]["out_tokens"]) / 2) for k in A if k in B}


def gate(tau):
    g = {}; opened = 0
    for k in arms["ONE"]:
        if k not in J:
            return None, 0
        a, b, j = A[k], B[k], J[k]; pick = b if j.get("chosen_seed") == SB else a; v = []
        for x, y in ((a, b), (b, a)):
            if x["out_tokens"] > tau:
                opened += 1; v.append((c(pick), x["out_tokens"] + y["out_tokens"] + j["out_tokens"]))
            else:
                v.append((c(x), x["out_tokens"]))
        g[k] = (sum(p for p, _ in v) / 2, sum(t for _, t in v) / 2)
    return g, opened


if J and "ONE" in arms:
    arms["GJ"], OPENED = gate(TAU)
    if arms["GJ"] is None:
        del arms["GJ"]
    else:
        arms["GJ_PROC"] = gate(0)[0]          # MCST-C: the procedure assigns no gate (dev pooled AUROC 0.44 < 0.6)
for name, R in (("TIR", T), ("PAPER", PA), (f"OWNEF_s{SA}", A), (f"OWNEF_s{SB}", B)):
    if R:
        arms[name] = {k: (c(z), z["out_tokens"]) for k, z in R.items()}
if T2:
    arms["TIR2"] = {k: (c(z), z["out_tokens"]) for k, z in T2.items()}; arms["TIR2_len"] = {k: (float(bool(z["correct_len"])), z["out_tokens"]) for k, z in T2.items()}
common = sorted(set.intersection(*[set(v) for v in arms.values()])) if arms else []
print(f"MCST: arms {list(arms)}; {len(common)} common instances")
for sub, ks in (("all 329", common), ("320 (verifier-accepted references)", [k for k in common if k not in BAD])):
    key = [P[k]["problem_type"] for k in ks]; n = len(ks)
    print(f"--- {sub}: n = {n}")
    for a, d in arms.items():
        sat = [k for k in ks if P[k]["satisfiable"]]; uns = [k for k in ks if not P[k]["satisfiable"]]
        print(f"{a:9s} {100*sum(d[k][0] for k in ks)/n:5.1f}% @ {sum(d[k][1] for k in ks)/n/1000:5.2f}k  utility {sum(U(*d[k]) for k in ks)/n:6.2f} | SAT {100*sum(d[k][0] for k in sat)/max(1,len(sat)):5.1f}% UNSAT {100*sum(d[k][0] for k in uns)/max(1,len(uns)):5.1f}%")
    for x, y in (("ONE", "PAPER"), ("ONE", "TIR"), ("ONE", "TIR2_len"), ("GJ", "ONE"), ("GJ_PROC", "ONE"), ("GJ_PROC", "GJ"), ("GJ", "PAPER"), ("GJ_PROC", "PAPER"), ("TIR", "PAPER"), ("TIR2_len", "PAPER")):
        if x in arms and y in arms:
            print(f"{x} − {y}: utility {S.ci([U(*arms[x][k]) - U(*arms[y][k]) for k in ks], key)}  accuracy {S.ci([100*(arms[x][k][0]-arms[y][k][0]) for k in ks], key)}")
if "GJ" in arms:
    print(f"gate opened on {OPENED} of {2*len(arms['ONE'])} first attempts (tau {TAU})")
    pairs = [(k, J[k]) for k in arms["ONE"] if not J[k].get("same") and c(A[k]) != c(B[k])]
    w = [(1 if j.get("chosen_seed") == (SA if c(A[k]) else SB) else 0, P[k]["satisfiable"]) for k, j in pairs]
    print(f"judge within-pair (one right, one wrong): {sum(x for x,_ in w)}/{len(w)} = {sum(x for x,_ in w)/max(1,len(w)):.2f}; SAT instances {sum(x for x,s in w if s)}/{sum(1 for _,s in w if s)}, UNSAT {sum(x for x,s in w if not s)}/{sum(1 for _,s in w if not s)}")
    L = [j for j in J.values() if not j.get("same")]
    print(f"judge: {len(L)} differing pairs, {sum(j['out_tokens'] for j in L)/max(1,len(L))/1000:.2f}k tokens, no letter {sum(not j.get('letter') for j in L)}, picked first shown {sum(j.get('letter') == 'A' for j in L)}")
    ks = [k for k in common]; key = [P[k]["problem_type"] for k in ks]
    print("tau curve (GJ − ONE utility, all 329):", "  ".join(f"{t//1000 if t < 10**8 else 'inf'}k {sum(U(*g[k]) - U(*arms['ONE'][k]) for k in ks)/len(ks):+.2f} ({100*o/(2*len(ks)):.0f}%)" for t in (1000, 2000, 3000, 5000, 7536, 10000, 15000, 25000, 10**9) for g, o in [gate(t)]))
    # pooled vs within-pair discrimination of the gate signal (first-attempt tokens), as on MathConstruct
    X = [(z["out_tokens"], c(z)) for R in (A, B) for z in R.values()]
    pos = [t for t, y in X if not y]; neg = [t for t, y in X if y]
    au = sum((p > q) + 0.5 * (p == q) for p in pos for q in neg) / max(1, len(pos) * len(neg))
    print(f"pooled AUROC of tokens for 'wrong': {au:.2f} ({len(pos)} wrong of {len(X)})")
# beyond accuracy: claims, polarity, tokens, tool use, finish
for name, R in (("PAPER", PA), ("TIR", T), ("TIR2", T2), ("OWNEF_s1", A), ("OWNEF_s2", B)):
    if not R:
        continue
    ks = [k for k in common] or list(R); cl = collections.Counter()
    for k in ks:
        z = R[k]; truth = P[k]["satisfiable"]; cl[("SAT" if truth else "UNSAT") + "->" + {True: "SAT", False: "UNSAT", None: "none"}[z.get("claim")]] += 1
    tk = sorted(R[k]["out_tokens"] for k in ks)
    print(f"{name:9s} claims {dict(sorted(cl.items()))}; tokens median {tk[len(tk)//2]/1000:.2f}k p90 {tk[int(.9*len(tk))]/1000:.2f}k; calls {statistics.mean(R[k].get('calls', 0) or 0 for k in ks):.1f}; finish {dict(collections.Counter(str(R[k].get('finish'))[:10] for k in ks).most_common(4))}")
for name, R in (("TIR", T), ("OWNEF_s1", A)):
    if R:
        imp = collections.Counter(m for z in R.values() for m in ("pysat", "z3", "ortools", "pycosat", "itertools") if any(m in cd for cd in z.get("codes", [])))
        print(f"{name}: attempts importing / using {dict(imp)} of {len(R)}; format feedback used {sum(1 for z in R.values() if z.get('fmt') and z['fmt'][0]['error'])}")
