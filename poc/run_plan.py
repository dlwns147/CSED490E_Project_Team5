"""NaturalPlan Trip Planning (Zheng et al. 2406.04520), PREREG_NP: does the count gate carry to planning, the task where Amonkar et al. (2505.13252) find
the formalizer losing to the solver most consistently? NaturalPlan builds each trip "with enough constraints that there is only one solution" (its section
2.1.1), so a translation whose constraint model allows exactly one plan passes a free check, and 0 or 2 plans is label-free feedback, as on the grids.

The interface is not specific to trips: the model writes an OR-Tools CP-SAT model `m`, a dict `ANSWER` of the variables that decide the answer, and
`plan(val)` that renders the answer; the harness (PL_SOLVE) counts distinct rendered answers (projected count: it blocks each found assignment of
ANSWER until a second, different plan appears or none is left).

usage: run_plan.py <tag> <arm tr|trt|trc|trct|think|direct> <seed> [--resume (keep the rows already written, run the rest)]
       (arm direct, PREREG_MOT addendum MOT-T: the think prompt without thinking; every round keeps its plan)
       (arm thinkb, PREREG_BUD: the think prompt under budget forcing at each of --budgets, default 1000,2000,4000,8000, cut from one think; row["cuts"][B])
       run_plan.py --check <tag> [--dev] [--label L (another model serving: writes np_<tag>_<L>.jsonl)] (PREREG_NPC: the model checks each count-1 plan against the task, see check())
       run_plan.py --rescore <result files> (re-run stored programs under the current harness, see rescore()) [--dev N (N trips outside Amonkar's 100, spread over the file, so over 3-10 cities)] [--max_tokens N] [--rounds N (default 3)]
Default: Amonkar et al.'s 100 trips (data/trip_planning_100.json of github.com/rikhil-amonkar/llm-csp). Prompts: NaturalPlan's 5-shot prompt as is
(as Amonkar et al. use it), with our instruction after the task. Writes results/np_<tag>[_dev]_<arm>_s<seed>.jsonl.
"""
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
from llm import chat_msgs, last_block, think_cuts  # noqa: E402
from sandbox import run_python  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = f"{ROOT}/results"

PL_SOLVE = """
import json
from ortools.sat.python import cp_model
def _solve():
    s = cp_model.CpSolver(); s.parameters.num_workers = 1; s.parameters.max_time_in_seconds = 60
    st = s.Solve(m)
    return s if st in (cp_model.OPTIMAL, cp_model.FEASIBLE) else ("unknown" if st == cp_model.UNKNOWN else None)
assert isinstance(ANSWER, dict) and ANSWER, "ANSWER must be a non-empty dict of model variables"
class _V(dict):   # val(name) as asked; val[name] also works (the dev pilot's first programs indexed it)
    __call__ = dict.__getitem__
first, cnt = None, 0
for _ in range(50):
    s = _solve()
    if s == "unknown":
        cnt = -2 if first is None else cnt; break
    if s is None:
        break
    v = {k: s.Value(x) for k, x in ANSWER.items()}
    p = plan(_V(v))
    if first is None:
        first, cnt = p, 1
    elif p != first:
        cnt = 2; break
    bs = []
    for k, x in ANSWER.items():
        b = m.NewBoolVar(""); m.Add(x != v[k]).OnlyEnforceIf(b); bs.append(b)
    m.AddBoolOr(bs)
print(json.dumps({"count": cnt, "plan": first}, default=str))
"""
NP_TR = ("{p}\n\nDo not solve the task. Translate it into a constraint model. Give one ```python block that uses OR-Tools CP-SAT (`from ortools.sat.python import "
         "cp_model`) and defines three things: `m`, a cp_model.CpModel holding every constraint the task states (read the day-counting convention off the example "
         "solutions above); `ANSWER`, a dict from names to the model variables whose values decide the trip plan; and `plan(val)`, a function that, given "
         "val(name) = the solved value of ANSWER[name], returns the plan as a list of {{\"city\": name, \"start\": first day, \"end\": last day}} in visiting order. "
         "Do not call a solver and do not fix the answer by hand: a harness solves `m` and counts the plans it allows.")
