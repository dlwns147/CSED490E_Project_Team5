"""Within-pair selection rates on Project Euler pooled over the three DISPUTE-E seed pairs (8/9, 14/15, 16/17): judge, tail confidence, fewer tokens (2026-11-27; gs15 container)."""
import json, sys
sys.path.insert(0, "/NAS/SJ/POSTECH/nlp/poc"); import ma_effort as M, run_compute as RC, tir_dispute as D
g = {p["id"]: p["answer"] for st in ("euler", "eulert") for p in RC.problems(st)}
ok = lambda r, i: (lambda a: bool(a) and RC.norm(a) == RC.norm(g[i]))(M.ans(r["final"]) or "")
J = {"n": 0, "w": 0}; C = {"n": 0, "w": 0}; T = {"n": 0, "w": 0}
for pre, s in (("tirdis", "8_9"), ("tirdis2", "14_15"), ("tirdis2", "16_17")):
    for st in ("euler", "eulert"):
        for l in open(f"/NAS/SJ/POSTECH/nlp/results/x44/{pre}_{st}_medium_s{s}.jsonl"):
            z = json.loads(l); a, b = ok(z["A"], z["id"]), ok(z["B"], z["id"])
            if a == b: continue
            R, W = (z["A"], z["B"]) if a else (z["B"], z["A"])
            if z.get("judge") and z["disputed"]:
                J["n"] += 1; J["w"] += D.eq(z["judge"].get("ans"), R["ans"]) and not D.eq(z["judge"].get("ans"), W["ans"])
            if R.get("lp") and W.get("lp"):
                C["n"] += 1; C["w"] += R["lp"]["tail_conf"] > W["lp"]["tail_conf"]
            T["n"] += 1; T["w"] += R["out_tokens"] < W["out_tokens"]
print(f"Project Euler, one-right pairs pooled over three seed pairs: judge picks right {J['w']}/{J['n']} = {J['w']/max(1,J['n']):.2f} (disputed pairs with a judge reply); tail confidence {C['w']}/{C['n']} = {C['w']/max(1,C['n']):.2f}; fewer tokens {T['w']}/{T['n']} = {T['w']/max(1,T['n']):.2f}")
