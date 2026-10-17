"""X3 (results/PREREG_X3.md): verbal optimization problems. Accuracy / tokens per mode and source, failure kinds (crash vs runs-but-wrong),
leak of agreement checks (mip vs cpsat, mip vs text, mip vs mip next seed). usage: python analyze_x3.py <model>"""
import json, os, statistics as st, sys
from collections import Counter

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "x3")
m = sys.argv[1]
modes = ("mip", "mipf", "cpsat", "text", "think")
D = {(md, sd): {r["id"]: r for r in map(json.loads, open(f"{RES}/opt_{m}_{md}_s{sd}.jsonl"))} for md in modes for sd in (1, 2, 3)
     if os.path.exists(f"{RES}/opt_{m}_{md}_s{sd}.jsonl")}
ids = sorted(D[("mip", 1)])
groups = {"NL4OPT": [i for i in ids if i.startswith("nl4opt")], "IndustryOR": [i for i in ids if i.startswith("industryor")]}
print(f"=== {m}")
for md in modes:
    rows = [D[(md, sd)][i] for sd in (1, 2, 3) if (md, sd) in D for i in ids]
    if not rows:
        continue
    t = sorted(r["out_tokens"] or 0 for r in rows)
    wrong = [r for r in rows if not r["correct"]]
    kinds = Counter(("runs, wrong value" if r["pred"] is not None else r.get("status")) for r in wrong)
    acc = " | ".join(f"{g} {100 * sum(D[(md, sd)][i]['correct'] for sd in (1, 2, 3) if (md, sd) in D for i in I) / (len(I) * sum((md, sd) in D for sd in (1, 2, 3))):.1f}%" for g, I in groups.items())
    print(f"  {md:5s} {acc} | tokens {st.mean(t):.0f} (p90 {t[int(.9 * len(t))]}), caps {sum(r.get('finish') == 'length' for r in rows)} | failures {dict(kinds.most_common(4))}")
same = lambda a, b: a["pred"] is not None and b["pred"] is not None and (a["pred"] == b["pred"] if "NBS" in (a["pred"], b["pred"]) else abs(a["pred"] - b["pred"]) <= max(1e-2, 1e-3 * abs(b["pred"])))
for g, I in groups.items():
    out = []
    for a_md, b_md, shift in (("mip", "cpsat", 0), ("mip", "text", 0), ("mip", "mip", 1)):
        ag = wr = 0
        for sd in (1, 2, 3):
            sd2 = sd % 3 + 1 if shift else sd
            if (a_md, sd) not in D or (b_md, sd2) not in D:
                continue
            for i in I:
                A, B = D[(a_md, sd)][i], D[(b_md, sd2)][i]
                if same(A, B):
                    ag += 1; wr += not A["correct"]
        out.append(f"{a_md}-{b_md}{' (next seed)' if shift else ''}: agree {ag}, wrong among agreeing {wr} ({100 * wr / max(1, ag):.1f}%)")
    print(f"  {g} leak: " + " | ".join(out))
