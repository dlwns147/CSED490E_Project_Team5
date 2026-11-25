"""OEIS-RETRY (2026-11-25; offline, stored rows seen): does OEIS-TP's gain over one thinking program survive the cheapest competitor, a second program only if the first prints nothing? usage: python oeis_retry.py"""
import json, os, random
R = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "x44")
L = lambda f: {json.loads(l)["id"]: json.loads(l) for l in open(f"{R}/{f}")}
U = lambda ok, t: 100 * ok - 0.5 * t / 1000


def outs(r):
    o = r.get("outs"); return o if isinstance(o, list) else (eval(o) if o else [])


def ci(d, n=4000):
    rng = random.Random(1); b = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(n)); return f"{sum(d)/len(d):+.2f} [{b[100]:+.2f}, {b[3899]:+.2f}]"


for pfx, tags in (("oeisf", ("all_tp", "all_tpf", "tp")), ("oeis", ("all_tp",))):
    A = {s: L(f"{pfx}_oss120M_think_s{s}.jsonl") for s in (2, 3) if os.path.exists(f"{R}/{pfx}_oss120M_think_s{s}.jsonl")}
    f = next((f"{pfx}_diff_{t}.jsonl" for t in tags if os.path.exists(f"{R}/{pfx}_diff_{t}.jsonl")), None)
    if len(A) < 2 or not f:
        print(pfx, "missing", list(A), f); continue
    D = L(f); ids = [i for i in A[2] if i in A[3]]; ok = lambda r: str(r["correct"]) == "True"; tk = lambda r: int(r.get("out_tokens") or 0)
    arms = {"one": [], "RETRY": [], "TP": []}
    for i in ids:
        for k in arms:
            v = []
            for a, b in ((2, 3), (3, 2)):
                x, y = A[a][i], A[b][i]
                if k == "one" or (k == "RETRY" and outs(x)):
                    v.append((ok(x), tk(x)))
                elif k == "RETRY":
                    v.append((ok(y), tk(x) + tk(y)))
                else:
                    d = D.get(i); v.append((bool(d["right"]), d["pool_tok"] + d["oracle_tok"]) if d else (False, tk(x) + tk(y)))
            arms[k].append((sum(a for a, _ in v) / 2, sum(t for _, t in v) / 2))
    print(f"== {pfx} n={len(ids)} ({f}); first prints nothing: s2 {sum(not outs(A[2][i]) for i in ids)}, s3 {sum(not outs(A[3][i]) for i in ids)}")
    for k, v in arms.items():
        print(f"  {k:6s} {100*sum(a for a, _ in v)/len(v):.1f}% @ {sum(t for _, t in v)/len(v)/1000:.2f}k utility {sum(U(*x) for x in v)/len(v):.2f}")
    for x, y in (("RETRY", "one"), ("TP", "one"), ("TP", "RETRY")):
        print(f"  {x} − {y}: accuracy {ci([100*(a[0]-b[0]) for a, b in zip(arms[x], arms[y])])} ktok {ci([(a[1]-b[1])/1000 for a, b in zip(arms[x], arms[y])])} utility {ci([U(*a)-U(*b) for a, b in zip(arms[x], arms[y])])}")
