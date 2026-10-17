"""VIEWS-P4 (docs/prereg/PREREG_VIEWS.md): are errors shared by two views (both wrong with the same answer) harder than view-specific errors?
Agreement of two wrong math answers is decided by math_verify in worker processes with a per-pair time limit.
usage: python analyze_views_p4.py"""
import json, multiprocessing as mp, os, statistics as st, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")


def lvl(x):
    s = str(x).split()[-1]
    return int(s) if s.isdigit() else 6


def agree(args):
    from run_math import same
    return same(*args)


if __name__ == "__main__":
    print("VIEWS-P4: shared errors (both views wrong, same answer) vs view-specific errors (exactly one view wrong)")
    for m in ("oss20", "q32b", "q36"):
        T = {sd: {r["id"]: r for r in map(json.loads, open(f"{RES}/x1/math_{m}_text_s{sd}.jsonl"))} for sd in (1, 2, 3)}
        Pg = {sd: {r["id"]: r for r in map(json.loads, open(f"{RES}/x1/math_{m}_prog_s{sd}.jsonl"))} for sd in (1, 2, 3)}
        both = [(sd, i) for sd in (1, 2, 3) for i, t in T[sd].items() if not t["correct"] and not Pg[sd][i]["correct"] and t["cands"] and Pg[sd][i]["cands"]]
        with mp.get_context("fork").Pool(16) as pool:
            res = [pool.apply_async(agree, ((T[sd][i]["cands"], Pg[sd][i]["cands"]),)) for sd, i in both]
            ag = []
            for r in res:
                try:
                    ag.append(r.get(timeout=30))
                except Exception:
                    ag.append(False)
        shared = [lvl(T[sd][i]["level"]) for (sd, i), a in zip(both, ag) if a]
        specific = [lvl(T[sd][i]["level"]) for sd in (1, 2, 3) for i, t in T[sd].items() if t["correct"] != Pg[sd][i]["correct"]]
        f = lambda Q: f"mean level {st.mean(Q):.2f} (AIME = 6), AIME share {sum(x == 6 for x in Q) / max(1, len(Q)):.0%}, n {len(Q)}" if Q else "n 0"
        print(f"  math {m}: shared {f(shared)} | view-specific {f(specific)}", flush=True)
    for m in ("oss20", "q32b"):
        D = {(md, sd): {r["id"]: r for r in map(json.loads, open(f"{RES}/x3/opt_{m}_{md}_s{sd}.jsonl"))} for md in ("mip", "text") for sd in (1, 2, 3)}
        def sv(x, y):
            if x is None or y is None:
                return False
            if "NBS" in (x, y):
                return x == y
            return abs(x - y) <= max(1e-2, 1e-3 * abs(y))
        sh, sp = Counter(), Counter()
        for sd in (1, 2, 3):
            for i, a in D[("mip", sd)].items():
                if not i.startswith("industryor"):
                    continue
                b = D[("text", sd)][i]
                if not a["correct"] and not b["correct"] and sv(a["pred"], b["pred"]):
                    sh[a["difficulty"]] += 1
                elif a["correct"] != b["correct"]:
                    sp[a["difficulty"]] += 1
        g = lambda c: " / ".join(f"{k} {c[k] / max(1, sum(c.values())):.0%}" for k in ("Hard", "Medium", "Easy")) + f" (n {sum(c.values())})"
        print(f"  IndustryOR {m}: shared mip-text errors {g(sh)} | view-specific {g(sp)}", flush=True)
