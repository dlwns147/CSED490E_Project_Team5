"""DECL scorer (2026-11-28): tirsubfdecl_OWN_mcong vs tirsubf_OWN_mcong (OWN-EF), seeds 1-2, clustered by problem; gs15 container.
Solver-call rate is not measurable from these rows (the runner does not store code); calls and tokens are reported instead."""
import json, os, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import tir_score as S
U = S.U; D = S.R + "/"
L = lambda f: {z["id"]: z for z in map(json.loads, open(D + f))}
B = [L(f"tirsubf_OWN_mcong_medium_s{s}.jsonl") for s in (1, 2)]; F = [L(f"tirsubfdecl_OWN_mcong_medium_s{s}.jsonl") for s in (1, 2)]
ks = sorted(set.intersection(*[set(x) for x in B + F])); key = [k.split("__")[0] for k in ks]
m = lambda X, k: (sum(float(bool(x[k]["correct"])) for x in X) / 2, sum(x[k]["out_tokens"] for x in X) / 2)
for n, X in (("OWN-EF", B), ("DECL", F)):
    a = [m(X, k) for k in ks]; Z = [x[k] for x in X for k in ks]
    print(f"{n:7s} {100*sum(p for p,_ in a)/len(a):.1f}% @ {sum(t for _,t in a)/len(a)/1000:.2f}k utility {sum(U(*v) for v in a)/len(a):.2f}; calls {sum(z['calls'] for z in Z)/len(Z):.1f}; length cuts {sum(z['finish']=='length' for z in Z)}; tags {collections.Counter(z['detail'].split(':')[0][:24] for z in Z if not z['correct']).most_common(4)}")
print("DECL − OWN-EF: utility", S.ci([U(*m(F, k)) - U(*m(B, k)) for k in ks], key), "accuracy", S.ci([100 * (m(F, k)[0] - m(B, k)[0]) for k in ks], key), "ktok", S.ci([(m(F, k)[1] - m(B, k)[1]) / 1000 for k in ks], key))
