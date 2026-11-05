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


def env_half(path=None):
    """addendum MT-SEL-ENV: item -> 0 / 1 by environment group, None when it uses classes of both. The groups are the two-group split of
    BFCL's eight classes (GorillaFileSystem in group 0) that maximises the smaller group's count of items using only its classes.
    path: the items file (default $POC_DATA/bfcl/mt_items.jsonl; run_mt.py passes its DATA)."""
    PD = os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data")
    M = [json.loads(l) for l in open(path or f"{PD}/bfcl/mt_items.jsonl")]
    cls = sorted({c for r in M for c in r["involved_classes"]})
    size = lambda A: min(sum(set(r["involved_classes"]) <= A for r in M), sum(not set(r["involved_classes"]) & A for r in M))
    A = max(({c for k, c in enumerate(cls) if m >> k & 1} for m in range(1, 2 ** len(cls) - 1) if m & 1), key=size)
    return {r["id"]: 0 if set(r["involved_classes"]) <= A else 1 if not set(r["involved_classes"]) & A else None for r in M}


def main_sel_env_build():
    """addendum MT-SEL-ENV (--sel-env-build): the group item lists $POC_DATA/bfcl/mt_selenv_ids_h{0,1}.txt (training) and MT-SEL's turn-0
    requests of each group's items, results/conf/sel_req_mtenv_h{0,1}.jsonl (scoring by the verifier trained on the other group)."""
    PD = os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data")
    C = os.path.join(os.path.dirname(RES), "conf")
    eh = env_half()
    items = {json.loads(l)["id"] for l in open(f"{PD}/bfcl/mt_sel_items.jsonl")}
    for g in (0, 1):
        ids = sorted(i for i in items if eh.get(i) == g)
        open(f"{PD}/bfcl/mt_selenv_ids_h{g}.txt", "w").write("\n".join(ids) + "\n")
        n = 0
        with open(f"{C}/sel_req_mtenv_h{g}.jsonl", "w") as w:
            for h in (0, 1):
                for l in open(f"{C}/sel_req_mt_h{h}.jsonl"):
                    if eh.get(json.loads(l)["id"]) == g:
                        w.write(l); n += 1
        print(f"group {g}: {len(ids)} items with turn-0 sets, {n} requests", flush=True)
    print(f"dropped (both groups): {sum(eh.get(i) is None for i in items)} items")


def main_so_env_build():
    """addendum MT-SO-ENV (--so-env-build): per environment group g, mt_sel2's request ids of its items (turn 0 and the later turns,
    '<item>' / '<item>/t<k>'), $POC_DATA/bfcl/mt_soenv_ids_h<g>.txt (training), and their texts, results/conf/sel_req_mt2env_h<g>.jsonl
    (scored by the verifier trained on the other group)."""
    PD = os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data")
    C = os.path.join(os.path.dirname(RES), "conf")
    eh = env_half()
    ids = [json.loads(l)["id"] for l in open(f"{PD}/bfcl/mt_sel2_items.jsonl")]
    for g in (0, 1):
        mine = sorted(i for i in ids if eh.get(i.split("/")[0]) == g)
        open(f"{PD}/bfcl/mt_soenv_ids_h{g}.txt", "w").write("\n".join(mine) + "\n")
        n = 0
        with open(f"{C}/sel_req_mt2env_h{g}.jsonl", "w") as w:
            for h in (0, 1):
                for l in open(f"{C}/sel_req_mt2_h{h}.jsonl"):
                    if eh.get(json.loads(l)["id"].split("/")[0]) == g:
                        w.write(l); n += 1
        print(f"group {g}: {len(mine)} requests ({sum('/' not in i for i in mine)} at turn 0), {n} texts", flush=True)
    print(f"dropped (both groups): {sum(eh.get(i.split('/')[0]) is None for i in ids)} requests")


