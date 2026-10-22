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
