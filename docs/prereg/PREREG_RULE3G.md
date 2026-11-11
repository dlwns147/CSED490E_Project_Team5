# PREREG_RULE3G: do PREREG_RULE3's checked rules carry to puzzles written by people (GridPuzzle, Mitra-Baral)? Qwen3-8B, seeds 4–6, registered 2026-11-11 23:2x UTC, before any run

**Why.**
- PREREG_RULE3 holds on ZebraLogic. Each rule is stated by the quick model from a reading that the solver count admitted, and kept only if it makes the quick translation reproduce that reading. With these rules the ladder matches the hand-written fact (+0.9 [−0.9, +3.0]) and beats no fact (+3.9 [+1.4, +6.5]).
- ZebraLogic's clues come from a few templates, and one template ("N houses between") causes most of the misreadings. If the method only works there, it is a fix for one generator, not a method. The paper's claim is domain-general.
- GridPuzzle (Tyagi et al. 2024, Puzzle Baron) and Mitra-Baral puzzles are written by people. Qwen3-8B's errors on them are spread over several phrasings. From the 48 wrong count-1 programs that passed the free checks on seeds 4–6 (PREREG_FREE result):
  - "X is 6 dollars less than Y" written with the wrong sign;
  - "the four X were A, B, C and D" written as "A is one of B, C, D" instead of "all different";
  - "of A and B, one is C and the other is D" mis-encoded;
  - a named value written as a number or a value of another category.
- **Measured on the stored seeds 1–3 (not these seeds):** the quick translation fails its count and the thinking translation reaches a count of 1 on 59–61 GridPuzzle and 27–30 Mitra-Baral puzzles per seed. On 30–33 and 16–19 of them, both programs have one expression per clue and the same VALUES, and some clues read differently (57–80 and 29–33 pairs per seed). So the stream has material to state rules from.
- **What an escalation costs here:** on seeds 4–6, the quick translation reaches a count of 1 on only 81–91 of 215 GridPuzzle puzzles. Every other puzzle pays the thinking translation, about 20k tokens (−10 utility).

**The method (arm `gtrrv`: `poc/run_zebra.py --gp q8b gtrr <seed> --check [--set lgp]`, as committed with this file).**
- As in PREREG_RULE3, from an empty start; the puzzles of the test split in file order.
- Pairs: `grid_score.gp_clue_pairs`. Both expressions are resolved as the solver resolves names (`gp_canon`: a value named by its number or letters, a first-category value as its number). They count as different if their truth differs on one of 300 random solutions (`gp_disagree`).
- Rule prompt (`ZL_RULE`) and rule list (`ZL_RULES`) unchanged. The check is the same as RULE3's: one quick translation of the same puzzle with the rule must write that clue as the thinking translation did (same VALUES, `gp_disagree` False).

**Runs.** Qwen3-8B, the GridPuzzle test split (215) and the Mitra-Baral test split (94), seeds 4, 5, 6. `gtr`, `gtrt` and `think` of these seeds are stored and unchanged. Ladder: quick step → `gtrt` → `think`, every step paid, rule calls paid at their puzzle. All grids are scored by scoring v2 (`grid_score.score`). 95% bootstrap over puzzles, a puzzle's seeds together. `python poc/gp_eval.py --rule3g`.

**Predictions.**
- **RULE3G-P1 (decides; no harm):** ladder(`gtrrv`) − ladder(`gtr`), lower bound above −2.0 on both sets.
- **RULE3G-P2 (mechanism):** on GridPuzzle, the quick step reaches a count of 1 on more puzzle-seeds with the rules than without (pooled over seeds). Its precision is not more than 2 points lower.
- **RULE3G-P3:** GridPuzzle: interval of ladder(`gtrrv`) − ladder(`gtr`) above 0.
- **Derivation.**
  - On ZebraLogic the rules raised the quick count-1 rate from 64% to 79% of puzzle-seeds. Here the misreadings are spread over more phrasings, so I expect a third to a half of that: 5 to 8 points.
  - Each converted puzzle saves about 10 utility of thinking-translation tokens. It may also gain accuracy, because the escalated puzzles that reach `think` are 60% right.
  - Expected: +0.5 to +1.5 on GridPuzzle, about 0 on Mitra-Baral (fewer escalations, 94 puzzles). Interval half-width about 2. So P3 will probably fail, and P1 is the test.
  - A wrong rule can lower the reading, as in RULE2. The check is the guard against that.

**Decision.**
- **P1 and P2 hold:** the rules are stated as carrying to human-written puzzles: no loss, more quick count-1. If P3 holds too, they are stated as a gain there.
- **P1 fails:** the method is stated as specific to template-generated clues (ZebraLogic), and the cause is analysed from the kept rules.
- **P1 holds, P2 fails:** the rules do not carry; reported as no effect.

**Prior work.** As PREREG_RULE3: HtT (2310.07064) and RIMRULE (2601.00086) keep rules by labelled accuracy; AutoManual (2405.16247) by environment feedback. Here the reference is the reading that the count admitted, and the check uses no label.
