"""ADAPT (docs/prereg/PREREG_X1.md): AdaptThink-7B (trained when-to-think switch) vs our label-free gate on its base model
DeepSeek-R1-Distill-Qwen-7B, and the two combined. Per group (MATH-500 / AIME 24+25), mean over seeds 1-3: accuracy @ mean output tokens.
  r1d7 text / prog / think   : the base model, NoThinking text, NoThinking program, thinking
  GATE(r1d7)                 : r1d7 text == r1d7 program -> accept, else r1d7 thinking (tokens: text + program [+ thinking])
  ADAPT                      : AdaptThink as released (it chooses), its NoThinking share
  ADAPT+CHECK                : AdaptThink; when it skipped thinking, also its NoThinking program; disagree -> r1d7 thinking
  GATE(adt7)                 : adt7 text == adt7 program -> accept, else AdaptThink as released
usage: python analyze_adapt.py"""
import json, os, sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_math import RES, same  # noqa: E402


def load(tag, mode, sd):
    f = f"{RES}/math_{tag}_{mode}_s{sd}.jsonl"
    return {r["id"]: r for r in map(json.loads, open(f))} if os.path.exists(f) else None


D = {(t, m, s): load(t, m, s) for t in ("r1d7", "adt7") for m in ("text", "prog", "think") for s in (1, 2, 3)}
miss = [k for k, v in D.items() if v is None]
if miss:
    sys.exit(f"incomplete: {miss}")
ids = sorted(D[("r1d7", "text", 1)])
src = {i: D[("r1d7", "text", 1)][i]["src"] for i in ids}
lvl = {i: D[("r1d7", "text", 1)][i].get("level") for i in ids}
tok = lambda *rs: sum(r["out_tokens"] or 0 for r in rs)
for g, I in (("MATH-500", [i for i in ids if src[i] == "math500"]), ("AIME", [i for i in ids if src[i] != "math500"])):
    acc = defaultdict(lambda: [0, 0, 0]); nt = [0, 0]; by_lvl = defaultdict(lambda: [0, 0, 0]); leak = [0, 0]
    for sd in (1, 2, 3):
        for i in I:
            rt, rp, rk = (D[("r1d7", m, sd)][i] for m in ("text", "prog", "think"))
            at, ap, ak = (D[("adt7", m, sd)][i] for m in ("text", "prog", "think"))
            agree = bool(rt["cands"]) and bool(rp["cands"]) and same(rt["cands"], rp["cands"])
            if agree:
                leak[0] += 1; leak[1] += not rt["correct"]
            pol = {"r1d7 text": (rt["correct"], tok(rt)), "r1d7 prog": (rp["correct"], tok(rp)), "r1d7 think": (rk["correct"], tok(rk)),
                   "GATE(r1d7)": ((rt if agree else rk)["correct"], tok(rt, rp) + (0 if agree else tok(rk))),
                   "ADAPT": (ak["correct"], tok(ak))}
            if ak["nothink"]:
                ok_ = bool(ak["cands"]) and bool(ap["cands"]) and same(ak["cands"], ap["cands"])
                pol["ADAPT+CHECK"] = ((ak if ok_ else rk)["correct"], tok(ak, ap) + (0 if ok_ else tok(rk)))
            else:
                pol["ADAPT+CHECK"] = pol["ADAPT"]
            agree_a = bool(at["cands"]) and bool(ap["cands"]) and same(at["cands"], ap["cands"])
            pol["GATE(adt7)"] = ((at if agree_a else ak)["correct"], tok(at, ap) + (0 if agree_a else tok(ak)))
            for k, (c, t) in pol.items():
                acc[k][0] += c; acc[k][1] += t; acc[k][2] += 1
            nt[0] += ak["nothink"]; nt[1] += 1
            b = by_lvl[lvl[i]]; b[0] += ak["nothink"]; b[1] += ak["correct"]; b[2] += 1
    print(f"\n=== {g} ({len(I)} problems x 3 seeds)")
    for k, (c, t, n) in acc.items():
        print(f"  {k:12s} {100 * c / n:5.1f}% @ {t / n / 1000:.2f}k")
    print(f"  AdaptThink NoThinking share {100 * nt[0] / nt[1]:.1f}% | r1d7 text==program agree {leak[0]}, wrong among agreeing {leak[1]} "
          f"({100 * leak[1] / max(1, leak[0]):.1f}%)")
    if g == "MATH-500":
        print("  AdaptThink by level (NoThinking share, accuracy): " + ", ".join(
            f"L{l} {100 * b[0] / b[2]:.0f}% / {100 * b[1] / b[2]:.0f}%" for l, b in sorted(by_lvl.items(), key=lambda x: str(x[0]))))
