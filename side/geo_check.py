"""A small independent checker for closure proofs (SIDE-GT-CHECK). It imports nothing from the engine and uses exact fractions. A certificate from
`geo_closure.py cert` lists the construction's facts and, row by row, a rule, its premises, its conclusion and the linear relation the rule adds. Three things are checked:
  1. the relation is exactly what the rule's conclusion says, including its constant (0 or π/2 for directions, a multiple of log 2 for log lengths);
  2. the premises and the conclusion fit the rule's statement;
  3. every premise, and the goal, is an exact linear combination of earlier rows, with its constant, integer for directions.
What it does not check is listed in each result: non-degeneracy, and the rules that read a configuration from the figure (`config`).
  python side/geo_check.py <cert.json> ...
"""
import json, sys
from fractions import Fraction as Fr


def def_facts(nm, c):
    """what an auxiliary point's construction gives, from its statement alone"""
    k, *a = [q for q in c.split() if q != "aux"]
    if k == "midpoint":
        return [["midp", nm, a[0], a[1]]]
    if k == "mirror":
        return [["midp", a[1], a[0], nm]]
    if k == "circle":
        return [["circle", nm, *a]]
    if k == "foot":
        return [["coll", nm, a[1], a[2]], ["perp", nm, a[0], a[1], a[2]]]
    if k == "reflect":
        return [["perp", nm, a[0], a[1], a[2]], ["cong", a[1], a[0], a[1], nm], ["cong", a[2], a[0], a[2], nm]]
    if k == "intersection_ll":
        return [["coll", nm, a[0], a[1]], ["coll", nm, a[2], a[3]]]
    if k == "second_lc":
        return [["coll", nm, a[0], a[1]], ["cyclic", nm, a[0], a[2], a[3]]]
    if k == "second_cc":
        return [["cyclic", nm, a[0], a[1], a[2]], ["cyclic", nm, a[0], a[3], a[4]]]
    raise Bad(f"unknown construction {k}")



class Bad(Exception):
    pass


def pair(k, a, b):
    if a == b:
        raise Bad(f"degenerate {k} {a} {b}")
    return (k, min(a, b), max(a, b))


def lin(*terms):
    out = {}
    for v, c in terms:
        out[v] = out.get(v, 0) + c
    return {v: c for v, c in out.items() if c}


def u(a, b):
    return pair("u", a, b)


def w(a, b):
    return pair("w", a, b)


def s(a, b):
    return pair("s", a, b)


def form(F):
    """a fact -> system, linear form, constant: the form equals the constant (units of π mod 1 for directions, of log 2 for log lengths)"""
    k, *a = F
    if k == "coll":
        if len(a) == 3:
            return "D", lin((u(a[0], a[1]), 1), (u(a[0], a[2]), -1)), Fr(0)
        return "D", lin((u(a[0], a[1]), 1), (u(a[2], a[3]), -1)), Fr(0)
    if k == "para":
        return "D", lin((u(a[0], a[1]), 1), (u(a[2], a[3]), -1)), Fr(0)
    if k == "perp":
        return "D", lin((u(a[0], a[1]), 1), (u(a[2], a[3]), -1)), Fr(1, 2)
    if k == "eqangle":
        return "D", lin((u(a[0], a[1]), 1), (u(a[2], a[3]), -1), (u(a[4], a[5]), -1), (u(a[6], a[7]), 1)), Fr(0)
    if k == "cong":
        return "W", lin((w(a[0], a[1]), 1), (w(a[2], a[3]), -1)), Fr(0)
    if k == "eqratio":
        return "W", lin((w(a[0], a[1]), 1), (w(a[2], a[3]), -1), (w(a[4], a[5]), -1), (w(a[6], a[7]), 1)), Fr(0)
    if k == "half":
        return "W", lin((w(a[0], a[1]), 1), (w(a[2], a[3]), -1)), Fr(1)
    if k == "sqcong":
        return "Q", lin((s(a[0], a[1]), 1), (s(a[2], a[3]), -1)), Fr(0)
    if k == "sqperp":
        t = [(s(x, y), c) for x, y, c in ((a[0], a[2], 1), (a[0], a[3], -1), (a[1], a[2], -1), (a[1], a[3], 1)) if x != y]
        return "Q", lin(*t), Fr(0)
    if k == "sqmid":
        return "Q", lin((s(a[1], a[2]), 1), (s(a[0], a[1]), -4)), Fr(0)
    if k == "sqmedian":
        return "Q", lin((s(a[0], a[1]), 2), (s(a[1], a[2]), 2), (s(a[0], a[2]), -1), (s(a[0], a[3]), -1)), Fr(0)
    raise Bad(f"no form for {k}")


