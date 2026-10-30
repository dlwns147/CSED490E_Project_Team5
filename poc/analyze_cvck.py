"""CV-1 addendum 4 (docs/prereg/PREREG_CV.md), CV-P10 / P11: C2's gate at its saved checkpoints (adapter_r10 ... r90, tags
q8bcvc2r<k>; r94 = q8bcvc2, the final adapter) on BIRD dev. C2's turn 1 is SQL-1's base query, so correctness comes from q8b's grades;
the policy is CV-1's: failed check -> T->T; passing -> ACCEPT if P(ACCEPT) >= tau (0.5), else T->T (turn 2 = 1 token). Per checkpoint:
the accept rate on passing queries, by stratum against T->T (RW = query right, T->T wrong; WR = query wrong, T->T right), the ratio
a_RW / a_WR against the break-even pi_WR / pi_RW (accuracy rises over T->T iff pi_RW a_RW > pi_WR a_WR; the token term is ~0.5 point
per 1k), and utility minus T->T and minus the peer gate (paired 95% intervals over questions, seed means).
usage: python analyze_cvck.py"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_cv import RES, base, per_q, summary  # noqa: E402
from analyze_ho3 import ci  # noqa: E402
from run_nlopt import _rows  # noqa: E402

TAGS = [(f"r{k}", f"q8bcvc2r{k}") for k in range(10, 100, 10)] + [("r94", "q8bcvc2")]


def gate_rows(tag, B, G, tau=0.5):
    """{(id, seed): (right, tokens, decision)} or None if a seed's rows are missing"""
    out = {}
    for s in (1, 2, 3):
        p = f"{RES}/{tag}_cheap_s{s}.jsonl"
        if not os.path.exists(p):
            return None
        for r in _rows(p):
            k = (r["id"], s)
            if k not in B or "N" not in G[s].get(r["id"], {}):
                continue
            ok, (tt_ok, tt_tok) = G[s][r["id"]]["N"]["ok"], B[k]["T->T"]
            if r["c_n"] != "pass":
                out[k] = (tt_ok, r["n_tok"] + tt_tok, "fail")
            elif r.get("g_acc") is not None and r["g_acc"] >= tau:
                out[k] = (ok, r["n_tok"] + 1, "accept")
            else:
                out[k] = (tt_ok, r["n_tok"] + 1 + tt_tok, "defer")
    return out


def main():
    B = base()
    G = {}
    for s in (1, 2, 3):
        G[s] = json.load(open(f"{RES}/grades_q8b_s{s}.json")); G[s].pop("_gold_fail", None)
    from analyze_sqlpa import cascade, grades, ntok
    peer = cascade(B, grades("q8b"), ntok("q8b"), grades("q35"), ntok("q35"))
    R = {name: gate_rows(tag, B, G) for name, tag in TAGS}
    R = {k: v for k, v in R.items() if v}
    keys = set(B) & set(peer)
    for v in R.values():
        keys &= set(v)
    ids = {i for i, _ in keys}
    ids = {i for i in ids if all((i, s) in keys for s in (1, 2, 3))}
    keys = {k for k in keys if k[0] in ids}
    TT = {k: B[k]["T->T"] for k in keys}
    Q = {"T->T": per_q(TT), "peer": per_q({k: peer[k] for k in keys})}
    st = {}
    for k in keys:
        n = G[k[1]][k[0]]["N"]
        if n["chk"] == "pass":
            st[k] = ("R" if n["ok"] else "W") + ("R" if TT[k][0] else "W")
    n = len(keys)
    pi = {s: sum(v == s for v in st.values()) / n for s in ("RR", "RW", "WR", "WW")}
    print(f"=== CV-P10 / P11: C2's gate by checkpoint, Qwen3-8B, BIRD dev: {len(ids)} questions x 3 seeds")
    print("  strata (base query vs T->T, SQL-1's check): " + ", ".join(f"{s} {100 * p:.1f}%" for s, p in pi.items())
          + f"; break-even ratio pi_WR / pi_RW = {pi['WR'] / pi['RW']:.2f}")
    a, t = summary(TT)
    print(f"  T->T: {a:.1f}% @ {t:.2f}k, utility {a - 0.5 * t:.1f}")
    a, t = summary({k: peer[k] for k in keys})
    print(f"  peer gate: {a:.1f}% @ {t:.2f}k, utility {a - 0.5 * t:.1f}")
    p10, p11, n11 = 0, 0, 0
    for name, rows in R.items():
        rr = {k: rows[k] for k in keys}
        Q[name] = per_q(rr)
        a, t = summary(rr)
        acc = {s: [rr[k][2] == "accept" for k, v in st.items() if v == s] for s in pi}
        ar = {s: sum(v) / max(1, len(v)) for s, v in acc.items()}
        share = sum(rr[k][2] == "accept" for k in st) / len(st)
        ratio = ar["RW"] / ar["WR"] if ar["WR"] else float("inf") if ar["RW"] else float("nan")
        du = ci({i: Q[name][i][1] - Q["T->T"][i][1] for i in ids})
        dp = ci({i: Q[name][i][1] - Q["peer"][i][1] for i in ids})
        p10 += du[1] > 0
        if share >= 0.01:
            n11 += 1; p11 += ratio < pi["WR"] / pi["RW"]
        print(f"  {name:>4}: {a:.1f}% @ {t:.2f}k, utility {a - 0.5 * t:.1f} | accepts {100 * share:.1f}% of passing queries; "
              + ", ".join(f"{s} {100 * r:.1f}%" for s, r in ar.items()) + f"; a_RW / a_WR {ratio:.2f} | utility - T->T {du[0]:+.2f} "
              f"[{du[1]:+.2f}, {du[2]:+.2f}] | - peer gate {dp[0]:+.2f} [{dp[1]:+.2f}, {dp[2]:+.2f}]")
        print(f"        frontier: " + "; ".join("tau %.1f %.1f%% @ %.2fk" % ((tau,) + summary({k: v for k, v in gate_rows(
            dict(TAGS)[name], B, G, tau).items() if k in keys})) for tau in (0.1, 0.3, 0.7, 0.9)))
    print(f"*** CV-P10 (no checkpoint beats T->T: utility lower bound > 0 in none of {len(R)}): {p10 == 0} ({p10} beat it); "
          f"CV-P11 (a_RW / a_WR below the break-even wherever the gate accepts >= 1%): {p11 == n11} ({p11} of {n11})")


if __name__ == "__main__":
    main()
