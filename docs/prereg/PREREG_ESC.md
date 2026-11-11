# PREREG_ESC: choose the escalation step from the failed count, registered 2026-11-11 14:5x UTC, before the evaluation below is run

**Why.** On GridPuzzle the ladder's lead splits by where it stops (FINDINGS 2026-11-11 14:5x). Stops at the quick translation gain; puzzles sent on to thinking lose, because they pay both translations first. For the stronger thinkers the middle step (the thinking translation) is a net loss:
- gpt-oss-120b: its thinking translation costs 10.2 ktok, more than its thinking (9.1 ktok); the ladder ties thinking (GP-120-P2 fails).
- gpt-oss-20b: a ladder without the middle step would do better (+7.4 against +3.9).
- On trips the ladder's cost is its middle step (FINDINGS 2026-11-10).

The fixed three-step ladder runs the middle step on every failed count, whatever it costs that model.

**What the stored runs show (read on test before this file; descriptive).** The value of running the middle step before thinking, for a puzzle-seed whose quick count failed, depends on the model and on how the count failed:
- **No solution:** the model wrote a contradiction, which a careful re-translation can fix. Middle-step stop rates are 46–63% on GridPuzzle, and the value is positive for three of four models.
- **Several solutions:** a constraint is missing, which thinking rarely restores (idea 35). gpt-oss-20b's middle step stops only 18% of these, at −15.4 utility each.
- **No count** (no program or a crash).
- These per-outcome values were seen on the full test set. The evaluation below is therefore out-of-sample by construction (cross-fitting), not by my blindness.

**The rule (arm ESC, `python poc/gp_eval.py --esc --score2`, `esc_main` as committed with this file).**
- After the quick step's count fails, look up the outcome: no solution, several, or no count.
- Run the middle step only if its mean value for that outcome, on puzzles other than this one, is at least 0. Otherwise go straight to thinking.
- Value of the middle step = utility(middle step, then thinking if its count is not 1) − utility(thinking). The quick step's tokens are paid either way.
- This is the Bayes decision for the next step given the free signal, with the two expectations estimated from the other puzzles. No threshold is tuned.
- **Estimation:** 2-fold cross-fitting over puzzles. The value is learned on one half and applied to the other, then swapped. This is repeated over 20 random splits (seed 0), and each puzzle's ESC utility is its mean.
- An outcome with no training case keeps the middle step. Labels enter only through the training half's utilities, as for any learned cascade.
- **Cells (utility, 95% bootstrap over problems, seeds together):**
  - GridPuzzle and Mitra-Baral × Qwen3-8B, Qwen3-32B-AWQ, gpt-oss-20b, gpt-oss-120b (plain ladder, scoring v2);
  - Amonkar et al.'s 100 trips × Qwen3-8B, Qwen3-32B-AWQ, gpt-oss-20b, gpt-oss-120b (trc → trct → think).
- No new model call.

**Prior work.**
- FrugalGPT (Chen et al., 2305.05176) learns cascade thresholds on a scorer.
- AutoMix (Madaan et al., 2310.12963) routes on a self-verification estimate with a POMDP.
- Dekoninck et al. (2410.10347) derive the optimal cascade/routing strategy from quality and cost estimates, and show that it depends on the quality of those estimates.
- **Here:** the signal is exact and free (a solver count and how it failed), the steps are a translation and thinking, and the choice is per outcome. The novelty is the signal, not the decision rule.

**Predictions.**
- **ESC-P1 (decides).** ESC − fixed ladder: the point is at or above −0.5 in every one of the 12 cells, and the interval is above 0 for GridPuzzle with gpt-oss-20b and with gpt-oss-120b.
  - Derivation: the rule drops the middle step only where its held-out value is negative. Where that value is clearly negative (gpt-oss-20b several: −15.4; gpt-oss-120b, all outcomes: −4 to −9), dropping it gains the escalated share times that value: about 0.18 × 15 ≈ +2.7 and 0.24 × 7 ≈ +1.6.
  - Where the value is near 0, the cost is only the estimation noise of a half-sample.
- **ESC-P2.** GridPuzzle, gpt-oss-120b, ESC − think: the point is above 0 (fixed ladder: −0.0).
- **ESC-P3.** Trips: ESC − fixed ladder ≥ 0 at the point for all four models.

**Decision.**
- **P1 holds:** the paper's ladder becomes ESC. The fixed three-step ladder is reported as the ablation, and GP-120 is restated with ESC (the fixed-ladder tie stays reported).
- **P1 fails in some cell, with an interval below 0:** the per-outcome estimates overfit at these sample sizes, and the fixed ladder stays. I then report which outcome's estimate flipped.
- **P1 fails only because an interval for gpt-oss-20b or gpt-oss-120b crosses 0, with every point ≥ −0.5:** the rule is safe but its gain is not resolved, and the fixed ladder stays as the headline.
