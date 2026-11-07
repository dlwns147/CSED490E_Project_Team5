"""X1 (docs/prereg/PREREG_X1.md): short-answer competition math (MATH-500 + AIME 2024 + AIME 2025 = 560 problems).
Modes: text  = reason in text, final answer in \\boxed{};
       prog  = write a Python program (sympy allowed) that computes and prints the answer; we run it (30 s);
       think = the expensive mode (Qwen: thinking on; gpt-oss: POC_REASONING_EFFORT set by the caller), final answer in \\boxed{}.
Grading: math_verify against the gold answer; a program's printed answer is also tried through sympy -> LaTeX.
usage: POC_BASE_URL=... python run_math.py <tag> <mode> <seed> [--max_tokens N] [--think]
       -> results/x1/math_<tag>_<mode>_s<seed>.jsonl
Note: rewritten by the experiment session 2026-10-16 18:00 (it overwrote the writing session's prepared version by mistake)."""
import json, os, re, sys, zlib
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import chat, last_block  # noqa: E402
from sandbox import run_python  # noqa: E402

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "x1")



def _rows(path):
    """rows of a results file; skips a torn line (a NUL-filled line from an interrupted write on the NAS, 2026-10-18)"""
    out = []
    for l in (open(path, errors="replace") if os.path.exists(path) else []):
        try:
            out.append(json.loads(l))
        except ValueError:
            pass
    return out

def problems():   # results/x1/problems.json, prepared by the writing session for X1 (MATH-500, AIME 2024, AIME 2025)
    D = json.load(open(f"{RES}/problems.json"))
    return [{**r, "id": str(r["id"]), "src": src, "answer": str(r["answer"])} for src in ("math500", "aime24", "aime25") for r in D[src]]


TEXT = "{p}\n\nSolve the problem. Put your final answer in \\boxed{{}}."
PROG = ("{p}\n\nDo not solve this by hand. Write a complete Python 3 program that computes the answer (you may use sympy, fractions, "
        "itertools, math) and prints ONLY the final answer, in exact form (an integer, a fraction, or a sympy expression such as "
        "sqrt(2)/2), on the last line. Give the program in a single ```python code block.")


# computation ideas (docs/notes/IDEAS_COMPUTATION.md): program arms with another instruction, graded as `prog`
ARMS = {
    "extrap": ("{p}\n\nDo not solve this by hand. Write a complete Python 3 program (sympy, fractions, itertools, math allowed). Where the problem has a large parameter, count or "
               "compute by brute force on small values of it, find the exact pattern from those values (a recurrence, a polynomial, a period), and extend it to the value asked. "
               "Print ONLY the final answer, in exact form, on the last line. Give the program in a single ```python code block."),
    "cert": ("{p}\n\nDo not solve this by hand. Write a complete Python 3 program (sympy, fractions, itertools, math allowed) that computes the answer, and then checks it by a different "
             "route: substitute it back into the conditions of the problem, or test the formula against direct enumeration on a smaller case. If the check passes, print ONLY the final "
             "answer, in exact form, on the last line. If it fails, print ONLY the word FAIL. Give the program in a single ```python code block."),
    "numid": ("{p}\n\nDo not solve this by hand. Write a complete Python 3 program that computes the answer numerically to 60 digits with mpmath, then recovers its exact form with "
              "mpmath.identify, sympy.nsimplify or a continued fraction, and prints ONLY that exact form on the last line. Give the program in a single ```python code block."),
}
VFY = "{p}\n\nA student's answer is {a}. Check it, by a different route from the obvious one if you can. End with \\boxed{{yes}} if it is right and \\boxed{{no}} if it is wrong."


# idea 13: Python while thinking, by prompt alone. The server stops at the end of a code block, we run it and put the output in the reasoning.
TIR_NOTE = ("While you think you can run Python (sympy, fractions, itertools, math): write a ```python block that prints what you need, and its output "
            "appears right after it. Each block runs alone, with no memory of earlier blocks.")
TIR_HINT = ("I can run Python here. For any step that is a calculation, an enumeration or a check, I should write a short ```python block and read the ```output "
            "after it, instead of working it out by hand.\n\n")


def tir(q, sd, mt, calls_max=20):
    """a think with code runs inside it: returns the llm.chat fields, with the runs and the seconds they took"""
    from llm import client
    import time
    head = f"<|im_start|>user\n{q}\n\n{TIR_NOTE}<|im_end|>\n<|im_start|>assistant\n<think>\n{TIR_HINT}"
    gen, used, runs, secs, errs, finish = "", 0, 0, 0.0, 0, None
    while used < mt:
        c_ = client.completions.create(model="local", prompt=head + gen, temperature=0.7, top_p=0.95, max_tokens=mt - used, seed=sd + runs,
                                       stop=["\n```\n"] if runs < calls_max else None)
        c = c_.choices[0]
        gen += c.text
        used += c_.usage.completion_tokens
        finish = c.finish_reason
        if finish != "stop" or not getattr(c, "stop_reason", None):
            break
        gen += "\n```\n"
        tail = gen[:-5].rsplit("```", 1)
        if "</think>" in gen or len(tail) < 2 or not tail[1].startswith(("python", "py\n")):
            continue
        t0 = time.time()
        r = run_python(tail[1].split("\n", 1)[-1], "", timeout=20, mem_bytes=2 << 30)
        secs += time.time() - t0
        runs += 1
        errs += r.status != "ok"
        out = (r.stdout if r.status == "ok" else (r.status + " " + (getattr(r, "stderr", "") or "")[-300:])) or "(nothing printed)"
        gen += f"```output\n{out[:1000]}\n```\n"
    text = gen.split("</think>")[-1] if "</think>" in gen else ""
    return {"text": text, "finish": finish, "out_tokens": used, "think_text": gen, "runs": runs, "run_secs": round(secs, 1), "run_errors": errs}


