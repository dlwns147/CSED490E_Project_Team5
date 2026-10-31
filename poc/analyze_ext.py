"""EXT (docs/prereg/PREREG_EXT.md; offline on stored rows + poc/score_conf.py's scores): the peer check of the cascade against the
in-model confidence gate (2404.10136) and against agreement alone (ABC, 2407.02348). 12 cells: Qwen3-8B / Qwen3-14B-AWQ / Qwen3.5-9B
as A with HO-PA's peers on BIRD dev, the fresh BIRD-train questions and BFCL non-live / live; items, check, "same answer" and the
default SB->T->T as poc/analyze_breakeven.py. c = mean log-prob over A's answer tokens and the end token (secondary: 10% quantile,
minimum). Gates (rejection -> SB->T->T): PEER; CONF@r (top share r of passing c, r = PEER's accept share of passing N); CONF* / AND*
(threshold tuned on the other half of the questions, crc32(id) mod 2); AND20 (PEER and c above the 20% quantile of agreeing c); ABC
(same answer, no check, the peer always run). Gate - PEER in utility (100 x right - 0.5 x ktokens), paired 95% intervals over
questions (seed means); AUROC of c among passing N and among agreeing passing N; c's TPR at the peer's FPR; accept rates in the
strata RW (N right, default wrong) and WR (N wrong, default right).
usage: python3.11 poc/analyze_ext.py"""
import contextlib, io, json, os, sys, zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_ho3 import ci  # noqa: E402
from run_nlopt import _rows  # noqa: E402
with contextlib.redirect_stdout(io.StringIO()):
    import analyze_hopa as H  # noqa: E402
    import analyze_sqlpa as Q  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONF = os.environ.get("EXT_CONF") or f"{ROOT}/results/conf"   # another directory of scores: the dry run on random scores
PEER = {"q8b": "q35", "q14a": "q35", "q35": "q8b"}
SCORES = ("mean", "q10", "min")


def conf(kind, tag):
    """{seed: {id: (mean, q10, min)}} over the answer tokens and the end token, or None"""
    out = {}
    for s in (1, 2, 3):
        p = f"{CONF}/{kind}_{tag}_s{s}.jsonl"
        if not os.path.exists(p):
            return None
        out[s] = {}
        for r in _rows(p):
            v = sorted(r["lp"] + [r["end"]])
            out[s][r["id"]] = (sum(v) / len(v), v[int(0.1 * (len(v) - 1))], v[0])
    return out


def sql_cells():
    for dev in (True, False):
        tag = {m: m if dev else m + "pa" for m in PEER}
        for A, P in PEER.items():
            GA, GP, C = Q.grades(tag[A]), Q.grades(tag[P]), conf("sql" if dev else "sqltr", tag[A])
            if not (GA and GP and C):
                yield f"sql{'dev' if dev else 'tr'} {A}", None; continue
            KA, KP, items = Q.ntok(tag[A]), Q.ntok(tag[P]), []
            for (i, s), v in Q.base(tag[A]).items():
                n, o = GA[s][i]["N"], GP[s].get(i, {}).get("N", {})
                ps = n["chk"] == "pass"
                items.append(dict(id=i, s=s, ps=ps, ok=bool(n["ok"]), tok=KA[s][i], ptok=KP[s].get(i, 0),
                                  agree=ps and o.get("chk") == "pass" and o.get("h") == n["h"],
                                  abc=n.get("h") is not None and o.get("h") is not None and o.get("h") == n["h"],
                                  dok=bool(v["SB->T->T"][0]), dtok=v["SB->T->T"][1], c=C[s].get(i)))
            yield f"sql{'dev' if dev else 'tr'} {A}", items


def tc_cells():
    for split in ("non-live", "live"):
        for A, P in PEER.items():
            RA, RP, C = H.tc_rows(A, split), H.tc_rows(P, split), conf("tc", A)
            if not (RA and RP and C):
                yield f"tc {split} {A}", None; continue
            items = []
            for (i, s), r in H.policies(RA, {"p": RP}, H.same_tc).items():
                f, p = RA["formx"][s][i], RP["formx"][s][i]
                has = lambda x: json.loads(x[3]) not in ("", "[]", None)
                items.append(dict(id=i, s=s, ps=bool(f[0]), ok=bool(f[1]), tok=f[2], ptok=p[2], agree=bool(H.same_tc(f, p)),
                                  abc=has(f) and has(p) and f[3] == p[3], dok=bool(r["SB->T->T"][0]), dtok=r["SB->T->T"][1],
                                  c=C[s].get(i)))
            yield f"tc {split} {A}", items


