# Pre-registration HO: does the whole label-free recipe hold on an unseen, harder optimization benchmark?

Written 2026-10-19 18:0x UTC, before any run. Results are appended below without editing this section.

**Why (the decisive test the project still lacks).** Every recipe component was found or tuned on NL4OPT / IndustryOR / MAMO; MAMO was held
out, but its recurring templates favour the program library (FORM2). OptMATH-Bench (100 test problems as shipped with STORM's code; larger
production / scheduling / network / routing MILPs written with many decimal parameters) has never been used here. If the recipe (automatic
fact → two programs + strict check → library → think only on failure) is a real method for 24 GB-GPU models, it must hold here against
always-thinking and the trained specialist STORM, at its cost.

**Setup** (poc/queues/queue_s2_ho.sh; NLOPT_SET=optmath; grader = run_nlopt.correct, as everywhere). Models that fit one 24 GB GPU:
gpt-oss-20b (cheap arms low effort, thinking = medium), Qwen3-14B-AWQ, Qwen3-8B (thinking on, 16k). Arms: mip (no fact, s1), mipf (hand
snippet, s1), mips (automatic fact: the model's own shortest check-passing program from NL4OPT, s1–3), thinks (thinking + automatic fact,
s1–3), then formx (library: the program of the most similar OTHER OptMATH problem from the three models' strict-check-passing mips programs,
s1–3). STORM-Qwen3-4B with its official tool-integrated inference (3 samples) when a GPU frees. Policies as in PREREG_X7 / FORM: CHEAP,
FF, FFR-strict (two programs run, agree and are not 'No Best Solution'; else think), THINK; with mips or formx as the cheap arm.

**Predictions.**
- HO-P1: the automatic fact beats no fact on the cheap program for every model (seed 1), as on X6 / MAMO.
- HO-P2 (main): FFR-strict (mips) is within 3 points of always-thinking at ≤ 50% of its tokens, for each model (seed means).
- HO-P3: the library (formx) raises the cheap program by ≥ +2 points over mips if OptMATH problems recur in type (it is generated from seed
  families), and the FFR pipeline by ≥ +1 at fewer tokens; if problems do not recur, ≤ +1 (as on NL4OPT + IndustryOR).
- HO-P4: STORM is ≥ 5 points above the best 24 GB recipe at ≥ 3 × its tokens (its MAMO lead was +3.0 at 4.4 ×).
- HO-P5 (failure kinds, read from raw programs): most wrong-but-running programs on OptMATH mis-transcribe or drop parameters / index sets
  (large data), not API errors — so facts help less here than on MAMO.

## Setup problem found in the raw programs, and addendum HO-L (2026-10-19 18:37 UTC, before running the new arms)
gpt-oss-20b, pywraplp arms (seed means): no fact 32.0% @ 1.1k, hand snippet 28.0%, automatic fact 26.0%, thinking 32.7% @ 5.4k; 66 of 300
automatic-fact programs print 'No Best Solution'. Raw: these are NOT over-strict models — the problems are nonlinear (second-order cone /
quadratic constraints; 27 of the 100 texts mention quadratic / cone / nonlinear terms) and our prompt demands OR-Tools pywraplp, so the
model correctly writes "this cannot be modelled with pywraplp" and prints No Best Solution (optmath-11, optmath-7). The held-out result
would measure our prompt's library restriction, not the recipe. Other raw errors: an asymmetric weight table read as symmetric
(optmath-6, 25 vs 49) and a problem whose text omits which operations share a machine (optmath-10, ill-posed).
**HO-L:** the same models with a prompt that lets the model pick the solver for the problem class (OR-Tools pywraplp / CP-SAT, cvxpy for
convex continuous models incl. quadratic and second-order cone, scipy.optimize; cvxpy 1.9.3 + scipy 1.17.1 installed in the run
environment): arms free (cheap, s1–3) and thinkfree (thinking, s1–3); gpt-oss-20b first, then Qwen3-14B-AWQ and Qwen3-8B. The automatic
fact cannot cover cvxpy (no checked cvxpy programs exist in NL4OPT / MAMO); the library arm (formx) can, if OptMATH programs pass the check.
- HO-L-P1: free beats mip by ≥ +8 points for gpt-oss-20b (most of the 22% 'No Best Solution' become numbers; about half of those right).
- HO-L-P2: with free as the cheap arm, FF (think if the program fails or prints No Best Solution) is ≥ always-thinking at ≤ 70% of its
  tokens for each model (seed 1–3 means).

