"""COMP-FIG: a geometry problem as a figure the model only describes. The model writes a short script of points, unknowns and conditions; least squares finds figures
from random starts, and the script's answer is read on each. A determined problem has one answer on every figure, so an answer that changes between figures, or a
statement with no figure, is a free check on the translation. The model computes nothing and picks no coordinates.
  python poc/figlib.py <script.py> [--budget S] [--starts N] [--keep K]   -> one JSON line: status (err / none / inv / multi / const), values [[value, figures]], figures, starts, msg, sec
Status: inv = every figure kept gives one answer; multi = at least two; none = no figure satisfies the conditions; const = the answer does not depend on the figure; err = the script failed.
The script runs once per evaluation on plain floats and numpy vectors, so ordinary arithmetic and loops are allowed. Runs in a subprocess with limits from run_fig.py."""
import ast, itertools, json, math, sys, time
from fractions import Fraction
import numpy as np
from scipy.optimize import least_squares

TOL = 1e-8   # a condition holds when its residual, relative to the size of its sides, is below this
SAME = 1e-5  # two named points closer than this, relative to the figure, are one point: distinct names are distinct points
AGREE = 1e-6 # two answers are one when they differ by less than this, relatively


class Form(Exception):
    pass


def squarefree(limit):
    s = [True] * (limit + 1)
    for i in range(2, int(limit ** 0.5) + 1):
        for j in range(i * i, limit + 1, i * i):
            s[j] = False
    return [i for i in range(1, limit + 1) if s[i]]


SF = squarefree(20000)


def rat(v, den=2000, tol=1e-9):
    """v as a fraction. A real number falls this close to some fraction with denominator up to Q with chance about Q^2 * tol, so both are small, and the figures hold about 1e-11"""
    f = Fraction(v).limit_denominator(den)
    return f if abs(float(f) - v) <= tol * max(1, abs(v)) else None


class Ctx:
    def __init__(self, x, final):
        self.x, self.i, self.res, self.scale, self.final = x, 0, [], [], final
        self.names, self.ans, self.hinge = [], None, []

    def take(self, n):
        if self.x is None:  # the first pass only counts the unknowns; distinct values keep a script's divisions alive
            self.i += n
            return np.random.default_rng(self.i).normal(0, 1, n)
        v = self.x[self.i:self.i + n]
        self.i += n
        return v

    def add(self, r, s=1.0):
        self.res.append(float(r))
        self.scale.append(max(1.0, abs(float(s))))


