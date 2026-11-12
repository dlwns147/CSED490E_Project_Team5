# PREREG_GRLK: does RL on the quick grid translation reach puzzles the base model does not, or only sharpen it? Registered 2026-11-12 03:1x UTC, before any sample

**Why.**
- GRL (PREREG_GRL, result 2026-11-12 03:1x) raised the quick translation's right one-solution share on GridPuzzle from 31.9% to 55.2% per run, held out by cross-fitting.
- Yue et al. (2504.13837, read 2026-11-12) find that RL with verifiable rewards wins at small k but loses to the base model at large k on math and code: the trained model's coverage stays inside the base's, and narrows.
- The two readings give different papers. If the curves cross, RL here makes cheap sampling of what the base can already write, and a sampled-k gate at test time is the training-free rival. If they do not cross by large k, RL teaches readings that the base does not sample, and the claim is stronger.
- The stored runs cannot settle it: 6 trained runs per puzzle against 6 matched base runs (pass@6 46.0% vs 69.3% after 3 rounds) is small k.

**Method (`poc/gp_passk.py`, `poc/slurm/gpk_lane.sh`, committed with this file).**
- First round of arm `gtr` only (no feedback rounds), gtr's prompt and sampling (no thinking, temperature 0.7, top_p 0.95), cap 1536 tokens.
- N = 128 samples per puzzle, graded as GRL's reward: solver count 1 and the gold grid under scoring v2.
- Base Qwen3-8B on all 309 test puzzles (GridPuzzle 215, Mitra-Baral 94). Each fold's GRL adapter on its own held-out test puzzles only (fold files of PREREG_GRL), so every trained sample is still held out.
- pass@k for k = 1, 2, 4, …, 128 with the unbiased estimator; differences with a 95% bootstrap over puzzles. Command: `python poc/gp_passk.py --report gpkb0,gpkb1 gpkt0,gpkt1`.

**Expectation (before any run).** Base first-round pass@k from the stored runs grows slowly: 24.7% at k = 1 and 34.9% at k = 6 (seeds 4–9). A log-linear extrapolation gives about 45% at k = 128. The trained model is at 49.5% at k = 1 and 57.7% at k = 6.

**Predictions.**
- **GRLK-P1 (decides the claim).** GridPuzzle: trained pass@128 − base pass@128 has a 95% interval above 0.
- **GRLK-P2 (reported).** Mitra-Baral, the same difference; and the largest k at which the trained model is ahead on each set.
- **GRLK-P3 (reported).** Of puzzles the base never gets right in 128 samples, the number the trained model gets right at least once; and the reverse.

**Decision.**
- **P1 holds:** the paper states that RL on the cheap translation reaches puzzles outside the base model's 128-sample coverage, unlike Yue et al.'s math and code. The test-time sampled-k gate is not a rival at equal coverage.
- **P1 fails (the curves meet or cross by 128):** the paper states that RL sharpens within the base's coverage, as Yue et al. find. The next registered comparison is the training-free rival: k sampled quick programs gated by the count, against the trained translator, at equal tokens.

**Runs.** On the paper-extension server, four lanes: base fold 0 and fold 1 puzzles, trained fold 0 and fold 1.

## Result (2026-11-12 04:2x UTC): P1 holds; the trained translator is ahead at every k up to 128 on both sets

| pass@k (first round, 128 samples per puzzle) | k = 1 | 8 | 32 | 128 |
|---|---|---|---|---|
| GridPuzzle (215) base | 25.0% | 36.8% | 41.7% | 45.1% |
| GridPuzzle trained | 49.4% | 57.6% | 61.2% | 62.8% |
| GridPuzzle trained − base | +24.3 [+19.2, +29.8] | +20.9 [+15.3, +26.5] | +19.4 [+14.2, +25.0] | **+17.7 [+12.6, +23.3]** |
| Mitra-Baral (94) base | 43.1% | 56.1% | 60.7% | 62.8% |
| Mitra-Baral trained | 64.8% | 71.3% | 75.3% | 78.7% |
| Mitra-Baral trained − base | +21.7 [+14.3, +29.9] | +15.2 [+7.8, +23.3] | +14.6 [+6.5, +23.3] | **+16.0 [+7.4, +25.5]** |

- **P1 holds.** On GridPuzzle the gap narrows only slowly with k (+24.3 → +17.7). The base gains about 1.6 points per doubling at large k, so at that rate it would need about 11 more doublings to catch up. On Mitra-Baral the gap is flat to widening (+15.2 → +16.0).
- **P2 (reported).** The trained model is ahead at every k on both sets; there is no crossing up to 128.
- **P3 (reported).** GridPuzzle: the base is never right in 128 samples on 118 puzzles; the trained model gets 41 of them at least once, and loses 3 the base gets. Mitra-Baral: 35 never-right puzzles, 18 gained, 3 lost.
- **Precision per sample.** When a sample has exactly one solution, it is right 86.8% → 95.1% of the time on GridPuzzle and 94.3% → 98.7% on Mitra-Baral.
- **Decision (as registered).** RL on the cheap translation reaches puzzles outside the base model's 128-sample coverage, unlike Yue et al.'s math and code. Sampling more base programs and keeping one that has exactly one solution is not a rival at equal coverage: at k = 128 the base covers less than the trained model does at k = 1 on Mitra-Baral, and 45.1% against 49.4% on GridPuzzle.
- **Caveats.** This is a single prompt at temperature 0.7. Yue et al. use larger k (up to 1024) on other tasks. A likely reason the result differs here: the reward fixes systematic misreadings (for example the sign of "X less than Y", PREREG_GRL's example), which the base makes on nearly every sample of the same clue. Sampling cannot escape a misreading that every sample shares.
