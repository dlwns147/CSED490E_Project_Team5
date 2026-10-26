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

## WF: which cheap fix — a label-free census of the first programs' failures (2026-10-20 00:38 UTC)
Exploratory, on all 23 existing (benchmark, model, fact) cells (poc/analyze_which_fix.py): x = share of the no-fact programs that crash with a
usage exception (AttributeError / ModuleNotFoundError / ImportError — Python's own exception class, no text rules), y = gain of the cheap
program when a fact (hand snippet / usage card, or the label-free library) is added. Pearson r = 0.47; mean gain **+11.2 points where ≥ 5% of
the first programs crash with usage exceptions (n = 16, every one ≥ −0.3)**, +0.9 where < 5% (n = 7, incl. OptMATH gpt-oss-20b −6 / −7).
The 5% threshold was chosen after seeing these points, so it is tested prospectively now.
**WF pre-registration (before running; queue_s2_wf.sh, GPUs 0 / 1 / 3):** three models with no fact runs on these benchmarks yet — Qwen3-4B,
Qwen3-1.7B, Qwen3-32B-AWQ — on OptiBench (free = census and base; freef usage card; formx library) and OptMATH (mip = census and base; mips
automatic fact; formx library), seeds 1–3. Rule: compute the census on the base arm first; **WF-P1: in every cell with census ≥ 5% each fact
raises the cheap program by ≥ +3 points; in every cell with census < 5% each fact changes it by ≤ +2.** WF-P2: across the new cells the rule's
call (add a fact or not) is right in ≥ 10 of 12 (benchmark, model, fact) points.

## STORM on OptiBench (2026-10-20 00:54 UTC; its official TIR inference, 3 samples)
**78.7% @ 7.9k tokens** under our grader (its own 82.4%; linear 88.9%, nonlinear 64.4%, linear with tables 71.7%, nonlinear with tables 58.0%).
Best 24 GB recipe: gpt-oss-20b with the label-free library, FF 73.0% @ 0.96k. **OB-P2 refuted on accuracy:** STORM leads by 5.7 points (FF with
solver choice alone: by 8.0), not ±4; at 6.7–8.2 × the tokens. Composition (offline, same seed): gpt-oss-20b's library program, STORM only on a
visible failure: **76.3% @ 2.3k** (Qwen3-8B 71.2% @ 3.0k, Qwen3-14B-AWQ 69.8% @ 2.4k) — 2.4 points below STORM alone at 29% of its tokens.
Caveat: STORM's training data is not public in a form we could check for overlap with OptiBench's textbook problems.

## WF results (2026-10-20 01:36 UTC; results/x3/wf_analysis.log; 12 new cells, all with census ≥ 5%)
| new cell (usage-crash census of the first programs) | automatic / usage-card fact | label-free library (formx) |
|---|---|---|
| Qwen3-32B-AWQ, OptMATH (9.3%) | mips +0.3 ✗ | +6.0 ✓ |
| Qwen3-32B-AWQ, OptiBench (14.2%) | card +17.2 ✓ | +13.2 ✓ |
| Qwen3-4B, OptMATH (30.7%) | mips +2.3 ✗ | +8.0 ✓ |
| Qwen3-4B, OptiBench (49.0%) | card +19.1 ✓ | +23.2 ✓ |
| Qwen3-1.7B, OptMATH (37.7%) | mips +0.0 ✗ | +5.0 ✓ |
| Qwen3-1.7B, OptiBench (68.7%) | card +12.5 ✓ | +33.8 ✓ |
**WF-P1 refuted for one fact type, holds for the others:** where usage crashes are common, the label-free library and the usage card always
pay (+5 to +34), but the example mined from NL4OPT does not on OptMATH (+0 to +2: a usage example from easy textbook problems does not fit
large structured models — the same miss as for the first three models). **WF-P2 narrowly refuted** (9 of 12 calls right, not ≥ 10).
All 37 points: Pearson r = 0.62; mean gain +13.2 where the census is ≥ 5% (n = 30), +0.9 where < 5% (n = 7). No new cell fell below 5%, so the
"do not add a fact" side was not tested prospectively. Scope: this census concerns library-usage facts on word problems; on the generated
geometry tasks the fact is an algorithm hint and fixes logic errors, not crashes (e.g. Qwen3-8B logic errors 19 → 5 of 108), so it is not
covered by this rule.
**WF2 pre-registration (2026-10-20 01:37 UTC, before running; queue_s2_wf2.sh, GPUs 0 / 1):** the other side of the rule, with strong models expected to make
few usage errors — gpt-oss-120b (low effort) and Qwen3.6 (no thinking) — on OptiBench (free base, freef card, formx library) and OptMATH (mip
base, formx library; mips for Qwen3.6), seeds 1–3. Rule applied per cell from the base arm's census: **WF2-P1: where the census is < 5%,
each fact changes the cheap program by ≤ +2 points; where it is ≥ 5%, the card and the library add ≥ +3.**

## WF2 results (2026-10-20 02:45 UTC; results/x3/wf_all_analysis.log)
| cell (narrow census / share failing the free check) | usage card | library | rule's call |
|---|---|---|---|
| gpt-oss-120b, OptMATH (1.7% / 31.7%) | – | −3.3 | no fact: right |
| gpt-oss-120b, OptiBench (0.4% / 11.7%) | +2.7 | +1.7 | no fact: right for the library, borderline wrong for the card |
| Qwen3.6, OptiBench (2.3% / 18.2%) | **+8.7** | **+9.6** | no fact: **wrong** |
| Qwen3.6, OptMATH (25.7% / 47.3%) | mips −2.0 | +4.3 | fact: right for the library, wrong for the mined example |
**WF2-P1 refuted** (a low census does not rule out a gain). Raw (Qwen3.6, OptiBench): the strong model wraps its solver calls in try / except
and prints 'No Best Solution' when they fail — 44 of the problems the card fixes were such hidden failures — and 97 were programs that ran but
chose the wrong variable type or library (e.g. continuous where the problem counts trucks), which the card's pywraplp IntVar example fixes. A
broader census (share failing the free check at all) predicts worse (r = 0.31 vs 0.62 over 46 points). **Revised reading:** the usage-crash
census tells where facts pay most (+12.0 on average where ≥ 5%, n = 34) but not where they do not (+2.1 where < 5%, n = 12, range −7 to +10).
The label-free library raised the first program in 17 of 19 model × benchmark cells (up to +34); it hurt only the gpt-oss models on OptMATH
(−3.3, −7.3), whose failures there are formulation and data errors. Practical rule: use the library by default.

## Self-consistency baselines (offline, the existing 3 seeds as 3 samples)
| | majority of 3 cheap programs | FF (one cheap program, think on failure) | majority of 3 thinking runs | FF with majority-of-3 thinking as the fallback |
|---|---|---|---|---|
| OptiBench gpt-oss-20b (library) | 68.9% @ 1.4k | 73.0% @ 1.0k | 75.0% @ 6.3k | **74.6% @ 1.9k** |
| OptiBench Qwen3-14B-AWQ (library) | 57.9% @ 1.1k | 63.9% @ 1.8k | 64.1% @ 19.5k | **65.6% @ 4.8k** |
| OptiBench Qwen3-8B (library) | 56.7% @ 1.2k | 63.1% @ 2.7k | 65.6% @ 22.9k | **66.1% @ 7.5k** |
| OptMATH gpt-oss-20b (mips) | 34.0% @ 3.2k | 38.3% @ 3.7k | 35.0% @ 16.2k | 36.3% @ 8.9k |
Voting over cheap programs is below FF everywhere. Self-consistency over thinking runs (the standard test-time-scaling baseline) is the most
accurate on OptiBench, and the recipe composes with it: thinking only on a visible failure, by majority of three, matches or beats it at
24–33% of its tokens. On OptMATH more thinking samples do not help (thinking itself is weak there).

## HO2 + WF3 pre-registration (2026-10-22 02:3x UTC, Slurm / RTX 3090, before any run on these data)
**Data (never used here):** BWOR (SJTU/BWOR, 82 textbook OR problems: IP 34, LP 30, MIP 11, NLP 5, goal programming 2; 2 without an optimum
→ gold 'No Best Solution') and LogiOR (LabMem012/LogiOR, 92 logistics problems: ILP 43, LP 22, NLP 16, MILP 11; only the description is
shown, never its model or gurobipy code). Loaded by `run_nlopt.problems('bwor' | 'logior')` from `$POC_DATA`; grader `run_nlopt.correct`.
**Arms** (as OB; seeds 1–3; gpt-oss-20b low for cheap arms, medium for thinking; Qwen3 thinking 16k): free (solver-choice prompt), freef
(+ the usage card), formx (the label-free library: the program of the most similar OTHER problem of the same benchmark from the three
models' strict-check-passing free programs; run after all free runs), thinkfree. Lanes `poc/slurm/lane.sh`, one job per model and arm group.
**HO2 (the core rule on a third and fourth unseen benchmark):**
- HO2-P1: FF (free; think if the program fails, prints nothing or prints 'No Best Solution') ≥ always thinkfree at ≤ 80% of its tokens, in
  ≥ 5 of the 6 model × benchmark cells (seed means), as OB-P1.
- HO2-P2: FF with the library program as the cheap arm is ≥ FF with free in ≥ 4 of 6 cells.
**WF3 (a label-free signal for when a fact does NOT pay; fixed from the 46 existing points, analyze_which_fix.py):** for each new cell,
compute on the free arm (3 seeds, no labels) u = share of programs crashing with a usage exception and n = share failing the free check
(crash, no value, 'No Best Solution') minus u. **Rule: add the fact unless u < 5% and n ≥ 25%.** (On the 46 old points this separates the
three negative library / mined-example cells of the gpt-oss models on OptMATH from all other low-u cells; the thresholds were chosen after
seeing those points, so this is their first prospective test.)
- WF3-P1: where the rule says add, the card and the library each raise the free program by ≥ +2 points; where it says don't, each changes
  it by ≤ 0.
- WF3-P2: the rule's call is right in ≥ 10 of the 12 (cell, fact) points. If every new cell has u ≥ 5%, only the "add" side is tested
  (stated as such).

### WF3 calls, recorded before any gain was read (2026-10-22 02:55 UTC; `analyze_which_fix.py --census`, free arm, 3 seeds, no labels)
| cell | u (usage crashes) | fail the check | n (non-usage failures) | call |
|---|---|---|---|---|
| BWOR gpt-oss-20b | 6.1% | 32.9% | 26.8% | add |
| LogiOR gpt-oss-20b | 7.2% | 39.5% | 32.2% | add |
| BWOR Qwen3-14B-AWQ | 37.4% | 66.3% | 28.9% | add |
| LogiOR Qwen3-14B-AWQ | 42.0% | 76.8% | 34.8% | add |
| BWOR Qwen3-8B | 16.3% | 62.2% | 45.9% | add |
| LogiOR Qwen3-8B | 22.1% | 77.2% | 55.1% | add |
Every new cell has u ≥ 5%, so only the "add" side of the rule is tested here (as stated in WF3-P2); gpt-oss-20b is near the boundary
(u 6–7%, n ≥ 25%).

### WF3 results (2026-10-22 03:2x UTC; results/x3/wf3_analysis.log; 3 seeds; cheap program accuracy, gain = with fact − free)
| cell (call: add) | free | + usage card | + label-free library |
|---|---|---|---|
| BWOR gpt-oss-20b | 41.9% | +7.7 ✓ | +7.3 ✓ |
| LogiOR gpt-oss-20b | 37.3% | +10.1 ✓ | +5.8 ✓ |
| BWOR Qwen3-14B-AWQ | 13.4% | +10.6 ✓ | +11.0 ✓ |
| LogiOR Qwen3-14B-AWQ | 7.2% | +13.0 ✓ | +14.9 ✓ |
| BWOR Qwen3-8B | 9.8% | +0.0 ✗ | +5.7 ✓ |
| LogiOR Qwen3-8B | 9.4% | +0.7 ✗ | +6.2 ✓ |
- **WF3-P2 holds** (10 of 12 calls right); **WF3-P1 holds for the library in all six cells and for the card except Qwen3-8B.** Only the "add"
  side was tested (every new cell had u ≥ 5%), so the "do not add" side of the rule is still untested prospectively.
- Raw (Qwen3-8B, card): usage crashes do not fall (BWOR 16.3 → 15.9%, LogiOR 22.1 → 31.5%): on the routing-heavy LogiOR it writes
  `from ortools.constraint_solver import pywraplp` (38 programs) — the card shows pywraplp under `ortools.linear_solver` but not the routing
  library the model reaches for, and it attaches the name to the wrong module. The library (checked programs of similar problems) has no
  such gap (+6.2): working code of a similar problem transfers where a generic card does not (as in CD / FORM).
- All 58 points: r = 0.60; mean gain +10.9 where u ≥ 5% (n = 46), +2.1 where u < 5% (n = 12). **The label-free library now raises the
  first program in 23 of 25 model × benchmark cells** (it hurt only the gpt-oss models on OptMATH).

## HO2 results (2026-10-22 05:2x UTC; results/x3/ho2_{bwor,logior}_analysis.log; 3 seeds; paired bootstrap 95% CIs over problems)
| cell | free / always thinking | FF (free) − THINK | FF (library) − THINK | FFR (library, two agree) − THINK | free-check passers that are wrong |
|---|---|---|---|---|---|
| BWOR gpt-oss-20b | 41.9% / 59.3% @ 4.3k | +1.2 [−4.5, +6.9] at 53% | +0.8 [−6.1, +7.3] at 48% | +3.7 [+1.2, +6.5] at 112% | 41% |
| BWOR Qwen3-14B-AWQ | 13.4% / 30.1% @ 9.9k | +1.2 [−4.9, +7.3] at 75% | +4.1 [−4.1, +12.2] at 55% | +5.3 [−1.2, +11.4] at 91% | 61% |
| BWOR Qwen3-8B | 9.8% / 38.2% @ 11.6k | **−8.1 [−13.4, −3.3]** at 74% | −4.9 [−11.4, +1.2] at 65% | +0.8 [−3.3, +4.9] at 100% | 75% |
| LogiOR gpt-oss-20b | 37.3% / 51.4% @ 4.5k | −1.1 [−6.9, +4.7] at 63% | −1.1 [−6.9, +4.0] at 59% | +2.5 [−0.0, +5.4] at 118% | 38% |
| LogiOR Qwen3-14B-AWQ | 7.2% / 27.9% @ 9.8k | −2.2 [−5.4, +1.8] at 88% | **+10.1 [+4.3, +15.9]** at 74% | +8.7 [+4.3, +13.8] at 102% | 69% |
| LogiOR Qwen3-8B | 9.4% / 34.8% @ 11.4k | −2.9 [−6.5, +0.4] at 91% | −2.2 [−6.9, +2.5] at 80% | +1.8 [−0.7, +5.1] at 108% | 59% |
(token shares = the policy's output tokens as a share of always thinking's.)
- **HO2-P1 refuted:** FF with the plain cheap program is ≥ always thinking at ≤ 80% of its tokens in 2 of 6 cells (BWOR gpt-oss-20b and
  Qwen3-14B-AWQ), not ≥ 5. For the two stronger models it ties always thinking (all CIs include 0) at 53–88% of its tokens; for Qwen3-8B it
  loses (BWOR −8.1, significant).
- **HO2-P2 holds:** FF with the library is ≥ FF with free in 5 of 6 cells (it lifts Qwen3-14B-AWQ on LogiOR to +10.1 over always thinking).
- **Why (labels used only here):** these benchmarks are hard for the cheap programs (7–42% right), and the free check leaks: 38–75% of the
  programs that run and print a number are wrong, so FF keeps them. Qwen3-8B's thinking is the strongest relative to its cheap program
  (+28 points) even though 19–24% of its thinking runs stop at the 16k cap (counted wrong). Requiring two cheap programs to agree (FFR)
  recovers always-thinking's accuracy in every cell (library: +0.8 to +8.7) but costs 91–120% of its tokens.
**Reading:** on harder unseen problems the recipe's saving depends on how much its check leaks: with a cheap single-program check it saves
12–47% of the tokens at equal accuracy for the stronger models and loses for the weakest; with a strict two-program check it keeps or beats
always-thinking's accuracy but saves nothing. The label-free library is the one part that pays everywhere.

## HO3 pre-registration (2026-10-23 0x:xx UTC, before running): a solution checker as the free check on hard word problems
**Why.** HO2 located the recipe's limit on BWOR / LogiOR: 38–75% of the cheap programs that run and print a number are wrong (formulation and
data errors), so "think only when the program visibly fails" keeps them; two agreeing programs recover accuracy but cost 91–120% of always
thinking. Checking a given solution is easier than formulating the model: each constraint stated in the text can be tested on it, and the
objective recomputed. Closest work: self-verification of answers (Weng et al. 2023), verifier / debugging agents for optimization models
(OptiMUS); here an *execution-based* checker of one solution, written from the text by the same model, gates thinking.
**Arms** (BWOR, LogiOR; 3 models; seeds 1–3; cheap-arm settings): `freev` = the solver-choice prompt + "also print, on the line before the
objective, the values of all decision variables as one JSON object" (`run_nlopt.py`); `verify` (`poc/run_verify.py`) = for each freev row that
runs and prints a value, the same model gets the problem text and that JSON solution and writes a program that checks every constraint
of the text on it and recomputes the objective, printing `OK <objective>` or `VIOLATION <which>`; the check passes if it prints OK and its
objective matches the printed one (run_nlopt tolerance). Thinking arm: the stored thinkfree rows.
**Policies:** FF(freev) — think if the program fails, prints nothing or 'No Best Solution'; **FF-V** — also think if the checker does not pass
(a checker that crashes counts as not passing); THINK. Tokens: freev + checker (only where it runs) + thinking where escalated.
**Predictions** (seed means, 95% intervals over problems):
- HO3-P1: the checker flags ≥ 40% of the freev programs that run and print a value but are wrong, and ≤ 15% of the right ones (each model).
- HO3-P2: FF-V ≥ THINK − 1 at ≤ 80% of its tokens in ≥ 4 of the 6 cells (FF without the checker: 2 of 6 in HO2).
- HO3-P3: for Qwen3-8B on BWOR, FF-V closes at least half of FF's gap to always thinking (FF −8.1 in HO2).
**Decision.** If P2 holds, the recipe's free check for word problems becomes "runs + a solution checker", and the held-out claim extends to
the hard benchmarks; if only P1 holds, the checker is reported as a partial fix with its cost; otherwise the limit stands as in HO2.

### HO3 bound, recorded before any HO3 result (2026-10-22 18:5x UTC; offline on the HO2 rows, labels used only for the bound)
A *perfect* check on the cheap program (accept exactly the right ones, think on the rest) would use 83–103% of always thinking's tokens on
BWOR / LogiOR (free: 89–103%; library: 83–98%), because the cheap programs are right on only 7–42% of these problems — so **HO3-P2 (≤ 80% of the
tokens) is infeasible in most cells by construction**; it was set without this cost model (CRITIQUE item 7). The same perfect check
*raises* accuracy above always thinking (e.g. BWOR gpt-oss-20b library 69.5% vs 59.3%; LogiOR Qwen3-14B-AWQ library 41.3% vs 27.9%), because
right cheap programs are kept where thinking fails. So for HO3 the informative outcome is accuracy: P1 (flag rates) and whether FF-V
exceeds always thinking; P2 is reported as pre-registered.

## HO3 results (2026-10-22 19:0x UTC; results/x3/ho3_analysis.log; 3 seeds; paired 95% intervals over problems)
| cell | FF (freev) − THINK | **FF-V (+ solution checker) − THINK** | checker flags running-but-wrong / right programs |
|---|---|---|---|
| BWOR gpt-oss-20b | −2.0 [−7.7, +3.7] at 56% | **+3.7 [+0.8, +6.9]** at 109% | 51 / 69 (74%) · 18 / 98 (18%) |
| LogiOR gpt-oss-20b | +1.4 [−4.3, +7.2] at 70% | **+4.3 [+0.4, +8.3]** at 107% | 31 / 47 (66%) · 32 / 124 (26%) |
| BWOR Qwen3-14B-AWQ | +2.4 [−2.8, +7.7] at 72% | **+3.3 [+0.4, +6.1]** at 102% | 45 / 51 (88%) · 22 / 43 (51%) |
| LogiOR Qwen3-14B-AWQ | +1.1 [−2.9, +5.4] at 81% | +1.8 [−0.4, +4.3] at 106% | 46 / 55 (84%) · 16 / 31 (52%) |
| BWOR Qwen3-8B | −6.9 [−12.6, −1.6] at 80% | −2.0 [−4.5, +0.0] at 106% | 50 / 58 (86%) · 13 / 20 (65%) |
| LogiOR Qwen3-8B | −3.3 [−7.2, +0.4] at 95% | +0.4 [−0.7, +1.4] at 110% | 33 / 34 (97%) · 12 / 19 (63%) |
- **HO3-P1 half holds:** the checker flags 66–97% of the running-but-wrong programs (≥ 40%: holds in 6 / 6) but also 18–65% of the right
  ones (≤ 15%: refuted in 6 / 6). **HO3-P2 refuted** in 6 / 6 on tokens (102–110%; infeasible by the bound recorded before the results);
  on accuracy alone FF-V ≥ THINK − 1 in 5 / 6. **HO3-P3 holds** (Qwen3-8B BWOR: −6.9 → −2.0, 71% of the gap closed).
- **Decision: a partial fix, reported with its cost.** On hard benchmarks the solution checker turns the recipe from a tie into a
  significant accuracy gain over always thinking for the stronger models (+3.3 to +4.3 in 3 of 4 cells) at about always thinking's tokens,
  and brings Qwen3-8B to within 2 points; it is as accurate as two agreeing programs (HO2 FFR) at 5–13 points fewer tokens. It saves no
  tokens there — no check can (bound).
- Raw (false alarms, BWOR seed 1): the checker misreads the text — an inverted comparison ("minerals 92.3 < 30.0"), an invented
  constraint ("plan not available for its factory"); both models' checkers flag BWOR-056, whose text has almost no numbers. The check
  repeats the model's comprehension errors in the other direction.

## HO4 pre-registration (2026-10-22 19:1x UTC, before running): the solution checker where savings are possible (OptiBench, library)
**Why.** HO3 showed a solution checker buys accuracy but no tokens on BWOR / LogiOR, where no check can save tokens. The cost model says
savings remain possible where cheap programs are often right: on OptiBench with the label-free library, FF already beats always thinking at
28–46% of its tokens, and a *perfect* check would add +4.4 to +5.8 points while staying at 54–69% of its tokens (bound from the stored rows).
The question: does the imperfect, model-written checker convert part of that headroom into accuracy without giving up the saving?
**Arms** (OptiBench 605; 3 models; seeds 1–3; cheap-arm settings): `formxv` = the library arm (run_form.py formx: same selected program)
with the solution-printing instruction of freev; `verify` (run_verify.py, source arm formxv); thinking: the stored thinkfree rows.
**Policies:** FF(formxv), FF-V(formxv) (also think unless the checker passes), THINK; paired 95% intervals over problems.
**Predictions** (seed means):
- HO4-P1: FF-V ≥ FF + 2 points for each model.
- HO4-P2: FF-V ≥ THINK + 3 points at ≤ 70% of THINK's tokens for each model.
- HO4-P3: the checker flags ≥ 50% of the running-but-wrong library programs and ≤ 30% of the right ones.
**Decision.** P1 + P2 → the free check for word problems becomes "runs + solution checker", and the held-out claim on OptiBench is stated as
more accurate and cheaper by the measured amounts; P1 only → the checker is a knob that trades the saving for accuracy (report the curve);
neither → the checker is not worth its cost where savings are possible.

### HO3-C pre-registration (2026-10-22 19:2x UTC, before computing; offline on the HO3 rows, and on HO4's when they exist)
The checker's false alarms are its own misreadings (HO3 raw). **FF-VA:** think only if the checker does not pass **and** a second cheap program
(the same arm, next seed: s1↔s2, s2↔s3, s3↔s1) fails or prints a different value; otherwise keep the first program. The second program is
written only when the checker objects (its tokens are counted only there).
- HO3C-P1: FF-VA halves the false alarms on right programs of FF-V and keeps ≥ 70% of its catches of running-but-wrong programs (pooled per model).
- HO3C-P2: FF-VA accuracy ≥ FF-V − 0.5 points at fewer tokens, in ≥ 4 of 6 BWOR / LogiOR cells.

### HO3-C results (2026-10-22 19:3x UTC; results/x3/ho3c_analysis.log)
| cell | FF-V (checker) | **FF-VA (checker AND a disagreeing second program)** | THINK | false alarms on right programs V → VA | catches of wrong programs V → VA |
|---|---|---|---|---|---|
| BWOR gpt-oss-20b | 63.0% @ 109% | 61.4% @ 106% | 59.3% | 18 → 11 / 98 | 51 → 41 / 69 |
| LogiOR gpt-oss-20b | 55.8% @ 107% | 56.5% @ 107% | 51.4% | 32 → 12 / 124 | 31 → 26 / 47 |
| BWOR Qwen3-14B-AWQ | 33.3% @ 102% | **36.2% @ 98%** | 30.1% | 22 → 11 / 43 | 45 → 39 / 51 |
| LogiOR Qwen3-14B-AWQ | 29.7% @ 106% | 30.1% @ 104% | 27.9% | 16 → 10 / 31 | 46 → 40 / 55 |
| BWOR Qwen3-8B | 36.2% @ 106% | 37.0% @ 105% | 38.2% | 13 → 4 / 20 | 50 → 47 / 58 |
| LogiOR Qwen3-8B | 35.1% @ 110% | 34.8% @ 110% | 34.8% | 12 → 7 / 19 | 33 → 30 / 34 |
- **HO3C-P1 holds for gpt-oss-20b and Qwen3-8B** (false alarms −54% / −56%, catches kept 82% / 93%), narrowly misses for Qwen3-14B-AWQ (−45%,
  87% kept). **HO3C-P2 holds** (4 of 6 cells: ≥ FF-V − 0.5 at fewer tokens; not gpt-oss-20b BWOR −1.6, LogiOR equal tokens).
- Reading: two independent views (a checker of the solution, a second formulation) disagree with each other's errors; requiring both to
  object removes about half the false alarms at almost no loss of catches. Still no token saving on these benchmarks (bound).

## HO4 results (2026-10-22 19:4x UTC; results/x3/ho4_analysis.log; OptiBench 605 × 3 seeds; library arm with the solution printed)
| model | FF (formxv) − THINK | FF-V (checker) − THINK | FF-VA (checker AND second program) | checker flags wrong / right |
|---|---|---|---|---|
| gpt-oss-20b | **+5.0 [+3.2, +6.8] at 55%** | +5.5 [+4.0, +7.1] at 86% | 74.7% @ 84% (FF 73.9% @ 55%) | 86 / 283 (30%) · 86 / 1,159 (7%) |
| Qwen3-14B-AWQ | **+15.0 [+12.4, +17.5] at 36%** | +14.1 [+12.0, +16.3] at 65% | 64.3% @ 51% (FF 63.3% @ 36%) | 218 / 385 (57%) · 181 / 956 (19%) |
| Qwen3-8B | **+7.2 [+5.1, +9.5] at 45%** | +5.4 [+4.1, +6.8] at 79% | 65.8% @ 61% (FF 65.1% @ 45%) | 216 / 321 (67%) · 311 / 854 (36%) |
- **HO4-P1 refuted** (FF-V − FF: +0.5 / −0.9 / −1.8, not ≥ +2); **HO4-P2 refuted** (≥ THINK + 3 at ≤ 70% of its tokens only for Qwen3-14B-AWQ);
  **HO4-P3 mixed** (flags ≥ 50% of wrong programs for the Qwen models, not gpt-oss-20b at 30%; false alarms ≤ 30% except Qwen3-8B at 36%).
- **Decision: the checker is not worth its cost where savings are possible.** With the library the plain recipe already beats always thinking
  by +5.0 / +15.0 / +7.2 points at 36–55% of its tokens; the checker's false alarms and the thinking they trigger cost about what its catches
  gain (checker AND a second program: +0.7 to +1.0 points for 16–29 points more of always thinking's tokens).
**Reading (HO3 + HO4 + the bounds):** a stronger check pays where cheap programs are usually wrong (BWOR / LogiOR: from a tie to +3 to +6 points
over always thinking, no saving possible) and not where they are usually right (OptiBench: plain FF is the best trade-off). Which regime a
new benchmark is in can be read without labels from how often the cheap programs fail the free check or disagree — the next thing to test.

## HO5 pre-registration (2026-10-22 19:5x UTC, before running): which regime is a new benchmark in? A prospective test on OptMATH
**Rule (fixed from the 9 HO3 / HO4 cells, exploratory; label-free):** among the cheap programs that run and print a value, the share whose
value agrees with a second cheap program of the next seed. Agreement ≥ 85% (OptiBench 89–92%) → "easy" regime: keep the plain recipe;
< 85% (BWOR / LogiOR 49–77%) → "hard" regime: add the solution checker (it raised accuracy over the plain recipe there by +0.7 to +5.7 and
over always thinking in 5 of 6 cells; tokens cannot be saved in that regime).
**Test:** OptMATH (100; never used with the checker), 3 models, seeds 1–3: freev + verify (lane poc/slurm/ho3_lane.sh with NLOPT_SET=optmath);
thinking = the stored thinkfree rows. The agreement rate is computed first and its call recorded before any accuracy is read.
**Predictions:**
- HO5-P1: OptMATH falls in the hard regime for all three models (agreement < 85%; a perfect check would need 96–105% of always thinking's
  tokens there).
- HO5-P2: FF-V ≥ FF + 2 points for gpt-oss-20b and Qwen3-8B, ≥ FF for Qwen3-14B-AWQ (as on BWOR / LogiOR).
- HO5-P3: FF-V ≥ always thinking (seed means) for at least 2 of 3 models.

### HO5 regime call, recorded before any accuracy was read (2026-10-22 19:4x UTC; results/x3/ho5_regime_call.log)
OptMATH, freev, 3 seeds: two-program agreement among programs that run and print a value — gpt-oss-20b 59% (109 pairs), Qwen3-14B-AWQ 36%
(22 pairs), Qwen3-8B 20% (5 pairs) → **hard regime for all three models: add the solution checker** (HO5-P1 holds). Few Qwen pairs: only
11–19% of their programs run and print a value.

## HO5 results (2026-10-22 19:5x UTC; results/x3/ho5_analysis.log; OptMATH 100 × 3 seeds)
| model | FF (freev) − THINK | FF-V (checker) − THINK | FF-V − FF | checker flags wrong / right |
|---|---|---|---|---|
| gpt-oss-20b | +0.7 [−5.0, +6.7] at 75% | −1.7 [−6.0, +2.0] at 114% | **−2.3** | 37 / 100 (37%) · 28 / 60 (47%) |
| Qwen3-14B-AWQ | +2.7 [−0.0, +5.7] at 96% | +1.3 [+0.0, +3.0] at 112% | **−1.4** | 32 / 42 · 10 / 15 |
| Qwen3-8B | +1.0 [−1.0, +3.0] at 102% | −0.3 [−1.0, +0.0] at 113% | **−1.4** | 19 / 24 · 10 / 10 |
- **HO5-P1 holds** (hard regime called for all three, before the accuracies were read) but **HO5-P2 and P3 are refuted**: the checker lowers
  accuracy on OptMATH for every model (−1.4 to −2.3) and FF-V ≥ THINK only for Qwen3-14B-AWQ. **The agreement rule does not transfer:**
  low agreement is necessary for a checker to help (no help on OptiBench) but not sufficient.
- Raw (gpt-oss-20b, false alarms): OptMATH solutions carry auxiliary formulation variables (routing order variables, linearizations); the
  checker must re-interpret them and misjudges correct tours ("Subtour constraint for (0,5): lhs=6"), and 3 checkers were never written
  (no code). Checking these solutions needs the same formulation knowledge as writing them, so the check is not an independent view.
  On BWOR / LogiOR the constraints are stated directly on the decision variables, which is where the checker helped.
**Reading:** a solution checker helps where the problem's constraints can be checked on the decision variables alone (textbook-style
BWOR / LogiOR) and thinking can fix what it flags; it does not where checking needs the formulation itself (OptMATH) or where cheap programs
are mostly right (OptiBench). No label-free rule for this was found; the default stays the plain recipe with the library.

## HO6 pre-registration (2026-10-22 20:0x UTC, before running): a cheap repair before thinking, on a visible failure (BWOR / LogiOR)
**Why.** The perfect-check bound (no token saving on BWOR / LogiOR) assumes every visible failure pays for full thinking (≈ 4–12k tokens).
The failure evidence is specific — Python's error for a crash, the checker's violated constraint (HO3), 'No Best Solution' — so one short
repair turn without thinking (≈ 1k tokens) may fix many programs; thinking is then paid only when the repair also fails. Prior evidence:
repair from Lean errors was worse than a fresh attempt (PROOF-R), one repair round on contests helped little (N2); word-problem programs with
a named violated constraint have not been tried.
**Arm** (`poc/run_repair.py`; BWOR, LogiOR; 3 models; seeds 1–3; cheap-arm settings, no thinking): for each freev program that does not run,
prints nothing / 'No Best Solution', or whose solution the HO3 checker does not pass, the same model gets the problem, its program and the
evidence (the error's last lines, or the checker's VIOLATION line, or "the program printed No Best Solution") and writes a corrected program
in the freev format. **Policy FF-R:** freev program if it passes the free check and the checker; else the repaired program if it runs and
prints a value; else THINK. Tokens: freev + checker + repair (where written) + thinking where escalated.
**Predictions** (seed means; vs the stored THINK rows; 95% intervals over problems):
- HO6-P1: the repair turns ≥ 30% of the escalated items into programs that run and print a value, and ≥ 30% of those are right.
- HO6-P2: FF-R ≥ FF-V − 1 point at ≤ 75% of always thinking's tokens for gpt-oss-20b and Qwen3-14B-AWQ on both benchmarks (FF-V: 102–110%).
- HO6-P3 (uncertain): FF-R ≥ always thinking at ≤ 75% of its tokens in ≥ 3 of the 6 cells.
**Decision.** P2 → the recipe's ladder becomes cheap program → free check (+ checker where it is an independent view) → one cheap repair
with the evidence → thinking, and the hard benchmarks regain a token saving; otherwise repair is reported as not paying before thinking.

## HO6 results (2026-10-22 20:1x UTC; results/x3/ho6_analysis.log; 3 seeds; paired 95% intervals)
| cell | FF-V (HO3) − THINK | **FF-R (checker → one cheap repair → think) − THINK** | repairs that run / are right |
|---|---|---|---|
| BWOR gpt-oss-20b | +3.7 at 109% | **+5.7 [+1.2, +11.0] at 82%** | 86 / 148 (58%) · 45 (52%) |
| LogiOR gpt-oss-20b | +4.3 at 107% | **+6.5 [+0.7, +12.3] at 90%** | 90 / 168 (54%) · 51 (57%) |
| BWOR Qwen3-14B-AWQ | +3.3 at 102% | **+7.3 [+0.8, +13.8] at 70%** | 94 / 219 (43%) · 39 (41%) |
| LogiOR Qwen3-14B-AWQ | +1.8 at 106% | +4.3 [−1.4, +10.5] at 81% | 100 / 252 (40%) · 41 (41%) |
| BWOR Qwen3-8B | −2.0 at 106% | −7.3 [−13.8, −1.2] at 80% | 90 / 231 (39%) · 27 (30%) |
| LogiOR Qwen3-8B | +0.4 at 110% | −5.8 [−10.5, −1.4] at 96% | 76 / 268 (28%) · 25 (33%) |
- **HO6-P1 mostly holds** (repairs run in 28–58% of escalated items, ≥ 30% in 5 / 6; of those 30–57% right). **HO6-P2 refuted on tokens**
  (≥ FF-V − 1: 4 / 4 — FF-R is more accurate than FF-V in every stronger-model cell — but ≤ 75% of THINK's tokens only for Qwen3-14B-AWQ
  BWOR; 70–90%). **HO6-P3 refuted** (1 / 6).
- Per the decision rule the ladder is not adopted from this test. What the numbers do show: for gpt-oss-20b and Qwen3-14B-AWQ, one cheap
  repair with the evidence dominates the checker alone (more accurate and 15–31 points of THINK's tokens cheaper) and beats always thinking
  by +4.3 to +7.3 points at 70–90% of its tokens (3 of 4 intervals above 0). For Qwen3-8B it hurts: its repaired programs are accepted on the
  free check alone and 67–70% of them are wrong.
- Next (to be pre-registered separately, not inferred from this run): the repair step without the checker on other benchmarks, and
  re-checking the repaired program before accepting it.

## HO7 pre-registration (2026-10-22 20:2x UTC, before running): one cheap repair on a visible failure, no checker (OptiBench, OptMATH)
**Why.** HO6 suggested that a short repair turn with the failure evidence is a better first escalation than thinking (stronger models:
+4.3 to +7.3 over always thinking at 70–90% of its tokens on BWOR / LogiOR). This tests the step alone — the recipe's own visible-failure
check, no checker — on two benchmarks HO6 did not use: OptiBench with the label-free library (arm formx; savings possible) and OptMATH (arm
free; the checker did not help there).
**Arm** (`run_repair.py <model> <seed> <arm>`; 3 models; seeds 1–3; no thinking): for each cheap program that does not run, prints nothing or
prints 'No Best Solution', the same model gets the task, its program and the evidence and writes a corrected program (same output format).
**Policies:** FF (think on a visible failure; the existing rows), **FF-R0** (on a visible failure, the repaired program if it runs and prints a
value, else think), THINK (stored thinkfree rows). Paired 95% intervals; tokens = cheap + repair (where written) + thinking where escalated.
**Predictions** (seed means):
- HO7-P1: FF-R0 uses ≤ 75% of FF's tokens for every model × benchmark (thinking on 40–60% fewer escalated items).
- HO7-P2: FF-R0 accuracy ≥ FF − 1.5 points in ≥ 5 of the 6 cells (repairs right about as often as thinking on these items).
- HO7-P3: for Qwen3-8B, FF-R0 < FF − 1.5 in at least one cell (its repairs leak, as in HO6).
**Decision.** P1 + P2 → the recipe's ladder becomes cheap program → visible failure → one cheap repair with the evidence → thinking, stated
with the measured saving; otherwise the repair step stays an option for the stronger models only.

## HO7 results (2026-10-22 20:5x UTC; results/x3/ho7_analysis.log; 3 seeds; paired 95% intervals)
| cell | FF − THINK | **FF-R0 (repair on a visible failure) − THINK** | FF-R0 − FF | FF-R0 tokens / FF's | repaired runs · right (thinking right on those items) |
|---|---|---|---|---|---|
| OptiBench gpt-oss-20b (library) | +4.1 [+2.1, +6.1] | +4.8 [+2.7, +6.9] | +0.7 | 93% | 118 / 286 · 60 (48) |
| OptMATH gpt-oss-20b | +3.0 [−3.0, +9.3] | +6.3 [−1.0, +13.7] | +3.3 | 86% | 48 / 130 · 26 (16) |
| OptiBench Qwen3-14B-AWQ | +15.6 [+13.1, +18.3] | +16.3 [+13.5, +19.1] | +0.7 | 90% | 74 / 314 · 35 (23) |
| OptMATH Qwen3-14B-AWQ | +4.7 [+1.7, +8.0] | **+8.7 [+4.3, +13.0]** | +4.0 | 100% | 28 / 233 · 16 (4) |
| OptiBench Qwen3-8B | +5.2 [+2.6, +7.7] | +6.2 [+3.6, +8.8] | +1.0 | 84% | 140 / 481 · 103 (85) |
| OptMATH Qwen3-8B | +2.0 [−0.7, +4.7] | **+3.0 [+0.3, +6.0]** | +1.0 | 101% | 24 / 247 · 4 (1) |
- **HO7-P1 refuted** (FF-R0 uses 84–101% of FF's tokens, not ≤ 75%: only 10–41% of the repairs produce a running program, so most escalated
  items still think). **HO7-P2 holds** (≥ FF − 1.5 in 6 / 6; in fact more accurate than FF in every cell, +0.7 to +4.0). **HO7-P3 refuted**
  (Qwen3-8B does not get worse: +1.0 / +1.0).
- Per the decision rule the repair step is not adopted as a token saver. What it is: a free accuracy gain — never worse than FF, at equal or
  lower cost in 5 of 6 cells — because where the repair yields a running program it is right more often than thinking on the same items
  (in all six cells). With HO6: repair visible failures only; repairing running programs that a checker flagged made Qwen3-8B worse (HO6).

## Addendum HO-B (2026-10-22 23:0x UTC, before computing; offline): is always thinking handicapped by its 16k-token budget?
Always thinking (THINK) ran with 16,000 output tokens (what fits beside the model on a 24 GB GPU); 0.3–7.6% of the stronger models' THINK
rows hit it (Qwen3-8B 3–24%). **Worst case:** count every THINK row that hit the budget and is wrong as right — in THINK and wherever FF
escalates to it — and recompute FF − THINK with its paired 95% interval in every held-out cell (OptMATH mined example, OptiBench free /
library, BWOR, LogiOR free / library, geometry). **Prediction HOB-P1:** no cell where FF ties or beats THINK for gpt-oss-20b or
Qwen3-14B-AWQ becomes a significant loss (upper bound < 0). **Decision:** if P1 holds, no longer-budget THINK run (it cannot change the
claim) and the bound goes into the report's limitations; if not, re-run the budget-capped THINK rows of the flipping cells at 32k tokens.

### Results HO-B (2026-10-22 23:1x UTC; `python poc/analyze_budget.py`, 3 seeds; FF − THINK, paired 95% interval)
| cell | gpt-oss-20b as run → worst case | Qwen3-14B-AWQ as run → worst case | Qwen3-8B as run → worst case |
|---|---|---|---|
| OptMATH, mined example | +5.7 [+0.3, +11.3] → +2.7 [−3.0, +8.7] | 0.0 [−4.0, +4.0] → 0.0 | +1.7 [−1.3, +5.0] → 0.0 [−3.3, +3.7] |
| OptiBench, no fact | +1.8 [+0.3, +3.4] → +1.7 [+0.1, +3.3] | +11.0 → +10.9 [+8.7, +13.2] | −0.4 → −1.2 [−3.1, +0.6] |
| OptiBench, library | +4.1 [+2.1, +6.1] → +4.0 [+1.9, +6.0] | +15.6 → +15.1 [+12.5, +17.9] | +5.2 → +4.1 [+1.7, +6.7] |
| BWOR, no fact | +1.2 [−4.5, +6.9] → −2.0 [−7.3, +3.7] | +1.2 [−4.9, +7.3] → −1.2 [−7.7, +5.7] | −8.1 → −14.2 [−20.7, −8.5] |
| LogiOR, no fact | −1.1 [−6.9, +4.7] → −4.0 [−9.8, +1.4] | −2.2 [−5.4, +1.8] → −2.9 [−6.5, +1.1] | −2.9 → −5.4 [−9.8, −1.4] |
| LogiOR, library | −1.1 [−6.9, +4.0] → −4.3 [−10.1, +0.7] | +10.1 → +9.1 [+2.9, +14.9] | −2.2 → −5.4 [−10.5, −0.4] |
| geometry, helpers + hint | +5.9 [+3.5, +8.7] → +5.9 (no row capped) | +7.6 [+4.2, +11.5] → +4.2 [+2.1, +6.9] | −14.2 → −19.1 [−24.7, −13.9] |
- **HOB-P1 holds:** in the worst case no tie or win of gpt-oss-20b or Qwen3-14B-AWQ becomes a significant loss (closest: gpt-oss-20b
  LogiOR with the library, −4.3 [−10.1, +0.7]); one win becomes a tie (gpt-oss-20b OptMATH). Qwen3-8B's losses only deepen.
- **Decision:** no 32k-budget THINK run; the report states the bound (a longer budget could cost the recipe at most ~3 points in a cell and
  turn gpt-oss-20b's OptMATH win into a tie).

## Addendum HO-TF (2026-10-23 09:0x UTC, before any run): is always thinking *with the same fact* a stronger baseline?
**Why.** In the held-out table the library rows compare FF with the label-free library against always thinking *without* it (OptiBench,
BWOR, LogiOR); only OptMATH's thinking arm had the fact. That conflates the fact with where thinking goes. The fair baseline is the
thinking arm given the same prompt, library program included (`formxt`), and FF should then escalate to that arm too.
**Run:** `run_form.py <m> formx <seed> --tarm` (Qwen3: `--think`, 16k; gpt-oss-20b: medium effort, as its thinking arms), seeds 1–3, for
gpt-oss-20b, Qwen3-14B-AWQ, Qwen3-8B on BWOR and LogiOR (all problems) and OptiBench (a fixed third: problems 0, 3, 6, …, 202 of 605,
`FORM_SUBSET=0/3`, to keep the cost to ~40 GPU-hours of RTX 3090); every comparison on OptiBench uses the same 202 problems.
Policies: THINK (thinkfree, no fact), THINK+F (formxt), FF+F (formx; on a visible failure formxt). Paired 95% intervals, token shares.
- **TF-P1:** THINK+F ≥ THINK in ≥ 7 of the 9 cells (the fact helps thinking too).
- **TF-P2 (the claim):** FF+F ties or beats THINK+F (interval upper bound ≥ 0) in ≥ 5 of the 6 cells of gpt-oss-20b and Qwen3-14B-AWQ, at
  ≤ 60% of its tokens.
- **TF-P3:** for Qwen3-8B, FF+F is significantly below THINK+F on BWOR (its leak), as against THINK.
**Decision.** TF-P2 holds → the held-out claim stands against the strongest thinking baseline and the table's library rows are replaced
by the fair comparison; fails → the library rows are restated as a token-for-accuracy trade-off against thinking with the fact.

## Addendum HO-TF2 (2026-10-23 12:0x UTC, before any run; written after reading HO-TF for gpt-oss-20b, Qwen3-14B-AWQ and Qwen3-8B OptiBench)
**Why.** HO-TF shows the fact helps thinking a lot (THINK+F − THINK up to +22.6 points) and FF+F loses to THINK+F for the Qwen models
on OptiBench / BWOR. Two more comparisons in the report are not fact-matched either: held-out geometry (FF with the needed helpers + the
algorithm hint vs thinking with helpers + 8 distractors and no hint) and every Qwen3.5-9B word cell (thinking without the library).
**Run:** geometry thinking with the fact prompt (`run_geo_cross.py --think --distract 0 --algo_hint`, tag `S2_HOG_<m>_geo_thinkfact_s<seed>`;
16k, gpt-oss-20b medium; Qwen3.5-9B 32k with its card sampling) for all four models, seeds 1–3; Qwen3.5-9B `formxt` (32k, card sampling) on
OptiBench (the same fixed third), BWOR, LogiOR, OptMATH. Same policies as HO-TF (geometry: FF+F = fact program unless the MR check
fails, then thinkfact).
- **TF2-P1:** THINK+F ≥ THINK on geometry for ≥ 3 of the 4 models.
- **TF2-P2:** FF+F ties or beats THINK+F on geometry for gpt-oss-20b, Qwen3-14B-AWQ and Qwen3.5-9B (upper bound ≥ 0) at ≤ 60% of its tokens.
- **TF2-P3:** for Qwen3.5-9B, FF+F ties or beats THINK+F on ≥ 3 of its 4 word benchmarks (its thinking misuses the libraries; the fact in
  the prompt may not fix that while thinking).
**Decision.** With HO-TF, the held-out table is rebuilt against the fact-matched thinking arm everywhere, and the claim is restated from
whatever survives: where FF+F ties THINK+F the recipe is a pure saving; where it loses it is a token-for-accuracy trade-off.

### Results HO-TF (2026-10-23 13:5x UTC; `python poc/analyze_hotf.py`, 3 seeds; OptiBench = problems 0, 3, …, 603; all rows complete after
re-running 52 Qwen3-8B rows whose requests had timed out at the client's 1-hour limit)
| model · benchmark | THINK (no fact) | THINK+F | FF+F | THINK+F − THINK | **FF+F − THINK+F** | FF+F tokens / THINK+F's |
|---|---|---|---|---|---|---|
| gpt-oss-20b · OptiBench | 66.7% | 71.6% | 74.1% | +5.0 [+1.2, +9.1] | **+2.5 [+0.5, +4.8]** | 48% |
| gpt-oss-20b · BWOR | 59.3% | 60.2% | 58.9% | +0.8 [−6.9, +8.9] | −1.2 [−6.9, +4.5] | 46% |
| gpt-oss-20b · LogiOR | 51.4% | 50.7% | 50.0% | −0.7 [−7.2, +5.4] | −0.7 [−5.1, +3.3] | 63% |
| Qwen3-14B-AWQ · OptiBench | 44.1% | 66.7% | 62.4% | +22.6 [+17.7, +27.7] | **−4.3 [−7.8, −0.8]** | 33% |
| Qwen3-14B-AWQ · BWOR | 30.1% | 52.4% | 40.2% | +22.4 [+13.8, +30.9] | **−12.2 [−20.3, −4.5]** | 56% |
| Qwen3-14B-AWQ · LogiOR | 27.9% | 42.8% | 40.9% | +14.9 [+7.6, +22.1] | −1.8 [−6.2, +2.5] | 75% |
| Qwen3-8B · OptiBench | 55.3% | 67.5% | 63.0% | +12.2 [+8.6, +15.7] | **−4.5 [−8.1, −1.0]** | 39% |
| Qwen3-8B · BWOR | 38.2% | 46.7% | 35.8% | +8.5 [+1.6, +15.4] | **−11.0 [−16.7, −5.7]** | 65% |
| Qwen3-8B · LogiOR | 34.8% | 44.6% | 37.0% | +9.8 [+4.3, +15.6] | **−7.6 [−11.6, −3.6]** | 82% |
- **TF-P1 holds** (THINK+F ≥ THINK in 8 / 9; the library raises the Qwen models' thinking by +8.5 to +22.6 points). **TF-P2 refuted**
  (2 / 6: gpt-oss-20b OptiBench and BWOR; gpt-oss-20b LogiOR ties at 63% of the tokens, Qwen3-14B-AWQ LogiOR ties at 75%, Qwen3-14B-AWQ
  loses on OptiBench and BWOR). **TF-P3 holds** (Qwen3-8B BWOR −11.0).
- Geometry (TF2, same rows): FF+F − THINK+F gpt-oss-20b +3.1 [+1.0, +5.6] at 59%, Qwen3-14B-AWQ +2.4 [−0.3, +5.6] at 39%, Qwen3-8B −16.7
  [−21.9, −11.5]; THINK+F − THINK +3.5 / +11.1 / +4.2. (TF2 is decided with Qwen3.5-9B, still running.)
- **Decision (as pre-registered):** the library rows of the held-out table are restated against the fact-matched thinking arm. The fact is
  the main lever — it raises the cheap program *and* thinking. Spending thinking only on visible failures is a pure saving for gpt-oss-20b
  (ties or wins at 46–63% of the tokens) and on geometry for the two stronger models; for the Qwen models on word problems it is a trade:
  33–82% of the tokens for 2–12 points less than always thinking with the fact.
*HO-TF2 operations (2026-10-23 14:5x UTC; no setting of the comparison changed):* Qwen3.5-9B's OptMATH thinking-with-the-library tasks
wrote no rows in 2–3 hours: some library prompts of long OptMATH problems plus the 32k thinking budget exceed the server's 36,864-token
context, vLLM rejects those requests (HTTP 400), and the client stops writing rows at the first failed request. The three tasks were
cancelled and rerun with a 45,056-token context (still at most 32k new tokens), which every thinking-with-the-fact server now uses.

### Results HO-TF2 (2026-10-23 19:0x UTC; `python poc/analyze_hotf.py [--geo]`, 3 seeds, all rows complete)
FF+F − THINK+F (fact-matched thinking), paired 95% interval, FF+F's tokens / THINK+F's:
| | geometry (hint) | OptiBench (third) | BWOR | LogiOR | OptMATH |
|---|---|---|---|---|---|
| gpt-oss-20b | **+3.1 [+1.0, +5.6]** 59% | **+2.5 [+0.5, +4.8]** 48% | −1.2 [−6.9, +4.5] 46% | −0.7 [−5.1, +3.3] 63% | **+5.7 [+0.3, +11.3]** 68% (HO: thinks) |
| Qwen3-14B-AWQ | +2.4 [−0.3, +5.6] 39% | **−4.3 [−7.8, −0.8]** 33% | **−12.2 [−20.3, −4.5]** 56% | −1.8 [−6.2, +2.5] 75% | 0.0 [−4.0, +4.0] 83% (thinks) |
| Qwen3-8B | **−16.7 [−21.9, −11.5]** 53% | **−4.5 [−8.1, −1.0]** 39% | **−11.0 [−16.7, −5.7]** 65% | **−7.6 [−11.6, −3.6]** 82% | +1.7 [−1.3, +5.0] 88% (thinks) |
| Qwen3.5-9B | −0.3 [−3.1, +2.4] 30% | **+4.0 [+1.0, +6.9]** 30% | 0.0 [−4.9, +4.9] 66% | **+7.6 [+3.6, +12.0]** 78% | +2.7 [−3.3, +8.7] 60% |
THINK+F − THINK on geometry: +3.5 / +11.1 / +4.2 / +6.9; on Qwen3.5-9B's word benchmarks +9.8 to +21.9.
- **TF2-P1 holds** (4 / 4). **TF2-P2 holds** (geometry: gpt-oss-20b wins, Qwen3-14B-AWQ and Qwen3.5-9B tie, at 30–59% of the tokens).
  **TF2-P3 holds** (Qwen3.5-9B ties or wins on 4 / 4 word benchmarks; wins on OptiBench and LogiOR).
- **The rebuilt held-out claim:** against thinking given the same fact, fact-first-then-think ties or wins on all five benchmarks for
  gpt-oss-20b and Qwen3.5-9B (at 30–78% of the tokens) and for Qwen3-14B-AWQ on geometry, LogiOR and OptMATH; it loses for Qwen3-14B-AWQ
  on OptiBench / BWOR and for Qwen3-8B everywhere but OptMATH — there thinking with the fact is worth its tokens.

## Addendum HO-VF (2026-10-23 20:4x UTC, before any run): a stronger check *with the fact*, where the recipe loses
**Why.** Against thinking given the same fact, fact-first loses for Qwen3-14B-AWQ on OptiBench / BWOR and for Qwen3-8B on OptiBench /
BWOR / LogiOR, because its free check (the program runs and prints a value) lets through programs that thinking with the fact would get
right (§5.2 decomposition). The solution checker (HO3: a program written from the text that tests every constraint on the printed
solution) caught 66–97% of running-but-wrong programs on BWOR / LogiOR. **Policy FF-V+F:** the library program printing its solution
(`formxv`) is accepted only if it runs, prints a value and the checker passes; otherwise thinking with the fact (`formxt`, HO-TF rows).
**Run:** `run_form.py <m> formxv <seed>` then `run_verify.py <m> <seed> formxv` on BWOR and LogiOR for Qwen3-14B-AWQ and Qwen3-8B, seeds
1–3 (no thinking; RTX 3090); OptiBench uses the existing HO4 `formxv` / checker rows on the HO-TF third.
- **VF-P1:** FF-V+F closes at least half of the gap FF+F → THINK+F in ≥ 3 of the 5 losing cells, at ≤ 80% of THINK+F's tokens.
- **VF-P2:** FF-V+F ties THINK+F (interval includes 0) in ≥ 3 of the 5 cells.
**Decision.** P1 → the checker becomes the word-problem check for models whose plain check leaks (chosen by the 30-label pilot as a sixth
policy); otherwise the loss stays a trade-off and thinking with the fact is the answer there.

## Addendum HO-TB (2026-10-23 20:4x UTC, before any run): how much thinking with the fact is needed?
**Why.** Where fact-first loses (Qwen3 models, OptiBench / BWOR / LogiOR), thinking with the fact costs 5.6–11k tokens per problem. If a
short thinking budget keeps most of its accuracy, the right escalation (and the right always-on policy) is budgeted thinking with the fact.
**Run:** `run_form.py <m> formx <seed> --think_budget B` (Qwen3 budget forcing: think at most B tokens, then answer within 8,192) for
Qwen3-14B-AWQ and Qwen3-8B, B ∈ {2,000, 6,000}, seeds 1–3, on the OptiBench third, BWOR, LogiOR.
- **TB-P1:** at B = 6,000, always thinking with the fact keeps ≥ THINK+F − 3 points in ≥ 4 of the 6 cells at ≤ 75% of its tokens.
- **TB-P2:** at B = 2,000 it loses > 5 points in ≥ 3 of the 6 cells (a short budget is not enough on these word problems).
- **TB-P3:** FF escalating to B = 6,000 thinking with the fact (FF+Fb) is within 3 points of THINK+F in ≥ 3 of the 6 cells at ≤ 60% of its
  tokens.
**Decision.** TB-P1 / P3 → the recipe's escalation for these models becomes budgeted thinking with the fact, and the pilot gets it as a policy.

## Addendum WF4 + HO-LG (2026-10-23 20:4x UTC, before any run): larger models on RTX 3090s (user 10-23: the project is no longer limited to
24 GB models, but stays on the RTX 3090 partition — large models run tensor-parallel over 4 × 3090 in one job)
**WF4 — the "do not add a fact" side, prospectively.** gpt-oss-120b (low effort for the cheap arms, as in WF2) on BWOR and LogiOR (new
cells for this model): `free`, `freef` (usage card), `formx` (label-free library), seeds 1–3. The WF3 rule ("add unless usage crashes
u < 5% and non-usage failures n ≥ 25%") is applied to the `free` arm and its calls are recorded here before any gain is read.
- **WF4-P1:** where the rule says "do not add", the card and the library each change the free program by ≤ +2 points; where it says
  "add", each adds ≥ +2. If both cells say "add", the "do not add" side stays untested (stated).
**HO-LG — the core rule on a large model, against the fair baseline.** gpt-oss-120b, `formx` (cheap, low) vs `formxt` (thinking with the
same library, medium effort, 16k), on the OptiBench third, BWOR, LogiOR, seeds 1–3; FF+F = formx, on a visible failure formxt.
- **LG-P1:** FF+F ties or beats THINK+F (interval upper bound ≥ 0) in all 3 cells, at ≤ 60% of its tokens (a strong model's passing cheap
  programs should be as often right as its thinking).
**Decision.** WF4 decides whether the census rule is two-sided; LG-P1 extends (or limits) the rebuilt claim to a 120B model.

### WF4 calls, recorded before any gain was read (2026-10-23 21:2x UTC; `CENSUS_SETS=bwor,logior python poc/analyze_which_fix.py --census oss120`)
| cell | u (usage crashes) | fail the check | n (non-usage failures) | call |
|---|---|---|---|---|
| BWOR gpt-oss-120b | 2.0% | 19.5% | 17.5% | add (u < 5% but n < 25%) |
| LogiOR gpt-oss-120b | 1.1% | 23.2% | 22.1% | add (u < 5% but n < 25%) |
The first cells with u < 5% since the rule was fixed, but both fall on its "add" side through the second condition (few failures of any
kind), so WF4-P1 tests the rule's claim that a fact still pays where usage crashes are rare and failures are few; the "do not add" region
(u < 5%, n ≥ 25%) is again not reached.

### Results WF4 (2026-10-23 21:3x UTC; gpt-oss-120b, 3 seeds, paired 95% intervals; gain = with fact − free)
| cell (call: add) | free | + usage card | + label-free library |
|---|---|---|---|
| BWOR gpt-oss-120b (u 2.0%) | 61.8% @ 1.08k | +6.5 [+0.8, +12.6] ✓ | +3.3 [−2.8, +9.3] ✓ |
| LogiOR gpt-oss-120b (u 1.1%) | 57.2% @ 1.04k | +2.5 [−3.3, +8.0] ✓ | −3.3 [−9.1, +2.5] ✗ |
- **WF4-P1 refuted narrowly** (3 / 4 calls right; only BWOR's card gain is significant). Tally of prospective calls: 21 / 24 right, all
  on the "add" side. Where usage crashes are rare (< 5%) the gains are small and of either sign (here −3.3 to +6.5; WF2: −3.3 to +9.6),
  so the census marks where facts pay a lot (≥ 5%: +12 on average) but cannot call the low-crash cells; there the pilot decides.

### Results HO-VF (2026-10-23 22:5x UTC; `python poc/analyze_hovf.py q14a q8b`, 3 seeds; vs thinking given the same fact)
| cell | FF+F − THINK+F | **FF-V+F − THINK+F** | FF-V+F tokens / THINK+F's |
|---|---|---|---|
| Qwen3-14B-AWQ OptiBench (third) | −4.3 [−7.8, −0.8] | **+0.7 [−1.7, +3.0]** | 71% |
| Qwen3-14B-AWQ BWOR | −12.2 [−20.3, −4.5] | −1.6 [−4.9, +1.6] | 101% |
| Qwen3-8B OptiBench (third) | −4.5 [−8.1, −1.0] | **+1.0 [+0.2, +2.0]** | 79% |
| Qwen3-8B BWOR | −11.0 [−16.7, −5.7] | −1.2 [−3.7, +0.4] | 108% |
| Qwen3-8B LogiOR | −7.6 [−11.6, −3.6] | 0.0 (the checker passes almost nothing) | 111% |
- **VF-P2 holds** (FF-V+F ties or beats THINK+F in 5 / 5 losing cells). **VF-P1 refuted** (the gap is closed in all 5, but at ≤ 80% of
  THINK+F's tokens only on OptiBench, 2 / 5): on BWOR / LogiOR the checker sends almost everything to thinking anyway.
- **Decision:** the solution checker is the word-problem check for models whose plain check leaks *on easier benchmarks* (OptiBench:
  matches thinking with the fact at 71–79% of its tokens); on the hardest benchmarks thinking with the fact is the answer for these models.
  It joins the pilot as a sixth policy.

### Results HO-LG (2026-10-23 22:5x UTC; gpt-oss-120b on 4 × RTX 3090, 3 seeds)
FF+F − THINK+F: OptiBench (third) −1.0 [−2.8, +0.8] at 50% of the tokens, BWOR +3.7 [−1.6, +8.9] at 52%, LogiOR 0.0 [−3.6, +3.3] at 63%
(THINK+F 75.6% / 70.7% / 62.7% at 1.7–3.1k tokens). **LG-P1 refuted narrowly** (ties in all 3 cells, but LogiOR at 63% > 60% of the
tokens): for a 120B model fact-first-then-think keeps the accuracy of thinking with the fact at half to two-thirds of its tokens.

### Results HO-TB (2026-10-24 02:0x UTC; `python poc/analyze_hotb.py 2000|6000`, 3 seeds; vs thinking with the fact at 16k, THINK+F)
| cell | THINK+Fb, B = 2,000 | THINK+Fb, B = 6,000 | FF+Fb, B = 6,000 |
|---|---|---|---|
| Qwen3-14B-AWQ OptiBench (third) | −2.3 [−5.1, +0.3] @ 41% | −2.3 [−4.6, −0.0] @ 83% | −5.6 @ 25% |
| Qwen3-14B-AWQ BWOR | −11.4 @ 32% | −2.0 [−8.1, +3.7] @ 68% | −11.8 @ 39% |
| Qwen3-14B-AWQ LogiOR | −13.0 @ 31% | −2.5 [−8.0, +2.9] @ 68% | −3.6 @ 52% |
| Qwen3-8B OptiBench (third) | −3.6 [−6.6, −0.8] @ 36% | −1.7 [−3.8, +0.7] @ 79% | −5.1 @ 29% |
| Qwen3-8B BWOR | −13.4 @ 30% | **−9.8 [−15.4, −4.1]** @ 62% | −15.4 @ 42% |
| Qwen3-8B LogiOR | −17.0 @ 29% | **−5.8 [−10.5, −1.1]** @ 62% | −13.4 @ 52% |
- **TB-P1 refuted** (within 3 points at ≤ 75% of the tokens in 2 / 6: Qwen3-14B-AWQ BWOR and LogiOR at 68%). **TB-P2 holds** (B = 2,000
  loses > 5 points in 4 / 6; on OptiBench it keeps all but 2–4 points at 36–41% of the tokens). **TB-P3 refuted** (0 / 6).
- **Reading.** A shorter think with the fact is a token-for-accuracy trade, not a free saving: about a third of the tokens for 2–3 points
  on OptiBench (2k) or for Qwen3-14B-AWQ on BWOR / LogiOR (6k); Qwen3-8B needs the full budget on the hard benchmarks. Escalating to a
  budgeted think does not rescue fact-first for these models: their loss is the leaky check (HO-VF), not the cost of the escalation.

## Addendum HO-VR (2026-10-24 13:3x UTC, before any run): a short thinking-mode review as the gate
**Why it could change the claim / what is new.** The claim's weak point is the Qwen3 cells where the free check passes wrong programs that
thinking with the fact would solve (fact-first loses 4–15 points). The solution checker (HO-VF) closed the gap but escalated almost everything
on BWOR / LogiOR (101–111% of the tokens). Prior cascades gate escalation *between models* by answer consistency or self-verification
(AutoMix, LLM cascades; docs/notes/RELATED_WORK.md); here the gate is the *same model's thinking mode reviewing its own non-thinking
program* under a small budget — a different reasoning path than the cheap mode, at a fraction of a full think — on the fact-matched setup.
**Run** (`poc/run_review.py <m> <seed> 2000`): for every passing library program (formx) of Qwen3-14B-AWQ and Qwen3-8B on the OptiBench
third, BWOR, LogiOR (seeds 1–3), thinking cut at 2,000 tokens, then `VERDICT: CORRECT | WRONG`. **Policy FF-R+F:** accept the program on
CORRECT, else thinking with the fact (formxt, HO-TF rows). Tokens = program + review + thinking where escalated.
- **VR-P1:** FF-R+F ties THINK+F (interval upper bound ≥ 0) in ≥ 3 of the 5 losing cells at ≤ 75% of THINK+F's tokens.
- **VR-P2:** pooled, the review flags ≥ 60% of the wrong passing programs and ≤ 30% of the right ones.
**Decision.** P1 → the recipe's check for these models becomes "free check + a short self-review", turning the trade into a saving;
otherwise the Qwen3 cells stay a trade and the pilot decides.

### Results HO-VR (2026-10-24 14:0x UTC; `python poc/analyze_hovr.py`, 3 seeds; vs thinking with the fact, THINK+F)
| cell | FF+F − THINK+F | **FF-R+F − THINK+F** | FF-R+F tokens | perfect check (labels): accuracy / tokens |
|---|---|---|---|---|
| Qwen3-14B-AWQ OptiBench (third) | −4.3 [−7.8, −0.8] | **−0.7 [−3.1, +1.7]** | 70% | 70.3% / 62% |
| Qwen3-14B-AWQ BWOR | −12.2 [−20.3, −4.5] | **+0.4 [−2.8, +3.7]** | 103% | 56.9% / 88% |
| Qwen3-14B-AWQ LogiOR | −1.8 [−6.2, +2.5] | **+2.9 [+0.7, +5.4]** | 99% | 47.8% / 93% |
| Qwen3-8B OptiBench (third) | −4.5 [−8.1, −1.0] | **−1.0 [−3.5, +1.2]** | 73% | 70.8% / 64% |
| Qwen3-8B BWOR | −11.0 [−16.7, −5.7] | **+0.4 [−0.8, +2.0]** | 102% | 49.2% / 96% |
| Qwen3-8B LogiOR | −7.6 [−11.6, −3.6] | **−1.1 [−3.3, +0.7]** | 103% | 46.4% / 100% |
Review flags 361 / 556 (65%) of the wrong passing programs and 113 / 851 (13%) of the right ones.
- **VR-P1 refuted** (ties at ≤ 75% of the tokens in 2 / 5 losing cells, both OptiBench) — but the target was unreachable on BWOR / LogiOR:
  even a *perfect* check saves only 0–12% of the tokens there (88–100%), because the cheap program is right on too few problems. I should
  have checked this bound before setting the threshold. **VR-P2 holds** (65% of wrong programs flagged, 13% false alarms — far fewer false
  alarms than the solution checker, which flagged 18–65% of right programs in HO3).
- **Decision.** A short self-review in thinking mode (2k tokens) makes fact-first lose nothing to thinking with the fact in all six Qwen3
  cells (−1.1 to +2.9, one significant win), at 70–73% of the tokens where saving is possible (OptiBench, near the perfect-check 62–64%)
  and at the same cost where it is not (BWOR / LogiOR). With it, the recipe's Qwen3 "trade" becomes a saving or a tie: the gate joins the
  recipe for models whose plain check leaks.

## Addendum HO-VR2 (2026-10-24 14:0x UTC, before any run): does the self-review gate generalize, including the cell every check failed?
**Why it could change the claim.** HO-VR made the Qwen3 trade a saving or a tie on three word benchmarks. Two cells remain: OptMATH (mined
example `mips`, thinking `thinks`) and held-out geometry, where Qwen3-8B's fact-first loses 16.7 points to thinking with the hint and every
self-written check failed (brute force, resampling, edge tests, relations, a second model, repair; 37 of its 64 leaks are edge-case-only).
A review that reads the statement may see what checks on the given input cannot.
**Run** (`run_review.py <m> <seed> 2000 mips` with NLOPT_SET=optmath; NLOPT_SET=geo for geometry): Qwen3-14B-AWQ and Qwen3-8B, seeds 1–3.
- **VR2-P1:** FF-R+F ties or beats THINK+F (OptMATH: thinks; geometry: thinkfact) in ≥ 3 of the 4 cells.
- **VR2-P2:** on Qwen3-8B geometry the review flags ≥ 40% of the leaked programs (pass MR, wrong) with ≤ 20% false alarms.

### Results HO-VR2 (2026-10-24 14:3x UTC; `python poc/analyze_hovr.py --vr2`, 3 seeds; vs thinking with the fact)
| cell | FF+F − THINK+F | **FF-R+F − THINK+F** | FF-R+F tokens |
|---|---|---|---|
| Qwen3-14B-AWQ OptMATH (mips / thinks) | 0.0 [−4.0, +4.0] | +1.0 [−0.7, +3.0] | 107% |
| Qwen3-14B-AWQ geometry (fact / thinkfact) | +2.4 [−0.3, +5.6] | **+3.5 [+1.0, +6.2]** | 84% |
| Qwen3-8B OptMATH | +1.7 [−1.3, +5.0] | **+2.7 [+0.3, +5.3]** | 109% |
| Qwen3-8B geometry | −16.7 [−21.9, −11.5] | **−6.6 [−10.1, −3.5]** | 98% |
Qwen3-8B geometry: the review flags 24 / 27 leaks wrong on the given input and **20 / 37 edge-case-only leaks** (false alarms 41 / 132,
31%); Qwen3-14B-AWQ: 6 / 7 leaks, 57 / 232 false alarms.
- **VR2-P1 holds** (ties or beats in 3 / 4; two significant wins). **VR2-P2 refuted narrowly** (69% of Qwen3-8B's leaks flagged, ≥ 40%,
  but 31% false alarms, not ≤ 20%).
- **Reading.** Reading the statement, the short review sees edge-case errors no check on the given input could (20 of the 37 that defeated
  brute force, resampling, edge tests, relations, a second model and repair), cutting Qwen3-8B's geometry loss from 16.7 to 6.6 points;
  it is still a loss, and the false alarms cost the saving. Across the eight Qwen3 cells the gate ties or beats thinking with the fact in 7.

## Addendum HO-VR3 (2026-10-24 15:3x UTC, before any run): is the self-review gate safe where the recipe already wins?
**Why.** To state the recipe as one procedure, the gate must not hurt models whose plain check is already good (otherwise it is a pilot
option, not a step). **Run:** Qwen3.5-9B (its HO-N / HO-TF2 rows: formx, formxt at 32k), review cut at 2,000 tokens, OptiBench third, BWOR,
LogiOR, seeds 1–3.
- **VR3-P1:** FF-R+F ≥ FF+F − 1 point in all 3 cells (the gate does not cost accuracy where the check is good).
- **VR3-P2:** FF-R+F uses ≤ FF+F's tokens + 15% of THINK+F's in all 3 (false alarms are rare when the check is good).
**Decision.** P1 + P2 → the gate is a default step of the recipe; otherwise it is a pilot option for models whose check leaks.
*HO-VR3 harness fix (2026-10-24 16:4x UTC, before any result was read beyond the verdict counts): with the answer after the thinking
budget capped at 512 tokens (as for Qwen3), 70% of Qwen3.5-9B's reviews ended mid-explanation without a VERDICT line (its answers are
long), which the policy counts as WRONG. The run is discarded and repeated with the answer capped at 2,048 tokens (REVIEW_ANSWER_MAX);
predictions unchanged.*

### Results HO-VR3 (2026-10-24 18:0x UTC; rerun with a 2,048-token answer cap; Qwen3.5-9B, 3 seeds; vs THINK+F)
| cell | FF+F − THINK+F (tokens) | FF-R+F − THINK+F (tokens) |
|---|---|---|
| OptiBench (third) | +4.0 [+1.0, +6.9] (30%) | +5.1 [+3.5, +6.9] (67%) |
| BWOR | 0.0 [−4.9, +4.9] (66%) | +3.3 [+0.4, +6.1] (96%) |
| LogiOR | +7.6 [+3.6, +12.0] (78%) | +4.3 [+1.4, +7.2] (96%) |
Even at 2,048 answer tokens 10–33% of the reviews end without a verdict (counted as WRONG); the review flags 117 / 199 wrong passing
programs and 102 / 509 right ones.
- **VR3-P1 refuted** (FF-R+F ≥ FF+F − 1 in 2 / 3: +1.1, +3.2, −3.3 on LogiOR). **VR3-P2 refuted** (the gate adds 18–37% of THINK+F's
  tokens, not ≤ 15%: every false alarm or missing verdict sends a problem to a 32k-token think).
- **Decision:** the gate is not a free default. Where the plain check is already good (Qwen3.5-9B), it buys little accuracy for many tokens;
  where the check leaks (the Qwen3 models), it removes the loss. It is a policy the 30-label pilot switches on, and it depends on the model
  answering the review in the asked format.

## Addendum WF5 (2026-10-24 21:1x UTC, before any run): the "do not add a fact" side, reached through fine-tuning
**Why it could change the claim.** The census rule (add a fact unless usage crashes u < 5% and non-usage failures n ≥ 25%) is part of the
claim, but all 24 prospective calls so far fell on its "add" side (WF3, WF4): no base model reaches the "do not add" region. Label-free
fine-tuning (DT) moves the usage fact into the weights (u 16–28% → 1–7%) while formulation failures stay, so fine-tuned models are the
first to land there. If the rule's second side holds, the census tells — with no labels — when the library has become unnecessary after
fine-tuning (and its input tokens can be saved); if not, the rule is one-sided and the report says the pilot decides there.
**Calls, recorded before any gain was read** (`CENSUS_SETS=optibench,bwor,logior,optmath python poc/analyze_which_fix.py --census
q14sft q8bsft2 q8bsft`; `free` arm, 3 seeds; fine-tuned models from PREREG_DT.md):
| cell | u | n | call | facts run (3 seeds) |
|---|---|---|---|---|
| Qwen3-14B fine-tuned (`q14sft`) OptiBench | 2.0% | 23.0% | add | card (`freef`), library (`formx`, all 605) |
| `q14sft` BWOR | 4.9% | 31.7% | **do not add** | card, library |
| `q14sft` LogiOR | 6.9% | 47.5% | add | card, library |
| `q14sft` OptMATH | 11.7% | 55.0% | add | library |
| Qwen3-8B self-trained round 2 (`q8bsft2`) BWOR | 3.7% | 37.0% | **do not add** | card, library |
| Qwen3-8B fine-tuned (`q8bsft`) BWOR | 4.1% | 39.4% | **do not add** | card (its library arm was read in DT2: retrospective, not counted) |
| `q8bsft` OptMATH | 10.0% | 60.3% | add | library |
- **WF5-P1 (the new side):** in the 5 prospective "do not add" points, the fact changes the free program by ≤ +2 points in ≥ 4.
- **WF5-P2 (the old side, on fine-tuned models):** in the 6 "add" points, the fact adds ≥ +2 points in ≥ 4.
- Reported with each: the paired 95% interval, output tokens, and the library's extra input tokens.
**Decision.** P1 → the census rule is two-sided: after label-free fine-tuning it says when to drop the fact; the claim's rule bullet
becomes two-sided. P1 refuted → the rule only marks where facts pay a lot; below 5% usage crashes the pilot decides (stated as one-sided).

### Results WF5 (2026-10-25 00:0x UTC; `python poc/analyze_wf5.py`; 3 seeds, paired 95% intervals; gain = with fact − free)
| cell (call) | free | + usage card | + label-free library (extra input) |
|---|---|---|---|
| `q14sft` OptiBench (add) | 58.0% @ 393 | −1.0 [−2.9, +0.9] ✗ | **+5.1 [+2.6, +8.0]** ✓ (331) |
| `q14sft` BWOR (**do not add**) | 24.0% @ 1,027 | +2.8 [−2.4, +8.5] ✗ | +4.1 [−1.6, +10.6] ✗ (468) |
| `q14sft` LogiOR (add) | 19.6% @ 1,130 | −1.1 [−6.5, +4.3] ✗ | +4.0 [−0.7, +9.1] ✓ (723) |
| `q14sft` OptMATH (add) | 9.3% @ 1,489 | — | **+6.7 [+2.0, +12.3]** ✓ (858) |
| `q8bsft2` BWOR (**do not add**) | 15.0% @ 961 | −2.4 [−7.7, +2.4] ✓ | +5.7 [−0.8, +12.2] ✗ (468) |
| `q8bsft` BWOR (**do not add**) | 18.3% @ 921 | **−6.9 [−12.6, −2.4]** ✓ | (DT2, retrospective: −1.2 [−7.3, +4.9]) |
| `q8bsft` OptMATH (add) | 8.3% @ 1,424 | — | +1.3 [−3.0, +6.0] ✗ (858) |
- **WF5-P1 refuted** (the "do not add" side right on 2 / 5). **WF5-P2 refuted** (the "add" side right on 3 / 6).
- **The pattern is by kind of fact, not by the census.** After label-free fine-tuning the usage card pays nowhere (5 / 5 points below
  +2 whatever the call; on Qwen3-8B BWOR it hurts, −6.9: raw, the card makes the fine-tuned model write shorter programs with integer
  variables for divisible quantities and wrong unit conversions, running-but-wrong 96 → 121 of 246), while the library of similar
  problems' programs still pays on 5 / 6 points (significantly on Qwen3-14B OptiBench and OptMATH) — the usage fact is in the weights, the
  formulations of other problem types are not. The census, which counts usage crashes, predicts the first and is blind to the second.
- **Tally of prospective census calls:** 21 / 24 on the development base models (WF1–WF4), 5 / 11 here, 3 / 8 on Nemotron-3-Nano
  (PREREG_HON.md, HO-N4). **Decision as registered:** the rule is not two-sided and does not transfer beyond the base models it was
  built on; the report states it as a description of where usage facts paid on those models, and leaves the add / do-not-add choice to
  the pilot (which can include "no fact" as a policy).

## Addendum HO-SB (2026-10-25 00:0x UTC, before any run): short thinking first — a cheaper fix for leaky models than the review gate?
**Origin (post hoc, exploratory).** Re-reading HO-TB's stored runs (`python poc/analyze_hotb.py 2000`, policy added today): thinking with
the fact cut at 2,000 tokens first, full thinking with the fact only when that program visibly fails (SB+F), ties THINK+F in 5 of the 6
Qwen3 cells at 62–92% of its tokens (Qwen3-14B-AWQ OptiBench +0.5 @ 68%, BWOR +1.2 @ 83%, LogiOR +1.1 @ 90%; Qwen3-8B OptiBench −0.3 @
62%, BWOR +2.4 @ 86%, LogiOR −4.0 [−7.6, −0.4] @ 92%), where the review gate ties at 70–73% (OptiBench) and ~100% (BWOR / LogiOR). The
short-thinking program leaks less than the non-thinking one, so the free check suffices more often. These 6 cells chose the idea and are
not evidence for it. **Why it could change the claim.** For leaky models the recipe's current branch (the gate) removes the loss but saves
nothing on hard problems; if SB+F holds on unseen cells it is a saving there and needs no review. Related work: escalating from a cheap tier
to a stronger one on a failed check is the standard cascade (docs/notes/RELATED_WORK.md; CodeRescue 2607.19338 between models; 2605.07686
on cascades failing when the fallback budget is too small); we test it inside one model, with the fact matched, as the fix for a leaky check.
**Run (prospective cells).** `run_form.py <m> formx <seed> --think_budget 2000` (as HO-TB: budget forcing, T 0.7, answer ≤ 8,192) on
OptiBench's HO-TF third, BWOR, LogiOR, OptMATH, seeds 1–3, for Nemotron-3-Nano (`n3n`, leaky: FF+F − THINK+F −6 to −12 on the cells
finished so far) and Qwen3.5-9B (`q35`, where FF+F already ties or wins); compared with their THINK+F (formxt), FF+F and (n3n) the gate.
- **SB-P1:** on Nemotron's 4 cells SB+F ties or beats THINK+F (upper bound ≥ 0) in ≥ 3, at ≤ 90% of its tokens.
- **SB-P2:** on Nemotron's 4 cells SB+F is within 2 points of the gate FF-R+F and uses fewer tokens than it in ≥ 3.
- **SB-P3:** on Qwen3.5-9B's 4 cells SB+F is within 2 points of FF+F at no more than its tokens in ≥ 3 (it costs nothing where the plain
  recipe already works).
**Decision.** P1 and P2 → for leaky models the recipe's branch becomes short thinking with the fact first (no review); with P3 it is the
candidate no-label default for hybrid-thinking models and joins the pilot. Otherwise the gate stays.

### Results HO-SB, Nemotron-3-Nano: SB-P1 / P2 (2026-10-25 02:2x UTC; `python poc/analyze_hotb.py 2000 n3n`; 3 seeds, all rows)
| cell | THINK+F | SB+F (tokens vs THINK+F) | SB+F − THINK+F | gate FF-R+F (tokens) | SB+F − gate |
|---|---|---|---|---|---|
| OptiBench (third) | 67.8% @ 6.6k | 71.6% (72%) | **+3.8 [+1.8, +5.9]** | 69.3% (94%) | +2.3 [−0.0, +4.8] |
| BWOR | 49.2% @ 11.9k | 54.5% (79%) | +5.3 [−0.8, +11.4] | 49.2% (107%) | +5.3 [−0.8, +11.4] |
| LogiOR | 44.6% @ 12.8k | 47.8% (92%) | +3.3 [−1.4, +8.0] | 46.7% (109%) | +1.1 [−4.0, +6.2] |
| OptMATH | 29.7% @ 19.1k | 36.0% (73%) | **+6.3 [+1.0, +12.0]** | 30.3% (106%) | **+5.7 [+0.7, +11.0]** |
- **SB-P1 holds** (ties or beats THINK+F in 4 / 4, at ≤ 90% of its tokens in 3 / 4; LogiOR at 92%). **SB-P2 holds** (no more than
  2 points below the gate — in fact above it — and fewer tokens in 4 / 4).
- **Raw: where the gain comes from.** On the problems where the 2k-token program passes the free check and full thinking does not get it
  right, full thinking's own program mostly crashes or prints no value (BWOR 18 of 26, OptMATH 6 of 35) or hits the 32k cap (OptMATH 17
  of 35); the reverse (full thinking right, the short program wrong though it passed) is 13 on BWOR and 16 on OptMATH. Budget forcing makes
  the short think finish, and the escalation is a second attempt only where the first visibly failed.
- **Exploratory (not pre-registered):** putting the non-thinking library program in front (library → short think → full think) brings
  the leak back for this model (−4.6 to −7.7 on OptiBench / BWOR / LogiOR vs THINK+F); for the leaky models the cheap step must think.
SB-P3 (Qwen3.5-9B) is scored when its OptiBench / OptMATH runs finish.

## Addendum HO-SB2 (2026-10-25 02:2x UTC, before any run): short thinking first on the Qwen3 cells it was not chosen on
**Why it could change the claim.** HO-SB held on Nemotron-3-Nano; if it also holds on the Qwen3 cells the idea was not chosen on —
OptMATH and held-out geometry, including the claim's worst cell (Qwen3-8B geometry: fact-first −16.7 against thinking with the fact,
−6.6 with the gate) — the recipe's step for leaky hybrid-thinking models becomes "think briefly with the fact first" instead of the
non-thinking program plus a review. **Run.** Qwen3-14B-AWQ and Qwen3-8B, seeds 1–3: OptMATH with the library arm (`formx`, `formxt`
at 16k as HO-TF, `formx --think_budget 2000`); geometry: `run_geo_cross.py ... --distract 0 --algo_hint --think_budget 2000 --max_tokens
8192` (tag `S2_HOG_<m>_geo_thinkfactb2000_s<seed>`; THINK+F = the stored thinkfact runs at 16k; a visible failure = the metamorphic
check fails, as everywhere). Nemotron's geometry is left out: its thinking with the fact already costs only 1.7k tokens.
- **SB2-P1:** SB+F ties or beats THINK+F (upper bound ≥ 0) in ≥ 3 of the 4 cells at ≤ 90% of its tokens.
- **SB2-P2:** on Qwen3-8B geometry SB+F is within 3 points of THINK+F (the worst cell closed).
**Decision.** P1 → the leaky-model branch of the recipe is "short thinking with the fact first, full thinking on a visible failure";
the gate stays a second option. With P2 the claim no longer has a losing Qwen3 cell.

### Results HO-SB, Qwen3.5-9B: SB-P3 (2026-10-25 02:5x UTC; `python poc/analyze_hotb.py 2000 q35`, `analyze_hotf.py q35`; 3 seeds, all rows)
| cell | THINK+F | FF+F | SB+F | SB+F − THINK+F | FF+SB+F (exploratory) |
|---|---|---|---|---|---|
| OptiBench (third) | 64.0% @ 17.0k | 68.0% @ 5.0k | 70.0% @ 8.3k | **+5.9 [+3.6, +8.4]** | 69.5% @ 4.2k |
| BWOR | 41.9% @ 19.3k | 41.9% @ 12.7k | 50.0% @ 15.2k | **+8.1 [+2.8, +13.4]** | 45.1% @ 12.0k |
| LogiOR | 38.8% @ 23.8k | 46.4% @ 18.7k | 48.9% @ 19.5k | **+10.1 [+5.4, +14.9]** | 51.8% @ 17.2k |
| OptMATH | 29.0% @ 22.6k | 31.7% @ 13.7k | 34.0% @ 19.3k | **+5.0 [+0.3, +9.7]** | 36.3% @ 13.6k |
- **SB-P3 refuted** (within 2 points of FF+F at no more than its tokens in 0 / 4): on this model SB+F is *more* accurate than FF+F
  (+2.0 to +8.1) but costs 4–66% more tokens, because its non-thinking programs are already right when they pass.
- SB+F beats always thinking with the fact on all four (+5.0 to +10.1, at 49–85% of its tokens): Qwen3.5's long thinking runs out at
  32k on 9–33% of problems; the forced-short think finishes.
- **Exploratory (not pre-registered):** the three-step cascade — the library program if it passes, else short thinking, else full
  thinking — is at least as accurate as FF+F at no more tokens on all four (OptiBench +1.5 @ 84%, BWOR +3.3 @ 94%, LogiOR +5.4 @ 92%,
  OptMATH +4.7 @ 100%), whereas on the leaky models it brings the leak back (HO-SB, Nemotron −5 to −8).
- **Decision as registered.** SB-P1 / P2 held, P3 refuted: short thinking first is the step for leaky models (replacing the review
  gate), not a universal default; where the free check holds, the non-thinking program stays first. Which side a cell is on is what the
  pilot detects (next: HO-P4).

## Addendum HO-SB3 (2026-10-25 05:0x UTC, before any run): the three-step cascade where the free check holds
**Why.** On Qwen3.5-9B's word problems (exploratory, HO-SB) the cascade non-thinking program → short thinking → full thinking (FF+SB+F)
was at least as accurate as the plain recipe at no more tokens in all 4 cells; on leaky cells it brings the leak back. If it holds on
new low-leak cells, the recipe's menu is: FF+SB+F where the check holds, SB+F where it leaks (the pilot picks; HO-P4). **Run (new
cells).** Held-out geometry, where the metamorphic check leaks little for these models (Qwen3.5-9B; Nemotron-3-Nano: 5%):
`run_geo_cross.py ... --distract 0 --algo_hint --think_budget 2000 --max_tokens 8192`, seeds 1–3 (`S2_HOG_<m>_geo_thinkfactb2000`).
Qwen3-14B-AWQ geometry (FF+SB+F +4.5 [+1.0, +8.3] at 37%, HO-SB2 rows) was seen before this addendum and is not counted.
- **SB3-P1:** in both new cells FF+SB+F is no more than 1 point below FF+F at no more than 110% of its tokens.
**Decision.** P1 → the cascade is the recipe's form for low-leak cells (stated with the HO-P4 pilot); otherwise the plain recipe stays.

