"""HO-B (docs/prereg/PREREG_HO.md, addendum): worst case for the 16k-token thinking budget. Every THINK row that hit the budget and is wrong
is counted as right (in THINK and wherever FF escalates to it); FF - THINK with its paired bootstrap 95% interval, as stored and in the
worst case, per held-out cell. FF = the cheap program unless it crashes / prints nothing / 'No Best Solution' (geometry: unless the
metamorphic check fails), else THINK.
usage: python analyze_budget.py [model ...]"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_ho3 import ci, ok_  # noqa: E402
from run_nlopt import RES as XRES, _rows  # noqa: E402

CELLS = [("optmath", "mips", "thinks"), ("optmath", "free", "thinkfree"), ("optibench", "free", "thinkfree"), ("optibench", "formx", "thinkfree"),
         ("bwor", "free", "thinkfree"), ("logior", "free", "thinkfree"), ("logior", "formx", "thinkfree")]   # (set, cheap arm, THINK arm) as in analyze_ho


def cell(name, pairs):
    """pairs: (item id, cheap kept?, cheap right?, think right?, think hit the budget?)"""
    out = []
    for worst in (False, True):
        per = {}
        for i, kept, fc, tc, cap in pairs:
            t = tc or (worst and cap)
            per.setdefault(i, []).append((fc if kept else t) - t)
        out.append(ci({i: sum(v) / len(v) for i, v in per.items()}))
    cap = sum(1 for p in pairs if p[4] and not p[3]) / len(pairs)
    print(f"  {name:22s} as run {out[0][0]:+5.1f} [{out[0][1]:+5.1f}, {out[0][2]:+5.1f}]   worst case {out[1][0]:+5.1f} [{out[1][1]:+5.1f}, {out[1][2]:+5.1f}]"
          f"   (THINK capped and wrong {100 * cap:.1f}%)")


def main():
    for m in sys.argv[1:] or ["oss20", "q14a", "q8b"]:
        print(f"=== {m}: FF - THINK, seed means, paired 95% interval")
        for b, a, th in CELLS:
            pairs = []
            for s in (1, 2, 3):
                F = {r["id"]: r for r in _rows(f"{XRES}/opt_{m}_{b}_{a}_s{s}.jsonl")}
                T = {r["id"]: r for r in _rows(f"{XRES}/opt_{m}_{b}_{th}_s{s}.jsonl")}
                pairs += [(i, ok_(f), bool(f["correct"]), bool(T[i]["correct"]), T[i].get("finish") == "length") for i, f in F.items() if i in T]
            if pairs:
                cell(f"{b} {a} / {th}", pairs)
        try:
            import analyze_n10 as N
            from analyze_hogc import load, ok
        except Exception as e:   # geometry needs the client environment (python >= 3.10)
            print("  geometry skipped:", e); continue
        pairs = []
        for s in (1, 2, 3):
            F, T = load(f"S2_HOG_{m}_geo_fact_s{s}"), load(f"S2_HOG_{m}_geo_think_s{s}")
            pairs += [(k, N.geo_check(f)[0], ok(f), ok(T[k]), T[k].get("finish") == "length") for k, f in F.items() if k in T]
        cell("geometry fact", pairs)


if __name__ == "__main__":
    main()
