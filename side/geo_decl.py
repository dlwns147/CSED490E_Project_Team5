"""SIDE-GT-DECL: a statement as points, hypotheses and a goal, with no construction order. AlphaGeometry's language builds each point from earlier ones,
so "EF = EG = EC" or a point fixed by two angle conditions cannot be written, and half of the translations of held-out problems come back UNEXPRESSIBLE.
The closure (geo_closure.py) needs only a figure and facts, so it does not need a construction. The figure comes from least squares from random starts
(the idea of Krueger, Han, Selsam, 2012.02590, diagrams by numerical optimisation), and the statement's hypotheses are the facts.
A statement is one line:
  decl: a b c d; para a b c d; cong a b c d; between a e c ? cyclic a b d e
Facts, which the closure may use: coll, para, perp, cong, cyclic, midp, circle (centre, then points on it), eqangle (directed, modulo pi: the angle from
line ab to line cd equals the one from line ef to line gh), uangle a b c d e f (the angles abc and def, unsigned, are equal), uconst a b c 60 (angle abc, unsigned, in
degrees), eqratio (ab/cd = ef/gh), aconst a b c d 60 (angle from ab to cd, in degrees), rconst a b c d 2/3 (ab/cd). An unsigned angle becomes a directed one with the
orientation of the figure: the statement fixes the configuration by its order conditions, and the figures kept share one orientation.
Order, which only selects the figure: between a b c (b strictly inside segment ac; it also gives the fact coll a b c), inside p a b c, sameside p q a b, opposite p q a b, acute a b c (angle at b),
obtuse a b c, convex a b c d, ncoll a b c. Distinct names are distinct points.
  python side/geo_decl.py one '<statement>'     (solve and print the figures found and whether the goal holds on them)
  python side/geo_decl.py guard '<statement>'   (the status alone, for geo_translate.py)
  python side/geo_decl.py reduce <rows.jsonl> <out.jsonl> [--workers W]   (SIDE-GT-REDUCE: hypotheses the others imply become goals)
  python side/geo_decl.py ndg <rows.jsonl> <out.jsonl> [--workers W] [--limit S]   (SIDE-GT-NDG: degenerate figures on which the goal fails)"""
import cmath, itertools, json, math, os, signal, sys, time
import numpy as np

FACT = {"coll": 3, "para": 4, "perp": 4, "cong": 4, "cyclic": 4, "midp": 3, "circle": 3, "eqangle": 8, "eqratio": 8, "aconst": 5, "rconst": 5, "uangle": 6, "uconst": 4}
ORDER = {"between": 3, "inside": 4, "sameside": 4, "opposite": 4, "acute": 3, "obtuse": 3, "convex": 4, "ncoll": 3, "flip": 6, "flip2": 6, "flipt": 5, "flipz": 6}   # flip*: a reading of a proof, negated (SIDE-GT-LEAN-RD)
GOAL = ("coll", "para", "perp", "cong", "cyclic", "midp", "circle", "eqangle", "eqratio", "uangle")
MARGIN = 0.02  # how far an order condition must hold, as a fraction of the sizes in it; a figure is rejected only by the exact test
STARTS, KEEP = int(os.environ.get("GT_DECL_STARTS", 80)), 12


def parse(text):
    """-> points, hypotheses [(name, args)], goal (name, args). Raises ValueError with a message the model can read."""
    t = text.strip()
    if not t.startswith("decl:"):
        raise ValueError("a statement starts with decl:")
    if " ? " not in t:
        raise ValueError('no " ? " before the goal')
    body, goal = t[5:].split(" ? ", 1)
    parts = [p.strip() for p in body.split(";") if p.strip()]
    if not parts:
        raise ValueError("no points")
    pts = parts[0].split()
    if len(set(pts)) != len(pts):
        raise ValueError("a point is listed twice")
    hyps = []

    def item(s, allowed):
        w = s.split()
        name, args = w[0], w[1:]
        if name not in allowed:
            raise ValueError(f"unknown predicate {name}")
        const = name in ("aconst", "rconst", "uconst")
        names = args[:-1] if const else args
        need = (FACT | ORDER).get(name)
        if len(args) < need or (name not in ("coll", "cyclic", "circle") and len(args) != need):
            raise ValueError(f"{name} takes {need} arguments, got {len(args)}")
        for q in names:
            if q not in pts:
                raise ValueError(f"{q} is not in the list of points")
        if name in ("coll", "cyclic", "circle") and len(set(names)) != len(names):
            raise ValueError(f"{name} repeats a point")
        if name in ("aconst", "uconst"):
            args = names + [float(args[-1].rstrip("o"))]
        if name == "rconst":
            p, _, q = args[-1].partition("/")
            args = names + [float(p) / float(q or 1)]
        return name, args
    for s in parts[1:]:
        hyps.append(item(s, set(FACT) | set(ORDER)))
        if hyps[-1][0] == "between":    # a point inside a segment is on its line, which the closure may use
            hyps.append(("coll", list(hyps[-1][1])))
    return pts, hyps, item(goal.strip(), set(GOAL))


