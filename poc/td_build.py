"""TD (docs/prereg/PREREG_TD.md): the two SFT sets from poc/td_gen.py's rows, the same number of examples each (n = the smaller set; a
Random(0) sample of the larger). td: per problem the thinking program that is right (the cut think's, else the full think's); rft: per
problem the first of the 8 quick programs that is right (rejection-sampling fine-tuning, RFT 2308.01825, on the model's own quick mode).
Prompt = run_nlopt.P_FREE (thinking off at training), target = the program in a Python block, as DT (poc/sft_lora.py).
Writes $POC_DATA/optmath_train/sft_{td,rft}_<tag>.jsonl (td/ is written by the container as root) and prints the coverage table.
usage: python td_build.py <tag> [--rft-all <tag2> ...]"""
import glob, json, os, random, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run_nlopt import P_FREE, _rows  # noqa: E402

DATA = os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data")


def rft_all(tags):
    """addendum RF: per problem the first right quick program, over the rows of every tag (no size matching) -> sft_rft4k_<tag 1>"""
    Q = {r["id"]: r["q"] for r in map(json.loads, open(f"{DATA}/optmath_train/wp_train_items.jsonl"))}
    R = {r["id"]: r for t in tags for f in sorted(glob.glob(f"{DATA}/optmath_train/td/td_{t}_p*.jsonl")) for r in _rows(f)}
    S = [{"id": i, "prompt": P_FREE.format(q=Q[i]), "target": "```python\n" + qk["code"].strip() + "\n```"}
         for i, r in sorted(R.items()) for qk in [next((x for x in r["quick"] if x["right"]), None)] if qk]
    with open(f"{DATA}/optmath_train/sft_rft4k_{tags[0]}.jsonl", "w") as f:
        for x in S:
            f.write(json.dumps(x) + "\n")
    print(f"{len(R)} problems, quick right in any of 8: {len(S)}; sft_rft4k_{tags[0]}: {len(S)} examples")


def main():
    if "--rft-all" in sys.argv:
        return rft_all([sys.argv[1]] + sys.argv[sys.argv.index("--rft-all") + 1:])
    tag = sys.argv[1]
    Q = {r["id"]: r["q"] for r in map(json.loads, open(f"{DATA}/optmath_train/wp_train_items.jsonl"))}
    R = [r for f in sorted(glob.glob(f"{DATA}/optmath_train/td/td_{tag}_p*.jsonl")) for r in _rows(f)]
    td, rft, cell = [], [], {(a, b): 0 for a in (0, 1) for b in (0, 1)}
    for r in sorted(R, key=lambda r: r["id"]):
        th = r["sb"] if r["sb"]["right"] else r["t"] if r["t"] and r["t"]["right"] else None
        qk = next((x for x in r["quick"] if x["right"]), None)
        cell[(qk is not None, th is not None)] += 1
        ex = lambda c: {"id": r["id"], "prompt": P_FREE.format(q=Q[r["id"]]), "target": "```python\n" + c.strip() + "\n```"}
        if th:
            td.append(ex(th["code"]))
        if qk:
            rft.append(ex(qk["code"]))
    n = min(len(td), len(rft))
    print(f"{len(R)} problems; quick right in any of 8 / thinking right: both {cell[(1, 1)]}, quick only {cell[(1, 0)]}, "
          f"thinking only {cell[(0, 1)]}, neither {cell[(0, 0)]}; quick right samples {sum(x['right'] for r in R for x in r['quick'])}"
          f"/{8 * len(R)}; cut think right {sum(r['sb']['right'] for r in R)}")
    for name, S in (("td", td), ("rft", rft)):
        S = random.Random(0).sample(S, n) if len(S) > n else S
        with open(f"{DATA}/optmath_train/sft_{name}_{tag}.jsonl", "w") as f:
            for x in S:
                f.write(json.dumps(x) + "\n")
        print(f"sft_{name}: {len(S)} examples")


if __name__ == "__main__":
    main()
