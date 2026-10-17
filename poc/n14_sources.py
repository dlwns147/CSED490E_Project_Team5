"""N14 (docs/prereg/PREREG_N14.md): pick the source programs for adaptation. For a model's stored N10 programs of a source problem, run
every program on ALL instances of that problem (same sizes / n_inst as N10) and count optimal answers. good = the program optimal on
the most instances (ties: fewer tokens); bad = a program that runs but is optimal on none (ties: most instances feasible = plausible).
Also the best knapsack program (an unrelated verified program). Writes results/n14/src_<prefix>_<prob>_{good,bad}.py + a summary.
usage: python n14_sources.py <prefix: S2_N10 | S2_N10m3> tsp cvrp knapsack"""
import glob, json, os, random, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_co import REAL, SIZES, HELDOUT, describe, gen, objective, parse_solution  # noqa: E402
from sandbox import run_python  # noqa: E402

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
REFS = json.load(open(f"{RES}/co_refs.json"))
pre = sys.argv[1]


def score(code, prob):
    ok = feas = 0
    for n in {**SIZES, **HELDOUT, **REAL}[prob]:
        for i in range(4):
            key = f"{prob}-{n}-{i}"; inst = gen(prob, n, random.Random(key))
            x = run_python(code, describe(prob, inst)[1], timeout=40, mem_bytes=4 << 30)   # as run_co.run_code
            sol = parse_solution("solver", "", x.stdout) if x.status == "ok" else None
            f, v = objective(prob, inst, sol) if sol else (False, None)
            feas += f; ok += f and v == REFS[key]["ref"]
    return ok, feas


summary = {}
for prob in sys.argv[2:]:
    progs = {}
    for f in sorted(glob.glob(f"{RES}/co_{pre}_co_*.jsonl")):
        for r in map(json.loads, open(f)):
            if r["prob"] == prob and r.get("code") and "cap16k" not in f:   # pool: optimal on its own instance (good) / ran, not optimal (bad)
                tag = "good" if (r["status"] == "ok" and r["feasible"] and r["gap"] == 0) else "bad" if r["status"] == "ok" else None
                if tag:
                    progs.setdefault(r["code"], (r.get("out_tokens") or 0, tag))
    rng = random.Random(0)
    codes = [c for t in ("good", "bad") for c in (lambda L: rng.sample(L, min(24, len(L))))(sorted(c for c in progs if progs[c][1] == t))]
    progs = {c: progs[c][0] for c in codes}
    with ThreadPoolExecutor(16) as ex:
        S = list(ex.map(lambda c: score(c, prob), codes))
    n_inst = 4 * len({**SIZES, **HELDOUT, **REAL}[prob])
    good = max(range(len(codes)), key=lambda j: (S[j][0], -progs[codes[j]]))
    bads = [j for j in range(len(codes)) if S[j][0] == 0 and S[j][1] > 0] or [j for j in range(len(codes)) if S[j][0] == 0]
    bad = max(bads, key=lambda j: (S[j][1], -progs[codes[j]])) if bads else None
    open(f"{RES}/n14/src_{pre}_{prob}_good.py", "w").write(codes[good])
    if bad is not None:
        open(f"{RES}/n14/src_{pre}_{prob}_bad.py", "w").write(codes[bad])
    summary[prob] = {"programs": len(codes), "instances": n_inst, "good_optimal": S[good][0], "good_feasible": S[good][1],
                     "bad_optimal": S[bad][0] if bad is not None else None, "bad_feasible": S[bad][1] if bad is not None else None,
                     "n_fully_correct": sum(s[0] == n_inst for s in S)}
    print(pre, prob, summary[prob], flush=True)
json.dump(summary, open(f"{RES}/n14/sources_{pre}.json", "w"), indent=1)
