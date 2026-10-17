"""PoC CO1 — combinatorial optimization: three LLM paradigms on the same instances.

problems (exact optimum or best-known reference from OR-Tools):
  knapsack : 0/1 knapsack, n items                      (exact DP)
  tsp      : symmetric Euclidean TSP, n cities, integer coordinates, rounded distances (OR-Tools routing + GLS reference;
             exact by DP for n <= 12)
  color    : graph colouring, minimise the number of colours (CP-SAT exact, 20 s limit)
  sched    : P||Cmax, n jobs on m identical machines, minimise makespan (CP-SAT exact, 20 s limit)
arms:
  direct    : the model outputs a solution in a fixed format (thinking off / on)
  solver    : the model writes Python that models the instance with OR-Tools and prints the solution (we run it, 30 s)
  heuristic : the model writes Python WITHOUT any solver/optimisation library (we run it, 30 s)
baselines (textbook greedy, not LLM): knapsack value/weight ratio; TSP nearest neighbour; colouring largest-degree-first;
  scheduling LPT. Metrics: feasibility, optimality gap (%), within-1% rate.
"""
import argparse
import zlib
import itertools
import json
import math
import os
import random
import re
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
from llm import chat, chat_msgs, last_block, strip_think  # noqa: E402
from sandbox import run_python
from api_shim import SHIM  # noqa: E402

RES = "/NAS/SJ/POSTECH/nlp/results"
SIZES = {"knapsack": (10, 20, 40, 80), "tsp": (8, 12, 20, 40), "color": (10, 20, 40), "sched": (10, 20, 40)}
HELDOUT = {"binpack": (10, 20, 40), "vcover": (10, 20, 40)}   # held-out problems (added after all CO findings; not tuned on)
REAL = {"cvrp": (8, 12, 16), "vrptw": (8, 12)}   # review item 3: realistic multi-constraint problem (capacitated vehicle routing), added after all findings


# ---------------- instances, references, checkers ----------------
def _routes(seq):
    routes, cur = [], []
    for v in list(seq) + [0]:
        if v == 0:
            if cur:
                routes.append(cur)
            cur = []
        else:
            cur.append(v)
    return routes