### Results HO-SB3 (2026-10-25 05:4x UTC; `python poc/analyze_hotb.py 2000 --geo q35 n3n q14a`; 3 seeds, all rows)
| geometry cell | THINK+F | FF+F | SB+F | FF+SB+F | FF+SB+F vs FF+F |
|---|---|---|---|---|---|
| Qwen3.5-9B | 92.0% @ 18.1k | 91.7% @ 5.4k | 94.8% @ 8.9k | 92.7% @ 4.1k | +1.0 at 75% of its tokens ✓ |
| Nemotron-3-Nano | 93.1% @ 1.7k | 93.1% @ 1.1k | **97.2%** @ 2.3k | 94.1% @ 1.4k | +1.0 at 119% ✗ |
| (Qwen3-14B-AWQ, seen before; not counted) | 87.8% @ 6.8k | 90.3% @ 2.6k | 91.3% @ 6.4k | 92.4% @ 2.5k | +2.1 at 96% |
- **SB3-P1 refuted** (1 / 2): on Nemotron-3-Nano, whose full thinking on geometry is already short (1.7k), a 2k-token budget costs more
  than the thinking it replaces, so the cascade adds tokens (+19%) for +1.0 point. Where full thinking is long (Qwen3.5: 18k) the cascade
  is cheaper and as accurate.
