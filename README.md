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

More: `PROPOSAL.md` (proposal; Korean: `PROPOSAL_ko.md`), `PROPOSAL_slides.pptx` (slides), `docs/README.md` (experiment index).

## Folders

```
PROPOSAL*.md, PROPOSAL_slides.pptx   proposal and slides
docs/       lab log (FINDINGS.md), per-experiment pre-registrations and results (prereg/), notes (notes/)
poc/        code: run_*.py experiments, analyze_*.py analyses, queues/ the exact commands we ran
results/    benchmark inputs and reference solutions (model outputs *.jsonl and logs are not in git)
figs/       figures
```

## Run

```bash
pip install -r poc/requirements.txt sympy math-verify pandas
python poc/sanity_check.py                           # check the harness without a model (CPU)
python bench.py list                                 # benchmarks, arms (prompt conditions) and model aliases
python bench.py serve q32b --gpu 0                   # vLLM server on port 8041; model folders under $MODELS_DIR
python bench.py run geo k8 --model q32b --seed 1     # one arm of one benchmark -> results/
```

| Experiment | Commands (`python bench.py ...`) |
|---|---|
| Geometry + unneeded tools (slide 7) | `run geo none`, `run geo k8`, `run geo think` (each `--model q32b`), then `N10_PREFIX=q32b python bench.py analyze n12 1 geo` |
| Optimization + docs (slide 6) | `run co nodoc` / `doc` / `snippet` / `rag3` / `think` `--model q32b` |
| Contest geometry (slide 8) | `run contest plain --model oss120 --effort medium` (high effort: `serve oss120 -- --max-model-len 65536`, `run ... --effort high -- --max_tokens 62000`) |
| Program reuse (slide 9) | `run vrptw plain --model oss120 --effort low` (seeds 1, 2), then `REUSE_SEEDS=1,2 python poc/analyze_reuse_curve.py oss120_low_plain` |
| Job-shop, competition math, optimization modeling, Lean, factual QA | `run jssp plain`, `run math text\|prog\|think`, `run nlopt mip\|mipf\|think\|thinkf`, `run lean gen`, `run popqa direct\|recall\|think` |

`bench.py` only fills in the settings we used; anything after `--` goes to the harness (`poc/run_*.py`, usage at the top of each).
Full commands for each experiment: `poc/queues/queue_s2_<id>.sh`. Outputs go to `results/`.

**Notes:** the Python code finds the repository root by itself; only the recorded queue scripts hard-code `/NAS/SJ/POSTECH/nlp`. GPUs are shared, so check
`nvidia-smi` for a free GPU and port. We claim a result only if it holds on 3 seeds.
