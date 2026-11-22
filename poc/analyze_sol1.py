"""SOL-1 headroom (LOOP §2, 2026-11-21; exploratory, decides only whether SOL-1 gets registered): the model writes brute(n) for the
problem's main size parameter (run_compute.py mode brutef); a fixed guesser fits a structure to brute(0..k) and extrapolates to ASKED.
Families, fewest free parameters first; a fit counts only if it has >= 3 more equations than unknowns (held-out values it must match):
  poly   a(n) polynomial in n of degree <= 12 (finite differences)
  lin    a(n) = sum_{i<=d} c_i a(n-i) + c_0, constant rational coefficients, d <= 10
  prec   sum_{i=0..d} p_i(n) a(n-i) = 0 with deg p_i <= e, d <= 3, e <= 3 (P-recursive; p_0 monic of degree g <= e)
The free check before extrapolating: the statement's own small cases (CHECKS) must equal brute's values where both exist.
Extrapolation: poly exactly; lin / prec by iteration (exactly, or modulo MOD when the problem asks for one and ASKED > 5000; exact iteration beyond 5000 steps is not attempted: 11-21 one row ran 13 h); lin with
ASKED > 10^6 by companion-matrix power modulo MOD. Graded against the stored gold with run_compute's norm.
usage: python3 poc/analyze_sol1.py <tag> [<tag> ...]     (rows: results/x44/euler_<tag>_brutef_s*.jsonl)"""
import glob
import json
import os
import re
import signal
import sys
from fractions import Fraction as F

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "x44")
norm = lambda s: re.sub(r"[\s,]", "", str(s or "")).rstrip(".").lstrip("+")


def ints(vals):
    """longest run of integer values starting at the first integer one -> (start n, values)"""
    out, start = [], None
    for n, v in enumerate(vals or []):
        try:
            x = int(v) if re.fullmatch(r"-?\d+", str(v)) else (int(F(str(v))) if re.fullmatch(r"-?\d+/1", str(v)) else None)
        except (ValueError, ZeroDivisionError):
            x = None
        if x is None:
            if start is not None:
                break
            continue
        if start is None:
            start = n
        out.append(x)
    return start, out


def solve(A, b):
    """exact least-squares-free solve: a solution of A x = b over Q if the system is consistent, else None"""
    n = len(A[0]); M = [[F(v) for v in r] + [F(y)] for r, y in zip(A, b)]; piv = []; r = 0
    for c in range(n):
        p = next((i for i in range(r, len(M)) if M[i][c] != 0), None)
        if p is None:
            continue
        M[r], M[p] = M[p], M[r]; inv = 1 / M[r][c]; M[r] = [x * inv for x in M[r]]
        for i in range(len(M)):
            if i != r and M[i][c] != 0:
                f = M[i][c]; M[i] = [x - f * y for x, y in zip(M[i], M[r])]
        piv.append(c); r += 1
    if any(all(x == 0 for x in row[:-1]) and row[-1] != 0 for row in M):
        return None
    x = [F(0)] * n
    for i, c in enumerate(piv):
        x[c] = M[i][-1]
    return x


def fit(n0, a):
    k = len(a)
    for deg in range(0, 13):                                    # poly: unknowns deg+1, equations k
        if k < deg + 1 + 3:
            break
        c = solve([[F(n0 + i) ** j for j in range(deg + 1)] for i in range(k)], a)
        if c is not None:
            return ("poly", deg, c)
    for d in range(1, 11):                                      # lin: unknowns d+1, equations k-d
        if k - d < d + 1 + 3:
            break
        c = solve([[a[i - j] for j in range(1, d + 1)] + [1] for i in range(d, k)], a[d:])
        if c is not None:
            return ("lin", d, c)
    for d in range(1, 4):                                       # prec: p_0 = n^g + lower (g <= e), p_t of degree <= e; unknowns g + d(e+1)
        for e, g in [(e, g) for e in range(0, 4) for g in range(e + 1)]:
            u = g + d * (e + 1)
            if k - d < u + 3:
                continue
            rows, rhs = [], []
            for i in range(d, k):
                n = n0 + i
                row = [F(n) ** j * a[i] for j in range(g)]      # p_0's lower coefficients
                row += [F(n) ** j * a[i - t] for t in range(1, d + 1) for j in range(e + 1)]
                rows.append(row); rhs.append(-F(n) ** g * a[i])
            c = solve(rows, rhs)
            if c is not None:
                return ("prec", (d, e, g), c)
    return None


def value(f, n0, a, N, mod):
    kind, d, c = f
    if N < n0:
        return None
    if N - n0 < len(a):
        v = F(a[N - n0])
    elif kind == "poly":
        v = sum(cj * F(N) ** j for j, cj in enumerate(c))
    elif kind == "lin" and N - n0 > 10 ** 6:
        if not mod:
            return None
        return lin_pow(c, d, a, N - n0, mod)
    elif N - n0 > 5000 and not mod:
        return None
    else:
        md = mod if (mod and N - n0 > 5000) else None
        seq = [F(x) if not md else x % md for x in a]
        for i in range(len(a), N - n0 + 1):
            n = n0 + i
            if kind == "lin":
                nv = sum(c[j - 1] * seq[-j] for j in range(1, d + 1)) + c[d]
            else:
                dd, e, g = d
                lead = F(n) ** g + sum(c[j] * F(n) ** j for j in range(g))
                rest = sum(c[g + (t - 1) * (e + 1) + j] * F(n) ** j * seq[-t] for t in range(1, dd + 1) for j in range(e + 1))
                if lead == 0:
                    return None
                nv = -rest / lead
            if md:
                nv = modq(nv, md)
                if nv is None:
                    return None
            seq.append(nv)
            if len(seq) > 50:
                seq = seq[-50:]
        v = seq[-1]
        if md:
            return v
    if isinstance(v, F) and v.denominator != 1:
        return None
    v = int(v)
    return v % mod if mod else v


