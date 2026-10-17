"""N14e (results/PREREG_N14.md): two more job-shop rungs built on la01-la40 (H5), to test the transfer rule.
  tard: due dates d_j and objective = total tardiness sum_j max(0, C_j - d_j)  (no new CP-SAT fact needed)
        d_j = floor(f_j * P_j), P_j = job j's total processing time, f_j uniform in [1.2, 2.0] (seed "tard-<name>-<j>").
        Input: the H5 format + a final line with the n due dates. Output: as H5 (n lines of m start times).
  flex: flexible job-shop: every operation can run on its H5 machine or on one alternative machine (seed "flex-<name>-<j>-<k>")
        with duration round(d * u), u uniform in [0.8, 1.3]. Input: first line n m; then n lines, each with m operations written as
        "a da b db" (two alternatives). Output: n lines; line j has m pairs "machine start" for job j's operations in order.
        Objective: makespan. Needs optional intervals (a new CP-SAT fact relative to the H5 program).
Reference: CP-SAT, 8 workers, 120 s. Score: feasible; objective; within 5% of the reference (tard: within 5% or +5 time units).
usage: python run_jssp_var.py <tard|flex> prep | ref
       POC_BASE_URL=... python run_jssp_var.py <tard|flex> run <tag> <seed> [--adapt FILE --note TEXT] [--snippet] [--max_tokens N]
       python run_jssp_var.py <tard|flex> reuse <tag>   (verify once on the 8 training instances, reuse on the 32 others)"""
import json, os, random, sys, zlib
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_jssp as J  # noqa: E402
from sandbox import run_python  # noqa: E402

V = sys.argv[1]
assert V in ("tard", "flex")
D = f"{J.RES}/{V}"
TRAIN = ["la01", "la06", "la11", "la16", "la21", "la26", "la31", "la36"]


def due(name):
    n, m, jobs = J.load(name)
    return [int(random.Random(f"tard-{name}-{j}").uniform(1.2, 2.0) * sum(d for _, d in jobs[j])) for j in range(n)]


def flex(name):
    n, m, jobs = J.load(name)
    out = []
    for j in range(n):
        row = []
        for k, (a, d) in enumerate(jobs[j]):
            rng = random.Random(f"flex-{name}-{j}-{k}")
            b = rng.choice([x for x in range(m) if x != a])
            row.append((a, d, b, max(1, round(d * rng.uniform(0.8, 1.3)))))
        out.append(row)
    return n, m, out


def prep():
    os.makedirs(f"{D}/instances", exist_ok=True)
    for name in J.names():
        if V == "tard":
            txt = open(f"{J.RES}/instances/{name}.txt").read().strip() + "\n" + " ".join(map(str, due(name))) + "\n"
        else:
            n, m, ops = flex(name)
            txt = f"{n} {m}\n" + "\n".join(" ".join(f"{a} {d} {b} {e}" for a, d, b, e in row) for row in ops) + "\n"
        open(f"{D}/instances/{name}.txt", "w").write(txt)
    print(len(J.names()), "instances written to", D)


def check(name, out):   # -> (feasible, objective, reason)
    n, m, jobs = J.load(name)
    try:
        S = [list(map(int, l.replace(",", " ").split())) for l in (out or "").strip().split("\n") if l.strip()]
    except ValueError:
        return False, None, "unparsable"
    if V == "tard":
        ok, ms, why = J.check(name, out)
        if not ok:
            return ok, None, why
        dd = due(name)
        return True, sum(max(0, S[j][m - 1] + jobs[j][m - 1][1] - dd[j]) for j in range(n)), "ok"
    n, m, ops = flex(name)
    if len(S) != n or any(len(s) != 2 * m for s in S):
        return False, None, "wrong shape"
    busy = {}
    for j in range(n):
        prev_end = 0
        for k in range(m):
            mach, st = S[j][2 * k], S[j][2 * k + 1]
            a, da, b, db = ops[j][k]
            if mach not in (a, b):
                return False, None, "machine not allowed"
            d = da if mach == a else db
            if st < 0 or st < prev_end:
                return False, None, "job order"
            prev_end = st + d
            busy.setdefault(mach, []).append((st, st + d))
    for iv in busy.values():
        iv.sort()
        if any(iv[i + 1][0] < iv[i][1] for i in range(len(iv) - 1)):
            return False, None, "machine overlap"
    return True, max(S[j][2 * m - 1] + (ops[j][m - 1][1] if S[j][2 * m - 2] == ops[j][m - 1][0] else ops[j][m - 1][3]) for j in range(n)), "ok"


