# PREREG_GRLLF: can the free check alone, with no labels, train the cheap grid translation? Registered 2026-11-12 04:2x UTC, before any training round

**Why.**
- GRL (PREREG_GRL) trained the quick translation with a reward that needs the gold grid. The paper's claim is "cheap answer + free check". If the check that gates the ladder (the solver finds exactly one solution) is also enough to train the cheap step, no labels are needed anywhere. The method could then train on the very puzzles it must answer.
- **The risk is reward hacking.** A wrong translation can also have exactly one solution, so a check-only reward also reinforces some wrong readings. Per sample, the base translation on GridPuzzle is right 25.0% of the time and is wrong with a single solution 3.8% of the time (precision 86.8%; PREREG_GRLK). Mitra-Baral: 43.1% and 2.6%. So the check-only reward is right about 6.6 times out of 7.6 on GridPuzzle. Training should mostly follow right readings unless the wrong unique readings are the ones the model can learn fastest.
- **Prior work (checked 2026-11-12).**
  - TTRL (Zuo et al. 2504.16084) trains on unlabeled test questions with a majority-vote label.
  - Spurious Rewards (Shao et al. 2506.10947, ICML 2026) find that Qwen2.5-Math improves even with random rewards, through GRPO's clipping bias. Our loop takes one on-policy step per round, so the clipping term is inactive and a random reward has zero expected gradient. The gold-reward run is the matching positive control.
  - Puzzle RL (Enigmata 2505.19914, RLVE 2511.07317, SAT-RL 2610.14402, LogicPuzzleRL 2506.04821) uses generators with known answers or rule checkers that see the solution.
  - I found no work that trains with the solution-uniqueness check alone as the reward on human-written puzzles.

**Method (`poc/gp_train.py --reward count1`, `poc/slurm/grl_lane.sh` with `GRL_NAME`, committed with this file).** GRL's loop and settings unchanged. Reward = 1 if the program's solver count is 1, else 0. The gold grid is not read in training; it is logged as "right" for monitoring only.
- **lf (cross-fitted):** GRL's two folds and training sets, so the result is comparable with GRL's. Tags `q8bgrllf0`, `q8bgrllf1`.
- **tt (transductive):** one model trained on every puzzle of both sets, dev and test, without labels (309 test + 88 dev puzzles, 4 epochs). Evaluated on all 309 test puzzles. This is the deployment setting: train on the questions you must answer, no labels. Tag `q8bgrltt`.
- **Evaluation** as GRL: arm `gtr` with the adapter (3 rounds), seeds 4–9, then base `gtrt` → `think`, every step paid. Command: `python poc/gp_eval.py --grl --extra lf=q8bgrllf0+q8bgrllf1,tt=q8bgrltt`.

**Predictions.**
- **LF-P1 (decides whether the check trains).** GridPuzzle ladder(lf) − ladder(gtr), seeds 4–9, interval above 0. Mitra-Baral lower bound above −2.0.
- **LF-P2 (decides whether labels are needed).** GridPuzzle ladder(lf) − ladder(grl), lower bound above −3.0. That is non-inferiority: lf keeps at least about 57% of GRL's +7.0. Reported on Mitra-Baral.
- **LF-P3 (mechanism, no hacking).** GridPuzzle quick count-1 precision of lf is at least the base's 82.4%.
- **TT-P4.** GridPuzzle ladder(tt) − ladder(gtr) interval above 0. Mitra-Baral lower bound above −2.0. tt − grl is reported.

**Decision.**
- **P1 and P2 hold:** the free check is both the gate and the training signal. Label-free GRL is the stated method, and gold-reward GRL becomes its labelled upper reference.
- **P1 holds, P2 fails:** the check trains the cheap step, but labels add value. Both are reported; gold-reward GRL stays the method where labels exist.
- **P1 fails:** the check alone does not train; labels are needed.
- **P3 fails:** the check-only reward teaches wrong unique readings. Report it as reward hacking with the per-puzzle cases.
- **P4 holds:** report the transductive label-free setting as the deployment variant. It answers "what if there is no labelled training set at all".

**Runs.** On the paper-extension server, three lanes, each with a vLLM GPU and a trainer GPU: lf fold 0, lf fold 1, tt.

## Result (2026-11-12 05:5x UTC): every prediction holds. The check alone trains the cheap step as well as the labels do; trained on the test puzzles without labels, the ladder beats thinking on accuracy and tokens

Seeds 4–9, `python poc/gp_eval.py --grl --extra lf=q8bgrllf0+q8bgrllf1,tt=q8bgrltt`:

| Ladder (quick step → base `gtrt` → base `think`) | GridPuzzle (1290) | Mitra-Baral (564) |
|---|---|---|
| base `gtr` | 69.6% at 18.31 ktok, utility 60.5 | 88.5% at 9.71, 83.6 |
| GRL (gold reward, cross-fitted) | 74.7% at 14.37, 67.5 | 90.8% at 6.73, 87.4 |
| **lf** (check-only, cross-fitted) | **75.8% at 14.00, 68.8** | **90.2% at 6.85, 86.8** |
| **tt** (check-only, trained on all puzzles incl. test) | **79.7% at 10.96, 74.2** | **93.6% at 3.69, 91.8** |
| think alone | 63.4% at 11.53, 57.6 | 87.1% at 6.31, 83.9 |

