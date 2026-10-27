# Pre-registration TC: the recipe on tool calling, where the free check is weak and answers are comparable

Written 2026-10-27 12:1x UTC, before any run (the smoke below comes first and is not part of the results). Results go below.

**Why it could change the claim.** The recipe (cheap answer → free check → think only on a visible failure) needs a check that fires
on wrong answers. On the word problems the check was execution, and its blind spot (a program that runs but is wrong, the leak) was
the main loss; IF-1 asks whether a self-written check can stand in on free text. Tool calling is the other end: a free check exists for
every answer (validate the calls against the function docs: known function, required and known parameters, types, enums), but it
cannot see the errors that matter most (a wrong value, a wrong but existing function, a call where none is needed) — in
ComplexFuncBench (2501.10132) 78.8% of a strong model's errors are wrong values. Unlike free text, tool calls are comparable, so a
second label-free signal applies: agreement between two cheap answers (DART, 2606.23181, on math and code). If agreement supplies the
visible failure the schema check misses and the result matches thinking at a fraction of its tokens, the claim becomes "a free check
*or* agreement of cheap answers, where answers are comparable"; if thinking still wins, the boundary is the check's power, measured.
**Prior work, and what is new here.** Thinking on function calling: the Qwen3 report (2505.09388: BFCL v3 thinking 68.1 vs non-thinking
60.2 for 8B, no tokens), IFFC (2608.22472: Qwen3-8B live 74.5 → 83.3 with thinking, non-live 93.8 → 94.9), the Reasoning Trap
(2510.22977: thinking raises Qwen3-8B's distractor-tool hallucination 36.2% → 56.8%), ThinkBrake (2510.00546: stopping a thinking
model's reasoning early on BFCL raises accuracy). Answer first, think when unsure: CopT (2605.20075, an internal reliability estimate,
Qwen3.5-35B-A3B on BFCL v4: 85.8 → 86.5% at 168 vs 235 tokens); DART (two non-thinking drafts agree → answer, else think; math and
code); verify-then-escalate across models: AutoMix (2310.12963). Reviewing calls before execution with an LLM: Reinforced Agent
(2604.27233). New: a deterministic schema check *and* cheap-answer agreement as the gates for the same model's thinking on tool calls,
against the check-matched think, Li-style self-selection and the DART-style gate, with tokens counted, per split, with the check's power
(the leak) measured against BFCL's own error types.
**Run.** BFCL v4 (pip `bfcl-eval` 2026.3.23, Apache-2.0), single-turn Python categories in BFCL's own prompt mode (its default system
prompt with the function docs in JSON; calls returned as `[f(a=1), ...]`), graded by BFCL's own decoder and AST checker
(`poc/prep_tc.py`, `poc/grade_tc.py`). Items (2,198): non-live — simple_python 400, multiple 200, parallel 200, parallel_multiple 200,
irrelevance 240; live — live_simple 258, live_parallel 16, live_parallel_multiple 24, live_relevance 16, and every 3rd item of
live_multiple (351) and live_irrelevance (293), for cost; items whose question has an assistant turn are left out. Models: Qwen3-8B
(q8b), Qwen3-14B-AWQ (q14a), Qwen3.5-9B (q35; its card's thinking sampling, as HO-N / IF-1), RTX 3090, seeds 1–3. Per item and seed
(`poc/run_tc.py`): N = non-thinking calls (T 0.7, 2k cap); S = the model's yes / no answer to "would thinking first help you make the
right calls?"; T = thinking (16k cap); SB = thinking cut at 2,000 tokens, then the calls. **The free check** (offline, deterministic, no
gold): fail = a malformed call (the text names a provided function with "(" but does not decode into calls), an unknown function, a
missing required or unknown parameter, a value of the wrong type, or a value outside its enum (None for an optional parameter = unset);
no call passes. On the gold calls themselves (written out with their first allowed values: 1,604 that BFCL passes) it fails 7 (0.4%:
the docs and the gold disagree on a type or enum), a floor for its false alarms. **Agreement**: the decoded calls in a canonical form are identical (no call = no call).
Policies (`poc/analyze_tc.py`; tokens = every call's output tokens; s' = seed s mod 3 + 1): N, T, SB; S (T if yes, else N); N→T (T
where the check fails on N); **SB→T** (the recipe as stated); T→T (T; seed s' T where the check fails on T: the check-matched think);
2N→T (DART-style without its entropy budget: N and seed s' N, T where they disagree); **N→T|ag** (N and seed s' N; T where the check
fails on N or they disagree); SB→T|ag (N and SB; T where the check fails on SB or they disagree). Utility = accuracy − 0.5 × ktokens;
paired 95% intervals over items. Cells: 3 models × {non-live, live} = 6; accuracy pools items within a split (BFCL's leaderboard
averages categories instead; per-category accuracy is reported).
- **TC-P1 (the free check is weak on tool calls):** the schema check fails on fewer than 25% of the wrong N responses in ≥ 4 of the 6
  cells.
- **TC-P2 (agreement adds the missing power):** N→T|ag's accuracy ≥ N→T's + 1.0 point in ≥ 4 of the 6 cells.
- **TC-P3 (a saving against thinking):** N→T|ag is within 1.0 point of T's accuracy (or above) at ≤ 50% of T's tokens in ≥ 4 of the 6
  cells.
- **TC-P4 (the check is worth adding to agreement):** N→T|ag's utility ≥ 2N→T's in ≥ 4 of the 6 cells.
- **TC-P5 (the recipe as stated transfers):** SB→T is within 1.0 point of T's accuracy (or above) with utility ≥ T's in ≥ 4 of the 6
  cells.
- Reported for every cell, no decision attached: the check's power and false alarms; N/N' and N/SB disagreement (and on wrong N);
  the share of SB thinks cut at 2,000; the self-selection yes rate and S; oracle(N, T); per-category accuracy of N / T / SB (irrelevance:
  does thinking call tools where none applies, as the Reasoning Trap reports?); BFCL's error types of the leaks; raw failures read.
**Decision.** P1, P2 and P3 → where the free check is weak but answers are comparable, the visible failure is the check *or*
disagreement of two cheap answers; the claim is stated that way (new REPORT section; PROJECT claim; PROPOSAL and PROPOSAL_ko).
P1 refuted → the schema check catches what matters on tool calls; N→T is the recipe there and agreement is reported as optional.
P2 refuted with P1 holding → neither free signal sees the errors; the boundary of the recipe is the check's power, reported with the
leak's error types. P3 refuted → on tool calls cheap-first loses to thinking at this price; reported as a boundary. P4 refuted →
agreement alone (DART-style) is the gate, the schema check adds only cost. P5 refuted → the recipe's short think first does not
transfer to tool calls (reported with the SB cut rate: if the cut rarely binds, SB is simply T).
**Smoke (before the main runs; not part of the results).** Qwen3-8B, seed 1, TC_SUBSET=0/40 (55 items), all arms, graded. Amendment
rule fixed now: if any arm's rows are missing, a request fails, or the grader fails, the harness is fixed first; if more than 10% of
N responses are malformed in a way BFCL's own decoder rejects because of our client (not the model), the client is fixed. Nothing about
the policies, the check or the predictions changes after the smoke. The item subset (every 3rd of two live categories) and the job
split (one job per model and seed, or one per model) are fixed from the smoke's token counts and recorded here.

*TC smoke (2026-10-27 12:1x UTC, job 1261112, tag q8bsmoke, TC_SUBSET=0/40 = 55 items, seed 1; not part of the results): every arm
wrote every row, 0 request failures, BFCL's decoder and checker run on every response; no response is malformed because of the client
(the malformed ones are the model's, e.g. JSON `true` for a Python boolean, which BFCL decodes as a string and grades as a type error
— the schema check sees it). Thinks are short: T 0.32k tokens on average (max 1.7k), SB 0.31k with 1 of 55 thinks cut at 2,000, N 28
tokens; the model says "yes, think" on 43 of 55. **Recorded before any main row:** the every-3rd subset of live_multiple and
live_irrelevance was for cost, and at these lengths the full set costs about an hour per model and seed, so every item is used:
3,482 items (live_multiple 1,053; live_irrelevance 875 — 9 whose question is more than one user turn are left out, by the same rule as
the assistant turns). The gold-call floor on the full set: the check fails 14 of the 2,300 gold calls BFCL passes (0.6%). One job per
model and seed (9 jobs, `-x n19`), seeds 1–3; nothing else changes. Main runs submitted 12:2x UTC: jobs tc_{q8b,q14a,q35}_s{1,2,3}
(1261150–1261158).*

*Citation check (2026-10-27 13:3x UTC, after registration and before any result; nothing in the design, the predictions or the decision rules
changes): every ID above exists and says what is quoted, with three corrections. (i) 2608.22472 is "Small Reasoning Models are
Instruction Followers in Function Calling"; IFFC is its method (tool calls posed to the model as an instruction-following task), and
the 74.5 → 83.3 (live) / 93.8 → 94.9 (non-live) thinking gains are inside IFFC (its Table 5); native function calling with thinking
scores 75.5 live / 88.8 non-live (its Table 2). (ii) ThinkBrake's oracle-stopping numbers (Qwen3-4B-Thinking-2507, BFCL single-turn
non-live average 85.8 → 94.2 at 87.1% fewer tokens) are from 2510.00546v1; v5 reports about 90.7 → 95.4. (iii) ComplexFuncBench's 78.8%
value errors are Qwen2.5-72B's. Also: CopT's estimate is a contrastive reverse-KL score (85.77% at 235 tokens → 86.45% at 168, or 86.17%
at 130); DART, where its drafts disagree, predicts a thinking budget from the drafts' entropy (our 2N→T uses the full think instead).*

