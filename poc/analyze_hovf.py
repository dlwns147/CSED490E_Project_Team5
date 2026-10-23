"""HO-VF / HO-LG (docs/prereg/PREREG_HO.md, addenda): against thinking given the same fact (formxt). FF+F = the library program (formx),
formxt on a visible failure; FF-V+F = the library program that prints its solution (formxv), accepted only if it runs, prints a value
and the solution checker passes (verify_<m>_<set>_formxv), else formxt. OptiBench on the HO-TF third. Paired bootstrap 95% intervals;
tokens = programs + checker + thinking where escalated.
usage: python analyze_hovf.py [model ...]"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_ho3 import ci, ok_  # noqa: E402
from run_nlopt import RES, _rows  # noqa: E402

g = lambda r: (r or {}).get("out_tokens") or 0


def main():
    for m in sys.argv[1:] or ["q14a", "q8b"]:
        for b in ("optibench", "bwor", "logior"):
            per, tok = {}, {"THINK+F": 0, "FF+F": 0, "FF-V+F": 0}
            for s in (1, 2, 3):
                A = {a: {r["id"]: r for r in _rows(f"{RES}/opt_{m}_{b}_{a}_s{s}.jsonl")} for a in ("formx", "formxt", "formxv")}
                V = {r["id"]: r for r in _rows(f"{RES}/verify_{m}_{b}_formxv_s{s}.jsonl")}
                for i, t in A["formxt"].items():
                    if i not in A["formx"]:
                        continue
                    f, fv, v = A["formx"][i], A["formxv"].get(i), V.get(i)
                    keep_f = ok_(f); keep_v = bool(fv and ok_(fv) and v and v.get("passed"))
                    x = {"THINK+F": t["correct"], "FF+F": f["correct"] if keep_f else t["correct"]}
                    if A["formxv"]:
                        x["FF-V+F"] = fv["correct"] if keep_v else t["correct"]
                        tok["FF-V+F"] += g(fv) + g(v) + (0 if keep_v else g(t))
                    per.setdefault(i, []).append({k: bool(y) for k, y in x.items()})
                    tok["THINK+F"] += g(t); tok["FF+F"] += g(f) + (0 if keep_f else g(t))
            n = sum(len(v) for v in per.values())
            if not n:
                print(f"=== {m} {b}: no rows"); continue
            arms = [k for k in tok if all(k in x for v in per.values() for x in v)]
            acc = {k: 100 * sum(x[k] for v in per.values() for x in v) / n for k in arms}
            print(f"=== {m} {b} ({len(per)} problems, {n} rows): " + " | ".join(f"{k} {acc[k]:.1f}% @ {tok[k] / n / 1000:.2f}k ({100 * tok[k] / tok['THINK+F']:.0f}%)" for k in arms))
            for k in arms[1:]:
                mu, lo, hi = ci({i: sum(x[k] - x["THINK+F"] for x in v) / len(v) for i, v in per.items()})
                print(f"  {k} - THINK+F {mu:+.1f} [{lo:+.1f}, {hi:+.1f}]")


if __name__ == "__main__":
    main()
