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
