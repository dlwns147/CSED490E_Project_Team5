"""Check auxiliary constructions proposed by an LLM: insert each before the goal, rebuild the problem, run DD+AR (time limit per
proposal). usage: python ddar_aux.py <aux_<tag>.jsonl> [timeout_s]   -> adds valid / proved / seconds to each row (rewrites the file)."""
import json, multiprocessing as mp, sys, time
import matplotlib
matplotlib.use("Agg"); matplotlib.use = lambda *a, **k: None   # numericals.py forces TkAgg (no display here)
sys.path.insert(0, "/SSD/lean_postech/ag/alphageometry")
import graph as gh, problem as pr, ddar  # noqa: E402

DEFS = pr.Definition.from_txt_file("/SSD/lean_postech/ag/alphageometry/defs.txt", to_dict=True)
RULES = pr.Theorem.from_txt_file("/SSD/lean_postech/ag/alphageometry/rules.txt", to_dict=True)


def attempt(args):
    name, prob, aux = args
    if not aux:
        return {"valid": False, "proved": False, "why": "no clause"}
    setup, goal = prob.split(" ? ")
    txt = f"{name}\n{setup}; {aux} ? {goal}"
    try:
        p = pr.Problem.from_txt(txt.split("\n", 1)[1], translate=False)
        g, _ = gh.Graph.build_problem(p, DEFS)
    except Exception as e:   # unknown construction, wrong arity, reused name, impossible configuration
        return {"valid": False, "proved": False, "why": f"{type(e).__name__}: {str(e)[:80]}"}
    t = time.time()
    ddar.solve(g, RULES, p, max_level=1000)
    ok = bool(g.check(p.goal.name, g.names2nodes(p.goal.args)))
    return {"valid": True, "proved": ok, "seconds": round(time.time() - t, 1)}


def run(args, timeout):
    with mp.get_context("fork").Pool(1) as pool:
        r = pool.apply_async(attempt, (args,))
        try:
            return r.get(timeout)
        except mp.TimeoutError:
            return {"valid": True, "proved": False, "why": "timeout"}


if __name__ == "__main__":
    path, timeout = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 600
    rows = [json.loads(l) for l in open(path, errors="replace") if l.strip() and not l.startswith(chr(0))]
    todo = [r for r in rows if "proved" not in r]
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(16) as ex:
        res = list(ex.map(lambda r: run((r["name"], r["problem"], r["aux"]), timeout), todo))
    for r, c in zip(todo, res):
        r.update(c)
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    names = {r["name"] for r in rows}
    proved = {r["name"] for r in rows if r.get("proved")}
    print(path, f"proposals {len(rows)}, valid {sum(r.get('valid', False) for r in rows)}, proving {sum(r.get('proved', False) for r in rows)}; "
          f"problems proved {len(proved)} of {len(names)}: {sorted(proved)}", flush=True)
