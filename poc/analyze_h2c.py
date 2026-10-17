"""H2c Part A (docs/prereg/PREREG_H2C.md): MBR-exec among the samples that pass the statement's examples, offline on the H2b samples.
Selection inputs = generated tests 30.. (inputs only; disjoint from the evaluation tests), at most 20 per problem.
Part B (CC_SET=full): the full set, conditions with 3 seeds, by rating band, with and without the flagged problems, bootstrap CIs.
usage: [CC_SET=full] python analyze_h2c.py"""
import json, os, random, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_cc import MAX_GEN, OPRE, PFILE, SET, VFILE, tok_eq  # noqa: E402
from sandbox import run_python  # noqa: E402

RES = "/NAS/SJ/POSTECH/nlp/results/h2"
NSEL = 20
P = {p["name"]: p for p in json.load(open(PFILE))}
VAL = json.load(open(VFILE))
TOL = {n: v["tol"] for n, v in VAL.items()}
NPUB = {n: sum(t["kind"] == "public" for t in p["tests"]) for n, p in P.items()}
SEL = {n: [t["input"] for t in p["tests"] if t["kind"] == "generated"][MAX_GEN:MAX_GEN + NSEL] for n, p in P.items()}
COND = ({"q32b_plain": 8, "oss20_low": 8, "oss120_low": 8, "q32b_think1024": 3, "oss20_medium": 3, "oss120_medium": 3} if SET == "local" else
        {c: 3 for c in ("q32b_plain", "q32b_think1024", "q32b_think", "oss20_low", "oss20_medium", "oss120_low", "oss120_medium")})

_cache = {}


def outs(code, name):   # outputs on the selection inputs; a failure is a unique object, so it never agrees
    key = (hash(code), name)
    if key not in _cache:
        res = []
        for inp in SEL[name]:
            r = run_python(code, inp, timeout=5)
            res.append(r.stdout if r.status == "ok" else object())
        _cache[key] = res
    return _cache[key]


def agree(a, b, tol):
    return sum(isinstance(x, str) and isinstance(y, str) and tok_eq(x, y, tol) for x, y in zip(a, b))


def pick(name, rs):
    cand = [r for r in rs if r["code"] and r["passed"] >= NPUB[name]] or [r for r in rs if r["code"]]
    if not cand:
        return rs[0], rs[0]
    first = cand[0]
    if len(cand) == 1 or not SEL[name]:
        return first, first
    O = [outs(r["code"], name) for r in cand]
    sc = [sum(agree(O[i], O[j], TOL[name]) for j in range(len(cand)) if j != i) for i in range(len(cand))]
    return first, cand[max(range(len(cand)), key=lambda i: (sc[i], -i))]


def one(args):
    tag, k, name, rs = args
    f, m = pick(name, rs)
    return tag, name, f["passed_all"], m["passed_all"], any(r["passed_all"] for r in rs), sum(r.get("out_tokens") or 0 for r in rs)


def band(r):
    return "<=1600" if r <= 1600 else ("1700-2200" if r <= 2200 else ">=2300")


def ci(v, B=5000):
    rng = random.Random(0); n = len(v)
    bs = sorted(sum(v[rng.randrange(n)] for _ in range(n)) / n for _ in range(B))
    return 100 * bs[int(.025 * B)], 100 * bs[int(.975 * B)]


