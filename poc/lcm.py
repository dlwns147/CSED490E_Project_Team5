"""LCM (docs/prereg/PREREG_LCM.md): the cascade derived instead of hand-set. A generative model of every call's answer on a question,
fitted mostly without labels, and the Bayes-optimal adaptive policy over one seed's calls under it.

Model (per question): a latent class z ~ Cat(pi). Each call j of type t(j) in {N (quick), P (the peer's quick), SB (short think),
T (think)} independently returns the right answer y with prob a[t][z], no answer (nothing decodable / an execution error) with prob
x[t][z], else a wrong answer. Wrong answers coincide the way a two-level Chinese restaurant franchise says: each model (restaurant: the
answering model, the peer) reuses its own wrong answers with concentration th1[z]; its new wrong answers come from a question-level
pool shared by both models with concentration th0[z]. So a model repeats its own mistakes more often than another model shares them,
and "trap" classes (small th0) make every source land on the same wrong answer. The free check passes with prob c[t][role], role in
{R, W, X}. Exact marginal likelihood of any labelled partition of wrong answers (sum over table seatings: unsigned Stirling numbers per
restaurant and dish, a CRP over tables per dish; projective, so the predictive of the next call is a likelihood ratio).

Fit: EM over (z, which observed answer is y, or none) per question, on all calls of all seeds (12 per question); labelled questions fix
y. th0 / th1 by exact maximisation over a log grid. K by BIC.
Policy: dynamic programming over observation patterns of one seed's five calls (N, P, SB, T, the retry T), question-independent, so
computed once per fitted model: at each pattern stop and return the answer with the largest posterior, or make the call with the
largest expected value (cost lambda x the call type's mean tokens). Executed on the stored outputs; the realised utility is scored with
the labels. Fixed policies (N, SB->T->T, T->T, N->T->T, the peer cascade) scored on the same question-seeds.
usage: python lcm.py <sql|tc|word> <generator> <peer> <set>   (set: dev | pa | sp; non-live | live; optibench | bwor | logior | optmath)
  -> results/lcm/<task>_<set>_<generator>_<peer>.json; python lcm.py --synthetic: the self-test on data drawn from a known model"""
import json, math, os, random, sys, zlib
from functools import lru_cache
from itertools import combinations

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TYPES = ("N", "P", "SB", "T")
REST = {"N": 0, "SB": 0, "T": 0, "P": 1}   # restaurant: 0 the answering model, 1 the peer
MODE = {"N": 0, "SB": 1, "T": 1, "P": 3}   # LCM-3: a restaurant per mode, nested in its model: the answering model's quick mode (0) and
# its thinking mode (1: the short think is the same think cut at 2k, so SB and T share one); 3 the peer (2 unused)
CALLS = tuple((t, MODE[t]) for t in ("N", "P", "SB", "T", "T"))   # one seed: quick, peer's quick, short think, think, retry think (next seed)
GRID = (0.05, 0.1, 0.2, 0.4, 0.8, 1.6, 3.2, 6.4, 12.8, 25.6, 51.2, 1000.0)
LAM = 0.5   # utility = 100 x right - LAM x ktokens (the project's unit); as a fraction: right - LAM / 100 x ktokens


# ---------------------------------------------------------------- data: per question, 12 sources (type, seed, key, check, ok, tokens)
def _q(src):
    """ys: the observed answers that are right (several on BFCL, whose checker accepts variants)"""
    return {"src": src, "ys": frozenset(k for t, s, k, c, o, tk in src if o and k is not None)}


def load_sql(gen, peer, suf):
    from analyze_sqlpa import grades, ntok
    from run_nlopt import _rows
    R = os.path.join(ROOT, "results", "sql")
    GA, GP, KP = grades(gen + suf), grades(peer + suf), ntok(peer + suf)
    if not (GA and GP):
        return None
    tok = {(a, s): {r["id"]: r.get("n_tok" if a == "cheap" else "out_tokens") for r in _rows(f"{R}/{gen}{suf}_{a}_s{s}.jsonl")}
           for a in ("cheap", "sb", "think") for s in (1, 2, 3)}
    out = {}
    for i in GA[1]:
        src = []
        for s in (1, 2, 3):
            g, p = GA[s].get(i, {}), GP[s].get(i, {}).get("N")
            if not {"N", "SB", "T"} <= set(g) or p is None or i not in KP[s] or any(i not in tok[(a, s)] for a in ("cheap", "sb", "think")):
                break
            for t, a, x in (("N", "cheap", g["N"]), ("SB", "sb", g["SB"]), ("T", "think", g["T"])):
                src.append((t, s, x["h"], x["chk"] == "pass", bool(x["ok"]), tok[(a, s)][i] or 0))
            src.append(("P", s, p["h"], p["chk"] == "pass", bool(p["ok"]), KP[s][i] or 0))
        else:
            out[i] = _q(src)
    return out


