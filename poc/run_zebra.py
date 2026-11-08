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


# ZebraLogic (2502.01100), idea 14: the model only translates, a solver in the sandbox counts the solutions. A puzzle has exactly one, so a count of 1 is a free
# check on the translation, and 0 or 2 is label-free feedback. usage: run_zebra.py --zl <tag> <arm tr|think|direct> <seed> [--per K] [--max_tokens N]
ZL_SOLVE = """
import ast, itertools, json
from ortools.sat.python import cp_model
class _C(cp_model.CpSolverSolutionCallback):
    def __init__(self, v):
        super().__init__(); self.v, self.s = v, []
    def on_solution_callback(self):
        self.s.append({k: self.Value(x) for k, x in self.v.items()})
        if len(self.s) >= 2:
            self.StopSearch()
n = max(len(x) for x in groups.values())
m, v = cp_model.CpModel(), {}
for a, vals in groups.items():
    assert len(vals) == n, f"attribute {a} does not have {n} values"
    for x in vals:
        v[f"{a}:{x}"] = m.NewIntVar(1, n, f"{a}:{x}")
    m.AddAllDifferent([v[f"{a}:{x}"] for x in vals])
for c in clues:
    keys = sorted({t.slice.value for t in ast.walk(ast.parse(c, mode="eval")) if isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant)})
    assert keys and all(k in v for k in keys), f"unknown name in clue: {c}"
    code = compile(c, "clue", "eval")
    ok = [t for t in itertools.product(range(1, n + 1), repeat=len(keys)) if eval(code, {"abs": abs, "min": min, "max": max}, {"p": dict(zip(keys, t))})]
    m.AddAllowedAssignments([v[k] for k in keys], ok)
s = cp_model.CpSolver(); s.parameters.enumerate_all_solutions = True; s.parameters.num_workers = 1
cb = _C(v); s.Solve(m, cb)
g = {}
if cb.s:
    for a, vals in groups.items():
        row = [None] * n
        for x in vals:
            row[cb.s[0][f"{a}:{x}"] - 1] = x
        g[a] = row
print(json.dumps({"count": len(cb.s), "grid": g}))
"""
ZL_TR = ("{p}\n\nDo not solve the puzzle. Translate it. Give one ```python block that defines two things: `groups`, a dict from each attribute to the list of its values, "
         "with exactly these attribute names: {cols}; and `clues`, a list with one Python expression, as a string, for each clue. In an expression, p['Attribute:value'] is the "
         "house number (1 to {n}) of that value. Examples of strings: \"p['Name:Bob'] == p['Pet:cat']\", \"p['Name:Bob'] != 2\", \"p['Name:Bob'] < p['Pet:cat']\", "
         "\"p['Name:Bob'] + 1 == p['Pet:cat']\", \"abs(p['Name:Bob'] - p['Pet:cat']) == 1\". Keep each value exactly as the puzzle writes it.")
ZL_FACT = " \"There is one house between A and B\" means abs(p[A] - p[B]) == 2, two houses between means 3. A clue about one value's house uses a house number; never compare p[...] with a string."
ZL_FMT = "{p}\n\nSolve the puzzle. On the last line give JSON mapping each attribute ({cols}) to the list of its values for houses 1 to {n} in order."


def zl_gold(r):
    h, rows = r["solution"]["header"], r["solution"]["rows"]
    return {a: [str(x[i]).strip().lower() for x in rows] for i, a in enumerate(h) if a != "House"}


def zl_extract(text):
    """the last JSON value in an answer, as {attribute: [values by house]}: models also give a list of rows or a dict of houses (format is not what we measure)"""
    dec, i, g = json.JSONDecoder(), 0, None
    while i < len(text or ""):
        if text[i] in "{[":
            try:
                g, n = dec.raw_decode(text, i)
                i = n
                continue
            except ValueError:
                pass
        i += 1
    if isinstance(g, dict) and g and all(isinstance(v, dict) for v in g.values()):
        num = lambda k: int(re.sub(r"\D", "", str(k)) or 0)
        g = [g[k] for k in sorted(g, key=num)]
    if isinstance(g, list) and g and all(isinstance(x, dict) for x in g):
        g = {a: [x.get(a) for x in g] for a in g[0]}
    return g


def zl_score(g, gold):
    if not isinstance(g, dict):
        return False, 0.0
    low = {str(k).strip().lower(): [str(x).strip().lower() for x in v] for k, v in g.items() if isinstance(v, list)}
    n = sum(len(v) for v in gold.values())
    c = sum(x == y for a, v in gold.items() for x, y in zip(v, low.get(a.lower(), [])))
    return c == n, c / n


