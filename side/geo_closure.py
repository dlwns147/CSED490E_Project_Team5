"""SIDE-GT-CLOSE: one deductive closure over a whole pool of auxiliary points, instead of a search over which points to add.

DDAR is monotone, so the closure of H plus a pool contains every proof that uses any subset of that pool. Adding points one at a time, in pairs,
or in batches of six (HAGeo) is only a way to keep DDAR affordable. Its cost comes from matching rules over all point tuples. But a sound rule
concludes only facts true on the figure, so instantiate from the other side: compute what is true numerically, and for each true fact test
whether a rule's premises are already derived. Angle and length chasing become membership in a linear span, tested in O(1) by a random
element of the span's annihilator (each line direction and each log-length carries a value mod a large prime, kept on every relation added).
A circle is one more linear fact: chord (x, y) has direction t_x + t_y, and with a known centre the radius to x has direction 2 t_x, which absorbs the
inscribed angle, central angle, tangent-chord, Thales-circle and parallel-chord rules. Constants are dropped: a conclusion is only ever drawn when
it holds on the figure, and that fixes the constant. The rules are Newclid 2.0.2's default 43; the ones that are not linear (similar triangles, the
bisector theorem, perpendicular bisectors, midpoints, the trapezoid) are tested on their numerically true instances.
The engine finds proofs. Every relation it adds is logged with its rule and premises, and `explain` reads a proof back from that log: the exact
linear combination behind each premise, the points the proof needs, and each step's truth on fresh figures. Plain guarded Newclid is tried on the
same points as a second, separate check.
  python side/geo_closure.py run <rows.jsonl> <out.jsonl> --k K [--timeout S] [--workers W] [--proofs DIR]
K = 0: the translation alone; K > 0: K candidates (geo_translate.aux_candidates, seed 0) all at once."""
import itertools, json, math, os, random, subprocess, sys, time
import numpy as np

P = (1 << 61) - 1
TOL = 1e-7


class Lin:
    """Variables mod P, each as an expression in the free ones, with a random value that vanishes on every relation added."""

    def __init__(self, seed=0):
        self.rng, self.idx, self.expr, self.val, self.rv, self.users, self.rank = random.Random(seed), {}, [], [], {}, {}, 0

    def var(self, key):
        i = self.idx.get(key)
        if i is None:
            i = len(self.expr)
            self.idx[key] = i
            r = self.rng.randrange(1, P)
            self.expr.append({i: 1}); self.val.append(r); self.rv[i] = r; self.users[i] = {i}
        return i

    def add(self, rel):
        """rel = [(variable, coefficient), ...] = 0. -> True if it was new."""
        if not sum(c * self.val[v] for v, c in rel) % P:
            return False
        e = {}
        for v, c in rel:
            for f, q in self.expr[v].items():
                e[f] = (e.get(f, 0) + c * q) % P
        e = {f: q for f, q in e.items() if q}
        if not e:
            return False
        w = min(e, key=lambda f: len(self.users[f]))
        ic = pow(P - e.pop(w), P - 2, P)   # w = sum(ic * q * f)
        sol = {f: q * ic % P for f, q in e.items()}
        d = (sum(q * self.rv[f] for f, q in sol.items()) - self.rv[w]) % P
        for v in self.users.pop(w):
            ex = self.expr[v]
            cv = ex.pop(w)
            for f, q in sol.items():
                n = (ex.get(f, 0) + cv * q) % P
                if n:
                    ex[f] = n
                    self.users[f].add(v)
                else:
                    ex.pop(f, None)
                    self.users[f].discard(v)
            self.val[v] = (self.val[v] + cv * d) % P
        del self.rv[w]
        self.rank += 1
        return True