def lib(c):
    """the names a script may use; every condition appends to c.res"""
    def points(names, dim=2):
        out = []
        for _ in names.split():
            p = np.array(c.take(dim), dtype=float)
            c.names.append(p)
            out.append(p)
        return out[0] if len(out) == 1 else out

    def var(name=""):
        return float(c.take(1)[0])

    def dist(a, b):
        return float(np.linalg.norm(np.asarray(a) - np.asarray(b)))

    def cross2(u, v):
        return float(u[0] * v[1] - u[1] * v[0])

    def crossn(u, v):
        return cross2(u, v) if len(u) == 2 else float(np.linalg.norm(np.cross(u, v)))

    def angle(a, b, c_):
        u, v = np.asarray(a) - np.asarray(b), np.asarray(c_) - np.asarray(b)
        return math.degrees(math.atan2(abs(crossn(u, v)), float(np.dot(u, v))))

    def area(*p):
        if len(p[0]) == 3:
            return float(sum(np.linalg.norm(np.cross(p[i] - p[0], p[i + 1] - p[0])) for i in range(1, len(p) - 1)) / 2)
        return abs(sum(cross2(p[i], p[(i + 1) % len(p)]) for i in range(len(p)))) / 2

    def perimeter(*p):
        return sum(dist(p[i], p[(i + 1) % len(p)]) for i in range(len(p)))

    def volume(a, b, c_, d):
        return abs(float(np.dot(b - a, np.cross(c_ - a, d - a)))) / 6

    # A built point returns the point. Given one more point first, it also works as the condition that this point is the built one: foot(D, C, A, B) is D = foot(C, A, B).
    def midpoint(*q):
        m = (np.asarray(q[-2]) + np.asarray(q[-1])) / 2
        if len(q) == 3:
            eq(q[0], m)
        return m

    def foot(*q):
        p, a, b = q[-3:]
        d = b - a
        f = a + d * float(np.dot(p - a, d)) / max(float(np.dot(d, d)), 1e-300)
        if len(q) == 4:
            eq(q[0], f)
        return f

    def reflect(*q):
        r_ = 2 * foot(*q[-3:]) - q[-3]
        if len(q) == 4:
            eq(q[0], r_)
        return r_

    def mirror(*q):
        """the point P through the point Q; mirror(M, P, Q) is the condition M = mirror(P, Q)"""
        m = 2 * np.asarray(q[-1]) - np.asarray(q[-2])
        if len(q) == 3:
            eq(q[0], m)
        return m

    def intersection(*q):
        a, b, c_, d = q[-4:]
        u, v = b - a, d - c_
        den = cross2(u, v)
        x = a + u * (cross2(c_ - a, v) / (den if abs(den) > 1e-300 else 1e-300))
        if len(q) == 5:
            eq(q[0], x)
        return x

    def centroid(*p):
        return sum(p) / len(p)

    def circumcenter(a, b, c_):
        u, v = b - a, c_ - a
        den = 2 * cross2(u, v)
        den = den if abs(den) > 1e-300 else 1e-300
        uu, vv = float(np.dot(u, u)), float(np.dot(v, v))
        return a + np.array([v[1] * uu - u[1] * vv, u[0] * vv - v[0] * uu]) / den

    def incenter(a, b, c_):
        x, y, z = dist(b, c_), dist(c_, a), dist(a, b)
        return (x * a + y * b + z * c_) / max(x + y + z, 1e-300)

    def inradius(a, b, c_):
        return 2 * area(a, b, c_) / max(perimeter(a, b, c_), 1e-300)

    def circumradius(a, b, c_):
        return dist(a, b) * dist(b, c_) * dist(c_, a) / max(4 * area(a, b, c_), 1e-300)

    def eq(a, b):
        if np.ndim(a) or np.ndim(b):  # two points, or a point and its coordinates
            for x, y in zip(np.asarray(a, dtype=float), np.asarray(b, dtype=float)):
                eq(float(x), float(y))
            return
        c.add(a - b, max(abs(a), abs(b)))

    def gt(a, b):
        c.hinge.append((float(a), float(b)))
        c.add(max(0.0, b - a), max(abs(a), abs(b)))

    def lt(a, b):
        gt(b, a)

    def perp(a, b, c_, d):
        u, v = b - a, d - c_
        c.add(float(np.dot(u, v)), float(np.linalg.norm(u) * np.linalg.norm(v)))

    def parallel(a, b, c_, d):
        u, v = b - a, d - c_
        c.add(crossn(u, v), float(np.linalg.norm(u) * np.linalg.norm(v)))

    def collinear(a, b, c_):
        parallel(a, b, a, c_)

    def order(*p):
        """the points lie on one line in this order"""
        for i in range(2, len(p)):
            collinear(p[0], p[1], p[i])
        for i in range(1, len(p) - 1):
            gt(-float(np.dot(p[i - 1] - p[i], p[i + 1] - p[i])), 0.0)

    def on_ray(p, a, b):
        collinear(a, b, p)
        gt(float(np.dot(p - a, b - a)), 0.0)

    def on_circle(p, o, r, *more):
        if more:  # on_circle(A, B, C, D): four points on one circle
            concyclic(p, o, r, more[0])
        else:
            eq(dist(p, o), r)

    def concyclic(a, b, c_, d):
        rows = [[*(q - a), float(np.dot(q - a, q - a))] for q in (b, c_, d)]
        s = max(dist(a, b), dist(a, c_), dist(a, d))
        c.add(float(np.linalg.det(np.array(rows))), s ** 4)

    def tangent_line(a, b, o, r):
        eq(abs(crossn(b - a, o - a)) / max(dist(a, b), 1e-300), r)

    def tangent_circles(o1, r1, o2, r2):
        eq(dist(o1, o2), r1 + r2)

    def tangent_inside(o1, r1, o2, r2):  # circle 2 inside circle 1
        eq(dist(o1, o2), r1 - r2)

    def same_side(p, q, a, b):
        gt(cross2(b - a, p - a) * cross2(b - a, q - a), 0.0)

    def opposite_side(p, q, a, b):
        gt(0.0, cross2(b - a, p - a) * cross2(b - a, q - a))

    def inside(p, *poly):
        n = len(poly)
        s = [cross2(poly[(i + 1) % n] - poly[i], p - poly[i]) for i in range(n)]
        sg = 1.0 if sum(s) >= 0 else -1.0
        for v in s:
            gt(sg * v, 0.0)

    def convex(*poly):
        n = len(poly)
        s = [cross2(poly[(i + 1) % n] - poly[i], poly[(i + 2) % n] - poly[(i + 1) % n]) for i in range(n)]
        sg = 1.0 if sum(s) >= 0 else -1.0
        for v in s:
            gt(sg * v, 0.0)

    def parallelogram(a, b, c_, d):
        for x, y in zip(a + c_, b + d):
            eq(float(x), float(y))
        gt(crossn(b - a, d - a) ** 2, 0.0)

    def rectangle(a, b, c_, d):
        parallelogram(a, b, c_, d)
        perp(a, b, b, c_)

    def rhombus(a, b, c_, d):
        parallelogram(a, b, c_, d)
        eq(dist(a, b), dist(b, c_))

    def square(a, b, c_, d):
        rectangle(a, b, c_, d)
        eq(dist(a, b), dist(b, c_))

    def regular(*p):
        """a regular polygon with its vertices in order"""
        n = len(p)
        convex(*p)
        for i in range(n):
            eq(dist(p[i], p[(i + 1) % n]), dist(p[0], p[1]))
            eq(angle(p[i], p[(i + 1) % n], p[(i + 2) % n]), 180.0 * (n - 2) / n)

    def answer(v):
        c.ans = v

    def frac(v):
        """v = m/n in lowest terms -> m, n"""
        if not c.final:
            return v, 1
        f = rat(v)
        if f is None:
            raise Form(f"{v} is not a fraction")
        return f.numerator, f.denominator

    def surd(v):
        """v = m*sqrt(n)/p, n squarefree, m and p coprime -> m, n, p"""
        if not c.final:
            return v, 1, 1
        best = None
        for n in SF[:3100]:  # the simplest form: a number close to a large fraction is not that fraction
            f = rat(v / math.sqrt(n), den=500, tol=1e-10)
            if f is not None:
                h = abs(f.numerator) + n + f.denominator
                if best is None or h < best[0]:
                    best = (h, f.numerator, n, f.denominator)
        if best is None:
            raise Form(f"{v} is not m*sqrt(n)/p")
        return best[1:]

    def surd2(v):
        """v = (a + b*sqrt(n))/d, n squarefree > 1, d > 0 -> a, b, n, d, in the smallest integers found"""
        if not c.final:
            return v, 1, 1, 1
        best = None
        for n in SF[1:4000]:
            s = math.sqrt(n)
            for d in range(1, 200):
                for b in range(-400, 401):
                    if b == 0:
                        continue
                    a = v * d - b * s
                    if abs(a - round(a)) < 1e-7 * max(1, abs(a)) and abs(a) < 5000:
                        h = abs(round(a)) + abs(b) + n + d
                        if best is None or h < best[0]:
                            best = (h, int(round(a)), b, n, d)
                if best is not None and best[0] < d:
                    break
            if best is not None and best[0] < n:
                break
        if best is None:
            raise Form(f"{v} is not (a + b*sqrt(n))/d")
        return best[1:]

    names = dict(points=points, var=var, dist=dist, angle=angle, area=area, perimeter=perimeter, volume=volume, midpoint=midpoint, foot=foot, reflect=reflect,
                 intersection=intersection, centroid=centroid, circumcenter=circumcenter, incenter=incenter, inradius=inradius, circumradius=circumradius, eq=eq, gt=gt, lt=lt,
                 perp=perp, parallel=parallel, collinear=collinear, order=order, mirror=mirror, on_ray=on_ray, on_circle=on_circle, concyclic=concyclic, tangent_line=tangent_line,
                 tangent_circles=tangent_circles, tangent_inside=tangent_inside, same_side=same_side, opposite_side=opposite_side, inside=inside, convex=convex,
                 parallelogram=parallelogram, rectangle=rectangle, rhombus=rhombus, square=square, regular=regular, answer=answer, frac=frac, surd=surd, surd2=surd2, dot=lambda u, v: float(np.dot(u, v)), sqrt=math.sqrt, pi=math.pi,
                 sin=lambda d: math.sin(math.radians(d)), cos=lambda d: math.cos(math.radians(d)), tan=lambda d: math.tan(math.radians(d)))
    names["__builtins__"] = {k: __builtins__[k] if isinstance(__builtins__, dict) else getattr(__builtins__, k)
                             for k in ("abs", "min", "max", "sum", "range", "len", "zip", "enumerate", "float", "int", "round", "list", "tuple", "print", "pow", "sorted", "map", "all", "any")}
    return names


