"""CROSSREF (PREREG_DIFF, 2026-11-25): a referee on the disagreements of two different families, A = gpt-oss-120b one program (corrected environment, seed 1)
and B = OptiMind-SFT. usage: POC_BASE_URL=... python wp_crossref.py run <set> [...]   |   python wp_crossref.py score | scorec | scorec2   |   ... runc <set> [...]   (CROSSREF-C: same-family judge)"""
import json, os, random, re, sys, zlib
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wp_plan as W
SETS = ("optc", "indc", "mamoc", "optnew", "optmath", "omtf", "omtf2", "bwor", "logior", "optibench", "easyc", "nl4c")
L = lambda f: {json.loads(l)["id"]: json.loads(l) for l in open(f"{W.R3}/{f}")} if os.path.exists(f"{W.R3}/{f}") else None
U = lambda ok, t: 100 * ok - 0.5 * t / 1000
tk = lambda r: int(r.get("out_tokens") or 0)


def load(st):
    os.environ["NLOPT_SET"] = st
    import run_nlopt as RN
    return RN, {p["id"]: p for p in RN.problems(st)}, L(f"opt_oss120_{st}_thinkfreenE_s1.jsonl"), L(f"opt_optimind_{st}_gurobi_s1.jsonl"), L(f"opt_sirl32_{st}_copt_s1.jsonl"), L(f"opt_oss120_{st}_thinkfreenE_s2.jsonl")


def same(RN, x, y):
    if x is None or y is None:
        return False
    if x == "NBS" or y == "NBS":
        return x == y
    return isinstance(x, float) and isinstance(y, float) and RN.correct(x, str(y))


def run(sets):
    from llm import chat
    for st in sets:
        RN, P, A, B, _, _ = load(st)
        out = f"{W.OUT}/crossref_{st}_judge.jsonl"
        done = {json.loads(l)["id"] for l in open(out)} if os.path.exists(out) else set()
        todo = [i for i in P if i not in done and A[i]["pred"] is not None and B[i]["pred"] is not None and not same(RN, A[i]["pred"], B[i]["pred"])]
        print(st, "to judge", len(todo), flush=True)

        def one(i):
            first = "A" if zlib.crc32(i.encode()) % 2 == 0 else "B"
            X = {"A": A[i], "B": B[i]}; o = {"A": "B", "B": "A"}[first]
            z = chat(W.JUDGE.format(q=P[i]["q"], v1=X[first]["pred"], c1=(X[first].get("code") or "")[:6000], v2=X[o]["pred"], c2=(X[o].get("code") or "")[:6000]),
                     think=True, max_tokens=12000, temperature=0.7, seed=5000 + zlib.crc32(i.encode()) % 997)
            m = re.findall(r"\\boxed\{\s*([12])\s*\}", z.get("text") or "")
            pick = {"1": first, "2": o}[m[-1]] if m else None
            return {"id": i, "pick": pick, "tok": z.get("out_tokens") or 0}
        with ThreadPoolExecutor(32) as ex, open(out, "a") as f:
            for z in ex.map(one, todo):
                f.write(json.dumps(z) + "\n"); f.flush()


def runc(sets):
    """CROSSREF-C: SAMEREF = the same judge on the disagreements of two gpt-oss-120b programs (seeds 1, 2, corrected environment)"""
    from llm import chat
    for st in sets:
        RN, P, A, _, _, A2 = load(st)
        out = f"{W.OUT}/crossref_{st}_samejudge.jsonl"
        done = {json.loads(l)["id"] for l in open(out)} if os.path.exists(out) else set()
        todo = [i for i in P if i not in done and A[i]["pred"] is not None and A2[i]["pred"] is not None and not same(RN, A[i]["pred"], A2[i]["pred"])]
        print(st, "to judge (same family)", len(todo), flush=True)

        def one(i):
            first = "A" if zlib.crc32(i.encode()) % 2 == 0 else "A2"
            X = {"A": A[i], "A2": A2[i]}; o = {"A": "A2", "A2": "A"}[first]
            z = chat(W.JUDGE.format(q=P[i]["q"], v1=X[first]["pred"], c1=(X[first].get("code") or "")[:6000], v2=X[o]["pred"], c2=(X[o].get("code") or "")[:6000]),
                     think=True, max_tokens=12000, temperature=0.7, seed=5000 + zlib.crc32(i.encode()) % 997)
            m = re.findall(r"\\boxed\{\s*([12])\s*\}", z.get("text") or "")
            return {"id": i, "pick": {"1": first, "2": o}[m[-1]] if m else None, "tok": z.get("out_tokens") or 0}
        with ThreadPoolExecutor(32) as ex, open(out, "a") as f:
            for z in ex.map(one, todo):
                f.write(json.dumps(z) + "\n"); f.flush()


