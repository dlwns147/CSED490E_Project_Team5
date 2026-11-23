"""PREREG_DIFF addendum MC-SEQ (2026-11-23): sequential acquisition of MathConstruct samples with cross-verification.
Sources (seeds 1-3 each): progc of q8b / oss20 / oss120 (candidate + its verify()), parsed think-then-program of the three (candidate
only). Dawid-Skene over verifier families fitted label-free on the other half of problems (crc32 halves). Buy source s next iff
100 * p_s * (1 - P_best) - lam * c_s > 0 (p_s = mean posterior that s's candidates are right on the fit half). usage: python3 poc/mcon_seq.py"""
import json, math, os, random, zlib
from collections import defaultdict
R = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "x44")
LAM = 0.5
SEQ2 = bool(os.environ.get("SEQ2"))   # addendum MC-SEQ2
FAM = lambda v: v.split("_s")[0].rstrip("T")
U = lambda ok, t: 100 * ok - LAM * t / 1000

cand, tok = {}, {}
for m in ("q8b", "oss20", "oss120"):
    for s in (1, 2, 3):
        for l in open(f"{R}/mcon_{m}_progc_s{s}.jsonl"):
            r = json.loads(l); k = (r["id"], f"{m}_s{s}")
            cand[k] = str(r["correct"]) == "True"; tok[k] = int(r.get("out_tokens") or 0)
objok = {(json.loads(l)["id"], json.loads(l)["src"]): json.loads(l)["obj"] is not None for l in open(f"{R}/mcon_xv_objs.jsonl")}
for l in open(f"{R}/mcon_xv_objs2.jsonl"):
    o = json.loads(l); k = (o["id"], o["src"])
    cand[k] = o["correct"]; tok[k] = o["tok"]; objok[k] = o["obj"] is not None
chk = defaultdict(dict)
for fn in ("mcon_xv_checks.jsonl", "mcon_xv_checks2.jsonl"):
    for l in open(f"{R}/{fn}"):
        x = json.loads(l)
        if x["pass"] is not None:
            chk[(x["id"], x["cand"])][x["ver"]] = x["pass"]
ids = sorted({k[0] for k in cand})
SRCS = [f"{m}{t}_s{s}" for m in ("oss120", "oss20", "q8b") for t in ("", "T") for s in (1, 2, 3)]
srcfam = lambda s: s.split("_s")[0]


def fit(I):
    a = {f: 0.8 for f in ("q8b", "oss20", "oss120")}; b = {f: 0.2 for f in a}; pi = 0.4
    keys = [(i, s) for i in I for s in SRCS if (i, s) in chk]
    def post(k, vers=None):
        lr, lw = math.log(pi), math.log(1 - pi)
        for v, p in chk[k].items():
            if vers is not None and v not in vers:
                continue
            f = FAM(v); lr += math.log(a[f] if p else 1 - a[f]); lw += math.log(b[f] if p else 1 - b[f])
        mx = max(lr, lw); return math.exp(lr - mx) / (math.exp(lr - mx) + math.exp(lw - mx))
    for _ in range(40):
        na = defaultdict(lambda: [1.0, 2.0]); nb = defaultdict(lambda: [1.0, 2.0]); sp = 0
        for k in keys:
            q = post(k); sp += q
            for v, p in chk[k].items():
                f = FAM(v); na[f][0] += q * p; na[f][1] += q; nb[f][0] += (1 - q) * p; nb[f][1] += (1 - q)
        a = {f: na[f][0] / na[f][1] for f in a}; b = {f: nb[f][0] / nb[f][1] for f in b}; pi = sp / max(1, len(keys))
    ps = {}
    for s in SRCS:   # fitted rate of right candidates per source family-type (label-free)
        fs = srcfam(s); v = [post((i, x)) if (i, x) in chk else 0.0 for i in I for x in SRCS if srcfam(x) == fs and (i, x) in cand]
        ps[fs] = sum(v) / max(1, len(v))
    cs = {srcfam(s): sum(tok.get((i, x), 0) for i in I for x in SRCS if srcfam(x) == srcfam(s)) /
          max(1, sum(1 for i in I for x in SRCS if srcfam(x) == srcfam(s) and (i, x) in tok)) for s in SRCS}
    beta = {}
    for fs in ps:   # method-of-moments Beta per family over problems (MC-SEQ2)
        rates = []
        for i in I:
            v = [post((i, x)) for x in SRCS if srcfam(x) == fs and (i, x) in chk]
            if v:
                rates.append(sum(v) / len(v))
        m_ = sum(rates) / max(1, len(rates)); var = sum((r - m_) ** 2 for r in rates) / max(1, len(rates) - 1)
        k = max(0.1, m_ * (1 - m_) / var - 1) if var > 0 else 100.0
        beta[fs] = (m_ * k, (1 - m_) * k)
    return post, ps, cs, beta


