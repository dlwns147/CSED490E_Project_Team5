"""H2: real contest geometry problems (CodeContests, Codeforces geometry tag) with official tests and difficulty ratings.
  validate: run the C++ / Python reference solutions through our checker; keep problems where a reference passes every test, and record the
            tolerance needed (exact tokens, else numeric 1e-6, else 1e-4); problems no reference passes (special judges) are dropped.
  run:      the model writes a Python 3 program from the statement; pass = all kept tests correct (stop at the first failure).
  CC_SET=full uses the full set (results/h2/cc_geometry_full.json, 355 problems): validation runs all (≤ 5) C++ references, takes the
            smallest tolerance at which one passes (≥ 1e-6 if an expected output has a decimal number), and flags problems where a reference
            that runs fails a test another reference passes (several valid answers, or a special judge); outputs go to cc_full_<tag>_s<seed>.jsonl.
usage: [CC_SET=full] python run_cc.py validate
       [CC_SET=full] POC_BASE_URL=... [POC_REASONING_EFFORT=low] python run_cc.py run <tag> <seed> [--think | --think_budget B | --k8]"""
import json, os, random, re, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sandbox import run_python  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root (was hard-coded)
RES = f"{ROOT}/results/h2"
MAX_GEN = 30   # generated tests kept per problem (all public and private tests are kept)
SET = os.environ.get("CC_SET", "local")
PFILE = f"{RES}/cc_geometry_{SET}.json"
VFILE = f"{RES}/cc_valid.json" if SET == "local" else f"{RES}/cc_valid_{SET}.json"
OPRE = "cc_" if SET == "local" else f"cc_{SET}_"


def tests_of(p):
    pub = [t for t in p["tests"] if t["kind"] != "generated"]
    gen = [t for t in p["tests"] if t["kind"] == "generated"][:MAX_GEN]
    return pub + gen


def tok_eq(a, b, tol):
    A, B = a.split(), b.split()
    if len(A) != len(B):
        return False
    for x, y in zip(A, B):
        if x == y:
            continue
        if tol is None:
            return False
        try:
            fx, fy = float(x), float(y)
        except ValueError:
            if x.lower() != y.lower():
                return False
            continue
        if abs(fx - fy) > tol * max(1.0, abs(fy)):
            return False
    return True


def run_cpp(src, inputs, tl):
    with tempfile.TemporaryDirectory(prefix="cc_") as d:
        with open(f"{d}/a.cpp", "w") as f:
            f.write(src)
        c = subprocess.run(["g++", "-O2", "-std=c++17", "-o", f"{d}/a", f"{d}/a.cpp"], capture_output=True, timeout=120)
        if c.returncode != 0:
            return None
        outs = []
        for inp in inputs:
            try:
                r = subprocess.run([f"{d}/a"], input=inp.encode(), capture_output=True, timeout=max(4, 2 * tl))
                outs.append(r.stdout.decode(errors="replace") if r.returncode == 0 else None)
            except subprocess.TimeoutExpired:
                outs.append(None)
        return outs


RANK = [None, 1e-6, 1e-4]   # strictest first


def validate_full():
    P = json.load(open(PFILE))
    dec = re.compile(r"-?\d+\.\d+")

    def one(p):
        T = tests_of(p)
        floats = any(dec.fullmatch(tok) for t in T for tok in t["output"].split())
        tols = (1e-6, 1e-4) if floats else (None, 1e-6, 1e-4)
        found, ran, wrong = [], 0, 0   # found = tolerances at which a reference passes; wrong = references that run but print other answers
        for src in p["cpp"][:5]:
            outs = run_cpp(src, [t["input"] for t in T], p["time_limit"])
            if outs is None:
                continue
            ran += 1
            ok = [tol for tol in tols if all(o is not None and tok_eq(o, t["output"], tol) for o, t in zip(outs, T))]
            if ok:
                found.append(ok[0])
            elif all(o is not None for o in outs):
                wrong += 1
        best = min(found, key=RANK.index) if found else None
        return p["name"], bool(found), best, len(T), ran, wrong

    with ThreadPoolExecutor(32) as ex:
        res = list(ex.map(one, P))
    keep = {n: {"tol": tol, "n_tests": nt, "refs_run": ran, "refs_wrong": fl, "flag_multi": fl > 0}
            for n, ok, tol, nt, ran, fl in res if ok}
    json.dump(keep, open(VFILE, "w"), indent=1)
    print(f"validated {len(keep)} of {len(P)} problems; flagged (a reference that runs prints other answers): {sum(v['flag_multi'] for v in keep.values())}; "
          f"dropped {len(P) - len(keep)}")


