# Pre-registration N16: do the model's own token probabilities flag invented solver API calls, and is that a better trigger for
# documentation than running the program?

Written 2026-10-16 14:36 UTC, before any run. Results go below; this section is not edited afterwards.

**Why.** The user asked that analyses look at tokens and log-probs, not only accuracy. The largest failure class in solver code is
invented API calls (R1 / F3: e.g. `RegisterUnaryLongLivingCallback`). If the model is unsure exactly at those tokens, documentation
could be added only when needed, before running anything. Prior art: FLARE (active retrieval on low-confidence tokens, text QA);
API-hallucination work for code (De-Hallucinator; CloudAPIBench-style studies); our C1 found sequence-level confidence useless for
selecting programs. New here: token-level confidence at the API names, against execution as the trigger, priced in tokens.

**Design.** The 8 synthetic optimization problems (100 items), no documentation, project default library sentence, T = 0.7,
seeds 1–3, `run_co.py --logprobs` (raw log-probs of the first program's tokens). Fix arm: the exact task snippet (`--api_doc
--api_doc_task`), seeds 1–3. Models: Qwen3-32B-AWQ (GPU 0), Qwen3.6-35B-A3B (GPU 1), Qwen3-8B (GPU 2), all no-think.
Offline: every attribute call `x.Name(` in a program is labelled *invented* if Name is not an OR-Tools API name (poc/analyze_e1_
taxonomy.ortools_vocab) and not defined in the program, else *real*; its score = the minimum log-prob over the tokens that spell Name.
- N16-P1: invented API names have lower min log-prob than real ones: AUROC ≥ 0.75 per model (pooled over problems and seeds).
- N16-P2: confidence-triggered documentation (regenerate with the snippet when a program's lowest API-name log-prob is below a
  threshold chosen on the other problems) reaches ≥ 90% of always-snippet's optimal share while triggering on ≤ 60% of items.
- N16-P3: execution-triggered documentation (run the first program; regenerate with the snippet only if it crashes or prints an
  infeasible plan) is at least as accurate as the confidence trigger at no more tokens.

## Results (2026-10-16 14:45 UTC; seeds 1–3, 300 items per model; results/n16_analysis.log)
Analysis bug found and fixed before any reading: the first API vocabulary (class `dir()` only) labelled real calls such as
`CpModel.NewIntVar` and `cp_model.CpModel` as invented (AUROC ≈ 0.6); the vocabulary is now built from live OR-Tools objects.
| | Qwen3-32B | Qwen3.6 | Qwen3-8B |
|---|---|---|---|
| API-name calls real / invented | 3,817 / 231 | 4,094 / 42 | 2,935 / 460 |
| most invented | `RegisterUnaryLongLivingCallback` 60, `OnlyIf` 47 | `DefaultSearchParameters` 11 | `RegisterNodeCallback` 32 |
| min log-prob at the name, median invented / real | −0.14 / −0.00 | −0.32 / −0.00 | −0.71 / −0.00 |
| **AUROC (invented lower)** | **0.84** | **0.86** | **0.90** |
| first program (no docs): optimal @ output tokens | 42.0% @ 0.54k | 52.3% @ 0.95k | 13.0% @ 0.48k |
| always the exact snippet | **76.7% @ 0.47k** | **92.0% @ 0.66k** | **42.0% @ 0.49k** |
| execution trigger (snippet only if it crashes / is infeasible) | 74.7% @ 0.88k (167 regenerations) | 92.0% @ 1.38k (140) | 37.0% @ 0.90k (242) |
| confidence trigger (threshold from the other problems) | 76.3% @ 0.95k (245) | 92.0% @ 1.60k (292) | 42.0% @ 0.96k (300) |
| oracle trigger | 77.0% | 93.0% | 42.7% |
**N16-P1 holds** (the model's own log-probs flag invented API names, AUROC 0.84–0.90). **N16-P2 refuted**: the confidence trigger
matches always-snippet accuracy only by firing on 82–100% of programs (every program has some uncertain API token).
**N16-P3 mostly refuted**: the execution trigger fires less (47–81%) but loses 2–5 points for two models.
The decisive number is the token cost: **the snippet makes programs shorter** (0.47 vs 0.54k, 0.66 vs 0.95k output tokens; it adds
≈ 200 input tokens), so giving the exact fact up front is both the most accurate and the cheapest policy; any trigger pays for a
second generation. Log-probs are a good *diagnostic* of invented API calls, not a useful trigger when the fact is cheap to give.

## N16b pre-registration (2026-10-16 15:28 UTC, before computing; offline on the stored C1 geometry runs with log-probs)
Contrast with N16-P1: are calls to UNNEEDED helpers (the F1 / M1 steering) uncertain at the helper name, like invented API names?
Data: Qwen3-8B and Qwen3-32B, K8 toolbox (needed helpers + 8 related distractors), main 5 tasks, seeds 1–3 (S2_C1_*_dis8_*,
raw log-probs of every token). Score of a helper call = min log-prob over the tokens spelling the helper name at its first call.
- N16b-P1: distractor-helper calls are NOT less confident than needed-helper calls (AUROC "distractor lower" ≤ 0.60): steering is a
  confident choice, unlike an invented API name (0.84–0.90).
- N16b-P2: within distractor calls, calls in wrong programs are not less confident than in correct ones (AUROC ≤ 0.60).

## N16b results (2026-10-16 15:30 UTC; results/n16b_analysis.log; 900 programs per model)
Analysis fix before reading: the first version counted the model's own functions as "needed helpers"; restricted to the toolbox's
needed helpers (NEED + dependencies).
| | Qwen3-8B | Qwen3-32B |
|---|---|---|
| first calls of needed helpers / of unneeded (distractor) helpers | 372 / 48 | 360 / 143 |
| min log-prob at the helper name, median needed / distractor | −0.000 / 0.000 | −0.000 / 0.000 |
| AUROC (distractor lower) | **0.21** | **0.06** |
| distractor calls in wrong vs correct programs (n) | 8 / 40, AUROC (wrong lower) 0.99 | 11 / 132, AUROC 0.62 |
**N16b-P1 holds:** calls to unneeded helpers are at least as confident as calls to needed ones (more so for Qwen3-32B): steering by
offered helpers is a confident choice, the opposite of invented API names (AUROC 0.84–0.90). **N16b-P2 refuted for Qwen3-8B (0.99,
but only 8 wrong-program calls) and borderline for Qwen3-32B (0.62 > 0.60, 11 calls)**: too few wrong distractor calls to conclude.
Most distractor calls are harmless (e.g. `dist2` in closest pair, 38 of 143 for Qwen3-32B); the harmful ones (hull on `polar_sort`)
are few per seed. Reading: log-probs separate "the model does not know this name" (invented API) from "the model chose a tool it was
given" (steering, confident); only the first is visible in the logits.
