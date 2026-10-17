"""B1 baselines: model-written test cases (CodeT-style: stdin + expected output) for the C1 geometry instances. One call per instance,
no thinking, no toolbox (a deployer writes this prompt), the given instance shown as the problem statement. Parsed into a list of
{"input", "output"}; unparsable blocks are dropped. Used by analyze_b1.py for (a) MBR-exec on model-written inputs (outputs ignored) and
(b) CodeT dual agreement (outputs used).
usage: POC_BASE_URL=... python gen_tests.py <tag> <tasks comma> [n_inst=30] [seed=1]"""
import json, os, random, re, sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import chat  # noqa: E402
from run_geo import base_instance, render, variants  # noqa: E402

RES = "/NAS/SJ/POSTECH/nlp/results"
SIZES = {"hull": (10, 20), "area2": (8, 14), "pip": (8, 14), "segs": (6, 10), "close": (10, 20), "lattice": (8, 14), "rectunion": (5, 9)}
tag, tasks = sys.argv[1], sys.argv[2].split(",")
N = int(sys.argv[3]) if len(sys.argv) > 3 else 30
SEED = int(sys.argv[4]) if len(sys.argv) > 4 else 1
PAT = re.compile(r"INPUT:\s*```[a-zA-Z]*\n(.*?)```\s*OUTPUT:\s*`*([^\n`]+)", re.S)


def run(job):
    task, n, i = job
    rng = random.Random(f"{task}-{n}-{i}")
    V = variants(task, base_instance(task, n, rng), rng)
    q, _, fmt = render(task, V["identity"])
    prompt = (f"{q}\n\nA program for this problem reads stdin in this format: {fmt}. Write 5 small but non-trivial test cases for such a "
              f"program, different from the instance above and including edge cases. For each test give the exact stdin and the expected "
              f"output, exactly in this format:\n\nTEST 1\nINPUT:\n```\n<stdin>\n```\nOUTPUT: <expected output>\n\n(and so on up to TEST 5)")
    o = chat(prompt, think=False, max_tokens=3000, temperature=0.7, seed=SEED * 1000 + i + 100 * n)
    tests = [{"input": a.strip() + "\n", "output": b.strip().split()[0].lower() if b.strip() else ""} for a, b in PAT.findall(o["text"] or "")]
    return {"task": task, "n": n, "inst": i, "tests": tests[:5], "out_tokens": o["out_tokens"], "finish": o["finish"], "text": o["text"]}


if __name__ == "__main__":
    jobs = [(t, n, i) for t in tasks for n in SIZES[t] for i in range(N)]
    with ThreadPoolExecutor(64) as ex, open(f"{RES}/tests_{tag}.jsonl", "w") as f:
        for r in ex.map(run, jobs):
            f.write(json.dumps(r) + "\n"); f.flush()
    rows = [json.loads(l) for l in open(f"{RES}/tests_{tag}.jsonl")]
    print(tag, len(rows), "instances; tests parsed per instance:", sum(len(r["tests"]) for r in rows) / len(rows))
