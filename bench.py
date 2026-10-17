"""One entry point for the benchmarks: wraps poc/run_*.py with the settings used in the reported experiments.

  python bench.py list                                  benchmarks, arms and model aliases
  python bench.py download q32b oss20                   download models from Hugging Face into $MODELS_DIR (or: download all)
  python bench.py serve q32b --gpu 0                    start a vLLM server for a model (prints its PID once healthy)
  python bench.py run geo k8 --model q32b --seed 1      run one arm of one benchmark against that server
  python bench.py run contest plain --model oss120 --effort medium
  python bench.py analyze u1 q32b q8b                   = python poc/analyze_u1.py q32b q8b

Options of `run`: --port (default 8041; POC_BASE_URL overrides it), --effort low|medium|high (gpt-oss reasoning effort),
--tag (output name; default the model alias), --dry (print the command only); anything after `--` is passed to the harness (e.g. `-- --max_tokens 28000 --logprobs`).
Model folders are looked up under $MODELS_DIR (default /SSD/huggingface). Outputs go to results/ (file name printed by each harness)."""
import argparse, os, shlex, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
MODELS = {   # alias: (folder under MODELS_DIR, extra vLLM arguments)
    "q8b": ("Qwen/Qwen3-8B", ""),
    "q14b": ("Qwen/Qwen3-14B", ""),
    "q32b": ("Qwen/Qwen3-32B-AWQ", ""),
    "q36": ("Qwen/Qwen3.6-35B-A3B-FP8", "--max-num-seqs 64 --language-model-only"),
    "oss20": ("openai/gpt-oss-20b", ""),
    "oss120": ("openai/gpt-oss-120b", ""),
}
# alias: (download size in GB, smallest single-GPU memory in GB for our setting: 32k context, --frac 0.88; see README)
SIZES = {"q8b": (16, 32), "q14b": (30, 48), "q32b": (19, 40), "q36": (38, 80), "oss20": (14, 24), "oss120": (65, 80)}
GEO = ("poc/run_geo_cross.py --model_tag {tag}_geo_{arm}_s{seed} --seed {seed} --stdlib --n_inst 6 --temperature 0.7 --resume "
       "--tasks hull,area2,pip,segs,close,lattice,rectunion,delaunay,diameter")
CO = ("poc/run_co.py --model_tag {tag}_co_{arm}_s{seed} --seed {seed} --arms solver --n_inst 4 --temperature 0.7 --fmt_fix --resume "
      "--probs knapsack,tsp,color,sched,binpack,vcover,cvrp,vrptw")
