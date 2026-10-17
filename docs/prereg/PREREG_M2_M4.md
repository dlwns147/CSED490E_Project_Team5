# Pre-registration M2 / M3 / M4: three methods of our own for helper context, with baselines

Written 2026-10-14 01:06 UTC, before any model run below (the harness-side contract probe, which involves no model, was run once to build its
statements; its output is listed here). Results are appended below without editing this section.

**Shared setup.** Qwen3-8B and Qwen3-32B-AWQ, no thinking, `--stdlib`, T = 0.7, seeds 1–2, 60 instances per task. Groups: core = hull,
area2, pip, segs, close (the C1 K0 / K8 runs are the references); delaunay with the orientation-free `in_circle` as its needed helper;
lattice with the non-negative area helper as its needed helper. "K8" = needed helpers + 8 related extras, as in F1.
**Baselines on the same instances:** all offered helpers (K8); no helpers; needed helpers only (oracle K0); budget-forced thinking with
1,024 tokens on the K8 prompt (the best cheap baseline so far, E3).

**M4, algorithm first, tools second (our method).** The model writes its program WITHOUT helpers, then gets the K8 helpers and is asked to
rewrite its program to use them wherever one does exactly what a part of its program does, without changing the algorithm (2 calls).
- M4-P1: core: M4 ≥ K8 + 8 points for both models.  - M4-P2: delaunay + lattice: M4 ≥ no-helpers + 30 points for both models.
- M4-P3: pooled over the 7 tasks, M4 ≥ think-1,024 − 3 points at fewer output tokens per instance.

**M3, behavioural per-helper probe (Qwen3-8B only).** For each offered helper h, one program with only h; h is kept if that program is
consistent on the metamorphic copies of the given instance; then one final program with the kept helpers. Also reported: MR-select over
the no-helper draft and the per-helper programs (no extra generation).
- M3-P1: core: M3 ≥ K8 + 8.  - M3-P2: delaunay + lattice: M3 ≥ no-helpers + 30.  - M3-P3: M3 costs ≥ 3 × M4's tokens and is not
  better than M4 by more than 3 points pooled (the cheaper method is as good).

**M2, harness-side contract probing (no model).** Every offered helper with a scalar result is run on 200 random inputs and transformed
copies; a verified sentence is inserted when an orientation-reversing transform does not leave the result unchanged. Probe output (built
once): `orient`, `polygon_area2`, `in_circle` get "mirroring the input negates the result; swapping b and c (reversing the vertex order)
negates the result; translation and rotation leave it unchanged"; `segments_intersect` gets a statement that swapping b and c changes the
result (a generic argument swap that is not a symmetry of that helper; harmless here, as it is not offered in the M2 cells); all other
probed helpers are invariant; list-valued helpers are not probed. Cells: delaunay and lattice with only the needed helper in its terse
signed form + the probe sentence; references: terse (E2 for delaunay; new for lattice), hand-written warning (E2; new for lattice), fixed.
- M2-P1: delaunay: probe sentence ≥ hand-written warning − 10 points for both models (an automatic warning is as good as a human one).
- M2-P2 (uncertain): neither warning closes the gap to the fixed helper at 8B (probe sentence < 40% at 8B).

**Prior art (checked before running; agent opened the papers).** M2: DRAFT (2410.08197), Play2Prompt (2503.14432), ToolObserver
(2602.15197), DocsChisel (2608.10037) refine tool docs from model-chosen calls or trajectories; AutoMR / GenMorph (2312.15302) infer
metamorphic relations by execution but as test oracles, never as documentation for an LLM. Not pre-empted; limitation: our transformation
set (mirror, rotation, translation, argument swap / reversal) is geometry-specific. M3: closest is TroVE (2401.12869; sample programs per
toolbox *mode* and take the majority answer); GRETEL (2510.17843) trial-executes tools, Repoformer (2403.10059) self-judges context,
ContextCite (2409.00729) prunes by likelihood (our M1 failed with that family). M4: De-Hallucinator (2401.01701) and InlineCoder (2601.00376)
use a first draft to retrieve APIs and regenerate without a keep-the-algorithm constraint; ReGAL (2401.16467) refactors programs to use
helpers under an execution-equivalence check, for library learning. Background for F1: Jones & Steinhardt (2202.12299), Lou & Sun (2412.06593).
**Added baselines because of this check:** M4-free = De-Hallucinator-style draft → rewrite with the helpers *without* "do not change your
algorithm" (isolates that instruction); TroVE-style majority over modes (K8 samples + no-helper samples, seeds 1–2, computed offline).
- M4-P4: M4 ≥ M4-free + 5 points on the core tasks (the instruction matters).
- M3-P4: M3 ≥ the TroVE-style mode majority on the core tasks.


