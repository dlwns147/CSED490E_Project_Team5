"""E3 analysis (pre-registered in results/PREREG_E3.md): simulate the "check, then sample, then think" pipeline from stored independent runs.
Stage 1 = C1 seed 1; stage 2 = C1 seeds 2-3 (MR-select over the 3); stage 3 = one escalation program (budget-forced thinking 1,024, or a
self-generated hint). Baselines: single program, always best-of-3 + MR (no escalation), always budget-thinking, always full thinking.
Accuracy = correct on all 8 variants; tokens = mean output tokens actually spent per instance (incl. the self-hint call).
usage: python analyze_e3.py [model=8b]"""
import json, os, random, sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_geo import base_instance, variants  # noqa: E402
from run_geo_mr import mr_check  # noqa: E402

RES = "/NAS/SJ/POSTECH/nlp/results"
M = sys.argv[1] if len(sys.argv) > 1 else "8b"


def load(tag):
    p = f"{RES}/geocross_{tag}.jsonl"
    return {(r["task"], r["n"], r["inst"]): r for r in map(json.loads, open(p))} if os.path.exists(p) else {}


def ok(r):
    return r is not None and r["class"] == "correct_all"


def consistent(r):
    if not r or not r.get("code"):
        return None
    rng = random.Random(f"{r['task']}-{r['n']}-{r['inst']}")
    V = variants(r["task"], base_instance(r["task"], r["n"], rng), rng)
    base, bad = mr_check(r["code"], r["task"], V)
    return base if base is not None and not bad else None


def ci(d, B=10000):
    rng = random.Random(0); n = len(d); bs = sorted(sum(d[rng.randrange(n)] for _ in range(n)) / n for _ in range(B))
    return 100 * sum(d) / n, 100 * bs[int(.025 * B)], 100 * bs[int(.975 * B)]


for cond in ("dis0", "dis8", "hard"):
    S = [load(f"S2_C1_geox{M}_{cond}_t07s{s}") for s in (1, 2, 3)]
    E = {e: load(f"S2_E3_geox{M}_{cond}_{e}_t07s1") for e in ("b1024", "selfhint", "think")}
    keys = sorted(k for k in S[0] if all(k in s for s in S) and all(k in e for e in E.values()))
    if not keys:
        print(f"{cond}: missing runs ({[len(e) for e in E.values()]})"); continue

    def one(k):
        r = [s[k] for s in S]; c = [consistent(x) for x in r]
        tok1, tok3 = r[0]["out_tokens"], sum(x["out_tokens"] for x in r)
        if c[0] is not None:
            stage, picked, tok = 1, r[0], tok1
        else:
            cands = [(x, b) for x, b in zip(r, c) if b is not None]
            if cands:
                vote = Counter(b for _, b in cands).most_common(1)[0][0]
                stage, picked, tok = 2, next(x for x, b in cands if b == vote), tok3
            else:
                stage, picked, tok = 3, None, tok3
        k3 = picked if stage < 3 else None   # always best-of-3 + MR (no consistent candidate = failure), tokens = tok3
        out = {"stage": stage, "single": ok(r[0]), "k3": ok(k3), "tok1": tok1, "tok3": tok3}
        for e in ("b1024", "selfhint"):
            out[f"pipe_{e}"] = ok(picked) if stage < 3 else ok(E[e][k])
            out[f"pipe_{e}_tok"] = tok + (E[e][k]["out_tokens"] if stage == 3 else 0)
        for e in ("b1024", "selfhint", "think"):
            out[f"always_{e}"] = ok(E[e][k]); out[f"always_{e}_tok"] = E[e][k]["out_tokens"]
        return k[0], out

    with ThreadPoolExecutor(24) as ex:
        res = list(ex.map(one, keys))
    n = len(res); R = [o for _, o in res]
    acc = lambda f: 100 * sum(o[f] for o in R) / n
    tok = lambda f: sum(o[f] for o in R) / n
    st = Counter(o["stage"] for o in R)
    print(f"\n=== {M} {cond}: {n} instances; pipeline stopped at stage 1 / 2 / 3: {st[1]} / {st[2]} / {st[3]}")
    rows_ = [("single program", "single", "tok1"), ("always best-of-3 + MR", "k3", "tok3"),
             ("PIPELINE (escalate: think 1,024)", "pipe_b1024", "pipe_b1024_tok"), ("PIPELINE (escalate: self-hint)", "pipe_selfhint", "pipe_selfhint_tok"),
             ("always budget-think 1,024", "always_b1024", "always_b1024_tok"), ("always self-hint", "always_selfhint", "always_selfhint_tok"),
             ("always full thinking", "always_think", "always_think_tok")]
    for name, f, t in rows_:
        print(f"  {name:34s} {acc(f):5.1f}%   {tok(t):7.0f} tokens/instance")
    for a, b in (("pipe_b1024", "k3"), ("pipe_b1024", "always_think"), ("pipe_selfhint", "k3")):
        m, lo, hi = ci([o[a] - o[b] for o in R]); print(f"  {a} - {b}: {m:+.1f} [{lo:+.1f}, {hi:+.1f}]")
    print(f"  token ratio pipeline(b1024) / always full thinking: {tok('pipe_b1024_tok') / tok('always_think_tok'):.2f}; "
          f"/ best-of-3: {tok('pipe_b1024_tok') / tok('tok3'):.2f}")
    for t in sorted({t for t, _ in res}):
        Rt = [o for tt, o in res if tt == t]; m = len(Rt)
        print(f"    {t:9s} single {100 * sum(o['single'] for o in Rt) / m:5.1f} | k3+MR {100 * sum(o['k3'] for o in Rt) / m:5.1f} | "
              f"pipe {100 * sum(o['pipe_b1024'] for o in Rt) / m:5.1f} | think {100 * sum(o['always_think'] for o in Rt) / m:5.1f} | "
              f"stage3 {sum(o['stage'] == 3 for o in Rt)}")
