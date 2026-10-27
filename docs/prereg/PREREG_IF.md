# Pre-registration IF: the recipe beyond computation — instruction following, where thinking can hurt

Written 2026-10-27 10:01 UTC, before any run (the smoke below comes first and is not part of the results). Results go below.

**Why it could change the claim.** The recipe (missing fact → cheap answer → free check → think only on a visible failure) has been
tested only where answers are programs (geometry, optimization, contest problems) and the check is execution. The user widened the scope
on 2026-10-27 (PROJECT.md §3). Instruction following is the cleanest next test: (i) thinking does not reliably help there — chain of
thought *lowers* IFEval / ComplexBench accuracy across 15–20+ models (Li et al., "When Thinking Fails", NeurIPS 2025, 2505.11423), and
built-in thinking in Qwen3 shifts errors between constraint types rather than removing them (2606.09662); (ii) a free check exists
without labels: the model can write code for the instruction's verifiable requirements; (iii) the official graders are exact, so
accuracy is not judged by a model. If a self-written check that decides per prompt when to think beats both always and never thinking,
the claim generalizes from "programs with execution checks" to "any answer with a verifiable part"; if it does not, the claim's limit is
the check, measured by its false-pass rate.
**Prior work, and what is new here.** Selective reasoning for instruction following: Li et al. 2025 (self-selective: the model decides
whether to reason; classifier-selective: a trained classifier). Checking instructions with tools and refining: Divide-Verify-Refine
(Zhang et al., Findings of ACL 2025, 2410.12207: decompose, verify with tools, refine with retrieved fixes); NSVIF (2601.17789, a
neuro-symbolic verifier). Model-written verification functions: AutoIF (Dong et al. 2024), used to filter *training* data. Escalating
from a fast to a deep mode: HRBench (2605.28398, speculative switching on math / science / code); DART (2606.23181, draft agreement;
it needs comparable short answers, so it does not apply to free text). New: the model's *own executed checker* as the gate for its
*thinking mode* on instructions, against the check-matched think (thinking again when the checker fails, as HO-CM), a DVR-style rewrite
given the same check, and Li-style self-selection, all with tokens counted — and the leak decomposition (false passes of the checker).
**Run.** Benchmarks: IFEval (541 prompts, google/IFEval) and IFBench (300, allenai/IFBench test: 58 out-of-distribution constraint
types), official strict graders (`poc/grade_if.py`, data and graders in `$POC_DATA/ifeval`). Models: Qwen3-8B (q8b), Qwen3-14B-AWQ
(q14a), Qwen3.5-9B (q35; its card's thinking sampling, as HO-N), one RTX 3090 each, seeds 1–3. Per prompt and seed (`poc/run_if.py`):
N = non-thinking response (T 0.7, 4k cap); C = the model's own checker, written non-thinking from the instruction alone: a Python
function check(response) → list of violated requirements, standard library only, run in the sandbox (a checker that does not run gives
no signal: the response is accepted); R = one non-thinking rewrite of N given C's violations (only where C fails on N); S = the model's
yes / no answer to "would thinking first help you follow every requirement?"; T = thinking response (16k cap); SB = thinking cut at
2,000 tokens (budget forcing), then the response; C is also run on T and SB.
Policies (`poc/analyze_if.py`; tokens = every call's output tokens, the checker's included): N, T, SB; S (T if yes, else N);
**N→T** (N; T where C fails on N); N→R (DVR-style); N→R→T; SB→T (the recipe's order); T→T (T; the next seed's T where C fails on T: the
check-matched think). Accuracy = prompt-level strict (every instruction followed). Utility = accuracy − 0.5 × ktokens. Paired 95%
intervals over prompts. Cells: 3 models × 2 benchmarks = 6.
- **IF-P1 (saving):** N→T is within 1.0 point of T's accuracy (or above) at ≤ 50% of T's tokens in ≥ 4 of the 6 cells.
- **IF-P2 (better than both modes):** N→T's accuracy is ≥ max(N, T) + 1.0 point in ≥ 4 of the 6 cells.
- **IF-P3 (the check's message is the fact):** with the same check, the non-thinking rewrite is at least as accurate as thinking:
  N→R ≥ N→T in accuracy in ≥ 4 of the 6 cells.
- **IF-P4 (an executed check beats the model's guess of when to think):** N→T ≥ S + 1.0 point in ≥ 4 of the 6 cells.
- **IF-P5 (vs the check-matched think):** N→T's utility ≥ T→T's in ≥ 4 of the 6 cells.
- Reported for every cell, no decision attached: the share of checkers that run; the checker's false-pass rate on wrong N responses and
  false-alarm rate on right ones; oracle(N, T); accuracy with tokens of every policy; raw failures read per constraint type.
**Decision.** P1 and P2 → the recipe holds beyond computation: where thinking helps some requirements and hurts others, the model's
own executed check picks per prompt and beats both modes (new REPORT section; PROJECT claim; PROPOSAL and PROPOSAL_ko). P1 holds, P2
refuted → a saving, not a gain, as for gpt-oss / Qwen3.5 on word problems. P1 refuted → the self-written check leaks on instructions
(reported with its false-pass rate); next, the checker written after a short think. P3 holds → for instructions the recipe is N→R→T
(repair with the check's message first, think after); refuted → think on the failed check. P4 refuted → self-selection is as good and
cheaper; reported as such. P5 refuted → as on the word problems, the cheap end is a trade against the check-matched think.
**Smoke (before the main runs; not part of the results).** Qwen3-8B, seed 1, IF_SUBSET=0/27 (21 IFEval + 12 IFBench prompts), all arms,
graded. Amendment rule fixed now: if more than 25% of the smoke's checkers do not run, the checker prompt is revised once (and the
revision recorded here) before any main row; if any arm's rows are missing or a grader fails, the harness is fixed first.