def _cos(P, a, b, c):
    u, v = P[a] - P[b], P[c] - P[b]
    return (u.conjugate() * v).real / (abs(u) * abs(v) + 1e-12)


def _turn(P, a, b, c):
    """the orientation of angle abc: +1 or -1"""
    return 1 if ((P[a] - P[b]).conjugate() * (P[c] - P[b])).imag > 0 else -1


def signature(H, goal, P):
    """the orientation of every unsigned angle equality on this figure"""
    return tuple(_turn(P, *a[:3]) * _turn(P, *a[3:6]) for k, a in H + [goal] if k == "uangle")


def directed(k, a, P, pts):
    """a fact over names, as the closure reads it; an unsigned angle takes the figure's orientation"""
    n = [pts[x] if isinstance(x, int) and j < (4 if k in ("aconst", "rconst") else 3 if k == "uconst" else 99) else x for j, x in enumerate(a)]
    if k == "uangle":
        same = _turn(P, *a[:3]) * _turn(P, *a[3:6]) > 0
        return ("eqangle", n[1], n[0], n[1], n[2], n[4], n[3] if same else n[5], n[4], n[5] if same else n[3])
    if k == "uconst":
        return ("aconst", n[1], n[0], n[1], n[2])
    if k in ("aconst", "rconst"):
        return (k, *n[:4])
    return (k, *n)


def residual(name, a, P):
    """-> list of numbers, all zero exactly when the fact holds; each is scale-free"""
    z = lambda p, q: P[q] - P[p]
    n = lambda c: abs(c) + 1e-12
    if name == "coll":
        return [(z(a[0], a[1]).conjugate() * z(a[0], c)).imag / (n(z(a[0], a[1])) * n(z(a[0], c))) for c in a[2:]]
    if name == "para":
        u, v = z(a[0], a[1]), z(a[2], a[3])
        return [(u.conjugate() * v).imag / (n(u) * n(v))]
    if name == "perp":
        u, v = z(a[0], a[1]), z(a[2], a[3])
        return [(u.conjugate() * v).real / (n(u) * n(v))]
    if name == "cong":
        u, v = abs(z(a[0], a[1])), abs(z(a[2], a[3]))
        return [(u - v) / (u + v + 1e-12)]
    if name == "cyclic":
        out = []
        for d in a[3:]:
            w = (P[a[0]] - P[a[2]]) * (P[a[1]] - P[d]) / ((P[a[1]] - P[a[2]]) * (P[a[0]] - P[d]) + 1e-12)
            out.append(w.imag / (abs(w) + 1))
        return out
    if name == "midp":
        c = P[a[0]] - (P[a[1]] + P[a[2]]) / 2
        s = abs(z(a[1], a[2])) + 1e-12
        return [c.real / s, c.imag / s]
    if name == "circle":
        r = abs(z(a[0], a[1]))
        return [(abs(z(a[0], c)) - r) / (abs(z(a[0], c)) + r + 1e-12) for c in a[2:]]
    if name == "eqangle":
        u = z(a[0], a[1]).conjugate() * z(a[2], a[3])
        v = z(a[4], a[5]).conjugate() * z(a[6], a[7])
        return [(u.conjugate() * v).imag / (n(u) * n(v))]
    if name == "uangle":
        return [_cos(P, a[0], a[1], a[2]) - _cos(P, a[3], a[4], a[5])]
    if name == "uconst":
        return [_cos(P, a[0], a[1], a[2]) - math.cos(math.radians(a[3]))]
    if name == "eqratio":
        x, y = abs(z(a[0], a[1])) * abs(z(a[6], a[7])), abs(z(a[2], a[3])) * abs(z(a[4], a[5]))
        return [(x - y) / (x + y + 1e-12)]
    if name == "aconst":
        u = z(a[0], a[1]).conjugate() * z(a[2], a[3])
        return [(u.conjugate() * cmath.exp(1j * math.radians(a[4]))).imag / n(u)]
    if name == "rconst":
        x, y = abs(z(a[0], a[1])), abs(z(a[2], a[3])) * a[4]
        return [(x - y) / (x + y + 1e-12)]
    raise ValueError(name)


