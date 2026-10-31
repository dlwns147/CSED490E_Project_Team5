"""RF (docs/prereg/PREREG_TD.md, addendum RF): RFT on WP-RL's 4,000 training problems (q8brft4k: per problem the first right of 8 quick
programs) against RFT on the first 2,000 (q8brft), against plain on-policy RL on the same 4,000 (WP-RL, q8bwp1), and the default, in
HO-PA's word-problem cascade (N -> its free check -> Qwen3.5-9B's formx prints the same value -> N, else Qwen3-8B's SB->T->T), as
analyze_td.py. Paired 95% intervals over problems (seed means), pooled over OptiBench's third, BWOR, LogiOR, OptMATH; utility = accuracy
- 0.5 x ktokens. RF-P1: rft4k cascade - SB->T->T; RF-P2: rft4k cascade - rft cascade; RF-P3: rft4k cascade - wp cascade, lower bound
> -0.5 (non-inferior within 0.5 utility points = 1,000 tokens per problem). Reported: quick right, tokens, right | passes (the leak),
per benchmark, and each cascade's gain split into the problems no base sample of 16 answers right and the others.
usage: python analyze_rf.py [--tags rft4k,rft,wp]   (default q8brft4k,q8brft,q8bwp1)"""
import contextlib, io, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
with contextlib.redirect_stdout(io.StringIO()):
    from analyze_ho3 import ci
    from analyze_hopa import BENCH, per_q, policies, word_rows
    from analyze_sharp import safe_same, word_k

CAS = "N->q35->SB->T->T"
K = 16


def main():
    tags = (sys.argv[sys.argv.index("--tags") + 1] if "--tags" in sys.argv else "q8brft4k,q8brft,q8bwp1").split(",")
    names = ("rft4k", "rft", "wp")
    pool = {}
    for b in BENCH:
        A, X = word_rows("q8b", b), word_rows("q35", b)
        Bk = word_k("q8b", b, range(1, K + 1))
        arms = {"base": {s: Bk[s] for s in (1, 2, 3)}}
        for n, t in zip(names, tags):
            F = word_k(t, b, (1, 2, 3))
            if len(F) == 3:
                arms[n] = F
        R0 = policies(A, {"q35": X}, safe_same)
        ids = sorted({i for i, _ in R0 if all(i in Bk[s] for s in range(1, K + 1)) and all(i in F[s] for F in arms.values() for s in (1, 2, 3))})
        never = {i: not any(Bk[s][i][1] for s in range(1, K + 1)) for i in ids}
        q = {"d": per_q({k: v for k, v in R0.items() if k[0] in ids}, "SB->T->T")}
        for n, F in arms.items():
            R = policies(dict(A, formx=F), {"q35": X}, safe_same)
            q["c_" + n] = per_q({k: v for k, v in R.items() if k[0] in ids}, CAS)
            q["k_" + n] = {i: (sum(F[s][i][1] for s in (1, 2, 3)) / 3, sum(F[s][i][2] for s in (1, 2, 3)) / 3,
                               sum(F[s][i][0] for s in (1, 2, 3)), sum(F[s][i][0] and F[s][i][1] for s in (1, 2, 3))) for i in ids}
        print(f"=== {b}: {len(ids)} problems; " + ", ".join(
            f"{n} quick right {100 * sum(q['k_' + n][i][0] for i in ids) / len(ids):.1f}%, cascade - SB->T->T "
            f"{100 * sum(q['c_' + n][i][1] - q['d'][i][1] for i in ids) / len(ids):+.2f}" for n in arms))
        for k, v in q.items():
            pool.setdefault(k, {}).update({f"{b}/{i}": v[i] for i in ids})
        pool.setdefault("never", {}).update({f"{b}/{i}": never[i] for i in ids})
    ids = sorted(pool["d"])
    have = [n for n in ("base",) + names if "k_" + n in pool]
    print(f"=== pooled: {len(ids)} problems, {sum(pool['never'][i] for i in ids)} base-never")
    for n in have:
        k, c = pool["k_" + n], pool["c_" + n]
        g = ci({i: c[i][1] - pool["d"][i][1] for i in ids})
        parts = [ci({i: (c[i][1] - pool["d"][i][1]) if pool["never"][i] == nv else 0.0 for i in ids})[0] for nv in (True, False)]
        print(f"  {n:>5}: quick right {100 * sum(k[i][0] for i in ids) / len(ids):.1f}% @ {sum(k[i][1] for i in ids) / len(ids) / 1000:.2f}k, "
              f"right | passes {100 * sum(k[i][3] for i in ids) / max(1, sum(k[i][2] for i in ids)):.1f}%; cascade - SB->T->T "
              f"{g[0]:+.2f} [{g[1]:+.2f}, {g[2]:+.2f}] (base-never {parts[0]:+.2f}, covered {parts[1]:+.2f})")
    if "c_rft4k" not in pool:
        return
    out = []
    for name, a, b_, bar in (("RF-P1 rft4k cascade - SB->T->T", "c_rft4k", "d", 0.0), ("RF-P2 rft4k cascade - rft cascade", "c_rft4k", "c_rft", 0.0),
                             ("RF-P3 rft4k cascade - wp cascade (margin -0.5)", "c_rft4k", "c_wp", -0.5)):
        if b_ not in pool:
            continue
        g = ci({i: pool[a][i][1] - pool[b_][i][1] for i in ids})
        print(f"{name}: utility {g[0]:+.2f} [{g[1]:+.2f}, {g[2]:+.2f}]")
        out.append(f"{name.split()[0]} {g[1] > bar} ({g[0]:+.2f} [{g[1]:+.2f}, {g[2]:+.2f}])")
    print("*** " + "; ".join(out))


if __name__ == "__main__":
    main()
