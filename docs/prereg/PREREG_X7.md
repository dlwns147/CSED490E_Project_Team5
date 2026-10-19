# Pre-registration X7: the final recipe on a held-out benchmark (MAMO), with no hand-written fact

Written 2026-10-19 02:37 UTC, before any run. Results go below.

**Why.** Everything so far was developed on NL4OPT / IndustryOR and our generated suites. MAMO (Huang et al. 2024; EasyLP 652 + ComplexLP 211
optimization word problems, CardinalOperations/MAMO) has not been used. The recipe as it now stands, with no human-written component:
the fact = the model's own shortest program from NL4OPT / IndustryOR that passed the label-free check (runs and prints a value); write
the program with it (twice); think only unless both run and agree (FFR) — or only if it fails to run (FF). The hand-written snippet is
run alongside as the reference. Models: Qwen3-32B-AWQ (GPU0), Qwen3-14B-AWQ (GPU1), gpt-oss-20b (GPU2; low effort for the cheap
arms, medium for thinking), Qwen3-8B (GPU3, expected to lag); tag <model>_mamo (poc/queues/queue_s2_x7.sh).
Arms: mip s1 (no fact); mipf s1–2 + thinkf s1 (hand-written); mips s1–2 + thinks s1 (automatic).
- X7-P1: automatic FFR within 2 points of hand-written FFR for Qwen3-32B, Qwen3-14B-AWQ and gpt-oss-20b; ≥ 4 points below for Qwen3-8B.
- X7-P2: automatic FF ≥ always-thinks − 2 points at ≤ 40% of its tokens for those three models.
- X7-P3: picking the policy (CHEAP / FF / FFR / THINK) from 30 labelled MAMO items gives ≤ 1.5 points of regret (λ = 0.5) per model.

## Results, gpt-oss-20b (2026-10-19 03:36 UTC; results/x3/analysis_x7.log; MAMO 863 problems, seeds 1–2 for the cheap arms)
No fact 73.2%. Hand-written fact: CHEAP 76.1% @ 0.5k, FF 79.3% @ 0.6k, FFR 78.9% @ 1.7k, THINK 77.4% @ 2.5k. **Automatic fact: CHEAP 74.4%,
FF 77.3% @ 0.6k, FFR 78.8% @ 1.9k, THINK 76.0% @ 2.7k** (EasyLP / ComplexLP FFR 85.6 / 57.8%).
- **X7-P1 holds for gpt-oss-20b** (automatic FFR −0.1 points vs hand-written). **X7-P2 holds** (automatic FF 77.3% ≥ always-thinks 76.0% − 2,
  at 22% of its tokens). **X7-P3 holds** (pilot-of-30 regret 1.27 points; best policy FFR).
Addendum (before running): Qwen3.6 on MAMO, same arms, 80k thinking (T 1.0 / top_k 20), GPU2 — prediction: automatic FFR ≥ 3 points
below hand-written (as on X6).

## Results, Qwen3-14B-AWQ and Qwen3-8B (2026-10-19 05:36 UTC)
| model | no fact | hand: CHEAP / FF / FFR / THINK | automatic: CHEAP / FF / FFR / THINK | pilot-30 regret |
|---|---|---|---|---|
| Qwen3-14B-AWQ | 59.7% | 68.0 / 71.4 @ 0.9k / 71.4 @ 2.6k / 65.5 @ 6.5k | 68.4 / **70.7 @ 0.8k** / **71.7 @ 2.8k** / 68.8 @ 6.6k | 0.82 |
| Qwen3-8B | 45.5% | 57.5 / 70.2 @ 1.8k / 72.0 @ 4.5k / 69.2 @ 7.9k | **67.7** / 69.5 @ 1.0k / 71.0 @ 3.1k / 65.1 @ 7.7k | 1.35 |
- **X7-P1 holds for Qwen3-14B-AWQ** (+0.3); **refuted for Qwen3-8B in the good direction** (−1.0, not ≥ 4 below): on MAMO the 8B model's mined
  example is a *better* cheap fact than the snippet (67.7 vs 57.5%: 94% of its programs run vs 84%, pass-but-wrong 28% vs 30%).
