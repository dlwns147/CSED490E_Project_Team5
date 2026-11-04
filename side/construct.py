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
  analyze (dev) choosing among sampled objects by agreement with sampled checkers (CodeT's dual execution agreement, 2207.10397),
          else the thinking answer; right, tokens, utility per configuration
usage: python side/construct.py build
       $P side/construct.py gen <tag> <ids file> --arm direct|program|checker [--think] [--max_tokens N] [--k K]
       python side/construct.py grade <answer tag> [<answer tag> ...] --checkers <checker tag> [<checker tag> ...]
       python side/construct.py analyze <grade file tags> [...] --checkers <checker tag> --think <answer tag>
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
    if "--more" in sys.argv:   # SIDE-MC-H2: variations 2 and 3 (generate_multiple is prefix-stable), appended; fresh ids for held-out problems
        return build_more(C)
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


def build_more(C):
    old = [json.loads(l) for l in open(os.path.join(PD, "instances.jsonl"))]
    seen = {x["statement"] for x in old}
    held = {x.split("__")[0] for x in open(os.path.join(PD, "ids_mceval.txt")).read().split()}
    rows = []
    for c in C:
        for v, p in enumerate(c.generate_multiple(5, include_original=True)[1:]):
            if v < 2 or str(p) in seen:
                continue
            seen.add(str(p))
            try:
                ex = c.parse(p.get_formatting())
                example = f" For example, the answer in the example above parses to `{ex!r}`."
            except Exception:
                example = ""
            rows.append({"id": f"{c.config.name}__v{v}", "name": c.config.name, "v": v, "statement": str(p), "formatting": p.get_formatting(),
                         "example": example, "params": json.loads(json.dumps(p.to_json()["param_values"], default=str))})
    with open(os.path.join(PD, "instances.jsonl"), "a") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    fresh = [r["id"] for r in rows if r["name"] in held]
    open(os.path.join(PD, "ids_mcfresh.txt"), "w").write("\n".join(fresh) + "\n")
    print(f"{len(rows)} new instances; {len(fresh)} of held-out problems -> ids_mcfresh.txt")


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
            variations[x["name"]] = C[x["name"]].generate_multiple(5, include_original=True)[1:]   # prefix-stable (v0, v1 as before)
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


def analyze():
    """Answers of the quick tags (their first k samples) are grouped by parsed value; a group scores its size times the number of the
    first m checker samples accepting it (CodeT: consensus set size x tests passed). The best group answers when some checker accepts
    it; otherwise the thinking answer does (its tokens added). Tokens: every answer and checker sampled. Utility 100 x right - 0.5 x
    ktokens per instance; the arms alone for reference."""
    from collections import defaultdict
    k = sys.argv.index("--checkers")
    files, ctag, ttag = sys.argv[2:k], sys.argv[k + 1], sys.argv[sys.argv.index("--think") + 1]
    G = [json.loads(l) for f in files for l in open(f"{OUT}/mc_grade_{f}.jsonl")]
    ctok = {(r["id"], r.get("s", 0)): r["out_tokens"] for r in map(json.loads, open(f"{OUT}/mc_{ctag}.jsonl"))}
    by = defaultdict(list)
    for g in G:
        by[(g["id"], g["tag"])].append(g)
    think = {g["id"]: g for g in G if g["tag"] == ttag}
    ids = sorted(think)
    qt = sorted({g["tag"] for g in G} - {ttag})
    verdict = lambda g, s: g.get("checks", {}).get(ctag if s == 0 else f"{ctag}#{s}")
    print(f"SIDE-MC analyze: {len(ids)} instances; quick tags {qt}; checkers {ctag}; think {ttag}")
    th_r, th_t = sum(think[i]["right"] for i in ids), sum(think[i]["out_tokens"] for i in ids) / 1000
    print(f"  think alone: {th_r} right, {th_t / len(ids):.1f}k tokens, utility {(100 * th_r - 0.5 * th_t) / len(ids):+.2f} per instance")
    for t in qt:
        for kk in (1, 8):
            C = [g for i in ids for g in by[(i, t)] if g["s"] < kk]
            anyr = sum(any(g["right"] for g in by[(i, t)] if g["s"] < kk) for i in ids)
            print(f"  {t} k={kk}: right among them on {anyr} instances; {sum(g['right'] for g in C) / max(1, len(C)) * 100:.1f}% of answers right; "
                  f"{sum(g['out_tokens'] for g in C) / len(ids) / 1000:.1f}k tokens")
    for lab in (True, False):
        V = [verdict(g, s) for g in G if g["tag"] != ttag and g["parsed"] and g["right"] == lab for s in range(8)]
        print(f"  checkers on {'right' if lab else 'wrong'} parsed answers: accept {sum(v == 'accept' for v in V)}, reject "
              f"{sum(v == 'reject' for v in V)}, error {sum(bool(v) and v.startswith('error') for v in V)} of {len(V)}")
    for tags in [[t] for t in qt] + [qt]:
        for kk in (1, 2, 4, 8):
            for m in (1, 4, 8):
                sel = selr = right = esc = 0; tok = 0.0
                for i in ids:
                    C = [g for t in tags for g in by[(i, t)] if g["s"] < kk]
                    tok += sum(g["out_tokens"] for g in C) + sum(ctok.get((i, s), 0) for s in range(m))
                    grp = defaultdict(list)
                    for g in C:
                        if g["parsed"]:
                            grp[g["parsed"]].append(g)
                    sc = {p: len(v) * sum(verdict(v[0], s) == "accept" for s in range(m)) for p, v in grp.items()}
                    best = max(sc, key=sc.get) if sc else None
                    if best is not None and sc[best] > 0:
                        sel += 1; selr += grp[best][0]["right"]; right += grp[best][0]["right"]
                    else:
                        esc += 1; right += think[i]["right"]; tok += think[i]["out_tokens"]
                tok /= 1000
                print(f"  {'+'.join(tags)} k={kk} m={m}: chosen {sel} ({selr} right), escalated {esc}; right {right}; "
                      f"{tok / len(ids):.1f}k tokens; utility {(100 * right - 0.5 * tok) / len(ids):+.2f}")


def cascade():
    """SIDE-MC-H (PREREG_SIDE): arms D (direct, thinking), P (program, thinking), C (P's object when it parses and one of the first m
    quick checkers accepts it, else D's), C0 (parsing as the only check); accuracy and utility (100 x right - 0.5 x ktokens), paired
    95% bootstrap intervals over problems (both variations of a problem resampled together).
    usage: python side/construct.py cascade <grade file tag> --direct <tag> --program <tag> --checkers <tag> [--m 4]"""
    import random
    from collections import defaultdict
    G = [json.loads(l) for l in open(f"{OUT}/mc_grade_{sys.argv[2]}.jsonl")]
    dt, pt, ct = (sys.argv[sys.argv.index(f) + 1] for f in ("--direct", "--program", "--checkers"))
    m = int(sys.argv[sys.argv.index("--m") + 1]) if "--m" in sys.argv else 4
    ctok = defaultdict(int)
    for r in map(json.loads, open(f"{OUT}/mc_{ct}.jsonl")):
        if r.get("s", 0) < m:
            ctok[r["id"]] += r["out_tokens"]
    D = {g["id"]: g for g in G if g["tag"] == dt}
    P = {g["id"]: g for g in G if g["tag"] == pt}
    ids = sorted(set(D) & set(P))
    acc = lambda g: any(g.get("checks", {}).get(ct if s == 0 else f"{ct}#{s}") == "accept" for s in range(m))
    arms = {"D": {}, "P": {}, "C": {}, "C0": {}}
    for i in ids:
        d, p = D[i], P[i]
        arms["D"][i] = (d["right"], d["out_tokens"])
        arms["P"][i] = (p["right"], p["out_tokens"])
        arms["C"][i] = ((p["right"], p["out_tokens"] + ctok[i]) if p["parsed"] and acc(p)
                        else (d["right"], p["out_tokens"] + ctok[i] + d["out_tokens"]))
        arms["C0"][i] = (p["right"], p["out_tokens"]) if p["parsed"] else (d["right"], p["out_tokens"] + d["out_tokens"])
    u = lambda rt: 100 * rt[0] - 0.5 * rt[1] / 1000
    prob = defaultdict(list)
    for i in ids:
        prob[i.rsplit("__", 1)[0]].append(i)
    names = sorted(prob)

    def ci(f):
        B = []
        for b in range(10000):
            r = random.Random(b)
            S = [i for _ in names for i in prob[r.choice(names)]]
            B.append(sum(f(i) for i in S) / len(S))
        B.sort()
        return sum(f(i) for i in ids) / len(ids), B[249], B[9749]
    print(f"SIDE-MC-H: {len(ids)} instances of {len(names)} problems; checkers {ct} (first {m})")
    for a, X in arms.items():
        print(f"  {a:3s} right {sum(v[0] for v in X.values()):3d} ({100 * sum(v[0] for v in X.values()) / len(ids):.1f}%), "
              f"{sum(v[1] for v in X.values()) / len(ids) / 1000:.1f}k tokens, utility {sum(u(v) for v in X.values()) / len(ids):+.2f}")
    for a, b in (("C", "D"), ("C0", "D"), ("C", "C0"), ("P", "D")):
        da = ci(lambda i: 100 * (arms[a][i][0] - arms[b][i][0]))
        du = ci(lambda i: u(arms[a][i]) - u(arms[b][i]))
        print(f"  {a} - {b}: accuracy {da[0]:+.2f} [{da[1]:+.2f}, {da[2]:+.2f}]; utility {du[0]:+.2f} [{du[1]:+.2f}, {du[2]:+.2f}]")
    pr = {i for i in ids if P[i]["right"]}; dr = {i for i in ids if D[i]["right"]}
    print(f"  right objects: P {len(pr)}, D {len(dr)}, both {len(pr & dr)}, union {len(pr | dr)}")
    for lab in (True, False):
        V = [acc(g) for g in list(P.values()) + list(D.values()) if g["parsed"] and g["right"] == lab]
        print(f"  {'right' if lab else 'wrong'} parsed objects accepted by a checker: {sum(V)} of {len(V)}")


if __name__ == "__main__":
    {"build": build, "gen": gen, "grade": grade, "analyze": analyze, "cascade": cascade}[sys.argv[1]]()
