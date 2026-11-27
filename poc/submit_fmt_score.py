"""SUBMIT-F scorer (2026-11-27): tirsubf_OWN_mcong vs stored tirsub3_OWN_mcong, seeds from SF_SEEDS (default 1,2); gs15 container."""
import json, sys, collections
sys.path.insert(0, "/NAS/SJ/POSTECH/nlp/poc"); import tir_score as S
import os
SEEDS = [int(x) for x in os.environ.get("SF_SEEDS", "1,2").split(",")]
U = S.U; D = "/NAS/SJ/POSTECH/nlp/results/x44/"
L = lambda f: {z["id"]: z for z in map(json.loads, open(D + f))}
B = [L(f"tirsub3_OWN_mcong_medium_s{s}.jsonl") for s in SEEDS]; F = [L(f"tirsubf_OWN_mcong_medium_s{s}.jsonl") for s in SEEDS]
ks = sorted(set(B[0]) & set(B[1]) & set(F[0]) & set(F[1])); key = [k.split("__")[0] for k in ks]
tk = lambda z: z.get("out_tokens_total", z["out_tokens"])
m = lambda X, k: (sum(float(bool(x[k]["correct"])) for x in X) / 2, sum(tk(x[k]) for x in X) / 2)
for n, X in (("OWN-E (stored)", B), ("SUBMIT-F", F)):
    a = [m(X, k) for k in ks]; Z = [x[k] for x in X for k in ks]
    print(f"{n:15s} {100*sum(p for p,_ in a)/len(a):.1f}% @ {sum(t for _,t in a)/len(a)/1000:.2f}k utility {sum(U(*v) for v in a)/len(a):.2f}; tags {collections.Counter(z['detail'].split(':')[0][:24] for z in Z if not z['correct']).most_common(5)}")
print("SUBMIT-F − OWN-E: utility", S.ci([U(*m(F, k)) - U(*m(B, k)) for k in ks], key), "accuracy", S.ci([100 * (m(F, k)[0] - m(B, k)[0]) for k in ks], key), "ktok", S.ci([(m(F, k)[1] - m(B, k)[1]) / 1000 for k in ks], key))
Z = [x[k] for x in F for k in ks]; fed = [z for z in Z if any(y["error"] for y in z["fmt"])]
print(f"format feedback used in {len(fed)} of {len(Z)} attempts; of those right {sum(bool(z['correct']) for z in fed)}, still unparseable {sum(z['detail'].startswith('Error parsing') for z in fed)}")
same = sum(B[i][k]["final"] == F[i][k]["final"] for i in range(2) for k in ks); print(f"identical final answers to the stored rows: {same} of {2*len(ks)}")
