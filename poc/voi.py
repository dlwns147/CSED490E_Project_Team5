"""PREREG_VOI (2026-11-22): label-free, cost-aware acquisition of answers across heterogeneous sources, on every math-computation set.

Model per set (fitted by EM on unlabeled samples, cross-fitted by problem halves):
  latent per problem: true answer y (one of the observed answer classes, or U = a value no sample shows) and difficulty class z (D by BIC);
  a sample of source s: right w.p. p[s,z], visible failure w.p. f[s,z], else wrong; the wrong values of a problem form an Ewens partition
  with concentration alpha (shared misreadings = wrong values that coincide); a free check on a sample passes w.p. cr[s] if the sample is
  right, cw[s] if wrong (no check -> no factor).
Policy: after each sample, posterior over (z, y); stop and return argmax_y unless querying some source has positive value of information:
  two-step lookahead of E[100 * P(return right)] minus lam * expected tokens (lam per 1,000 tokens). No threshold is set by hand.
Baselines on the same sample pools: single sources, self-consistency (majority of 3), CoT-PoT agreement, our cascade, static Dawid-Skene vote
over all samples, and a label-fitted best fixed ladder (FrugalGPT-style, cross-fitted with labels).
usage: python3 poc/voi.py <set> [--lam 0.5]     sets: math (MATH-500 + AIME), oeis, euler, eulert, words"""
import json
import math
import os
import random
import re
import sys
import zlib
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(ROOT, "results")
LAM = float(sys.argv[sys.argv.index("--lam") + 1]) if "--lam" in sys.argv else 0.5
SEEDS = (1, 2, 3)
DMAX = int(sys.argv[sys.argv.index("--dmax") + 1]) if "--dmax" in sys.argv else 6   # number of difficulty classes: chosen by BIC up to DMAX
SS = [float(x) for x in sys.argv[sys.argv.index("--ss") + 1].split(",")] if "--ss" in sys.argv else []   # amendment 3
OEIS_BRUTE = "--brute" in sys.argv   # amendment 4
V3 = "--v3" in sys.argv   # diagnostic after OEIS (see PREREG_VOI amendment 2): per-class concentration
TOKLIK = "--v1" not in sys.argv   # v2 (default): token counts are observations of the difficulty class and set expected costs


def rows(path):
    out = []
    if os.path.exists(path):
        for l in open(path, errors="replace"):
            try:
                out.append(json.loads(l))
            except ValueError:
                pass
    return out


T = lambda v: str(v) == "True"


# ---------------------------------------------------------------- data: problem -> {source: [sample, ...]} in seed order
# sample = (answer class id or None for a visible failure, tokens, right, check outcome None / True / False)
def canon_math(r):
    c = r.get("boxed") or ""
    if r.get("mode") == "prog":
        c = (r.get("stdout") or "").strip().splitlines()[-1] if (r.get("stdout") or "").strip() else ""
    c = re.sub(r"\\left|\\right|\$|\s|\\!|\\,", "", c).rstrip(".")
    c = re.sub(r"^\\text\{(.*)\}$", r"\1", c)
    c = re.sub(r"\.0+$", "", c)
    return c or None


def load_math():
    srcs = ["q8b_prog", "q8b_text", "q8b_think", "oss20_prog", "oss20_text", "oss20_think", "r1d7_think", "q14a_think", "q32b_think"]
    P = defaultdict(lambda: defaultdict(list))
    for s in srcs:
        for sd in SEEDS:
            for r in rows(f"{RES}/x1/math_{s}_s{sd}.jsonl"):
                ok = T(r["correct"]); a = canon_math(r)
                if r.get("mode") == "prog" and r.get("status") not in (None, "ok"):
                    a = None
                key = "GOLD" if ok else a     # two right answers are equal (both equal the gold); wrong ones by normalized string
                P[r["id"]][s].append((key, int(r.get("out_tokens") or 0), ok, None))
    return P, srcs


