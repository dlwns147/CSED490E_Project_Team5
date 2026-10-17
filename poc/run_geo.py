"""PoC G2 — computational-geometry metamorphic invariance: same geometry, transformed input — same answer?

tasks (integer coordinates, exact answers by integer cross products):
  hull   : number of vertices of the convex hull (points lying on hull edges do NOT count)
  area2  : twice the area of a simple polygon given by its vertices in order
  pip    : is the query point strictly inside the polygon? (yes/no)
  segs   : number of pairs of segments that intersect (touching counts)
  close  : squared distance of the closest pair of points
variants of one base instance:
  identity, translate, rot90, mirror, permute (shuffle points / cyclic-shift + reverse polygon), scale (x3; area2 and
  close scale by 9), big (translate by ~1e9: precision/overflow stress), degen (collinear/duplicate points, a ray
  through a vertex, touching segments: the classic degenerate cases; the answer is recomputed exactly)
modes: direct (thinking off / on) and code (the model writes a program for the stdin format; we run it).
consistency = all non-degen variants give the same answer after undoing the known scaling.
"""
import argparse
import json
import math
import os
import random
import re
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
from llm import chat, last_block  # noqa: E402
from sandbox import run_python  # noqa: E402

RES = "/NAS/SJ/POSTECH/nlp/results"


def orient(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def hull_count(P):
    P = sorted(set(map(tuple, P)))
    if len(P) < 3:
        return len(P)
    def half(pts):
        h = []
        for p in pts:
            while len(h) >= 2 and orient(h[-2], h[-1], p) <= 0:  # pop collinear too -> strict vertices only
                h.pop()
            h.append(p)
        return h
    lo, up = half(P), half(P[::-1])
    return len(lo) + len(up) - 2


def area2(poly):
    return abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly))))


def on_seg(a, b, q):
    return orient(a, b, q) == 0 and min(a[0], b[0]) <= q[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= q[1] <= max(a[1], b[1])


def pip(poly, q):
    wn = 0
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        if on_seg(a, b, q):
            return "boundary"
        if a[1] <= q[1]:
            if b[1] > q[1] and orient(a, b, q) > 0:
                wn += 1
        elif b[1] <= q[1] and orient(a, b, q) < 0:
            wn -= 1
    return "yes" if wn != 0 else "no"


def seg_inter(s, t):
    a, b = s; c, d = t
    d1, d2, d3, d4 = orient(c, d, a), orient(c, d, b), orient(a, b, c), orient(a, b, d)
    if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)):
        return True
    return on_seg(c, d, a) or on_seg(c, d, b) or on_seg(a, b, c) or on_seg(a, b, d)


def segs_count(S):
    return sum(seg_inter(S[i], S[j]) for i in range(len(S)) for j in range(i + 1, len(S)))


def closest(P):
    return min((P[i][0] - P[j][0]) ** 2 + (P[i][1] - P[j][1]) ** 2 for i in range(len(P)) for j in range(i + 1, len(P)))


def hull_pts(P):   # strict convex hull vertices, CCW
    P = sorted(set(map(tuple, P)))
    if len(P) < 3:
        return P
    def half(pts):
        h = []
        for p in pts:
            while len(h) >= 2 and orient(h[-2], h[-1], p) <= 0:
                h.pop()
            h.append(p)
        return h
    lo, up = half(P), half(P[::-1])
    return lo[:-1] + up[:-1]


def is_convex_poly(poly):   # collinear consecutive vertices allowed
    s_ = set()
    n = len(poly)
    for i in range(n):
        o = orient(poly[i], poly[(i + 1) % n], poly[(i + 2) % n])
        if o:
            s_.add(o > 0)
    return "yes" if len(s_) <= 1 else "no"


def tri_inside(T, P):   # points strictly inside the triangle, duplicates counted separately
    a, b, c = T
    s0 = orient(a, b, c)
    return sum(1 for p in P if all((orient(u, v, p) > 0) == (s0 > 0) and orient(u, v, p) != 0 for u, v in ((a, b), (b, c), (c, a))))


def polys_overlap(A, B):   # two convex polygons share at least one point (touching counts)
    for i in range(len(A)):
        for j in range(len(B)):
            if seg_inter((A[i], A[(i + 1) % len(A)]), (B[j], B[(j + 1) % len(B)])):
                return "yes"
    return "yes" if pip(B, A[0]) != "no" or pip(A, B[0]) != "no" else "no"


