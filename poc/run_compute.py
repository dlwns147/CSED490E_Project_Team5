"""Idea 44 (docs/notes/IDEAS_COMPUTATION.md): math computation problems where a program does the real work, and a free check that tests
the answer against the problem itself. A pilot: it decides nothing; what survives is pre-registered.
Sets (poc/prep_compute.py -> $POC_DATA/compute/):
  euler  Project Euler (PECC dev sample of 120; old problems, answers public)
  eulert Project Euler 943-992 (MathArena, late 2025), held for the report
  oeis   integer sequences added to the OEIS after July 2024 (2411.04372, contemporary half): a program that prints a(n) for n on stdin
  mcon   MathConstruct (2502.10197, github.com/eth-sri/mathconstruct in $POC_DATA/mathconstruct_dl): construct an object; the benchmark's
         own checker grades it. One instance per problem (the first variation in the paper's results, else the original), its prompt verbatim
Modes:
  think  thinking on, then the answer (Euler: \\boxed{}; OEIS: the program, as the benchmark asks)
  prog   no thinking: one program (Euler: prints the answer; OEIS: prints a(n))
  progc  Euler, no thinking: a program with solve(...) and CHECKS, the small cases the statement itself gives with their values, copied
         from it; the harness runs solve on each check (free check: the problem setter's own numbers) and runs the program for the answer.
         MathConstruct, no thinking: construct() and verify(obj), the problem's stated conditions as code; the harness runs verify(construct())
  progc2 Euler: progc with each check naming the function it tests (the pilot's right programs failed CHECKS when the statement's example
         is about an intermediate quantity, not the one solve returns) and the stated value's provenance tested: a check counts only if its
         value appears in the statement (the pilot's other failures were values the model made up)
  thinkp Euler and MathConstruct: thinking on, then the quick program's prompt (a program we run): thinking with code, the strong
         baseline on problems that need computation (the pilot found plain thinking at 16k capped on most Euler problems)
  thinkpb Euler: thinkp with budget forcing (s1 2501.19393; llm.think_cuts): one think cut at each of --budgets (default 2000,4000,8000,14000),
         the program written after each cut; row["cuts"] holds every budget, the row itself the largest (pilot: thinkp at 16k capped
         without a program on half the easy problems, so the plain cap undersells thinking)
  brute  OEIS only, no thinking: a deliberately slow program written straight from the definition, for comparing with `prog` on small n
  brutef Euler, no thinking (SOL-1, 2026-11-21): only brute(n), the asked quantity at a small value n of the problem's main size parameter,
         plus ASKED (that parameter's asked value), MOD (asked modulus / 10**k for last digits / None) and CHECKS [(n, value)] copied from
         the statement; the harness evaluates brute(0..60) (5 s each, 45 s total) and the checks; poc/analyze_sol1.py fits a structure
         (linear recurrence, P-recursive, polynomial) to the values, checks it on held-out values and extrapolates to ASKED
  mem    Euler only, no thinking, no work shown: the answer at once (memorization control: old answers are public)
Grading: MathConstruct its own parse_and_check; Euler exact integer string; OEIS a(n) on the first 20 listed terms (4 s each, as the benchmark's most lenient limit), right only if all match.
usage: POC_BASE_URL=... python run_compute.py <set> <tag> <mode> <seed> [--max_tokens N] [--n K] [--budgets B1,B2,..]
       python run_compute.py mcon <tag> <mode> <seed> --regrade   (grade stored program output again)
       -> results/x44/<set>_<tag>_<mode>_s<seed>.jsonl"""
import json, os, re, sys, threading, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import chat, last_block, think_cuts  # noqa: E402
from sandbox import run_python as _run_python  # noqa: E402

_SEM = threading.Semaphore(int(os.environ.get("X44_PAR", 4)))   # runs are timed by the wall clock: no more at once than the job's CPUs


def run_python(*a, **k):
    with _SEM:
        return _run_python(*a, **k)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results", "x44")
DATA = os.path.join(os.environ.get("POC_DATA", os.path.join(os.path.dirname(ROOT), "nlp_data")), "compute")
NTERMS, TERM_S, PROG_S = 20, 4, 60