def to_candidates(s):
    """the printed answer as strings math_verify can parse: raw, and via sympy LaTeX"""
    s = (s or "").strip().splitlines()[-1].strip() if (s or "").strip() else ""
    if not s:
        return []
    c = [f"${s}$"]
    try:
        import sympy
        lx = sympy.latex(sympy.sympify(s, convert_xor=True))
        c.append(f"${lx}$")
        if re.search(r"\d i\b", lx):   # sympy prints 6 + 9*I as "6 + 9 i", which math_verify does not equate with "6+9i" (2026-10-17)
            c.append("$" + re.sub(r"(\d) i\b", r"\1i", lx) + "$")
    except Exception:
        pass
    return c


def same(a_cands, b_cands):
    from math_verify import parse, verify
    for a in a_cands:
        for b in b_cands:
            try:
                if verify(parse(a), parse(b)):
                    return True
            except Exception:
                pass
    return False


def _grade(r):
    """runs in a worker process's main thread, where math_verify's timeouts work"""
    from math_verify import parse
    if r["mode"] == "prog" or r["mode"] in ARMS:
        r["cands"] = to_candidates(r.get("stdout"))
    elif r["mode"] == "vfy":
        v = re.findall(r"boxed\{\s*(?:\\text\{)?\s*(yes|no)", r.get("text") or "", re.I)
        r["verdict"] = v[-1].lower() if v else None
        r["correct"] = r["verdict"] == ("yes" if r["cand_right"] else "no")
        return r
    else:
        try:
            ext = parse(r.get("text") or "")
            ans = str(ext[1]) if len(ext) > 1 else ""
        except Exception:
            ans = ""
        r["boxed"], r["cands"] = ans, ([f"${ans}$"] if ans else [])
    r["correct"] = same([f"${r['gold']}$"], r["cands"]) if r["cands"] else False
    return r


def regrade(path):
    import multiprocessing as mp
    rows = [json.loads(l) for l in open(path)]
    with mp.get_context("fork").Pool(16) as pool:
        rows = pool.map(_grade, rows, chunksize=8)
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return rows


def main():
    tag, mode, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
    mt = int(sys.argv[sys.argv.index("--max_tokens") + 1]) if "--max_tokens" in sys.argv else 8192
    think = "--think" in sys.argv
    P = problems()
    if os.environ.get("X1_HARD"):   # AIME and MATH level 5 only
        P = [p for p in P if p["src"] != "math500" or str(p["level"]) == "5"]

    cand = {r["id"]: r for r in _rows(os.environ["X1_VFY"]) if r.get("boxed")} if mode == "vfy" else {}

    def one(p):
        sd = seed * 1000 + zlib.crc32(p["id"].encode()) % 997
        q = (ARMS[mode] if mode in ARMS else PROG if mode == "prog" else TEXT).format(p=p["problem"])
        if mode == "vfy":   # idea 8: a capped think on the quick text answer of X1_VFY (a results file of the same seed)
            if p["id"] not in cand:
                return None
            q = VFY.format(p=p["problem"], a=cand[p["id"]]["boxed"])
        o = tir(q, sd, mt) if mode == "tir" else chat(q, think=think, max_tokens=mt, temperature=0.7, seed=sd)
        text = o["text"] or ""
        row = {"id": p["id"], "src": p["src"], "level": p["level"], "subject": p["subject"], "gold": p["answer"], "mode": mode,
               "out_tokens": o.get("out_tokens"), "finish": o.get("finish")}
        if mode == "prog" or mode in ARMS:
            code = last_block(text, ("python", "py", "python3"))
            r = run_python(code, "", timeout=30, mem_bytes=2 << 30) if code else None
            out = (r.stdout if r and r.status == "ok" else "") or ""
            row.update(code=code, status=(r.status if r else "no_code"), stdout=out[-500:], cands=to_candidates(out))
        else:
            row.update(text=text[-3000:])
            if mode == "vfy":
                row.update(cand=cand[p["id"]]["boxed"], cand_right=cand[p["id"]]["correct"])
            if "think_text" in o:
                row.update(think_text=o["think_text"])
            if mode == "tir":
                row.update(runs=o["runs"], run_secs=o["run_secs"], run_errors=o["run_errors"])
        return row   # graded afterwards in worker processes: math_verify's signal-based timeout fails in threads (all-0 bug, 18:09)

    import threading
    from concurrent.futures import as_completed
    path = f"{RES}/math_{tag}_{mode}_s{seed}.jsonl"
    done = {r["id"] for r in _rows(path)}   # resume after a crash (2026-10-17)
    todo = [p for p in P if p["id"] not in done]
    lock = threading.Lock()
    with ThreadPoolExecutor(48) as ex, open(path, "a") as f:
        for fu in as_completed([ex.submit(one, p) for p in todo]):
            r = fu.result()
            if r is None:
                continue
            with lock:
                f.write(json.dumps(r) + "\n"); f.flush()
    rows = regrade(path)
    by = {}
    for r in rows:
        by.setdefault(r["src"], []).append(r["correct"])
    print(tag, mode, seed, {k: f"{sum(v)}/{len(v)}" for k, v in by.items()},
          f"tokens {sum(r['out_tokens'] or 0 for r in rows) / len(rows):.0f}", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "--regrade":
        for p_ in sys.argv[2:]:
            rr = regrade(p_); print(p_, sum(r["correct"] for r in rr), "/", len(rr), flush=True)
    else:
        main()