def load_tc(gen, peer, split):
    from analyze_tc import DATA, NONLIVE, load
    cats = {x["id"]: x["cat"] for x in (json.loads(l) for l in open(DATA))}
    DA, DP = {s: load(gen, s) for s in (1, 2, 3)}, {s: load(peer, s) for s in (1, 2, 3)}
    if any(v is None for v in list(DA.values()) + list(DP.values())):
        return None
    key = lambda x: None if x["chk"] == "fail" else json.dumps(x["calls"], sort_keys=True)
    out = {}
    for i in DA[1][0]:
        if cats.get(i) is None or (cats[i] in NONLIVE) != (split == "non-live"):
            continue
        src = []
        for s in (1, 2, 3):
            G, C, T, SB = DA[s]; GPs, CP = DP[s][0], DP[s][1]
            if i not in G or not {"N", "SB", "T"} <= set(G[i]) or i not in C or i not in T or i not in SB or "N" not in GPs.get(i, {}) \
                    or i not in CP:
                break
            for t, x, tk in (("N", G[i]["N"], C[i]["n_tok"]), ("SB", G[i]["SB"], SB[i]["out_tokens"]), ("T", G[i]["T"], T[i]["out_tokens"])):
                src.append((t, s, key(x), x["chk"] != "fail", bool(x["ok"]), tk or 0))
            x = GPs[i]["N"]; src.append(("P", s, key(x), x["chk"] != "fail", bool(x["ok"]), CP[i]["n_tok"] or 0))
        else:
            out[i] = _q(src)
    return out


def load_word(gen, peer, bench):
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()):
        import analyze_hopa as H
    from run_nlopt import correct
    A = H.word_rows(gen, bench)
    P = {"formx": {}}   # the peer needs only its quick program (gpt-oss-20b has no OptMATH think)
    for s in (1, 2, 3):
        R = H._rows(f"{H.XRES}/opt_{peer}_{bench}_formx_s{s}.jsonl")
        if not R:
            return None
        P["formx"][s] = {r["id"]: (H.ok_(r), bool(r["correct"]), r.get("out_tokens") or 0, r.get("pred")) for r in R}
    if A is None:
        return None
    same = lambda a, b: a == b if "NBS" in (a, b) else correct(a, str(b)) or correct(b, str(a))
    out = {}
    for i in A["formx"][1]:
        raw = []
        for s in (1, 2, 3):
            rows = [("N", A["formx"]), ("SB", A["formxtb2000"]), ("T", A["formxt"]), ("P", P["formx"])]
            if any(i not in X[s] for _, X in rows):
                break
            for t, X in rows:
                ps, ok, tk, pred = X[s][i]
                raw.append((t, s, pred if ps and pred is not None else None, bool(ps), bool(ok), tk or 0))
        else:
            reps = []   # canonical key: the first earlier answer within the grader's tolerance
            src = []
            for t, s, pred, ps, ok, tk in raw:
                k = None
                if pred is not None:
                    k = next((r for r in reps if same(pred, r)), None)
                    if k is None:
                        reps.append(pred); k = pred
                src.append((t, s, None if k is None else repr(k), ps, ok, tk))
            out[i] = _q(src)
    return out


def load(task, gen, peer, sset):
    if task == "sql":
        sset = {"dev": "", "fresh": "pa", "spider": "sp"}.get(sset, sset)
    return {"sql": load_sql, "tc": load_tc, "word": load_word}[task](gen, peer, sset)


# ---------------------------------------------------------------- the two-level Chinese restaurant franchise over wrong answers
@lru_cache(None)
def stir(n, k):   # unsigned Stirling numbers of the first kind
    if n == k:
        return 1
    if k == 0 or k > n:
        return 0
    return stir(n - 1, k - 1) + (n - 1) * stir(n - 1, k)


@lru_cache(maxsize=2_000_000)
def crf_logp(sig, th0, th1):
    """log P(this labelled partition of wrong answers); sig = sorted tuple of dishes, each (count in restaurant 0, count in 1)"""
    if not sig:
        return 0.0
    lp = 0.0
    for m in (0, 1):
        n = sum(d[m] for d in sig)
        if n:
            lp += math.lgamma(th1) - math.lgamma(th1 + n)
    dist = {0: 1.0}
    for d in sig:
        w = {0: 1.0}
        for m in (0, 1):
            if d[m]:
                w2 = {}
                for a, va in w.items():
                    for t in range(1, d[m] + 1):
                        w2[a + t] = w2.get(a + t, 0.0) + va * stir(d[m], t) * th1 ** t
                w = w2
        dist2 = {}
        for T, v in dist.items():
            for td, vt in w.items():
                dist2[T + td] = dist2.get(T + td, 0.0) + v * vt * th0 * math.factorial(td - 1)
        dist = dist2
    tot = sum(v * math.exp(math.lgamma(th0) - math.lgamma(th0 + T)) for T, v in dist.items())
    return lp + math.log(tot)


@lru_cache(maxsize=1_000_000)
def crp_logp(sizes, phi):
    """log P(this labelled partition of the right answers into variants) under a CRP with concentration phi; sizes sorted"""
    n = sum(sizes)
    if not n:
        return 0.0
    return len(sizes) * math.log(phi) + math.lgamma(phi) - math.lgamma(phi + n) + sum(math.lgamma(m) for m in sizes)


def sig_of(groups):
    """groups: {gid: [n per mode N, SB, T, P]} -> canonical signature (the dishes' per-mode counts)"""
    return tuple(sorted(tuple(g) for g in groups.values()))


def collapse(sig4):
    """per-mode counts -> per-model counts (the two-level franchise of LCM / LCM-2)"""
    return tuple(sorted((d[0] + d[1] + d[2], d[3]) for d in sig4))


