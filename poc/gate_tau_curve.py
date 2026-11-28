"""Descriptive (2026-11-28): utility of the gated judge over one OWN-EF attempt as a function of tau, on the two prospective seed pairs (7,8), (9,10)
(tau was fixed at 7,536 before those runs; this curve is read after them and decides nothing); gs15 container."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import tir_score as S
U = S.U; D = S.R + "/"; rows = []
for sa, sb in ((7, 8), (9, 10)):
    A = {z["id"]: z for z in map(json.loads, open(D + f"tirsubf_OWN_mcong_medium_s{sa}.jsonl"))}; B = {z["id"]: z for z in map(json.loads, open(D + f"tirsubf_OWN_mcong_medium_s{sb}.jsonl"))}
    J = {z["id"]: z for z in map(json.loads, open(D + f"mcjudge_tirsubf_s{sa}_{sb}.jsonl"))}
    rows += [(A[k], B[k], J[k], sb) for k in set(A) & set(B) & set(J)]
c = lambda z: float(bool(z["correct"]))
def u(tau):
    tot = 0; tk = 0; op = 0
    for a, b, j, sb in rows:
        pick = b if j.get("chosen_seed") == sb else a
        for x, y in ((a, b), (b, a)):
            if x["out_tokens"] > tau:
                op += 1; tot += U(c(pick), x["out_tokens"] + y["out_tokens"] + j["out_tokens"]); tk += x["out_tokens"] + y["out_tokens"] + j["out_tokens"]
            else:
                tot += U(c(x), x["out_tokens"]); tk += x["out_tokens"]
    n = 2 * len(rows); return tot / n, tk / n / 1000, op / n
base = u(10 ** 9)[0]
for t in (2000, 3000, 4000, 5000, 6000, 7536, 9000, 12000, 16000, 10 ** 9):
    v, k, o = u(t); print(f"tau {t:>10}: utility {v:6.2f} ({v-base:+.2f} vs one attempt) at {k:.2f}k tokens, gate open {100*o:.0f}%")
