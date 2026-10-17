"""V1-JSSP (docs/prereg/PREREG_V.md): verify once, reuse on job-shop. Candidates = H5 programs written for 8 training instances (2 seeds);
the one feasible on the most training instances (ties: lower mean makespan / reference) runs on the other 32 instances.
usage: python analyze_reuse_jssp.py <tag> [<tag> ...]     (tag = results/h5/sol_<tag>_s{1,2}.jsonl prefix)"""
import json, os, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_jssp import RES, TLIM, names, score  # noqa: E402

TRAIN = ["la01", "la06", "la11", "la16", "la21", "la26", "la31", "la36"]
TEST = [n for n in names() if n not in TRAIN]
REF = {n: v["makespan"] for n, v in json.load(open(f"{RES}/ref.json")).items()}


def run_on(code, insts, workers=4):   # CP-SAT programs are multi-threaded: few at a time
    with ThreadPoolExecutor(workers) as ex:
        return dict(zip(insts, ex.map(lambda n: score(n, code, TLIM + 30), insts)))


for tag in sys.argv[1:]:
    cands = [r for sd in (1, 2) for r in map(json.loads, open(f"{RES}/sol_{tag}_s{sd}.jsonl")) if r["name"] in TRAIN and r.get("code")]
    best = None
    for c in cands:
        res = run_on(c["code"], TRAIN)
        nf = sum(v["feasible"] for v in res.values())
        mg = sum(v["makespan"] / REF[n] for n, v in res.items() if v["feasible"]) / max(1, nf)
        if best is None or (nf, -mg) > (best[0], -best[1]):
            best = (nf, mg, c)
    res = run_on(best[2]["code"], TEST)
    g = [100 * (v["makespan"] / REF[n] - 1) for n, v in res.items() if v["feasible"]]
    print(f"{tag}: {len(cands)} candidates; best feasible on {best[0]}/8 training; reused on {len(TEST)} test: feasible {len(g)} "
          f"({100 * len(g) / len(TEST):.0f}%), mean gap {sum(g) / max(1, len(g)):.2f}%, max {max(g) if g else float('nan'):.2f}%; "
          f"generation tokens {sum(c.get('out_tokens') or 0 for c in cands)}", flush=True)
