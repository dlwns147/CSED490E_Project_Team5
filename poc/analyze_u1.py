"""U1 (results/PREREG_U1.md): mechanism signatures and allocation by mechanism vs by difficulty. Written 2026-10-16 22:31 UTC,
before any U1 result was read. Tags S2_U1_<model>_{geo,co}_{base_s1..3,fact_s1,decor_s1,think_s1}.
Signatures from the base samples only: S_conf = min log-prob at tool / API names in base_s1; S_cons = share of agreeing pairs among the
3 base outputs on the instance; S_check = base_s1 passes the label-free check. Accuracy: geometry correct on all 8 copies, optimization
optimal. usage: python analyze_u1.py [model ...]"""
import bisect, itertools, json, os, random, re, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_n10 as A  # noqa: E402  (geo_check, co_check, CACHE)
_argv, sys.argv = sys.argv, sys.argv[:1]   # analyze_n12 reads sys.argv at import
import analyze_n12 as B  # noqa: E402  (geo_out)
sys.argv = _argv
from analyze_n16 import ORT, COMMON  # noqa: E402

RES = A.RES
U1B = {}
U1F = {}
U2R = {}
GEO_TASKS = "hull,area2,pip,segs,close,lattice,rectunion,delaunay,diameter".split(",")


def load(m, dom, arm):
    cs = os.environ.get("U1_CURE_SEED")   # U1r: read the cure arms of another seed (the base samples stay seeds 1-3)
    if cs and arm in ("fact_s1", "decor_s1", "think_s1", "retr_s1"):
        arm = arm.replace("_s1", f"_s{cs}")
    f = f"{RES}/{'geocross' if dom == 'geo' else 'co'}_S2_U1_{m}_{dom}_{arm}.jsonl"
    if m == "q36" and arm == "think_s1" and os.environ.get("U1_Q36_THINK48K"):   # pre-registered sensitivity (PREREG_U1 addendum 03:29):
        f = f"{RES}/{'geocross' if dom == 'geo' else 'co'}_S2_N10m3_{dom}_think_s1.jsonl"   # same items + condition, 48k cap (N10-M3)
    if not os.path.exists(f):
        return None
    return {((r["task"], r["n"], r["inst"]) if dom == "geo" else r["key"]): r for r in map(json.loads, open(f))}


def ok(dom, r):
    return r["class"] == "correct_all" if dom == "geo" else (r["status"] == "ok" and r["feasible"] and r["gap"] == 0)


def check(dom, r):
    return (A.geo_check if dom == "geo" else A.co_check)(r)[0]


def answer(dom, r):
    if dom == "geo":
        return B.geo_out(r)
    return r["value"] if r["status"] == "ok" and r["feasible"] else None


def s_conf(dom, r):
    toks, lps = r.get("lp_tok") or [], r.get("lp") or []
    code = r.get("code") or ""
    if not toks or not code:
        return 0.0
    joined = "".join(toks); base = joined.rfind(code[:150])
    if base < 0:
        return 0.0
    starts = list(itertools.accumulate([0] + [len(t) for t in toks]))
    if dom == "geo":   # calls to helper functions defined in the program (the offered toolbox is copied in)
        names = set(re.findall(r"^def (\w+)\(", code, re.M))
        pat = re.compile(r"(?<![\w.])(" + "|".join(map(re.escape, names)) + r")\(") if names else None
    else:   # OR-Tools API attribute calls
        pat = re.compile(r"\.([A-Za-z_]\w*)\s*\(")
    if pat is None:
        return 0.0
    best = 0.0
    for mt in pat.finditer(code):
        name = mt.group(1)
        if dom == "co" and (name in COMMON and name not in ORT):
            continue
        if dom == "geo" and code.find(f"def {name}(") == mt.start(1) - 4:
            continue
        a, b = base + mt.start(1), base + mt.end(1)
        idx = [i for i in range(len(toks)) if starts[i] < b and starts[i + 1] > a]
        if idx:
            best = min(best, min(lps[i] for i in idx))
    return best


