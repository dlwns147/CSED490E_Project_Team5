"""Task 2 kit (side/README.md, "Target that beats related work", set 2026-11-13): HAGeo-409 coverage, scored from certificates alone.

A row counts when its certificate in <cert dir> passes three checks made here, not by the prover:
  1. it is bound to the frozen statement: the certificate's statement is the row's, its goal is the statement's goal, and every fact it
     takes about the statement's own points is one the construction gives (geo_check.py trusts the certificate's fact list, so this is
     the kit's job);
  2. geo_check.py accepts it (exact fractions, independent of the engine);
  3. on 8 of 8 fresh figures of the statement (Newclid's builder, seeds 1-8), the auxiliary points rebuilt from their definitions, every
     step's conclusion and premises and the goal hold.
The kit compares the count with the reference run (SIDE-GT-H409, 263 counted at 1,800 s on one core per row), paired by row and by
HAGeo's difficulty band, and reports CPU time from the prover's own result rows (`sec`, times --cores).

A certificate is `h409_<id>_<sample>_sat.txt.json` as `geo_closure.py cert` writes it; any other prover writes the same format, or
extends geo_check.py and this kit for a new kind of step (the control below must then still count 0).

usage:
  python side/kit_h409.py score <kit dir> <cert dir> [--times <run rows .jsonl>]... [--cores C] [--workers W]
  python side/kit_h409.py control <kit dir> [--workers W]
  python side/kit_h409.py build <kit dir> <reference run dir>      (once, by us: freezes rows, reference certificates and counts)

--control scores planted false certificates made from the reference certificates, three per certificate: (a) the goal replaced by a
false relation of the same kind (false on two figures by at least 1e-3), the proof unchanged (reported also for geo_check alone); (b) the
same false goal assumed as a fact of the statement (a prover that assumes what it proves); (c) one coefficient of the goal's combination doubled (goals other than cyclic and midp, which geo_check reads from
groups or from any one of several combinations). A sound
judge counts none of them. The kit dir holds rows.jsonl (the 409 frozen statements), certs/ (reference certificates), ref.json (the
reference count and times); frozen copies, not in the repository."""
import glob, json, math, os, random, re, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import geo_check as CK
import geo_closure as GC

SKIP = ("given_", "const", "tdiff", "cyclic_group")
KNOWN = {"coll", "para", "perp", "cong", "half", "eqangle", "eqratio", "cyclic", "circle", "sqperp", "sqcong", "sqmid", "sqmedian", "simtri",
         "simtri2"}   # the kinds geo_closure.num_fact checks; it passes any other kind, so the kit checks midp itself and rejects the rest
BANDS = [(1, 3), (3, 4), (4, 5), (5, 6), (6, 7.01)]
LIMIT = int(os.environ.get("KIT_LIMIT", "900"))   # seconds per certificate
CERT = re.compile(r"h409_(.+)_(\d+)_sat\.txt\.json$")


def key(F):
    """a fact up to the symmetries of its statement (point order on a line or circle, the order of pairs), so that the same fact written
    in another order compares equal; kinds without a known symmetry compare as written"""
    k, *a = F
    S, P = frozenset, lambda i: frozenset(a[i:i + 2])
    if k in ("coll", "cyclic", "collx"):
        return k, S(a)
    if k in ("para", "perp", "cong", "sqcong", "sqperp"):
        return k, S([P(0), P(2)])
    if k == "midp":
        return k, a[0], S(a[1:])
    if k == "circle":
        return k, a[0], S(a[1:])
    if k in ("eqangle", "eqratio") and len(a) == 8:
        l = [P(0), P(2), P(4), P(6)]
        forms = [(0, 1, 2, 3), (2, 3, 0, 1), (1, 0, 3, 2), (3, 2, 1, 0), (0, 2, 1, 3), (1, 3, 0, 2), (2, 0, 3, 1), (3, 1, 2, 0)]
        return k, min(tuple(tuple(sorted(l[i])) for i in f) for f in forms)
    return (k, *a)


def groups(F, kind, share):
    """the construction's lines (kind coll, share 2) or circles (kind cyclic, share 3): its facts of that kind merged while two share that
    many points. Newclid lists a different subset of each circle's 4-point facts from build to build, so a certificate's fact is checked
    against the merged circle, not against the list"""
    G = [set(q[1:]) for q in F if q[0] == kind]
    merged = True
    while merged:
        merged = False
        for i in range(len(G)):
            for j in range(i + 1, len(G)):
                if len(G[i] & G[j]) >= share:
                    G[i] |= G.pop(j)
                    merged = True
                    break
            if merged:
                break
    return G


