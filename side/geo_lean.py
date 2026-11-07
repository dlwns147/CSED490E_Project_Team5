"""SIDE-GT-LEAN: one Lean theorem per closure proof. A certificate from `geo_closure.py cert` is written over the rows its goal depends on: for all points, the statement's facts the proof
uses, the distinct names it uses, the conditions and the readings imply the goal. Every rule is a theorem of `side/lean/`, so Lean's kernel checks what `geo_check.py` trusts. A proof that cannot
be written stops with the reason, which is a fault of this file or of the checker.
  python side/geo_lean.py <cert.json> <out.lean>
  python side/geo_lean.py all <cert dir> <out dir>      (every certificate; the reasons go to <out dir>/export.jsonl)
"""
import glob, json, os, re, sys
from fractions import Fraction as Fr
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from geo_check import Bad, form, sim_rows, lin, key, mp, used


class Stop(Exception):
    pass


def pt(x):
    return "p_" + re.sub(r"[^A-Za-z0-9_]", "_", x)


def num(c):
    c = Fr(c)
    return f"({c.numerator})" if c.denominator == 1 else f"({c.numerator}/{c.denominator})"


def canon(v):
    return f"{ {'u': 'U', 'w': 'W', 's': 'd2'}[v[0]] } {pt(v[1])} {pt(v[2])}"


class Lattice:
    """the integer combinations of relations modulo 2π. A relation is a vector over directions and circle variables with a constant in units of π"""

    def __init__(self):
        self.piv, self.gens, self.order, self.seen = {}, [], {}, set()

    def add(self, vec, const, term):
        vec = {k: int(v) for k, v in vec.items() if v}
        key = (tuple(sorted(vec.items(), key=str)), const)
        if key in self.seen:
            return
        self.seen.add(key)
        for k in vec:
            self.order.setdefault(k, len(self.order))
        self.gens.append((vec, Fr(const), term))
        v, cb = dict(vec), {len(self.gens) - 1: 1}
        while v:
            c = min(v, key=self.order.get)
            if c not in self.piv:
                self.piv[c] = (v, cb)
                return
            p, pc = self.piv[c]
            while v.get(c):
                q = p[c] // v[c]
                p, pc, v, cb = v, cb, self.sub(p, v, q), self.sub(pc, cb, q)
            self.piv[c] = (p, pc)

    @staticmethod
    def sub(a, b, q):
        r = dict(a)
        for k, x in b.items():
            r[k] = r.get(k, 0) - q * x
            if not r[k]:
                del r[k]
        return r

    def solve(self, T):
        """-> generators and coefficients that sum to T, or None"""
        v, cb = dict(T), {}
        while v:
            if any(k not in self.order for k in v):
                return None
            c = min(v, key=self.order.get)
            if c not in self.piv or v[c] % self.piv[c][0][c]:
                return None
            p, pc = self.piv[c]
            q = v[c] // p[c]
            v, cb = self.sub(v, p, q), self.sub(cb, pc, -q)
        return cb


