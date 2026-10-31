"""AL (docs/prereg/PREREG_AL.md): a label-efficient pilot — label only the problems where the candidate policies' answers differ.
On a task with an exact grader, two policies that give the same answer on a problem are equally right there, so differences in
accuracy live only on the problems where some candidates' answers differ (share p of the pool, known without labels after running the
arms on the pool); tokens are known without labels everywhere. With k labels drawn from those problems the accuracy differences are
estimated with the variance of k / p random labels.
Per cell (one model on one benchmark, seeds pooled per problem, since a label grades every seed's answer):
  R   the PX pilot: the best utility on k random labelled problems (accuracy and tokens there);
  RP  k random labels for accuracy, tokens from the whole pool;
  TG  k labels drawn uniformly from the pool's problems where the menu's answers differ (all of them if fewer than k), accuracy
      difference = p x the mean there, tokens from the pool;
Primary (split-half): each pilot's pool is a random half of the cell (its labels and tokens come from there) and it is scored on
the other half: regret = that half's best utility - the pick's there (the pool is a sample of the task, as in deployment). Secondary
(in-sample, PX's way): pool = scored set = the cell. 1,000 pilots per cell (the same pools for every k); utility = accuracy - 0.5 x ktokens. Also always using
the default SB->T->T (D).
Menus. Word problems (OptiBench third / BWOR / LogiOR / OptMATH; Qwen3-8B, Qwen3-14B-AWQ, Qwen3.5-9B, Nemotron-3-Nano): peer = {D,
N -> Qwen peer -> D, N -> gpt-oss-20b -> D, PND (gpt-oss-20b also gates SB)}; broad = peer + {T->T, N->T->T}. SQL (BIRD dev and
SQL-PA's fresh questions; Qwen3-8B, Qwen3-14B-AWQ, Qwen3.5-9B): peer = {D, N -> p -> D for every stored peer p (the two other Qwen
models, Nemotron-3-Nano, gpt-oss-20b)}; broad = peer + {T->T, N->T->T}. Answers: word = the printed value (equal within the grader's
tolerance), SQL = the hash of the result rows; a missing answer is its own value. Exactness check: pairs with equal answers and unequal
correctness are counted.
usage: python analyze_al.py [--word] [--sql] [--fresh q8b:q8bob,q14a:q14aob] [--mamo]"""
import contextlib, io, os, random, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
with contextlib.redirect_stdout(io.StringIO()):
    import analyze_hopa as H
    import analyze_xpeer as X
    from analyze_sharp import safe_same

LAM, KS, REPS = 0.5, (10, 30, 100), 1000
VIOL = [0, 0]   # equal answers with unequal correctness, equal-answer pairs


def same(a, b):
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, str) and a.startswith("h:"):
        return a == b
    try:
        return H.correct(a, str(b))
    except Exception:
        return str(a) == str(b)


def cell(per):
    """per = {problem: {seed: {policy: (answer, right, tokens)}}} -> [{policy: (mean right, mean tokens)}, differs] per problem"""
    out = []
    for i, S in per.items():
        pols = list(next(iter(S.values())))
        diff = False
        for v in S.values():
            for a in pols[1:]:
                if same(v[pols[0]][0], v[a][0]):
                    VIOL[1] += 1; VIOL[0] += v[pols[0]][1] != v[a][1]
                else:
                    diff = True
        out.append(({p: (sum(v[p][1] for v in S.values()) / len(S), sum(v[p][2] for v in S.values()) / len(S)) for p in pols}, diff))
    return out


