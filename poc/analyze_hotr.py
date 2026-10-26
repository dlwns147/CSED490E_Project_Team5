"""HO-TR (docs/prereg/PREREG_HO.md, addendum): repair a visibly failed think from its error (repair_<m>_<set>_formxt) vs thinking again
(the next seed's stored think). Policies T, T->T, T->R (repair; if it does not run, or the think left no program, the next seed's think),
SB->T->T, SB->T->R; TR-P1 / TR-P2 tallies. usage: POC_DATA=... python analyze_hotr.py"""
import sys; sys.path.insert(0, "poc")
from analyze_ho3 import ok_, ci
from run_nlopt import RES, _rows
g = lambda r: (r or {}).get("out_tokens") or 0
p1 = p2 = 0
for m in ("q14a", "q8b", "n3n", "q35"):
    for b in ("optibench", "bwor", "logior", "optmath"):
        per = {}; A = dict.fromkeys(("T", "T->T", "T->R", "SB->T->T", "SB->T->R"), 0); K = dict(A); n = 0; nrep = nrok = 0
        for s in (1, 2, 3):
            S, T, T2, R = ({r["id"]: r for r in _rows(f"{RES}/{f}_s{x}.jsonl")} for f, x in ((f"opt_{m}_{b}_formxtb2000", s), (f"opt_{m}_{b}_formxt", s), (f"opt_{m}_{b}_formxt", s % 3 + 1), (f"repair_{m}_{b}_formxt", s)))
            for i, t in T.items():
                if i not in S or i not in T2: continue
                sb, t2, rep = S[i], T2[i], R.get(i); n += 1
                tt = (t["correct"], g(t)) if ok_(t) else (t2["correct"], g(t) + g(t2))
                if ok_(t): tr = (t["correct"], g(t))
                elif rep and ok_(rep): tr = (rep["correct"], g(t) + g(rep)); nrep += 1; nrok += 1
                else: tr = (t2["correct"], g(t) + g(rep) + g(t2)); nrep += bool(rep)
                sbtt = (sb["correct"], g(sb)) if ok_(sb) else (tt[0], g(sb) + tt[1])
                sbtr = (sb["correct"], g(sb)) if ok_(sb) else (tr[0], g(sb) + tr[1])
                res = {"T": (t["correct"], g(t)), "T->T": tt, "T->R": tr, "SB->T->T": sbtt, "SB->T->R": sbtr}
                for k, (a, tk) in res.items(): A[k] += a; K[k] += tk
                per.setdefault(i, []).append(sbtr[0] - sbtt[0])
        gain = A["T->T"] - A["T"]; rec = (A["T->R"] - A["T"]) / gain if gain > 0 else float("nan")
        xt = (K["T->R"] - K["T"]) / max(1, K["T->T"] - K["T"])
        d = ci({i: sum(v) / len(v) for i, v in per.items()}); tokr = K["SB->T->R"] / K["SB->T->T"]
        ok1 = rec >= 0.5 and xt <= 0.5; ok2 = d[2] >= 0 and tokr <= 0.9; p1 += ok1; p2 += ok2
        print(f"{m:5s} {b:9s} T {100*A['T']/n:.1f} | T->T {100*A['T->T']/n:.1f} | T->R {100*A['T->R']/n:.1f} (recovers {100*rec:.0f}% of the gain at {100*xt:.0f}% of the extra tokens; repairs run {nrok}/{nrep}) {'P1' if ok1 else ''} | SB->T->R - SB->T->T {d[0]:+.1f} [{d[1]:+.1f}, {d[2]:+.1f}] at {100*tokr:.0f}% {'P2' if ok2 else ''}")
print(f"TR-P1 {p1}/16, TR-P2 {p2}/16")
