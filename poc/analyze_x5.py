"""VIEWS-P5 (docs/prereg/PREREG_VIEWS.md): PopQA views for Qwen3-8B. Accuracy by popularity bin, error kappa and leak between views, the
agreement gate (direct == recall -> accept, else thinking). usage: python analyze_x5.py"""
import json, os, re, statistics as st, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
def kappa(a, b):   # Cohen's kappa on two 0/1 "wrong" lists (same as analyze_views.kappa, which runs its whole analysis on import)
    n = len(a); po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "x5")
M = sys.argv[1] if len(sys.argv) > 1 else "q8b"
L = lambda v, s: {r["id"]: r for r in map(json.loads, open(f"{RES}/qa_{M}_{v}_s{s}.jsonl"))} if os.path.exists(f"{RES}/qa_{M}_{v}_s{s}.jsonl") else None
D1, D2, R, T = L("direct", 1), L("direct", 2), L("recall", 1), L("think", 1)
norm = lambda a: re.sub(r"[^a-z0-9 ]", "", (a or "").lower()).strip()
agree = lambda a, b: bool(norm(a)) and bool(norm(b)) and (norm(a) in norm(b) or norm(b) in norm(a))
ids = sorted(set(D1) & set(D2) & set(R) & (set(T) if T else set(D1)))
print(f"items {len(ids)}" + ("" if T and len(T) == 1500 else " (thinking incomplete: gate rows use the finished thinking answers only)"))
for name, D in (("direct s1", D1), ("direct s2", D2), ("recall", R), ("thinking", T)):
    if D:
        I = [i for i in ids if i in D]
        print(f"  {name:10s} {100 * sum(D[i]['correct'] for i in I) / len(I):5.1f}% | by popularity bin " +
              " ".join(f"{100 * sum(D[i]['correct'] for i in I if D[i]['bin'] == b) / max(1, sum(D[i]['bin'] == b for i in I)):.0f}%" for b in range(5)) +
              f" | tokens {st.mean(D[i]['out_tokens'] or 0 for i in I):.0f}")
for name, A, B in (("direct–direct (same view)", D1, D2), ("direct–recall (different view)", D1, R)):
    wa = [not A[i]["correct"] for i in ids]; wb = [not B[i]["correct"] for i in ids]
    ag = [i for i in ids if agree(A[i]["answer"], B[i]["answer"])]
    lk = sum(not A[i]["correct"] for i in ag) / max(1, len(ag))
    print(f"  {name:32s} error kappa {kappa(wa, wb):.2f}, agree {len(ag)}, leak (wrong among agreeing) {100 * lk:.1f}%")
if T:
    I = [i for i in ids if i in T]
    gate = sum(D1[i]["correct"] if agree(D1[i]["answer"], R[i]["answer"]) else T[i]["correct"] for i in I)
    esc = sum(not agree(D1[i]["answer"], R[i]["answer"]) for i in I)
    print(f"  on {len(I)} items with a thinking answer: always direct {100 * sum(D1[i]['correct'] for i in I) / len(I):.1f}% | gate direct==recall -> thinking "
          f"{100 * gate / len(I):.1f}% (escalated {esc}) | always thinking {100 * sum(T[i]['correct'] for i in I) / len(I):.1f}%")
shared = [D1[i]["bin"] for i in ids if not D1[i]["correct"] and not R[i]["correct"] and agree(D1[i]["answer"], R[i]["answer"])]
specific = [D1[i]["bin"] for i in ids if D1[i]["correct"] != R[i]["correct"]]
print(f"  shared errors by popularity bin (0 = least popular): {[shared.count(b) for b in range(5)]}; view-specific: {[specific.count(b) for b in range(5)]}")
