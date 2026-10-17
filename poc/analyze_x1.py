"""X1 (docs/prereg/PREREG_X1.md): text vs program vs thinking on MATH-500 + AIME 2024/25; the agreement gate (text == program -> accept,
else thinking), its leak (wrong share among agreeing pairs) and the text-text control (seed s vs seed s+1).
usage: python analyze_x1.py [model ...]"""
import json, os, statistics as st, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_math import RES, same  # noqa: E402


def load(m, mode, sd):
    if mode == "think" and os.environ.get("X1_THINK_TAG"):   # X1-Q36R: the thinking arm from another run (e.g. q36c), text / program from m
        m = os.environ["X1_THINK_TAG"]
    f = f"{RES}/math_{m}_{mode}_s{sd}.jsonl"
    return {r["id"]: r for r in map(json.loads, open(f))} if os.path.exists(f) else None


for m in sys.argv[1:] or ["q32b", "oss20", "q36"]:
    D = {(mode, sd): load(m, mode, sd) for mode in ("text", "prog", "think") for sd in (1, 2, 3)}
    if any(v is None for v in D.values()):
        print(m, "incomplete:", [k for k, v in D.items() if v is None]); continue
    ids = sorted(D[("text", 1)])
    grp = {"MATH-500": [i for i in ids if D[("text", 1)][i]["src"] == "math500"], "AIME": [i for i in ids if D[("text", 1)][i]["src"] != "math500"]}
    print(f"\n=== {m}")
    for mode in ("text", "prog", "think"):
        rows = [D[(mode, sd)][i] for sd in (1, 2, 3) for i in ids]
        t = sorted(r["out_tokens"] or 0 for r in rows)
        extra = (f", program status {dict(Counter(r.get('status') for r in rows).most_common(4))}" if mode == "prog" else "")
        print(f"  {mode:5s}: " + " | ".join(f"{g} {100 * sum(D[(mode, sd)][i]['correct'] for sd in (1, 2, 3) for i in I) / (3 * len(I)):.1f}%" for g, I in grp.items())
              + f" | tokens mean {st.mean(t):.0f}, p90 {t[int(.9 * len(t))]}, caps {sum(r.get('finish') == 'length' for r in rows)}{extra}")
    for g, I in grp.items():
        res = {k: [0, 0, 0] for k in ("always text", "always thinking", "gate text==program -> thinking", "gate text==text(next seed) -> thinking")}
        leak = {"text-program": [0, 0], "text-text": [0, 0]}
        for sd in (1, 2, 3):
            sd2 = sd % 3 + 1
            for i in I:
                T, Pg, K, T2 = D[("text", sd)][i], D[("prog", sd)][i], D[("think", sd)][i], D[("text", sd2)][i]
                tok = lambda *rs: sum(r["out_tokens"] or 0 for r in rs)
                for k, ok, tk in (("always text", T["correct"], tok(T)), ("always thinking", K["correct"], tok(K))):
                    res[k][0] += ok; res[k][1] += tk; res[k][2] += 1
                ag = bool(T["cands"]) and bool(Pg["cands"]) and same(T["cands"], Pg["cands"])
                res["gate text==program -> thinking"][0] += T["correct"] if ag else K["correct"]
                res["gate text==program -> thinking"][1] += tok(T, Pg) + (0 if ag else tok(K)); res["gate text==program -> thinking"][2] += 1
                if ag:
                    leak["text-program"][0] += 1; leak["text-program"][1] += not T["correct"]
                ag2 = bool(T["cands"]) and bool(T2["cands"]) and same(T["cands"], T2["cands"])
                res["gate text==text(next seed) -> thinking"][0] += T["correct"] if ag2 else K["correct"]
                res["gate text==text(next seed) -> thinking"][1] += tok(T, T2) + (0 if ag2 else tok(K)); res["gate text==text(next seed) -> thinking"][2] += 1
                if ag2:
                    leak["text-text"][0] += 1; leak["text-text"][1] += not T["correct"]
        print(f"  {g}: " + " | ".join(f"{k} {100 * a / n:.1f}% @ {t / n / 1000:.1f}k" for k, (a, t, n) in res.items()))
        print(f"  {g} leak: " + " | ".join(f"{k}: agree {a}, wrong among agreeing {w} ({100 * w / max(1, a):.1f}%)" for k, (a, w) in leak.items()))