## HO-L harness bug (2026-10-19 19:39 UTC): first HO-L numbers withdrawn, re-run
The first HO-L run looked like a large negative (gpt-oss-20b free 16.3% vs pywraplp 32.0%; Qwen3-14B-AWQ thinkfree 7.6% vs thinks 26.3%). Raw:
all 22 of gpt-oss-20b's cvxpy programs (seed 1) ended 'tle' with empty output. Cause: in the sandbox (RLIMIT_AS 4 GB, RLIMIT_CPU = 60 s),
importing scipy starts one OpenBLAS thread per core and the import alone exceeds the CPU limit (`import scipy.optimize`: killed after 57 s;
numpy and OR-Tools import in 0.1 s, so earlier runs — which had no scipy installed — are unaffected). A second cause: CP-SAT programs
chosen under the free prompt run many worker threads and hit RLIMIT_CPU (the H5 bug). Fixes: BLAS / OpenMP single-threaded in the sandbox
(cvxpy import + a cone solve: 0.6 s), and a CPU limit of 3,600 s for the free modes (wall clock still 60 s). The buggy outputs are kept as
results/x3/opt_*_optmath_{free,thinkfree}_s*_sandboxbug.jsonl; HO-L re-runs with the same prompts, seeds and predictions.

## Interim results, gpt-oss-20b (2026-10-19 19:47 UTC; after the sandbox fix; thinkfree 290 / 300 rows)
| arm (3 seeds) | accuracy @ tokens | 'No Best Solution' | nonlinear-text problems (27) / others (73) |
|---|---|---|---|
| mip (no fact, s1) | 32.0% @ 1.09k | 24 / 100 | 33.3 / 31.5% |
| mips (automatic fact) | 26.0% @ 1.07k | 66 / 300 | 19.8 / 28.3% |
| thinks (thinking + automatic fact) | 32.7% @ 5.39k | 35 / 300 | 35.8 / 31.5% |
| free (solver choice) | 25.3% @ 1.01k | 74 / 300 | 32.1 / 22.8% |
| thinkfree | 36.6% @ 4.43k | 44 / 290 | 38.5 / 35.5% |
Policies, seeds 1 / 2 / 3: **FF (mips, think on failure or 'No Best Solution') 37.0 / 35.0 / 43.0% @ 3.3–4.2k vs always thinking 34.0 / 31.0 /
33.0% @ 5.4k**; FFR 37.0 / 33.0 / 34.0% @ 6.5–6.9k. With solver choice: FF 39.4 / 36.6 / 41.8% @ 3.0–3.3k vs always thinkfree 34.3 / 38.7 / 36.7%
@ 3.9–4.8k; FFR 35.4 / 37.6 / 38.8% @ 5.2–5.8k.
- So far: **the recipe's core holds on the unseen benchmark** — thinking only when the cheap program fails is more accurate than always
  thinking (+4 to +10 points with the pywraplp prompt) at 62–77% of its tokens. **The agreement check does not pay here** (agreement is rare
  on hard problems, so FFR pays two cheap programs and thinks anyway: HO-P2 refuted on tokens). **The automatic fact mined from NL4OPT hurts**
  (26.0 vs 32.0% without it; HO-P1 refuted for gpt-oss-20b): a fact from easy textbook problems does not fit large structured models.
