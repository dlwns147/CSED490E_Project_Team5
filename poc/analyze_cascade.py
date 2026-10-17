"""N3 (results/PREREG_N.md): escalation cascade with the statement's examples as the acceptance check, offline on the H2c Part B
samples. Stage 1 = cheap mode seed s; if its program passes the public examples, accept; otherwise run stage 2 = expensive mode seed s
and take it. Cost = stage-1 tokens on every problem + stage-2 tokens on escalated problems. Compared with each mode alone and with
cheap mode best-of-2 + example check. Averaged over the seeds both modes have.
usage: python analyze_cascade.py"""
import json, os

RES = "/NAS/SJ/POSTECH/nlp/results/h2"
P = {p["name"]: p for p in json.load(open(f"{RES}/cc_geometry_full.json"))}
NPUB = {n: sum(t["kind"] == "public" for t in p["tests"]) for n, p in P.items()}


def load(tag, sd):
    f = f"{RES}/cc_full_{tag}_s{sd}.jsonl"
    return {r["name"]: r for r in map(json.loads, open(f))} if os.path.exists(f) else None


passes = lambda r: bool(r["code"]) and r["passed"] >= NPUB[r["name"]]
tok = lambda r: r.get("out_tokens") or 0
for cheap, dear in (("q32b_plain", "q32b_think1024"), ("oss20_low", "oss20_medium"), ("oss120_low", "oss120_medium"), ("oss20_low", "oss120_medium")):
    acc = {"cheap": [], "dear": [], "cascade": [], "cheap x2 + check": []}; cost = {k: [] for k in acc}; esc = []
    for sd in (1, 2, 3):
        C, D = load(cheap, sd), load(dear, sd); C2 = load(cheap, sd % 3 + 1)
        if not C or not D:
            continue
        for n in C:
            c, d = C[n], D[n]
            acc["cheap"].append(c["passed_all"]); cost["cheap"].append(tok(c))
            acc["dear"].append(d["passed_all"]); cost["dear"].append(tok(d))
            e = not passes(c); esc.append(e)
            acc["cascade"].append(d["passed_all"] if e else c["passed_all"]); cost["cascade"].append(tok(c) + (tok(d) if e else 0))
            if C2:
                c2 = C2[n]; pick = c if passes(c) else (c2 if passes(c2) else c)
                acc["cheap x2 + check"].append(pick["passed_all"]); cost["cheap x2 + check"].append(tok(c) + tok(c2))
    if not esc:
        continue
    print(f"{cheap} -> {dear} (n={len(esc)} problem-seeds, escalated {100 * sum(esc) / len(esc):.0f}%): " + " | ".join(
        f"{k} {100 * sum(v) / len(v):.1f}% @ {sum(cost[k]) / len(cost[k]):.0f} tok" for k, v in acc.items() if v))
