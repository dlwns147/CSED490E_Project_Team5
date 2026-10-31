"""XPEER (docs/prereg/PREREG_XPEER.md; offline on stored rows): which peer makes the word-problem cascade pay, and does the break-even
account predict it? Cascade = HO-PA's: N's quick program (formx) -> its free check -> the peer's quick program prints the same value
(analyze_sharp.safe_same) -> N's; else N's default SB->T->T. Per (N, peer): cascade - SB->T->T in utility (accuracy - 0.5 x ktokens),
paired 95% interval over problems (seed means), pooled over OptiBench's third / BWOR / LogiOR / OptMATH, and its exact decomposition
(analyze_breakeven.acct: break-even r*, the peer's TPR / FPR on N's passing programs, accepted gain, the peer's and N's tokens).
Prediction from N's own rows only (no peer outcome): N's passing programs split into 4 strata by (N right, default right); accept gain
= sum over strata of share x mean gain of accepting x the peer's agreement rate in that stratum measured on the calibration N
(Qwen3-8B), minus the peer's tokens (its mean per call on the calibration N x N's pass rate) and N's.
--fresh <tag>: N's think arms from results/x3/opt_<tag>_optibench_{formxt,formxtb2000}_s*.jsonl (OptiBench problems outside the third),
N's and the peer's quick programs from their stored 605-problem formx rows.
--mamo: MAMO (EasyLP + ComplexLP, 863 problems), N = Qwen3-8B / Qwen3-14B-AWQ, peers gpt-oss-20b and the other Qwen3 model.
usage: python analyze_xpeer.py [--explore | --models | --fresh <N>:<tag>[,<N>:<tag>] | --mamo]"""
import contextlib, io, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
with contextlib.redirect_stdout(io.StringIO()):
    import analyze_hopa as H
    from analyze_breakeven import acct
    from analyze_ho3 import ci
    from analyze_sharp import safe_same
from run_nlopt import _rows  # noqa: E402

CAS, DEF = "N->p->SB->T->T", "SB->T->T"
PEERS = ("q35", "q8b", "q14a", "q32b", "n3n", "seed36", "oss20", "oss120")


def formx(m, b, arm="formx"):
    return {s: {r["id"]: (H.ok_(r), bool(r["correct"]), r.get("out_tokens") or 0, r.get("pred"))
                for r in _rows(f"{H.XRES}/opt_{m}_{b}_{arm}_s{s}.jsonl")} for s in (1, 2, 3)}


def rows(N, peer, benches=H.BENCH, fresh=None):
    """per problem-seed decomposition items, per problem (cascade, default) utilities, keyed 'bench/id'"""
    items, q = [], {}
    for b in benches:
        A = H.word_rows(N, b) if not fresh else {"formx": formx(N, b), "formxt": formx(fresh, b, "formxt"),
                                                  "formxtb2000": formx(fresh, b, "formxtb2000")}
        P = {"formx": formx(peer, b)}
        R = H.policies(A, {"p": P}, safe_same)
        for (i, s), r in R.items():
            f, p = A["formx"][s][i], P["formx"][s][i]
            items.append((f[0], f[1], f[2], f[0] and safe_same(f, p), p[2], r[DEF][0], r[DEF][1]))
        c, d = H.per_q(R, CAS), H.per_q(R, DEF)
        q.update({f"{b}/{i}": (c[i][1], d[i][1], c[i][0], d[i][0]) for i in c})
    return items, q


def report(name, items, q):
    g = ci({i: v[0] - v[1] for i, v in q.items()})
    a = ci({i: v[2] - v[3] for i, v in q.items()})
    acct(name, items)
    print(f"{'':>16}  cascade - SB->T->T: utility {g[0]:+.2f} [{g[1]:+.2f}, {g[2]:+.2f}], accuracy {a[0]:+.2f} [{a[1]:+.2f}, {a[2]:+.2f}]"
          f" ({len(q)} problems)")
    return g