@lru_cache(maxsize=2_000_000)
def crf3_logp(sig4, th0, th1, th2):
    """LCM-3: log P(labelled partition of wrong answers) under a three-level franchise: question pool (th0) -> model (th1) -> mode
    (th2); modes N, SB, T in the answering model, P in the peer. Exact: Stirling numbers at the mode and model levels, a CRP over the
    model-level tables per dish; a DP over dishes keeps the totals the normalisers need"""
    if not sig4:
        return 0.0
    lp = 0.0
    for r in range(4):
        n = sum(d[r] for d in sig4)
        if n:
            lp += math.lgamma(th2) - math.lgamma(th2 + n)
    models = ((0, 1, 2), (3,))
    dist = {(0, 0, 0): 1.0}   # (mode-level tables of model 0, of model 1, model-level tables in all)
    for d in sig4:
        per = []   # per model: {(T_md, u_md): weight}
        for modes in models:
            w = {0: 1.0}
            for r in modes:
                if d[r]:
                    w2 = {}
                    for a, va in w.items():
                        for t in range(1, d[r] + 1):
                            w2[a + t] = w2.get(a + t, 0.0) + va * stir(d[r], t) * th2 ** t
                    w = w2
            wu = {}
            for T, vT in w.items():
                if T == 0:
                    wu[(0, 0)] = wu.get((0, 0), 0.0) + vT
                    continue
                for u in range(1, T + 1):
                    wu[(T, u)] = wu.get((T, u), 0.0) + vT * stir(T, u) * th1 ** u
            per.append(wu)
        dist2 = {}
        for (T0, T1, U), v in dist.items():
            for (t0, u0), w0 in per[0].items():
                for (t1, u1), w1 in per[1].items():
                    ud = u0 + u1
                    k = (T0 + t0, T1 + t1, U + ud)
                    dist2[k] = dist2.get(k, 0.0) + v * w0 * w1 * th0 * math.factorial(ud - 1)
        dist = dist2
    tot = 0.0
    for (T0, T1, U), v in dist.items():
        lg = math.lgamma(th0) - math.lgamma(th0 + U)
        for T in (T0, T1):
            if T:
                lg += math.lgamma(th1) - math.lgamma(th1 + T)
        tot += v * math.exp(lg)
    return lp + math.log(tot)


# ---------------------------------------------------------------- model
class Model:
    def __init__(self, K, rng):
        self.K = K
        self.pi = [1.0 / K] * K
        self.a = {t: [min(0.9, max(0.1, 0.5 + 0.3 * rng.uniform(-1, 1))) for _ in range(K)] for t in TYPES}
        self.x = {t: [0.05] * K for t in TYPES}
        self.c = {t: {"R": 0.9, "W": 0.7, "X": 0.05} for t in TYPES}
        self.th0 = [GRID[rng.randrange(2, 9)] for _ in range(K)]
        self.th1 = [GRID[rng.randrange(2, 9)] for _ in range(K)]
        self.phi = [0.1] * K   # right answers come in variants (BFCL) with concentration phi
        self.th2 = [1.0] * K   # LCM-3: the mode level
        self.levels = 2
        self.tok = {t: 500.0 for t in TYPES}

    def wrong_ll(self, sig4, z):
        if self.levels == 3:
            return crf3_logp(sig4, self.th0[z], self.th1[z], self.th2[z])
        return crf_logp(collapse(sig4), self.th0[z], self.th1[z])

    def role_ll(self, t, role, chk, z):
        p = self.a[t][z] if role == "R" else self.x[t][z] if role == "X" else 1.0 - self.a[t][z] - self.x[t][z]
        c = self.c[t][role]
        return math.log(max(p, 1e-12)) + math.log(max(c if chk else 1.0 - c, 1e-12))

    def params(self):
        return self.K * (1 + 2 * len(TYPES) + 3 + (self.levels == 3)) - 1 + 3 * len(TYPES)


def hyps(q, labelled):
    """the hypotheses about which observed answers are right: every subset (the empty one: none is); a labelled question has one"""
    if labelled:
        return [q["ys"]]
    keys = sorted({k for _, _, k, _, _, _ in q["src"] if k is not None})
    return [frozenset(c) for r in range(len(keys) + 1) for c in combinations(keys, r)]


def stats(src, S):
    """per hypothesis: role counts, the sizes of the right variants and the signature of the wrong answers"""
    roles, groups, right = [], {}, {}
    for t, s, k, chk, ok, tk in src:
        role = "X" if k is None else "R" if k in S else "W"
        roles.append((t, role, chk))
        if role == "W":
            groups.setdefault(k, [0, 0, 0, 0])[MODE[t]] += 1
        elif role == "R":
            right[k] = right.get(k, 0) + 1
    return roles, tuple(sorted(right.values())), sig_of(groups)


def dep_from_labels(Q, labels, grid=GRID):
    """LCM-2: the dependence parameters where they are identified, on the labelled questions only (their roles are known): the
    maximum-likelihood (th0, th1) of their wrong-answer partitions and phi of their right variants"""
    sigs = [stats(Q[i]["src"], Q[i]["ys"]) for i in labels]
    th = max(((a, b) for a in grid for b in grid), key=lambda ab: sum(crf_logp(collapse(sig), ab[0], ab[1]) for _, _, sig in sigs))
    phi = max(PHI, key=lambda f: sum(crp_logp(rs, f) for _, rs, _ in sigs))
    return th[0], th[1], phi


