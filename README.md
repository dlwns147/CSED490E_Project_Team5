# Tools, Facts, and Checks

POSTECH CSED490E (Graduate NLP) team project, Team 5.

LLMs often solve math problems by writing and running a program (e.g., computational geometry, optimization with
OR-Tools). These programs can be silently wrong. We study **when they fail and what the cheapest fix is**.

| Mistake | Cheapest fix | Result |
|---|---|---|
| Doesn't know a library function | Show 5 lines of exact usage | optimal 23% → 77–90% (thinking longer: 3%) |
| Distracted by unneeded tools | Write programs with and without the tools; think only if they disagree | 99% (always thinking: 98%), 27% fewer tokens |
| The problem is hard | Think harder only when the examples fail | same 66%, 18% fewer tokens |
| The same problem repeats | Reuse one checked program | 94% valid (new program each time: 7%) |

## Files

```
bench.py                              one entry point: list / serve / run / analyze
PROPOSAL.md, PROPOSAL_ko.md           proposal (English, Korean)
PROPOSAL_slides.pptx                  10-slide overview with examples
HANDOFF.md                            server notes for continuing the work
docs/                                 lab log, one pre-registration + results file per experiment, notes (index: docs/README.md)
poc/                                  code: run_*.py benchmarks, analyze_*.py analyses, queues/ the exact commands we ran
results/                              benchmark inputs and reference solutions (model outputs *.jsonl and logs are not in git)
figs/                                 figures
```

## Setup

```bash
pip install -r poc/requirements.txt sympy math-verify pandas   # generated programs run with this Python, so it needs OR-Tools
pip install vllm                                               # model server (we used vLLM 0.22)
export MODELS_DIR=/path/to/models                              # holds Qwen/Qwen3-32B-AWQ, openai/gpt-oss-120b, ...
python poc/sanity_check.py                                     # harness check without a model (CPU)
```

## Run

```bash
python bench.py list                                 # benchmarks, arms (prompt conditions), model aliases
python bench.py serve q32b --gpu 0                   # vLLM server on port 8041 (prints the PID; stop with kill)
python bench.py run geo k8 --model q32b --seed 1     # one arm of one benchmark -> results/
python bench.py run geo k8 --model q32b --dry        # only print the underlying command
```

| Result | Commands (`python bench.py ...`) |
|---|---|
| Library facts (slide 6) | `run co nodoc`, `doc`, `snippet`, `rag3`, `think` with `--model q32b` |
| Distracting tools (slide 7) | `run geo none`, `k8`, `think` with `--model q32b`; then `N10_PREFIX=q32b python bench.py analyze n12 1 geo` |
| Hard problems (slide 8) | `run contest plain --model oss120 --effort medium` (see below for the cascade analysis) |
| Program reuse (slide 9) | `run vrptw plain --model oss120 --effort low --seed 1` and `--seed 2`; then `REUSE_SEEDS=1,2 python bench.py analyze reuse_curve oss120_low_plain` |
| Other benchmarks | `run jssp plain`, `run math text`/`prog`/`think`, `run nlopt mip`/`mipf`/`think`, `run lean gen`, `run popqa direct`/`recall`/`think` |

The slide-8 cascade analysis reads the run names `oss120_low`, `oss120_medium` and `oss120_high64k` for seeds 1–3,
so run those with the harness directly:

```bash
python bench.py serve oss120 --gpu 0 -- --max-model-len 65536
export CC_SET=full POC_BASE_URL=http://127.0.0.1:8041/v1
for s in 1 2 3; do
  POC_REASONING_EFFORT=low    python poc/run_cc.py run oss120_low     $s --max_tokens 16000
  POC_REASONING_EFFORT=medium python poc/run_cc.py run oss120_medium  $s --max_tokens 16000
  POC_REASONING_EFFORT=high   python poc/run_cc.py run oss120_high64k $s --max_tokens 62000
done
python bench.py analyze n8     # the "medium->high" row: think harder only when the examples fail
```

`analyze n13` adds the brute-force cross-check behind the 66% result; it also needs the N5 oracle run
(`docs/prereg/PREREG_N.md`).

Each harness (`poc/run_*.py`) explains its options at the top of the file. Anything after `--` in `bench.py run` is
passed to it. The exact commands behind every reported number are in `poc/queues/queue_s2_<id>.sh`, and the
predictions and results in `docs/prereg/PREREG_<id>.md`.

Figures and slides: `python poc/make_figures_explain.py`, `node poc/make_slides.js` (needs `npm install pptxgenjs`).

**Notes:** GPUs are shared: check `nvidia-smi` for a free GPU and port first. We claim a result only if it holds on
3 seeds. Every output row stores its tokens (`out_tokens`), so accuracy can always be read with its cost.
