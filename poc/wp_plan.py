"""PREREG_DIFF addendum WP-PLAN (2026-11-24): separate-and-ask on optimization word problems with the candidates' own plans.
Pool: a model's freev programs (they print the decision variables as JSON, then the objective). Where the pool's objective values
disagree, the oracle does not judge formulations; it checks each candidate's PLAN against the problem text: is every stated constraint
met, and what is the plan's objective under the text. Any plan that truly satisfies the text bounds the true optimum (>= for max,
<= for min), so among candidates whose plan the oracle finds feasible and whose claimed value matches the oracle's evaluation, the best
value is chosen; otherwise the plurality stands. Baseline JUDGE: the oracle sees the two most frequent candidates' programs and picks one.
usage: POC_BASE_URL=... python wp_plan.py run <pooltag> <set> <plan|judge>   |   python wp_plan.py score <pooltag> <set>"""
import glob, json, os, random, re, sys, zlib
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R3 = f"{ROOT}/results/x3"
OUT = f"{ROOT}/results/x44"
PLAN = ("{q}\n\nA candidate solution (values of the decision variables) is:\n```json\n{plan}\n```\nCheck this candidate against the problem "
        "statement only (do not re-solve the problem). Go through every condition the statement imposes and check it with these values; "
        "then compute the objective the statement defines for these values. Variable names are the candidate's own; map them to the "
        "quantities they clearly stand for, and treat a quantity the candidate leaves out as a failed check.\nEnd with three lines:\n"
        "SENSE: MAX or MIN (what the problem optimizes)\nFEASIBLE: YES or NO\n\\boxed{{objective value of this candidate}}")
JUDGE = ("{q}\n\nTwo programs were written for this problem and they disagree.\nProgram 1 printed {v1}:\n```python\n{c1}\n```\nProgram 2 "
         "printed {v2}:\n```python\n{c2}\n```\nCompare each with the problem statement and decide which one models it correctly. "
         "End with \\boxed{{1}} or \\boxed{{2}}.")


CDIS = ("{q}\n\nTwo programs were written for this problem and they disagree.\nProgram 1 printed {v1}:\n```python\n{c1}\n```\nProgram 2 "
        "printed {v2}:\n```python\n{c2}\n```\nDo not judge the programs as a whole. List every constraint, bound, variable domain or "
        "objective term that one program has and the other lacks or states differently. For each difference, quote the sentence of the "
        "problem that settles it and say which program the text supports. The program the text contradicts on any difference loses. "
        "End with \\boxed{{1}} or \\boxed{{2}}.")


def pool(tag, st):
    import run_nlopt as RN
    os.environ["NLOPT_SET"] = st
    P = {p["id"]: p for p in RN.problems()}
    G = defaultdict(list)
    for f in sorted(glob.glob(f"{R3}/opt_{tag}_{st}_freev_s*.jsonl")):
        for l in open(f):
            r = json.loads(l)
            if r["id"] in P:
                G[r["id"]].append(r)
    return P, G, RN


def val(r):
    try:
        v = float(r.get("pred"))
        return v if v == v else None
    except (TypeError, ValueError):
        return None


def classes(rows):
    """objective classes (relative 1e-6), most frequent first; each with its rows"""
    C = []
    for r in rows:
        v = val(r)
        if v is None:
            continue
        for c in C:
            if abs(c["v"] - v) <= 1e-6 * max(1.0, abs(v)):
                c["rows"].append(r); break
        else:
            C.append({"v": v, "rows": [r]})
    return sorted(C, key=lambda c: -len(c["rows"]))


