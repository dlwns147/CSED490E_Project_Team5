"""HO-X (docs/prereg/PREREG_HOGC.md, addendum): a check from a different model. Policy XV accepts a model's fact program only if it passes its
own free check and agrees with gpt-oss-20b's fact program for the same item and seed, else the model's own THINK.
Geometry: own check = analyze_n10.geo_check (MR); agreement = analyze_hogc.agree (equal outputs on the six inputs). Rows: HO-G fact / think.
Word problems (BWOR, LogiOR): own check = the freev program runs and prints a value; agreement = gpt-oss-20b's freev program runs and prints a
value within the grader's tolerance of it. Compared with FF-V (HO3: own checker) and THINK. Tokens = both cheap programs (+ checker for
FF-V) + thinking where escalated. Paired bootstrap 95% intervals over items. Note (not pre-registered): OSS = gpt-oss-20b's own FF, the
reference for "the second model is run anyway".
usage: python analyze_hox.py [model ...]"""
import os, sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_n10 as N  # noqa: E402
from analyze_hogc import agree, load, ok, outs, tok  # noqa: E402
from analyze_ho3 import ci, ok_  # noqa: E402
from run_nlopt import RES as XRES, _rows, correct  # noqa: E402

REF = "oss20"


def geometry(m):
    F = {s: load(f"S2_HOG_{m}_geo_fact_s{s}") for s in (1, 2, 3)}
    T = {s: load(f"S2_HOG_{m}_geo_think_s{s}") for s in (1, 2, 3)}
    O = {s: load(f"S2_HOG_{REF}_geo_fact_s{s}") for s in (1, 2, 3)}
    OT = {s: load(f"S2_HOG_{REF}_geo_think_s{s}") for s in (1, 2, 3)}
    rows = [r for X in (F, O) for s in X for r in X[s].values()]
    with ThreadPoolExecutor(int(os.environ.get("HOGC_THREADS", 8))) as ex:
        list(ex.map(N.geo_check, rows)); list(ex.map(outs, rows))
    import json
    json.dump(N.CACHE, open(N.CACHE_F, "w"))
    per, tk, st = {}, Counter(), Counter()
    for s in (1, 2, 3):
        for k in F[s]:
            if k not in T[s] or k not in O[s]:
                continue
            f, t, o, ot = F[s][k], T[s][k], O[s][k], OT[s][k]
            fm, om = N.geo_check(f)[0], N.geo_check(o)[0]
            ag = agree(f, o)
            acc_x = fm and ag
            ff = ok(f) if fm else ok(t); xv = ok(f) if acc_x else ok(t); oss = ok(o) if om else ok(ot)
            per.setdefault(k, []).append((ff, xv, ok(t), oss))
            tk["FF"] += tok(f) + (0 if fm else tok(t)); tk["XV"] += tok(f) + tok(o) + (0 if acc_x else tok(t))
            tk["THINK"] += tok(t); tk["OSS"] += tok(o) + (0 if om else tok(ot)); tk["n"] += 1
            if fm and not ok(f):
                st["leak"] += 1; st["leak_flag"] += not ag; st["leak_edge_only"] += bool(f["per_variant"].get("identity"))
                st["leak_edge_only_flag"] += bool(f["per_variant"].get("identity")) and not ag
            if fm and ok(f):
                st["right"] += 1; st["fa"] += not ag; st["fa_oss_wrong"] += (not ag) and not ok(o)
    report(f"{m} geometry", per, tk, ("FF", "XV", "THINK", "OSS"))
    print(f"  XV flags {st['leak_flag']}/{st['leak']} leaked fact programs (pass MR, wrong; edge-case-only {st['leak_edge_only_flag']}/{st['leak_edge_only']}) "
          f"and {st['fa']}/{st['right']} right MR-passing ones ({st['fa_oss_wrong']} of these where gpt-oss-20b is wrong)")
    return per, tk, st


def words(m, bench):
    per, tk, st = {}, Counter(), Counter()
    for s in (1, 2, 3):
        F = {r["id"]: r for r in _rows(f"{XRES}/opt_{m}_{bench}_freev_s{s}.jsonl")}
        O = {r["id"]: r for r in _rows(f"{XRES}/opt_{REF}_{bench}_freev_s{s}.jsonl")}
        V = {r["id"]: r for r in _rows(f"{XRES}/verify_{m}_{bench}_s{s}.jsonl")}
        T = {r["id"]: r for r in _rows(f"{XRES}/opt_{m}_{bench}_thinkfree_s{s}.jsonl")}
        OT = {r["id"]: r for r in _rows(f"{XRES}/opt_{REF}_{bench}_thinkfree_s{s}.jsonl")}
        for i, f in F.items():
            if i not in T or i not in O or i not in OT:
                continue
            t, o, v = T[i], O[i], V.get(i)
            runs = ok_(f); vpass = bool(runs and v and v["passed"]); ag = runs and ok_(o) and correct(f["pred"], str(o["pred"]))
            tf, tt, to, tv = f.get("out_tokens") or 0, t.get("out_tokens") or 0, o.get("out_tokens") or 0, (v or {}).get("out_tokens") or 0
            ffv = f["correct"] if vpass else t["correct"]; xv = f["correct"] if ag else t["correct"]
            oss = o["correct"] if ok_(o) else OT[i]["correct"]
            per.setdefault(i, []).append((ffv, xv, t["correct"], oss))
            tk["FF-V"] += tf + tv + (0 if vpass else tt); tk["XV"] += tf + to + (0 if ag else tt); tk["THINK"] += tt
            tk["OSS"] += to + (0 if ok_(o) else OT[i].get("out_tokens") or 0); tk["n"] += 1
            if runs:
                kk = "right" if f["correct"] else "wrong"
                st[(kk, "n")] += 1; st[(kk, "xv")] += not ag; st[(kk, "fv")] += not vpass
    report(f"{m} {bench}", per, tk, ("FF-V", "XV", "THINK", "OSS"))
    print(f"  running-but-wrong programs flagged: XV {st[('wrong', 'xv')]}/{st[('wrong', 'n')]}, FF-V {st[('wrong', 'fv')]}/{st[('wrong', 'n')]}; "
          f"right ones flagged: XV {st[('right', 'xv')]}/{st[('right', 'n')]}, FF-V {st[('right', 'fv')]}/{st[('right', 'n')]}")
    return per, tk


def report(name, per, tk, arms):
    n = tk["n"]
    acc = {a: 100 * sum(x[j] for v in per.values() for x in v) / n for j, a in enumerate(arms)}
    print(f"=== {name} ({len(per)} items, {n} rows): " + " | ".join(
        f"{a} {acc[a]:.1f}% @ {tk[a] / n / 1000:.2f}k ({100 * tk[a] / tk['THINK']:.0f}%)" for a in arms))
    for j, a in enumerate(arms):
        if a == "XV":
            continue
        mu, lo, hi = ci({i: sum(x[1] - x[j] for x in v) / len(v) for i, v in per.items()})
        print(f"  XV - {a:5s} {mu:+.1f} [{lo:+.1f}, {hi:+.1f}]")


def main():
    for m in sys.argv[1:] or ["q8b", "q14a"]:
        geometry(m)
        for bench in ("bwor", "logior"):
            words(m, bench)


if __name__ == "__main__":
    main()