def load_oeis():
    srcs, P = [], defaultdict(lambda: defaultdict(list))
    for m in ("q8b", "oss20", "oss120"):
        for mode, tag in (("prog", m), ("think", {"q8b": "q8b", "oss20": "oss20M", "oss120": "oss120"}[m])):
            s = f"{m}_{mode}"; got = False
            for sd in SEEDS:
                fn = f"{RES}/x44/oeis_{tag}_{mode}_s{sd}.jsonl"
                if m == "q8b" and mode == "think":
                    fn = f"{RES}/x44/oeis_{'q8bT' if sd == 1 else 'q8bTg'}_think_s{sd}.jsonl"
                B = {}
                if OEIS_BRUTE:   # amendment 4 (OEIS development only): the same model's brute force of the same seed as a free check
                    for rb in rows(f"{RES}/x44/oeis_{m}_brute_s{sd}.jsonl"):
                        ob = rb.get("outs"); ob = ob if isinstance(ob, list) else (eval(ob) if ob else [])
                        B[rb["id"]] = ([str(x) for x in ob], int(rb.get("out_tokens") or 0))
                for r in rows(fn):
                    got = True
                    outs = r.get("outs")
                    outs = outs if isinstance(outs, list) else (eval(outs) if outs else [])   # stored as a list or its repr
                    a = "|".join(map(str, outs)) if outs and r.get("code") is not False else None
                    ck, bt = None, 0
                    if OEIS_BRUTE and r["id"] in B:
                        ob, bt = B[r["id"]]
                        ck = (len(ob) == 8 and [str(x) for x in outs[:8]] == ob) if outs else None
                    P[r["id"]][s].append(("GOLD" if T(r["correct"]) else a, int(r.get("out_tokens") or 0) + bt, T(r["correct"]), ck))
            if got:
                srcs.append(s)
    return P, srcs


def load_euler(which):
    srcs, P = [], defaultdict(lambda: defaultdict(list))
    for m, tag in (("q8b", "q8bL"), ("oss20", "oss20"), ("oss120", "oss120")):
        for mode in ("progc", "thinkp"):
            s = f"{m}_{mode}"; got = False
            for sd in SEEDS:
                for r in rows(f"{RES}/x44/{which}_{tag}_{mode}_s{sd}.jsonl"):
                    got = True
                    a = re.sub(r"[\s,]", "", str(r.get("answer") or "")).rstrip(".") or None
                    ck = None
                    if mode == "progc" and isinstance(r.get("checks"), list) and r["checks"]:
                        ck = all(c[-1] is True or str(c[-1]) == "True" for c in r["checks"])
                    P[r["id"]][s].append(("GOLD" if T(r["correct"]) else a, int(r.get("out_tokens") or 0), T(r["correct"]), ck))
            if got:
                srcs.append(s)
    return P, srcs


def load_words():
    sys.argv_saved = sys.argv
    sys.argv = [sys.argv[0], "--nopool"]
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()):
        import analyze_frontier as F
    sys.argv = sys.argv_saved
    P = defaultdict(lambda: defaultdict(list)); srcs = []
    for st in ("x3", "optmath", "optibench", "bwor", "logior"):
        for m in ("q8b", "oss20"):
            ft, fo, fk = F.files(m, st)
            for nm, path in ((f"{m}_own", fo), (f"{m}_think", fk)):
                if nm not in srcs:
                    srcs.append(nm)
                R = F.load(path, {st})
                for (i, sd), r in sorted(R.items(), key=lambda t: (t[0][0], str(t[0][1]))):
                    g = F.gold_of(i, r["gold"])
                    if g is None:
                        continue
                    pred = r.get("pred"); ok = F.correct(pred, g)
                    vis = r.get("status") != "ok" or pred in (None, "NBS")
                    key = None if vis else ("GOLD" if ok else pred)
                    P[i][nm].append((key, int(r.get("out_tokens") or 0), ok, None))
    # numeric wrong answers: merge values that agree() into one class per problem
    for i, S in P.items():
        cls = []
        for s, L in S.items():
            for j, (k, t, ok, ck) in enumerate(L):
                if k in (None, "GOLD"):
                    continue
                hit = next((c for c in cls if F.agree(c, k)), None)
                if hit is None:
                    cls.append(k); hit = k
                L[j] = (str(hit), t, ok, ck)
    return P, srcs


