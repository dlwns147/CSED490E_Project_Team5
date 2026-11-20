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

**Addendum F-4, second family (written 2026-11-18 21:4x UTC, before any Qwen3-32B Futoshiki output exists).** Qwen3-32B (AWQ) on the same
300 test puzzles, seed 1: trc, trct (30k), think (30k). Ladder trc → trct → think. Third for the blind estimate: gpt-oss-20b's quick
translation. Pilot evidence is only Qwen3-8B, whose translations almost never reached one solution, so: F-4a: Qwen3-32B's ladder − its
thinking ≥ 0 (lower bound above −2); F-4b: the blind estimate, logged before scoring, within max(3.0, 10% of the measured term).

**F-2 blind prediction, gpt-oss-120b (logged 2026-11-18 22:4x UTC, before any of its scores was read).** Baselines: thinking at the 30k
cap on 0 / 6 / 27 (medium) and 10 / 68 / 99 (high) of 100 at 5 / 7 / 9. Quick translations reach one solution on 36 / 3 / 1, thinking
translations on 78 / 64 / 63; the ladder accepts 71%, the third (gpt-oss-20b quick) answers 6% of those.
- vs thinking at medium effort: **predicted accuracy term +41.7** (rule A +43.3), token term −1.73.
- vs thinking at high effort: **predicted accuracy term +39.7** (rule A +41.0), token term +0.90.

**gpt-oss-120b result and verdict (2026-11-18 22:4x UTC; `python3 results/tmp_futo_score.py oss120`, after the prediction was committed).**
Thinking: medium 35.7% at 17.7k (utility 26.8), high 38.0% at 25.7k (25.1); baseline = medium. **Ladder 77.0% at 21.2k: ΔU +39.6
[+33.4, +45.8]. Measured accuracy term +41.3 vs predicted +41.7** (error 0.4). By size: 5×5 92 vs 57, 7×7 71 vs 35, 9×9 68 vs 15.
- **F-1 holds for both models** (+35.1, +39.6). **F-2 holds in both cells** (errors 2.3 and 0.4). F-3 holds for gpt-oss-20b (largest gain at
  7×7) and fails for gpt-oss-120b (largest at 9×9, where its thinking falls to 15% but its translation stays at 68%).
- **Decision: the method and the label-free rule are shown on an untouched domain with large room.** With PREREG_KK (no room, the
  estimate predicting the loss), both sides of the rule now hold on domains no choice touched. Qwen3-32B (F-4) is running.

**Addendum F-5, program-of-thought baseline (written 2026-11-19 04:0x UTC, before any `pot` output exists).** The closest prior method
for search puzzles is to have the model write the whole solver (PAL, Gao et al. 2211.10435; Program of Thoughts, Chen et al. 2211.12588):
one ```python program that searches and prints the grid, with thinking at medium effort (30k); its printed grid is the answer, no check,
no escalation. Same 300 test puzzles, seed 1; gpt-oss-20b first, gpt-oss-120b after (arm `pot`, tags `oss20M`, `oss120M`).
- F-5: our ladder − program-of-thought > 0 (interval above 0) for each model. Reason: the solver is not the hard part; reading the
  picture is, and the ladder's count check rejects misread translations and escalates, while a program-of-thought answer is accepted as
  printed. If program-of-thought wins, the report says the gain comes from code execution itself, not from the count check.

**F-4b blind prediction, Qwen3-32B (logged 2026-11-19 04:0x UTC, before any Qwen3-32B score was read; the 9×9 thinking run was moved
between GPUs with `--resume`, 100 unique ids per file checked).** Thinking at the cap on 9 / 26 / 39, parsed 94 / 90 / 83. Quick
translations reach one solution on 4 / 0 / 0, thinking translations on 44 / 6 / 0; the ladder accepts 17%, the third answers 15% of those.
**Predicted accuracy term +14.3** (rule A +15.3); token term −10.50 (the failed thinking translations cost tokens before thinking).

**Qwen3-32B result (2026-11-19 04:0x UTC; `python3 results/tmp_futo_score.py q32`, after the prediction above was committed).**
Thinking 3.7% at 24.6k (74 of 300 at the cap); ladder 15.0% at 45.6k; **ΔU +0.8 [−3.5, +5.4]; measured accuracy term +11.3 vs predicted
+14.3** (error 3.0, at the bar max(3.0, 1.1): F-4b holds). F-4a fails (lower bound below −2): the ladder gains 11 points of accuracy, all
at 5×5 (41 vs 11; 7×7 4 vs 0, 9×9 0 vs 0), and pays for it with failed thinking translations (+21k tokens per puzzle). Qwen3-32B reads the
Futoshiki picture into constraints far less often than gpt-oss (thinking translations one-solution on 44 / 6 / 0 vs gpt-oss-20b's 89 / 68 /
38), so on this domain the method pays only for models whose translation succeeds; the label-free estimate saw that before scoring.

**F-5 first run invalid (2026-11-19 05:1x UTC).** Read before deciding anything: program-of-thought scored 12.7% / 12.0%, but the harness
was at fault, not only the method: the code extractor also took untagged blocks, so a final answer grid written in an untagged block was run
as code (50 SyntaxErrors for gpt-oss-120b); 87 programs printed output the grid reader could not parse (output not stored, so it cannot be
checked); 11 imported z3, which the sandbox lacks. Fixes: python-tagged blocks first, the program's output stored, a fallback reader (the
last n² numbers), and the prompt names the allowed libraries (standard library or OR-Tools, the solver our harness itself uses). The same
extractor change applies to future translation runs; the registered test's translation runs used the old one, which can only have hurt the
ladder. Rerun of F-5 with the fixed harness; the prediction and decision rule are unchanged.

**F-5 result, rerun with the fixed harness (2026-11-19 06:1x UTC; `POT_SUFFIX=2 python3 results/tmp_futo_pot.py oss20 oss120`).**
Failure categories read first: gpt-oss-20b's programs: 140 of 300 gave no code (reasoning ran to the 30k cap, 139), 146 ran, of which 70
printed "No solution found"; gpt-oss-120b: 257 ran, 121 printed "No solution found" (the program encodes a misread picture and searches
it, with nothing to send it back). Program-of-thought 19.0% at 22.6k / 33.7% at 8.9k. **Ladder − program-of-thought +38.4 [+30.4, +45.9]
(gpt-oss-20b), +37.2 [+29.7, +44.3] (gpt-oss-120b): F-5 holds.** Reading the picture is the hard part for both; what the ladder adds is
the count check that sends a contradictory reading back and, failing that, falls back to thinking.

*Scripts (2026-11-21 22:39 UTC):* the scorer, the blind predictor and the program-of-thought scorer are committed as poc/analyze_futo_score.py,
poc/analyze_futo_pred.py and poc/analyze_futo_pot.py (identical to the results/tmp_futo_*.py copies named above).
