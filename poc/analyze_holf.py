"""HO-LF (docs/prereg/PREREG_MODEL.md, addendum): a label-free pilot from cross-mode votes. On k = 30 random items of each HO-CM cell
(analyze_hop.py --repair --fair --sb --cm: nine policies), every item's pseudo-answer is the plurality value of the pilot's programs that
pass the free check: cheap F (seed s), cheap F2 (seed s+1), 2k-token think SB, think T (seed s), think T2 (seed s+1); values equal within
the grader's tolerance (geometry: equal outputs on the six agreement inputs); ties go to T, T2, SB, F, F2; no passing program -> no
pseudo-answer. Each policy is scored against the pseudo-answers (the repaired program of FF-R0 too), tokens as observed, and the pilot
picks the best utility (lambda 0.5). Regret on the full cell with the true labels, against the labelled pilot on the same samples and
always SB->T->T. --think: votes from SB, T, T2 only (secondary). Geometry re-runs programs: run as a job (NPROC threads).
usage: python analyze_holf.py [--think] [model ...]   (default q14a q8b n3n q35)"""
import os, random, sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

sys.argv += [a for a in ("--repair", "--fair", "--sb", "--cm") if a not in sys.argv]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_hop as H  # noqa: E402
from analyze_ho import ok_  # noqa: E402
from run_nlopt import RES as XRES, _rows  # noqa: E402

LAM, K, NP = 0.5, 30, 1000
ORDER = ("T", "T2", "SB", "F", "F2")   # tie-break order
VOTERS = ("SB", "T", "T2") if "--think" in sys.argv else ORDER


def eq_word(x, y):
    return x is not None and y is not None and abs(x - y) <= max(1e-2, 1e-3 * max(abs(x), abs(y)))


def eq_geo(x, y):
    from analyze_hogc import same
    return x is not None and y is not None and all(same(p, q) for p, q in zip(x, y))


def word_vals(m, b, s):
    a, th = {bb: (aa, tt) for bb, aa, tt in (H.WORDS if m in ("oss20", "q14a", "q8b") else H.WORDS_NEW)}[b]
    arms = {"F": (a, s), "F2": (a, s % 3 + 1), "SB": ("formxtb2000", s), "T": (th, s), "T2": (th, s % 3 + 1)}
    V = {k: {r["id"]: (r["pred"] if ok_(r) else None) for r in _rows(f"{XRES}/opt_{m}_{b}_{x}_s{y}.jsonl")} for k, (x, y) in arms.items()}
    V["R"] = {r["id"]: (r["pred"] if ok_(r) else None) for r in _rows(f"{XRES}/repair_{m}_{b}_{a}_s{s}.jsonl")}
    return V


def geo_vals(m, s):
    import analyze_n10 as N
    from analyze_hogc import load, outs
    arms = {"F": ("fact", s), "F2": ("fact", s % 3 + 1), "SB": ("thinkfactb2000", s), "T": (H.GEO_THINK, s), "T2": (H.GEO_THINK, s % 3 + 1)}
    rows = {k: load(f"S2_HOG_{m}_geo_{x}_s{y}") or {} for k, (x, y) in arms.items()}

    def one(j):
        r = rows[j[0]][j[1]]
        if not N.geo_check(r)[0]:
            return None
        o = outs(r)
        return tuple(o) if o and None not in o else None
    jobs = [(k, i) for k, R in rows.items() for i in R]
    with ThreadPoolExecutor(int(os.environ.get("NPROC", 16))) as ex:
        res = dict(zip(jobs, ex.map(one, jobs)))
    V = {k: {} for k in arms}
    for (k, i), v in res.items():
        V[k][i] = v
    V["R"] = {}
    return V


def pseudo(vals, eq):
    best, bc = None, 0
    for c in (vals.get(k) for k in ORDER if k in VOTERS):
        n = sum(eq(c, vals.get(v)) for v in VOTERS) if c is not None else 0
        if n > bc:
            best, bc = c, n
    return best


