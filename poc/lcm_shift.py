"""LS (docs/prereg/PREREG_LCM.md, addendum LS): the derived policy on a new problem set with no label from it. The supervised planner
of addendum B needs the law of the calls' outcomes on the set it acts on, and with no labels that law is not identified (LCM: unanimity
cannot be told from a shared mistake). Label shift makes it identified: let c be a question-seed's correctness vector (which of the five
calls N, P, SB, T, retry T are right) and o its full observation (the calls' checks and which answers coincide). If P(o | c) is the same
on every problem set of a kind and only the class prior pi(c) moves (harder or easier sets), P(o | c) comes from the labelled
development sets, pi on the new set from its unlabelled observations by EM (Saerens, Latinne & Decaestecker 2002; identified when the
columns P(. | c) are linearly independent, Lipton et al. 2018), and the development rows reweighted by pi_new(c) / pi_dev(c) are a
sample of the new set's joint law; the planner is solved on them.
Per target cell, cross-fitted over halves (crc32(id) mod 2): pi and the calls' mean tokens are estimated on one half's unlabelled
question-seeds (all five calls run, no label read), the policies act on the other half, which is then scored with its labels.
Policies: LS (reweighted development rows); transfer (the development rows unweighted); the reference (B's planner on the target
half's own labels: needs the labels LS does without); pseudo-labels (B's planner on the target half with "right" = the answer of
T, else retry T, the most expensive call; label-free like C3PO, 2511.07396); fixed cascade, SB->T->T, T->T and P->SB->T->T. A
question-seed reaching a pattern its planner never saw is scored with the cascade's outcome (counted).
Addendum TR (--tr): the transfer planner fitted on every labelled SQL set so far (BIRD dev, the fresh BIRD questions, Spider test) with
those sets' mean tokens per call (nothing from the target), on Spider's dev split, never used before; the four generators.
Addendum TR-C1 (--tr-c1): the same with CV-1's trained quick query as N (FINAL's F5 cell). Addendum TRT (--trt): tool calls, the
policy fitted on BFCL and run on 3,549 held-out ToolACE requests, base and trained (TC-RL) quick calls. Addendum RV (--rv-build,
then score_conf.py rv on a GPU, then --rv): where the cascade falls back after a passing quick answer, choose among the distinct passing
answers of N, P and the fallback by their votes, ties by the channel (reviewer) score log p(question | answer). --dqs: Spider graded with a SQLite that
accepts double-quoted literals (FINAL's sensitivity).
usage: python3 lcm_shift.py [--tr | --tr-c1 [--explore]] [--dqs]   -> results/lcm_shift.log (results/lcm_tr*.log) lines,
results/lcm_shift/<cell>.json"""
import contextlib, io, json, math, os, sys, zlib
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lcm  # noqa: E402
from lcm_bound import Supervised, full  # noqa: E402

LAM = lcm.LAM
DEV_WORD = ("optibench", "bwor", "logior", "optmath")
PEER = {"q8b": "q35", "q14a": "q35", "q35": "q8b", "oss20": "q35"}   # the cascade's pre-registered peers on SQL and tool calls


