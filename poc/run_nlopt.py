"""X3 (docs/prereg/PREREG_X3.md): optimization word problems -> models (NL4OPT 245, IndustryOR 100). The answer is the optimal objective
value (or "No Best Solution" when infeasible / unbounded).
modes: mip   = Python program with OR-Tools pywraplp (SCIP), prints the optimal objective value;
       mipf  = mip + a 6-line exact pywraplp usage snippet (the API fact);
       cpsat = Python program with OR-Tools CP-SAT (integer model), prints the optimal objective value;
       text  = reason in text, final value in \\boxed{};
       think = mip with thinking on (Qwen) / the caller's higher reasoning effort (gpt-oss);
       thinkf = think + the snippet of mipf (X6: does the API fact make thinking pay?);
       mipa / thinka = mip / think + the library's public names by introspection (automatic fact, no human).
usage: POC_BASE_URL=... python run_nlopt.py <tag> <mode> <seed> [--think] [--max_tokens N] -> results/x3/opt_<tag>_<mode>_s<seed>.jsonl"""
import json, os, re, sys, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "x3")
TAIL = (" If the problem has no optimal solution (infeasible or unbounded), print exactly `No Best Solution`. Give the program in a single "
        "```python code block.")
P_MIP = ("{q}\n\nWrite a complete Python 3 program that formulates this problem as a (mixed-integer) linear program with Google OR-Tools "
         "(`from ortools.linear_solver import pywraplp`, solver SCIP), solves it, and prints ONLY the optimal objective value." + TAIL)
SNIP = ("\n\nOR-Tools pywraplp usage (exact API):\n```python\nfrom ortools.linear_solver import pywraplp\ns = pywraplp.Solver.CreateSolver('SCIP')\n"
        "x = s.IntVar(0, s.infinity(), 'x')      # or s.NumVar(lb, ub, name) for a continuous variable\ns.Add(2 * x + 3 <= 10)\n"
        "s.Maximize(5 * x)                       # or s.Minimize(...)\nst = s.Solve()                          # pywraplp.Solver.OPTIMAL, INFEASIBLE, UNBOUNDED\n"
        "print(s.Objective().Value() if st == pywraplp.Solver.OPTIMAL else 'No Best Solution')\n```")
def _auto_card():
    """MODEL / automatic facts (2026-10-18): the library's own public names, read by introspection; no human writes it"""
    from ortools.linear_solver import pywraplp
    return ("\n\nThe complete list of public names in OR-Tools pywraplp (anything else does not exist):\n" +
            "\n".join(f"pywraplp.{c}: " + ", ".join(n for n in dir(getattr(pywraplp, c)) if not n.startswith("_"))
                      for c in ("Solver", "Variable", "Constraint", "Objective")))


AUTO = _auto_card()


def _verified_examples(src_tag):
    """automatic usage fact (2026-10-18): programs of the same model WITHOUT any fact (mode mip, seed 1) that pass the label-free check
    (run and print a value) on the OTHER benchmark; for each problem the most similar such program (BM25 over question words) is shown"""
    import math
    from collections import Counter
    pool = []
    for r in _rows(f"{RES}/opt_{src_tag}_mip_s1.jsonl"):
        if r.get("status") == "ok" and r.get("pred") is not None and r.get("code"):
            pool.append(r)
    Q = {p["id"]: p for p in problems("all")}
    tok = lambda t: re.findall(r"[a-z]+", t.lower())
    docs = [(r, Counter(tok(Q[r["id"]]["q"]))) for r in pool if r["id"] in Q]
    df = Counter(w for _, d in docs for w in d); N = max(1, len(docs)); avg = sum(sum(d.values()) for _, d in docs) / N

    if os.environ.get("NLOPT_EX_SHORTEST"):   # X6-VER2: the shortest check-passing program of the other benchmark (least problem-specific)
        short = {}
        for r, _ in docs:
            b_ = Q[r["id"]]["src"]
            if b_ not in short or len(r["code"]) < len(short[b_]):
                short[b_] = r["code"]
        return lambda p: next((c for b_, c in short.items() if b_ != p["src"]), None)

    def best(p):
        q = set(tok(p["q"])); src = p["src"]
        cands = [(sum(math.log(1 + (N - df[w] + .5) / (df[w] + .5)) * d[w] * 2.2 / (d[w] + 1.2 * (.25 + .75 * sum(d.values()) / avg))
                      for w in q if w in d), r["code"]) for r, d in docs if Q[r["id"]]["src"] != src]
        return max(cands)[1] if cands else None
    return best
