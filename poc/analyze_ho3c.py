"""HO3-C (docs/prereg/PREREG_HO.md): think only if the solution checker objects AND a second cheap program (same arm, next seed) fails or
disagrees. Offline on the HO3 / HO4 rows. usage: [HO3_ARM=freev|formxv] [HO3_SETS=bwor,logior] python analyze_ho3c.py [model ...]"""
import os, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_nlopt import RES, _rows  # noqa: E402

ok_ = lambda r: r.get("status") == "ok" and r.get("pred") not in (None, "NBS")
same = lambda a, b: abs(float(a) - float(b)) <= max(1e-2, 1e-3 * abs(float(b)))


def main():
    ARM = os.environ.get("HO3_ARM", "freev"); suf = "" if ARM == "freev" else "_" + ARM
    for m in sys.argv[1:] or ["oss20", "q14a", "q8b"]:
        for bench in os.environ.get("HO3_SETS", "bwor,logior").split(","):
            acc, tok, st = Counter(), Counter(), Counter()
            for s in (1, 2, 3):
                s2 = s % 3 + 1
                F, F2 = ({r["id"]: r for r in _rows(f"{RES}/opt_{m}_{bench}_{ARM}_s{k}.jsonl")} for k in (s, s2))
                V = {r["id"]: r for r in _rows(f"{RES}/verify_{m}_{bench}{suf}_s{s}.jsonl")}
                T = {r["id"]: r for r in _rows(f"{RES}/opt_{m}_{bench}_thinkfree_s{s}.jsonl")}
                for i, f in F.items():
                    if i not in T or i not in F2:
                        continue
                    t, g = T[i], F2[i]; v = V.get(i); runs = ok_(f); vpass = bool(runs and v and v["passed"])
                    tf, tt, tv, tg = f.get("out_tokens") or 0, t.get("out_tokens") or 0, (v.get("out_tokens") or 0) if v else 0, g.get("out_tokens") or 0
                    agree = runs and ok_(g) and same(f["pred"], g["pred"])
                    keep_va = runs and (vpass or agree)
                    acc["n"] += 1; acc["FF-V"] += f["correct"] if vpass else t["correct"]; acc["FF-VA"] += f["correct"] if keep_va else t["correct"]
                    acc["THINK"] += t["correct"]
                    tok["FF-V"] += tf + tv + (0 if vpass else tt); tok["THINK"] += tt
                    tok["FF-VA"] += tf + tv + (tg if runs and not vpass else 0) + (0 if keep_va else tt)
                    if runs:
                        k = "right" if f["correct"] else "wrong"
                        st[(k, "n")] += 1; st[(k, "V")] += not vpass; st[(k, "VA")] += not keep_va
            n = acc["n"]
            if not n:
                print(m, bench, "no rows"); continue
            print(f"=== {m} {bench} ({ARM}): " + " | ".join(f"{k} {100 * acc[k] / n:.1f}% @ {tok[k] / n / 1000:.2f}k ({100 * tok[k] / tok['THINK']:.0f}%)" for k in ("FF-V", "FF-VA", "THINK"))
                  + f" | flags wrong: V {st[('wrong', 'V')]}, VA {st[('wrong', 'VA')]} of {st[('wrong', 'n')]}; right: V {st[('right', 'V')]}, VA {st[('right', 'VA')]} of {st[('right', 'n')]}")


if __name__ == "__main__":
    main()
