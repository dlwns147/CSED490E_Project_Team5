"""N10 (docs/prereg/PREREG_N10.md): choosing the fix automatically from the first attempt's label-free failure signal. Offline, CPU.
Reads the fix-menu factorial (tags S2_N10_geo_<arm> / S2_N10_co_<arm>), runs the label-free check on every program (geometry: the
metamorphic check of poc/run_geo_mr.py on the given instance; optimization: the stored feasibility of the printed solution), and
scores the pre-registered policies: always-fix, gated single fix, cost-ordered cascade, the leave-one-task-out learned router (+ its
cascade variant) and the oracle. Scores: geometry correct on all 8 copies; optimization optimal. Tokens: every output token used.
Check results are cached in results/n10_check_cache.json (md5 of code + item).
usage: python analyze_n10.py [geo|co ...]"""
import hashlib, json, os, random, sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_geo import base_instance, render, variants  # noqa: E402
from run_geo_mr import mr_check  # noqa: E402
from sandbox import run_python  # noqa: E402

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
ARMS = {"geo": {"first": "k8_s1", "s2": "k8_s2", "s3": "k8_s3", "remove": "none_s1", "choose": "auto_s1", "input": "stdin_s1",
                "plan": "plan_s1", "think": "think_s1", "needed": "k0_s1"},
        "co": {"first": "doc_s1", "s2": "doc_s2", "s3": "doc_s3", "remove": "nodoc_s1", "choose": "rag3_s1", "input": "stdin_s1",
               "plan": "repair_s1", "think": "think_s1", "needed": "snippet_s1"}}
MENU = ["sample", "remove", "choose", "input", "plan", "think"]
NAME = {"geo": {"plan": "plan first"}, "co": {"plan": "repair once"}}
CACHE_F = f"{RES}/n10_check_cache.json"
CACHE = json.load(open(CACHE_F)) if os.path.exists(CACHE_F) else {}


def exc_type(stderr):
    lines = [l for l in (stderr or "").strip().splitlines() if l.strip()]
    head = lines[-1].split(":")[0].strip() if lines else ""
    return head.split(".")[-1] if head.split(".")[-1].isidentifier() else "other"


def geo_check(r):
    """(passes the metamorphic check, signal) for one geometry program on its own instance; no answer is used."""
    if not r.get("code"):
        return False, "no_code"
    k = hashlib.md5(f"{r['task']}-{r['n']}-{r['inst']}|{r['code']}".encode()).hexdigest()
    if k not in CACHE:
        rng = random.Random(f"{r['task']}-{r['n']}-{r['inst']}")
        V = variants(r["task"], base_instance(r["task"], r["n"], rng), rng)
        x = run_python(r["code"], render(r["task"], V["identity"])[1], timeout=10)
        if x.status != "ok":
            sig = "timeout" if x.status == "tle" else "exc:" + exc_type(x.stderr)
            CACHE[k] = [False, sig]
        elif not x.stdout.strip():
            CACHE[k] = [False, "no_output"]
        else:
            base, bad = mr_check(r["code"], r["task"], V)
            CACHE[k] = [base is not None and not bad, "pass" if base is not None and not bad else "check_fail"]
    return tuple(CACHE[k])


def co_check(r):
    if r["status"] == "no_code":
        return False, "no_code"
    if r["status"] == "tle":
        return False, "timeout"
    if r["status"] not in ("ok", "no_output"):
        return False, "exc:" + exc_type(r.get("err"))
    if r["status"] == "no_output":
        return False, "no_output"
    return bool(r["feasible"]), "pass" if r["feasible"] else "check_fail"


def load(dom):
    rows = {}
    for arm, tag in ARMS[dom].items():
        pre = os.environ.get("N10_PREFIX", "S2_N10")   # S2_N10m2 = the gpt-oss-20b replication
        f = f"{RES}/geocross_{pre}_geo_{tag}.jsonl" if dom == "geo" else f"{RES}/co_{pre}_co_{tag}.jsonl"
        if not os.path.exists(f):
            print(f"{dom}: missing {f}"); return None
        R = [json.loads(l) for l in open(f)]
        rows[arm] = {(r["task"], r["n"], r["inst"]) if dom == "geo" else r["key"]: r for r in R}
    keys = sorted(set.intersection(*(set(v) for v in rows.values())))
    return rows, keys


