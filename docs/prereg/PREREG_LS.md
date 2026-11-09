# Pre-registration: declarations-only translation as a gate on AR-LSAT (LS)

Written 2026-11-08 09:5x UTC, before any test-split output of this arm exists. Idea 18 in `docs/notes/IDEAS_COMPUTATION.md`.

**Why.** On ZebraLogic the translate-and-count ladder beats thinking (`PREREG_ZL.md`), but ZebraLogic clues come from templates. On AR-LSAT (real LSAT text) the same ladder tied with thinking, because the model's programs crashed on about half the questions and one marked option covered only 26–40%. Arm `trs` has the model write only declarations (candidate arrangements, one predicate per rule, the question's condition, one predicate per option, the question kind); the harness enumerates, applies could/must/cannot/EXCEPT, and counts a predicate that raises as False.

**Development, on the dev split only (231 questions, seed 1, Qwen3-8B).**

| Arm | One option marked | Right of those | Tokens | Ladder → think, utility minus think |
|---|---|---|---|---|
| tr (whole program) | 34 | 85.3% | 2.7k | +1.8 [−1.3, +5.3] |
| trs (declarations) | 52 | 92.3% | 1.9k | +6.4 [+2.6, +10.4] |
| trsd (trs + per-rule count feedback) | 45 | 84.4% | 2.0k | +2.8 [−0.9, +6.6] |

Thinking on dev: 71.0% at 7.7k; on the 52 questions trs covers, thinking is right on only 63.5%. The per-rule feedback (trsd) did not help on this seed and is not carried forward. One seed, so the dev numbers only choose the arm.

**Prior work.** Logic-LM (2305.12295, read) uses the same declarations/constraints/options split with Z3; its GPT-4 programs run on 32.6% of AR-LSAT, 39.8% after self-refinement, 43.0% accuracy. SatLM (2305.09656, read) abstains on unsat or ambiguous outcomes. Neither compares against a thinking model or counts tokens. The claim tested is the cost gate in front of a current thinking model on real text.

**Setup.** Qwen3-8B, the test split (230 questions), seeds 1, 2, 3, temperature 0.7. `trs`: no thinking, 4,096 tokens a round, up to 3 rounds. `think`: 16,000 tokens (seed 1 already exists from the earlier tie; seeds 2 and 3 new). Ladder: `trs`; if not exactly one option, `think`; tokens of both counted. Composed offline on the same question and seed. Utility per question = 100·right − 0.5·ktok; intervals by bootstrap over the 230 questions, 95%, each question's mean over seeds.

**Predictions.**
- **LS-P1:** ladder utility exceeds think, interval above 0.
- **LS-P2:** ladder accuracy at least think minus 2 (lower bound above −2).
- **LS-P3 (reported):** exactly one mark is right at least 90% of the time, and covers at least 20% of questions.

**Decision.** P1 and P2 hold: the gate survives real text, and the ZebraLogic claim is stated for both, with this as the evidence that it does not need templated clues; next, a second model. P1 fails: on real text the gate ties, and the claim stays limited to ZebraLogic.

## Addendum: arm trse (idea 22)

Written 2026-11-08 20:4x UTC, before any test output of `trse` exists and before reading the test rows of `trs` (only row counts were looked at). LS-P1–P3 above stay on `trs` as registered.

**Why.** Reading dev programs: the harness reverses the test when the model sets `EXCEPT = True`, and 42 of the 57 such flags are on questions without EXCEPT ("which one CANNOT be true?" declared as KIND = "cannot" plus a reversal). The harness then marks the four wrong options. `trse` is `trs` with EXCEPT set by the harness from the question's text, after the model's code; the prompt is unchanged. Replaying only the final rounds on dev: one-mark right 48 → 61 (one new wrong mark), ladder accuracy 77.5% → 78.8%, ladder tokens 7.9k → 7.5k. A rerun can differ from the replay, because the wrong flag also drove the repair rounds.

**Setup.** As above; `trse` on the test split, seeds 1, 2, 3, paired with `trs` on the same question and seed, each composed with the same `think` run.

**Predictions.**
- **LS-P4:** ladder utility of `trse` minus that of `trs`, interval above 0.
- **LS-P5:** `trse` one mark right at least 88% of the time and on at least 3 points more of the questions than `trs`.
- **LS-P6 (reported):** in `trs` test programs, the share of `EXCEPT = True` flags on questions without EXCEPT is 50–85%.

