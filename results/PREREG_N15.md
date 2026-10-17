# Pre-registration N15: choosing the TOOL itself: which solver library should solver code use?

Written 2026-10-16 12:30 UTC, before any run. Results go below; this section is not edited afterwards.

**Why.** The user reads the project as "selecting adequate tools for problems". So far "tools" meant helper functions and
documentation; the solver library is the other tool choice, and F3 / R1 failures are mostly API facts of the OR-Tools routing
library. OR-Tools ships three solver APIs (CP-SAT, the routing library, the MIP wrapper pywraplp with SCIP / CBC); a plain-Python
heuristic is the no-tool option. Question: does the forced library change accuracy and tokens per problem, and does the model's own
choice pick its best library?

**Design.** The 8 synthetic optimization problems of N10 (knapsack, tsp, color, sched, binpack, vcover, cvrp, vrptw; 4 instances per
size = 100 items), no documentation, T = 0.7, seeds 1–2. Conditions (`run_co.py --lib`): free choice among the three APIs; CP-SAT;
routing library (tsp, cvrp, vrptw only); MIP (pywraplp); no library (`--arms heuristic`); the project's default sentence (CP-SAT, or
routing for TSP / VRP; seed 1 = N10 nodoc_s1). Models: Qwen3-32B-AWQ (GPU 0), gpt-oss-20b low (GPU 1), Qwen3.6-35B-A3B (GPU 2).
Scored optimal (feasible reported); tokens = output tokens; the library actually used is read from the imports.
- N15-P1: for each model, the best forced library per problem beats free choice by ≥ 10 points on ≥ 2 of the 8 problems.
- N15-P2: the MIP wrapper is the weakest library on ≥ 5 of 8 problems for each model.
- N15-P3: under free choice, the model imports its best library (by the forced results) on ≤ 60% of problems.
- N15-P4: CP-SAT beats the routing library on CVRP or VRPTW for at least one model.

Addendum (2026-10-16 12:31 UTC, before any result): a fourth model, gpt-oss-120b low (16k cap) on GPU 3, same design and
predictions (default seed 1 rerun as S2_N15_oss120_default_s1, since N10 did not run gpt-oss-120b). poc/queue_s2_n15b.sh.

## Results (2026-10-16 12:47 UTC; seeds 1–2 pooled; results/n15_analysis.log)
Optimal share over the 8 problems (output tokens per program):
| model | free choice | CP-SAT | routing (TSP / VRP only) | MIP (pywraplp) | no library | project default | best library per problem (hindsight) |
|---|---|---|---|---|---|---|---|
| Qwen3-32B | 41.5% (0.5k) | 42.5% | 0.0% | 46.0% | 21.5% | 44.0% | **59.5%** |
| gpt-oss-20b | 71.0% (0.7k) | 64.0% | 25.0% | 72.5% | 42.5% | 72.5% | 75.5% |
| Qwen3.6 | 55.5% (1.1k) | 58.0% | 5.6% | 42.5% | **59.5%** | 50.0% | 66.5% |
| gpt-oss-120b | 81.0% (1.2k) | 64.5% | 80.6% | 48.0% | 51.5% | 81.0% | 85.0% |
Largest cells (raw outputs read): Qwen3-32B bin packing MIP 23 / 24 vs CP-SAT 1 / 24 (CP-SAT programs crash on reification:
`Constraint … has no attribute …`, `Invalid boolean literal`); Qwen3.6 TSP in plain Python 22 / 32 vs routing library 2 / 32 and
free choice 6 / 32; gpt-oss-120b CVRP routing 22 / 24 vs CP-SAT 2 / 24. Free choice is a habit: CP-SAT for every non-routing problem
and the routing library for TSP / VRP (all four models), whatever works best for that model.
- **N15-P1 holds** for all four models (the best forced library beats free choice by ≥ 10 points on 3 / 2 / 3 / 3 problems).
- **N15-P2 refuted** except for gpt-oss-120b (MIP weakest on 2 / 2 / 4 / 6 problems): MIP is the *best* library for Qwen3-32B and gpt-oss-20b on several packing / scheduling problems.
- **N15-P3 holds** for three models (free choice = best library on 4 / 4 / 2 of 8), refuted for gpt-oss-120b (6 / 8).
- **N15-P4 refuted**: the routing library is never worse than CP-SAT on CVRP / VRPTW.
Caveat: TSP "infeasible" outputs include tours printed with the closing city (the E1 scoring caveat), the same in every condition.