NINE = ("optc", "indc", "mamoc", "optnew", "optmath", "omtf", "bwor", "logior", "optibench")


def scorec():
    pool = {k: {} for k in ("A", "B", "JUDGE", "SAMEREF", "PLUR3", "ADAPT3", "ADAPT3+J")}; rr = {"JUDGE": [0, 0], "SAMEREF": [0, 0]}
    for st in NINE:
        RN, P, A, B, S, A2 = load(st)
        A3 = L(f"opt_oss120_{st}_thinkfreenE_s3.jsonl")
        ZJ = {json.loads(l)["id"]: json.loads(l) for l in open(f"{W.OUT}/crossref_{st}_judge.jsonl")}; ZS = {json.loads(l)["id"]: json.loads(l) for l in open(f"{W.OUT}/crossref_{st}_samejudge.jsonl")}

        def ref(i, X, Y, Z, name, yk):
            x, y = X[i], Y[i]; cx, cy = bool(x["correct"]), bool(y["correct"]); base = tk(x) + tk(y)
            if same(RN, x["pred"], y["pred"]):
                return cx, base
            if x["pred"] is None or y["pred"] is None:
                return (cy if x["pred"] is None else cx), base
            z = Z.get(i, {}); pk = z.get("pick")
            if cx != cy:
                rr[name][1] += 1; rr[name][0] += (pk == "A") == cx and pk is not None
            return (cy if pk == yk else cx), base + (z.get("tok") or 0)
        for i in P:
            pool["A"][(st, i)] = (bool(A[i]["correct"]), tk(A[i])); pool["B"][(st, i)] = (bool(B[i]["correct"]), tk(B[i]))
            pool["JUDGE"][(st, i)] = ref(i, A, B, ZJ, "JUDGE", "B"); pool["SAMEREF"][(st, i)] = ref(i, A, A2, ZS, "SAMEREF", "A2")
            if A3:
                rows = [A[i], A2[i], A3[i]]; cls = []
                for r in rows:
                    for c in cls:
                        if same(RN, c[0]["pred"], r["pred"]):
                            c.append(r); break
                    else:
                        if r["pred"] is not None:
                            cls.append([r])
                best = max(cls, key=len) if cls and max(len(c) for c in cls) >= 2 else [A[i]]
                pool["PLUR3"][(st, i)] = (bool(best[0]["correct"]), sum(tk(r) for r in rows))
                # adaptive consistency (ASC with at most 3 samples): stop after two that agree, else a third; majority, else the first program (ADAPT3); ADAPT3+J: the judge when the two differ and no third agrees
                a2 = A2[i]; t2 = tk(A[i]) + tk(a2)
                if same(RN, A[i]["pred"], a2["pred"]) or A[i]["pred"] is None or a2["pred"] is None:
                    pick = A[i] if A[i]["pred"] is not None else a2
                    pool["ADAPT3"][(st, i)] = pool["ADAPT3+J"][(st, i)] = (bool(pick["correct"]), t2)
                else:
                    t3 = t2 + tk(A3[i]); m = [r for r in (A[i], a2) if same(RN, A3[i]["pred"], r["pred"])]
                    pool["ADAPT3"][(st, i)] = (bool((m[0] if m else A[i])["correct"]), t3)
                    zs = ZS.get(i, {}); pickj = a2 if zs.get("pick") == "A2" else A[i]
                    pool["ADAPT3+J"][(st, i)] = (bool((m[0] if m else pickj)["correct"]), t3 + (0 if m else (zs.get("tok") or 0)))
    print("judge right on resolvable disagreements:", {k: f"{a} of {b} ({100*a/max(1,b):.0f}%)" for k, (a, b) in rr.items()})
    for k, v in pool.items():
        if v:
            print(f"{k:8s} n={len(v)} accuracy {100*sum(x for x, _ in v.values())/len(v):.1f}%  tokens {sum(t for _, t in v.values())/len(v)/1000:.2f}k  utility {sum(U(*x) for x in v.values())/len(v):.2f}")
    for x, y in (("JUDGE", "A"), ("SAMEREF", "A"), ("JUDGE", "SAMEREF"), ("JUDGE", "PLUR3"), ("PLUR3", "A"), ("SAMEREF", "PLUR3"), ("SAMEREF", "ADAPT3"), ("JUDGE", "ADAPT3"), ("ADAPT3", "A"), ("ADAPT3+J", "SAMEREF")):
        if pool[x] and pool[y]:
            ids = list(pool[x])
            print(f"{x} − {y}: accuracy {ci([100*(pool[x][i][0]-pool[y][i][0]) for i in ids])}  ktok {ci([(pool[x][i][1]-pool[y][i][1])/1000 for i in ids])}  utility {ci([U(*pool[x][i])-U(*pool[y][i]) for i in ids])}")
    for st in NINE:
        ids = [i for i in pool["A"] if i[0] == st]
        print(f"  {st:9s} JUDGE − SAMEREF accuracy {100*sum(pool['JUDGE'][i][0]-pool['SAMEREF'][i][0] for i in ids)/len(ids):+.2f}" + (f"  PLUR3 acc {100*sum(pool['PLUR3'][i][0] for i in ids)/len(ids):.1f}" if pool["PLUR3"] else ""))


