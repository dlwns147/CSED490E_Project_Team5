"""HO-G-C (docs/prereg/PREREG_HOGC.md): does a brute-force view close the check leak on the held-out geometry tasks?
Rows: fact F and THINK from HO-G (geocross_S2_HOG_<m>_geo_{fact,think}_s<seed>), brute-force B from the Slurm run
(geocross_SL_HOGC_<m>_geo_brute_s<seed>). MR = analyze_n10.geo_check (runs + consistent metamorphic outputs, no answers).
Agreement (no answers): equal outputs (as fractions where both parse) on the given instance and its translate / rot90 / mirror /
permute / scale copies; a crash, timeout or empty output = disagreement. Policies per seed: FF, STRICT, TWO-VIEW, RESAMPLE, THINK.
Correct = right on all 8 variants (labels used for scoring and for the leak / false-alarm notes only). utility = accuracy - 0.5 x ktokens.
--edge (addendum HO-G-E): also policy EDGE = accept the fact program only if it passes MR and the model's own edge-case tests for the task
(results/edgetests_SL_HOGCE_<m>_s<seed>.jsonl, written once per task; their tokens are spread over the task's items).
--mr (addendum HO-G-M): also policy MR+ = accept the fact program only if it passes MR and the model's own metamorphic relations for the task
(results/edgemr_SL_HOGCM_<m>_s<seed>.jsonl: transform(stdin) and expect(old answer), written once per task; a transform that crashes or
returns nothing is skipped for that input; the program crashing on a transformed input counts as a violation).
usage: python analyze_hogc.py [--edge] [--mr] [model ...]"""
import hashlib, json, os, random, sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze_n10 as N  # noqa: E402
from run_geo import base_instance, render, variants  # noqa: E402
from run_geo_mr import run_out  # noqa: E402
from sandbox import run_python  # noqa: E402

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


def edge_pass(r, tests):
    """True if the program prints the expected output on every edge-case test of its task (cached)"""
    if not r.get("code"):
        return False
    k = "edge|" + hashlib.md5(f"{r['task']}-{r['n']}-{r['inst']}|{r['code']}|{json.dumps(tests)}".encode()).hexdigest()
    if k not in N.CACHE:
        res = []
        for t in tests:
            x = run_python(r["code"], t["stdin"] if t["stdin"].endswith("\n") else t["stdin"] + "\n", timeout=10)
            out = (x.stdout.strip().split() or [""])[-1].lower() if x.status == "ok" else None
            res.append(out is not None and same(out, t["expected"].strip().split()[-1].lower() if t["expected"].strip() else ""))
        N.CACHE[k] = res
    return all(N.CACHE[k])


MR_T = "\n\nimport sys as _s, json as _j\n_x = _s.stdin.read()\n_o = []\nfor _t, _e in RELATIONS:\n    try:\n        _o.append(_t(_x))\n    except Exception:\n        _o.append(None)\nprint(_j.dumps(_o))\n"
MR_E = "\n\nimport sys as _s, json as _j\n_a = _s.stdin.read().strip()\n_o = []\nfor _t, _e in RELATIONS:\n    try:\n        _o.append(str(_e(_a)))\n    except Exception:\n        _o.append(None)\nprint(_j.dumps(_o))\n"


def _json_list(code, stdin, key):
    if key not in N.CACHE:
        x = run_python(code, stdin, timeout=10)
        try:
            v = json.loads(x.stdout.strip().splitlines()[-1]) if x.status == "ok" and x.stdout.strip() else []
        except ValueError:
            v = []
        N.CACHE[key] = v if isinstance(v, list) else []
    return N.CACHE[key]