def texts(which):
    """question text per problem id, for the pre-generation router baseline"""
    if which == "math":
        D = json.load(open(f"{RES}/x1/problems.json"))
        return {str(r["id"]): r["problem"] for v in D.values() for r in v}
    DATA = os.path.join(os.path.dirname(ROOT), "nlp_data")
    if which == "oeis":
        return {x["id"]: x["name"] + " " + str(x.get("comments", "")) for x in json.load(open(f"{DATA}/compute/oeis.json"))}
    if which in ("euler", "eulert"):
        return {x["id"]: x["problem"] for x in json.load(open(f"{DATA}/compute/{'euler_dev' if which == 'euler' else 'euler_test'}.json"))}
    import analyze_frontier as F
    return dict(F.Q)


def router(P, srcs, fit_ids, ev_ids, txt):
    """'Is Escalation Worth It?' (arXiv 2605.06350)-style pre-generation router: from the question alone, predict the single source
    whose first sample has the highest utility (TF-IDF + multinomial logistic regression, trained with LABELS on the other half)"""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    y = [max(srcs, key=lambda s: U(P[i][s][0][2], P[i][s][0][1])) for i in fit_ids]
    if len(set(y)) < 2:
        return {i: (P[i][y[0]][0][2], P[i][y[0]][0][1]) for i in ev_ids}
    vec = TfidfVectorizer(min_df=2, ngram_range=(1, 2), sublinear_tf=True)
    X = vec.fit_transform([txt.get(i, "") for i in fit_ids])
    clf = LogisticRegression(max_iter=2000, C=1.0).fit(X, y)
    pr = clf.predict(vec.transform([txt.get(i, "") for i in ev_ids]))
    return {i: (P[i][s][0][2], P[i][s][0][1]) for i, s in zip(ev_ids, pr)}


