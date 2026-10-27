"""IF-1 (docs/prereg/PREREG_IF.md): grade every response of run_if.py with the benchmark's official grader (strict and loose,
per instruction) and write results/if/grades_<bench>_<tag>_s<seed>.json = {id: {arm: {"strict": [bool, ...], "loose": [...]}}}
for the arms N, R (where it exists), T and SB. Needs the graders' packages (absl-py, langdetect, nltk, immutabledict, emoji, syllapy):
  /home1/leesangjun/venvs/ifgrade/bin/python poc/grade_if.py <ifeval|ifbench> <tag> [seed ...]   (default seeds 1 2 3)
The graders (google-research instruction_following_eval; allenai/IFBench) and the data sit in $POC_DATA/ifeval (fetched 2026-10-27)."""
import json, os, sys

DATA = os.path.join(os.environ.get("POC_DATA", "/home1/leesangjun/SJ/POSTECH/nlp_data"), "ifeval")
RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "if")
FILES = {"ifeval": "ifeval_input_data.jsonl", "ifbench": "IFBench_test.jsonl"}


def rows(path):
    return {r["id"]: r for r in (json.loads(l) for l in open(path))} if os.path.exists(path) else {}


def main():
    bench, tag = sys.argv[1], sys.argv[2]
    seeds = [int(s) for s in sys.argv[3:]] or [1, 2, 3]
    sys.path.insert(0, os.path.join(DATA, "grader_ifeval" if bench == "ifeval" else "grader_ifbench"))
    import nltk
    for r in ("punkt", "punkt_tab"):
        nltk.download(r, quiet=True)
    import evaluation_lib as E
    inputs = {str(x["key"]): x for x in (json.loads(l) for l in open(os.path.join(DATA, FILES[bench])))}
    for s in seeds:
        C, T, SB = (rows(f"{RES}/{bench}_{tag}_{a}_s{s}.jsonl") for a in ("cheap", "think", "sb"))
        out = {}
        for i, x in inputs.items():
            resp = {"N": C.get(i, {}).get("n_text"), "R": C.get(i, {}).get("r_text"), "T": T.get(i, {}).get("text"), "SB": SB.get(i, {}).get("text")}
            g = {}
            for arm, r in resp.items():
                if r is None:
                    continue
                inp = E.InputExample(key=x["key"], instruction_id_list=list(x["instruction_id_list"]), prompt=x["prompt"],
                                     kwargs=[dict(k) for k in x["kwargs"]])
                g[arm] = {m: f(inp, {x["prompt"]: r}).follow_instruction_list for m, f in
                          (("strict", E.test_instruction_following_strict), ("loose", E.test_instruction_following_loose))}
            if g:
                out[i] = g
        json.dump(out, open(f"{RES}/grades_{bench}_{tag}_s{s}.json", "w"))
        n = {a: [v[a]["strict"] for v in out.values() if a in v] for a in ("N", "R", "T", "SB")}
        print(bench, tag, s, {a: f"{100 * sum(all(z) for z in v) / max(1, len(v)):.1f}% of {len(v)}" for a, v in n.items()}, flush=True)


if __name__ == "__main__":
    main()