## N15c pre-registration (2026-10-16 12:47 UTC, before computing; offline): a library tournament on a few instances
Per model and problem: run every library (CP-SAT, routing where it applies, MIP, no library) on the probe instances (instance 0 of
each size, seed 1); keep the library with the most feasible plans, ties broken by the better objective rank on the probes (no
reference used); commit to it for the problem's other instances. Probe tokens charged. Compared on the committed items with free
choice, the default and the hindsight best library.
- N15c-P1: the tournament ≥ free choice for every model, and ≥ free + 5 points pooled over models.
- N15c-P2: the tournament is within 5 points of the hindsight best library per problem for every model.

## N15c results (2026-10-16 12:47 UTC; results/n15c_analysis.log; 150 committed items per model)
| model | tournament (probe tokens charged) | free choice | default | best library per problem (hindsight) |
|---|---|---|---|---|
| Qwen3-32B | **54.7% @ 0.8k** | 40.7% @ 0.5k | 43.3% | 58.7% |
| gpt-oss-20b | 72.7% @ 1.2k | 72.0% @ 0.7k | 73.3% | 75.3% |
| Qwen3.6 | 59.3% @ 2.4k | 55.3% @ 1.1k | 50.0% | 66.7% |
| gpt-oss-120b | 74.0% @ 1.9k | **83.3% @ 1.2k** | 80.7% | 87.3% |
**N15c-P1 refuted** (+14.0 / +0.7 / +4.0 / −9.3 points; pooled +2.4), **P2 refuted** (−4.0 / −2.6 / −7.4 / −13.3). Three probe
instances per problem are too few: gpt-oss-120b's tournament picks plain Python for CVRP and CP-SAT for TSP, where its routing-library
habit was right. Same lesson as N11: probing a few instances helps a model whose habit is bad (Qwen3-32B) and hurts one whose habit
is good.

## N15d pre-registration (2026-10-16 12:47 UTC, before computing; offline): a library portfolio per instance
Run two (or all) libraries on every instance and keep, per instance, the feasible plan with the best objective (label-free: no
reference). Pairs: free choice + MIP, free + no library, and all four libraries; tokens = sum of the programs written.
- N15d-P1: free + MIP ≥ the hindsight best library per problem (N15 table) for Qwen3-32B and gpt-oss-20b, at ≤ 2.2 × free choice's tokens.
- N15d-P2: the all-library portfolio ≥ every single policy for every model (at ≈ 4 × the tokens).

## N15d results (2026-10-16 12:48 UTC; results/n15d_analysis.log)
Per-instance portfolio (best feasible objective, no reference), optimal share and output tokens per instance:
| model | free | free + MIP | free + no library | all four libraries | hindsight best library per problem (N15) |
|---|---|---|---|---|---|
| Qwen3-32B | 41.5% @ 0.5k | 59.0% @ 1.2k | 55.5% @ 1.0k | **64.5% @ 1.9k** | 59.5% |
| gpt-oss-20b | 71.0% @ 0.7k | 82.5% @ 1.5k | 83.0% @ 1.5k | **84.5% @ 2.7k** | 75.5% |
| Qwen3.6 | 55.5% @ 1.1k | 63.0% @ 2.4k | 73.5% @ 2.9k | **78.5% @ 4.9k** | 66.5% |
| gpt-oss-120b | 81.0% @ 1.2k | 87.5% @ 2.4k | 89.0% @ 3.1k | **94.5% @ 4.7k** | 85.0% |
**N15d-P1:** holds for gpt-oss-20b (82.5% ≥ 75.5% at 2.1 ×), narrowly refuted for Qwen3-32B (59.0 vs 59.5%, 2.4 ×). **N15d-P2 holds**
(the all-library portfolio beats every single policy for all four models).
Equal-budget control (2 programs per instance, seed-1 instances): the same library twice vs two libraries:
Qwen3-32B free × 2 47.0% vs free + MIP **61.0%**; Qwen3.6 65.0% vs free + no library **74.0%**; gpt-oss-20b **84.0%** vs 79.0–83.0%;
gpt-oss-120b **94.0%** vs 89.0%. A second *library* beats a second *sample* only for the models whose habitual library is weak for
them; for gpt-oss, resampling its own habit is as good or better. Same pattern as N11 / N15c and the second-opinion results (N12):
diversity pays where the default is systematically wrong.

