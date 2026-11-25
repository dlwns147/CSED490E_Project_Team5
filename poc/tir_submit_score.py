"""SUBMIT scorer (PREREG_DIFF): TIR-F vs S0 / OWN / BLIND, paired and clustered by problem. usage: python tir_submit_score.py <mconf|mcon> [seeds...]"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tir_score as S
st = sys.argv[1]; seeds = [int(x) for x in sys.argv[2:]] or [1]; L, R, U = S.L, S.R, S.U
nm = {}
p = os.path.join(os.environ.get("POC_DATA", os.path.join(os.path.dirname(S.ROOT), "nlp_data")), "construct", "instances.jsonl")
if st == "mconf" and os.path.exists(p):
    nm = {json.loads(l)["id"]: json.loads(l)["name"] for l in open(p)}
F = {"TIR-F": lambda s: f"{R}/tir_{st}_mediumF_s{s}.jsonl", **{a: (lambda s, a=a: f"{R}/tirsub3_{a}_{st}_medium_s{s}.jsonl") for a in ("S0", "OWN", "BLIND", "BLIND2")}}
A = {}
for k, f in F.items():
    for s in seeds:
        z = L(f(s))
        if z:
            for i, r in z.items():
                A.setdefault(k, {}).setdefault(i, []).append((float(bool(r["correct"])), r["out_tokens"] + r.get("spec_tokens", 0)))
A = {k: {i: (sum(a for a, _ in v) / len(v), sum(t for _, t in v) / len(v)) for i, v in x.items()} for k, x in A.items()}
for k, x in A.items():
    print(f"{k:6s} n={len(x)} {100*sum(a for a, _ in x.values())/len(x):.1f}% @ {sum(t for _, t in x.values())/len(x)/1000:.2f}k utility {sum(U(*v) for v in x.values())/len(x):.2f}")
for a, b in (("S0", "TIR-F"), ("OWN", "TIR-F"), ("BLIND", "TIR-F"), ("BLIND", "S0"), ("BLIND", "OWN"), ("OWN", "S0"), ("BLIND2", "TIR-F"), ("BLIND2", "S0"), ("BLIND2", "OWN"), ("BLIND2", "BLIND")):
    if a in A and b in A:
        ids = [i for i in A[a] if i in A[b]]; ky = [nm.get(i, i) for i in ids]
        print(f"{a} − {b} (n={len(ids)}): accuracy {S.ci([100*(A[a][i][0]-A[b][i][0]) for i in ids], ky)} ktok {S.ci([(A[a][i][1]-A[b][i][1])/1000 for i in ids], ky)} utility {S.ci([U(*A[a][i])-U(*A[b][i]) for i in ids], ky)}")
