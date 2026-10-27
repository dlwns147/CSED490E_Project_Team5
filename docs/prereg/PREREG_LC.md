# Pre-registration LC: the recipe on contest code, where the free check is the problem's own sample tests

Written 2026-10-27 16:2x UTC, before any main row (the smoke below runs alongside and is not part of the results). Results go below.

**Why it could change the claim.** The recipe (cheap answer → free check → think only on a visible failure) saves tokens where the
check is free and full thinks are long. Its two transfer tests so far had no tokens to save: tool calls (TC-1, thinks of 0.3k tokens)
and instructions (IF-1, a checker that costs more than the think). Contest code is the canonical case the claim should cover: every
problem ships sample tests (a free check that needs no labels), and thinking models spend 10k+ tokens per problem. It can fail in two
ways the word problems did not show as strongly: the samples are small, so a program can pass them and still be wrong or too slow on
the hidden tests (the leak), and the tokens may sit on hard problems the cheap answer never solves, so skipping thinking where the
cheap answer passes saves little. Either outcome bounds the claim with a measured mechanism.
**Prior work (related-work check, 2026-10-27 16 UTC; IDs and numbers opened and verified).** Closest: DART (2606.23181, no training,
Qwen3 0.6B–32B): two non-thinking drafts, accept on agreement, else think with an entropy-set budget; on code (HumanEval, MBPP only) its
gate *runs the drafts on the reference tests that later score the answer*, so accept precision is 100% by construction (its own
Limitations); re-gated on half of each problem's assertions, precision falls to 92.5 / 97.9 / 98.1% (8B / 14B / 32B), and its code gains
(up to +22.5 points) are measured with that gate. PaT (2605.07248): try first, check on the given examples plus model-written tests,
escalate to planning (not thinking), Qwen3 4B–32B non-thinking, HumanEval / MBPP / xCodeEval. Model cascading for code (2405.15842):
small → large model gated by self-generated tests (HumanEval, MBPP, APPS-intro), 26% cost cut. S* (2502.14382): public tests drive up to
two revision rounds and selection, on LiveCodeBench, always reasoning, tokens not counted — in effect our check-matched think. Execution
feedback without mode routing: Self-Debugging (2304.05128), CodeT (2207.10397), AlphaCode's example-test filtering (2203.07814),
repair vs resample at matched cost (Olausson et al., 2306.09896). Trained mode routers: Thinkless (2505.13379), AdaptThink (2505.13417),
AutoThink (2505.10832) on math; LHRM (2505.14631) also on LiveCodeBench. Reported scale: Qwen3 report (2505.09388) LiveCodeBench v5
(2024.10–2025.02, 32k output): Qwen3-8B 57.5 thinking / 22.8 non-thinking, Qwen3-14B 63.5 / 29.0 (BF16). No study found reports how
often programs that pass LiveCodeBench's samples fail its hidden tests. **New here:** the cheap-first and short-think-first cascades on
contest code with a gate that sees only the samples, against always thinking and the check-matched think, with output tokens counted,
the leak measured with how it fails, and what DART's scoring-test gate would have reported on the same rows.
**Run.** Problems: LiveCodeBench (livecodebench/code_generation_lite, files test5 / test6) dated 2025-01-01 or later: 182 problems
(45 easy, 55 medium, 82 hard; 112 AtCoder stdin / stdout, 70 LeetCode functional; 2.6 sample tests and 40 tests in all per problem on
average; `poc/prep_lcb.py`). LiveCodeBench's own generic prompt (system + question + format). Models: Qwen3-8B (q8b) and Qwen3-14B-AWQ
(q14a), one RTX 3090 each, 20,480-token context, thinking cap 16,000 (the project's cap for these models), every arm at the harness
sampling (T 0.7, top-p 0.95); Qwen3.5-9B (q35), thinking cap 32,000 (as on the word problems), both thinking arms at its card's
precise-coding preset (T 0.6, top-p 0.95, top-k 20, no presence penalty: matched, the SAMP lesson), the non-thinking arm at the harness
sampling. Seeds 1–3, one job per model and seed (9 jobs). Per problem and seed (`poc/run_lcb.py`): N = non-thinking program (4k cap);
S = the model's yes / no answer to "would thinking first help?"; T = thinking program; SB = thinking cut at 2,000 tokens (budget
forcing), then the program (4k cap). Grade (`poc/grade_lcb.py`, CPU partition): LiveCodeBench's official grader (`run_test`, repo
@28fef95), 6 s per test, its global timeout; tests run samples first, then hidden, so one run gives the free check (a program was
extracted and passes every sample) and the grade (passes every test). Policies (`poc/analyze_lcb.py`): N, T, SB, S; **N→T** (T where N
fails the samples); N→SB→T; **SB→T→T** (the recipe's default from HO-SB: SB; T where SB fails; the next seed's T where T fails too);
**T→T** (the check-matched think: T; the next seed's T where T fails the samples); N→T|hidden (gated on the hidden tests, DART's code
gate). Utility = accuracy − 0.5 × ktokens; paired 95% intervals over problems (seed means).
- **LC-P1 (cheap first saves):** N→T is within 1.0 point of T's accuracy (or above) at ≤ 85% of T's output tokens, for ≥ 2 of 3 models.
- **LC-P2 (the recipe's default saves against the check-matched think):** SB→T→T is within 1.0 point of T→T's accuracy (or above) at
  ≤ 85% of its tokens, for ≥ 2 of 3 models.
- **LC-P3 (the samples leak):** ≥ 10% of the N programs that pass the samples fail a hidden test, for ≥ 2 of 3 models.
- **LC-P4 (an honest gate costs DART-style routing):** N→T|hidden is ≥ 2.0 points more accurate than N→T, for ≥ 2 of 3 models.
- Reported, no decision: every policy by difficulty with its share of the tokens; the leak of N, SB and T with how the first hidden
  test fails (wrong answer / time limit / runtime error); S's yes-rate; thinks that hit the cap (no program); raw failures read.
**Expected (stated now, not a rule).** N passes the samples on 30–40% of problems (non-thinking pass@1 is 23–29% in the Qwen3 report)
and leaks on 15–35% of those, many by time limit (Python, hidden max-size inputs); T's tokens concentrate on hard problems (> 60% of
them on the 45% that are hard), where N passes nothing, so N→T saves ≤ 10% and loses 1–4 points: LC-P1 refuted, LC-P3 and LC-P4 hold.
SB→T→T is the open one: a 2k think should pass the samples on most easy and some medium problems.
**Decision.** P1 holds → the cheap-first saving extends to contest code under an honest gate (new REPORT section; PROJECT claim;
PROPOSAL and PROPOSAL_ko). P1 refuted, P2 holds → on code the saving needs the short think first: SB→T→T is the recipe's general form
(claim restated in the same places). P1 and P2 refuted → contest code is a boundary, explained by where the tokens sit (by difficulty)
and by the leak; next, only if at least half of the leaks of N and SB fail by time limit: a size check (the model writes, once per
problem and non-thinking, a generator of one maximum-size input; a program that does not finish on it within the limit fails the
check), pre-registered then; otherwise no further run. P3 → the sample tests leak on contest code (measured, with how). P4 → DART's
code results would shrink by about that much under an honest gate (REPORT §6.5).
**Smoke (before the main runs; not part of the results).** Qwen3-8B, seed 1, LCB_SUBSET=0/26 (7 problems), all arms, graded and
analysed in the same job (job 1262398). Amendment rules fixed now: if an arm's rows are missing, code is not extracted from a response
that holds a code block, or the grader fails, the harness is fixed first; if 3 or more of the 7 thinks hit the 16k cap without a
program, the Qwen3 thinking cap becomes 32,000 on two RTX 3090s (tensor parallel) before any main row, recorded here.
