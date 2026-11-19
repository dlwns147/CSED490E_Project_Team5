"""Typed translation for templated optimization word problems (PREREG_TYPED, 11-20): the model names the problem type and writes only
the data; a fixed, verified solver does the modelling. Stored rows (11-19) showed the models read max-flow data right and model it wrong
(results/tmp_flow_closure.py: a fixed solver on the model's own table doubles accuracy).

usage: run_typed.py <tag> <seed> [--think]   -> results/x3/typed_<tag>_s<seed>.jsonl
Problems: MAMO ComplexLP max-flow and TSP problems (the two graph templates of PREREG_TYPED), from run_nlopt.problems("mamo").
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


def kind(q):
    ql = q.lower()
    if "exactly once" in ql:
        return "tsp"
    if "capacit" in ql and re.search(r"From (?:\w+ )?0\b", q):
        return "max_flow"
    return None


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

    def run(p):
        sd = seed * 10007 + int(p["id"].rsplit("-", 1)[1])
        o = chat_msgs([{"role": "user", "content": PROMPT.format(q=p["q"])}], think=think, max_tokens=16000 if think else 4096,
                      temperature=0.7, seed=sd)
        d = parse(o["text"]); val = None; err = None
        try:
            if d and d.get("type") == "max_flow" and d.get("edges"):
                val = maxflow(d["edges"], d["source"], d["sink"])
            elif d and d.get("type") == "tsp" and d.get("edges"):
                val = tsp(d["edges"])
        except Exception as e:  # noqa: BLE001
            err = repr(e)[:200]
        return {"id": p["id"], "kind": kind(p["q"]), "type": d.get("type") if d else None, "pred": val, "gold": p["gold"],
                "correct": val is not None and abs(val - float(p["gold"])) < 1e-6 * max(1, abs(float(p["gold"]))),
                "data": d, "err": err, "tokens": o["out_tokens"], "finish": o["finish"], "text": (o["text"] or "")[-600:]}

    path = os.path.join(RN.RES, f"typed_{tag}_s{seed}.jsonl")
    with ThreadPoolExecutor(32) as ex, open(path, "w") as f:
        rows = []
        for r in ex.map(run, P):
            rows.append(r); f.write(json.dumps(r) + "\n"); f.flush()
    print(tag, seed, f"{len(rows)} rows, typed {sum(r['pred'] is not None for r in rows)}, tokens {sum(r['tokens'] for r in rows) / len(rows):.0f}")


if __name__ == "__main__":
    main()
