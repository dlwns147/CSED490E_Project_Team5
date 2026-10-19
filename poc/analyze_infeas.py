"""INFEAS (docs/prereg/PREREG_X7.md): offline policies over the cheap pair + thinking + the repair rows of run_infeas.py.
FFR: two cheap programs (seed s, s+1) run and agree -> accept, else think (seed s). FFR-I: 'No Best Solution' counts as a failed check.
(a) FFR-I -> think;  (b) FFR-I, and a first program that printed 'No Best Solution' gets the repair turn; think only if the repaired
program still fails (crash / no value / infeasible again).  usage: python analyze_infeas.py [model ...]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_x7 as X  # noqa: E402


def ag(a, b):
    if a is None or b is None:
        return False
    return a == b if "NBS" in (a, b) else X.same(a, b)


for m in sys.argv[1:] or ["oss20", "q14a", "q8b"]:
    for tag, src, thk in ((f"{m}_mamo", "mips", "thinks"), (m, "mipf", "thinkf")):
        for s in (1, 2, 3):
            F, F2, T, Rr = X.rows(tag, src, s), X.rows(tag, src, s % 3 + 1), X.rows(tag, thk, s), X.rows(tag, src + "r", s)
            if not (F and F2 and T and Rr is not None):
                continue
            acc = {"FFR": [0, 0], "(a) infeasible->think": [0, 0], "(b) infeasible->repair->think": [0, 0]}; n = 0
            for i, f in F.items():
                if i not in F2 or i not in T:
                    continue
                n += 1; t = T[i]; ct = (f["out_tokens"] or 0) + (F2[i]["out_tokens"] or 0)
                agree = X.runs(f) and X.runs(F2[i]) and ag(f["pred"], F2[i]["pred"])
                acc["FFR"][0] += f["correct"] if agree else t["correct"]; acc["FFR"][1] += ct + (0 if agree else t["out_tokens"] or 0)
                ok = agree and f["pred"] != "NBS"
                acc["(a) infeasible->think"][0] += f["correct"] if ok else t["correct"]
                acc["(a) infeasible->think"][1] += ct + (0 if ok else t["out_tokens"] or 0)
                if ok:
                    c, k = f["correct"], ct
                elif f.get("pred") == "NBS" and i in Rr:
                    r = Rr[i]; good = X.runs(r) and r["pred"] != "NBS"
                    c = r["correct"] if good else t["correct"]; k = ct + (r["out_tokens"] or 0) + (0 if good else t["out_tokens"] or 0)
                else:
                    c, k = t["correct"], ct + (t["out_tokens"] or 0)
                acc["(b) infeasible->repair->think"][0] += c; acc["(b) infeasible->repair->think"][1] += k
            print(f"{tag:11s} s{s}: " + " | ".join(f"{p} {100 * a / n:.1f}% @ {tk / n / 1000:.2f}k" for p, (a, tk) in acc.items()))
