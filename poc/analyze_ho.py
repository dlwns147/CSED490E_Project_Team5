"""HO (docs/prereg/PREREG_HO.md): held-out OptMATH-Bench. Per model: single arms (accuracy @ tokens, run / crash / 'No Best Solution' shares)
and policies with the automatic-fact program (mips), the library program (formx) or the solver-choice program (free, with thinkfree) as the cheap arm: CHEAP, FF (think if the program
does not run, prints nothing or prints 'No Best Solution'), FFR-strict (two programs run, agree and are feasible, else think), THINK.
usage: [HO_SET=optibench] python analyze_ho.py [model ...]"""
import os, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_x7 as X  # noqa: E402

ok_ = lambda r: X.runs(r) and r["pred"] != "NBS"


def ag(a, b):
    return a is not None and b is not None and a != "NBS" and b != "NBS" and X.same(a, b)


for m in sys.argv[1:] or ["oss20", "q14a", "q8b"]:
    tag = f"{m}_{os.environ.get('HO_SET', 'optmath')}"   # HO_SET=optibench for the second held-out benchmark (OB)
    print(f"=== {m}")
    for a in ("mip", "mipf", "mips", "formx", "thinks", "free", "freef", "thinkfree"):
        R = [r for s in (1, 2, 3) for r in (X.rows(tag, a, s) or {}).values()]
        if not R:
            continue
        st = Counter("NBS" if r.get("pred") == "NBS" else r["status"] for r in R)
        print(f"  {a:6s} n={len(R):3d} {100 * sum(r['correct'] for r in R) / len(R):5.1f}% @ {sum(r['out_tokens'] or 0 for r in R) / len(R) / 1000:.2f}k | {dict(st)}"
              f" | caps {sum(r.get('finish') == 'length' for r in R)}")
    pairs = ((("free", "thinkfree"), ("freef", "thinkfree"), ("formx", "thinkfree")) if os.environ.get("HO_SET") == "optibench"
             else (("mips", "thinks"), ("formx", "thinks"), ("free", "thinkfree")))
    for c, th in pairs:
        for s in (1, 2, 3):
            F, F2, T = X.rows(tag, c, s), X.rows(tag, c, s % 3 + 1), X.rows(tag, th, s)
            if not (F and F2 and T):
                continue
            acc = dict(CHEAP=[0, 0], FF=[0, 0], FFR=[0, 0], THINK=[0, 0]); n = 0
            for i, f in F.items():
                if i not in F2 or i not in T:
                    continue
                n += 1; t = T[i]; tf, tf2, tt = (f["out_tokens"] or 0), (F2[i]["out_tokens"] or 0), (t["out_tokens"] or 0)
                acc["CHEAP"][0] += f["correct"]; acc["CHEAP"][1] += tf
                acc["THINK"][0] += t["correct"]; acc["THINK"][1] += tt
                acc["FF"][0] += f["correct"] if ok_(f) else t["correct"]; acc["FF"][1] += tf + (0 if ok_(f) else tt)
                g = ok_(f) and ok_(F2[i]) and ag(f["pred"], F2[i]["pred"])
                acc["FFR"][0] += f["correct"] if g else t["correct"]; acc["FFR"][1] += tf + tf2 + (0 if g else tt)
            print(f"  policies ({c} / {th}, s{s}, n={n}): " + " | ".join(f"{k} {100 * a / n:.1f}% @ {k_ / n / 1000:.2f}k" for k, (a, k_) in acc.items()))