P_FREE = ("{q}\n\nWrite a complete Python 3 program that formulates this problem and solves it with a suitable solver library, "
          "whichever fits the problem class: Google OR-Tools (`pywraplp` with SCIP for linear / mixed-integer models, CP-SAT), cvxpy "
          "(convex continuous models, including quadratic and second-order cone constraints) or scipy.optimize. Print ONLY the optimal "
          "objective value." + TAIL)   # HO-L (PREREG_HO.md, 2026-10-19): 27 of 100 OptMATH problems are not linear
SNIP_TEXT = ("\n\nOR-Tools pywraplp usage, in words: create the solver with pywraplp.Solver.CreateSolver('SCIP'); make an integer "
             "variable with s.IntVar(lower, upper, name) (a continuous one with s.NumVar(lower, upper, name)); add a constraint with "
             "s.Add(linear expression); set the objective with s.Maximize(expression) or s.Minimize(expression); solve with st = s.Solve() "
             "and compare st with pywraplp.Solver.OPTIMAL (or INFEASIBLE / UNBOUNDED); read the optimal value with s.Objective().Value().")
# CD (PREREG_CD.md, 2026-10-19): the content of SNIP as a description instead of code (matched-content test)
P_CPSAT = ("{q}\n\nWrite a complete Python 3 program that formulates this problem with Google OR-Tools CP-SAT (`from ortools.sat.python "
           "import cp_model`; scale any fractional coefficients to integers), solves it, and prints ONLY the optimal objective value." + TAIL)
P_TEXT = "{q}\n\nSolve the problem. Put the optimal objective value in \\boxed{{}} (or \\boxed{{No Best Solution}} if there is none)."



def _rows(path):
    """rows of a results file; skips a torn line (a NUL-filled line from an interrupted write on the NAS, 2026-10-18)"""
    out = []
    for l in (open(path, errors="replace") if os.path.exists(path) else []):
        try:
            out.append(json.loads(l))
        except ValueError:
            pass
    return out

MAMO = "/SSD/huggingface/datasets/MAMO"   # X7 (2026-10-19): held-out benchmark, MAMO EasyLP 652 + ComplexLP 211 (NLOPT_SET=mamo)


OPTMATH = "/SSD/lean_postech/storm/STORM/data/test.tir_prompt.OptMath.jsonl"


def problems(which=None):
    which = which or os.environ.get("NLOPT_SET", "x3")
    out = []
    if which in ("x3", "all"):
        for name in ("nl4opt", "industryor"):
            for k, r in enumerate(json.load(open(f"{RES}/{name}.json"))):
                out.append({"id": f"{name}-{k}", "src": name, "q": r["en_question"], "gold": str(r["en_answer"]).strip(),
                            "difficulty": r.get("difficulty", "NL4OPT")})
    if which == "optmath":   # held-out (PREREG_HO.md): OptMATH-Bench test problems as shipped with STORM's code (100), problem text only
        for k, l in enumerate(open(OPTMATH)):
            r = json.loads(l)
            out.append({"id": f"optmath-{k}", "src": "optmath", "q": r["prompt"].split("### Problem:\n", 1)[1].strip(),
                        "gold": str(r["gt_answer"]).strip(), "difficulty": "optmath"})
    if which in ("mamo", "all"):
        for name, fn in (("mamo_easy", "MAMO_EasyLP"), ("mamo_complex", "MAMO_ComplexLP")):
            for k, l in enumerate(l for l in open(f"{MAMO}/{fn}.json") if l.strip()):
                r = json.loads(l)
                out.append({"id": f"{name}-{k}", "src": name, "q": r["en_question"], "gold": str(r["en_answer"]).strip(), "difficulty": name})
    return out


