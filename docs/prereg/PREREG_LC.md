# Pre-registration LC: is "contests need the full think" about contest code, or about the geometry set?

Written 2026-10-27 16:2x UTC, before any main row (the smoke below runs alongside and is not part of the results); revised 16:3x UTC,
still before any main row: the project's own contest result (HO-CC / HO-CAP) is now the reference, the thinking cap is 32,000 for every
model (HO-CC's 16k cap left 57–87% of contest thinks without a program), and the criteria are HO-CC's so the two sets compare. Results
go below.

**Why it could change the claim.** The claim's contest statement rests on one set: 311 Codeforces geometry problems (HO-CC, PREREG_HO.md),
where short think → think → retry tied the check-matched think at 94% / 82% of its tokens (Qwen3-14B-AWQ / Nemotron-3-Nano; CC-P1
refuted at ≤ 90%), a non-thinking program first lost 5.5–7.8 points, and an uncapped think beat short thinking first (HO-CAP, −3.1). The
report states it as "contest problems need the full think". That set is hard and one domain (Qwen3-14B-AWQ's 32k think solves 40.8%).
LiveCodeBench is general contest code with graded difficulty (easy / medium / hard, AtCoder and LeetCode). If the recipe saves there,
the contest boundary was the geometry set's difficulty, and the claim is restated by difficulty; if not, the boundary is contest code
itself, now on a second set and for two models not tested on contests (Qwen3-8B, the leaky one; Qwen3.5-9B, the one whose check holds).
Two quantities are new either way: how often LiveCodeBench's sample tests leak, and what DART's scoring-test gate would report instead.
**Prior work (related-work check, 2026-10-27 16 UTC; IDs and numbers opened and verified).** In the project: HO-CC / HO-CAP (above);
CC-P2: cross-mode agreement flags leaked contest programs. Outside: DART (2606.23181, no training, Qwen3 0.6B–32B): two non-thinking
drafts, accept on agreement, else think with an entropy-set budget; on code (HumanEval, MBPP only) its gate *runs the drafts on the
reference tests that later score the answer*, so accept precision is 100% by construction (its own Limitations); re-gated on half of each
problem's assertions, precision falls to 92.5 / 97.9 / 98.1% (8B / 14B / 32B), and its code gains (up to +22.5 points) are measured with
that gate. PaT (2605.07248): try first, check on the given examples plus model-written tests, escalate to planning (not thinking), Qwen3
4B–32B non-thinking, HumanEval / MBPP / xCodeEval. Model cascading for code (2405.15842): small → large model gated by self-generated
tests (HumanEval, MBPP, APPS-intro), 26% cost cut. S* (2502.14382): public tests drive up to two revision rounds and selection on
LiveCodeBench, always reasoning, tokens not counted — in effect the check-matched think. Execution feedback without mode routing:
Self-Debugging (2304.05128), CodeT (2207.10397), AlphaCode's example-test filtering (2203.07814), repair vs resample at matched cost
(Olausson et al., 2306.09896). Trained mode routers: Thinkless (2505.13379), AdaptThink (2505.13417), AutoThink (2505.10832) on math;
LHRM (2505.14631) also on LiveCodeBench. Scale: Qwen3 report (2505.09388) LiveCodeBench v5 (2024.10–2025.02, 32k output): Qwen3-8B 57.5
thinking / 22.8 non-thinking, Qwen3-14B 63.5 / 29.0 (BF16). No study found reports how often programs that pass LiveCodeBench's samples
fail its hidden tests.
**Run.** Problems: LiveCodeBench (livecodebench/code_generation_lite, files test5 / test6) dated 2025-01-01 or later: 182 problems
(45 easy, 55 medium, 82 hard; 112 AtCoder stdin / stdout, 70 LeetCode functional; 2.6 sample tests and 40 tests in all per problem on
average; `poc/prep_lcb.py`). Every problem predates every model's release, so contamination is not controlled; it shifts all arms of a
model alike. LiveCodeBench's own generic prompt (system + question + format). Models, thinking cap 32,000 for all: Qwen3-8B (q8b, two
RTX 3090s, tensor parallel: one 3090 holds no 32k context in bf16) and Qwen3-14B-AWQ (q14a, one 3090), 36,864-token context, every arm
at the harness sampling (T 0.7, top-p 0.95), as HO-CC; Qwen3.5-9B (q35, one 3090), both thinking arms at its card's precise-coding
preset (T 0.6, top-p 0.95, top-k 20, no presence penalty; matched, the SAMP lesson), the non-thinking arm at the harness sampling.
Seeds 1–3, one job per model and seed. Per problem and seed (`poc/run_lcb.py`): N = non-thinking program (4k cap); S = the model's
yes / no answer to "would thinking first help?"; T = thinking program (32k); SB = thinking cut at 2,000 tokens (budget forcing), then
the program (4k cap). Grade (`poc/grade_lcb.py`, CPU partition): LiveCodeBench's official grader (`run_test`, repo @28fef95), 6 s per
test, its global timeout; tests run samples first, then hidden, so one run gives the free check (a program was extracted and passes
every sample) and the grade (passes every test). Policies (`poc/analyze_lcb.py`): N, T, SB, S; **N→T** (T where N fails the samples);
N→SB→T; **SB→T→T** (the recipe's default: SB; T where SB fails; the next seed's T where T fails too); **T→T** (the check-matched
think: T; the next seed's T where T fails the samples); N→T|hidden (gated on the hidden tests: DART's code gate). Utility = accuracy −
0.5 × ktokens; paired 95% intervals over problems (seed means). "Ties or beats" = the paired 95% interval's upper bound ≥ 0 (CC-P1).
- **LC-P1 (the recipe's default saves on contest code):** SB→T→T ties or beats T→T at ≤ 90% of its tokens, for ≥ 2 of 3 models.
- **LC-P2 (cheap first saves on contest code):** N→T ties or beats T at ≤ 90% of its tokens, for ≥ 2 of 3 models.
- **LC-P3 (the samples leak):** ≥ 10% of the N programs that pass the samples fail a hidden test, for ≥ 2 of 3 models.
- **LC-P4 (an honest gate costs DART-style routing):** N→T|hidden is ≥ 2.0 points more accurate than N→T, for ≥ 2 of 3 models.
- Reported, no decision: every policy by difficulty with its share of the tokens (where the saving sits); the leak of N, SB and T with
  how the first hidden test fails (wrong answer / time limit / runtime error); S's yes-rate; thinks at the cap; raw failures read;
  Qwen3-14B-AWQ against its own HO-CC numbers.
**Expected (stated now, not a rule).** From HO-CC: LC-P1 is close (SB→T→T was at 82–94% of T→T's tokens on geometry); LiveCodeBench's
easy and medium problems, where a 2k think should pass the samples, make it more likely to hold than on geometry. LC-P2 refuted (on
geometry the non-thinking program first lost 5.5–7.8; here non-thinking pass@1 is 23–29% in the Qwen3 report, and T's tokens sit on
the hard problems where N passes nothing). LC-P3 holds (15–35% leak, many by time limit: Python, hidden max-size inputs), LC-P4 holds.
**Decision.** P1 holds → "contests need the full think" was the geometry set, not contest code: the claim's contest statement is
restated by difficulty (REPORT contests section; PROJECT claim; PROPOSAL and PROPOSAL_ko). P1 refuted → the contest boundary holds on
general contest code and for Qwen3-8B / Qwen3.5-9B too; the claim stands, now with two sets, and the by-difficulty table says where
the tokens that cannot be saved sit. P2 holds → cheap first saves on contest code (against HO-CC; restated in the same places). P1 and P2
refuted → next, only if at least half of the leaks of N and SB fail by time limit: a size check (the model writes, once per problem and
non-thinking, a generator of one maximum-size input; a program that does not finish on it within the limit fails the check),
pre-registered then; otherwise no further run on code. P3 → the sample tests leak on contest code (measured, with how). P4 → DART's
code results would shrink by about that much under an honest gate (REPORT §6.5).
**Smoke (before the main runs; not part of the results).** Qwen3-8B, seed 1, LCB_SUBSET=0/26 (7 problems), all arms (submitted before
the revision, so at a 16k think on one 3090), graded and analysed in the same job (job 1262398). It checks the harness only: if an
arm's rows are missing, code is not extracted from a response that holds a code block, or the grader fails in the image, the harness is
fixed before any main row.

*LC smoke (2026-10-27 16:3x UTC, job 1262398, Qwen3-8B, seed 1, 7 problems, a 16k think on one 3090; not part of the results): every
arm wrote all 7 rows; code was extracted from every response that closes a code block; the official grader runs in the image (N 4 / 7
right, T 5 / 7, SB 3 / 7; one N and one SB program pass the samples and fail a hidden test with a wrong answer). Both hard-problem thinks
hit the 16k cap without a program (the main runs use 32k), and on both the cut think's answer ran to its 4k cap writing reasoning as
comments inside an unclosed code block — no program, a visible failure, as LiveCodeBench's own extraction treats it. **Fixed before any
main row:** the yes / no question showed the problem last, so its format line made the model start the program (a code block in 1 of 7
answers, "yes" and then code in the other 6); it now shows the problem without its format line, asks last, and has no system turn. S
carries no decision. Main runs submitted 16:3x UTC: lcb_q14a_s{1,2,3} (1262533, 1262535, 1262537; `lane.sh --vllm '--max-model-len
36864'`) and lcb_q35_s{1,2,3} (1262534, 1262536, 1262538; `hon_lane.sh lcb lcb <seed>`); Qwen3-8B (two 3090s per seed) follows when
the IF-1 jobs free their GPUs.*

*Operations (2026-10-27 17:2x UTC, no change to the design): one RTX 3090 on n22 has ~10 GB held by a process outside Slurm's
allocation, so vLLM refuses to start on it (13.0–13.4 of 23.6 GiB free). lcb_q14a_s3 (1262537) and lcb_q8b_s{1,2,3} (1262745–1262747)
landed on it and exited at server start without a row; resubmitted with `-x n19,n22` as 1262743 and 1262807–1262809. First rows read
(17:1x UTC): the yes / no question now gets one-word answers (Qwen3-14B-AWQ: "yes" on 31 of 31; Qwen3.5-9B: 3 of 3 so far); 0 failed
requests. Throughput is KV-bound at 32k (3–4 thinks at a time, 115–150 tokens/s per job), so each seed takes about 6–7 hours.*
