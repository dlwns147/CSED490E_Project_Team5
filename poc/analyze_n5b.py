"""N5b (results/PREREG_V.md): the saved approximate oracles select among the 3 Part B samples (ALGO's use): the first example-passer
that agrees with the oracle on every saved input, else the first example-passer, else seed 1. Also detection / false-alarm rates of the
oracle on example-passing seed-1 programs and the seed-1 counterexample-repair result.
usage: CC_SET=full python analyze_n5b.py <tag> [<tag> ...]"""
import json, os, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_cc import OPRE, PFILE, RES, VFILE, tok_eq  # noqa: E402
from sandbox import run_python  # noqa: E402

LOOSE = 1e-2
P = {p["name"]: p for p in json.load(open(PFILE))}; V = json.load(open(VFILE))
NPUB = {n: sum(t["kind"] == "public" for t in p["tests"]) for n, p in P.items()}


def agrees(code, cases):
    for inp, ref in cases:
        r = run_python(code, inp, timeout=10)
        if r.status != "ok" or not tok_eq(r.stdout, ref, LOOSE):
            return False
    return True


for tag in sys.argv[1:]:
    N5 = {r["name"]: r for r in map(json.loads, open(f"{RES}/n5_{tag}_s1.jsonl"))}
    S = [{r["name"]: r for r in map(json.loads, open(f"{RES}/{OPRE}{tag}_s{sd}.jsonl"))} for sd in (1, 2, 3)]
    names = sorted(N5)
    jobs = [(n, i) for n in names if N5[n]["oracle_ok"] and N5[n]["cases"] for i in range(3)
            if S[i][n]["code"] and S[i][n]["passed"] >= NPUB[n]]
    with ThreadPoolExecutor(24) as ex:
        A = dict(zip(jobs, ex.map(lambda j: agrees(S[j[1]][j[0]]["code"], N5[j[0]]["cases"]), jobs)))
    fp = sel = orc = rep = 0
    det = [0, 0, 0, 0]   # wrong passers, flagged; correct passers, flagged (seed 1, problems with an oracle)
    for n in names:
        rs = [S[i][n] for i in range(3)]
        pas = [i for i in range(3) if rs[i]["code"] and rs[i]["passed"] >= NPUB[n]]
        first = rs[pas[0]] if pas else rs[0]
        ok = [i for i in pas if A.get((n, i))]
        pick = rs[ok[0]] if ok else first
        fp += first["passed_all"]; sel += pick["passed_all"]; orc += any(r["passed_all"] for r in rs); rep += N5[n]["passed_all"]
        if (n, 0) in A:
            k = 0 if not rs[0]["passed_all"] else 2
            det[k] += 1; det[k + 1] += not A[(n, 0)]
    m = len(names); tok = sum(N5[n]["oracle_tokens"] for n in names) / m
    print(f"{tag}: oracle accepted {sum(N5[n]['oracle_ok'] for n in names)}/{m} ({tok:.0f} tokens per problem) | seed-1 passers: wrong flagged "
          f"{det[1]}/{det[0]}, correct flagged {det[3]}/{det[2]} | k=3: example check {100 * fp / m:.1f}% | oracle selection {100 * sel / m:.1f}% | "
          f"oracle any-of-3 {100 * orc / m:.1f}% | seed 1 {100 * sum(S[0][n]['passed_all'] for n in names) / m:.1f}% -> counterexample repair {100 * rep / m:.1f}%")
