"""PoC D — NL -> solver vs. direct reasoning on logic-grid ("zebra") puzzles, with and without thinking.

Puzzles: n houses x m attributes, each attribute a permutation of n values; clues are generated from a random hidden
solution until it is UNIQUE (checked with CP-SAT, solution limit 2), then redundant clues are pruned. Search space
(n!)^m grows from 216 (3x3) to 720^5 ~ 1.9e14 (6x5).
Arms:
  direct      : answer the grid (JSON) directly
  code        : write a Python program (any library) that prints the grid; up to R repairs with LABEL-FREE feedback
                (crash / unparseable output / which clue numbers the printed grid violates)
  (+ --think for either)
Scored against the unique solution: whole-grid exact match and cell accuracy. Tokens recorded for the cost side.
"""
import argparse
import ast
import json
import os
import random
import re
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
from llm import chat_msgs, last_block, strip_think  # noqa: E402
from sandbox import run_python  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root (was hard-coded)
RES = f"{ROOT}/results"
EXTRA_API = [   # correct but UNNEEDED CP-SAT features for zebra (distractor dose-response for NL->solver, cf. geometry S4d)
    "  b = m.NewBoolVar('b'); m.Add(x == y).OnlyEnforceIf(b); m.Add(x != y).OnlyEnforceIf(b.Not())   # reified constraint\n",
    "  m.AddElement(index_var, [10, 20, 30], target_var)               # target == list[index]\n",
    "  m.AddBoolOr([b1, b2, b3]); m.AddImplication(b1, b2)              # clauses on Boolean variables\n",
    "  iv = m.NewIntervalVar(start, size, end, 'iv'); m.AddNoOverlap([iv1, iv2])   # scheduling intervals\n",
    "  m.AddCircuit([(i, j, lit_ij) for ...])                           # Hamiltonian circuit over arc literals\n",
    "  m.AddMultiplicationEquality(z, [x, y]); m.AddModuloEquality(r, x, 3)   # non-linear helpers\n",
    "  m.AddMaxEquality(z, [x1, x2]); m.AddMinEquality(z, [x1, x2])      # z == max(...) / min(...)\n",
    "  m.AddAllowedAssignments([x, y], [(0, 1), (1, 2)])                # table constraint\n",
]
STATUS_LINE = ("  a solved model returns cp_model.OPTIMAL (for a pure satisfaction model too), so test "
               "`if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):`, never `st == cp_model.FEASIBLE`.\n")
API_DOC = """OR-Tools CP-SAT, correct usage for this kind of puzzle (a position variable per value):
  from ortools.sat.python import cp_model
  m = cp_model.CpModel()
  p = {v: m.NewIntVar(0, n - 1, v) for v in all_values}           # house index of each value
  m.AddAllDifferent([p[v] for v in values_of_one_attribute])       # once per attribute
  m.Add(p[a] == p[b]); m.Add(p[a] != p[b]); m.Add(p[a] == 2); m.Add(p[a] != 2)
  m.Add(p[a] + 1 == p[b])                                          # a directly left of b
  m.Add(p[a] < p[b])                                               # a somewhere left of b
  d = m.NewIntVar(-n, n, ""); m.Add(d == p[a] - p[b]); ad = m.NewIntVar(0, n, ""); m.AddAbsEquality(ad, d); m.Add(ad == 1)  # next to
  s = cp_model.CpSolver(); st = s.Solve(m); s.Value(p[v])
  never use Python if/and/or/abs()/| on solver expressions; build every constraint with m.Add(...).
"""
ATTRS = {
    "colour": ["red", "green", "blue", "yellow", "white", "purple"],
    "nationality": ["Brit", "Swede", "Dane", "German", "Norwegian", "Japanese"],
    "pet": ["dog", "cat", "bird", "fish", "horse", "rabbit"],
    "drink": ["tea", "coffee", "milk", "water", "juice", "soda"],
    "sport": ["tennis", "soccer", "golf", "chess", "rugby", "hockey"],
}
ORD = ["first", "second", "third", "fourth", "fifth", "sixth"]


