# Pre-registration: ZebraLogic ladder on held-out puzzles (ZL)

Written before any held-out output exists. Idea 14 in `docs/notes/IDEAS_COMPUTATION.md`.

**Why.** The pilot (first 10 puzzles of each of the 25 sizes, Qwen3-8B, seed 1) suggests a translate-then-check ladder beats thinking on both accuracy and tokens. But the fact added to the prompt (`ZL_FACT`) was written after reading failures on those same puzzles, and thinking was capped at 16,000 tokens. This run removes both problems.

**Prior work, read before this.** The count check is not ours. SatLM (2305.09656) names UNSAT and AMBIG outcomes and abstains on them, and leaves re-prompting to future work. Logic-LM (2305.12295) repairs on solver errors, and ZPS (2407.03956) feeds solver output back for zebra puzzles. Logic.py (2502.15776, 91.4% with Llama 3.1 70B on ZebraLogic) names the ambiguity check and does not implement it. The claim tested here is narrower: with a current reasoning model, whether that check works as a cost gate in front of thinking. None of those papers compares against a thinking model or reports tokens.

**Setup.** Qwen3-8B. Puzzles: the next 10 of each size (`--skip 10`), 250 puzzles, none read while writing `ZL_FACT`. Seeds 1, 2, 3. Temperature 0.7.

- `trf`: translate, no thinking, with `ZL_FACT`, up to 3 rounds with label-free feedback.
- `trt`: translate with thinking, 8,192 tokens a round, no `ZL_FACT`, up to 3 rounds.
- `think`: thinking, 32,000 tokens.
- **Ladder:** `trf`; if the count is not 1, `trt`; if the count is not 1, `think`. Tokens of every step paid are counted. Composed offline from the three arms on the same puzzle and seed.

Utility per puzzle = 100·right − 0.5·ktok. Intervals: bootstrap over the 250 puzzles, 95%, with each puzzle's mean over seeds.

**Predictions.**

- ZL-P1: ladder utility exceeds `think`, interval above 0.
- ZL-P2: ladder accuracy is at least `think` minus 2 points (interval lower bound above −2).
- ZL-P3: a count of 1 is right at least 95% of the time, for `trf` and for `trt` (point estimates; pilot 96.4%, 98.1%).
- ZL-P4: on the 50 puzzles with more than 20 cells, `trt` accuracy exceeds `think` accuracy at 32,000 tokens, interval above 0. The pilot's think arm was capped at 16,000 and unfinished there, so this is the least certain.

**Decision.** If P1 and P2 hold, run all 1,000 puzzles and a second model, and report against Logic.py and the Qwen3 report's 84.8 (Qwen3-8B thinking). If P1 fails, the ladder is a tie and stays a pilot. P4 alone decides only whether the thinking step of the ladder can be dropped.

**Limits stated now.** ZebraLogic clues come from a small set of templates, so translation is easier here than on real text; `ZL_FACT` is a fact about those templates. AR-LSAT (real text, pilot running alongside) tests whether the check survives that. Utility prices all tokens alike and ignores solver seconds.

## Results
