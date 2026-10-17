# Tools, Facts, and Checks

CSED490E (Graduate NLP, POSTECH) team project, Team 5.

LLMs often solve math problems by writing a program and running it. Computational geometry (convex hulls,
polygon areas) and optimization (vehicle routing, scheduling with the OR-Tools solver library) are two examples.
Programs like these can be silently wrong. This project asks **when LLM-written programs fail, and what is the
cheapest fix**. "Think longer" is not always the answer.

| Kind of mistake | Example | Cheapest fix we found |
|---|---|---|
| The model does not know a library fact | calls `RegisterUnaryLongLivingCallback`, which does not exist in OR-Tools | show 5 lines of exact usage (CVRP, Qwen3-32B: 23% → 77–90% optimal; thinking longer: 3%) |
| Extra tools in the prompt distract it | 8 unneeded helper functions make it build a convex hull on `polar_sort` and get it wrong | write the program with and without the helpers; think only when the answers differ (99% at 4.3k tokens vs always thinking 98% at 5.9k) |
| The problem is simply hard | Codeforces geometry rated 1900–2000 | medium effort first, high effort only when the statement's examples fail (66% at 25k tokens vs always high 66% at 30k) |
| The same problem repeats with new data | daily vehicle routing (Solomon VRPTW) | check one program on 8 past instances and reuse it (94% valid vs 7% with a new program each time) |

Where to read more:
- `PROPOSAL_slides.pptx`: 10-slide overview with examples.
- `PROPOSAL.md` and `PROPOSAL_ko.md`: the proposal (English and Korean).
- `docs/README.md`: index of all experiments, grouped by theme.
- `docs/FINDINGS.md`: the full chronological lab log.
- `docs/prereg/PREREG_*.md`: the pre-registration and the results of each experiment.

## Repository layout

```
README.md                                           this file
PROPOSAL.md, PROPOSAL_ko.md, PROPOSAL_slides.pptx   proposal and slides
HANDOFF.md                                          server notes for continuing the work (environment, paths, status)
docs/                                               everything written about the experiments (index: docs/README.md)
  FINDINGS.md                                       chronological lab log
  prereg/PREREG_<id>.md                             one file per experiment: predictions first, then dated results
  notes/                                            critique, check coverage, failure -> fix map, related work, drafts
  archive/                                          proposal versions from before the repository existed
figs/                                               figures used in the proposal and the slides
poc/                                                all code (flat: the scripts import each other)
  llm.py, sandbox.py                                OpenAI-compatible client; sandboxed runner for generated programs
  serve_gpu.sh, start_server.sh                     start a vLLM server
  run_*.py                                          experiment harnesses (one per benchmark, see below)
  analyze_*.py                                      analyses (one per experiment id, e.g. analyze_n12.py)
  make_figures*.py, make_slide*.py, make_slides.js  figures and slides
  queues/queue_*.sh                                 the exact command sequences we ran (one per experiment)
results/                                            benchmark inputs, reference solutions, small analysis outputs,
                                                    queue_log.txt (when each run started and ended)
```

Raw model outputs (`*.jsonl`, about 1.2 GB) and run logs (`*.log`) are not in git: see `.gitignore`. Each run
script regenerates its output file. The original files are on the lab server at `/NAS/SJ/POSTECH/nlp/results`.

## Setup

