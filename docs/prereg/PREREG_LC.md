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

**Amendment (2026-10-27 19:4x UTC, before any Qwen3.5-9B row is graded or analysed).** Qwen3.5-9B's thinking arms switch to the card's
*general* preset (T 1.0, top-p 0.95, top-k 20, presence penalty 1.5), still matched across the full and the cut think (tag q35g,
`hon_lane.sh lcbg lcb <seed>`, jobs 1263769–1263771); its non-thinking arm stays at the harness sampling. Why: SAMP (a), finished at
19:4x, shows that on the project's program-writing word problems the coding preset doubles the full think's 32k-capped, program-less runs
(95 vs 44 of 246; 149 vs 90 of 276) and lowers the check-matched think by 4.5–6.2 points, and the coding-preset LiveCodeBench thinks
finished so far show the same pattern (102 of 224 at the cap; finish reasons only, no grade read). A capped baseline flatters a short
think first (HO-CAP), which is what LC-1 tests. The coding-preset jobs (1262534 / 6 / 8) were stopped at 67–76 of 182 problems per seed;
their rows stay as a record (tag q35) and are reported for their cap rate only. Everything else is unchanged.

## Interim: Qwen3-14B-AWQ (2026-10-27 21:0x UTC; no decision until all three models are in, each prediction needs 2 of 3)
3 seeds × 182 problems, official grader (job 1264396). Accuracy (pass@1) @ tokens per problem:

| N | SB | T | N→T | N→SB→T | SB→T→T | T→T | N→T\|hidden |
|---|---|---|---|---|---|---|---|
| 27.5% @ 0.49k | 36.6% @ 3.19k | 55.1% @ 13.20k | 50.7% @ 10.43k | 48.5% @ 10.59k | 53.8% @ 16.46k | 57.3% @ 17.43k | 55.7% @ 12.53k |

- **LC-P1 refuted for this model:** SB→T→T − T→T = −3.5 [−5.7, −1.6] at 94% of its tokens (HO-CC: −1.5 [−3.3, +0.2] at 94%).
  The whole loss is leaked cut-think programs: of the 277 problem-seeds where SB passes the samples, SB is wrong on 77, and on 23 of
  those (medium 15, hard 7, easy 1) the check-matched think is right, against 4 the other way: −19 / 546 = −3.5. The saving is small
  because the cut think passes the samples on 23% of hard problems (T: 67%), where 63% of T's tokens sit, and then pays for both.