- Short thinking first beats always thinking with the fact on all three geometry cells (+2.8 to +4.2; Nemotron +4.2 [+1.4, +6.9]).
- **Reading.** The budget is the knob: a fixed 2k budget helps where full thinking is long and leaks, and costs where full thinking is
  already short. As registered, the cascade is not adopted as the low-leak default; the pilot (HO-P4) decides per cell.

### Results HO-SB2 (2026-10-25 07:4x UTC; `python poc/analyze_hotb.py 2000 [--geo] q14a q8b`; 3 seeds, all rows; OptMATH THINK+F rerun at a 28,672-token context after the first run lost its rows to over-long requests)
| cell | THINK+F | FF+F − THINK+F | SB+F − THINK+F (tokens) |
|---|---|---|---|
| Qwen3-14B-AWQ OptMATH | 23.0% @ 9.9k | — | +2.3 [−1.3, +6.3] (85%) |
| Qwen3-8B OptMATH | 23.3% @ 10.9k | — | +3.3 [+0.0, +7.0] (90%) |
| Qwen3-14B-AWQ geometry | 87.8% @ 6.8k | +2.4 [−0.3, +5.6] | **+3.5 [+0.3, +6.6]** (94%) |
| Qwen3-8B geometry | 78.1% @ 7.8k | **−16.7 [−21.9, −11.5]** | −0.3 [−2.8, +2.1] (98%) |
- **SB2-P1 refuted** (ties or beats in 4 / 4, but at ≤ 90% of the tokens in 2 / 4: the geometry cells use 94–98%; the budgeted
  geometry program fails the metamorphic check often enough that most problems still escalate). **SB2-P2 holds:** Qwen3-8B geometry,
  the claim's worst cell (−16.7 for fact-first, −6.6 with the review gate), is closed (−0.3) — at the cost of always thinking.
