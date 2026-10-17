"""V1c (results/PREREG_V.md): reuse cost curve. Every candidate of a pool runs once on the 8 mining instances; candidates feasible on at least
one mining instance also run on the 48 test instances (results cached in results/h3/cand_eval_<arm>.json). Then, drawing k candidates
(without replacement, 2,000 draws), V1 picks the most mining-feasible one (ties: lower mean distance / reference); reported: expected test
feasibility of the pick and the tokens of k candidates.
usage: REUSE_SEEDS=1,2,... python analyze_reuse_curve.py <arm> [<arm> ...]"""
import hashlib, json, os, random, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_solomon import RES, TLIM, names, score  # noqa: E402

MINE = ["c101", "c201", "r101", "r201", "rc101", "rc201", "r105", "rc105"]
TEST = [n for n in names() if n not in MINE]
B = json.load(open(f"{RES}/bks.json")); R0 = json.load(open(f"{RES}/ref.json"))["ortools300_ins"]
REF = {n: min(B[n]["distance"], R0[n]["distance"]) for n in B}
seeds = [int(x) for x in os.environ.get("REUSE_SEEDS", "1,2").split(",")]


def evaluate(code, insts):
    with ThreadPoolExecutor(8) as ex:
        res = dict(zip(insts, ex.map(lambda n: score(n, code, TLIM + 30), insts)))
    return {n: (v["feasible"], v["distance"] / REF[n] if v["feasible"] else None) for n, v in res.items()}


for arm in sys.argv[1:]:
    cache_f = f"{RES}/cand_eval_{arm}.json"
    cache = json.load(open(cache_f)) if os.path.exists(cache_f) else {}
    cands = [r for sd in seeds if os.path.exists(f"{RES}/sol_{arm}_s{sd}.jsonl")
             for r in map(json.loads, open(f"{RES}/sol_{arm}_s{sd}.jsonl")) if r["name"] in MINE and r.get("code")]
    todo = [c for c in cands if hashlib.md5(c["code"].encode()).hexdigest() not in cache]

    def one(c):
        mv = evaluate(c["code"], MINE)
        nf = sum(f for f, _ in mv.values())
        md = sum(d for f, d in mv.values() if f) / nf if nf else None
        tv = evaluate(c["code"], TEST) if nf else {}
        return hashlib.md5(c["code"].encode()).hexdigest(), {"mining": nf, "mdist": md, "test": sum(f for f, _ in tv.values()), "tokens": c.get("out_tokens") or 0}
    with ThreadPoolExecutor(3) as ex:
        for k, v in ex.map(one, todo):
            cache[k] = v
    json.dump(cache, open(cache_f, "w"))
    E = [cache[hashlib.md5(c["code"].encode()).hexdigest()] for c in cands]
    tok = sum(e["tokens"] for e in E) / len(E)
    rng = random.Random(0); line = []
    for k in (1, 2, 4, 8, 16, 32, 64):
        if k > len(E):
            break
        tot = 0.0
        for _ in range(2000 if k < len(E) else 1):
            S = rng.sample(E, k)
            best = max(S, key=lambda e: (e["mining"], -(e["mdist"] or 9)))
            tot += best["test"] / len(TEST) if best["mining"] else 0.0
        line.append(f"k={k}: {100 * tot / (2000 if k < len(E) else 1):.0f}% @ {k * tok / 1000:.0f}k")
    print(f"{arm} ({len(E)} candidates; {sum(e['mining'] > 0 for e in E)} feasible on >= 1 mining; mean {tok:.0f} tokens): " + " | ".join(line), flush=True)
