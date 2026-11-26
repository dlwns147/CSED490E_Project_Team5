"""TABLE-H ceiling on OEIS (2026-11-26): the baseline guesser (poc/euler_guess.py) on the GOLD first k terms of the 309 fresh sequences; extrapolate to term 20; labels used, zero tokens. Run inside the gs15 container (paths /NAS/...)."""
import json, sys, collections
from fractions import Fraction
sys.path.insert(0, "/NAS/SJ/POSTECH/nlp/poc"); import euler_guess as G
P = json.load(open("/NAS/SJ/POSTECH/nlp_data/compute/oeis_fresh.json"))
wrong = {json.loads(l)["id"]: not json.loads(l)["correct"] for l in open("/NAS/SJ/POSTECH/nlp/results/x44/tir_oeisf_medium_s1.jsonl")}
for k in (8, 10, 12, 15):
    C = collections.Counter(); hit = []
    for p in P:
        T = p["terms"] if isinstance(p["terms"], list) else eval(p["terms"]); t = [Fraction(int(x)) for x in T[:20]]
        if not t or len(t) < 20: C["<20 terms"] += 1; continue
        n0 = int(p["offset"]); m = G.guess(n0, t[:k])
        if m is None: C["none"] += 1; continue
        ok = True
        try:
            for i in range(k, 20):
                x, how = G.evaluate(m, n0, t[:k], n0 + i, None)
                if x != t[i]: ok = False; break
        except Exception as e:
            ok = False
        C[(m[0], ok)] += 1
        if ok: hit.append(p["id"])
    print(f"k={k}: {dict(C)}; right extrapolations {len(hit)}, of them TIR-wrong {sum(wrong.get(i, False) for i in hit)} (TIR wrong overall {sum(wrong.values())})")