# ---------------------------------------------------------------- model
class Model:
    def __init__(self, srcs, D):
        self.S, self.D = srcs, D
        self.pi = [1.0 / D] * D
        self.p = {s: [0.3 + 0.5 * (d + 1) / D for d in range(D)][::-1] for s in srcs}    # class 0 = easy
        self.f = {s: [0.05] * D for s in srcs}
        self.alpha = 1.0
        self.alz = [1.0] * D   # v3: one Ewens concentration per difficulty class (shared misreadings differ with difficulty)
        self.cr = {s: 0.8 for s in srcs}
        self.cw = {s: 0.3 for s in srcs}
        self.mu = {s: [math.log(500.0)] * D for s in srcs}   # v2 (decided after MATH, see PREREG_VOI): log tokens ~ N(mu[s,z], sd[s,z])
        self.sd = {s: [1.0] * D for s in srcs}

    def loglik(self, obs, y, d):
        """obs: list of (source, key, check); y: a class key or None (= U); d: difficulty class"""
        ll, wrong = 0.0, defaultdict(int)
        for s, k, ck, t in obs:
            p, f = self.p[s][d], self.f[s][d]
            if t is not None and TOKLIK:
                z = (math.log(max(t, 1)) - self.mu[s][d]) / self.sd[s][d]
                ll += -0.5 * z * z - math.log(self.sd[s][d])
            if k is None:
                ll += math.log(f)
            elif y is not None and k == y:
                ll += math.log(p)
                if ck is not None:
                    ll += math.log(self.cr[s] if ck else 1 - self.cr[s])
            else:
                ll += math.log(max(1e-12, 1 - p - f)); wrong[k] += 1
                if ck is not None:
                    ll += math.log(self.cw[s] if ck else 1 - self.cw[s])
        n = sum(wrong.values()); a = self.alz[d] if V3 else self.alpha
        if n:   # Ewens partition probability of the wrong values
            ll += len(wrong) * math.log(a) + sum(math.lgamma(c) for c in wrong.values()) + math.lgamma(a) - math.lgamma(a + n)
        return ll

    def posterior(self, obs, label="UNK"):
        """label (semi-supervised fit only): the known true class key ('GOLD' if some sample is right, None = U), else unknown"""
        hyps = sorted({k for _, k, _, _ in obs if k is not None}) + [None]
        if label != "UNK":
            hyps = [label]
        L = {(y, d): math.log(self.pi[d]) + self.loglik(obs, y, d) for y in hyps for d in range(self.D)}
        m = max(L.values()); Z = sum(math.exp(v - m) for v in L.values())
        return {k: math.exp(v - m) / Z for k, v in L.items()}, m + math.log(Z)

    def fit(self, problems, iters=40, labels=None):
        for _ in range(iters):
            cnt = {s: [[1e-3, 1e-3, 1e-3] for _ in range(self.D)] for s in self.S}   # right, fail, wrong
            ck = {s: [1.0, 1.0, 1.0, 1.0] for s in self.S}   # right&pass, right&fail, wrong&pass, wrong&fail (+1 smoothing)
            pis = [1e-3] * self.D; wrong_sets = []
            tk = {s: [[1e-3, 0.0, 0.0] for _ in range(self.D)] for s in self.S}   # weight, sum log t, sum (log t)^2
            for n_, obs in enumerate(problems):
                post, _ = self.posterior(obs, labels[n_] if labels else "UNK")
                for (y, d), w in post.items():
                    if w < 1e-6:
                        continue
                    pis[d] += w; wr = defaultdict(int)
                    for s, k, c, t in obs:
                        if t is not None:
                            lt = math.log(max(t, 1)); tk[s][d][0] += w; tk[s][d][1] += w * lt; tk[s][d][2] += w * lt * lt
                        j = 1 if k is None else (0 if (y is not None and k == y) else 2)
                        cnt[s][d][j] += w
                        if c is not None and j != 1:
                            ck[s][(0 if c else 1) + (0 if j == 0 else 2)] += w
                        if j == 2:
                            wr[k] += 1
                    if wr:
                        wrong_sets.append((w, list(wr.values()), d))
            for s in self.S:
                for d in range(self.D):
                    r, f_, w = cnt[s][d]; t = r + f_ + w
                    self.p[s][d], self.f[s][d] = max(1e-4, r / t), max(1e-4, f_ / t)
                a, b, c, e = ck[s]; self.cr[s], self.cw[s] = a / (a + b), c / (c + e)
                for d in range(self.D):
                    w, s1, s2 = tk[s][d]
                    if w > 1e-2:
                        m_ = s1 / w; self.mu[s][d] = m_; self.sd[s][d] = max(0.1, math.sqrt(max(1e-6, s2 / w - m_ * m_)))
            tp = sum(pis); self.pi = [x / tp for x in pis]
            grid = [math.exp(x / 4) for x in range(-16, 25)]   # alpha by maximum expected Ewens likelihood (grid e^-4 .. e^6)
            ev = lambda a, sel: sum(w * (len(c) * math.log(a) + math.lgamma(a) - math.lgamma(a + sum(c))) for w, c, d in wrong_sets if sel(d))
            self.alpha = max(grid, key=lambda a: ev(a, lambda d: True))
            if V3:
                self.alz = [max(grid, key=lambda a, z=z: ev(a, lambda d: d == z)) for z in range(self.D)]
            order = sorted(range(self.D), key=lambda d: -sum(self.p[s][d] for s in self.S))   # keep class 0 = easiest
            self.pi = [self.pi[d] for d in order]
            for s in self.S:
                self.p[s] = [self.p[s][d] for d in order]; self.f[s] = [self.f[s][d] for d in order]
                self.mu[s] = [self.mu[s][d] for d in order]; self.sd[s] = [self.sd[s][d] for d in order]
            self.alz = [self.alz[d] for d in order]
        return sum(self.posterior(o, labels[n_] if labels else "UNK")[1] for n_, o in enumerate(problems))


