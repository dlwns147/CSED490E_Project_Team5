"""SQL-PA (docs/prereg/PREREG_SQL.md, addendum SQL-PA): another model's quick query as the check. Per model A: A's non-thinking query
(N) -> the free check -> a peer's N on the same question and seed returns the same rows: answer with A's query; else A's T->T (as
SQL-1). Against A's T->T and the no-label default SB->T->T (poc/analyze_cv.py's base(): SQL-1's policies and question filter), paired
95% intervals over questions (seed means); utility = accuracy - 0.5 x ktokens, the peer's tokens counted.
Error coincidence: of A's passing wrong N queries where the other query also passes and is wrong, the share returning the same rows;
the other query: A's N at the next seed (s mod 3 + 1), A's SB, each other model's N (same seed). Differences: bootstrap over questions.
usage: python analyze_sqlpa.py [--dev]   (default: the fresh BIRD-train questions, tags q8bpa / q14apa / q35pa / n3npa;
  --dev: SQL-1's dev rows, tags q8b / q14a / q35 / n3n)"""
import json, os, random, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyze_cv import RES, base, per_q  # noqa: E402
from analyze_ho3 import ci  # noqa: E402
from run_nlopt import _rows  # noqa: E402

PEER = {"q8b": "q35", "q14a": "q35", "q35": "q8b"}   # pre-registered: the other generation (Qwen3 <-> Qwen3.5)
SAME = {"q8b": "q14a", "q14a": "q8b"}                # the same generation (Qwen3)
MODELS = ("q8b", "q14a", "q35", "n3n")


def grades(tag):
    out = {}
    for s in (1, 2, 3):
        p = f"{RES}/grades_{tag}_s{s}.json"
        if not os.path.exists(p):
            return None
        g = json.load(open(p)); g.pop("_gold_fail", None); out[s] = g
    return out


def ntok(tag):
    return {s: {r["id"]: r["n_tok"] for r in _rows(f"{RES}/{tag}_cheap_s{s}.jsonl")} for s in (1, 2, 3)}


def cascade(B, GA, KA, GP, KP):
    """{(id, seed): (right, tokens)}: A's N; failed check -> T->T; passing -> the peer's N; same rows -> answer, else T->T"""
    rows = {}
    for (i, s), v in B.items():
        n, k, tto = GA[s][i]["N"], KA[s][i], v["T->T"]
        if n["chk"] != "pass":
            rows[(i, s)] = (tto[0], k + tto[1])
            continue
        o, kp = GP[s].get(i, {}).get("N", {}), KP[s].get(i, 0)
        rows[(i, s)] = (n["ok"], k + kp) if o.get("chk") == "pass" and o.get("h") == n["h"] else (tto[0], k + kp + tto[1])
    return rows


def coincide(GA, other):
    """{id: [same rows, pairs]} over seeds: A's passing wrong N against another passing wrong query (other(s, i) -> its grade)"""
    out = {}
    for s in (1, 2, 3):
        for i, v in GA[s].items():
            n = v.get("N")
            if not n or n["chk"] != "pass" or n["ok"]:
                continue
            o = other(s, i)
            if not o or o.get("chk") != "pass" or o["ok"]:
                continue
            x = out.setdefault(i, [0, 0]); x[0] += o.get("h") == n["h"]; x[1] += 1
    return out


def rate(d, qs):
    return 100 * sum(d[i][0] for i in qs if i in d) / max(1, sum(d[i][1] for i in qs if i in d))


def boot_diff(a, b, n=2000):
    qs, rng = sorted(set(a) | set(b)), random.Random(0)
    bs = sorted(rate(a, q) - rate(b, q) for q in ([rng.choice(qs) for _ in qs] for _ in range(n)))
    return rate(a, qs) - rate(b, qs), bs[int(0.025 * n)], bs[int(0.975 * n) - 1]