class Closure:
    def __init__(self, names, xy, facts, deadline=None, seed=0, log=True):
        self.names, self.n = list(names), len(names)
        self.log = [] if log else None
        self.ix = {a: i for i, a in enumerate(self.names)}
        self.xy = np.array(xy, float)
        self.deadline = deadline
        self.D, self.W = Lin(seed), Lin(seed + 1)
        n = self.n
        self.u = [[0] * n for _ in range(n)]
        self.w = [[0] * n for _ in range(n)]
        for a, b in itertools.combinations(range(n), 2):
            self.u[a][b] = self.u[b][a] = self.D.var(("u", a, b))
            self.w[a][b] = self.w[b][a] = self.W.var(("w", a, b))
        dx = self.xy[:, 0, None] - self.xy[:, 0]
        dy = self.xy[:, 1, None] - self.xy[:, 1]
        self.dx, self.dy, self.L = dx, dy, np.hypot(dx, dy)
        self.groups, self.gid, self.done_center, self.mid_done = {}, 0, set(), set()
        self.cur_group, self.group_rows = None, {}
        self.prep()
        for f in facts:
            self.ingest(*f)

    def da(self, rel, tag, prem, concl):
        """an angle relation, with the rule, its premises and its conclusion (facts over point numbers), kept in the log if it was new"""
        new = self.D.add(rel)
        if new and self.log is not None:
            self.log.append(("D", rel, tag, prem, concl))
            if self.cur_group is not None:
                self.group_rows.setdefault(self.cur_group, []).append(len(self.log) - 1)
        return new

    def wa(self, rel, tag, prem, concl):
        new = self.W.add(rel)
        if new and self.log is not None:
            self.log.append(("W", rel, tag, prem, concl))
        return new

    def tick(self):
        if self.deadline and time.time() > self.deadline:
            raise TimeoutError

    # numeric truth
    def cross(self, a, b, c, d):
        return self.dx[b, a] * self.dy[d, c] - self.dy[b, a] * self.dx[d, c]

    def is_para(self, a, b, c, d):
        return abs(self.cross(a, b, c, d)) <= TOL * max(self.L[a, b] * self.L[c, d], 1e-3)

    def is_coll(self, a, b, c):
        return a != b and a != c and b != c and self.is_para(a, b, a, c)

    def prep(self):
        n, L = self.n, self.L
        # lines
        self.line_of = {}
        lines = {}
        for a in range(n):
            self.tick()
            for b in range(a + 1, n):
                if L[a, b] < 1e-9 or (a, b) in self.line_of:
                    continue
                pts = [a, b] + [c for c in range(n) if c != a and c != b and self.is_para(a, b, a, c)]
                lid = len(lines)
                lines[lid] = sorted(pts)
                for x, y in itertools.combinations(sorted(pts), 2):
                    self.line_of[x, y] = lid
        self.lines = lines
        # equal distances from each point, midpoints, perpendicular bisectors
        self.eq_at, self.bis_of, self.mids = {}, {}, []
        for o in range(n):
            d = {}
            for x in range(n):
                if x != o and L[o, x] > 1e-9:
                    d.setdefault(round(L[o, x] * 1e6), []).append(x)
            gs = [sorted(g) for g in d.values() if len(g) >= 2]
            self.eq_at[o] = gs
            for g in gs:
                for x, y in itertools.combinations(g, 2):
                    self.bis_of.setdefault((x, y), []).append(o)
                    if self.is_coll(o, x, y) and abs(self.xy[o] * 2 - self.xy[x] - self.xy[y]).max() < 1e-6:
                        self.mids.append((o, x, y))
        # circles of four or more points
        C = {}
        if n >= 4:
            I = np.array(list(itertools.combinations(range(n), 3)), dtype=np.int32)
            A, B, Cc = self.xy[I[:, 0]], self.xy[I[:, 1]], self.xy[I[:, 2]]
            D = 2 * (A[:, 0] * (B[:, 1] - Cc[:, 1]) + B[:, 0] * (Cc[:, 1] - A[:, 1]) + Cc[:, 0] * (A[:, 1] - B[:, 1]))
            ok = np.abs(D) > 1e-9
            a2, b2, c2 = (A ** 2).sum(1), (B ** 2).sum(1), (Cc ** 2).sum(1)
            with np.errstate(divide="ignore", invalid="ignore"):
                ux = (a2 * (B[:, 1] - Cc[:, 1]) + b2 * (Cc[:, 1] - A[:, 1]) + c2 * (A[:, 1] - B[:, 1])) / D
                uy = (a2 * (Cc[:, 0] - B[:, 0]) + b2 * (A[:, 0] - Cc[:, 0]) + c2 * (B[:, 0] - A[:, 0])) / D
            r = np.hypot(A[:, 0] - ux, A[:, 1] - uy)
            for (i, j, k), x, y, rr, o in zip(I.tolist(), ux.tolist(), uy.tolist(), r.tolist(), ok.tolist()):
                if o and rr < 1e4:
                    C.setdefault((round(x * 1e6), round(y * 1e6), round(rr * 1e6)), set()).update((i, j, k))
        self.circles = {i: sorted(s) for i, s in enumerate(v for v in C.values() if len(v) >= 4)}
        self.circle_at = {}
        for cid, s in self.circles.items():
            for q in s:
                self.circle_at.setdefault(q, []).append(cid)
        self.quad_done = set()
        # similar triangles: numerically true pairs with their correspondence
        self.sim = []
        if n >= 4:
            s1, s2, s3 = L[I[:, 0], I[:, 1]], L[I[:, 1], I[:, 2]], L[I[:, 0], I[:, 2]]
            S = np.sort(np.stack([s1, s2, s3], 1), 1)
            good = (S[:, 0] > 1e-9) & (S[:, 0] + S[:, 1] - S[:, 2] > 1e-7 * S[:, 2])
            kr = np.round(S[:, 0] / S[:, 2] * 1e6).astype(np.int64)
            ks = np.round(S[:, 1] / S[:, 2] * 1e6).astype(np.int64)
            G = {}
            for t, g, p, q in zip(I.tolist(), good.tolist(), kr.tolist(), ks.tolist()):
                if g:
                    G.setdefault((p, q), []).append(tuple(t))
            for g in G.values():
                if len(g) < 2:
                    continue
                self.tick()
                for t1, t2 in itertools.combinations(g, 2):
                    self.sim += self.correspond(t1, t2)
        # bisector theorem instances: apex a, line through b, c, d
        self.bisect = []
        for pts in lines.values():
            if len(pts) < 3:
                continue
            self.tick()
            for b, c in itertools.combinations(pts, 2):
                for d in pts:
                    if d == b or d == c:
                        continue
                    for a in range(n):
                        if a in pts:
                            continue
                        if abs(L[d, b] * L[a, c] - L[d, c] * L[a, b]) < 1e-7 * max(L[a, b] * L[d, c], 1e-3):
                            self.bisect.append((a, b, c, d))
        # Thales' converse: lines through o, a c on one, b d on the other, ab parallel to cd
        self.thales = []
        by_pt = {}
        for lid, pts in lines.items():
            if len(pts) >= 3:
                for q in pts:
                    by_pt.setdefault(q, []).append(lid)
        for o, ls in by_pt.items():
            self.tick()
            for l1, l2 in itertools.combinations(ls, 2):
                A_ = [q for q in lines[l1] if q != o]
                B_ = [q for q in lines[l2] if q != o]
                for a, c in itertools.permutations(A_, 2):
                    for b, d in itertools.permutations(B_, 2):
                        if a < c and self.is_para(a, b, c, d):
                            self.thales.append((o, a, c, b, d))
        # the trapezoid: ab, cd, mn parallel, m on ad, n on bc
        self.trap = []
        cl = {}
        for lid, pts in lines.items():
            a, b = pts[0], pts[1]
            th = round(math.atan2(self.dy[b, a], self.dx[b, a]) % math.pi * 1e6) % round(math.pi * 1e6)
            cl.setdefault(th, []).append(lid)
        for ls in cl.values():
            if len(ls) < 3:
                continue
            for l1, l2, l3 in itertools.permutations(ls, 3):
                self.tick()
                if l1 > l2:
                    continue
                for a, b in itertools.permutations(lines[l1], 2):
                    for c, d in itertools.permutations(lines[l2], 2):
                        for m in lines[l3]:
                            if self.is_coll(m, a, d):
                                for k in lines[l3]:
                                    if k != m and self.is_coll(k, b, c):
                                        self.trap.append((a, b, c, d, m, k))

    def correspond(self, t1, t2):
        """every vertex correspondence that makes t1, t2 similar, with its orientation; t1 and t2 differ"""
        L, out = self.L, []
        a, b, c = t1
        for p, q, r in itertools.permutations(t2):
            if abs(L[a, b] * L[q, r] - L[b, c] * L[p, q]) < TOL * L[b, c] * L[p, q] and abs(L[b, c] * L[r, p] - L[c, a] * L[q, r]) < TOL * L[c, a] * L[q, r]:
                o = self.cross(a, b, a, c) * self.cross(p, q, p, r) > 0
                out.append((a, b, c, p, q, r, o))
        return out

    # facts
    def ingest(self, name, *a):
        i = [self.ix[x] if isinstance(x, str) else x for x in a]
        u, w = self.u, self.w
        F = (name, *i)
        if name in ("coll", "collx"):
            q = list(dict.fromkeys(i))
            for x, y in itertools.combinations(q, 2):
                self.da([(u[q[0]][q[1]], 1), (u[x][y], -1)], "given", (), ("coll", q[0], q[1], x, y))
        elif name in ("para", "perp"):
            self.da([(u[i[0]][i[1]], 1), (u[i[2]][i[3]], -1)], "given", (), F)
        elif name == "cong":
            self.wa([(w[i[0]][i[1]], 1), (w[i[2]][i[3]], -1)], "given", (), F)
        elif name == "cyclic":
            self.new_group(set(i), None, "given", ())
        elif name == "circle":
            for c in i[2:]:
                self.wa([(w[i[0]][i[1]], 1), (w[i[0]][c], -1)], "given", (), ("cong", i[0], i[1], i[0], c))
        elif name == "midp":
            self.da([(u[i[0]][i[1]], 1), (u[i[0]][i[2]], -1)], "given", (), ("coll", i[0], i[1], i[0], i[2]))
            self.wa([(w[i[0]][i[1]], 1), (w[i[0]][i[2]], -1)], "given", (), ("cong", i[0], i[1], i[0], i[2]))
        elif name in ("eqangle", "eqangle6"):
            self.eqa("given", (), *i)
        elif name in ("eqratio", "eqratio6"):
            self.eqr("given", (), *i)
        elif name == "aconst":
            self.da([(u[i[0]][i[1]], 1), (u[i[2]][i[3]], -1)], "given", (), ("const", *i))
        elif name == "rconst":
            self.wa([(w[i[0]][i[1]], 1), (w[i[2]][i[3]], -1)], "given", (), ("const", *i))
        elif name == "lconst":
            self.wa([(w[i[0]][i[1]], 1)], "given", (), ("const", *i))
        elif name in ("simtri", "simtri2", "contri", "contri2", "simtri*", "contri*"):
            self.sim_fact("given", (), *i, not name.endswith("2"))
            if name.startswith("contri"):
                self.wa([(w[i[0]][i[1]], 1), (w[i[3]][i[4]], -1)], "given", (), ("cong", i[0], i[1], i[3], i[4]))

    def eqa(self, tag, prem, a, b, c, d, e, f, g, h):
        u = self.u
        rel = {}
        for v, s in ((u[a][b], 1), (u[c][d], -1), (u[e][f], -1), (u[g][h], 1)):
            rel[v] = rel.get(v, 0) + s
        return self.da(list(rel.items()), tag, prem, ("eqangle", a, b, c, d, e, f, g, h))

    def eqr(self, tag, prem, a, b, c, d, e, f, g, h):
        w = self.w
        rel = {}
        for v, s in ((w[a][b], 1), (w[c][d], -1), (w[e][f], -1), (w[g][h], 1)):
            rel[v] = rel.get(v, 0) + s
        return self.wa(list(rel.items()), tag, prem, ("eqratio", a, b, c, d, e, f, g, h))

    def sim_fact(self, tag, prem, a, b, c, p, q, r, o):
        s = -1 if o else 1
        u, w, ch = self.u, self.w, False
        F = ("simtri" if o else "simtri2", a, b, c, p, q, r)
        for (x, y, z), (x2, y2, z2) in (((a, b, c), (p, q, r)), ((b, a, c), (q, p, r))):
            rel = {}
            for v, k in ((u[x][y], 1), (u[x][z], -1), (u[x2][y2], s), (u[x2][z2], -s)):
                rel[v] = rel.get(v, 0) + k
            ch |= self.da(list(rel.items()), tag, prem, F)
        for x, y, x2, y2 in ((b, c, q, r), (c, a, r, p)):
            rel = {}
            for v, k in ((w[a][b], 1), (w[p][q], -1), (w[x][y], -1), (w[x2][y2], 1)):
                rel[v] = rel.get(v, 0) + k
            ch |= self.wa(list(rel.items()), tag, prem, F)
        return ch

    def new_group(self, pts, centre, tag, prem):
        """a set of points proved concyclic (with its centre if known): chord (x, y) has direction t_x + t_y, a radius 2 t_x"""
        pts = set(pts)
        ids = []
        for g in list(self.groups.values()):
            if centre == g["centre"] and len(pts & g["pts"]) >= 3:
                pts |= g["pts"]
                ids.append(g["id"])
                prem = tuple(prem) + (("cyclic_group", g["id"]),)
                del self.groups[g["id"]]
        self.gid += 1
        g = {"id": self.gid, "pts": pts, "centre": centre, "t": {x: self.D.var(("t", self.gid, x)) for x in pts}}
        self.groups[self.gid] = g
        F = ("circle", centre, *sorted(pts)) if centre is not None else ("cyclic", *sorted(pts))
        self.cur_group = self.gid
        for x, y in itertools.combinations(sorted(pts), 2):
            self.da([(self.u[x][y], 1), (g["t"][x], -1), (g["t"][y], -1)], tag, prem, F)
        if centre is not None:
            for x in pts:
                self.da([(self.u[centre][x], 1), (g["t"][x], -2)], tag, prem, F)
        self.cur_group = None
        return g

    # one pass over the rules that are not linear
    def round(self):
        Dv, Wv = self.D.val, self.W.val
        u, w, L = self.u, self.w, self.L
        r0 = self.D.rank + self.W.rank
        g0 = len(self.groups)

        def d(a, b):
            return Dv[u[a][b]]

        def l(a, b):
            return Wv[w[a][b]]

        def ang(a, b, c, e, f, h):   # (ab, ac) = (ef, eh) as directed angles
            return not (Dv[u[a][b]] - Dv[u[a][c]] - Dv[u[e][f]] + Dv[u[e][h]]) % P
        # lines: two of a triple's directions equal means collinear; two proved lines sharing two points are one
        for pts in self.lines.values():
            if len(pts) < 3:
                continue
            sets = []
            for x, y, z in itertools.combinations(pts, 3):
                p_, q_, r_ = d(x, y), d(x, z), d(y, z)
                if p_ == q_ or p_ == r_ or q_ == r_:
                    pr = ("para", x, y, x, z) if p_ == q_ else ("para", x, y, y, z) if p_ == r_ else ("para", x, z, y, z)
                    new, prem = {x, y, z}, [pr]
                    for t in [t for t in sets if len(t[0] & new) >= 2]:
                        new |= t[0]
                        prem += t[1]
                        sets.remove(t)
                    sets.append((new, prem))
            for t, prem in sets:
                q = sorted(t)
                for x, y in itertools.combinations(q, 2):
                    if d(x, y) != d(q[0], q[1]):
                        self.da([(u[q[0]][q[1]], 1), (u[x][y], -1)], "line", tuple(prem), ("coll", q[0], q[1], x, y))
        # centres and isosceles triangles
        for o, gs in self.eq_at.items():
            self.tick()
            for g in gs:
                cls = {}
                for x in g:
                    cls.setdefault(l(o, x), []).append(x)
                for c in cls.values():
                    if len(c) >= 2:
                        for x, y in itertools.combinations(c, 2):
                            if not self.is_coll(o, x, y):
                                self.da([(u[x][y], 2), (u[o][x], -1), (u[o][y], -1)], "isosceles", (("cong", o, x, o, y),), ("eqangle", x, y, o, x, o, y, x, y))
                    if len(c) >= 3 and (o, tuple(c)) not in self.done_center:
                        self.done_center.add((o, tuple(c)))
                        prem = tuple(("cong", o, c[0], o, x) for x in c[1:])
                        self.new_group(c, o, "centre", prem)
                        if len(c) >= 4:
                            self.new_group(c, None, "centre_cyclic", prem)
                reps = list(cls.values())
                for c1, c2 in itertools.combinations(reps, 2):
                    x, y = c1[0], c2[0]
                    if not self.is_coll(o, x, y) and not (2 * d(x, y) - d(o, x) - d(o, y)) % P:
                        self.wa([(w[o][x], 1), (w[o][y], -1)], "base_angles", (("eqangle", x, y, o, x, o, y, x, y),), ("cong", o, x, o, y))
        # circles: inscribed angles conclude cyclic
        for cid, pts in self.circles.items():
            self.tick()
            for q in itertools.combinations(pts, 4):
                if (cid, q) in self.quad_done:
                    continue
                if any(set(q) <= g["pts"] for g in self.groups.values() if g["centre"] is None):
                    self.quad_done.add((cid, q))
                    continue
                a, b, p, s = q
                for x, y, e, f in ((p, s, a, b), (b, s, a, p), (b, p, a, s)):
                    if ang(x, e, f, y, e, f):
                        self.quad_done.add((cid, q))
                        self.new_group(set(q), None, "inscribed", (("eqangle", x, e, x, f, y, e, y, f),))
                        break
        # equal chords
        for g in list(self.groups.values()):
            T = g["t"]
            pts = sorted(g["pts"])
            if len(pts) < 3:
                continue
            ch = {}
            for x, y in itertools.combinations(pts, 2):
                ch.setdefault(round(L[x, y] * 1e6), []).append((x, y))
            for c in ch.values():
                for (x, y), (p, q) in itertools.combinations(c, 2):
                    a = Dv[T[x]] - Dv[T[y]]
                    b = Dv[T[p]] - Dv[T[q]]
                    if not (a - b) % P or not (a + b) % P:
                        sg = -1 if not (a - b) % P else 1
                        self.wa([(w[x][y], 1), (w[p][q], -1)], "equal_chords", (("tdiff", g["id"], T[x], T[y], T[p], T[q], sg),), ("cong", x, y, p, q))
        # perpendicular bisectors
        for (x, y), os_ in self.bis_of.items():
            pr = [o for o in os_ if l(o, x) == l(o, y)]
            for o in pr[1:]:
                self.da([(u[x][y], 1), (u[pr[0]][o], -1)], "perp_bisector", (("cong", pr[0], x, pr[0], y), ("cong", o, x, o, y)), ("perp", x, y, pr[0], o))
        # midpoints
        pm = []
        for m, a, b in self.mids:
            if d(m, a) == d(m, b) and l(m, a) == l(m, b):
                pm.append((m, a, b))
                if (m, a, b) not in self.mid_done:
                    self.mid_done.add((m, a, b))
                    self.wa([(w[a][b], 1), (w[m][a], -1)], "midp_half", (("coll", m, a, b), ("cong", m, a, m, b)), ("half", a, b, m, a))    # the factor 2 is a constant
        mp = lambda m, a, b: (("coll", m, a, b), ("cong", m, a, m, b))
        by_end = {}
        for m, a, b in pm:
            by_end.setdefault(a, []).append((m, b))
            by_end.setdefault(b, []).append((m, a))
        for a, v in by_end.items():
            for (m1, b), (m2, c) in itertools.combinations(v, 2):
                if b != c and m1 != m2:
                    self.da([(u[m1][m2], 1), (u[b][c], -1)], "midline", mp(m1, a, b) + mp(m2, a, c), ("para", m1, m2, b, c))
        same = {}
        for m, a, b in self.mids:
            same.setdefault(m, []).append((a, b))
        for m, a, b in pm:
            for c, e in same[m]:
                if {c, e} == {a, b}:
                    continue
                if (c, e) in [(p, q) for mm, p, q in pm if mm == m]:
                    self.da([(u[a][c], 1), (u[b][e], -1)], "parallelogram", mp(m, a, b) + mp(m, c, e), ("para", a, c, b, e))
                    self.da([(u[a][e], 1), (u[b][c], -1)], "parallelogram", mp(m, a, b) + mp(m, c, e), ("para", a, e, b, c))
                elif d(a, c) == d(b, e) and d(a, e) == d(b, c):
                    prem = mp(m, a, b) + (("para", a, c, b, e), ("para", a, e, b, c))
                    self.da([(u[m][c], 1), (u[m][e], -1)], "parallelogram_mid", prem, ("coll", m, c, m, e))
                    self.wa([(w[m][c], 1), (w[m][e], -1)], "parallelogram_mid", prem, ("cong", m, c, m, e))
            for g in self.eq_at[m]:
                if a in g:
                    for q in g:
                        if q != a and q != b and d(a, q) == d(q, b):    # the median to a right angle
                            self.wa([(w[m][a], 1), (w[m][q], -1)], "right_median", mp(m, a, b) + (("perp", a, q, q, b),), ("cong", m, a, m, q))
            for o in self.bis_of.get((a, b), []):   # a point on the line through the midpoint, perpendicular to the segment
                if o != m and d(o, m) == d(a, b):
                    self.wa([(w[o][a], 1), (w[o][b], -1)], "mid_perp", mp(m, a, b) + (("perp", o, m, a, b),), ("cong", o, a, o, b))
        for m, a, b in self.mids:
            if l(m, a) != l(m, b) and d(m, a) == d(m, b):
                for o in self.bis_of.get((a, b), []):
                    if o != m and l(o, a) == l(o, b) and d(o, m) == d(a, b):
                        self.wa([(w[m][a], 1), (w[m][b], -1)], "chord_mid", (("cong", o, a, o, b), ("coll", m, a, b), ("perp", o, m, a, b)), ("cong", m, a, m, b))
        # similar triangles
        left = []
        self.tick()
        for t in self.sim:
            a, b, c, p, q, r, o = t
            s = -1 if o else 1
            A = not (Dv[u[a][b]] - Dv[u[a][c]] + s * (Dv[u[p][q]] - Dv[u[p][r]])) % P
            B = not (Dv[u[b][a]] - Dv[u[b][c]] + s * (Dv[u[q][p]] - Dv[u[q][r]])) % P
            C = not (Dv[u[c][a]] - Dv[u[c][b]] + s * (Dv[u[r][p]] - Dv[u[r][q]])) % P
            r1, r2, r3 = (l(a, b) - l(p, q)) % P, (l(b, c) - l(q, r)) % P, (l(c, a) - l(r, p)) % P
            if A + B + C >= 2 or (r1 == r2 == r3) or (r1 == r2 and B) or (r2 == r3 and C) or (r1 == r3 and A):
                aa = lambda x, y, z, x2, y2, z2: (("eqangle", x, y, x, z, x2, y2, x2, z2) if o else ("eqangle", x, y, x, z, x2, z2, x2, y2))
                rr = lambda x, y, x2, y2, e, f, e2, f2: ("eqratio", x, y, x2, y2, e, f, e2, f2)
                prem = []
                if A + B + C >= 2:
                    prem = [aa(a, b, c, p, q, r) if A else None, aa(b, a, c, q, p, r) if B else None, aa(c, a, b, r, p, q) if C else None]
                    prem = [x for x in prem if x][:2]
                elif r1 == r2 == r3:
                    prem = [rr(a, b, p, q, b, c, q, r), rr(a, b, p, q, c, a, r, p)]
                elif r1 == r2 and B:
                    prem = [rr(a, b, p, q, b, c, q, r), aa(b, a, c, q, p, r)]
                elif r2 == r3 and C:
                    prem = [rr(b, c, q, r, c, a, r, p), aa(c, a, b, r, p, q)]
                else:
                    prem = [rr(a, b, p, q, c, a, r, p), aa(a, b, c, p, q, r)]
                self.sim_fact("similar", tuple(prem), a, b, c, p, q, r, o)
            else:
                left.append(t)
        self.sim = left
        # the bisector theorem, both ways
        for a, b, c, e in self.bisect:
            if d(e, b) != d(e, c):
                continue
            if not (l(e, b) - l(e, c) - l(a, b) + l(a, c)) % P:
                self.da([(u[a][b], 1), (u[a][e], -2), (u[a][c], 1)], "bisector", (("coll", e, b, c), ("eqratio", e, b, e, c, a, b, a, c)), ("eqangle", a, b, a, e, a, e, a, c))
            elif not (d(a, b) - 2 * d(a, e) + d(a, c)) % P:
                self.wa([(w[e][b], 1), (w[e][c], -1), (w[a][b], -1), (w[a][c], 1)], "bisector", (("coll", e, b, c), ("eqangle", a, b, a, e, a, e, a, c)), ("eqratio", e, b, e, c, a, b, a, c))
        # Thales' converse
        for o, a, c, b, e in self.thales:
            if d(o, a) == d(o, c) and d(o, b) == d(o, e) and not (l(o, a) - l(a, c) - l(o, b) + l(b, e)) % P:
                self.da([(u[a][b], 1), (u[c][e], -1)], "thales", (("coll", o, a, c), ("coll", o, b, e), ("eqratio", o, a, a, c, o, b, b, e)), ("para", a, b, c, e))
        # the trapezoid
        for a, b, c, e, m, k in self.trap:
            if d(a, b) == d(c, e) and d(m, a) == d(m, e) and d(k, b) == d(k, c):
                base = (("para", a, b, c, e), ("coll", m, a, e), ("coll", k, b, c))
                if not (l(m, a) - l(m, e) - l(k, b) + l(k, c)) % P:
                    self.da([(u[m][k], 1), (u[a][b], -1)], "trapezoid", base + (("eqratio", m, a, m, e, k, b, k, c),), ("para", m, k, a, b))
                elif d(m, k) == d(a, b):
                    self.wa([(w[m][a], 1), (w[m][e], -1), (w[k][b], -1), (w[k][c], 1)], "trapezoid", base + (("para", m, k, a, b),), ("eqratio", m, a, m, e, k, b, k, c))
        return self.D.rank + self.W.rank != r0 or len(self.groups) != g0

    def holds(self, name, *a):
        i = [self.ix[x] for x in a]
        Dv, Wv, u, w = self.D.val, self.W.val, self.u, self.w
        if name in ("coll", "collx"):
            return all(Dv[u[i[0]][i[1]]] == Dv[u[i[0]][c]] for c in i[2:])
        if name in ("para", "perp"):
            return Dv[u[i[0]][i[1]]] == Dv[u[i[2]][i[3]]]
        if name == "cong":
            return Wv[w[i[0]][i[1]]] == Wv[w[i[2]][i[3]]]
        if name == "cyclic":
            return any(set(i) <= g["pts"] and g["centre"] is None or set(i) <= g["pts"] and len(i) <= 3 for g in self.groups.values())
        if name == "circle":
            return all(Wv[w[i[0]][i[1]]] == Wv[w[i[0]][c]] for c in i[2:])
        if name == "midp":
            return Dv[u[i[0]][i[1]]] == Dv[u[i[0]][i[2]]] and Wv[w[i[0]][i[1]]] == Wv[w[i[0]][i[2]]]
        if name in ("eqangle", "eqangle6"):
            return not (Dv[u[i[0]][i[1]]] - Dv[u[i[2]][i[3]]] - Dv[u[i[4]][i[5]]] + Dv[u[i[6]][i[7]]]) % P
        if name in ("eqratio", "eqratio6"):
            return not (Wv[w[i[0]][i[1]]] - Wv[w[i[2]][i[3]]] - Wv[w[i[4]][i[5]]] + Wv[w[i[6]][i[7]]]) % P
        return False

    def run(self, goal=None):
        """-> goal fell, rounds"""
        k = 0
        while True:
            if goal and self.holds(*goal):
                return True, k
            if self.deadline and time.time() > self.deadline:
                return False, k
            k += 1
            if not self.round():
                return bool(goal and self.holds(*goal)), k


