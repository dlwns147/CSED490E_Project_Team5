# PREREG_RULE4: keep a stated rule only if it changes the reading (with the rule the clue reads as admitted, without it, same seed, it does not); GridPuzzle, Mitra-Baral and ZebraLogic, registered 2026-11-12 00:2x UTC, before any run

**Why.**
- PREREG_RULE3G: the checked rules helped on GridPuzzle (+1.9 [−0.7, +4.6]) but failed the no-harm bound on Mitra-Baral (−0.9 [−4.4, +2.8]).
- The Mitra-Baral rules were mostly generic, for example "when a clue relates two entities, equate their values", restated for each new pair of categories.
- RULE3's check asks only whether the quick translation, given the rule, reproduces the admitted reading. A rule that says nothing passes whenever that translation reads the clue right anyway, and at temperature 0.7 it often does: the misreading that produced the pair can be a sampling accident.
- The fix is a counterfactual. The same quick translation, with the same seed and the rule list without the new rule, must still misread the clue. Then the rule is kept only if it is what changes the reading. This costs one more quick translation per stated rule that passes the first check.

**The method (arms `gtrrc` and `trrc`: `run_zebra.py --gp q8b gtrr <seed> --check --cf [--set lgp]` and `--zl q8bh trr <seed> --skip 10 --check --cf`, as committed with this file).** Everything else is RULE3's, from an empty start.

**Runs (Qwen3-8B).**
- GridPuzzle (215) and Mitra-Baral (94) test splits:
  - fresh seeds 7, 8, 9 with `gtr`, `gtrt`, `think` (`--max_tokens 32000`), `gtrrv` and `gtrrc`;
  - seeds 4–6 with `gtrrc` added to the stored arms.
- ZebraLogic: `trrc` on the 250 unseen puzzles, seeds 7–9, against the stored `trf` and `trrv`.
- Ladder, scoring and bootstrap as RULE3G and RULE3. `python poc/gp_eval.py --rule3g --rule4` (seeds 4–9; `--seeds 7,8,9` for the fresh seeds alone) and `python poc/gp_eval.py --conv --rule3`.

**Predictions.**
- **RULE4-P0 (mechanism):** on each GP set, `gtrrc` keeps fewer rules than `gtrrv` on the same seeds, pooled over seeds 7–9.
- **RULE4-P1 (decides):** ladder(`gtrrc`) − ladder(`gtr`), lower bound above −2.0 on both GP sets, seeds 4–9 pooled.
  - Six seeds, because three on 94 puzzles gave a half-width of 3.6. With that width, a −2.0 bound needs a point above +1.6. Seeds 4–6 were seen for `gtrrv` only; `gtrrc`'s outcomes there are unseen.
- **RULE4-P2:** GridPuzzle quick count-1 higher with `gtrrc` than with `gtr` (seeds 4–9 pooled), and precision not lower by more than 2 points.
- **RULE4-P3:** GridPuzzle: the interval of ladder(`gtrrc`) − ladder(`gtr`) is above 0 (seeds 4–9).
- **RULE4-P4:** ZebraLogic: ladder(`trrc`) − ladder(`trf`), lower bound above −2.0 (seeds 7–9). The counterfactual must not cost the ZebraLogic result. There the clue is misread 95% of the time without a rule, so right rules should rarely be rejected.
- **Derivation.**
  - The counterfactual removes rules that do not change a reading. On Mitra-Baral those were most kept rules, so I expect a point of 0 to +1 there, against −0.9.
  - On GridPuzzle, rules for real misreadings stay ("N months before", value equality), so about +1.5 to +2, as with `gtrrv`.
  - Six seeds should bring the Mitra-Baral half-width to about 2.5–3. P1 is therefore uncertain on Mitra-Baral even if the mechanism works.

**Decision.**
- **P1, P2 and P4 hold:** the rule method is stated as carrying to human-written puzzles, with the counterfactual check as part of it, and `trrc` replaces `trrvw` as the ZebraLogic arm only if P4 holds. If P3 holds too, it is stated as a gain on GridPuzzle.
- **P1 fails:** the rule method stays stated for ZebraLogic only.
- **P0 fails:** the counterfactual does not remove rules, and the result is not read as its effect.

**Prior work.** As PREREG_RULE3. Ablation-style acceptance (keep a component only if removing it changes the outcome) is standard. Here it is applied per rule, on the reading of one clue, with the reading that the count admitted as the reference and no label.

## Result (2026-11-12 02:0x UTC): P1 fails on Mitra-Baral, P4 holds; the rule method stays stated for ZebraLogic only

The verdict is final: P1 needs both sets, and Mitra-Baral's seeds 4–9 are complete. GridPuzzle seeds 7–9 are still running. They decide only P0 on GridPuzzle and the reported P2 and P3, which will be added as an addendum.

| Prediction | Result | Verdict |
|---|---|---|
| P0, Mitra-Baral (seeds 7–9) | `gtrrc` kept 16 rules, `gtrrv` 22 (seeds 4–9: 35 and 51) | holds |
| P0, GridPuzzle | seeds 4–6 so far: 25 against 51 | pending (7–9) |
| P1, Mitra-Baral (seeds 4–9, 564 puzzle-seeds) | ladder(`gtrrc`) − ladder(`gtr`) −0.3 [−2.8, +2.2]; fresh seeds 7–9 alone −0.3 [−3.0, +2.3] | **fails** (lower bound below −2.0) |
| P1, GridPuzzle | seeds 4–6 so far: +1.3 [−1.3, +3.9] | pending, cannot change the verdict |
| P4, ZebraLogic (seeds 7–9, 750) | ladder(`trrc`) − ladder(`trf`) +0.3 [−1.8, +2.5] | holds |

**Reported.**
- Mitra-Baral, seeds 4–9: `gtrrv` − `gtr` −0.6 [−3.2, +2.1]; `gtrrc` − `gtrrv` +0.2 [−1.5, +2.0]. Quick count-1 precision: `gtr` 92.1%, `gtrrv` 89.4%, `gtrrc` 90.5%.
- ZebraLogic: `trrc` − `trrv` −0.9 [−2.2, +0.4]. `trrc` shows 3.2 rules per puzzle against 7.3 and misreads "N houses between" in 12% of clues against 17%.
- GridPuzzle seeds 4–6: `gtrrc` 71.0% at 17.97 ktok, `gtrrv` 71.2% at 16.97, `gtr` 69.8% at 18.05. Quick count-1 precision 85.9%, 84.5% and 80.5%.

**Reading.**
- The counterfactual does what P0 said: it keeps about a third fewer rules on Mitra-Baral and half as many on GridPuzzle.
- On Mitra-Baral it moved the point from −0.6 to −0.3, not to the 0 to +1 derived. With a half-width of 2.5, a no-harm bound of −2.0 needs a point above +0.5. A method whose best case on this set is "no harm" cannot pass that test on 94 puzzles.
- What the data do say: the rules bring no gain on Mitra-Baral. The quick translation there is already 92% precise, and its errors do not repeat in a way one stated rule can fix.
- **Decision as registered:** P1 fails, so the rule method stays stated for ZebraLogic only, and `trrc` does not replace `trrvw` there (that needed P1, P2 and P4).
- The rule line ends here for human-written puzzles. Two registrations (RULE3G, RULE4) failed on the same set, and a third would be a knob variant.
