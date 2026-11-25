"""PREREG_DIFF addendum STOP (registered 2026-11-25): when should one high-effort sample stop thinking? (competition answers, gpt-oss-120b)
trace:  raw harmony completions with token ids (so a think can be cut exactly)  -> results/x44/stop_trace_s<seed>.jsonl
probe:  at geometric cuts of the analysis channel, force the final channel and read the answer + its probability -> results/x44/stop_probe_s<seed>.jsonl
usage: POC_BASE_URL=... python ma_stop.py trace <seed>  |  ... probe <seed>   |   python ma_stop.py headroom | score"""
import json, os, random, re, sys, zlib, math
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ma_effort as M
PROBS, R, ans = M.PROBS, M.R, M.ans
CAP = 38000
CUTS = [int(512 * 2 ** (k / 2)) for k in range(13)]          # 512 ... 32768, ratio sqrt(2): a resolution, not a tuned choice; the rule decides where to stop
END, START, MSG, CHAN = 200007, 200006, 200008, 200005       # harmony special tokens <|end|> <|start|> <|message|> <|channel|>
HEAD = ("<|start|>system<|message|>You are ChatGPT, a large language model trained by OpenAI.\nKnowledge cutoff: 2024-06\nCurrent date: 2026-11-25\n\nReasoning: {e}\n\n"
        "# Valid channels: analysis, commentary, final. Channel must be included for every message.<|end|><|start|>user<|message|>{q}<|end|><|start|>assistant")
FORCE = "<|end|><|start|>assistant<|channel|>final<|message|>The final answer is $\\boxed{"


def rows(p):
    return [json.loads(l) for l in open(p)] if os.path.exists(p) else []


def comp(**k):
    import llm
    return llm.client.completions.create(model="local", extra_body={"return_token_ids": True, "skip_special_tokens": False, **k.pop("extra", {})}, **k)


def trace(seed):
    out = f"{R}/stop_trace_s{seed}.jsonl"; done = {r["id"] for r in rows(out)}

    def one(p):
        r = comp(prompt=HEAD.format(e="high", q=M.PROMPT.format(p=p["problem"])), temperature=1.0, top_p=0.95, max_tokens=CAP, seed=seed * 1000 + zlib.crc32(p["id"].encode()) % 997)
        c = r.choices[0]; ids = list(c.token_ids); text = c.text or ""
        fin = text.split("<|channel|>final<|message|>")[-1] if "<|channel|>final<|message|>" in text else None
        a = ans(fin) if fin else None
        return {"id": p["id"], "comp": p["comp"], "ids": ids, "prompt_ids": list(c.prompt_token_ids or []), "ans": a, "correct": a is not None and a == p["gold"].strip(),
                "tok": r.usage.completion_tokens, "finish": c.finish_reason, "tail": text[-600:]}
    with ThreadPoolExecutor(48) as ex, open(out, "a") as f:
        for z in ex.map(one, [p for p in PROBS if p["id"] not in done]):
            f.write(json.dumps(z) + "\n"); f.flush()


def analysis_len(ids):
    """number of generated tokens up to (not including) the end of the analysis channel"""
    return ids.index(END) if END in ids else len(ids)


def probe(seed):
    import llm
    out = f"{R}/stop_probe_s{seed}.jsonl"; done = {(r["id"], r["cut"]) for r in rows(out)}
    tokz = lambda s: llm.post_json("/tokenize", {"model": "local", "prompt": s, "add_special_tokens": False})["tokens"]
    force = tokz(FORCE); gold = {p["id"]: p["gold"].strip() for p in PROBS}
    jobs = []
    for r in rows(f"{R}/stop_trace_s{seed}.jsonl"):
        n = analysis_len(r["ids"])
        for c in [c for c in CUTS if c < n] + [n]:          # the last probe is the end of the analysis (or the cap): the zero-think-token control
            if (r["id"], c) not in done:
                jobs.append((r, c, n))

    def one(j):
        r, c, n = j
        z = comp(prompt=r["prompt_ids"] + r["ids"][:c] + force, temperature=0.0, max_tokens=32, stop=["}"], logprobs=1)
        ch = z.choices[0]; a = re.sub(r"[\s,$]|\\[,!;]|\\text\{[^}]*\}", "", ch.text or "").lstrip("+").split("}")[0]
        lp = [x for x in (ch.logprobs.token_logprobs or []) if x is not None]
        return {"id": r["id"], "cut": c, "n": n, "ans": a, "correct": a == gold[r["id"]], "lp": sum(lp), "tok": z.usage.completion_tokens}
    with ThreadPoolExecutor(48) as ex, open(out, "a") as f:
        for z in ex.map(one, jobs):
            f.write(json.dumps(z) + "\n"); f.flush()
    print("probes", len(rows(out)))