def stmt(dsl):
    """the statement's figure facts (up to symmetry), its lines and circles, and its goal, as geo_closure.cert_file reads them"""
    n, x, f, g = GC.figure(dsl)
    f = [tuple(q[:-1] if q[-1] == "_" else q) for q in f]
    return n, x, ({key(q) for q in f}, {"coll": groups(f, "coll", 2), "cyclic": groups(f, "cyclic", 3)}), tuple(g[0])


def bound(cert, dsl):
    """None if the certificate proves the frozen statement, else the reason"""
    if cert.get("dsl") != dsl:
        return "another statement"
    n, _, (F, L), g = stmt(dsl)
    if tuple(cert["goal"]) != g:
        return "another goal"
    aux = {nm for nm, _ in cert["defs"]}
    for f in cert["facts"]:
        if aux & set(f[1:]) or key(tuple(f)) in F:
            continue
        if f[0] in L and any(set(f[1:]) <= G for G in L[f[0]]):
            continue
        return f"fact {f} is not given by the construction"
    return None


def fact_ok(F, C):
    """is fact F true on the named coordinates C"""
    if not F or F[0] in SKIP:
        return True
    if F[0] == "midp":
        m, a, b = (np.asarray(C[p]) for p in F[1:4])
        return float(np.hypot(*(2 * m - a - b))) < 1e-6 * max(float(np.hypot(*(a - b))), 1e-3)
    if F[0] not in KNOWN:
        return False
    names = list(C)
    ix = {p: i for i, p in enumerate(names)}
    try:
        return bool(GC.num_fact((F[0], *[ix[x] if isinstance(x, str) and x in ix else x for x in F[1:]]), [C[p] for p in names]))
    except (KeyError, IndexError, ValueError, ZeroDivisionError):
        return False


def fresh(cert, n=8):
    """-> (figures built, figures on which every step and the goal hold)"""
    facts = [r["concl"] for r in cert["rows"]] + [h for r in cert["rows"] for h in r.get("prem", [])] + [cert["goal"]]
    built = held = 0
    for sd in range(1, n + 1):
        try:
            nm, xy, _, _ = GC.figure(cert["dsl"], seed=sd)
        except Exception:
            continue
        C = dict(zip(nm, xy))
        ok = True
        for a, c in cert["defs"]:
            q = GC.numeric_cand(c, C)
            if q is None:
                ok = False
                break
            C[a] = q[0]
        if not ok:
            continue
        built += 1
        held += all(fact_ok(F, C) for F in facts)
    return built, held


def judge(cert, dsl, n=8):
    """-> (counted, reason)"""
    t0 = time.time()
    try:
        why = bound(cert, dsl)
    except Exception as e:
        why = f"statement does not build: {type(e).__name__}"
    if why:
        return False, why, time.time() - t0
    try:
        CK.check(cert)
    except Exception as e:
        return False, f"geo_check: {str(e)[:120]}", time.time() - t0
    b, h = fresh(cert, n)
    if b < n or h < b:
        return False, f"fresh figures: {h} of {b} hold, {n} needed", time.time() - t0
    return True, "", time.time() - t0


def band(d):
    return next(k for k, (a, b) in enumerate(BANDS) if a <= d < b)


class _Late(Exception):
    pass


def _alarm(sec):
    """a per-item time limit in the worker (a statement whose figure never builds must not stall the kit)"""
    import signal

    def late(*_):
        raise _Late()
    signal.signal(signal.SIGALRM, late)
    signal.alarm(int(sec))


def _job(a):
    rid, dsl, path = a
    try:
        cert = json.load(open(path))
    except Exception as e:
        return rid, False, f"unreadable: {type(e).__name__}", 0.0
    t0 = time.time()
    _alarm(LIMIT)
    try:
        return (rid, *judge(cert, dsl))
    except _Late:
        return rid, False, f"judge took over {LIMIT} s", time.time() - t0
    finally:
        _alarm(0)


def pmap(f, xs, workers):
    out = []
    if workers > 1:
        from multiprocessing import get_context
        with get_context("fork").Pool(workers) as pool:
            for k, r in enumerate(pool.imap_unordered(f, xs), 1):
                out.append(r)
                if k % 25 == 0:
                    print(f"  ... {k} of {len(xs)}", file=sys.stderr, flush=True)
        return out
    return list(map(f, xs))