EULER_THINK = "{p}\n\nSolve the problem. You may not run code. Put the final answer (an integer or the exact form asked for) in \\boxed{{}}."
EULER_PROG = ("{p}\n\nDo not solve this by hand. Write a complete, efficient Python 3 program (standard library, sympy, numpy allowed) that computes "
              "the answer and prints ONLY the final answer on the last line. It must finish within one minute. Give the program in a single ```python code block.")
EULER_PROGC = ("{p}\n\nDo not solve this by hand. Write a complete, efficient Python 3 program (standard library, sympy, numpy allowed) with:\n"
               "1. a function `solve(...)` that computes the quantity asked for, with the problem's parameters as arguments;\n"
               "2. a list `CHECKS = [((arguments...), value), ...]` holding every small case whose value the problem statement itself gives, "
               "copied exactly from the statement (an empty list if it gives none);\n"
               "3. under `if __name__ == \"__main__\":`, a call of `solve` with the parameters the problem asks about, printing ONLY that answer.\n"
               "It must finish within one minute. Give the program in a single ```python code block.")
EULER_PROGC2 = ("{p}\n\nDo not solve this by hand. Write a complete, efficient Python 3 program (standard library, sympy, numpy allowed) with:\n"
                "1. a function `solve(...)` that computes the quantity asked for, with the problem's parameters as arguments, and a separate function "
                "for every other quantity the statement gives an example of;\n"
                "2. a list `CHECKS = [(\"function_name\", (arguments...), value), ...]` holding every small case whose value the problem statement "
                "itself gives, each with the function that computes that quantity, the value copied exactly from the statement (an empty list "
                "if it gives none; never a value you computed or remember);\n"
                "3. under `if __name__ == \"__main__\":`, a call of `solve` with the parameters the problem asks about, printing ONLY that answer.\n"
                "It must finish within one minute. Give the program in a single ```python code block.")
EULER_BRUTEF = ("{p}\n\nDo not try to solve the problem at the size it asks about. Write a Python 3 program (standard library, sympy, numpy "
                "allowed) that defines:\n"
                "1. `brute(n)`: the exact quantity the problem asks for when its main size parameter (the one that is large in the question) "
                "equals n, every other parameter as stated, computed by the simplest direct brute force from the definitions (it only needs to "
                "work for small n). Return the exact value: no modulus, no last-digit truncation, no rounding;\n"
                "2. `ASKED`: the value of that parameter in the question (an integer);\n"
                "3. `MOD`: the modulus if the answer is asked modulo m, 10**k if its last k digits are asked, else None;\n"
                "4. `CHECKS = [(n, value), ...]`: every small case whose value the statement itself gives for this quantity, copied exactly "
                "(an empty list if it gives none).\n"
                "No code may run on import. Give the program in a single ```python code block.")
BRUTEF_DRIVER = """

import json as _j, signal as _s, time as _t
class _TO(Exception):
    pass
def _h(*_):
    raise _TO()
_s.signal(_s.SIGALRM, _h)
def _ev(n, lim):
    _s.setitimer(_s.ITIMER_REAL, lim)
    try:
        v = brute(n)
        return repr(v)
    except _TO:
        return 'TIMEOUT'
    except Exception as e:
        return 'error ' + type(e).__name__
    finally:
        _s.setitimer(_s.ITIMER_REAL, 0)
_t0 = _t.time(); _vals = []
for _n in range(61):
    if _t.time() - _t0 > 45:
        break
    _v = _ev(_n, 5.0)
    _vals.append(_v)
    if _v == 'TIMEOUT':
        break
_ck = []
try:
    for _a, _b in CHECKS:
        _ck.append([repr(_a), repr(_b), _vals[_a] if isinstance(_a, int) and 0 <= _a < len(_vals) else _ev(_a, 10.0)])
except Exception as e:
    _ck = 'error ' + type(e).__name__
try:
    _meta = [repr(ASKED), repr(MOD)]
except Exception as e:
    _meta = ['error', 'error']
print('__BRUTEF__' + _j.dumps({'vals': _vals, 'checks': _ck, 'asked': _meta[0], 'mod': _meta[1]}))
"""
EULER_MEM = "{p}\n\nGive only the final answer in \\boxed{{}}, with no working."
OEIS = ("Write a python code that takes a number n as input from stdin, outputs a single element of a sequence as a string to stdout. Just output "
        "the n-th element in the sequence, not the whole sequence or anything other than the single sequence element. You will be graded by my "
        "running your code and comparing the results with a look-up table. If you use a look-up table for your code, you will not only fail the "
        "test. Hardcoding values that can be computed without hardcoding is considered to be using a look-up table. Use only the standard python "
        "library. No packages will be installed with pip or conda. Output your final code at the end of your response inside triple backticks like:\n"
        "```\n#your code goes here\n```\nThe last part of your response that is inside triple backticks will be used as your response for the "
        "purposes of the test. The code will be stopped after a short period of time, so make it efficient if needed.\n\n"
        "Here is some information on the sequence:\n```\nName: {name}\nComments: {comments}\n```")   # 2411.04372's prompt, verbatim
