"""N17 (results/PREREG_N.md): a different model's program as the second opinion on contest geometry. Escalate gpt-oss-120b medium to
high (64k) if medium fails the examples, or if Qwen3.6's no-think program (same seed) passes the examples and disagrees with medium's on
any N5-generated input (relative 1e-2). usage: CC_SET=full python analyze_n17.py"""
import json, os, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("CC_SET", "full")
from run_cc import PFILE, RES, tok_eq  # noqa: E402
from sandbox import run_python  # noqa: E402

P = {p["name"]: p for p in json.load(open(PFILE))}
NPUB = {n: sum(t["kind"] == "public" for t in p["tests"]) for n, p in P.items()}
N5 = {r["name"]: r for r in map(json.loads, open(f"{RES}/n5_oss120_low_s1.jsonl"))}
INP = {n: [c[0] for c in r["cases"]] for n, r in N5.items() if r.get("cases")}
load = lambda t, s: {r["name"]: r for r in map(json.loads, open(f"{RES}/cc_full_{t}_s{s}.jsonl"))}
passes = lambda r: bool(r["code"]) and r["passed"] >= NPUB[r["name"]]
tok = lambda r: r.get("out_tokens") or 0
M = {sd: load("oss120_medium", sd) for sd in (1, 2, 3)}; H = {sd: load("oss120_high64k", sd) for sd in (1, 2, 3)}
Q = {sd: load("q36_plain", sd) for sd in (1, 2, 3)}


def outs(code, inputs):
    res = []
    for x in inputs:
        r = run_python(code, x, timeout=10)
        res.append(r.stdout if r.status == "ok" else None)
    return res


jobs = [(sd, n) for sd in (1, 2, 3) for n in M[sd] if n in INP and passes(M[sd][n]) and passes(Q[sd][n])]
with ThreadPoolExecutor(32) as ex:
    OM = dict(zip(jobs, ex.map(lambda j: outs(M[j[0]][j[1]]["code"], INP[j[1]]), jobs)))
    OQ = dict(zip(jobs, ex.map(lambda j: outs(Q[j[0]][j[1]]["code"], INP[j[1]]), jobs)))
dis = {j: any(a is None or b is None or not tok_eq(a, b, 1e-2) for a, b in zip(OM[j], OQ[j])) for j in jobs}
A = {k: [0, 0, 0] for k in ("always high", "medium -> high (examples)", "N17 medium -> high (examples + Qwen3.6 disagreement)")}
add = lambda k, ok, t: (A[k].__setitem__(0, A[k][0] + ok), A[k].__setitem__(1, A[k][1] + t), A[k].__setitem__(2, A[k][2] + 1))
det = [0, 0, 0, 0]
for sd in (1, 2, 3):
    for n in M[sd]:
        m, h, q = M[sd][n], H[sd][n], Q[sd][n]
        add("always high", h["passed_all"], tok(h))
        add("medium -> high (examples)", m["passed_all"] if passes(m) else h["passed_all"], tok(m) + (0 if passes(m) else tok(h)))
        esc = (not passes(m)) or dis.get((sd, n), False)
        add("N17 medium -> high (examples + Qwen3.6 disagreement)", h["passed_all"] if esc else m["passed_all"], tok(m) + tok(q) + (tok(h) if esc else 0))
        if (sd, n) in dis:
            if m["passed_all"]:
                det[3] += 1; det[2] += dis[(sd, n)]
            else:
                det[1] += 1; det[0] += dis[(sd, n)]
for k, (s, t, c) in A.items():
    print(f"{k:56s} {100 * s / c:5.1f}% @ {t / c / 1000:5.1f}k tokens per problem (n = {c})")
print(f"cross-model check where both pass the examples and inputs exist ({len(jobs)} problem-seeds): flags {det[0]}/{det[1]} wrong medium "
      f"programs ({100 * det[0] / max(1, det[1]):.0f}%), {det[2]}/{det[3]} correct ({100 * det[2] / max(1, det[3]):.1f}% false alarms)")
