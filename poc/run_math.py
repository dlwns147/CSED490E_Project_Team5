"""X1 (docs/prereg/PREREG_X1.md): short-answer competition math (MATH-500 + AIME 2024 + AIME 2025 = 560 problems).
Modes: text  = reason in text, final answer in \\boxed{};
       prog  = write a Python program (sympy allowed) that computes and prints the answer; we run it (30 s);
       think = the expensive mode (Qwen: thinking on; gpt-oss: POC_REASONING_EFFORT set by the caller), final answer in \\boxed{}.
Grading: math_verify against the gold answer; a program's printed answer is also tried through sympy -> LaTeX.
usage: POC_BASE_URL=... python run_math.py <tag> <mode> <seed> [--max_tokens N] [--think]
       -> results/x1/math_<tag>_<mode>_s<seed>.jsonl
Note: rewritten by the experiment session 2026-10-16 18:00 (it overwrote the writing session's prepared version by mistake)."""
import json, os, sys, zlib
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import chat, last_block  # noqa: E402
from sandbox import run_python  # noqa: E402

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "x1")


def problems():   # results/x1/problems.json, prepared by the writing session for X1 (MATH-500, AIME 2024, AIME 2025)
    D = json.load(open(f"{RES}/problems.json"))
    return [{**r, "id": str(r["id"]), "src": src, "answer": str(r["answer"])} for src in ("math500", "aime24", "aime25") for r in D[src]]


TEXT = "{p}\n\nSolve the problem. Put your final answer in \\boxed{{}}."
PROG = ("{p}\n\nDo not solve this by hand. Write a complete Python 3 program that computes the answer (you may use sympy, fractions, "
        "itertools, math) and prints ONLY the final answer, in exact form (an integer, a fraction, or a sympy expression such as "
        "sqrt(2)/2), on the last line. Give the program in a single ```python code block.")


def to_candidates(s):
    """the printed answer as strings math_verify can parse: raw, and via sympy LaTeX"""
    s = (s or "").strip().splitlines()[-1].strip() if (s or "").strip() else ""
    if not s:
        return []
    c = [f"${s}$"]
    try:
        import sympy
        c.append("$" + sympy.latex(sympy.sympify(s, convert_xor=True)) + "$")
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
    if r["mode"] == "prog":
        r["cands"] = to_candidates(r.get("stdout"))
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

    def one(p):
        sd = seed * 1000 + zlib.crc32(p["id"].encode()) % 997
        q = (PROG if mode == "prog" else TEXT).format(p=p["problem"])
        o = chat(q, think=think, max_tokens=mt, temperature=0.7, seed=sd)
        text = o["text"] or ""
        row = {"id": p["id"], "src": p["src"], "level": p["level"], "subject": p["subject"], "gold": p["answer"], "mode": mode,
               "out_tokens": o.get("out_tokens"), "finish": o.get("finish")}
        if mode == "prog":
            code = last_block(text, ("python", "py", "python3"))
            r = run_python(code, "", timeout=30, mem_bytes=2 << 30) if code else None
            out = (r.stdout if r and r.status == "ok" else "") or ""
            row.update(code=code, status=(r.status if r else "no_code"), stdout=out[-500:], cands=to_candidates(out))
        else:
            row.update(text=text[-3000:])
        return row   # graded afterwards in worker processes: math_verify's signal-based timeout fails in threads (all-0 bug, 18:09)

    import threading
    from concurrent.futures import as_completed
    path = f"{RES}/math_{tag}_{mode}_s{seed}.jsonl"
    done = {json.loads(l)["id"] for l in open(path)} if os.path.exists(path) else set()   # resume after a crash (2026-10-17)
    todo = [p for p in P if p["id"] not in done]
    lock = threading.Lock()
    with ThreadPoolExecutor(48) as ex, open(path, "a") as f:
        for fu in as_completed([ex.submit(one, p) for p in todo]):
            r = fu.result()
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