def numeric_cand(c, P_):
    """a candidate "kind {x} args" -> its coordinates and the facts its construction gives, over names, with x as "_x"; None if degenerate"""
    kind, *a = c.split()
    a = [q for q in a if q not in ("{x}", "aux", "aux0", "aux1", "zaux")]
    x_ = "_x"
    pt = lambda q: np.array(P_[q], float)
    if kind == "midpoint":
        return tuple((pt(a[0]) + pt(a[1])) / 2), [("midp", x_, a[0], a[1])]
    if kind == "mirror":
        return tuple(2 * pt(a[1]) - pt(a[0])), [("midp", a[1], a[0], x_)]
    if kind == "circle":
        A, B, C = pt(a[0]), pt(a[1]), pt(a[2])
        D = 2 * (A[0] * (B[1] - C[1]) + B[0] * (C[1] - A[1]) + C[0] * (A[1] - B[1]))
        if abs(D) < 1e-9:
            return None
        s = lambda p: p @ p
        return (float((s(A) * (B[1] - C[1]) + s(B) * (C[1] - A[1]) + s(C) * (A[1] - B[1])) / D),
                float((s(A) * (C[0] - B[0]) + s(B) * (A[0] - C[0]) + s(C) * (B[0] - A[0])) / D)), [("circle", x_, a[0], a[1], a[2])]
    if kind in ("foot", "reflect"):
        A, B, C = pt(a[0]), pt(a[1]), pt(a[2])
        e = C - B
        if e @ e < 1e-12:
            return None
        F = B + e * (((A - B) @ e) / (e @ e))
        if np.abs(A - F).max() < 1e-7:
            return None
        if kind == "foot":
            return tuple(F), [("coll", x_, a[1], a[2]), ("perp", x_, a[0], a[1], a[2])]
        return tuple(2 * F - A), [("perp", x_, a[0], a[1], a[2]), ("cong", a[1], a[0], a[1], x_), ("cong", a[2], a[0], a[2], x_)]
    if kind == "intersection_ll":
        A, B, C, E = pt(a[0]), pt(a[1]), pt(a[2]), pt(a[3])
        D = (A[0] - B[0]) * (C[1] - E[1]) - (A[1] - B[1]) * (C[0] - E[0])
        if abs(D) < 1e-9:
            return None
        t = ((A[0] - C[0]) * (C[1] - E[1]) - (A[1] - C[1]) * (C[0] - E[0])) / D
        return tuple(A + t * (B - A)), [("coll", x_, a[0], a[1]), ("coll", x_, a[2], a[3])]
    raise ValueError(kind)


