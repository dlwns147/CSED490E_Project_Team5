"""SIZE (docs/prereg/PREREG_SIZE.md): the size ladder Qwen3-1.7B / 4B / 8B / 32B on the U1 suites and X6, with cost as output tokens
and as compute = parameters (billions) x output tokens, and the cross-size cascade (small model with the fact, escalate to Qwen3-32B
thinkf when the program fails the check).
usage: python analyze_size.py [q17 q4b q8b q32b]"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_argv, sys.argv = sys.argv, sys.argv[:1]   # analyze_u1 -> analyze_n12 read sys.argv at import
import analyze_u1 as U  # noqa: E402
sys.argv = _argv

X3 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "x3")
PARAMS = {"q17": 1.7, "q4b": 4.0, "q8b": 8.2, "q14a": 14.8, "oss20": 3.6, "q32b": 32.8}   # ACTIVE parameters, billions (model cards;
# AWQ keeps the count; gpt-oss-20b is a mixture of experts with 3.6B active of 21B)


def x6(m, arm, s):
    f = f"{X3}/opt_{m}_{arm}_s{s}.jsonl"
    return {r["id"]: r for r in map(json.loads, open(f))} if os.path.exists(f) else None


def passes(r):
    return r["status"] == "ok" and r.get("pred") is not None


def x6_table(models):
    print("=== X6 (NL4OPT + IndustryOR, 345 x 3): accuracy @ output tokens | compute (B params x tokens, per item)")
    for m in models:
        cells = []
        for arm in ("mip", "mipf", "think", "thinkf"):
            rows = [r for s in (1, 2, 3) for r in (x6(m, arm, s) or {}).values()]
            if len(rows) < 1035:
                cells.append(f"{arm} incomplete ({len(rows)})"); continue
            acc = sum(r["correct"] for r in rows) / len(rows); tok = sum(r["out_tokens"] or 0 for r in rows) / len(rows)
            cells.append(f"{arm} {100 * acc:.1f}% @ {tok:.0f} ({PARAMS[m] * tok / 1000:.1f}k)")
        print(f"  {m:5}", " | ".join(cells))


def cascade(small, big="q32b"):
    """small mipf; if its program fails the check, big thinkf (same seed)"""
    a = t = c = esc = n = 0
    for s in (1, 2, 3):
        S, B = x6(small, "mipf", s), x6(big, "thinkf", s)
        if not S or not B or len(S) < 345 or len(B) < 345:
            return None
        for i, r in S.items():
            n += 1; t += r["out_tokens"] or 0; c += PARAMS[small] * (r["out_tokens"] or 0)
            if passes(r):
                a += r["correct"]
            else:
                esc += 1; b = B[i]; a += b["correct"]; c += PARAMS[big] * (b["out_tokens"] or 0)
    return a / n, c / n, esc / n


def u1_table(models):
    print("=== U1 suites: base_s1 / ALWAYS-FACT / THINK accuracy @ output tokens (cure seeds 1-3 for FACT and THINK)")
    for m in models:
        for dom in ("geo", "co"):
            base = U.load(m, dom, "base_s1")
            if base is None:
                print(f"  {m} {dom}: incomplete"); continue
            out = [f"base {100 * sum(U.ok(dom, r) for r in base.values()) / len(base):.1f}%"]
            for arm in ("fact", "think"):
                v = []
                for s in (1, 2, 3):
                    f = f"{U.RES}/{'geocross' if dom == 'geo' else 'co'}_S2_U1_{m}_{dom}_{arm}_s{s}.jsonl"
                    if os.path.exists(f):
                        R = [json.loads(l) for l in open(f)]
                        v.append(f"{100 * sum(U.ok(dom, r) for r in R) / len(R):.0f}%@{sum(r.get('out_tokens') or 0 for r in R) / len(R) / 1000:.1f}k")
                out.append(f"{arm} " + " / ".join(v))
            print(f"  {m:5} {dom:3}", " | ".join(out))


if __name__ == "__main__":
    models = sys.argv[1:] or ["q17", "q4b", "q8b", "q14a", "oss20", "q32b"]
    x6_table(models)
    big = x6("q32b", "thinkf", 1)
    if big:
        rows = [r for s in (1, 2, 3) for r in x6("q32b", "thinkf", s).values()]
        ref = (sum(r["correct"] for r in rows) / len(rows), PARAMS["q32b"] * sum(r["out_tokens"] or 0 for r in rows) / len(rows))
        print(f"=== cross-size cascade (small mipf -> Qwen3-32B thinkf on a failed check); Qwen3-32B always-thinkf {100 * ref[0]:.1f}% @ compute {ref[1] / 1000:.1f}k")
        for m in models:
            if m == "q32b":
                continue
            r = cascade(m)
            print(f"  {m:5}", "incomplete" if r is None else f"{100 * r[0]:.1f}% @ compute {r[1] / 1000:.1f}k ({100 * r[1] / ref[1]:.0f}% of always-thinkf), escalated {100 * r[2]:.0f}%")
    u1_table(models)
