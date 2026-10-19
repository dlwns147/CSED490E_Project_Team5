"""Offline, exploratory (not pre-registered): difficulty-based escalation vs the free examples check on contest geometry.
gpt-oss-120b, 311 validated Codeforces geometry problems, 3 seeds of medium effort (16k) and high effort (64k) stored by run_cc.py.
Policies (accuracy @ mean output tokens per problem, averaged over seeds):
  examples gate      medium; high effort only if the medium program fails the statement's examples (N8 'medium->high')
  oracle difficulty  high effort if the problem's true Codeforces rating >= T, decided before solving (an upper bound for difficulty routing)
  length as difficulty  medium; high effort if the medium answer used more than L tokens
usage: python poc/analyze_difficulty_gate.py  (CPU, seconds) -> results/difficulty_gate.log"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results", "h2")
P = {p["name"]: p for p in json.load(open(f"{RES}/cc_geometry_full.json"))}
V = json.load(open(f"{RES}/cc_valid_full.json"))
NPUB = {n: sum(t["kind"] == "public" for t in P[n]["tests"]) for n in V}
passes = lambda r: bool(r.get("code")) and r.get("passed", 0) >= NPUB[r["name"]]
tok = lambda r: r.get("out_tokens") or 0


def load(tag, sd):
    D = {}
    for line in open(f"{RES}/cc_full_{tag}_s{sd}.jsonl"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r["name"] in V:
            D[r["name"]] = r
    return D


RUNS = []
for sd in (1, 2, 3):
    M, H = load("oss120_medium", sd), load("oss120_high64k", sd)
    RUNS.append((M, H, [n for n in V if n in M and n in H]))


def evaluate(policy):
    acc = tks = 0
    for M, H, names in RUNS:
        a = t = 0
        for n in names:
            ok, tk = policy(n, M[n], H[n])
            a += ok; t += tk
        acc += 100 * a / len(names); tks += t / len(names) / 1000
    return acc / len(RUNS), tks / len(RUNS)


lines = ["always medium        %.1f%% @ %.1fk" % evaluate(lambda n, m, h: (m["passed_all"], tok(m))),
         "always high          %.1f%% @ %.1fk" % evaluate(lambda n, m, h: (h["passed_all"], tok(h))),
         "examples gate        %.1f%% @ %.1fk" % evaluate(lambda n, m, h: (m["passed_all"], tok(m)) if passes(m) else (h["passed_all"], tok(m) + tok(h)))]
for T in (1200, 1600, 1800, 2000, 2200, 2400, 2600, 2800):
    lines.append("oracle rating >= %d  %.1f%% @ %.1fk" % ((T,) + evaluate(lambda n, m, h, T=T: (h["passed_all"], tok(h)) if (P[n]["rating"] or 0) >= T else (m["passed_all"], tok(m)))))
for L in (2000, 4000, 6000, 8000, 12000):
    lines.append("length > %5d       %.1f%% @ %.1fk" % ((L,) + evaluate(lambda n, m, h, L=L: (h["passed_all"], tok(m) + tok(h)) if tok(m) > L else (m["passed_all"], tok(m)))))
open(os.path.join(ROOT, "results", "difficulty_gate.log"), "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
