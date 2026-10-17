"""X3 (docs/prereg/PREREG_X3.md): optimization word problems -> models (NL4OPT 245, IndustryOR 100). The answer is the optimal objective
value (or "No Best Solution" when infeasible / unbounded).
modes: mip   = Python program with OR-Tools pywraplp (SCIP), prints the optimal objective value;
       mipf  = mip + a 6-line exact pywraplp usage snippet (the API fact);
       cpsat = Python program with OR-Tools CP-SAT (integer model), prints the optimal objective value;
       text  = reason in text, final value in \\boxed{};
       think = mip with thinking on (Qwen) / the caller's higher reasoning effort (gpt-oss);
       thinkf = think + the snippet of mipf (X6: does the API fact make thinking pay?).
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
P_CPSAT = ("{q}\n\nWrite a complete Python 3 program that formulates this problem with Google OR-Tools CP-SAT (`from ortools.sat.python "
           "import cp_model`; scale any fractional coefficients to integers), solves it, and prints ONLY the optimal objective value." + TAIL)
P_TEXT = "{q}\n\nSolve the problem. Put the optimal objective value in \\boxed{{}} (or \\boxed{{No Best Solution}} if there is none)."


def problems():
    out = []
    for name in ("nl4opt", "industryor"):
        for k, r in enumerate(json.load(open(f"{RES}/{name}.json"))):
            out.append({"id": f"{name}-{k}", "src": name, "q": r["en_question"], "gold": str(r["en_answer"]).strip(),
                        "difficulty": r.get("difficulty", "NL4OPT")})
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

    def one(p):
        sd = seed * 1000 + zlib.crc32(p["id"].encode()) % 997
        tmpl = {"mip": P_MIP, "mipf": P_MIP + SNIP, "cpsat": P_CPSAT, "text": P_TEXT, "think": P_MIP, "thinkf": P_MIP + SNIP}[mode]
        o = chat(tmpl.format(q=p["q"]), think=think, max_tokens=mt, temperature=0.7, seed=sd)
        text = o["text"] or ""
        row = {"id": p["id"], "src": p["src"], "difficulty": p["difficulty"], "gold": p["gold"], "mode": mode,
               "out_tokens": o.get("out_tokens"), "finish": o.get("finish")}
        if mode == "text":
            b = re.findall(r"\\boxed\{([^{}]*)\}", text)
            pred = value_of(b[-1]) if b else None
            row.update(text=text[-1500:], pred=pred, status="ok" if b else "no_answer")
        else:
            code = last_block(text, ("python", "py", "python3"))
            r = run_python(code, "", timeout=60, mem_bytes=4 << 30) if code else None
            out = (r.stdout if r and r.status == "ok" else "") or ""
            lines = [l for l in out.strip().splitlines() if l.strip()]
            pred = value_of(lines[-1]) if lines else None
            row.update(code=code, status=(r.status if r else "no_code"), stdout=out[-300:], err=((r.stderr or "")[-300:] if r else ""), pred=pred)
        row["correct"] = correct(row["pred"], p["gold"])
        return row

    path = f"{RES}/opt_{tag}_{mode}_s{seed}.jsonl"   # rows are flushed as they finish; a re-run resumes (2026-10-17)
    done = {json.loads(l)["id"] for l in open(path)} if os.path.exists(path) else set()
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