def stop_value(model, obs):
    post, _ = model.posterior(obs)
    py = defaultdict(float)
    for (y, d), w in post.items():
        py[y] += w
    cands = {y: v for y, v in py.items() if y is not None}
    if not cands:
        return 0.0, None, post
    y = max(cands, key=cands.get)
    return 100 * cands[y], y, post


def outcomes(model, obs, s, post):
    """predictive distribution of the next sample of source s: list of (prob, key)"""
    wrong_all = defaultdict(int)
    out = defaultdict(float)
    for (y, d), w in post.items():
        if w < 1e-9:
            continue
        p, f = model.p[s][d], model.f[s][d]
        out[None] += w * f
        wr = defaultdict(int)
        for _, k, _, _ in obs:
            if k is not None and k != y:
                wr[k] += 1
        n = sum(wr.values()); a = model.alz[d] if V3 else model.alpha
        if y is not None:
            out[y] += w * p
        else:
            out["__NEW_RIGHT__"] += w * p
        q = w * (1 - p - f)
        for k, c in wr.items():
            out[k] += q * c / (a + n)
        out["__NEW__"] += q * a / (a + n)
    out["__NEW__"] += out.pop("__NEW_RIGHT__", 0.0)
    return [(v, k) for k, v in out.items() if v > 1e-9]


def exp_cost(model, post, s, cost):
    """v2: expected tokens of the next sample of s under the posterior over difficulty classes"""
    if not TOKLIK:
        return cost[s]
    pz = defaultdict(float)
    for (y, d), w in post.items():
        pz[d] += w
    return sum(w * math.exp(model.mu[s][d] + model.sd[s][d] ** 2 / 2) for d, w in pz.items())


def lookahead(model, obs, avail, cost, depth):
    """best value achievable from this state with at most `depth` more samples: (value, source or None)"""
    v0, _, post = stop_value(model, obs)
    best = (v0, None)
    if depth == 0:
        return best
    for s, n in avail.items():
        if n <= 0:
            continue
        ev = 0.0
        for pr, k in outcomes(model, obs, s, post):
            kk = f"__new{len(obs)}" if k == "__NEW__" else k
            av = dict(avail); av[s] -= 1
            ev += pr * lookahead(model, obs + [(s, kk, None, None)], av, cost, depth - 1)[0]
        ev -= LAM * exp_cost(model, post, s, cost) / 1000
        if ev > best[0] + 1e-9:
            best = (ev, s)
    return best


def run_voi(model, prob, cost):
    """prob: {source: [samples]}; returns (right, tokens, n samples)"""
    obs, used, tok = [], defaultdict(int), 0
    avail = {s: len(L) for s, L in prob.items()}
    while True:
        v, s = lookahead(model, obs, avail, cost, 2)
        if s is None:
            break
        k, t, ok, ck = prob[s][used[s]]
        used[s] += 1; avail[s] -= 1; tok += t
        obs.append((s, k, ck, t))
    _, y, _ = stop_value(model, obs)
    return (y == "GOLD"), tok, len(obs)


# ---------------------------------------------------------------- baselines
def majority(samples):
    c = defaultdict(int)
    for k, *_ in samples:
        if k is not None:
            c[k] += 1
    return max(c, key=lambda k: (c[k], k == "GOLD" and False)) if c else None


def base_single(prob, s):
    L = prob.get(s, [])
    if not L:
        return None
    k, t, ok, ck = L[0]
    return (k == "GOLD"), t


