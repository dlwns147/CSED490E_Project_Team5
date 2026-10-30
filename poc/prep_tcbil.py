"""TC-RL addendum 2 (docs/prereg/PREREG_TCRL.md): the cascade's own reward for one member, from the training items' stored rows.
With the peer X fixed, the cascade's utility is linear in N's answer distribution: G = sum_i sum_y P_N(y|i) w(y, i),
w(y, i) = P_X(y|i) (r(y) - r_D(i) + 0.005 kd(i)) (accepted when X gives the same answer; kd = the default's ktokens it saves; utility
= accuracy - 0.5 x ktokens in points). Estimated per training item without bias from K peer samples (P_X) and one default sample (r_D):
the default is Qwen3-8B's SB (seed 1), or its T (seed 1) where SB fails the free check (poc/tc_reward.py: check, canon, right).
Writes $POC_DATA/toolace/tc_bil_<peer>.json = {"_scale": c, "_n": items, id: {"rD", "kd", "px": {canon: P_X}}}; c = 1 / the mean over the
training items (the first --questions of tc_train.py's order) of max(0, max_y w) - min(0, min_y w), so that the mean per-item reward
range equals plain RL's 1.
usage: python prep_tcbil.py <default tag> <peer tag> <K>        (--need-t: print the ids whose SB fails the check, for the T pass)"""
import json, os, random, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tc_reward import canon, check, right  # noqa: E402

DATA = os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data")
RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "tc")


def rows(path):
    return {r["id"]: r for r in (json.loads(l) for l in open(path))} if os.path.exists(path) else {}


def main():
    dtag, ptag = sys.argv[1], sys.argv[2]
    items = [json.loads(l) for l in open(f"{DATA}/toolace/tc_train_items.jsonl")]
    by = {p["id"]: p for p in items}
    SB, T = rows(f"{RES}/{dtag}_sb_s1.jsonl"), rows(f"{RES}/{dtag}_think_s1.jsonl")
    if "--need-t" in sys.argv:
        print("\n".join(i for i, r in SB.items() if i in by and not check(r["text"], by[i]["functions"])))
        return
    K = int(sys.argv[3])
    X = [rows(f"{RES}/{ptag}_cheap_s{s}.jsonl") for s in range(1, K + 1)]
    order = list(items); random.Random(0).shuffle(order)
    train = {p["id"] for p in order[:6000]}
    out, rng, st = {}, [], {"n": 0, "rD": 0.0, "peer right": 0.0, "peer none": 0.0, "pos": 0, "neg": 0, "no default": 0}
    for i, p in by.items():
        sb = SB.get(i)
        if sb is None or not all(i in x for x in X):
            st["no default"] += sb is None; continue
        if check(sb["text"], p["functions"]):
            rD, kd = right(sb["text"], p["gold"], p["functions"]), sb["out_tokens"] / 1000
        elif i in T:
            rD, kd = right(T[i]["text"], p["gold"], p["functions"]), (sb["out_tokens"] + T[i]["out_tokens"]) / 1000
        else:
            st["no default"] += 1; continue
        px, rx = {}, {}
        for x in X:
            t = x[i]["n_text"]
            if check(t, p["functions"]):
                c = canon(t); px[c] = px.get(c, 0) + 1 / K; rx[c] = right(t, p["gold"], p["functions"])
        out[i] = {"rD": rD, "kd": round(kd, 4), "px": px}
        if i in train:
            w = [px[c] * (rx[c] - rD + 0.005 * kd) for c in px]
            rng.append(max([0.0] + w) - min([0.0] + w))
            st["n"] += 1; st["rD"] += rD; st["peer right"] += sum(px[c] * rx[c] for c in px); st["peer none"] += px.get("none", 0)
            st["pos"] += max([0.0] + w) > 0.01; st["neg"] += min([0.0] + w) < -0.01
    c = len(rng) / sum(rng)
    out["_scale"], out["_n"] = c, len(rng)
    json.dump(out, open(f"{DATA}/toolace/tc_bil_{ptag}.json", "w"))
    n = st["n"]
    print(f"{ptag}: {len(out) - 2} items with a default and {K} peer samples ({st['no default']} without); training items {n}: default right "
          f"{100 * st['rD'] / n:.1f}%, peer right {100 * st['peer right'] / n:.1f}%, peer no call {100 * st['peer none'] / n:.1f}%; "
          f"items with a positive w {100 * st['pos'] / n:.1f}%, a negative w {100 * st['neg'] / n:.1f}%; mean range {sum(rng) / n:.3f}, scale c {c:.2f}")


if __name__ == "__main__":
    main()
