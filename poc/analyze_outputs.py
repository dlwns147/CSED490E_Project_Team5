"""Beyond accuracy: what do the generated programs look like? (offline, stored code)
For each condition: code length (tokens ~ regex word/symbol count), lines, number of function definitions, branch count (if/elif),
copied helpers, special-case handling (collinear/duplicate/degenerate code), and the hull algorithm family (monotone chain / Graham-polar / gift wrapping /
other). Compared between K=0 and K=8 (and thinking), and between passing and failing programs.
usage: analyze_outputs.py"""
import json, os, re, sys
from collections import Counter
import numpy as np

R = "/NAS/SJ/POSTECH/nlp/results"
HELPERS = ["orient", "on_segment", "segments_intersect", "point_in_polygon", "dist2", "bbox", "collinear", "polar_sort",
           "is_convex", "polygon_area2", "convex_hull", "closest_pair_sq"]
TOK = re.compile(r"[A-Za-z_]\w*|\d+|\S")


def feats(code):
    code = code or ""
    body = re.sub(r"#[^\n]*", "", code)
    defs = re.findall(r"^\s*def (\w+)\(", body, re.M)
    copied = [h for h in HELPERS if h in defs]
    special = len(re.findall(r"collinear|duplicate|degenerate|on_segment|== 0\b|same point|coincid", body))
    if re.search(r"lower|upper", body) and re.search(r"sorted\(|\.sort\(", body):
        algo = "monotone chain"
    elif re.search(r"polar_sort|atan2|angle", body):
        algo = "Graham / polar sort"
    elif re.search(r"gift|jarvis|next_point|wrap", body, re.I):
        algo = "gift wrapping"
    else:
        algo = "other"
    return {"tokens": len(TOK.findall(body)), "lines": body.count("\n") + 1, "defs": len(defs), "copied": len(copied),
            "branches": len(re.findall(r"\b(if|elif)\b", body)), "special": special, "algo": algo}


def load(tag):
    f = f"{R}/geocross_{tag}.jsonl"
    return [json.loads(l) for l in open(f)] if os.path.exists(f) and os.path.getsize(f) else []


def summary(rows, label):
    if not rows:
        return
    F = [feats(r["code"]) | {"ok": r["class"] == "correct_all", "task": r["task"]} for r in rows if r.get("code")]
    m = lambda k, sel=None: np.mean([f[k] for f in F if sel is None or sel(f)])
    hull = [f for f in F if f["task"] == "hull"]
    algos = Counter(f["algo"] for f in hull)
    print(f"{label:34s} n={len(F):4d} acc {100*m('ok'):5.1f} | tokens {m('tokens'):5.0f} lines {m('lines'):4.0f} defs {m('defs'):.1f} "
          f"copied {m('copied'):.1f} branches {m('branches'):4.1f} special {m('special'):4.1f} | hull algo {dict(algos.most_common(3))}")
    return F


if __name__ == "__main__":
    for m in ["8b", "14b", "32b"]:
        print(f"--- Qwen3-{m}")
        a = summary(sum((load(f"F_geox{m}_dis0_t07s1") for _ in [0]), []), "K=0 (toolbox, no-think)")
        b = summary(sum((load(f"F_geox{m}_dis8_t07s{s}") for s in (1, 2, 3)), []), "K=8 (no-think, 3 seeds)")
        summary(load(f"F_geox{m}_dis8pre_t07s1"), "K=8 pre-defined helpers")
        summary(sum((load(t) for t in ([f"T_geox{m}_dis8", f"T_geox{m}_dis8_s2"] if m != "8b" else ["T_geox8b_dis8_s1", "T_geox8b_dis8_s2"])), []), "K=8 + thinking")
        if b:
            for lab, sel in [("  K=8 passing", lambda f: f["ok"]), ("  K=8 failing", lambda f: not f["ok"])]:
                S = [f for f in b if sel(f)]
                print(f"{lab:34s} n={len(S):4d} tokens {np.mean([f['tokens'] for f in S]):5.0f} branches {np.mean([f['branches'] for f in S]):4.1f} "
                      f"special {np.mean([f['special'] for f in S]):4.1f} copied {np.mean([f['copied'] for f in S]):.1f}")