def clue_text(c):
    k = c[0]
    if k == "pos":
        return f"The {c[1][1]} {c[1][0] if c[1][0] in ('colour',) else ''} person lives in the {ORD[c[2]]} house.".replace("  ", " ")
    if k == "notpos":
        return f"The {fmt(c[1])} does not live in the {ORD[c[2]]} house."
    if k == "same":
        return f"The {fmt(c[1])} is the {fmt(c[2])}."
    if k == "diff":
        return f"The {fmt(c[1])} is not the {fmt(c[2])}."
    if k == "leftof":
        return f"The {fmt(c[1])} lives directly to the left of the {fmt(c[2])}."
    if k == "next":
        return f"The {fmt(c[1])} lives next to the {fmt(c[2])}."
    if k == "before":
        return f"The {fmt(c[1])} lives somewhere to the left of the {fmt(c[2])}."


def fmt(av):
    a, v = av
    return {"colour": f"person in the {v} house", "nationality": v, "pet": f"{v} owner", "drink": f"{v} drinker",
            "sport": f"{v} player"}[a]


def clue_text2(c):  # uniform phrasing via fmt for every clue type
    if c[0] == "pos":
        return f"The {fmt(c[1])} lives in the {ORD[c[2]]} house."
    return clue_text(c)


def holds(c, pos):
    """pos[(attr, value)] -> house index"""
    k = c[0]
    if k == "pos":
        return pos[c[1]] == c[2]
    if k == "notpos":
        return pos[c[1]] != c[2]
    a, b = pos[c[1]], pos[c[2]]
    return {"same": a == b, "diff": a != b, "leftof": a + 1 == b, "next": abs(a - b) == 1, "before": a < b}[k]


def count_solutions(n, attrs, clues, limit=2):
    from ortools.sat.python import cp_model
    m = cp_model.CpModel()
    P = {(a, v): m.NewIntVar(0, n - 1, f"{a}_{v}") for a, vs in attrs.items() for v in vs}
    for a, vs in attrs.items():
        m.AddAllDifferent([P[(a, v)] for v in vs])
    for c in clues:
        k = c[0]
        if k == "pos":
            m.Add(P[c[1]] == c[2])
        elif k == "notpos":
            m.Add(P[c[1]] != c[2])
        else:
            x, y = P[c[1]], P[c[2]]
            if k == "same":
                m.Add(x == y)
            elif k == "diff":
                m.Add(x != y)
            elif k == "leftof":
                m.Add(x + 1 == y)
            elif k == "before":
                m.Add(x < y)
            else:
                d = m.NewIntVar(-n, n, ""); m.Add(d == x - y); ad = m.NewIntVar(0, n, ""); m.AddAbsEquality(ad, d); m.Add(ad == 1)

    class CB(cp_model.CpSolverSolutionCallback):
        def __init__(self):
            super().__init__(); self.k = 0

        def on_solution_callback(self):
            self.k += 1
            if self.k >= limit:
                self.StopSearch()
    s = cp_model.CpSolver(); s.parameters.enumerate_all_solutions = True; s.parameters.num_workers = 1
    cb = CB(); s.Solve(m, cb)
    return cb.k


def make_puzzle(n, m_attr, rng):
    names = list(ATTRS)[:m_attr]
    attrs = {a: rng.sample(ATTRS[a], n) for a in names}
    sol = {a: rng.sample(vs, n) for a, vs in attrs.items()}          # sol[a][house] = value
    pos = {(a, v): h for a in names for h, v in enumerate(sol[a])}
    items = list(pos)

    def rand_clue():
        k = rng.choices(["pos", "notpos", "same", "diff", "leftof", "next", "before"], [1, 1, 3, 1, 2, 2, 2])[0]
        x = rng.choice(items)
        if k in ("pos", "notpos"):
            h = pos[x] if k == "pos" else rng.choice([i for i in range(n) if i != pos[x]])
            return (k, x, h)
        y = rng.choice([i for i in items if i[0] != x[0] or k != "same"])
        if x == y:
            return None
        c = (k, x, y)
        return c if holds(c, pos) else None
    clues = []
    while count_solutions(n, attrs, clues) > 1:
        c = rand_clue()
        if c and c not in clues:
            clues.append(c)
    for c in list(clues):                       # prune redundant clues
        rest = [d for d in clues if d != c]
        if count_solutions(n, attrs, rest) == 1:
            clues = rest
    rng.shuffle(clues)
    return {"n": n, "attrs": attrs, "sol": sol, "clues": clues}


