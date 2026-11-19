"""More baselines for PREREG_TYPED (user 11-19: "baselines are too few"), on the same MAMO ComplexLP graph-template problems (max flow, TSP).

usage: run_orbase.py <tag> <arm> <seed>   -> results/x3/orbase_<tag>_<arm>_s<seed>.jsonl
arms (all write a pywraplp program whose last printed line is the optimal value; the program runs in the sandbox):
  plain      the program, one round (the stronger-model baseline, e.g. gpt-oss-120b).
  selfdebug  Self-Debug (Chen et al. 2304.05128): program, run it, feed back the error / missing output / infeasibility, up to 3 rounds.
  fewshot    one worked example of the SAME template (a correct program written by us for a different instance) in the prompt:
             the strongest "teach the convention" baseline for typed translation.
  optimus    OptiMUS-style staged prompting (AhmadiTeshnizi et al. 2402.10172), single model: (1) parameters as JSON, (2) the formulation in
             math (variables, objective, constraints), (3) the code from (1)+(2), (4) one debugging round on an error.
  fiveel     LLMOPT's five-element formulation as a prompt (Jiang et al. 2410.13213; prompt only, no fine-tuning): sets, parameters,
             variables, objective, constraints, then the code.
"""
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
from llm import chat_msgs, last_block  # noqa: E402
from sandbox import run_python  # noqa: E402
import run_nlopt as RN  # noqa: E402
from run_typed import kind  # noqa: E402

BASE = ("{q}\n\nWrite a complete Python 3 program that formulates this problem as a (mixed-integer) linear program with Google OR-Tools "
        "(`from ortools.linear_solver import pywraplp`, solver 'SCIP'), solves it, and prints the optimal objective value on the last line "
        "(print \"No Best Solution\" if there is none). Give one ```python block.")
EX_FLOW = '''from ortools.linear_solver import pywraplp
# Example (different instance): maximum flow from node 0 to node 3; cap[(u, v)] is the capacity of the directed edge u -> v.
cap = {(0, 1): 5, (0, 2): 4, (1, 2): 2, (1, 3): 3, (2, 1): 1, (2, 3): 6, (1, 0): 2, (3, 0): 7}
s, t = 0, 3
nodes = {u for e in cap for u in e}
S = pywraplp.Solver.CreateSolver('SCIP')
f = {e: S.NumVar(0, c, f"f{e}") for e, c in cap.items()}
for v in nodes - {s, t}:
    S.Add(sum(f[e] for e in cap if e[1] == v) == sum(f[e] for e in cap if e[0] == v))
# the value is the NET flow out of the source (flow sent back into the source does not count)
S.Maximize(sum(f[e] for e in cap if e[0] == s) - sum(f[e] for e in cap if e[1] == s))
S.Solve()
print(S.Objective().Value())'''
EX_TSP = '''from ortools.linear_solver import pywraplp
# Example (different instance): visit every city exactly once and return to the start, minimum total cost (cost[(i, j)] directed).
cost = {(0, 1): 4, (1, 0): 4, (0, 2): 7, (2, 0): 7, (0, 3): 3, (3, 0): 3, (1, 2): 2, (2, 1): 2, (1, 3): 5, (3, 1): 5, (2, 3): 6, (3, 2): 6}
n = 4
S = pywraplp.Solver.CreateSolver('SCIP')
x = {e: S.BoolVar(f"x{e}") for e in cost}
for i in range(n):
    S.Add(sum(x[(i, j)] for j in range(n) if (i, j) in x) == 1)
    S.Add(sum(x[(j, i)] for j in range(n) if (j, i) in x) == 1)
# subtour elimination (Miller-Tucker-Zemlin): without it the cheapest answer is several separate loops, not one tour
u = {i: S.NumVar(1, n - 1, f"u{i}") for i in range(1, n)}
for (i, j) in cost:
    if i != 0 and j != 0:
        S.Add(u[i] - u[j] + n * x[(i, j)] <= n - 1)
S.Minimize(sum(c * x[e] for e, c in cost.items()))
S.Solve()
print(S.Objective().Value())'''
FIVE = ("{q}\n\nFirst write the problem's formulation in five parts: (1) sets, (2) parameters with their values, (3) decision variables, "
        "(4) objective, (5) constraints. Then write a complete Python 3 program with Google OR-Tools pywraplp (solver 'SCIP') that implements "
        "exactly that formulation and prints the optimal objective value on the last line (\"No Best Solution\" if none). Give one ```python block.")
