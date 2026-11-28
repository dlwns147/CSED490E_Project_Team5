"""JUDGE-EF pooled test (2026-11-28): JUDGE vs ONE over the OWN-EF seed pairs (1,2), (3,4), (5,6); clustered by problem; gs15 container."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import tir_score as S
U = S.U; D = S.R + "/"; dj, key = [], []; w = n = 0
for sa, sb in ((1, 2), (3, 4), (5, 6)):
    A = {z["id"]: z for z in map(json.loads, open(D + f"tirsubf_OWN_mcong_medium_s{sa}.jsonl"))}; B = {z["id"]: z for z in map(json.loads, open(D + f"tirsubf_OWN_mcong_medium_s{sb}.jsonl"))}
    p = D + f"mcjudge_tirsubf_s{sa}_{sb}.jsonl"
    if not os.path.exists(p):
        print("missing", sa, sb); continue
    J = {z["id"]: z for z in map(json.loads, open(p))}
    for k in sorted(set(A) & set(B) & set(J)):
        a, b, j = A[k], B[k], J[k]; c = lambda z: float(bool(z["correct"]))
        one = ((c(a) + c(b)) / 2, (a["out_tokens"] + b["out_tokens"]) / 2)
        pick = b if j.get("chosen_seed") == sb else a
        jud = (c(pick), a["out_tokens"] + b["out_tokens"] + j["out_tokens"])
        dj.append(U(*jud) - U(*one)); key.append(k.split("__")[0])
        if c(a) != c(b):
            n += 1; w += (j.get("chosen_seed") == (sa if c(a) else sb))
print(f"JUDGE − ONE on OWN-EF attempts ({len(dj)} instances, clustered by problem): utility {S.ci(dj, key)}; within-pair {w}/{n} = {w/max(1,n):.2f}")