- Exploratory: the three-step cascade on Qwen3-8B OptMATH is +6.7 [+2.0, +11.3] at 77% (Qwen3-14B-AWQ +0.3 at 77%).
- **Reading (HO-SB, SB2, SB3).** Short thinking with the fact first never loses to always thinking with the fact in the 14 cells it
  was not chosen on (Nemotron 5, Qwen3.5 5, Qwen3 4): −0.3 to +10.1. It saves tokens where full thinking is long (word problems:
  49–92%) and not where it is short or the short program rarely passes (geometry: 94–137%). It replaces the review gate as the
  leaky-model step: on Nemotron's word problems it is as accurate or more and cheaper in all 4, and on Qwen3-8B geometry it closes the
  gap the gate left (−6.6 → −0.3).

## Addendum HO-SB4 (2026-10-25 07:5x UTC, before any run): is "short thinking first" tied to the 2,000-token budget?
**Why it could change the claim.** The budget 2,000 was fixed from HO-TB before any SB+F result; if SB+F only works near it, the claim must
say "a budget chosen per model" (and the pilot must choose it); if it holds from 1,000 to 4,000 tokens, the claim is "a short think
first". **Run.** `run_form.py <m> formx <seed> --think_budget B`, B ∈ {1,000, 4,000}, seeds 1–3, for the two leaky models where SB+F is
the recommended step: Nemotron-3-Nano and Qwen3-8B, on OptiBench (third), BWOR, LogiOR, OptMATH (8 cells; THINK+F = the stored formxt).
- **SB4-P1:** at B = 1,000 and at B = 4,000 separately, SB+F ties or beats THINK+F (upper bound ≥ 0) in ≥ 7 of the 8 cells.
- **SB4-P2:** the utility (accuracy − 0.5 × ktokens) of SB+F varies by ≤ 2 points across the three budgets in ≥ 6 of the 8 cells.
**Decision.** P1 and P2 → the claim says "a short think first (1–4k tokens)"; otherwise the budget is part of what the pilot chooses.

