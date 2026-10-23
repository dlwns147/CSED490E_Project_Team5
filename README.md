# Solving Computational Math with LLMs, Accurately and Cheaply

*Tools, Facts, and Checks.* POSTECH CSED490E (Graduate NLP) team project, Team 5.

This is the manual: how to set up, run and analyze everything in this repository. **What the project is for, its claim, scope and
working rules: `PROJECT.md`.** The argument with all numbers: `PROPOSAL.md` (Korean: `PROPOSAL_ko.md`).

LLMs can solve geometry, optimization, contest and word problems by writing a program. Programs can be silently wrong, and thinking longer
is expensive. We look for the cheapest way to get exactly right answers: a program, the missing fact, a free check, and thinking only
when the check fails.

![Findings at a glance](figs/fig21_results_glance.png)

## 1. Files

```
PROJECT.md                     goal, claim, scope, working rules, status
README.md                      this manual
PROPOSAL.md, PROPOSAL_ko.md    the argument with every number (English, Korean)
bench.py                       one entry point: list / download / serve / run / submit (Slurm) / analyze
poc/run_*.py                   benchmark harnesses (each explains its options at the top)
poc/analyze_*.py               analyses of the stored rows
poc/slurm/                     Slurm job template (job.sh), generic lane (lane.sh), experiment lanes
poc/queues/                    the exact commands of the old servers' runs (records; see poc/queues/README.md)
docs/                          lab log (FINDINGS.md), pre-registrations (prereg/), notes, cluster state (SLURM_HANDOFF.md); index docs/README.md
results/                       problem sets and reference data (model outputs *.jsonl and logs are not in git)
figs/, *.pptx                  figures; the talk (Proposal_Team5*.pptx) and the full findings deck
```

## 2. Setup

```bash
pip install -r poc/requirements.txt sympy math-verify pandas   # generated programs run with this Python, so it needs OR-Tools
pip install vllm                                               # model server (we used vLLM 0.22)
python poc/sanity_check.py                                     # harness check without a model (CPU)
```

**Models** come from Hugging Face into `$MODELS_DIR/<model id>` (default `/SSD/huggingface`); the command checks free space first,
resumes interrupted downloads and skips duplicate weight formats. **External benchmark data** (OptMATH, OptiBench, MAMO, BWOR, LogiOR)
is read from `$POC_DATA` (the loaders in `poc/run_nlopt.py` name the source of each).

```bash
export MODELS_DIR=/path/to/a/large/disk
python bench.py download q14a oss20 q8b      # the three 24 GB models (--dry only shows what would be downloaded)
```

| Alias | Model | Download | Smallest GPU | Example GPUs |
|---|---|---|---|---|
| `q8b` | Qwen/Qwen3-8B (16-bit) | 16 GB | 24 GB (20k context) | RTX 3090, RTX 4090, A100 40GB, L40S |
| `q14a` | Qwen/Qwen3-14B-AWQ (4-bit) | 10 GB | 24 GB | RTX 3090, RTX 4090, A10G |
| `oss20` | openai/gpt-oss-20b (4-bit MXFP4) | 14 GB | 24 GB | RTX 3090, RTX 4090, L4, A10G |
| `q35` | Qwen/Qwen3.5-9B (16-bit; text only: `--language-model-only`) | 19 GB | 24 GB (37k context; hybrid attention, 73k-token KV) | RTX 3090 (HO-N, the unseen-model test) |
| `q14b` | Qwen/Qwen3-14B (16-bit) | 30 GB | 48 GB | L40S, RTX 6000 Ada, A100 80GB |
| `q32b` | Qwen/Qwen3-32B-AWQ (4-bit) | 19 GB | 40 GB | A100 40GB, L40S, RTX 6000 Ada |
| `q36` | Qwen/Qwen3.6-35B-A3B-FP8 (8-bit) | 38 GB | 80 GB | H100, RTX PRO 6000 |
| `oss120` | openai/gpt-oss-120b (4-bit MXFP4) | 65 GB | 80 GB | H100 80GB, H200, RTX PRO 6000 |