def simulate(name, C, rng, default="D", split=True):
    """regret of R / RP / TG for k in KS on one cell. split (primary): each pilot sees a random half of the cell as its pool (labels
    and tokens from there) and is scored on the other half against that half's best; else the PX way, pool = scored set = the cell.
    The same pool serves every k. Returns {method: {k: regret}}, always-D regret, p (share of the cell's problems where the menu's
    answers differ), the cell's best policy"""
    pols = list(C[0][0])
    R = [[c[0][q][0] for q in pols] for c in C]                          # mean right per problem and policy
    K = [[LAM * c[0][q][1] / 1000 for q in pols] for c in C]             # utility cost of the tokens
    dif = [c[1] for c in C]
    P, d0 = range(len(pols)), pols.index(default)
    mean = lambda I, A: [sum(A[i][q] for i in I) / len(I) for q in P]
    Uc = [100 * a - b for a, b in zip(mean(range(len(C)), R), mean(range(len(C)), K))]
    res, dreg = {m: {k: 0.0 for k in KS} for m in ("R", "RP", "TG")}, 0.0
    idx = list(range(len(C)))
    for _ in range(REPS):
        if split:
            rng.shuffle(idx); pool, ev = idx[:len(C) // 2], idx[len(C) // 2:]
        else:
            pool = ev = idx
        Ue = [100 * a - b for a, b in zip(mean(ev, R), mean(ev, K))]; best = max(Ue)
        dreg += best - Ue[d0]
        tokp = mean(pool, K)
        Dset = [i for i in pool if dif[i]]
        p = len(Dset) / len(pool)
        arg = lambda e: max(P, key=lambda q: e[q])
        for k in KS:
            S = rng.sample(pool, min(k, len(pool)))
            rs, ks = mean(S, R), mean(S, K)
            res["R"][k] += best - Ue[arg([100 * a - b for a, b in zip(rs, ks)])]
            res["RP"][k] += best - Ue[arg([100 * a - b for a, b in zip(rs, tokp)])]
            L = Dset if len(Dset) <= k else rng.sample(Dset, k)
            rl = mean(L, R) if L else [0.0] * len(pols)
            res["TG"][k] += best - Ue[arg([100 * p * a - b for a, b in zip(rl, tokp)])]
    return {m: {k: v / REPS for k, v in r.items()} for m, r in res.items()}, dreg / REPS, sum(dif) / len(C), pols[max(P, key=lambda q: Uc[q])]


def word_cells(N, benches=H.BENCH, fresh=None, qwen=None):
    qwen = qwen or H.PEER[N]
    for b in benches:
        A = H.word_rows(N, b) if not fresh else {"formx": X.formx(N, b), "formxt": X.formx(fresh, b, "formxt"),
                                                  "formxtb2000": X.formx(fresh, b, "formxtb2000")}
        P, Q = X.formx("oss20", b), X.formx(qwen, b)
        F, T, SB = A["formx"], A["formxt"], A["formxtb2000"]
        ids = set.intersection(*(set(Z[s]) for Z in (F, T, SB, P, Q) for s in (1, 2, 3)))
        per = {}
        for s in (1, 2, 3):
            s2 = s % 3 + 1
            for i in ids:
                f, sb, t, t2, p, q = F[s][i], SB[s][i], T[s][i], T[s2][i], P[s][i], Q[s][i]
                x = lambda r, tok: (r[3], r[1], tok)   # (answer, right, tokens)
                tt = x(t, t[2]) if t[0] else x(t2, t[2] + t2[2])
                d = x(sb, sb[2]) if sb[0] else (tt[0], tt[1], sb[2] + tt[2])
                aq, ao, asb = f[0] and safe_same(f, q), f[0] and safe_same(f, p), sb[0] and safe_same(sb, p)
                pq = x(f, f[2] + q[2]) if aq else (d[0], d[1], f[2] + (q[2] if f[0] else 0) + d[2])
                po = x(f, f[2] + p[2]) if ao else (d[0], d[1], f[2] + (p[2] if f[0] else 0) + d[2])
                if ao:
                    pnd = po
                elif sb[0]:
                    pnd = x(sb, f[2] + p[2] + sb[2]) if asb else (tt[0], tt[1], f[2] + p[2] + sb[2] + tt[2])
                else:
                    pnd = (tt[0], tt[1], f[2] + (p[2] if f[0] else 0) + sb[2] + tt[2])
                nt = x(f, f[2]) if f[0] else (tt[0], tt[1], f[2] + tt[2])
                per.setdefault(f"{b}/{i}", {})[s] = {"D": d, "PEER_q": pq, "PEER_o": po, "PND_o": pnd, "T->T": tt, "N->T->T": nt}
        yield f"{N} {b}", per


def sql_cells(A):
    import analyze_sqlpa as S
    from analyze_cv import base
    others = [m for m in ("q8b", "q14a", "q35", "n3n", "oss20") if m != A]
    for dev in (True, False):
        sfx = "" if dev else "pa"
        GA, KA = S.grades(A + sfx), S.ntok(A + sfx)
        G = {m: S.grades(m + sfx) for m in others}; K = {m: S.ntok(m + sfx) for m in others}
        per = {}
        for (i, s), v in base(A + sfx).items():
            s2 = s % 3 + 1
            g, g2 = GA[s][i], GA[s2][i]
            key = lambda r: "h:" + r["h"] if r.get("h") else None
            tt = (key(g["T"]), g["T"]["ok"], v["T->T"][1]) if g["T"]["chk"] == "pass" else (key(g2["T"]), g2["T"]["ok"], v["T->T"][1])
            sb = g["SB"]
            d = (key(sb), sb["ok"], v["SB->T->T"][1]) if sb["chk"] == "pass" else (tt[0], tt[1], v["SB->T->T"][1])
            n, kn = g["N"], KA[s][i]
            row = {"D": d, "T->T": tt, "N->T->T": (key(n), n["ok"], kn) if n["chk"] == "pass" else (tt[0], tt[1], kn + tt[2])}
            for m in others:
                o, kp = G[m][s].get(i, {}).get("N", {}), K[m][s].get(i, 0)
                ag = n["chk"] == "pass" and o.get("chk") == "pass" and o.get("h") == n["h"]
                row[f"PEER_{m}"] = (key(n), n["ok"], kn + kp) if ag else (d[0], d[1], kn + (kp if n["chk"] == "pass" else 0) + d[2])
            per.setdefault(i, {})[s] = row
        yield f"{A} {'dev' if dev else 'fresh'}", {i: S_ for i, S_ in per.items() if len(S_) == 3}


def run(title, cells, menus):
    rng = random.Random(0)
    for (mname, keep), split in [(x, s) for x in menus.items() for s in (True, False)]:
        tot, n = {m: {k: 0.0 for k in KS} for m in ("R", "RP", "TG")}, 0
        dreg, wins = 0.0, {k: 0 for k in KS}
        title_ = f"{title} [{'split-half' if split else 'in-sample'}]"
        print(f"=== {title_}, menu {mname}")
        for name, per in cells:
            per = {i: {s: {p: v[p] for p in keep(v)} for s, v in S.items()} for i, S in per.items()}
            res, dr, p, b = simulate(name, cell(per), rng, split=split)
            n += 1; dreg += dr
            for m in res:
                for k in KS:
                    tot[m][k] += res[m][k]
            for k in KS:
                wins[k] += res["TG"][k] < res["RP"][k]
            print(f"  {name:>18} (p {100 * p:.0f}%, best {b}): always D {dr:.2f} | " + " | ".join(
                f"{m} " + "/".join(f"{res[m][k]:.2f}" for k in KS) for m in res))
        print(f"  *** {title_} {mname}: {n} cells; mean regret (k = {'/'.join(map(str, KS))}): always D {dreg / n:.2f} | " + " | ".join(
            f"{m} " + "/".join(f"{tot[m][k] / n:.2f}" for k in KS) for m in tot)
            + f" | TG < RP in " + "/".join(f"{wins[k]}" for k in KS) + f" of {n} cells | TG-30 / RP-30 {tot['TG'][30] / max(1e-9, tot['RP'][30]):.2f}")


def main():
    H.SAME_FN = H.same_word
    word = {"peer": lambda v: ("D", "PEER_q", "PEER_o", "PND_o"), "broad": lambda v: ("D", "PEER_q", "PEER_o", "PND_o", "T->T", "N->T->T")}
    sql = {"peer": lambda v: ["D"] + [p for p in v if p.startswith("PEER_")], "broad": lambda v: list(v)}
    if "--word" in sys.argv:
        run("word problems", [c for N in ("q8b", "q14a", "q35", "n3n") for c in word_cells(N)], word)
    if "--sql" in sys.argv:
        run("SQL", [c for A in ("q8b", "q14a", "q35") for c in sql_cells(A)], sql)
    if "--fresh" in sys.argv:
        specs = [x.split(":") for x in sys.argv[sys.argv.index("--fresh") + 1].split(",")]
        run("fresh OptiBench", [c for N, tag in specs for c in word_cells(N, ("optibench",), fresh=tag)], word)
    if "--mamo" in sys.argv:
        run("MAMO", [c for N, q in (("q8b", "q14a"), ("q14a", "q8b")) for c in word_cells(N, ("mamo",), qwen=q)], word)
    print(f"exactness: {VIOL[0]} of {VIOL[1]} equal-answer pairs differ in correctness")


if __name__ == "__main__":
    main()