INTRO_TARD = J.STATEMENT.replace(
    "every job visits every machine exactly once).",
    "every job visits every machine exactly once); the LAST line has n integers d_0 ... d_{n-1}, the due dates of the jobs.").replace(
    "Objective: minimise the makespan (the time the last operation ends).",
    "Objective: minimise the total tardiness, the sum over jobs of max(0, C_j - d_j), where C_j is the time job j's last operation ends.")
INTRO_FLEX = """Flexible job-shop scheduling. The instance is given on stdin: the first line has the number of jobs n and the number of machines m;
then n lines, one per job, each with m operations in the order they must be processed; every operation is written as four integers
"a da b db": it can run EITHER on machine a with duration da OR on machine b with duration db (machines are numbered 0..m-1).
Rules: each operation is assigned to one of its two machines and runs without interruption for that machine's duration; a job's
operations run in the given order, each starting no earlier than the previous one ends; a machine processes at most one operation at
a time. Start times are non-negative integers.
Objective: minimise the makespan (the time the last operation ends).
Output: n lines; line j has, for each of job j's m operations in order, the chosen machine and the start time ("machine start"), all
separated by spaces, and nothing else.
Your program may use up to {T} seconds of wall time; Python 3 with the standard library and Google OR-Tools (ortools) is available.
Write the complete Python 3 program that reads the instance from stdin and prints the schedule. Give the program in a single ```python code block."""
STATEMENT = INTRO_TARD if V == "tard" else INTRO_FLEX
assert V == "flex" or (STATEMENT != J.STATEMENT and "total tardiness" in STATEMENT and "due dates" in STATEMENT)
SNIPPET_FLEX = """OR-Tools CP-SAT fact for alternative machines (optional intervals):
    p = model.NewBoolVar("")                                   # 1 if the operation runs on this machine
    iv = model.NewOptionalIntervalVar(start, dur, start + dur, p, "")   # only counts on this machine when p == 1
    model.AddExactlyOne([p_a, p_b])                            # exactly one alternative is chosen
    model.AddNoOverlap(intervals_of_machine)                   # per machine, over the optional intervals assigned to it"""

REF_TARD = J.REF.replace('n, m = L[0]; jobs', 'n, m = L[0]; dd = L[n + 1]; jobs').replace(
    "ms = md.NewIntVar(0, H, \"\"); [md.Add(ms >= st[j, m - 1] + jobs[j][m - 1][1]) for j in range(n)]; md.Minimize(ms)",
    "T = [md.NewIntVar(0, H, \"\") for j in range(n)]; [md.Add(T[j] >= st[j, m - 1] + jobs[j][m - 1][1] - dd[j]) for j in range(n)]; md.Minimize(sum(T))")
