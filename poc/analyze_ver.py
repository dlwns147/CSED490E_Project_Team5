"""VER (docs/prereg/PREREG_VER.md): a learned check — Qwen3-8B fine-tuned on OptMATH-Train to say whether a passing program's printed
value is right (poc/ver_build.py, labels in training only; scores poc/ver_score.py) — as the gate of HO-PA's word-problem cascades,
offline on Qwen3-8B's stored rows (OptiBench third, BWOR, LogiOR, OptMATH; seeds 1-3; s2 = s % 3 + 1). V(x) = the verifier's P(yes)
for a passing program x (programs that fail the free check are never gated). Per problem and seed:
  D        the default SB->T->T (analyze_hopa);
  PEER     N -> Qwen3.5-9B's quick program prints the same value -> N, else D (HO-PA);
  VN(t)    N passes and V(N) >= t -> N; else D (cheap first with the learned check; the verifier's one generated token counted);
  VD(t)    D with every passing think program gated: SB passes and V >= t -> SB; else think s: passes and V >= t -> it; else think s2's
           end if it passes; if nothing was accepted, the passing program of the three with the highest V, else wrong;
  VND(t)   VN, then VD on a rejected or failed N (N joins the fallback).
t: t_dev = the threshold (0.05 ... 0.95) that maximises VN's utility on the train-dev problems (OptMATH-Train problems never trained on,
labels in training only; D there = the cut think's program if it passes, else the full think's, one sample), one threshold for every
gate; reported: t = 0.5 and per-policy cross-fitted thresholds (chosen on one half of the test problems by crc32(id) % 2, scored on
the other).
Tests: VER-P1 VD(t_dev) - D; VER-P2 VN(t_dev) - D; VER-P3 VND(t_dev) - D; VER-P4 AUC of V over the passing programs of all three arms
(test sets pooled), trained - untrained (bootstrap over problems); VER-P5 VND(t_dev) with the trained verifier - with the untrained
base model (its own t_dev). Paired 95% intervals over problems (seed means), utility = accuracy - 0.5 x ktokens. --oracle: V = the
label (the ceilings).
usage: python analyze_ver.py [vtag verv1] [base tag ver0] [--oracle]"""
import contextlib, io, json, os, random, sys, zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
with contextlib.redirect_stdout(io.StringIO()):
    from analyze_ho3 import ci
    from analyze_hopa import BENCH, LAM, per_q, policies, same_word, word_rows
    from analyze_ho import ok_
    from run_nlopt import RES, _rows

GRID = [round(0.05 * k, 2) for k in range(1, 20)]
DATA = os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data")
ARMS = ("formx", "formxtb2000", "formxt")


def scores(vtag, oracle=False):
    """{(bench, arm, seed, id): V} for passing programs, and the train-dev rows"""
    V = {}
    for b in BENCH:
        for a in ARMS:
            for s in (1, 2, 3):
                if oracle:
                    keep = {r["id"] for r in _rows(f"{RES}/opt_q8b_{b}_formxt_s{s}.jsonl")}
                    V.update({(b, a, s, r["id"]): float(r["correct"]) for r in _rows(f"{RES}/opt_q8b_{b}_{a}_s{s}.jsonl")
                              if ok_(r) and r["id"] in keep})
                else:
                    V.update({(b, a, s, r["id"]): r["p_yes"] for r in _rows(f"{RES}/ver_{vtag}_{b}_{a}_s{s}.jsonl")})
    if oracle:
        dev = [dict(r, p_yes=float(r["right"])) for r in map(json.loads, open(f"{DATA}/optmath_train/ver_dev_{os.environ.get('VER_DATA', 'v1')}.jsonl"))]
    else:   # the dev outcome fields come from the data file (the score rows carry id, arm, right, prompt_hash)
        meta = {(x["id"], zlib.crc32(x["prompt"].encode())): x for x in map(json.loads, open(f"{DATA}/optmath_train/ver_dev_{os.environ.get('VER_DATA', 'v1')}.jsonl"))}
        dev = [dict(meta[(r["id"], r["prompt_hash"])], p_yes=r["p_yes"]) for r in _rows(f"{RES}/ver_{vtag}_dev.jsonl")
               if (r["id"], r["prompt_hash"]) in meta]
    return V, dev


def t_dev(dev):
    """VN's threshold on the train-dev problems: per problem with a cut-think row, each passing quick program x is accepted iff V >= t,
    else D (the cut think's program if it passes, else the full think's: d_right, d_tok); quick programs that fail go to D in every
    policy, so only passing ones matter. Utility per program = 100 * right - LAM * ktokens."""
    best = None
    for t in GRID:
        u = n = 0
        for x in dev:
            if x["arm"] != "quick" or "d_right" not in x:
                continue
            n += 1
            u += (100 * x["right"] - LAM * (x["tok"] + 1) / 1000) if x["p_yes"] >= t else (100 * x["d_right"] - LAM * (x["tok"] + 1 + x["d_tok"]) / 1000)
        if n and (best is None or u / n > best[0]):
            best = (u / n, t)
    return best[1] if best else 0.5