class Writer:
    def __init__(self, c, lift=False):
        self.sims = set()
        self.lat, self.proved, self.throws, self.lifted, self.opposite = Lattice() if lift else None, {}, set(), 0, 0
        self.c, self.body, self.pairs, self.hyps, self.nc, self.reads, self.groups, self.points = c, [], set(), {}, {}, {}, {}, set()
        self.rows = {r["j"]: r for r in c["rows"]}
        self.by = {}
        for ch in c["chases"]:
            self.by.setdefault(ch["ctx"], []).append(ch)
        self.facts = c["facts"]
        self.names = {nm for nm, _ in c["defs"]}
        self.fresh = 0

    def line(self, s):
        self.body.append("  " + s)

    def new(self, p):
        self.fresh += 1
        return f"{p}{self.fresh}"

    def ne(self, x, y):
        """the hypothesis that two names are apart"""
        if x == y:
            raise Stop(f"a pair {x} {x}")
        a, b = sorted((x, y))
        self.pairs.add((a, b))
        self.points |= {a, b}
        n = f"n_{pt(a)}_{pt(b)}"
        return n if (x, y) == (a, b) else f"{n}.symm"

    def NC(self, x, y, z):
        s = tuple(sorted((x, y, z)))
        if len(set(s)) < 3:
            raise Stop("a condition on two points")
        self.points |= set(s)
        n = self.nc.setdefault(s, f"nc{len(self.nc)}")
        return _perm(n, s, (x, y, z), lambda t, i: f"{t}.swap{'12' if i == 0 else '23'}")

    def read(self, kind, a, b, c, p, q, r):
        """a similar pair's orientation, in the order the rule wants"""
        o = sorted(zip((a, b, c), (p, q, r)))
        s = (tuple(x for x, _ in o), tuple(y for _, y in o))
        self.points |= {a, b, c, p, q, r}
        if self.lat is not None and (kind, *s) not in self.reads:
            t = self.proved.get((kind, a, b, c, p, q, r)) or self.discharge(kind, a, b, c, p, q, r)
            if t:
                self.proved[(kind, a, b, c, p, q, r)] = t
                return t
        n = self.reads.setdefault((kind, *s), f"rd{len(self.reads)}")
        return _perm2(n, s, ((a, b, c), (p, q, r)))

    # readings proved: directions modulo 2π (GeoLift.lean)

    def atoms(self, vec):
        """every direction is known with its reverse"""
        for k in list(vec):
            if k[0] == "th" and ("th", k[2], k[1]) in self.lat.order and k not in self.lat.order:
                self.swap(k[1], k[2])
            self.lat.order.setdefault(k, len(self.lat.order))

    def swap(self, a, b):
        self.lat.add({("th", b, a): 1, ("th", a, b): -1}, 1, lambda: f"(th_swap {self.ne(a, b)})")

    def known(self, vec, const, term):
        vec = {k: v for k, v in vec.items() if v}
        for k in vec:
            if k[0] == "th" and ("th", k[2], k[1]) in self.lat.order:
                self.swap(k[1], k[2])
        self.lat.add(vec, const, term)

    def lift_row(self, r):
        """the double of a row modulo π holds modulo 2π"""
        vec = {}
        for v, c in r["rel"].items():
            if Fr(c).denominator != 1:
                return
            k = ("th", v[1], v[2]) if v[0] == "u" else v
            vec[k] = 2 * int(c)
        j = r["j"]

        def term():
            if j not in self.throws:
                self.throws.add(j)
                us = [(v, c) for v, c in r["rel"].items() if v[0] == "u"]
                add = f"r{j}"
                for v, c in us:
                    add = f"({add}).add ((th_u {self.ne(v[1], v[2])}).zmul ({int(c)}))"
                e = " + ".join(f"{num(c)} * Th {pt(v[1])} {pt(v[2])}" if v[0] == "u" else f"{num(c)} * tz {self.groups[v[1]]['o']} {self.groups[v[1]]['r']} {pt(v[2])}" for v, c in r["rel"].items())
                self.line(f"have t{j} : ModPi ({e} - {num(r['const'])} * Real.pi) := ModPi.congr (by push_cast; ring) ({add})")
            return f"(Mod2.dbl t{j})"
        self.known(vec, 2 * Fr(r["const"]), term)

    def lift_sim(self, name, o, a, b, c, p, q, s):
        if len({a, b, c}) < 3 or len({p, q, s}) < 3:
            return
        sg = -1 if o else 1
        lem = "sim_lift" if o else "sim2_lift"
        for (x, y, z, x2, y2, z2, h) in ((a, b, c, p, q, s, name), (b, a, c, q, p, s, f"({name}).p12")):
            self.known(add_vec({("th", x, y): 1}, {("th", x, z): -1}, {("th", x2, y2): sg}, {("th", x2, z2): -sg}), 0,
                       lambda x=x, y=y, z=z, x2=x2, y2=y2, z2=z2, h=h: f"({lem} {h} {self.ne(x, y)} {self.ne(x, z)} {self.ne(x2, y2)} {self.ne(x2, z2)})")

    def lift_midp(self, m, a, b, n):
        self.known({("th", m, a): 1, ("th", b, m): -1}, 0, lambda: f"(midp_lift {n})")
        self.known({("th", a, m): 1, ("th", a, b): -1}, 0, lambda: f"(midp_end {n})")

    def discharge(self, kind, a, b, c, p, q, r):
        """a proof of the reading, or None: the angle at some vertex of the pair, modulo 2π, as a combination of what is known"""
        sg = -1 if kind == "Read" else 1
        lem = "read_lift" if kind == "Read" else "read2_lift"
        for x, y, z, x2, y2, z2, back in ((a, b, c, p, q, r, ""), (b, a, c, q, p, r, ".p12"), (c, a, b, r, p, q, ".p12.p23")):
            T = add_vec({("th", x, y): 1}, {("th", x, z): -1}, {("th", x2, y2): sg}, {("th", x2, z2): -sg})
            self.atoms(T)
            cb = self.lat.solve(T)
            if cb is None:
                continue
            tot = sum((self.lat.gens[g][1] * co for g, co in cb.items()), Fr(0))
            if tot % 2:
                self.opposite += 1
                continue
            acc = f"(Mod2.int ({int(tot / 2)}))"
            for g, co in cb.items():
                acc = f"({acc}).add (Mod2.zmul ({co}) {self.lat.gens[g][2]()})"
            n = self.new("q")
            th = lambda u, v: f"Th {pt(u)} {pt(v)}"
            e = f"{th(x, y)} - {th(x, z)} {'-' if kind == 'Read' else '+'} {th(x2, y2)} {'+' if kind == 'Read' else '-'} {th(x2, z2)}"
            self.line(f"have {n} : Mod2 ({e}) := Mod2.congr (by push_cast; ring) ({acc})")
            self.lifted += 1
            return f"({lem} {n} {self.ne(x, y)} {self.ne(x, z)} {self.ne(x2, y2)} {self.ne(x2, z2)} {self.NC(x, y, z)}){back}"
        return None

    def readx(self, kind, *a):
        self.points |= set(a)
        return self.reads.setdefault((kind, a), f"rd{len(self.reads)}")

    def hyp(self, F):
        """the name of a fact of the statement or of a construction"""
        k = json.dumps(F)
        if k not in self.hyps:
            self.hyps[k] = (F, f"h{len(self.hyps)}")
            self.points |= set(q for q in F[1:] if isinstance(q, str))
        return self.hyps[k][1]

    # facts: Lean proposition, what `iff` turns it into, and the terms with their signs as written

    def prop(self, F):
        k, *a = F
        p = [pt(x) for x in a]
        self.points |= set(a)
        if k == "coll" and len(a) == 3:
            return f"Para {p[0]} {p[1]} {p[0]} {p[2]}"
        if k in ("coll", "para"):
            return f"Para {' '.join(p)}"
        names = {"perp": "Perp", "eqangle": "EqA", "cong": "Cong", "eqratio": "Ratio", "half": "Half", "sqcong": "SqCong", "sqperp": "SqPerp", "sqmid": "SqMid", "sqmedian": "SqMedian"}
        if k not in names:
            raise Stop(f"no proposition for {k}")
        return f"{names[k]} {' '.join(p)}"

    def terms(self, F):
        """the linear form as the Lean definition writes it: (kind, x, y), coefficient"""
        k, *a = F
        if k == "coll" and len(a) == 3:
            return "D", [(("u", a[0], a[1]), 1), (("u", a[0], a[2]), -1)], Fr(0)
        if k in ("coll", "para"):
            return "D", [(("u", a[0], a[1]), 1), (("u", a[2], a[3]), -1)], Fr(0)
        if k == "perp":
            return "D", [(("u", a[0], a[1]), 1), (("u", a[2], a[3]), -1)], Fr(1, 2)
        if k == "eqangle":
            return "D", [(("u", a[0], a[1]), 1), (("u", a[2], a[3]), -1), (("u", a[4], a[5]), -1), (("u", a[6], a[7]), 1)], Fr(0)
        if k == "cong":
            return "W", [(("w", a[0], a[1]), 1), (("w", a[2], a[3]), -1)], Fr(0)
        if k == "eqratio":
            return "W", [(("w", a[0], a[1]), 1), (("w", a[2], a[3]), -1), (("w", a[4], a[5]), -1), (("w", a[6], a[7]), 1)], Fr(0)
        if k == "half":
            return "W", [(("w", a[0], a[1]), 1), (("w", a[2], a[3]), -1)], Fr(1)
        if k == "sqcong":
            return "Q", [(("s", a[0], a[1]), 1), (("s", a[2], a[3]), -1)], Fr(0)
        if k == "sqperp":
            return "Q", [(("s", a[0], a[2]), 1), (("s", a[0], a[3]), -1), (("s", a[1], a[2]), -1), (("s", a[1], a[3]), 1)], Fr(0)
        if k == "sqmid":
            return "Q", [(("s", a[1], a[2]), 1), (("s", a[0], a[1]), -4)], Fr(0)
        if k == "sqmedian":
            return "Q", [(("s", a[0], a[1]), 2), (("s", a[1], a[2]), 2), (("s", a[0], a[2]), -1), (("s", a[0], a[3]), -1)], Fr(0)
        raise Stop(f"no form for {k}")

    def iff(self, F):
        k, *a = F
        if k == "coll" and len(a) == 3:
            a = [a[0], a[1], a[0], a[2]]
        n = lambda i: self.ne(a[i], a[i + 1])
        if k in ("coll", "para"):
            return f"(para_iff {n(0)} {n(2)})"
        if k == "perp":
            return f"(perp_iff {n(0)} {n(2)})"
        if k == "eqangle":
            return f"(eqa_iff {n(0)} {n(2)} {n(4)} {n(6)})"
        if k == "cong":
            return f"(cong_iff {n(0)} {n(2)})"
        if k == "eqratio":
            return f"(ratio_iff {n(0)} {n(2)} {n(4)} {n(6)})"
        if k == "half":
            return f"(half_iff {n(0)} {n(2)})"
        raise Stop(f"no iff for {k}")

    def expr(self, T):
        """a form as Lean writes it, in the order given"""
        s = []
        for (k, x, y), c in T:
            s.append(f"{num(c)} * {canon((k, x, y))}" if x != y else "0")
        return " + ".join(s) if s else "0"

    def swaps(self, T, sign):
        """the terms of a form written against the canonical order, for linear_combination"""
        out = []
        comm = {"u": "U_comm", "w": "W_comm", "s": "d2_comm"}
        for (k, x, y), c in T:
            if x == y:
                out.append(f"{num(sign * c)} * d2_self {pt(x)}")
            elif x > y:
                out.append(f"{num(sign * c)} * {comm[k]} {pt(x)} {pt(y)}")
        return out

    def rowexpr(self, r):
        """the row as a linear form in canonical variables"""
        s = []
        for v, c in r["rel"].items():
            if v[0] == "t":
                g = self.groups.get(v[1])
                if g is None:
                    raise Stop(f"variable of an unknown circle {v[1]}")
                s.append(f"{num(c)} * tz {g['o']} {g['r']} {pt(v[2])}")
            else:
                s.append(f"{num(c)} * {canon(v)}")
        return " + ".join(s) if s else "0"

    def rowprop(self, r):
        e, k = self.rowexpr(r), r["const"]
        if r["sys"] == "D":
            return f"ModPi ({e} - {num(k)} * Real.pi)"
        if r["sys"] == "W":
            return f"{e} = {num(k)} * Real.log 2"
        return f"{e} = 0"

    def combine(self, ch):
        """the sum of rows a chase names: for directions a term and a constant, otherwise a linear_combination"""
        return [(int(i), Fr(co)) for i, co in ch["rows"].items()]

    def have_fact(self, F, ch):
        """a fact from a chase of rows"""
        sy, T, cst = self.terms(F)
        return self.from_rows(sy, T, cst, ch, self.prop(F), F)

    def from_rows(self, sy, T, cst, ch, prop, F):
        name = self.new("c")
        rows = self.combine(ch)
        if any(self.rows[i]["const"] is None for i, _ in rows):
            raise Stop("a constant read from the figure")
        total = sum((co * self.rows[i]["const"] for i, co in rows), Fr(0))
        if sy == "D":
            n = total - cst
            if n.denominator != 1:
                raise Stop(f"direction constants differ by {n}")
            if any(co.denominator != 1 for _, co in rows):
                raise Stop("a fractional combination of directions")
            s = None
            for i, co in rows:
                t = f"(ModPi.zmul ({int(co)}) r{i})"
                s = t if s is None else f"(ModPi.add {s} {t})"
            s = f"(ModPi.add {s} (ModPi.int ({int(n)})))" if s else f"(ModPi.int ({int(n)}))"
            e = " + ".join(self.swaps(T, -1)) or "(0 : ℝ) * (0 : ℝ)"
            self.line(f"have {name} : {prop} := {self.iff(F)}.mpr (ModPi.congr (by push_cast; linear_combination {e}) {s})")
        elif sy == "W":
            if total != cst:
                raise Stop("log constants differ")
            e = " + ".join([f"{num(co)} * r{i}" for i, co in rows] + self.swaps(T, 1))
            self.line(f"have {name} : {prop} := {self.iff(F)}.mpr (by linear_combination {e})")
        else:
            if total != 0:
                raise Stop("square constants differ")
            e = " + ".join([f"{num(co)} * r{i}" for i, co in rows] + self.swaps(T, 1))
            self.line(f"have {name} : {prop} := by")
            self.line(f"  show {qform(F)} = 0")
            self.line(f"  linear_combination {e}")
        return name

    def row_from(self, j, F, term):
        """row j from a proof of the fact F"""
        r = self.rows[j]
        sy, T, cst = self.terms(F)
        if r["sys"] != sy:
            raise Stop(f"row {j} in the wrong system")
        if sy == "D":
            e = " + ".join(self.swaps(T, 1)) or "(0 : ℝ) * (0 : ℝ)"
            self.line(f"have r{j} : {self.rowprop(r)} := ModPi.congr (by linear_combination {e}) ({self.iff(F)}.mp {term})")
        elif sy == "W":
            e = " - ".join(["h"] + [x for x in self.swaps(T, 1)])
            self.line(f"have r{j} : {self.rowprop(r)} := by")
            self.line(f"  have h := {self.iff(F)}.mp {term}")
            self.line(f"  linear_combination {e}")
        else:
            e = " - ".join(["h"] + [x for x in self.swaps(T, 1)])
            self.line(f"have r{j} : {self.rowprop(r)} := by")
            self.line(f"  have h : {qform(F)} = 0 := {term}")
            self.line(f"  linear_combination {e}")

    # the facts of the statement

    def line_of(self, g):
        """a collinear or midpoint fact as a line: two points, and each point's proof of lying on it"""
        if g[0] == "midp":
            m, a, b = g[1:]
            h = self.hyp(g)
            return a, b, {a: f"(coll_self1 {pt(a)} {pt(b)})", b: f"(coll_self2 {pt(a)} {pt(b)})", m: f"({h}).coll"}
        p, q, *rest = g[1:]
        mem = {p: f"(coll_self1 {pt(p)} {pt(q)})", q: f"(coll_self2 {pt(p)} {pt(q)})"}
        for i, x in enumerate(rest):
            mem[x] = _nth(self.hyp(g), i, len(rest))
        return p, q, mem

    def given(self, F):
        """the proof of a row's fact from the statement"""
        k, *a = F
        for g in self.facts:
            h, *b = g
            if k == "coll" and h in ("coll", "collx", "midp") and set(a) <= set(b):
                p, q, mem = self.line_of(g)
                w = a if len(a) == 4 else [a[0], a[1], a[0], a[2]]
                return f"(para_of_line {self.ne(p, q)} {mem[w[0]]} {mem[w[1]]} {mem[w[2]]} {mem[w[3]]})"
            if k == "cong" and h == "cong" and sorted([sorted(a[:2]), sorted(a[2:])]) == sorted([sorted(b[:2]), sorted(b[2:])]):
                sign = 1 if sorted(a[:2]) == sorted(b[:2]) else -1
                T = [(("s", b[0], b[1]), sign), (("s", b[2], b[3]), -sign)]
                U_ = [(("s", a[0], a[1]), 1), (("s", a[2], a[3]), -1)]
                x = self.new("g")
                e = [f"{num(sign)} * {self.hyp(g)}"] + [q for q in _sw(U_, T)]
                self.line(f"have {x} : {self.prop(F)} := by")
                self.line(f"  show d2 {pt(a[0])} {pt(a[1])} = d2 {pt(a[2])} {pt(a[3])}")
                self.line(f"  have {x}h : d2 {pt(b[0])} {pt(b[1])} = d2 {pt(b[2])} {pt(b[3])} := {self.hyp(g)}")
                self.line(f"  linear_combination {num(sign)} * {x}h {' '.join('+ ' + q for q in _sw(U_, T))}")
                return x
            if k == "cong" and h == "circle" and a[0] == b[0] == a[2] and {a[1], a[3]} <= set(b[1:]):
                if a[1] == a[3]:
                    return f"(rfl : {self.prop(F)})"
                return f"(Eq.trans ({self.circ(g, a[1])}).symm {self.circ(g, a[3])})"
            if k == "cong" and h == "midp" and a[0] == b[0] == a[2] and {a[1], a[3]} == set(b[1:]):
                t = f"({self.hyp(g)}).cong"
                return t if a[1] == b[1] else f"({t}).symm"
            if k == h and list(a) == list(b):
                return self.hyp(g)
        raise Stop(f"{F} not in the statement")

    def circ(self, g, x):
        """a proof of `d2 o first = d2 o x`"""
        b = g[1:]
        if x == b[1]:
            return f"(rfl : d2 {pt(b[0])} {pt(x)} = d2 {pt(b[0])} {pt(x)})"
        return _nth(self.hyp(g), b[2:].index(x), len(b) - 2)

    # circles

    def from_fact(self, g):
        """the circle of a cyclic fact"""
        k = "circ_" + self.hyp(g)
        if k not in self.groups:
            o, r, hr = self.new("o"), self.new("ra"), self.new("hr")
            pts = g[1:]
            on = {x: self.new("on") for x in pts}
            self.line(f"obtain ⟨{o}, {r}, {hr}, {', '.join(on[x] for x in pts)}⟩ := {self.hyp(g)}")
            self.groups[k] = {"o": o, "r": r, "hr": hr, "on": on}
        return self.groups[k]

    def merge(self, gs):
        """one circle from several that share three points each with what is already merged"""
        cur, todo = dict(gs[0], on=dict(gs[0]["on"])), list(gs[1:])
        while todo:
            for g in todo:
                sh = sorted(set(g["on"]) & set(cur["on"]))
                if cur["o"] == g["o"] and sh:     # one centre: a shared point gives the radius
                    s = sh[0]
                    for x, n in g["on"].items():
                        if x not in cur["on"]:
                            m = self.new("on")
                            self.line(f"have {m} : On {cur['o']} {cur['r']} {pt(x)} := ({n}).trans (({g['on'][s]}).symm.trans {cur['on'][s]})")
                            cur["on"][x] = m
                    todo.remove(g)
                    break
                if len(sh) >= 3:
                    x, y, z = sh[:3]
                    for p, n in g["on"].items():
                        if p not in cur["on"]:
                            m = self.new("on")
                            self.line(f"have {m} : On {cur['o']} {cur['r']} {pt(p)} := On.move {cur['on'][x]} {cur['on'][y]} {cur['on'][z]} {g['on'][x]} {g['on'][y]} {g['on'][z]} {self.ne(x, y)} {self.ne(x, z)} {self.ne(y, z)} {n}")
                            cur["on"][p] = m
                    todo.remove(g)
                    break
            else:
                raise Stop(f"circles joined on fewer than three points: {sorted(cur['on'])} and {[sorted(g['on']) for g in todo]}")
        return cur

    def make_group(self, r):
        j, tag, gid, concl = r["j"], r["tag"], r["gid"], r["concl"]
        prem = r["prem"]
        real = [F for F in prem if F[0] != "cyclic_group"]
        base = [self.groups[F[1]] for F in prem if F[0] == "cyclic_group"]
        pts = set(concl[2:]) if concl[0] == "circle" else set(concl[1:])
        gs = []
        if tag == "given":
            need, fs = pts - {x for g in base for x in g["on"]}, []
            for g in sorted([g for g in self.facts if g[0] == "cyclic" and set(g[1:]) <= pts], key=lambda g: -len(set(g[1:]) & (need or pts))):
                if need & set(g[1:]) or not base and not fs:
                    fs.append(g)
                    need = need - set(g[1:])
            if need:
                raise Stop(f"no fact gives {need}")
            gs = base + [self.from_fact(g) for g in fs]
        elif tag == "inscribed":
            F = real[0]
            x, a, b, y = F[1], F[2], F[4], F[5]
            c = self.prem(j, F)
            o, rr, hr, ox, oa, ob, oy = (self.new(q) for q in ("o", "ra", "hr", "on", "on", "on", "on"))
            self.line(f"obtain ⟨{o}, {rr}, {hr}, {ox}, {oa}, {ob}, {oy}⟩ := cyc_of_eqa {self.ne(x, a)} {self.NC(x, a, b)} {c}")
            gs = base + [{"o": o, "r": rr, "hr": hr, "on": {x: ox, a: oa, b: ob, y: oy}}]
        else:
            o = real[0][1]
            ends = {}
            first = real[0][2]
            rname = f"(d2 {pt(o)} {pt(first)})"
            hr = self.new("hr")
            self.line(f"have {hr} : 0 < {rname} := d2_pos {self.ne(o, first)}")
            n0 = self.new("on")
            self.line(f"have {n0} : On {pt(o)} {rname} {pt(first)} := rfl")
            ends[first] = n0
            edges = [(F[2], F[4], self.prem(j, F)) for F in real]
            more = True
            while more:
                more = False
                for x, y, c in edges:
                    for s, t, tm in ((x, y, f"({c}).symm"), (y, x, c)):
                        if s in ends and t not in ends:
                            m = self.new("on")
                            self.line(f"have {m} : On {pt(o)} {rname} {pt(t)} := ({tm}).trans {ends[s]}")
                            ends[t] = m
                            more = True
            if any(x not in ends or y not in ends for x, y, _ in edges):
                raise Stop("equal radii that are not joined")
            gs = [{"o": pt(o), "r": rname, "hr": hr, "on": ends}] + base
        g = self.merge(gs)
        if not pts <= set(g["on"]):
            raise Stop(f"the circle lacks {pts - set(g['on'])}")
        self.groups[gid] = g

    def prem(self, j, F):
        """the proof of a premise, from the row's chases"""
        k = json.dumps(F)
        m = self.cache.get(k)
        if m:
            return m
        for ch in self.by.get(j, []):
            if json.dumps(ch["fact"]) == k:
                m = self.have_fact(F, ch)
                self.cache[k] = m
                return m
        raise Stop(f"row {j}: no chase for {F}")

    def group_row(self, r):
        g = self.groups[r["gid"]]
        rel, j = r["rel"], r["j"]
        ts = [(v, c) for v, c in rel.items() if v[0] == "t"]
        us = [(v, c) for v, c in rel.items() if v[0] == "u"]
        if len(us) != 1 or us[0][1] != 1:
            raise Stop(f"row {j}: not a chord or radius")
        (_, x, y), _c = us[0]
        if len(ts) == 2:
            t = f"chord {g['hr']} {g['on'][x]} {g['on'][y]} {self.ne(x, y)}"
            self.line(f"have r{j} : {self.rowprop(r)} := ModPi.congr (by ring) ({t})")
        else:
            p = ts[0][0][2]
            o = x if p == y else y
            if pt(o) != g["o"]:
                raise Stop(f"row {j}: radius from {o}, the circle's centre is {g['o']}")
            t = f"radius {g['hr']} {g['on'][p]} {self.ne(o, p)}"
            if self.lat is not None:
                self.known({("th", o, p): 1, ts[0][0]: -2}, Fr(-1, 2), lambda: f"(radius_lift {g['hr']} {g['on'][p]} {self.ne(o, p)})")
            e = " + ".join(self.swaps([(("u", o, p), 1)], 1)) or "(0 : ℝ) * (0 : ℝ)"
            self.line(f"have r{j} : {self.rowprop(r)} := ModPi.congr (by linear_combination {e}) ({t})")

    def similar(self, r):
        j, concl, real = r["j"], r["concl"], [F for F in r["prem"] if F[0] != "cyclic_group"]
        a, b, c, p, q, s = concl[1:]
        o = concl[0] == "simtri"
        P = (lambda x: pt(x)) if o else (lambda x: f"(rf {pt(x)})")
        aa = lambda x, y, z, x2, y2, z2: ["eqangle", x, y, x, z, x2, y2, x2, z2] if o else ["eqangle", x, y, x, z, x2, z2, x2, y2]
        A, B, C = aa(a, b, c, p, q, s), aa(b, a, c, q, p, s), aa(c, a, b, s, p, q)
        rr = lambda x, y, x2, y2, e, f, e2, f2: ["eqratio", x, y, x2, y2, e, f, e2, f2]
        R12, R13, R23 = rr(a, b, p, q, b, c, q, s), rr(a, b, p, q, c, a, s, p), rr(b, c, q, s, c, a, s, p)
        ang = lambda F: self.prem(j, F) if o else f"(eqa_rf {self.prem(j, F)})"
        rat = lambda F: self.prem(j, F) if o else f"(ratio_rf {self.prem(j, F)})"
        ne = lambda x, y: self.ne(x, y) if o else f"(rf_ne {self.ne(x, y)})"
        rd = (lambda *t: self.read("Read", *t)) if o else (lambda *t: f"(Read2.rf {self.read('Read2', *t)})")
        have = [F in real for F in (A, B, C)]
        if sum(have) == 2 and len(real) == 2:
            if have[0] and have[1]:
                t = f"sim_aa {self.ne(a, b)} {ne(p, q)} {self.NC(a, b, c)} {ang(A)} {ang(B)}"
            elif have[0]:
                t = f"(sim_aa {self.ne(a, c)} {ne(p, s)} {self.NC(a, c, b)} (eqa_flip {ang(A)}) {ang(C)}).p23"
            else:
                t = f"(sim_aa {self.ne(b, c)} {ne(q, s)} {self.NC(b, c, a)} (eqa_flip {ang(B)}) (eqa_flip {ang(C)})).p23.p12"
        elif real == [R12, R13]:
            t = f"sim_sss {self.ne(a, b)} {ne(p, q)} {rd(a, b, c, p, q, s)} {rat(R12)} {rat(R13)}"
        elif real == [R13, A]:
            t = f"sim_sas {self.ne(a, b)} {ne(p, q)} {rd(a, b, c, p, q, s)} {rat(R13)} {ang(A)}"
        elif real == [R12, B]:
            t = f"(sim_sas {self.ne(b, a)} {ne(q, p)} {rd(b, a, c, q, p, s)} (ratio_swap {rat(R12)}) {ang(B)}).p12"
        elif real == [R23, C]:
            t = f"(sim_sas {self.ne(c, a)} {ne(s, p)} {rd(c, a, b, s, p, q)} (ratio_flip {rat(R23)}) {ang(C)}).p12.p23"
        else:
            raise Stop(f"row {j}: premises of a similar pair {real}")
        name = self.new("s")
        tr = f"{P(p)} {P(q)} {P(s)}"
        self.line(f"have {name} : Sim {pt(a)} {pt(b)} {pt(c)} {tr} := {t}")
        if self.lat is not None and json.dumps(concl) not in self.sims:
            self.sims.add(json.dumps(concl))
            self.lift_sim(name, o, a, b, c, p, q, s)
        for i, (sy, f, _) in enumerate(sim_rows(concl)):
            if r["sys"] == sy and lin(*r["rel"].items()) == f:
                pre = "sim" if o else "sim2"
                F = (A, B, [], [])[i] if i < 2 else None
                if i == 2:
                    F = R12
                if i == 3:
                    F = R13
                term = f"({pre}_{('eqa1', 'eqa2', 'r1', 'r2')[i]} {name})"
                return self.row_from(j, F, term)
        raise Stop(f"row {j}: not a relation of the pair")

    def lines(self, j, P):
        """the rule `line`: triples merged while they share two points; each merged line keeps its first two points"""
        L = []
        for F in P:
            pts = []
            for q in F[1:]:
                if q not in pts:
                    pts.append(q)
            c = self.prem(j, F)
            shared = ({F[1], F[2]} & {F[3], F[4]}).pop()
            x = F[2] if F[1] == shared else F[1]
            y = F[4] if F[3] == shared else F[3]
            nm = self.new("l")
            sw = [f"{c_} * U_comm {pt(p)} {pt(q)}" for p, q, c_ in ((F[1], F[2], "(1)"), (F[3], F[4], "(-1)")) if q == shared]
            self.line(f"have {nm} : Para {pt(shared)} {pt(x)} {pt(shared)} {pt(y)} := (para_iff {self.ne(shared, x)} {self.ne(shared, y)}).mpr (ModPi.congr (by linear_combination {' + '.join(sw) or '(0 : ℝ) * (0 : ℝ)'}) ({self.iff(F)}.mp {c}))")
            L.append({"p": shared, "q": x, "mem": {shared: f"(coll_self1 {pt(shared)} {pt(x)})", x: f"(coll_self2 {pt(shared)} {pt(x)})", y: nm}})
        return L

    def line_rule(self, r):
        j, concl = r["j"], r["concl"]
        P = [F for F in r["prem"] if F[0] != "cyclic_group"]
        L = self.lines(j, P)
        done = True
        while done:
            done = False
            for u in L:
                for v in L:
                    if u is v:
                        continue
                    sh = sorted(set(u["mem"]) & set(v["mem"]))
                    if len(sh) >= 2:
                        s, t = sh[:2]
                        # s, t on both: the points of v move to u through line st
                        for x, tm in v["mem"].items():
                            if x not in u["mem"]:
                                m = self.new("l")
                                vs = f"(para_of_line {self.ne(v['p'], v['q'])} {v['mem'][s]} {v['mem'][t]} {v['mem'][s]} {tm})"
                                self.line(f"have {m} : Coll {pt(u['p'])} {pt(u['q'])} {pt(x)} := coll_ext {self.ne(u['p'], u['q'])} {self.ne(s, t)} {u['mem'][s]} {u['mem'][t]} {vs}")
                                u["mem"][x] = m
                        L.remove(v)
                        done = True
                        break
                if done:
                    break
        a = concl[1:]
        w = a if len(a) == 4 else [a[0], a[1], a[0], a[2]]
        for u in L:
            if set(w) <= set(u["mem"]):
                return f"(para_of_line {self.ne(u['p'], u['q'])} {u['mem'][w[0]]} {u['mem'][w[1]]} {u['mem'][w[2]]} {u['mem'][w[3]]})"
        raise Stop(f"row {j}: the line lacks {concl}")

    def midp(self, j, F1, F2):
        """(coll m a b), (cong m a m b) -> m, a, b, a proof of Midp"""
        m, a, b = mp(F1, F2)
        c = self.prem(j, F1)
        c = c if F1[2] == a else f"(coll_sw {c})"
        h = self.prem(j, F2)
        n = self.new("m")
        self.line(f"have {n} : Midp {pt(m)} {pt(a)} {pt(b)} := midp_of {self.ne(a, b)} {c} {h}")
        if self.lat is not None:
            self.lift_midp(m, a, b, n)
        return m, a, b, n

    def rule(self, r):
        j, tag, concl = r["j"], r["tag"], r["concl"]
        P = [F for F in r["prem"] if F[0] != "cyclic_group"]
        pr = lambda F: self.prem(j, F)
        k = concl[0]
        if tag == "given":
            if k == "const":
                raise Stop("a constant read from the figure")
            return concl, self.given(concl)
        if tag == "isosceles":
            F = P[0]
            x, y, o, A = concl[1], concl[2], concl[3], concl[4]
            h = pr(F) if F[2] == x else f"({pr(F)}).symm"
            if self.lat is not None:
                self.known(add_vec({("th", x, y): 2}, {("th", o, x): -1}, {("th", y, o): -1}), 0, lambda: f"(isos_lift {h} {self.ne(x, y)} {self.ne(o, x)} {self.ne(o, y)})")
            return concl, f"({'isos1' if A == x else 'isos2'} {h})"
        if tag == "base_angles":
            F = P[0]
            x, y, o, A = F[1], F[2], F[3], F[4]
            t = f"({'base1' if A == x else 'base2'} {self.NC(o, x, y)} {pr(F)})"
            return concl, t if concl[2] == x else f"({t}).symm"
        if tag == "perp_bisector":
            a, b = concl[1], concl[2]
            p, q = P[0][1], P[1][1]
            h1 = pr(P[0]) if P[0][2] == a else f"({pr(P[0])}).symm"
            h2 = pr(P[1]) if P[1][2] == a else f"({pr(P[1])}).symm"
            return ["perp", a, b, p, q], f"(perp_bisector {h1} {h2})"
        if tag == "line":
            return concl, self.line_rule(r)
        if tag == "midp_half":
            m, a, b, n = self.midp(j, P[0], P[1])
            return concl, f"(midp_half {n})"
        if tag == "midline":
            m1, a1, b1, n1 = self.midp(j, P[0], P[1])
            m2, a2, c2, n2 = self.midp(j, P[2], P[3])
            if self.lat is not None:
                self.known({("th", m1, m2): 1, ("th", b1, c2): -1}, 0, lambda: f"(midline_lift {n1} {n2})")
            return concl, f"(midline {n1} {n2})"
        if tag == "parallelogram":
            m, a, b, n1 = self.midp(j, P[0], P[1])
            m2, c_, e, n2 = self.midp(j, P[2], P[3])
            if self.lat is not None:
                one = concl[1:] == [a, c_, b, e]
                self.known({("th", a, c_ if one else e): 1, ("th", e if one else c_, b): -1}, 0, lambda: f"({'para1_lift' if one else 'para2_lift'} {n1} {n2})")
            return concl, f"({'parallelogram1' if concl[1:] == [a, c_, b, e] else 'parallelogram2'} {n1} {n2})"
        if tag == "parallelogram_mid":
            m, a, b, n1 = self.midp(j, P[0], P[1])
            c_, e = P[2][2], P[3][2]
            if P[2][4] != e or P[3][4] != c_:
                raise Stop(f"row {j}: not a parallelogram {P[2]} {P[3]}")
            n = self.new("m")
            self.line(f"have {n} : Midp {pt(m)} {pt(c_)} {pt(e)} := parallelogram_mid {self.NC(a, b, c_)} {n1} {pr(P[2])} {pr(P[3])}")
            if k == "cong":
                return concl, f"({n}).cong" if concl[2] == c_ else f"(({n}).cong).symm"
            mem = {m: f"({n}).coll", c_: f"(coll_self1 {pt(c_)} {pt(e)})", e: f"(coll_self2 {pt(c_)} {pt(e)})"}
            w = concl[1:] if len(concl) == 5 else [concl[1], concl[2], concl[1], concl[3]]
            return concl, f"(para_of_line {self.ne(c_, e)} {mem[w[0]]} {mem[w[1]]} {mem[w[2]]} {mem[w[3]]})"
        if tag == "right_median":
            m, a, b, n = self.midp(j, P[0], P[1])
            return concl, f"(right_median {n} {pr(P[2])})"
        if tag == "mid_perp":
            m, a, b, n = self.midp(j, P[0], P[1])
            return concl, f"(mid_perp {n} {pr(P[2])})"
        if tag == "chord_mid":
            F, G, H = P
            a, b = H[3], H[4]
            h = pr(F) if F[2] == a else f"({pr(F)}).symm"
            t = f"(chord_mid {h} {pr(H)})"
            return concl, t if concl[2] == a else f"({t}).symm"
        if tag == "bisector":
            Co, F = P
            e, b, c_ = Co[1:]
            if F[0] == "eqratio":
                return concl, f"(bisector_A {self.ne(b, c_)} {pr(Co)} {pr(F)})"
            return concl, f"(bisector_R {self.ne(b, c_)} {self.NC(F[1], b, c_)} {pr(Co)} {pr(F)})"
        if tag == "thales":
            A1, A2, R = P
            o, a, c_ = A1[1:]
            b, e = A2[2:]
            return concl, f"(thales {self.ne(o, a)} {self.ne(o, b)} {pr(A1)} {pr(A2)} {pr(R)} {self.readx('ReadT', o, a, c_, b, e)})"
        if tag == "trapezoid":
            Pa, C1, C2, X = P
            a, b, c_, e = Pa[1:]
            m, q = C1[1], C2[1]
            s = f"{self.ne(a, b)} {self.ne(a, e)} {self.ne(b, c_)} {self.NC(a, b, c_)} {pr(Pa)} {pr(C1)} {pr(C2)}"
            if X[0] == "eqratio":
                return concl, f"(trap_Q {s} {pr(X)} {self.readx('ReadZ', m, a, e, q, b, c_)})"
            return concl, f"(trap_R {s} {pr(X)})"
        if tag == "pyth":
            return concl, f"({'pyth_to' if P[0][0] == 'perp' else 'pyth_of'} {pr(P[0])})"
        if tag == "sq_cong":
            return concl, f"({'sqcong_to' if P[0][0] == 'cong' else 'sqcong_of'} {pr(P[0])})"
        if tag == "median":
            m, a, b, n = self.midp(j, P[0], P[1])
            return concl, f"({'sqmid' if k == 'sqmid' else 'sqmedian'} {n})"
        raise Stop(f"rule {tag}")

    def chords(self, r):
        j, concl = r["j"], r["concl"]
        ch = next((h for h in self.by.get(j, []) if h["fact"][0] == "tdiff"), None)
        if ch is None or len(ch["form"]) != 4:
            raise Stop(f"row {j}: equal chords without four variables")
        (a, ca), (b, cb), (c_, cc), (e, ce) = ch["form"]
        ca, cb, cc, ce = (Fr(x) for x in (ca, cb, cc, ce))
        if abs(ca) != 1 or abs(cc) != 1 or ca != -cb or cc != -ce or len({a[1], b[1], c_[1], e[1]}) != 1:
            raise Stop(f"row {j}: equal chords with coefficients {ca} {cb} {cc} {ce}")
        g = self.groups[a[1]]
        sg = ca
        T = lambda v: f"tz {g['o']} {g['r']} {pt(v[2])}"
        mid = "-" if cc == -ca else "+"
        end = "+" if cc == -ca else "-"
        rows = [(int(i), Fr(co) * sg) for i, co in ch["rows"].items()]
        if any(self.rows[i]["const"] is None for i, _ in rows):
            raise Stop("a constant read from the figure")
        total = sum((co * self.rows[i]["const"] for i, co in rows), Fr(0))
        if total.denominator != 1 or any(co.denominator != 1 for _, co in rows):
            raise Stop(f"row {j}: equal chords with a fractional constant")
        s = None
        for i, co in rows:
            t = f"(ModPi.zmul ({int(co)}) r{i})"
            s = t if s is None else f"(ModPi.add {s} {t})"
        s = f"(ModPi.add {s} (ModPi.int ({int(total)})))"
        name = self.new("d")
        self.line(f"have {name} : ModPi ({T(a)} - {T(b)} {mid} {T(c_)} {end} {T(e)}) := ModPi.congr (by push_cast; ring) {s}")
        lem = "equal_chords1" if cc == -ca else "equal_chords2"
        x = [a[2], b[2], c_[2], e[2]]
        return concl, f"({lem} {g['hr']} {g['on'][x[0]]} {g['on'][x[1]]} {g['on'][x[2]]} {g['on'][x[3]]} {name})"

    def goal(self):
        G = self.c["goal"]
        k = G[0]
        if k == "cyclic":
            for g in self.groups.values():
                if set(G[1:]) <= set(g["on"]) and g.get("named"):
                    return f"⟨{g['o']}, {g['r']}, {g['hr']}, {', '.join(g['on'][x] for x in G[1:])}⟩"
            raise Stop("no circle holds the goal")
        forms = self.by.get(-1, [])
        if not forms:
            raise Stop("goal has no combination")
        self.cache = {}
        if k == "cong" and G[1:3] == G[3:5]:    # a statement whose goal is an identity
            return "rfl"
        if k == "midp":
            m, x, y = G[1:]
            names = {}
            for F in (["coll", m, x, y], ["cong", m, x, m, y]):
                sy, T, cst = self.terms(F)
                want = lin(*[(key(v), Fr(c)) for v, c in form_list(F)])
                for ch in forms:
                    tot = {}
                    for i, co in ch["rows"].items():
                        for v, q in self.rows[int(i)]["rel"].items():
                            tot[v] = tot.get(v, 0) + Fr(co) * q
                    if lin(*tot.items()) == want:
                        names[F[0]] = self.have_fact(F, ch)
                        break
                else:
                    raise Stop(f"midpoint goal without {F[0]}")
            return f"midp_of {self.ne(x, y)} {names['coll']} {names['cong']}"
        for ch in forms:
            if json.dumps(ch["fact"]) == json.dumps(G):
                return self.have_fact(G, ch)
        raise Stop("goal is not what was combined")

    def run(self):
        c = self.c
        rows = used(json.loads(json.dumps(c)))
        need = {r["j"] for r in rows}
        for r in c["rows"]:
            r["rel"] = lin(*[(key(k), Fr(v)) for k, v in r["rel"]])
            r["const"] = self.const_of(r) if r["j"] in need else None
        seen = set()
        for row in c["rows"]:
            if row["j"] not in need:
                continue
            self.cache = {}
            r = row
            k, tag = r["concl"][0], r["tag"]
            if k in ("cyclic", "circle") and tag in ("given", "centre", "centre_cyclic", "inscribed"):
                if r["gid"] not in seen:
                    seen.add(r["gid"])
                    self.make_group(r)
                    self.groups[r["gid"]]["named"] = r["concl"][0] == "cyclic"
                self.group_row(r)
            elif tag == "similar":
                self.similar(r)
            else:
                F, t = self.chords(r) if tag == "equal_chords" else self.rule(r)
                self.row_from(r["j"], F, t)
            if self.lat is not None and r["sys"] == "D":
                self.lift_row(r)
        done = self.goal()
        self.line(f"exact {done}")
        return self.text()

    def const_of(self, r):
        """the constant of a row, computed as the checker does"""
        F, tag = r["concl"], r["tag"]
        if tag == "given" and F[0] == "const":
            return None
        if F[0] in ("cyclic", "circle"):
            return Fr(1, 2) if any(v[0] == "u" and F[0] == "circle" and F[1] in v[1:] and sum(1 for w in r["rel"] if w[0] == "t") == 1 for v in r["rel"]) else Fr(0)
        if F[0] in ("simtri", "simtri2"):
            return Fr(0)
        return form(F)[2]

    def text(self):
        hs, ex = [], []
        for F, n in self.hyps.values():
            k, *a = F
            p = [pt(x) for x in a]
            if k in ("coll", "collx"):
                cs = [f"Coll {p[0]} {p[1]} {x}" for x in p[2:]]
                t = " ∧ ".join(cs)
            elif k == "midp":
                t = f"Midp {' '.join(p)}"
            elif k == "cyclic":
                t = "∃ (o : P) (r : ℝ), 0 < r ∧ " + " ∧ ".join(f"On o r {x}" for x in p)
            elif k == "circle":
                t = " ∧ ".join(f"d2 {p[0]} {p[1]} = d2 {p[0]} {x}" for x in p[2:]) or "True"
            else:
                t = self.prop(F)
            hs.append(f"({n} : {t})")
        for (a, b) in sorted(self.pairs):
            hs.append(f"(n_{pt(a)}_{pt(b)} : {pt(a)} ≠ {pt(b)})")
        for s, n in self.nc.items():
            hs.append(f"({n} : NC {' '.join(pt(x) for x in s)})")
        for k, n in self.reads.items():
            if k[0] in ("Read", "Read2"):
                hs.append(f"({n} : {k[0]} {' '.join(pt(x) for x in k[1])} {' '.join(pt(x) for x in k[2])})")
            else:
                hs.append(f"({n} : {k[0]} {' '.join(pt(x) for x in k[1])})")
        G = self.c["goal"]
        self.points |= set(G[1:])
        if G[0] == "cyclic":
            g = "∃ (o : P) (r : ℝ), 0 < r ∧ " + " ∧ ".join(f"On o r {pt(x)}" for x in G[1:])
        elif G[0] == "midp":
            g = f"Midp {' '.join(pt(x) for x in G[1:])}"
        else:
            g = self.prop(G)
        vs = " ".join(pt(x) for x in sorted(self.points))
        head = f"import {'GeoLift' if self.lat is not None else 'GeoCert'}\nopen GeoCert\n\nset_option maxHeartbeats 4000000 in\ntheorem cert ({vs} : P)\n    " + "\n    ".join(hs) + f" :\n    {g} := by\n"
        return head + "\n".join(self.body) + "\n\n#print axioms cert\n"


