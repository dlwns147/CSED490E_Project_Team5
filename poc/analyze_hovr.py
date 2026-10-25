"""HO-VR (docs/prereg/PREREG_HO.md, addendum): FF-R+F = the library program (formx) if it passes the free check AND a 2k-token thinking-mode
review says CORRECT (review_<m>_<set>_formx), else thinking with the fact (formxt); vs THINK+F and FF+F. OptiBench on the HO-TF third.
Also the review's flag rates on wrong / right passing programs (labels used only for that note). Paired 95% intervals.
HO-VR2: --vr2 for OptMATH (mips vs thinks) and held-out geometry (fact, MR check + review, vs thinkfact; leak flags).
HO-N4: OptMATH with the library arm (formx vs formxt) is included when its reviews exist (models never run with mips there).
usage: python analyze_hovr.py [--vr2] [model ...]"""
import os, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_ho3 import ci, ok_  # noqa: E402
from run_nlopt import RES, _rows  # noqa: E402

g = lambda r: (r or {}).get("out_tokens") or 0


def vr2(models):
    import analyze_n10 as N
    from analyze_hogc import load, ok, tok as gt
    for m in models:
        per, tk, flag = {}, Counter(), Counter()   # OptMATH
        for s in (1, 2, 3):
            F = {r["id"]: r for r in _rows(f"{RES}/opt_{m}_optmath_mips_s{s}.jsonl")}
            T = {r["id"]: r for r in _rows(f"{RES}/opt_{m}_optmath_thinks_s{s}.jsonl")}
            V = {r["id"]: r for r in _rows(f"{RES}/review_{m}_optmath_mips_s{s}.jsonl")}
            for i, t in T.items():
                if i not in F:
                    continue
                f, v = F[i], V.get(i); runs = ok_(f); acc = runs and bool(v and v["accept"])
                per.setdefault(i, []).append({"THINK+F": bool(t["correct"]), "FF+F": bool(f["correct"] if runs else t["correct"]), "FF-R+F": bool(f["correct"] if acc else t["correct"])})
                tk["THINK+F"] += g(t); tk["FF+F"] += g(f) + (0 if runs else g(t)); tk["FF-R+F"] += g(f) + g(v) + (0 if acc else g(t))
        report(f"{m} optmath", per, tk)
        per, tk = {}, Counter()   # geometry
        for s in (1, 2, 3):
            F, T = load(f"S2_HOG_{m}_geo_fact_s{s}"), load(f"S2_HOG_{m}_geo_thinkfact_s{s}")
            V = {r["id"]: r for r in _rows(f"{RES}/review_{m}_geo_fact_s{s}.jsonl")}
            for k, t in T.items():
                f = F[k]; v = V.get("|".join(map(str, k))); passes = N.geo_check(f)[0]; acc = passes and bool(v and v["accept"])
                per.setdefault(k, []).append({"THINK+F": ok(t), "FF+F": ok(f) if passes else ok(t), "FF-R+F": ok(f) if acc else ok(t)})
                tk["THINK+F"] += gt(t); tk["FF+F"] += gt(f) + (0 if passes else gt(t)); tk["FF-R+F"] += gt(f) + g(v) + (0 if acc else gt(t))
                if passes and v:
                    kk = "right" if ok(f) else ("edge" if f["per_variant"].get("identity") else "input")
                    flag[(kk, "n")] += 1; flag[(kk, "flag")] += not v["accept"]
        report(f"{m} geometry", per, tk)
        print(f"  review flags leaked programs: wrong on the given input {flag[('input', 'flag')]}/{flag[('input', 'n')]}, edge-case-only "
              f"{flag[('edge', 'flag')]}/{flag[('edge', 'n')]}; false alarms {flag[('right', 'flag')]}/{flag[('right', 'n')]}")


def report(name, per, tok):
    n = sum(len(v) for v in per.values())
    if not n:
        print(f"=== {name}: no rows"); return
    acc = {k: 100 * sum(x[k] for v in per.values() for x in v) / n for k in ("THINK+F", "FF+F", "FF-R+F")}
    print(f"=== {name} ({len(per)} items, {n} rows): " + " | ".join(f"{k} {acc[k]:.1f}% @ {tok[k] / n / 1000:.2f}k ({100 * tok[k] / tok['THINK+F']:.0f}%)" for k in acc))
    for k in ("FF+F", "FF-R+F"):
        mu, lo, hi = ci({i: sum(x[k] - x["THINK+F"] for x in v) / len(v) for i, v in per.items()})
        print(f"  {k} - THINK+F {mu:+.1f} [{lo:+.1f}, {hi:+.1f}]")


def main():
    if "--vr2" in sys.argv:
        return vr2([a for a in sys.argv[1:] if not a.startswith("--")] or ["q14a", "q8b"])
    flag = Counter()
    for m in sys.argv[1:] or ["q14a", "q8b"]:
        for b in ("optibench", "bwor", "logior") + (("optmath",) if os.path.exists(f"{RES}/review_{m}_optmath_formx_s1.jsonl") else ()):   # HO-N4
            per, tok = {}, {"THINK+F": 0, "FF+F": 0, "FF-R+F": 0}
            for s in (1, 2, 3):
                F = {r["id"]: r for r in _rows(f"{RES}/opt_{m}_{b}_formx_s{s}.jsonl")}
                T = {r["id"]: r for r in _rows(f"{RES}/opt_{m}_{b}_formxt_s{s}.jsonl")}
                V = {r["id"]: r for r in _rows(f"{RES}/review_{m}_{b}_formx_s{s}.jsonl")}
                for i, t in T.items():
                    if i not in F:
                        continue
                    f, v = F[i], V.get(i); runs = ok_(f); acc = runs and bool(v and v["accept"])
                    per.setdefault(i, []).append({"THINK+F": bool(t["correct"]), "FF+F": bool(f["correct"] if runs else t["correct"]),
                                                  "FF-R+F": bool(f["correct"] if acc else t["correct"])})
                    tok["THINK+F"] += g(t); tok["FF+F"] += g(f) + (0 if runs else g(t)); tok["FF-R+F"] += g(f) + g(v) + (0 if acc else g(t))
                    if runs and v:
                        k = "right" if f["correct"] else "wrong"
                        flag[(k, "n")] += 1; flag[(k, "flag")] += not v["accept"]
            n = sum(len(v) for v in per.values())
            if not n:
                print(f"=== {m} {b}: no rows"); continue
            acc = {k: 100 * sum(x[k] for v in per.values() for x in v) / n for k in tok}
            print(f"=== {m} {b} ({len(per)} problems, {n} rows): " + " | ".join(f"{k} {acc[k]:.1f}% @ {tok[k] / n / 1000:.2f}k ({100 * tok[k] / tok['THINK+F']:.0f}%)" for k in tok))
            for k in ("FF+F", "FF-R+F"):
                mu, lo, hi = ci({i: sum(x[k] - x["THINK+F"] for x in v) / len(v) for i, v in per.items()})
                print(f"  {k} - THINK+F {mu:+.1f} [{lo:+.1f}, {hi:+.1f}]")
    print(f"review flags {flag[('wrong', 'flag')]}/{flag[('wrong', 'n')]} wrong passing programs and {flag[('right', 'flag')]}/{flag[('right', 'n')]} right ones")


if __name__ == "__main__":
    main()
