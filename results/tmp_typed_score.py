"""PREREG_TYPED scoring: typed translation vs the same model's stored quick program (formx), paired by problem-seed.
Max flow: against the exact max flow from the problem text (results/tmp_flow_closure.text_edges) and against the dataset label.
TSP: against the dataset label."""
import io, contextlib, json, random, sys
sys.path.insert(0, "poc"); sys.path.insert(0, "results")
with contextlib.redirect_stdout(io.StringIO()):
    import run_nlopt as RN, analyze_hopa as H
    import tmp_flow_closure as FC
RN.MAMO = "/home1/leesangjun/SJ/POSTECH/nlp_data/MAMO"
P = {p["id"]: p for p in RN.problems("mamo")}
close = lambda a, b: a is not None and abs(float(a) - float(b)) < 1e-6 * max(1, abs(float(b)))
def num(x):
    try: return float(x)
    except Exception: return None
for tag in ("q8b", "oss20"):
    res = {"max_flow": {"exact": [], "label": []}, "tsp": {"label": []}}
    for s in (1, 2, 3):
        T = {r["id"]: r for r in map(json.loads, open(f"results/x3/typed_{tag}_s{s}.jsonl"))}
        F = {r["id"]: r for r in RN._rows(f"{H.XRES}/opt_{tag}_mamo_formx_s{s}.jsonl")}
        for i, t in T.items():
            if i not in F: continue
            f = F[i]; fp = num(f.get("pred")); tp = t["pred"]
            if t["kind"] == "max_flow":
                e = FC.text_edges(P[i]["q"])
                if len(e) >= 3:
                    ex = FC.maxflow(e); res["max_flow"]["exact"].append((close(tp, ex), close(fp, ex)))
                res["max_flow"]["label"].append((close(tp, P[i]["gold"]), bool(f["correct"])))
            else:
                res["tsp"]["label"].append((close(tp, P[i]["gold"]), bool(f["correct"])))
    for k, d in res.items():
        for lab, v in d.items():
            n = len(v); dd = [a - b for a, b in v]; random.seed(0)
            bs = sorted(sum(random.choice(dd) for _ in dd) / n for _ in range(4000))
            print(f"{tag} {k:8s} vs {lab:5s}: n={n} typed {sum(a for a,_ in v)/n:.1%} own program {sum(b for _,b in v)/n:.1%} | typed - program {100*sum(dd)/n:+.1f} [{100*bs[100]:+.1f}, {100*bs[3899]:+.1f}]")
