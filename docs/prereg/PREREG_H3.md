# Pre-registration H3: standard optimisation benchmark — the 56 Solomon VRPTW instances (100 customers)

Written 2026-10-14 06:48 UTC, before any LLM run below (the non-LLM references were run first to calibrate the harness). Results are appended
below without editing this section.

**Why.** Our optimisation tasks had ≤ 16 customers. The user asked whether the problems are too easy; this is the standard hard set
(SINTEF best-known table, 56 instances; harness poc/run_solomon.py). Related work runs LLM-written routing solvers on VRP benchmarks
(DRoC; ARS 2502.15359; AFL 2510.16701; HeuriGym 2506.07972); none asks which cheap fix (API facts vs reasoning) pays at this scale.

**Task.** The instance file is given verbatim on stdin; the model writes a Python program (OR-Tools available, 60 s) that prints routes.
The statement says explicitly: unrounded Euclidean travel times, waiting allowed, service start ≤ due date, return by the depot's due
date, at most K vehicles, minimise total distance, exact real-valued checking. Checker: run_solomon.check (verified: our OR-Tools reference
reproduces 828.94 on c101/c102/c105–c108, the best-known values).
**Reference distance** per instance = min(best-known distance (vehicles-first, so not always distance-minimal), our OR-Tools 300 s with
cheapest insertion + guided local search). Gap = distance / reference − 1.
**Calibration (non-LLM, already run).** Nearest-feasible greedy: 56 / 56 feasible, mean +47.6% vs best-known. OR-Tools 30 s with the
documentation's first-solution strategy (PATH_CHEAPEST_ARC): 49 / 56 — on 7 tight-window instances (r101–r103, r105, r106, rc101, rc105)
it finds no first solution and the program crashes on `sol = None`; with PARALLEL_CHEAPEST_INSERTION all 7 are solved. This is an API
fact a correct-looking documentation snippet does not carry.

**Conditions** (2 seeds each, 56 instances): Qwen3-32B-AWQ no-think; gpt-oss-20b low; gpt-oss-120b low; gpt-oss-120b medium; × three arms:
plain; + documentation snippet (correct OR-Tools VRPTW usage incl. integer scaling, PATH_CHEAPEST_ARC); + robust snippet (the same with
cheapest insertion and a None check). Reported: feasible rate, mean gap (feasible only) and "within 5% of the reference" rate (infeasible =
not within), output tokens, program wall time.

**Predictions.**
- H3-P1 (difficulty): plain arm feasible rate ≤ 50% for Qwen3-32B no-think and ≥ 70% for gpt-oss-120b medium.
- H3-P2 (which fact): the documentation snippet raises Qwen3-32B's feasible rate by ≥ 15 points; the robust snippet beats the documentation
  snippet by ≥ 8 points pooled over the four models, concentrated on the 7 tight-window instances.
- H3-P3 (cost): Qwen3-32B no-think + robust snippet is within 10 points of gpt-oss-120b medium plain on "within 5%" at ≤ 1/3 of its tokens.
- H3-P4 (quality): feasible programs that use OR-Tools routing with a metaheuristic have mean gap ≤ 5%; hand-written heuristics ≥ 10%.
- H3-P5 (failure mode): in the plain arm, ≥ 30% of infeasible results are time-window or depot violations under exact checking
  (rounding / truncating real distances, or service time left out), not crashes or timeouts.

## Amendment (2026-10-14 08:20 UTC, after the first Qwen runs and before any other H3 run; predictions unchanged)

Qwen3-32B no-think was feasible on 0 / 56 in all three arms (5 runs). Raw programs and re-run errors: nearly all are input-parsing crashes
(`int('NUMBER')`, `int('CAPACITY')`, `int('R105')`, index errors after blank lines): the statement described the Solomon file
format in words but did not show it, and the file has multi-word header lines, blank lines and CRLF endings. This is our harness, as in the
earlier VRPTW header case (F3y), not the solver question the arms test. Fix: stdin is normalised to LF and the prompt shows the first 12
lines of the instance verbatim. The words-only runs are kept as an extra arm (results/h3/sol_noex_*), plus words-only plain for gpt-oss-120b
medium. All arms are re-run with the example.

