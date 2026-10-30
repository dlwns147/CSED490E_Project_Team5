"""TD (docs/prereg/PREREG_TD.md): the quick program fine-tuned on the thinking mode's right programs (q8btd) against the one fine-tuned
on its own right quick programs (q8brft), in HO-PA's word-problem cascade (as analyze_wprl.py): N -> its free check -> Qwen3.5-9B's
formx prints the same value -> N, else Qwen3-8B's SB->T->T. Base coverage = base Qwen3-8B formx seeds 1..K (SHARP); "base-never" =
no base seed answers right. Paired 95% intervals over problems (seed means), pooled over OptiBench's third, BWOR, LogiOR, OptMATH;
utility = accuracy - 0.5 x ktokens. TD-P1: quick right td - rft on base-never problems; TD-P2: the same on all; TD-P3: td cascade -
SB->T->T; TD-P4: td cascade - rft cascade. Also each arm against the base and WP-RL's q8bwp1 where its rows exist.
usage: python analyze_td.py [K 16] [--tags td,rft,wp]   (default q8btd,q8brft,q8bwp1)"""
import contextlib, io, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
with contextlib.redirect_stdout(io.StringIO()):   # imported modules print their own tables
    from analyze_ho3 import ci
    from analyze_hopa import BENCH, per_q, policies, word_rows
    from analyze_sharp import safe_same, word_k
    from run_nlopt import RES, _rows

CAS = "N->q35->SB->T->T"


def main():
    K = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 16
    td, rft, wp = (sys.argv[sys.argv.index("--tags") + 1] if "--tags" in sys.argv else "q8btd,q8brft,q8bwp1").split(",")
    K = min(max(k for k in range(1, K + 1) if all(_rows(f"{RES}/opt_q8b_{b}_formx_s{s}.jsonl") for s in range(1, k + 1))) for b in BENCH)
    pool = {}
    for b in BENCH:
        A, X = word_rows("q8b", b), word_rows("q35", b)
        B = word_k("q8b", b, range(1, K + 1))
        arms = {"base": {s: B[s] for s in (1, 2, 3)}}
        for name, tag in (("td", td), ("rft", rft), ("wp", wp)):
            F = word_k(tag, b, (1, 2, 3))
            if len(F) == 3:
                arms[name] = F
        R0 = policies(A, {"q35": X}, safe_same)
        ids = sorted({i for i, _ in R0 if all(i in B[s] for s in range(1, K + 1)) and all(i in F[s] for F in arms.values() for s in (1, 2, 3))})
        never = {i: not any(B[s][i][1] for s in range(1, K + 1)) for i in ids}
        q = {"d": per_q({k: v for k, v in R0.items() if k[0] in ids}, "SB->T->T")}
        for name, F in arms.items():
            R = policies(dict(A, formx=F), {"q35": X}, safe_same)
            q["c_" + name] = per_q({k: v for k, v in R.items() if k[0] in ids}, CAS)
            q["k_" + name] = {i: (sum(F[s][i][1] for s in (1, 2, 3)) / 3, sum(F[s][i][2] for s in (1, 2, 3)) / 3) for i in ids}
        line = ", ".join(f"{n} {100 * sum(q['k_' + n][i][0] for i in ids) / len(ids):.1f}% @ "
                         f"{sum(q['k_' + n][i][1] for i in ids) / len(ids) / 1000:.2f}k" for n in arms)
        print(f"=== {b}: {len(ids)} problems ({sum(never.values())} base-never at K = {K}); quick right: {line}")
        for n in arms:
            g = ci({i: q["c_" + n][i][1] - q["d"][i][1] for i in ids})
            print(f"  N {n:>4} -> peer -> SB->T->T: accuracy {100 * sum(q['c_' + n][i][0] for i in ids) / len(ids):.1f}%, "
                  f"- SB->T->T utility {g[0]:+.2f} [{g[1]:+.2f}, {g[2]:+.2f}]")
        for k, v in q.items():
            pool.setdefault(k, {}).update({f"{b}/{i}": v[i] for i in ids})
        pool.setdefault("never", {}).update({f"{b}/{i}": never[i] for i in ids})
    ids = sorted(pool["d"])
    nv = [i for i in ids if pool["never"][i]]
    names = [k[2:] for k in pool if k.startswith("k_")]
    print(f"=== pooled: {len(ids)} problems, {len(nv)} base-never")
    for n in names:
        print(f"  {n:>4}: quick right {100 * sum(pool['k_' + n][i][0] for i in ids) / len(ids):.1f}% (base-never "
              f"{100 * sum(pool['k_' + n][i][0] for i in nv) / max(1, len(nv)):.1f}%), quick tokens "
              f"{sum(pool['k_' + n][i][1] for i in ids) / len(ids) / 1000:.2f}k; cascade - SB->T->T "
              + "{:+.2f} [{:+.2f}, {:+.2f}]".format(*ci({i: pool['c_' + n][i][1] - pool['d'][i][1] for i in ids})))
    if "td" not in names or "rft" not in names:
        return
    out = []
    for name, d, sub, j in (("TD-P1 quick right td - rft, base-never", ("k_td", "k_rft"), nv, 0),
                            ("TD-P2 quick right td - rft, all", ("k_td", "k_rft"), ids, 0),
                            ("TD-P3 td cascade - SB->T->T", ("c_td", "d"), ids, 1),
                            ("TD-P4 td cascade - rft cascade", ("c_td", "c_rft"), ids, 1)):
        g = ci({i: pool[d[0]][i][j] - pool[d[1]][i][j] for i in sub})
        print(f"pooled: {name}: {'points' if j == 0 else 'utility'} {g[0]:+.2f} [{g[1]:+.2f}, {g[2]:+.2f}]")
        out.append(f"{name.split()[0]} {g[1] > 0} ({g[0]:+.2f} [{g[1]:+.2f}, {g[2]:+.2f}])")
    for other in ("base", "wp"):
        if other in names:
            for k, j in (("c_", 1), ("k_", 0)):
                g = ci({i: pool[k + "td"][i][j] - pool[k + other][i][j] for i in ids})
                print(f"  td - {other} ({'cascade utility' if j else 'quick right'}): {g[0]:+.2f} [{g[1]:+.2f}, {g[2]:+.2f}]")
    print("*** " + "; ".join(out))


if __name__ == "__main__":
    main()
