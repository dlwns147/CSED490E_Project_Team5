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


def load():
    X = {}
    for s in (1, 2):
        T = {r["id"]: r for r in rows(f"{R}/stop_trace_s{s}.jsonl")}; P = {}
        for z in rows(f"{R}/stop_probe_s{s}.jsonl"):
            P.setdefault(z["id"], []).append(z)
        for i, r in T.items():
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


if __name__ == "__main__":
    {"trace": lambda: trace(int(sys.argv[2])), "probe": lambda: probe(int(sys.argv[2])), "headroom": headroom}[sys.argv[1]]()
