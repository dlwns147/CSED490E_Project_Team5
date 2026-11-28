"""REFLEX-E pooled test over seed pairs (2026-11-28); gs15 container."""
import os, sys, importlib
sys.path.insert(0, "/NAS/SJ/POSTECH/nlp/poc")
import tir_score as S, ma_effort as M, run_compute as RC, json
U = S.U; d = []; key = []; acc = []
g = {p["id"]: p["answer"] for st in ("euler", "eulert") for p in RC.problems(st)}
ok = lambda r, i: float((lambda a: bool(a) and RC.norm(a) == RC.norm(g[i]))(M.ans(r.get("final", "")) or ""))
for pair, rs, pre in (("16_17", 18, "tirdis2"), ("14_15", 19, "tirdis2"), ("8_9", 20, "tirdis")):
    if not os.path.exists(f"/NAS/SJ/POSTECH/nlp/results/x44/eulrefl_s{rs}.jsonl"): continue
    X = {json.loads(l)["id"]: json.loads(l) for l in open(f"/NAS/SJ/POSTECH/nlp/results/x44/eulrefl_s{rs}.jsonl")}
    for st in ("euler", "eulert"):
        for l in open(f"/NAS/SJ/POSTECH/nlp/results/x44/{pre}_{st}_medium_s{pair}.jsonl"):
            z = json.loads(l); i = z["id"]; a, b = z["A"], z["B"]
            if not a["flag"]:
                d.append(0.0); acc.append(0.0); key.append(i); continue
            r = X.get(i)
            if r is None: continue
            p2 = ((ok(b, i) if not b["flag"] else ok(a, i)), a["out_tokens"] + b["out_tokens"]); rf = ((ok(r, i) if not r["flag"] else ok(a, i)), a["out_tokens"] + r["out_tokens"])
            d.append(U(*rf) - U(*p2)); acc.append(100 * (rf[0] - p2[0])); key.append(i)
print(f"pooled over both seed pairs ({len(d)} problem-pairs, clustered by problem): REFLEX − PROV2 utility {S.ci(d, key)}, accuracy {S.ci(acc, key)}")
