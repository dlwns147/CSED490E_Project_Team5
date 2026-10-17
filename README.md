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
bash poc/start_server.sh <model dir> 8041 <gpu> 0.88 <tag>   # vLLM server (OpenAI-compatible)
export POC_BASE_URL=http://127.0.0.1:8041/v1
export POC_REASONING_EFFORT=medium                           # gpt-oss only: low | medium | high
python poc/sanity_check.py                                   # check the harness without a model
```

| Experiment | Example command |
|---|---|
| Geometry + unneeded tools (slide 7) | `python poc/run_geo_cross.py --model_tag S2_N10_geo_k8_s1 --distract 8 --seed 1 --temperature 0.7` |
| Optimization + docs (slide 6) | `python poc/run_co.py --model_tag S2_N10_co_snippet_s1 --arms solver --api_doc --api_doc_task --seed 1 --temperature 0.7` |
| Contest geometry (slide 8) | `CC_SET=full python poc/run_cc.py run oss120_medium 1 --max_tokens 16000` |
| Program reuse (slide 9) | `POC_REASONING_EFFORT=low python poc/run_solomon.py run oss120_low_plain 1` → `REUSE_SEEDS=1 python poc/analyze_reuse_curve.py oss120_low_plain` |
| Job-shop / competition math / optimization modeling / Lean | `poc/run_jssp.py`, `run_math.py`, `run_nlopt.py`, `run_lean.py` (usage at the top of each file) |

Full commands for each experiment: `poc/queues/queue_s2_<id>.sh`. Outputs go to `results/`.

**Notes:** scripts hard-code the path `/NAS/SJ/POSTECH/nlp`; change it on another machine. GPUs are shared, so check
`nvidia-smi` for a free GPU and port. We claim a result only if it holds on 3 seeds.