def add_vec(*vs):
    r = {}
    for v in vs:
        for k, x in v.items():
            r[k] = r.get(k, 0) + x
    return {k: x for k, x in r.items() if x}


def _nth(h, i, n):
    """part i of a conjunction of n parts"""
    if n == 1:
        return h
    return f"{h}{'.2' * i}{'.1' if i < n - 1 else ''}"


def _perm(n, s, want, f):
    """from the order s to the order want, by swaps of the first two and the last two"""
    s, want = list(s), list(want)
    seen, todo = {tuple(s): n}, [(s, n)]
    while todo:
        cur, t = todo.pop(0)
        if cur == want:
            return t if t == n else f"({t})"
        for i in (0, 1):
            nx = list(cur)
            nx[i], nx[i + 1] = nx[i + 1], nx[i]
            if tuple(nx) not in seen:
                seen[tuple(nx)] = 1
                todo.append((nx, f(t, i)))
    raise Stop("no order")


def _perm2(n, s, want):
    a, b = list(s[0]), list(s[1])
    wa, wb = list(want[0]), list(want[1])
    seen, todo = set(), [(a, b, n)]
    while todo:
        x, y, t = todo.pop(0)
        if x == wa and y == wb:
            return t if t == n else f"({t})"
        for i, nm in ((0, "p12"), (1, "p23")):
            x2, y2 = list(x), list(y)
            x2[i], x2[i + 1] = x2[i + 1], x2[i]
            y2[i], y2[i + 1] = y2[i + 1], y2[i]
            k = (tuple(x2), tuple(y2))
            if k not in seen:
                seen.add(k)
                todo.append((x2, y2, f"{t}.{nm}"))
    raise Stop("no order of the triangles")


