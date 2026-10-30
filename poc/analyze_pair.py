"""TC-RL addendum 1 (docs/prereg/PREREG_TCRL.md) and CV-1 addendum 7 (docs/prereg/PREREG_CV.md): train the peer too. Cascade N -> X
makes the same answer -> N, else the default (SB->T->T); paired 95% intervals over items (seed means), utility = accuracy - 0.5 x ktokens.
--tc: TCRL-P4..P9 — Qwen3-4B trained on ToolACE (q4btcc1) against its base (q4b) with its own default; the 2x2 N in {q8b, q8btcc1} x
X in {q4b, q4btcc1} with Qwen3-8B's default; the no-call rule (a no-call quick answer is accepted without the peer).
--sql: CV-P18 / P19 — the same 2x2 on BIRD dev with X in {q4b, q4bcvc1} (and q35 for P19).
Independence estimate (theory row): the peer's answer at the other two seeds in place of its answer at the same seed.
--bil: TCRL-P10..P12 (addendum 2) — Qwen3-8B trained with the cascade's own reward against peer Qwen3.5-9B (q8btcb35) / C1tc-4B
(q8btcb4t) vs C1tc with the same peer; P12: accepted wrong where the default is right (and accepted right where it is wrong).
usage: python analyze_pair.py --tc | --sql | --bil"""
import contextlib, io, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
with contextlib.redirect_stdout(io.StringIO()):   # imported modules print their own tables
    from analyze_dv import default, quick, same, per_q
    from analyze_ho3 import ci
    from analyze_cv import base
    from analyze_cvpeer import composed
    import analyze_hopa  # noqa: F401 (default() imports it lazily)


def run(kind, D, N, X, nocall=False, indep=False):
    """{(id, seed): (right, tokens)} of N -> X agrees -> N, else D"""
    out = {}
    for (i, s), d in D.items():
        n = N[s][i]
        if not n[0]:
            out[(i, s)] = (d[0], n[2] + d[1]); continue
        if nocall and n[3] == "none":
            out[(i, s)] = (n[1], n[2]); continue
        ts = [t for t in (1, 2, 3) if t != s] if indep else [s]
        ag = sum(same(kind, n, X[t][i]) for t in ts) / len(ts)
        out[(i, s)] = (ag * n[1] + (1 - ag) * d[0], n[2] + X[s][i][2] + (1 - ag) * d[1])
    return out


def common(D, Zs):
    ids = {i for i, s in D if all((i, t) in D and all(i in Z[t] for Z in Zs) for t in (1, 2, 3))}
    return ids, {k: v for k, v in D.items() if k[0] in ids}


def show(name, Q, ref, ids):
    a = 100 * sum(Q[i][0] for i in ids) / len(ids)
    du = ci({i: Q[i][1] - ref[i][1] for i in ids})
    print(f"  {name:>44}: accuracy {a:.1f}%, utility {100 * sum(Q[i][1] for i in ids) / len(ids):.2f} | - default {du[0]:+.2f} "
          f"[{du[1]:+.2f}, {du[2]:+.2f}]")
    return du


def grid(kind, D, Ns, Xs):
    """the 2x2 (and extra peers): {(n, x): per-item (acc, utility)}, the same-seed - independence gap per cell"""
    ids, D = common(D, list(Ns.values()) + list(Xs.values()))
    ref = per_q(D)
    print(f"  {len(ids)} items x 3 seeds; default {100 * sum(ref[i][0] for i in ids) / len(ids):.1f}%")
    Q, gap = {}, {}
    for nn, N in Ns.items():
        for xn, X in Xs.items():
            Q[(nn, xn)] = per_q(run(kind, D, N, X))
            show(f"N {nn} -> peer {xn} -> default", Q[(nn, xn)], ref, ids)
            I = per_q(run(kind, D, N, X, indep=True))
            gap[(nn, xn)] = 100 * sum(Q[(nn, xn)][i][1] - I[i][1] for i in ids) / len(ids)
            print(f"  {'':>44}  independence estimate {100 * sum(I[i][1] for i in ids) / len(ids):.2f} (same seed - it: "
                  f"{gap[(nn, xn)]:+.2f})")
    return ids, ref, Q, gap


