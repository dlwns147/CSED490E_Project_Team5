"""E3b analysis (pre-registered in results/PREREG_E3B.md): differential testing of the first program against a brute-force program written by
the same model (no toolbox, "simplest brute-force program"), on the given instance and 5 transformed copies (no 10^9 copy).
Gate = metamorphic check passes AND outputs agree on all 6 inputs; otherwise escalate to one budget-thinking (1,024) program (E3 run).
usage: python analyze_e3b.py [model=8b]"""
import json, os, random, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_geo import base_instance, variants  # noqa: E402
from run_geo_mr import mr_check, run_out  # noqa: E402

RES = "/NAS/SJ/POSTECH/nlp/results"
M = sys.argv[1] if len(sys.argv) > 1 else "8b"
DIFF = ("identity", "translate", "rot90", "mirror", "permute", "scale")


def load(tag):
    p = f"{RES}/geocross_{tag}.jsonl"
    return {(r["task"], r["n"], r["inst"]): r for r in map(json.loads, open(p))} if os.path.exists(p) else {}


def ok(r):
    return r is not None and r["class"] == "correct_all"


def ci(d, B=10000):
    rng = random.Random(0); n = len(d); bs = sorted(sum(d[rng.randrange(n)] for _ in range(n)) / n for _ in range(B))
    return 100 * sum(d) / n, 100 * bs[int(.025 * B)], 100 * bs[int(.975 * B)]


BRUTE = {**load(f"S2_E3B_geox{M}_brute_core_t07s1"), **load(f"S2_E3B_geox{M}_brute_hard_t07s1")}
for cond in ("dis0", "dis8", "hard"):
    C = load(f"S2_C1_geox{M}_{cond}_t07s1"); E = load(f"S2_E3_geox{M}_{cond}_b1024_t07s1")
    keys = sorted(k for k in C if k in BRUTE and k in E)
    if not keys:
        print(f"{cond}: missing data"); continue

    def one(k):
        c, b = C[k], BRUTE[k]
        task, n, inst = k
        rng = random.Random(f"{task}-{n}-{inst}")
        V = variants(task, base_instance(task, n, rng), rng)
        mr_ok = False
        if c.get("code"):
            base, bad = mr_check(c["code"], task, V); mr_ok = base is not None and not bad
        agree = bool(c.get("code") and b.get("code")) and all(
            (oc := run_out(c["code"], task, V[v])) is not None and oc == run_out(b["code"], task, V[v]) for v in DIFF)
        gate = mr_ok and agree
        return dict(task=task, ok=ok(c), mr=mr_ok, agree=agree, gate=gate, brute_ok=ok(b),
                    pipe=ok(c) if gate else ok(E[k]), pipe_mr=ok(c) if mr_ok else ok(E[k]), always=ok(E[k]),
                    tok=c["out_tokens"] + b["out_tokens"] + (0 if gate else E[k]["out_tokens"]),
                    tok_mr=c["out_tokens"] + (0 if mr_ok else E[k]["out_tokens"]), tok_always=E[k]["out_tokens"])

    with ThreadPoolExecutor(24) as ex:
        R = list(ex.map(one, keys))
    n = len(R)
    miss = [r for r in R if r["mr"] and not r["ok"]]; corr = [r for r in R if r["ok"]]
    print(f"\n=== {M} {cond}: {n} instances | first program correct {len(corr)} | brute-force program correct on all 8 variants "
          f"{sum(r['brute_ok'] for r in R)}")
    print(f"  B1 MR-accepted but wrong: {len(miss)}; flagged by the differential check: {sum(not r['agree'] for r in miss)}"
          f" ({100 * sum(not r['agree'] for r in miss) / max(1, len(miss)):.0f}%)")
    print(f"  B2 false alarms: correct first programs flagged {sum(not r['agree'] for r in corr)}/{len(corr)}"
          f" ({100 * sum(not r['agree'] for r in corr) / max(1, len(corr)):.0f}%)")
    acc = lambda f: 100 * sum(r[f] for r in R) / n; tok = lambda f: sum(r[f] for r in R) / n
    print(f"  escalated: MR gate {sum(not r['mr'] for r in R)}, MR + brute-force gate {sum(not r['gate'] for r in R)}")
    for name, f, t in (("MR-gated -> think 1,024", "pipe_mr", "tok_mr"), ("MR + brute-force gated -> think 1,024", "pipe", "tok"),
                       ("always think 1,024", "always", "tok_always")):
        print(f"  {name:40s} {acc(f):5.1f}% @ {tok(t):6.0f} tokens/instance")
    m, lo, hi = ci([r["pipe"] - r["always"] for r in R]); print(f"  gated - always-think: {m:+.1f} [{lo:+.1f}, {hi:+.1f}];"
                                                               f" token ratio {tok('tok') / tok('tok_always'):.2f}")
    for t in sorted({r["task"] for r in R}):
        Rt = [r for r in R if r["task"] == t]
        print(f"    {t:9s} first {sum(r['ok'] for r in Rt):3d} | brute ok {sum(r['brute_ok'] for r in Rt):3d} | MR-accepted wrong "
              f"{sum(r['mr'] and not r['ok'] for r in Rt):3d} flagged {sum(r['mr'] and not r['ok'] and not r['agree'] for r in Rt):3d} | "
              f"false alarms {sum(r['ok'] and not r['agree'] for r in Rt):3d}/{sum(r['ok'] for r in Rt):3d} | gated {100 * sum(r['pipe'] for r in Rt) / len(Rt):5.1f} "
              f"vs always-think {100 * sum(r['always'] for r in Rt) / len(Rt):5.1f}")
