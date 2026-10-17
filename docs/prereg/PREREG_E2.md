# Pre-registration: E2, do the F1 / F2 mechanisms predict NEW tasks?

Written 2026-10-13 12:45 UTC, after implementing and validating the two new tasks (no model output on them has been generated or seen).
Results will be appended below without editing this section.

## New tasks (poc/run_geo.py; validated before any model run)
- **delaunay**: n points (8 or 12; no 3 collinear, no 4 cocircular) and a triangulation of them (Delaunay + 0–3 random edge flips;
  identity input lists every triangle counter-clockwise). Question: how many triangles have a listed point STRICTLY inside their
  circumcircle? The prompt does not mention vertex order. Variants as for all tasks; `mirror` makes every triangle clockwise, `permute`
  relabels points and gives each triangle a random start vertex and orientation; `degen` = doubled coordinates + 4 cocircular points
  (a small rectangle), re-triangulated, so a non-strict test is wrong. Oracle checked against an independent Fraction circumcentre test,
  triangulations checked (2n − h − 2 triangles, each edge in ≤ 2 triangles, areas sum to the hull area). Reference passthrough 480/480,
  MR false alarms 0/60. Negative controls through the harness: a program using the counter-clockwise-only in-circle test without fixing
  orientation is correct on all 8 variants for 0/60 instances (fails mirror 59, permute 59); a non-strict test fails `degen` 60/60.
- **diameter**: squared distance of the farthest pair of n points (12 or 24). `degen` = doubled coordinates + a duplicated hull vertex +
  the midpoint of a hull edge (answer ×4). Reference passthrough 480/480, MR false alarms 0/60.

## Conditions (Qwen3-8B and Qwen3-32B-AWQ without thinking; gpt-oss-20b at low effort as the reasoning reference)
`--stdlib`, T = 0.7, "should use" toolbox header, seeds 1 and 2, 30 instances × 2 sizes = 60 programs per task per seed.
- delaunay (F2 replication, hidden contract): (a) no toolbox; (b) **signed**: the needed helper `in_circle(a, b, c, d)` with the terse
  but true comment "exact in-circle test for a counter-clockwise triangle abc: > 0 inside, 0 on, < 0 outside its circumcircle";
  (c) **doc**: same code, comment spells out "WARNING: valid only if a, b, c are in COUNTER-CLOCKWISE order; for a clockwise triangle the
  sign is reversed"; (d) **fixed**: the helper multiplies by the orientation sign, comment "any vertex order".
- diameter (F1 replication, algorithm-suggesting helpers; exactly as PREREG_E4): K0 (no helper needed, so no toolbox); **HIGH** =
  {convex_hull, polar_sort} (+ deps orient, dist2), suggesting hull + rotating calipers; **LOW** = {point_in_polygon, segments_intersect}
  (+ deps on_segment, orient), related geometry that suggests no alternative algorithm.
Primary metric: correct on all 8 variants; paired by instance; 95% bootstrap CI over instances (pooled seeds).

## Predictions
- **F2-P1:** fixed − signed ≥ +15 points for both Qwen models.
- **F2-P2:** under signed, ≥ 60% of the Qwen failures are orientation failures: right on identity, translate, rot90, scale and big,
  wrong on mirror and/or permute.
- **F2-P3 (uncertain):** the warning does not fix it: doc recovers less than half of the signed → fixed gap (Qwen models).
- **F2-P4:** gpt-oss-20b low is much less affected: fixed − signed ≤ 10 points.
- **F1-P1:** diameter HIGH − LOW < 0 for both Qwen models (confirmed if the CI excludes 0, weak if only the point estimate is < 0).
- **F1-P2:** under HIGH, ≥ 25% of Qwen programs call convex_hull or polar_sort (the route switch is visible).
- **F1-P3:** under HIGH, programs that call convex_hull / polar_sort are correct less often than those that do not (both Qwen models).
- **F1-P4:** gpt-oss-20b low: |HIGH − K0| ≤ 5 points.
Exploratory (no prediction): no toolbox vs signed on delaunay; tokens per condition.

A dropped condition, noted before any run: a float `circumcenter` helper as an algorithm-suggesting distractor for delaunay was
designed and then dropped, because float circumcentre programs (with and without a tolerance) pass all 8 variants on the validation
set (Python computes the numerators exactly), so that route is not fragile here and the test would be uninformative.


---
## Results (appended 2026-10-13 12:25 UTC; predictions above unedited)

Correct on all 8 variants, k of 120 (2 seeds × 60); differences paired by (instance, seed) with 95% bootstrap CIs; script `poc/analyze_e2.py`.

**delaunay (F2 replication: a needed helper with a hidden orientation contract)**

| model | no toolbox | signed (terse contract) | doc (explicit warning) | fixed (any order) | fixed − signed | share of failures under signed that are orientation-only |
|---|---|---|---|---|---|---|
| Qwen3-8B | 2 | **1** | 18 | **109** | **+90.0** [+84.2, +95.0] | 109/119 (92%) |
| Qwen3-32B-AWQ | 55 | **3** | 80 | **106** | **+85.8** [+79.2, +91.7] | 113/117 (97%) |
| gpt-oss-20b low | 93 | 118 | 118 | 117 | −0.8 [−4.2, +2.5] | 0/2 |

