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
