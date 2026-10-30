"""WP-RL (docs/prereg/PREREG_WPRL.md): the trained quick program in HO-PA's word-problem cascade. Per benchmark (OptiBench third, BWOR,
LogiOR, OptMATH; 476 problems x 3 seeds), Qwen3-8B's default SB->T->T and T->T (its stored formxtb2000 / formxt rows), the quick program
N = Qwen3-8B (formx) or the trained adapter (<tag>_<bench>_formx), the peer Qwen3.5-9B's formx; cascade N -> its free check -> the peer's
program prints the same value (run_nlopt tolerance) -> N, else the default (analyze_hopa.policies). Paired 95% intervals over problems
(seed means), pooled over the four benchmarks and per benchmark; utility = accuracy - 0.5 x ktokens, the peer's tokens counted.
WP-P1: quick right, trained - base; WP-P2: trained cascade - SB->T->T; WP-P3: trained cascade - base cascade (utility).
GREEDY (PREREG_SHARP.md): --peer TAG = the peer's formx rows of another tag (e.g. q35g, greedy) in place of q35's.
usage: python analyze_wprl.py [tag q8bwp1] [--peer TAG]"""
import contextlib, io, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
with contextlib.redirect_stdout(io.StringIO()):   # imported modules print their own tables
    from analyze_ho3 import ci
    from analyze_hopa import BENCH, per_q, policies, same_word, word_rows
    from analyze_ho import ok_
    from run_nlopt import RES, _rows

CAS = "N->q35->SB->T->T"


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "q8bwp1"
    peer = sys.argv[sys.argv.index("--peer") + 1] if "--peer" in sys.argv else None
    pool = {k: {} for k in ("kb", "kt", "cb", "ct", "d")}
    for b in BENCH:
        A, X = word_rows("q8b", b), word_rows("q35", b)
        if peer:
            P = {s: {r["id"]: (ok_(r), bool(r["correct"]), r.get("out_tokens") or 0, r.get("pred")) for r in _rows(f"{RES}/opt_{peer}_{b}_formx_s{s}.jsonl")}
                 for s in (1, 2, 3)}
            if not all(P.values()):
                print(f"=== {b}: no rows of peer {peer}"); continue
            X = {"formx": P}
        F = {s: {r["id"]: (ok_(r), bool(r["correct"]), r.get("out_tokens") or 0, r.get("pred")) for r in _rows(f"{RES}/opt_{tag}_{b}_formx_s{s}.jsonl")}
             for s in (1, 2, 3)}
        if not all(F.values()):
            print(f"=== {b}: no rows of {tag}"); continue
        At = dict(A, formx=F)
        Rb, Rt = policies(A, {"q35": X}, same_word), policies(At, {"q35": X}, same_word)
        ids = sorted({i for i, _ in Rb} & {i for i, _ in Rt})
        Rb = {k: v for k, v in Rb.items() if k[0] in ids}; Rt = {k: v for k, v in Rt.items() if k[0] in ids}
        q = {"kb": {i: (sum(A["formx"][s][i][1] for s in (1, 2, 3)) / 3, 0) for i in ids},
             "kt": {i: (sum(F[s][i][1] for s in (1, 2, 3)) / 3, 0) for i in ids},
             "cb": per_q(Rb, CAS), "ct": per_q(Rt, CAS), "d": per_q(Rb, "SB->T->T")}
        quick = lambda k: 100 * sum(q[k][i][0] for i in ids) / len(ids)
        tok = lambda R, k: sum(v[k][1] for v in R.values()) / len(R) / 1000
        acc = lambda R, k: 100 * sum(v[k][0] for v in R.values()) / len(R)
        print(f"=== {b}: {len(ids)} problems x 3 seeds; quick formx right: base {quick('kb'):.1f}%, trained {quick('kt'):.1f}%")
        print(f"  SB->T->T {acc(Rb, 'SB->T->T'):.1f}% @ {tok(Rb, 'SB->T->T'):.2f}k; cascade base N {acc(Rb, CAS):.1f}% @ {tok(Rb, CAS):.2f}k; "
              f"trained N {acc(Rt, CAS):.1f}% @ {tok(Rt, CAS):.2f}k")
        for name, a, c in (("trained cascade - SB->T->T", "ct", "d"), ("trained cascade - base cascade", "ct", "cb")):
            d = ci({i: q[a][i][1] - q[c][i][1] for i in ids})
            print(f"  {name}: utility {d[0]:+.2f} [{d[1]:+.2f}, {d[2]:+.2f}]")
        for k in pool:
            pool[k].update({f"{b}/{i}": q[k][i] for i in ids})
    ids = sorted(pool["d"])
    if not ids:
        return
    out = []
    for name, a, c, j in (("WP-P1 quick right, trained - base", "kt", "kb", 0), ("WP-P2 trained cascade - SB->T->T", "ct", "d", 1), ("WP-P3 trained cascade - base cascade", "ct", "cb", 1),
                          ("base cascade - SB->T->T", "cb", "d", 1)):
        d = ci({i: pool[a][i][j] - pool[c][i][j] for i in ids})
        print(f"pooled {len(ids)}: {name}: {'points' if j == 0 else 'utility'} {d[0]:+.2f} [{d[1]:+.2f}, {d[2]:+.2f}]")
        out.append(f"{name.split()[0]} {d[1] > 0} ({d[0]:+.2f} [{d[1]:+.2f}, {d[2]:+.2f}])")
    print("*** " + "; ".join(out))


if __name__ == "__main__":
    main()
