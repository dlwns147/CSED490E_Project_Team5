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