def part_b():
    jobs = []
    for tag in COND:
        fs = [f"{RES}/{OPRE}{tag}_s{sd}.jsonl" for sd in (1, 2, 3)]
        if not all(os.path.exists(f) for f in fs):
            print(f"{tag}: missing seeds", [sd for sd, f in zip((1, 2, 3), fs) if not os.path.exists(f)])
            fs = [f for f in fs if os.path.exists(f)]
            if not fs:
                continue
        S = [{r["name"]: r for r in map(json.loads, open(f))} for f in fs]
        jobs += [(tag, len(S), n, [s[n] for s in S]) for n in sorted(S[0])]
    with ThreadPoolExecutor(32) as ex:
        res = list(ex.map(one, jobs))
    single = {(j[0], j[2]): sum(r["passed_all"] for r in j[3]) / len(j[3]) for j in jobs}
    tok1 = {(j[0], j[2]): sum(r.get("out_tokens") or 0 for r in j[3]) / len(j[3]) for j in jobs}
    def body_img(n):   # an <image> placeholder before the Input section: a figure or a formula the text lost
        d = P[n]["description"]; i = d.find("\nInput")
        return "<image>" in (d[:i] if i > 0 else d)
    keepf = {"all": lambda n: True, "unflagged": lambda n: not VAL[n]["flag_multi"],
             "unflagged, no image in the statement body": lambda n: not VAL[n]["flag_multi"] and not body_img(n)}
    for subset, f in keepf.items():
        print(f"\n=== {subset} problems")
        for tag in COND:
            X = [r for r in res if r[0] == tag and f(r[1])]
            if not X:
                continue
            n = len(X); k = next(j[1] for j in jobs if j[0] == tag)
            s1 = [single[(tag, r[1])] for r in X]; fp = [r[2] for r in X]; mb = [r[3] for r in X]
            lo, hi = ci(s1); lo3, hi3 = ci(mb)
            print(f"{tag:15s} n={n} k={k}: single {100 * sum(s1) / n:5.1f}% [{lo:4.1f},{hi:4.1f}] @ {sum(tok1[(tag, r[1])] for r in X) / n:6.0f} tok | "
                  f"first-passing {100 * sum(fp) / n:5.1f}% | MBR-exec {100 * sum(mb) / n:5.1f}% [{lo3:4.1f},{hi3:4.1f}] | oracle {100 * sum(r[4] for r in X) / n:5.1f}% "
                  f"@ {sum(r[5] for r in X) / n:6.0f} tok")
            if subset == "all":
                print("   by band (single / MBR-exec):", {b: (round(100 * sum(single[(tag, r[1])] for r in X if band(P[r[1]]['rating']) == b) / max(1, sum(band(P[r[1]]['rating']) == b for r in X)), 1),
                                                        round(100 * sum(r[3] for r in X if band(P[r[1]]['rating']) == b) / max(1, sum(band(P[r[1]]['rating']) == b for r in X)), 1))
                                                    for b in ("<=1600", "1700-2200", ">=2300")})


if __name__ == "__main__" and SET != "local":
    part_b()
elif __name__ == "__main__":
    jobs = []
    for tag, k in COND.items():
        S = {sd: {r["name"]: r for r in map(json.loads, open(f"{RES}/cc_{tag}_s{sd}.jsonl"))} for sd in range(1, k + 1)}
        jobs += [(tag, k, n, [S[sd][n] for sd in range(1, k + 1)]) for n in sorted(S[1])]
    with ThreadPoolExecutor(24) as ex:
        res = list(ex.map(one, jobs))
    for tag, k in COND.items():
        X = [r for r in res if r[0] == tag]; n = len(X)
        print(f"{tag:15s} k={k}: first-passing {100 * sum(r[2] for r in X) / n:5.1f}% | MBR-exec {100 * sum(r[3] for r in X) / n:5.1f}% | "
              f"oracle {100 * sum(r[4] for r in X) / n:5.1f}% | tokens/problem {sum(r[5] for r in X) / n:6.0f} | "
              f"MBR wins on {[r[1][:12] for r in X if r[3] and not r[2]]} loses on {[r[1][:12] for r in X if r[2] and not r[3]]}")
    k8 = [r for r in res if COND[r[0]] == 8]
    print(f"pooled k=8 (n={len(k8)}): first-passing {sum(r[2] for r in k8)} | MBR-exec {sum(r[3] for r in k8)} | oracle {sum(r[4] for r in k8)}")