def order_value(name, a, P):
    """-> numbers that are positive exactly when the condition holds, scale-free"""
    z = lambda p, q: P[q] - P[p]
    cr = lambda u, v: (u.conjugate() * v).imag / (abs(u) * abs(v) + 1e-12)
    if name == "between":
        u, v = z(a[1], a[0]), z(a[1], a[2])
        return [-(u.conjugate() * v).real / (abs(u) * abs(v) + 1e-12)]
    if name == "inside":
        p, x, y, w = a
        s = cr(z(x, y), z(x, w))
        s = 1 if s > 0 else -1
        return [s * cr(z(x, y), z(x, p)), s * cr(z(y, w), z(y, p)), s * cr(z(w, x), z(w, p))]
    if name in ("sameside", "opposite"):
        p, q, x, y = a
        v = cr(z(x, y), z(x, p)) * cr(z(x, y), z(x, q))
        return [v if name == "sameside" else -v]
    if name in ("acute", "obtuse"):
        u, v = z(a[1], a[0]), z(a[1], a[2])
        c = (u.conjugate() * v).real / (abs(u) * abs(v) + 1e-12)
        return [c if name == "acute" else -c]
    if name == "convex":
        vs = [cr(z(a[i], a[(i + 1) % len(a)]), z(a[(i + 1) % len(a)], a[(i + 2) % len(a)])) for i in range(len(a))]
        s = 1 if sum(vs) > 0 else -1
        return [s * v for v in vs]
    if name == "ncoll":
        return [abs(cr(z(a[0], a[1]), z(a[0], a[2])))]
    dt = lambda u, v: (u.conjugate() * v).real / (abs(u) * abs(v) + 1e-12)
    if name in ("flip", "flip2"):
        v = cr(z(a[0], a[1]), z(a[0], a[2])) * cr(z(a[3], a[4]), z(a[3], a[5]))
        return [-v if name == "flip" else v]
    if name == "flipt":
        o, p, c, q, e = a
        return [-dt(z(p, o), z(p, c)) * dt(z(q, o), z(q, e))]
    if name == "flipz":
        m, p, e, k, q, c = a
        return [-dt(z(m, p), z(m, e)) * dt(z(k, q), z(k, c))]
    raise ValueError(name)


def solve(text, seed=0, starts=STARTS, keep=KEEP):
    """figures of the statement: least squares from random starts. A figure must satisfy every hypothesis and order condition exactly, with its points apart.
    Of those, the ones with the fewest chance coincidences are kept: a generic point of the solution set has fewest. -> pts, hyps, goal, figures (arrays), how many starts solved"""
    from scipy.optimize import least_squares
    pts, hyps, goal = parse(text)
    ix = {p: i for i, p in enumerate(pts)}
    H = [(k, [ix[x] if isinstance(x, str) else x for x in a]) for k, a in hyps]
    facts = [h for h in H if h[0] in FACT]
    orders = [h for h in H if h[0] in ORDER]
    n = len(pts)

    def f(v):
        P = v[:n] + 1j * v[n:]
        out = []
        for k, a in facts:
            out += residual(k, a, P)
        for k, a in orders:
            out += [max(0.0, MARGIN - x) for x in order_value(k, a, P)]
        d = np.abs(P[:, None] - P[None, :])[np.triu_indices(n, 1)]   # distinct names are distinct points
        out += list(np.maximum(0.0, 0.02 - d))
        return np.array(out)
    rng = np.random.default_rng(seed)
    found = []
    solved = 0
    for _ in range(starts):
        try:
            r = least_squares(f, rng.normal(size=2 * n), method="trf", xtol=1e-14, ftol=1e-14, gtol=1e-14, max_nfev=200)
        except Exception:
            continue
        P = r.x[:n] + 1j * r.x[n:]
        if np.abs(f(r.x)).max() > 1e-9 or not np.isfinite(r.x).all():
            continue
        if any(x <= 0 for k, a in orders for x in order_value(k, a, P)):
            continue
        d = np.abs(P[:, None] - P[None, :])[np.triu_indices(n, 1)]
        if d.min() < 1e-3 or d.max() > 1e3:
            continue
        solved += 1
        found.append((coincidences(P), P))
        if len(found) >= keep * 4:
            break
    if not found:
        return pts, H, goal, [], 0
    low = min(c for c, _ in found)
    gen = [P for c, P in found if c == low]
    return pts, H, goal, gen, solved


def coincidences(P):
    """collinear triples and concyclic quadruples, counted on a sample: the generic figure of a statement has fewest"""
    n = len(P)
    c = 0
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                u, v = P[j] - P[i], P[k] - P[i]
                if abs((u.conjugate() * v).imag) < 1e-7 * abs(u) * abs(v):
                    c += 1
    return c


_cache = {}


def figure(text, seed=0):
    """what geo_closure.figure returns for a translation: names, coordinates, facts over names, goals; seed picks among the figures found"""
    if text not in _cache:
        _cache[text] = solve(text)
    pts, H, goal, figs, _ = _cache[text]
    if not figs:
        raise ValueError("no figure found")
    ix = {p: i for i, p in enumerate(pts)}
    G = (goal[0], [ix[x] if isinstance(x, str) else x for x in goal[1]])
    by = {}
    for P in figs:
        by.setdefault(signature(H, G, P), []).append(P)
    figs = max(by.values(), key=len)   # the facts must be one set: the orientation most figures share
    if seed >= len(figs):
        raise ValueError("no such figure")
    P = figs[seed]
    facts = [directed(k, a, P, pts) for k, a in H if k in FACT]
    return list(pts), [(float(z.real), float(z.imag)) for z in P], facts, [directed(*G, P, pts)]


