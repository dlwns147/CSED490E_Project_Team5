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
  python side/geo_decl.py guard '<statement>'   (the status alone, for geo_translate.py)"""
import cmath, json, math, os, sys
import numpy as np

FACT = {"coll": 3, "para": 4, "perp": 4, "cong": 4, "cyclic": 4, "midp": 3, "circle": 3, "eqangle": 8, "eqratio": 8, "aconst": 5, "rconst": 5, "uangle": 6, "uconst": 4}
ORDER = {"between": 3, "inside": 4, "sameside": 4, "opposite": 4, "acute": 3, "obtuse": 3, "convex": 4, "ncoll": 3}
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


if __name__ == "__main__":
    if sys.argv[1] == "guard":
        print(json.dumps(guard(sys.argv[2])))
    if sys.argv[1] == "agree":
        agree_rows()
    if sys.argv[1] == "one":
        print(json.dumps(guard(sys.argv[2])))
        print(figure(sys.argv[2])[2])
