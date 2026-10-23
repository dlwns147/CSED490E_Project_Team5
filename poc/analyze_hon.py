"""HO-N (docs/prereg/PREREG_HON.md): the recipe on an unseen model. Per held-out benchmark, seed means:
P1 FF (library program formx; think if it fails, prints nothing or 'No Best Solution'; geometry: the fact program, think if the MR check
fails) vs always thinking, paired bootstrap 95% interval over problems and the token share; the budget note (thinking rows at the cap, and
FF - THINK when every capped wrong row counts as right); P3 gains of the card / library over the free program (calls: --census first).
usage: python analyze_hon.py [model]   (default q35; the pilot P2: python analyze_hop.py q35)"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_ho3 import ci, ok_  # noqa: E402
from run_nlopt import RES as XRES, _rows  # noqa: E402

SETS = ("optibench", "bwor", "logior", "optmath")


def rows(m, b, a, s):
    return {r["id"]: r for r in _rows(f"{XRES}/opt_{m}_{b}_{a}_s{s}.jsonl")}


def report(name, pairs):
    """pairs: (id, kept, cheap right, think right, think capped, cheap tokens, think tokens)"""
    n = len(pairs); th = sum(p[6] for p in pairs); ff = sum(p[5] + (0 if p[1] else p[6]) for p in pairs)
    out = []
    for worst in (False, True):
        per = {}
        for i, kept, fc, tc, cap, _, _ in pairs:
            t = tc or (worst and cap)
            per.setdefault(i, []).append(((fc if kept else t), t))
        d = ci({i: sum(a - b for a, b in v) / len(v) for i, v in per.items()})
        out.append(d)
    acc_ff = 100 * sum((p[2] if p[1] else p[3]) for p in pairs) / n; acc_t = 100 * sum(p[3] for p in pairs) / n
    print(f"=== {name} ({n} rows): FF {acc_ff:.1f}% @ {ff / n / 1000:.2f}k | THINK {acc_t:.1f}% @ {th / n / 1000:.2f}k | FF - THINK "
          f"{out[0][0]:+.1f} [{out[0][1]:+.1f}, {out[0][2]:+.1f}] at {100 * ff / th:.0f}% of THINK's tokens -> P1 "
          f"{'ties or beats' if out[0][2] >= 0 and ff <= 0.8 * th else 'fails'}")
    print(f"  thinking rows at the cap {100 * sum(p[4] for p in pairs) / n:.1f}%; worst case FF - THINK {out[1][0]:+.1f} [{out[1][1]:+.1f}, {out[1][2]:+.1f}]")


def main():
    m = sys.argv[1] if len(sys.argv) > 1 else "q35"
    for b in SETS:
        pairs, acc = [], {}
        for s in (1, 2, 3):
            F, T = rows(m, b, "formx", s), rows(m, b, "thinkfree", s)
            pairs += [(i, ok_(f), bool(f["correct"]), bool(T[i]["correct"]), T[i].get("finish") == "length", f.get("out_tokens") or 0,
                       T[i].get("out_tokens") or 0) for i, f in F.items() if i in T]
            for a in ("free", "freef", "formx"):
                R = rows(m, b, a, s).values(); acc.setdefault(a, []).extend(bool(r["correct"]) for r in R)
        if pairs:
            report(f"{m} {b}", pairs)
        if acc.get("free"):
            base = 100 * sum(acc["free"]) / len(acc["free"])
            print(f"  P3: free {base:.1f}% | card " + (f"{100 * sum(acc['freef']) / len(acc['freef']) - base:+.1f}" if acc["freef"] else "n/a")
                  + " | library " + (f"{100 * sum(acc['formx']) / len(acc['formx']) - base:+.1f}" if acc["formx"] else "n/a") + " points")
    try:
        import analyze_n10 as N
        from analyze_hogc import load, ok, tok
    except Exception as e:   # geometry needs python >= 3.10 (the client environment)
        print("geometry skipped:", e); return
    pairs = []
    for s in (1, 2, 3):
        F, T = load(f"S2_HOG_{m}_geo_fact_s{s}"), load(f"S2_HOG_{m}_geo_think_s{s}")
        if F and T:
            pairs += [(k, N.geo_check(f)[0], ok(f), ok(T[k]), T[k].get("finish") == "length", tok(f), tok(T[k])) for k, f in F.items() if k in T]
    if pairs:
        report(f"{m} geometry", pairs)


if __name__ == "__main__":
    main()
