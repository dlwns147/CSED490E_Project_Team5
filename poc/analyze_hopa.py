"""HO-PA (docs/prereg/PREREG_SQL.md, addendum HO-PA; offline on stored rows): SQL-PA's peer check on word problems and tool calls.
Per model A and cell: A's cheap answer -> its free check -> a peer's cheap answer for the same item and seed is the same: answer with
A's; else A's T->T (think; on its visible failure the next seed's think). A failed check escalates without running the peer.
Word problems (OptiBench third, BWOR, LogiOR, OptMATH; results/x3, every model given the same library fact): cheap = formx, think =
formxt, short think = formxtb2000; check = the program runs and prints a value (analyze_ho.ok_); same answer = within the grader's
tolerance (run_nlopt.correct, as HO-X). Tool calls (BFCL, results/tc, non-live / live): cheap N, think T, short think SB; check =
schema validation; same answer = the same canonical calls (grade_tc). Against T->T and the no-label default SB->T->T (SB; on its
visible failure T->T); paired 95% intervals over items (seed means); utility = accuracy - 0.5 x ktokens, the peer's tokens counted.
Error coincidence: of A's passing wrong cheap answers where the other answer also passes and is wrong, the share that are the same.
usage: python analyze_hopa.py [--words | --tc]   (default both)"""
import json, os, random, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_ho import ok_  # noqa: E402
from analyze_ho3 import ci  # noqa: E402
from run_nlopt import RES as XRES, _rows, correct  # noqa: E402

PEER = {"q8b": "q35", "q14a": "q35", "q35": "q8b", "n3n": "q35"}   # pre-registered: the other Qwen generation; Nemotron: Qwen3.5-9B
SAME = {"q8b": "q14a", "q14a": "q8b"}                              # the same generation (Qwen3)
FAMILY = {"q8b": "n3n", "q14a": "n3n", "q35": "n3n"}               # another family (Nemotron-3-Nano)
BENCH = ("optibench", "bwor", "logior", "optmath")
LAM = 0.5


def word_rows(m, b):
    """{seed: {id: (passes, right, tokens, answer)}} per arm, or None if a seed is missing"""
    out = {}
    for a in ("formx", "formxt", "formxtb2000"):
        out[a] = {}
        for s in (1, 2, 3):
            R = _rows(f"{XRES}/opt_{m}_{b}_{a}_s{s}.jsonl")
            if not R:
                return None
            out[a][s] = {r["id"]: (ok_(r), bool(r["correct"]), r.get("out_tokens") or 0, r.get("pred")) for r in R}
    return out


def same_word(x, y):
    return x[0] and y[0] and correct(x[3], str(y[3]))


def tc_rows(m, split):
    from analyze_tc import DATA, NONLIVE, load
    cats = {x["id"]: x["cat"] for x in (json.loads(l) for l in open(DATA))}
    out = {"formx": {}, "formxt": {}, "formxtb2000": {}}
    for s in (1, 2, 3):
        D = load(m, s)
        if D is None:
            return None
        G, C, T, SB = D
        keep = [i for i in C if cats.get(i) is not None and (cats[i] in NONLIVE) == (split == "non-live") and i in G and i in T and i in SB
                and {"N", "T", "SB"} <= set(G[i])]
        out["formx"][s] = {i: (G[i]["N"]["chk"] != "fail", G[i]["N"]["ok"], C[i]["n_tok"], json.dumps(G[i]["N"]["calls"], sort_keys=True)) for i in keep}
        out["formxt"][s] = {i: (G[i]["T"]["chk"] != "fail", G[i]["T"]["ok"], T[i]["out_tokens"], None) for i in keep}
        out["formxtb2000"][s] = {i: (G[i]["SB"]["chk"] != "fail", G[i]["SB"]["ok"], SB[i]["out_tokens"], json.dumps(G[i]["SB"]["calls"], sort_keys=True)) for i in keep}
    return out


def same_tc(x, y):
    return x[0] and y[0] and x[3] == y[3]


