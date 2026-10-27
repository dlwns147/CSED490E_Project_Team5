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

*IF smoke (2026-10-27 10:1x UTC, job 1260342, tag q8bsmoke, IF_SUBSET=0/27, seed 1; not part of the results): every arm wrote all rows (21 IFEval +
12 IFBench), both graders run, every checker runs (0 / 33 errors). But the checkers invent requirements the instruction never states
(a 100-character limit on a one-sentence answer, "start with SUMMARY:", "contains the word joke", no punctuation for a "professional"
joke): on IFEval they fail 15 of the 18 responses the grader passes, so N→T would think on almost every prompt and N→R rewrites right
answers (R 78% vs N 86%). This is the checker prompt, not the model's ability to check: it listed requirement types (format, length,
counts, …), which the model read as a menu. **Amendment (before any main row):** the checker prompt now says to check only requirements
the instruction states explicitly, to quote each one in a comment above its check, to add none of its own, and to accept the response
when a stated requirement is ambiguous (`poc/run_if.py`, CHECKER). A second smoke on other prompts (IF_SUBSET=1/27, tag q8bsmoke2)
checks it; rule fixed now: if its checkers still fail more than half of the responses the grader passes on IFEval, the checker is
written after a 2k think instead (one more amendment, recorded here) — otherwise the main runs start unchanged. Other smoke facts: the
self-selective question gets "yes" on 31 of 33 prompts (Li-style self-selection ≈ always thinking for Qwen3-8B); thinks are short on
IFEval (0.7k mean) and longer on IFBench (2.5k; 1 of 12 at the 16k cap).*