- Solver choice (HO-L-P1 refuted: 25.3% vs 32.0%) helps the nonlinear problems (+12 points over mips; cvxpy in 64 of 81) and hurts the
  linear ones (−5.5: more CP-SAT, more API errors). Raw cvxpy failures: array shape mismatches from transcribing large coefficient tables, and
  `solver=cp.ECOS`, which is not installed (SolverError → 'No Best Solution') — the same missing-knowledge error the fact was built for.

## Results, all three models and STORM (2026-10-19 20:37 UTC; library arm still running)
| OptMATH (100), seed means | cheap program (automatic fact) | always thinking | **FF: think only if the program fails / prints nothing / 'No Best Solution'** | FFR (two agree) |
|---|---|---|---|---|
| gpt-oss-20b | 26.0% @ 1.1k | 32.7% @ 5.4k | **38.3% @ 3.7k** | 34.7% @ 6.7k |
| gpt-oss-20b, solver choice | 25.3% @ 1.0k | 36.6% @ 4.4k | **39.3% @ 3.1k** | 37.3% @ 5.5k |
| Qwen3-14B-AWQ | 8.7% @ 1.3k | 26.3% @ 10.5k | 26.3% @ 8.7k | 27.0% @ 12.2k |
| Qwen3-8B | 8.7% @ 1.6k | 26.3% @ 11.7k | 28.0% @ 10.3k | 28.0% @ 14.1k |
| STORM-Qwen3-4B (official TIR, 3 samples; its own grader 47.0%) | | 40.3% @ 14.1k | | |
| gpt-oss-20b cheap program, STORM on failure (offline, same seed) | | | **43.3% @ 7.0k** (40 / 41 / 49%) | |
- **HO-P1 refuted** (the automatic fact mined from NL4OPT does not help: gpt-oss-20b 26.0 vs 32.0% without a fact; Qwen 8.7 vs 6.0 / 9.0%).
- **HO-P2 refuted** (the agreement check costs more than always thinking here: two cheap programs rarely agree on hard problems). But the
  recipe's core rule holds: **thinking only when the cheap program fails is at least as accurate as always thinking at 62–90% of its tokens
  for every model** (gpt-oss-20b +5.6 points at 69%; Qwen3-14B-AWQ ±0 at 83%; Qwen3-8B +1.7 at 88%).
- **HO-P4 refuted on accuracy, holds on cost:** STORM leads gpt-oss-20b's recipe by only 1.0–2.0 points (not ≥ 5) at 3.8–4.5 × the tokens;
  and the two compose: gpt-oss-20b's cheap program with STORM only on failure beats STORM alone (43.3% vs 40.3%) at half its tokens.
- HO-P5 (failure kinds, raw): Qwen's cheap programs crash on 58% of problems — mostly formulation, not API: products of two variables
  passed to the linear solver (`x[i] * x[j]` → TypeError; the dispersion problems need a linearisation), index errors in large data tables;
  gpt-oss-20b's wrong-but-running programs misread data (an asymmetric weight table read as symmetric) or face texts that omit data.
**Reading:** on an unseen, harder benchmark the part of the recipe that generalises is "cheap program first, pay for reasoning only on a
visible failure"; the parts tuned on easy textbook problems (the mined usage example, two agreeing programs) do not.

## HO-P3 library on OptMATH (2026-10-19 21:38 UTC; formx = the program of the most similar other OptMATH problem from the three models' strict-check-passing programs)
Cheap program: gpt-oss-20b 24.7% (mips 26.0), Qwen3-14B-AWQ 10.0% (8.7), Qwen3-8B 14.3% (8.7). FF with formx: 36.7% @ 3.9k (gpt-oss-20b; mips 38.3% @ 3.7k),
24.0% @ 7.2k (Qwen3-14B-AWQ; 26.3% @ 8.7k), 28.7% @ 7.6k (Qwen3-8B; 28.0% @ 10.3k). **HO-P3: as on NL4OPT + IndustryOR, not MAMO** — the library
saves 17–26% of the Qwen models' tokens (fewer crashes, fewer escalations) at −2.3 to +0.7 points, and helps only Qwen3-8B's first program.

