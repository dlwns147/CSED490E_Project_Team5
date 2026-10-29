"""SQL-F (docs/prereg/PREREG_SQL.md, addendum SQL-F): the fact on text-to-SQL. Per model, SQL-1's rows (tag m, no fact) against the
rows with the fact (tag m + 'f': card and library), both through analyze_sql.py's policies; the card-only / library-only non-thinking
queries (tags m + 'c' / m + 'l', cheap arm only) against N. Paired 95% intervals over questions (seed means), tokens per question.
usage: python analyze_sqlf.py [model ...]   (default q8b q14a q35)"""
import json, os, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_sql as A  # noqa: E402
from analyze_ho3 import ci  # noqa: E402
from run_nlopt import _rows  # noqa: E402


def cheap_only(m):
    """{id: [N right per seed]}, N tokens, N passes, N leaks: a tag with only the cheap arm graded"""
    per, tok, n, ps, lk = {}, 0, 0, 0, 0
    for s in (1, 2, 3):
        gp = f"{A.RES}/grades_{m}_s{s}.json"
        if not os.path.exists(gp):
            return None
        G = json.load(open(gp)); G.pop("_gold_fail", None)
        C = {r["id"]: r for r in _rows(f"{A.RES}/{m}_cheap_s{s}.jsonl")}
        for i, g in G.items():
            if "N" in g and i in C:
                per.setdefault(i, []).append(g["N"]["ok"]); tok += C[i]["n_tok"]; n += 1
                ps += C[i]["c_n"] == "pass"; lk += C[i]["c_n"] == "pass" and not g["N"]["ok"]
    return per, tok, n, ps, lk


def main():
    score = Counter()
    for m in [a for a in sys.argv[1:] if not a.startswith("--")] or ["q8b", "q14a", "q35"]:
        r0, r1 = A.cell(m), A.cell(m + "f")
        if not r0 or not r1:
            print(f"=== {m}: rows missing"); continue
        (p0, t0, n0, c0, _), (p1, t1, n1, c1, _) = r0, r1
        ids = sorted(set(p0) & set(p1))
        mean = lambda per, i, k: sum(x[k] for x in per[i]) / len(per[i])
        acc = lambda per, k: 100 * sum(mean(per, i, k) for i in ids) / len(ids)
        kt = lambda tok, n, k: tok[k] / n["all"] / 1000
        d = lambda pa, a, pb, b: ci({i: mean(pa, i, a) - mean(pb, i, b) for i in ids})
        print(f"=== {m} ({len(ids)} questions in both): N passes {100 * c0['n_pass'] / n0['all']:.0f}% -> {100 * c1['n_pass'] / n1['all']:.0f}% "
              f"with the fact; leak {100 * c0['n_leak'] / c0['n_pass']:.1f}% -> {100 * c1['n_leak'] / c1['n_pass']:.1f}%; "
              f"power {100 * c0['n_caught'] / c0['n_wrong']:.0f}% -> {100 * c1['n_caught'] / c1['n_wrong']:.0f}%")
        for k in ("N", "T", "SB", "N->R", "N->T", "SB->T->T", "T->T"):
            print(f"  {k}: {acc(p0, k):.1f}% @ {kt(t0, n0, k):.2f}k -> {acc(p1, k):.1f}% @ {kt(t1, n1, k):.2f}k with the fact "
                  "(%+.1f [%+.1f, %+.1f])" % d(p1, k, p0, k))
        for a, b in (("N->T", "T"), ("SB->T->T", "T->T"), ("N->R", "N->T")):
            mu, lo, hi = d(p1, a, p1, b)
            print(f"  with the fact: {a} - {b} {mu:+.1f} [{lo:+.1f}, {hi:+.1f}] at {100 * t1[a] / t1[b]:.0f}% of its tokens")
        mu, lo, hi = d(p1, "N->T", p0, "T")
        print(f"  {m}f N->T - {m} T (no fact) {mu:+.1f} [{lo:+.1f}, {hi:+.1f}] at {100 * kt(t1, n1, 'N->T') / kt(t0, n0, 'T'):.0f}% of its tokens")
        for x, name in (("c", "card only"), ("l", "library only")):
            r = cheap_only(m + x)
            if r:
                per, tok, n, ps, lk = r
                js = sorted(set(per) & set(p0))
                mu, lo, hi = ci({i: sum(per[i]) / len(per[i]) - mean(p0, i, "N") for i in js})
                print(f"  N, {name}: {100 * sum(sum(per[i]) / len(per[i]) for i in js) / len(js):.1f}% @ {tok / n / 1000:.2f}k "
                      f"({mu:+.1f} [{lo:+.1f}, {hi:+.1f}] vs N); passes {100 * ps / n:.0f}%, leak {100 * lk / max(1, ps):.1f}%")
        score["F1"] += acc(p1, "N") >= acc(p0, "N") + 2.0
        mu, lo, hi = d(p1, "N->T", p1, "T")
        score["F2"] += hi >= 0 and t1["N->T"] <= 0.90 * t1["T"]
        score["F3"] += acc(p1, "T") >= acc(p0, "T") + 1.0
        score["F4"] += d(p1, "SB->T->T", p0, "SB->T->T")[1] > 0
        score["F5"] += 100 * c1["n_leak"] / c1["n_pass"] <= 100 * c0["n_leak"] / c0["n_pass"] - 3.0
    print(f"*** SQL-F1 {score['F1']}; SQL-F2 {score['F2']}; SQL-F3 {score['F3']}; SQL-F4 {score['F4']}; SQL-F5 {score['F5']} "
          "(each needs >= 2 of 3)")


if __name__ == "__main__":
    main()
