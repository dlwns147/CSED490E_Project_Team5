"""CV-1 addendum 4 (docs/prereg/PREREG_CV.md), CV-P8 / P9: plain RL's quick query (C1, tag q8bcvc1) with the peer check. Policies on
BIRD dev (Qwen3-8B, 3 seeds): SB->T->T (the no-label default); N -> Qwen3.5-9B's quick query returns the same rows -> N, else SB->T->T,
with the base quick query (SQL-PA / SQL-DV's peer cascade) and with C1's; reported: C1 deployed as in CV-1 (N -> check -> T->T), C1's
peer cascade with the peer at the next seed (s mod 3 + 1) and with T->T as the fallback. Paired 95% intervals over questions (seed
means), utility = accuracy - 0.5 x ktokens, the peer's tokens counted. Theory (SQL-AND's discordant decomposition): against the default,
accepting changes accuracy only on (N right, default wrong) = RW and (N wrong, default right) = WR, so
  acc(N -> peer) - acc(D) = pi_RW a_RW - pi_WR a_WR,   tokens = E k_N + P(pass) E k_peer - sum_s pi_s a_s E[c_D | s]
(a_s = the peer's agreement rate in stratum s); --predict transfers a_s from the base quick query to C1's strata, written before any
agreement between C1 and the peer is computed.
--c1think (addendum 5, CV-P12 / P13): the default with C1's adapter on its SB / T steps (tag q8bc1t) as the comparator and fallback.
usage: python analyze_cvpeer.py [--predict] [--c1think]"""
import contextlib, io, json, sys

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
with contextlib.redirect_stdout(io.StringIO()):   # analyze_dv's imports print word-problem tables
    from analyze_dv import cascade, per_q, quick, same
from analyze_cv import RES, base  # noqa: E402
from run_nlopt import _rows  # noqa: E402
from analyze_ho3 import ci  # noqa: E402


def strata(NA, D, keys):
    """{stratum: [(id, seed), ...]} with strata RR / RW / WR / WW (N right? default right?) over passing N, and fail"""
    out = {k: [] for k in ("RR", "RW", "WR", "WW", "fail")}
    for i, s in keys:
        n = NA[s][i]
        out["fail" if not n[0] else ("R" if n[1] else "W") + ("R" if D[(i, s)][0] else "W")].append((i, s))
    return out


def theory(NA, D, keys, a, kpeer):
    """predicted (accuracy points, ktokens) of N -> peer -> D minus D, with agreement rates a per stratum"""
    S = strata(NA, D, keys)
    n = len(keys)
    acc = 100 * (len(S["RW"]) * a["RW"] - len(S["WR"]) * a["WR"]) / n
    kn = sum(NA[s][i][2] for i, s in keys) / n
    kp = sum(kpeer[q] for st in ("RR", "RW", "WR", "WW") for q in S[st]) / n
    saved = sum(a[st] * sum(D[q][1] for q in S[st]) for st in ("RR", "RW", "WR", "WW")) / n
    return acc, (kn + kp - saved) / 1000, {st: len(v) / n for st, v in S.items()}


def composed(tag):
    """{(id, seed): {"T->T": (right, tokens), "SB->T->T": (right, tokens)}} from a tag's graded T / SB rows (analyze_cv.base's
    composition: T at seed s, its retry T at s mod 3 + 1; SB, then T->T where SB's query fails the check)"""
    G, T, SB = {}, {}, {}
    for s in (1, 2, 3):
        G[s] = json.load(open(f"{RES}/grades_{tag}_s{s}.json")); G[s].pop("_gold_fail", None)
        T[s], SB[s] = ({r["id"]: r for r in _rows(f"{RES}/{tag}_{a}_s{s}.jsonl")} for a in ("think", "sb"))
    out = {}
    for s in (1, 2, 3):
        s2 = s % 3 + 1
        for i, g in G[s].items():
            g2 = G[s2].get(i, {})
            if not {"T", "SB"} <= set(g) or "T" not in g2 or i not in T[s] or i not in SB[s] or i not in T[s2]:
                continue
            tt, st, t2t = T[s][i]["out_tokens"], SB[s][i]["out_tokens"], T[s2][i]["out_tokens"]
            tto = (g2["T"]["ok"], tt + t2t) if g["T"]["chk"] != "pass" else (g["T"]["ok"], tt)
            out[(i, s)] = {"T->T": tto, "SB->T->T": (g["SB"]["ok"], st) if g["SB"]["chk"] == "pass" else (tto[0], st + tto[1])}
    return out


