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
  brute  OEIS only, no thinking: a deliberately slow program written straight from the definition, for comparing with `prog` on small n
  mem    Euler only, no thinking, no work shown: the answer at once (memorization control: old answers are public)
Grading: MathConstruct its own parse_and_check; Euler exact integer string; OEIS a(n) on the first 20 listed terms (4 s each, as the benchmark's most lenient limit), right only if all match.
usage: POC_BASE_URL=... python run_compute.py <set> <tag> <mode> <seed> [--max_tokens N] [--n K]
       -> results/x44/<set>_<tag>_<mode>_s<seed>.jsonl"""
import json, os, re, sys, threading, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import chat, last_block  # noqa: E402
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


def problems(s):
    if s == "mcon":
        return mcon_problems()
    return json.load(open(f"{DATA}/{ {'euler': 'euler_dev', 'eulert': 'euler_test', 'oeis': 'oeis'}[s] }.json"))


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
    euler, mcon = s.startswith("euler"), s == "mcon"

    def one(p):
        sd = seed * 1000 + zlib.crc32(p["id"].encode()) % 997
        if mcon:
            q = {"think": "{p}", "prog": MC_PROG, "progc": MC_PROGC}[mode].format(p=p["problem"])
        elif euler:
            q = {"think": EULER_THINK, "prog": EULER_PROG, "progc": EULER_PROGC, "mem": EULER_MEM}[mode].format(p=p["problem"])
        else:
            q = OEIS.format(name=p["name"], comments=p["comments"])
            q = OEIS_BRUTE.format(q=q) if mode == "brute" else q
        o = chat(q, think=mode == "think", max_tokens=mt, temperature=0.6 if mode == "think" else 0.7, seed=sd)
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
            else:
                code = last_block(text, ("python", "py", "python3"))
                r = run_python(code, "", timeout=PROG_S, mem_bytes=4 << 30) if code else None
                out = ((r.stdout if r and r.status == "ok" else "") or "").strip()
                row.update(code=code, status=(r.status if r else "no_code"), answer=out.splitlines()[-1] if out else "")
                if mode == "progc" and code:
                    row["checks"], row["check_status"] = run_checks(code)
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
    path = f"{RES}/{s}_{tag}_{mode}_s{seed}.jsonl"
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
