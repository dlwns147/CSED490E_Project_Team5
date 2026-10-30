"""The SQL version of TC-RL addendum 2's cascade reward (poc/prep_tcbil.py) for cv_train.py --bil: per training question, the peer's
quick queries as a distribution over result hashes, P_X(h|i) = the share of K samples that pass the free check with result hash h
(grade_sql.py's digest, as cv_train.run_query's). With the default's T->T (v, c of cv_train.think_values) the cascade's reward for
a quick query with hash h is w = P_X(h|i) (right - v + 0.005 c / 1000), as on tool calls.
Writes $POC_DATA/bird/cv_bil_<peer>.json = {"_scale": c, "_n": questions, id: {"px": {h: P_X}}}; c = 1 / the mean per-question range
max(0, max_h w) - min(0, min_h w) over C1's 6,000 training questions ($POC_DATA/bird/cv_train_ids.txt).
usage: SQL_SPLIT=train python prep_cvbil.py <peer tag> <K>"""
import json, os, sys

os.environ.setdefault("SQL_SPLIT", "train")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cv_train import RES, think_values  # noqa: E402

DATA = os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data")


def main():
    ptag, K = sys.argv[1], int(sys.argv[2])
    V = think_values()
    ids = open(f"{DATA}/bird/cv_train_ids.txt").read().split()
    G = [json.load(open(f"{RES}/grades_{ptag}_s{s}.json")) for s in range(1, K + 1)]
    out, rng, st = {}, [], {"right": 0.0, "pass": 0.0, "pos": 0, "neg": 0, "rD": 0.0}
    for i in ids:
        if i not in V or not all("N" in g.get(i, {}) for g in G):
            continue
        v, c = V[i]
        px, ok = {}, {}
        for g in G:
            x = g[i]["N"]
            st["right"] += x["ok"] / K
            if x["chk"] == "pass":
                px[x["h"]] = px.get(x["h"], 0) + 1 / K; ok[x["h"]] = float(x["ok"]); st["pass"] += 1 / K
        w = [px[h] * (ok[h] - v + 0.005 * c / 1000) for h in px]
        rng.append(max([0.0] + w) - min([0.0] + w))
        st["pos"] += max([0.0] + w) > 0.01; st["neg"] += min([0.0] + w) < -0.01; st["rD"] += v
        out[i] = {"px": px}
    n = len(rng)
    out["_scale"], out["_n"] = n / sum(rng), n
    json.dump(out, open(f"{DATA}/bird/cv_bil_{ptag}.json", "w"))
    print(f"{ptag}: {n} of {len(ids)} training questions; T->T right {100 * st['rD'] / n:.1f}%, peer quick right {100 * st['right'] / n:.1f}%, "
          f"passes {100 * st['pass'] / n:.1f}%; w > 0.01 on {100 * st['pos'] / n:.1f}%, w < -0.01 on {100 * st['neg'] / n:.1f}%; mean range "
          f"{sum(rng) / n:.3f}, scale c {out['_scale']:.2f}")


if __name__ == "__main__":
    main()