# benchmark: (description, command template, {arm: (description, harness flags)}); {mode} = the arm name unless the flags set it
BENCH = {
    "geo": ("9 generated geometry tasks; a program counts only if right on all 8 transformed copies of each input", GEO, {
        "none": ("the task only", "--max_tokens 4096"),
        "k8": ("the task + 8 helper functions, most of them not needed", "--distract 8 --max_tokens 4096"),
        "fact": ("a short algorithm hint + only the helpers the task needs", "--distract 0 --algo_hint --max_tokens 4096"),
        "retr": ("k8 + a BM25-retrieved algorithm note (may be a near miss)", "--distract 8 --hint_retrieve --max_tokens 8192"),
        "think": ("k8 with thinking on", "--distract 8 --think --max_tokens 16000")}),
    "co": ("8 optimization problems (knapsack ... VRPTW) solved with OR-Tools; scored by the gap to our reference", CO, {
        "nodoc": ("the problem only", "--max_tokens 4096"),
        "doc": ("+ a long OR-Tools reference sheet", "--api_doc --max_tokens 4096"),
        "snippet": ("+ only the exact API lines this problem needs", "--api_doc --api_doc_task --max_tokens 4096"),
        "rag3": ("+ the 3 BM25-retrieved documentation snippets", "--retrieve 3 --max_tokens 4096"),
        "think": ("+ reference sheet, thinking on", "--api_doc --think --max_tokens 16000")}),
    "contest": ("355 Codeforces geometry problems with official tests (CodeContests)",
                "poc/run_cc.py run {tag}_{arm} {seed}", {
        "plain": ("the statement", "--max_tokens 16000"),
        "k8": ("the statement + 8 related helper functions", "--k8 --max_tokens 16000"),
        "think": ("thinking on (Qwen)", "--think --max_tokens 16000")}),
    "vrptw": ("56 Solomon VRPTW instances (100 customers), compared with the best-known solutions",
              "poc/run_solomon.py run {tag}_{arm} {seed}", {
        "plain": ("the instance file and the task", "--max_tokens 16000"),
        "snippet": ("+ a correct OR-Tools routing snippet", "--snippet --max_tokens 16000"),
        "think": ("thinking on (Qwen)", "--think")}),
    "jssp": ("40 job-shop instances (la01-la40), compared with a CP-SAT reference",
             "poc/run_jssp.py run {tag}_{arm} {seed}", {"plain": ("the instance and the task", "--max_tokens 6000")}),
    "math": ("MATH-500 + AIME 2024/2025, graded with math-verify", "poc/run_math.py {tag} {mode} {seed}", {
        "text": ("answer in text", ""),
        "prog": ("write a Python program that prints the answer", ""),
        "think": ("text answer with thinking on", "--think --max_tokens 28000")}),
    "nlopt": ("NL4OPT (245) + IndustryOR (100) word problems -> an optimization model", "poc/run_nlopt.py {tag} {mode} {seed}", {
        "mip": ("a pywraplp (SCIP) program", ""),
        "mipf": ("mip + a 6-line exact pywraplp snippet", ""),
        "cpsat": ("a CP-SAT program", ""),
        "text": ("solve in text", ""),
        "think": ("mip with thinking on", "--think --max_tokens 16000"),
        "thinkf": ("mipf with thinking on", "--think --max_tokens 16000")}),
    "lean": ("miniF2F test (244) in Lean 4 + Mathlib; needs Lean (see poc/run_lean.py)", "poc/run_lean.py {mode} {tag} test 8", {
        "gen": ("generate 8 proofs per statement (then run the `check` arm, CPU only)", "--logprobs")}),
    "popqa": ("1,500 PopQA questions in 5 popularity bins (factual QA)", "poc/run_popqa.py {tag} {mode} {seed}", {
        "direct": ("answer directly", ""), "recall": ("recall related facts, then answer", ""), "think": ("thinking on", "")}),
}


def cmd_list():
    print("models (under $MODELS_DIR; download size, smallest GPU):")
    for k, (folder, _) in MODELS.items():
        print(f"  {k:7} {folder:28} {SIZES[k][0]:3d} GB, GPU >= {SIZES[k][1]} GB")
    for b, (about, _, arms) in BENCH.items():
        print(f"\n{b}: {about}")
        for a, (d, flags) in arms.items():
            print(f"  {a:8} {d}" + (f"   [{flags}]" if flags else ""))
    print("\nlean check (CPU, after gen): python poc/run_lean.py check results/x4/lean_<model>_test.jsonl")


def cmd_download(a):
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        sys.exit("needs huggingface_hub: pip install huggingface_hub")
    root = os.environ.get("MODELS_DIR", "/SSD/huggingface")
    names = list(MODELS) if "all" in a.models else a.models
    todo = [m for m in names if not os.path.exists(os.path.join(root, MODELS[m][0], "config.json"))]
    need = sum(SIZES[m][0] for m in todo)
    os.makedirs(root, exist_ok=True)
    free = shutil.disk_usage(root).free / 1e9
    print(f"{root}: {free:.0f} GB free; new downloads need about {need} GB", flush=True)
    if free < need + 10 and not a.dry:
        sys.exit("not enough free disk space (keeps 10 GB spare); set MODELS_DIR to a larger disk")
    for m in names:
        rid = MODELS[m][0]
        dst = os.path.join(root, rid)
        print(f"{m}: {rid} -> {dst}", flush=True)
        if a.dry:
            continue
        for k in range(3):   # an interrupted download resumes where it stopped
            try:
                # gpt-oss repos also hold the same weights in two other formats (original/, metal/): 196 GB instead of 65 GB
                snapshot_download(rid, local_dir=dst, ignore_patterns=["original/*", "metal/*"])
                break
            except Exception as e:
                print(f"  attempt {k + 1} failed: {e}", flush=True)
        else:
            sys.exit(f"{m}: download failed")


