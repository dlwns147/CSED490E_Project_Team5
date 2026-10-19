"""CD (docs/prereg/PREREG_CD.md): the same knowledge as code vs as a description. K1 API usage on NL4OPT + IndustryOR (mip / mipf code /
mipt words); K2 TSP and K3 redistribution on MAMO (mips base / formh sentence / formc code). Seed means, per-seed values, run / crash /
'No Best Solution' shares. usage: python analyze_cd.py"""
import os, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_x7 as X  # noqa: E402

KIND = {r["id"]: r.get("kind") for r in X.rows("oss20_mamo", "formc", 1).values()}
for m in ("oss20", "q14a", "q8b"):
    print(f"=== {m}")
    for a, name in (("mip", "no fact"), ("mipt", "words"), ("mipf", "code")):
        per = []; st = Counter()
        for s in (1, 2, 3):
            R = list(X.rows(m, a, s).values()); per.append(100 * sum(r["correct"] for r in R) / len(R))
            st.update("NBS" if r.get("pred") == "NBS" else r["status"] for r in R)
        print(f"  K1 API {name:8s} {sum(per) / 3:5.1f}% (" + " / ".join(f"{x:.1f}" for x in per) + f") | {dict(st)}")
    for k in ("tsp", "redistribution"):
        for a, name in (("mips", "base"), ("formh", "sentence"), ("formc", "code")):
            per = []; st = Counter()
            for s in (1, 2, 3):
                R = [r for i, r in X.rows(f"{m}_mamo", a, s).items() if KIND.get(i) == k]
                per.append(100 * sum(r["correct"] for r in R) / len(R)); st.update("NBS" if r.get("pred") == "NBS" else r["status"] for r in R)
            print(f"  {k:14s} {name:8s} {sum(per) / 3:5.1f}% (" + " / ".join(f"{x:.0f}" for x in per) + f") | {dict(st)}")