**1. Client environment.** Generated programs run with the same Python interpreter, so it needs OR-Tools.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r poc/requirements.txt           # openai numpy requests ortools==9.15.6755 matplotlib
pip install sympy math-verify pandas          # competition math (run_math.py) and data extraction (cc_extract.py)
```

**2. Model server.** Any OpenAI-compatible server works. We used vLLM (0.22 on RTX PRO 6000 Blackwell GPUs; 0.10.2
on the earlier server). Models: Qwen3-8B/14B, Qwen3-32B-AWQ, gpt-oss-20b, gpt-oss-120b, Qwen3.6-35B-A3B.

```bash
# from the repository root: bash poc/start_server.sh <model dir> <port> <gpu id> <GPU memory fraction> <log tag> [extra vLLM args]
bash poc/start_server.sh /models/Qwen3-32B-AWQ 8041 0 0.88 q32b       # prints the server PID once it is healthy
export POC_BASE_URL=http://127.0.0.1:8041/v1                          # every run script reads this
export POC_REASONING_EFFORT=medium                                    # gpt-oss only: low | medium | high
```

The server is served as model name `local`. Its log goes to `results/server_vllm_<tag>.log`. Stop it with `kill <PID>`.

**3. Paths.** Most scripts hard-code the project root `/NAS/SJ/POSTECH/nlp`, and the queue scripts also hard-code
the client Python (`/root/venvs/llm_algo_poc/bin/python`) and model folders (`/SSD/huggingface/...`). On another
machine, replace them once:

```bash
grep -rl /NAS/SJ/POSTECH/nlp poc | xargs sed -i "s#/NAS/SJ/POSTECH/nlp#$PWD#g"
```

**4. Sanity check (CPU, no model).** Every reference solution must pass the harness on all 13 geometry tasks:

```bash
python poc/sanity_check.py
```

## How to run the main experiments

Run every command from the repository root, with `POC_BASE_URL` set. Outputs go to `results/`.

### Geometry with and without extra helpers (slide 7)

13 generated geometry tasks (hull, area, point-in-polygon, ...). Each program is run on 8 transformed copies of the
input (moved, rotated, mirrored, degenerate) and counts as correct only if it is right on all 8.

```bash
T=hull,area2,pip,segs,close,lattice,rectunion,delaunay,diameter
X="--stdlib --n_inst 6 --temperature 0.7 --tasks $T --max_tokens 4096"
for s in 1 2 3; do   # Prompt B: task + 8 helpers (the analysis also uses seeds 2-3 as extra samples)
  python poc/run_geo_cross.py --model_tag S2_N10_geo_k8_s$s $X --seed $s --distract 8; done
python poc/run_geo_cross.py --model_tag S2_N10_geo_none_s1 $X --seed 1                  # Prompt A: task only
python poc/run_geo_cross.py --model_tag S2_N10_geo_think_s1 --stdlib --n_inst 6 --temperature 0.7 --tasks $T \
       --seed 1 --distract 8 --think --max_tokens 16000                                 # always think