---
## Results (appended 2026-10-14 02:00 UTC; predictions above unedited)

`poc/analyze_mx.py`, `poc/analyze_mx_pf.py`, `poc/rescore_pf2.py`. Correct on all 8 variants; 2 seeds pooled; tokens = output tokens per
instance incl. drafts and probes. **Packaging-free** = a program that calls an offered helper without copying it is re-run with the helpers
pre-defined (our standard F1 scoring; deployable by shipping the helpers as a library). Qwen3-32B's M4 programs often call a helper in the
refactor without copying it (lattice: 68 crashes), so its as-measured numbers are much lower (pooled 69.8% as measured).

**Pooled over the 7 tasks (packaging-free):**

| method | Qwen3-8B | tokens | Qwen3-32B | tokens |
|---|---|---|---|---|
| all helpers (K8) | 78.9% | 883 | 79.4% | 524 |
| no helpers | 68.8% | 395 | 77.5% | 380 |
| needed helpers only (oracle) | 80.6% | 372 | 89.6% | 321 |
| think-1,024 on K8 | **94.5%** | 1,704 | 90.0% | 1,591 |
| **M4 algorithm first** | 89.0% | **951** | 85.2% | **824** |
| M4-free (no keep-the-algorithm sentence) | 88.2% | 1,010 | 85.7% | 822 |
| **M3 per-helper probe** | 80.0% | ≈ 6–10k | – | – |
| TroVE-style mode majority (2 K8 + 2 no-helper samples, majority on the given input; per instance) | 91.2% | ≈ 2,560 | **95.0%** | ≈ 1,810 |

Per group (8B / 32B, packaging-free): core K8 468 / 462, no helpers 554 / 508, M4 **579** / 513, think 569 / 545 (of 600); delaunay K8
105 / 115, no helpers 2 / 55, M4 105 / 103, think 120 / 116 (of 120); lattice K8 90 / 90, no helpers 22 / 88, M4 64 / 100, think 105 / 95.

- **M4-P1** confirmed for 8B (core 579 vs 468, +18.5) and, packaging-free, for 32B (513 vs 462, +8.5; as measured −1.0).
- **M4-P2** confirmed for 8B (delaunay +81.7, lattice +35.0) and 32B delaunay (+37.5); not for 32B lattice (as measured −39.2, packaging-free +10.0).
- **M4-P3 not confirmed:** pooled M4 is 5.5 (8B) and 4.8 (32B) points below think-1,024, at 56% and 52% of its tokens.
- **M4-P4 not confirmed:** without the "do not change your algorithm" sentence M4 does as well (88.2 vs 89.0; 85.7 vs 85.2). What
  helps is the *order* (writing the program before seeing the helpers), not the instruction.
- M4 failures read from the programs: on lattice the 8B refactors `polygon_area` into the offered `polygon_area2`, which returns *twice*
  the area, and forgets to halve; the 32B calls `polygon_area2` without copying it (packaging).
- **M3-P1 not confirmed** (core 485 vs 468): the per-helper programs written with `polar_sort` are mostly *consistent but wrong* (Graham-scan
  errors are invariant), so the probe keeps `polar_sort` in 58 of 92 hull instances: the same blind spot as E3. **M3-P2 confirmed**
  (delaunay 98 vs 2; lattice 89 vs 22). **M3-P3 confirmed** (it costs 6–10k tokens per instance and is 9 points below M4). **M3-P4 not
  confirmed:** the TroVE-style mode majority beats it (core 94.0% vs 80.8%). The no-extra-generation variant "MR-select over the draft and
  the per-helper programs" reaches 577/600 on core but 38/120 on delaunay.
- **M2-P1 not confirmed:** the automatic probe sentence does not help on delaunay (8B 0/120, 32B 10/120 vs the hand-written warning 18 / 80
  and the terse helper 1 / 3); on lattice it matches the warning for 32B (41 vs 38) but not for 8B (3 vs 42). A verified but generic
  relation ("mirroring negates the result") is not enough; the hand-written warning states the consequence ("valid only for counter-clockwise
  triangles; for clockwise ones the sign is reversed"). **M2-P2 confirmed** (8B stays far below 40%).
- **The strongest method in this comparison is published:** TroVE-style voting across contexts (programs written with and without the
  toolbox) fixes both failure types because their errors are uncorrelated: helper steering hurts the with-toolbox samples, missing helpers
  hurt the no-helper samples. On 32B it beats every method here (95.0% pooled at ≈ 1.8k tokens).