def certs_in(d):
    out = {}
    for p in sorted(glob.glob(os.path.join(d, "**", "*.json"), recursive=True)):
        m = CERT.search(os.path.basename(p))
        if m:
            out.setdefault(m.group(1), p)
    return out


def score(kit, cdir, times, cores, workers):
    rows = [json.loads(l) for l in open(os.path.join(kit, "rows.jsonl"))]
    ref = json.load(open(os.path.join(kit, "ref.json")))
    C = certs_in(cdir)
    res = {r[0]: r for r in pmap(_job, [(r["id"], r["dsl"], C[r["id"]]) for r in rows if r["id"] in C], workers)}
    got = {i for i, (_, ok, _, _) in res.items() if ok}
    for i, (_, ok, why, s) in sorted(res.items()):
        if not ok:
            print(f"  not counted {i}: {why}")
    R = set(ref["counted"])
    D = {r["id"]: r["difficulty"] for r in rows}
    print(f"counted {len(got)} of {len(rows)} ({len(C)} certificates); reference {len(R)}; HAGeo 287 at K = 8,192, 263 at K = 2,048")
    print("  by band: " + "; ".join(f"[{a}, {min(b, 7):g}) {sum(band(D[i]) == k for i in got)} vs {sum(band(D[i]) == k for i in R)} of "
                                    f"{sum(band(D[i]) == k for i in D)}" for k, (a, b) in enumerate(BANDS)))
    gain, lost = sorted(got - R), sorted(R - got)
    # exact two-sided sign test on the rows that differ
    m, k = len(gain) + len(lost), min(len(gain), len(lost))
    p = min(1.0, 2 * sum(math.comb(m, j) for j in range(k + 1)) / 2 ** m) if m else 1.0
    print(f"  vs reference: +{len(gain)} {gain}, -{len(lost)} {lost}; sign test p = {p:.3g}")
    print(f"  judge CPU {sum(r[3] for r in res.values()):.0f} s")
    if times:
        T = {}
        for f in times:
            for l in open(f):
                x = json.loads(l)
                T[x["id"]] = x
        sec = [cores * (T[i].get("sec") or 0) for i in T]
        print(f"  prover CPU ({cores} core(s) per row): {sum(sec) / 3600:.1f} core-hours over {len(T)} rows, {np.mean(sec):.0f} s per row")
        for B in [1800 * 2 ** j for j in range(7)]:
            within = {i for i in got if i in T and cores * (T[i].get("sec") or 1e18) <= B}
            print(f"    counted within {B:>7,} core-s per row: {len(within)}")


def false_goal(dsl, g, rng):
    """a relation of the goal's kind on the statement's points, false on figures 0 and 1 by at least 1e-3, or None"""
    figs = [GC.figure(dsl, seed=s) for s in (0, 1)]
    names = figs[0][0]
    for _ in range(200):
        a = list(g[1:])
        a[rng.randrange(len(a))] = rng.choice(names)
        cand = (g[0], *a)
        if g[0] in ("coll", "cyclic", "midp") and len(set(a)) < len(a) or any(a[i] == a[i + 1] for i in range(0, len(a) - 1, 2)):
            continue   # a repeated point makes the relation degenerate (true on every figure), not false
        if cand != tuple(g) and all(not fact_ok_tol(cand, dict(zip(f[0], f[1]))) for f in figs):
            return cand
    return None


def fact_ok_tol(F, C, tol=1e-3):
    if F[0] == "midp":
        m, a, b = (np.asarray(C[p]) for p in F[1:4])
        return float(np.hypot(*(2 * m - a - b))) < tol * max(float(np.hypot(*(a - b))), 1e-3)
    names = list(C)
    ix = {p: i for i, p in enumerate(names)}
    return bool(GC.num_fact((F[0], *[ix[x] for x in F[1:]]), [C[p] for p in names], tol=tol))


def _plants(a):
    _alarm(4 * LIMIT)
    try:
        return _plants1(a)
    except _Late:
        return [(a[0], "time limit", (False, f"plants took over {4 * LIMIT} s"))]
    finally:
        _alarm(0)