# Arms trc / trct (dev pilot 2026-11-10: in the CP-SAT interface the quick translation reached count 1 on 1 of 30 trips: it orders the cities in its
# head and misplaces the shared flight day). Declarations only, as idea 18 on AR-LSAT: the model writes what an answer can look like and one check per
# stated requirement; the harness enumerates and counts. Nothing here is specific to trips either.
PC_SOLVE = """
import json, time
if callable(constraints):   # dev pilots: `constraints` written as a function returning the list, or as one check taking an answer
    try:
        constraints = constraints()
    except TypeError:
        constraints = [constraints]
def _ok(f, a):   # 2026-11-10 19:5x fix: `constraints(answer)` that RETURNS the list of checks was taken as one check, and a non-empty list is true
    v = f(a)
    return all((g(a) if callable(g) else bool(g)) for g in v) if isinstance(v, (list, tuple)) else bool(v)
_t0, _seen, _n = time.time(), [], 0
for _a in candidates():
    _n += 1
    if all(_ok(_f, _a) for _f in constraints):
        _k = json.dumps(_a, sort_keys=True, default=str)
        if _k not in _seen:
            _seen.append(_k)
            if len(_seen) >= 2:
                break
    if time.time() - _t0 > 240:
        print(json.dumps({"count": -2, "plan": None, "n": _n})); raise SystemExit
print(json.dumps({"count": len(_seen), "plan": json.loads(_seen[0]) if _seen else None, "n": _n}))
"""
NP_TRC = ("{p}\n\nDo not solve the task. Translate it. Give one ```python block that defines two things. `candidates()`: a generator that yields every "
          "answer of the right form, a superset of the valid ones (what an answer could be before the task's requirements are checked; read the "
          "day-counting convention off the example solutions above), each as a list of {{\"city\": name, \"start\": first day, \"end\": last day}} in "
          "visiting order. `constraints`: a list of functions, one for each requirement the task states, each taking an answer and returning True or False. "
          "Do not solve the task and do not fix the answer by hand: a harness keeps the answers that pass every constraint and counts them.")
# PREREG_NP addendum NP-DAY: the day convention, shown only by NaturalPlan's examples, stated in the task for every arm (thinking included). In the dev pilot
# 5 of 5 zero-plan declarations had right constraints and a candidate generator that started the next city the day after the last one ended.
NP_DAY = " A day on which you fly from one city to another counts as a day in both cities, so the next city's stay starts on the day the previous stay ends."
NP_FMT = "{p}\n\nSolve the task. On the last line give the plan as JSON: a list of {{\"city\": name, \"start\": first day, \"end\": last day}} in visiting order."


def np_norm(plan):
    """a plan as a tuple of (city, start, end), or None"""
    try:
        return tuple((str(x["city"]).strip().lower(), int(x["start"]), int(x["end"])) for x in plan)
    except (TypeError, KeyError, ValueError, AttributeError):
        return None


def np_extract(text):
    """the last JSON list in an answer"""
    dec, i, g = json.JSONDecoder(), 0, None
    while i < len(text or ""):
        if text[i] == "[":
            try:
                x, n = dec.raw_decode(text, i)
                if isinstance(x, list):
                    g = x
                i = n
                continue
            except ValueError:
                pass
        i += 1
    return g


def rescore(paths):
    """run_plan.py --rescore <results/np_*_trc*.jsonl ...>: re-run each row's final program under the current PC_SOLVE (no model call); writes
    results/np_rescore.jsonl with id, file, old count, new count, candidates enumerated (n) and whether the new plan is the gold plan."""
    G = {r["id"]: r for r in map(json.loads, open(os.path.join(os.environ["POC_DATA"], "naturalplan", "trip.jsonl")))}
    jobs = [(p, json.loads(l)) for p in paths for l in open(p)]
    def one(pr):
        p, r = pr
        res = run_python("import itertools\n" + r["code"] + "\n" + PC_SOLVE, "", timeout=300, mem_bytes=4 << 30) if r.get("code") else None
        try:
            out = json.loads(res.stdout.strip().splitlines()[-1])
        except (AttributeError, IndexError, ValueError):
            out = {"count": -1, "plan": None}
        gold = np_norm({"city": c, "start": s_, "end": e} for c, s_, e in G[r["id"]]["gold"])
        pl = np_norm(out["plan"]) if out.get("plan") is not None else None
        return {"file": os.path.basename(p), "id": r["id"], "seed": r["seed"], "old": r["count"], "new": out["count"], "n": out.get("n"), "exact": pl == gold, "old_exact": r["exact"]}
    with ThreadPoolExecutor(32) as ex, open(f"{RES}/np_rescore.jsonl", "w") as f:
        for x in ex.map(one, jobs):
            f.write(json.dumps(x) + "\n")