def table(V, t):
    """{(bench, id, seed): {policy: (right, tokens)}}"""
    out = {}
    for b in BENCH:
        A, X = word_rows("q8b", b), word_rows("q35", b)
        R = policies(A, {"q35": X}, same_word)
        F, T, SB = A["formx"], A["formxt"], A["formxtb2000"]
        for (i, s), r in R.items():
            s2 = s % 3 + 1
            f, sb, t1, t2 = F[s][i], SB[s][i], T[s][i], T[s2][i]
            v = lambda arm, seed, x: V.get((b, arm, seed, i)) if x[0] else None
            vf, vsb, vt1, vt2 = v("formx", s, f), v("formxtb2000", s, sb), v("formxt", s, t1), v("formxt", s2, t2)
            d = r["SB->T->T"]
            gate = lambda vx: vx is not None and vx >= t
            vn = (f[1], f[2] + 1) if gate(vf) else (d[0], f[2] + (1 if f[0] else 0) + d[1])

            def vd(extra):   # extra = [(V, right)] of programs already paid for (N when VND)
                tok, cand = 0, list(extra)
                for x, vx in ((sb, vsb), (t1, vt1)):
                    tok += x[2] + (1 if x[0] else 0)
                    if gate(vx):
                        return x[1], tok
                    if x[0]:
                        cand.append((vx, x[1]))
                tok += t2[2]
                if t2[0]:
                    return t2[1], tok
                return (max(cand)[1] if cand else False), tok
            vd0 = vd([])
            if gate(vf):
                vnd = vn
            else:
                rr, tk = vd([(vf, f[1])] if f[0] else [])
                vnd = (rr, f[2] + (1 if f[0] else 0) + tk)
            out[(b, i, s)] = {"D": d, "PEER": r["N->q35->SB->T->T"], "VN": vn, "VD": vd0, "VND": vnd,
                              "accept N": (gate(vf), f[0], f[1])}
    return out


def pq(tab, k, ids=None):
    acc = {}
    for (b, i, s), v in tab.items():
        if ids is None or f"{b}/{i}" in ids:
            r, tok = v[k]
            acc.setdefault(f"{b}/{i}", []).append(float(r) - LAM / 100 * tok / 1000)
    return {i: sum(u) / len(u) for i, u in acc.items()}


def auc(V, arm="formx"):
    pos, neg = [], []
    for b in BENCH:
        for s in (1, 2, 3):
            for r in _rows(f"{RES}/opt_q8b_{b}_{arm}_s{s}.jsonl"):
                x = V.get((b, arm, s, r["id"]))
                if x is not None:
                    (pos if r["correct"] else neg).append((x, f"{b}/{r['id']}"))
    return pos, neg


