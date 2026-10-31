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
Addendum B (gate): the peer's program also checks SB's passing program (PND = N -> peer agrees -> N; else SB passes and the peer agrees
-> SB; else T->T); printed by --fresh / --mamo ("B" lines), exploratory on stored rows with --gate.
usage: python analyze_xpeer.py [--explore | --models | --gate | --fresh <N>:<tag>[,<N>:<tag>] | --mamo]"""
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


def gate(N, peer, benches=H.BENCH, fresh=None):
    """addendum B: the peer's quick program as the check of every program the default would accept. Per (problem, seed) (right,
    tokens) of D = SB->T->T, T->T, PEER = N -> the peer agrees -> N, else D; PD = D with SB's passing program accepted only if the
    peer prints the same value, else T->T; PND = PEER, then PD (the peer's program, paid once, also gates SB). And SB's passing programs
    by (SB right, T->T right): (the peer agrees, gain of rejecting = 100 x (T->T right - SB right) - LAM x T->T's ktokens, peer tokens)"""
    R, st = {}, {}
    for b in benches:
        A = H.word_rows(N, b) if not fresh else {"formx": formx(N, b), "formxt": formx(fresh, b, "formxt"),
                                                  "formxtb2000": formx(fresh, b, "formxtb2000")}
        P = formx(peer, b)
        F, T, SB = A["formx"], A["formxt"], A["formxtb2000"]
        ids = set.intersection(*(set(Z[s]) for Z in (F, T, SB, P) for s in (1, 2, 3)))
        for s in (1, 2, 3):
            s2 = s % 3 + 1
            for i in ids:
                f, sb, t, t2, p = F[s][i], SB[s][i], T[s][i], T[s2][i], P[s][i]
                tt = (t[1], t[2]) if t[0] else (t2[1], t[2] + t2[2])
                d = (sb[1], sb[2]) if sb[0] else (tt[0], sb[2] + tt[1])
                acc_n, acc_sb = f[0] and safe_same(f, p), sb[0] and safe_same(sb, p)
                pd = d if not sb[0] else (sb[1], sb[2] + p[2]) if acc_sb else (tt[0], sb[2] + p[2] + tt[1])
                R[(f"{b}/{i}", s)] = {"D": d, "T->T": tt, "PEER": (f[1], f[2] + p[2]) if acc_n else (d[0], f[2] + (p[2] if f[0] else 0) + d[1]),
                                      "PD": pd, "PND": (f[1], f[2] + p[2]) if acc_n else (pd[0], f[2] + (p[2] if f[0] and not sb[0] else 0) + pd[1])}
                if sb[0]:
                    st.setdefault((bool(sb[1]), bool(tt[0])), []).append((acc_sb, 100 * (float(tt[0]) - float(sb[1])) - H.LAM * tt[1] / 1000, p[2]))
    return R, st


def gate_parts(R, st):
    n = len(R)
    return {"st": {k: (len(v) / n, sum(g for _, g, _ in v) / len(v), sum(a for a, _, _ in v) / len(v)) for k, v in st.items()},
            "pass": sum(map(len, st.values())) / n, "peer_tok": sum(x[2] for v in st.values() for x in v) / max(1, sum(map(len, st.values())))}


def gate_report(name, R, st, cal=None):
    """accuracy @ tokens per policy; PD - D, PND - D, PND - PEER; SB's strata; PD - D predicted from the calibration cell's agreement
    by stratum (N's own strata shares and gains)"""
    Q = {k: H.per_q(R, k) for k in ("D", "T->T", "PEER", "PD", "PND")}
    tok = lambda k: sum(t for v in R.values() for t in [v[k][1]]) / len(R) / 1000
    print(f"{name:>16}  " + ", ".join(f"{k} {100 * sum(a for a, _ in Q[k].values()) / len(Q[k]):.1f}% @ {tok(k):.2f}k" for k in Q)
          + f" ({len(Q['D'])} problems)")
    for a, b in (("PD", "D"), ("PND", "D"), ("PND", "PEER"), ("PND", "T->T")):
        g = ci({i: Q[a][i][1] - Q[b][i][1] for i in Q["D"]})
        print(f"{'':>16}  {a} - {b}: utility {g[0]:+.2f} [{g[1]:+.2f}, {g[2]:+.2f}]")
    p = gate_parts(R, st)
    print(f"{'':>16}  SB's passing programs by (SB right, T->T right): " + "; ".join(
        f"{k}: {len(st[k])} ({100 * v[0]:.1f}%), the peer agrees {100 * v[2]:.1f}%, gain of rejecting {v[1]:+.1f}" for k, v in sorted(p["st"].items()))
        + f"; peer tokens per call {p['peer_tok']:.0f}")
    if cal:
        pr = sum(sh * g * (1 - cal["st"].get(k, (0, 0, 0))[2]) for k, (sh, g, _) in p["st"].items()) - H.LAM * cal["peer_tok"] / 1000 * p["pass"]
        print(f"{'':>16}  PD - D predicted from the calibration cell's agreement by stratum {pr:+.2f}")


def sql_peer(A, P, dev):
    """addendum C (SQL): per (set/question, seed) (right, tokens) of D = SB->T->T and N -> P's quick query returns the same rows -> N,
    else D (P's tokens counted when N passes); A's passing quick queries by (N right, D right): (P agrees, gain of accepting)"""
    import analyze_sqlpa as S
    from analyze_cv import base
    sfx = "" if dev else "pa"
    GA, GP, KA, KP = S.grades(A + sfx), S.grades(P + sfx), S.ntok(A + sfx), S.ntok(P + sfx)
    R, st = {"D": {}, "PEER": {}}, {}
    for (i, s), v in base(A + sfx).items():
        n, d, k = GA[s][i]["N"], v["SB->T->T"], (f"{'dev' if dev else 'fresh'}/{i}", s)
        o, kp = GP[s].get(i, {}).get("N", {}), KP[s].get(i, 0)
        ag = n["chk"] == "pass" and o.get("chk") == "pass" and o.get("h") == n["h"]
        R["D"][k] = d
        R["PEER"][k] = (n["ok"], KA[s][i] + kp) if ag else (d[0], KA[s][i] + (kp if n["chk"] == "pass" else 0) + d[1])
        if n["chk"] == "pass":
            st.setdefault((bool(n["ok"]), bool(d[0])), []).append((ag, 100 * (float(n["ok"]) - float(d[0])) + H.LAM * d[1] / 1000, kp))
    return R, st


def sql_report(peer="oss20"):
    """addendum C: the peer on SQL (BIRD dev 1,530 + fresh BIRD-train 1,338 questions, pooled and per set)"""
    from analyze_cv import per_q as sq
    for A, qwen in (("q8b", "q35"), ("q14a", "q35"), ("q35", "q8b")):
        res = {}
        for P in (peer, qwen):
            R, st = {"D": {}, "PEER": {}}, {}
            for dev in (True, False):
                r, s_ = sql_peer(A, P, dev)
                for k in R:
                    R[k].update(r[k])
                for k, v in s_.items():
                    st.setdefault(k, []).extend(v)
            res[P] = ({k: sq(v) for k, v in R.items()}, R, st)
        Qd = res[peer][0]["D"]
        for part in ("pooled", "dev", "fresh"):
            ids = [i for i in Qd if part == "pooled" or i.startswith(part + "/")]
            line = f"SQL {A} {part} ({len(ids)} questions): D {100 * sum(Qd[i][0] for i in ids) / len(ids):.1f}%"
            for P in (peer, qwen):
                Q = res[P][0]["PEER"]
                g = ci({i: Q[i][1] - Qd[i][1] for i in ids})
                line += f"; N->{P}->D {100 * sum(Q[i][0] for i in ids) / len(ids):.1f}%, - D {g[0]:+.2f} [{g[1]:+.2f}, {g[2]:+.2f}]"
            a, b = res[peer][0]["PEER"], res[qwen][0]["PEER"]
            g = ci({i: a[i][1] - b[i][1] for i in ids})
            print(line + f"; {peer} - {qwen} {g[0]:+.2f} [{g[1]:+.2f}, {g[2]:+.2f}]")
        n = len(res[peer][1]["D"])
        for P in (peer, qwen):
            st = res[P][2]
            print(f"{'':>8}{A}<-{P} N's passing queries by (N right, D right): " + "; ".join(
                f"{k}: {100 * len(v) / n:.1f}%, gain {sum(x[1] for x in v) / len(v):+.1f}, agrees {100 * sum(x[0] for x in v) / len(v):.1f}%"
                for k, v in sorted(st.items())) + f"; peer tokens per call {sum(x[2] for v in st.values() for x in v) / max(1, sum(map(len, st.values()))):.0f}")


def main():
    H.SAME_FN = H.same_word
    if "--sql" in sys.argv:       # addendum C (XC-P1..P4): gpt-oss-20b as the peer on SQL; `--sql <stand-in peer>` for a smoke
        a = sys.argv[sys.argv.index("--sql") + 1:]
        sql_report(a[0] if a and not a[0].startswith("--") else "oss20")
    if "--gate" in sys.argv:      # addendum B, exploratory (stored rows of the four held-out sets): the peer gates SB's program too
        for N in ("q8b", "q35", "q14a", "n3n"):
            for peer in ("oss20", H.PEER[N], "oss120"):
                gate_report(f"{N}<-{peer}", *gate(N, peer))
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
        for spec in sys.argv[sys.argv.index("--fresh") + 1].split(","):   # addendum B (XP-P8 / XP-P10)
            N, tag = spec.split(":")
            gcal = gate_parts(*gate(N, "oss20"))
            for peer in ("oss20", H.PEER[N]):
                gate_report(f"B fresh {N}<-{peer}", *gate(N, peer, ("optibench",), fresh=tag), gcal if peer == "oss20" else None)
    if "--mamo" in sys.argv:      # addendum MAMO (XP-P6 / XP-P7): MAMO EasyLP + ComplexLP, N's think arms run for XPEER
        for N, qwen in (("q8b", "q14a"), ("q14a", "q8b")):
            for peer in ("oss20", qwen):
                items, q = rows(N, peer, ("mamo",))
                report(f"mamo {N}<-{peer}", items, q)
                for sub in ("mamo_easy", "mamo_complex"):
                    qs = {i: v for i, v in q.items() if i.split("/", 1)[1].startswith(sub + "-")}
                    g = ci({i: v[0] - v[1] for i, v in qs.items()})
                    print(f"{'':>16}  {sub}: cascade - SB->T->T {g[0]:+.2f} [{g[1]:+.2f}, {g[2]:+.2f}] ({len(qs)} problems)")
        for N, qwen in (("q8b", "q14a"), ("q14a", "q8b")):   # addendum B (XP-P9 / XP-P11)
            gcal = gate_parts(*gate(N, "oss20"))
            for peer in ("oss20", qwen):
                R, st = gate(N, peer, ("mamo",))
                gate_report(f"B mamo {N}<-{peer}", R, st, gcal if peer == "oss20" else None)
                for sub in ("mamo_easy", "mamo_complex"):
                    Rs = {k: v for k, v in R.items() if k[0].split("/", 1)[1].startswith(sub + "-")}
                    a, b_ = H.per_q(Rs, "PND"), H.per_q(Rs, "D")
                    g = ci({i: a[i][1] - b_[i][1] for i in a})
                    print(f"{'':>16}  {sub}: PND - D {g[0]:+.2f} [{g[1]:+.2f}, {g[2]:+.2f}] ({len(a)} problems)")


if __name__ == "__main__":
    main()
