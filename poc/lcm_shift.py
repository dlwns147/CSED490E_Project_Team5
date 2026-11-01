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


def rv_texts(task, sset, nsrc):
    """{(call type, seed, id): the answer's text}: SQL the extracted query (prep_sql.extract), tool calls the graded calls"""
    from run_nlopt import _rows
    R, out = os.path.join(lcm.ROOT, "results", task), {}
    if task == "sql":
        from prep_sql import extract
        suf = {"dev": "", "spider": "sp", "spiderdev": "sd"}[sset]
        for t, tag, a, fld in (("N", nsrc or "q8b", "cheap", "n_text"), ("P", "q35", "cheap", "n_text"), ("SB", "q8b", "sb", "text"),
                               ("T", "q8b", "think", "text")):
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


def rv_items(task, sset, nsrc):
    """(questions, [(id, seed, {answer key: [right, (calls returning it), [texts]]}, fallback right)]): the cascade's question-seeds where
    N passed, P did not return the same answer, and N, P and the fallback d (SB if it passes, else T, else the retry T) give >= 2
    distinct passing answers"""
    k = {"nsrc": nsrc} if nsrc else {}
    if task == "sql":
        D = quiet(lcm.load, "sql", "q8b", "q35", sset, **k)
    else:
        nl, lv = quiet(lcm.load, "tc", "q8b", "q35", "non-live", **k), quiet(lcm.load, "tc", "q8b", "q35", "live", **k)
        assert not set(nl) & set(lv)
        D = {**nl, **lv}
    X, out = rv_texts(task, sset, nsrc), []
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
    rng, dp = random.Random(seed), (math.sqrt(2) * NormalDist().inv_cdf(A) if A > 0.5 else 0.0)
    cnt, rt = Counter(), Counter()
    for _, _, cand, _ in items:
        st = tuple(sorted(v[1] for v in cand.values()))
        for r, calls, _ in cand.values():
            cnt[(st, calls)] += 1; rt[(st, calls)] += r
    g = g1 = 0.0
    for _, _, cand, dr in items:
        st = tuple(sorted(v[1] for v in cand.values()))
        for _ in range(reps):
            best = b1 = None
            for r, calls, _ in cand.values():
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
    against the Gaussian bound at the measured AUROC"""
    from analyze_ho3 import ci
    from run_nlopt import _rows
    S = {r["h"]: r for r in _rows(os.path.join(lcm.ROOT, "results", "conf", "rv_scores.jsonl"))}
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
                    if any(x is None for x in rv + cd):
                        miss += 1; c.append(None); c.append(None); continue
                    c.append(sum(x["s"] for x in rv) / len(rv)); c.append(sum(x["s"] / max(1, x["n"]) for x in cd) / len(cd))
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


def main():
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