def guard(text):
    """the checks before the closure -> status, message. status: syntax error / no figure / goal fails / guarded"""
    try:
        pts, H, goal = parse(text)
    except ValueError as e:
        return "syntax error", str(e)
    pts, H, goal, figs, solved = solve(text)
    if not figs:
        return "no figure", "no figure satisfies the hypotheses, with all named points distinct"
    ix = {p: i for i, p in enumerate(pts)}
    a = [ix[x] if isinstance(x, str) else x for x in goal[1]]
    held = sum(all(abs(r) < 1e-6 for r in residual(goal[0], a, P)) for P in figs)
    if not held:
        return "goal fails", f"the goal is false on all {len(figs)} figures of the hypotheses"
    if held < len(figs):
        return "goal fails", f"the goal holds on {held} of {len(figs)} figures of the hypotheses, so a condition is missing"
    if any(goal[0] == k and a == x for k, x in H):
        return "trivial", "the goal is one of the hypotheses"
    return "guarded", f"{len(figs)} figures, {solved} solved"


def holds_on(b, figs_a, pts_a, tol=1e-6):
    """does statement b hold on translation a's figures? Points are matched by name, and b's other points to a's other points by trying every assignment (translations name auxiliary
    points differently). Holding means: on every figure of a that meets b's order conditions, all b's facts and its goal are true, and at least one figure meets them. A fact over a point
    a has no match for is skipped; the goal must be evaluable. -> (holds, share of b's facts evaluated)"""
    import itertools
    pts_b, hyps, goal = parse(b)
    rest_b = [q for q in pts_b if q not in pts_a]
    rest_a = [q for q in pts_a if q not in pts_b]
    maps = []
    k = min(len(rest_a), len(rest_b))
    for sub in itertools.permutations(rest_b, k):
        for img in itertools.combinations(rest_a, k):
            maps.append(dict(zip(sub, img)))
        if len(maps) > 720:
            break
    ix_a = {q: i for i, q in enumerate(pts_a)}
    best = (False, 0.0)
    for m in maps or [{}]:
        name = {q: (q if q in ix_a else m.get(q)) for q in pts_b}

        def args(a):
            out = []
            for x in a:
                if isinstance(x, str):
                    if name[x] is None:
                        return None
                    out.append(ix_a[name[x]])
                else:
                    out.append(x)
            return out
        g = args(goal[1])
        if g is None:
            continue
        facts = [(k_, args(a)) for k_, a in hyps if k_ in FACT and args(a) is not None]
        orders = [(k_, args(a)) for k_, a in hyps if k_ in ORDER and args(a) is not None]
        share = len(facts) / max(1, sum(1 for k_, _ in hyps if k_ in FACT))
        met = [P for P in figs_a if all(x > 0 for k_, a in orders for x in order_value(k_, a, P))]
        if met and all(abs(v) < tol for P in met for k_, a in facts + [(goal[0], g)] for v in residual(k_, a, P)):
            if share >= best[1]:
                best = (True, share)
    return best


def _figs(x):
    try:
        pts, _, _, figs, _ = solve(x["dsl"], seed=0)
        return dict(x, pts=pts, figs=[(list(P.real), list(P.imag)) for P in figs])
    except Exception:
        return dict(x, pts=[], figs=[])


def agree_rows():
    """agree <rows.jsonl> <out.jsonl> [--workers W]: every ordered pair of statements of one problem -> id, a, b, b_holds_on_a, share. SIDE-GT-AGREE rebuilt for statements: two translations
    corroborate each other when each holds on the other's figures"""
    from concurrent.futures import ProcessPoolExecutor
    rows = [json.loads(l) for l in open(sys.argv[2])]
    w = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 4
    with ProcessPoolExecutor(w) as ex:
        F = list(ex.map(_figs, rows))
    with open(sys.argv[3], "w") as f:
        for x in F:
            for y in F:
                if x["id"] != y["id"] or x["sample"] == y["sample"]:
                    continue
                figs = [np.array(re) + 1j * np.array(im) for re, im in x["figs"]]
                try:
                    h, sh = holds_on(y["dsl"], figs, x["pts"]) if figs else (False, 0.0)
                except Exception as e:
                    h, sh = False, 0.0
                f.write(json.dumps(dict(id=x["id"], a=x["sample"], b=y["sample"], b_holds_on_a=bool(h), share=round(sh, 3))) + "\n")


def _clean(text):
    """the statement's hypotheses as written, one per fact or order condition, without repeats; a coll that a between already gives is a repeat. -> points, kept texts, goal text"""
    body, goal = text.strip()[5:].split(" ? ", 1)
    parts = [p.strip() for p in body.split(";") if p.strip()]
    can = lambda w: (w[0], tuple(sorted(w[1:]))) if w[0] in ("coll", "cyclic") else (w[0], tuple(w[1:]))
    seen = {("coll", tuple(sorted(s.split()[1:]))) for s in parts[1:] if s.split()[0] == "between"}
    kept = []
    for s in parts[1:]:
        c = can(s.split())
        if c not in seen or s.split()[0] == "between":
            seen.add(c)
            kept.append(s)
    return parts[0], kept, goal.strip()


def _state(pts, hyps, goal):
    return "decl: " + "; ".join([pts] + hyps) + " ? " + goal