def sim_rows(F):
    """the four relations two similar triangles give, as in the statement: two angles and two ratios"""
    k, a, b, c, p, q, r = F
    o = k == "simtri"
    sg = -1 if o else 1
    out = []
    for (x, y, z), (x2, y2, z2) in (((a, b, c), (p, q, r)), ((b, a, c), (q, p, r))):
        out.append(("D", lin((u(x, y), 1), (u(x, z), -1), (u(x2, y2), sg), (u(x2, z2), -sg)), Fr(0)))
    for x, y, x2, y2 in ((b, c, q, r), (c, a, r, p)):
        out.append(("W", lin((w(a, b), 1), (w(p, q), -1), (w(x, y), -1), (w(x2, y2), 1)), Fr(0)))
    return out


def key(k):
    return pair(*k) if k[0] != "t" else tuple(k)


def same(a, b):
    return lin(*a.items()) == lin(*b.items())


def eq_rel(row, sy, f, c=None):
    if row["sys"] != sy or not same(row["rel"], f):
        raise Bad(f"row {row['j']}: relation is not the conclusion's")
    row["const"] = row["const"] if c is None else c


def mp(F1, F2):
    """(coll m a b), (cong m a m b) -> m, a, b"""
    if F1[0] != "coll" or F2[0] != "cong" or F1[1] != F2[1] or F2[1] != F2[3] or {F1[2], F1[3]} != {F2[2], F2[4]} or len(F1) != 4:
        raise Bad(f"not a midpoint: {F1} {F2}")
    return F1[1], F2[2], F2[4]


def given_ok(F, facts):
    """the row's fact follows at once from one of the construction's facts"""
    k, *a = F
    for g in facts:
        h, *b = g
        if k == "coll" and h in ("coll", "collx") and set(a) <= set(b):
            return True
        if k == "coll" and h == "midp" and set(a) <= set(b):
            return True
        if k == "cong" and h == "cong" and (sorted([sorted(a[:2]), sorted(a[2:])]) == sorted([sorted(b[:2]), sorted(b[2:])])):
            return True
        if k == "cong" and h == "circle" and a[0] == b[0] == a[2] and {a[1], a[3]} <= set(b[1:]):
            return True
        if k == "cong" and h == "midp" and a[0] == b[0] == a[2] and {a[1], a[3]} == set(b[1:]):
            return True
        if k == h and list(a) == list(b):
            return True
        if k in ("simtri", "simtri2") and h in (k, k.replace("simtri", "contri")) and a == b:
            return True
        if k == "cong" and h in ("contri", "contri2") and a == [b[0], b[1], b[3], b[4]]:
            return True
    return False


