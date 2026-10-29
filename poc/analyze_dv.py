"""SQL-DV (docs/prereg/PREREG_SQL.md, addendum SQL-DV): where does a check's independence come from? For model A, the check X is a
second quick answer to the same item and seed: A's next-seed answer, A with the schema / function docs shuffled (view s), A with a
one-line plan first (view p), the fixed peer of SQL-PA / HO-PA, Llama-3.1-8B-Instruct, Llama-3.2-3B-Instruct, Qwen3-4B. Per X:
its error coincidence with A (same answer among both-wrong passing pairs) and the cascade N -> X agrees -> A's answer, else SB->T->T
(A's no-label default; tokens include X's), against SB->T->T and against the fixed peer's cascade (paired 95% intervals over items,
seed means; utility = accuracy - 0.5 x ktokens). Text-to-SQL: BIRD dev (SQL-1's rows); tool calls: BFCL (TC-1's rows, both splits).
usage: python analyze_dv.py [--sql | --tc]   (default both)"""
import json, os, random, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_ho3 import ci  # noqa: E402
from run_nlopt import _rows  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PEER = {"q8b": "q35", "q14a": "q35", "q35": "q8b"}
OTHER = {"view s": "{m}vs", "view p": "{m}vp", "Llama-3.1-8B": "l8", "Llama-3.2-3B": "l3", "Qwen3-4B": "q4b"}
LAM = 0.5


def quick(kind, tag):
    """{seed: {id: (passes, right, tokens, answer)}} of a tag's quick answer (N), or None"""
    res = f"{ROOT}/results/{'sql' if kind == 'sql' else 'tc'}"
    out = {}
    for s in (1, 2, 3):
        gp = f"{res}/grades_{tag}_s{s}.json"
        if not os.path.exists(gp):
            return None
        G = json.load(open(gp)); G.pop("_gold_fail", None)
        K = {r["id"]: r["n_tok"] for r in _rows(f"{res}/{tag}_cheap_s{s}.jsonl")}
        if kind == "sql":
            out[s] = {i: (g["N"]["chk"] == "pass", g["N"]["ok"], K.get(i, 0), g["N"]["h"]) for i, g in G.items() if "N" in g}
        else:
            out[s] = {i: (g["N"]["chk"] != "fail", g["N"]["ok"], K.get(i, 0), g["N"]["calls"]) for i, g in G.items() if "N" in g}
    return out


def default(kind, m):
    """{(id, seed): (SB->T->T right, tokens)} for A"""
    if kind == "sql":
        from analyze_cv import base
        return {k: v["SB->T->T"] for k, v in base(m).items()}
    from analyze_hopa import tc_rows
    out = {}
    for split in ("non-live", "live"):
        A = tc_rows(m, split)
        for s in (1, 2, 3):
            s2 = s % 3 + 1
            for i, sb in A["formxtb2000"][s].items():
                t, t2 = A["formxt"][s][i], A["formxt"][s2].get(i)
                if t2 is None:
                    continue
                tt = (t[1], t[2]) if t[0] else (t2[1], t[2] + t2[2])
                out[(i, s)] = (sb[1], sb[2]) if sb[0] else (tt[0], sb[2] + tt[1])
    return out


def same(kind, x, y):
    return x[0] and y[0] and x[3] is not None and x[3] == y[3]


def cascade(kind, D, NA, X):
    out = {}
    for (i, s), d in D.items():
        n, x = NA[s].get(i), X[s].get(i)
        if n is None or x is None:
            continue
        if not n[0]:
            out[(i, s)] = (d[0], n[2] + d[1])
        elif same(kind, n, x):
            out[(i, s)] = (n[1], n[2] + x[2])
        else:
            out[(i, s)] = (d[0], n[2] + x[2] + d[1])
    return out


def per_q(rows):
    acc = {}
    for (i, s), (a, t) in rows.items():
        acc.setdefault(i, []).append((float(a), float(a) - LAM / 100 * t / 1000))
    return {i: (sum(x for x, _ in v) / len(v), sum(u for _, u in v) / len(v)) for i, v in acc.items() if len(v) == 3}


def coincide(kind, NA, X):
    out = {}
    for s in (1, 2, 3):
        for i, n in NA[s].items():
            x = X[s].get(i)
            if n[0] and not n[1] and x and x[0] and not x[1]:
                c = out.setdefault(i, [0, 0]); c[0] += same(kind, n, x); c[1] += 1
    return out


