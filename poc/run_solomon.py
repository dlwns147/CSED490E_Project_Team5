"""H3: the 56 Solomon VRPTW benchmark instances (100 customers) with best-known solutions (SINTEF table), as a hard optimisation set.
The model gets the instance file verbatim on stdin and writes a Python program (OR-Tools allowed) that prints one route per line.
Checker: every customer exactly once, load <= capacity, routes <= the vehicle count, service starts within [ready, due] with exact real
arithmetic (travel time = unrounded Euclidean distance, waiting allowed, service time at each customer), return to the depot by its due
date. Gap = distance / best-known distance - 1 (the best-known table minimises vehicles first, so a pure-distance solution can be below it).
usage: python run_solomon.py prep <zip> <sintef_page.html>
       python run_solomon.py repair <src_tag> <seed> [arm flags] [--max_tokens N]   # N2 one-round repair
       python run_solomon.py ref [arm ...]              # non-LLM references (REF_ARMS): greedy, OR-Tools 30 s / 300 s
       POC_BASE_URL=... [POC_REASONING_EFFORT=low] python run_solomon.py run <tag> <seed> [--snippet | --snippet_robust] [--parser | --parser_int] [--noexample] [--think | --think_budget B]"""
import html, json, math, os, re, sys, zipfile
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sandbox import run_python  # noqa: E402

RES = "/NAS/SJ/POSTECH/nlp/results/h3"
TLIM = 60   # seconds the program may use (stated in the prompt); killed at TLIM + 30


def prep(zpath, page):
    os.makedirs(f"{RES}/instances", exist_ok=True)
    z = zipfile.ZipFile(zpath)
    for n in z.namelist():
        if n.lower().endswith(".txt"):
            open(f"{RES}/instances/{os.path.basename(n).lower()}", "wb").write(z.read(n))
    s = open(page).read(); bks = {}
    for r in re.findall(r"<tr>(.*?)</tr>", s, re.S):
        c = [html.unescape(re.sub(r"<[^>]+>", "", x)).strip() for x in re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)]
        m = re.fullmatch(r"(?i)((?:c|r|rc)\d{3})[a-z]?", c[0]) if c else None   # "r205b": footnote letter after the name
        if m:
            bks[m.group(1).lower()] = {"vehicles": int(re.sub(r"[^\d]", "", c[1])), "distance": float(re.sub(r"[^\d.]", "", c[2])),
                                 "ref": c[3] if len(c) > 3 else "", "mark": c[2]}
    json.dump(bks, open(f"{RES}/bks.json", "w"), indent=1)
    print(len(os.listdir(f"{RES}/instances")), "instances;", len(bks), "best-known entries; missing:",
          sorted(set(f[:-4] for f in os.listdir(f"{RES}/instances")) - set(bks)))


def load(name):
    L = open(f"{RES}/instances/{name}.txt").read().split("\n")
    K, Q = map(int, L[4].split())
    rows = [list(map(float, l.split())) for l in L[9:] if len(l.split()) == 7]
    return {"K": K, "Q": Q, "xy": [(r[1], r[2]) for r in rows], "dem": [r[3] for r in rows], "ready": [r[4] for r in rows],
            "due": [r[5] for r in rows], "svc": [r[6] for r in rows]}


def check(I, out, detail=False):   # -> (feasible, distance, vehicles, reason[, detail message for repair feedback])
    res = _check(I, out)
    return res if detail else res[:4]


