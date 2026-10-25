"""HO-CC (docs/prereg/PREREG_HO.md, addendum): the check-at-every-step order on contest programming (311 Codeforces geometry problems,
hidden tests; CC_SET=full run_cc.py). A visible failure = no program, or the program fails one of the statement's sample (public) tests
(tests run in order, public first, stopping at the first failure). Policies, tokens of every step counted:
T (one think), T->T (on T's visible failure, the next seed's think), SB+T (2k-token think first), SB->T->T, FF+T (non-thinking first),
FF+SB+T. Paired 95% intervals over problems (seed means).
CC-P2: --agree runs every plain program that passes the samples and the same seed's short-think program on all test inputs (no expected
outputs) and compares their outputs (writes results/h2/hocc_agree_<m>.json; CPU-heavy: run on a CPU node).
Amendment (PREREG_HO.md, HO-CC): --think_tag think32k scores the order against the 32,000-token think (the 16k one mostly hits its cap).
usage: python analyze_hocc.py [--agree] [--think_tag TAG] [model ...]"""
import json, os, sys
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_ho3 import ci  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = f"{ROOT}/results/h2"
P = {p["name"]: p for p in json.load(open(f"{RES}/cc_geometry_full.json"))}
NPUB = {n: sum(t["kind"] == "public" for t in p["tests"]) for n, p in P.items()}
g = lambda r: r.get("out_tokens") or 0
TT = sys.argv[sys.argv.index("--think_tag") + 1] if "--think_tag" in sys.argv else "think"


def rows(tag, s):
    return {r["name"]: r for r in map(json.loads, open(f"{RES}/cc_full_{tag}_s{s}.jsonl"))}


def vis_pass(r):
    return bool(r.get("code")) and r["passed"] >= NPUB[r["name"]]


def policies(m):
    per, tok, n = {}, {}, 0
    for s in (1, 2, 3):
        C, S, T, T2 = rows(f"{m}_plain", s), rows(f"{m}_tb2000", s), rows(f"{m}_{TT}", s), rows(f"{m}_{TT}", s % 3 + 1)
        for i, t in T.items():
            if i not in C or i not in S or i not in T2:
                continue
            c, sb, t2 = C[i], S[i], T2[i]; n += 1
            tt = (t["passed_all"], g(t)) if vis_pass(t) else (t2["passed_all"], g(t) + g(t2))
            sbt = (sb["passed_all"], g(sb)) if vis_pass(sb) else (t["passed_all"], g(sb) + g(t))
            sbtt = (sb["passed_all"], g(sb)) if vis_pass(sb) else (tt[0], g(sb) + tt[1])
            fft = (c["passed_all"], g(c)) if vis_pass(c) else (t["passed_all"], g(c) + g(t))
            ffsbt = (c["passed_all"], g(c)) if vis_pass(c) else (sbt[0], g(c) + sbt[1])
            res = {"T": (t["passed_all"], g(t)), "T->T": tt, "SB+T": sbt, "SB->T->T": sbtt, "FF+T": fft, "FF+SB+T": ffsbt}
            per.setdefault(i, []).append({k: bool(v[0]) for k, v in res.items()})
            for k, v in res.items():
                tok[k] = tok.get(k, 0) + v[1]
    return per, tok, n


def leak(m, arm):
    w = p = 0
    for s in (1, 2, 3):
        for r in rows(f"{m}_{arm}", s).values():
            if vis_pass(r):
                p += 1; w += not r["passed_all"]
    return 100 * w / max(1, p), p


def outputs(args):
    from run_cc import tests_of
    from sandbox import run_python
    name, code = args
    return [((r.stdout if r.status == "ok" else None) or None) for r in (run_python(code, t["input"], timeout=10) for t in tests_of(P[name]))]


def agree(m):
    from run_cc import tok_eq
    tol = {k: v.get("tol") if isinstance(v, dict) else v for k, v in json.load(open(f"{RES}/cc_valid_full.json")).items()}
    jobs, keys = [], []
    for s in (1, 2, 3):
        C, S = rows(f"{m}_plain", s), rows(f"{m}_tb2000", s)
        for i, c in C.items():
            if vis_pass(c) and i in S:
                keys.append((s, i, bool(c["passed_all"]), vis_pass(S[i])))
                jobs += [(i, c["code"]), (i, S[i]["code"] or "")]
    with ProcessPoolExecutor(int(os.environ.get("NPROC", 16))) as ex:
        outs = list(ex.map(outputs, jobs, chunksize=4))
    res = []
    for k, (s, i, right, sbp) in enumerate(keys):
        a, b = outs[2 * k], outs[2 * k + 1]
        same = sbp and all(x is not None and y is not None and tok_eq(x, y, tol.get(i, 1e-6)) for x, y in zip(a, b))
        res.append({"seed": s, "name": i, "plain_right": right, "sb_passes_samples": sbp, "agree_all_inputs": bool(same)})
    json.dump(res, open(f"{RES}/hocc_agree_{m}.json", "w"))
    return res


def main():
    models = [a for a in sys.argv[1:] if not a.startswith("--") and a != TT] or ["q14a", "n3n"]
    if "--agree" in sys.argv:
        for m in models:
            R = agree(m)
            for k, lab in ((True, "agree on every input"), (False, "disagree or the short think fails the samples")):
                X = [r for r in R if r["agree_all_inputs"] == k]
                print(f"{m}: sample-passing plain programs that {lab}: {100 * sum(r['plain_right'] for r in X) / max(1, len(X)):.1f}% pass all hidden tests (n={len(X)})")
            X = [r for r in R if not r["agree_all_inputs"] and r["sb_passes_samples"]]
            print(f"{m}:   of which the short think passes the samples but disagrees: {100 * sum(r['plain_right'] for r in X) / max(1, len(X)):.1f}% (n={len(X)})")
        return
    for m in models:
        per, tok, n = policies(m)
        acc = {k: 100 * sum(x[k] for v in per.values() for x in v) / n for k in tok}
        print(f"=== {m} contest geometry ({len(per)} problems, {n} rows); leak (sample-passing but wrong): plain {leak(m, 'plain')[0]:.0f}%, "
              f"short think {leak(m, 'tb2000')[0]:.0f}%, think {leak(m, TT)[0]:.0f}%")
        print("  " + " | ".join(f"{k} {acc[k]:.1f}% @ {tok[k] / n / 1000:.2f}k ({100 * tok[k] / tok['T->T']:.0f}% of T->T)" for k in tok))
        for k in ("T", "SB+T", "SB->T->T", "FF+T", "FF+SB+T"):
            mu, lo, hi = ci({i: sum(x[k] - x["T->T"] for x in v) / len(v) for i, v in per.items()})
            print(f"  {k} - T->T {mu:+.1f} [{lo:+.1f}, {hi:+.1f}]")


if __name__ == "__main__":
    main()
