"""CROSS, headroom (descriptive, 2026-11-25): do two different families complement each other more than two programs of one family?
On the 12 word-problem sets: A = gpt-oss-120b one program (corrected environment, seed 1), B = OptiMind-SFT (seed 1), A2 = gpt-oss-120b seed 2 where stored.
Reports coverage (either right), agreement rate and its precision, and who is right on disagreements. Labels are used: this only says whether a selector has room."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wp_plan as W
L = lambda f: {json.loads(l)["id"]: json.loads(l) for l in open(f"{W.R3}/{f}")} if os.path.exists(f"{W.R3}/{f}") else None
num = lambda r: r["pred"] if isinstance(r["pred"], float) else None
tot = {}
for st in ("optc", "indc", "mamoc", "optnew", "optmath", "omtf", "omtf2", "bwor", "logior", "optibench", "easyc", "nl4c"):
    os.environ["NLOPT_SET"] = st
    import run_nlopt as RN
    ids = [p["id"] for p in RN.problems(st)]
    A, A2, B = L(f"opt_oss120_{st}_thinkfreenE_s1.jsonl"), L(f"opt_oss120_{st}_thinkfreenE_s2.jsonl"), L(f"opt_optimind_{st}_gurobi_s1.jsonl")
    if not (A and B):
        print(st, "missing"); continue

    def stats(X, Y):
        c = dict(either=0, agree=0, agree_right=0, dis=0, x_only=0, y_only=0, neither=0)
        for i in ids:
            x, y = X[i], Y[i]; cx, cy = bool(x["correct"]), bool(y["correct"])
            c["either"] += cx or cy
            same = (x["pred"] == "NBS" and y["pred"] == "NBS") or (num(x) is not None and num(y) is not None and RN.correct(num(x), str(num(y))))
            if same:
                c["agree"] += 1; c["agree_right"] += cx
            else:
                c["dis"] += 1; c["x_only"] += cx and not cy; c["y_only"] += cy and not cx; c["neither"] += not cx and not cy
        return c
    n = len(ids); a = sum(bool(A[i]["correct"]) for i in ids) / n; b = sum(bool(B[i]["correct"]) for i in ids) / n
    s = stats(A, B); s2 = stats(A, A2) if A2 else None
    print(f"{st:9s} n={n} A {100*a:.1f} B {100*b:.1f} | A+B either {100*s['either']/n:.1f}  agree {100*s['agree']/n:.0f}% (right {100*s['agree_right']/max(1,s['agree']):.0f}%)  disagree {s['dis']}: A only {s['x_only']}, B only {s['y_only']}, neither {s['neither']}"
          + (f" | A+A2 either {100*s2['either']/n:.1f}  agree {100*s2['agree']/n:.0f}% (right {100*s2['agree_right']/max(1,s2['agree']):.0f}%)" if s2 else ""))
    for k in s:
        tot.setdefault(k, 0); tot[k] += s[k]
    tot["n"] = tot.get("n", 0) + n; tot["a"] = tot.get("a", 0) + a * n; tot["b"] = tot.get("b", 0) + b * n
n = tot["n"]
print(f"pooled n={n}: A {100*tot['a']/n:.1f}  B {100*tot['b']/n:.1f}  either {100*tot['either']/n:.1f}  agree {100*tot['agree']/n:.0f}% (right {100*tot['agree_right']/tot['agree']:.1f}%)  disagree {tot['dis']}: A only {tot['x_only']}, B only {tot['y_only']}, neither {tot['neither']}")
