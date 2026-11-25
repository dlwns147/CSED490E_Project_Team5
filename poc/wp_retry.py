"""WP-RETRY (2026-11-25; offline on stored rows, all seen: a first look, plus other seed orders): the cheapest competitor of SAMEREF. RETRY = one program; a second program only if the first prints no value (visible failure). usage: python wp_retry.py"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wp_crossref as C
ALL = C.NINE + ("easyc", "nl4c", "omtf2"); U, tk, ci = C.U, C.tk, C.ci
D = {}
for st in ALL:
    RN, P, A, _, _, A2 = C.load(st); A3 = C.L(f"opt_oss120_{st}_thinkfreenE_s3.jsonl")
    Z = {json.loads(l)["id"]: json.loads(l) for l in open(f"{C.W.OUT}/crossref_{st}_samejudge.jsonl")}
    D[st] = (RN, P, {1: A, 2: A2, 3: A3}, Z)


def retry(R, i, a, b):
    x = R[a][i]
    if x["pred"] is not None:
        return bool(x["correct"]), tk(x)
    y = R[b][i]
    return bool(y["correct"]), tk(x) + tk(y)


def samer(RN, R, Z, i):
    x, y = R[1][i], R[2][i]; t = tk(x) + tk(y)
    if C.same(RN, x["pred"], y["pred"]) or x["pred"] is None or y["pred"] is None:
        return bool((y if x["pred"] is None else x)["correct"]), t
    z = Z.get(i, {})
    return bool((y if z.get("pick") == "A2" else x)["correct"]), t + (z.get("tok") or 0)


f = lambda v: f"{100*sum(a for a, _ in v)/len(v):.1f}% @ {sum(t for _, t in v)/len(v)/1000:.2f}k  utility {sum(U(*x) for x in v)/len(v):.2f}"
for lab, ss in (("all twelve", ALL), ("nine", C.NINE), ("three easy", ("easyc", "nl4c", "omtf2"))):
    k = [(st, i) for st in ss for i in D[st][1]]
    one = [(bool(D[s][2][1][i]["correct"]), tk(D[s][2][1][i])) for s, i in k]; ret = [retry(D[s][2], i, 1, 2) for s, i in k]; sr = [samer(D[s][0], D[s][2], D[s][3], i) for s, i in k]
    print(f"== {lab} n={len(k)}: one {f(one)} | RETRY {f(ret)} | SAMEREF {f(sr)}")
    for n, x, y in (("RETRY − one", ret, one), ("SAMEREF − RETRY", sr, ret)):
        print(f"   {n}: accuracy {ci([100*(a[0]-b[0]) for a, b in zip(x, y)])}  ktok {ci([(a[1]-b[1])/1000 for a, b in zip(x, y)])}  utility {ci([U(*a)-U(*b) for a, b in zip(x, y)])}")
for a, b, ss in ((2, 1, ALL), (2, 3, C.NINE), (3, 1, C.NINE), (3, 2, C.NINE)):
    k = [(st, i) for st in ss for i in D[st][1]]
    one = [(bool(D[s][2][a][i]["correct"]), tk(D[s][2][a][i])) for s, i in k]; ret = [retry(D[s][2], i, a, b) for s, i in k]
    print(f"order s{a}→s{b} n={len(k)}: RETRY − one accuracy {ci([100*(x[0]-y[0]) for x, y in zip(ret, one)])}  ktok {ci([(x[1]-y[1])/1000 for x, y in zip(ret, one)])}  utility {ci([U(*x)-U(*y) for x, y in zip(ret, one)])}")