def _jac(facts, P):
    """the facts' residuals differentiated in the coordinates at figure P, each row of unit length -> rows, the fact each row belongs to"""
    n = len(P)
    v = np.r_[P.real, P.imag]

    def R(x):
        Q = x[:n] + 1j * x[n:]
        out = []
        for j, (k, a) in enumerate(facts):
            out += [(j, r) for r in residual(k, a, Q)]
        return out
    owner = [j for j, _ in R(v)]
    J = np.zeros((len(owner), 2 * n))
    for c in range(2 * n):
        e = np.zeros(2 * n)
        e[c] = 1e-6
        J[:, c] = (np.array([r for _, r in R(v + e)]) - np.array([r for _, r in R(v - e)])) / 2e-6
    return J / (np.linalg.norm(J, axis=1, keepdims=True) + 1e-12), owner


def _rk(J):
    return int((np.linalg.svd(J, compute_uv=False) > 1e-5).sum()) if J.size else 0


def redundant(pts, hyps, figs):
    """SIDE-GT-REDUCE: the hypotheses (texts, facts only) whose equations lie in the span of the others' at every figure (Michelucci and Foufou's dependence test at a witness), and the
    number of dependent equations"""
    ix = {p: i for i, p in enumerate(pts.split())}
    H = []
    for s in hyps:
        w = s.split()
        if w[0] in FACT or w[0] == "between":   # a between's line is an equation too, though the condition stays
            _, hh, _ = parse(f"decl: {pts}; {s} ? {'coll ' + ' '.join(pts.split()[:3])}")
            H.append((s if w[0] != "between" else None, hh[-1][0], [ix[x] if isinstance(x, str) else x for x in hh[-1][1]]))
    out, gap = None, 0
    for P in figs[:3]:
        J, own = _jac([(k, a) for _, k, a in H], P)
        r = _rk(J)
        gap = max(gap, J.shape[0] - r)
        here = {H[j][0] for j in range(len(H)) if H[j][0] and _rk(J[[i for i, o in enumerate(own) if o != j]]) == r}
        out = here if out is None else out & here
    return [s for s in hyps if s in (out or ())], gap


def reduce_one(x):
    """SIDE-GT-REDUCE: a hypothesis the others imply may be the claim itself. Drop it and make it a goal: H without h proves h, and H proves the goal, so H without h proves the goal, a
    stronger statement that assumes less. A dependent equation whose hypothesis fails on some figure of the others selects a branch and stays. One basis per first choice. -> the row with
    bases: lists of obligations (statements to prove), the last hypotheses left, and the first reading"""
    pts, hyps, goal = _clean(x["dsl"])
    base = _state(pts, hyps, goal)
    _, _, _, figs, _ = solve(base)
    row = dict(id=x["id"], sample=x["sample"], dsl=x["dsl"], figs=len(figs), gap=0, cands=[], bases=[])
    if not figs:
        return row
    cands, row["gap"] = redundant(pts, hyps, figs)
    status = {}

    def st(h, rest):
        k = (h, tuple(rest))
        if k not in status:
            status[k] = guard(_state(pts, rest, h))[0]
        return status[k]
    row["cands"] = [dict(h=h, status=st(h, [s for s in hyps if s != h])) for h in cands]
    seen = set()
    for first in cands:
        now, ob = list(hyps), []
        order = [first] + [c for c in cands if c != first]
        while True:
            rd = set(redundant(pts, now, figs)[0])
            h = next((c for c in order if c in rd and st(c, [s for s in now if s != c]) == "guarded"), None)
            if h is None:
                break
            now = [s for s in now if s != h]
            w = h.split()
            ob.append(_state(pts, now, f"cong {w[1]} {w[2]} {w[1]} {w[3]}" if w[0] == "circle" and len(w) == 4 else h))   # the closure takes a circle goal of three points or more
        if ob and tuple(ob) not in seen:
            seen.add(tuple(ob))
            row["bases"].append(dict(obligations=ob, left=now))
    return row


class RowLimit(BaseException):
    pass


def reduce_limited(a):
    """reduce_one under a time limit; a statement that runs out is written with timeout set, and counts as undetermined"""
    x, limit = a

    def stop(*_):
        raise RowLimit()
    signal.signal(signal.SIGALRM, stop)
    signal.alarm(limit)
    try:
        return reduce_one(x)
    except RowLimit:
        return dict(id=x["id"], sample=x["sample"], dsl=x["dsl"], figs=None, gap=0, cands=[], bases=[], timeout=limit)
    finally:
        signal.alarm(0)


def reduce_rows():
    """reduce <rows.jsonl> <out.jsonl> [--workers W] [--limit S]: reduce_one on every statement not yet in out, written as each finishes (one 19-point statement held back all others)"""
    from concurrent.futures import ProcessPoolExecutor, as_completed
    rows = [json.loads(l) for l in open(sys.argv[2])]
    w = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 4
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 0
    done = {(r["id"], r["sample"]) for r in map(json.loads, open(sys.argv[3]))} if os.path.exists(sys.argv[3]) else set()
    with ProcessPoolExecutor(w) as ex, open(sys.argv[3], "a") as f:
        for u in as_completed([ex.submit(reduce_limited, (r, limit)) for r in rows if (r["id"], r["sample"]) not in done]):
            f.write(json.dumps(u.result()) + "\n")
            f.flush()


