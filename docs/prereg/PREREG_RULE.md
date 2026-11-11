# PREREG_RULE: the ladder's own escalations are turned into stated reading rules for the quick translation, registered 2026-11-11 18:1x UTC, before any run

**Why.** PREREG_CONV (2026-11-11 16:0x UTC) failed in a way that names its own cause.
- The ladder's escalations gave the right reading of "N houses between" (thinking expressions agree with the gold solution in all 115 compared pairs). The quick translation, shown up to 27 such examples, still wrote the phrase as adjacency: 61% and 85% misread, against 94–95% without memory.
- The same model follows a one-sentence stated rule: with the hand-written fact (`ZL_FACT`), 18% misread.
- So the open question is whether the model can state that rule itself from its own escalations, so that the ZebraLogic ladder no longer needs a fact we wrote after reading dev errors.

**The method (arm `trr`, `poc/run_zebra.py` and `poc/grid_score.clue_pairs(..., both=True)` as committed with this file).**
- Exactly as `trm` in PREREG_CONV: puzzles in order, one at a time. Where a puzzle's quick translation ends without a count of 1 and the ladder's thinking translation (the stored `trt` row of the same seed) reaches one, the clues the two programs read differently are found the same way.
- New: each such clue, not seen before, is sent to the quick model (Qwen3-8B, no thinking, `ZL_RULE`) with both expressions and the rules so far. It replies SAME, if a rule already gives the second reading, or one sentence starting "RULE:" that states the general reading rule behind the second expression.
- Every later quick translation gets the rules (`ZL_RULES`), not the examples. No template fact, no labels, same seeds, 3 rounds with count feedback.
- The rule calls' output tokens are paid at the puzzle where they are made. Nothing is tuned; every stated rule is kept.

**Runs (Qwen3-8B, seeds 1–3).** Cell A: ZL-AM, Amonkar et al.'s 100 puzzles (`q8bam`). Cell B: the 250 main puzzles unseen when the fact was written (`q8bh`, `--skip 10`). Ladder: quick step → `trt` → `think`, every step paid, a count of 1 stops; utility = 100·exact − 0.5·ktok; 95% bootstrap over puzzles, a puzzle's seeds together. `python poc/gp_eval.py --conv`.

**Stored baselines (same cells and seeds).**
- Cell B ladder: tr 92.1% at 3.15 ktok, trf (hand fact) 95.3% at 2.27 ktok, so trf − tr ≈ +3.6 utility. Cell A: tr 92.0% at 2.54 ktok.
- "Between" clues misread: tr 95% (A) and 94% (B); trf 18% (B).
- Quick count-1 precision: tr 89.3% (A) and 92.2% (B); trf 96.6% (B).

**Predictions.**
- **RULE-P1 (mechanism):** in `trr` programs with one expression per clue, "N houses between" clues read against the gold solution are at most 30% in each cell, counted from the first puzzle at which a rule was stated from such a clue. Gold is used only for this measurement.
- **RULE-P2:** `trr` quick count-1 precision is at least 95% in each cell.
- **RULE-P3 (decides):** ladder(`trr`) − ladder(`tr`), utility, cell B: the interval is above 0. Expected about +3: the fact's +3.6, less the puzzles before the first rule (the first "between" pair comes at the first escalated puzzle in every seed) and the rule calls. Cell A is reported with its own interval; its point should be above 0.
- **RULE-P4 (replaces the hand fact):** ladder(`trr`) − ladder(`trf`), cell B: the lower bound is above −2.0, as in CONV-P4.

**Decision.**
- **P3 and P4 hold:** the headline ZebraLogic ladder is restated without the hand-written fact. The method gains a third use of the free count: it admits the readings from which the model states its own rules.
- **P1 holds and P3 fails:** the mechanism works, but the gain is below this test's reach. Reported, no claim.
- **P1 fails:** a rule the model states itself does not move its own quick reading, and CONV's "a stated rule works" holds only for our sentence. Kill `trr`; the hand fact stays disclosed as dev-mined.
- Not claimed in any case: conventions the thinking translation also misreads (either/or on grids, the day window on trips), and GridPuzzle (forms rarely repeat; no run).

**Prior work.**
- **Hypotheses-to-Theories** (Zhu et al., 2310.07064) induces rules from training examples whose answers are checked against labels, then gives the rule library at deduction time.
- **TRAN** (Yang et al., 2310.15746) accumulates rules from the model's mistakes, which are found with ground truth.
- **LEAP** (Zhang et al., 2402.05403) states principles from mistakes the model makes on labelled few-shot examples.
- **Dynamic Cheatsheet** (2504.07952) curates its own memory with no external check.
- **Here:** a rule is induced only from a reading the solver's count admitted (exactly one solution where the cheap reading had not), with no label. Its teacher is the ladder's own expensive step on other puzzles, and it costs one short call per new clue.
