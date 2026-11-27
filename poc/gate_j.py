"""GATE-J (PREREG_DIFF, 2026-11-27): offline cross-fitted gate on the stored CONF-MC (seeds 5 / 6) and JUDGE-MC rows: buy the second attempt + judge
only when the first attempt used more than tau generated tokens; tau maximises utility on the other fold's problems (2-fold by crc32 parity). No model call.
usage (gs15 container): python gate_j.py"""
import json, os, sys, zlib
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import tir_score as S
R = S.R; U = S.U
L = lambda s: {z["id"]: z for z in map(json.loads, open(f"{R}/tirsublp_OWN_mcong_medium_s{s}.jsonl"))}
A, B = L(5), L(6); J = {z["id"]: z for z in map(json.loads, open(f"{R}/mcjudge_s5_6.jsonl"))}
ks = sorted(set(A) & set(B) & set(J)); fold = {k: zlib.crc32(k.split("__")[0].encode()) % 2 for k in ks}
c = lambda z: float(bool(z["correct"]))
def judged(k):
    j = J[k]; return B[k] if j.get("chosen_seed") == 6 else A[k]
def arm(k, tau):
    out = []
    for x, y in ((A[k], B[k]), (B[k], A[k])):
        if x["out_tokens"] > tau:
            out.append((c(judged(k)), x["out_tokens"] + y["out_tokens"] + J[k]["out_tokens"]))
        else:
            out.append((c(x), x["out_tokens"]))
    return sum(a for a, _ in out) / 2, sum(t for _, t in out) / 2
taus = sorted({z["out_tokens"] for k in ks for z in (A[k], B[k])}) + [10 ** 9]
res = {}; chosen = {}
for f in (0, 1):
    tr = [k for k in ks if fold[k] != f]
    best = max(taus[::3] + [10 ** 9], key=lambda t: sum(U(*arm(k, t)) for k in tr) / len(tr)); chosen[f] = best
    for k in ks:
        if fold[k] == f:
            res[k] = arm(k, best)
one = {k: ((c(A[k]) + c(B[k])) / 2, (A[k]["out_tokens"] + B[k]["out_tokens"]) / 2) for k in ks}
jud = {k: (c(judged(k)), A[k]["out_tokens"] + B[k]["out_tokens"] + J[k]["out_tokens"]) for k in ks}
key = [k.split("__")[0] for k in ks]; buy = sum((A[k]["out_tokens"] > chosen[fold[k]]) + (B[k]["out_tokens"] > chosen[fold[k]]) for k in ks) / (2 * len(ks))
for n, d in (("ONE", one), ("GATE-J", res), ("JUDGE", jud)):
    print(f"{n:7s} {100*sum(d[k][0] for k in ks)/len(ks):.1f}% @ {sum(d[k][1] for k in ks)/len(ks)/1000:.2f}k utility {sum(U(*d[k]) for k in ks)/len(ks):.2f}")
print(f"tau per fold {chosen}; share of first attempts that buy {buy:.2f}")
print(f"GATE-J − ONE: utility {S.ci([U(*res[k]) - U(*one[k]) for k in ks], key)} accuracy {S.ci([100*(res[k][0]-one[k][0]) for k in ks], key)} ktok {S.ci([(res[k][1]-one[k][1])/1000 for k in ks], key)}")
print(f"GATE-J − JUDGE: utility {S.ci([U(*res[k]) - U(*jud[k]) for k in ks], key)}")
