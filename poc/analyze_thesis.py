"""THESIS (critique point 1, docs/notes/CRITIQUE.md 10-31; offline on stored rows): one test of the project's thesis across every stored
peer-cascade cell. Thesis: a cheap answer pays only if its check accepts (quick right, default wrong) at least r* times as often as
(quick wrong, default right), r* = (n_W / n_R) (L / G) from analyze_breakeven, and the saving outweighs the two quick answers' tokens.
Cells: every generator (Qwen3-8B / 14B-AWQ / 3.5-9B, gpt-oss-20b) x every stored peer x set, on text-to-SQL (BIRD dev, fresh BIRD
train; Spider test when graded), tool calls (BFCL non-live, live) and word problems (OptiBench third, BWOR, LogiOR, OptMATH).
Per cell and per half of the questions (crc32(id) mod 2): the peer's TPR / FPR on all passing quick answers, r*, and the cascade's
gain over the default (utility, the peer's tokens counted). Out of sample: the predictor x = log2((TPR / FPR) / r*) on one half against
the gain on the other, both ways. Writes results/thesis_cells.json (one record per cell and direction) and prints the agreement.
usage: python3.11 poc/analyze_thesis.py"""
import contextlib, io, json, math, os, sys, zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_ho3 import ci  # noqa: E402
with contextlib.redirect_stdout(io.StringIO()):
    import analyze_cv as CV  # noqa: E402
    import analyze_sqlpa as Q  # noqa: E402
    import analyze_xg as XG  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENS = ("q8b", "q14a", "q35", "oss20")
PEERS = ("q35", "q8b", "q14a", "oss20")


def sql_items(n, p, suf):
    n, p = n + suf, p + suf
    GN, GP = Q.grades(n), Q.grades(p)
    if not (GN and GP) or not all(os.path.exists(f"{CV.RES}/{n}_{a}_s{s}.jsonl") for a in ("think", "sb") for s in (1, 2, 3)):
        return None
    KN, KP, out = Q.ntok(n), Q.ntok(p), []
    for (i, s), v in CV.base(n, need_r=False).items():
        x, o = GN[s].get(i, {}).get("N"), GP[s].get(i, {}).get("N")
        if x is None or o is None or i not in KN[s]:
            continue
        ps = x["chk"] == "pass"
        out.append(dict(id=i, s=s, ps=ps, ok=bool(x["ok"]), tok=KN[s][i], ptok=KP[s].get(i, 0),
                        agree=ps and o["chk"] == "pass" and o["h"] == x["h"], dok=bool(v["SB->T->T"][0]), dtok=v["SB->T->T"][1]))
    return out


def other_items(g, p, split, word):
    XG.A = g
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            return XG.tc_cell(split, p, word=word)
        except (FileNotFoundError, KeyError, TypeError):
            return None


def stats(items):
    """peer TPR / FPR on passing quick answers, r*, and the cascade's gain (utility per question-seed, points)"""
    R = [x for x in items if x["ps"] and x["ok"]]; W = [x for x in items if x["ps"] and not x["ok"]]
    d = lambda x: 100 * (float(x["ok"]) - float(x["dok"])) + XG.H.LAM * x["dtok"] / 1000
    G = sum(map(d, R)) / max(1, len(R)); L = -sum(map(d, W)) / max(1, len(W))
    tpr = sum(x["agree"] for x in R) / max(1, len(R)); fpr = sum(x["agree"] for x in W) / max(1, len(W))
    rstar = len(W) * L / max(1e-9, len(R) * G) if G > 0 else float("inf")
    gain = lambda x: (100 * float(x["ok"]) - XG.H.LAM * (x["tok"] + x["ptok"]) / 1000 if x["agree"] else
                      100 * float(x["dok"]) - XG.H.LAM * (x["tok"] + (x["ptok"] if x["ps"] else 0) + x["dtok"]) / 1000) \
        - (100 * float(x["dok"]) - XG.H.LAM * x["dtok"] / 1000)
    pq = XG.per_q(items, lambda x: gain(x) / 100)
    lo = ci(pq) if len(pq) > 1 else (0.0, 0.0, 0.0)
    x = math.log2(max(1e-6, tpr) / max(1e-6, fpr) / rstar) if rstar not in (0, float("inf")) and fpr > 0 else None
    return dict(n=len(items), tpr=tpr, fpr=fpr, rstar=rstar, x=x, gain=lo[0], lo=lo[1], hi=lo[2])


def cells():
    for g in GENS:
        for p in PEERS:
            if p == g:
                continue
            for suf, name in (("", "BIRD dev"), ("pa", "BIRD fresh"), ("sp", "Spider test")):
                yield "SQL", name, g, p, lambda g=g, p=p, suf=suf: sql_items(g, p, suf)
            for split in ("non-live", "live"):
                yield "tool calls", f"BFCL {split}", g, p, lambda g=g, p=p, split=split: other_items(g, p, split, False)
            for b in ("optibench", "bwor", "logior", "optmath"):
                yield "word problems", b, g, p, lambda g=g, p=p, b=b: other_items(g, p, b, True)


def fmt(x):
    return "  —  " if x is None else f"{x:+.2f}"


def main():
    out = []
    for task, name, g, p, f in cells():
        items = f()
        if not items:
            continue
        full = stats(items)
        half = {h: [x for x in items if zlib.crc32(x["id"].encode()) % 2 == h] for h in (0, 1)}
        S = {h: stats(half[h]) for h in (0, 1)}
        for h in (0, 1):   # predictor on half h, gain on the other half
            out.append(dict(task=task, set=name, gen=g, peer=p, half=h, x=S[h]["x"], gain=S[1 - h]["gain"], lo=S[1 - h]["lo"],
                            hi=S[1 - h]["hi"], full=full))
        print(f"{task:>13} {name:<16} {g:>5} <- {p:<5} n {full['n']:>6}  TPR {100 * full['tpr']:4.0f}% FPR {100 * full['fpr']:4.0f}%  "
              f"r* {full['rstar']:5.2f}  x {fmt(full['x'])}  gain {full['gain']:+.2f} "
              f"[{full['lo']:+.2f}, {full['hi']:+.2f}]", flush=True)
    json.dump(out, open(f"{ROOT}/results/thesis_cells.json", "w"))
    sig = [r for r in out if r["x"] is not None and (r["lo"] > 0 or r["hi"] < 0)]
    agree = sum((r["x"] > 0) == (r["lo"] > 0) for r in sig)
    print(f"\n*** out of sample: {len(out)} cell-halves; {len(sig)} with the other half's interval excluding 0; the predictor's sign "
          f"agrees in {agree} / {len(sig)} ({100 * agree / max(1, len(sig)):.0f}%)")
    full = {(r["task"], r["set"], r["gen"], r["peer"]): r["full"] for r in out}
    fs = [v for v in full.values() if v["x"] is not None and (v["lo"] > 0 or v["hi"] < 0)]
    print(f"*** in sample: {len(full)} cells; {len(fs)} with an interval excluding 0; sign of log2(TPR/FPR / r*) agrees in "
          f"{sum((v['x'] > 0) == (v['lo'] > 0) for v in fs)} / {len(fs)}")
    for t in ("SQL", "tool calls", "word problems"):
        v = [r for r in sig if r["task"] == t]
        print(f"    {t}: {sum((r['x'] > 0) == (r['lo'] > 0) for r in v)} / {len(v)}")


if __name__ == "__main__":
    main()
