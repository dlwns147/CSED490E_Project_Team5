"""HO-TF (docs/prereg/PREREG_HO.md, addendum): always thinking with the same library fact (formxt) as the baseline. Per model x benchmark
(OptiBench: the fixed third run with FORM_SUBSET=0/3; BWOR, LogiOR: all), seed means on the problems every arm has: THINK (thinkfree, no
fact), THINK+F (formxt), FF+F (formx; formxt on a visible failure), FF (formx; thinkfree on a visible failure, the original table's
policy). Paired bootstrap 95% intervals over problems; token shares of THINK+F.
usage: python analyze_hotf.py [model ...]"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_ho3 import ci, ok_  # noqa: E402
from run_nlopt import RES, _rows  # noqa: E402


def main():
    for m in sys.argv[1:] or ["oss20", "q14a", "q8b"]:
        for b in ("optibench", "bwor", "logior"):
            per, tok, cap = {}, {k: 0 for k in ("THINK", "THINK+F", "FF+F", "FF")}, 0
            for s in (1, 2, 3):
                A = {a: {r["id"]: r for r in _rows(f"{RES}/opt_{m}_{b}_{a}_s{s}.jsonl")} for a in ("formx", "formxt", "thinkfree")}
                for i, tf in A["formxt"].items():
                    if i not in A["formx"] or i not in A["thinkfree"]:
                        continue
                    f, t = A["formx"][i], A["thinkfree"][i]; vis = not ok_(f); cap += tf.get("finish") == "length"
                    acc = {"THINK": t["correct"], "THINK+F": tf["correct"], "FF+F": tf["correct"] if vis else f["correct"],
                           "FF": t["correct"] if vis else f["correct"]}
                    per.setdefault(i, []).append({k: bool(v) for k, v in acc.items()})
                    g = lambda r: r.get("out_tokens") or 0
                    tok["THINK"] += g(t); tok["THINK+F"] += g(tf); tok["FF+F"] += g(f) + (g(tf) if vis else 0); tok["FF"] += g(f) + (g(t) if vis else 0)
            n = sum(len(v) for v in per.values())
            if not n:
                print(f"=== {m} {b}: no rows yet"); continue
            acc = {k: 100 * sum(x[k] for v in per.values() for x in v) / n for k in tok}
            print(f"=== {m} {b} ({len(per)} problems, {n} rows; THINK+F at the cap {100 * cap / n:.1f}%): " + " | ".join(
                f"{k} {acc[k]:.1f}% @ {tok[k] / n / 1000:.2f}k ({100 * tok[k] / tok['THINK+F']:.0f}%)" for k in tok))
            for a, c in (("THINK+F", "THINK"), ("FF+F", "THINK+F"), ("FF+F", "FF")):
                mu, lo, hi = ci({i: sum(x[a] - x[c] for x in v) / len(v) for i, v in per.items()})
                print(f"  {a} - {c} {mu:+.1f} [{lo:+.1f}, {hi:+.1f}]")


if __name__ == "__main__":
    main()