*Operations (2026-10-27 13:3x UTC, no change to the design): on Qwen3-8B and Qwen3-14B-AWQ, 3 items per seed lost their T row because
their prompt (≥ 4.48k tokens) plus the 16k thinking cap exceeds the default 20,480-token context; jobs tc_q8b_fix / tc_q14a_fix
(1261464, 1261465) rerun only the missing rows with `--max-model-len 32768`.*

### Results TC-1 (2026-10-27 14:2x UTC; `python3.11 poc/analyze_tc.py` after `grade_tc.py` per model; 3 models × 3 seeds × 3,482 items, every row; results/tc_analysis.log; λ = 0.5)
| cell | N | T | SB | S | N→T | SB→T | T→T | 2N→T | N→T\|ag | check power / false alarm |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-8B non-live | 89.4 @ 0.03k | 92.5 @ 0.30k | 92.7 @ 0.30k | 91.3 @ 0.26k | 90.7 @ 0.04k | **93.0 @ 0.31k** | 92.9 @ 0.31k | 90.4 @ 0.08k | 91.3 @ 0.09k | 17.5% / 0% |
| Qwen3-8B live | 69.5 @ 0.02k | 77.4 @ 0.40k | 77.4 @ 0.37k | 76.6 @ 0.30k | 73.5 @ 0.07k | 78.2 @ 0.40k | **78.6 @ 0.43k** | 72.9 @ 0.11k | 75.8 @ 0.14k | 25.1% / 1% |
| Qwen3-14B-AWQ non-live | 86.1 @ 0.04k | 93.5 @ 0.27k | 93.7 @ 0.26k | 90.8 @ 0.25k | 86.9 @ 0.04k | **94.0 @ 0.27k** | 93.8 @ 0.27k | 87.4 @ 0.09k | 87.9 @ 0.09k | 8.7% / 0% |
| Qwen3-14B-AWQ live | 62.3 @ 0.03k | 79.0 @ 0.32k | 79.6 @ 0.31k | 75.2 @ 0.28k | 66.6 @ 0.07k | **80.6 @ 0.34k** | 80.1 @ 0.34k | 69.3 @ 0.12k | 72.0 @ 0.14k | 21.4% / 1% |
| Qwen3.5-9B non-live | 81.5 @ 0.04k | 76.9 @ 0.35k | 80.2 @ 0.30k | 73.9 @ 0.31k | 84.1 @ 0.07k | 84.3 @ 0.34k | 84.2 @ 0.40k | 84.3 @ 0.16k | **84.9 @ 0.18k** | 41.6% / 1% |
| Qwen3.5-9B live | 61.4 @ 0.04k | 67.2 @ 0.31k | 71.3 @ 0.28k | 62.6 @ 0.24k | 66.9 @ 0.10k | **74.7 @ 0.33k** | 73.7 @ 0.38k | 70.6 @ 0.21k | 71.8 @ 0.23k | 39.2% / 4% |
(accuracy % @ output tokens per item; bold: best utility; at these lengths utility ≈ accuracy — the most expensive policy costs 0.3 points.)
- **TC-P1 refuted** (3 / 6, needed 4): the schema check fails on fewer than 25% of wrong N in the Qwen3 cells (17.5, 8.7, 21.4%) except
  Qwen3-8B live (25.1%), and on 39–42% for Qwen3.5-9B, whose errors are mostly malformed calls the check sees. Its false alarms are
  0–4%. The leaks (wrong but passing) are, in order: a call where none applies (irrelevance), a wrong string value, the wrong number of calls.