def value_of(s):
    s = (s or "").strip()
    if not s:
        return None
    if "no best solution" in s.lower():
        return "NBS"
    m = re.findall(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", s.replace(",", ""))
    return float(m[-1]) if m else None


def correct(pred, gold):
    if pred is None:
        return False
    if gold.lower().startswith("no best"):
        return pred == "NBS"
    if pred == "NBS":
        return False
    g = float(gold)
    return abs(pred - g) <= max(1e-2, 1e-3 * abs(g))


def main():
    from llm import chat, last_block
    from sandbox import run_python
    tag, mode, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
    mt = int(sys.argv[sys.argv.index("--max_tokens") + 1]) if "--max_tokens" in sys.argv else 8192
    think = "--think" in sys.argv

    if mode in ("mips", "thinks"):
        os.environ["NLOPT_EX_SHORTEST"] = "1"
    EX = _verified_examples(os.environ.get("NLOPT_EX_TAG", tag)) if mode in ("mipv", "thinkv", "mips", "thinks") else None

    def one(p):
        sd = seed * 1000 + zlib.crc32(p["id"].encode()) % 997
        tmpl = {"mip": P_MIP, "mipf": P_MIP + SNIP, "cpsat": P_CPSAT, "text": P_TEXT, "think": P_MIP, "thinkf": P_MIP + SNIP,
                "mipa": P_MIP + AUTO.replace("{", "{{").replace("}", "}}"), "thinka": P_MIP + AUTO.replace("{", "{{").replace("}", "}}"),
                "mipv": P_MIP, "thinkv": P_MIP, "mips": P_MIP, "thinks": P_MIP, "free": P_FREE, "thinkfree": P_FREE, "mipt": P_MIP + SNIP_TEXT}[mode]
        q = tmpl.format(q=p["q"])
        if mode in ("mipv", "thinkv", "mips", "thinks"):   # automatic usage fact: a check-passing program of this model for a similar problem of the other benchmark
            ex = EX(p)
            if ex:
                q += "\n\nA program that runs with this library (written for a different problem):\n```python\n" + ex.strip() + "\n```"
        o = chat(q, think=think, max_tokens=mt, temperature=0.7, seed=sd)
        text = o["text"] or ""
        row = {"id": p["id"], "src": p["src"], "difficulty": p["difficulty"], "gold": p["gold"], "mode": mode,
               "out_tokens": o.get("out_tokens"), "finish": o.get("finish")}
        if mode == "text":
            b = re.findall(r"\\boxed\{([^{}]*)\}", text)
            pred = value_of(b[-1]) if b else None
            row.update(text=text[-1500:], pred=pred, status="ok" if b else "no_answer")
        else:
            code = last_block(text, ("python", "py", "python3"))
            r = run_python(code, "", timeout=60, mem_bytes=4 << 30,   # free modes may pick multi-threaded CP-SAT: CPU limit >> wall (H5 bug)
                           cpu_s=(3600 if mode in ("free", "thinkfree") else None)) if code else None
            out = (r.stdout if r and r.status == "ok" else "") or ""
            lines = [l for l in out.strip().splitlines() if l.strip()]
            pred = value_of(lines[-1]) if lines else None
            row.update(code=code, status=(r.status if r else "no_code"), stdout=out[-300:], err=((r.stderr or "")[-300:] if r else ""), pred=pred)
        row["correct"] = correct(row["pred"], p["gold"])
        return row

    path = f"{RES}/opt_{tag}_{mode}_s{seed}.jsonl"   # rows are flushed as they finish; a re-run resumes (2026-10-17)
    done = {r["id"] for r in _rows(path)}
    with ThreadPoolExecutor(48) as ex, open(path, "a") as f:
        for fu in as_completed([ex.submit(one, p) for p in problems() if p["id"] not in done]):
            f.write(json.dumps(fu.result()) + "\n"); f.flush()
    rows = [json.loads(l) for l in open(path)]
    by = {}
    for r in rows:
        by.setdefault(r["src"], []).append(r["correct"])
    print(tag, mode, seed, {k: f"{sum(v)}/{len(v)}" for k, v in by.items()}, f"tokens {sum(r['out_tokens'] or 0 for r in rows) / len(rows):.0f}", flush=True)


if __name__ == "__main__":
    main()
