"""SUBMIT-F20 scorer (2026-11-27): gpt-oss-20b OWN-EF (tirsubf20) vs the RFT-C base rows on the 126 held-out instances; gs15 container."""
import json, sys, collections
sys.path.insert(0, "/NAS/SJ/POSTECH/nlp/poc"); import tir_score as S
U = S.U; D = "/NAS/SJ/POSTECH/nlp/results/x44/"
B = collections.defaultdict(dict)
for l in open(D + "rft_base_held_s1.jsonl"):
    z = json.loads(l); B[z["seed"]][z["id"]] = z
F = {s: {z["id"]: z for z in map(json.loads, open(D + f"tirsubf20_OWN_mcong_medium_s{s}.jsonl"))} for s in (1, 2)}
ks = sorted(set(B[1]) & set(B[2]) & set(F[1]) & set(F[2])); key = [k.split("__")[0] for k in ks]
c = lambda z: float(bool(z["correct"]))
m = lambda X, k: ((c(X[1][k]) + c(X[2][k])) / 2, (X[1][k]["out_tokens"] + X[2][k]["out_tokens"]) / 2)
for n, X in (("OWN-E 20B", B), ("OWN-EF 20B", F)):
    a = [m(X, k) for k in ks]; Z = [X[s][k] for s in (1, 2) for k in ks]
    print(f"{n:11s} {100*sum(p for p,_ in a)/len(a):.1f}% @ {sum(t for _,t in a)/len(a)/1000:.2f}k utility {sum(U(*v) for v in a)/len(a):.2f}; tags {collections.Counter(z['detail'].split(':')[0][:24] for z in Z if not z['correct']).most_common(4)}")
print("OWN-EF − OWN-E (20B, held-out 126):", "utility", S.ci([U(*m(F, k)) - U(*m(B, k)) for k in ks], key), "accuracy", S.ci([100 * (m(F, k)[0] - m(B, k)[0]) for k in ks], key))
Z = [F[s][k] for s in (1, 2) for k in ks]; fed = [z for z in Z if any(y["error"] for y in z["fmt"])]
print("format feedback used", len(fed), "of", len(Z), "; right", sum(c(z) for z in fed))