U = lambda ok, t: 100 * ok - 0.5 * t / 1000


def ci(d, n=4000):
    rng = random.Random(1); b = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(n))
    return f"{sum(d)/len(d):+.2f} [{b[int(.025*n)]:+.2f}, {b[int(.975*n)-1]:+.2f}]"


GOLD = {p["id"]: p["gold"].strip() for p in PROBS}


def load():
    """rows with the own answer re-read by the corrected reader (M.ans) from the stored tail, or from the stored string when the tail holds no box"""
    X = {}
    for s in (1, 2):
        T = {r["id"]: r for r in rows(f"{R}/stop_trace_s{s}.jsonl")}; P = {}
        for z in rows(f"{R}/stop_probe_s{s}.jsonl"):
            P.setdefault(z["id"], []).append(z)
        for i, r in T.items():
            a = ans(r["tail"].split("<|channel|>final<|message|>")[-1]) if r["finish"] == "stop" else None
            r["ans"] = a if a is not None else (M.clean(r["ans"]) if r["ans"] else None); r["correct"] = r["ans"] == GOLD[i]
            if i in P:
                X[(i, s)] = (r, sorted(P[i], key=lambda z: z["cut"]))
    return X


def by_problem(X, f, g=None):
    """per-problem means of f (minus g), so that seeds of one problem are one unit"""
    d = {}
    for (i, s), v in X.items():
        d.setdefault(i, []).append(f(v) - (g(v) if g else 0))
    return [sum(v) / len(v) for v in d.values()]


def headroom():
    X = load(); arms = {}
    full = lambda v: (bool(v[0]["correct"]), v[0]["tok"])
    last = lambda v: (bool(v[1][-1]["correct"]) if v[0]["ans"] is None else bool(v[0]["correct"]), v[0]["tok"] + (v[1][-1]["tok"] if v[0]["ans"] is None else 0))
    forced_end = lambda v: (bool(v[1][-1]["correct"]), v[1][-1]["cut"] + v[1][-1]["tok"])

    def oracle(v):                                   # hindsight best: the best utility over every stop (probes up to it charged) and the full sample
        best = max([last(v)], key=lambda x: U(*x)); t = 0
        for z in v[1]:
            t += z["tok"]; best = max(best, (bool(z["correct"]), z["cut"] + t), key=lambda x: U(*x))
        return best
    arms = {"HIGH": full, "HIGH + forced answer at the cap": last, "forced answer at the end of the analysis": forced_end, "oracle stop (hindsight)": oracle}
    print(f"n={len(X)} traces; no answer at the cap: {sum(v[0]['ans'] is None for v in X.values())}, of which the forced answer is right: {sum(v[0]['ans'] is None and v[1][-1]['correct'] for v in X.values())}")
    for k, f in arms.items():
        z = [f(v) for v in X.values()]
        print(f"{k:42s} accuracy {100*sum(a for a, _ in z)/len(z):.1f}% tokens {sum(t for _, t in z)/len(z)/1000:.2f}k utility {sum(U(*x) for x in z)/len(z):.2f}   − HIGH {ci(by_problem(X, lambda v: U(*f(v)), lambda v: U(*full(v))))}")
    for c in CUTS:
        z = [([p for p in v[1] if p["cut"] == c] or [None])[0] for v in X.values()]
        z2 = [p for p in z if p]
        print(f"  cut {c:6d}: still thinking {len(z2):3d}  forced answer right {100*sum(p['correct'] for p in z2)/max(1,len(z2)):.1f}%")


