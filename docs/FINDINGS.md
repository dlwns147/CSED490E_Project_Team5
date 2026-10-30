# PoC findings log

Setup: GPUs are blocked (container lost access to the device files: EPERM, which needs a container restart), so everything runs
on CPU with llama.cpp. Main model is Qwen3-8B Q4_K_M with thinking OFF, temperature 0.7, 16 slots. CIs come from a
cluster bootstrap over problems.

## PoC #2: breaking subtly-wrong solutions (2026-10-04, Qwen3-8B, 40 items × k=2)

Benchmark: 128 CodeContests items (data/hack_bench.jsonl). Each has 3 agreeing Python reference solutions and 1 wrong
Python solution that passes the public tests but gets WA on a hidden test. A hack = an input on which all 3 references
run cleanly and agree, and the wrong solution's output differs.

| strategy | hack@1 | 95% CI | any@2 | invalid |
|---|---|---|---|---|
| blind (no code shown) | 0.138 | [0.05, 0.24] | 0.175 | 0.04 |
| direct (code shown) | 0.087 | [0.01, 0.19] | 0.100 | 0.00 |
| bugfirst (explain bug, then input) | 0.113 | [0.04, 0.20] | 0.175 | 0.01 |
| stress (LLM generator, ≤100 random inputs, reference = oracle) | 0.412 | [0.29, 0.54] | 0.550 | 0.11 |

- **Seeing the buggy code does not help a single-shot input** (direct − blind = −0.05 [−0.19, +0.09]). An 8B
  non-thinking model doesn't use the code. Explaining the bug first doesn't help either (+0.03, CI spans 0); bug
  explanations read plausibly but are often wrong.
- **Generators win clearly** (stress − direct = +0.33 [+0.17, +0.46]). But 52% of stress hits come on the FIRST
  random input, and the hit generators look generic, not targeted. Open question: is this targeting or plain random
  testing? A `stress_blind` control (same generator task, no code) is queued.
- Format compliance is its own failure mode. Before the prompt spelled out "include the t line", 8/8 generators left out
  the test-count line and every input was invalid.
- Harness bug found and fixed: in `bugfirst`, the model writes an ```input block and then an expected-output block.
  Parsing took the last block, which made 9/80 inputs falsely "invalid". Now the labelled input block is preferred, and
  saved responses were re-scored with `rescore_hack.py`: 8 verdicts changed.
- **stress_blind control (done 04:30):** the same generator task without the buggy code gives hack@1 0.287
  [0.19, 0.39]. **stress − stress_blind = +0.125 [−0.03, +0.26]**, so most of the generator gain is plain random
  testing. Reading the code adds maybe +0.1, and the CI still spans 0. Breakdown: with the code, generators are valid
  more often (0.89 vs 0.79; the buggy code also shows how input is parsed) and hit more often when valid (0.46 vs 0.37).
  Tightening this contrast on all 128 items is queued.
- Caveat: stress gets 100 oracle comparisons, single-shot gets 1. A realistic version needs an LLM-written brute-force
  checker instead of the reference solution.

## PoC #1: rewritten statements (eval set done, 2026-10-05 01:35, 58 paired problems, k=2)

Two validity problems found in the harness, both handled in `analyze.py perturb` (strict mode):
1. **Problems with several correct answers.** Statements that say "print any of them" need a special checker, and the
   exact-match judge marks correct answers wrong. That's ~1/3 of easy problems (16/58 here; 56/282 across all
   CodeContests eval problems). Strict mode excludes them.
2. **Rewrites that break the I/O format.** The story rewrite sometimes renames the input alphabet (A/B/C → X/Y/Z,
   a/b → G/S), so the original tests no longer match the statement. Caught by checking that the example input still
   appears verbatim (9 problems). The rewrite prompt is now fixed (keep the same letters/symbols).

| strict, n=33 | pass@1 | 95% CI |
|---|---|---|
| orig | 0.242 | [0.14, 0.36] |
| story | 0.318 | [0.18, 0.47] |
| formal | 0.242 | [0.12, 0.38] |

story − orig = **+0.08 [+0.00, +0.15]**; formal − orig = 0.00 [−0.08, +0.09].
- No memorization drop. If anything, the story version is slightly *easier*. One hypothesis: the rewriter is the same
  model, so a rewrite in its own words is easier for it to read ("self-paraphrase effect"). Test it with a different
  rewriter model.
- n is small, and 8B non-thinking only solves ~25% of 800–1200-rated problems. The larger clean run (95 problems) is
  queued. A real study should use problems published after the cutoff vs. before (LiveCodeBench) and stronger models
  (needs the GPUs).

## PoC #5: simulating algorithms in text (done 04:30, Qwen3-8B, 12 instances per cell, temperature 0)

| task | n | direct | CoT | code | majority baseline | CoT truncated |
|---|---|---|---|---|---|---|
| BFS | 6 / 12 / 24 / 48 | .42 / .17 / .17 / .17 | **.92 / .75 / .42 / .08** | 1.00 all | .50 / .50 / .33 / .25 | 0 / 0 / .42 / .92 |
| knapsack | 6 / 12 / 24 / 48 | .25 / 0 / 0 / 0 | .08 / 0 / 0 / 0 | 1.00 all | .17 / .17 / .08 / .08 | .25 / 0 / .17 / .25 |
| LIS | 6 / 12 / 24 / 48 | .67 / .42 / .17 / 0 | **.83 / .75 / .42 / 0** | 1.00 all | .67 / .50 / .33 / .33 | 0 / 0 / 0 / .83 |

- Answer-only (after the prefill fix; every response parsed) is at or below the majority-guess baseline. The model can't
  shortcut these tasks.
- CoT helps for BFS and LIS at small n, then falls off steeply. Knapsack simulation never works.
- Code (tool use) is perfect. The interesting research questions are therefore *where and why* text simulation breaks:
  wrong state update vs. right trace with a wrong read-out (seen in raw traces), and length generalization with a
  bigger token budget. Truncation confounds n=48, see the note below.
- Harness bug, fixed: the first answer-only run was invalid (the model explained instead of answering, the output
  was truncated and the wrong number parsed). Fixed with an assistant prefill; the old rows are archived.
- Truncation confound: 92% of BFS n=48 and 83% of LIS n=48 CoT runs hit the 3072-token limit. Rerun with a larger
  budget on GPU and score completed traces separately.

## PoC #1b: older problems (CodeContests train shards, contest ids 5–1547), partial at 05:35 (43/95 problems)

Unique-answer problems only, with the fixed rewrite prompt. 6/190 rewrites still break the I/O format (excluded).
- orig 0.45, story 0.37, formal 0.41. **story − orig = −0.08 [−0.20, +0.03]**; solved→unsolved 9 vs. unsolved→solved 2.
- This is the opposite sign from the newer eval-split problems (contest ids 1548–1623: +0.08). Older problems are
  both easier for the model (0.45 vs 0.24) and more sensitive to rewording. That fits a memorization story and is
  exactly the before/after-cutoff design idea #1 proposes. **Confounds:** rating mix, problem age and the source split
  differ. Proper version: match on rating, use more recent problems (LiveCodeBench dates), and use a rewriter different
  from the solver. Partial result; wait for the full run.

## Novelty check (2026-10-05 ~06:00)
- PoC #2 overlaps heavily with **REFUTE** (arXiv 2502.19414). REFUTE has the model output a *generator program*,
  uses a **code-blind random generator** to filter out easy items, and has a **RandSearch** baseline (random
  generator + LLM brute force). So "does reading the code help?" and "oracle-free stress testing" are partly
  covered. **TestCase-Eval** (2506.12278) covers single-input fault exposure (Qwen3-8B 41.3%, Qwen3-32B 43.8%;
  includes RE/TLE faults, unlike our wrong-answer-only, passes-public-tests setting). The remaining angle is narrower:
  budget-matched per-item code-aware vs. code-blind comparisons across sizes and thinking modes.
- Background literature scans for all candidate topics are running (agents); the topic ranking gets updated when
  they report.
- Scan 1 (current PoCs) is back. URLs were opened by the agent; verify against the PDFs before citing:
  - **A, counterexamples: medium novelty.** Also relevant: CodeHacker 2602.20213 (thinking 64.8% vs non-thinking
    23.8%; removing the code analyst costs only ~1.5pt, but there's no fully code-blind ablation), UOJ-Bench
    2606.12864, RL testers CURE/UTGen/Code-A1. **Open:** a per-item, budget-matched code-aware vs. code-blind ×
    thinking/non-thinking design, plus a **placebo** (show a *different* wrong solution), plus a bug-localization step
    as a mediator. Needs ~150–300 items.
  - **B, rewrites/contamination: low–medium.** StoryCoder 2604.14631 and MIMIC 2609.16076 show rewrites *raise*
    scores (clarity/"recall shortcut"; MIMIC Qwen3-8B 23.8 → 34.4 → 42.2). That confounds story−orig.
    **Open:** a difference-in-differences design (story−orig, pre- vs. post-cutoff), which is exactly our +0.08 / −0.08
    contrast, with rewriter≠solver controls.
  - **C, executing algorithms in text: medium only for the trace-checking angle.** Length collapse and code > CoT are
    known (CLRS-Text, Faith&Fate, Illusion of Thinking, GrAlgoBench). **Open:** a step-level reference checker that
    splits failures into a wrong state update vs. a correct trace with the wrong final answer, across thinking modes,
    with truncation controlled.

## PoC #1b: older problems DONE (06:35): difference-in-differences signal
Qwen3-8B, 89 strict-valid unique-answer CF problems (contest ids 5–1547), k=2:
orig 0.506, story 0.427, formal 0.416. **story − orig = −0.079 [−0.15, −0.02]**, formal − orig = −0.090 [−0.18, −0.01]
(solved→unsolved 13 vs. 3 for story; 18 vs. 4 for formal). Both CIs exclude 0.
- **DiD (newer minus older): story +0.154 [+0.057, +0.257]**; formal +0.090 [−0.03, +0.21].
- It holds within rating strata. At rating 800: newer orig 0.32, story−orig +0.18 (n=17); older orig **0.68**,
  story−orig **−0.18** (n=22). At equal rating, older problems are far easier for the model *and* lose accuracy when
  reworded. That is the memorization signature, and it runs opposite to StoryCoder/MIMIC's "rewrites help", which
  only shows up on newer problems here.
- Caveats: the newer-set rewrites used the pre-fix prompt (both sets strict-filtered); era effects (older problems
  may just be simpler); rewriter = solver; small newer set. The full study needs a dated pre/post-cutoff split
  (LiveCodeBench), rewriter≠solver, and n≈300 per side.

## PoC #6: special checkers / grading distortion. Exact-match baseline (06:44)
43 multi-answer CodeContests eval problems (≥2 Python-3 correct and incorrect solutions each), up to 40 tests,
≤5 correct and ≤10 incorrect solutions per problem.
- **Exact-match grading falsely rejects 64/199 = 32% of solutions that Codeforces ACCEPTED.** That hits 24/43
  problems, and on 4 of them *every* correct solution is rejected. Exact match "catches" 92% of incorrect
  solutions, but those catches can't be told apart from the false rejections.
- So any benchmark that grades CodeContests-style multi-answer problems by exact match under-counts pass rates on
  those problems. This needs no LLM to show, and it frames the checker study. LLM-written checker accuracy
  (Qwen3-8B, k=2) is running now.
- Harness note: a monitor's `pgrep -f` pattern matched its own command line and deadlocked the queue for ~10 min.
  Fixed by stopping the monitor; avoid pgrep -f on literal script arguments in watchers.
- **Checker v1 (07:25): invalid, rerunning as v2.** LLM checkers "falsely rejected" 74% of accepted solutions
  (worse than exact match's 32%), with only 6/43 problems having a checker perfect on all labelled solutions. Breaking
  down the verdicts showed the cause was harness/prompt, not model skill: 27/82 checkers errored on every case. The
  main cause: CodeContests test files hold *many* test cases (first line t), while the checkers parsed `inp` as a single
  case (`int('7\n1\n2…')` → ValueError). A second cause: checkers that read stdin or print at import swallowed the
  harness's JSON payload. Fixes: the prompt now states that inp/out are whole multi-case files, the checker source is
  exec'd with stdin emptied, and the last stdout line is parsed. v1 artifacts are archived in results/archive/.
  Lesson worth keeping for the project: **checker quality depends heavily on a precise I/O contract**, and
  "error = reject" can make an LLM checker look worse than exact match.
- **Checker v2 (08:30): still partly a harness artifact, re-evaluating as v3.** FRR 0.63 / 0.65, catch rate
  0.87 / 0.94, 8/43 problems with a checker perfect on all labelled solutions. Breakdown: 29 checkers accept every
  correct solution, 11 reject every correct one, 20 mixed, 22 "all-error". Of the all-error ones, some are real model
  bugs: wrong parsing (ValueError/IndexError on multi-case files, e.g. treating "YES" as an int), Syntax/NameError.
  But some work when called directly and failed only because the 400-case batch hit the 120 s timeout (one slow
  checker made the whole problem None). Fix: batches of 20 with a 40 s timeout, and false rejects split into
  "explicit False" vs. "only via error/timeout". The checkers are not regenerated; v3 re-scores the same 86.
- **Checker v3 (09:30): valid result, and a negative one for 8B checkers.** The timeout fix didn't change the
  numbers, and the false rejects are mostly *explicit* `False` verdicts: 94/200 and 97/199, against 32 via
  error/timeout. Inspection confirms real model errors. Example, 1594_C "Make Them Equal": instead of validating the
  contestant's operations against the reference *count*, the checker re-derives its own (wrong) "optimal" answer,
  demands sorted(x) equal it, and misparses the m=0 case (no second line).
  - Per (problem, sample): the LLM checker makes **fewer** errors than exact match on 13, **more** on 54, ties on 15.
    **Qwen3-8B non-thinking checkers are worse than exact match.**
  - Only 8/43 problems get a checker that's perfect on all labelled solutions. Labelled accepted/rejected solutions
    are therefore essential for *selecting* checkers (as AutoCode does with frontier models).
  - Re-grading the solver's own solutions on those 8 problems (12 attempts): exact match 0 AC, perfect checker 2 AC.
    Exact match under-counts here too (tiny n).
  - Project angle: "checker generation for small open models": failure taxonomy (re-solving instead of validating,
    parsing multi-case files, missing optimality-vs-reference logic), selection by labelled solutions, thinking mode,
    and how grading errors move benchmark rankings.

## PoC #2c: placebo control, partial (10:35, 74/128 items paired, k=2, 100 generator calls each)
| generator strategy | hack@1 | valid input | hack given valid |
|---|---|---|---|
| no code (stress_blind) | 0.33 | 0.78 | 0.42 |
| **different** wrong solution shown (stress_placebo) | 0.45 | 0.90 | 0.50 |
| target wrong solution shown (stress) | 0.47 | 0.90 | 0.52 |
- stress − blind = **+0.14 [+0.03, +0.25]**, now significant with more items. **stress − placebo = +0.02
  [−0.09, +0.13]**; placebo − blind = +0.12 [+0.00, +0.25].
- **Showing code helps about as much when it's the WRONG program.** The benefit doesn't come from finding the target's
  bug. It comes mostly from seeing *some* solution: valid-input rate rises 0.78 → 0.90 (the code shows how the input is
  parsed), and hit rate given a valid input rises a little. So for Qwen3-8B non-thinking, "reading the bug" adds ≈0 on
  top of "reading a solution". This is the measurement prior work hadn't made (REFUTE/CodeHacker have no placebo).
  The obvious next question: does thinking mode or a bigger model open a target-vs-placebo gap? (needs the GPUs)

## PoC #7: compression × algorithmic tasks (queued 10:55, after the 128-item PoC #2 run)
Prompted by the user: combine with LLM efficiency. Six configs of Qwen3-8B on llama.cpp:
weights Q8_0 / Q4_K_M / Q3_K_M / Q2_K (KV f16), and Q4_K_M with KV cache q8_0 / q4_0. Per config:
wikitext-2 PPL (40×512 tokens); text simulation (BFS, LIS, n=6/12/24, CoT + code, temperature 0, so answers can be
compared item by item against Q8_0); counterexample stress test (40 items, k=2).
Question: is degradation on verifiable algorithmic tasks (especially long CoT, where KV quantization should hurt
most) visible in PPL, or "PPL-blind"? A literature scan for this combination is running.
- Literature scan (compression × algorithmic reasoning; abstracts only, verify before citing):
  - Covered: weight quantization on math/LiveCodeBench (W4A16 ≈ lossless; 3-bit risky: 2504.04823); quantization
    inflates CoT length (2606.25519, 2606.00206); KV eviction on math CoT (R-KV, Hold Onto That Thought); PPL/accuracy
    hide answer flips (2407.09141, LLM-KICK; 2609.07664 shows JSD drift down to Q2_K GGUF).
  - **Open:** (A) falsification/checker tasks under compression ("does falsification break before solving?");
    (B) KV *quantization* (not eviction) on exact state-copy traces (BFS queue, DP table), separating weight error
    from KV error with a difficulty knob; (C) small-many vs. quantized-big-few at matched CPU time, with an LLM
    checker or counterexample as the selector. Also untested: quantization × the rewrite-gap memorization probe.
  - The sweep now also records wikitext **KL divergence vs. Q8_0** (llama-perplexity --kl-divergence, 20 chunks) and
    the **solve rate** on 40 easy unique-answer problems per config, so falsification, solving, simulation and PPL/KL
    can be compared on the same compression axis.
- Throughput fix (11:35): run_hack verified stress results *serially* after each generation chunk (100 generator
  runs × up to 4 solution runs per job), so the LLM sat idle most of the time and chunks took up to 1,600 s. Now
  parallelized (16 threads). The run resumed from 352/606, and the queue was rebuilt (queue_next7: PoC #2 →
  compression sweep → 1.7B).

## PoC #2c FINAL (12:50; 128 items × k=2, 100 generator calls each)
| generator strategy | hack@1 | 95% CI | invalid | rating ≤1300 (n=67) | rating >1300 (n=61) |
|---|---|---|---|---|---|
| no code (stress_blind) | 0.391 | [0.32, 0.46] | 0.21 | 0.52 | 0.25 |
| different wrong solution (placebo) | 0.441 | [0.37, 0.52] | 0.13 | 0.53 | 0.34 |
| target wrong solution (stress) | 0.453 | [0.38, 0.53] | 0.12 | 0.54 | 0.36 |
- Paired: stress − blind **+0.06 [−0.02, +0.14]** (the partial "significant" +0.14 at n=74 shrank: report the full
  n). **stress − placebo +0.01 [−0.07, +0.09]**; placebo − blind +0.06 [−0.04, +0.15].
- Conclusion holds and is now cleaner: **no evidence that Qwen3-8B (non-thinking) uses the specific bug.** Whatever
  code helps comes from seeing *a* solution: fewer invalid inputs (0.21 → 0.12), concentrated on harder problems
  (>1300: 0.25 → 0.34–0.36; easy problems are saturated by random testing at ~0.53).
- Lesson: interim results at n≈74 overstated the effect. Keep pre-planned n and report final CIs.
- Sweep check (14:35): config 1 (Q8_0) CoT generation runs at ~0.7–0.8 tok/s per slot (≈12 tok/s aggregate) on
  long traces. Only the Q8 server is busy, so this is real cost, not contention. Expect ~2 h per Q8 config and
  ~1.2 h per Q4 or lower, so the sweep ends around 02:00–03:00. Confound check: the KV-quant configs pass `-fa on`
  and the others use the default `auto`. llama.cpp resolves auto by probing FA support on the device (src/llama-context.cpp:557),
  and the CPU backend supports it, so all configs run with flash attention and the attention kernel is not a confound.
- Sweep rescoped (15:37): on Q8_0 the CoT n=24 chunk took **6,858 s for 32 generations** (a ~3,000-token trace with
  16 parallel slots on CPU). At that rate the 6-config sweep would take more than a day. Simulation sizes are cut to
  **n = 6, 12** for all configs. Q8_0 already had all n=6/12 cells (128 rows; 8 n=24 rows are kept but excluded from
  the comparison). The run was killed and restarted: Q8_0 resumes with hack + solve, then configs 2–6. Long-trace
  (n ≥ 24) KV-quantization effects need the GPUs.
- Sweep, 2 of 6 configs (17:35):
  | config | PPL | KLD vs Q8 | same top-1 | CoT acc (n=6,12) | CoT answer = Q8 | CoT tokens | hack@1 | solve |
  |---|---|---|---|---|---|---|---|---|
  | Q8_0 | 10.74 | — | — | 0.77 | 1.00 | 1287 | 0.28 | 0.45 |
  | Q4_K_M | 11.02 | 0.055 | 90.6% | 0.85 | 0.71 | 929 | 0.33 | (running) |
  - **Noise floor matters:** the *same* Q4_K_M config at temperature 0, run twice (the earlier PoC #5 run vs. this
    one), agrees on only **42/48 = 0.875** CoT answers. llama.cpp with 16 parallel slots is not deterministic
    (batch composition changes the float summation order). So Q4-vs-Q8 agreement 0.71 is below the noise floor
    0.875, but only modestly. Any "answer flip" metric must be reported against a same-config replicate, and the full
    study should use single-slot or batch-invariant decoding for the flip analysis.
  - No accuracy drop from Q8 → Q4_K_M at this n (0.77 vs. 0.85, 48 items, within noise). Q4 traces are *shorter*
    here, not longer (contrary to the "quantization inflates CoT" papers; tiny n).
- Sweep, Q3_K_M done (19:35): PPL 11.74 (+9% vs Q8), KLD 0.174, top-1 83%. **CoT simulation unchanged (0.88)**, but
  **solve 0.45 → 0.40 → 0.25** (Q8 → Q4 → Q3; 40 problems, k=1, so ±~0.15) and hack 0.28 / 0.33 / 0.23. Hint:
  open-ended problem solving degrades at 3-bit while short exact simulation does not; ranking task sensitivity is
  the angle. The n is too small to claim.
- Q2_K partial: collapse. PPL 17.2, KLD 0.81, top-1 65%; CoT 0.12, and even **code mode 0.25** (was 1.00). Raw
  responses checked: genuine broken programs (e.g. `input = sys.stdin.read; data = input.split()` without calling
  it; hard-coded `print(dist[5])`), not harness errors.
- Sweep, Q2_K done (22:00): solve **0.05**, hack 0.12, CoT 0.12, code 0.25. Retention vs. Q8: solve 11%, CoT 16%,
  code 25%, **hack 43%**. The random-generator strategy is the most compression-robust task, consistent with PoC #2's
  finding that much of its success is random testing. Weight-quant ordering of sensitivity so far:
  open-ended solving > text simulation ≈ code > generator-based falsification.
- KV q8_0 (with Q4_K_M weights), partial: PPL 11.09, KLD 0.055 (≈ the Q4_K_M/f16 0.055, so 8-bit KV adds ~nothing),
  CoT 0.83, code 1.00.
- KV q4_0 partial (00:35): PPL 10.95, KLD 0.081 (vs 0.055 for f16/q8 KV), CoT 0.77, agreement with Q8 0.69,
  code 0.96 (2 failures), hack 0.44 on the first 16 items. The 2 code failures are the same signature as Q2_K:
  `input = sys.stdin.read; data = input.split()` (the bound method is never called → AttributeError). It's a
  recognizable "degraded model" idiom worth tracking as a qualitative compression symptom.

## PoC #7 FINAL: compression sweep (Qwen3-8B, llama.cpp CPU; done 01:30, 2026-10-06)
| config | PPL | KLD vs Q8 | top-1 same | CoT sim (n=6,12; 48) | code | hack@1 (40×2) | solve (40×1) |
|---|---|---|---|---|---|---|---|
| Q8_0 / KV f16 | 10.74 | — | — | 0.77 | 1.00 | 0.28 | 0.45 |
| Q4_K_M / f16 | 11.02 | 0.055 | 90.6% | 0.85 | 1.00 | 0.33 | 0.40 |
| Q3_K_M / f16 | 11.74 | 0.174 | 83.4% | 0.88 | 1.00 | 0.23 | 0.25 |
| Q2_K / f16 | 17.18 | 0.805 | 64.6% | 0.12 | 0.25 | 0.12 | 0.05 |
| Q4_K_M / KV q8_0 | 11.09 | 0.055 | 90.3% | 0.83 | 1.00 | 0.38 | 0.38 |
| Q4_K_M / KV q4_0 | 10.95 | 0.081 | 88.3% | 0.77 | 0.96 | 0.44 | 0.42 |

Paired differences vs. Q8_0 (bootstrap 95% CI over items):
- Q3_K_M: **solve −0.20 [−0.40, 0.00]**, hack −0.05 [−0.19, +0.09], CoT +0.10 [−0.02, +0.23].
- Q2_K: solve −0.40 [−0.57, −0.23], hack −0.15 [−0.28, −0.03], CoT −0.65 [−0.77, −0.50]. All significant.
- Q4_K_M and both KV-quant configs: no significant drop on any task. hack is *higher* than Q8 for KV q4 (+0.16
  [+0.04, +0.28]), but Q8's hack run (0.28) looks unluckily low vs. the earlier Q4 run of the same 40 items (0.41).
  Sampling noise at k=2 is ±0.1. Treat hack differences < 0.15 as noise.

**Takeaways for a project:**
1. **Task sensitivity is ordered:** open-ended solving breaks first (borderline at 3-bit), then text simulation and
   code (only at 2-bit). Generator-based falsification is the most robust (keeps 43% at 2-bit) because random testing
   needs little reasoning. PPL rises only +9% at 3-bit while solve drops ~45% relative; it's "PPL-blind"-ish but
   needs a larger n.
2. **KV q8_0 is free and KV q4_0 is ~free at short traces** (KLD 0.081 vs 0.055; no task drop at n ≤ 12). The
   hypothesis that KV quantization hurts *long* state-copying traces is still untested: it needs n ≥ 24 traces,
   which take ~2 h/chunk on CPU, so the GPUs are needed.
3. **Methodological:** llama.cpp with parallel slots is non-deterministic at temperature 0 (same-config replicate
   agreement 0.875), so answer-flip analyses need a replicate noise floor or single-slot decoding. Per-cell n
   (40–48) only resolves effects ≥ ~0.2.
4. A qualitative degradation signature, `input = sys.stdin.read; data = input.split()`, appears under both Q2_K
   and KV q4_0.
- Qwen3-1.7B on PoC #2, partial (02:35, 36 items): hack@1 ≈ 0 for every strategy (stress 0.04). Generator
  strategies are 90–99% *invalid*. Raw responses show 1.7B ignores "print one random input, read nothing" and instead
  writes a *solution* that calls `input()` (RE on empty stdin). The generator/falsification task needs a minimum model
  scale or instruction following. Scale curve so far: 1.7B ≈ 0 → 8B 0.45 (stress).
- Queued: larger-n solve follow-up for the borderline Q3 cell (95 problems × k=2 for Q8 / Q4 / Q3), after the 1.7B runs.
- Qwen3-1.7B PoC #2 FINAL (03:00, 40 items): blind 0.00, direct 0.00, bugfirst 0.01, stress_blind 0.01, stress 0.06
  [0.01, 0.14]. Generator invalid rate 0.88–0.96 (it writes stdin-reading solutions instead of generators).
- Qwen3-1.7B PoC #5, partial (03:35): code 1.00 for BFS/LIS at every n, but knapsack code 0.33 / 0.42 / 0.08 / 0.00
  (checked: it misreads the "n capacity" first line and hard-codes the capacity). Direct answers are a constant guess
  ("The answer is: 3" for every BFS n=6 instance → 0.00 vs. the majority baseline 0.50). CoT n=6: BFS 0.58, LIS 0.62,
  knapsack 0.17 (8B: 0.92 / 0.83 / 0.08). Parsing checked; these are genuine.
- Qwen3-1.7B PoC #5 FINAL (05:00). CoT by n=6/12/24/48: BFS .58/.58/.50/.00, LIS .67/.58/.17/.00, knapsack
  .17/0/0/0 (8B: BFS .92/.75/.42/.08, LIS .83/.75/.42/0). Code: BFS/LIS 1.00 everywhere; knapsack .33/.42/.08/0.
  Direct answers sit at or below the majority baseline. Unlike 8B, 1.7B's BFS CoT is *flatter* over n=6–24
  (0.58 → 0.50) but lower at small n. Scale mostly lifts the small-n ceiling; the long-n collapse (plus truncation)
  hits both sizes.
- Solve follow-up, 95 problems × k=2 (07:35): Q8_0 0.484. **Q4_K_M 0.479, paired −0.005 [−0.07, +0.05]**: no loss,
  with a tight CI. **Q3_K_M (partial, 48 problems): 0.28 vs. Q8 0.45 on the same problems, −0.17 [−0.26, −0.08]**,
  already significant. This confirms the 40-problem hint: open-ended solving drops at 3-bit (PPL +9%, KLD 0.17) while
  short text simulation and code do not.

## Solve follow-up FINAL (08:15; 95 unique-answer easy CF problems × k=2, paired vs. Q8_0)
| weights | solve pass@1 | Δ vs Q8 [95% CI] | runtime errors |
|---|---|---|---|
| Q8_0 | 0.484 | — | 3 |
| Q4_K_M | 0.479 | −0.005 [−0.07, +0.05] | 3 |
| Q3_K_M | 0.353 | **−0.13 [−0.20, −0.06]** (−27% relative) | 11 |
**Confirmed: open-ended solving loses ~27% at 3-bit**, while PPL rises 9% (KLD 0.17, top-1 agreement 83%) and short
CoT simulation and code show no drop. Runtime errors almost quadruple (3 → 11), in line with the "broken code idiom"
signature seen at Q2_K / KV q4.
- Queued (08:40): **PoC #1 rewriter≠solver control.** Llama-3.1-8B-Instruct (Q4_K_M) writes the story rewrites
  (fixed letter-preserving prompt); Qwen3-8B Q4_K_M solves orig + story, k=2, unique-answer problems. Newer (eval,
  ≤1200) vs. older (train shards). This tests whether the DiD (+0.15) survives once the self-paraphrase confound is
  removed.
- **Rewriter control, newer problems (10:35):** with Llama-3.1-8B as rewriter (Qwen3-8B solving), story − orig =
  **−0.133 [−0.24, −0.03]** (n=45 io-valid of 53; orig 0.24 → story 0.11). With Qwen rewriting its own statements it
  was **+0.08**. So the earlier "rewrites don't hurt newer problems" was at least partly a **self-paraphrase effect**:
  a statement rewritten by the solver itself is easier for it. Llama and Qwen rewrites are similar in length (median
  0.83× vs. 0.80× the original), so it isn't truncation, though Llama rewrites may drift semantically in ways the
  example-input check can't catch. The DiD interpretation now depends on the older-problem arm (running). If older
  problems drop by much more than −0.13 with Llama rewrites, the memorization reading survives; if not, it doesn't.

## PoC #1 rewriter≠solver control FINAL (13:30): **the memorization DiD does NOT survive**
Llama-3.1-8B rewrites (story, fixed prompt), Qwen3-8B Q4_K_M solves, k=2, unique-answer problems, io-broken rewrites
excluded:
| set | n | orig | story (Llama) | story − orig |
|---|---|---|---|---|
| newer (eval, contest ids 1548–1623) | 45 | 0.244 | 0.111 | −0.133 [−0.24, −0.03] |
| older (train shards, ids 5–1547) | 88 | 0.466 | 0.386 | −0.080 [−0.15, −0.01] |
**DiD (newer − older) = −0.05 [−0.19, +0.07]**, vs. **+0.15 [+0.06, +0.26]** when Qwen rewrote its own statements.
- With an independent rewriter, rewording hurts old and new problems *equally*. The earlier memorization signature
  came from the **self-paraphrase confound**: Qwen solves its *own* rewrites of newer problems better (+0.08) than
  Llama's (−0.13).
- Still unexplained: older problems are solved far more often at the same rating (0.47 vs. 0.24 originals,
  replicated). That fits memorization *or* era/difficulty drift, and rewording doesn't separate the two.
- **Lesson for the project (and a critique of StoryCoder/MIMIC-style results): rewriter≠solver is mandatory.**
  A 2×2 rewriter × solver design measures the self-paraphrase effect directly. That's queued next.

## PoC #1 rewriter × solver 2×2 (16:35): **correction to the previous section**
Newer problems valid under both rewriters (n=31; small):
| solver \ statement | original | Qwen rewrite | Llama rewrite |
|---|---|---|---|
| Qwen3-8B | 0.234 | 0.274 | 0.129 |
| Llama-3.1-8B | 0.129 | 0.097 | **0.016** |
- **Both solvers do worse on Llama's rewrites**, Llama included: its own rewrites take it from 0.13 to 0.02.
  Qwen's rewrites barely hurt either solver. The self-paraphrase interaction is +0.07 [−0.07, +0.19], not
  significant.
- So the previous section's attribution is **wrong in mechanism**. The collapse of the DiD with Llama rewrites is
  better explained by **rewriter quality**: Llama-3.1-8B's rewrites degrade solvability for everyone (semantic drift the
  example-input check can't detect), and that uniform noise (−0.08 old, −0.13 new) swamps any old/new difference.
- Status of the memorization question: **unresolved, reopened.** The Qwen-rewrite DiD (+0.15) is neither confirmed
  nor refuted. Its confounds are rewriter = solver (self-paraphrase not supported here, but n=31) and era/difficulty.
  The right control is a *stronger*, independent rewriter (e.g. Qwen2.5-72B / Llama-3.3-70B on GPU) plus a
  rewrite-faithfulness check (e.g. a reference solution must still pass when re-derived from the rewrite, or a
  judge model).
- Methodological lesson: rewrite-based probes need a **rewrite-quality control** (a neutral solver's accuracy on the
  rewrite), not just rewriter≠solver.
- Ops (16:40): the shared root/SSD disk hit **0 bytes free**. My artifacts were stable (~29 GB in
  /root/llm_algo_poc_tools), so another process is filling the shared device. Freed 12 GB by deleting the finished
  sweep's Qwen3-8B Q8_0 and Q2_K GGUFs (each regenerable in ~5 min from /SSD/huggingface). Free space was 8.8 GB
  right after, so something is still writing. No new local model conversions until that's resolved (an independent
  gpt-oss-20b rewriter was considered, but it needs ~13 GB and the converter here may not support it).
- Ops (2026-10-07 04:35): shared disk fell to 2.5 GB free again (external writer). Deleted the finished sweep's Qwen3-8B Q3_K_M GGUF (4.1 GB, regenerable).

## GPU phase (2026-10-07 11:00)
GPUs are back after a container restart: 4× A100-80GB, **shared** with other containers. Each GPU already has a
foreign process using 28–62 GB, three of them at 100% util. Policy: use mainly GPU 2 (~53 GB free, ~31% util) and cap
vLLM memory. vLLM 0.10.2 (torch 2.8, cu128, on driver 535 / CUDA 12.2 via minor-version compatibility) is installed
with `pip --target` on the NAS because local disk is full. The restart killed the CPU checker-v2 run (rerunning on GPU).
GPU plan, in order:
1. PoC #2 **thinking-mode placebo test**: Qwen3-8B bf16 with thinking on and off; stress / placebo / blind, 128 items.
2. PoC #6b checker v2 (prompt + selection + repair), thinking off and on.
3. Scale: Qwen3-32B-AWQ on #2 and #6.
4. PoC #1 with a strong independent rewriter (Gemma-3-27B-AWQ or Llama-3.3-70B-w4a16).
5. PoC #7 long traces (n = 24/48) with fp8 KV cache vs. bf16 in vLLM.

## GPU results
### PoC #2 on vLLM, Qwen3-8B bf16, thinking OFF (14:40; 128 items × k=2, 100 generator calls each)
| strategy | hack@1 | 95% CI | invalid |
|---|---|---|---|
| no code (blind) | 0.461 | [0.40, 0.53] | 0.125 |
| placebo code | 0.406 | [0.33, 0.48] | 0.122 |
| target code | 0.387 | [0.32, 0.46] | 0.141 |
Paired: target − blind **−0.07 [−0.16, +0.01]**; target − placebo −0.02 [−0.10, +0.06].
- The sign is **flipped** vs. the CPU Q4_K_M run (+0.06 [−0.02, +0.14]). Across two independent runs, the effect of
  showing code is **≈ 0 ± 0.1**. Conclusion strengthened: the non-thinking 8B does not use the bug, and isn't
  helped by code at all at bf16.
- The CPU run's "code reduces invalid inputs" (0.21 → 0.12) **does not replicate** at bf16 (0.125 vs. 0.14). That
  hints the Q4 model was worse at following the input format when it got no code (a quantization effect on
  instruction following). Unconfirmed.
- Thinking-ON run is in progress. Partial (21 items): target 0.41, placebo 0.21, blind 0.45; target − placebo
  +0.19 [0.00, +0.36]. Too early; ~15% of thinking traces hit the 14k-token cap.
### PoC #6b checker v2, Qwen3-8B bf16, thinking OFF (15:40)
Prompt v2 ("validate, don't re-solve"; token-stream parsing), K=4 checkers per problem, selected on held-out-split
labelled solutions, plus one repair round. Errors on the TEST half (264 labelled solutions, 43 problems):
| grader | errors | false rejects | misses |
|---|---|---|---|
| exact match | **43** | 27 | 16 |
| avg of 4 v2 checkers | 73 | 64 | 9 |
| selected checker | 63 | 43 | 20 |
| selected + repair | 60 | 40 | 20 |
- Selection helps (73 → 63) and repair helps a little (34 tried, 6 kept, 63 → 60), but **8B non-thinking checkers are
  still worse than exact match**. 12/43 problems get a checker with 0 test errors.
- Next: (a) grading *policies* that combine exact match with a checker (OR rule; per-problem choice on the selection
  set; running now, no new generations); (b) thinking-mode checkers (queued in the same lane).
### PoC #6c grading policies from imperfect 8B checkers (16:40; same held-out test half, 264 solutions)
| policy | errors | false rejects | misses |
|---|---|---|---|
| exact match | 43 | 27 | 16 |
| best checker alone | 63 | 43 | 20 |
| **per problem: exact or best checker, chosen on the selection half** | **38** | 20 | 18 |
| OR rule (accept if exact OR checker) | 44 | **12** | 32 |
| **per problem: exact or OR-rule** | **37** | 18 | 19 |
- **First "solution" that beats exact match with an 8B model, without thinking:** use labelled accepted/rejected
  solutions to decide *per problem* whether to trust the LLM checker: **−14% errors** (43 → 37). The OR rule more than
  halves false rejections of correct answers (27 → 12) but lets in more wrong ones (16 → 32), a tunable trade-off.
- Small n (264 solutions / 43 problems). The thinking-mode checkers (running) may shift this a lot.
- Ops (17:30–18:15): a foreign job grew on GPU 2 (68 GB used in total, 14 GB free), so I stopped our vLLM and moved to
  GPU 3 (lanes resume from cache). The restart then **hung for 30 min in CIFS I/O** (process in D state,
  `wait_for_response`; NAS small-file reads at ~5 kB/s): importing vLLM from the NAS is fragile. Fix: reinstall vLLM
  into RAM-backed /dev/shm (179 GB free), with HF/vLLM caches there too. The root disk hit 0 bytes again from the
  external writer; I deleted my Llama-3.1-8B and Qwen3-1.7B GGUFs (7 GB, regenerable) and kept Qwen3-8B Q4 as the CPU
  fallback.
- Ops fix (18:40): the real cause of the slow/hung vLLM imports was **cwd on the NAS**. `python -c` / `-m` puts cwd
  first on sys.path, so every one of thousands of imports probed CIFS before finding the module. The import took
  7.4 min from the NAS cwd vs. **12.7 s** with cwd=/dev/shm. serve_gpu.sh now `cd /dev/shm` first. vLLM is healthy
  again (picked GPU 2, which had freed up), and the lanes resumed from cache.
### PoC #6b checker v2, Qwen3-8B, thinking ON (19:10)
Only 36/43 problems have ≥1 usable checker: with thinking, many responses hit the 14k cap or end without a final
code block. On those 36 problems' TEST half (223 solutions): exact match 32 errors; avg checker 61; selected 49;
selected + repair 44 (24 repairs, 5 kept); 13/36 problems with a zero-error checker. **Thinking does not make 8B
checkers beat exact match.** Policies (per-problem choice / OR rule) are running.
### PoC #6c policies with THINKING checkers (19:40; 264 test solutions)
exact 43 · best checker 60 · per-problem 39 · OR rule 41 (false rejects 13) · per-problem OR **38**. Same picture as
non-thinking (37): selective use of LLM checkers beats exact match by ~12–14%; thinking adds nothing.

### PoC #2 THINKING ON, Qwen3-8B bf16 (19:40; 128 items × k=2, 100 generator calls, 14k-token cap) **key result**
| strategy | hack@1 | 95% CI | truncated | hack given finished | first-call hit among hacks |
|---|---|---|---|---|---|
| no code (blind) | 0.477 | [0.40, 0.55] | 14% | 0.54 | 0.49 |
| **placebo** (different wrong solution) | **0.193** | [0.14, 0.25] | 17% | 0.23 | 0.94 |
| target wrong solution | 0.359 | [0.29, 0.43] | 26% | 0.48 | 0.92 |
Paired: target − placebo **+0.17 [+0.10, +0.24]**; placebo − blind **−0.28 [−0.37, −0.20]**; target − blind −0.12 [−0.21, −0.02].
- **With thinking, the model *does* read the code.** Target ≫ placebo, and successful generators hit on the *first*
  call 92–94% of the time (blind: 49%). Thinking turns the generator from broad random testing into a **narrow,
  hypothesis-targeted** test.
- **That targeting is a double-edged sword.** With the right code it's about as good as blind random testing
  (0.48 vs 0.54 on finished responses). It does not beat it, because narrow generators lose coverage. With *wrong*
  code (placebo) it is **misdirected**: hack rate drops to less than half of blind (0.19 vs 0.48). Without
  thinking, none of this happened (all ≈ 0.4).
- Thinking with code also runs longer: 26% of responses hit the 14k cap vs. 14% blind.
- This is a clean, novel finding for the project: "reasoning models anchor on the code they're shown; code-guided
  falsification helps only when the code is exactly the target, and misleads otherwise." Next: does scale (32B)
  turn the targeting into a net gain over blind?
### PoC #2 scale: Qwen3-32B-AWQ, thinking OFF (20:10; 128 × k=2)
| strategy | hack@1 | 95% CI | invalid |
|---|---|---|---|
| no code (blind) | **0.781** | [0.72, 0.84] | 0.07 |
| placebo code | 0.657 | [0.59, 0.72] | 0.04 |
| target code | 0.672 | [0.61, 0.74] | 0.04 |
Paired: target − blind **−0.11 [−0.18, −0.04]**; target − placebo +0.02 [−0.05, +0.08].
- Scale lifts generator falsification sharply: blind **0.46 (8B) → 0.78 (32B)**, with invalid inputs at 0.07.
- At 32B without thinking, showing code **hurts** (−0.11, significant), and it hurts equally whether it's the target
  or a placebo. The code distracts (generators bend toward the shown program) without bug-specific benefit.
  Consistent with 8B: non-thinking models don't use the specific bug. 32B thinking run started.
- Ops (20:30–20:45): a foreign job joined GPU 0 (16 GB left free), so we moved to GPU 3. A foreign job there then grew
  to 67 GB *between our pick and vLLM's start*, and vLLM refused to start ("free 12.4 GiB < 35.6 GiB"; no harm to
  others). Added `poc/start_vllm.sh` (re-pick and retry up to 6×). The 32B server now runs on GPU 0 alongside a 17 GB
  foreign job (~20 GB free). The 32B thinking run restarts from scratch (no rows were saved before the move).
### PoC #6c policies, Qwen3-32B-AWQ checkers, thinking OFF (23:35; 264 test solutions)
exact 43 · best checker alone 59 (8B: 63) · **per-problem 36** (8B: 38) · OR rule 43 (false rejects 14) ·
per-problem OR 37. **Scale barely helps the checkers themselves** (a 32B checker alone is still worse than exact
match). The *policy* of choosing per problem with labelled solutions is what reliably beats exact match (−16% here).
### PoC #2 scale: Qwen3-32B-AWQ, THINKING ON (02:10; 64 items × k=2, 12k-token cap)
| strategy | hack@1 | 95% CI | truncated | hack given finished |
|---|---|---|---|---|
| no code (blind) | 0.344 | [0.23, 0.45] | 38% | 0.55 |
| placebo | 0.164 | [0.09, 0.25] | 33% | 0.23 |
| target | 0.414 | [0.31, 0.52] | 37% | **0.65** |
Paired: target − placebo **+0.25 [+0.14, +0.36]**; placebo − blind −0.18 [−0.31, −0.04]; target − blind +0.07 [−0.06, +0.20].
- Same anchoring signature as 8B-thinking: the target code is used (target ≫ placebo; 100% of target hacks hit on
  the first generator call), and a wrong program misleads.
- **Scale hint:** among finished responses, target now *beats* blind at 32B (0.65 vs 0.55; at 8B it was 0.48 vs 0.54).
  Bigger reasoning models may turn code-targeting into a net gain. Not significant on n=64 with heavy truncation.
- **Caveat that dominates:** 33–38% of 32B thinking traces hit the 12k cap, so *raw* thinking hack rates are far
  below non-thinking 32B (blind 0.78). For falsification, cheap non-thinking random generators at 32B are the
  strongest single strategy measured. A fair thinking test needs a larger budget (≥24k) and token-matched
  comparisons.
### PoC #6 at 32B, complete (finished ~02:40, logged 07:15)
| checkers | exact | best checker | +repair | **per-problem policy** | OR rule | zero-error problems |
|---|---|---|---|---|---|---|
| 8B no-think | 43 | 63 | 60 | 38 | 44 | 12/43 |
| 8B think | 43 | 60 | (44/223 on 36 probs) | 39 | 41 | 13/36 |
| 32B no-think | 43 | 59 | 53 | 36 | 43 | 15/43 |
| 32B think | 43 | 58 | 48 (on 42 probs) | **35** | 40 | 16/42 |
(errors on the 264 held-out labelled solutions; lower is better)
- Scale and thinking each help the checkers a little (best+repair 60 → 48; zero-error problems 12 → 16), but **no
  single LLM checker beats exact match**. The **per-problem policy beats exact match in every configuration**
  (−12% to −19%, best 35 vs 43). Thinking also produced more repairable checkers (10 of 32 repairs kept).
- Ops bug: the queue scripts started vLLM with `&` and ended with a bare `wait`, which also waits for the server, so
  the queue never exited. **The 32B server sat idle on GPU 3 holding 58 GB for ~4.5 h** (until 07:15). Fix: `wait`
  on the lane PIDs only, then kill the server. The session restart also dropped the session-only hourly cron and the
  GPU monitor.

## Non-coding topics (GPU, 2026-10-08)
### PoC F: progressive hints, tutor Qwen3-8B → student Qwen3-1.7B (80 easy unique-answer CF problems, k=4)
| condition | pass@1 (all) | pass@1 on problems the student fails alone (n=57) | student-code similarity to reference |
|---|---|---|---|
| no hint (L0) | 0.234 | 0.035 | 0.13 |
| hint 1 (key observation) | 0.228 | 0.110 | 0.14 |
| hints 1–2 (+ approach) | 0.209 | 0.096 | 0.13 |
| hints 1–3 (+ plan in words) | **0.375** | **0.259** | 0.15 |
| placebo (another problem's 3 hints) | 0.163 | 0.075 | 0.11 |
| full reference solution | 0.441 | 0.311 | 0.36 |
- **Hints work without leaking code.** Three levels recover ~80% of the full-solution gain on hard problems
  (0.035 → 0.26 vs 0.31). Student code stays dissimilar to the reference (0.15 vs 0.36 when given the solution), and
  0% of hints contain code.
- **Levels 1–2 barely help a 1.7B student.** The jump happens at the step-by-step plan, which suggests weak students
  need procedural, not conceptual, hints.
- **Placebo hints hurt** (0.234 → 0.163 overall). The student follows irrelevant hints: the same anchoring effect as
  PoC #2.
- Next: an LLM-judge/n-gram "how much is revealed" score per level, a stronger student (8B) for the level-1/2 effect,
  and tutor thinking on/off.
### PoC A: interactive games (partial, thinking OFF)
Number guessing is near-optimal binary search: N=16 mean 3.7 guesses (optimal worst case 5), N=100 6.0 (7),
N=1000 10.9 (10). Guesses are 89–98% consistent with past feedback and sit at the interval midpoint (median deviation
≤ 3%). Bug: at N=10^6 the 60-turn dialogues overflowed the 32k context and crashed the run. Fixed by compacting old
turns to their GUESS lines (all feedback kept) and treating an overflow as a failed game. Rerunning, then Mastermind
and thinking ON.

## Novelty scan, non-coding topics (08:30; agent opened every cited page; verify against the PDFs before citing)
- **F hints: medium–high (best).** Covered: tutor/student LLM pairs (GPT4Hints-GPT3.5Val 2310.03780), multi-level
  hints in intro programming (2404.02213), human hints on USACO (2404.10952), ELABORATION (2505.16667),
  LLM-to-LLM math tutoring (2506.04920). **Open, and exactly our pilot design:** placebo-hint controls, a
  dose-response curve over hint levels vs. the full solution on competitive programming, and leakage via code
  similarity ("leakage-adjusted gain"). Next: Qwen3-32B tutor, 1.7B/8B students, leakage-adjusted gain.
- **A interactive strategy: medium.** Covered: AQA-Bench (interactive binary search/DFS/BFS, 2402.09404),
  MastermindEval (2503.05891), reasoning models on 20Q (2601.17716), Battleship EIG (2510.20886). **Open:** splitting
  the excess-guess gap into *inconsistent* guesses vs. *consistent but uninformative* ones, scaled over N = 16…10^6 and
  model size × thinking. Plus an externalized "feasible interval" scratchpad intervention (state tracking vs. strategy).
- **B graph encodings: low.** GrAlgoBench (2602.06319) already crosses formats × Qwen3 thinking on/off, and finds
  performance largely format-independent; Talk-like-a-Graph (2310.04560) and NLGraph cover the rest. **Deprioritized:**
  the thinking-mode graph run was cancelled; the running non-thinking run finishes as a cheap sanity check.
- **D NL→solver: medium.** Logic-LM / LINC / SatLM / OptiBench / "when do solvers help" (2512.03272) cover it.
  Open: a crossover map for *thinking* models (direct vs. formalize+solve) over model size × search-space size,
  plus per-error-class repair.

## Refocus on Computational Geometry / Combinatorial Optimization (user request, 2026-10-08)
Novelty scan (agent; pages opened): **CG metamorphic invariance = clearest gap (medium–high).** GeoRepEval
(2604.16421) varies the *representation* (Euclidean/coordinate/vector), not rigid/similarity transforms. "Can LLMs
integrate spatial data" (2508.05009) asks CG primitives directly with no code-vs-direct comparison. SGP-Bench checks
SE(2) consistency for graphics programs, not CG computations. **CO three-way comparison: medium.** "Formalize, Don't
Optimize" (2605.12421) compares code paradigms with frontier models only. NLCO (2602.02188) and GraphArena show
direct-answer collapse. Open: the text-answer arm, thinking on/off at matched tokens, and small open models.
**Geometry counterexamples: medium** (REFUTE/CodeHacker are general). Too few local geometry problems (16), so this is
folded into G2 as a "degen" variant. **Text-vs-image: low** (IsoBench/VisOnlyQA/BlindTest), skipped.

### PoC G2 (running): CG metamorphic invariance
5 exact integer-geometry tasks (hull vertex count, twice the polygon area, strict point-in-polygon, number of
intersecting segment pairs, closest-pair squared distance) × 2 sizes × 10 instances × 8 variants (identity,
translate, rot90, mirror, permute, scale ×3, big offset ~1e9, degen = collinear/duplicate points, a ray through a
vertex, touching segments). Generators self-tested: answers invariant under all transforms (0 bugs), scale ×9 for
area/distance, point-in-polygon labels balanced. Modes: direct (thinking off/on) vs. code (the model writes a program
for the stdin format; we run it). Metrics: accuracy per variant, cross-transform **consistency**, consistent & correct.
### Deep related-work check for G2 and CO1 (full text; agent; re-check exact figures in the papers before citing)
- **G2 stays open.** Nobody combines exact-integer CG tasks, same-instance metamorphic transforms, direct-vs-executed-code,
  and thinking off/on. Closest: **Spatter** (2410.12496; integer affine metamorphic relations for spatial DBMSs, no LLM:
  cite it as the SE ancestor); **SGP-Bench** (SE(2) consistency on SVG semantics, direct MCQ only); **GeoRepEval**
  (re-encoding, not transforms; "convert-then-solve" helps); **NoReGeo** (integer CG primitives, no transforms);
  **Reasoning, Code, or Both?** (2605.26414; direct vs code under GSM-Symbolic perturbation, not geometry). Nobody
  uses classic CG degeneracies or 1e9 offsets as LLM test conditions. Tweaks adopted: cross-variant execution of
  one program per instance with a failure taxonomy (logic / degen-only / big-only / transform-only / crash →
  `poc/run_geo_cross.py`); scale reported as equivariance (×9). Planned: a canonicalize-then-solve arm, a
  shapely/float reference-library arm, and a second model family (Llama-3.1-8B).
- **CO1: EHOP (2502.13776) is the main overlap.** It has direct vs LLM-written gurobipy ILP vs fixed greedy on
  knapsack/TSP/coloring (tiny sizes), with Qwen3-32B thinking off/on and an exact-optimum metric (no gap). Also
  NLCO (direct; Qwen3-14B off/on; token profiles), Formalize-Don't-Optimize (code paradigms, frontier only),
  SDDL (2608.18409, scheduling: direct vs OR-Tools vs DSL), HeuriGym (heuristic arm only). **Open for CO1:** an
  LLM-written *heuristic* arm alongside direct and solver on the same instances; a 1.7B/8B/32B × thinking sweep;
  optimality gap + feasibility; matched token budgets (+ best-of-k direct); the crossover size where code beats direct
  per model size; greedy and CP-SAT baselines ("does an LLM heuristic beat textbook greedy?").
### PoC A games v1 → v2 (08:50)
v1, thinking OFF (valid parts): number guessing near-optimal to N=1000 (3.9/6.4/9.5 guesses vs 5/7/10 optimal worst
case, 93–95% consistent), but at N=10^6 only 11/15 solved and **guess consistency dropped to 0.64**: the model loses
track of the feasible interval in long dialogues (old turns compacted to GUESS lines plus feedback). **v1 Mastermind
(0/30, 10% consistent, 36% "bad format") is INVALID.** The non-thinking model writes strategy essays containing
*example* guesses ("GUESS: ABBA") and gets truncated; the parser took illustrative guesses as real ones. v2: the rules
demand a single guess line and the parser reads only the last line. Rerunning thinking off + on. v1 archived.

### PoC G2 CG metamorphic invariance, Qwen3-8B, thinking OFF (09:05; 5 tasks × 2 sizes × 10 instances × 8 variants)
| arm | non-degenerate accuracy | identity | degenerate | consistent across 7 transforms | consistent & correct |
|---|---|---|---|---|---|
| direct answer | 0.22 | 0.20 | 0.34 | **0.00** (every task) | 0.00 |
| code (one program per prompt, executed) | **0.97** | 0.98 | 0.96 | 0.90 hull / 0.90 area / **0.50 pip** / 1.00 segs / 1.00 close | same |
- **Direct answers are not invariant at all.** Not a single instance gets the same answer across the 7 equivalent
  inputs. 21% of non-thinking direct replies run out of tokens doing arithmetic.
- **Code is invariant except where CG is numerically fragile.** Point-in-polygon breaks on the **1e9-offset** variant
  (7/20 wrong, floating-point ray casting) and under rotation (3/20). Hull fails on degenerate/huge inputs (4 cases).
  Segments and closest pair are perfect. This supports the "code is invariant except at degeneracies/precision"
  hypothesis. The cross-variant run (one program, run on all variants) will attribute failures per program.
- Thinking-ON direct/code arms are running.

### PoC F with a 32B tutor (09:05; same 80 problems, student 1.7B, k=4)
| condition | 8B tutor: all / hard | **32B tutor: all / hard** | 32B: leakage-adjusted pass@1 (solve AND sim<0.5) |
|---|---|---|---|
| L0 | 0.23 / 0.04 | 0.22 / 0.05 | 0.22 |
| L1 | 0.23 / 0.11 | **0.29 / 0.16** | 0.29 |
| L2 | 0.21 / 0.10 | **0.29 / 0.18** | 0.29 |
| L3 | 0.38 / 0.26 | 0.32 / 0.24 | 0.32 |
| placebo | 0.16 / 0.08 | 0.15 / 0.08 | 0.15 |
| full solution | 0.44 / 0.31 | 0.40 / 0.29 | **0.24** |
- A stronger tutor makes **conceptual hints (L1–L2) useful** (hard problems 0.04 → 0.16–0.18). The 8B tutor's L1–L2
  did little.
- **Leakage-adjusted:** handing over the full solution yields 0.40, but only 0.24 if near-copies (similarity ≥ 0.5) are
  discounted. **Hints give more "own" solves (0.29–0.32) than the full solution.**
- Placebo hints hurt with both tutors (0.22 → 0.15).

### PoC A games v2 (guess-only replies), thinking OFF
Guess-only replies make number guessing *less* consistent at larger N: consistency 0.98 / 0.90 / 0.73 / 0.71 for
N = 16 / 100 / 1e3 / 1e6 (v1 with free-text reasoning: 0.93/0.95/0.94/0.64). Solved 15/15/14/12 of 15. Mastermind is
still 0/30, 10% consistent, with 28% unparseable replies even in v2. The non-thinking model cannot play Mastermind;
the thinking run will show whether reasoning fixes it. (Next: store raw replies for the unparseable turns.)
### PoC G2b cross-variant execution (10:10; one program per instance, written from the IDENTITY prompt, run on all 8 variants)
| model | correct on all 8 | logic error | transform-only | degenerate-only | crash/no code |
|---|---|---|---|---|---|
| Qwen3-8B thinking OFF | **96/100** | 2 (pip) | 2 (pip) | 0 | 0 |
| Qwen3-8B thinking ON | 87/100 | 0 | 0 | **6** (pip 5, segs 1) | 7 (mostly no final code: long traces) |
- **Code written from a normal instance is invariant and precision-safe.** Programs written from the identity prompt
  pass the 1e9-offset variant (only the 2 logic-error programs fail there). But in G2, where a *new* program was
  written from each variant's prompt, point-in-polygon failed on the 1e9 variant **8/20** and hull **2/20**.
  **Seeing huge coordinates in the prompt makes the model write worse code** (input-conditioned code quality).
  Likely mechanism: floats/normalization or special-casing. Unverified: the raw programs weren't stored and a probe
  timed out on the busy server.
- **Thinking makes geometry code more brittle on degeneracies.** 5/20 thinking point-in-polygon programs fail only on
  the ray-through-vertex case (non-thinking: 0/20). Plus 7 traces end without a program.

### PoC CO1 (launched 11:05): three LLM paradigms on the same CO instances
knapsack (n = 10/20/40/80), TSP (8/12/20/40), graph colouring (10/20/40), P||Cmax scheduling (10/20/40), 6
instances each. References: exact for 72/84 (DP / Held–Karp / CP-SAT optimal); TSP n=20/40 = OR-Tools GLS 10 s
best-known (flagged). Textbook greedy gaps: knapsack 0.1–1.3%, scheduling 0.6–3%, colouring 0–12.5%, TSP 8–29%.
Arms: direct solution text vs. LLM-written OR-Tools model vs. LLM-written heuristic (solver libraries banned and
detected), executed in the sandbox (OR-Tools installed in the venv). Metrics: feasibility, gap, ≤1% rate, beats greedy.
Qwen3-8B thinking off → on, on its own server on GPU 0 (:8004).
### PoC CO1, Qwen3-8B thinking OFF (12:00; 6 instances per cell)
- **Direct answers degrade fast with size.** Knapsack gap 6% (n=10) → 48% (n=80); TSP 9% (n=8) → 139% (n=20),
  infeasible at n=40; colouring infeasible for n ≥ 20; scheduling 11–26%.
- **The solver arm works only where the OR-Tools model is trivial.** Knapsack: 0% gap and feasible 0.67–1.0. Every
  colouring/scheduling/TSP solver program crashed. Verified *genuine* (the sandbox runs OR-Tools fine): **CP-SAT API
  misuse**, e.g. `model.Minimize(max(colors))` over IntVars ("BoundedLinearExpression as a Boolean") and
  `model.Add(machine_loads[...] += p)` (SyntaxError). The bottleneck for small models is solver-API competence, not
  formulation. A self-repair arm with the traceback fed back is the natural next step.
- **The LLM heuristic arm** is mostly feasible but rarely beats textbook greedy beyond tiny sizes (knapsack 40:
  gap 16%; colouring 40: 467%, i.e. nearly one colour per node; scheduling 40: 133%). It times out on TSP 40.
- So far, the paradigm ranking flips by problem and size; the thinking-ON run is in progress.
### PoC CO1, Qwen3-8B thinking OFF → ON (12:30; all sizes pooled, 12k-token cap)
| problem / arm | feasible off→on | gap % (feasible only) off→on | within 1% off→on |
|---|---|---|---|
| knapsack direct | 0.58 → 0.04 | 30 → 0.8 | 0.08 → 0.04 |
| knapsack solver | 0.88 → 0.75 | 0 → 0 | 0.88 → 0.75 |
| knapsack heuristic | 1.00 → 0.92 | 19 → 60 | 0.79 → 0.17 |
| TSP heuristic | 0.33 → 0.33 | 3.1 → 2.7 | 0.17 → 0.25 |
| colouring heuristic | 0.89 → 0.78 | 217 → **5.4** | 0.06 → **0.61** |
| scheduling heuristic | 0.89 → 0.72 | 52 → **1.0** | 0.22 → **0.44** |
| TSP / scheduling solver | 0 → 0 | — | — |
- **Thinking trades coverage for quality.** 50% of thinking responses hit the 12k cap (direct: 74/84 never reach an
  answer; code arms: 25–26/84 no code). When they *do* answer, quality jumps (colouring heuristic gap 217% → 5%,
  scheduling 52% → 1%, direct answers near-optimal).
- **The solver arm is still blocked by API misuse with thinking** (TSP/scheduling solver feasible 0/24 each).
- For the project: compare at **matched token budgets** (and/or larger caps) and add a **repair arm** (feed back the
  traceback / infeasibility), which is likely the decisive factor for the solver paradigm at 8B.
### PoC CO1 repair arm, Qwen3-8B thinking OFF, ≤2 feedback rounds (traceback / no output / "infeasible") (12:35)
| problem / arm | feasible 0 → 2 repairs | within 1% | beats greedy | mean tokens |
|---|---|---|---|---|
| colouring solver | 0.33 → **0.83** | 0.06 → **0.56** | 0.00 → 0.22 | 299 → 789 |
| TSP heuristic | 0.33 → **0.79** | 0.17 → 0.29 | 0.25 → 0.38 | 577 → 1370 |
| TSP solver | 0 → **0** | – | – | 365 → 1193 |
| scheduling solver | 0 → **0** | – | – | 397 → 1747 |
| knapsack (both arms) | unchanged (already working) | | | |
- **Repair fixes colouring's CP-SAT model** (feasible 0.33 → 0.83, within-1% 0.06 → 0.56), but **never** fixes TSP or
  scheduling: 44/84 solver programs still crash after 2 rounds. Repair spends 2–4× the tokens.
- Repair makes TSP heuristics feasible (0.33 → 0.79), but at worse average gap (newly feasible tours are poor).
- So at 8B the solver paradigm is blocked by persistent API misuse for routing/scheduling models. A hypothesis
  for the project: API errors are model-size limited and won't be fixed by feedback alone. Test at 32B, and with
  documentation/API snippets in the prompt (retrieval).

### 13:30 batch
**G2 with thinking ON (Qwen3-8B, 10k cap):**
- Direct + thinking: 81% of answers never arrive (66% truncated). Accuracy 0.15, consistency 0.00. Thinking doesn't
  rescue direct geometric computation.
- Code + thinking: accuracy 0.89, **lower than code without thinking (0.97)**, and less consistent (hull 0.25,
  closest pair 0.25, pip 0.35 vs 0.90/1.00/0.50 without thinking). Combined with G2b (thinking code breaks on
  degeneracies), **thinking makes this 8B write more fragile geometry code.**

**CO1 scale and API-doc follow-ups** (cells = feasible / within 1% / beats greedy, all sizes pooled):
| problem / arm | 8B | 8B + repair | 8B + API doc + repair | **32B + repair** |
|---|---|---|---|---|
| TSP solver | 0/0/0 | 0/0/0 | 0/0/0 | **0.83/0.38/0.29** |
| TSP heuristic | 0.33/0.17/0.25 | 0.79/0.29/0.38 | – | **1.00/0.71/0.88** |
| colouring solver | 0.33/0.06/0 | 0.83/0.56/0.22 | 1.00/0.06/0 | **0.94/0.94/0.22** |
| scheduling solver | 0/0/0 | 0/0/0 | 0.11/0/0 | **0.44/0.33/0.33** |
| knapsack solver | 0.88/0.88/0.42 | same | 1.00/1.00/0.58 | 1.00/1.00/0.58 |
- **Solver-API competence is mostly a scale effect.** 32B crashes 11/84 solver programs after repair vs 44/84 for 8B,
  and a hand-written OR-Tools cheat sheet barely helps 8B (40/84 still crash; TSP still 0). With the doc, 8B colouring
  becomes feasible but no longer optimal (it drops the minimisation).
- **At 32B the LLM-written TSP heuristic beats nearest-neighbour greedy 88% of the time** (71% within 1% of the
  best-known tour). It's the first configuration where an LLM heuristic clearly beats the textbook baseline.

**PoC F with an 8B student (tutor 8B or 32B):** hints give **no gain** (L0 0.47–0.48; L1–L3 0.45–0.47; placebo
0.45–0.47). Only the full solution helps (0.62), and that disappears when near-copies are discounted
(leakage-adjusted 0.48 ≈ baseline). **Hint value depends on the tutor–student gap:** a large gain for the 1.7B student
(L3 0.04 → 0.24–0.26 on hard problems), none for 8B. Full-solution "help" for strong students is mostly copying.

### 14:30 batch
**PoC A games with thinking ON (8B, 6k tokens/turn), v2 rules:** number guessing is not better than without thinking
(N=10^6: 10/15 solved, guess consistency 0.55; v2 thinking-off 0.71). **Mastermind: 8/30 solved** (non-thinking
0/30), but averaging 9.4 guesses vs Knuth's ≤5, with only 26% of guesses consistent with past feedback and 43%
unparseable or truncated turns. Thinking unlocks Mastermind partially; deduction over accumulated feedback (the
state) is the bottleneck, as MastermindEval reports. Novel angle per the scan: separate *inconsistent* from
*consistent-but-uninformative* guesses (needs consistent-set size tracking, already logged per guess).

**G2 scale point, Qwen3-32B-AWQ code arm (thinking off):** accuracy 0.93 (8B: 0.97). Consistency: hull 0.90,
area 1.00, closest pair 1.00, but **pip 0.35, segs 0.40** (segments on the 1e9 variant: 0.55). Cross-variant
execution: 89/100 programs correct on all variants (8B: 96/100); failures are transform-only 5, degenerate-only 3,
logic 2. **Scale does not buy geometric robustness of code**: the 32B writes slightly *less* invariant geometry
code. (Direct 32B arm still running.)
**G2 scale point, Qwen3-32B direct answers (thinking off):** overall accuracy **0.23 (8B: 0.22)**, cross-transform
consistency ≈ 0 (hull 0.05, all others 0.00). **Model size does nothing for direct geometric computation's invariance**,
just as it did nothing for code robustness. The paradigm (code vs direct) dominates; size doesn't.
Ops 15:05: the 32B geo queue finished and freed GPU 0. The new 8B lane server on GPU 1 was crowded to 6 GB free by
a foreign 36.6 GB job, so I moved it to GPU 2. The canonicalize + best-of-4 runs restarted from scratch (neither
supports resume).
### 15:00 batch: last CG/CO follow-ups (8B, thinking off)
**G2 canonicalize-then-solve** (translate so min x,y = 0 first): overall accuracy 0.22 → 0.25 (area 0.20 → 0.60 on
identity, the only clear gain), and consistency still **0.00 on every task**. Removing big-coordinate arithmetic is
not enough; direct answers stay non-invariant. The drift is in the algorithmic reasoning, not the offsets.
**CO1 token-matched comparison** (feasible / mean gap / within 1% / mean output tokens):
| problem | direct ×1 | direct best-of-4 | solver + 2 repairs |
|---|---|---|---|
| knapsack | 0.58 / 30% / 0.08 / 970 | 0.88 / 20% / 0.12 / 3826 | **0.88 / 0% / 0.88 / 439** |
| TSP | 0.42 / 42% / 0.04 / 1158 | 0.83 / 72% / 0.00 / 2914 | 0 / – / 0 / 1193 |
| colouring | 0.17 / 28% / 0.06 / 960 | 0.39 / 250% / 0.17 / 3776 | **0.83 / 12% / 0.56 / 789** |
| scheduling | 0.61 / 13% / 0 / 1815 | 0.94 / 12% / 0 / 7027 | 0 / – / 0 / 1747 |
- Sampling 4× buys **feasibility, not quality**: gaps stay large or get worse because more poor-but-feasible answers
  are counted. At 4–9× fewer tokens, a working solver program dominates (knapsack/colouring), but where 8B can't
  write the solver (TSP/scheduling), extra direct samples are the only route to feasibility.

## Novelty check T1 / T2 (15:20; agent; abstracts + partial full text)
- **T1 CO metamorphic invariance: novel as a combined design.** The closest threat is *Falsification-Based Verification
  of LLM-Generated Optimization Models* (2607.16646, Jul 2026): exchange (swap interchangeable entities) and objective
  homogeneity (scaling) relations, but for LLM-written LP/MILP formulations only. EHOP covers costumed/inverted
  presentations; *Lost in Serialization* covers relabel/edge-order for graph reasoning (not CO objectives). Open: one
  battery of exact symmetries across direct / solver / heuristic; violation rate as a metric separate from optimality
  gap; whether code mode inherits solver invariance. Tweak: add **near-symmetry controls** (scale + rounding, a
  barely-dominated item) and report violations conditional on the base answer being correct.
- **T2 adversarial tests for buggy LLM geometry code: likely novel.** No LLM work targets geometric degeneracies;
  REFUTE/CodeHacker/TestCase-Eval are general, Spatter is library-only. Must-have baseline per the scan: a **non-LLM
  degeneracy-biased random generator** (lattice snap; forced collinear/coincident/touching), so any LLM hint gain
  is measured against cheap structured sampling.
### T3 robustness hint for geometry code, Qwen3-8B (15:20; cross-variant execution)
Prompt adds: "coordinates up to 1e9; use exact integer arithmetic only (cross products, no floats/division/atan2);
handle degenerate cases (duplicates, collinear points, a ray through a vertex, touching/overlapping segments)".
| | correct on all 8 variants | point-in-polygon correct_all |
|---|---|---|
| no hint (G2b) | 96/100 | 16/20 |
| **with robustness hint** | 84/100 | **4/20** (6 crash, 4 degen-only, 4 transform-only, 2 logic) |
**The robustness instruction makes the code worse.** The other tasks stay at 20/20. For point-in-polygon the model
abandons the standard ray-casting idiom and hand-rolls integer-only edge/degeneracy logic with new bugs: undefined
variables (`qy` NameError), treating "on the edge" or "collinear with an edge's line" as outside, wrong side tests.
Over-specifying robustness requirements pushes a small model off well-trodden code paths. This is a useful negative
result for the G2 project (32B run of T3 in progress).
### T3 at 32B (15:25): the robustness hint hurts here too
Qwen3-32B cross-variant: correct on all 8 variants **89 → 73/100** with the hint. Segments drop 17 → **5/20**
(10 degenerate-only, 5 logic); pip 12 → 11; closest pair 20 → 17 (3 crash). The model and the task that break differ
(8B: pip; 32B: segments), but **explicit robustness requirements make LLM geometry code less correct at both sizes.**

### T1 CO metamorphic invariance, Qwen3-8B thinking off, ≤2 repairs (15:35; 6 instances × 4–5 variants per cell)
- **Direct answers: consistency 0.00 in every cell**, and never optimal (knapsack, TSP, colouring, scheduling), exactly
  as with direct geometry answers (G2).
- **Code arms: consistency 0.22 on average.** Even when the base answer is optimal, a semantics-preserving variant
  breaks it 17–33% of the time (knapsack 20 solver 0.17, heuristic 0.33; colouring solver 0.25), and 100% for
  knapsack-40 solver / TSP-12 heuristic (small n).
- **Input-conditioned code again:** TSP heuristics hit the optimum 0.83 of the time on the *translated* instance vs
  0.17 on the identity one. Scaled-weight knapsack (×3) is the variant code arms fail most (0.67–0.83). Because the
  program is regenerated per variant, surface numbers change the algorithm the model writes. (Same mechanism as G2b's
  "seeing 1e9 coordinates writes worse code".)
- The 8B solver arm is unusable for scheduling and TSP (0 feasible), so invariance can't be assessed there. Needs 32B.
### T2 setup note (15:50)
The 38 buggy programs harvested from G2b/T3 are **not subtle**: random instances break most of them immediately
(random fail rate 0.08–0.83; only 2/38 fail ≤5% of random instances but some degenerate ones). Real T2 targets need
a pool: `poc/run_geo_pool.py` samples 24 programs per task per model (temperature 0.8) and keeps the SUBTLE ones
(random fail ≤5%, degeneracy-biased fail >0). Then 4 strategies race to break them: random, degeneracy-biased random
(non-LLM), LLM blind generator, LLM code-aware generator.
### T2 breaking subtly-wrong LLM geometry code (16:45)
**Pool:** 240 sampled programs (24 per task × 5 tasks × {8B, 32B}, temperature 0.8). **205 are correct on both random
and degeneracy-biased inputs**; only **7 are subtly wrong** (pass ≥95% of random instances, fail some degenerate ones:
32B segments ×2, 8B polygon area ×5). Degenerate-only bugs are **rare** in LLM geometry code at these sizes. Most
failures are gross ones that random testing catches.
**Breaking the 7 subtle programs (50 inputs each):**
| strategy | broken |
|---|---|
| random instances | 2/7 |
| **degeneracy-biased random (no LLM)** | **6/7** |
| LLM generator, problem only | **0/7** |
| LLM generator, sees the buggy code | 5/7 |
- **The cheap structured (non-LLM) baseline wins.** An LLM that doesn't see the code never finds these bugs (its
  "tricky" generators produce generic inputs). Seeing the code lets the 8B target the bug (0 → 5/7, unlike PoC #2's
  non-thinking result, where code didn't help).
- **Verdict for T2 as a project:** too few natural targets (7/240) for statistics. It would need injected bugs
  (mutation of correct programs at degenerate predicates) to scale. Keep it as a sub-result of the G2 project:
  "degenerate-only bugs are rare; when present, structured degeneracy fuzzing beats LLM test generation".

### 17:30 batch: scale and model-family checks
**T1 CO metamorphic at Qwen3-32B (≤2 repairs):**
| arm | mean consistency (8B → 32B) | notes |
|---|---|---|
| direct | 0.00 → **0.00** | never optimal in any cell, any variant |
| heuristic | 0.22 → 0.31 | even optimal base answers break under a variant 25–100% of the time |
| solver | 0.22 → **0.50** | **knapsack 20/40 and colouring: 1.00 consistent and 100% optimal on every variant**; TSP solver still 0 feasible; scheduling 0.33 feasible |
- **The only invariant paradigm is a correct solver model**: when the 32B writes a working CP-SAT model, every
  variant is optimal (consistency 1.00). LLM heuristics stay non-invariant (TSP-12: identity optimal 1.00, but
  translate drops to 0.67), and direct answers never are.
- At 32B the routing/scheduling solver arm is still the bottleneck (TSP solver 0 feasible here, vs. 0.83 in CO1 with
  repair; different prompts per variant).
**G2 with a second model family, Llama-3.1-8B-Instruct:**
- Direct: accuracy **0.12** (Qwen3-8B 0.22), consistency **0.00** on every task. Same conclusion across families.
- Code: accuracy 0.81 (Qwen 0.97). Hull/area/closest pair ~invariant (0.95–1.00), **point-in-polygon 0.00 consistent**
  (identity 0.40, 1e9 offset 0.00), segments 0.45. Cross-variant: 82/100 programs correct on all variants; 11/20 pip
  programs crash.
- **G2's headline generalises across model families:** direct answers are never invariant; code is invariant except
  for the numerically fragile predicates (point-in-polygon, segment intersection).

### PoC A state-tracking control (18:30; environment restates the state each turn), Qwen3-8B
| game | thinking off: no state → **with state** | thinking on: no state → **with state** |
|---|---|---|
| guess N=1000 | 14/15 solved, consistent 0.73 → **15/15, 1.00** (8.5 guesses; optimal ≤10) | 15/15, 0.84 → **15/15, 1.00** |
| guess N=10^6 | 12/15, consistent 0.71, 27.6 guesses → **15/15, 1.00, 19.3** (optimal ≤20) | 10/15, 0.55 → **15/15, 1.00, 18.7** |
| Mastermind | 0/30, consistent 0.10 → **0/30, 0.10** | 8/30, 0.26 → **10/30, 0.31** (10.7 guesses vs ≤5) |
- **A clean decomposition.** Number-guessing failures were **pure state tracking**. Given the current interval, the
  8B plays optimal binary search at every N with 100% consistent guesses. **Mastermind failures are deduction, not
  memory.** Restating the full feedback history barely helps (consistency 0.10 → 0.10 without thinking, 0.26 → 0.31
  with thinking). The model can't infer which codes remain possible.
- This is exactly the open angle the novelty scan named (split the excess-guess gap into state tracking vs.
  strategy/inference), now answered for one family. Next: does scale (32B) fix Mastermind deduction?
- 32B with state summary, thinking OFF (19:30): number guessing optimal at every N (N=10^6: 15/15, 19.1 guesses,
  100% consistent). **Mastermind 0/30 solved, consistency 0.08**, the same as 8B. **Scale alone does not fix
  non-thinking Mastermind deduction.** (32B thinking ON is running.)
- **32B + thinking + state summary, Mastermind (22:30):** **15/30 solved** (8B thinking + state 10/30; any model
  without thinking 0/30). Mean 8.3 guesses when solved (5 games in ≤5, Knuth's bound), but **only 29% of guesses are
  consistent with the feedback**, and 30% of turns are unparseable or truncated at 8k tokens. Thinking plus scale
  partially unlock deduction, but even the best configuration mostly guesses codes that the feedback already rules
  out. **Topic A summary:** binary search = a state-tracking problem (solved by restating state, at any size);
  Mastermind = a deduction problem (needs thinking; improves with scale; still far from consistent).

## G2-deep: from diagnosis to SOLUTIONS (user request, 2026-10-09)
**Pairwise cross-variant agreement** (a softer metric than all-8-identical): direct answers agree only 0.00–0.50
(yes/no point-in-polygon ≈ chance 0.35–0.50; hull 0.14–0.35; area/segments/closest pair 0.00–0.22). Thinking makes it
*worse* (0.00–0.35). Code is 0.97–1.00 except pip (0.05–0.80) and segments (0.78–1.00).
**Offline solution arms (no new generations):**
- **S3 metamorphic voting for direct answers** (majority of the normalised answers over the 7 equivalent variants):
  identity accuracy 8B 0.20 → **0.34**, 32B 0.21 → **0.33**, Llama 0.09 → 0.11, 8B-canon 0.31 → 0.34. It helps (+60–70%
  relative for Qwen) but stays far below code (0.8–0.97). Invariance can be bought at inference time only partially.
- **S2 canonicalising the input given to code** (min x = min y = 0 before execution): **no effect** (0.96 → 0.96;
  32B 0.89 → 0.89; Llama 0.82 → 0.83). Programs written from a normal-looking instance have no offset bug. The
  huge-coordinate damage happens at *generation time*, so the fix must canonicalise the **prompt** (S2b, running).
**Running (GPU):** S1 metamorphic self-repair (label-free) vs. oracle-feedback repair vs. none, 8B + 32B, with
fresh-instance generalisation; S4 exact predicates supplied in the prompt (8B + 32B); S2b canonicalised prompt (8B);
code-mode rerun with stored programs (float-usage mechanism).
### G2-deep results, 8B (14:30)
- **S1 metamorphic self-repair: no gain at 8B** (all variants correct 0.97 → 0.97; fresh instances 0.97 → 0.96).
  Oracle-feedback repair: also 0.97. The base programs are already 97% right, and the rare pip failures are mostly
  *consistently* wrong (invariant-but-wrong), which a metamorphic check can't see; repair rarely triggers (0.05–0.07
  rounds/program). MR repair needs targets that are non-invariant. (32B results pending; its base rate is lower.)
- **S4 exact primitives in the prompt: the best fix.** Correct on all 8 variants **98/100** (baseline 96; robustness
  hint 84). **Point-in-polygon 20/20** (baseline 16/20, hint 4/20). Supplying trusted predicates works; *telling* the
  model to be robust backfires.
- **Mechanism of the 1e9 effect (8B code per variant, programs stored):** for pip, programs written from the 1e9
  prompt use floating point only 11% of the time (normal prompts 80–100%), and they are wrong 42%. Float programs are
  97% correct, integer-only ones 53%. **Huge coordinates push the model off the standard (float ray-casting) idiom
  onto hand-rolled integer logic with bugs**, the same failure the T3 hint causes. Unifying claim: *perturbations that
  push a model off its well-practised idiom (huge numbers, robustness instructions) cause bugs; supplying the idiom
  (S4) fixes them.*
### G2-deep results, 32B + S2b (15:30)
- **S1 metamorphic self-repair at 32B: small, real gain.** All 8 variants correct 0.89 → **0.93** (label-free MR feedback)
  = 0.93 with oracle feedback; fresh instances 0.87 → 0.91 (oracle 0.90); acc_fresh 0.956 → 0.972. All gain is pip
  (0.55 → 0.70 base; 0.40 → 0.60 fresh). **Label-free MR feedback matches ground-truth feedback**, so the metamorphic
  check carries as much information as labels here. Repair triggers rarely (0.12 rounds/program). Contrast with 8B
  (0.97, no headroom): MR repair pays off only where the base has non-invariant bugs.
- **S4 exact primitives at 32B: mixed.** 84/100 correct on all variants (baseline 89). It fixes exactly the targeted
  tasks (pip 12 → **20/20**, segs 17 → **20/20**) but breaks unrelated ones: hull 20 → 8 (logic 4, degen_only 6),
  close 20 → 16 (4 crashes). Inspection: (a) **tool-induced over-engineering**: with `on_segment` in context the model
  adds a spurious "remove collinear points on hull edges" pass after a correct monotone chain, which drops real
  vertices; (b) **format neglect**: the long predicate block pushes the stdin spec out of focus and the program reads
  the `n` line as a point (crash) or mis-indexes. 8B didn't show this (hull 18, close 20). Follow-up running
  (queue_s4b.sh, 32B): task-matched predicates only (S4b) × restating the stdin format after the block (S4c).
- **S2b canonicalised prompt (8B code; instance translated to min x = min y = 0 in prompt and execution):**
  'big' variant pip 11 → **18/20**, hull 15 → **20/20**; consistency pip 0.35 → 0.65, hull 0.75 → 1.00; overall
  non-degenerate acc 0.959 → 0.979. **Confirms the mechanism**: pip-big float use 2/20 → 18/20 once the 1e9 numbers are
  hidden. (S2 = canonicalising execution alone did nothing, so the damage is at generation time.) One regression,
  area2-mirror 20 → 14: all 6 failures are a single n=14 instance family whose program has the typo
  `x1*y2 - x1*y2` (a sporadic slip, not a mechanism). Caveat: S2b removes the 'big' variant by construction, so
  it's a preprocessing fix that applies only to translation-invariant tasks (true for all five).
- **Solution scoreboard (all variants correct, /100):** 8B base 96, hint 84, S1 97, S4 **98**; 32B base 89, S1 93,
  S4 84 (pip/segs 20/20 but hull/close broken). Story: *supplying the idiom works when it's scoped; a generic
  toolbox can distract a larger model.*
### S4b/S4c ablation, 32B (15:36): the toolbox has to be scoped
| 32B arm (all 8 variants correct, /100) | total | hull | close | pip | segs |
|---|---|---|---|---|---|
| baseline code | 89 | 20 | 20 | 12 | 17 |
| S4 all predicates | 84 | 8 | 16 | 20 | 20 |
| S4c all predicates + format restated after the block | 98 | 18 | 20 | 20 | 20 |
| **S4b task-matched predicates only** | **100** | 20 | 20 | 20 | 20 |
| S4b + S4c | 100 | 20 | 20 | 20 | 20 |
- Mechanism confirmed by counting: with all predicates, **20/20 hull programs call `on_segment`** (baseline 0/20, task-matched
  0/20), and **all 12 failing hull programs** do; this is the spurious "remove collinear points" pass. Restating the
  format fixes the close crashes (format neglect) and reduces the over-use (14/20, failures 2).
- Takeaway for the project: *what to give the model* matters more than *how hard to tell it*. Scoped exact primitives
  give 100/100 at 32B, up from 89 baseline and 84 with the unscoped toolbox, while a "be robust" instruction lowers
  accuracy. That's a clean diagnosis-and-fix story (distractor-tool effect ≈ the "irrelevant context" literature,
  e.g. GSM-IC). **8B task-matched: 100/100** too (baseline 96, all predicates 98).
### Ops (16:30)
- Killed an orphaned `run_graphs.py --model_tag gr8b_nothink` (PID 318305; up 32 h, pointed at the dead :8000 server,
  produced no output). B (graph encodings) stays deprioritised (GrAlgoBench covers it), so it won't be rerun.
- Queued queue_s4seeds.sh: does task-matched > all-predicates > baseline survive sampling? T=0.7 × 3 seeds × 3 arms,
  8B (:8025) and 32B-AWQ (:8026) lanes.
### S4 under sampling (T=0.7, 3 seeds, 17:10): the scoped-toolbox result holds
All 8 variants correct, % of 100 programs, mean over 3 seeds; paired cluster bootstrap over the 100 instances.
| arm | 8B | 32B | hull 8B/32B | area2 | pip | segs | close |
|---|---|---|---|---|---|---|---|
| baseline | 88.7 | 84.3 | 78/88 | 92/93 | 77/60 | 97/80 | 100/100 |
| all predicates | 91.3 | 80.3 | **58/62** | 100/**60** | 100/98 | 98/100 | 100/**82** |
| **task-matched** | **96.0** | **96.7** | 98/93 | 82/95 | 100/97 | 100/100 | 100/98 |
- task-matched − baseline: **8B +7.3 pts [+2.7, +12.0]; 32B +12.3 [+7.3, +17.3]**. Task-matched − all: 8B +4.7
  [−0.3, +9.7]; **32B +16.3 [+11.3, +21.3]**. All − baseline: 8B +2.7 [−3.0, +8.0]; 32B −4.0 [−11.3, +3.3].
- The distractor effect replicates and spreads. Unscoped predicates fix pip/segs but damage hull at both sizes (8B
  78 → 58, 32B 88 → 62), plus area2 (93 → 60) and close (100 → 82) at 32B. `on_segment` is called in 49/60 (8B) and 57/60
  (32B) hull programs, including **23/23 failing 32B hull programs**. Under sampling, 8B is hurt as well, which the
  greedy run had hidden.
- Noise check: for area2, the task-matched prompt equals the baseline (no predicates), yet 8B scores 82 vs 92 (big_only
  8 vs 4; float `abs(s)/2` at 1e9). So **per-task cells carry about ±10 pts of sampling noise at n=60**. Use the pooled
  numbers and CIs, not single cells. The 1e9 float issue on area2 is the remaining failure mode, and S2b canonicalisation
  addresses it.
### CO scoped API snippet: the geometry S4b idea carried over to CO (17:25)
Solver arm + 2 repair rounds; cells = feasible / within 1% of optimum, 6 instances × sizes pooled (84 per row).
| arm | knapsack | TSP | colouring | scheduling | **all** | crashes |
|---|---|---|---|---|---|---|
| 8B, no doc | .88/.88 | 0/0 | .83/.56 | 0/0 | .43/.37 | 46 |
| 8B, full cheat sheet | 1/1 | 0/0 | 1/.06 | .11/0 | .52/.30 | 40 |
| **8B, scoped snippet** | 1/1 | 0/0 | .83/.83 | **.61/.61** | **.60/.60** | 34 |
| 32B, no doc | 1/1 | .83/.38 | .94/.94 | .44/.33 | .82/.67 | 11 |
| 32B, full cheat sheet | 1/1 | 1/1 | .94/.89 | .56/.50 | .89/.87 | 9 |
| **32B, scoped snippet** | 1/1 | .92/.92 | **1/1** | **.72/.72** | **.92/.92** | 5 |
- **Scoped beats full on quality at both sizes** (within 1%: 8B .30 → .60, 32B .87 → .92). The full sheet's main
  failure at 8B is the one already noted: colouring becomes feasible but drops the minimisation (.06 optimal). The
  scoped snippet restores it (.83) and unlocks scheduling (0 → .61). Same shape as geometry: *scope the toolbox*.
  (Single greedy run, n=84; per-problem cells are 18–24 instances, so differences of about 0.1 are noise.)
- **Limit: 8B TSP is still 0/24 even with the 12-line routing recipe in the prompt.** Probe with stderr (9 programs):
  the model passes the Python function instead of the registered callback index
  (`SetArcCostEvaluatorOfAllVehicles(transit_callback)`), and invents
  `routing_enums_pb2.RoutingSearchParameters`. Neither the doc nor 2 rounds of stderr repair fix it: **the API prior
  overrides the in-context recipe**. Remaining 32B scheduling failures at n=40 (5/6), and 8B ones, are
  `m.Add(makespan >= load[q] for q in ...)`, a generator passed to `Add` (CP-SAT has no batch Add). This is a
  consistent misconception, not a slip.
- Project framing: "a solver-API prior that resists in-context correction" is a sharp, testable sub-question.
  Candidate fixes: a verified wrapper (`solve_tsp(D)` / `add_all(m, cons)`), or AST-level lint+rewrite of known
  misuse patterns before execution. Both are cheap to test next.
### Running (17:40): misconception shim for solver code
poc/api_shim.py is a prelude that makes OR-Tools tolerant of the observed misuse and logs each use: `Add(<generator>)` → add
each one; `SetArcCostEvaluatorOfAllVehicles(<function>)` → register it first; invented
`routing_enums_pb2.RoutingSearchParameters()` → `DefaultRoutingSearchParameters()`. Unit-tested: both probe failure
patterns now run (sched optimum 9, TSP tour found). run_co.py `--shim` also re-runs the round-0 program without the shim
(status0_noshim/feas0_noshim) for attribution, and now stores `code`, `err` and `shim_used`. Queue: queue_shim.sh (8B
scoped+shim, 8B no-doc+shim, 32B scoped+shim).
### ⚠️ Harness bug found (17:55): CP-SAT thread crashes in the sandbox; CO solver numbers to be re-measured
- While attributing the shim, 14 of the 32B round-0 programs "failed only with the shim". Reproduced serially: the same
  final programs randomly die with `Resource temporarily unavailable` / `cannot allocate memory for thread-local data`
  **with or without the shim**. Cause: CP-SAT starts one worker per core (64), and glibc's per-thread malloc arenas
  (64 MB of address space each) exceed the sandbox RLIMIT_AS (4 GB). FIX: sandbox env `MALLOC_ARENA_MAX=2` → 0 thread
  errors on re-run; the remaining failures are genuine (`x[j][var]` indexing, invented `SetMaximizeTotalCost`, NameErrors).
- Impact: every OR-Tools solver-arm number so far (CO1, T1 cometa, doc/doctask tables) contains random crashes. Those
  wasted repair rounds and probably **under-state solver arms**, mostly scheduling and colouring, which use CP-SAT
  (routing/TSP is single-threaded, so its failures are real). Shim attribution (round-0 noshim vs shim) is
  contaminated too. Heuristic/direct arms are unaffected.
- Provisional shim results (contaminated, kept for the record): 8B scoped+shim .69 within 1% (scoped .60; crashes
  34 → 7; sched .61 → .89, colour .83 → 1.00). 8B no-doc+shim .35 (no gain: without the doc the model makes *different*
  misuses, e.g. `SetArcCostEvaluatorOfTransitCallback`, wrong RoutingModel ctor). 32B scoped+shim .93 (shim never fired).
- **8B TSP is still ~0 with scoped doc + shim, and this one is real:** 19/24 programs now RUN (the shim fixed the
  invented params class) but print `tour + [tour[0]]` (n+1 cities: the "return to start" convention). They also
  register the cost callback but never set it as arc cost, which yields arbitrary tours. Two more misconceptions
  sit behind the first; fixing one exposes the next (error cascade).
- Re-run queued: queue_co_v2.sh, solver arm × {no doc, full doc, scoped doc, scoped+shim, shim} × {8B, 32B}, tags *_v2.
### CO solver arms, CLEAN re-run after the sandbox fix (18:10): supersedes the doc/doctask/shim tables above
Solver arm + 2 repair rounds; feasible / within 1%; 84 instances; 0 thread errors in every run.
| arm | 8B knap | 8B TSP | 8B colour | 8B sched | **8B all** | crashes | **32B all** | 32B TSP |
|---|---|---|---|---|---|---|---|---|
| no doc | .88/.88 | 0/0 | 1/.72 | 0/0 | .46/.40 | 42 | .92/.80 | .75/.33 |
| full cheat sheet | 1/1 | 0/0 | 1/**.06** | 0/0 | .50/.30 | 42 | **1.00/1.00** | 1/1 |
| **scoped snippet** | 1/1 | 0/0 | 1/1 | **1/1** | **.71/.71** | 24 | .98/.98 | .92/.92 |
| shim only | .88/.88 | 0/0 | 1/.72 | .06/.06 | .48/.42 | 41 | .89/.70 | .75/.08 |
| scoped + shim | 1/1 | .12/.04 | 1/1 | 1/1 | **.75/.73** | **4** | 1.00/1.00 | 1/1 |
- **8B: the scoped snippet is the lever** (within 1%: .30 full sheet / .40 no doc → **.71**). The full sheet makes colouring
  feasible but drops the minimisation (.06), and leaves scheduling at 0. The scoped snippet takes both to 1.00.
- **32B: any API doc saturates** (full 1.00, scoped .98). **RETRACT** the earlier "scoped beats full at 32B" (.87 vs .92):
  that was the thread-crash artifact. The doc mainly fixes 32B TSP *quality* (no doc: feasible .75 but only .33 near-optimal;
  the doc's GLS + time-limit recipe gives 1.00).
- **Shim = a cheaper substitute for repair, not a new capability.** Round-0 success with the scoped doc: 42 → **60**/84 with
  the shim (same programs; it fired add_iter 18, params_alias 24, register_cb 4). Crashes 24 → 4, repair rounds/instance
  .79 → .55, but the final within-1% gain is small (.71 → .73) because 2 repair rounds fix most of the same errors. Without the
  doc it does nothing (the misuses differ). At 32B it never fires.
- **8B TSP stays ~0 in every arm, a robust negative.** After the shim, programs run but append the start city (n+1 entries)
  and/or never set the registered callback as arc cost. Neither the doc nor stderr repair fixes it.
- **Noise estimate:** "shim only" has the same prompt as "no doc" (the shim never fires at 32B), yet 32B TSP near-optimal
  is .33 vs .08 and overall .80 vs .70. So **single-run per-problem cells carry about ±0.1–0.25 of noise**; quote pooled rows.
- Earlier CO1/T1 solver-arm numbers (before 17:55) also had random thread crashes. The qualitative CO1 claims (direct collapses
  with size; 8B solver API misuse; 32B better) still hold in the clean rows. T1 solver consistency should be re-measured
  before any write-up.
### T1 solver arm, clean re-run (18:25)
Mean consistency (all variants feasible + same normalised objective): **8B 0.22 → 0.28, 32B 0.50 → 0.61**. Largest change:
32B scheduling feasible .33 → **1.00** (consistent .67). That cell was mostly thread crashes. Knapsack/colour unchanged
(32B 1.00). Conclusions unchanged in direction (32B solver code is the most invariant arm). **But solver-TSP is 0 feasible
at both sizes in T1, while CO1 solver-TSP on the SAME instances is .75–1.0** (after 2 repair rounds). Suspect: T1's repair
feedback says "missing or INFEASIBLE" while CO1 says "INFEASIBLE (… wrong format/length)". The round-0 programs print
n+1 cities (return to start), and only the explicit "length" hint lets the model fix that. Testing (queue_t1fb.sh: 32B,
TSP, detailed vs vague feedback). If confirmed: feedback specificity is itself a finding, and T1 TSP solver cells must use
the detailed wording.
- **Confirmed (18:33): repair-feedback wording decides solver-TSP.** 32B, T1 TSP, same instances and code path; only the repair
  message differs. Vague "missing or INFEASIBLE": feasible **0.00 / 0.00** (n=12/20). Detailed "INFEASIBLE (… wrong
  format/length)": **0.93 / 0.60**. The model can't diagnose its n+1-city output (return to start) without the word "length".
  So *repair feedback specificity* is a first-class variable, and every repair comparison must hold it fixed (CO1 used
  the detailed wording; T1 now has `--fb_detail`).
- Even when feasible, solver-TSP without a time-limited metaheuristic is **not invariant** (consistency 0.00; optimal .37/.17).
  Default routing first-solution heuristics depend on labels/coordinates. "Uses an exact solver" ≠ invariant unless it
  actually proves optimality. That's a nice nuance for the T1 story.
### PoC A solutions for Mastermind deduction (queued 18:45)
- Reference from an offline harness test: a **uniformly random player** has guess consistency **0.08**. Non-thinking 8B/32B
  (0.10/0.08) are therefore at chance: no deduction at all.
- New arms in run_games.py: **S-A1 `--verify K`**: an inconsistent guess is rejected (not counted) with a concrete
  counter-example ("your earlier guess X got B1 W2, but if the secret were Y it would have got B0 W1"), up to K times
  per turn. **S-A3 `--code`**: the model writes one codebreaker program (stdin = history, stdout = next guess) that the
  env runs each turn (the code-vs-direct theme of G2/CO, carried into an interactive setting). Offline check with a
  reference "first consistent code" program: solves 5/5 in 4–6 guesses.
- queue_mmsol.sh: 8B {code, code+think, sp+verify3, think+sp+verify3}; 32B {code, code+think, sp+verify3}; 30 games each.
### PoC A Mastermind solutions: results (22:35)
30 games each; "consistent" = share of counted guesses consistent with all prior feedback (random player 0.08).
| config | solved | guesses when solved | solved in ≤5 | consistent |
|---|---|---|---|---|
| 8B / 32B no-think + state (baseline) | 0 / 0 | – | 0 / 0 | .10 / .08 |
| 8B think + state (baseline) | 10 | 10.7 | 1 | .31 |
| 32B think + state (best baseline) | 15 | 8.3 | 5 | .29 |
| **S-A1 verifier, no-think + state** 8B / 32B | 0 / 2 | – | 0 / 2 | .10 / .10 (32–37 rejections/game) |
| **S-A1 verifier, 8B think + state** | **17** | **5.4** | **10** | .45 (14 rejections/game) |
| **S-A3 code policy, no-think** 8B / 32B | 8 / **19** | 5.5 / **5.2** | 2 / **12** | .69 / .84 |
| S-A3 code policy + think (8k budget) | 1 / 2 | – | – | – (29/28 of 30 produced no code: truncated) |
- **Code-as-policy is the strongest fix:** 32B non-thinking writes a codebreaker program that solves 19/30 in 5.2 guesses
  (12 within Knuth's bound of 5). The same model playing directly solves 0/30, and with thinking 15/30 in 8.3. Every
  failure is a program crash or invalid output (32B 10/30: NameError/KeyError/IndexError, 1 timeout; 8B 18/30), never bad
  play. So the "code beats direct" theme from G2/CO carries over to interactive deduction. Program repair is queued.
- **The verifier only helps a model that can deduce.** Without thinking, counter-examples change nothing (consistency
  stays at chance 0.10 even after 3 rejections/turn, ~35 rejections/game). With thinking, 8B goes 10 → **17/30** and
  10.7 → **5.4 guesses**, beating the 32B thinking baseline, at ~14 rejected proposals/game (the hidden cost).
- Harness note: code+think at 8k tokens truncates (thinking eats the budget): 29/30 games produced no program. Rerun at 20k.
- Queued queue_mmsol2.sh: code + repair (2 repairs/game) for 8B/32B, and code + think at a 20k budget.
- **Ops bug found and fixed (22:40): the vLLM server inherited the GPU-pick lock fd** (start_server_retry.sh does
  `exec 9>lock; flock 9`, and start_server.sh started the server in the background without `9>&-`). Every server held
  the lock for its whole life, so **the second lane of every two-lane queue waited until the first lane's server
  exited**. Example: the 32B Mastermind lane waited 18:35 → 22:12. Results were unaffected (only wall-clock). Fix:
  `9>&-` on the server launch, and pick failures are now logged in gpu_choice.log. (Also: `sed -i` on this CIFS mount
  can't rename its temp file and **deleted both scripts**. They were recreated from known contents. Never use `sed -i` on
  /NAS; write with python/Write instead.)
### PoC A Mastermind, code-policy follow-ups (22:57): near-optimal play via code
| config | solved | guesses when solved | ≤5 | consistent | crashes | repairs/game |
|---|---|---|---|---|---|---|
| 32B code, no think | 19 | 5.2 | 12 | .84 | 10 | – |
| **32B code + 2 repairs** | **27** | 5.4 | 14 | .86 | 2 | .47 |
| **32B code + think (20k) + repairs** | **30/30** | **4.5** | **29** | 1.00 | 0 | .07 |
| 8B code, no think / + repairs | 8 / 8 | 5.5 / 5.4 | 2 / 3 | .69 / .32 | 18 / 11 | – / 1.23 |
| **8B code + think (20k) + repairs** | **20** | **4.7** | **19** | .46 | 0 | .03 |
- **32B thinking + code is effectively optimal:** 30/30 games, mean 4.5 guesses, 29 within Knuth's worst-case bound of 5. The same model
  playing directly with thinking: 15/30, 8.3. Only 5/30 programs mention minimax/Knuth. Most implement "filter to consistent
  codes + a good pick", which already gives ~4.5 on average. The deduction the model can't do in-context, it can *program*.
- **Repair helps 32B (19 → 27) but not 8B (8 → 8):** 8B's repaired programs stop crashing but play badly.
- **8B thinking + code: 20/30 in 4.7 guesses.** All 10 failures are the same bug class: the program's candidate filter goes
  empty (feedback computed wrong) and it falls back to a constant guess (`AAAA` ×10). Repair never triggers because the output
  is valid. An env-side "repeated guess = invalid → repair" rule would likely rescue these.
- Earlier 8k-budget code+think runs were budget artifacts (29/30 no program). Thinking needs about 20k tokens for a program.
- **Topic A, final story:** binary search fails from *state tracking* (fixed by restating state). Mastermind fails from *deduction*
  (restating doesn't help; at-chance without thinking). Fixes, ranked: **code-as-policy + thinking (30/30, 4.5)** > code +
  repair (27/30) > counter-example verifier + thinking (17/30, 5.4; useless without thinking) > thinking alone (15/30, 8.3).
### PoC D NL→solver on zebra puzzles (started 23:05)
poc/run_zebra.py: logic-grid puzzles generated from a hidden solution until UNIQUE (CP-SAT solution limit 2), redundant clues
pruned. Cells 3x3, 4x3, 4x4, 5x4, 5x5, 6x5 (search space 216 → 1.9e14; 5–22 clues), 8 puzzles each. Arms: direct (JSON grid)
vs code (any library, ≤60 s, up to 2 repairs with LABEL-FREE feedback: crash / bad output / which clue numbers the grid
violates). Thinking off (4k) and on (20k), 8B and 32B. Scored as exact grid + cell accuracy, with tokens for cost.
- Harness fix before the real run: 8B programs `print(dict)` (single quotes). The strict JSON parser scored them as bad_output
  even after 2 repairs, because the model never switched to json.dumps. The parser now also accepts Python literals
  (format isn't the construct under test). The first 3 minutes were discarded and the run restarted on the same servers.
- (Lock fix verified: 8B and 32B servers started 46 s apart, in parallel.)
### PoC D zebra, first results (00:35): exact-grid accuracy, 8 puzzles per cell
| model / arm | 3x3 | 4x3 | 4x4 | 5x4 | 5x5 | 6x5 | **all** | tokens |
|---|---|---|---|---|---|---|---|---|
| 8B direct, no think | 4 | 1 | 0 | 0 | 0 | 0 | .10 | 0.9k |
| **8B code, no think** | 7 | 6 | 8 | 4 | 2 | 0 | **.56** | 3.0k |
| 32B direct, no think | 5 | 3 | 2 | 1 | 0 | 0 | .23 | 2.3k |
| 32B code, no think | 7 | 5 | 8 | 1 | 0 | 0 | .44 | 3.4k |
| **32B direct, think** | 8 | 8 | 8 | 7 | 6 | 2 | **.81** | 7.3k |
| 32B code, think | 8 | 7 | 5 | 3 | 1 | 1 | .52 | 20.1k |
- **Crossover found, and it's reversed by thinking.** Without thinking, code beats direct at both sizes (8B .56 vs .10; 32B .44 vs
  .23). Direct collapses beyond 3x3 while code holds to 4x4. **With thinking, 32B direct beats code (.81 vs .52) at about a third of
  the tokens.** Thinking-mode direct degrades only at 6x5 (2/8).
- **Why code loses: OR-Tools expression misuse, not modelling.** 32B code failures are almost all runtime errors (think 21/48,
  no-think 16/48). They come from `|` on literals, `if` on a BoundedLinearExpression, indexing a list by an IntVar, and invented
  `AddAbs`/`BoolVar`, the same misconception family as in CO. Only 1 (think) / 5 (no think) programs ran and gave a wrong grid.
  8B code fails differently: itertools brute force times out from 5x4 up (tle 9) — modelling-scale.
- Harness bug: the 8B think run died at 29/96 on a context overflow (the repair history carried 20k tokens of thinking).
  Fixed: thinking is stripped from repair history and chat errors are caught. Rerunning.
- Queued (queue_zebra3.sh): scoped CP-SAT snippet for code (the CO S4b fix) for 8B/32B × think on/off; 8B think rerun; 32B think
  code rerun under the history fix (fair baseline for the doc arm). Hypothesis: with the API fixed, code+think ≥ direct+think
  at 5x5/6x5, where direct degrades.
### PoC D zebra with the scoped CP-SAT snippet (01:50): the crossover moves again
| model / arm | 3x3 | 4x3 | 4x4 | 5x4 | 5x5 | 6x5 | **all** | tokens |
|---|---|---|---|---|---|---|---|---|
| 32B direct, think | 8 | 8 | 8 | 7 | 6 | 2 | .81 | 7.3k |
| 32B code, think (history fix) | 7 | 6 | 6 | 3 | 3 | 3 | .58 | 17.8k |
| **32B code + snippet, think** | 8 | 8 | 8 | 8 | 8 | 8 | **1.00** | 7.4k |
| **32B code + snippet, no think** | 8 | 7 | 8 | 7 | 5 | 5 | **.83** | **1.9k** |
| 8B direct, think (rerun) | 8 | 8 | 8 | 7 | 5 | 5 | .85 | 7.1k |
| 8B code, think | 7 | 6 | 3 | 3 | 1 | 1 | .44 | 21.6k |
| 8B code + snippet, think | 6 | 7 | 4 | 5 | 7 | 5 | .71 | 12.6k |
| 8B code + snippet, no think | 6 | 5 | 2 | 2 | 3 | 2 | .42 | 2.4k |
- **With the API fixed, 32B code + thinking is perfect: 48/48, including every 6x5 puzzle, at the same token cost as direct thinking
  (7.4k vs 7.3k).** Direct thinking degrades with size (6x5: 2/8). Without thinking, the scoped snippet takes 32B code from .44 to
  **.83 at 1.9k tokens**, matching direct+thinking (.81) at a quarter of the tokens. The 32B "thinking beats solvers" result was
  entirely an API-misuse artifact: runtime errors 15–21/48 → 0/48.
- **8B can't exploit the solver even with the snippet** (think .71 < direct think .85; no think .42 < plain itertools code .56).
  Without thinking it still misuses CP-SAT (re 18/48). With thinking, 11/48 runs hit the 20k budget before writing code (finish=length).
  This matches CO (8B TSP never fixed by docs): the API prior resists in-context correction at 8B.
- Remaining 32B no-think failures (8 bad_output) are genuine modelling errors (empty output / "No solution found" = an
  over-constrained model / wrong JSON keys).
- **Topic D story:** "When does NL→solver help?" depends on (i) whether the model can drive the solver API (fixable by a scoped
  snippet at 32B, not at 8B), (ii) thinking (direct+think is strong but degrades with search-space size), (iii) size: with a working
  API, code is size-invariant (32B 6x5: 8/8 vs direct-think 2/8). Uncorrected, the comparison inverts: solvers look worse than
  thinking purely because of API misuse. That's a measurement trap worth a section in the paper.
### Running (01:55): generalisation + robustness of the headline fixes (queue_xfam.sh)
- Cross-family: Llama-3.1-8B-Instruct on zebra (direct / code / code+snippet) and geometry (baseline exists: 82/100; + all
  predicates; + task-matched predicates). Does "scoped toolbox" transfer beyond Qwen3?
- Robustness: 32B zebra 5x5/6x5 at T=0.7 × 2 seeds, direct+think vs code+snippet+think (greedy: 14/16 vs 16/16 on these cells).
- run_zebra.py: added --temperature/--seed; the puzzle cache is rewritten only when puzzles are added (concurrent runs read it).
### Generalisation + robustness (02:45)
- **Geometry scoped-toolbox effect replicates on Llama-3.1-8B:** baseline 82 → all predicates **63** → task-matched **94**/100.
  Same mechanism, stronger: with all predicates, hull drops to **0/20** (Qwen 32B: 8) and segs to 7/20. Task-matched: pip 6 → 20,
  segs 20, close 20, hull 14. "Scope the toolbox" is not a Qwen quirk.
- **32B zebra headline is robust under sampling** (T=0.7, 2 seeds, 5x5+6x5, 16 puzzles per seed): direct+think **10/16, 13/16**
  (6 and 3 runs truncated at 20k tokens) vs code+snippet+think **15/16, 16/16** at fewer tokens (9.9k/8.8k vs 13.8k/11.9k).
- **Llama-3.1-8B can't do zebra at all** (0/48 in every arm). Direct: 46/48 runs hit the 4k limit without an answer (long
  unfinished derivations). Code: programs print "No solution found" (over-constrained models) or uninitialised-looking garbage
  values. The snippet doesn't help (like Qwen 8B). A lower bound on capability; the template is fine (the same server gives 82/100 on geometry).

## Cross-topic synthesis (02:50): what is worth doing, with evidence
1. **G2 geometry: invariance failures + fixes (strongest, complete).** Direct answers aren't invariant (0% consistent); code is
   but breaks on perturbations that push the model off its idiom (1e9 → no float → integer bugs; robustness hint hurts).
   Fixes: **task-matched exact predicates 100/100 (8B, 32B, greedy), 96–97 sampled (+7/+12 pts, CI excludes 0); Llama 94**. An
   unscoped toolbox *hurts* (distractor: on_segment over-use, 23/23 failing hull programs). Canonicalised prompt fixes the
   1e9 class. Label-free MR self-repair = oracle repair at 32B.
2. **D NL→solver on zebra (complete, sharp).** No thinking: code ≫ direct. With thinking: direct > code, **but only because of API
   misuse**. With a scoped CP-SAT snippet, 32B code+think = **48/48** (robust: 31/32 sampled) vs direct+think .81 (23/32 sampled,
   degrades with size). 8B/Llama can't drive the solver even with docs. Measurement trap + fix.
3. **CO1/T1 combinatorial optimisation (complete).** Direct collapses with size; solver code needs the API. Scoped snippet: 8B
   .40 → .71 near-optimal (the full cheat sheet *hurts*: .30). The misconception shim replaces repair rounds. Repair-feedback wording
   alone decides solver-TSP (0.00 vs 0.93). Solver ≠ invariant unless optimality is proved.
4. **A interactive strategy (complete).** Binary search = state tracking (restating the state fixes it). Mastermind = deduction
   (at chance without thinking). **Code-as-policy + think: 30/30 in 4.5 guesses (Knuth-level)** vs direct+think 15/30, 8.3. The
   counter-example verifier only helps with thinking (8B 10 → 17/30).
5. #6 checkers, F hints, #2 anchoring: smaller, earlier PoCs (see above), usable as side sections.
**Common thread for a paper:** *LLMs fail at algorithmic tasks less for lack of reasoning than through tool/representation
mismatch. Scoped tools, code-as-policy and specific feedback fix them, while generic toolboxes or vague feedback hurt.*
Caveat: 2 models (+Llama spot checks), small n per cell (pooled CIs where given), and Qwen3 thinking budgets matter (≥20k
tokens for code+think).
### S-A3 behavioural checks on 8B code policy (03:00)
- `--no_repeat` (a repeated guess triggers a program repair): 8B code+think **20 → 23/30**. No gain without thinking (8 → 7).
  **The check gets gamed:** in all 7 remaining failures the repaired program no longer repeats, but falls back to *lexicographic
  enumeration of unplayed codes* (AAAA, AAAB, AAAC, …). It satisfies the check without fixing the broken deduction (a Goodhart
  effect on the repair signal).
- Running: `--consistent_check` (a guess the feedback rules out triggers a repair with a concrete counter-example). Offline it
  catches the enumeration fallback (stub program: solved in 8 vs 15 failed).
- **Result (03:18): the consistency check works and isn't gamed. 8B code+think 20 → 28/30, 4.6 guesses, 26 within Knuth's ≤5**
  (no_repeat alone 23/30; 32B ceiling 30/30). Consistency .46 → .81, repairs/game .57. The 2 remaining failures used up the
  2-repair budget and fell back to `AAAA`. Without thinking it barely moves (8 → 9/30): 8B's no-think programs crash or hard-code
  `AAAA` and can't be repaired into a working deduction.
- Lesson for repair design: **check the behaviour you care about** (consistency with the evidence), not a proxy (no repeats).
  A proxy check gets satisfied by the cheapest change (enumeration), while the semantic check plus a concrete counter-example
  pushes the model to fix the deduction. Same pattern as T1/CO: specific feedback (format/length, counter-example) beats vague.
## Model-scale sweep (10:10): Qwen3 1.7B / 8B / 14B / 32B-AWQ on every headline fix
| metric | 1.7B | 8B | 14B | 32B |
|---|---|---|---|---|
| **Geometry** all-variants-correct /100: base / all predicates / **task-matched** | 62 / 57 / **72** | 96 / 98 / **100** | 79 / 80 / **100** | 89 / 84 / **100** |
| **CO** solver within 1%: no doc / full sheet / **scoped snippet** | .01 / .05 / **.13** | .40 / .30 / **.71** | .64 / .79 / **1.00** | .80 / 1.00 / .98 |
| **Zebra** no think: direct / code / code+snippet | 0 / 0 / 0 | .10 / .56 / .42 | .25 / .54 / .60 | .23 / .44 / **.83** |
| **Zebra** think: direct / code / **code+snippet** (6x5 in brackets) | .58 (0) / .40 (0) / .06 (0) | .85 (5) / .44 (1) / .71 (5) | **.94 (6)** / .73 (3) / .85 (6) | .81 (2) / .58 (3) / **1.00 (8)** |
| **Mastermind** solved /30: code+repair ; code+think(+consistency check) | 0 ; 8 | 8 ; 28 | 25 ; 25 | 27 ; 30 |
- **Task-matched predicates are the best geometry arm at every size** (+10 at 1.7B, +4/+21/+11 at 8B/14B/32B over baseline). Reaching 100 needs ≥8B.
  The unscoped toolbox is ≤ baseline at 1.7B and 32B (distractor effect), roughly neutral at 8B/14B.
- **Scoped solver snippet ≥ full cheat sheet at 1.7B–14B** (14B: .79 → **1.00**). At 32B both saturate. The snippet's *relative* value peaks
  in the middle (8B/14B): too small and the model can't write the solver (1.7B .13), too big and any doc works.
- **Zebra: a capability threshold for "NL→solver with thinking"**: code+snippet+think goes .06 → .71 → .85 → **1.00**, while direct+think is
  .58 → .85 → .94 → .81 and **never solves 6x5 reliably** (0/2/6… vs code 8/8 at 32B). At 1.7B the snippet *hurts* (code .40 → .06): it pushes the
  model onto an API it can't drive (20 runtime errors, 13 context overflows).
- **14B zebra no-think + snippet = .60 with a non-monotone curve (3x3 0/8 but 6x5 8/8).** Real bug class: programs test
  `if status != cp_model.FEASIBLE: print("No solution found")`. CP-SAT returns OPTIMAL when the search completes (small puzzles), so correct
  models print "no solution", and the repair loop never fixes it because the model edits constraints, not the status check. A one-line
  doc/shim fix (`st in (OPTIMAL, FEASIBLE)`) is the obvious next arm. Another API misconception that resists repair.
- **Mastermind code policy scales smoothly** (code+repair 0 → 8 → 25 → 27; with think 8 → 28 → 25 → 30). 14B think+check (25) is not above 14B
  no-think, so thinking matters most at 8B.
- **Overall shape:** the fixes help most at mid sizes (8B–14B). The smallest model lacks the base skill, and the largest saturates or only needs them on the
  hardest cells (zebra 6x5, Mastermind ≤5). That's a clean "who benefits from tool scaffolding" curve for the paper.
- **Status-check line confirmed (10:13).** Adding one sentence to the snippet ("a solved model returns OPTIMAL; test `st in (OPTIMAL,
  FEASIBLE)`") moves zebra code+snippet, **no thinking**: **14B .60 → .96** (3x3 0/8 → 8/8) and **32B .83 → .94** (the 32B "No solution found"
  bad_outputs were the same misconception). Without thinking, 14B code+snippet+status (.96, ~2k tokens) now beats every
  direct+thinking arm (≤.94 at ~7k tokens). One API fact the model can't learn from repair feedback, stated once in the prompt, is
  worth more than thinking here.
### 14B robustness under sampling (11:35; T=0.7, 2 seeds) + status line at 8B
- **Geometry 14B: task-matched predicates 99 / 98 vs baseline 82 / 82** (greedy 100 vs 79). Robust, +16.5 pts.
- **Zebra 14B, code+snippet+status, no think, all cells: .85 / .81** (greedy .96) at ~2k tokens. On the hardest cells (5x5+6x5, 16 puzzles per seed):
  code no-think 12/16, 12/16; **direct+think 13/16, 12/16 at ~11k tokens**; code+snippet+think 12/16, 12/16 at 12–15k. **Correction:** at 14B the
  sampled advantage of code is **cost, not accuracy** (≈ same accuracy at 1/5 of the tokens). The greedy ".96 beats every think arm" was
  partly a lucky draw. At 32B the accuracy gap on 6x5 remains (8/8 code vs 2/8 direct greedy; 16/16 vs 11/16 sampled).
- **The status line doesn't help 8B** (no think .42 → .46, think .71 → .62; within noise). 8B's failures are runtime misuse (10–18) and
  thinking-budget truncation (11–16 runs hit 20k without code), not the status check. Again: the API fact matters only once
  the model can otherwise write the model (≥14B).
### PoC F hints with a 14B student (13:05): the tutor–student gap curve
pass@1 overall (and on problems the student fails alone):
| student (tutor) | L0 none | L1 | L3 | placebo | full solution (leak-adjusted) |
|---|---|---|---|---|---|
| 1.7B (32B) | .22 (.05) | .29 (.16) | **.32 (.24)** | .15 (.08) | .40 (.24) |
| 8B (32B) | .47 (.08) | .46 (.08) | .45 (.07) | .45 (.09) | .62 (.48) |
| 14B (32B) | .53 (.06) | .53 (.14) | .50 (.14) | .52 (**.16**) | .75 (**.43**) |
| 14B (8B) | .50 (.09) | .51 (.17) | .49 (.14) | .50 (**.14**) | .75 (.43) |
- **Hints help only the weakest student.** For 14B (like 8B), hint levels don't beat no-hint overall. The apparent gain on "problems failed alone"
  (.06 → .14) is fully matched by the **placebo** (.14–.16), so it's resampling/regression to the mean, not hint content. The placebo control is
  essential: without it, this would be reported as a +8–10 pt hint effect.
- Full solutions: 14B pass@1 .75, but leakage-adjusted .43 is *below* no-hint .53. Strong students copy. **The tutoring topic's main claim: hint
  usefulness decreases with student strength, gone by 8B**. The big tutor–student gap (32B→1.7B) is the only regime with real gains.
### Fifth scale point: Qwen2.5-72B-Instruct (no thinking mode; TP4 at 0.6/GPU) (13:27)
| metric | 1.7B | 8B | 14B | 32B | **72B (Qwen2.5)** |
|---|---|---|---|---|---|
| Geometry base / all predicates / task-matched | 62/57/72 | 96/98/100 | 79/80/100 | 89/84/100 | **77/79/100** |
| CO within-1% no doc / full / scoped | .01/.05/.13 | .40/.30/.71 | .64/.79/1.00 | .80/1.00/.98 | **.67/.93/.99** |
| Zebra no-think direct / code / code+snippet(+status) | 0/0/0 | .10/.56/.42 | .25/.54/.96* | .23/.44/.94* | **.04/.02/.42*** |
| Mastermind code + repair (/30) | 0 | 8 | 25 | 27 | **30 (5.5 guesses)** |
(* with the status line)
- **Task-matched predicates reach 100 at 72B too** (base 77): the geometry fix holds from 8B to 72B across two model generations.
- **CO: any doc ≈ saturates at 72B like 32B**, and the scoped snippet stays ≥ the full sheet.
- **Zebra without thinking is hard even at 72B** (direct .04). Code without the snippet fails on CP-SAT misuse (29/48 runtime errors, mostly
  `OnlyEnforceIf`/boolean use of BoundedLinearExpressions). The snippet+status lifts it to .42 but not to the Qwen3 14B/32B level (.94–.96).
  The non-reasoning Qwen2.5 generation is worse at modelling logic puzzles than the Qwen3 hybrid-reasoning models even with thinking off.
  Scale alone doesn't buy NL→solver competence.
- Mastermind code policy: 30/30 at 72B. Writing a deduction program is easy for large models; deducing in-context is not.
### CO scoped snippet under sampling (13:52; T=0.7, 3 seeds, 84 instances, paired cluster bootstrap)
| within 1% of optimum | no doc | full cheat sheet | **scoped snippet** | scoped − full | scoped − none |
|---|---|---|---|---|---|
| 8B | .29 (.27/.26/.32) | .33 (.31/.35/.33) | **.71** (.71/.71/.70) | **+.38 [+.28, +.48]** | +.43 [+.33, +.51] |
| 14B | .62 (.61/.57/.67) | .80 (.85/.76/.80) | **.97** (.99/.98/.95) | **+.17 [+.11, +.23]** | +.36 [+.28, +.43] |
- **The CO headline is robust:** the scoped snippet beats the full cheat sheet at both sizes with CIs far from 0, and is remarkably stable across seeds
  (8B .70–.71). The full sheet barely helps 8B (+.04, CI spans 0) but does help 14B (+.19). The *scoping* adds +.38/+.17 on top.
### Mastermind headline replicates (14:32; same 30 secrets, 3 sampling-seed sets)
| config | rep0 | rep1 | rep2 | mean solved | guesses when solved |
|---|---|---|---|---|---|
| **32B code + think** | 30 | 30 | 28 | **29.3/30** | 4.5–4.7 (27–29 games ≤5) |
| **8B code + think + consistency check** | 28 | 27 | 26 | **27.0/30** | 4.6 |
| 32B code + repair, no think | 27 | 20 | 24 | 23.7/30 | 4.8–5.4 |
| (reference: 32B direct + think + state, single run) | 15 | – | – | 15/30 | 8.3 |
- Both thinking headlines replicate tightly (±1–2 games). The no-think code number is noisier (20–27). Quote 23.7 ± 3.5, not 27.
- With this, **every headline result in the project has a sampled replicate or CI**: geometry (seeds + CI), zebra (2 seeds), CO (3 seeds + CI),
  Mastermind (3 replicates), hints (placebo-controlled).
### Running (14:40): S4d toolbox dose-response (why do unscoped tools hurt?)
poc/geo_distractors.py + run_geo_cross.py `--distract K --distract_kind related|unrelated`. Every prompt gets the task-matched
helpers plus K extra *correct* helpers (dependencies auto-included, order shuffled, never one that solves the task outright). K = 0, 2, 4, 8
geometry helpers (orient, on_segment, segments_intersect, point_in_polygon, dist2, bbox, collinear, polar_sort, is_convex, polygon_area2,
convex_hull, closest_pair_sq) vs a control of 8 *unrelated* helpers (gcd, is_prime, fib, reverse_words, lower_bound, lcs_len). Distractor
helpers were unit-tested. 8B / 14B / 32B, T=0.7, 2 seeds. Rows record which distractors the program calls.
Hypothesis: harm grows with K for *related* helpers (temptation to misuse) but not for unrelated ones (prompt length alone).
### S4d toolbox dose-response: results (14:55)
All-variants-correct /100, mean of 2 seeds (T=0.7); "used" = share of programs calling ≥1 distractor (comments stripped).
| model | K=0 | K=2 related | K=4 related | K=8 related | 6 unrelated (control) |
|---|---|---|---|---|---|
| 8B | 98.0 | 87.0 (used .59) | 81.0 (.69) | **74.5** (.81) | 91.0 (.01) |
| 14B | 84.5 | 83.0 (.48) | 73.5 (.46) | 75.0 (.48) | 77.5 (.00) |
| 32B | 95.5 | 83.5 (.36) | 76.0 (.39) | **75.5** (.55) | 91.0 (.00) |
- **Monotone dose-response for related helpers:** each pair of extra correct geometry helpers costs ~5–12 pts, −23.5 (8B) / −20 (32B) / −9.5 (14B) at K=8.
  Seeds agree within ±3.
- **It's relevance, not length:** 6 unrelated helpers (gcd, fib, …; the whole pool, ≈ same prompt length as K=4–6) cost only −7 / −7 / −4.5 and are almost
  never called (≤.01). Related ones are called by 36–81% of programs.
- **Mechanism, the hull collapse again:** at K=8, hull drops to 2/20 (8B) and 4/20 (32B). Programs build Graham-scan variants around `polar_sort` / `collinear`
  / `on_segment` and get the collinear/duplicate cases wrong. 85% (8B) / 71% (32B) of failing programs call a distractor (though so do many passing ones,
  so a call is necessary-ish, not sufficient).
- Caveat on 14B: its K=0 here (84.5) is below the earlier task-matched arm (98.5). The only differences are the toolbox header wording ("helper functions;
  copy the ones you use" vs "exact integer predicates; copy them unchanged") and shuffled order. 11/20 segs programs call `segments_intersect` with 8
  scalars instead of 4 points. So **14B is wording-sensitive in interface use**. 8B/32B K=0 match their earlier arms (98 vs 96–97; 95.5 vs 96.7).
  Within-experiment comparisons are unaffected.
- **For the geometry paper:** a clean causal story. Irrelevant-but-plausible tools hurt in proportion to their number, because models use them. Equally long
  irrelevant text doesn't. Scope the toolbox to the task.
### S4d mitigation by wording (15:05): "use only if needed" doesn't undo the harm
| model | K=0 should / may | K=8 related, should | K=8 related, **may ("most are NOT needed")** |
|---|---|---|---|
| 8B | 98.0 / 96.5 | 74.5 (used .81) | 71.5 (used **.29**) |
| 14B | 84.5 / 86.5 | 75.0 (.48) | 79.5 (.30) |
| 32B | 95.5 / 93.5 | 75.5 (.55) | 80.5 (.35) |
- The cautious header cuts distractor *use* by 40–65%, but accuracy barely recovers (8B −3, 14B +4.5, 32B +5 vs "should"; still 15–24 pts below K=0).
  **Harm without use:** in 8B "may", 22/33 failures call no distractor. Those programs still add a spurious "remove collinear points from the hull" pass
  and similar degenerate-case code. **Related helpers prime degenerate-case over-engineering even when not called.** This is the same failure as the T3
  "be robust" hint, which hurt for the same reason.
- 14B's wording sensitivity at K=0 isn't explained by "should" vs "may" (84.5 vs 86.5). It's the header/interface framing vs the original
  "predicates" block (98.5); not pursued further.
- **Practical conclusion: you can't instruct the harm away. Remove irrelevant tools** (the task-matched arm), which is what the dose-response predicts.
### Distractor effect generalises to NL→solver (15:31): zebra code+snippet+status, no think, + K unneeded CP-SAT API lines (T=0.7, 2 seeds)
| model | K=0 | K=4 | K=8 | programs using any extra API |
|---|---|---|---|---|
| 32B | **.93** (.94/.92) | .90 (.85/.94) | **.74** (.71/.77) | .01 / .03 / .04 |
| 14B | .81 (.81/.81) | .81 | .78 (.79/.77) | .00 / .01 / .02 |
- **32B loses 19 pts with 8 unneeded API lines, while almost never calling them (4%).** It's the same harm-without-use as geometry under the "may"
  header. Failure mix at K=8: ok-but-wrong grids 2 → 12 (cell acc .44, i.e. mis-modelled clues), plus `AddAbsEquality` arity errors 1 → 4 (the extra
  `AddMaxEquality/AddMinEquality` lines seem to blur the `AddAbsEquality(target, expr)` signature). The errors concentrate on large puzzles (5x4–6x5).
- 14B is barely affected (−3), the same model-dependence as geometry, where 14B's dose-response was the flattest.
- **The theme now holds across two topics:** irrelevant-but-plausible tool documentation degrades LLM-written programs (geometry helpers; solver API lines),
  mostly *without being used*. Scoping is the remedy, and auto-scoping is being tested now.
### S5 auto-scope (15:45): the model picks its own helpers from the K=8 pool (catalog of one-line docs → only the chosen ones in full)
| model | all 8 given (dis8) | **auto-scope** | oracle task-matched (dis0) | gap closed | picks/program | precision / recall vs needed |
|---|---|---|---|---|---|---|
| 8B | 74.5 | **80.0** (80/80) | 98.0 | 23% | 1.1 | .57 / .44 |
| 14B | 75.0 | **83.5** (87/80) | 84.5 | 89% | 2.6 | .42 / .88 |
| 32B | 75.5 | **85.0** (84/86) | 95.5 | 48% | 1.1 | .60 / .55 |
- **A deployable but partial solution:** self-scoping recovers +5.5 / +8.5 / +9.5 pts with no oracle. Selection is the bottleneck. 8B and 32B pick ~1 helper
  and miss needed ones (recall .44–.55), while 14B over-picks (2.6, precision .42). Next: retrieval-style scoping (embed task ↔ helper docs) or
  "pick then verify"; a better selector should close the remaining gap.

### Related-work check for the toolbox/distractor theme (15:45)
- **Irrelevant context hurts reasoning:** GSM-IC (Shi et al. 2023); arXiv 2505.18761 (EMNLP'25): accuracy falls ~power-law with distractor count (math word problems).
- **Too many tools in agents (function-calling):** RAG-MCP (retrieve tools before the LLM sees the catalog); ToolRet (2503.01763, tool-retrieval benchmark);
  "How Many Tools Should an LLM Agent See?" (Meta, 2605.24660: adaptive short lists beat fixed K=5, 93.1% vs 87.1%); ToolChoiceConfusion/CMTF (2606.06284:
  expose a minimal causal tool frontier, ~1 tool/step, ~90% fewer tokens); "tool-use tax" (2605.00136: tools don't beat CoT under semantic distractors);
  tool-irrelevance bias (2604.11322: ~20% spurious invocation when all tools are irrelevant); canary tools (2608.04719).
- **Docs for code generation:** Jain et al. 2024 (2407.09726): documentation augmentation helps rare APIs (+9 pts) but irrelevant retrieved docs cut
  frequent-API accuracy by 39 pts; fix = retrieve only when needed.
- **Logic puzzles:** ZebraLogic (Lin et al., ICML'25): "curse of complexity", accuracy collapses beyond ~10^7 search space even for large/reasoning models;
  they try Best-of-N/backtracking/self-verification, *not* solver code with an API fix. Logic-LM / SatLM / LINC use solvers but don't study API misuse.
- **Geometry code robustness:** general studies (e.g. 2503.20197: >90% of LLM-code robustness gaps are missing condition checks; 3D-geometry coding
  benchmark 2603.30038). Nothing found on computational-geometry degeneracies × supplied predicates.
- **What looks new in ours (not exhaustive):** (1) *code-level* tools (helper functions copied into LLM-written programs), not function-calling;
  (2) **harm without invocation**: related helpers prime degenerate-case over-engineering, and "not needed" instructions cut use but not harm; prior agent work
  measures wrong selection/spurious calls; (3) a controlled dose-response with a length-matched unrelated control; (4) the same effect in two domains
  (geometry predicates, solver-API docs); (5) the API-misuse confound that makes solvers look worse than thinking on ZebraLogic-style puzzles.
### S5b/S5c better self-scoping? No (15:46). Precision, not recall, is the bottleneck
| model | pick list | pointwise yes/no | plan-first | (all 8 given / no helpers sampled / oracle) |
|---|---|---|---|---|
| 8B | 80.0 (prec .57, rec .44) | 82.0 (.37/.39) | 78.5 (.54/**.78**) | 74.5 / 88.7 / 98.0 |
| 14B | 83.5 (.42/.88) | 74.5 (.50/.63) | 79.5 (.52/.85) | 75.0 / 82.0 / 84.5 |
| 32B | 85.0 (.60/.55) | 79.5 (.48/.45) | 73.0 (.52/.74) | 75.5 / 84.3 / 95.5 |
- Plan-first raises *recall* of needed helpers (.74–.85) but accuracy falls (32B 85 → 73), because it also pulls in more plausible extras.
- **Pooled over all self-scoping runs: when the model's pick contains no unneeded helper, accuracy ≈ oracle (8B .90, 32B .93, 14B .81); when it contains ≥1,
  accuracy drops to .68 / .60 / .78.** The dose-response again: each admitted distractor costs, and precision (not recall) decides success.
- Honest bottom line: LLM self-scoping ≈ giving no helpers at all (80–85 vs 82–89). Helpers pay off only when correctly scoped.
  A deployable fix must be precision-oriented. Testing next, offline and label-free: **select among candidate programs (no helpers / self-scoped
  variants / all helpers) by metamorphic consistency on the given instance** (poc/mr_select.py; programs already stored, CPU only).
### S6 label-free selection by metamorphic consistency (16:00, offline CPU, stored programs): **a deployable fix that needs no tools**
mr_select.py: run each candidate program on the metamorphic copies of the given instance (translate/rot90/mirror/permute/scale/1e9). Keep
the consistent ones, majority-vote the identity output, pick a program with that output. Scored on all 8 variants incl. degenerate (unseen by the check).
| model | best single arm | MR-select over {no helpers, 3 self-scoped, all 8} | **MR-select over 3 samples with NO helpers** | oracle-any | task-matched oracle |
|---|---|---|---|---|---|
| 8B | 89 / 85 | 95 / 91 | **98** (singles 89/85/92) | 97–100 | 96–98 |
| 14B | 87 / 82 | 93 / 89 | 88 (2 samples; 9 with no consistent candidate) | 91–99 | 98.5* |
| 32B | 92 / 86 | 92 / 86 | **97** (singles 92/81/80) | 98–99 | 96.7 |
- **Key control:** the gain comes from *sampling several programs and filtering by metamorphic consistency*, not from tools. Three tool-free samples +
  MR-vote reach 97–98, matching the oracle task-matched predicates, with no oracle and no labels (cost: 3 generations + 21 executions).
- **Caveat: consistent ≠ correct.** With 2 candidates the tie-break order matters (base-first 94–96 vs self-scoped-first 87–88), because some
  wrong programs are perfectly invariant (degenerate-case bugs the MR check can't see; same limit as S1). More samples help (3 > 2).
- **Revised geometry solution menu:** (a) task known → give exactly the needed exact predicates (96–100); (b) task unknown/no oracle → sample k≈3 programs,
  filter by metamorphic consistency, vote (97–98 at 8B/32B). (c) Don't hand over a broad toolbox, and don't rely on the model to scope it (≈ no helpers).
(*14B oracle = original predicate-header arm; its toolbox-header K=0 was 84.5.)
### S6 k-curve + ablation (16:40): sample k tool-free programs → metamorphic filter → vote
All-variants-correct /100 (seed-1 instance set). Single-sample mean in brackets.
| model | singles (mean) | k=1 | k=2 | **k=3** | k=4 | k=5 | plain vote, no MR filter (k=3 / k=5) |
|---|---|---|---|---|---|---|---|
| 1.7B | 65/59/57/56/60 (59) | 65 | 72 | 73 | 72 | 72 | 70 / 71 |
| 8B | 89/85/92/92/87 (89) | 89 | 95 | **98** | 99 | 99 | 94 / 94 |
| 14B | 82/82/84/81/81 (82) | 82 | 88 | 89 | 92 | 92 | 89 / 92 |
| 32B | 92/81/80/82/80 (83) | 92 | 94 | **97** | 98 | 98 | 96 / 96 |
- **k=3 captures most of the gain** (8B +9 over the mean single program, 32B +14, 14B +7, 1.7B +14); k=4–5 adds ≤3.
- **The metamorphic filter adds over plain self-consistency voting** at 8B (98/99 vs 94) and 32B (97/98 vs 96), ties at 14B, and helps a little at 1.7B
  (73 vs 70). Filtering out programs that break under translation/rotation/1e9 removes the "consistently wrong under perturbation" class that
  voting on one input can't see.
- 8B and 32B reach 98–99 with no tools, labels or hand-picking, i.e. the hand-picked task-matched predicates (96–100) at k=3–4 generations.
### S6 for CO: best-of-3 with label-free verification (feasible + best objective), offline over the 3 sampled seeds (16:42)
| within 1% | no doc: single → best-of-3 | full sheet: single → best-of-3 | scoped snippet: single → best-of-3 |
|---|---|---|---|
| 8B | .29 → **.43** | .33 → .39 | .71 → .71 |
| 14B | .62 → **.87** | .80 → **.99** | .97 → 1.00 |
- Sampling + verify helps a lot at 14B (full sheet + best-of-3 = .99 ≈ scoped snippet) but **can't replace the snippet at 8B** (.43 vs .71): when every
  sample misuses the API the same way (8B TSP 0/24 in all seeds), there's nothing to select. Verification needs *diversity of correct attempts*.
### S6 for zebra: verified best-of-k without the snippet (17:41); clue-satisfaction is an exact label-free check (unique solutions)
| model (code, no think, no snippet) | singles | best-of-k, k=1..5 | 5x5+6x5 solved at k=5 | vs code+snippet+status (single sample) |
|---|---|---|---|---|
| 8B | .38–.52 | .38 .56 .60 .65 **.69** | 1/16 | .46 (greedy; 8B can't use the snippet) |
| 14B | .50–.54 | .50 .62 .67 .71 **.71** | 3/16 | **.81–.96** |
| 32B | .40–.48 | .44 .54 .60 .65 **.65** | 2/16 | **.93** (sampled) |
- **Sampling + exact verification can't replace the API snippet at 14B/32B:** 5 samples reach .65–.71 vs .81–.96 from one sample with the snippet, and the
  large puzzles stay unsolved (2–3/16 vs 12–16/16). All samples share the same API misconceptions (status check, expression misuse), so there's little
  diversity to select from. Same limit as CO at 8B.
- **At 8B, sampling beats the snippet** (.69 vs .46): 8B can't drive CP-SAT anyway, and its brute-force programs vary enough for selection to help on small puzzles.
- **Solution menu, refined across topics:** sample-and-verify works when attempts fail *independently* (geometry degeneracy bugs, 14B CO). Stated
  facts (scoped snippet / status line) are needed when failures are *systematic* (shared API misconceptions). The two are complementary, not substitutes.
### Complementarity confirmed (18:19): snippet+status AND verified sampling on zebra (no think)
| model | snippet, single samples | **snippet + best-of-k (k=1..5)** | 5x5+6x5 at k=5 | (no snippet, best-of-5) |
|---|---|---|---|---|
| 8B | .38–.46 | .46 .67 .75 .77 **.81** | 10/16 | .69 (1/16) |
| 14B | .81–.88 | .85 .98 **1.00** 1.00 1.00 | **16/16** | .71 (3/16) |
| 32B | .85–.94 | .94 .98 **1.00** 1.00 1.00 | **16/16** | .65 (2/16) |
- **The two fixes stack: 14B and 32B solve every puzzle (48/48, incl. all 6x5) at k=3, without thinking**, at ~2k tokens per sample. Compare direct+thinking
  .75–.81 at ~11k tokens. The snippet removes the *shared* misconceptions, and the leftover failures are independent, so verified sampling clears them.
  Even 8B gets to .81 (10/16 on the largest).
- **Unified recipe across topics:** (1) state the facts the model systematically gets wrong (scoped tools / API snippet / status line), with no irrelevant
  extras; (2) sample a few programs and keep the one that passes a label-free check (metamorphic consistency in geometry, clue satisfaction in zebra,
  feasibility + objective in CO). Geometry k=3: 97–98; zebra k=3: 1.00; CO 14B: .99–1.00.
### Cross-family check of verified sampling: Llama-3.1-8B geometry, tool-free, T=0.7 (18:40)
- Single samples are much worse than greedy for Llama: 53/51/57/48/46 (mean 51; 22–29 crashes per 100) vs greedy 82.
- MR-select over k samples: k=1 53, k=2 69, **k=3 74**, k=5 77. Plain vote k=3: 63. **The metamorphic filter adds +11 over plain voting**, and k=3 adds +23 over the
  mean single sample, but it **doesn't reach Llama's own greedy (82) or task-matched predicates (94).**
- So the sampling half of the recipe transfers in *relative* terms (big gains over single samples, filter > vote), but its absolute value depends on the
  sampler: at T=0.7 Llama's samples are too degraded. Qwen3 tolerates T=0.7 (singles 82–89). A lower temperature (or greedy + a few samples) would be the
  fair Llama setting; not run. For a model-agnostic recipe, prefer **scoped tools first** (Llama 94) and treat sampling as the add-on.
- **Llama at T=0.3 (19:34):** singles 73/66/75/71/69 (mean 71; still 13–21 crashes). MR-select k=1 73, k=2 77, **k=3 81**, k=5 83; plain vote k=3 81.
  Lower temperature helps (k=3: 74 → 81), but verified sampling only *matches* Llama's greedy single program (82). The MR filter adds nothing over voting at
  T=0.3. **For Llama, verified sampling doesn't beat greedy; scoped tools do (94).** The sampling fix is model-dependent (strong for Qwen3, where single
  samples are already good and failures independent; weak for Llama, whose crashes are frequent and correlated). **Final recipe ordering: scoped tools first,
  then verified sampling where samples are good.**
- **Llama T=0.3 (19:36), the fair setting:** singles 73/66/75/71/69 (mean 71; still 13–21 crashes per 100). MR-select k=1 73, k=2 77, k=3 81, **k=5 83**;
  plain vote identical (73/76/81/83). Sampling at a sane temperature roughly **matches Llama's greedy (82)**, but the metamorphic filter adds nothing over voting
  here, and it stays well below task-matched predicates (94). Llama's failures are crashes/format bugs shared across samples (systematic), not independent
  degeneracy bugs, so the "facts first, then sample" ordering of the recipe matters most for Llama. **Cross-family conclusion: scoped tools transfer (82 → 94);
  verified sampling transfers only weakly.**
### ⚠️ Ops incident (20:31): vLLM port clash between two Claude sessions working in this repo
- Session sj-c4 (queue_heldout.sh) and session sj-f2 (queue_llamastd.sh, Llama-3.1-8B + `--stdlib`) both started vLLM on **port 8088**. Both binds succeeded
  and start_server.sh's /health check passed against the other server, so **from ~20:30:26 to ~20:31:40 requests to :8088 were split between Llama-3.1-8B and
  Qwen3-8B.** Contaminated: the first held-out 8B outputs (moved to results/contaminated_port8088/) and **geoxllama8b_std* (99/100 and 86–94 look
  Qwen-like; must be re-run on a free port before use)**. sj-f2 was notified. sj-c4 now uses ports 8100+. Lesson: check the port is *unanswered* before
  starting (`ss` isn't installed here, so ss-based guards silently pass).
### Running (20:37): HELD-OUT geometry tasks (designed after all findings): convex (yes/no, collinear vertices allowed) and tri (points strictly inside a triangle)
run_geo.py tasks `convex`, `tri` (exact oracles; all 7 metamorphic variants preserve the answer, verified; degen = doubled coords + collinear vertex / point
on an edge + duplicate). Arms: no helpers (3 seeds → MR-select), task-matched (orient), all 4 original predicates, K=8 related distractors. 8B/14B/32B,
T=0.7, n=80 programs per run, `--stdlib` (models otherwise import shapely, which isn't installed; the environment fact is stated for every arm).
Question: do "scoped tools > all tools", the distractor harm, and verified sampling hold on tasks we didn't tune on?
### ⚠️ Port clash (20:30): Llama stdlib run contaminated, re-running
- Llama crash diagnosis (valid, CPU re-execution of stored programs): **all 29 crashes in the Llama T=0.3 runs are `import shapely`** (not installed in the sandbox;
  the prompt never said which libraries exist). Third-party imports across all stored geometry programs: Qwen3 1.3% (146/11,100), Qwen2.5-72B 6.7%, Llama 15%.
  The earlier Llama numbers were partly a harness/prompt artifact. run_geo_cross.py `--stdlib` now states "only the Python standard library is available".
- The first `--stdlib` run (queue_llamastd.sh, port 8088) is **INVALID**: a peer session's Qwen3-8B server bound the same port 20:30:26–20:31:40 (vLLM uses
  SO_REUSEPORT, so both binds succeed, and start_server.sh's health check passes against the other server), splitting requests between Llama and Qwen.
  Its numbers (99/100 greedy, 86–94 sampled) are discarded. Re-run: queue_llamastd2.sh, port 8091, port-free check + /v1/models identity check. Port
  convention agreed: this session 8040–8099, peer session (sj-c4) 8100+. Only overlap found in gpu_choice.log today: 8088 at 20:30.
- TODO: add a port-in-use guard to the shared poc/start_server.sh, once no start_server.sh is executing (the peer's is running now).
- **Caveat on the Llama verified-sampling entries (18:40, 19:34; sj-c4):** session sj-f2 found that Llama's sampled-run crashes were `import shapely`
  (not installed), an environment artifact. The conclusion "verified sampling doesn't beat greedy for Llama" is therefore **provisional**, pending sj-f2's
  clean `--stdlib` rerun (queue_llamastd2.sh, port 8091). Port split agreed: sj-f2 8040–8099, sj-c4 8100+.
### HELD-OUT geometry tasks (convex, tri): results (20:50). Correct on all 8 variants, % of 80 programs (mean over seeds)
| model | no helpers (3 seeds) | orient only (our pre-set "needed") | all 4 original predicates | +8 related distractors | **MR-select k=3** (plain vote) |
|---|---|---|---|---|---|
| 8B | 47% | 48% | **60%** | 39% | **56%** (48%) |
| 14B | 77% | 81% | **89%** | **27%** | **86%** (86%) |
| 32B | 77.5% | 64% | **92.5%** | 71% | **92.5%** (90%) |
- **Replicates:** (1) **distractor harm** (+8 related helpers: −8 / **−50** / −6.5 pts vs no helpers). 14B collapses because programs *call toolbox helpers
  without copying their definitions* (NameError: orient/collinear, 21–22/40 convex programs) and mishandle tri's edge points (degen_only 22–24/40).
  (2) **Verified sampling**: MR-select k=3 adds +9 / +9 / +15 pts over the mean single program, and the metamorphic filter beats plain voting at 8B (+8) and 32B (+2.5).
- **Doesn't replicate as pre-specified, and that's informative:** our pre-set "needed" helper for both tasks was the low-level `orient` (the solving
  helpers is_convex / point_in_polygon were deliberately withheld). Orient alone gives ~0 gain, and *hurts* 32B on tri (64%: programs assume a CCW triangle,
  `o1>0 and o2>0 and o3>0`, and fail the mirror variant, 12–13 transform_only). The **4-predicate block helps a lot** (tri: 32B 40/40, 14B 37/40) because it
  contains point_in_polygon, which encapsulates exactly the hard part (exact boundary handling). Reconciles with the original tasks, where the task-matched
  set for pip/segs *also* contained the encapsulating predicate.
- **Refined claim:** the helpful tool is the one that **encapsulates the task's degenerate-case logic**. A low-level primitive alone doesn't help and
  can mislead (sign conventions). Unrelated or merely related helpers hurt. "Scope" = supply the encapsulating predicate, not just related primitives.
### ✅ Clean Llama re-run with the environment fact (20:45; port 8091, model identity verified): SUPERSEDES the 18:40 / 19:34 Llama entries (sj-c4) and the contaminated 8088 run
| Llama-3.1-8B geometry (/100 all-variants-correct) | no "stdlib" line | **"only the standard library is available"** |
|---|---|---|
| greedy, no helpers | 83 (14 crashes = `import shapely`) | **99** (0 crashes) |
| greedy, task-matched predicates | 94 | 80 (hull: 17 crashes = gift-wrapping loops that time out) |
| T=0.3 samples, 5 seeds | 66–75 (13–21 crashes) | 89–94 (0–1 crashes) |
| MR-select k=3 / k=5 (plain vote) | 81 / 83 (81 / 83) | **96 / 98** (95 / 97) |
- **Llama's geometry "weakness" was an environment mismatch:** it reaches for `shapely`, which the sandbox lacks. Stating the one environment fact takes greedy from 83 to
  **99**, and verified sampling then works as for Qwen (k=5: 98). The contaminated 8088 run happened to give almost the same numbers (99 / 86–94).
- **Correction to the cross-family conclusion:** the task-matched predicates' earlier Llama gain (82 → 94) mostly came from *displacing shapely*, not from exactness. With
  the stdlib fact, adding `orient` actually *hurts* Llama's hull (99 → 80): it abandons the familiar monotone chain for a hand-rolled gift-wrapping loop
  that hangs. Same "off-idiom" mechanism as the 1e9 / robustness-hint effects.
- **The recipe, sharpened:** (1) state the facts the model gets wrong (environment: available libraries; API contracts: status, callbacks), and keep the tool
  surface minimal. Helpers are a means, not the goal, and can push a model off its idiom. (2) Then verified sampling. sj-c4's "verified sampling doesn't beat greedy
  for Llama" was an artifact of the shapely crashes.
- Harness note: all earlier geometry runs lacked the stdlib line (third-party imports: Qwen3 1.3%, Qwen2.5-72B 6.7%, Llama 15%). Qwen3 conclusions are barely
  affected. Use `--stdlib` in any final experiments.
### ⚠️ Confound audit (21:00): non-stdlib imports in "no helpers" geometry baselines (prompted by sj-f2's Llama/shapely finding)
Programs importing shapely/numpy/scipy/sympy all fail (not installed). Count per 100 baseline programs: **14B 13–20 (greedy 20), 72B 20**, 8B 3–5, 32B 0–3,
1.7B 0–3, Llama 11–24. Arms *with* a helper block contain zero such imports, and so do the dis*/disU* distractor runs.
- **Consequence:** the "task-matched predicates vs no helpers" gain is inflated by displacing shapely, heavily at 14B (79 → 100 greedy) and 72B (77 → 100),
  slightly at 8B. 32B's gain (89 → 100; pip/segs logic bugs) is mostly real. The distractor dose-response (all arms have a toolbox) and the held-out runs
  (--stdlib everywhere) are unaffected. The MR-select k-curves partly benefit from filtering crashed shapely programs.
- Re-measuring now with `--stdlib` on both base and task-matched (queue_qstd.sh: 8B/14B/32B, greedy + 3 seeds). The size-sweep geometry row and the
  "+7 to +17 pts" headline must be replaced by the stdlib numbers.
- **Correction (21:00) to "Qwen3 barely affected":** the pooled 1.3% hid the arms that matter. Verified (with sj-c4's audit) on the *no-helper* baselines, unavailable-library
  imports are: 14B greedy **20/100** (sampled s1 14), 72B **20/100**, 8B 0–5, 32B 0, 1.7B 0; task-matched arms 0. So the task-matched-predicate gain is partly
  *displacement of shapely* at 14B (79 → 100) and 72B (77 → 100), slightly at 8B, and essentially real at 32B/1.7B. The distractor dose-response is unaffected (every
  arm there has a toolbox, with 0 shapely imports). The 14B MR k-curve (base samples) is also affected. sj-c4 is re-measuring 8B/14B/32B with `--stdlib` (base + task-matched,
  greedy + 3 seeds); 72B needs all 4 GPUs, so it will be re-run when they're free.
### Corrected geometry headline with the stdlib environment fact (21:00): **supersedes the "+7 to +17 pts" claim and the size-sweep geometry row**
All-variants-correct /100; both arms `--stdlib` (zero non-stdlib imports in every run). Sampled = T=0.7, 3 seeds, paired cluster bootstrap.
| model | greedy: base → task-matched | sampled: base → task-matched | **gain (95% CI)** | where the gain comes from |
|---|---|---|---|---|
| 8B | 96 → 95 | 92.0 → 96.3 | **+4.3 [+2.0, +7.0]** | pip 85 → 100, area2 75 → 82 |
| 14B | **100** → 100 (was 79 without stdlib) | 94.3 → 97.3 | +3.0 [−0.3, +6.3] | segs 82 → 100 |
| 32B | 91 → 99 | 86.3 → 95.3 | **+9.0 [+4.0, +14.7]** | pip 68 → 100, segs 80 → 98 |
- **Honest correction:** most of the 14B (and 72B) "predicate gain" was displacing shapely. With the environment fact stated, 14B needs no help (greedy 100).
  The real effect of supplying the encapsulating predicates is **smaller but significant at 8B and 32B (+4 / +9)**, concentrated exactly on the tasks whose
  predicate encapsulates the degenerate logic (pip, segs). At hull/close (no encapsulating predicate given) it's neutral or slightly negative (32B hull 95 → 92).
- **Unaffected:** the distractor dose-response, the "may" header, auto-scope, the held-out runs (all toolbox or --stdlib arms). **Updated recipe step 0: state
  the environment** (available libraries). That one sentence alone moved 14B 79 → 100 and Llama 83 → 99, the largest single effect in the geometry topic.
- MR k-curve on these stdlib seeds: session sj-f2 is running it (geox{m}_stdbase_t07s1–3).
- **MR k-curve on the stdlib seeds (21:05):** all-variants-correct /100 for tool-free samples, metamorphic filter + vote vs plain vote. The task-matched single-sample mean is for comparison.
  | model | stdbase singles (mean) | k=2 MR / vote | **k=3 MR / vote** | task-matched singles (mean) |
  |---|---|---|---|---|
  | 8B | 94/89/93 (92.0) | 99 / 94 | **100** / 95 | 95/97/97 (96.3) |
  | 14B | 93/98/92 (94.3) | 94 / 93 | **95** / 95 | 99/96/97 (97.3) |
  | 32B | 89/85/85 (86.3) | 90 / 89 | **94** / 94 | 95/96/95 (95.3) |
  - **Tool-free verified sampling at k=3 ≈ one task-matched sample** (8B 100 vs 96.3; 14B 95 vs 97.3; 32B 94 vs 95.3). The two are interchangeable fixes on top of the
    environment fact. Sampling needs no knowledge of which predicate encapsulates the degeneracy, but costs 3 generations + 21 executions.
  - The metamorphic filter beats plain voting only at 8B (+5 at k=3). At 14B/32B with stdlib the two tie: once the shapely crashes are gone, the remaining errors
    are mostly invariant-but-wrong degeneracy bugs the filter can't see. The earlier pre-stdlib "filter > vote" gaps (8B 98 vs 94, Llama +11) were partly driven by crash/env
    errors. Revised claim: **sampling + vote is the robust part; the MR filter adds a little, sometimes.**
- **Environment audit of the other topics (21:30):** sandbox has numpy/networkx/sympy/OR-Tools, lacks shapely/python-constraint/z3/pulp. Zebra programs importing a missing
  library: 8/3076 (constraint 5, z3 3; the zebra prompt already names "standard library or OR-Tools"). Mastermind 0/621, CO 0/3342. Only the geometry results were
  affected (shapely); zebra/CO/Mastermind conclusions stand.
- **72B --stdlib attempt via pipeline parallelism is INVALID (23:40).** To avoid waiting on a foreign 42 GB job on GPU 2, Qwen2.5-72B was served PP=3 over GPUs 0/1/3
  (TP3 impossible, 64 heads). Output quality collapsed: 21/100 and 24/100 with 56–63 crashes, mostly SyntaxError/IndentationError/unterminated strings. The same
  model under TP4 earlier scored 77 / 100 (base / task-matched). That's a serving artifact (PP=3 uneven split in this vLLM build), not a model result. Files renamed
  `*_pp3_INVALID`. TP4 waiter re-armed (queue_72b_std.sh); the 72B stdlib number stays open until GPU 2 is free.
## FINAL geometry table (07:00): n = 300 programs per run (30 instances × 2 sizes × 5 tasks), all arms `--stdlib`, T=0.7 unless greedy
| model | greedy base → task-matched | sampled base (3 seeds) | sampled task-matched | **task-matched − base (95% CI)** | **K=8 distractors − task-matched** | **MR-select k=3** / plain vote k=3 |
|---|---|---|---|---|---|---|
| 8B | 97.3 → 97.3 | 92.7 / 90.0 / 92.7 | 95.0 | +2.3 [−0.3, +5.0] | **−17.7 [−23.0, −12.7]** | **98.7** / 94.7 |
| 14B | 100 → 100 | 96.0 / 96.3 / 96.3 | 97.0 | +1.0 [−2.0, +3.7] | **−29.0 [−34.3, −23.7]** | **97.7** / 97.3 |
| 32B | 88.7 → 97.0 | 84.3 / 84.3 / 84.7 | 93.3 | **+9.0 [+4.3, +13.7]** | **−17.0 [−22.7, −11.7]** | **94.3** / 92.7 |
- **Final geometry claims (powered, clean environment):**
  1. **Environment fact first:** with the available libraries stated, the no-helper baseline is already 97–100 greedy at 8B/14B (Llama 99).
  2. **Task-matched (encapsulating) predicates help where the model's own degeneracy handling is weak:** significant at 32B (+9.0); not significant at 8B/14B, which are near ceiling.
  3. **Irrelevant-but-plausible helpers hurt a lot and robustly: −17 to −29 pts at every size** (largest at 14B). This is the cleanest, biggest effect in the topic.
  4. **Verified sampling (k=3, metamorphic filter + vote) recovers or beats task-matched without knowing the task:** 98.7 / 97.7 / 94.3 vs one task-matched sample
     95.0 / 97.0 / 93.3. The filter beats plain voting at 8B (+4.0) and 32B (+1.6), and ties at 14B.
## FINAL zebra table (09:16): 144 puzzles (24 per cell, 3x3…6x5), T=0.7, no think unless noted; best-of-k uses the exact label-free clue check
| model | code+snippet+status: singles | **best-of-k (k=1,2,3)** | 5x5+6x5 solved at k=3 | code, no snippet: best-of-3 (big) | **direct + think** (big; tokens) |
|---|---|---|---|---|---|
| 8B | .40 / .34 / .38 | .40 .55 .65 | 26/48 | .58 (2/48) | **.89** (33/48; 7.0k) |
| 14B | .83 / .88 / .84 | .83 .97 **1.00** | **48/48** | .67 (3/48) | .92 (36/48; 6.2k) |
| 32B | .92 / .85 / .85 | .92 .99 **1.00** | **48/48** | .60 (6/48) | .90 (38/48; 6.7k) |
- **Final zebra claims (powered):** (1) at 14B/32B, *stated API facts + verified sampling* solves **all 144 puzzles at k=3 without thinking** (~2k tokens/sample;
  ~6k total), beating direct+thinking (.90–.92, which misses 10–12 of the 48 largest puzzles). (2) Without the snippet, sampling plateaus at .60–.67 and the large
  puzzles stay unsolved: the two fixes are complementary. (3) **At 8B the recipe loses to thinking** (.65 vs .89): 8B can't reliably drive CP-SAT even with the
  snippet, so the NL→solver route needs ≥14B.
## FINAL CO table (10:33): 252 instances (knapsack/TSP/colouring/scheduling × sizes, 18 per cell), solver arm + 2 repairs, T=0.7, 3 seeds; within 1% of the
best-known/optimal value; best-of-3 = label-free (feasible + best objective)
| model | no doc (best-of-3) | full cheat sheet (best-of-3) | **scoped snippet** (best-of-3) | **scoped − full (95% CI)** | scoped − none |
|---|---|---|---|---|---|
| 8B | .255 (.377) | .349 (.444) | **.710** (.718) | **+.361 [+.307, +.415]** | +.455 [+.402, +.509] |
| 14B | .607 (.857) | .810 (.952) | **.959** (1.000) | **+.149 [+.112, +.189]** | +.352 [+.310, +.397] |
| 32B | .701 (.873) | .926 (1.000) | **.970** (1.000) | **+.044 [+.021, +.067]** | +.269 [+.228, +.310] |
- **Final CO claims (powered):** (1) the scoped snippet beats the full cheat sheet at every size, CI excluding 0, and the gain shrinks with scale (+.36 → +.15 → +.04).
  (2) Verified best-of-3 on top of the snippet reaches **1.000 at 14B and 32B**. Even the full sheet + best-of-3 reaches 1.000 at 32B (.952 at 14B). (3) At 8B, best-of-3
  adds almost nothing to the snippet (.710 → .718): its TSP failures are systematic (same API misuse every sample), so stating facts is the only lever there.
- **Project scope (user decision, 10:30): computational geometry + combinatorial optimization only.** Zebra (CSP) optional; Mastermind/hints appendix at most.
### CO distractor dose-response (10:58): scoped snippet + K = 0/4/8 correct-but-unneeded CP-SAT lines, 84 instances × 2 seeds, T=0.7
| model | K=0 | K=4 | K=8 | per-problem at K=0 → K=8 |
|---|---|---|---|---|
| 8B | .708 | .708 | .708 | knap 1.00, TSP 0.00, colour 1.00, sched .97 at every K (prompts and programs verified to differ; outcomes saturated) |
| 14B | .982 | .970 | .958 | only TSP moves: .94 → .90 → .85 |
| 32B | .964 | .970 | .964 | flat |
- **Little or no distractor effect in CO** (14B −2.4 pts, mostly TSP; 8B/32B flat), unlike geometry (−17 to −29) and zebra 32B (−19). The extra lines here (automaton, inverse,
  table, reified constraints…) are clearly unrelated to knapsack/TSP/colouring/scheduling, and the models ignore them. In geometry the distractors are *plausible*
  helpers for the same task (collinear, on_segment, polar_sort) and get used or prime over-engineering.
- **This reinterprets the CO "scoped vs full cheat sheet" gain (+.36 / +.15 / +.04):** it's mainly the snippet supplying the *right modelling pattern* (e.g. makespan via a
  bound variable, the routing recipe), not the removal of irrelevant text. **Paper framing:** irrelevant tools hurt when they're plausible for the task at hand. Unrelated
  documentation is mostly harmless. The CO lever is stating the problem-specific facts/patterns.
### CO plausible distractors (13:30): scoped snippet + the other three problems' snippets (84 instances × 2 seeds)
- No harm either: others − none = 8B +.006 [.000, +.018], 14B −.012 [−.054, +.024], 32B .000 [−.036, +.030]. **CO is robust to extra documentation, related or
  not.** The plausibility hypothesis doesn't explain the domain difference. CO models re-derive a standard formulation and ignore extra text, while geometry
  distractors are *functions to embed in the program*.
### Mechanism of the geometry distractor harm (13:40), from the final n=300 K=8 runs: what the failures are
- 8B: 68 failures = 41 logic + 5 degen + 15 crashes (IndexError 8, segments_intersect arg misuse 7) → mostly **semantic** (wrong algorithm/degenerate handling).
- 14B: 96 failures = **32 `segments_intersect()` called with 8 scalars** (interface misuse) + **30 NameError (helper called but not copied)** + 19 logic.
- 32B: 71 failures = 34 logic + **24 NameError (not copied)**.
- So a large share of the harm at 14B/32B is *packaging/interface* (the copy-in protocol and helper signatures), on top of the semantic over-engineering seen at 8B.
  Running: queue_prelude.sh. Helpers pre-defined at execution ("already defined, call them directly"), K=0 vs 8, to split copy-failure harm from semantic harm.
### Mechanism split, prelude (pre-defined helpers) vs copy-in (13:41): n=300, --stdlib, T=0.7 s1
| model | copy: K=0 → K=8 (Δ, 95% CI) | prelude: K=0 → K=8 (Δ, 95% CI) |
|---|---|---|
| 8B | 91.7 → 77.3 (**−14.3** [−20.3, −8.7]) | 92.0 → 79.7 (**−12.3** [−17.7, −6.7]) |
| 14B | 83.7 → 68.0 (**−15.7** [−21.3, −10.3]) | 77.3 → 76.0 (−1.3 [−6.7, +4.0]) |
| 32B | 92.0 → 76.3 (**−15.7** [−21.3, −10.3]) | 90.0 → 75.0 (**−15.0** [−20.0, −10.0]) |
- **The harm is mainly semantic, not packaging:** with copy failures impossible, 8B and 32B lose as much as before (−12 / −15). The uncopied-helper NameErrors were
  programs that would have failed anyway. Per task (32B prelude K=8): hull 16/60, area2 43/60, close 51/60. The extra helpers drive over-engineered hull/area/closest-pair code.
- **14B is the exception, and it's confounded:** under the toolbox header, 14B misuses the *needed* `segments_intersect` (8 scalars instead of 4 points) even at K=0 (segs
  16/60 copy, 12/60 prelude), which floors the baseline. Under prelude, its hull still drops with distractors (44 → 26/60) but segs moves the other way (12 → 22), netting
  −1.3. With the original "predicates" header 14B segs was fine (98.5 / 97.0). **14B is header/interface-sensitive**, so its distractor number should be reported
  per task, not pooled.
- Paper-ready mechanism statement: *irrelevant-but-plausible helper functions cause semantic over-engineering (wrong hull/area/closest-pair logic) at every size, independent of
  how the helpers are delivered. At 14B, interface misuse of helper signatures adds a packaging failure mode.*
### HELD-OUT CO problems (14:07): bin packing + minimum vertex cover (added after all CO findings; 108 instances, refs all proven optimal), T=0.7
Within 1% of optimum, mean of 2 seeds (best-of-2, label-free feasible + best objective). Direct = answer the solution in text.
| model | direct | solver, no doc | full cheat sheet | **scoped snippet** | per problem with snippet |
|---|---|---|---|---|---|
| 8B | .06 | .13 (.22) | .45 (.50) | **.56** (.62) | binpack .12, vcover 1.00 |
| 14B | .12 | .58 (.66) | .59 (.68) | **.75** (.87) | binpack .49, vcover 1.00 |
| 32B | .19 | .62 (.70) | .68 (.81) | **.94** (.97) | binpack .87, vcover 1.00 |
- **The CO claims replicate on unseen problems:** (1) direct answers collapse (.06–.19); (2) the **scoped snippet beats the full sheet at every size** (+.11 / +.16 / +.26).
  Unlike the original problems, the gain *doesn't* shrink with scale here, because bin packing is harder to model; (3) best-of-2 adds +.03 to +.12.
- Vertex cover is easy (1.00 with any doc at ≥14B). Bin packing carries the signal: the remaining failures are CP-SAT misuse (`CpModel.Not`, boolean use of
  BoundedLinearExpression, `OnlyEnforceIf` on the wrong object) and feasible-but-poor packings at 8B (mean gap 93%). These are genuine model errors (checked), the same misconception
  family as zebra/CO, and again fixed most by stating the right pattern (32B .35 → .87 on bin packing).
### API-contract line fixes 14B's interface misuse (14:18); held-out CO best-of-3
- **14B toolbox K=0 + one sentence of API contract** ("every point argument is ONE (x, y) tuple" + 4 example calls): **83.7 → 94.0**, segs **16 → 55/60** (the 8-scalar
  `segments_intersect` calls disappear). Another stated-fact fix. **With 8 distractors it stays ~68** (67.3; segs 18 → 35 but hull 24/60, pip 26/60): the contract fixes
  the *interface* failure, not the *semantic* over-engineering. So the 14B distractor harm under a correct interface is −26.7 (94.0 → 67.3), in line with 8B/32B
  (−12 to −16) and the final 14B −29.
- **Held-out CO with 3 seeds:** best-of-3 for full sheet / scoped snippet: 8B .51 / **.74**, 14B .73 / **.92**, 32B .89 / **.99**. Singles were .45 / .58, .58 / .74, .68 / .94.
  Same shape as the main CO table: snippet ≫ full sheet, and verified sampling stacks on top (+.16 to +.18 at 8B/14B).
### Does thinking help once the facts are stated? (15:20) — geometry n=100 (--stdlib, T=0.7 s1), CO 84 instances (scoped snippet + repair, s1)
| model | geometry no helpers: think / no-think | geometry task-matched: think / no-think | **CO scoped snippet: think / no-think** |
|---|---|---|---|
| 8B | 92 / 94 | 99 / 95 | **.87** / .71 (TSP **.58** / 0) |
| 14B | 94 / 93 | 99 / 99 | **1.00** / .96–.98 |
| 32B | 92 / 89 | 98 / 95 | .98 / .96–.97 |
- **Geometry: thinking is roughly neutral** (±3 without helpers, +0–4 with task-matched predicates). The remaining failures under thinking are almost all **degenerate-case
  bugs** (degen_only 6–7/100) that more reasoning doesn't find. Verified sampling (k=3: 94–99) or the encapsulating predicate is the better lever.
- **CO: thinking is the one lever that breaks 8B's TSP floor** (0 in every no-think arm, docs/shim/repair/sampling included → **.58** with thinking). It lets the model work through
  the routing API instead of pattern-matching a wrong prior. At 14B/32B it closes the last gap (1.00 / .98). No thinking run hit the 20k budget (finish=length 0).
- Recipe update: thinking is worth its cost (~5–10× tokens) only where errors are systematic API/modelling misconceptions *and* the model is small (8B CO). For
  edge-case-heavy code (geometry), sample-and-check is cheaper and better.
### Cross-family replication (17:25): Llama-3.3-70B (w4a16); Granite and Gemma not runnable
| Llama-3.3-70B | value |
|---|---|
| geometry greedy: base / task-matched (n=300, --stdlib) | 92.0 / 91.3 |
| geometry sampled singles (T=0.7) | 84.3 / 83.7 / 86.0 |
| **K=0 → K=8 distractors** | 87.3 → 83.3, **Δ −4.0 [−9.3, +1.0]** (not significant) |
| **MR-select k=3 / plain vote k=3** | **92.7** / 86.0 |
| **CO (84 inst, T=0.7 s1): no doc / full sheet / scoped snippet** | .33 / .55 / **.87** |
- **Replicates:** the CO snippet ≫ full cheat sheet (+.32), and verified sampling (k=3 recovers greedy level, with the metamorphic filter +6.7 over voting).
- **Doesn't replicate:** the geometry distractor harm is small and not significant for Llama-70B (−4.0 vs −17 to −29 for Qwen3), and task-matched predicates give no gain
  (greedy base is already 92). The distractor sensitivity is model-dependent: report it as strong for Qwen3 8B–32B, weak for Llama-3.3-70B.
- Granite-4.1-8B: the checkpoint has no chat template (base model). The API returned 400 for every request, so all files are empty and *no* result. Gemma-3-27B: vLLM 0.10.2's
  Gemma-3 path hard-requires flash_attn, and the installed build is ABI-incompatible (even with an import stub). Not runnable in this environment.
### E3 retrieval baseline for tool scoping (17:52): top-1 helper by IDF-weighted word overlap (task text vs helper name+doc), K=8 pool, n=100, T=0.7, 2 seeds
| model | self-pick list | pointwise | plan-first | **lexical top-1** | (all 8 / oracle) |
|---|---|---|---|---|---|
| 8B | 80.0 | 82.0 | 78.5 | 76.5 | 74.5 / 98.0 |
| 14B | 83.5 | 74.5 | 79.5 | 62.0 | 75.0 / 84.5 |
| 32B | 85.0 | 79.5 | 73.0 | 80.0 | 75.5 / 95.5 |
- Per task (seed 1), lexical retrieval is all-or-nothing: **pip 20/20 at every size** (it always retrieves `point_in_polygon`) and segs 15/3/20 (14B again misuses the
  signature), but **hull collapses to 1–2/20**. For hull the name match picks `collinear`, a single plausible distractor, and the model then over-engineers collinear handling.
- Takeaway for E3: naive retrieval finds the encapsulating predicate when the task name matches it, but one wrong retrieved helper is enough to wreck a task. Precision
  dominates, as with self-scoping. A deployable scoper needs a precision guard (abstain when unsure) or must be combined with verified selection.
- Qwen3-Next-80B-A3B (AWQ, cyankiwi) is not loadable in vLLM 0.10.2 (KeyError layers.14.mlp.shared_expert.down_proj.weight in the weight loader); E1 architecture-variety point dropped.
### Llama-3.3-70B follow-ups (18:12): no distractor effect; CO held-out replicates strongly
- **Geometry distractors, 3 seeds (n = 900 paired programs): K=0 → K=8 Δ = −0.8 [−3.8, +2.1]** (per seed −4.0 / +1.3 / +0.3). Pre-defined helpers: +4.3 [−0.7, +9.3].
  **Llama-3.3-70B is immune to the plausible-helper harm** that costs Qwen3 8B–32B 17–29 points. The effect is model-dependent, not universal. Open question (E1):
  family (Qwen vs Llama) or capability? Llama-3.1-8B dose test queued.
- **Held-out CO (bin packing + vertex cover, 108 inst), Llama-3.3-70B:** direct .02 | solver no doc .51 | full sheet .54 | **scoped snippet .98** (bin packing **.96** vs .07
  with the full sheet). The "state the problem-specific pattern" claim replicates across families and on unseen problems, with the largest gap seen anywhere.
### Family or capability? Llama-3.1-8B distractor test (18:22): capability
- **Llama-3.1-8B, K=0 → K=8 related helpers (n = 300 × 2 seeds, --stdlib, T=0.7): 73.0/79.0 → 36.7/36.7, pooled Δ = −39.3 [−43.8, −34.7]**, the largest harm measured.
  Llama-3.3-70B (same family) shows none (−0.8 [−3.8, +2.1]). So the plausible-helper harm is a **capability effect, not a family effect**: smaller/weaker models
  (Qwen3 8B–32B, Llama 8B) are hurt, while the strongest model tested ignores irrelevant helpers.
- Failure mix at K=8 (seed 1): 95 logic + 87 crashes (≥28 NameError = helper called but not copied, 7 IndexError, `is_convex`-style ValueErrors such as "Input polygon is not
  convex" from misapplied helpers). Per task: hull 2/60, area2 6/60, pip 38, segs 28, close 36. Both semantic misuse and packaging, as for Qwen3-14B.
### Reasoning removes the plausible-helper harm (20:44); DeepSeek-R1-Distill-Llama-70B
| model / mode | K=0 → K=8 related helpers | Δ (95% CI) |
|---|---|---|
| Qwen3-14B **thinking** (n=100, s1) | 100 → 99 | −1.0 [−3.0, 0.0] |
| Qwen3-32B **thinking** (n=100, s1) | 100 → 97 | −3.0 [−7.0, 0.0] |
| DeepSeek-R1-Distill-Llama-70B (reasoning model, T=0.6, n=100) | 99 → 99 | +0.0 [−3.0, +3.0] |
| *(no-think, for comparison: Qwen3-14B / 32B, n=300)* | | *−29.0 / −17.0* |
- **Thinking makes the same Qwen3 models immune** to the 8 plausible helpers (−1 / −3 vs −29 / −17 without thinking), and the reasoning-distilled R1-70B is unaffected too.
  Together with Llama-70B (−0.8, no thinking) and Llama-8B (−39.3): **robustness to irrelevant in-context tools comes with reasoning or high capability.** Weaker, non-reasoning
  generation copies and misapplies plausible helpers. Thinking costs ~5–10× tokens; it buys tool-robustness here, while for clean geometry it was neutral (T6).
- R1-Distill-70B also: geometry greedy-ish (T=0.6) base 94 → task-matched 100; CO solver no doc .50 | full sheet .92 | scoped snippet .95 (5/1/0 runs hit the 16k budget).
  The scoped-vs-full gap nearly vanishes for a reasoning model (+.03), matching the shrinking gap with scale/thinking elsewhere.
- **Thinking result confirmed with 2 seeds (21:58; n = 200 paired programs each):** K=0 → K=8 with thinking: Qwen3-8B −1.5 [−4.5, +1.5], 14B −0.5 [−2.5, +1.0], 32B −3.0
  [−5.5, −1.0] (small but non-zero), vs −17.7 / −29.0 / −17.0 without thinking. Even the weakest Qwen model is essentially immune once it reasons. Robust conclusion.
- **Qwen3-1.7B (22:10):** no-think K=0 → K=8: 58.7 → 23.0, **−35.7 [−41.7, −29.7]** (n=300); thinking: 90.0 → 86.0, −4.0 [−13.0, +4.0] (n=100). Even the smallest model is largely
  protected by thinking (wide CI; one seed), and thinking also lifts its K=0 baseline from 59 to 90. The harm without reasoning grows as models get weaker (1.7B −36, Llama-8B −39,
  Qwen3 8–32B −17 to −29, Llama-70B −1).
- **Qwen3-1.7B thinking, 3 seeds (22:31; n = 300 paired):** −4.3 [−9.3, +0.7] (per seed −4 / −5 / −4) vs −35.7 without thinking. A small residual harm is possible at 1.7B, but thinking
  removes ~88% of it. Consistent across all Qwen3 sizes.
### Fallback when tools can't be trimmed (22:53): verified sampling under K=8 distractors (n = 300, --stdlib, T=0.7)
| model | K=8 single samples (mean) | **K=8 + MR-select k=3** (vote) | K=8 + thinking (2 seeds) | needed helpers only, one sample |
|---|---|---|---|---|
| 8B | 77.1 | **81.3** (80.7) | 97.0 | 95.0 |
| 14B | 71.0 | **84.3** (84.0) | 99.0 | 97.0 |
| 32B | 75.0 | **84.0** (82.7) | 97.0 | 93.3 |
- Sampling + check **recovers only part** of the distractor loss (+4 / +13 / +9) and stays 9–13 points below trimming the toolbox. Thinking fully recovers it (≥ trimmed level), at ~5–10×
  tokens. **Decision table:** trim irrelevant tools (cheapest, best) ≳ think (expensive, robust) ≫ sample-and-check under a broad toolbox ≫ nothing. The distractor errors are
  partly *systematic* (every sample over-engineers the same way), which is why selection helps less here than on clean prompts (where k=3 gave 94–99).
### Thinking on the held-out CO problems (00:19; bin packing + vertex cover, 108 inst, T=0.7 s1)
| model | scoped snippet: no think → **think** | full sheet: no think → **think** | bin packing with snippet: no think → think |
|---|---|---|---|
| 8B | .58 → **.94** | .45 → **.71** | .17 → **.87** |
| 14B | .74 → **.98** | .59 → **.94** | .48 → **.96** |
- **Thinking fixes the systematic modelling/API failures on unseen problems** too (bin packing +.70 at 8B, +.48 at 14B), extending the 8B-TSP result (0 → .58) to held-out CO.
  The snippet still matters under thinking at 8B (.94 vs .71 with the full sheet; 8 of the full-sheet runs hit the 20k budget), less at 14B (.98 vs .94).
- **Recipe, final form:** facts/snippet first; thinking is the lever for *systematic* errors in small models (CO API/modelling, distractor over-engineering); verified sampling for
  *independent* errors (geometry edge cases) when thinking's 5–10× token cost isn't wanted.
### E2 started (00:25): new held-out geometry task `overlap` (designed after all findings)
Two convex polygons (hulls of random even-coordinate points, B offset to balance yes/no; no vertex on the other's boundary in the base instance). Question: do they share at
least one point (touching counts, containment counts)? Exact oracle `polys_overlap` (edge-pair intersection + containment). Variants: translate/rot90/mirror/permute (start
vertex, orientation, A↔B swap)/scale/1e9 preserve the answer. Degenerate variant: B moved so one vertex exactly touches A, answer becomes yes. Unit-tested: handmade
touch/edge/containment/separate cases, all 8 variants of 20 instances agree with the oracle, and an exact reference program matches the oracle on all 160 inputs.
Task-matched helpers = the 4 predicates; the K=8 pool is the other 8 geometry helpers (none solves the task). queue_overlap.sh: Qwen3 8B/14B/32B.
### E2 held-out task `overlap`: results (01:05; 60 programs per run, --stdlib)
| model | greedy: no helpers → 4 predicates | samples (T=0.7) | **MR-select k=3** (vote) | K=0 → K=8 toolbox (Δ, CI) | **K=8 + thinking** |
|---|---|---|---|---|---|
| 8B | 58.3 → **100** | 83.3 / 81.7 / 86.7 | **96.7** (88.3) | 98.3 → 93.3 (−5.0 [−11.7, +1.7]) | **100** |
| 14B | 75.0 → 53.3 | 93.3 / 91.7 / 80.0 | **95.0** (93.3) | 78.3 → 70.0 (−8.3 [−23.3, +6.7]) | **100** |
| 32B | 46.7 → **100** | 61.7 / 56.7 / 53.3 | **70.0** (63.3) | 100 → 85.0 (**−15.0 [−25.0, −6.7]**) | **100** |
- **Replicates on a task designed after all findings:** (1) the encapsulating predicates (`segments_intersect` + `point_in_polygon`) fix the task at 8B/32B (58 → 100,
  47 → 100). Baseline failures are mostly the exact-touch degenerate case (8B degen_only 17/60) or wrong logic (32B 28/60). (2) Verified sampling helps a lot, and the metamorphic
  filter beats voting (+8.4 / +1.7 / +6.7). (3) Plausible extra helpers hurt in the same direction (significant at 32B; n = 60 is small). (4) **Thinking makes all three sizes
  100% even with 8 extra helpers.**
- Exception: 14B with the 4-predicate block drops to 53.3 (11 IndexError input-parsing crashes, 9 transform_only, 8 logic). The same interface/format fragility of 14B
  seen before (segments_intersect signature, toolbox header). Report 14B per task.
### Per-helper presence analysis (01:20; 2,700 K=8 programs, Qwen3 8B/14B/32B × 3 seeds)
- No single helper explains the harm: presence effect per helper (stratified by model × task) ranges −3.3 (`polygon_area2`) to +2.7 (`bbox`) pts. At K=8 most helpers are present,
  so the contrast is limited; the dose levels K=2/4 are the better design for E4.
- Use in failing vs passing programs: hull `collinear` 64% vs 42%; closest pair `orient` 46% vs 25%, `collinear` 42% vs 16%, `on_segment` 34% vs 19%. So degenerate-case predicates
  are associated with failure where they're irrelevant. Mechanism synthesis written up in PROPOSAL.md Appendix B.4 ("off-idiom drift": helpers act as algorithm hints that
  standard generation follows; reasoning/scale lets the model judge relevance first).
### Beyond accuracy: what the generated programs look like (01:35; poc/analyze_outputs.py, stored code; Qwen3, K=0 vs K=8, n = 300/900)
| model / condition | acc | code tokens | function defs | helpers copied | branches (if/elif) | special-case code* | hull algorithm |
|---|---|---|---|---|---|---|---|
| 8B K=0 | 91.7 | 301 | 3.0 | 1.6 | 3.0 | 1.8 | monotone chain 60/60 |
| 8B K=8 | 77.1 | **786** | 9.7 | 7.3 | **10.6** | **6.7** | monotone 85, **Graham/polar 74**, other 18 |
| 8B K=8 thinking | 97.0 | 449 | 5.0 | 3.7 | 5.8 | 3.6 | monotone 30, Graham 9 |
| 14B K=0 | 83.7 | 314 | 3.0 | 1.6 | 3.1 | 1.9 | monotone 60/60 |
| 14B K=8 | 70.9 | 418 | 4.7 | 3.1 | 4.6 | 3.3 | **Graham 88**, monotone 85 |
| 14B K=8 thinking | 99.0 | 533 | 6.0 | 4.7 | 6.8 | 4.3 | monotone 37, Graham 3 |
| 32B K=0 | 92.0 | 290 | 3.2 | 1.4 | 2.8 | 1.9 | monotone 55/60 |
| 32B K=8 | 75.0 | 465 | 5.5 | 3.8 | 5.4 | 3.9 | **Graham 129**, monotone 32 |
| 32B K=8 pre-defined | 75.0 | 184 | 1.8 | 0.4 | 1.9 | 0.5 | Graham 46, monotone 8 |
| 32B K=8 thinking | 97.5 | 331 | 3.4 | 2.3 | 4.2 | 2.4 | monotone 20, Graham 20 |
(*matches of collinear/duplicate/degenerate/on_segment/`== 0` handling)
- **Extra helpers change the program, not just the score:** with 8 helpers the code is 1.4–2.6× longer, has 1.7–3.5× more branches and 2–3.7× more special-case handling, and the hull
  algorithm **switches from the monotone chain (100% at K=0) to a polar-sort Graham scan** (44% / 51% / 75% of hull programs at 8B / 14B / 32B). Failing programs are longer and
  more special-cased than passing ones (8B special-case 8.0 vs 6.3; 14B 4.8 vs 2.6; tokens 865 vs 762, 503 vs 383).
- The algorithm switch persists when helpers are pre-defined (32B: Graham 46/58) although the code gets *shorter*. So the driver is the **algorithm choice suggested by the helpers**,
  not the copying. With thinking, 8B/14B return to the monotone chain (Graham 9/40, 3/40). 32B still picks Graham in half the programs but implements it **correctly** (97.5%).
  The Graham scan is not wrong per se; non-reasoning generation implements the less-practised algorithm badly. Direct evidence for "off-idiom drift" (Appendix B.4).
- Next (queued): logit probe (poc/logit_probe.py), teacher-forced log-probability of fixed monotone / Graham / collinear-pass programs under K=0 vs K=8 vs the "may" header,
  scoring only the algorithm part (copying helper text excluded). Tests whether the helpers shift the model's *prior* over algorithms.
### Logit probe (01:50): extra helpers shift probability mass toward helper-based programs (teacher forcing, 20 hull instances, Qwen3)
Log-odds (nats) of a fixed program vs the textbook monotone chain, **whole program** (helper copying included) | **algorithm part only** (after the helper definitions):
| model | Graham(polar_sort) vs mono: K=0 → K=8 → K=8 "may" | collinear-pass vs mono: K=0 → K=8 → "may" | algorithm part, Graham vs mono: K=0 → K=8 |
|---|---|---|---|
| 8B | −318 → **−87** → −97 | −154 → **−65** → −73 | +14.8 → −1.7 |
| 14B | −215 → **−73** → −80 | −156 → **−77** → −80 | +30.5 → +3.1 |
| 32B | −185 → **−56** → −62 | −85 → **−45** → −50 | −1.9 → −2.1 |
- With 8 helpers in the prompt, the helper-based programs become **130–230 nats (Graham) and 40–90 nats (collinear pass) more likely relative to the textbook program**. The
  monotone chain is still the single most likely of the three fixed programs, but sampled programs (T=0.7) take the helper routes 44–75% of the time (Graham family).
  The "most are NOT needed" header moves these log-odds back by only 7–10 nats, the logit-level counterpart of "the warning doesn't remove the harm".
- **Where the shift happens:** almost entirely in the *prefix* (choosing to copy and use the helpers). Conditional on the helper definitions already written, the algorithm-part
  log-odds barely move (or move toward mono). The decision point is at the start of the program: helpers make helper-based starts cheap, and the rest of the program follows.
  Caveat: whole-program scores include the helper text itself (copying is trivially likely under K=8), so magnitudes partly reflect copy-ability. That is the affordance.
### How much thinking is needed? Budget forcing (01:50; K=8 related helpers, n=100, T=0.7 s1)
| model | 0 tokens | 256 | 1024 | 4096 | (full thinking ≤20k, 2 seeds) |
|---|---|---|---|---|---|
| 8B | 74 | 86 | **95** | 97 | 97.0 |
| 14B | 62 | 92 | **93** | 100 | 99.0 |
| 32B | 75 | 82 | **92** | 98 | 97.0 |
- **About 1k thinking tokens recovers most of the distractor loss** (to 92–95), and 4k matches full thinking. B=0 reproduces no-thinking accuracy (74 / 62 / 75), a sanity check of the
  budget-forcing harness. The cost of the thinking fix is ~1–4k extra tokens per program, not the 10–20k of unconstrained thinking.
### Leakage check for verified sampling (02:10)
The metamorphic check uses 6 of the 8 evaluation variants. On the variant the check never sees (degenerate), MR-select still improves over the mean single sample:
8B 96.7 → 99.0, 14B 96.6 → 97.7, 32B 87.2 → 95.0 (identity: 96.1 → 98.7, 98.0 → 100, 90.2 → 98.0). The gain isn't purely an artifact of shared transforms. Fresh-instance
evaluation is still recommended (PROPOSAL Section 5, item 1).
### Thinking trace example (02:05; Qwen3-32B, hull, K=8, saved to results/example_thinking_32b_hull_k8.txt)
The model notices `polar_sort`, lists Graham/Andrew/Jarvis, chooses Andrew's monotone chain (named 18×), and reasons that `<= 0` already drops collinear points. Qualitative evidence
that reasoning re-anchors on the practised algorithm (PROPOSAL Appendix C.5). Added a constructive critical review as PROPOSAL Section 5 (13 concerns with checks and fixes).
### Review item 1 resolved (02:30): verified sampling on FRESH instances (poc/fresh_eval.py)
The selection uses the metamorphic check on the given instance; the chosen program is then scored on 5 fresh instances × 8 variants (never seen by the check). n = 300 original instances:
| model | one sample | **3 samples + metamorphic check** | one sample with task-matched predicates |
|---|---|---|---|
| 8B | 91.7 | **98.2** | 95.0 |
| 14B | 96.2 | **97.7** | 97.0 |
| 32B | 85.4 | **93.9** | 93.7 |
- Matches the in-instance numbers (98.7 / 97.7 / 94.3): **no leakage**. Verified sampling selects programs that generalize, and it equals or beats the hand-picked predicates on unseen inputs.
### Review item 2 resolved (03:30): neutral header, no instruction ("The following tested helper functions are available:"), n = 300, T=0.7 s1
| model | "should use" header: K=0 → K=8 | **neutral header: K=0 → K=8** |
|---|---|---|
| 8B | 91.7 → 77.3 (−14.3) | 92.7 → 80.0 (**−12.7**) |
| 14B | 83.7 → 68.0 (−15.7) | 79.3 → 61.0 (**−18.3**) |
| 32B | 92.0 → 76.3 (−15.7) | 91.7 → 62.7 (**−29.0**) |
- The harm is **not** caused by the instruction to use the helpers: without any instruction it is as large or larger (32B −29.0). The helpers alone change the programs.
### Efficiency pilot X1/X2 (03:30; Qwen3-8B, geometry K=8 n=100 / n=300, CO)
- **X2 precision, fp8 weights (W8A16) vs bf16:** geometry tool-free 272 vs 272 /300, K=8 227 vs 228, CO scoped snippet .714 vs .702, held-out CO with thinking .935 vs .935 (mean thinking
  tokens 6.6k vs 5.9k). **fp8 weight quantization is harmless for this algorithmic code.** fp8 KV cache could not be run: vLLM 0.10.2 falls back to the V0/XFormers backend for fp8 KV,
  which imports the ABI-broken flash_attn (also with the import stub). 4-bit 8B needs bitsandbytes/AWQ checkpoints not installed here (the 32B we use *is* AWQ 4-bit).
- **X1 compute frontier, token-accounted** (K=8 distractors, seed 4, n=100):
  | strategy | mean tokens / program | accuracy |
  |---|---|---|
  | one sample, no thinking | 837 | 79.7 (3 seeds) |
  | 2 samples + check | ≈1.7k | 81 |
  | 3 samples + check | ≈2.5k | 84 |
  | thinking budget 256 | 0.8k | 85 |
  | thinking budget 1024 | 1.6k | 87 |
  | thinking budget 4096 | 3.9k | 95 |
  | full thinking | 5.8k | 97 |
  **At equal tokens, budgeted thinking beats best-of-k** (1.6k: 87 vs 81; ~2.5k: thinking ≳ 90 vs 84). Under distractors the errors are systematic, so extra samples repeat them while
  reasoning avoids them. (Budget 1024 gave 95 on seed 1 vs 87 on seed 4: n = 100 per point is noisy; more seeds needed.)
### Review item 3 (04:30): 5× larger instances (hull/close 50–100 points, polygons 40–70 vertices, 30–50 segments; --stdlib; 200 programs per run)
| model | greedy: no helpers → task-matched | samples (T=0.7) | **3 samples + check** (vote) | K=0 → K=8 toolbox |
|---|---|---|---|---|
| 8B | 100 → 99 | 94.0 / 94.0 / 93.5 | **99.0** (97.0) | 95.5 → 66.5 (**−29.0**) |
| 14B | 93.5 → **100** | 93.0 / 92.5 / 91.0 | **98.0** (97.0) | 84.5 → 73.0 (**−11.5**) |
| 32B | 82.5 → **99.5** | 78.0 / 81.0 / 79.0 | **93.0** (90.5) | 85.5 → 69.0 (**−16.5**) |
- **Every geometry claim holds at 5× scale:** encapsulating predicates fix the weak baselines (32B 82.5 → 99.5, 14B 93.5 → 100); verified sampling adds +4 to +14 over single samples and the
  metamorphic filter beats voting (+2 / +1 / +2.5); plausible extra helpers hurt by 11–29 points. Item 3 is resolved for size; realistic multi-function tasks remain open.


## Review item 6 (prompt paraphrases) + clean-prompt compute frontier (2026-10-12)

**Item 6: 3 instruction templates (pv0 original, pv1 "Solve this by writing code…", pv2 "Your task is to implement…"), neutral header, n=300 geometry, correct of 300:**

| model | pv0 K0 → K8 | pv1 K0 → K8 | pv2 K0 → K8 |
|---|---|---|---|
| 8B | 278 → 240 (−38) | 294 → 234 (−60) | 290 → 237 (−53) |
| 14B | (−18.3 pts) | 233 → 227 (−6) | 220 → 170 (−50) |
| 32B | (−29.0 pts) | 270 → 181 (−89) | 274 → 178 (−96) |

- The distractor harm persists under every template (5 of 6 new cells: −50 to −96 of 300). The exception is 14B pv1 (−6), consistent with 14B's known prompt sensitivity.
- Templates move the clean baseline too (14B 233 vs 220), so the spread across templates is reported, not one number. Item 6 resolved.

**X1 on clean prompts (8B, no extra helpers, n=100, tokens = mean output tokens incl. thinking):**

| arm | correct | tokens |
|---|---|---|
| single sample (3 seeds) | 94 / 90 / 97 | ≈290 |
| MR best-of-2 / best-of-3 | 97 / **100** | ≈580 / ≈870 |
| budget 256 / 1024 | 88 / 87 | 578 / 1335 |
| full thinking | 91 | 5467 |

- **On clean prompts, verified sampling dominates thinking:** best-of-3 = 100 at ≈0.9k tokens vs 91 at 5.5k for full thinking. Thinking's failures here are degenerate-case answers (7 of 9 full-thinking failures are degen_only), i.e. reasoning "over-handles" edge cases.
- **Under distractors the order flips** (earlier: budget 1k 87 vs best-of-2 81; thinking 97 vs best-of-3 84). Errors there are systematic (the same off-idiom algorithm in every sample), so extra samples repeat them; thinking changes the algorithm choice.
- Takeaway for the compute-optimal question: choose the fix by error type — independent errors → sample + check; systematic (prompt-induced) errors → reasoning.


## Review item 7: automatic harness sanity check (poc/sanity_check.py, CPU) (2026-10-12)

- **Reference passthrough:** a correct program (oracle code + stdin parser) is pushed through the same render → sandbox → output-parse path as model
  programs: **480/480 on all 10 geometry tasks** (8 variants × 60 instances). **MR false alarms: 0/60 on every task** (the label-free check never
  rejects a correct program).
- **New defect found — "simple" polygons are mostly self-intersecting.** `star_polygon` keeps the n smallest-angle points around the centroid of a
  larger sample, so the angular span is often < 2π and the closing edge crosses the chain: area2 53/60, pip 49/60, convex 25/60 identity polygons
  self-intersect although the prompt says "a simple polygon".
  - **Labels are unaffected by the choice of rule:** pip — even-odd vs non-zero winding agree on 960/960 variant queries; convex — every
    self-intersecting polygon is labelled "no" (0 "yes"); area2 — the label is |shoelace|, which is exactly what a standard program computes.
  - So the reported accuracies measure the intended skills, but the prompt makes a false claim. Full project: regenerate with a simple-polygon
    generator (rejection with `is_simple` works for n ≤ 14; 2-opt untangling for larger n). The new `lattice` task already uses rejection
    (Pick's theorem needs simplicity); its oracle was cross-checked against a winding-number brute force on 140/140 variants.

## Review item 3: two realistic multi-step CG tasks added (lattice, rectunion) — runs queued (queue_real.sh, prefix R_)

- `lattice`: integer points strictly inside a simple polygon (Pick: area + boundary gcd; `polygon_area2` is the needed helper; `point_in_polygon`
  over the bounding box is a plausible slower alternative). MR: scale is skipped (no closed-form relation). Degenerate: doubled coords + collinear vertex.
- `rectunion`: area of the union of overlapping axis-aligned rectangles given by arbitrary opposite corners (sweep / coordinate compression).
  MR: scale ×9. Degenerate: duplicate rectangle, one sharing an edge exactly, one nested 1×1.
- Both oracles verified (lattice vs winding brute force 140/140; rectunion vs cell painting 96/96); reference passthrough 480/480, MR false alarms 0.

## X1 for optimization, offline part (existing runs, scoped snippet, repair 2; "opt" = optimal & feasible)

| 8B | single (3 seeds) | best-of-2 / 3 (label-free: feasible, best objective) | full thinking |
|---|---|---|---|
| main 4 problems (n=252 / 84) | .71 / .72 / .71 @ ≈770 tok | .72 / .72 @ ≈1.5k / 2.3k | **.87** @ 5.9k |
| held-out binpack+vcover (n=108) | .58 / .54 / .65 @ ≈600 tok | .62 / .74 @ ≈1.2k / 1.8k | **.94** @ 6.1k |

- 14B: main .98/.94/.95 → best-of-3 **1.00** (≈1.6k tok) vs thinking 1.00 (3.8k); held-out .74 → best-of-3 .92 (≈2k) vs thinking .98 (4.7k).
- 32B: main .96 → best-of-2 1.00; held-out .96 → best-of-3 .99 (≈1.3k).
- **The error-type rule carries over to CO:** at 8B the failures are systematic API misconceptions (routing callback index, generator in `Add`),
  so best-of-3 barely moves the main set (.71 → .72) while thinking reaches .87; at 14B/32B the remaining errors are independent slips and
  best-of-k matches thinking at ≈1/3 of the tokens. Budget-forced thinking (B = 256/1024/2048) queued (queue_cobudget.sh) to fill in the curve.


## CORRECTION (06:40): the neutral-header harm was inflated by copy failures (poc/rescore_prelude.py)

The neutral header ("The following tested helper functions are available:") never says "copy them into your program", so many programs call a
listed helper without defining it → NameError → "crash". Diagnosis on the realistic-task runs: 32B K8-neutral 32 of 51 crashes, 14B 45+4 of 58 are
NameErrors. Re-scoring every stored program with the offered toolbox pre-defined in front of it (model's own definitions override), n=300:

| model | "should use" K0 → K8, raw → packaging-free | neutral K0 → K8, raw → packaging-free | neutral pv1 (pkg-free) | neutral pv2 (pkg-free) |
|---|---|---|---|---|
| 8B | 275→232 (−43) → 275→232 (**−43**) | 278→240 (−38) → 278→243 (**−35**) | 294→235 (−59) | 290→238 (−52) |
| 14B | 251→204 (−47) → 251→228 (**−23**) | 238→183 (−55) → 240→239 (**−1**) | 233→231 (−2) | 222→233 (+11) |
| 32B | 276→229 (−47) → 276→236 (**−40**) | 275→188 (−87) → 275→226 (**−49**) | 270→208 (−62) | 274→205 (−69) |

- **8B and 32B:** semantic harm of −35 to −69 of 300 under every header and template. The review-item-2/6 conclusion holds for them.
- **14B:** almost all of its harm is packaging (copying), as the prelude experiment had already shown. Its neutral/paraphrase harm vanishes.
- The 32B "neutral is worse than should-use" (−29 vs −16 pts) was copy failures; packaging-free it is −16.3 vs −13.3.
- Fix for the full project: always pre-define offered helpers (prelude) or score packaging-free, and report copy failures separately.

## Realistic tasks (lattice, rectunion), no-thinking arms (prefix R_, 120 programs/arm = 2 tasks × 2 sizes × 30)

Correct on all 8 variants, of 60 per task (T=0.7 s1 unless noted; K0 = toolbox with only the needed helper; lattice's needed helper is `polygon_area2`):

| model | lattice: no toolbox (s1/s2/s3) | lattice K0 should / neutral | lattice K8 should / neutral | rectunion no toolbox (s1/s2/s3) | rectunion K0 | rectunion K8 should / neutral |
|---|---|---|---|---|---|---|
| 8B | 12 / 10 / 12 | **2 / 4** | **47 / 46** | 8 / 8 / 10 | 5 | 10 / 6 |
| 14B | 1 / 1 / 4 | 1 / 4 | **37** / 20 (packaging-free 45 / 46) | 9 / 6 / 4 | 6 | 7 / 6 |
| 32B | 44 / 43 / 39 (greedy 59) | **9 / 15** | 37 / 20 (packaging-free 40 / 33) | 22 / 29 / 23 (greedy 32) | 22 | **7 / 11** |

- **The tasks are hard without thinking** (8B/14B near floor on both), so the old "harm" contrast is floor-limited there; 32B is mid-range.
- **A correct-but-signed needed helper is a trap.** `polygon_area2` returns the SIGNED doubled area. Given it, every program uses it, and most
  drop the `abs` (8B: 55/60 no abs; 32B: 43/60). Pick's formula with a negative area fails on clockwise inputs (mirror / reversed permutation):
  all 30 (8B) and 14–21 (32B) transform-only failures are exactly "signed area without abs". 32B goes from 44/60 (writes its own |shoelace| + gcd)
  to 9/60 with the helper. Same mechanism as T2: the offered helper decides the algorithm, here with a subtle contract (sign) the model doesn't check.
- **A plausible "distractor" can be the best tool on a hard task.** With K=8, `point_in_polygon` (exact, returns inside/outside/BOUNDARY) is often
  offered; 48–58 of 60 lattice programs switch to brute force over the bounding box with it, and 37–47 are correct (8B 2 → 47). The boundary label
  is exactly what plain winding/ray casting gets wrong ("strictly inside"). So "irrelevant" is task-relative: the same helpers that pull models
  off the textbook idiom on easy tasks supply a missing correct primitive on a hard one.
- rectunion (no helper useful): 32B K8 harm persists (no toolbox 22–29 → K8 7 should / 11 neutral; packaging-free 9 / 12). 8B/14B at floor.
- **Verified sampling on the hard tasks:** MR-select over 3 samples = 44 / 19 / 96 of 120 (8B / 14B / 32B) vs single 18–22 / 7–10 / 62–72;
  oracle-any 53 / 23 / 108. "No consistent candidate" for 34 / 58 / 2 instances: at low accuracy the check mostly abstains rather than picking wrong.
- Thinking arms still running.

## X1 for optimization, budget forcing (8B, scoped snippet, repair 2 without thinking)

| thinking budget | main 4 problems (n=84): opt / tokens | per problem (knap/tsp/color/sched) | held-out (n=108): opt / tokens | binpack / vcover |
|---|---|---|---|---|
| 0 (single) | .71 / 770 | 1.0 / 0 / 1.0 / .96 | .58 / 600 | .17 / 1.0 |
| 256 | .70 / 1.1k | 1.0 / .08 / 1.0 / .83 | .55 / 1.5k | .11 / .98 |
| 1024 | .71 / 1.7k | 1.0 / 0 / 1.0 / 1.0 | .69 / 2.3k | .37 / 1.0 |
| 2048 | .71 / 2.7k | 1.0 / 0 / 1.0 / 1.0 | .80 / 3.0k | .59 / 1.0 |
| full thinking | .87 / 5.9k | 1.0 / .58 / 1.0 / .94 | .94 / 6.1k | .87 / 1.0 |

- **Optimization needs far more thinking than geometry:** ~1k tokens recovered geometry; here TSP stays at 0 up to 2k tokens (the routing-API
  misconception is only fixed by long reasoning), and bin packing climbs .17 → .37 → .59 → .87 only with the full ~6k.
- Per token, best-of-3 (held-out .74 @ 1.8k) ≈ budget 2048 (.80 @ 3.0k); neither touches TSP. Systematic API errors need either long reasoning
  or the stated fact (the routing recipe), consistent with T4.


## T7 follow-up (07:25): causal test of the signed-area trap + thinking on the hard tasks

**Sign test** (lattice, K0 = only the needed `polygon_area2`, "should" header, T=0.7, 2 seeds, correct of 60; tf = transform-only failures):

| model | signed helper (as before) | same helper + comment "SIGNED: negative for clockwise; use abs()" | helper returns abs() | no toolbox (ref.) |
|---|---|---|---|---|
| 8B | 2 / 3 (tf 30 / 25) | **17 / 15** (tf 1 / 1) | **15 / 14** (tf 0) | 12 / 10 / 12 |
| 14B | 1 / 0 | 0 / 1 | 0 / 1 | 1 / 1 / 4 |
| 32B | 9 / 15 (tf 14 / 22) | 17 / 19 (tf 1 / 2) | **46 / 49** | 44 / 43 / 39 |

- **Causal:** making the helper unsigned removes the trap completely (32B back to its no-toolbox level, 8B above it). The transform-only
  failures vanish with either fix, so they were the sign bug.
- **A warning in the docstring is not enough at 32B** (17–19 vs 46–49). With the warning, 32B abandons the helper: 38 of 60 programs switch to a
  bounding-box brute force (vs 4 with the abs helper), and get the boundary wrong. A helper that "looks tricky" pushes the model off the
  Pick-formula idiom, the same off-idiom drift as T2. Lesson for tool design: fix the contract in the tool, don't document the hazard.
- 14B fails for another reason in every condition: 59 of 60 programs brute-force with a plain winding test and count boundary points
  (identity off by ≈B/2 or similar).

**Thinking on T7** (T=0.7 s1, correct of 60 per task):

| model | lattice: think / think + K8 | rectunion: think / think + K8 | mean tokens |
|---|---|---|---|
| 8B | **59 / 57** | **59 / 58** | 8.6k / 8.8k |
| 14B | **60** / (running) | **59** / (running) | 7.3k |
| 32B | **60 / 58** | **56 / 56** | 7.8k / 7.9k |

- Thinking solves both hard tasks almost perfectly (no-think 1–44 of 60), and stays robust to the 8 extra helpers (≤ 3 lost). The "reasoning gate"
  from T2 holds on harder tasks, at ≈ 15–20× the tokens of a no-think program (≈ 0.45k).
- So on hard tasks thinking is the only fix that works across models; verified sampling helps only where single-sample accuracy is already
  moderate (32B), because it can only select, not create, a correct program.


## T7 × another family (08:25): Llama-3.3-70B-w4a16 and Llama-3.1-8B on the hard tasks (queue_t7llama.sh, correct of 60)

| model | lattice: none (s1/s2/s3) | K0 signed / abs | K8 should / prelude | rectunion: none (s1/s2/s3) | K8 should / prelude |
|---|---|---|---|---|---|
| Llama-70B | 0 / 0 / 0 | 0 / 0 | **45 / 46** | 0 / 1 / 1 | 3 / 0 |
| Llama-8B | 0 / 0 / 0 | 0 / 0 | 3 / 11 | 0 / 0 / 0 | 0 / 0 |

- **The "capable model ignores helpers" result from T2 does not transfer to hard tasks.** Llama-70B (−0.8 on the easy tasks) is at the floor here:
  it never uses Pick's theorem (0/60 programs use gcd), writes ad hoc float ray casting over the bounding box, and is off by a boundary-sized
  amount; on rectunion it overcounts by 10–17% (pairwise overlap subtraction without inclusion–exclusion). Verified checks: these are model errors.
- **The exact-primitive helper rescues it:** with K8, `point_in_polygon` (boundary-exact) is offered and Llama-70B jumps 0 → 45–46 on lattice,
  in both the should-use and the pre-defined condition. Same as Qwen 8B/14B. So across both families, "irrelevant" helpers help when they supply
  a primitive the model would get wrong, and hurt when they replace an idiom it knows (T2).
- The signed-area trap doesn't apply to Llama (it never takes the Pick route, so the sign of the area never matters: signed = abs = 0).
- Llama-8B is at the floor everywhere (many crashes: input parsing and NameErrors); pre-defining helpers helps a little (3 → 11).
- MR-select can't help at the floor: no consistent candidate for 107/120 (70B) and 97/120 (8B) instances, 0 wrong picks beyond oracle.
- Qwen3-14B thinking + K8 (finished): lattice 56/60, rectunion 59/60. Thinking is robust to extra helpers at all three Qwen sizes.

Queued (queue_t7bud.sh): R1-Distill-Llama-70B on T7 (does reasoning fix the hard tasks in the Llama family?), and budget forcing
B = 1k/2k/4k for Qwen3-8B / 32B on T7 (how much thinking do hard tasks need? geometry-easy needed ≈1k, optimization ≥6k).


## X1 on the hard tasks (09:25): budget-forced thinking, no toolbox, T=0.7 s1 (correct of 60 @ mean tokens/program)

| model | task | no thinking | B=1024 | B=2048 | B=4096 | full thinking |
|---|---|---|---|---|---|---|
| 8B | lattice | 12 @ 0.6k | **58** @ 1.4k | 57 @ 2.4k | 50 @ 4.5k | 59 @ 7.5k |
| 8B | rectunion | 8 @ 0.6k | 39 @ 2.2k | 41 @ 3.2k | 54 @ 4.8k | 59 @ 9.8k |
| 14B | lattice | 1 @ 0.4k | **58** @ 1.4k | 55 @ 2.4k | 54 @ 4.4k | 60 @ 6.0k |
| 14B | rectunion | 9 @ 0.5k | 50 @ 1.6k | 53 @ 2.7k | 55 @ 4.6k | 59 @ 8.6k |
| 32B | lattice | 44 @ 0.4k | 44 @ 2.3k | 43 @ 3.1k | 57 @ 4.7k | 60 @ 7.5k |
| 32B | rectunion | 22 @ 0.5k | 49 @ 1.7k | 53 @ 2.9k | 52 @ 4.6k | 56 @ 8.0k |

- **About 1k thinking tokens buys most of the gain on the hard tasks** (8B lattice 12 → 58, 14B 1 → 58; rectunion 8–22 → 39–50). The sweep
  line (rectunion) keeps improving up to the full ≈ 9k; the point count saturates at ≈ 1k. Same picture as easy geometry (≈1k), unlike optimization
  (TSP 0 at 2k, bin packing needs ≈ 6k).
- **At equal tokens, thinking beats verified sampling on hard tasks:** 8B best-of-3 + metamorphic check = 44/120 at ≈ 1.7k tokens vs B=1024 97/120
  at ≈ 1.8k. The no-think errors are systematic (no Pick, wrong boundary rule, wrong sweep), so resampling repeats them. Consistent with the X1 rule.
- 32B lattice is flat (44) until B=4096: with short budgets it keeps its no-think Pick program and its residual bugs; only longer reasoning fixes them.

## Review item 3, optimization side: CVRP added (queue_cvrp.sh, prefix V_)

- Capacitated vehicle routing: depot + 8/12/16 customers (demands 1–9), capacity 15–25, K = ceil(total/Q) + 1 vehicles; answer = one node sequence
  with depot separators. Checker verifies coverage, ≤ K routes, capacities; objective = total rounded-Euclidean distance.
- References: exact CP-SAT (AddMultipleCircuit + load propagation), all 30 proven optimal in ≤ 8 s; verified against brute force (8/8 on n = 7).
- Reference passthrough: a correct OR-Tools routing program with a capacity dimension, run through the harness, is optimal on 30/30, so the
  ceiling is 100%. The full cheat sheet only covers TSP routing (no capacity dimension), so it acts as an incomplete-documentation condition.
- Arms (8B, 14B, 32B): no doc / full sheet / CVRP snippet × 3 seeds / snippet + budget 2048 / snippet + thinking / no doc + thinking; repair 2.


## CVRP results (10:25; 30 instances, solver arm, repair 2, T=0.7; opt = proven optimum reached; partial: 14B thinking arms running)

| model | no doc | full sheet (TSP routing only) | CVRP snippet s1/s2/s3 | best-of-3 (label-free: min objective of feasible) | snippet + B=2048 | snippet + thinking |
|---|---|---|---|---|---|---|
| 8B | .00 | .00 | .03 / .07 / .03 | .13 | .07 @ 4.3k | .17 @ 18.8k (no doc + thinking .00) |
| 14B | .20 | .20 | .73 / .70 / .80 @ ≈1.1k | **1.00** @ ≈3.3k | (running) | (running) |
| 32B | .23 | **.07** | .83 / .77 / .90 @ ≈1.6k | **1.00** @ ≈4.8k | .83 @ 3.8k | .97 @ 12.2k |

- **The problem-specific snippet is the decisive fix on a realistic problem** (14B .20 → .73–.80, 32B .23 → .77–.90), as in T4, and **an
  incomplete reference is worse than none at 32B** (.07 vs .23): the full sheet shows TSP routing without the capacity dimension, and 32B
  invents the rest (10 programs call a non-existent `RegisterUnaryLongLivingCallback`, others pass wrong vehicle-count arguments to RoutingIndexManager).
- Failures are API misconceptions and input parsing, verified in the stderr (old/non-existent names such as
  `pywrapcp.RoutingModel.DefaultRoutingSearchParameters`, `routing_enums_pb2.RoutingSearchParameters`; `n, capacity = ...` ignoring K),
  not harness issues (a correct program reaches 30/30).
- **Efficiency:** best-of-3 with a label-free choice (smallest objective among feasible outputs) reaches 1.00 at ≈ 3–5k tokens; thinking gets .97
  at 12k. Here errors at 14B/32B are independent slips, so sampling wins (X1 rule).
- 8B cannot do CVRP: even with the snippet .03–.07, runtime errors dominate; thinking only reaches .17 at ≈ 19k tokens.

## R1-Distill-Llama-70B on the hard geometry tasks (T=0.6, no toolbox): lattice 57/60, rectunion 54/60

- Llama-3.3-70B (same base family, no reasoning) scored 0 / 0–1. **Reasoning distillation fixes the hard tasks in the Llama family too**: the
  reasoning gate holds across families, not only for Qwen3's thinking mode. (K8 arm running.)


## 11:25 update: CVRP (rest) + Llama family on CVRP + R1 with helpers

**CVRP, opt of 30** (solver arm, repair 2):

| model | no doc | full sheet | snippet s1/s2/s3 | best-of-3 | snippet + B=2048 | snippet + thinking | no doc + thinking |
|---|---|---|---|---|---|---|---|
| 14B | .20 | .20 | .73/.70/.80 | 1.00 | **.93** @ 3.3k | .97 @ 13.3k | (running) |
| 32B | .23 | .07 | .83/.77/.90 | 1.00 | .83 @ 3.8k | .97 @ 12.2k | **.03** @ 15.4k |
| Llama-3.3-70B | .40 | .60 | **.93/.87/.83** @ 0.7k | **1.00** @ 2.2k | – | – | – |
| R1-Distill-Llama-70B | (running) | – | .90 @ 6.4k | – | – | – | – |

- **Thinking cannot replace the missing fact:** 32B with thinking but no documentation reaches .03 (15k tokens/program); it still calls
  non-existent routing methods (`RegisterUnaryC…`/`RegisterUnaryL…`, 14 programs). With the snippet, the same model reaches .83 without thinking.
- **Llama-70B confirms the snippet effect in another family** (.40 → .60 full sheet → .83–.93 snippet; best-of-3 1.00) at the lowest cost of all
  (≈ 0.7k tokens per program). Its no-doc failures are mostly a wrong `AddDimensionWithVehicleCapacity` call (12 programs).
- Efficiency ranking on CVRP (14B): snippet + 2k thinking .93 @ 3.3k ≈ best-of-3 1.00 @ 3.3k > full thinking .97 @ 13k.

**R1-Distill-Llama-70B + 8 extra helpers on the hard tasks:** lattice 42/60 (vs 57 without helpers), rectunion 48 (vs 54).
- **The signed-area trap catches the reasoning model too:** all 16 lattice transform-only failures use `polygon_area2` without abs (53/60 programs
  take the helper). Qwen3 thinking + K8 lost only 1–4 there. So reasoning protects against plausible-but-unneeded helpers, but not reliably
  against a needed helper with a hidden contract. Queued (queue_signthink.sh): Qwen3 32B/8B with thinking, K0 signed vs abs, to test this directly.


## 12:25: does thinking avoid the signed-area trap? (lattice, K0 = only `polygon_area2`, thinking on, T=0.7 s1, of 60)

| model | signed helper | abs helper |
|---|---|---|
| Qwen3-32B think | 59 (1 transform-only) | 59 (1 crash) |
| Qwen3-8B think | **52** (8 transform-only) | 60 |
| R1-Distill-Llama-70B (K8, T=0.6) | 42 (16 transform-only, all signed w/o abs) | – |
| (no thinking: 8B / 32B) | 2–3 / 9–15 | 14–15 / 46–49 |

- Qwen3 thinking mostly handles the sign (all 59/60 programs mention abs), 8B still slips on 8. R1-Distill is caught much more often.
  So reasoning reduces but does not remove the hidden-contract hazard; an unsigned helper removes it for every model.

**CVRP without documentation + thinking:** 14B .33 (18.5k tokens/program), 32B .03, R1-Distill-Llama-70B .00 (10.9k). With the snippet:
14B .97, 32B .97, R1 .90. **The fact, not more reasoning, is what fixes API-knowledge failures** (same as T4, now on a realistic problem
and a reasoning model).


## 13:25: E4 pre-registered similarity test (docs/prereg/PREREG_E4.md) + logit probe v2 (poc/logit_probe2.py)

**E4 (full table and verdicts in PREREG_E4.md).** P1 confirmed on hull only (HIGH−LOW −50 points at 8B and 32B; 14B −23), reversed on area2 at 32B;
P2 refuted (LOW helpers also cost 32B 15–27 points, partly via the `on_segment` dependency); P3 confirmed for hull (`polar_sort` called in
65–93% of HIGH programs, accuracy 97 → 8 / 83 → 6), refuted for area2 (no hull detour). Conclusion: one algorithm-naming helper is enough for
a near-total collapse, but a priori "similarity" labels do not predict harm across tasks.

**Logit probe v2: 180 sampled programs per condition (hull/area2/close), each teacher-forced under both prompts:**

| | 8B | 14B | 32B |
|---|---|---|---|
| preference shift (K8-style vs K0-style code, K8 vs K0 prompt), nats/token | **+0.71** | +0.54 | +0.40 |
| instances with a positive shift | 100% | 100% | 100% |
| K8 program, mean lp/token under K0 → K8 prompt | −0.55 → −0.02 | −0.44 → −0.03 | −0.36 → −0.07 |
| K0 program, mean lp/token under K0 → K8 prompt | −0.03 → −0.20 | −0.02 → −0.15 | −0.07 → −0.18 |
| Δ on K8 programs, first decile / last decile (nats per program) | +139 / +2 | +64 / +2 | +47 / +2 |
| Δ on K8 programs: helper-definition copies / own code | +433 / +14 | +144 / +30 | +122 / +16 |
| top-5 entropy per token, K0 program under K0 → K8 | .037 → .047 | .031 → .049 | .096 → .133 |
| top-5 entropy per token, K8 program under K0 → K8 | .103 → .027 | .066 → .042 | .167 → .103 |

- **The toolbox flips which program is "natural":** without the toolbox, the model's own K8 program loses 0.3–0.5 nats per token (≈1.4–1.7×
  per token, compounding to many orders of magnitude over a ~500-token program); with the toolbox, its K0 program loses 0.1–0.2 nats per token. The shift is positive for every one of 180 instances at every size, and it shrinks with model size
  (8B > 14B > 32B), matching the behavioural harm.
- **The decision is made at the top of the program.** Most of the shift sits in the first 10% of tokens and decays to ≈0 at the end;
  the tokens gaining most under K8 are the imports and names of the helper route (`functools` for polar_sort's `cmp_to_key`, `orient`, `dist`,
  `polar`, `convex`, `polygon`). Once the route is chosen, the rest of the program is about equally likely under both prompts.
- **Copying inflates whole-program scores:** most of the raw Δ is the verbatim helper definitions (+122 to +433 nats); the model's own code
  carries +14 to +30. (This was review item 9's concern about v1; v2 separates the two.)
- **Certainty, not confusion:** under the toolbox the helper-route program is generated with *lower* entropy (8B .103 → .027), while the
  textbook program becomes less certain. The toolbox does not make the model hesitant; it makes it confidently follow the helper route.


## Queued 13:30: does retrieval (RAG) fix the problems? (queue_rag.sh; 8B / 32B / Llama-70B)

- **CO, BM25 over a titled snippet library** (7 problem snippets + general CP-SAT reference + 8 extra API lines; query = problem text).
  Retrieval quality was checked offline first: with titles, top-1 is the right snippet for every instance (≈ the oracle condition), and top-3 adds a
  near-miss (CVRP → +TSP snippet; knapsack → +bin-packing) plus an unneeded API line. Without titles (code-only chunks), top-1 is an unneeded API
  line for 6 of 7 problems and the knapsack snippet is never in the top-3. Arms: titled top-1 / titled top-3 / code-only top-3.
- **Geometry, text hints instead of helper code** (`--algo_hint`): Pick's theorem for lattice, sweep line for rectunion, monotone chain for hull;
  hull also with the E4 HIGH helpers (polar_sort, collinear) + hint, to test whether a text hint counters the helper steering.


## 14:25: RAG results (queue_rag.sh)

**Optimization, BM25 retrieval over the snippet library** (opt rate; 360 main+held-out instances / 30 CVRP; solver arm, repair 2, T=0.7 s1):

| model | no doc | oracle snippet | titled top-1 | titled top-3 (+ near-miss + extra) | code-only top-3 (weak retriever) |
|---|---|---|---|---|---|
| 8B (6 problems) | .21 | .67 | .68 | .64 | .61 |
| 32B (6 problems) | .67 | .96 | **.97** | .93 (binpack .67 vs .93) | .90 (binpack .54) |
| Llama-70B (6 problems) | .43* | .87 | .85 | .83 | .85 |
| 8B CVRP | .00 | .03 | .00 | .13 | .00 |
| 32B CVRP | .23 | .83 | .70 | **.57** (CVRP + TSP snippet) | .53 |
| Llama-70B CVRP | .40 | .93 | .93 | .93 | .87 |
(*Llama no-doc main problems from the older n_inst-6 run, 192 instances.)

- **Precise retrieval ≈ the hand-written snippet:** with titled pages, top-1 is always the right snippet, and accuracy matches the oracle
  (32B .97 vs .96, 8B .68 vs .67, Llama .85 vs .87). So the T4 "oracle" fix is deployable when the documentation has good titles.
- **Extra retrieved chunks cost a little overall, a lot on specific problems:** top-3 adds a near-miss snippet. 32B bin packing .93 → .67
  (bin packing + vertex-cover snippet), 32B CVRP .83 → .57 (CVRP + TSP routing snippet). Precision matters more than recall, as in geometry.
- **Even a weak retriever beats no documentation by a wide margin** (8B .21 → .61, 32B .67 → .90): in optimization, a noisy reference is far
  better than none, except where a near-miss replaces the right page (the full-sheet CVRP case, .07).
- Llama-70B is the least sensitive to extra chunks (.83–.85 for all retrieval variants).

**Geometry: a TEXT algorithm hint instead of helper code** (correct of 60, T=0.7 s1, no toolbox unless stated):

| model | lattice: none → hint | rectunion: none → hint | hull: K0 / hint only | hull: HIGH helpers (polar_sort, collinear) → HIGH + hint |
|---|---|---|---|---|
| 8B | 12 → **59** | 8 → 29 | 59 / 60 | 4 → **58** (polar_sort called 41 → 0) |
| 32B | 44 → **59** | 22 → 47 | 50 / 55 | 3 → **52** (polar_sort 56 → 0) |
| Llama-70B | 0 → **55** | 0 → 18 | – / 47 | 28 → 33 (polar_sort 41 → 31) |

- **A one-sentence algorithm description does what helper code could not:** Pick's theorem takes the lattice task to 55–59 of 60 in both
  families (Llama-70B 0 → 55). The sweep-line hint helps less (rectunion 18–47): knowing the algorithm is not the same as implementing it.
- **A text hint overrides the helper steering for Qwen:** with the HIGH helpers present, adding "use Andrew's monotone chain" brings 8B from
  4 → 58 and 32B from 3 → 52, and `polar_sort` is no longer called at all. This is direct causal evidence that the harm comes from the
  *algorithm choice*: name the algorithm and the same helpers stop hurting. Llama-70B keeps following the helpers (31 of 60 still call polar_sort).
- These hints are oracle (hand-written per task). Queued (queue_selfhint.sh): the deployable versions, the model naming its own algorithm
  first (self-hint) and BM25 retrieval from an 11-entry algorithm library. Offline check: plain BM25 on the task text retrieves the right entry only
  for rectunion and closest pair; hull and lattice get "ray casting", area2 gets "Pick's theorem" (realistic misfires, not tuned).


## 15:25: non-oracle hints — the model's own plan (self-hint) and retrieved hints (queue_selfhint.sh; correct of 60, T=0.7 s1)

| model | lattice: none / oracle hint / self-hint / retrieved ("ray casting") | rectunion: none / oracle / self / retrieved ("sweep line", correct) | hull + HIGH helpers: none / oracle / self / retrieved ("ray casting") |
|---|---|---|---|
| 8B | 12 / 59 / **44** / 15 | 8 / 29 / 14 / **38** | 4 / 58 / 27 / 7 |
| 32B | 44 / 59 / **55** / **3** | 22 / 47 / 24 / 44 | 3 / 52 / 21 / 3 |
| Llama-70B | 0 / 55 / **0** / 0 | 0 / 18 / 4 / 14 | 28 / 33 / 40 / 33 (no helpers: 47) |

- **Self-hint works only when the model knows the right algorithm.** Asked to name the algorithm first, Qwen names Pick's theorem in 60/60
  plans and the lattice task improves (8B 12 → 44, 32B 44 → 55); Llama-70B names it in only 4/60 and stays at 0. You cannot self-retrieve
  knowledge you don't have. Plans cost ≈ 550 tokens (vs ≈ 1–8k for thinking).
- **Naming an algorithm is not the same as implementing it:** every rectunion plan names a sweep line, but accuracy barely moves (8 → 14,
  22 → 24); the hand-written hint, which spells out "merge the y-intervals per slab", does much better (29 / 47).
- **Self-planning can lock in the fragile algorithm.** For hull, 32B's own plan names the Graham scan in 60/60 (the textbook name), which
  matches the harmful `polar_sort` helper: it is still called in 52/60 and accuracy is 21 (vs 52 with the monotone-chain hint).
- **A wrong retrieved hint is destructive:** BM25 on the task text retrieves "ray casting" for lattice, and 32B drops from 44 to **3** of 60
  (it brute-forces with ray casting and mishandles the boundary). A correct retrieval (sweep line for rectunion) works as well as or better than the
  hand-written hint (8B 38 vs 29). A near-miss can carry a useful sub-fact: area2 with the retrieved Pick note (which says "exact integer
  shoelace, absolute value") goes 42 → 56 (8B), 56 → 59 (32B), 42 → 45 (Llama).
- Net: text hints are powerful in both directions. Retrieval quality decides the sign; self-hints help only within the model's own knowledge.

## E5 started (15:30): can robustness to irrelevant helpers be learned? (self-distillation, LoRA)

Plan: Qwen3-8B with thinking (robust) writes programs for 1800 TRAINING prompts on instances disjoint from all eval instances
(5 core tasks, K = 0/4/8, `--inst_prefix train-`); keep oracle-correct programs; LoRA-SFT Qwen3-8B *without thinking* on (prompt → program)
in two arms with equal size: (a) mixed K0/K4/K8 prompts, (b) clean K0 prompts only. Eval without thinking on the standard n=300 K0/K8
sets and the held-out tasks. Question: does the fast no-think model inherit the robustness (efficiency: thinking-level accuracy at no-think cost),
and does that require distractor-laden training prompts?


## 17:25: E5 results — robustness to irrelevant helpers CAN be distilled into the no-thinking model, but only task-specifically

Setup: Qwen3-8B with thinking wrote programs for 1,800 training prompts (instances disjoint from eval; 596 / 585 / 582 of 600 correct for K0 / K4 / K8).
LoRA r=16 on Qwen3-8B, 2 epochs, 600 examples each: **mixed** (200 each from K0 / K4 / K8 prompts) vs **clean** (K0 prompts only).
Train loss starts at ≈0.05 (self-distillation: the programs are already likely under the student). Eval without thinking, T=0.7 s1;
% correct on all 8 variants; paired differences vs base with 95% bootstrap CIs.

| eval set | base | clean LoRA | mixed LoRA | mixed − base |
|---|---|---|---|---|
| main 5 tasks, K0 (n=300) | 92.7 | 98.7 | **99.7** | +7.0 [+4.0, +10.3] |
| main 5 tasks, **K8** (n=300) | 76.0 | 75.3 | **97.7** | **+21.7 [+17.3, +26.3]** |
| held-out convex/tri/overlap, K0 (n=180) | 60.6 | **73.9** | 66.7 | +6.1 [−1.7, +13.3] |
| held-out, K8 (n=180) | 56.7 | 55.0 | 52.8 | −3.9 [−11.7, +3.3] |
| hard lattice/rectunion, no toolbox (n=120) | 22.5 | 13.3 | 31.7 | +9.2 [−0.9, +20.0] |
| CO scoped snippet (84 inst, opt rate) | .69 | .70 | .69 | 0 |

Per task under K8 (base / clean / mixed): hull 15 / 17 / **90**, close 82 / 97 / 100, area2 97 / 63 / 100, segs 87 / 100 / 98, pip 100 / 100 / 100.
Mean output tokens under K8: 808 / 676 / **350**; programs calling an offered distractor: 252 / 203 / **92** of 300.

- **Robustness is learnable, and it needs distractor-laden training prompts.** The mixed LoRA reaches 97.7 under K8, the level of full thinking
  (8B thinking K8 ≈ 97–98) at ≈ 350 output tokens instead of ≈ 6k, i.e. ~17× cheaper. The clean LoRA, trained on the same number of verified
  programs from the same teacher, gains nothing under K8 (−0.7). So it is not "better code" in general: the model learned to ignore helpers.
- **It does not transfer to unseen tasks.** On the held-out tasks with K8 the mixed LoRA is no better than base (52.8 vs 56.7; convex
  63 → 38). What was learned is "for these 5 tasks, keep the textbook program", not a general skill of ignoring irrelevant helpers.
  (Clean prompts do transfer some general coding habits: held-out K0 tri 15 → 55.)
- No collateral damage on optimization code (.69 / .70 / .69).
- Queued (queue_e5loto.sh): leave-one-task-out LoRAs (train on 4 tasks, eval the 5th) to measure transfer cleanly, plus base seed 2.


## 18:25: E5b leave-one-task-out (train the mixed LoRA on 4 tasks, eval the 5th; seeds 1–2, 60 programs × 2 per cell, % correct)

| held-out task | K0: base → LOTO (Δ [95% CI]) | K8: base → LOTO (Δ [95% CI]) | K8 with the task in training (mixed LoRA) |
|---|---|---|---|
| hull | 97 → **34** (−62.5 [−70.8, −52.5]) | 15 → 21 (+5.8 [−4.2, +15.0]) | 90 |
| area2 | 77 → 62 (−15.0 [−26.7, −3.3]) | 97 → 99 (+2.5) | 100 |
| pip | 100 → 100 | 100 → 99 | 100 |
| segs | 92 → 88 | 88 → 88 | 98 |
| close | 100 → 100 | 86 → **98** (+11.7 [+5.0, +18.3]) | 100 |
| pooled K8 | | 77.0 → 80.8 | 97.7 |

- **The robustness is task-specific, as the held-out-task result suggested:** with the task left out of training, K8 accuracy barely moves
  (pooled 77.0 → 80.8; only closest pair gains, +11.7), while including the task gives 90–100.
- **Narrow fine-tuning can damage an unseen task.** The LoRA trained without hull drops hull from 97 to 34 *on clean prompts*: 40 of its 41 correct
  programs are monotone chains, but of the 79 failures only 16 are (broken) monotone chains: 22 are Graham-scan variants and 41 other ad hoc loops. The fine-tune moved
  the model off its textbook idiom on a task it never trained on (area2 K0 also −15). Self-distillation on a few tasks is not a free efficiency
  win: it buys robustness where it trained and can cost accuracy elsewhere.
- Base model seed 2 replicates seed 1 (main K0 93.3 vs 92.7, K8 78.0 vs 76.0).
- Queued (queue_repl.sh): seed-2/3 replications of E5 mixed, the T8 text hints, and the RAG results.


## 19:25: replications (seeds 1–3 for hints, 1–2 for E5 and RAG); paired 95% CIs over instances × seeds

| result | before → after | Δ [95% CI] |
|---|---|---|
| hull with HIGH helpers → + monotone-chain hint, 8B (n=180) | 7.2 → 94.4 | +87.2 [+81.7, +91.7] |
| same, 32B | 5.0 → 87.8 | +82.8 [+77.2, +87.8] |
| same, Llama-70B | 46.7 → 59.4 | +12.8 [+3.3, +21.7] |
| lattice, no hint → Pick hint: 8B / 32B / Llama-70B | 19.4 / 71.1 / 0.0 → 99.4 / 98.9 / 86.7 | +80.0 / +27.8 / +86.7 |
| rectunion, no hint → sweep hint: 8B / 32B / Llama-70B | 18.9 / 43.3 / 0.6 → 55.0 / 76.1 / 30.0 | +36.1 / +32.8 / +29.4 |
| E5 mixed LoRA, main K8 (n=600) | 77.0 → 98.0 | +21.0 [+17.8, +24.3] |
| E5 mixed LoRA, main K0 (n=600) | 93.0 → 99.8 | +6.8 [+4.8, +9.0] |
| E5 mixed LoRA, held-out K8 (n=360) | 58.6 → 52.2 | **−6.4 [−12.2, −0.6]** |

RAG, 2 seeds (opt rate): 32B titled top-1 .965 (oracle snippet .956), top-3 .912 (bin packing .59 vs .89; CVRP .55 vs .78);
Llama-70B top-1 .846 / top-3 .838 (CVRP .97 / .93). All seed-1 conclusions hold; the E5 held-out effect is now a small but significant *loss*.


## 22:25: E5c (task diversity) and E5d (prompt-format generalization)

**E5c: 9-task leave-one-out** (mixed LoRA on the other 9 geometry tasks, 600 examples ≈ 55–80 per task; % correct; Δ vs base [95% CI];
K8 seeds 1–2, K0 seeds 1–2 for hull, seed 1 for convex/tri):

| unseen task | K0: base → 9-task LOTO | K8: base → 9-task LOTO | earlier: 4-task LOTO (hull) / 5-task mixed (convex, tri unseen) |
|---|---|---|---|
| hull | 97 → **28** (−68.3 [−76.7, −59.2]) | 15 → 10 (−5.0) | K0 97 → 34, K8 15 → 21 |
| convex | 70 → 58 (−11.7 [−28.3, +6.7]) | 68 → **34** (−33.3 [−44.2, −23.3]) | K0 70 → 62, K8 68 → 39 |
| tri | 15 → 7 (−8.3) | 12 → 28 (+15.0 [+5.0, +24.2]) | K0 15 → 42, K8 12 → 32 |

- **More task variety does not buy transfer.** Training on 9 tasks instead of 4 leaves the unseen task's K8 accuracy unchanged or worse, and the
  damage on clean hull prompts stays (97 → 28). Convex under K8 drops by a third in both versions. Only `tri`, where the base model is very weak
  (12–15), improves, plausibly from general exact-integer habits rather than helper robustness.

**E5d: is the in-task robustness tied to the training prompt format?** (main 5 tasks, n=300, s1; base → E5 mixed LoRA)

| condition (never seen in training) | base → mixed | Δ [95% CI] |
|---|---|---|
| neutral header ("available", no instruction), K8 | 78 → 97 | +19.3 [+15.0, +24.0] |
| K = 10 (more helpers than any training prompt) | 77 → 98 | +21.0 [+16.0, +26.0] |
| 6 unrelated (non-geometry) helpers | 94 → 100 | +6.0 [+3.3, +9.0] |
| prelude header (helpers pre-defined), K8 | 78 → 96 | +18.0 [+13.7, +22.3] |

- **Within the trained tasks the robustness is format-independent**: other headers, more helpers and unrelated helpers all keep the gain. So
  the LoRA did not memorise a prompt template; it learned, per task, to keep the robust program whatever the toolbox looks like.
- **E5 summary:** robustness to irrelevant helpers distils into the fast model *per task* (+21 points, thinking-level, ≈17× fewer tokens, robust
  to prompt format), but neither 4 nor 9 training tasks give transfer to an unseen task, and narrow fine-tuning repeatedly damages fragile
  unseen tasks (hull 97 → 28–34 on clean prompts, convex K8 68 → 34–39). Practical reading: distil for the task family you deploy on,
  and re-validate every other task.


## 23:25: E5e — is the damage an over-training effect? (4-task leave-hull-out LoRA, lighter training; seed 1, % correct)

| training | unseen hull K0 | unseen hull K8 | 4 trained tasks under K8 (in-task gain; base 91.2) |
|---|---|---|---|
| base (no LoRA) | 98 | 15 | 91.2 |
| full: r=16, lr 1e-4, 2 epochs, 600 ex. (E5b) | 35 | 22 | (5-task mixed LoRA: 99.6) |
| A: 1 epoch | 32 | 23 | 96.2 |
| B: r=4, lr 5e-5, 1 epoch | **100** | 17 | **81.2** (area2 97 → 35: prints the area instead of twice the area) |
| C: 150 examples, 2 epochs | 70 | 17 | 94.6 |

- **Damage and gain move together.** The light LoRA (B) leaves hull intact but gives no in-task robustness, and it even breaks area2
  (39 of 60 programs divide by 2, misreading "twice the area"); half the steps (A) keeps the gain and the damage; a quarter of the data (C)
  sits in between. No setting tried gives the gain without side effects: any update strong enough to change the helper behaviour also moves
  nearby task idioms. Fine-tuning for robustness needs task-wide re-validation (or replay data from the tasks that must not change).

## New family: OpenAI gpt-oss (20b / 120b) serves on vLLM 0.10.2 (A100), with adjustable reasoning effort

`poc/llm.py` now forwards `POC_REASONING_EFFORT` (low/medium/high) as `reasoning_effort`. Smoke test (20b, convex-hull prompt): low effort
641 tokens / 6 s, medium 807 tokens / 5 s, both return a clean ```python block (reasoning in a separate channel). Queued next: the core
suite on gpt-oss-20b/120b (review item 5, a third model family and a natively reasoning one).


## 00:25: gpt-oss results (third family, natively reasoning; T=0.7 s1)

**Geometry** (% correct, n=300; tokens = mean output incl. reasoning):

| model / effort | K0 | K8 | Δ [95% CI] | tokens K0 / K8 | hard: lattice / rectunion (of 60) | lattice + signed helper (of 60) |
|---|---|---|---|---|---|---|
| 20b low | 99.3 | 98.3 | −1.0 [−2.7, +0.7] | 428 / 877 | 60 / 57 | 60 |
| 20b medium | 98.7 | 99.3 | +0.7 [−1.0, +2.3] | 1266 / 1319 | 60 / 59 | 60 |
| 120b low | 99.3 | (94.7)* | | 688 / 955 | 56 / 58 | 58 |
| 120b medium | 99.7 | (86.7)* | | 1277 / 1424 | 60 / 60 | 58 |
*120b K8 is **invalid as measured**: 16 / 38 programs were scored "no code" because the answer ended with an extra unbalanced fence
("```\n```") that broke `last_block`'s fence pairing. A scan of all 79,260 stored geometry rows finds 57 such rows in total, 54 of them in
these two files, so no earlier result is affected. `last_block` now falls back to the last tagged opening fence; 120b K8 is being re-run.

- **gpt-oss is robust to irrelevant helpers even at low effort** (20b: −1.0 / +0.7), solves both hard tasks (56–60 of 60, where non-reasoning
  Qwen/Llama score 0–44), and does not fall into the signed-area trap (58–60 of 60). Low effort costs ≈ 430–880 tokens, about the cost of a
  non-thinking Qwen program, so a natively reasoning model gives the robustness of Qwen thinking at non-thinking cost.

**Optimization** (opt rate; 6 problems, n_inst 6 = 120 instances; CVRP 30): no doc → scoped snippet

| model / effort | 6 problems | CVRP |
|---|---|---|
| 20b low | .93 → **1.00** | .67 → .93 |
| 20b medium | .94 → **1.00** | .80 → **1.00** |
| 120b low | .95 → **1.00** | .87 → **1.00** |
| 120b medium | **1.00** (no doc) | (running) |

- gpt-oss knows OR-Tools far better than Qwen/Llama (no doc .93–1.00 vs .21–.67), yet the snippet still closes the remaining gap to 1.00
  (CVRP .67–.87 → .93–1.00). The "state the API fact" fix holds for the strongest family tested, with less headroom.


## 01:25: gpt-oss-120b K8 re-run with the fixed extractor; high effort

- 120b K8 after the `last_block` fix: low 93.3 (Δ −6.0 [−9.0, −3.3]), medium 86.0 (Δ −13.7 [−17.7, −10.0]); still 17 / 40 rows without an
  extractable code block, so the fence fallback did not cover these cases. Diagnosing with raw outputs (re-sampling the failing prompts);
  until then the 120b K8 drop is **not** counted as a helper effect.
- **20b high effort runs away:** 80 of 300 K0 programs hit the 24k-token cap inside the reasoning (finish = length, no answer); the 220 that
  finish are all correct. Mean 11.7k tokens (median 7.8k). High effort buys nothing here and costs 10–25× the tokens of low effort.
- 120b medium CVRP: no doc .97, snippet 1.00.
- **Cause of the remaining 120b "no code" rows found (02:05):** the answer opens the code block twice ("```python\n```python\n<code>```\n```").
  The fence regex then pairs the two openings into an EMPTY python block, which `last_block` returned as the program. Fix: skip empty
  blocks, then the tagged-fence fallback recovers the code (verified on the captured failing output: 1,346-char program extracted). Only
  57 of 79,260 stored geometry rows have no code at all, so earlier models are unaffected. 120b K8 low/medium are re-run (queue_ossfix2.sh).


## 02:25: gpt-oss reasoning-effort frontier + documentation variants

**Effort frontier, geometry K0 (n=300; % correct @ mean output tokens; capped = reasoning hit the token limit, no answer):**

| model | low | medium | high |
|---|---|---|---|
| 20b | 99.3 @ 0.43k | 98.7 @ 1.3k | **73.3 @ 11.7k** (80 capped at 24k; all 220 finished programs correct) |
| 20b, K8 | 98.3 @ 0.88k | 99.3 @ 1.3k | 76.0 @ 12.7k (72 capped) |
| 20b, hard tasks (of 120) | 117 | 119 | 80 (39 capped) |
| 120b | 99.3 @ 0.69k | 99.7 @ 1.3k | 99.3 @ 4.9k (2 capped) |

- **Low effort is the efficient point**; high effort makes 20b reason without stopping in about a quarter of the problems. In accuracy per token,
  gpt-oss-20b low (≈ 99% at ≈ 0.4–0.9k tokens) beats every Qwen/Llama configuration we measured, including Qwen3 thinking (≈ 97% at ≈ 6k).

**Documentation for a strong model (gpt-oss-20b low; opt rate, 6 problems / CVRP):** no doc .93 / .67, full sheet .97 / .93, BM25 top-3
(with near-misses) .98 / .97, scoped snippet 1.00 / .93. Unlike Qwen-32B (near-miss top-3 cost up to 26 points), the strong model is not
hurt by extra or near-miss chunks; any relevant reference helps.


## 03:25: gpt-oss-120b K8 after the second extractor fix — the "helper harm" was entirely an extraction artifact

| model / effort | K0 | K8 (fixed extractor) | Δ [95% CI] | no-code rows |
|---|---|---|---|---|
| 120b low | 99.3 | 98.7 | −0.7 [−2.3, +1.0] | 0 (was 17) |
| 120b medium | 99.7 | 99.7 | 0.0 [−1.0, +1.0] | 0 (was 40) |
| 20b low, seed 2 | 98.7 | 98.3 | −0.3 [−2.3, +1.7] | 0 |
| 20b medium, seed 2 | 99.3 | 98.7 | −0.7 [−2.3, +1.0] | 0 |

- The earlier 120b K8 numbers (94.7 / 86.7, then 93.3 / 86.0) are **retracted**: they were the doubled-fence extraction bug, not the model.
  **gpt-oss (both sizes, all efforts that finish) is not hurt by irrelevant helpers.** Lesson for the harness: every new model family needs an
  extraction audit (rows with no code, by finish reason) before its numbers are trusted.
- Seed-2 CO for 20b replicates (no doc → snippet: low .93 → .98, CVRP .60 → 1.00; medium .97 → 1.00, CVRP .80 → 1.00).

## 03:45: polygon clipping task added ("clip", review item 3 "still open: polygon clipping")

Twice the exact area of the intersection of two convex polygons, printed as an irreducible fraction p/q (all 60 identity answers are
non-integral). Oracle = Sutherland–Hodgman with `Fraction`; verified symmetric (A∩B = B∩A) and against Monte-Carlo estimates on 60/60;
all 8 variants consistent (scale ×9 handled in the MR check; degenerate = exact vertex touch → 0). Reference passthrough 480/480, MR
false alarms 0/60. Runs queued (queue_clip.sh) on Qwen 8B/32B, gpt-oss-20b low, Llama-70B: no toolbox ×3 seeds, K0, K8, text hint, thinking.


## 04:25: polygon clipping results (first pass; correct of 60 on all 8 variants, T=0.7)

| model | no toolbox s1/s2/s3 | K0 (orient) | K8 | text hint (Sutherland–Hodgman) | thinking | MR-select over 3 samples |
|---|---|---|---|---|---|---|
| Qwen3-8B | 0 / 0 / 0 | 0 | 0 | 0 | **20** (15.6k tok) | 0 |
| Qwen3-32B | 0 / 0 / 0 | 0 | 2 | 0 | (running) | 0 |
| gpt-oss-20b low | 15 / 16 / 12 | 14 | 13 | **41** | – | **28** (= oracle-any 28: every solvable instance found, 0 wrong picks) |

- **The hardest task so far**: Qwen without thinking solves none of 360 programs in any condition, even with the algorithm spelled out (the
  hint makes every program use `Fraction`, but the clipping logic is still wrong: e.g. 32B returns 18995280751471724234/17378631478774559 for 69721/85).
  Thinking gets 8B to 20/60.
- **gpt-oss fails on orientation, which the metamorphic check catches.** 35 of its 45 failures (s1) are transform-only: correct on the original
  polygons, 0 on the mirrored / reversed ones, because the program assumes counter-clockwise input (the same hidden-orientation hazard as the
  signed-area trap). Since the failure is variant-dependent, MR-select over 3 samples nearly doubles accuracy (28 vs 12–16).
- The text hint (which says "orient both polygons counter-clockwise") takes gpt-oss from 15 to 41: it names exactly the step the model skips.
- 120b high K8 (fixed extractor): 294/300 (6 capped). Queued (queue_clip2.sh): hint + MR together, gpt-oss medium effort, 120b.


## 05:25: polygon clipping — fixes compose (correct of 60; seeds 1/2/3; MR = metamorphic selection over the 3 seeds)

| model | no toolbox | + hint | MR-select (no hint) | **hint + MR-select** | tokens/program (no hint / hint) |
|---|---|---|---|---|---|
| gpt-oss-20b low | 15 / 16 / 12 | 41 / 46 / 45 | 28 | **59** | 948 / 925 |
| gpt-oss-20b medium | 52 / 51 / 50 | 57 / 60 / 57 | 59 | **60** | 2520 / 2335 |
| gpt-oss-120b low | 28 / 29 / 24 | 58 / 60 / 60 | 51 | **60** | 1680 / 1336 |
| gpt-oss-120b medium | 54 / 50 / 53 | 54 / 60 / 60 | 60 | **60** | 3652 / 3324 |
| Qwen3-32B | 0 / 0 / 0 | 0 | 0 | – | thinking: 24 (14.4k tok) |
| Llama-70B | 1 / 0 / 0 | 2 | – | – | – |

- **The three cheap fixes compose on the hardest task:** gpt-oss-20b at low effort goes 14 (single) → 44 (+ one-sentence hint) → **59 / 60**
  (+ hint + 3 samples with the label-free metamorphic check) at ≈ 2.8k tokens in total, matching medium effort + check (59) and beating a
  single medium-effort program (51) at similar cost. The check never picks a wrong program (MR-select = oracle-any in every row).
- The orientation bug (transform-only failures: 35 → 15 → 0–1) is exactly what the hint names and what the check detects.
- Non-reasoning models are at the floor (Qwen-32B 0/180, Llama-70B 1/180) and the hint does not lift them; Qwen thinking reaches 20–24.

## 05:50: VRPTW added (review item 3, "time windows")

Capacitated VRP with time windows (service 10, travel time = rounded distance, return by horizon H; windows built around a greedy schedule so
every instance is feasible). Exact CP-SAT reference (multiple circuits + load + arrival-time propagation), all 30 proven optimal; verified
against brute force on 8/8 six-customer instances. A correct OR-Tools program (time dimension + capacity dimension) is optimal on 20/20
through the harness. New `--api_doc_as` flag gives a near-miss reference (the CVRP snippet, which lacks the time dimension). Runs queued
(queue_vrptw.sh): Qwen 8B/32B, Llama-70B, gpt-oss-20b low × no doc / full sheet / CVRP snippet / VRPTW snippet ×3 / snippet + thinking.


## 06:25: VRPTW results (30 instances, opt rate; feasible rate in brackets; best-of-3 = label-free min objective over snippet seeds 1–3)

| model | no doc | full sheet | near-miss CVRP snippet | VRPTW snippet s1/s2/s3 | best-of-3 | snippet + thinking |
|---|---|---|---|---|---|---|
| Qwen3-8B | 0 (0) | 0 (0) | 0 (0) | 0 / 0 / 0 | 0 | 0 |
| Qwen3-32B | 0 (0) | 0 (0) | 0 (0) | .27 / .10 / .27 (feas .47–.60) | .47 | (running) |
| Llama-70B | 0 (.03) | 0 (.07) | 0 (.07) | **.60 / .77 / .60** | **.93** | – |
| gpt-oss-20b low | .10 (.23) | .07 | .07 | .13 / .07 / .17 | .37 | – |

- **Only the exact snippet works; a near-miss reference is as useless as none.** The CVRP snippet (same routing API, no time dimension) gives
  0 for every non-reasoning model; the full sheet too. Llama-70B goes 0 → .60–.77 with the VRPTW snippet and .93 with best-of-3; Qwen-32B
  0 → .10–.27 (.47). Failures without it are invented/misused time-dimension calls (`GetDimension…`, `AddDimension` argument errors).
- **gpt-oss-20b (low) fails on input format, not on the API:** 23/30 snippet programs read only 4 of the 5 header fields (`n capacity K
  horizon`, skipping the stated `service`), so horizon = 10 and the first time-window `SetRange` raises "CP Solver fail". A stated input
  format skimmed at low effort, the same kind of hidden-assumption error as its counter-clockwise assumption in clipping. Queued: gpt-oss
  medium effort and 120b (queue_vrptw2.sh) to see whether more reasoning fixes it.


## 07:35: VRPTW follow-up (queue_vrptw2): more reasoning helps 20b, the larger 120b is worse; the cause is one skipped header field

opt rate of 30 (feasible in brackets); best-of-3 = label-free min objective over the 3 snippet seeds. Mean output tokens incl. repairs.

| model | no doc | VRPTW snippet s1 / s2 / s3 | best-of-3 | programs that parse `service` (snippet runs) | tokens |
|---|---|---|---|---|---|
| gpt-oss-20b low (06:25) | .10 (.23) | .13 / .07 / .17 | .37 | 7 / 90 | ~4.5k |
| **gpt-oss-20b medium** | .33 (.50) | **.70 / .57 / .63** | **.90** | 66 / 90 | 8.8–10.2k |
| gpt-oss-120b low | .07 (.07) | 0 / 0 / 0 | 0 | 0 / 90 | 4.5k |
| gpt-oss-120b medium | .13 (.13) | .07 / .03 / (s3 running) | – | 3 / 60 | 9.8k |
| Qwen3-32B snippet + thinking | – | .10 (.13), 9/30 no output | – | – | 23k |

- **The 120b is not worse at the solver API; it skips a stated input field.** The prompt says the first line is `n capacity K service
  horizon`; 120b programs (both efforts) almost all read `n capacity K horizon` (their own docstrings restate the 4-field format) and
  hard-code `SERVICE_TIME = 10`. The horizon then reads as 10, the first time-window `SetRange` makes the model infeasible, and OR-Tools
  raises "CP Solver fail". Two repair rounds with that traceback never fix it (the message does not point at parsing).
- **Counterfactual check (harness-side, CPU):** re-running the failing programs on the same instance with the `service` field removed from
  the header turns 120b-low 23/27 and 120b-medium 20/22 "CP Solver fail" programs **optimal** (20b-low: 14/23). So the routing models
  are right; one misread field is the entire failure. Prompt and harness checked: the format string and stdin both have 5 fields.
- 20b at medium effort mostly reads the field (66/90) and reaches .57–.70, .90 with best-of-3, matching Llama-70B (.60–.77, .93).
- Qwen3-32B with thinking is worse than without (.10 vs .10–.27; 9/30 traces end without code at 23k tokens).
- Interpretation: a strong prior for the "usual" format (service time as a constant, as in most VRPTW write-ups) overrides the stated
  spec, and more scale does not help. Queued (queue_vrptw3.sh, `--show_stdin`): the same arms with the instance's literal stdin appended
  to the prompt, to test whether a concrete example of the format removes the error.

## 07:50: showing the literal input fixes the skipped field (gpt-oss-20b low, VRPTW, `--show_stdin`); GPUs stopped by the user

| gpt-oss-20b low | no doc | snippet s1 / s2 / s3 | best-of-3 | programs parsing `service` | tokens |
|---|---|---|---|---|---|
| format in prose only (06:25) | .10 (.23) | .13 / .07 / .17 | .37 | 7 / 90 | ~4.5k |
| **+ instance stdin in the prompt** | .33 (.63) | **.90 / .97 / .87** | **1.00** | 81 / 90 | 2.0–2.4k |
| medium effort, prose only (for reference) | .33 (.50) | .70 / .57 / .63 | .90 | 66 / 90 | 8.8–10.2k |

- **One concrete example of the input removes the error.** With the 5-number first line visible, 81/90 programs read `service`, "CP Solver
  fail" drops from 21–23 to 1–4 per run, and the snippet runs go from .07–.17 to .87–.97 (best-of-3 30/30), at half the tokens of the
  low-effort prose runs and a quarter of medium effort. A cheaper and stronger fix than more reasoning effort.
- Without the snippet the example helps feasibility (.23 → .63) but the time-dimension API is still the bottleneck (opt .33): the two fixes
  address different errors (format fact vs API fact) and compose.
- The 120b `--show_stdin` lane was stopped by the user before it produced results (W_cooss120low_doctask_ex_s1/s2 partial, discard).
  All our servers and queues are down (07:50); the hourly loop is cancelled.


## 2026-10-13 12:10: server 2 (new machine): environment rebuilt, harness and one known number reproduced

- **Machine:** 8 × RTX PRO 6000 Blackwell (96 GB); this project uses GPUs 0–3 (user assignment). Serving with **vLLM 0.22.0** (torch 2.11,
  cu130, base conda python) instead of 0.10.2; client venv `/root/venvs/llm_algo_poc` rebuilt (openai 3.29, ortools 9.15.6755, numpy,
  matplotlib), so the ~150 hard-coded client paths still work. Changes: `poc/serve_gpu.sh` (no `--disable-log-requests` in 0.22,
  `VLLM_USE_FLASHINFER_SAMPLER=0` needed on Blackwell, `POC_PYLIB` optional), `poc/start_server.sh` calls `bash poc/serve_gpu.sh`
  (the CIFS copy has no exec bits; call every script with `bash`). Qwen3-32B-AWQ downloaded to /SSD/huggingface (the bf16 32B there is a
  different model; all 32B numbers stay AWQ). Ports 8040–8049 on this server.
- **Harness check** (`poc/sanity_check.py 30`): reference passthrough 480/480 on all 11 geometry tasks, MR false alarms 0/60 everywhere;
  the known "simple polygons self-intersect" generator defect reproduces exactly (area2 53/60, pip 49/60, convex 25/60; labels unaffected,
  see the review-item-7 entry).
- **Known number reproduced on the new stack:** gpt-oss-20b low, VRPTW, snippet + literal stdin, seed 1 (`S2_W_cooss20low_doctask_ex_s1`):
  **27/30 optimal** (old server: 27/30), 2,206 vs 2,228 mean output tokens, 2 "CP Solver fail" in both.
- New CPU analysis `poc/analyze_vrptw_stdin.py`: per run opt/feasible/tokens, label-free best-of-3, and the input-format counterfactual
  (each final program is re-run with the `service` field removed from the header; "skips service" = fails on the real input but is feasible
  on the 4-field one). On the old gpt-oss-20b-low runs: prose format 18 / 21 / 19 of 30 programs skip the field; with the literal stdin
  2 / 1 / 2. Old numbers re-derived exactly (.13/.07/.17, best-of-3 11/30; with stdin .90/.97/.87, best-of-3 30/30).
- Running (queue_s2_vrptw.sh): HANDOFF step 2, `--show_stdin` for gpt-oss-120b low/medium, gpt-oss-20b medium, Qwen3-32B-AWQ, Llama-3.3-70B;
  each lane first re-runs its old prose-only snippet seed 1 as a same-stack control.


## 2026-10-13 12:15: PRE-REGISTRATION C1 (written before any run): is the model's own confidence a label-free program selector?

**Question (HANDOFF step 5).** Token log-probs come free with generation. Do they tell correct from wrong programs, and can they replace or
complement the metamorphic check (MR-select), which needs k × 6 program executions? Prior work ranks code samples by mean log-prob
(Codex paper, Chen et al. 2021; Coder-Reviewer reranking, Zhang et al. 2023) and finds code LMs poorly calibrated (Spiess et al. 2024);
our angle is the contrast between random slips and the helper-induced systematic errors of F1.

**Design.** Qwen3-8B (bf16), no thinking, `--stdlib`, T = 0.7, top-p 0.95, "should use" header. Core 5 tasks × 2 sizes × 30 instances
(300 programs per seed) with K = 0 (needed helpers only) and K = 8 (8 related extra helpers); hard tasks lattice + rectunion without a
toolbox (120 per seed). Seeds 1–3. The raw log-prob of every sampled token is stored (`run_geo_cross.py --logprobs`; vLLM raw logprobs).
Scores fixed in advance: (a) mean token log-prob of the whole reply (primary), (b) mean over the code-block tokens, (c) minimum token
log-prob inside the code block.
**Metrics.** AUROC of each score for "correct on all 8 variants", computed within each task and averaged over tasks (primary; pooled
AUROC is confounded by task difficulty and program length), with bootstrap CIs over instances. Selection among the 3 seeds per instance:
max-confidence vs mean single sample vs MR-select (`poc/mr_select.py` rule) vs oracle-any; hybrid = MR-consistent candidates first, ties and
"no consistent candidate" broken by confidence.
**Predictions.**
- P1: K0 (independent slips): macro AUROC(a) ≥ 0.60; max-confidence selection beats the mean single sample but not MR-select.
- P2: K8, hull (systematic, helper-induced errors): AUROC(a) ≤ 0.55 within hull; the toolbox raises the probability of the wrong
  helper-route program (logit probe: +0.40 to +0.71 nats/token), so confidence cannot flag it.
- P3: hybrid ≥ MR-select in every condition.
- P4 (uncertain): on the hard tasks confidence is uninformative (macro AUROC < 0.60), because the wrong algorithm recurs in every sample.
All four are reported whichever way they come out. Same-stack sanity: K0 / K8 seed-1 accuracy should be near the old 92 / 77.


## 2026-10-13 12:15: C1 results: the model's own confidence is NOT a substitute for the metamorphic check (pre-registered 12:15)

Qwen3-8B, no thinking, 3 seeds (`S2_C1_geox8b_{dis0,dis8,hard}_t07s{1,2,3}`; `poc/analyze_c1.py`). Same-stack sanity: K0 92.3%, K8 77.3%
(old server 92 / 77). Confidence = mean raw log-prob of the sampled reply tokens (score a; b = code tokens only and c = min token gave
the same picture). AUROC within task, averaged over tasks (macro), 95% bootstrap CI over instances:

| condition | programs correct | macro AUROC (a) | per task | single sample | max-confidence of 3 | MR-select of 3 | hybrid | oracle-any |
|---|---|---|---|---|---|---|---|---|
| K0 (needed helpers only) | 831/900 | **0.68** [0.63, 0.73] | hull .96, area2 .61, segs .46 (pip, close all correct) | 92.3 | 93.3 | **99.3** | 99.0 | 100 |
| K8 (8 extra helpers) | 696/900 | 0.57 [0.49, 0.66] | **hull .43**, area2 .82, close .52, segs .52 | 77.3 | 78.7 | **83.0** | 83.7 | 85.7 |
| hard (lattice, rectunion) | 61/360 | **0.40** [0.33, 0.47] | lattice .31, rectunion .49 | 16.9 | **13.3** | **33.3** | 34.2 | 41.7 |

Selection differences (paired, 95% CI): max-confidence − single +1.0 [−1.1, +3.1] (K0), +1.3 [−0.9, +3.6] (K8), −3.6 [−8.3, +1.1] (hard);
MR − max-confidence +6.0 [+3.3, +9.0], +4.3 [+2.0, +7.0], +20.0 [+12.5, +28.3]; hybrid − MR −0.3 [−1.0, 0.0], +0.7 [0.0, +1.7], +0.8 [−4.2, +5.8].

- **P1 half confirmed:** confidence does separate correct from wrong programs on clean prompts (macro AUROC 0.68 ≥ 0.60; hull 0.96), but
  picking the most confident of 3 programs is not significantly better than one sample (+1.0), while MR-select gains +7.0.
- **P2 confirmed:** on hull under 8 extra helpers, confidence points the wrong way (AUROC 0.43). The wrong programs, mostly Graham scans on
  the offered `polar_sort`, are *more* probable than the correct ones (mean log-prob −0.018 for wrong programs that call `polar_sort` vs
  −0.023 for correct programs), as the logit probe predicted: the toolbox raises the probability of the wrong route.
- **P4 confirmed, and worse than "uninformative":** on the hard tasks confidence is anti-correlated with correctness (lattice 0.31) and
  choosing the most confident program loses 3.6 points. Reading the most confident wrong programs: degenerate repetition (the same line
  `gcd = abs(dx) if dx != 0 else abs(dy)` repeated until the program breaks) and long boiler-plate brute-force code; both are highly
  predictable token by token. Excluding the 6 truncated replies changes nothing (0.41).
- **P3 not confirmed for K0** (hybrid 99.0 vs MR 99.3, one instance), holds on K8 / hard, and the gains are ≤ 1 point everywhere:
  confidence adds nothing useful to the metamorphic check.
- **Reading:** token confidence measures how *typical* a program is for the model, not whether it is right. It is weakest exactly where
  the errors are systematic (helper-induced routes, wrong algorithms on hard tasks), which is also where sampling + checking struggles,
  so it cannot fill that gap. The executable check costs ≈ 6 short CPU runs per candidate and wins in every condition.


## 2026-10-13 12:30: HANDOFF step 2 done: the literal stdin fixes the skipped VRPTW field for every gpt-oss setting (server 2)

VRPTW, 30 instances, opt rate (feasible), solver arm, repair 2, T = 0.7; `poc/analyze_vrptw_stdin.py`. "Snippet" = the exact VRPTW
OR-Tools snippet; "+ stdin" = the instance's literal input appended (`--show_stdin`). Same-stack control = the old prose-only snippet seed 1
re-run on vLLM 0.22: identical opt counts to the old server for every model (20b-medium 21, 120b-low 0, Qwen3-32B 8, Llama-70B 18).
"skips service" = the input-format counterfactual (fails on the real input, feasible with the field removed).

| model | snippet, prose only (s1) | snippet + stdin s1 / s2 / s3 | best-of-3 | skips `service`: prose → stdin | tokens: prose → stdin | no doc + stdin |
|---|---|---|---|---|---|---|
| gpt-oss-20b low | .13 / .07 / .17 (old) | .90 / .90 / .80 | 1.00 | 18–21 → 2–3 of 30 | 4.8k → 2.2k | .33 (old) |
| gpt-oss-20b medium | .70 | **.97 / 1.00 / .90** | 1.00 | 7 → 0 | 8.3k → 3.9k | .50 |
| gpt-oss-120b low | **0** | **.97 / .97 / 1.00** | 1.00 | 29 → 0–1 | 4.8k → 1.7k | **.70** |
| gpt-oss-120b medium | .07 | **1.00 / 1.00 / 1.00** | 1.00 | 28 → 0 | 10.7k → 3.7k | .77 |
| Qwen3-32B-AWQ | .27 | .37 / .37 / .50 | .83 (prose .47) | 0 → 0 (fails on the API: 11 → 3–13 other failures) | 2.7k → 2.6k | 0 |
| Llama-3.3-70B | .60 | .73 / .67 / .77 | .97 (prose .93) | 2 → 0 | 1.5k → 1.2k | 0 |

- **One concrete input example removes the format error completely for gpt-oss**, at both sizes and both efforts: 120b goes from 0–.07 to
  .97–1.00 with a third of the tokens. The larger model was not worse at routing; it was the one that most strongly overrode the stated
  input format with the "usual" one, and the example overrides that prior.
- Qwen3-32B and Llama-70B rarely skip the field; for them the example helps less (+.10 to +.23 single, best-of-3 .83 / .97) because
  their remaining failures are API errors, which only the snippet addresses. Without the snippet they stay at 0 even with the example,
  while gpt-oss reaches .50–.77 (it knows the routing API).
- Fix-to-error matching again (F4): format fact → show the input; API fact → show the snippet; the two compose.


## 2026-10-13 12:35: E2 results (pre-registered in docs/prereg/PREREG_E2.md): F2 replicates strongly on a new task, F1 only partly

New tasks: delaunay (count triangles of a given triangulation whose circumcircle strictly contains a point) and diameter (squared
farthest-pair distance); Qwen3-8B, Qwen3-32B-AWQ (no thinking), gpt-oss-20b low; 2 seeds × 60 programs per cell. Full tables in the
pre-registration file; `poc/analyze_e2.py`.
- **F2 (hidden contract) replicates:** with the needed `in_circle` helper whose comment says (tersely) that it assumes a counter-clockwise
  triangle, Qwen3-8B / 32B get 1 / 3 of 120 right; the same helper made orientation-free gives 109 / 106 (+90 / +86 points). 92% / 97% of
  the failures are right on every orientation-preserving variant and wrong only on mirror / permute: the programs never orient the
  triangle. A spelled-out warning recovers 16% of the gap at 8B but 75% at 32B. For 32B the terse helper is worse than no helper at all
  (3 vs 55). gpt-oss-20b low is not affected (118 vs 117).
- **F1 (algorithm steering) only partly:** on diameter, 32B switches to the offered hull code in 97% of programs (HIGH) and loses 21.7
  points vs no toolbox, but the "non-suggestive" LOW helpers hurt even more (−46.7): 64 of 66 LOW failures read every input line as a
  point and ignore the stated count line (counterfactual: correct once that line is removed), and 53 of them call none of the helpers.
  So irrelevant helpers also derail **input-format adherence**, the same failure as the skipped VRPTW field. 8B keeps brute force under
  both toolboxes and is unaffected; gpt-oss −3.3.

## 2026-10-13 12:40: PRE-REGISTRATION F3x (before running): does the VRPTW format fix also fix the geometry format failure?

E2 found that Qwen3-32B-AWQ under the LOW toolbox on diameter fails 66/120, 64 of them by ignoring the stated count line. Test: the same
cells (diameter K0 and LOW, seeds 1–2) with the instance's literal stdin appended (`run_geo_cross.py --show_stdin`, same text as
run_co's). Predictions: (1) count-line failures under LOW drop from 64 to ≤ 5; (2) LOW accuracy rises to within 5 points of K0 with the
example; (3) HIGH (not re-run) is not the point. If (1) fails, the format failure is not a missing-example problem.

## 2026-10-13 12:50: F3x result: the same input example also fixes the geometry format failure (both predictions confirmed)

Qwen3-32B-AWQ, diameter, 2 seeds × 60, with the instance's literal stdin appended (`S2_F3x_geox32b_diam_{k0,low}_ex_t07s{1,2}`):
K0 110 → **120/120**; LOW toolbox 54 → **119/120**; count-line failures under LOW 64 → **0** (the one remaining failure is a crash);
mean tokens 255 → 314. So the "irrelevant helpers break input parsing" effect of E2 is entirely a format-attention failure, and the fix is
the same one that rescued gpt-oss on VRPTW: show one concrete input. This makes "show the literal input" a cross-domain fix for
format errors (CO and CG), next to "state the API fact" (F3) and "name the algorithm" (F1).

## 2026-10-13 12:55: CORRECTION: figures re-scored packaging-free (poc/rescore_figs.py, results/figs_packaging_free.json)

HANDOFF step 3. Every K0 → K8 number in figs 2, 4, 7, 8 is now scored the same way (stored programs re-run with the offered helpers
pre-defined, so a program that calls a helper without copying it is judged on its logic); paired 95% CIs over instances, seeds kept together.
- **Qwen3-1.7B (no thinking): −35.7 as measured → +0.3 [−7.0, +7.7] packaging-free.** 185 of its 214 K8 crashes were copy failures
  (mostly correct programs calling `orient` / `dist2` / `on_segment` without copying them). The near-zero total hides opposite per-task
  effects (of 60, K0 → K8): hull 49 → 17, area2 60 → 43, but close 29 → 57 and segs 1 → 18. The earlier reading "helper harm grows as
  models get weaker" relied on this row and is withdrawn; the semantic harm at 1.7B is task-specific (hull, area2), as at 8B / 32B.
- Llama-3.1-8B −39.3 → −35.2 [−40.3, −30.2]; Llama-3.3-70B −0.8 → +0.8; Qwen3-1.7B thinking −4.3 → −4.7; Qwen3 8B / 14B / 32B −14.3 /
  −7.7 / −13.3 (unchanged; these were already packaging-free); gpt-oss low / medium −0.7 to 0.0 (high effort is excluded: 20b hits the 24k
  cap in 72–80 of 300 programs).
- Old fig 7 / fig 4 Qwen rows (−17.7 / −29.0 / −17.0) compared K8 with a different arm (task-matched predicates, other header), not K0;
  fixed. Fig 8's "needed helpers only" baseline switched to the matched K0 run (91.7 / 83.7 / 92.0); with it, 14B's 3 samples + check
  (86.7) exceed its K0 single sample. Fig 2 packaging-free: K8 − K0 = −23.5 (8B), −3.5 [−11.0, +4.0] (14B, n.s.), −16.5 (32B).
- Fig 1's "without the stdlib sentence" values (83 / 79) have no stored jsonl and cannot be re-checked; figs 3, 5, 6 match the stored data.


## 2026-10-13 12:50: E4 results (pre-registered in docs/prereg/PREREG_E4_REPLAY.md): self-replay prevents the collateral damage of distillation

Leave-hull-out LoRA (Qwen3-8B, E5b data) with no replay (A), + 270 of the student's own verified no-thinking programs on 5 other tasks (B),
or + the thinking teacher's programs for exactly the same 270 prompts (C). Unseen hull on clean prompts: base 109/120, **A 48, B 118, C 36**
(B − A +58.3 [+49.2, +67.5]; B − C +68.3 [+60.0, +76.7]). In-task K8 gain kept (B 240/240). P1–P3 confirmed; P4 (other unseen tasks)
not: delaunay drops in both replay arms (B 47, C 45 vs A 59 of 60; B's failures are one stdin off-by-one repeated 13 times). The
student's hull programs show the mechanism: monotone chain in 120/120 (base), 120/120 (B), 59/120 (A), 49/120 (C). Practical recipe for
F5: distil robustness from a reasoning teacher, but mix in the student's own verified programs on the tasks it must keep; then
re-validate any task neither data source covers (delaunay).

## 2026-10-13 12:58: C1 replication at 32B (registered before running): same design and the same four predictions for Qwen3-32B-AWQ

`queue_s2_c1.sh` with M=32b on its own server (GPU 3). Predictions P1–P4 exactly as in the 12:15 entry; the hull-specific P2 is the key one.


## 2026-10-13 13:00: E3 results (pre-registered in docs/prereg/PREREG_E3.md): the check-gated pipeline is efficient for slips, blind to systematic errors

Qwen3-8B, "one program → if the metamorphic check fails, 3 samples + MR → if none is consistent, think (1,024)". K0: 98.0% at 365 tokens
per instance (best-of-3 + MR 98.0% at 938; full thinking 100% at 3,792). K8: 84.7% at 1,120 (best-of-3 + MR 82.0; budget-1,024
thinking for every instance 93.0% at 1,555; full thinking 97.0% at 5,571). Hard tasks: 53.3% at 1,816 (best-of-3 + MR 32.5; budget
thinking 80.8% at 1,735; full 99.2% at 8,463). P1, P2, P4 confirmed; P3 (within 5 points of full thinking under K8 / hard) not.
Cause: the check accepts programs that are wrong on every transformed copy in the same way (K8: 28 of 264 accepted stage-1 programs are
wrong, 23 of them hull; hard: 21 of 40). A wrong algorithm is usually wrong invariantly, so the router never escalates the systematic errors.
Practical reading for F4: under a broad toolbox or on hard tasks, spend a small fixed thinking budget on every instance rather than gating
on the check; use the check (and sampling) when errors are random.

## 2026-10-13 13:05: C1 replication at 32B (registered 12:58): confidence is again no selector; the confident-wrong task moves

Qwen3-32B-AWQ, same design. Macro AUROC K0 0.69 [0.64, 0.74], K8 0.66 [0.59, 0.72], hard 0.53 [0.47, 0.60]. Max-confidence vs one sample:
+1.1 [−1.3, +3.6], 0.0 [−3.1, +3.0], +1.9 [−4.4, +8.1]; MR-select vs max-confidence: +6.7, +9.3, +22.5 (all CIs above 0); hybrid − MR:
−0.7, −0.7, −5.0 (confidence tie-breaking hurts). **P1 confirmed** (AUROC ≥ 0.60 on clean prompts, selection gain n.s.), **P4 confirmed**
(0.53), **P3 not confirmed** (hybrid below MR everywhere), **P2 not confirmed for hull** (0.65 at 32B), but the anti-correlation
reappears on the task where 32B is hurt by the helpers: area2 under K8, AUROC **0.33**, where picking the most confident program loses
9.5 points (67.8 → 58.3). Across both sizes: confidence never beats one random sample significantly, and the metamorphic check beats
confidence by 4–23 points in every condition.

## 2026-10-13 13:30: E1 failure taxonomy done (HANDOFF step 4; full write-up docs/notes/E1_TAXONOMY_DRAFT.md, code poc/analyze_e1_taxonomy.py)

All 14,822 failing programs of 388 headline runs (47,868 programs) classified from behaviour only (per-version results, re-run exception,
counterfactual re-runs: other input layout, VRPTW header without `service`, helpers pre-defined); label check by reading 8 random programs
per class: geometry 127/128, optimization 85/97 (misses in two small CO classes, < 5% of CO failures). Stored failures reproduce on re-run
(2,501/2,502 crashes, 5,912/5,912 wrong answers, 3,955/3,969 CO failures).
- Geometry: 72% algorithmic (logic 5,846, orientation 519, degenerate 288, precision 236, other variant-dependent 166); 81–87% on the hard
  tasks in every family; with a toolbox, packaging/interface dominates for some models (Qwen3-14B K0 44/49, K8 185/262; 1.7B K8 192/231).
- Optimization: 51% API/knowledge (Qwen3 58%), 29% modelling/logic, 8% input format (all VRPTW; 343/379 gpt-oss), 6% output format.
- Fix map (failures of a class solved by one fix, paired; control = re-sample): API → exact snippet 618/1,042 (thinking 91/240; control
  104/682); input format → literal input 75/94 (effort 44/178; control 8/85); orientation → hint 188/221, effort 170/197 (control 28/80);
  logic → thinking 476/544, hint 810/1,204, MR-select 204/914 ≈ control 223/1,022; precision → MR-select 46/55; degenerate → thinking 23/27,
  MR-select 0/70 (the check never runs the degenerate copy); interface → API-contract sentence 61/83; packaging → same program with helpers
  pre-defined 329/630 (14B 125/162, 32B 22/78, 8B 3/12).
- **Scoring caveat found:** 293 TSP failures print the tour with the closing city (`0 … 0`) against the requested "each city exactly once";
  281 are optimal tours. Accepting them: Qwen3-32B no doc .701 → .828, snippet .970 → .995; Llama-70B no doc / sheet / snippet .33 / .55 / .87
  → .54 / .73 / .99. F3's ordering is unchanged, gaps shrink. Kept the stated format as primary; reported in PROPOSAL as a sensitivity.
- VRPTW: 69 of the 88 "CP Solver fail" programs pass that point once `service` is removed, then fail on a second bug; the literal input
  solves 15 of 23 of them.


## 2026-10-13 13:55: E2 extension (registered 13:20): the hidden-contract trap holds for Llama-70B and Qwen3-14B; thinking fixes it only at 32B

delaunay, 2 seeds × 60. Signed (terse contract) → fixed helper: Llama-3.3-70B 8 → 120, Qwen3-14B 4 → 120 (97–98% of failures
orientation-only; both worse than no helper: 81 / 76). With thinking: Qwen3-32B 118 → 120 (trap removed), Qwen3-8B 51 → 118 (trap halved),
at 7.8–8.8k tokens per program. X1 confirmed, X2 not (32B better and 8B worse than predicted). Across 4 non-reasoning models and 2 families
the same one-line contract costs 86–97 points; fixing the tool, not the model, is the cheap remedy.


## 2026-10-13 16:45: E3b (pre-registered, docs/prereg/PREREG_E3B.md): a brute-force reference catches the invariant errors but costs as much as thinking

Qwen3-8B writes a "simplest brute-force program" per instance; the first program is accepted only if it passes the metamorphic check AND
agrees with the brute force on 6 inputs. Catches 24/28 (K8) and 19/21 (hard) of the wrong programs the metamorphic check accepted, with
5–7% false alarms on the core tasks; but on the hard tasks the brute force is itself wrong (lattice 1/60), flagging 84% of correct programs.
Gated pipeline vs giving every instance 1,024 thinking tokens: K8 92.3% vs 93.0% at 0.98 × tokens; hard 80.0% vs 80.8% at 1.53 ×. No saving.

## 2026-10-13 16:50: honest assessment of importance (user asked "are the problems and solutions important and not trivial?") and next direction

- Non-trivial and robust: the hidden-contract trap (F2/E2: a true but terse one-line contract costs 86–97 points in 4 non-reasoning models,
  worse than no helper); the stated-input-format override (gpt-oss-120b 0/30 on VRPTW even at medium effort, Qwen3-32B ignoring the count
  line under irrelevant helpers); distillation damage and its self-replay cure as a controlled contrast (118 vs 36, same prompts).
- Largely known or obvious as remedies: exact API snippet > manual (doc-augmented code generation), "show an example input", "fix the
  helper's docs", replay against forgetting (rehearsal / SDFT), metamorphic testing and self-consistency selection, poor calibration of
  token confidence. Our contribution there is measurement and the error-type → fix matching, not new methods.
- Limits on importance: small synthetic textbook tasks; most effects shrink or vanish with reasoning models (gpt-oss, Qwen thinking at 32B),
  which is what current code assistants use. The fixes are cheap prompt hygiene.
- **Next direction (most important open problem that survives reasoning):** spec adherence when the stated input/output format conflicts
  with the model's prior for the "usual" format. Plan: a pre-registered family of CG/CO tasks whose stated stdin/stdout formats deviate from
  convention in controlled ways (extra field, reordered fields, 1-based indices, different tour convention), measured across model size and
  reasoning effort (gpt-oss 20b/120b low/medium, Qwen3 8B/32B with and without thinking); test whether the failure grows with scale/effort
  (inverse-scaling-like), and which fixes (literal example, restated format, a format-check unit test) remove it at what token cost.
  Prior art to check first: Inverse Scaling Prize tasks (memo trap, redefine), "prompt vs prior" conflicts, format-following benchmarks.

## 2026-10-13 17:20: related-work check for all findings (4 searches, papers opened) → docs/notes/RELATED_WORK.md; PROPOSAL §2 rewritten

- Must-cite overlaps found: 2606.04057 (incidental cues steer algorithm choice) and 2609.14157 (unneeded tool hurts without a call) for F1;
  2602.14878 / DRAFT / ContractEval for F2; **DRoC (ICLR 2025)** and CP-Bench for F3; 2505.17225 and 2507.14417 for the format override;
  MBR-exec / CodeT / incoherence 2507.00057 / 2607.16646 for MR-select; 2610.11300 and Coder-Reviewer for C1; DART 2606.23181 and ALGO /
  ExeCRE for E3 / E3b; 2510.18874, 2601.19897, 2501.14315, SDFT for E4; ICSE / EMSE code-error taxonomies for E1.
- Nothing pre-empts a specific claim, but each finding's novelty is narrower than written before (see the table). **The "next direction"
  of 16:50 is revised:** "priors override explicit specs, growing with scale / reasoning" is largely shown for math and puzzles
  (2505.17225, 2507.14417, 2305.15507); only stated I/O formats in generated programs remain. Priority for the hourly loop instead:
  run the baselines in RELATED_WORK.md, in order: (1) label-free selection baselines vs MR-select (MBR-exec on generated inputs, CodeT,
  self-certainty) and a DART-style router for E3; (2) forgetting-mitigation baselines vs self-replay (WiSE-FT α scaling, SDFT rewrite,
  KL-to-base); (3) helper-context baselines (scope instruction, S2A, DRAFT docstring rewriting); (4) DRoC port for F3 if time allows.
  Pre-register each comparison before running.


## 2026-10-13 17:38 (heading first said 17:50 by mistake): B1 (pre-registered, docs/prereg/PREREG_B1.md): MR-select vs published label-free selectors on the same candidates

Qwen3-8B, 3 candidates per instance. MR-select 99.7 / 83.3 / 33.3 (K0 / K8 / hard) vs CodeT 96.0 / 82.7 / 26.7, self-consistency vote
95.7 / 81.3 / 21.7, MBR-exec on model-written inputs 93.7 / 80.3 / 25.0, MBR-exec on fresh generator inputs 93.7 / 80.3 / 21.7, DeepConf
confidence ≤ 95.3 / 80.0 / 15.0 (hard: below a single sample); oracle-any 100 / 85.0 / 42.5. MR-select is best or tied everywhere, at no
generation cost; fresh inputs from the same distribution miss orientation / sign errors that transformed copies expose. A DART-style
router (two drafts, think if they disagree) is 2.0–2.5 points below a fixed 1,024-token thinking budget at 1.3–1.6 × the tokens.


## 2026-10-13 18:08 UTC: B2 (pre-registered, docs/prereg/PREREG_B2.md): forgetting-mitigation baselines vs self-replay

Leave-hull-out LoRA on Qwen3-8B; unseen hull K0 / hull K8 / trained-task K8: base 109 / 23 / 225; no replay (A′) 53 / 29 / 237; WiSE-FT
α 0.25 / 0.5 / 0.75: 120 / 17 / 217, 119 / 18 / 222, 96 / 29 / 236; SDFT 85 / **58** / 236; self-SFT (no teacher) 104 / 16 / 235;
self-replay (E4 B) **118** / 31 / **240**. Self-replay is the only arm keeping both the unseen task and the in-task gain; WiSE-FT trades
one for the other (and α 0.25 breaks diameter input parsing, 24/60); SDFT is the only arm that helps the unseen task under helpers.
Caveat found: the trained tasks have little K8 headroom (base 225/240), so self-SFT alone already reaches 235.


## 2026-10-13 18:52 UTC: B3 (pre-registered, docs/prereg/PREREG_B3.md): published context fixes for helper steering and hidden contracts

Qwen3-8B / 32B. Scope sentence (2609.14157-style) on 8 extra helpers: +0.3 / +0.5 points (recovers 2–3% of the harm, though helper use drops by a
third). System 2 Attention: −11.0 / −11.7 on the core tasks (the rewrite loses details: float outputs, signed areas; 32B: 82/600 replies
without a program) but it fixes the 32B format channel on diameter (54 → 98 of 120, count-line failures 64 → 0). DRAFT-style self-written
docs for the hidden-contract helper: 20/180 (8B), 27/180 (32B) vs the hand-written warning 11/60, 43/60 and the fixed helper 55/60, 52/60;
the models' probes never tried a clockwise triangle, so the docs only restate the precondition.

## 2026-10-13 19:53 UTC: PRE-REGISTRATION F3y (before running): is the skipped VRPTW field an ambiguous spec rather than a prior override?

While reading B4b outputs: asked to restate the stdin fields, gpt-oss-120b low writes "`n capacity K horizon` … maximum route end time
(service horizon)", i.e. it reads the stated header `n capacity K service horizon` as four fields with the compound noun "service horizon".
So the format string itself is ambiguous. Test: same VRPTW arm (exact snippet, prose format, no example input) with the header written
unambiguously as `n capacity K service_time horizon` (five integers), gpt-oss-120b low and 20b low, seeds 1–2.
Predictions: (Y1) if the ambiguity is the cause, programs skipping the field drop from 26–29 (120b) / 18–21 (20b) of 30 to ≤ 5, and opt
rises to ≥ .80; (Y2) if a prior for "service time is a constant" dominates, skipping stays ≥ 15 of 30.

## 2026-10-13 19:55 UTC: CORRECTION (F3y result): the "skipped VRPTW field" was an ambiguous header in our prompt, not a prior overriding a clear spec

Same VRPTW arm (exact snippet, prose format only, no example input), header written as `n capacity K service_time horizon` (five integers)
instead of `n capacity K service horizon`: **gpt-oss-120b low 30/30 and 30/30 optimal (0 programs skip the field; before: 0/30, 26–29
skipping); gpt-oss-20b low 29/30 and 29/30 (0 skipping; before .07–.17, 18–21 skipping)**, at 1.4–1.7k tokens. Prediction Y1 confirmed.
- Mechanism: "service horizon" reads as a compound noun ("the service horizon" = the planning horizon). Asked to restate the fields
  (B4b), gpt-oss-120b writes exactly that: "`n capacity K horizon` … maximum route end time (service horizon)". The model resolved an
  ambiguous spec in a plausible way; the larger model did so more consistently.
- What this changes: F3's "a skipped input field defeats the larger model" and the reading "a strong prior for the usual format overrides
  the stated spec" are withdrawn as stated. What stands: the literal input example fixes it (it disambiguates); repair with the traceback
  never finds it; and the counterfactual (field removed → optimal) correctly located the error. E1's "input format" class for gpt-oss on
  VRPTW (343 programs) is this ambiguity. The geometry count-line failure (Qwen3-32B, diameter + irrelevant helpers) is not affected: that
  format ("first line n, then n lines `x y`") is unambiguous.
- Lesson for the harness: field names in a format string must be unambiguous tokens (underscores or a typed list); check every format
  string by asking a model to restate it before running.


## 2026-10-13 19:56 UTC: B4 (pre-registered, docs/prereg/PREREG_B4.md): DRoC-style retrieval and restating the fields as baselines for F3

DRoC-style decomposed retrieval over a 12-chunk OR-Tools routing doc base beats plain BM25 top-3 (+.12 / +.15 pooled, Qwen3-32B / Llama-70B)
but stays below the exact snippet (−.12 / −.40), and fails on VRPTW (.03 / .03 vs .23 / .63) although it keeps the right chunks: the
models splice argument patterns across chunks (a per-vehicle capacity list passed to the time dimension; a starts list without ends).
Restating the stdin fields recovers nothing for gpt-oss (0/30, 2/30) and revealed the ambiguous header (see the F3y correction above).

## 2026-10-13 20:28 UTC: PRE-REGISTRATION A1 (before running): audit of every stdin format string for ambiguity (after the F3y correction)

Method (behavioural, no text matching of the model's prose): for each of the 23 format strings (13 geometry tasks, 9 optimization
problems, plus the corrected VRPTW header), each model writes a program that ONLY parses stdin according to the stated format and prints a
JSON object with one key per field; we run it on a real instance's stdin and compare the multiset of numbers in its JSON with the numbers
in stdin (pass = equal; "omitted counts" = only the count fields such as n / m are missing, which is benign; fail = anything else).
Models: gpt-oss-120b and gpt-oss-20b (low effort), Qwen3-32B-AWQ and Qwen3-8B (no thinking); 3 samples each; the prompt shows the problem
statement and the format but not the literal stdin.
Calibration prediction: the original VRPTW header (`service horizon`) fails for gpt-oss-120b in ≥ 2 of 3 samples, the corrected one
(`service_time`) in ≤ 1. No prediction for the other formats (this is an audit); any format failing in ≥ 2 of 3 samples for some model
is inspected and, if ambiguous, its earlier results are flagged.


## 2026-10-13 20:32 UTC: A1 result (pre-registered above): only the old VRPTW header is ambiguous; no other format string is

`poc/format_audit.py`, results in `results/format_audit_<model>.json` (full parser code and output per sample). 22 format strings × 4 models ×
3 samples. Judge: multiset of the numbers in the parser's JSON vs the numbers in stdin; omitting standalone count lines (n, m) is benign.
- **Calibration as predicted:** original VRPTW header (`n capacity K service horizon`): gpt-oss-120b fail 3/3 (it reads four header fields),
  gpt-oss-20b crash 3/3 ("too many values to unpack (expected 4)"), **Qwen3-8B fail 3/3** (parses only n, capacity, K: `service` and
  `horizon` missing), Qwen3-32B crash 1/3. Corrected header (`service_time`): 0/3, 1/3 crash, 0/3, 1/3 crash.
- **All 20 other formats (13 geometry, 7 optimization): no model misreads any of them in ≥ 2 of 3 samples.** The 2 isolated failures are not
  format readings (Qwen3-32B also printed a TSP tour despite "do not solve"; gpt-oss-120b once printed only the point count for hull).
- So the ambiguity was specific to the VRPTW header, and no other earlier result needs a format caveat. The probe costs one short call per
  model and format string and would have caught the problem before the VRPTW runs: it is now a pre-run check for new tasks.


## 2026-10-13 21:45 UTC: E4b (pre-registered, docs/prereg/PREREG_E4B.md): self-replay keeps a large in-task gain AND the unseen task

Hull now trained (in-task K8 on the 5 core tasks: base 236/300 → 296 no replay / 295 self-replay / 294 teacher replay; hull 11 → 55–57 of 60);
unseen convex under 8 helpers: base 81/120, no replay 55, **self-replay 80**, teacher replay 42 (self − teacher +31.7 [+21.7, +41.7]).
All three predictions confirmed. On clean convex prompts some damage remains in every arm (89 → 71 / 76 / 66).

## 2026-10-13 22:28 UTC: PRE-REGISTRATION R1 (before running): training-seed replication of the self-replay contrasts (E4, E4b)

E4 and E4b used one training run per arm (example sampling, data order and LoRA init all from seed 0). Replicate the two decisive arms of
each with training seed 1 (`E4_SEED=1`: a different sample of the 600 teacher examples, a different order and a different LoRA init; the
replay sets are unchanged): E4 leave-hull-out B (self-replay) and C (teacher replay), evaluated on hull K0 (seeds 1–2, 120); E4b B5 and
C5, evaluated on convex K8 (seeds 1–2, 120) and the 5 core tasks under K8 (300).
Predictions: R1-P1: hull K0, B − C ≥ +30 (seed 0: +68.3). R1-P2: convex K8, B5 − C5 ≥ +15 (seed 0: +31.7). R1-P3: B5 core K8 ≥ 285 of 300.

## 2026-10-13 22:45 UTC: R1 result (pre-registered above): the self-replay contrasts replicate with a second training seed

Training seed 1 (different example sample, data order and LoRA init; same replay sets):
- E4 (leave-hull-out), unseen hull on clean prompts: self-replay **118/120**, teacher replay **28/120** (seed 0: 118 / 36); B − C +75.0
  [+66.7, +82.5]. Trained tasks under K8: 240 / 240 for both.
- E4b (hull trained, convex unseen), convex under 8 helpers: self-replay **85/120**, teacher replay **34/120** (seed 0: 80 / 42); B5 − C5
  +42.5 [+31.7, +52.5]; 5 core tasks under K8: 298 / 294 of 300. Clean convex: 87 / 62 of 120 (base 89; seed 0 self-replay was 76, so
  the clean-prompt damage seen with seed 0 is not stable).
All three predictions confirmed; the effect is larger in the replicate than in the original run.


## 2026-10-13 23:33 UTC: L1 (pre-registered, docs/prereg/PREREG_L1.md): helper steering survives an API-only library; 8B hallucinates library functions

Helpers offered as an importable module `geomlib` described only by signatures + one-line docs. Qwen3-32B: K0 → K8 558 → 442 of 600
(−19.3; copy-in −16.7); hull 104 → 32 with `polar_sort` imported in 84/120 programs. Qwen3-8B: hull at K0 already 13/120 because 53/54
failed programs `from geomlib import convex_hull` (not in the listed API) → ImportError; K8 effect −1.0. Steering does not need pasted code;
the library framing adds hallucinated imports for the smaller model.


## 2026-10-14 00:33 UTC: L2 (registered extension of L1): "the module contains exactly these functions" stops hallucinated imports, not the steering

Qwen3-8B, API-only library: programs importing a function the module lacks 106 → 3 (K0), hull K0 13 → 103 of 120; with that removed the
helper steering reappears (K0 → K8 553 → 500, hull 103 → 46, `polar_sort` in 92/120). Qwen3-32B unchanged (−20.0). Both predictions confirmed.


## 2026-10-14 00:49 UTC: M1 (pre-registered method, docs/prereg/PREREG_M1.md) failed at the dev stage: likelihood shift confounds "writes differently" with "chooses a different algorithm"

The steering score (how much an offered helper lowers the likelihood of the model's own no-helper draft) ranks the known harmful hull
helpers highest (AUROC 0.92) but ranks the needed helper `orient` about as low, because every helper changes naming / copying; the
registered thresholds keep no helpers. The test phase was not run. Next method candidates: a behavioural per-helper probe (generate with each
helper alone, compare with the no-helper draft on the metamorphic copies; costs N programs) and, for hidden contracts, harness-side
metamorphic probing of each helper (mirror / reverse its inputs) to detect orientation dependence and write the contract automatically.


## 2026-10-14 02:00 UTC: M2 / M3 / M4 (pre-registered, docs/prereg/PREREG_M2_M4.md): our methods vs baselines, with prior art checked first

Pooled over 7 tasks, packaging-free, Qwen3-8B / 32B: all helpers 78.9 / 79.4%; no helpers 68.8 / 77.5%; needed only 80.6 / 89.6%;
think-1,024 94.5 / 90.0% (≈1.6–1.7k tokens); **M4 (write without helpers first, then refactor to use them) 89.0 / 85.2% at ≈0.8–0.95k
tokens** (core tasks: 8B 579/600, the best of all methods; delaunay / lattice below think); M4 without the keep-the-algorithm sentence
is as good (the order matters, not the sentence); M3 (per-helper behavioural probe) 80.0% at 6–10k tokens (the probe keeps `polar_sort`
because its wrong programs are consistent); M2 (automatic probe sentence) does not help on delaunay (0 / 10 of 120 vs hand warning 18 / 80).
A published baseline, TroVE-style majority over samples with and without the toolbox, is the strongest: 91.2 / 95.0% at ≈2.6k / 1.8k tokens.


## 2026-10-14 02:45 UTC: M5 (pre-registered, docs/prereg/PREREG_M5.md): draft-vs-rewrite check makes M4 a frontier method for Qwen3-32B

M4 replicates (8B 88.9%, 32B 85.2%). Voting over draft + rewrite + one all-helpers sample does not reach TroVE (87.7 / 88.0%). Breaking
draft–rewrite disagreements with the metamorphic check (V2, no extra generation): 8B 89.0%, **32B 91.5% at 826 tokens**, above think-1,024
(90.0% at 1,591) and below TroVE-style 4-sample voting (95.0% at ≈1.8k). Frontier: 8B → M4 then thinking; 32B → V2 then TroVE.

## 2026-10-14 03:30 UTC: difficulty check and plan for harder problems (user asked whether the problems are too easy, and about LLM-generated problems)

- Honest status: intrinsically the tasks are easy (textbook statements, 6–40 elements; reasoning models or 8B with full thinking reach
  95–100% on almost all; clipping and Delaunay without helper are the exceptions for small models). The measured difficulty comes from the
  context interventions and the strict 8-variant scoring.
- Plan, in order: H1 large inputs with a time limit (running: hullL / closeL / diamL, n = 2,000 / 20,000, PREREG_H1.md); H2 real contest
  geometry with official tests and ratings (CodeContests: 31 geometry problems in the local shards, ≈ 300 in the full set, needs a ≈3.5 GB
  download to /SSD); H3 standard OR instances (CVRPLIB / Solomon VRPTW, judged by the gap to best-known solutions); H4 gpt-oss-120b at
  medium/high effort on all of them.
- LLM-generated problems: only as a verified pilot, not as the main benchmark. Reasons: (1) every reference answer must still come from
  independent verified solvers (agreement of several solutions + brute force on small inputs), otherwise label noise; (2) generated
  problems tend to be near-duplicates of well-known ones and their difficulty is uncalibrated; (3) statements written by a model can be
  ambiguous, which is exactly the failure that cost us the VRPTW result; (4) for reviewers, real contest problems with official tests and
  ratings are stronger evidence. Synthetic generation with verification is already an active line (e.g. KodCode, rStar-Coder) to cite if used.


## 2026-10-14 04:29 UTC: H1 (pre-registered, docs/prereg/PREREG_H1.md): large inputs make the helper harm bigger, not the problems hard for reasoning models

n = 2,000 / 20,000 with a 10 s limit: Qwen3-8B / 32B without helpers 70.8 / 69.2%, with all helpers 40.4 / 34.6% (hull 14 of 80 for both),
think-1,024 87.1 / 84.6% (≈1.7k tokens), M4 69.2 / 61.7%; gpt-oss-20b / 120b low 97.9 / 91.7% without helpers. Large inputs do not make
these textbook tasks hard for reasoning models; the steering harm doubles relative to small inputs.


## 2026-10-14 05:30 UTC: H2 (pre-registered, docs/prereg/PREREG_H2.md): real contest geometry is hard, unlike our synthetic tasks

31 Codeforces geometry problems with official tests: Qwen3-8B / 32B without thinking 9.7 / 7.5% solved, full thinking 31 / 30% (half the
attempts truncated at 16k tokens); gpt-oss-20b low / medium 34 / 53%; gpt-oss-120b low / medium 49.5 / 65.6% (≈3k / 6k tokens). 5 problems
(rated 2100–3400) are never solved. Generic helpers do not change much here. This is the regime where the project's questions (which cheap
fix, at what cost) matter for strong models; next: label-free selection with the public tests and thinking budgets on this set.

## 2026-10-14 06:20 UTC: decision (user: "decide yourself"): download the full CodeContests set for the contest-geometry benchmark

Going ahead: 31 problems give wide confidence intervals (± ~15 points per condition), so the hard-problem conclusions need the ≈ 300
geometry problems of the full set. Size is 7.6 GB in total (not 3.5 GB as first estimated); only the 36 missing train shards are
downloaded, to /SSD/huggingface/datasets_cc (84 GB free before). Plan: extract the geometry subset (+ tests, ratings, references) to
results/h2/cc_geometry_full.json, validate every problem with its C++ references and the reference-disagreement check, then delete the
parquet shards from the shared /SSD.

## 2026-10-14 06:24 UTC: H2b (pre-registered, docs/prereg/PREREG_H2B.md): on hard contest geometry, a short reasoning budget + the public examples is the cheap fix

8 samples per problem (31 Codeforces geometry problems), first sample passing the statement's examples. gpt-oss-120b: 8 low-effort samples
filtered 61.3% at 24.9k tokens vs one medium attempt 65.6% at 6.5k (P1 confirmed: more effort beats more samples); medium + filter over 3
reaches 71.0%. Qwen3-32B: 8 no-think samples filtered 29.0% at 5.5k = full thinking 30.1% at 14.0k (P2 refuted narrowly: equal, not
better, at 40% cost); think-1,024 + filter over 3: 38.7% at 10.1k, the best Qwen point. The filter recovers 61% of the single → oracle gap
pooled (P3 refuted): 72 samples pass the examples but fail a hidden test, and rerunning them shows 66 plain wrong answers, so the examples
are a weak check on strong models (they pass many wrong programs). Raw programs read: e.g. 703_C wrong closed-form instead of the
pass-before/after-bus case analysis. n = 31 → ± 10–15 points; the full CodeContests geometry set is downloading.

## 2026-10-14 06:33 UTC: H2c Part A (pre-registered, docs/prereg/PREREG_H2C.md): output agreement among the example-passing samples adds a little, never hurts

Offline on the H2b samples (CPU only): run every example-passing program on 20 extra contest inputs (disjoint from the evaluation tests;
outputs never used) and pick the one agreeing most with the others (MBR-exec / AlphaCode-style clustering). +3 problems of 93 at k = 8
(P1 ≥ +5 refuted), 0 losses (P3 confirmed); gpt-oss-120b low ×8 reaches 64.5% ≈ one medium attempt (65.6%) at 3.8 × tokens (P2 confirmed:
effort still wins on cost); medium ×3 + MBR-exec = 74.2% at 19.2k tokens is the best point. Remaining misses read: shared misconceptions
(wrong programs agree), inputs that never hit the bug, and precision-only differences.

## 2026-10-14 06:42 UTC: full contest-geometry set built and validated; H2c Part B running

- 355 Codeforces geometry-tagged problems (train 345, valid 4, test 6; ratings 800–3500, median 2200) extracted to
  results/h2/cc_geometry_full.json (poc/cc_extract.py; public + private + first 60 generated tests; up to 5 C++ / Python references).
- Validation (CC_SET=full poc/run_cc.py validate; all ≤ 5 C++ references, strictest tolerance at which one passes, ≥ 1e-6 whenever an
  expected output has a decimal number): 311 kept, 44 dropped (no reference passes: special judges, interactive, or slow on our machine).
  74 of the 311 are flagged because a reference that runs prints other answers (several valid answers or a special checker); this
  reproduces 6 of the 7 hand flags on the 31 (the 7th was flagged from the statement). Two of the 31 now use 1e-6 instead of 1e-4.
- Text completeness: 106 of 355 statements have an <image> placeholder before the Input section (a figure or a formula lost in the
  dataset's text). A 2025 contest benchmark (arXiv 2506.22954) drops figure-dependent geometry problems for this reason; we report all
  problems, unflagged, and unflagged without body images.
- The parquet shards were deleted from the shared /SSD after extraction (7.0 GB).
- Part B (pre-registered B-P1..P5 in PREREG_H2C.md) running: 7 conditions × 3 seeds on the 311 problems; full thinking on an extra
  Qwen3-32B-AWQ server (GPU 0, ≈ 700 tokens/s, ≈ 1.8 h per seed).

## 2026-10-14 06:49 UTC: H3 set up and pre-registered (docs/prereg/PREREG_H3.md): the 56 Solomon VRPTW instances as the hard optimisation set

- Harness poc/run_solomon.py: instance file verbatim on stdin, explicit real-valued time rules in the statement, exact checker; best-known
  table parsed from SINTEF (56 / 56 entries; r205 and rc101 carry a footnote letter). Checker verified: our OR-Tools reference reproduces
  the best-known 828.94 on six C1 instances.
- Non-LLM calibration: nearest-feasible greedy 56 / 56 feasible, +47.6% vs best-known. OR-Tools 30 s as in the documentation example
  (PATH_CHEAPEST_ARC first solution): 49 / 56, mean −1.0% vs best-known (the table minimises vehicles first; on R2/RC2 pure-distance
  solutions with more vehicles are shorter). On r101–r103, r105, r106, rc101, rc105 it finds no first solution and the program crashes on
  `sol = None`; PARALLEL_CHEAPEST_INSERTION solves all 7. A correct-looking documentation snippet therefore fails at benchmark scale;
  the pre-registration tests the documentation snippet against the robust one.
- Queued (poc/queues/queue_s2_h3.sh): each server starts H3 once its H2c Part B lanes finish. OR-Tools 300 s reference (for the gap) running on CPU.

## 2026-10-14 07:29 UTC: H2c Part B interim (311 problems; seeds finished so far) and the H3 reference

- Single-sample solve rates so far: Qwen3-32B no-think 12.4% (3 seeds), think-1,024 22.2% (s1); gpt-oss-20b low 37.4% (3 seeds), medium
  46.9% (s1); gpt-oss-120b low 42.4% (s1). All within ± 8 points of the 31-problem estimates (B-P1 so far holds).
- Failure types (seed 1, failing test re-run): almost all are wrong answers, most already on the statement's examples (Qwen 217 / 268
  failures, gpt-oss-120b 129 / 179); timeouts ≤ 4 per condition, so Python speed is not what fails.
- Two non-solving behaviours to report in the cost-accuracy plot: gpt-oss-20b low gives up without code on 38–43 of 311 (e.g. "I'm sorry,
  but I can't provide the solution to this problem." on a 1400-rated problem; 369–2,241 tokens), and gpt-oss-20b medium hits the
  16k-token cap without code on 84 of 311 (27%). gpt-oss-120b and Qwen never return without code.
- H3 reference: OR-Tools 300 s with cheapest insertion is feasible on 56 / 56, mean −2.8% vs the vehicles-first best-known distances
  (30 s: −0.6%). The gap reference is min(best-known, this run).

## 2026-10-14 08:25 UTC: H3 harness check — Qwen3-32B 0 / 56 on Solomon, first because of our prompt, then because of the model

- First runs: Qwen3-32B no-think 0 / 56 feasible in every arm (plain, documentation snippet, robust snippet). Re-running the programs:
  input-parsing crashes (`int('NUMBER')`, `int('CAPACITY')`): the statement described the file in words only. Treated as our harness
  bug: amendment in PREREG_H3.md (stdin normalised to LF, first 12 lines of the file shown verbatim); the old runs are kept as a
  words-only arm (sol_noex_*). H3 queue stopped by PID and relaunched.
- With the verbatim example, Qwen3-32B plain is still 0 / 56 (seed 1). Raw errors now: it still reads the header line "NUMBER CAPACITY"
  as the numbers (≈ half of the programs, although the example shows the layout), and calls OR-Tools methods that do not exist
  (`RegisterUnaryLongLivingCallback`, `GetDimensionName`). These are model failures (format reading + invented API), the two failure
  classes of E1, now at benchmark scale. The snippet arms will show how much of it the API fact removes.

## 2026-10-14 08:36 UTC: H2c Part B interim analysis (poc/analyze_h2c.py, CC_SET=full; seeds finished so far; not final)

| condition (311 problems) | single | first sample passing the examples | MBR-exec | oracle any-of-k | tokens per problem (all k samples) |
|---|---|---|---|---|---|
| Qwen3-32B no-think, k = 3 | 12.1% | 21.2% | 20.6% | 21.9% | 2.1k |
| Qwen3-32B think-1,024, k = 3 | 21.8% | 30.2% | 29.9% | 32.2% | 8.8k |
| gpt-oss-20b low, k = 3 | 37.7% | 47.9% | 48.9% | 51.1% | 4.5k |
| gpt-oss-20b medium, k = 2 | 47.3% | 53.7% | 53.7% | 55.9% | 17.3k |
| gpt-oss-120b low, k = 2 | 46.0% | 51.1% | 51.1% | 53.4% | 6.5k |
| gpt-oss-120b medium, k = 1 | 54.7% | – | – | – | 6.7k |

- On the full set the example check recovers most of the single → oracle gap at k = 3 (Qwen 92%, gpt-oss-20b low 76%); MBR-exec adds
  nothing over it (−0.6 to +1.0). gpt-oss-20b low ×3 + check (47.9% at 4.5k tokens) equals one medium attempt (47.3% at 8.7k) at half
  the tokens; one gpt-oss-120b medium attempt (54.7% at 6.7k) is above everything else so far. Unflagged and text-complete subsets
  move every number up by 2–5 points without changing the order. ≥ 2300 band: 2.7% (Qwen no-think) to 29.5% (120b medium).

## 2026-10-14 09:32 UTC: H3 interim (Solomon VRPTW, 56 instances × 2 seeds; PREREG_H3.md): at benchmark scale the program fails at reading the file

- Feasible of 112: Qwen3-32B no-think plain / documentation snippet / robust snippet 0 / 1 / 1; gpt-oss-20b low 0 / 18 / 17 (≈1.4–1.7k
  output tokens everywhere). Re-run errors: about half of all programs crash reading the file although its first 12 lines are shown
  verbatim (header "NUMBER CAPACITY" parsed as numbers; the 11-token column header slips through a `len(parts) < 7` guard), the rest on
  invented OR-Tools methods, `sol` None and index errors. When a program does run, it is good: all 36 feasible programs use guided local
  search and the gaps to the reference are −0.1 to 11.1% (median ≈ 3%).
- Pre-registered H3-P2 (snippet +15 for Qwen) and H3-P5 (window violations) refuted; H3-P1 holds. The input format is the first missing
  fact. H3b (pre-registered in the same file): a correct 8-line reader in the prompt, alone and with each snippet; running on 8041/8042;
  gpt-oss-120b low/medium get all arms once their H2c lanes end. The old H3 queue was stopped by PID and folded into poc/queues/queue_s2_h3b.sh.

## 2026-10-14 09:39 UTC: methods for the hard benchmarks (user: "what are the methods? why don't you suggest and test?"), docs/prereg/PREREG_N.md

Honest status: our own methods so far (M1–M5) were built and tested on the synthetic tasks (M4/M5 won on helper steering; M1, M2
failed; M3 too expensive). On the hard benchmarks we had only measured existing fixes (effort, sampling + example check, MBR-exec,
snippets). The failure analysis now says what to target, so three methods, with prior-art checks, in PREREG_N.md:
- N1 metamorphic example augmentation (new): the model writes an output-preserving input transformation; applied to the statement's
  examples it yields new tests whose expected outputs are inherited, not predicted. Tested as a check on all Part B example-passers.
- N2 one round of label-free feedback repair, split by failure type (crash vs wrong answer), against a second sample and against more
  reasoning at matched tokens (Olausson et al. 2024 found self-repair modest at matched compute; we test where it is not).
- N3 escalation cascade (prior art: Model Cascading for Code 2405.15842), computed offline before pre-registration: gpt-oss-20b low →
  medium 49.8% at 7.6k tokens vs medium alone 47.1% at 8.7k; Qwen no-think → think-1,024 23.7% at 3.2k vs 21.8% at 2.9k; no saving for
  gpt-oss-120b (56.4% vs 56.1%).
- Reallocation: Qwen3-32B full thinking stopped after seed 1 (29.9% = 93 / 311; ≈ 3.5 h per seed); GPU 0 now runs N1/N2
  (poc/queues/queue_s2_n.sh: mea_cc.py, repair_cc.py, run_solomon.py repair). Deviation from H2c Part B: full thinking has k = 1.

## 2026-10-14 09:46 UTC: N1 (metamorphic example augmentation) is a real negative on contest geometry

Qwen-written output-preserving transforms turn the statement's examples into 7 labelled tests per problem, but flag 38% of wrong and
41.5% of correct example-passers (invalid transforms). Restricted to the 108 problems whose derived tests the C++ reference confirms, it
flags 6% of wrong passers (1.7% of correct): contest errors survive symmetry transformations, unlike the orientation traps of F2.
Details in PREREG_N.md. N2 (feedback repair) running.

## 2026-10-14 09:46 UTC: N2 first results (gpt-oss-20b low, contest geometry): one repair round ≈ a second sample + check, cheaper

Seed 1: 125 → 140 of 311 (40.2 → 45.0%) with +733 repair tokens per problem; seed 2: 115 → 139 (37.0 → 44.7%) with +794. A second
independent sample + the example check gives 44.8% at +1.5k tokens (N3 table), so repair matches resampling at about half the extra tokens.
By failure type: wrong answers fixed 13 / 103 and 23 / 121, crashes 1 / 12, give-ups ("I'm sorry…", no code) 2 / 81; no correct program
was broken (programs passing the examples are kept). Example: 1036_E (covered lattice points) fixed by de-duplicating points on ≥ 3 segments.
Qwen3-32B and routing repairs running.

## 2026-10-14 10:41 UTC: H2c Part B final (311 real Codeforces geometry problems; PREREG_H2C.md)

Cost-accuracy frontier per model (tokens per problem, all samples counted): Qwen3-32B: no-think 12.1% (0.7k) → no-think + one repair round
18.0% (1.5k, N2) → no-think ×3 + example check 21.2% (2.1k) → think-1,024 21.8% (2.9k) → no-think→think-1,024 cascade 23.7% (3.2k, N3)
→ think-1,024 ×3 + check 30.2% (8.8k) ≈ full thinking 29.9% (13.7k). gpt-oss-20b: low 37.7% (1.5k) → low + repair 44.8% (2.3k) → low ×3 +
check 47.9% (4.5k) → cascade to medium 49.8% (7.6k) > medium single 47.1% (8.7k). gpt-oss-120b: low 46.1% (3.2k), medium 56.8% (6.8k),
medium ×3 + MBR-exec 62.4% (20.3k); ceiling (oracle of 3 medium) 68.2%. Predictions: B-P2, B-P3, B-P5 confirmed; B-P1 mostly; B-P4 half
refuted (MBR-exec +1, not +2). On real problems the cheap label-free check is the statement's examples; more samples + that check beat
more reasoning for the 20b model, more reasoning beats more samples for the 120b model.

## 2026-10-14 10:47 UTC: H3b (facts compose), N2 / N4 results; H3c and N2b running

- H3b (PREREG_H3.md table): reader + robust snippet makes gpt-oss-120b feasible on 56 / 56 at low effort and 56 / 55 at medium (median
  gap 1.5%, all 7 tight-window instances), gpt-oss-20b 24 / 25; each fact alone is far lower. Re-run errors show our reader is a hidden
  contract: it returns floats and OR-Tools rejects them (`AddDimension ... argument 3 of type 'int64_t'`, 27 of 40 crashes for 120b low).
  Qwen3-32B: 0–3 of 56 in every arm, rewriting given calls into non-existent signatures (`RoutingIndexManager(n + 1, K, [0] * K)`).
  H3c (integer reader) pre-registered and running.
- N2 (one repair round): contest geometry ≈ a second sample + check at the same or half the extra tokens (20b 45%, Qwen 18%); routing
  0 → 7 / 3 (20b), 0 → 0 (Qwen), P1 refuted (fixing one crash exposes the next). N4 (repair, then escalate) adds ≈ 1 point over the plain
  cascade at similar tokens (20b 51.6% at 7.3k vs 50.3% at 7.5k). N2b (120b low, Qwen think-1,024 repair) running on a second 120b server.

## 2026-10-14 11:33 UTC: H3c, N2b, N4 results; H4 (helpers on real contest geometry) started

- H3c: an integer reader alone does not help either (120b low 14 / 10 of 56): the models write their own float literals into OR-Tools
  (1e7 slack). The missing fact is "integers everywhere" (in both snippets); with reader + robust snippet the integer reader adds ten
  instances for gpt-oss-20b (36 / 32 vs 24 / 25). Three facts compose: file layout, integer arguments, a first-solution strategy for tight
  windows.
- N2b: one repair round lifts gpt-oss-120b low 46.0 → 53.1% (4.6k tokens) and Qwen think-1,024 22.2 → 27.3% (4.4k). N4-P3 refuted on cost.
- H4 pre-registered (PREREG_H4.md) and running: 8 related helpers on the 311 contest problems (Qwen3-32B no-think, gpt-oss-20b low), the
  external-validity test of F1.

## 2026-10-14 11:34 UTC: honest novelty assessment of our methods (user: "so there is novelty over methods?")

| method | closest prior art | novel? | result |
|---|---|---|---|
| M1 likelihood filter for helpers | ContextCite-style pruning | weak | failed |
| M2 probe-verified behaviour sentence as tool doc | DRAFT, Play2Prompt (docs from calls); AutoMR (MRs as oracles) | yes | did not help |
| M3 per-helper probing | TroVE, GRETEL | weak | works, 6–10k tokens |
| M4 draft first, then refactor with helpers | De-Hallucinator, InlineCoder, ReGAL | no (the new "keep the algorithm" sentence adds nothing) | strong on steering |
| M5-V2 draft/rewrite disagreement settled by the metamorphic check | — (combination) | small | 32B 91.5% @ 0.8k, on the frontier; 8B no gain; synthetic only |
| N1 metamorphic example augmentation | MR-Adopt, CodeMetaAgent | yes | real negative (6% detection) |
| N2 one repair round | Self-Debugging, Olausson et al. 2024 | no (our part: split by failure type, matched cost) | best next step per token |
| N3 escalation cascade | Model Cascading for Code, FrugalGPT | no | +2.7 at −13% tokens (20b) |
| N4 repair then escalate | combination of N2 + N3 | small | +1 point |
Verdict: no strong method contribution yet; the novel methods (M2, N1) are negative and the positive ones are published or small
combinations. The project's contribution is diagnostic: matched one-fact interventions, metamorphic scoring, the helper-steering and
hidden-contract findings, "facts compose" at benchmark scale, and cost-accuracy maps of the cheap fixes.

## 2026-10-14 12:31 UTC: H4 result (helpers on real contest geometry) and FM (fact mining) started

- H4 (PREREG_H4.md): 8 related helpers on the 311 problems: Qwen3-32B no-think 12.1 → 13.7% (n.s.; 58% of programs call a helper; +21%
  tokens); gpt-oss-20b low 37.7 → 33.4% (96 lost vs 56 gained, p ≈ 0.002), mostly in programs that never call a helper: with the toolbox
  the model reasons less (median 1,168 vs 1,482 tokens on lost pairs) and writes different wrong solutions. F1's mechanism on real problems
  is distraction that shortens reasoning, and the low-effort reasoning model is the one hurt, opposite to the synthetic tasks.
- H3 complete: the 12-line file example alone is worth ≈ 20 instances for gpt-oss-120b medium (words only 6 / 2 vs 26 / 28).
- FM (PREREG_FM.md; prior art: Dynamic Cheatsheet, ExploraCoder, AutoManual/ExpeL, OptiMUS/LLMOPT/SAC-Opt): the model mines facts
  from its own failures on 8 instances, each fact admitted only if a counterfactual re-run adds ≥ 2 feasible programs; tested on 48
  held-out instances against no facts, unverified facts, hand facts and per-instance repair. Two chains on two gpt-oss-120b servers;
  transfer to gpt-oss-20b. Qwen server (GPU 0) stopped: no run uses it.

## 2026-10-14 13:30 UTC: FM (fact mining) result: the model finds two of the three facts, but verification by feasibility hurts; FM2 running

On 48 held-out Solomon instances (gpt-oss-120b low): no facts 7.3%, one repair round 25.0%, mined sheets 19.8 / 35.4% (verified) and
31.3 / 39.6% (unverified), hand facts 100%. Both chains find the file layout and "AddDimension's slack must be an integer"; none finds
integers everywhere, the None check or the tight-window strategy. Verification by end-to-end feasibility on 16 programs rejected right
facts because facts compose (a program that still misreads the file stays infeasible after the slack fix). All five predictions except
P5 refuted (PREREG_FM.md). FM2 (pre-registered): accept a fact if it halves its targeted failure signature, and allow short code facts;
chains C / D on the two 120b servers. 8042 (gpt-oss-20b) stopped; GPU 0 and 2 free.

## 2026-10-14 14:15 UTC: FM2 result: execution-verified fact mining works on one of two chains (7% → 64.6% on held-out instances)

Accepting a fact when it halves its targeted failure (and allowing short code facts) gives chain D 64.6% (31 / 31 of 48; median gap
1.2–1.5%) from three mined facts (skip the file's title lines; integers for AddDimension and every time callback; no disjunctions for
customers), vs 7.3% without facts, 25% with one repair round per instance, 100% with hand facts. Chain C admitted a harmful fact (24.0%).
Unverified sheets collapse to 3–10% (wrong code facts), so verification is now what makes the method work; the mining score picks the
better chain without test labels. Variance across chains is the open problem (PREREG_FM.md).

## 2026-10-14 14:33 UTC: generality tests for FM2 started (model: gpt-oss-20b; task: job-shop with CP-SAT, H5)

- FM2g (PREREG_FM.md): chain D's sheet (mined by 120b) given to gpt-oss-20b, and a chain mined by 20b itself; 8042 restarted on GPU 2.
- H5 (PREREG_H5.md): job-shop la01–la40 (OR-Library, downloaded), CP-SAT reference on CPU, no-facts baselines for gpt-oss-120b low (new
  server 8045 on GPU 0) and 20b low; FM2 is applied there only if a model is below 70% feasible. CVRPLIB (a second routing set) moved to
  a JavaScript site; not used.
- FM2 replication chains E–H running on 8043 / 8044.

## 2026-10-14 15:31 UTC: FM2 does not replicate (mean 32.5% over six chains); harness bug found in H5 (CPU-time limit vs multi-threaded CP-SAT)

- FM2 replication (PREREG_FM.md): chains E–H reach 22.9 / 39.6 / 27.1 / 16.7% on the held-out instances; with C and D the mean is
  32.5% (16.7–64.6%). The final mining score barely predicts the test score (Spearman 0.38). The mined sheets do not help gpt-oss-20b
  (4.2% with D's sheet; 0% self-mined). D's 64.6% came from one fact only it found ("no disjunctions for customers"). FM3 (pool the six
  chains' verified facts, prune by leave-one-out on the mining set) is pre-registered and running.
- **Harness bug (H5):** sandbox.run_python sets RLIMIT_CPU = the wall timeout. Multi-threaded CP-SAT (default or 8 workers) exhausts it in
  2–11 s of wall time and is killed by SIGXCPU, which the sandbox reported as "tle": the job-shop "timeouts" (4–7 per run) and our own
  reference on la21 / la29 / la38 were this bug (re-run alone: "tle" after 2–11 s). Fixed: run_python takes cpu_s; run_jssp uses a
  wall-time limit only (cpu_s = 64 × timeout). The stored H5 programs are being re-scored (old files kept as *.cpulimit_bug.jsonl).
  Audit of earlier results: Solomon programs use the single-threaded routing solver and contest programs are plain Python; the old
  synthetic CP-SAT runs (co_*.jsonl) have 67 "tle" of 26,118 rows (0.26%), so any effect there is negligible, but those rows are suspect.

## 2026-10-14 15:40 UTC: H5 (job-shop la01–la40, CP-SAT) after the fix: 85% / 79% feasible and optimal when feasible

gpt-oss-120b low 35 / 33 of 40, gpt-oss-20b low 31 / 32 (before the CPU-limit fix: 30 / 29 and 28 / 28), mean gap ≤ 0.04%. Remaining
failures are invented CP-SAT attributes and (20b) wrong models. The textbook CP-SAT task needs no mined facts; the H3 routing results
(layout + integer + strategy facts) are about a less familiar API and file format. PREREG_H5.md.

## 2026-10-14 16:33 UTC: FM3 (pool + prune) fails; fact mining closed as a partial negative; H4b (helper controls) started

FM3: pooled 22 facts → 27.1% on held-out, pruned 18 → 20.8% (both below the mean single chain). Fact-mining verdict in PREREG_FM.md:
7% → 21–40% on average, noisy verification and prose, one-error-at-a-time facts; longer sheets hurt. H4b pre-registered and running:
is the helper harm on real problems about plausibility (unrelated helpers), the "should use" instruction (a "most are not needed"
header), and does it hold for gpt-oss-120b? 8043 stopped, 8042 (gpt-oss-20b) restarted.

## 2026-10-14 17:44 UTC: H4b (helper controls on real problems) and figures 9–11

gpt-oss-20b low: 8 related "should use" 33.4% (p = 0.001), 6 unrelated 35.6% (p = 0.16), related + "most not needed" 35.4% (p = 0.11),
vs 37.7% without helpers; gpt-oss-120b low unaffected (46.1 → 45.3%, p = 0.62). Any toolbox shortens the 20b model's reasoning; the
synthetic steering effects of F1 do not carry over at this size. Figures (poc/make_figures_hard.py, shared style poc/make_figures_style.py):
fig9 contest cost-accuracy frontier, fig10 routing facts compose, fig11 helpers on real problems.

## 2026-10-14 17:58 UTC: proposal restructured (Section 4.4 Hard benchmarks); H6 (newer model family) started; answer-extraction fix

- PROPOSAL.md / PROPOSAL_ko.md: the hard-benchmark results moved out of Limitations into a compact Section 4.4 (table, four bullets,
  figures 9–11); the long methods bullet condensed there; backups in results/archive/*_before_hard_section_2026-10-14.md.
- H6 pre-registered (PREREG_H6.md): Qwen3.8-27B-FP8 (local, newest open model; Qwen3.5 architecture, hybrid Mamba: vLLM 0.22 needs
  --max-num-seqs 64 --language-model-only) on the contest set (no-think ×3, + helpers ×3, thinking ×1) and Solomon (3 arms ×2).
- **Extraction fix (poc/llm.py):** this model's template opens <think> in the prompt, so outputs carry only </think>; chat() now keeps
  the text after the last </think>, and returns no answer when thinking was requested and never closed (finish = length). Audit: the
  old extraction took a code block from inside truncated reasoning in 11 of 190 truncated Qwen3-32B full-thinking attempts (H2c), 2 of
  which passed: strict full thinking = 91 / 311 = 29.3% (reported 29.9%); the 31-problem runs had none. Conclusions unchanged.

## 2026-10-14 18:33 UTC: H6 running on four Qwen3.8-27B servers

Qwen3.8-27B without thinking writes long explanations before the code (≈ 3k output tokens on an 1000-rated problem, vs ≈ 0.7k for
Qwen3-32B no-think), so the runs are ≈ 4× slower than planned; started two more servers (GPU 1, 2) and run seeds in parallel
(poc/queues/queue_s2_h6b.sh). Its cost will be reported per problem as for every other model.

## 2026-10-14 18:59 UTC: new methods pre-registered and running (user: keep suggesting and testing methods; check related work)

PREREG_V.md: V1 "verify once, reuse the program" for routing (offline, CPU; the baseline published solver benchmarks use: one program
per problem class, picked on a few instances) and N5 approximate-oracle differential testing for contest geometry (ALGO, NeurIPS 2023,
extended to continuous answers: sampled / grid oracles with loose tolerance, accepted only if they pass the statement's examples, plus a
counterexample repair round), compared with N2. N5 runs first on Qwen3.8-27B no-think (all GPUs serve it for H6; its no-think programs
solve 108 / 311 = 34.7%, vs 12.1% for Qwen3-32B). Next candidates: train-set repair before reuse (routing); draft-first for the
real-problem helper distraction.

## 2026-10-14 19:01 UTC: V1 first arm: one validated program reused beats per-instance generation by a wide margin (routing)

gpt-oss-120b low, plain arm: of 16 programs generated for the 8 mining instances, the best is feasible on 4 / 8; reused unchanged on the
48 test instances it is feasible on 45 (94%), median gap 1.35%, 40 within 5% of the reference, for 28k generation tokens in total
(0 per new instance). Per-instance generation in the same arm: 7% feasible at ≈ 1.8k tokens per instance. Other arms running.

## 2026-10-14 19:13 UTC: PROPOSAL / PROPOSAL_ko: new Section 0 (primer: how LLMs solve geometry and optimization problems)

Added at the top of both files (user request): the two problem families; six approaches (direct answer, LLM as optimizer, program,
solver formulation, evolved heuristic, LLM + symbolic prover) with representative work (venues checked: EoH ICML 2024, ReEvo NeurIPS
2024, AlphaEvolve 2506.13131, OPRO ICLR 2024, Chain-of-Experts ICLR 2024); worked examples from our pilot (polygon area direct vs
shoelace program; 40-node colouring direct vs heuristic vs CP-SAT, with the max() API crash) and two from the literature (OPRO, FunSearch).
Backups: docs/archive/PROPOSAL*_before_primer_2026-10-14.md.

## 2026-10-14 19:29 UTC: V1 interim, V2 started, H6 routing done

- V1 (PREREG_V.md): reusing the best of 16 mining-instance programs gives 45 / 48 held-out instances (94%) for gpt-oss-120b low and
  medium (plain) and 120b low + docs, at 27–56k tokens in total; it fails where no candidate is feasible anywhere (gpt-oss-20b plain /
  docs, Qwen3-32B plain). V2 (repair on the mining instances, then reuse) pre-registered and running for Qwen3.8 plain on 8049.
- H6 Solomon (Qwen3.8-27B no-think): plain 8.9%, docs 46.4%, integer reader + robust 81.3% feasible (H6-P4 holds).

## 2026-10-14 20:37 UTC: H6, V1, N5 results; V2 re-run, N5b, H6b started

- H6 (Qwen3.8-27B, newest local model): contest no-think 33.0% (Qwen3-32B 12.1%) at 4.2k tokens; × 3 + example check 44.7%; helpers no
  effect (82 lost / 81 gained); one repair round +8.1; full thinking cap-bound (226 / 311 unclosed at 16k; finished attempts 95% correct).
  Solomon: facts still needed and compose (8.9 / 46.4 / 81.3%). Template effort control works (low / medium / xhigh): H6b running.
- V1 complete: one reused program reaches 94–100% on 48 held-out Solomon instances whenever a candidate is feasible on ≥ 4 of 8 mining
  instances (gpt-oss-120b all arms; gpt-oss-20b with reader + robust snippet), at 20–56k tokens in total.
- N5 (Qwen3.8): approximate oracles accepted on 68% of problems; flag 39% of wrong example-passers, 6.4% of correct; counterexample
  repair −1 (false alarms) vs N2 +25. N5b (oracle selection, gpt-oss) and V2 with fixed empty-output feedback started.
- Servers: 8046 / 8049 Qwen3.8 (GPU 0 / 2), 8042 gpt-oss-20b (GPU 1), 8043 gpt-oss-120b (GPU 3); 8047 / 8048 stopped.

## 2026-10-14 21:32 UTC: N5b closed (good detector, no gain), V2 gives 20b a reusable program but Qwen3.8 "fixes" by abandoning the solver; V3, N6 started

- N5b: approximate oracles flag 53–68% of wrong example-passers at ≈ 4% false alarms (gpt-oss-120b / 20b), yet selection among 3 samples
  adds +0.3 / +0.7 and counterexample repair +0.7 / +0.6: when the first passer is wrong the others are too. Contest geometry is
  generation-bound, not check-bound.
- V2: gpt-oss-20b plain goes from no feasible candidate to a program feasible on 45 / 48 held-out instances (gap 6.3%) after three repair
  rounds on the 8 mining instances; gpt-oss-120b's repairs never fix the tight-window instances; Qwen3.8's accepted repair replaced
  OR-Tools by a due-date-sorted nearest-neighbour heuristic: feasible on 48 / 48, 56% longer routes (read). Feasibility-only acceptance
  rewards giving up on optimisation.
- Started: V3 (V2 + "beat our greedy baseline by 10% on the mining instances", label-free) and N6 (one retrieved solved geometry problem
  as an exemplar, by statement BM25 or by the model's own draft; prior art SolveRank, USACO, AlgoSimBench).

## 2026-10-14 22:50 UTC: V2/V3 closed (repair-before-reuse unreliable for weak models); N6: one retrieved solved problem helps gpt-oss-120b, hurts 20b

- V3: the quality guard blocks Qwen3.8's degenerate greedy program, but no good program follows; gpt-oss-20b's V2 success (round 3) did not
  recur (0 / 8 in all rounds): V1 reuse stands when a working candidate exists, the repair variants are closed.
- N6 seed 1: a statement-retrieved solved geometry problem lifts gpt-oss-120b low 132 → 147 / 311 (p = 0.032; unflagged +13, p = 0.035; no
  extra tokens; no retrieved solution solves its target) and lowers gpt-oss-20b low 125 → 112 (p = 0.09). Retrieval by the model's own
  draft is weaker for 120b. Seeds 2–3 running. Prior art: SolveRank, USACO episodic retrieval, AlgoSimBench.

## 2026-10-14 22:51 UTC: H6b (Qwen3.8 effort) and a cap caveat; H6c started

Qwen3.8 thinking at effort low 44.4% (10.8k tokens), medium 37.3%, default 26.0%; no-think 34.7%. Our caps bind for this model: 158 of
311 no-think answers hit the 6k cap and 150–226 thinking attempts the 16k cap; finished attempts are 66–95% correct, so every absolute
Qwen3.8 number is cap-limited (relative findings unaffected). H6c re-runs no-think and thinking-low with a 28k cap on the idle GPUs 0 / 2.

## 2026-10-14 23:29 UTC: N6 does not replicate (correction)

Over three seeds the statement exemplar adds +1.2 points for gpt-oss-120b (p = 0.39; seed 1 alone: +4.8, p = 0.032) and costs gpt-oss-20b
2.0 (p = 0.14). The seed-1 claim in PROPOSAL (both languages) is corrected. Lesson kept: a single-seed p-value on 311 problems is not a
result; every positive method claim needs ≥ 3 seeds.

## 2026-10-14 23:29 UTC: V1s started (how many candidates does reuse need?), V1 for Qwen3.8 arms (CPU); 8043 stopped

## 2026-10-15 00:29 UTC: V1s (reuse needs one working candidate; 64 draws suffice even for gpt-oss-20b without facts), H6c no-think, V1 on job-shop started

- V1s: gpt-oss-20b low plain, whose per-instance programs were never feasible (0 / 112), yields one reusable program among 64 draws:
  45 / 48 held-out (94%, median gap 5.9%) for 107k tokens; + docs 94% (gap 2.3%). Qwen3.8: docs 94%, reader + robust 100% (16 draws);
  plain none in 16.
- H6c: Qwen3.8 no-think with a 28k cap 48.2% (150 / 311; 6k cap: 34.7%); thinking-low with 28k still running.
- V1-JSSP pre-registered and running on CPU (PREREG_V.md). Servers 8042, 8046 stopped (idle); only 8049 (Qwen3.8, GPU 2) is up.

## 2026-10-15 00:32 UTC: D1 started: distillation with self-replay (F5) on real contest geometry

PREREG_D1.md. Split 206 train / 105 test (crc32 % 3); 431 training examples = up to 3 distinct verified programs per train problem from
the teacher runs (159 train problems have one); student Qwen3-8B no-think LoRA; arms A (teacher programs) and B (+ the E4 self-replay
set); evaluation on the test split (3 seeds) and the E4 synthetic battery. Training on GPUs 1 / 3, base Qwen3-8B runs on GPU 0.

## 2026-10-15 01:30 UTC: V1 on job-shop (100%); D1 distillation hurts (12.1 → 4.8% on held-out contest problems); D1b′ started

- V1-JSSP: one program chosen on 8 training instances solves all 32 test instances for both gpt-oss models (gap ≤ 0.03%).
- D1: LoRA-distilling 431 verified teacher programs into Qwen3-8B no-think lowers the held-out contest split from 12.1% to 4.8% (A) and 3.5%
  (with self-replay, B); self-replay still protects the synthetic tasks (hull 118 vs 77 of 120). Read: students copy the teachers' terse
  style (72 → 50 lines, 12 → 5 comment lines; teachers 49 / 3) and lose the step-by-step comments the no-think base writes while coding.
  D1b′ (pre-registered): restore comments by having the base annotate each teacher program (kept only if still correct), and a self-data
  (STaR-style) arm.

## 2026-10-15 02:29 UTC: D1 clean split; self-data helps a little, teacher data hurts; duplicate statements in CodeContests; H6c

- 37 validated problems have a duplicate statement (Div. 1 / Div. 2 copies); 17 D1 test problems duplicated train problems → clean split
  (88). On it: base 12.9%, teacher programs 5.3% (A) / 4.2% (B), the model's own 63 correct answers 15.2% (D, comments kept).
- H6c: Qwen3.8 no-think 48.2% with a 28k cap (no attempt at the cap, 6.4k tokens); thinking-low 50.5% at 15.9k (113 still at the cap).
- Arm E (comment-restoring rewrite) re-running after a lookup fix; 8049 stopped.

## 2026-10-15 03:29 UTC: D1 arm E: restoring comments does not undo the harm (6.8% vs base 12.9%); D2 (self-training at scale, learnable teacher data) pre-registered

## 2026-10-15 04:29 UTC: D2: teacher programs hurt even on problems the student can solve (5.3%); own data neutral (15.2% vs 8-seed base 14.6%); D3 started

The F5 contrast holds on real contest problems for an 8B student: verified teacher programs damage it whatever their difficulty or
comment density (A, E, L: 5.3–6.8% vs 12.9–14.6%), its own verified programs do not (S, D: 15.2%) but do not help either. Read: the student
adopts the teachers' idiom and makes new logic errors on easy problems (1064_A). D3: hinted self-solutions (the student rewrites teacher
solutions in its own style, verified), pre-registered and running.

## 2026-10-15 05:41 UTC: D3 closed (hinted self-solutions 11.0%: distillation line closed); V1G: reuse removes the F1 harm on synthetic tasks

- D3: 219 verified own-style rewrites of teacher solutions (128 problems) + own data: 11.0% on the clean split (base 12.9–14.6%).
  Distillation of a few hundred programs never helps the 8B student on held-out contest geometry (D1–D3).
- V1G: one program chosen on 5 validation instances with known answers and reused: hull under 8 helpers 17–21% per instance → 100% on the
  55 test instances (Qwen3-8B / 32B); pooled 97.8% vs 76%. Label-free metamorphic selection picks a consistent-but-wrong hull program for
  8B (0%). Accidental self-kill: a pkill -f matched my own shell (exit 144); no run was affected.

## 2026-10-15 06:29 UTC: V1A: model-written brute-force oracles make reuse label-free only where the model can write the oracle

Qwen3-32B hull: oracle correct, reuse 100%; Qwen3-8B hull: the oracle is wrong and consistent (prints 3 everywhere), reuse 0%. With 5 known
answers both reach 100% (V1G). Next: condense the methods into one table in the proposal (it has grown long).

## 2026-10-15 06:49 UTC: V1G-mix / V1G-tb: a subtly wrong closest-pair program passes 5 labelled checks (even with large instances); agreement among the
## passers on 10 unlabelled inputs removes it: reuse 100% on all 10 task-model pairs under 8 helpers (per-instance 18–100%, pooled 76%)

## 2026-10-15 07:03 UTC: proposal condensed (7,457 → ≈5,500 words; methods in one table in Section 4.4; backups in results/archive/*_before_condense_2026-10-15.md)
A subagent replaced the method prose with one table (M1–M5, F5 self-replay, N1–N6, FM, V1, V2/V3, V1A, D1–D3), trimmed Sections 0–3 and
F1–F5, and added two corrections that were only in FINDINGS (strict full thinking 29.3%; CPU-limit bug). Secondary numbers it removed are
listed in its report and remain in FINDINGS / PREREG files. V1G-tb added to the V1 row (both languages).

## 2026-10-15 07:48 UTC: H6d: asked for code only, Qwen3.8 no-think still reasons (in prose and in 88 comment lines): −14% tokens, −2.2 points; N2m running

## 2026-10-15 08:25 UTC: N2m: repair rounds give +4.8 / +2.3 / +0.6 points (gpt-oss-20b low); 3 rounds = 3 samples + check (47.9%) at 76% of the tokens

## 2026-10-15 08:29 UTC: V1c started: reuse cost curve (how many candidates, how many tokens) and Qwen3-32B with 64 candidates

PREREG_V.md. CPU: poc/analyze_reuse_curve.py runs every candidate once on the 8 mining and (if any mining success) the 48 test instances,
cached per arm, then resamples k candidates. GPU 0: Qwen3-32B-AWQ generates 48 more mining candidates per arm (plain, docs).

## 2026-10-15 08:41 UTC: PROPOSAL / PROPOSAL_ko Section 0 primer rewritten simply (user request; writing session)

≈ 600 → ≈ 400 words: plain-language problem definitions, a six-row table with one concrete example per approach, two short worked
examples (polygon area; 40-node colouring) with the same pilot numbers. Backups: docs/archive/PROPOSAL*_before_simple_primer_2026-10-15.md.

## 2026-10-15 09:11 UTC: V1c: cost of reuse ≈ tokens per candidate / share of working candidates; facts raise that share 6× (gpt-oss-120b: 94% at 14k
## tokens with the documentation snippet vs 28k without); Qwen3-32B: 0–1 working program in 64 (reuse 0–10%)

## 2026-10-15 09:35 UTC: V1c complete; Figure 12 (reuse cost curve vs a new program per instance)
Qwen3.8 + reader + robust reaches 100% of the 48 held-out instances from 4 candidates (5k tokens in total); per-instance generation costs
≈ 70–85k tokens for 0–82%. figs/fig12_reuse_cost.png added to both proposals.

## 2026-10-15 10:16 UTC: V1p: a portfolio of the top 3–5 reused programs does not fix the 3 tight-window instances (all copy the documentation's
## first-solution strategy: a shared failure); only the robust fact does. Qwen3.8 + docs median gap 1.35 → 1.00%. V1p closed.

## 2026-10-15 10:29 UTC: V1x started: do reused routing programs transfer from 100-customer Solomon to 200-customer Homberger instances? (CPU only)
60 Homberger 200-customer instances + SINTEF best-known table in results/h3/homberger200; poc/analyze_reuse_size.py; PREREG_V.md.

## 2026-10-15 10:58 UTC: V1x: reused programs transfer to 200-customer instances: 60 / 60 feasible (reader + robust programs of all three models), gap ≈ 4%

## 2026-10-15 11:29 UTC: H2d (gpt-oss-120b high effort, 3 seeds, GPUs 0–2) and V1x-400 (reuse on 400-customer instances, CPU) started; PREREG_H2C / PREREG_V

## 2026-10-15 12:28 UTC: V1x-400: reused programs stay feasible on 60 / 60 400-customer instances; gap 9.6–11.8% at their fixed 30 s search (1.5 → 4 → 11%
## from 100 to 400 customers). H2d still running (no seed finished after 1 h).

## 2026-10-15 13:03 UTC: compact proposal draft written (writing session): PROPOSAL_DRAFT.md + PROPOSAL_DRAFT_ko.md

≈ 1,250 words: problem and questions, background (six approaches, related work, gap), method, preliminary results (F1–F5 table with
the hard-benchmark numbers, methods in two sentences), plan, limitations. Numbers taken from PROPOSAL.md as of 08:25 UTC; PROPOSAL.md
stays the full document.

## 2026-10-15 13:28 UTC: V1x-TL: 4× more search time lowers the 400-customer gap only 11.4 → 10.1% (prediction ≤ 6% refuted): the limit is the solver
## (OR-Tools GLS), not the time budget; proposal wording corrected. H2d (120b high) still running after 2 h.

## 2026-10-15 14:30 UTC: H2d: gpt-oss-120b high effort is cap-bound at 30k (47.9%; 418 / 933 attempts unfinished; finished ones 86.8% correct); H2e (64k
## cap, sharded over 3 servers, run_cc CC_SHARD) started

## 2026-10-15 16:28 UTC: H2e: gpt-oss-120b high effort with a 64k cap: 66.2% (≥ 2300 band 50.3%) at 29.9k tokens per problem (one seed)

## 2026-10-15 17:28 UTC: H2e replication started (gpt-oss-120b high, 64k, seeds 2–3 on GPUs 0–3): the 66.2% headline is one seed; ≥ 3 seeds required

## 2026-10-15 18:21 UTC: PROPOSAL.md / PROPOSAL_ko.md replaced by the compact proposal (user: use the existing files, not new ones)

The 13:03 draft files (PROPOSAL_DRAFT*.md) were folded into PROPOSAL.md / PROPOSAL_ko.md and deleted. New structure (≈1.5k words):
0 primer, 1 problem, 2 related work, 3 method, 4 preliminary results (F1–F5 table incl. hard-benchmark numbers, methods paragraph,
figs 9 / 10 / 12), 5 plan, 6 limitations, appendix of files. Numbers updated to 16:29 UTC (gpt-oss-120b high 66% one seed; reuse
transfers to 200- / 400-customer instances). Full previous version: docs/archive/PROPOSAL*_before_compact_2026-10-15.md.
Note for the experiment loop: keep PROPOSAL compact; update numbers in place (HANDOFF §0).

## 2026-10-15 20:11 UTC: PROPOSAL.md / PROPOSAL_ko.md rewritten in plain language with examples and a measured-baselines table (writing session)

User: "write compactly and easily with examples" and "you can also measure baseline researches". Each finding F1–F5 now opens with
one real, shortened example (polar_sort hull; signed-area lattice; invented RegisterUnaryLongLivingCallback; float-parsing slip; LoRA
249 vs 1,067 tokens). Section 4 lists the published baselines already measured on our tasks (B1–B4, TroVE vote, AlphaCode filter +
MBR-exec, Self-Debugging, FrugalGPT-style cascade, Dynamic-Cheatsheet-style memory) next to our methods. No new runs (writing only).
Backups: docs/archive/PROPOSAL*_before_easy_2026-10-15.md.

## 2026-10-15 20:28 UTC: H2e replicated: gpt-oss-120b high effort 66.2% over 3 seeds (206 / 204 / 208) at 30.1k tokens; ≥ 2300 band 49.2%. Compact
## proposal: two numbers updated in place (both languages); nothing restructured.

## 2026-10-15 20:32 UTC: F2R pre-registered and started: F2 on Solomon (a needed travel-time helper that rounds to nearest vs rounds up vs warns)
Calibration without an LLM: a correct OR-Tools model with rounded travel times is feasible on 33 / 56 instances (23 window violations),
with rounded-up times on 56 / 56. Runs: gpt-oss-120b low (GPU 0), Qwen3.8 no-think (GPU 1). PREREG_F2R.md.

## 2026-10-15 21:29 UTC: F2R: F2 replicates on Solomon: a needed travel-time helper that rounds (instead of rounding up) costs 26–34 points of feasibility
## (gpt-oss-120b 95 → 69%, Qwen3.8 94 → 60%), failures are time-window violations, a warning comment does not help (64 / 65%).
## Compact proposal: F2 paragraph extended by one sentence, plan item (2) marked done (both languages).

## 2026-10-15 22:29 UTC: docs/notes/FIX_MAP.md: failure → fix map with token costs (draft for plan item 3), from the pre-registered results; plan item (3)
## in the compact proposal points to it (both languages). All planned experiments are done; nothing running.

## 2026-10-15 23:30 UTC: N7: routing contest failures by type (crash → repair, wrong answer → escalate) = plain escalation (50.3 / 56.4%); repairing
## wrong answers before escalating is what adds the point (N4 51.6 / 57.7%). FIX_MAP row corrected.

## 2026-10-16 02:29 UTC: V1x-J started (CPU, no LLM): reused job-shop programs on the 42 larger OR-Library instances (up to 50 × 10, 20 × 20); PREREG_V.md

## 2026-10-16 04:28 UTC: V1x-J: reused job-shop programs: 42 / 42 larger OR-Library instances feasible, mean gap 0.24–0.44% (max 4.3%) to a 120 s CP-SAT
## run; compact proposal reuse row extended in place (both languages)

## 2026-10-16 07:58 UTC: N8 (three-level cascade): low→medium→high 62.8% @ 19.0k, medium→high 65.0% @ 20.2k vs always-high 66.2% @ 30.1k (gpt-oss-120b,
## 3 seeds); N9 (repair at medium effort) and H7 (Qwen3.6-35B-A3B) started on GPUs 0, 2, 3

## 2026-10-16 08:33 UTC: N9: one repair round at MEDIUM effort fixes 41 / 139 low-effort failures vs 38 for a fresh medium attempt (n.s., seed 1);
## chaining them (repair, then fresh medium) gives 58.8% @ 9.6k tokens, a new contest frontier point (PREREG_N.md).
## H7 part 1: Qwen3.6-35B-A3B (≈ 3B active) no-think 42.6% @ 3.4k on contest geometry (3 seeds; × 3 + examples check 54.0% @ 10.3k),
## close to gpt-oss-120b low; Solomon per instance 0% plain, 37% with the integer reader + robust snippet (varied unit / index slips;
## PREREG_H7.md). N10 pre-registered and started (GPUs 1 + 3): can the fix / tool be chosen automatically from the first failure?
## Fix-menu factorial with Qwen3-32B-AWQ on 9 geometry tasks + 8 optimization problems; routers computed offline (PREREG_N10.md).

## 2026-10-16 08:59 UTC: N10: choosing the fix from the first failure's error signal does NOT beat the best single fix (geometry 88.9 vs 89.8%,
## optimization 73.0 vs 76.0% at equal tokens; leave-one-task-out). The right fix follows the problem type, not the error type;
## cheap per-domain defaults are strong (geometry: remove the toolbox 80.6% @ 0.4k, think 97.2% @ 6.1k; optimization: BM25 snippets
## 70% @ 0.5k). Oracle routing would save tokens in geometry (91.7% @ 1.0k vs 2.5k) and add 9 points in optimization (PREREG_N10.md).
## H7 V1 reuse: Qwen3.6-35B-A3B, reader + robust: one program from 16 candidates is feasible on 48 / 48 held-out Solomon instances
## (per instance 37%); plain: no candidate works (0 / 16), so reuse cannot help.
## (proposal: models list + negative-methods row updated in place, both languages)

## 2026-10-16 09:01 UTC: N11 (probe a few instances per problem, commit to the option with the best check pass rate): geometry 82.2% @ 3.2k
## (thinking 96.7% @ 6.2k), optimization 74.7% @ 4.2k (BM25 snippets 72.0% @ 0.5k): refuted. Two probes are too few and the label-free
## check is blind to consistent errors; per-domain defaults from the fix map stay the best choice. LLM router (N10 P4) running on GPU 1.

## 2026-10-16 09:04 UTC: N9 replicated (3 seeds): medium-effort repair = a fresh medium attempt (98 vs 100 of 381 failures, p = 1.0) at 12% fewer
## tokens; the chain (repair, then fresh medium) 59.9% @ 9.1k is +3.1 points over medium alone but only +1.3 on seed 3: not claimed.
## 2026-10-16 09:05 UTC: N10 P4: the LLM's own pick of the fix (85.2 / 69.0%) is worse than the best single fix (89.8 / 76.0%); N10-M2 (gpt-oss-20b) started on GPUs 0 + 2
## 2026-10-16 09:30 UTC: correction: the 10-16 entries from 08:45 on carried estimated times up to 30 min late; replaced by the times from queue_log (pre-registrations were written before each launch).
## 2026-10-16 09:32 UTC: N12 (seed 1): agreement between two tool conditions as the escalation gate is the most accurate label-free policy (Qwen3-32B geometry 99.1% @ 3.7k vs thinking 97.2% @ 6.1k; optimization 82.0%; gpt-oss-20b 100 / 93–95%), but the pre-registered token bounds fail; seeds 2–3 running. N10-M2 (gpt-oss-20b): router again no better; snippets again the best cheap default (PREREG_N10.md).
## 2026-10-16 09:34 UTC: N10-M3 (Qwen3.6): toolbox harmless in geometry; snippets the best cheap default in optimization (91% vs 64% with the full manual); thinking arm hit the 16k cap (setup failure), re-running at 48k on GPUs 1 + 3.

## 2026-10-16 09:53 UTC: PROPOSAL / PROPOSAL_ko reorganised around why it matters (writing session; user: "I can't feel that these are the important problems")

New Section 1 "Why this matters" (silent errors in deployed code; "give the model more" is the default and can hurt: full manual .07 <
no doc .23; token cost: high effort 4.4× the tokens of medium for +9 points). Results reordered: R1–R4 on real benchmarks first (facts;
verify once and reuse; pay for reasoning only when the examples fail, incl. N8 cascade 65.0% @ 20.2k vs always-high 66.2% @ 30.1k; R4 = N10:
fix by problem type, not error message), then mechanisms M1–M4 on generated tasks. Recent results added: N8, N9 (in R3 framing), N10, H7
(model list), V1x-J, N12 seed 1 (plan, preliminary). Corrected the generated-task count (13 geometry + 8 optimization, not 9 + 8).
Backups: docs/archive/PROPOSAL*_before_why_2026-10-16.md.
## 2026-10-16 09:54 UTC: N13: escalating also when the program disagrees with an approximate brute-force oracle recovers the points the examples-only cascade lost: medium→high 66.3% @ 25.7k vs always-high 66.2% @ 30.1k (N8 65.0% @ 20.2k); token bounds missed (PREREG_N.md).
## 2026-10-16 09:59 UTC: N13b: oracle only when medium passes the examples: 66.3% @ 24.7k (always-high 66.2% @ 30.1k). docs/notes/CRITIQUE.md written
## (user request: constructive criticism): main points: the unifying claim is "the check is the bottleneck"; reuse has close 2026 prior art;
## F1 vanishes for gpt-oss / Qwen3.6; cost ignores input tokens (BM25 prompt 1.8 × the sheet) and CPU; small suites (N12 vs thinking 3 vs 1 items).
## 2026-10-16 10:03 UTC: N12 geometry replicated (3 seeds): agreement gate = always-thinking accuracy (99.1%) at 61–79% of its tokens (Qwen3-32B).

## 2026-10-16 10:29 UTC: N12 optimization replicated (Qwen3-32B, 3 seeds: AGREE 81–85% vs thinking 67–68% vs snippets 69–72%, at 11 × the snippet
## tokens). Qwen3.6 thinking at 48k: correct whenever it finishes, but 27% of geometry items need > 48k (mean 32.6k tokens) for no gain over
## no-think (98.1% @ 1.0k): for Qwen3.6 thinking is a fix to avoid, and the agreement gate that escalates to it is dominated by the cheap default.
## 2026-10-16 10:35 UTC: N14 (adapt a verified program to a problem with one more rule): no gain (Qwen3-32B 0/60 like scratch; Qwen3.6 3/60 vs 2/60); the source lacks the new rule's API facts and adaptation even breaks verified lines (7/24). N14b (adapt + the new rule's snippet) started on GPUs 0 + 2.
## 2026-10-16 10:39 UTC: N14b: adapting a verified CVRP program plus the time-window snippet: Qwen3-32B VRPTW 18/24 optimal vs snippet alone 7/24 (p = 0.007, every seed) vs scratch 0/24; no gain from a TSP source to CVRP, Qwen3.6 +4/24 n.s.
## 2026-10-16 10:39 UTC: compact proposal (restructured by the writing session at 09:53) updated in place, both languages: R3 table + N13 row; related work + 2605.14141 / 2608.27296; plan: N12 replicated, N14b.
## 2026-10-16 11:29 UTC: N14c (job-shop + release dates): adapting the verified job-shop program: gpt-oss-120b 80/80 feasible vs 72/80 from scratch (p = 0.008), Qwen3-32B 30/80 vs 4/80 (p < 1e-6), failing source 0/80; Qwen3-32B's failures rewrite lines the rule does not touch. gpt-oss-20b TSP→CVRP adaptation hurts (13 vs 24/36). N14d (minimal-edit instruction; verify the adaptation once and reuse) and N14c on two more models started (PREREG_N14.md).
## 2026-10-16 11:35 UTC: N14d: 'change as few lines as possible' lifts Qwen3-32B's job-shop adaptation from 30/80 to 54/80 feasible (p = 0.0005; no effect on VRPTW, 17 vs 18/24); one verified adapted program covers all 32 held-out release-date instances (gpt-oss-120b, gap 0.00%).
## 2026-10-16 11:36 UTC: FIX_MAP: two rows added (consistent errors → a different second opinion; a problem gains a rule → minimal-edit adaptation + the new rule's snippet + reuse). Proposal plan line updated in place (both languages) with N14c / N14d.
## 2026-10-16 12:30 UTC: N14c on 4 models: adapting the verified job-shop program to release dates gives 80/80 for gpt-oss-120b, gpt-oss-20b and Qwen3.6 (scratch 72, 61, 59) and one reused adapted program covers 32/32 held-out for Qwen3-32B (its scratch candidates never work). N14e: tardiness helps Qwen3-32B (18 vs 2/80); flexible job-shop: adaptation hurts gpt-oss-120b (36 vs 67/80 with the snippet) while the snippet alone helps (76). N15 (which solver library: CP-SAT / routing / MIP / none / free choice) pre-registered and started on GPUs 0–2.
## 2026-10-16 12:30 UTC: proposal plan clause (both languages) and FIX_MAP 'gains a rule' row refined with N14c / N14e (adaptation hurts a strong model when the rule restructures the solver model).
## 2026-10-16 12:48 UTC: N15 (which solver library): free choice = habit (CP-SAT, routing for VRP); the best library differs by model and problem (Qwen3-32B bin packing MIP 23/24 vs CP-SAT 1/24; Qwen3.6 TSP plain Python 22/32 vs routing 2/32); hindsight best per problem +4 to +18 points over free choice. A 3-instance tournament helps Qwen3-32B (+14) but hurts gpt-oss-120b (−9); a per-instance portfolio of all libraries (best feasible objective, no reference) beats every single policy for all 4 models (64.5 / 84.5 / 78.5 / 94.5%) at ≈ 4 × tokens; at equal budget a second library beats a second sample only for the weak-habit models (PREREG_N15.md).
## 2026-10-16 12:49 UTC: proposal R4 extended in place by one sentence (both languages): solver library = tool choice (N15 / N15d). N15e (library choice on job-shop la01–la40, 4 models) started on GPUs 0–3.
## 2026-10-16 14:21 UTC: N15e (job-shop library choice): every model's default is CP-SAT; CP-SAT is near-optimal when it runs, plain Python almost always feasible but 25–430% worse, MIP times out; portfolio of all four: 79–80/80 within 5% for Qwen3.6 / gpt-oss-20b / gpt-oss-120b. N15f: a fallback cascade (default, then other libraries only when the plan is infeasible) keeps 96–98% of the portfolio's accuracy at 34–84% of its tokens (synthetic) and the same feasibility at 50–91% (job-shop). Seed-3 replication of N15 + N14c started on GPUs 0–3 (Qwen3-32B job-shop cap 4096 instead of 8000; its programs average 0.9k).
## 2026-10-16 14:21 UTC: FIX_MAP row added (solver library by habit → default + fallback cascade / portfolio); proposal R4 sentence extended in place (both languages) with the cascade numbers.
## 2026-10-16 14:34 UTC: seed-3 replication done: N15d portfolio (66.0 / 84.7 / 78.3 / 93.3% vs best single 50.0 / 72.3 / 60.3 / 81.7%) and N14c (adapt verified job-shop program: 120/120 for three models, Qwen3-32B 82/120 with minimal edit vs 12 from scratch, all p < 1e-4) hold on 3 seeds; token / failure-kind profiles added (libraries crash, plain Python is suboptimal: complementary). User instruction 14:3x: analyses report tokens, finish reasons, failure kinds and log-probs where stored, not only accuracy.
## 2026-10-16 14:45 UTC: N16 (log-probs, per user request): invented OR-Tools API names have much lower token log-probs than real ones (AUROC 0.84 / 0.86 / 0.90 for Qwen3-32B / Qwen3.6 / Qwen3-8B), but triggering documentation on low confidence or on execution failure never beats always giving the exact snippet, which is also the cheapest (shorter programs: 0.47 vs 0.54k, 0.66 vs 0.95k output tokens).
## 2026-10-16 15:30 UTC: N14b addendum: gpt-oss-20b VRPTW adapt + snippet 21/24 vs snippet 18/24 at fewer tokens (n.s.). N16b: calls to unneeded geometry helpers are as confident as needed ones (AUROC distractor-lower 0.21 / 0.06): steering is invisible in log-probs, unlike invented API names (0.84–0.90). P1 (prompt rewording robustness on contest geometry, gpt-oss-120b + Qwen3.6, 2 rewordings × 3 seeds) started on GPUs 0–3.
## 2026-10-16 16:28 UTC: P1: rewording the contest prompt (two variants × 3 seeds × 2 models) changes accuracy by +1.3 to +1.9 points and tokens by ≤ 6%, within seed noise; per-problem agreement with the original ≈ seed-to-seed agreement (CRITIQUE item 9 addressed).
## 2026-10-16 16:31 UTC: N17: a second model (Qwen3.6) as the second opinion flags 41% of wrong example-passing gpt-oss-120b programs at 8.8% false alarms; cascade 65.5% @ 25.2k (brute-force oracle: 66.3% @ 24.7k). N18 (Qwen3.6 contest programs with log-probs) running on GPUs 0–2.
## 2026-10-16 16:32 UTC: docs/notes/CHECKS.md (user question 'isn't it solved by verifying the output?'): the cheap checks never reject a correct program but accept 24–37% of wrong contest programs (examples), 24–36% of wrong geometry programs (symmetry), 61–79% of wrong plain-Python optimization plans (feasibility); second opinions catch 41–49% of the contest misses at 7–9% false alarms.
## 2026-10-16 16:32 UTC: proposal R3 first sentence extended in place (both languages): the examples check never rejects a correct program but accepts 24–37% of wrong ones (CHECKS.md).
## 2026-10-16 16:51 UTC: N18: token log-probs of Qwen3.6 contest programs separate wrong from correct example-passers only weakly (AUROC 0.61 mean, 0.69 min); most low-confidence tokens are in the reasoning comments; confidence-based selection +1.3 points. N12-M4 (agreement gate on Qwen3-8B) started on GPUs 0–2.
## 2026-10-16 17:09 UTC: N12-M4: the agreement gate on Qwen3-8B geometry beats always-thinking on every seed (99.1 / 98.1 / 97.2 vs 97.2 / 95.4 / 94.4%) at 71–81% of its tokens. N19: the same gate on gpt-oss-120b contest programs (with vs without helpers) fails (56.9% @ 11.8k vs 56.8% @ 7.1k): gpt-oss's two programs share their mistakes; a second opinion pays only when its errors are independent.

## 2026-10-16 17:29 UTC: PROPOSAL / PROPOSAL_ko updated with recent results and figures (writing session; user: "update ... with examples", "explain with visualizations")

New figures (poc/make_figures_explain.py; same style as the other figures; palette validated): fig0 fix flow (which fix for which
situation), fig13 checks leak (CHECKS.md), fig14 reasoning policies for gpt-oss-120b (N2, N8, N13), fig15 agreement gate (N12, 3 seeds),
fig16 adapting a verified program (N14c, 3 seeds), fig17 solver-library portfolio (N15d, 3 seeds). Text: R2 now includes adaptation
(N14), R3 the leaky checks + brute-force escalation (N13) + second opinion (N12, with the gpt-oss failure N19), R4 the library choice
(N15 / N15f); methods table updated (log-prob-triggered docs N16 negative). Backups: docs/archive/PROPOSAL*_before_figs_2026-10-16.md.
## 2026-10-16 18:01 UTC: X1 (short-answer competition math, MATH-500 + AIME 24/25; PREREG_X1.md written by the writing session at 17:53) started by the experiment session at the user's request on GPUs 0–3: Qwen3-32B / gpt-oss-20b / Qwen3.6, text vs program vs thinking, 3 seeds; addendum X1-P6 (text–program agreement less leaky than text–text). poc/run_math.py rewritten (the prepared version was overwritten by mistake).
## 2026-10-16 18:10 UTC: X2 pre-registered (verify once, reuse on GSM-Symbolic numeric variants: one checked solver per template vs per-instance answers, priced in tokens); starts after X1. X1 harness bug (math_verify timeouts fail in threads → every grade 0) found from the raw outputs and fixed by regrading in worker processes; gpt-oss-20b low regraded: text 85.9–86.6%, program 69.1–70.2% (560 problems × 3 seeds).

## 2026-10-16 18:15 UTC: PROPOSAL / PROPOSAL_ko: an example for every benchmark and every method (writing session; user request)

Section 2 now has a benchmark table with one real example each (Codeforces 1620_B with its sample input/output, Solomon c101 customer 1,
OR-Library la01 job 1, a generated hull instance, generated optimization sizes). Section 5's two tables now describe what each
published baseline and each of our methods does with a concrete example. No new results. Backups: docs/archive/PROPOSAL*_before_examples_2026-10-16.md.
## 2026-10-16 18:25 UTC: user: the proposal reads as heuristic / debugging; reframed in docs/notes/PROPOSAL_CORE_DRAFT.md (three failure mechanisms with label-free signatures — missing knowledge, context steering, reasoning difficulty — each needing a different resource; compute allocation by mechanism vs by difficulty) and pre-registered the decisive test U1 (PREREG_U1.md; runs after X2). Prior art checked: Snell et al. ICLR 2025 (difficulty-based allocation), verifier blind spots (Rajput et al. 2609.01345: blind spot 0.12 → 0.55 with student size on MATH), correlated errors (Kim et al. / Goel et al. ICML 2025).
## 2026-10-16 18:29 UTC: X1 part 1 (gpt-oss-20b, competition math): a program answer agreeing with the text answer is wrong 0.3% (MATH-500) / 6.8% (AIME) of the time vs 1.5% / 13.5% for two text samples (decorrelation holds beyond computation), but the gate does not save tokens because medium effort is cheap for this model. X2 restarted on the idle GPUs 0 + 2; U1 waits for X1 and X2.
## 2026-10-16 18:34 UTC: user: computation-only topics feel superficial / debug-like. Pre-registered a research question (docs/prereg/PREREG_VIEWS.md): when can a model catch its own mistakes? Error correlation between a model's views (tool on/off, library, text vs program, recall-first) should predict the leak and gain of self-verification across ≥ 15 measured settings, and knowledge errors should be shared across views (factual QA test with PopQA after U1). Computation becomes the measuring instrument (exact labels), not the topic.
## 2026-10-16 18:39 UTC: user: go beyond computation. Math ladder pre-registered: X1 competition math (running), X2 numeric-variant word problems (running), X3 verbal optimization problems → models (NL4OPT + IndustryOR; PREREG_X3.md; after X2), X4 formal proofs in Lean 4 (miniF2F; Lean v4.15 + Mathlib being installed under /SSD/lean_postech; predictions in PREREG_X3.md). U1 moved after X3.
## 2026-10-16 19:07 UTC: X3 part 1 (gpt-oss-20b, words → optimization models): failures move from API facts to modelling (70% of failures run and print a wrong value; the API snippet adds only +2–3 points); two solver formulations by the same model agree on wrong answers as often as two samples (IndustryOR 28.6% vs 30.8% of agreeing pairs wrong), while a text-reasoning view is more independent (12.3%). X2 solver runs had crashed (int ids) → fixed and re-running on GPU 2.
## 2026-10-16 19:29 UTC: X2 (math word-problem variants): one solver per template reused across variants is only as good as its check: verified programs are 99–100% right on held-out variants, but only 47–60% of templates get one in 4 tries (programs overfit the shown instance or misparse numbers); with per-instance answers as fallback, reuse gains +1.7 / +2.0 / −0.2 points at 59–89% of the tokens. Reuse pays where per-instance answers are unreliable (routing 7%), not where they are already 91–95%.
## 2026-10-16 19:30 UTC: X3 part 2: Qwen3-32B replicates gpt-oss-20b on word problems → optimization models (API snippet +0–2 points; mip–CP-SAT agreement wrong 26% vs mip–mip 30% vs mip–text 13.5% on IndustryOR). X4 (Lean 4 miniF2F, gpt-oss-20b, k = 8) started on GPU 2.
## 2026-10-16 20:29 UTC: X4 part 1 (Lean 4 miniF2F, gpt-oss-20b): 66 / 244 statements proved with 8 attempts (15.8% of attempts); a third of the attempts that give a proof cite Mathlib lemmas that do not exist (Nat.pos_of_gt, Nat.sum_range, old Lean-3 spellings), the proof-world analogue of invented OR-Tools methods. Feedback round vs fresh sample and Qwen3-32B with log-probs running on GPU 2.
## 2026-10-16 21:35 UTC: X4 part 2 (Lean, Qwen3-32B with log-probs): 31 / 244 proved (gpt-oss-20b 66); 38% of attempts hit unknown names, but token confidence barely separates invented Mathlib names from real ones (AUROC 0.60 vs 0.84–0.90 for invented OR-Tools methods) — plausible, compositional names are written confidently. X4-P2 refuted: telling gpt-oss-20b 'these names do not exist' fixes 3.4% vs a fresh sample 3.2% (and it invents more names). Fact feedback with similar existing names + types (X4-P2b) running on GPU 2.
## 2026-10-16 21:44 UTC: X4-P2b: giving the 3 most similar existing Mathlib names + types fixes 2.7% of attempts with invented lemma names (plain feedback 3.4%, fresh sample 3.2%): in proofs an invented lemma usually stands in for a step that is not a library fact (337 / 412 attempts have other errors too), so — unlike invented OR-Tools methods — it is a reasoning gap, written confidently and not cured by facts.
## 2026-10-16 22:30 UTC: X1 part 2 (Qwen3.6): no-think text 98.3% / 68.3% beats thinking 91.7% / 47.8% (213 answers cut at 28k), so every gate escalating to thinking loses. X3 part 3 (Qwen3-32B thinking): thinking LOWERS NL4OPT from 78.0% to 56.7% at 16 × the tokens — while reasoning, the model writes the lower-level objective API and invents SetMaximize / SetMinimize (104 crashes in one seed): compute can add knowledge failures. U1 started on GPUs 0, 2, 3 (Qwen3-8B on port 8056 after a port-guard refusal).
## 2026-10-16 22:32 UTC: X4 part 3 (Lean, Qwen3.6): 133 / 244 miniF2F statements proved with 8 attempts (38% of attempts; gpt-oss-20b 66, Qwen3-32B 31); its invented Mathlib names do carry low confidence (AUROC 0.81 vs 0.60 for Qwen3-32B): the 'knowledge gap = low confidence' signature holds for some models only. U1 analysis script written before any U1 output (poc/analyze_u1.py).
## 2026-10-16 23:47 UTC: VIEWS meta-analysis (56 settings): different views are much less error-correlated than resampling (math text–program kappa 0.12–0.38 vs text–text 0.41–0.68; geometry toolbox on/off 0.19–0.34 vs 0.54–0.79; word problems mip–text 0.20–0.36 vs mip–mip 0.59–0.73), and for a fixed first view the less correlated second view leaks less in 13 / 14 comparisons; but kappa does not predict leaks ACROSS domains (pre-registered Spearman 0.36 < 0.7) because wrong answers coincide at domain-specific rates. Two solver formulations of a verbal problem are nearly as correlated as resampling.
## 2026-10-17 00:29 UTC: incident: all four vLLM servers terminated at 2026-10-16 23:51:25 (NCCL watchdog in every engine at once). Lost: U1 thinking arms and the X1 Qwen3-32B thinking runs (1,674 / 1,680 done, written only at the end). Harnesses now write rows as they complete (run_geo_cross, run_math with resume). All four GPUs re-running the lost arms. VIEWS meta-analysis was unaffected.
## 2026-10-17 02:56 UTC: second incident: servers starved again (NCCL watchdog stuck 480 s at 01:51–01:59 and 02:17–02:25) while the host load average was ~2,800 and swap was full (other containers); I also found and killed 5 orphaned Lean processes of mine (one 16 GB, 5 h; subprocess timeout killed lake but not lean → Lean checks now kill the whole process group). run_geo_cross / run_co got --resume; the thinking arms re-run under a retry loop (up to 6 attempts, finished rows kept). VIEWS-P4: shared text–program errors are on harder math problems (3 / 3 models, small n), but shared IndustryOR errors are on easy problems with ambiguous gold values (e.g. integer vs continuous).

## 2026-10-17 03:11 UTC: PROPOSAL_slides.pptx (writing session; user: proposal PPT, compact, easy, examples, visualizations, default template)

14 slides in the default Office look (white, Calibri, Office accent colours; layouts Title Slide / Title Only), built by
poc/make_slides.js (pptxgenjs; run with NODE_PATH pointing at a pptxgenjs install). Content: background + why programs, why it matters,
core claim (three mechanisms from docs/notes/PROPOSAL_CORE_DRAFT.md), benchmarks with examples, mechanisms 1–3 (figs 10, 15, 13, 14), views
kappa (VIEWS meta-analysis), reuse / adapt (figs 12, 16), the math ladder X1–X4, baselines, progress (U1 running), takeaways; speaker notes on
every slide. Validated (validate.py) and visually checked via LibreOffice renders.
## 2026-10-17 03:23 UTC: U1 partial (Qwen3-8B only): allocating by mechanism beats allocating by difficulty at equal tokens in optimization (36.0% vs 27.0% @ ~4.9k, the fact chosen on 49 items) and narrowly in geometry (95.4% vs 94.4% @ 5.7k); pooled 66.8% vs 62.0%. Qwen3-32B and Qwen3.6 still running.
## 2026-10-17 03:29 UTC: raw-output check of the running U1 thinking arms: Qwen3-32B geometry think 88/90 correct at 6.0k tokens, optimization 62/92 at 5.5k (all finished); Qwen3.6 think hits the 28k cap on all 5 finished geometry items and 11/49 optimization items: pre-registered a sensitivity analysis with the same-condition 48k run from N10-M3 (PREREG_U1.md addendum). X1 Qwen3-32B thinking re-run: 138/560 rows per seed, all finished, 3.8–4.1k tokens. Host swap is full again (load ~120).
## 2026-10-17 03:30 UTC: VIEWS-P5 (factual QA, PopQA, Qwen3-8B): knowledge errors are shared across views (error kappa 0.75–0.91 vs 0.12–0.38 for text vs program in math); when two views agree the answer is still wrong 38–63% of the time (math 0.3–19%); thinking adds +1.8 points at 70× the tokens. Self-checks catch format / tool / reasoning-path errors, not missing facts.

## 2026-10-17 03:47 UTC: PROPOSAL_slides.pptx simplified for beginners (writing session; user: too much text, unclear figures)

8 slides, no research figures: each result slide shows one concrete example (code line, check outcome, step flow) plus 2–4 plain bars drawn
as shapes; plain-language titles (three kinds of mistakes: doesn't know the library / distracted by extra tools / the problem is hard).
Generator: poc/make_slides.js.
## 2026-10-17 04:15 UTC: PROPOSAL_slides.pptx (writing session): slides 6–9 rebuilt as concrete stories (slide 6 two prompts → wrong vs right OR-Tools call; slide 7 adds the 4-strategy bars, Qwen3-32B geometry 3 seeds: helpers 59% @ 0.6k, task only 77% @ 0.4k, always think 98% @ 5.9k, compare-then-think 99% @ 4.3k; slide 8 real samples of 1064_A / 630_O; slide 9 retitled 'Same problem every day: check one program, reuse it'). Generator: poc/make_slides.js.
## 2026-10-17 04:31 UTC: U1 (decisive test) done: allocating facts / second opinions / thinking by mechanism beats allocating thinking by difficulty at equal tokens (82.5% vs 73.9% pooled over 3 models × 2 domains; difficulty is even below uniform 77.1%). But an exploratory baseline — give the fact to every item first, think only when its check fails — reaches 87.2% at far fewer tokens: the win is 'facts before compute', not signature routing. VIEWS-P5 on Qwen3.6 (PopQA): kappa direct–recall 0.74 again, shared errors concentrated in the least popular facts; thinking +5.0 points at 200 × tokens.
## 2026-10-17 04:34 UTC: U1b (experiment session): a Snell-faithful baseline (difficulty bins that may pick any arm, LOTO) reaches 78.7% pooled vs MECHANISM 82.5% at 80% of its tokens; always-FACT 79.3% at 0.44k tokens beats every adaptive policy in optimization for all three models; with Qwen3.6's 48k thinking run the ordering holds. Together with the fact-first baseline (87.2%) recorded at 04:31: 'facts before compute' is the result. U1r (seeds 2–3 of the cure arms, 3 models) started on GPUs 0, 2, 3 to replicate it (positive claims need ≥ 3 seeds).
## 2026-10-17 04:35 UTC: VIEWS-P5 replication (PopQA, Qwen3.6) recorded in PREREG_VIEWS.md: kappa direct–recall 0.74 (holds); thinking +5.0 (refutes ≤ +2) but its net gain is +28 items in the most popular bin and −1 in the least popular (Qwen3-8B: +28 / −3): compute recalls weakly-held facts, never adds missing ones. 37 / 1,500 thinking runs hit the 4,096 cap (all wrong).
## 2026-10-17 05:36 UTC: U1r Qwen3-8B replicated on cure seeds 2–3: FACT-FIRST-THEN-THINK best on every seed (73.6 / 72.6 / 72.1% vs MECHANISM 66.8 / 67.3 / 64.9%, DIFFICULTY 62.0 / 60.6 / 62.0%) at fewer tokens than MECHANISM. U2 pre-registered and started on GPU3: does it survive with RETRIEVED facts (BM25 snippets / a retrieved algorithm note instead of hand-written ones)?
## 2026-10-17 05:38 UTC (hourly-cron session): X6 pre-registered (PREREG_X3.md): Qwen3-32B thinking on NL4OPT/IndustryOR loses 21 points (56.7% vs 78.0%) because 314 of its 343 crashes call one invented method (Objective().SetMaximize / SetMinimize); new arm 'thinkf' = thinking + the 6-line pywraplp snippet tests whether the fact makes thinking pay on external benchmarks, and FACT-FIRST-THEN-THINK vs think-first. Queued for GPU1 after the X1 re-run (poc/queues/queue_s2_x6.sh; GPU3 went to U2). run_nlopt.py now writes rows as they finish and resumes. U1r partial (Qwen3-8B cure seeds 2 / 3; full record left to the experiment session): MECHANISM 67.3 / 64.9% vs DIFFICULTY 60.6 / 62.0% (U1r-P1 holds for this model); FACT-FIRST-THEN-THINK 72.1% @ 4.4k (seed 3) is again the best policy. PROPOSAL / PROPOSAL_ko: one row added to the 'our methods' table (facts first, then think).
## 2026-10-17 05:46 UTC: U2 (retrieved instead of hand-written facts), Qwen3-8B, 3 seeds: retrieved-first-then-think 72.1 / 68.3 / 68.8% pooled vs hand-written fact-first 73.6 / 72.6 / 72.1% vs difficulty 62.0 / 60.6 / 62.0% (U2-P1/P2/P3 hold for this model). BM25 often retrieves a near-miss note in geometry (hull → ray casting: 1/12 vs 12/12), but the check routes those failures to thinking, so a wrong fact costs tokens more than accuracy. PREREG_U1.md. Qwen3-32B / Qwen3.6 U2 + U1r still running.
## 2026-10-17 06:33 UTC: U1r + U2 done (3 models × 2 domains × 3 cure seeds). Pooled per seed: FACT-FIRST-THEN-THINK 87.2 / 87.3 / 86.5% @ ≈ 2.5k tokens > RETRIEVED-FIRST-THEN-THINK (BM25 facts, deployable) 84.1 / 84.1 / 83.5% @ ≈ 3.2k > MECHANISM 82.5 / 83.5 / 82.2% @ 4.2–4.7k > uniform 76.6–77.1% > DIFFICULTY 73.9 / 74.0 / 75.5%; ALWAYS-FACT 79% @ 0.44k is the cheapest. All pre-registered U1r / U2 predictions hold. X6 (does the API fact make thinking pay on NL4OPT / IndustryOR; Qwen3-32B, Qwen3-8B, Qwen3.6) started on GPUs 0 / 3 / 2 at 06:31 (PREREG_X3.md X6 + addendum).
## 2026-10-17 07:17 UTC: repository reorganized for git (user request): docs/ (FINDINGS.md, prereg/, notes/, archive/), poc/queues/ (all queue scripts), docs/README.md index of experiments by theme; path references updated in 160 files (running queue scripts moved but not edited).
## 2026-10-17 07:37 UTC: simpler execution (user request): bench.py = one entry point (list / serve <model> / run <benchmark> <arm> / analyze <id>) that fills in the settings of the reported experiments; the 72 Python files that hard-coded /NAS/SJ/POSTECH/nlp now compute the repository root from their own location. Live check from another folder: `bench.py run popqa direct --model q8b` gave 308/1,500 = 20.5% (the recorded Qwen3-8B direct run: 20.7%); test output deleted.
## 2026-10-17 08:39 UTC: X1 Qwen3-32B thinking done (re-run after the server crashes): thinking 97.4 / 77.2% (MATH-500 / AIME) @ 5.4k vs text 86.1 / 19.4% @ 0.95k; the text == program gate keeps 97.2% at 77% of the tokens on MATH-500 but costs more than always thinking on AIME; text–program agreement leaks 4× less than text–text (X1-P6 holds). Grader bug fixed: sympy's '6 + 9 i' was not matched to '6+9i' (program accuracy +0.6–0.7 points, all models regraded). Raw check of Qwen3.6 thinking: 213 / 1,680 runs ended at the 28k cap with no answer, incl. level-1 problems, and our sampling (T 0.7, no presence penalty) differs from the model card (T 1.0, top_k 20, presence_penalty 1.5, 80k budgets): X1-Q36R pre-registered and started on GPU1 (PREREG_X1.md). The same setup affects the Qwen3.6 thinking cells of U1 / U2 / X6.
## 2026-10-17 08:40 UTC: X6 Qwen3-32B (NL4OPT + IndustryOR, 3 seeds; PREREG_X3.md): the 6-line API fact turns thinking from −13 points (52.0% vs 65.4%, 314 invented Objective().SetMaximize calls) into +6 (thinkf 72.0% vs mipf 66.2%; IndustryOR +16); fact-first-then-think 72.4% @ 1.3k tokens matches always-thinkf (72.0% @ 5.5k) at 23% of the tokens. X6-P2 holds, P1 / P3 mostly (71 invented calls remain with thinking on; think → mipf is 1.6 points better at 5 × the tokens).
## 2026-10-17 09:33 UTC: X6 Qwen3-8B: thinkf 72.2% @ 7.2k > think 67.7% > mipf 51.7% @ 0.45k > mip 34.3%; fact-first-then-think 68.3% @ 2.45k (−3.9 vs always-thinkf at 34% of its tokens: 22% of fact programs run but print a wrong value for both models; thinking would fix ~31% of those, and it breaks 71 right ones for Qwen3-32B but only 35 for Qwen3-8B, so the leak costs only the 8B model). For the 8B model thinking pays even without the fact (P5 refuted); for Qwen3-32B it pays only with it. Card sampling check so far: 0 of 413 X1 and 0 of 206 X6 Qwen3.6 thinking runs hit the 80k cap (old setting: 73 of 1,087 X6 runs at 30k). U1-Q36C (Qwen3.6 U1 thinking arm, card sampling) pre-registered and started on GPU3.
## 2026-10-17 10:13 UTC: user: consider smaller models = models that run on one RTX 3090 (24 GB). SIZE pre-registered (docs/prereg/PREREG_SIZE.md + addendum with a 24 GB fit table): Qwen3-1.7B / 4B / 14B-AWQ (downloading) and gpt-oss-20b on the U1 suites and X6, vs the existing Qwen3-8B / 32B; cost also as active parameters × tokens; cross-size cascade (small model + fact, escalate to Qwen3-32B thinkf). Existing data already says Qwen3-8B (fits a 3090) with fact + thinking matches Qwen3-32B on X6 (72.2 vs 72.0%). To free a GPU, the old-sampling Qwen3.6 X6 thinking arms were stopped by PID (partial 555 / 529 rows; replaced by the card-sampling X6c arms); its mip / mipf finish first.
## 2026-10-17 10:37 UTC: SIZE part 1 (gpt-oss-20b, fits one RTX 3090): X6 thinkf 74.9% @ 2.3k tokens > Qwen3-32B thinkf 72.0% @ 5.5k (5% of its compute); fact-first-then-think 73.0% @ 0.7k; U1 optimization fact-first-then-think 94–97% @ ≈ 1k vs Qwen3-32B 79–85% @ ≈ 2.8k (geometry at ceiling, 100% without help). Paused the Qwen3.6 card-sampling runs X6c (423/2,070) and U1-Q36C (35/624): vLLM 0.22 builds a CPU tensor of every request's output tokens each step when presence_penalty is set, so 80k-token thinking ran at 0.6–1.1k tok/s (ETA 7–18 h); GPUs 0 / 3 went to the 3090-class lanes (Qwen3-14B-AWQ, Qwen3-4B; Qwen3-1.7B on GPU2). X1-Q36R continues on GPU1 (694/1,680). To try when resuming: VLLM_USE_V2_MODEL_RUNNER=1 (penalties kept on the GPU).
## 2026-10-17 11:32 UTC: SIZE part 2 (no-thinking arms, all sizes): on X6 the API fact's gain grows strictly as the model shrinks: +0.8 (Qwen3-32B), +7.9 (14B-AWQ), +17.4 (8B), +31.3 (4B), +44.4 points (1.7B: 0.1% → 44.5%; its crashes are invented OR-Tools attributes). SIZE-P1 holds on X6, not on the generated U1 suites (they also need the algorithm; 1.7B cannot use the optimization snippet). Thinking arms of 1.7B / 4B / 14B-AWQ still running; X1-Q36R 1,024 / 1,680.
## 2026-10-17 12:35 UTC: SIZE, Qwen3-1.7B on the U1 suites (3 cure seeds; results/u1_q17.log): FACT-FIRST-THEN-THINK 42.3 / 44.7 / 42.3% @ 7.2k tokens is again the best policy (uniform gated thinking 36.5–39.9%, MECHANISM 29.8–33.2%, DIFFICULTY 28.8–36.1%, ALWAYS-FACT 25% @ 0.55k); almost all of it is geometry (75.9% with fact-first, seed 1) — the 1.7B model solves ≤ 10% of the optimization suite with any fix (oracle 10%). Its thinking hits the 16k cap on 13% of optimization items (4B: 20%; 8B: ≈ 17%).
## 2026-10-17 13:44 UTC: SIZE, Qwen3-1.7B on X6 (results/x3/analysis_x6_q17.log): mip 0.1%, mipf 44.5% @ 0.47k, think 1.2% @ 7.7k, thinkf 38.2% @ 7.1k: at 1.7B thinking hurts even with the fact (thinkf < mipf), and fact-first-then-think 50.1% @ 2.65k beats every single arm; thinkf → mipf 56.2% (two views). vLLM's V2 model runner (to keep presence penalties on the GPU) does not start for Qwen3.6 ("Model Runner V2 has not yet supported mamba_cache_mode='align'"; without prefix caching the engine died during start-up): the paused Qwen3.6 card-sampling runs stay paused (they would take 7–18 h with the V1 runner). GPU2 instead runs SIZE-CC (pre-registered in PREREG_SIZE.md): gpt-oss-20b, which fits a 3090, at medium and high effort with a 62k cap on the 311 Codeforces geometry problems — its earlier medium runs were cut at 16k on 85–93 of 311 problems. run_cc.py now writes rows as they finish and resumes.
## 2026-10-17 14:36 UTC: SIZE done (PREREG_SIZE.md part 3): with the fact first and thinking only on a failed check, models that fit one RTX 3090 match or beat Qwen3-32B: Qwen3-14B-AWQ X6 thinkf 76.0% (32B: 72.0%) and 87–92% on the optimization suite (32B: 79–85%); gpt-oss-20b X6 74.9% at 5% of the 32B compute, and as the first stage of a cascade to the 32B model 73.2% at 8%. Below 14B the optimization suite stays ≤ 47% whatever the fix; geometry is solved from 4B up. P2, P5, P6 hold; P3 half (4B fact-first −17.8 vs always-thinkf on X6); P4 refuted for 4B → 32B (52.6%), holds for 14B-AWQ / gpt-oss-20b → 32B. Started X1-SIZE (competition math for Qwen3-4B / 8B / 14B-AWQ) on GPUs 0 / 3; SIZE-CC (gpt-oss-20b contest geometry, 62k) running on GPU2.

## 2026-10-17 15:17 UTC: reframe (writing session; user: the main frame is solving computational math efficiently and effectively): PROPOSAL.md / PROPOSAL_ko.md rewritten around a 5-step recipe (write a program; add the missing fact; run a free check; think only when the check fails; reuse a checked program) with U1/U2 (fact first, then think on failure: 87.2% @ 2.5k vs difficulty 73.9% @ 4.1k) and SIZE (fact gain +44 → +1 from 1.7B to 32B; 24 GB-GPU models match Qwen3-32B) as the headline; new figs 18–20 (poc/make_figures_frame.py); PROPOSAL_slides.pptx rebuilt (11 slides, poc/make_slides.js); README intro reframed. Backups: docs/archive/PROPOSAL*_before_reframe_2026-10-17.md. Keep the frame; update numbers in place.
## 2026-10-17 15:33 UTC: SIZE-CHK (offline, pre-registered): requiring two cheap fact programs to agree (RESAMPLE) before skipping thinking repairs most of fact-first's leak: Qwen3-8B 72.4% @ 5.1k (= always-thinkf 72.2% @ 7.2k), Qwen3-14B-AWQ 75.6% @ 2.9k (76.0% @ 5.6k), gpt-oss-20b 74.9% @ 1.9k, Qwen3-32B 74.8% @ 2.6k (> always-thinkf 72.0%); Qwen3-4B only 57.8% (its fact programs are wrong consistently). A no-fact program as the second view leaks a bit less but escalates far more for ≤ 8B. X1-Q36R 1,669 / 1,680 (rows are graded at the end of the run).
## 2026-10-17 17:05 UTC: baselines restored in the reframed proposal (writing session; user: why no related baseline results?): PROPOSAL.md / PROPOSAL_ko.md section 7 is now a table of published methods measured here vs the recipe on the same problems, accuracy @ tokens (Snell-style difficulty allocation 74% @ 4.1k vs 87% @ 2.5k; always-high 66.2% @ 30.1k vs 66.3% @ 24.7k; CodeT 96.0% vs symmetry check 99.7%; DRoC 72% @ 2.1k vs exact snippet 77% @ 1.7k; S2A 64% / scope sentence 76% vs needed tools only 92%; Dynamic Cheatsheet 31–40% vs reuse 94%; Mixture-of-Thought cascade on MATH-500); slide 11 'Compared with published methods' added (12 slides).
## 2026-10-17 17:36 UTC: X1-Q36R (PREREG_X1.md): with the model card's sampling and an 80k cap, Qwen3.6 thinking reaches 99.6% on MATH-500 and 94.4% on AIME (old setting: 91.7 / 47.8%, 213 runs cut at 28k; now 4 of 1,680), mean 30k tokens on AIME; text without thinking 98.3 / 68.3%. Most of the gain is the budget (counting runs past 28k as failed: 95.3 / 51.1%), the sampling adds ≈ 3 points. The text == program gate keeps 99.3% on MATH-500 at 44% of thinking's tokens. 'Thinking hurts Qwen3.6' was a setup failure. Started U1-Q36D on GPU1: Qwen3.6's U1 thinking arm with an 80k cap and T 1.0 / top_k 20 but no presence penalty (vLLM applies it on the CPU; pre-registered addendum).
## 2026-10-17 17:55 UTC: results at a glance (writing session; user: show the results compactly, easily, intuitively): fig21_results_glance.png (six small bar panels, recipe step vs the usual way or a published method, accuracy · tokens; poc/make_figures_frame.py) at the top of README and in PROPOSAL / PROPOSAL_ko section 2; slide 5 draws the same six panels natively (13 slides).
## 2026-10-17 18:05 UTC: slides reordered (writing session; user: method slide after the problem / findings): Problem (title, polygon, words) → Findings (at a glance; Finding 1 fact, 2 small models, 3 two versions, 4 think on failure, 5 reuse) → Method (recipe built from the findings, all together, published methods) → Next. 13 slides, poc/make_slides.js.
## 2026-10-17 18:08 UTC: self-consistency baselines (offline, majority of the 3 seeds per item): X6 word problems — majority of 3 fact programs (mipf) 68.4% @ 1.1k (Qwen3-32B), 69.9% (14B-AWQ), 72.8% (gpt-oss-20b), 64.3% (8B), 49.3% (4B), below our check-gated fact-first at similar tokens (Qwen3-32B 72.4% @ 1.3k; with the two-program check 74.8% @ 2.6k); majority of 3 thinking runs (thinkf) is the most accurate at 3–7× the tokens (79.4% @ 16.4k for Qwen3-32B, 80.0% @ 16.7k for 14B-AWQ, 77.1% @ 6.9k for gpt-oss-20b). Competition math — majority of 3 text answers: Qwen3-32B 89.2% @ 2.3k on MATH-500 (text == program gate: 97.2% @ 3.4k), 23.3% on AIME; gpt-oss-20b 92.4% @ 1.9k (gate 95.7% @ 1.9k); Qwen3.6 99.0% @ 3.8k (gate 99.3% @ 4.0k), AIME 76.7% @ 13.8k (thinking 94.4% @ 30k). A second *view* (program) beats a second *sample* (self-consistency) at equal cost; more samples of thinking buy the last points at many times the tokens.
## 2026-10-17 18:12 UTC: user: extend to proofs and other math, incl. geometry / optimization. PREREG_PROOF.md: phase 1 (queued; waits for downloads + a free GPU) = formal proofs in Lean 4 on miniF2F (244), compiler as the exact check: specialized provers that fit a 3090 (Goedel-Prover-V2-8B, DeepSeek-Prover-V2-7B, downloading to /SSD/huggingface) vs general models, 8 attempts, compile-gated loop; phase 2 premises retrieved first; phase 3 geometry proofs (LeanEuclid or AlphaGeometry IMO-AG-30 with its symbolic engine as the tool); phase 4 optimization proofs (competition inequalities in Lean; LP optimality certificates checked exactly). run_lean.py gen now writes rows as they finish, resumes, and takes --think; poc/analyze_proof.py written before the runs.
## 2026-10-17 18:36 UTC: X1-SIZE part 1 (PREREG_X1.md): competition math for 3090-class models: Qwen3-14B-AWQ thinking 97.3% / 73.3% (MATH-500 / AIME) vs Qwen3-32B 97.4 / 77.2% at similar tokens; Qwen3-8B 97.0 / 68.3%; the text == program gate keeps all but 0.2–0.3 points at 78–79% of thinking's tokens; all four predictions hold for both models. Qwen3-4B, gpt-oss-20b contest geometry, Qwen3.6 re-runs (U1 112/624, X6 154/2,070) still running; the proof run waits for a free GPU.
## 2026-10-17 19:35 UTC: check-in: all four GPUs busy (X6d 488/2,070, U1-Q36D 342/624, SIZE-CC 1,392/1,866, X1-SIZE q4b 4,947/5,040; the proof run waits for a GPU). With the 80k cap the Qwen3.6 thinking runs now stop at the cap on 1% (U1 geometry 2/162, optimization 2/180, X6 1/488) instead of 60% / 19–26%; geometry thinking averages 33k tokens.
## 2026-10-17 20:36 UTC: X1-SIZE complete (Qwen3-4B: thinking 96.6 / 66.7%, gate 95.7% @ 81% of thinking's tokens). PROOF phase 1 restarted with the provers' own prompt and thinking (32k cap): the first Goedel-Prover-V2 run used our general prompt with thinking off, an off-spec setup that would have biased the comparison against it (564 attempts kept apart as gpv2ourprompt).
## 2026-10-17 21:36 UTC: U1-Q36D done (PREREG_U1.md): Qwen3.6's U1 thinking arm with an 80k cap solves 97% of geometry (was 38–41% at 28k) at ≈ 33k tokens per item; re-pooled headline over 3 models unchanged: fact-first-then-think 86.7–87.5% @ 2.5–2.7k > retrieved-first 83.5–84.3% > mechanism 82.2–83.7% > uniform 76.9–77.9% > difficulty 73.7–74.8%. Proof runs now parallel: Goedel-Prover-V2 continues on GPU3, DeepSeek-Prover-V2 started on GPU1, Qwen3-14B thinking waits for the next GPU.
## 2026-10-18 00:39 UTC: check-in: all GPUs busy (SIZE-CC 1,838/1,866: gpt-oss-20b medium with a 62k cap 52.4% on contest geometry (16k: 47%), its high-effort runs hit the 62k cap on half the problems so far; X6d 1,788/2,070; Goedel-Prover-V2 1,472 and DeepSeek-Prover-V2 1,271 of 1,952 proof attempts). Prep for PROOF phase 3 (geometry proofs, CPU only): AlphaGeometry's repository (IMO-AG-30, JGEX-AG-231 and its DD+AR symbolic engine) in /SSD/lean_postech/ag with a small venv; /SSD/lean_postech/ag/ddar_one.py runs the engine without a language model (baseline: which problems need no auxiliary construction).
## 2026-10-18 01:37 UTC: (1) SIZE-CC: gpt-oss-20b medium with a 62k cap: 52.4% of 311 contest geometry problems (3 seeds; 16k cap: 47.0%), 14 of 933 runs at the cap: P1 holds. High effort: the seed-2 file had a NUL-filled line (a torn write on the NAS) that made every resume crash, so 10 problems are missing; queued to finish on the next free GPU (queue_s2_sizecc_fix.sh), then the pre-registered analysis. All resumable harnesses (run_cc, run_math, run_nlopt, run_lean, run_geo_cross, run_co) now skip such torn lines instead of crashing. (2) Geometry proofs, phase-3 baseline: AlphaGeometry's symbolic engine alone (DD+AR, no language model, CPU) proves 12 of IMO-AG-30 (paper: 14); one problem (IMO 2022 P4) fails to parse in this engine version. (3) GPU2's stale claim from SIZE-CC removed: the Qwen3-14B thinking proof run started on GPU2.
## 2026-10-18 05:02 UTC: (1) Formal proofs (PREREG_PROOF.md): specialized provers that fit a 3090 prove the most miniF2F statements with 8 attempts — Goedel-Prover-V2-8B 180 / 244 (73.8%), DeepSeek-Prover-V2-7B 165 (67.6%) vs general Qwen3.6 133, gpt-oss-20b 66, Qwen3-32B 31 — and almost never invent lemma names (6–7% vs 22–40% of failed attempts), at 2–3 × the tokens. (2) X6 with Qwen3.6 fixed (80k): the fact turns thinking from −9 to +4.5 points; fact-first-then-think 78.2% @ 3.0k vs always-thinkf 79.1% @ 22.6k. (3) SIZE-CC: gpt-oss-20b on contest geometry, low → medium escalation 54.6% @ 11k vs gpt-oss-120b medium 56.8%; its high effort overruns 62k on half the problems. Started: Qwen3.6 thinking and gpt-oss-20b medium on the proofs (GPUs 0 / 1), Goedel 24 more attempts on its 64 unsolved statements (GPU3); Qwen3-14B thinking proofs still on GPU2.
## 2026-10-18 06:39 UTC: proofs: Qwen3-14B-AWQ with thinking proves only 21 / 244 (vs Goedel-Prover-V2-8B 180, Qwen3.6 no-think 133) at 9k tokens per attempt: thinking does not replace knowing Lean 4 (16k caps, Lean 3 syntax, invented names). Extractor fix (':=' and 'by' on separate lines; all finished proof files re-checked, only Qwen3-14B changed: +1 statement). Phase 3a started on GPU2: gpt-oss-20b proposes auxiliary points for the 18 IMO-AG-30 problems AlphaGeometry's engine cannot prove alone; the engine checks each proposal (pre-registered).
## 2026-10-18 07:36 UTC: geometry proofs: gpt-oss-20b proposed 288 auxiliary points (18 problems × 16); 122 stopped at the 16k cap without a clause; DD+AR is checking the rest (CPU, ≤ 600 s each). Second proposer started on GPU2: Qwen3.6 with thinking (30k cap). The engine scripts are now in the repo (poc/geoproof_ddar_one.py, poc/geoproof_ddar_aux.py; they run in a small venv with numpy / scipy, see /SSD/lean_postech/ag).
## 2026-10-18 08:36 UTC: geometry proofs, first result: gpt-oss-20b's one-point proposals prove 0 of the 18 IMO-AG-30 problems AlphaGeometry's engine cannot do alone (288 proposals: 42% cut at 16k, 22% rejected by the engine, 104 valid, none completes a proof). Qwen3.6 with thinking proves 129 of 244 Lean statements (133 without): thinking does not help general models on Lean. Started phase 3b: the same with a 30k budget, with and without the construction definitions as the fact.
## 2026-10-18 09:36 UTC: Lean: gpt-oss-20b at medium effort proves 72 of 244 (low: 66) at 9 × the tokens. Geometry: Qwen3.6 with thinking proposes the point that proves IMO 2014 P4 (d = midpoint of b c) — 1 of the 18 problems the engine cannot do alone — but 151 of its 288 proposals stop at the 30k cap; re-run with 80k on GPU2 (pre-registered). DeepSeek-Prover-V2 gets 24 more attempts on its 79 unsolved statements (GPU1). Phase 3b (gpt-oss-20b with / without the construction definitions) is being checked.
## 2026-10-18 10:36 UTC: the Qwen3.6 geometry proposer's server died at 10:11 (NCCL watchdog during a host-load spike, 15-min load 552) after 22 of 288 proposals; relaunched with retries (resumes). Started PROOF phase 2 on GPU0 (pre-registered): Qwen3.6 sees a Lean-verified proof of the most similar other statement before writing — the 'fact first' step for proofs.
## 2026-10-18 11:32 UTC: proofs, phase 2: a verified similar proof in the prompt does not help Qwen3.6 (133 / 244 with and without; first attempt 77 vs 94; invented names 23%) — refutes PROOF-P8. Geometry, phase 3b: with a 30k budget gpt-oss-20b's proposals prove 1 of 18 (IMO 2014 P4), with or without the construction definitions (16k: 0). gpt-oss-20b + worked example started on GPU0 (first launch used the wrong model through a copied script; stopped within a minute, no rows).
## 2026-10-18 12:19 UTC: proofs phase 2: a verified similar proof also does not help gpt-oss-20b (65 vs 66 of 244).
## 2026-10-18 12:36 UTC: proof cascade (offline): a cheap general model before the prover keeps 180 / 244 but saves no compute (98–105%): prover cost is spent on statements nobody proves, so routing easy statements to a cheap model does not pay; the attempt budget does. Started on GPU0: Goedel-Prover-V2 revising its failed first attempts from Lean's error lines vs a fresh attempt (pre-registered).
## 2026-10-18 13:36 UTC: optimization-type proofs (inequalities / bounds, 50 of the 244 Lean statements): the provers prove them as often as other statements (72% / 66%), general models much less (Qwen3.6 48%, gpt-oss-20b 10%). Started: DeepSeek-Prover-V2 repair from Lean errors (GPU2); AlphaGeometry's engine alone on JGEX-AG-231 (CPU) as a larger geometry baseline. Qwen3.6 80k geometry proposals done, being checked.
## 2026-10-18 14:36 UTC: (1) JGEX-AG-231 baseline: AlphaGeometry's engine alone (no language model) proves 187 of 231 (44 left for proposers). (2) Two harness failures fixed and re-run: the Goedel revision run stopped at 16 of 107 because long failed proofs + a 32k output request exceeded the 40k context (max_tokens now fitted to the prompt; failed requests are recorded, not fatal); the DD+AR check of the Qwen3.6 80k proposals crashed on an engine exception (numericals.InvalidLineIntersectError; now counted as 'not proved').
## 2026-10-18 15:36 UTC: proofs: repairing a failed Goedel proof from Lean's error lines proves half as many as simply sampling a fresh attempt (11 vs 22 of 107, same tokens; with our single-turn repair prompt). Geometry: Qwen3.6 with an 80k budget writes valid points (184 / 288) but still unlocks only IMO 2014 P4. Started: JGEX-AG-231 proposer test (44 problems the engine cannot do alone; GPU0) and the DeepSeek-Prover repair run again (GPU2).
## 2026-10-18 16:36 UTC: repair from compiler errors loses to a fresh attempt for DeepSeek-Prover-V2 too (5 vs 13 of 112). Started phase 4b (GPU2): a hand-written 10-line inequality toolkit before the 50 bound statements, Qwen3.6 (pre-registered: ≥ 29 of 50, baseline 24).
## 2026-10-18 17:36 UTC: phase 4b: an inequality fact sheet does not help Qwen3.6 on Lean bound proofs (21 vs 24 of 50). Geometry on easier problems: gpt-oss-20b's auxiliary points make 13 of the 44 JGEX problems provable (engine alone 187 / 231 → 200). Refocus (user asked whether the work is important): pre-registered MODEL (docs/prereg/PREREG_MODEL.md) — when does the recipe win, and can 10–30 labelled items pick the right policy for a new task / model; offline on 63 stored cells.
## 2026-10-18 17:39 UTC: refocus step 2 started — automatic facts (X6-AUTO, pre-registered in PREREG_X3.md): instead of the hand-written 6-line snippet, the prompt gets the solver library's own public names read by introspection (dir()); Qwen3-32B / Qwen3-8B / Qwen3.6, with and without thinking, on GPUs 0 / 3 / 2. The policy model (MODEL) is computing offline.
## 2026-10-18 17:40 UTC: MODEL (refocus step 1, offline, 63 cells): 'fact first, think on failure' is the best single default (regret 1.4 points vs each cell's best policy; always thinking 8.4, even with free tokens 5.8); 30 labelled problems of a new task choose the right variant with 0.6 points of regret (10: 2.0). The exact decomposition FF − THINK = P(pass) × [P(cheap right | pass) − P(think right | pass)] holds in every cell. PROPOSAL / PROPOSAL_ko: one paragraph added (§4).
## 2026-10-18 18:36 UTC: automatic facts, part 1: an introspected list of the solver library's names is worse than the hand-written 6-line snippet without thinking (Qwen3-32B 56.1 vs 66.2%; Qwen3-8B 44.3 vs 51.7%, though above no fact 34.3%): the list steers the model to names it cannot use (an enum passed to CreateSolver, low-level constraint calls). Names are not usage. Goedel-Prover-V2 with 32 attempts proves 187 / 244 (180 at 8); each extra proof costs 67 × the tokens of the first ones.
## 2026-10-18 19:36 UTC: automatic facts: the introspected name list also hurts Qwen3-8B with thinking (57.5% vs 67.7% without anything). Next automatic fact started (X6-VER, GPU3): show the model its own check-passing program for the most similar problem of the other benchmark (selected by the label-free check, not by answers).
## 2026-10-18 20:36 UTC: automatic facts: a list of the library's names fails (Qwen3-32B thinking still invents SetMaximize 241 times; fact-first 63.1% vs 72.4% with the snippet), but the model's OWN check-passing program for a similar problem of the other benchmark works as well as the hand-written snippet (Qwen3-8B: 51.0% vs 51.7%; no fact 34.3%), selected by the label-free check, no human and no answers. Running for Qwen3-32B (GPU0) and Qwen3.6 (GPU1); DeepSeek-Prover's 32-attempt tail done.
## 2026-10-18 21:36 UTC: automatic facts: the mined similar-problem example matches the hand-written snippet without thinking for Qwen3-32B too (66.0 vs 66.2%), but in the fact-first pipeline it loses for Qwen3-8B (60.0 vs 68.3%): it makes more wrong programs run (pass-but-wrong 35% vs 30%) because the model copies the other problem's formulation. Started X6-VER2: the shortest check-passing program as the fact (usage without a formulation to copy).
## 2026-10-18 22:35 UTC: automatic facts: the shortest check-passing program as the fact matches the hand-written snippet without thinking (Qwen3-8B 52.1 vs 51.7%) with the fewest crashes, but more of the programs that now run are wrong (38% vs 30%): fixing the API removes the crash that used to flag a wrong formulation, so the 'runs and prints' check leaks more.
## 2026-10-18 23:36 UTC: automatic facts in the full pipeline: for Qwen3-32B the model's own check-passing program for a similar problem (mined from the other benchmark, no human, no answers) replaces the hand-written snippet — fact-first with the agreement check 75.8% @ 3.0k vs 75.2% @ 3.0k hand-written — and repairs its thinking (52.0 → 71.4%); for Qwen3-8B it is 6 points short. Extending to Qwen3-14B-AWQ and the shortest-program fact on GPUs 0 / 3.
## 2026-10-19 00:36 UTC: the introspected name list also breaks Qwen3.6's thinking (47.2% vs 59.6% with no fact; 294 wrong-argument errors in low-level calls it exposes). Started automatic facts for gpt-oss-20b (GPU2).
## 2026-10-19 01:37 UTC: automatic facts on the word problems, 4 models: a fact mined from the model's own check-passing programs replaces the hand-written snippet for Qwen3-32B and gpt-oss-20b (≤ 1 point), not for Qwen3-8B and Qwen3.6 (5–6 points short). Started U1-MINED (pre-registered): the headline optimization suite with a mined fact (the model's shortest feasible program for the most similar other problem type) instead of the hand-written snippet.
## 2026-10-19 02:36 UTC: automatic facts, two verdicts. (1) Within one problem family it works: on the word problems (all LP / MIP in one library) the model's own shortest check-passing program from the other benchmark matches the hand-written snippet for Qwen3-32B, Qwen3-14B-AWQ and gpt-oss-20b (≤ 1 point). (2) Across problem types it fails: on the headline optimization suite, a mined program of the most similar other problem type is 14–21 points below the hand-written fact (and below retrieval) — it transfers the other type's library and solver backend (the 8B model's knapsack programs copy bin packing's continuous LP solver). The fact must match the task's tool.
## 2026-10-19 03:36 UTC: held-out benchmark (MAMO, 863 problems, never used before): with no hand-written component gpt-oss-20b gets 78.8% (two agreeing programs with its own mined example, thinking only otherwise) vs 78.9% with the hand-written snippet, and 77.3% @ 0.6k tokens with plain fact-first vs 76.0% @ 2.7k for always thinking; 30 labelled problems pick the policy with 1.3 points of regret. All three pre-registered predictions hold for this model. Qwen3.6 added on GPU2.
## 2026-10-19 05:36 UTC: held-out MAMO, with no hand-written component: Qwen3-14B-AWQ 71.7% vs 71.4% hand-written (two agreeing programs, else think), Qwen3-8B 71.0% vs 72.0%; plain fact-first beats always-thinking at 12–13% of its tokens for both; 30 labelled problems pick the policy with ≤ 1.4 points of regret. Replication seeds started for Qwen3-14B-AWQ and gpt-oss-20b (rule: ≥ 3 seeds).
## 2026-10-19 06:36 UTC: held-out MAMO replication: for gpt-oss-20b the automatic recipe is within 1.2 points of the hand-written one on all 3 seeds (−0.1 / −0.8 / −1.2).
## 2026-10-19 07:27 UTC: writing session (user: update ppt and md files with recent progress and points): PROPOSAL / PROPOSAL_ko updated in place (proofs row in §1; automatic fact in the recipe; §4 held-out MAMO with no human + small-GPU competition math / contest geometry; §5 proofs need a specialized model, automatic facts only within a problem family; §6 models / benchmarks; §7 Lean repair row; §8 plan); new fig22_new_results.png (automatic facts on MAMO, policy from 30 labels, Lean provers); slides: Finding 6 (fact without a human), Finding 7 (proofs), policy panel on 'All together', new limits / next (15 slides); README and docs/README updated. Backups: docs/archive/PROPOSAL*_before_update_2026-10-19.md.
## 2026-10-19 07:28 UTC: related-work search (docs/notes/RELATED_WORK.md): closest to our mined facts is OptiSkill (2609.22987: a skill bank from a strong teacher's programs validated against ground-truth answers, routed by problem type) — ours is label-free, uses the same small model's own programs, and shows why type routing is needed. On MAMO our training-free recipe puts 3090-class models at the fine-tuned ORLM-8B level (Qwen3-8B 81.7 / 37.9% vs reported 82.3 / 37.4%), below trained reasoning models (STORM-Qwen3-4B 86.3 / 70.3%) and frontier agents. A same-harness ORLM-8B run is queued (download in progress; COPT works here).
## 2026-10-19 07:37 UTC: md files reorganized (writing session; user: methods explanations should come later): PROPOSAL / PROPOSAL_ko = 1 problem → 2 findings at a glance (figs 21, 22) → 3 findings 1–7 (fact, small models, two versions, think on failure, reuse, automatic fact, proofs) → 4 our method (the recipe, citing the findings) → 5 does the whole recipe pay off (U1 table, policy choice, small GPUs) → 6 published methods + related work (OptiSkill, ORLM/STORM/EVOM, Thinkless/AdaptThink added) → 7 limits → 8 setup → 9 plan; README intro the same order; fig21 legend 'blue = the better way'. Same order as the slides. Backups: docs/archive/PROPOSAL*_before_reorder_2026-10-19.md.
## 2026-10-19 07:44 UTC: proposal explained with examples (writing session; user: explain with examples and visualizations, not only results): every finding in PROPOSAL / PROPOSAL_ko now has a real example (F2 Qwen3-1.7B writes Solver.SUCCESS / solver.INFINITY; F3 Qwen3-14B hull 6 vs 0 + Find Color passing 3 examples, failing test 11; F6 Qwen3-8B MAMO easy-189: Objective().Minimize() crash → own vans-and-trucks program as the fact → solver.Minimize(...) twice, 20000, 0.6k tokens vs 5.3k thinking; F7 miniF2F mathd_numbertheory_34: Qwen3-32B cites Nat.ModEq_iff_modEq, Goedel interval_cases) and an example picture (figs/ex_finding1-7.png, exported from the slides by poc/export_slide_figs.py; replaces the CVRP table, fig14 and fig12 there); a worked 'one problem through the recipe' in §4 and how the 30-label policy choice works in §5; slides 10–11 now show these examples.
## 2026-10-19 07:50 UTC: 5-minute talk deck (writing session; user: reorganize and update the ppt for a 5-minute presentation): PROPOSAL_slides.pptx is now the talk (7 slides, about 45 s each, timing in the speaker notes): title; the problem (polygon); what we found (4 findings, each a real example + number); our method (recipe); it pays off (U1 bars + automatic fact 79% = 79% on MAMO, 24 GB GPU, 30 labels); published methods (5-row table); where it stops and next. The 15-slide deck with every finding moved to PROPOSAL_slides_full.pptx; both built by poc/make_slides.js; poc/export_slide_figs.py now reads the full deck.
## 2026-10-19 08:04 UTC: talk deck reorganized (writing session; user: findings in more detail, other things in extra pages; 5-minute talk + 5-minute Q&A): PROPOSAL_slides.pptx = title, problem, Finding 1 fact (prompt A/B + bars), Finding 2 two versions (hull 6 vs 0 + bars), Finding 3 think on a failed check (Make a triangle / Arrow + bars), Finding 4 fact without a human (MAMO example + chart), our method (recipe, 87% @ 2.5k vs 74% @ 4.1k), 'Thank you: questions?' with the takeaway and an index of 9 extra pages (pays off, all policies, small models, reuse, proofs, published methods, limits, all findings, words). Every full-deck slide is now a function in poc/make_slides.js, shared by both decks.
## 2026-10-19 08:33 UTC: method explained in more detail (writing session; user): new slide 'How the recipe runs on one problem' in both decks (Qwen3-8B, MAMO easy-189: 0 mine the fact once, 1-2 program + fact 316 tokens, 3 second version agrees +312, 4 no thinking needed (thinking alone 5.3k), 5 reuse; plus the free check for each kind of problem); talk = 9 slides + 9 extra pages (index numbers computed in poc/make_slides.js); the same check table added to PROPOSAL / PROPOSAL_ko §4.
## 2026-10-19 08:39 UTC: same-harness specialist baseline: ORLM-LLaMA-3-8B (fine-tuned) gets 69.5% on MAMO (Easy / Complex 80.5 / 35.5%, as reported) at 1.1k tokens; our training-free recipe matches it with Qwen3-8B (69.5% @ 1.0k plain fact-first; 71.0% with the agreement check) and beats it with gpt-oss-20b (78.8%, +9.3). STORM-Qwen3-4B (SFT + RL, the strongest public small specialist) queued with its official inference code on GPU0.
## 2026-10-19 08:59 UTC: method made visual (writing session; user: compact, easy, intuitive, with examples and visualization): the talk's two method slides became one, 'Our method: cheap steps first' (five steps on the real MAMO problem, each with what it produced and its tokens; bars: this problem 0.6k vs 5.3k tokens, all 624 problems 87% @ 2.5k vs 74% @ 4.1k; the free check per problem type as chips); talk = 8 slides + 9 extra pages; the full deck has it after the recipe; exported as figs/ex_method.png, which replaces the text walk-through and table in PROPOSAL / PROPOSAL_ko §4.
## 2026-10-19 10:45 UTC: held-out MAMO replication: for Qwen3-14B-AWQ the automatic recipe is within 1.6 points of the hand-written one on all 3 seeds (+0.3 / +1.6 / +0.2; gpt-oss-20b −0.1 / −0.8 / −1.2), so 'no hand-written component within a problem family' now holds on 3 seeds for two 3090-class models. Started ADAPT (pre-registered in docs/prereg/PREREG_X1.md, GPU1): the closest related method for 'when to think' is AdaptThink (RL-trained switch that skips thinking on easy problems); we run it and its base model DeepSeek-R1-Distill-Qwen-7B on MATH-500 + AIME (3 seeds, the paper's settings) and compare the trained switch with our free check on the same backbone, and the two combined. STORM's 6 h time limit removed (its code writes results only at the end; the first pass alone took ~3.5 h).
## 2026-10-19 11:20 UTC: related research and comparison expanded (writing session; user): PROPOSAL / PROPOSAL_ko §6 = 6.1 where this work sits (8 themes: closest work, what they do, what we add), 6.2 same-harness comparison (+ ORLM-8B on held-out MAMO 69.5% @ 1.1k vs Qwen3-8B with the recipe 69.5% @ 1.0k, gpt-oss-20b 78.8%), 6.3 numbers reported in papers (ORLM / STORM / OptiSkill on MAMO, Goedel-Prover-V2 84.6% card vs 76.6% ours, AlphaGeometry 25/30 and DD+AR 14 vs our 12 / 13) + what is new; slides: ORLM row on 'compared with published methods', new 'where this work sits' and 'numbers reported in papers' (full deck after the baselines; talk extra pages 15–16, index updated). Backups: docs/archive/PROPOSAL*_before_related_2026-10-19.md.
## 2026-10-19 11:47 UTC: how much would a better check buy? (exploratory, offline, word problems): little for 14B+ models. Our check for word problems (two programs run and agree, else think) lets through 12–16% of problems as agreeing-but-wrong, yet a perfect check (send exactly those to thinking) would add only +0.8 to +2.6 points for Qwen3-32B, gpt-oss-20b and Qwen3-14B-AWQ (NL4OPT + IndustryOR and MAMO, every available seed), because thinking solves only 7–16% of them; for Qwen3-8B +5.6 (thinking solves 30%). Part of the 'leak' is wrong labels: on 7 of Qwen3-32B's 41 leaked NL4OPT/IndustryOR problems (seed 1) two programs, a CP-SAT program, a text answer and thinking all give the same answer, and 3 of the 4 we read are mislabelled (nl4opt-36 gold 'No Best Solution', true 1215; nl4opt-174 gold 7500, true 5625; nl4opt-197 gold −99999). A different second view (a text answer instead of a second program) halves the leak (17% → 10% of agreeing pairs) but sends more problems to thinking: +0.4 / 0.0 points at 2.2 / 1.8× the tokens (Qwen3-32B / gpt-oss-20b, 3 seeds). Reading: for strong models the leak is mostly problems nobody here solves; the next point comes from a better solver for those, not a better check. ADAPT (GPU1) partial: R1-Distill-Qwen-7B without thinking 80.5% on MATH-500 (paper 80.6%).
## 2026-10-19 11:52 UTC: ADAPT raw check: R1-Distill-Qwen-7B's program replies without code are real, not a harness bug. Re-asked on two such MATH-500 problems, the model either answers in text with \boxed{15} and no program (prealgebra/1761) or, on a fresh sample, writes the sympy program (algebra/1098). Without thinking it ignores the 'write a program' instruction on about a third of problems (516 of 1,500 MATH-500 replies); the gate treats those as a failed check and sends them to thinking, as it would for a crashing program.
## 2026-10-19 11:58 UTC: problem framing made explicit (writing session; user: the first slide does not show what we do, what matters, what the problems are): title subtitle 'A fact, a check, or more thinking: where should the extra effort go?'; new slide 3 'What goes wrong, and what we do' in both decks (programs fail silently: Qwen3-14B hull outputs 0 instead of 6, 24–37% of wrong contest programs pass the examples; thinking is expensive: 57% @ 6.8k vs 66% @ 30k, 4.4× tokens for 9 points; why it matters; our question and plan); talk = 9 slides + 11 extra pages; PROPOSAL / PROPOSAL_ko §1 gain 'why it matters' and 'what we do'.
## 2026-10-19 12:00 UTC: slide 3 'What goes wrong, and what we do' redrawn compactly (writing session; user): two panels with a picture each (program A 6 ✓ vs program B 0 ✗ with no error, '24–37% of wrong programs pass the examples'; medium vs high effort token bars, '4.4× tokens for only 9 more points'), three 'why it matters' chips, and the question with three option pills (a missing fact / a free check / more thinking).
## 2026-10-19 12:04 UTC: slide 3 with pictures and examples instead of numbers only (writing session; user): the hull picture and a terminal showing the two real runs (task only → 6; + 8 helpers → 0, no error), the Find Color example (passes all 3 examples, fails hidden test 11), the token cost drawn as pages (medium ≈ 10 pages, 57%; high ≈ 43 pages, 66%), icon chips for why it matters, and icon pills for the three options. Icons: figs/icons/*.png from poc/make_icons.js (react-icons).
## 2026-10-19 12:37 UTC: held-out MAMO replication, Qwen3-8B (3 seeds): with no hand-written component the recipe is within −0.9 / +1.6 / +2.2 points of the hand-written one (71.0 / 72.2 / 73.1% vs 72.0 / 70.6 / 70.9%) and a third cheaper (3.1–3.2k vs 4.5–4.6k tokens), because the hand snippet still leaves the `solver.Objective().Minimize()` crash (91 crashes in seeds 2–3 vs 39 with the model's own mined program) and every crash buys a thinking run. All three 3090-class models now hold on 3 seeds. Started: Qwen3-32B-AWQ seeds 2–3 on GPU3 (pre-registered in PREREG_X7.md).
## 2026-10-19 12:38 UTC: what the problems are and how hard (writing session; user: show how LLMs solve the math problems, what the problems are, how hard vs LeetCode): slide 2 'How an LLM solves a math problem' (four ways with icons: words, program, solver library, think longer; then the polygon example); new slide 3 'The problems we study, and how hard they are' (five kinds with an example and a LeetCode tag each; histogram of the 311 contest problems by Codeforces rating over LeetCode Easy / Medium / Hard / harder zones: median 2200, 46% at 2400+, where gpt-oss-120b high solves 48%); talk = 10 slides + 11 extra pages. PROPOSAL / PROPOSAL_ko §1: a LeetCode column, the four ways, and figs/ex_problems.png. poc/export_slide_figs.py now finds slides by title.
## 2026-10-19 12:47 UTC: talk rebuilt after review (writing session; user: update the ppt; 5-minute talk + 5-minute Q&A): 8 slides, script ≈ 650 spoken words (was ≈ 1,135), no text under 14 pt (was 87 runs): 1 title; 2 'Programs help, but two things go wrong' (four ways; words vs program; silent failure; pages of thinking; the question); 3 what we solve and how hard (5 kinds with LeetCode tags); 4 Finding 1 fact vs manual; 5 Finding 2 think only when a free check fails (examples check + two-versions check); 6 method on one problem + results (87% vs 74%, 79% = 79%, 0.6k vs 5.3k); 7 what is new vs prior work + plan + takeaway; 8 questions with a 16-page index. New extra page 'Setup and fairness' (also in the full deck).
## 2026-10-19 12:49 UTC: talk slide 7 made visual (writing session; user: compact, intuitive, examples and visualization, not only results): 'What is new, and what is next' = three rows 'the usual way → ours' with icons and arrows (think on hard problems / train a switch → think only when a free check fails; manual or teacher programs checked against answers → the model's own checked program; fine-tuned specialist → no training, one 24 GB GPU, same 69.5%), a three-step timeline with icons, and the takeaway.
## 2026-10-19 12:51 UTC: exploratory, offline (writing session; user asked for other difficulty baselines; not pre-registered): on the 311 contest geometry problems (gpt-oss-120b, 3 seeds of stored medium / high runs) even an ORACLE difficulty router that knows each problem's true Codeforces rating and sends rating ≥ T to high effort is dominated by the free examples check: examples gate 65.0% @ 20.2k vs rating gate 61.4% @ 19.4k (T 2600), 63.3% @ 22.7k (T 2400), 65.3% @ 27.8k (T 1800); using the medium answer's length as the difficulty signal is worse still (62.1% @ 23.0k, 65.4% @ 33.9k). poc/analyze_difficulty_gate.py → results/difficulty_gate.log. Worth pre-registering as a proper baseline (with the brute-force cross-check arm).
## 2026-10-19 13:01 UTC: difficulty yardsticks better known than LeetCode (writing session; user): slides and PROPOSAL / PROPOSAL_ko §1 now use human contest ranks (Codeforces: median 2200 = Master, 46% at Grandmaster level 2400+; 18% of problems solved by none of 9 model settings), exams (AIME invites at least the top 2.5% of AMC 10 / 5% of AMC 12 takers), IMO-AG-30 human reference (average gold medallist 25.9 / 30, average participant 15.2; AlphaGeometry paper, checked via secondary sources), the routing greedy baseline (+47.6% vs best known) and NL4OPT (NeurIPS 2022 competition). The extra-page histogram now shows Codeforces rank bands instead of LeetCode bands.
## 2026-10-19 13:06 UTC: talk opening split for beginners (writing session; user: too much information on one slide): slide 2 'Let the computer do the math' (only the shape copies and words vs program); slide 3 'But two things go wrong' (two large panels: program A → 6 vs program B → 0 with no error; normal vs think-hard drawn as pages, 4.4× for 9 points) and the question with three options; statistics moved to the notes; talk = 9 slides + 16 extras.
## 2026-10-19 13:21 UTC: talk flow fixes after review (writing session; user: apply the slide fixes, ignore notes): order is now title → what we solve and how hard → let the computer do the math → but two things go wrong (question: a missing fact, a free check, or more thinking?) → Finding 1 → Finding 2 → method → what is new → questions. Findings 1, 2 and the method carry the matching answer badge(s) from the question slide; Finding 2 uses the same names as slide 4 (program A, task only → 6; program B, + helper code → 0); the method slide says what the automatic fact is (the model's own earlier checked program); plain labels on the problem-kinds slide ('a simple plan drives 48% farther', 'university operations-research exercises', 'AIME: top ~5% of high-school contestants'); 'the same 69.5% on MAMO'. Still 9 slides + 16 extras; the full deck is unchanged.
## 2026-10-19 13:27 UTC: talk review, second pass (writing session; user: review flow and slides for a 5-minute talk + 5-minute Q&A, change the ppt, remove the slide notes): the talk deck has no speaker notes now (the full deck keeps them). Slide 2's caption says how we score (open models on our GPUs; exact answers and tokens spent) instead of repeating the contest rank; slide 3 says what 436 is (twice the area); slide 4 has taller panels with the question and the source of each panel (Qwen3-14B; 311 contest problems, gpt-oss-120b; 1 page ≈ 700 tokens) and the question bar where the takeaway usually is; Finding 2 and the method slide show accuracy and cost the same way (number = % solved, bar = tokens per problem; before, the bar was tokens on one slide and accuracy on the next); 'Next' on slide 8 and on the extra page now follows the latest result (a perfect check adds only 1–3 points on word problems, so the next target is programs that run but model the problem wrong).
## 2026-10-19 13:36 UTC: talk review, third pass (writing session; user: keep reviewing the flow and slides, 5-minute talk + 5-minute Q&A): every choice in the question now has a visible cause on slide 4 (panel 1 'Programs fail, often silently' adds 'or it crashes on a library function that does not exist', which Finding 1 answers with the fact; the silent 6 vs 0 is what the free check catches; the 4.4× pages is the cost of thinking). The three choice pills (a missing fact, a free check, more thinking) now open the talk on the title slide and are drawn by one helper on slides 1, 4 and the answer badges. Plainer words: 'no answer key needed' (Finding 2, slide 8), 'think only if the two differ', 'same kind, new data: no new tokens', 'think on hardest-looking'; the extra page drops the 'DC' abbreviation.
## 2026-10-19 13:41 UTC: three finished runs. (1) STORM-Qwen3-4B (trained specialist, its official tool-integrated reasoning) on all of MAMO under our grader: 81.8% at 8.4k tokens per answer — above our best 3090-class recipe (gpt-oss-20b 78.8% @ 1.9k) by 3.0 points at 4.4× the tokens (prediction held). Sending only the problems where our two cheap programs disagree to STORM gives 80.4% @ 3.0k (gpt-oss-20b), below STORM alone because agreeing-but-wrong programs are kept; STORM's first sample is right on 28–49% of those leaked problems. Reading 12 of them: most are reading choices on ambiguous text ('difference cannot exceed' as |A−B|; the sign of a loss bound), over-strict models that come out infeasible (an equality where the surplus may stay), a flipped objective, units, int() truncation; one label is wrong (complex-68: brute force 175 = ours, label 158, STORM also 158) and one problem lacks its bounds. MAMO has no infeasible label, so 'infeasible' should count as a failed check: +0.1 to +1.6 points at +0.1–0.4k tokens. Pre-registered and started (GPU1): our recipe on top of STORM (its no-thinking program + agreement check, its full reasoning only on disagreement). (2) AdaptThink side baseline (competition math, out of the CG + CO scope): a trained when-to-think switch gives 91.7% @ 1.9k vs our label-free gate on the same base model 93.0% @ 3.9k; our check on its skipped answers adds +2.2 (93.9% @ 3.4k). (3) Qwen3.6 on MAMO (1 seed): automatic fact 75.0% vs hand-written 73.6%; thinking hurts it here (71% at 9× the tokens).
## 2026-10-19 13:47 UTC: expected questions and a Korean script (writing session; user: suggest expected questions and prepare the slides; main-slide script in Korean as speaker notes): the questions slide (9) is now a list of 12 expected questions, each with the extra page(s) that answer it. Five new extra pages whose titles are the questions: 'what if a wrong program passes the check?' (24–37% of wrong contest programs pass the examples; 12–16% of word problems agree-but-wrong; a perfect check would add only +0.8 to +2.6 points, +5.6 for Qwen3-8B; some labels are wrong), 'why can thinking make it worse?' (Qwen3-32B word problems 65.4 → 52.0% with thinking, invented Objective().SetMaximize; fact + thinking 72.0% @ 5.5k, fact first 72.4% @ 1.3k), 'is think-on-the-hardest a weak baseline?' (exploratory oracle Codeforces-rating router vs the free examples check, from the 12:51 entry; 74 → 87% on 624), 'why not majority voting?' (pick 1 of 3: vote 4.3% wrong vs symmetry check 0.3%; word problems vote of 3 programs 68.4% @ 1.1k, 3 thinking runs 79.4% @ 16.4k, fact first 72.4% @ 1.3k; MATH-500 vote 89.2% vs text = program 97.2%), 'is the comparison fair?' (input tokens from CRITIQUE §4 update, contamination proxy from CRITIQUE §6, p = 0.62 from §5). Extra pages reordered by question (21 in all, 30 slides). Speaker notes: a Korean script on slides 1–9 only (≈ 4 minutes, seconds per slide in brackets); the extra pages keep no notes. README updated (21 extras; the full deck has 21 slides, not 15).
## 2026-10-19 13:54 UTC: what the remaining MAMO errors are, and two fixes tested. (1) About half of each model's 'leaked' problems (two cheap programs agree on a wrong answer) are disputed labels: on 66 problems (7.6%) our five models' programs agree against the label and STORM, trained separately, agrees with them on 60; the 3 we read are wrong or ill-posed labels (easy-71: the text gives 3000, label 1340). Without those 66, STORM scores 87.7% and gpt-oss-20b's cheap program 80.1%. (2) The next class is over-strict models that come out infeasible, concentrated in two recurring problem types: TSPs where the Miller-Tucker-Zemlin order constraints include the start city (gpt-oss-20b: 0% on MAMO's 34 TSPs, 29 infeasible; Qwen3 models 49–62%) and supply redistributions written as equalities (16 problems, 0–38% for every model). (3) A generic repair turn ('infeasible, but the problem has a solution: find the over-strict constraint') rarely helps: 8–14% (gpt-oss-20b) and 24–33% (Qwen3-14B-AWQ) of infeasible programs become right, most stay infeasible with the same formulation; +0.0 to +0.7 points on MAMO and up to −1.8 on NL4OPT + IndustryOR (which has true infeasible labels). (4) Our recipe cannot sit on top of STORM: its no-thinking mode is broken (55% of programs hit 8k tokens; stopped after 93 rows). Started (pre-registered, PREREG_X7.md FORM): is a systematic formulation error missing knowledge that one fact fixes? A hand-written formulation sentence (mechanism test) vs a label-free fact: the program of the most similar other MAMO problem from all models' strict-check-passing programs.
## 2026-10-19 14:03 UTC: questions the talk slides raise, fewer extra pages, and a correction to Finding 1 (writing session; user: expected questions that the main slides make people think of, prepare the slides, remove unimportant extras)
- **Correction (Finding 1, CVRP).** The routing numbers are % of 30 instances (no doc .23, no doc + thinking .03, the TSP-only reference sheet .07, the CVRP snippet .83 / .77 / .90 on 3 seeds; FINDINGS 'CVRP results (10:25)'), not 'out of 100', and the snippet given is DOC_TASK['cvrp'] in poc/run_co.py, 11 lines of code, not 5. The 'whole manual' is the full cheat sheet, which shows TSP routing without the capacity dimension (an incomplete reference). Fixed in the talk (slide 5 and its Korean script), the full deck, figs 18 / 21 and ex_finding1, PROPOSAL.md / PROPOSAL_ko.md (Finding 1 example, §4 step 2, §6.1 and §6.2 rows) and the README comment. No number changed; only what they count and the snippet length.
- **Questions slide (9):** 16 expected questions, each tagged with the talk slide that raises it (2–8) and linked to the extra page(s). Four new pages: 'is a program always better than words?' (Qwen3-8B polygon copies 1 of 8 vs 8 of 8; Qwen3.6 MATH-500 text 98.3% vs program 86.8%; gpt-oss-20b agreeing pairs wrong: two texts 1.5%, text + program 0.3%; from PROPOSAL §1), 'what exactly is the fact?' (excerpt of the real CVRP snippet; why the sheet hurts: 10 programs call RegisterUnaryLongLivingCallback), 'can retrieval (RAG) find the fact?' (FINDINGS '14:25: RAG results', Qwen3-32B seed 1: 6 problems no doc 67 / snippet 96 / top-1 97 / top-3 93 / code-only 90; CVRP 23 / 83 / 70 / 57 / 53), 'is there always a free check?' (one check per problem kind with its measured leak).
- **Removed extra pages:** 'it pays off' (repeated slide 7), 'all findings at a glance', 'the examples check in detail' (repeated Finding 2 and the leak page), 'words we use'. The talk deck is 9 slides + 21 extra pages.
## 2026-10-19 14:15 UTC: which problem kinds each finding covers (writing session; user: the problem range of slide 2 and the findings' ranges differ; do the findings consider all problems?)
- **Answer: no.** Measured scope of each talk claim: program vs words: geometry (holds), competition math (text as good; the program as a second opinion). Fact: routing (CVRP 23 → 77–90%, Solomon ≤ 6 → 100% valid), word problems (65.4 → 72.0%, small models +44), geometry as 'only the needed tools' (92% vs 75%); not tested on contest problems; no step helps proofs. Free check + think on failure: contest (examples), geometry (two versions), word problems (MAMO, 12–22% of always-thinking's tokens), routing (inside the U1 pool); competition math mixed (MATH-500 yes, AIME costs more). Whole recipe 87% vs 74%: only the geometry suite (108) + optimization suite (100) × 3 models; word problems via the held-out MAMO test; contest only check + think. Reuse: routing / scheduling only.
- **Correction:** '624 problems' was 208 problems (108 geometry + 100 optimization) × 3 models = 624 runs (PREREG_U1 §Results). Fixed in the talk (slide 7 and its Korean script, the extra pages), the full deck, figs 19 / 21 and ex_method, PROPOSAL.md / PROPOSAL_ko.md §5 and the §6.2 row (which now also say that contest, word problems and proofs are tested separately).
- **Deck:** slide 2 marks 'Math and proofs' as an extension (dashed card); Findings 1, 2 and the method carry a 'holds on' strip with the five slide-2 icons (faded = not tested or does not hold); new extra page 'do the findings cover all five kinds?' (the matrix above) as the first expected question. 9 slides + 22 extra pages.
## 2026-10-19 14:16 UTC: talk deck renamed (writing session; user): PROPOSAL_slides.pptx → Proposal_Team5.pptx (git mv; poc/make_slides.js writes the new name; README and the poc/make_slide2_shapes.py docstring updated). The full deck keeps its name PROPOSAL_slides_full.pptx.
## 2026-10-19 14:19 UTC: correction, contest check (writing session; user: keep finding problems while reviewing the slides): the contest result 66.3% @ 24.7k (= always high effort 66.2% @ 30.1k, 18% fewer tokens) is N13b, the examples check PLUS an approximate brute-force program on small inputs (FINDINGS 2026-10-16 09:54 / 09:59); the examples alone (N8) give 65.0% @ 20.2k. Slides and text had credited the examples alone. Fixed: talk Finding 2 (Check A now shows always 66.2% · 30k, examples 65.0% · 20k, + brute-force check 66.3% · 25k) and its Korean script, the 'free check' and coverage pages, the full deck (examples-check slide, glance panel, baselines row), fig21 and ex_finding4, PROPOSAL.md / PROPOSAL_ko.md Finding 4. Every other number on talk slides 2–8 was re-checked against PROPOSAL / FINDINGS / PREREG and holds.
## 2026-10-19 14:25 UTC: speaker notes updated (writing session; user: update the slide note scripts): the Korean talk script (slides 1–9) follows the current slides (311 contest problems named on slide 4; 65% with the examples alone and 66% with the brute-force check on slide 6; 208 problems × 3 models and the held-out 79% = 79% on slide 7; ≈ 4.5 minutes, seconds per slide in brackets). Each of the 22 extra pages now has a short Korean answer in its notes ('(답변) ...'), with the numbers shown on that page.
## 2026-10-19 14:28 UTC: why these problems (writing session; user: how do geometry, contest, routing / scheduling and word problems differ, split or combine, and why did we choose them?): new extra page 'why these problems, and how do they differ?' (first expected question): exact answers graded by code, a free check for each, code agents already write; two needs: the right algorithm (geometry: textbook tasks; contest: the same kind, much harder) or the right solver call (routing / scheduling from data; word problems add text → equations); per kind: input, program, free check, typical failure, what helps most, size. Evidence for the two needs: U1 (geometry failures fixed by thinking, 36 / 37 for Qwen3-8B; fact-only fixes ≈ 1 item per model; the mechanism router chose the fact on 49 of 100 optimization items). Slide 2 caption now gives the reason; Korean script slide 2 says it (35 s). 9 slides + 23 extra pages.
## 2026-10-19 14:34 UTC: slide 2 = the four kinds the recipe covers (writing session; user: why does the slide 2 script still mention math and proofs?): the talk scripts were already in the deck's notes (commit 5142087), but slide 2 still showed and named 'Math and proofs (extension)'. Now slide 2 shows four kinds in two families (needs the right algorithm: geometry, contest problems; needs the right solver call: routing / scheduling, word problems), and its Korean script (30 s) names only these and why they were chosen. Competition math and proofs stay in the extra pages (coverage table column 'Math, proofs (extension)', the proofs page, the 'how hard' page, and the expected question 'what about competition math and proofs?'). The 'holds on' strips show the four kinds.
## 2026-10-19 14:42 UTC: talk deck without competition math and proofs, and 'hint' instead of 'fact' (writing session; user: remove math / proofs from the proposal ppt for now, not from the md files; 'fact' is not intuitive for beginners)
- Proposal_Team5.pptx only: no competition math or proofs on any page (pages 'program vs words' and 'proofs' removed; the vote, free-check, coverage, how-hard, related, reported, setup and limits pages drop their math / proof rows; their Korean answers updated). A switch WITH_MATH in poc/make_slides.js keeps them in PROPOSAL_slides_full.pptx, so the full deck and its figures still match PROPOSAL.md / PROPOSAL_ko.md, which are unchanged.
- The talk says 'a code hint' / 'hint' where the full deck and the proposal say 'fact' (one renaming pass over every text, table and chart label of the talk; Korean notes '힌트'). 9 slides + 21 extra pages.
## 2026-10-19 14:51 UTC: contest scope made explicit; team members on the title (writing session; user: why does the method not hold on contest problems, should we show it; add Sangjun Lee and Seongbin Park): contest programs are plain algorithms with no library, so the hint step has nothing to add (failures are reasoning errors, U1 mechanism 3), and each problem is new, so reuse does not apply; steps 3–4 (examples + brute-force check, think on failure) hold there (66.3% @ 24.7k vs 66.2% @ 30.1k). Talk slide 7 now shows, under each of the five steps, the slide-2 kinds that use it (hint: geometry, routing, word problems; reuse: routing only); the coverage page says why (no library to hint; each problem is new) and is linked from a new expected question 'why no hint for contest problems?'; Korean script of slide 7 says it. Title slides of both decks: 'Team 5: Sangjun Lee, Seongbin Park'.
## 2026-10-19 14:55 UTC: thank-you slide (writing session; user: compact, no content listing): talk slide 9 is now 'Thank you / Questions? / Team 5: Sangjun Lee, Seongbin Park' on the title layout; the expected questions with their extra-page numbers moved into that slide's speaker notes for the presenters.
## 2026-10-19 14:57 UTC: a checked program for a similar problem fixes the formulation errors that thinking repeats (FORM, FORM-S; PREREG_X7.md). On MAMO, errors that repeat across a problem type are knowledge, not effort: gpt-oss-20b writes all 34 travelling-salesman problems with Miller-Tucker-Zemlin constraints that include the start city (no solution); with 10k tokens of thinking the Qwen3 models write the same textbook constraints (1–18% right), and a hand-written sentence describing the correct form is misapplied (it excludes the start city on one side only) and drops Qwen3 TSP accuracy from 50–68% to 0–6%. Showing each problem the program of its most similar other MAMO problem that passed the strict check (two runs agree, solver finds a solution; no labels) fixes them: TSP 47–71%, and the whole recipe (two agreeing programs, else think) rises from 78.4–78.8 to 79.8–80.5% (gpt-oss-20b), 71.7–73.5 to 76.8–77.5% (Qwen3-14B-AWQ), 71.0–73.1 to 77.6–78.0% (Qwen3-8B) at 17–33% fewer tokens, every seed. Control: with only the model's own programs, gpt-oss-20b keeps the full gain, the Qwen3 models 22–47% (the rest comes from other models' programs). Also: STORM on NL4OPT + IndustryOR is 73.6% at 7.9k tokens — our training-free recipe matches or beats it there at a quarter to a third of the tokens. Started (pre-registered): the stream version (only earlier problems' programs) and the same library on NL4OPT + IndustryOR.
## 2026-10-19 14:58 UTC: why no hint for contest problems (writing session; user question): contest programs call no library, so the API hint has nothing to supply; failures are reasoning errors. The closest hint was measured (H4, PREREG_H4.md, 311 problems × 3 seeds): 8 related geometry helpers, Qwen3-32B no-think 12.1 → 13.7% (n.s.), gpt-oss-20b low 37.7 → 33.4% (96 lost / 56 gained, p ≈ 0.002; it reasons less and writes different wrong solutions). A per-problem algorithm hint would be part of the solution (needs a human per problem; not automatic: no problem family to mine from). The talk's coverage page now shows this measured result (✗) instead of 'not tested', and its Korean answer explains it.
## 2026-10-19 15:23 UTC: the checked-program library holds as a stream on MAMO but not on NL4OPT + IndustryOR (FORM2, 3 seeds × 3 models). Showing only earlier problems' programs keeps 60–77% of the cheap-program gain and +0.4 to +3.9 points for the whole recipe at 15–26% fewer tokens. On NL4OPT + IndustryOR, where problems rarely repeat, the library lifts the Qwen3 models' first program but the recipe loses 0.5–1.4 points (more wrong programs agree after copying a similar problem's formulation). Verdict: the library is worth it where problem types recur. Also pre-registered and started (user task, docs/prereg/PREREG_CH.md): an approach hint on the 311 contest geometry problems — human Codeforces tags (an upper bound) and the model's own low-effort plan — as a first attempt and as a cheap step before high effort, gpt-oss-120b (GPU1) and gpt-oss-20b (GPU2), seeds 1–3.
## 2026-10-19 16:39 UTC: approach hints on contest geometry, gpt-oss-20b (user task CH, 3 seeds; 120b still running). As a first attempt neither hint earns its place: human Codeforces tags +2.1 points (49.2% @ 8.2k vs medium 47.1% @ 8.7k; p = 0.09), the model's own plan −0.8. As a step before high effort both add ~3 points over N13b (55.3 / 55.0% vs 51.9%) but at slightly more tokens than the rule allows — and a control (added after seeing this, not pre-registered) shows a second plain medium attempt gives most of it (54.6%): the hint itself adds +0.7 / +0.4 (n.s.). For 20b the extra step works because its high effort is weak (37.9%, hits the 64k cap), not because of the hint. Raw rows: tags mostly shorten its reasoning (16k cap hits 28.9% → 21.8%); half the problems it gains were medium replies that ran out of tokens.
## 2026-10-19 17:46 UTC: approach hints on the 311 contest geometry problems — verdict (user task CH, PREREG_CH.md, 3 seeds × 2 models). No hint earns its place. First attempt: human Codeforces tags +1.7 (gpt-oss-120b, 58.5% @ 6.6k vs 56.8% @ 6.8k, p = 0.17) and +2.1 (gpt-oss-20b, p = 0.09) — below the +3 bar and not significant; the model's own low-effort plan HURTS 120b by 5.8 points (p < 0.001, every seed): the coder trusts the plan, reasons ~1.4k tokens less and implements wrong plans faithfully. As a step before high effort: 120b TAG 67.5% @ 25.3k (rule: ≥ 66.2% at < 24.7k or ≥ 68.3%) and PLAN 66.5% @ 26.0k fail; against a plain second medium attempt neither hint is significantly better for either model (p = 0.32–0.70). What gain there is depends on human labels (tags: net gain from named-algorithm tags, larger above rating 1800), not on the method. Judge (gpt-oss-120b low; 20 verdicts read, 18 agree, 2 borderline): tags followed 72–75% of the time, plans 75%; followed hints pass more often. N13b (examples + brute-force check, 66.3% @ 24.7k) stays the best contest policy; the proposal is unchanged.
## 2026-10-19 17:48 UTC: for the 24 GB-GPU model, retrying at medium with the free check may beat thinking harder on contest geometry (exploratory, seeds 1–3; pre-registered for fresh seeds 4–8 now, PREREG_CH.md CH-R). gpt-oss-20b's high effort is weak (37.9% @ 47.5k, it runs out of its 64k budget); up to three medium attempts, accepting the first that passes the examples and the brute-force check, reach 55.9% @ 20.7k — 4 points above the examples-plus-oracle cascade to high (51.9% @ 37.7k) at 55% of its tokens. For gpt-oss-120b high remains the better last step. Running: gpt-oss-20b medium seeds 4–8 (GPU1 + GPU2) to test this on samples it was not found on.
## 2026-10-19 18:21 UTC: slide 8 script in more detail (writing session; user): the Korean note of talk slide 8 now has a spoken core (≈ 60 s: each 'usual way → ours' row with its number, the three next steps, the takeaway) and, below it, a longer explanation for questions or spare time (Snell et al., Thinkless / AdaptThink, teacher-program banks, 74 → 87% and 4.1k → 2.5k on 208 problems × 3 models, 79% = 79% on held-out MAMO, ORLM-8B 69.5% = untrained Qwen3-8B, gpt-oss-20b 78.8%; MAMO residual errors: about half disputed labels, the rest repeated formulation mistakes). Spoken total of slides 1–9 ≈ 295 s.
## 2026-10-19 18:28 UTC: what 74% and 87% are (writing session; user question): PREREG_U1 (U1 / U1r): 108 generated geometry + 100 generated optimization problems, each solved by Qwen3-8B, Qwen3-32B-AWQ and Qwen3.6-35B-A3B (624 runs), cure seeds 1–3. 74% = DIFFICULTY (Snell-style: 3 quick samples, thinking for the items whose samples disagree most, budget matched to the mechanism router; 73.7 / 74.7 / 74.8%). 87% = FACT-FIRST-THEN-THINK with the HAND-WRITTEN fact (exact solver snippet; geometry: one-sentence algorithm hint or only the needed helpers), thinking only when the label-free check fails (87.2 / 87.5 / 86.7% @ 2.5–2.7k); found as an exploratory baseline after U1, then predicted and confirmed on seeds 2–3; with BM25-retrieved facts 84.1 / 84.3 / 83.5% @ 3.2–3.5k. The automatic (own checked program) fact was tested on word problems (MAMO), not on this suite. Talk slide 7's bar now reads 'ours, hand-written hint'; Korean notes of slides 7 and 8 say so (and 84% with a retrieved hint).
## 2026-10-19 18:31 UTC: methods next to the numbers on talk slides 7–8 (writing session; user: what are 69.5% and 79%, why only results again?): from PREREG_X7. 79% = gpt-oss-20b on the 863 held-out MAMO word problems, write the program twice with the fact and think unless both run and agree: fact mined automatically (its own shortest check-passing program from NL4OPT / IndustryOR) 78.8% vs hand-written 78.9% (3 seeds within −1.2 to −0.1), no fact 73.2%. 69.5% = ORLM-LLaMA-3-8B (fine-tuned specialist; its template and solver, greedy, our grader) 69.5% @ 1.1k on MAMO vs untrained Qwen3-8B with its own mined fact, one program, thinking only if it fails to run, 69.5% @ 1.0k (71.0% @ 3.1k with the two-version check). Slide 7 now states the 79% comparison (model, benchmark, no-fact baseline); slide 8's rows state what each number compares; the Korean scripts say how the 74 / 87% were measured (3 quick answers that disagree = 'hard-looking'; hand-written hint, check, think on failure), with optional parts marked. Spoken total ≈ 315 s at 5.2 syllables / s (≈ 280 s at a normal 5.8).
## 2026-10-19 18:36 UTC: slide 6 explains what a free check is (writing session; user: what is a free check, slide 6 is unclear): a flow at the top (the model's program → free check: run it and compare, no answer key, no thinking → pass: keep the answer / fail: think harder, tokens spent only there); each check with one pass and one fail example in plain words (Make a triangle!: example 3 4 5 → 0, the program prints 0; Arrow: corners differ from the example; two versions print the same / 6 vs 0); rows 'think if an example fails' and '… or a brute-force run'. Korean script of slide 6 defines the free check first (≈ 60 s).
## 2026-10-19 18:42 UTC: slide 6 shows how the check runs; 'Graduate NLP' removed; how the hint is obtained (writing session; user): talk slide 1 reads 'Team 5: Sangjun Lee, Seongbin Park · POSTECH CSED490E'. Slide 6: numbered run order (① the model writes a program at normal effort → ② the free check runs on the computer, no model, no answer key → ③ pass: submit / fail: think harder and write again) and each check drawn as it runs (Make a triangle!: example 3 4 5 → 0, our program prints 0 → submit; Arrow: corners differ → think again; version A prints 6, version B prints 0 → think again); Korean script ≈ 70 s. New extra page 'how do we get the exact hint?': one hint per problem type in the prompt before the task, three sources with how / result / limit (by hand: routing 23 → 77–90%, word problems 65 → 72%; BM25 search: 97% vs 96% on 6 optimization problems, 84% vs 87% on the 208 suite, near miss 83 → 57%; the model's own shortest check-passing program of the same type: MAMO 79 = 79 / 72 vs 71 / 71 vs 72; another type's program −14 to −21); only the needed calls (geometry 75% with all helpers vs 92%). 9 slides + 22 extra pages.
## 2026-10-19 18:46 UTC: talk slide 6 remade (writing session; user: review and remake slide 6): two panels instead of a strip plus two dense panels. Left 'How a free check works': one real example as a flow (the problem shows an example, sticks 3 4 5 → 0 → run our program on 3 4 5, no model needed: it prints 0 → same: submit, no extra tokens / different: think harder, write again), and below it the no-example case (version A prints 6, version B prints 0 → different → think). Right 'Result: the same accuracy, fewer tokens': contest 66.2% @ 30k always vs 66.3% @ 25k thinking only on failure (examples alone 65.0% @ 20k; a brute-force second check gives 66.3%), geometry 98% @ 5.9k vs 99% @ 4.3k. Korean script ≈ 60 s.
## 2026-10-19 18:54 UTC: talk slides 5, 7, 8 remade (writing session; user: review and remake slides 5, 7, 8; show how the hint is provided)
- Slide 5: left 'How the hint is given' (task + the hint, 11 lines of exact OR-Tools usage with two of its calls → the program runs: best route; a long reference sheet without the weight rule → the model invents RegisterUnaryLongLivingCallback → crash); right: 30 routing problems solved optimally (task only 23%, + think longer 3%, + long sheet 7%, + short hint 77–90% over 3 runs) and 'where the hint comes from, once per problem type' (by hand / found by search / the model's own checked program, no human).
- Slide 7: four steps in a row (① program + hint, ② free check, ③ pass: submit · fail: think, ④ same type again: reuse) with the kinds that use each; left one real MAMO problem (no hint → crash; its own checked program as the hint → both versions print 20000 → submit; 0.6k vs 5.3k tokens); right 208 problems × 3 models: think where answers differ 74% @ 4.1k, ours with a searched hint 84% @ 3.3k, with a hand-written hint 87% @ 2.5k; note: held-out MAMO, automatic = hand-written (79% = 79%, gpt-oss-20b).
- Slide 8: each row has a topic (when to think / what to give / what it costs) and plainer words.
- Korean scripts of slides 5 and 7 follow the new layouts.
## 2026-10-19 18:58 UTC: slide 5 shows how the hint is picked (writing session; user: describe or visualize simply how we pick the hint): the three-line list of hint sources became a four-box flow, 'How we pick the hint (once per problem type)': solve other problems of this type → keep those passing the check → pick the shortest one → = the hint, with 'no human needed; a hand-written or searched hint also works' below. Korean script of slide 5 says the same in two sentences (≈ 60 s).
## 2026-10-19 19:01 UTC: '3 runs' explained and taken off the talk slides (writing session; user: what is '3 runs', why does it keep appearing?): '3 runs' = the same experiment repeated with 3 random seeds (sampling makes each run differ); it is our replication rule since a one-seed result did not replicate (N6, 2026-10-14). On slide 5 only the short-hint arm had 3 runs (CVRP snippet .83 / .77 / .90); task only, think longer and the long sheet are single runs. Slide 5 now shows the hint bar as 83% (mean of the 3 runs) and its notes say so (presenter's note, not read aloud); slide 6 drops '3 runs'; the extra pages say 'runs' instead of 'seeds' (talk only).
## 2026-10-19 19:06 UTC: talk tightened for 5 minutes + 5 minutes of questions (writing session; user: review and reorganize for the 5 + 5 format): the slides stay as remade (flow: problems → programs → two problems and the question → Finding 1 hint → Finding 2 free check → method and overall result → what is new and next → thank you); the Korean scripts were rewritten shorter with each number and its method kept (≈ 210 s spoken at 5.2 syllables / s, ≈ 4:30–4:50 with pointing and transitions; was ≈ 360 s). Presenter notes kept: slide 5 (the 83% is the mean of 3 runs), slide 8 (longer explanation for questions), slide 9 (expected questions → extra-page numbers). 22 extra pages in the order of the talk slides that raise them.
## 2026-10-19 19:10 UTC: slide 5, fewer words on picking the hint (writing session; user: too much text): 'How we pick the hint (per problem type, no human):' its past programs → ✓ passed the check → shortest = hint (three boxes; the footnote removed).
## 2026-10-19 19:30 UTC: hint picking moved to the method slide (writing session; user: how we pick the hint belongs to our method slide; 'check' appeared before slide 6 defines it): slide 5 keeps how the hint is given and the 30-problem result, with a pointer 'How we pick the hint without a human: see our method'; slide 7's left panel now starts with '① How we pick the hint (once per type, no human): its past programs → ✓ passed the check → shortest = hint', then the one real problem (no hint → crash; with the hint both versions print 20000 → submit; 0.6k vs 5.3k tokens). Korean scripts of slides 5 and 7 moved the sentence accordingly.
## 2026-10-19 19:31 UTC: slide 1 states only the focus (writing session; user: slide 1 should simply say where we focus, not hints or checks): the talk's title slide now reads 'Focus: math with an exact answer, solved by programs an LLM writes' under the title, with the team line; the hint / check / thinking pills are gone (the full deck keeps its old subtitle through slideTitle's default). Korean script: '저희는 답을 정확히 계산해야 하는 수학 문제를 LLM이 프로그램을 짜서 푸는 경우에 집중합니다. 목표는 더 적은 토큰으로 맞는 답을 얻는 것입니다.'
## 2026-10-19 19:34 UTC: slide 6 defines the free check in one line (writing session; user): the left panel opens with 'Free check: run the program and compare with something we already know. No answer key, almost no cost.', then the example flow; Korean script adds '공짜 검사란 프로그램을 실행해서 이미 아는 것과 비교해 보는 것으로, 정답도 추가 생각도 필요 없습니다.' (≈ 40 s).
## 2026-10-19 19:36 UTC: two extra pages on getting hints effectively and cheaply (writing session; user): 'Q: how do we get a hint that works?' — what works (the exact calls the type needs: routing 23 → 83%; only what is needed: geometry 75 → 92%; short and from the same type: MAMO 79% = by hand) and what hurts (a long manual missing one rule 7%; a near-miss page 83 → 57%; another type's program −14 to −21; a bare list of names 66 → 56%), plus a decision flow (past programs of this type and a free check → the shortest that passed; titled snippet docs → search, top one only; neither → write once by hand). 'Q: what does a hint cost, and what does it save?' — input tokens per prompt (no hint 488, exact snippet 701, long sheet 901, search top 3 1,138; geometry helpers 912 vs needed 113; from CRITIQUE §4 update) against output tokens saved (word problems, Qwen3-32B: hint + always think 72.0% @ 5.5k vs hint first 72.4% @ 1.3k; 208 × 3: 74% @ 4.1k vs 87% @ 2.5k) and the one-time cost per type. Korean answers in the notes; linked from the expected question 'how do we get a hint that works, cheaply?'. 9 slides + 24 extra pages.
## 2026-10-19 19:37 UTC: slide 6, the 'examples alone' line simplified (writing session; user: what does it mean, is it necessary?): the contest result 66.3% @ 25k uses two checks (the examples and a slow brute-force version, N13b); the examples alone give 65.0% @ 20k (N8). The slide now says only 'checks used: the examples, and a slow brute-force version of the program' (so 66.3% is not credited to the examples alone); the 65.0% moved to the presenter note of slide 6 and stays on the free-check extra page.
## 2026-10-19 19:47 UTC: extra pages on checking well and cheaply; slide 8's next steps (writing session; user: extra slides on checking efficiently and effectively; the next part should be about getting hints and doing checks efficiently and effectively)
- 'Q: how do we make a check catch more?': the second view must err differently (moved / turned copies pick the right program 99.7%; two versions with and without helpers 99% vs 98% always thinking; examples + brute force 65.0 → 66.3% on contests; a text answer next to the program cuts wrong agreements 17% → 10%) vs what does not (majority vote 4.3% picked wrong; two versions that share a mistake: gpt-oss-120b contest 56.9% @ 11.8k vs 56.8% @ 7.1k); and the ceiling (24–37% of wrong contest programs pass the examples; 12–16% of word problems agree but are wrong; a perfect check adds only 1–3 points for 14B+).
- 'Q: what does a check cost, and when is it worth it?': examples, moved copies and plan rules cost 0 tokens (CPU); model-written tests +340; a second version one more program; a brute-force version +4.5k on contests; contest policies: always 66.2% @ 30k, examples only 65.0% @ 20k, + brute force 66.3% @ 25k, + a second model (Qwen3.6, N17) 65.5% @ 25k; order: zero-token checks first, a different second version only where mistakes stay silent, stop when a better check adds 1–3 points.
- Slide 8 'Next: get the hints and run the checks better and cheaper': hints picked automatically for every problem type; checks that catch more mistakes without extra tokens; test both on more models, report and code. Korean core script and the longer explanation updated. 9 slides + 26 extra pages.
## 2026-10-19 19:49 UTC: slide 8 next steps say 'automatically' (writing session; user): 'Next: get the hints and run the checks automatically, better and cheaper' — hints picked automatically for every problem type; checks chosen automatically, catching more for no extra tokens; test both on more models, report and code. Korean script and its longer explanation say the same (checks chosen per problem type; today 30 labelled problems already pick the policy, 0.6 points from the best).
## 2026-10-19 19:50 UTC: slide 8's next part = how to get hints and run checks automatically, effectively and cheaply (writing session; user): two panels under 'Next: get the hints and run the checks automatically, effectively and cheaply' (then: more models, report and code). Hints: pick per type the shortest past program that passed the check; tell a new problem's type first (another type's hint misleads); keep only the needed calls (about 200 input tokens). Checks: zero-token checks first (examples, moved copies, plan rules); add a second view that errs differently where errors stay silent; choose the policy per type from 30 labelled problems. The 'what is new' rows were tightened to make room; Korean script ≈ 55 s.
## 2026-10-19 19:51 UTC: slide 8's next part ends with math proofs, not more models (writing session; user): the header note 'then: more models, report and code' became a box 'then: extend to math proofs'; Korean script: extend the method to math proofs, where Lean already gives a perfect free check and the open problem is a hint that helps (longer note: for general models neither a similar proof nor an inequality toolkit helped; Goedel-Prover-V2-8B proves 74% of miniF2F). Slide 8 script ≈ 65 s; talk ≈ 4:15 spoken.
## 2026-10-19 19:53 UTC: slide 8 with less text, math proofs as a full card (writing session; user: too much text in the next part, the math proof part too small): the 'what is new' rows shortened (think more on hard-looking problems → only when a free check fails: 87% vs 74%; the whole manual → one short hint, picked with no human; fine-tune a specialist: 69.5% → no training, one 24 GB GPU: 69.5%); 'Next' = three equal cards (Automatic hints: picked per problem type, only the needed calls; Sharper free checks: catch more mistakes, still with no extra tokens; Math proofs: Lean checks every step, find the hints that help). Korean script ≈ 40 s; the longer explanation stays in the notes.
## 2026-10-19 19:54 UTC: slide 8 reviewed and tidied (writing session; user: review and update that slide): row 3 names the benchmark (fine-tune a specialist: 69.5% on MAMO → no training, one 24 GB GPU: the same 69.5%); the three 'Next' cards are shorter with larger icons and titles (no empty half), leaving air above the takeaway.
## 2026-10-19 19:55 UTC: slide 8 references (writing session; user: small references at the bottom): 10-pt line under the takeaway: Snell et al., ICLR 2025 (think on hard problems) · DRoC, ICLR 2025 (documentation for solver code) · Huang et al., ORLM, arXiv 2405.17743 (fine-tuned specialist) · Huang et al., Mamo benchmark, 2024 · Zheng et al., miniF2F, ICLR 2022 (Lean proofs).
## 2026-10-19 19:56 UTC: where '24 GB' comes from (writing session; user question): PREREG_SIZE addendum (2026-10-17, user clarification): the target was models that run on one RTX 3090 (24 GB); fit computed as weights + the KV cache of one 16k-token request (Qwen3-8B bf16: 16 GB + 2.4 GB ≈ 20 GB with overhead; gpt-oss-20b MXFP4 13 GB; Qwen3-14B-AWQ ≈ 10 GB; Qwen3-32B-AWQ does not fit with 16k thinking). All runs were on 96 GB RTX PRO 6000 GPUs (accuracy does not depend on memory); the 24 GB is a computed fit, not a run on a 3090. Slide 8's small footnote now says so.
## 2026-10-19 19:57 UTC: slide 8's 24 GB footnote removed (writing session; user): the reference line keeps only the references.
## 2026-10-19 19:58 UTC: slide 8's usual way referenced (writing session; user): small gray markers on 'the usual way' items pointing to a numbered reference line at the bottom: think more on hard-looking problems [1] Snell et al., ICLR 2025; the whole manual, or retrieved documentation [2] DRoC, ICLR 2025; fine-tune a specialist: 69.5% on MAMO [3] ORLM, arXiv 2405.17743, [4] Mamo benchmark; the Math proofs card [5] miniF2F, ICLR 2022.
## 2026-10-19 20:00 UTC: slide 8 row 3 compares same-size models (writing session; user: what is MAMO; if we say 24 GB, show how big the other side is): MAMO is the benchmark (863 optimization word problems), not a model. The specialist ORLM-LLaMA-3-8B is itself 8B and would fit the same 24 GB GPU, so the difference is training, not GPU size. Row 3 now reads 'fine-tune an 8B specialist (ORLM): 69.5% on MAMO [3, 4]' → 'an untrained 8B model (Qwen3-8B): the same 69.5%' (topic 'What it takes'); reference [4] says 'Mamo: 863 optimization word problems'; Korean script updated.
## 2026-10-19 20:07 UTC: the first time, with no past programs (writing session; user question): new extra page from the experiment session's FORM2 stream result (PREREG_X7, 15:23 UTC): MAMO in a random order, each problem shown only programs of earlier problems that passed the strict check (first problem: one example program from another benchmark; no answer key): FFR 78.6% @ 1.9k → 79.0% @ 1.6k (gpt-oss-20b), 72.5% @ 2.8k → 76.4% @ 2.1k (Qwen3-14B-AWQ), 72.1% @ 3.2k → 75.9% @ 2.3k (Qwen3-8B); limits: 60–77% of the full library's gain, the pool holds five models' programs, a type whose own programs are all wrong gets a wrong hint, varied problems (NL4OPT + IndustryOR) only save tokens. Korean answer in the notes; expected question 'what about the first time, with no past programs?'. 9 slides + 27 extra pages.
## 2026-10-19 20:09 UTC: the hint pool named on the method slide (writing session; user: so it requires some hint pool): yes, a pool of programs is required, but no human, no answers and no curated library: it is the model's own programs on earlier problems of the type that passed the check, and it fills up as problems arrive (stream result on extra page 25). Slide 7: '① Hint pool: its own checked programs (no human)' with 'programs on earlier problems → ✓ passed the check → shortest = hint'; Korean script says the pool is filled without answers as problems arrive.
## 2026-10-19 20:14 UTC: what a hint is and does (writing session; user: are hints part of the solution or library usage? what exactly do they do?): extra page 14 rebuilt — two kinds side by side (hand-written routing hint: library usage only, 11 lines, the same for all 30 problems; automatic word-problem hint: another problem's shortest checked program, e.g. the vans-and-trucks program with CreateSolver / IntVar / Minimize / Solve and that problem's own limits) and what it does (✓ stops invented function names: Qwen3-1.7B wrote Solver.SUCCESS and solver.INFINITY, 0.1% → 45%; ✗ does not write the equations, most errors left are wrong equations; ✗ never this problem's numbers or answer, one hint per type). Korean note adds the nuance: the most-similar program (instead of the shortest) carries a formulation pattern, which fixes repeated formulation mistakes when it is right and copies them when it is wrong (FORM, X6-VER).
## 2026-10-19 20:37 UTC: held-out test of the whole recipe on unseen OptMATH-Bench (100 harder optimization problems; PREREG_HO.md; 3 seeds × 3 models + STORM). What generalises: cheap program first, thinking only when it visibly fails — at least as accurate as always thinking at 62–90% of its tokens for every 24 GB-GPU model (gpt-oss-20b 38.3% @ 3.7k vs 32.7% @ 5.4k), within 1–2 points of the trained STORM-4B (40.3% @ 14.1k) at a quarter of its tokens, and combined with STORM as the fallback it beats STORM alone (43.3% @ 7.0k). What does not: the usage example mined from NL4OPT (no help or worse) and the two-agreeing-programs check (agreement is rare on hard problems, so it costs more than always thinking). Raw failures are mostly formulation and data (products of variables in a linear solver, large index tables, an asymmetric table read as symmetric), not API. Also fixed a sandbox bug (scipy/cvxpy imports exceeded the CPU limit; earlier runs unaffected).
## 2026-10-19 21:38 UTC: same knowledge as code vs as words (CD, PREREG_CD.md, 3 seeds × 3 models): the form is not the mechanism. API usage transfers equally in words and code (e.g. Qwen3-8B 34.3% → 51.5% / 51.7%). For formulation knowledge a partial note, in words or code, can displace the model's own working formulation: on MAMO's TSPs both notes drop the Qwen3 models from 57–59% to 0–5% (they copy the note's x[i][j] notation and lose the self-loop exclusion). A note helps only when it pins down the whole constraint the model gets wrong (redistribution: Qwen3 0–10% → 85–88% with the full constraint as code). The robust fix remains a complete checked program for a similar problem (FORM). Also: on OptMATH the program library saves 17–26% of the Qwen models' tokens but does not raise accuracy (problems recur less than in MAMO).
## 2026-10-19 23:36 UTC: MAMO replication, Qwen3-32B-AWQ (3 seeds): the automatic fact (its own mined program) beats the hand-written snippet on every seed (two-agreeing-programs pipeline 75.3–76.2% vs 70.7–71.1%; fact-first 76.7–78.3% @ 0.6k vs always thinking 63–64% @ 7.0k). The no-human claim on held-out MAMO now holds on 3 seeds for all four models.
## 2026-10-19 23:37 UTC: on the unseen benchmarks the default needs no labels: "cheap program first, think only on a visible failure" is within 1.1 points (utility) of the best policy in all 15 held-out cells (best in 9); always thinking loses up to 11 points; a 30-problem labelled pilot does no better than the default.
## 2026-10-20 00:37 UTC: second unseen benchmark, OptiBench (605 problems, 3 seeds × 3 models): the recipe holds and here the facts pay. Thinking only on a visible failure beats always thinking for gpt-oss-20b (70.7% @ 1.2k vs 68.9% @ 2.1k) and Qwen3-14B-AWQ (59.3% @ 3.4k vs 48.3% @ 6.5k), ties for Qwen3-8B (57.5% @ 4.9k vs 57.9% @ 7.7k). Unlike OptMATH, the small models' failures here are usage errors, and a fact fixes them: a hand-written usage card for the installed libraries +4 / +14 / +7 points on the first program, and the label-free library (the checked program of the most similar other problem) even more, +7 / +17 / +24. Full label-free recipe: Qwen3-14B-AWQ 63.9% @ 1.8k and Qwen3-8B 63.1% @ 2.7k vs always thinking 48.3% @ 6.5k / 57.9% @ 7.7k. The library's gain holds on dissimilar source problems too (not only near-duplicates). So: facts pay where failures are usage errors, not where they are formulation or data errors.
## 2026-10-20 00:44 UTC: slide 4's left side explained (writing session; user: the script for the left side is hard to follow): the caption under the terminal now says what A and B are ('A: the task only. B: the task + 8 helper functions it did not need (Qwen3-14B)'); the Korean script walks through it: 10 points, the rubber band has 6 corners; the same model writes a counting program twice; A (task only) prints 6, B (task + 8 unneeded helpers) prints 0 with no error, so without the answer you cannot tell B is wrong; a program can also stop on a library function that does not exist.
## 2026-10-20 00:54 UTC: STORM-4B on OptiBench: 78.7% @ 7.9k — 5.7 points above our best training-free 24 GB recipe (gpt-oss-20b with the checked-program library, 73.0% @ 1.0k), at 8 × the tokens; our cheap program with STORM only on a visible failure gets 76.3% @ 2.3k. (On OptMATH STORM's lead was 1–2 points; its training data could not be checked for overlap.)
## 2026-10-20 01:14 UTC: the automatic hint is the program text itself (writing session; user question): poc/run_nlopt.py (_verified_examples, NLOPT_EX_SHORTEST): the pool is the same model's programs without any hint on the OTHER benchmark that run and print a value; the shortest one per source benchmark is pasted into the prompt after the problem as 'A program that runs with this library (written for a different problem):' followed by the code; the model is not asked to run it and writes its own program. Slide 7's box now reads 'shortest, pasted as an example'; the Korean script says the code is attached as an example and only its function usage is reused.
## 2026-10-20 01:17 UTC: how the hint pool is checked (writing session; user question): for the shortest-program hint (MAMO 79% = 79%) a program enters the pool if it runs without error and prints a value (poc/run_nlopt.py _verified_examples: status ok and a parsed value); no answers. For the most-similar-program library (FORM) the check is stricter: two runs both succeed and agree, the answer is not 'No Best Solution', and among a problem's programs the one whose answer most other models share is preferred. A running program can still be wrong (X6-VER2: 38% of passing programs wrong with the mined example). Slide 7's box now reads '✓ runs and prints a number'; Korean script says the same.
## 2026-10-20 01:18 UTC: Korean scripts of slides 6 and 7 rewritten (writing session; user): slide 6 follows the slide (what a free check is → the example check: sticks 3 4 5 → 0 → submit or think again → no example: two versions, think if they differ → results: contest 66% at 25k instead of 30k, geometry 99% at 4.3k instead of 5.9k, no answers needed); slide 7 follows the slide (the four steps and the icons → left: how the hint is made, programs on earlier problems of the type that run and print a number, the shortest pasted as an example, no human or answers; the one real problem, crash without, 20000 with, 0.6k vs 5.3k tokens → right: 74% usual vs 84% searched hint vs 87% hand-written hint, with fewer tokens).
## 2026-10-20 01:24 UTC: audit after the user's question on wrong hint programs (writing session; user: the shortest program can be wrong, as on slide 4; I kept asking you to check such things)
- Checked offline with the labels (only for this note): the pool (runs and prints a value) holds 17–38% wrong programs for the 8B–35B models (Qwen3.6 17%, Qwen3-14B-AWQ 24%, Qwen3-32B 25%, gpt-oss-20b 26%, Qwen3-8B 38%), 55% for Qwen3-4B; the chosen shortest program per benchmark was right for all five 8B+ models (NL4OPT and IndustryOR), wrong for Qwen3-4B and Qwen3-1.7B (whose pool has 2 programs). On extra page 25 and in slide 7's presenter note.
- Found a misattribution: slides 7 and 8 credited 87% to 'think only when a free check fails', but 87% is hint + check; the check alone (no hint) gives 77% @ 4.2k (U1 'uniform'). Slide 7 now shows 74% (think where answers differ) → 77% (think when the check fails) → 84% (+ searched hint) → 87% (+ hand-written hint); slide 8: 'only when a free check fails: 77%' and 'a short hint first: 87%; one picked with no human matches it'; Korean scripts updated.
## 2026-10-20 01:29 UTC: talk scripts rewritten along the flow review, slides unchanged (writing session; user: change only the scripts): slide 2 states the stakes (agents already write such code; errors go unnoticed; thinking is costly) and asks the audience to remember the two families; slide 3 shortened with a bridge; slide 4 explains the helper functions as an agent's tool list and speaks of 'a large model' instead of model names; Finding 1 is introduced as the solver-call family's story, Finding 2 as the algorithm family's; slide 7 answers slide 4's question in order (hint → check → think) and states the principle (spend effort on what went wrong, not on how hard a problem looks); slide 8 gives the plan as three concrete next steps measured by accuracy and tokens; slide 9 repeats the principle. ≈ 4:45 at a calm pace; presenter notes kept.
## 2026-10-20 01:37 UTC: which cheap fix — a label-free census predicts when a usage fact pays (WF, PREREG_HO.md). Count how many of the first, fact-free programs crash with a usage exception (AttributeError / ModuleNotFoundError / ImportError). Over 37 (benchmark, model, fact) points, gain +13.2 where ≥ 5% crash this way vs +0.9 where < 5% (r = 0.62). Prospective test on three new models (Qwen3-32B-AWQ, Qwen3-4B, Qwen3-1.7B) × OptiBench / OptMATH: the label-free library (6 cells) and the usage card (3 OptiBench cells) paid every time (+5 to +34); the example mined from NL4OPT failed on OptMATH again (+0 to +2), so 9 of 12 calls were right. The low-census side ("don't add a fact") is being tested now with gpt-oss-120b and Qwen3.6 (GPUs 0 / 1).

## 2026-10-20 01:39 UTC: talk script versions split into two files (writing session; user: make another PPT file that reflects the review, change only the scripts): Proposal_Team5.pptx is back to the script it had before the flow review; Proposal_Team5_v2.pptx has the same slides (checked part by part) with the rewritten script. In v2, slide 7 now says that 87% uses a hand-written hint and that the hint picked with no human was shown on word problems only, and slide 8 gives the plan as three questions, each with how we try it and how we measure it (accuracy and tokens). poc/make_slides.js writes both (SCRIPTS_KO.v1 / v2). v2 ≈ 4:50 at a calm pace.
## 2026-10-20 02:45 UTC: (1) the census rule's "no fact" side fails (WF2): Qwen3.6 makes few usage crashes on OptiBench (2.3%) yet gains +9 to +10 points from the usage card or library — it hides failures behind try / except ('No Best Solution') and picks the wrong variable type; so the census says where facts pay most, not where they do not. The label-free library helped the first program in 17 of 19 model × benchmark cells (hurt only gpt-oss on OptMATH): use it by default. (2) Self-consistency baselines (offline): majority voting over cheap programs is below the recipe everywhere; majority voting over three thinking runs is the most accurate on OptiBench, and thinking-only-on-failure with that vote as the fallback matches it at 24–33% of its tokens (gpt-oss-20b 74.6% @ 1.9k vs 75.0% @ 6.3k; Qwen3-8B 66.1% @ 7.5k vs 65.6% @ 22.9k).
## 2026-10-20 04:24 UTC: held-out geometry (HO-G, four tasks never used in a recipe test, 3 seeds): fact first, think only if the free check fails — gpt-oss-20b 99.0% @ 0.8k vs always thinking 93.1% @ 1.7k; Qwen3-14B-AWQ 84.4% @ 2.9k vs 76.7% @ 8.6k; but Qwen3-8B 59.7% @ 4.6k vs 74.0% @ 9.8k, because 64 of its 216 fact programs are consistently wrong and pass the metamorphic check. The recipe generalises to held-out geometry for the stronger 24 GB models; for the weakest the check leak decides. Hourly loop stopped (user, 2026-10-20 04:2x): the project moves to a Slurm server (docs/SLURM_HANDOFF.md).
## 2026-10-21 18:40 UTC: moved to the Slurm cluster; setup and smoke test (RTX 3090). Runs go through `poc/slurm/job.sh` (docker image nlp_project:261021 = the old environment: vLLM 0.22.0, torch 2.11 cu130, the client / sandbox venv; partition RTX3090, one GPU, 4 CPUs). External data now under `$POC_DATA` (OptMATH from STORM's repo, OptiBench from ReSocratic, MAMO from CardinalOperations/MAMO); Qwen3-14B-AWQ downloaded to the shared model pool. Smoke test (`poc/slurm/smoke.sh`, the first 10 OptiBench problems, solver-choice prompt, seed 1, one 3090 each): Qwen3-8B 2/10 @ 0.41k tokens, Qwen3-14B-AWQ 5/10 @ 0.35k, gpt-oss-20b (low) 3/10 @ 0.53k (old server, 605 × 3 seeds: 27.4%, 41.7%, 58.8% @ 0.49k). Raw programs read: the failures are the old kinds (invented cvxpy names `sum_entries` / `ones`, DCP violations, `import pywraplp`, CP-SAT and pywraplp type errors, pyomo not installed); no empty replies, all finished normally; the right ones are plain pywraplp / scipy models. The setup reproduces the old harness; 10 problems are too few to compare accuracy more finely. Next: HO-G-C (PREREG_HOGC.md), a brute-force view against the check leak of Qwen3-8B on held-out geometry; raw results of the old server are being copied (needed for its analysis).
## 2026-10-22 01:58 UTC: HO-G-C (PREREG_HOGC.md): a second program by the same model does not close Qwen3-8B's check leak on held-out geometry; most leaks are edge-case bugs the given input never shows. Each fact program (stored HO-G rows) was paired with a new brute-force program by the same model (no helpers, no hint; RTX 3090, 3 seeds) or with a second fact sample; accept only if they agree on the given instance and its rigid copies, else think. Qwen3-8B: brute-force agreement 64.2% @ 6.6k, resample agreement 65.6% @ 6.5k, vs always thinking 74.0% @ 9.8k and plain FF 59.7% @ 4.6k (decision (c): the limit stays). For gpt-oss-20b and Qwen3-14B-AWQ the second program only costs (FF 99.0% @ 0.8k / 84.4% @ 2.9k stays best; strict agreement 96.2% / 77.1%), because their brute-force programs are often wrong (clip, tri) and flag correct programs. Raw: 37 of Qwen3-8B's 64 leaked programs answer the given instance correctly and fail only the degenerate copy — convex crashes when the first vertex triple is collinear, tri uses the textbook `not (has_neg and has_pos)` test that counts points on an edge as inside, and the brute force copies that snippet; the brute force does flag 19 of the 27 programs wrong on the given instance (70%). So the leak is mainly edge cases the statement names but the input does not contain; a check would have to exercise them. PROPOSAL finding 6 and §7 updated (both languages). Setup notes: the old raw results (2.0 GB) are now on the Slurm side (copied from the shared NAS through the old-server host); the census table of WF / WF2 reproduces exactly (46 points, r = 0.62).
## 2026-10-22 02:16 UTC: HO-G-E (PREREG_HOGC.md addendum): edge-case tests written by the model once per task (from the statement, 10–50 tokens per problem) do see Qwen3-8B's leaked programs (59 of 64 flagged) but are wrong on the same boundary cases, so they also flag 67% of its correct programs; the gate then escalates almost everything (72.9% @ 9.1k vs always thinking 74.0% @ 9.8k; decision (c)). For gpt-oss-20b and Qwen3-14B-AWQ they only cost (97.6% @ 1.5k / 76.7% @ 6.7k vs FF 99.0% @ 0.8k / 84.4% @ 2.9k). Raw tests: every tri test set of every model has a wrong expected count (e.g. gpt-oss-20b counts (2, 3) as inside the triangle (0,0) (5,0) (0,5) though it is on the edge x + y = 5); tests also break the stated input format (fractional coordinates, degenerate triangles). With HO-G-C: for the weakest model no self-written check (brute force, second sample, edge-case tests) rescues fact-first on held-out geometry — the checks that see edge-case bugs get the edge cases wrong themselves. PROPOSAL finding 6 sentence extended (both languages).
## 2026-10-22 03:25 UTC: WF3 (PREREG_HO.md): on two more unseen benchmarks (BWOR, 82 textbook OR problems; LogiOR, 92 logistics problems; 3 models × 3 seeds, RTX 3090) the label-free library of checked programs raises the first program in all six cells (+5.7 to +14.9 points) and the hand-written usage card in four (+7.7 to +13.0; not for Qwen3-8B: +0.0 / +0.7). The pre-registered rule (add a fact unless usage crashes < 5% and non-usage failures ≥ 25%, calls recorded before any gain was read) called "add" everywhere and was right in 10 of 12 points; its "do not add" side stays untested because every new cell had ≥ 5% usage crashes. Raw: with the card Qwen3-8B still crashes on usage (LogiOR 22 → 32%), mostly `from ortools.constraint_solver import pywraplp` — it reaches for the routing library the card does not cover and attaches pywraplp to it; the library of similar problems' working programs has no such gap. Library tally: 23 of 25 model × benchmark cells (PROPOSAL finding 6, both languages). Thinking arms for the HO2 policy comparison still running.
## 2026-10-22 05:25 UTC: HO2 (PREREG_HO.md): on two more unseen optimization benchmarks (BWOR 82, LogiOR 92; 3 models × 3 seeds, RTX 3090) "think only when the cheap program visibly fails" ties always thinking for gpt-oss-20b and Qwen3-14B-AWQ (−2.2 to +1.2 points, every 95% CI includes 0) at 53–88% of its tokens, and loses for Qwen3-8B (BWOR −8.1 [−13.4, −3.3]; LogiOR −2.9) — HO2-P1 refuted (2 of 6 cells). Cause, read from the rows: the cheap programs are right on only 7–42% of these problems and 38–75% of those that run and print a number are wrong, so the free check leaks; Qwen3-8B's thinking gains 25–28 points over its cheap program despite 19–24% of its runs stopping at the 16k cap. Requiring two cheap programs to agree recovers always-thinking's accuracy everywhere (with the library +0.8 to +8.7) but at 91–120% of its tokens. The label-free library again pays (HO2-P2 holds, 5 of 6; Qwen3-14B-AWQ on LogiOR +10.1 [+4.3, +15.9] over always thinking at 74% of its tokens). Reading: the saving of the recipe on hard unseen problems is bounded by its check's leak; the project's "check is the bottleneck" thesis, now on held-out data. Every comparison now reports a paired bootstrap CI (analyze_ho.py).
## 2026-10-22 05:35 UTC: review check — why Qwen3-14B-AWQ thinks worse than Qwen3-8B on OptiBench (48.3% vs 57.9%; the source of the recipe's largest held-out margin, +11): not a harness artifact. Its thinking programs crash on library usage in 28.3% of runs (Qwen3-8B 8.4%, gpt-oss-20b 2.6%): invented `solver.status` (157), `import pywraplp` (126), `CpSolver.Objective` (80), `solver.Response` (59); running-but-wrong shares are similar (14.5% vs 17.8%), cap hits rare (15 / 1,815). Thinking does not supply an API fact the model lacks (finding 1), so for this model the cheap program plus a fact beats thinking. Cap hits do handicap always-thinking elsewhere — Qwen3-8B stops at 16k on 12% of OptMATH and 19–24% of BWOR / LogiOR thinking runs (counted wrong) — but those are the cells where always thinking already wins or ties, so a larger budget would only widen its lead there.
## 2026-10-22 06:2x UTC: input tokens of the held-out policies (review item; poc/analyze_input_tokens.py, results/x3/input_tokens_analysis.log; prompts rebuilt exactly, counted with each model's tokenizer, chat-template tokens excluded). Prompts are 0.3–1.3k tokens; the label-free library adds 0.3–0.7k per cheap call. Fact-first-then-think vs always thinking, all 24 held-out (benchmark, model, cheap arm) cells: 28–91% of the output tokens, 37–97% of input + output tokens — the saving shrinks most for the library (OptiBench gpt-oss-20b 46% → 67%; OptMATH gpt-oss-20b 73% → 94%) but never reverses. Input tokens are cheaper and cacheable (prefill), so output stays the main axis; both are now reported. PROPOSAL §8 'Fair comparisons' updated (both languages).
## 2026-10-22 06:4x UTC: held-out geometry with intervals (cached checks, bootstrap over the 96 items): fact-first-then-think minus always thinking gpt-oss-20b +5.9 [+3.5, +8.7], Qwen3-14B-AWQ +7.6 [+4.5, +11.5], Qwen3-8B −14.2 [−19.8, −9.4], at 34–48% of its output tokens. Draft outline of the final report with the full held-out table (5 benchmarks × 3 models, CIs, output and input tokens): docs/notes/REPORT_OUTLINE.md; handoff §3 updated (steps 1–2 done, write-up open; format asked of the user).
## 2026-10-22 18:5x UTC: final-report draft written (docs/REPORT.md, English): abstract, recipe, setup, development findings, U1 result, held-out table with intervals and token shares, the check-leak analysis (HOG-C / HOG-E / HO2), the label-free library and the fact rule, same-harness baselines, where the recipe stops, limitations. Numbers taken from the logs and pre-registrations cited at its end; format and length to be fitted to the course's requirements.
## 2026-10-22 18:5x UTC: HO-G-M (PREREG_HOGC.md addendum): metamorphic relations the model writes once per task from the statement (no expected answers) target the right failures — they flag 23 of Qwen3-8B's 37 edge-case-only leaks — but are often wrong themselves (malformed transforms, wrong expectations; correct programs break gpt-oss-20b's tri relations 144 / 144), so false alarms are 54% for Qwen3-8B: 67.7% @ 7.2k vs always thinking 74.0% @ 9.8k (best of the four self-written checks; decision (c)). Perfect-check bounds (labels only for the bound): on held-out geometry a perfect check lifts Qwen3-8B only to 75.0% @ 70% of thinking's tokens (the pre-registered ≤ 60% was unreachable by any check: its fact programs are wrong too often), gpt-oss-20b 99.0% @ 49%, Qwen3-14B-AWQ 84.4% @ 38%; on BWOR / LogiOR a perfect check saves no tokens (83–103% of always thinking's) but raises accuracy above it (e.g. gpt-oss-20b BWOR 69.5% vs 59.3%). Reading — a cost model for the recipe: its token saving is capped by how often the cheap program is right; the check's leak decides how much of the accuracy it keeps. HO3's token prediction is infeasible by this bound (recorded before its results).
## 2026-10-22 19:0x UTC: HO3 (PREREG_HO.md): a solution checker written from the problem text (the cheap program prints its solution; the same model writes a program that tests every stated constraint on it and recomputes the objective; think unless it passes) on BWOR / LogiOR, 3 models × 3 seeds. It catches 66–97% of the running-but-wrong programs but also flags 18–65% of right ones (it misreads the text: inverted comparisons, invented constraints). Result: the recipe goes from a tie to a significant accuracy gain over always thinking for gpt-oss-20b (BWOR +3.7 [+0.8, +6.9], LogiOR +4.3 [+0.4, +8.3]) and Qwen3-14B-AWQ on BWOR (+3.3 [+0.4, +6.1]); Qwen3-8B from −6.9 to −2.0 (BWOR) and to a tie (LogiOR) — at 102–110% of always thinking's tokens (no check can save tokens here: the cheap programs are right too rarely; bound recorded before the results). As accurate as two agreeing programs at 5–13 points fewer tokens. Reading: on hard problems a better free check buys accuracy, not tokens.
## 2026-10-22 19:3x UTC: HO3-C (PREREG_HO.md): think only if the solution checker objects AND a second cheap program disagrees — halves the checker's false alarms on right programs (gpt-oss-20b 50 → 23, Qwen3-8B 25 → 11, Qwen3-14B-AWQ 38 → 21) while keeping 82–93% of its catches; ≥ checker-alone accuracy at fewer tokens in 4 of 6 BWOR / LogiOR cells (best: Qwen3-14B-AWQ BWOR 36.2% @ 98% of always thinking's tokens vs 30.1%). Two independent views object to different errors. HO4 (the checker on OptiBench with the library, where savings are possible) running: 9 jobs.
## 2026-10-22 19:4x UTC: HO4 (PREREG_HO.md): on OptiBench with the label-free library — where cheap programs are usually right — the solution checker does not pay: the plain recipe already beats always thinking by +5.0 / +15.0 / +7.2 points (gpt-oss-20b / Qwen3-14B-AWQ / Qwen3-8B, all CIs above 0) at 36–55% of its tokens; adding the checker changes accuracy by +0.5 / −0.9 / −1.8 at 65–86% of the tokens (its false alarms, 7–36% of right programs, and the thinking they trigger cost what its catches gain). HO4-P1 / P2 refuted. Together with HO3: a stronger check is worth it where cheap programs are usually wrong (BWOR / LogiOR) and not where they are usually right — consistent with the perfect-check cost model. Next: a label-free rule for which regime a benchmark is in.
## 2026-10-22 19:5x UTC: HO5 (PREREG_HO.md): the label-free regime rule (two cheap programs agree < 85% → add the solution checker), fixed from the BWOR / LogiOR / OptiBench cells, called "add" on OptMATH for all three models before any accuracy was read — and was wrong: the checker lowers accuracy there by 1.4–2.3 points (gpt-oss-20b 36.3% → 34.0%) at 112–114% of always thinking's tokens. Raw: OptMATH solutions carry auxiliary formulation variables (routing order, linearizations) that the checker must re-interpret, and it misjudges correct tours; checking needs the same formulation knowledge as writing. So the checker helps only where constraints are stated directly on the decision variables (textbook-style BWOR / LogiOR); low agreement is necessary, not sufficient. Default stays the plain recipe with the label-free library.
## 2026-10-22 20:1x UTC: HO6 (PREREG_HO.md): one cheap repair turn with the failure evidence (Python's error, the checker's violated constraint, or 'No Best Solution'), before thinking, on BWOR / LogiOR. For gpt-oss-20b and Qwen3-14B-AWQ it beats always thinking by +4.3 to +7.3 points at 70–90% of its tokens (BWOR gpt-oss-20b +5.7 [+1.2, +11.0] @ 82%; Qwen3-14B-AWQ +7.3 [+0.8, +13.8] @ 70%) and dominates the checker-alone policy; 40–58% of escalated programs come back running, 41–57% of those right. For Qwen3-8B it hurts (−7.3 / −5.8): its repaired programs are accepted on the free check alone and mostly wrong. Pre-registered token bound (≤ 75%) met in 1 of 4 stronger-model cells, so not adopted from this test; the repair-before-thinking step gets its own pre-registered test next.
## 2026-10-22 20:5x UTC: HO7 (PREREG_HO.md): one cheap repair turn on a visible failure (crash, no value, 'No Best Solution'), no checker, before thinking — OptiBench with the library and OptMATH, 3 models × 3 seeds. Never worse than the plain recipe and more accurate in all 6 cells (+0.7 to +4.0 points; vs always thinking: Qwen3-14B-AWQ OptMATH +8.7 [+4.3, +13.0], Qwen3-8B OptMATH +3.0 [+0.3, +6.0]) at 84–101% of the plain recipe's tokens: where a repair runs it is right more often than thinking on the same items (6 / 6), but only 10–41% of repairs run, so the token saving is small (pre-registered ≤ 75% refuted). Unlike HO6, Qwen3-8B does not get worse: repair visible failures, not running programs a checker flagged.
## 2026-10-22 21:0x UTC (exploratory, not pre-registered; offline on the HO6 rows): the HO7 policy (repair visible failures only, no checker) on BWOR / LogiOR. Stronger models gain over the plain recipe at fewer tokens (gpt-oss-20b BWOR −2.0 → −0.4, LogiOR +1.4 → +3.6; Qwen3-14B-AWQ +2.4 → +3.7, +1.1 → +4.3 points vs always thinking, at 54–72% of its tokens); Qwen3-8B loses (BWOR −6.9 → −8.9, LogiOR −3.3 → −6.9): its repaired programs run but are mostly wrong on these hard problems, while on OptiBench / OptMATH they helped it (HO7). So repair-before-thinking is a reliable gain for gpt-oss-20b and Qwen3-14B-AWQ on all four word-problem benchmarks, and for Qwen3-8B only where its repairs are usually right.
## 2026-10-22 22:0x UTC: HO-G-R (PREREG_HOGC.md addendum): one cheap repair on a visible failure before thinking, on held-out geometry — only 13–20% of the Qwen repairs pass the free check (evidence "these copies disagree" is less actionable than a Python error or a named violated constraint); Qwen3-14B-AWQ gains +1.7 (84.4 → 86.1%, +9.4 [+5.6, +13.9] over always thinking at 90% of FF's tokens), gpt-oss-20b +0.7, Qwen3-8B −1.0 (its passing repairs are mostly wrong). P1 / P2 refuted: repair stays a word-problem step; Qwen3-8B's geometry limit stands.
## 2026-10-22 23:0x UTC: HO-X (PREREG_HOGC.md addendum; offline on stored rows): a check from a different model — accept Qwen's fact program only if gpt-oss-20b's program agrees. On held-out geometry it catches 26 of Qwen3-8B's 64 leaks: all but one of those wrong on the given input, none of the 37 wrong only on edge cases (63.2% vs THINK 74.0%; P1 / P2 refuted). On BWOR / LogiOR it beats each Qwen model's own solution checker by +1.4 to +3.3 points with half the false alarms (P3 holds). But simply using gpt-oss-20b beats every such policy by 16–36 points at a fraction of the tokens. So Qwen3-8B's geometry limit is mostly edge-case errors that no check on the given input can see, and a stronger second model is a reason to switch models, not a check.
## 2026-10-22 23:0x UTC: HO-D gate (PREREG_HOGC.md; offline): best case of a differential test on edge inputs for Qwen3-8B's geometry leak, using the benchmark's own edge inputs as a stand-in for a perfect generator (inputs only, no labels). Agreement with a second sample of its own on those inputs catches 32 of the 37 edge-case-only leaks — the first check that sees them — but reaches only 71.9% at 78% of always thinking's tokens (both second programs: 73.3% at 94%; THINK 74.0%). The pre-registered gate fails, so no generator run: even perfect edge inputs cannot make the recipe pay for Qwen3-8B here. Its geometry limit is final and reported as 27 on-input leaks (removable by a different model's program) + 37 edge-only leaks (visible only to edge inputs, and too costly to remove).
## 2026-10-22 23:1x UTC: HO-B (PREREG_HO.md addendum; offline): is always thinking handicapped by its 16k-token budget? 0.3–7.6% of the stronger models' thinking rows hit it. Worst case — every capped wrong row counted as right, in always thinking and wherever the recipe escalates to it: no tie or win of gpt-oss-20b or Qwen3-14B-AWQ becomes a significant loss (closest: gpt-oss-20b LogiOR −4.3 [−10.1, +0.7]); gpt-oss-20b's OptMATH win (+5.7) becomes a tie (+2.7 [−3.0, +8.7]); Qwen3-8B's losses deepen. P1 holds, so no longer-budget run; the bound goes into the report's limitations.
## 2026-10-22 23:1x UTC: HO-P (PREREG_MODEL.md addendum; offline): the 30-label pilot on the 45 held-out cells (3 models × 3 seeds × OptMATH, OptiBench, BWOR, LogiOR, geometry, each with the recipe's fact). Labelling 30 random problems of a cell and running the four policies on them (cheap program only, fact first, fact first with two agreeing programs, always think) picks a policy within 0.87 points of the cell's best (accuracy − 0.5 × ktokens; k = 10: 2.81); in Qwen3-8B's losing cells (geometry, BWOR) it picks thinking and loses 0.74 points where always using the recipe loses 7.83. Fact-first stays the best single default (regret 1.80). All three predictions hold: the recipe's held-out losses are detectable with 30 labels.
## 2026-10-23 00:1x UTC: HO-L (PREREG_MODEL.md addendum; offline): can the 30-label pilot work without labels? Estimating the cheap program's and thinking's accuracy from how often three runs agree (cheap program, a second cheap sample, thinking; triplet method) and choosing fact-first vs always-thinking from that: mean regret 1.71 over the 45 held-out cells, against 0.57 for the labelled pilot and 1.41 for always fact-first (P1 refuted). It keeps fact-first in Qwen3-8B's losing cells (geometry 97% of pilots, BWOR 93%), because the cheap program and its resample share their errors and so vouch for each other — the self-correlation that makes the check leak also blinds an agreement-based pilot. Labels stay: 30 per new cell.
## 2026-10-23 02:5x UTC: HO-N P3 (PREREG_HON.md): on a model the project never used (Qwen3.5-9B), the label-free census of its first programs says "add a fact" on all four held-out word-problem benchmarks (19–32% of programs crash on library usage: gurobipy imports, invented solver attributes), recorded before any gain was read; the usage card and the label-free library each raise the first program by +3.7 to +19.7 points (OptiBench +19.1 / +19.7, OptMATH +8.3 / +13.0). 8 / 8 calls right; with WF3 18 / 20 prospective calls right, all on the "add" side. Thinking arms still running.
## 2026-10-23 07:3x UTC: HO-N (PREREG_HON.md): the recipe on a model it was never developed with — Qwen3.5-9B (bf16, one RTX 3090; thinking with the model card's sampling and a 32k budget). Fact first, think on a visible failure beats always thinking on all five held-out benchmarks: OptiBench 68.3% vs 44.7% (+23.5 [+20.8, +26.3]) at 30% of its tokens, BWOR +11.0, LogiOR +11.6, OptMATH +14.3, geometry +3.8 [+0.3, +6.9] at 28%; even counting every budget-capped wrong thinking run as right it ties or beats everywhere. The 30-label pilot keeps regret at 0.81 (P2 holds), the census's "add" calls were right 8 / 8 (P3, "add" side only). Thinking fails this model by library misuse (14–25% of its programs) and long unfinished reasoning (6–32% at 32k): the missing fact, not effort, is the bottleneck. All three predictions hold.
## 2026-10-23 08:1x UTC: HO-N3 (PREREG_HON.md): one cheap repair turn on a visible failure before thinking, on the unseen Qwen3.5-9B — more accurate than the plain recipe in 4 / 4 word benchmarks (OptiBench +2.2 [+1.4, +3.0], BWOR +2.0, LogiOR +6.2 [+2.2, +9.8], OptMATH +6.0 [+3.0, +9.3]) at 73–88% of its tokens (P1 holds; P2's ≤ 85% met in 2 / 4). Where a repair runs it is right in 182 of 277 cases, thinking on the same problems in 102. With HO7 (6 / 6 cells on the development models) the repair step becomes the recipe's first escalation on word problems; geometry keeps thinking directly (HO-G-R).
## 2026-10-23 08:5x UTC: HO-R (PREREG_HON.md): repair-first on every held-out word cell (1,284 new repairs for the three development models on BWOR / LogiOR / OptMATH) and as a fifth pilot policy over all 60 held-out cells. Always repairing first loses 1.22 utility points to each cell's best policy, against 2.85 for the plain recipe (development models alone 1.62 vs 2.10), so it becomes the default on word problems; but it costs accuracy on BWOR for all three development models (−0.8 to −3.6) and on LogiOR for Qwen3-8B (R-P1 refuted, 5 / 9 cells). The 30-label pilot over five policies keeps regret at 0.94 (≤ 1.0).
## 2026-10-23 13:5x UTC: HO-TF (PREREG_HO.md addendum): the fair baseline — always thinking *with the same library fact* — changes the held-out claim. The library raises thinking too (+8.5 to +22.6 points for the Qwen models: Qwen3-14B-AWQ OptiBench 44.1% → 66.7%), so against it fact-first-then-think ties or wins only for gpt-oss-20b (OptiBench +2.5 [+0.5, +4.8], BWOR / LogiOR ties at 46–63% of the tokens) and loses for the Qwen models on OptiBench (−4.3, −4.5) and BWOR (−12.2, −11.0) and for Qwen3-8B on LogiOR (−7.6), at 33–82% of the tokens. TF-P2 refuted (2 / 6). On held-out geometry (fact = the hint) it still wins or ties for gpt-oss-20b (+3.1) and Qwen3-14B-AWQ (+2.4). The earlier library rows compared the recipe with the fact against thinking without it; they are restated: the fact is the main lever, and thinking only on failure is a saving for gpt-oss-20b and on geometry, a token-for-accuracy trade for the Qwen models on word problems.
## 2026-10-23 19:0x UTC: HO-TF2 + HO-P2 (PREREG_HO.md, PREREG_MODEL.md): the held-out claim rebuilt against thinking given the same fact. Fact-first-then-think ties or wins on all five benchmarks for gpt-oss-20b and the unseen Qwen3.5-9B (e.g. Qwen3.5-9B OptiBench +4.0 [+1.0, +6.9] at 30% of the tokens, LogiOR +7.6; geometry ties / wins at 30–59%), and for Qwen3-14B-AWQ on geometry, LogiOR and OptMATH; it loses for Qwen3-14B-AWQ on OptiBench (−4.3) / BWOR (−12.2) and for Qwen3-8B on four of five. The fact helps thinking too (+3.5 to +22.6). No fixed policy is good everywhere any more (best fixed regret 3.32), but the 30-label pilot over five policies keeps it at 0.85 and picks thinking-with-the-fact in the 17 cells where it is best. All TF2 and P2 predictions hold.
## 2026-10-23 20:1x UTC (offline, analyze_hotf.py decomposition): why fact-first loses where it does, against the fact-matched thinking arm. FF − THINK+F = P(pass) × [P(cheap right | pass) − P(THINK+F right | pass)], and the bracket decides every cell: wins / ties where the passing cheap programs are about as often right as thinking with the fact would be on them (gpt-oss-20b OptiBench 80% vs 77%, Qwen3.5-9B LogiOR 74% vs 52%, geometry 95–100% vs 94–96% for the three stronger models); losses where thinking with the fact solves far more of them (Qwen3-14B-AWQ BWOR 42% vs 64%, Qwen3-8B BWOR 31% vs 55%, Qwen3-8B geometry 67% vs 92%). The leak alone does not decide: 62% of Qwen3.5-9B's passing OptMATH programs are wrong, yet thinking with the fact is no better on them (34%). Report §5.2 opens with this.
## 2026-10-23 21:1x UTC: PF (PREREG_PROOF.md addendum; offline on the stored miniF2F attempts) — the recipe where the check is perfect (Lean compiles ⇒ right). Up to 16k tokens per statement the best policy is always more cheap (non-thinking) attempts; thinking adds statements only after 8 cheap attempts (gpt-oss-20b 66 → 77 of 244, Qwen3.6 133 → 140) and then beats always thinking at its own budget by +4 / +10 statements. One cheap try before thinking saves nothing (97–101% of always thinking's tokens). With a sound check the escalation rule is "sample cheaply until it stops paying, then think" — first result of the proof direction.
## 2026-10-23 21:3x UTC: WF4 (PREREG_HO.md): gpt-oss-120b on 4 × RTX 3090 (tensor parallel) — the first new cells with < 5% usage crashes (BWOR 2.0%, LogiOR 1.1%); the census rule said "add" (few failures of any kind). The usage card helps on BWOR (+6.5 [+0.8, +12.6]) and LogiOR (+2.5, n.s.), the label-free library +3.3 (n.s.) and −3.3 (n.s.): 3 / 4 calls right (21 / 24 overall). For a model that rarely misuses the libraries a fact is a small, uncertain gain; the census predicts big gains (usage crashes ≥ 5%) but not small ones.
## 2026-10-23 22:5x UTC: HO-VF + HO-LG (PREREG_HO.md). (1) Where fact-first loses for the Qwen3 models, the solution checker written from the text (accept the library program only if its printed solution passes) closes the gap to thinking with the fact in all 5 cells (−4 to −12 → −1.6 to +1.0), but saves tokens only on OptiBench (71–79%; on BWOR / LogiOR it escalates almost everything, 101–111%). (2) gpt-oss-120b on 4 × RTX 3090: fact-first ties thinking with the fact on OptiBench, BWOR, LogiOR at 50–63% of its tokens. The rebuilt claim now covers 8B to 120B: a pure saving where the cheap program with the fact is about as good as thinking with it (gpt-oss-20b / -120b, Qwen3.5-9B; the Qwen3 models on OptiBench with the checker), thinking with the fact where it is not (the Qwen3 models on BWOR / LogiOR).
## 2026-10-24 01:3x UTC: DT (PREREG_DT.md, direction 2): label-free fine-tuning. Qwen3-8B LoRA-tuned for 36 minutes on 2 × RTX 3090 on 1,127 programs from the development sets that pass the strict check (no label anywhere) writes, with no fact in the prompt, programs as good as the base model given the label-free library: OptiBench 54.2% vs 51.6% (base without a fact 27.4%), BWOR 18.3 vs 15.4, LogiOR 16.7 vs 15.6 — ties within their intervals — but not on OptMATH (8.3 vs 14.3), whose problem types the development data lacks. Usage crashes drop to 0.7–4.1% on OptiBench / BWOR (not LogiOR / OptMATH), and the leak does not rise (it falls on OptiBench 39 → 30%). The fact can be moved into the weights with the recipe's own checked programs.
## 2026-10-24 02:0x UTC: HO-TB (PREREG_HO.md): thinking with the fact under a budget (Qwen3 budget forcing). At 2k tokens it keeps all but 2–4 points on OptiBench at 36–41% of the tokens but loses 11–17 on BWOR / LogiOR; at 6k Qwen3-14B-AWQ keeps all but 2–2.5 points at 68% of the tokens on BWOR / LogiOR, Qwen3-8B still loses 6–10. Fact-first escalating to a budgeted think stays 4–15 points below full thinking with the fact. TB-P1 / P3 refuted, P2 holds: budget is a trade, and the Qwen3 models' fact-first loss is the leaky check, not the escalation's cost.
## 2026-10-24 03:4x UTC: DT-14 + DT2-P1 (PREREG_DT.md). Label-free fine-tuning on Qwen3-14B (4 × RTX 3090, 53 min): with no fact it reaches the base model *with* the library on all of OptiBench (58.0% vs 58.1%; base without a fact 36.3%) and beats it on BWOR (+3.3, n.s.), but not on LogiOR (−5.4) / OptMATH (−4.7); usage crashes fall from 16–28% to 2–7%. For the fine-tuned Qwen3-8B the library no longer adds much (OptiBench +3.8, BWOR −1.2, LogiOR −5.8). Fine-tuning on the recipe's own checked programs internalizes the usage fact; similar-problem programs still help where the training data has no such problems.
## 2026-10-24 04:0x UTC: PL1 (PREREG_PROOF.md, proof direction): with the Lean compiler as a perfect check, 32 cheap attempts per miniF2F statement solve 74 (gpt-oss-20b) and 83 (gpt-oss-120b on 4 × RTX 3090) of 244 — more than 8 thinking attempts (72, 81) — and thinking after them adds statements cheap sampling never reaches (80, 91). Up to the budget of always thinking, the best policy is mostly cheap attempts (gpt-oss-20b: cheap-only up to 32k tokens per statement; gpt-oss-120b, whose thinking is cheaper, with 1–2 thinking attempts). For proofs the recipe becomes "sample cheaply until it stops paying, then think".
## 2026-10-24 04:1x UTC: PL2 (PREREG_PROOF.md): on miniF2F, 30 labelled statements pick the budget split (cheap attempts, then thinking attempts) within 0.55 / 0.90 utility points of the best fixed split for gpt-oss-20b / -120b (λ = 0.5); the best splits are short (6 cheap; 4 cheap + 1 thinking), so with tokens priced the token penalty decides how far to sample. The 30-label pilot transfers from word problems to proofs.
## 2026-10-24 06:1x UTC: DT2 (PREREG_DT.md): the fine-tuned Qwen3-8B inside the recipe. The library no longer adds on top of fine-tuning (+3.8 / −1.2 / −5.8), the fine-tuned model's thinking with the fact is within its intervals of the base's (−3.3 / +3.7 / −4.0), and fact-first with it still loses to base thinking with the fact on OptiBench / BWOR / LogiOR (−5.1 / −10.2 / −14.5): all three predictions refuted. Fine-tuning fixes the fact, not the check.
## 2026-10-24 09:0x UTC: DT3 (PREREG_DT.md): a label-free self-training round on 3,996 unlabeled OR problems (OptMATH-Train, OR-Instruct; decontaminated) does not help: the round-1 fine-tuned Qwen3-8B solved 1,957 twice in agreement, retraining on them plus the development data leaves OptiBench unchanged (54.2%) and lowers BWOR / LogiOR / OptMATH by 2–3 points, with the leak rising from 69 → 76% (BWOR) and 72 → 82% (OptMATH). All three predictions refuted; the risk DT-P3 named appeared in round 2: agreement of one model's own runs on unfamiliar hard problems passes consistent wrong formulations. The check's leak bounds self-training as it bounds the recipe.
## 2026-10-24 12:1x UTC: DT4 (PREREG_DT.md): filtering the self-training data by agreement with a different model (gpt-oss-20b; 1,348 of 3,996 problems pass) removes the harm DT3 showed (BWOR 15.0 → 20.7%, +5.7 [+2.8, +8.9]; leaks back to round-1 levels) but gains nothing over round 1 (OptiBench −0.4, BWOR +2.4, LogiOR 0.0, OptMATH −0.7). With a label-free check, self-training on unfamiliar problem types either learns the check's mistakes (same-model filter) or only what the model already knew (cross-model filter): direction 2 ends at the first round's internalized usage fact.
## 2026-10-24 12:3x UTC: PL3 (PREREG_PROOF.md): Qwen3-8B on miniF2F — 32 cheap attempts 23.0 statements, 8 thinking attempts 20.0, both 29.0; cheap-only is the best policy up to 16k tokens per statement. All three predictions hold; the "sample cheaply, then think" frontier holds for gpt-oss-20b, gpt-oss-120b and Qwen3-8B.
## 2026-10-24 14:0x UTC: HO-VR (PREREG_HO.md): a 2k-token thinking-mode self-review of the cheap program as the escalation gate. For Qwen3-14B-AWQ and Qwen3-8B, where fact-first lost 4–12 points to thinking with the fact, accepting the program only when the review says CORRECT ties or beats thinking with the fact in all 6 cells (−1.1 to +2.9), at 70–73% of its tokens on OptiBench and ~100% on BWOR / LogiOR — where even a perfect check saves at most 12% (the cheap program is right too rarely). The review flags 65% of wrong passing programs with 13% false alarms (the solution checker: 18–65%). P1's ≤ 75% token target refuted on the hard benchmarks, but it was unreachable there; P2 holds. The recipe's Qwen3 trade becomes a saving where saving is possible and a tie elsewhere.
## 2026-10-24 14:3x UTC: HO-VR2 (PREREG_HO.md): the 2k-token self-review gate on OptMATH and held-out geometry. It ties or beats thinking with the fact for Qwen3-14B-AWQ (OptMATH +1.0, geometry +3.5 [+1.0, +6.2]) and Qwen3-8B on OptMATH (+2.7 [+0.3, +5.3]); on Qwen3-8B geometry — the cell every earlier check failed — it cuts the loss from −16.7 to −6.6 by catching 20 of the 37 edge-case-only leaks from the statement (and 24 / 27 on-input ones), at 31% false alarms. With HO-VR: the gate makes fact-first tie or beat thinking with the fact in 7 of 8 Qwen3 cells.
## 2026-10-24 18:0x UTC: HO-VR3 (PREREG_HO.md): the self-review gate on Qwen3.5-9B, where fact-first already wins. It keeps or slightly changes accuracy (+1.1, +3.2, −3.3 vs fact-first) but adds 18–37% of always-thinking's tokens, because false alarms and reviews that end without a verdict (10–33%, even with a 2k answer cap) send problems to its 32k-token think. Both predictions refuted: the gate is a pilot option for models whose free check leaks (Qwen3: it removes the loss), not a default step. An earlier run with a 512-token answer cap was discarded as a harness error (70% no verdict).

## 2026-10-24 21:05 UTC: DT5 (PREREG_DT.md): a better label-free filter does not make self-training learn
Qwen3-8B round 1 (fine-tuned on 1,127 checked development programs) wrote programs for 3,996 unlabeled OR problems; base Qwen3-8B, in
thinking mode cut at 2,000 tokens, reviewed every runnable one (3,106; accept 1,935). Problems where round 1's two runs agree and the
review says CORRECT (1,452) were added to the development data and Qwen3-8B was retrained from base (2,579 examples, 324 steps, 2 h on
RTX 3090). Held-out, no fact, 3 seeds, vs round 1: OptiBench 53.6% (−0.7 [−2.1, +0.7]), BWOR 20.7% (+2.4 [−0.8, +6.1]), LogiOR 14.9%
(−1.8 [−5.8, +2.2]; leak 61 → 67%), OptMATH 8.7% (+0.3 [−3.0, +3.7]); output tokens +0–33%. DT5-P2 (≥ +3 on OptMATH or LogiOR) refuted;
P1 half (fewer kept, but the LogiOR leak rises 6 points). With self-consistency (DT3), cross-model agreement (DT4) and agreement plus
review (DT5), label-free self-training goes from harmful to neutral, never useful: it stays bounded by what the model already solves.
Raw LogiOR losses are ordinary formulation slips (undefined data table, a capacity used only as a variable bound).

## 2026-10-24 21:10 UTC: HO-P3 (PREREG_MODEL.md): the self-review gate is the best fixed policy for leaky models, not a pilot addition
Offline, on the 39 held-out cells with review rows (Qwen3-14B-AWQ and Qwen3-8B on five benchmarks, Qwen3.5-9B on three; 3 seeds), the
self-review gate (a passing program is the answer only if a 2k-token thinking-mode review says CORRECT, else thinking with the fact) was
added to HO-P2's 30-label pilot as a sixth policy (λ = 0.5 utility = accuracy − 0.5 × k-tokens). Always using the gate loses 2.52 points
to the best policy per cell, against 3.99 for always thinking with the fact and 5.17 for repair-first: with no labels it is the best
fixed policy there. The six-policy pilot keeps regret at 0.96 (P3-1 holds) but beats the five-policy pilot by only +0.28 (pre-registered
bar +0.5: P3-2 refuted; gate best in 9 of 39 cells), because the five-policy pilot already found a near-equal policy in the gate's cells
and a sixth option adds pick noise. Decision as registered: the gate is the no-label default for a leaky model, outside the pilot.

## 2026-10-24 23:25 UTC: HO-N4 cheap arms (PREREG_HON.md): on a new model family the fact pays on OptiBench only
NVIDIA-Nemotron-3-Nano-30B-A3B (hybrid Mamba-Transformer mixture of experts, never used before; 4 × RTX 3090, tensor parallel), cheap
non-thinking programs, 3 seeds. The label-free library raises the first program by +16.3 [+13.1, +19.3] on OptiBench (36.2 → 52.5%) and
+3.7 [−1.3, +8.7] on OptMATH, but not on BWOR (−1.6) or LogiOR (−2.2); the usage card adds +6.1 on OptiBench and hurts LogiOR (−6.9
[−13.0, −0.7]). N4-P1 (library ≥ +2 on 3 of 4) and N4-P2 (census calls, all "add", right on ≥ 6 of 8: 3 / 8) refuted. Raw: with the card
the model writes `pywraplp` in 97–99% of programs and mixes CP-SAT idioms into it (AttributeErrors 18 → 40 on BWOR); the failures that
decide BWOR / LogiOR are formulations, which neither fact fixes. Thinking with the library, the gate and the pilot (N4-P3–P5) are running.

## 2026-10-25 00:03 UTC: WF5 (PREREG_HO.md): the census rule is not two-sided; after fine-tuning the card stops paying, the library does not
On the label-free fine-tuned models (Qwen3-14B and Qwen3-8B, DT / DT-14 / DT3) — the first models whose usage crashes fall below 5%, the
rule's "do not add" region — the prospective calls were right on 2 / 5 "do not add" and 3 / 6 "add" points (both predictions refuted).
The split is by kind of fact: the usage card adds nothing on any fine-tuned cell (−6.9 to +2.8; −6.9 [−12.6, −2.4] on Qwen3-8B BWOR),
while the library of similar problems' programs adds +4 to +7 on 5 of 6 points (Qwen3-14B OptiBench +5.1 [+2.6, +8.0], OptMATH +6.7
[+2.0, +12.3]) for 331–858 extra input tokens. Fine-tuning internalizes the usage fact, not the formulations of other problem types; the
census counts usage crashes, so it predicts the first and misses the second. With Nemotron-3-Nano (3 / 8) the prospective tally beyond
the development base models is 8 / 19: the rule is reported as descriptive only, and the fact choice goes to the pilot.

## 2026-10-25 01:13 UTC: HO-N4 complete (PREREG_HON.md): Nemotron-3-Nano is a leaky model; the gate transfers, the savings do not
Thinking with the library (32k, model-card sampling), the 2k-token self-review gate, one cheap repair and held-out geometry on
NVIDIA-Nemotron-3-Nano-30B-A3B (4 × RTX 3090), 3 seeds. Fact-first loses to thinking with the same fact on OptiBench (−5.9 [−9.4, −2.5]),
BWOR (−11.8) and LogiOR (−9.8) and ties on OptMATH (−3.0, 72% of the tokens) and geometry (0.0, 66%): 33–79% of its passing word-problem
programs are wrong (5% on geometry). The review gate ties or beats thinking with the fact in all 5 cells (LogiOR +2.2 [+0.7, +4.0],
geometry +1.7 [+0.3, +3.8]) but at 94–109% of its tokens (221% on geometry, where it raises false alarms on 64% of right programs).
The 30-label pilot loses 1.05 points (pre-registered ≤ 1.0: refuted narrowly); the best fixed policy here is two agreeing cheap programs
(0.80). Pre-registered: P3 (gate) held; P1 (library), P2 (census), P4 (pure saving), P5 (pilot) refuted. The family-independent part of
the claim is the decomposition and the gate's accuracy; the token saving belongs to models whose free check does not leak.

## 2026-10-25 02:20 UTC: HO-SB on Nemotron-3-Nano (PREREG_HO.md): short thinking first is cheaper and more accurate than the review gate
For the leaky Nemotron-3-Nano, thinking with the library cut at 2,000 tokens first (budget forcing) and full thinking only when that
program visibly fails ties or beats always thinking with the fact in all 4 word-problem cells (OptiBench +3.8 [+1.8, +5.9] at 72% of the
tokens, BWOR +5.3 at 79%, LogiOR +3.3 at 92%, OptMATH +6.3 [+1.0, +12.0] at 73%) and is at least as accurate as the self-review gate at
fewer tokens in all 4 (OptMATH +5.7 [+0.7, +11.0]). Raw: the extra accuracy comes from problems where full thinking's program crashes,
prints nothing or runs out at 32k while the forced-short program works. Pre-registered SB-P1 and P2 hold (idea chosen post hoc on the
6 Qwen3 cells of HO-TB; these 4 cells were not used). Putting the non-thinking program first brings the leak back (exploratory, −5 to −8).

## 2026-10-25 02:53 UTC: HO-SB complete (PREREG_HO.md): short thinking first fixes leaky models; on Qwen3.5 the plain recipe stays cheaper
On Qwen3.5-9B, where fact-first already ties or wins, short thinking with the fact first (2k-token budget forcing, full thinking on a
visible failure) beats always thinking with the fact on all four word benchmarks (+5.0 to +10.1 at 49–85% of its tokens: full thinking
runs out at 32k on 9–33% of problems) but costs more than the plain recipe (4–66% more tokens for +2 to +8 points): SB-P3 refuted, as
registered the policy is for leaky models (Nemotron: SB-P1 / P2 held). Exploratory: on Qwen3.5 a three-step cascade (non-thinking program,
then short thinking, then full thinking) is at least as accurate as the plain recipe at no more tokens on all four. HO-SB2 (Qwen3 OptMATH
and geometry, including Qwen3-8B geometry, the claim's worst cell) is running.

## 2026-10-25 05:49 UTC: HO-SB3 (PREREG_HO.md): the three-step cascade is not a free default on low-leak cells
On held-out geometry, where the free check rarely passes wrong programs, the cascade non-thinking program → 2k-token thinking → full
thinking (all with the fact) matched the plain recipe at 75% of its tokens for Qwen3.5-9B (+1.0) but cost 19% more for Nemotron-3-Nano
(+1.0), whose full thinking there is already only 1.7k tokens: SB3-P1 refuted (1 / 2). Short thinking first beat always thinking with the
fact in all three geometry cells (+2.8 to +4.2). A fixed 2k budget pays where full thinking is long and costs where it is short; the
choice per cell goes to the pilot (HO-P4, run when HO-SB2's OptMATH thinking reruns finish).

## 2026-10-25 07:49 UTC: HO-SB2 and HO-P4: short thinking first closes the last losing Qwen3 cell and is the best no-label default
HO-SB2 (PREREG_HO.md): on the Qwen3 cells the idea was not chosen on, short thinking with the fact first (2k-token budget, full
thinking on a visible failure) ties or beats always thinking with the fact in 4 / 4 — OptMATH +2.3 / +3.3 at 85–90% of the tokens,
geometry +3.5 and −0.3 at 94–98% — closing Qwen3-8B geometry (fact-first −16.7, gate −6.6) but saving tokens there only on OptMATH (P1
refuted on tokens, P2 holds). Over 14 new cells it never loses (−0.3 to +10.1). HO-P4 (PREREG_MODEL.md, offline, 54 cells, λ = 0.5):
adding SB+F and the three-step cascade to the 30-label pilot raises its utility by +2.12 per cell (P4-1 holds); a short-thinking policy
is best in 40 of 54 cells; always SB+F loses 1.47 to each cell's best (other fixed policies 5.8–7.6), the pilot 1.19 (P4-2, ≤ 1.0,
refuted). Harness: the first Qwen3 OptMATH thinking run lost all rows to 9 over-long requests (fixed in run_form; rerun at 28,672).

## 2026-10-25 08:29 UTC: exploratory — our baseline ignores its own visible failures (always thinking should also get the check)
Re-reading stored runs (no new generation): if always thinking with the fact is also given the free check — a second full think (the
next seed's stored run) whenever the first program visibly fails — it gains +2.5 to +12.3 points over one think on all 16 word-problem
cells of Qwen3-14B-AWQ, Qwen3-8B, Nemotron-3-Nano and Qwen3.5-9B, at 119–164% of its tokens; short thinking first (SB+F) gets part of
that gain at 49–92%. At λ = 0.5 the two are close on several cells (e.g. Nemotron BWOR: utility 50.5 vs 49.8). So the fair baseline must
be matched in the check as well as in the fact, and the claim read as a frontier, not "ties or beats one think". Pre-registered next:
HO-CM (PREREG_HO.md). On contest geometry (311 Codeforces problems, hidden tests; the check = the statement's samples), stored Qwen3-32B
runs (seed 1) give SB+F 32.2% at 97% of one think's tokens vs 29.9%: little to save where short programs rarely pass the samples.

## 2026-10-25 08:42 UTC: HO-CM (PREREG_HO.md): with the check given to thinking too, the best policy is short think → think → retry
On HO-P4's 54 cells (stored runs; λ = 0.5), giving always-thinking the free check (a second think when its program visibly fails) makes
it the best policy in 16 cells and short thinking first followed by that check-matched think (SB→T→T) the best in 21; always SB→T→T loses
1.74 to each cell's best, always T→T 3.40, always SB+F 3.00, and one think — the baseline of every earlier comparison — 7.64. The recipe's
cheap-first policies stay within 1.0 of T→T in 37 / 54 cells (CM-P1, ≥ 40, refuted): ahead on Qwen3.5-9B and wherever the check holds,
2–4 points behind on the leaky models' hardest word problems. The claim is restated: the free check is worth applying to every step,
thinking included, and the step order that wins without labels is short think first, full think on a visible failure, a retry on its failure.

## 2026-10-25 11:51 UTC: exploratory — agreement between the non-thinking and the short-think program flags wrong passing programs
Stored runs, 16 word cells (Qwen3-14B-AWQ, Qwen3-8B, Nemotron-3-Nano, Qwen3.5-9B × OptiBench / BWOR / LogiOR / OptMATH, 3 seeds): a
non-thinking program that passes the free check is right 78% of the time when the same model's 2k-token-think program also passes and
prints the same value (2,029 cases; 80–94% on OptiBench / BWOR / LogiOR), 16% when it prints a different value (759), 36% when the short
think fails visibly (617). No label is used for the signal. Same-mode agreement had failed as a label-free check because a model's cheap
programs share their mistakes (HO-L); across modes they do not, except on OptMATH, where both modes share wrong formulations (agree 26–38%
right vs disagree 12–30%). As a gate it does not pay (accepting only agreeing programs costs both runs: utility below short think → think
→ retry in 13 of 16 cells), so its use is as a label-free estimate of the leak per cell; the pre-registered test is HO-CC's CC-P2 on
contest problems (running).

## 2026-10-25 15:44 UTC: HO-SB4 (PREREG_HO.md): the first think needs 2–4k tokens; 1k is too short for Qwen3-8B
Short thinking with the fact first (full thinking on a visible failure) at budgets 1,000 / 2,000 / 4,000 tokens, Nemotron-3-Nano and
Qwen3-8B on four word benchmarks, 3 seeds: Nemotron ties or beats always thinking at every budget (+2.2 to +10.2 at 64–96% of its tokens;
BWOR +10.2 [+5.3, +15.4] at 4,000); Qwen3-8B loses at 1,000 on OptiBench (−3.1) and LogiOR (−6.2) and ties or beats at 4,000 in all four
(86–109% of the tokens). SB4-P1 / P2 refuted: the budget matters; 4,000 has the best utility (λ = 0.5) in 6 of 8 cells. The claim reads
"a short think first (2–4k tokens)", the budget being one of the pilot's choices.

## 2026-10-25 17:46 UTC: HO-CC CC-P2 (PREREG_HO.md): cross-mode agreement is a label-free leak detector on contest problems too
311 Codeforces geometry problems (hidden tests), 3 seeds: a non-thinking program that passes the samples and whose outputs agree with the
same model's 2k-token-think program on every test input (inputs only, no expected outputs) passes all hidden tests 92.7% (Qwen3-14B-AWQ,
n = 110) and 97.0% (Nemotron-3-Nano, n = 168) of the time; when they disagree or the short think fails the samples, 18.8% and 33.8%.
Pre-registered CC-P2 (≥ 20-point gap) holds by +74 and +63. This is the label-free signal for "the cheap program is wrong although the
free check passed" that the project set out to find; its limit is shared formulation errors (OptMATH). CC-P1 waits for the 32k thinks.

## 2026-10-25 23:25 UTC: DT6 (PREREG_DT.md): distilling the short think into the non-thinking mode does not fix the leak
Qwen3-8B fine-tuned (no labels) on the programs its own 2k-token think wrote for 1,197 unlabeled problems that pass the strict check
(code only, non-thinking prompt): held-out, no fact, 3 seeds, vs the round-1 model — OptiBench 55.7% (+1.5 [−0.7, +3.5]), BWOR 18.7%
(+0.4), LogiOR 14.9% (−1.8; leak 61 → 71%), OptMATH 9.7% (+1.3). Both predictions refuted. The short think helps at inference, not as
training data for the non-thinking mode (consistent with System-2 distillation failing on reasoning-heavy tasks). Direction 2 is closed:
label-free training moves the usage fact into the weights, not formulations and not the check.

## 2026-10-25 23:27 UTC: exploratory — why no label-free check works on OptMATH: a third of its problems are underspecified or misread by every model
Cross-family agreement does not flag OptMATH errors either (passing programs that agree with another family's are right 16–38%, vs 68–96%
on BWOR / LogiOR). Reading the problems: on 35 of its 97 problems (with stored programs) at least four of six models (gpt-oss-20b /
120b, Qwen3-14B-AWQ, Qwen3-8B, Nemotron-3-Nano, Qwen3.5-9B) agree on one value the gold calls wrong. 18 of these are job-shop problems
(26 in the set); at least 12 of the 26 name no machine and no shared operation pair, so the makespan cannot be derived from the text
(e.g. optmath-16: "multiple operations ... may need to be assigned to the same machine", gold 4; all six models print 2 — every
operation on its own machine). 5 are dispersion problems whose pair values differ by direction (Node 0→1: 24, Node 1→0: 22): the gold
sums both directions (optmath-42: 46 = 24 + 22), every model counts each pair once (25). OptMATH's ceiling is the statement, not the
check; the report's "shared formulation errors" are mostly these two kinds.

## 2026-10-26 03:23 UTC: HO-CC complete (PREREG_HO.md): on contest programming the retry transfers, the short-think saving does not
311 Codeforces geometry problems (hidden tests), 3 seeds, full think at 32k (amendment). Thinking again when the program fails a sample
test adds +4.5 (Qwen3-14B-AWQ: 40.8 → 45.3%) and +6.4 points (Nemotron-3-Nano: 34.9 → 41.4%) over one think. Short think → think → retry
ties that (−1.5 [−3.3, +0.2], −0.5 [−2.4, +1.3]) at 94% / 82% of its tokens (CC-P1 refuted: ≤ 90% needed for both); a non-thinking
program first loses 5.5–7.8. Nemotron's think hits 32k on 56% of these problems, so its numbers are lower bounds. CC-P2 (cross-mode
agreement flags leaked programs: 93–97% vs 19–34%) held earlier. Contest problems need the full think; the check at every step carries over.

## 2026-10-26 03:24 UTC: exploratory — the retry inside the recipe for gpt-oss
gpt-oss has no budgeted think (its cheap arm already reasons at low effort), so its analogue of short think → think → retry is
low-effort program → medium think → retry (FF→T→T). Against the check-matched think (T→T): gpt-oss-120b ties on BWOR (0.0) and LogiOR
(−1.1) and trails on OptiBench (−2.0) at 51–64% of the tokens; gpt-oss-20b ties on OptiBench (+0.7 at 48%) but trails on BWOR (−7.7
[−13.8, −1.6]) and LogiOR (−5.1): its low-effort programs that pass the check are wrong too often on the hardest word problems.

## 2026-10-26 07:35 UTC: HO-CAP, Qwen3.5-9B: short thinking first's gain survives an uncapped think; its saving shrinks to 16–19%
Thinking with the fact at a 64k cap (instead of 32k) on Qwen3.5-9B's two most-capped cells: the full think gains +9.0 (LogiOR 38.8 →
47.8%) and +2.7 (OptMATH 29.0 → 31.7%), but short thinking first (escalating to the 64k think) is still ahead, +4.0 [−1.1, +8.7] and +4.3
[+0.3, +8.7], at 81–84% of the 64k think's tokens (CAP-P1, ≤ 70%, refuted on tokens). With a retry on both sides the two tie (−1.8,
+0.7) at 80–81%. Nemotron's 64k contest thinks (CAP-P2) are ~40% done.

## 2026-10-26 09:04 UTC: HO-TR (PREREG_HO.md): repairing a failed think is not cheaper than thinking again
On 16 word cells (four hybrid-thinking models, 3 seeds), one non-thinking repair turn shown the error of a visibly failed think fixes only
4–36 of 26–117 failures per cell; the rest still need a second think. Repair-then-think is as accurate or more than think-again
(recovers 90–145% of its gain) but at 79–104% of its extra tokens (TR-P1 and TR-P2 refuted, 0 / 16 each); with a short think first it
adds +0 to +2.8 points at 95–102% of the tokens. Consistent with Olausson et al. (ICLR 2024): self-repair does not beat resampling on
cost. The recipe's retry stays a fresh think.

## 2026-10-26 12:45 UTC: HO-CAP complete: on contests an uncapped think beats short thinking first; the retry still pays
Nemotron-3-Nano on 311 Codeforces geometry problems with a 64k think: the think solves 55.4% (32k: 34.9%, capped on 56%), 58.5% with a
retry on a failed sample; short think → think → retry 55.4% at 84% of the tokens, −3.1 [−4.8, −1.4] (CAP-P2 refuted; the earlier tie was
the 32k cap). With Qwen3.5-9B's word problems (+4 against a 64k think), short thinking first is a word-problem / geometry step, not a
contest one; the retry adds +3.1 to +12 points in every domain.

## 2026-10-26 21:41 UTC: HO-LF (PREREG_MODEL.md): pseudo-labels from cross-mode votes do not replace the pilot's 30 labels
Labelling a 30-problem pilot by the plurality value of its passing programs (cheap ×2, 2k-token think, think ×2) and choosing among the
nine check-matched policies gives regret 2.00 over HO-CM's 54 cells — worse than always short think → think → retry (1.74) and than 30
labels (1.35); votes of the three thinks only: 1.93. LF-P1 and LF-P2 refuted, LF-P3 holds (Qwen3-8B BWOR 1.18, where HO-L's same-mode
votes kept the leaky cheap program, 2.58). The pseudo-labels match the true labels on 83–92% of programs, but their errors are one-sided
(a wrong think counted right 175–269 times per model, a right one counted wrong 13–20): shared mistakes outvote the truth across modes too
— Qwen3-8B geometry (wrong cheap programs that fail only the degenerate variant agree with the thinks on all six voting inputs; regret 7.5)
and OptMATH (shared misformulations; Qwen3.5 3.4, with thinking-only votes 7.9). Decision as registered: labels stay; cross-mode
agreement is reported as a per-program leak flag only.

## 2026-10-26 22:14 UTC: HO-OSB (PREREG_HO.md): a 2k think first works for gpt-oss too — the recipe's first step holds for all three families
gpt-oss has no budgeted think; its recipe started from low reasoning effort (median 0.7–0.8k tokens) and trailed the check-matched think
on the hard word problems. Cutting a medium-effort think at 2,000 tokens (gpt-oss chat format rendered by hand, the final channel
forced; harmony_budget_chat) and using it as the first step: short think → think → retry ties the check-matched think on BWOR (−2.0
[−6.9, +2.4] at 69% of its tokens; low effort first: −7.7) and LogiOR (+3.3 [−0.4, +7.2] at 83%; low effort first: −5.1), and is the
best policy on OptiBench (76.9% @ 2.26k vs T→T 74.9% @ 2.59k). The short think beats low effort as the first step by +6.5 / +8.3 points
on BWOR / LogiOR: it passes the check as often but its passing programs are wrong less often (30% vs 38%, 23% vs 36%). All three
predictions hold. With Qwen3 / Nemotron (HO-SB, SB2, SB4, CM), the rule for a model whose cheap programs leak is now one rule for every
family tested: a 2k think first, a full think on a visible failure, one retry. (Where the check holds — Qwen3.5 — a non-thinking
program first stays the cheap end; for gpt-oss-20b even OptiBench prefers the short think, 75.8 vs 73.5 utility.)

## 2026-10-26 22:15 UTC: exploratory — cross-mode agreement as a gate on contests does not pay
Stored rows (HO-CC agreement files), 311 problems × 3 seeds: accept the non-thinking program when it passes the samples and agrees with
the short-think program on every test input, else think with a retry. Accuracy equals the check-matched think (Qwen3-14B-AWQ +0.2 [−0.3,
+0.9], Nemotron-3-Nano +0.0 [−0.6, +0.5]) but costs 103–113% of its tokens: only 12–18% of problems agree, so both cheap runs are paid
almost always. Not pursued; agreement stays a per-program flag.

## 2026-10-27 01:23 UTC: HO-32 (PREREG_HO.md): the recipe holds on Qwen3-32B — the leak does not shrink with size
Qwen3-32B-AWQ (2 × RTX 3090), 4 held-out word benchmarks × 3 seeds, the six check-matched policies. Short think → think → retry has
the best utility on OptiBench (72.0% @ 4.06k), BWOR (64.2% @ 7.83k) and LogiOR (56.2% @ 11.21k) and ties the check-matched think there
(−0.8 / +2.4 / +2.5 points at 64–82% of its tokens); on OptMATH every policy lies within 2 points (31.7–33.7%) and the cheapest
(non-thinking → short think → think) wins. The retry pays in all 4 cells (+2.3 to +10.9). A non-thinking program first still trails the
check-matched think by 5–12 points on OptiBench / BWOR / LogiOR: passing non-thinking programs are wrong 27–48% of the time vs 22–29% after
the 2k think (e.g. a reliability table read transposed). Cross-mode agreement flags them: 81% right when the two programs agree, 15% when
they differ. All three predictions hold; the recipe is stated for 8B–32B hybrid models. Running: HO-SEED (Seed-OSS-36B, a fourth family
with a trained thinking budget).

## 2026-10-27 02:42 UTC: HO-PB (PREREG_MODEL.md): the first think's budget is not worth putting in the pilot
Offline, on the 24 HO-SB4 cells (Nemotron-3-Nano and Qwen3-8B × OptiBench third / BWOR / LogiOR / OptMATH × 3 seeds), HO-CM's nine
policies plus SB+F, FF+SB+F and SB→T→T at 1,000 and 4,000 tokens (fifteen), λ = 0.5, k = 30: the extra budgets raise the best of the
menu by +1.02 per cell, but the fifteen-policy pilot gains only +0.69 over the nine-policy one and picks worse in 10 of 24 cells
(PB-1 refuted, ≤ 8 registered); its regret is 1.68 (PB-2, ≤ 1.5, refuted), against 1.60 for always SB4k→T→T with no labels and 2.38
for always SB→T→T at 2k (PB-3 holds). Per model × benchmark (3 seeds pooled) SB4k→T→T − SB2k→T→T is +0.78 utility on average, ≥ 0 in
5 of 8, no accuracy difference significant; the 4k think fails visibly less often in 8 / 8. At λ = 2 the 1k think wins and the pilot
helps (1.80 vs 2.94). Decision as registered: the budget leaves the pilot; the first think is fixed — 4,000 on these two models.
Pre-registered next (HO-4K, PREREG_HO.md, submitted): a 4,000-token first think on Qwen3-14B-AWQ, Qwen3.5-9B and Qwen3-32B-AWQ, which
so far ran at 2,000 only; if it does not carry over, the default stays 2,000.

## 2026-10-27 09:54 UTC: HO-SEED (PREREG_HO.md): the recipe holds on a fourth family; its trained thinking budget is not a better first step
Seed-OSS-36B-Instruct-AWQ (ByteDance Seed, never run here; 4 × RTX 3090), the label-free library prompt on the OptiBench third, BWOR,
LogiOR and OptMATH, 3 seeds, six check-matched policies at λ = 0.5. Short think (forced 2,000-token cut) → full think → retry has the
best utility in all 4 cells (72.6% @ 5.1k, 64.2% @ 12.6k, 55.8% @ 13.2k, 36.0% @ 13.4k; SD-P1 holds), against the check-matched think
−0.7 to +3.7 points at 72–90% of its tokens; the retry pays in all 4 (+3.6 to +10.6; SD-P2 holds); a passing non-thinking program that
agrees with the short-think program is right 83.9% of the time, one that differs 16.1% (SD-P4 holds). The leak is Qwen3's: passing
budget-0 programs are wrong 35–47% of the time on the three solvable benchmarks (28–35% after the 2k think), and the non-thinking
program first trails by 6–12 points. The budget Seed-OSS was trained to keep (thinking_budget 2,048) overruns it in 88–99% of problems
(median 2.6–3.7k tokens) and, as the first step, loses 1.4–3.2 utility points in 3 of 4 cells (SD-P3 refuted). Decision as registered:
the recipe is stated for four families; the forced cut stays the first step.

## 2026-10-27 12:43 UTC: HO-4K (PREREG_HO.md): a 4,000-token first think does not carry over — the default stays 2,000

Qwen3-14B-AWQ, Qwen3.5-9B and Qwen3-32B-AWQ on the four held-out word-problem benchmarks (12 cells, 3 seeds): the recipe
(SB→T→T) with a 4,000-token first think against the 2,000-token one, the same full-think rows. Mean utility gain −0.06 (4K-P1 needed
+0.5), 4k ≥ 2k in 5 / 12 cells (4K-P2 needed 7), the 4k think fails visibly less often in 9 / 12 (4K-P3 needed 10); no cell's accuracy
difference is significant (−1.8 to +2.8 points) and the cascade costs 99–131% of the tokens. On these models 4,000 tokens is still a cut
(Qwen3.5-9B reaches it in 98–100% of rows, the Qwen3 models in 58–98%), so the longer think changes the first program in both directions
and the cascade repairs the visible failures either way (e.g. a correct `linear_sum_assignment` at 2k becomes a CP-SAT program calling a
method that does not exist at 4k). Decision as registered: the first think stays 2,000 tokens; 4,000 pays only for the leakiest models
(Nemotron-3-Nano, Qwen3-8B).

## 2026-10-27 13:32 UTC: related-work check of the budget results; HO-4K's mechanism corrected (the 4k first program is better, the cascade absorbs it)

The 12:43 entry said the 4k think "changes the first program in both directions"; reported apart from the cascade (as the literature
check advised), the 4k first program is right +2.4 points more often, pooled over 1,428 problems [+1.1, +3.8] (10 of 12 cells ≥ 0),
with the passing-but-wrong rate about unchanged. The gain falls mostly where the 2k program fails visibly and the full think repairs it
anyway: end accuracy +0.6 [−0.3, +1.5] (equivalent within ±2 points) at +1.5k tokens per problem (≈ −0.75 utility) — the registered
outcome (P1–P3 refuted, default 2,000) stands. Literature: DART (2606.23181) finds fixed caps just as flat (Qwen3-8B, MATH-500: 69.25 /
69.75 / 70.00 at 1k / 2k / 4k); the Coupling Tax (2605.07686) finds a cascade's fallback must be long enough (Qwen3-8B, GSM8K: −15 net
at 512 tokens, +77 at 2,048), which matches HO-SB4's "1k is too short"; "Does Thinking More Always Help?" (2506.04210) finds gains from
longer thinking non-monotone and parallel samples better than longer thinks, which matches HO-CM. Known: answer-side compensation after
a cut (Nemotron Nano 2, 2508.14444). Not found in the literature: a short forced think as the first stage behind a run-only check
(HO-SB), a trained budget overrun in 88–99% of problems (HO-SEED), and budget choice by a few labels failing (HO-PB; with 30 labels an
accuracy's standard error is about 9 points against 1–3-point budget differences, so this was predictable). Citations in PREREG_TC and
PREREG_IF were verified (three corrections in PREREG_TC; ProgCo, 2501.01264, added as IF-1's closest prior work). Details:
docs/notes/RELATED_WORK.md (2026-10-27 section).

## 2026-10-27 14:23 UTC: TC-1 (PREREG_TC.md): on tool calls the recipe transfers as a small gain, not a saving; the free check is weak and thinking is short

BFCL v4 single-turn (3,482 items; Qwen3-8B, Qwen3-14B-AWQ, Qwen3.5-9B; 3 seeds; BFCL's own checker). TC-P1 refuted (3 / 6: the schema
check fails 17.5 / 25.1 / 8.7 / 21.4% of the Qwen3 models' wrong non-thinking answers, 41.6 / 39.2% of Qwen3.5-9B's, whose errors are
mostly malformed calls; false alarms 0–4%). TC-P2 holds (4 / 6: agreement of two cheap answers adds +1.0 to +5.4). TC-P3 refuted (0 / 6:
cheap-first with check and agreement is 1.3–7.0 points below thinking for Qwen3 at 29–45% of its tokens; 4.7–8.1 above for Qwen3.5-9B,
at 51–72%). TC-P4 holds (6 / 6: the check is worth adding to agreement). TC-P5 holds (6 / 6: SB→T at or above T, +0.5 to +7.6, at
97–105% of its tokens). Thinks are 0.3k tokens, so the cut never binds and the dearest policy costs 0.3 utility points: accuracy
decides, and thinking (with a check-gated second think) wins for Qwen3. The leaks no free signal sees are repeated wrong answers, most
often a call where no tool applies (Qwen3-14B books an Uber ride for a food order in both cheap answers; the think declines). Thinking
cuts irrelevant calls (Qwen3-14B 56 → 91% non-live irrelevance), opposite to the Reasoning Trap's distractor tools. Reading the rows
found a confound: Qwen3.5-9B's full think runs at its card's sampling (T 1.0, top-k 20, presence penalty 1.5), its cut think and
non-thinking answer at T 0.7 without a penalty — it copies BFCL's template (`[func_name1=…]`) in 16% of thinking outputs vs 12%, and
the same mismatch sits under every Qwen3.5-9B / Nemotron short-think result since HO-N. Pre-registered next: PREREG_SAMP.md.

## 2026-10-27 17:17 UTC: SAMP (b) (PREREG_SAMP.md): on tool calls Qwen3.5-9B's "thinking is worse" was mostly its sampling preset
Qwen3.5-9B, BFCL v4 (3,482 items, 3 seeds), a 2 × 2 of mode (full / cut think) × sampling (card general preset / harness). At the harness
sampling the mode does not matter (Th − SB −0.5 non-live, +0.8 live; SAMP-P3 holds); at the card's preset the cut think keeps +1.7
[+0.7, +2.7] on live (SAMP-P4 refuted on one split). The preset is the bigger effect: T 1.0 + presence 1.5 costs the full think 2.9 /
4.9 points and the cut think 3.2 / 2.5, at equal tokens, mostly through answers that copy BFCL's format placeholders and do not decode
(640 of the 1,105 items the harness preset wins). At matched sampling thinking vs not thinking is −1.7 [−3.4, +0.3] on non-live (TC-1
said −4.6) and +10.7 on live. In line with A Sober Look (2504.07086, sampling moves reasoning accuracy by up to 15 points) and the card's
own warning about the presence penalty; the placeholder copying is a new observation. The word-problem half (SAMP-P1 / P2) is running.

## 2026-10-27 19:49 UTC: SAMP (a) (PREREG_SAMP.md): Qwen3.5-9B's word-problem saving holds at a matched preset; the coding preset caps the full think
Every thinking arm of Qwen3.5-9B at the card's precise-coding preset (T 0.6, no presence penalty), BWOR / LogiOR, 3 seeds: short think →
think → retry beats the check-matched think by +5.3 [+0.8, +9.8] / +7.2 [+2.9, +12.3] at 68–74% of its tokens (SAMP-P1 holds 2 / 2). The
general preset did not handicap the baseline (SAMP-P2 holds): the coding preset makes the full think worse (−5.7 / −6.9 for one think)
because it runs to the 32k cap without a program twice as often (95 vs 44 of 246, 149 vs 90 of 276); the card says the presence penalty
is there against endless repetitions. The short-think-first policy does not move with the preset (54.5 vs 54.9%, 52.2 vs 52.5%). With
SAMP (b): the preset matters in opposite directions (short tool-call thinks lose 3–5 points to the presence penalty, long program thinks
lose 5–7 without it); the recipe is robust to it, the full-think baseline is not, and the report's comparison was the conservative one.
LC-1 is amended before any Qwen3.5-9B row is graded: its thinks move to the general preset (102 of the first 224 coding-preset
LiveCodeBench thinks hit the cap).

## 2026-10-27 19:52 UTC: IF-1 (PREREG_IF.md): on instructions the self-written check buys accuracy, not tokens
IFEval (541) / IFBench (300), Qwen3-8B, Qwen3-14B-AWQ, Qwen3.5-9B, 3 seeds, official strict graders. IF-P1 refuted (0 / 6): thinking
only where the model's own executed checker fails costs 98–262% of always thinking's tokens — the checker (written after a 2k think)
costs 1.8–2.5k tokens per prompt and fails 19–47% of right answers; it leaks little (passes 7–20% of wrong ones). IF-P2 holds (4 / 6):
that gated think beats both modes by +1.1 to +2.5 (IFEval all models, IFBench Qwen3-8B). IF-P3 refuted (0 / 6): a non-thinking rewrite
with the checker's message is 0.2–18.4 points worse; 32–61% of rewrites are verbatim (Feedback Friction 2506.11930). IF-P4 holds (5 / 6:
the executed check beats the model's yes / no; it says yes almost always). IF-P5 refuted (3 / 6: a trade against the check-matched
think). Thinking fixes length / counting and breaks combined instructions in every model (Li et al. 2505.11423's pitfall, but on
average it helps these hybrid models). With TC-1: beyond programs the recipe's order transfers as a gain, its saving does not, because
the check is not free. No further run on instructions.

## 2026-10-27 21:05 UTC: LC-1 interim (PREREG_LC.md), Qwen3-14B-AWQ on LiveCodeBench: the contest boundary holds, and the samples leak a third
182 problems from 2025, 3 seeds, official grader, think at 32k (cut on 3 / 546). Short think → think → retry loses to the check-matched
think, −3.5 [−5.7, −1.6] at 94% of its tokens (HO-CC on geometry: −1.5 at 94%), and the non-thinking program first loses −4.4 at 79%:
for this model "contests need the full think" holds on general contest code, by difficulty too (hard problems carry 63% of the think's
tokens and the cut think passes their samples 23% of the time). The loss is all leaked cut-think programs (23 problem-seeds where the
full think was right). The samples leak about a third of every mode's passing programs — N 33.6%, SB 27.8%, T 31.3% — wrong answers on
small inputs the samples miss, time limits on large ones (42% of N's and SB's leaks; a low-load re-grade keeps 134 / 135); DART's
hidden-test gate would add +4.9 points. New against prior work: no study we found reports LiveCodeBench's sample-test leak, and
HardTests (2505.24098) measures test-suite precision, not the samples a model can run. Exploratory: gated on the hidden tests, the
recipe would still cost 105% of the check-matched think's tokens — a better check (ALGO's brute force, a size check) buys accuracy,
not a saving, for this model. Qwen3.5-9B (general preset) and Qwen3-8B wait for GPUs; no decision until they are in.

## 2026-10-28 03:21 UTC: LC-1 (PREREG_LC.md), Qwen3-8B: LC-P1 refuted — short thinking first does not save on general contest code
Qwen3-8B (bf16), LiveCodeBench 2025, 3 seeds: short think → think → retry ties the check-matched think (−0.5 [−2.0, +0.7]) but at
102% of its tokens; with Qwen3-14B-AWQ (−3.5 at 94%) LC-P1 is refuted whatever Qwen3.5-9B does. The two failures differ: Qwen3-14B's
cut-think programs leak (27.8%), Qwen3-8B's often never arrive (32% keep reasoning in comments inside the code block to the 4k cap).
The non-thinking program first ties thinking for Qwen3-8B (−1.3 [−3.1, +0.2] at 87%, LC-P2 holds for it; Qwen3-14B −4.4) — LC-P2
waits for Qwen3.5-9B. LC-P3 holds (2 / 2): the samples leak 26–34% of N's passing programs and 31–34% of the full think's; 41% of
the N / SB leaks are time limits (stable under a low-load re-grade), under the size-check trigger. DART's honest-gate gap is +1.8 for
Qwen3-8B (+4.9 Qwen3-14B). Exploratory: a perfect check still leaves short-think-first at 105–106% of the check-matched think's tokens
for both models — on contest code the full think's tokens sit on problems a 2k think does not solve, whatever the gate.

## 2026-10-28 08:2x UTC: LC-OSS (PREREG_LC.md), gpt-oss-20b on LiveCodeBench: the contest boundary holds on a third family
gpt-oss-20b, 182 LiveCodeBench problems from 2025, 3 seeds, official grader; N = low effort, SB = medium effort cut at 2k (forced
final channel), T = medium, TH = high, thinks at 32k. Short think → think → retry ties the check-matched think (−1.6 [−3.8, +0.4]) at
94% of its tokens — no saving, OSS-P1 refuted, as for Qwen3-14B-AWQ and Qwen3-8B; low effort first loses to one medium think (−2.9
[−5.7, −0.5] at 83%, OSS-P2 refuted); high effort is not the full think at this cap (TH→TH 45.8 vs T→T 66.3; 57% of its runs end at
32k with no program; OSS-P4 refuted), so no 64k run (the mid-run rule). The mechanism differs from Qwen3-8B's: the forced final
channel makes the cut think write a program (no program 2% vs 32%), and the loss is its leaks — 17 problem-seeds where a sample-passing
cut-think program fails a hidden test and the full think is right, e.g. an "already zero → 0" case no example covers. The samples leak
for gpt-oss too (OSS-P3: 24.4% of N's passing programs; SB 17.8%, T 21.0%); DART's honest-gate gap +5.1. Decision: the claim stands
and names three families; no further gpt-oss code run. **Grader finding:** the official LiveCodeBench grader fails any program that
does its work in an unjoined thread (`threading.Thread(target=main).start()`), since it returns before the thread prints; not in the
project's issue tracker. Joining the threads (sensitivity, `LCB_JOIN=1`) turns 2 → 18 of gpt-oss's 77 threaded programs right and
makes OSS-P2 a bare tie (−2.4 [−5.1, +0.2] at 83%, still 7.5 below T→T); Qwen3-14B-AWQ 71 threaded, no verdict changes; Qwen3-8B and
Qwen3.5-9B write none. The official grade decides, as pre-registered; the claim reports both.

## 2026-10-28 09:2x UTC: LC-1 (PREREG_LC.md), all three models: short think first never saves on contest code; cheap first ties for two — against cap-bound thinks
LiveCodeBench 2025 (182 problems), 3 seeds, official grader. LC-P1 refuted 0 / 3: short think → think → retry ties or loses to the
check-matched think at 94–102% of its tokens (Qwen3-8B −0.5, Qwen3-14B-AWQ −3.5, Qwen3.5-9B −0.9). LC-P2 reaches 2 / 3: the
non-thinking program first ties one think for Qwen3-8B (−1.3 [−3.1, +0.2] at 87%) and Qwen3.5-9B (+1.1 [−0.9, +3.3] at 85%), not
Qwen3-14B-AWQ (−4.4). But Qwen3.5-9B's think ends at 32k on 46% of rows (77% of hard ones), so by the cap rule stated before its
analysis the claim waits for its think at 64k (3 jobs submitted); a cap-bound think flatters a cheap first step (HO-CAP). LC-P3 holds
3 / 3 (the samples leak 11–34% of N's passing programs); LC-P4 refuted (DART's honest-gate gap ≥ 2 points only for Qwen3-14B-AWQ,
+4.9). Mechanism: Qwen3.5-9B's samples hold (N leak 11%, T 3%) and its non-thinking program is the strongest (38%), so its cheap
first step is right where it passes — the property the recipe needs; the other models leak a quarter to a third. The yes / no
selector asks to think on 99–100% of contest problems. Related work: no study we found reports LiveCodeBench's sample-test leak by
model (HardTests 2505.24098 measures test-suite precision); DART gates on hidden tests.

## 2026-10-29 01:1x UTC: LC-1 cap rule (PREREG_LC.md), Qwen3.5-9B's think at 64k: cheap first still ties one think on contest code — LC-P2 holds 2 / 3
Qwen3.5-9B's think rerun at 64k on the 182 LiveCodeBench problems, 3 seeds, official grader (two jobs per seed, rows merged by the
rule fixed before grading). The think gains 15 points over 32k (64.3% vs 49.3%; the card reports 65.6 on LiveCodeBench v6 at 81,920
tokens) and now ends at the cap on 17% of rows (32% of hard ones). Against it the non-thinking program first, thinking only when it
fails the samples, ties one think: −1.3 [−3.1, +0.5] at 88% of its tokens (at 32k it was +1.1 at 85%: the cap flattered the cheap
step, as HO-CAP said, but the tie survives). LC-P2 therefore holds for 2 of 3 Qwen models (Qwen3-8B −1.3 at 87%); it loses for
Qwen3-14B-AWQ (−4.4) and gpt-oss-20b (LC-OSS), and the check-matched think (think again when its program fails the samples) is 3.7–5.5
points above it for both models at 1.6× its tokens. The saving sits on easy and medium problems; on hard ones cheap first costs what
the think costs. What it loses: 13 problem-seeds where a sample-passing non-thinking program is wrong and the think is right (11
medium) against 6 the other way, e.g. a "decrement a chosen subset by exactly val" problem where the cheap program solves the easier
sibling problem (accumulate the range totals), passes all three samples and fails the hidden tests. Reported, not re-decided: the 64k
think's programs leak more (12.5% vs 3.2%, on hard problems the 32k think left unsolved) and DART's hidden-test gate gains +2.4
[+0.9, +4.0] over cheap first at 64k (LC-P4 was decided at 32k, 1 / 3). Related work: HRBench (2605.28398) compares mode-switch
strategies in hybrid models (prompt, routing, speculative fast-then-deep on uncertainty signals); none we found gates the switch on
the program's sample tests; DART (2606.23181) gates on the hidden tests. Decision: the claim is restated (REPORT §5.6b, PROJECT,
PROPOSAL, PROPOSAL_ko): on contest code cheap first is a small saving (12–13% of one think's tokens at −1.3 points) for Qwen3-8B and
Qwen3.5-9B, never a match for the check-matched think; short think first is never a saving.

## 2026-10-29 01:2x UTC: PX (PREREG_MODEL.md), the 30-label pilot on contest code, tool calls and instructions: the no-label default does as well or better, except on contest code
The claim's practical rule ("the recipe by default; 30 labelled problems of a new task choose the setting") had been measured only on
word problems and geometry. Pre-registered and run once on the 48 cells of the three task types it was not developed on (HO-P's pilot:
the best of each type's whole policy menu on 30 random labelled problems, scored on the cell; utility = accuracy − 0.5 × ktokens):
the pilot loses 1.29 / 1.96 / 1.77 points to each cell's best on contest code / tool calls / instructions, and always using the
default order (short think, full think only on a visible failure) loses 3.07 / 0.23 / 0.92. PX-1, PX-2 and PX-3 are refuted (1 / 3,
1 / 3, 0 / 3). Mechanism: with about ten policies and 30 labels the argmax carries 1.8–2.0 points of selection noise (the optimizer's
curse, Smith & Winkler 2006), so the pilot only pays where the default is wrong by more than that — contest code, where the 2k first
step plus an extra think costs 3.07 and one plain think (1.24) does as well as the pilot. 100 labels bring the pilot to 0.25 / 0.74 /
0.82. Decision: the claim's pilot bullet is restated — the no-label default is the rule (it loses 1.47 on the word-problem and
geometry cells, HO-P4, 0.23 on tool calls, 0.92 on instructions); labels are for telling a contest-like task (where the full think
should go first) from the rest, and 30 of them are too few to fine-tune among close policies. Next (to pre-register): a conservative pilot that keeps the default unless the labels show a paired gain.

## 2026-10-29 01:3x UTC: PX2 (PREREG_MODEL.md), a significance-gated pilot recovers the default, not more; the argmax pilot loses to the default on 33 fresh cells too
A pilot that keeps the default order unless 30 labels show a paired gain (one-sided 5%, Bonferroni over the menu) was pre-registered
after PX and decided on 33 cells no pilot had seen (Qwen3-32B-AWQ, Seed-OSS-36B, gpt-oss-20b on the word benchmarks; six policies).
There the argmax pilot loses 1.30 points to each cell's best, the conservative one 0.79 (switching in 9% of draws), always using short
think → think → retry 0.72 (best policy in 18 of 33 cells): PX2-1 refuted (0 / 3 models; the gated pilot is 0.04–0.09 above the
default), and in-sample it matches the default on tool calls / instructions (0.38 / 1.09) but cannot see contest code's 3-point loss
in 30 problems (2.76; PX2-2 refuted). Together with PX: across 81 cells of six models and four task types, labels chosen by argmax add
noise and labels gated by a test add nothing; the no-label default order is the project's rule, and the one task type it loses on
(contest code, where one plain think is better by 1.8 points) is not detectable from 30 labels.

## 2026-10-29 06:1x UTC: SQL-1 (PREREG_SQL.md), text-to-SQL: the default order saves, cheap first does not; the no-label default beats the 30-label pilot on a fifth task type
BIRD dev (corrected 2025-11-06, 1,530 questions), Qwen3-8B / Qwen3-14B-AWQ / Qwen3.5-9B, 3 seeds; the free check is "the query runs
and returns rows". It is weak: 40.7–42.9% of the passing non-thinking queries are wrong and it fails only 30–36% of the wrong ones
(SQL-P1 3 / 3), so the non-thinking query first, thinking on a failed check, is 2.7–5.9 points below one think at 27–38% of its
tokens (SQL-P2 0 / 3), and one non-thinking repair from the error does not replace thinking (SQL-P4 0 / 3). The default order — a
2k-token think first, full think on a failed check, think again once — ties the check-matched think at 69% (Qwen3.5-9B) and 89.7%
(Qwen3-14B-AWQ) of its tokens (SQL-P3 2 / 3; Qwen3-8B ties at 91%), saving where the think is long (the cut binds on 50% of Qwen3.5-9B's
questions, 22–24% of Qwen3's). Agreement with a second non-thinking query adds +2.4 / +3.1 (SQL-P5 2 / 3) at 1.5–2.2× the tokens.
Over 9 model × seed cells the no-label default loses 0.33 to each cell's best, the 30-label pilot 2.25 (SQL-P6); the label-free token
switch to the check-matched think costs nothing here (0.34, SQL-P7); in-sample it cuts contest code's loss from 3.07 to 2.40 but raises
PX2's word cells from 0.72 to 0.86 (90 cells: 0.94 → 0.91), so it is kept as an option for contest-like tasks, not added to the default. Raw
outputs: half the leaks are wrong rows (filter values, joins), 40% return other columns than gold (some of them right answers in another
shape, the execution-accuracy false negatives FLEX, 2409.19014, measures); thinking loses N's right answers on 5–7% of rows (e.g. a
value's case). Self-selection ("would thinking help?") says yes on 99.6–100%. Prior work: a trained think router saves 14.7% on BIRD
(2607.22622); the training-free default here saves 9–31% at a tie. Decision: the claim's task list adds text-to-SQL as a type where the
default order saves and cheap first does not (REPORT §5.11, PROJECT, PROPOSAL, PROPOSAL_ko). Next (pre-registered, running): SQL-F,
whether the fact (a SQLite card and the model's own check-passing queries on the same database) makes cheap first a saving.

## 2026-10-29 16:0x UTC: SQL-F (PREREG_SQL.md), the fact on text-to-SQL: it raises the cheap query, not the cascade; a check-admitted library inherits the check's leak
The fact (a three-line SQLite card plus each question's 3 most similar other questions on its database with the model's own SQL-1
queries that passed the free check) given to every arm, 3 models × 3 seeds × 1,530 questions. It raises the non-thinking query by
2.8–3.7 points (SQL-F1 3 / 3; all of it from the library, +2.5 to +3.4; the card alone costs 0.4–1.8), but cheap first still loses to
one think given the same fact (−3.9 / −1.2 / −3.2 at 20–28% of its tokens; F2 1 / 3), the default order is not better with the fact
(F4 0 / 3; −2.2 / −0.1 / +0.9), and the leak does not move (F5 0 / 3): 4–6% more queries run, wrong as often as the rest, so the check's
power falls from 30–36% to 23–26%. Unexpected (F3 1 / 3): the fact lowers the Qwen3 thinks (−2.1 [−3.5, −0.7] / −1.0) and raises Qwen3.5-9B's
(+1.9). Why (post hoc, gold used only to analyse): the library is admitted by the same weak check, so 57–61% of its queries are right,
and the fact's effect rises with how many of the 3 are right — think −3.3 to −5.9 points with 0–1 right (Qwen3), +1.1 to +2.9 with all
3 right; the non-thinking query 0 to +2 with 0–1 right, +5.7 to +6.6 with 3. Raw thinks lost to the fact copy a wrong library structure
(a join path, a two-column output, COUNT for a list) in 3 of 8 read; exact copies are rare (≈1%). Prior work: SAFE-SQL (2502.11438)
filters self-generated examples because unfiltered ones can hurt; ODIS (2310.06302) keeps synthetic examples that execute — the same
check, shown here to be too weak on BIRD; unlike classification (2202.12837), wrong demonstrations matter in SQL generation because the
structure is copied. Decision (pre-registered rule): the fact raises the cheap end and the check's power bounds it; text-to-SQL stays a
type where cheap first is a trade, also with the fact; the default on SQL is stated without the fact (REPORT §5.11, PROJECT, PROPOSAL,
PROPOSAL_ko). For the claim: the fact lever and the check are not independent — a fact the model builds itself is only as good as the
check that admits it: on word problems the library was admitted by a stricter check (two runs agree) and raised thinking too; on
SQL it is admitted by "runs and returns rows" (41–44% leak) and lowers the Qwen3 thinks.

## 2026-10-29 19:4x UTC: SQL-PA pre-registered (PREREG_SQL.md): another model's ~60-token quick query is as strong a check as the model's own 1.1k-token short think, because what sets a check's value is how rarely it shares the generator's wrong answer

Exploratory, on SQL-1's stored dev rows (gold used only to analyse; `python3.11 poc/analyze_sqlpa.py --dev`). Accepting model A's
passing non-thinking query only when another model's non-thinking query on the same question returns the same rows (else A's T→T)
turns SQL's cheap-first trade (N→T→T 3.7–6.5 below T→T) into a tie or win at 73–83% of T→T's tokens when the peer is from the other
Qwen generation: Qwen3-8B ← Qwen3.5-9B +0.5 [−0.4, +1.3], Qwen3-14B-AWQ ← Qwen3.5-9B +0.8 [−0.1, +1.7], Qwen3.5-9B ← Qwen3-8B
+1.2 [+0.3, +2.1]; utility vs the no-label default SB→T→T +0.3 / +1.2 / +1.9. With a same-generation peer (Qwen3-8B ↔ Qwen3-14B) it
is −1.0 / −0.2. Decomposition: every peer adds the same +2.4 to +3.0 points (A right, kept, T→T wrong); the peer only changes the loss
(A wrong, kept, T→T right): −1.8 / −1.9 for the other generation, −3.0 / −3.4 for the same. That loss is set by error coincidence ρ
(same rows given both wrong and passing): a second sample of the same Qwen3 model 83–86%, its own short think 45–52%, the same
generation 52%, the other generation 41–45%. So self-consistency of quick queries is no check here, and the cheap peer (59–70 tokens)
does what the own short think does (1.1–1.4k). It also bears on CV-1: its trained in-model gates keep 47–55% of wrong passing queries
on training questions by round 16–27, the untrained peer 25% on dev (PREREG_CV.md addendum 3, CV-P7, before any CV dev row). Prior
work: agreement-based cascades (2407.02348, 2509.21837) defer when cheaper models disagree; similar models share mistakes
(2502.04313); HO-X here used a much stronger second model. Pre-registered test on 1,338 fresh BIRD-train questions (66 databases,
none in dev), three Qwen models with all SQL-1 arms and Nemotron-3-Nano (another family) as a further peer, 3 seeds: PA1 a saving
against T→T, PA2 beats the default, PA3 the coincidence ordering, PA4 another family coincides less.

## 2026-10-29 22:2x UTC: SQL-FA (PREREG_SQL.md): the self-built library's precision causes what the fact does on SQL
Same library construction, only the admission rule changed (check, agreement with the short think, gold-right, gold-wrong), Qwen3-8B
and Qwen3-14B-AWQ, 3 seeds, 1,530 BIRD dev questions. Right minus wrong examples: non-thinking query +5.8 / +6.2, think +4.9 / +6.2
points (FA1 holds); think with right minus check-admitted examples +3.0 [+1.8, +4.3] / +3.9 [+2.7, +5.2] against +3.2 / +3.3 predicted
from SQL-F's bins (FA2: the difficulty-only alternative predicted 0). The composition model fixed from SQL-F predicts all 12 cells
within 2 points (mean error 0.67; thinks 0.23; FA3 12 / 12). The label-free agreement library (78–79% right) beats the check library
for thinking by +1.8 [+1.1, +2.6] pooled and removes the Qwen3 thinks' loss (+0.0, +0.5 vs no fact; FA4 holds), at 86–88% of the
no-fact thinks' tokens. Raw thinks: what transfers is the example's structure (a COUNT(*) pattern, MIN on a text column, an added
DISTINCT lose; an ORDER BY … LIMIT 1 or a column layout copied from a wrong example wins). Decision: "a fact the model builds itself is
only as good as the check that admits it" is now causal (PROPOSAL keeps it, as tested); the recipe's SQL library is admitted by
agreement with the short think (REPORT §5.11, PROJECT), not stated as a gain over no fact.

## 2026-10-29 22:5x UTC: SQL-PA (PREREG_SQL.md): a peer's quick query makes cheap first a saving against T→T on SQL, not better than the default
1,338 fresh BIRD-train questions, 3 seeds. Accepting a model's passing non-thinking query only when another Qwen generation's quick
query returns the same rows, else think-with-retry: not below T→T in any model (+1.6 [+0.7, +2.6], +1.0 [+0.1, +1.9], +0.5 [−0.2,
+1.3]) at 63–69% of its tokens (PA1 3 / 3; without the peer cheap first was 3.7–6.5 below T→T on dev). Against the no-label default
SB→T→T it is more accurate and cheaper in all three but significant in utility only for Qwen3-8B (PA2 1 / 3, refuted). A second
sample of the same model repeats 87–90% of its wrong answers (Qwen3), its own short think 60–63%, another model 52–62%; the
same-generation > other-generation ordering holds for Qwen3-8B (+10.4) but not Qwen3-14B-AWQ (+3.0 [−1.9, +8.1]; PA3 3 / 4,
refuted). All 6 shared wrong answers read are label or evidence noise (BIRD train, 2402.12243), so coincidence is overstated here.
Decision: reported as an option; SQL's default stays SB→T→T. Exploratory (post hoc): sending a disagreement to the default instead
beats SB→T→T in 3 / 3 models here (+0.9 to +1.7 utility at 64–70% of its tokens) and 2 / 3 on dev — pre-registered out of sample on
word problems and tool calls (HO-PA, stored rows). Nemotron's rows (PA4) still running.

## 2026-10-29 23:0x UTC: HO-PA (PREREG_SQL.md; offline on stored rows): a peer's cheap answer, then the default, pays on tool calls, not on word problems
Accept the model's passing cheap answer only when another Qwen generation's cheap answer is the same, else the no-label default
(SB→T→T). Tool calls (BFCL, 3,482 items, 3 models): more accurate and cheaper than the default for Qwen3-8B (+0.8 points, utility
+0.9 [+0.5, +1.3], 73% of its tokens) and Qwen3.5-9B (+1.9, +2.0 [+1.5, +2.5], 71%); Qwen3-14B-AWQ −0.3 (n.s.) at 77% (HO-PA2 2 / 3,
holds); against T→T 3 / 3. Word problems (476 items, 4 models): utility −0.7 to +0.1, tokens 101–105% of the default (HO-PA1 1 / 4,
HO-PA2 0 / 4): the two cheap programs cost 1–6k and pass and agree on too few hard items to pay for themselves (OptiBench alone:
87–92% of the default's tokens, same accuracy), and two models' wrong programs coincide 56–67% (tool calls 33–39%). A second sample
of the same Qwen model repeats 75–80% of its wrong answers on both types (Nemotron: 59%, as diverse as another model; HO-PA3 6 / 7).
Decision: tool calls' no-label default becomes N → peer agrees → answer, else SB→T→T; word problems unchanged; SQL keeps the peer
check as an option. Two analysis-script fixes (utility scale, the non-inferiority clause) were made after a first run, before deciding.

## 2026-10-29 23:3x UTC: SQL-PA4 (PREREG_SQL.md): another family is not a less correlated peer on SQL
Nemotron-3-Nano's quick queries on the 1,338 fresh questions share 49–55% of the Qwen models' wrong answers, against 52–59% for the
fixed Qwen peers (differences −4.0 to +0.7, none significant; PA4 0 / 3, refuted), and are right less often (45.1% vs 51.4–55.7%). As
the check it ties T→T at 68–73% of its tokens and the default in utility. On SQL the coincidence of two different models' wrong
answers sits around 50% whatever their family; the drop that matters is from the same model (75–90%) to any other (≈ 50%).

## 2026-10-30 02:3x UTC: SQL-DV (PREREG_SQL.md): a check's independence comes from another model of about the same accuracy, not from the same model seen differently
Quick answers only, BIRD dev (1,534) and BFCL (3,482), 3 seeds. Taking A's passing quick answer only when the check's quick answer
agrees, else SB→T→T: the model's own answer with a one-line plan loses to the fixed peer on tool calls (−1.6, −2.2, −0.1 utility;
DV3 0 / 3, refuted), and so does Llama-3.2-3B (−1.0, −0.3, −0.9; DV4 0 / 3); Llama-3.1-8B (another family, same size) ties it. Error
coincidence (independent seeds, SQL / tool calls): own resample 53–86%, shuffled schema / docs 51–71%, plan line 38–56%, other models
23–47%; within the small models Qwen3-4B shares 11–18 points more of a Qwen3 model's wrong answers than Llama-3.2-3B (DV5 4 / 4,
holds). DV1 (a shuffle does not decorrelate, < 15 points) held as pre-registered but is not credited: every run shares the per-item
sampling seed, so the shuffled view at A's seed reuses A's random draws (text identical 37–44% on SQL vs 31–38% at the next seed;
85–87% vs 78–79% on tool calls) — at independent seeds the shuffle removes 9–19 points (2 / 4, refuted). The plan view and the other
models show no such coupling, so SQL-PA / HO-PA stand. A check enters only through r = P(agrees | A right) and e = P(agrees | A
wrong): the linear (r, e) model from A's own rows predicts the 42 cascade gains within 0.66 points on average; the plan view accepts
too many wrong answers (e 26–44%), the 3B model too few right ones (r 44–67%). Decision: the peer check needs a second model of about
the same accuracy, from another family before a larger one of the same family; agreement checks must not reuse the generator's seed.

## 2026-10-30 02:3x UTC: SQL-AND (PREREG_SQL.md, offline): a second check from another family does not pay; a check's value lives on the items where the quick answer and the default differ
Accepting A's passing quick answer only when the peer and then a third model (Nemotron on SQL train, Llama-3.1-8B on tool calls) both
agree, else SB→T→T: against the single peer −0.93 / −0.41 / −0.85 utility on SQL train (0 / 3 better; AND2 refuted) and −0.24 / +0.59
/ −0.40 on tool calls (1 / 3; AND3 refuted); the independence-based prediction (+0.1 to +1.6) had the sign right in 1 / 6 (AND4
refuted), and the joint leak stays at 7–24%, far above the product of the two (AND1 1 / 6). Exact decomposition: accepting changes
accuracy only where A is right and the default wrong (2.8–6.6% of items: +1) or A wrong and the default right (7.1–14.0%: −1), so the
cascade's accuracy upside over the default is at most 3–7 points whatever the check. Every check agrees much less with A's right
answers where the default fails (34–64%) than where it succeeds (74–88%): agreement falls with difficulty for all checks together,
so stacking checks halves the useful agreement along with the leak. Decision: reported; the single peer remains the agreement
route's end. Leaks passing both checks are mostly output-shape conventions (3 of 6 read).

## 2026-10-30 04:2x UTC: CV-1 (PREREG_CV.md): trained for the cascade's value, the quick mode learns to defer everything
RL (LoRA, 94 rounds of 64 BIRD-train questions) on Qwen3-8B's non-thinking mode, rewarded with the cascade's value: on 1,530 dev
questions × 3 seeds CV and the gate-only control C2 both end exactly at T→T (59.2% at 1.92–1.93k vs 59.2% at 1.85k): ACCEPT is not in
the top 20 first tokens on any of 7,395 passing queries. CV-P1–P7 refuted (CV − SB→T→T −0.3 [−1.1, +0.4]; − C1 +1.1 [−0.6, +2.7];
the untrained peer gate − C2 +0.7 [−0.2, +1.5]). In training C2's gate went from accepting 90% of passing queries to 28% (88% right),
5% (100% right), then none. Theory: the gate's exact-expected-reward gradient is ±1 only on RW (query right, T→T wrong: 4.2%) and WR
(10.8%), so any gate pays only if a_RW / a_WR > π_WR / π_RW = 2.5; the peer reaches 3.2, the in-model gate kept right and wrong
passing queries at a ratio near 1.5. Once the gate defers everything, eq. (3) gives the generator zero gradient: CV's quick query
stays at 46.1% (base 46.0%; plain RL C1 50.6%), with no turn-1 DEFER — the learning-to-defer failure Mozannar & Sontag's surrogate
(2006.01862) avoids by training the classifier on every point. The deferred right queries where T→T fails are mostly convention cases
(the think's careful reading differs from the gold's literal one). Checkpoints r10–r90 are being evaluated (CV-P10 / P11).

## 2026-10-30 04:2x UTC: CV-P8 / P9 (PREREG_CV.md addendum 4, offline): plain RL's quick query with the peer check beats the SQL default
C1's quick query (plain RL) → Qwen3.5-9B's quick query returns the same rows → accept, else SB→T→T: 61.3% at 1.36k tokens vs the
default's 59.5% at 1.68k, utility +2.0 [+1.1, +2.9] (P8 holds), +1.4 [+0.7, +2.2] over the base query's peer cascade (P9 holds); the
peer at the next seed +1.9. Predicted beforehand from SQL-AND's decomposition with the base query's agreement rates: +2.24 (inside the
interval). The rates transfer (RW 54.0% vs 54.3%, WR 20.7% vs 18.4%); what changed is the strata: RL moved RW from 4.5% to 6.6% and
WR from 11.0% to 8.3% (200 question-seeds WR → RR). New RW items read: quoting columns with spaces, join paths, unambiguous columns —
the databases' conventions. First cascade to beat the default significantly on BIRD dev; claim changed (PROJECT, REPORT, PROPOSAL).

## 2026-10-30 04:4x UTC: CV-P10 / P11 (PREREG_CV.md addendum 4 (b)): the in-model gate never had a profitable region
C2's gate at checkpoints r10–r90 on dev: utility − T→T rises monotonically from −4.5 (r10, accepting 89% of passing queries) to
+0.04 (r70–r80, 4%) and never beats T→T (P10 holds, 0 / 10) or the peer gate. Wherever it accepts 11–89% it accepts RW (query
right, T→T wrong) only 1.10–1.30× as often as WR, against the 2.54 a gate needs; what it learns is the easy RR questions. The ratio
clears 2.54 only in the last 4–5% (5 RW vs 2–4 WR question-seeds of 4,590: P11 refuted 5 / 8, worth +0.04 points). The collapse is
the Bayes response throughout, not an optimizer artefact: no stopping point or KL term would keep a gain. Raw counts in results/cvck.txt.

## 2026-10-30 06:4x UTC: CV-P12 / P13 (PREREG_CV.md addendum 5): the cascade's gain survives the default trained the same way
SQL-1's short think and think of Qwen3-8B run with C1's adapter (trained in non-thinking mode): SB→T→T(C1) 60.3% at 1.63k, +0.9
[−0.1, +1.9] over the untrained default — the adapter carries little to thinking (T 58.8% vs 58.1%). The peer cascade still adds on
top: C1 → peer → SB→T→T(C1) 62.0% at 1.32k, +1.8 [+0.9, +2.7] over SB→T→T(C1) (P12 holds; predicted +1.9 from the strata), and CV-P8's
policy is non-inferior to it (+1.1 [−0.1, +2.4]; P13 holds). So the gain is the cascade's, not only the training's: training lands in
the quick path, and the peer check is what lets it pay. Best no-label SQL policy: +2.7 [+1.5, +4.0] over the untrained default.
