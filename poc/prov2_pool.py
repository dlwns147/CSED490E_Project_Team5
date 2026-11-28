"""PROV2 − ONE pooled over the three DISPUTE-E seed pairs (8/9, 14/15, 16/17; both orders; corrected reader), descriptive (2026-11-28); gs15 container."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tir_dispute2 as D2, tir_score as S, ma_effort as M, run_compute as RC
U = S.U; d, a, t, key = [], [], [], []
for pre, pair in (("tirdis", "8_9"), ("tirdis2", "14_15"), ("tirdis2", "16_17")):
    for st in ("euler", "eulert"):
        g = {p["id"]: p["answer"] for p in RC.problems(st)}
        for l in open(f"{S.R}/{pre}_{st}_medium_s{pair}.jsonl"):
            z = json.loads(l)
            for k in ("A", "B"):
                x = M.ans(z[k]["final"]) or ""; z[k]["correct"] = bool(x) and RC.norm(x) == RC.norm(g[z["id"]])
            A = D2.arms(z); one = [sum(v) / len(v) for v in zip(*A["ONE"])]; p2 = [sum(v) / len(v) for v in zip(*A["PROV2"])]
            d.append(U(*p2) - U(*one)); a.append(100 * (p2[0] - one[0])); t.append((p2[1] - one[1]) / 1000); key.append(z["id"])
print(f"PROV2 − ONE over {len(d)} problem-pairs (3 seed pairs, clustered by problem): utility {S.ci(d, key)}, accuracy {S.ci(a, key)}, ktok {S.ci(t, key)}")
