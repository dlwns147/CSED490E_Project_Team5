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

## Results