def _check(I, out):
    routes = []
    for line in (out or "").strip().split("\n"):
        t = line.replace(",", " ").split()
        if not t:
            continue
        try:
            r = [int(float(x)) for x in t]
        except ValueError:
            return False, None, None, "unparsable line", f"This output line is not a list of integers: {line[:200]!r}"
        r = [c for c in r if c != 0]
        if r:
            routes.append(r)
    n = len(I["xy"]) - 1
    seen = sorted(c for r in routes for c in r)
    if seen != list(range(1, n + 1)):
        miss = sorted(set(range(1, n + 1)) - set(seen)); rep = sorted({c for c in seen if seen.count(c) > 1})
        return False, None, len(routes), "customers missing or repeated", (f"Customers missing from the routes: {miss[:30]}; customers "
                                                                          f"visited more than once or out of range: {rep[:30]}")
    if len(routes) > I["K"]:
        return False, None, len(routes), "too many vehicles", f"{len(routes)} routes printed, but only {I['K']} vehicles are available."
    d = lambda a, b: math.dist(I["xy"][a], I["xy"][b])
    tot = 0.0
    for r in routes:
        if sum(I["dem"][c] for c in r) > I["Q"] + 1e-9:
            return False, None, len(routes), "capacity", (f"Route {r} carries {sum(I['dem'][c] for c in r):g} > capacity {I['Q']}.")
        t, prev = 0.0, 0
        for c in r:
            t = max(t + d(prev, c), I["ready"][c])
            if t > I["due"][c] + 1e-6:
                return False, None, len(routes), "time window", (f"On route {r[:40]}, service at customer {c} would start at {t:.4f}, "
                                                                 f"after its due date {I['due'][c]:g} (travel times are unrounded distances).")
            t += I["svc"][c]; tot += d(prev, c); prev = c
        tot += d(prev, 0)
        if t + d(prev, 0) > I["due"][0] + 1e-6:
            return False, None, len(routes), "depot due date", (f"Route {r[:40]} returns to the depot at {t + d(prev, 0):.4f}, after the "
                                                                    f"depot's due date {I['due'][0]:g}.")
    return True, tot, len(routes), "ok", ""


STATEMENT = """Vehicle routing problem with time windows (a standard Solomon benchmark instance). The instance is given on stdin in the Solomon
file format: an instance name line, then a VEHICLE section with the number of available vehicles and their capacity, then a CUSTOMER table
with columns CUST NO., XCOORD., YCOORD., DEMAND, READY TIME, DUE DATE, SERVICE TIME. Customer 0 is the depot (all vehicles start and end
there); customers 1..100 must each be visited by exactly one vehicle.
Rules: travel time between two locations equals their Euclidean distance (real-valued, NOT rounded). A vehicle leaves the depot at time 0,
may arrive early at a customer and wait until its READY TIME, must start service no later than its DUE DATE, and spends SERVICE TIME there
before leaving. Every vehicle must be back at the depot no later than the depot's DUE DATE. The total demand on a route is at most the
capacity, and at most the given number of vehicles may be used. Feasibility is checked with exact real arithmetic.
Objective: minimise the total travel distance (sum of unrounded Euclidean distances of all routes).
Output: one line per used vehicle with the customer numbers in visiting order, separated by spaces (do not print the depot), and nothing
else. Your program may use up to {T} seconds of wall time; Python 3 with the standard library and Google OR-Tools (ortools) is available.
Write the complete Python 3 program that reads the instance from stdin and prints the routes. Give the program in a single ```python code block."""

SNIPPET = """
Reference (OR-Tools routing with time windows; correct usage):
  from ortools.constraint_solver import pywrapcp, routing_enums_pb2
  mgr = pywrapcp.RoutingIndexManager(n + 1, K, 0); r = pywrapcp.RoutingModel(mgr)    # node 0 = depot
  # OR-Tools callbacks must return integers: scale real distances, e.g. S = 1000, dist_int = int(round(d * S)); for TIME use
  # math.ceil(d * S) so that every schedule feasible in integers is feasible in reals.
  def cost(i, j): return Dint[mgr.IndexToNode(i)][mgr.IndexToNode(j)]
  cb = r.RegisterTransitCallback(cost); r.SetArcCostEvaluatorOfAllVehicles(cb)
  def ttime(i, j): a = mgr.IndexToNode(i); return Tint[a][mgr.IndexToNode(j)] + svc_int[a]   # travel + service at the origin
  tcb = r.RegisterTransitCallback(ttime); r.AddDimension(tcb, H, H, False, "Time"); td = r.GetDimensionOrDie("Time")   # slack H = waiting
  for node in range(1, n + 1): td.CumulVar(mgr.NodeToIndex(node)).SetRange(ready_int[node], due_int[node])   # service START in window
  for v in range(K): td.CumulVar(r.Start(v)).SetRange(0, 0); td.CumulVar(r.End(v)).SetRange(0, due_int[0])
  def demand(i): return dem[mgr.IndexToNode(i)]
  dcb = r.RegisterUnaryTransitCallback(demand); r.AddDimensionWithVehicleCapacity(dcb, 0, [Q] * K, True, "Load")
  p = pywrapcp.DefaultRoutingSearchParameters()
  p.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
  p.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
  p.time_limit.seconds = 30; sol = r.SolveWithParameters(p)
  for v in range(K): i = r.Start(v); route = []; then while not r.IsEnd(i): route.append(mgr.IndexToNode(i)); i = sol.Value(r.NextVar(i))
"""
# robust variant: the one change that matters at this scale (our reference with PATH_CHEAPEST_ARC finds no first solution on 7 of the 56
# instances with tight windows and K vehicles, and `sol` is None); cheapest insertion finds one on all 56
SNIPPET_ROBUST = SNIPPET.replace("PATH_CHEAPEST_ARC", "PARALLEL_CHEAPEST_INSERTION   # PATH_CHEAPEST_ARC often finds NO first solution "
                                 "when windows are tight").replace("sol = r.SolveWithParameters(p)", "sol = r.SolveWithParameters(p)   "
                                 "# None if no solution was found: check it")

