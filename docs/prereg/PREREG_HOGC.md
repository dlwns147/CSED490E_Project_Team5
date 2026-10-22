# Pre-registration HO-G-C: does a brute-force view close the check leak that breaks the recipe for Qwen3-8B on held-out geometry?

Written 2026-10-21 18:5x UTC (Slurm server), before any brute-force program exists. Results are appended below without editing this section.

**Why.** On the four held-out geometry tasks (PREREG_HOG.md) "fact first, think only if the free check fails" (FF) beats always thinking
for gpt-oss-20b and Qwen3-14B-AWQ but not for Qwen3-8B (59.7% @ 4.55k vs THINK 74.0% @ 9.82k): 64 of its fact programs are consistently
wrong, so every transformed copy reproduces the same wrong answer and the metamorphic check (MR) accepts them (convex 19, tri 27, clip 18;
Qwen3-14B-AWQ 7, gpt-oss-20b 1). This is the one place on held-out data where the recipe fails. If a second, label-free view catches these
programs cheaply, the recipe holds for all three 24 GB models; if not, the limit stays as stated (for the weakest model, always think).
E3b (PREREG_E3B.md, dev tasks, Qwen3-8B) found that a brute-force program by the same model flags 86–90% of the programs MR misses, with
5–7% false alarms on simple tasks but 84% on hard ones (its own brute force was wrong), and saved nothing against a 1,024-token thinking
budget. Here the fallback is full thinking (≈ 9.8k tokens for Qwen3-8B), so a ~0.5k-token second program has more room to pay.

**New arm (the only GPU run):** `brute` = `poc/run_geo_cross.py --brute --stdlib`, the task prompt plus E3b's sentence "Write the simplest
brute-force program you can: correctness matters, speed does not (inputs are small).", **no toolbox and no algorithm hint** (a view
independent of the fact's helpers and algorithm), same instances and settings as HO-G (n_inst 12, T 0.7, seeds 1–3, max_tokens 4096;
gpt-oss-20b low effort, Qwen3 thinking off). Lane `poc/slurm/hogc_brute.sh`, tag `SL_HOGC_<model>_geo_brute_s<seed>`, on RTX 3090. The fact
(F) and thinking (THINK) rows are the stored HO-G rows of the old server; every policy pairs rows of the same item and seed.
**Agreement** (label-free): two programs agree if their outputs are equal (as numbers where both parse as fractions) on each of six inputs:
the given instance and its translate / rot90 / mirror / permute / scale copies (no 10^9 copy, where a brute force may be legitimately slow);
a crash, timeout or empty output = disagreement.
**Policies** (offline, `poc/analyze_hogc.py`; tokens = every cheap program written + thinking where escalated; correct = right on all 8
variants, as before):
- FF (HO-G): accept F if it passes MR, else THINK.
- STRICT (differential check): accept F only if F passes MR **and** agrees with the brute-force program B; else THINK.
- TWO-VIEW (two cheap views): accept F if F and B both pass MR and agree; if exactly one passes MR, accept that one; THINK if neither passes
  or both pass and disagree.
- RESAMPLE (no new run): accept F only if it passes MR and agrees with a second fact sample (the same item's fact row of the next seed:
  s1↔s2, s2↔s3, s3↔s1); its tokens are added.
- THINK (always).

**Predictions** (seed means over 96 items × 3 seeds unless stated):
- HOGC-P1 (the leak is visible): for Qwen3-8B, STRICT flags ≥ 60% of the fact programs that pass MR but are wrong, and ≤ 15% of the correct
  MR-passing ones on overlap / convex / tri; on clip (exact rational area, no natural brute force) its false alarms are ≥ 30%.
