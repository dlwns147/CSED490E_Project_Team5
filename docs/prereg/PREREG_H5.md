# Pre-registration H5: a second optimisation benchmark with another solver library — job-shop scheduling (la01–la40) with CP-SAT

Written 2026-10-14 14:32 UTC, before any LLM run. Results are appended below without editing this section.

**Why.** Every optimisation result so far (F3, H3, FM) uses the OR-Tools routing library. A method or finding about "facts" must hold
for another library and problem. Job-shop (Lawrence la01–la40: 10×5 to 30×10 and 15×15, OR-Library) is the textbook CP-SAT example.
**Task.** Standard format on stdin (n m, then per job m pairs "machine duration"), explicit rules, output = start times per job; 60 s;
OR-Tools available. Checker: job order, machine overlap, non-negative integers. Reference = our CP-SAT, 8 workers, 120 s.
**Conditions.** gpt-oss-120b low (new server on GPU 0) and gpt-oss-20b low, 2 seeds, no facts.
- H5-P1: gpt-oss-120b low feasible ≥ 80% with mean gap ≤ 5% (textbook API, simple format).
- H5-P2: gpt-oss-20b low feasible ≥ 60%.
- H5-P3: if 120b is ≥ 80% feasible, the remaining loss is search quality: ≥ 30% of its feasible programs leave CP-SAT at one worker or set
  no time limit (read from the code), and those have larger gaps. FM2 is run on H5 only if a model is below 70% feasible.

## Results (2026-10-14 15:40 UTC; after the CPU-limit fix, see FINDINGS; feasible of 40, seed 1 / seed 2)

| model | feasible (before fix → after) | mean gap to our CP-SAT reference (feasible) | output tokens |
|---|---|---|---|
| gpt-oss-120b low | 30 / 29 → **35 / 33 (85%)** | 0.03–0.04% (max 1.4%) | 0.9–1.0k |
| gpt-oss-20b low | 28 / 28 → **31 / 32 (79%)** | 0.00% | 0.8–1.2k |
Reference: CP-SAT 120 s, 8 workers: optimal on 39 of 40 (la29 feasible 1157).
- **H5-P1 holds** (≥ 80%, gap ≤ 5%) and **H5-P2 holds** (≥ 60%). **H5-P3 refuted:** every program sets a time limit (40 / 40) and the
  rest leave the default (parallel) workers; search quality is not the problem: feasible programs are optimal or within 1.4%.
- Remaining failures (read): invented CP-SAT attributes (`cp_model.thread_count()`, `cp_model.thread_pool_size()`, wrong
  `new_interval_var` arguments) and, for 20b, wrong models (machine overlaps, 4–5 per seed). As pre-registered, FM is not run here
  (both models ≥ 70%): job-shop with CP-SAT is the textbook case these models know; the facts problem of H3 is specific to the less
  common routing API and the benchmark's file format.
