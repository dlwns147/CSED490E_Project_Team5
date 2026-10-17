"""N4 (results/PREREG_N.md): typed combination, offline. Cheap sample -> accept if it passes the examples; else one repair round (from
cc_full_rep_<cheap>_s<seed>.jsonl); if the repaired program passes the examples accept it; else the expensive mode's sample. Costs count
every call made. Compared with the N3 cascade (no repair) and each mode alone, on the seeds with repair data.
usage: python analyze_n4.py"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("CC_SET", "full")
from repair_cc import feedback  # noqa: E402
from run_cc import PFILE, RES, VFILE  # noqa: E402

P = {p["name"]: p for p in json.load(open(PFILE))}; V = json.load(open(VFILE))
NPUB = {n: sum(t["kind"] == "public" for t in p["tests"]) for n, p in P.items()}
load = lambda f: {r["name"]: r for r in map(json.loads, open(f))} if os.path.exists(f) else None
passes = lambda r: bool(r["code"]) and r["passed"] >= NPUB[r["name"]]
tok = lambda r: r.get("out_tokens") or 0
for cheap, dear in (("q32b_plain", "q32b_think1024"), ("oss20_low", "oss20_medium"), ("oss120_low", "oss120_medium")):
    A = {k: [0, 0, 0] for k in ("cheap", "dear", "N3 cascade", "cheap + repair", "N4")}   # solved, tokens, n
    for sd in (1, 2):
        C, D, R = load(f"{RES}/cc_full_{cheap}_s{sd}.jsonl"), load(f"{RES}/cc_full_{dear}_s{sd}.jsonl"), load(f"{RES}/cc_full_rep_{cheap}_s{sd}.jsonl")
        if not (C and D and R):
            continue
        for n in C:
            c, d, r = C[n], D[n], R[n]
            add = lambda k, ok, t: (A[k].__setitem__(0, A[k][0] + ok), A[k].__setitem__(1, A[k][1] + t), A[k].__setitem__(2, A[k][2] + 1))
            add("cheap", c["passed_all"], tok(c)); add("dear", d["passed_all"], tok(d))
            add("N3 cascade", c["passed_all"] if passes(c) else d["passed_all"], tok(c) + (0 if passes(c) else tok(d)))
            add("cheap + repair", r["passed_all"], tok(c) + r["repair_tokens"])
            if passes(c):
                add("N4", c["passed_all"], tok(c))
            else:
                rep_ok = r["repaired"] and r["code"] and feedback(P[n], r["code"], V[n]["tol"]) is None
                add("N4", r["passed_all"] if rep_ok else d["passed_all"], tok(c) + r["repair_tokens"] + (0 if rep_ok else tok(d)))
    if A["N4"][2]:
        print(f"{cheap} -> {dear} (n={A['N4'][2]} problem-seeds): " + " | ".join(f"{k} {100 * v[0] / v[2]:.1f}% @ {v[1] / v[2]:.0f} tok" for k, v in A.items()))
