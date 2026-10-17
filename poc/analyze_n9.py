"""N9 (results/PREREG_N.md): repair at a higher effort, gpt-oss-120b, seeds 1-3 paired. On the problems whose low-effort program fails
the statement's examples: (a) low-effort repair (N2, cc_full_rep_oss120_low_s<sd>.jsonl), (b) medium-effort repair
(cc_full_rep_oss120_low_s<sd>_med.jsonl), (c) a fresh medium attempt (cc_full_oss120_medium_s<sd>.jsonl). Also the full pipelines (low,
then the fix only when the examples fail), every call's tokens counted. usage: CC_SET=full python analyze_n9.py [seeds, default 1,2,3]"""
import json, math, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("CC_SET", "full")
from repair_cc import feedback  # noqa: E402
from run_cc import PFILE, RES, VFILE  # noqa: E402

P = {p["name"]: p for p in json.load(open(PFILE))}; V = json.load(open(VFILE))
NPUB = {n: sum(t["kind"] == "public" for t in p["tests"]) for n, p in P.items()}
load = lambda f: {r["name"]: r for r in map(json.loads, open(f))}
passes = lambda r: bool(r["code"]) and r["passed"] >= NPUB[r["name"]]
tok = lambda r: r.get("out_tokens") or 0
seeds = [int(x) for x in (sys.argv[1] if len(sys.argv) > 1 else "1,2,3").split(",")]
fx = {"low repair (N2)": [0, 0, 0], "medium repair (N9)": [0, 0, 0], "fresh medium (N3)": [0, 0, 0]}
pipe = {k: [0, 0, 0] for k in ("low only", "low + low repair", "low + medium repair", "low -> fresh medium (N3)",
                               "low + medium repair -> fresh medium", "fresh medium alone")}
win = [0, 0]
for sd in seeds:
    L, M = load(f"{RES}/cc_full_oss120_low_s{sd}.jsonl"), load(f"{RES}/cc_full_oss120_medium_s{sd}.jsonl")
    RM = load(f"{RES}/cc_full_rep_oss120_low_s{sd}_med.jsonl")
    RL = load(f"{RES}/cc_full_rep_oss120_low_s{sd}.jsonl") if os.path.exists(f"{RES}/cc_full_rep_oss120_low_s{sd}.jsonl") else None   # N2 ran seeds 1-2
    for n in L:
        add = lambda d, k, ok, t: (d[k].__setitem__(0, d[k][0] + ok), d[k].__setitem__(1, d[k][1] + t), d[k].__setitem__(2, d[k][2] + 1))
        f = not passes(L[n])
        if f:
            if RL:
                add(fx, "low repair (N2)", RL[n]["passed_all"], RL[n]["repair_tokens"])
            add(fx, "medium repair (N9)", RM[n]["passed_all"], RM[n]["repair_tokens"])
            add(fx, "fresh medium (N3)", M[n]["passed_all"], tok(M[n]))
            if RM[n]["passed_all"] != M[n]["passed_all"]:
                win[0 if RM[n]["passed_all"] else 1] += 1
        t0 = tok(L[n]); c0 = L[n]["passed_all"]
        add(pipe, "low only", c0, t0)
        if RL:
            add(pipe, "low + low repair", RL[n]["passed_all"] if f else c0, t0 + (RL[n]["repair_tokens"] if f else 0))
        add(pipe, "low + medium repair", RM[n]["passed_all"] if f else c0, t0 + (RM[n]["repair_tokens"] if f else 0))
        add(pipe, "low -> fresh medium (N3)", M[n]["passed_all"] if f else c0, t0 + (tok(M[n]) if f else 0))
        if not f:
            add(pipe, "low + medium repair -> fresh medium", c0, t0)
        elif RM[n]["repaired"] and RM[n]["code"] and feedback(P[n], RM[n]["code"], V[n]["tol"]) is None:
            add(pipe, "low + medium repair -> fresh medium", RM[n]["passed_all"], t0 + RM[n]["repair_tokens"])
        else:
            add(pipe, "low + medium repair -> fresh medium", M[n]["passed_all"], t0 + RM[n]["repair_tokens"] + tok(M[n]))
        add(pipe, "fresh medium alone", M[n]["passed_all"], tok(M[n]))
print(f"seeds {seeds}: problems failing the examples at low: {fx['fresh medium (N3)'][2]} problem-seeds")
for k, (s, t, n) in fx.items():
    if not n:
        continue
    print(f"  {k:22s} (n = {n}) correct {s}/{n} ({100 * s / n:.1f}%), fix tokens {t / n / 1000:.1f}k per failed problem")
b = sum(math.comb(sum(win), i) for i in range(min(win), sum(win) + 1)) / 2 ** sum(win) * 2 if sum(win) else 1
print(f"  paired, medium repair only vs fresh medium only: {win[0]} vs {win[1]} (two-sided sign test p = {min(1, b):.2f})")
for k, (s, t, n) in pipe.items():
    if not n:
        continue
    print(f"pipeline {k:38s} (n = {n}): {100 * s / n:.1f}% @ {t / n / 1000:.1f}k tokens per problem")