def base_sc(prob, s, n=3):
    L = prob.get(s, [])[:n]
    if not L:
        return None
    return majority(L) == "GOLD", sum(t for _, t, _, _ in L)


def ladder(prob, steps):
    """fixed ladder: steps = [(source, accept rule)], rule 'agree' accepts when its answer equals an earlier sample's, 'any' when it is
    not a visible failure, 'last' always; tokens of every executed step are paid"""
    seen, tok, idx = [], 0, defaultdict(int)
    for s, rule in steps:
        L = prob.get(s, [])
        if idx[s] >= len(L):
            continue
        k, t, ok, ck = L[idx[s]]; idx[s] += 1; tok += t
        if rule == "any" and k is not None and ck is not False:
            return k == "GOLD", tok
        if rule == "agree" and k is not None and any(k == x for x in seen):
            return k == "GOLD", tok
        if rule == "last":
            if k is None:
                continue
            return k == "GOLD", tok
        seen.append(k) if k is not None else None
    return False, tok


def ds_static(model, prob):
    obs = [(s, k, ck, t) for s, L in prob.items() for k, t, ok, ck in L]
    _, y, _ = stop_value(model, obs)
    return y == "GOLD", sum(t for L in prob.values() for _, t, _, _ in L)


# ---------------------------------------------------------------- evaluation
U = lambda ok, tok: 100 * float(ok) - LAM * tok / 1000


def boot(d, B=4000, seed=1):
    ids = list(d); rng = random.Random(seed); n = len(ids)
    mu = sum(d.values()) / n
    m = sorted(sum(d[rng.choice(ids)] for _ in range(n)) / n for _ in range(B))
    return mu, m[int(0.025 * B)], m[int(0.975 * B) - 1], (sum(x <= 0 for x in m) + 1) / (B + 1)


