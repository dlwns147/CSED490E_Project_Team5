"""Task 1 kit (side/README.md, "Goal for the teammate", set 2026-11-11): the fresh-figure stage of MechGeo's 44 IMO problems (SIDE-GT-MG), rerun from the
stored certificates, with the figure solver as the one part you replace.

A problem counts whole when one of its statements is judged faithful (verdicts against MechGeo's audited Lean statements), its certificate passes
geo_check.py, and every step of its proof holds on 8 of 8 fresh figures. The stored run counted 13 per arm. 8 more problems were lost only because the
figure solver built fewer than 8 fresh figures; every figure it did build passed.

A fresh figure is accepted only if, checked here and not by the solver:
  - every hypothesis and order condition of the statement holds (residual at most 1e-9, order values above 0) and its points are apart;
  - its unsigned angles have the orientation of the proof's own figure (the configuration the proof was found on);
  - it has no more chance coincidences (collinear triples) than the proof's figure, so it is not a degenerate case;
  - it is not similar to the proof's figure or to a figure already accepted (a rotated or scaled copy proves nothing new).
Then the proof's auxiliary points are rebuilt on it, and every step's conclusion and premises must hold.

Plug in your solver: a Python module (on the path) with `figures(dsl, n, seed)` returning a list of candidate figures, each a list of complex numbers in the
statement's point order (geo_decl.parse). The default is geo_decl.solve with the stored run's 240 starts, the solver that produced the stored count.
usage: python side/kit_fresh.py <kit dir> [--solver module] [--n 8] [--only <problem id>] [--workers W (default solver only)]
The kit dir holds certs_nl/, certs_lean/ (certificates), verdicts.json and checked.json (geo_check results); frozen copies, not in the repository.
Prints, per arm, the whole problems counted, the problems lost at the fresh-figure rule, and the CPU seconds per statement."""
import importlib, json, os, sys, time
import numpy as np

