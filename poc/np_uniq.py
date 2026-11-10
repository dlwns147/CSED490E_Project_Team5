"""PREREG_NP: how many valid plans does each NaturalPlan trip allow? Enumerates city orders over the direct flights (one-way "from A to B" parsed from the
prompt, "A and B" both ways), stays of the stated lengths sharing the flight day, total length; a dated event either inside the stay ("cover") or
only overlapping it ("overlap"). usage: python3 poc/np_uniq.py <nlp_data>/naturalplan_dl/a_trip_planning_100_constraints.json
(2026-11-10: cover 95 one plan, 3 two, 2 three; overlap 36 one)."""
import json, ast, sys, collections
c = json.load(open(sys.argv[1]))
def count(C, mode):
    L = {d["city"]: d["days"] for d in C["city_length"]}
    E = set()
    fl = C["_prompt"].split("direct flights:")[1].split("\n\n")[0].strip().rstrip(".")
    for part in fl.split(", "):
        part = part.strip()
        if part.startswith("from "):
            a, b = part[5:].split(" to "); E.add((a.strip(), b.strip()))
        else:
            a, b = part.split(" and "); E.add((a.strip(), b.strip())); E.add((b.strip(), a.strip()))
    R = collections.defaultdict(list)
    for r in C["city_day_ranges"]: R[r["city"]].append((r["start"], r["end"]))
    sols = []
    def ok(city, s, e):
        for a, b in R[city]:
            if mode == "cover" and not (s <= a and b <= e): return False
            if mode == "overlap" and (e < a or s > b): return False
        return True
    def dfs(path, day, left):
        if not left:
            if day == C["trip_length"]: sols.append(list(path))
            return
        for x in left:
            if path and (path[-1][0], x) not in E: continue
            s = day if path else 1; e = s + L[x] - 1
            if e > C["trip_length"] or not ok(x, s, e): continue
            path.append((x, s, e)); dfs(path, e, left - {x}); path.pop()
    dfs([], 1, frozenset(L)); return sols
H = collections.Counter()
for k, v in c.items():
    C = ast.literal_eval(v["constraints"]) if isinstance(v["constraints"], str) else v["constraints"]
    C["_prompt"] = v["prompt_0shot"]
    # directed? prompt says "from A to B" for some edges
    for mode in ["cover", "overlap"]:
        n = len(count(C, mode)); H[(mode, min(n, 3))] += 1
print(sorted(H.items()))