def zl_main():
    tag, arm, seed = sys.argv[2], sys.argv[3], int(sys.argv[4])
    opt = lambda k, d: int(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d
    per, mt, skip = opt("--per", 10), opt("--max_tokens", 16000 if arm == "think" else 8192 if arm == "trt" else 4096), opt("--skip", 0)
    tr = arm in ("tr", "trf", "trt")   # trf: with the fact below; trt: a translation with thinking on
    R = [json.loads(l) for l in open(os.path.join(os.environ["POC_DATA"], "zebralogic", "grid.jsonl"))]
    seen, P = {}, []
    for r in sorted(R, key=lambda r: (r["size"], int(r["id"].rsplit("-", 1)[1]))):
        seen[r["size"]] = seen.get(r["size"], 0) + 1
        if skip < seen[r["size"]] <= skip + per:   # --skip 10: the next puzzles of each size, unseen when ZL_FACT was written
            P.append(r)

    def run(r):
        gold = zl_gold(r)
        n, cols = len(next(iter(gold.values()))), ", ".join(gold)
        sd = seed * 10007 + int(r["id"].rsplit("-", 1)[1])
        row = {"id": r["id"], "size": r["size"], "arm": arm, "seed": seed}
        if not tr:
            o = chat_msgs([{"role": "user", "content": ZL_FMT.format(p=r["puzzle"], cols=cols, n=n)}], think=arm == "think", max_tokens=mt, temperature=0.7, seed=sd)
            ex, ca = zl_score(zl_extract(o["text"]), gold)
            return {**row, "exact": ex, "cell_acc": ca, "tokens": o["out_tokens"], "finish": o["finish"], "text": (o["text"] or "")[-1500:]}
        msgs = [{"role": "user", "content": ZL_TR.format(p=r["puzzle"], cols=cols, n=n) + (ZL_FACT if arm == "trf" else "")}]
        tok, hist = 0, []
        for rnd in range(3):
            o = chat_msgs(msgs, think=arm == "trt", max_tokens=mt, temperature=0.7, seed=sd + rnd)
            tok += o["out_tokens"]
            code = last_block(o["text"], ("python", "py", "python3"))
            res = run_python(code + "\n" + ZL_SOLVE, "", timeout=30, mem_bytes=4 << 30) if code else None
            try:
                out = json.loads(res.stdout.strip().splitlines()[-1])
            except (AttributeError, IndexError, ValueError):
                out = {"count": -1, "grid": {}}
            ex, ca = zl_score(out["grid"], gold)
            hist.append({"count": out["count"], "exact": ex, "cell_acc": ca, "tokens": o["out_tokens"], "err": (res.stderr[-300:] if res else "no code")})
            if out["count"] == 1:
                break
            fb = {-1: f"it failed to run: {(res.stderr[-600:] if res else 'no python block')}", 0: "the clues as you wrote them have no solution, so one of them is wrong",
                  2: "the clues as you wrote them allow more than one solution, so one of them is missing or too weak"}[out["count"]]
            msgs += [{"role": "assistant", "content": o["text"] or "(empty)"},
                     {"role": "user", "content": f"The puzzle has exactly one solution, but {fb}. Compare each clue with the puzzle and give the complete corrected ```python block."}]
        return {**row, "exact": ex, "cell_acc": ca, "count": out["count"], "tokens": tok, "rounds": len(hist), "hist": hist, "code": code}

    path = f"{RES}/zl_{tag}_{arm}_s{seed}.jsonl"
    with ThreadPoolExecutor(32) as ex, open(path, "w") as f:
        rows = []
        for r in ex.map(run, P):
            rows.append(r); f.write(json.dumps(r) + "\n"); f.flush()
    print(tag, arm, seed, f"{sum(r['exact'] for r in rows)}/{len(rows)}", f"tokens {sum(r['tokens'] for r in rows) / len(rows):.0f}", flush=True)


# AR-LSAT (Zhong et al. 2022; test split of Logic-LM), idea 14 on real text: the model writes a program that enumerates the arrangements and marks the options. A question has
# exactly one right option, so one mark is a free check, and any other number is label-free feedback. usage: run_zebra.py --ls <tag> <arm tr|trt|trs|trsd|trse|trk|think|direct> <seed> [--max_tokens N] [--dev]
LS_SOLVE = """
import json
print(json.dumps({"marks": sorted(k for k in "ABCDE" if qualifies[k])}))
"""
LS_Q = "{context}\n\nQuestion: {question}\n{options}"
LS_TR = ("{q}\n\nDo not answer by reasoning. Translate it. Give one ```python block that enumerates every arrangement the rules allow (itertools and ortools are available; keep it under "
         "a minute) and defines `qualifies`, a dict from each letter A to E to True or False, computed from that enumeration: True when the option is the answer to the question. "
         "A condition stated in the question is added to the rules first. \"Could be true\" means the option holds in at least one allowed arrangement, \"must be true\" in all of them, "
         "\"cannot be true\" in none; EXCEPT reverses the test.")
LS_FMT = "{q}\n\nEnd with a line \"Answer: X\" where X is the letter of the right option."
# arm trs (idea 18): the model writes only declarations, and the harness enumerates, applies the question's test and survives a predicate that raises (Logic-LM's
# declarations/constraints/options split, with enumeration in place of Z3). Crashes were 47% of tr's final rounds and the could/must/EXCEPT test was the model's to code.
LS_TRS = ("{q}\n\nDo not answer by reasoning. Translate it. Give one ```python block that defines only these names (itertools is available):\n"
          "- `arrangements()`: a generator yielding every candidate arrangement as a dict (it may yield ones that break the rules; keep it under a few million).\n"
          "- `RULES`: a list of functions, one per rule of the passage, each taking an arrangement and returning True when the rule holds.\n"
          "- `CONDITION`: a function for a condition the question itself adds (`lambda a: True` if none).\n"
          "- `OPTIONS`: a dict from each letter A to E to a function returning True when the option's statement holds in the arrangement (for a full or partial list, "
          "when the arrangement matches it).\n"
          "- `KIND`: \"could\" (could be true), \"must\" (must be true), \"cannot\" (cannot be true) or \"could_false\" (could be false), as the question asks, "
          "and `EXCEPT = True` if the question says EXCEPT.\n"
          "Do not compute the answer; the checker does that from these names.")
LS_TRS_SOLVE = """
import json, time
_t, _err, _ok = time.time(), {}, []
def _holds(f, a, name):
    try:
        return bool(f(a))
    except Exception as e:
        _err.setdefault(name, f"{type(e).__name__}: {e}"[:120]); return False
for _a in arrangements():
    if all(_holds(f, _a, f"rule {i + 1}") for i, f in enumerate(RULES)) and _holds(CONDITION, _a, "CONDITION"):
        _ok.append(_a)
    if time.time() - _t > 50:
        raise SystemExit("enumeration took over 50 s")
_k = {"could": "cannot", "cannot": "could", "must": "could_false", "could_false": "must"}[KIND] if globals().get("EXCEPT") else KIND
_n = {L: sum(_holds(OPTIONS[L], a, f"option {L}") for a in _ok) for L in "ABCDE"}
_q = {"could": lambda n: n > 0, "must": lambda n: n == len(_ok), "cannot": lambda n: n == 0, "could_false": lambda n: n < len(_ok)}[_k]
print(json.dumps({"marks": sorted(L for L in "ABCDE" if _q(_n[L])) if _ok else [], "allowed": len(_ok), "errors": _err}))
"""
# arm trsd: the same, plus where the arrangements are lost. An LSAT game always allows at least one arrangement, and so does each rule alone, so a rule that alone
# keeps none, or the first rule at which the running count reaches 0, locates the error without a label; per-option counts show what the question's test saw.
LS_TRSD_SOLVE = """
import json, time
_t, _err, _ok, _N = time.time(), {}, [], 0
def _holds(f, a, name):
    try:
        return bool(f(a))
    except Exception as e:
        _err.setdefault(name, f"{type(e).__name__}: {e}"[:120]); return False
_alone, _run = [0] * len(RULES), [0] * len(RULES)
for _a in arrangements():
    _N += 1
    _h = [_holds(f, _a, f"rule {i + 1}") for i, f in enumerate(RULES)]
    for i, h in enumerate(_h):
        _alone[i] += h
    for i in range(len(_h)):
        if not _h[i]:
            break
        _run[i] += 1
    if all(_h) and _holds(CONDITION, _a, "CONDITION"):
        _ok.append(_a)
    if time.time() - _t > 50:
        raise SystemExit("enumeration took over 50 s")
_k = {"could": "cannot", "cannot": "could", "must": "could_false", "could_false": "must"}[KIND] if globals().get("EXCEPT") else KIND
_n = {L: sum(_holds(OPTIONS[L], a, f"option {L}") for a in _ok) for L in "ABCDE"}
_q = {"could": lambda n: n > 0, "must": lambda n: n == len(_ok), "cannot": lambda n: n == 0, "could_false": lambda n: n < len(_ok)}[_k]
print(json.dumps({"marks": sorted(L for L in "ABCDE" if _q(_n[L])) if _ok else [], "allowed": len(_ok), "errors": _err,
                  "diag": {"candidates": _N, "alone": _alone, "running": _run, "options": _n, "test": _k}}))
"""


# arm trse (idea 22): trs, but the harness sets EXCEPT from the question's text after the model's code. In trs dev, 42 of 57 EXCEPT = True flags were on
# questions without EXCEPT ("CANNOT be true" read as a reversal on top of KIND = "cannot"), which marks the complement of the answer.
# arm trk (idea 20): the harness owns the arrangement's shape. In trsd's zero-allowed dev questions most rules failed by reading a different shape than
# arrangements() made (names local to the generator, dicts keyed the other way), so the model declares entities and attributes and the harness builds the candidates.
LS_TRK = ("{q}\n\nDo not answer by reasoning. Translate it. Give one ```python block that defines only these names:\n"
          "- `ENTITIES`: the list of people or things being placed, as strings.\n"
          "- `DIMS`: a dict from each attribute name to the list of its possible values; every entity gets exactly one value of each attribute "
          "(put None in the list if an entity may be left out).\n"
          "- `DISTINCT`: the list of attribute names for which no two entities may share a value (None excepted); `[]` if none.\n"
          "The checker builds every candidate arrangement `a` itself, as a dict from each entity to a dict from attribute name to value, for example "
          "`a[\"Fred\"][\"day\"] == 3`. Do not define arrangements. Write every function against exactly that shape, using only `a`, the names above and the helper "
          "`who(a, attr, value)`, which returns the list of entities with that value.\n"
          "- `RULES`: a list of functions, one per rule of the passage, each taking an arrangement and returning True when the rule holds.\n"
          "- `CONDITION`: a function for a condition the question itself adds (`lambda a: True` if none).\n"
          "- `OPTIONS`: a dict from each letter A to E to a function returning True when the option's statement holds in the arrangement (for a full or partial list, "
          "when the arrangement matches it).\n"
          "- `KIND`: \"could\" (could be true), \"must\" (must be true), \"cannot\" (cannot be true) or \"could_false\" (could be false), as the question asks, "
          "and `EXCEPT = True` if the question says EXCEPT.\n"
          "Do not compute the answer; the checker does that from these names.")
LS_TRK_GEN = """
import itertools, math
def who(a, attr, value):
    return [e for e in ENTITIES if a[e][attr] == value]
_E, _D, _dist = list(ENTITIES), list(DIMS), set(globals().get("DISTINCT") or [])
def _choices(d):
    v = list(DIMS[d])
    if d in _dist and None not in v:
        return math.perm(len(v), len(_E)) if len(v) >= len(_E) else 0, lambda: itertools.permutations(v, len(_E))
    if d in _dist:
        return len(v) ** len(_E), lambda: (t for t in itertools.product(v, repeat=len(_E)) if len([x for x in t if x is not None]) == len({x for x in t if x is not None}))
    return len(v) ** len(_E), lambda: itertools.product(v, repeat=len(_E))
_C = [_choices(d) for d in _D]
if math.prod(n for n, _ in _C) > 3_000_000:
    raise SystemExit(f"{math.prod(n for n, _ in _C)} candidate arrangements from ENTITIES and DIMS, over the limit of 3,000,000: narrow DIMS or move fixed facts into the values")
def arrangements():
    for combo in itertools.product(*[list(g()) for _, g in _C]):
        yield {e: {d: combo[j][i] for j, d in enumerate(_D)} for i, e in enumerate(_E)}
"""


def ls_main():
    tag, arm, seed = sys.argv[2], sys.argv[3], int(sys.argv[4])
    mt = int(sys.argv[sys.argv.index("--max_tokens") + 1]) if "--max_tokens" in sys.argv else 16000 if arm == "think" else 8192 if arm == "trt" else 4096
    P = json.load(open(os.path.join(os.environ["POC_DATA"], "arlsat", ("dev" if "--dev" in sys.argv else "test") + ".json")))

    def run(k, r):
        q, sd = LS_Q.format(context=r["context"], question=r["question"], options="\n".join(r["options"])), seed * 10007 + k
        row = {"id": r["id"], "arm": arm, "seed": seed, "gold": r["answer"]}
        if arm in ("think", "direct"):
            o = chat_msgs([{"role": "user", "content": LS_FMT.format(q=q)}], think=arm == "think", max_tokens=mt, temperature=0.7, seed=sd)
            a = re.findall(r"Answer:\W*([A-E])\b", o["text"] or "")
            return {**row, "pick": a[-1] if a else None, "exact": bool(a) and a[-1] == r["answer"], "tokens": o["out_tokens"], "finish": o["finish"], "text": (o["text"] or "")[-800:]}
        msgs, tok, hist = [{"role": "user", "content": (LS_TRK if arm == "trk" else LS_TRS if arm in ("trs", "trsd", "trse") else LS_TR).format(q=q)}], 0, []
        marks, code = None, ""
        for rnd in range(3):
            try:
                o = chat_msgs(msgs, think=arm == "trt", max_tokens=mt, temperature=0.7, seed=sd + rnd)
            except Exception as e:   # a repair round past the context length: keep what the earlier rounds gave
                hist.append({"marks": None, "tokens": 0, "err": f"request failed: {str(e)[:200]}"})
                break
            tok += o["out_tokens"]
            code = last_block(o["text"], ("python", "py", "python3"))
            res = run_python(code + "\n" + {"trs": LS_TRS_SOLVE, "trsd": LS_TRSD_SOLVE, "trk": LS_TRK_GEN + LS_TRS_SOLVE, "trse": f"\nEXCEPT = {'EXCEPT' in r['question']}\n" + LS_TRS_SOLVE}.get(arm, LS_SOLVE), "", timeout=60, mem_bytes=4 << 30) if code else None
            try:
                out = json.loads(res.stdout.strip().splitlines()[-1])
                marks = out["marks"]
            except (AttributeError, IndexError, ValueError, KeyError, TypeError):
                out, marks = {}, None
            hist.append({"marks": marks, "tokens": o["out_tokens"], "err": (res.stderr[-300:] if res else "no code"), "allowed": out.get("allowed"), "errors": out.get("errors"), "diag": out.get("diag")})
            if marks is not None and len(marks) == 1:
                break
            fb = f"it failed to run: {(res.stderr[-600:] if res else 'no python block')}" if marks is None else f"your program marks {len(marks)} options ({', '.join(marks) or 'none'})"
            if marks is not None and "allowed" in out:
                fb += f"; {out['allowed']} arrangements pass the rules" + (f", and these raised (counted as False): {json.dumps(out['errors'])[:500]}" if out.get("errors") else "")
            if marks is not None and "diag" in out:
                d = out["diag"]
                fb += (f". Of {d['candidates']} candidate arrangements, each rule alone keeps {d['alone']}; applied in order, {d['running']} remain after each rule"
                       f" (a real question always allows at least one arrangement, and so does each rule alone); the question's condition leaves {out['allowed']};"
                       f" among those, each option holds in {d['options']}, and the test applied was \"{d['test']}\"")
            msgs += [{"role": "assistant", "content": o["text"] or "(empty)"},
                     {"role": "user", "content": f"The question has exactly one right option, but {fb}. Compare each rule and the question with your program and give the complete corrected ```python block."}]
        return {**row, "marks": marks, "count": -1 if marks is None else len(marks), "pick": marks[0] if marks and len(marks) == 1 else None, "exact": marks == [r["answer"]],
                "tokens": tok, "rounds": len(hist), "hist": hist, "code": code}

    path = f"{RES}/ls_{tag}{'_dev' if '--dev' in sys.argv else ''}_{arm}_s{seed}.jsonl"
    rows = [json.loads(l) for l in open(path)] if os.path.exists(path) else []   # resume: keep rows already written
    done = {r["id"] for r in rows}
    with ThreadPoolExecutor(32) as ex, open(path, "a") as f:
        for r in ex.map(lambda a: run(*a), [(k, r) for k, r in enumerate(P) if r["id"] not in done]):
            rows.append(r); f.write(json.dumps(r) + "\n"); f.flush()
    print(tag, arm, seed, f"{sum(r['exact'] for r in rows)}/{len(rows)}", f"tokens {sum(r['tokens'] for r in rows) / len(rows):.0f}", flush=True)


if __name__ == "__main__":
    {"--zl": zl_main, "--ls": ls_main}.get(sys.argv[1], main)()
