"""PoC #5 — can an LLM *execute* classic algorithms in text, and how does that scale with input size?

Synthetic instances with exact answers (so no contamination, unlimited data, controllable size):
  bfs      : shortest-path length 0 -> n-1 in a random connected unweighted graph
  knapsack : 0/1 knapsack optimum
  lis      : length of the longest strictly increasing subsequence
Modes:
  direct : answer only (no reasoning)
  cot    : simulate the algorithm step by step in text, then answer
  code   : write a Python program; we execute it on the instance (tool use)
"""
import argparse
import json
import os
import random
import re
import sys
import time
from bisect import bisect_left
from collections import deque

sys.path.insert(0, os.path.dirname(__file__))
from llm import chat_many, last_block  # noqa: E402
from sandbox import run_python  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root (was hard-coded)
RES = f"{ROOT}/results"


def gen_bfs(n, rng):
    edges = set()
    order = list(range(n))
    rng.shuffle(order)
    for i in range(1, n):  # random tree => connected
        a, b = order[i], order[rng.randrange(i)]
        edges.add((min(a, b), max(a, b)))
    while len(edges) < int(1.4 * n):
        a, b = rng.sample(range(n), 2)
        edges.add((min(a, b), max(a, b)))
    edges = sorted(edges, key=lambda e: rng.random())
    adj = [[] for _ in range(n)]
    for a, b in edges:
        adj[a].append(b); adj[b].append(a)
    dist = [-1] * n; dist[0] = 0; q = deque([0])
    while q:
        u = q.popleft()
        for v in adj[u]:
            if dist[v] < 0:
                dist[v] = dist[u] + 1; q.append(v)
    txt = (f"An undirected graph has {n} nodes numbered 0..{n - 1} and the following {len(edges)} edges:\n"
           + ", ".join(f"{a}-{b}" for a, b in edges)
           + f"\nWhat is the length (number of edges) of the shortest path from node 0 to node {n - 1}?")
    stdin = f"{n} {len(edges)}\n" + "\n".join(f"{a} {b}" for a, b in edges) + "\n"
    io = "Input format for the program: first line `n m`, then m lines `a b` (an undirected edge). Print the answer."
    return txt, stdin, io, dist[n - 1]


def gen_knapsack(n, rng):
    w = [rng.randint(1, 10) for _ in range(n)]
    v = [rng.randint(1, 20) for _ in range(n)]
    cap = max(1, sum(w) // 2)
    dp = [0] * (cap + 1)
    for wi, vi in zip(w, v):
        for c in range(cap, wi - 1, -1):
            dp[c] = max(dp[c], dp[c - wi] + vi)
    txt = (f"There are {n} items. Item i has weight w_i and value v_i:\n"
           + "\n".join(f"item {i}: w={a}, v={b}" for i, (a, b) in enumerate(zip(w, v)))
           + f"\nThe knapsack capacity is {cap}. Each item can be taken at most once. What is the maximum total value?")
    stdin = f"{n} {cap}\n" + "\n".join(f"{a} {b}" for a, b in zip(w, v)) + "\n"
    io = "Input format for the program: first line `n capacity`, then n lines `w v`. Print the answer."
    return txt, stdin, io, dp[cap]


def gen_lis(n, rng):
    a = [rng.randint(1, 100) for _ in range(n)]
    t = []
    for x in a:
        i = bisect_left(t, x)
        t[i:i + 1] = [x]
    txt = f"Sequence: {' '.join(map(str, a))}\nWhat is the length of the longest strictly increasing subsequence?"
    stdin = f"{n}\n{' '.join(map(str, a))}\n"
    io = "Input format for the program: first line n, second line the n numbers. Print the answer."
    return txt, stdin, io, len(t)


TASKS = {"bfs": gen_bfs, "knapsack": gen_knapsack, "lis": gen_lis}
MODES = {
    # direct: the model ignores "number only" and starts explaining, so force it with an assistant prefill
    "direct": ("{txt}\n\nAnswer with the number only, no explanation.", 8),
    "cot": ("{txt}\n\nSolve this by explicitly simulating the standard algorithm step by step (show the intermediate "
            "state). End with a final line of the form `ANSWER: <number>`.", 3072),
    "code": ("{txt}\n\nDo not compute the answer by hand. Instead write a Python 3 program that solves the general "
             "problem. {io} Give the program in a single ```python code block.", 1024),
}


PREFILL = {"direct": "The answer is: "}


def parse_num(text, mode):
    if mode == "direct":
        m = re.match(re.escape(PREFILL["direct"]) + r"\s*\**\s*(-?\d+)", text)
        return int(m.group(1)) if m else None
    if mode == "cot":
        m = re.findall(r"ANSWER:\s*\**\s*(-?\d+)", text)
        return int(m[-1]) if m else None
    m = re.findall(r"-?\d+", text)
    return int(m[-1]) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_tag", required=True)
    ap.add_argument("--sizes", default="6,12,24,48")
    ap.add_argument("--n_inst", type=int, default=12)
    ap.add_argument("--tasks", default="bfs,knapsack,lis")
    ap.add_argument("--modes", default="direct,code,cot")
    ap.add_argument("--workers", type=int, default=16)
    a = ap.parse_args()
    out_path = f"{RES}/exec_{a.model_tag}.jsonl"
    done = {(d["task"], d["n"], d["inst"], d["mode"]) for d in map(json.loads, open(out_path))} if os.path.exists(out_path) else set()
    jobs = []
    for t in a.tasks.split(","):
        for n in map(int, a.sizes.split(",")):
            for i in range(a.n_inst):
                inst = TASKS[t](n, random.Random(f"{t}-{n}-{i}"))
                jobs += [(t, n, i, m, inst) for m in a.modes.split(",") if (t, n, i, m) not in done]
    jobs.sort(key=lambda j: (j[3] == "cot", j[1]))  # cheap modes first
    print(len(jobs), "generations", flush=True)
    B = a.workers * 2
    for s in range(0, len(jobs), B):
        chunk, t0 = jobs[s:s + B], time.time()
        outs = chat_many([(MODES[m][0].format(txt=inst[0], io=inst[2]), {"max_tokens": MODES[m][1], "prefill": PREFILL.get(m)})
                          for _, _, _, m, inst in chunk], workers=a.workers, temperature=0.0)
        with open(out_path, "a") as f:
            for (t, n, i, m, inst), o in zip(chunk, outs):
                if m == "code":
                    code = last_block(o["text"], ("python", "py", "python3"))
                    r = run_python(code, inst[1], timeout=10) if code else None
                    pred = parse_num(r.stdout, m) if r and r.status == "ok" else None
                else:
                    pred = parse_num(o["text"], m)
                f.write(json.dumps({"task": t, "n": n, "inst": i, "mode": m, "gold": inst[3], "pred": pred,
                                    "correct": pred == inst[3], "finish": o["finish"],
                                    "out_tokens": o["out_tokens"], "response": o["text"][-3000:]}) + "\n")
        print(f"[{s + len(chunk)}/{len(jobs)}] {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