def clip_area2(A, B):   # twice the area of the intersection of two convex polygons, exact (Sutherland-Hodgman with Fractions)
    from fractions import Fraction as F
    def ccw(P):
        return P if sum(P[i][0] * P[(i + 1) % len(P)][1] - P[(i + 1) % len(P)][0] * P[i][1] for i in range(len(P))) > 0 else P[::-1]
    A, B = ccw([tuple(map(F, p)) for p in A]), ccw([tuple(map(F, p)) for p in B])
    out = A
    for i in range(len(B)):
        a, b = B[i], B[(i + 1) % len(B)]
        side = lambda p: (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
        inp, out = out, []
        for j in range(len(inp)):
            p, q = inp[j], inp[(j + 1) % len(inp)]
            sp, sq = side(p), side(q)
            if sp >= 0:
                out.append(p)
            if (sp > 0 and sq < 0) or (sp < 0 and sq > 0):
                t = sp / (sp - sq); out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
        if not out:
            return F(0)
    return abs(sum(out[i][0] * out[(i + 1) % len(out)][1] - out[(i + 1) % len(out)][0] * out[i][1] for i in range(len(out))))


def fmt_frac(x):
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


def is_simple(P):   # no two non-adjacent edges share a point
    n = len(P)
    return not any(seg_inter((P[i], P[(i + 1) % n]), (P[j], P[(j + 1) % n]))
                   for i in range(n) for j in range(i + 2, n) if not (i == 0 and j == n - 1))


def lattice_inside(poly):   # integer points strictly inside a simple lattice polygon (Pick: A = I + B/2 - 1)
    A2 = abs(area2(poly)); n = len(poly)
    B = sum(math.gcd(abs(poly[(i + 1) % n][0] - poly[i][0]), abs(poly[(i + 1) % n][1] - poly[i][1])) for i in range(n))
    return (A2 - B + 2) // 2


def rect_union(R):   # area of the union of axis-aligned rectangles (each given by two opposite corners), coordinate compression
    rs = [(min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])) for a, b in R]
    xs = sorted({v for r in rs for v in (r[0], r[2])}); ys = sorted({v for r in rs for v in (r[1], r[3])})
    tot = 0
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            if any(r[0] <= xs[i] and xs[i + 1] <= r[2] and r[1] <= ys[j] and ys[j + 1] <= r[3] for r in rs):
                tot += (xs[i + 1] - xs[i]) * (ys[j + 1] - ys[j])
    return tot


def in_circle_det(a, b, c, d):   # E2: > 0 iff d is strictly inside the circumcircle of the COUNTER-CLOCKWISE triangle abc (exact)
    ax, ay, bx, by, cx, cy = a[0] - d[0], a[1] - d[1], b[0] - d[0], b[1] - d[1], c[0] - d[0], c[1] - d[1]
    return ((ax * ax + ay * ay) * (bx * cy - cx * by) - (bx * bx + by * by) * (ax * cy - cx * ay)
            + (cx * cx + cy * cy) * (ax * by - bx * ay))


def in_cc(a, b, c, d):   # d strictly inside the circumcircle of triangle abc, any vertex order
    return in_circle_det(a, b, c, d) * (1 if orient(a, b, c) > 0 else -1) > 0


def bad_triangles(P, T):   # E2 delaunay: triangles whose circumcircle strictly contains another input point (0 = Delaunay)
    return sum(any(in_cc(P[i], P[j], P[k], P[m]) for m in range(len(P)) if m not in (i, j, k)) for i, j, k in T)


def diam2(P):   # E2 diameter: squared distance of the farthest pair
    return max((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 for p in P for q in P)


def _sweep_tri(P):   # any triangulation of a point set with no 3 collinear points (lexicographic sweep); triangles CCW
    order = sorted(range(len(P)), key=lambda i: P[i])
    a, b, c = order[:3]
    if orient(P[a], P[b], P[c]) < 0:
        b, c = c, b
    T, hull = [(a, b, c)], [a, b, c]
    for p in order[3:]:
        n = len(hull)
        vis = [orient(P[hull[i]], P[hull[(i + 1) % n]], P[p]) < 0 for i in range(n)]
        s = next(i for i in range(n) if vis[i] and not vis[i - 1])
        H, V = hull[s:] + hull[:s], vis[s:] + vis[:s]
        k = 0
        while V[k]:
            T.append((H[k], p, H[(k + 1) % n])); k += 1
        hull = [H[0], p] + H[k:]
    return T


def _third(t, u, v):
    return next(z for z in t if z not in (u, v))


def _flip(T, E, u, v):   # replace (u, v, w), (v, u, x) by (w, u, x), (x, v, w); all CCW
    t1, t2 = E[(u, v)], E[(v, u)]
    w, x = _third(t1, u, v), _third(t2, u, v)
    T.remove(t1); T.remove(t2); T += [(w, u, x), (x, v, w)]


def _edge_map(T):
    return {e: t for t in T for e in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0]))}


def _lawson(P, T):   # flip strictly illegal edges until the triangulation is Delaunay (on-circle points are legal)
    while True:
        E = _edge_map(T)
        bad = [(u, v) for (u, v), t in E.items() if (v, u) in E and in_cc(P[u], P[v], P[_third(t, u, v)], P[_third(E[(v, u)], u, v)])]
        if not bad:
            return T
        _flip(T, E, *bad[0])


def _random_flips(P, T, r, rng):   # r flips of random interior edges with a strictly convex quadrilateral (creates violations)
    for _ in range(r):
        E = _edge_map(T)
        cand = sorted((u, v) for (u, v), t in E.items() if u < v and (v, u) in E
                      and orient(P[_third(t, u, v)], P[u], P[_third(E[(v, u)], u, v)]) > 0
                      and orient(P[_third(E[(v, u)], u, v)], P[v], P[_third(t, u, v)]) > 0)
        if cand:
            _flip(T, E, *rng.choice(cand))
    return T