- HOGC-P2 (accuracy): STRICT for Qwen3-8B ≥ THINK − 3 (≥ 71.0%; FF 59.7%).
- HOGC-P3 (the handoff's decision rule = HOG-P1): STRICT ≥ THINK − 1 at ≤ 60% of THINK's tokens for Qwen3-8B. **Predicted to fail on
  tokens** (expected ≈ 70%: FF already escalates 41% of items at ≈ 9.8k each, and each newly flagged item adds another thinking run).
- HOGC-P4 (uncertain): TWO-VIEW meets HOG-P1 for Qwen3-8B (≥ THINK − 1 at ≤ 60% of its tokens), because the brute-force program replaces
  thinking where F visibly fails but B passes MR; this holds only if B is right on most such items.
- HOGC-P5 (no harm without a leak): for gpt-oss-20b and Qwen3-14B-AWQ, STRICT and TWO-VIEW are within 1.5 points of FF, and HOG-P1 still
  holds for both (≥ THINK − 1 at ≤ 60% of THINK's tokens).
- HOGC-P6: RESAMPLE flags < 40% of Qwen3-8B's leaked programs (consistent wrong logic repeats across samples, as for Qwen3-4B in SIZE-CHK).

**Decision rule.** (a) If STRICT or TWO-VIEW meets HOG-P1 for Qwen3-8B on the seed means and on ≥ 2 of 3 seeds, and HOGC-P5 holds: the free
check on geometry becomes "metamorphic copies + a brute-force view", and "the recipe holds on held-out geometry" extends to all three 24 GB
models (PROPOSAL finding 6, §7 'Checks leak', both languages). (b) If only accuracy is recovered (≥ THINK − 3) at > 60% of THINK's tokens:
the limit is restated with the measured saving. (c) Otherwise the limit stays: for Qwen3-8B on geometry, always think.
Also reported (labels used only for these notes): brute-force correctness per task, its tokens / finish reasons / crashes / timeouts, and
≥ 10 flagged leaked programs and ≥ 5 false alarms read in full.

## Results (2026-10-22 01:5x UTC; results/hogc_analysis.log, poc/analyze_hogc.py; 96 items × 3 seeds; brute-force rows on RTX 3090)
Harness check: FF and THINK reproduce PREREG_HOG.md exactly for all three models.
| held-out geometry, seed means | FF | STRICT (MR + agree with brute force) | TWO-VIEW | RESAMPLE (second fact sample) | THINK |
|---|---|---|---|---|---|
| gpt-oss-20b | **99.0% @ 0.82k** | 96.2% @ 1.93k | 99.0% @ 1.41k | 98.3% @ 1.64k | 93.1% @ 1.69k |
| Qwen3-14B-AWQ | **84.4% @ 2.92k** | 77.1% @ 6.44k | 83.0% @ 3.58k | 79.2% @ 4.93k | 76.7% @ 8.58k |
| Qwen3-8B | 59.7% @ 4.55k | 64.2% @ 6.63k | 55.9% @ 3.14k | 65.6% @ 6.54k | **74.0% @ 9.82k** |
- **HOGC-P1 refuted** on the main part: STRICT flags 26 of Qwen3-8B's 64 leaked programs (41%, not ≥ 60%). False alarms on overlap / convex /
  tri 17 / 132 (12.9%, ≤ 15%: holds); clip false alarms ≥ 30% hold for gpt-oss-20b (42 / 59) and Qwen3-14B-AWQ (22 / 23) (Qwen3-8B has no
  correct clip program that passes MR).
- **HOGC-P2 refuted** (STRICT 64.2% < 71.0%); **P3 fails** as predicted, and on accuracy too; **P4 refuted** (TWO-VIEW 55.9%: where the fact
  program visibly fails, the brute-force program it takes instead is right on 16 of 60); **P5 refuted for STRICT** (−2.8 / −7.3 points for
  gpt-oss-20b / Qwen3-14B-AWQ: wrong brute-force programs flag correct ones, e.g. 54 of Qwen3-14B-AWQ's 69 correct tri programs), holds for
  TWO-VIEW (0.0 / −1.4; HOG-P1 still holds for Qwen3-14B-AWQ, not for gpt-oss-20b at 83% of THINK's tokens); **P6 refuted** (RESAMPLE flags
  29 / 64 = 45%, as many as the brute force, at the same cost).
- **Decision (c): the limit stays** — for Qwen3-8B on held-out geometry always thinking is best (74.0% @ 9.8k vs the best label-free check,
  RESAMPLE, 65.6% @ 6.5k); for the two stronger models plain FF remains best and a second view only adds tokens and false alarms.
- **Why (raw programs; labels used only here):** 37 of the 64 leaked programs (all 19 convex, 18 tri) answer the given instance and all its
  rigid copies correctly and fail only the degenerate copy, which no check on the given instance exercises: convex sets its turn direction
  at the first vertex triple and crashes when that triple is collinear; tri uses the textbook `not (has_neg and has_pos)` test, which
  counts points on an edge as inside (the statement says strictly inside), and the brute force repeats the same snippet. Of the 27 programs
  wrong on the given instance itself (clip 18, tri 9), the brute force flags 19 (70%). Every false alarm comes from a wrong brute-force
  program (logic errors, float errors on transformed copies, crashes), not from the fact program.
**Reading:** the check leak that breaks the recipe for the weakest model is mostly edge-case bugs that never show on the given input; a
second program written by the same model catches most wrong answers on the given input but shares its edge-case habits. A check would have to
exercise the edge cases the statement names (collinear vertices allowed, points on an edge do not count) to see them.

## Addendum HO-G-E (2026-10-22 02:0x UTC, before any test is written): edge-case tests from the statement, written once per task
**Why.** HO-G-C showed that 37 of Qwen3-8B's 64 leaked programs fail only edge cases that the statement names but the given input does not
contain (collinear vertices allowed; points on an edge do not count; duplicates count; touching counts), so no check on the given input
sees them, and a second program by the same model copies the same textbook snippet. Closest work: CodeT (model-written tests), AlphaCodium
(AI-written edge-case tests). Difference here: the tests depend only on the statement, so the model writes them **once per task type** (not
per problem), and they only gate thinking.
**New arm (GPU, cheap):** `poc/run_edge_tests.py`: for each task (overlap, convex, tri, clip) and seed 1–3, the same model (cheap-arm
settings: Qwen3 thinking off, gpt-oss-20b low) gets the statement of one instance and is asked for 3–6 SMALL test cases, each a stdin plus the
expected output, that exercise the special cases the statement names or implies, small enough to compute by hand (JSON list). Tests are
used as written (no answers, no filtering by other programs); a malformed test counts against every program. Tag
`SL_HOGCE_<model>_s<seed>`, lane `poc/slurm/hogce_tests.sh`.
**Policy EDGE** (offline, `poc/analyze_hogc.py --edge`): accept the fact program only if it passes MR **and** prints the expected output on
every test of its task (numbers compared as fractions); else THINK. Test-writing tokens are spread over the task's 24 items of that seed.
**Predictions** (seed means; same decision rule as above):
- HOGE-P1: for Qwen3-8B, EDGE flags ≥ 60% of the 37 edge-case-only leaks and ≥ 40% of the 27 wrong-on-input leaks; false alarms (correct
  MR-passing fact programs flagged) ≤ 15% for each model.
- HOGE-P2: EDGE for Qwen3-8B ≥ THINK − 3 (≥ 71.0%) at ≤ 70% of THINK's tokens; HOG-P1 itself (≥ THINK − 1 at ≤ 60%) is uncertain.
- HOGE-P3: for gpt-oss-20b and Qwen3-14B-AWQ, EDGE is within 1.5 points of FF and HOG-P1 still holds.
**Decision.** As HO-G-C: (a) if EDGE meets HOG-P1 for Qwen3-8B (seed means, ≥ 2 of 3 seeds) and HOGE-P3 holds, the recipe's geometry check
becomes "metamorphic copies + edge-case tests written once per task" and the held-out claim extends to all three 24 GB models; (b) accuracy
≥ THINK − 3 at > 60% of THINK's tokens → the limit is restated with the saving; (c) otherwise the limit stays.

## HO-G-E results (2026-10-22 02:15 UTC; results/hogce_analysis.log; tests: results/edgetests_SL_HOGCE_*; 36 test sets, 5–7 tests each)
| seed means | FF | EDGE (MR + own edge-case tests) | THINK |
|---|---|---|---|
| gpt-oss-20b | **99.0% @ 0.82k** | 97.6% @ 1.54k (91% of THINK's tokens) | 93.1% @ 1.69k |
| Qwen3-14B-AWQ | **84.4% @ 2.92k** | 76.7% @ 6.70k | 76.7% @ 8.58k |
| Qwen3-8B | 59.7% @ 4.55k | 72.9% @ 9.14k (93%) | **74.0% @ 9.82k** |
Writing the tests costs 0.2–1.2k tokens per task, i.e. 10–50 per problem.
- **HOGE-P1 half holds:** the tests flag 32 of Qwen3-8B's 37 edge-case-only leaks and all 27 wrong-on-input ones — they do exercise the
  cases the given input lacks — but **false alarms are not ≤ 15%**: 89 of 132 correct MR-passing Qwen3-8B programs (67%); gpt-oss-20b
  convex 72 / 72 and tri 72 / 72; Qwen3-14B-AWQ tri 69 / 69, clip 23 / 23.
- **HOGE-P2 refuted:** accuracy ≥ THINK − 3 holds (72.9%), but at 93% of THINK's tokens (not ≤ 70%): the gate escalates almost everything.
  **HOGE-P3 refuted:** gpt-oss-20b stays within 1.5 points (−1.4) but HOG-P1 no longer holds (91% of THINK's tokens); Qwen3-14B-AWQ −7.7.
- **Decision (c): the limit stays.**
- **Why (raw tests):** the models state the rule correctly but compute the boundary cases wrong by hand, exactly where the rule matters.
  Every tri test set of every model contains a wrong expected count (all correct tri programs fail them: Qwen3-8B 80 / 80, gpt-oss-20b
  144 / 144, Qwen3-14B-AWQ 139 / 139) — e.g. gpt-oss-20b counts (2, 3) inside the triangle (0,0) (5,0) (0,5) though it lies on the edge
  x + y = 5; Qwen3-14B-AWQ expects (1, 1) inside (0,0) (2,0) (0,2). Tests also break the input contract (fractional coordinates where the
  format says integers, degenerate triangles, non-simple polygons), and Qwen3-8B marks the unit square as not convex.
**Reading (HO-G-C + HO-G-E):** for the weakest model none of three label-free second views — a brute-force program, a second sample,
model-written edge-case tests — lets "fact first, think only on a visible failure" beat always thinking on held-out geometry. The views that
see the edge-case bugs (the tests) are themselves wrong on those edge cases; the views that are mostly right (a second program) share the
bugs. The recipe's limit is the model's own edge-case knowledge, which a self-written check cannot supply.

## Addendum HO-G-M (2026-10-23 0x:xx UTC, before any relation is written): model-written metamorphic relations from the statement
**Why.** HO-G-E's model-written edge-case tests saw Qwen3-8B's leaked programs (59 / 64) but were useless because the models computed the
expected answers of the boundary cases wrong (every tri test set). A metamorphic relation needs no expected answer: only an invariance the
statement implies ("a vertex added at the midpoint of an edge does not change convexity"; "a point added exactly on an edge does not change
the count of points strictly inside"; "touching counts as intersecting"). The program's own answer on the given instance is compared with its
answer on the transformed instance. Closest work: LLM-generated metamorphic relations for testing (e.g. Zhang et al. 2023, "Can LLMs
generate metamorphic relations?"; MR-Scout 2024); here they are written once per task type from the statement and gate thinking.
**New arm (GPU, cheap):** `poc/run_edge_mr.py`: per task (overlap, convex, tri, clip) and seed 1–3, the same model (cheap-arm settings)
writes a Python function `transform(stdin_text) -> stdin_text` for 2–4 transformations that the statement says must keep the answer the
same (or change it in a stated way it encodes as `expect(old_answer) -> new_answer` using only the old answer), aimed at the special cases
the statement names. Tag `SL_HOGCM_<model>_s<seed>`. Used as written; a transform that crashes on an input is skipped for that input.
**Policy MR+** (offline, `poc/analyze_hogc.py --mr`): accept the fact program only if it passes the original MR check **and** every model-written
relation on the given instance (its output on the transformed input equals `expect(output on the given input)`); else THINK.
**Predictions** (seed means; decision rule as HO-G-C):
- HOGM-P1: MR+ flags ≥ 60% of Qwen3-8B's 37 edge-case-only leaks (the target of this check) with false alarms ≤ 15% of correct MR-passing
  programs for each model (no hand-computed answers, so far fewer wrong expectations than HO-G-E).
- HOGM-P2: MR+ for Qwen3-8B ≥ THINK − 3 (≥ 71.0%) at ≤ 70% of THINK's tokens.
- HOGM-P3: for gpt-oss-20b and Qwen3-14B-AWQ, MR+ is within 1.5 points of FF and HOG-P1 still holds.
**Decision** as HO-G-C: (a) MR+ meets HOG-P1 for Qwen3-8B (≥ THINK − 1 at ≤ 60% of its tokens, ≥ 2 of 3 seeds) and P3 holds → the geometry
check becomes "rigid copies + statement-derived relations" and the held-out geometry claim extends to all three models; (b) accuracy only →
restated limit with the saving; (c) the limit stays.

## HO-G-M results (2026-10-22 18:4x UTC; results/hogcm_analysis.log; relations: results/edgemr_SL_HOGCM_*; 36 relation sets, 29 run)
| seed means | FF | MR+ (MR + own relations) | THINK |
|---|---|---|---|
| gpt-oss-20b | **99.0% @ 0.82k** | 95.8% @ 1.89k (111% of THINK's tokens) | 93.1% @ 1.69k |
| Qwen3-14B-AWQ | **84.4% @ 2.92k** | 79.2% @ 4.98k | 76.7% @ 8.58k |
| Qwen3-8B | 59.7% @ 4.55k | 67.7% @ 7.19k (73%) | **74.0% @ 9.82k** |
- **HOGM-P1 half holds:** the relations flag 23 of Qwen3-8B's 37 edge-case-only leaks (62%; but only 3 of the 27 wrong-on-input ones);
  false alarms are not ≤ 15% (Qwen3-8B 71 / 132; correct programs break the models' own relations: gpt-oss-20b tri 144 / 144, Qwen3-8B
  convex 100 / 118 — malformed transforms that also shift the count line, wrong expectations such as "a duplicated vertex flips convexity").
- **HOGM-P2 refuted** (67.7% < 71.0%; 73% of THINK's tokens); **HOGM-P3 refuted** (−3.2 / −5.2 points for the stronger models).
- **Decision (c).** MR+ is the best of the four self-written checks for Qwen3-8B (brute force 64.2%, resample 65.6%, edge tests 72.9% at 93%
  of the tokens) but none reaches always thinking.
**Bound (computed after these results; labels used only for the bound):** with a *perfect* check on the fact program (accept exactly the
correct ones), FF reaches gpt-oss-20b 99.0% @ 49% of THINK's tokens, Qwen3-14B-AWQ 84.4% @ 38%, **Qwen3-8B 75.0% @ 70%**. For Qwen3-8B the
pre-registered rule (≥ THINK − 1 at ≤ 60% of its tokens) is unreachable by any check: its fact programs are wrong on so many items that
each must pay for thinking. The attainable target is "same accuracy at about 70% of the tokens"; the self-written checks get 64–68% at
67–73%. **Reading:** for the weakest model the limit is the fact program's error rate first and the check's leak second.

## Addendum HO-G-R (2026-10-22 21:4x UTC, before running): one cheap repair on a visible failure, before thinking, on held-out geometry
**Why.** On word problems one short repair turn shown the failure, before thinking, was never worse than the plain recipe (HO7). On held-out
geometry FF sends 41% of Qwen3-8B's items to thinking at ≈ 9.8k tokens each, so a ≈ 1k repair that succeeds saves most of that. The repair
cannot touch the leak (wrong programs that pass the check), only the visible failures.
**Arm** (`poc/run_geo_repair.py`; the stored HO-G fact rows; 3 models; seeds 1–3; cheap-arm settings, no thinking): for each fact program that
fails the free check (crash, timeout, no output, or outputs that disagree across the moved / rotated / mirrored / permuted / scaled /
shifted copies of its own input), the same model gets the task statement, its program and the evidence (the error, or "on the given input
it printed X; on the copy <kind> it printed Y; they must agree") and writes a corrected program. **Policy FF-RG:** accept the repaired
program if it passes the same free check; else THINK (stored rows). Tokens: fact + repair (where written) + thinking where escalated.
**Predictions** (seed means):
- HOGR-P1: for Qwen3-14B-AWQ and Qwen3-8B, ≥ 30% of the escalated items get a repaired program that passes the check.
- HOGR-P2: FF-RG ≥ FF for every model, at ≤ 85% of FF's tokens for Qwen3-14B-AWQ and Qwen3-8B.
- HOGR-P3: for Qwen3-8B, FF-RG stays below always thinking by more than 1 point (the leak is untouched).
**Decision.** P1 + P2 → the repair step joins the recipe's ladder on geometry as on word problems; otherwise it stays word-problem-only.

## HO-G-R results (2026-10-22 22:0x UTC; results/hogr_analysis.log; repairs: results/georepair_*; 3 seeds)
| model | FF − THINK | FF-RG (repair on a visible failure) − THINK | FF-RG tokens / FF's | repairs passing the check · right (thinking right on those) |
|---|---|---|---|---|
| gpt-oss-20b | +5.9 [+3.5, +8.7] | +6.6 [+4.2, +9.4] | 99% | 6 / 12 · 6 (4) |
| Qwen3-14B-AWQ | +7.6 [+4.2, +11.5] | **+9.4 [+5.6, +13.9]** | 90% | 10 / 49 (20%) · 7 (2) |
| Qwen3-8B | −14.2 [−19.4, −9.4] | −15.3 [−20.8, −10.4] | 95% | 12 / 92 (13%) · 3 (6) |
- **HOGR-P1 refuted** (repairs pass the check on 20% / 13% of the escalated items, not ≥ 30%); **HOGR-P2 refuted** (FF-RG ≥ FF for gpt-oss-20b
  +0.7 and Qwen3-14B-AWQ +1.7, not Qwen3-8B −1.0; tokens 90–95% of FF's, not ≤ 85%); **HOGR-P3 holds** (Qwen3-8B 15.3 points below THINK).
- **Decision: the repair step stays word-problem-only.** On geometry a disagreement between copies is less actionable than a Python error or a
  named constraint; it helps Qwen3-14B-AWQ a little, and Qwen3-8B's few repairs that pass the check are mostly wrong (the leak again).

## Addendum HO-X (2026-10-22 22:4x UTC, before computing; offline on stored rows): a check from a different model
**Why.** Every self-written second view (brute force, resample, edge tests, relations, repair) failed for Qwen3-8B because it repeats the
model's own mistakes. If the limit is this self-correlation, a view from a *different* model should catch the leaks. gpt-oss-20b also fits
one 24 GB GPU; its stored HO-G fact programs cover the same items (and its freev programs BWOR / LogiOR).
**Policy XV:** accept Qwen3-8B's (or Qwen3-14B-AWQ's) fact program only if it passes its own free check **and** agrees with gpt-oss-20b's
fact program for the same item and seed (geometry: equal outputs on the six inputs, as STRICT; word problems: equal printed values within
the grader's tolerance, the other program running); else the model's own THINK. Tokens: both cheap programs + thinking where escalated.
**Predictions** (seed means):
- HOX-P1: on held-out geometry XV flags ≥ 80% of Qwen3-8B's 64 leaked programs with ≤ 15% false alarms (gpt-oss-20b is right on 99%).
- HOX-P2: XV for Qwen3-8B on geometry ≥ THINK − 1 (≥ 73.0%) at ≤ 75% of THINK's tokens — the self-written checks reached at most 67.7%.
- HOX-P3: on BWOR / LogiOR XV for Qwen3-8B ≥ its FF-V (HO3) in both cells.
**Reading planned:** P1 + P2 → the weakest model's limit is self-correlation, and a second small model's program is the check that removes
it (at the price of running two models); otherwise the limit is also in what the stronger model gets wrong or in the cost.

### Results HO-X (2026-10-22 23:0x UTC; `python poc/analyze_hox.py`, offline on stored rows, 3 seeds)
XV = accept the model's fact program only if it passes its own free check and agrees with gpt-oss-20b's; else the model's THINK.
OSS (note, not pre-registered) = gpt-oss-20b's own plain recipe, for "the second model is run anyway".

| model · set | own policy | XV | THINK | OSS | XV − own | XV − THINK |
|---|---|---|---|---|---|---|
| Qwen3-8B · geometry | FF 59.7% @ 4.55k | 63.2% @ 6.45k (66%) | 74.0% @ 9.82k | 99.0% @ 0.82k | +3.5 [+1.0, +6.6] | −10.8 [−15.3, −6.6] |
| Qwen3-8B · BWOR | FF-V 36.2% @ 12.22k | 39.4% @ 13.03k (113%) | 38.2% @ 11.58k | 57.3% @ 2.39k | +3.3 [+0.8, +6.5] | +1.2 [+0.0, +3.3] |
| Qwen3-8B · LogiOR | FF-V 35.1% @ 12.49k | 36.6% @ 13.04k (115%) | 34.8% @ 11.38k | 52.9% @ 3.11k | +1.4 [+0.4, +2.9] | +1.8 [+0.4, +3.6] |
| Qwen3-14B-AWQ · geometry | FF 84.4% @ 2.92k | 83.7% @ 4.05k (47%) | 76.7% @ 8.58k | 99.0% @ 0.82k | −0.7 [−1.7, +0.0] | +6.9 [+3.8, +10.4] |
| Qwen3-14B-AWQ · BWOR | FF-V 33.3% @ 10.09k | 35.4% @ 10.67k (108%) | 30.1% @ 9.89k | 57.3% @ 2.39k | +2.0 [−0.4, +4.9] | +5.3 [+2.4, +8.9] |
| Qwen3-14B-AWQ · LogiOR | FF-V 29.7% @ 10.44k | 32.6% @ 11.01k (112%) | 27.9% @ 9.82k | 52.9% @ 3.11k | +2.9 [+0.7, +5.1] | +4.7 [+2.5, +7.6] |

- Geometry leaks (Qwen3-8B fact programs that pass MR and are wrong): XV flags **26 / 64**, all on the 27 that are wrong on the given
  input and **0 of the 37 that are wrong only on edge cases**; false alarms 0 / 132. Word problems: XV flags as many wrong programs as the
  model's own checker (55 / 58 vs 50 / 58; 33 / 34 vs 33 / 34) with half or fewer false alarms (6 / 20 vs 13 / 20; 2 / 19 vs 12 / 19).
- **HOX-P1 refuted** (26 / 64 = 41% flagged, not ≥ 80%; false alarms 0%). **HOX-P2 refuted** (63.2%, not ≥ 73.0%). **HOX-P3 holds**
  (XV ≥ FF-V on BWOR +3.3 [+0.8, +6.5] and LogiOR +1.4 [+0.4, +2.9]).
- **Reading.** Qwen3-8B's geometry leak has two parts. Errors on the given input are self-correlated, and a different model's program
  removes them (26 / 27). Errors only on edge cases cannot be seen by any check that runs on the given input and its transformed copies,
  however independent the second view; they need inputs the model does not generate well (its own edge tests failed, HO-G-E). On word
  problems a second model's answer is a better check than a self-written checker (same catches, fewer false alarms). But the check is
  dominated in every cell by simply using gpt-oss-20b (OSS − XV −16 to −36 points at 8–32% of THINK's tokens): **a check from a stronger
  model is not a recipe step, it is a reason to use the stronger model.** The weakest model's limit stands; the report states it with this
  split (on-input vs edge-only).

## Addendum HO-D gate (2026-10-22 23:0x UTC, before computing; offline): is a differential test on edge inputs worth a run?
37 of Qwen3-8B's 64 leaks are wrong only on the degenerate copy (convex: a collinear vertex; tri: a point on an edge / a duplicate), where a
second program of its own is right in 19 (resample F2) / 14 (brute force B) of 37. A differential test needs no expected answers: run two of
the model's own programs on edge inputs and escalate when they disagree. Before writing a generator of edge inputs (one GPU call per task),
its best case is bounded offline by using the benchmark's own extra inputs (`big`, `degen`; inputs only, no labels) as if the generator had
produced exactly them. **Policies** DIFF-F2 / DIFF-B / DIFF-ALL: accept F only if it passes MR and agrees with F2 / with B / with both on all
eight inputs; else THINK. **Gate:** if the best of these bounds is < THINK − 1 (73.0%) or needs > 75% of THINK's tokens, no generator run
(the claim cannot change); otherwise pre-register the generator run (HO-D) with its predictions before it.
