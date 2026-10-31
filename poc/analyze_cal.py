"""XPEER addendum CAL (docs/prereg/PREREG_XPEER.md; offline on stored rows): is the stratified prediction's overshoot a winner's curse
(the peer chosen on the calibration rows) or a transfer bias (agreement by stratum depends on the N model)? 200 random half-splits of
the four stored word-problem sets' problems. On half A, Qwen3-8B as the calibration N: each stored peer's cascade gain (N -> its check ->
the peer prints the same value -> N, else SB->T->T; minus SB->T->T) and its agreement rate in each stratum of Qwen3-8B's passing
programs (analyze_xpeer.parts); k* = the peer with the largest gain on A. On half B, for each target N and peer k != N: realised gain
and analyze_xpeer.predict (N's strata on B x A's calibration). Averaged over splits: curse = gain(k*, A) - realised(k*, B) for
Qwen3-8B; e_sel(N) = predicted - realised for k*; e_all(N) = the same averaged over the peers.
usage: python3.11 poc/analyze_cal.py [splits]"""
import contextlib, io, os, random, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
with contextlib.redirect_stdout(io.StringIO()):
    import analyze_hopa as H  # noqa: E402
    import analyze_xpeer as X  # noqa: E402

TARGETS = ("q8b", "q14a", "q35", "n3n")


def cells():
    """{(N, peer): [(problem key, item tuple, cascade utility, default utility)]} per problem-seed"""
    out = {}
    for N in TARGETS:
        A = {b: H.word_rows(N, b) for b in H.BENCH}
        for k in X.PEERS:
            if k == N:
                continue
            rows = []
            for b in H.BENCH:
                P = {"formx": X.formx(k, b)}
                if A[b] is None or any(not P["formx"][s] for s in (1, 2, 3)):
                    rows = None; break
                for (i, s), r in H.policies(A[b], {"p": P}, X.safe_same).items():
                    f, p = A[b]["formx"][s][i], P["formx"][s][i]
                    u = lambda v: 100 * float(v[0]) - H.LAM * v[1] / 1000
                    rows.append((f"{b}/{i}", (f[0], f[1], f[2], f[0] and X.safe_same(f, p), p[2], r[X.DEF][0], r[X.DEF][1]),
                                 u(r[X.CAS]), u(r[X.DEF])))
            if rows:
                out[(N, k)] = rows
    return out


def gain(rows):
    per = {}
    for key, _, c, d in rows:
        per.setdefault(key, []).append(c - d)
    return sum(sum(v) / len(v) for v in per.values()) / max(1, len(per))


def main():
    S = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    C = cells()
    print("cells: " + ", ".join(f"{N}<-{k}" for N, k in sorted(C)))
    keys = sorted({x[0] for v in C.values() for x in v})
    peers = [k for k in X.PEERS if ("q8b", k) in C]
    curse, esel, eall, full = [], {N: [] for N in TARGETS}, {N: [] for N in TARGETS}, {}
    for N, k in C:
        full[(N, k)] = gain(C[(N, k)])
    rng = random.Random(0)
    for _ in range(S):
        half = set(rng.sample(keys, len(keys) // 2))
        A = {nk: [x for x in v if x[0] in half] for nk, v in C.items()}
        B = {nk: [x for x in v if x[0] not in half] for nk, v in C.items()}
        gA = {k: gain(A[("q8b", k)]) for k in peers}
        ks = max(peers, key=gA.get)
        curse.append(gA[ks] - gain(B[("q8b", ks)]))
        for N in TARGETS:
            errs = {}
            for k in peers:
                if (N, k) not in C:
                    continue
                cal = X.parts([x[1] for x in A[("q8b", k)]])
                errs[k] = X.predict([x[1] for x in B[(N, k)]], cal) - gain(B[(N, k)])
            if ks in errs:
                esel[N].append(errs[ks])
            eall[N].append(sum(errs.values()) / len(errs))
    m = lambda v: sum(v) / max(1, len(v))
    sd = lambda v: (sum((x - m(v)) ** 2 for x in v) / max(1, len(v) - 1)) ** 0.5
    print("full-data gains (Qwen3-8B as N): " + ", ".join(f"{k} {full[('q8b', k)]:+.2f}" for k in peers))
    print(f"{S} splits: curse (Qwen3-8B, chosen peer's gain on A - on B) {m(curse):+.2f} (sd {sd(curse):.2f})")
    for N in TARGETS:
        print(f"  {N}: e_sel {m(esel[N]):+.2f} (sd {sd(esel[N]):.2f}, {len(esel[N])} splits), e_all {m(eall[N]):+.2f} (sd {sd(eall[N]):.2f}), "
              f"e_sel - e_all {m(esel[N]) - m(eall[N]):+.2f}")
    others = [N for N in TARGETS if N != "q8b"]
    p2 = sum(abs(m(eall[N])) <= 0.3 for N in TARGETS)
    p3 = sum(m(esel[N]) - m(eall[N]) >= 0.3 for N in others)
    print(f"*** CAL-P1 curse >= 0.4: {m(curse) >= 0.4}; CAL-P2 |e_all| <= 0.3 in {p2} / 4 (needs 3): {p2 >= 3}; "
          f"CAL-P3 e_sel - e_all >= 0.3 in {p3} / 3 (needs 3): {p3 >= 3}")


if __name__ == "__main__":
    main()