def main():
    dev = "--dev" in sys.argv
    tag = {m: m if dev else m + "pa" for m in MODELS}
    G = {m: grades(tag[m]) for m in MODELS}
    K = {m: ntok(tag[m]) for m in MODELS if G[m]}
    print(f"=== SQL-PA, {'BIRD dev (SQL-1)' if dev else 'fresh BIRD-train questions'}; missing: {[m for m in MODELS if not G[m]]}")
    pa1 = pa2 = 0
    for A, P in PEER.items():
        if not (G[A] and G[P]):
            continue
        B = base(tag[A])
        pol = {k: {key: v[k] for key, v in B.items()} for k in ("T->T", "SB->T->T", "N->T->T")}
        for name, p in (("peer", P), ("same generation", SAME.get(A)), ("other family", "n3n")):
            if p and G.get(p):
                pol[f"N->{p}->T->T ({name})"] = cascade(B, G[A], K[A], G[p], K[p])
        ids = {i for i, _ in B}
        Q = {k: per_q(r) for k, r in pol.items()}
        tok = {k: sum(v[1] for v in r.values()) / len(r) for k, r in pol.items()}
        print(f"--- {A} ({len(ids)} questions, 3 seeds)")
        for k, r in pol.items():
            a = 100 * sum(v[0] for v in r.values()) / len(r)
            line = f"  {k:>34}: {a:.1f}% @ {tok[k] / 1000:.2f}k, utility {a - 0.5 * tok[k] / 1000:.1f}"
            if k.startswith("N->") and k != "N->T->T":
                da = ci({i: Q[k][i][0] - Q["T->T"][i][0] for i in ids})
                du = ci({i: Q[k][i][1] - Q["SB->T->T"][i][1] for i in ids})
                line += (f" | vs T->T acc {da[0]:+.1f} [{da[1]:+.1f}, {da[2]:+.1f}] at {100 * tok[k] / tok['T->T']:.0f}% of its tokens;"
                         f" vs SB->T->T utility {du[0]:+.1f} [{du[1]:+.1f}, {du[2]:+.1f}]")
                if "(peer)" in k:
                    pa1 += da[2] >= 0 and tok[k] <= 0.9 * tok["T->T"]
                    pa2 += du[1] > 0
            print(line)
    print(f"*** SQL-PA1 {pa1} of 3 (needs 2); SQL-PA2 {pa2} of 3 (needs 2)")
    pa3 = pa4 = 0
    for A in PEER:
        if not G[A]:
            continue
        src = {"own N, next seed": lambda s, i, A=A: G[A][s % 3 + 1].get(i, {}).get("N"),
               "own SB": lambda s, i, A=A: G[A][s].get(i, {}).get("SB")}
        for o in MODELS:
            if o != A and G[o]:
                src[f"{o} N"] = lambda s, i, o=o: G[o][s].get(i, {}).get("N")
        C = {k: coincide(G[A], f) for k, f in src.items()}
        print(f"--- {A}: error coincidence (same rows among both-wrong passing pairs)")
        for k, d in C.items():
            print(f"  {k:>18}: {rate(d, list(d)):.0f}% (n {sum(x[1] for x in d.values())})")
        if A in SAME and G[SAME[A]] and G[PEER[A]]:
            for a, b in (("own N, next seed", "own SB"), (f"{SAME[A]} N", f"{PEER[A]} N")):
                mu, lo, hi = boot_diff(C[a], C[b])
                print(f"  {a} - {b}: {mu:+.1f} [{lo:+.1f}, {hi:+.1f}]")
                pa3 += lo > 0
        if G["n3n"] and G[PEER[A]]:
            mu, lo, hi = boot_diff(C["n3n N"], C[f"{PEER[A]} N"])
            print(f"  n3n N - {PEER[A]} N: {mu:+.1f} [{lo:+.1f}, {hi:+.1f}]")
            pa4 += hi < 0
    print(f"*** SQL-PA3 {pa3} of 4 (needs 4); SQL-PA4 {pa4} of 3 (needs 2)")


if __name__ == "__main__":
    main()