**Decision.** P4 holds: `trse` replaces `trs` as the front of the ladder, and LS-P1/P2 are also reported for it (labelled as the post-registration arm). P4's point is positive but its interval includes 0: a tie; `trs` stays the registered result and `trse` is reported beside it. P5 fails on precision: the text flag is not the whole story and the arm is dropped.

## Results

### Results, 2026-11-08 22:4x UTC (test split, 230 questions, seeds 1–3, all runs complete)

**A scoring bug in the thinking baseline, found while reading raw outputs.** The `think` arm's answer parser looked only for "Answer: X". Qwen3-8B with thinking often ends with `\boxed{B}` instead; 100 of the 690 test runs (and 40 of 231 dev runs) were scored as no answer although they gave one. All 100 test cases now parse; the only runs left without an answer are the 44 cut off at the 16,000-token limit. The parser in `poc/run_zebra.py` now also reads `\boxed{X}`. Corrected, thinking is right on **85.8%** of test runs (was scored 72.9%) and **88.3%** on dev (was 71.0%). The `trs` / `trse` scores are unaffected (the harness gives their answers). Every verdict below uses the corrected scores; the registered (wrong) scoring is shown for completeness.

| | Accuracy | Tokens | Utility |
|---|---|---|---|
| think | 85.8% | 7.69k | 81.9 |
| ladder trs → think | 85.2% | 8.11k | 81.2 |
| ladder trse → think | 85.1% | 7.73k | 81.2 |

- **LS-P1 fails:** ladder (trs) minus think, utility −0.8 [−2.1, +0.5]. (With the wrong scoring it was +1.7 [−0.2, +3.7], which also fails.)
- **LS-P2 holds:** accuracy −0.6 [−1.7, +0.6], lower bound above −2.
- **LS-P3 holds:** one mark on 160 of 690 runs (23.2%), right on 145 (90.6%).
- **LS-P4: a tie.** trse minus trs, utility +0.0 [−0.9, +1.0].
- **LS-P5 fails on precision:** trse one mark on 187 (27.1%, +3.9 points over trs), right on 164 (**87.7%**, below 88%).
- **LS-P6 holds:** 90 of the 123 `EXCEPT = True` flags in trs test programs (73%) are on questions without EXCEPT.

**Decision (as registered).** P1 fails: on real text the gate ties with thinking, and the solution-count claim stays limited to ZebraLogic. `trse` is dropped (P5). One mark is right about 90% of the time, but thinking alone is right about as often on the same questions, so the gate saves no tokens at equal accuracy.

**Correction to the development section above.** The dev table and the reason for this test rest on the same scoring bug. With corrected scoring on dev (seed 1): thinking 88.3%; ladder minus think, utility: tr −2.5 [−4.4, −1.1], **trs +1.2 [−1.4, +4.0]** (was +6.4 [+2.6, +10.4]), trsd −1.1 [−3.8, +1.7]; on the 52 questions trs covers, thinking is right on 86.5% (was 63.5%). The earlier AR-LSAT "tie" for the whole-program arm (test seed 1) used the same parser and is also corrected: thinking was right on 199 of 230, not 174.

## Addendum: LS-OSS, a stronger translator on real text (written 2026-11-09 00:5x UTC, before any run)

**Why.** On Qwen3-8B the gate tied: the translation settled only 23% of questions, and those were the ones thinking also got right (90.6% against 93.1%). On ZebraLogic, gpt-oss-20b translates far better than Qwen3-8B (a count of 1 on 98% of puzzles at about 700 tokens, against 61% for Qwen3-8B's trf). So it tests whether the AR-LSAT tie was the 8B translator's limit or real text's.

**Setup.** gpt-oss-20b, the AR-LSAT test split, seeds 1–3. `trs` (as registered above, prompt and harness unchanged) at low effort; `think` at high effort, capped at 22,000 tokens, scored with the corrected parser. Ladder, utility and intervals as above.

**Predictions.**
- **LO-P1:** ladder utility exceeds think, interval above 0.
- **LO-P2:** ladder accuracy at least think minus 2.
- **LO-P3 (reported):** trs one-mark coverage and precision, and thinking's accuracy on the questions trs settles.

**Decision.** LO-P1 holds: the gate pays on real text when the translator is strong enough, and the claim is stated for both benchmarks with gpt-oss-20b. LO-P1 fails: on real text the gate does not pay even with a strong translator.