def modq(x, m):
    x = F(x)
    try:
        return x.numerator % m * pow(x.denominator, -1, m) % m
    except ValueError:
        return None


def lin_pow(c, d, a, idx, m):
    """a(idx) for a(n) = sum c_j a(n-j) + c_0 by companion-matrix power modulo m"""
    cc = [modq(x, m) for x in c]
    if None in cc:
        return None
    size = d + 1
    T = [[0] * size for _ in range(size)]
    T[0][:d] = cc[:d]; T[0][d] = cc[d]
    for i in range(1, d):
        T[i][i - 1] = 1
    T[d][d] = 1
    mul = lambda X, Y: [[sum(X[i][k] * Y[k][j] for k in range(size)) % m for j in range(size)] for i in range(size)]
    R = [[int(i == j) for j in range(size)] for i in range(size)]; P = T; e = idx - (d - 1)
    while e > 0:
        if e & 1:
            R = mul(R, P)
        P = mul(P, P); e >>= 1
    s = [a[d - 1 - i] % m for i in range(d)] + [1]
    return sum(R[0][j] * s[j] for j in range(size)) % m


def lit(x):
    import ast
    try:
        return ast.literal_eval(x)
    except Exception:
        return None


def _alarm(*_):
    raise TimeoutError()


def main():
    signal.signal(signal.SIGALRM, _alarm)
    tags = sys.argv[1:] or ["q8b", "o20"]
    think = {json.loads(l)["id"]: json.loads(l)["correct"] for l in open(f"{RES}/euler_q8bL_thinkpb_s1.jsonl")}
    for tag in tags:
        files = sorted(glob.glob(f"{RES}/euler_{tag}_brutef_s*.jsonl"))
        if not files:
            print(tag, "no rows"); continue
        tot = {}
        for fn in files:
            for l in open(fn):
                r = json.loads(l); pid = r["id"]
                n0, a = ints(r.get("vals"))
                N, mod = lit(r.get("asked", "None")), lit(r.get("mod", "None"))
                ck = r.get("checks") if isinstance(r.get("checks"), list) else []
                ckres = [str(g) == str(lit(v) if lit(v) is not None else v) for _, v, g in ck if g not in ("TIMEOUT",) and not str(g).startswith("error")]
                st = {"vals": len(a), "checks_ok": bool(ckres) and all(ckres), "checks_bad": bool(ckres) and not all(ckres)}
                signal.alarm(30)                                        # one row's fit + extrapolation: 30 s, else no answer
                try:
                    f = fit(n0, a) if a and len(a) >= 5 else None
                    v = value(f, n0, a, N, mod if isinstance(mod, int) and mod > 1 else None) if f and isinstance(N, int) else None
                except TimeoutError:
                    f, v = None, None
                finally:
                    signal.alarm(0)
                st.update(fit=f[0] if f else None, ok=v is not None and norm(v) == norm(r["gold"]), ans=v)
                tot.setdefault(pid, []).append(st)
        print(f"\n== {tag}: {len(tot)} problems, {sum(len(v) for v in tot.values())} rows ({len(files)} seeds)")
        rows = [s for v in tot.values() for s in v]; nr = len(rows)
        print(f"  rows with >= 8 integer brute values {sum(s['vals'] >= 8 for s in rows)}; a structure fits {sum(bool(s['fit']) for s in rows)}"
              f" (poly {sum(s['fit'] == 'poly' for s in rows)}, lin {sum(s['fit'] == 'lin' for s in rows)}, prec {sum(s['fit'] == 'prec' for s in rows)});"
              f" statement checks pass {sum(s['checks_ok'] for s in rows)}, fail {sum(s['checks_bad'] for s in rows)}")
        acc = [s for s in rows if s["fit"] and not s["checks_bad"] and s["ans"] is not None]
        print(f"  accepted (fit + no failed statement check + a value at ASKED) {len(acc)} rows, right {sum(s['ok'] for s in acc)}"
              f" ({100 * sum(s['ok'] for s in acc) / max(1, len(acc)):.0f}% precise); right rows {sum(s['ok'] for s in rows)} of {nr}")
        solved = sorted(p for p, v in tot.items() if any(s["ok"] for s in v))
        print(f"  problems right in some seed: {len(solved)} {solved}; of these thinking-with-code (Qwen3-8B, 14k) wrong on"
              f" {sum(not think.get(p, False) for p in solved)}")
        print(f"  problems right in a majority of seeds: {sum(sum(s['ok'] for s in v) * 2 > len(v) for v in tot.values())}")


if __name__ == "__main__":
    main()
