"""SQL-FA (docs/prereg/PREREG_SQL.md, addendum SQL-FA): does the library's precision decide what the fact does? Per model, the
non-thinking query (N) and the think (T) with the fact whose library is admitted by agreement with the short think (tag m + 'fg'), by
gold as right (m + 'fr') or as wrong (m + 'fw'), against no fact (SQL-1, tag m) and the check-admitted library (SQL-F, m + 'f').
Paired 95% intervals over questions (seed means); predictions are the pre-registered ones (SQL-F's effect per number of right library
queries, weighted by each library's composition).
usage: python analyze_sqlfa.py [model ...]   (default q8b q14a)"""
import json, os, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_ho3 import ci  # noqa: E402
from analyze_sql import RES  # noqa: E402
from run_nlopt import _rows  # noqa: E402

PRED = {"q8b": {"g": (4.3, -0.5), "r": (5.7, 1.1), "w": (0.0, -3.9)},     # (N, T) vs no fact, points
        "q14a": {"g": (4.9, 0.4), "r": (6.5, 2.3), "w": (-2.4, -3.3)}}
NAME = {"": "no fact", "f": "check (SQL-F)", "fg": "agree", "fr": "right", "fw": "wrong"}


def load(tag):
    """{id: {"N": mean right, "T": mean right}}, tokens per question {"N", "T"}; None if a seed is missing"""
    per, tok, n = {}, Counter(), 0
    for s in (1, 2, 3):
        gp = f"{RES}/grades_{tag}_s{s}.json"
        if not os.path.exists(gp):
            return None
        G = json.load(open(gp)); G.pop("_gold_fail", None)
        C = {r["id"]: r for r in _rows(f"{RES}/{tag}_cheap_s{s}.jsonl")}
        T = {r["id"]: r for r in _rows(f"{RES}/{tag}_think_s{s}.jsonl")}
        for i, g in G.items():
            if {"N", "T"} <= set(g) and i in C and i in T:
                d = per.setdefault(i, {"N": [], "T": []})
                d["N"].append(g["N"]["ok"]); d["T"].append(g["T"]["ok"])
                tok["N"] += C[i]["n_tok"]; tok["T"] += T[i]["out_tokens"]; n += 1
    return {i: {a: sum(v) / len(v) for a, v in d.items()} for i, d in per.items() if len(d["N"]) == 3}, {a: tok[a] / n for a in tok}


def main():
    score, pooled = Counter(), {}
    for m in [a for a in sys.argv[1:] if not a.startswith("--")] or ["q8b", "q14a"]:
        R = {x: load(m + x) for x in NAME}
        if any(v is None for v in R.values()):
            print(f"=== {m}: rows missing:", [NAME[x] for x, v in R.items() if v is None]); continue
        ids = sorted(set.intersection(*(set(v[0]) for v in R.values())))
        d = lambda a, x, y: ci({i: R[x][0][i][a] - R[y][0][i][a] for i in ids})
        acc = lambda a, x: 100 * sum(R[x][0][i][a] for i in ids) / len(ids)
        print(f"=== {m} ({len(ids)} questions in all five)")
        for x in NAME:
            print(f"  {NAME[x]:>14}: N {acc('N', x):.1f}% @ {R[x][1]['N'] / 1000:.2f}k, T {acc('T', x):.1f}% @ {R[x][1]['T'] / 1000:.2f}k", end="")
            if x:
                (mn, ln, hn), (mt, lt, ht) = d("N", x, ""), d("T", x, "")
                print(f"; vs no fact N {mn:+.1f} [{ln:+.1f}, {hn:+.1f}], T {mt:+.1f} [{lt:+.1f}, {ht:+.1f}]", end="")
                if x in ("fg", "fr", "fw"):
                    pn, pt = PRED[m][x[1]]
                    hit = (abs(mn - pn) <= 2.0) + (abs(mt - pt) <= 2.0)
                    score["FA3"] += hit; score["FA3_n"] += 2
                    print(f" (predicted N {pn:+.1f}, T {pt:+.1f}: {hit} / 2 within 2.0)", end="")
            print()
        for a in ("N", "T"):
            mu, lo, hi = d(a, "fr", "fw")
            print(f"  {a}: right - wrong library {mu:+.1f} [{lo:+.1f}, {hi:+.1f}]")
            score["FA1_" + a] += lo > 0
        for x in ("fr", "fg"):
            mu, lo, hi = d("T", x, "f")
            print(f"  T: {NAME[x]} - check library {mu:+.1f} [{lo:+.1f}, {hi:+.1f}]")
        score["FA2"] += d("T", "fr", "f")[1] > 0
        score["FA4b"] += d("T", "fg", "")[2] >= 0
        pooled.update({(m, i): R["fg"][0][i]["T"] - R["f"][0][i]["T"] for i in ids})
    if not pooled:
        return
    mu, lo, hi = ci(pooled)
    print(f"  pooled over models, T: agree - check library {mu:+.1f} [{lo:+.1f}, {hi:+.1f}]")
    print(f"*** SQL-FA1 N {score['FA1_N']}, T {score['FA1_T']} (each needs 2 of 2); FA2 {score['FA2']} (2 of 2); "
          f"FA3 {score['FA3']} / {score['FA3_n']} cells (needs 9 of 12); FA4 pooled lower bound {lo:+.1f} (> 0) and "
          f"T(agree) not below no fact in {score['FA4b']} (2 of 2)")


if __name__ == "__main__":
    main()
