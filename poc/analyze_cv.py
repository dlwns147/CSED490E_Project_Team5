"""CV-1 (docs/prereg/PREREG_CV.md): the trained cascades on BIRD dev against SQL-1's fixed orders (Qwen3-8B, tag q8b). Escalation is
SQL-1's T->T of the base model (T at seed s; where its query fails the check, T of seed s mod 3 + 1), as poc/analyze_sql.py.
  cv  quick query (adapter) -> DEFER or failed check: T->T; else ACCEPT (P(ACCEPT) >= tau) the query, DEFER: T->T
  c1  quick query (adapter, plain RL) -> failed check: T->T
  c2  SQL-1's base query -> failed check: T->T; else the trained gate as cv
Accuracy and output tokens per question (turn 2: 1 token), paired 95% intervals over questions (seed means), utility = acc - 0.5 x ktokens.
usage: python analyze_cv.py [cv tag] [c1 tag] [c2 tag]   (default q8bcv q8bc1 q8bc2)"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_ho3 import ci  # noqa: E402
from run_nlopt import _rows  # noqa: E402

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "sql")
LAM = 0.005


def base(m="q8b"):
    """{(id, seed): {policy: (right, tokens)}} for SQL-1's fixed orders, with analyze_sql.cell's question filter"""
    G, C, T, SB = {}, {}, {}, {}
    for s in (1, 2, 3):
        G[s] = json.load(open(f"{RES}/grades_{m}_s{s}.json")); G[s].pop("_gold_fail", None)
        C[s], T[s], SB[s] = ({r["id"]: r for r in _rows(f"{RES}/{m}_{a}_s{s}.jsonl")} for a in ("cheap", "think", "sb"))
    out = {}
    for s in (1, 2, 3):
        s2 = s % 3 + 1
        for i, c in C[s].items():
            g, g2 = G[s].get(i, {}), G[s2].get(i, {})
            if not {"N", "T", "SB"} <= set(g) or not {"N", "T"} <= set(g2) or i not in T[s] or i not in SB[s] or i not in T[s2] \
                    or i not in C[s2] or (c["c_n"] != "pass" and "R" not in g):
                continue
            tt, st, t2t = T[s][i]["out_tokens"], SB[s][i]["out_tokens"], T[s2][i]["out_tokens"]
            ft, fs = g["T"]["chk"] != "pass", g["SB"]["chk"] != "pass"
            tto = (g2["T"]["ok"], tt + t2t) if ft else (g["T"]["ok"], tt)
            out[(i, s)] = {"T": (g["T"]["ok"], tt), "T->T": tto, "SB->T->T": (g["SB"]["ok"], st) if not fs else (tto[0], st + tto[1]),
                           "N->T->T": (g["N"]["ok"], c["n_tok"]) if c["c_n"] == "pass" else (tto[0], c["n_tok"] + tto[1])}
    return out


def trained(tag, kind, B, tau=0.5):
    """{(id, seed): (right, tokens, decision)} for a trained cascade; decision: accept / defer / fail (check) / turn1 (DEFER)"""
    out = {}
    for s in (1, 2, 3):
        gp = f"{RES}/grades_{tag}_s{s}.json"
        if not os.path.exists(gp):
            return None
        G = json.load(open(gp)); G.pop("_gold_fail", None)
        for r in _rows(f"{RES}/{tag}_cheap_s{s}.jsonl"):
            k = (r["id"], s)
            if k not in B or "N" not in G.get(r["id"], {}):
                continue
            ok, (tt_ok, tt_tok) = G[r["id"]]["N"]["ok"], B[k]["T->T"]
            if r.get("dfr"):
                out[k] = (tt_ok, r["n_tok"] + tt_tok, "turn1")
            elif r["c_n"] != "pass":
                out[k] = (tt_ok, r["n_tok"] + tt_tok, "fail")
            elif kind == "c1":
                out[k] = (ok, r["n_tok"], "accept")
            elif r.get("g_acc") is not None and r["g_acc"] >= tau:
                out[k] = (ok, r["n_tok"] + 1, "accept")
            else:
                out[k] = (tt_ok, r["n_tok"] + 1 + tt_tok, "defer")
    return out


def per_q(rows):
    """{id: (mean right, mean utility in accuracy units)} over seeds"""
    acc = {}
    for (i, s), v in rows.items():
        acc.setdefault(i, []).append((float(v[0]), float(v[0]) - LAM * v[1] / 1000))
    return {i: (sum(x for x, _ in v) / len(v), sum(u for _, u in v) / len(v)) for i, v in acc.items()}


def summary(rows):
    n = len(rows)
    return 100 * sum(v[0] for v in rows.values()) / n, sum(v[1] for v in rows.values()) / n / 1000


def main():
    tags = (sys.argv[1:] + ["q8bcv", "q8bc1", "q8bc2"][len(sys.argv[1:]):])[:3]
    B = base()
    pol = {k: {key: v[k] for key, v in B.items()} for k in ("T", "T->T", "SB->T->T", "N->T->T")}
    for kind, tag in zip(("cv", "c1", "c2"), tags):
        r = trained(tag, kind, B)
        if r:
            pol[kind] = r
    ids = None
    for k, rows in pol.items():
        q = {i for i, _ in rows}
        ids = q if ids is None else ids & q
    Q = {k: per_q({key: v for key, v in rows.items() if key[0] in ids}) for k, rows in pol.items()}
    print(f"=== CV-1, Qwen3-8B, BIRD dev: {len(ids)} questions in every arm, 3 seeds")
    for k, rows in pol.items():
        rr = {key: v for key, v in rows.items() if key[0] in ids}
        a, t = summary(rr)
        extra = ""
        if k in ("cv", "c1", "c2"):
            d = [v[2] for v in rr.values()]
            acc = [v for v in rr.values() if v[2] == "accept"]
            extra = (f" | answers itself {100 * len(acc) / len(d):.0f}% (wrong {100 * sum(not v[0] for v in acc) / max(1, len(acc)):.1f}%), "
                     f"turn-1 DEFER {100 * d.count('turn1') / len(d):.0f}%, check fails {100 * d.count('fail') / len(d):.0f}%, "
                     f"gate defers {100 * d.count('defer') / len(d):.0f}%")
        print(f"  {k}: {a:.1f}% @ {t:.2f}k, utility {a - 0.5 * t:.1f}{extra}")
    d = lambda x, y, j: ci({i: Q[x][i][j] - Q[y][i][j] for i in ids})
    tok = lambda k: summary({key: v for key, v in pol[k].items() if key[0] in ids})[1]
    if "cv" in pol:
        for y in ("T->T", "SB->T->T", "c1", "c2"):
            if y in pol:
                print(f"  cv - {y}: accuracy %+.1f [%+.1f, %+.1f], utility %+.1f [%+.1f, %+.1f], at {100 * tok('cv') / tok(y):.0f}%% of its tokens"
                      % (*d("cv", y, 0), *d("cv", y, 1)))
        p1 = d("cv", "T->T", 0)[2] >= 0 and tok("cv") <= 0.75 * tok("T->T")
        p2 = d("cv", "SB->T->T", 1)[1] > 0
        p3 = "c1" in pol and d("cv", "c1", 1)[1] > 0
        p4 = "c2" in pol and d("cv", "c2", 1)[1] > 0
        acc = [v for key, v in pol["cv"].items() if key[0] in ids and v[2] == "accept"]
        n = sum(1 for key in pol["cv"] if key[0] in ids)
        p5 = len(acc) >= 0.4 * n and sum(not v[0] for v in acc) <= 0.2 * len(acc)
        print(f"*** CV-P1 {p1}; CV-P2 {p2}; CV-P3 {p3}; CV-P4 {p4}; CV-P5 {p5}")
        for tau in (0.1, 0.3, 0.5, 0.7, 0.9):
            a, t = summary({key: v for key, v in trained(tags[0], "cv", B, tau).items() if key[0] in ids})
            print(f"  frontier tau {tau}: {a:.1f}% @ {t:.2f}k")
    for k in ("cv", "c1"):
        if k in pol:
            G = {}
            for s in (1, 2, 3):
                g = json.load(open(f"{RES}/grades_{tags[0 if k == 'cv' else 1]}_s{s}.json")); g.pop("_gold_fail", None)
                G.update({(i, s): v["N"]["ok"] for i, v in g.items() if "N" in v and i in ids})
            b = {}
            for s in (1, 2, 3):
                g = json.load(open(f"{RES}/grades_q8b_s{s}.json")); g.pop("_gold_fail", None)
                b.update({(i, s): v["N"]["ok"] for i, v in g.items() if "N" in v and i in ids})
            print(f"  quick query's own accuracy, {k}: {100 * sum(G.values()) / len(G):.1f}% (base {100 * sum(b.values()) / len(b):.1f}%)")


if __name__ == "__main__":
    main()