def run(code, x, final=False):
    c = Ctx(x, final)
    exec(code, lib(c))
    return c


def literals(src):
    """the sizes the script states, for the scale of the random starts"""
    out = [abs(n.value) for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool)]
    return [v for v in out if v > 0]


def solve(src, budget=40.0, starts=96, keep=16, seed=0):
    t0 = time.time()
    try:
        code = compile(src, "script", "exec")
        c0 = run(code, None)
    except Exception as e:
        return dict(status="err", values=[], figures=0, starts=0, msg=f"{type(e).__name__}: {e}"[:400], sec=round(time.time() - t0, 2))
    n = c0.i
    if n == 0:
        return dict(status="err", values=[], figures=0, starts=0, msg="the script declares no points or unknowns", sec=0.0)
    big = max(literals(src) + [1.0])
    rng = np.random.default_rng(seed)
    last_err, kept, tried = None, [], 0

    def fun(x, sc):
        c = run(code, x)
        if c.i != n:
            raise ValueError("the number of unknowns changed")
        return np.array(c.res + [0.0], dtype=float) / sc

    def scales(x):
        return np.array(run(code, x).scale + [1.0], dtype=float)

    while tried < starts and len(kept) < keep and time.time() - t0 < budget:
        s = math.exp(rng.uniform(0, math.log(max(big, 2.0))))
        x0 = rng.normal(0, s, n)
        tried += 1
        try:
            # relative residuals, so a determinant of size s^4 does not drown a length; the sizes are held fixed within a round, because a residual
            # divided by its own moving size has a false minimum far away on the wrong side of a coordinate
            xk = x0
            for _ in range(3):
                sol = least_squares(fun, xk, method="trf", xtol=1e-14, ftol=1e-14, gtol=1e-14, max_nfev=60, args=(scales(xk),))
                xk = sol.x
            c = run(code, sol.x)
            r = np.abs(np.array(c.res, dtype=float)) / np.array(c.scale, dtype=float) if c.res else np.zeros(1)
            if not np.all(np.isfinite(sol.x)) or r.max(initial=0.0) > TOL:
                continue
            P = c.names
            size = max([float(np.linalg.norm(p - q)) for p, q in itertools.combinations(P, 2)] + [1e-12])
            if size < SAME or any(float(np.linalg.norm(p - q)) < SAME * size for p, q in itertools.combinations(P, 2)):  # a figure shrunk to a point meets any condition with no stated size
                continue
            if any(a <= b + 1e-9 * max(1.0, abs(a), abs(b)) for a, b in c.hinge):  # a strict inequality met only at its boundary
                continue
            f = run(code, sol.x, final=True)
            if f.ans is None:
                return dict(status="err", values=[], figures=0, starts=tried, msg="the script never calls answer()", sec=round(time.time() - t0, 2))
            v = float(f.ans)
            if math.isfinite(v):
                kept.append(v)
        except Form as e:
            last_err = f"Form: {e}"
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"[:400]
    groups = []
    for v in kept:
        for g in groups:
            if abs(g[0] - v) <= AGREE * max(1.0, abs(v)):
                g[1] += 1
                break
        else:
            groups.append([v, 1])
    groups.sort(key=lambda g: -g[1])
    st = "none" if not groups else "inv" if len(groups) == 1 else "multi"
    if st == "inv":  # the same answer on every figure means nothing if the answer never reads the figure
        seen = []
        for _ in range(3):
            try:
                seen.append(float(run(code, rng.normal(0, big, n)).ans))
            except Exception:
                pass
        if len(seen) == 3 and max(seen) - min(seen) <= AGREE * max(1.0, abs(seen[0])):
            st = "const"
    return dict(status=st, values=groups[:6], figures=len(kept), starts=tried, msg=last_err or "", sec=round(time.time() - t0, 2))


if __name__ == "__main__":
    a = sys.argv
    arg = lambda n, d: type(d)(a[a.index(n) + 1]) if n in a else d
    print(json.dumps(solve(open(a[1]).read(), budget=arg("--budget", 40.0), starts=arg("--starts", 96), keep=arg("--keep", 16))))
