"""X6 (results/PREREG_X3.md, X6 + addendum): does the API fact make thinking pay on verbal optimization (NL4OPT 245 + IndustryOR 100)?
Arms (results/x3/opt_<m>_<arm>_s<seed>.jsonl): mip, mipf (+ 6-line pywraplp snippet), think, thinkf (thinking + the snippet).
Label-free check = the program runs and prints a value. Policies use the same seed's rows; tokens = mean output tokens per item.
usage: python analyze_x6.py q32b q8b q36"""
import json, os, re, sys
from collections import Counter

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "x3")
ARMS = ("mip", "mipf", "think", "thinkf")


def load(m, arm, s):
    f = f"{RES}/opt_{m}_{arm}_s{s}.jsonl"
    return {r["id"]: r for r in map(json.loads, open(f))} if os.path.exists(f) else None


def passes(r):
    return r["status"] == "ok" and r.get("pred") is not None


def tok(r):
    return r.get("out_tokens") or 0


def invented(r):
    return re.findall(r"AttributeError: '(\w+)' object has no attribute '(\w+)'", r.get("err") or "")


def run(m):
    D = {(a, s): load(m, a, s) for a in ARMS for s in (1, 2, 3)}
    missing = [k for k, v in D.items() if v is None or len(v) < 345]
    if missing:
        print(m, "incomplete:", [(k, 0 if D[k] is None else len(D[k])) for k in missing]); return None
    ids = sorted(D[("mip", 1)])
    print(f"=== {m} (345 problems x 3 seeds)")
    acc = {}
    for a in ARMS:
        rows = [D[(a, s)][i] for s in (1, 2, 3) for i in ids]
        by = Counter(); n = Counter()
        for r in rows:
            n[r["src"]] += 1; by[r["src"]] += r["correct"]
        st = Counter(r["status"] for r in rows); inv = Counter(x for r in rows for x in invented(r))
        sm = sum(c for (o, name), c in inv.items() if name in ("SetMaximize", "SetMinimize"))
        acc[a] = (sum(r["correct"] for r in rows) / len(rows), sum(map(tok, rows)) / len(rows))
        print(f"  {a:6} NL4OPT {100 * by['nl4opt'] / n['nl4opt']:.1f}% | IndustryOR {100 * by['industryor'] / n['industryor']:.1f}% | pooled "
              f"{100 * acc[a][0]:.1f}% @ {acc[a][1]:.0f} tok | caps {sum(r.get('finish') == 'length' for r in rows)} | status {dict(st)} | "
              f"invented SetMaximize/SetMinimize {sm}, top invented {inv.most_common(3)}")

    def policy(first, second):
        a_ = t_ = esc = 0
        for s in (1, 2, 3):
            for i in ids:
                r = D[(first, s)][i]; t_ += tok(r)
                if passes(r):
                    a_ += r["correct"]
                else:
                    esc += 1; r2 = D[(second, s)][i]; t_ += tok(r2); a_ += r2["correct"]
        N = 3 * len(ids)
        return a_ / N, t_ / N, esc / N
    P = {"FACT-FIRST-THEN-THINK (mipf -> thinkf)": policy("mipf", "thinkf"), "base-then-think (mip -> think)": policy("mip", "think"),
         "THINK-FIRST (think -> mipf)": policy("think", "mipf"), "thinkf-then-mipf": policy("thinkf", "mipf")}
    for k, (a_, t_, e) in P.items():
        print(f"  {k:40} {100 * a_:.1f}% @ {t_:.0f} tok (escalated {100 * e:.0f}%)")
    ff = P["FACT-FIRST-THEN-THINK (mipf -> thinkf)"]
    print(f"  P2/P4 thinkf - think {100 * (acc['thinkf'][0] - acc['think'][0]):+.1f} | P5 (thinkf - mipf) {100 * (acc['thinkf'][0] - acc['mipf'][0]):+.1f} "
          f"vs (think - mip) {100 * (acc['think'][0] - acc['mip'][0]):+.1f} | P3 FF - always thinkf {100 * (ff[0] - acc['thinkf'][0]):+.1f} at "
          f"{100 * ff[1] / acc['thinkf'][1]:.0f}% of its tokens; FF - always think {100 * (ff[0] - acc['think'][0]):+.1f} at "
          f"{100 * ff[1] / acc['think'][1]:.0f}% of its tokens")
    return acc, P


if __name__ == "__main__":
    for m in sys.argv[1:] or ["q32b", "q8b", "q36"]:
        run(m)
