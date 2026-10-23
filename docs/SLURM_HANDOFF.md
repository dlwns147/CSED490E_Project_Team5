# Handoff to the Slurm server (2026-10-20)

State at commit `7d0d055` (origin/main, github.com/dlwns147/CSED490E_Project_Team5, public). The hourly loop on the old server
(/NAS/SJ/POSTECH/nlp, 8 × RTX PRO 6000 Blackwell, GPUs 0–3) was stopped on 2026-10-20 04:2x UTC; no job is running there.

## 0. Status on the Slurm cluster (updated 2026-10-22 23:1x UTC)
- **Done 10-22/23 (all recorded in the prereg files and FINDINGS):** HO3–HO5 solution checker (helps on BWOR / LogiOR only), HO6 / HO7 /
  HO-G-R one cheap repair before thinking (helps the stronger models on word problems, not on geometry), HO-X a second model's program
  as the check (catches Qwen3-8B's on-input leaks, none of its 37 edge-only leaks; using gpt-oss-20b directly dominates), HO-D gate (even
  perfect edge inputs leave a differential test below always thinking), HO-B (the 16k thinking budget cannot flip a held-out tie or win),
  HO-P (30 labelled problems pick the policy within 0.87 points on 45 held-out cells; 0.74 instead of 7.8 where the recipe loses).
- **Done 10-23:** HO-L (an agreement-based, label-free pilot fails where the choice matters; the 30 labels stay) and HO-N
  (`docs/prereg/PREREG_HON.md`, `poc/slurm/hon_lane.sh` / `hon_array.sh`): on Qwen3.5-9B, never used before, fact first beats always
  thinking on all five held-out benchmarks (+3.8 to +23.5 at 28–79% of its tokens), pilot regret 0.81, census "add" calls 8 / 8.
  Nothing is running.
