"""B4 analysis (docs/prereg/PREREG_B4.md): DRoC-style retrieval vs BM25 top-3 vs exact snippet (CVRP, VRPTW; Qwen3-32B, Llama-70B), and the
restate-the-fields prompt vs the literal stdin (VRPTW, gpt-oss). Opt = optimal and feasible; tokens = output tokens per instance incl. the
DRoC decomposition / filter calls and repairs.
usage: python analyze_b4.py"""
import json, os, random, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repository root (was hard-coded)
RES = f"{ROOT}/results"


def load(tag):
    p = f"{RES}/co_{tag}.jsonl"
    return {r["key"]: r for r in map(json.loads, open(p))} if os.path.exists(p) else {}


opt = lambda r: bool(r["feasible"]) and r["gap"] is not None and abs(r["gap"]) < 1e-9


def pooled(prefix):
    out = {}
    for sd in (1, 2):
        for k, r in load(f"{prefix}_s{sd}").items():
            out[(k, sd)] = r
    return out


def diff(a, b, B=10000):
    ks = sorted(set(a) & set(b)); d = [opt(b[k]) - opt(a[k]) for k in ks]; rng = random.Random(0); n = len(d)
    if not n:
        return None
    bs = sorted(sum(d[rng.randrange(n)] for _ in range(n)) / n for _ in range(B))
    return sum(d) / n, bs[int(.025 * B)], bs[int(.975 * B)]


print("=== B4a: retrieval arms (2 seeds x 30 instances per problem)")
for m in ("q32b", "l70"):
    for prob in ("cvrp", "vrptw", "both"):
        probs = ("cvrp", "vrptw") if prob == "both" else (prob,)
        A = {arm: {(p_,) + k: v for p_ in probs for k, v in pooled(f"S2_B4_co{m}_{p_}_{arm}").items()} for arm in ("snippet", "bm25top3", "droc")}
        if not all(A.values()):
            print(f"  {m} {prob}: missing"); continue
        line = f"  {m:5s} {prob:6s}"
        for arm, R in A.items():
            line += f" | {arm} {sum(map(opt, R.values()))}/{len(R)} ({sum(map(opt, R.values())) / len(R):.2f}) @ {sum(r['out_tokens'] for r in R.values()) / len(R):5.0f} tok"
        d1 = diff(A["bm25top3"], A["droc"]); d2 = diff(A["snippet"], A["droc"])
        line += f" || droc-bm25 {d1[0]:+.2f} [{d1[1]:+.2f},{d1[2]:+.2f}] droc-snippet {d2[0]:+.2f} [{d2[1]:+.2f},{d2[2]:+.2f}]"
        print(line)
        if prob != "both":
            D = A["droc"].values()
            kept = Counter(c for r in D for c in (r.get("droc") or {}).get("kept", []))
            retr = Counter(c for r in D for c in (r.get("droc") or {}).get("retrieved", []))
            print(f"      DRoC retrieved {dict(retr.most_common())}\n      DRoC kept      {dict(kept.most_common())}")
            errs = Counter(("ok" if opt(r) else (r["status"] + ":" + (r.get("err") or "").strip().splitlines()[-1][:60] if r.get("err") else r["status"]))
                           for r in D)
            print(f"      DRoC outcomes  {errs.most_common(4)}")

print("\n=== B4b: restate the input fields (VRPTW, exact snippet, gpt-oss low)")
from analyze_vrptw_stdin import label  # noqa: E402
from concurrent.futures import ThreadPoolExecutor  # noqa: E402
for m, refs in (("oss120low", ("S2_W_cooss120low_doctask_s1", "S2_W_cooss120low_doctask_ex_s1", "S2_W_cooss120low_doctask_ex_s2")),
                ("oss20low", ("W_cooss20low_doctask_s1", "W_cooss20low_doctask_s2", "S2_W_cooss20low_doctask_ex_s1", "S2_W_cooss20low_doctask_ex_s2"))):
    for tag in refs + (f"S2_B4_co{m}_vrptw_restate_s1", f"S2_B4_co{m}_vrptw_restate_s2"):
        R = list(load(tag).values())
        if not R:
            print(f"  {tag}: missing"); continue
        with ThreadPoolExecutor(16) as ex:
            labs = list(ex.map(label, R))
        print(f"  {tag:36s} opt {sum(map(opt, R))}/{len(R)}  tokens {sum(r['out_tokens'] for r in R) / len(R):5.0f}  skips service {labs.count('skips_service')}")