def cmd_serve(a):
    folder, extra = MODELS[a.model]
    path = os.path.join(os.environ.get("MODELS_DIR", "/SSD/huggingface"), folder)
    c = ["bash", "poc/start_server.sh", path, str(a.port), str(a.gpu), str(a.frac), f"{a.model}_{a.port}"] + extra.split() + a.rest
    print("$", shlex.join(c), flush=True)
    r = subprocess.run(c, cwd=ROOT, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"server failed; see results/server_vllm_{a.model}_{a.port}.log and results/gpu_choice.log")
    print(f"server PID {r.stdout.strip()} on port {a.port} (stop it with: kill {r.stdout.strip()})")


def cmd_run(a):
    about, tmpl, arms = BENCH[a.bench]
    if a.arm not in arms:
        sys.exit(f"unknown arm '{a.arm}' for {a.bench}; choose from {', '.join(arms)}")
    tag = a.tag or a.model + (f"_{a.effort}" if a.effort else "")
    line = tmpl.format(tag=tag, arm=a.arm, mode=a.arm, seed=a.seed) + " " + arms[a.arm][1]
    c = [sys.executable] + shlex.split(line) + a.rest
    env = dict(os.environ)
    env.setdefault("POC_BASE_URL", f"http://127.0.0.1:{a.port}/v1")
    if a.effort:
        env["POC_REASONING_EFFORT"] = a.effort
    if a.bench == "contest":
        env["CC_SET"] = "full"
    print("$", " ".join(f"{k}={env[k]}" for k in ("POC_BASE_URL", "POC_REASONING_EFFORT", "CC_SET") if k in env), shlex.join(c), flush=True)
    if not a.dry:
        sys.exit(subprocess.run(c, cwd=ROOT, env=env).returncode)


def main():
    argv = sys.argv[1:]
    rest = argv[argv.index("--") + 1:] if "--" in argv else []
    argv = argv[:argv.index("--")] if "--" in argv else argv
    if argv[:1] == ["analyze"] and len(argv) > 1:
        sys.exit(subprocess.run([sys.executable, f"poc/analyze_{argv[1]}.py"] + argv[2:] + rest, cwd=ROOT).returncode)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    d = sub.add_parser("download")
    d.add_argument("models", nargs="+", choices=list(MODELS) + ["all"])
    d.add_argument("--dry", action="store_true", help="only print what would be downloaded")
    s = sub.add_parser("serve")
    s.add_argument("model", choices=MODELS)
    s.add_argument("--gpu", type=int, default=0)
    s.add_argument("--port", type=int, default=8041)
    s.add_argument("--frac", type=float, default=0.88, help="GPU memory fraction for vLLM")
    r = sub.add_parser("run")
    r.add_argument("bench", choices=BENCH)
    r.add_argument("arm")
    r.add_argument("--model", required=True, help="model alias (see `list`); with --effort, names the output files")
    r.add_argument("--tag", default="", help="name the output files differently (an existing tag is resumed or overwritten)")
    r.add_argument("--seed", type=int, default=1)
    r.add_argument("--port", type=int, default=8041)
    r.add_argument("--effort", choices=["low", "medium", "high"], help="gpt-oss reasoning effort")
    r.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)
    a.rest = rest
    {"list": lambda: cmd_list(), "download": lambda: cmd_download(a), "serve": lambda: cmd_serve(a), "run": lambda: cmd_run(a)}[a.cmd]()


if __name__ == "__main__":
    main()
