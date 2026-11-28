"""SUBMIT-F3 pooled test (2026-11-28): OWN-EF (tirsubf_OWN_mcong) vs OWN-E over three seed pairs — (1,2), (3,4) vs tirsub3_OWN_mcong, (5,6) vs tirsublp_OWN_mcong; clustered by problem; gs15 container."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import tir_score as S
U = S.U; D = S.R + "/"; d, a, key = [], [], []
L = lambda f: {z["id"]: z for z in map(json.loads, open(D + f))} if os.path.exists(D + f) else None
for pair, base in (((1, 2), "tirsub3"), ((3, 4), "tirsub3"), ((5, 6), "tirsublp")):
    B = [L(f"{base}_OWN_mcong_medium_s{s}.jsonl") for s in pair]; F = [L(f"tirsubf_OWN_mcong_medium_s{s}.jsonl") for s in pair]
    if None in B + F:
        print("missing", pair); continue
    ks = sorted(set.intersection(*[set(x) for x in B + F])); tk = lambda z: z.get("out_tokens_total", z["out_tokens"])
    m = lambda X, k: (sum(float(bool(x[k]["correct"])) for x in X) / 2, sum(tk(x[k]) for x in X) / 2)
    dd = [U(*m(F, k)) - U(*m(B, k)) for k in ks]; aa = [100 * (m(F, k)[0] - m(B, k)[0]) for k in ks]
    print(f"seeds {pair}: OWN-E {100*sum(m(B,k)[0] for k in ks)/len(ks):.1f}% OWN-EF {100*sum(m(F,k)[0] for k in ks)/len(ks):.1f}%; utility {S.ci(dd, [k.split('__')[0] for k in ks])}")
    d += dd; a += aa; key += [k.split("__")[0] for k in ks]
print(f"pooled ({len(d)} instance-pairs): OWN-EF − OWN-E utility {S.ci(d, key)}, accuracy {S.ci(a, key)}")