PHI = (0.01, 0.03, 0.1, 0.3, 1.0, 3.0)


GRID3 = (0.1, 0.4, 1.6, 6.4, 25.6, 1000.0)


def fit(Q, labels, K, rng, iters=60, tol=1e-4, grid=GRID, dep=None, levels=2):
    """EM; Q {id: q}; labels: the ids whose y is revealed; grid: the concentrations allowed (INDEP: only 1000, wrong answers
    almost never coincide, the classical independent-errors model); dep = (th0, th1, phi) fixed for every class (LCM-2: estimated
    on the labelled questions) instead of fitted by EM. Returns (model, log-likelihood)"""
    M = Model(K, rng)
    M.levels = levels
    if levels == 3:   # LCM-3: per class, from the labelled questions only (weighted by their class posteriors)
        M.th0, M.th1, M.th2 = [1.6] * K, [1.6] * K, [1.6] * K
    if len(grid) == 1:
        M.th0, M.th1 = [grid[0]] * K, [grid[0]] * K
    if dep is not None:
        M.th0, M.th1, M.phi = [dep[0]] * K, [dep[1]] * K, [dep[2]] * K
    S = {i: [(h,) + stats(q["src"], h) for h in hyps(q, i in labels)] for i, q in Q.items()}
    for t in TYPES:
        v = [tk for q in Q.values() for tt, _, _, _, _, tk in q["src"] if tt == t]
        M.tok[t] = sum(v) / max(1, len(v))
    prev = -1e300
    for it in range(iters):
        acc_a = {t: [[0.0, 0.0, 0.0] for _ in range(K)] for t in TYPES}   # R, W, X
        acc_c = {t: {r: [0.0, 0.0] for r in "RWX"} for t in TYPES}
        acc_pi = [0.0] * K
        acc_sig = [dict() for _ in range(K)]
        acc_rs = [dict() for _ in range(K)]
        lab_sig, lab_rs = [dict() for _ in range(K)], [dict() for _ in range(K)]
        ll = 0.0
        for i, H in S.items():
            terms = []
            for h, roles, rs, sig in H:
                base = [sum(M.role_ll(t, r, c, z) for t, r, c in roles) + M.wrong_ll(sig, z) + crp_logp(rs, M.phi[z])
                        + math.log(M.pi[z]) for z in range(K)]
                terms.append(base)
            mx = max(max(b) for b in terms)
            tot = sum(math.exp(v - mx) for b in terms for v in b)
            ll += mx + math.log(tot)
            for (h, roles, rs, sig), b in zip(H, terms):
                for z in range(K):
                    w = math.exp(b[z] - mx) / tot
                    if w < 1e-9:
                        continue
                    acc_pi[z] += w
                    acc_sig[z][sig] = acc_sig[z].get(sig, 0.0) + w
                    acc_rs[z][rs] = acc_rs[z].get(rs, 0.0) + w
                    if i in labels:
                        lab_sig[z][sig] = lab_sig[z].get(sig, 0.0) + w
                        lab_rs[z][rs] = lab_rs[z].get(rs, 0.0) + w
                    for t, r, c in roles:
                        acc_a[t][z]["RWX".index(r)] += w
                        acc_c[t][r][0 if c else 1] += w
        n = sum(acc_pi)
        M.pi = [max(1e-6, v / n) for v in acc_pi]
        for t in TYPES:
            for z in range(K):
                r, w, x = acc_a[t][z]; s = r + w + x + 1e-9
                M.a[t][z], M.x[t][z] = (r + 0.5) / (s + 1.5), (x + 0.5) / (s + 1.5)   # Jeffreys-style smoothing
            for r in "RWX":
                p, f = acc_c[t][r]
                M.c[t][r] = (p + 0.5) / (p + f + 1.0)
        for z in range(K if dep is None and levels == 2 else 0):
            M.th0[z], M.th1[z] = max(((a, b) for a in grid for b in grid),
                                     key=lambda ab: sum(w * crf_logp(collapse(sig), ab[0], ab[1]) for sig, w in acc_sig[z].items()))
            M.phi[z] = max(PHI, key=lambda f: sum(w * crp_logp(rs, f) for rs, w in acc_rs[z].items()))
        for z in range(K if levels == 3 else 0):
            M.th0[z], M.th1[z], M.th2[z] = max(((a, b, c) for a in GRID3 for b in GRID3 for c in GRID3),
                                               key=lambda abc: sum(w * crf3_logp(sig, *abc) for sig, w in lab_sig[z].items()))
            M.phi[z] = max(PHI, key=lambda f: sum(w * crp_logp(rs, f) for rs, w in lab_rs[z].items()))
        if ll - prev < tol * abs(ll):
            break
        prev = ll
    return M, ll


INDEP = (1000.0,)


def fit_best(Q, labels, Ks=(1, 2, 3), restarts=3, seed=0, grid=GRID, dep=None, levels=2):
    """K by BIC over the fitting questions; the best of a few random starts per K"""
    best = None
    if dep == "labels":
        dep = dep_from_labels(Q, labels, grid)
    for K in Ks:
        for r in range(restarts if K > 1 else 1):
            M, ll = fit(Q, labels, K, random.Random(1000 * seed + 10 * K + r), grid=grid, dep=dep, levels=levels)
            bic = -2 * ll + M.params() * math.log(len(Q))
            if best is None or bic < best[0]:
                best = (bic, M, ll)
    return best[1], best[0]


