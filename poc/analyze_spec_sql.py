"""PREREG_SPEC addendum SQL (2026-11-21): check-and-escalate on top of Arctic-Text2SQL-R1-7B. Per checker m (FINAL's generator with its
pre-registered peer), on Spider test (FINAL_SUFFIX=sp, decisive) or BIRD dev's 1,354 unchanged questions (FINAL_SUFFIX=""):
  SPEC    Arctic's greedy query (graded by grade_sql, our gold and free check)
  SPEC+C  Arctic's query kept if it passes the check and m's quick query returns the same rows; else m's default D (SB -> T -> T);
          m's quick query is paid on every question
  FULL    m's FINAL cascade (N, peer's same rows, else D)
Utility = 100 x right - 0.5 x ktokens; one-sided bootstrap over questions (seed means), Holm over SQ-1 (both checkers) and SQ-3.
usage: FINAL_SUFFIX=sp python3 poc/analyze_spec_sql.py     (FINAL_SUFFIX="" for BIRD dev)"""
import contextlib
import io
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
with contextlib.redirect_stdout(io.StringIO()):
    import analyze_final as FN  # noqa: E402
    import analyze_xg as XG  # noqa: E402

SUF = FN.SUF
ARC = {"sp": "arc7sp", "": "arc7"}[SUF]
CHECKERS = [("Qwen3-8B", "q8b", "q35"), ("gpt-oss-20b", "oss20", "q35")]
U = lambda ok, tok: 100 * float(ok) - 0.5 * tok / 1000


def ci_p(d, B=10000):
    ids = sorted(d); n = len(ids); rng = random.Random(1)
    m = sorted(sum(d[rng.choice(ids)] for _ in range(n)) / n for _ in range(B))
    return sum(d.values()) / n, m[int(0.025 * B)], m[int(0.975 * B) - 1], (sum(x <= 0 for x in m) + 1) / (B + 1)


def main():
    G = json.load(open(f"{FN.CV.RES}/grades_{ARC}_s1.json")); G.pop("_gold_fail", None)
    K = {json.loads(l)["id"]: json.loads(l)["n_tok"] for l in open(f"{FN.CV.RES}/{ARC}_cheap_s1.jsonl")}
    print(f"Arctic rows: {len(K)}, graded {len(G)} ({'Spider test' if SUF == 'sp' else 'BIRD dev, unchanged questions'})")
    tests = []
    for name, m, peer in CHECKERS:
        X = FN.items(m, m, peer)
        if X is None:
            print(name, "rows missing"); continue
        GM = FN.Q.grades(m + SUF)
        rows = []
        for x in X:
            i, s = x["id"], x["s"]
            if i not in G or "N" not in G[i] or i not in K:
                continue
            a = G[i]["N"]; n = GM[s][i]["N"]
            spec = (a["ok"], K[i])
            keep = a["chk"] == "pass" and n["chk"] == "pass" and a.get("h") == n.get("h")
            specc = (a["ok"], K[i] + x["tok"]) if keep else (x["dok"], K[i] + x["tok"] + x["dtok"])
            full = XG.POL["cascade"](x)
            rows.append((i, spec, specc, full, keep))
        nq = len({r[0] for r in rows}); nr = len(rows)
        acc = lambda j: 100 * sum(r[j][0] for r in rows) / nr
        kt = lambda j: sum(r[j][1] for r in rows) / nr / 1000
        print(f"\n== checker {name}: {nq} questions, {nr} question-seeds; Arctic kept {100 * sum(r[4] for r in rows) / nr:.0f}%")
        for j, arm in ((1, "SPEC (Arctic alone)"), (2, "SPEC+C"), (3, "FULL (our cascade)")):
            print(f"   {arm:22s} {acc(j):5.1f}% @ {kt(j):5.2f}k  U {sum(U(*r[j]) for r in rows) / nr:6.1f}")
        per = lambda f: {q: sum(v) / len(v) for q, v in _group(rows, f).items()}
        tests.append((f"SQ-1 SPEC+C - SPEC, checker {name}", per(lambda r: U(*r[2]) - U(*r[1]))))
        if m == "q8b":
            tests.append(("SQ-3 SPEC - FULL (Qwen3-8B cascade)", per(lambda r: U(*r[1]) - U(*r[3]))))
    res = [(k,) + ci_p(d) for k, d in tests]
    order = sorted(range(len(res)), key=lambda j: res[j][4]); held = {}; stop = False
    for j, idx in enumerate(order):
        thr = 0.05 / (len(res) - j); ok = not stop and res[idx][4] <= thr; stop = stop or not ok; held[idx] = ok
    print("\nregistered tests (one-sided, Holm at 0.05):")
    for idx, (k, mu, lo, hi, p) in enumerate(res):
        print(f"  {k:40s} {mu:+6.2f} [{lo:+6.2f}, {hi:+6.2f}]  p={p:.4f}  {'HOLDS' if held[idx] else 'not shown'}")


def _group(rows, f):
    out = {}
    for r in rows:
        out.setdefault(r[0], []).append(f(r))
    return out


if __name__ == "__main__":
    main()