- **TC-P2 holds** (4 / 6): agreement adds +2.3 to +5.4 points on the live splits and Qwen3-14B non-live (+1.0); +0.5 / +0.8 elsewhere.
  Disagreement is rare where the check is blind: two non-thinking answers disagree on only 3–14% of items for Qwen3 (14–29% of the wrong
  ones — most wrong answers are repeated).
- **TC-P3 refuted** (0 / 6): for Qwen3, N→T|ag is 1.3–7.0 points below T at 29–45% of its tokens; for Qwen3.5-9B it is 4.7–8.1 above T
  but at 51% / 72% of T's tokens (above the 50% bound).
- **TC-P4 holds** (6 / 6): adding the schema check to agreement is worth its cost (+0.5 to +2.9 points over 2N→T at 103–131% tokens).
- **TC-P5 holds** (6 / 6): the recipe as stated (SB→T) is at or above T in every cell: +0.5 [+0.0, +0.9], +0.8 [+0.2, +1.3], +0.5
  [−0.1, +1.0], +1.5 [+0.8, +2.2], +7.4 [+6.3, +8.6], +7.6 [+6.7, +8.5], at 97–105% of T's tokens. The 2,000-token cut almost never
  binds (0–2% of thinks reach it): on tool calls the short think *is* the full think, and SB→T is "think, and think again on a
  failed schema check".