# ---------------------------------------------------------------- the Bayes-optimal policy over one seed's five calls
def canon(pat):
    """relabel answer groups by first appearance in call order"""
    m, out = {}, []
    for e in pat:
        if e is None or e[0] == "X":
            out.append(e)
        else:
            m.setdefault(e[0], len(m)); out.append((m[e[0]], e[1]))
    return tuple(out)


class Planner:
    def __init__(self, M, lam=LAM):
        self.M, self.lam = M, lam
        self.V, self.act, self.P = {}, {}, {}

    def posterior(self, pat):
        """{(z, S): prob}: S = the observed answer groups that are right"""
        if pat in self.P:
            return self.P[pat]
        M = self.M
        gids = sorted({e[0] for e in pat if e is not None and e[0] != "X"})
        out, mx = {}, -1e300
        for r in range(len(gids) + 1):
            for S in combinations(gids, r):
                S = frozenset(S)
                groups, right, roles = {}, {}, []
                for (t, m), e in zip(CALLS, pat):
                    if e is None:
                        continue
                    role = "X" if e[0] == "X" else "R" if e[0] in S else "W"
                    roles.append((t, role, e[1]))
                    if role == "W":
                        groups.setdefault(e[0], [0, 0, 0, 0])[m] += 1
                    elif role == "R":
                        right[e[0]] = right.get(e[0], 0) + 1
                sig, rs = sig_of(groups), tuple(sorted(right.values()))
                for z in range(M.K):
                    v = (math.log(M.pi[z]) + sum(M.role_ll(t, ro, c, z) for t, ro, c in roles) + M.wrong_ll(sig, z)
                         + crp_logp(rs, M.phi[z]))
                    out[(z, S)] = v; mx = max(mx, v)
        tot = sum(math.exp(v - mx) for v in out.values())
        self.P[pat] = {k: math.exp(v - mx) / tot for k, v in out.items()}
        return self.P[pat]

    def outcomes(self, pat, post, j):
        """{next pattern: prob} for making call j"""
        M = self.M
        t, m = CALLS[j]
        gids = sorted({e[0] for e in pat if e is not None and e[0] != "X"})
        new = len(gids)
        res = {}
        def add(e, p):
            nxt = list(pat); nxt[j] = e; key = canon(tuple(nxt)); res[key] = res.get(key, 0.0) + p
        for (z, S), w in post.items():
            if w < 1e-12:
                continue
            a, x = M.a[t][z], M.x[t][z]
            groups, right = {}, {}
            for (tt, mm), e in zip(CALLS, pat):
                if e is not None and e[0] != "X":
                    if e[0] in S:
                        right[e[0]] = right.get(e[0], 0) + 1
                    else:
                        groups.setdefault(e[0], [0, 0, 0, 0])[mm] += 1
            nr, phi = sum(right.values()), M.phi[z]
            joinR = [(g, n / (nr + phi)) for g, n in right.items()] + [(new, phi / (nr + phi))]
            base = M.wrong_ll(sig_of(groups), z)
            joinW = []
            for d in list(groups) + [None]:
                g2 = {k: list(v) for k, v in groups.items()}
                g2.setdefault(d if d is not None else "new", [0, 0, 0, 0])[m] += 1
                joinW.append((d if d is not None else new, math.exp(M.wrong_ll(sig_of(g2), z) - base)))
            for chk in (True, False):
                cx, cr, cw = (M.c[t][r] if chk else 1 - M.c[t][r] for r in "XRW")
                add(("X", chk), w * x * cx)
                for g, p in joinR:
                    add((g, chk), w * a * cr * p)
                for g, p in joinW:
                    add((g, chk), w * (1 - a - x) * cw * p)
        return res

    def right_prob(self, pat):
        py = {}
        for (z, S), w in self.posterior(pat).items():
            for g in S:
                py[g] = py.get(g, 0.0) + w
        return py

    def value(self, pat):
        if pat in self.V:
            return self.V[pat]
        post = self.posterior(pat)
        py = self.right_prob(pat)
        best = (max(py.values()) if py else 0.0, ("stop", max(py, key=py.get) if py else None))
        for j, e in enumerate(pat):
            if e is not None:
                continue
            cost = self.lam / 100 * self.M.tok[CALLS[j][0]] / 1000
            v = -cost + sum(p * self.value(nxt) for nxt, p in self.outcomes(pat, post, j).items())
            if v > best[0] + 1e-12:
                best = (v, ("call", j))
        self.V[pat], self.act[pat] = best
        return best[0]

    def run(self, seed_calls):
        """execute on one question-seed: seed_calls = the five stored (key, check, ok, tokens); -> (right, tokens, calls made)"""
        pat, keys, tok, made = (None,) * 5, {}, 0, []
        while True:
            self.value(pat)
            kind, arg = self.act[pat]
            if kind == "stop":
                if arg is None:
                    return False, tok, made
                k = next(k for k, g in keys.items() if g == arg)
                return any(o for kk, c, o, t in seed_calls if kk == k and kk is not None), tok, made
            j = arg; k, chk, ok, t = seed_calls[j]; tok += t; made.append(j)
            if k is None:
                e = ("X", chk)
            else:
                keys.setdefault(k, len(keys)); e = (keys[k], chk)
            raw = list(pat); raw[j] = e
            order = []   # canonical relabelling, as canon()
            for x in raw:
                if x is not None and x[0] != "X" and x[0] not in order:
                    order.append(x[0])
            remap = {g: i for i, g in enumerate(order)}
            keys = {kk: remap[g] for kk, g in keys.items() if g in remap}
            pat = tuple(None if x is None else x if x[0] == "X" else (remap[x[0]], x[1]) for x in raw)


