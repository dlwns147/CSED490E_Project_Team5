# PREREG_IFRL: does the free check train a model off puzzles, and what predicts when? Instruction following, Qwen3-8B, registered 2026-11-12 09:2x UTC, before any training round

**Why.**
- Every RL result so far (GRL, GRLLF, GRLX, GRLV) is on logic grid puzzles. The user asked whether the method is puzzle-only.
- The cross-domain table (FINDINGS 2026-11-12 08:0x) proposed a rule from the right : wrong ratio among answers that pass the check: above about 3 the check should work as a reward, below it should fail. That rule is a guess. It also depends on how often the model is already right.
- A derivation gives a different rule. Write the check's reward as a noisy copy of the gold reward, with TPR = P(pass | right) and FPR = P(pass | wrong). Suppose the noise depends only on whether a response is right (class-conditional). Then E[check | response] = FPR + J · right, with J = TPR − FPR (Youden's index). With a group-mean baseline the constant FPR cancels in expectation. So the expected GRPO gradient under the check is exactly J times the expected gradient under gold labels. Rad et al. (2601.04411, "Rate or Fate? RLVεR") derive the same J for GRPO as a replicator flow: J > 0 learns, noise rescales time by 1/J. Cai et al. (2510.00915) correct GRPO for asymmetric verifier noise.
- So the derivation predicts that any check with J > 0 trains, at about J times the speed of gold. The ratio rule predicts failure where right : wrong is low. The two disagree on IFBench.
- Where noise is not class-conditional, the difference pushes the policy toward wrong responses the checker passes (hacking). That shows up as a rise in wrong responses that pass the checker.

**Post-hoc fit on the grid runs (not a test; stated so it can be checked).**

| Run | J of its reward (base samples) | Reward gain / gold gain, quick right with one solution |
|---|---|---|
| Qwen3-8B, check (GridPuzzle) | 0.94 | 25.9 / 23.3 = 1.11 |
| Granite-4.1-8B, check (GridPuzzle) | about 0.94 | 20.5 / 22.8 = 0.90 |
| Qwen3-8B, majority vote (GridPuzzle) | about 0.58 (exact grid, offline) | 14.8 / 23.3 = 0.64 |

The vote's right : wrong among rewarded samples is 1.1, yet it kept 64% of the gold gain, close to its J.

**Related work.**
- AutoIF (Dong et al. 2406.13542) has a model write Python verification functions for instructions. It filters SFT data with them and builds DPO pairs. It is the closest use of a model-written checker. It does not ask when such a checker is precise enough to train on, and it filters the functions with tests on its own generated data.
- VerIF (Peng et al. 2506.09942, EMNLP 2025) combines rule-based code checks with an LLM judge as the RL reward for instruction following, with checks written by people.
- IFBench (Pyatkin et al. 2507.02833) trains with gold verification functions (IF-RLVR) and finds that IFEval-style training transfers poorly to IFBench.
- None of these predicts, from the checker's measured J, how much of the gold-label gain a label-free check keeps. That prediction, tested where the two rules disagree, is the contribution.

