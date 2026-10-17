"""N1 (docs/prereg/PREREG_N.md): metamorphic example augmentation (MEA) on the contest-geometry set.
gen:  the model writes transform(inp) -> list[str] (inputs whose correct output is exactly the same as for inp, as guaranteed by the
      statement), one call per problem -> results/h2/mea_<tag>.json
eval: each public example's derived inputs inherit the example's output; every Part B sample that passes the public examples is run on
      them. Detection = wrong passers that fail a derived test; false alarm = correct passers that fail one. Also used as a selector.
usage: CC_SET=full POC_BASE_URL=... python mea_cc.py gen <tag>
       CC_SET=full python mea_cc.py eval <tag>"""
import json, os, sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_cc import OPRE, PFILE, RES, VFILE, tok_eq  # noqa: E402
from sandbox import run_python  # noqa: E402

ASK = """{desc}

Do NOT solve this problem. Instead write a Python function `transform(inp: str) -> list[str]` that takes one valid input of this
problem (the whole stdin text) and returns up to 4 NEW valid inputs whose correct output is guaranteed by the statement to be EXACTLY the
same as the correct output for `inp` (character for character, up to the stated precision). Typical transformations: reorder items whose
order does not matter, translate all coordinates, rotate all coordinates by 90 degrees or mirror them when the answer does not depend on
orientation, swap roles that are symmetric. Every new input must respect the input format and all constraints (coordinate bounds, sizes).
Use only transformations you are sure about from the statement; if none is guaranteed, return []. Use the standard library only and no
randomness without a fixed seed. Give only the function in a single ```python code block."""
CONDS = ("q32b_plain", "q32b_think1024", "oss20_low", "oss20_medium", "oss120_low", "oss120_medium")


def gen(tag):
    from llm import chat, last_block
    P = json.load(open(PFILE)); keep = json.load(open(VFILE))

    def one(p):
        o = chat(ASK.format(desc=p["description"].strip()), max_tokens=3000, temperature=0.7, seed=4242)
        return p["name"], {"code": last_block(o["text"] or "", ("python", "py", "python3")), "out_tokens": o.get("out_tokens")}

    with ThreadPoolExecutor(16) as ex:
        out = dict(ex.map(one, [p for p in P if p["name"] in keep]))
    json.dump(out, open(f"{RES}/mea_{tag}.json", "w"), indent=1)
    print(f"{sum(bool(v['code']) for v in out.values())} transforms of {len(out)}; tokens per problem "
          f"{sum(v['out_tokens'] or 0 for v in out.values()) / len(out):.0f}")


DRIVER = "\nimport sys as _s, json as _j\n_o = transform(_s.stdin.read())\nprint(_j.dumps([x for x in (_o or [])[:4] if isinstance(x, str)]))\n"


def derived(p, code):   # [(input, expected)] inherited from the public examples
    out = []
    if not code:
        return out
    for t in [t for t in p["tests"] if t["kind"] == "public"]:
        r = run_python(code + DRIVER, t["input"], timeout=10)
        if r.status != "ok":
            continue
        try:
            new = json.loads(r.stdout.strip().split("\n")[-1])
        except (ValueError, IndexError):
            continue
        out += [(x, t["output"]) for x in new if x.strip() and x.strip() != t["input"].strip()]
    return out


def evaluate(tag):
    P = {p["name"]: p for p in json.load(open(PFILE))}; V = json.load(open(VFILE)); M = json.load(open(f"{RES}/mea_{tag}.json"))
    npub = {n: sum(t["kind"] == "public" for t in p["tests"]) for n, p in P.items()}
    with ThreadPoolExecutor(32) as ex:
        D = dict(zip(M, ex.map(lambda n: derived(P[n], M[n]["code"]), M)))
    print(f"problems with derived tests: {sum(bool(v) for v in D.values())} of {len(D)}; derived tests per such problem "
          f"{sum(map(len, D.values())) / max(1, sum(bool(v) for v in D.values())):.1f}")
    S = {}   # (cond, seed) -> rows
    for c in CONDS:
        for sd in (1, 2, 3):
            f = f"{RES}/{OPRE}{c}_s{sd}.jsonl"
            if os.path.exists(f):
                S[(c, sd)] = {r["name"]: r for r in map(json.loads, open(f))}

    def flag(a):   # does a program that passes the examples fail a derived test?
        n, code = a
        for inp, exp in D[n]:
            r = run_python(code, inp, timeout=10)
            if r.status != "ok" or not tok_eq(r.stdout, exp, V[n]["tol"]):
                return True
        return False

    jobs = sorted({(n, r["code"]) for R in S.values() for n, r in R.items()
                   if n in D and D[n] and r["code"] and r["passed"] >= npub[n]})
    with ThreadPoolExecutor(32) as ex:
        F = dict(zip(jobs, ex.map(flag, jobs)))
    stat = defaultdict(lambda: [0, 0, 0, 0])   # wrong passers, flagged; correct passers, flagged
    for (c, sd), R in S.items():
        for n, r in R.items():
            if (n, r["code"]) in F and not V[n]["flag_multi"]:
                s = stat[c]
                if r["passed_all"]:
                    s[2] += 1; s[3] += F[(n, r["code"])]
                else:
                    s[0] += 1; s[1] += F[(n, r["code"])]
    tot = [sum(s[i] for s in stat.values()) for i in range(4)]
    for c, s in list(stat.items()) + [("ALL", tot)]:
        print(f"{c:15s} wrong passers flagged {s[1]}/{s[0]} ({100 * s[1] / max(1, s[0]):.0f}%) | correct passers flagged {s[3]}/{s[2]} "
              f"({100 * s[3] / max(1, s[2]):.1f}%)")
    print("selector at k = 3 (unflagged problems): first sample passing examples (+ derived tests)")
    for c in CONDS:
        Rs = [S[(c, sd)] for sd in (1, 2, 3) if (c, sd) in S]
        if len(Rs) < 3:
            continue
        names = [n for n in Rs[0] if not V[n]["flag_multi"]]
        ex_ = mea = orc = 0
        for n in names:
            rs = [R[n] for R in Rs]
            pas = [r for r in rs if r["code"] and r["passed"] >= npub[n]]
            pick1 = pas[0] if pas else rs[0]
            pas2 = [r for r in pas if not F.get((n, r["code"]), False)]
            pick2 = pas2[0] if pas2 else pick1
            ex_ += pick1["passed_all"]; mea += pick2["passed_all"]; orc += any(r["passed_all"] for r in rs)
        print(f"  {c:15s} n={len(names)}: examples {100 * ex_ / len(names):.1f}% | examples + MEA {100 * mea / len(names):.1f}% | oracle {100 * orc / len(names):.1f}%")


if __name__ == "__main__":
    (gen if sys.argv[1] == "gen" else evaluate)(sys.argv[2])
