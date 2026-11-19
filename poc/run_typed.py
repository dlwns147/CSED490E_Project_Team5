"""Typed translation for templated optimization word problems (PREREG_TYPED, 11-19): the model names the problem type and writes only
the data; a fixed, verified solver does the modelling. Stored rows (11-19) showed the models read max-flow data right and model it wrong
(results/tmp_flow_closure.py: a fixed solver on the model's own table doubles accuracy).

usage: run_typed.py <tag> <seed> [--think] [--v3]   -> results/x3/typed_<tag>_s<seed>.jsonl
Problems: MAMO ComplexLP max-flow and TSP problems (the two graph templates of PREREG_TYPED), from run_nlopt.problems("mamo").
--all: every MAMO problem, not only the selected templates (addendum E).
--v3 (PREREG_TYPED addendum D, 11-19): a third type, capacitated facility location, in the same JSON menu; runs the graph problems and the
facility-location problems with the three-type prompt.
"""
import itertools
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
from llm import chat_msgs  # noqa: E402
import run_nlopt as RN  # noqa: E402

PROMPT = ("{q}\n\nDo not solve the problem. Identify its type and write its data. On the last line give one JSON object:\n"
          '{{"type": "max_flow" | "tsp" | "other", "edges": [[from, to, value], ...], "source": node, "sink": node}}\n'
          "- max_flow: each directed connection with its capacity, as stated (a connection listed in both directions is two edges); "
          "source and sink are the nodes flow starts from and must reach.\n"
          "- tsp: each directed travel cost between two places (the cost from A to B and from B to A are two edges); a tour visits every "
          "place exactly once and returns to its start; source and sink are null.\n"
          "- other: anything else; edges may be empty.\n"
          "Use the names or numbers the problem uses for the nodes.")


PROMPT3 = ("{q}\n\nDo not solve the problem. Identify its type and write its data. On the last line give one JSON object:\n"
           '{{"type": "max_flow" | "tsp" | "facility_location" | "other", ...data fields of that type...}}\n'
           '- max_flow: "edges": [[from, to, capacity], ...] (a connection listed in both directions is two edges), "source", "sink".\n'
           '- tsp: "edges": [[from, to, cost], ...] (the cost from A to B and from B to A are two edges); a tour visits every place exactly '
           "once and returns to its start.\n"
           '- facility_location: facilities that may be opened at a fixed cost, each with a supply capacity, serving customers with demands at '
           'a per-unit shipping cost: "open_cost": {{facility: cost}}, "capacity": {{facility: units}}, "demand": {{customer: units}}, '
           '"ship_cost": [[facility, customer, cost per unit], ...].\n'
           "- other: anything else; no data fields.\n"
           "Use the names or numbers the problem uses for the nodes, facilities and customers; write every number exactly as given.")


def facility(d):
    """capacitated facility location: open y_f (binary), ship x_fc >= 0 (continuous); min open + shipping s.t. demand met, x_fc <= cap_f y_f"""
    from ortools.linear_solver import pywraplp
    oc = {str(k): float(v) for k, v in d["open_cost"].items()}; cap = {str(k): float(v) for k, v in d["capacity"].items()}
    dem = {str(k): float(v) for k, v in d["demand"].items()}; sc = {(str(a), str(b)): float(c) for a, b, c in d["ship_cost"]}
    S = pywraplp.Solver.CreateSolver("SCIP")
    y = {f: S.BoolVar(f"y{f}") for f in oc}
    x = {e: S.NumVar(0, S.infinity(), f"x{e}") for e in sc if e[0] in oc and e[1] in dem}
    for c in dem:
        S.Add(sum(x[e] for e in x if e[1] == c) == dem[c])
    for f in oc:
        S.Add(sum(x[e] for e in x if e[0] == f) <= cap.get(f, 0.0) * y[f])
    S.Minimize(sum(oc[f] * y[f] for f in oc) + sum(sc[e] * x[e] for e in x))
    prm = pywraplp.MPSolverParameters(); prm.SetDoubleParam(pywraplp.MPSolverParameters.RELATIVE_MIP_GAP, 0.0)   # 11-19: SCIP's default
    return S.Objective().Value() if S.Solve(prm) == pywraplp.Solver.OPTIMAL else None                            # gap stopped 6e-5 short


