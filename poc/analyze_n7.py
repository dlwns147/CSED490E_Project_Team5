"""N7 (docs/prereg/PREREG_N.md): the failure map as a policy. R = accept the low sample if it passes the examples; crash / timeout / no code
-> one repair round (N2 results), accept if it passes the examples, else medium; wrong answer -> medium directly. Compared with N3 and N4.
usage: CC_SET=full python analyze_n7.py"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from repair_cc import feedback  # noqa: E402
from run_cc import PFILE, RES, VFILE  # noqa: E402

P = {p["name"]: p for p in json.load(open(PFILE))}; V = json.load(open(VFILE))
NPUB = {n: sum(t["kind"] == "public" for t in p["tests"]) for n, p in P.items()}
load = lambda f: {r["name"]: r for r in map(json.loads, open(f))}
passes = lambda r: bool(r["code"]) and r["passed"] >= NPUB[r["name"]]
tok = lambda r: r.get("out_tokens") or 0
for cheap, dear in (("oss20_low", "oss20_medium"), ("oss120_low", "oss120_medium")):
    A = {k: [0, 0, 0] for k in ("N3 cascade", "N4 repair then escalate", "R typed router")}
    kinds = {}
    for sd in (1, 2):
        C, D, Rp = load(f"{RES}/cc_full_{cheap}_s{sd}.jsonl"), load(f"{RES}/cc_full_{dear}_s{sd}.jsonl"), load(f"{RES}/cc_full_rep_{cheap}_s{sd}.jsonl")
        for n in C:
            c, d, r = C[n], D[n], Rp[n]
            def add(k, ok, t):
                A[k][0] += ok; A[k][1] += t; A[k][2] += 1
            if passes(c):
                for k in A:
                    add(k, c["passed_all"], tok(c))
                continue
            kind = r.get("feedback_kind") or ("no code" if not c["code"] else "wrong")
            kinds[kind] = kinds.get(kind, 0) + 1
            add("N3 cascade", d["passed_all"], tok(c) + tok(d))
            rep_ok = bool(r.get("code")) and feedback(P[n], r["code"], V[n]["tol"]) is None
            add("N4 repair then escalate", r["passed_all"] if rep_ok else d["passed_all"], tok(c) + r["repair_tokens"] + (0 if rep_ok else tok(d)))
            if kind in ("crash", "timeout", "no code"):
                add("R typed router", r["passed_all"] if rep_ok else d["passed_all"], tok(c) + r["repair_tokens"] + (0 if rep_ok else tok(d)))
            else:
                add("R typed router", d["passed_all"], tok(c) + tok(d))
    print(f"{cheap} -> {dear} (failure kinds on the examples: {kinds}): " + " | ".join(f"{k} {100 * v[0] / v[2]:.1f}% @ {v[1] / v[2]:.0f} tok" for k, v in A.items()))
