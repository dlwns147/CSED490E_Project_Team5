"""CONT-A (docs/prereg/PREREG_CONT.md, addendum A): agreement as the stop signal inside the default's thinks, on poc/run_cont.py's rows
and the stored cheap programs (formx of Qwen3-8B, N, and of Qwen3.5-9B, the peer; HO-PA's pairing: same problem and seed). An answer =
(passes, right, tokens, value); two answers agree = both pass and print the same value within the grader's tolerance (HO-PA's same_word).
Per problem and seed s (s2 = s % 3 + 1, s3 = s2 % 3 + 1):
  RD(S)   CONT's restart policy with exits (analyze_cont): first(s); on a failed check think s2 checked at S, the first passing program answers;
  RDc(S)  RD with convergence exits: inside think s2 a forced program answers only if it passes and agrees with an earlier passing forced
          program of think s2 (Dynasor-CoT / Answer Convergence on executed programs); its end, then think s3's end, as RD;
  PR0     the peer cascade replayed on these thinks: N passes and the peer agrees -> N; else R0 (analyze_cont);
  PRA(S)  the peer cascade with agreement exits: N passes and the peer agrees -> N; else every later program answers only if it passes and
          agrees with an earlier passing answer of the stream (N, the peer, the 2,000-token cut of think s, earlier forced programs of think
          s2); think s2's end answers if it passes, then think s3's end; if none passes, the last passing think program, else wrong.
The peer runs only when N passes (HO-PA). S: greedy forward selection over 1,000 ... 15,000 on one half of the problems (crc32(id) % 2),
scored on the other (cross-fitted), as analyze_cont. Tests: CA-P1 RDc - RD, CA-P2 PRA - the stored default SB->T->T, CA-P3 PRA - the
stored peer cascade N->q35->SB->T->T (analyze_hopa, rows of other runs), CA-P4 the share right of passing forced programs (every cut of
every think) that agree with the peer's quick program - of those that agree with the latest earlier passing forced program of the same think.
usage: python analyze_conta.py [tag q8b]"""
import contextlib, io, os, sys, zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
with contextlib.redirect_stdout(io.StringIO()):
    from analyze_cont import GRID, first, load, ok_, util
    from analyze_ho3 import ci
    from analyze_hopa import BENCH, boot_diff, per_q, policies, same_word, word_rows


def ans(p):
    return (ok_(p), bool(p["right"]), p["tok"], p["pred"])


def agrees(x, seen):
    return x[0] and any(same_word(x, y) for y in seen)


def think(t, S, need, seen, last):
    """think t checked at S (from 0); a passing forced program answers if (not need) or it agrees with `seen` (extended in place with
    every passing forced program; `last` collects them); -> (stopped, right, tokens): stopped False = the end program failed"""
    cut = {p["at"]: p for p in t["probes"]}
    tok, at = 0, 0
    for c in sorted(S):
        if c not in cut:
            continue
        p = cut[c]; tok += c - at + p["tok"]; at = c
        x = ans(p)
        if x[0]:
            if not need or agrees(x, seen):
                return True, x[1], tok
            seen.append(x); last.append(x)
    e = t["end"]
    return ok_(e), e["right"], tok + max(0, t["think_tok"] - at) + e["tok"]


def policy(T, NQ, PQ, i, s, kind, S=()):
    s2 = s % 3 + 1; s3 = s2 % 3 + 1
    tok, seen, last = 0, [], []
    if kind in ("PR0", "PRA"):
        n = NQ[s][i]; tok += n[2]
        if n[0]:
            p = PQ[s][i]; tok += p[2]
            if same_word(n, p):
                return n[1], tok
            seen += [x for x in (n, p) if x[0]]
    a_ok, a_r, a_tok, _ = first(T[s][i]); tok += a_tok
    a = next((p for p in T[s][i]["probes"] if p["at"] == 2000), T[s][i]["end"])   # the program first() checked
    if a_ok and (kind != "PRA" or agrees(ans(a), seen)):
        return a_r, tok
    if a_ok:
        seen.append(ans(a)); last.append(ans(a))
    if kind in ("RD", "RDc", "PRA"):
        own = [] if kind == "RDc" else seen     # RDc: agreement among think s2's own forced programs only
        b_ok, b_r, b_tok = think(T[s2][i], S, kind != "RD", own, last)
    else:
        b_ok, b_r, b_tok = think(T[s2][i], (), False, seen, last)
    tok += b_tok
    if b_ok:
        return b_r, tok
    c = T[s3][i]["end"]; tok += T[s3][i]["think_tok"] + c["tok"]
    if ok_(c) or kind != "PRA":
        return c["right"], tok
    return (last[-1][1] if last else False), tok


