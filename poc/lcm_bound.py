"""LCM addendum B (docs/prereg/PREREG_LCM.md): how much any policy over one seed's five calls (quick, the peer's quick, short think,
think, retry think) can gain over the hand-set cascade when the joint law of their outcomes is known instead of modelled. The
"supervised planner": on one half of a cell's questions (crc32(id) mod 2), with all labels, the empirical law of every partial
observation pattern (which calls were made, which of their answers coincide, their checks) — the next call's outcome given the pattern,
and the chance that each observed answer is right — then the Bayes-optimal stop / call policy under that law by dynamic programming,
executed on the other half (cross-fitting both ways). A question-seed that reaches a pattern never seen on the fitting half is
scored with the cascade's own outcome (counted and reported; it can only pull the planner toward the cascade). It is an estimate of the information limit of these five calls: if it cannot beat the cascade,
no model-based planner can, and the cascade has used what the calls carry.
usage: python3 lcm_bound.py <task> <generator> <peer> <set>   -> results/lcm_bound/<task>_<set>_<generator>_<peer>.json"""
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
    pat = tuple(obs[j] if j in calls else None for j in range(5))
    m, out = {}, []
    for e in pat:
        if e is None or e[0] == "X":
            out.append(e)
        else:
            m.setdefault(e[0], len(m)); out.append((m[e[0]], e[1]))
    return tuple(out), frozenset(m[g] for g in right if g in m)


class Supervised:
    def __init__(self, rows, tok):
        """rows: (obs, right) per question-seed of the fitting half; tok: mean tokens per call index"""
        self.n, self.nxt, self.r, self.tok = {}, {}, {}, tok
        for obs, right in rows:
            for r in range(6):
                for calls in itertools.combinations(range(5), r):
                    cs = frozenset(calls)
                    pat, rt = project(obs, right, cs)
                    self.n[pat] = self.n.get(pat, 0) + 1
                    for g in rt:
                        self.r[(pat, g)] = self.r.get((pat, g), 0) + 1
                    for j in range(5):
                        if j not in cs:
                            nxt, _ = project(obs, right, cs | {j})
                            self.nxt.setdefault((pat, j), {})
                            self.nxt[(pat, j)][nxt] = self.nxt[(pat, j)].get(nxt, 0) + 1
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
        for j in range(5):
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


def main():
    task, gen, peer, sset = sys.argv[1:5]
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


if __name__ == "__main__":
    main()