def main_pw_build():
    """addendum MT-PW (--pw-build): every ordered pair of distinct rollout texts in every pseudo-set (results/conf/mt_sel2_rows.jsonl) of
    half h -> results/conf/sel_req_mt2pw_h<h>.jsonl (task tc, sset mt2, kind pw; scored by the pairwise verifier trained on the other half)"""
    import lcm_shift as L
    C = os.path.join(os.path.dirname(RES), "conf")
    req = {0: {}, 1: {}}
    for r in map(json.loads, open(f"{C}/mt_sel2_rows.jsonl")):
        T = list(dict.fromkeys(r["roll"][k][0] for k in ("N", "P", "T")))
        for a in T:
            for b in T:
                if a != b:
                    h = L.rv_key("tc", "mt2", r["id"], "pw", [a, b])
                    req[r["half"]][h] = {"h": h, "task": "tc", "sset": "mt2", "id": r["id"], "kind": "pw", "text": a, "text2": b}
    for g in (0, 1):
        with open(f"{C}/sel_req_mt2pw_h{g}.jsonl", "w") as f:
            for v in req[g].values():
                f.write(json.dumps(v) + "\n")
        print(f"half {g}: {len(req[g])} ordered pairs", flush=True)


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
    # addendum MT-SEL-ENV: MT_SEL_SPLIT=env takes the halves by environment group (env_half), =same keeps the scenario halves; both drop
    # the items that use both groups, and dump the per-item utilities to results/tc/mtselenv_<split>.json (P3 when both exist)
    sp = os.environ.get("MT_SEL_SPLIT")
    if sp:
        eh = env_half()
        rows = [dict(r, half=eh[r["id"]]) if sp == "env" else r for r in rows if eh.get(r["id"]) is not None]
    dump = {}
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
        dump[m] = {i: {"SEL3": U["SEL3"][i], "T": U["T"][i]} for i in ids}
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
    if sp and not synth:
        json.dump(dump, open(f"{RES}/mtselenv_{sp}.json", "w"))
        other = f"{RES}/mtselenv_{'same' if sp == 'env' else 'env'}.json"
        if os.path.exists(other):
            E, S = (dump, json.load(open(other))) if sp == "env" else (json.load(open(other)), dump)
            p3 = ci({f"{m}/{i}": (E[m][i]["SEL3"] - S[m][i]["SEL3"]) / 100 for m in E for i in E[m] if i in S.get(m, {})})
            print(f"*** MT-SEL-ENV-P3 (SEL3 environment split - scenario split, same items, three models pooled): {f(p3)}")


