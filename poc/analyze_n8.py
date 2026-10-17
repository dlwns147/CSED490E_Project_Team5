"""N8 (docs/prereg/PREREG_N.md): three-level cascade low -> medium -> high (64k) for gpt-oss-120b, escalating when the statement's examples fail.
usage: CC_SET=full [N8_MODEL=oss20 N8_MEDIUM=medium64k] python analyze_n8.py"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_cc import PFILE, RES  # noqa: E402

P = {p["name"]: p for p in json.load(open(PFILE))}
NPUB = {n: sum(t["kind"] == "public" for t in p["tests"]) for n, p in P.items()}
load = lambda t, s: {r["name"]: r for r in map(json.loads, open(f"{RES}/cc_full_{t}_s{s}.jsonl"))}
passes = lambda r: bool(r["code"]) and r["passed"] >= NPUB[r["name"]]
tok = lambda r: r.get("out_tokens") or 0
A = {k: [0, 0, 0] for k in ("low", "medium", "high", "low->medium", "low->medium->high", "medium->high")}
for sd in (1, 2, 3):
    mo = os.environ.get("N8_MODEL", "oss120")   # SIZE-CC: N8_MODEL=oss20 N8_MEDIUM=medium64k (the 3090-class model)
    L, M, H = load(f"{mo}_low", sd), load(f"{mo}_{os.environ.get('N8_MEDIUM', 'medium')}", sd), load(f"{mo}_high64k", sd)
    for n in L:
        l, m, h = L[n], M[n], H[n]
        def add(k, ok, t):
            A[k][0] += ok; A[k][1] += t; A[k][2] += 1
        add("low", l["passed_all"], tok(l)); add("medium", m["passed_all"], tok(m)); add("high", h["passed_all"], tok(h))
        add("low->medium", l["passed_all"] if passes(l) else m["passed_all"], tok(l) + (0 if passes(l) else tok(m)))
        if passes(l):
            add("low->medium->high", l["passed_all"], tok(l))
        elif passes(m):
            add("low->medium->high", m["passed_all"], tok(l) + tok(m))
        else:
            add("low->medium->high", h["passed_all"], tok(l) + tok(m) + tok(h))
        add("medium->high", m["passed_all"] if passes(m) else h["passed_all"], tok(m) + (0 if passes(m) else tok(h)))
for k, (s, t, n) in A.items():
    print(f"{k:20s} {100 * s / n:5.1f}% @ {t / n / 1000:5.1f}k tokens per problem (n = {n})")
