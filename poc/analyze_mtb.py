"""MT-B (docs/prereg/PREREG_MT.md, addendum MT-B): the information limit of a turn's signals at turn 0. Per item-seed the four turn-0
calls (N, the peer's N, T, next-seed T) from `mt_peer0.py --dump` (end-state groups as answers, "no visible failure" as the check);
the supervised planner of PREREG_LCM addendum B (lcm_bound.Supervised; cross-fitted over halves of the items, crc32(item) mod 2)
against always thinking (T), T with a retry on a visible failure (T->T), the rollback rule (N; on a visible failure T) and the peer rule
(N; when the end states differ T); utility 100 x right - 0.5 x ktokens of turn 0; paired 95% intervals over items (seed means).
usage: python3.11 poc/analyze_mtb.py [tags]"""
import json, os, sys, zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_ho3 import ci  # noqa: E402
from lcm_bound import Supervised, full  # noqa: E402

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "tc")
LAM = 0.5
u = lambda ok, t: 100 * float(ok) - LAM * t / 1000


def fixed(name, c):
    N, P, T, T2 = c
    if name == "T":
        return T[2], T[3]
    if name == "T->T":
        return (T[2], T[3]) if T[1] else (T2[2], T[3] + T2[3])
    if name == "N":
        return N[2], N[3]
    if name == "rollback":
        return (N[2], N[3]) if N[1] else (T[2], N[3] + T[3])
    if name == "peer":
        return (N[2], N[3] + P[3]) if N[0] == P[0] else (T[2], N[3] + P[3] + T[3])


def main():
    out = {}
    for tag in sys.argv[1:] or ["q8b", "q14a", "q35"]:
        D = {k: [tuple(x) for x in v] for k, v in json.load(open(f"{RES}/mt_turn0_{tag}.json")).items()}
        items = sorted({k.rsplit("/", 1)[0] for k in D})
        half = {h: [i for i in items if zlib.crc32(i.encode()) % 2 == h] for h in (0, 1)}
        U = {k: {} for k in ("planner", "T", "T->T", "N", "rollback", "peer")}
        A = {k: {} for k in U}; K = {k: {} for k in U}
        for h in (0, 1):
            rows = [full(D[f"{i}/{s}"]) for i in half[h] for s in (1, 2, 3)]
            tok = [sum(D[f"{i}/{s}"][j][3] for i in half[h] for s in (1, 2, 3)) / (3 * len(half[h])) for j in range(4)]
            S = Supervised(rows, tok)
            for i in half[1 - h]:
                for k in U:
                    vals = []
                    for s in (1, 2, 3):
                        c = D[f"{i}/{s}"]
                        if k == "planner":
                            ok, t, seen = S.run(c)
                            if not seen:
                                ok, t = fixed("T", c)
                        else:
                            ok, t = fixed(k, c)
                        vals.append((ok, t))
                    U[k][i] = sum(u(o, t) for o, t in vals) / 3
                    A[k][i] = 100 * sum(o for o, _ in vals) / 3; K[k][i] = sum(t for _, t in vals) / 3
        n = len(items)
        line = "; ".join(f"{k} {sum(A[k].values()) / n:.1f}% @ {sum(K[k].values()) / n / 1000:.2f}k" for k in U)
        d = ci({i: (U["planner"][i] - U["T"][i]) / 100 for i in items})
        print(f"=== {tag} ({n} items x 3 seeds, turn 0): {line}")
        print(f"    planner - T: {d[0]:+.2f} [{d[1]:+.2f}, {d[2]:+.2f}]; T->T - T: "
              + "{:+.2f} [{:+.2f}, {:+.2f}]".format(*ci({i: (U['T->T'][i] - U['T'][i]) / 100 for i in items})))
        out[tag] = d
    held = sum(v[1] > 0 for v in out.values())
    print(f"*** MT-B1: planner - T lower bound > 0 in {held} of {len(out)} models (needs 2): {'holds' if held >= 2 else 'refuted'}")


if __name__ == "__main__":
    main()
