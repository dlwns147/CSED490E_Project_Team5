"""MODEL (docs/prereg/PREREG_MODEL.md): when does "fact first, think only where the check fails" win, and can k labelled items pick
the right policy for a new cell? Offline on stored rows (X6 word problems; U1 geometry / optimization suites).
Per item of a cell: cheap fact program (correct?, passes its label-free check?, tokens, answer), a second cheap sample (answer, check),
and a thinking run (correct?, tokens). Policies: CHEAP, FF, FFR (two cheap samples must agree), THINK.
usage: python analyze_policy_model.py"""
import json, os, random, sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_argv, sys.argv = sys.argv, sys.argv[:1]   # analyze_u1 -> analyze_n12 read sys.argv at import
import analyze_u1 as U  # noqa: E402
sys.argv = _argv

X3 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "x3")
MODELS = ["q17", "q4b", "q8b", "q14a", "oss20", "q32b", "q36"]


def x6_rows(m, arm, s):
    tag = "q36d" if (m == "q36" and arm == "thinkf") else m
    f = f"{X3}/opt_{tag}_{arm}_s{s}.jsonl"
    return {r["id"]: r for r in map(json.loads, open(f))} if os.path.exists(f) else None


def same(a, b):
    try:
        return abs(float(a) - float(b)) <= 1e-6 * max(1.0, abs(float(b)))
    except (TypeError, ValueError):
        return a is not None and str(a).strip().lower() == str(b).strip().lower()


def x6_cells():
    for m in MODELS:
        for s in (1, 2, 3):
            F, F2, T = x6_rows(m, "mipf", s), x6_rows(m, "mipf", s % 3 + 1), x6_rows(m, "thinkf", s)
            if not (F and F2 and T):
                continue
            items = []
            for i, f in F.items():
                if i not in T or i not in F2:
                    continue
                pf = f["status"] == "ok" and f.get("pred") is not None
                p2 = F2[i]["status"] == "ok" and F2[i].get("pred") is not None
                items.append(dict(f_ok=f["correct"], f_pass=pf, f_tok=f["out_tokens"] or 0, agree=pf and p2 and same(f["pred"], F2[i]["pred"]),
                                  f2_tok=F2[i]["out_tokens"] or 0, t_ok=T[i]["correct"], t_tok=T[i]["out_tokens"] or 0))
            yield (f"X6 {m} s{s}", items)


def u1_cells():
    for m in MODELS:
        for dom in ("geo", "co"):
            for s in (1, 2, 3):
                os.environ["U1_CURE_SEED"] = "" if s == 1 else str(s)
                if m == "q36":
                    os.environ["U1_THINK_M"] = "q36d"
                else:
                    os.environ.pop("U1_THINK_M", None)
                F, T = U.load(m, dom, "fact_s1"), U.load(m, dom, "think_s1")
                os.environ["U1_CURE_SEED"] = str(s % 3 + 1) if s % 3 + 1 != 1 else ""
                F2 = U.load(m, dom, "fact_s1")
                if not (F and T and F2):
                    continue
                items = []
                for k, f in F.items():
                    if k not in T or k not in F2:
                        continue
                    pf, p2 = U.check(dom, f), U.check(dom, F2[k])
                    a1, a2 = U.answer(dom, f), U.answer(dom, F2[k])
                    items.append(dict(f_ok=U.ok(dom, f), f_pass=pf, f_tok=f.get("out_tokens") or 0, agree=pf and p2 and a1 is not None and a1 == a2,
                                      f2_tok=F2[k].get("out_tokens") or 0, t_ok=U.ok(dom, T[k]), t_tok=T[k].get("out_tokens") or 0))
                yield (f"U1 {m} {dom} s{s}", items)
    os.environ.pop("U1_CURE_SEED", None); os.environ.pop("U1_THINK_M", None)


def policies(items):
    """accuracy (%) and mean output tokens (k) per policy"""
    n = len(items); out = {}
    acc = {"CHEAP": 0, "FF": 0, "FFR": 0, "THINK": 0}; tok = dict.fromkeys(acc, 0)
    for it in items:
        acc["CHEAP"] += it["f_ok"]; tok["CHEAP"] += it["f_tok"]
        acc["THINK"] += it["t_ok"]; tok["THINK"] += it["t_tok"]
        acc["FF"] += it["f_ok"] if it["f_pass"] else it["t_ok"]; tok["FF"] += it["f_tok"] + (0 if it["f_pass"] else it["t_tok"])
        acc["FFR"] += it["f_ok"] if it["agree"] else it["t_ok"]; tok["FFR"] += it["f_tok"] + it["f2_tok"] + (0 if it["agree"] else it["t_tok"])
    for p in acc:
        out[p] = (100 * acc[p] / n, tok[p] / n / 1000)
    return out


def decomposition(items):
    n = len(items); passed = [it for it in items if it["f_pass"]]
    if not passed:
        return 0.0
    pp = len(passed) / n
    return 100 * pp * (sum(it["f_ok"] for it in passed) - sum(it["t_ok"] for it in passed)) / len(passed)


if __name__ == "__main__":
    cells = [c for c in list(x6_cells()) + list(u1_cells()) if len(c[1]) >= 50]
    print(f"{len(cells)} cells")
    worst = 0
    for name, items in cells:
        P = policies(items); d = decomposition(items)
        worst = max(worst, abs((P["FF"][0] - P["THINK"][0]) - d))
    print(f"MODEL-P1: max |(FF - THINK) - decomposition| over cells = {worst:.6f} points")
    rng = random.Random(0)
    for lam in (0.0, 0.5, 2.0):
        util = lambda P: {p: a - lam * t for p, (a, t) in P.items()}
        best_count = defaultdict(int); reg = defaultdict(list)
        for name, items in cells:
            U_full = util(policies(items)); best = max(U_full, key=U_full.get); best_count[best] += 1
            for k in (10, 30, 100):
                r = []
                for _ in range(1000):
                    pilot = rng.sample(items, min(k, len(items)))
                    U_p = util(policies(pilot)); pick = max(U_p, key=U_p.get)
                    r.append(U_full[best] - U_full[pick])
                reg[k].append(sum(r) / len(r))
        fixed = {p: sum(max(util(policies(it)).values()) - util(policies(it))[p] for _, it in cells) / len(cells) for p in ("CHEAP", "FF", "FFR", "THINK")}
        print(f"lambda {lam}: best policy counts {dict(best_count)} | mean regret of a pilot pick: "
              + ", ".join(f"k={k} {sum(v) / len(v):.2f}" for k, v in reg.items())
              + " | regret of always using one policy: " + ", ".join(f"{p} {v:.2f}" for p, v in fixed.items()))
    print("\nper cell (lambda 0.5): CHEAP / FF / FFR / THINK accuracy @ tokens(k)")
    for name, items in cells:
        P = policies(items)
        print(f"  {name:22} " + " | ".join(f"{p} {a:.1f}@{t:.1f}" for p, (a, t) in P.items()))