## Addendum HO-CM (2026-10-25 08:2x UTC, offline, before computing the pilot): the baseline matched in the check, not only in the fact
**Why it could change the claim.** Every "ties or beats always thinking with the fact" in the claim compares with one think that ignores
its own visible failures. Exploratory (FINDINGS 08:29): a second think on a visible failure (T→T) adds +2.5 to +12.3 points at 119–164% of
the tokens on 16 word cells. If check-matched thinking dominates the recipe's policies at λ = 0.5, the claim's comparisons must be
restated against it. **Run (stored rows only).** `analyze_hop.py --repair --fair --sb --cm q14a q8b n3n q35`: HO-P4's 54 cells with two
more policies — T→T (thinking with the fact; on its visible failure, the next seed's stored think) and SB→T→T (short think first, then
T→T); tokens of every step counted; geometry uses the next seed's thinkfact.
- **CM-P1:** with T→T in the menu, the best of the recipe's policies (FF+F, FF-R0, FFR, SB+F, FF+SB+F) is within 1.0 utility point of
  T→T or above it in ≥ 40 of 54 cells (the recipe is on the frontier at λ = 0.5).
- **CM-P2:** always T→T has a larger regret than always SB+F over the 54 cells.
- **CM-P3:** the 30-label pilot over the nine policies keeps regret ≤ 1.2 (HO-P4: 1.19).
**Decision.** CM-P1 refuted → the claim is restated: what the recipe buys is tokens at matched accuracy only where the check holds;
against a check-matched think it is a token-accuracy trade elsewhere. CM-P1 and P2 hold → the claim stands with the stronger baseline,
and every table gains a T→T column.