for k, v in dict(GT_DECL_STARTS="240", GT_SOUND="1", GT_STRICT="1", GT_SQ="1", OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1").items():
    os.environ.setdefault(k, v)   # the stored run's settings (nlp_data/geo/mg_close.sh): 240 starts per statement

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geo_closure as GC   # noqa: E402
import geo_decl as GD   # noqa: E402

SKIP = ("given_", "const", "tdiff", "cyclic_group")


def default_figures(dsl, n, seed=0):
    """the stored run's solver: least squares from random starts, generic figures first (geo_decl.solve), all of them, in the order found"""
    if dsl not in GD._cache:
        GD._cache[dsl] = GD.solve(dsl)
    return list(GD._cache[dsl][3])


def _shape(P):
    """the figure up to similarity: points 0 and 1 sent to 0 and 1"""
    P = np.asarray(P, complex)
    return (P - P[0]) / (P[1] - P[0])


def valid(dsl, P, ref):
    """None if P is an acceptable fresh figure of the statement for the proof found on figure ref, else the reason"""
    pts, hyps, goal = GD.parse(dsl)
    ix = {p: i for i, p in enumerate(pts)}
    H = [(k, [ix[x] if isinstance(x, str) else x for x in a]) for k, a in hyps]
    G = (goal[0], [ix[x] if isinstance(x, str) else x for x in goal[1]])
    P = np.asarray(P, complex)
    if P.shape != (len(pts),) or not np.isfinite(P).all():
        return "wrong number of points or not finite"
    for k, a in H:
        if k in GD.FACT and max(abs(np.asarray(GD.residual(k, a, P))), default=0) > 1e-9:
            return f"hypothesis {k} fails"
        if k in GD.ORDER and any(x <= 0 for x in GD.order_value(k, a, P)):
            return f"order condition {k} fails"
    d = np.abs(P[:, None] - P[None, :])[np.triu_indices(len(P), 1)]
    if d.min() < 1e-3 or d.max() > 1e3:
        return "points not apart"
    if GD.signature(H, G, P) != GD.signature(H, G, ref):
        return "another configuration"
    if GD.coincidences(P) > GD.coincidences(ref):
        return "more coincidences than the proof's figure"
    return None


def holds(cert, P, pts):
    """do all of the proof's steps hold on figure P (auxiliary points rebuilt from their definitions)"""
    C = {p: (float(z.real), float(z.imag)) for p, z in zip(pts, P)}
    for nm, c in cert["defs"]:
        q = GC.numeric_cand(c, C)
        if q is None:
            return False
        C[nm] = q[0]
    names = list(C)
    ix = {p: i for i, p in enumerate(names)}
    XY = [C[p] for p in names]
    facts = [r["concl"] for r in cert["rows"]] + [h for r in cert["rows"] for h in r.get("prem", [])]
    for F in facts:
        if not F or F[0] in SKIP:
            continue
        try:
            Fi = (F[0], *[ix[x] if isinstance(x, str) and x in ix else x for x in F[1:]])
            if not GC.num_fact(Fi, XY):
                return False
        except (KeyError, IndexError, ValueError, ZeroDivisionError):
            return False
    return True


def score_cert(cert, solver, n):
    """-> (fresh figures accepted, of which the proof holds on all, seconds)"""
    t0 = time.time()
    dsl = cert["dsl"]
    pts = GD.parse(dsl)[0]
    try:
        ref_names, ref_xy, _, _ = GD.figure(dsl, 0)   # the proof's own figure, as the closure saw it
    except ValueError:
        return 0, 0, time.time() - t0
    ref = np.array([complex(*ref_xy[ref_names.index(p)]) for p in pts])
    try:
        cands = solver(dsl, 4 * n, 1)
    except Exception:
        cands = []
    acc, shapes = 0, [_shape(ref)]
    held = 0
    for P in cands:
        if acc >= n:
            break
        if valid(dsl, P, ref) is not None:
            continue
        s = _shape(P)
        if any(np.abs(s - t).max() < 1e-3 for t in shapes):
            continue
        shapes.append(s)
        acc += 1
        held += holds(cert, np.asarray(P, complex), pts)
    return acc, held, time.time() - t0


def _one(a):
    (pid, sample, cert), n = a
    return (pid, sample, *score_cert(cert, default_figures, n))


def main():
    kit = sys.argv[1]
    opt = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
    n = int(opt("--n", 8))
    solver = getattr(importlib.import_module(opt("--solver", "")), "figures") if "--solver" in sys.argv else default_figures
    only = opt("--only", None)
    V = json.load(open(os.path.join(kit, "verdicts.json")))
    ok = json.load(open(os.path.join(kit, "checked.json")))
    workers = int(opt("--workers", 1))
    for arm in ["nl", "lean"]:
        d = os.path.join(kit, f"certs_{arm}")
        whole, lost, secs, rows, todo = set(), set(), [], [], []
        for fn in sorted(os.listdir(d)):
            pid, sample = fn.split("_", 1)[1].rsplit("_", 2)[0], int(fn.rsplit("_", 2)[1])
            if only and pid != only:
                continue
            if V.get(f"{arm}|{pid}:{sample}", {}).get("verdict") != "faithful" or not ok.get(f"{arm}/{fn}"):
                continue
            todo.append((pid, sample, json.load(open(os.path.join(d, fn)))))
        one = lambda t: (t[0], t[1], *score_cert(t[2], solver, n))
        if workers > 1:   # one process per statement (the solver holds the CPU); fork, so a --solver module is shared
            from multiprocessing import get_context
            with get_context("fork").Pool(workers) as pool:
                res = pool.imap_unordered(_one, [(t, n) for t in todo]) if solver is default_figures else map(one, todo)
                res = list(res)
        else:
            res = map(one, todo)
        for pid, sample, acc, held, sec in res:
            print(f"  {arm} {pid} {sample}: fresh {acc}, proof holds on {held}, {sec:.0f} s", flush=True)
            secs.append(sec)
            rows.append((pid, sample, acc, held))
            (whole if acc >= n and held == acc else lost).add(pid)
        lost -= whole
        print(f"{arm}: whole problems {len(whole)}; faithful certified problems lost at the fresh-figure rule {len(lost)} {sorted(lost)}; "
              f"{len(secs)} statements, {np.mean(secs) if secs else 0:.1f} CPU s each")


if __name__ == "__main__":
    main()
