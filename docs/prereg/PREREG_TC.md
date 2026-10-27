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
