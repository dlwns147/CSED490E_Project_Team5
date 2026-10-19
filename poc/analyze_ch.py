"""CH (docs/prereg/PREREG_CH.md): approach hints (TAG = human Codeforces tags; PLAN = the model's own low-effort plan) on the 311 contest
geometry problems, gpt-oss-120b / gpt-oss-20b, seeds 1-3, paired with the existing medium (16k) and high (64k) runs.
(a) first attempt: medium + hint vs medium. TAG runs only exist for the 255 problems with tags; the other 56 have the plain prompt, so their
    medium row is used (same prompt, same seed).
(b) escalation: medium -> gate -> [medium + hint -> gate] -> high, vs N13b (medium -> gate -> high). Gate = the statement's examples, then
    the problem's approximate brute-force oracle (N5, the model's own low-effort oracle, seed 1); the oracle's tokens are charged once per
    problem-seed, only when a program that passes the examples has to be checked (as N13b). The last level is kept when everything fails.
Reports accuracy @ mean tokens per problem, paired exact sign tests (problem-seed pairs), rating bands, unflagged problems, token tails,
finish reasons and failure kinds.  usage: CC_SET=full python analyze_ch.py [oss120|oss20 ...]"""
import json, math, os, sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("CC_SET", "full")
from run_cc import PFILE, VFILE, RES, tok_eq, tests_of  # noqa: E402
from sandbox import run_python  # noqa: E402

P = {p["name"]: p for p in json.load(open(PFILE))}
V = json.load(open(VFILE))
NPUB = {n: sum(t["kind"] == "public" for t in p["tests"]) for n, p in P.items()}
CACHE = f"{RES}/ch_oracle_agree.jsonl"   # (tag, seed, name) -> agrees with the oracle cases; filled on demand


def rows(tag, s):
    f = f"{RES}/cc_full_{tag}_s{s}.jsonl"
    return {r["name"]: r for r in map(json.loads, open(f))} if os.path.exists(f) else None


passes = lambda r: bool(r["code"]) and r["passed"] >= NPUB[r["name"]]
tok = lambda r: r.get("total_tokens") or r.get("out_tokens") or 0


def sign_p(a, b):   # exact two-sided sign test on discordant pairs
    n = a + b
    if n == 0:
        return 1.0
    k = min(a, b)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def oracle(m):
    N5 = {r["name"]: r for r in map(json.loads, open(f"{RES}/n5_{m}_low_s1.jsonl"))}
    return {n: r["cases"] for n, r in N5.items() if r["oracle_ok"] and r.get("cases")}, {n: r.get("oracle_tokens") or 0 for n, r in N5.items()}


def agreement(jobs, ORC):
    have = {}
    if os.path.exists(CACHE):
        for l in open(CACHE):
            try:
                x = json.loads(l); have[(x["tag"], x["seed"], x["name"])] = x["agree"]
            except ValueError:
                pass
    todo = [j for j in jobs if (j[0], j[1], j[2]) not in have]

    def agrees(j):
        tag, s, n, code = j
        for inp, ref in ORC[n]:
            x = run_python(code, inp, timeout=10)
            if x.status != "ok" or not tok_eq(x.stdout, ref, 1e-2):
                return False
        return True
    with ThreadPoolExecutor(24) as ex, open(CACHE, "a") as f:
        for j, a in zip(todo, ex.map(agrees, todo)):
            have[(j[0], j[1], j[2])] = a
            f.write(json.dumps({"tag": j[0], "seed": j[1], "name": j[2], "agree": a}) + "\n"); f.flush()
    return have


