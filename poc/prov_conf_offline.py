"""PROV-CONF (2026-11-28, offline on the LP rows of seed pairs 14/15 and 16/17, no fitted parameter): the GATE-JP principle on Project Euler —
the PROV flag (a pooled failure signal) decides whether to buy the second attempt; tail confidence (within-pair 0.70-0.79 on Euler) decides which to keep.
Compared with PROV2 (second replaces first unless flagged) and ONE; both orders; corrected reader; gs15 container."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import tir_score as S, ma_effort as M, run_compute as RC
U = S.U; out = {"ONE": [], "PROV2": [], "PROV-CONF": []}; key = []
for pair in ("14_15", "16_17"):
    for st in ("euler", "eulert"):
        g = {p["id"]: p["answer"] for p in RC.problems(st)}
        for l in open(f"{S.R}/tirdis2_{st}_medium_s{pair}.jsonl"):
            z = json.loads(l); ok = lambda r: float((lambda a: bool(a) and RC.norm(a) == RC.norm(g[z["id"]]))(M.ans(r["final"]) or ""))
            v = {k: [] for k in out}
            for x, y in ((z["A"], z["B"]), (z["B"], z["A"])):
                v["ONE"].append((ok(x), x["out_tokens"]))
                if not x["flag"]:
                    v["PROV2"].append((ok(x), x["out_tokens"])); v["PROV-CONF"].append((ok(x), x["out_tokens"])); continue
                both = x["out_tokens"] + y["out_tokens"]
                v["PROV2"].append(((ok(y) if not y["flag"] else ok(x)), both))
                cx, cy = (x.get("lp") or {}).get("tail_conf") or -1e9, (y.get("lp") or {}).get("tail_conf") or -1e9
                v["PROV-CONF"].append((ok(y) if cy > cx else ok(x), both))
            for k in out:
                out[k].append((sum(a for a, _ in v[k]) / 2, sum(t for _, t in v[k]) / 2))
            key.append(z["id"])
n = len(key)
for k, r in out.items():
    print(f"{k:9s} {100*sum(a for a,_ in r)/n:.1f}% @ {sum(t for _,t in r)/n/1000:.2f}k utility {sum(U(*x) for x in r)/n:.2f}")
print("PROV-CONF − PROV2:", S.ci([U(*a) - U(*b) for a, b in zip(out["PROV-CONF"], out["PROV2"])], key), "; PROV-CONF − ONE:", S.ci([U(*a) - U(*b) for a, b in zip(out["PROV-CONF"], out["ONE"])], key))
