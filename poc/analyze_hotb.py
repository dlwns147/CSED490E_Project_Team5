"""HO-TB (docs/prereg/PREREG_HO.md, addendum): thinking with the fact under a token budget (Qwen3 budget forcing, formxtb<B>) vs thinking
with the fact at 16k (formxt). Per model x benchmark (OptiBench on the HO-TF third), seed means on the problems both arms have:
THINK+F, THINK+Fb (always budgeted thinking), FF+Fb (the library program, budgeted thinking on a visible failure). Paired 95% intervals.
usage: python analyze_hotb.py <B> [model ...]"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_ho3 import ci, ok_  # noqa: E402
from run_nlopt import RES, _rows  # noqa: E402

g = lambda r: (r or {}).get("out_tokens") or 0


def main():
    B = sys.argv[1]
    for m in sys.argv[2:] or ["q14a", "q8b"]:
        for b in ("optibench", "bwor", "logior"):
            per, tok = {}, {"THINK+F": 0, "THINK+Fb": 0, "FF+Fb": 0}
            for s in (1, 2, 3):
                A = {a: {r["id"]: r for r in _rows(f"{RES}/opt_{m}_{b}_{a}_s{s}.jsonl")} for a in ("formx", "formxt", f"formxtb{B}")}
                for i, tb in A[f"formxtb{B}"].items():
                    if i not in A["formx"] or i not in A["formxt"]:
                        continue
                    f, t = A["formx"][i], A["formxt"][i]; keep = ok_(f)
                    per.setdefault(i, []).append({"THINK+F": bool(t["correct"]), "THINK+Fb": bool(tb["correct"]),
                                                  "FF+Fb": bool(f["correct"] if keep else tb["correct"])})
                    tok["THINK+F"] += g(t); tok["THINK+Fb"] += g(tb); tok["FF+Fb"] += g(f) + (0 if keep else g(tb))
            n = sum(len(v) for v in per.values())
            if not n:
                print(f"=== {m} {b}: no rows"); continue
            acc = {k: 100 * sum(x[k] for v in per.values() for x in v) / n for k in tok}
            print(f"=== {m} {b} B={B} ({len(per)} problems, {n} rows): " + " | ".join(f"{k} {acc[k]:.1f}% @ {tok[k] / n / 1000:.2f}k ({100 * tok[k] / tok['THINK+F']:.0f}%)" for k in tok))
            for k in ("THINK+Fb", "FF+Fb"):
                mu, lo, hi = ci({i: sum(x[k] - x["THINK+F"] for x in v) / len(v) for i, v in per.items()})
                print(f"  {k} - THINK+F {mu:+.1f} [{lo:+.1f}, {hi:+.1f}]")


if __name__ == "__main__":
    main()
