"""SQL-AND (docs/prereg/PREREG_SQL.md, addendum SQL-AND): two checks from different families. A's passing quick answer is accepted
only when the first check's quick answer agrees and then the second's does too (the second is asked only after the first agrees);
otherwise A's no-label default SB->T->T. Against the single-peer cascade (SQL-PA / HO-PA) and SB->T->T: paired 95% intervals over
items (seed means), utility = accuracy - 0.5 x ktokens, every check's tokens counted. Theory (SQL-DV's operating-point model): a check
enters only through r = P(agrees | A's passing answer right), e = P(agrees | wrong) and its tokens; --predict prints the single
checks' (r, e) and the gains the linear model gives for the two-check rule if the checks agree independently given A's correctness
(r1 r2, e1 e2) — written before any joint agreement is computed.
usage: python analyze_and.py [--predict]"""
import contextlib, io, sys

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
with contextlib.redirect_stdout(io.StringIO()):   # analyze_dv's imports print word-problem tables
    from analyze_dv import cascade, default, quick, same
from analyze_ho3 import ci  # noqa: E402

# (type, A): (first check, second check); decision cells first, then BIRD dev (reported)
CELLS = {("sql train", "q8bpa"): ("q35pa", "n3npa"), ("sql train", "q14apa"): ("q35pa", "n3npa"), ("sql train", "q35pa"): ("q8bpa", "n3npa"),
         ("tc", "q8b"): ("q35", "l8"), ("tc", "q14a"): ("q35", "l8"), ("tc", "q35"): ("q8b", "l8"),
         ("sql dev", "q8b"): ("q35", "l8"), ("sql dev", "q14a"): ("q35", "l8"), ("sql dev", "q35"): ("q8b", "l8")}


def cascade2(D, NA, X1, X2):
    out = {}
    for (i, s), d in D.items():
        n, x1, x2 = NA[s].get(i), X1[s].get(i), X2[s].get(i)
        if n is None or x1 is None or x2 is None:
            continue
        if not n[0]:
            out[(i, s)] = (d[0], n[2] + d[1])
        elif not same(None, n, x1):
            out[(i, s)] = (d[0], n[2] + x1[2] + d[1])
        elif same(None, n, x2):
            out[(i, s)] = (n[1], n[2] + x1[2] + x2[2])
        else:
            out[(i, s)] = (d[0], n[2] + x1[2] + x2[2] + d[1])
    return out


def util(rows):
    """{id: mean utility over seeds}, items with all three seeds"""
    acc = {}
    for (i, s), (a, t) in rows.items():
        acc.setdefault(i, []).append(100 * float(a) - 0.5 * t / 1000)
    return {i: sum(v) / 3 for i, v in acc.items() if len(v) == 3}


def main():
    pred_only = "--predict" in sys.argv
    score = {"and1": 0, "and2a": 0, "and2b": 0, "and3": 0, "and4": 0}
    for (kind, A), (c1, c2) in CELLS.items():
        k = "sql" if kind.startswith("sql") else "tc"
        NA, D, X1, X2 = quick(k, A), default(k, A), quick(k, c1), quick(k, c2)
        keys = [key for key in D if all(key[0] in Z[key[1]] for Z in (NA, X1, X2))]
        D = {key: D[key] for key in keys}
        n = len(keys)
        PR = [key for key in keys if NA[key[1]][key[0]][0] and NA[key[1]][key[0]][1]]
        PW = [key for key in keys if NA[key[1]][key[0]][0] and not NA[key[1]][key[0]][1]]
        piR, piW = len(PR) / n, len(PW) / n
        al = 100 * sum(1 - D[q][0] for q in PR) / len(PR) + 0.5 * sum(D[q][1] for q in PR) / len(PR) / 1000
        be = 100 * sum(D[q][0] for q in PW) / len(PW) - 0.5 * sum(D[q][1] for q in PW) / len(PW) / 1000
        ag = lambda X, qs: sum(same(None, NA[q[1]][q[0]], X[q[1]][q[0]]) for q in qs) / len(qs)
        r1, e1, r2, e2 = ag(X1, PR), ag(X1, PW), ag(X2, PR), ag(X2, PW)
        k2 = sum(X2[q[1]][q[0]][2] for q in PR + PW) / len(PR + PW) / 1000
        d_pred = -piR * al * r1 * (1 - r2) + piW * be * e1 * (1 - e2) - 0.5 * (piR * r1 + piW * e1) * k2
        print(f"=== {kind} {A}: checks {c1} then {c2} ({n // 3} items x 3 seeds); pi_R {piR:.2f} pi_W {piW:.2f} alpha {al:.1f} beta {be:.1f}")
        print(f"  {c1}: r {100 * r1:.1f} e {100 * e1:.1f} | {c2}: r {100 * r2:.1f} e {100 * e2:.1f} | {c2} costs {1000 * k2:.0f} tokens")
        print(f"  predicted (independent agreement): two checks r {100 * r1 * r2:.1f} e {100 * e1 * e2:.1f}; two checks - {c1} alone {d_pred:+.2f}")
        if pred_only:
            continue
        P1, P2 = cascade(k, D, NA, X1), cascade2(D, NA, X1, X2)
        U = {"SB->T->T": util(D), "peer": util(P1), "two": util(P2)}
        ids = set.intersection(*(set(u) for u in U.values()))
        for name, rows in (("SB->T->T", D), (f"N->{c1}->SB->T->T", P1), (f"N->{c1}->{c2}->SB->T->T", P2)):
            rr = [v for key, v in rows.items() if key[0] in ids]
            a, t = 100 * sum(v[0] for v in rr) / len(rr), sum(v[1] for v in rr) / len(rr) / 1000
            print(f"  {name:>28}: {a:.1f}% @ {t:.2f}k, utility {a - 0.5 * t:.1f}")
        rj = sum(same(None, NA[q[1]][q[0]], X1[q[1]][q[0]]) and same(None, NA[q[1]][q[0]], X2[q[1]][q[0]]) for q in PR) / len(PR)
        ej = sum(same(None, NA[q[1]][q[0]], X1[q[1]][q[0]]) and same(None, NA[q[1]][q[0]], X2[q[1]][q[0]]) for q in PW) / len(PW)
        dp = ci({i: U["two"][i] - U["peer"][i] for i in ids})
        dd = ci({i: U["two"][i] - U["SB->T->T"][i] for i in ids})
        print(f"  measured two checks r {100 * rj:.1f} e {100 * ej:.1f}; two - {c1} alone {dp[0]:+.2f} [{dp[1]:+.2f}, {dp[2]:+.2f}]; "
              f"two - SB->T->T {dd[0]:+.2f} [{dd[1]:+.2f}, {dd[2]:+.2f}]")
        if kind == "sql dev":
            continue
        score["and1"] += ej <= 0.5 * min(e1, e2)
        score["and4"] += (d_pred > 0) == (dp[0] > 0)
        if kind == "sql train":
            score["and2a"] += dp[1] > 0
            score["and2b"] += dd[1] > 0
        else:
            score["and3"] += dp[1] > 0
    if not pred_only:
        print(f"*** SQL-AND1 {score['and1']} of 6 (needs 6); SQL-AND2 vs the single peer {score['and2a']} of 3 and vs SB->T->T "
              f"{score['and2b']} of 3 (each needs 2); SQL-AND3 {score['and3']} of 3 (needs 2); SQL-AND4 sign {score['and4']} of 6 (needs 5)")


if __name__ == "__main__":
    main()
