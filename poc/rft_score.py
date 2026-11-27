"""RFT-C scorer (PREREG_DIFF, 2026-11-26): fine-tuned − base on the held-out problems (decisive) and on the training problems (in-distribution),
paired by instance, clustered by problem; first row per (id, seed). Also gpt-oss-120b OWN-E on the same instances (stored tirsub3_OWN_mcong_medium_s1..4).
Reported beyond accuracy: tokens, tool calls, finish reasons, give-ups (empty submission), solver-call rate is not available in these rows (codes not stored).
usage: python rft_score.py <tag_ft> [tag_base=base]"""
import json, os, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import tir_score as S
R = S.R; U = S.U


def load(tag, st):
    out = collections.defaultdict(list); seen = set()
    for s in range(1, 9):
        p = f"{R}/rft_{tag}_{st}_s{s}.jsonl"
        if not os.path.exists(p):
            continue
        for l in open(p):
            z = json.loads(l); k = (z["id"], z["seed"])
            if k in seen:
                continue
            seen.add(k); out[z["id"]].append(z)
    return out


def big(ids):
    out = collections.defaultdict(list)
    for s in (1, 2, 3, 4):
        p = f"{R}/tirsub3_OWN_mcong_medium_s{s}.jsonl"
        if os.path.exists(p):
            for l in open(p):
                z = json.loads(l)
                if z["id"] in ids:
                    out[z["id"]].append(z)
    return out


def summ(rows):
    n = len(rows)
    return {"acc": 100 * sum(z["correct"] for z in rows) / n, "ktok": sum(z["out_tokens"] for z in rows) / n / 1000, "calls": sum(z["calls"] for z in rows) / n,
            "finish": dict(collections.Counter(z["finish"][:9] for z in rows)), "empty": sum(not z["final"] or z["final"].strip() in ("\\boxed{}",) for z in rows)}


def main(ft, base="base"):
    for st in ("held", "trainp"):
        B, F = load(base, st), load(ft, st); ks = sorted(set(B) & set(F))
        if not ks:
            print(f"== {st}: no paired rows"); continue
        m = lambda rows: (sum(z["correct"] for z in rows) / len(rows), sum(z["out_tokens"] for z in rows) / len(rows))
        key = [k.split("__")[0] for k in ks]
        print(f"== {st}: {len(ks)} instances of {len(set(key))} problems; attempts base {sum(len(B[k]) for k in ks)}, fine-tuned {sum(len(F[k]) for k in ks)}")
        for lab, D in (("base", B), ("fine-tuned", F)):
            a = [m(D[k]) for k in ks]; s = summ([z for k in ks for z in D[k]])
            print(f"   {lab:10s} {100*sum(x for x, _ in a)/len(a):.1f}% @ {sum(t for _, t in a)/len(a)/1000:.2f}k utility {sum(U(*x) for x in a)/len(a):.2f}; calls {s['calls']:.1f}; finish {s['finish']}; empty {s['empty']}")
        G = big(set(ks))
        if G:
            gk = [k for k in ks if k in G]; a = [m(G[k]) for k in gk]
            print(f"   120b OWN-E (stored, {len(gk)} instances) {100*sum(x for x, _ in a)/len(a):.1f}% @ {sum(t for _, t in a)/len(a)/1000:.2f}k utility {sum(U(*x) for x in a)/len(a):.2f}")
        print(f"   fine-tuned − base: utility {S.ci([U(*m(F[k])) - U(*m(B[k])) for k in ks], key)} accuracy {S.ci([100*(m(F[k])[0]-m(B[k])[0]) for k in ks], key)} ktok {S.ci([(m(F[k])[1]-m(B[k])[1])/1000 for k in ks], key)}")


if __name__ == "__main__":
    main(*sys.argv[1:])
