# Pre-registration: E4 helper-similarity test (review item 8)

Written 2026-10-12 12:26 UTC, BEFORE any run of this design. Results will be appended below without editing this section.

**Hypothesis (off-idiom drift):** an unneeded helper hurts in proportion to how strongly it suggests an alternative *algorithm* for the task,
not in proportion to prompt length or to being geometry code.

**Design.** Qwen3-8B and Qwen3-32B-AWQ, no thinking, "should use" header with the needed helpers always given, T=0.7, seeds 1 and 2,
tasks hull / area2 / close, n_inst 30 × 2 sizes (60 programs per task per seed). Exactly 2 extra helpers (plus their dependencies), chosen a priori:

| task | HIGH (suggests another algorithm) | LOW (related geometry, not suggestive) |
|---|---|---|
| hull | polar_sort, collinear (Graham scan, explicit collinear removal) | segments_intersect, point_in_polygon |
| area2 | convex_hull, is_convex (hull-area / convexity detour) | closest_pair_sq, segments_intersect |
| close | dist2, bbox (grid / divide-and-conquer bucketing) | polygon_area2, is_convex |

Baseline: K=0 (same seeds). Primary metric: programs correct on all 8 variants. Paired by instance.

**Predictions (registered):**
- P1: HIGH harm > LOW harm on hull and area2 for both models (pooled over seeds, paired difference < 0).
- P2: LOW harm is small (|Δ| ≤ 5 points vs K=0) on every task for 32B.
- P3: in HIGH, the algorithm switch is visible: hull programs using polar_sort ≥ 25%; area2 programs calling convex_hull ≥ 10%.
- P4 (uncertain, stated anyway): on close, HIGH ≈ LOW (dist2 is genuinely useful; bbox rarely suggests a full grid algorithm).

A failure of P1 would contradict the off-idiom mechanism as the main cause; we will report it as such.


---
## Results (appended 2026-10-12 13:30 UTC, unedited predictions above)

Correct on all 8 variants, %, pooled over seeds 1–2 (120 programs per cell); HIGH−LOW = paired difference with 95% bootstrap CI over instances.

| model | task | K0 | HIGH (Δ vs K0) | LOW (Δ vs K0) | HIGH − LOW |
|---|---|---|---|---|---|
| 8B | hull | 96.7 | 7.5 (−89.2) | 58.3 (−38.3) | **−50.8** [−60.8, −40.8] |
| 8B | area2 | 75.8 | 90.8 (+15.0) | 97.5 (+21.7) | −6.7 [−12.5, −0.8] |
| 8B | close | 100.0 | 54.2 (−45.8) | 99.2 (−0.8) | −45.0 [−55.9, −34.2] |
| 32B | hull | 82.5 | 5.8 (−76.7) | 55.8 (−26.7) | **−50.0** [−60.0, −40.0] |
| 32B | area2 | 90.8 | 95.0 (+4.2) | 71.7 (−19.2) | +23.3 [+15.0, +31.7] |
| 32B | close | 94.2 | 90.0 (−4.2) | 79.2 (−15.0) | +10.8 [+2.5, +19.2] |
| 14B (exploratory) | hull / area2 / close | 93.3 / 96.7 / 100 | 28.3 / 100 / 100 | 51.7 / 92.5 / 100 | −23.3 / +7.5 / 0 |

**Verdicts:**
- **P1 partly confirmed.** Hull: HIGH ≫ LOW harm for both models (−50 points, CIs far from 0; 14B −23). Area2: holds only weakly at 8B (−6.7) and
  is **reversed at 32B** (+23.3). → P1 fails as stated.
- **P2 refuted.** LOW helpers are not harmless at 32B: hull −26.7, area2 −19.2, close −15.0. Post hoc: the LOW sets pull in `on_segment`
  as a dependency, and it is called in 44–49 of 60 LOW hull programs (explicit collinear handling again); on area2, LOW programs call
  `segments_intersect`/`on_segment` and drift into intersection checks (note: those polygons self-intersect, see the item-7 caveat).
- **P3 half confirmed.** Hull: `polar_sort` is called in 39/60 (8B) and 56/60 (32B) HIGH programs (≥ 25% ✔), and those programs fail.
  Area2: `convex_hull` is never called (0% vs ≥ 10% predicted ✘): the hull-area detour does not happen when only 2 helpers are offered.
- **P4 mixed.** Close: HIGH ≈ LOW at 14B, HIGH better at 32B (+10.8), HIGH much worse at 8B (−45; `bbox` called in 30/60 programs, grid
  bucketing bugs).

**What survives:** the strongest version of the mechanism. A single helper that names an alternative algorithm (polar_sort → Graham scan)
drives a near-total collapse (97 → 8, 83 → 6) with the switch visible in the code. **What does not:** predicting harm from a priori
"similarity" labels. Weakly related helpers also hurt through their *dependencies* and through task-specific detours, and the same
helper can help one task (area2 at 8B: +15 to +22, integer predicates remove float `big`-variant failures) while hurting another.
