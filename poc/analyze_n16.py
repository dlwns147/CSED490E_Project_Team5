"""N16 (docs/prereg/PREREG_N16.md): token log-probs at solver API names, and confidence- vs execution-triggered documentation.
usage: python analyze_n16.py"""
import itertools, json, math, os, random, re, sys, collections, heapq, time, statistics as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_e1_taxonomy import ortools_vocab  # noqa: E402

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")
PROBS = ["knapsack", "tsp", "color", "sched", "binpack", "vcover", "cvrp", "vrptw"]
def real_api_names():
    """names that exist on live OR-Tools objects and modules (instances built here; dir() of classes alone missed CamelCase aliases
    such as CpModel.NewIntVar and module-level classes such as cp_model.CpModel: N16 analysis bug, fixed 2026-10-16)"""
    from ortools.sat.python import cp_model
    from ortools.constraint_solver import pywrapcp, routing_enums_pb2
    from ortools.linear_solver import pywraplp
    md = cp_model.CpModel(); sv = cp_model.CpSolver(); x = md.NewIntVar(0, 5, "x"); b = md.NewBoolVar("b")
    iv = md.NewIntervalVar(x, 1, x + 1, "i"); ct = md.Add(x >= 1)
    mg = pywrapcp.RoutingIndexManager(3, 1, 0); rt = pywrapcp.RoutingModel(mg); pr = pywrapcp.DefaultRoutingSearchParameters()
    cb = rt.RegisterTransitCallback(lambda i, j: 1); rt.AddDimension(cb, 0, 10, True, "D"); dm = rt.GetDimensionOrDie("D")
    ls = pywraplp.Solver.CreateSolver("SCIP"); lv = ls.IntVar(0, 1, "y"); lc = ls.Constraint(0, 1)
    objs = [cp_model, pywrapcp, routing_enums_pb2, pywraplp, md, sv, x, b, iv, ct, mg, rt, pr, cb if not isinstance(cb, int) else md, dm,
            ls, lv, lc, ls.Objective(), routing_enums_pb2.FirstSolutionStrategy, routing_enums_pb2.LocalSearchMetaheuristic, pr.time_limit,
            rt.solver(), x + 1, x == 1]
    names = set().union(*(dir(o) for o in objs))
    return {n for n in names if not n.startswith("_")} | set(ortools_vocab()[1]) | set(ortools_vocab()[0])


ORT = real_api_names()
COMMON = set().union(*(dir(t) for t in (list, dict, str, int, float, tuple, set, bool, type(None), object, math, sys, sys.stdin,
                                        itertools, collections, random, heapq, time, re, st, collections.deque, collections.Counter)))
opt = lambda r: r["status"] == "ok" and r["feasible"] and r["gap"] == 0
ok = lambda r: r["status"] == "ok" and r["feasible"]


def api_calls(r):
    """[(name, min log-prob over its tokens, invented?)] for every `.Name(` call of the first program."""
    toks, lps, text = r.get("lp_tok") or [], r.get("lp") or [], r.get("text0") or ""
    if not toks or not r.get("code"):
        return []
    joined = "".join(toks)
    base = joined.find(r["code"][:200])
    if base < 0:
        return []
    starts = list(itertools.accumulate([0] + [len(t) for t in toks]))
    defined = set(re.findall(r"def (\w+)", r["code"])) | set(re.findall(r"class (\w+)", r["code"]))
    out = []
    for m in re.finditer(r"\.([A-Za-z_]\w*)\s*\(", r["code"]):
        name = m.group(1)
        if name in defined or (name in COMMON and name not in ORT):
            continue
        a, b = base + m.start(1), base + m.end(1)
        idx = [i for i in range(len(toks)) if starts[i] < b and starts[i + 1] > a]
        if not idx:
            continue
        out.append((name, min(lps[i] for i in idx), name not in ORT))
    return out


