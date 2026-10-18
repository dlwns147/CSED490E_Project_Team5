"""Run AlphaGeometry's symbolic engine (DD+AR, no language model) on problems from a file; print solved / time.
usage: python ddar_one.py <problems file> [name ...]"""
import sys, time
import matplotlib
matplotlib.use("Agg"); matplotlib.use = lambda *a, **k: None   # numericals.py forces TkAgg (no display here)
sys.path.insert(0, "/SSD/lean_postech/ag/alphageometry")
import graph as gh, problem as pr, ddar
defs = pr.Definition.from_txt_file("/SSD/lean_postech/ag/alphageometry/defs.txt", to_dict=True)
rules = pr.Theorem.from_txt_file("/SSD/lean_postech/ag/alphageometry/rules.txt", to_dict=True)
probs = pr.Problem.from_txt_file(sys.argv[1], to_dict=True, translate=False)
names = sys.argv[2:] or list(probs)
ok = 0
for n in names:
    p = probs[n]; t = time.time()
    try:
        g, _ = gh.Graph.build_problem(p, defs)
        ddar.solve(g, rules, p, max_level=1000)
        goal = p.goal
        args = g.names2nodes(goal.args)
        s = g.check(goal.name, args)
    except Exception as e:
        s = False; print(n, "error", str(e)[:80])
    ok += bool(s); print(n, "solved" if s else "not solved", f"{time.time() - t:.1f}s", flush=True)
print(f"DD+AR alone: {ok}/{len(names)}")
