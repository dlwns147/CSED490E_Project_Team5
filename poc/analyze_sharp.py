"""SHARP (docs/prereg/PREREG_SHARP.md): is plain RL's gain on the quick answer a sharpening of what the base model already samples?
Per task — BIRD dev (SQL), BFCL (tool calls), the four held-out word-problem benchmarks (OptiBench third, BWOR, LogiOR, OptMATH) —
Qwen3-8B's base quick answer at seeds 1..K, the trained quick answer (q8bcvc1 / q8btcc1 / <wp tag>, seeds 1-3), the peer Qwen3.5-9B's
quick answer and Qwen3-8B's default SB->T->T (seeds 1-3). sharp_k = the base sample at seeds 1-3, except on an item some base seed <= k
answered right: there that right answer (the most frequent right answer among those seeds, earliest on a tie; its check flag and value,
this seed's tokens) — the base fully sharpened onto its k-sample coverage. The cascade N -> the peer agrees -> N, else the default
(analyze_pair.run; word problems analyze_hopa.policies), so G is linear in N's per-item answer distribution and G(sharp_k) is the most
a reweighting of the base's k samples can give. Paired 95% intervals over items (seed means); utility = accuracy - 0.5 x ktokens.
SH-P1: share of the trained model's right samples on items no base seed <= K answers right; SH-P2 (SQL, tool calls) / SH-P3 (word
problems): trained cascade - sharp_K cascade. Also: base pass@k (unbiased estimator), and the default's right answers on items the base
never answers right (what only thinking reaches).
usage: python analyze_sharp.py [K 16] [--wp TAG]   (--wp: the trained word-problem tag, default q8bwp1; missing rows are skipped)"""
import contextlib, io, json, math, os, sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
with contextlib.redirect_stdout(io.StringIO()):   # imported modules print their own tables
    from analyze_dv import ROOT, default, per_q
    from analyze_ho3 import ci
    from analyze_pair import common, run
    from analyze_hopa import BENCH, policies, same_word, word_rows
    from analyze_ho import ok_
    from run_nlopt import RES, _rows

CAS = "N->q35->SB->T->T"


def quick_k(kind, tag, seeds):
    """{seed: {id: (passes, right, tokens, answer)}} as analyze_dv.quick, for any seeds present"""
    res = f"{ROOT}/results/{kind}"
    out = {}
    for s in seeds:
        gp = f"{res}/grades_{tag}_s{s}.json"
        if not os.path.exists(gp):
            continue
        G = json.load(open(gp)); G.pop("_gold_fail", None)
        K = {r["id"]: r["n_tok"] for r in _rows(f"{res}/{tag}_cheap_s{s}.jsonl")}
        if kind == "sql":
            out[s] = {i: (g["N"]["chk"] == "pass", g["N"]["ok"], K.get(i, 0), g["N"]["h"]) for i, g in G.items() if "N" in g}
        else:
            out[s] = {i: (g["N"]["chk"] != "fail", g["N"]["ok"], K.get(i, 0), g["N"]["calls"]) for i, g in G.items() if "N" in g}
    return out


def word_k(tag, b, seeds):
    out = {}
    for s in seeds:
        R = _rows(f"{RES}/opt_{tag}_{b}_formx_s{s}.jsonl")
        if R:
            out[s] = {r["id"]: (ok_(r), bool(r["correct"]), r.get("out_tokens") or 0, r.get("pred")) for r in R}
    return out


def sharpen(B, ids, k):
    """seeds 1-3 of the base, each wrong sample replaced by the right answer where a base seed <= k is right"""
    out = {s: {} for s in (1, 2, 3)}
    for i in ids:
        right = [B[s][i] for s in range(1, k + 1) if s in B and i in B[s] and B[s][i][1]]
        top = None
        if right:
            c = Counter(repr(r[3]) for r in right)
            top = next(r for r in right if c[repr(r[3])] == max(c.values()))
        for s in (1, 2, 3):
            n = B[s][i]
            out[s][i] = (top[0], True, n[2], top[3]) if top and not n[1] else n
    return out


def passk(B, ids, k, K):
    """unbiased pass@k over the K seeds present for every item"""
    tot = 0.0
    for i in ids:
        c = sum(B[s][i][1] for s in range(1, K + 1))
        tot += 1 - (math.comb(K - c, k) / math.comb(K, k) if K - c >= k else 0)
    return 100 * tot / len(ids)


def report(name, ids, B, T, K, Gs, ref, Dright):
    c = {i: sum(B[s][i][1] for s in range(1, K + 1)) for i in ids}
    pk = ", ".join(f"pass@{k} {passk(B, ids, k, K):.1f}%" for k in (1, 3, 8, K) if k <= K)
    print(f"=== {name}: {len(ids)} items, base K = {K} seeds: {pk}")
    only_d = sum(1 for i in ids if c[i] == 0 and Dright[i] > 0) / len(ids)
    print(f"  items the base never answers right in {K} and the default answers right at some seed: {100 * only_d:.1f}%"
          f" (mean default right there {100 * sum(Dright[i] for i in ids if c[i] == 0) / len(ids):.1f} points)")
    out = {}
    if T:
        new = sum(T[s][i][1] for s in (1, 2, 3) for i in ids if c[i] == 0)
        allr = sum(T[s][i][1] for s in (1, 2, 3) for i in ids)
        q = lambda M: 100 * sum(M[s][i][1] for s in (1, 2, 3) for i in ids) / 3 / len(ids)
        print(f"  quick right: base {q(B):.1f}%, trained {q(T):.1f}%; trained right samples on base-0/{K} items {new}/{allr}"
              f" ({100 * new / max(1, allr):.1f}%)")
        out["P1"] = 100 * new / max(1, allr)
    for k, G in Gs.items():
        g = ci({i: G[i][1] - ref[i][1] for i in ids})
        print(f"  N {k:>9} -> peer -> default - default: utility {g[0]:+.2f} [{g[1]:+.2f}, {g[2]:+.2f}]")
    if "trained" in Gs:
        g = ci({i: Gs["trained"][i][1] - Gs[f"sharp{K}"][i][1] for i in ids})
        gain, sh = (sum(Gs[x][i][1] - Gs["base"][i][1] for i in ids) for x in ("trained", f"sharp{K}"))
        print(f"  trained - sharp{K} cascade: {g[0]:+.2f} [{g[1]:+.2f}, {g[2]:+.2f}]; share of training's gain a full sharpening "
              f"onto {K} base samples gives: {100 * sh / gain if gain else float('nan'):.0f}%")
        out["P2"] = g
    return out


