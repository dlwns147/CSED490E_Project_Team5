"""N19 (results/PREREG_N.md): tool-condition agreement gate on contest geometry (gpt-oss-120b low without vs with the K8 toolbox),
escalating to medium. usage: CC_SET=full python analyze_n19.py"""
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
L = {sd: load("oss120_low", sd) for sd in (1, 2, 3)}; K = {sd: load("oss120_low_k8", sd) for sd in (1, 2, 3)}
M = {sd: load("oss120_medium", sd) for sd in (1, 2, 3)}


def outs(code, inputs):
    return [(lambda r: r.stdout if r.status == "ok" else None)(run_python(code, x, timeout=10)) for x in inputs]


jobs = [(sd, n) for sd in (1, 2, 3) for n in L[sd] if n in INP and passes(L[sd][n]) and passes(K[sd][n])]
with ThreadPoolExecutor(32) as ex:
    OL = dict(zip(jobs, ex.map(lambda j: outs(L[j[0]][j[1]]["code"], INP[j[1]]), jobs)))
    OK_ = dict(zip(jobs, ex.map(lambda j: outs(K[j[0]][j[1]]["code"], INP[j[1]]), jobs)))
agree = {j: all(a is not None and b is not None and tok_eq(a, b, 1e-2) for a, b in zip(OL[j], OK_[j])) for j in jobs}
A = {k: [0, 0, 0] for k in ("low only", "medium only", "N3 low -> medium (examples)", "N19 low -> medium (examples + K8 agreement)",
                            "N19b (examples + K8 agreement where inputs exist, examples alone elsewhere)")}
add = lambda k, ok, t: (A[k].__setitem__(0, A[k][0] + ok), A[k].__setitem__(1, A[k][1] + t), A[k].__setitem__(2, A[k][2] + 1))
for sd in (1, 2, 3):
    for n in L[sd]:
        l, k, m = L[sd][n], K[sd][n], M[sd][n]
        add("low only", l["passed_all"], tok(l)); add("medium only", m["passed_all"], tok(m))
        add("N3 low -> medium (examples)", l["passed_all"] if passes(l) else m["passed_all"], tok(l) + (0 if passes(l) else tok(m)))
        acc = passes(l) and agree.get((sd, n), False)
        add("N19 low -> medium (examples + K8 agreement)", l["passed_all"] if acc else m["passed_all"], tok(l) + tok(k) + (0 if acc else tok(m)))
        acc_b = passes(l) and (agree.get((sd, n), False) if n in INP else True)
        add("N19b (examples + K8 agreement where inputs exist, examples alone elsewhere)", l["passed_all"] if acc_b else m["passed_all"],
            tok(l) + (tok(k) if n in INP else 0) + (0 if acc_b else tok(m)))
for k, (s, t, c) in A.items():
    print(f"{k:76s} {100 * s / c:5.1f}% @ {t / c / 1000:4.1f}k (n = {c})")
wrong_acc = sum(1 for j in jobs if agree[j] and not L[j[0]][j[1]]["passed_all"]); right_rej = sum(1 for j in jobs if not agree[j] and L[j[0]][j[1]]["passed_all"])
wl = sum(1 for j in jobs if not L[j[0]][j[1]]["passed_all"]); rl = len(jobs) - wl
print(f"where both pass the examples and inputs exist ({len(jobs)}): wrong low programs accepted by agreement {wrong_acc}/{wl}, correct ones rejected {right_rej}/{rl}")
