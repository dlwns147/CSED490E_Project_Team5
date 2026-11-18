# PREREG_FUTO — Futoshiki: a new domain where thinking is weak; does the ladder win, and does the blind estimate hold?

Written 2026-11-18 17:4x UTC, before any test-puzzle output exists.

**Why.** Knights and Knaves (PREREG_KK) tested only the "no room" side: thinking was at 95–100%. Here thinking fails (pilot), so this tests
the other side of both claims on an untouched domain: the ladder wins where thinking is weak and translation succeeds, and the label-free
estimate predicts the gain before labels.

**Known from the pilot (exploratory, 60 puzzles per size, generator seed 101; `results/futo_*_pilot_*`).** gpt-oss-20b thinking: 52 / 3 / 0%
at 5 / 7 / 9 (high effort, mostly at the 30k cap); medium effort 18% at 7×7. Its thinking translation (picture-parsing code allowed, 30k):
high effort 93% at 5×5, 23% at 7×7 (reasoning eats the budget), medium effort 70% at 7×7 (26 of 27 one-solution programs right), 42% of the
first 12 at 9×9. Quick translations 12–20% at 5×5, near 0 above. Qwen3-8B: thinking 10 / 0 / 0%, translations nearly never one solution;
not in the test. Runner and harness fixed after the pilot (`poc/run_futo.py`: CP-SAT count, round text kept).

**Run.** 300 new puzzles (Reasoning Gym `futoshiki`, difficulty 3, generator seed 202, sizes 5 / 7 / 9 × 100; every puzzle checked to have
exactly one solution equal to the stored one; none equal to a pilot puzzle). Seed 1. gpt-oss-20b and gpt-oss-120b, each: `trc` (low
effort), `trct` (medium effort, 30k), `think` at medium and at high effort (30k). Ladder: trc → trct → think (the better thinking
setting), accept at the first program with exactly one solution. Baseline = the thinking setting with the higher utility (PREREG_X56 rule).

**Predictions (utility, paired bootstrap over the 300 puzzles).**
- F-1: each model's ladder − its best thinking > 0, interval above 0; gpt-oss-20b by more than +20.
- F-2 (the label-free estimate, decisive): before reading any score, the hybrid estimate of each ladder's accuracy term (third = the other
  gpt-oss model's quick translation, its answer used where its count is 1, else trust the accepted answer) is logged with the time. Holds if
  it is within max(3.0, 10% of the measured term) of the measured accuracy term in both cells. (The bar is wider than PREREG_KK's 2.0
  because the terms here are expected to be several times larger, and the third covers few items.)
- F-3: by size, the ladder's gain is largest at 7×7 (thinking ~0–20%, translation ~70%).

**Decision.** F-1 and F-2 hold → the method and the label-free rule are shown on an untouched domain with large room. F-1 holds, F-2
fails → the method stands, the estimate does not transfer to low-coverage thirds. F-1 fails → reported as a loss with the cause.

**F-2 blind prediction, gpt-oss-20b (logged 2026-11-18 21:4x UTC, before any test score was read; `python3 results/tmp_futo_pred.py oss20`,
which reads only count, ans and tokens).** Baselines: thinking at the 30k cap on 24 / 71 / 81 (medium) and 40 / 94 / 100 (high) of 100
puzzles at 5 / 7 / 9; quick translations reach one solution on 14 / 1 / 0, thinking translations on 89 / 68 / 38. The ladder accepts 66%;
the third (gpt-oss-120b quick translation) answers 18% of those.
- vs thinking at medium effort: **predicted accuracy term +46.3** (rule A +47.0), token term −8.87.
- vs thinking at high effort: **predicted accuracy term +47.7** (rule A +48.7), token term −7.35.
gpt-oss-120b's prediction waits for its thinking runs.

**gpt-oss-20b result (2026-11-18 21:4x UTC; `python3 results/tmp_futo_score.py oss20`, after the prediction above was committed).**
Thinking: medium 23.0% at 24.1k (utility 11.0), high 20.7% at 28.2k (6.5); baseline = medium. **Ladder 67.0% at 41.8k: ΔU +35.1
[+28.1, +42.0]** (F-1 holds, above +20). **Measured accuracy term +44.0 vs predicted +46.3** (error 2.3, within max(3.0, 4.4): F-2 holds
for this cell). By size, ladder vs thinking: 5×5 90 vs 52, 7×7 72 vs 16, 9×9 39 vs 1 (F-3: the gain is largest at 7×7, holds). The
ladder costs more tokens (the 9×9 thinking translation alone averages 47.6k over its rounds) and still gains 35 utility points.
