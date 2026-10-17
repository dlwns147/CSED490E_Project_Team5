"""H5: job-shop scheduling (OR-Library la01-la40, Lawrence 1984) as a second optimisation benchmark with a different solver library (CP-SAT).
The model gets the instance in the standard format on stdin and writes a Python program (OR-Tools available, 60 s) that prints start times.
Checker: integer start times >= 0, each job's operations in the given order without overlap, each machine one operation at a time.
Gap = makespan / reference - 1, reference = our CP-SAT run (REF, 8 workers, 120 s; optimal for most la instances).
usage: python run_jssp.py prep <orlib jobshop1.txt>
       python run_jssp.py ref
       POC_BASE_URL=... [POC_REASONING_EFFORT=low] python run_jssp.py run <tag> <seed> [--max_tokens N]"""
import json, os, re, sys, zlib
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sandbox import run_python  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root (was hard-coded)
RES = f"{ROOT}/results/h5"
TLIM = 60


def prep(path):
    os.makedirs(f"{RES}/instances", exist_ok=True)
    txt = open(path).read()
    for m in re.finditer(r"instance (\S+)\s*\n\s*\++\s*\n[^\n]*\n((?:\s*\d+[^\n]*\n)+?)\s*\++", txt):
        name, body = m.group(1), m.group(2)
        if re.fullmatch(r"la\d\d", name):
            rows = [l.split() for l in body.strip().split("\n")]
            open(f"{RES}/instances/{name}.txt", "w").write("\n".join(" ".join(r) for r in rows) + "\n")
    print(sorted(os.listdir(f"{RES}/instances")))


def load(name):
    L = [list(map(int, l.split())) for l in open(f"{RES}/instances/{name}.txt").read().strip().split("\n")]
    n, m = L[0]
    jobs = [[(L[1 + j][2 * k], L[1 + j][2 * k + 1]) for k in range(m)] for j in range(n)]
    return n, m, jobs


def check(name, out):   # -> (feasible, makespan, reason)
    n, m, jobs = load(name)
    try:
        S = [list(map(int, l.replace(",", " ").split())) for l in (out or "").strip().split("\n") if l.strip()]
    except ValueError:
        return False, None, "unparsable"
    if len(S) != n or any(len(s) != m for s in S):
        return False, None, "wrong shape"
    if any(t < 0 for s in S for t in s):
        return False, None, "negative start"
    ops = {}
    for j in range(n):
        for k in range(m):
            mach, d = jobs[j][k]
            if k and S[j][k] < S[j][k - 1] + jobs[j][k - 1][1]:
                return False, None, "job order"
            ops.setdefault(mach, []).append((S[j][k], S[j][k] + d))
    for mach, iv in ops.items():
        iv.sort()
        if any(iv[i + 1][0] < iv[i][1] for i in range(len(iv) - 1)):
            return False, None, "machine overlap"
    return True, max(S[j][m - 1] + jobs[j][m - 1][1] for j in range(n)), "ok"


def names():
    return sorted(f[:-4] for f in os.listdir(f"{RES}/instances"))


STATEMENT = """Job-shop scheduling (a standard benchmark instance). The instance is given on stdin: the first line has the number of jobs n and the
number of machines m; then n lines, one per job, each with m pairs "machine duration" listing the job's operations in the order they
must be processed (machines are numbered 0..m-1; every job visits every machine exactly once).
Rules: each operation runs without interruption on its machine for its duration; a job's operations run in the given order, each
starting no earlier than the previous one ends; a machine processes at most one operation at a time. Start times are non-negative integers.
Objective: minimise the makespan (the time the last operation ends).
Output: n lines; line j has the m start times of job j's operations in the given order, separated by spaces, and nothing else.
Your program may use up to {T} seconds of wall time; Python 3 with the standard library and Google OR-Tools (ortools) is available.
Write the complete Python 3 program that reads the instance from stdin and prints the start times. Give the program in a single ```python code block."""

REF = r'''
import sys
from ortools.sat.python import cp_model
L = [list(map(int, l.split())) for l in sys.stdin.read().strip().split("\n")]
n, m = L[0]; jobs = [[(L[1 + j][2 * k], L[1 + j][2 * k + 1]) for k in range(m)] for j in range(n)]
H = sum(d for j in jobs for _, d in j); md = cp_model.CpModel(); st = {}; mi = {}
for j in range(n):
    for k, (mc, d) in enumerate(jobs[j]):
        s = md.NewIntVar(0, H, ""); st[j, k] = s; mi.setdefault(mc, []).append(md.NewIntervalVar(s, d, s + d, ""))
        if k: md.Add(s >= st[j, k - 1] + jobs[j][k - 1][1])
for v in mi.values(): md.AddNoOverlap(v)
ms = md.NewIntVar(0, H, ""); [md.Add(ms >= st[j, m - 1] + jobs[j][m - 1][1]) for j in range(n)]; md.Minimize(ms)
sv = cp_model.CpSolver(); sv.parameters.max_time_in_seconds = 120; sv.parameters.num_search_workers = 8; r = sv.Solve(md)
for j in range(n): print(*[sv.Value(st[j, k]) for k in range(m)])
print("STATUS", sv.StatusName(r), file=sys.stderr)
'''


