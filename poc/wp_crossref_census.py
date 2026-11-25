"""CROSSREF census (descriptive, 2026-11-25): where SAMEREF's gain over one program comes from: the judge on two printed values, or the second program standing in when the first prints none. usage: python wp_crossref_census.py"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wp_crossref as C
tot = [0, 0, 0, 0, 0]; agree_ok = agree_n = 0
for st in C.NINE + ("easyc", "nl4c", "omtf2"):
    RN, P, A, _, _, A2 = C.load(st); Z = {json.loads(l)["id"]: json.loads(l) for l in open(f"{C.W.OUT}/crossref_{st}_samejudge.jsonl")}
    v = [len(P), 0, 0, 0, 0]
    for i in P:
        x, y = A[i], A2[i]; cx, cy = bool(x["correct"]), bool(y["correct"])
        if C.same(RN, x["pred"], y["pred"]):
            agree_n += 1; agree_ok += cx; continue
        if x["pred"] is None or y["pred"] is None:
            v[1] += x["pred"] is None; v[2] += (x["pred"] is None) * (int(cy) - int(cx))
        else:
            v[3] += 1; v[4] += (Z.get(i, {}).get("pick") == "A2") * (int(cy) - int(cx))
    tot = [a + b for a, b in zip(tot, v)]
    print(f"{st:9s} n={v[0]:3d}  first prints no value {v[1]:3d} -> net right gained {v[2]:+d}   judged {v[3]:3d} -> net right gained {v[4]:+d}")
print(f"all n={tot[0]}: stand-in {tot[2]:+d}, judge {tot[4]:+d} (of {tot[3]} judged); agreeing pairs right {agree_ok} of {agree_n} ({100*agree_ok/agree_n:.1f}%)")