def ndg_one(a):
    """SIDE-GT-NDG: the figures kept for a statement are the generic ones, so a statement false only on a degenerate figure passes every check here. Force each collinear triple the
    statement neither states nor excludes, solve, and test the goal. A line is not a circle: a figure whose cyclic hypothesis has three collinear points is dropped, and a cyclic goal with three
    collinear points fails. -> the row with events: triples with a figure, how many figures, how many of them fail the goal, and one failing figure"""
    x, limit = a
    t0 = time.time()
    pts, hyps, goal = _clean(x["dsl"])
    names = pts.split()
    _, _, G, figs, _ = solve(_state(pts, hyps, goal))
    row = dict(id=x["id"], sample=x["sample"], dsl=x["dsl"], figs=len(figs), triples=0, tried=0, events=[], stopped=False)
    if not figs:
        return row
    ix = {p: i for i, p in enumerate(names)}
    ga = [ix[q] if isinstance(q, str) else q for q in G[1]]
    no = {frozenset(s.split()[1:]) for s in hyps if s.split()[0] == "ncoll"}
    line = lambda t, P: abs(residual("coll", list(t), P)[0]) < 1e-7
    flat = lambda a, P: any(line(t, P) for t in itertools.combinations(a, 3))
    cyc = [[ix[q] for q in s.split()[1:]] for s in hyps if s.split()[0] == "cyclic"]
    todo = [t for t in itertools.combinations(names, 3) if frozenset(t) not in no and not line([ix[q] for q in t], figs[0])]
    row["triples"] = len(todo)
    np.random.default_rng(0).shuffle(todo)
    for t in todo:
        if limit and time.time() - t0 > limit:
            row["stopped"] = True
            break
        row["tried"] += 1
        got = solve(_state(pts, hyps + ["coll " + " ".join(t)], goal), starts=40)[3]
        got = [P for P in got if not any(flat(c, P) for c in cyc)]
        if not got:
            continue
        bad = [P for P in got if any(abs(r) > 1e-6 for r in residual(G[0], ga, P)) or (G[0] == "cyclic" and flat(ga, P))]
        e = dict(triple=list(t), figs=len(got), fails=len(bad))
        if bad:
            e["fig"] = {q: [round(float(bad[0][i].real), 5), round(float(bad[0][i].imag), 5)] for q, i in ix.items()}
        row["events"].append(e)
    return row


def ndg_rows():
    """ndg <rows.jsonl> <out.jsonl> [--workers W] [--limit S]: ndg_one on every statement not yet in out"""
    from concurrent.futures import ProcessPoolExecutor, as_completed
    rows = [json.loads(l) for l in open(sys.argv[2])]
    w = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 4
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 0
    done = {(r["id"], r["sample"]) for r in map(json.loads, open(sys.argv[3]))} if os.path.exists(sys.argv[3]) else set()
    with ProcessPoolExecutor(w) as ex, open(sys.argv[3], "a") as f:
        for u in as_completed([ex.submit(ndg_one, (r, limit)) for r in rows if (r["id"], r["sample"]) not in done]):
            f.write(json.dumps(u.result()) + "\n")
            f.flush()


def _subst(fact, nm, y):
    """an auxiliary point's fact with the point put on y, as the fact that is left: None if nothing is, False if it cannot be"""
    k, *a = fact
    a = [y if q == nm else q for q in a]
    if k in ("coll", "cyclic", "circle"):
        b = list(dict.fromkeys(a))
        if k == "coll":
            return None if len(b) < 3 else [k, *b]
        if k == "circle":
            return None if len(b) < 3 or a[0] in a[1:] and len(b) < 4 else [k, *b]
        return None if len(b) < 4 else [k, *b]
    if k == "midp":
        return False if len(set(a)) < 3 else [k, *a]
    if k in ("perp", "cong"):
        return None if a[0] == a[1] or a[2] == a[3] or (k == "cong" and {a[0], a[1]} == {a[2], a[3]}) else [k, *a]
    raise ValueError(k)


def _negate(cond, pts, hyps, defs):
    """the statement on the figures where one condition of the proof fails, with the auxiliary points that condition depends on written as points. -> points, hypotheses, or None and
    why no such statement is written"""
    from geo_check import def_facts
    kind, *a = cond[:-1]
    d = dict(defs)
    words = lambda nm: [q for q in d[nm].split() if q != "aux"]
    gone, y = (a[0], a[1]) if kind == "same" else (a[0], None) if kind == "tangent" else (None, None)
    extra = []
    if kind == "ncoll":
        extra = [["coll", *a]]
    elif kind.startswith("flip"):
        extra = [[kind, *a]]
    elif kind == "para":
        extra = [["para", *a]]
    elif kind == "tangent":
        k, *b = words(gone)
        if k != "second_lc":
            return None, "tangent circles"
        extra = [["eqangle", b[0], b[1], b[0], b[2], b[3], b[0], b[3], b[2]]]   # the line touches the circle at b[0]
    else:
        k, *b = words(gone)
        if k in ("second_lc", "second_cc") and y == b[0]:
            return None, "same as tangent"
        if k == "reflect" and y == b[0]:
            extra = [["coll", y, b[1], b[2]]]
        for f in def_facts(gone, d[gone]):
            g = _subst(f, gone, y)
            if g is False:
                return None, "impossible"
            if g:
                extra.append(g)
    need, todo = [], [q for f in extra for q in f[1:] if q in d]
    while todo:
        m = todo.pop()
        if m in need or m == gone:
            continue
        need.append(m)
        todo += [q for q in words(m)[1:] if q in d]
    for m, _ in defs:
        if m in need:
            for f in def_facts(m, d[m]):
                g = _subst(f, gone, y) if kind == "same" else f
                if g is False:
                    return None, "impossible"
                if g:
                    extra.append(g)
    return " ".join(pts.split() + [m for m, _ in defs if m in need]), hyps + [" ".join(f) for f in extra]