*Second IF smoke (2026-10-27 10:2x UTC, job 1260399, tag q8bsmoke2, IF_SUBSET=1/27, seed 1; not part of the results): with the amended prompt the
checkers still fail 11 of the 18 IFEval responses the grader passes (61%; false passes 0 / 2), and 10 of 12 IFBench responses (2 do not
run). The invented limits are gone; what remains are requirements the instruction does state but code cannot verify ("must answer the
question", "not a limerick", "rhyme scheme not AABBA", "APA format") checked by brittle heuristics, plus over-strict readings ("exactly
2" italic sections for "include two"; "yes" / "no" matched inside other words). **Second amendment, as fixed above:** the checker is
written after a think cut at 2,000 tokens (`budget_chat`, its think and code counted as the check's cost); nothing else changes, and
no further change follows from the checker's false-alarm rate, which is now a result. Expected consequence, stated before any main row:
on IFEval, where Qwen3-8B's full think is short (0.7k tokens in the smokes), a thought-out checker costs about as much as thinking, so
IF-P1 (≤ 50% of T's tokens) is unlikely to hold there; P2–P5 are unaffected. A third smoke (IF_SUBSET=2/27) checks only that the
harness writes every row.*

*Third IF smoke (2026-10-27 10:3x UTC, job 1260445, tag q8bsmoke3, IF_SUBSET=2/27; not part of the results): every arm wrote every row, 0 request
failures, every checker came with code (2 of 32 do not run); the thought-out checker costs 2.0–2.2k tokens. Main runs submitted
unchanged (2026-10-27 10:3x UTC): jobs if_{q8b,q14a,q35}_{ifeval,ifbench} (1260488–1260493), seeds 1–3, one RTX 3090 each.*

*Operations (2026-10-27 11:4x UTC, no change to the design): job 1260491 (if_q8b_ifbench) sat on an RTX 3090 held at 450 MHz by
its power cap (n19, 146 generated tokens/s against 677 for the same model on the next GPU); cancelled after an hour and resubmitted
off that node as 1260938. Rows resume, so only the requests in flight were lost.*

*Related-work check (2026-10-27 13:3x UTC, after registration and before any result; nothing in the design, the predictions or the decision rules
changes). The cited IDs and claims hold (2505.11423 NeurIPS 2025; 2606.09662 "When Built-in Thinking Helps and Hurts: Constraint-Level
Error Shifts in Instruction Following": 10–20% of IFEval prompts flip between thinking on and off for Qwen3 1.7–32B; DVR Findings of ACL
2025; AutoIF 2406.13542, ICLR 2025, training data only). **Closest prior work missed above: ProgCo (2501.01264, ACL 2025)** — the model
writes a verification program from the instruction, runs it on its answer and refines, with a reflection step that questions the program
itself (aimed at false alarms): IFEval prompt-strict GPT-4o 83.0 → 88.0 (91.3 with real Python execution), Llama3.1-8B 73.8 → 76.3;
without its contrast step correct → incorrect flips rise from 15.4% to 35.2%. ProgCo and DVR refine only; neither escalates into a
thinking mode, uses hybrid-thinking models or IFBench, or counts tokens against always / never thinking. Other relevant: Instruction
Boosting (2510.14842, an LLM judge detects violations, 73% accurate); self-correction that does not change the output (Self-Correction
Blind Spot 2507.02778; Feedback Friction 2506.11930) — the verbatim rewrites seen in the partial rows are this; model-written tests that
fail right outputs (2501.12793). CounterRoute (2609.29109) routes Qwen3 between modes with a trained router. New here remains the executed
self-written checker as the gate for the thinking mode, the rewrite-vs-think comparison under the same gate, IFBench at inference time,
and measured false-alarm and copy rates. If IF-1's checker is the bottleneck (false alarms), the named follow-ups are a ProgCo-style
reflection on the checker and AutoIF-style cross-checks of the checker against its own test cases.*


*Operations (2026-10-27 16:2x UTC, no change to the design): one row is missing, Qwen3-14B-AWQ IFBench prompt 187, seed 1 (cheap and
check arms; 299 of 300). Its checker returns one violation per sentence, and the rewrite prompt that lists them is longer than the
context: 16,385+ tokens against 20,480 in the main job, 28,673+ against 32,768 in a rerun (job 1262230). The analysis pairs within each
seed, so that (prompt, seed) pair is left out of every policy alike.*

### Results IF-1 (2026-10-27 19:5x UTC; `python3 poc/analyze_if.py` after `grade_if.py` for every cell; 3 seeds, all rows but one pair, see Operations)
| cell | N | T | N→T (tokens vs T) | N→R | SB→T | T→T | S | checker: false pass / false alarm |
|---|---|---|---|---|---|---|---|---|
| Qwen3-8B IFEval | 82.6% @ 0.37k | 85.2% @ 1.19k | **87.4%** (251%) | 85.5% | 87.6% | 87.2% | 85.0% | 7% / 34% |
| Qwen3-8B IFBench | 25.6% @ 0.60k | 30.4% @ 2.75k | **32.9%** (179%) | 28.6% | 33.1% | 32.3% | 30.0% | 9% / 47% |
| Qwen3-14B-AWQ IFEval | 84.8% @ 0.35k | 86.3% @ 0.97k | **88.7%** (262%) | 88.5% | 88.5% | 89.2% | 86.4% | 13% / 22% |
| Qwen3-14B-AWQ IFBench | 27.5% @ 0.51k | 34.9% @ 1.79k | 35.2% (210%) | 32.6% | 37.3% | 36.7% | 34.9% | 20% / 34% |
| Qwen3.5-9B IFEval | 83.6% @ 0.33k | 91.3% @ 4.25k | **92.4%** (98%) | 88.5% | 92.7% | 93.0% | 89.3% | 14% / 19% |
| Qwen3.5-9B IFBench | 33.1% @ 0.57k | 59.4% @ 8.38k | 58.0% (102%) | 39.6% | 64.1% | 63.2% | 51.3% | 17% / 22% |
- **IF-P1 refuted (0 / 6):** N→T costs 98–262% of always thinking's tokens. Not because the check leaks (it passes 7–20% of wrong answers)
  but because it costs: the checker, written after a 2k think, is 1.8–2.5k tokens per prompt — more than a Qwen3 think on IFEval — and
  it fails 19–47% of right answers, so the think runs anyway. Even with the checker free, N→T would cost 46–99% of T's tokens (≤ 50% only
  for Qwen3.5-9B on IFEval). The named next step (the checker written after a short think) is already the design (second amendment), so
  the line closes here.
- **IF-P2 holds (4 / 6):** the check-gated think is above both modes by +1.1 to +2.5 points on IFEval for all three models and on
  IFBench for Qwen3-8B (N→T − T +2.2 [+1.2, +3.3], +2.5 [+1.5, +3.5], +1.1 [+0.2, +2.0], +2.4 [+0.3, +4.8]); a tie (+0.2) and a loss
  (−1.4) on IFBench for the two stronger models.
- **IF-P3 refuted (0 / 6):** under the same check, one non-thinking rewrite is worse than thinking (N→R − N→T −0.2 to −18.4): 32–61% of
  rewrites return the answer verbatim and only 3–25% then pass the model's own checker.
- **IF-P4 holds (5 / 6):** the executed check beats the model's yes / no choice (N→T − S +2.3 to +6.7; +0.2 on Qwen3-14B-AWQ IFBench).
  The model says "yes, thinking would help" almost always, so S ≈ T for the Qwen3 models.
- **IF-P5 refuted (3 / 6):** against the check-matched think the cheap end is a trade (utility ahead for Qwen3-8B on both and Qwen3.5-9B
  on IFEval, behind elsewhere; accuracy −5.2 to +0.6).
- Raw failures by constraint type (all six cells): thinking fixes length and counting constraints most (Qwen3.5-9B IFBench count 55 →
  87%, IFEval length 87 → 97%) and breaks more than it fixes on IFEval's combined instructions in every model (fixes / breaks 11 / 17,
  3 / 14, 5 / 13 — "repeat the request, then answer", "two responses separated by ******"); the checker's false passes sit on IFBench's
  ratio and repeat constraints (19–38% and 21–56% of the wrong answers there pass it) and IFEval's combined ones; its false alarms come from
  requirements the instruction states but code cannot verify, checked by brittle heuristics (second smoke).
- Caveat (SAMP): Qwen3.5-9B's full think ran at the card's general preset, its cut think and non-thinking answer at T 0.7; every
  N→T / T→T comparison uses the same T rows, so only the SB→T column mixes presets.
- **Decision as registered:** P1 refuted → on instructions the self-written check does not save tokens; its false-pass rate is low
  (7–20%), its cost and false alarms are the problem; no further run (the named next step is in place). P2 holds → where thinking
  helps some requirements and hurts others, the executed check picks per prompt and beats both modes on IFEval: a gain at 1.0–2.6× the
  tokens of thinking, not a saving (as TC-1). P3 refuted → think on the failed check, do not rewrite. New REPORT section; the PROPOSAL's
  claim does not change (P1 refuted).
- Related work: Li et al. (2505.11423) find reasoning can hurt instruction following and propose selective reasoning — for these hybrid
  models thinking helps on average (+1.5 to +26.3) and hurts one constraint family (combined instructions), and the executed check
  beats the model's own selection (P4). ProgCo (2501.01264) refines with a program-driven check; with the same kind of check, thinking
  beats refining in 6 / 6 cells here, and the verbatim rewrites are the resistance to feedback reported by Feedback Friction
  (2506.11930) and the Self-Correction Blind Spot (2507.02778). ProgCo's reflection on the checker (aimed at its false alarms) is the
  untested piece that could lower the cost side; it would add tokens to a check that already costs more than thinking.
