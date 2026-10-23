"""HO-TF (docs/prereg/PREREG_HO.md, addendum): always thinking with the same library fact (formxt) as the baseline. Per model x benchmark
(OptiBench: the fixed third run with FORM_SUBSET=0/3; BWOR, LogiOR: all), seed means on the problems every arm has: THINK (thinkfree, no
fact), THINK+F (formxt), FF+F (formx; formxt on a visible failure), FF (formx; thinkfree on a visible failure, the original table's
policy). Paired bootstrap 95% intervals over problems; token shares of THINK+F.
HO-TF2: also OptMATH for Qwen3.5-9B (its cheap arm is formx there) and held-out geometry for every model (THINK = think, THINK+F =
thinkfact, the fact prompt with thinking on; a visible failure = the metamorphic check fails); --geo for geometry (needs Python >= 3.10).
usage: python analyze_hotf.py [--geo] [model ...]"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_ho3 import ci, ok_  # noqa: E402
from run_nlopt import RES, _rows  # noqa: E402


def report(name, per, tok, cap):
    n = sum(len(v) for v in per.values())
    if not n:
        print(f"=== {name}: no rows yet"); return
    acc = {k: 100 * sum(x[k] for v in per.values() for x in v) / n for k in tok}
    print(f"=== {name} ({len(per)} problems, {n} rows; THINK+F at the cap {100 * cap / n:.1f}%): " + " | ".join(
        f"{k} {acc[k]:.1f}% @ {tok[k] / n / 1000:.2f}k ({100 * tok[k] / tok['THINK+F']:.0f}%)" for k in tok))
    for a, c in (("THINK+F", "THINK"), ("FF+F", "THINK+F"), ("FF+F", "FF")):
        mu, lo, hi = ci({i: sum(x[a] - x[c] for x in v) / len(v) for i, v in per.items()})
        print(f"  {a} - {c} {mu:+.1f} [{lo:+.1f}, {hi:+.1f}]")


def geometry(m):
    import analyze_n10 as N
    from analyze_hogc import load, ok, tok as gt
    per, tok, cap = {}, {k: 0 for k in ("THINK", "THINK+F", "FF+F", "FF")}, 0
    for s in (1, 2, 3):
        F, T, TF = (load(f"S2_HOG_{m}_geo_{a}_s{s}") or {} for a in ("fact", "think", "thinkfact"))
        for k, tf in TF.items():
            if k not in F or k not in T:
                continue
            f, t = F[k], T[k]; vis = not N.geo_check(f)[0]; cap += tf.get("finish") == "length"
            per.setdefault(k, []).append({"THINK": ok(t), "THINK+F": ok(tf), "FF+F": ok(tf) if vis else ok(f), "FF": ok(t) if vis else ok(f)})
            tok["THINK"] += gt(t); tok["THINK+F"] += gt(tf); tok["FF+F"] += gt(f) + (gt(tf) if vis else 0); tok["FF"] += gt(f) + (gt(t) if vis else 0)
    report(f"{m} geometry", per, tok, cap)


def main():
    if "--geo" in sys.argv:
        for m in [a for a in sys.argv[1:] if not a.startswith("--")] or ["oss20", "q14a", "q8b", "q35"]:
            geometry(m)
        return
    for m in sys.argv[1:] or ["oss20", "q14a", "q8b", "q35"]:
        for b in ("optibench", "bwor", "logior") + (("optmath",) if m == "q35" else ()):
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
            report(f"{m} {b}", per, tok, cap)


if __name__ == "__main__":
    main()