def run(tag, st, arm):
    from llm import chat
    P, G, RN = pool(tag, st)
    out = f"{OUT}/wpplan_{tag}_{st}_{arm}.jsonl"
    done = {json.loads(l)["id"] for l in open(out)} if os.path.exists(out) else set()
    todo = [i for i, rows in G.items() if len(classes(rows)) >= 2 and i not in done]

    def one(i):
        C = classes(G[i]); q = P[i]["q"]; res = {"id": i, "tok": 0}
        if arm == "plan":
            checks = []
            for k, c in enumerate(C[:3]):
                r = next((x for x in c["rows"] if x.get("solution")), None)
                if r is None:
                    checks.append({"v": c["v"], "plan": False}); continue
                o = chat(PLAN.format(q=q, plan=r["solution"][:4000]), think=True, max_tokens=12000, temperature=0.7,
                         seed=4000 + zlib.crc32(f"{i}|{k}".encode()) % 997)
                t = o.get("text") or ""; res["tok"] += o.get("out_tokens") or 0
                b = re.findall(r"\\boxed\{([^{}]*)\}", t); s = re.findall(r"SENSE:\s*\**\s*(MAX|MIN)", t, re.I); f = re.findall(r"FEASIBLE:\s*\**\s*(YES|NO)", t, re.I)
                checks.append({"v": c["v"], "plan": True, "obj": RN.value_of(b[-1]) if b else None, "sense": s[-1].upper() if s else None,
                               "feasible": (f[-1].upper() == "YES") if f else None})
            res["checks"] = checks
        else:   # judge or cdis
            a, b = C[0], C[1]
            ra = next((x for x in a["rows"] if x.get("code")), a["rows"][0]); rb = next((x for x in b["rows"] if x.get("code")), b["rows"][0])
            o = chat((CDIS if arm == "cdis" else JUDGE).format(q=q, v1=a["v"], c1=(ra.get("code") or "")[:6000], v2=b["v"], c2=(rb.get("code") or "")[:6000]), think=True,
                     max_tokens=12000, temperature=0.7, seed=5000 + zlib.crc32(i.encode()) % 997)
            t = o.get("text") or ""; res["tok"] = o.get("out_tokens") or 0
            m = re.findall(r"\\boxed\{\s*([12])\s*\}", t); res["pick"] = int(m[-1]) if m else None
        return res
    with ThreadPoolExecutor(32) as ex, open(out, "a") as f:
        for z in ex.map(one, todo):
            f.write(json.dumps(z) + "\n"); f.flush()


def score(tag, st):
    P, G, RN = pool(tag, st)
    U = lambda ok, t: 100 * ok - 0.5 * t / 1000
    Z = {a: ({json.loads(l)["id"]: json.loads(l) for l in open(f"{OUT}/wpplan_{tag}_{st}_{a}.jsonl")}
             if os.path.exists(f"{OUT}/wpplan_{tag}_{st}_{a}.jsonl") else {}) for a in ("plan", "judge", "cdis")}
    right = lambda i, v: v is not None and RN.correct(v, P[i]["gold"])
    arms = defaultdict(dict); ids = sorted(G)
    for i in ids:
        rows = G[i]; C = classes(rows); tp = sum(int(r.get("out_tokens") or 0) for r in rows)
        arms["single (seed mean)"][i] = sum(U(right(i, val(r)), int(r.get("out_tokens") or 0)) for r in rows) / len(rows)
        plur = C[0]["v"] if C else None
        arms["plurality"][i] = U(right(i, plur), tp)
        arms["some right (bound)"][i] = U(any(right(i, val(r)) for r in rows), tp)
        z = Z["plan"].get(i)
        pick = plur; extra = 0
        if z:
            extra = z["tok"]; ok = [c for c in z["checks"] if c.get("plan") and c.get("feasible") and c.get("obj") is not None
                                     and abs(c["obj"] - c["v"]) <= max(1e-2, 1e-3 * abs(c["v"]))]
            sense = Counter(c["sense"] for c in z["checks"] if c.get("sense")).most_common(1)
            if ok and sense:
                pick = (max if sense[0][0] == "MAX" else min)(ok, key=lambda c: c["v"])["v"]
        arms["PLAN (ours)"][i] = U(right(i, pick), tp + extra)
        z = Z["judge"].get(i)
        jp = plur
        if z and z.get("pick") in (1, 2) and len(C) >= 2:
            jp = C[z["pick"] - 1]["v"]
        arms["JUDGE"][i] = U(right(i, jp), tp + (z["tok"] if z else 0))
        z = Z["cdis"].get(i); cp = plur
        if z and z.get("pick") in (1, 2) and len(C) >= 2:
            cp = C[z["pick"] - 1]["v"]
        arms["CDIS"][i] = U(right(i, cp), tp + (z["tok"] if z else 0))
    for a, d in arms.items():
        print(f"{st} {a:20s} n={len(d)} utility {sum(d.values())/len(d):.2f}")
    for a, b in (("PLAN (ours)", "plurality"), ("PLAN (ours)", "JUDGE"), ("JUDGE", "plurality"), ("CDIS", "plurality"), ("CDIS", "JUDGE")):
        d = [arms[a][i] - arms[b][i] for i in ids]; rng = random.Random(1)
        bs = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(4000))
        print(f"{st} {a} - {b}: {sum(d)/len(d):+.2f} [{bs[100]:+.2f}, {bs[3899]:+.2f}] p={(sum(x <= 0 for x in bs)+1)/4001:.4f}")
    print(f"{st}: disputed problems {sum(len(classes(G[i])) >= 2 for i in ids)}, plan checks {len(Z['plan'])}, judge calls {len(Z['judge'])}")


if __name__ == "__main__":
    run(sys.argv[2], sys.argv[3], sys.argv[4]) if sys.argv[1] == "run" else score(sys.argv[2], sys.argv[3])