def main():
    which = sys.argv[1]
    P, srcs = {"math": load_math, "oeis": load_oeis, "words": load_words}.get(which, lambda: load_euler(which))()
    ids = sorted(i for i in P if all(len(P[i].get(s, [])) for s in srcs))
    global TXT
    TXT = texts(which)
    print(f"{which}: {len(ids)} problems with every source; sources {srcs}; lam {LAM}", flush=True)
    half = {i: zlib.crc32(i.encode()) % 2 for i in ids}
    res = defaultdict(dict)
    think_srcs = [s for s in srcs if "think" in s]
    for h in (0, 1):
        fit_ids = [i for i in ids if half[i] != h]; ev_ids = [i for i in ids if half[i] == h]
        probs = [[(s, k, ck, t) for s in srcs for k, t, ok, ck in P[i][s]] for i in fit_ids]
        best = None
        for D in range(1, DMAX + 1):
            m = Model(srcs, D); ll = m.fit(probs)
            k = len(srcs) * D * (4 if TOKLIK else 2) + (D - 1) + 1 + 2 * len(srcs)
            bic = -2 * ll + k * math.log(len(probs))
            if best is None or bic < best[0]:
                best = (bic, D, m)
        model = best[2]
        cost = {s: sum(t for i in fit_ids for _, t, _, _ in P[i][s]) / max(1, sum(len(P[i][s]) for i in fit_ids)) for s in srcs}
        print(f"  half {h}: D={best[1]} alpha={model.alpha:.2f} alz={[round(a, 2) for a in model.alz]} pi={[round(x, 2) for x in model.pi]}; p[s]: "
              + ", ".join(f"{s} {[round(x, 2) for x in model.p[s]]}" for s in srcs), flush=True)
        # label-fitted best fixed ladder (FrugalGPT-style): all ladders of length <= 3 over sources with rules, chosen on fit_ids by labels
        cands = []
        for a in srcs:
            cands.append([(a, "last")])
            for b in srcs:
                if b != a:
                    cands.append([(a, "any"), (b, "last")])
                    for c in srcs:
                        cands.append([(a, None), (b, "agree"), (c, "last")])
        def mean_u(steps, I):
            return sum(U(*ladder(P[i], steps)) for i in I) / len(I)
        lad = max(cands, key=lambda st: mean_u(st, fit_ids))
        res["pre-generation router (labels)"].update(router(P, srcs, fit_ids, ev_ids, TXT))
        for frac in SS:   # amendment 3: semi-supervised fit, labels on a fraction of the fit half (crc32 order), same D as label-free
            lab_ids = set(sorted(fit_ids, key=lambda i: zlib.crc32(("lab" + i).encode()))[:int(round(frac * len(fit_ids)))])
            labs = [("GOLD" if any(ok for s_ in srcs for _, _, ok, _ in P[i][s_]) else None) if i in lab_ids else "UNK" for i in fit_ids]
            ms = Model(srcs, best[1]); ms.fit(probs, labels=labs)
            for i in ev_ids:
                res[f"VOI-SS {int(100 * frac)}% labels"][i] = run_voi(ms, P[i], cost)[:2]
        for i in ev_ids:
            res["VOI"][i] = run_voi(model, P[i], cost)[:2]
            res["DS-static (all samples)"][i] = ds_static(model, P[i])
            res["FrugalGPT-style ladder (labels)"][i] = ladder(P[i], lad)
        print(f"  half {h}: label-fitted ladder {lad}", flush=True)
    for i in ids:
        for s in srcs:
            res[f"single {s}"][i] = base_single(P[i], s)
        for s in think_srcs:
            res[f"SC@3 {s}"][i] = base_sc(P[i], s)
        for m in ("q8b", "oss20"):
            if f"{m}_text" in srcs and f"{m}_prog" in srcs:   # CoT-PoT agreement (2604.17433), else that model's think
                res[f"CoT-PoT {m}"][i] = ladder(P[i], [(f"{m}_prog", None), (f"{m}_text", "agree"), (f"{m}_think", "last")])
        cheap = [s for s in srcs if "think" not in s]
        for m in ("q8b", "oss20"):
            own = next((s for s in cheap if s.startswith(m)), None); peer = next((s for s in cheap if not s.startswith(m) and ("prog" in s or "own" in s or "progc" in s)), None)
            if own and peer and f"{m}_think" in srcs and f"{m}_{own.split('_')[1]}" == own:
                res[f"our cascade {m}"][i] = ladder(P[i], [(own, None), (peer, "agree"), (f"{m}_think", "last"), (f"{m}_think", "last")])
    print(f"\n  arm (n={len(ids)})                        acc     ktok   utility")
    tab = []
    for arm, R in res.items():
        R = {i: v for i, v in R.items() if v is not None}
        if len(R) < len(ids):
            continue
        acc = 100 * sum(v[0] for v in R.values()) / len(R); kt = sum(v[1] for v in R.values()) / len(R) / 1000
        tab.append((sum(U(*v) for v in R.values()) / len(R), arm, acc, kt))
    for u, arm, acc, kt in sorted(tab, reverse=True):
        print(f"  {arm:40s} {acc:5.1f}%  {kt:6.2f}  {u:7.2f}")
    vo = res["VOI"]
    print("\n  VOI - baseline (utility, paired bootstrap by problem, one-sided p):")
    for u, arm, acc, kt in sorted(tab, reverse=True):
        if arm == "VOI":
            continue
        mu, lo, hi, p = boot({i: U(*vo[i]) - U(*res[arm][i]) for i in ids})
        print(f"  {arm:40s} {mu:+6.2f} [{lo:+6.2f}, {hi:+6.2f}]  p={p:.4f}")
    json.dump({arm: {i: list(v) for i, v in R.items() if v is not None} for arm, R in res.items()},
              open(f"{RES}/voi_{which}_lam{LAM}{'_v3' if V3 else ''}{'_brute' if OEIS_BRUTE else ''}.json", "w"))


if __name__ == "__main__":
    main()