def feats(P, k):
    z = P[k]; run = 1
    while run <= k and P[k - run]["ans"] == z["ans"]:
        run += 1
    pr = math.exp(max(-20, z["lp"])); valid = bool(re.fullmatch(r"-?\d+", z["ans"])); lc = math.log2(z["cut"] / 512) / 12; dis = len({P[q]["ans"] for q in range(k + 1)}) / (k + 1)
    b = [1.0, pr, float(valid), math.log(run), (run - 1) / (k + 1), dis, lc]
    return b + [pr * math.log(run), pr * lc, math.log(run) * lc, pr * pr]


def fit_rule(tr, np, lam):
    """Longstaff-Schwartz: backward over probe positions; stop value and continuation value regressed (ridge, features standardised) on the pooled states; returns the two weight vectors. The last probe (end of analysis or cap) always stops."""
    S = []                                              # states (trace index, probe index)
    for j, P in enumerate(tr):
        S += [(j, k) for k in range(len(P))]
    F = np.array([feats(tr[j], k) for j, k in S]); mu, sd = F.mean(0), F.std(0) + 1e-9; mu[0], sd[0] = 0, 1; G = (F - mu) / sd
    R = np.eye(G.shape[1]) * lam; R[0, 0] = 1e-6
    ws = np.linalg.solve(G.T @ G + R, G.T @ np.array([100.0 * tr[j][k]["correct"] for j, k in S]))
    sv = dict(zip(S, G @ ws)); row = dict(zip(S, range(len(S)))); wc = np.zeros(G.shape[1])
    for _ in range(12):                                 # policy iteration on the pooled continuation value
        y, x = [], []
        for j, P in enumerate(tr):
            val = None
            for k in range(len(P) - 1, -1, -1):
                if k == len(P) - 1:
                    val = 100.0 * P[k]["correct"]
                else:
                    cont = val - 0.5 * (P[k + 1]["cut"] - P[k]["cut"] + P[k + 1]["tok"]) / 1000
                    x.append(row[(j, k)]); y.append(cont)
                    val = 100.0 * P[k]["correct"] if sv[(j, k)] >= G[row[(j, k)]] @ wc else cont
        A = G[x]; new = np.linalg.solve(A.T @ A + R, A.T @ np.array(y))
        if np.abs(new - wc).max() < 1e-6:
            break
        wc = new
    return lambda P, k: ((np.array(feats(P, k)) - mu) / sd) @ ws >= ((np.array(feats(P, k)) - mu) / sd) @ wc


def play(P, stop):
    t = 0
    for k, z in enumerate(P):
        t += z["tok"]
        if k == len(P) - 1 or stop(P, k):
            return bool(z["correct"]), z["cut"] + t