## Interim results with the example (2026-10-14 09:31 UTC; Qwen3-32B no-think and gpt-oss-20b low finished; feasible of 112 = 56 × 2 seeds)

| model | plain | + documentation snippet | + robust snippet | output tokens |
|---|---|---|---|---|
| Qwen3-32B no-think | 0 | 1 | 1 | 1.4–1.8k |
| gpt-oss-20b low | 0 | 18 | 17 | 1.6–1.7k |

Re-running the crashed programs: about half crash while reading the file even with the verbatim example (`int('NUMBER')` on the
header "NUMBER CAPACITY", `int('CUST')` on the column header, which has 11 tokens and slips through a `len(parts) < 7` guard), the rest
on invented OR-Tools methods, solver failures (`CP Solver fail`, `sol` None) and index errors. So far: H3-P1 holds for Qwen (0%);
H3-P2 refuted for Qwen (+1 of 112, not +15 points) and the robust snippet does not beat the documentation snippet; H3-P5 refuted (nearly
every infeasible result is a crash, not a window violation). The solver question is hidden behind reading the file.

## H3b pre-registration (2026-10-14 09:31 UTC, before any run): the format fact

New arm: a correct 8-line reader for the file in the prompt (`--parser`; verified to match the checker's parse on all 56 instances),
alone and with each snippet: parser, parser + documentation snippet, parser + robust snippet; 2 seeds; Qwen3-32B no-think, gpt-oss-20b
low, and (with the original three arms and words-only plain) gpt-oss-120b low and medium.
- H3b-P1: the reader alone raises feasibility more than either solver snippet alone: Qwen3-32B ≥ 30% (from 0%), gpt-oss-20b low ≥ 40%.
- H3b-P2: with the reader in place, the robust snippet beats the documentation snippet by ≥ 8 points pooled (the 7 tight-window instances).
- H3b-P3: parser + robust snippet is the best arm for every model, at the same output tokens (the fix costs ≈ 150 prompt tokens).
- H3b-P4: gpt-oss-120b medium plain (with the example) ≥ 50% feasible; its words-only plain run ≥ 30%.

## H3b results so far (2026-10-14 10:40 UTC; feasible of 56 per seed, s1 / s2; output tokens ≈ 1.1–1.8k low effort, 2.5–3.5k medium)

| model | plain | docs | robust | reader | reader + docs | reader + robust |
|---|---|---|---|---|---|---|
| Qwen3-32B no-think | 0 / 0 | 0 / 1 | 1 / 0 | 0 / 0 | 3 / 2 | 1 / 2 |
| gpt-oss-20b low | 0 / 0 | 10 / 8 | 11 / 6 | 1 / 1 | 13 / 15 | **24 / 25** |
| gpt-oss-120b low | 6 / 1 | 21 / 18 | 17 / – | 7 / 13 | (running) | **56 / 56** |
| gpt-oss-120b medium | 26 / (running) | (running) | (running) | 45 / 39 | (running) | **56 / 55** |

- With both facts (reader + robust snippet) gpt-oss-120b is feasible on every instance at low effort (median gap 1.5%; 46–49 of 56
  within 5% of the reference; 1.5k tokens), and on all 7 tight-window instances, which no other arm solves (0–1 of 7) except gpt-oss-20b
  with the same two facts (3 / 5 of 7). The documentation snippet is never enough for the tight windows: the robust fact is the one that
  matters there (H3b-P2 holds where the reader is present: 20b +11 / +10, 120b low: reader + docs pending).
- **The reader we supplied is itself a trap (F2 at benchmark scale).** Re-running the reader-only programs: gpt-oss-120b low crashes in
  27 of 40 cases on `AddDimension(..., argument 3 of type 'int64_t')`: our reader returns floats (`due[0]` as slack), OR-Tools needs
  integers. The robust snippet says to scale to integers, which is why the two facts together work and the reader alone barely helps for low
  effort (medium effort converts: 45 / 39). H3b-P1 (reader alone ≥ 40% for gpt-oss-20b) refuted for this reason; a reader returning
  integers is pre-registered below to separate the format fact from the float contract.
- Qwen3-32B stays at 0–3 of 56 in every arm: it rewrites the snippet's calls into signatures that do not exist (`RoutingIndexManager(n + 1,
  K, [0] * K)`, 33 of 45 crashes with the reader + robust snippet), i.e. it does not copy the exact API fact it is given.

## H3c pre-registration (2026-10-14 10:40 UTC, before any run): integer reader
Arm `--parser_int`: the same reader returning integers for every column (all Solomon values are integers; verified below), alone and
with the robust snippet; 2 seeds; all four models.
- H3c-P1: integer reader alone ≥ 30 / 56 for gpt-oss-120b low (float reader: 7 / 13) and ≥ 10 / 56 for gpt-oss-20b low (1 / 1).
- H3c-P2: integer reader + robust snippet ≥ float reader + robust snippet − 2 for every model (the scaling instruction already handles floats).
- H3c-P3: Qwen3-32B ≤ 5 / 56 in both arms (its failure is invented signatures, not the format).
(H3c runs: Qwen3-32B on 8040, gpt-oss-20b on 8042, gpt-oss-120b low/medium on a second 120b server on GPU 1 (8044); queue poc/queues/queue_s2_h3c.sh.)

## H3c results (2026-10-14 11:33 UTC; feasible of 56, s1 / s2; gpt-oss-120b medium integer reader + robust still running)

| model | float reader | integer reader | float reader + robust | integer reader + robust | reader + docs (float) |
|---|---|---|---|---|---|
| Qwen3-32B no-think | 0 / 0 | 0 / 0 | 1 / 2 | 2 / 1 | 3 / 2 |
| gpt-oss-20b low | 1 / 1 | 1 / 1 | 24 / 25 | **36 / 32** | 13 / 15 |
| gpt-oss-120b low | 7 / 13 | 14 / 10 | 56 / 56 | 56 / 56 | 49 / 48 |
| gpt-oss-120b medium | 45 / 39 | 37 / 39 | 56 / 55 | (running) | (running) |

- **H3c-P1 refuted:** the integer reader alone barely helps (120b low 14 / 10, 20b 1 / 1). Re-running the crashes: the models now write
  their own floats into OR-Tools (`AddDimension(cb, 1e7, max(due), ...)`, `horizon = max(due) + 1e3`), 20 of 29 crashes for 120b low.
  So my earlier diagnosis (the reader's floats) was only part of it: the missing fact is "OR-Tools takes integers everywhere", which both
  snippets state ("callbacks must return integers: scale ...") and the reader does not.
- **H3c-P2 confirmed** (integer + robust ≥ float + robust − 2): 120b equal (56 / 56), 20b +10 (36 / 32 vs 24 / 25): for the smaller model the
  reader's float contract did cost about ten instances. **H3c-P3 confirmed** (Qwen ≤ 5).
- Overall H3 reading: three facts compose, none suffices alone: the file layout (reader), integers everywhere (in either snippet), and a
  first-solution strategy that works with tight windows (robust snippet; docs + reader reaches 48–49 but never the 7 tight instances).

## H3b / H3c complete (2026-10-14 12:29 UTC)
gpt-oss-120b medium: plain (example shown) 26 / 28, words only 6 / 2, docs 34 / 35, robust 39 / 36, float reader 45 / 39, integer reader
37 / 39, reader + docs 48 / 49, float reader + robust 56 / 55, integer reader + robust 55 / 56. gpt-oss-120b low reader + docs 49 / 48.
H3b-P4: plain with the example 46–50% (≥ 50% narrowly missed), words only 5–11% (≥ 30% refuted): showing the file layout is itself
worth ≈ 20 instances for the strongest model.
