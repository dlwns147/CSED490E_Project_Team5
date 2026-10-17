"""V1x (docs/prereg/PREREG_V.md): size transfer of reused programs. The V1 pick of an arm (most feasible on the 8 Solomon mining instances,
ties by mean distance / reference) runs unchanged on the 60 Homberger 200-customer instances (results/h3/homberger200).
usage: REUSE_SEEDS=1,2 python analyze_reuse_size.py <arm> [<arm> ...]"""
import json, math, os, statistics as st, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_solomon import RES, TLIM, check, score  # noqa: E402
from sandbox import run_python  # noqa: E402

MINE = ["c101", "c201", "r101", "r201", "rc101", "rc201", "r105", "rc105"]
HD = f"{RES}/{os.environ.get('HOMB', 'homberger200')}"   # V1x: homberger200 | homberger400
HB = json.load(open(f"{HD}/bks.json"))
B = json.load(open(f"{RES}/bks.json")); R0 = json.load(open(f"{RES}/ref.json"))["ortools300_ins"]
REF = {n: min(B[n]["distance"], R0[n]["distance"]) for n in B}
seeds = [int(x) for x in os.environ.get("REUSE_SEEDS", "1,2").split(",")]


def load_h(name):
    L = open(f"{HD}/{name}.txt").read().replace("\r\n", "\n").split("\n")
    K, Q = map(int, L[4].split())
    rows = [list(map(float, l.split())) for l in L[9:] if len(l.split()) == 7]
    return {"K": K, "Q": Q, "xy": [(r[1], r[2]) for r in rows], "dem": [r[3] for r in rows], "ready": [r[4] for r in rows],
            "due": [r[5] for r in rows], "svc": [r[6] for r in rows]}


def run_h(code, name):
    inp = open(f"{HD}/{name}.txt").read().replace("\r\n", "\n")
    r = run_python(code, inp, timeout=int(os.environ.get("TL", TLIM)) + 60, mem_bytes=4 << 30)
    if r.status != "ok":
        return False, None, r.status
    ok, dist, veh, why = check(load_h(name), r.stdout)
    return ok, dist, why


insts = sorted(f[:-4] for f in os.listdir(HD) if f.endswith(".txt"))
for arm in sys.argv[1:]:
    cands = [r for sd in seeds for r in map(json.loads, open(f"{RES}/sol_{arm}_s{sd}.jsonl")) if r["name"] in MINE and r.get("code")]

    def mine(c):
        with ThreadPoolExecutor(8) as ex:
            res = list(ex.map(lambda n: (n, score(n, c["code"], TLIM + 30)), MINE))
        f = [(n, v) for n, v in res if v["feasible"]]
        return len(f), (st.mean(v["distance"] / REF[n] for n, v in f) if f else 9)
    with ThreadPoolExecutor(3) as ex:
        keys = list(ex.map(mine, cands))
    i = max(range(len(cands)), key=lambda k: (keys[k][0], -keys[k][1]))
    code = cands[i]["code"]
    if os.environ.get("TL"):   # V1x-TL: scale the reused program's own search time limit (no LLM call)
        import re
        code, k1 = re.subn(r"(time_limit\.seconds\s*=\s*)\d+", rf"\g<1>{os.environ['TL']}", code)
        code, k2 = re.subn(r"(time_limit\.FromSeconds\()\d+", rf"\g<1>{os.environ['TL']}", code)
        print(f"{arm}: time limit set to {os.environ['TL']} s in {k1 + k2} place(s)", flush=True)
    with ThreadPoolExecutor(8) as ex:
        R = dict(zip(insts, ex.map(lambda n: run_h(code, n), insts)))
    gaps = [100 * (d / HB[n]["distance"] - 1) for n, (ok, d, _) in R.items() if ok]
    why = {}
    for ok, _, w in R.values():
        if not ok:
            why[w] = why.get(w, 0) + 1
    print(f"{arm}: pick feasible on {keys[i][0]}/8 Solomon mining | {os.path.basename(HD)}: feasible {len(gaps)}/60, median gap {st.median(gaps) if gaps else math.nan:.2f}% "
          f"(vs vehicles-first best-known), failures {why}", flush=True)
