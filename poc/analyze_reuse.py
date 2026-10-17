"""V1 (docs/prereg/PREREG_V.md): verify once, reuse the program. Candidates = an arm's programs generated for the 8 FM mining instances
(2 seeds -> 16); each runs on all 8 mining instances; the one feasible on the most (ties: lower mean distance) runs on the 48 test instances.
usage: python analyze_reuse.py <arm> [<arm> ...]      (arm = a results/h3/sol_<arm>_s{1,2}.jsonl prefix, e.g. oss120_low_plain)"""
import json, os, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_solomon import RES, TLIM, names, score  # noqa: E402

MINE = ["c101", "c201", "r101", "r201", "rc101", "rc201", "r105", "rc105"]
TEST = [n for n in names() if n not in MINE]
B = json.load(open(f"{RES}/bks.json")); R0 = json.load(open(f"{RES}/ref.json"))["ortools300_ins"]
REF = {n: min(B[n]["distance"], R0[n]["distance"]) for n in B}


def run_on(code, insts, workers=12):
    with ThreadPoolExecutor(workers) as ex:
        return dict(zip(insts, ex.map(lambda n: score(n, code, TLIM + 30), insts)))


out = {}
for arm in sys.argv[1:]:
    seeds = [int(x) for x in os.environ.get("REUSE_SEEDS", "1,2").split(",")]   # V1s: more candidates (seeds 3-8 generated on the mining set only)
    cands = [r for sd in seeds for r in map(json.loads, open(f"{RES}/sol_{arm}_s{sd}.jsonl")) if r["name"] in MINE and r.get("code")]
    best = None
    for i, c in enumerate(cands):
        res = run_on(c["code"], MINE)
        nf = sum(v["feasible"] for v in res.values())
        md = sum(v["distance"] / REF[n] for n, v in res.items() if v["feasible"]) / max(1, nf)
        if best is None or (nf, -md) > (best[0], -best[1]):
            best = (nf, md, i, c)
    if best is None or best[0] == 0:
        out[arm] = {"candidates": len(cands), "best_mining": 0, "test_feasible": 0}
        print(f"{arm}: {len(cands)} candidates, none feasible on any mining instance -> reuse fails", flush=True)
        continue
    res = run_on(best[3]["code"], TEST)
    g = sorted(100 * (v["distance"] / REF[n] - 1) for n, v in res.items() if v["feasible"])
    tok = sum(c.get("out_tokens") or 0 for c in cands)
    out[arm] = {"candidates": len(cands), "best_mining": best[0], "test_feasible": len(g), "median_gap": g[len(g) // 2] if g else None,
                "within5": sum(x <= 5 for x in g), "gen_tokens": tok, "picked": best[3]["name"]}
    print(f"{arm}: {len(cands)} candidates; best feasible on {best[0]}/8 mining; reused on 48 test: feasible {len(g)} "
          f"({100 * len(g) / 48:.0f}%), median gap {out[arm]['median_gap']}, within 5% {out[arm]['within5']}; generation tokens {tok}", flush=True)
json.dump(out, open(f"{RES}/reuse_v1{os.environ.get('REUSE_SUFFIX', '')}.json", "w"), indent=1)
