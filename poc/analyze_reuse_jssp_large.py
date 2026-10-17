"""V1x-J (results/PREREG_V.md): reused job-shop programs on the 42 larger OR-Library instances (results/h5/large_root/instances).
The V1 pick (most feasible on the 8 Lawrence training instances, ties by mean makespan / reference) runs unchanged; reference = REF CP-SAT.
usage: python analyze_reuse_jssp_large.py <tag> [<tag> ...]"""
import json, os, statistics as st, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_jssp as J  # noqa: E402

TRAIN = ["la01", "la06", "la11", "la16", "la21", "la26", "la31", "la36"]
BASE = J.RES; LARGE = f"{BASE}/large_root"
REFL = {n: v["makespan"] for n, v in json.load(open(f"{BASE}/ref.json")).items()}


def run_set(code, insts, root, workers, timeout=J.TLIM + 30):
    J.RES = root
    with ThreadPoolExecutor(workers) as ex:
        out = dict(zip(insts, ex.map(lambda n: J.score(n, code, timeout), insts)))
    J.RES = BASE
    return out


large = sorted(f[:-4] for f in os.listdir(f"{LARGE}/instances"))
ref_f = f"{LARGE}/ref.json"
REF = json.load(open(ref_f)) if os.path.exists(ref_f) else {}
missing = [n for n in large if not REF.get(n)]
if missing:   # the REF program runs 120 s: it needs a 200 s wall limit (a 90 s limit killed half of the references, 2026-10-16)
    R = run_set(J.REF, missing, LARGE, 3, timeout=200)
    REF.update({n: v["makespan"] for n, v in R.items()})
    json.dump(REF, open(ref_f, "w"), indent=1)
print("reference available:", sum(bool(v) for v in REF.values()), "of", len(large), flush=True)
for tag in sys.argv[1:]:
    cands = [r for sd in (1, 2) for r in map(json.loads, open(f"{BASE}/sol_{tag}_s{sd}.jsonl")) if r["name"] in TRAIN and r.get("code")]
    best = None
    for c in cands:
        res = run_set(c["code"], TRAIN, BASE, 4)
        nf = sum(v["feasible"] for v in res.values())
        mg = sum(v["makespan"] / REFL[n] for n, v in res.items() if v["feasible"]) / max(1, nf)
        if best is None or (nf, -mg) > (best[0], -best[1]):
            best = (nf, mg, c)
    res = run_set(best[2]["code"], large, LARGE, 3)
    json.dump({n: v["makespan"] for n, v in res.items()}, open(f"{LARGE}/reuse_{tag}.json", "w"), indent=1)
    g = {n: 100 * (v["makespan"] / REF[n] - 1) for n, v in res.items() if v["feasible"] and REF.get(n)}
    small = [x for n, x in g.items() if n.startswith(("abz5", "abz6", "ft06", "ft10", "orb"))]
    print(f"{tag}: pick feasible on {best[0]}/8 training | 42 larger instances: feasible {sum(v['feasible'] for v in res.values())}/42, "
          f"mean gap {st.mean(g.values()):.2f}% (≤ 10×10: {st.mean(small):.2f}%, max {max(g.values()):.1f}%)", flush=True)
