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

`poc/slurm/job.sh` runs one job on one allocated GPU inside the project's docker image (paths, port, caches and the client Python are set
there; see its header). `poc/slurm/lane.sh` serves one model and runs client commands against it. `bench.py submit` writes such a job for
the standard arms. Use the RTX3090 partition; keep thinking budgets ≤ 16k tokens there (the lane serves a 20k context).

```bash
python bench.py submit geo fact --model q14a --seeds 1,2,3          # one job: server + three seeds (--dry to only print)
sbatch -J smoke poc/slurm/job.sh poc/slurm/smoke.sh                 # setup check: 10 OptiBench problems per 24 GB model
sbatch -J ob_q8b poc/slurm/job.sh poc/slurm/lane.sh Qwen/Qwen3-8B ob_q8b \
  'NLOPT_SET=optibench $P poc/run_nlopt.py q8b_optibench free 1 --max_tokens 8192'
```

CPU-only analyses that re-run stored programs use the same image (`sbatch -p cpu-max16,cpu-max10,cpu-max24 -q nogpu --gres=none
poc/slurm/job.sh '$P poc/analyze_x.py'`; when CPU partitions are crowded, submit them as a GPU job). Cluster state, data locations and
environment notes: `docs/SLURM_HANDOFF.md`.

## 5. Analyses

Every output row stores its tokens (`out_tokens`), so accuracy always comes with its cost.

```bash
python bench.py analyze <id> ...                                   # = python poc/analyze_<id>.py ...
HO_SET=optibench python poc/analyze_ho.py oss20 q14a q8b           # held-out policies with 95% intervals and token ratios
python poc/analyze_which_fix.py [--census]                         # when a fact pays (usage-crash census)
python poc/analyze_input_tokens.py                                 # input tokens of the held-out policies
python poc/analyze_hogc.py [--edge]                                # held-out geometry: second views against the check leak
```

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
- On the Slurm cluster the host user may not write the shared model pool (`/SSD`); the container does (see `docs/SLURM_HANDOFF.md`).

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