### Results HO-CM (2026-10-25 08:4x UTC; `python poc/analyze_hop.py --repair --fair --sb --cm q14a q8b n3n q35`, 54 cells, λ = 0.5)
| | best in (of 54) | always this policy: regret |
|---|---|---|
| SB→T→T (short think, then thinking with a retry on a visible failure) | 21 | **1.74** |
| T→T (thinking with the fact, retry on a visible failure) | 16 | 3.40 |
| FF+SB+F / FF-R0 / SB+F | 10 / 4 / 3 | 7.28 / 9.15 / 3.00 |
| THINK+F (one think: the baseline used so far) | 0 | 7.64 |
- **CM-P1 refuted** (the best of the recipe's policies is within 1.0 of T→T or above in 37 / 54 cells). Per model × benchmark (mean
  utility difference, recipe's best − T→T): ahead on Qwen3.5-9B (+2.1 to +11.7), Nemotron OptMATH (+8.1) and Qwen3-14B-AWQ geometry
  (+2.1); behind on the leaky models' hard word problems (Qwen3-14B-AWQ LogiOR −4.0, BWOR −2.0; Qwen3-8B BWOR −2.7, geometry −2.1;
  Nemotron LogiOR −2.7). **CM-P2 holds** (always T→T 3.40 > always SB+F 3.00). **CM-P3 refuted** (pilot regret 1.35 > 1.2; adding the
  two check-matched policies still raises it by +1.37 per cell).
