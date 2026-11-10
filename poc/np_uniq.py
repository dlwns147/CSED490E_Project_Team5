"""PREREG_NP: how many valid plans does each NaturalPlan trip allow? Enumerates city orders over the direct flights (one-way "from A to B" parsed from the
prompt, "A and B" both ways), stays of the stated lengths sharing the flight day, total length; a dated event either inside the stay ("cover") or
only overlapping it ("overlap"). usage: python3 poc/np_uniq.py <nlp_data>/naturalplan_dl/a_trip_planning_100_constraints.json
(2026-11-10: cover 95 one plan, 3 two, 2 three; overlap 36 one)."""
import json, ast, sys, collections
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
def valid_plans(path):
    """{trip id: set of valid plans, each a tuple of (city lowercased, start, end)}, "cover" reading (poc/gp_eval.py --np)"""
    out = {}
    for k, v in json.load(open(path)).items():
        C = ast.literal_eval(v["constraints"]) if isinstance(v["constraints"], str) else v["constraints"]
        C["_prompt"] = v["prompt_0shot"]
        out[k] = {tuple((x.lower(), s, e) for x, s, e in p) for p in count(C, "cover")}
    return out

def error_types(path):
    """PREREG_NPC addendum NPC-T: {trip id: f(plan) -> frozenset of the ways a plan breaks the task}: cities (wrong set), total (not day 1 to the
    last day), dayafter (every stay starts the day after the last ends), gap (other start-day mismatch), stay (length), flight (no direct flight),
    event_overlap_only (a dated event overlaps the stay but is not inside it: right under the "overlap" reading), event_miss; none if no break."""
    out = {}
    for k, v in json.load(open(path)).items():
        C = ast.literal_eval(v["constraints"]) if isinstance(v["constraints"], str) else v["constraints"]
        L = {d["city"].lower(): d["days"] for d in C["city_length"]}
        E = set(); fl = v["prompt_0shot"].split("direct flights:")[1].split("\n\n")[0].strip().rstrip(".")
        for part in fl.split(", "):
            part = part.strip()
            if part.startswith("from "):
                a, b = part[5:].split(" to "); E.add((a.strip().lower(), b.strip().lower()))
            else:
                a, b = part.split(" and "); E.add((a.strip().lower(), b.strip().lower())); E.add((b.strip().lower(), a.strip().lower()))
        R = collections.defaultdict(list)
        for r in C["city_day_ranges"]: R[r["city"].lower()].append((r["start"], r["end"]))
        def f(plan, L=L, E=E, R=R, T=C["trip_length"]):
            P = [(c.lower(), s, e) for c, s, e in plan]; t = set()
            if sorted(c for c, _, _ in P) != sorted(L): t.add("cities")
            if P[0][1] != 1 or P[-1][2] != T: t.add("total")
            if len(P) > 1 and all(P[i + 1][1] == P[i][2] + 1 for i in range(len(P) - 1)): t.add("dayafter")
            elif any(P[i + 1][1] != P[i][2] for i in range(len(P) - 1)): t.add("gap")
            if any(c in L and e - s + 1 != L[c] for c, s, e in P): t.add("stay")
            if any((P[i][0], P[i + 1][0]) not in E for i in range(len(P) - 1)): t.add("flight")
            for c, s, e in P:
                for a, b in R.get(c, []):
                    if not (s <= a and b <= e): t.add("event_overlap_only" if not (e < a or s > b) else "event_miss")
            return frozenset(t) or frozenset(["none"])
        out[k] = f
    return out


if __name__ == "__main__":
    c = json.load(open(sys.argv[1]))
    H = collections.Counter()
    for k, v in c.items():
        C = ast.literal_eval(v["constraints"]) if isinstance(v["constraints"], str) else v["constraints"]
        C["_prompt"] = v["prompt_0shot"]
        # directed? prompt says "from A to B" for some edges
        for mode in ["cover", "overlap"]:
            n = len(count(C, mode)); H[(mode, min(n, 3))] += 1
    print(sorted(H.items()))
