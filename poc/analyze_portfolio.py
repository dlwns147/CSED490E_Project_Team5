"""V1p (docs/prereg/PREREG_V.md): portfolio of verified programs. Top-m candidates by mining feasibility (ties: mean distance) run on every test
instance; the shortest feasible solution is kept. usage: REUSE_SEEDS=... python analyze_portfolio.py <arm> [<arm> ...]"""
import json, os, statistics as st, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_solomon import RES, TLIM, names, score  # noqa: E402

MINE = ["c101", "c201", "r101", "r201", "rc101", "rc201", "r105", "rc105"]
TEST = [n for n in names() if n not in MINE]
B = json.load(open(f"{RES}/bks.json")); R0 = json.load(open(f"{RES}/ref.json"))["ortools300_ins"]
REF = {n: min(B[n]["distance"], R0[n]["distance"]) for n in B}
seeds = [int(x) for x in os.environ.get("REUSE_SEEDS", "1,2").split(",")]


def ev(code, insts):
    with ThreadPoolExecutor(8) as ex:
        return dict(zip(insts, ex.map(lambda n: score(n, code, TLIM + 30), insts)))


for arm in sys.argv[1:]:
    cands = [r for sd in seeds for r in map(json.loads, open(f"{RES}/sol_{arm}_s{sd}.jsonl")) if r["name"] in MINE and r.get("code")]
    with ThreadPoolExecutor(3) as ex:
        M = list(ex.map(lambda c: ev(c["code"], MINE), cands))
    key = lambda i: (sum(v["feasible"] for v in M[i].values()),
                     -st.mean([v["distance"] / REF[n] for n, v in M[i].items() if v["feasible"]] or [9]))
    order = sorted(range(len(cands)), key=key, reverse=True)[:5]
    with ThreadPoolExecutor(2) as ex:
        T = list(ex.map(lambda i: ev(cands[i]["code"], TEST), order))
    for m in (1, 3, 5):
        feas, gaps = 0, []
        for n in TEST:
            ds = [T[j][n]["distance"] for j in range(min(m, len(T))) if T[j][n]["feasible"]]
            if ds:
                feas += 1; gaps.append(100 * (min(ds) / REF[n] - 1))
        print(f"{arm} m={m}: feasible {feas}/48 | median gap {st.median(gaps) if gaps else float('nan'):.2f}% | mean gap {st.mean(gaps) if gaps else float('nan'):.2f}% "
              f"| mining feasibility of the top-{m}: {[key(i)[0] for i in order[:m]]}", flush=True)
