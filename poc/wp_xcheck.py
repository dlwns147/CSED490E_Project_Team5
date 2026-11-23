"""PREREG_DIFF addendum WP (2026-11-23): own vs cross-family solution checker on word problems (BWOR, LogIOR, OptMATH; seeds 1-3).
Per solver A in {q8b, oss20}: A's freev solutions; own checker verify_<A>_<set>; cross checker verify_<B>_on_<A>_<set>.
Reports false-alarm / catch rates and the FF-V policy (accept the freev answer if the checker passes, else A's think) with each checker.
usage: python3 poc/wp_xcheck.py"""
import json, os, random
R = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "x3")
U = lambda ok, t: 100 * ok - 0.5 * t / 1000
rows = lambda p: {json.loads(l)["id"]: json.loads(l) for l in open(p)} if os.path.exists(p) else {}
T = lambda v: str(v) == "True"


def boot(d):
    ids = list(d); rng = random.Random(1); B = 4000; n = len(ids)
    bs = sorted(sum(d[rng.choice(ids)] for _ in ids) / n for _ in range(B))
    return sum(d.values()) / n, bs[int(.025 * B)], bs[int(.975 * B) - 1], (sum(x <= 0 for x in bs) + 1) / (B + 1)


def per_problem(keys, pol):
    g = {}
    for k in keys:
        g.setdefault(k[0], []).append(pol["cross"][k] - pol["own"][k])
    return {i: sum(v) / len(v) for i, v in g.items()}


for A, B_ in (("q8b", "oss20"), ("oss20", "q8b")):
    stats = {"own": [0, 0, 0, 0], "cross": [0, 0, 0, 0]}   # right&flag, right, wrong&caught, wrong
    pol = {"own": {}, "cross": {}}
    for st in ("bwor", "logior", "optmath"):
        for s in (1, 2, 3):
            F = rows(f"{R}/opt_{A}_{st}_freev_s{s}.jsonl"); K = rows(f"{R}/opt_{A}_{st}_thinkfree_s{s}.jsonl")
            chk = {"own": rows(f"{R}/verify_{A}_{st}_s{s}.jsonl"), "cross": rows(f"{R}/verify_{B_}_on_{A}_{st}_s{s}.jsonl")}
            for i, f in F.items():
                if i not in K:
                    continue
                ok = T(f.get("correct")); tf = int(f.get("out_tokens") or 0)
                runs = f.get("status") == "ok" and f.get("pred") not in (None, "NBS") and f.get("solution")
                for nm, Cc in chk.items():
                    if runs and i not in Cc:
                        continue
                    c = Cc.get(i)
                    passed = bool(runs and c and T(c.get("passed")))
                    if runs:
                        st_ = stats[nm]
                        if ok:
                            st_[1] += 1; st_[0] += not passed
                        else:
                            st_[3] += 1; st_[2] += not passed
                    tc = int(c.get("out_tokens") or 0) if c else 0
                    u = U(ok, tf + tc) if passed else U(T(K[i].get("correct")), tf + tc + int(K[i].get("out_tokens") or 0))
                    pol[nm][(i, s)] = u
    keys = [k for k in pol["own"] if k in pol["cross"]]
    for nm, (fa, r, ca, w) in stats.items():
        print(f"solver {A}, {nm} checker: false alarms on right {fa}/{r} ({100*fa/max(r,1):.0f}%), catches wrong {ca}/{w} ({100*ca/max(w,1):.0f}%)")
    print(f"  FF-V utility: own {sum(pol['own'][k] for k in keys)/len(keys):.2f}  cross {sum(pol['cross'][k] for k in keys)/len(keys):.2f}  "
          f"cross - own %+.2f [%+.2f, %+.2f] p=%.4f  (n={len(keys)}, clustered by problem)" % boot(per_problem(keys, pol)))
