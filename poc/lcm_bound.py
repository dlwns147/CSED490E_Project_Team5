"""LCM addendum B (docs/prereg/PREREG_LCM.md): how much any policy over one seed's five calls (quick, the peer's quick, short think,
think, retry think) can gain over the hand-set cascade when the joint law of their outcomes is known instead of modelled. The
"supervised planner": on one half of a cell's questions (crc32(id) mod 2), with all labels, the empirical law of every partial
observation pattern (which calls were made, which of their answers coincide, their checks) — the next call's outcome given the pattern,
and the chance that each observed answer is right — then the Bayes-optimal stop / call policy under that law by dynamic programming,
executed on the other half (cross-fitting both ways). A question-seed that reaches a pattern never seen on the fitting half is
scored with the cascade's own outcome (counted and reported; it can only pull the planner toward the cascade). It is an estimate of the information limit of these five calls: if it cannot beat the cascade,
no model-based planner can, and the cascade has used what the calls carry.
usage: python3 lcm_bound.py <task> <generator> <peer> <set>   -> results/lcm_bound/<task>_<set>_<generator>_<peer>.json
  B2: python3 lcm_bound.py sql <generator> - <dev|fresh|spider> --peers p1,p2,p3   (the first peer is the cascade's)
  J: python3 lcm_bound.py sql <generator> <peer> <dev|spider> --judge <name>   (poc/judge_sql.py's rows)"""
import itertools, json, os, sys, zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lcm  # noqa: E402

LAM = lcm.LAM


def full(sc):
    """the five calls' observations: per call (group id in call order, check) or ('X', check); the set of right group ids"""
    keys, obs, right = {}, [], set()
    for k, c, o, t in sc:
        if k is None:
            obs.append(("X", c))
        else:
            keys.setdefault(k, len(keys)); obs.append((keys[k], c))
            if o:
                right.add(keys[k])
    return tuple(obs), frozenset(right)


def project(obs, right, calls):
    """the pattern seen after making `calls` (a frozenset of call indices), canonical; and which of its groups are right"""
    pat = tuple(obs[j] if j in calls else None for j in range(len(obs)))
    m, out = {}, []
    for e in pat:
        if e is None or e[0] == "X":
            out.append(e)
        else:
            m.setdefault(e[0], len(m)); out.append((m[e[0]], e[1]))
    return tuple(out), frozenset(m[g] for g in right if g in m)


class Supervised:
    def __init__(self, rows, tok, w=None):
        """rows: (obs, right) per question-seed of the fitting half; tok: mean tokens per call index; w: a weight per row (addendum
        LS: importance weights of the labelled rows of other problem sets; rows of weight 0 are left out)"""
        self.n, self.nxt, self.r, self.tok = {}, {}, {}, tok
        C = len(tok)
        for k, (obs, right) in enumerate(rows):
            wt = 1 if w is None else w[k]
            if wt <= 0:
                continue
            for r in range(C + 1):
                for calls in itertools.combinations(range(C), r):
                    cs = frozenset(calls)
                    pat, rt = project(obs, right, cs)
                    self.n[pat] = self.n.get(pat, 0) + wt
                    for g in rt:
                        self.r[(pat, g)] = self.r.get((pat, g), 0) + wt
                    for j in range(C):
                        if j not in cs:
                            nxt, _ = project(obs, right, cs | {j})
                            self.nxt.setdefault((pat, j), {})
                            self.nxt[(pat, j)][nxt] = self.nxt[(pat, j)].get(nxt, 0) + wt
        self.V, self.act = {}, {}

    def stop(self, pat):
        gids = sorted({e[0] for e in pat if e is not None and e[0] != "X"})
        n = self.n.get(pat, 0)
        if not gids or not n:
            return 0.0, None
        p = {g: self.r.get((pat, g), 0) / n for g in gids}
        g = max(p, key=p.get)
        return p[g], g

    def value(self, pat):
        if pat in self.V:
            return self.V[pat]
        best = self.stop(pat) + (None,)
        best = (best[0], ("stop", best[1]))
        for j in range(len(self.tok)):
            if pat[j] is not None or (pat, j) not in self.nxt:
                continue
            D = self.nxt[(pat, j)]; tot = sum(D.values())
            v = -LAM / 100 * self.tok[j] / 1000 + sum(c / tot * self.value(q) for q, c in D.items())
            if v > best[0] + 1e-12:
                best = (v, ("call", j))
        self.V[pat], self.act[pat] = best
        return best[0]

    def run(self, sc):
        obs, right = full(sc)
        calls, tok = frozenset(), 0
        while True:
            pat, rt = project(obs, right, calls)
            if pat not in self.n:   # never seen on the fitting half: the caller scores the cascade's outcome instead
                return False, tok, False
            self.value(pat)
            kind, arg = self.act[pat]
            if kind == "stop":
                return (arg in rt) if arg is not None else False, tok, True
            calls = calls | {arg}; tok += sc[arg][3]