def parts(items):
    """N's passing programs split by (N right, the default right): share of problem-seeds, mean utility of accepting N instead of the
    default (100 x right difference + 0.5 x the default's ktokens), and the peer's agreement rate in each stratum (its false accepts
    concentrate where the default fails too, so a uniform TPR / FPR misses the accepted gain; stratifying by the default's outcome
    removes most of that)"""
    n = len(items)
    d = lambda x: 100 * (float(x[1]) - float(x[5])) + H.LAM * x[6] / 1000
    st = {}
    for x in items:
        if x[0]:
            st.setdefault((bool(x[1]), bool(x[5])), []).append(x)
    return {"st": {k: (len(v) / n, sum(map(d, v)) / len(v), sum(x[3] for x in v) / len(v)) for k, v in st.items()},
            "pass": sum(map(len, st.values())) / n, "Ncost": H.LAM * sum(x[2] for x in items) / 1000 / n,
            "peer_tok": sum(x[4] for x in items if x[0]) / max(1, sum(map(len, st.values())))}


def predict(items_n, cal):
    """the cascade's gain for N from N's rows (strata shares and gains, its tokens) and the peer's agreement rate per stratum and tokens
    per call on the calibration N"""
    p = parts(items_n)
    return (sum(share * gain * cal["st"].get(k, (0, 0, 0))[2] for k, (share, gain, _) in p["st"].items())
            - H.LAM * cal["peer_tok"] / 1000 * p["pass"] - p["Ncost"])


def main():
    H.SAME_FN = H.same_word
    if "--explore" in sys.argv:   # the cells that chose the hypothesis (post hoc): Qwen3-8B and Qwen3.5-9B as N, every stored peer
        for N in ("q8b", "q35"):
            for peer in PEERS:
                if peer != N:
                    report(f"{N}<-{peer}", *rows(N, peer))
    if "--models" in sys.argv:    # XP-P1 / XP-P2: new N with gpt-oss-20b as the peer, predicted from Qwen3-8B's calibration
        cal = parts(rows("q8b", "oss20")[0])
        print("calibration (Qwen3-8B <- gpt-oss-20b): agreement by (N right, default right) " + ", ".join(
            f"{k}: {100 * v[2]:.1f}% (share {100 * v[0]:.1f}%, gain {v[1]:+.1f})" for k, v in sorted(cal["st"].items()))
            + f"; peer tokens per call {cal['peer_tok']:.0f}")
        for N in ("q14a", "n3n"):
            items, q = rows(N, "oss20")
            pr = predict(items, cal)
            g = report(f"{N}<-oss20", items, q)
            print(f"{'':>16}  predicted {pr:+.2f}; realised - predicted {g[0] - pr:+.2f}")
    if "--fresh" in sys.argv:     # XP-P3 / XP-P4: OptiBench problems outside the third
        cal = parts(rows("q8b", "oss20", ("optibench",))[0])
        for spec in sys.argv[sys.argv.index("--fresh") + 1].split(","):
            N, tag = spec.split(":")
            for peer in ("oss20", H.PEER[N]):
                items, q = rows(N, peer, ("optibench",), fresh=tag)
                g = report(f"fresh {N}<-{peer}", items, q)
                if peer == "oss20":
                    print(f"{'':>16}  predicted from the third's agreement by stratum {predict(items, cal):+.2f}")
    if "--mamo" in sys.argv:      # addendum MAMO (XP-P6 / XP-P7): MAMO EasyLP + ComplexLP, N's think arms run for XPEER
        for N, qwen in (("q8b", "q14a"), ("q14a", "q8b")):
            for peer in ("oss20", qwen):
                items, q = rows(N, peer, ("mamo",))
                report(f"mamo {N}<-{peer}", items, q)
                for sub in ("mamo_easy", "mamo_complex"):
                    qs = {i: v for i, v in q.items() if i.split("/", 1)[1].startswith(sub + "-")}
                    g = ci({i: v[0] - v[1] for i, v in qs.items()})
                    print(f"{'':>16}  {sub}: cascade - SB->T->T {g[0]:+.2f} [{g[1]:+.2f}, {g[2]:+.2f}] ({len(qs)} problems)")


if __name__ == "__main__":
    main()