# H3b "format fact": a correct reader for the file (the dominant H3 failure is reading the file, not the solver)
PARSER = """
A correct reader for this input (you may use it as is):
  def read_instance():
      import sys
      lines = [l.split() for l in sys.stdin.read().splitlines()]
      K, Q = map(int, lines[4])                                    # VEHICLE section: number of vehicles, capacity
      rows = [list(map(float, t)) for t in lines[9:] if len(t) == 7]   # customer rows; row 0 is the depot
      xy = [(r[1], r[2]) for r in rows]; dem = [r[3] for r in rows]; ready = [r[4] for r in rows]
      due = [r[5] for r in rows]; svc = [r[6] for r in rows]
      return K, Q, xy, dem, ready, due, svc
"""

# H3c: the same reader returning integers (every Solomon value is an integer), to separate the format fact from the float contract
PARSER_INT = PARSER.replace("rows = [list(map(float, t))", "rows = [list(map(int, t))").replace(
    "# customer rows; row 0 is the depot", "# customer rows (all integers); row 0 is the depot")

# F2R: F2 on a standard benchmark. The robust snippet without its scaling advice, plus a needed helper whose contract is hidden or not.
SNIPPET_F2 = SNIPPET_ROBUST.replace(
    "  # OR-Tools callbacks must return integers: scale real distances, e.g. S = 1000, dist_int = int(round(d * S)); for TIME use\n"
    "  # math.ceil(d * S) so that every schedule feasible in integers is feasible in reals.\n",
    "  # OR-Tools needs integers: Tint = Dint = travel_times(xy) (helper below); ready / due / service times are integers in the file\n")
_TT = "def travel_times(xy):   # travel-time matrix between all locations, as integers (OR-Tools needs integers)\n"
HELPERS_F2 = {
    "round": _TT + "    return [[int(round(math.dist(a, b))) for b in xy] for a in xy]\n",
    "ceil": _TT + "    return [[int(math.ceil(math.dist(a, b))) for b in xy] for a in xy]\n",
    "roundwarn": _TT + ("    # rounded to the NEAREST integer: a schedule planned with these times can start service up to 0.5 per leg later\n"
                        "    # than planned under the exact (unrounded) travel times, which the checker uses\n"
                        "    return [[int(round(math.dist(a, b))) for b in xy] for a in xy]\n"),
}


def helper_block(kind):
    return "\n\nA tested helper you should use (it needs `import math`):\n```python\n" + HELPERS_F2[kind] + "```"


