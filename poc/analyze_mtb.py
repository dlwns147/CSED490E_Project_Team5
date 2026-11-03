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


def main_sel():
    """addendum MT-SEL (--sel <verifier trained on half 0>,<verifier trained on half 1> [--ref <name>]): at turn 0, a verifier choosing
    among the rollouts of N, the peer's N and T (SEL3; with the next seed's T too, SEL4), and the gate (N kept when its score clears tau,
    else T), against always thinking (T). Rows: results/conf/mt_sel_rows.jsonl (mt_peer0.py --sel-build; each rollout graded on its
    own). A half's items are scored by the verifier trained on the other half; the selector (lcm_shift.sel_fit_cl: log prior by the roles
    that produced a rollout + beta_CL z) and tau are fitted per model on one half and applied to the other. --ref: a verifier trained on
    neither half (the same cross-fitted selector). MT_SEL_SYNTH=1: random scores (the dry run). (MT-SEL-P1..P4)"""
    import random
    from collections import Counter
    import lcm_shift as L
    a = sys.argv[sys.argv.index("--sel") + 1].split(",")
    ref = sys.argv[sys.argv.index("--ref") + 1] if "--ref" in sys.argv else None
    C = os.path.join(os.path.dirname(RES), "conf")
    load = lambda nm: {r["h"]: r["s"] for r in map(json.loads, open(f"{C}/sel_scores_{nm}.jsonl"))} if os.path.exists(f"{C}/sel_scores_{nm}.jsonl") else {}
    synth = os.environ.get("MT_SEL_SYNTH") == "1"
    V = {0: load(a[1]), 1: load(a[0])}   # half h's items are scored by the verifier trained on the other half
    Rf = load(ref) if ref else None
    rows = [json.loads(l) for l in open(f"{C}/mt_sel_rows.jsonl")]
    f = lambda v: f"{v[0]:+.2f} [{v[1]:+.2f}, {v[2]:+.2f}]"
    out, outr, auc = {}, {}, {}

    def sc(S, i, t):
        if synth:
            return random.Random(L.rv_key("tc", "mt", i, "sel", t)).gauss(0, 2)
        return S.get(L.rv_key("tc", "mt", i, "sel", t))

    def sets(rs, roles, S):
        X, miss = [], 0
        for r in rs:
            g = {}
            for k in roles:
                g.setdefault(r["roll"][k][0], []).append(k)
            Cc = []
            for t, ks in g.items():
                v = sc(S(r) if callable(S) else S, r["id"], t)
                if v is None:
                    Cc = None; break
                Cc.append({"r": r["roll"][ks[0]][1], "calls": tuple(sorted(ks)), "s": v, "t": t})
            if Cc is None:
                miss += 1; continue
            X.append(((r["id"], r["seed"]), r["seed"], Cc, r["roll"]["T"][1]))
        return X, miss
    for m in ("q8b", "q14a", "q35"):
        R = [r for r in rows if r["model"] == m]
        ids = sorted({r["id"] for r in R})
        U = {k: Counter() for k in ("T", "N", "SEL3", "SEL4", "GATE", "alone3", "ref3")}
        A, K, miss, unseen = {k: Counter() for k in U}, {k: Counter() for k in U}, Counter(), Counter()
        tk = lambda r, ks: sum(r["roll"][k][2] for k in ks)
        z0 = lambda X: [(i, s, [dict(c, s=0.0) for c in Cc], dr) for i, s, Cc, dr in X]
        aucs = {}
        for h in (0, 1):
            fitR, testR = [r for r in R if r["half"] != h], [r for r in R if r["half"] == h]
            Sv = lambda r: V[r["half"]]
            for nm, roles, S in (("SEL3", ("N", "P", "T"), Sv), ("SEL4", ("N", "P", "T", "T2"), Sv), ("ref3", ("N", "P", "T"), Rf)):
                if S is None:
                    continue
                fit, _ = sets(fitR, roles, S)
                test, ms = sets(testR, roles, S)
                miss[nm] += ms
                choose, beta = L.sel_fit_cl(z0(fit), fit)
                ch = {x[0]: choose(x) for x in test}
                if nm == "SEL3":
                    aucs.update({(x[0], h): x for x in test})
                for r in testR:
                    c = ch.get((r["id"], r["seed"]))
                    unseen[nm] += c is None
                    ok = c["r"] if c else r["roll"]["T"][1]
                    t = tk(r, roles)
                    U[nm][r["id"]] += u(ok, t) / 3; A[nm][r["id"]] += 100 * ok / 3; K[nm][r["id"]] += t / 3
                if nm == "SEL3":
                    byk = {(y["id"], y["seed"]): y for y in testR}
                    for x in test:
                        cs, r = max(x[2], key=lambda c: c["s"]), byk[x[0]]
                        U["alone3"][r["id"]] += u(cs["r"], tk(r, roles)) / 3
            # the gate: N's own score against tau (fitted on the other half for the highest utility)
            gs = lambda rs: [(sc(V[r["half"]], r["id"], r["roll"]["N"][0]), r) for r in rs]
            fg = [x for x in gs(fitR) if x[0] is not None]
            gu = lambda tau, X: sum(u(r["roll"]["N"][1], r["roll"]["N"][2]) if v >= tau else u(r["roll"]["T"][1], r["roll"]["N"][2] + r["roll"]["T"][2])
                                    for v, r in X)
            qs = sorted(v for v, _ in fg)
            tau = max([qs[int(q * (len(qs) - 1) / 40)] for q in range(41)] + [float("inf")], key=lambda t: gu(t, fg))
            for v, r in gs(testR):
                keep = v is not None and v >= tau
                ok, t = (r["roll"]["N"][1], r["roll"]["N"][2]) if keep else (r["roll"]["T"][1], r["roll"]["N"][2] + r["roll"]["T"][2])
                U["GATE"][r["id"]] += u(ok, t) / 3; A["GATE"][r["id"]] += 100 * ok / 3; K["GATE"][r["id"]] += t / 3
            for r in testR:
                for k in ("T", "N"):
                    ok, t = r["roll"][k][1], r["roll"][k][2]
                    U[k][r["id"]] += u(ok, t) / 3; A[k][r["id"]] += 100 * ok / 3; K[k][r["id"]] += t / 3
        n = len(ids)
        d = lambda x: ci({i: (U[x][i] - U["T"][i]) / 100 for i in ids})
        out[m] = {k: d(k) for k in ("SEL3", "SEL4", "GATE")}
        out[m]["alone3"] = ci({i: (U["alone3"][i] - U["SEL3"][i]) / 100 for i in ids})
        if Rf is not None:
            outr[m] = ci({i: (U["SEL3"][i] - U["ref3"][i]) / 100 for i in ids})
        sa = L.sel_auc([(k[0][0], k[0][1], x[2], x[3]) for k, x in aucs.items()])
        auc[m] = ci(sa)
        print(f"=== MT-SEL {m} ({n} items x 3 seeds, turn 0; missing scores {dict(miss)}, unseen structures keep T {dict(unseen)}): "
              + "; ".join(f"{k} {sum(A[k].values()) / n:.1f}% @ {sum(K[k].values()) / n / 1000:.2f}k" for k in ("T", "N", "SEL3", "SEL4", "GATE")
                          + (("ref3",) if Rf is not None else ())), flush=True)
        print(f"    within-set AUROC (SEL3 sets) {auc[m][0] / 100:.3f} [{auc[m][1] / 100:.3f}, {auc[m][2] / 100:.3f}]; SEL3 - T {f(out[m]['SEL3'])}; "
              f"SEL4 - T {f(out[m]['SEL4'])}; GATE - T {f(out[m]['GATE'])}; score alone - fitted selector (SEL3 sets) {f(out[m]['alone3'])}"
              + (f"; SEL3 trained - SEL3 {ref} {f(outr[m])}" if Rf is not None else ""), flush=True)
    up = sum(v["SEL3"][1] > 0 for v in out.values())
    print(f"*** MT-SEL-P1 (SEL3 - T utility at turn 0, lower bound > 0 in >= 2 of 3 models): {up} of 3 -> {'holds' if up >= 2 else 'refuted'}")
    up = sum(v[0] / 100 >= 0.75 for v in auc.values())
    print(f"*** MT-SEL-P2 (within-set AUROC >= 0.75 in >= 2 of 3 models): {[round(v[0] / 100, 3) for v in auc.values()]} -> "
          f"{'holds' if up >= 2 else 'refuted'}")
    up = sum(v["GATE"][1] > 0 for v in out.values())
    print(f"*** MT-SEL-P3 (GATE - T utility, lower bound > 0 in >= 2 of 3 models): {up} of 3 -> {'holds' if up >= 2 else 'refuted'}")
    if outr:
        up = sum(v[1] > 0 for v in outr.values())
        print(f"*** MT-SEL-P4 (SEL3 with the trained verifiers - with {ref}, lower bound > 0 in >= 2 of 3 models): {up} of 3 -> "
              f"{'holds' if up >= 2 else 'refuted'}")


if __name__ == "__main__":
    if "--sel" in sys.argv:
        main_sel()
    else:
        main()
