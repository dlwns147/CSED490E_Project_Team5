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
K = 0: the translation alone; K > 0: K candidates (geo_translate.aux_candidates, seed 0) all at once; K < 0: SIDE-GT-SAT, -K candidates a round, the one that adds most relations becomes a point.
GT_STRICT=1: angle chases in integers only (ZSpan)."""
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


class ZSpan:
    """The angle relations as an exact integer lattice (GT_STRICT): directed angles live modulo pi, where 2a = 2b does not give a = b, so a chase may
    only use integer combinations. Variables are eliminated on a coefficient of 1 or -1; what is left (multiples like 2(a - b) = 0) stays in an
    integer echelon form, so a member is exactly an integer combination of the relations added. With track, each answer carries that combination."""

    def __init__(self, track=False):
        self.expr, self.users, self.ech, self.track, self.prov = {}, {}, {}, track, {}

    def _reduce(self, rel):
        e, pr = {}, {}
        for v, c in rel:
            for f, q in self.expr.get(v, {v: 1}).items():
                e[f] = e.get(f, 0) + c * q
            if self.track:
                for j, q in self.prov.get(v, {}).items():
                    pr[j] = pr.get(j, 0) + c * q
        return {f: q for f, q in e.items() if q}, pr

    def _echelon(self, e, pr):
        """reduce by the echelon form as far as it goes -> what is left, its combination"""
        out = {}
        while e:
            k = max(e)
            row = self.ech.get(k)
            if row is None or e[k] % row[0][k]:
                out[k] = e.pop(k)
                continue
            m = e[k] // row[0][k]
            for f, q in row[0].items():
                n = e.get(f, 0) - m * q
                if n:
                    e[f] = n
                else:
                    e.pop(f, None)
            if self.track:
                for j, q in row[1].items():
                    pr[j] = pr.get(j, 0) + m * q
        return out, pr

    def comb(self, rel):
        """the integer combination of added relations that gives rel, or None if it is not a member"""
        e, pr = self._reduce(rel)
        e, pr = self._echelon(e, pr)
        return None if e else pr

    def member(self, rel):
        return self.comb(rel) is not None

    def _insert(self, e, pr):
        """e into the echelon form, by Euclid on the leading variable. -> changed"""
        new = False
        while e:
            k = max(e)
            row = self.ech.get(k)
            if row is None:
                self.ech[k] = (e, pr)
                return True
            a, b = row[0][k], e[k]
            if not b % a:
                m = b // a
                e = {f: e.get(f, 0) - m * row[0].get(f, 0) for f in set(e) | set(row[0])}
                pr = {j: pr.get(j, 0) - m * row[1].get(j, 0) for j in set(pr) | set(row[1])}
                e = {f: q for f, q in e.items() if q}
                continue
            new = True
            m = a // b      # the pivot row becomes the remainder, and the two swap
            ne = {f: row[0].get(f, 0) - m * e.get(f, 0) for f in set(e) | set(row[0])}
            np_ = {j: row[1].get(j, 0) - m * pr.get(j, 0) for j in set(pr) | set(row[1])}
            self.ech[k] = (e, pr)
            e, pr = {f: q for f, q in ne.items() if q}, np_
        return new

    def add(self, rel, j=None):
        """-> True if the lattice grew"""
        e, pr = self._reduce(rel)
        pr = {i: -q for i, q in pr.items()}     # e = rel - (the combination so far)
        if self.track:
            pr[j] = pr.get(j, 0) + 1
        out, red = self._echelon(dict(e), {i: -q for i, q in pr.items()})
        red = {i: -q for i, q in red.items()}
        if not out:
            return False
        e, pr = out, red
        units = [f for f, q in e.items() if abs(q) == 1]
        if not units or math.gcd(*e.values()) > 1:
            return self._insert(e, pr)
        w = min(units, key=lambda f: len(self.users.get(f, ())))
        s = e.pop(w)
        sol = {f: -s * q for f, q in e.items()}     # w = sum(q * f)
        us = self.users.pop(w, set()) | {w}
        for v in us:
            ex = self.expr.get(v) or {v: 1}
            self.expr[v] = ex
            cv = ex.pop(w)
            for f, q in sol.items():
                n = ex.get(f, 0) + cv * q
                if n:
                    ex[f] = n
                    self.users.setdefault(f, set()).add(v)
                else:
                    ex.pop(f, None)
                    self.users.get(f, set()).discard(v)
            if self.track:
                d = self.prov.setdefault(v, {})
                for i, q in pr.items():
                    d[i] = d.get(i, 0) + cv * s * q
        if any(w in r[0] for r in self.ech.values()):       # the echelon form is rewritten without w
            rows, self.ech = list(self.ech.values()), {}
            for r, rp in rows:
                x, y = {}, dict(rp)
                for f, q in r.items():
                    if f == w:
                        for g, h in sol.items():
                            x[g] = x.get(g, 0) + q * h
                        if self.track:
                            for i, h in pr.items():
                                y[i] = y.get(i, 0) - q * s * h
                    else:
                        x[f] = x.get(f, 0) + q
                x = {f: q for f, q in x.items() if q}
                self._insert(x, y)
        return True


class Closure:
    def __init__(self, names, xy, facts, deadline=None, seed=0, log=True):
        self.names, self.n = list(names), len(names)
        self.log = [] if log else None
        self.ix = {a: i for i, a in enumerate(self.names)}
        self.xy = np.array(xy, float)
        self.deadline = deadline
        self.D, self.W = Lin(seed), Lin(seed + 1)
        self.Z = ZSpan() if os.environ.get("GT_STRICT") else None
        self.zver, self.zseen, self.zfail = 0, set(), {}
        self.Q = Lin(seed + 2) if os.environ.get("GT_SQ") else None     # squared lengths, a third linear system (SIDE-GT-SQ)
        n = self.n
        if self.Q is not None:
            self.s = [[None] * n for _ in range(n)]
            self.q_mid = set()
            for a, b in itertools.combinations(range(n), 2):
                self.s[a][b] = self.s[b][a] = self.Q.var(("s", a, b))
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
        if self.Q is not None:
            self.sq_prep()
        for f in facts:
            self.ingest(*f)

    def da(self, rel, tag, prem, concl):
        """an angle relation, with the rule, its premises and its conclusion (facts over point numbers), kept in the log if it was new"""
        if self.Z is not None:
            key = tuple(sorted(rel))
            if key in self.zseen or not self.zok(prem):
                return False
            self.zseen.add(key)
            new = self.D.add(rel)
            znew = self.Z.add(rel)
            self.zver += znew
            new = new or znew
        else:
            new = self.D.add(rel)
        if new and self.log is not None:
            self.log.append(("D", rel, tag, prem, concl))
            if self.cur_group is not None:
                self.group_rows.setdefault(self.cur_group, []).append(len(self.log) - 1)
        return new

    def zok(self, prem):
        """under GT_STRICT: every angle premise is an exact member of the integer lattice"""
        if self.Z is None or not prem:
            return True
        if self.zfail.get(prem) == self.zver:
            return False
        for F in prem:
            if F[0] in ("cyclic_group", "cyclic", "half"):
                continue
            sy, rel = lform(self, ("coll", F[1], F[2], F[3]) if F[0] == "midp" else F)
            if sy == "D" and not self.Z.member(rel):
                self.zfail[prem] = self.zver
                return False
        return True

    def wa(self, rel, tag, prem, concl):
        if not self.zok(prem):
            return False
        new = self.W.add(rel)
        if new and self.log is not None:
            self.log.append(("W", rel, tag, prem, concl))
        return new

    def qa(self, rel, tag, prem, concl):
        """a relation among squared lengths: an identity of the plane, so nothing comes from the figure"""
        if not self.zok(prem):
            return False
        new = self.Q.add(rel)
        if new and self.log is not None:
            self.log.append(("Q", rel, tag, prem, concl))
        return new

    def sq_prep(self):
        """numerically true instances: perpendicular pairs of point pairs on two lines, and equal lengths"""
        L, ids = self.L, list(self.lines)
        self.q_perp, self.q_eq = [], []
        if ids:
            A = np.array([self.lines[i][0] for i in ids])
            B = np.array([self.lines[i][1] for i in ids])
            vx, vy = self.dx[B, A] / L[A, B], self.dy[B, A] / L[A, B]
            near = np.abs(np.outer(vx, vx) + np.outer(vy, vy)) <= TOL
            for i, j in zip(*np.nonzero(np.triu(near, 1))):
                for (a, b), (c, e) in itertools.product(itertools.combinations(self.lines[ids[i]], 2), itertools.combinations(self.lines[ids[j]], 2)):
                    self.q_perp.append((a, b, c, e))
        by = {}
        for a, b in itertools.combinations(range(self.n), 2):
            if L[a, b] > 1e-9:
                by.setdefault(round(L[a, b] * 1e6), []).append((a, b))
        for g in by.values():
            self.q_eq += [(a, b, c, e) for (a, b), (c, e) in itertools.combinations(g, 2)]

    def sq_round(self, pm):
        """cong and perp, in and out, and the median identity at proved midpoints"""
        u, w, s = self.u, self.w, self.s
        Dv, Wv, Qv = self.D.val, self.W.val, self.Q.val
        for a, b, c, e in self.q_perp:
            F = ("sqperp", a, b, c, e)
            if Dv[u[a][b]] == Dv[u[c][e]]:
                if self.zok((("perp", a, b, c, e),)):
                    self.qa(lform(self, F)[1], "pyth", (("perp", a, b, c, e),), F)
            elif not sum(k * Qv[v] for v, k in lform(self, F)[1]) % P:
                self.da([(u[a][b], 1), (u[c][e], -1)], "pyth", (F,), ("perp", a, b, c, e))
        for a, b, c, e in self.q_eq:
            F = ("sqcong", a, b, c, e)
            if Wv[w[a][b]] == Wv[w[c][e]]:
                self.qa(lform(self, F)[1], "sq_cong", (("cong", a, b, c, e),), F)
            elif Qv[s[a][b]] == Qv[s[c][e]]:
                self.wa([(w[a][b], 1), (w[c][e], -1)], "sq_cong", (F,), ("cong", a, b, c, e))
        for m, a, b in pm:
            if (m, a, b) in self.q_mid:
                continue
            self.q_mid.add((m, a, b))
            prem = (("coll", m, a, b), ("cong", m, a, m, b))
            self.qa([(s[a][b], 1), (s[m][a], -4)], "median", prem, ("sqmid", m, a, b))
            for x in range(self.n):
                if x not in (m, a, b):
                    self.qa([(s[x][m], 2), (s[m][a], 2), (s[x][a], -1), (s[x][b], -1)], "median", prem, ("sqmedian", x, m, a, b))

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
        g0, z0 = len(self.groups), self.zver

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
                    if ang(x, e, f, y, e, f) and self.zok((("eqangle", x, e, x, f, y, e, y, f),)):
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
        if self.Q is not None:
            q0 = self.Q.rank
            self.sq_round(pm)
            return self.D.rank + self.W.rank != r0 or len(self.groups) != g0 or self.zver != z0 or self.Q.rank != q0
        return self.D.rank + self.W.rank != r0 or len(self.groups) != g0 or self.zver != z0

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

    def zgoal(self, goal):
        if self.Z is None or goal[0] in ("cyclic", "cong", "eqratio", "circle", "eqratio6"):
            return True
        k, *a = goal
        i = [self.ix[x] for x in a]
        if k in ("coll", "collx"):
            return all(self.Z.member(lform(self, ("coll", i[0], i[1], c))[1]) for c in i[2:])
        return self.Z.member(lform(self, ("coll", i[0], i[1], i[2]) if k == "midp" else ("eqangle" if k == "eqangle6" else k, *i))[1])

    def run(self, goal=None):
        """-> goal fell, rounds"""
        k = 0
        while True:
            if goal and self.holds(*goal) and self.zgoal(goal):
                return True, k
            if self.deadline and time.time() > self.deadline:
                return False, k
            k += 1
            if not self.round():
                return bool(goal and self.holds(*goal) and self.zgoal(goal)), k


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
    if kind == "second_lc":     # the line through p and q meets the circle through p, b, c again
        A, B, C, E = pt(a[0]), pt(a[1]), pt(a[2]), pt(a[3])
        o = circum(A, C, E)
        v = B - A
        if o is None or v @ v < 1e-12:
            return None
        return tuple(A + v * (2 * ((o - A) @ v) / (v @ v))), [("coll", x_, a[0], a[1]), ("cyclic", x_, a[0], a[2], a[3])]
    if kind == "second_cc":     # the circles through p, a, b and p, c, d meet again
        A, B, C, E, G = pt(a[0]), pt(a[1]), pt(a[2]), pt(a[3]), pt(a[4])
        o1, o2 = circum(A, B, C), circum(A, E, G)
        if o1 is None or o2 is None or (o2 - o1) @ (o2 - o1) < 1e-12:
            return None
        F = o1 + (o2 - o1) * (((A - o1) @ (o2 - o1)) / ((o2 - o1) @ (o2 - o1)))
        return tuple(2 * F - A), [("cyclic", x_, a[0], a[1], a[2]), ("cyclic", x_, a[0], a[3], a[4])]
    raise ValueError(kind)


def figure(dsl, seed=0):
    """the translation's figure and facts from Newclid's builder (or geo_decl for a statement with no construction) -> names, coordinates, facts, goals"""
    if dsl.startswith("decl:"):
        import geo_decl
        return geo_decl.figure(dsl, seed)
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
    if k == "sqperp":
        rel = {}
        for x, y, c in ((a[0], a[2], 1), (a[0], a[3], -1), (a[1], a[2], -1), (a[1], a[3], 1)):
            if x != y:
                rel[e.s[x][y]] = rel.get(e.s[x][y], 0) + c
        return "Q", [(v, c) for v, c in rel.items() if c]
    if k == "sqcong":
        return "Q", [(e.s[a[0]][a[1]], 1), (e.s[a[2]][a[3]], -1)]
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
    Ech = {"D": ({}, []), "W": ({}, []), "Q": ({}, [])}   # pivot variable -> (log index, vector, provenance)

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
    zans = {}
    if e.Z is not None:     # the exact integer combination behind every angle premise, by replaying the log
        Z = ZSpan(track=True)

        def zq(F, t):
            forms = [lform(e, ("coll", F[1], F[2], F[3]))] if F[0] == "midp" else [] if F[0] in ("cyclic_group", "cyclic", "half") else [lform(e, F)]
            for sy, rel in forms:
                if sy == "D":
                    zans[(t, tuple(sorted(rel)))] = Z.comb(rel)
        gF = ("coll", e.ix[goal[1]], e.ix[goal[2]], e.ix[goal[3]]) if goal[0] in ("coll", "midp") else None if goal[0] == "cyclic" else ("eqangle" if goal[0] == "eqangle6" else goal[0], *[e.ix[x] for x in goal[1:]])
        for t, (sy, rel, _tag, prem, _c) in enumerate(e.log):
            for F in prem:
                zq(F, t)
            if sy == "D":
                Z.add(rel, t)
        if gF is not None:
            zq(gF, len(e.log))
    for t, (sy, rel, *_x) in enumerate(e.log):
        if e.Z is not None and sy == "D":
            continue
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
            if e.Z is not None and sy == "D":
                pr_ = zans.get((t, tuple(sorted(rel))))
                if pr_ is None:
                    raise RuntimeError(f"not in the lattice: {F} at {t}")
                rows = {j: q % P for j, q in pr_.items() if q}
            else:
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
    if k == "sqperp":
        return abs(float(vec(a[0], a[1]) @ vec(a[2], a[3]))) < tol * max(ln(a[0], a[1]) * ln(a[2], a[3]), 1e-3)
    if k == "sqcong":
        return abs(ln(a[0], a[1]) - ln(a[2], a[3])) < tol * max(ln(a[0], a[1]), 1e-3)
    if k == "sqmid":
        return abs(ln(a[1], a[2]) - 2 * ln(a[0], a[1])) < tol * max(ln(a[1], a[2]), 1e-3)
    if k == "sqmedian":
        return abs(2 * ln(a[0], a[1]) ** 2 + 2 * ln(a[1], a[2]) ** 2 - ln(a[0], a[2]) ** 2 - ln(a[0], a[3]) ** 2) < tol * max(ln(a[0], a[2]) ** 2, 1e-3)
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


def relations(e, m):
    """how many independent relations hold among the direction and log-length variables of the first m points"""
    out = 0
    for lin, tab in ((e.D, e.u), (e.W, e.w)) + (((e.Q, e.s),) if e.Q is not None else ()):
        piv, n, rank = {}, 0, 0
        for a, b in itertools.combinations(range(m), 2):
            n += 1
            v = dict(lin.expr[tab[a][b]])
            while v:
                k = max(v)
                if k not in piv:
                    ic = pow(v[k], P - 2, P)
                    piv[k] = {f: q * ic % P for f, q in v.items()}
                    rank += 1
                    break
                c = v[k]
                for f, q in piv[k].items():
                    w = (v.get(f, 0) - c * q) % P
                    if w:
                        v[f] = w
                    else:
                        v.pop(f, None)
        out += n - rank
    return out


def luby(j):
    """the j-th term of Luby, Sinclair and Zuckerman's universal restart sequence: 1, 1, 2, 1, 1, 2, 4, ..."""
    k = 1
    while (1 << k) - 1 < j:
        k += 1
    return 1 << (k - 1) if (1 << k) - 1 == j else luby(j - (1 << (k - 1)) + 1)