## N15e pre-registration (2026-10-16 12:48 UTC, before running): library choice on a real benchmark (job-shop la01–la40)
H5 prompt plus one sentence (`JSSP_LIB`): CP-SAT / MIP (pywraplp) / no library; the H5 runs are the "OR-Tools available" default
(gpt-oss-120b and gpt-oss-20b low, Qwen3-32B and Qwen3.6 no-think: sol_<m>_plain). 40 instances × seeds 1–2; feasible + gap to the
CP-SAT reference. poc/queue_s2_n15e.sh, GPUs 0–3, one condition at a time per model (CPU load).
- N15e-P1: Qwen3-32B: no library ≥ 50% feasible while CP-SAT ≤ 20%; the no-library plans have a median gap ≥ 10%.
- N15e-P2: gpt-oss-120b: CP-SAT feasible ≥ 90% with median gap < 1%; MIP ≤ 50% feasible.
- N15e-P3: a per-instance portfolio of the default and the no-library program (best feasible makespan) is at least as feasible as
  the best single condition for every model, with a median gap within 1 point of that condition's.

## N15e results (2026-10-16 14:20 UTC; job-shop la01–la40, seeds 1–2; results/h5/n15e_analysis.log)
Feasible of 80 (within 5% of the reference) @ output tokens per program:
| model | default ("OR-Tools available") | CP-SAT | MIP | no library | portfolio default + none | portfolio all four |
|---|---|---|---|---|---|---|
| Qwen3-32B | 8 (4) @ 0.6k | 3 (2) | 2 (0) | 23 (0) @ 0.4k | 28 (4) @ 1.1k | 31 (6) @ 2.4k |
| Qwen3.6 | 64 (64) @ 0.9k | 52 (52) | 7 (6) | 44 (2) @ 1.3k | 73 (64) @ 2.2k | **79 (78)** @ 4.4k |
| gpt-oss-20b | 63 (63) @ 1.0k | 62 (62) | 8 (7) | 75 (3) @ 0.6k | 79 (66) @ 1.6k | **80 (78)** @ 3.4k |
| gpt-oss-120b | 68 (68) @ 0.9k | 68 (66) | 23 (13) | 80 (3) @ 0.8k | 80 (69) @ 1.8k | **80 (79)** @ 3.8k |
Every model's default imports CP-SAT. MIP mostly times out (34–51 of its failures are `tle`: the disjunctive big-M model is slow).
Plain-Python programs are almost always feasible but are greedy list schedulers (raw: gpt-oss-120b la01 makespan 858 vs 666;
median gap 25–430%). So the libraries are complementary: CP-SAT gives near-optimal plans when it runs, plain Python a valid fallback.
**N15e-P1 refuted** (Qwen3-32B no library 23 / 80, not ≥ 40; CP-SAT 3 / 80 ≤ 16 holds; gap 430% ≥ 10% holds). **N15e-P2 refuted on
the first clause** (gpt-oss-120b CP-SAT 68 / 80 = 85%, not ≥ 90%; gap 0.00%; MIP 23 / 80 ≤ 40 holds). **N15e-P3 holds** for all four
models (portfolio default + none is at least as feasible as the best single condition, with a better or equal median gap).