def main_sel2():
    """addendum MT-SO (--sel2 <verifier trained on half 0>,<on half 1> [--ref <another pair>]): MT-SEL's choice among N, the peer's N and
    T on turn 0 and on the later turns' pseudo-sets (results/conf/mt_sel2_rows.jsonl, mt_peer0.py --sel-build2; scores of sset mt2), per
    turn (0, 1, 2, >= 3), cross-fitted as main_sel; writes the online arm's fit, results/tc/mt_so_fit_<model>.json: per test half h,
    lcm_shift.sel_fit_cl on the other half's sets of every turn pooled (scores of the verifier trained on h), keys '<structure>|<roles>'.
    MT-SO-P3: SEL3 - T on the later turns, the three models pooled, intervals over items; P4: SEL3 - SEL3 with --ref, same sets.
    MT_SEL_SYNTH=1: random scores (the dry run; the fit goes to mt_so_fit_<model>_synth.json).
    MT_SEL_SPLIT=env (addendum MT-SO-ENV): halves by environment group (env_half), the items of both groups dropped; the fit goes to
    results/tc/mt_soenv_fit_<model>.json."""
    import random
    from collections import Counter, defaultdict
    import lcm_shift as L
    a = sys.argv[sys.argv.index("--sel2") + 1].split(",")
    ref = sys.argv[sys.argv.index("--ref") + 1].split(",") if "--ref" in sys.argv else None
    C = os.path.join(os.path.dirname(RES), "conf")
    load = lambda nm: {r["h"]: r["s"] for r in map(json.loads, open(f"{C}/sel_scores_{nm}.jsonl"))} if os.path.exists(f"{C}/sel_scores_{nm}.jsonl") else {}
    synth = os.environ.get("MT_SEL_SYNTH") == "1"
    VS = {"SEL3": {0: load(a[1]), 1: load(a[0])}}   # half h's sets are scored by the verifier trained on the other half
    if ref:
        VS["ref3"] = {0: load(ref[1]), 1: load(ref[0])}
    pw = sys.argv[sys.argv.index("--pw") + 1].split(",") if "--pw" in sys.argv else None
    if pw:   # addendum MT-PW: the pairwise verifier (pairs of the other half's training); a rollout's score is set-dependent
        VS["PW"] = {0: dict(load(pw[1]), _pw=True), 1: dict(load(pw[0]), _pw=True)}
    rows = [json.loads(l) for l in open(f"{C}/mt_sel2_rows.jsonl")]
    f = lambda v: f"{v[0]:+.2f} [{v[1]:+.2f}, {v[2]:+.2f}]"
    tg = lambda k: str(k) if k < 3 else "3+"
    base = lambda i: i.split("/")[0]
    env = os.environ.get("MT_SEL_SPLIT") == "env"
    if env:
        eh = env_half()
        rows = [dict(r, half=eh[base(r["id"])]) for r in rows if eh.get(base(r["id"])) is not None]

    def sc(S, i, t, texts=()):
        if synth:
            return random.Random(L.rv_key("tc", "mt2", i, "sel", t)).gauss(0, 2)
        if S.get("_pw"):   # MT-PW: mean over the set's other texts b of (s(t, b) - s(b, t)) / 2; one distinct text scores 0
            xs = [(S.get(L.rv_key("tc", "mt2", i, "pw", [t, b])), S.get(L.rv_key("tc", "mt2", i, "pw", [b, t]))) for b in texts if b != t]
            if any(x is None or y is None for x, y in xs):
                return None
            return sum((x - y) / 2 for x, y in xs) / len(xs) if xs else 0.0
        return S.get(L.rv_key("tc", "mt2", i, "sel", t))

    def sets(rs, S):
        X, miss = [], 0
        for r in rs:
            g = {}
            for k in ("N", "P", "T"):
                g.setdefault(r["roll"][k][0], []).append(k)
            Cc = []
            for t, ks in g.items():
                v = sc(S[r["half"]], r["id"], t, list(g))
                if v is None:
                    Cc = None; break
                Cc.append({"r": r["roll"][ks[0]][1], "calls": tuple(sorted(ks)), "s": v, "t": t})
            if Cc is None:
                miss += 1; continue
            X.append(((r["id"], r["seed"]), r["seed"], Cc, r["roll"]["T"][1]))
        return X, miss
    z0 = lambda X: [(i, s, [dict(c, s=0.0) for c in Cc], dr) for i, s, Cc, dr in X]
    later = {nm: defaultdict(list) for nm in VS}; vsref = defaultdict(list)
    OK = {nm: {} for nm in VS}   # MT-PW: (model, request, seed) -> the chosen rollout right
    for m in ("q8b", "q14a", "q35"):
        R = [r for r in rows if r["model"] == m]
        D = {nm: defaultdict(lambda: defaultdict(list)) for nm in VS}   # name -> turn group -> item -> [utility - T's]
        A = {nm: defaultdict(list) for nm in VS}; At = defaultdict(list); AU = {nm: defaultdict(list) for nm in VS}
        U2 = {nm: {} for nm in VS}; miss = Counter(); unseen = Counter(); out = {}
        for h in (0, 1):
            fitR, testR = [r for r in R if r["half"] != h], [r for r in R if r["half"] == h]
            for nm, S in VS.items():
                fit, _ = sets(fitR, S)
                test, ms = sets(testR, S)
                miss[nm] += ms
                choose, beta = L.sel_fit_cl(z0(fit), fit)
                if nm == ("PW" if pw else "SEL3"):
                    st = choose.state
                    out[f"h{h}"] = {"cnt": {f"{k[0]!r}|{k[1]!r}": v for k, v in st["cnt"].items()},
                                    "rt": {f"{k[0]!r}|{k[1]!r}": v for k, v in st["rt"].items()}, "beta": st["beta"], "sd": st["sd"]}
                byk = {(r["id"], r["seed"]): r for r in testR}
                for x in test:
                    r = byk[x[0]]; c = choose(x); unseen[nm] += c is None
                    ok = c["r"] if c else r["roll"]["T"][1]
                    t = sum(r["roll"][k][2] for k in ("N", "P", "T"))
                    d = u(ok, t) - u(r["roll"]["T"][1], r["roll"]["T"][2])
                    D[nm][tg(r["turn"])][base(r["id"])].append(d)
                    A[nm][tg(r["turn"])].append(100 * ok)
                    U2[nm][(r["id"], r["seed"])] = u(ok, t)
                    OK[nm][(m, r["id"], r["seed"])] = ok
                    if nm == "SEL3":
                        At[tg(r["turn"])].append(100 * r["roll"]["T"][1])
                    if r["turn"] >= 1:
                        later[nm][base(r["id"])].append(d)
                for k, v in L.sel_auc([(x[0][0], x[0][1], x[2], x[3]) for x in test]).items():
                    AU[nm][tg(int(k.split("/t")[1]) if "/t" in k else 0)].append(v)
        if "ref3" in VS:
            for k, v in U2["SEL3"].items():
                if k in U2["ref3"] and "/t" in k[0]:
                    vsref[base(k[0])].append(v - U2["ref3"][k])
        json.dump(out, open(f"{RES}/mt_so{'pw' if pw else 'env' if env else ''}_fit_{m}{'_synth' if synth else ''}.json", "w"))
        print(f"=== MT-SO offline {m}: missing scores {dict(miss)}, unseen structures keep T {dict(unseen)}; fit written "
              f"(beta_CL h0 {out['h0']['beta']:.2f}, h1 {out['h1']['beta']:.2f})", flush=True)
        for g in ("0", "1", "2", "3+"):
            if not D["SEL3"][g]:
                continue
            per = lambda nm: ci({i: sum(v) / len(v) / 100 for i, v in D[nm][g].items()})
            au = lambda nm: sum(AU[nm][g]) / max(1, len(AU[nm][g]))
            print(f"    turn {g}: {len(A['SEL3'][g])} sets; T {sum(At[g]) / len(At[g]):.1f}%; "
                  + "; ".join(f"{nm} {sum(A[nm][g]) / len(A[nm][g]):.1f}%, AUROC {au(nm):.3f}, - T {f(per(nm))}" for nm in VS), flush=True)
    if pw:   # MT-PW-P1: per-turn choice accuracy, PW - SEL3, all turns, three models pooled, intervals over items
        dd = defaultdict(list)
        for k, v in OK["PW"].items():
            if k in OK["SEL3"]:
                dd[base(k[1])].append(float(v) - float(OK["SEL3"][k]))
        p1 = ci({i: sum(v) / len(v) for i, v in dd.items()})
        print(f"*** MT-PW-P1 (per-turn choice accuracy, PW - SEL3, pooled, lower bound > 0): {p1[0]:+.2f} [{p1[1]:+.2f}, "
              f"{p1[2]:+.2f}] points -> {'holds' if p1[1] > 0 else 'refuted'}")
    p3 = ci({i: sum(v) / len(v) / 100 for i, v in later["SEL3"].items()})
    print(f"*** MT-SO-P3 (SEL3 - T on the later turns' pseudo-sets, three models pooled, lower bound > 0): {f(p3)} -> "
          f"{'holds' if p3[1] > 0 else 'refuted'}")
    if vsref:
        p4 = ci({i: sum(v) / len(v) / 100 for i, v in vsref.items()})
        print(f"*** MT-SO-P4 (SEL3 with {','.join(a)} - with {','.join(ref)} on the same later-turn sets, lower bound > 0): {f(p4)} -> "
              f"{'holds' if p4[1] > 0 else 'refuted'}")


if __name__ == "__main__":
    if "--sel-env-build" in sys.argv:
        main_sel_env_build()
    elif "--so-env-build" in sys.argv:
        main_so_env_build()
    elif "--pw-build" in sys.argv:
        main_pw_build()
    elif "--sel2" in sys.argv:
        main_sel2()
    elif "--sel" in sys.argv:
        main_sel()
    else:
        main()