def policies(A, others, same):
    """{(id, seed): {policy: (right, tokens)}} over the items every arm of A (all seeds) and every other model's cheap arm cover"""
    F, T, SB = A["formx"], A["formxt"], A["formxtb2000"]
    ids = set.intersection(*(set(X[s]) for X in (F, T, SB) for s in (1, 2, 3)), *(set(O["formx"][s]) for O in others.values() for s in (1, 2, 3)))
    out = {}
    for s in (1, 2, 3):
        s2 = s % 3 + 1
        for i in ids:
            f, t, t2, sb = F[s][i], T[s][i], T[s2][i], SB[s][i]
            tt = (t[1], t[2]) if t[0] else (t2[1], t[2] + t2[2])
            r = {"T->T": tt, "SB->T->T": (sb[1], sb[2]) if sb[0] else (tt[0], sb[2] + tt[1]),
                 "N->T->T": (f[1], f[2]) if f[0] else (tt[0], f[2] + tt[1])}
            for name, o in [("own", F[s2][i])] + [(k, O["formx"][s][i]) for k, O in others.items()]:
                for tail, e in (("T->T", tt), ("SB->T->T", r["SB->T->T"])):   # after a failed check or a disagreement: T->T or the default
                    if not f[0]:
                        r[f"N->{name}->{tail}"] = (e[0], f[2] + e[1])
                    elif same(f, o):
                        r[f"N->{name}->{tail}"] = (f[1], f[2] + o[2])
                    else:
                        r[f"N->{name}->{tail}"] = (e[0], f[2] + o[2] + e[1])
            out[(i, s)] = r
    return out


def per_q(rows, k):
    acc = {}
    for (i, s), v in rows.items():
        a, t = v[k]
        acc.setdefault(i, []).append((float(a), float(a) - LAM / 100 * t / 1000))   # accuracy as a fraction: 0.5 points = 0.005
    return {i: (sum(x for x, _ in v) / len(v), sum(u for _, u in v) / len(v)) for i, v in acc.items()}


def coincide(A, other):
    """{id: [same, pairs]}: A's passing wrong cheap answer against another passing wrong answer (other(s, i) -> its row)"""
    out = {}
    for s in (1, 2, 3):
        for i, f in A["formx"][s].items():
            if not f[0] or f[1]:
                continue
            o = other(s, i)
            if not o or not o[0] or o[1]:
                continue
            x = out.setdefault(i, [0, 0]); x[0] += SAME_FN(f, o); x[1] += 1
    return out


def rate(d, qs):
    return 100 * sum(d[i][0] for i in qs if i in d) / max(1, sum(d[i][1] for i in qs if i in d))


def boot_diff(a, b, n=2000):
    qs, rng = sorted(set(a) | set(b)), random.Random(0)
    bs = sorted(rate(a, q) - rate(b, q) for q in ([rng.choice(qs) for _ in qs] for _ in range(n)))
    return rate(a, qs) - rate(b, qs), bs[int(0.025 * n)], bs[int(0.975 * n) - 1]


SAME_FN = same_word