def relabel(it, vals, eq):
    g = pseudo(vals, eq)
    hit = lambda k: g is not None and eq(vals.get(k), g)
    out = dict(it, f_ok=hit("F"), t_ok=hit("T"), t2=(hit("T2"), it["t2"][1]))
    if it.get("sb"):
        out["sb"] = (it["sb"][0], hit("SB"), it["sb"][2])
    if it.get("r"):
        out["r"] = (it["r"][0], hit("R"), it["r"][2])
    return out


def main():
    models = [a for a in sys.argv[1:] if not a.startswith("--")] or ["q14a", "q8b", "n3n", "q35"]
    util = lambda P: {p: a - LAM * t for p, (a, t) in P.items()}
    rng = random.Random(0); reg = defaultdict(list); rows = []; flags = Counter()
    for name, items in H.cells(models):
        m, b, s = name
        geo = b == "geometry"; V = geo_vals(m, s) if geo else word_vals(m, b, s); eq = eq_geo if geo else eq_word
        P = [relabel(it, {k: V[k].get(it["id"]) for k in V}, eq) for it in items]
        for it, p in zip(items, P):   # pseudo-labels vs true labels, per arm (diagnostic only)
            for k, x, y in (("F", it["f_ok"], p["f_ok"]), ("T", it["t_ok"], p["t_ok"])):
                flags[(m, k, x, y)] += 1
        U = util(H.policies(items)); best = max(U.values()); n = len(items)
        r = defaultdict(float); picks = Counter()
        for _ in range(NP):
            idx = rng.sample(range(n), min(K, n))
            Ul = util(H.policies([items[j] for j in idx])); Up = util(H.policies([P[j] for j in idx]))
            lf = max(Up, key=Up.get); picks[lf] += 1
            r["label-free"] += (best - U[lf]) / NP; r["labelled"] += (best - U[max(Ul, key=Ul.get)]) / NP
        r["always SB->T->T"] = best - U["SB->T->T"]
        Ufull = util(H.policies(P)); r["label-free, all items"] = best - U[max(Ufull, key=Ufull.get)]
        for k, v in r.items():
            reg[k].append(v)
        rows.append((name, n, r, picks.most_common(2), max(U, key=U.get)))
    print(f"{len(rows)} cells, k = {K}, lambda {LAM}, votes {'+'.join(VOTERS)}: mean regret "
          + ", ".join(f"{k} {sum(v) / len(v):.2f}" for k, v in reg.items()))
    q8 = [x for x in rows if x[0][:2] == ("q8b", "bwor")]
    if q8:
        print(f"  Qwen3-8B BWOR ({len(q8)} cells): label-free {sum(x[2]['label-free'] for x in q8) / len(q8):.2f}, "
              f"labelled {sum(x[2]['labelled'] for x in q8) / len(q8):.2f}")
    for m in models:
        for k in ("F", "T"):
            c = {xy: flags[(m, k, *xy)] for xy in ((True, True), (True, False), (False, True), (False, False))}; tot = max(1, sum(c.values()))
            print(f"  {m} {k}: pseudo-label = true label on {100 * (c[(True, True)] + c[(False, False)]) / tot:.1f}% of rows; right but pseudo-wrong "
                  f"{c[(True, False)]}, wrong but pseudo-right {c[(False, True)]}")
    print("per cell: n | regret label-free / labelled / always SB->T->T | label-free picks (of 1,000) | best policy on the full cell")
    for name, n, r, pk, bp in rows:
        print(f"  {' '.join(map(str, name)):20} {n:4d} | {r['label-free']:5.2f} / {r['labelled']:5.2f} / {r['always SB->T->T']:5.2f} | "
              + ", ".join(f"{p} {c}" for p, c in pk) + f" | {bp}")


if __name__ == "__main__":
    main()