OEIS_BRUTE = ("{q}\n\nThis time ignore speed: write the simplest, most direct program you can, computed straight from the definition by brute "
              "force (it only needs to work for the first few n). Do not use any formula or shortcut that is not in the definition itself.")


MC = os.path.join(os.path.dirname(DATA), "mathconstruct_dl", "repo")
MC_PROG = ("{p}\n\nDo not construct this by hand. Write a complete Python 3 program (standard library, sympy, numpy allowed) that builds or "
           "searches for the required object and prints ONLY the final answer in exactly the format above, including \\boxed{{...}}. It must "
           "finish within one minute. Give the program in a single ```python code block.")
MC_PROGC = ("{p}\n\nDo not construct this by hand. Write a complete Python 3 program (standard library, sympy, numpy allowed) with:\n"
            "1. a function `construct()` that builds or searches for the required object and returns it as Python data;\n"
            "2. a function `verify(obj)` that checks every condition the problem states and returns True only if all of them hold;\n"
            "3. under `if __name__ == \"__main__\":`, `x = construct()` and a print of ONLY the final answer for x in exactly the format above, "
            "including \\boxed{{...}}.\nIt must finish within one minute. Give the program in a single ```python code block.")
_MC = {}


def mcon_problems():
    """one instance per MathConstruct problem: the first variation in the paper's results, else the original parameters"""
    sys.path[:0] = [os.path.join(MC, "src"), os.path.join(os.path.dirname(MC), "pylib")]   # pylib: loguru, antlr4 4.11 (pure Python)
    from loguru import logger
    logger.remove()
    from math_construct.problems import get_all_problem_classes
    var = {}
    for m in json.load(open(f"{MC}/data/results.json"))[0]["model_results"].values():
        for r in m["detailed_results"]:
            var.setdefault(r["problem_name"], r["variation_parameters"])
    out = []
    for cls in get_all_problem_classes():
        name = cls.config.name
        try:
            obj = cls(**var[name]) if name in var else cls.get_original()
        except Exception:
            obj = cls.get_original()
        _MC[name] = obj
        out.append({"id": name, "problem": str(obj) + "\n\nFormat your reply as follows:\n" + obj.get_formatting()})
    return out


def mconf_problems():
    """PREREG_DIFF MC-R-F: MathConstruct instances with fresh parameters (side/construct.py build; $POC_DATA/construct/ids_mcfresh.txt,
    137 instances of 70 held-out problems), graded by the benchmark's own checker for those parameters"""
    import ast
    mcon_problems()   # loads the package path and the problem classes
    from math_construct.problems import get_all_problem_classes
    C = {cls.config.name: cls for cls in get_all_problem_classes()}
    base = os.path.join(os.path.dirname(DATA), "construct")
    inst = {json.loads(l)["id"]: json.loads(l) for l in open(f"{base}/instances.jsonl")}
    out = []
    for i in [l.strip() for l in open(f"{base}/ids_mcfresh.txt") if l.strip()]:
        x = inst[i]
        try:
            obj = C[x["name"]](**(x["params"] if isinstance(x["params"], dict) else ast.literal_eval(x["params"])))
        except Exception:
            continue
        _MC[i] = obj
        out.append({"id": i, "problem": str(obj) + "\n\nFormat your reply as follows:\n" + obj.get_formatting()})
    return out