| Quick step | GridPuzzle right count-1 / precision | Mitra-Baral |
|---|---|---|
| base | 31.9% / 82.4% | 49.6% / 92.1% |
| GRL | 55.2% / 91.8% | 69.5% / 94.9% |
| lf | 57.8% / 93.0% | 70.7% / 94.3% |
| tt | 71.0% / 96.2% | 83.9% / 96.9% |

- **LF-P1 holds.** ladder(lf) − ladder(gtr): GridPuzzle **+8.4 [+5.4, +11.5]**; Mitra-Baral +3.2 [−1.1, +7.4] (lower bound above −2.0).
- **LF-P2 holds.** ladder(lf) − ladder(grl): GridPuzzle **+1.3 [−0.6, +3.3]** (lower bound above −3.0); Mitra-Baral −0.6 [−2.8, +1.2]. Quick step right count-1, lf − GRL: +2.6 [+0.1, +5.3] points on GridPuzzle (`--quick`).
- **LF-P3 holds.** lf's count-1 precision is 93.0%, against the base's 82.4%. The wrong count-1 share falls: 6.8% → 4.3%, −2.5 [−5.5, +0.2]. During training, 90–100% of single-solution samples were also right, read from the logged labels the trainer did not use.
- **TT-P4 holds.** ladder(tt) − ladder(gtr): GridPuzzle **+13.8 [+10.0, +17.7]**; Mitra-Baral **+8.2 [+3.6, +13.1]**. Against GRL: +6.7 [+4.3, +9.3] and +4.4 [+1.1, +8.0]. Against thinking: **+16.6 [+12.3, +21.1] with fewer tokens** (79.7% at 10.96 ktok against 63.4% at 11.53) and **+7.9 [+3.3, +12.9]** (93.6% at 3.69 against 87.1% at 6.31).
- **tt's training cost, which the ladder's ktok leave out.**
  - tt sampled 100 rounds × 128 programs of about 0.42 ktok each (first-round mean of the trained model), about 5.4M tokens. That is 17.4 ktok per test puzzle if all of it is charged to the 309 test puzzles, or 13.4 ktok if only each test puzzle's own 32 samples are.
  - At the utility's 0.5 per ktok, that is −6.7 to −8.7 per puzzle answered once, about tt's whole gain over lf (+6.7 on GridPuzzle). It pays only when the same puzzles are answered more than once, or with fewer samples.
  - lf's training happens once, on other puzzles, and costs nothing per test puzzle.
  - So lf is the method; tt is the deployment variant for a fixed pool of questions.
- **Decision (as registered).** P1 and P2 hold. The free check is both the gate and the training signal: label-free GRL is the stated method, and gold-reward GRL is its labelled reference. P4 holds, and tt is reported as the transductive deployment variant, with its training cost.
- **Why it does not hack** (a reading, to be tested). Right translations share reusable rules (how a comparison clue maps to code). Wrong translations that happen to have one solution are puzzle-specific accidents. Shared parameters therefore move right readings up faster than wrong ones, even though both earn the same reward. PREREG_GRLX tests the same reward on a family whose check is less precise (Granite, right : wrong 3.5 and 3.0 against Qwen's 4.7 and 11.5).

## Prior work read after the result (2026-11-12 06:5x UTC), for positioning
- **Label-free RLVR is an active area.** Each method below makes its own reward from the model's samples:
  - TTRL (2504.16084) uses the majority vote.
  - Co-rewarding (2508.00410, ICLR 2026) uses votes crossed between a question and its rephrasing.
  - RESTRAIN (2510.02172) penalises low-agreement prompts.
  - OM-GRPO (2608.03119) uses soft consensus, with gradients masked on the answer span.
  - Spark (2512.03244) uses generative process rewards.
  - All of these are math or general reasoning with a final answer. Their known failure is a reward for confident consensus on a wrong answer.
- **Closest: JURY-RL** (ICML 2026, OpenReview EzgoVswq4a). Votes propose an answer, and Lean must verify it before it is rewarded; unverified pluralities are dropped. It matches ground-truth training at pass@1.
- **How ours differs.**
  - The check is structural and built into the task. The model's own formalisation of the puzzle must have exactly one solution. No vote, no answer proposal and no prover are needed.
  - The same check gates the cheap → thinking ladder at test time, and tokens are counted.
  - Its false-positive rate can be measured offline before training. Wrong passes were 3.8% of samples against 25.0% right on GridPuzzle, a right : wrong of 6.6 per sample (PREREG_GRLK). PREREG_GRLX tests a model with a lower ratio.
  - A paper claim needs a comparison with a vote reward on the same puzzles. A majority vote over the grids of a group's count-1 programs is the TTRL analogue here; it is not yet run.
