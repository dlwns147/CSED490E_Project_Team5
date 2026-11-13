"""Ids of the word-problem rows that survive the expert audit of Xiao et al. 2025 (arXiv 2508.10047, github.com/LLM4OR/LLM4OR,
static/clean_benchmarks): they removed the problems with a wrong label, a missing datum or an ill-posed statement and kept the rest with
unchanged labels (OptiBench 403 of 605, MAMO EasyLP 545 of 652, ComplexLP 111 of 211, NL4Opt 199 of our 245 (214 folders; IndustryOR's audited file is another text version, not applied)). Matched to our rows by the question text.
usage: python poc/or_clean.py   -> $POC_DATA/clean_or/clean_ids.json; `OR_CLEAN=1` makes run_nlopt._rows drop every other row of those sets."""
import json
import os

DATA = os.environ.get("POC_DATA", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "nlp_data"))
SRC = f"{DATA}/clean_or_dl/repo/static/clean_benchmarks"
norm = lambda s: " ".join(str(s).split())


def load(p):
    t = open(p).read().strip()
    return json.loads(t) if t.startswith("[") else [json.loads(l) for l in t.splitlines() if l.strip()]


def main():
    keep, sets = set(), {}
    for name, orig, clean in [("mamo_easy", "MAMO/MAMO_EasyLP.json", "Mamo/Mamo_easy_lp_clean.jsonl"),
                              ("mamo_complex", "MAMO/MAMO_ComplexLP.json", "Mamo/Mamo_complex_lp_clean.jsonl")]:
        cq = {norm(c["Question"]) for c in load(f"{SRC}/{clean}")}
        O = load(f"{DATA}/{orig}")
        ids = {f"{name}-{k}" for k, r in enumerate(O) if norm(r["en_question"]) in cq}
        keep |= ids; sets[name] = (len(ids), len(O), len(cq))
    cq = {norm(c["question"]) for c in load(f"{SRC}/ReSocratic.jsonl")}
    O = load(f"{DATA}/optibench/ReSocratic/data/OptiBench.json")
    ids = {f"optibench-{r['index']}" for r in O if norm(r["question"]) in cq}
    keep |= ids; sets["optibench"] = (len(ids), len(O), len(cq))
    res = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results", "x3")
    # IndustryOR: the audited file (42 problems) is another text version; 3 of 42 match ours, so it is not applied
    # NL4Opt: one folder per kept problem with description.txt; matched on the first 120 normalised characters (formatting differs)
    pre = lambda t: norm(t).lower()[:120]
    cq = {pre(open(os.path.join(f"{SRC}/NL4Opt", d, "description.txt")).read()) for d in os.listdir(f"{SRC}/NL4Opt") if d.startswith("prob_")}
    O = json.load(open(f"{res}/nl4opt.json"))
    ids = {f"nl4opt-{k}" for k, r in enumerate(O) if pre(r["en_question"]) in cq}
    keep |= ids; sets["nl4opt"] = (len(ids), len(O), len(cq))
    os.makedirs(f"{DATA}/clean_or", exist_ok=True)
    json.dump({"sets": ["mamo_easy", "mamo_complex", "optibench", "nl4opt"], "keep": sorted(keep)}, open(f"{DATA}/clean_or/clean_ids.json", "w"))
    for k, (a, n, c) in sets.items():
        print(f"{k}: {a} of {n} kept (clean file {c})")


if __name__ == "__main__":
    main()