def outcome(x, gate, k=0, tau=None):
    """(right, tokens) of one problem-seed under a gate; k = index of the score"""
    c = x["c"][k] if x["c"] else float("-inf")
    d = (x["dok"], x["tok"] + x["dtok"])
    if gate == "ABC":
        return (x["ok"], x["tok"] + x["ptok"]) if x["abc"] else (x["dok"], x["tok"] + x["ptok"] + x["dtok"])
    if not x["ps"]:
        return d
    if gate == "CONF":
        return (x["ok"], x["tok"]) if c >= tau else d
    keep = x["agree"] and (gate == "PEER" or c >= tau)
    return (x["ok"], x["tok"] + x["ptok"]) if keep else (x["dok"], x["tok"] + x["ptok"] + x["dtok"])


def util(rows):
    """{id: mean utility as a fraction (ci() prints points)} over (x, (right, tokens))"""
    acc = {}
    for x, (ok, t) in rows:
        acc.setdefault(x["id"], []).append(float(ok) - H.LAM / 100 * t / 1000)
    return {i: sum(v) / len(v) for i, v in acc.items()}


def q(v, p):
    v = sorted(v)
    return v[min(len(v) - 1, max(0, int(p * len(v))))] if v else float("-inf")


def tuned(items, gate, k, pool):
    """two-fold: the threshold (a 0..100% quantile of pool(fold)'s c) that maximises utility on one half, applied to the other"""
    out = []
    for f in (0, 1):
        tr = [x for x in items if zlib.crc32(x["id"].encode()) % 2 == f]
        te = [x for x in items if zlib.crc32(x["id"].encode()) % 2 != f]
        vals = [x["c"][k] for x in pool(tr)]
        grid = [q(vals, p / 20) for p in range(21)] + [float("inf")]
        best = max(grid, key=lambda t: sum(util([(x, outcome(x, gate, k, t)) for x in tr]).values()))
        out += [(x, outcome(x, gate, k, best)) for x in te]
    return util(out)


