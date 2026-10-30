"""TC-RL (docs/prereg/PREREG_TCRL.md): plain RL's quick tool calls (tag q8btcc1, ToolACE-trained adapter) on BFCL against the base
quick calls (TC-1's q8b), each with the peer check (Qwen3.5-9B's quick calls the same, else Qwen3-8B's SB->T->T, HO-PA's cascade), paired
95% intervals over items (seed means), utility = accuracy - 0.5 x ktokens; the decomposition's prediction with the base calls' agreement
rates (SQL-AND, PREREG_CV.md addendum 4) printed first. BFCL categories: non-live / live.
usage: python analyze_tcrl.py [tag]   (default q8btcc1)"""
import contextlib, io, os, random, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
with contextlib.redirect_stdout(io.StringIO()):   # analyze_dv's / analyze_ho3's imports print word-problem tables
    from analyze_cvpeer import compare
    from analyze_dv import default, quick
    from analyze_ho3 import ci
    import analyze_hopa  # noqa: F401 (default() imports it lazily)


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else "q8btcc1"
    D, N0, N1, X = default("tc", "q8b"), quick("tc", "q8b"), quick("tc", tag), quick("tc", "q35")
    ids, keys, Q, pol, pred, _, _ = compare(f"TC-RL, Qwen3-8B, BFCL (quick calls {tag}), peer Qwen3.5-9B", D, N0, N1, X, ("base", "C1tc"))
    acc = {name: {} for name in ("base", "C1tc")}
    for name, N in (("base", N0), ("C1tc", N1)):
        for i, s in keys:
            acc[name].setdefault(i, []).append(float(N[s][i][1]))
    d1 = ci({i: sum(acc["C1tc"][i]) / 3 - sum(acc["base"][i]) / 3 for i in ids})
    for name in ("base", "C1tc"):
        for part, sel in (("non-live", lambda i: not i.startswith("live")), ("live", lambda i: i.startswith("live"))):
            qs = [i for i in ids if sel(i)]
            print(f"  quick calls right, {name}, {part}: {100 * sum(sum(acc[name][i]) / 3 for i in qs) / len(qs):.1f}% ({len(qs)} items)")
    u2 = ci({i: Q["N(C1tc)->peer->default"][i][1] - Q["default"][i][1] for i in ids})
    u3 = ci({i: Q["N(C1tc)->peer->default"][i][1] - Q["N(base)->peer->default"][i][1] for i in ids})
    p = pred["C1tc"] - pred["base"]
    print(f"  quick calls right, C1tc - base: {d1[0]:+.1f} [{d1[1]:+.1f}, {d1[2]:+.1f}] points")
    print(f"*** TCRL-P1 {d1[1] > 0}; TCRL-P2 {u2[1] > 0} ({u2[0]:+.2f} [{u2[1]:+.2f}, {u2[2]:+.2f}]); TCRL-P3 {u3[1] > 0} ({u3[0]:+.2f} "
          f"[{u3[1]:+.2f}, {u3[2]:+.2f}]); TCRL-P3 theory (predicted {p:+.2f} inside the P3 interval) {u3[1] <= p <= u3[2]}")


if __name__ == "__main__":
    main()