def check(c):
    facts, rows, chases, goal = c["facts"], c["rows"], c["chases"], c["goal"]
    names = {nm for nm, _ in c["defs"]}
    allowed = [f for nm, d in c["defs"] for f in def_facts(nm, d)]
    for f in facts:     # a fact about an auxiliary point must be what its construction states; the statement's own facts come from its construction language
        if names & set(f[1:]) and f not in allowed:
            raise Bad(f"fact {f} is not what the construction gives")
    by = {}
    for ch in chases:
        by.setdefault(ch["ctx"], []).append(ch)
    seen, groups, stats, group_of = {}, {}, {"rows": len(rows), "config": {}, "figure_constants": 0, "fractional_directions": 0}, {}

    def tick(n):
        stats["config"][n] = stats["config"].get(n, 0) + 1

    def verify(ch, j):
        sy, f, cst = form(ch["fact"]) if ch["fact"][0] != "tdiff" else ("D", lin(*[(key(k), v) for k, v in ch["form"]]), Fr(0))
        if ch["fact"][0] == "midp":
            raise Bad("midp form")
        total, const, fig = {}, Fr(0), False
        for i, co in ch["rows"].items():
            i = int(i)
            co = Fr(co)
            if i not in seen or i >= j:
                raise Bad(f"row {j}: premise uses row {i} before it")
            r = seen[i]
            if r["sys"] != sy:
                raise Bad(f"row {j}: premise in {sy} uses row {i} in {r['sys']}")
            if sy == "D" and co.denominator != 1:
                stats["fractional_directions"] += 1
            for v, q in r["rel"].items():
                total[v] = total.get(v, 0) + co * q
            if r["const"] is None:
                fig = True
            else:
                const += co * r["const"]
        if not same(total, f):
            raise Bad(f"row {j}: premise {ch['fact']} is not the combination given")
        if fig:
            stats["figure_constants"] += 1
        elif sy == "D" and (const - cst) % 1:
            raise Bad(f"row {j}: premise {ch['fact']} has constant {const}, not {cst}")
        elif sy != "D" and const != cst:
            raise Bad(f"row {j}: premise {ch['fact']} has constant {const}, not {cst}")

    def expand(prem):
        """a premise midp stands for its coll and cong"""
        out = []
        for F in prem:
            out += [("coll", F[1], F[2], F[3]), ("cong", F[1], F[2], F[1], F[3])] if F[0] == "midp" else [F]
        return out

    for row in rows:
        j, tag, prem, concl = row["j"], row["tag"], [list(x) for x in row["prem"]], list(row["concl"])
        row["rel"] = lin(*[(key(k), Fr(v)) for k, v in row["rel"]])
        row["const"] = Fr(0)
        k = concl[0]
        real = [F for F in prem if F[0] != "cyclic_group"]
        for ch in by.get(j, []):
            verify(ch, j)
        want = [F for F in expand(real) if F[0] not in ("half_", "cyclic")]
        got = {json.dumps(ch["fact"]) for ch in by.get(j, [])}
        for F in want:
            if json.dumps(F) not in got:
                raise Bad(f"row {j}: premise {F} has no combination")
        if k in ("cyclic", "circle") and tag in ("given", "centre", "centre_cyclic", "inscribed"):
            pts = set(concl[2:]) if k == "circle" else set(concl[1:])
            centre = concl[1] if k == "circle" else None
            gid = row["gid"]
            if gid not in groups:
                base = set()
                for F in prem:
                    if F[0] == "cyclic_group":
                        g = groups.get(F[1])
                        if g is None or g["centre"] != centre:
                            raise Bad(f"row {j}: group {F[1]} unknown")
                        base |= g["pts"]
                if tag == "given":
                    if not any((g[0] == "cyclic" and set(g[1:]) | base >= pts and len(set(g[1:]) & base) >= (3 if base else 0)) or (g[0] == "cyclic" and pts == set(g[1:]) | base) for g in facts):
                        raise Bad(f"row {j}: cyclic not from the construction")
                elif tag == "inscribed":
                    F = real[0]
                    if F[0] != "eqangle" or F[1] != F[3] or F[5] != F[7] or F[2] != F[6] or F[4] != F[8] or F[1] == F[5]:
                        raise Bad(f"row {j}: not an inscribed angle {F}")
                    q = {F[1], F[5], F[2], F[4]}
                    if len(q) != 4 or pts != q | base or (base and len(q & base) < 3):
                        raise Bad(f"row {j}: inscribed points {pts} from {q}, {base}")
                else:   # equal distances from one centre
                    o, ends = None, set()
                    for F in real:
                        if F[0] != "cong" or F[1] != F[3] or (o and F[1] != o):
                            raise Bad(f"row {j}: not equal radii {F}")
                        o = F[1]
                        ends |= {F[2], F[4]}
                    if pts != ends | base or (centre is not None and centre != o):
                        raise Bad(f"row {j}: radii give {ends}, not {pts}")
                groups[gid] = {"pts": pts, "centre": centre}
            g = groups[gid]
            if g["pts"] != pts or g["centre"] != centre:
                raise Bad(f"row {j}: group changed")
            t = lambda x: ("t", gid, x)
            r = row["rel"]
            ok = False
            for x in pts:
                for y in pts:
                    if x < y and row["sys"] == "D" and same(r, lin((u(x, y), 1), (t(x), -1), (t(y), -1))):
                        ok, row["const"] = True, Fr(0)
                if centre is not None and same(r, lin((u(centre, x), 1), (t(x), -2))):
                    ok, row["const"] = True, Fr(1, 2)
            if not ok and tag == "given" and centre is not None:
                raise Bad(f"row {j}: not a chord")
            if not ok:
                raise Bad(f"row {j}: not a chord or radius of the group")
        elif tag == "given":
            if k == "const":
                row["const"] = None
            else:
                if not given_ok(concl, facts):
                    raise Bad(f"row {j}: {concl} is not in the construction")
                if k in ("simtri", "simtri2"):
                    if not any(row["sys"] == a and same(row["rel"], b) for a, b, _ in sim_rows(concl)):
                        raise Bad(f"row {j}: not a relation of the similar pair")
                else:
                    sy, f, cst = form(concl)
                    eq_rel(row, sy, f, cst)
        elif tag == "similar":
            if not any(row["sys"] == a and same(row["rel"], b) for a, b, _ in sim_rows(concl)):
                raise Bad(f"row {j}: not a relation of the similar pair")
            a, b, c_, p, q, r = concl[1:]
            o = k == "simtri"
            aa = lambda x, y, z, x2, y2, z2: ["eqangle", x, y, x, z, x2, y2, x2, z2] if o else ["eqangle", x, y, x, z, x2, z2, x2, y2]
            A, B, C = aa(a, b, c_, p, q, r), aa(b, a, c_, q, p, r), aa(c_, a, b, r, p, q)
            rr = lambda x, y, x2, y2, e, f, e2, f2: ["eqratio", x, y, x2, y2, e, f, e2, f2]
            R12, R13, R23 = rr(a, b, p, q, b, c_, q, r), rr(a, b, p, q, c_, a, r, p), rr(b, c_, q, r, c_, a, r, p)
            n = sum(F in (A, B, C) for F in real)
            if n == 2 and len(real) == 2:
                pass        # two directed angles: no branch
            elif real == [R12, R13]:
                tick("similar_sss")
            elif real in ([R12, B], [R23, C], [R13, A]):
                tick("similar_sas")
            else:
                raise Bad(f"row {j}: premises do not give the similar pair: {real}")
        else:
            sy, f, cst = form(concl) if k not in ("simtri", "simtri2") else (None, None, None)
            eq_rel(row, sy, f, cst)
            P = real
            ok = False
            if tag == "isosceles":
                x, y, o, _x, o2, _y, *_ = concl[1:] + [None] * 8
                ok = len(P) == 1 and P[0][0] == "cong" and P[0][1] == P[0][3] == concl[3] == concl[5] and concl[1:3] == concl[7:9] and {P[0][2], P[0][4]} == {concl[1], concl[2]} and {concl[4], concl[6]} == {concl[1], concl[2]}
            elif tag == "base_angles":
                F = P[0]
                ok = len(P) == 1 and F[0] == "eqangle" and F[1:3] == F[7:9] and F[3] == F[5] == concl[1] == concl[3] and {F[4], F[6]} == {F[1], F[2]} == {concl[2], concl[4]}
            elif tag == "perp_bisector":
                ok = len(P) == 2 and all(F[0] == "cong" and F[1] == F[3] for F in P) and {P[0][2], P[0][4]} == {P[1][2], P[1][4]} == {concl[1], concl[2]} and {P[0][1], P[1][1]} == {concl[3], concl[4]}
            elif tag == "line":
                groups_ = []
                for F in P:
                    if F[0] != "para" or len({F[1], F[2], F[3], F[4]}) != 3 or not ({F[1], F[2]} & {F[3], F[4]}):
                        raise Bad(f"row {j}: not a collinear triple {F}")
                    new = {F[1], F[2], F[3], F[4]}
                    for t in [t for t in groups_ if len(t & new) >= 2]:
                        new |= t
                        groups_.remove(t)
                    groups_.append(new)
                ok = any(set(concl[1:]) <= t for t in groups_)
            elif tag == "midp_half":
                m, a, b = mp(P[0], P[1])
                ok = concl[1:] == [a, b, m, a]
            elif tag == "midline":
                m1, a1, b1 = mp(P[0], P[1])
                m2, a2, c2 = mp(P[2], P[3])
                ok = a1 == a2 and concl[1:] == [m1, m2, b1, c2]
            elif tag == "parallelogram" and len(P) == 4:
                m, a, b = mp(P[0], P[1])
                m2, c_, e = mp(P[2], P[3])
                ok = m == m2 and concl[1:] in ([a, c_, b, e], [a, e, b, c_])
            elif tag == "parallelogram_mid":
                m, a, b = mp(P[0], P[1])
                c_, e = P[2][2], P[3][2]
                ok = P[2] == ["para", a, c_, b, P[2][4]] and P[3] == ["para", a, P[3][2], b, P[3][4]] and (concl[1:] in ([m, P[2][2], m, P[3][2]],) or k in ("coll", "cong"))
                ok = ok and concl[1] == m and {concl[2], concl[-1]} == {P[2][2], P[3][2]}
            elif tag == "right_median":
                m, a, b = mp(P[0], P[1])
                F = P[2]
                ok = F[0] == "perp" and F[1] == a and F[2] == F[3] and F[4] == b and concl[1:] == [m, a, m, F[2]]
            elif tag == "mid_perp":
                m, a, b = mp(P[0], P[1])
                F = P[2]
                ok = F[0] == "perp" and F[2] == m and F[3:] == [a, b] and concl[1:] == [F[1], a, F[1], b]
            elif tag == "chord_mid":
                F, G, H = P
                ok = F[0] == "cong" and F[1] == F[3] and G[0] == "coll" and H[0] == "perp" and H[1] == F[1] and H[2] == G[1] and {H[3], H[4]} == {F[2], F[4]} == {G[2], G[3]} and concl[1] == concl[3] == G[1]
            elif tag == "equal_chords":
                ch = next((h for h in by.get(j, []) if h["fact"][0] == "tdiff"), None)
                if ch and len(ch["form"]) == 4:
                    (a, ca), (b, cb), (c_, cc), (e, ce) = ch["form"]
                    ok = all(q[0] == "t" and q[1] == a[1] for q in (a, b, c_, e)) and ca == -cb and cc == -ce and concl[1:] == [a[2], b[2], c_[2], e[2]]
            elif tag == "bisector":
                Co, F = P
                e, b, c_ = Co[1:]
                a = F[5] if F[0] == "eqratio" else F[1]
                R, A = ["eqratio", e, b, e, c_, a, b, a, c_], ["eqangle", a, b, a, e, a, e, a, c_]
                ok = Co[0] == "coll" and (F, concl) in ((R, A), (A, R))
            elif tag == "thales":
                A1, A2, R = P
                o, a, c_ = A1[1:]
                o2, b, e = A2[1:]
                ok = o == o2 and A1[0] == A2[0] == "coll" and R == ["eqratio", o, a, a, c_, o, b, b, e] and concl == ["para", a, b, c_, e]
                tick(tag)
            elif tag == "trapezoid":
                Pa, C1, C2, X = P
                a, b, c_, e = Pa[1:]
                m, k = C1[1], C2[1]
                R, Q = ["eqratio", m, a, m, e, k, b, k, c_], ["para", m, k, a, b]
                ok = Pa[0] == "para" and C1 == ["coll", m, a, e] and C2 == ["coll", k, b, c_] and (X, concl) in ((R, Q), (Q, R))
                tick(tag)
            elif tag == "pyth":
                ok = len(P) == 1 and ((P[0][0] == "perp" and concl == ["sqperp"] + P[0][1:]) or (P[0][0] == "sqperp" and concl == ["perp"] + P[0][1:]))
            elif tag == "sq_cong":
                ok = len(P) == 1 and ((P[0][0] == "cong" and concl == ["sqcong"] + P[0][1:]) or (P[0][0] == "sqcong" and concl == ["cong"] + P[0][1:]))
            elif tag == "median":
                m, a, b = mp(P[0], P[1])
                ok = concl == ["sqmid", m, a, b] or concl == ["sqmedian", concl[1], m, a, b]
            if not ok:
                raise Bad(f"row {j}: {tag} does not give {concl} from {P}")
        seen[j] = row
    # the goal
    if goal[0] == "cyclic":
        if not any(g["centre"] is None and set(goal[1:]) <= g["pts"] for g in groups.values()) and len(goal) > 4:
            raise Bad("goal: no group holds the points")
    else:
        forms = by.get(-1, [])
        if not forms:
            raise Bad("goal has no combination")
        for ch in forms:
            verify(ch, 10 ** 9)
        if json.dumps(goal) not in {json.dumps(ch["fact"]) for ch in forms} and goal[0] != "midp":
            raise Bad(f"goal {goal} is not what was combined")
    return stats


def main():
    for fn in sys.argv[1:]:
        c = json.load(open(fn))
        try:
            print(json.dumps({"file": fn, "ok": True, **check(c)}))
        except Bad as e:
            print(json.dumps({"file": fn, "ok": False, "why": str(e)}))
        except Exception as e:
            print(json.dumps({"file": fn, "ok": False, "why": f"{type(e).__name__}: {e}"}))


if __name__ == "__main__":
    main()
