"""N13 (docs/prereg/PREREG_N.md): escalation gated on the statement's examples OR disagreement with the problem's approximate brute-force
oracle (N5 cases of gpt-oss-120b low seed 1). gpt-oss-120b low / medium / high64k, seeds 1-3. Oracle tokens charged to every
problem-seed. usage: CC_SET=full python analyze_n13.py"""
import json, os, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("CC_SET", "full")
from run_cc import PFILE, RES, tok_eq  # noqa: E402
from sandbox import run_python  # noqa: E402

P = {p["name"]: p for p in json.load(open(PFILE))}
NPUB = {n: sum(t["kind"] == "public" for t in p["tests"]) for n, p in P.items()}
N5 = {r["name"]: r for r in map(json.loads, open(f"{RES}/n5_oss120_low_s1.jsonl"))}
ORC = {n: r["cases"] for n, r in N5.items() if r["oracle_ok"] and r.get("cases")}
OTOK = {n: r.get("oracle_tokens") or 0 for n, r in N5.items()}
load = lambda t, s: {r["name"]: r for r in map(json.loads, open(f"{RES}/cc_full_{t}_s{s}.jsonl"))}
passes = lambda r: bool(r["code"]) and r["passed"] >= NPUB[r["name"]]
tok = lambda r: r.get("out_tokens") or 0


def agrees(code, cases):
    for inp, ref in cases:
        x = run_python(code, inp, timeout=10)
        if x.status != "ok" or not tok_eq(x.stdout, ref, 1e-2):
            return False
    return True


runs = {(lv, sd): load(t, sd) for lv, t in (("low", "oss120_low"), ("medium", "oss120_medium"), ("high", "oss120_high64k")) for sd in (1, 2, 3)}
jobs = [(lv, sd, n) for (lv, sd), R in runs.items() if lv != "high" for n in R if n in ORC and passes(R[n])]
with ThreadPoolExecutor(32) as ex:
    AG = dict(zip(jobs, ex.map(lambda j: agrees(runs[(j[0], j[1])][j[2]]["code"], ORC[j[2]]), jobs)))
gate = lambda lv, sd, n: passes(runs[(lv, sd)][n]) and AG.get((lv, sd, n), True)   # True = accept
A = {k: [0, 0, 0] for k in ("always high", "N8 medium->high (examples)", "N13 medium->high (examples + oracle)", "N13b oracle only if medium passes the examples",
                            "N8 low->medium->high (examples)", "N13 low->medium->high (examples + oracle)")}
add = lambda k, ok, t: (A[k].__setitem__(0, A[k][0] + ok), A[k].__setitem__(1, A[k][1] + t), A[k].__setitem__(2, A[k][2] + 1))
det = [0, 0, 0, 0]   # medium wrong passers flagged / total; correct passers flagged / total (problems with an oracle)
for sd in (1, 2, 3):
    L, M, H = runs[("low", sd)], runs[("medium", sd)], runs[("high", sd)]
    for n in L:
        l, m, h = L[n], M[n], H[n]; o = OTOK.get(n, 0)
        add("always high", h["passed_all"], tok(h))
        add("N8 medium->high (examples)", m["passed_all"] if passes(m) else h["passed_all"], tok(m) + (0 if passes(m) else tok(h)))
        g = gate("medium", sd, n)
        add("N13 medium->high (examples + oracle)", m["passed_all"] if g else h["passed_all"], o + tok(m) + (0 if g else tok(h)))
        add("N13b oracle only if medium passes the examples", m["passed_all"] if g else h["passed_all"], (o if passes(m) else 0) + tok(m) + (0 if g else tok(h)))
        if passes(l):
            add("N8 low->medium->high (examples)", l["passed_all"], tok(l))
        elif passes(m):
            add("N8 low->medium->high (examples)", m["passed_all"], tok(l) + tok(m))
        else:
            add("N8 low->medium->high (examples)", h["passed_all"], tok(l) + tok(m) + tok(h))
        if gate("low", sd, n):
            add("N13 low->medium->high (examples + oracle)", l["passed_all"], o + tok(l))
        elif g:
            add("N13 low->medium->high (examples + oracle)", m["passed_all"], o + tok(l) + tok(m))
        else:
            add("N13 low->medium->high (examples + oracle)", h["passed_all"], o + tok(l) + tok(m) + tok(h))
        if n in ORC and passes(m):
            if m["passed_all"]:
                det[3] += 1; det[2] += not AG[("medium", sd, n)]
            else:
                det[1] += 1; det[0] += not AG[("medium", sd, n)]
for k, (s, t, c) in A.items():
    print(f"{k:44s} {100 * s / c:5.1f}% @ {t / c / 1000:5.1f}k tokens per problem (n = {c})")
print(f"oracle on medium example-passers (problems with an oracle): flags {det[0]}/{det[1]} wrong ({100 * det[0] / max(1, det[1]):.0f}%), "
      f"{det[2]}/{det[3]} correct ({100 * det[2] / max(1, det[3]):.1f}% false alarms)")