def report(m):
    med, high = f"{m}_medium", f"{m}_high64k"
    arms = {"TAG": f"{m}_medium_tag", "PLAN": f"{m}_medium_plan"}
    ORC, OTOK = oracle(m)
    R = {(t, s): rows(t, s) for t in [med, high] + list(arms.values()) for s in (1, 2, 3)}
    have_arm = {a: all(R[(t, s)] for s in (1, 2, 3)) for a, t in arms.items()}
    for s in (1, 2, 3):   # TAG: problems without tags use the medium row (identical prompt)
        if R[(arms["TAG"], s)] is not None:
            R[(arms["TAG"], s)] = {n: R[(arms["TAG"], s)].get(n, R[(med, s)][n]) for n in V}
    jobs = [(t, s, n, R[(t, s)][n]["code"]) for (t, s), X in R.items() if X and t != high for n in X if n in ORC and passes(X[n])]
    AG = agreement(jobs, ORC)
    gate = lambda t, s, n: passes(R[(t, s)][n]) and AG.get((t, s, n), True)
    print(f"\n=== {m}: {len(V)} problems x 3 seeds; oracle cases for {len(ORC)} problems")
    pol = {}
    for s in (1, 2, 3):
        M, H = R[(med, s)], R[(high, s)]
        for n in V:
            mr, hr = M[n], H[n]; o = OTOK.get(n, 0)   # the oracle was generated for every problem (as analyze_n13): charged even if it failed
            add = lambda k, ok, t: pol.setdefault(k, []).append((n, s, bool(ok), t))
            add("medium", mr["passed_all"], tok(mr))
            add("always high", hr["passed_all"], tok(hr))
            g = gate(med, s, n); oc = o if passes(mr) else 0
            add("N13b medium -> high", mr["passed_all"] if g else hr["passed_all"], oc + tok(mr) + (0 if g else tok(hr)))
            for a, t in arms.items():
                if not have_arm[a]:
                    continue
                xr = R[(t, s)][n]
                add(f"(a) medium + {a}", xr["passed_all"], tok(xr))
                if g:
                    add(f"(b) N13b + {a} step", mr["passed_all"], oc + tok(mr))
                else:
                    g2 = gate(t, s, n); oc2 = oc if oc else (o if passes(xr) else 0)
                    add(f"(b) N13b + {a} step", xr["passed_all"] if g2 else hr["passed_all"], oc2 + tok(mr) + tok(xr) + (0 if g2 else tok(hr)))
    flag = {n for n in V if V[n]["flag_multi"]}
    for k, L in pol.items():
        acc = 100 * sum(x[2] for x in L) / len(L); t = sorted(x[3] for x in L)
        sub = lambda f: [x for x in L if f(x[0])]
        lo, hi, uf = sub(lambda n: P[n]["rating"] <= 1800), sub(lambda n: P[n]["rating"] > 1800), sub(lambda n: n not in flag)
        pct = lambda X: 100 * sum(x[2] for x in X) / max(1, len(X))
        line = (f"  {k:26s} {acc:5.1f}% @ {sum(t) / len(t) / 1000:5.1f}k (p90 {t[int(.9 * len(t))] / 1000:.1f}k) | <=1800 {pct(lo):.1f}%, >1800 {pct(hi):.1f}%, "
                f"unflagged {pct(uf):.1f}%")
        ref = "N13b medium -> high" if k.startswith("(b)") else "medium" if k.startswith("(a)") else None
        if ref:
            B = {(x[0], x[1]): x[2] for x in pol[ref]}
            gain = sum(x[2] and not B[(x[0], x[1])] for x in L); lost = sum(B[(x[0], x[1])] and not x[2] for x in L)
            per = [100 * (sum(x[2] for x in L if x[1] == s) - sum(B[(x[0], x[1])] for x in L if x[1] == s)) / len(V) for s in (1, 2, 3)]
            line += f" | vs {ref}: +{gain} / -{lost}, sign p = {sign_p(gain, lost):.3f}, per seed " + " / ".join(f"{d:+.1f}" for d in per)
        print(line)
    bf = [json.loads(l) for s in (1, 2, 3) if os.path.exists(f"{RES}/ch_basefail_{med}_s{s}.jsonl")
          for l in open(f"{RES}/ch_basefail_{med}_s{s}.jsonl")]   # poc/ch_basefail.py: the medium runs did not record failure kinds
    if bf:
        mt = sorted(tok(r) for s in (1, 2, 3) for r in R[(med, s)].values())
        print(f"  medium runs: tokens mean {sum(mt) / len(mt):.0f}, p90 {mt[int(.9 * len(mt))]}; finish "
              f"{dict(Counter(r['finish'] for s in (1, 2, 3) for r in R[(med, s)].values()))}; fail kinds {dict(Counter(x['fail'] for x in bf))}")
    for a, t in arms.items():   # token tails, finish reasons, failure kinds of the hint runs (only the problems actually run)
        if not have_arm[a]:
            continue
        X = [r for s in (1, 2, 3) for r in map(json.loads, open(f"{RES}/cc_full_{t}_s{s}.jsonl"))]
        tt = sorted(tok(r) for r in X)
        print(f"  {a} runs: n {len(X)}, tokens mean {sum(tt) / len(tt):.0f}, p90 {tt[int(.9 * len(tt))]}, max {tt[-1]}; finish {dict(Counter(r['finish'] for r in X))}; "
              f"fail kinds {dict(Counter(r.get('fail') or 'pass' for r in X))}"
              + (f"; plan tokens mean {sum(r.get('plan_tokens') or 0 for r in X) / len(X):.0f}, empty plans {sum(not r.get('plan') for r in X)}, "
                 f"plan finish {dict(Counter(r.get('plan_finish') for r in X))}" if a == "PLAN" else ""))


if __name__ == "__main__":
    for m in sys.argv[1:] or ["oss120", "oss20"]:
        report(m)
