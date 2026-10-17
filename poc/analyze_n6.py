"""N6 (results/PREREG_V.md): retrieved exemplar vs plain, paired on seed 1; by rating band; duplicate check (does the retrieved solution
itself pass the target's public + private tests?). usage: CC_SET=full python analyze_n6.py"""
import json, os, sys
from math import comb
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_cc import OPRE, PFILE, RES, VFILE, run_cpp, tok_eq  # noqa: E402
from sandbox import run_python  # noqa: E402

P = {p["name"]: p for p in json.load(open(PFILE))}; FULL = {p["name"]: p for p in json.load(open(f"{RES}/cc_geometry_full.json"))}
V = json.load(open(VFILE))
sign_p = lambda a, b: min(1.0, 2 * sum(comb(a + b, i) for i in range(min(a, b) + 1)) / 2 ** (a + b)) if a + b else 1.0


def solves(ex_name, target):   # the exemplar's accepted solution run on the target's public + private tests
    c = FULL[ex_name]; T = [t for t in P[target]["tests"] if t["kind"] != "generated"]; tol = V[target]["tol"]
    if c["py3"]:
        return all((r := run_python(c["py3"][0], t["input"], timeout=10)).status == "ok" and tok_eq(r.stdout, t["output"], tol) for t in T)
    outs = run_cpp(c["cpp"][0], [t["input"] for t in T], 2)
    return outs is not None and all(o is not None and tok_eq(o, t["output"], tol) for o, t in zip(outs, T))


for m in ("oss20_low", "oss120_low"):
    B = {r["name"]: r for r in map(json.loads, open(f"{RES}/{OPRE}{m}_s1.jsonl"))}
    for arm in ("ex_stmt", "ex_draft"):
        X = {r["name"]: r for r in map(json.loads, open(f"{RES}/{OPRE}{m}_{arm}_s1.jsonl"))}
        with ThreadPoolExecutor(16) as ex:
            dup = dict(zip(X, ex.map(lambda n: solves(X[n]["exemplar"], n), X)))
        lost = sum(B[n]["passed_all"] and not X[n]["passed_all"] for n in X); gained = sum(X[n]["passed_all"] and not B[n]["passed_all"] for n in X)
        hi = [n for n in X if P[n]["rating"] > 1800]
        nd = [n for n in X if not dup[n]]
        tb = sum(B[n]["out_tokens"] or 0 for n in X) / len(X); tx = sum(X[n]["out_tokens"] or 0 for n in X) / len(X)
        print(f"{m} {arm}: plain {sum(B[n]['passed_all'] for n in X)} -> {sum(X[n]['passed_all'] for n in X)} of {len(X)} (lost {lost}, gained {gained}, "
              f"p = {sign_p(lost, gained):.3f}) | rating > 1800: {sum(B[n]['passed_all'] for n in hi)} -> {sum(X[n]['passed_all'] for n in hi)} of {len(hi)} | "
              f"retrieved solution itself solves the target: {sum(dup.values())} (excluding them: {sum(B[n]['passed_all'] for n in nd)} -> "
              f"{sum(X[n]['passed_all'] for n in nd)} of {len(nd)}) | tokens {tb:.0f} -> {tx:.0f}")
