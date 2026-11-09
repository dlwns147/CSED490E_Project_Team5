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

### 2026-11-08 07:4x UTC: all three seeds complete (Qwen3-8B, 250 held-out puzzles)

| Arm | Accuracy | Output tokens |
|---|---|---|
| think, 32,000 | 81.3% | 6,627 |
| trf | 76.3% | 500 |
| trt | 91.6% | 3,367 |
| ladder trf → trt → think | 95.3% | 2,267 |

- **ZL-P1 holds:** ladder minus think utility +16.18 [+11.74, +20.96].
- **ZL-P2 holds:** ladder minus think accuracy +14.0 [+9.7, +18.5], far above −2.
- **ZL-P3 holds:** a count of 1 is right 561 of 581 times for trf (96.6%) and 686 of 689 for trt (99.6%).
- **ZL-P4 holds:** on puzzles with more than 20 cells, trt 82.8% against think 46.7%, +36.1 [+23.3, +48.9]. The set has 60 puzzles, not the 50 I wrote: six sizes have more than 20 cells (4×6, 5×5, 5×6, 6×4, 6×5, 6×6), not five. No think row hit the 32,000 cap.

Every prediction holds. By the registered decision, the next step is all puzzles and a second model (below). Our think accuracy, 81.3%, is near the Qwen3 report's 84.8 for the same model, so our thinking baseline is not weak.

## ZL-FULL: the remaining 500 puzzles and Qwen3-4B (written 2026-11-08 07:4x UTC, before any run)

**Why.** The decision above. The held-out result could still depend on these 250 puzzles or on one model.

**Set.**
- **ZL-F8:** Qwen3-8B on the remaining 500 puzzles (`--skip 20 --per 20`: puzzles 21–40 of each size), seeds 1–3, arms trf, trt, think at 32,000, the same code and prompts as above.
- **ZL-F4:** Qwen3-4B on the 250 held-out puzzles, seeds 1–3, the same arms. The Qwen3 report gives Qwen3-4B 81.0 with thinking.

Intervals: bootstrap over puzzles, 95%, each puzzle's mean over seeds.

**Predictions.**
- **F-P1:** ZL-F8 ladder utility exceeds think, interval above 0.
- **F-P2:** ZL-F8 ladder accuracy at least think minus 2 (lower bound above −2).
- **F-P3:** ZL-F4 ladder utility exceeds think, interval above 0.
- **F-P4 (reported):** a count of 1 right at least 95% of the time for each model and translation arm.
- **F-P5 (reported):** Qwen3-8B ladder accuracy over the 750 puzzles never read while writing `ZL_FACT` (30 of each size, so the size mix of the full set), beside Logic.py's 91.4 (Llama 3.1 70B, all 1,000) and the Qwen3 report's 84.8 (thinking). The first 250 are left out because `ZL_FACT` was written from them.

**Decision.** F-P1 and F-P3 hold: the ladder is our claim on ZebraLogic for both models, stated as a cost gate in front of thinking (SatLM, Logic-LM and Logic.py named above for the check itself), and the next question is real text (AR-LSAT, idea 18). F-P1 fails: the held-out result depended on those 250 puzzles, and it is reported as such. F-P3 fails alone: the claim is limited to Qwen3-8B.

## ZL-OSS: a second model family, gpt-oss-20b (written 2026-11-08 23:5x UTC, before any run)

**Why.** Both models so far are Qwen3. The gate pays only where the translation's precision on the puzzles it accepts beats the thinker's accuracy on those same puzzles (idea 15's identity; on AR-LSAT the thinker was the stronger one, 93.1% against 90.6%, and the gate tied). gpt-oss-20b is a different family with a different training recipe, and at high effort it should be a stronger thinker than Qwen3-8B. That makes it a harder test of the gate.

**Set.** gpt-oss-20b (MXFP4, one RTX 3090 per seed, 24,576-token context), the same 250 held-out puzzles as the first test (`--skip 10`), seeds 1–3, the same prompts and code. Effort maps onto the Qwen arms:
- `trf` (translation, no thinking) at low effort;
- `trt` (translation with thinking) at medium effort;
- `think` at high effort, capped at 22,000 tokens.

The ladder is trf → trt → think, as before. Tokens include reasoning tokens. Intervals: bootstrap over puzzles, 95%, each puzzle's mean over seeds.

**Predictions.**
- **O-P1:** ladder utility exceeds think (high), interval above 0.
- **O-P2:** ladder accuracy at least think minus 2 (lower bound above −2).
- **O-P3 (reported):** a count of 1 right at least 95% of the time for trf and trt.

**Decision.**
- **O-P1 holds:** the ZebraLogic claim is stated for two families.
- **O-P1 fails:** the claim is stated for Qwen3 only. The report gives the gate's precision and the thinker's accuracy on the accepted puzzles, which say why.

### Results, 2026-11-09 00:5x UTC: ZL-F4 (Qwen3-4B) and ZL-OSS (gpt-oss-20b), all three seeds complete

| Model | Ladder trf → trt → think | Think | Utility, ladder − think | Accuracy, ladder − think |
|---|---|---|---|---|
| Qwen3-4B | 95.5% at 3.03k | 81.5% at 6.39k | +15.68 [+11.67, +19.93] | +14.0 [+10.1, +18.0] |
| gpt-oss-20b (low / medium / high effort) | 98.7% at 1.09k | 75.3% at 8.26k | +26.92 [+22.11, +31.83] | +23.3 [+18.9, +27.9] |

- **F-P3 holds** (Qwen3-4B).
- **O-P1 and O-P2 hold** (gpt-oss-20b).
- **F-P4 (Qwen3-4B part) and O-P3 hold.** A count of 1 is right as follows:
  - Qwen3-4B: trf 444 of 460 (96.5%), trt 666 of 670 (99.4%).
  - gpt-oss-20b: trf 734 of 737 (99.6%), trt 734 of 739 (99.3%).

**gpt-oss-20b, read in the raw rows.**
- Its translation alone at low effort solves 98.8% of the puzzles at about 700 tokens. A count of 1 accepts 98% of them.
- Thinking at high effort hit the 22,000-token cap on 132 of 750 runs (all wrong, no grid). The other 53 wrong runs gave grids with some cells wrong.
- The cap hurts thinking. But even if every capped run had been right, thinking would reach 92.9%, below the ladder's 98.7%. So the verdict doesn't depend on the cap.
- On the puzzles trf accepts, thinking is right on 76.1%, against the gate's 99.6%. That gap is where the ladder's gain comes from (idea 15).

For Qwen3-4B the same comparison is 88.5% against 96.5%.

ZL-F8 (Qwen3-8B, F-P1, F-P2, F-P5 and the Qwen3-8B part of F-P4) is still waiting on its thinking runs (483–490 of 500 rows written).