- **X7-P2 holds** for both (automatic FF ≥ always-thinks − 2 at 12–13% of its tokens). **X7-P3 holds** (regret 0.82 / 1.35).
Replication (pre-registered now; our rule: positive claims need ≥ 3 seeds): cheap arms seed 3 and thinking seeds 2–3 for Qwen3-14B-AWQ
(GPU1) and gpt-oss-20b (GPU3) (queue_s2_x7rep.sh); prediction: the automatic-vs-hand FFR gap stays within ±2 points on each seed pair.
- **Replication, gpt-oss-20b, 3 seeds (2026-10-19 06:36 UTC):** automatic minus hand-written FFR = −0.1 / −0.8 / −1.2 points (78.8 / 78.6 / 78.4% vs 78.9 / 79.4 /
  79.6%), at the same tokens (1.8–1.9k); the ±2 prediction holds on every seed. Qwen3-14B-AWQ seeds running; Qwen3-32B / Qwen3.6 finishing.

## ORLM same-harness baseline, pre-registration (2026-10-19 07:36 UTC, before running)
ORLM-LLaMA-3-8B (fine-tuned for optimization modeling; its model-card template, coptpy, greedy decoding = seed 1, plus sampled seeds 2–3 at
T 0.7) on NL4OPT + IndustryOR (tag orlm) and MAMO (tag orlm_mamo); the objective is read from the solver (Model.solve wrapped), graded with
the same tolerance as every other arm (poc/run_orlm.py; poc/queues/queue_s2_orlm.sh, first free GPU).
- ORLM-P1: greedy MAMO Easy / Complex within ±4 points of the reported 82.3 / 37.4%.
- ORLM-P2: our training-free recipe (automatic fact, two agreeing programs, else think) with Qwen3-8B is within 3 points of ORLM on MAMO overall
  (same model size, no training); with gpt-oss-20b it is ≥ 5 points above.
- ORLM-P3 (cost): ORLM's single greedy program is cheaper per problem than our FFR (fewer output tokens), so per token ORLM wins; per accuracy
  at a 3090 budget gpt-oss-20b wins.

## ORLM results (2026-10-19 08:39 UTC; results/x3/opt_orlm*_orlm_s*.jsonl; 17 programs that began with a 'pip install' line re-run without it — no change)
ORLM-LLaMA-3-8B, greedy (seed 1) / sampled (2, 3): **MAMO Easy / Complex 80.5 / 35.5%** (77.8 / 22.3, 77.3 / 29.4); overall 69.5% (64.2, 65.6) at
1.1k output tokens; NL4OPT / IndustryOR 78.8 / 27.0% (75.5 / 29.0, 75.1 / 29.0).
- **ORLM-P1 holds** (greedy within ±4 of the reported 82.3 / 37.4%).
- **ORLM-P2 holds:** our training-free recipe (automatic fact, two agreeing programs, else think) on MAMO overall — Qwen3-8B 71.0% @ 3.1k (+1.5
  over ORLM greedy; plain fact-first 69.5% @ 1.0k = ORLM at the same tokens), Qwen3-14B-AWQ 71.7% @ 2.8k, gpt-oss-20b 78.8% @ 1.9k (+9.3),
  Qwen3-32B 76.9% @ 0.5k (fact-first; its best policy).
- **ORLM-P3 refuted:** ORLM is not cheaper than our plain fact-first at equal accuracy (Qwen3-8B 69.5% @ 1.0k vs ORLM 69.5% @ 1.1k).
**Reading:** a fine-tuned 8B specialist is matched, with no training, by a general 8B model given its own mined example and a cheap check.
**STORM-Qwen3-4B (pre-registered now):** the strongest public small specialist (SFT + RL, tool-integrated reasoning; reported MAMO 86.3 / 70.3% on
its cleaned 100-problem subsets with a 5% tolerance after rounding). Run with its official inference code (cloned; vLLM 0.22; 3 samples,
T 0.6) on our full MAMO and NL4OPT + IndustryOR, graded with our tolerance (and with theirs, for reference) (queue_s2_storm.sh, GPU0).
Prediction: STORM ≥ our best training-free 3090-class result on MAMO (gpt-oss-20b 78.8%) under our grader, at ≥ 3 × the tokens.
