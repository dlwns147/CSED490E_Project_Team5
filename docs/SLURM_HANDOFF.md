# Handoff to the Slurm server (2026-10-20)

State at commit `7d0d055` (origin/main, github.com/dlwns147/CSED490E_Project_Team5, public). The hourly loop on the old server
(/NAS/SJ/POSTECH/nlp, 8 × RTX PRO 6000 Blackwell, GPUs 0–3) was stopped on 2026-10-20 04:2x UTC; no job is running there.

## 1. The project in one paragraph
POSTECH CSED490E team project "Tools, Facts, and Checks": computational geometry (CG) and combinatorial-optimization (CO) problems solved
by LLM-written programs, accurately and cheaply, with models that fit one 24 GB GPU. Every result is accuracy *and* tokens. The recipe:
write a cheap program first; give the model the missing knowledge as a **fact** (library usage, or a checked program for a similar
problem); run a **free label-free check** (the program runs / is feasible / metamorphic copies agree); pay for **thinking only when the
check visibly fails**. Text: `PROPOSAL.md` (+ Korean mirror `PROPOSAL_ko.md`, always updated together, short, numbers edited in place).
Lab log: `docs/FINDINGS.md` (dated, append-only). Pre-registrations with appended results: `docs/prereg/PREREG_*.md`. Index: `docs/README.md`.
Slides are maintained by a separate writing session (`PROPOSAL_slides*.pptx`, `Proposal_Team5*.pptx`, `poc/make_slides.js`) — do not edit them
unless asked.

## 2. Where the evidence stands (all 3 seeds unless noted; tokens = output tokens per problem)
| claim | evidence | file |
|---|---|---|
| Fact first, think only on a visible failure, beats always thinking (in-distribution suites) | U1: 86.7–87.5% @ 2.5–2.7k vs difficulty-based 74–75% | PREREG_U1.md |
| … holds on an unseen CO benchmark (OptMATH, 100) | gpt-oss-20b 38.3% @ 3.7k vs 32.7% @ 5.4k; ≥ always-thinking at 62–90% tokens for 3 models; STORM-4B 40.3% @ 14.1k | PREREG_HO.md |
| … and on a second one (OptiBench, 605) | gpt-oss-20b 70.7% @ 1.2k vs 68.9% @ 2.1k; Qwen3-14B-AWQ 59.3% @ 3.4k vs 48.3% @ 6.5k; Qwen3-8B tie | PREREG_HO.md (OB) |
| … and on four held-out geometry tasks | gpt-oss-20b 99.0% @ 0.8k vs 93.1% @ 1.7k; Qwen3-14B-AWQ 84.4% @ 2.9k vs 76.7% @ 8.6k; **fails for Qwen3-8B** (59.7% vs 74.0%: 64 of 216 consistently-wrong programs pass the check) | PREREG_HOG.md |
| No labels needed to pick the policy | held-out: always-FF within 1.1 utility points of the best in 15 / 15 cells | PREREG_HO.md |
| Facts without a human: the model's own checked program for a similar problem | MAMO (held out): matches the hand snippet on 3 seeds for 4 models (Qwen3-32B better by 5); OptiBench library +7 / +17 / +24 on the first program | PREREG_X7.md, PREREG_HO.md |
| Repeated formulation errors are knowledge, not effort | MAMO TSP: thinking 1–18%, hand sentence misapplied, checked program of a similar problem 47–71%; stream version keeps most of it; no gain where problems rarely repeat (NL4OPT / IndustryOR) | PREREG_X7.md (FORM, FORM2) |
| Form is not the mechanism | same knowledge as words vs code: equal for API usage; partial notes in either form can displace a working formulation | PREREG_CD.md |
| When does a fact pay? | share of first programs crashing with a usage exception ≥ 5% → +12 points on average (n = 34); below 5% unpredictable (−7 to +10). Library helps in 17 / 19 cells | PREREG_HO.md (WF, WF2) |
| Trained baselines on our harness | ORLM-8B MAMO 69.5% @ 1.1k (Qwen3-8B recipe equal); STORM-4B MAMO 81.8% @ 8.4k, OptiBench 78.7% @ 7.9k (leads our best 24 GB recipe by 3–6 at 4–8 × tokens); cheap program + STORM on failure 76.3% @ 2.3k | PREREG_X7.md, PREREG_HO.md |
| Self-consistency baseline | majority of 3 thinking runs 75.0% @ 6.3k (OptiBench, gpt-oss-20b); recipe with that vote as fallback 74.6% @ 1.9k | PREREG_HO.md |
| Contest geometry (311 Codeforces, gpt-oss-120b / 20b) | examples + brute-force-oracle gate to high 66.3% @ 24.7k ≈ always-high 66.2% @ 30.1k; approach hints (tags / own plan) do not earn their place | PREREG_N.md, PREREG_CH.md |
| Limits | checks leak (consistent wrong programs); about half of MAMO's leaked problems are wrong labels (66 disputed); proofs need a trained prover | PREREG_X7.md, PREREG_PROOF.md |