# ---------------------------------------------------------------- fixed policies and evaluation
def seed_calls(q, s):
    by = {(t, ss): (k, c, o, tk) for t, ss, k, c, o, tk in q["src"]}
    return [by[("N", s)], by[("P", s)], by[("SB", s)], by[("T", s)], by[("T", s % 3 + 1)]]


def fixed(name, sc):
    """(right, tokens) of a fixed policy on one question-seed's calls"""
    N, P, SB, T, T2 = sc
    tt = (T[2], T[3]) if T[1] else (T2[2], T[3] + T2[3])
    d = (SB[2], SB[3]) if SB[1] else (tt[0], SB[3] + tt[1])
    if name == "N":
        return N[2], N[3]
    if name == "SB->T->T":
        return d
    if name == "T->T":
        return tt
    if name == "N->T->T":
        return (N[2], N[3]) if N[1] else (tt[0], N[3] + tt[1])
    if name == "cascade":
        if not N[1]:
            return d[0], N[3] + d[1]
        if P[1] and P[0] is not None and P[0] == N[0]:
            return N[2], N[3] + P[3]
        return d[0], N[3] + P[3] + d[1]
    raise KeyError(name)


FIXED = ("N", "SB->T->T", "T->T", "N->T->T", "cascade")


def util(rows):
    """mean utility in points over question-seeds: 100 x right - LAM x ktokens"""
    return sum(100 * float(r) - LAM * t / 1000 for r, t in rows) / max(1, len(rows))


VARIANTS = REGISTERED = (("lcm", 0, GRID), ("lcm", 30, GRID), ("indep", 30, INDEP))   # LCM (pre-registered)
if os.environ.get("LCM_VARIANTS"):   # LCM-2: e.g. "lcm2:30,lcm2:100" (dependence from the labels)
    VARIANTS = tuple((n, int(k), GRID) for n, k in (v.split(":") for v in os.environ["LCM_VARIANTS"].split(",")))