def c1think():
    """CV-P12 / P13"""
    B, BC = base(), composed("q8bc1t")
    N0, N1, X = quick("sql", "q8b"), quick("sql", "q8bcvc1"), quick("sql", "q35")
    keys = [k for k in B if k in BC and all(k[0] in Z[k[1]] for Z in (N0, N1, X))]
    ids = {i for i, _ in keys}
    ids = {i for i in ids if all((i, s) in B and (i, s) in BC and all(i in Z[s] for Z in (N0, N1, X)) for s in (1, 2, 3))}
    keys = [k for k in keys if k[0] in ids]
    D0 = {k: B[k]["SB->T->T"] for k in keys}
    DC = {k: BC[k]["SB->T->T"] for k in keys}
    kpeer = {(i, s): X[s][i][2] for i, s in keys}
    S0 = strata(N0, D0, keys)
    a0 = {st: sum(same(None, N0[s][i], X[s][i]) for i, s in v) / len(v) for st, v in S0.items() if st != "fail"}
    print(f"=== CV-P12 / P13, Qwen3-8B, BIRD dev: {len(ids)} questions x 3 seeds; the default with C1's adapter (q8bc1t)")
    acc, kt, pi = theory(N1, DC, keys, a0, kpeer)
    print(f"  predicted (C1 quick query vs SB->T->T(C1), base agreement rates): accuracy {acc:+.2f}, ktokens {kt:+.3f}, utility "
          f"{acc - 0.5 * kt:+.2f} | strata " + ", ".join(f"{st} {100 * p:.1f}%" for st, p in pi.items()))
    pol = {"SB->T->T(base)": D0, "SB->T->T(C1)": DC, "T->T(C1)": {k: BC[k]["T->T"] for k in keys},
           "C1->peer->SB->T->T(C1)": cascade("sql", DC, N1, X), "C1->peer->SB->T->T(base)": cascade("sql", D0, N1, X)}
    Q = {k: per_q(v) for k, v in pol.items()}
    for k, r in pol.items():
        a, t = 100 * sum(v[0] for v in r.values()) / len(r), sum(v[1] for v in r.values()) / len(r) / 1000
        line = f"  {k:>26}: {a:.1f}% @ {t:.2f}k, utility {a - 0.5 * t:.1f}"
        for y in ("SB->T->T(base)", "SB->T->T(C1)"):
            if y != k:
                da, du = ci({i: Q[k][i][0] - Q[y][i][0] for i in ids}), ci({i: Q[k][i][1] - Q[y][i][1] for i in ids})
                line += f" | vs {y}: acc {da[0]:+.1f} [{da[1]:+.1f}, {da[2]:+.1f}], utility {du[0]:+.1f} [{du[1]:+.1f}, {du[2]:+.1f}]"
        print(line)
    u12 = ci({i: Q["C1->peer->SB->T->T(C1)"][i][1] - Q["SB->T->T(C1)"][i][1] for i in ids})
    u13 = ci({i: Q["C1->peer->SB->T->T(base)"][i][1] - Q["SB->T->T(C1)"][i][1] for i in ids})
    print(f"*** CV-P12 {u12[1] > 0} ({u12[0]:+.2f} [{u12[1]:+.2f}, {u12[2]:+.2f}]); CV-P13 {u13[1] > -0.5} ({u13[0]:+.2f} [{u13[1]:+.2f}, "
          f"{u13[2]:+.2f}])")