- **Set up and tested.** Docker image `nlp_project:261021` (`/home1/leesangjun/nlp_project_261021.tar`; vLLM 0.22.0, torch 2.11 cu130,
  client / sandbox venv `/root/venvs/llm_algo_poc`), loaded per node on first use (258 s). Partition **RTX3090** (24 GB = the project's
  target GPU; RTX6000ADA / L40S / A100-80GB are used by the user's other sessions). 4 CPUs per GPU, no `--time`, no `-q` on this partition.
- **How to run.** `poc/slurm/job.sh <lane.sh> [args]` = one job, one GPU, inside the image (paths below, `PORT`, `$P` = client python,
  results chowned back). `poc/slurm/lane.sh <model dir> <tag> '<cmd>' ...` = one server + client commands (the Slurm form of a queue-script
  lane); `python bench.py submit <bench> <arm> --model <alias> --seeds 1,2,3` writes that line for the standard arms. The old
  `poc/queues/*.sh` are records only (they claim GPUs 0-3 of a shared machine; see `poc/queues/README.md`).
- **Paths in the container** (same as the old server where possible): repo `/NAS/SJ/POSTECH/nlp` (= `/home1/leesangjun/SJ/POSTECH/nlp`),
  models `/SSD/huggingface` (root-owned shared pool; the host uid has a 1 MB quota there, so only the container writes it), external data
  `$POC_DATA` = `/NAS/SJ/POSTECH/nlp_data` (OptMATH via STORM's repo, OptiBench via ReSocratic, MAMO via CardinalOperations/MAMO).
  Lean / AlphaGeometry / STORM's venv are not installed here (proof track and STORM baselines only; their code now reads `$POC_DATA`).
- **Models present:** gpt-oss-20b, gpt-oss-120b, Qwen3-14B-AWQ (added 10-22), Qwen3-8B, Qwen3-4B, Qwen3-1.7B, Qwen3-32B-AWQ, Qwen3-14B.
  On a 3090 all 24 GB models serve with frac 0.92 and `--max-model-len 20480` (Qwen3-8B: 37k-token KV cache, ≈ 1.8 full requests).
  Also checked on a 3090 (10 OptiBench problems, solver-choice prompt, 10-21 21:4x UTC; setup only): Qwen3.5-9B (new to the project;
  `--language-model-only --max-num-seqs 64`, hybrid attention, 73k-token KV) 4/10 @ 0.86k; granite-4.1-8b 1/10 @ 0.45k; both crash
  mostly on library usage (invented attributes, gurobipy), so as new cells for step 3.2 they would sit on the census's high side.
- **Smoke test** (`poc/slurm/smoke.sh`, first 10 OptiBench problems): Qwen3-8B 2/10 @ 0.41k, Qwen3-14B-AWQ 5/10 @ 0.35k, gpt-oss-20b
  3/10 @ 0.53k; raw programs show the old failure kinds; the harness reproduces (FINDINGS 2026-10-21 18:40).
- **Raw results** of the old server (results/*.jsonl, 2.0 GB) are here (10-22 01:48 UTC), copied from the shared NFS `/NAS/SJ/POSTECH/nlp`
  with `ssh -F /home1/leesangjun/cpu_jobs/ssh_origin.conf remote 'cd /NAS/SJ/POSTECH/nlp && tar czf - results' | tar xzf - --skip-old-files`
  (`remote` = the old-server host in the team's local ssh config, not kept in this public repo; read-only there). `cpu_jobs/nlp/status_hourly.sh` (login node, nohup)
  logs jobs hourly to `out/nlp/status_hourly.log`.
- **Done on Slurm (10-22):** HO2 + WF3 on BWOR / LogiOR (PREREG_HO.md): think-on-failure ties always thinking for the two stronger models,
  loses for Qwen3-8B (leaky check on hard problems); library pays 6 / 6; WF3 rule right 10 / 12 (only its 'add' side tested).
- **Done on Slurm:** HO-G-C (`docs/prereg/PREREG_HOGC.md`, step 3.1): a second program by the same model does not close Qwen3-8B's leak;
  most leaked programs fail only edge cases the given input never contains (decision (c), see §2).

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
| … and on two more unseen benchmarks (BWOR 82, LogiOR 92): ties for gpt-oss-20b / Qwen3-14B-AWQ, loses for Qwen3-8B | FF − always-thinking −2.2 to +1.2 (CIs include 0) at 53–88% of its tokens; Qwen3-8B BWOR −8.1 [−13.4, −3.3]; 38–75% of check-passing programs wrong; two-agree check recovers accuracy at 91–120% of the tokens; library +10.1 for Qwen3-14B-AWQ on LogiOR | PREREG_HO.md (HO2) |
| … a second program by the same model does not rescue Qwen3-8B there | brute-force agreement 64.2% @ 6.6k, resample 65.6% @ 6.5k vs always-thinking 74.0% @ 9.8k; 37 / 64 leaked programs are right on the given input, wrong only on edge cases (collinear vertex, point on an edge) | PREREG_HOGC.md |
| … nor do edge-case tests the model writes (they see the leaks, but 67% false alarms: wrong boundary answers) | 72.9% @ 9.1k vs 74.0% @ 9.8k | PREREG_HOGC.md (HO-G-E) |
| … nor a check from a different model, nor even perfect edge inputs; but a 30-label pilot detects these cells | gpt-oss-20b agreement 63.2% @ 6.5k (26 / 27 on-input leaks, 0 / 37 edge-only); differential test with the benchmark's edge inputs ≤ 71.9% @ 78%; pilot regret 0.87 over 45 held-out cells, 0.74 vs 7.83 in Qwen3-8B's losing cells | PREREG_HOGC.md (HO-X, HO-D), PREREG_MODEL.md (HO-P) |
| Limits | checks leak (consistent wrong programs); about half of MAMO's leaked problems are wrong labels (66 disputed); proofs need a trained prover | PREREG_X7.md, PREREG_PROOF.md |

## 3. Most important next steps (in this order; each pre-registered before running)
1. **Close the check leak for weak models** — the one place the recipe fails on held-out data (HO-G, Qwen3-8B). Done 10-22 (HO-G-C): a
   brute-force or resampled second program by the same model catches 41–45% of the leaks and does not reach always-thinking; most leaks are
   edge-case bugs the given input never contains. HO-G-E (10-22): model-written edge-case tests (once per task) see the leaks but get the
   same boundary cases wrong (67% false alarms) → no self-written check rescues Qwen3-8B; the limit stands (closed unless a check that
   does not rely on the model's own edge-case knowledge is proposed). Reopened 10-23 as the main line: HO-G-M (model-written metamorphic
   relations, no expected answers) for geometry and HO3 (a solution checker from the text) for BWOR / LogiOR. Closed 10-23: HO-G-M, HO-G-R,
   HO-X and the HO-D gate leave the limit in place (27 on-input leaks a different model can catch, 37 edge-only leaks only edge inputs
   reveal, too costly even then); HO-P shows a 30-label pilot detects these cells. The limit is final for this project.
2. **Where facts do not pay** — WF3 (10-22, BWOR / LogiOR): the rule "add a fact unless usage crashes < 5% and non-usage failures ≥ 25%"
   (fixed from the 46 old points) was right in 10 / 12 new points, but every new cell had ≥ 5% usage crashes, so only its "add" side was
   tested; the label-free library paid in 6 / 6 (23 / 25 cells overall). The "do not add" side needs a strong, rarely-crashing model on a new
   benchmark (in 24 GB only gpt-oss-20b comes close; gpt-oss-120b would need an A100 / H200 the user keeps for other sessions — ask first).
   Practical rule meanwhile: use the library by default.
3. **Write-up** (open; format, length and deadline asked of the user 10-22): fold HO / OB / HOG / HOGC / HO2 / CD / WF into the final report
   around one claim, every number with tokens and a 95% interval (draft outline: docs/notes/REPORT_OUTLINE.md). Held-out tally for the report:
   the recipe ties or beats always thinking for gpt-oss-20b and Qwen3-14B-AWQ on every unseen benchmark at 28–88% of its output tokens
   (37–97% with input tokens); for Qwen3-8B it holds only on OptiBench with the library; the limit is the free check's leak. No new
   replications or baselines unless a claim in the report needs them (user, 2026-10-19).

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

## 6. Running on Slurm (implemented 2026-10-21; see §0)
On the old server a queue script (`poc/queues/queue_s2_*.sh`) claimed a GPU (`mkdir results/.gpu_claim_<g>`), started vLLM with
`bash poc/start_server.sh <model> <port> <gpu> <mem-frac> <tag> [vllm args]` and launched clients (`poc/run_*.py`) against `POC_BASE_URL`.
On Slurm one job is one lane: `poc/slurm/job.sh` (allocated GPU = index 0, port from the job id, caches inside the container, no claim
dirs) runs `poc/slurm/lane.sh` (or an experiment's own lane script such as `poc/slurm/hogc_brute.sh`), which calls the same
`start_server.sh` / `serve_gpu.sh` and the same clients. Example:
```bash
cd /home1/leesangjun/SJ/POSTECH/nlp
sbatch -J ob_q8b poc/slurm/job.sh poc/slurm/lane.sh Qwen/Qwen3-8B ob_q8b \
  'NLOPT_SET=optibench $P poc/run_nlopt.py q8b_optibench free 1 --max_tokens 8192'
python bench.py submit geo fact --model q14a --seeds 1,2,3 --dry      # prints the sbatch line for a standard arm
```
CPU-only analyses that re-run stored programs use the same image (`sbatch ... -p cpu-max16,cpu-max10,cpu-max24 -q nogpu --gres=none
poc/slurm/job.sh '$P poc/analyze_x.py'`); when the CPU partitions pend for long (days on 10-22), run them as a GPU job instead; light
reading of result files runs on the login node.

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

## 8. Working rules
The team's goal, scope and standing rules are kept in one place: `PROJECT.md` (§4 Working rules); how to run things: `README.md`.
