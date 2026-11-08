# Pre-registration: Python inside thinking, forced open, against thinking at the same budget (TIR)

Written before any of the runs below exist. Idea 13 in `docs/notes/IDEAS_COMPUTATION.md`.

**Why.** We want exactly right answers for fewer tokens. In the pilot (Qwen3-8B, seed 1, `tirf` mode of `poc/run_math.py`), the model thinks with a Python sandbox. Whenever its thinking says it will use Python, we open the code block for it, run the block, and paste the output back. It got AIME 80.0% at 11.1k tokens and MATH level 5 92.5% at 5.7k. But its cap was 28,000 tokens and the plain-thinking runs we compared it with were capped at 16,000, where 40 of 240 AIME runs hit the cap. Cut offline at 16,000, `tirf` gets AIME 73.3% at 9.9k against thinking's 69.6% at 15.6k: a tie on utility, +6.6 [−1.4, +15.1]. So the fair baseline is plain thinking at 28,000, which we have not run.

**Prior work, read before this.** START (2503.04625, Hint-infer) inserts a hint ending in an open ```python block into QwQ-32B-Preview's thinking after "Wait" and similar words, no training; AIME24 rises from 50.0% to 60.0% over three rounds. Their hint, like ours, opens the block. CoRT (2506.09820) starts R1's thinking with a hint to use Python ("prompt-hint") to make training data, then trains for token efficiency. Our trigger differs only in where the block opens: on the model's own statement that it will use Python. We claim no new mechanism. What is untested is the cost side: whether a current 8B thinking model with this training-free opening gives the same or better accuracy for fewer tokens than plain thinking at the same cap. START reports accuracy only, and CoRT's token gains come after training.

**Setup.** Qwen3-8B, the 194 problems of `X1_HARD` (AIME 2024 and 2025, 60; MATH-500 level 5, 134). Temperature 0.7, top-p 0.95, both arms capped at 28,000 output tokens; server context 32,768. Tokens = output tokens; pasted outputs (at most 1,000 characters each) are prompt, not counted, stated as a limit.

- `tirf`: seeds 2, 3, 4 (seed 1 is the pilot and is reported, not counted).
- `think`: plain thinking, seeds 1, 2, 3, tag `q8bk`.

Per problem, each arm's accuracy and tokens are averaged over its three seeds. Utility = 100·right − 0.5·ktok. Intervals: bootstrap over problems, 95%, AIME and level 5 separately.

**Predictions.**

- TIR-P1: on AIME, `tirf` utility exceeds `think`, interval above 0.
- TIR-P2: `tirf` uses at least 20% fewer tokens than `think`, on AIME and on level 5 (point estimate), and the interval of the token difference is below 0 on both.
- TIR-P3: on level 5, `tirf` accuracy is at least `think` minus 3 points (interval lower bound above −3).

**Decision.** If P1 holds, repeat on a second model (Qwen3-4B) and report against START's Hint-infer numbers. If P1 fails while P2 and P3 hold, the result is the cost claim alone: the same accuracy for fewer tokens. If P2 fails, idea 13 is closed.

## Results


### 2026-11-08 09:5x UTC: three seeds each (tirf seeds 2–4, think seeds 1–3, both at 28,000)

| | AIME (60) accuracy | AIME tokens | Level 5 (134) accuracy | Level 5 tokens |
|---|---|---|---|---|
| think | 64.4% | 16,061 | 93.0% | 8,509 |
| tirf | 70.0% | 11,947 | 89.8% | 5,982 |

- **TIR-P1 fails:** AIME utility +7.6 [−0.5, +15.9]; accuracy +5.6 [−2.2, +13.3]. A tie.
- **TIR-P2 holds:** tokens −25.6% on AIME (−4,114 [−5,264, −3,048]) and −29.7% on level 5 (−2,526 [−3,023, −2,045]).
- **TIR-P3 fails:** level-5 accuracy −3.2 [−6.5, 0.0], lower bound below −3.

Hitting the 28,000 cap: tirf 9 of 180 AIME runs, think 31. **The case is not one the decision named** (P1 and P3 fail, P2 holds), so I state it plainly: no claim. Forced Python cuts a quarter of the tokens and ties on AIME, but may cost accuracy on level 5. On the 18 level-5 problems where thinking is right more often, 15 of tirf's 25 wrong runs ran the program without an error and boxed its wrong answer: the model trusted a program that modelled the problem wrongly. START's answer to this is training (Hint-RFT); prompting alone does not fix it here. Idea 13 is not closed (P2 holds), but it has no claim as it stands.
