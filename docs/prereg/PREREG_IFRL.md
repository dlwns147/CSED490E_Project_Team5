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