## 3. Most important next steps (in this order; each pre-registered before running)
1. **Close the check leak for weak models** — the one place the recipe fails on held-out data (HO-G, Qwen3-8B: consistent-but-wrong
   programs pass the metamorphic check). Candidate: a label-free differential check (a brute-force program on small random inputs, as the N13
   oracle for contests) as the second check on geometry; test on the four held-out tasks with Qwen3-8B / Qwen3-14B-AWQ, 3 seeds. Decision:
   FF with the stronger check ≥ always-thinking at ≤ 60% of its tokens for Qwen3-8B.
2. **Where facts do not pay** — the census rule predicts only the high side; a label-free signal for the low side (e.g. 'No Best Solution'
   rate, wrong-variable-type rate read from programs) needs a prospective test on a new model × benchmark.
3. Write-up: fold HO / OB / HOG / CD / WF into the final report (proposal already updated in place). No new replications or baselines unless a
   claim in the report needs them (user, 2026-10-19: "do important things, not superficial").

## 4. What to bring to the Slurm server
- **Code + docs + small data:** `git clone git@github.com:dlwns147/CSED490E_Project_Team5.git` (problem sets in `results/x1/problems.json`,
  `results/x3/{nl4opt,industryor,minif2f}.json`, `results/h2/cc_geometry_full.json`, `cc_valid_full.json` are tracked).
- **Raw outputs are NOT in git** (`*.jsonl`, `*.log`; `results/` = 2.0 GB: x3 351 MB, h2 384 MB, x4 327 MB, x1 66 MB). Needed only to re-run
  analyses: `rsync -a <old>:/NAS/SJ/POSTECH/nlp/results/ <new>/results/` (or the subfolder you need).
- **External data** (paths are hard-coded; change the constants or recreate the paths):
  MAMO `/SSD/huggingface/datasets/MAMO/MAMO_{EasyLP,ComplexLP}.json` (`run_nlopt.MAMO`);
  OptMATH `/SSD/lean_postech/storm/STORM/data/test.tir_prompt.OptMath.jsonl` (`run_nlopt.OPTMATH`, from github.com/tangzhy/STORM);
  OptiBench `/SSD/lean_postech/optibench/ReSocratic/data/OptiBench.json` (`run_nlopt.OPTIBENCH`, github.com/yangzhch6/ReSocratic);
  Lean 4 + Mathlib `/SSD/lean_postech/mf2f`, AlphaGeometry `/SSD/lean_postech/ag` (proof track only).
- **Models** (HF ids; local copies were under /SSD/huggingface): openai/gpt-oss-20b, openai/gpt-oss-120b, Qwen/Qwen3-8B, Qwen/Qwen3-14B-AWQ,
  Qwen/Qwen3-32B-AWQ, Qwen/Qwen3-4B, Qwen/Qwen3-1.7B, Qwen/Qwen3.6-35B-A3B-FP8, tangzhy/STORM-Qwen3-4B, CardinalOperations/ORLM-LLaMA-3-8B,
  deepseek-ai/DeepSeek-R1-Distill-Qwen-7B, THU-KEG/AdaptThink-7B-delta0.05, Goedel-LM/Goedel-Prover-V2-8B, deepseek-ai/DeepSeek-Prover-V2-7B.

## 5. Environment (versions that produced every number)
- Server: vLLM 0.22.0, torch 2.11.0+cu130 (`/opt/conda`); `VLLM_USE_FLASHINFER_SAMPLER=0` (Blackwell). Qwen3.6 needs
  `--max-num-seqs 64 --language-model-only` (+ `--max-model-len 90000` for 80k thinking).