def scorec2():
    """CROSSREF-C2: SAMEREF - A per set and pooled, on the three easy sets and (for the agreement rate -> gain relation) the nine sets of CROSSREF-C. The agreement rate uses no labels."""
    T3 = ("easyc", "nl4c", "omtf2"); pool = {}
    for st in NINE + T3:
        RN, P, A, _, _, A2 = load(st)
        Z = {json.loads(l)["id"]: json.loads(l) for l in open(f"{W.OUT}/crossref_{st}_samejudge.jsonl")}
        agree = res = right = miss = 0; row = []
        for i in P:
            x, y = A[i], A2[i]; cx, cy = bool(x["correct"]), bool(y["correct"]); t = tk(x) + tk(y); ok = cx
            if same(RN, x["pred"], y["pred"]):
                agree += 1
            elif x["pred"] is None or y["pred"] is None:
                ok = cy if x["pred"] is None else cx
            else:
                z = Z.get(i); miss += z is None; z = z or {}; pk = z.get("pick"); t += z.get("tok") or 0; ok = cy if pk == "A2" else cx
                if cx != cy:
                    res += 1; right += pk is not None and (pk == "A") == cx
            row.append((cx, tk(x), ok, t))
        pool[st] = row; n = len(row)
        print(f"{st:9s} n={n:3d} agree {100*agree/n:5.1f}%  A {100*sum(r[0] for r in row)/n:5.1f}% {sum(r[1] for r in row)/n/1000:.2f}k  SAMEREF {100*sum(r[2] for r in row)/n:5.1f}% {sum(r[3] for r in row)/n/1000:.2f}k  judge {right}/{res}" + (f"  NOT JUDGED {miss}" if miss else "")
              + f"  acc {ci([100*(r[2]-r[0]) for r in row])}  utility {ci([U(r[2], r[3])-U(r[0], r[1]) for r in row])}", flush=True)
    for lab, ss in (("three easy sets", T3), ("nine sets", NINE), ("all twelve", NINE + T3)):
        R = [r for st in ss for r in pool[st]]
        print(f"{lab}: n={len(R)} acc {ci([100*(r[2]-r[0]) for r in R])}  ktok {ci([(r[3]-r[1])/1000 for r in R])}  utility {ci([U(r[2], r[3])-U(r[0], r[1]) for r in R])}")