def _no_collinear(P):
    n = len(P)
    return all(orient(P[i], P[j], P[k]) != 0 for i in range(n) for j in range(i + 1, n) for k in range(j + 1, n))


def _no_cocircular(P):
    n = len(P)
    return all(in_circle_det(P[i], P[j], P[k], P[m]) != 0 for i in range(n) for j in range(i + 1, n) for k in range(j + 1, n)
               for m in range(k + 1, n))


def _triangulation(P, rng):   # Delaunay triangulation + 0-3 random flips; each triangle CCW with a random start vertex, shuffled
    T = _random_flips(P, _lawson(P, _sweep_tri(P)), rng.choice([0, 1, 1, 2, 2, 3]), rng)
    T = [t[k:] + t[:k] for t in T for k in [rng.randrange(3)]]
    rng.shuffle(T)
    return T


def closest_fast(P):   # H1: exact closest pair, sort + strip sweep (O(n log n) on random inputs)
    P = sorted(map(tuple, P))
    best = None
    import bisect
    act = []   # (y, x) sorted by y, points within the current x-window
    left = 0
    for p in P:
        if best is not None:
            while left < len(P) and (p[0] - P[left][0]) ** 2 > best:
                q = P[left]; j = bisect.bisect_left(act, (q[1], q[0])); act.pop(j); left += 1
            lo = bisect.bisect_left(act, (p[1] - int(best ** 0.5) - 1, -10**18))
            hi = bisect.bisect_right(act, (p[1] + int(best ** 0.5) + 1, 10**18))
            for y, x in act[lo:hi]:
                d = (x - p[0]) ** 2 + (y - p[1]) ** 2
                if d < best:
                    best = d
        else:
            if act:
                y, x = act[0]; best = (x - p[0]) ** 2 + (y - p[1]) ** 2
        bisect.insort(act, (p[1], p[0]))
        if best == 0:
            return 0
    return best if best is not None else 0