def rate(d, qs):
    return 100 * sum(d[i][0] for i in qs if i in d) / max(1, sum(d[i][1] for i in qs if i in d))


def boot_diff(a, b, n=2000):
    qs, rng = sorted(set(a) | set(b)), random.Random(0)
    bs = sorted(rate(a, q) - rate(b, q) for q in ([rng.choice(qs) for _ in qs] for _ in range(n)))
    return rate(a, qs) - rate(b, qs), bs[int(0.025 * n)], bs[int(0.975 * n) - 1]


def run(kind):
    score = {"self": 0, "small": 0, "family": 0, "family_n": 0, "n": 0}
    for m in ("q8b", "q14a", "q35"):
        NA, D = quick(kind, m), default(kind, m)
        src = {"own, next seed": {s: NA[s % 3 + 1] for s in (1, 2, 3)}, f"peer ({PEER[m]})": quick(kind, PEER[m])}
        src.update({k: quick(kind, t.format(m=m)) for k, t in OTHER.items()})
        missing = [k for k, v in src.items() if v is None]
        src = {k: v for k, v in src.items() if v is not None}
        pol = {"SB->T->T": D}
        pol.update({f"N->{k}->SB->T->T": cascade(kind, D, NA, X) for k, X in src.items()})
        ids = set.intersection(*(set(i for i, _ in r) for r in pol.values()))
        Q = {k: per_q({key: v for key, v in r.items() if key[0] in ids}) for k, r in pol.items()}
        ids = set.intersection(*(set(q) for q in Q.values()))
        print(f"=== {kind} {m} ({len(ids)} items, 3 seeds; missing: {missing})")
        C = {k: coincide(kind, NA, X) for k, X in src.items()}
        pk = f"N->peer ({PEER[m]})->SB->T->T"
        for k, r in pol.items():
            rr = [v for key, v in r.items() if key[0] in ids]
            a, t = 100 * sum(v[0] for v in rr) / len(rr), sum(v[1] for v in rr) / len(rr) / 1000
            line = f"  {k:>34}: {a:.1f}% @ {t:.2f}k, utility {a - LAM * t:.1f}"
            if k != "SB->T->T":
                x = k[3:-10]
                du = ci({i: Q[k][i][1] - Q["SB->T->T"][i][1] for i in ids})
                line += f" | vs SB->T->T {du[0]:+.1f} [{du[1]:+.1f}, {du[2]:+.1f}]; coincidence {rate(C[x], list(C[x])):.0f}% (n {sum(c[1] for c in C[x].values())})"
                if pk in Q and k != pk:
                    dp = ci({i: Q[k][i][1] - Q[pk][i][1] for i in ids})
                    line += f" | vs peer cascade {dp[0]:+.1f} [{dp[1]:+.1f}, {dp[2]:+.1f}]"
                    if x == "view p":
                        score["self"] += dp[1] > -0.5
                    if x == "Llama-3.2-3B":
                        score["small"] += dp[1] > -0.5
            print(line)
        score["n"] += 1
        if m in ("q8b", "q14a") and "Qwen3-4B" in C and "Llama-3.2-3B" in C:
            mu, lo, hi = boot_diff(C["Qwen3-4B"], C["Llama-3.2-3B"]); score["family"] += lo > 0; score["family_n"] += 1
            print(f"  coincidence Qwen3-4B - Llama-3.2-3B: {mu:+.1f} [{lo:+.1f}, {hi:+.1f}]")
        for a, b in (("own, next seed", "view s"), ("own, next seed", "view p"), ("view p", f"peer ({PEER[m]})")):
            if a in C and b in C:
                mu, lo, hi = boot_diff(C[a], C[b])
                print(f"  coincidence {a} - {b}: {mu:+.1f} [{lo:+.1f}, {hi:+.1f}]")
    print(f"*** {kind}: SQL-DV3 plan view non-inferior to the peer (lower bound > -0.5) in {score['self']} of {score['n']}; "
          f"SQL-DV4 Llama-3.2-3B non-inferior in {score['small']} of {score['n']}; SQL-DV5 Qwen3-4B coincides more than Llama-3.2-3B "
          f"in {score['family']} of {score['family_n']}")


if __name__ == "__main__":
    for kind in ("sql", "tc"):
        if f"--{'tc' if kind == 'sql' else 'sql'}" not in sys.argv:
            run(kind)