# PREREG_NPC: PREREG_GC's clue check on trips. The same model, thinking, is shown the task (0-shot text plus NP_DAY) and the stored count-1 plan, and
# lists the requirements the plan breaks; a non-empty list sends the ladder step on. Aimed at misreadings that keep the count at 1 (a shifted schedule).
NP_CHECK = ("{p}\n\nHere is a proposed plan, one line per stay:\n{plan}\n\nDo not solve the task. Check the plan against each requirement the task states, "
            "in turn: for each requirement write it briefly, yes if the plan satisfies it as written or no if it does not, and a short reason. "
            "On the last line give JSON {{\"violated\": [short names of the requirements the plan breaks]}}.")


def check(tag, dev):
    """run_plan.py --check <tag> [--dev]: PREREG_NPC's check on every count-1 row of results/np_<tag>[_dev]_{trc,trct}_s{1,2,3}.jsonl;
    writes results/np_<tag>[_dev]_checkt.jsonl (id, tr, seed, exact, violated (None = unparsed, read as no flag), tokens, finish, text tail)."""
    G = {r["id"]: r for r in map(json.loads, open(os.path.join(os.environ["POC_DATA"], "naturalplan", "trip.jsonl")))}
    pre = f"{RES}/np_{tag}{'_dev' if dev else ''}"
    jobs = [(tr, sd, r) for tr in ["trc", "trct"] for sd in [1, 2, 3] if os.path.exists(f"{pre}_{tr}_s{sd}.jsonl")
            for r in map(json.loads, open(f"{pre}_{tr}_s{sd}.jsonl")) if r["count"] == 1 and r["plan"]]
    def one(j):
        tr, sd, r = j
        p = G[r["id"]]["prompt0"].rstrip() + NP_DAY
        plan = "\n".join(f"Day {s_}-{e}: {c.title()}" for c, s_, e in r["plan"])
        o = chat_msgs([{"role": "user", "content": NP_CHECK.format(p=p, plan=plan)}], think=True, max_tokens=8000, temperature=0.7,
                      seed=sd * 10007 + int(r["id"].rsplit("_", 1)[1]) + 99)
        m = re.findall(r"\{[^{}]*\"violated\"[^{}]*\}", o["text"] or "")
        try:
            vio = list(json.loads(m[-1])["violated"])
        except (IndexError, ValueError, TypeError, KeyError):
            vio = None
        return {"id": r["id"], "ncity": r["ncity"], "tr": tr, "seed": sd, "exact": r["exact"], "violated": vio, "tokens": o["out_tokens"],
                "finish": o["finish"], "text": (o["text"] or "")[-2500:]}
    rows = []
    lab = sys.argv[sys.argv.index("--label") + 1] if "--label" in sys.argv else "checkt"   # NPC-X: the same check served by another model family
    with ThreadPoolExecutor(32) as ex, open(f"{pre}_{lab}.jsonl", "w") as f:
        for x in ex.map(one, jobs):
            rows.append(x); f.write(json.dumps(x) + "\n"); f.flush()
    W = [x for x in rows if not x["exact"]]
    print(tag, lab, f"{len(rows)} checked; wrong flagged {sum(bool(x['violated']) for x in W)}/{len(W)}, right flagged "
          f"{sum(bool(x['violated']) for x in rows if x['exact'])}/{len(rows) - len(W)}, unparsed {sum(x['violated'] is None for x in rows)}, "
          f"truncated {sum(x['finish'] == 'length' for x in rows)}, ktok {sum(x['tokens'] for x in rows) / max(1, len(rows)) / 1000:.2f}", flush=True)