def mr_pass(r, code):
    """True if the program keeps every model-written relation on its given instance (no relations that run = no extra check)"""
    if not r.get("code") or not code:
        return bool(r.get("code"))
    k = "mrP|" + hashlib.md5(f"{r['task']}-{r['n']}-{r['inst']}|{r['code']}|{code}".encode()).hexdigest()
    if k not in N.CACHE:
        rng = random.Random(f"{r['task']}-{r['n']}-{r['inst']}")
        x = render(r["task"], variants(r["task"], base_instance(r["task"], r["n"], rng), rng)["identity"])[1]
        base = (outs(r) or [None])[0]
        ys = _json_list(code + MR_T, x, "mrT|" + hashlib.md5((code + "|" + x).encode()).hexdigest())
        es = _json_list(code + MR_E, base or "", "mrE|" + hashlib.md5((code + "|" + str(base)).encode()).hexdigest())
        ok = True
        for y, e in zip(ys, es):
            if not (isinstance(y, str) and y.strip() and isinstance(e, str) and e.strip()):
                continue
            z = run_python(r["code"], y if y.endswith("\n") else y + "\n", timeout=10)
            out = (z.stdout.strip().split() or [None])[-1] if z.status == "ok" else None
            if out is None or not same(out.lower(), e.strip().split()[-1].lower()):
                ok = False; break
        N.CACHE[k] = ok
    return N.CACHE[k]


def load_mr(m, s):
    f = f"{RES}/edgemr_SL_HOGCM_{m}_s{s}.jsonl"
    return {r["task"]: r for r in map(json.loads, open(f))} if os.path.exists(f) else None


def load_edge(m, s):
    f = f"{RES}/edgetests_SL_HOGCE_{m}_s{s}.jsonl"
    return {r["task"]: r for r in map(json.loads, open(f))} if os.path.exists(f) else None


ok = lambda r: r["class"] == "correct_all"
tok = lambda r: (r.get("out_tokens") or 0) + (r.get("think_tokens") or 0)   # as analyze_hog (think_tokens is set only by budget forcing)