def extra_calls(gen, peers, sset):
    """B2: SQL, one seed's calls N, P1 .. Pm (each peer's quick query, same seed), SB, T, retry T; {id: {seed: [(key, check, ok, tok)]}}"""
    from analyze_sqlpa import grades, ntok
    suf = {"dev": "", "fresh": "pa", "spider": "sp"}[sset]
    Q = lcm.load("sql", gen, peers[0], sset)
    G = {p: grades(p + suf) for p in peers}; K = {p: ntok(p + suf) for p in peers}
    out = {}
    for i, q in Q.items():
        if not all(G[p] and i in G[p][s] and "N" in G[p][s][i] and i in K[p][s] for p in peers for s in (1, 2, 3)):
            continue
        out[i] = {}
        for s in (1, 2, 3):
            N, P, SB, T, T2 = lcm.seed_calls(q, s)
            ex = [(G[p][s][i]["N"]["h"], G[p][s][i]["N"]["chk"] == "pass", bool(G[p][s][i]["N"]["ok"]), K[p][s][i] or 0) for p in peers[1:]]
            out[i][s] = [N, P] + ex + [SB, T, T2]
    return out


def main_judge(gen, peer, sset, name):
    """addendum J: the supervised planner over N, P, the judge's verdict on N (J; a non-answer observation, yes / no as its bit),
    SB, T, retry T, against the same planner without J (B) and the cascade; the judge's AUROC on passing N"""
    from analyze_ho3 import ci
    from run_nlopt import _rows
    suf = {"dev": "", "fresh": "pa", "spider": "sp"}[sset]
    Q = lcm.load("sql", gen, peer, sset)
    J = {s: {r["id"]: r for r in _rows(os.path.join(lcm.ROOT, "results", "sql", f"judge_{name}_{gen}{suf}_s{s}.jsonl"))} for s in (1, 2, 3)}
    ids = sorted(i for i in Q if all(i in J[s] for s in (1, 2, 3)))
    calls = {}
    for i in ids:
        calls[i] = {}
        for s in (1, 2, 3):
            N, P, SB, T, T2 = lcm.seed_calls(Q[i], s)
            v = J[s][i]["verdict"]
            calls[i][s] = [N, P, (None, bool(v), False, 1), SB, T, T2]
    pos = [J[s][i]["p_yes"] for i in ids for s in (1, 2, 3) if J[s][i]["p_yes"] is not None and lcm.seed_calls(Q[i], s)[0][2]]
    neg = [J[s][i]["p_yes"] for i in ids for s in (1, 2, 3) if J[s][i]["p_yes"] is not None and not lcm.seed_calls(Q[i], s)[0][2]]
    allv = sorted([(v, 1) for v in pos] + [(v, 0) for v in neg])
    rank = {}; k = 0
    while k < len(allv):
        j = k
        while j < len(allv) and allv[j][0] == allv[k][0]:
            j += 1
        for t in range(k, j):
            rank[t] = (k + j - 1) / 2 + 1
        k = j
    rsum = sum(rank[t] for t, (v, lab) in enumerate(allv) if lab)
    auc = (rsum - len(pos) * (len(pos) + 1) / 2) / max(1, len(pos) * len(neg))
    half = {h: [i for i in ids if zlib.crc32(i.encode()) % 2 == h] for h in (0, 1)}
    five = lambda sc: [sc[0], sc[1], sc[3], sc[4], sc[5]]
    U = {"judge": {}, "five": {}, "cascade": {}, "judge_cascade": {}}
    for h in (0, 1):
        for nm, sel in (("judge", lambda sc: sc), ("five", five)):
            rows = [full(sel(calls[i][s])) for i in half[h] for s in (1, 2, 3)]
            C = len(sel(calls[half[h][0]][1]))
            tok = [sum(sel(calls[i][s])[j][3] for i in half[h] for s in (1, 2, 3)) / (3 * len(half[h])) for j in range(C)]
            S = Supervised(rows, tok)
            for i in half[1 - h]:
                u = 0.0
                for s in (1, 2, 3):
                    ok, t, seen = S.run(sel(calls[i][s]))
                    if not seen:
                        ok, t = lcm.fixed("cascade", five(calls[i][s]))
                    u += 100 * float(ok) - LAM * t / 1000
                U[nm][i] = u / 3
        for i in half[1 - h]:
            c = jc = 0.0
            for s in (1, 2, 3):
                sc = calls[i][s]
                r, t = lcm.fixed("cascade", five(sc)); c += 100 * float(r) - LAM * t / 1000
                N, SB, T, T2 = sc[0], sc[3], sc[4], sc[5]   # the judge cascade: N if it passes and the judge says yes, else SB->T->T
                if N[1] and sc[2][1]:
                    r2, t2 = N[2], N[3] + 1
                else:
                    r2, t2 = lcm.fixed("SB->T->T", five(sc)); t2 += N[3] + (1 if N[1] else 0)
                jc += 100 * float(r2) - LAM * t2 / 1000
            U["cascade"][i], U["judge_cascade"][i] = c / 3, jc / 3
    d = lambda a, b: ci({i: (U[a][i] - U[b][i]) / 100 for i in ids})
    rec = dict(task=f"sql {sset} {gen}<-{peer} judge {name}", n=len(ids), auroc=auc, **{k: sum(v.values()) / len(ids) for k, v in U.items()},
               judge_vs_five=d("judge", "five"), judge_vs_cascade=d("judge", "cascade"), jcas_vs_cascade=d("judge_cascade", "cascade"))
    f = lambda v: f"{v[0]:+.2f} [{v[1]:+.2f}, {v[2]:+.2f}]"
    print(f"*** {rec['task']} ({len(ids)} questions): judge AUROC on passing N {auc:.3f}; planner with the judge {rec['judge']:+.2f}, "
          f"without {rec['five']:+.2f}, cascade {rec['cascade']:+.2f}, judge cascade {rec['judge_cascade']:+.2f}; with - without "
          f"{f(rec['judge_vs_five'])}; with - cascade {f(rec['judge_vs_cascade'])}; judge cascade - cascade {f(rec['jcas_vs_cascade'])}",
          flush=True)
    od = os.path.join(lcm.ROOT, "results", "lcm_bound")
    os.makedirs(od, exist_ok=True)
    json.dump(rec, open(f"{od}/judge_{name}_sql_{sset}_{gen}.json", "w"))