def outcomes(dom, rows, keys):
    """item -> {arm/fix: (correct, tokens, check_pass)}, item -> first-attempt signal, item -> task"""
    chk = geo_check if dom == "geo" else co_check
    jobs = [(a, k) for a in rows for k in keys]
    with ThreadPoolExecutor(24) as ex:
        res = dict(zip(jobs, ex.map(lambda j: chk(rows[j[0]][j[1]]), jobs)))
    json.dump(CACHE, open(CACHE_F, "w"))
    ok = (lambda r: r["class"] == "correct_all") if dom == "geo" else (lambda r: r["status"] == "ok" and r["feasible"] and r["gap"] == 0)
    tok = lambda r: r.get("out_tokens") or 0
    O, SIG, TASK = {}, {}, {}
    for k in keys:
        o = {}
        for a in rows:
            o[a] = (ok(rows[a][k]), tok(rows[a][k]), res[(a, k)][0])
        # sample + check: the first attempt plus seeds 2-3, choose by the label-free check
        cands = [a for a in ("first", "s2", "s3") if res[(a, k)][0]]
        if dom == "geo" and cands:   # metamorphic-consistent candidates, majority vote on the identity output (as mr_select.py)
            outs = {}
            for a in cands:
                rng = random.Random(f"{k[0]}-{k[1]}-{k[2]}")
                V = variants(k[0], base_instance(k[0], k[1], rng), rng)
                x = run_python(rows[a][k]["code"], render(k[0], V["identity"])[1], timeout=10)
                outs[a] = (x.stdout.strip().split() or [""])[-1].lower()
            vote = Counter(outs.values()).most_common(1)[0][0]
            pick = next(a for a in cands if outs[a] == vote)
        elif cands:   # optimization: feasible candidates, best objective (no reference used)
            sign = -1 if rows["first"][k]["prob"] == "knapsack" else 1
            pick = min(cands, key=lambda a: sign * rows[a][k]["value"])
        else:
            pick = "first"
        o["sample"] = (o[pick][0], tok(rows["s2"][k]) + tok(rows["s3"][k]), bool(cands))
        if dom == "co":   # the repair arm's tokens include its round-0 program (= the first attempt): count only the repair round
            rr = rows["plan"][k]
            o["plan"] = (o["plan"][0], max(0, tok(rr) - tok(rows["first"][k])) if rr.get("repair_rounds") else 0, o["plan"][2])
        O[k], SIG[k] = o, res[("first", k)][1]
        TASK[k] = k[0] if dom == "geo" else rows["first"][k]["prob"]
    return O, SIG, TASK


def run_policy(O, keys, choose):
    """choose(k) -> list of fixes to try in order (empty = keep the first attempt). Gated: only items failing the check."""
    acc = tok = 0
    for k in keys:
        o = O[k]; t = o["first"][1]; c = o["first"][0]
        if not o["first"][2]:
            for f in choose(k):
                c, t = o[f][0], t + o[f][1]
                if o[f][2]:
                    break
        acc += c; tok += t
    return 100 * acc / len(keys), tok / len(keys)


def main(dom):
    L = load(dom)
    if not L:
        return
    rows, keys = L
    O, SIG, TASK = outcomes(dom, rows, keys)
    tasks = sorted(set(TASK.values()))
    fail = [k for k in keys if not O[k]["first"][2]]
    print(f"\n=== {dom}: {len(keys)} items, {len(tasks)} tasks; first attempt correct {sum(O[k]['first'][0] for k in keys)} "
          f"({100 * sum(O[k]['first'][0] for k in keys) / len(keys):.1f}%), fails the check {len(fail)}; "
          f"check passes but wrong: {sum(O[k]['first'][2] and not O[k]['first'][0] for k in keys)}")
    print("first-attempt signals:", dict(Counter(SIG[k] for k in keys).most_common()))
    nm = lambda f: NAME[dom].get(f, f)
    # fix success on the failing items, per signal
    print("success of each fix on items failing the check (by signal):")
    sigs = [s for s, _ in Counter(SIG[k] for k in fail).most_common()]
    for s in sigs:
        ks = [k for k in fail if SIG[k] == s]
        print(f"  {s:28s} n={len(ks):3d} " + " ".join(f"{nm(f)} {sum(O[k][f][0] for k in ks)}" for f in MENU + ["needed"]))
    print("  token cost per fix (mean over all items): " + ", ".join(f"{nm(f)} {sum(O[k][f][1] for k in keys) / len(keys):.0f}" for f in MENU))
    lines = []
    a, t = run_policy(O, keys, lambda k: []); lines.append(("first attempt only", a, t))
    for f in MENU + ["needed"]:   # always-fix: use the fix's condition from the start (sample = 3 samples + check)
        if f == "sample":
            acc = sum(O[k]["sample"][0] for k in keys); tk = sum(O[k]["first"][1] + O[k]["sample"][1] for k in keys)
        elif f == "plan" and dom == "co":
            acc = sum(O[k]["plan"][0] for k in keys); tk = sum(O[k]["first"][1] + O[k]["plan"][1] for k in keys)
        else:
            acc = sum(O[k][f][0] for k in keys); tk = sum(O[k][f][1] for k in keys)
        lines.append((f"always {nm(f)}" + (" (reference: needs a human)" if f == "needed" else ""), 100 * acc / len(keys), tk / len(keys)))
    gated = {f: run_policy(O, keys, lambda k, f=f: [f]) for f in MENU}
    for f in MENU:
        lines.append((f"gated {nm(f)}", *gated[f]))
    best_f = max(MENU, key=lambda f: (gated[f][0], -gated[f][1]))
    # leave-one-task-out learned router and cascades
    route, lcasc, ccasc, loto_single = {}, {}, {}, {}
    for T in tasks:
        tr = [k for k in fail if TASK[k] != T]; tr_all = [k for k in keys if TASK[k] != T]
        cost = {f: sum(O[k][f][1] for k in tr_all) / len(tr_all) for f in MENU}
        rate = lambda ks, f: (sum(O[k][f][0] for k in ks) / len(ks)) if ks else 0
        overall = sorted(MENU, key=lambda f: (-rate(tr, f), cost[f]))
        for k in keys:
            if TASK[k] != T:
                continue
            ks = [j for j in tr if SIG[j] == SIG[k]]
            order = sorted(MENU, key=lambda f: (-rate(ks, f), cost[f])) if len(ks) >= 5 else overall
            route[k], lcasc[k] = [order[0]], order
            ccasc[k] = sorted(MENU, key=lambda f: cost[f])
            loto_single[k] = [overall[0]]
    lines.append(("cascade, cheapest fix first (LOTO costs)", *run_policy(O, keys, lambda k: ccasc[k])))
    lines.append(("single fix chosen on the other tasks (LOTO)", *run_policy(O, keys, lambda k: loto_single[k])))
    lines.append(("LEARNED ROUTER (LOTO, by signal)", *run_policy(O, keys, lambda k: route[k])))
    lines.append(("learned router + cascade in its order", *run_policy(O, keys, lambda k: lcasc[k])))
    # oracle: per failing item, the cheapest correct fix (gives up when none is correct)
    acc = tok = 0
    for k in keys:
        o = O[k]; t = o["first"][1]; c = o["first"][0]
        if not o["first"][2]:
            good = [f for f in MENU if o[f][0]]
            if good:
                f = min(good, key=lambda f: o[f][1]); c, t = True, t + o[f][1]
        acc += c; tok += t
    lines.append(("oracle (cheapest correct fix per item)", 100 * acc / len(keys), tok / len(keys)))
    print(f"policies (accuracy @ mean tokens per item); best gated single fix in hindsight: {nm(best_f)}")
    for name, a, t in lines:
        print(f"  {name:46s} {a:5.1f}% @ {t:7.0f}")