def figure(dsl, seed=0):
    """the translation's figure and facts from Newclid's builder -> names, coordinates, facts, goals"""
    from newclid import GeometricSolverBuilder
    from newclid.geometry import Point
    from newclid.predicates import Predicate
    s = GeometricSolverBuilder(seed=seed).load_problem_from_txt(dsl, translate=False).build()
    p = s.proof_state
    pts = list(p.symbols_graph.all_points())
    names = [q.name for q in pts]
    xy = [(float(q.num.x), float(q.num.y)) for q in pts]
    facts = []

    def fact(st):
        a = [x.name if isinstance(x, Point) else None for x in st.args]
        if all(a):
            return (st.predicate.value, *a)
        if st.predicate.value in ("aconst", "rconst", "lconst"):
            return (st.predicate.value, *[x for x in a if x], "_")
        return None
    seen = set()
    for st in [d.statement for d in p._init_added] + [t[0] for t in p._init_to_cache]:
        f = fact(st)
        if f and f not in seen:
            seen.add(f)
            facts.append(f)
    goals = [fact(g) for g in p.goals_as_statements()]
    return names, xy, facts, goals


def build(names, xy, facts, pool=(), timeout=600.0, seed=0):
    N, X, F = list(names), list(xy), []
    for f in facts:
        F.append(f[:-1] if f[-1] == "_" else f)
    for i, (c, q, own) in enumerate(pool):
        nm = f"_x{i}"
        N.append(nm)
        X.append(tuple(q))
        F += [tuple(nm if v == "_x" else v for v in f) for f in own]
    return Closure(N, X, F, deadline=time.time() + timeout, seed=seed)