def score(name, code, timeout):
    r = run_python(code, open(f"{RES}/instances/{name}.txt").read(), timeout=timeout, mem_bytes=8 << 30, cpu_s=64 * timeout)   # wall-time limit only
    if r.status != "ok":
        return {"feasible": False, "reason": r.status, "makespan": None, "stderr": (r.stderr or "")[-600:]}
    ok, ms, why = check(name, r.stdout)
    return {"feasible": ok, "reason": why, "makespan": ms, "stderr": (r.stderr or "")[-200:]}


def ref():
    with ThreadPoolExecutor(3) as ex:   # 3 x 8 CP-SAT workers; other runs share the CPUs
        out = dict(zip(names(), ex.map(lambda n: score(n, REF, 200), names())))
    json.dump(out, open(f"{RES}/ref.json", "w"), indent=1)
    print({n: (v["makespan"], v["stderr"].strip()[-20:]) for n, v in out.items()})


LIBS = {"cpsat": "\nUse OR-Tools CP-SAT (`from ortools.sat.python import cp_model`).",   # N15e: required solver library (JSSP_LIB env)
        "mip": "\nUse OR-Tools' MIP wrapper (`from ortools.linear_solver import pywraplp`, solver SCIP or CBC) and model the problem as a mixed-integer program.",
        "none": "\nDo NOT use OR-Tools or any other solver / optimisation library: write your own scheduling algorithm or heuristic in plain Python."}


def run(tag, seed, maxtok):
    from llm import chat, last_block

    def one(name):
        o = chat(STATEMENT.replace("{T}", str(TLIM)) + LIBS.get(os.environ.get("JSSP_LIB", ""), ""), temperature=0.7, max_tokens=maxtok,
                 seed=seed * 1000 + zlib.crc32(name.encode()) % 997)
        code = last_block(o["text"] or "", ("python", "py", "python3"))
        s = score(name, code, TLIM + 30) if code else {"feasible": False, "reason": "no code", "makespan": None, "stderr": ""}
        return {"name": name, **s, "out_tokens": o.get("out_tokens"), "code": code}

    with ThreadPoolExecutor(8) as ex:
        rows = list(ex.map(one, names()))
    with open(f"{RES}/sol_{tag}_s{seed}.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(tag, seed, f"feasible {sum(r['feasible'] for r in rows)}/{len(rows)} (gaps: analyze after the reference run)")


def rescore(tag, seed):   # re-run stored programs with the fixed CPU limit (H5 harness bug, 2026-10-14)
    f = f"{RES}/sol_{tag}_s{seed}.jsonl"
    rows = list(map(json.loads, open(f)))
    with ThreadPoolExecutor(4) as ex:
        new = list(ex.map(lambda r: score(r["name"], r["code"], TLIM + 30) if r["code"] else
                          {"feasible": False, "reason": "no code", "makespan": None, "stderr": ""}, rows))
    os.rename(f, f.replace(".jsonl", ".cpulimit_bug.jsonl"))
    with open(f, "w") as fo:
        for r, s in zip(rows, new):
            fo.write(json.dumps({**r, **s, "old_reason": r["reason"]}) + "\n")
    print(tag, seed, f"feasible {sum(r['feasible'] for r in rows)} -> {sum(s['feasible'] for s in new)} of {len(rows)} after the CPU-limit fix")


if __name__ == "__main__":
    if sys.argv[1] == "rescore":
        rescore(sys.argv[2], int(sys.argv[3])); sys.exit()
    if sys.argv[1] == "ref_missing":   # re-run the reference where it failed
        R = json.load(open(f"{RES}/ref.json"))
        for n in [n for n, v in R.items() if not v["feasible"]]:
            R[n] = score(n, REF, 200); print(n, R[n]["makespan"], R[n]["stderr"].strip()[-20:], flush=True)
        json.dump(R, open(f"{RES}/ref.json", "w"), indent=1); sys.exit()
    if sys.argv[1] == "prep":
        prep(sys.argv[2])
    elif sys.argv[1] == "ref":
        ref()
    else:
        run(sys.argv[2], int(sys.argv[3]), int(sys.argv[sys.argv.index("--max_tokens") + 1]) if "--max_tokens" in sys.argv else 6000)