def diam_fast(P):   # H1: farthest pair = max over hull vertices (hull of random points is small)
    H = hull_pts(list(set(map(tuple, P))))
    if len(H) < 2:
        return 0
    return max((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 for a in H for b in H)


LARGE_NOTE = " n can be up to 20000; the program must finish within 10 seconds."


def star_polygon(n, rng, R=20):
    while True:
        pts = {(rng.randint(-R, R) * 2, rng.randint(-R, R) * 2) for _ in range(3 * n)}  # even coords: integer midpoints
        pts = list(pts)
        cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
        ang = {}
        for p in pts:
            ang.setdefault(round(math.atan2(p[1] - cy, p[0] - cx), 9), p)
        poly = [ang[k] for k in sorted(ang)][:n] if len(ang) >= n else None
        if poly is None:
            continue
        poly = sorted(poly, key=lambda p: math.atan2(p[1] - cy, p[0] - cx))
        if all(orient(poly[i - 1], poly[i], poly[(i + 1) % n]) != 0 for i in range(n)) and area2(poly) > 0:
            return poly


def base_instance(task, n, rng):
    if task in ("hullL", "closeL", "diamL"):   # H1: large inputs, coordinates up to 1e7 (few duplicates)
        P = list({(rng.randint(-5 * 10**6, 5 * 10**6) * 2, rng.randint(-5 * 10**6, 5 * 10**6) * 2) for _ in range(n)})
        return {"P": P}
    if task == "delaunay":   # E2 (pre-registered): count triangles of a given triangulation that violate the empty-circle property
        while True:
            P = list({(rng.randint(-15, 15) * 2, rng.randint(-15, 15) * 2) for _ in range(n)})
            if len(P) == n and _no_collinear(P) and _no_cocircular(P):
                return {"DP": P, "DT": _triangulation(P, rng)}
    if task == "diameter":   # E2 (pre-registered): squared distance of the farthest pair of points
        return {"P": list({(rng.randint(-30, 30) * 2, rng.randint(-30, 30) * 2) for _ in range(n)})}
    if task == "clip":   # realistic multi-step (review item 3): polygon clipping, exact rational area of the intersection of two convex polygons
        while True:
            A = hull_pts([(rng.randint(-15, 15) * 2, rng.randint(-15, 15) * 2) for _ in range(n)])
            B0 = hull_pts([(rng.randint(-15, 15) * 2, rng.randint(-15, 15) * 2) for _ in range(n)])
            if len(A) < 3 or len(B0) < 3:
                continue
            ox, oy = rng.randint(-12, 12) * 2, rng.randint(-12, 12) * 2
            B = [(x + ox, y + oy) for x, y in B0]
            if clip_area2(A, B) > 0 or rng.random() < 0.15:   # mostly overlapping, some disjoint
                ka, kb = rng.randrange(len(A)), rng.randrange(len(B))
                return {"A": A[ka:] + A[:ka], "B": B[kb:] + B[:kb]}
    if task == "lattice":   # realistic multi-step (added for review item 3): Pick's theorem = area + boundary gcd counting
        while True:   # Pick needs a truly simple polygon (star_polygon alone is often self-intersecting, see is_simple)
            poly = star_polygon(n, rng)
            if is_simple(poly):
                return {"poly": poly}
    if task == "rectunion":  # realistic multi-step (review item 3): union area of overlapping axis-aligned rectangles (sweep / compression)
        R = []
        while len(R) < n:
            x, y = rng.randint(-30, 30), rng.randint(-30, 30); w, h = rng.randint(3, 25), rng.randint(3, 25)
            a, b = (x, y), (x + w, y + h)
            R.append((a, b) if rng.random() < 0.5 else ((x, y + h), (x + w, y)))   # any pair of opposite corners
        return {"R": R}
    if task == "overlap":   # held-out (designed after all findings): do two convex polygons intersect? (touching counts)
        want = "yes" if rng.random() < 0.5 else "no"
        while True:
            A = hull_pts([(rng.randint(-15, 15) * 2, rng.randint(-15, 15) * 2) for _ in range(n)])
            B0 = hull_pts([(rng.randint(-15, 15) * 2, rng.randint(-15, 15) * 2) for _ in range(n)])
            if len(A) < 3 or len(B0) < 3:
                continue
            ox, oy = rng.randint(-35, 35) * 2, rng.randint(-35, 35) * 2
            B = [(x + ox, y + oy) for x, y in B0]
            if polys_overlap(A, B) == want and all(pip(A, b) != "boundary" for b in B) and all(pip(B, a_) != "boundary" for a_ in A):
                ka, kb = rng.randrange(len(A)), rng.randrange(len(B))
                return {"A": A[ka:] + A[:ka], "B": B[kb:] + B[:kb]}
    if task == "convex":   # held-out: half convex (hull of random points), half star polygons
        if rng.random() < 0.5:
            while True:
                H = hull_pts([(rng.randint(-20, 20) * 2, rng.randint(-20, 20) * 2) for _ in range(3 * n)])
                if len(H) >= 5:
                    k = rng.randrange(len(H)); return {"poly": H[k:] + H[:k]}
        return {"poly": star_polygon(n, rng)}
    if task == "tri":      # held-out: count points strictly inside a triangle
        while True:
            T = [(rng.randint(-20, 20) * 2, rng.randint(-20, 20) * 2) for _ in range(3)]
            if abs(orient(*T)) > 200:
                break
        xs = [t[0] for t in T]; ys = [t[1] for t in T]   # odd coords inside the bounding box: never on an even-coord edge vertex
        return {"T": T, "P": [(rng.randrange(min(xs) - 1, max(xs) + 2, 2), rng.randrange(min(ys) - 1, max(ys) + 2, 2)) for _ in range(n)]}
    if task in ("hull", "close"):
        return {"P": list({(rng.randint(-30, 30) * 2, rng.randint(-30, 30) * 2) for _ in range(n)})}
    if task in ("area2", "pip"):
        poly = star_polygon(n, rng)
        want = "yes" if rng.random() < 0.5 else "no"   # balance inside / outside
        xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
        while True:  # odd coords inside the bounding box: never on an even-coord vertex row
            q = (rng.randrange(min(xs) + 1, max(xs), 2), rng.randrange(min(ys) + 1, max(ys), 2))
            if pip(poly, q) == want:
                return {"poly": poly, "q": q}
    S = []
    while len(S) < n:
        a = (rng.randint(-20, 20) * 2, rng.randint(-20, 20) * 2); b = (rng.randint(-20, 20) * 2, rng.randint(-20, 20) * 2)
        if a != b:
            S.append((a, b))
    return {"S": S}


def tf(inst, f, permute=None):
    out = {}
    for k, v in inst.items():
        if k == "q":
            out[k] = f(v)
        elif k in ("S", "R"):
            out[k] = [(f(a), f(b)) for a, b in v]
        elif k == "DT":   # E2 delaunay: triangles are index triples (the same after any point map; mirror flips their orientation)
            out[k] = [tuple(t) for t in v]
        else:
            out[k] = [f(p) for p in v]
    if permute:
        out = permute(out)
    return out


def variants(task, inst, rng):
    dx, dy = rng.randint(100, 999), -rng.randint(100, 999)
    BX, BY = 10**9 + rng.randint(0, 999), -(10**9) - rng.randint(0, 999)
    def perm(o):
        o = dict(o)
        if "P" in o:
            o["P"] = rng.sample(o["P"], len(o["P"]))
        if "poly" in o:
            k = rng.randrange(len(o["poly"])); p = o["poly"][k:] + o["poly"][:k]
            o["poly"] = p[::-1] if rng.random() < 0.5 else p
        if "T" in o:
            o["T"] = rng.sample(o["T"], 3)
        for key in ("A", "B"):
            if key in o:
                k = rng.randrange(len(o[key])); p = o[key][k:] + o[key][:k]
                o[key] = p[::-1] if rng.random() < 0.5 else p
        if "A" in o and rng.random() < 0.5:
            o["A"], o["B"] = o["B"], o["A"]
        if "R" in o:
            o["R"] = [((b, a) if rng.random() < 0.5 else (a, b)) for a, b in rng.sample(o["R"], len(o["R"]))]
        if "S" in o:
            o["S"] = [((b, a) if rng.random() < 0.5 else (a, b)) for a, b in rng.sample(o["S"], len(o["S"]))]
        if "DP" in o:   # E2 delaunay: relabel the points, shuffle the triangles, random start vertex and orientation per triangle
            sig = rng.sample(range(len(o["DP"])), len(o["DP"])); P = [None] * len(o["DP"])
            for i, p in enumerate(o["DP"]):
                P[sig[i]] = p
            T = []
            for t in o["DT"]:
                t = [sig[i] for i in t]; k = rng.randrange(3); t = t[k:] + t[:k]
                T.append(tuple(t[::-1] if rng.random() < 0.5 else t))
            o["DP"], o["DT"] = P, rng.sample(T, len(T))
        return o
    V = {"identity": inst,
         "translate": tf(inst, lambda p: (p[0] + dx, p[1] + dy)),
         "rot90": tf(inst, lambda p: (-p[1], p[0])),
         "mirror": tf(inst, lambda p: (-p[0], p[1])),
         "permute": tf(inst, lambda p: p, perm),
         "scale": tf(inst, lambda p: (3 * p[0], 3 * p[1])),
         "big": tf(inst, lambda p: (p[0] + BX, p[1] + BY))}
    d = json.loads(json.dumps(inst))
    if task == "hull":      # duplicates + points on hull edges (must not be counted)
        P = [tuple(p) for p in d["P"]]; H = sorted(set(P))
        P += [P[0], P[1]] + [((a[0] + b[0]) // 2, (a[1] + b[1]) // 2) for a, b in zip(H, H[1:])][:2]
        d["P"] = P
    elif task == "area2":   # extra collinear vertex at an edge midpoint (area unchanged)
        p = [tuple(x) for x in d["poly"]]; a, b = p[0], p[1]
        d["poly"] = [a, ((a[0] + b[0]) // 2, (a[1] + b[1]) // 2)] + p[1:]
    elif task == "pip":     # query on the horizontal line through a vertex (the classic ray-casting bug)
        p = [tuple(x) for x in d["poly"]]; v = p[rng.randrange(len(p))]
        cand = [(x, v[1]) for x in range(min(c[0] for c in p) - 3, max(c[0] for c in p) + 4, 2)]
        cand = [c for c in cand if pip(p, c) != "boundary"]
        yes = [c for c in cand if pip(p, c) == "yes"]
        d["q"] = rng.choice(yes if yes and rng.random() < 0.5 else cand)
    elif task == "segs":    # a segment touching another at its endpoint + a collinear overlapping one
        S = [tuple(map(tuple, s)) for s in d["S"]]; a, b = S[0]
        S += [(b, (b[0] + 6, b[1] - 4)), (a, ((a[0] + b[0]) // 2, (a[1] + b[1]) // 2))]
        d["S"] = S
    elif task in ("overlap", "clip"):  # B moved so its lowest-then-leftmost vertex sits exactly on A's highest-then-rightmost vertex: touching -> yes
        A = [tuple(x) for x in d["A"]]; B = [tuple(x) for x in d["B"]]
        a = max(A, key=lambda p: (p[1], p[0])); b = min(B, key=lambda p: (p[1], p[0]))
        d["A"], d["B"] = A, [(x + a[0] - b[0], y + a[1] - b[1]) for x, y in B]
    elif task == "lattice":  # extra collinear vertex at an edge midpoint (answer unchanged) + doubled coordinates
        p = [(2 * x[0], 2 * x[1]) for x in d["poly"]]; a, b = p[0], p[1]
        d["poly"] = [a, ((a[0] + b[0]) // 2, (a[1] + b[1]) // 2)] + p[1:]
    elif task == "rectunion":  # a duplicate rectangle, one sharing an edge exactly with rectangle 0, one nested inside rectangle 1
        R = [tuple(map(tuple, r)) for r in d["R"]]
        (ax, ay), (bx, by) = R[0]; x0, x1, y1 = min(ax, bx), max(ax, bx), max(ay, by)
        (cx, cy), (ex, ey) = R[1]; mx, my = (cx + ex) // 2, (cy + ey) // 2
        R += [R[2], ((x0, y1), (x1, y1 + 7)), ((mx, my), (mx + (1 if ex > cx else -1), my + (1 if ey > cy else -1)))]
        d["R"] = R
    elif task == "convex":  # doubled coordinates + an extra collinear vertex at an edge midpoint (convexity unchanged)
        p = [(2 * x[0], 2 * x[1]) for x in d["poly"]]; a, b = p[0], p[1]
        d["poly"] = [a, ((a[0] + b[0]) // 2, (a[1] + b[1]) // 2)] + p[1:]
    elif task == "tri":     # doubled coordinates + a point on a triangle edge (not inside) + a duplicated point
        T = [(2 * x[0], 2 * x[1]) for x in d["T"]]; P = [(2 * x[0], 2 * x[1]) for x in d["P"]]
        P += [((T[0][0] + T[1][0]) // 2, (T[0][1] + T[1][1]) // 2), P[rng.randrange(len(P))]]
        d["T"], d["P"] = T, P
    elif task == "delaunay":  # doubled coordinates + 4 cocircular points (a small rectangle) to the right, re-triangulated:
        P = [(2 * x[0], 2 * x[1]) for x in d["DP"]]   # points exactly ON a circumcircle must not count
        mx, ys = max(p[0] for p in P), [p[1] for p in P]
        while True:
            x0, y0 = mx + 10 + 2 * rng.randint(0, 3), 2 * rng.randint(min(ys) // 2, max(ys) // 2)
            w, h = 2 * rng.randint(1, 3), 2 * rng.randint(1, 3)
            Q = P + [(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h)]
            if _no_collinear(Q):
                break
        d["DP"], d["DT"] = Q, _triangulation(Q, rng)
    elif task in ("hullL", "closeL", "diamL"):   # H1: duplicates + midpoints of two hull edges (collinear points on the hull)
        P = [tuple(p) for p in d["P"]]; H = hull_pts(P)
        d["P"] = P + [P[rng.randrange(len(P))], H[0]] + [((H[k][0] + H[k + 1][0]) // 2, (H[k][1] + H[k + 1][1]) // 2) for k in range(min(2, len(H) - 1))]
    elif task == "diameter":  # doubled coordinates + a duplicated hull vertex + the midpoint of a hull edge (answer x4)
        P = [(2 * x[0], 2 * x[1]) for x in d["P"]]; H = hull_pts(P)
        d["P"] = P + [H[0], ((H[0][0] + H[1][0]) // 2, (H[0][1] + H[1][1]) // 2)]
    else:                   # duplicate point -> closest distance 0
        P = [tuple(p) for p in d["P"]]; d["P"] = P + [P[rng.randrange(len(P))]]
    V["degen"] = d
    return V


def answer(task, x):
    if task == "hullL":
        return str(hull_count([tuple(p) for p in x["P"]]))
    if task == "closeL":
        return str(closest_fast([tuple(p) for p in x["P"]]))
    if task == "diamL":
        return str(diam_fast([tuple(p) for p in x["P"]]))
    if task == "delaunay":
        return str(bad_triangles([tuple(p) for p in x["DP"]], [tuple(t) for t in x["DT"]]))
    if task == "diameter":
        return str(diam2([tuple(p) for p in x["P"]]))
    if task == "clip":
        return fmt_frac(clip_area2([tuple(p) for p in x["A"]], [tuple(p) for p in x["B"]]))
    if task == "lattice":
        return str(lattice_inside([tuple(p) for p in x["poly"]]))
    if task == "rectunion":
        return str(rect_union([tuple(map(tuple, r)) for r in x["R"]]))
    if task == "overlap":
        return polys_overlap([tuple(p) for p in x["A"]], [tuple(p) for p in x["B"]])
    if task == "convex":
        return is_convex_poly([tuple(p) for p in x["poly"]])
    if task == "tri":
        return str(tri_inside([tuple(p) for p in x["T"]], [tuple(p) for p in x["P"]]))
    if task == "hull":
        return str(hull_count([tuple(p) for p in x["P"]]))
    if task == "area2":
        return str(area2([tuple(p) for p in x["poly"]]))
    if task == "pip":
        return pip([tuple(p) for p in x["poly"]], tuple(x["q"]))
    if task == "segs":
        return str(segs_count([tuple(map(tuple, s)) for s in x["S"]]))
    return str(closest([tuple(p) for p in x["P"]]))


def render(task, x):
    if task in ("hullL", "closeL", "diamL"):   # H1: same statements as hull / close / diameter, plus the size bound and time limit
        base = {"hullL": "hull", "closeL": "close", "diamL": "diameter"}[task]
        q, stdin, fmt = render(base, {"P": x["P"][:3]})   # statement text without listing 20000 points
        head = "Points: (given on stdin; up to 20000 points with integer coordinates up to 10^7 in absolute value)"
        q = head + q[q.index("\n\n"):] + LARGE_NOTE
        stdin = f"{len(x['P'])}\n" + "\n".join(f"{p[0]} {p[1]}" for p in x["P"]) + "\n"
        return q, stdin, fmt
    if task == "delaunay":
        pts = " ".join(f"{i}:({p[0]},{p[1]})" for i, p in enumerate(x["DP"])); tris = " ".join(f"[{a},{b},{c}]" for a, b, c in x["DT"])
        stdin = (f"{len(x['DP'])}\n" + "\n".join(f"{p[0]} {p[1]}" for p in x["DP"]) + f"\n{len(x['DT'])}\n"
                 + "\n".join(f"{a} {b} {c}" for a, b, c in x["DT"]) + "\n")
        return (f"Points (numbered from 0): {pts}\nA triangulation of these points consists of the triangles (point numbers): {tris}\n\n"
                f"How many of these triangles have at least one of the listed points STRICTLY inside their circumcircle? (A point "
                f"exactly on a circumcircle does not count; 0 means the triangulation is a Delaunay triangulation.)", stdin,
                "first line n, then n lines `x y` (points 0..n-1), then a line m, then m lines `i j k` (the point numbers of one triangle)")
    if task == "diameter":
        pts = " ".join(f"({p[0]},{p[1]})" for p in x["P"])
        stdin = f"{len(x['P'])}\n" + "\n".join(f"{p[0]} {p[1]}" for p in x["P"]) + "\n"
        return (f"Points: {pts}\n\nWhat is the SQUARED Euclidean distance between the two points that are farthest apart?", stdin,
                "first line n, then n lines `x y`")
    if task == "clip":
        pa = " ".join(f"({p[0]},{p[1]})" for p in x["A"]); pb = " ".join(f"({p[0]},{p[1]})" for p in x["B"])
        stdin = (f"{len(x['A'])}\n" + "\n".join(f"{p[0]} {p[1]}" for p in x["A"]) + f"\n{len(x['B'])}\n"
                 + "\n".join(f"{p[0]} {p[1]}" for p in x["B"]) + "\n")
        return (f"Convex polygon A has vertices in order: {pa}\nConvex polygon B has vertices in order: {pb}\n\nWhat is TWICE the area of "
                f"the intersection of A and B? Give the exact value as an irreducible fraction p/q, or as an integer if it is whole "
                f"(0 if they do not overlap or only touch).", stdin,
                "first line n, then n lines `x y` (polygon A in order), then a line m, then m lines `x y` (polygon B in order); "
                "print the exact value as p/q or an integer")
    if task == "lattice":
        poly = " ".join(f"({p[0]},{p[1]})" for p in x["poly"])
        stdin = f"{len(x['poly'])}\n" + "\n".join(f"{p[0]} {p[1]}" for p in x["poly"]) + "\n"
        return (f"A simple polygon has these integer vertices in order: {poly}\n\nHow many points with integer coordinates lie "
                f"STRICTLY inside the polygon? (Points on the boundary do not count.)", stdin,
                "first line n, then n lines `x y` (polygon vertices in order)")
    if task == "rectunion":
        rs = "; ".join(f"[({a[0]},{a[1]})-({b[0]},{b[1]})]" for a, b in x["R"])
        stdin = f"{len(x['R'])}\n" + "\n".join(f"{a[0]} {a[1]} {b[0]} {b[1]}" for a, b in x["R"]) + "\n"
        return (f"Axis-aligned rectangles, each given by two opposite corners: {rs}\n\nWhat is the total area covered by the "
                f"union of these rectangles? (Overlapping regions count once.)", stdin,
                "first line m, then m lines `x1 y1 x2 y2` (two opposite corners of one rectangle)")
    if task == "overlap":
        pa = " ".join(f"({p[0]},{p[1]})" for p in x["A"]); pb = " ".join(f"({p[0]},{p[1]})" for p in x["B"])
        stdin = (f"{len(x['A'])}\n" + "\n".join(f"{p[0]} {p[1]}" for p in x["A"]) + f"\n{len(x['B'])}\n"
                 + "\n".join(f"{p[0]} {p[1]}" for p in x["B"]) + "\n")
        return (f"Convex polygon A has vertices in order: {pa}\nConvex polygon B has vertices in order: {pb}\n\nDo A and B "
                f"intersect, i.e. share at least one point? (Touching at a single point or along an edge counts; one polygon lying "
                f"entirely inside the other counts.) Answer yes or no.", stdin,
                "first line n, then n lines `x y` (polygon A in order), then a line m, then m lines `x y` (polygon B in order); print yes or no")
    if task == "convex":
        poly = " ".join(f"({p[0]},{p[1]})" for p in x["poly"])
        stdin = f"{len(x['poly'])}\n" + "\n".join(f"{p[0]} {p[1]}" for p in x["poly"]) + "\n"
        return (f"A simple polygon has these vertices in order: {poly}\n\nIs the polygon convex? (Three consecutive collinear "
                f"vertices are allowed in a convex polygon.) Answer yes or no.", stdin,
                "first line n, then n lines `x y` (polygon vertices in order); print yes or no")
    if task == "tri":
        tri = " ".join(f"({p[0]},{p[1]})" for p in x["T"]); pts = " ".join(f"({p[0]},{p[1]})" for p in x["P"])
        stdin = " ".join(f"{p[0]} {p[1]}" for p in x["T"]) + f"\n{len(x['P'])}\n" + "\n".join(f"{p[0]} {p[1]}" for p in x["P"]) + "\n"
        return (f"Triangle with vertices {tri}. Points: {pts}\n\nHow many of the listed points lie STRICTLY inside the triangle? "
                f"(Points on an edge do not count; duplicate points count separately.)", stdin,
                "first line `x1 y1 x2 y2 x3 y3` (the triangle), then a line n, then n lines `x y`")
    if task in ("hull", "close"):
        pts = " ".join(f"({p[0]},{p[1]})" for p in x["P"])
        stdin = f"{len(x['P'])}\n" + "\n".join(f"{p[0]} {p[1]}" for p in x["P"]) + "\n"
        q = ("How many vertices does the convex hull of these points have? Points lying on a hull edge (collinear) "
             "are not vertices; duplicate points count once." if task == "hull" else
             "What is the SQUARED Euclidean distance between the closest pair of points (two points of the list; "
             "if two points coincide the answer is 0)?")
        fmt = "first line n, then n lines `x y`"
        return f"Points: {pts}\n\n{q}", stdin, fmt
    if task in ("area2", "pip"):
        poly = " ".join(f"({p[0]},{p[1]})" for p in x["poly"])
        stdin = f"{len(x['poly'])}\n" + "\n".join(f"{p[0]} {p[1]}" for p in x["poly"])
        if task == "area2":
            return (f"A simple polygon has these vertices in order: {poly}\n\nWhat is TWICE its area (an integer)?",
                    stdin + "\n", "first line n, then n lines `x y` (polygon vertices in order)")
        qx, qy = x["q"]
        return (f"A simple polygon has these vertices in order: {poly}\n\nIs the point ({qx},{qy}) strictly inside the "
                f"polygon? (It is not on the boundary.) Answer yes or no.", stdin + f"\n{qx} {qy}\n",
                "first line n, then n lines `x y` (polygon vertices in order), then a line `qx qy`; print yes or no")
    segs = "; ".join(f"[({a[0]},{a[1]})-({b[0]},{b[1]})]" for a, b in x["S"])
    stdin = f"{len(x['S'])}\n" + "\n".join(f"{a[0]} {a[1]} {b[0]} {b[1]}" for a, b in x["S"]) + "\n"
    return (f"Segments: {segs}\n\nHow many PAIRS of these segments intersect (sharing even a single point counts)?",
            stdin, "first line m, then m lines `x1 y1 x2 y2`")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_tag", required=True)
    ap.add_argument("--mode", choices=["direct", "code"], default="direct")
    ap.add_argument("--think", action="store_true")
    ap.add_argument("--max_tokens", type=int, default=2048)
    ap.add_argument("--n_inst", type=int, default=10)
    ap.add_argument("--workers", type=int, default=64)
    ap.add_argument("--canon", action="store_true", help="direct arm: tell the model to translate to the origin first")
    ap.add_argument("--canon_prompt", action="store_true", help="S2b: translate the instance (min x = min y = 0) before showing it")
    a = ap.parse_args()
    sizes = {"hull": (10, 20), "area2": (8, 14), "pip": (8, 14), "segs": (6, 10), "close": (10, 20)}
    jobs = []
    for task, ns in sizes.items():
        for n in ns:
            for i in range(a.n_inst):
                rng = random.Random(f"{task}-{n}-{i}")
                inst = base_instance(task, n, rng)
                for vname, x in variants(task, inst, rng).items():
                    jobs.append((task, n, i, vname, x))

    def canon_inst(x):
        pts = []
        for k, v in x.items():
            pts += [p for s_ in v for p in s_] if k == "S" else ([v] if k == "q" else list(v))
        mx, my = min(p[0] for p in pts), min(p[1] for p in pts)
        f = lambda p: (p[0] - mx, p[1] - my)  # noqa: E731
        return {k: ([(f(a_), f(b_)) for a_, b_ in v] if k == "S" else (f(v) if k == "q" else [f(p) for p in v])) for k, v in x.items()}

    def run(j):
        task, n, i, vname, x = j
        if a.canon_prompt:
            x = canon_inst(x)   # translation keeps every answer unchanged
        q, stdin, fmt = render(task, x)
        gold = answer(task, x)
        if a.mode == "direct":
            canon = ("\n\nBefore computing anything, translate all coordinates so that the smallest x and the smallest y "
                     "become 0 (subtract the minimum x and minimum y; this does not change the answer), list the "
                     "translated coordinates, then compute.") if a.canon else ""
            o = chat(q + canon + "\n\nEnd your reply with a line `ANSWER: <answer>`.", think=a.think, max_tokens=a.max_tokens, temperature=0.0)
            m = re.findall(r"ANSWER:\s*\**\s*(-?\d+|yes|no|Yes|No|YES|NO)", o["text"])
            pred = m[-1].lower() if m else None
        else:
            o = chat(f"{q}\n\nDo not compute the answer by hand. Write a Python 3 program that solves this problem for any "
                     f"input in the following stdin format: {fmt}. Print only the answer. Give the program in a single "
                     f"```python code block.", think=a.think, max_tokens=a.max_tokens, temperature=0.0)
            code = last_block(o["text"], ("python", "py", "python3"))
            r = run_python(code, stdin, timeout=10) if code else None
            pred = (r.stdout.strip().split() or [None])[-1].lower() if r and r.status == "ok" else None
        return {"task": task, "n": n, "inst": i, "variant": vname, "gold": gold, "pred": pred, "correct": pred == gold,
                "finish": o["finish"], "out_tokens": o["out_tokens"], "code": code if a.mode == "code" else None}
    with ThreadPoolExecutor(a.workers) as ex, open(f"{RES}/geo_{a.model_tag}.jsonl", "w") as f:
        for r in ex.map(run, jobs):
            f.write(json.dumps(r) + "\n")


if __name__ == "__main__":
    main()