## N14e flexible job-shop re-scored (2026-10-16 14:20 UTC) against the reference re-run with a free CPU (14 / 40 proven optimal):
within 5%: Qwen3-32B scratch 0, adapt 1, snippet 0, adapt + snippet 8 / 80; gpt-oss-120b scratch 56, adapt 59, snippet **66**,
adapt + snippet 35 / 80. Verdicts unchanged (P2: no gain without the snippet holds; +15 with it refuted; the snippet alone is best for
gpt-oss-120b, adapting with it hurts).

## N15f pre-registration (2026-10-16 14:20 UTC, before computing; offline): a library fallback cascade
Run the default / free-choice program first; only if its plan is infeasible (or it crashes), run the next library in a fixed order
(synthetic: CP-SAT → MIP → no library; job-shop: no library); keep the first feasible plan. No reference used.
- N15f-P1 (synthetic, 4 models): ≥ 90% of the all-library portfolio's optimal share at ≤ 50% of its tokens.
- N15f-P2 (job-shop): the cascade default → no library has the portfolio default + none's feasibility at ≤ 70% of its tokens
  (its within-5% count may be lower: the cascade never compares objectives).

## N15f results (2026-10-16 14:20 UTC; results/n15f_analysis.log)
Synthetic, cascade free → CP-SAT → MIP → none (first feasible plan): Qwen3-32B 63.5% @ 1.6k (portfolio 64.5% @ 1.9k), gpt-oss-20b
82.0% @ 1.4k (84.5% @ 2.7k), Qwen3.6 76.0% @ 3.7k (78.5% @ 4.9k), gpt-oss-120b 91.0% @ 1.6k (94.5% @ 4.7k): 96–98% of the
portfolio's optimal share at 34–84% of its tokens. **N15f-P1: accuracy part holds for all four, token part (≤ 50%) only for
gpt-oss-120b.** Job-shop, cascade default → none: the same feasibility and within-5% counts as the portfolio default + none for every
model (28 / 73 / 79 / 80 feasible) at 1.0–1.1k vs 1.1–2.2k tokens; **N15f-P2 holds for three models (50–69% of the tokens), not for
Qwen3-32B (91%: its default fails almost always, so the fallback always runs).**

## Replication pre-registration (2026-10-16 14:21 UTC, before running): seed 3 for the positive claims of N15d and N14c
Positive claims need ≥ 3 seeds. Seed 3 of every N15 library condition (synthetic, 4 models) and of the job-shop + release-dates
scratch / adapt runs (4 models; Qwen3-32B also minimal edit). Claims are kept only if they hold with seed 3 included:
N15d-P2 (the all-library portfolio beats every single policy, each model), N14c (adapt verified > scratch in feasibility, each model).
poc/queue_s2_rep3.sh, GPUs 0–3.

## Seed-3 replication (2026-10-16 14:34 UTC; results/n15_analysis_s123.log, n15d_analysis_s123.log, n15_tokens_s123.log)
With seeds 1–3: free choice 40.7 / 72.0 / 55.0 / 81.7% (Qwen3-32B / gpt-oss-20b / Qwen3.6 / gpt-oss-120b); all-library portfolio
**66.0 / 84.7 / 78.3 / 93.3%**; best single library 50.0 (MIP) / 72.3 (MIP) / 60.3 (none) / 81.7 (free). **N15d-P2 replicated**
(the portfolio beats every single policy for every model); per-seed spread of single libraries ±3 points. Beyond accuracy (user,
14:3x: report tokens and everything): the libraries cost about the same output tokens (0.5–1.4k mean; plain Python is the most
expensive for the two strongest models, 1.8k vs 1.2k), cap hits are rare (≤ 5 of 300 per cell), and they fail in different ways:
library programs fail by crashing (Qwen3-32B CP-SAT: 154 of 175 failures are run-time errors) while plain-Python programs fail by
being feasible but suboptimal (Qwen3-32B: 142 of 229; gpt-oss-120b: 101 of 135). That complementarity is why the portfolio works.
Token logs only: these runs store no log-probs (run_co has no log-prob option); the confidence analysis C1 found log-probs no better
than one random sample for selection, so they were not collected here.