## OB pre-registration (2026-10-19 21:38 UTC, before running): does the OptMATH result replicate on a second unseen benchmark?
OptiBench (Yang et al., ICLR 2025; 605 problems: linear 422 / nonlinear 183, 130 with data tables; never used here). The gold is the last listed
result (the objective; checked on a random 12, and 552 / 605 last keys name a total / min / max / profit / cost). Prompt with solver choice
(the problems are 30% nonlinear): free (cheap, gpt-oss-20b low) and thinkfree (thinking; gpt-oss-20b medium), seeds 1–3; Qwen3-14B-AWQ,
Qwen3-8B (thinking 16k). STORM with its official inference on the same problems (data/test.tir_prompt.optibench.jsonl) when a GPU frees.
poc/queues/queue_s2_ob.sh (GPU0: gpt-oss-20b then Qwen3-8B; GPU1: Qwen3-14B-AWQ).
- OB-P1 (the core rule): FF (think only if the cheap program fails / prints nothing / 'No Best Solution') ≥ always thinking at ≤ 80% of its
  tokens, for each model (seed means) — as on OptMATH (62–90%).
- OB-P2: the trained STORM-4B is within ±4 points of gpt-oss-20b's FF at ≥ 3 × its tokens (OptMATH: +2.0 at 3.8 ×).
- OB-P3: as on OptMATH, the two-agreeing-programs check costs more tokens than FF without beating it by ≥ 2 points.

## OB interim, gpt-oss-20b (2026-10-19 22:36 UTC; HO_SET=optibench poc/analyze_ho.py; 605 × 3 seeds; Qwen models and STORM running)
Cheap program (solver choice) 58.8% @ 0.49k; always thinking 68.9% @ 2.09k. Policies, seeds 1 / 2 / 3: **FF 71.9 / 70.2 / 69.9% @ 1.12–1.23k**
vs always thinking 70.6 / 67.1 / 68.9% @ 1.99–2.15k; FFR 73.2 / 70.4 / 71.2% @ 2.13–2.20k. **OB-P1 holds for gpt-oss-20b** (FF +1.8 points at 56% of
always-thinking's tokens); **OB-P3 holds** (the agreement check adds +0.9 over FF at 1.8 × its tokens). By type (cheap program): linear 73.8%,
linear with tables 51.2%, nonlinear 39.6%, nonlinear with tables 19.3%. Raw: crashes are mostly API / modelling-rule errors of the chosen
library (cvxpy DCP violations 30, `pulp` not installed 27, CP-SAT integer-only coefficients 13); of 317 wrong-but-running programs 28 are within
1% of the gold, and those read are genuinely different optima (3220 vs 3200; 240 vs 239), not grading tolerance.

## Policy choice on the unseen benchmarks (2026-10-19 23:37 UTC; offline, utility = accuracy − 0.5 × ktokens, as in PREREG_MODEL.md)
15 cells (OptMATH: 3 models × 3 seeds with the automatic fact, gpt-oss-20b × 3 seeds with solver choice; OptiBench: gpt-oss-20b × 3 seeds).
The best policy is FF in 9 cells, FFR in 4, THINK in 2. **Always using FF costs at most 1.1 points of utility in any cell (0 in 9 of 15)**;
always thinking costs up to 11.0, always FFR up to 10.8. A 30-problem labelled pilot picks with 0.3–1.3 points of regret — no better than
simply using FF. So the in-distribution result (MODEL: FF the best fixed default, regret 1.4) holds on unseen benchmarks, where no labels are
needed at all.

## OB-F pre-registration (2026-10-19 23:37 UTC, before running): does a fact help on the unseen benchmark where the failures ARE usage errors?
On OptiBench the Qwen3 models' solver-choice programs crash with usage errors in 14–21% of runs (missing attributes, wrong signatures,
pulp not installed; gpt-oss-20b 3%), unlike OptMATH where the failures were formulation / data. Arms (GPU3; queue_s2_obf.sh), seeds 1–3,
gpt-oss-20b (low), Qwen3-14B-AWQ, Qwen3-8B: freef = the solver-choice prompt + a hand-written usage card for the installed libraries
(pywraplp, cvxpy, scipy; "pulp / gurobipy / pyomo not installed"; poc/run_nlopt.py LIBCARD); formx = label-free library: the solver-choice
prompt + the program of the most similar OTHER OptiBench problem from the three models' strict-check-passing programs.
- OB-F-P1: freef halves the usage-error crashes and raises the cheap program by ≥ +5 points for each Qwen3 model; ≤ +2 for gpt-oss-20b.
- OB-F-P2: with freef as the cheap arm, FF gains ≥ +2 over FF with free, at fewer tokens (fewer failures go to thinking), for each Qwen3 model.
- OB-F-P3: formx (no human) gets ≥ half of freef's cheap-program gain for the Qwen3 models.

