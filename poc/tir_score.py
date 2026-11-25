"""TIR-N scorer (PREREG_DIFF): native-tool gpt-oss-120b against this project's recipe on each set, paired by problem (stored rows of the recipe, seed means). usage: python tir_score.py [effort]"""
import json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); R = f"{ROOT}/results/x44"; R3 = f"{ROOT}/results/x3"
L = lambda f: {json.loads(l)["id"]: json.loads(l) for l in open(f)} if os.path.exists(f) else None
U = lambda a, t: 100 * a - 0.5 * t / 1000
ok = lambda r: str(r["correct"]) == "True"; tk = lambda r: int(r.get("out_tokens") or 0)


def ci(d, key=None, n=4000):
    """paired bootstrap; key = cluster of each item (MathConstruct: several parameter instances per problem)"""
    rng = random.Random(1)
    if key is None:
        b = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(n))
    else:
        g = {}
        for x, k in zip(d, key):
            g.setdefault(k, []).append(x)
        g = list(g.values()); b = []
        for _ in range(n):
            s = [rng.choice(g) for _ in g]; m = [x for v in s for x in v]; b.append(sum(m) / len(m))
        b.sort()
    return f"{sum(d)/len(d):+.2f} [{b[int(.025*n)]:+.2f}, {b[int(.975*n)-1]:+.2f}]"


def mean(arms):
    """seed mean of several row files -> {id: (accuracy, tokens)}"""
    arms = [a for a in arms if a]
    ids = set.intersection(*(set(a) for a in arms)) if arms else set()
    return {i: (sum(ok(a[i]) for a in arms) / len(arms), sum(tk(a[i]) for a in arms) / len(arms)) for i in ids}


def show(st, eff, T, arms, key=None):
    t = {i: (float(ok(r)), tk(r)) for i, r in T.items()}; n = len(t)
    s = lambda v: f"{100*sum(a for a, _ in v.values())/len(v):.1f}% @ {sum(x for _, x in v.values())/len(v)/1000:.2f}k u {sum(U(*x) for x in v.values())/len(v):.2f}"
    print(f"== {st} ({eff}) n={n}  TIR {s(t)}  calls {sum(r['calls'] for r in T.values())/n:.1f}  finish {dict((k, sum(r['finish'] == k for r in T.values())) for k in sorted(set(r['finish'] for r in T.values())))}")
    for k, v in arms.items():
        ids = [i for i in t if i in v]
        if not ids:
            print(f"   {k}: no rows"); continue
        ky = [key(i) for i in ids] if key else None
        print(f"   vs {k} {s({i: v[i] for i in ids})} (n={len(ids)}): accuracy {ci([100*(t[i][0]-v[i][0]) for i in ids], ky)}  ktok {ci([(t[i][1]-v[i][1])/1000 for i in ids], ky)}  utility {ci([U(*t[i])-U(*v[i]) for i in ids], ky)}")


def regrade(st, T):
    """Project Euler: the answer reader also strips LaTeX digit grouping (303\\,963 ...), as every other reader does (2026-11-25: 2 of the first 20 right answers were marked wrong); competition answers by the corrected ma_effort reader"""
    if not T:
        return T
    import ma_effort as M
    import run_compute as RC
    g = {p["id"]: p["answer"] for p in RC.problems(st)} if st.startswith("euler") else {p["id"]: p["gold"].strip() for p in M.PROBS}
    ch = 0
    for i, r in T.items():
        a = M.ans(r["final"]) or ""; ok2 = bool(a) and RC.norm(a) == RC.norm(g[i]); ch += ok2 != bool(r["correct"]); r["correct"] = ok2
    print(f"{st}: {ch} grades changed by the corrected reader")
    return T