def pcond_one(a):
    """SIDE-GT-NDGP: the conditions a certified proof needs, each tested: is there a figure of the statement where it fails, and does the goal hold there? The search covers the proof's own
    conditions, not every triple, so a counterexample outside a configuration the proof read has to appear here. -> a row with one entry per condition"""
    from geo_check import conditions
    path, limit = a
    t0 = time.time()
    c = json.load(open(path))
    pts, hyps, goal = _clean(c["dsl"])
    conds = conditions(c)
    no = {frozenset(s.split()[1:]) for s in hyps if s.split()[0] == "ncoll"}
    row = dict(file=os.path.basename(path), dsl=c["dsl"], defs=c["defs"], n=len(conds), conds=[], stopped=False)
    G = parse(_state(pts, hyps, goal))[2]
    line = lambda t, P: abs(residual("coll", list(t), P)[0]) < 1e-7
    flat = lambda q, P: any(line(t, P) for t in itertools.combinations(q, 3))
    seen = {}
    for cd in conds:
        e = dict(cond=cd)
        row["conds"].append(e)
        key = tuple(cd[:-1])
        if key in seen:
            e["same_as"] = seen[key]
            continue
        seen[key] = len(row["conds"]) - 1
        if cd[0] == "ncoll" and frozenset(cd[1:-1]) in no:
            e["state"] = "stated"
            continue
        if limit and time.time() - t0 > limit:
            row["stopped"] = True
            e["state"] = "not tried"
            continue
        p2, h2 = _negate(cd, pts, hyps, c["defs"])
        if p2 is None:
            e["state"] = "untested: " + h2
            continue
        ix = {p: i for i, p in enumerate(p2.split())}
        got = solve(_state(p2, h2, goal), starts=40)[3]
        cyc = [[ix[q] for q in s.split()[1:]] for s in h2 if s.split()[0] == "cyclic"]
        got = [P for P in got if not any(flat(q, P) for q in cyc)]
        ga = [ix[q] if isinstance(q, str) else q for q in G[1]]
        bad = [P for P in got if any(abs(r) > 1e-6 for r in residual(G[0], ga, P)) or (G[0] == "cyclic" and flat(ga, P))]
        e.update(state="figures" if got else "none", figs=len(got), fails=len(bad))
        if bad:
            e["fig"] = {q: [round(float(bad[0][i].real), 5), round(float(bad[0][i].imag), 5)] for q, i in ix.items()}
    row["sec"] = round(time.time() - t0, 1)
    return row


def rread_one(a):
    """SIDE-GT-LEAN-RD: each reading of a certified proof, negated. A figure of the statement where the reading fails is outside what the proof shows; if the goal fails there too, the statement
    is false as written and only the reading saved it. -> a row with one entry per reading"""
    from geo_lean import Writer, Stop
    path, limit = a
    t0 = time.time()
    c = json.load(open(path))
    row = dict(file=os.path.basename(path), dsl=c["dsl"], reads=[], stopped=False)
    w = Writer(json.loads(json.dumps(c)))
    w.cache = {}
    try:
        w.run()
    except Stop as e:
        row["error"] = str(e)
        return row
    pts, hyps, goal = _clean(c["dsl"])
    G = parse(_state(pts, hyps, goal))[2]
    line = lambda t, P: abs(residual("coll", list(t), P)[0]) < 1e-7
    flat = lambda q, P: any(line(t, P) for t in itertools.combinations(q, 3))
    for k in w.reads:
        q = [*k[1], *k[2]] if k[0] in ("Read", "Read2") else list(k[1])
        kind = {"Read": "flip", "Read2": "flip2", "ReadT": "flipt", "ReadZ": "flipz"}[k[0]]
        e = dict(read=[k[0], *q])
        row["reads"].append(e)
        if limit and time.time() - t0 > limit:
            row["stopped"] = True
            e["state"] = "not tried"
            continue
        p2, h2 = _negate([kind, *q, "read"], pts, hyps, c["defs"])
        ix = {p: i for i, p in enumerate(p2.split())}
        got = solve(_state(p2, h2, goal), starts=40)[3]
        cyc = [[ix[x] for x in s.split()[1:]] for s in h2 if s.split()[0] == "cyclic"]
        got = [P for P in got if not any(flat(x, P) for x in cyc)]
        ga = [ix[x] if isinstance(x, str) else x for x in G[1]]
        bad = [P for P in got if any(abs(r) > 1e-6 for r in residual(G[0], ga, P)) or (G[0] == "cyclic" and flat(ga, P))]
        e.update(state="figures" if got else "none", figs=len(got), fails=len(bad))
        if bad:
            e["fig"] = {x: [round(float(bad[0][i].real), 5), round(float(bad[0][i].imag), 5)] for x, i in ix.items()}
    row["sec"] = round(time.time() - t0, 1)
    return row