def problems(s):
    if s == "mcon":
        return mcon_problems()
    if s == "mconf":
        return mconf_problems()
    return json.load(open(f"{DATA}/{ {'euler': 'euler_dev', 'eulert': 'euler_test', 'oeis': 'oeis', 'oeisf': 'oeis_fresh'}[s] }.json"))


def _rows(path):
    out = []
    for l in (open(path, errors="replace") if os.path.exists(path) else []):
        try:
            out.append(json.loads(l))
        except ValueError:
            pass
    return out


def norm(s):
    return re.sub(r"[\s,]", "", str(s or "")).rstrip(".").lstrip("+")


def boxed(t):
    m = re.findall(r"\\boxed\{((?:[^{}]|\{[^{}]*\})*)\}", t or "")
    return m[-1].strip() if m else ""


def run_seq(code, offset, terms, k=NTERMS):
    """a(n) for the first k listed terms -> (all right, number right, outputs)"""
    outs = []
    for i, t in enumerate(terms[:k]):
        r = run_python(code, str(offset + i), timeout=TERM_S, mem_bytes=2 << 30)
        outs.append(r.stdout.strip() if r.status == "ok" else r.status)
    right = sum(o == t.strip() for o, t in zip(outs, terms))
    return right == len(outs) and len(outs) > 0, right, outs


def stated(v, problem):
    """progc2 provenance: the check's value, as digits (or a decimal), appears in the statement once LaTeX spacing and digit grouping are removed"""
    t = re.sub(r"(?<=\d)(\\[,;! ]|\{,\}|,(?=\d{3}))(?=\d)", "", problem)
    v = str(v).strip().strip("'\"")
    return bool(re.fullmatch(r"-?\d+(\.\d+)?", v)) and re.search(r"(?<![\d.])" + re.escape(v) + r"(?![\d]|\.\d)", t) is not None


def run_checks2(code, problem):
    """Euler progc2: run each named function on its check -> list of (name, args, stated, got, equal, stated-in-statement)"""
    runner = ("\n\nimport json as _j\n_out = []\nfor _c in CHECKS:\n    try:\n        _f, _a, _v = _c\n        _g = globals()[_f](*(_a if isinstance(_a, (tuple, list)) else (_a,)))\n"
              "    except Exception as _e:\n        _f, _a, _v, _g = str(_c[0]) if _c else '', _c[1:2], _c[-1] if _c else '', 'error ' + type(_e).__name__\n"
              "    _out.append([str(_f), repr(_a), repr(_v), repr(_g), str(_g).strip() == str(_v).strip()])\n"
              "print('__CHECKS__' + _j.dumps(_out))\n")
    r = run_python("__name__ = '__check__'\n" + code + runner, "", timeout=PROG_S, mem_bytes=4 << 30)
    m = re.search(r"__CHECKS__(.*)", r.stdout or "")
    if r.status != "ok" or not m:
        return None, r.status
    return [c + [stated(eval_lit(c[2]), problem)] for c in json.loads(m.group(1))], "ok"


def eval_lit(x):
    import ast
    try:
        return ast.literal_eval(x)
    except Exception:
        return x


def run_checks(code):
    """Euler progc: run solve on the program's CHECKS (with its main block switched off) -> list of (args, stated, got, equal)"""
    runner = ("\n\nimport json as _j\n_out = []\nfor _a, _v in CHECKS:\n    try:\n        _g = solve(*(_a if isinstance(_a, (tuple, list)) else (_a,)))\n"
              "    except Exception as _e:\n        _g = 'error ' + type(_e).__name__\n    _out.append([repr(_a), repr(_v), repr(_g), str(_g).strip() == str(_v).strip()])\n"
              "print('__CHECKS__' + _j.dumps(_out))\n")
    r = run_python("__name__ = '__check__'\n" + code + runner, "", timeout=PROG_S, mem_bytes=4 << 30)
    m = re.search(r"__CHECKS__(.*)", r.stdout or "")
    if r.status != "ok" or not m:
        return None, r.status
    return json.loads(m.group(1)), "ok"


