"""A1 (FINDINGS 2026-10-13, pre-registered): behavioural audit of every stdin format string for ambiguity.
Each model writes a program that ONLY parses stdin per the stated format and prints JSON (one key per field); we run it on a real stdin and
compare the multiset of numbers in the JSON with the numbers in stdin. pass / omitted_counts (only count fields missing) / fail.
usage: POC_BASE_URL=... [POC_REASONING_EFFORT=low] python format_audit.py <model_tag> [samples=3]"""
import json, os, random, re, sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_co as C  # noqa: E402
import run_geo as G  # noqa: E402
from llm import chat, last_block  # noqa: E402
from sandbox import run_python  # noqa: E402

RES = "/NAS/SJ/POSTECH/nlp/results"
GEO = {"hull": 10, "area2": 8, "pip": 8, "segs": 6, "close": 10, "convex": 8, "tri": 10, "overlap": 8, "lattice": 8, "rectunion": 5,
       "clip": 6, "delaunay": 8, "diameter": 12}
CO = {"knapsack": 10, "tsp": 8, "color": 10, "sched": 10, "binpack": 10, "vcover": 10, "cvrp": 8, "vrptw": 8}


def cases():
    out = []
    for t, n in GEO.items():
        rng = random.Random(f"audit-{t}")
        x = G.variants(t, G.base_instance(t, n, rng), rng)["identity"]
        q, stdin, fmt = G.render(t, x)
        out.append((f"geo:{t}", q, fmt, stdin, None))
    for p, n in CO.items():
        inst = C.gen(p, n, random.Random(f"audit-{p}"))
        for fix in ((False, True) if p == "vrptw" else (False,)):
            C.FMT_FIX = fix
            text, stdin, fmt, _ = C.describe(p, inst)
            out.append((f"co:{p}" + (":service_time" if fix else ""), text, fmt, stdin, None))
    C.FMT_FIX = False
    return out


def nums(s):
    return [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", s)]


def flat(o):
    if isinstance(o, bool):
        return []
    if isinstance(o, (int, float)):
        return [float(o)]
    if isinstance(o, str):
        return nums(o)
    if isinstance(o, dict):
        return [v for x in o.values() for v in flat(x)]
    if isinstance(o, (list, tuple)):
        return [v for x in o for v in flat(x)]
    return []


def count_values(stdin):   # benign omissions: standalone single-number lines and the leading n of a multi-number first line
    lines = [l for l in stdin.strip().split("\n") if l.strip()]
    v = [nums(l)[0] for l in lines if len(nums(l)) == 1]
    first = nums(lines[0])
    if len(first) > 1:
        v.append(first[0])
    return Counter(v)


def judge(stdin, out):
    try:
        js = json.loads(out[out.index("{"): out.rindex("}") + 1])
    except Exception:
        return "no_json"
    want, got = Counter(nums(stdin)), Counter(flat(js))
    if want == got:
        return "pass"
    missing, extra = want - got, got - want
    if not extra and not (missing - count_values(stdin)):
        return "omitted_counts"
    return "fail"


def one(job):
    name, text, fmt, stdin, _ = job[0]; sd = job[1]
    p = (f"{text}\n\nThe input arrives on stdin in this format: {fmt}.\nWrite a Python 3 program that ONLY parses stdin according to this "
         f"format and prints a single JSON object with one key per field of the format (use the field names from the format; lists for "
         f"repeated records). Do not solve the problem. Give the program in a single ```python code block.")
    o = chat(p, think=False, max_tokens=8000, temperature=0.7, seed=sd)
    code = last_block(o["text"], ("python", "py", "python3"))
    if not code:
        return name, sd, "no_code", ""
    r = run_python(code, stdin, timeout=10)
    return name, sd, (judge(stdin, r.stdout) if r.status == "ok" else "crash"), (r.stdout if r.status == "ok" else r.stderr[-600:]) + "\n#CODE\n" + code


if __name__ == "__main__":
    tag = sys.argv[1]; S = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    jobs = [(c, sd) for c in cases() for sd in range(1, S + 1)]
    with ThreadPoolExecutor(32) as ex:
        res = list(ex.map(one, jobs))
    json.dump([{"format": n, "seed": s, "verdict": v, "out": o} for n, s, v, o in res], open(f"{RES}/format_audit_{tag}.json", "w"), indent=0)
    by = {}
    for n, s, v, o in res:
        by.setdefault(n, []).append(v)
    for n, vs in by.items():
        print(f"{tag:10s} {n:24s} {' '.join(vs)}")