def _sw(want, have):
    """d2_comm terms taking the pairs of `have` to those of `want`, for a cong read in another order"""
    out = []
    for (_, x, y), c in want:
        for (_, p, q), c2 in have:
            if (x, y) == (q, p):
                out.append(f"{num(c2)} * d2_comm {pt(p)} {pt(q)}")
    return out


def qform(F):
    k, *a = F
    p = [pt(x) for x in a]
    if k == "sqcong":
        return f"d2 {p[0]} {p[1]} - d2 {p[2]} {p[3]}"
    if k == "sqperp":
        return f"d2 {p[0]} {p[2]} - d2 {p[0]} {p[3]} - d2 {p[1]} {p[2]} + d2 {p[1]} {p[3]}"
    if k == "sqmid":
        return f"d2 {p[1]} {p[2]} - 4 * d2 {p[0]} {p[1]}"
    if k == "sqmedian":
        return f"2 * d2 {p[0]} {p[1]} + 2 * d2 {p[1]} {p[2]} - d2 {p[0]} {p[2]} - d2 {p[0]} {p[3]}"
    raise Stop(f"no square form for {k}")


def form_list(F):
    return list(form(F)[1].items())


def export(path, lift=False):
    c = json.load(open(path))
    w = Writer(c, lift)
    w.cache = {}
    t = w.run()
    export.info = dict(left=len(w.reads), lifted=w.lifted, opposite=w.opposite)
    return t


def main():
    if sys.argv[1] == "all":
        src, out = sys.argv[2:4]
        os.makedirs(out, exist_ok=True)
        with open(f"{out}/export.jsonl", "w") as log:
            for f in sorted(glob.glob(f"{src}/*.json")):
                b = os.path.basename(f).replace(".txt.json", "").replace(".json", "")
                b = re.sub(r"[^A-Za-z0-9_]", "_", b)
                try:
                    t = export(f, "--lift" in sys.argv)
                    open(f"{out}/{b}.lean", "w").write(t)
                    log.write(json.dumps({"file": b, "ok": True, **export.info}) + "\n")
                except (Stop, Bad, KeyError, IndexError, ValueError, TypeError, AttributeError) as e:
                    log.write(json.dumps({"file": b, "ok": False, "why": f"{type(e).__name__}: {e}"}) + "\n")
        return
    open(sys.argv[2], "w").write(export(sys.argv[1]))


if __name__ == "__main__":
    main()