def validate():
    if SET != "local":
        return validate_full()
    P = json.load(open(PFILE))

    def one(p):
        T = tests_of(p)
        for src in p["cpp"][:3]:
            outs = run_cpp(src, [t["input"] for t in T], p["time_limit"])
            if outs is None:
                continue
            for tol in (None, 1e-6, 1e-4):
                if all(o is not None and tok_eq(o, t["output"], tol) for o, t in zip(outs, T)):
                    return p["name"], True, tol, len(T)
        return p["name"], False, None, len(T)

    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(one, P))
    keep = {n: {"tol": tol, "n_tests": nt} for n, ok, tol, nt in res if ok}
    json.dump(keep, open(f"{RES}/cc_valid.json", "w"), indent=1)
    print(f"validated {len(keep)} of {len(P)} problems (a C++ reference passes every kept test); dropped:",
          [n for n, ok, _, _ in res if not ok])


def _toks(t):
    return re.findall(r"[a-z_]+|\d+", t.lower())


def exemplars(mode):
    """N6: for every problem, the top-1 other geometry problem by BM25 (statement text, or code: the model's own seed-1 program against
    the corpus solutions), excluding the same contest and the same title. -> {name: (problem, solution, language)}"""
    import math
    from collections import Counter
    C = [p for p in json.load(open(f"{RES}/cc_geometry_full.json")) if p["py3"] or p["cpp"]]
    doc = lambda p: p["description"] if mode == "stmt" else (p["py3"] or p["cpp"])[0]
    D = [Counter(_toks(doc(p))) for p in C]; L = [sum(d.values()) for d in D]; avg = sum(L) / len(L)
    df = Counter(t for d in D for t in d)
    idf = {t: math.log(1 + (len(C) - n + 0.5) / (n + 0.5)) for t, n in df.items()}
    src = None if mode == "stmt" else {r["name"]: r for r in map(json.loads, open(f"{RES}/{OPRE}{mode.split(':')[1]}_s1.jsonl"))}
    title = lambda n: n.split(". ", 1)[-1].strip().lower()
    out = {}
    for p in json.load(open(PFILE)):
        q = Counter(_toks(p["description"] if src is None else (src.get(p["name"], {}).get("code") or p["description"])))
        best = None
        for c, d, l in zip(C, D, L):
            if c["name"].split("_")[0] == p["name"].split("_")[0] or title(c["name"]) == title(p["name"]):
                continue
            sc = sum(idf.get(t, 0) * d[t] * 2.5 / (d[t] + 1.5 * (0.25 + 0.75 * l / avg)) for t in q if t in d)
            if best is None or sc > best[0]:
                best = (sc, c)
        c = best[1]; lang = "python" if c["py3"] else "cpp"
        out[p["name"]] = (c["name"], c["description"][:2000], (c["py3"] or c["cpp"])[0][:3000], lang, best[0])
    return out


