# PREREG_GRLV: is the free check a better label-free reward than a majority vote (TTRL)? Qwen3-8B, grids, registered 2026-11-12 06:5x UTC, before any training round

**Why.**
- Label-free RL is an active area. TTRL (2504.16084) rewards agreement with the group's majority answer. Co-rewarding (2508.00410), RESTRAIN (2510.02172) and OM-GRPO (2608.03119) refine votes. JURY-RL (ICML 2026) rewards a vote only when Lean verifies it.
- GRLLF showed that the check alone (the program has one solution) trains as well as labels. To claim the check as the reason, it must beat the standard label-free reward on the same puzzles, model and loop.

**Offline derivation (before any run;** stored base `gtr` first rounds, seeds 4–9 taken as one group of 6 per puzzle, scratch script).
- **Rewarded samples:**
  - GridPuzzle: the check rewards 319 right and 53 wrong samples (right : wrong 6.0). The vote (most common first-solution grid among samples with a grid) rewards 357 right and 326 wrong (1.1).
  - Mitra-Baral: 242 : 13 (18.6) against 273 : 86 (3.2).
- **Why the vote is worse here.**
  - Programs with two or more solutions still yield a grid and vote.
  - A misreading shared by most samples wins the vote.
  - The plurality grid is right on only 77 of 215 GridPuzzle puzzles.
- **Expectation.** The vote reinforces wrong readings about as often as right ones on GridPuzzle. Its quick step should gain much less than the check's, and its precision should fall.

**Method.** `poc/gp_train.py --reward vote` (committed with this file). It is GRLLF's cross-fitted run (same folds, loop, settings and prompt) with one change. The reward is 1 if the sample's first-solution grid (lower-cased) is the most common grid among the group's 8 samples that have one; samples with no grid get 0. The label is logged, not used. Tags `q8bgrlv0`, `q8bgrlv1`. Evaluated as GRLLF: arm `gtr` with the adapter, seeds 4–9, the ladder through base `gtrt` → `think`. Command: `python poc/gp_eval.py --grl --extra lf=q8bgrllf0+q8bgrllf1,vote=q8bgrlv0+q8bgrlv1`, and `--quick q8b lf=... vote=... --seeds 4,5,6,7,8,9` for the quick step.

**Predictions.**
- **V-P1 (decides).** GridPuzzle: ladder(lf) − ladder(vote), interval above 0.
- **V-P2.** GridPuzzle quick step, vote − base wrong count-1 share: point estimate above lf's −2.5 (the vote adds wrong passes relative to the check).
- **V-P3 (reported).** Mitra-Baral, the same two differences; ladder(vote) − ladder(gtr) on both sets.

**Decision.**
- **V-P1 holds:** the paper states that a structural check is a better label-free reward than a vote on these puzzles, with the reward-precision derivation (6.0 against 1.1) as the reason.
- **V-P1 fails:** the label-free result is stated as label-free RL in general. The check's role is then the gate and the precision, not the reward.

**Runs.** On the paper-extension server, two lanes (vote fold 0 and fold 1), each started when GPUs free up from the Granite runs (PREREG_GRLX).

## Result (2026-11-12 09:1x UTC)

Both vote folds trained 62 rounds and were evaluated on seeds 4–9 (`gp_eval.py --grl --extra lf=...,vote=...`, which now also prints the first extra against each later one, and `--quick q8b lf=... vote=... --seeds 4,5,6,7,8,9`).

| Qwen3-8B, seeds 4–9 | Ladder accuracy | Ladder ktok | Utility | Quick right count-1 | Quick wrong count-1 | Precision |
|---|---|---|---|---|---|---|
| GridPuzzle, base gtr | 69.6% | 18.31 | 60.5 | 31.9% | 6.8% | 82.4% |
| GridPuzzle, lf | 75.8% | 14.00 | 68.8 | 57.8% | 4.3% | 93.0% |
| GridPuzzle, vote | 71.9% | 16.35 | 63.8 | 46.7% | 5.8% | 88.9% |
| Mitra-Baral, base gtr | 88.5% | 9.71 | 83.6 | 49.6% | 4.3% | 92.1% |
| Mitra-Baral, lf | 90.2% | 6.85 | 86.8 | 70.7% | 4.3% | 94.3% |
| Mitra-Baral, vote | 90.2% | 8.78 | 85.9 | 62.2% | 3.2% | 95.1% |

- **V-P1 holds.** GridPuzzle ladder(lf) − ladder(vote): utility +5.0 [+2.9, +7.5] (accuracy +3.9 points, −2.35 ktok).
- **V-P2 holds.** GridPuzzle vote − base, wrong count-1: −1.0 [−3.1, +1.1], above lf's −2.5. Vote − lf, wrong: +1.5 [−0.7, +3.8], so the difference itself is not resolved.
- **V-P3 (reported).** Mitra-Baral ladder(lf) − ladder(vote): +1.0 [−2.8, +4.7]. Ladder(vote) − ladder(gtr): GridPuzzle +3.3 [+1.1, +5.5], Mitra-Baral +2.2 [−1.6, +5.9]. Quick step vote − lf, right count-1: GridPuzzle −11.1 [−15.0, −7.3], Mitra-Baral −8.5 [−14.4, −2.8].

**Decision (V-P1 holds).** The paper states that a structural check is a better label-free reward than a majority vote on these puzzles, with the reward-precision derivation (right : wrong 6.0 against 1.1 on GridPuzzle) as the reason.

**Not predicted.** The vote still lifts the quick step by +14.8 [+10.2, +19.5] points, although on the derivation it rewards right and wrong grids about equally. The training log shows why it is not neutral: in the last fold-0 round the vote rewarded 62.5% of samples while 20.3% were right, so most of its reward goes to agreement itself. Agreement still pushes the translator toward programs that run and pin down one grid: quick count-1 programs rose from 500 to 678 of 1,290 (lf: 802). That is the gain Spurious Rewards (2506.10947) and TTRL (2504.16084) also report from rewards with little information about correctness. The check's extra +11.1 points is the part that needs the check.