def inter(Q, ids, n0, n1, x0, x1):
    return ci({i: Q[(n1, x1)][i][1] - Q[(n1, x0)][i][1] - Q[(n0, x1)][i][1] + Q[(n0, x0)][i][1] for i in ids})


def tc():
    N4, T4, X = quick("tc", "q4b"), quick("tc", "q4btcc1"), quick("tc", "q35")
    D4 = default("tc", "q4b")
    print("=== TCRL-P4..P6, P9: Qwen3-4B, BFCL, peer Qwen3.5-9B, Qwen3-4B's SB->T->T")
    ids, D4 = common(D4, [N4, T4, X])
    ref = per_q(D4)
    d1 = ci({i: sum(T4[s][i][1] for s in (1, 2, 3)) / 3 - sum(N4[s][i][1] for s in (1, 2, 3)) / 3 for i in ids})
    print(f"  {len(ids)} items; quick calls right: base {100 * sum(N4[s][i][1] for s in (1, 2, 3) for i in ids) / 3 / len(ids):.1f}%, "
          f"C1tc-4B {100 * sum(T4[s][i][1] for s in (1, 2, 3) for i in ids) / 3 / len(ids):.1f}% ({d1[0]:+.1f} [{d1[1]:+.1f}, {d1[2]:+.1f}])")
    show("default (Qwen3-4B SB->T->T)", ref, ref, ids)
    Qb, Qt = per_q(run("tc", D4, N4, X)), per_q(run("tc", D4, T4, X))
    show("N base 4B -> peer -> default", Qb, ref, ids)
    u2 = show("N C1tc-4B -> peer -> default", Qt, ref, ids)
    u3 = ci({i: Qt[i][1] - Qb[i][1] for i in ids})
    Qr = per_q(run("tc", D4, T4, X, nocall=True))
    show("N C1tc-4B, no-call accepted, else peer", Qr, ref, ids)
    u9 = ci({i: Qr[i][1] - Qt[i][1] for i in ids})
    print(f"*** TCRL-P4 {d1[1] > 0}; TCRL-P5 {u2[1] > 0}; TCRL-P6 {u3[1] > 0} ({u3[0]:+.2f} [{u3[1]:+.2f}, {u3[2]:+.2f}]); TCRL-P9 "
          f"{u9[1] > 0} ({u9[0]:+.2f} [{u9[1]:+.2f}, {u9[2]:+.2f}])")
    print("=== TCRL-P7 / P8: Qwen3-8B's default, N in {q8b, q8btcc1}, peer in {q4b, q4btcc1, q35}")
    ids, ref, Q, gap = grid("tc", default("tc", "q8b"), {"q8b": quick("tc", "q8b"), "q8btcc1": quick("tc", "q8btcc1")},
                            {"q4b": N4, "q4btcc1": T4, "q35": X})
    u7 = inter(Q, ids, "q8b", "q8btcc1", "q4b", "q4btcc1")
    u8 = ci({i: Q[("q8btcc1", "q4btcc1")][i][1] - Q[("q8btcc1", "q35")][i][1] for i in ids})
    th = all(abs(gap[(n, x)]) <= 0.2 for n in ("q8b", "q8btcc1") for x in ("q4b", "q4btcc1"))
    print(f"*** TCRL-P7 (interaction) {u7[1] > 0} ({u7[0]:+.2f} [{u7[1]:+.2f}, {u7[2]:+.2f}]); TCRL-P8 {u8[1] > 0} ({u8[0]:+.2f} "
          f"[{u8[1]:+.2f}, {u8[2]:+.2f}]); TCRL-P8 theory (independence within 0.2 in the 2x2) {th}")