def rctl_one(a):
    """SIDE-GT-LEAN-RC: can the search behind rread find a flipped figure at all? For each reading, the statement with its auxiliary points and without the negation (how many of the
    starts solve, and the reading's sign on those figures), and the negated reading with the statement's order conditions removed (figures, and how many break the goal). -> a row"""
    from geo_lean import Writer, Stop
    path, limit = a
    t0 = time.time()
    c = json.load(open(path))
    row = dict(file=os.path.basename(path), dsl=c["dsl"], reads=[], stopped=False)
    w = Writer(json.loads(json.dumps(c)))
    w.cache = {}
    try:
        w.run()
    except Stop as e:
        row["error"] = str(e)
        return row
    pts, hyps, goal = _clean(c["dsl"])
    G = parse(_state(pts, hyps, goal))[2]
    line = lambda t, P: abs(residual("coll", list(t), P)[0]) < 1e-7
    flat = lambda q, P: any(line(t, P) for t in itertools.combinations(q, 3))
    row["orders"] = sorted({s.split()[0] for s in hyps if s.split()[0] in ORDER and s.split()[0] != "ncoll"})
    for k in w.reads:
        q = [*k[1], *k[2]] if k[0] in ("Read", "Read2") else list(k[1])
        kind = {"Read": "flip", "Read2": "flip2", "ReadT": "flipt", "ReadZ": "flipz"}[k[0]]
        e = dict(read=[k[0], *q])
        row["reads"].append(e)
        if limit and time.time() - t0 > limit:
            row["stopped"] = True
            e["state"] = "not tried"
            continue
        p2, h2 = _negate([kind, *q, "read"], pts, hyps, c["defs"])
        ix = {p: i for i, p in enumerate(p2.split())}
        cyc = [[ix[x] for x in s.split()[1:]] for s in h2 if s.split()[0] == "cyclic"]
        ga = [ix[x] if isinstance(x, str) else x for x in G[1]]
        keep = lambda got: [P for P in got if not any(flat(x, P) for x in cyc)]
        r = solve(_state(p2, [s for s in h2 if s.split()[0] != kind], goal), starts=40)
        got = keep(r[3])
        e.update(solved=r[4], figs=len(got), flipped=sum(all(x > 0 for x in order_value(kind, [ix[x] for x in q], P)) for P in got))
        free = ["coll " + s.split(None, 1)[1] if s.split()[0] == "between" else s for s in h2]
        got = keep(solve(_state(p2, [s for s in free if s.split()[0] not in ORDER or s.split()[0] in ("ncoll", kind)], goal), starts=40)[3])
        bad = [P for P in got if any(abs(x) > 1e-6 for x in residual(G[0], ga, P)) or (G[0] == "cyclic" and flat(ga, P))]
        e.update(state="figures" if got else "none", free=len(got), free_fails=len(bad))
    row["sec"] = round(time.time() - t0, 1)
    return row


def pcond_rows(one=pcond_one):
    """pcond <cert dir> <out.jsonl> [--workers W] [--limit S] [--only substring ...]: pcond_one on every certificate not yet in out"""
    from concurrent.futures import ProcessPoolExecutor, as_completed
    w = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 4
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 0
    done = {r["file"] for r in map(json.loads, open(sys.argv[3]))} if os.path.exists(sys.argv[3]) else set()
    todo = [os.path.join(sys.argv[2], f) for f in sorted(os.listdir(sys.argv[2])) if f.endswith(".json") and f not in done]
    with ProcessPoolExecutor(w) as ex, open(sys.argv[3], "a") as f:
        for u in as_completed([ex.submit(one, (p, limit)) for p in todo]):
            f.write(json.dumps(u.result()) + "\n")
            f.flush()


if __name__ == "__main__":
    if sys.argv[1] == "guard":
        print(json.dumps(guard(sys.argv[2])))
    if sys.argv[1] == "agree":
        agree_rows()
    if sys.argv[1] == "one":
        print(json.dumps(guard(sys.argv[2])))
        print(figure(sys.argv[2])[2])
    if sys.argv[1] == "ndg":
        ndg_rows()
    if sys.argv[1] == "pcond":
        pcond_rows()
    if sys.argv[1] == "rread":
        pcond_rows(rread_one)
    if sys.argv[1] == "rctl":
        pcond_rows(rctl_one)
    if sys.argv[1] == "reduce":
        reduce_rows()