def main():
    if "--c1think" in sys.argv:
        return c1think()
    B = base()
    D = {k: v["SB->T->T"] for k, v in B.items()}
    TT = {k: v["T->T"] for k, v in B.items()}
    N0, N1, X = quick("sql", "q8b"), quick("sql", "q8bcvc1"), quick("sql", "q35")
    Xn = {s: X[s % 3 + 1] for s in (1, 2, 3)}
    keys = [k for k in D if all(k[0] in Z[k[1]] for Z in (N0, N1, X, Xn))]
    ids3 = {i for i, _ in keys}
    ids3 = {i for i in ids3 if all((i, s) in D for s in (1, 2, 3)) and all(i in Z[s] for Z in (N0, N1, X, Xn) for s in (1, 2, 3))}
    keys = [k for k in keys if k[0] in ids3]
    D = {k: D[k] for k in keys}
    kpeer = {(i, s): X[s][i][2] for i, s in keys}
    S0 = strata(N0, D, keys)
    a0 = {st: sum(same(None, N0[s][i], X[s][i]) for i, s in v) / len(v) for st, v in S0.items() if st != "fail"}
    print(f"=== CV-P8 / P9, Qwen3-8B, BIRD dev: {len(ids3)} questions x 3 seeds; peer Qwen3.5-9B (q35)")
    print("  base quick query: strata " + ", ".join(f"{st} {100 * len(v) / len(keys):.1f}%" for st, v in S0.items())
          + " | peer agrees " + ", ".join(f"{st} {100 * r:.1f}%" for st, r in a0.items()))
    for name, NA in (("base", N0), ("C1", N1)):
        acc, kt, pi = theory(NA, D, keys, a0, kpeer)
        print(f"  predicted ({name} quick query, base agreement rates): peer cascade - SB->T->T accuracy {acc:+.2f}, ktokens {kt:+.3f}, "
              f"utility {acc - 0.5 * kt:+.2f} | strata " + ", ".join(f"{st} {100 * p:.1f}%" for st, p in pi.items()))
    if "--predict" in sys.argv:
        return
    P0, P1, P1n, P1t = cascade("sql", D, N0, X), cascade("sql", D, N1, X), cascade("sql", D, N1, Xn), cascade("sql", TT, N1, X)
    C1 = {(i, s): (N1[s][i][1], N1[s][i][2]) if N1[s][i][0] else (TT[(i, s)][0], N1[s][i][2] + TT[(i, s)][1]) for i, s in keys}
    pol = {"SB->T->T": D, "N(base)->peer->SB->T->T": P0, "N(C1)->peer->SB->T->T": P1, "N(C1)->peer next seed->SB->T->T": P1n,
           "N(C1)->peer->T->T": P1t, "C1 as CV-1 (N->T->T)": C1}
    Q = {k: per_q(v) for k, v in pol.items()}
    for k, r in pol.items():
        a, t = 100 * sum(v[0] for v in r.values()) / len(r), sum(v[1] for v in r.values()) / len(r) / 1000
        line = f"  {k:>34}: {a:.1f}% @ {t:.2f}k, utility {a - 0.5 * t:.1f}"
        if k != "SB->T->T":
            for y in ("SB->T->T", "N(base)->peer->SB->T->T"):
                if y != k:
                    da, du = ci({i: Q[k][i][0] - Q[y][i][0] for i in ids3}), ci({i: Q[k][i][1] - Q[y][i][1] for i in ids3})
                    line += f" | vs {y}: acc {da[0]:+.1f} [{da[1]:+.1f}, {da[2]:+.1f}], utility {du[0]:+.1f} [{du[1]:+.1f}, {du[2]:+.1f}]"
        print(line)
    S1 = strata(N1, D, keys)
    a1 = {st: sum(same(None, N1[s][i], X[s][i]) for i, s in v) / len(v) for st, v in S1.items() if st != "fail"}
    print("  C1 quick query: measured peer agreement " + ", ".join(f"{st} {100 * r:.1f}%" for st, r in a1.items()))
    acc, kt, _ = theory(N1, D, keys, a1, kpeer)
    print(f"  identity check (C1, measured rates): accuracy {acc:+.2f}, ktokens {kt:+.3f}")
    u8 = ci({i: Q["N(C1)->peer->SB->T->T"][i][1] - Q["SB->T->T"][i][1] for i in ids3})
    u9 = ci({i: Q["N(C1)->peer->SB->T->T"][i][1] - Q["N(base)->peer->SB->T->T"][i][1] for i in ids3})
    pa, pk, _ = theory(N1, D, keys, a0, kpeer)
    print(f"*** CV-P8 {u8[1] > 0}; CV-P9 {u9[1] > 0}; CV-P8 theory (predicted {pa - 0.5 * pk:+.2f} inside [{u8[1]:+.2f}, {u8[2]:+.2f}]) "
          f"{u8[1] <= pa - 0.5 * pk <= u8[2]}")


if __name__ == "__main__":
    main()