def _plants1(a):
    rid, dsl, path, seed = a
    cert = json.load(open(path))
    rng = random.Random(seed)
    out = []
    fg = None
    if cert["goal"][0] in KNOWN | {"midp"}:
        try:
            fg = false_goal(dsl, tuple(cert["goal"]), rng)
        except Exception:
            fg = None
    if fg:
        bad = dict(cert, goal=list(fg))
        out.append((rid, "a false goal", judge(bad, dsl)[:2]))
        try:
            CK.check(bad)
            alone = (True, "")
        except Exception as e:
            alone = (False, f"geo_check: {str(e)[:60]}")
        out.append((rid, "a false goal, geo_check alone", alone))
        out.append((rid, "the false goal assumed", judge(dict(bad, facts=cert["facts"] + [list(fg)]), dsl)[:2]))
    ch = [c for c in cert["chases"] if c["ctx"] == -1]
    if ch and ch[0]["rows"] and cert["goal"][0] not in ("cyclic", "midp"):   # these goals are checked by groups or by any one of several combinations
        k = sorted(ch[0]["rows"])[0]
        c2 = [dict(c, rows={**c["rows"], k: str(2 * CK.Fr(c["rows"][k]))}) if c is ch[0] else c for c in cert["chases"]]
        out.append((rid, "a coefficient doubled", judge(dict(cert, chases=c2), dsl)[:2]))
    return out


def control(kit, workers):
    rows = {r["id"]: r for r in map(json.loads, open(os.path.join(kit, "rows.jsonl")))}
    C = certs_in(os.path.join(kit, "certs"))
    res = [p for ps in pmap(_plants, [(i, rows[i]["dsl"], C[i], k) for k, i in enumerate(sorted(C)) if i in rows], workers) for p in ps]
    by = {}
    for rid, kind, (ok, why) in res:
        by.setdefault(kind, []).append((rid, ok, why))
    for kind, xs in by.items():
        bad = [r for r, ok, _ in xs if ok]
        why = {}
        for _, ok, w in xs:
            if not ok:
                w = w.split(":")[0] if w.startswith(("geo_check", "fact")) else w.split(",")[0]
                why[w] = why.get(w, 0) + 1
        print(f"control, {kind}: {len(xs)} plants; counted {len(bad)} (must be 0) {bad}; rejected by {why}")
    J = [ok for _, kind, (ok, _) in res if "alone" not in kind]
    print(f"control: {len(J)} plants from {len(C)} reference certificates; counted {sum(J)} (must be 0); the 'geo_check alone' line is "
          "the checker without the kit's binding, for reference")


def build(kit, run):
    """freeze the reference: rows, the reference certificates (fixed rows' certificates replace the first ones) and the counted ids"""
    import shutil
    src = os.path.join(os.environ.get("POC_DATA", "../nlp_data"), "geo", "hageo409", "rows.jsonl")
    os.makedirs(os.path.join(kit, "certs"), exist_ok=True)
    shutil.copyfile(src, os.path.join(kit, "rows.jsonl"))
    rows = [json.loads(l) for l in open(src)]
    C = certs_in(os.path.join(run, "certs"))
    C.update(certs_in(os.path.join(run, "certs_fix")))
    for i, p in C.items():
        shutil.copyfile(p, os.path.join(kit, "certs", os.path.basename(p)))
    T = {}
    for f in sorted(glob.glob(os.path.join(run, "gt_h409_*.jsonl"))) + [os.path.join(run, "gt_fix.jsonl")]:
        for l in open(f):
            x = json.loads(l)
            T[x["id"]] = {"sec": x.get("sec"), "proved": x.get("proved"), "timeout": x.get("timeout"), "err": x.get("err")}
    res = pmap(_job, [(r["id"], r["dsl"], os.path.join(kit, "certs", os.path.basename(C[r["id"]]))) for r in rows if r["id"] in C], WORKERS)
    counted = sorted(i for i, ok, _, _ in res if ok)
    json.dump({"counted": counted, "times": T, "note": "SIDE-GT-H409 (jobs 1341669-70, certificates 1344459, fix 1344462): 1,800 s on one "
               "core per row, k = -300, GT_SOUND GT_STRICT GT_SQ GT_SECOND GT_LUBY"}, open(os.path.join(kit, "ref.json"), "w"))
    print(f"kit built: {len(rows)} rows, {len(C)} reference certificates, {len(counted)} counted through the kit")
    for i, ok, why, _ in res:
        if not ok:
            print(f"  not counted {i}: {why}")


WORKERS = 8


def main():
    global WORKERS
    opt = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
    workers = WORKERS = int(opt("--workers", 8 if sys.argv[1] == "build" else 1))
    if sys.argv[1] == "build":
        return build(sys.argv[2], sys.argv[3])
    if sys.argv[1] == "control":
        return control(sys.argv[2], workers)
    times = [a for i, a in enumerate(sys.argv) if i and sys.argv[i - 1] == "--times"]
    score(sys.argv[2], sys.argv[3], times, float(opt("--cores", 1)), workers)


if __name__ == "__main__":
    main()