def auc_of(pos, neg):
    if not pos or not neg:
        return float("nan")
    allv = sorted([(x, 1) for x, _ in pos] + [(x, 0) for x, _ in neg])
    rank, i, r1 = {}, 0, 0.0
    while i < len(allv):   # mid-ranks for ties
        j = i
        while j < len(allv) and allv[j][0] == allv[i][0]:
            j += 1
        for k in range(i, j):
            if allv[k][1]:
                r1 += (i + j + 1) / 2
        i = j
    return (r1 - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def boot_auc(a, b, B=1000):
    """AUC(a) - AUC(b) with a bootstrap over problems; a, b = (pos, neg) lists of (score, problem)"""
    probs = sorted({p for x in (a, b) for L in x for _, p in L})
    rng = random.Random(0)
    d0 = auc_of(*[[x for x in L] for L in a]) - auc_of(*[[x for x in L] for L in b])
    idx = lambda L: {p: [x for x in L if x[1] == p] for p in probs}
    ia, ib = [idx(L) for L in a], [idx(L) for L in b]
    bs = []
    for _ in range(B):
        smp = [rng.choice(probs) for _ in probs]
        A_ = [[x for p in smp for x in I[p]] for I in ia]
        B_ = [[x for p in smp for x in I[p]] for I in ib]
        bs.append(auc_of(*A_) - auc_of(*B_))
    bs.sort()
    return d0, bs[int(0.025 * B)], bs[int(0.975 * B) - 1]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    vtag, base = (args[0] if args else "verv1"), (args[1] if len(args) > 1 else "ver0")
    oracle = "--oracle" in sys.argv
    res = {}
    for name, tag in (("trained", vtag), ("untrained", base)):
        V, dev = scores(tag, oracle)
        if not V:
            print(f"{name} ({tag}): no scores"); continue
        td = t_dev(dev) if dev else 0.5
        dev_auc = auc_of([(r["p_yes"], r["id"]) for r in dev if r["right"]], [(r["p_yes"], r["id"]) for r in dev if not r["right"]])
        tabs = {t: table(V, t) for t in GRID}
        # cross-fitted t: chosen on one half of the test problems (VN's utility), scored on the other
        half = lambda key: zlib.crc32(key.split("/", 1)[1].encode()) % 2
        D = pq(tabs[0.5], "D")
        tcf = {k: {h: max(GRID, key=lambda t: sum(pq(tabs[t], k, {i for i in D if half(i) != h}).values())) for h in (0, 1)}
               for k in ("VN", "VD", "VND")}
        res[name] = {"V": V, "t": td, "tab": tabs[td], "tabs": tabs, "tcf": tcf}
        tab = tabs[td]
        acc = [v["accept N"] for v in tab.values()]
        npass = sum(a[1] for a in acc); nacc = sum(a[0] for a in acc)
        print(f"=== {name} ({tag}): t_dev {td}; train-dev AUC {dev_auc:.3f} over {len(dev)} programs; test: N passes {npass}, accepted "
              f"{nacc} ({100 * nacc / max(1, npass):.0f}%), right | accepted {100 * sum(a[2] for a in acc if a[0]) / max(1, nacc):.1f}% "
              f"(right | passes {100 * sum(a[2] for a in acc if a[1]) / max(1, npass):.1f}%); cross-fitted t {tcf}")
        for arm in ARMS:
            print(f"  AUC on passing {arm}: {auc_of(*auc(V, arm)):.3f}")
        print(f"  AUC on passing programs, three arms pooled: {auc_of(*tuple(sum(L, []) for L in zip(*(auc(V, a) for a in ARMS)))):.3f}")
        for t_name, tb in (("t_dev", tab), ("t=0.5", tabs[0.5])):
            for k in ("D", "PEER", "VN", "VD", "VND"):
                u = pq(tb, k)
                acc_ = {}
                for (b, i, s), v in tb.items():
                    acc_.setdefault(f"{b}/{i}", []).append((float(v[k][0]), v[k][1]))
                a = sum(sum(x for x, _ in L) / len(L) for L in acc_.values()) / len(acc_)
                tk = sum(sum(y for _, y in L) / len(L) for L in acc_.values()) / len(acc_)
                print(f"  [{t_name}] {k:>4}: accuracy {100 * a:.1f}% @ {tk / 1000:.2f}k, utility {100 * sum(u.values()) / len(u):.2f}")
        for k in ("VN", "VD", "VND"):
            cf = {}
            for h in (0, 1):
                cf.update(pq(tabs[tcf[k][h]], k, {i for i in D if half(i) == h}))
            g = ci({i: cf[i] - D[i] for i in D})
            print(f"  [cross-fitted t {tcf[k]}] {k} - D: {g[0]:+.2f} [{g[1]:+.2f}, {g[2]:+.2f}]")
        for arm in ARMS:   # calibration: the verifier's mean P(yes) against the share right (labels: reported only)
            pos, neg = auc(V, arm)
            print(f"  calibration {arm}: mean V {sum(x for x, _ in pos + neg) / max(1, len(pos + neg)):.3f}, right "
                  f"{len(pos) / max(1, len(pos + neg)):.3f} over {len(pos + neg)} passing programs")
        for b in BENCH:
            jj = [i for i in D if i.startswith(b + "/")]
            print(f"  {b}: " + ", ".join(f"{k} {100 * sum(pq(tab, k)[i] for i in jj) / len(jj):.2f}" for k in ("D", "PEER", "VN", "VD", "VND")))
    if "trained" not in res:
        return
    T = res["trained"]["tab"]
    D, out = pq(T, "D"), []
    tests = [("VER-P1 VD - D", pq(T, "VD"), D), ("VER-P2 VN - D", pq(T, "VN"), D), ("VER-P3 VND - D", pq(T, "VND"), D)]
    if "untrained" in res:
        tests.append(("VER-P5 VND trained - VND untrained", pq(T, "VND"), pq(res["untrained"]["tab"], "VND")))
    for name, a, b_ in tests:
        g = ci({i: a[i] - b_[i] for i in D})
        print(f"{name}: utility {g[0]:+.2f} [{g[1]:+.2f}, {g[2]:+.2f}]")
        out.append(f"{name.split()[0]} {g[1] > 0} ({g[0]:+.2f} [{g[1]:+.2f}, {g[2]:+.2f}])")
    if "untrained" in res:
        pooled = lambda V: tuple(sum(L, []) for L in zip(*(auc(V, a) for a in ARMS)))
        g = boot_auc(pooled(res["trained"]["V"]), pooled(res["untrained"]["V"]))
        print(f"VER-P4 AUC on the passing programs of N, SB and T, trained - untrained: {g[0]:+.3f} [{g[1]:+.3f}, {g[2]:+.3f}]")
        out.insert(3, f"VER-P4 {g[1] > 0} ({g[0]:+.3f} [{g[1]:+.3f}, {g[2]:+.3f}])")
    print("*** " + "; ".join(out))


if __name__ == "__main__":
    main()
