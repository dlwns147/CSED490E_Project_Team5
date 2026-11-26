"""DISPUTE-E amendment 2 analysis (2026-11-26): AUROC of free per-attempt signals (DeepConf confidences, mean log-prob, final-answer log-probs, tokens, calls, PROV) for right vs wrong, on tirdis2 seeds 14/15. Run inside the gs15 container."""
import json, sys
sys.path.insert(0, "/NAS/SJ/POSTECH/nlp/poc"); import ma_effort as M, run_compute as RC
gold = {p["id"]: p["answer"] for st in ("euler", "eulert") for p in RC.problems(st)}
X = []
for st in ("euler", "eulert"):
    for l in open(f"/NAS/SJ/POSTECH/nlp/results/x44/tirdis2_{st}_medium_s14_15.jsonl"):
        z = json.loads(l)
        for k in ("A", "B"):
            r = z[k]; a = M.ans(r["final"]) or ""; ok = bool(a) and RC.norm(a) == RC.norm(gold[z["id"]]); lp = r.get("lp") or {}
            fl = lp.get("final_lp") or []
            X.append(dict(ok=ok, tail=lp.get("tail_conf"), low=lp.get("lowest_group_conf"), mean=lp.get("mean_conf"), mlp=lp.get("mean_lp"), fmin=min(fl) if fl else None, fsum=sum(fl) if fl else None, tok=-r["out_tokens"], calls=-r["calls"], prov=0 if r["flag"] else 1))
def auroc(key):
    P = [x[key] for x in X if x["ok"] and x[key] is not None]; N = [x[key] for x in X if not x["ok"] and x[key] is not None]
    s = sum((p > n) + 0.5 * (p == n) for p in P for n in N); return s / (len(P) * len(N)), len(P), len(N)
for k in ("tail", "low", "mean", "mlp", "fmin", "fsum", "tok", "calls", "prov"):
    a, p, n = auroc(k); print(f"{k:6s} AUROC(right vs wrong) {a:.3f}  (right {p}, wrong {n})")
# within PROV-unflagged attempts: does tail confidence still separate?
U = [x for x in X if x["prov"] == 1]
P = [x["tail"] for x in U if x["ok"]]; N = [x["tail"] for x in U if not x["ok"]]
print("tail AUROC among unflagged:", round(sum((p > n) + 0.5 * (p == n) for p in P for n in N) / (len(P) * len(N)), 3), len(P), len(N))
P = [x["tok"] for x in U if x["ok"]]; N = [x["tok"] for x in U if not x["ok"]]
print("tokens AUROC among unflagged:", round(sum((p > n) + 0.5 * (p == n) for p in P for n in N) / (len(P) * len(N)), 3))