def one_sat(row, budget, timeout, proofs, fresh=8):
    """SIDE-GT-SAT: greedy on the relations a point adds. In a round, each of -k one-step candidates over the current points gets a closure with the current facts, and its gain is the
    relations among the current points and it, less those of the two closures apart. The best becomes a point. Rank is submodular on linear relations, so this is the
    greedy algorithm for a monotone submodular objective (Nemhauser, Wolsey, Fisher 1978) when the other rules add nothing. -> a result row"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import geo_translate as GT
    out = {"id": row["id"], "sample": row.get("sample", 0), "dsl": row["dsl"], "k": -budget, "proved": False}
    t0 = time.time()
    end = t0 + timeout
    n, x, f, g = figure(row["dsl"])
    defs, kept_by_round, ok, tried, runs = [], [], False, 0, 0
    lub = bool(os.environ.get("GT_LUBY"))    # restarts: a run stops after luby(j) * budget candidates, and the next uses a fresh sample
    two0 = None     # a second figure: a relation true by accident on one figure gains nothing on the other
    if os.environ.get("GT_TWOFIG"):
        for sd in range(1, 9):
            try:
                n2, x2, f2, _ = figure(row["dsl"], seed=sd)
            except Exception:
                continue
            if set(n2) == set(n):
                two0 = [list(n2), [tuple(q) for q in x2], [q[:-1] if q[-1] == "_" else q for q in f2]]
                break
    try:
      while True:
        runs += 1
        cap = luby(runs) * budget if lub else None
        N, X, F = list(n), [tuple(q) for q in x], [q[:-1] if q[-1] == "_" else q for q in f]
        defs, kept_by_round, ok, used = [], [], False, 0
        two = [list(two0[0]), list(two0[1]), list(two0[2])] if two0 else None
        for rnd in range(1000):
            e = Closure(N, X, F, deadline=end, log=False)
            ok, _ = e.run(g[0])
            if ok:
                break
            r0 = relations(e, len(N))
            if two:
                e_b = Closure(two[0], two[1], two[2], deadline=end, log=False)
                e_b.run(None)
                r0b = relations(e_b, len(two[0]))
            best, fell = None, False
            for c, _ in GT.aux_candidates(f"{' '.join(N)} = free ? {g[0][0]}", budget, seed=rnd + 1000 * (runs - 1)):
                if cap and used >= cap:
                    break
                q = numeric_cand(c, dict(zip(N, X)))
                if q is None or not all(math.isfinite(v) and abs(v) < 1e4 for v in q[0]) or any(math.dist(q[0], v) < 1e-6 for v in X):
                    continue
                tried += 1
                used += 1
                alone = Closure(N + ["_x"], X + [tuple(q[0])], list(q[1]), deadline=end, log=False)
                alone.run(None)
                e2 = Closure(N + ["_x"], X + [tuple(q[0])], F + list(q[1]), deadline=end, log=False)
                fell, _ = e2.run(g[0])
                gain = relations(e2, len(N) + 1) - r0 - relations(alone, len(N) + 1)
                qb = None
                if two and (fell or best is None or gain > best[0]):
                    qb = numeric_cand(c, dict(zip(two[0], two[1])))
                    if qb is None or not all(math.isfinite(v) and abs(v) < 1e4 for v in qb[0]) or any(math.dist(qb[0], v) < 1e-6 for v in two[1]):
                        fell = False
                        continue
                    alone_b = Closure(two[0] + ["_x"], two[1] + [tuple(qb[0])], list(qb[1]), deadline=end, log=False)
                    alone_b.run(None)
                    e2b = Closure(two[0] + ["_x"], two[1] + [tuple(qb[0])], two[2] + list(qb[1]), deadline=end, log=False)
                    fell_b, _ = e2b.run(g[0])
                    fell = fell and fell_b
                    gain = min(gain, relations(e2b, len(two[0]) + 1) - r0b - relations(alone_b, len(two[0]) + 1))
                if fell or best is None or gain > best[0]:
                    best = (gain, c, tuple(q[0]), q[1], qb)
                if fell:
                    break
            if best is None or (best[0] <= 0 and not fell) or (cap and used >= cap and not fell):
                break
            kept_by_round.append(best[0])
            nm = f"_x{len(defs)}"
            defs.append((nm, best[1]))
            N.append(nm)
            X.append(best[2])
            F += [tuple(nm if v == "_x" else v for v in h) for h in best[3]]
            if two:
                two[0].append(nm)
                two[1].append(tuple(best[4][0]))
                two[2] += [tuple(nm if v == "_x" else v for v in h) for h in best[4][1]]
        if ok or not lub or time.time() > end:
            break
    except TimeoutError:
        pass
    out.update(kept=kept_by_round, tried=tried, runs=runs, sec=round(time.time() - t0, 2), timeout=time.time() > end)
    if not ok:
        return out
    # the proof, then only the points it needs and their parents
    e = Closure(N, X, F, deadline=time.time() + timeout)
    e.run(g[0])
    rows, chases = explain(e, g[0])
    pts = {e.names[v] for j in rows for H in (e.log[j][4],) + tuple(e.log[j][3]) for v in H[1:] if isinstance(v, (int, np.integer)) and H[0] not in ("tdiff", "cyclic_group")}
    dep = dict(defs)
    need = set()
    stack = [q for q in pts if q in dep]
    while stack:
        q = stack.pop()
        if q not in need:
            need.add(q)
            stack += [a for a in dep[q].split()[1:] if a in dep]
    kept = [(nm, c) for nm, c in defs if nm in need]
    N2, X2, F2 = list(n), [tuple(q) for q in x], [q[:-1] if q[-1] == "_" else q for q in f]
    for nm, c in kept:
        q = numeric_cand(c, dict(zip(N2, X2)))
        N2.append(nm)
        X2.append(tuple(q[0]))
        F2 += [tuple(nm if v == "_x" else v for v in h) for h in q[1]]
    e = Closure(N2, X2, F2, deadline=time.time() + timeout)
    fell, _ = e.run(g[0])
    if fell:        # it can fail when a dropped point's facts mattered only through the span; then the full list stands
        defs_, rows, chases = kept, *explain(e, g[0])
    else:
        e = Closure(N, X, F, deadline=time.time() + timeout)
        e.run(g[0])
        defs_ = defs
        rows, chases = explain(e, g[0])
    out.update(proved=True, sec=round(time.time() - t0, 2), points=[c for _, c in defs_], steps=len(rows), chases=len(chases),
               fractional_angle=sum(1 for H, t, ctx, r in chases if H[0] not in ("cong", "eqratio", "half", "sqperp", "sqcong") and any("/" in rat(c) for c in r.values()) and not (H[0] == "midp" and e.log[next(iter(r))][0] == "W")),
               rules={tg: sum(1 for j in rows if e.log[j][2] == tg) for tg in {e.log[j][2] for j in rows}})
    facts = [e.log[j][4] for j in rows] + [H for j in rows for H in e.log[j][3] if H[0] not in ("tdiff", "cyclic_group")]
    tried_f, held, false_ = 0, 0, {}
    for sd in range(1, fresh + 1):
        try:
            n3, x3, _, _ = figure(row["dsl"], seed=sd)
        except Exception:
            continue
        C = dict(zip(n3, x3))
        bad = set(C) != set(n)
        for nm, c in defs_:
            q = None if bad else numeric_cand(c, C)
            if q is None:
                bad = True
                break
            C[nm] = q[0]
        if bad:
            continue
        tried_f += 1
        XY = [C[v] for v in e.names]
        wrong = [H for H in facts if H[0] not in ("given_", "const") and not num_fact(H, XY)]
        held += not wrong
        for H in wrong[:5]:
            false_[pretty(e, H)] = false_.get(pretty(e, H), 0) + 1
    out.update(fresh=tried_f, fresh_held=held, fresh_false=false_)
    if proofs:
        os.makedirs(proofs, exist_ok=True)
        with open(os.path.join(proofs, f"{row.get('tag', 'x')}_{row['id']}_{row.get('sample', 0)}_sat.txt"), "w") as fh:
            fh.write(row["dsl"] + "\n")
            for nm, c in defs_:
                fh.write(f"{nm} = {c}\n")
            by = {}
            for H, t, ctx, r in chases:
                by.setdefault(ctx, []).append((H, r))
            for j in rows:
                sy, rel, tag, prem, concl = e.log[j]
                fh.write(f"[{j}] {tag}: " + ", ".join(pretty(e, H) for H in prem) + " => " + pretty(e, concl) + "\n")
                for H, r in by.get(j, []):
                    fh.write(f"      {pretty(e, H)} = " + " + ".join(f"{rat(c)}*[{i}]" for i, c in sorted(r.items())) + "\n")
            for H, r in by.get(-1, []):
                fh.write(f"GOAL {pretty(e, H)} = " + " + ".join(f"{rat(c)}*[{i}]" for i, c in sorted(r.items())) + "\n")
    return out


def one(row, k, timeout, proofs, fresh=8):
    """the arm on one translation -> a result row; k < 0: SIDE-GT-SAT with a budget of -k candidates a round"""
    if k < 0:
        return one_sat(row, -k, timeout, proofs, fresh)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import geo_translate as GT
    out = {"id": row["id"], "sample": row.get("sample", 0), "dsl": row["dsl"], "k": k, "proved": False}
    t0 = time.time()
    n, x, f, g = figure(row["dsl"])
    P_ = dict(zip(n, x))
    cand = []
    if k:
        for c, _ in GT.aux_candidates(f"{' '.join(n)} = free ? {g[0][0]}" if row["dsl"].startswith("decl:") else row["dsl"], k):
            q = numeric_cand(c, P_)
            if q is not None and all(math.isfinite(v) and abs(v) < 1e4 for v in q[0]) and not any(math.dist(q[0], v) < 1e-6 for v in x) \
                    and not any(math.dist(q[0], cc[1]) < 1e-6 for cc in cand):
                cand.append((c, q[0], q[1]))
    out["cands"] = len(cand)
    gi = [n.index(v) for v in g[0][1:]]
    if not num_fact((g[0][0], *gi), x):     # the engine drops constants and relies on the goal being true on the figure
        out.update(rounds=0, sec=round(time.time() - t0, 2), goal_false=True)
        return out
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
    denom_a = sum(1 for F, t, ctx, r in chases if F[0] not in ("cong", "eqratio", "half") and any("/" in rat(c) for c in r.values()) and not (F[0] == "midp" and e.log[next(iter(r))][0] == "W"))
    tags = {}
    for j in rows:
        tags[e.log[j][2]] = tags.get(e.log[j][2], 0) + 1
    out.update(points=needed, steps=len(rows), chases=len(chases), fractional_chases=denom, fractional_angle=denom_a, torsion=len(e.Z.ech) if e.Z is not None else None, rules=tags)
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


def lemma_of(c):
    """a conclusion in a proof file as Newclid statements"""
    k, *a = c.split()
    if k in ("given", "const") or k == "half" and len(a) != 4:
        return []
    if k == "half":
        return [f"midp {a[2]} {a[0]} {a[1]}"]
    if k == "coll":
        q = list(dict.fromkeys(a))
        return [" ".join(["coll"] + q)] if len(q) >= 3 else []
    if k == "cyclic":
        return [c] if len(a) >= 4 else []
    if k == "circle":
        return [f"cong {a[0]} {a[1]} {a[0]} {x}" for x in a[2:]]
    if k in ("simtri", "simtri2"):      # what a similar pair adds to the spans; Newclid cannot take simtri as a goal or a lemma here
        x, y, z, p, q, r = a
        ang = [f"eqangle {x} {y} {x} {z} {p} {q} {p} {r}", f"eqangle {y} {x} {y} {z} {q} {p} {q} {r}"] if k == "simtri" else [f"eqangle {x} {y} {x} {z} {p} {r} {p} {q}", f"eqangle {y} {x} {y} {z} {q} {r} {q} {p}"]
        return ang + [f"eqratio {x} {y} {p} {q} {y} {z} {q} {r}", f"eqratio {x} {y} {p} {q} {z} {x} {r} {p}"]
    return [c]


def certify_file(path, timeout):
    """replay a proof file in Newclid, one conclusion at a time: DDAR gets the translation, the proof's points and only the conclusions that this
    step's premises were chased from, as lemmas, and has to reach the step's conclusion. So the rules and the arithmetic are checked by another engine."""
    import re, tempfile
    L = open(path).read().split("\n")
    pre, goal = L[0].split(" ? ")
    defs, steps, cur = {}, {}, None
    rows, goals = {}, []
    for ln in L[1:]:
        m = re.match(r"_x(\d+) = (\S+) aux (.*)", ln)
        if m:
            defs[m[1]] = f"{m[2]} zx{m[1]} {m[3]}".replace("_x", "zx")
            continue
        m = re.match(r"\[(\d+)\] (\w+): (.*) => (.*)", ln)
        if m:
            cur = int(m[1])
            rows[cur] = {"tag": m[2], "prem": m[3], "concl": m[4].replace("_x", "zx"), "from": set()}
            continue
        m = re.match(r"      .* = (.*)", ln)
        if m and cur is not None:
            rows[cur]["from"] |= {int(x) for x in re.findall(r"\[(\d+)\]", m[1])}
            continue
        if ln.startswith("GOAL"):
            goals.append({int(x) for x in re.findall(r"\[(\d+)\]", ln)})
    d0 = pre + "".join(f"; zx{k} = {v}" for k, v in defs.items())
    names = set(re.findall(r"\b[a-z_][a-z0-9_]*\b", " ".join(rows[j]["concl"] for j in rows)))
    tasks, merged = {}, {}
    for j, r in rows.items():
        if r["tag"] in ("given", "centre", "midp_half"):
            continue
        c = r["concl"]
        merged.setdefault(c, set()).update(r["from"])
        if "cyclic_group" in r["prem"]:
            k = set(c.split()[1:])
            merged[c] |= {i for i, q in rows.items() if i < j and q["concl"].startswith("cyclic") and set(q["concl"].split()[1:]) <= k and q["concl"] != c}
    merged["GOAL"] = set().union(*goals) if goals else set()
    out = []

    def one(item):
        c, frm = item
        tgts = [goal] if c == "GOAL" else lemma_of(c)[:1] if not c.startswith("simtri") else [lemma_of(c)[0], lemma_of(c)[2]]
        if not tgts:
            return {"concl": c, "skip": True}
        rs = [one_t(c, frm, t) for t in tgts]
        return next((r for r in rs if not r["proved"]), rs[0])

    def one_t(c, frm, tgt):
        lem = sorted({x for i in frm for x in lemma_of(rows[i]["concl"]) if rows[i]["tag"] != "given" and x != tgt})
        with tempfile.NamedTemporaryFile("w", suffix=".json") as f:
            json.dump({"pts": [], "lem": lem, "trace": False, "proof": None}, f)
            f.flush()
            try:
                p = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "geo_translate.py"), "one_lem", f"{d0} ? {tgt}", str(timeout), f.name],
                                   capture_output=True, text=True, timeout=timeout * 4 + 600)
                q = json.loads(p.stdout.strip().splitlines()[-1])
                return {"concl": c, "target": tgt, "lemmas": len(lem), "proved": q["proved"], "drop": q["drop"], "err": q["err"], "sec": round(q["sec"], 1), "tag": next((r["tag"] for r in rows.values() if r["concl"] == c), "goal")}
            except Exception as e:
                return {"concl": c, "target": tgt, "lemmas": len(lem), "proved": False, "err": type(e).__name__, "tag": next((r["tag"] for r in rows.values() if r["concl"] == c), "goal")}
    return [one(x) for x in merged.items()]


def recon(c):
    """a coefficient mod P as a fraction, by rational reconstruction; the checker tests it exactly"""
    r0, r1, t0, t1 = P, c % P, 0, 1
    while r1 * r1 * 2 > P:
        q = r0 // r1
        r0, r1, t0, t1 = r1, r0 - q * r1, t1, t0 - q * t1
    return f"{-r1}/{-t1}" if t1 < 0 else f"{r1}/{t1}"


def cert_file(path, out):
    """a proof file -> a certificate for geo_check.py: the closure is rerun on the proof's points, and every row carries its relation by variable names"""
    L = open(path).read().split("\n")
    dsl = L[0]
    n, x, f, g = figure(dsl)
    N, X, F = list(n), [tuple(q) for q in x], [q[:-1] if q[-1] == "_" else q for q in f]
    defs = []
    for ln in L[1:]:
        if not ln.startswith("_x"):
            break
        nm, c = ln.split(" = ", 1)
        q = numeric_cand(c, dict(zip(N, X)))
        N.append(nm)
        X.append(tuple(q[0]))
        F += [tuple(nm if v == "_x" else v for v in h) for h in q[1]]
        defs.append((nm, c))
    e = Closure(N, X, F, deadline=time.time() + 1800)
    fell, _ = e.run(g[0])
    if not fell:
        raise RuntimeError("the goal does not fall on the proof's points")
    rows, chases = explain(e, g[0])
    keys = {}
    for sy, lin in (("D", e.D), ("W", e.W)) + ((("Q", e.Q),) if e.Q is not None else ()):
        for key, i in lin.idx.items():
            keys[sy, i] = [key[0], *[e.names[v] for v in key[1:]]] if key[0] != "t" else ["t", key[1], e.names[key[2]]]
    nm = lambda H: [H[0], *[e.names[v] if isinstance(v, (int, np.integer)) else v for v in H[1:]]]
    gid = {j: g_ for g_, rs in e.group_rows.items() for j in rs}
    Rows = []
    for j in rows:
        sy, rel, tag, prem, concl = e.log[j]
        cn = nm(concl)
        if concl[0] == "circle" and concl[1] is None:
            cn = ["cyclic", *cn[2:]]
        Rows.append({"j": j, "sys": sy, "rel": [[keys[sy, v], c] for v, c in rel], "tag": tag, "prem": [[H[0], H[1]] if H[0] == "cyclic_group" else ["tdiff", H[1]] if H[0] == "tdiff" else nm(H) for H in prem], "concl": cn, "gid": gid.get(j)})
    Ch = []
    for H, t, ctx, r in chases:
        ent = {"fact": ["tdiff"] if H[0] == "tdiff" else nm(H), "ctx": ctx, "rows": {str(i): recon(c) for i, c in r.items()}}
        if H[0] == "tdiff":
            ent["form"] = [[keys["D", v], c] for v, c in lform(e, H)[1]]
        Ch.append(ent)
    json.dump({"dsl": dsl, "defs": defs, "goal": list(g[0]), "facts": [list(q) for q in F], "rows": Rows, "chases": Ch}, open(out, "w"))