def fit(data, keys, kind):
    def score(S):
        return sum(util(*policy(*data[b], i, s, kind, S)) for b, i in keys for s in (1, 2, 3))
    S, best = (), score(())
    while True:
        cand = [(score(tuple(sorted(S + (c,)))), c) for c in GRID if c not in S]
        if not cand or max(cand)[0] <= best:
            return S
        best, c = max(cand); S = tuple(sorted(S + (c,)))


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "q8b"
    data, stored = {}, {}
    for b in BENCH:
        (T, ids), A, P = load(tag, b), word_rows("q8b", b), word_rows("q35", b)
        if not (A and P):
            continue
        ids = [i for i in ids if all(i in A["formx"][s] and i in P["formx"][s] for s in (1, 2, 3))]
        data[b] = (T, A["formx"], P["formx"], ids)
        R = policies(A, {"q35": P}, same_word)
        for k in ("SB->T->T", "N->q35->SB->T->T"):
            for i, v in per_q(R, k).items():
                stored.setdefault(k, {})[f"{b}/{i}"] = v
    keys = [(b, i) for b in data for i in data[b][3]]
    data = {b: v[:3] for b, v in data.items()}
    print(f"=== CONT-A {tag}: {len(keys)} problems with three thinks and both cheap programs")
    if not keys:
        return
    # precision of passing forced programs by what they agree with (every cut of every think)
    cls = {k: {} for k in ("peer", "N", "prev", "none", "all")}
    for b, i in keys:
        T, NQ, PQ = data[b]
        for s in (1, 2, 3):
            n, p = NQ[s][i], PQ[s][i]
            prev = None
            for q in T[s][i]["probes"]:
                x = ans(q)
                if not x[0]:
                    continue
                tags = ["all"] + [k for k, y in (("peer", p), ("N", n), ("prev", prev)) if y and same_word(x, y)]
                if len(tags) == 1:
                    tags.append("none")
                for k in tags:
                    v = cls[k].setdefault(f"{b}/{i}", [0, 0]); v[0] += x[1]; v[1] += 1
                prev = x
    n_all = sum(v[1] for v in cls["all"].values())
    print("passing forced programs: " + ", ".join(f"agree {k} {100 * sum(v[0] for v in d.values()) / max(1, sum(v[1] for v in d.values())):.1f}% right "
                                                   f"({100 * sum(v[1] for v in d.values()) / max(1, n_all):.0f}% of them)" for k, d in cls.items()))
    folds = {f: [k for k in keys if zlib.crc32(k[1].encode()) % 2 == f] for f in (0, 1)}
    S = {kind: {f: fit(data, folds[1 - f], kind) for f in (0, 1)} for kind in ("RD", "RDc", "PRA")}
    for kind in S:
        print(f"{kind} cut points fitted on half 1 (scored on half 0): {S[kind][0]}; on half 0: {S[kind][1]}")
    q = {}
    for kind in ("RD", "RDc", "PR0", "PRA"):
        for f in (0, 1):
            for b, i in folds[f]:
                v = [policy(*data[b], i, s, kind, S[kind][f] if kind in S else ()) for s in (1, 2, 3)]
                q.setdefault(kind, {})[f"{b}/{i}"] = (sum(r for r, _ in v) / 3, sum(util(r, t) for r, t in v) / 3, sum(t for _, t in v) / 3)
    for k, d in stored.items():
        q[k] = {i: (v[0], v[1], None) for i, v in d.items() if i in q["RD"]}
    ids = sorted(q["RD"])
    for kind, d in q.items():
        jj = [i for i in ids if i in d]
        tk = f" @ {sum(d[i][2] for i in jj) / len(jj) / 1000:.2f}k" if d[jj[0]][2] is not None else ""
        print(f"  {kind:>16}: {len(jj)} problems, accuracy {100 * sum(d[i][0] for i in jj) / len(jj):.1f}%{tk}, utility "
              f"{100 * sum(d[i][1] for i in jj) / len(jj):.2f}")
    for b in BENCH:
        jj = [i for i in ids if i.startswith(b + "/")]
        if jj:
            print(f"  {b}: " + ", ".join(f"{k} {100 * sum(q[k][i][1] for i in jj) / len(jj):.2f}" for k in q if all(i in q[k] for i in jj)))
    out = []
    for name, a, b_ in (("CA-P1 RDc - RD", "RDc", "RD"), ("CA-P2 PRA - stored SB->T->T", "PRA", "SB->T->T"),
                        ("CA-P3 PRA - stored N->q35->SB->T->T", "PRA", "N->q35->SB->T->T")):
        jj = [i for i in ids if i in q[a] and i in q[b_]]
        g = ci({i: q[a][i][1] - q[b_][i][1] for i in jj})
        print(f"{name}: utility {g[0]:+.2f} [{g[1]:+.2f}, {g[2]:+.2f}] ({len(jj)} problems)")
        out.append(f"{name.split()[0]} {g[1] > 0} ({g[0]:+.2f} [{g[1]:+.2f}, {g[2]:+.2f}])")
    g = boot_diff(cls["peer"], cls["prev"])
    print(f"CA-P4 right | agrees with the peer - right | agrees with the latest earlier passing forced program of the same think: {g[0]:+.1f} [{g[1]:+.1f}, {g[2]:+.1f}] points")
    out.append(f"CA-P4 {g[1] > 0} ({g[0]:+.1f} [{g[1]:+.1f}, {g[2]:+.1f}])")
    print("*** " + "; ".join(out))


if __name__ == "__main__":
    main()