def score():
    import numpy as np
    X = load(); comp_of = {p["id"]: p["comp"] for p in PROBS}; comps = sorted(set(comp_of.values())); res = {}
    last = lambda v: (bool(v[0]["correct"]), v[0]["tok"]) if v[0]["ans"] is not None else (bool(v[1][-1]["correct"]), v[0]["tok"] + v[1][-1]["tok"])
    run = lambda P, k: next((r for r in range(1, k + 2) if r == k + 1 or P[k - r]["ans"] != P[k]["ans"]), 1)
    mu = lambda f, K: sum(U(*f(X[x])) for x in K) / len(K)
    for c in comps:
        tr = [x for x in X if comp_of[x[0]] != c]; te = [x for x in X if comp_of[x[0]] == c]; inner = sorted({comp_of[x[0]] for x in tr})
        # ridge strength by inner leave-one-competition-out utility
        best = None
        for lam in (0.1, 1, 10, 100, 1000):
            u = 0
            for c2 in inner:
                st = fit_rule([X[x][1] for x in tr if comp_of[x[0]] != c2], np, lam); u += sum(U(*play(X[x][1], st)) for x in tr if comp_of[x[0]] == c2)
            best = max(best or (-1e9, 0), (u, lam))
        rules = {"OPTSTOP (ours)": fit_rule([X[x][1] for x in tr], np, best[1])}
        rules["static budget"] = max(((lambda P, k, c0=c0: P[k]["cut"] >= c0) for c0 in CUTS + [10 ** 9]), key=lambda s: mu(lambda v: play(v[1], s), tr))
        rules["answer convergence"] = max(((lambda P, k, r=r: run(P, k) >= r) for r in range(1, 14)), key=lambda s: mu(lambda v: play(v[1], s), tr))
        q = sorted(math.exp(z["lp"]) for x in tr for z in X[x][1]); rules["confidence threshold"] = max(((lambda P, k, a=a: math.exp(P[k]["lp"]) >= a) for a in [q[int(len(q) * g / 40)] for g in range(1, 40)] + [0.999, 0.9999, 2]), key=lambda s: mu(lambda v: play(v[1], s), tr))
        for x in te:
            for n, s in rules.items():
                res.setdefault(n, {})[x] = play(X[x][1], s)
            res.setdefault("HIGH", {})[x] = (bool(X[x][0]["correct"]), X[x][0]["tok"]); res.setdefault("HIGH + forced answer at the cap", {})[x] = last(X[x]); res.setdefault("forced answer at the end of the analysis", {})[x] = play(X[x][1], lambda P, k: False)
        print("fold", c, "n", len(te), "ridge", best[1], flush=True)
    for e in ("medium",):
        for s in (1, 2):
            f = f"{R}/ma_oss120{e}_s{s}.jsonl"
            for r in rows(f):
                a = M.clean(r["ans"]) if r["ans"] else None; res.setdefault("MEDIUM (stored seeds 1-2)", {})[(r["id"], s)] = (a == GOLD[r["id"]], r["tok"])
    H = res["HIGH"]; med = res.get("MEDIUM (stored seeds 1-2)", {})
    res["HIGH + medium retry at the cap (MA-RETRY)"] = {x: H[x] if X[x][0]["ans"] is not None else (med[x][0], H[x][1] + med[x][1]) for x in X if x in med}
    for n, z in res.items():
        print(f"{n:44s} n={len(z)} accuracy {100*sum(a for a, _ in z.values())/len(z):.1f}% tokens {sum(t for _, t in z.values())/len(z)/1000:.2f}k utility {sum(U(*v) for v in z.values())/len(z):.2f}")

    def diff(a, b, f):
        d = {}
        for x in res[a]:
            if x in res[b]:
                d.setdefault(x[0], []).append(f(res[a][x]) - f(res[b][x]))
        return ci([sum(v) / len(v) for v in d.values()])
    for b in [n for n in res if n != "OPTSTOP (ours)"]:
        print(f"OPTSTOP − {b}: accuracy {diff('OPTSTOP (ours)', b, lambda z: 100*z[0])} ktok {diff('OPTSTOP (ours)', b, lambda z: z[1]/1000)} utility {diff('OPTSTOP (ours)', b, lambda z: U(*z))}")
    for a, b in (("HIGH + forced answer at the cap", "HIGH + medium retry at the cap (MA-RETRY)"), ("forced answer at the end of the analysis", "HIGH + forced answer at the cap"), ("HIGH + forced answer at the cap", "HIGH")):
        print(f"{a} − {b}: accuracy {diff(a, b, lambda z: 100*z[0])} ktok {diff(a, b, lambda z: z[1]/1000)} utility {diff(a, b, lambda z: U(*z))}")


if __name__ == "__main__":
    {"trace": lambda: trace(int(sys.argv[2])), "probe": lambda: probe(int(sys.argv[2])), "headroom": headroom, "score": score}[sys.argv[1]]()