def close(names, xy, facts, goal, pool=(), timeout=600.0, seed=0):
    """closure of the figure plus the pool. pool: [(candidate, (x, y), its facts)]. -> proved, rounds, seconds, facts about the run"""
    t0 = time.time()
    e = build(names, xy, facts, pool, timeout, seed)
    prep = time.time() - t0
    try:
        ok, k = e.run(goal)
    except TimeoutError:
        ok, k = False, -1
    return ok, k, time.time() - t0, dict(prep=round(prep, 2), n=e.n, rank=(e.D.rank, e.W.rank), sim=len(e.sim)), e


def minimal(n, x, f, goal, pool, timeout):
    """drop candidates while the goal still falls (ddmin); the closure on a few points takes milliseconds"""
    t0, cur, k = time.time(), list(pool), 2
    while len(cur) > 0 and time.time() - t0 < timeout:
        size = max(1, len(cur) // k)
        for i in range(0, len(cur), size):
            t = cur[:i] + cur[i + size:]
            if close(n, x, f, goal, t, timeout)[0]:
                cur, k = t, max(k - 1, 2)
                break
        else:
            if size == 1:
                break
            k = min(k * 2, len(cur))
    return cur


def lform(e, F):
    """a fact as (system, linear form over base variables)"""
    u, w = e.u, e.w
    k, *a = F
    if k == "coll":
        return "D", [(u[a[0]][a[1]], 1), (u[a[0]][a[2]], -1)]
    if k in ("para", "perp"):
        return "D", [(u[a[0]][a[1]], 1), (u[a[2]][a[3]], -1)]
    if k == "eqangle":
        return "D", [(u[a[0]][a[1]], 1), (u[a[2]][a[3]], -1), (u[a[4]][a[5]], -1), (u[a[6]][a[7]], 1)]
    if k == "cong":
        return "W", [(w[a[0]][a[1]], 1), (w[a[2]][a[3]], -1)]
    if k == "eqratio":
        return "W", [(w[a[0]][a[1]], 1), (w[a[2]][a[3]], -1), (w[a[4]][a[5]], -1), (w[a[6]][a[7]], 1)]
    if k == "tdiff":
        return "D", [(a[1], 1), (a[2], -1), (a[3], a[5]), (a[4], -a[5])]
    if k == "midp":
        return None
    raise ValueError(k)


def explain(e, goal):
    """the proof behind the goal, from the log: the rows it rests on, by the exact linear combination behind each premise"""
    Ech = {"D": ({}, []), "W": ({}, [])}   # pivot variable -> (log index, vector, provenance)

    def reduce(sys_, v, t):
        piv = Ech[sys_][0]
        v = {k: c % P for k, c in v.items() if c % P}
        prov = {}
        stack = list(v)
        while stack:
            k = stack.pop()
            c = v.get(k)
            if not c or k not in piv or piv[k][0] >= t:
                continue
            _, r, pr = piv[k]
            for j, q in r.items():
                n = (v.get(j, 0) - c * q) % P
                if n:
                    v[j] = n
                    stack.append(j)
                else:
                    v.pop(j, None)
            for j, q in pr.items():
                prov[j] = (prov.get(j, 0) - c * q) % P
        return v, prov
    for t, (sy, rel, *_x) in enumerate(e.log):
        v = {}
        for k, c in rel:
            v[k] = v.get(k, 0) + c
        v, pr = reduce(sy, v, t)
        pr = {j: q for j, q in pr.items() if q}
        pr[t] = (pr.get(t, 0) + 1) % P
        k = max(v, key=str)
        ic = pow(v[k], P - 2, P)
        Ech[sy][0][k] = (t, {j: q * ic % P for j, q in v.items()}, {j: q * ic % P for j, q in pr.items()})
    used, chases = {}, []

    def need(F, t, ctx):
        k = F[0]
        if k == "cyclic_group":
            for j in e.group_rows.get(F[1], []):
                add(j)
            return
        if k == "cyclic":
            g = next(g for g in e.groups.values() if set(F[1:]) <= g["pts"] and g["centre"] is None)
            for j in e.group_rows.get(g["id"], []):
                add(j)
            return
        if k == "midp":
            forms = [lform(e, ("coll", F[1], F[2], F[3])), lform(e, ("cong", F[1], F[2], F[1], F[3]))]
        elif k == "half":
            forms = [("W", [(e.w[F[1]][F[2]], 1), (e.w[F[3]][F[4]], -1)])]
        else:
            forms = [lform(e, F)]
        for sy, rel in forms:
            v = {}
            for j, c in rel:
                v[j] = v.get(j, 0) + c
            r, prov = reduce(sy, v, t)
            if r:
                raise RuntimeError(f"not in the span: {F} at {t}")
            rows = {j: (-q) % P for j, q in prov.items() if q}
            chases.append((F, t, ctx, rows))
            for j in rows:
                add(j)

    def add(j):
        if j in used:
            return
        used[j] = True
        for F in e.log[j][3]:
            need(F, j, j)
    if goal[0] == "cyclic":
        need(("cyclic", *[e.ix[x] for x in goal[1:]]), len(e.log), -1)
    else:
        need((goal[0], *[e.ix[x] for x in goal[1:]]), len(e.log), -1)
    return sorted(used), chases


def num_fact(F, xy, tol=1e-6):
    """is the fact true on these coordinates (fresh figures)"""
    k, *a = F
    X = np.asarray(xy)

    def vec(p, q):
        return X[q] - X[p]

    def th(p, q):
        v = vec(p, q)
        return math.atan2(v[1], v[0])

    def ln(p, q):
        return float(np.hypot(*vec(p, q)))

    def modpi(x):
        x = x % math.pi
        return min(x, math.pi - x)
    if k == "coll":
        q = list(dict.fromkeys(a))
        return all(modpi(th(q[0], q[1]) - th(q[0], r)) < tol for r in q[2:])
    if k == "para":
        return modpi(th(a[0], a[1]) - th(a[2], a[3])) < tol
    if k == "perp":
        return modpi(th(a[0], a[1]) - th(a[2], a[3]) - math.pi / 2) < tol
    if k == "cong":
        return abs(ln(a[0], a[1]) - ln(a[2], a[3])) < tol * max(ln(a[0], a[1]), 1e-3)
    if k == "half":
        return abs(ln(a[0], a[1]) - 2 * ln(a[2], a[3])) < tol * max(ln(a[0], a[1]), 1e-3)
    if k == "eqangle":
        return modpi(th(a[0], a[1]) - th(a[2], a[3]) - th(a[4], a[5]) + th(a[6], a[7])) < tol
    if k == "eqratio":
        return abs(ln(a[0], a[1]) * ln(a[6], a[7]) - ln(a[2], a[3]) * ln(a[4], a[5])) < tol * max(ln(a[0], a[1]) * ln(a[6], a[7]), 1e-3)
    if k == "cyclic":
        if len(a) < 4:
            return True
        c = circum(X[a[0]], X[a[1]], X[a[2]])
        return c is not None and all(abs(float(np.hypot(*(X[r] - c))) - float(np.hypot(*(X[a[0]] - c)))) < tol for r in a[3:])
    if k == "circle":
        return all(abs(ln(a[0], a[1]) - ln(a[0], r)) < tol * max(ln(a[0], a[1]), 1e-3) for r in a[2:])
    if k in ("simtri", "simtri2"):
        p, q, r, s, t, v = a
        sides = [(ln(p, q), ln(s, t)), (ln(q, r), ln(t, v)), (ln(r, p), ln(v, s))]
        return all(abs(x[0] * sides[0][1] - x[1] * sides[0][0]) < tol * max(x[0] * sides[0][1], 1e-3) for x in sides)
    return True


def circum(A, B, C):
    D = 2 * (A[0] * (B[1] - C[1]) + B[0] * (C[1] - A[1]) + C[0] * (A[1] - B[1]))
    if abs(D) < 1e-9:
        return None
    s = lambda p: p @ p
    return np.array([(s(A) * (B[1] - C[1]) + s(B) * (C[1] - A[1]) + s(C) * (A[1] - B[1])) / D, (s(A) * (C[0] - B[0]) + s(B) * (A[0] - C[0]) + s(C) * (B[0] - A[0])) / D])


def rat(c):
    """a coefficient mod P as a small fraction"""
    for d in range(1, 121):
        n = c * d % P
        if n > P // 2:
            n -= P
        if abs(n) <= 720:
            return f"{n}/{d}" if d > 1 else str(n)
    return "?"


def pretty(e, F):
    k, *a = F
    if k in ("cyclic_group", "tdiff"):
        return k
    return k + " " + " ".join(e.names[x] for x in a if isinstance(x, (int, np.integer)))


def one(row, k, timeout, proofs, fresh=8):
    """the arm on one translation -> a result row"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import geo_translate as GT
    out = {"id": row["id"], "sample": row.get("sample", 0), "dsl": row["dsl"], "k": k, "proved": False}
    t0 = time.time()
    n, x, f, g = figure(row["dsl"])
    P_ = dict(zip(n, x))
    cand = []
    if k:
        for c, _ in GT.aux_candidates(row["dsl"], k):
            q = numeric_cand(c, P_)
            if q is not None and all(math.isfinite(v) and abs(v) < 1e4 for v in q[0]) and not any(math.dist(q[0], v) < 1e-6 for v in x) \
                    and not any(math.dist(q[0], cc[1]) < 1e-6 for cc in cand):
                cand.append((c, q[0], q[1]))
    out["cands"] = len(cand)
    try:
        ok, rounds, sec, info, e = close(n, x, f, g[0], cand, timeout)
    except TimeoutError:
        out.update(rounds=-1, sec=round(time.time() - t0, 2), timeout=True)
        return out
    out.update(proved=ok, rounds=rounds, sec=round(sec, 2), info={k_: v for k_, v in info.items()}, timeout=rounds < 0)
    if not ok:
        return out
    rows, chases = explain(e, g[0])
    pts = set()
    for j in rows:
        for F in (e.log[j][4],) + tuple(e.log[j][3]):
            pts |= {v for v in F[1:] if isinstance(v, (int, np.integer)) and F[0] not in ("tdiff", "cyclic_group")}
    needed = [cand[int(e.names[v][2:])] for v in sorted(pts) if e.names[v].startswith("_x")]
    out["points_first"] = len(needed)
    if needed:      # the proof again on the smallest set of points found, which is the one read and certified
        needed = minimal(n, x, f, g[0], needed, timeout)
        cand = needed
        ok2, _, _, _, e = close(n, x, f, g[0], cand, timeout)
        rows, chases = explain(e, g[0])
        pts = set()
        for j in rows:
            for F in (e.log[j][4],) + tuple(e.log[j][3]):
                pts |= {v for v in F[1:] if isinstance(v, (int, np.integer)) and F[0] not in ("tdiff", "cyclic_group")}
    needed = sorted(c[0] for c in needed)
    denom = sum(1 for F, t, ctx, r in chases if any("/" in rat(c) for c in r.values()))
    tags = {}
    for j in rows:
        tags[e.log[j][2]] = tags.get(e.log[j][2], 0) + 1
    out.update(points=needed, steps=len(rows), chases=len(chases), fractional_chases=denom, rules=tags)
    # each step's conclusion and premises on fresh figures of the translation, with the points it needs
    facts = [e.log[j][4] for j in rows] + [F for j in rows for F in e.log[j][3] if F[0] not in ("tdiff", "cyclic_group")]
    held, tried = 0, 0
    false_ = {}
    for sd in range(1, fresh + 1):
        try:
            n2, x2, _, _ = figure(row["dsl"], seed=sd)
        except Exception:
            continue
        P2 = dict(zip(n2, x2))
        C2 = dict(P2)
        bad = False
        for i, (c, _, _) in enumerate(cand):
            q = numeric_cand(c, P2)
            if q is None:
                bad = bad or f"_x{i}" in [e.names[v] for v in pts]
                C2[f"_x{i}"] = (0.0, 0.0)
            else:
                C2[f"_x{i}"] = q[0]
        if bad or set(C2) != set(e.names):
            continue
        tried += 1
        XY = [C2[v] for v in e.names]
        wrong = [F for F in facts if F[0] not in ("given_", "const") and not num_fact(F, XY)]
        if not wrong:
            held += 1
        for F in wrong[:5]:
            false_[pretty(e, F)] = false_.get(pretty(e, F), 0) + 1
    out.update(fresh=tried, fresh_held=held, fresh_false=false_)
    if proofs:
        os.makedirs(proofs, exist_ok=True)
        with open(os.path.join(proofs, f"{row.get('tag', 'x')}_{row['id']}_{row.get('sample', 0)}_k{k}.txt"), "w") as fh:
            fh.write(row["dsl"] + "\n")
            for i, (c, _, _) in enumerate(cand):
                if f"_x{i}" in [e.names[v] for v in pts]:
                    fh.write(f"_x{i} = {c}\n")
            by = {}
            for F, t, ctx, r in chases:
                by.setdefault(ctx, []).append((F, r))
            for j in rows:
                sy, rel, tag, prem, concl = e.log[j]
                fh.write(f"[{j}] {tag}: " + ", ".join(pretty(e, F) for F in prem) + " => " + pretty(e, concl) + "\n")
                for F, r in by.get(j, []):
                    fh.write(f"      {pretty(e, F)} = " + " + ".join(f"{rat(c)}*[{i}]" for i, c in sorted(r.items())) + "\n")
            for F, r in by.get(-1, []):
                fh.write(f"GOAL {pretty(e, F)} = " + " + ".join(f"{rat(c)}*[{i}]" for i, c in sorted(r.items())) + "\n")
    return out


def main():
    cmd = sys.argv[1]
    arg = lambda n, d: type(d)(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d
    if cmd == "one":
        r = json.loads(sys.argv[2])
        print(json.dumps(one(r, arg("--k", 0), arg("--timeout", 600.0), arg("--proofs", "")), default=str))
        return
    from concurrent.futures import ThreadPoolExecutor, as_completed
    R = [json.loads(l) for l in open(sys.argv[2])]
    k, timeout, workers, proofs = arg("--k", 0), arg("--timeout", 600.0), arg("--workers", 16), arg("--proofs", "")

    def run(r):
        try:
            p = subprocess.run([sys.executable, os.path.abspath(__file__), "one", json.dumps(r), "--k", str(k), "--timeout", str(timeout), "--proofs", proofs],
                               capture_output=True, text=True, timeout=timeout * 2 + 1800)
            return json.loads(p.stdout.strip().splitlines()[-1])
        except Exception as e:
            return {"id": r["id"], "sample": r.get("sample", 0), "dsl": r["dsl"], "k": k, "proved": False, "err": type(e).__name__, "stderr": (getattr(e, "stderr", "") or "")[-300:]}
    with ThreadPoolExecutor(workers) as ex, open(sys.argv[3], "w") as f:
        for fu in as_completed([ex.submit(run, r) for r in R]):
            f.write(json.dumps(fu.result()) + "\n")
            f.flush()


if __name__ == "__main__":
    main()