def short(kind, tr, K):
    D = default(kind, "q8b")
    B, T, X = quick_k(kind, "q8b", range(1, K + 1)), quick_k(kind, tr, (1, 2, 3)), quick_k(kind, "q35", (1, 2, 3))
    K = max(k for k in range(1, K + 1) if all(s in B for s in range(1, k + 1)))
    ids, D = common(D, [{s: B[s] for s in (1, 2, 3)}, T, X])
    ids = {i for i in ids if all(i in B[s] for s in range(1, K + 1))}
    D = {k: v for k, v in D.items() if k[0] in ids}
    ref = per_q(D)
    Dright = {i: sum(D[(i, s)][0] for s in (1, 2, 3)) for i in ids}
    Gs = {"base": per_q(run(kind, D, B, X))}
    for k in sorted({3, K}):
        Gs[f"sharp{k}"] = per_q(run(kind, D, sharpen(B, ids, k), X))
    Gs["trained"] = per_q(run(kind, D, T, X))
    return report(f"{kind} (trained {tr})", ids, B, T, K, Gs, ref, Dright)


def safe_same(x, y):
    try:
        return same_word(x, y)
    except ValueError:   # a value that is not a number ('NBS' against a number): no agreement, as no stored pair reached it
        return False


def words(tag, K):
    K = min(max(k for k in range(1, K + 1) if all(_rows(f"{RES}/opt_q8b_{b}_formx_s{s}.jsonl") for s in range(1, k + 1))) for b in BENCH)
    p = {"B": {s: {} for s in range(1, K + 1)}, "T": {s: {} for s in (1, 2, 3)}, "G": {}, "ref": {}, "D": {}}
    trained = True
    for b in BENCH:
        A, X = word_rows("q8b", b), word_rows("q35", b)
        B, T = word_k("q8b", b, range(1, K + 1)), word_k(tag, b, (1, 2, 3))
        T = T if len(T) == 3 else None
        trained &= T is not None
        R0 = policies(A, {"q35": X}, safe_same)
        ids = {i for i, _ in R0 if all(i in B[s] for s in range(1, K + 1)) and (T is None or all(i in T[s] for s in (1, 2, 3)))}
        arms = {"base": B, **{f"sharp{k}": sharpen(B, ids, k) for k in sorted({3, K})}, **({"trained": T} if T else {})}
        Gs = {}
        for name, F in arms.items():
            R = policies(dict(A, formx={s: F[s] for s in (1, 2, 3)}), {"q35": X}, safe_same)
            Gs[name] = per_q({k: v[CAS] for k, v in R.items() if k[0] in ids})
        ref = per_q({k: v["SB->T->T"] for k, v in R0.items() if k[0] in ids})
        Dright = {i: sum(R0[(i, s)]["SB->T->T"][0] for s in (1, 2, 3)) for i in ids}
        report(f"{b} (trained {tag if T else 'none yet'})", ids, B, T, K, Gs, ref, Dright)
        key = lambda i: f"{b}/{i}"
        for s in range(1, K + 1):
            p["B"][s].update({key(i): B[s][i] for i in ids})
        for s in (1, 2, 3):
            p["T"][s].update({key(i): T[s][i] for i in ids} if T else {})
        for name, G in Gs.items():
            p["G"].setdefault(name, {}).update({key(i): G[i] for i in ids})
        p["ref"].update({key(i): ref[i] for i in ids}); p["D"].update({key(i): Dright[i] for i in ids})
    if not trained:
        p["G"].pop("trained", None)
    return report(f"word problems pooled (trained {tag if trained else 'none yet'})", sorted(p["ref"]), p["B"],
                  p["T"] if trained else None, K, p["G"], p["ref"], p["D"])


def main():
    K = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 16
    tag = sys.argv[sys.argv.index("--wp") + 1] if "--wp" in sys.argv else "q8bwp1"
    res = {"SQL": short("sql", "q8bcvc1", K), "TC": short("tc", "q8btcc1", K), "WP": words(tag, K)}
    line = []
    for t, r in res.items():
        if "P1" in r:
            line.append(f"{t}: P1 {r['P1']:.1f}% (< 5: {r['P1'] < 5}); bound (trained - sharp lower <= 0) {r['P2'][1] <= 0} "
                        f"({r['P2'][0]:+.2f} [{r['P2'][1]:+.2f}, {r['P2'][2]:+.2f}])")
    print("*** " + "; ".join(line))


if __name__ == "__main__":
    main()
