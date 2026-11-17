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