def render(p):
    n, attrs = p["n"], p["attrs"]
    lines = [f"There are {n} houses in a row, numbered 1 (leftmost) to {n} (rightmost). Each house has exactly one value of "
             f"each attribute below, and each value is used by exactly one house:"]
    lines += [f"- {a}: {', '.join(sorted(vs))}" for a, vs in attrs.items()]
    lines += ["", "Clues:"] + [f"{i + 1}. {clue_text2(c)}" for i, c in enumerate(p["clues"])]
    example = "{" + ", ".join(f'"{a}": [{", ".join(chr(34) + v + chr(34) for v in sorted(vs))}]' for a, vs in attrs.items()) + "}"
    return "\n".join(lines), example


def parse_grid(text, p):
    m = re.findall(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text or "", re.S)
    for blob in reversed(m):
        try:
            g = json.loads(blob)
        except Exception:
            try:   # lenient: a printed Python dict (single quotes) is scored too; format is not what we measure
                g = ast.literal_eval(blob)
            except Exception:
                continue
        if not isinstance(g, dict):
            continue
        if all(isinstance(g.get(a), list) and len(g[a]) == p["n"] for a in p["attrs"]):
            return {a: [str(x).strip() for x in g[a]] for a in p["attrs"]}
    return None


def violated(g, p):
    try:
        pos = {(a, v): g[a].index(v) for a, vs in p["attrs"].items() for v in vs}
    except ValueError:
        return None   # not a permutation
    return [i + 1 for i, c in enumerate(p["clues"]) if not holds(c, pos)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_tag", required=True)
    ap.add_argument("--arms", default="direct,code")
    ap.add_argument("--think", action="store_true")
    ap.add_argument("--max_tokens", type=int, default=4096)
    ap.add_argument("--repair", type=int, default=2)
    ap.add_argument("--n_per", type=int, default=8)
    ap.add_argument("--cells", default="3x3,4x3,4x4,5x4,5x5,6x5")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=None, help="sampling seed (with --temperature > 0); per-puzzle offset added")
    ap.add_argument("--doc_extra", type=int, default=0, help="append K correct but unneeded CP-SAT API lines to the snippet")
    ap.add_argument("--doc_status", action="store_true", help="add the status-check line (OPTIMAL or FEASIBLE) to the snippet")
    ap.add_argument("--api_doc", action="store_true", help="code arm: add a zebra-scoped CP-SAT API snippet (cf. CO S4b)")
    a = ap.parse_args()
    cache = f"{RES}/zebra_puzzles.json"
    P = json.load(open(cache)) if os.path.exists(cache) else {}
    n_cached = len(P)
    for cell in a.cells.split(","):
        n, m_ = map(int, cell.split("x"))
        for i in range(a.n_per):
            key = f"{cell}-{i}"
            if key not in P:
                P[key] = make_puzzle(n, m_, random.Random(key))
                P[key]["clues"] = [list(c) for c in P[key]["clues"]]
    if len(P) > n_cached:   # rewrite only when puzzles were added (concurrent runs read this file)
        json.dump(P, open(cache, "w"))
    for p in P.values():   # json turns tuples into lists
        p["clues"] = [(c[0], tuple(c[1]), tuple(c[2]) if isinstance(c[2], list) else c[2]) for c in p["clues"]]
    keys = [f"{c}-{i}" for c in a.cells.split(",") for i in range(a.n_per)]
    jobs = [(k, arm) for k in keys for arm in a.arms.split(",")]

    def run(j):
        key, arm = j
        p = P[key]
        text, example = render(p)
        fmt_ = (f"Give the answer as JSON mapping each attribute to the list of its values for houses 1..{p['n']} in order, "
                f"e.g. a line like {example} (with the correct order).")
        if arm == "direct":
            msgs = [{"role": "user", "content": f"{text}\n\nSolve the puzzle. {fmt_} Put the JSON on the last line."}]
        else:
            msgs = [{"role": "user", "content": f"{text}\n\nDo not solve the puzzle by hand. Write a Python 3 program that solves "
                     f"it (any standard library or OR-Tools is available; it must finish within 60 seconds) and prints only the "
                     f"answer. {fmt_} Give the program in a single ```python code block." + ("\n\n" + API_DOC + (STATUS_LINE if a.doc_status else "") + "".join(EXTRA_API[:a.doc_extra]) if a.api_doc else "")}]
        o = chat_msgs(msgs, think=a.think, max_tokens=a.max_tokens, temperature=a.temperature,
                          seed=None if a.seed is None else a.seed * 10007 + keys.index(key) * 7)
        tokens, rounds, code, err = o["out_tokens"], 0, None, ""
        while True:
            if arm == "direct":
                g = parse_grid(o["text"], p); status = "ok" if g else "no_answer"
                break
            code = last_block(o["text"], ("python", "py", "python3"))
            g, fb = None, None
            if not code:
                status, fb = "no_code", "no Python code block was found in your answer"
            else:
                r = run_python(code, "", timeout=60, mem_bytes=4 << 30)
                err = r.stderr[-300:]
                if r.status != "ok":
                    status, fb = r.status, f"the program failed ({r.status}). stderr:\n{r.stderr[-1500:]}"
                else:
                    g = parse_grid(r.stdout, p)
                    if not g:
                        status, fb = "bad_output", f"its output is not the required JSON: {r.stdout.strip()[:300]!r}"
                    else:
                        v = violated(g, p)
                        status = "ok"
                        if v is None:
                            fb = "the printed grid is not valid: every attribute must list each of its values exactly once"
                        elif v:
                            fb = f"the printed grid violates clue(s) {', '.join(map(str, v))}"
            if not fb or rounds >= a.repair:
                break
            rounds += 1
            msgs += [{"role": "assistant", "content": strip_think(o["text"] or "") or "(empty)"},   # drop thinking: ctx overflow
                     {"role": "user", "content": f"Your program did not work: {fb}.\nFix it and give the complete corrected "
                      f"program in a single ```python code block."}]
            try:
                o = chat_msgs(msgs, think=a.think, max_tokens=a.max_tokens, temperature=a.temperature,
                          seed=None if a.seed is None else a.seed * 10007 + keys.index(key) * 7 + rounds)
            except Exception as e:   # e.g. context overflow on a late repair round: keep the last result
                err = f"chat error: {str(e)[:200]}"
                break
            tokens += o["out_tokens"]
        cells = sum(g[at][h] == p["sol"][at][h] for at in p["attrs"] for h in range(p["n"])) if g else 0
        total = p["n"] * len(p["attrs"])
        lib = None if not code else ("ortools" if "ortools" in code else "constraint" if "constraint" in code else
                                     "z3" if "z3" in code else "itertools" if "itertools" in code else "other")
        return {"key": key, "cell": key.rsplit("-", 1)[0], "arm": arm, "think": a.think, "status": status,
                "exact": cells == total, "cell_acc": cells / total, "n_clues": len(p["clues"]), "tokens": tokens,
                "rounds": rounds, "finish": o["finish"], "lib": lib, "code": code, "err": err}
    with ThreadPoolExecutor(48) as ex, open(f"{RES}/zebra_{a.model_tag}.jsonl", "w") as f:
        for r in ex.map(run, jobs):
            f.write(json.dumps(r) + "\n"); f.flush()


if __name__ == "__main__":
    main()