def evaluate(Q, task_desc, reps=3, out=None):
    """cross-fitting over two halves (crc32(id) mod 2): fit on one half (all calls unlabelled, k labelled questions), act on the
    other. Per question (seed mean, label-draw mean): the planner of each variant; the fixed policies; the best fixed policy chosen
    with all of the evaluation half's labels (oracle); the fixed policy a k-label pilot chooses on the fitting half (pilot)."""
    from analyze_ho3 import ci
    ids = sorted(Q)
    half = {h: [i for i in ids if zlib.crc32(i.encode()) % 2 == h] for h in (0, 1)}
    qu = lambda rows: sum(100 * float(r) - LAM * t / 1000 for r, t in rows) / len(rows)
    per = {f: {i: qu([fixed(f, seed_calls(Q[i], s)) for s in (1, 2, 3)]) for i in ids} for f in FIXED}
    acc = {f: {i: sum(fixed(f, seed_calls(Q[i], s))[0] for s in (1, 2, 3)) / 3 for i in ids} for f in FIXED}
    tok = {f: {i: sum(fixed(f, seed_calls(Q[i], s))[1] for s in (1, 2, 3)) / 3 for i in ids} for f in FIXED}
    P = {v: {} for v in VARIANTS}; PA = {v: {} for v in VARIANTS}; PT = {v: {} for v in VARIANTS}
    oracle, pilot, models = {}, {}, []
    for h in (0, 1):
        fitq, ev = {i: Q[i] for i in half[h]}, half[1 - h]
        best = max(FIXED, key=lambda f: sum(per[f][i] for i in ev))
        for i in ev:
            oracle[i] = per[best][i]
        for v in VARIANTS:
            name, k, grid = v
            reps_v = reps if k else 1
            for r in range(reps_v):
                rng = random.Random(97 * r + 7 * k + h)
                lab = set(rng.sample(half[h], min(k, len(half[h])))) if k else set()
                M, bic = fit_best(fitq, lab, seed=r, grid=grid, dep="labels" if name == "lcm2" else None,
                                  levels=3 if name == "lcm3" else 2, Ks=(1, 2, 3, 4, 5) if name == "lcm3" else (1, 2, 3))
                Pl = Planner(M)
                for i in ev:
                    rows = [Pl.run(seed_calls(Q[i], s))[:2] for s in (1, 2, 3)]
                    P[v][i] = P[v].get(i, 0.0) + qu(rows) / reps_v
                    PA[v][i] = PA[v].get(i, 0.0) + sum(x for x, _ in rows) / 3 / reps_v
                    PT[v][i] = PT[v].get(i, 0.0) + sum(t for _, t in rows) / 3 / reps_v
                if v == next(u for u in VARIANTS if u[1]):   # the pilot: the first labelled variant's label draws
                    pick = max(FIXED, key=lambda f: sum(per[f][i] for i in lab))
                    for i in ev:
                        pilot[i] = pilot.get(i, 0.0) + per[pick][i] / reps_v
                models.append(dict(variant=name, k=k, half=h, rep=r, K=M.K, bic=bic, patterns=len(Pl.V), pi=M.pi, a=M.a, x=M.x, c=M.c,
                                   th0=M.th0, th1=M.th1, tok=M.tok))
                print(f"{task_desc} {name} k {k} half {h} rep {r}: K {M.K}, patterns {len(Pl.V)}", flush=True)
    d = lambda A, B: ci({i: (A[i] - B[i]) / 100 for i in ids})
    if VARIANTS != REGISTERED:   # LCM-2: the same comparisons for each variant
        rec = dict(task=task_desc, n=len(ids), fixed={f: sum(per[f].values()) / len(ids) for f in FIXED},
                   fixed_acc={f: 100 * sum(acc[f].values()) / len(ids) for f in FIXED},
                   fixed_ktok={f: sum(tok[f].values()) / len(ids) / 1000 for f in FIXED},
                   oracle=sum(oracle.values()) / len(ids), pilot=sum(pilot.values()) / len(ids), models=models,
                   variants={f"{v[0]}{v[1]}": dict(u=sum(P[v].values()) / len(ids), acc=100 * sum(PA[v].values()) / len(ids),
                                                   ktok=sum(PT[v].values()) / len(ids) / 1000, vs_default=d(P[v], per["cascade"]),
                                                   vs_pilot=d(P[v], pilot), vs_oracle=d(P[v], oracle)) for v in VARIANTS})
        if ("lcm3", 30, GRID) in VARIANTS and ("lcm2", 30, GRID) in VARIANTS:   # L3-P2, paired on the same label draws
            rec["lcm3_vs_lcm2"] = d(P[("lcm3", 30, GRID)], P[("lcm2", 30, GRID)])
            print(f"*** {task_desc} lcm3 - lcm2 (k = 30): {rec['lcm3_vs_lcm2'][0]:+.2f} [{rec['lcm3_vs_lcm2'][1]:+.2f}, "
                  f"{rec['lcm3_vs_lcm2'][2]:+.2f}]", flush=True)
        if ("lcm2", 30, GRID) in VARIANTS and ("lcm", 30, GRID) in VARIANTS:   # L2-P2, paired on the same label draws
            rec["lcm2_vs_lcm"] = d(P[("lcm2", 30, GRID)], P[("lcm", 30, GRID)])
            print(f"*** {task_desc} lcm2 - lcm (k = 30): {rec['lcm2_vs_lcm'][0]:+.2f} [{rec['lcm2_vs_lcm'][1]:+.2f}, "
                  f"{rec['lcm2_vs_lcm'][2]:+.2f}]", flush=True)
        for name, r in rec["variants"].items():
            print(f"*** {task_desc} {name}: {r['u']:+.2f} ({r['acc']:.1f}% @ {r['ktok']:.2f}k); vs default {r['vs_default'][0]:+.2f} "
                  f"[{r['vs_default'][1]:+.2f}, {r['vs_default'][2]:+.2f}]; vs pilot {r['vs_pilot'][0]:+.2f} [{r['vs_pilot'][1]:+.2f}, "
                  f"{r['vs_pilot'][2]:+.2f}]; vs oracle {r['vs_oracle'][0]:+.2f} [{r['vs_oracle'][1]:+.2f}, {r['vs_oracle'][2]:+.2f}]",
                  flush=True)
        if out:
            json.dump(rec, open(out, "w"))
        return rec
    main = ("lcm", 30, GRID)
    rec = dict(task=task_desc, n=len(ids), fixed={f: sum(per[f].values()) / len(ids) for f in FIXED},
               fixed_acc={f: 100 * sum(acc[f].values()) / len(ids) for f in FIXED},
               fixed_ktok={f: sum(tok[f].values()) / len(ids) / 1000 for f in FIXED},
               oracle=sum(oracle.values()) / len(ids), pilot=sum(pilot.values()) / len(ids),
               planner={f"{v[0]}{v[1]}": sum(P[v].values()) / len(ids) for v in VARIANTS},
               planner_acc={f"{v[0]}{v[1]}": 100 * sum(PA[v].values()) / len(ids) for v in VARIANTS},
               planner_ktok={f"{v[0]}{v[1]}": sum(PT[v].values()) / len(ids) / 1000 for v in VARIANTS},
               vs_oracle=d(P[main], oracle), vs_default=d(P[main], per["cascade"]), vs_pilot=d(P[main], pilot),
               vs_indep=d(P[main], P[("indep", 30, INDEP)]), k0_vs_default=d(P[("lcm", 0, GRID)], per["cascade"]),
               k0_vs_k30=d(P[("lcm", 0, GRID)], P[main]), models=models)
    print(f"*** {task_desc} ({len(ids)} questions): planner(30) {rec['planner']['lcm30']:+.2f} ({rec['planner_acc']['lcm30']:.1f}% @ "
          f"{rec['planner_ktok']['lcm30']:.2f}k) | oracle fixed {rec['oracle']:+.2f} | default cascade {rec['fixed']['cascade']:+.2f} | "
          f"30-label pilot {rec['pilot']:+.2f} | indep {rec['planner']['indep30']:+.2f} | k=0 {rec['planner']['lcm0']:+.2f}", flush=True)
    for key in ("vs_oracle", "vs_default", "vs_pilot", "vs_indep", "k0_vs_default", "k0_vs_k30"):
        print(f"    {key}: {rec[key][0]:+.2f} [{rec[key][1]:+.2f}, {rec[key][2]:+.2f}]", flush=True)
    if out:
        json.dump(rec, open(out, "w"))
    return rec