def sql():
    D = {k: v["SB->T->T"] for k, v in base("q8b").items()}
    print("=== CV-P18 / P19: BIRD dev, Qwen3-8B's default, N in {q8b, q8bcvc1}, peer in {q4b, q4bcvc1, q35}")
    ids, ref, Q, gap = grid("sql", D, {"q8b": quick("sql", "q8b"), "q8bcvc1": quick("sql", "q8bcvc1")},
                            {"q4b": quick("sql", "q4b"), "q4bcvc1": quick("sql", "q4bcvc1"), "q35": quick("sql", "q35")})
    u18 = inter(Q, ids, "q8b", "q8bcvc1", "q4b", "q4bcvc1")
    u19 = ci({i: Q[("q8bcvc1", "q4bcvc1")][i][1] - Q[("q8bcvc1", "q35")][i][1] for i in ids})
    th = all(abs(gap[(n, x)]) <= 0.2 for n in ("q8b", "q8bcvc1") for x in ("q4b", "q4bcvc1"))
    print(f"*** CV-P18 (interaction) {u18[1] > 0} ({u18[0]:+.2f} [{u18[1]:+.2f}, {u18[2]:+.2f}]); CV-P19 {u19[1] > 0} ({u19[0]:+.2f} "
          f"[{u19[1]:+.2f}, {u19[2]:+.2f}]); CV-P18 theory (independence within 0.2 in the 2x2) {th}")


def accepted(kind, D, N, X, ids):
    """per item (seed means): N accepted and wrong where the default is right; accepted and right where it is wrong"""
    wr, rw = {}, {}
    for i in ids:
        a = [(N[s][i][0] and same(kind, N[s][i], X[s][i]), N[s][i][1], D[(i, s)][0]) for s in (1, 2, 3)]
        wr[i] = sum(g and not n and d for g, n, d in a) / 3
        rw[i] = sum(g and n and not d for g, n, d in a) / 3
    return wr, rw


def bil():
    D = default("tc", "q8b")
    C1, B35, B4t = quick("tc", "q8btcc1"), quick("tc", os.environ.get("BIL35", "q8btcb35")), quick("tc", os.environ.get("BIL4T", "q8btcb4t"))
    out = []
    for name, B, xt in (("P10", B35, "q35"), ("P11", B4t, "q4btcc1")):
        if B is None:
            print(f"=== TCRL-{name}: no rows"); continue
        X = quick("tc", xt)
        ids, Dc = common(D, [C1, B, X])
        ref = per_q(Dc)
        print(f"=== TCRL-{name}: peer {xt}, Qwen3-8B's SB->T->T ({100 * sum(ref[i][0] for i in ids) / len(ids):.1f}%), {len(ids)} items x 3 seeds")
        r = {k: 100 * sum(Q[s][i][1] for s in (1, 2, 3) for i in ids) / 3 / len(ids) for k, Q in (("C1tc", C1), ("cascade reward", B))}
        print(f"  quick calls right: C1tc {r['C1tc']:.1f}%, cascade reward {r['cascade reward']:.1f}%")
        Qc, Qb = per_q(run("tc", Dc, C1, X)), per_q(run("tc", Dc, B, X))
        show(f"N C1tc -> peer {xt} -> default", Qc, ref, ids)
        show(f"N cascade reward -> peer {xt} -> default", Qb, ref, ids)
        u = ci({i: Qb[i][1] - Qc[i][1] for i in ids})
        (wc, rc), (wb, rb) = accepted("tc", Dc, C1, X, ids), accepted("tc", Dc, B, X, ids)
        w, a = ci({i: wb[i] - wc[i] for i in ids}), ci({i: rb[i] - rc[i] for i in ids})
        print(f"  accepted wrong where the default is right: C1tc {100 * sum(wc.values()) / len(ids):.2f}%, cascade reward "
              f"{100 * sum(wb.values()) / len(ids):.2f}% ({w[0]:+.2f} [{w[1]:+.2f}, {w[2]:+.2f}]); accepted right where it is wrong: "
              f"{100 * sum(rc.values()) / len(ids):.2f}% vs {100 * sum(rb.values()) / len(ids):.2f}% ({a[0]:+.2f} [{a[1]:+.2f}, {a[2]:+.2f}])")
        out.append(f"TCRL-{name} {u[1] > 0} ({u[0]:+.2f} [{u[1]:+.2f}, {u[2]:+.2f}]); TCRL-P12 ({xt}) {w[2] < 0}")
    print("*** " + "; ".join(out))


if __name__ == "__main__":
    {"--tc": tc, "--sql": sql, "--bil": bil}[sys.argv[1]]()