Results up to 2026-10-20 come from NVIDIA RTX PRO 6000 Blackwell (96 GB; 32k context, 88% of memory), from 2026-10-22 from RTX 3090
(24 GB; 20k context, 92% of memory). On a smaller GPU shorten the context, e.g. `python bench.py serve q8b --frac 0.95 -- --max-model-len 16384`.
On Blackwell, `poc/serve_gpu.sh` sets `VLLM_USE_FLASHINFER_SAMPLER=0`, which vLLM 0.22 needs there.

## 3. Running on one machine

```bash
python bench.py list                                              # benchmarks, arms (prompt conditions), model aliases
python bench.py serve oss20 --gpu 0                               # vLLM server on port 8041 (prints the PID; stop with kill <PID>)
python bench.py run geo none --model oss20 --effort low --seed 1  # one arm of one benchmark -> results/
python bench.py run geo none --model oss20 --dry                  # only print the underlying command
```

Run everything from the repository root. One server uses port 8041; for a second model give it its own GPU and port
(`serve oss120 --gpu 1 --port 8042`, then `run ... --port 8042`). Anything after `--` in `bench.py run` is passed to the harness.

## 4. Running on the Slurm cluster (current setup)

Every model run is a Slurm job inside the project's docker image. The login node is for editing, submitting, and reading results.
Run all commands from the repository root. The current state of the work on the cluster is in `docs/SLURM_HANDOFF.md`.

### 4.1 What is where

| on the cluster (host) | inside a job's container | what |
|---|---|---|
| `/home1/leesangjun/SJ/POSTECH/nlp` | `/NAS/SJ/POSTECH/nlp` | this repository; every job runs from here |
| `/home1/leesangjun/nlp_project_261021.tar` | image `nlp_project:261021` | vLLM 0.22.0 + torch 2.11 cu130 (`/opt/conda`); client and sandbox Python `/root/venvs/llm_algo_poc` (= `$P`) |
| `/home/leesangjun/SSD/huggingface` | `/SSD/huggingface` | shared model pool (root-owned) |
| `/home1/leesangjun/SJ/POSTECH/nlp_data` | `$POC_DATA` = `/NAS/SJ/POSTECH/nlp_data` | external benchmark data (MAMO, OptMATH, OptiBench, BWOR, LogiOR) |
| `/home1/leesangjun/out/nlp/<jobid>.out` | | job log: node, image load time, `lane exit <code>` |

These are the paths of the account that runs the jobs. For another account, change them in `poc/slurm/job.sh`: the log path, the image
file, and the `-v` mounts.

### 4.2 Partition and rules

- **Partition `RTX3090`** (24 GB, the GPU the project targets). The team's other projects use RTX6000ADA, L40S and A100-80GB; use those
  only when really needed, and agree first.
- One GPU and 4 CPUs per job. Never set `--time`, and add no `-q` on this partition. Stop jobs with `scancel <jobid>`, never by killing
  their processes.
- A node loads the image on its first job, which takes 2.5–4.5 minutes; later jobs on that node start at once. `--nodelist=<node>` reuses
  a warm node, and the first line of each job log names its node.
- On a 3090 every 24 GB model serves at 92% of memory with a 20k context (`--max-model-len 20480`), so keep thinking budgets at
  `--max_tokens 16000` or less. Runs with larger budgets (contest high effort, Qwen3.6 with 80k) need a larger GPU.

### 4.3 Submitting

```bash
# a standard arm of bench.py: one job = one server + all seeds (--effort low|medium|high for gpt-oss; --dry only prints the sbatch line)
python bench.py submit geo fact --model q14a --seeds 1,2,3

# any model + any client commands: one job, commands run in parallel against the job's server (--seq: one after another)
sbatch -J ob_q8b poc/slurm/job.sh poc/slurm/lane.sh Qwen/Qwen3-8B ob_q8b \
  'NLOPT_SET=optibench $P poc/run_nlopt.py q8b_optibench free 1 --max_tokens 8192' \
  'NLOPT_SET=optibench $P poc/run_nlopt.py q8b_optibench freef 1 --max_tokens 8192'

# an experiment's own lane script, e.g. the setup check (10 OptiBench problems per 24 GB model)
sbatch -J smoke poc/slurm/job.sh poc/slurm/smoke.sh
```

