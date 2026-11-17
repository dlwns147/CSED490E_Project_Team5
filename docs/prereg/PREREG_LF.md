# PREREG_LF — predicting the method's accuracy gain on a domain without labels

Written 2026-11-17 20:3x UTC. Purpose: the progress note's "rule for a new domain" should tell, before any labels exist, whether the ladder
beats thinking. The utility gain splits exactly as ΔU = 100·a·(p − q) − 0.5·Δktok (progress §7); a and Δktok need no labels, the accuracy
term 100·a·(p − q) does.

**Estimators (per accepted item, summed and divided by all items, ×100):**
- Rule A: [thinking's answer ≠ the accepted answer] (trusts the accepted answer).
- Rule B: [accepted = third] − [thinking = third], where "third" is a model outside the ladder; 0 when the third has no answer.
- **Hybrid:** rule B's term where the third has a (checked, where a check exists) answer, rule A's term where it has none.

**Known before writing (exploratory, all seen):** OEIS, nine cells (seeds 1–3, three ladders): mean absolute error rule A 4.2, rule B 0.9,
hybrid 1.0 points. Trips, four cells (seeds 20–22; third = gpt-oss-20b for Qwen and gpt-oss-120b ladders, Qwen3-32B for gpt-oss-20b):
rule A 3.0, rule B fails (the third answers mostly easy trips, where thinking agrees; e.g. Qwen3-8B +8.3 vs +33.3 measured), hybrid 1.5.
Seed-3 OEIS rule B was pre-registered (PREREG_X56 S3) and held.

**Test (grids, never computed for any estimator).** The four grid cells of `results/tmp_decomp.py` (seeds 14–16, closure and one-solution
check as registered): GridPuzzle and Mitra-Baral, Qwen3-8B RL ladder and gpt-oss-20b ladder; measured accuracy terms +32.4, +16.4, +8.5,
+1.4 (already known). Third: gpt-oss-20b's quick translation for the Qwen3-8B ladder; Qwen3-8B (RL translator) quick translation for the
gpt-oss-20b ladder; its answer counts only when its own count is 1. Answers compared after the same scoring normalisation.
- **Prediction:** the hybrid is within 2.0 points of the measured term in each of the four cells, and its mean absolute error over all
  17 cells stays below 2.0 and below rule A's.
- **Decision:** holds → the progress note states the hybrid as the label-free rule for a new domain (two quick translations from different
  families + both routes on a few hundred items, no labels). Fails in any grid cell → the rule stays "rule A plus a small labeled sample",
  and the note says where the hybrid broke.

**Result (2026-11-17 20:4x UTC; `results/tmp_lf3_grids.py`).** The recomputed closures reproduce the stored ones row for row (counts and
exactness equal in all 3,492 rows) and now keep each closure's grid.

| Cell | Measured | Rule A | Rule B | Hybrid |
|---|---|---|---|---|
| GridPuzzle, Qwen3-8B (RL) ladder | +32.4 | +36.3 | +14.0 | **+33.2** |
| GridPuzzle, gpt-oss-20b ladder | +16.4 | +20.2 | +4.3 | **+16.3** |
| Mitra-Baral, Qwen3-8B (RL) ladder | +8.5 | +15.2 | +2.8 | **+8.9** |
| Mitra-Baral, gpt-oss-20b ladder | +1.4 | +2.1 | −0.4 | **+1.1** |

The hybrid is within 0.8 points in every grid cell; over all 17 cells (OEIS 9, trips 4, grids 4) its mean absolute error is 1.0 point
(rule A 3.8). **Prediction holds.** Rule B fails on grids as on trips: the third model answers a selected, easier subset. By the decision the
progress note states the hybrid as the label-free rule. Limits: the hybrid was shaped on OEIS and trips (seen), grids are its only held-out
test; it needs a third model's quick translation on the sample, and all domains here have a check; it estimates the accuracy term, the token
term is measured directly.
