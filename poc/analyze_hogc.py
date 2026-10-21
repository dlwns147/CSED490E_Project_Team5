"""HO-G-C (docs/prereg/PREREG_HOGC.md): does a brute-force view close the check leak on the held-out geometry tasks?
Rows: fact F and THINK from HO-G (geocross_S2_HOG_<m>_geo_{fact,think}_s<seed>), brute-force B from the Slurm run
(geocross_SL_HOGC_<m>_geo_brute_s<seed>). MR = analyze_n10.geo_check (runs + consistent metamorphic outputs, no answers).
Agreement (no answers): equal outputs (as fractions where both parse) on the given instance and its translate / rot90 / mirror /
permute / scale copies; a crash, timeout or empty output = disagreement. Policies per seed: FF, STRICT, TWO-VIEW, RESAMPLE, THINK.
Correct = right on all 8 variants (labels used for scoring and for the leak / false-alarm notes only). utility = accuracy - 0.5 x ktokens.
usage: python analyze_hogc.py [model ...]"""
import hashlib, json, os, random, sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_n10 as N  # noqa: E402
from run_geo import base_instance, variants  # noqa: E402
from run_geo_mr import run_out  # noqa: E402

RES = N.RES
SIX = ["identity", "translate", "rot90", "mirror", "permute", "scale"]


def load(tag):
    f = f"{RES}/geocross_{tag}.jsonl"
    return {(r["task"], r["n"], r["inst"]): r for r in map(json.loads, open(f))} if os.path.exists(f) else None


def outs(r):
    """outputs of one program on the six agreement inputs (cached next to the MR check results)"""
    if not r.get("code"):
        return None
    k = "six|" + hashlib.md5(f"{r['task']}-{r['n']}-{r['inst']}|{r['code']}".encode()).hexdigest()
    if k not in N.CACHE:
        rng = random.Random(f"{r['task']}-{r['n']}-{r['inst']}")
        V = variants(r["task"], base_instance(r["task"], r["n"], rng), rng)
        N.CACHE[k] = [run_out(r["code"], r["task"], V[v]) for v in SIX]
    return N.CACHE[k]


def same(a, b):
    try:
        return Fraction(a) == Fraction(b)
    except (ValueError, ZeroDivisionError):
        return a == b


def agree(a, b):
    oa, ob = outs(a), outs(b)
    return bool(oa and ob and None not in oa and None not in ob and all(same(x, y) for x, y in zip(oa, ob)))


ok = lambda r: r["class"] == "correct_all"
tok = lambda r: (r.get("out_tokens") or 0) + (r.get("think_tokens") or 0)   # as analyze_hog (think_tokens is set only by budget forcing)