assert "dd[j]" in REF_TARD and "md.Minimize(sum(T))" in REF_TARD
REF_FLEX = r'''
import sys
from ortools.sat.python import cp_model
L = [list(map(int, l.split())) for l in sys.stdin.read().strip().split("\n")]
n, m = L[0]; ops = [[L[1 + j][4 * k: 4 * k + 4] for k in range(m)] for j in range(n)]
H = sum(max(o[1], o[3]) for j in ops for o in j); md = cp_model.CpModel(); per = {}; st = {}; en = {}; ch = {}
for j in range(n):
    for k, (a, da, b, db) in enumerate(ops[j]):
        s = md.NewIntVar(0, H, ""); e = md.NewIntVar(0, H, ""); st[j, k] = s; en[j, k] = e
        pa = md.NewBoolVar(""); pb = md.NewBoolVar(""); md.AddExactlyOne([pa, pb]); ch[j, k] = (pa, a, b)
        per.setdefault(a, []).append(md.NewOptionalIntervalVar(s, da, e, pa, "")); per.setdefault(b, []).append(md.NewOptionalIntervalVar(s, db, e, pb, ""))
        if k: md.Add(s >= en[j, k - 1])
for v in per.values(): md.AddNoOverlap(v)
ms = md.NewIntVar(0, H, ""); [md.Add(ms >= en[j, m - 1]) for j in range(n)]; md.Minimize(ms)
sv = cp_model.CpSolver(); sv.parameters.max_time_in_seconds = 120; sv.parameters.num_search_workers = 8; r = sv.Solve(md)
for j in range(n): print(*[x for k in range(m) for x in ((ch[j, k][1] if sv.Value(ch[j, k][0]) else ch[j, k][2]), sv.Value(st[j, k]))])
print("STATUS", sv.StatusName(r), file=sys.stderr)
'''
REF = REF_TARD if V == "tard" else REF_FLEX


def score(name, code, timeout):
    r = run_python(code, open(f"{D}/instances/{name}.txt").read(), timeout=timeout, mem_bytes=8 << 30, cpu_s=64 * timeout)
    if r.status != "ok":
        return {"feasible": False, "reason": r.status, "obj": None, "stderr": (r.stderr or "")[-600:]}
    ok, obj, why = check(name, r.stdout)
    return {"feasible": ok, "reason": why, "obj": obj, "stderr": (r.stderr or "")[-200:]}


def ref():
    with ThreadPoolExecutor(3) as ex:
        out = dict(zip(J.names(), ex.map(lambda n: score(n, REF, 200), J.names())))
    json.dump(out, open(f"{D}/ref.json", "w"), indent=1)
    print({n: (v["obj"], v["stderr"].strip()[-12:]) for n, v in out.items()})


def run(tag, seed, maxtok, adapt=None, note="", snippet=False):
    from llm import chat, last_block
    p = STATEMENT.replace("{T}", str(J.TLIM))
    if snippet and V == "flex":
        p += "\n\n" + SNIPPET_FLEX
    if adapt:
        p += (f"\n\nBelow is a Python program that {note}. Use it as your starting point and adapt it to THIS problem (keep what still "
              f"applies, change what the new problem requires):\n```python\n{open(adapt).read()}\n```")
        if "--minimal" in sys.argv:   # N14d instruction
            p += "\nChange as few lines as possible: keep every line that is unrelated to the new rule exactly as it is."

    def one(name):
        o = chat(p, temperature=0.7, max_tokens=maxtok, seed=seed * 1000 + zlib.crc32(name.encode()) % 997)
        code = last_block(o["text"] or "", ("python", "py", "python3"))
        s = score(name, code, J.TLIM + 30) if code else {"feasible": False, "reason": "no code", "obj": None, "stderr": ""}
        return {"name": name, **s, "out_tokens": o.get("out_tokens"), "finish": o.get("finish"), "code": code}

    with ThreadPoolExecutor(8) as ex:
        rows = list(ex.map(one, J.names()))
    with open(f"{D}/sol_{tag}_s{seed}.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(V, tag, seed, f"feasible {sum(r['feasible'] for r in rows)}/{len(rows)}", flush=True)


if __name__ == "__main__":
    a = sys.argv
    mt = int(a[a.index("--max_tokens") + 1]) if "--max_tokens" in a else 8000
    if a[2] == "prep":
        prep()
    elif a[2] == "ref":
        ref()
    elif a[2] == "run":
        run(a[3], int(a[4]), mt, a[a.index("--adapt") + 1] if "--adapt" in a else None, a[a.index("--note") + 1] if "--note" in a else "",
            "--snippet" in a)
