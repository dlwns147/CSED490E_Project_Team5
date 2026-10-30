"""TC-RL addendum 3 (docs/prereg/PREREG_TCRL.md): the cascade on held-out ToolACE requests — the 3,549 of tc_train_items.jsonl after
tc_train.py's first 6,000 in its order (the training distribution, unseen in training; $POC_DATA/toolace/tc_ho_ids.txt). Per request,
Qwen3-8B's default from one sample (SB seed 1, or T seed 1 where SB fails the free check, as prep_tcbil.py) and K = 4 quick samples of
N and of the peer X; every N sample is paired with every X sample (independent, so the products are unbiased): an N answer that fails
the free check goes to the default, one that passes is accepted with the share of X samples that pass and make the same calls
(tc_reward.check / canon, as analyze_dv.same), else the default. Utility = accuracy - 0.5 x ktokens (points); G = the cascade's
utility minus the default's; paired 95% bootstrap intervals over requests (analyze_ho3.ci).
TCRL-P14..P16: B35 vs C1tc with Qwen3.5-9B, B4t and P4t vs C1tc with C1tc-4B; reported: C1tc vs the base, accepted wrong where the
default is right / right where it is wrong, quick calls right.
usage: python analyze_tcho.py     (env TCHO_IDS, TCHO_D, TCHO_K and TCHO_ARMS="name:tag,..." for the smoke on the training items)"""
import contextlib, io, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tc_reward import canon, check, right  # noqa: E402
with contextlib.redirect_stdout(io.StringIO()):
    from analyze_ho3 import ci  # noqa: E402

DATA = os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data")
RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "tc")
K = int(os.environ.get("TCHO_K", 4))


def rows(path):
    return {r["id"]: r for r in (json.loads(l) for l in open(path))} if os.path.exists(path) else {}


def samples(tag, by, ids):
    """{id: [(passes, canon, right, ktokens)] x K} or None if a seed file is missing"""
    S = [rows(f"{RES}/{tag}_cheap_s{s}.jsonl") for s in range(1, K + 1)]
    if not all(S):
        return None
    return {i: [(check(x[i]["n_text"], by[i]["functions"]), canon(x[i]["n_text"]), right(x[i]["n_text"], by[i]["gold"], by[i]["functions"]),
                 x[i]["n_tok"] / 1000) for x in S] for i in ids if all(i in x for x in S)}


def default(dtag, by, ids):
    SB, T = rows(f"{RES}/{dtag}_sb_s1.jsonl"), rows(f"{RES}/{dtag}_think_s1.jsonl")
    out = {}
    for i in ids:
        sb, p = SB.get(i), by[i]
        if sb is None:
            continue
        if check(sb["text"], p["functions"]):
            out[i] = (right(sb["text"], p["gold"], p["functions"]), sb["out_tokens"] / 1000)
        elif i in T:
            out[i] = (right(T[i]["text"], p["gold"], p["functions"]), (sb["out_tokens"] + T[i]["out_tokens"]) / 1000)
    return out


def gain(N, X, D):
    """{id: (G, accepted wrong where D right, accepted right where D wrong, quick right)} in accuracy units (ci scales by 100)"""
    out = {}
    for i, (rD, kd) in D.items():
        if i not in N or i not in X:
            continue
        tX = sum(x[3] for x in X[i]) / K
        g = aw = ar = 0.0
        for ok, c, r, t in N[i]:
            ag = sum(x[0] and x[1] == c for x in X[i]) / K if ok and c is not None else 0.0
            if not ok:
                g += -0.005 * t
                continue
            g += ag * (r - rD) - 0.005 * (t + tX - ag * kd)
            aw += ag * (rD == 1 and r == 0); ar += ag * (rD == 0 and r == 1)
        out[i] = (g / K, aw / K, ar / K, sum(n[2] for n in N[i]) / K)
    return out


def main():
    items = {p["id"]: p for p in (json.loads(l) for l in open(f"{DATA}/toolace/tc_train_items.jsonl"))}
    ids = open(os.environ.get("TCHO_IDS", f"{DATA}/toolace/tc_ho_ids.txt")).read().split()
    D = default(os.environ.get("TCHO_D", "hoq8b"), items, ids)
    print(f"default (Qwen3-8B SB->T, seed 1): {len(D)} of {len(ids)} requests, right {100 * sum(r for r, _ in D.values()) / len(D):.1f}%, "
          f"{sum(t for _, t in D.values()) / len(D):.2f}k tokens")
    arms = os.environ.get("TCHO_ARMS", "base:hoq8b,C1tc:hoq8btcc1,B35:hoq8btcb35,B4t:hoq8btcb4t,P4t:hoq8btcp4t")
    arms = [a.split(":") for a in arms.split(",")]
    S = {name: samples(tag, items, ids) for name, tag in arms}
    peers = {"q35": samples(os.environ.get("TCHO_X35", "hoq35"), items, ids),
             "q4btcc1": samples(os.environ.get("TCHO_X4T", "hoq4btcc1"), items, ids)}
    for name, tag in arms:
        print(f"  N {name} ({tag}): " + ("no rows" if S[name] is None else
              f"{len(S[name])} requests, quick calls right {100 * sum(sum(n[2] for n in v) / K for v in S[name].values()) / len(S[name]):.1f}%"))
    out = []
    for p, (a, b) in (("q35", ("C1tc", "base")), ("q4btcc1", ("C1tc", "base")), ("q35", ("B35", "C1tc")), ("q4btcc1", ("B4t", "C1tc")),
                      ("q4btcc1", ("P4t", "C1tc"))):
        if peers[p] is None or S.get(a) is None or S.get(b) is None:
            print(f"=== {a} vs {b}, peer {p}: no rows"); continue
        Ga, Gb = gain(S[a], peers[p], D), gain(S[b], peers[p], D)
        c = sorted(set(Ga) & set(Gb))
        print(f"=== {a} vs {b}, peer {p}: {len(c)} requests")
        for n, G in ((a, Ga), (b, Gb)):
            g = ci({i: G[i][0] for i in c})
            print(f"  G({n}) {g[0]:+.2f} [{g[1]:+.2f}, {g[2]:+.2f}]; accepted wrong / default right {100 * sum(G[i][1] for i in c) / len(c):.2f}%, "
                  f"accepted right / default wrong {100 * sum(G[i][2] for i in c) / len(c):.2f}%")
        d = ci({i: Ga[i][0] - Gb[i][0] for i in c})
        w = ci({i: Ga[i][1] - Gb[i][1] for i in c})
        print(f"  G({a}) - G({b}): {d[0]:+.2f} [{d[1]:+.2f}, {d[2]:+.2f}]; accepted wrong / default right {w[0]:+.2f} [{w[1]:+.2f}, {w[2]:+.2f}]")
        out.append(f"{a}-{b} ({p}) {d[0]:+.2f} [{d[1]:+.2f}, {d[2]:+.2f}] lb>0 {d[1] > 0}")
    print("*** " + "; ".join(out))


if __name__ == "__main__":
    main()
