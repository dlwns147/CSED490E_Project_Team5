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