def main():
    task, gen, peer, sset = sys.argv[1:5]
    if "--judge" in sys.argv:   # addendum J
        return main_judge(gen, peer, sset, sys.argv[sys.argv.index("--judge") + 1])
    if "--peers" in sys.argv:   # B2: the bound with more peers' quick queries (SQL)
        return main_b2(gen, sys.argv[sys.argv.index("--peers") + 1].split(","), sset)
    Q = lcm.load(task, gen, peer, sset)
    ids = sorted(Q)
    half = {h: [i for i in ids if zlib.crc32(i.encode()) % 2 == h] for h in (0, 1)}
    per, cas, unseen = {}, {}, 0
    for h in (0, 1):
        rows = [full(lcm.seed_calls(Q[i], s)) for i in half[h] for s in (1, 2, 3)]
        tok = [sum(lcm.seed_calls(Q[i], s)[j][3] for i in half[h] for s in (1, 2, 3)) / (3 * len(half[h])) for j in range(5)]
        S = Supervised(rows, tok)
        for i in half[1 - h]:
            u, c = 0.0, 0.0
            for s in (1, 2, 3):
                sc = lcm.seed_calls(Q[i], s)
                ok, t, seen = S.run(sc)
                if not seen:   # back off: the cascade's own answer for this question-seed
                    ok, t = lcm.fixed("cascade", sc); unseen += 1
                u += 100 * float(ok) - LAM * t / 1000
                r, t2 = lcm.fixed("cascade", sc)
                c += 100 * float(r) - LAM * t2 / 1000
            per[i], cas[i] = u / 3, c / 3
    from analyze_ho3 import ci
    d = ci({i: (per[i] - cas[i]) / 100 for i in ids})
    rec = dict(task=f"{task} {sset} {gen}<-{peer}", n=len(ids), supervised=sum(per.values()) / len(ids), cascade=sum(cas.values()) / len(ids),
               vs_cascade=d, unseen=unseen)
    print(f"*** {rec['task']} ({len(ids)} questions): supervised planner {rec['supervised']:+.2f}, cascade {rec['cascade']:+.2f}, "
          f"difference {d[0]:+.2f} [{d[1]:+.2f}, {d[2]:+.2f}]; question-seeds on an unseen pattern {unseen}", flush=True)
    od = os.path.join(lcm.ROOT, "results", "lcm_bound")
    os.makedirs(od, exist_ok=True)
    json.dump(rec, open(f"{od}/{task}_{sset}_{gen}_{peer}.json", "w"))


