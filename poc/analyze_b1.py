"""B1 analysis (pre-registered in docs/prereg/PREREG_B1.md): label-free selectors over the same 3 candidates per instance.
Candidates: results/geocross_S2_B1_geox<m>_{dis0,dis8,hard}_t07s{1,2,3}.jsonl (with DeepConf token confidence `ctop`);
model-written tests: results/tests_S2_B1_{core,hard}.jsonl (poc/gen_tests.py). Also the offline DART-style router on the E3 data.
usage: python analyze_b1.py [model=8b]"""
import json, os, random, sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_geo import base_instance, render, variants  # noqa: E402
from run_geo_mr import MR, expected_rel  # noqa: E402
from sandbox import run_python  # noqa: E402

RES = "/NAS/SJ/POSTECH/nlp/results"
M = sys.argv[1] if len(sys.argv) > 1 else "8b"
SEEDS = (1, 2, 3)
N_FRESH = 5


def load(tag):
    p = f"{RES}/{tag}.jsonl"
    return {(r["task"], r["n"], r["inst"]): r for r in map(json.loads, open(p))} if os.path.exists(p) else {}


def out_of(code, stdin):
    if not code:
        return None
    r = run_python(code, stdin, timeout=10)
    return (r.stdout.strip().split() or [None])[-1].lower() if r.status == "ok" and r.stdout.strip() else None


def ok(r):
    return r["class"] == "correct_all"


def conf_scores(r):
    c, lp = r.get("ctop") or [], r.get("lp") or []
    if not c:
        return {"conf_mean": -1e9, "conf_low": -1e9, "conf_tail": -1e9, "logprob": -1e9}
    w = 64
    groups = [sum(c[i:i + w]) / len(c[i:i + w]) for i in range(0, max(1, len(c) - w + 1), 8)] or [sum(c) / len(c)]
    tail = c[-256:]
    return {"conf_mean": sum(c) / len(c), "conf_low": min(groups), "conf_tail": sum(tail) / len(tail),
            "logprob": sum(lp) / len(lp) if lp else -1e9}


def mbr_pick(outs):   # outs[i] = list of outputs of candidate i on the shared inputs; most agreement with the others wins
    k = len(outs)
    score = [sum(1 for j in range(k) if j != i for a, b in zip(outs[i], outs[j]) if a is not None and a == b) for i in range(k)]
    return max(range(k), key=lambda i: (score[i], -i))


def analyze(cond, tests):
    S = [load(f"geocross_S2_B1_geox{M}_{cond}_t07s{s}") for s in SEEDS]
    keys = sorted(k for k in S[0] if all(k in s for s in S))

    def one(key):
        task, n, inst = key
        C = [s[key] for s in S]; codes = [c.get("code") for c in C]
        rng = random.Random(f"{task}-{n}-{inst}")
        V = variants(task, base_instance(task, n, rng), rng)
        given = render(task, V["identity"])[1]
        o_given = [out_of(c, given) for c in codes]
        # MR-select
        cons = []
        for i, c in enumerate(codes):
            if o_given[i] is None:
                continue
            if all(out_of(c, render(task, V[v])[1]) == expected_rel(task, v, o_given[i]) for v in MR if not (task == "lattice" and v == "scale")):
                cons.append(i)
        T = tests.get(key, {}).get("tests", [])
        o_tests = [[out_of(c, t["input"]) for t in T] for c in codes]
        fresh = [render(task, base_instance(task, n, random.Random(f"fresh{j}-{task}-{n}-{inst}")))[1] for j in range(N_FRESH)]
        o_fresh = [[out_of(c, f) for f in fresh] for c in codes]
        pick = {}
        pick["single"] = None
        if cons:
            vote = Counter(o_given[i] for i in cons).most_common(1)[0][0]
            pick["MR-select"] = next(i for i in cons if o_given[i] == vote)
        else:
            pick["MR-select"] = -1
        valid = [i for i in range(3) if o_given[i] is not None]
        pick["vote (given input)"] = (next(i for i in valid if o_given[i] == Counter(o_given[j] for j in valid).most_common(1)[0][0])
                                      if valid else 0)
        pick["MBR-exec (model inputs)"] = mbr_pick([[o_given[i]] + o_tests[i] for i in range(3)])
        pick["MBR-exec (fresh generator inputs)"] = mbr_pick([[o_given[i]] + o_fresh[i] for i in range(3)])
        if T:   # CodeT dual agreement: clusters of identical behaviour on the test inputs, score = size x tests passed
            clusters = {}
            for i in range(3):
                clusters.setdefault(tuple(o_tests[i]), []).append(i)
            def cscore(sig):
                return len(clusters[sig]) * sum(1 for a, t in zip(sig, T) if a is not None and a == t["output"])
            best = max(clusters, key=lambda sg: (cscore(sg), len(clusters[sg]), -min(clusters[sg])))
            pick["CodeT"] = clusters[best][0]
        else:
            pick["CodeT"] = pick["vote (given input)"]
        cs = [conf_scores(c) for c in C]
        for f in ("conf_mean", "conf_low", "conf_tail", "logprob"):
            pick[f"confidence: {f}"] = max(range(3), key=lambda i: (cs[i][f], -i))
        if len(cons) > 1:
            sc = [sum(1 for j in range(3) if j != i for a, b in zip([o_given[i]] + o_tests[i], [o_given[j]] + o_tests[j]) if a is not None and a == b) for i in cons]
            pick["hybrid MR + MBR"] = cons[max(range(len(cons)), key=lambda x: (sc[x], -x))]
        elif cons:
            pick["hybrid MR + MBR"] = cons[0]
        else:
            pick["hybrid MR + MBR"] = pick["MBR-exec (model inputs)"]
        res = {name: (sum(map(ok, C)) / 3 if i is None else (False if i < 0 else ok(C[i]))) for name, i in pick.items()}
        res["oracle-any"] = any(map(ok, C))
        return task, res, len(T), tests.get(key, {}).get("out_tokens", 0), sum(1 for t in T if t["output"])

    with ThreadPoolExecutor(24) as ex:
        R = list(ex.map(one, keys))
    return R