def main():
    EDGE, MRX = "--edge" in sys.argv, "--mr" in sys.argv
    for m in [x for x in sys.argv[1:] if not x.startswith("--")] or ["oss20", "q14a", "q8b"]:
        F = {s: load(f"S2_HOG_{m}_geo_fact_s{s}") for s in (1, 2, 3)}
        T = {s: load(f"S2_HOG_{m}_geo_think_s{s}") for s in (1, 2, 3)}
        B = {s: load(f"SL_HOGC_{m}_geo_brute_s{s}") for s in (1, 2, 3)}
        E = {s: load_edge(m, s) for s in (1, 2, 3)} if EDGE else {}
        M = {s: load_mr(m, s) for s in (1, 2, 3)} if MRX else {}
        if any(v is None for v in [*F.values(), *T.values(), *B.values(), *E.values(), *M.values()]):
            print(m, "incomplete (missing seeds):", {n: [s for s in (1, 2, 3) if X[s] is None] for n, X in (("fact", F), ("think", T), ("brute", B))})
            continue
        rows = [r for X in (F, B) for s in X for r in X[s].values()]
        with ThreadPoolExecutor(int(os.environ.get("HOGC_THREADS", 8))) as ex:
            list(ex.map(N.geo_check, rows)); list(ex.map(outs, rows))
            if MRX:
                list(ex.map(lambda r: mr_pass(r[0], r[1]), [(r, M[s][r["task"]]["code"]) for X in (F, T) for s in X for r in X[s].values()]))
            if EDGE:   # fact programs and (for the test-validity note) thinking programs against their task's tests
                list(ex.map(lambda r: edge_pass(r[0], r[1]), [(r, E[s][r["task"]]["tests"]) for X in (F, T) for s in X for r in X[s].values()]))
        json.dump(N.CACHE, open(N.CACHE_F, "w"))
        print(f"=== {m}")
        per, leak, fa, bstat, est, mst = {}, Counter(), Counter(), Counter(), Counter(), Counter()
        for s in (1, 2, 3):
            s2 = s % 3 + 1
            keys = [k for k in F[s] if k in T[s] and k in B[s] and k in F[s2]]; n = len(keys)
            P = {p: [0, 0] for p in ("FF", "STRICT", "TWO-VIEW", "RESAMPLE", "THINK") + (("EDGE",) if EDGE else ()) + (("MR+",) if MRX else ())}
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
                if MRX:
                    mt = M[s][task]; mp = mr_pass(f, mt["code"])
                    acc_m = fm and mp; share = (mt.get("out_tokens") or 0) / sum(1 for kk in keys if kk[0] == task)
                    P["MR+"][0] += ok(f) if acc_m else ok(t); P["MR+"][1] += tf + share + (0 if acc_m else tt)
                    kind = "on_input" if not f["per_variant"].get("identity") else "edge_only"
                    if fm and not ok(f):
                        mst[(kind, "n")] += 1; mst[(kind, "flag")] += not mp
                    if fm and ok(f):
                        mst[("fa", task, "n")] += 1; mst[("fa", task, "flag")] += not mp
                    for r_ in (f, t):
                        if ok(r_):
                            mst[("valid", task, "n")] += 1; mst[("valid", task, "fail")] += not mr_pass(r_, mt["code"])
                if EDGE:
                    et = E[s][task]; ep = edge_pass(f, et["tests"])
                    acc_e = fm and ep; share = (et.get("out_tokens") or 0) / sum(1 for kk in keys if kk[0] == task)
                    P["EDGE"][0] += ok(f) if acc_e else ok(t); P["EDGE"][1] += tf + share + (0 if acc_e else tt)
                    kind = "on_input" if not f["per_variant"].get("identity") else "edge_only"
                    if fm and not ok(f):
                        est[(kind, "n")] += 1; est[(kind, "flag")] += not ep
                    if fm and ok(f):
                        est[("fa", task, "n")] += 1; est[("fa", task, "flag")] += not ep
                    for r_ in (f, t):   # validity note: correct programs (fact or thinking) that fail the tests
                        if ok(r_):
                            est[("valid", task, "n")] += 1; est[("valid", task, "fail")] += not edge_pass(r_, et["tests"])
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
        if MRX:
            print(f"  MR+ flags leaked fact programs: edge-case-only {mst[('edge_only', 'flag')]}/{mst[('edge_only', 'n')]}, "
                  f"wrong on the given input {mst[('on_input', 'flag')]}/{mst[('on_input', 'n')]}")
            print("  MR+ false alarms on correct MR-passing fact programs: " + ", ".join(f"{t} {mst[('fa', t, 'flag')]}/{mst[('fa', t, 'n')]}" for t in tasks))
            print("  relation validity (correct fact / thinking programs that break a relation): " + ", ".join(
                f"{t} {mst[('valid', t, 'fail')]}/{mst[('valid', t, 'n')]}" for t in tasks)
                  + "; relations per task that run (s1 / s2 / s3): " + ", ".join(f"{t} " + "/".join(str(M[s][t]["n_relations"] if M[s][t]["runs"] else 0) for s in (1, 2, 3)) for t in tasks))
        if EDGE:
            print(f"  EDGE flags leaked fact programs: edge-case-only {est[('edge_only', 'flag')]}/{est[('edge_only', 'n')]}, "
                  f"wrong on the given input {est[('on_input', 'flag')]}/{est[('on_input', 'n')]}")
            print("  EDGE false alarms on correct MR-passing fact programs: " + ", ".join(f"{t} {est[('fa', t, 'flag')]}/{est[('fa', t, 'n')]}" for t in tasks))
            print("  test validity (correct fact / thinking programs that fail the task's tests): " + ", ".join(
                f"{t} {est[('valid', t, 'fail')]}/{est[('valid', t, 'n')]}" for t in tasks)
                  + "; tests per task (s1 / s2 / s3): " + ", ".join(f"{t} " + "/".join(str(E[s][t]["n_tests"]) for s in (1, 2, 3)) for t in tasks))
        print("  F fails MR, B passes (TWO-VIEW takes B): " + ", ".join(
            f"{t} {bstat[(t, 'f_fail_b_pass')]} (B right {bstat[(t, 'f_fail_b_pass_ok')]}, THINK right {bstat[(t, 'f_fail_b_pass_think_ok')]})" for t in tasks))


if __name__ == "__main__":
    main()