**Setting.** IFEval (541 prompts) and IFBench (300 prompts, test split) with the official strict graders, prompt level (every instruction followed). Response = the non-thinking answer (IF-1's N).
- **The check.** The response passes the model's own checker. The checker is fixed before training: the one Qwen3-8B wrote at seed 1 in IF-1 (`run_if.py`; copied to `$POC_DATA/if_rl/checkers_<bench>.json`). It runs in the sandbox (10 s, 1 GB); a crash scores 0.
- **Offline, the fixed checker on IF-1's stored responses (seeds 1–3, scratch script, before any run):**

| Bench | Right | TPR | FPR | J | Precision | Right : wrong among passing |
|---|---|---|---|---|---|---|
| IFEval | 82.6% | 0.630 | 0.071 | **0.56** | 97.7% | 42.2 |
| IFBench | 25.6% | 0.509 | 0.087 | **0.42** | 66.9% | 2.0 |

**Method.** `poc/if_train.py` (committed with this file): GRL's loop unchanged (LoRA r 16, plain GRPO without std normalisation, group 8, batch 16, lr 2e-5, no KL, 4 epochs, one step per round). Responses are capped at 2,048 tokens in training. Cross-fitted: fold = crc32(prompt key) mod 2 (IFBench 148 / 152, IFEval 279 / 262 held-out prompts). Each fold's model trains on the other fold's prompts and answers its own.
- **gold:** reward = the official strict grader. Tags `q8bifg0`, `q8bifg1`.
- **check:** reward = passes the fixed checker, no label. Tags `q8bifc0`, `q8bifc1`.
- **base:** tag `q8bif`, the same generation without an adapter.
- **Evaluation:** one non-thinking response per held-out prompt (4,096 tokens, temperature 0.7, IF-1's seeding), seeds 4–6, graded by `grade_if.py` (arm N). Report: `python poc/if_train.py --report <bench> q8bif gold=q8bifg0+q8bifg1 check=q8bifc0+q8bifc1`. It gives right and "wrong but passes the checker" shares, paired 95% bootstrap over prompts, and the gain ratio (check − base) / (gold − base) with its bootstrap interval.

**Predictions.** IFBench decides, because the two rules disagree there. IFEval is reported.
- **IF-P1 (precondition).** IFBench gold − base, right: interval above 0. If it fails, RL does not move this benchmark at this scale and the test says nothing about the check.
- **IF-P2 (decides between the rules).** IFBench check − base, right: interval above 0. The J rule predicts it holds (J = 0.42). The ratio rule predicts it fails (2.0).
- **IF-P3 (the J rule's size).** IFBench gain ratio (check − base) / (gold − base): the interval overlaps [0.42, 1]. If gains saturate the ratio can exceed J, so the band's top is 1.
- **IF-P4 (hacking).** IFBench check − base, wrong-and-passes share: point estimate below the right gain's point estimate. If the checker's errors are exploitable, the policy gains more wrong passes than right answers.
- **IF-P5 (reported).** The same quantities on IFEval (J = 0.56; the base is right 82.6% of the time, so gains are expected to be small).

**Decision.**
- **IF-P1, IF-P2 and IF-P3 hold:** the paper replaces the right : wrong rule with J. A check trains a model when its J is positive, at about J times the gold gain, puzzles and instruction following alike. The cross-domain table gets a J column.
- **IF-P1 holds and IF-P2 fails:** the ratio rule survives this test. The label-free claim is stated for checks with high precision only. The J derivation is reported as not predictive because the noise is not class-conditional; IF-P4 tells whether through hacking.
- **IF-P1 fails:** IFBench is not usable at this scale. The test moves to IFEval's ratio alone, stated as weaker.

**Runs.** On the paper-extension server, after the Qwen3-32B runs free their GPUs: IFBench folds first (gold and check), then IFEval. Base rows (seeds 4–6, all prompts) on the Slurm cluster.

## Interim and amendment (2026-11-12 10:2x UTC): IFBench fold 0 shows no learning even on the training prompts; IFRL2 registered

**Interim, IFBench fold 0** (148 held-out prompts, seeds 4–6; fold 1 still training; `--report ifbench q8bif gold=q8bifg0 check=q8bifc0`).
- gold − base, right: +1.1 [−0.9, +3.4]. check − base: +1.6 [−0.5, +3.6]. Wrong and passes the checker: +0.0 and −0.2.
- **Root cause.** The gold reward did not rise on the training prompts themselves. The training log's right share by epoch was 0.274, 0.261, 0.260, 0.291. Only 22% of prompts per round had samples that both passed and failed, so about 3.5 of 16 prompts carried a gradient. 38 steps over 152 prompts, each with its own mix of 58 constraint types, are too few for the policy to move.
- IFBench's authors trained on about 95,000 prompts. Their training constraints repeat across thousands of prompts; ours appear a few times each.
- So IF-P1 is on course to fail, and the registered test would say nothing about the check. Fold 1 and the IFEval folds are left to finish, and the registered result will be reported as registered.

**IFRL2 (new test, registered before any of its runs).** The same question at a scale where gold RL can move.
- **Training pool.** 2,000 prompts from Ai2's IF-RLVR training data (`allenai/IF_multi_constraints_upto5`, the IFBench paper's training set). Only rows whose constraints are all among IFEval's 25 types are used (18,221 of 95,373), so IFEval's official grader is the gold. They are shuffled with seed 0. None is an IFEval or IFBench test prompt.
- **The check.** Qwen3-8B writes a checker for every pool prompt with IF-1's checker prompt and 2,000-token think (`if_train.py --checkers pool`). The checker is fixed before training.
- **J of the check.** Measured on 4 base samples per pool prompt, drawn as in training (`--sample pool 4`, `--jstat pool`). This finishes before training starts and is recorded here before any training round.
- **Arms.** One epoch over the pool (125 rounds), GRL's loop otherwise unchanged. One GPU per run.
  - gold (`q8bifpg`);
  - check (`q8bifpc`);
  - **noisy:** gold passed through random, class-conditional noise with the check's measured TPR and FPR (`--reward noisy --tpr --fpr`, tag `q8bifpn`). Same J as the check, but its errors do not depend on which response is given.
  - The noisy arm separates the two parts of the derivation. Check ≈ noisy means the J rule is the whole story. Check < noisy means the checker's errors are structured and the policy exploits them.
- **Evaluation.** Every IFEval and IFBench test prompt, seeds 4–6, against the base rows `q8bif` (already collected). IFEval's fixed checker (IF-1 seed 1) gives the "wrong and passes" share.

**Predictions (IFEval decides: the pool's constraints are IFEval's types; IFBench is reported).**
- **I2-P1 (precondition).** IFEval gold − base, right: interval above 0.
- **I2-P2.** IFEval noisy − base, right: interval above 0. The derivation says J > 0 is enough.
- **I2-P3.** IFEval ratio (noisy − base) / (gold − base): interval overlaps [J, 1].
- **I2-P4.** IFEval check − noisy, right: interval contains 0 (the checker's errors behave as class-conditional).
- **I2-P5.** IFEval check − base, wrong and passes the checker: point estimate below check − base's right gain.
- **Reported.** The same on IFBench (unseen constraint types).

**Decision.**
- **I2-P1–P4 hold:** the paper states the J rule. A label-free check trains a model at about J times the gold gain, and real checkers here act as class-conditional noise. This holds on grids and instruction following alike.
- **I2-P1–P3 hold and I2-P4 fails (check below noisy):** the J rule is stated as an upper bound for real checkers. The shortfall is the structured part of the checker's errors, measured by I2-P5.
- **I2-P1 fails:** RL does not move IFEval at this scale. Instruction following is reported as a domain where we could not test the check.

## Registered result, IFRL (2026-11-12 11:3x UTC)

IFBench, both folds held out, seeds 4–6 (`--report ifbench q8bif gold=q8bifg0+q8bifg1 check=q8bifc0+q8bifc1`; 900 prompt-seeds).

| Arm | Right | Passes own check | Right and passes | Wrong and passes | J |
|---|---|---|---|---|---|
| base | 26.6% | 18.7% | 13.2% | 5.4% | 0.42 |
| gold | 26.6% | 18.4% | 12.7% | 5.8% | 0.40 |
| check | 26.0% | 19.4% | 13.6% | 5.9% | 0.44 |

- **IF-P1 fails.** gold − base, right: +0.0 [−1.7, +1.7]. Training on the official grader did not move IFBench. Fold 1's training-prompt accuracy also stayed flat: 0.25, 0.25, 0.24 and 0.26 by epoch; 20% of prompts had a gradient.
- IF-P2: check − base −0.6 [−2.2, +0.9]. IF-P3: undefined (no gold gain). IF-P4: check − base wrong and passes +0.4 [−0.4, +1.4].
- IF-P5, IFEval fold 0 (279 prompts; fold 1 still training): gold − base +0.5 [−1.2, +2.0], check − base +0.7 [−0.8, +2.3], ratio 1.50 [−2.0, 11.0].

**Decision (as registered: IF-P1 fails).** IFBench is not usable at this scale: 152 training prompts per fold over 58 constraint types give too few steps with a gradient. IFEval's ratio alone is too wide to test anything. The test of the check is IFRL2.