- **Decision as registered.** The claim is restated against the stronger baseline: one think that ignores its own visible failures is
  a weak baseline (regret 7.64; never best). The recipe's check pays inside thinking too — retrying a visibly failed think is the
  largest single gain on the hard word problems — and the best fixed policy is short thinking first with a retry on a visible failure
  (SB→T→T, regret 1.74). The recipe without thinking first (FF+F) is on the frontier only where the check holds (Qwen3.5, geometry);
  on the leaky models' hardest word problems the check-matched think is 2–4 utility points ahead of every cheap-first policy.
*HO-CM supplement (2026-10-25 09:4x UTC, computed after the results above; stored runs): the gpt-oss models against the check-matched
think (no budgeted runs exist for them; their cheap arm already reasons at low effort). FF+F − T→T: gpt-oss-20b OptiBench −0.8 [−3.0,
+1.5], BWOR **−10.2 [−16.7, −4.1]**, LogiOR **−8.0 [−12.3, −4.0]**, at 37–44% of T→T's tokens; gpt-oss-120b OptiBench −2.3 [−4.1,
−0.7], BWOR −0.8, LogiOR −4.7 [−9.1, −0.7], at 47–51%. Against one think these cells were ties (−1.2 to +3.7). So on the hard word
problems the check-matched think is more accurate for every model; the recipe is the cheap end of the frontier, not a free saving.*

## Addendum HO-CC (2026-10-25 09:4x UTC, before any run): the check-at-every-step order on contest programming
**Why it could change the claim.** The restated claim (HO-CM) — apply the free check at every step; without labels, short think → full
think → retry on a visible failure — was measured on OR word problems and generated geometry only. Contest programming has the classic
leaky check: a program passes the statement's sample tests and fails the hidden ones. If the order holds there, the claim is about
programs, not about OR; if not, it is stated for those two domains. Related work: sample tests as a filter (AlphaCode, CodeT) and test-gated
cascades *between* models (2405.15842); we test the order of thinking budgets inside one model against a check-matched think.
**Run.** 311 validated Codeforces geometry problems (hidden tests; `CC_SET=full poc/run_cc.py`), no fact; Qwen3-14B-AWQ (1 × 3090 per
seed) and Nemotron-3-Nano (4 × 3090), seeds 1–3: `plain` (non-thinking, 6,000 tokens), `tb2000` (2,000-token think, then the answer),
`think` (16,000 tokens). A visible failure = the program fails a sample (public) test, crashes or prints nothing on it. Policies: T (one
think), T→T (on T's visible failure the next seed's think), SB→T→T, FF+T (plain first), FF+SB+T; tokens of every step counted.
- **CC-P1:** for each model, SB→T→T ties or beats T→T (paired 95% upper bound ≥ 0) at ≤ 90% of its tokens.
- **CC-P2 (a label-free signal, per problem):** among plain programs that pass the samples, those whose outputs agree with the short-think
  program's on every test input (inputs only, no expected outputs) pass all hidden tests ≥ 20 points more often than those that disagree.