def kind(q):
    ql = q.lower()
    if "exactly once" in ql:
        return "tsp"
    if "capacit" in ql and re.search(r"From (?:\w+ )?0\b", q):
        return "max_flow"
    if V3 and re.search(r"(open|opening)[^.]*(facilit|warehouse|center|store|plant)|fixed cost", ql, re.S):
        return "facility_location"
    return None


V3 = "--v3" in sys.argv


def maxflow(edges, s, t):
    nodes = sorted({str(a) for a, _, _ in edges} | {str(b) for _, b, _ in edges} | {str(s), str(t)})
    ix = {v: k for k, v in enumerate(nodes)}; n = len(nodes)
    cap = [[0.0] * n for _ in range(n)]
    for a, b, c in edges:
        cap[ix[str(a)]][ix[str(b)]] += float(c)
    s, t, flow = ix[str(s)], ix[str(t)], 0.0
    while True:
        par = {s: None}; q = [s]
        while q:
            u = q.pop(0)
            for v in range(n):
                if v not in par and cap[u][v] > 1e-9:
                    par[v] = u; q.append(v)
        if t not in par:
            return flow
        v = t; f = float("inf")
        while par[v] is not None:
            f = min(f, cap[par[v]][v]); v = par[v]
        v = t
        while par[v] is not None:
            u = par[v]; cap[u][v] -= f; cap[v][u] += f; v = u
        flow += f


def tsp(edges):
    nodes = sorted({str(a) for a, _, _ in edges} | {str(b) for _, b, _ in edges})
    c = {(str(a), str(b)): float(v) for a, b, v in edges}
    if len(nodes) > 9:
        return None
    best = None
    first, rest = nodes[0], nodes[1:]
    for perm in itertools.permutations(rest):
        tour = (first,) + perm + (first,)
        if all((tour[k], tour[k + 1]) in c for k in range(len(tour) - 1)):
            v = sum(c[(tour[k], tour[k + 1])] for k in range(len(tour) - 1))
            best = v if best is None else min(best, v)
    return best


def parse(text):
    for m in reversed(re.findall(r"\{.*\}", text or "", re.S)):
        try:
            d = json.loads(m)
            if isinstance(d, dict) and "type" in d:
                return d
        except ValueError:
            continue
    return None


def main():
    tag, seed = sys.argv[1], int(sys.argv[2]); think = "--think" in sys.argv
    P = [p for p in RN.problems("mamo") if p["id"].startswith("mamo_complex") and kind(p["q"])]
    if "--all" in sys.argv:   # addendum E: every MAMO problem (ComplexLP 211 + EasyLP 652); the model's type field is the router
        P = RN.problems("mamo")

    def run(p):
        sd = seed * 10007 + int(p["id"].rsplit("-", 1)[1])
        o = chat_msgs([{"role": "user", "content": (PROMPT3 if V3 else PROMPT).format(q=p["q"])}], think=think, max_tokens=16000 if think else 4096,
                      temperature=0.7, seed=sd)
        d = parse(o["text"]); val = None; err = None
        try:
            if d and d.get("type") == "max_flow" and d.get("edges"):
                val = maxflow(d["edges"], d["source"], d["sink"])
            elif d and d.get("type") == "tsp" and d.get("edges"):
                val = tsp(d["edges"])
            elif V3 and d and d.get("type") == "facility_location" and d.get("ship_cost"):
                val = facility(d)
        except Exception as e:  # noqa: BLE001
            err = repr(e)[:200]
        return {"id": p["id"], "kind": kind(p["q"]), "type": d.get("type") if d else None, "pred": val, "gold": p["gold"],
                "correct": val is not None and abs(val - float(p["gold"])) < 1e-6 * max(1, abs(float(p["gold"]))),
                "data": d, "err": err, "tokens": o["out_tokens"], "finish": o["finish"], "text": (o["text"] or "")[-600:] if not V3 else (o["text"] or "")[-4000:]}

    path = os.path.join(RN.RES, f"typed_{tag}_s{seed}.jsonl")
    with ThreadPoolExecutor(32) as ex, open(path, "w") as f:
        rows = []
        for r in ex.map(run, P):
            rows.append(r); f.write(json.dumps(r) + "\n"); f.flush()
    print(tag, seed, f"{len(rows)} rows, typed {sum(r['pred'] is not None for r in rows)}, tokens {sum(r['tokens'] for r in rows) / len(rows):.0f}")


if __name__ == "__main__":
    main()
