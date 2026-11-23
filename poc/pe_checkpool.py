"""PREREG_DIFF addendum PE3 (2026-11-23): Project Euler candidates (progc, thinkpc; all families and seeds) filtered by the statement's own
small cases (CHECKS), then the plurality final answer. usage: python3 poc/pe_checkpool.py"""
import json, os, random, re
from collections import defaultdict
R = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "x44")
norm = lambda s: re.sub(r"[\s,]", "", str(s or "")).rstrip(".")
U = lambda ok, t: 100 * ok - 0.5 * t / 1000


def boot(d):
    ids = list(d); rng = random.Random(1); B = 4000; n = len(ids)
    bs = sorted(sum(d[rng.choice(ids)] for _ in ids) / n for _ in range(B))
    return sum(d.values()) / n, bs[int(.025 * B)], bs[int(.975 * B) - 1], (sum(x <= 0 for x in bs) + 1) / (B + 1)


for which in ("euler", "eulert"):
    C = defaultdict(list); tok = defaultdict(int)
    for m, tag in (("q8b", "q8bL"), ("oss20", "oss20"), ("oss120", "oss120")):
        for mode in ("progc", "thinkpc"):
            for s in (1, 2, 3):
                p = f"{R}/{which}_{tag}_{mode}_s{s}.jsonl"
                for l in (open(p) if os.path.exists(p) else []):
                    r = json.loads(l); tok[r["id"]] += int(r.get("out_tokens") or 0)
                    ck = r.get("checks")
                    passed = isinstance(ck, list) and len(ck) > 0 and all(c[-1] is True or str(c[-1]) == "True" for c in ck)
                    C[r["id"]].append((norm(r.get("answer")), passed, str(r["correct"]) == "True"))
    S = {}
    for s in (1, 2, 3):
        for l in open(f"{R}/{which}_oss120_thinkp_s{s}.jsonl"):
            r = json.loads(l); S.setdefault(r["id"], []).append(U(str(r["correct"]) == "True", int(r.get("out_tokens") or 0)))
    res, plu = {}, {}
    for i, L in C.items():
        def pick(rows):
            c = defaultdict(int)
            for a, _, _ in rows:
                if a:
                    c[a] += 1
            return max(c, key=c.get) if c else None
        right = {a for a, _, ok in L if ok}
        kept = [x for x in L if x[1]]
        a = pick(kept) or pick(L); b = pick(L)
        res[i] = U(a in right, tok[i]); plu[i] = U(b in right, tok[i])
    ids = [i for i in res if i in S]
    acc = lambda D: sum(D[i] for i in ids) / len(ids)
    print(f"{which}: n={len(ids)}  PE3 U {acc(res):.2f}  plurality U {acc(plu):.2f}  oss120 think-then-program U {sum(sum(S[i])/len(S[i]) for i in ids)/len(ids):.2f}  "
          f"pool {sum(tok[i] for i in ids)/len(ids)/1000:.1f}k")
    for nm, D in (("plurality", plu), ("oss120 think-then-program", {i: sum(S[i]) / len(S[i]) for i in ids})):
        print(f"   PE3 - {nm}: %+.2f [%+.2f, %+.2f] p=%.4f" % boot({i: res[i] - D[i] for i in ids}))
