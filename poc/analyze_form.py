"""FORM (docs/prereg/PREREG_X7.md): mips (automatic API example from the other benchmark) vs formh (+ one hand formulation sentence, TSP and
redistribution only) vs formx (label-free cross-model mined program for the most similar other MAMO problem). Accuracy by problem type
(TSP / redistribution / other), share of 'No Best Solution', tokens; and the FFR pipeline (two cheap programs agree and are not
'No Best Solution' -> accept, else thinking) with mips vs formx as the cheap arm.  usage: python analyze_form.py [model ...]"""
import os, sys
from collections import defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_x7 as X  # noqa: E402

KIND = {r["id"]: r.get("kind") or "other" for r in X.rows("oss20_mamo", "formx", 1).values()}


def ag(a, b):
    return a is not None and b is not None and a != "NBS" and b != "NBS" and X.same(a, b)


for m in sys.argv[1:] or ["oss20", "q14a", "q8b"]:
    tag = f"{m}_mamo"
    print(f"=== {m}")
    for s in (1, 2, 3):
        line = []
        for a in ("mips", "formh", "formx"):
            R = X.rows(tag, a, s)
            if not R:
                continue
            by = defaultdict(lambda: [0, 0, 0, 0])
            for i, r in R.items():
                b = by[KIND[i]]; b[0] += r["correct"]; b[1] += 1; b[2] += r.get("pred") == "NBS"; b[3] += r["out_tokens"] or 0
            line.append(f"{a}: " + ", ".join(f"{k} {100 * b[0] / b[1]:.0f}% (NBS {b[2]}, {b[3] / b[1]:.0f} tok)" for k, b in sorted(by.items())))
        print(f"  s{s} | " + " | ".join(line))
    for s in (1, 2, 3):
        T = X.rows(tag, "thinks", s); out = []
        for a in ("mips", "formx"):
            F, F2 = X.rows(tag, a, s), X.rows(tag, a, s % 3 + 1)
            acc = tok = n = 0; cheap = 0
            for i, f in F.items():
                if i not in F2 or i not in T:
                    continue
                n += 1; ok = X.runs(f) and X.runs(F2[i]) and ag(f["pred"], F2[i]["pred"]); cheap += f["correct"]
                acc += f["correct"] if ok else T[i]["correct"]
                tok += (f["out_tokens"] or 0) + (F2[i]["out_tokens"] or 0) + (0 if ok else T[i]["out_tokens"] or 0)
            out.append(f"{a}: cheap {100 * cheap / n:.1f}% | FFR {100 * acc / n:.1f}% @ {tok / n / 1000:.2f}k")
        print(f"  pipeline s{s}: " + " || ".join(out))
