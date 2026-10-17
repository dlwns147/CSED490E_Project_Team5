# Pre-registration B1: published label-free selection methods as baselines for the metamorphic check (MR-select)

Written 2026-10-13 ≈17:19 UTC (file last saved 17:21:30, one second before the data runs were launched; the header first said 17:35 by mistake), before generating any of the data below. Results are appended below without editing this section.

**Question.** Is selecting by consistency of one program on transformed copies of the given instance (ours) better or cheaper than the
published label-free selectors? Same candidates for every selector: Qwen3-8B, no thinking, `--stdlib`, T = 0.7, 3 samples (seeds 1–3) per
instance, new runs with top-20 log-probs stored (`S2_B1_geox8b_{dis0,dis8,hard}_t07s{1,2,3}`): 5 core tasks with K0 and K8 helpers
(300 instances each), hard tasks lattice + rectunion (120).

**Selectors (k = 3).**
1. single sample (mean over seeds); oracle-any (upper bound).
2. **MR-select (ours):** candidates consistent on the 6 metamorphic copies of the given instance; majority vote on the given-instance output.
3. **Vote on the given instance** (self-consistency / MBR-exec with one input).
4. **MBR-exec on model-written inputs** (Shi et al. 2022; CodeT's inputs without outputs): the same model writes 5 test inputs per
   instance (no toolbox, no thinking; `poc/gen_tests.py`); choose the candidate agreeing with most others on the given + written inputs.
5. **MBR-exec on fresh inputs from the task's own instance generator** (an oracle input distribution: stronger than a deployer has).
6. **CodeT dual agreement** (Chen et al. 2022): model-written tests with expected outputs; score each agreement cluster by
   (#candidates in it) × (#tests it passes); pick from the best cluster.
7. **Confidence (DeepConf-style, 2508.15260):** pick the candidate with the highest mean token confidence (minus mean top-20 log-prob),
   lowest-group confidence (min over 64-token windows) and tail confidence (last 256 tokens); plus mean log-prob (C1).
8. **Hybrid (ours + MBR):** MR-consistent candidates first, ties broken by MBR agreement on model-written inputs.
Cost per instance: extra generation tokens (test writing ≈ one call) + program executions.

**Predictions.**
- B1-P1: MR-select ≥ MBR-exec on model-written inputs and ≥ CodeT in all three conditions (point estimates).
- B1-P2: CodeT is the weakest execution-based selector on geometry (expected outputs written in text are unreliable, cf. direct answers 22%).
- B1-P3: MBR-exec on fresh generator inputs is within 2 points of MR-select under K0 and K8.
- B1-P4: no confidence variant beats the single sample by more than 2 points (CI excluding 0) in any condition.
- B1-P5: under K8 on hull (systematic errors), every label-free selector stays below 50% correct (oracle-any was ≈ 40% there in C1). [wording cleaned before any data was generated]
Also (offline, existing data): **DART-style router** (2606.23181) for E3: two no-thinking drafts (C1 seeds 1–2); if their outputs on the
given instance agree, answer with draft 1, else one budget-thinking (1,024) program. **B1-P6:** under K8 and on the hard tasks it is at
least 5 points below always-think-1,024 at matched tokens (agreeing wrong drafts, as in E3).


---
## Results (appended 2026-10-13 ≈17:38 UTC; predictions above unedited)

Qwen3-8B, the same 3 candidates per instance for every selector; % correct on all 8 variants; differences paired, 95% bootstrap CI;
`poc/analyze_b1.py`. Model-written tests: 3.6 parsed per instance (≈ 320–360 generation tokens per instance).

| selector (k = 3) | K0 (300) | K8 (300) | hard (120) | extra cost per instance |
|---|---|---|---|---|
| single sample | 91.8 | 77.9 | 17.8 | – |
| **MR-select (ours)** | **99.7** | **83.3** | **33.3** | 6 runs of each program (CPU) |
| vote on the given input (self-consistency) | 95.7 | 81.3 | 21.7 | – |
| MBR-exec, model-written inputs | 93.7 | 80.3 | 25.0 | ≈ 340 tokens + runs |
| MBR-exec, fresh inputs from the task generator | 93.7 | 80.3 | 21.7 | runs (needs a generator) |
| CodeT dual agreement | 96.0 | 82.7 | 26.7 | ≈ 340 tokens + runs |
| confidence: mean token confidence (DeepConf) | 94.7 | 79.3 | 13.3 | – (top-20 log-probs) |
| confidence: lowest-group (DeepConf) | 95.3 | 80.0 | 7.5 | – |
| confidence: mean log-prob | 93.7 | 80.3 | 10.8 | – |
| hybrid MR + MBR | 99.7 | 83.0 | 35.8 | ≈ 340 tokens + runs |
| oracle-any | 100 | 85.0 | 42.5 | – |

MR-select minus the best published baseline: K0 +3.7 [+1.3, +6.0] (CodeT), K8 +0.7 [−1.0, +2.3] (CodeT), hard +6.7 [0.0, +13.3] (CodeT).
- **B1-P1 confirmed:** MR-select ≥ MBR-exec and ≥ CodeT in all three conditions (vs CodeT under K8 only +0.7, n.s.).
- **B1-P2 not confirmed:** CodeT is the *strongest* baseline, not the weakest: the model's expected outputs on its own small tests
  (e.g. a unit triangle) are often right even though its direct answers on real instances are not.
- **B1-P3 not confirmed:** MBR-exec on fresh generator inputs is 6.0 (K0) and 3.0 (K8) points below MR-select. Reading the cases: fresh
  inputs come from the same distribution (e.g. counter-clockwise polygons), so programs that print a *signed* area or assume an
  orientation agree with the correct ones there; the mirrored / scaled copies of the given instance expose them.
- **B1-P4 not confirmed on clean prompts:** DeepConf-style confidence does beat a single sample a little (K0 +2.9 to +3.6, K8 lowest-group
  +2.1), unlike the C1 mean log-prob; on the hard tasks every confidence variant is *worse* than a single sample (lowest-group −10.3).
- **B1-P5 confirmed:** on hull under K8 (systematic errors) no selector reaches 50% (best: MR-select 32%, oracle-any 38%).
- **B1-P6 (DART-style router) not confirmed in magnitude:** 2.0–2.5 points below always-think-1,024 (not ≥ 5), but at 1.3–1.6 × its
  tokens under K8 / hard (it escalates 74 / 113 instances after paying for two drafts). It does not beat the fixed budget either.
