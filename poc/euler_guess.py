"""Baseline guesser for TABLE-H (PREREG_DIFF, 2026-11-26; written before any table was read). CPU only, no model call.
Input: the brute-force table [n, f(n)] of poc/euler_table.py, the target n and the modulus. Model classes, simplest first, each fitted on the
first two thirds of the longest consecutive run and accepted only if it reproduces every held-out term exactly:
  P  polynomial in n (degree <= 12)
  C  linear recurrence with constant coefficients (rational generating function; Berlekamp-Massey over Q, order <= L/2 of the fit part)
  H  linear recurrence with polynomial coefficients (P-recursive / holonomic; order <= 4, degree <= 4; one-dimensional null space required)
The accepted model is refitted on the whole table and evaluated at the target: P exactly; C by matrix power (mod m when a modulus is given, exactly
when the target is within 10^6 of the table); H by unrolling (mod m, or exactly within 10^5 steps; at most 5*10^6 steps). Larger targets are left
undone (the fast-evaluation algorithms, e.g. baby-step giant-step for P-recursive sequences, are the teammate's part).
usage: python euler_guess.py score [<table files>]   (default: results/x44/eultab_{euler,eulert}_medium_s1.jsonl)"""
import json, os, re, sys, glob, collections
from fractions import Fraction
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE); R = f"{ROOT}/results/x44"


def val(v):
    if isinstance(v, bool):
        raise ValueError
    if isinstance(v, int):
        return Fraction(v)
    if isinstance(v, float):
        raise ValueError("float value")
    return Fraction(str(v).strip())


def intpar(s):
    """'10^12', '10**12', '1e12', '10 000 000', '2·10^7', '$10^{9}$' -> int; NONE -> None"""
    if not s or re.match(r"\s*none", s, re.I):
        return None
    t = re.sub(r"[\s,$\\{}]|\\,|text|mathrm", "", s.split("=")[-1]).replace("**", "^").replace("·", "*").replace("times", "*").replace("cdot", "*")
    m2 = re.match(r"^10\^(\d+)([+-]\d+)?", t)
    if m2:
        return 10 ** int(m2.group(1)) + int(m2.group(2) or 0)
    m = re.match(r"^(\d+(?:\.\d+)?)(?:\*?10\^(\d+)|[eE](\d+))?([+-]\d+)?", t)
    if not m:
        return None
    b = Fraction(m.group(1)) * 10 ** int(m.group(2) or m.group(3) or 0) + int(m.group(4) or 0)
    return int(b) if b.denominator == 1 else None


def run(tab):
    """longest run of consecutive n -> (n0, [values])"""
    pts = {}
    for x in tab:
        try:
            n, v = int(x[0]), val(x[1]); pts[n] = v
        except Exception:
            continue
    best = (None, [])
    for n in sorted(pts):
        if n - 1 in pts:
            continue
        k = n; vs = []
        while k in pts:
            vs.append(pts[k]); k += 1
        if len(vs) > len(best[1]):
            best = (n, vs)
    return best


def rref(M):
    """reduced row echelon form over Q (pure Fraction; sympy was too slow on long tables, 11-26 19:4x) -> (rows, pivot columns)"""
    M = [[Fraction(x) for x in r] for r in M]; piv = []; r = 0; ncol = len(M[0]) if M else 0
    for c in range(ncol):
        k = next((i for i in range(r, len(M)) if M[i][c] != 0), None)
        if k is None:
            continue
        M[r], M[k] = M[k], M[r]; pv = M[r][c]; M[r] = [x / pv for x in M[r]]
        for i in range(len(M)):
            if i != r and M[i][c] != 0:
                f = M[i][c]; M[i] = [x - f * y for x, y in zip(M[i], M[r])]
        piv.append(c); r += 1
        if r == len(M):
            break
    return M[:r], piv


def solve_lin(A, b):
    """A x = b, overdetermined and consistent, unique solution; else None"""
    n = len(A[0]); R, piv = rref([list(r) + [y] for r, y in zip(A, b)])
    if n in piv or len(piv) != n:
        return None
    return [R[i][n] for i in range(n)]


def nullspace1(M):
    """the null space vector if the null space is one-dimensional (integers, primitive), else None"""
    n = len(M[0]); R, piv = rref(M); free = [c for c in range(n) if c not in piv]
    if len(free) != 1:
        return None
    x = [Fraction(0)] * n; x[free[0]] = Fraction(1)
    for i, c in enumerate(piv):
        x[c] = -R[i][free[0]]
    import math
    L = 1
    for t in x:
        L = L * t.denominator // math.gcd(L, t.denominator)
    return [t * L for t in x]


def fit_poly(n0, v, deg):
    A = [[Fraction(n0 + i) ** j for j in range(deg + 1)] for i in range(len(v))]
    return solve_lin(A, v)


def ev_poly(c, n):
    return sum(ci * Fraction(n) ** j for j, ci in enumerate(c))