def auroc(neg, pos):
    if not neg or not pos:
        return float("nan")
    p = sorted(pos); n = 0.0
    for x in neg:
        lo, hi = bisect.bisect_left(p, x), bisect.bisect_right(p, x); n += (len(p) - hi) + 0.5 * (hi - lo)
    return n / (len(neg) * len(p))


def tok(r):
    return r.get("out_tokens") or 0


def run(m):
    pooled = {}
    for dom in ("geo", "co"):
        D = {arm: load(m, dom, arm) for arm in ("base_s1", "base_s2", "base_s3", "fact_s1", "decor_s1", "think_s1")}
        if any(v is None for v in D.values()):
            print(m, dom, "incomplete:", [k for k, v in D.items() if v is None]); continue
        keys = sorted(set.intersection(*(set(v) for v in D.values())))
        task = (lambda k: k[0]) if dom == "geo" else (lambda k: k.rsplit("-", 2)[0])
        F = {}
        for k in keys:
            b = [D[f"base_s{s}"][k] for s in (1, 2, 3)]
            outs = [answer(dom, x) for x in b]
            pairs = [(i, j) for i in range(3) for j in range(i + 1, 3)]
            cons = sum(outs[i] is not None and outs[i] == outs[j] for i, j in pairs) / 3
            F[k] = {"conf": s_conf(dom, b[0]), "cons": cons, "check": check(dom, b[0]), "ok": {a: ok(dom, D[a][k]) for a in D},
                    "tok": {a: tok(D[a][k]) for a in D}, "decor_check": check(dom, D["decor_s1"][k]),
                    "decor_agree": answer(dom, D["decor_s1"][k]) is not None and answer(dom, D["decor_s1"][k]) == outs[0]}
        A_ = lambda k, a: F[k]["ok"][a]
        fail = [k for k in keys if not A_(k, "base_s1")]
        # P1: signatures vs which cure works
        fact_only = [k for k in fail if A_(k, "fact_s1") and not A_(k, "think_s1")]
        think_fix = [k for k in fail if A_(k, "think_s1")]
        decor_only = [k for k in fail if A_(k, "decor_s1") and not A_(k, "think_s1")]
        think_only = [k for k in fail if A_(k, "think_s1") and not A_(k, "decor_s1") and not A_(k, "fact_s1")]
        p1a = auroc([F[k]["conf"] for k in fact_only], [F[k]["conf"] for k in think_fix])
        p1b = 1 - auroc([F[k]["cons"] for k in decor_only], [F[k]["cons"] for k in think_only]) if decor_only and think_only else float("nan")
        print(f"{m} {dom}: {len(keys)} items, base_s1 {100 * sum(A_(k, 'base_s1') for k in keys) / len(keys):.1f}%, failing {len(fail)}; "
              f"fixed by FACT only {len(fact_only)}, by THINK {len(think_fix)}, by DECOR only {len(decor_only)}, THINK only {len(think_only)}")
        print(f"   P1a AUROC (FACT-only items have lower S_conf than THINK-fixed) {p1a:.3f}; P1b AUROC (DECOR-only items have higher S_cons than "
              f"THINK-only) {p1b:.3f}")
        base_tok = sum(F[k]["tok"]["base_s1"] for k in keys)
        samp_tok = sum(F[k]["tok"]["base_s2"] + F[k]["tok"]["base_s3"] for k in keys)
        # uniform: gated THINK on the label-free check
        uni_acc = sum(A_(k, "think_s1") if not F[k]["check"] else A_(k, "base_s1") for k in keys)
        uni_tok = base_tok + sum(F[k]["tok"]["think_s1"] for k in keys if not F[k]["check"])
        # mechanism policy with tau_conf chosen leave-one-task-out
        def mech(k, tau):
            f = F[k]
            if f["check"] and f["cons"] == 1:
                return "base_s1"
            if f["conf"] < tau:
                return "fact_s1"
            if f["cons"] == 1:
                return "decor_s1" if (f["decor_check"] and not f["decor_agree"]) else "think_s1"
            return "think_s1"
        taus = sorted({round(F[k]["conf"], 3) for k in keys}) + [0.5]
        mech_acc = mech_tok = 0; choice = Counter()
        for T in sorted({task(k) for k in keys}):
            tr = [k for k in keys if task(k) != T]; te = [k for k in keys if task(k) == T]
            tau = max(taus, key=lambda t: (sum(A_(k, mech(k, t)) for k in tr), -sum(F[k]["tok"][mech(k, t)] for k in tr)))
            for k in te:
                a = mech(k, tau); choice[a] += 1
                mech_acc += A_(k, a); mech_tok += F[k]["tok"]["base_s1"] + (F[k]["tok"][a] if a != "base_s1" else 0)
        mech_tok += samp_tok
        # difficulty policy at the same total budget as MECHANISM: THINK on the lowest-S_cons items (ties: failing the check first)
        budget = mech_tok - base_tok - samp_tok
        order = sorted(keys, key=lambda k: (F[k]["cons"], F[k]["check"], random.Random(str(k)).random()))
        spent = 0; think_set = set()
        for k in order:
            if spent + F[k]["tok"]["think_s1"] > budget:
                break
            think_set.add(k); spent += F[k]["tok"]["think_s1"]
        dif_acc = sum(A_(k, "think_s1") if k in think_set else A_(k, "base_s1") for k in keys)
        dif_tok = base_tok + samp_tok + spent
        orc = sum(any(A_(k, a) for a in ("base_s1", "fact_s1", "decor_s1", "think_s1")) for k in keys)
        n = len(keys)
        print(f"   uniform (gated THINK) {100 * uni_acc / n:.1f}% @ {uni_tok / n:.0f} | DIFFICULTY {100 * dif_acc / n:.1f}% @ {dif_tok / n:.0f} | "
              f"MECHANISM {100 * mech_acc / n:.1f}% @ {mech_tok / n:.0f} (choices {dict(choice)}) | oracle {100 * orc / n:.1f}%")
        pooled[dom] = (mech_acc, dif_acc, uni_acc, n)
        # U1b (PREREG_U1.md, 04:31): Snell-faithful difficulty bins choosing among ALL arms (LOTO), and always-FACT
        arms = ("base_s1", "fact_s1", "decor_s1", "think_s1")
        sn_acc = sn_tok = 0; sn_choice = Counter()
        for T in sorted({task(k) for k in keys}):
            tr = [k for k in keys if task(k) != T]; te = [k for k in keys if task(k) == T]
            for c in sorted({F[k]["cons"] for k in te}):
                bt = [k for k in tr if F[k]["cons"] == c] or tr
                arm = max(arms, key=lambda a_: (sum(A_(k, a_) for k in bt), -sum(F[k]["tok"][a_] for k in bt)))
                for k in te:
                    if F[k]["cons"] == c:
                        sn_choice[arm] += 1; sn_acc += A_(k, arm)
                        sn_tok += F[k]["tok"]["base_s1"] + (F[k]["tok"][arm] if arm != "base_s1" else 0)
        sn_tok += samp_tok
        af_acc = sum(A_(k, "fact_s1") for k in keys); af_tok = sum(F[k]["tok"]["fact_s1"] for k in keys)
        fc = {k: check(dom, D["fact_s1"][k]) for k in keys}   # fact first, THINK only when the fact program fails the label-free check
        ft_acc = sum(A_(k, "fact_s1") if fc[k] else A_(k, "think_s1") for k in keys)
        ft_tok = sum(F[k]["tok"]["fact_s1"] + (0 if fc[k] else F[k]["tok"]["think_s1"]) for k in keys)
        print(f"   FACT-FIRST-THEN-THINK {100 * ft_acc / n:.1f}% @ {ft_tok / n:.0f} (thinking on {sum(not v for v in fc.values())})")
        U1F[(m, dom)] = (ft_acc, ft_tok, n)
        # U2 (PREREG_U1.md 05:36): RETRIEVED fact first (geometry: K8 + BM25 algorithm note; optimization: BM25 top-3 snippets = DECOR arm),
        # THINK (same cure seed) only when the retrieved program fails the label-free check
        R = load(m, dom, "retr_s1") if dom == "geo" else D["decor_s1"]
        if R is not None and all(k in R for k in keys):
            rc = {k: check(dom, R[k]) for k in keys}
            rt_acc = sum(ok(dom, R[k]) if rc[k] else A_(k, "think_s1") for k in keys)
            rt_tok = sum(tok(R[k]) + (0 if rc[k] else F[k]["tok"]["think_s1"]) for k in keys)
            r_acc = sum(ok(dom, R[k]) for k in keys); r_tok = sum(tok(R[k]) for k in keys)
            print(f"   U2: ALWAYS-RETRIEVED {100 * r_acc / n:.1f}% @ {r_tok / n:.0f} | RETRIEVED-FIRST-THEN-THINK {100 * rt_acc / n:.1f}% @ "
                  f"{rt_tok / n:.0f} (thinking on {sum(not v for v in rc.values())}; hand-written fact fails its check on {sum(not v for v in fc.values())})")
            U2R[(m, dom)] = (rt_acc, rt_tok, n, r_acc, r_tok, dif_acc, ft_acc)
        else:
            print(f"   U2: retrieved arm incomplete ({0 if R is None else sum(k in R for k in keys)}/{n})")
        print(f"   U1b: SNELL-BINNED {100 * sn_acc / n:.1f}% @ {sn_tok / n:.0f} (choices {dict(sn_choice)}) | ALWAYS-FACT {100 * af_acc / n:.1f}% @ {af_tok / n:.0f}")
        U1B[(m, dom)] = (mech_acc, mech_tok, sn_acc, sn_tok, af_acc, af_tok, n)
    json.dump(A.CACHE, open(A.CACHE_F, "w"))
    return pooled