- **F2-P1 confirmed** (+90 / +86, threshold +15). **F2-P2 confirmed** (92% / 97% of failures are right on identity, translate,
  rot90, scale and +10^9 and wrong only on mirror and/or permute, i.e. the program never orients the triangle). **F2-P4 confirmed**
  (gpt-oss −0.8). **F2-P3 split:** the warning recovers 16% of the gap at 8B (holds) but 75% at 32B (fails): the larger model can act on
  an explicit contract, the smaller cannot.
- Exploratory: for Qwen3-32B the needed-but-terse helper is far **worse than no helper** (3 vs 55 of 120); for gpt-oss the same helper
  helps (93 → 118). For 8B the task is out of reach without the helper (2 of 120).

**diameter (F1 replication: algorithm-suggesting vs. non-suggesting extra helpers)**

| model | K0 (no toolbox) | HIGH (convex_hull, polar_sort) | LOW (point_in_polygon, segments_intersect) | HIGH − LOW | programs calling convex_hull / polar_sort under HIGH |
|---|---|---|---|---|---|
| Qwen3-8B | 112 | 119 | 120 | −0.8 [−2.5, 0.0] | 20/120 (17%) |
| Qwen3-32B-AWQ | 110 | 84 | **54** | **+25.0** [+12.5, +37.5] | 116/120 (97%) |
| gpt-oss-20b low | 120 | 116 | 120 | −3.3 [−6.7, −0.8] | 120/120 |

- **F1-P1 not confirmed:** 8B only weakly (−0.8, CI touches 0); **32B goes the other way** (+25). **F1-P2:** 32B yes (97%), 8B no (17%).
  **F1-P3:** 8B 19/20 vs 100/100 (direction as predicted, one failure); 32B uninformative (only 4 programs avoid the route).
  **F1-P4 confirmed** (gpt-oss −3.3).
- **Why 32B fails the prediction: a second channel of helper harm, input format.** 64 of the 66 LOW failures (and 8 of 36 HIGH, 10 of 10
  K0 failures) crash because the program reads every stdin line as a point and ignores the stated first line `n`; re-run with that line
  removed, they print the right answer (counterfactual check). 53 of the 66 failing LOW programs call none of the offered helpers: the
  irrelevant toolbox did not change the algorithm (all are brute force), it displaced attention from the stated input format (one program
  even tests `if 'n' in line`). Under HIGH, 32B switches to hull-based code (97%) and 20 programs are wrong on the original input.
- Net for the mechanism: algorithm steering (F1) and hidden contracts (F2) both predict new tasks for the 32B, but "only
  algorithm-suggesting helpers hurt" is false: unrelated-but-plausible helpers also break input parsing, the same skipped-field failure
  as gpt-oss on VRPTW (F3). The 8B, which keeps brute force under both toolboxes, is unaffected on this task.

---
## Extension (registered 2026-10-13 13:20 UTC, before running): more models and thinking on the delaunay hidden-contract test

Same delaunay conditions (none / signed / doc / fixed), 2 seeds × 60. Added: Llama-3.3-70B-Instruct w4a16 and Qwen3-14B without thinking;
Qwen3-8B and Qwen3-32B-AWQ WITH thinking (signed and fixed only; 16k max tokens).
- **X1:** Llama-3.3-70B and Qwen3-14B behave like the Qwen 8B / 32B: fixed − signed ≥ +15 points, and ≥ 60% of signed failures are
  orientation-only.
- **X2:** thinking reduces but does not remove the trap: for both Qwen sizes, signed stays below fixed (CI excludes 0) but the gap is less
  than half of the no-thinking gap (8B: < 45 points; 32B: < 43 points).


### Extension results (appended 2026-10-13 13:55 UTC; predictions above unedited)

| model | no toolbox | signed | doc | fixed | fixed − signed | orientation-only share of signed failures | tokens signed / fixed |
|---|---|---|---|---|---|---|---|
| Llama-3.3-70B | 81 | **8** | 59 | **120** | +93.3 [+88.3, +97.5] | 110/112 (98%) | 348 / 382 |
| Qwen3-14B | 76 | **4** | 52 | **120** | +96.7 [+93.3, +99.2] | 113/116 (97%) | 430 / 453 |
| Qwen3-8B, thinking | – | 51 | – | 118 | +55.8 [+46.7, +65.0] | 65/69 (94%) | 8,806 / 4,697 |
| Qwen3-32B, thinking | – | 118 | – | 120 | +1.7 [0.0, +4.2] | 2/2 | 7,832 / 5,392 |

- **X1 confirmed:** the trap is the same in a second family and at 14B (+93 / +97 points; 97–98% orientation-only). For both, the terse
  helper is far worse than no helper (8 vs 81; 4 vs 76); the warning recovers 41–46% of the gap.
- **X2 not confirmed, in opposite directions:** thinking removes the trap at 32B (118/120, gap +1.7, CI touches 0) but only partly at 8B
  (51/120; gap 55.8 > 45, 62% of the no-thinking gap remains). Either way thinking costs 7.8–8.8k tokens per program, against ≈0.4k for
  fixing the helper's contract.
