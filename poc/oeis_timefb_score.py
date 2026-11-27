"""TIME-FB scorer (2026-11-27): tirtf_oeisf vs stored tir_oeisf, seeds 1-2; gs15 container."""
import json, sys, collections
sys.path.insert(0, "/NAS/SJ/POSTECH/nlp/poc"); import tir_score as S, run_compute as RC
U = S.U; D = "/NAS/SJ/POSTECH/nlp/results/x44/"
L = lambda f: {z["id"]: z for z in map(json.loads, open(D + f))}
B = [L(f"tir_oeisf_medium_s{s}.jsonl") for s in (1, 2)]; F = [L(f"tirtf_oeisf_medium_s{s}.jsonl") for s in (1, 2)]
ks = sorted(set.intersection(*[set(x) for x in B + F])); c = lambda z: float(str(z["correct"]) == "True")
m = lambda X, k: (sum(c(x[k]) for x in X) / 2, sum(x[k]["out_tokens"] for x in X) / 2)
for n, X in (("TIR (stored)", B), ("TIME-FB", F)):
    a = [m(X, k) for k in ks]; Z = [x[k] for x in X for k in ks]
    tle = sum("tle" in (z.get("pred") or []) for z in Z if not c(z))
    print(f"{n:12s} {100*sum(p for p,_ in a)/len(a):.1f}% @ {sum(t for _,t in a)/len(a)/1000:.2f}k utility {sum(U(*v) for v in a)/len(a):.2f}; wrong with a timeout {tle}")
print("TIME-FB − TIR: utility", S.ci([U(*m(F, k)) - U(*m(B, k)) for k in ks]), "accuracy", S.ci([100 * (m(F, k)[0] - m(B, k)[0]) for k in ks]), "ktok", S.ci([(m(F, k)[1] - m(B, k)[1]) / 1000 for k in ks]))
Z = [x[k] for x in F for k in ks]; fed = [z for z in Z if z["fb"] and (z["fb"][0]["tle"] or z["fb"][0]["err"])]
print(f"feedback used in {len(fed)} of {len(Z)}; of those right {sum(c(z) for z in fed)}; tle-only first feedback {sum(bool(z['fb'][0]['tle']) and not z['fb'][0]['err'] for z in fed)}")
