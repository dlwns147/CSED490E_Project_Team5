"""DT2 (docs/prereg/PREREG_DT.md, addendum): the fine-tuned Qwen3-8B inside the recipe, against base Qwen3-8B thinking with the fact
(THINK+F, formxt). FF-ft = the fine-tuned model's cheap program (free: no fact, as DT; formx in brackets), its own thinking with the fact
(q8bsft formxt) on a visible failure. OptiBench on the HO-TF third; 3 seeds; paired 95% intervals.
usage: python analyze_dt2.py"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_ho3 import ci, ok_  # noqa: E402
from run_nlopt import RES, _rows  # noqa: E402

g = lambda r: (r or {}).get("out_tokens") or 0


def main():
    for b in ("optibench", "bwor", "logior"):
        per, tok = {}, {"base THINK+F": 0, "ft THINK+F": 0, "FF-ft (free)": 0, "FF-ft (formx)": 0}
        for s in (1, 2, 3):
            A = {k: {r["id"]: r for r in _rows(f"{RES}/opt_{t}_s{s}.jsonl")} for k, t in
                 (("bt", f"q8b_{b}_formxt"), ("ft", f"q8bsft_{b}_formxt"), ("ff", f"q8bsft_{b}_free"), ("fx", f"q8bsft_{b}_formx"))}
            for i, t in A["ft"].items():
                if not all(i in A[k] for k in A):
                    continue
                bt, f, fx = A["bt"][i], A["ff"][i], A["fx"][i]
                x = {"base THINK+F": bt["correct"], "ft THINK+F": t["correct"], "FF-ft (free)": f["correct"] if ok_(f) else t["correct"],
                     "FF-ft (formx)": fx["correct"] if ok_(fx) else t["correct"]}
                per.setdefault(i, []).append({k: bool(v) for k, v in x.items()})
                tok["base THINK+F"] += g(bt); tok["ft THINK+F"] += g(t)
                tok["FF-ft (free)"] += g(f) + (0 if ok_(f) else g(t)); tok["FF-ft (formx)"] += g(fx) + (0 if ok_(fx) else g(t))
        n = sum(len(v) for v in per.values())
        if not n:
            print(f"=== {b}: no rows"); continue
        acc = {k: 100 * sum(x[k] for v in per.values() for x in v) / n for k in tok}
        print(f"=== {b} ({len(per)} problems, {n} rows): " + " | ".join(f"{k} {acc[k]:.1f}% @ {tok[k] / n / 1000:.2f}k ({100 * tok[k] / tok['base THINK+F']:.0f}%)" for k in tok))
        for k in ("ft THINK+F", "FF-ft (free)", "FF-ft (formx)"):
            mu, lo, hi = ci({i: sum(x[k] - x["base THINK+F"] for x in v) / len(v) for i, v in per.items()})
            print(f"  {k} - base THINK+F {mu:+.1f} [{lo:+.1f}, {hi:+.1f}]")


if __name__ == "__main__":
    main()
