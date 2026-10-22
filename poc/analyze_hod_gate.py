"""HO-D gate (docs/prereg/PREREG_HOGC.md, addendum): best case of a differential test on edge inputs for a model's held-out geometry fact
programs. DIFF-F2 / DIFF-B / DIFF-ALL accept the fact program F only if it passes MR and agrees with a second sample F2 (next seed) / the
brute-force program B / both on all eight inputs (the six agreement inputs plus the benchmark's `big` and `degen` copies, used as inputs
only, standing in for a perfect edge-input generator); else THINK. Tokens: F + the second program(s) + thinking where escalated.
usage: python analyze_hod_gate.py [model ...]"""
import hashlib, json, os, random, sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_n10 as N  # noqa: E402
from analyze_hogc import load, ok, same, tok  # noqa: E402
from run_geo import base_instance, variants  # noqa: E402
from run_geo_mr import run_out  # noqa: E402

EIGHT = ["identity", "translate", "rot90", "mirror", "permute", "scale", "big", "degen"]


def outs8(r):
    if not r.get("code"):
        return None
    k = "eight|" + hashlib.md5(f"{r['task']}-{r['n']}-{r['inst']}|{r['code']}".encode()).hexdigest()
    if k not in N.CACHE:
        rng = random.Random(f"{r['task']}-{r['n']}-{r['inst']}")
        V = variants(r["task"], base_instance(r["task"], r["n"], rng), rng)
        N.CACHE[k] = [run_out(r["code"], r["task"], V[v]) for v in EIGHT]
    return N.CACHE[k]


def agree8(a, b):
    oa, ob = outs8(a), outs8(b)
    return bool(oa and ob and None not in oa and None not in ob and all(same(x, y) for x, y in zip(oa, ob)))


def main():
    for m in sys.argv[1:] or ["q8b"]:
        F = {s: load(f"S2_HOG_{m}_geo_fact_s{s}") for s in (1, 2, 3)}
        T = {s: load(f"S2_HOG_{m}_geo_think_s{s}") for s in (1, 2, 3)}
        B = {s: load(f"SL_HOGC_{m}_geo_brute_s{s}") for s in (1, 2, 3)}
        with ThreadPoolExecutor(int(os.environ.get("HOGC_THREADS", 8))) as ex:
            list(ex.map(outs8, [r for X in (F, B) for s in X for r in X[s].values()]))
        json.dump(N.CACHE, open(N.CACHE_F, "w"))
        P, st, n = Counter(), Counter(), 0
        for s in (1, 2, 3):
            s2 = s % 3 + 1
            for k in F[s]:
                if k not in T[s] or k not in B[s] or k not in F[s2]:
                    continue
                f, t, b, f2 = F[s][k], T[s][k], B[s][k], F[s2][k]; n += 1
                fm = N.geo_check(f)[0]; a2, ab = agree8(f, f2), agree8(f, b)
                for name, acc, extra in (("FF", fm, 0), ("DIFF-F2", fm and a2, tok(f2)), ("DIFF-B", fm and ab, tok(b)),
                                         ("DIFF-ALL", fm and a2 and ab, tok(f2) + tok(b)), ("THINK", False, -tok(f))):
                    P[(name, "acc")] += ok(f) if acc else ok(t); P[(name, "tok")] += tok(f) + extra + (0 if acc else tok(t))
                if fm:
                    kind = "right" if ok(f) else ("edge" if f["per_variant"].get("identity") else "input")
                    st[(kind, "n")] += 1
                    for name, a in (("F2", a2), ("B", ab), ("ALL", a2 and ab)):
                        st[(kind, name)] += not a
        th = P[("THINK", "tok")]
        print(f"=== {m} ({n} rows): " + " | ".join(f"{p} {100 * P[(p, 'acc')] / n:.1f}% @ {P[(p, 'tok')] / n / 1000:.2f}k ({100 * P[(p, 'tok')] / th:.0f}%)"
                                               for p in ("FF", "DIFF-F2", "DIFF-B", "DIFF-ALL", "THINK")))
        for kind in ("input", "edge", "right"):
            print(f"  flagged {kind:5s} (n={st[(kind, 'n')]}): " + ", ".join(f"{x} {st[(kind, x)]}" for x in ("F2", "B", "ALL")))


if __name__ == "__main__":
    main()