def main_b2(gen, peers, sset):
    """B2: the supervised planner over N, the peers' quick queries, SB, T, retry T, against the same planner over the five calls (B)
    and against the cascade (with the first peer), on the same questions"""
    from analyze_ho3 import ci
    D = extra_calls(gen, peers, sset)
    ids = sorted(D)
    half = {h: [i for i in ids if zlib.crc32(i.encode()) % 2 == h] for h in (0, 1)}
    m = len(peers)
    five = lambda sc: [sc[0], sc[1], sc[m + 1], sc[m + 2], sc[m + 3]]
    U = {"many": {}, "five": {}, "cascade": {}}
    for h in (0, 1):
        for name, sel in (("many", lambda sc: sc), ("five", five)):
            rows = [full(sel(D[i][s])) for i in half[h] for s in (1, 2, 3)]
            C = len(sel(D[half[h][0]][1]))
            tok = [sum(sel(D[i][s])[j][3] for i in half[h] for s in (1, 2, 3)) / (3 * len(half[h])) for j in range(C)]
            S = Supervised(rows, tok)
            for i in half[1 - h]:
                u = 0.0
                for s in (1, 2, 3):
                    sc = sel(D[i][s])
                    ok, t, seen = S.run(sc)
                    if not seen:
                        ok, t = lcm.fixed("cascade", five(D[i][s]))
                    u += 100 * float(ok) - LAM * t / 1000
                U[name][i] = u / 3
        for i in half[1 - h]:
            U["cascade"][i] = sum(100 * float(r) - LAM * t / 1000 for r, t in (lcm.fixed("cascade", five(D[i][s])) for s in (1, 2, 3))) / 3
    d = lambda a, b: ci({i: (U[a][i] - U[b][i]) / 100 for i in ids})
    rec = dict(task=f"sql {sset} {gen}<-{'+'.join(peers)}", n=len(ids), **{k: sum(v.values()) / len(ids) for k, v in U.items()},
               many_vs_five=d("many", "five"), many_vs_cascade=d("many", "cascade"), five_vs_cascade=d("five", "cascade"))
    print(f"*** {rec['task']} ({len(ids)} questions): planner with {m} peers {rec['many']:+.2f}, with one {rec['five']:+.2f}, cascade "
          f"{rec['cascade']:+.2f}; more peers - one {rec['many_vs_five'][0]:+.2f} [{rec['many_vs_five'][1]:+.2f}, {rec['many_vs_five'][2]:+.2f}]; "
          f"more peers - cascade {rec['many_vs_cascade'][0]:+.2f} [{rec['many_vs_cascade'][1]:+.2f}, {rec['many_vs_cascade'][2]:+.2f}]", flush=True)
    od = os.path.join(lcm.ROOT, "results", "lcm_bound")
    os.makedirs(od, exist_ok=True)
    json.dump(rec, open(f"{od}/b2_sql_{sset}_{gen}.json", "w"))


if __name__ == "__main__":
    main()
