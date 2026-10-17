# Pre-registration N14: reuse when a rule changes: adapt a verified program instead of writing from scratch

Written 2026-10-16 10:05 UTC, before any run. Results go below; this section is not edited afterwards.

**Why.** Verify-once-reuse needs identical rules; real routing / scheduling problems gain rules over time. Prior art (checked
2026-10-16): ARS (2502.15359) regenerates code per VRP variant; DRoC retrieves per constraint; constraint injection (2606.04816)
verifies a formulation's constraint set; one-solver-per-family papers (2605.14141, 2608.27296) assume a fixed family. Not found:
editing a solver that was already verified on the old problem when one rule is added.

**Design.** Rule ladder on our synthetic optimization problems (exact references): TSP → CVRP (add vehicles and capacity),
CVRP → VRPTW (add time windows). Models: Qwen3-32B-AWQ and Qwen3.6-35B-A3B (no thinking), T = 0.7, seeds 1–3, the full OR-Tools
reference sheet in the prompt (the N10 first-attempt condition, whose runs are the from-scratch baseline: doc_s1–s3).
Source programs (poc/n14_sources.py, from the same model's stored N10 programs, re-run on all instances of the source problem):
- verified related: the program optimal on the most source instances;
- failing related: a program of the same source problem that runs but is optimal on none (same description in the prompt);
- verified unrelated: the best knapsack program (CP-SAT usage, different problem).
The prompt appends: "Below is a Python program that solves a related problem (…). Use it as your starting point and adapt it."
Scoring as N10 (optimal; feasible reported), tokens = output tokens; input length reported (the source adds ≈ 1–2k tokens).
- N14-P1: the verified related source raises the optimal rate over from-scratch by ≥ 25 points for both models on both rungs
  (pooled over 3 seeds), at ≤ the from-scratch output tokens.
- N14-P2: the failing related source gives ≤ half of that gain (the source's correctness matters, not only its presence).
- N14-P3: the verified unrelated source gives ≤ half of that gain (relatedness matters, not only correct API usage).
- Reference, not a prediction: the exact task snippet arm (N10 snippet_s1).

Addendum 2026-10-16 10:30 UTC (before any N14 result): a third model, gpt-oss-20b low (16k cap; from-scratch baseline S2_N10m2_co_doc_s1–s3),
same design and predictions, poc/queue_s2_n14m2.sh on GPU 1. Source programs found (re-run on all source instances; good / bad):
Qwen3-32B TSP 15 / 16 optimal vs 0 (bad infeasible everywhere), CVRP 12 / 12 vs 0 (bad feasible on 12, never optimal), knapsack 16 / 16;
Qwen3.6 TSP 15 / 16 vs 0 (feasible 16), CVRP 12 / 12 vs 0, knapsack 16 / 16. No program is optimal on all 16 TSP instances, so the
"verified" TSP source is 94% correct.

## Results (2026-10-16 10:35 UTC; Qwen3-32B and Qwen3.6, seeds 1–3 pooled; results/n14_analysis.log)
| destination (optimal / feasible of all runs) | from scratch (sheet) | adapt verified related | adapt failing related | adapt verified unrelated | exact snippet (ref., seed 1) |
|---|---|---|---|---|---|
| Qwen3-32B CVRP (36) | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 5 / 7 of 12 |
| Qwen3-32B VRPTW (24) | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 2 / 3 of 8 |
| Qwen3.6 CVRP (36) | 2 / 2 | 0 / 0 | 0 / 0 | 0 / 0 | 10 / 10 of 12 |
| Qwen3.6 VRPTW (24) | 0 / 1 | 3 / 6 | 0 / 0 | 1 / 1 | 4 / 5 of 8 |
Output tokens are similar in every condition (0.9–2.3k). **N14-P1 refuted** (no gain except Qwen3.6 VRPTW, 3 vs 0, p = 0.25); P2 / P3
moot. Raw programs (a real negative, not a harness fault: the adapted programs visibly start from the source):
- The verified source carries only the facts it contains. TSP → CVRP: Qwen3.6 keeps the TSP's correct index manager in all 36
  adaptations but fails on the capacity call the TSP program never had (`AddDimensionWithVehicleCapacity` with an int, 5 of 12 in
  seed 1); Qwen3-32B invents the depot as a list (`[0] * K`).
- Adapting can break verified lines: Qwen3-32B's CVRP source calls `RoutingIndexManager(n + 1, K, 0)` (correct, 12 / 12 instances);
  7 of its 24 VRPTW adaptations change that line to `[0] * K` and crash; the new time-window rule brings invented calls
  (`GetDimensionName`, `AddDimensionWithVehicleT…`).
So a verified program is not a fact source for the NEW rule; the exact snippet of the new rule is (5–10 of 12 alone).

## N14b pre-registration (2026-10-16 10:35 UTC, before running): adapt the verified program AND give the new rule's exact snippet
Same ladder and sources (verified related only), the destination problem's exact snippet in place of the sheet (`--api_doc_task`),
Qwen3-32B and Qwen3.6, seeds 1–3; compared with the snippet alone (N10 snippet_s1 + new seeds 2–3).
- N14b-P1: adapt + snippet ≥ snippet alone + 10 points (pooled, each model), at ≤ its output tokens (the verified scaffold removes the
  input-parsing / indexing slips, the snippet supplies the new rule's API).
- N14b-P2 (descriptive): share of adaptations that change a verified API line of the source (index manager / capacity dimension).

## N14b results (2026-10-16 10:39 UTC; seeds 1–3; results/n14b_analysis.log)
| optimal (pooled) | adapt verified program + new rule's snippet | snippet alone | from scratch (sheet, N14) |
|---|---|---|---|
| Qwen3-32B VRPTW (from its CVRP program) | **18 / 24** (per seed 6 / 5 / 7) | 7 / 24 (2 / 2 / 3) | 0 / 24 |
| Qwen3.6 VRPTW (from its CVRP program) | 16 / 24 (5 / 6 / 5) | 12 / 24 (4 / 2 / 6) | 0 / 24 |
| Qwen3-32B CVRP (from its TSP program) | 9 / 36 | 12 / 36 | 0 / 36 |
| Qwen3.6 CVRP (from its TSP program) | 31 / 36 | 33 / 36 | 2 / 36 |
Paired (instance × seed): Qwen3-32B VRPTW 13 : 2, sign test p = 0.007; Qwen3.6 VRPTW 8 : 4, p = 0.39; CVRP 7 : 10 and 1 : 3 (n.s.).
Output tokens: 1.3k vs 1.1k (Qwen3-32B VRPTW), 2.3k vs 2.5k (Qwen3.6). **N14b-P1: holds for Qwen3-32B pooled (27 vs 19 of 60, +13
points), not for Qwen3.6 (47 vs 45, +3).** P2: with the snippet, Qwen3-32B keeps the source's verified index-manager line in 23 of 24
VRPTW adaptations (without the snippet it broke it in 7 of 24). Raw program (vrptw-8-2, seed 2): the source's reader, distance and
capacity code kept, a time callback, a 'Time' dimension and per-node windows added.
Reading: a verified program helps with a new rule when it already contains most of the machinery (CVRP → VRPTW: routing model,
capacity dimension, reader) and the new rule's API fact is given; from a much simpler source (TSP → CVRP) it does not help, and alone
(without the fact) it never helps. Claim limited to Qwen3-32B, one rung, 24 runs.

## N14c pre-registration (2026-10-16 10:41 UTC, before any run): the same question on a real benchmark rung
Job-shop la01–la40 (H5) → job-shop with RELEASE DATES (job j may not start before r_j; r_j uniform in 0 .. half of job j's processing
time, fixed seed; poc/run_jssp_rd.py; reference CP-SAT 8 workers 120 s). Feasibility is checked without the reference.
Models: gpt-oss-120b low (verified source = its H5 program feasible on the most of the 8 H5 training instances; failing source = an
H5 program infeasible on its own instance) and Qwen3-32B-AWQ no-think (H5 programs generated first, same picking rule). 40 instances ×
seeds 1–2 per condition: from scratch / adapt verified / adapt failing. No snippet is needed (CP-SAT job-shop needs none, H5).
- N14c-P1: Qwen3-32B: adapting the verified program ≥ from scratch + 10 points feasible (pooled, 80 runs), at ≤ its output tokens.
- N14c-P2: gpt-oss-120b: adapting ≥ from scratch (no loss), mean gap to the reference within 1 point of from-scratch's.
- N14c-P3: adapting the failing source ≤ from scratch for both models.
- Descriptive: share of adapted programs that keep the source's CP-SAT model (AddNoOverlap) and only add the release constraint.

## N14c results (2026-10-16 11:29 UTC; job-shop + release dates, la01–la40, seeds 1–2; results/h5/rd/n14c_analysis.log)
Reference: CP-SAT 120 s, 38 optimal, 2 feasible. Feasible plans (of 80) and median gap to the reference:
| model | from scratch | adapt verified job-shop program | adapt failing program |
|---|---|---|---|
| gpt-oss-120b low | 72 (gap 0.00%) @ 0.9k | **80** (0.00%) @ 0.8k | – (no failing source: every H5 program that ran was feasible) |
| Qwen3-32B no-think | 4 (gap 253%) @ 0.7k | **30** (0.00%) @ 0.9k | 0 @ 0.9k |
Paired: gpt-oss 8 : 0 (p = 0.008); Qwen3-32B 28 : 2 (p < 1e-6). **N14c-P1 holds** (+32 points, not at ≤ tokens: 0.9k vs 0.7k),
**P2 holds** (gpt-oss +10 points, same gap), **P3 holds** (failing source 0 / 80). All 80 gpt-oss and 66 / 80 Qwen3-32B adaptations keep
the source's `AddNoOverlap` model and add `start[j][0] >= r_j`. (Qwen3-32B's own H5 programs: 3 / 40 and 5 / 40 feasible per instance;
V1 picked one feasible on 8 / 8 training instances.)
Raw failures of the Qwen3-32B adaptations (50 / 80 crash): they rewrite lines the new rule does not touch: a list turned into a dict
(`'dict' object has no attribute 'append'`, 29), broken indentation (14), a new parser for the release line (4). The same pattern as
N14 (7 / 24 broken index-manager lines): the model edits verified code it should leave alone.
Reading across N14–N14c: a verified program transfers to a new rule when the new rule needs no API fact the program lacks (release
dates = one linear constraint; time windows only with their snippet); what remains is edit discipline.

## N14d pre-registration (2026-10-16 11:29 UTC, before running / computing)
(a) Minimal-edit instruction: the same adaptation prompt plus "Change as few lines as possible: keep every line unrelated to the new
rule exactly as it is." Qwen3-32B, job-shop + release dates (seeds 1–2) and CVRP → VRPTW with the snippet (seeds 1–3).
(b) Verify the adaptation once and reuse it (offline, existing N14c programs): candidates = the adapted programs written for the 8
H5 training instances (2 seeds → 16); keep the one feasible on the most training instances (ties: lower mean makespan / reference);
run it unchanged on the 32 others. Same for from-scratch candidates.
- N14d-P1: minimal edit raises Qwen3-32B job-shop feasibility from 30 / 80 to ≥ 45 / 80 and VRPTW optimal from 18 / 24 to ≥ 20 / 24.
- N14d-P2: verified-once adapted program feasible on ≥ 31 / 32 held-out instances for both models; from-scratch candidates for
  Qwen3-32B ≤ 50% (at most 1–2 of its 16 candidates work anywhere).

## N14 third model (2026-10-16 11:29 UTC): gpt-oss-20b low, seeds 1–3 (results/n14_analysis.log)
CVRP from its TSP program: 13 / 36 optimal vs 24 / 36 from scratch (paired 5 : 16, p = 0.027; 17 crashes `Assignment_Value returned
NULL`: the adapted program reads a solution the solver never found); unrelated knapsack source 17 / 36. VRPTW from its CVRP program
(no snippet): 4 / 24 vs 2 / 24 (n.s.). A distant source hurts a model that can already write the target (as unneeded helpers do, M1).

## N14c addendum pre-registration (2026-10-16 11:29 UTC, before running): two more models on the job-shop rung
gpt-oss-20b low (sources from its H5 programs oss20_low_plain) on GPU 1 and Qwen3.6-35B-A3B no-think (H5 programs generated first)
on GPU 0; seeds 1–2; from scratch vs adapt verified (vs failing when one exists). Prediction: adapt ≥ from scratch for both
(N14c-P1/P2 extended); poc/queue_s2_n14c2.sh.

## N14e pre-registration (2026-10-16 11:31 UTC, before implementation or runs): test the transfer rule on two new job-shop rungs
Rule read from N14–N14c: a verified program transfers to a new rule when the rule needs no API fact the program lacks.
Rungs from the verified H5 job-shop program: (i) due dates with total-tardiness objective (needs only linear max / sums; no new API);
(ii) flexible job-shop: each operation may run on one of 2 machines (needs optional intervals, a new CP-SAT fact). Qwen3-32B and
gpt-oss-120b, from scratch vs adapt verified, seeds 1–2, la01–la40-based instances, CP-SAT references.
- N14e-P1: (i) adapt ≥ scratch + 15 points feasible-and-within-5%-of-reference for Qwen3-32B; gpt-oss-120b no loss.
- N14e-P2: (ii) adapt without the optional-interval snippet ≤ scratch + 5 points for Qwen3-32B; with the snippet ≥ scratch + 15.

## N14d results, part 1 (2026-10-16 11:35 UTC)
(a) Minimal-edit instruction, Qwen3-32B: job-shop + release dates **54 / 80 feasible vs 30 / 80** with the plain adaptation prompt
(paired 35 : 11, p = 0.0005; 0.8k vs 0.9k tokens; the `dict.append` rewrites disappear, 10 indentation and 9 syntax errors remain);
CVRP → VRPTW with the snippet 17 / 24 optimal vs 18 / 24 (no change, 1.2k tokens). **N14d-P1: holds for job-shop, refuted for VRPTW**
(there the plain adaptation already kept the verified lines, 23 / 24, so there was little to gain).
(b) Verify once, reuse the adaptation: gpt-oss-120b: all 16 adapted candidates are feasible somewhere; the pick (8 / 8 training) is
feasible on 32 / 32 held-out instances with 0.00% median and max gap, 13k generation tokens in total. Qwen3-32B and from-scratch
candidates: still computing (results/h5/rd/n14d_reuse.log).

N14e addendum (2026-10-16 11:36 UTC, before any N14e run): since N14d, the adapt arm uses the minimal-edit instruction. Arms per
model (Qwen3-32B on GPU 2, gpt-oss-120b low on GPU 3), seeds 1–2, 40 instances: tard: scratch, adapt; flex: scratch, adapt,
scratch + optional-interval snippet, adapt + snippet. Predictions unchanged (P1 for tard, P2 for flex). poc/queue_s2_n14e.sh.

## N14d part 2 + N14c addendum + N14e results (2026-10-16 12:30 UTC; results/h5/n14ce_analysis.log, results/h5/rd/n14d_reuse.log)
**N14d (b), verify the adaptation once and reuse it (job-shop + release dates):** Qwen3-32B: 9 of its 16 adapted candidates work
somewhere; the pick (8 / 8 training) is feasible on **32 / 32 held-out instances** (median gap 0.00%, max 1.38%) for 15k tokens in
total; its from-scratch candidates: none works on any training instance, so reuse is impossible. gpt-oss-120b: 32 / 32 from either
pool. **N14d-P2 holds.**
**N14c on two more models (feasible of 80, seeds 1–2):** gpt-oss-20b scratch 61, adapt verified **80** (19 : 0, p < 1e-5), adapt
"failing" 78 (that source only printed the wrong shape; the model fixed it); Qwen3.6 scratch 59, adapt verified **80** (21 : 0,
p < 1e-6), adapt failing (a crashing program) 0. Gaps 0.0% median throughout. Across four models adapting the verified program gives
80, 80, 80 / 80 and 30 → 54 / 80 (Qwen3-32B with minimal edit).
**N14e (gaps pending: the CPU-loaded references were weak, 27 / 40 tardiness and 31 / 40 flexible not proven optimal; re-running):**
| feasible of 80 (within 5% of the current reference) | scratch | adapt (minimal edit) | snippet | adapt + snippet |
|---|---|---|---|---|
| tardiness, Qwen3-32B | 2 (0) | **18 (12)**, 18 : 2, p = 0.0004 | – | – |
| tardiness, gpt-oss-120b | 76 (58) | 80 (55) | – | – |
| flexible, Qwen3-32B | 0 | 3 (1) | 1 (0) | 9 (8), p = 0.004 |
| flexible, gpt-oss-120b | 67 (57) | 61 (60) | **76 (69)**, 12 : 3, p = 0.035 | 36 (36), 7 : 38, p < 1e-5 |
Raw failures: tardiness adaptations of Qwen3-32B crash on invented reification (`Constraint … has no attribute 'BoolVar'`, 20 of
62), i.e. the model reaches for an API it does not know although `T_j ≥ C_j − d_j, T_j ≥ 0` needs none; gpt-oss-120b's flexible
adaptations with the snippet invent variable look-ups (`GetBoolVarFromName`, `GetBoolVar`, … 29 of 39 crashes) to retrofit
optional intervals into the existing model, while the snippet without a source works best.
Provisional verdict: **N14e-P1 holds for Qwen3-32B (+15 points within 5%) and is unclear for gpt-oss-120b (−3 within 5% on a weak
reference)**; **N14e-P2: the "no gain without the snippet" part holds (3 vs 0 / 80), the "+15 with the snippet" part is refuted (+10)**,
and for gpt-oss-120b the snippet alone beats adapting with it. The transfer rule needs a refinement: adapting helps a model that
cannot write the problem (Qwen3-32B: 0–4 / 80 from scratch) on every rung; for a model that can, it helps only when the change is
local (release dates) and hurts when the change restructures the model (alternative machines).

## N14e tardiness re-scored (2026-10-16 12:49 UTC) against the reference re-run with a free CPU (14 / 40 proven optimal, 26 feasible;
tardiness is hard for CP-SAT in 120 s): within 5% (or + 5 time units) of the reference: Qwen3-32B scratch 0 / 80, adapt **14 / 80**;
gpt-oss-120b scratch 48 / 80, adapt 44 / 80 (feasible 76 vs 80). **N14e-P1 holds for Qwen3-32B (+17.5 points); "no loss" for
gpt-oss-120b is refuted by 4 items** (more feasible plans, slightly worse objective). Flexible-job-shop reference re-run still running.

## N14c seed-3 replication (2026-10-16 14:34 UTC; results/h5/rd/n14c_3seeds.log)
Feasible of 120 (per seed), median gap, output tokens mean / p90:
| model | from scratch | adapt verified | adapt + minimal edit |
|---|---|---|---|
| Qwen3-32B | 12 (4 / 0 / 8), gap 409%, 674 / 771 | 50 (11 / 19 / 20), gap 0.00%, 914 / 1000 | **82** (29 / 25 / 28), 0.00%, 806 / 873 |
| Qwen3.6 | 83 (26 / 33 / 24), 984 / 1132 | **120** (40 / 40 / 40), 816 / 822 | – |
| gpt-oss-20b | 92 (30 / 31 / 31), 891 / 1059 | **120**, 814 / 865 | – |
| gpt-oss-120b | 103 (36 / 36 / 31), 927 / 1096 | **120**, 824 / 862 | – |
Paired good vs scratch: 46 : 8, 37 : 0, 28 : 0, 17 : 0 (all p < 1e-4). **N14c replicated on every seed for all four models.** Adapted
programs are also cheaper and more uniform in length (p90 0.82–0.86k vs 1.06–1.13k tokens for the three strong models). No cap hits.

N14b addendum (2026-10-16 14:45 UTC, before running): gpt-oss-20b low, VRPTW from its verified CVRP program + the time-window snippet
vs the snippet alone, seeds 1–3, with the minimal-edit sentence (as N14d), poc/queue_s2_n14b2.sh on GPU 0. Prediction: adapt +
snippet ≥ snippet alone (N10m2 snippet_s1 VRPTW 7 / 8; new seeds 2–3).

## N14b addendum result (2026-10-16 15:28 UTC; results/n14b2_analysis.log)
gpt-oss-20b VRPTW: adapt verified CVRP program + snippet + minimal edit **21 / 24** optimal (7 / 7 / 7 per seed) at 1.07k output tokens
(p90 1.22k) vs the snippet alone 18 / 24 (7 / 5 / 6) at 1.19k (p90 1.35k); paired 5 : 2 (n.s.); no cap hits; the 3 failures are crashes.
Prediction (≥) holds. Across three models the CVRP → VRPTW rung with the snippet: adapt 18 / 16 / 21 vs snippet alone 7 / 12 / 18 of 24
(only Qwen3-32B significant), always at equal or fewer output tokens.