def ci(d, n=4000):
    rng = random.Random(1); b = sorted(sum(rng.choice(d) for _ in d) / len(d) for _ in range(n))
    return f"{sum(d)/len(d):+.2f} [{b[100]:+.2f}, {b[3899]:+.2f}]"


def score():
    pool = {k: {} for k in ("A", "B", "JUDGE", "VOTE", "A2")}; judged = right_res = res = 0
    for st in SETS:
        RN, P, A, B, S, A2 = load(st)
        Z = {json.loads(l)["id"]: json.loads(l) for l in open(f"{W.OUT}/crossref_{st}_judge.jsonl")}
        row = {k: {} for k in pool}
        for i in P:
            a, b = A[i], B[i]; ca, cb, ta, tb = bool(a["correct"]), bool(b["correct"]), tk(a), tk(b)
            row["A"][i] = (ca, ta); row["B"][i] = (cb, tb)
            agree = same(RN, a["pred"], b["pred"]); base = ta + tb
            if agree:
                for k in ("JUDGE", "VOTE", "A2"):
                    row[k][i] = (ca, base)
                continue
            if a["pred"] is None or b["pred"] is None:
                ok = cb if a["pred"] is None else ca
                for k in ("JUDGE", "VOTE", "A2"):
                    row[k][i] = (ok, base)
                continue
            z = Z.get(i, {}); pk = z.get("pick")
            row["JUDGE"][i] = (cb if pk == "B" else ca, base + (z.get("tok") or 0))
            if ca != cb and z:
                res += 1; judged += 1; right_res += (pk == "A") == ca and pk is not None
            for k, T in (("VOTE", S), ("A2", A2)):
                if T:
                    v = T[i]["pred"]; row[k][i] = (cb if same(RN, v, b["pred"]) else ca, base + tk(T[i]))
        for k, v in row.items():
            if len(v) == len(P):
                pool[k].update({(st, i): x for i, x in v.items()})
        f = lambda X: f"{100*sum(x for x, _ in X.values())/len(X):5.1f}% {sum(t for _, t in X.values())/len(X)/1000:5.2f}k {sum(U(*x) for x in X.values())/len(X):6.2f}"
        print(f"{st:9s} " + "  ".join(f"{k} {f(v)}" for k, v in row.items() if len(v) == len(P)))
    print(f"JUDGE right on resolvable disagreements: {right_res} of {res} ({100*right_res/max(1,res):.0f}%)")
    for ks, lab in ((list(pool["A"]), "all 12 sets"),):
        for k in ("JUDGE", "VOTE", "A2"):
            ids = [i for i in ks if i in pool[k]]
            mA, mB = sum(U(*pool["A"][i]) for i in ids), sum(U(*pool["B"][i]) for i in ids); best = "A" if mA >= mB else "B"
            print(f"{k:6s} pooled n={len(ids)} (best single {best}): accuracy {100*sum(pool[k][i][0] for i in ids)/len(ids):.1f}% vs A {100*sum(pool['A'][i][0] for i in ids)/len(ids):.1f}% B {100*sum(pool['B'][i][0] for i in ids)/len(ids):.1f}%;"
                  f" tokens {sum(pool[k][i][1] for i in ids)/len(ids)/1000:.2f}k vs A {sum(pool['A'][i][1] for i in ids)/len(ids)/1000:.2f}k B {sum(pool['B'][i][1] for i in ids)/len(ids)/1000:.2f}k")
            print(f"        {k} − {best}: accuracy {ci([100*(pool[k][i][0]-pool[best][i][0]) for i in ids])}  utility {ci([U(*pool[k][i])-U(*pool[best][i]) for i in ids])}")


if __name__ == "__main__":
    {"run": lambda: run(sys.argv[2:]), "runc": lambda: runc(sys.argv[2:]), "score": score, "scorec": scorec, "scorec2": scorec2}[sys.argv[1]]()