N10_PREFIX=S2_N10 python poc/analyze_n12.py 1 geo     # compare both programs, think only if they differ
```

Output: `results/geocross_<tag>.jsonl`. The full set of arms is in `poc/queues/queue_s2_n10.sh`.

### Optimization with library documentation (slide 6)

Knapsack, TSP, graph colouring, scheduling, bin packing, vertex cover, CVRP and VRPTW, solved by programs that use
OR-Tools. The score is the optimality gap against our reference solutions.

```bash
X="--arms solver --probs knapsack,tsp,color,sched,binpack,vcover,cvrp,vrptw --n_inst 4 --temperature 0.7 --fmt_fix --max_tokens 4096"
python poc/run_co.py --model_tag S2_N10_co_nodoc_s1   $X --seed 1                          # nothing extra
python poc/run_co.py --model_tag S2_N10_co_doc_s1     $X --seed 1 --api_doc                # long reference sheet
python poc/run_co.py --model_tag S2_N10_co_snippet_s1 $X --seed 1 --api_doc --api_doc_task # only the exact lines needed
python poc/run_co.py --model_tag S2_N10_co_rag3_s1    $X --seed 1 --retrieve 3             # BM25-retrieved snippets
```

Output: `results/co_<tag>.jsonl`. Add `--think --max_tokens 16000` for the thinking arm and `--repair 1` for one repair round.

### Real contest geometry problems (slide 8)

355 Codeforces geometry problems from CodeContests, with official tests (311 have a reference that passes them all).

```bash
export CC_SET=full
python -I poc/cc_extract.py <CodeContests parquet dir>      # -> results/h2/cc_geometry_full.json (already in the repo)
python poc/run_cc.py validate                               # -> results/h2/cc_valid_full.json (keeps problems a reference passes)
POC_REASONING_EFFORT=medium python poc/run_cc.py run oss120_medium 1 --max_tokens 16000
POC_REASONING_EFFORT=high   python poc/run_cc.py run oss120_high64k 1 --max_tokens 62000   # server needs --max-model-len 65536
python poc/analyze_n8.py      # medium first, high only when the statement's examples fail
python poc/analyze_n13.py     # the same, plus a brute-force cross-check
```

Output: `results/h2/cc_full_<tag>_s<seed>.jsonl`. One label-free repair round: `python poc/repair_cc.py <tag> <seed>`.

### Reusing one checked program (slide 9)

The 56 Solomon VRPTW instances (100 customers each), compared with the best-known solutions. These are in the repo
in `results/h3/instances/` and `results/h3/bks.json`. To rebuild them: `python poc/run_solomon.py prep <zip> <SINTEF page>`.

```bash
POC_REASONING_EFFORT=low python poc/run_solomon.py run oss120_low_plain 1 --max_tokens 16000
POC_REASONING_EFFORT=low python poc/run_solomon.py run oss120_low_plain 2 --max_tokens 16000
REUSE_SEEDS=1,2 python poc/analyze_reuse_curve.py oss120_low_plain   # pick on 8 instances, reuse on the other 48
```

### Other benchmarks

| Benchmark | Command | Notes |
|---|---|---|
| Job-shop scheduling (OR-Library la01–la40) | `python poc/run_jssp.py ref`, then `python poc/run_jssp.py run <tag> <seed>` | instances in `results/h5/instances/`; `run_jssp_rd.py` / `run_jssp_var.py` add release dates, tardiness, flexible machines |
| Competition math (MATH-500, AIME 2024/2025) | `python poc/run_math.py <tag> <text\|prog\|think> <seed> [--think]` | problems in `results/x1/problems.json`; graded with math-verify |
| Word problems → optimization models (NL4OPT, IndustryOR) | `python poc/run_nlopt.py <tag> <mip\|mipf\|cpsat\|text\|think> <seed>` | `mipf` adds the 6-line exact solver snippet; see `docs/prereg/PREREG_X3.md` |
| Lean 4 proofs (miniF2F) | `python poc/run_lean.py gen <tag> <split> <k>`, then `check <file>` | needs Lean 4 v4.15.0 + Mathlib (path `PROJ` in the script) |

Each experiment's exact commands are in `poc/queues/queue_s2_<id>.sh`. Its pre-registration and results are in
`docs/prereg/PREREG_<id>.md`.

## Figures and slides

```bash
python poc/make_figures_explain.py                                 # figs/fig0 and fig13-fig17 (proposal figures)
python poc/make_slide2_shapes.py && python poc/make_slide5_hull.py # slide illustrations
npm install pptxgenjs && node poc/make_slides.js                   # PROPOSAL_slides.pptx
```

`make_slides.js` also applies the theme through a helper from a local skill folder. If that path does not exist on
your machine, remove the `applyTheme` lines. The deck still builds with the default Office colours.

## Notes

- **Shared GPUs.** Check `nvidia-smi` before starting a server, cap the memory fraction to what is free, and use a
  port that nothing answers yet: `start_server.sh` refuses a busy port.
- **CIFS / NAS mounts.** Run scripts as `bash poc/<script>.sh` because there are no exec bits. Do not edit files with
  `sed -i` on the mount, because it can delete them there. Use the `sed -i` path fix above only on a local copy.
- **Seeds.** Runs use temperature 0.7 with per-item seeds. We report a claim only if it holds on 3 seeds.
- **Tokens.** Every result row stores the output tokens (`out_tokens`) and the finish reason, so accuracy can always
  be read together with its cost.
