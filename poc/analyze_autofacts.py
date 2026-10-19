"""X6-AUTO / VER / VER2 (docs/prereg/PREREG_X3.md): hand-written vs automatic facts in the fact-first pipeline, with the 'runs' check (FF)
and the 'two cheap programs agree' check (FFR). usage: python analyze_autofacts.py q8b q32b"""
import json, os, sys

X3 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "x3")
FACTS = {"none": ("mip", "think"), "snippet (hand)": ("mipf", "thinkf"), "name list (auto)": ("mipa", "thinka"),
         "similar example (auto)": ("mipv", "thinkv"), "shortest program (auto)": ("mips", "thinks")}


def rows(m, a, s):
    if m == "q36":   # Qwen3.6: cheap no-fact / snippet arms under q36, every arm run with the 80k thinking setup under q36d
        m = "q36" if a in ("mip", "mipf") else "q36d"
    f = f"{X3}/opt_{m}_{a}_s{s}.jsonl"
    return {r["id"]: r for r in map(json.loads, open(f))} if os.path.exists(f) else None


def same(a, b):
    try:
        return abs(float(a) - float(b)) <= 1e-6 * max(1.0, abs(float(b)))
    except (TypeError, ValueError):
        return False


runs = lambda r: r["status"] == "ok" and r.get("pred") is not None
for m in sys.argv[1:] or ["q8b", "q32b"]:
    print(f"=== {m}: accuracy @ output tokens per item (345 problems x 3 seeds)")
    for name, (c, t) in FACTS.items():
        cell = {"CHEAP": [0, 0], "FF": [0, 0], "FFR": [0, 0], "THINK": [0, 0]}; n = 0; ok = True
        for s in (1, 2, 3):
            C, C2, T = rows(m, c, s), rows(m, c, s % 3 + 1), rows(m, t, s)
            if not (C and C2 and T) or min(len(C), len(C2), len(T)) < 345:
                ok = False; break
            for i, r in C.items():
                n += 1; tr = T[i]; r2 = C2[i]; tc, tt = r["out_tokens"] or 0, tr["out_tokens"] or 0
                cell["CHEAP"][0] += r["correct"]; cell["CHEAP"][1] += tc
                cell["THINK"][0] += tr["correct"]; cell["THINK"][1] += tt
                p = runs(r); cell["FF"][0] += r["correct"] if p else tr["correct"]; cell["FF"][1] += tc + (0 if p else tt)
                ag = p and runs(r2) and same(r["pred"], r2["pred"])
                cell["FFR"][0] += r["correct"] if ag else tr["correct"]; cell["FFR"][1] += tc + (r2["out_tokens"] or 0) + (0 if ag else tt)
        if not ok:
            print(f"  {name:26} incomplete"); continue
        print(f"  {name:26} " + " | ".join(f"{k} {100 * a / n:.1f}%@{t / n / 1000:.1f}k" for k, (a, t) in cell.items()))
