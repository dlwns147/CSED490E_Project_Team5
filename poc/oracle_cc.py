"""N5 (docs/prereg/PREREG_V.md): approximate-oracle differential testing on the contest-geometry set (ALGO-style, extended to continuous
answers), plus one counterexample repair round.
gen:   per problem the model writes (1) gen(rng) -> one small valid input, (2) a slow, obviously-correct oracle program (may approximate
       continuous answers). The oracle is accepted only if it passes the statement's examples (relative tolerance 1e-2).
check: the source run's program (if it passes the examples) runs on 20 generated inputs; mismatch with the oracle (rel. 1e-2) = flag.
repair: flagged programs get the counterexample (input, oracle output, program output) and write a corrected program.
usage: CC_SET=full POC_BASE_URL=... POC_REASONING_EFFORT=low python oracle_cc.py all <src_tag> <seed> [--max_tokens N]
       -> results/h2/n5_<src_tag>_s<seed>.jsonl"""
import json, os, sys, zlib
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_cc import OPRE, PFILE, RES, VFILE, tests_of, tok_eq  # noqa: E402
from sandbox import run_python  # noqa: E402

LOOSE, NIN = 1e-2, 20
MAXTOK = int(sys.argv[sys.argv.index("--max_tokens") + 1]) if "--max_tokens" in sys.argv else 6000

GEN_ASK = """{desc}

Do NOT solve this problem. Write a Python function `gen(rng)` that returns ONE random valid input for this problem as a single string
(exactly the stdin format above), using only the random.Random instance `rng`. Keep the input SMALL (for example at most 6-8 objects
and coordinates of absolute value at most 10) so that a slow brute-force program can solve it, but respect every constraint of the
statement (distinctness, convexity, non-collinearity, ordering, guarantees ...). Vary the cases: include degenerate and boundary
configurations that the statement allows. Give only the function in a single ```python code block."""

ORACLE_ASK = """{desc}

Write a SLOW but obviously correct Python 3 reference program for this problem, for SMALL inputs only (at most 6-8 objects). Prefer
brute force: enumerate all choices, try all candidate points, or, when the answer is a continuous optimum, area or probability that cannot
be enumerated, approximate it by dense sampling or a fine grid / repeated ternary search; 2-3 correct significant digits are enough.
Do not optimise and do not reuse a clever algorithm: clarity and correctness matter, speed does not (10 seconds per input).
It reads the input from stdin and prints the answer in the required output format. Give the program in a single ```python code block."""

REPAIR = """{desc}

Write a Python 3 program that reads the input from stdin and prints the answer to stdout.

Your previous program:
```python
{code}
```

It passes the examples from the statement, but on this small input it disagrees with a slow brute-force reference program (the
reference may be approximate in the last digits):
Input:
{inp}
Reference output:
{ref}
Your program printed:
{got}

Find the mistake and fix it. Give the complete corrected program in a single ```python code block."""
DRIVER = "\nimport random as _r, sys as _s\n_x = gen(_r.Random(int(_s.argv[1]) if len(_s.argv) > 1 else int(_s.stdin.read() or 0)))\nprint(_x if isinstance(_x, str) else '', end='')\n"


def run(code, inp, t=10):
    r = run_python(code, inp, timeout=t)
    return r.stdout if r.status == "ok" else None


def build(p, gcode, ocode):
    """-> (oracle accepted?, [(input, oracle output)])"""
    if not (gcode and ocode):
        return False, []
    pub = [t for t in p["tests"] if t["kind"] == "public"]
    if not all((o := run(ocode, t["input"])) is not None and tok_eq(o, t["output"], LOOSE) for t in pub):
        return False, []
    cases = []
    for s in range(NIN):
        inp = run(gcode + DRIVER, str(s), t=5)
        if inp and inp.strip():
            o = run(ocode, inp)
            if o is not None and o.strip():
                cases.append((inp if inp.endswith("\n") else inp + "\n", o))
    return True, cases