`lane.sh` arguments are `[--vllm '<vLLM args>'] [--frac F] [--seq] <model dir under /SSD/huggingface> <tag> '<command>' ...`. The
defaults are `--max-model-len 20480` and 0.92. Inside a command, `$P` is the client Python and `POC_BASE_URL` points at the job's server.
Put `POC_REASONING_EFFORT=low` (or medium / high) before `$P` for gpt-oss, and quote each command in single quotes so `$P` reaches the
job unexpanded. The scripts in `poc/queues/` are records of the old servers' runs, not jobs; `poc/queues/README.md` shows how to turn
one of their lanes into a job.

**Sizing jobs** (measured on RTX 3090, 2026-10-22):
- **Cheap arms** (no thinking) are fast: one model's free + usage-card arms on BWOR and LogiOR, 3 seeds, took 10–35 minutes in one job.
- **Qwen3 thinking arms** (10–12k tokens per problem) are slow, so give each seed its own job. One job per seed finished about 3× sooner
  than three seeds sharing one server, and free RTX3090 slots are usually available.
- **Dependent steps** chain with `sbatch --dependency=afterok:<id>[:<id>...]`. For example, the label-free library arm (`run_form.py
  formx`) needs every model's cheap programs first.

### 4.4 Watching, resuming, stopping

```bash
squeue -u $USER                                   # state and node of your jobs
tail -f /home1/leesangjun/out/nlp/<jobid>.out     # node, image load, "lane exit <code>"
tail results/run_<tag>.log                        # each client's own output (lane.sh)
tail results/server_vllm_<tag>.log                # vLLM: model load, KV cache size, throughput, errors
wc -l results/x3/opt_<tag>_<arm>_s<seed>.jsonl    # rows written so far (one per problem)
scancel <jobid>
```

- **Nothing written is lost.** Rows are written as each problem finishes and every harness resumes, so a cancelled or crashed job can be
  resubmitted with the same command and it continues.
- **`lane exit 0` only means the lane finished,** not that every client succeeded: check the row counts.
- **If the server does not start,** the reason is in `results/server_vllm_<tag>.log` and `results/gpu_choice.log`.
- **File ownership:** files a job writes are root-owned until the job ends, when it hands `results/` back to you.

### 4.5 Analyses and other CPU work

- **Login node:** analyses that only read stored rows run there with the system Python, for example `poc/analyze_ho.py`,
  `analyze_which_fix.py` and `analyze_input_tokens.py` (the last needs `pip install --user tokenizers`).
- **A job in the image:** analyses that run stored programs again (geometry checks: `analyze_hogc.py`, `analyze_n10.py`, `analyze_hog.py`)
  run as a job. An argument that is not a `.sh` file runs as a command:
  `sbatch -J an poc/slurm/job.sh '$P poc/analyze_hogc.py > results/hogc_analysis.log 2>&1'`.
- **CPU partitions** (`-p cpu-max16,cpu-max10,cpu-max24 -q nogpu --gres=none`) are often booked for days. When they are, submit the same
  command as an ordinary RTX3090 job.

### 4.6 Adding a model or a dataset

- **Models:** your own user cannot write the model pool, which has a 1 MB user quota; only root inside the container writes there.
  1. Download the model on the login node, which has internet, into `nlp_data/stage/<name>` with `huggingface_hub.snapshot_download`.
  2. Compare the file sizes with the Hub.
  3. Copy it into `/SSD/huggingface/<org>/` from inside a job, as `poc/slurm/smoke.sh` did for Qwen3-14B-AWQ.
- **Datasets:** put the files under `nlp_data/<name>/` and add a loader to `problems()` in `poc/run_nlopt.py` that reads `$POC_DATA`;
  the BWOR and LogiOR loaders are examples. Name the source in the loader's comment.

The raw outputs of the old servers (up to 2026-10-20, 2.0 GB, not in git) have been copied into `results/`. How to reach the old storage
is in the team's local notes, not in this public repository.