REF_ORTOOLS = r'''
import sys, math
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
L = sys.stdin.read().split("\n"); K, Q = map(int, L[4].split())
R = [list(map(float, l.split())) for l in L[9:] if len(l.split()) == 7]
n = len(R) - 1; S = 1000
d = [[math.dist(R[a][1:3], R[b][1:3]) for b in range(n + 1)] for a in range(n + 1)]
Dint = [[int(round(x * S)) for x in row] for row in d]; Tint = [[math.ceil(x * S) for x in row] for row in d]
ready = [int(math.ceil(r[4] * S)) for r in R]; due = [int(r[5] * S) for r in R]; svc = [int(math.ceil(r[6] * S)) for r in R]
dem = [int(r[3]) for r in R]; H = due[0]
mgr = pywrapcp.RoutingIndexManager(n + 1, K, 0); r = pywrapcp.RoutingModel(mgr)
cb = r.RegisterTransitCallback(lambda i, j: Dint[mgr.IndexToNode(i)][mgr.IndexToNode(j)]); r.SetArcCostEvaluatorOfAllVehicles(cb)
tcb = r.RegisterTransitCallback(lambda i, j: Tint[mgr.IndexToNode(i)][mgr.IndexToNode(j)] + svc[mgr.IndexToNode(i)])
r.AddDimension(tcb, H, H, False, "Time"); td = r.GetDimensionOrDie("Time")
for node in range(1, n + 1): td.CumulVar(mgr.NodeToIndex(node)).SetRange(ready[node], due[node])
for v in range(K): td.CumulVar(r.Start(v)).SetRange(0, 0); td.CumulVar(r.End(v)).SetRange(0, H)
dcb = r.RegisterUnaryTransitCallback(lambda i: dem[mgr.IndexToNode(i)]); r.AddDimensionWithVehicleCapacity(dcb, 0, [Q] * K, True, "Load")
p = pywrapcp.DefaultRoutingSearchParameters()
p.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
p.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
p.time_limit.seconds = TL
sol = r.SolveWithParameters(p)
for v in range(K):
    i = r.Start(v); route = []
    while not r.IsEnd(i):
        if mgr.IndexToNode(i): route.append(mgr.IndexToNode(i))
        i = sol.Value(r.NextVar(i))
    if route: print(*route)
'''

REF_GREEDY = r'''
import sys, math
L = sys.stdin.read().split("\n"); K, Q = map(int, L[4].split())
R = [list(map(float, l.split())) for l in L[9:] if len(l.split()) == 7]
n = len(R) - 1; d = lambda a, b: math.dist(R[a][1:3], R[b][1:3])
left = set(range(1, n + 1))
while left:   # nearest feasible neighbour, one vehicle at a time
    t, load, cur, route = 0.0, 0.0, 0, []
    while True:
        best = None
        for c in left:
            a = max(t + d(cur, c), R[c][4])
            if load + R[c][3] <= Q and a <= R[c][5] and a + R[c][6] + d(c, 0) <= R[0][5]:
                key = a - t
                if best is None or key < best[0]: best = (key, c, a)
        if best is None: break
        _, c, a = best; route.append(c); left.discard(c); t = a + R[c][6]; load += R[c][3]; cur = c
    if not route: break
    print(*route)
'''


def names():
    return sorted(f[:-4] for f in os.listdir(f"{RES}/instances"))


def score(name, code, timeout):
    I = load(name); inp = open(f"{RES}/instances/{name}.txt").read().replace("\r\n", "\n")   # the distributed files use CRLF
    r = run_python(code, inp, timeout=timeout, mem_bytes=4 << 30)
    if r.status != "ok":
        return {"feasible": False, "reason": r.status, "distance": None, "vehicles": None}
    ok, dist, veh, why = check(I, r.stdout)
    return {"feasible": ok, "reason": why, "distance": dist, "vehicles": veh}


REF_ARMS = {"greedy": (REF_GREEDY, 120),
            "ortools30": (REF_ORTOOLS.replace("TL", "30"), 120),   # the documentation's first-solution strategy (PATH_CHEAPEST_ARC)
            "ortools30_ins": (REF_ORTOOLS.replace("TL", "30").replace("PATH_CHEAPEST_ARC", "PARALLEL_CHEAPEST_INSERTION"), 120),
            "ortools300_ins": (REF_ORTOOLS.replace("TL", "300").replace("PATH_CHEAPEST_ARC", "PARALLEL_CHEAPEST_INSERTION"), 420)}