def modulo_critics(path):
    """LLM-Modulo (Gundawar et al. 2411.14484) on our trips: critics built from each task's structured constraints (Amonkar et al.'s file, parsed
    from the task text, not from the gold plan): {trip id: f(plan) -> list of the requirements the plan breaks, in words}."""
    import ast, collections
    out = {}
    for k, v in json.load(open(path)).items():
        C = ast.literal_eval(v["constraints"]) if isinstance(v["constraints"], str) else v["constraints"]
        L = {d["city"].lower(): (d["city"], d["days"]) for d in C["city_length"]}
        E = set()
        fl = v["prompt_0shot"].split("direct flights:")[1].split("\n\n")[0].strip().rstrip(".")
        for part in fl.split(", "):
            part = part.strip()
            if part.startswith("from "):
                x, y = part[5:].split(" to "); E.add((x.strip().lower(), y.strip().lower()))
            else:
                x, y = part.split(" and "); E.add((x.strip().lower(), y.strip().lower())); E.add((y.strip().lower(), x.strip().lower()))
        R = collections.defaultdict(list)
        for r in C["city_day_ranges"]:
            R[r["city"].lower()].append((r["start"], r["end"]))

        def f(plan, L=L, E=E, R=R, T=C["trip_length"]):
            if not plan:
                return ["no plan was given as a JSON list on the last line"]
            P, bad = list(plan), []
            got = [c for c, _, _ in P]
            for c in sorted(set(L) - set(got)):
                bad.append(f"{L[c][0]} is not visited")
            for c in got:
                if c not in L:
                    bad.append(f"{c} is not one of the cities to visit")
                elif got.count(c) > 1:
                    bad.append(f"{L[c][0]} is visited more than once")
            if P[0][1] != 1:
                bad.append("the trip must start on day 1")
            if P[-1][2] != T:
                bad.append(f"the trip must end on day {T}")
            for i in range(len(P) - 1):
                if P[i + 1][1] != P[i][2]:
                    bad.append(f"the stay in {P[i + 1][0]} must start on day {P[i][2]}, the day of the flight from {P[i][0]}")
                if (P[i][0], P[i + 1][0]) not in E:
                    bad.append(f"there is no direct flight from {P[i][0]} to {P[i + 1][0]}")
            for c, a0, e0 in P:
                if c in L and e0 - a0 + 1 != L[c][1]:
                    bad.append(f"the stay in {L[c][0]} must be {L[c][1]} days (day {a0} to day {e0} is {e0 - a0 + 1})")
                for a1, b1 in R.get(c, []):
                    if not (a0 <= a1 and b1 <= e0):
                        bad.append(f"the stay in {L[c][0]} must cover day {a1} to day {b1}")
            return bad
        out[k] = f
    return out


