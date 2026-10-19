# Pre-registration X1: does the project carry over to short-answer competition math? (writing session, GPUs 0–1)

Written 2026-10-16 17:53 UTC, before any run. Results are appended below without editing this section.

**Why.** The project so far covers computational math (geometry on coordinates, routing, scheduling), where programs and solvers are the
natural tool. User question: what about other math? Short-answer competition math is where frontier models mostly reason in text and use
Python only as an add-on. We test whether our three ideas carry over: programs vs text, a cheap check deciding when to pay for reasoning,
and the leakiness of that check.
**Data.** MATH-500 (HuggingFaceH4/MATH-500, 500 problems, levels 1–5) and AIME 2024 + 2025 (60 problems, integer answers).
Grading with math-verify (symbolic equivalence; standard grader, no hand-written rules).
**Conditions** (3 seeds, T = 0.7): Qwen3-32B-AWQ: text without thinking (answer in \boxed{}), program without thinking (a Python program,
sympy available, prints the final answer; run in the sandbox, 30 s), text with thinking (28k cap). gpt-oss-20b: text low, program low,
text medium. **Gate** (offline): if the text answer and the program answer are equivalent, accept it; else use the thinking / medium answer.
Costs: all output tokens actually spent.
**Prior art.** Mixture-of-thought cascades (Yue et al., ICLR 2024: escalate to a stronger LLM when chain-of-thought and program answers
disagree); PAL / Program-of-Thoughts; ToRA (tool-integrated reasoning). New here only: the same gate escalating to *thinking* of the same
model, priced in tokens, and how often agreeing answers are wrong (the check's leak).
**Predictions.**
- X1-P1 (Qwen3-32B, MATH-500): program no-think ≥ text no-think + 3 points; both ≥ 10 points below thinking.
- X1-P2 (Qwen3-32B, MATH-500): the gate is within 2 points of always-thinking at ≤ 50% of its tokens.
- X1-P3: among items where text and program agree, ≤ 5% are wrong (MATH-500), but ≥ 20% on AIME (agreement is a leaky check on hard problems).
- X1-P4 (AIME): program no-think and text no-think are both ≤ 30% for Qwen3-32B; thinking ≥ 60%; the gate recovers ≤ 80% of the gap
  (most AIME items disagree, so the gate escalates almost everything and saves little).
- X1-P5 (gpt-oss-20b, MATH-500): gate within 1 point of medium at ≤ 70% of its tokens.

## Status (2026-10-16 17:57 UTC)
Stopped by the user before any run (servers were started and shut down; no generations). Harness and data kept for later use.

## Taken over by the experiment session (2026-10-16 18:01 UTC, before any run)
The user asked the experiment session to "suggest and test for other math" after stopping the run here; X1 runs from the experiment
session on GPUs 0–3 with this pre-registration unchanged. **Harness note:** at 18:00 the experiment session wrote poc/run_math.py
without noticing the prepared version and overwrote it (the prepared file is lost); the new version uses the same data
(results/x1/problems.json) and the same grader (math-verify; a program's printed answer is also tried through sympy → LaTeX), writes
results/x1/math_<tag>_<mode>_s<seed>.jsonl. Caps: no-think 8,192 output tokens, thinking 28k, gpt-oss 16k.
**Addendum (before any run):**
- X1-P6 (decorrelation, the project's second-opinion lesson): agreement between the text and the program answer is a less leaky check
  than agreement between two text samples (seeds 1 and 2) at the same budget: among agreeing pairs, the wrong share is lower for
  text–program, for each model, on MATH-500 and on AIME.
- Exploratory third model: Qwen3.6-35B-A3B (text no-think, program no-think, thinking 28k), same analysis, no separate predictions.
**Harness bug found 18:09 UTC, before any analysis:** every first grade was 0 / 560 because math_verify's signal-based timeout raises
inside worker threads ("doesn't support threaded environment"), and the harness caught the error as "no answer". Raw outputs were fine
(e.g. `\boxed{\frac{14}{3}}`, program printing `14/3`). Fix: generation threads only store the raw text / program output; grading runs
afterwards in worker processes (`run_math.py --regrade`), and every file is regraded. No generation was repeated.

## Results, part 1 (2026-10-16 18:29 UTC; gpt-oss-20b, 560 problems × 3 seeds; results/x1/analysis_oss20.log)
| gpt-oss-20b | MATH-500 | AIME 24+25 | output tokens mean (p90) |
|---|---|---|---|
| text, low effort | 91.0% | 46.1% | 757 (1,804) |
| program, low effort | 73.4% | 39.4% | 324 (692); 204 of 1,680 without a code block, 119 crashes, 18 time-outs |
| text, medium effort | 95.4% | 68.9% | 2,210 (5,744); 60 cap hits |
| gate text == program → medium | **95.7%** @ 1.9k | 69.4% @ 8.9k | (medium alone: 1.6k / 7.3k) |
| gate text == text (next seed) → medium | 95.5% @ 1.9k | 69.4% @ 9.3k | |
Leak (wrong share among agreeing pairs): MATH-500 text–program **0.3%** (3 / 1,049) vs text–text **1.5%** (20 / 1,331); AIME 6.8% (3 / 44)
vs 13.5% (10 / 74). **X1-P6 holds for gpt-oss-20b:** a different method is a 2–5× less leaky check than a second sample of the same
method. **X1-P5 refuted:** the gate is +0.3 points over medium at 1.2 × its tokens, because medium effort is cheap for gpt-oss-20b
(1.6k on MATH-500) and the program disagrees often (it fails to produce a program or a closed form). Qwen3-32B / Qwen3.6: running.

## Results, part 2 (2026-10-16 22:30 UTC; Qwen3.6, 560 × 3; results/x1/analysis_q36.log)
text no-think 98.3% (MATH-500) / 68.3% (AIME) @ 1.6k (p90 4.0k, 33 caps); program 86.8% / 63.9% @ 1.0k; thinking (28k cap) 91.7% / 47.8% @
11.6k with **213 of 1,680 answers cut off at the cap** (AIME mean 24k tokens): thinking is worse than not thinking for this model at
this budget (the same failure as N10-M3). Gates escalate to the worse mode: text == program → thinking 96.7% @ 4.0k, text == text →
thinking 98.1% @ 3.1k, both below always-text. Leak MATH-500: text–program 0.5% (6 / 1,295) vs text–text 0.5% (8 / 1,467); AIME 2.1% vs
2.8%. **X1-P6 not supported for Qwen3.6** (equal leaks: its text answers are already 98% right, so both checks rarely see a wrong pair).

**Incident (2026-10-17 00:29 UTC):** the Qwen3-32B thinking runs (1,674 of 1,680 generations done after 5.8 h) died with the server at
2026-10-16 23:51:25 (all four servers terminated at once) and wrote nothing (rows were written only at the end). run_math.py now writes
each row as it completes and resumes from an existing file. Re-run with identical settings from 00:29 on GPU 1.

## X1-Q36R pre-registration (2026-10-17 08:39 UTC, before running): was "Qwen3.6 thinking is worse than not thinking" a setup failure?
Raw check: 213 of 1,680 Qwen3.6 thinking runs stopped at the 28k cap with no answer (12.7%), including level-1 MATH-500 problems
(e.g. test/geometry/434), which points to runaway reasoning rather than hard problems. Our harness sampled thinking with T 0.7, top_p
0.95, no presence penalty; the Qwen3.6 model card recommends T 1.0, top_p 0.95, top_k 20, presence_penalty 1.5 for thinking and shows
80k-token budgets. Re-run (tag q36c): the same 560 problems × seeds 1–3, thinking with the card's sampling (POC_THINK_SAMPLING in
poc/llm.py), cap 80,000 output tokens (server max-model-len 90,000), GPU1 (poc/queues/queue_s2_x1q36r.sh). Text and program arms (no
thinking) are reused. Analysis: X1_THINK_TAG=q36c python poc/analyze_x1.py q36.
- Q36R-P1 (setup): ≤ 2% of thinking runs hit the cap.
- Q36R-P2: thinking ≥ text without thinking on MATH-500 (98.3%), and ≥ text + 10 points on AIME (68.3% → ≥ 78.3%).
- Q36R-P3 (cost): mean thinking output on AIME ≤ 30k tokens.
- Q36R-P4 (policy): the gate (text == program → accept, else thinking) is within 1 point of always-thinking at ≤ 50% of its tokens (MATH-500).
If P1 holds and P2 fails, thinking does not pay for this model on these problems, independent of the setup.

## Results, part 3 (2026-10-17 08:39 UTC; Qwen3-32B, 560 × 3; thinking re-run finished 07:33; results/x1/analysis_q32b.log)
**Grader fix first (raw outputs):** program answers printed with sympy's imaginary unit (`6 + 9*I`) were graded wrong against `6+9i`
because math_verify does not equate `6 + 9 i` (sympy's LaTeX) with `6+9i`; 3–5 rows per program file (all models). `to_candidates` now
adds the LaTeX form without the space; all 9 program files regraded: program accuracy on MATH-500 +0.6 to +0.7 points (gpt-oss-20b
73.4 → 74.0%, Qwen3-32B 67.8 → 68.5%, Qwen3.6 86.8 → 87.5%); the gates move by ≤ 0.1. Remaining program errors read as real (degrees
printed as radians, unevaluated sums, wrong values).
Qwen3-32B (accuracy MATH-500 / AIME @ mean output tokens): text 86.1 / 19.4% @ 0.95k; program 68.5 / 24.4% @ 0.24k (270 runtime errors,
38 time-outs of 1,680); thinking 97.4 / 77.2% @ 5.4k (23 runs at the 28k cap).
- **X1-P1 refuted** (the program is 17.6 points *below* text on MATH-500; both are ≥ 10 points below thinking, as predicted).
- **X1-P2 half holds:** the gate text == program → thinking reaches 97.2% vs 97.4% (within 2 points) but at 77% of the tokens (3.4k vs
  4.4k), not ≤ 50%.
- **X1-P3:** leak among agreeing pairs 0.9% on MATH-500 (holds, ≤ 5%) and 18.8% on AIME (3 / 16; narrowly below the predicted ≥ 20%).
- **X1-P4:** text 19.4% and program 24.4% ≤ 30%, thinking 77.2% ≥ 60% (hold); the gate recovers 99% of the gap (refutes ≤ 80%) but costs
  more than always thinking (15.8k vs 13.5k tokens), because 95% of AIME items disagree and pay for text + program + thinking.
- **X1-P6 holds for Qwen3-32B:** text–program agreement is the less leaky check (0.9% vs text–text 3.4% on MATH-500; 18.8% vs 45.8% on AIME).
**Reading (cost-accuracy):** for Qwen3-32B, thinking is worth +11 points on MATH-500 and +58 on AIME. On MATH-500 a cheap second
view (a program) decides where to think and saves 23% of the tokens at −0.2 points; on AIME almost everything needs thinking, so
the cheapest policy is to think directly. The same split as the project's main result: spend compute where a cheap check fails,
and skip the check when it would fail almost everywhere.

## X1-SIZE pre-registration (2026-10-17 14:32 UTC, before running): competition math for models that fit one RTX 3090
Qwen3-4B, Qwen3-8B, Qwen3-14B-AWQ (tags q4b, q8b, q14a), the X1 problems (MATH-500 + AIME 2024/25), text / program / thinking (28k cap)
× seeds 1–3, same harness settings as Qwen3-32B (part 3) so the four Qwen3 sizes compare; GPU0 (q14a) and GPU3 (q8b, then q4b)
(poc/queues/queue_s2_x1size.sh). Analysis: python poc/analyze_x1.py q4b q8b q14a.
- X1-SIZE-P1: thinking − text on AIME ≥ +30 points for each model (Qwen3-32B: +58).
- X1-SIZE-P2: the gate text == program → else thinking is within 1 point of always-thinking on MATH-500 at ≤ 80% of its tokens, for each.
- X1-SIZE-P3: text–program agreement leaks less than text–text agreement on MATH-500 for each model (X1-P6).
- X1-SIZE-P4: Qwen3-14B-AWQ thinking reaches ≥ 65% on AIME (Qwen3-32B-AWQ: 77.2%).

## X1-Q36R results (2026-10-17 17:36 UTC; results/x1/analysis_q36c.log; 560 × 3)
| Qwen3.6 thinking | MATH-500 | AIME | runs at the cap | mean (p90) output tokens, AIME |
|---|---|---|---|---|
| old: T 0.7, no presence penalty, 28k cap | 91.7% | 47.8% | 213 / 1,680 | 24.1k (28.0k) |
| **card sampling, 80k cap** | **99.6%** | **94.4%** | 4 / 1,680 | 30.2k (57.8k) |
| text, no thinking (unchanged) | 98.3% | 68.3% | | 4.6k |
- **Q36R-P1 holds** (0.24% at the cap). **Q36R-P2 holds** (thinking ≥ text: +1.3 on MATH-500, +26.1 on AIME). **Q36R-P3 narrowly
  refuted** (AIME mean 30.2k > 30k). **Q36R-P4 holds** (gate text == program → thinking 99.3% @ 4.0k vs always-thinking 99.6% @ 9.1k: −0.3
  at 44% of the tokens; on AIME the gate is 94.4% @ 25.3k vs 30.2k).
- Which change mattered (from the new runs, counting a run as failed if it used more than the old cap): card sampling *with* a 28k cap
  would give 95.3% / 51.1%: the sampling is worth +3.6 / +3.3 points (fewer runaway runs: 67 vs 119 MATH-500 runs past 28k), the
  budget +4.3 / +43.3 (AIME runs need up to 58k tokens at p90).
**Reading:** "thinking is worse than not thinking for Qwen3.6" (part 2) was a setup failure, mostly the token cap. With enough budget
thinking is the most accurate mode (94.4% on AIME), and the cheap text == program gate keeps 99.3% on MATH-500 at 44% of its tokens.
The same cap (28k / 30k) also limited the Qwen3.6 thinking cells of U1 / U1r / U2 and X6 (re-run below / in PREREG_U1, PREREG_X3).

## X1-SIZE results, part 1: Qwen3-8B and Qwen3-14B-AWQ (2026-10-17 18:36 UTC; results/x1/analysis_size_partial.log; Qwen3-4B still running)
| model (fits a 3090) | text MATH-500 / AIME | program | thinking (28k cap) | gate text == program → thinking, MATH-500 |
|---|---|---|---|---|
| Qwen3-8B (yes) | 84.3 / 23.9% @ 1.1k | 65.5 / 21.7% @ 0.27k | 97.0 / 68.3% @ 6.6k (42 caps) | 96.7% @ 4.3k (thinking 5.5k) |
| Qwen3-14B-AWQ (yes) | 85.9 / 26.1% @ 1.0k | 66.4 / 18.9% @ 0.26k | 97.3 / 73.3% @ 5.9k (23 caps) | 97.1% @ 3.7k (thinking 4.7k) |
| Qwen3-32B-AWQ (part 3) | 86.1 / 19.4% @ 0.95k | 68.5 / 24.4% @ 0.24k | 97.4 / 77.2% @ 5.4k (23 caps) | 97.2% @ 3.4k (thinking 4.4k) |
- **X1-SIZE-P1 holds** (thinking − text on AIME: +44.4 / +47.2). **P2 holds** (gate −0.3 / −0.2 points at 78% / 79% of thinking's tokens).
  **P3 holds** (text–program leak 1.5% / 1.0% vs text–text 3.4% / 3.1% on MATH-500). **P4 holds** (Qwen3-14B-AWQ AIME 73.3% ≥ 65%).
**Reading:** on competition math the 3090-class Qwen3-14B-AWQ is within 0.1 (MATH-500) and 3.9 points (AIME) of Qwen3-32B at about the
same tokens; for all three sizes thinking is what solves AIME, and a program as a second view saves about a fifth of the tokens on
MATH-500 at −0.2 to −0.3 points.

## X1-SIZE results, part 2: Qwen3-4B (2026-10-17 20:36 UTC; results/x1/analysis_size.log)
Qwen3-4B: text 84.1 / 19.4% @ 1.1k; program 63.4 / 20.6% @ 0.34k; thinking 96.6 / 66.7% @ 6.3k (40 caps); gate text == program → thinking
95.7% @ 4.2k on MATH-500 (thinking 5.2k); leak text–program 2.1% vs text–text 4.8%.
- **P1 holds** (+47.3 on AIME). **P2 narrowly refuted** for 4B (−0.9 points but at 81% of the tokens, not ≤ 80%). **P3 holds.**
Across the four Qwen3 sizes (4B / 8B / 14B-AWQ / 32B-AWQ) thinking reaches 96.6 / 97.0 / 97.3 / 97.4% on MATH-500 and 66.7 / 68.3 / 73.3 /
77.2% on AIME at 5.2–6.6k tokens: competition math is solved by thinking at every size, and size buys AIME points, not MATH-500 points.

## ADAPT pre-registration (2026-10-19 10:43 UTC, before running): a learned when-to-think switch vs our label-free gate, same backbone
**Why.** Our recipe decides when to pay for thinking with a free check (two cheap answers agree → accept, else think). The closest
related work *trains* that decision: AdaptThink (Zhang et al. 2025, arXiv 2505.13417) uses RL so that DeepSeek-R1-Distill-Qwen-7B
skips thinking on easy problems (reported MATH-500 92.0% @ 1,875 tokens, 76.6% NoThinking, vs the base 90.2% @ 3,674; AIME 2024 55.6% vs
53.5%; 16K context, T 0.6). Nobody has compared the trained switch with a training-free check on the same backbone, nor combined them.
**Setup** (poc/run_adapt.py; poc/queues/queue_s2_adapt.sh, GPU1, both 7B servers): X1's 560 problems (MATH-500 + AIME 2024 + 2025),
seeds 1–3, the paper's settings (T 0.6, top_p 0.95, 16K context, DeepScaleR's 'Let's think step by step ... \boxed{}' instruction).
Base DeepSeek-R1-Distill-Qwen-7B (r1d7) and AdaptThink-7B-delta0.05 (adt7), each in three modes: think (the card template; r1d7 always
thinks, adt7 chooses), text and program in the paper's NoThinking mode (response starts with '</think>'). Grader: math-verify (as X1).
Costs: all output tokens. 3090: both are 7B (15 GB in bf16).
**Predictions.**
- ADAPT-P1 (replication): r1d7 think MATH-500 90.2 ± 3% at 3.7k ± 25% tokens; r1d7 NoThinking text 80.6 ± 4%; adt7 think 92.0 ± 3% at
  ≤ 60% of r1d7's thinking tokens with a NoThinking share of 65–85% on MATH-500 (and ≤ 20% on AIME).
- ADAPT-P2 (head-to-head, MATH-500): AdaptThink dominates our gate on the base model (gate = r1d7 NoThinking text == NoThinking program →
  accept, else r1d7 thinking): AdaptThink accuracy ≥ gate accuracy − 1 at ≤ 75% of the gate's tokens. Reason: R1-distill's NoThinking
  program is weak, so agreement is rarer than for Qwen3 and the gate pays two cheap answers on every problem.
- ADAPT-P3 (combination, new): a free check on AdaptThink's skipped thinking — when adt7 answers without thinking, also run a NoThinking
  program (adt7 prog); if they disagree, pay for r1d7 thinking — gains ≥ +1.0 point over AdaptThink alone on MATH-500 at ≤ +40% tokens.
- ADAPT-P4 (3090 frontier): on MATH-500 Qwen3-8B with our gate (96.7% @ 4.3k, X1-SIZE) is ≥ 3 points above AdaptThink-7B at ≥ 1.5× its
  tokens: neither dominates; on AIME Qwen3-8B thinking (68.3%) is ≥ 8 points above AdaptThink.
