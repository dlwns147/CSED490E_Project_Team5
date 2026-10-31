"""VER (docs/prereg/PREREG_VER.md): the verifier's SFT set from poc/td_gen.py's rows on OptMATH-Train (labels in training only).
One example per program that passes the free check (runs and prints a number; analyze_cont.ok_): the problem text, the program and the
value it printed -> "yes" if the value is right, else "no" (VER_PROMPT; thinking off). Programs: Qwen3-8B's 8 quick programs per problem
(tags q8b, problems 1-2,000, and q8bq2, 2,001-4,000) and the cut-think / full-think programs of q8b. Problems with crc32(id) % 10 == 0
are held out (train-dev, never trained on). At most K programs per problem (a Random(0) sample), then a Random(0) sample of N examples.
Writes $POC_DATA/optmath_train/sft_ver_<name>.jsonl (prompt, target) and ver_dev_<name>.jsonl (id, arm, prompt, right, tok, and the
problem's default outcome d_right / d_tok where it has a cut-think row: the cut think's program if it passes, else the full think's).
usage: python ver_build.py <name> [--n 12000] [--k 4]"""
import glob, json, os, random, sys, zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_nlopt import _rows, value_of  # noqa: E402

DATA = os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data")
VER_PROMPT = ("{q}\n\nA Python program written for this problem:\n```python\n{code}\n```\nIt ran and printed the value {out}.\n\nIs {out} the "
              "correct optimal objective value of the problem exactly as stated? Check the program's formulation against the statement: the "
              "decision variables and whether they must be integers, every constraint and its numbers, and the objective. Answer with one "
              "word: yes or no.")


def passes(x):
    return str(x.get("runs")) == "True" and value_of(str(x.get("pred"))) not in (None, "NBS")


def fmt(v):
    v = value_of(str(v))
    return f"{v:g}" if isinstance(v, float) and abs(v) < 1e15 else str(v)


def prompt(q, code, pred):
    return VER_PROMPT.format(q=q.strip(), code=(code or "").strip(), out=fmt(pred))


def main():
    name = sys.argv[1]
    arg = lambda k, d: int(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else d
    N, K = arg("--n", 12000), arg("--k", 4)
    Q = {r["id"]: r["q"] for r in map(json.loads, open(f"{DATA}/optmath_train/wp_train_items.jsonl"))}
    R = {r["id"]: r for t in ("q8b", "q8bq2") for f in sorted(glob.glob(f"{DATA}/optmath_train/td/td_{t}_p*.jsonl")) for r in _rows(f)}
    rng = random.Random(0)
    train, dev = [], []
    for i, r in sorted(R.items()):
        progs = [("quick", x) for x in r["quick"]] + [(a, r[a]) for a in ("sb", "t") if r.get(a)]
        progs = [(a, x) for a, x in progs if passes(x)]
        d = r.get("sb") and (r["sb"] if passes(r["sb"]) else r.get("t"))
        dd = {"d_right": str(d["right"]) == "True", "d_tok": int(r["sb"]["tok"]) + (0 if d is r["sb"] else int(d["tok"]))} if d else {}
        ex = [{"id": i, "arm": a, "prompt": prompt(Q[i], x["code"], x["pred"]), "right": str(x["right"]) == "True", "tok": int(x["tok"]), **dd}
              for a, x in progs]
        if zlib.crc32(i.encode()) % 10 == 0:
            dev += ex
        else:
            ex = [{k: x[k] for k in ("id", "arm", "prompt", "right")} for x in ex]
            train += rng.sample(ex, K) if len(ex) > K else ex
    train = rng.sample(train, N) if len(train) > N else train
    with open(f"{DATA}/optmath_train/sft_ver_{name}.jsonl", "w") as f:
        for x in train:
            f.write(json.dumps({"id": x["id"], "prompt": x["prompt"], "target": "yes" if x["right"] else "no"}) + "\n")
    with open(f"{DATA}/optmath_train/ver_dev_{name}.jsonl", "w") as f:
        for x in dev:
            f.write(json.dumps(x) + "\n")
    print(f"{len(R)} problems; train {len(train)} examples ({sum(x['right'] for x in train)} yes; arms "
          + ", ".join(f"{a} {sum(x['arm'] == a for x in train)}" for a in ("quick", "sb", "t"))
          + f"); train-dev {len(dev)} programs of {len({x['id'] for x in dev})} problems ({sum(x['right'] for x in dev)} right)")


if __name__ == "__main__":
    main()