def ref(arms):
    bks = json.load(open(f"{RES}/bks.json"))
    out = json.load(open(f"{RES}/ref.json")) if os.path.exists(f"{RES}/ref.json") else {}

    def one(a):
        name, arm = a
        return name, arm, score(name, REF_ARMS[arm][0], REF_ARMS[arm][1])

    with ThreadPoolExecutor(16) as ex:
        for name, arm, s in ex.map(one, [(n, a) for n in names() for a in arms]):
            out.setdefault(arm, {})[name] = s
    json.dump(out, open(f"{RES}/ref.json", "w"), indent=1)
    for arm, D in out.items():
        g = [D[n]["distance"] / bks[n]["distance"] - 1 for n in D if D[n]["feasible"]]
        print(f"{arm}: feasible {sum(v['feasible'] for v in D.values())}/{len(D)}; mean gap to the best-known (vehicles-first) distance "
              f"{100 * sum(g) / max(1, len(g)):.2f}% (n={len(g)}); reasons {sorted(set(v['reason'] for v in D.values()))}")


def run(tag, seed, mode):
    from llm import chat, last_block
    import zlib

    def one(name):
        prompt = STATEMENT.replace("{T}", str(TLIM))
        if not mode.get("noexample"):   # 2026-10-14 amendment: show the exact layout (first 12 lines of this instance's file, verbatim)
            head = "\n".join(open(f"{RES}/instances/{name}.txt").read().replace("\r\n", "\n").split("\n")[:12])
            prompt += "\n\nThe first 12 lines of this instance's input, verbatim (header lines, blank lines, then one row per customer):\n```\n" + head + "\n```"
        prompt += (PARSER_INT if mode.get("parser_int") else PARSER if mode.get("parser") else "") + {"docs": SNIPPET, "robust": SNIPPET_ROBUST, "f2": SNIPPET_F2}.get(mode.get("snippet"), "") + (helper_block(mode["helper"]) if mode.get("helper") else "")
        sd = seed * 1000 + zlib.crc32(name.encode()) % 997
        if mode.get("think_budget"):
            from run_geo_cross import budget_chat
            o = budget_chat(prompt, mode["think_budget"], max_tokens=6000, temperature=0.7, seed=sd)
        else:
            o = chat(prompt, think=mode.get("think", False), max_tokens=mode.get("max_tokens", 6000), temperature=0.7, seed=sd)
        code = last_block(o["text"] or "", ("python", "py", "python3"))
        s = score(name, code, TLIM + 30) if code else {"feasible": False, "reason": "no code", "distance": None, "vehicles": None}
        return {"name": name, **s, "out_tokens": o.get("out_tokens"), "finish": o.get("finish"), "code": code,
                "text": (o.get("text") or "")[-4000:]}

    only = [x for x in os.environ.get("SOLOMON_ONLY", "").split(",") if x]   # V1s: generate for a subset (the mining instances) only
    with ThreadPoolExecutor(8) as ex:   # each program may use a CPU core for 60 s; several lanes share the machine
        rows = list(ex.map(one, [n for n in names() if not only or n in only]))
    with open(f"{RES}/sol_{tag}_s{seed}.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(tag, seed, f"feasible {sum(r['feasible'] for r in rows)}/{len(rows)}")


def repair(src, seed, mode):
    """N2 (docs/prereg/PREREG_N.md): one repair round for programs that crash or are infeasible on the actual instance (feasibility needs no
    optimum). Feedback = the last 15 lines of the error, or the violated constraint. Same prompt arms as the source run."""
    from llm import chat, last_block
    import zlib
    rows = {r["name"]: r for r in map(json.loads, open(f"{RES}/sol_{src}_s{seed}.jsonl"))}

    def one(name):
        r = rows[name]; base = {"name": name, "orig_feasible": r["feasible"], "orig_tokens": r.get("out_tokens") or 0}
        if r["feasible"]:
            return {**base, "repaired": False, "feasible": True, "distance": r["distance"], "vehicles": r["vehicles"], "reason": "ok", "repair_tokens": 0}
        inp = open(f"{RES}/instances/{name}.txt").read().replace("\r\n", "\n")
        if not r["code"]:
            fb = "Your previous reply did not contain a complete program in a ```python code block."
        else:
            x = run_python(r["code"], inp, timeout=TLIM + 30, mem_bytes=4 << 30)
            if x.status == "tle":
                fb = f"Your program did not finish within {TLIM + 30} seconds on this instance."
            elif x.status != "ok":
                fb = "Your program crashed on this instance:\n" + "\n".join((x.stderr or "").strip().split("\n")[-15:])[-2500:]
            else:
                fb = "Your program's output is not a feasible solution: " + check(load(name), x.stdout, detail=True)[4]
        prompt = STATEMENT.replace("{T}", str(TLIM))
        if not mode.get("noexample"):
            head = "\n".join(inp.split("\n")[:12])
            prompt += "\n\nThe first 12 lines of this instance's input, verbatim (header lines, blank lines, then one row per customer):\n```\n" + head + "\n```"
        prompt += (PARSER_INT if mode.get("parser_int") else PARSER if mode.get("parser") else "") + {"docs": SNIPPET, "robust": SNIPPET_ROBUST, "f2": SNIPPET_F2}.get(mode.get("snippet"), "") + (helper_block(mode["helper"]) if mode.get("helper") else "")
        prompt += (f"\n\nYour previous program:\n```python\n{r['code']}\n```\n" if r["code"] else "\n") + "\n" + fb + \
            "\n\nFind the mistake and fix it. Give the complete corrected program in a single ```python code block."
        o = chat(prompt, max_tokens=mode.get("max_tokens", 6000), temperature=0.7, seed=9000 + seed * 1000 + zlib.crc32(name.encode()) % 997)
        code = last_block(o["text"] or "", ("python", "py", "python3"))
        s = score(name, code, TLIM + 30) if code else {"feasible": False, "reason": "no code", "distance": None, "vehicles": None}
        return {**base, "repaired": True, **s, "repair_tokens": o.get("out_tokens") or 0, "feedback": fb[:300], "code": code}

    with ThreadPoolExecutor(8) as ex:
        out = list(ex.map(one, names()))
    with open(f"{RES}/sol_rep_{src}_s{seed}.jsonl", "w") as f:
        for r in out:
            f.write(json.dumps(r) + "\n")
    print(src, seed, f"feasible {sum(r['orig_feasible'] for r in out)} -> {sum(r['feasible'] for r in out)} of {len(out)} after one repair round")


if __name__ == "__main__":
    if sys.argv[1] == "prep":
        prep(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "ref":
        ref(sys.argv[2:] or list(REF_ARMS))
    elif sys.argv[1] == "repair":   # python run_solomon.py repair <src_tag> <seed> [same arm flags as the source run] [--max_tokens N]
        m = {"snippet": "docs" if "--snippet" in sys.argv else ("robust" if "--snippet_robust" in sys.argv else None),
             "noexample": "--noexample" in sys.argv, "parser": "--parser" in sys.argv, "parser_int": "--parser_int" in sys.argv}
        if "--max_tokens" in sys.argv:
            m["max_tokens"] = int(sys.argv[sys.argv.index("--max_tokens") + 1])
        repair(sys.argv[2], int(sys.argv[3]), m)
    else:
        mode = {"snippet": "docs" if "--snippet" in sys.argv else ("robust" if "--snippet_robust" in sys.argv else None),
                "noexample": "--noexample" in sys.argv, "parser": "--parser" in sys.argv, "parser_int": "--parser_int" in sys.argv}
        if "--helper" in sys.argv:   # F2R: --helper round | ceil | roundwarn (uses the f2 snippet)
            mode.update(snippet="f2", helper=sys.argv[sys.argv.index("--helper") + 1])
        if "--think" in sys.argv:
            mode.update(think=True, max_tokens=16000)
        if "--think_budget" in sys.argv:
            mode["think_budget"] = int(sys.argv[sys.argv.index("--think_budget") + 1])
        if "--max_tokens" in sys.argv:
            mode["max_tokens"] = int(sys.argv[sys.argv.index("--max_tokens") + 1])
        run(sys.argv[2], int(sys.argv[3]), mode)