if __name__ == "__main__" and not os.environ.get("N11"):
    for d in sys.argv[1:] or ["geo", "co"]:
        main(d)


def probe_commit(dom):
    """N11 (PREREG_N10.md): per problem, probe every whole-prompt option on instance 0 of each size, commit to the option with the
    highest label-free check pass rate on the probes (ties: fewer tokens), use it on the other instances; probe tokens are charged."""
    rows, keys = load(dom)
    O, SIG, TASK = outcomes(dom, rows, keys)
    OPT = ["first", "remove", "choose", "input", "plan", "think", "sample"]
    inst = (lambda k: k[2]) if dom == "geo" else (lambda k: int(k.rsplit("-", 1)[1]))
    def opt(k, f):   # whole-prompt option: (correct, tokens, check) with sample = 3 samples, repair = first + repair round
        o = O[k]
        if f == "sample" or (f == "plan" and dom == "co"):
            return o[f][0], o["first"][1] + o[f][1], o[f][2]
        return o[f]
    tasks = sorted(set(TASK.values()))
    pc = {"acc": 0, "tok": 0, "n": 0}; glob = {f: [0, 0] for f in OPT}; orac = [0, 0]; picks = {}
    for T in tasks:
        P = [k for k in keys if TASK[k] == T and inst(k) == 0]; C = [k for k in keys if TASK[k] == T and inst(k) != 0]
        probe_tok = sum(opt(k, f)[1] for k in P for f in OPT)
        score = {f: (sum(opt(k, f)[2] for k in P) / len(P), -sum(opt(k, f)[1] for k in P)) for f in OPT}
        f = max(OPT, key=lambda f: score[f]); picks[T] = f
        pc["acc"] += sum(opt(k, f)[0] for k in C); pc["tok"] += sum(opt(k, f)[1] for k in C) + probe_tok; pc["n"] += len(C)
        for g in OPT:
            glob[g][0] += sum(opt(k, g)[0] for k in C); glob[g][1] += sum(opt(k, g)[1] for k in C)
        best = max(OPT, key=lambda g: (sum(opt(k, g)[0] for k in C), -sum(opt(k, g)[1] for k in C)))
        orac[0] += sum(opt(k, best)[0] for k in C); orac[1] += sum(opt(k, best)[1] for k in C)
    n = pc["n"]; nm = lambda f: NAME[dom].get(f, f)
    print(f"\n=== N11 {dom}: probe, then commit ({n} committed items; probe tokens charged) ===")
    print("  picks:", {T: nm(f) for T, f in picks.items()})
    print(f"  {'PROBE, THEN COMMIT':34s} {100 * pc['acc'] / n:5.1f}% @ {pc['tok'] / n:6.0f}")
    print(f"  {'per-problem oracle default':34s} {100 * orac[0] / n:5.1f}% @ {orac[1] / n:6.0f}")
    for g in OPT:
        print(f"  {'always ' + nm(g):34s} {100 * glob[g][0] / n:5.1f}% @ {glob[g][1] / n:6.0f}")


if __name__ == "__main__" and os.environ.get("N11"):
    for d in sys.argv[1:] or ["geo", "co"]:
        probe_commit(d)