- Client / sandbox venv (`/root/venvs/llm_algo_poc`): openai 3.29, ortools 9.15.6755, coptpy 8.0.7 (size-limited free licence), numpy 2.4.6,
  sympy 1.14, math-verify 0.9.0, cvxpy 1.9.3, scipy 1.17.1. The sandbox runs programs with this interpreter (`POC_PYTHON` overrides).
- STORM: its own venv with its official code (`/SSD/lean_postech/storm/venv`, plus pebble, math_verify, pulp, timeout_decorator, regex).

## 6. Running on Slurm (what changes)
Today a queue script (`poc/queues/queue_s2_*.sh`) claims a GPU (`mkdir results/.gpu_claim_<g>`), starts vLLM with
`bash poc/start_server.sh <model> <port> <gpu> <mem-frac> <tag> [vllm args]` (port guard, health wait) and launches clients
(`poc/run_*.py`) against `POC_BASE_URL`. On Slurm: one `sbatch` job per lane with `--gres=gpu:1`; inside, pass the allocated device
(`CUDA_VISIBLE_DEVICES` is already set: call `poc/serve_gpu.sh` with that index or edit it to keep the variable), pick a free port from the job
id, drop the `.gpu_claim` dirs, and keep the rest of the script. `serve_gpu.sh` puts caches in `/dev/shm` (HF_HOME, VLLM_CACHE_ROOT) — move them to
node-local scratch if `/dev/shm` is small. Example skeleton:
```bash
#!/bin/bash
#SBATCH --gres=gpu:1 --cpus-per-task=16 --mem=128G --time=12:00:00 --job-name=ho_q8b
cd $HOME/CSED490E_Project_Team5
PORT=$((20000 + SLURM_JOB_ID % 20000))
S=$(bash poc/start_server.sh /path/to/Qwen3-8B $PORT ${CUDA_VISIBLE_DEVICES:-0} 0.88 ho_q8b) || exit 1
export POC_BASE_URL=http://127.0.0.1:$PORT/v1 NLOPT_SET=optibench
python poc/run_nlopt.py q8b_optibench free 1 --max_tokens 8192
kill $S
```
`bench.py` (repo root) wraps the common arms: `python bench.py list | serve | run`.

## 7. Harness facts that cost us time (keep them)
- Results are flushed row by row and runs resume (re-running the same command skips finished rows); a torn line is skipped.
- Sandbox (`poc/sandbox.py`): BLAS / OpenMP single-threaded (else `import scipy` / `cvxpy` exceeds the CPU limit: fixed 2026-10-19);
  multi-threaded CP-SAT needs `cpu_s` ≫ wall time (free-solver modes use 3,600 s).
- gpt-oss: a small `max_tokens` returns empty content (reasoning eats the budget) — use ≥ 2,000 and count empty replies; effort via
  `POC_REASONING_EFFORT` or `chat(..., effort=)`. Qwen3 thinking via `enable_thinking`; card sampling via `POC_THINK_SAMPLING`.
- Grading: word problems `run_nlopt.correct` (abs 1e-2 or rel 1e-3; 'No Best Solution' as a value); geometry = right on all 8 metamorphic
  copies; contests = all official + generated tests; math = math-verify. STORM is regraded with ours (`poc/analyze_storm.py <set>`).
- Treat a surprising number as a harness bug until the raw programs say otherwise (it was, three times this week: sandbox BLAS, STORM ids,
  no-think STORM).
- Old-server traps that may not apply on Slurm: the NAS was CIFS (no exec bits → `bash poc/x.sh`; never `sed -i`; no symlinks); kill by PID,
  never PID 1; detach long jobs (`setsid nohup`).

## 8. Working rules (user's standing instructions)
Pre-register predictions (with numbers and a decision rule) in `docs/prereg/PREREG_*.md` before running; report accuracy *with* tokens; at
least 3 seeds for a positive claim; read raw programs, not only scores; explain methods and results for a first-time reader; append dated
entries to `docs/FINDINGS.md`; update `PROPOSAL.md` and `PROPOSAL_ko.md` together (short, in place); commit and push after each change (public
repo: scan the staged diff for secrets, never add raw outputs); before any run ask "does this change the project's main claim?" — if not, skip it.
