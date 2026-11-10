"""NaturalPlan Trip Planning (Zheng et al. 2406.04520), PREREG_NP: does the count gate carry to planning, the task where Amonkar et al. (2505.13252) find
the formalizer losing to the solver most consistently? NaturalPlan builds each trip "with enough constraints that there is only one solution" (its section
2.1.1), so a translation whose constraint model allows exactly one plan passes a free check, and 0 or 2 plans is label-free feedback, as on the grids.

The interface is not specific to trips: the model writes an OR-Tools CP-SAT model `m`, a dict `ANSWER` of the variables that decide the answer, and
`plan(val)` that renders the answer; the harness (PL_SOLVE) counts distinct rendered answers (projected count: it blocks each found assignment of
ANSWER until a second, different plan appears or none is left).

usage: run_plan.py <tag> <arm tr|trt|think> <seed> [--dev N (first N trips outside Amonkar's 100)] [--max_tokens N] [--rounds N (default 3)]
Default: Amonkar et al.'s 100 trips (data/trip_planning_100.json of github.com/rikhil-amonkar/llm-csp). Prompts: NaturalPlan's 5-shot prompt as is
(as Amonkar et al. use it), with our instruction after the task. Writes results/np_<tag>[_dev]_<arm>_s<seed>.jsonl.
"""
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
from llm import chat_msgs, last_block  # noqa: E402
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


def main():
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    opt = lambda k, d: int(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d
    tag, arm, seed = a[0], a[1], int(a[2])
    mt, nr, dev = opt("--max_tokens", 32000 if arm == "think" else 16000 if arm == "trt" else 4096), opt("--rounds", 3), opt("--dev", 0)
    R = [json.loads(l) for l in open(os.path.join(os.environ["POC_DATA"], "naturalplan", "trip.jsonl"))]
    P = [r for r in R if not r["amonkar"]][:dev] if dev else [r for r in R if r["amonkar"]]

    def run(r):
        p = re.sub(r"\s*SOLUTION:\s*$", "", r["prompt"])
        gold = np_norm({"city": c, "start": s, "end": e} for c, s, e in r["gold"])
        sd = seed * 10007 + int(r["id"].rsplit("_", 1)[1])
        row = {"id": r["id"], "ncity": r["ncity"], "arm": arm, "seed": seed}
        if arm == "think":
            o = chat_msgs([{"role": "user", "content": NP_FMT.format(p=p)}], think=True, max_tokens=mt, temperature=0.7, seed=sd)
            pl = np_norm(np_extract(o["text"]) or [])
            return {**row, "exact": pl == gold, "plan": pl, "tokens": o["out_tokens"], "finish": o["finish"], "text": (o["text"] or "")[-1500:]}
        msgs = [{"role": "user", "content": NP_TR.format(p=p)}]
        tok, hist = 0, []
        for rnd in range(nr):
            o = chat_msgs(msgs, think=arm == "trt", max_tokens=mt, temperature=0.7, seed=sd + rnd)
            tok += o["out_tokens"]
            code = last_block(o["text"], ("python", "py", "python3"))
            res = run_python("from ortools.sat.python import cp_model\n" + code + "\n" + PL_SOLVE, "", timeout=300, mem_bytes=4 << 30) if code else None
            try:
                out = json.loads(res.stdout.strip().splitlines()[-1])
            except (AttributeError, IndexError, ValueError):
                out = {"count": -1, "plan": None}
            pl = np_norm(out["plan"]) if out.get("plan") is not None else None
            hist.append({"count": out["count"], "exact": pl == gold, "tokens": o["out_tokens"], "finish": o["finish"], "err": (res.stderr[-300:] if res else "no code")})
            if out["count"] == 1:
                break
            fb = {-1: f"it failed to run: {(res.stderr[-600:] if res else 'no python block')}", -2: "the solver timed out on it",
                  0: "the constraints as you wrote them allow no plan, so one of them is wrong",
                  2: "the constraints as you wrote them allow more than one plan, so one is missing or too weak"}[out["count"]]
            msgs += [{"role": "assistant", "content": o["text"] or "(empty)"},
                     {"role": "user", "content": f"The task has exactly one valid plan, but {fb}. Compare each constraint with the task and give the complete corrected ```python block."}]
        return {**row, "exact": pl == gold, "plan": pl, "count": out["count"], "tokens": tok, "rounds": len(hist), "hist": hist, "code": code}

    path = f"{RES}/np_{tag}{'_dev' if dev else ''}_{arm}_s{seed}.jsonl"
    with ThreadPoolExecutor(32) as ex, open(path, "w") as f:
        rows = []
        for r in ex.map(run, P):
            rows.append(r); f.write(json.dumps(r) + "\n"); f.flush()
    print(tag, arm, seed, f"{sum(r['exact'] for r in rows)}/{len(rows)}", f"tokens {sum(r['tokens'] for r in rows) / len(rows):.0f}", flush=True)


if __name__ == "__main__":
    main()
