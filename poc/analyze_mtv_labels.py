"""MT-V secondary (PREREG_MT): the turn-0 vote policy's need for labels. MT-B's supervised planner fitted on k labelled items of one
half (k = 10, 30, 100, all; 5 random draws), evaluated on the other half against always thinking (T); utility as MT-B.
usage: python3.11 poc/analyze_mtv_labels.py [tags]"""
import json, os, random, sys, zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_ho3 import ci  # noqa: E402
from analyze_mtb import RES, fixed, u  # noqa: E402
from lcm_bound import Supervised, full  # noqa: E402


def main():
    for tag in sys.argv[1:] or ["q8b", "q14a", "q35"]:
        D = {k: [tuple(x) for x in v] for k, v in json.load(open(f"{RES}/mt_turn0_{tag}.json")).items()}
        items = sorted({k.rsplit("/", 1)[0] for k in D})
        half = {h: [i for i in items if zlib.crc32(i.encode()) % 2 == h] for h in (0, 1)}
        line = []
        for k in (10, 30, 100, None):
            res = []
            for r in range(5 if k else 1):
                per = {}
                for h in (0, 1):
                    fit = half[h] if k is None else random.Random(100 * r + h).sample(half[h], k)
                    rows = [full(D[f"{i}/{s}"]) for i in fit for s in (1, 2, 3)]
                    tok = [sum(D[f"{i}/{s}"][j][3] for i in fit for s in (1, 2, 3)) / (3 * len(fit)) for j in range(4)]
                    S = Supervised(rows, tok)
                    for i in half[1 - h]:
                        v = 0.0
                        for s in (1, 2, 3):
                            c = D[f"{i}/{s}"]
                            ok, t, seen = S.run(c)
                            if not seen:
                                ok, t = fixed("T", c)
                            v += u(ok, t) - u(*fixed("T", c))
                        per[i] = v / 3 / 100
                res.append(ci(per))
            m = sum(x[0] for x in res) / len(res)
            line.append(f"k={k or 'all'}: {m:+.2f} (draws: " + ", ".join(f"{x[0]:+.1f} [{x[1]:+.1f}, {x[2]:+.1f}]" for x in res) + ")")
        print(f"=== {tag}: planner - T at turn 0, by labelled items")
        for l in line:
            print("    " + l)


if __name__ == "__main__":
    main()
