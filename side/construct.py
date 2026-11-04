"""SIDE-MC (docs/prereg/PREREG_SIDE.md): constructions, the computation side of the proof track. A constructive problem ("show there
exists an object with these properties") is solved by the object itself, and whether an object is right is decided by computation.
MathConstruct (Balunović et al., 2502.10197; eth-sri/mathconstruct, MIT) has 121 such problems from competitions, each with a
human-written verifier and generated variations (other parameters, so a remembered answer does not help).
The questions: (1) which route gives a verified object with the fewest tokens: answering directly, quick or thinking, or writing a
program that constructs (or searches for) the object; (2) whether a checker the model writes from the statement alone, before seeing
any answer, can stand in for the human verifier as the free check (on these problems its errors are measurable exactly).
  build   (MathConstruct's environment) instances -> $POC_DATA/construct/instances.jsonl, ids_mcdev.txt / ids_mceval.txt
  gen     (lane.sh job) --arm direct | program | checker [--think] -> results/proof/mc_<tag>.jsonl; a program runs in the sandbox here
  grade   (MathConstruct's environment) every answer by the human verifier, and every checker on every answer of the same instance
          -> results/proof/mc_grade_<tags>.jsonl
usage: python side/construct.py build
       $P side/construct.py gen <tag> <ids file> --arm direct|program|checker [--think] [--max_tokens N] [--k K]
       python side/construct.py grade <answer tag> [<answer tag> ...] --checkers <checker tag> [<checker tag> ...]
(MathConstruct's environment: PYTHONPATH=$POC_DATA/construct/mathconstruct/src:$POC_DATA/construct/pylib)"""
import json, os, random, re, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "poc"))
PD = os.path.join(os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data"), "construct")
OUT = os.path.join(ROOT, "results", "proof")

PROMPT_PROGRAM = """{statement}

Do not answer directly. Write one Python 3 program that constructs the required object for exactly these parameters (by an explicit \
construction, or by searching for it) and prints the final answer in the format below. Use only the standard library; the program \
must finish within 60 seconds.

Format the printed answer as follows:
{formatting}

Reply with the program in one ```python code block."""

PROMPT_CHECKER = """{statement}

Do not solve the problem. Write a Python 3 function `check(x)` that returns True exactly when `x` is a correct answer to this problem \
for exactly these parameters (it satisfies every requirement of the statement), and False otherwise.

An answer is written as follows:
{formatting}
`x` is that answer already parsed into Python values (integers, Fractions, floats, strings, nested lists).{example}

Use only the standard library; `check` must finish within 10 seconds. Reply with the function in one ```python code block."""


def code_of(text):
    b = re.findall(r"```(?:python|py)?[ \t]*\n(.*?)```", text, flags=re.S)
    return b[-1] if b else None


def build():
    from math_construct.problems import get_all_problem_classes
    C = sorted(get_all_problem_classes(), key=lambda c: c.config.name)
    os.makedirs(PD, exist_ok=True)
    rows = []
    for c in C:
        for v, p in enumerate(c.generate_multiple(3, include_original=True)[1:]):   # two variations, not the published original
            try:
                ex = c.parse(p.get_formatting())
                example = f" For example, the answer in the example above parses to `{ex!r}`."
            except Exception:
                example = ""
            rows.append({"id": f"{c.config.name}__v{v}", "name": c.config.name, "v": v, "statement": str(p), "formatting": p.get_formatting(),
                         "example": example, "params": json.loads(json.dumps(p.to_json()["param_values"], default=str))})
    with open(os.path.join(PD, "instances.jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    names = sorted({r["name"] for r in rows})
    random.Random(0).shuffle(names)
    dev = set(names[:40])
    for fn, keep in (("ids_mcdev.txt", lambda n: n in dev), ("ids_mceval.txt", lambda n: n not in dev)):
        open(os.path.join(PD, fn), "w").write("\n".join(r["id"] for r in rows if keep(r["name"])) + "\n")
    print(f"{len(rows)} instances of {len(names)} problems; dev {sum(r['name'] in dev for r in rows)}")


def gen():
    from llm import chat
    from sandbox import run_python
    tag, ids_file = sys.argv[2], sys.argv[3]
    arm = sys.argv[sys.argv.index("--arm") + 1]
    think = "--think" in sys.argv
    mt = int(sys.argv[sys.argv.index("--max_tokens") + 1]) if "--max_tokens" in sys.argv else (16000 if think else 4096)
    k = int(sys.argv[sys.argv.index("--k") + 1]) if "--k" in sys.argv else 1   # independent samples per instance
    want = set(open(ids_file).read().split())
    X = [x for x in map(json.loads, open(os.path.join(PD, "instances.jsonl"))) if x["id"] in want]
    os.makedirs(OUT, exist_ok=True)
    out = f"{OUT}/mc_{tag}.jsonl"
    done = {(r["id"], r.get("s", 0)) for r in map(json.loads, open(out))} if os.path.exists(out) else set()
    todo = [(x, i) for x in X for i in range(k) if (x["id"], i) not in done]
    print(f"SIDE-MC gen {tag}: {len(todo)} of {len(X) * k} samples (arm={arm}, think={think}, k={k})", flush=True)

    def one(x, i):
        if arm == "direct":   # MathConstruct's own prompt
            q = f"{x['statement']}\n\nFormat your reply as follows:\n{x['formatting']}"
        elif arm == "program":
            q = PROMPT_PROGRAM.format(statement=x["statement"], formatting=x["formatting"])
        else:
            q = PROMPT_CHECKER.format(statement=x["statement"], formatting=x["formatting"], example=x["example"])
        r = chat(q, think=think, max_tokens=mt, temperature=0.6 if think else 0.7)
        row = {"id": x["id"], "s": i, "arm": arm, "think": think, "out_tokens": r["out_tokens"], "in_tokens": r["in_tokens"],
               "finish": r["finish"], "text": r["text"][-6000:]}
        if arm != "direct":
            row["code"] = code_of(r["text"])
        if arm == "program" and row["code"]:
            run = run_python(row["code"], "", timeout=60)
            row.update(status=run.status, stdout=run.stdout[-20000:], stderr=run.stderr[-300:])
        return row
    with ThreadPoolExecutor(32) as ex, open(out, "a") as f:
        for fu in as_completed([ex.submit(one, x, i) for x, i in todo]):
            try:
                r = fu.result()
            except Exception as e:
                print(f"  failed: {type(e).__name__}: {str(e)[:200]}", flush=True); continue
            f.write(json.dumps(r) + "\n"); f.flush()


def answer_text(r):
    """the text the human verifier parses: the reply, or for a program the program's output"""
    if r["arm"] == "program":
        return r.get("stdout", "") if r.get("status") == "ok" else ""
    return r["text"]


def grade():
    import logging
    from fractions import Fraction  # noqa: F401  (answers are passed to checkers by repr)
    from math_construct.problems import get_all_problem_classes
    from sandbox import run_python
    logging.disable(logging.CRITICAL)
    try:
        from loguru import logger
        logger.remove()
    except ImportError:
        pass
    k = sys.argv.index("--checkers")
    atags, ctags = sys.argv[2:k], sys.argv[k + 1:]
    C = {c.config.name: c for c in get_all_problem_classes()}
    inst = {x["id"]: x for x in map(json.loads, open(os.path.join(PD, "instances.jsonl")))}
    A = [r | {"tag": t} for t in atags for r in map(json.loads, open(f"{OUT}/mc_{t}.jsonl"))]
    K = [r | {"tag": t} for t in ctags for r in map(json.loads, open(f"{OUT}/mc_{t}.jsonl"))]
    variations = {}   # rebuilt as `build` drew them (generate_multiple seeds its draws)
    rows = []
    for r in A:
        x = inst[r["id"]]
        if x["name"] not in variations:
            variations[x["name"]] = C[x["name"]].generate_multiple(3, include_original=True)[1:]
        p = variations[x["name"]][x["v"]]
        assert str(p) == x["statement"], x["id"]
        parsed, ok, detail = p.parse_and_check([{"role": "assistant", "content": answer_text(r)}])   # MathConstruct reads a chat
        rows.append({"id": r["id"], "s": r.get("s", 0), "tag": r["tag"], "right": bool(ok), "parsed": None if parsed is None else repr(parsed),
                     "detail": str(detail)[:200], "out_tokens": r["out_tokens"]})

    def run_checker(code, parsed):
        harness = code + "\n\nfrom fractions import Fraction\nimport sys\nx = eval(sys.stdin.read())\nprint('CHECK', bool(check(x)))\n"
        run = run_python(harness, parsed, timeout=10)
        last = (run.stdout.strip().splitlines() or [""])[-1]
        return "accept" if last == "CHECK True" else ("reject" if last == "CHECK False" else f"error ({run.status})")
    jobs = [(a, c) for a in rows if a["parsed"] for c in K if c["id"] == a["id"] and c.get("code")]
    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(lambda ac: run_checker(ac[1]["code"], ac[0]["parsed"]), jobs))
    for (a, c), v in zip(jobs, res):
        a.setdefault("checks", {})[c["tag"] if c.get("s", 0) == 0 else f"{c['tag']}#{c['s']}"] = v   # one verdict per checker sample
    out = f"{OUT}/mc_grade_{'+'.join(atags)}.jsonl"
    with open(out, "w") as f:
        for a in rows:
            f.write(json.dumps(a) + "\n")
    print(f"SIDE-MC grade: {len(rows)} answers, {len(jobs)} checker runs -> {out}")


if __name__ == "__main__":
    {"build": build, "gen": gen, "grade": grade}[sys.argv[1]]()