def main():
    if "--rescore" in sys.argv:
        return rescore([x for x in sys.argv[1:] if not x.startswith("--")])
    if "--check" in sys.argv:
        a = [x for x in sys.argv[1:] if not x.startswith("--")]
        return check(a[0], "--dev" in sys.argv)
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    opt = lambda k, d: int(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d
    tag, arm, seed = a[0], a[1], int(a[2])
    mt, nr, dev = opt("--max_tokens", 32000 if arm in ("think", "modulo") else 16000 if arm in ("trt", "trct") else 4096), opt("--rounds", 10 if arm == "modulo" else 3), opt("--dev", 0)
    global CRIT
    CRIT = modulo_critics(os.path.join(os.environ["POC_DATA"], "naturalplan_dl", "a_trip_planning_100_constraints.json")) if arm == "modulo" else {}
    BUD = [int(x) for x in sys.argv[sys.argv.index("--budgets") + 1].split(",")] if "--budgets" in sys.argv else [1000, 2000, 4000, 8000]
    R = [json.loads(l) for l in open(os.path.join(os.environ["POC_DATA"], "naturalplan", "trip.jsonl"))]
    P = [r for r in R if not r["amonkar"]][::max(1, 1500 // dev)][:dev] if dev else [r for r in R if r["amonkar"]]

    def run(r):
        p = re.sub(r"\s*SOLUTION:\s*$", "", r["prompt"])
        k = p.rindex("Find a trip plan")   # the task's own last sentence, after the five examples
        p = p[:k] + p[k:].rstrip() + NP_DAY
        gold = np_norm({"city": c, "start": s, "end": e} for c, s, e in r["gold"])
        sd = seed * 10007 + int(r["id"].rsplit("_", 1)[1])
        row = {"id": r["id"], "ncity": r["ncity"], "arm": arm, "seed": seed}
        if arm == "thinkb":   # PREREG_BUD: budget-forced thinking at every budget of --budgets, cut from one think (llm.think_cuts)
            C = think_cuts(NP_FMT.format(p=p), BUD, seed=sd)
            cuts = {str(b): {"exact": pl == gold, "tokens": o["out_tokens"], "cut": o["cut"], "finish": o["finish"], "plan": pl}
                    for b, o in C.items() for pl in [np_norm(np_extract(o["text"]) or [])]}
            return {**row, "exact": cuts[str(max(BUD))]["exact"], "tokens": cuts[str(max(BUD))]["tokens"], "cuts": cuts}
        if arm in ("think", "direct"):
            o = chat_msgs([{"role": "user", "content": NP_FMT.format(p=p)}], think=arm == "think", max_tokens=mt, temperature=0.7, seed=sd)
            pl = np_norm(np_extract(o["text"]) or [])
            return {**row, "exact": pl == gold, "plan": pl, "tokens": o["out_tokens"], "finish": o["finish"], "text": (o["text"] or "")[-1500:]}
        if arm == "modulo":   # LLM-Modulo: think, then the critics' list of broken requirements goes back, up to --rounds (their setting: 10)
            msgs, tok, hist = [{"role": "user", "content": NP_FMT.format(p=p)}], 0, []
            for rnd in range(nr):
                try:
                    o = chat_msgs(msgs, think=True, max_tokens=mt, temperature=0.7, seed=sd + rnd)
                except Exception as e:
                    hist.append({"exact": False, "tokens": 0, "err": repr(e)[:300]}); break
                tok += o["out_tokens"]
                raw = np_extract(o["text"]) or []
                pl = np_norm(raw)
                bad = CRIT[r["id"]](pl)
                hist.append({"exact": pl == gold, "tokens": o["out_tokens"], "finish": o["finish"], "plan": pl, "broken": bad[:8]})
                if not bad:
                    break
                msgs += [{"role": "assistant", "content": json.dumps(raw)},
                         {"role": "user", "content": "A checker found that this plan breaks the task: " + "; ".join(bad[:8]) + ". Give a corrected plan; on the last "
                          "line give it as JSON: a list of {\"city\": name, \"start\": first day, \"end\": last day} in visiting order."}]
            return {**row, "exact": pl == gold, "plan": pl, "tokens": tok, "rounds": len(hist), "passed": not bad, "hist": hist}
        dc = arm in ("trc", "trct")
        msgs = [{"role": "user", "content": (NP_TRC if dc else NP_TR).format(p=p)}]
        tok, hist = 0, []
        for rnd in range(nr):
            try:
                o = chat_msgs(msgs, think=arm in ("trt", "trct"), max_tokens=mt, temperature=0.7, seed=sd + rnd)
            except Exception as e:   # test run 2026-11-10: a repair round's history passed the 40,960-token context; the rounds end there, as on the grids
                if rnd == 0:
                    raise
                hist.append({"count": None, "exact": False, "tokens": 0, "finish": "error", "err": repr(e)[:300]})
                break
            tok += o["out_tokens"]
            code = last_block(o["text"], ("python", "py", "python3"))
            res = (run_python(("import itertools\n" + code + "\n" + PC_SOLVE) if dc else ("from ortools.sat.python import cp_model\n" + code + "\n" + PL_SOLVE),
                              "", timeout=300, mem_bytes=4 << 30) if code else None)
            try:
                out = json.loads(res.stdout.strip().splitlines()[-1])
            except (AttributeError, IndexError, ValueError):
                out = {"count": -1, "plan": None}
            pl = np_norm(out["plan"]) if out.get("plan") is not None else None
            hist.append({"count": out["count"], "exact": pl == gold, "tokens": o["out_tokens"], "finish": o["finish"], "n": out.get("n"), "err": (res.stderr[-300:] if res else "no code"), "plan": pl})
            if out["count"] == 1:
                break
            fb = {-1: f"it failed to run: {(res.stderr[-600:] if res else 'no python block')}", -2: "the solver timed out on it",
                  0: "the constraints as you wrote them allow no plan, so one of them is wrong" + (" (or `candidates` misses the valid plan)" if dc else ""),
                  2: "the constraints as you wrote them allow more than one plan, so one is missing or too weak"}[out["count"]]
            msgs += [{"role": "assistant", "content": o["text"] or "(empty)"},
                     {"role": "user", "content": f"The task has exactly one valid plan, but {fb}. Compare each constraint with the task and give the complete corrected ```python block."}]
        return {**row, "exact": pl == gold, "plan": pl, "count": out["count"], "tokens": tok, "rounds": len(hist), "hist": hist, "code": code}

    path = f"{RES}/np_{tag}{'_dev' if dev else ''}_{arm}_s{seed}.jsonl"
    rows = []
    if "--resume" in sys.argv and os.path.exists(path):   # keep the rows a crashed run wrote, run the rest
        rows = [json.loads(l) for l in open(path)]
        P = [r for r in P if r["id"] not in {x["id"] for x in rows}]
    with ThreadPoolExecutor(32) as ex, open(path, "a" if rows else "w") as f:
        for r in ex.map(run, P):
            rows.append(r); f.write(json.dumps(r) + "\n"); f.flush()
    print(tag, arm, seed, f"{sum(r['exact'] for r in rows)}/{len(rows)}", f"tokens {sum(r['tokens'] for r in rows) / len(rows):.0f}", flush=True)


if __name__ == "__main__":
    main()
