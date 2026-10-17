"""PoC B — graph algorithms described in text: does the ENCODING of a graph change LLM accuracy?

tasks: conn (are s and t connected?), sp (shortest-path length), cycle (does the graph contain a cycle?),
       bip (is the graph bipartite?)  — all with exact answers from networkx-free reference code.
encodings: edges ("0-1, 2-5"), adj ("0: 1, 4"), story (people & friendships), matrix (0/1 rows).
sizes n = 8, 16, 32 nodes.
"""
import argparse
import json
import os
import random
import re
import sys
from collections import deque
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
from llm import chat  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root (was hard-coded)
RES = f"{ROOT}/results"
NAMES = ("Alice Bob Carol Dave Erin Frank Grace Heidi Ivan Judy Karl Liam Mona Nick Olga Paul Quinn Rita Sam Tina "
         "Uma Vic Wendy Xena Yuri Zoe Adam Beth Carl Dana Eli Fay Gus Hana Igor Jade Kurt Lola").split()


def components(n, E):
    adj = [[] for _ in range(n)]
    for a, b in E:
        adj[a].append(b); adj[b].append(a)
    return adj


def bfs(adj, s):
    d = [-1] * len(adj); d[s] = 0; q = deque([s])
    while q:
        u = q.popleft()
        for v in adj[u]:
            if d[v] < 0:
                d[v] = d[u] + 1; q.append(v)
    return d


def gen(task, n, rng):
    E = set()
    if task == "cycle":
        order = list(range(n)); rng.shuffle(order)
        for i in range(1, n):  # random tree, then maybe one extra edge
            a, b = order[i], order[rng.randrange(i)]; E.add((min(a, b), max(a, b)))
        if rng.random() < 0.5:
            while True:
                a, b = rng.sample(range(n), 2)
                if (min(a, b), max(a, b)) not in E:
                    E.add((min(a, b), max(a, b))); break
    elif task == "bip":
        side = [rng.randint(0, 1) for _ in range(n)]
        while len(E) < int(1.3 * n):
            a, b = rng.sample(range(n), 2)
            if side[a] != side[b]:
                E.add((min(a, b), max(a, b)))
        if rng.random() < 0.5:  # break bipartiteness with one same-side edge
            same = [(a, b) for a in range(n) for b in range(a + 1, n) if side[a] == side[b] and (a, b) not in E]
            E.add(rng.choice(same))
    else:
        k = 2 if (task == "conn" and rng.random() < 0.5) else 1  # conn: half the graphs have 2 components
        parts = [list(range(n))[i::k] for i in range(k)]
        for p in parts:
            rng.shuffle(p)
            for i in range(1, len(p)):
                a, b = p[i], p[rng.randrange(i)]; E.add((min(a, b), max(a, b)))
        for _ in range(int(0.4 * n)):
            p = rng.choice(parts)
            if len(p) > 2:
                a, b = rng.sample(p, 2); E.add((min(a, b), max(a, b)))
    E = sorted(E, key=lambda e: rng.random())
    adj = components(n, E)
    s, t = rng.sample(range(n), 2)
    if task in ("conn", "sp"):
        d = bfs(adj, s)
        if task == "sp" and d[t] < 0:
            return gen(task, n, rng)
        ans = ("yes" if d[t] >= 0 else "no") if task == "conn" else str(d[t])
    elif task == "cycle":
        ans = "yes" if len(E) >= n else "no"   # connected graph: cycle iff |E| >= n
    else:
        col = [-1] * n; ok = True
        for st in range(n):
            if col[st] < 0:
                col[st] = 0; q = deque([st])
                while q:
                    u = q.popleft()
                    for v in adj[u]:
                        if col[v] < 0:
                            col[v] = 1 - col[u]; q.append(v)
                        elif col[v] == col[u]:
                            ok = False
        ans = "yes" if ok else "no"
    return E, s, t, ans


def render(enc, n, E, s, t, task):
    if enc == "story":
        nm = NAMES
        g = " ".join(f"{nm[a]} and {nm[b]} are friends." for a, b in E)
        who = lambda x: nm[x]  # noqa: E731
        intro = f"There are {n} people: {', '.join(nm[:n])}. {g}"
    else:
        who = str
        if enc == "edges":
            intro = f"An undirected graph has nodes 0..{n - 1} and edges: " + ", ".join(f"{a}-{b}" for a, b in E) + "."
        elif enc == "adj":
            adj = components(n, E)
            intro = f"An undirected graph with nodes 0..{n - 1}, given as adjacency lists:\n" + "\n".join(
                f"{u}: {', '.join(map(str, sorted(adj[u]))) or '(none)'}" for u in range(n))
        else:
            M = [[0] * n for _ in range(n)]
            for a, b in E:
                M[a][b] = M[b][a] = 1
            intro = f"An undirected graph with nodes 0..{n - 1}, given as an adjacency matrix (row i, column j = 1 if i and j are connected):\n" + "\n".join(" ".join(map(str, r)) for r in M)
    q = {"conn": f"Is {who(s)} connected to {who(t)} through some chain of {'friendships' if enc == 'story' else 'edges'}? Answer yes or no.",
         "sp": f"What is the minimum number of {'friendships' if enc == 'story' else 'edges'} on a path from {who(s)} to {who(t)}? Answer with a number.",
         "cycle": "Does this graph contain a cycle? Answer yes or no." if enc != "story" else "Is there a cycle of friendships (a closed chain of distinct people)? Answer yes or no.",
         "bip": "Can the nodes be split into two groups so that every edge goes between the groups (is the graph bipartite)? Answer yes or no." if enc != "story" else "Can the people be split into two teams so that no two friends are on the same team? Answer yes or no."}[task]
    return f"{intro}\n\n{q} End your reply with a line `ANSWER: <answer>`."


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_tag", required=True)
    ap.add_argument("--think", action="store_true")
    ap.add_argument("--max_tokens", type=int, default=2048)
    ap.add_argument("--n_inst", type=int, default=10)
    a = ap.parse_args()
    jobs = []
    for task in ("conn", "sp", "cycle", "bip"):
        for n in (8, 16, 32):
            for i in range(a.n_inst):
                E, s, t, ans = gen(task, n, random.Random(f"{task}-{n}-{i}"))
                for enc in ("edges", "adj", "story", "matrix"):
                    jobs.append((task, n, i, enc, render(enc, n, E, s, t, task), ans))

    def run(j):
        task, n, i, enc, prompt, ans = j
        o = chat(prompt, think=a.think, max_tokens=a.max_tokens, temperature=0.0)
        m = re.findall(r"ANSWER:\s*\**\s*([A-Za-z]+|-?\d+)", o["text"])
        pred = m[-1].lower() if m else None
        return {"task": task, "n": n, "inst": i, "enc": enc, "gold": ans, "pred": pred, "correct": pred == ans,
                "finish": o["finish"], "out_tokens": o["out_tokens"]}
    with ThreadPoolExecutor(64) as ex, open(f"{RES}/graphs_{a.model_tag}.jsonl", "w") as f:
        for r in ex.map(run, jobs):
            f.write(json.dumps(r) + "\n")


if __name__ == "__main__":
    main()
