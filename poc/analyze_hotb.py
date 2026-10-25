"""HO-TB (docs/prereg/PREREG_HO.md, addendum): thinking with the fact under a token budget (Qwen3 budget forcing, formxtb<B>) vs thinking
with the fact at 16k (formxt). Per model x benchmark (OptiBench on the HO-TF third), seed means on the problems both arms have:
THINK+F, THINK+Fb (always budgeted thinking), FF+Fb (the library program, budgeted thinking on a visible failure). Paired 95% intervals.
HO-SB: also SB+F = budgeted thinking with the fact first, full thinking with the fact (formxt) only when the budgeted program visibly
fails (crash, no value, 'No Best Solution'); OptMATH is included for models whose cheap arm there is the library (formx).
FF+SB+F (exploratory, added after HO-SB's first cells): the library program if it passes, else SB+F (a three-step cascade).
usage: python analyze_hotb.py <B> [model ...]"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_ho3 import ci, ok_  # noqa: E402
from run_nlopt import RES, _rows  # noqa: E402

g = lambda r: (r or {}).get("out_tokens") or 0


def main():
    B = sys.argv[1]
    for m in sys.argv[2:] or ["q14a", "q8b"]:
        for b in ("optibench", "bwor", "logior") + (("optmath",) if os.path.exists(f"{RES}/opt_{m}_optmath_formxtb{B}_s1.jsonl") else ()):
            per, tok = {}, {"THINK+F": 0, "THINK+Fb": 0, "FF+Fb": 0, "SB+F": 0, "FF+SB+F": 0}
            for s in (1, 2, 3):
                A = {a: {r["id"]: r for r in _rows(f"{RES}/opt_{m}_{b}_{a}_s{s}.jsonl")} for a in ("formx", "formxt", f"formxtb{B}")}
                for i, tb in A[f"formxtb{B}"].items():
                    if i not in A["formx"] or i not in A["formxt"]:
                        continue
                    f, t = A["formx"][i], A["formxt"][i]; keep = ok_(f)
                    sb = ok_(tb)   # HO-SB: the budgeted program passes the free check
                    per.setdefault(i, []).append({"THINK+F": bool(t["correct"]), "THINK+Fb": bool(tb["correct"]),
                                                  "FF+Fb": bool(f["correct"] if keep else tb["correct"]), "SB+F": bool(tb["correct"] if sb else t["correct"]),
                                                  "FF+SB+F": bool(f["correct"] if keep else tb["correct"] if sb else t["correct"])})
                    tok["THINK+F"] += g(t); tok["THINK+Fb"] += g(tb); tok["FF+Fb"] += g(f) + (0 if keep else g(tb)); tok["SB+F"] += g(tb) + (0 if sb else g(t))
                    tok["FF+SB+F"] += g(f) + (0 if keep else g(tb) + (0 if sb else g(t)))
            n = sum(len(v) for v in per.values())
            if not n:
                print(f"=== {m} {b}: no rows"); continue
            acc = {k: 100 * sum(x[k] for v in per.values() for x in v) / n for k in tok}
            print(f"=== {m} {b} B={B} ({len(per)} problems, {n} rows): " + " | ".join(f"{k} {acc[k]:.1f}% @ {tok[k] / n / 1000:.2f}k ({100 * tok[k] / tok['THINK+F']:.0f}%)" for k in tok))
            for k in ("THINK+Fb", "FF+Fb", "SB+F", "FF+SB+F"):
                mu, lo, hi = ci({i: sum(x[k] - x["THINK+F"] for x in v) / len(v) for i, v in per.items()})
                print(f"  {k} - THINK+F {mu:+.1f} [{lo:+.1f}, {hi:+.1f}]")


if __name__ == "__main__":
    main()