OPT1 = "{q}\n\nList every parameter (given number) of this problem as one JSON object mapping a short name to its value (a number, list or table). Give only the JSON."
OPT2 = ("{q}\n\nParameters:\n{params}\n\nWrite the mathematical formulation: decision variables, the objective, and every constraint, each "
        "referring to the parameters by name. Do not write code.")
OPT3 = ("{q}\n\nParameters (JSON):\n{params}\n\nFormulation:\n{form}\n\nWrite a complete Python 3 program with Google OR-Tools pywraplp (solver "
        "'SCIP') that implements this formulation with these parameters and prints the optimal objective value on the last line (\"No Best "
        "Solution\" if none). Give one ```python block.")


def execute(code):
    r = run_python(code, "", timeout=60, mem_bytes=4 << 30) if code else None
    out = (r.stdout if r and r.status == "ok" else "") or ""
    lines = [l for l in out.strip().splitlines() if l.strip()]
    pred = RN.value_of(lines[-1]) if lines else None
    return pred, (r.status if r else "no_code"), ((r.stderr or "")[-600:] if r else "no python block")


def main():
    tag, arm, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
    P = [p for p in RN.problems("mamo") if p["id"].startswith("mamo_complex") and kind(p["q"])]

    def ask(msgs, sd, mt=4096):
        return chat_msgs(msgs, think=False, max_tokens=mt, temperature=0.7, seed=sd)

    def run(p):
        sd = seed * 10007 + int(p["id"].rsplit("-", 1)[1]); tok = 0; rounds = []
        if arm in ("selfdebug", "fewshot", "fiveel", "plain"):
            if arm == "fiveel":
                prompt = FIVE.format(q=p["q"])
            else:
                prompt = BASE.format(q=p["q"])
                if arm == "fewshot":
                    prompt += "\n\nA correct program for a different problem of the same kind:\n```python\n" + (EX_FLOW if kind(p["q"]) == "max_flow" else EX_TSP) + "\n```"
            msgs = [{"role": "user", "content": prompt}]
            for rnd in range(3 if arm == "selfdebug" else 1):
                o = ask(msgs, sd + rnd, 8192); tok += o["out_tokens"]
                code = last_block(o["text"] or "", ("python", "py", "python3"))
                pred, status, err = execute(code); rounds.append({"pred": pred, "status": status})
                if pred not in (None, "NBS"):
                    break
                fb = (f"Running it failed: {err}" if status != "ok" else "It printed no objective value." if pred is None else
                      "It reports no feasible / bounded solution, but the problem has an optimum.")
                msgs += [{"role": "assistant", "content": o["text"] or "(empty)"},
                         {"role": "user", "content": f"{fb} Fix the program and give the complete corrected ```python block."}]
        elif arm == "optimus":
            o1 = ask([{"role": "user", "content": OPT1.format(q=p["q"])}], sd); tok += o1["out_tokens"]
            params = (o1["text"] or "").strip()[-6000:]
            o2 = ask([{"role": "user", "content": OPT2.format(q=p["q"], params=params)}], sd + 1); tok += o2["out_tokens"]
            msgs = [{"role": "user", "content": OPT3.format(q=p["q"], params=params, form=(o2["text"] or "")[-6000:])}]
            for rnd in range(2):
                o = ask(msgs, sd + 2 + rnd, 8192); tok += o["out_tokens"]
                code = last_block(o["text"] or "", ("python", "py", "python3"))
                pred, status, err = execute(code); rounds.append({"pred": pred, "status": status})
                if status == "ok" and pred is not None:
                    break
                msgs += [{"role": "assistant", "content": o["text"] or "(empty)"},
                         {"role": "user", "content": f"Running it failed: {err} Fix the program and give the complete corrected ```python block."}]
        return {"id": p["id"], "kind": kind(p["q"]), "arm": arm, "pred": rounds[-1]["pred"] if rounds else None, "gold": p["gold"],
                "tokens": tok, "rounds": rounds}

    path = os.path.join(RN.RES, f"orbase_{tag}_{arm}_s{seed}.jsonl")
    with ThreadPoolExecutor(32) as ex, open(path, "w") as f:
        rows = []
        for r in ex.map(run, P):
            rows.append(r); f.write(json.dumps(r) + "\n"); f.flush()
    print(tag, arm, seed, f"{len(rows)} rows, tokens {sum(r['tokens'] for r in rows) / len(rows):.0f}")


if __name__ == "__main__":
    main()