# ---------------------------------------------------------------- self-test on synthetic data drawn from a model
def sample(M, n, rng):
    """questions drawn from M: y = 'y', wrong answers named by dish"""
    Q = {}
    for qi in range(n):
        z = rng.choices(range(M.K), M.pi)[0]
        tables = {0: [], 1: []}; dish_tables = []; rv = []   # restaurant tables: [dish, count]; dish table counts; right variants
        src = []
        for s in (1, 2, 3):
            for t in ("N", "SB", "T", "P"):
                m = REST[t]; u = rng.random(); a, x = M.a[t][z], M.x[t][z]
                if u < a:
                    nr = sum(rv)
                    v = rng.random() * (nr + M.phi[z]); acc = 0.0; ri = None
                    for idx, cnt in enumerate(rv):
                        acc += cnt
                        if v < acc:
                            ri = idx; break
                    if ri is None:
                        rv.append(0); ri = len(rv) - 1
                    rv[ri] += 1
                    k, role = f"y{ri}", "R"
                elif u < a + x:
                    k, role = None, "X"
                else:
                    n_m = sum(c for _, c in tables[m])
                    v = rng.random() * (n_m + M.th1[z])
                    acc = 0.0; chosen = None
                    for tb in tables[m]:
                        acc += tb[1]
                        if v < acc:
                            chosen = tb; break
                    if chosen is None:
                        T = sum(dish_tables)
                        v2 = rng.random() * (T + M.th0[z]); acc = 0.0; d = None
                        for di, cnt in enumerate(dish_tables):
                            acc += cnt
                            if v2 < acc:
                                d = di; break
                        if d is None:
                            dish_tables.append(0); d = len(dish_tables) - 1
                        dish_tables[d] += 1
                        chosen = [d, 0]; tables[m].append(chosen)
                    chosen[1] += 1
                    k, role = f"w{chosen[0]}", "W"
                chk = rng.random() < M.c[t][role]
                src.append((t, s, k, chk, role == "R", int(M.tok[t])))
        Q[f"q{qi}"] = _q(src)
    return Q


def selftest():
    rng = random.Random(0)
    M = Model(2, rng)
    M.pi = [0.7, 0.3]
    M.a = {"N": [0.75, 0.2], "P": [0.7, 0.25], "SB": [0.85, 0.35], "T": [0.9, 0.45]}
    M.x = {t: [0.05, 0.1] for t in TYPES}
    M.c = {t: {"R": 0.95, "W": 0.75, "X": 0.02} for t in TYPES}
    M.th0, M.th1 = [3.2, 0.4], [0.8, 0.2]
    M.phi = [0.1, 0.3]
    M.tok = {"N": 100.0, "P": 100.0, "SB": 1200.0, "T": 1800.0}
    # projectivity check: probabilities of all labelled partitions of 4 items (2 per restaurant) sum to 1
    def parts(items):
        if not items:
            yield []
            return
        f, rest = items[0], items[1:]
        for p in parts(rest):
            for i in range(len(p)):
                yield p[:i] + [[f] + p[i]] + p[i + 1:]
            yield [[f]] + p
    tot = 0.0
    for p in parts([0, 0, 1, 1]):
        tot += math.exp(crf_logp(tuple(sorted((b.count(0), b.count(1)) for b in p)), 1.3, 0.7))
    print(f"self-test: CRF partition probabilities sum to {tot:.6f} (4 items, 2 restaurants)")
    Q = sample(M, 1500, rng)
    fitq = {i: Q[i] for i in sorted(Q)[:750]}
    for k in (0, 30):
        lab = set(sorted(fitq)[:k])
        Mh, bic = fit_best(fitq, lab)
        print(f"self-test k {k}: K {Mh.K}; pi {[round(v, 2) for v in Mh.pi]}; a_N {[round(v, 2) for v in Mh.a['N']]}; "
              f"a_T {[round(v, 2) for v in Mh.a['T']]}; th0 {Mh.th0}; th1 {Mh.th1}")
        ev = sorted(Q)[750:]
        for name, Pl in (("true model", Planner(M)), ("fitted", Planner(Mh))):
            rows = [Pl.run(seed_calls(Q[i], s))[:2] for i in ev for s in (1, 2, 3)]
            print(f"   planner ({name}): {util(rows):+.2f} ({100 * sum(r for r, _ in rows) / len(rows):.1f}% @ "
                  f"{sum(t for _, t in rows) / len(rows) / 1000:.2f}k); expected under the true model {Planner(M).value((None,) * 5) * 100:+.2f}")
        for f in FIXED:
            print(f"   {f}: {util([fixed(f, seed_calls(Q[i], s)) for i in ev for s in (1, 2, 3)]):+.2f}")


def main():
    if "--synthetic" in sys.argv:
        return selftest()
    task, gen, peer, sset = sys.argv[1:5]
    Q = load(task, gen, peer, sset)
    if not Q:
        print("rows missing"); return
    od = os.environ.get("LCM_OUT", f"{ROOT}/results/lcm")
    os.makedirs(od, exist_ok=True)
    evaluate(Q, f"{task} {sset} {gen}<-{peer}", out=f"{od}/{task}_{sset}_{gen}_{peer}.json")


if __name__ == "__main__":
    main()
