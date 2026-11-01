"""MT-V (docs/prereg/PREREG_MT.md, addendum MT-V): arm V (per-turn vote over sandboxed rollouts) against always thinking (T) and the
other arms, per model: accuracy, output tokens, utility (100 x right - 0.5 x ktokens), paired 95% intervals over items (seed means);
the share of turns committed without thinking (the quick or the peer's turn), the fallback rate, rollouts per turn; MT-V1 / V2.
usage: python3.11 poc/analyze_mtv.py [tags]   (after grade_mt.py <tag> V)"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_ho3 import ci  # noqa: E402
from analyze_mt import load  # noqa: E402


def main():
    v1 = v2 = 0
    tags = sys.argv[1:] or ["q8b", "q35"]
    for tag in tags:
        D = {(a, s): load(tag, a, s) for a in ("V", "T", "N", "F") for s in (1, 2, 3)}
        if any(D[("V", s)] is None for s in (1, 2, 3)):
            print(f"=== {tag}: V rows or grades missing"); continue
        ids = sorted(set.intersection(*(set(D[(a, s)]) for a in ("V", "T") for s in (1, 2, 3))))
        u = lambda r: 100 * float(r["ok"]) - 0.5 * r["tok"] / 1000
        per = {a: {i: sum(u(D[(a, s)][i]) for s in (1, 2, 3)) / 3 for i in ids} for a in ("V", "T")}
        acc = {a: {i: sum(100 * float(D[(a, s)][i]["ok"]) for s in (1, 2, 3)) / 3 for i in ids} for a in ("V", "T")}
        tok = {a: sum(D[(a, s)][i]["tok"] for i in ids for s in (1, 2, 3)) / (3 * len(ids)) / 1000 for a in ("V", "T")}
        du = ci({i: (per["V"][i] - per["T"][i]) / 100 for i in ids})
        da = ci({i: (acc["V"][i] - acc["T"][i]) / 100 for i in ids})
        votes = [v for s in (1, 2, 3) for i in ids for v in D[("V", s)][i].get("votes", [])]
        quick = sum(v["commit"] in (0, 1) for v in votes) / max(1, len(votes))
        nothink = sum(set(v["calls"]) <= {0, 1} for v in votes) / max(1, len(votes))   # no thinking rollout run at that turn
        fb = sum(v["fallback"] for v in votes) / max(1, len(votes))
        roll = sum(len(v["calls"]) for v in votes) / max(1, len(votes))
        print(f"=== {tag} ({len(ids)} items x 3 seeds): V {sum(acc['V'].values()) / len(ids):.1f}% @ {tok['V']:.2f}k; "
              f"T {sum(acc['T'].values()) / len(ids):.1f}% @ {tok['T']:.2f}k")
        print(f"    V - T utility {du[0]:+.2f} [{du[1]:+.2f}, {du[2]:+.2f}]; accuracy {da[0]:+.2f} [{da[1]:+.2f}, {da[2]:+.2f}]; "
              f"turns committing a quick rollout {100 * quick:.1f}%, with no thinking rollout {100 * nothink:.1f}%; rollouts per turn {roll:.2f}; fallback {100 * fb:.1f}%")
        v1 += du[1] > 0; v2 += da[1] > 0
    print(f"*** MT-V1 (utility, both models): {v1} / {len(tags)} -> {'holds' if v1 == len(tags) else 'refuted'}; "
          f"MT-V2 (accuracy): {v2} / {len(tags)} -> {'holds' if v2 == len(tags) else 'refuted'}")


if __name__ == "__main__":
    main()