def main(src, seed):
    from llm import chat, last_block
    P = {p["name"]: p for p in json.load(open(PFILE))}; V = json.load(open(VFILE))
    rows = {r["name"]: r for r in map(json.loads, open(f"{RES}/{OPRE}{src}_s{seed}.jsonl"))}
    npub = {n: sum(t["kind"] == "public" for t in p["tests"]) for n, p in P.items()}

    def one(name):
        p, r = P[name], rows[name]; d = p["description"].strip(); tok = 0
        sd = 31000 + seed * 1000 + zlib.crc32(name.encode()) % 997
        og = chat(GEN_ASK.replace("{desc}", d), max_tokens=MAXTOK, temperature=0.7, seed=sd)
        oo = chat(ORACLE_ASK.replace("{desc}", d), max_tokens=MAXTOK, temperature=0.7, seed=sd + 1)
        tok += (og.get("out_tokens") or 0) + (oo.get("out_tokens") or 0)
        gcode, ocode = last_block(og["text"] or "", ("python", "py")), last_block(oo["text"] or "", ("python", "py", "python3"))
        ok, cases = build(p, gcode, ocode)
        base = {"name": name, "orig_passed_all": r["passed_all"], "passes_examples": bool(r["code"]) and r["passed"] >= npub[name],
                "oracle_ok": ok, "n_cases": len(cases), "oracle_tokens": tok, "gen_code": gcode, "oracle_code": ocode,
                "cases": cases if ok else []}   # saved for N5b (selection among samples)
        if not (ok and cases and base["passes_examples"]):
            return {**base, "flagged": False, "repaired": False, "passed_all": r["passed_all"], "repair_tokens": 0}
        cex = None
        for inp, ref in cases:
            got = run(r["code"], inp)
            if got is None or not tok_eq(got, ref, LOOSE):
                cex = (inp, ref, got if got is not None else "(crash or time-out)"); break
        if cex is None:
            return {**base, "flagged": False, "repaired": False, "passed_all": r["passed_all"], "repair_tokens": 0}
        cut = lambda s: s if len(s) <= 1200 else s[:1200] + "\n..."
        q = REPAIR
        for k, v in (("{desc}", d), ("{code}", r["code"]), ("{inp}", cut(cex[0])), ("{ref}", cut(cex[1])), ("{got}", cut(cex[2]))):
            q = q.replace(k, v)
        o = chat(q, max_tokens=MAXTOK, temperature=0.7, seed=sd + 2)
        code = last_block(o["text"] or "", ("python", "py", "python3"))
        T = tests_of(p); passed = 0; tol = V[name]["tol"]
        if code:
            for t in T:
                x = run_python(code, t["input"], timeout=10)
                if x.status != "ok" or not tok_eq(x.stdout, t["output"], tol):
                    break
                passed += 1
        return {**base, "flagged": True, "repaired": True, "passed_all": bool(code) and passed == len(T), "repair_tokens": o.get("out_tokens") or 0,
                "cex": [cut(x) for x in cex], "code": code}

    lim = int(os.environ.get("N5_LIMIT", "0"))
    with ThreadPoolExecutor(16) as ex:
        out = list(ex.map(one, sorted(rows)[:lim] if lim else sorted(rows)))
    with open(f"{RES}/n5_{src}_s{seed}" + ("_test" if lim else "") + ".jsonl", "w") as f:
        for r in out:
            f.write(json.dumps(r) + "\n")
    print(src, seed, f"oracle accepted {sum(r['oracle_ok'] for r in out)}/{len(out)}; flagged {sum(r['flagged'] for r in out)}; "
          f"solved {sum(r['orig_passed_all'] for r in out)} -> {sum(r['passed_all'] for r in out)}")


if __name__ == "__main__":
    main(sys.argv[2], int(sys.argv[3]))