def run(kind):
    global SAME_FN
    SAME_FN = same_word if kind == "words" else same_tc
    models = ("q8b", "q14a", "q35", "n3n") if kind == "words" else ("q8b", "q14a", "q35")
    cells = [(b, m) for b in BENCH for m in models] if kind == "words" else [(sp, m) for sp in ("non-live", "live") for m in models]
    load = word_rows if kind == "words" else tc_rows
    C, pooled, cnt = {}, {}, {"win": 0, "loss": 0, "n": 0}
    for c, m in cells:
        A = load(m, c)
        if A is None:
            print(f"=== {kind} {c} {m}: rows missing"); continue
        names = {"peer": PEER[m], "same generation": SAME.get(m), "other family": FAMILY.get(m)}
        others = {o: load(o, c) for o in names.values() if o and o in models}
        others = {o: O for o, O in others.items() if O is not None}
        rows = policies(A, others, SAME_FN)
        ks = list(next(iter(rows.values())))
        tok = {k: sum(v[k][1] for v in rows.values()) / len(rows) for k in ks}
        acc = {k: 100 * sum(v[k][0] for v in rows.values()) / len(rows) for k in ks}
        Q = {k: per_q(rows, k) for k in ks}
        ids = list(Q["T->T"])
        P = pooled.setdefault(m, {})
        for k in ks:
            P.setdefault(k, {}).update({(c, i): v for i, v in Q[k].items()})
            P.setdefault("_tok_" + k, []).append((tok[k], len(ids)))
        print(f"=== {kind} {c} {m} ({len(ids)} items, 3 seeds)")
        for k in ks:
            line = f"  {k:>27}: {acc[k]:.1f}% @ {tok[k] / 1000:.2f}k, utility {acc[k] - LAM * tok[k] / 1000:.1f}"
            o = k.split("->")[1] if k.count("->") >= 3 else None
            if o:
                base = "T->T" if k.endswith("->" + o + "->T->T") else "SB->T->T"
                da = ci({i: Q[k][i][0] - Q["T->T"][i][0] for i in ids})
                du = ci({i: Q[k][i][1] - Q["SB->T->T"][i][1] for i in ids})
                role = next((r for r, x in names.items() if x == o), "own resample")
                line += (f" | vs T->T acc {da[0]:+.1f} [{da[1]:+.1f}, {da[2]:+.1f}] at {100 * tok[k] / tok['T->T']:.0f}%;"
                         f" vs SB->T->T utility {du[0]:+.1f} [{du[1]:+.1f}, {du[2]:+.1f}] at {100 * tok[k] / tok['SB->T->T']:.0f}%  ({role})")
                if role == "peer" and base == "SB->T->T":
                    cnt["n"] += 1; cnt["win"] += du[1] > 0; cnt["loss"] += du[2] < 0
            print(line)
        C[(c, m)] = (A, others)
    h1 = h2 = 0
    print(f"--- {kind}: pre-registered tests per model, pooled over its cells (items weighted equally)")
    for m, P in pooled.items():
        p = PEER[m]
        tk = lambda k: sum(t * n for t, n in P["_tok_" + k]) / sum(n for _, n in P["_tok_" + k])
        ids = list(P["T->T"])
        da = ci({i: P[f"N->{p}->T->T"][i][0] - P["T->T"][i][0] for i in ids})
        du = ci({i: P[f"N->{p}->SB->T->T"][i][1] - P["SB->T->T"][i][1] for i in ids})
        ds = ci({i: P[f"N->{p}->SB->T->T"][i][0] - P["SB->T->T"][i][0] for i in ids})   # non-inferiority in accuracy (margin 2 points)
        a1 = da[2] >= 0 and tk(f"N->{p}->T->T") <= 0.9 * tk("T->T"); a2 = du[1] > 0 and ds[1] > -2.0
        h1 += a1; h2 += a2
        print(f"  {m} <- {p} ({len(ids)} items): N->peer->T->T vs T->T acc {da[0]:+.1f} [{da[1]:+.1f}, {da[2]:+.1f}] at "
              f"{100 * tk(f'N->{p}->T->T') / tk('T->T'):.0f}% of its tokens [{a1}]; N->peer->SB->T->T vs SB->T->T utility {du[0]:+.1f} "
              f"[{du[1]:+.1f}, {du[2]:+.1f}], accuracy {ds[0]:+.1f} [{ds[1]:+.1f}, {ds[2]:+.1f}], at {100 * tk(f'N->{p}->SB->T->T') / tk('SB->T->T'):.0f}% of its tokens [{a2}]")
    print(f"*** {kind}: HO-PA1 {h1} of {len(pooled)}; HO-PA2 {h2} of {len(pooled)}; cells where N->peer->SB->T->T beats SB->T->T "
          f"(lower bound > 0) {cnt['win']} / loses (upper bound < 0) {cnt['loss']} of {cnt['n']}")
    pa3 = n3 = 0
    for m in models:
        src = {}
        for (c, mm), (A, others) in C.items():
            if mm != m:
                continue
            S = {"own cheap, next seed": lambda s, i, A=A: A["formx"][s % 3 + 1].get(i),
                 "own short think": lambda s, i, A=A: A["formxtb2000"][s].get(i)}
            for o, O in others.items():
                S[f"{o} cheap"] = lambda s, i, O=O: O["formx"][s].get(i)
            for k, f in S.items():
                src.setdefault(k, {}).update({(c, i): v for i, v in coincide(A, f).items()})
        if not src:
            continue
        print(f"--- {kind} {m}: error coincidence (same answer among both-wrong passing pairs), pooled over cells")
        for k, d in src.items():
            print(f"  {k:>22}: {rate(d, list(d)):.0f}% (n {sum(x[1] for x in d.values())})")
        p = f"{PEER[m]} cheap"
        if p in src:
            mu, lo, hi = boot_diff(src["own cheap, next seed"], src[p]); n3 += 1
            print(f"  own cheap, next seed - {p}: {mu:+.1f} [{lo:+.1f}, {hi:+.1f}]"); pa3 += lo > 0
            mu, lo, hi = boot_diff(src["own short think"], src[p])
            print(f"  own short think - {p}: {mu:+.1f} [{lo:+.1f}, {hi:+.1f}] (reported)")
    print(f"*** {kind}: HO-PA3 {pa3} of {n3}")


if __name__ == "__main__":
    for kind in ("words", "tc"):
        if f"--{'tc' if kind == 'words' else 'words'}" not in sys.argv:
            run(kind)