## 5. Analyses

Every output row stores its tokens (`out_tokens`), so accuracy always comes with its cost.

```bash
python bench.py analyze <id> ...                                   # = python poc/analyze_<id>.py ...
HO_SET=optibench python poc/analyze_ho.py oss20 q14a q8b           # held-out policies with 95% intervals and token ratios
python poc/analyze_which_fix.py [--census]                         # when a fact pays (usage-crash census)
python poc/analyze_input_tokens.py                                 # input tokens of the held-out policies
python poc/analyze_hogc.py [--edge] [--mr]                         # held-out geometry: second views against the check leak
python poc/analyze_hox.py; python poc/analyze_hod_gate.py q8b      # a second model's program as the check; differential test on edge inputs
python poc/analyze_budget.py                                       # worst case of the 16k thinking budget for every held-out cell
python poc/analyze_hop.py [--repair] [model ...]                   # 30-label pilot over the held-out cells (FF-R0 as a fifth policy)
python poc/analyze_hol.py                                          # label-free pilot from agreement (negative result)
python poc/analyze_hon.py q35                                      # the unseen model: FF vs THINK, budget worst case, fact gains
python poc/analyze_hotf.py [--geo] [model ...]                     # the fair baseline: always thinking given the same fact
python poc/analyze_hop.py --repair --fair                          # 30-label pilot against the fact-matched thinking arm
HO7_CELLS=optibench:formx,bwor:formx python poc/analyze_ho7.py q35 # one cheap repair before thinking
python poc/merge_shards.py results/x3/opt_<tag>_<mode>_s<seed>.jsonl  # after a run split with NLOPT_SHARD=i/k
```
Geometry analyses import the client (`llm.py`): on a login node without the container use Python ≥ 3.10 and a stub `openai` module on
`PYTHONPATH` (the analyses never call a model).

The predictions and results of each experiment are in `docs/prereg/PREREG_<id>.md`; the commands behind each number in
`poc/queues/queue_s2_<id>.sh` (old servers) and `poc/slurm/` (Slurm).

## 6. Harness facts that cost us time

- Rows are flushed as they finish and runs resume: re-running the same command skips finished rows; a torn line is skipped.
- The sandbox runs BLAS / OpenMP single-threaded (else `import scipy` exceeds the CPU limit); multi-threaded CP-SAT needs a CPU-time limit far
  above the wall time (the free-solver modes use 3,600 s).
- gpt-oss with a small `max_tokens` returns empty content (reasoning eats the budget): use ≥ 2,000 and count empty replies. Effort via
  `POC_REASONING_EFFORT`; Qwen3 thinking via `--think`. Budgets that are too small or non-card sampling make thinking look worse than it
  is (Qwen3.6: AIME 48% → 94% with the card's settings and an 80k budget): report cap hits.
- Grading: word problems `run_nlopt.correct` (abs 1e-2 or rel 1e-3; 'No Best Solution' is a value); geometry = right on all 8 copies
  (moved, rotated, mirrored, permuted, scaled, 10^9-shifted, degenerate); contests = all official + generated tests; math = math-verify.

## 7. Reproducing the talk's examples

```bash
python bench.py serve q32b --gpu 0
for arm in nodoc doc snippet; do python bench.py run co $arm --model q32b --seed 1; done   # slide 6: library facts
for arm in none k8 think; do python bench.py run geo $arm --model q32b --seed 1; done     # slide 7: distracting tools
N10_PREFIX=q32b python bench.py analyze n12 1 geo                                         # think only when the two programs differ
```

Contest problems (gpt-oss-120b; `CC_SET=full poc/run_cc.py`, analyses `bench.py analyze n8` / `n13`) and Solomon reuse
(`bench.py run vrptw plain --model oss120 --effort low`, then `REUSE_SEEDS=1,2 python bench.py analyze reuse_curve oss120_low_plain`) need
an 80 GB GPU. Figures and slides: `python poc/make_figures_frame.py`, `node poc/make_slides.js` (needs `npm install pptxgenjs`),
`python poc/export_slide_figs.py`.