## OB and OB-F results (2026-10-20 00:36 UTC; results/x3/ob_analysis.log; 605 × 3 seeds; STORM still running)
| OptiBench, seed means | cheap program | always thinking | FF | FF with the usage card | FF with the label-free library |
|---|---|---|---|---|---|
| gpt-oss-20b | 58.8% (card 62.7, library 66.1) | 68.9% @ 2.09k | 70.7% @ 1.18k | 72.7% @ 1.01k | **73.0% @ 0.96k** |
| Qwen3-14B-AWQ | 41.7% (55.3, 58.8) | 48.3% @ 6.52k | 59.3% @ 3.39k | **65.2% @ 2.24k** | 63.9% @ 1.83k |
| Qwen3-8B | 27.4% (34.0, 51.6) | 57.9% @ 7.65k | 57.5% @ 4.89k | 60.1% @ 4.28k | **63.1% @ 2.74k** |
- **OB-P1 holds for gpt-oss-20b and Qwen3-14B-AWQ** (FF +1.8 at 56% and +11.0 at 52% of always-thinking's tokens) and **narrowly misses for
  Qwen3-8B** (−0.4 at 64%). **OB-P3 holds** (FFR adds 0.6–1.5 points over FF at 1.5–1.8 × its tokens).
- **OB-F-P1 holds for the Qwen3 models** (usage card +13.6 / +6.6 on the cheap program; crashes −43% / −15%, so not halved for Qwen3-8B) and is
  exceeded for gpt-oss-20b (+3.9 > +2). **OB-F-P2 holds** (FF +5.9 / +2.6 at fewer tokens). **OB-F-P3 holds and is exceeded:** the label-free
  library (the program of the most similar other OptiBench problem that passed the strict check) beats the hand-written card on the cheap
  program for all three models (+7.3 / +17.1 / +24.2 over no fact).
- Raw / leakage check (Qwen3-8B, seed 1): OptiBench has near-duplicate problems (131 of 605 selected sources share ≥ 60% of the target's words,
  e.g. the same farm text with another question). The library helps most there (65% vs 34%) but also on dissimilar sources (word overlap
  < 0.4: 44% vs 20%, n = 299): most of the gain is usage knowledge in working code, not copying a near-twin. No labels are used.
**Reading:** on a second unseen benchmark the full label-free recipe — the checked program of a similar earlier problem as the fact, a cheap
program first, thinking only on a visible failure — gives Qwen3-14B-AWQ 63.9% @ 1.8k vs 48.3% @ 6.5k for always thinking, and Qwen3-8B 63.1% @ 2.7k
vs 57.9% @ 7.7k. Where failures are usage errors (OptiBench), facts pay; where they are formulation / data errors (OptMATH), they do not.