def fit_const(v, order):
    """f(n+order) = sum_{i<order} c_i f(n+i) on all consecutive windows"""
    rows = [[v[k + i] for i in range(order)] for k in range(len(v) - order)]; b = [v[k + order] for k in range(len(v) - order)]
    if len(rows) < order + 2:
        return None
    return solve_lin(rows, b)


def fit_holo(n0, v, order, deg):
    rows = []
    for k in range(len(v) - order):
        n = Fraction(n0 + k); rows.append([n ** j * v[k + i] for i in range(order + 1) for j in range(deg + 1)])
    u = (order + 1) * (deg + 1)
    if len(rows) < u + 2:
        return None
    x = nullspace1(rows)
    if x is None:
        return None
    return [[x[i * (deg + 1) + j] for j in range(deg + 1)] for i in range(order + 1)]


def holo_step(c, n, prev, mod=None):
    """next value from prev = [f(n), ..., f(n+r-1)]"""
    r = len(c) - 1; p = [sum(cij * n ** j for j, cij in enumerate(ci)) for ci in c]
    if mod is None:
        if p[r] == 0:
            raise ZeroDivisionError
        return -sum(p[i] * prev[i] for i in range(r)) / p[r]
    pm = [int(x.numerator * pow(x.denominator, -1, mod)) % mod for x in map(Fraction, p)]
    inv = pow(pm[r], -1, mod)
    return (-sum(pm[i] * prev[i] for i in range(r)) * inv) % mod


def check(model, n0, v, k0):
    """does the model fitted on v[:k0] reproduce v[k0:]?"""
    kind, c = model
    try:
        if kind == "P":
            return all(ev_poly(c, n0 + i) == v[i] for i in range(len(v)))
        if kind == "C":
            r = len(c); w = list(v[:r])
            for i in range(r, len(v)):
                w.append(sum(c[j] * w[i - r + j] for j in range(r)))
            return w == list(v)
        r = len(c) - 1; w = list(v[:r])
        for i in range(r, len(v)):
            w.append(holo_step(c, Fraction(n0 + i - r), w[i - r:i]))
        return w == list(v)
    except (ZeroDivisionError, ValueError):
        return False


