"""T1 — metamorphic invariance for combinatorial optimization (CO analogue of G2).

Each base instance gets semantics-preserving variants whose optimum is known (unchanged or scaled):
  knapsack: permute items | weights & capacity x3 (opt same) | values x2 (opt x2) | dummy item (too heavy, huge value)
  tsp     : relabel cities | translate (+500, +500) | rotate 90 deg | mirror           (distances unchanged)
  color   : relabel nodes | shuffle edge order | add an isolated node                 (opt same)
  sched   : permute jobs | processing times x3 (opt x3) | add a zero-length job       (opt same)
Arms: direct, heuristic, solver (+ up to R repair rounds). Per instance we report whether the arm's NORMALISED objective
(value / known scale) is identical across all variants (consistency) and whether all are optimal.
"""
import argparse
import json
import os
import random
import re
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
from llm import chat_msgs, last_block  # noqa: E402
from run_co import describe, gen, objective, parse_solution, prompt, reference  # noqa: E402
from sandbox import run_python  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root (was hard-coded)
RES = f"{ROOT}/results"
CELLS = [("knapsack", 20), ("knapsack", 40), ("tsp", 12), ("tsp", 20), ("color", 20), ("sched", 20)]


def variants(prob, inst, rng):
    V = {"identity": (inst, 1)}
    if prob == "knapsack":
        it = inst["items"]; perm = rng.sample(range(len(it)), len(it))
        V["permute"] = ({"items": [it[i] for i in perm], "cap": inst["cap"]}, 1)
        V["scale_w"] = ({"items": [(3 * w, v) for w, v in it], "cap": 3 * inst["cap"]}, 1)
        V["scale_v"] = ({"items": [(w, 2 * v) for w, v in it], "cap": inst["cap"]}, 2)
        k = rng.randrange(len(it) + 1)
        V["dummy"] = ({"items": it[:k] + [(inst["cap"] + 1, 10 ** 4)] + it[k:], "cap": inst["cap"]}, 1)
    elif prob == "tsp":
        P = inst["pts"]; perm = rng.sample(range(len(P)), len(P))
        V["relabel"] = ({"pts": [P[i] for i in perm]}, 1)
        V["translate"] = ({"pts": [(x + 500, y + 500) for x, y in P]}, 1)
        V["rot90"] = ({"pts": [(-y + 100, x) for x, y in P]}, 1)
        V["mirror"] = ({"pts": [(100 - x, y) for x, y in P]}, 1)
    elif prob == "color":
        n = inst["n"]; perm = rng.sample(range(n), n)
        V["relabel"] = ({"n": n, "edges": sorted((min(perm[a], perm[b]), max(perm[a], perm[b])) for a, b in inst["edges"])}, 1)
        V["shuffle_edges"] = ({"n": n, "edges": rng.sample(inst["edges"], len(inst["edges"]))}, 1)
        V["isolated"] = ({"n": n + 1, "edges": inst["edges"]}, 1)
    else:
        J = inst["jobs"]; perm = rng.sample(range(len(J)), len(J))
        V["permute"] = ({"jobs": [J[i] for i in perm], "m": inst["m"]}, 1)
        V["scale"] = ({"jobs": [3 * p for p in J], "m": inst["m"]}, 3)
        V["zero_job"] = ({"jobs": J + [0], "m": inst["m"]}, 1)
    return V


def run_arm(prob, inst, arm, a):
    msgs = [{"role": "user", "content": prompt(arm, prob, inst)}]
    o = chat_msgs(msgs, think=a.think, max_tokens=a.max_tokens, temperature=0.0)
    if arm == "direct":
        return parse_solution(arm, o["text"])
    for rnd in range(a.repair + 1):
        code = last_block(o["text"], ("python", "py", "python3"))
        fb = None
        if not code:
            fb = "no Python code block was found in your answer"
        elif arm == "heuristic" and re.search(r"ortools|pulp|scipy|cvxpy|gurobi|mip\b", code):
            fb = "you used a solver/optimisation library, which is not allowed here"
        else:
            r = run_python(code, describe(prob, inst)[1], timeout=40, mem_bytes=4 << 30)
            if r.status != "ok":
                fb = f"the program failed ({r.status}). stderr:\n{r.stderr[-1500:]}"
            else:
                sol = parse_solution(arm, "", r.stdout)
                if sol and objective(prob, inst, sol)[0]:
                    return sol
                fb = ("the printed solution is missing or INFEASIBLE" if not a.fb_detail else
                      "the printed solution is INFEASIBLE (it violates a constraint or has the wrong format/length)")
        if rnd == a.repair:
            return None
        msgs += [{"role": "assistant", "content": o["text"] or "(empty)"},
                 {"role": "user", "content": f"Your program did not work: {fb}\nFix it and give the complete corrected program in a single ```python code block."}]
        o = chat_msgs(msgs, think=a.think, max_tokens=a.max_tokens, temperature=0.0)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_tag", required=True)
    ap.add_argument("--arms", default="direct,heuristic,solver")
    ap.add_argument("--think", action="store_true")
    ap.add_argument("--max_tokens", type=int, default=4096)
    ap.add_argument("--repair", type=int, default=2)
    ap.add_argument("--n_inst", type=int, default=6)
    ap.add_argument("--probs", default="", help="comma list to restrict CELLS by problem")
    ap.add_argument("--fb_detail", action="store_true", help="repair feedback names format/length (as run_co.py does)")
    a = ap.parse_args()
    jobs = []
    for prob, n in [c for c in CELLS if not a.probs or c[0] in a.probs.split(",")]:
        for i in range(a.n_inst):
            rng = random.Random(f"meta-{prob}-{n}-{i}")
            inst = gen(prob, n, random.Random(f"{prob}-{n}-{i}"))
            for vname, (x, scale) in variants(prob, inst, rng).items():
                for arm in a.arms.split(","):
                    jobs.append((prob, n, i, vname, x, scale, arm))
    ref_cache = {}

    def run(j):
        prob, n, i, vname, x, scale, arm = j
        key = (prob, n, i, vname)
        if key not in ref_cache:
            ref_cache[key] = reference(prob, x)[0]
        sol = run_arm(prob, x, arm, a)
        feas, val = objective(prob, x, sol) if sol else (False, None)
        return {"prob": prob, "n": n, "inst": i, "variant": vname, "arm": arm, "scale": scale, "feasible": feas,
                "value": val, "norm_value": (val / scale if val is not None else None), "ref": ref_cache[key],
                "optimal": feas and val == ref_cache[key]}
    with ThreadPoolExecutor(48) as ex, open(f"{RES}/cometa_{a.model_tag}.jsonl", "w") as f:
        for r in ex.map(run, jobs):
            f.write(json.dumps(r) + "\n"); f.flush()


if __name__ == "__main__":
    main()
