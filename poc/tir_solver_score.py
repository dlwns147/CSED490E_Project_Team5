"""PREREG_DIFF SOLVER scorer: TIR-F (tag F) vs TIR-F + the installed-library sentence (tag FE, TIR_ENV=1), paired per instance,
clustered by problem; also how often a complete solver is called and how often a tool call times out.
usage: python poc/tir_solver_score.py <mconf|mcong> [seeds...]"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tir_score as S
st = sys.argv[1]; seeds = [int(x) for x in sys.argv[2:]] or [1]; R, U = S.R, S.U
SOLV = re.compile(r"cp_model|ortools|linear_solver|milp\(|linprog\(")
A, D = {}, {}
for tag in ("F", "FE"):
    for s in seeds:
        p = f"{R}/tir_{st}_medium{tag}_s{s}.jsonl"
        if not os.path.exists(p):
            continue
        for r in map(json.loads, open(p)):
            A.setdefault(tag, {}).setdefault(r["id"], []).append((float(bool(r["correct"])), r["out_tokens"]))
            d = D.setdefault(tag, [0, 0, 0, 0]); d[0] += 1; d[1] += bool(SOLV.search(" ".join(r.get("codes", []))))
            d[2] += any("timed out" in o or "Timeout" in o for o in r.get("outs", [])); d[3] += r.get("finish") != "stop"
A = {k: {i: (sum(a for a, _ in v) / len(v), sum(t for _, t in v) / len(v)) for i, v in x.items()} for k, x in A.items()}
for k, x in A.items():
    n, sv, to, cut = D[k]
    print(f"{k:3s} n={len(x)} {100*sum(a for a, _ in x.values())/len(x):.1f}% @ {sum(t for _, t in x.values())/len(x)/1000:.2f}k utility {sum(U(*v) for v in x.values())/len(x):.2f}"
          f" | rows {n}: solver called {100*sv/n:.0f}%, a call timed out {100*to/n:.0f}%, not finished {cut}")
if "F" in A and "FE" in A:
    ids = [i for i in A["FE"] if i in A["F"]]; ky = [i.split("__")[0] for i in ids]
    print(f"FE − F (n={len(ids)}, {len(set(ky))} problems): accuracy {S.ci([100*(A['FE'][i][0]-A['F'][i][0]) for i in ids], ky)} "
          f"ktok {S.ci([(A['FE'][i][1]-A['F'][i][1])/1000 for i in ids], ky)} utility {S.ci([U(*A['FE'][i])-U(*A['F'][i]) for i in ids], ky)}")