- Reported: thinking helps every Qwen3 cell (T − N +3.1 to +16.8). On BFCL's irrelevance items thinking calls tools *less* (Qwen3-14B
  56 → 91% non-live, 42 → 81% live; Qwen3-8B 77 → 87%; Qwen3.5-9B 66 → 92%), the opposite direction from the Reasoning Trap's distractor
  tools (2510.22977, a different setup: similar but wrong tools, a judge), and it calls less where a call is needed (live_relevance,
  n = 48: Qwen3-14B 100 → 75%, Qwen3.5-9B 79 → 52%). Self-selection says "think" on 69–86% of items; S is 0.0–3.1 points better than
  N→T|ag for Qwen3 at 2–3× its tokens, 9–11 points worse for Qwen3.5-9B. oracle(N, T) 79.9–95.6%.
- **Qwen3.5-9B's thinking is worse than its non-thinking answer on non-live (−4.6 [−6.4, −2.7]), and raw outputs show why:** it copies
  BFCL's format template literally (`[func_name1=solve_quadratic_equation(a=2, b=6, c=5)]`, `math.factorial(params_name1=5)`) in 16% of
  thinking outputs vs 12% of non-thinking and 12% of short-think ones; BFCL cannot decode these. **Confound found in reading:** its
  full think runs at the card's sampling (T 1.0, top-k 20, presence penalty 1.5) while the short think (`budget_chat`) and the
  non-thinking answer run at T 0.7 without a penalty, so part of SB's +3–4 points over T on Qwen3.5-9B may be sampling, not length.
  The same holds for SB vs T of Qwen3.5-9B and Nemotron-3-Nano in the HO word-problem runs (HO-4K's "card sampling" for the budget
  arm was wrong: `budget_chat` never applied it) — a sampling-matched control is pre-registered next (PREREG_SAMP.md).
- Raw rows (Qwen3-14B, seed 1): live_irrelevance_10-1-0 ("order five burgers … from Uber Eats McDonald's", only `uber.ride` given):
  both non-thinking answers book a ride (`uber.ride(loc="123 Main St, New York, …", type="plus", time=300)`) — the schema check passes,
  the two answers agree, a leak no free signal sees; the 206-token think says no tool applies (right). live_multiple_12-4-4 ("who is
  park ji sung"): the two non-thinking answers differ (max_results 1 vs 10), so N→T|ag thinks and the think's
  `HNA_WQA.search(keyword="park ji sung")` is right.
- **Decision as registered:** P1, P2 and P3 do not all hold, so the claim is not restated as "check or agreement". The P1-refuted rule
  ("the schema check catches what matters; N→T is the recipe there") applies only where P1 failed — Qwen3.5-9B, whose errors are
  malformed calls — and even there N→T|ag and SB→T beat N→T; for Qwen3 the check is as weak as predicted. P3 refuted → on tool calls
  cheap-first loses to thinking for Qwen3 (−1.3 to −7.0 points), reported as a boundary; with thinks this short (0.3k tokens) there is
  almost nothing to save at λ = 0.5 (the dearest policy costs 0.3 utility points), so accuracy decides. P4 holds → the check is worth
  adding to agreement. P5 holds → the recipe as stated transfers to tool calls, as a small accuracy gain (+0.5 to +1.5 for Qwen3), not a
  saving: the short think is the full think, and the check-gated second think fixes malformed calls.