def run(tag, seed, mode):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from llm import chat, last_block
    P = {p["name"]: p for p in json.load(open(PFILE))}
    keep = json.load(open(VFILE))

    EX = exemplars(mode["exemplar"]) if mode.get("exemplar") else {}

    def one(name):
        p = P[name]; T = tests_of(p); tol = keep[name]["tol"]
        tb = ""
        if name in EX:   # N6: one retrieved solved problem, before the target statement
            en, ed, ec, lang, _ = EX[name]
            tb_ex = (f"A different, already solved problem that may use related techniques:\n\n{ed}\n\nAn accepted solution ({lang}):\n```{lang}\n{ec}\n```\n\n"
                     "Now solve the following problem.\n\n")
        else:
            tb_ex = ""
        if mode.get("k8"):
            from geo_distractors import RELATED, render_names, with_deps
            names = random.Random(f"cc-{name}-tb").sample(list(RELATED), 8)
            tb = "\n\n" + render_names(with_deps(names), head=mode.get("head", "should"))
        if mode.get("k8u"):   # H4b control: all 6 unrelated helpers (gcd, is_prime, ...), same header
            from geo_distractors import UNRELATED, render_names
            names = list(UNRELATED); random.Random(f"cc-{name}-tbu").shuffle(names)
            tb = "\n\n" + render_names(names)
        prompt = (tb_ex + p["description"].strip() + "\n\nWrite a Python 3 program that reads the input from stdin and prints the answer to stdout. "
                  "Give the program in a single ```python code block." + tb
                  + (" Reply with the program only: no explanation before or after the code block." if mode.get("codeonly") else ""))
        if mode.get("para") == 1:   # P1 (CRITIQUE item 9): same content, reworded instruction after the statement
            prompt = (p["description"].strip() + "\n\nSolve the problem above with a complete Python 3 program. It must read its input "
                      "from standard input and write the answer to standard output. Put the whole program in one ```python code block.")
        elif mode.get("para") == 2:   # instruction first, terser
            prompt = ("Implement a solution in Python 3 (input from stdin, answer to stdout) and return it as a single ```python code "
                      "block.\n\nProblem:\n" + p["description"].strip())
        import zlib
        sd = seed * 1000 + zlib.crc32(name.encode()) % 997
        if mode.get("think_budget"):
            from run_geo_cross import budget_chat
            o = budget_chat(prompt, mode["think_budget"], max_tokens=6000, temperature=0.7, seed=sd)
        else:
            o = chat(prompt, think=mode.get("think", False), max_tokens=mode.get("max_tokens", 6000), temperature=0.7, seed=sd,
                     logprobs=bool(mode.get("logprobs")))
        code = last_block(o["text"] or "", ("python", "py", "python3"))
        passed = 0
        if code:
            for t in T:
                r = run_python(code, t["input"], timeout=10)
                if r.status != "ok" or not tok_eq(r.stdout, t["output"], tol):
                    break
                passed += 1
        return {"name": name, "rating": p["rating"], "passed_all": bool(code) and passed == len(T), "passed": passed, "n_tests": len(T),
                "exemplar": EX[name][0] if name in EX else None,
                "out_tokens": o.get("out_tokens"), "finish": o.get("finish"), "code": code, "text": (o.get("text") or "")[-4000:],
                **({"lp": o.get("lp"), "lp_tok": o.get("lp_tok")} if mode.get("logprobs") else {})}   # N18

    shard = os.environ.get("CC_SHARD")   # "i/n": this process handles problems with index % n == i (H2e)
    todo = sorted(keep)
    if shard:
        i, n = map(int, shard.split("/")); todo = [x for k, x in enumerate(todo) if k % n == i]
    path = f"{RES}/{OPRE}{tag}_s{seed}" + (f"_shard{shard.replace('/', 'of')}" if shard else "") + ".jsonl"
    done = set()   # rows flushed as they finish; resumes (2026-10-17); skips a torn line (a NUL-filled line on the NAS, 2026-10-18)
    for l in (open(path, errors="replace") if os.path.exists(path) else []):
        try:
            done.add(json.loads(l)["name"])
        except ValueError:
            pass
    from concurrent.futures import as_completed
    with ThreadPoolExecutor(16) as ex, open(path, "a") as f:
        for fu in as_completed([ex.submit(one, x) for x in todo if x not in done]):
            f.write(json.dumps(fu.result()) + "\n"); f.flush()
    rows = [json.loads(l) for l in open(path)]
    print(tag, seed, f"solved {sum(r['passed_all'] for r in rows)}/{len(rows)}")


if __name__ == "__main__":
    if sys.argv[1] == "validate":
        validate()
    else:
        mode = {}
        if "--think" in sys.argv:
            mode.update(think=True, max_tokens=16000)
        if "--think_budget" in sys.argv:
            mode["think_budget"] = int(sys.argv[sys.argv.index("--think_budget") + 1])
        if "--k8" in sys.argv:
            mode["k8"] = True
        if "--k8may" in sys.argv:   # H4b: related helpers with the "most are probably NOT needed" header
            mode.update(k8=True, head="may")
        if "--k8u" in sys.argv:
            mode["k8u"] = True
        if "--max_tokens" in sys.argv:
            mode["max_tokens"] = int(sys.argv[sys.argv.index("--max_tokens") + 1])
        if "--logprobs" in sys.argv:   # N18
            mode["logprobs"] = True
        if "--para" in sys.argv:   # P1
            mode["para"] = int(sys.argv[sys.argv.index("--para") + 1])
        if "--codeonly" in sys.argv:   # H6d
            mode["codeonly"] = True
        if "--exemplar" in sys.argv:   # N6: stmt | draft:<src_tag>
            mode["exemplar"] = sys.argv[sys.argv.index("--exemplar") + 1]
        run(sys.argv[2], int(sys.argv[3]), mode)