def guess(n0, v):
    """-> (kind, coefficients on the whole table) or None; simplest accepted class first"""
    v = v[:int(os.environ.get("GUESS_MAXTERMS", 64))]       # the first 64 terms (speed; registered before any guesser output was read)
    L = len(v); k = (2 * L) // 3
    if L < 8:
        return None
    fit, hold = v[:k], v[k:]
    for deg in range(0, min(12, k - 3) + 1):
        c = fit_poly(n0, fit, deg)
        if c is not None and check(("P", c), n0, v, k):
            return ("P", fit_poly(n0, v, deg))
    for order in range(1, k // 2):
        c = fit_const(fit, order)
        if c is not None and check(("C", c), n0, v, k):
            return ("C", fit_const(v, order))
    for order in range(1, 5):
        for deg in range(0, 5):
            if (order + 1) * (deg + 1) + 2 > k - order:
                continue
            c = fit_holo(n0, fit, order, deg)
            if c is not None and check(("H", c), n0, v, k):
                cc = fit_holo(n0, v, order, deg)
                return ("H", cc if cc is not None else c)
    return None


def evaluate(model, n0, v, N, mod):
    kind, c = model; last = n0 + len(v) - 1
    if N is None:
        return None, "no target"
    if n0 <= N <= last:
        x = v[N - n0]; return (x % mod if mod and x.denominator == 1 else x), "in table"
    if N < n0:
        return None, "target below table"
    if kind == "P":
        x = ev_poly(c, N); return (x % mod if mod and x.denominator == 1 else x), "poly"
    if kind == "C":
        r = len(c); steps = N - last
        if mod is None:
            if steps > 10 ** 6:
                return None, "C exact too far"
            w = list(v[-r:])
            for _ in range(steps):
                w = w[1:] + [sum(c[j] * w[j] for j in range(r))]
            return w[-1], "C exact"
        try:
            cm = [int(x.numerator * pow(x.denominator, -1, mod)) % mod for x in c]; w = [int(x.numerator * pow(x.denominator, -1, mod)) % mod for x in v[-r:]]
        except ValueError:
            return None, "C not invertible mod m"
        # companion matrix power
        M = [[0] * r for _ in range(r)]
        for i in range(r - 1):
            M[i][i + 1] = 1
        M[r - 1] = cm[:]
        def mul(A, B):
            return [[sum(A[i][t] * B[t][j] for t in range(r)) % mod for j in range(r)] for i in range(r)]
        P = [[int(i == j) for j in range(r)] for i in range(r)]; e = steps; B = M
        while e:
            if e & 1:
                P = mul(P, B)
            B = mul(B, B); e >>= 1
        return sum(P[r - 1][j] * w[j] for j in range(r)) % mod, "C matrix power"
    r = len(c) - 1; steps = N - last
    if steps > 5 * 10 ** 6 or (mod is None and steps > 10 ** 5):
        return None, "H too far"
    try:
        w = list(v[-r:]) if mod is None else [int(x.numerator * pow(x.denominator, -1, mod)) % mod for x in v[-r:]]
        n = last - r + 1
        for _ in range(steps):
            w = w[1:] + [holo_step(c, Fraction(n) if mod is None else n, w, mod)]; n += 1
    except (ZeroDivisionError, ValueError):
        return None, "H singular"
    return w[-1], "H unrolled"


def right(x, gold):
    if x is None:
        return False
    g = str(gold).strip().replace(",", "")
    try:
        if "." in g:
            d = len(g.split(".")[1]); return abs(float(x) - float(g)) <= 0.5 * 10 ** -d + 1e-12
        return x == Fraction(int(g))
    except Exception:
        return False


def never_right():
    """problems never right in the stored medium tool attempts (the headroom table of 11-26 16:25)"""
    import ma_effort as M, run_compute as RC
    out = {}
    for st in ("euler", "eulert"):
        c = collections.defaultdict(list); g = {p["id"]: p["answer"] for p in RC.problems(st)}
        for f in glob.glob(f"{R}/tir_{st}_medium*_s*.jsonl") + glob.glob(f"{R}/tirfb_{st}_medium_s*.jsonl"):
            seen = set()
            for l in open(f):
                r = json.loads(l)
                if r["id"] not in seen:
                    a = M.ans(r.get("final", "")) or ""; seen.add(r["id"]); c[r["id"]].append(bool(a) and RC.norm(a) == RC.norm(g[r["id"]]))   # the corrected reader (tir_score.regrade)
        out[st] = {k for k, v in c.items() if not any(v)}
    return out


def score(files):
    import run_compute as RC
    NR = never_right()
    for f in files:
        st = os.path.basename(f).split("_")[1]; gold = {p["id"]: p["answer"] for p in RC.problems(st)}
        Z = [json.loads(l) for l in open(f)]; C = collections.Counter(); acc = []
        for z in Z:
            tab = z.get("table")
            if not isinstance(tab, list):
                C["no table"] += 1; continue
            n0, v = run(tab)
            if len(v) < 8:
                C["table < 8 consecutive"] += 1; continue
            m = guess(n0, v)
            if m is None:
                C["no model accepted"] += 1; continue
            if len(v) > 64 and not check(m, n0, v, 0):            # terms beyond the 64 used must also be reproduced
                C["rejected by terms beyond 64"] += 1; continue
            N, mod = intpar(z.get("target", "")), intpar(z.get("modulus", ""))
            x, how = evaluate(m, n0, v, N, mod)
            if x is None:
                C["accepted, not evaluated: " + how] += 1; continue
            ok = right(x, gold[z["id"]]); acc.append((z["id"], m[0], how, ok)); C[f"answered ({m[0]})"] += 1
        nr = NR.get(st, set()); n = len(Z)
        print(f"== {os.path.basename(f)}: {n} problems; tokens {sum(z.get('out_tokens', 0) for z in Z)/max(1,n)/1000:.2f}k; {dict(C)}")
        print(f"   answered {len(acc)}, right {sum(a[3] for a in acc)} (precision {100*sum(a[3] for a in acc)/max(1,len(acc)):.0f}%); "
              f"on the {len(nr)} never-right problems: answered {sum(a[0] in nr for a in acc)}, right {sum(a[3] and a[0] in nr for a in acc)}")
        for a in sorted(acc):
            print("   ", a, "never-right" if a[0] in nr else "")


if __name__ == "__main__":
    if sys.argv[1] == "selftest":
        tests = [("fib", 1, [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144], 50, None, 12586269025), ("cubes-sum", 1, [sum(k ** 3 for k in range(1, n + 1)) for n in range(1, 16)], 10 ** 6, 10 ** 9 + 7, (10 ** 6 * (10 ** 6 + 1) // 2) ** 2 % (10 ** 9 + 7)),
                 ("catalan", 0, [1, 1, 2, 5, 14, 42, 132, 429, 1430, 4862, 16796, 58786, 208012, 742900, 2674440, 9694845, 35357670, 129644790, 477638700, 1767263190, 6564120420, 24466267020], 30, None, 3814986502092304),
                 ("n!", 1, [1, 2, 6, 24, 120, 720, 5040, 40320, 362880, 3628800, 39916800, 479001600, 6227020800, 87178291200], 1000, 10 ** 9 + 7, None)]
        import math
        for name, n0, v, N, mod, want in tests:
            m = guess(n0, [Fraction(x) for x in v]); x, how = evaluate(m, n0, [Fraction(x) for x in v], N, mod) if m else (None, "none")
            want = want if want is not None else math.factorial(N) % mod
            print(name, m[0] if m else None, how, x, x == want)
        print(intpar("N = 10^{12}"), intpar("10**12"), intpar("1e12"), intpar("10 000 000"), intpar("2\\cdot10^7"), intpar("1 000 000 007"), intpar("NONE"))
    else:
        score(sys.argv[2:] or [f"{R}/eultab_{s}_medium_s1.jsonl" for s in ("euler", "eulert")])
