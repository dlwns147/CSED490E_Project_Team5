"""MT-V (docs/prereg/PREREG_MT.md, addendum MT-V): the per-turn commit policy for run_mt.py's arm V, learned from the turn-0 dumps
(mt_peer0.py --dump) of one half of the items (crc32(item) mod 2 = h, all their labels): MT-B's supervised planner over the four
turn rollouts (N, the peer's N, T, T at the next seed), solved for every observation pattern seen on that half; run_mt.py applies the
policy learned on one half to the items of the other.
usage: python3.11 poc/mt_policy.py <tag>   -> results/tc/mt_policy_<tag>_fit<h>.json for h = 0, 1 {repr(pattern): [kind, arg]}"""
import json, os, sys, zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lcm_bound import Supervised, full  # noqa: E402

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "tc")


def main():
    tag = sys.argv[1]
    D = {k: [tuple(x) for x in v] for k, v in json.load(open(f"{RES}/mt_turn0_{tag}.json")).items()}
    items = sorted({k.rsplit("/", 1)[0] for k in D})
    for h in (0, 1):
        fit = [i for i in items if zlib.crc32(i.encode()) % 2 == h]
        rows = [full(D[f"{i}/{s}"]) for i in fit for s in (1, 2, 3)]
        tok = [sum(D[f"{i}/{s}"][j][3] for i in fit for s in (1, 2, 3)) / (3 * len(fit)) for j in range(4)]
        S = Supervised(rows, tok)
        for pat in list(S.n):
            S.value(pat)
        pol = {repr(p): list(a) for p, a in S.act.items()}
        json.dump({"tok": tok, "value": S.value((None,) * 4), "policy": pol}, open(f"{RES}/mt_policy_{tag}_fit{h}.json", "w"))
        print(f"{tag} fitted on half {h} ({len(fit)} items): {len(pol)} patterns, planned turn-0 utility {100 * S.value((None,) * 4):+.2f}")


if __name__ == "__main__":
    main()