def auroc(neg, pos):   # P(score of an invented name < score of a real name)
    if not neg or not pos:
        return float("nan")
    pos_s = sorted(pos); n = 0.0
    import bisect
    for x in neg:
        lo, hi = bisect.bisect_left(pos_s, x), bisect.bisect_right(pos_s, x)
        n += (len(pos_s) - hi) + 0.5 * (hi - lo)
    return n / (len(neg) * len(pos))


for m in ("q32b", "q36", "q8b"):
    F, S = {}, {}
    for sd in (1, 2, 3):
        for kind, D in (("nodoclp", F), ("snippet", S)):
            f = f"{RES}/co_S2_N16_{m}_{kind}_s{sd}.jsonl"
            if os.path.exists(f):
                for r in map(json.loads, open(f)):
                    D[(r["key"], sd)] = r
    if not F:
        continue
    keys = sorted(k for k in F if k in S)
    calls = {k: api_calls(F[k]) for k in keys}
    inv = [lp for k in keys for _, lp, i in calls[k] if i]; real = [lp for k in keys for _, lp, i in calls[k] if not i]
    names = collections.Counter(n for k in keys for n, _, i in calls[k] if i)
    print(f"\n=== {m}: {len(keys)} items; API-name calls: {len(real)} real, {len(inv)} invented (top invented {names.most_common(5)})")
    print(f"  min log-prob at the name: invented median {st.median(inv) if inv else float('nan'):.2f}, real median {st.median(real) if real else float('nan'):.2f}; "
          f"AUROC (invented lower) {auroc(inv, real):.3f}")
    crash_attr = sum(1 for k in keys if F[k]["status"] == "re" and "AttributeError" in (F[k].get("err") or ""))
    print(f"  first programs: optimal {sum(opt(F[k]) for k in keys)}, crash {sum(F[k]['status'] == 're' for k in keys)} "
          f"(AttributeError {crash_attr}), with >= 1 invented name {sum(any(i for _, _, i in calls[k]) for k in keys)}")
    score = {k: min([lp for _, lp, _ in calls[k]] or [0.0]) for k in keys}
    # policies
    res = {}
    res["first only"] = (sum(opt(F[k]) for k in keys), sum(F[k]["out_tokens"] for k in keys), 0)
    res["always snippet"] = (sum(opt(S[k]) for k in keys), sum(S[k]["out_tokens"] for k in keys), len(keys))
    trig = [k for k in keys if not ok(F[k])]
    res["execution trigger"] = (sum(opt(S[k]) if k in trig else opt(F[k]) for k in keys), sum(F[k]["out_tokens"] + (S[k]["out_tokens"] if k in trig else 0) for k in keys), len(trig))
    # confidence trigger, threshold chosen on the other problems (leave-one-problem-out), maximising optimal count, ties: fewer triggers
    a = t = n = 0
    for p in PROBS:
        tr = [k for k in keys if not k[0].startswith(p + "-")]; te = [k for k in keys if k[0].startswith(p + "-")]
        cands = sorted({round(score[k], 3) for k in tr}) + [1.0]
        def val(th, ks):
            return sum(opt(S[k]) if score[k] < th else opt(F[k]) for k in ks), -sum(score[k] < th for k in ks)
        th = max(cands, key=lambda c: val(c, tr))
        for k in te:
            g = score[k] < th; n += g
            a += opt(S[k]) if g else opt(F[k]); t += F[k]["out_tokens"] + (S[k]["out_tokens"] if g else 0)
    res["confidence trigger (LOPO)"] = (a, t, n)
    res["oracle trigger"] = (sum(max(opt(F[k]), opt(S[k])) for k in keys), 0, 0)
    for name, (a, t, n) in res.items():
        print(f"  {name:28s} {100 * a / len(keys):5.1f}% optimal" + (f" @ {t / len(keys) / 1000:.2f}k output tokens, re-generations {n}" if t else ""))