if __name__ == "__main__":
    tot = Counter()
    for m in sys.argv[1:] or ["q32b", "q8b", "q36"]:
        for dom, (ma, da, ua, n) in run(m).items():
            tot["mech"] += ma; tot["dif"] += da; tot["uni"] += ua; tot["n"] += n
    if U1B:
        S = [sum(v[i] for v in U1B.values()) for i in range(7)]
        print(f"U1b POOLED: MECHANISM {100 * S[0] / S[6]:.1f}% @ {S[1] / S[6]:.0f} | SNELL-BINNED {100 * S[2] / S[6]:.1f}% @ {S[3] / S[6]:.0f} | "
              f"ALWAYS-FACT {100 * S[4] / S[6]:.1f}% @ {S[5] / S[6]:.0f} (n = {S[6]})")
    if U1F:
        S = [sum(v[i] for v in U1F.values()) for i in range(3)]
        print(f"FACT-FIRST-THEN-THINK POOLED: {100 * S[0] / S[2]:.1f}% @ {S[1] / S[2]:.0f} (n = {S[2]})")
    if U2R:
        S = [sum(v[i] for v in U2R.values()) for i in range(7)]
        print(f"U2 POOLED over {sorted(U2R)}: RETRIEVED-FIRST-THEN-THINK {100 * S[0] / S[2]:.1f}% @ {S[1] / S[2]:.0f} | ALWAYS-RETRIEVED "
              f"{100 * S[3] / S[2]:.1f}% @ {S[4] / S[2]:.0f} | DIFFICULTY {100 * S[5] / S[2]:.1f}% | FACT-FIRST-THEN-THINK {100 * S[6] / S[2]:.1f}% (n = {S[2]})")
    if tot["n"]:
        print(f"POOLED: MECHANISM {100 * tot['mech'] / tot['n']:.1f}% | DIFFICULTY {100 * tot['dif'] / tot['n']:.1f}% | uniform {100 * tot['uni'] / tot['n']:.1f}% (n = {tot['n']})")
