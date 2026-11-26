"""PREREG_DIFF SOLVER scorer: TIR-F (tag F) vs TIR-F + the installed-library sentence (tag FE, TIR_ENV=1), paired per instance,
clustered by problem; also how often a complete solver is called and how often a tool call times out.
usage: python poc/tir_solver_score.py <set> [seeds...]   (SOLVER_TAGS=base,new; default F,FE; SOLVER-U: SOLVER_TAGS=,E)"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tir_score as S
st = sys.argv[1]; seeds = [int(x) for x in sys.argv[2:]] or [1]; R, U = S.R, S.U
SOLV = re.compile(r"cp_model|ortools|linear_solver|milp\(|linprog\(")
A, D = {}, {}
TG = os.environ.get("SOLVER_TAGS", "F,FE").split(","); NB, NN = TG[0] or "TIR", TG[1]
for tag in TG:
    for s in seeds:
        p = f"{R}/tir_{st}_medium{tag}_s{s}.jsonl"
        if not os.path.exists(p):
            continue
        for r in map(json.loads, open(p)):
            A.setdefault(tag or "TIR", {}).setdefault(r["id"], []).append((float(bool(r["correct"])), r["out_tokens"]))
            d = D.setdefault(tag or "TIR", [0, 0, 0, 0]); d[0] += 1; d[1] += bool(SOLV.search(" ".join(r.get("codes", []))))
            d[2] += any("timed out" in o or "Timeout" in o for o in r.get("outs", [])); d[3] += r.get("finish") != "stop"
A = {k: {i: (sum(a for a, _ in v) / len(v), sum(t for _, t in v) / len(v)) for i, v in x.items()} for k, x in A.items()}
for k, x in A.items():
    n, sv, to, cut = D[k]
    print(f"{k:3s} n={len(x)} {100*sum(a for a, _ in x.values())/len(x):.1f}% @ {sum(t for _, t in x.values())/len(x)/1000:.2f}k utility {sum(U(*v) for v in x.values())/len(x):.2f}"
          f" | rows {n}: solver called {100*sv/n:.0f}%, a call timed out {100*to/n:.0f}%, not finished {cut}")
if NB in A and NN in A:
    a, b = A[NN], A[NB]; ids = [i for i in a if i in b]; ky = [i.split("__")[0] for i in ids]
    print(f"{NN} − {NB} (n={len(ids)}, {len(set(ky))} clusters): accuracy {S.ci([100*(a[i][0]-b[i][0]) for i in ids], ky)} "
          f"ktok {S.ci([(a[i][1]-b[i][1])/1000 for i in ids], ky)} utility {S.ci([U(*a[i])-U(*b[i]) for i in ids], ky)}")
    if os.environ.get("SOLVER_DUMP"):   # per-item differences, for pooling several sets
        json.dump({"ids": ids, "u": [U(*a[i])-U(*b[i]) for i in ids]}, open(os.environ["SOLVER_DUMP"], "w"))
