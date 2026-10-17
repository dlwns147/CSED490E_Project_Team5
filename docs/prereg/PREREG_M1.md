# Pre-registration M1: a steering-score filter for offered helpers (our method)

Written 2026-10-14 00:44 UTC, before any data below. Results are appended below without editing this section.

**Problem.** Offered helpers can be needed (Delaunay without its in_circle helper: 2/120; lattice needs the area helper) or harmful
(hull with `polar_sort`: 97% → 8%). The model cannot tell which (self-scoping, scope sentence, S2A all failed, B3), and similarity labels
did not predict harm (PREREG_E4). Deployed systems do not know which helpers are needed.
**Method (label-free, before generating the final program).** (1) Draft: the model writes one program P0 with NO helpers (its default
approach). (2) For each offered helper h (with its dependencies), score shift(h) = mean token log-prob of P0 under the prompt with only h
offered minus under the bare prompt (teacher-forced prefill, no generation). A helper that pulls the model away from its default algorithm
lowers P0's likelihood. (3) Keep the helpers with shift(h) ≥ −τ (plus their dependencies) and generate the final program with them.
Cost: one extra generation (the draft) + (N + 1) prefill passes of a ≈ 300-token program. Related idea: context ablation for attribution
(ContextCite, 2024); here used as a pre-generation filter and checked against measured harm.
**Calibration (dev, fixed before test):** τ ∈ {0.005, 0.01, 0.02, 0.05} nats/token chosen by accuracy on dev instances (training-split
instances of hull, area2, close; 60), then frozen.
**Test:** Qwen3-8B, no thinking, `--stdlib`, T = 0.7, seeds 1–2, 60 instances per task: 5 core tasks (extras mostly harmful) + delaunay
(fixed `in_circle` needed) + lattice (non-negative area helper needed), each with the needed helpers + 8 related extras (K8).
Baselines on the same instances: all offered helpers (K8); no helpers (the draft itself); needed helpers only (oracle K0); model
self-scoping (it picks helpers from the catalog, `--autoscope`).
**Predictions.**
- M1-P1: on the core tasks, filter ≥ all-helpers + 8 points (pooled seeds).
- M1-P2: on delaunay + lattice, filter ≥ no-helpers + 30 points.
- M1-P3: pooled over all 7 tasks, filter within 5 points of the oracle needed-only toolbox, and above all-helpers, no-helpers and self-scoping.
- M1-P4: the needed helper is kept in ≥ 90% of delaunay / lattice instances; `polar_sort` is dropped in ≥ 70% of hull instances where it is offered.

Addendum (written 00:46 UTC, still before any data): if two τ values tie on dev accuracy, the larger τ (keeps more helpers) is chosen;
an instance whose draft has no extractable program keeps all offered helpers.


---
## Dev-stage result (appended 2026-10-14 00:49 UTC): the registered score does not separate harmful from needed helpers; the test phase was not run

Dev: 60 training-split instances (hull, area2, close), Qwen3-8B drafts written without helpers (54/60 correct), every offered helper scored
(`results/m1_scores_dev.json`).
- **The registered τ grid is degenerate:** every helper lowers the draft's likelihood (mean shifts −0.02 to −0.29 nats/token), so
  τ ≤ 0.05 keeps 0.00 / 0.02 / 0.17 / 0.93 of 8.9 offered helpers, i.e. "no helpers".
- **As a ranking, the score finds the known harmful hull helpers** (AUROC 0.92 for `polar_sort` + `collinear` vs the rest; close 0.70;
  area2 0.53, where no helper is harmful for 8B) **but ranks the needed helper about as low**: on hull, `orient` (needed) −0.112 sits between
  `collinear` −0.125 and `point_in_polygon` −0.084; on area2 it is the most negative (−0.259). Splitting the score into the first 30% and the
  last 70% of program tokens: almost all of the shift is early (imports and helper definitions) for every helper, needed or not, and the late
  shift does not separate them (hull: `polar_sort` −0.016, `orient` −0.008, `on_segment` −0.020).
- Reading: offering any helper changes how the model would *write* the program (naming, copying), and the draft's likelihood measures that
  change, not whether the *algorithm* changes. Any threshold that drops `polar_sort` also drops the needed helpers, which would fail the
  Delaunay / lattice part of the test by design (no-helper Delaunay: 2/120). Running the test would only confirm the failure, so it was not run.
- Also seen on dev: the model's one-sentence plan is not a usable proxy either: for hull the 8B *says* "Graham's scan" but *writes* the
  monotone chain, so plan likelihood rewards `polar_sort`.
