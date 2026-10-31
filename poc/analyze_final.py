"""FINAL (docs/prereg/PREREG_FINAL.md; offline on stored rows): the SQL claim on an untouched benchmark, Spider's test split (2,147
questions; tags <model>sp). Per generator: N -> free check -> the pre-registered peer's quick query returns the same rows -> N, else the
default SB->T->T (the peer's tokens paid on every passing N); minus the default. F1 Qwen3-8B, F2 Qwen3-14B-AWQ, F3 Qwen3.5-9B,
F4 gpt-oss-20b (low-effort N, medium-effort default), F5 Qwen3-8B with CV-1's trained quick query (C1 adapter) as N and the base
model's default. One-sided paired bootstrap p-values over questions (seed means, 10,000 resamples) for cascade - default > 0 in
utility (100 x right - 0.5 x ktokens), Holm over F1-F5 at 0.05; per test the dominance / trade label, the break-even accounting and
the decisive-strata ratio (analyze_xg.report).
usage: python3.11 poc/analyze_final.py     (FINAL_SUFFIX=<s>: other tags, e.g. "" = BIRD dev, the dry run)"""
import contextlib, io, os, random, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
with contextlib.redirect_stdout(io.StringIO()):
    import analyze_cv as CV  # noqa: E402
    import analyze_sqlpa as Q  # noqa: E402
    import analyze_xg as XG  # noqa: E402

SUF = os.environ.get("FINAL_SUFFIX", "sp")
TESTS = [("F1", "Qwen3-8B", "q8b", "q8b", "q35"), ("F2", "Qwen3-14B-AWQ", "q14a", "q14a", "q35"), ("F3", "Qwen3.5-9B", "q35", "q35", "q8b"),
         ("F4", "gpt-oss-20b", "oss20", "oss20", "q35"), ("F5", "Qwen3-8B, trained quick query (C1)", "q8bcvc1", "q8b", "q35")]   # (N, default, peer)
ALPHA = 0.05


def items(n, d, p):
    n, d, p = n + SUF, d + SUF, p + SUF
    GN, GP = Q.grades(n), Q.grades(p)
    if not (GN and GP and Q.grades(d)) or not all(os.path.exists(f"{CV.RES}/{d}_{a}_s{s}.jsonl") for a in ("think", "sb") for s in (1, 2, 3)):
        return None
    KN, KP, out = Q.ntok(n), Q.ntok(p), []
    for (i, s), v in CV.base(d, need_r=False).items():
        x, o = GN[s].get(i, {}).get("N"), GP[s].get(i, {}).get("N")
        if x is None or o is None or i not in KN[s]:
            continue
        ps = x["chk"] == "pass"
        out.append(dict(id=i, s=s, ps=ps, ok=bool(x["ok"]), tok=KN[s][i], ptok=KP[s].get(i, 0),
                        agree=ps and o["chk"] == "pass" and o["h"] == x["h"], dok=bool(v["SB->T->T"][0]), dtok=v["SB->T->T"][1],
                        tt=v["T->T"], ntt=(x["ok"], KN[s][i]) if ps else (v["T->T"][0], KN[s][i] + v["T->T"][1])))
    return out


def pvalue(d, B=10000):
    """one-sided paired bootstrap p-value of mean > 0 over questions"""
    ids = sorted(d); n = len(ids); rng = random.Random(1)
    m = [sum(d[rng.choice(ids)] for _ in range(n)) / n for _ in range(B)]
    return (sum(x <= 0 for x in m) + 1) / (B + 1)


def main():
    res = []
    for k, name, n, d, p in TESTS:
        X = items(n, d, p)
        print(f"=== {k} {name}: N {n}{SUF}, default {d}{SUF}, peer {p}{SUF}")
        if X is None:
            print("  rows missing"); continue
        du, p3, p4 = XG.report("Spider" if SUF == "sp" else SUF or "BIRD dev", X)
        u = lambda f: (lambda x: float(XG.POL[f](x)[0]) - XG.H.LAM / 100 * XG.POL[f](x)[1] / 1000)
        pv = pvalue(XG.per_q(X, lambda x: u("cascade")(x) - u("D")(x)))
        print(f"    one-sided p = {pv:.4f}")
        res.append((k, pv, du, p4))
    m = len(res)
    print(f"\n*** Holm over {m} tests at {ALPHA}:")
    held, stop = {}, False
    for j, (k, pv, du, p4) in enumerate(sorted(res, key=lambda r: r[1])):
        thr = ALPHA / (m - j)
        held[k] = not stop and pv <= thr
        stop = stop or not held[k]
        print(f"    {k}: p {pv:.4f} vs {thr:.4f} -> {'holds' if held[k] else 'not shown'}; cascade - D {du[0]:+.2f} [{du[1]:+.2f}, {du[2]:+.2f}]; "
              f"sign follows the break-even: {'not scored' if p4 is None else p4}")
    print(f"*** FINAL: {sum(held.values())} of {len(TESTS)} hold after Holm ({', '.join(k for k in held if held[k]) or '-'})")


if __name__ == "__main__":
    main()