res = {}
for h in (0, 1):
    fitI = [i for i in ids if zlib.crc32(i.encode()) % 2 != h]; ev = [i for i in ids if zlib.crc32(i.encode()) % 2 == h]
    post, ps, cs, beta = fit(fitI)
    for i in ev:
        have, used, spent = [], set(), 0
        while True:
            vers = {x for x in used if not srcfam(x).endswith("T")}   # verifiers = verify() of the progc samples bought so far
            best = max(have, key=lambda x: post((i, x), vers), default=None)
            pb = post((i, best), vers) if best else 0.0
            def prate(fs):
                if not SEQ2:
                    return ps[fs]
                a0, b0 = beta[fs]; got = [post((i, x), vers) for x in have if srcfam(x) == fs]
                return (a0 + sum(got)) / (a0 + b0 + len(got))
            opts = [(100 * prate(srcfam(s)) * (1 - pb) - LAM * cs[srcfam(s)] / 1000, s) for s in SRCS if s not in used and (i, s) in tok]
            if not opts:
                break
            g, s = max(opts)
            if g <= 0:
                break
            used.add(s); spent += tok[(i, s)]
            if (i, s) in cand and objok.get((i, s), True):
                have.append(s)
        vers = {x for x in used if not srcfam(x).endswith("T")}
        best = max(have, key=lambda x: post((i, x), vers), default=None)
        res[i] = (bool(best and cand.get((i, best), False)), spent, len(used))

lad, th = {}, {}
for i in ids:
    L, Tt = [], []
    for s in (1, 2, 3):
        c = None
        for l in open(f"{R}/mcon_oss120_progc_s{s}.jsonl"):
            r = json.loads(l)
            if r["id"] == i:
                c = r; break
        t = None
        for l in open(f"{R}/mcon_oss120_thinkp_s{s}.jsonl"):
            r = json.loads(l)
            if r["id"] == i:
                t = r; break
        if c is None or t is None:
            continue
        tc, tt = int(c.get("out_tokens") or 0), int(t.get("out_tokens") or 0)
        L.append(U(str(c["correct"]) == "True", tc) if str(c.get("verify")) == "True" else U(str(t["correct"]) == "True", tc + tt))
        Tt.append(U(str(t["correct"]) == "True", tt))
    if L:
        lad[i] = sum(L) / len(L); th[i] = sum(Tt) / len(Tt)
I = [i for i in ids if i in lad and i in res]
print(f"MC-SEQ: n={len(I)} accuracy {100*sum(res[i][0] for i in I)/len(I):.1f}%  tokens {sum(res[i][1] for i in I)/len(I)/1000:.2f}k  "
      f"samples {sum(res[i][2] for i in I)/len(I):.1f}  utility {sum(U(*res[i][:2]) for i in I)/len(I):.2f}")
print(f"ladder utility {sum(lad[i] for i in I)/len(I):.2f}   gpt-oss-120b think-then-program utility {sum(th[i] for i in I)/len(I):.2f}")
for nm, D in (("ladder", lad), ("oss120 think-then-program", th)):
    d = {i: U(*res[i][:2]) - D[i] for i in I}; rng = random.Random(1); B = 4000
    bs = sorted(sum(d[rng.choice(I)] for _ in I) / len(I) for _ in range(B))
    print(f"  MC-SEQ - {nm}: {sum(d.values())/len(I):+.2f} [{bs[int(.025*B)]:+.2f}, {bs[int(.975*B)-1]:+.2f}] p={(sum(x<=0 for x in bs)+1)/(B+1):.4f}")