- **LC-P2 refuted:** N→T − T = −4.4 [−6.8, −2.2] at 79%. **LC-P3 holds:** the samples leak 33.6% of N's passing programs (76 / 226),
  27.8% of SB's (77 / 277) and **31.3% of T's (137 / 438)** — the full think leaks as much as the non-thinking program. **LC-P4 holds:**
  N→T|hidden − N→T = +4.9 [+2.9, +7.1] (DART's gate). Retry: T→T − T = +2.2 [+1.1, +3.5] at 132% (HO-CC: +4.5).
- **How leaks fail:** first hidden failure wrong answer / time limit / runtime error: N 44 / 32 / 0, SB 45 / 32 / 0, T 86 / 48 / 3. Wrong
  answers fail on small inputs (median failing input 6–7% of the problem's largest; half under 200 characters: edge cases the samples
  miss, e.g. abc391_d, a closed form that is wrong once a second row fills); time limits fail on large ones (57–79% at ≥ half the largest; the
  intended algorithm too slow in Python, e.g. abc390_d's Bell(12) partitions, 3716's O(300 n²) DP). Time limit is 42% of N's and SB's
  leaks (64 / 153), under the half that triggers the size check. Re-graded at 4 workers on 16 CPUs (`LCB_RECHECK=1`, job 1264444),
  134 of the 135 time-limit failures stay time limits (one passes): the time limits are not grading load.
- **Exploratory (not pre-registered): even a perfect check would not make the short think save here.** Gated on the hidden tests,
  SB→T→T|hidden is 61.7% @ 22.8k vs T→T|hidden 61.4% @ 21.7k (105% of its tokens); N→SB→T|hidden 56.6% @ 14.1k vs T 55.1% @ 13.2k. The
  cut think fails where the tokens are, so no check (a size check, ALGO's brute-force oracle 2305.14591, HardTests 2505.24098) can turn
  this model's leak into a saving; a better check would buy accuracy, as the retry does.
- Reported: S answers "yes" on 546 / 546 (S = T). T is cut at 32k on 3 / 546; SB's answer runs out of its 4k on 62 (58 without a
  program). By difficulty (T's share of tokens): easy 99% @ 3.7k (7%), medium 59% @ 13.2k (30%), hard 29% @ 18.4k (63%). Against the
  Qwen3 report (2505.09388; BF16, LiveCodeBench v5, 2024-10 → 2025-02): Qwen3-14B 63.5 thinking / 29.0 non-thinking; here 55.1 / 27.5 on
  2025 problems with the AWQ model. Grader: the official grader compares numbers exactly, so 2 of 182 problems with a stated float
  tolerance (abc392_d, 3763) fail right answers by digits (abc392_d's 9 programs count as leaks); without them every interval above moves
  by ≤ 0.2. Kept as pre-registered.
- Qwen3.5-9B at the coding preset (stopped runs, tag q35; reported for the cap only): T cut at 32k on 102 / 224 (hard 70 / 95), SB's
  answer at its 4k cap on 122 / 204; its non-thinking program runs to the 4k cap on 93 / 207 (it reasons in plain text at length,
  2.3–2.4k tokens on average) — the general-preset runs keep the same non-thinking arm.

## Interim 2: Qwen3-8B (2026-10-28 03:2x UTC; LC-P1 and LC-P3 are now decided, LC-P2 and LC-P4 wait for Qwen3.5-9B)
3 seeds × 182 problems, bf16 on two 3090s (jobs 1265067, 1265728, 1265729):

| N | SB | T | N→T | N→SB→T | SB→T→T | T→T | N→T\|hidden |
|---|---|---|---|---|---|---|---|
| 24.9% @ 0.50k | 35.5% @ 3.75k | 50.2% @ 14.52k | 48.9% @ 12.65k | 48.5% @ 13.78k | 52.0% @ 20.57k | 52.6% @ 20.09k | 50.7% @ 13.93k |

- **LC-P1 refuted for this model** (−0.5 [−2.0, +0.7]: a tie, but at 102% of T→T's tokens), so **LC-P1 is refuted** (0 of 2; the third
  model cannot make 2 of 3): short think → think → retry does not save on general contest code either. The cut think writes no program
  on 173 of 546 problem-seeds (32%; Qwen3-14B-AWQ 11%): it keeps reasoning in comments inside the code block until its 4k answer cap,
  on medium and hard problems, so the recipe pays for the cut think and the full one. Its leaks cost little here (9 problem-seeds where
  the check-matched think was right, 6 the other way), because this model's cut-think programs leak less (17.8%).
- **LC-P2 holds for this model:** N→T − T = −1.3 [−3.1, +0.2] at 87% of its tokens (the non-thinking program first, a tie at 87%;
  Qwen3-14B-AWQ: −4.4 at 79%, refuted). Its full think is weaker and dearer (50.2% @ 14.5k vs 55.1% @ 13.2k), so the cheap first step
  loses less; the saving sits on easy problems (N→T 93% @ 1.1k vs T 97% @ 3.9k) and on hard ones, where a passing N replaces a think that is
  mostly wrong too (20% @ 18.5k vs 20% @ 20.0k).
- **LC-P3 holds** (2 of 2): the samples leak 25.7% of N's passing programs (47 / 183), 17.8% of SB's (42 / 236), 33.7% of T's
  (139 / 413). **LC-P4 refuted for this model:** N→T|hidden − N→T = +1.8 [+0.5, +3.5], under the 2.0 points.
- How leaks fail (wrong answer / time limit / runtime error): N 26 / 19 / 2, SB 25 / 17 / 0, T 92 / 46 / 1; time limit is 40% of N's
  and SB's leaks (36 / 89; with Qwen3-14B-AWQ 100 / 242, 41%), under the half that triggers the size check. The low-load re-grade (job
  1265737) keeps 94 of 94 time limits. Raw: 3634's cut-think program pairs mirror letters with a stack but still pushes a matched
  index (a wrong answer on an 8-letter hidden input); abc392_d again fails by digits only (the grader's exact float comparison).
- Exploratory (as for Qwen3-14B-AWQ): gated on the hidden tests, SB→T→T|hidden 56.4% @ 26.1k vs T→T|hidden 56.0% @ 24.6k (106%);
  N→T|hidden 50.7% @ 13.9k vs T 50.2% @ 14.5k.
- Reported: S answers "yes" on 543 / 546. T is cut at 32k on 17 / 546; N runs out of its 4k on 16. Against the Qwen3 report (BF16,
  LiveCodeBench v5): Qwen3-8B 57.5 thinking / 22.8 non-thinking; here 50.2 / 24.9 on 2025 problems.

## Addendum LC-OSS (2026-10-28 03:2x UTC, before any gpt-oss row): does the contest boundary hold for gpt-oss?
**Why it could change the claim.** The contest statement ("contests need the full think") now rests on the hybrid-thinking models:
Qwen3-14B-AWQ and Nemotron-3-Nano on geometry (HO-CC), Qwen3-8B and Qwen3-14B-AWQ on LiveCodeBench (LC-P1 refuted), Qwen3.5-9B
running. gpt-oss is the family where the recipe is a pure saving on the word problems, with its own first step (a medium-effort think
cut at 2,000 tokens, HO-OSB) and a trained cheap mode that still reasons (low effort) instead of a non-thinking one. Its cut think ends
in a forced final channel, not inside a code block, so the failure that made Qwen3-8B pay twice (32% of cut thinks with no program) may
not occur. If the cut medium think first saves here, the contest statement is a property of the hybrid-thinking models, not of
contest code, and the claim names the family. **Prior work (2026-10-28 03 UTC, IDs opened):** the gpt-oss model card (2508.10925)
reports accuracy by effort level (low / medium / high), not an effort cascade gated by a check; CodeRescue (2607.19338) routes a
failed coding attempt between a cheap model's retry and a stronger model with a trained router (GPT-5.4-nano / GPT-5.4); DART, PaT,
S*, model cascading (above). No study found escalates gpt-oss's effort on a failed sample test.
**Run.** gpt-oss-20b (tag oss20, one RTX 3090, MXFP4, `--max-model-len 36864`), the same 182 problems, prompt, grader, seeds 1–3, every
arm at the harness sampling (T 0.7, top-p 0.95; matched): N = low effort (4k cap, as every cheap arm); SB = medium effort, the analysis
channel cut at 2,000 tokens, the final channel forced (`harmony_budget_chat`, LiveCodeBench's system turn as the developer message; 4k
answer cap); T = medium effort (the model's default; 32k); TH = high effort (32k). S is not run (no non-thinking mode to ask). Policies
as LC-1 (`analyze_lcb.py oss20`), and with TH in T's place (`LCB_THINK=thinkh`).
- **OSS-P4 (high effort is the full think here):** TH→TH is ≥ 2.0 points more accurate than T→T.
- **OSS-P1 (the recipe saves for gpt-oss on contest code):** SB→T→T ties or beats T→T (paired 95% upper bound ≥ 0) at ≤ 90% of its
  tokens; if OSS-P4 holds, also SB→TH→TH against TH→TH, and P1 holds only if it holds against both (a weaker full think flatters a
  short one, HO-CAP).
- **OSS-P2 (low effort first saves):** N→T ties or beats T at ≤ 90% of its tokens (if OSS-P4 holds, also N→TH against TH; both).
- **OSS-P3 (the samples leak):** ≥ 10% of the N programs that pass the samples fail a hidden test.
- Reported, no decision: everything LC-1 reports (by difficulty, leaks and how they fail, caps, raw failures), and the cut think's
  no-program rate against Qwen3's.
**Expected (stated now, not a rule).** OSS-P4 holds (high effort is gpt-oss's contest setting); OSS-P1 refuted (as for Qwen3: the
tokens sit on hard problems a 2k think does not solve), but closer than Qwen3's, since the cut think should write a program more often;
OSS-P2 more likely than for Qwen3 (low effort reasons, 1–3k tokens); OSS-P3 holds.
**Decision.** P1 holds → the contest statement is restated by family (hybrid-thinking models need the full think; gpt-oss's cut medium
think first saves): REPORT contests section, PROJECT claim, PROPOSAL and PROPOSAL_ko. P1 refuted → the contest boundary holds on a
third family; the claim stands and names it. P2 holds → low effort first saves on contest code for gpt-oss, stated the same way. P1
and P2 refuted → no further run on code for gpt-oss.
**Smoke (before the main runs; not part of the results).** seed 1, LCB_SUBSET=0/26 (7 problems), all four arms, graded and analysed in
the same job: if an arm writes no rows, the harmony cut think's final channel holds no code where the full think does, or the effort
levels do not change the think's length (low < medium < high), the harness is fixed before any main row.

*LC-OSS smoke (2026-10-28 03:4x UTC, job 1265873, seed 1, 7 problems; not part of the results): every arm wrote 7 rows; the effort levels
order the think (low 0.67k, medium 6.4k, high 12.4k tokens per problem); the cut medium think's forced final channel holds a program in
7 / 7 (on the two hard problems it reasons across 9–12 code blocks for 2.7–3.2k tokens first, and the last block is a program that
runs). One high-effort think on a hard problem stopped at 31,283 tokens with an empty final answer (no program: a visible failure, as
graded); the client now keeps the end of the reasoning and any tool-call count for such replies so the main rows say why. S is not run
(its rows hold an empty answer; S = N for gpt-oss and carries nothing). Main runs submitted: lcb_oss_s{1,2,3}.*

*LC-OSS mid-run note (2026-10-28 04:4x UTC, before any oss20 row is graded; rows so far: s1 ≈ half, s2–s3 ≈ a fifth).* At the shared
32k cap the high-effort think is cut on most hard problems: TH ends at the cap on 37 / 45 hard rows (82%, mean 30.3k tokens), 10 / 33
medium, 1 / 56 easy; the medium think (T) on 2 / 66 hard (mean 7.5k), 2 / 46 medium, 0 / 60 easy. A capped think has no final channel,
so it is graded as no program (a visible failure). Two medium thinks (of 167) stopped with an empty answer and reasoning that ends
"Let's implement in python to test." / "We'll test all subarrays.": gpt-oss reaching for the python tool it was trained with and not
given here (tool-call count 0: the call is not parsed). Both are graded as written. **Added rule (stated before grading; no rule above
changes):** OSS-P4 is scored, and reported, as "high effort at the 32k cap". If OSS-P1 or OSS-P2 holds against T→T while TH ends at
the cap on ≥ 20% of its rows, the claim is not restated until TH is rerun at a 64k cap (`--max-model-len 69632`, the same three
seeds, tag oss20 arm thinkh64) and the policy that held is scored again against it as in OSS-P1 (both comparators): a cap-bound full
think flatters a short one (HO-CAP). If P1 and P2 are refuted against T→T, the 64k run cannot change the claim and is not run.

## Results LC-OSS: gpt-oss-20b (2026-10-28 08:2x UTC; final, 3 seeds, official grader)
| policy | N | SB | T (medium) | TH (high) | N→T | N→SB→T | SB→T→T | T→T | N→T\|hidden | TH→TH | SB→TH→TH |
|---|---|---|---|---|---|---|---|---|---|---|---|
| accuracy | 44.9 | 53.1 | 61.9 | 41.6 | 59.0 | 59.7 | 64.7 | 66.3 | 64.1 | 45.8 | 55.9 |
| ktokens | 0.97 | 2.18 | 7.24 | 21.92 | 5.99 | 6.32 | 10.19 | 10.89 | 7.52 | 39.80 | 24.08 |
- **OSS-P4 refuted (high effort at the 32k cap):** TH→TH 45.8 vs T→T 66.3. TH ends at the cap with no program on 310 / 546 (57%;
  hard 76 / 82 in seed 1), so the comparator is T→T only.
- **OSS-P1 refuted:** SB→T→T − T→T −1.6 [−3.8, +0.4] at 94% of its tokens: a tie, not a saving.
- **OSS-P2 refuted:** N→T − T −2.9 [−5.7, −0.5] at 83% of its tokens.
- **OSS-P3 holds:** 24.4% of the N programs that pass the samples fail a hidden test (79 / 324); SB 17.8%, T 21.0%.
- Mid-run rule: neither P1 nor P2 holds against the medium think, so the 64k high-effort run cannot change the claim and is not run.
- **Decision (as stated):** P1 refuted → the contest boundary holds on a third family; the claim stands and names it. P1 and P2
  refuted → no further run on code for gpt-oss.
- Reported: the forced final channel removes Qwen3-8B's failure — the cut think leaves no program on 10 / 546 (2%; Qwen3-8B 32%,
  Qwen3-14B-AWQ 11%) — and the loss is leaks instead: 17 problem-seeds where SB's sample-passing program fails a hidden test and T is
  right (11 hard, 6 medium). Read: 3795 (LeetCode, medium), SB's bitset DP returns the first k at which every target is reachable and
  never returns 0 for an array that is already zero, a case no example covers; T checks it first. abc391_e (hard), SB's recursive
  majority DP is right but runs in an unjoined thread (below). By difficulty the hard problems carry 74–79% of the tokens (T 37% at
  12.0k; SB→T→T 39% at 17.3k; T→T 42% at 19.0k). Leaks fail by wrong answer 61 / 46 / 76 (N / SB / T), by time limit 16 / 13 / 11
  (20% of N's and SB's leaks; a low-load re-grade keeps 48 / 48 time limits). DART's honest-gate gap: N→T|hidden − N→T +5.1
  [+3.1, +7.3]. The medium think stopped with an empty answer on 7 / 546, 6 of them ending in "implement in python and test" (the
  python tool gpt-oss was trained with, not given here; no call parsed). Exploratory (no rule): N→SB→T ties one think (−2.2 [−5.1,
  +0.5]) at 87% of its tokens.
- **Grader sensitivity (found reading the raw failures; the grade stays official, as pre-registered).** The official grader runs a
  stdio program as a function under patched stdin / stdout and returns when that function returns, so a program that does its work in
  a thread it does not join (`threading.Thread(target=main).start()`, the contest idiom for a larger stack) reads and prints after the
  patches are gone and fails whatever it computes; a judge waits for the thread (checked: abc389_f's medium think fails sample 2 as
  graded and passes all three samples joined). No report of it in the LiveCodeBench issue tracker (searched 2026-10-28). Re-graded with
  `Thread.start` joining (`grade_lcb.py LCB_JOIN=1`): gpt-oss 77 threaded programs over N / SB / T (18 / 27 / 32; none in TH), 2 right as
  graded, 18 joined; Qwen3-14B-AWQ 71 (N 39, SB 28, T 4), 0 → 2; Qwen3-8B and Qwen3.5-9B write none. With threads joined
  (`analyze_lcb.py LCB_JOIN=1`): gpt-oss N→T − T −2.4 [−5.1, +0.2] at 83% — **OSS-P2 would tie**; SB→T→T − T→T −1.8 [−4.0, +0.2] at
  94% (P1 unchanged); Qwen3-14B-AWQ N→T − T −4.0 (official −4.4), no verdict changes. So OSS-P2's refutation rests on the grader: under
  a judge that waits for threads, low effort first is a bare tie with one medium think at 83% of its tokens, and 7.5 points below the
  check-matched think (T→T). The decision follows the official grade; the claim reports both.
