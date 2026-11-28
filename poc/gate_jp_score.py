"""GATE-JP scorer (2026-11-28): prospective gated judge on OWN-EF seeds 7 / 8 with tau fixed at 7,536 tokens; clustered by problem; gs15 container."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import tir_score as S
U = S.U; D = S.R + "/"; TAU = 7536
A = {z["id"]: z for z in map(json.loads, open(D + "tirsubf_OWN_mcong_medium_s7.jsonl"))}; B = {z["id"]: z for z in map(json.loads, open(D + "tirsubf_OWN_mcong_medium_s8.jsonl"))}
J = {z["id"]: z for z in map(json.loads, open(D + "mcjudge_tirsubf_s7_8.jsonl"))}
c = lambda z: float(bool(z["correct"])); G, O, key = [], [], []; opened = 0
for k in sorted(set(A) & set(B) & set(J)):
    a, b, j = A[k], B[k], J[k]; pick = b if j.get("chosen_seed") == 8 else a; g = []
    for x, y in ((a, b), (b, a)):
        if x["out_tokens"] > TAU:
            opened += 1; g.append((c(pick), x["out_tokens"] + y["out_tokens"] + j["out_tokens"]))
        else:
            g.append((c(x), x["out_tokens"]))
    G.append((sum(p for p, _ in g) / 2, sum(t for _, t in g) / 2)); O.append(((c(a) + c(b)) / 2, (a["out_tokens"] + b["out_tokens"]) / 2)); key.append(k.split("__")[0])
n = len(G)
print(f"ONE {100*sum(p for p,_ in O)/n:.1f}% @ {sum(t for _,t in O)/n/1000:.2f}k; GATE {100*sum(p for p,_ in G)/n:.1f}% @ {sum(t for _,t in G)/n/1000:.2f}k; gate opened on {opened} of {2*n} first attempts")
print("GATE − ONE: utility", S.ci([U(*g) - U(*o) for g, o in zip(G, O)], key), "accuracy", S.ci([100 * (g[0] - o[0]) for g, o in zip(G, O)], key))
