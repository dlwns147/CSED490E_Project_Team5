"""DT3 (docs/prereg/PREREG_DT.md): unlabeled training problems. 2,000 random question texts each from OptMATH-Train (Aurora-Gem/OptMATH-
Train) and OR-Instruct-Data-3K (CardinalOperations), with their answers / code / completions dropped; any text sharing ≥ 30% of its
8-gram set with a held-out problem (OptMATH, OptiBench, BWOR, LogiOR) is removed (decontamination).
usage: python build_unlabeled.py  -> $POC_DATA/sft/unlabeled_4k.jsonl"""
import json, os, random, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_nlopt import DATA, problems  # noqa: E402

SRC = f"{DATA}/stage/unlabeled"


def grams(t, n=8):
    w = re.findall(r"[a-z0-9]+", t.lower())
    return {" ".join(w[k:k + n]) for k in range(max(0, len(w) - n + 1))}


def main():
    rng = random.Random(0)
    om = []
    with open(f"{SRC}/OptMATH-Train.jsonl") as f:
        for k, l in enumerate(f):
            if k % 50 == 0:   # every 50th line, then a random 2,000 of those (the file has 201k)
                t = json.loads(l)["input"]
                om.append(t.split("# Question:", 1)[-1].split("# Note:", 1)[0].strip())
    oi = [json.loads(l)["prompt"] for l in open(f"{SRC}/OR-Instruct-Data-3K.json")]
    oi = [t.split("# Question:", 1)[-1].split("# Response:", 1)[0].strip() for t in oi]
    held = [grams(p["q"]) for w in ("optmath", "optibench", "bwor", "logior") for p in problems(w)]
    out, dropped = [], 0
    for src, pool in (("optmath_train", om), ("or_instruct", oi)):
        for k, q in enumerate(rng.sample(pool, 2000)):
            g = grams(q)
            if g and any(len(g & h) >= 0.3 * min(len(g), len(h)) for h in held if h):
                dropped += 1; continue
            out.append({"id": f"{src}-{k}", "src": src, "q": q})
    os.makedirs(f"{DATA}/sft", exist_ok=True)
    with open(f"{DATA}/sft/unlabeled_4k.jsonl", "w") as f:
        for o in out:
            f.write(json.dumps(o) + "\n")
    print(f"wrote {len(out)} unlabeled problems; dropped {dropped} for overlap with a held-out problem")


if __name__ == "__main__":
    main()