def gen(prob, n, rng):
    if prob == "vrptw":   # CVRP + time windows (travel time = rounded distance, service 10); windows built around a greedy schedule => feasible
        inst = gen("cvrp", n, rng); P, d, Q = inst["pts"], inst["dem"], inst["cap"]
        routes = _routes(greedy("cvrp", inst)); arr = [0] * len(P); end = 0
        for r_ in routes:
            t, prev = 0, 0
            for v in r_:
                t += dist(P[prev], P[v]); arr[v] = t; t += 10; prev = v
            end = max(end, t + dist(P[prev], P[0]))
        win = [(0, end + 100)] + [(max(0, arr[v] - rng.randint(10, 60)), arr[v] + rng.randint(10, 60)) for v in range(1, len(P))]
        return {**inst, "win": win, "svc": 10, "H": end + 100, "K": len(routes) + 1}
    if prob == "cvrp":   # depot = node 0 at the centre, n customers with demands 1-9, capacity 15-25, K = ceil(total/Q) + 1 vehicles
        pts = [(50, 50)] + [(rng.randint(0, 100), rng.randint(0, 100)) for _ in range(n)]
        dem = [0] + [rng.randint(1, 9) for _ in range(n)]
        Q = rng.randint(15, 25)
        return {"pts": pts, "dem": dem, "cap": Q, "K": -(-sum(dem) // Q) + 1}
    if prob == "binpack":
        return {"sizes": [rng.randint(10, 60) for _ in range(n)], "cap": 100}
    if prob == "vcover":
        p = 0.3 if n <= 20 else 0.15
        return {"n": n, "edges": [(i, j) for i in range(n) for j in range(i + 1, n) if rng.random() < p]}
    if prob == "knapsack":
        items = [(rng.randint(5, 60), rng.randint(5, 100)) for _ in range(n)]  # (weight, value)
        return {"items": items, "cap": sum(w for w, _ in items) // 3}
    if prob == "tsp":
        return {"pts": [(rng.randint(0, 100), rng.randint(0, 100)) for _ in range(n)]}
    if prob == "color":
        p = 0.3 if n <= 20 else 0.15
        return {"n": n, "edges": [(i, j) for i in range(n) for j in range(i + 1, n) if rng.random() < p]}
    return {"jobs": [rng.randint(5, 50) for _ in range(n)], "m": 3 if n <= 20 else 5}


def dist(a, b):
    return round(math.hypot(a[0] - b[0], a[1] - b[1]))


def objective(prob, inst, sol):
    """returns (feasible, value). Minimisation for tsp/color/sched, maximisation for knapsack."""
    try:
        if prob == "vrptw":
            seq = [int(x) for x in sol]; n = len(inst["pts"]) - 1; routes = _routes(seq); P = inst["pts"]
            if sorted(v for r_ in routes for v in r_) != list(range(1, n + 1)) or len(routes) > inst["K"]:
                return False, None
            for r_ in routes:
                if sum(inst["dem"][v] for v in r_) > inst["cap"]:
                    return False, None
                t, prev = 0, 0
                for v in r_:
                    t = max(t + dist(P[prev], P[v]), inst["win"][v][0])
                    if t > inst["win"][v][1]:
                        return False, None
                    t += inst["svc"]; prev = v
                if t + dist(P[prev], P[0]) > inst["H"]:
                    return False, None
            return True, sum(dist(P[a_], P[b_]) for r_ in routes for a_, b_ in zip([0] + r_, r_ + [0]))
        if prob == "cvrp":   # sol = node sequence, routes separated by depot 0 (e.g. 0 3 5 0 2 1 0); empty routes ignored
            seq = [int(x) for x in sol]; n = len(inst["pts"]) - 1
            routes, cur = [], []
            for v in seq + [0]:
                if v == 0:
                    if cur:
                        routes.append(cur)
                    cur = []
                else:
                    cur.append(v)
            if sorted(v for r_ in routes for v in r_) != list(range(1, n + 1)) or len(routes) > inst["K"]:
                return False, None
            if any(sum(inst["dem"][v] for v in r_) > inst["cap"] for r_ in routes):
                return False, None
            P = inst["pts"]
            return True, sum(dist(P[a_], P[b_]) for r_ in routes for a_, b_ in zip([0] + r_, r_ + [0]))
        if prob == "binpack":
            a = [int(x) for x in sol]
            if len(a) != len(inst["sizes"]) or any(x < 0 for x in a):
                return False, None
            loads = {}
            for i, b in enumerate(a):
                loads[b] = loads.get(b, 0) + inst["sizes"][i]
            return (all(v <= inst["cap"] for v in loads.values()), len(loads)) if all(v <= inst["cap"] for v in loads.values()) else (False, None)
        if prob == "vcover":
            S = set(int(x) for x in sol)
            if any(not 0 <= v < inst["n"] for v in S) or any(a not in S and b not in S for a, b in inst["edges"]):
                return False, None
            return True, len(S)
        if prob == "knapsack":
            S = set(int(x) for x in sol)
            ok = all(0 <= i < len(inst["items"]) for i in S) and sum(inst["items"][i][0] for i in S) <= inst["cap"]
            return ok, sum(inst["items"][i][1] for i in S)
        if prob == "tsp":
            t = [int(x) for x in sol]; n = len(inst["pts"])
            if sorted(t) != list(range(n)):
                return False, None
            return True, sum(dist(inst["pts"][t[i]], inst["pts"][t[(i + 1) % n]]) for i in range(n))
        if prob == "color":
            c = [int(x) for x in sol]
            if len(c) != inst["n"] or any(c[a] == c[b] for a, b in inst["edges"]):
                return False, None
            return True, len(set(c))
        a = [int(x) for x in sol]; m = inst["m"]
        if len(a) != len(inst["jobs"]) or any(not 0 <= x < m for x in a):
            return False, None
        loads = [0] * m
        for j, x in enumerate(a):
            loads[x] += inst["jobs"][j]
        return True, max(loads)
    except Exception:
        return False, None


def reference(prob, inst):
    from ortools.sat.python import cp_model
    if prob == "knapsack":
        cap = inst["cap"]; dp = [0] * (cap + 1)
        for w, v in inst["items"]:
            for c in range(cap, w - 1, -1):
                dp[c] = max(dp[c], dp[c - w] + v)
        return dp[cap], True
    if prob == "tsp":
        P = inst["pts"]; n = len(P)
        if n <= 12:  # Held-Karp exact
            D = [[dist(P[i], P[j]) for j in range(n)] for i in range(n)]
            best = {(1, 0): 0}
            for mask in range(1, 1 << n):
                if not mask & 1:
                    continue
                for j in range(n):
                    if (mask, j) not in best:
                        continue
                    for k in range(n):
                        if mask & (1 << k):
                            continue
                        key = (mask | (1 << k), k); val = best[(mask, j)] + D[j][k]
                        if val < best.get(key, 1 << 60):
                            best[key] = val
            full = (1 << n) - 1
            return min(best[(full, j)] + D[j][0] for j in range(1, n)), True
        from ortools.constraint_solver import pywrapcp, routing_enums_pb2
        mgr = pywrapcp.RoutingIndexManager(n, 1, 0); r = pywrapcp.RoutingModel(mgr)
        cb = r.RegisterTransitCallback(lambda i, j: dist(P[mgr.IndexToNode(i)], P[mgr.IndexToNode(j)]))
        r.SetArcCostEvaluatorOfAllVehicles(cb)
        prm = pywrapcp.DefaultRoutingSearchParameters()
        prm.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        prm.time_limit.seconds = 10
        return r.SolveWithParameters(prm).ObjectiveValue(), False
    m = cp_model.CpModel(); s = cp_model.CpSolver(); s.parameters.max_time_in_seconds = 20; s.parameters.num_workers = 8
    if prob == "vrptw":   # exact CP-SAT: multiple circuits + load + arrival-time propagation along used arcs
        P, d, Q, W, S, H = inst["pts"], inst["dem"], inst["cap"], inst["win"], inst["svc"], inst["H"]; N = len(P)
        s.parameters.max_time_in_seconds = 120
        lit = {(i, j): m.NewBoolVar(f"a{i}_{j}") for i in range(N) for j in range(N) if i != j}
        m.AddMultipleCircuit([(i, j, l) for (i, j), l in lit.items()])
        m.Add(sum(lit[0, j] for j in range(1, N)) <= inst["K"])
        load = [m.NewIntVar(d[i], Q, f"l{i}") for i in range(N)]
        T = [m.NewIntVar(W[i][0], W[i][1], f"t{i}") for i in range(N)]
        for (i, j), l in lit.items():
            if i and j:
                m.Add(load[j] >= load[i] + d[j]).OnlyEnforceIf(l)
                m.Add(T[j] >= T[i] + S + dist(P[i], P[j])).OnlyEnforceIf(l)
            elif i == 0:
                m.Add(T[j] >= dist(P[0], P[j])).OnlyEnforceIf(l)
            else:
                m.Add(T[i] + S + dist(P[i], P[0]) <= H).OnlyEnforceIf(l)
        m.Minimize(sum(dist(P[i], P[j]) * l for (i, j), l in lit.items()))
        st = s.Solve(m)
        return int(s.ObjectiveValue()), st == cp_model.OPTIMAL
    if prob == "cvrp":   # exact CP-SAT model: multiple circuits through the depot + load propagation along used arcs
        P, d, Q = inst["pts"], inst["dem"], inst["cap"]; N = len(P)
        s.parameters.max_time_in_seconds = 120
        lit = {(i, j): m.NewBoolVar(f"a{i}_{j}") for i in range(N) for j in range(N) if i != j}
        m.AddMultipleCircuit([(i, j, l) for (i, j), l in lit.items()])
        m.Add(sum(lit[0, j] for j in range(1, N)) <= inst["K"])
        load = [m.NewIntVar(d[i], Q, f"l{i}") for i in range(N)]
        for (i, j), l in lit.items():
            if i and j:
                m.Add(load[j] >= load[i] + d[j]).OnlyEnforceIf(l)
        m.Minimize(sum(dist(P[i], P[j]) * l for (i, j), l in lit.items()))
        st = s.Solve(m)
        return int(s.ObjectiveValue()), st == cp_model.OPTIMAL
    if prob == "binpack":
        S, C = inst["sizes"], inst["cap"]; n = len(S)
        x = [[m.NewBoolVar(f"x{i}_{b}") for b in range(n)] for i in range(n)]; u = [m.NewBoolVar(f"u{b}") for b in range(n)]
        for i in range(n):
            m.AddExactlyOne(x[i])
        for b in range(n):
            m.Add(sum(S[i] * x[i][b] for i in range(n)) <= C * u[b])
        for b in range(n - 1):
            m.Add(u[b] >= u[b + 1])
        m.Minimize(sum(u))
        st = s.Solve(m)
        return int(s.ObjectiveValue()), st == cp_model.OPTIMAL
    if prob == "vcover":
        x = [m.NewBoolVar(f"v{i}") for i in range(inst["n"])]
        for a, b in inst["edges"]:
            m.AddBoolOr([x[a], x[b]])
        m.Minimize(sum(x))
        st = s.Solve(m)
        return int(s.ObjectiveValue()), st == cp_model.OPTIMAL
    if prob == "color":
        n = inst["n"]; K = n
        x = [m.NewIntVar(0, K - 1, f"c{i}") for i in range(n)]; used = m.NewIntVar(1, K, "k")
        for a, b in inst["edges"]:
            m.Add(x[a] != x[b])
        for i in range(n):
            m.Add(x[i] < used)
        if n:
            m.Add(x[0] == 0)
        m.Minimize(used)
    else:
        J = inst["jobs"]; M = inst["m"]
        x = [[m.NewBoolVar(f"x{j}_{k}") for k in range(M)] for j in range(len(J))]
        mk = m.NewIntVar(0, sum(J), "mk")
        for j in range(len(J)):
            m.AddExactlyOne(x[j])
        for k in range(M):
            m.Add(sum(J[j] * x[j][k] for j in range(len(J))) <= mk)
        m.Minimize(mk)
    st = s.Solve(m)
    return int(s.ObjectiveValue()), st == cp_model.OPTIMAL


def greedy(prob, inst):
    if prob == "vrptw":   # the generator's own greedy schedule is feasible by construction
        return greedy("cvrp", inst)
    if prob == "cvrp":   # nearest neighbour, start a new route when the next customer does not fit
        P, d, Q = inst["pts"], inst["dem"], inst["cap"]; left = set(range(1, len(P))); seq, cur, load = [0], 0, 0
        while left:
            fit = [j for j in left if load + d[j] <= Q]
            if not fit:
                seq.append(0); cur, load = 0, 0; continue
            j = min(fit, key=lambda j: dist(P[cur], P[j])); seq.append(j); left.remove(j); cur = j; load += d[j]
        return seq + [0]
    if prob == "binpack":   # first-fit decreasing
        loads, a = [], [0] * len(inst["sizes"])
        for i in sorted(range(len(inst["sizes"])), key=lambda i: -inst["sizes"][i]):
            b = next((k for k, l in enumerate(loads) if l + inst["sizes"][i] <= inst["cap"]), None)
            if b is None:
                loads.append(0); b = len(loads) - 1
            loads[b] += inst["sizes"][i]; a[i] = b
        return a
    if prob == "vcover":    # repeatedly take a max-degree node
        E = set(inst["edges"]); S = []
        while E:
            deg = {}
            for a_, b_ in E:
                deg[a_] = deg.get(a_, 0) + 1; deg[b_] = deg.get(b_, 0) + 1
            v = max(deg, key=deg.get); S.append(v); E = {e for e in E if v not in e}
        return S
    if prob == "knapsack":
        order = sorted(range(len(inst["items"])), key=lambda i: -inst["items"][i][1] / inst["items"][i][0])
        S, w = [], 0
        for i in order:
            if w + inst["items"][i][0] <= inst["cap"]:
                S.append(i); w += inst["items"][i][0]
        return S
    if prob == "tsp":
        P = inst["pts"]; t = [0]; left = set(range(1, len(P)))
        while left:
            nxt = min(left, key=lambda j: dist(P[t[-1]], P[j])); t.append(nxt); left.remove(nxt)
        return t
    if prob == "color":
        n = inst["n"]; adj = [set() for _ in range(n)]
        for a, b in inst["edges"]:
            adj[a].add(b); adj[b].add(a)
        c = [-1] * n
        for v in sorted(range(n), key=lambda v: -len(adj[v])):
            used = {c[u] for u in adj[v]}
            c[v] = next(k for k in itertools.count() if k not in used)
        return c
    J = inst["jobs"]; M = inst["m"]; loads = [0] * M; a = [0] * len(J)
    for j in sorted(range(len(J)), key=lambda j: -J[j]):
        k = loads.index(min(loads)); a[j] = k; loads[k] += J[j]
    return a


# ---------------- prompts ----------------
def describe(prob, inst):
    if prob == "vrptw":
        P, d, W = inst["pts"], inst["dem"], inst["win"]
        cust = "\n".join(f"customer {i}: ({P[i][0]}, {P[i][1]}), demand {d[i]}, time window [{W[i][0]}, {W[i][1]}]" for i in range(1, len(P)))
        stdin = (f"{len(P) - 1} {inst['cap']} {inst['K']} {inst['svc']} {inst['H']}\n{P[0][0]} {P[0][1]}\n"
                 + "\n".join(f"{P[i][0]} {P[i][1]} {d[i]} {W[i][0]} {W[i][1]}" for i in range(1, len(P))) + "\n")
        return (f"Vehicle routing with capacities and time windows. A depot at ({P[0][0]}, {P[0][1]}) (node 0); {inst['K']} identical vehicles of "
                f"capacity {inst['cap']} (not all need to be used) leave the depot at time 0 and must be back by time {inst['H']}. Customers:\n{cust}\n"
                f"Travel time between two locations equals their Euclidean distance rounded to the nearest integer. A vehicle may arrive early and "
                f"wait, but must START service no later than the end of the customer's window; service takes {inst['svc']} time units. Every "
                f"customer is visited by exactly one vehicle; the total demand on a route is at most {inst['cap']}. Minimise the total travel "
                f"distance of all routes.", stdin,
                ("first line `n capacity K service_time horizon` (five integers)" if FMT_FIX else "first line `n capacity K service horizon`")
                + ", then a line `x y` (depot), then n lines `x y demand window_start window_end` (customers 1..n)",
                "all routes as one sequence of node indices separated by the depot 0, e.g. `0 3 5 0 2 1 4 0`")
    if prob == "cvrp":
        P, d = inst["pts"], inst["dem"]
        cust = "\n".join(f"customer {i}: ({P[i][0]}, {P[i][1]}), demand {d[i]}" for i in range(1, len(P)))
        stdin = f"{len(P) - 1} {inst['cap']} {inst['K']}\n{P[0][0]} {P[0][1]}\n" + "\n".join(f"{P[i][0]} {P[i][1]} {d[i]}" for i in range(1, len(P))) + "\n"
        return (f"Capacitated vehicle routing. A depot at ({P[0][0]}, {P[0][1]}) (node 0) and {inst['K']} identical vehicles of capacity "
                f"{inst['cap']} (not all need to be used). Customers:\n{cust}\nEvery route starts and ends at the depot; every customer is "
                f"visited by exactly one vehicle; the total demand on a route is at most {inst['cap']}. The distance between two locations is "
                f"their Euclidean distance rounded to the nearest integer. Minimise the total distance of all routes.", stdin,
                "first line `n capacity K`, then a line `x y` (depot), then n lines `x y demand` (customers 1..n)",
                "all routes as one sequence of node indices separated by the depot 0, e.g. `0 3 5 0 2 1 4 0`")
    if prob == "binpack":
        S = inst["sizes"]; items = ", ".join(f"item {i}: {v}" for i, v in enumerate(S))
        stdin = f"{len(S)} {inst['cap']}\n" + " ".join(map(str, S)) + "\n"
        return (f"Bin packing. Every bin has capacity {inst['cap']}. Item sizes: {items}. Put every item into a bin (bins numbered "
                f"0, 1, 2, ...) so that the total size in each bin is at most {inst['cap']}, using as FEW bins as possible.", stdin,
                "first line `n capacity`, then a line with the n item sizes", "the bin of item 0, item 1, ..., item n-1, space-separated")
    if prob == "vcover":
        e = ", ".join(f"{a}-{b}" for a, b in inst["edges"])
        stdin = f"{inst['n']} {len(inst['edges'])}\n" + "\n".join(f"{a} {b}" for a, b in inst["edges"]) + "\n"
        return (f"Minimum vertex cover. Nodes 0..{inst['n'] - 1}. Edges: {e}\nChoose a set of nodes such that every edge has at least one "
                f"chosen endpoint, with as FEW nodes as possible.", stdin,
                "first line `n m`, then m lines `a b` (edges)", "the chosen node indices (0-based), space-separated")
    if prob == "knapsack":
        items = "\n".join(f"item {i}: weight {w}, value {v}" for i, (w, v) in enumerate(inst["items"]))
        stdin = f"{len(inst['items'])} {inst['cap']}\n" + "\n".join(f"{w} {v}" for w, v in inst["items"]) + "\n"
        return (f"0/1 knapsack. Capacity {inst['cap']}. Items:\n{items}\nChoose a subset of items with total weight <= "
                f"{inst['cap']} that maximises the total value.", stdin,
                "first line `n capacity`, then n lines `weight value`", "the chosen item indices (0-based), space-separated")
    if prob == "tsp":
        pts = "\n".join(f"city {i}: ({x}, {y})" for i, (x, y) in enumerate(inst["pts"]))
        stdin = f"{len(inst['pts'])}\n" + "\n".join(f"{x} {y}" for x, y in inst["pts"]) + "\n"
        return (f"Travelling salesman. Cities:\n{pts}\nThe distance between two cities is their Euclidean distance "
                f"rounded to the nearest integer. Find a tour visiting every city exactly once and returning to the start "
                f"that minimises the total distance.", stdin, "first line n, then n lines `x y`",
                "the order of the cities (0-based indices, each exactly once), space-separated")
    if prob == "color":
        e = ", ".join(f"{a}-{b}" for a, b in inst["edges"])
        stdin = f"{inst['n']} {len(inst['edges'])}\n" + "\n".join(f"{a} {b}" for a, b in inst["edges"]) + "\n"
        return (f"Graph colouring. Nodes 0..{inst['n'] - 1}. Edges: {e}\nAssign a colour (non-negative integer) to every "
                f"node so that adjacent nodes get different colours, using as FEW distinct colours as possible.", stdin,
                "first line `n m`, then m lines `a b` (edges)", "the colour of node 0, node 1, ..., node n-1, space-separated")
    J = inst["jobs"]
    jobs = ", ".join(f"job {j}: {p}" for j, p in enumerate(J))
    stdin = f"{len(J)} {inst['m']}\n" + " ".join(map(str, J)) + "\n"
    return (f"Scheduling. {len(J)} jobs with processing times {jobs}. There are {inst['m']} identical machines "
            f"(numbered 0..{inst['m'] - 1}). Assign every job to a machine so that the makespan (the largest total "
            f"processing time on any machine) is as small as possible.", stdin,
            "first line `n m`, then a line with the n processing times", "the machine of job 0, job 1, ..., job n-1, space-separated")


API_DOC = """OR-Tools quick reference (correct usage):
CP-SAT:  from ortools.sat.python import cp_model
  m = cp_model.CpModel(); x = m.NewIntVar(lo, hi, "x"); b = m.NewBoolVar("b")
  m.Add(x != y); m.Add(sum(w[i] * b[i] for i in range(n)) <= C); m.AddExactlyOne(bs)
  m.AddMaxEquality(z, [x1, x2, x3])        # z == max(...)  (never use Python max() on variables)
  m.Minimize(z) / m.Maximize(expr); s = cp_model.CpSolver(); s.parameters.max_time_in_seconds = 20
  st = s.Solve(m); if st in (cp_model.OPTIMAL, cp_model.FEASIBLE): s.Value(x)
  constraints are built with m.Add(...) on expressions; never write `+=` inside m.Add, never use `if var:`.
Routing (TSP): from ortools.constraint_solver import pywrapcp, routing_enums_pb2
  mgr = pywrapcp.RoutingIndexManager(n, 1, 0); r = pywrapcp.RoutingModel(mgr)
  def cost(i, j): return D[mgr.IndexToNode(i)][mgr.IndexToNode(j)]
  cb = r.RegisterTransitCallback(cost); r.SetArcCostEvaluatorOfAllVehicles(cb)
  p = pywrapcp.DefaultRoutingSearchParameters()
  p.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
  p.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
  p.time_limit.seconds = 10; sol = r.SolveWithParameters(p)
  i = r.Start(0); tour = []
  while not r.IsEnd(i): tour.append(mgr.IndexToNode(i)); i = sol.Value(r.NextVar(i))
"""
API_DOC_ON = False
DOC_EXTRA = 0
DOC_OTHERS = False   # plausible distractors: append the scoped snippets of the OTHER three problems
EXTRA_CO = [   # correct but UNNEEDED CP-SAT features for these four problems (distractor dose-response, cf. geometry S4d / zebra)
    "  b = m.NewBoolVar('b'); m.Add(x == y).OnlyEnforceIf(b); m.Add(x != y).OnlyEnforceIf(b.Not())   # reified constraint\n",
    "  m.AddElement(index_var, [10, 20, 30], target_var)               # target == list[index]\n",
    "  m.AddBoolOr([b1, b2, b3]); m.AddImplication(b1, b2)              # clauses on Boolean variables\n",
    "  m.AddMultiplicationEquality(z, [x, y]); m.AddModuloEquality(r, x, 3)   # non-linear helpers\n",
    "  m.AddAllowedAssignments([x, y], [(0, 1), (1, 2)])                # table constraint\n",
    "  m.AddInverse(f_vars, g_vars)                                     # g is the inverse permutation of f\n",
    "  m.AddLinearExpressionInDomain(expr, cp_model.Domain.FromIntervals([[0, 3], [7, 9]]))   # expr in a union of intervals\n",
    "  m.AddAutomaton(vars, start_state, final_states, transitions)     # regular-language constraint\n",
]
# S4-for-CO: only the API calls this problem type needs (scoped toolbox, cf. geometry S4b)
_CPSAT = """OR-Tools CP-SAT (correct usage):
  from ortools.sat.python import cp_model
  m = cp_model.CpModel(); s = cp_model.CpSolver(); s.parameters.max_time_in_seconds = 20
"""
_SOLVE = """  st = s.Solve(m); if st in (cp_model.OPTIMAL, cp_model.FEASIBLE): read values with s.Value(v)
  build constraints with m.Add(...) on expressions; never use Python max()/if on solver variables.
"""
DOC_TASK = {
    "knapsack": _CPSAT + """  b = [m.NewBoolVar(f"b{i}") for i in range(n)]
  m.Add(sum(w[i] * b[i] for i in range(n)) <= C); m.Maximize(sum(v[i] * b[i] for i in range(n)))
""" + _SOLVE,
    "color": _CPSAT + """  c = [m.NewIntVar(0, n - 1, f"c{i}") for i in range(n)]; m.Add(c[a] != c[b])  # per edge
  k = m.NewIntVar(0, n - 1, "k"); m.AddMaxEquality(k, c); m.Minimize(k)   # k == max colour
""" + _SOLVE,
    "sched": _CPSAT + """  x = [[m.NewBoolVar(f"x{j}_{q}") for q in range(M)] for j in range(n)]; m.AddExactlyOne(x[j])  # per job
  load_q = sum(p[j] * x[j][q] for j in range(n)); z = m.NewIntVar(0, sum(p), "z"); m.Add(load_q <= z)  # per machine
  m.Minimize(z)
""" + _SOLVE,
    "tsp": API_DOC[API_DOC.index("Routing (TSP)"):],
    "cvrp": """OR-Tools routing for CVRP (correct usage):
  from ortools.constraint_solver import pywrapcp, routing_enums_pb2
  mgr = pywrapcp.RoutingIndexManager(n + 1, K, 0); r = pywrapcp.RoutingModel(mgr)    # node 0 = depot, K vehicles
  def cost(i, j): return D[mgr.IndexToNode(i)][mgr.IndexToNode(j)]
  cb = r.RegisterTransitCallback(cost); r.SetArcCostEvaluatorOfAllVehicles(cb)
  def demand(i): return dem[mgr.IndexToNode(i)]
  dcb = r.RegisterUnaryTransitCallback(demand); r.AddDimensionWithVehicleCapacity(dcb, 0, [Q] * K, True, "Load")
  p = pywrapcp.DefaultRoutingSearchParameters()
  p.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
  p.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
  p.time_limit.seconds = 10; sol = r.SolveWithParameters(p)
  for v in range(K): i = r.Start(v); route = []; then while not r.IsEnd(i): route.append(mgr.IndexToNode(i)); i = sol.Value(r.NextVar(i))
""",
    "vrptw": """OR-Tools routing for VRP with time windows + capacities (correct usage):
  from ortools.constraint_solver import pywrapcp, routing_enums_pb2
  mgr = pywrapcp.RoutingIndexManager(n + 1, K, 0); r = pywrapcp.RoutingModel(mgr)    # node 0 = depot
  def cost(i, j): return D[mgr.IndexToNode(i)][mgr.IndexToNode(j)]
  cb = r.RegisterTransitCallback(cost); r.SetArcCostEvaluatorOfAllVehicles(cb)
  def ttime(i, j): a = mgr.IndexToNode(i); return D[a][mgr.IndexToNode(j)] + (svc if a != 0 else 0)   # travel + service at the origin
  tcb = r.RegisterTransitCallback(ttime); r.AddDimension(tcb, H, H, False, "Time"); td = r.GetDimensionOrDie("Time")
  for node in range(1, n + 1): td.CumulVar(mgr.NodeToIndex(node)).SetRange(a[node], b[node])     # service start within the window
  for v in range(K): td.CumulVar(r.Start(v)).SetRange(0, 0); td.CumulVar(r.End(v)).SetRange(0, H)
  def demand(i): return dem[mgr.IndexToNode(i)]
  dcb = r.RegisterUnaryTransitCallback(demand); r.AddDimensionWithVehicleCapacity(dcb, 0, [Q] * K, True, "Load")
  p = pywrapcp.DefaultRoutingSearchParameters()
  p.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
  p.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
  p.time_limit.seconds = 10; sol = r.SolveWithParameters(p)
  for v in range(K): i = r.Start(v); route = []; then while not r.IsEnd(i): route.append(mgr.IndexToNode(i)); i = sol.Value(r.NextVar(i))
""",
    "binpack": _CPSAT + """  x = [[m.NewBoolVar(f"x{i}_{b}") for b in range(B)] for i in range(n)]; m.AddExactlyOne(x[i])  # per item
  u = [m.NewBoolVar(f"u{b}") for b in range(B)]; m.Add(sum(s[i] * x[i][b] for i in range(n)) <= C * u[b])  # per bin
  m.Minimize(sum(u))
""" + _SOLVE,
    "vcover": _CPSAT + """  x = [m.NewBoolVar(f"v{i}") for i in range(n)]; m.AddBoolOr([x[a], x[b]])   # per edge
  m.Minimize(sum(x))
""" + _SOLVE,
}


# realistic retrieval (RAG) over a small titled snippet library: every problem-specific snippet + the general CP-SAT reference +
# the 8 extra API lines. Query = the problem text. BM25 (k1=1.5, b=0.75). Titles are what real documentation pages would carry.
TITLES = {"knapsack": "0/1 knapsack: choose items under a capacity, maximise value (CP-SAT)",
          "color": "Graph colouring: minimise the number of colours, adjacent nodes differ (CP-SAT)",
          "sched": "Scheduling identical machines: assign jobs, minimise makespan (CP-SAT)",
          "tsp": "Travelling salesman / vehicle routing: tour through all cities, routing library",
          "binpack": "Bin packing: put items into bins of a capacity, minimise bins used (CP-SAT)",
          "vcover": "Minimum vertex cover: choose nodes so every edge is covered (CP-SAT)",
          "cvrp": "Capacitated vehicle routing: routes from a depot with vehicle capacities and demands, routing library",
          "vrptw": "Vehicle routing with time windows and capacities: service start within windows, routing library time dimension"}
RETRIEVE_NOTITLE = False   # harder retrieval: code-only chunks, no page titles


def _corpus():
    docs = [(f"snippet:{k}", ("" if RETRIEVE_NOTITLE else TITLES[k] + "\n") + v) for k, v in DOC_TASK.items()]
    docs.append(("general:cpsat", "CP-SAT general reference: variables, constraints, objective, solve\n" + API_DOC[:API_DOC.index("Routing (TSP)")]))
    docs += [(f"extra:{i}", "CP-SAT API: " + l) for i, l in enumerate(EXTRA_CO)]
    return docs
def _toks(t):
    return re.findall(r"[a-z]+", t.lower())
def retrieve(query, k):
    docs = _corpus(); D = [_toks(t) for _, t in docs]; N = len(D); avg = sum(map(len, D)) / N
    df = {}
    for d in D:
        for w in set(d):
            df[w] = df.get(w, 0) + 1
    q = set(_toks(query)); scores = []
    for (name, text), d in zip(docs, D):
        sc = 0.0
        for w in q:
            f = d.count(w)
            if f:
                idf = math.log(1 + (N - df[w] + 0.5) / (df[w] + 0.5))
                sc += idf * f * 2.5 / (f + 1.5 * (1 - 0.75 + 0.75 * len(d) / avg))
        scores.append((sc, name, text))
    scores.sort(key=lambda x: -x[0])
    return scores[:k]

# B4 (docs/prereg/PREREG_B4.md): constraint-level OR-Tools routing documentation, written once in the style of the official routing guide
# (6 needed topics + 6 plausible near-misses). Used by --rag_lib routing (BM25 top-K) and --droc (DRoC-style decomposed retrieval).
ROUTING_LIB = {
    "setup": ("Routing model setup: index manager, routing model, distance (transit) callback, arc cost evaluator",
              """from ortools.constraint_solver import pywrapcp, routing_enums_pb2
manager = pywrapcp.RoutingIndexManager(num_locations, num_vehicles, depot)   # depot = node index of the depot
routing = pywrapcp.RoutingModel(manager)
def distance_callback(from_index, to_index):
    return dist[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]   # convert solver indices to node indices
transit_idx = routing.RegisterTransitCallback(distance_callback)
routing.SetArcCostEvaluatorOfAllVehicles(transit_idx)   # cost of a route = sum of arc distances"""),
    "capacity": ("Capacity constraints: demand callback and a capacity dimension per vehicle",
                 """def demand_callback(from_index):
    return demands[manager.IndexToNode(from_index)]
demand_idx = routing.RegisterUnaryTransitCallback(demand_callback)
routing.AddDimensionWithVehicleCapacity(demand_idx, 0, vehicle_capacities, True, "Capacity")   # slack 0, list of capacities, start at 0"""),
    "timewindows": ("Time windows: time dimension with waiting allowed, time window range for every location and for each vehicle start",
                    """def time_callback(from_index, to_index):
    return travel_time[manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]
time_idx = routing.RegisterTransitCallback(time_callback)
routing.AddDimension(time_idx, max_waiting_time, max_time_per_vehicle, False, "Time")   # slack = allowed waiting; do not force start cumul to 0
time_dim = routing.GetDimensionOrDie("Time")
for node, (start, end) in enumerate(time_windows):
    if node == depot: continue
    time_dim.CumulVar(manager.NodeToIndex(node)).SetRange(start, end)   # service at the node starts within [start, end]
for v in range(num_vehicles):
    time_dim.CumulVar(routing.Start(v)).SetRange(depot_open, depot_open)   # vehicle departure time
    time_dim.CumulVar(routing.End(v)).SetRange(0, horizon)                 # back at the depot by the horizon"""),
    "service": ("Service times: add the service duration of a location to the travel time of every arc leaving it",
                """def time_callback(from_index, to_index):
    a = manager.IndexToNode(from_index); b = manager.IndexToNode(to_index)
    return travel_time[a][b] + service_time[a]   # service at the origin happens before travelling (depot: service 0)"""),
    "search": ("Search parameters: first solution strategy, guided local search, time limit; solving",
               """params = pywrapcp.DefaultRoutingSearchParameters()
params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
params.time_limit.FromSeconds(10)
solution = routing.SolveWithParameters(params)   # None if no solution was found"""),
    "routes": ("Reading the solution: route of each vehicle from start to end",
               """for v in range(num_vehicles):
    index = routing.Start(v); route = []
    while not routing.IsEnd(index):
        route.append(manager.IndexToNode(index))
        index = solution.Value(routing.NextVar(index))
    route.append(manager.IndexToNode(index))   # the end node (depot)"""),
    "disjunction": ("Optional visits: penalties and disjunctions so that locations may be dropped",
                    """for node in range(1, num_locations):
    routing.AddDisjunction([manager.NodeToIndex(node)], penalty)   # dropping the node costs `penalty`"""),
    "pickup": ("Pickup and delivery: pairs served by the same vehicle, pickup before delivery",
               """dist_dim = routing.GetDimensionOrDie("Distance")
for pickup, delivery in pairs:
    p = manager.NodeToIndex(pickup); d = manager.NodeToIndex(delivery)
    routing.AddPickupAndDelivery(p, d)
    routing.solver().Add(routing.VehicleVar(p) == routing.VehicleVar(d))
    routing.solver().Add(dist_dim.CumulVar(p) <= dist_dim.CumulVar(d))"""),
    "depots": ("Multiple depots: custom start and end locations for each vehicle",
               """manager = pywrapcp.RoutingIndexManager(num_locations, num_vehicles, starts, ends)   # lists of node indices, one per vehicle"""),
    "resources": ("Resource constraints at the depot: limit how many vehicles load or unload at the same time",
                  """solver = routing.solver()
intervals = [solver.FixedDurationIntervalVar(time_dim.CumulVar(routing.Start(v)), load_time, f"load{v}") for v in range(num_vehicles)]
solver.Add(solver.Cumulative(intervals, [1] * num_vehicles, depot_capacity, "depot"))"""),
    "fixedcost": ("Vehicle fixed cost: penalise every vehicle that is used, to minimise the number of vehicles",
                  """routing.SetFixedCostOfAllVehicles(fixed_cost)"""),
    "span": ("Global span cost: balance route lengths by penalising the longest route",
             """dist_dim = routing.GetDimensionOrDie("Distance")
dist_dim.SetGlobalSpanCostCoefficient(100)"""),
}


def lib_retrieve(query, k):   # BM25 over the routing documentation chunks (title + code)
    docs = [(name, t + "\n" + c) for name, (t, c) in ROUTING_LIB.items()]
    D = [_toks(t) for _, t in docs]; N = len(D); avg = sum(map(len, D)) / N
    df = {}
    for d in D:
        for w in set(d):
            df[w] = df.get(w, 0) + 1
    q = set(_toks(query)); scores = []
    for (name, text), d in zip(docs, D):
        sc = sum(math.log(1 + (N - df[w] + 0.5) / (df[w] + 0.5)) * d.count(w) * 2.5 / (d.count(w) + 1.5 * (1 - 0.75 + 0.75 * len(d) / avg))
                 for w in q if d.count(w))
        scores.append((sc, name, text))
    scores.sort(key=lambda x: -x[0])
    return scores[:k]
LIB_K = 0
DROC = False
FMT_FIX = False   # F3y: unambiguous VRPTW header field name (service_time) instead of `service horizon`
RESTATE = False

RETRIEVE_K = 0
SHOW_STDIN = False   # VRPTW follow-up: append the instance's literal stdin to the prompt (a worked example of the stated format)
DOC_AS = ""   # near-miss documentation: show the snippet of ANOTHER problem (e.g. cvrp for vrptw)


def prompt(arm, prob, inst):
    text, _, fmt, outfmt = describe(prob, inst)
    if arm == "direct":
        return f"{text}\n\nGive your final solution on the last line as `SOLUTION: {outfmt}`."
    lib = ("Use Google OR-Tools (`from ortools.sat.python import cp_model`, or `ortools.constraint_solver` routing for "
           "the TSP / vehicle routing) to model and solve it; limit the solver to 20 seconds.") if arm == "solver" else (
           "Do NOT use OR-Tools, PuLP, scipy.optimize or any other solver/optimisation library: write your own "
           "algorithm/heuristic in plain Python (it must finish within 20 seconds).")
    if LIBCHOICE and arm == "solver":   # N15: which OR-Tools solver library the program must use
        lib = LIBS[LIBCHOICE]
    if LIB_K and arm == "solver":   # B4: BM25 top-K over the routing documentation library
        hits = lib_retrieve(text, LIB_K)
        return (f"{text}\n\nWrite a Python 3 program that solves this problem for any input in the stdin format: {fmt}. "
                f"{lib} Print only {outfmt} on one line. Give the program in a single ```python code block.\n\nRetrieved documentation:\n"
                + "\n\n".join(t for _, _, t in hits))
    if RETRIEVE_K and arm == "solver":
        hits = retrieve(text, RETRIEVE_K)
        return (f"{text}\n\nWrite a Python 3 program that solves this problem for any input in the stdin format: {fmt}. "
                f"{lib} Print only {outfmt} on one line. Give the program in a single ```python code block.\n\nRetrieved documentation:\n"
                + "\n".join(t for _, _, t in hits))
    doc = ("\n\n" + (DOC_TASK[DOC_AS or prob] if API_DOC_ON == "task" else API_DOC) + "".join(EXTRA_CO[:DOC_EXTRA])
           + ("".join("\n(another problem type)\n" + DOC_TASK[o] for o in DOC_TASK if o != prob) if DOC_OTHERS else "")) if (API_DOC_ON and arm == "solver") else ""
    ex = (f"\n\nExample stdin (this instance):\n```\n{describe(prob, inst)[1]}```") if SHOW_STDIN else ""
    rs = (" Before writing the program, list the fields of the stdin format in order (one per line, with their meaning), then write the "
          "program.") if RESTATE else ""
    ad = (f"\n\nBelow is a Python program that {ADAPT[1]}. Use it as your starting point and adapt it to THIS problem (keep what "
          f"still applies, change what the new problem requires):\n```python\n{ADAPT[0]}\n```") if ADAPT else ""   # N14
    return (f"{text}\n\nWrite a Python 3 program that solves this problem for any input in the stdin format: {fmt}. "
            f"{lib} Print only {outfmt} on one line. Give the program in a single ```python code block.{rs}{ex}{doc}{ad}")


ADAPT = None   # N14: (source program, one-line description) appended to the prompt
LIBCHOICE = ""   # N15: "", free, cpsat, routing, mip
LIBS = {"free": "Use Google OR-Tools to model and solve it, with whichever of its solvers fits best (CP-SAT `ortools.sat.python.cp_model`, "
                "the routing library `ortools.constraint_solver`, or the MIP wrapper `ortools.linear_solver.pywraplp` with SCIP or CBC); "
                "limit the solver to 20 seconds.",
        "cpsat": "Use Google OR-Tools CP-SAT (`from ortools.sat.python import cp_model`) to model and solve it; limit the solver to 20 seconds.",
        "routing": "Use the Google OR-Tools routing library (`from ortools.constraint_solver import pywrapcp, routing_enums_pb2`) to model "
                   "and solve it; limit the solver to 20 seconds.",
        "mip": "Use Google OR-Tools' MIP wrapper (`from ortools.linear_solver import pywraplp`, solver SCIP or CBC) to model and solve it as "
               "a mixed-integer program; limit the solver to 20 seconds."}


def parse_solution(arm, text, stdout=None):
    if arm == "direct":
        m = re.findall(r"SOLUTION:\s*([\d\s,]+)", text)
        return re.findall(r"\d+", m[-1]) if m else None
    if stdout is None:
        return None
    lines = [l for l in stdout.strip().splitlines() if l.strip()]
    return re.findall(r"\d+", lines[-1]) if lines else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_tag", required=True)
    ap.add_argument("--arms", default="direct,solver,heuristic")
    ap.add_argument("--think", action="store_true")
    ap.add_argument("--think_budget", type=int, default=0, help="X1: budget-forced thinking (B tokens, then </think>) for the first program; repairs without thinking")
    ap.add_argument("--max_tokens", type=int, default=4096)
    ap.add_argument("--n_inst", type=int, default=6)
    ap.add_argument("--repair", type=int, default=0, help="code arms: up to R repair rounds with error/infeasibility feedback")
    ap.add_argument("--api_doc", action="store_true", help="solver arm: include a short OR-Tools API reference")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--seed", type=int, default=None, help="sampling seed (with --temperature > 0)")
    ap.add_argument("--shim", action="store_true", help="solver arm: run code under the OR-Tools misconception shim (poc/api_shim.py)")
    ap.add_argument("--probs", default="knapsack,tsp,color,sched", help="comma list (held-out: binpack,vcover) or 'all'")
    ap.add_argument("--doc_others", action="store_true", help="append the scoped snippets of the other three problems (plausible distractors)")
    ap.add_argument("--doc_extra", type=int, default=0, help="append K correct but unneeded CP-SAT API lines to the doc (dose-response)")
    ap.add_argument("--api_doc_as", default="", help="with --api_doc_task: use this problem's snippet instead (near-miss reference)")
    ap.add_argument("--retrieve_notitle", action="store_true", help="RAG: index code-only chunks (no titles): a weaker retriever")
    ap.add_argument("--retrieve", type=int, default=0, help="RAG: BM25 top-K chunks from the snippet library instead of a fixed doc")
    ap.add_argument("--rag_lib", type=int, default=0, help="B4: BM25 top-K over the routing documentation library")
    ap.add_argument("--droc", action="store_true", help="B4: DRoC-style decomposed retrieval (decompose -> per-constraint top-1 -> filter)")
    ap.add_argument("--fmt_fix", action="store_true", help="F3y: write the VRPTW header field as service_time (unambiguous)")
    ap.add_argument("--restate", action="store_true", help="B4: ask the model to list the stdin fields before writing the program")
    ap.add_argument("--show_stdin", action="store_true", help="append this instance's literal stdin to the prompt (format example)")
    ap.add_argument("--api_doc_task", action="store_true", help="solver arm: only the API calls this problem needs")
    ap.add_argument("--adapt_from", default="", help="N14: a source program file appended to the prompt as a starting point")
    ap.add_argument("--adapt_note", default="solves a related problem", help="N14: how the source program is described")
    ap.add_argument("--logprobs", action="store_true", help="N16: store the raw log-probs of the first program's tokens")
    ap.add_argument("--resume", action="store_true", help="append to an existing result file, skipping finished instances")
    ap.add_argument("--lib", default="", choices=["", "free", "cpsat", "routing", "mip"], help="N15: required OR-Tools solver library")
    a = ap.parse_args()
    global ADAPT, LIBCHOICE
    ADAPT = (open(a.adapt_from).read(), a.adapt_note) if a.adapt_from else None
    LIBCHOICE = a.lib
    global SHOW_STDIN, LIB_K, DROC, RESTATE, FMT_FIX
    SHOW_STDIN = a.show_stdin; LIB_K = a.rag_lib; DROC = a.droc; RESTATE = a.restate; FMT_FIX = a.fmt_fix
    global API_DOC_ON
    API_DOC_ON = "task" if a.api_doc_task else a.api_doc
    global RETRIEVE_K
    RETRIEVE_K = a.retrieve
    global DOC_AS
    DOC_AS = a.api_doc_as
    global RETRIEVE_NOTITLE
    RETRIEVE_NOTITLE = a.retrieve_notitle
    global DOC_EXTRA
    DOC_EXTRA = a.doc_extra
    global DOC_OTHERS
    DOC_OTHERS = a.doc_others
    ref_path = f"{RES}/co_refs.json"
    refs = json.load(open(ref_path)) if os.path.exists(ref_path) else {}
    n_refs = len(refs)
    insts = []
    for prob, ns in ({**SIZES, **HELDOUT} if a.probs == "all" else {p_: {**SIZES, **HELDOUT, **REAL}[p_] for p_ in a.probs.split(",")}).items():
        for n in ns:
            for i in range(a.n_inst):
                key = f"{prob}-{n}-{i}"
                inst = gen(prob, n, random.Random(key))
                if key not in refs:
                    val, exact = reference(prob, inst)
                    g_ok, g_val = objective(prob, inst, greedy(prob, inst))
                    refs[key] = {"ref": val, "exact": exact, "greedy": g_val}
                insts.append((key, prob, n, inst))
    if len(refs) > n_refs:   # rewrite only when new references were computed (concurrent runs read this file)
        json.dump(refs, open(ref_path, "w"))
    jobs = [(k, p, n, inst, arm) for k, p, n, inst in insts for arm in a.arms.split(",")]

    def run_code(prob, inst, arm, code, shim=None, trace=None):
        if not code:
            return None, "no_code", "no Python code block was found in your answer"
        if arm == "heuristic" and re.search(r"ortools|pulp|scipy|cvxpy|gurobi|mip\b", code):
            return None, "used_solver", "you used a solver/optimisation library, which is not allowed here"
        shim = a.shim if shim is None else shim
        r = run_python((SHIM if shim else "") + code, describe(prob, inst)[1], timeout=40, mem_bytes=4 << 30)
        err = "\n".join(l for l in r.stderr.splitlines() if not l.startswith("#SHIM:"))
        if trace is not None:
            trace.update(err=err[-300:], shim_used=sorted({l[6:] for l in r.stderr.splitlines() if l.startswith("#SHIM:")}))
        if r.status != "ok":
            return None, r.status, f"the program failed ({r.status}). stderr (last lines):\n{err[-1500:]}"
        sol = parse_solution(arm, "", r.stdout)
        if not sol:
            return None, "no_output", "the program printed no solution"
        feas, _ = objective(prob, inst, sol)
        return sol, "ok", (None if feas else "the printed solution is INFEASIBLE (it violates a constraint or has the wrong format/length)")

    def run(j):
        key, prob, n, inst, arm = j
        msgs = [{"role": "user", "content": prompt("direct" if arm == "direct_bo4" else arm, prob, inst)}]
        droc_tok, droc_info = 0, None
        if DROC and arm == "solver":   # B4: DRoC-style: decompose into constraints, retrieve per constraint, filter, then generate
            text = describe(prob, inst)[0]
            sd0 = None if a.seed is None else a.seed * 10007 + zlib.crc32(key.encode()) % 1000 + 50
            o1 = chat(f"{text}\n\nList the constraints and modelling features that an OR-Tools model of this problem needs, one short phrase "
                      f"per line, at most 6 lines, nothing else.", think=a.think, max_tokens=1024, temperature=a.temperature, seed=sd0)
            phrases = [l.strip(" -*0123456789.").strip() for l in strip_think(o1["text"] or "").splitlines() if l.strip()][:6]
            cand = []
            for ph in phrases:
                for _, name, t in lib_retrieve(ph, 1):
                    if name not in [c[0] for c in cand]:
                        cand.append((name, t))
            listing = "\n\n".join(f"SNIPPET {j + 1}:\n{t}" for j, (_, t) in enumerate(cand))
            o2 = chat(f"{text}\n\nDocumentation snippets:\n{listing}\n\nFor each snippet, decide whether it is needed to model THIS problem. "
                      f"Answer one line per snippet as `SNIPPET j: yes` or `SNIPPET j: no`.", think=a.think, max_tokens=1024,
                      temperature=a.temperature, seed=None if sd0 is None else sd0 + 1)
            keep = {int(m_.group(1)) for m_ in re.finditer(r"SNIPPET\s*(\d+)\s*:\s*yes", strip_think(o2["text"] or ""), re.I)}
            kept = [cand[j - 1] for j in sorted(keep) if 1 <= j <= len(cand)] or cand
            droc_tok = (o1["out_tokens"] or 0) + (o2["out_tokens"] or 0)
            droc_info = {"phrases": phrases, "retrieved": [c[0] for c in cand], "kept": [c[0] for c in kept]}
            _, _, fmt, outfmt = describe(prob, inst)
            libtxt = ("Use Google OR-Tools (`from ortools.sat.python import cp_model`, or `ortools.constraint_solver` routing for "
                      "the TSP / vehicle routing) to model and solve it; limit the solver to 20 seconds.")
            msgs = [{"role": "user", "content": f"{text}\n\nWrite a Python 3 program that solves this problem for any input in the stdin format: "
                     f"{fmt}. {libtxt} Print only {outfmt} on one line. Give the program in a single ```python code block.\n\nRetrieved "
                     f"documentation:\n" + "\n\n".join(t for _, t in kept)}]
        lp0 = {}
        if arm == "direct_bo4":
            o = {"out_tokens": 0, "text": "", "finish": "stop"}
        elif a.think_budget > 0:
            from run_geo_cross import budget_chat
            o = budget_chat(msgs[0]["content"], a.think_budget, max_tokens=a.max_tokens, temperature=a.temperature,
                            seed=None if a.seed is None else a.seed * 10007 + zlib.crc32(key.encode()) % 1000)
        else:
            o = chat_msgs(msgs, think=a.think, max_tokens=a.max_tokens, temperature=a.temperature,
                          seed=None if a.seed is None else a.seed * 10007 + zlib.crc32(key.encode()) % 1000, logprobs=a.logprobs)
            lp0 = {"lp": o.get("lp"), "lp_tok": o.get("lp_tok"), "text0": o["text"]} if a.logprobs else {}   # N16: first program only
        tokens, rounds = o["out_tokens"] + droc_tok, 0
        trace, code = {}, None
        if arm == "direct_bo4":   # best of 4 sampled direct answers (token-matched comparison with the code arms)
            best = (None, None)
            for k in range(4):
                ok_ = chat(prompt("direct", prob, inst), think=a.think, max_tokens=a.max_tokens, temperature=0.7, seed=17 + k)
                tokens += ok_["out_tokens"]
                cand = parse_solution("direct", ok_["text"])
                f_, v_ = objective(prob, inst, cand) if cand else (False, None)
                if f_ and (best[1] is None or (v_ > best[1] if prob == "knapsack" else v_ < best[1])):
                    best = (cand, v_)
            sol = best[0]; status = "ok" if sol else "no_feasible_of_4"
        elif arm == "direct":
            sol = parse_solution(arm, o["text"]); status = "ok" if sol else "no_answer"
        else:
            code = last_block(o["text"], ("python", "py", "python3"))
            if a.shim:   # same round-0 program without the shim, to attribute the gain
                s0 = run_code(prob, inst, arm, code, shim=False)
                trace0 = {"status0_noshim": s0[1], "feas0_noshim": s0[0] is not None and objective(prob, inst, s0[0])[0]}
            sol, status, fb = run_code(prob, inst, arm, code, trace=trace)
            if a.shim:
                trace.update(trace0, status0_shim=status, feas0_shim=sol is not None and objective(prob, inst, sol)[0])
            while fb and rounds < a.repair:
                rounds += 1
                msgs += [{"role": "assistant", "content": strip_think(o["text"] or "") or "(empty)"},   # drop thinking: ctx overflow
                         {"role": "user", "content": f"Your program did not work: {fb}\nFix it and give the complete corrected program in a single ```python code block."}]
                try:
                    o = chat_msgs(msgs, think=a.think, max_tokens=a.max_tokens, temperature=a.temperature,
                                  seed=None if a.seed is None else a.seed * 10007 + zlib.crc32(key.encode()) % 1000 + rounds)
                except Exception:   # e.g. context overflow on a late repair round: keep the last result
                    break
                tokens += o["out_tokens"]
                code = last_block(o["text"], ("python", "py", "python3"))
                sol, status, fb = run_code(prob, inst, arm, code, trace=trace)
        feas, val = objective(prob, inst, sol) if sol else (False, None)
        ref = refs[key]["ref"]
        gap = None
        if feas and val is not None:
            gap = (ref - val) / ref * 100 if prob == "knapsack" else (val - ref) / ref * 100
        return {"key": key, "prob": prob, "n": n, "arm": arm, "status": status, "feasible": feas, "value": val,
                "ref": ref, "gap": gap, "out_tokens": tokens, "repair_rounds": rounds, "finish": o["finish"],
                "code": code, **trace, **({"droc": droc_info} if droc_info else {}), **lp0}
    out_path = f"{RES}/co_{a.model_tag}.jsonl"
    prev = []
    if a.resume and os.path.exists(out_path):   # keep finished rows after a server crash (2026-10-17)
        prev = [json.loads(l) for l in open(out_path) if l.strip()]
        done = {(r["key"], r["arm"]) for r in prev}
        jobs = [j for j in jobs if (j[0], j[4]) not in done]
    with ThreadPoolExecutor(48) as ex, open(out_path, "a" if prev else "w") as f:
        for r in ex.map(run, jobs):
            f.write(json.dumps(r) + "\n"); f.flush()


if __name__ == "__main__":
    main()