def main(eff):
    for st in ("euler", "eulert"):
        T = regrade(st, L(f"{R}/tir_{st}_{eff}_s1.jsonl"))
        if T:
            show(st, eff, T, {"think-then-program (3 seeds)": mean([L(f"{R}/{st}_oss120_thinkp_s{s}.jsonl") for s in (1, 2, 3)]), "think-then-program with CHECKS (3 seeds)": mean([L(f"{R}/{st}_oss120_thinkpc_s{s}.jsonl") for s in (1, 2, 3)])})
    T = L(f"{R}/tir_mconf_{eff}_s1.jsonl")
    if T:
        pol = {}
        for s in (1, 2, 3):
            C, RP, TH = (L(f"{R}/mconf_oss120_{m}_s{s}.jsonl") for m in ("progc", "progcR", "thinkp"))
            if not (C and TH):
                continue
            for i in C:
                c = C[i]; t = tk(c)
                if str(c.get("verify")) == "True":
                    z = (ok(c), t)
                else:
                    r = (RP or {}).get(i)
                    if r is not None and r.get("verify") is True:
                        z = (ok(r), t + tk(r))
                    elif i in TH:
                        z = (ok(TH[i]), t + (tk(r) if r else 0) + tk(TH[i]))
                    else:
                        continue
                pol.setdefault(i, []).append(z)
        pol = {i: (sum(a for a, _ in v) / len(v), sum(b for _, b in v) / len(v)) for i, v in pol.items()}
        nm = {json.loads(l)["id"]: json.loads(l)["name"] for l in open(os.path.join(os.environ.get("POC_DATA", os.path.join(os.path.dirname(ROOT), "nlp_data")), "construct", "instances.jsonl"))}
        show("mconf", eff, T, {"MC-R (verify, one repair, think)": pol, "think-then-program (3 seeds)": mean([L(f"{R}/mconf_oss120_thinkp_s{s}.jsonl") for s in (1, 2, 3)])}, key=lambda i: nm.get(i, i))
    T = L(f"{R}/tir_oeisf_{eff}_s1.jsonl")
    if T:
        D = L(f"{R}/oeisf_diff_all_tp.jsonl")
        show("oeisf", eff, T, {"one thinking program": mean([L(f"{R}/oeisf_oss120M_think_s{s}.jsonl") for s in (2, 3)]), "two thinking + DIFF": {i: (float(d["right"]), d["pool_tok"] + d["oracle_tok"]) for i, d in D.items()} if D else {}})
    T = regrade("comp", L(f"{R}/tir_comp_{eff}_s1.jsonl"))
    if T:
        g = lambda e: {i: r for i, r in {}.items()}
        import ma_effort as M_
        import ma_stop as ST
        GO = {p["id"]: p["gold"].strip() for p in M_.PROBS}; fe = {}
        for (i, s), v in ST.load().items():
            fe.setdefault(i, []).append((float(v[1][-1]["correct"]), v[1][-1]["cut"] + v[1][-1]["tok"]))
        fe = {i: (sum(a for a, _ in v) / len(v), sum(b for _, b in v) / len(v)) for i, v in fe.items()}
        f = lambda e: [dict((i, {"correct": (M_.clean(r["ans"]) if r["ans"] else None) == GO[i], "out_tokens": r["tok"], "ans": r["ans"]}) for i, r in x.items()) for x in [L(f"{R}/ma_oss120{e}_s{s}.jsonl") for s in (1, 2, 3)] if x]
        H, M = f("high"), f("medium"); ret = {}
        for h, m in zip(H, M):
            for i in h:
                if i in m:
                    a = (float(h[i]["correct"]), h[i]["out_tokens"]) if h[i]["ans"] is not None else (float(m[i]["correct"]), h[i]["out_tokens"] + m[i]["out_tokens"])
                    ret.setdefault(i, []).append(a)
        ret = {i: (sum(a for a, _ in v) / len(v), sum(b for _, b in v) / len(v)) for i, v in ret.items()}
        show("comp", eff, T, {"high": mean(H), "medium": mean(M), "high + medium retry at the cap": ret, "high, forced answer at the end of the thinking (recipe)": fe})
    import wp_crossref as C
    pool = {"t": {}, "o": {}, "r": {}}
    for st in ("optc", "indc", "mamoc", "bwor", "logior", "optmath", "optnew"):
        T = L(f"{R}/tir_{st}_{eff}_s1.jsonl")
        if not T:
            continue
        RN, P, A, _, _, A2 = C.load(st)
        one = {i: (float(ok(A[i])), tk(A[i])) for i in P}; ret = {i: one[i] if A[i]["pred"] is not None else (float(ok(A2[i])), tk(A[i]) + tk(A2[i])) for i in P}
        show(st, eff, T, {"one program": one, "RETRY": ret})
        for i in T:
            pool["t"][(st, i)] = T[i]; pool["o"][(st, i)] = one[i]; pool["r"][(st, i)] = ret[i]
    if pool["t"]:
        show("word problems pooled", eff, pool["t"], {"one program": pool["o"], "RETRY": pool["r"]})


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "medium")
