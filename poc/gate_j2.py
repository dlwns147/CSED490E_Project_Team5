"""GATE-J2 (2026-11-28, offline, cross-fitted): GATE-J on the OWN-EF attempts and their judge rows, three seed pairs; the gate is the first attempt's
generated tokens (tau fitted on the other fold's problems, 2-fold by crc32 parity); gs15 container."""
import json, os, sys, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import tir_score as S
U = S.U; D = S.R + "/"; rows = []
for sa, sb in ((1, 2), (3, 4), (5, 6)):
    A = {z["id"]: z for z in map(json.loads, open(D + f"tirsubf_OWN_mcong_medium_s{sa}.jsonl"))}; B = {z["id"]: z for z in map(json.loads, open(D + f"tirsubf_OWN_mcong_medium_s{sb}.jsonl"))}
    J = {z["id"]: z for z in map(json.loads, open(D + f"mcjudge_tirsubf_s{sa}_{sb}.jsonl"))}
    for k in sorted(set(A) & set(B) & set(J)):
        rows.append((k, A[k], B[k], J[k], sb))
c = lambda z: float(bool(z["correct"]))
def arm(r, tau):
    k, a, b, j, sb = r; out = []
    pick = b if j.get("chosen_seed") == sb else a
    for x, y in ((a, b), (b, a)):
        out.append((c(pick), x["out_tokens"] + y["out_tokens"] + j["out_tokens"]) if x["out_tokens"] > tau else (c(x), x["out_tokens"]))
    return sum(p for p, _ in out) / 2, sum(t for _, t in out) / 2
fold = lambda r: zlib.crc32(r[0].split("__")[0].encode()) % 2
taus = sorted({z["out_tokens"] for r in rows for z in (r[1], r[2])})[::5] + [10 ** 9]
res = []
for f in (0, 1):
    tr = [r for r in rows if fold(r) != f]; best = max(taus, key=lambda t: sum(U(*arm(r, t)) for r in tr) / len(tr))
    res += [(r, arm(r, best), best) for r in rows if fold(r) == f]
one = lambda r: ((c(r[1]) + c(r[2])) / 2, (r[1]["out_tokens"] + r[2]["out_tokens"]) / 2)
key = [r[0].split("__")[0] for r, _, _ in res]
print(f"GATE-J2 {100*sum(v[0] for _, v, _ in res)/len(res):.1f}% @ {sum(v[1] for _, v, _ in res)/len(res)/1000:.2f}k vs ONE {100*sum(one(r)[0] for r, _, _ in res)/len(res):.1f}% @ {sum(one(r)[1] for r, _, _ in res)/len(res)/1000:.2f}k; "
      f"taus {sorted({t for _, _, t in res})}; GATE-J2 − ONE utility {S.ci([U(*v) - U(*one(r)) for r, v, _ in res], key)}")

best_all = max(taus, key=lambda t: sum(U(*arm(r, t)) for r in rows) / len(rows))
print(f"tau fitted on all {len(rows)} instances (for the prospective test): {best_all}")