def certify():
    """certify <list.txt of proof files> <out.jsonl> [--timeout S] [--workers W]"""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    arg = lambda n, d: type(d)(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d
    timeout, workers = arg("--timeout", 60.0), arg("--workers", 16)
    files = open(sys.argv[2]).read().split()

    def run(fn):
        p = subprocess.run([sys.executable, os.path.abspath(__file__), "certify_one", fn, "--timeout", str(timeout)], capture_output=True, text=True)
        try:
            return json.loads(p.stdout.strip().splitlines()[-1])
        except Exception as e:
            return {"file": fn, "err": type(e).__name__, "stderr": p.stderr[-300:]}
    with ThreadPoolExecutor(workers) as ex, open(sys.argv[3], "w") as f:
        for fu in as_completed([ex.submit(run, x) for x in files]):
            f.write(json.dumps(fu.result()) + "\n")
            f.flush()


def main():
    cmd = sys.argv[1]
    if cmd == "certify":
        return certify()
    if cmd == "cert":
        return cert_file(sys.argv[2], sys.argv[3])
    if cmd == "certify_one":
        arg_t = float(sys.argv[sys.argv.index("--timeout") + 1])
        print(json.dumps({"file": sys.argv[2], "steps": certify_file(sys.argv[2], arg_t)}))
        return
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