def main():
    for m in sys.argv[1:] or ["oss20", "q14a", "q8b"]:
        F = {s: load(f"S2_HOG_{m}_geo_fact_s{s}") for s in (1, 2, 3)}
        T = {s: load(f"S2_HOG_{m}_geo_think_s{s}") for s in (1, 2, 3)}
        B = {s: load(f"SL_HOGC_{m}_geo_brute_s{s}") for s in (1, 2, 3)}
        if any(v is None for v in [*F.values(), *T.values(), *B.values()]):
            print(m, "incomplete (missing seeds):", {n: [s for s in (1, 2, 3) if X[s] is None] for n, X in (("fact", F), ("think", T), ("brute", B))})
            continue
        rows = [r for X in (F, B) for s in X for r in X[s].values()]
        with ThreadPoolExecutor(int(os.environ.get("HOGC_THREADS", 8))) as ex:
            list(ex.map(N.geo_check, rows)); list(ex.map(outs, rows))
        json.dump(N.CACHE, open(N.CACHE_F, "w"))
        print(f"=== {m}")
        per, leak, fa, bstat = {}, Counter(), Counter(), Counter()
        for s in (1, 2, 3):
            s2 = s % 3 + 1
            keys = [k for k in F[s] if k in T[s] and k in B[s] and k in F[s2]]; n = len(keys)
            P = {p: [0, 0] for p in ("FF", "STRICT", "TWO-VIEW", "RESAMPLE", "THINK")}
            for k in keys:
                f, t, b, f2 = F[s][k], T[s][k], B[s][k], F[s2][k]
                fm, bm, ag = N.geo_check(f)[0], N.geo_check(b)[0], agree(f, b)
                tf, tb, tt = tok(f), tok(b), tok(t)
                P["THINK"][0] += ok(t); P["THINK"][1] += tt
                P["FF"][0] += ok(f) if fm else ok(t); P["FF"][1] += tf + (0 if fm else tt)
                acc_s = fm and ag
                P["STRICT"][0] += ok(f) if acc_s else ok(t); P["STRICT"][1] += tf + tb + (0 if acc_s else tt)
                pick = (f if ag else None) if (fm and bm) else (f if fm else (b if bm else None))
                P["TWO-VIEW"][0] += ok(pick) if pick else ok(t); P["TWO-VIEW"][1] += tf + tb + (0 if pick else tt)
                acc_r = fm and agree(f, f2)
                P["RESAMPLE"][0] += ok(f) if acc_r else ok(t); P["RESAMPLE"][1] += tf + tok(f2) + (0 if acc_r else tt)
                task = k[0]
                if fm and not ok(f):   # leaked: passes MR, wrong
                    leak[(task, "n")] += 1; leak[(task, "strict")] += not ag; leak[(task, "resample")] += not agree(f, f2)
                if fm and ok(f):       # correct MR-passers: false alarms
                    fa[(task, "n")] += 1; fa[(task, "strict")] += not ag; fa[(task, "resample")] += not agree(f, f2)
                bstat[(task, "n")] += 1; bstat[(task, "ok")] += ok(b); bstat[(task, "mr")] += bm; bstat[(task, "crash")] += b["class"] == "crash"
                bstat[(task, "tok")] += tb; bstat[(task, "len")] += b["finish"] == "length"
                if not fm and bm:
                    bstat[(task, "f_fail_b_pass")] += 1; bstat[(task, "f_fail_b_pass_ok")] += ok(b); bstat[(task, "f_fail_b_pass_think_ok")] += ok(t)
            for p, (a, t_) in P.items():
                per.setdefault(p, []).append((100 * a / n, t_ / n / 1000))
        th_acc = sum(x for x, _ in per["THINK"]) / 3; th_tok = sum(y for _, y in per["THINK"]) / 3
        for p, L in per.items():
            acc = sum(x for x, _ in L) / 3; tk = sum(y for _, y in L) / 3
            seeds_ok = sum(x >= tx - 1 and y <= 0.6 * ty for (x, y), (tx, ty) in zip(L, per["THINK"]))
            print(f"  {p:9s} {acc:5.1f}% @ {tk:.2f}k  ({100 * tk / th_tok:3.0f}% of THINK tokens; seeds " + " / ".join(f"{x:.1f}" for x, _ in L)
                  + f") utility {acc - 0.5 * tk:.1f}  HOG-P1 {'holds' if acc >= th_acc - 1 and tk <= 0.6 * th_tok else 'fails'} (seeds {seeds_ok}/3)")
        tasks = sorted({t for t, _ in bstat})
        print("  leaked fact programs (pass MR, wrong) flagged by STRICT / RESAMPLE: " + ", ".join(
            f"{t} {leak[(t, 'strict')]}/{leak[(t, 'n')]} / {leak[(t, 'resample')]}" for t in tasks)
              + f"; all {sum(leak[(t, 'strict')] for t in tasks)}/{sum(leak[(t, 'n')] for t in tasks)} / {sum(leak[(t, 'resample')] for t in tasks)}")
        print("  false alarms on correct MR-passing fact programs, STRICT / RESAMPLE: " + ", ".join(
            f"{t} {fa[(t, 'strict')]}/{fa[(t, 'n')]} / {fa[(t, 'resample')]}" for t in tasks))
        print("  brute force by task (correct / passes MR / crash / at cap / mean tokens): " + ", ".join(
            f"{t} {bstat[(t, 'ok')]}/{bstat[(t, 'mr')]}/{bstat[(t, 'crash')]}/{bstat[(t, 'len')]} of {bstat[(t, 'n')]} @ {bstat[(t, 'tok')] / bstat[(t, 'n')]:.0f}" for t in tasks))
        print("  F fails MR, B passes (TWO-VIEW takes B): " + ", ".join(
            f"{t} {bstat[(t, 'f_fail_b_pass')]} (B right {bstat[(t, 'f_fail_b_pass_ok')]}, THINK right {bstat[(t, 'f_fail_b_pass_think_ok')]})" for t in tasks))


if __name__ == "__main__":
    main()