def main():
    s, tag, mode, seed = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
    mt = int(sys.argv[sys.argv.index("--max_tokens") + 1]) if "--max_tokens" in sys.argv else 4096
    P = problems(s)
    if "--n" in sys.argv:
        P = P[:int(sys.argv[sys.argv.index("--n") + 1])]
    euler, mcon = s.startswith("euler"), s in ("mcon", "mconf")
    BUD = [int(x) for x in sys.argv[sys.argv.index("--budgets") + 1].split(",")] if "--budgets" in sys.argv else [2000, 4000, 8000, 14000]
    path = f"{RES}/{s}_{tag}_{mode}_s{seed}.jsonl"
    if "--regrade" in sys.argv and mcon and mode != "think":   # grade stored program output again (2026-11-13: backspace fix); no model calls
        rows = _rows(path)
        for r in rows:
            ans = (r.get("stdout") or "").replace("\x08", "\\b")
            try:
                _, ok, detail = _MC[r["id"]].parse_and_check([{"role": "assistant", "content": ans}]) if ans else (None, False, "no answer")
            except Exception as e:
                ok, detail = False, f"grader error {type(e).__name__}"
            r.update(stdout=ans, correct=bool(ok), detail=str(detail)[:300])
        with open(path, "w") as f:
            f.writelines(json.dumps(r) + "\n" for r in rows)
        print(s, tag, mode, seed, "regraded", f"{sum(r['correct'] for r in rows)}/{len(rows)}", flush=True)
        return

    def one(p):
        sd = seed * 1000 + zlib.crc32(p["id"].encode()) % 997
        if mcon:
            q = {"think": "{p}", "prog": MC_PROG, "thinkp": MC_PROG, "progc": MC_PROGC}[mode].format(p=p["problem"])
        elif euler:
            q = {"think": EULER_THINK, "prog": EULER_PROG, "thinkp": EULER_PROG, "thinkpb": EULER_PROG, "progc": EULER_PROGC, "progc2": EULER_PROGC2, "mem": EULER_MEM,
                 "brutef": EULER_BRUTEF, "thinkpc": EULER_PROGC}[mode].format(p=p["problem"])
        else:
            q = OEIS.format(name=p["name"], comments=p["comments"])
            q = OEIS_BRUTE.format(q=q) if mode == "brute" else q
        th = mode in ("think", "thinkp", "thinkpc")   # thinkpc (PREREG_DIFF PE2): thinking, then the progc program (solve + CHECKS)
        if mode == "thinkpb":
            C = think_cuts(EULER_PROG.format(p=p["problem"]), BUD, seed=sd, temperature=0.6)
            cuts = {}
            for b, o in C.items():
                code = last_block(o["text"] or "", ("python", "py", "python3"))
                r = run_python(code, "", timeout=PROG_S, mem_bytes=4 << 30) if code else None
                out = ((r.stdout if r and r.status == "ok" else "") or "").strip()
                a = out.splitlines()[-1] if out else ""
                cuts[b] = {"out_tokens": o["out_tokens"], "think_tokens": o["think_tokens"], "cut": o["cut"], "finish": o["finish"],
                           "status": (r.status if r else "no_code"), "answer": a, "correct": bool(a) and norm(a) == norm(p["answer"]), "code": code}
            top = cuts[max(cuts)]
            return {"id": p["id"], "mode": mode, "out_tokens": top["out_tokens"], "finish": top["finish"], "gold": p["answer"],
                    "difficulty": p.get("difficulty"), "answer": top["answer"], "status": top["status"], "correct": top["correct"],
                    "cuts": {str(b): c for b, c in cuts.items()}}
        o = chat(q, think=th, max_tokens=mt, temperature=0.6 if th else 0.7, seed=sd)
        text = o["text"] or ""
        row = {"id": p["id"], "mode": mode, "out_tokens": o.get("out_tokens"), "finish": o.get("finish")}
        if mcon:
            obj = _MC[p["id"]]
            if mode == "think":
                ans = text
                row["text"] = text[-2000:]
            else:
                code = last_block(text, ("python", "py", "python3"))
                r = run_python(code, "", timeout=PROG_S, mem_bytes=4 << 30) if code else None
                ans = ((r.stdout if r and r.status == "ok" else "") or "").strip()
                ans = ans.replace("\x08", "\\b")   # print("\boxed{..}") in a non-raw string prints a backspace + "oxed{..}"; restore it
                row.update(code=code, status=(r.status if r else "no_code"), stdout=ans[-2000:])
                if mode == "progc" and code:
                    rv = run_python("__name__ = '__check__'\n" + code + "\n\nprint('__VERIFY__', bool(verify(construct())))\n", "",
                                    timeout=PROG_S, mem_bytes=4 << 30)
                    m = re.search(r"__VERIFY__ (True|False)", rv.stdout or "")
                    row["verify"] = (m.group(1) == "True") if (rv.status == "ok" and m) else None
                    row["check_status"] = rv.status
            try:
                _, ok, detail = obj.parse_and_check([{"role": "assistant", "content": ans}]) if ans else (None, False, "no answer")   # it takes messages
            except Exception as e:
                ok, detail = False, f"grader error {type(e).__name__}"
            row.update(correct=bool(ok), detail=str(detail)[:300])
        elif euler:
            row.update(gold=p["answer"], difficulty=p.get("difficulty"))
            if mode in ("think", "mem"):
                row.update(answer=boxed(text), text=text[-2000:])
            elif mode == "brutef":
                code = last_block(text, ("python", "py", "python3"))
                r = run_python("__name__ = '__brutef__'\n" + code + BRUTEF_DRIVER, "", timeout=PROG_S, mem_bytes=4 << 30) if code else None
                m = re.search(r"__BRUTEF__(.*)", (r.stdout if r else "") or "")
                row.update(code=code, status=(r.status if r else "no_code"), answer="", **(json.loads(m.group(1)) if m else {}))
            else:
                code = last_block(text, ("python", "py", "python3"))
                r = run_python(code, "", timeout=PROG_S, mem_bytes=4 << 30) if code else None
                out = ((r.stdout if r and r.status == "ok" else "") or "").strip()
                row.update(code=code, status=(r.status if r else "no_code"), answer=out.splitlines()[-1] if out else "")
                if mode in ("progc", "thinkpc") and code:
                    row["checks"], row["check_status"] = run_checks(code)
                if mode == "progc2" and code:
                    row["checks"], row["check_status"] = run_checks2(code, p["problem"])
            row["correct"] = bool(row["answer"]) and norm(row["answer"]) == norm(p["answer"])
        else:
            row.update(level=p["level"])
            code = last_block(text, ("python", "py", "python3", ""))
            if code:
                ok, right, outs = run_seq(code, p["offset"], p["terms"], k=8 if mode == "brute" else NTERMS)
                row.update(code=code, correct=ok, right=right, outs=outs)
            else:
                row.update(code=None, correct=False, right=0, outs=[])
        return row

    os.makedirs(RES, exist_ok=True)
    done = {r["id"] for r in _rows(path)}
    lock = threading.Lock()
    with ThreadPoolExecutor(32) as ex, open(path, "a") as f:
        for fu in as_completed([ex.submit(one, p) for p in P if p["id"] not in done]):
            r = fu.result()
            with lock:
                f.write(json.dumps(r) + "\n"); f.flush()
    rows = _rows(path)
    print(s, tag, mode, seed, f"{sum(r['correct'] for r in rows)}/{len(rows)}", f"tokens {sum(r['out_tokens'] or 0 for r in rows) / max(1, len(rows)):.0f}", flush=True)


if __name__ == "__main__":
    main()