**Decision.** CC-P1 → the order is stated for programs in general (three domains); otherwise for OR and geometry. CC-P2 → cross-mode
agreement is reported as a label-free leak signal (the project's open problem) and tested as a gate next.

### Results HO-CC as registered (2026-10-25 15:0x UTC; `python poc/analyze_hocc.py q14a n3n`; 311 problems × 3 seeds, all rows) — not interpretable for the order
| model | T (one think, 16k) | T→T | SB→T→T − T→T (tokens) | SB+T − T→T | FF+T − T→T |
|---|---|---|---|---|---|
| Qwen3-14B-AWQ | 32.5% @ 13.4k | 37.0% @ 22.9k | +1.1 [−1.0, +3.1] (92%) | −1.5 (57%) | −6.6 (51%) |
| Nemotron-3-Nano | 12.6% @ 15.2k | 15.8% @ 29.0k | +13.5 [+10.4, +16.5] (80%) | +13.1 (46%) | +8.9 (41%) |
- As registered, CC-P1 is refuted for Qwen3-14B-AWQ (a tie, but at 92% > 90% of the tokens) and holds for Nemotron-3-Nano.
- **But the full think is broken by its cap, so the comparison says nothing about the order.** At run_cc's 16,000-token think, 808 of
  933 Nemotron thinks and 528 of 933 Qwen3-14B-AWQ thinks hit the cap without a program (Nemotron's full think solves 12.6%, *below* its
  non-thinking program's 22.3%). Every other held-out thinking arm of these models used 32k (HO-N4); 16k was run_cc's old default, carried
  over without checking. **Amendment (before any 32k row is read):** both models' think is rerun at 32,000 tokens (`--think --max_tokens
  32000`, tag `<m>_think32k`) and CC-P1 is scored on it; the 16k table above stays as the record. CC-P2 does not involve the think and is
  scored as registered.

### Results HO-SB4 (2026-10-25 15:4x UTC; `python poc/analyze_hotb.py <B> n3n q8b`, B ∈ {1,000, 2,000, 4,000}; 3 seeds, all rows)
SB+F − THINK+F (tokens vs THINK+F); utility U = accuracy − 0.5 × ktokens:
| cell | B = 1,000 | B = 2,000 | B = 4,000 | U at 1k / 2k / 4k |
|---|---|---|---|---|
| Nemotron OptiBench | +3.8 (64%) | +3.8 (72%) | +4.0 (77%) | 69.5 / 69.3 / 69.3 |
| Nemotron BWOR | +4.1 (71%) | +5.3 (79%) | **+10.2 [+5.3, +15.4]** (81%) | 49.1 / 49.8 / 54.5 |
| Nemotron LogiOR | +2.2 (80%) | +3.3 (92%) | +4.0 (96%) | 41.6 / 41.9 / 42.5 |
| Nemotron OptMATH | +3.3 (68%) | +6.3 (73%) | +7.0 (80%) | 26.6 / 29.1 / 29.1 |
| Qwen3-8B OptiBench | **−3.1 [−5.8, −0.8]** (51%) | −0.3 (62%) | +1.3 (86%) | 62.7 / 65.1 / 65.9 |
| Qwen3-8B BWOR | −0.8 (83%) | +2.4 (86%) | +2.4 (99%) | 41.4 / 44.5 / 43.8 |
| Qwen3-8B LogiOR | **−6.2 [−10.9, −1.8]** (88%) | −4.0 (92%) | +0.7 (109%) | 33.8 / 35.7 / 39.5 |
| Qwen3-8B OptMATH | +1.7 (84%) | +3.3 (90%) | +4.3 (103%) | 20.4 / 21.8 / 22.1 |
- **SB4-P1 refuted** (at 1,000 tokens 6 / 8 tie or beat — Qwen3-8B loses on OptiBench and LogiOR; at 4,000: 8 / 8). **SB4-P2 refuted**
  (utility within 2 points across the budgets in 3 / 8). The best budget at λ = 0.5 is 4,000 in 6 / 8 cells, 2,000 in 1, 1,000 in 1.
- **Reading.** "Short thinking first" is not tied to 2,000 tokens, but it is not budget-free either: 1,000 is too short for Qwen3-8B;
  between 2,000 and 4,000 a longer first think buys accuracy (Nemotron BWOR +10.2 at 4,000) for tokens. **Decision as registered:** the
  claim says "a short think first (2–4k tokens)", and the budget joins what the 30-label pilot chooses.

### Results HO-CC, CC-P2 (2026-10-25 17:4x UTC; `python poc/analyze_hocc.py --agree q14a n3n` on a CPU node; 3 seeds)
Among non-thinking programs that pass the statement's samples, run with the same seed's short-think program on every test input (inputs
only; outputs compared with the problem's tolerance):
| model | agree on every input: pass all hidden tests | disagree, or the short think fails the samples | (short think passes the samples but disagrees) |
|---|---|---|---|
| Qwen3-14B-AWQ | **92.7%** (n = 110) | 18.8% (n = 117) | 8.5% (n = 59) |
| Nemotron-3-Nano | **97.0%** (n = 168) | 33.8% (n = 133) | 31.7% (n = 41) |
- **CC-P2 holds** (+73.9 and +63.2 points ≥ +20). On a domain it was not seen on, agreement between a model's non-thinking program and
  its short-think program on the test inputs (no expected outputs) separates hidden-test-correct from leaked programs: an agreeing
  program is right 93–97% of the time. With the word-problem result (exploratory: 78% vs 16%), this is the project's label-free signal
  for when the cheap program is wrong — the open problem since the start — with OptMATH (shared formulation errors) as its known limit.

### Results HO-CC, CC-P1 as amended (2026-10-26 03:2x UTC; `python poc/analyze_hocc.py --think_tag think32k n3n q14a`; 311 problems × 3 seeds)
| model | T (one think, 32k) | T→T | SB→T→T (tokens vs T→T) | SB→T→T − T→T | FF+T − T→T | think at the cap |
|---|---|---|---|---|---|---|
| Qwen3-14B-AWQ | 40.8% @ 16.6k | **45.3%** @ 24.6k | 43.8% (94%) | −1.5 [−3.3, +0.2] | −7.8 [−9.9, −5.8] | 10 / 933 |
| Nemotron-3-Nano | 34.9% @ 26.9k | **41.4%** @ 44.9k | 40.8% (82%) | −0.5 [−2.4, +1.3] | −5.5 [−7.7, −3.2] | 525 / 933 |
- **CC-P1 refuted** (holds for Nemotron-3-Nano: a tie at 82% of the tokens; for Qwen3-14B-AWQ a tie at 94% > 90%). Decision as
  registered: the order is stated for OR word problems and geometry; on contest programming short thinking first saves 6–18% of the
  check-matched think's tokens at a 0.5–1.5-point cost, and the non-thinking program first loses 5–8 points.
- What does transfer: **the check at every step.** A retry on a visibly failed think adds +4.5 (Qwen3-14B-AWQ) and +6.4 (Nemotron) over
  one think, as on the word problems. Caveat: Nemotron's full think is still cut at 32k on 56% of contest problems (507 without a
  program), so its think-based numbers here are lower bounds; Qwen3-14B-AWQ's are not.

## Addendum HO-CAP (2026-10-26 03:2x UTC, before any run): is short thinking first's gain an artefact of the full think's cap?
**Why it could change the claim.** Part of SB+F's gain over always thinking comes from problems where the full think runs out of tokens
(Qwen3.5-9B: 18.7% of OptMATH and 32.6% of LogiOR thinks hit 32k; Nemotron-3-Nano: 56% of contest thinks hit 32k). If the gain vanishes
against an uncapped think, the claim must read "short thinking first beats a *capped* think; against an uncapped one it saves tokens".
**Run.** Thinking with the fact at a 64,000-token cap: Qwen3.5-9B on LogiOR and OptMATH (`run_form.py q35t64 formx <seed> --tarm --think
--max_tokens 64000`, context 73,728; tag q35t64 is the same model under another name), Nemotron-3-Nano on the 311 contest problems
(`run_cc.py run n3n_think64k <seed> --think --max_tokens 64000`); seeds 1–3; SB+F / SB→T→T recomputed against these.
- **CAP-P1:** on both Qwen3.5-9B cells SB+F still ties or beats THINK+F at 64k (upper bound ≥ 0), at ≤ 70% of its tokens.
- **CAP-P2:** on contests Nemotron's SB→T→T still ties T→T at 64k at ≤ 90% of its tokens.
**Decision.** Both → the gain is not a cap artefact; otherwise the claim is restated against an uncapped think as a token saving only.

### Results HO-CAP, Qwen3.5-9B: CAP-P1 (2026-10-26 07:3x UTC; 64k thinks merged from shards; 3 seeds; SB+F escalates to the 64k think)
| cell | THINK+F 32k (at cap) | THINK+F 64k (at cap) | SB+F | SB+F − THINK+F 64k (tokens) | T64→T64 | SB→T→T − T64→T64 (tokens) |
|---|---|---|---|---|---|---|
| LogiOR | 38.8% @ 23.8k (90) | 47.8% @ 29.5k (13) | 51.8% @ 23.9k | +4.0 [−1.1, +8.7] (81%) | 60.9% @ 45.7k | −1.8 [−6.2, +2.2] (81%) |
| OptMATH | 29.0% @ 22.6k (56) | 31.7% @ 24.4k (3) | 36.0% @ 20.5k | **+4.3 [+0.3, +8.7]** (84%) | 40.7% @ 34.3k | +0.7 [−3.7, +5.0] (80%) |
- **CAP-P1 refuted on tokens** (SB+F ties or beats the 64k think in 2 / 2, but at 81–84% of its tokens, not ≤ 70%). The accuracy gain is
  not a cap artefact: lifting the cap helps the full think (+9.0 on LogiOR, +2.7 on OptMATH) yet short thinking first stays +4 ahead;
  the saving against an uncapped think is 16–19%. Against the check-matched think at 64k, short think → think → retry ties (−1.8, +0.7)
  at 80–81% of its tokens. CAP-P2 (Nemotron, contests) is scored when its 64k thinks finish.

## Addendum HO-TR (2026-10-26 08:3x UTC, before any run): repair a failed think from its error instead of thinking again?
**Why it could change the claim.** The largest transferable lever is the check applied to thinking: a second think on a visible failure
(T→T) adds +2.5 to +12.3 points but costs 19–64% more tokens. If one cheap non-thinking repair turn shown the error recovers most of that
at a fraction of the cost, the recipe's last step becomes "repair, then think again only if the repair fails". Prior work: self-repair
is often *not* more cost-effective than resampling for code (Olausson et al., ICLR 2024, "Is Self-Repair a Silver Bullet?"); our test is
the same question inside the fact-matched recipe. **Run.** `run_repair.py <m> <seed> formxt`: every thinking-with-the-fact program that
visibly fails (crash, no value, 'No Best Solution') and has code gets one non-thinking repair turn with the error (thinks that ran out
without a program cannot be repaired and go to a second think); Qwen3-14B-AWQ, Qwen3-8B, Nemotron-3-Nano, Qwen3.5-9B × OptiBench (third),
BWOR, LogiOR, OptMATH, seeds 1–3. Policies: T→R (repair, else the next seed's think when no code or the repair fails visibly) vs T→T.
- **TR-P1:** T→R recovers ≥ 50% of T→T's accuracy gain over one think in ≥ 10 of the 16 cells, at ≤ 50% of T→T's extra tokens.
- **TR-P2:** SB→T→R ties SB→T→T (upper bound ≥ 0) in ≥ 12 of the 16 cells at ≤ 90% of its tokens.
**Decision.** P1 and P2 → the recipe ends with a repair before a second think; otherwise a fresh think stays the retry (as Olausson et al.).

### Results HO-TR (2026-10-26 09:0x UTC; `python poc/analyze_hotr.py`; 16 word cells × 3 seeds)
- **TR-P1 refuted (0 / 16), TR-P2 refuted (0 / 16).** Repairing a visibly failed think from its error, then thinking again only if the
  repair does not run, is *at least as accurate* as thinking again (T→R recovers 90–145% of T→T's gain; 15 / 16 cells ≥ 100%) but costs
  79–104% of T→T's extra tokens, not ≤ 50%: only 4–36 of the 26–117 repairs per cell produce a running program, and the rest still need
  the second think. With a short think first, SB→T→R is +0.0 to +2.8 over SB→T→T (significant in Qwen3.5-9B BWOR +2.8 [+0.8, +5.3],
  OptMATH +1.7, Qwen3-14B-AWQ BWOR +1.6, OptMATH +1.3) at 95–102% of its tokens.
- **Reading.** As Olausson et al. (ICLR 2024) found for code, a repair turn is not a cheaper substitute for a second sample: most failed
  thinks cannot be fixed by a cheap turn. It is a small, nearly free accuracy add-on before the second think (+1 to +3 where it works).
  As registered, the recipe's retry stays a fresh think; the repair is noted as an optional step.

### Results HO-CAP, Nemotron-3-Nano on contests: CAP-P2 (2026-10-26 12:4x UTC; `python poc/analyze_hocc.py --think_tag think64k n3n`; 311 × 3)
At 64k the think hits the cap on 13 of 933 problems (32k: 525) and solves 55.4% (32k: 34.9%); with a retry 58.5% @ 40.3k.
SB→T→T 55.4% @ 33.7k: **−3.1 [−4.8, −1.4]** against T→T at 84% of its tokens; SB+T −5.4; the non-thinking program first −6.0.
- **CAP-P2 refuted.** The contest tie at 32k (HO-CC, −0.5) was an artefact of the capped think: against an uncapped think, short thinking
  first loses 3 points for a 16% saving on contest problems. The retry still adds +3.1 over one think.
- **HO-CAP overall (decision as registered).** On word problems the short think's gain survives an uncapped think (Qwen3.5-9B +4.0 / +4.3
  at 81–84% of the tokens); on contest programming it does not (Nemotron −3.1). The claim says: short thinking first pays where problems
  need modelling more than long search (OR word problems, geometry) and is a token–accuracy trade on contest programming; the check at
  every step (the retry) pays in all three domains.

## Addendum HO-32 (2026-10-26 12:4x UTC, before any run): the final recipe on a larger hybrid model (Qwen3-32B-AWQ, 2 × RTX 3090)
**Why it could change the claim.** The final recipe — fact; short think first where the check leaks; full think only on a visible
failure; think again once on failure — and its no-label default (SB→T→T) were measured on four hybrid models of 8–30B (3B active). A
32B dense model, never run on these held-out thinking arms, tests whether the order and the label-free leak signal hold at a larger size.
**Run.** Qwen3-32B-AWQ (tag q32b; tensor parallel over 2 × RTX 3090), seeds 1–3: `formx` (stored for OptiBench / OptMATH, new for BWOR /
LogiOR), `formx --think_budget 2000`, `formx --tarm --think --max_tokens 32000` (thinking with the fact, 32k as for the other unseen
models); OptiBench on the HO-TF third. Policies as HO-CM (T, T→T, FF+F, SB+F, SB→T→T, FF+SB+F; λ = 0.5).
- **32-P1:** SB→T→T is within 1.0 utility point of the best of the six policies in ≥ 3 of the 4 cells.
- **32-P2:** the retry pays: T→T − T ≥ +2 points in ≥ 3 of the 4 cells.
- **32-P3 (label-free signal):** pooled over the 4 cells, passing non-thinking programs that agree with the short-think program are right
  ≥ 30 points more often than those that disagree.
**Decision.** All three → the final recipe and its leak signal are stated for 8B–32B hybrid models; each refuted part is stated as a limit.
*HO-32 setting fix (2026-10-26 14:1x UTC, before any row): Qwen3-32B-AWQ allows at most 40,960 positions, so its server runs at 40,960 (not 45,056); a library prompt longer than ~8.9k tokens plus the 32k think would be rejected and is logged, not written.*

## Addendum HO-OSB (2026-10-26 21:4x UTC, before any run): a short think first for gpt-oss (the third family)
**Why it could change the claim.** The recipe's first step differs by family: hybrid-thinking models (Qwen3, Qwen3.5, Nemotron-3-Nano)
write the first program after a 2–4k-token think; gpt-oss has no budgeted think, so its first program comes from low reasoning effort
(median 0.7–0.8k tokens on BWOR / LogiOR) — and there its order low effort → medium think → retry trails the check-matched think
(gpt-oss-20b: BWOR −7.7 [−13.8, −1.6], LogiOR −5.1; exploratory, 2026-10-26 03:24). Low effort is about as long as the 1k first think
that was too short for Qwen3-8B (HO-SB4). If a 2k medium-effort think first closes the gap at fewer tokens, "a short think (2–4k) first"
holds for all three families; if not, gpt-oss stays the exception (its cheap end of the frontier is low effort). Related: budget
forcing (s1, Muennighoff et al. 2025); per-problem budgets (TALE, Han et al. 2024; L1, Aggarwal & Welleck 2025); here the budget is the
first step of a check cascade inside one model, for a model whose only control is an effort level.
**Run.** gpt-oss-20b (1 × RTX 3090), seeds 1–3, `run_form.py oss20 formx <seed> --think_budget 2000` with POC_HARMONY set (new, as
budget_chat for Qwen3: the model's own chat template at medium effort, the analysis channel cut at 2,000 tokens, then the final channel
forced; tokens = analysis + final) on the OptiBench third, BWOR and LogiOR (OptMATH has no stored medium think for gpt-oss). Stored arms:
formx (low effort) and formxt (medium, 16k). Policies as HO-CM (T, T→T, FF+F, SB+F, SB→T→T, FF+SB+F; λ = 0.5; `analyze_ho32.py oss20`).
- **OSB-P1:** SB→T→T ties or beats T→T (paired 95% upper bound ≥ 0) on BWOR and on LogiOR, at ≤ 85% of T→T's tokens.
- **OSB-P2:** the short think leaks less than low effort: SB+F − FF+F ≥ +3 points on BWOR and on LogiOR.
- **OSB-P3:** SB→T→T is within 1.0 utility point of the best of the six policies in ≥ 2 of the 3 cells.
**Decision.** P1 and P2 → the recipe's first step is stated for all three families as a 2k think (for gpt-oss: medium effort, cut);
low effort is too short a first think on the hard word problems. P1 refuted → gpt-oss stays the exception and the claim names it.

### Results HO-OSB (2026-10-26 22:1x UTC; `python poc/analyze_ho32.py oss20`; gpt-oss-20b, 3 seeds, all rows; λ = 0.5)
| cell | T (one think) | T→T | FF+F (low effort first) | SB+F (2k think first) | SB→T→T | SB→T→T − T→T (tokens) |
|---|---|---|---|---|---|---|
| OptiBench third | 71.6% @ 2.26k | 74.9% @ 2.59k | 74.1% @ 1.09k | 75.9% @ 2.13k | **76.9% @ 2.26k** | +2.0 [−0.0, +4.0] (87%) |
| BWOR | 60.2% @ 4.51k | **69.1% @ 5.73k** | 58.9% @ 2.10k | 65.4% @ 3.39k | 67.1% @ 3.93k | −2.0 [−6.9, +2.4] (69%) |
| LogiOR | 50.7% @ 4.69k | 58.0% @ 6.70k | 50.0% @ 2.98k | 58.3% @ 4.26k | **61.2% @ 5.54k** | +3.3 [−0.4, +7.2] (83%) |
- **OSB-P1 holds** (SB→T→T ties T→T on BWOR and LogiOR at 69% / 83% of its tokens; the low-effort order trailed by −7.7 / −5.1).
  **OSB-P2 holds** (SB+F − FF+F: BWOR +6.5 [+1.2, +12.2], LogiOR +8.3 [+4.3, +13.0]; OptiBench +1.8 [−0.5, +4.0]). **OSB-P3 holds**
  (SB→T→T has the best utility on OptiBench and LogiOR; on BWOR it is 1.1 below T→T).
- Mechanism (raw rows): the 2k medium think passes the free check about as often as low effort (69–88% vs 68–84%) but its passing
  programs are wrong less often on the hard sets (BWOR 30% vs 38%, LogiOR 23% vs 36%; OptiBench 20% vs 22%). It stops by itself in 37–41%
  of BWOR / LogiOR problems (median think = the 2,000 cap there; OptiBench 1,320); when cut, the forced final answer still writes a
  program that runs and prints a value in 67–75% of problems (natural stop: 72–86%), and its failures are visible API errors (e.g. an
  invented `IntervalVar.PresenceBoolVar`), which escalate to the full think.
- Cross-mode agreement (32-P3's measure, reported): a passing low-effort program that agrees with the short-think program is right 87%
  of the time, 20% when it prints a different value (gpt-oss-20b, 3 cells pooled).
- **Decision as registered:** the recipe's first step where the check leaks is stated for all three families as a 2k think —
  budget-forced for the hybrid-thinking models, medium effort cut at 2,000 tokens for gpt-oss. Low effort (0.7–0.8k tokens) is too short a first think on the
  hard word problems, as 1k was for Qwen3-8B (HO-SB4). gpt-oss-120b is not run.
