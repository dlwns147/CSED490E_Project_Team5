"""Which cheap fix (docs/FINDINGS.md 2026-10-20): does a label-free census of the FIRST programs' failures predict whether a fact pays?
x = share of the no-fact programs that crash with a usage exception (AttributeError / ModuleNotFoundError / ImportError: the runtime's own
class, no text rules); y = accuracy gain of the cheap program when the fact is added (hand snippet / usage card or the label-free library).
One point per (benchmark, model, fact); all available seeds pooled. usage: python analyze_which_fix.py"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_nlopt import RES  # noqa: E402

USAGE = re.compile(r"^(AttributeError|ModuleNotFoundError|ImportError)\b", re.M)


def load(tag, arm):
    R = []
    for s in (1, 2, 3):
        f = f"{RES}/opt_{tag}_{arm}_s{s}.jsonl"
        if os.path.exists(f):
            R += [json.loads(l) for l in open(f) if l.strip()]
    return R


acc = lambda R: 100 * sum(r["correct"] for r in R) / len(R)
usage = lambda R: 100 * sum(r["status"] == "re" and bool(USAGE.search(r.get("err") or "")) for r in R) / len(R)
# broad census (added 2026-10-20 after the Qwen3.6 raw programs: strong models catch their own exceptions and print 'No Best Solution'):
# share of first programs that fail the free check at all (crash, no value, or 'No Best Solution')
fails = lambda R: 100 * sum(not (r["status"] == "ok" and r.get("pred") not in (None, "NBS")) for r in R) / len(R)
rows = []
for m in ("oss20", "q14a", "q8b", "q32b", "q4b", "q17", "oss120", "q36"):
    for bench, tag, base, facts in (("NL4OPT+IndustryOR", m, "mip", ("mipf",)), ("MAMO", f"{m}_mamo", "mip", ("mips", "formx")),
                                    ("OptMATH", f"{m}_optmath", "mip", ("mips", "formx")), ("OptiBench", f"{m}_optibench", "free", ("freef", "formx"))):
        B = load(tag, base)
        if not B:
            continue
        for fct in facts:
            Fx = load(tag, fct)
            if Fx:
                rows.append((bench, m, fct, usage(B), acc(B), acc(Fx) - acc(B), fails(B)))
for r in rows:
    print(f"{r[0]:18s} {r[1]:5s} {r[2]:6s} usage crashes in first programs {r[3]:5.1f}% | fail the check {r[6]:5.1f}% | no fact {r[4]:5.1f}% | gain {r[5]:+5.1f}")
xs, ys = [r[3] for r in rows], [r[5] for r in rows]
n = len(xs); mx, my = sum(xs) / n, sum(ys) / n
cov = sum((a - mx) * (b - my) for a, b in zip(xs, ys)); vx = sum((a - mx) ** 2 for a in xs); vy = sum((b - my) ** 2 for b in ys)
print(f"n = {n}, Pearson r = {cov / (vx * vy) ** .5:.2f}; gain when usage crashes >= 5%: mean {sum(y for x, y in zip(xs, ys) if x >= 5) / max(1, sum(x >= 5 for x in xs)):+.1f} "
      f"(n={sum(x >= 5 for x in xs)}), < 5%: mean {sum(y for x, y in zip(xs, ys) if x < 5) / max(1, sum(x < 5 for x in xs)):+.1f} (n={sum(x < 5 for x in xs)})")

x2 = [r[6] for r in rows]; m2 = sum(x2) / n
c2 = sum((a - m2) * (b - my) for a, b in zip(x2, ys)); v2 = sum((a - m2) ** 2 for a in x2)
print(f"broad census (fail the check): Pearson r = {c2 / (v2 * vy) ** .5:.2f}")