def ci(d, B=10000):
    rng = random.Random(0); n = len(d); bs = sorted(sum(d[rng.randrange(n)] for _ in range(n)) / n for _ in range(B))
    return 100 * sum(d) / n, 100 * bs[int(.025 * B)], 100 * bs[int(.975 * B)]


if __name__ == "__main__":
    tests = {**load("tests_S2_B1_core"), **load("tests_S2_B1_hard")}
    for cond in ("dis0", "dis8", "hard"):
        R = analyze(cond, tests)
        if not R:
            print(f"{cond}: no data"); continue
        n = len(R); names = list(R[0][1])
        print(f"\n=== {M} {cond}: {n} instances | model-written tests per instance {sum(r[2] for r in R) / n:.1f} "
              f"(test-writing tokens {sum(r[3] for r in R) / n:.0f})")
        for name in names:
            acc = 100 * sum(r[1][name] for r in R) / n
            line = f"  {name:36s} {acc:5.1f}%"
            if name not in ("MR-select", "oracle-any", "single"):
                m, lo, hi = ci([float(r[1][name]) - float(r[1]["MR-select"]) for r in R]); line += f"   vs MR-select {m:+5.1f} [{lo:+5.1f}, {hi:+5.1f}]"
            if name not in ("single", "oracle-any"):
                m, lo, hi = ci([float(r[1][name]) - float(r[1]["single"]) for r in R]); line += f"   vs single {m:+5.1f} [{lo:+5.1f}, {hi:+5.1f}]"
            print(line)
        for t in sorted({r[0] for r in R}):
            Rt = [r for r in R if r[0] == t]
            print(f"    {t:9s} " + " | ".join(f"{nm.split(' (')[0].replace('confidence: ', 'c:')[:12]} {100 * sum(r[1][nm] for r in Rt) / len(Rt):4.0f}" for nm in names))
    # offline DART-style router on the E3 data (C1 seeds 1-2 as drafts, E3 budget-thinking run as escalation)
    print("\n=== DART-style router (E3 data): two drafts agree on the given input -> draft 1, else think 1,024")
    for cond in ("dis0", "dis8", "hard"):
        D1, D2, E = load(f"geocross_S2_C1_geox{M}_{cond}_t07s1"), load(f"geocross_S2_C1_geox{M}_{cond}_t07s2"), load(f"geocross_S2_E3_geox{M}_{cond}_b1024_t07s1")
        keys = sorted(k for k in D1 if k in D2 and k in E)

        def dart(k):
            task, n, inst = k
            rng = random.Random(f"{task}-{n}-{inst}"); V = variants(task, base_instance(task, n, rng), rng)
            g = render(task, V["identity"])[1]
            a, b = out_of(D1[k].get("code"), g), out_of(D2[k].get("code"), g)
            agree = a is not None and a == b
            return (ok(D1[k]) if agree else ok(E[k]), D1[k]["out_tokens"] + D2[k]["out_tokens"] + (0 if agree else E[k]["out_tokens"]),
                    ok(E[k]), E[k]["out_tokens"], agree)
        with ThreadPoolExecutor(24) as ex:
            X = list(ex.map(dart, keys))
        n = len(X)
        m, lo, hi = ci([float(x[0]) - float(x[2]) for x in X])
        print(f"  {cond}: router {100 * sum(x[0] for x in X) / n:.1f}% @ {sum(x[1] for x in X) / n:.0f} tok (escalated {sum(not x[4] for x in X)}/{n}) | "
              f"always think-1,024 {100 * sum(x[2] for x in X) / n:.1f}% @ {sum(x[3] for x in X) / n:.0f} | diff {m:+.1f} [{lo:+.1f}, {hi:+.1f}]")