def quiet(f, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return f(*a, **k)


def ob403(gen, peer):
    """OptiBench's other 403 problems (XPEER's fresh run): N's quick programs from the 605-problem rows, its think arms under <gen>ob"""
    import analyze_xpeer as X
    A = {"formx": X.formx(gen, "optibench"), "formxt": X.formx(gen + "ob", "optibench", "formxt"),
         "formxtb2000": X.formx(gen + "ob", "optibench", "formxtb2000")}
    return lcm.load_word(gen, peer, "optibench", rows=A)


def cells():
    """(name, development question dicts, target question dict, primary?)"""
    for g in ("q8b", "q14a"):   # primary: word problems, peer gpt-oss-20b, the two fresh sets of XPEER
        dev = [quiet(lcm.load, "word", g, "oss20", b) for b in DEV_WORD]
        yield f"word ob403 {g}<-oss20", dev, quiet(ob403, g, "oss20"), True
        yield f"word mamo {g}<-oss20", dev, quiet(lcm.load, "word", g, "oss20", "mamo"), True
    for g in ("q8b", "q14a", "q35", "oss20"):   # reported: tool calls one split from the other; SQL BIRD (dev + fresh) -> Spider
        p = PEER[g]
        nl, lv = quiet(lcm.load, "tc", g, p, "non-live"), quiet(lcm.load, "tc", g, p, "live")
        yield f"tc live {g}<-{p} (from non-live)", [nl], lv, False
        yield f"tc non-live {g}<-{p} (from live)", [lv], nl, False
        yield f"sql spider {g}<-{p} (from BIRD)", [quiet(lcm.load, "sql", g, p, "dev"), quiet(lcm.load, "sql", g, p, "fresh")], \
            quiet(lcm.load, "sql", g, p, "spider"), False


def cls(sc):
    return tuple(bool(c[2]) for c in sc)


def em_prior(dev_rows, target_obs, iters=2000):
    """pi on the target by EM with P(o | c) fixed from the development rows; returns pi, pi_dev, the share of target observations never
    seen in development (left out of EM), the rank of the matrix [P(o | c)] and the log-likelihood per observation (adapted, dev prior)"""
    nc, noc = Counter(), Counter()
    for o, c in dev_rows:
        nc[c] += 1; noc[(o, c)] += 1
    C = sorted(nc); N = sum(nc.values())
    pdev = {c: nc[c] / N for c in C}
    lik = {}
    for (o, c), k in noc.items():
        lik.setdefault(o, {})[c] = k / nc[c]
    seen = [o for o in target_obs if o in lik]
    pi = dict(pdev)
    for _ in range(iters):
        acc = Counter()
        for o in seen:
            z = sum(pi[c] * l for c, l in lik[o].items())
            if z <= 0:
                continue
            for c, l in lik[o].items():
                acc[c] += pi[c] * l / z
        new = {c: acc[c] / len(seen) for c in C}
        if max(abs(new[c] - pi[c]) for c in C) < 1e-10:
            pi = new
            break
        pi = new
    ll = lambda p: sum(math.log(max(1e-300, sum(p[c] * l for c, l in lik[o].items()))) for o in seen) / max(1, len(seen))
    rank = _rank([[lik[o].get(c, 0.0) for c in C] for o in lik])
    return pi, pdev, 1 - len(seen) / max(1, len(target_obs)), rank, len(C), ll(pi), ll(pdev)


def _rank(M, eps=1e-9):
    M = [r[:] for r in M]; rank = 0; cols = len(M[0]) if M else 0
    for j in range(cols):
        piv = max(range(rank, len(M)), key=lambda i: abs(M[i][j]), default=None)
        if piv is None or abs(M[piv][j]) < eps:
            continue
        M[rank], M[piv] = M[piv], M[rank]
        for i in range(len(M)):
            if i != rank and M[i][j]:
                f = M[i][j] / M[rank][j]
                M[i] = [a - f * b for a, b in zip(M[i], M[rank])]
        rank += 1
    return rank


def pseudo(sc):
    """label-free 'right' set: the group of T's answer if T passes, else the retry T's"""
    obs, _ = full(sc)
    j = 3 if sc[3][1] and sc[3][0] is not None else (4 if sc[4][1] and sc[4][0] is not None else None)
    return obs, frozenset() if j is None or obs[j][0] == "X" else frozenset({obs[j][0]})


def fixed(name, sc):
    if name == "P->SB->T->T":
        P = sc[1]; d = lcm.fixed("SB->T->T", sc)
        return (P[2], P[3]) if P[1] else (d[0], P[3] + d[1])
    return lcm.fixed(name, sc)


def run_cell(name, dev, tgt):
    from analyze_ho3 import ci
    u = lambda r, t: 100 * float(r) - LAM * t / 1000
    devsc = [lcm.seed_calls(q, s) for D in dev for q in D.values() for s in (1, 2, 3)]
    dev_rows = [full(sc) for sc in devsc]
    dev_oc = [(full(sc)[0], cls(sc)) for sc in devsc]
    ids = sorted(tgt); half = {h: [i for i in ids if zlib.crc32(i.encode()) % 2 == h] for h in (0, 1)}
    POL = ("LS", "transfer", "reference", "pseudo", "transfer_devtok")
    dev_tok = [sum(sc[j][3] for sc in devsc) / len(devsc) for j in range(5)]
    FIX = ("cascade", "SB->T->T", "T->T", "P->SB->T->T")
    U = {k: {} for k in POL + FIX}; A = {k: {} for k in POL + FIX}; K = {k: {} for k in POL + FIX}; unseen = Counter(); diag = []
    for h in (0, 1):
        sc_h = [lcm.seed_calls(tgt[i], s) for i in half[h] for s in (1, 2, 3)]
        tok = [sum(sc[j][3] for sc in sc_h) / len(sc_h) for j in range(5)]
        pi, pdev, miss, rank, ncls, ll_a, ll_d = em_prior(dev_oc, [full(sc)[0] for sc in sc_h])
        w = [pi[c] / pdev[c] for _, c in dev_oc]
        P = {"LS": Supervised(dev_rows, tok, w), "transfer": Supervised(dev_rows, tok),
             "reference": Supervised([full(sc) for sc in sc_h], tok), "pseudo": Supervised([pseudo(sc) for sc in sc_h], tok),
             "transfer_devtok": Supervised(dev_rows, dev_tok)}
        diag.append(dict(half=h, unseen_obs=miss, rank=rank, classes=ncls, ll_adapted=ll_a, ll_dev=ll_d,
                         pi_right_T=sum(v for c, v in pi.items() if c[3]), pdev_right_T=sum(v for c, v in pdev.items() if c[3]),
                         pi_right_N=sum(v for c, v in pi.items() if c[0]), pdev_right_N=sum(v for c, v in pdev.items() if c[0]),
                         estimation_ktok=sum(tok) / 1000))
        for i in half[1 - h]:
            acc, ra, ka = Counter(), Counter(), Counter()
            for s in (1, 2, 3):
                sc = lcm.seed_calls(tgt[i], s)
                out = {}
                for k, S in P.items():
                    ok, t, seen = S.run(sc)
                    if not seen:
                        ok, t = lcm.fixed("cascade", sc); unseen[k] += 1
                    out[k] = (ok, t)
                for f in FIX:
                    out[f] = fixed(f, sc)
                for k, (ok, t) in out.items():
                    acc[k] += u(ok, t); ra[k] += float(ok); ka[k] += t
            for k in POL + FIX:
                U[k][i], A[k][i], K[k][i] = acc[k] / 3, 100 * ra[k] / 3, ka[k] / 3
    m = {k: sum(v.values()) / len(ids) for k, v in U.items()}
    d = lambda a, b: ci({i: (U[a][i] - U[b][i]) / 100 for i in ids})
    rec = dict(task=name, n=len(ids), mean=m, unseen=dict(unseen), diag=diag,
               LS_vs_cascade=d("LS", "cascade"), LS_vs_transfer=d("LS", "transfer"), LS_vs_default=d("LS", "SB->T->T"),
               transfer_vs_cascade=d("transfer", "cascade"), reference_vs_cascade=d("reference", "cascade"),
               LS_vs_reference=d("LS", "reference"), pseudo_vs_cascade=d("pseudo", "cascade"), LS_vs_swap=d("LS", "P->SB->T->T"),
               tr_vs_cascade=d("transfer_devtok", "cascade"), tr_vs_default=d("transfer_devtok", "SB->T->T"),
               cascade_vs_default=d("cascade", "SB->T->T"), cascade_p=pboot({i: U["cascade"][i] - U["SB->T->T"][i] for i in ids}),
               tr_p=pboot({i: U["transfer_devtok"][i] - U["cascade"][i] for i in ids}),
               acc={k: sum(v.values()) / len(ids) for k, v in A.items()}, ktok={k: sum(v.values()) / len(ids) / 1000 for k, v in K.items()},
               tr_acc_vs_cascade=ci({i: (A["transfer_devtok"][i] - A["cascade"][i]) / 100 for i in ids}))
    f = lambda v: f"{v[0]:+.2f} [{v[1]:+.2f}, {v[2]:+.2f}]"
    room = m["reference"] - m["cascade"]
    print(f"*** {name} ({len(ids)} questions): " + ", ".join(f"{k} {v:+.2f}" for k, v in m.items()), flush=True)
    print(f"    LS - cascade {f(rec['LS_vs_cascade'])}; LS - transfer {f(rec['LS_vs_transfer'])}; LS - SB->T->T {f(rec['LS_vs_default'])}; "
          f"transfer - cascade {f(rec['transfer_vs_cascade'])}; reference - cascade {f(rec['reference_vs_cascade'])} (LS recovers "
          f"{(m['LS'] - m['cascade']) / room if abs(room) > 1e-9 else float('nan'):.2f} of it); pseudo - cascade {f(rec['pseudo_vs_cascade'])}; "
          f"LS - P->SB->T->T {f(rec['LS_vs_swap'])}; unseen patterns {dict(unseen)}", flush=True)
    for x in diag:
        print(f"    half {x['half']}: classes {x['classes']}, rank {x['rank']}, target observations unseen in development {100 * x['unseen_obs']:.1f}%, "
              f"log-lik per obs adapted {x['ll_adapted']:.3f} vs dev prior {x['ll_dev']:.3f}; P(T right) {x['pdev_right_T']:.2f} -> "
              f"{x['pi_right_T']:.2f}, P(N right) {x['pdev_right_N']:.2f} -> {x['pi_right_N']:.2f}; estimation sample cost "
              f"{x['estimation_ktok']:.1f}k tokens per question-seed", flush=True)
    od = os.path.join(lcm.ROOT, "results", "lcm_shift")
    os.makedirs(od, exist_ok=True)
    json.dump(rec, open(f"{od}/{name.split(' (')[0].replace(' ', '_').replace('<-', '_')}.json", "w"))
    return rec


def pboot(d, B=10000):
    """one-sided bootstrap p-value of mean(d) <= 0 over questions (as analyze_final.pvalue: resample questions)"""
    import random
    ids = sorted(d); n = len(ids); rng = random.Random(0)
    return sum(sum(d[rng.choice(ids)] for _ in range(n)) / n <= 0 for _ in range(B)) / B


def main_tr():
    """addendum TR: Spider dev, the four generators, the planner fitted on BIRD dev + fresh + Spider test with their tokens
    (--dqs: the sensitivity as in FINAL, Spider's rows graded with a SQLite that accepts double-quoted literals, tags <m>spq / <m>sdq)"""
    R = []
    q = "--dqs" in sys.argv
    for g in ("q8b", "q14a", "q35", "oss20"):
        p = PEER[g]
        dev = [quiet(lcm.load, "sql", g, p, x) for x in ("dev", "fresh", "spq" if q else "spider")]
        tgt = quiet(lcm.load, "sql", g, p, "sdq" if q else "spiderdev")
        if not tgt or not all(dev):
            print(f"*** sql spiderdev {g}<-{p}: rows missing", flush=True)
            continue
        r = run_cell(f"sql spiderdev{' dqs' if q else ''} {g}<-{p} (from BIRD + Spider test)", dev, tgt)
        f = lambda v: f"{v[0]:+.2f} [{v[1]:+.2f}, {v[2]:+.2f}]"
        print(f"    TR: transfer (development tokens) - cascade {f(r['tr_vs_cascade'])} (one-sided p {r['tr_p']:.4f}); accuracy "
              f"{f(r['tr_acc_vs_cascade'])}; {r['acc']['transfer_devtok']:.1f}% @ {r['ktok']['transfer_devtok']:.2f}k vs cascade "
              f"{r['acc']['cascade']:.1f}% @ {r['ktok']['cascade']:.2f}k; - SB->T->T {f(r['tr_vs_default'])}", flush=True)
        R.append(r)
    k = len(R); order = sorted(range(k), key=lambda j: R[j]["tr_p"]); holm = {}; run = 0.0
    for rank, j in enumerate(order):
        run = max(run, min(1.0, (k - rank) * R[j]["tr_p"])); holm[j] = run
    n_lo = sum(r["tr_vs_cascade"][1] > 0 for r in R)
    print(f"\n*** TR-P1 transfer - cascade on Spider dev: lower bound > 0 in {n_lo} of {k} (needs >= 3) -> "
          f"{'holds' if n_lo >= 3 else 'refuted'}; worse (upper bound < 0) in {sum(r['tr_vs_cascade'][2] < 0 for r in R)}; Holm-adjusted p: "
          + ", ".join(f"{R[j]['task'].split(' (')[0]} {holm[j]:.4f}" for j in range(k)))


def main_tr_c1():
    """addendum TR-C1: CV-1's trained quick query (C1 adapter on Qwen3-8B) as N, the base model's SB and T, Qwen3.5-9B's quick query as
    P (FINAL's F5 cell) on Spider dev; the planner fitted on BIRD dev and Spider test (not the fresh BIRD-train questions: C1's training
    pool). --explore: fitted on BIRD dev only and run on Spider test (an already used set: sets the expectation, decides nothing)"""
    q, ex = "--dqs" in sys.argv, "--explore" in sys.argv
    sp, sd = ("spq", "sdq") if q else ("spider", "spiderdev")
    dev = [quiet(lcm.load, "sql", "q8b", "q35", x, nsrc="q8bcvc1") for x in (("dev",) if ex else ("dev", sp))]
    tgt = quiet(lcm.load, "sql", "q8b", "q35", sp if ex else sd, nsrc="q8bcvc1")
    name = f"sql {'spider (explore)' if ex else 'spiderdev'}{' dqs' if q else ''} C1q8b<-q35 (from BIRD{'' if ex else ' + Spider test'})"
    if not tgt or not all(dev):
        print(f"*** {name}: rows missing", flush=True)
        return
    r = run_cell(name, dev, tgt)
    f = lambda v: f"{v[0]:+.2f} [{v[1]:+.2f}, {v[2]:+.2f}]"
    print(f"    TR-C1: cascade - SB->T->T {f(r['cascade_vs_default'])} (one-sided p {r['cascade_p']:.4f}); transfer (development tokens) "
          f"- cascade {f(r['tr_vs_cascade'])} (one-sided p {r['tr_p']:.4f}); {r['acc']['transfer_devtok']:.1f}% @ "
          f"{r['ktok']['transfer_devtok']:.2f}k vs cascade {r['acc']['cascade']:.1f}% @ {r['ktok']['cascade']:.2f}k vs SB->T->T "
          f"{r['acc']['SB->T->T']:.1f}% @ {r['ktok']['SB->T->T']:.2f}k; transfer - SB->T->T {f(r['tr_vs_default'])}", flush=True)
    if not ex:
        print(f"*** TR-C1-P1 (cascade - SB->T->T lower bound > 0): {'holds' if r['cascade_vs_default'][1] > 0 else 'refuted'}; "
              f"TR-C1-P2 (transfer - cascade lower bound > 0): {'holds' if r['tr_vs_cascade'][1] > 0 else 'refuted'}", flush=True)


def main_trt():
    """addendum TRT: the policy fitted on BFCL (non-live + live, all labels, their tokens) and run on 3,549 held-out ToolACE requests,
    for Qwen3-8B's base quick calls and TC-RL's trained ones (q8btcc1), Qwen3.5-9B's quick calls as P, Qwen3-8B's SB and T"""
    R = {}
    for name, nsrc, ntag in (("base", None, "hoq8b"), ("C1tc", "q8btcc1", "hoq8btcc1")):
        k = {"nsrc": nsrc} if nsrc else {}
        dev = [quiet(lcm.load, "tc", "q8b", "q35", x, **k) for x in ("non-live", "live")]
        tgt = quiet(lcm.load_tcho, ntag)
        if not tgt or not all(dev):
            print(f"*** toolace held-out {name}: rows missing", flush=True)
            continue
        r = R[name] = run_cell(f"toolace-ho {name}q8b<-q35 (from BFCL)", dev, tgt)
        f = lambda v: f"{v[0]:+.2f} [{v[1]:+.2f}, {v[2]:+.2f}]"
        print(f"    TRT {name}: transfer (development tokens) - cascade {f(r['tr_vs_cascade'])} (one-sided p {r['tr_p']:.4f}); "
              f"{r['acc']['transfer_devtok']:.1f}% @ {r['ktok']['transfer_devtok']:.2f}k vs cascade {r['acc']['cascade']:.1f}% @ "
              f"{r['ktok']['cascade']:.2f}k vs SB->T->T {r['acc']['SB->T->T']:.1f}% @ {r['ktok']['SB->T->T']:.2f}k; cascade - SB->T->T "
              f"{f(r['cascade_vs_default'])}", flush=True)
        S = [lcm.seed_calls(q, s) for q in tgt.values() for s in (1, 2, 3)]
        st = [sc for sc in S if sc[0][1] and not (sc[1][1] and sc[1][0] == sc[0][0])]
        print(f"    stratum N passes, P differs ({len(st)} question-seeds): N right {100 * sum(sc[0][2] for sc in st) / len(st):.1f}%, SB "
              f"{100 * sum(sc[2][2] for sc in st) / len(st):.1f}%, T {100 * sum(sc[3][2] for sc in st) / len(st):.1f}%", flush=True)
    if "C1tc" in R:
        print(f"*** TRT-P1 (trained: transfer - cascade lower bound > 0): {'holds' if R['C1tc']['tr_vs_cascade'][1] > 0 else 'refuted'}")
    if "base" in R:
        print(f"*** TRT-P2 (base: transfer - cascade lower bound > 0): {'holds' if R['base']['tr_vs_cascade'][1] > 0 else 'refuted'}")


def main_tl():
    """addendum TL: the policy fitted only on held-out questions of the trained quick answer's training split (SQL: the 1,338 fresh
    BIRD-train questions, C1's quick query as q8bcvc1pa; tool calls: the 3,549 held-out ToolACE requests) and run on the task's
    benchmarks (BIRD dev, Spider test, Spider dev; BFCL non-live + live as one set), trained (C1 / C1tc) and base quick answers.
    --dqs: Spider graded by the host's SQLite (spq / sdq), as FINAL's sensitivity"""
    q = "--dqs" in sys.argv
    f = lambda v: f"{v[0]:+.2f} [{v[1]:+.2f}, {v[2]:+.2f}]"
    R = {}
    for name, nsql, ntc, ntag in (("trained", "q8bcvc1", "q8btcc1", "hoq8btcc1"), ("base", None, None, "hoq8b")):
        ks = {"nsrc": nsql} if nsql else {}
        kt = {"nsrc": ntc} if ntc else {}
        cells = [("sql", "BIRD-train fresh", [quiet(lcm.load, "sql", "q8b", "q35", "fresh", **ks)], t,
                  quiet(lcm.load, "sql", "q8b", "q35", x, **ks)) for t, x in (("BIRD dev", "dev"), ("Spider test", "spq" if q else "spider"),
                                                                                ("Spider dev", "sdq" if q else "spiderdev"))]
        nl, lv = quiet(lcm.load, "tc", "q8b", "q35", "non-live", **kt), quiet(lcm.load, "tc", "q8b", "q35", "live", **kt)
        bf = None
        if nl and lv:
            assert not set(nl) & set(lv)
            bf = {**nl, **lv}
        cells.append(("tc", "ToolACE held-out", [quiet(lcm.load_tcho, ntag)], "BFCL", bf))
        for task, src, dev, tname, tgt in cells:
            cn = f"{task} {tname}{' dqs' if q and tname.startswith('Spider') else ''} {name} (from {src})"
            if not tgt or not all(dev):
                print(f"*** {cn}: rows missing", flush=True)
                continue
            r = R[(name, tname)] = run_cell(cn, dev, tgt)
            print(f"    TL {name} {tname}: transfer (training-split tokens) - cascade {f(r['tr_vs_cascade'])} (one-sided p {r['tr_p']:.4f}); "
                  f"{r['acc']['transfer_devtok']:.1f}% @ {r['ktok']['transfer_devtok']:.2f}k vs cascade {r['acc']['cascade']:.1f}% @ "
                  f"{r['ktok']['cascade']:.2f}k vs SB->T->T {r['acc']['SB->T->T']:.1f}% @ {r['ktok']['SB->T->T']:.2f}k", flush=True)
    for name, tag in (("trained", "TL-P1"), ("base", "TL-P2")):
        X = [R[(name, t)] for t in ("BIRD dev", "Spider test", "Spider dev", "BFCL") if (name, t) in R]
        if len(X) < 4:
            print(f"*** {tag}: {len(X)} of 4 cells present, not decided")
            continue
        up, down = sum(r["tr_vs_cascade"][1] > 0 for r in X), sum(r["tr_vs_cascade"][2] < 0 for r in X)
        print(f"*** {tag} ({name}: transfer - cascade lower bound > 0 in >= 2 of 4, upper bound < 0 in none): {up} above, {down} below -> "
              f"{'holds' if up >= 2 and down == 0 else 'refuted'}")


def main_tl4():
    """addendum TL4: TL's tool-call cell with Qwen3-4B as the generator (N = C1tc-4B q4btcc1 or base q4b, SB and T = base Qwen3-4B,
    P = Qwen3.5-9B): fitted on the 3,549 held-out ToolACE requests, run on BFCL (primary); the reverse direction reported"""
    f = lambda v: f"{v[0]:+.2f} [{v[1]:+.2f}, {v[2]:+.2f}]"
    R = {}
    for name, nsrc, ntag in (("trained", "q4btcc1", "hoq4btcc1"), ("base", None, "hoq4b")):
        k = {"nsrc": nsrc} if nsrc else {}
        nl, lv = quiet(lcm.load, "tc", "q4b", "q35", "non-live", **k), quiet(lcm.load, "tc", "q4b", "q35", "live", **k)
        ho = quiet(lcm.load_tcho, ntag, dtag="hoq4b")
        if not (nl and lv and ho):
            print(f"*** {name}: rows missing", flush=True)
            continue
        assert not set(nl) & set(lv)
        bf = {**nl, **lv}
        for tname, dev, tgt in (("BFCL", [ho], bf), ("ToolACE held-out", [nl, lv], ho)):
            r = R[(name, tname)] = run_cell(f"tc {tname} q4b {name} (from {'ToolACE held-out' if tname == 'BFCL' else 'BFCL'})", dev, tgt)
            S = [lcm.seed_calls(q, s) for q in tgt.values() for s in (1, 2, 3)]
            st = [sc for sc in S if sc[0][1] and not (sc[1][1] and sc[1][0] == sc[0][0])]
            print(f"    TL4 {name} {tname}: transfer - cascade {f(r['tr_vs_cascade'])} (one-sided p {r['tr_p']:.4f}); "
                  f"{r['acc']['transfer_devtok']:.1f}% @ {r['ktok']['transfer_devtok']:.2f}k vs cascade {r['acc']['cascade']:.1f}% @ "
                  f"{r['ktok']['cascade']:.2f}k vs SB->T->T {r['acc']['SB->T->T']:.1f}% @ {r['ktok']['SB->T->T']:.2f}k; cascade - SB->T->T "
                  f"{f(r['cascade_vs_default'])}; stratum N passes, P differs ({len(st)}): N {100 * sum(sc[0][2] for sc in st) / len(st):.1f}%, "
                  f"SB {100 * sum(sc[2][2] for sc in st) / len(st):.1f}%, T {100 * sum(sc[3][2] for sc in st) / len(st):.1f}%", flush=True)
    for name, tag in (("trained", "TL4-P1"), ("base", "TL4-P2")):
        if (name, "BFCL") in R:
            print(f"*** {tag} ({name} Qwen3-4B, BFCL from held-out ToolACE: transfer - cascade lower bound > 0): "
                  f"{'holds' if R[(name, 'BFCL')]['tr_vs_cascade'][1] > 0 else 'refuted'}")


# ---------------------------------------------------------------- addendum RV
RV_T = (("sql", "dev", "BIRD dev"), ("sql", "spider", "Spider test"), ("sql", "spiderdev", "Spider dev"), ("tc", "bfcl", "BFCL"))
RV_N = {"sql": "q8bcvc1", "tc": "q8btcc1"}   # the trained quick answers (C1, C1tc); base = Qwen3-8B's own quick answers


def rv_key(task, sset, i, kind, text):
    import hashlib
    return hashlib.sha1(json.dumps([task, sset, i, kind, text]).encode()).hexdigest()[:20]


def rv_texts(task, sset, nsrc, gen="q8b", peer="q35"):
    """{(call type, seed, id): the answer's text}: SQL the extracted query (prep_sql.extract), tool calls the graded calls; gen / peer
    (SQL, addendum SEL-G): the generator whose quick query, short think and think are N, SB, T, and the peer"""
    from run_nlopt import _rows
    R, out = os.path.join(lcm.ROOT, "results", task), {}
    if task == "sql":
        from prep_sql import extract
        suf = {"dev": "", "spider": "sp", "spiderdev": "sd", "fresh": "pa"}[sset]   # fresh: SEL's validation questions
        for t, tag, a, fld in (("N", nsrc or gen, "cheap", "n_text"), ("P", peer, "cheap", "n_text"), ("SB", gen, "sb", "text"),
                               ("T", gen, "think", "text")):
            for s in (1, 2, 3):
                for r in _rows(f"{R}/{tag}{suf}_{a}_s{s}.jsonl"):
                    out[(t, s, r["id"])] = extract(r.get(fld) or "")
        return out
    from analyze_tc import load

    def show(calls):   # the graded calls (a JSON list of JSON {name: args} strings) one per line as name(arg=value, ...)
        try:
            L = [json.loads(x) if isinstance(x, str) else x for x in json.loads(calls)]
            return "\n".join(f"{n}({', '.join(f'{k}={json.dumps(v)}' for k, v in a.items())})" for c in L for n, a in c.items()) or "(no call)"
        except Exception:
            return str(calls)
    for t, tag, arm in (("N", nsrc or "q8b", "N"), ("P", "q35", "N"), ("SB", "q8b", "SB"), ("T", "q8b", "T")):
        for s in (1, 2, 3):
            for i, g in load(tag, s)[0].items():
                if arm in g and g[arm].get("calls") is not None:
                    out[(t, s, i)] = show(g[arm]["calls"])
    return out


def rv_items(task, sset, nsrc, gen="q8b", peer="q35"):
    """(questions, [(id, seed, {answer key: [right, (calls returning it), [texts]]}, fallback right)]): the cascade's question-seeds where
    N passed, P did not return the same answer, and N, P and the fallback d (SB if it passes, else T, else the retry T) give >= 2
    distinct passing answers"""
    k = {"nsrc": nsrc} if nsrc else {}
    if task == "sql":
        D = quiet(lcm.load, "sql", gen, peer, sset, **k)
    else:
        nl, lv = quiet(lcm.load, "tc", "q8b", "q35", "non-live", **k), quiet(lcm.load, "tc", "q8b", "q35", "live", **k)
        assert not set(nl) & set(lv)
        D = {**nl, **lv}
    X, out = rv_texts(task, sset, nsrc, gen, peer), []
    for i, q in D.items():
        for s in (1, 2, 3):
            N, P, SB, T, T2 = lcm.seed_calls(q, s)
            if not N[1] or (P[1] and P[0] is not None and P[0] == N[0]):
                continue
            dn, d, dk = ("SB", SB, ("SB", s)) if SB[1] else (("T", T, ("T", s)) if T[1] else ("T2", T2, ("T", s % 3 + 1)))
            cand = {}
            for nm, x, tk in (("N", N, ("N", s)), ("P", P, ("P", s)), (dn, d, dk)):
                if x[1] and x[0] is not None:
                    c = cand.setdefault(x[0], [bool(x[2]), (), []])
                    c[1] += (nm,); c[2].append(X[(tk[0], tk[1], i)])
            if len(cand) >= 2:
                out.append((i, s, cand, bool(d[2])))
    return D, out


def main_rv_build():
    req = {}
    for task, sset, tname in RV_T:
        for nsrc in (None, RV_N[task]):
            D, items = rv_items(task, sset, nsrc)
            for i, s, cand, dr in items:
                for r, calls, texts in cand.values():
                    for t in set(texts):
                        for kind in ("rev", "cod"):
                            h = rv_key(task, sset, i, kind, t)
                            req[h] = {"h": h, "task": task, "sset": sset, "id": i, "kind": kind, "text": t}
            print(f"RV build {tname} {nsrc or 'base'}: {len(D)} questions, {len(items)} multi-answer fallback question-seeds "
                  f"({100 * len(items) / (3 * len(D)):.1f}%); requests so far {len(req)}", flush=True)
    od = os.path.join(lcm.ROOT, "results", "conf")
    os.makedirs(od, exist_ok=True)
    with open(f"{od}/rv_req.jsonl", "w") as f:
        for r in req.values():
            f.write(json.dumps(r) + "\n")
    print(f"RV build: {len(req)} requests -> results/conf/rv_req.jsonl")


def rv_gauss(items, A, reps=20, seed=0):
    """PREREG_LCM addendum RV, theory: gain (points over all question-seeds, given len(items) of n) of the Bayes selector with the
    in-cell structural prior and a score of within-item AUROC A (equal-variance Gaussian), and of R1 (votes, ties by the score)"""
    import random
    from statistics import NormalDist
    rng, dp = random.Random(seed), (math.sqrt(2) * NormalDist().inv_cdf(min(A, 0.999)) if A > 0.5 else 0.0)   # A = 1 (a tiny smoke) clamped
    cnt, rt = Counter(), Counter()
    for _, _, cand, _ in items:
        st = tuple(sorted(v[1] for v in cand.values()))
        for c in cand.values():
            r, calls = c[0], c[1]
            cnt[(st, calls)] += 1; rt[(st, calls)] += r
    g = g1 = 0.0
    for _, _, cand, dr in items:
        st = tuple(sorted(v[1] for v in cand.values()))
        for _ in range(reps):
            best = b1 = None
            for c in cand.values():
                r, calls = c[0], c[1]
                p = min(max(rt[(st, calls)] / cnt[(st, calls)], 1e-3), 1 - 1e-3)
                x = rng.gauss(dp if r else 0.0, 1.0)
                lr = math.exp(dp * x - dp * dp / 2)
                post = p * lr / (p * lr + 1 - p)
                best = max(best or (-1, 0), (post, r)); b1 = max(b1 or ((-1, -1e9), 0), ((len(calls), x), r))
            g += (best[1] - dr) / reps; g1 += (b1[1] - dr) / reps
    return g, g1


def main_rv():
    """addendum RV: within-item AUROC of the channel score (rev) and the direct score (cod) on the mixed candidate sets; R1 (votes, ties
    by rev) against the cascade; the cross-fitted Bayes selector (structural prior + beta x standardized rev, fitted on one crc32 half)
    against the Gaussian bound at the measured AUROC. RV2 (when results/conf/rv_scores_q35.jsonl exists): the peer's (Qwen3.5-9B's)
    channel score and the sum of both models' within-question standardized channel scores"""
    from analyze_ho3 import ci
    from run_nlopt import _rows
    from statistics import NormalDist
    S = {r["h"]: r for r in _rows(os.path.join(lcm.ROOT, "results", "conf", "rv_scores.jsonl"))}
    S2 = {r["h"]: r for r in _rows(os.path.join(lcm.ROOT, "results", "conf", "rv_scores_q35.jsonl"))}
    Z = NormalDist()
    f = lambda v: f"{v[0]:+.2f} [{v[1]:+.2f}, {v[2]:+.2f}]"
    g = lambda v: f"{v[0]:.3f} [{v[1]:.3f}, {v[2]:.3f}]"
    R = {}
    for task, sset, tname in RV_T:
        for name, nsrc in (("base", None), ("trained", RV_N[task])):
            D, items = rv_items(task, sset, nsrc)
            miss, pre = 0, 0
            for i, s, cand, dr in items:
                for c in cand.values():
                    rv, cd = [S.get(rv_key(task, sset, i, "rev", t)) for t in c[2]], [S.get(rv_key(task, sset, i, "cod", t)) for t in c[2]]
                    r2 = [S2.get(rv_key(task, sset, i, "rev", t)) for t in c[2]]
                    if any(x is None for x in rv + cd):
                        miss += 1; c.extend([None, None, None]); continue
                    c.append(sum(x["s"] for x in rv) / len(rv)); c.append(sum(x["s"] / max(1, x["n"]) for x in cd) / len(cd))
                    c.append(sum(x["s"] for x in r2) / len(r2) if S2 and all(r2) else None)   # c[5]: the peer's channel score
                    pre += sum(x["pre"] for x in rv)
            items = [it for it in items if all(c[3] is not None for c in it[2].values())]
            auc = {"rev": {}, "cod": {}, "diff": {}}
            r1, r1c, rmax, dd = Counter(), Counter(), Counter(), Counter()
            nseed = Counter()
            for i, s, cand, dr in items:
                C = list(cand.values())
                pos, neg = [c for c in C if c[0]], [c for c in C if not c[0]]
                if pos and neg:
                    a = {j: sum((p[j] > n[j]) + 0.5 * (p[j] == n[j]) for p in pos for n in neg) / (len(pos) * len(neg)) for j in (3, 4)}
                    for key, v in (("rev", a[3]), ("cod", a[4]), ("diff", a[3] - a[4])):
                        auc[key].setdefault(i, []).append(v)
                r1[i] += max(C, key=lambda c: (len(c[1]), c[3]))[0] - dr
                r1c[i] += max(C, key=lambda c: (len(c[1]), c[4]))[0] - dr
                rmax[i] += max(C, key=lambda c: c[3])[0] - dr
            A = {k: tuple(y / 100 for y in ci({i: sum(v) / len(v) for i, v in x.items()})) for k, x in auc.items()}   # fractions
            ids = sorted(D)
            r1ci = ci({i: r1[i] / 3 for i in ids}); r1cci = ci({i: r1c[i] / 3 for i in ids}); rmci = ci({i: rmax[i] / 3 for i in ids})
            # cross-fitted Bayes: logit pi(structure, calls) + beta x z, z = (rev - item mean) / sd, fitted on the other crc32 half
            bay = Counter()
            for h in (0, 1):
                fit = [it for it in items if zlib.crc32(it[0].encode()) % 2 == h]
                dev = [(c[3] - sum(x[3] for x in it[2].values()) / len(it[2])) for it in fit for c in it[2].values()]
                sd = (sum(x * x for x in dev) / max(1, len(dev))) ** 0.5 or 1.0
                cnt, rt = Counter(), Counter()
                for it in fit:
                    st = tuple(sorted(v[1] for v in it[2].values()))
                    for c in it[2].values():
                        cnt[(st, c[1])] += 1; rt[(st, c[1])] += c[0]
                lg = lambda st, c: math.log(min(max((rt[(st, c[1])] + 0.5) / (cnt[(st, c[1])] + 1), 1e-3), 1 - 1e-3) /
                                            (1 - min(max((rt[(st, c[1])] + 0.5) / (cnt[(st, c[1])] + 1), 1e-3), 1 - 1e-3)))

                def ll(beta):
                    t = 0.0
                    for it in fit:
                        st, mu = tuple(sorted(v[1] for v in it[2].values())), sum(x[3] for x in it[2].values()) / len(it[2])
                        for c in it[2].values():
                            z = lg(st, c) + beta * (c[3] - mu) / sd
                            t += -math.log1p(math.exp(-z)) if c[0] else -math.log1p(math.exp(z))
                    return t
                beta = max((b / 10 for b in range(0, 41)), key=ll)
                for it in items:
                    if zlib.crc32(it[0].encode()) % 2 == h:
                        continue
                    st, mu = tuple(sorted(v[1] for v in it[2].values())), sum(x[3] for x in it[2].values()) / len(it[2])
                    if any(cnt[(st, c[1])] == 0 for c in it[2].values()):
                        continue   # a structure the fitting half never saw: the cascade's answer
                    bay[it[0]] += max(it[2].values(), key=lambda c: lg(st, c) + beta * (c[3] - mu) / sd)[0] - it[3]
            byci = ci({i: bay[i] / 3 for i in ids})
            pb, p1 = rv_gauss(items, A["rev"][0])
            n = 3 * len(ids)
            R[(name, tname)] = dict(A=A, r1=r1ci, bayes=byci, bound=(100 * pb / n, 100 * p1 / n))
            it2 = [it for it in items if all(c[5] is not None for c in it[2].values())]
            if S2 and it2:   # RV2: z = (score - question mean) / pooled sd per model (label-free), sum of the two models' z
                sd = {}
                for j in (3, 5):
                    dv = [c[j] - sum(x[j] for x in it[2].values()) / len(it[2]) for it in it2 for c in it[2].values()]
                    sd[j] = (sum(x * x for x in dv) / len(dv)) ** 0.5 or 1.0
                for it in it2:
                    mu = {j: sum(x[j] for x in it[2].values()) / len(it[2]) for j in (3, 5)}
                    for c in it[2].values():
                        c.append((c[3] - mu[3]) / sd[3] + (c[5] - mu[5]) / sd[5])   # c[6]
                au2 = {"q35": {}, "sum": {}, "sum-rev": {}}
                r2s = Counter(); zz = {True: [], False: []}
                for i, s, cand, dr in it2:
                    C = list(cand.values())
                    pos, neg = [c for c in C if c[0]], [c for c in C if not c[0]]
                    mu = {j: sum(x[j] for x in C) / len(C) for j in (3, 5)}
                    for c in C:
                        zz[c[0]].append(((c[3] - mu[3]) / sd[3], (c[5] - mu[5]) / sd[5]))
                    if pos and neg:
                        a = {j: sum((p[j] > q_[j]) + 0.5 * (p[j] == q_[j]) for p in pos for q_ in neg) / (len(pos) * len(neg)) for j in (3, 5, 6)}
                        for key, v in (("q35", a[5]), ("sum", a[6]), ("sum-rev", a[6] - a[3])):
                            au2[key].setdefault(i, []).append(v)
                    r2s[i] += max(C, key=lambda c: (len(c[1]), c[6]))[0] - dr
                A2 = {k: tuple(y / 100 for y in ci({i: sum(v) / len(v) for i, v in x.items()})) for k, x in au2.items()}
                num = den1 = den2 = 0.0   # within-class correlation of the two models' standardized deviations
                for cl, L in zz.items():
                    if len(L) < 2:
                        continue
                    m1, m2 = sum(a for a, _ in L) / len(L), sum(b for _, b in L) / len(L)
                    num += sum((a - m1) * (b - m2) for a, b in L); den1 += sum((a - m1) ** 2 for a, _ in L); den2 += sum((b - m2) ** 2 for _, b in L)
                rho = num / math.sqrt(den1 * den2) if den1 and den2 else float("nan")
                dpr = lambda a: math.sqrt(2) * Z.inv_cdf(min(max(a, 1e-6), 1 - 1e-6))
                pred = Z.cdf((dpr(A["rev"][0]) + dpr(A2["q35"][0])) / math.sqrt(2 + 2 * rho) / math.sqrt(2))
                r2ci = ci({i: r2s[i] / 3 for i in ids})
                R[(name, tname)].update(A2=A2, r2=r2ci, pred=pred)
                print(f"    RV2 {tname} {name}: {len(it2)} of {len(items)} question-seeds scored by both; within-question AUROC Qwen3.5-9B rev "
                      f"{g(A2['q35'])}, sum {g(A2['sum'])}, sum - Qwen3-8B rev {g(A2['sum-rev'])}; within-class correlation {rho:.2f}, "
                      f"predicted sum AUROC {pred:.3f}; R1 with the sum - cascade {f(r2ci)}", flush=True)
            print(f"    RV {tname} {name}: {len(ids)} questions, {len(items)} multi-answer fallback question-seeds ({100 * len(items) / n:.1f}%), "
                  f"missing scores {miss}; within-item AUROC rev {g(A['rev'])}, cod {g(A['cod'])}, rev - cod {g(A['diff'])} "
                  f"({len(auc['rev'])} questions with a mixed set); R1 (votes, ties by rev) - cascade {f(r1ci)} (votes, ties by cod "
                  f"{f(r1cci)}; rev alone {f(rmci)}); cross-fitted Bayes - cascade {f(byci)}; Gaussian bound at the measured AUROC: Bayes "
                  f"{100 * pb / n:+.2f}, R1 {100 * p1 / n:+.2f}; reviewer prefill {pre / n:.0f} tokens per question-seed", flush=True)
    for name, tag in (("base", "RV-P2b"), ("trained", "RV-P2t")):
        X = [R[(name, t)] for _, _, t in RV_T if (name, t) in R]
        if len(X) < 4:
            print(f"*** {tag}: {len(X)} of 4 targets present, not decided"); continue
        up, down = sum(r["r1"][1] > 0 for r in X), sum(r["r1"][2] < 0 for r in X)
        print(f"*** {tag} ({name}: R1 - cascade lower bound > 0 in >= 2 of 4, upper bound < 0 in none): {up} above, {down} below -> "
              f"{'holds' if up >= 2 and down == 0 else 'refuted'}")
    if len(R) == 8:
        p1 = sum(r["A"]["diff"][1] > 0 for r in R.values())
        p3 = sum(abs(r["bayes"][0] - r["bound"][0]) <= 0.7 for r in R.values())
        hi = [f"{t} {nm}" for (nm, t), r in R.items() if r["A"]["rev"][0] >= 0.75]
        print(f"*** RV-P1 (rev - cod within-item AUROC lower bound > 0 in >= 6 of 8): {p1} -> {'holds' if p1 >= 6 else 'refuted'}")
        print(f"*** RV-P3 (cross-fitted Bayes within 0.7 of the Gaussian bound in >= 6 of 8): {p3} -> {'holds' if p3 >= 6 else 'refuted'}")
        print(f"*** cells with rev AUROC >= 0.75: {hi or 'none'}")
    if S2 and sum("A2" in r for r in R.values()) == 8:
        q1 = sum(r["A2"]["sum-rev"][1] > 0 for r in R.values())
        q3 = sum(abs(r["A2"]["sum"][0] - r["pred"]) <= 0.03 for r in R.values())
        print(f"*** RV2-P1 (sum - Qwen3-8B rev within-question AUROC lower bound > 0 in >= 6 of 8): {q1} -> {'holds' if q1 >= 6 else 'refuted'}")
        print(f"*** RV2-P3 (sum AUROC within 0.03 of the prediction from the two AUROCs and their correlation in >= 6 of 8): {q3} -> "
              f"{'holds' if q3 >= 6 else 'refuted'}")
        for name, tag in (("base", "RV2-P2b"), ("trained", "RV2-P2t")):
            X = [R[(name, t)] for _, _, t in RV_T]
            up, down = sum(r["r2"][1] > 0 for r in X), sum(r["r2"][2] < 0 for r in X)
            print(f"*** {tag} ({name}: R1 with the sum - cascade lower bound > 0 in >= 2 of 4, upper bound < 0 in none): {up} above, "
                  f"{down} below -> {'holds' if up >= 2 and down == 0 else 'refuted'}")


SEL_T = (("dev", "BIRD dev"), ("spider", "Spider test"), ("spiderdev", "Spider dev"))


def sel_val_ids():
    return set(open(os.path.join(os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data"), "bird", "sel_val_ids.txt")).read().split())


def main_sel_build():
    """addendum SEL: the candidates to score -> results/conf/sel_req.jsonl (RV's SQL cells, and the fresh questions on the held-out
    databases for the checkpoint and beta)"""
    req, val = {}, sel_val_ids()
    for sset in ("fresh",) + tuple(x for x, _ in SEL_T):
        for nsrc in (None, RV_N["sql"]):
            D, items = rv_items("sql", sset, nsrc)
            for i, s, cand, dr in items:
                if sset == "fresh" and i not in val:
                    continue
                for r, calls, texts in cand.values():
                    for t in set(texts):
                        h = rv_key("sql", sset, i, "sel", t)
                        req[h] = {"h": h, "task": "sql", "sset": sset, "id": i, "kind": "sel", "text": t}
            print(f"SEL build {sset} {nsrc or 'base'}: {len(items)} multi-answer fallback question-seeds; requests so far {len(req)}", flush=True)
    with open(os.path.join(lcm.ROOT, "results", "conf", "sel_req.jsonl"), "w") as f:
        for r in req.values():
            f.write(json.dumps(r) + "\n")
    print(f"SEL build: {len(req)} requests -> results/conf/sel_req.jsonl")


def sel_items(sset, nsrc, S, kind="sel", gen="q8b", peer="q35"):
    """RV's items with each candidate as {r: right, calls, s: its mean score over its texts}; items missing a score are dropped"""
    D, items = rv_items("sql", sset, nsrc, gen, peer)
    out, miss = [], 0
    for i, sd, cand, dr in items:
        C = []
        for r, calls, texts in cand.values():
            x = [S.get(rv_key("sql", sset, i, kind, t)) for t in texts]
            C.append(None if any(v is None for v in x) else {"r": r, "calls": calls, "s": sum(v["s"] for v in x) / len(x),
                                                             "pre": sum(v.get("pre", 0) for v in x)})
        if any(c is None for c in C):
            miss += 1; continue
        out.append((i, sd, C, dr))
    return D, items, out, miss


def sel_auc(items):
    """{question: mean over its mixed question-seeds of the share of (right, wrong) pairs the score orders correctly}"""
    a = {}
    for i, _, C, _ in items:
        pos, neg = [c["s"] for c in C if c["r"]], [c["s"] for c in C if not c["r"]]
        if pos and neg:
            a.setdefault(i, []).append(sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg)))
    return {i: sum(v) / len(v) for i, v in a.items()}


def sel_fit(prior, fit):
    """the Bayes selector: logit pi(calls | set structure) from `prior`, z = (s - question mean) / pooled within-question sd and beta
    (grid 0-4, maximum likelihood) from `fit`; returns choose(item) -> the chosen candidate or None (a structure never seen)"""
    st = lambda C: tuple(sorted(c["calls"] for c in C))
    cnt, rt = Counter(), Counter()
    for _, _, C, _ in prior:
        for c in C:
            cnt[(st(C), c["calls"])] += 1; rt[(st(C), c["calls"])] += c["r"]

    def lg(S, c):
        q = min(max((rt[(S, c["calls"])] + 0.5) / (cnt[(S, c["calls"])] + 1), 1e-3), 1 - 1e-3)
        return math.log(q / (1 - q))
    mu = lambda C: sum(c["s"] for c in C) / len(C)
    dv = [c["s"] - mu(C) for _, _, C, _ in fit for c in C]
    sd = (sum(x * x for x in dv) / max(1, len(dv))) ** 0.5 or 1.0

    def ll(beta):
        t = 0.0
        for _, _, C, _ in fit:
            for c in C:
                z = lg(st(C), c) + beta * (c["s"] - mu(C)) / sd
                t += -math.log1p(math.exp(-z)) if c["r"] else -math.log1p(math.exp(z))
        return t
    beta = max((b / 10 for b in range(0, 41)), key=ll)

    def choose(it):
        C = it[2]
        if any(cnt[(st(C), c["calls"])] == 0 for c in C):
            return None
        return max(C, key=lambda c: lg(st(C), c) + beta * (c["s"] - mu(C)) / sd)
    return choose, beta


def main_sel():
    """addendum SEL. --sel-val n1,n2,...: within-question AUROC of each checkpoint's scores on the fresh held-out-database questions
    (N base and trained pooled) and the choice. --sel <name>: the targets (SEL-P1..P4)."""
    from analyze_ho3 import ci
    from run_nlopt import _rows
    cd = os.path.join(lcm.ROOT, "results", "conf")
    load = lambda nm: {r["h"]: r for r in _rows(os.path.join(cd, f"sel_scores_{nm}.jsonl"))}
    val = sel_val_ids()
    g = lambda v: f"{v[0]:.3f} [{v[1]:.3f}, {v[2]:.3f}]"
    f = lambda v: f"{v[0]:+.2f} [{v[1]:+.2f}, {v[2]:+.2f}]"
    if "--sel-val" in sys.argv:
        best = None
        for nm in sys.argv[sys.argv.index("--sel-val") + 1].split(","):
            S, per = load(nm), {}
            for nsrc in (None, RV_N["sql"]):
                _, _, it, miss = sel_items("fresh", nsrc, S)
                it = [x for x in it if x[0] in val]
                a = sel_auc(it)
                per[nsrc or "base"] = ci(a) if a else (float("nan"),) * 3
                for i, v in a.items():
                    per.setdefault("pooled", {}).setdefault(i, []).append(v)
            if not per.get("pooled"):
                print(f"SEL val {nm}: no scored mixed set", flush=True); continue
            pa = ci({i: sum(v) / len(v) for i, v in per["pooled"].items()})
            print(f"SEL val {nm}: AUROC base {g([x / 100 for x in per['base']])}, trained {g([x / 100 for x in per['q8bcvc1']])}, "
                  f"pooled {g([x / 100 for x in pa])} ({len(per['pooled'])} questions)", flush=True)
            if nm != "local" and (best is None or pa[0] > best[1]):   # the untrained model is reported, not chosen
                best = (nm, pa[0])
        print(f"*** SEL checkpoint (highest pooled held-out-database AUROC): {best[0]}")
        return
    nm = sys.argv[sys.argv.index("--sel") + 1]
    S = load(nm)
    SR = {r["h"]: r for r in _rows(os.path.join(cd, "rv_scores.jsonl"))}
    R = {}
    for nsrc in (None, RV_N["sql"]):
        name = "trained" if nsrc else "base"
        _, _, fr, _ = sel_items("fresh", nsrc, S)
        fval = [x for x in fr if x[0] in val]
        Dp, allfr = rv_items("sql", "fresh", nsrc)   # the prior: every fresh question (labels only, no score needed)
        prior = [(i, s, [{"r": c[0], "calls": c[1], "s": 0.0} for c in cand.values()], dr) for i, s, cand, dr in allfr]
        choose, beta = sel_fit(prior, fval)
        av = ci(sel_auc(fval))
        for sset, tname in SEL_T:
            D, raw, it, miss = sel_items(sset, nsrc, S)
            _, _, itr, _ = sel_items(sset, nsrc, SR, "rev")
            ids, n = sorted(D), 3 * len(D)
            a, ar = sel_auc(it), sel_auc(itr)
            if not a:
                print(f"    SEL {tname} {name}: no scored mixed set (missing scores {miss})", flush=True); continue
            A = ci(a)
            dA = ci({i: a[i] - ar[i] for i in a if i in ar})
            sel, r1, alone, cross, unseen = Counter(), Counter(), Counter(), Counter(), 0
            for x in it:
                i, _, C, dr = x
                c = choose(x)
                unseen += c is None
                sel[i] += (c["r"] if c else dr) - dr
                r1[i] += max(C, key=lambda c: (len(c["calls"]), c["s"]))["r"] - dr
                alone[i] += max(C, key=lambda c: c["s"])["r"] - dr
            for h in (0, 1):   # RV's cross-fitted Bayes on the target's own halves
                half = [x for x in it if zlib.crc32(x[0].encode()) % 2 == h]
                ch, _ = sel_fit(half, half)
                for x in it:
                    if zlib.crc32(x[0].encode()) % 2 != h:
                        c = ch(x)
                        cross[x[0]] += (c["r"] if c else x[3]) - x[3]
            c3 = lambda d: ci({i: d[i] / 3 for i in ids})
            pb, p1 = rv_gauss(raw, A[0] / 100)
            pre = sum(c["pre"] for x in it for c in x[2]) / n
            R[(name, tname)] = r = dict(A=A, dA=dA, sel=c3(sel), cross=c3(cross), bound=100 * pb / n, val=av)
            print(f"    SEL {tname} {name}: {len(raw)} multi-answer fallback question-seeds, missing scores {miss}; within-question AUROC "
                  f"verifier {g([x / 100 for x in A])} (rev {ci(ar)[0] / 100:.3f}; verifier - rev {g([x / 100 for x in dA])}; held-out-"
                  f"database fresh {av[0] / 100:.3f}); fresh-fitted selector (beta {beta:.1f}; {unseen} question-seeds with an unseen "
                  f"structure keep d) - cascade {f(r['sel'])}; cross-fitted Bayes {f(r['cross'])}; bound at the measured AUROC Bayes "
                  f"{100 * pb / n:+.2f}, R1 {100 * p1 / n:+.2f}; R1 with the verifier {f(c3(r1))}; verifier alone {f(c3(alone))}; "
                  f"verifier prefill {pre:.0f} tokens per question-seed", flush=True)
    if len(R) < 6:
        print(f"*** {len(R)} of 6 cells present, not decided"); return
    for name, tag in (("base", "SEL-P2b"), ("trained", "SEL-P2t")):
        X = [R[(name, t)] for _, t in SEL_T]
        up, down = sum(r["sel"][1] > 0 for r in X), sum(r["sel"][2] < 0 for r in X)
        print(f"*** {tag} ({name}: fresh-fitted selector - cascade lower bound > 0 in >= 2 of 3, upper bound < 0 in none): {up} above, "
              f"{down} below -> {'holds' if up >= 2 and down == 0 else 'refuted'}")
    p1 = [R[(nm2, "BIRD dev")]["dA"][1] > 0 for nm2 in ("base", "trained")]
    print(f"*** SEL-P1 (verifier - rev AUROC lower bound > 0 on BIRD dev for both N types): {p1} -> {'holds' if all(p1) else 'refuted'}")
    p3 = sum(abs(r["cross"][0] - r["bound"]) <= 0.7 for r in R.values())
    print(f"*** SEL-P3 (cross-fitted Bayes within 0.7 of the bound in >= 4 of 6): {p3} -> {'holds' if p3 >= 4 else 'refuted'}")
    p4 = [abs(R[(nm2, "BIRD dev")]["A"][0] - R[(nm2, "BIRD dev")]["val"][0]) / 100 for nm2 in ("base", "trained")]
    print(f"*** SEL-P4 (BIRD dev AUROC within 0.05 of the held-out-database fresh AUROC, both N types): differences "
          f"{[round(x, 3) for x in p4]} -> {'holds' if max(p4) <= 0.05 else 'refuted'}")
    cr = sum(R[(nm2, t)]["cross"][1] > 0 for nm2 in ("base", "trained") for _, t in SEL_T)
    print(f"*** cross-fitted Bayes lower bound > 0 in {cr} of 6 cells")


def main_sel_build_pw():
    """addendum SEL-PW: every ordered pair of distinct passing answers in SEL's cells, one query per answer (the first call's in the order
    N, P, d) -> results/conf/sel_req_pw.jsonl (text = query A, text2 = query B)"""
    req, val = {}, sel_val_ids()
    for sset in ("fresh",) + tuple(x for x, _ in SEL_T):
        for nsrc in (None, RV_N["sql"]):
            D, items = rv_items("sql", sset, nsrc)
            for i, s, cand, dr in items:
                if sset == "fresh" and i not in val:
                    continue
                reps = [texts[0] for r, calls, texts in cand.values()]
                for a in reps:
                    for b in reps:
                        if a != b:
                            h = rv_key("sql", sset, i, "pw", [a, b])
                            req[h] = {"h": h, "task": "sql", "sset": sset, "id": i, "kind": "pw", "text": a, "text2": b}
            print(f"SEL-PW build {sset} {nsrc or 'base'}: {len(items)} multi-answer fallback question-seeds; requests so far {len(req)}",
                  flush=True)
    with open(os.path.join(lcm.ROOT, "results", "conf", "sel_req_pw.jsonl"), "w") as f:
        for r in req.values():
            f.write(json.dumps(r) + "\n")
    print(f"SEL-PW build: {len(req)} requests -> results/conf/sel_req_pw.jsonl")


def pw_items(sset, nsrc, S, gen="q8b", peer="q35"):
    """sel_items for SEL-PW: candidate a's s = the mean over the other candidates b of (s(a, b) - s(b, a)) / 2, the order-debiased
    log-odds that a is the right one of the two; pre = the prefill of the ordered pairs a heads (summed over a: every pair once)"""
    D, items = rv_items("sql", sset, nsrc, gen, peer)
    out, miss = [], 0
    for i, sd, cand, dr in items:
        V = list(cand.values())
        reps = [v[2][0] for v in V]
        C = []
        for a in range(len(V)):
            d, pre = [], 0
            for b in range(len(V)):
                if a != b:
                    x, y = S.get(rv_key("sql", sset, i, "pw", [reps[a], reps[b]])), S.get(rv_key("sql", sset, i, "pw", [reps[b], reps[a]]))
                    if x is None or y is None:
                        d = None; break
                    d.append((x["s"] - y["s"]) / 2); pre += x.get("pre", 0)
            if d is None:
                C = None; break
            C.append({"r": V[a][0], "calls": V[a][1], "s": sum(d) / len(d), "pre": pre})
        if C is None:
            miss += 1; continue
        out.append((i, sd, C, dr))
    return D, items, out, miss


def ncols(q):
    """the number of top-level items in the query's first SELECT list (string literals blanked; SEL's mechanism split)"""
    import re
    q = re.sub(r"'[^']*'", "''", q)
    m = re.search(r"\bselect\b", q, re.I)
    if not m:
        return 0
    d, n, i = 0, 1, m.end()
    while i < len(q):
        ch = q[i]
        if ch == "(":
            d += 1
        elif ch == ")":
            d -= 1
        elif d == 0 and ch == ",":
            n += 1
        elif d == 0 and re.match(r"\s(from)\b", q[i:i + 6], re.I):
            break
        i += 1
    return n


def main_sel_pw():
    """addendum SEL-PW. --sel-val-pw n1,n2,...: pooled within-question AUROC of each pairwise checkpoint (and the untrained model, local,
    reported) on the fresh held-out-database questions and the choice. --sel-pw <name>: the targets, against SEL's pointwise verifier
    (sel_s125) on the same question-seeds (SEL-PW-P1..P4)"""
    from analyze_ho3 import ci
    from run_nlopt import _rows
    cd = os.path.join(lcm.ROOT, "results", "conf")
    load = lambda nm: {r["h"]: r for r in _rows(os.path.join(cd, f"sel_scores_{nm}.jsonl"))}
    val = sel_val_ids()
    g = lambda v: f"{v[0] / 100:.3f} [{v[1] / 100:.3f}, {v[2] / 100:.3f}]"
    f = lambda v: f"{v[0]:+.2f} [{v[1]:+.2f}, {v[2]:+.2f}]"
    if "--sel-val-pw" in sys.argv:
        best = None
        for nm in sys.argv[sys.argv.index("--sel-val-pw") + 1].split(","):
            S, pooled, per = load(nm), {}, {}
            for nsrc in (None, RV_N["sql"]):
                _, _, it, miss = pw_items("fresh", nsrc, S)
                a = sel_auc([x for x in it if x[0] in val])
                per[nsrc or "base"] = ci(a) if a else (float("nan"),) * 3
                for i, v in a.items():
                    pooled.setdefault(i, []).append(v)
            if not pooled:
                print(f"SEL-PW val {nm}: no scored mixed set", flush=True); continue
            pa = ci({i: sum(v) / len(v) for i, v in pooled.items()})
            print(f"SEL-PW val {nm}: AUROC base {g(per['base'])}, trained {g(per['q8bcvc1'])}, pooled {g(pa)} ({len(pooled)} questions)",
                  flush=True)
            if nm != "local" and (best is None or pa[0] > best[1]):
                best = (nm, pa[0])
        print(f"*** SEL-PW checkpoint (highest pooled held-out-database AUROC): {best[0]}")
        return
    nm = sys.argv[sys.argv.index("--sel-pw") + 1]
    S, ST = load(nm), load("sel_s125")
    SL = load("local") if os.path.exists(os.path.join(cd, "sel_scores_local.jsonl")) else {}
    R, pool = {}, {}
    for nsrc in (None, RV_N["sql"]):
        name = "trained" if nsrc else "base"
        Dp, allfr = rv_items("sql", "fresh", nsrc)
        prior = [(i, s, [{"r": c[0], "calls": c[1], "s": 0.0} for c in cand.values()], dr) for i, s, cand, dr in allfr]
        cw, bw = sel_fit(prior, [x for x in pw_items("fresh", nsrc, S)[2] if x[0] in val])
        ct, bt = sel_fit(prior, [x for x in sel_items("fresh", nsrc, ST)[2] if x[0] in val])
        for sset, tname in SEL_T:
            D, raw, itw, missw = pw_items(sset, nsrc, S)
            _, _, itt, misst = sel_items(sset, nsrc, ST)
            kw, kt = {(x[0], x[1]): x for x in itw}, {(x[0], x[1]): x for x in itt}
            keys = sorted(set(kw) & set(kt))
            if not keys:
                print(f"    SEL-PW {tname} {name}: no scored question-seed (missing pairwise {missw}, pointwise {misst})", flush=True); continue
            itw, itt = [kw[k] for k in keys], [kt[k] for k in keys]
            aw, at = sel_auc(itw), sel_auc(itt)
            Aw, At = ci(aw), ci(at)
            dA = {i: aw[i] - at[i] for i in aw if i in at}
            ids, n = sorted(D), 3 * len(D)
            sw, stt, cross, unseen = Counter(), Counter(), Counter(), 0
            for x in itw:
                c = cw(x); unseen += c is None
                sw[x[0]] += (c["r"] if c else x[3]) - x[3]
            for x in itt:
                c = ct(x)
                stt[x[0]] += (c["r"] if c else x[3]) - x[3]
            for h in (0, 1):
                half = [x for x in itw if zlib.crc32(x[0].encode()) % 2 == h]
                ch, _ = sel_fit(half, half)
                for x in itw:
                    if zlib.crc32(x[0].encode()) % 2 != h:
                        c = ch(x)
                        cross[x[0]] += (c["r"] if c else x[3]) - x[3]
            c3 = lambda d: ci({i: d.get(i, 0) / 3 for i in ids})
            pb, _ = rv_gauss(raw, Aw[0] / 100)
            txt = {(i, s): [v[2][0] for v in cand.values()] for i, s, cand, _ in raw}
            mech = {"same": {}, "diff": {}}   # per question: pairwise - pointwise ordering of (right, wrong) pairs, by output columns
            for (xw, xt) in zip(itw, itt):
                nc = [ncols(t) for t in txt[(xw[0], xw[1])]]
                Cw, Ct = xw[2], xt[2]
                for a in range(len(Cw)):
                    for b in range(len(Cw)):
                        if Cw[a]["r"] and not Cw[b]["r"]:
                            o = lambda C: (C[a]["s"] > C[b]["s"]) + 0.5 * (C[a]["s"] == C[b]["s"])
                            mech["same" if nc[a] == nc[b] else "diff"].setdefault((name, xw[0]), []).append((o(Cw), o(Ct)))
            al = ""
            if SL:
                _, _, itl, _ = pw_items(sset, nsrc, SL)
                if itl:
                    al = f"; untrained pairwise {ci(sel_auc(itl))[0] / 100:.3f}"
            pre_w = sum(c["pre"] for x in itw for c in x[2]) / n
            pre_t = sum(c["pre"] for x in itt for c in x[2]) / n
            R[(name, tname)] = r = dict(Aw=Aw, At=At, dA=ci(dA), sw=c3(sw), st=c3(stt), d=c3({i: sw[i] - stt[i] for i in ids}),
                                        cross=c3(cross), bound=100 * pb / n, mech=mech)
            for k, v in (("dA", {(tname, i): x for i, x in dA.items()}), ("d", {(tname, i): (sw[i] - stt[i]) / 3 for i in ids})):
                pool.setdefault((name, k), {}).update(v)
            print(f"    SEL-PW {tname} {name}: {len(raw)} multi-answer fallback question-seeds, {len(keys)} scored by both (missing pairwise "
                  f"{missw}, pointwise {misst}); within-question AUROC pairwise {g(Aw)}, pointwise {g(At)}, pairwise - pointwise "
                  f"{g(ci(dA))}{al}; selector - cascade pairwise (beta {bw:.1f}; {unseen} unseen structures keep d) {f(r['sw'])}, pointwise "
                  f"(beta {bt:.1f}) {f(r['st'])}; pairwise - pointwise selector {f(r['d'])}; cross-fitted Bayes (pairwise) "
                  f"{f(r['cross'])}; bound at the pairwise AUROC {100 * pb / n:+.2f}; prefill per question-seed pairwise {pre_w:.0f}, "
                  f"pointwise {pre_t:.0f} tokens", flush=True)
    if len(R) < 6:
        print(f"*** {len(R)} of 6 cells present, not decided"); return
    p1, p2 = [], []
    for name in ("base", "trained"):
        dA, d = ci(pool[(name, "dA")]), ci(pool[(name, "d")])
        print(f"    SEL-PW {name}, three targets pooled: pairwise - pointwise AUROC {g(dA)}; pairwise - pointwise selector {f(d)}")
        p1.append(dA[1] > 0); p2.append((d[1] > 0, d[2] < 0))
    print(f"*** SEL-PW-P1 (pairwise - pointwise AUROC, targets pooled, lower bound > 0 for both N types): {p1} -> "
          f"{'holds' if all(p1) else 'refuted'}")
    up, down = sum(a for a, _ in p2), sum(b for _, b in p2)
    print(f"*** SEL-PW-P2 (pairwise - pointwise selector, targets pooled per N type: lower bound > 0 in >= 1 of 2, upper bound < 0 in none): "
          f"{up} above, {down} below -> {'holds' if up >= 1 and down == 0 else 'refuted'}")
    M = {k: {} for k in ("same", "diff")}
    for name in ("base", "trained"):
        for k in M:
            M[k].update(R[(name, "BIRD dev")]["mech"][k])
    md = {k: ci({q: sum(a - b for a, b in v) / len(v) for q, v in M[k].items()}) for k in M}
    ns = {k: sum(len(v) for v in M[k].values()) for k in M}
    print(f"    SEL-PW BIRD dev (right, wrong) pairs, pairwise - pointwise ordering, per question, N types pooled: same output columns "
          f"{f(md['same'])} ({ns['same']} pairs), different {f(md['diff'])} ({ns['diff']} pairs)")
    p3 = md["same"][0] >= 3 and md["same"][1] > 0 and abs(md["diff"][0]) <= 3
    print(f"*** SEL-PW-P3 (same-column pairs >= +3 points with lower bound > 0, different-column pairs within 3): -> {'holds' if p3 else 'refuted'}")
    p4 = sum(abs(r["cross"][0] - r["bound"]) <= 0.7 for r in R.values())
    print(f"*** SEL-PW-P4 (cross-fitted Bayes within 0.7 of the bound at the pairwise AUROC in >= 4 of 6): {p4} -> "
          f"{'holds' if p4 >= 4 else 'refuted'}")


TC_HO_N = {None: "hoq8b", "q8btcc1": "hoq8btcc1"}   # SEL-TC: the held-out ToolACE quick calls of each N type


def tc_texts(sset, nsrc):
    """{(call type, seed, id): the raw text} of a tool-call cell's calls N, P, SB, T (tcho: the held-out ToolACE rows; else BFCL)"""
    from run_nlopt import _rows
    R = os.path.join(lcm.ROOT, "results", "tc")
    if sset == "tcho":
        src = (("N", TC_HO_N[nsrc], "cheap", "n_text"), ("P", "hoq35", "cheap", "n_text"), ("SB", "hoq8b", "sb", "text"),
               ("T", "hoq8b", "think", "text"))
    else:
        src = (("N", nsrc or "q8b", "cheap", "n_text"), ("P", "q35", "cheap", "n_text"), ("SB", "q8b", "sb", "text"),
               ("T", "q8b", "think", "text"))
    return {(t, s, r["id"]): (r.get(fld) or "").strip() for t, tag, a, fld in src for s in (1, 2, 3) for r in _rows(f"{R}/{tag}_{a}_s{s}.jsonl")}


def tc_items(sset, nsrc):
    """SEL-TC: (questions, [(id, seed, {key: [right, calls, [raw texts], [RV texts]]}, fallback right)]) on RV's fallback question-seeds;
    sset bfcl (non-live + live, RV's texts too) or tcho (the 3,549 held-out ToolACE requests, TRT's set)"""
    if sset == "tcho":
        D, X = quiet(lcm.load_tcho, TC_HO_N[nsrc]), {}
    else:
        k = {"nsrc": nsrc} if nsrc else {}
        D = {**quiet(lcm.load, "tc", "q8b", "q35", "non-live", **k), **quiet(lcm.load, "tc", "q8b", "q35", "live", **k)}
        X = rv_texts("tc", "bfcl", nsrc)
    W = tc_texts(sset, nsrc)
    out = []
    for i, q in D.items():
        for s in (1, 2, 3):
            N, P, SB, T, T2 = lcm.seed_calls(q, s)
            if not N[1] or (P[1] and P[0] is not None and P[0] == N[0]):
                continue
            dn, d, dk = ("SB", SB, ("SB", s)) if SB[1] else (("T", T, ("T", s)) if T[1] else ("T2", T2, ("T", s % 3 + 1)))
            cand = {}
            for nm, x, tk in (("N", N, ("N", s)), ("P", P, ("P", s)), (dn, d, dk)):
                if x[1] and x[0] is not None:
                    c = cand.setdefault(x[0], [bool(x[2]), (), [], []])
                    c[1] += (nm,); c[2].append(W[(tk[0], tk[1], i)]); c[3].append(X.get((tk[0], tk[1], i)))
            if len(cand) >= 2:
                out.append((i, s, cand, bool(d[2])))
    return D, out


def main_sel_build_tc():
    """addendum SEL-TC: the candidates to score -> results/conf/sel_req_tc.jsonl (held-out ToolACE for the checkpoint and beta; BFCL)"""
    req = {}
    for sset in ("tcho", "bfcl"):
        for nsrc in (None, RV_N["tc"]):
            D, items = tc_items(sset, nsrc)
            for i, s, cand, dr in items:
                for r, calls, texts, _ in cand.values():
                    for t in set(texts):
                        h = rv_key("tc", sset, i, "sel", t)
                        req[h] = {"h": h, "task": "tc", "sset": sset, "id": i, "kind": "sel", "text": t}
            print(f"SEL-TC build {sset} {nsrc or 'base'}: {len(D)} requests, {len(items)} multi-answer fallback request-seeds; "
                  f"scoring requests so far {len(req)}", flush=True)
    with open(os.path.join(lcm.ROOT, "results", "conf", "sel_req_tc.jsonl"), "w") as f:
        for r in req.values():
            f.write(json.dumps(r) + "\n")
    print(f"SEL-TC build: {len(req)} requests -> results/conf/sel_req_tc.jsonl")


def tc_sel_items(sset, nsrc, S, rev=None):
    """tc_items with each candidate as sel_items' dict (s: the verifier's mean score over its raw texts; rev: RV's channel score)"""
    D, raw = tc_items(sset, nsrc)
    out, miss = [], 0
    for i, sd, cand, dr in raw:
        C = []
        for r, calls, texts, shows in cand.values():
            x = [S.get(rv_key("tc", sset, i, "sel", t)) for t in texts]
            y = [rev.get(rv_key("tc", "bfcl", i, "rev", t)) for t in shows] if rev is not None else []
            if any(v is None for v in x) or any(v is None for v in y):
                C = None; break
            C.append({"r": r, "calls": calls, "s": sum(v["s"] for v in x) / len(x), "pre": sum(v.get("pre", 0) for v in x),
                      "rev": sum(v["s"] for v in y) / len(y) if y else None})
        if C is None:
            miss += 1; continue
        out.append((i, sd, C, dr))
    return D, [(i, s, {k: [v[0], v[1]] for k, v in c.items()}, dr) for i, s, c, dr in raw], out, miss


def main_sel_tc():
    """addendum SEL-TC. --sel-val-tc n1,n2,...: within-question AUROC of each checkpoint on the held-out ToolACE fallback sets (N types
    pooled) and the choice; --sel-tc <name>: BFCL (SEL-TC-P1..P4)"""
    from analyze_ho3 import ci
    from run_nlopt import _rows
    cd = os.path.join(lcm.ROOT, "results", "conf")
    load = lambda nm: {r["h"]: r for r in _rows(os.path.join(cd, f"sel_scores_{nm}.jsonl"))}
    g = lambda v: f"{v[0]:.3f} [{v[1]:.3f}, {v[2]:.3f}]"
    f = lambda v: f"{v[0]:+.2f} [{v[1]:+.2f}, {v[2]:+.2f}]"
    if "--sel-val-tc" in sys.argv:
        best = None
        for nm in sys.argv[sys.argv.index("--sel-val-tc") + 1].split(","):
            S, per = load(nm), {}
            for nsrc in (None, RV_N["tc"]):
                _, _, it, miss = tc_sel_items("tcho", nsrc, S)
                for i, v in sel_auc(it).items():
                    per.setdefault(nsrc or "base", {})[i] = v; per.setdefault("pooled", {}).setdefault(i, []).append(v)
            if not per.get("pooled"):
                print(f"SEL-TC val {nm}: no scored mixed set", flush=True); continue
            pa = ci({i: sum(v) / len(v) for i, v in per["pooled"].items()})
            print(f"SEL-TC val {nm}: AUROC base {ci(per['base'])[0] / 100:.3f}, trained {ci(per['q8btcc1'])[0] / 100:.3f}, pooled "
                  f"{g([x / 100 for x in pa])} ({len(per['pooled'])} requests)", flush=True)
            if nm != "local" and (best is None or pa[0] > best[1]):
                best = (nm, pa[0])
        print(f"*** SEL-TC checkpoint (highest pooled held-out ToolACE AUROC): {best[0]}")
        return
    nm = sys.argv[sys.argv.index("--sel-tc") + 1]
    S, SR = load(nm), {r["h"]: r for r in _rows(os.path.join(cd, "rv_scores.jsonl"))}
    R = {}
    for nsrc in (None, RV_N["tc"]):
        name = "trained" if nsrc else "base"
        _, raw_ho, ho, _ = tc_sel_items("tcho", nsrc, S)
        prior = [(i, s, [{"r": c[0], "calls": c[1], "s": 0.0} for c in cand.values()], dr) for i, s, cand, dr in raw_ho]
        choose, beta = sel_fit(prior, ho)
        av = ci(sel_auc(ho))
        D, raw, it, miss = tc_sel_items("bfcl", nsrc, S, SR)
        ids, n = sorted(D), 3 * len(D)
        a = sel_auc(it)
        ar = sel_auc([(i, s, [dict(c, s=c["rev"]) for c in C], dr) for i, s, C, dr in it])
        A, dA = ci(a), ci({i: a[i] - ar[i] for i in a if i in ar})
        sel, r1, alone, cross, unseen = Counter(), Counter(), Counter(), Counter(), 0
        for x in it:
            i, _, C, dr = x
            c = choose(x)
            unseen += c is None
            sel[i] += (c["r"] if c else dr) - dr
            r1[i] += max(C, key=lambda c: (len(c["calls"]), c["s"]))["r"] - dr
            alone[i] += max(C, key=lambda c: c["s"])["r"] - dr
        for h in (0, 1):
            half = [x for x in it if zlib.crc32(x[0].encode()) % 2 == h]
            ch, _ = sel_fit(half, half)
            for x in it:
                if zlib.crc32(x[0].encode()) % 2 != h:
                    c = ch(x)
                    cross[x[0]] += (c["r"] if c else x[3]) - x[3]
        c3 = lambda d: ci({i: d[i] / 3 for i in ids})
        pb, p1 = rv_gauss(raw, A[0] / 100)
        pre = sum(c["pre"] for x in it for c in x[2]) / n
        R[name] = r = dict(A=A, dA=dA, sel=c3(sel), cross=c3(cross), bound=100 * pb / n, val=av)
        print(f"    SEL-TC BFCL {name}: {len(raw)} multi-answer fallback request-seeds, missing scores {miss}; within-question AUROC verifier "
              f"{g([x / 100 for x in A])} (rev {ci(ar)[0] / 100:.3f}; verifier - rev {g([x / 100 for x in dA])}; held-out ToolACE "
              f"{av[0] / 100:.3f}); fitted selector (beta {beta:.1f}; {unseen} with an unseen structure keep d) - cascade {f(r['sel'])}; "
              f"cross-fitted Bayes {f(r['cross'])}; bound Bayes {100 * pb / n:+.2f}, R1 {100 * p1 / n:+.2f}; R1 with the verifier "
              f"{f(c3(r1))}; verifier alone {f(c3(alone))}; verifier prefill {pre:.0f} tokens per request-seed", flush=True)
    if len(R) < 2:
        print(f"*** {len(R)} of 2 cells present, not decided"); return
    for name in ("base", "trained"):
        r = R[name]
        print(f"*** SEL-TC-P2{name[0]} (fitted selector - cascade lower bound > 0): {f(r['sel'])} -> {'holds' if r['sel'][1] > 0 else 'refuted'}")
    p1 = [R[nm2]["dA"][1] > 0 for nm2 in ("base", "trained")]
    print(f"*** SEL-TC-P1 (verifier - rev AUROC lower bound > 0, both N types): {p1} -> {'holds' if all(p1) else 'refuted'}")
    p3 = sum(abs(r["cross"][0] - r["bound"]) <= 0.7 for r in R.values())
    print(f"*** SEL-TC-P3 (cross-fitted Bayes within 0.7 of the bound, both): {p3} of 2 -> {'holds' if p3 == 2 else 'refuted'}")
    p4 = [abs(R[nm2]["A"][0] - R[nm2]["val"][0]) / 100 for nm2 in ("base", "trained")]
    print(f"*** SEL-TC-P4 (BFCL AUROC within 0.05 of held-out ToolACE's, both): {[round(x, 3) for x in p4]} -> "
          f"{'holds' if max(p4) <= 0.05 else 'refuted'}")


def main_sel_build_pwtc():
    """addendum SEL-PW-TC: every ordered pair of distinct passing answers in SEL-TC's cells, one text per answer (the first call's in
    the order N, P, d) -> results/conf/sel_req_pwtc.jsonl (held-out ToolACE for the checkpoint and beta; BFCL)"""
    req = {}
    for sset in ("tcho", "bfcl"):
        for nsrc in (None, RV_N["tc"]):
            D, items = tc_items(sset, nsrc)
            for i, s, cand, dr in items:
                reps = [v[2][0] for v in cand.values()]
                for a in reps:
                    for b in reps:
                        if a != b:
                            h = rv_key("tc", sset, i, "pw", [a, b])
                            req[h] = {"h": h, "task": "tc", "sset": sset, "id": i, "kind": "pw", "text": a, "text2": b}
            print(f"SEL-PW-TC build {sset} {nsrc or 'base'}: {len(items)} multi-answer fallback request-seeds; requests so far {len(req)}",
                  flush=True)
    with open(os.path.join(lcm.ROOT, "results", "conf", "sel_req_pwtc.jsonl"), "w") as f:
        for r in req.values():
            f.write(json.dumps(r) + "\n")
    print(f"SEL-PW-TC build: {len(req)} requests -> results/conf/sel_req_pwtc.jsonl")


def pwtc_items(sset, nsrc, S):
    """tc_sel_items for SEL-PW-TC: candidate a's s = the mean over the other candidates b of (s(a, b) - s(b, a)) / 2 (as pw_items);
    also each candidate's answer key (k) and text (t)"""
    D, raw = tc_items(sset, nsrc)
    out, miss = [], 0
    for i, sd, cand, dr in raw:
        K = list(cand)
        reps = [cand[k][2][0] for k in K]
        C = []
        for a in range(len(K)):
            d, pre = [], 0
            for b in range(len(K)):
                if a != b:
                    x, y = S.get(rv_key("tc", sset, i, "pw", [reps[a], reps[b]])), S.get(rv_key("tc", sset, i, "pw", [reps[b], reps[a]]))
                    if x is None or y is None:
                        d = None; break
                    d.append((x["s"] - y["s"]) / 2); pre += x.get("pre", 0)
            if d is None:
                C = None; break
            C.append({"r": cand[K[a]][0], "calls": cand[K[a]][1], "s": sum(d) / len(d), "pre": pre, "k": K[a], "t": reps[a]})
        if C is None:
            miss += 1; continue
        out.append((i, sd, C, dr))
    return D, [(i, s, {k: [v[0], v[1]] for k, v in c.items()}, dr) for i, s, c, dr in raw], out, miss


def pair_kind(ka, kb):
    """SEL-PW-TC-P3's pair types: 'abstain' (one answer is no call), 'same' (the same functions, other argument values), 'other'"""
    un = lambda k: json.loads(k) if k.startswith('"') else k   # BFCL's keys are json.dumps of analyze_tc's calls; tcho's tc_reward.canon
    ka, kb = un(ka), un(kb)
    if "none" in (ka, kb):
        return "abstain"
    name = lambda e: e[0] if isinstance(e, list) else next(iter(e))
    fn = lambda k: sorted(name(json.loads(x)) for x in json.loads(k))
    return "same" if fn(ka) == fn(kb) else "other"


def main_sel_pwtc():
    """addendum SEL-PW-TC. --sel-val-pwtc n1,n2,...: pooled within-question AUROC of each pairwise checkpoint (and local, reported) on
    the held-out ToolACE fallback sets and the choice; --sel-pwtc <name>: BFCL against SEL-TC's pointwise verifier (seltc_s150) on the
    same request-seeds (SEL-PW-TC-P1..P4)"""
    from analyze_ho3 import ci
    from run_nlopt import _rows
    cd = os.path.join(lcm.ROOT, "results", "conf")
    load = lambda nm: {r["h"]: r for r in _rows(os.path.join(cd, f"sel_scores_{nm}.jsonl"))}
    g = lambda v: f"{v[0] / 100:.3f} [{v[1] / 100:.3f}, {v[2] / 100:.3f}]"
    f = lambda v: f"{v[0]:+.2f} [{v[1]:+.2f}, {v[2]:+.2f}]"
    if "--sel-val-pwtc" in sys.argv:
        best = None
        for nm in sys.argv[sys.argv.index("--sel-val-pwtc") + 1].split(","):
            S, pooled, per = load(nm), {}, {}
            for nsrc in (None, RV_N["tc"]):
                _, _, it, miss = pwtc_items("tcho", nsrc, S)
                a = sel_auc(it)
                per[nsrc or "base"] = ci(a) if a else (float("nan"),) * 3
                for i, v in a.items():
                    pooled.setdefault(i, []).append(v)
            if not pooled:
                print(f"SEL-PW-TC val {nm}: no scored mixed set", flush=True); continue
            pa = ci({i: sum(v) / len(v) for i, v in pooled.items()})
            print(f"SEL-PW-TC val {nm}: AUROC base {g(per['base'])}, trained {g(per['q8btcc1'])}, pooled {g(pa)} ({len(pooled)} requests)",
                  flush=True)
            if nm != "local" and (best is None or pa[0] > best[1]):
                best = (nm, pa[0])
        print(f"*** SEL-PW-TC checkpoint (highest pooled held-out ToolACE AUROC): {best[0]}")
        return
    nm = sys.argv[sys.argv.index("--sel-pwtc") + 1]
    S, ST = load(nm), load("seltc_s150")
    SL = load("local") if os.path.exists(os.path.join(cd, "sel_scores_local.jsonl")) else {}
    R, mech = {}, {k: {} for k in ("same", "other", "abstain")}
    for nsrc in (None, RV_N["tc"]):
        name = "trained" if nsrc else "base"
        _, raw_ho, how, _ = pwtc_items("tcho", nsrc, S)
        _, _, hot, _ = tc_sel_items("tcho", nsrc, ST)
        prior = [(i, s, [{"r": c[0], "calls": c[1], "s": 0.0} for c in cand.values()], dr) for i, s, cand, dr in raw_ho]
        cw, bw = sel_fit(prior, how)
        ct, bt = sel_fit(prior, hot)
        D, raw, itw, missw = pwtc_items("bfcl", nsrc, S)
        _, _, itt, misst = tc_sel_items("bfcl", nsrc, ST)
        kw, kt = {(x[0], x[1]): x for x in itw}, {(x[0], x[1]): x for x in itt}
        keys = sorted(set(kw) & set(kt))
        if not keys:
            print(f"    SEL-PW-TC BFCL {name}: no scored request-seed (missing pairwise {missw}, pointwise {misst})", flush=True); continue
        itw, itt = [kw[k] for k in keys], [kt[k] for k in keys]
        aw, at = sel_auc(itw), sel_auc(itt)
        Aw, At = ci(aw), ci(at)
        dA = {i: aw[i] - at[i] for i in aw if i in at}
        ids, n = sorted(D), 3 * len(D)
        sw, stt, cross, unseen = Counter(), Counter(), Counter(), 0
        for x in itw:
            c = cw(x); unseen += c is None
            sw[x[0]] += (c["r"] if c else x[3]) - x[3]
        for x in itt:
            c = ct(x)
            stt[x[0]] += (c["r"] if c else x[3]) - x[3]
        for h in (0, 1):
            half = [x for x in itw if zlib.crc32(x[0].encode()) % 2 == h]
            ch, _ = sel_fit(half, half)
            for x in itw:
                if zlib.crc32(x[0].encode()) % 2 != h:
                    c = ch(x)
                    cross[x[0]] += (c["r"] if c else x[3]) - x[3]
        c3 = lambda d: ci({i: d.get(i, 0) / 3 for i in ids})
        pb, _ = rv_gauss(raw, Aw[0] / 100)
        for xw, xt in zip(itw, itt):   # both lists hold the candidates in tc_items' order
            Cw, Ct = xw[2], xt[2]
            for a in range(len(Cw)):
                for b in range(len(Cw)):
                    if Cw[a]["r"] and not Cw[b]["r"]:
                        o = lambda C: (C[a]["s"] > C[b]["s"]) + 0.5 * (C[a]["s"] == C[b]["s"])
                        mech[pair_kind(Cw[a]["k"], Cw[b]["k"])].setdefault((name, xw[0]), []).append((o(Cw), o(Ct)))
        al = ""
        if SL:
            _, _, itl, _ = pwtc_items("bfcl", nsrc, SL)
            if itl:
                al = f"; untrained pairwise {ci(sel_auc(itl))[0] / 100:.3f}"
        pre_w = sum(c["pre"] for x in itw for c in x[2]) / n
        pre_t = sum(c["pre"] for x in itt for c in x[2]) / n
        R[name] = r = dict(Aw=Aw, At=At, dA=ci(dA), sw=c3(sw), st=c3(stt), d=c3({i: sw[i] - stt[i] for i in ids}), cross=c3(cross),
                           bound=100 * pb / n)
        print(f"    SEL-PW-TC BFCL {name}: {len(raw)} multi-answer fallback request-seeds, {len(keys)} scored by both (missing pairwise "
              f"{missw}, pointwise {misst}); within-question AUROC pairwise {g(Aw)}, pointwise {g(At)}, pairwise - pointwise "
              f"{g(r['dA'])}{al}; selector - cascade pairwise (beta {bw:.1f}; {unseen} unseen structures keep d) {f(r['sw'])}, pointwise "
              f"(beta {bt:.1f}) {f(r['st'])}; pairwise - pointwise selector {f(r['d'])}; cross-fitted Bayes (pairwise) {f(r['cross'])}; "
              f"bound at the pairwise AUROC {100 * pb / n:+.2f}; prefill per request-seed pairwise {pre_w:.0f}, pointwise {pre_t:.0f} tokens",
              flush=True)
    if len(R) < 2:
        print(f"*** {len(R)} of 2 cells present, not decided"); return
    p1 = [R[k]["dA"][1] > 0 for k in ("base", "trained")]
    print(f"*** SEL-PW-TC-P1 (pairwise - pointwise AUROC lower bound > 0, both N types): {p1} -> {'holds' if all(p1) else 'refuted'}")
    up, down = sum(R[k]["d"][1] > 0 for k in R), sum(R[k]["d"][2] < 0 for k in R)
    print(f"*** SEL-PW-TC-P2 (pairwise - pointwise selector: lower bound > 0 in >= 1 of 2 N types, upper bound < 0 in none): {up} above, "
          f"{down} below -> {'holds' if up >= 1 and down == 0 else 'refuted'}")
    md = {k: ci({q: sum(a - b for a, b in v) / len(v) for q, v in M.items()}) if M else (float("nan"),) * 3 for k, M in mech.items()}
    ns = {k: sum(len(v) for v in M.values()) for k, M in mech.items()}
    print("    SEL-PW-TC BFCL (right, wrong) pairs, pairwise - pointwise ordering, per request, N types pooled: " +
          "; ".join(f"{k} {f(md[k])} ({ns[k]} pairs)" for k in ("same", "other", "abstain")))
    p3 = md["same"][0] >= 3 and md["same"][1] > 0
    print(f"*** SEL-PW-TC-P3 (same-function pairs >= +3 points with lower bound > 0): -> {'holds' if p3 else 'refuted'}")
    p4 = sum(abs(r["cross"][0] - r["bound"]) <= 0.7 for r in R.values())
    print(f"*** SEL-PW-TC-P4 (cross-fitted Bayes within 0.7 of the bound at the pairwise AUROC, both): {p4} of 2 -> "
          f"{'holds' if p4 == 2 else 'refuted'}")

SELW_T = (("ob403", "OptiBench's other 403"), ("mamo", "MAMO"))   # SEL-W's targets; DEV_WORD fits the checkpoint, the arm, pi and beta
SELW_N = ("q8b", "q14a")


def w_items(gen, sset, raw=False):
    """SEL-W: (problems, [(id, seed, {key: [right, calls, [VER prompts]]}, fallback right)]) on the word cascade's fallback problem-seeds
    (N passed, gpt-oss-20b's quick program printed another value, >= 2 distinct passing values among N, P and d); sset a development
    set (DEV_WORD), ob403 (OptiBench's other 403 problems, XPEER's fresh run) or mamo; raw (SEL-PW-W): (problem, code, value) in place
    of each VER prompt"""
    from run_nlopt import RES, _rows, problems
    from ver_build import prompt
    b = "optibench" if sset == "ob403" else sset
    D = quiet(ob403, gen, "oss20") if sset == "ob403" else quiet(lcm.load, "word", gen, "oss20", sset)
    Q = {p["id"]: p["q"] for p in quiet(problems, b)}
    th = gen + "ob" if sset == "ob403" else gen
    W = {(t, s, r["id"]): (Q[r["id"]], r.get("code"), r.get("pred")) if raw else prompt(Q[r["id"]], r.get("code"), r.get("pred"))
         for t, tag, a in (("N", gen, "formx"), ("P", "oss20", "formx"), ("SB", th, "formxtb2000"), ("T", th, "formxt"))
         for s in (1, 2, 3) for r in _rows(f"{RES}/opt_{tag}_{b}_{a}_s{s}.jsonl") if r["id"] in D}
    out = []
    for i, q in D.items():
        for s in (1, 2, 3):
            N, P, SB, T, T2 = lcm.seed_calls(q, s)
            if not N[1] or (P[1] and P[0] is not None and P[0] == N[0]):
                continue
            dn, d, dk = ("SB", SB, ("SB", s)) if SB[1] else (("T", T, ("T", s)) if T[1] else ("T2", T2, ("T", s % 3 + 1)))
            cand = {}
            for nm, x, tk in (("N", N, ("N", s)), ("P", P, ("P", s)), (dn, d, dk)):
                if x[1] and x[0] is not None:
                    c = cand.setdefault(x[0], [bool(x[2]), (), []])
                    c[1] += (nm,); c[2].append(W[(tk[0], tk[1], i)])
            if len(cand) >= 2:
                out.append((i, s, cand, bool(d[2])))
    return D, out


def main_sel_build_w():
    """addendum SEL-W: the candidates to score -> results/conf/sel_req_w.jsonl (the development sets, then ob403 and MAMO)"""
    req = {}
    for sset in DEV_WORD + tuple(x for x, _ in SELW_T):
        for gen in SELW_N:
            D, items = w_items(gen, sset)
            for i, s, cand, dr in items:
                for r, calls, texts in cand.values():
                    for t in set(texts):
                        h = rv_key("word", sset, i, "selw", t)
                        req[h] = {"h": h, "task": "word", "sset": sset, "id": i, "kind": "selw", "text": t}
            print(f"SEL-W build {sset} {gen}: {len(D)} problems, {len(items)} multi-answer fallback problem-seeds "
                  f"({100 * len(items) / max(1, 3 * len(D)):.1f}%); scoring requests so far {len(req)}", flush=True)
    with open(os.path.join(lcm.ROOT, "results", "conf", "sel_req_w.jsonl"), "w") as f:
        for r in req.values():
            f.write(json.dumps(r) + "\n")
    print(f"SEL-W build: {len(req)} requests -> results/conf/sel_req_w.jsonl")


def w_sel_items(gen, sset, S):
    """w_items with each candidate as sel_items' dict (s: the verifier's mean score over its programs); problem keys '<sset>/<id>'"""
    D, raw = w_items(gen, sset)
    out, miss = [], 0
    for i, sd, cand, dr in raw:
        C = []
        for r, calls, texts in cand.values():
            x = [S.get(rv_key("word", sset, i, "selw", t)) for t in texts]
            if any(v is None for v in x):
                C = None; break
            C.append({"r": r, "calls": calls, "s": sum(v["s"] for v in x) / len(x), "pre": sum(v.get("pre", 0) for v in x)})
        if C is None:
            miss += 1; continue
        out.append((f"{sset}/{i}", sd, C, dr))
    return D, [(f"{sset}/{i}", s, c, dr) for i, s, c, dr in raw], out, miss


PWW_SPLIT = 28   # SEL-PW-W-P3: the median number of differing program lines over the targets' (right, wrong) pairs, fixed before any score


def main_sel_build_pww():
    """addendum SEL-PW-W: every ordered pair of distinct passing values in SEL-W's cells, one program per value (the first call's in the
    order N, P, d), as one prompt (ver_build.pw_prompt) -> results/conf/sel_req_pww.jsonl (the development sets, then ob403 and MAMO)"""
    from ver_build import pw_prompt
    req = {}
    for sset in DEV_WORD + tuple(x for x, _ in SELW_T):
        for gen in SELW_N:
            D, items = w_items(gen, sset, raw=True)
            for i, s, cand, dr in items:
                reps = [v[2][0] for v in cand.values()]
                for a in reps:
                    for b in reps:
                        if a != b:
                            t = pw_prompt(a[0], a[1:], b[1:])
                            h = rv_key("word", sset, i, "pw", t)
                            req[h] = {"h": h, "task": "word", "sset": sset, "id": i, "kind": "pw", "text": t}
            print(f"SEL-PW-W build {sset} {gen}: {len(items)} multi-answer fallback problem-seeds; requests so far {len(req)}", flush=True)
    with open(os.path.join(lcm.ROOT, "results", "conf", "sel_req_pww.jsonl"), "w") as f:
        for r in req.values():
            f.write(json.dumps(r) + "\n")
    print(f"SEL-PW-W build: {len(req)} requests -> results/conf/sel_req_pww.jsonl")


def pww_items(gen, sset, S):
    """w_sel_items for SEL-PW-W: candidate a's s = the mean over the other candidates b of (s(a, b) - s(b, a)) / 2 (as pw_items); also
    each candidate's representative program (code)"""
    from ver_build import pw_prompt
    D, raw = w_items(gen, sset, raw=True)
    out, miss = [], 0
    for i, sd, cand, dr in raw:
        V = list(cand.values())
        reps = [v[2][0] for v in V]
        C = []
        for a in range(len(V)):
            d, pre = [], 0
            for b in range(len(V)):
                if a != b:
                    x = S.get(rv_key("word", sset, i, "pw", pw_prompt(reps[a][0], reps[a][1:], reps[b][1:])))
                    y = S.get(rv_key("word", sset, i, "pw", pw_prompt(reps[b][0], reps[b][1:], reps[a][1:])))
                    if x is None or y is None:
                        d = None; break
                    d.append((x["s"] - y["s"]) / 2); pre += x.get("pre", 0)
            if d is None:
                C = None; break
            C.append({"r": V[a][0], "calls": V[a][1], "s": sum(d) / len(d), "pre": pre, "code": reps[a][1] or ""})
        if C is None:
            miss += 1; continue
        out.append((f"{sset}/{i}", sd, C, dr))
    return D, [(f"{sset}/{i}", s, {k: [v[0], v[1]] for k, v in c.items()}, dr) for i, s, c, dr in raw], out, miss


def main_sel_pww():
    """addendum SEL-PW-W. --sel-val-pww n1,n2,...: pooled within-question AUROC of each pairwise checkpoint on the development sets'
    fallback sets and the choice; --sel-pww <name>: the targets against SEL-W's V2 (selw_s50, the same loss and programs one at a time)
    on the same problem-seeds (SEL-PW-W-P1..P4)"""
    import difflib
    from analyze_ho3 import ci
    from run_nlopt import _rows
    cd = os.path.join(lcm.ROOT, "results", "conf")
    load = lambda nm: {r["h"]: r for r in _rows(os.path.join(cd, f"sel_scores_{nm}.jsonl"))}
    g = lambda v: f"{v[0] / 100:.3f} [{v[1] / 100:.3f}, {v[2] / 100:.3f}]"
    f = lambda v: f"{v[0]:+.2f} [{v[1]:+.2f}, {v[2]:+.2f}]"

    def dev(S, gen, fn):   # (prior items: every development fallback set with its labels, scored items)
        pr, it = [], []
        for b in DEV_WORD:
            _, raw, x, _ = fn(gen, b, S)
            pr += [(i, s, [{"r": c[0], "calls": c[1], "s": 0.0} for c in cand.values()], dr) for i, s, cand, dr in raw]; it += x
        return pr, it
    if "--sel-val-pww" in sys.argv:
        best = None
        for nm in sys.argv[sys.argv.index("--sel-val-pww") + 1].split(","):
            S, pooled, per = load(nm), {}, {}
            for gen in SELW_N:
                a = sel_auc(dev(S, gen, pww_items)[1])
                per[gen] = ci(a) if a else (float("nan"),) * 3
                for i, v in a.items():
                    pooled.setdefault(i, []).append(v)
            if not pooled:
                print(f"SEL-PW-W val {nm}: no scored mixed set", flush=True); continue
            pa = ci({i: sum(v) / len(v) for i, v in pooled.items()})
            print(f"SEL-PW-W val {nm}: AUROC q8b {g(per['q8b'])}, q14a {g(per['q14a'])}, pooled {g(pa)} ({len(pooled)} problems)", flush=True)
            if nm != "local" and (best is None or pa[0] > best[1]):
                best = (nm, pa[0])
        print(f"*** SEL-PW-W checkpoint (highest pooled development AUROC): {best[0]}")
        return
    nm = sys.argv[sys.argv.index("--sel-pww") + 1]
    S, ST = load(nm), load("selw_s50")
    SL = load("localw") if os.path.exists(os.path.join(cd, "sel_scores_localw.jsonl")) else {}   # the untrained model (SEL_ALIAS local=localw)
    R, pool, mech = {}, {}, {"small": {}, "large": {}}
    U = lambda r, t: 100 * float(r) - lcm.LAM * t / 1000
    for gen in SELW_N:
        cw, bw = sel_fit(*dev(S, gen, pww_items))
        ct, bt = sel_fit(*dev(ST, gen, w_sel_items))
        for sset, tname in SELW_T:
            D, raw, itw, missw = pww_items(gen, sset, S)
            _, _, itt, misst = w_sel_items(gen, sset, ST)
            kw, kt = {(x[0], x[1]): x for x in itw}, {(x[0], x[1]): x for x in itt}
            keys = sorted(set(kw) & set(kt))
            if not keys:
                print(f"    SEL-PW-W {tname} {gen}: no scored problem-seed (missing pairwise {missw}, pointwise {misst})", flush=True); continue
            itw, itt = [kw[k] for k in keys], [kt[k] for k in keys]
            aw, at = sel_auc(itw), sel_auc(itt)
            Aw, At = ci(aw), ci(at)
            dA = {i: aw[i] - at[i] for i in aw if i in at}
            ids, n = [f"{sset}/{i}" for i in sorted(D)], 3 * len(D)
            sw, stt, cross, pipe, unseen, ch = Counter(), Counter(), Counter(), Counter(), 0, {}
            for x in itw:
                c = cw(x); unseen += c is None
                sw[x[0]] += (c["r"] if c else x[3]) - x[3]
                ch[(x[0], x[1])] = c["r"] if c else x[3]
            for x in itt:
                c = ct(x)
                stt[x[0]] += (c["r"] if c else x[3]) - x[3]
            for h in (0, 1):
                half = [x for x in itw if zlib.crc32(x[0].encode()) % 2 == h]
                chh, _ = sel_fit(half, half)
                for x in itw:
                    if zlib.crc32(x[0].encode()) % 2 != h:
                        c = chh(x)
                        cross[x[0]] += (c["r"] if c else x[3]) - x[3]
            for i, q in D.items():   # the whole pipeline (cascade + pairwise choice) against Qwen's default SB->T->T
                k = f"{sset}/{i}"
                for sd in (1, 2, 3):
                    sc = lcm.seed_calls(q, sd)
                    r, t = lcm.fixed("cascade", sc)
                    r0, t0 = lcm.fixed("SB->T->T", sc)
                    pipe[k] += (U(ch.get((k, sd), r), t) - U(r0, t0)) / 300
            for xw in itw:   # (right, wrong) pairs by how many program lines differ (difflib), split at PWW_SPLIT
                Cw, Ct = xw[2], kt[(xw[0], xw[1])][2]
                for a in range(len(Cw)):
                    for b in range(len(Cw)):
                        if Cw[a]["r"] and not Cw[b]["r"]:
                            nd = sum(1 for l in difflib.ndiff(Cw[a]["code"].splitlines(), Cw[b]["code"].splitlines()) if l[:2] in ("+ ", "- "))
                            o = lambda C: (C[a]["s"] > C[b]["s"]) + 0.5 * (C[a]["s"] == C[b]["s"])
                            mech["small" if nd <= PWW_SPLIT else "large"].setdefault(xw[0], []).append((o(Cw), o(Ct)))
            c3 = lambda d: ci({i: d.get(i, 0) / 3 for i in ids})
            pb, _ = rv_gauss(raw, Aw[0] / 100)
            al = ""
            if SL:
                _, _, itl, _ = pww_items(gen, sset, SL)
                if itl:
                    al = f"; untrained pairwise {ci(sel_auc(itl))[0] / 100:.3f}"
            pre_w = sum(c["pre"] for x in itw for c in x[2]) / n
            pre_t = sum(c["pre"] for x in itt for c in x[2]) / n
            R[(gen, sset)] = r = dict(Aw=Aw, At=At, dA=ci(dA), sw=c3(sw), st=c3(stt), d=c3({i: sw[i] - stt[i] for i in ids}),
                                      cross=c3(cross), bound=100 * pb / n, pipe=ci({i: pipe[i] for i in ids}))
            pool.setdefault("dA", {}).update({(gen, i): v for i, v in dA.items()})
            print(f"    SEL-PW-W {tname} {gen}: {len(raw)} multi-answer fallback problem-seeds of {n}, {len(keys)} scored by both (missing "
                  f"pairwise {missw}, pointwise {misst}); within-question AUROC pairwise {g(Aw)}, pointwise (V2) {g(At)}, pairwise - V2 "
                  f"{g(r['dA'])}{al}; selector - cascade pairwise (beta {bw:.1f}; {unseen} unseen structures keep d) {f(r['sw'])}, V2 (beta "
                  f"{bt:.1f}) {f(r['st'])}; pairwise - V2 selector {f(r['d'])}; cross-fitted Bayes (pairwise) {f(r['cross'])}; bound at the "
                  f"pairwise AUROC {100 * pb / n:+.2f}; pipeline - SB->T->T {f(r['pipe'])}; prefill per problem-seed pairwise {pre_w:.0f}, "
                  f"V2 {pre_t:.0f} tokens", flush=True)
    cells = [(gen, sset) for gen in SELW_N for sset, _ in SELW_T]
    if any(c not in R for c in cells):
        print(f"*** {len(R)} of 4 cells present, not decided"); return
    p1 = ci(pool["dA"])
    print(f"*** SEL-PW-W-P1 (pairwise - V2 within-question AUROC, the four cells pooled, lower bound > 0): {g(p1)} -> "
          f"{'holds' if p1[1] > 0 else 'refuted'}")
    up, down = sum(R[c]["sw"][1] > 0 for c in cells), sum(R[c]["sw"][2] < 0 for c in cells)
    print(f"*** SEL-PW-W-P2 (pairwise selector - cascade lower bound > 0 in >= 2 of 4, upper bound < 0 in none): {up} above, {down} below "
          f"-> {'holds' if up >= 2 and down == 0 else 'refuted'}")
    md = {k: ci({q: sum(a - b for a, b in v) / len(v) for q, v in M.items()}) if M else (float("nan"),) * 3 for k, M in mech.items()}
    ns = {k: sum(len(v) for v in M.values()) for k, M in mech.items()}
    print(f"    SEL-PW-W (right, wrong) pairs, pairwise - V2 ordering, per problem, the four cells pooled: <= {PWW_SPLIT} lines differ "
          f"{f(md['small'])} ({ns['small']} pairs), more {f(md['large'])} ({ns['large']} pairs)")
    p3 = md["small"][0] >= 5 and md["small"][1] > 0
    print(f"*** SEL-PW-W-P3 (pairs whose programs differ in <= {PWW_SPLIT} lines: pairwise - V2 ordering >= +5 points, lower bound > 0): -> "
          f"{'holds' if p3 else 'refuted'}")
    p4 = sum(abs(R[c]["cross"][0] - R[c]["bound"]) <= 0.7 for c in cells)
    print(f"*** SEL-PW-W-P4 (cross-fitted Bayes within 0.7 of the bound at the pairwise AUROC in >= 3 of 4): {p4} -> "
          f"{'holds' if p4 >= 3 else 'refuted'}")

def main_sel_w():
    """addendum SEL-W. --sel-val-w n1,n2,...: within-question AUROC of each checkpoint on the development sets' fallback sets (both N
    types pooled) and the choice; --sel-w <V2's checkpoint>: the arms V0 (local: Qwen3-8B with VER's prompt, untrained), V1 (ver_v1:
    VER's pointwise adapter) and V2, the arm with the highest development AUROC, the targets (SEL-W-P1..P4)"""
    from analyze_ho3 import ci
    from run_nlopt import _rows
    cd = os.path.join(lcm.ROOT, "results", "conf")
    load = lambda nm: {r["h"]: r for r in _rows(os.path.join(cd, f"sel_scores_{nm}.jsonl"))}
    g = lambda v: f"{v[0]:.3f} [{v[1]:.3f}, {v[2]:.3f}]"
    f = lambda v: f"{v[0]:+.2f} [{v[1]:+.2f}, {v[2]:+.2f}]"

    def dev(S, gen):   # (prior items: every development fallback set with its labels, scored items)
        pr, it = [], []
        for b in DEV_WORD:
            _, raw, x, _ = w_sel_items(gen, b, S)
            pr += [(i, s, [{"r": c[0], "calls": c[1], "s": 0.0} for c in cand.values()], dr) for i, s, cand, dr in raw]; it += x
        return pr, it

    def dev_auc(S):
        per = {}
        for gen in SELW_N:
            for i, v in sel_auc(dev(S, gen)[1]).items():
                per.setdefault(gen, {})[i] = v; per.setdefault("pooled", {}).setdefault(i, []).append(v)
        return per, ci({i: sum(v) / len(v) for i, v in per.get("pooled", {}).items()}) if per.get("pooled") else None
    if "--sel-val-w" in sys.argv:
        best = None
        for nm in sys.argv[sys.argv.index("--sel-val-w") + 1].split(","):
            per, pa = dev_auc(load(nm))
            if pa is None:
                print(f"SEL-W val {nm}: no scored mixed set", flush=True); continue
            print(f"SEL-W val {nm}: AUROC q8b {ci(per['q8b'])[0] / 100:.3f}, q14a {ci(per['q14a'])[0] / 100:.3f}, pooled "
                  f"{g([x / 100 for x in pa])} ({len(per['pooled'])} problems)", flush=True)
            if nm not in ("local", "ver_v1") and (best is None or pa[0] > best[1]):
                best = (nm, pa[0])
        print(f"*** SEL-W checkpoint (highest pooled development AUROC): {best[0]}")
        return
    v2 = sys.argv[sys.argv.index("--sel-w") + 1]
    arms = (("V0", "local"), ("V1", "ver_v1"), ("V2", v2))
    SS = {a: load(nm) for a, nm in arms}
    dA = {a: dev_auc(SS[a])[1] for a, _ in arms}
    for a, nm in arms:
        print(f"SEL-W development AUROC {a} ({nm}): {g([x / 100 for x in dA[a]])}", flush=True)
    chosen = max((a for a, _ in arms), key=lambda a: dA[a][0])
    print(f"*** SEL-W arm (highest pooled development AUROC): {chosen}", flush=True)
    R, Aq = {}, {}
    for a, nm in arms:
        for gen in SELW_N:
            prior, fit = dev(SS[a], gen)
            choose, beta = sel_fit(prior, fit)
            choose0, _ = sel_fit(prior, [])   # beta 0: the development prior alone (who proposed which answer), no score
            for sset, tname in SELW_T:
                D, raw, it, miss = w_sel_items(gen, sset, SS[a])
                ids, n = [f"{sset}/{i}" for i in sorted(D)], 3 * len(D)
                au = sel_auc(it)
                Aq[(a, gen, sset)] = au
                if not au:
                    print(f"    SEL-W {tname} {gen} {a}: no scored mixed set (missing scores {miss})", flush=True); continue
                A = ci(au)
                sel, alone, cross, pipe, casc, unseen = Counter(), Counter(), Counter(), Counter(), Counter(), 0
                ch, prio = {}, Counter()
                for x in it:
                    i, sd, C, dr = x
                    c, c0 = choose(x), choose0(x)
                    unseen += c is None
                    sel[i] += (c["r"] if c else dr) - dr
                    prio[i] += (c0["r"] if c0 else dr) - dr
                    alone[i] += max(C, key=lambda c: c["s"])["r"] - dr
                    ch[(i, sd)] = c["r"] if c else dr
                for h in (0, 1):
                    half = [x for x in it if zlib.crc32(x[0].encode()) % 2 == h]
                    chh, _ = sel_fit(half, half)
                    for x in it:
                        if zlib.crc32(x[0].encode()) % 2 != h:
                            c = chh(x)
                            cross[x[0]] += (c["r"] if c else x[3]) - x[3]
                U = lambda r, t: 100 * float(r) - lcm.LAM * t / 1000
                acc = tok = acc0 = tok0 = 0
                for i, q in D.items():
                    k = f"{sset}/{i}"
                    for sd in (1, 2, 3):
                        sc = lcm.seed_calls(q, sd)
                        r, t = lcm.fixed("cascade", sc)
                        r0, t0 = lcm.fixed("SB->T->T", sc)
                        r2 = ch.get((k, sd), r)
                        pipe[k] += (U(r2, t) - U(r0, t0)) / 300; casc[k] += (U(r, t) - U(r0, t0)) / 300
                        acc += r2; tok += t; acc0 += r0; tok0 += t0
                c3 = lambda d: ci({i: d[i] / 3 for i in ids})
                pb, p1 = rv_gauss(raw, A[0] / 100)
                pre = sum(c["pre"] for x in it for c in x[2]) / n
                R[(a, gen, sset)] = r = dict(A=A, sel=c3(sel), cross=c3(cross), bound=100 * pb / n, d0={k: sel[k] - prio[k] for k in ids})
                print(f"    SEL-W {tname} {gen} {a}: {len(raw)} multi-answer fallback problem-seeds of {n}, missing scores {miss}; "
                      f"within-question AUROC {g([x / 100 for x in A])}; fitted selector (beta {beta:.1f}; {unseen} with an unseen structure "
                      f"keep d) - cascade {f(r['sel'])}; the prior alone - cascade {f(c3(prio))}; selector - the prior alone "
                      f"{f(c3(r['d0']))}; cross-fitted Bayes {f(r['cross'])}; bound Bayes {100 * pb / n:+.2f}, R1 "
                      f"{100 * p1 / n:+.2f}; verifier alone {f(c3(alone))}; pipeline {100 * acc / n:.1f}% at {tok / n / 1000:.2f}k vs "
                      f"SB->T->T {100 * acc0 / n:.1f}% at {tok0 / n / 1000:.2f}k: pipeline - SB->T->T {f(ci(pipe))} (cascade alone "
                      f"{f(ci(casc))}); verifier prefill {pre:.0f} tokens per problem-seed", flush=True)
    cells = [(gen, sset) for gen in SELW_N for sset, _ in SELW_T]
    if any((a, gen, sset) not in R for a, _ in arms for gen, sset in cells):
        print("*** not every cell present, not decided"); return
    d12 = {}
    for gen, sset in cells:
        A1, A2 = Aq[("V1", gen, sset)], Aq[("V2", gen, sset)]
        for i in A2:
            if i in A1:
                d12.setdefault(i, []).append(A2[i] - A1[i])
    p1 = ci({i: sum(v) / len(v) for i, v in d12.items()})
    print(f"*** SEL-W-P1 (V2 - V1 within-question AUROC on the targets, pooled, lower bound > 0): {g([x / 100 for x in p1])} -> "
          f"{'holds' if p1[1] > 0 else 'refuted'}")
    for tag, a in (("SEL-W-P2", chosen), ("SEL-W-P4", "V0")):
        X = [R[(a, gen, sset)] for gen, sset in cells]
        up, down = sum(r["sel"][1] > 0 for r in X), sum(r["sel"][2] < 0 for r in X)
        print(f"*** {tag} ({a}: fitted selector - cascade lower bound > 0 in >= 2 of 4, upper bound < 0 in none): {up} above, "
              f"{down} below -> {'holds' if up >= 2 and down == 0 else 'refuted'}")
    p3 = sum(abs(R[(chosen, gen, sset)]["cross"][0] - R[(chosen, gen, sset)]["bound"]) <= 0.7 for gen, sset in cells)
    print(f"*** SEL-W-P3 ({chosen}: cross-fitted Bayes within 0.7 of the bound in >= 3 of 4): {p3} -> {'holds' if p3 >= 3 else 'refuted'}")
    p5 = []
    for gen in SELW_N:   # the score's own share: selector - the prior alone, both targets pooled per N type
        d = {k: v for sset, _ in SELW_T for k, v in R[(chosen, gen, sset)]["d0"].items()}
        p5.append(ci({k: v / 3 for k, v in d.items()}))
        print(f"    SEL-W {gen} {chosen}: selector - the prior alone, both targets pooled {f(p5[-1])}")
    print(f"*** SEL-W-P5 ({chosen}: selector - the prior alone, pooled per N type, lower bound > 0 for both): "
          f"{'holds' if all(x[1] > 0 for x in p5) else 'refuted'}")


def tc2_cells(sset, nsrc):
    """SEL-TC2: (requests, {(id, seed): the five calls' texts}) — N, P, SB, T and the retry T (T at the next seed), as lcm.seed_calls"""
    if sset == "tcho":
        D = quiet(lcm.load_tcho, TC_HO_N[nsrc])
    else:
        k = {"nsrc": nsrc} if nsrc else {}
        D = {**quiet(lcm.load, "tc", "q8b", "q35", "non-live", **k), **quiet(lcm.load, "tc", "q8b", "q35", "live", **k)}
    W = tc_texts(sset, nsrc)
    X = {(i, s): [W.get((t, ss, i), "") for t, ss in (("N", s), ("P", s), ("SB", s), ("T", s), ("T", s % 3 + 1))] for i in D for s in (1, 2, 3)}
    return D, X


def main_sel_build_tc2():
    """addendum SEL-TC2: every passing text of the five calls on request-seeds with >= 2 distinct passing answers -> sel_req_tc2.jsonl"""
    req = {}
    for sset in ("tcho", "bfcl"):
        for nsrc in (None, RV_N["tc"]):
            D, X = tc2_cells(sset, nsrc)
            m = 0
            for i, q in D.items():
                for s in (1, 2, 3):
                    sc = lcm.seed_calls(q, s)
                    keys = {c[0] for c in sc if c[1] and c[0] is not None}
                    if len(keys) < 2:
                        continue
                    m += 1
                    for j, c in enumerate(sc):
                        if c[1] and c[0] is not None:
                            h = rv_key("tc", sset, i, "sel", X[(i, s)][j])
                            req[h] = {"h": h, "task": "tc", "sset": sset, "id": i, "kind": "sel", "text": X[(i, s)][j]}
            print(f"SEL-TC2 build {sset} {nsrc or 'base'}: {len(D)} requests, {m} request-seeds with >= 2 passing answers; "
                  f"scoring requests so far {len(req)}", flush=True)
    with open(os.path.join(lcm.ROOT, "results", "conf", "sel_req_tc2.jsonl"), "w") as f:
        for r in req.values():
            f.write(json.dumps(r) + "\n")
    print(f"SEL-TC2 build: {len(req)} requests -> results/conf/sel_req_tc2.jsonl")


def tc2_run(P, sc, txt, S, sset, i, beta=None, sd=1.0, task="tc"):
    """the planner P on one request-seed; at its stop, where >= 2 passing answers were seen and every one is scored, the answer with
    the highest logit P(right | pattern) + beta z (z: the verifier's mean score over the answer's calls, centred in the set, / sd);
    beta None: the planner's own choice. Returns (right, tokens, seen, the scored stop set or None)"""
    from lcm_bound import project
    obs, right = full(sc)
    calls, tok = frozenset(), 0
    while True:
        pat, rt = project(obs, right, calls)
        if pat not in P.n:
            return None
        P.value(pat)
        kind, arg = P.act[pat]
        if kind != "stop":
            calls = calls | {arg}; tok += sc[arg][3]; continue
        G = {}
        for j in sorted(calls):
            e = pat[j]
            if e is not None and e[0] != "X" and e[1]:
                G.setdefault(e[0], []).append(j)
        C = None
        if len(G) >= 2:
            sv = {g: [S.get(rv_key(task, sset, i, "sel", txt[j])) for j in js] for g, js in G.items()}
            if all(v is not None for x in sv.values() for v in x):
                n = P.n[pat]
                C = [{"g": g, "lp": math.log((P.r.get((pat, g), 0) + 0.5) / (n + 1) / max(1e-3, 1 - (P.r.get((pat, g), 0) + 0.5) / (n + 1))),
                      "s": sum(v["s"] for v in x) / len(x), "r": g in rt} for g, x in sv.items()]
        if beta is None or C is None:
            return ((arg in rt) if arg is not None else False), tok, True, C
        mu = sum(c["s"] for c in C) / len(C)
        c = max(C, key=lambda c: c["lp"] + beta * (c["s"] - mu) / sd)
        return c["r"], tok, True, C


def main_sel_tc2():
    """addendum SEL-TC2 (--sel-tc2 <verifier name>): TL's planner (fitted on the held-out ToolACE requests) with the verifier choosing at
    its stop, against the planner alone, SEL-TC's pipeline (the cascade with the verifier at its fallback) and the default, on BFCL"""
    from analyze_ho3 import ci
    from run_nlopt import _rows
    nm = sys.argv[sys.argv.index("--sel-tc2") + 1]
    S = {r["h"]: r for r in _rows(os.path.join(lcm.ROOT, "results", "conf", f"sel_scores_{nm}.jsonl"))}
    f = lambda v: f"{v[0]:+.2f} [{v[1]:+.2f}, {v[2]:+.2f}]"
    U = lambda r, t: 100 * float(r) - LAM * t / 1000
    R = {}
    for nsrc in (None, RV_N["tc"]):
        name = "trained" if nsrc else "base"
        Dh, Xh = tc2_cells("tcho", nsrc)
        sch = [(i, s, lcm.seed_calls(q, s)) for i, q in Dh.items() for s in (1, 2, 3)]
        tok = [sum(sc[j][3] for _, _, sc in sch) / len(sch) for j in range(5)]
        P = Supervised([full(sc) for _, _, sc in sch], tok)
        sets = [x[3] for i, s, sc in sch for x in [tc2_run(P, sc, Xh[(i, s)], S, "tcho", i)] if x and x[3]]
        dv = [c["s"] - sum(d["s"] for d in C) / len(C) for C in sets for c in C]
        sd = (sum(x * x for x in dv) / max(1, len(dv))) ** 0.5 or 1.0

        def ll(b):
            t = 0.0
            for C in sets:
                mu = sum(c["s"] for c in C) / len(C)
                for c in C:
                    z = c["lp"] + b * (c["s"] - mu) / sd
                    t += -math.log1p(math.exp(-z)) if c["r"] else -math.log1p(math.exp(min(z, 700)))
            return t
        beta = max((b / 10 for b in range(0, 41)), key=ll)
        # SEL-TC's pipeline on BFCL: the cascade, the fitted selector at its fallback (as main_sel_tc)
        _, raw_ho, ho, _ = tc_sel_items("tcho", nsrc, S)
        choose, beta1 = sel_fit([(i, s, [{"r": c[0], "calls": c[1], "s": 0.0} for c in cand.values()], dr) for i, s, cand, dr in raw_ho], ho)
        _, _, it, _ = tc_sel_items("bfcl", nsrc, S)
        selc = {(x[0], x[1]): choose(x) for x in it}
        Db, Xb = tc2_cells("bfcl", nsrc)
        ids = sorted(Db)
        acc, kt, Uq, unseen, nset = Counter(), Counter(), {k: Counter() for k in ("comb", "plan", "sel", "cascade", "default")}, 0, 0
        for i in ids:
            for s in (1, 2, 3):
                sc = lcm.seed_calls(Db[i], s)
                rc, tc_ = lcm.fixed("cascade", sc)
                c = selc.get((i, s))
                rs = c["r"] if c else rc
                out = {"cascade": (rc, tc_), "sel": (rs, tc_), "default": lcm.fixed("SB->T->T", sc)}
                a = tc2_run(P, sc, Xb[(i, s)], S, "bfcl", i, beta, sd)
                b = tc2_run(P, sc, Xb[(i, s)], S, "bfcl", i)
                if a is None:   # a pattern the planner never saw: SEL-TC's outcome
                    unseen += 1; out["comb"] = out["plan"] = (rs, tc_)
                else:
                    out["comb"], out["plan"] = a[:2], b[:2]; nset += a[3] is not None
                for k, (r, t) in out.items():
                    acc[k] += r; kt[k] += t; Uq[k][i] += U(r, t) / 300
        n = 3 * len(ids)
        d = lambda x, y: ci({i: Uq[x][i] - Uq[y][i] for i in ids})
        R[name] = r = {k: d("comb", k) for k in ("plan", "sel", "cascade", "default")}
        r["sel_vs_plan"] = d("sel", "plan")
        print(f"    SEL-TC2 BFCL {name}: beta {beta:.1f} (sd {sd:.2f}, {len(sets)} held-out stop sets); " + "; ".join(
            f"{k} {100 * acc[k] / n:.1f}% at {kt[k] / n / 1000:.2f}k" for k in ("comb", "plan", "sel", "cascade", "default")) +
            f"; planner stops with a scored set on {nset}, unseen patterns {unseen} of {n}", flush=True)
        print(f"    SEL-TC2 BFCL {name}: combined - planner {f(r['plan'])}; combined - SEL-TC pipeline {f(r['sel'])}; combined - cascade "
              f"{f(r['cascade'])}; combined - default {f(r['default'])}; SEL-TC pipeline - planner {f(r['sel_vs_plan'])}", flush=True)
    if len(R) < 2:
        print("*** not every cell present, not decided"); return
    p1 = [R[k]["plan"][1] > 0 for k in ("base", "trained")]
    print(f"*** SEL-TC2-P1 (combined - planner lower bound > 0, both N types): {p1} -> {'holds' if all(p1) else 'refuted'}")
    for k in ("trained", "base"):
        print(f"*** SEL-TC2-P2{k[0]} ({k}: combined - SEL-TC pipeline lower bound > 0): {f(R[k]['sel'])} -> "
              f"{'holds' if R[k]['sel'][1] > 0 else 'refuted'}")


SELG_GEN = ("q14a", "q35", "oss20")   # addendum SEL-G: other generators of the SQL cascade, each with its pre-registered peer (PEER)


def main_sel_build_g():
    """addendum SEL-G: the candidates of the other generators' SQL fallback cells -> results/conf/sel_req_g.jsonl"""
    req, val = {}, sel_val_ids()
    for gen in SELG_GEN:
        for sset in ("fresh",) + tuple(x for x, _ in SEL_T):
            D, items = rv_items("sql", sset, None, gen, PEER[gen])
            for i, s, cand, dr in items:
                if sset == "fresh" and i not in val:
                    continue
                for r, calls, texts in cand.values():
                    for t in set(texts):
                        h = rv_key("sql", sset, i, "sel", t)
                        req[h] = {"h": h, "task": "sql", "sset": sset, "id": i, "kind": "sel", "text": t}
            print(f"SEL-G build {gen}<-{PEER[gen]} {sset}: {len(items)} multi-answer fallback question-seeds; requests so far {len(req)}",
                  flush=True)
    with open(os.path.join(lcm.ROOT, "results", "conf", "sel_req_g.jsonl"), "w") as f:
        for r in req.values():
            f.write(json.dumps(r) + "\n")
    print(f"SEL-G build: {len(req)} requests -> results/conf/sel_req_g.jsonl")


def main_sel_g():
    """addendum SEL-G (--sel-g <SEL's checkpoint>): SEL's verifier and selector (pi on the generator's fresh questions, beta on the
    held-out-database ones) at the SQL fallback of Qwen3-14B-AWQ, Qwen3.5-9B and gpt-oss-20b (SEL-G-P1, P2)"""
    from analyze_ho3 import ci
    from run_nlopt import _rows
    nm = sys.argv[sys.argv.index("--sel-g") + 1]
    S = {r["h"]: r for r in _rows(os.path.join(lcm.ROOT, "results", "conf", f"sel_scores_{nm}.jsonl"))}
    val = sel_val_ids()
    g = lambda v: f"{v[0]:.3f} [{v[1]:.3f}, {v[2]:.3f}]"
    f = lambda v: f"{v[0]:+.2f} [{v[1]:+.2f}, {v[2]:+.2f}]"
    U = lambda r, t: 100 * float(r) - LAM * t / 1000
    R = {}
    for gen in SELG_GEN:
        peer = PEER[gen]
        _, _, fr, _ = sel_items("fresh", None, S, "sel", gen, peer)
        fval = [x for x in fr if x[0] in val]
        _, allfr = rv_items("sql", "fresh", None, gen, peer)
        choose, beta = sel_fit([(i, s, [{"r": c[0], "calls": c[1], "s": 0.0} for c in cand.values()], dr) for i, s, cand, dr in allfr], fval)
        av = ci(sel_auc(fval)) if fval else (float("nan"),) * 3
        for sset, tname in SEL_T:
            D, raw, it, miss = sel_items(sset, None, S, "sel", gen, peer)
            ids, n = sorted(D), 3 * len(D)
            a = sel_auc(it)
            if not a:
                print(f"    SEL-G {tname} {gen}: no scored mixed set (missing {miss})", flush=True); continue
            A = ci(a)
            sel, cross, pipe, casc, unseen, ch = Counter(), Counter(), Counter(), Counter(), 0, {}
            for x in it:
                c = choose(x)
                unseen += c is None
                sel[x[0]] += (c["r"] if c else x[3]) - x[3]
                ch[(x[0], x[1])] = c["r"] if c else x[3]
            for h in (0, 1):
                half = [x for x in it if zlib.crc32(x[0].encode()) % 2 == h]
                chh, _ = sel_fit(half, half)
                for x in it:
                    if zlib.crc32(x[0].encode()) % 2 != h:
                        c = chh(x)
                        cross[x[0]] += (c["r"] if c else x[3]) - x[3]
            acc = tok = acc0 = tok0 = 0
            for i, q in D.items():
                for sd in (1, 2, 3):
                    sc = lcm.seed_calls(q, sd)
                    r, t = lcm.fixed("cascade", sc); r0, t0 = lcm.fixed("SB->T->T", sc)
                    r2 = ch.get((i, sd), r)
                    pipe[i] += (U(r2, t) - U(r0, t0)) / 300; casc[i] += (U(r, t) - U(r0, t0)) / 300
                    acc += r2; tok += t; acc0 += r0; tok0 += t0
            c3 = lambda d: ci({i: d[i] / 3 for i in ids})
            pb, _ = rv_gauss(raw, A[0] / 100)
            R[(gen, tname)] = r = dict(A=A, sel=c3(sel), cross=c3(cross), bound=100 * pb / n)
            print(f"    SEL-G {tname} {gen}<-{peer}: {len(raw)} fallback question-seeds of {n}, missing scores {miss}; AUROC {g([x / 100 for x in A])} "
                  f"(held-out-database fresh {av[0] / 100:.3f}); selector (beta {beta:.1f}; {unseen} unseen structures keep d) - cascade "
                  f"{f(r['sel'])}; cross-fitted Bayes {f(r['cross'])}; bound {100 * pb / n:+.2f}; pipeline {100 * acc / n:.1f}% at "
                  f"{tok / n / 1000:.2f}k vs SB->T->T {100 * acc0 / n:.1f}% at {tok0 / n / 1000:.2f}k: pipeline - SB->T->T {f(ci(pipe))} "
                  f"(cascade alone {f(ci(casc))})", flush=True)
    if len(R) < 3 * len(SELG_GEN):
        print(f"*** {len(R)} of {3 * len(SELG_GEN)} cells present, not decided"); return
    hold = []
    for gen in SELG_GEN:
        X = [R[(gen, t)] for _, t in SEL_T]
        up, down = sum(r["sel"][1] > 0 for r in X), sum(r["sel"][2] < 0 for r in X)
        hold.append(up >= 2 and down == 0)
        print(f"    SEL-G-P1 {gen}: {up} above, {down} below -> {'holds' if hold[-1] else 'refuted'}")
    print(f"*** SEL-G-P1 (selector - cascade lower bound > 0 in >= 2 of 3 targets and upper < 0 in none, for >= 2 of 3 generators): "
          f"{sum(hold)} of 3 -> {'holds' if sum(hold) >= 2 else 'refuted'}")
    p2 = [R[(gen, "BIRD dev")]["A"][0] / 100 for gen in SELG_GEN]
    print(f"*** SEL-G-P2 (BIRD dev AUROC >= 0.70 for every generator): {[round(x, 3) for x in p2]} -> {'holds' if min(p2) >= 0.70 else 'refuted'}")


def tc3_choice(P, pat, rt, calls, txt, S, sset, i, beta, sd, loo=False):
    """SEL-TC3: whether the verifier's choice at a pattern (calls made) is right — logit of the planner's count rate + beta z over the
    passing answer groups seen; None where fewer than two are seen or a score is missing. loo: on a fitting row, the counts without the
    row itself (else a rare pattern's own label would make the choice right in-sample and pull the planner toward rare patterns)"""
    G = {}
    for j in sorted(calls):
        e = pat[j]
        if e is not None and e[0] != "X" and e[1]:
            G.setdefault(e[0], []).append(j)
    if len(G) < 2:
        return None
    sv = {g: [S.get(rv_key("tc", sset, i, "sel", txt[j])) for j in js] for g, js in G.items()}
    if any(v is None for x in sv.values() for v in x):
        return None
    n, C = P.n.get(pat, 0) - loo, []
    for g, x in sv.items():
        q = (P.r.get((pat, g), 0) - (loo and g in rt) + 0.5) / (n + 1)
        C.append((math.log(q / max(1e-3, 1 - q)), sum(v["s"] for v in x) / len(x), g in rt))
    mu = sum(c[1] for c in C) / len(C)
    return max(C, key=lambda c: c[0] + beta * (c[1] - mu) / sd)[2]


class VSupervised(Supervised):
    """SEL-TC3: the planner whose stop value, where >= 2 passing answers are seen, is the accuracy of the verifier's choice on its fitting
    rows (not its own vote's), so it values a call by what the verifier then does with the extra answer"""

    def __init__(self, items, tok, X, S, sset, beta, sd):
        import itertools
        from lcm_bound import project
        super().__init__([full(sc) for _, _, sc in items], tok)
        self.vr, self.vn = {}, {}
        for i, s, sc in items:
            obs, right = full(sc)
            for r in range(len(tok) + 1):
                for calls in itertools.combinations(range(len(tok)), r):
                    cs = frozenset(calls)
                    pat, rt = project(obs, right, cs)
                    v = tc3_choice(self, pat, rt, cs, X[(i, s)], S, sset, i, beta, sd, loo=True)
                    if v is not None:
                        self.vn[pat] = self.vn.get(pat, 0) + 1; self.vr[pat] = self.vr.get(pat, 0) + v

    def stop(self, pat):
        if self.vn.get(pat):
            return self.vr[pat] / self.vn[pat], "V"
        return super().stop(pat)


def tc3_run(P, sc, txt, S, sset, i, beta, sd):
    """VSupervised on one request-seed: (right, tokens) or None for a pattern it never saw"""
    from lcm_bound import project
    obs, right = full(sc)
    calls, tok = frozenset(), 0
    while True:
        pat, rt = project(obs, right, calls)
        if pat not in P.n:
            return None
        P.value(pat)
        kind, arg = P.act[pat]
        if kind != "stop":
            calls = calls | {arg}; tok += sc[arg][3]; continue
        if arg == "V":
            v = tc3_choice(P, pat, rt, calls, txt, S, sset, i, beta, sd)
            if v is not None:
                return v, tok
            arg = Supervised.stop(P, pat)[1]
        return ((arg in rt) if arg is not None else False), tok


def main_sel_tc3():
    """addendum SEL-TC3 (--sel-tc3 <verifier name>): the verifier-aware planner (VSupervised, fitted on the held-out ToolACE requests,
    SEL-TC2's beta and sd) against SEL-TC2's combination and the default on BFCL"""
    from analyze_ho3 import ci
    from run_nlopt import _rows
    nm = sys.argv[sys.argv.index("--sel-tc3") + 1]
    S = {r["h"]: r for r in _rows(os.path.join(lcm.ROOT, "results", "conf", f"sel_scores_{nm}.jsonl"))}
    f = lambda v: f"{v[0]:+.2f} [{v[1]:+.2f}, {v[2]:+.2f}]"
    U = lambda r, t: 100 * float(r) - LAM * t / 1000
    R = {}
    for nsrc in (None, RV_N["tc"]):
        name = "trained" if nsrc else "base"
        Dh, Xh = tc2_cells("tcho", nsrc)
        sch = [(i, s, lcm.seed_calls(q, s)) for i, q in Dh.items() for s in (1, 2, 3)]
        tok = [sum(sc[j][3] for _, _, sc in sch) / len(sch) for j in range(5)]
        P = Supervised([full(sc) for _, _, sc in sch], tok)
        sets = [x[3] for i, s, sc in sch for x in [tc2_run(P, sc, Xh[(i, s)], S, "tcho", i)] if x and x[3]]
        dv = [c["s"] - sum(d["s"] for d in C) / len(C) for C in sets for c in C]
        sd = (sum(x * x for x in dv) / max(1, len(dv))) ** 0.5 or 1.0

        def ll(b):
            t = 0.0
            for C in sets:
                mu = sum(c["s"] for c in C) / len(C)
                for c in C:
                    z = c["lp"] + b * (c["s"] - mu) / sd
                    t += -math.log1p(math.exp(-z)) if c["r"] else -math.log1p(math.exp(min(z, 700)))
            return t
        beta = max((b / 10 for b in range(0, 41)), key=ll)
        V = VSupervised(sch, tok, Xh, S, "tcho", beta, sd)
        Db, Xb = tc2_cells("bfcl", nsrc)
        ids = sorted(Db)
        acc, kt, Uq, unseen = Counter(), Counter(), {k: Counter() for k in ("v", "comb", "default")}, 0
        for i in ids:
            for s in (1, 2, 3):
                sc = lcm.seed_calls(Db[i], s)
                a = tc2_run(P, sc, Xb[(i, s)], S, "bfcl", i, beta, sd)
                b = tc3_run(V, sc, Xb[(i, s)], S, "bfcl", i, beta, sd)
                if a is None or b is None:   # a pattern a planner never saw: the cascade's outcome for both
                    unseen += 1; a = b = lcm.fixed("cascade", sc)
                out = {"v": b[:2], "comb": a[:2], "default": lcm.fixed("SB->T->T", sc)}
                for k, (r, t) in out.items():
                    acc[k] += r; kt[k] += t; Uq[k][i] += U(r, t) / 300
        n = 3 * len(ids)
        d = lambda x, y: ci({i: Uq[x][i] - Uq[y][i] for i in ids})
        R[name] = r = {"comb": d("v", "comb"), "default": d("v", "default")}
        print(f"    SEL-TC3 BFCL {name}: beta {beta:.1f}; verifier-aware planner {100 * acc['v'] / n:.1f}% at {kt['v'] / n / 1000:.2f}k, "
              f"SEL-TC2's combination {100 * acc['comb'] / n:.1f}% at {kt['comb'] / n / 1000:.2f}k, default {100 * acc['default'] / n:.1f}% "
              f"at {kt['default'] / n / 1000:.2f}k; verifier-aware - combination {f(r['comb'])}; - default {f(r['default'])}; unseen {unseen}",
              flush=True)
    if len(R) < 2:
        print("*** not every cell present, not decided"); return
    up, down = sum(R[k]["comb"][1] > 0 for k in R), sum(R[k]["comb"][2] < 0 for k in R)
    print(f"*** SEL-TC3-P1 (verifier-aware planner - SEL-TC2's combination, lower bound > 0 for both N types): {up} above, {down} below -> "
          f"{'holds' if up == 2 else 'refuted'}")


def sql2_cells(sset, nsrc):
    """addendum SEL2: (questions, {(id, seed): the five calls' extracted queries}) of the SQL cascade (Qwen3-8B, peer Qwen3.5-9B)"""
    D = quiet(lcm.load, "sql", "q8b", "q35", sset, **({"nsrc": nsrc} if nsrc else {}))
    W = rv_texts("sql", sset, nsrc)
    return D, {(i, s): [W.get((t, ss, i), "") for t, ss in (("N", s), ("P", s), ("SB", s), ("T", s), ("T", s % 3 + 1))]
               for i in D for s in (1, 2, 3)}


def main_sel_build_2():
    """addendum SEL2: every passing query of the five calls on question-seeds with >= 2 distinct passing results (the fresh questions on
    the held-out databases, BIRD dev, Spider test, Spider dev; both N types) -> results/conf/sel_req_2.jsonl"""
    req, val = {}, sel_val_ids()
    for sset in ("fresh",) + tuple(x for x, _ in SEL_T):
        for nsrc in (None, RV_N["sql"]):
            D, X = sql2_cells(sset, nsrc)
            m = 0
            for i, q in D.items():
                if sset == "fresh" and i not in val:
                    continue
                for s in (1, 2, 3):
                    sc = lcm.seed_calls(q, s)
                    if len({c[0] for c in sc if c[1] and c[0] is not None}) < 2:
                        continue
                    m += 1
                    for j, c in enumerate(sc):
                        if c[1] and c[0] is not None:
                            h = rv_key("sql", sset, i, "sel", X[(i, s)][j])
                            req[h] = {"h": h, "task": "sql", "sset": sset, "id": i, "kind": "sel", "text": X[(i, s)][j]}
            print(f"SEL2 build {sset} {nsrc or 'base'}: {m} question-seeds with >= 2 passing results; requests so far {len(req)}", flush=True)
    with open(os.path.join(lcm.ROOT, "results", "conf", "sel_req_2.jsonl"), "w") as f:
        for r in req.values():
            f.write(json.dumps(r) + "\n")
    print(f"SEL2 build: {len(req)} requests -> results/conf/sel_req_2.jsonl")


def main_sel_2():
    """addendum SEL2 (--sel-2 <SEL's checkpoint>): TL's SQL planner (fitted on the 1,338 fresh BIRD-train questions' labels) with SEL's
    verifier choosing at its stop (beta, sd from the stop sets of the 343 held-out-database fresh questions), against SEL's pipeline
    (the cascade with the verifier at its fallback), the planner alone and the default, on BIRD dev, Spider test and Spider dev"""
    from analyze_ho3 import ci
    from run_nlopt import _rows
    nm = sys.argv[sys.argv.index("--sel-2") + 1]
    S = {r["h"]: r for r in _rows(os.path.join(lcm.ROOT, "results", "conf", f"sel_scores_{nm}.jsonl"))}
    val = sel_val_ids()
    f = lambda v: f"{v[0]:+.2f} [{v[1]:+.2f}, {v[2]:+.2f}]"
    U = lambda r, t: 100 * float(r) - LAM * t / 1000
    R = {}
    for nsrc in (None, RV_N["sql"]):
        name = "trained" if nsrc else "base"
        Df, Xf = sql2_cells("fresh", nsrc)
        sch = [(i, s, lcm.seed_calls(q, s)) for i, q in Df.items() for s in (1, 2, 3)]
        tok = [sum(sc[j][3] for _, _, sc in sch) / len(sch) for j in range(5)]
        P = Supervised([full(sc) for _, _, sc in sch], tok)
        sets = [x[3] for i, s, sc in sch if i in val for x in [tc2_run(P, sc, Xf[(i, s)], S, "fresh", i, task="sql")] if x and x[3]]
        dv = [c["s"] - sum(d["s"] for d in C) / len(C) for C in sets for c in C]
        sd = (sum(x * x for x in dv) / max(1, len(dv))) ** 0.5 or 1.0

        def ll(b):
            t = 0.0
            for C in sets:
                mu = sum(c["s"] for c in C) / len(C)
                for c in C:
                    z = c["lp"] + b * (c["s"] - mu) / sd
                    t += -math.log1p(math.exp(-z)) if c["r"] else -math.log1p(math.exp(min(z, 700)))
            return t
        beta = max((b / 10 for b in range(0, 41)), key=ll)
        # SEL's pipeline: the cascade with SEL's fresh-fitted selector at its fallback (as main_sel)
        _, _, fr, _ = sel_items("fresh", nsrc, S)
        _, allfr = rv_items("sql", "fresh", nsrc)
        choose, _ = sel_fit([(i, s, [{"r": c[0], "calls": c[1], "s": 0.0} for c in cand.values()], dr) for i, s, cand, dr in allfr],
                            [x for x in fr if x[0] in val])
        for sset, tname in SEL_T:
            _, _, it, _ = sel_items(sset, nsrc, S)
            selc = {(x[0], x[1]): choose(x) for x in it}
            D, X = sql2_cells(sset, nsrc)
            ids = sorted(D)
            acc, kt, Uq, unseen, nset = Counter(), Counter(), {k: Counter() for k in ("comb", "plan", "sel", "default")}, 0, 0
            for i in ids:
                for s in (1, 2, 3):
                    sc = lcm.seed_calls(D[i], s)
                    rc, tc_ = lcm.fixed("cascade", sc)
                    c = selc.get((i, s))
                    out = {"sel": (c["r"] if c else rc, tc_), "default": lcm.fixed("SB->T->T", sc)}
                    a = tc2_run(P, sc, X[(i, s)], S, sset, i, beta, sd, task="sql")
                    b = tc2_run(P, sc, X[(i, s)], S, sset, i, task="sql")
                    if a is None:   # a pattern the planner never saw: SEL's outcome
                        unseen += 1; out["comb"] = out["plan"] = out["sel"]
                    else:
                        out["comb"], out["plan"] = a[:2], b[:2]; nset += a[3] is not None
                    for k, (r, t) in out.items():
                        acc[k] += r; kt[k] += t; Uq[k][i] += U(r, t) / 300
            n = 3 * len(ids)
            d = lambda x, y: ci({i: Uq[x][i] - Uq[y][i] for i in ids})
            R[(name, tname)] = r = {k: d("comb", k) for k in ("plan", "sel", "default")}
            print(f"    SEL2 {tname} {name}: beta {beta:.1f} (sd {sd:.2f}, {len(sets)} held-out-database stop sets); " + "; ".join(
                f"{k} {100 * acc[k] / n:.1f}% at {kt[k] / n / 1000:.2f}k" for k in ("comb", "plan", "sel", "default")) +
                f"; scored stop sets {nset}, unseen {unseen} of {n}; combined - planner {f(r['plan'])}; combined - SEL's pipeline "
                f"{f(r['sel'])}; combined - default {f(r['default'])}", flush=True)
    if len(R) < 6:
        print(f"*** {len(R)} of 6 cells present, not decided"); return
    for name in ("base", "trained"):
        X = [R[(name, t)]["sel"] for _, t in SEL_T]
        up, down = sum(x[1] > 0 for x in X), sum(x[2] < 0 for x in X)
        print(f"*** SEL2-P1{name[0]} ({name}: combined - SEL's pipeline lower bound > 0 in >= 2 of 3, upper < 0 in none): {up} above, "
              f"{down} below -> {'holds' if up >= 2 and down == 0 else 'refuted'}")


def main():
    if "--sel-build-pww" in sys.argv:
        return main_sel_build_pww()
    if "--sel-pww" in sys.argv or "--sel-val-pww" in sys.argv:
        return main_sel_pww()
    if "--sel-build-pwtc" in sys.argv:
        return main_sel_build_pwtc()
    if "--sel-pwtc" in sys.argv or "--sel-val-pwtc" in sys.argv:
        return main_sel_pwtc()
    if "--sel-build-pw" in sys.argv:
        return main_sel_build_pw()
    if "--sel-pw" in sys.argv or "--sel-val-pw" in sys.argv:
        return main_sel_pw()
    if "--sel-build-2" in sys.argv:
        return main_sel_build_2()
    if "--sel-2" in sys.argv:
        return main_sel_2()
    if "--sel-tc3" in sys.argv:
        return main_sel_tc3()
    if "--sel-build-g" in sys.argv:
        return main_sel_build_g()
    if "--sel-g" in sys.argv:
        return main_sel_g()
    if "--sel-build-tc2" in sys.argv:
        return main_sel_build_tc2()
    if "--sel-tc2" in sys.argv:
        return main_sel_tc2()
    if "--sel-build-w" in sys.argv:
        return main_sel_build_w()
    if "--sel-w" in sys.argv or "--sel-val-w" in sys.argv:
        return main_sel_w()
    if "--sel-build-tc" in sys.argv:
        return main_sel_build_tc()
    if "--sel-tc" in sys.argv or "--sel-val-tc" in sys.argv:
        return main_sel_tc()
    if "--sel-build" in sys.argv:
        return main_sel_build()
    if "--sel" in sys.argv or "--sel-val" in sys.argv:
        return main_sel()
    if "--rv-build" in sys.argv:
        return main_rv_build()
    if "--rv" in sys.argv:
        return main_rv()
    if "--tl4" in sys.argv:
        return main_tl4()
    if "--tl" in sys.argv:
        return main_tl()
    if "--trt" in sys.argv:
        return main_trt()
    if "--tr-c1" in sys.argv:
        return main_tr_c1()
    if "--tr" in sys.argv:
        return main_tr()
    R = []
    for name, dev, tgt, prim in cells():
        if not tgt or not all(dev):
            print(f"*** {name}: rows missing", flush=True)
            continue
        R.append((prim, run_cell(name, dev, tgt)))
    P = [r for p, r in R if p]
    c = lambda key, X: sum(r[key][1] > 0 for r in X)
    print(f"\n*** primary cells {len(P)}")
    print(f"LS-P1 LS - cascade: lower bound > 0 in {c('LS_vs_cascade', P)} of {len(P)} (needs >= 3) -> "
          f"{'holds' if c('LS_vs_cascade', P) >= 3 else 'refuted'}; upper bound < 0 in {sum(r['LS_vs_cascade'][2] < 0 for r in P)}")
    print(f"LS-P2 LS - transfer: lower bound > 0 in {c('LS_vs_transfer', P)} of {len(P)} (needs >= 2) -> "
          f"{'holds' if c('LS_vs_transfer', P) >= 2 else 'refuted'}; upper bound < 0 in {sum(r['LS_vs_transfer'][2] < 0 for r in P)}")
    S = [r for p, r in R if not p]
    print(f"reported, tool calls and SQL: LS - cascade better {c('LS_vs_cascade', S)}, worse {sum(r['LS_vs_cascade'][2] < 0 for r in S)} of "
          f"{len(S)}; reference - cascade better {c('reference_vs_cascade', S)}")


if __name__ == "__main__":
    main()