def auroc(pos, neg):
    if not pos or not neg:
        return float("nan")
    allv = sorted([(v, 1) for v in pos] + [(v, 0) for v in neg])
    i, s = 0, 0.0
    while i < len(allv):   # mid-ranks for ties
        j = i
        while j < len(allv) and allv[j][0] == allv[i][0]:
            j += 1
        mid = (i + j + 1) / 2
        s += mid * sum(1 for t in allv[i:j] if t[1])
        i = j
    return (s - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def main():
    V = {k: [] for k in ("P1a", "P1b", "P2", "P3", "P4a", "P4b", "P5", "P6", "abc+", "abc-", "conf*+", "confs+")}
    for name, items in list(sql_cells()) + list(tc_cells()):
        if items is None:
            print(f"=== {name}: missing grades, rows or scores"); continue
        miss = sum(1 for x in items if x["ps"] and not x["c"])
        for x in items:
            if not x["c"]:
                x["c"] = (float("-inf"),) * 3
        P = [x for x in items if x["ps"]]
        Ag = [x for x in P if x["agree"]]
        r = len(Ag) / max(1, len(P))
        base = util([(x, outcome(x, "PEER")) for x in items])
        nq = len(base)
        print(f"=== {name}: {nq} questions, {len(items)} problem-seeds; passing {100 * len(P) / len(items):.0f}%, PEER accepts {100 * r:.0f}% "
              f"of passing; passing without a score {miss}")
        RW = [x for x in P if x["ok"] and not x["dok"]]; WR = [x for x in P if not x["ok"] and x["dok"]]
        res = {}
        for k, sc in enumerate(SCORES):
            right, wrong = [x["c"][k] for x in P if x["ok"]], [x["c"][k] for x in P if not x["ok"]]
            a, ac = auroc(right, wrong), auroc([x["c"][k] for x in Ag if x["ok"]], [x["c"][k] for x in Ag if not x["ok"]])
            tpr_p = sum(x["agree"] for x in P if x["ok"]) / max(1, len(right)); fpr_p = sum(x["agree"] for x in P if not x["ok"]) / max(1, len(wrong))
            th = q(wrong, 1 - fpr_p); tpr_c = sum(v >= th for v in right) / max(1, len(right))
            tau = q([x["c"][k] for x in P], 1 - r)
            g = {"CONF@r": util([(x, outcome(x, "CONF", k, tau)) for x in items]),
                 "CONF*": tuned(items, "CONF", k, lambda xs: [x for x in xs if x["ps"]]),
                 "AND20": util([(x, outcome(x, "AND", k, q([y["c"][k] for y in Ag], 0.2))) for x in items]),
                 "AND*": tuned(items, "AND", k, lambda xs: [x for x in xs if x["ps"] and x["agree"]])}
            print(f"  [{sc}] AUROC passing {a:.3f}, agreeing {ac:.3f}; peer TPR {100 * tpr_p:.0f}% FPR {100 * fpr_p:.0f}%, c's TPR at that FPR "
                  f"{100 * tpr_c:.0f}%")
            ar = lambda S, f: 100 * sum(1 for x in S if f(x)) / max(1, len(S))
            G = {gname: ci({i: u[i] - base[i] for i in base}) for gname, u in g.items()}
            for gname, d in G.items():
                print(f"    {gname:6} - PEER {d[0]:+.2f} [{d[1]:+.2f}, {d[2]:+.2f}]")
            print(f"    accept RW / WR: PEER {ar(RW, lambda x: x['agree']):.0f}% / {ar(WR, lambda x: x['agree']):.0f}%, CONF@r "
                  f"{ar(RW, lambda x: x['c'][k] >= tau):.0f}% / {ar(WR, lambda x: x['c'][k] >= tau):.0f}%")
            res[sc] = (a, ac, tpr_c < tpr_p, G)
        abc = util([(x, outcome(x, "ABC")) for x in items])
        d = ci({i: abc[i] - base[i] for i in base})
        print(f"  ABC - PEER {d[0]:+.2f} [{d[1]:+.2f}, {d[2]:+.2f}]")
        a, ac, below, G = res["mean"]
        V["P1a"].append(0.60 <= a <= 0.82); V["P1b"].append(below); V["P3"].append(ac < a)
        V["P2"].append(G["CONF@r"][2] < 0)   # PEER - CONF@r lower bound > 0  <=>  CONF@r - PEER upper bound < 0
        V["conf*+"].append(G["CONF*"][1] > 0)
        V["P4a"].append(G["AND*"][1] > 0); V["P4b"].append(G["AND20"][1] > 0)
        V["P5"].append(G["CONF*"][1] < 0.5)   # PEER - CONF* lower bound > -0.5  <=>  CONF* - PEER upper bound < 0.5
        V["confs+"].append(G["CONF@r"][1] > 0)
        V["P6"].append(abs(d[0]) <= 0.3); V["abc+"].append(d[1] > 0); V["abc-"].append(d[2] < 0)
    n = len(V["P1a"])
    print(f"*** over {n} cells (score: mean log-prob)")
    print(f"EXT-P1 AUROC in [0.60, 0.82]: {sum(V['P1a'])} / {n}; peer above c's ROC: {sum(V['P1b'])} / {n} -> "
          f"{'holds' if sum(V['P1a']) >= 9 and sum(V['P1b']) >= 9 else 'refuted'} (needs 9 and 9)")
    print(f"EXT-P2 PEER - CONF@r lower bound > 0: {sum(V['P2'])} / {n}; CONF@r significantly better: {sum(V['confs+'])} -> "
          f"{'holds' if sum(V['P2']) >= 6 and sum(V['confs+']) == 0 else 'refuted'}")
    print(f"EXT-P3 conditional AUROC below unconditional: {sum(V['P3'])} / {n} -> {'holds' if sum(V['P3']) >= 9 else 'refuted'}")
    print(f"EXT-P4 AND* - PEER lower bound > 0: {sum(V['P4a'])}; AND20: {sum(V['P4b'])} -> "
          f"{'holds' if sum(V['P4a']) <= 2 and sum(V['P4b']) <= 2 else 'refuted'}")
    print(f"EXT-P5 PEER - CONF* lower bound > -0.5: {sum(V['P5'])} / {n} -> {'holds' if sum(V['P5']) >= 8 else 'refuted'}; "
          f"CONF* significantly better: {sum(V['conf*+'])}")
    print(f"decision: CONF@r better in {sum(V['confs+'])} (>= 4: replace the peer), CONF* better in {sum(V['conf*+'])} (>= 5), AND20 "
          f"better in {sum(V['P4b'])} (>= 4: add the filter), AND* in {sum(V['P4a'])} (>= 4: a labelled variant)")
    print(f"EXT-P6 |ABC - PEER| <= 0.3: {sum(V['P6'])} / {n} -> {'holds' if sum(V['P6']) >= 9 else 'refuted'}; ABC better {sum(V['abc+'])}, "
          f"worse {sum(V['abc-'])}")


if __name__ == "__main__":
    main()
