# Pre-registration X3: from words to an optimization model (NL4OPT, IndustryOR) — does the failure move from "facts" to "understanding"?

Written 2026-10-16 18:38 UTC, before any run. Results go below; this section is not edited afterwards.

**Why.** In our synthetic and benchmark optimization tasks the problem was given formally and most solver-code failures were missing
API facts (cured by a 5-line snippet). In real use the problem comes as words, and the hard part is *modelling*: choosing variables,
constraints and the objective. This is a different kind of math (formalising a verbal situation). Prior art: NL4OPT (NeurIPS 2022
competition), OptiMUS, ORLM / IndustryOR, Chain-of-Experts, SAC-Opt; all report accuracy of the final optimal value, mostly with one
formulation.
**Design.** NL4OPT test (245) and IndustryOR (100; Easy / Medium / Hard); gold = optimal objective value or "No Best Solution";
correct = within max(0.01, 0.1%) of the gold value. Modes (poc/run_nlopt.py): mip (pywraplp program), mipf (+ 6-line exact API
snippet), cpsat (CP-SAT program), text (answer in \boxed{}), think (mip with thinking / medium effort). Qwen3-32B-AWQ (no think; think
16k) and gpt-oss-20b (low; medium as think), seeds 1–3. Views analysis as PREREG_VIEWS.
**Predictions.**
- X3-P1 (failure moves to understanding): ≥ 60% of failing mip programs run and print a wrong value (modelling errors), and the API
  snippet adds ≤ 5 points (it added 18–35 points on formally stated problems).
- X3-P2 (shared misunderstanding): among items where the mip and cpsat programs agree, ≥ 15% are wrong on IndustryOR — far leakier than
  text–program agreement on MATH-500 (0.3%): two formulations by the same model share its reading of the words.
- X3-P3: text–program (mip) agreement leaks less than mip–cpsat agreement, for both models.
- X3-P4: thinking adds ≥ 10 points on IndustryOR over no-think mip (modelling is reasoning about the text), at ≥ 3 × the tokens.

# Pre-registration X4 (setup started 18:37; predictions fixed now, runs after setup): formal proofs in Lean 4 (miniF2F, 488 statements)
Perfect checker (the Lean kernel), so the "leaky check" problem disappears; what remains is facts and cost. Setup: Lean v4.15.0 +
Mathlib v4.15.0 under /SSD/lean_postech (≈ 6 GB). Conditions: whole-proof generation by the general models (Qwen3-32B, gpt-oss-20b,
Qwen3.6), k samples per statement; + the exact signatures of the Mathlib lemmas the reference proof uses would be the "fact" arm, but
miniF2F has no reference proofs, so the fact arm = the model's own named lemmas checked for existence first (`#check`) and the
non-existent ones reported back once.
- X4-P1: ≥ 30% of failing proofs cite a lemma name that does not exist in Mathlib (invented, like invented OR-Tools methods), and
  their token log-probs are lower than those of existing names (AUROC ≥ 0.75).
- X4-P2: one round of "these names do not exist: …" feedback fixes ≥ 20% of those proofs at ≤ 1.5 × the tokens of a fresh sample,
  and beats a fresh sample on them (facts beat compute when the failure is knowledge).
- X4-P3: pass@k grows with k with no plateau up to k = 8 (a perfect checker turns sampling into progress), unlike the leaky-check settings.

## X3 results, part 1 (2026-10-16 19:07 UTC; gpt-oss-20b, 345 problems × 3 seeds; results/x3/analysis_oss20.log)
| gpt-oss-20b | NL4OPT | IndustryOR | output tokens (p90) | failures |
|---|---|---|---|---|
| mip program (low) | 76.1% | 46.3% | 529 (929) | 235 run and print a wrong value, 82 crash, 20 no code |
| mip + exact API snippet | 79.2% | 48.0% | 516 (912) | 252 wrong value, 51 crash |
| CP-SAT program | 72.2% | 43.0% | 599 (1,099) | 313 wrong value, 33 crash |
| text answer | 54.3% | 32.0% | 1,231 (1,997) | 237 without a boxed answer |
| mip, medium effort | 78.6% | 52.3% | 2,440 (4,752) | 223 wrong value, 17 cap hits |
Leak (wrong share among agreeing pairs), NL4OPT / IndustryOR: mip–CP-SAT 14.5% / **28.6%**; mip–mip (next seed) 13.6% / 30.8%;
mip–text 10.0% / **12.3%**.
**X3-P1 holds** (70% of failures are programs that run and print a wrong value; the API snippet adds +3.1 / +1.7 points, against
+18 to +35 on formally stated problems). **X3-P2 holds** (28.6% of agreeing mip–CP-SAT pairs are wrong on IndustryOR, vs 0.3% for
text–program on MATH-500). **X3-P3 holds**: a second *formulation* is no more independent than a second sample (28.6% vs 30.8%), but
the text view is (12.3%): two programs share the model's reading of the words, a different way of reasoning does not.
**X3-P4 refuted** (medium effort +6.0 points on IndustryOR at 4.6 × the tokens, not ≥ +10). Qwen3-32B: running.

X4 run details (2026-10-16 19:30 UTC, before any generation): checker poc/run_lean.py (dataset header + dataset statement + the
model's proof body after ':= by'; no sorry / admit; 180 s; ≈ 4–9 s per check). miniF2F test split (244 statements), k = 8 samples
per statement, T = 0.7. gpt-oss-20b low (GPU 2, now); Qwen3.6 and Qwen3-32B no-think with raw log-probs when GPUs free up (X4-P1's
log-prob part uses the Qwen runs). Invented name = an `unknown identifier / constant` error.

## X3 results, part 2 (2026-10-16 19:30 UTC; Qwen3-32B no-think, thinking still running; results/x3/analysis_q32b_partial.log)
mip 78.0% / 34.7% (NL4OPT / IndustryOR) @ 383 tokens; + API snippet 78.2% / 36.7% (+0.2 / +2.0); CP-SAT 70.5% / 27.0%; text 53.6% /
30.3% @ 1,766. Failures of mip: 236 run and print a wrong value, 122 crash (66% modelling). Leak NL4OPT / IndustryOR: mip–CP-SAT 11.2% /
26.0%, mip–mip next seed 11.2% / 29.6%, mip–text 7.7% / 13.5%. **X3-P1, P2, P3 replicate on a second model family**: the fact no
longer helps, two formulations share the misreading as much as two samples do, and a text view halves the leak.

## X4 results, part 1 (2026-10-16 20:29 UTC; gpt-oss-20b low, miniF2F test 244 × 8; results/x4/lean_oss20_test.jsonl)
Harness fix before reading the numbers: 27 attempts gave the proof as a bare `by …` block, which the first extractor missed; re-extracted
and re-checked (2 more correct). **Proved: 309 / 1,952 attempts (15.8%), 66 / 244 statements with 8 attempts (27.0%).** Of the 1,643
failing attempts: 391 give no Lean block (the model declines, e.g. "goes beyond what can be expressed … without `sorry`"), 77 use
`sorry`, and **408 cite names that do not exist** (top: `False.intro` 19, `Nat.pos_of_gt` 10, `Nat.sum_range` 9,
`eq_of_mul_eq_mul_left` 9, `Nat.coprime` 6 (Lean-3 / old-Mathlib spelling of `Nat.Coprime`), `Finset.card_Icc` 6, …): 24.8% of
failing attempts, 32.6% of the 1,252 that give a proof. **X4-P1 (≥ 30% of failing proofs): narrowly refuted on all failures, holds on
the attempts that give a proof**; the log-prob half needs the Qwen run (running). Other errors: type mismatch 404, unsolved goals 253.
Next (running, GPU 2): the feedback round ("these names do not exist") vs a fresh sample on the 408 attempts (X4-P2), then Qwen3-32B
with log-probs.

## X4-P2 result and X4-P2b pre-registration (2026-10-16 21:29 UTC)
**X4-P2 refuted** (results/x4/fix_oss20_test.jsonl, gpt-oss-20b, 412 attempts citing non-existent names): telling the model which names
do not exist fixes 14 (3.4%) at 1.8k tokens, a fresh sample 13 (3.2%) at 1.9k; the feedback attempts cite non-existent names again
MORE often (240 vs 171): told only what is wrong, the model invents other names. Saying "this does not exist" is not a fact.
**X4-P2b (before running):** the analogue of the exact API snippet: for each non-existent name, the 3 most similar *existing* Mathlib
names (of 392,933 dumped from the environment; string similarity restricted to names sharing a name component) with their types
from `#check`, given in the feedback. Prediction: fixes ≥ 2 × the plain feedback (≥ 28 / 412) and fewer repeat non-existent names
than the fresh sample. (Retrieval by name similarity is a stand-in for real premise retrieval, e.g. LeanDojo / ReProver.)

## X4 results, part 2 (2026-10-16 21:35 UTC; Qwen3-32B no-think, miniF2F test 244 × 8, raw log-probs; results/x4/lp_q32b.log)
Proved: 85 / 1,952 attempts (4.4%), 31 / 244 statements with 8 attempts (gpt-oss-20b low: 66) at 1.4k tokens; 146 cap hits, 151 no proof.
751 attempts (38%) hit unknown identifiers; besides invented lemmas (`Nat.pos_of_gt` 9, `Complex.pow_two` 8, `Rat.mk` 8) many are
Lean-3-style tactic words used as terms (`exact` 16, `rw` 7) and out-of-scope local names (`n`, `x`, `h1`): a syntax / scoping failure.
**X4-P1, log-prob half, refuted:** over 5,139 existing and 1,298 non-existent lemma-style names (dotted or underscored) in proofs, the
minimum token log-prob separates them only weakly (median −0.80 vs −1.23; AUROC 0.60, against 0.84–0.90 for invented OR-Tools
methods). Invented Mathlib names are compositional and plausible (`Nat.pos_of_gt` follows the library's naming scheme), so the model
writes them almost as confidently as real ones: the "missing knowledge shows up as low confidence" signature does not transfer.

## X4-P2b result (2026-10-16 21:44 UTC; results/x4/factfix_oss20_test.jsonl)
Feedback naming, for each non-existent name, the 3 most similar existing Mathlib names with their types: **11 / 412 fixed (2.7%)** at
1.8k tokens, vs 14 (plain "does not exist") and 13 (fresh sample); suggestions found for 313 / 412 attempts, and 110 answers use a
suggested name. **X4-P2b refuted.** Why (raw errors): only 75 of the 412 attempts fail on the unknown name alone; the other 337 also have
type mismatches or unsolved goals, i.e. the invented lemma stands in for a step the proof needs but that is not a library fact (the
plan is wrong). Among the 75 name-only failures the fact feedback fixes 7 (9%). Contrast with solver code: an invented OR-Tools
method names an operation that exists under another name (a pure fact gap, fixed by the snippet, and flagged by low confidence,
AUROC 0.84–0.90); an invented Mathlib lemma usually names a step that does not exist (a reasoning gap, written confidently, AUROC 0.60,
not fixed by facts). Same surface symptom ("unknown name"), different mechanism.

## X3 results, part 3 (2026-10-16 22:30 UTC; Qwen3-32B thinking, 16k; results/x3/analysis_q32b.log)
mip with thinking: NL4OPT **56.7%** (no-think 78.0%), IndustryOR 40.3% (34.7%) @ 6.2k tokens (16 ×). Raw failures: 343 crashes, 104 of the
first seed's from **invented API calls written while thinking**: `objective.SetMaximize()` / `SetMinimize()` (80 + 24; the real
methods are `SetMaximization` / `SetMinimization`). Reasoning longer pushes the model to the lower-level objective API it does not
know, so thinking *adds* knowledge failures. **X3-P4 refuted for both models.**

## X4 results, part 3 (2026-10-16 22:32 UTC; Qwen3.6 no-think, miniF2F test 244 × 8, raw log-probs; results/x4/lp_q36.log)
Proved: **741 / 1,952 attempts (38.0%), 133 / 244 statements (54.5%)** at 1.9k tokens (gpt-oss-20b 66, Qwen3-32B 31). Attempts naming
unknown identifiers: 269 (13.8%), 19 of them failing on the name alone. Log-prob half of X4-P1: over 9,376 existing and 277 non-existent
names in proofs, median min log-prob −0.08 vs −0.87, **AUROC 0.81** (≥ 0.75 holds for Qwen3.6, failed for Qwen3-32B at 0.60).
The share of name-only failures does not explain the difference (7% for both Qwen models, 18% for gpt-oss-20b): whether a model's
invented names carry low confidence is model-specific; for the strongest prover it holds, as for invented OR-Tools methods.

## X6 pre-registration (2026-10-17 05:37 UTC, before running): does the API fact make thinking pay? ("facts before compute" on external benchmarks)
Motivation: U1 found that giving the missing fact first and spending compute only where a check still fails beats routing compute by
difficulty or by mechanism, but on hand-picked tasks with hand-written facts. X3 has an untested cell on external benchmarks (NL4OPT 245 +
IndustryOR 100): Qwen3-32B with thinking *loses* accuracy (NL4OPT 56.7% vs 78.0% without thinking) because 314 of its 343 crashes call one
invented method (`Objective().SetMaximize` 241, `SetMinimize` 73; the real API is `Solver.Maximize` / `Objective().SetMaximization`).
New arm **thinkf** = thinking + the same 6-line pywraplp snippet as mipf (16k cap as think); Qwen3-32B-AWQ, seeds 1–3, GPU1 after the X1
re-run frees it (GPU3 went to U2 at 05:36; poc/queues/queue_s2_x6.sh). Existing arms mip / mipf / text / think are reused. Label-free check = the program runs and prints a value.
- X6-P1 (mechanism): invented `SetMaximize` / `SetMinimize` calls drop from 314 to ≤ 30 and runtime errors from 343 to ≤ 114 (3 seeds).
- X6-P2 (fact makes compute pay): thinkf ≥ mipf on NL4OPT (78.2%) and ≥ mipf + 5 on IndustryOR (36.7% → ≥ 41.7%); thinkf > think by ≥ 10
  points on NL4OPT.
- X6-P3 (policy): FACT-FIRST-THEN-THINK (mipf; thinkf only when the check fails) reaches ≥ always-thinkf − 2 points (pooled 345 × 3) at
  ≤ 40% of its output tokens; and it beats THINK-FIRST policies (always think; think, then mipf on failure) at equal or fewer tokens.
Report accuracy @ mean output tokens per item for every arm and policy, by source; crash types and invented names from raw programs.

## X6 addendum (2026-10-17 06:29 UTC, before any X6 row exists): start now on idle GPUs, and two more models
GPUs 0, 2, 3 became idle at 06:08 (U1r / U2 done), so X6 no longer waits for GPU1: Qwen3-32B thinkf on GPU0 (port 8062). Added, same
prompts and seeds 1–3: Qwen3-8B (GPU3, port 8063; arms mip, mipf, think, thinkf; 16k cap) and Qwen3.6-35B-A3B (GPU2, port 8064; same arms;
30k cap because its thinking ran past 16k and 28k in U1). The X1 Qwen3-32B regrade + analysis now has its own waiter (queue_s2_x1fin.sh).
Predictions for the added models (written before any of their X3 rows exist):
- X6-P4: for each added model, thinkf ≥ think pooled over NL4OPT + IndustryOR (3 seeds), and its share of runtime errors is lower.
- X6-P5: thinking pays only with the fact: (thinkf − mipf) > (think − mip) for each model.
- X6-P3 is evaluated per model (FACT-FIRST-THEN-THINK ≥ always-thinkf − 2 at ≤ 40% of its tokens).

## X6 results, Qwen3-32B (2026-10-17 08:40 UTC; results/x3/analysis_x6_q32b.log; 345 problems × 3 seeds)
| arm | NL4OPT | IndustryOR | pooled @ mean output tokens | runtime errors | invented `SetMaximize` / `SetMinimize` |
|---|---|---|---|---|---|
| mip | 78.0% | 34.7% | 65.4% @ 0.38k | 122 | 4 |
| mipf (+ 6-line snippet) | 78.2% | 36.7% | 66.2% @ 0.35k | 127 | 23 |
| think | 56.7% | 40.3% | 52.0% @ 6.2k | 343 | 314 |
| **thinkf** (thinking + snippet) | **79.9%** | **52.7%** | **72.0% @ 5.5k** | 108 | 71 |
Policies (same seed; check = the program runs and prints a value): **FACT-FIRST-THEN-THINK (mipf → thinkf on a failed check) 72.4% @ 1.27k**
(escalates 12%); mip → think 70.0% @ 1.34k; always think 52.0% @ 6.2k; think → mipf 74.0% @ 6.4k; thinkf → mipf 76.8% @ 5.5k.
- **X6-P1 half holds:** runtime errors 343 → 108 (≤ 114 holds); the invented methods drop 314 → 71, not to ≤ 30: with thinking on, the
  model still writes `Objective().SetMaximize` in 7% of programs although the snippet shows `s.Maximize` (and invents
  `Solver.ContinuousVar` 17 times).
- **X6-P2 holds:** thinkf ≥ mipf on NL4OPT (79.9 vs 78.2%) and +16.0 on IndustryOR (52.7 vs 36.7%); thinkf − think = +23.2 on NL4OPT.
- **X6-P3 mostly holds:** fact-first-then-think is +0.4 over always-thinkf at 23% of its tokens and +20.4 over always-think at 20%;
  it is 1.6 points below think → mipf, which costs 5 × more (the fully pre-registered "beats think-first at ≤ tokens" holds against
  always-think, not against think → mipf). Best accuracy: thinkf → mipf 76.8% @ 5.5k.
**Reading (an external benchmark, not built by us):** without the API fact, thinking *loses* 13 points (it invents one method name);
with it, thinking gains 6 points over the same fact without thinking (+16 on the harder IndustryOR). Giving the fact to everyone and
thinking only where the program fails to run keeps all of that gain at a quarter of the tokens.

## X6 addendum 2 (2026-10-17 08:40 UTC, before any Qwen3.6 X6 result is read): Qwen3.6 thinking with the model card's sampling
The Qwen3.6 thinking arms of X6 (GPU2) use our default sampling (T 0.7, no presence penalty) and a 30k cap; in X1 that setting left 12.7%
of Qwen3.6 thinking runs without an answer (X1-Q36R, PREREG_X1.md). Added on GPU0 (port 8066): think and thinkf for Qwen3.6 with the
card's thinking sampling (T 1.0, top_p 0.95, top_k 20, presence_penalty 1.5) and an 80k cap, seeds 1–3, tag q36c
(poc/queues/queue_s2_x6c.sh). Analysis: X6_THINK_TAG=q36c python poc/analyze_x6.py q36 (mip / mipf from the q36 lane).
- X6c-P1: ≤ 2% of q36c thinking runs hit the cap. X6c-P2: P2 / P4 / P5 of X6 hold for Qwen3.6 with these arms (thinkf ≥ think; (thinkf −
  mipf) > (think − mip)). X6c-P3: fact-first-then-think ≥ always-thinkf − 2 points at ≤ 40% of its tokens.

## X6 results, Qwen3-8B (2026-10-17 09:33 UTC; results/x3/analysis_x6_q8b.log; 345 × 3; all four arms new)
| arm | NL4OPT | IndustryOR | pooled @ tokens | runtime errors | most frequent invented names |
|---|---|---|---|---|---|
| mip | 42.0% | 15.3% | 34.3% @ 0.53k | 409 | SumArray.Value 62, Objective.Minimize 61, Objective.SetMinimize 23 |
| mipf | 62.9% | 24.3% | 51.7% @ 0.45k | 267 | Solver.Expression 22, Objective.Minimize 15 |
| think | 78.5% | 41.3% | 67.7% @ 7.5k | 95 | Objective.SetConstantTerm 10 |
| thinkf | 82.3% | 47.3% | **72.2% @ 7.2k** | 49 | Objective.SetConstantTerm 10, Objective.GetCoeffs 9 |
Policies: FACT-FIRST-THEN-THINK (mipf → thinkf) 68.3% @ 2.45k (escalates 26%); mip → think 60.5% @ 3.9k; think → mipf 70.8% @ 7.6k;
thinkf → mipf 72.9% @ 7.2k.
- **X6-P4 holds** (thinkf − think = +4.4; runtime errors 95 → 49). **X6-P5 refuted for Qwen3-8B:** thinking pays without the fact too
  (think − mip = +33.4 > thinkf − mipf = +20.5): the 8B model without thinking misuses the API in many ways (409 crashes), and thinking
  repairs most of them, unlike Qwen3-32B, whose thinking *introduces* one invented method. **X6-P3 refuted for Qwen3-8B:** fact-first
  is 3.9 points below always-thinkf (at 34% of its tokens).
Raw check (where fact-first and always-thinkf differ): the fact program runs and prints a wrong value on 22% of rows for *both* models
(223 / 232 of 1,035); thinkf would fix 30% / 32% of those (67 / 75). But thinkf also breaks rows the fact program had right: 71 for
Qwen3-32B, 35 for Qwen3-8B. For Qwen3-32B the two cancel (fact-first = always-thinkf); for Qwen3-8B thinking breaks fewer, so the check's
leak costs 3.9 points.
**Reading:** "facts first, think where the check fails" loses exactly what the check lets through and thinking would have fixed, and
saves what thinking would have broken. With a check that only asks "does it run and print a number", that trade is even for Qwen3-32B
(full accuracy at 23% of the tokens) and costs Qwen3-8B 3.9 points (at 34% of the tokens).

## X6 addendum 3 (2026-10-17 18:04 UTC, before any new row): Qwen3.6 thinking arms with an 80k cap and no presence penalty (tag q36d)
X6c (card sampling incl. presence penalty) stays paused at 423 / 2,070 rows (vLLM applies the penalty on the CPU). X1-Q36R showed the
token cap is the main factor; so think / thinkf for Qwen3.6 are re-run with T 1.0, top_p 0.95, top_k 20, no presence penalty, 80k cap
(tag q36d), GPU0 (poc/queues/queue_s2_x6d.sh). Predictions X6c-P1..P3 apply to q36d; analysis X6_THINK_TAG=q36d python poc/analyze_x6.py q36.

## X6 results, Qwen3.6 with an 80k cap (q36d; 2026-10-18 05:02 UTC; results/x3/analysis_x6_q36d.log)
mip 68.6% @ 0.9k; mipf 74.6% @ 0.8k; think 59.6% @ 22.0k; **thinkf 79.1% @ 22.6k**; fact-first-then-think 78.2% @ 3.0k (escalates 7%);
thinkf → mipf 82.6% @ 22.7k. 17 of 2,070 thinking runs at the cap.
- X6c-P1 holds (0.8% at the cap). X6c-P2 holds (thinkf − think = +19.5; thinking without the fact *loses* 9 points: 255 runtime
  errors, invented Solver.Status / INFINITY). X6c-P3 holds (fact-first −1.0 point vs always-thinkf at 13% of its tokens).

## X6-AUTO pre-registration (2026-10-18 17:37 UTC, before running): facts without a human — the library's own names by introspection
The weakest point of the main result is that the facts are hand-written. Here the fact is produced automatically from the tool itself:
the public names of pywraplp's Solver / Variable / Constraint / Objective, read with dir() (2.1k characters; it contains SetMaximization
but no SetMaximize). Arms mipa (no thinking + card) and thinka (thinking + card), seeds 1–3, Qwen3-32B-AWQ (GPU0), Qwen3-8B (GPU3), Qwen3.6
(GPU2; thinking 80k, T 1.0 / top_k 20, tag q36d) (poc/queues/queue_s2_x6auto.sh). Prior art: API-reference grounding (DocPrompting;
De-Hallucinator); new here: an introspected card as the fact in the fact-first-then-think policy.
- AUTO-P1: Qwen3-32B thinka ≥ 66.0% (recovers ≥ 70% of the hand-written snippet's thinking gain: think 52.0 → thinkf 72.0) and invented
  SetMaximize / SetMinimize ≤ 30 (think: 314).
- AUTO-P2: mipa ≥ mipf − 2 points for each model.
- AUTO-P3: mipa → thinka (fact-first-then-think with the automatic card) is within 2 points of mipf → thinkf for each model.

## X6-AUTO, part 1: without thinking (2026-10-18 18:36 UTC; thinking arms still running)
| model | mip (no fact) | mipf (hand-written 6-line snippet) | **mipa (introspected name list)** |
|---|---|---|---|
| Qwen3-32B-AWQ | 65.4% (122 runtime errors) | 66.2% (127) | **56.1%** (177) |
| Qwen3-8B | 34.3% (409) | 51.7% (267) | **44.3%** (329) |
- **AUTO-P2 refuted** (−10.1 and −7.4 points vs the snippet). Raw programs (Qwen3-32B, 53 items right with the snippet and wrong with the card):
  the name list pulls the model toward names it does not know how to use — `CreateSolver('SCIP_MIXED_INTEGER_PROGRAMMING')` (an enum name
  from the list; returns None), `MakeRowConstraint` overloads, an objective created but never set (prints 0.0). For the 8B model the card
  still beats no fact (+10.0). **A list of names is not a usage fact:** the snippet works because it shows *how* the five needed calls
  fit together. Next automatic fact to test: usage mined from programs that passed the check.
- X6-AUTO, Qwen3-8B with thinking (2026-10-18 19:36 UTC): thinka 57.5% (220 runtime errors) vs think 67.7%, thinkf 72.2%; fact-first with the card
  (mipa → thinka) 59.7% vs with the snippet 68.3%: **AUTO-P3 refuted for Qwen3-8B**; the name list hurts with thinking too.

## X6-VER pre-registration (2026-10-18 19:36 UTC, before running): the automatic usage fact = a check-passing program of the same model
For each problem, the most similar problem of the OTHER benchmark (BM25 over question words) whose program — written by the same model
with no fact (mode mip, seed 1) — runs and prints a value is shown as an example (label-free: the check, not the answer, selects it;
NL4OPT examples for IndustryOR problems and vice versa). Arms mipv / thinkv, seeds 1–3; Qwen3-8B on GPU3 now (queue_s2_x6ver.sh), then
Qwen3-32B and Qwen3.6 as GPUs free up.
- VER-P1: mipv ≥ mipf − 2 points (the mined example is as good a usage fact as the hand-written snippet) for each model.
- VER-P2: fact-first with it (mipv → thinkv) is within 3 points of mipf → thinkf for each model.
- X6-AUTO, Qwen3-32B with thinking (2026-10-18 20:36 UTC): thinka 56.3% (invented SetMaximize / SetMinimize 241; think 314, thinkf 71) vs thinkf 72.0%;
  fact-first with the card 63.1% @ 1.7k vs with the snippet 72.4% @ 1.3k. **AUTO-P1 and AUTO-P3 refuted:** a list that contains
  SetMaximization does not stop the model from inventing SetMaximize while it thinks; the snippet's worked call does.
- **X6-VER, Qwen3-8B without thinking:** mipv (its own check-passing program for a similar problem of the other benchmark) **51.0%** vs
  the hand-written snippet 51.7% and no fact 34.3%; runtime errors 215 (snippet 267, none 409), invented SetMaximize 0. **VER-P1 holds
  for Qwen3-8B** — an automatically mined usage example is as good a fact as the hand-written one. Thinking arm and the other two models
  running.
- X6-VER results so far (2026-10-18 21:36 UTC): Qwen3-32B mipv 66.0% (snippet 66.2%; runtime errors 88 vs 127) — **VER-P1 holds for Qwen3-32B too.**
  Qwen3-8B with thinking: thinkv 67.7% vs thinkf 72.2%; fact-first mipv → thinkv 60.0% vs mipf → thinkf 68.3%: **VER-P2 refuted for
  Qwen3-8B.** Raw counts: the similar-problem example makes more programs run (79% vs 74% pass the check) but more of the passing ones are
  wrong (35% vs 30%), and thinking with it fixes fewer failures (93 vs 105 of 219): the model copies the other problem's *formulation*,
  so the "runs and prints" check passes wrong programs. The hand-written snippet carries usage without a formulation to copy.
**X6-VER2 pre-registration (before running):** the shortest check-passing program of the other benchmark (one per benchmark, ≈ 0.9k
characters for Qwen3-8B: CreateSolver, IntVar, Minimize, Add, Solve, solution_value — usage with almost no formulation) as the fact;
arms mips / thinks, Qwen3-8B on GPU3 (queue_s2_x6ver2.sh). VER2-P1: mips ≥ mipf − 2 and its pass-but-wrong share ≤ mipf's (30%);
VER2-P2: mips → thinks within 3 points of mipf → thinkf (68.3%).
- X6-VER2, Qwen3-8B without thinking (2026-10-18 22:35 UTC): mips (the shortest check-passing program) **52.1%** vs snippet 51.7%, mined similar example
  51.0%, no fact 34.3%; runtime errors 162 (snippet 267). But 84% of programs now pass the check and 38% of those are wrong (snippet:
  74% / 30%). VER2-P1 accuracy part holds; the pass-but-wrong part is refuted. Pattern across all facts: the better a fact removes
  crashes, the more wrong-but-running programs reach the check (no fact 41% → 30–38%; run share 59% → 74–84%) — a crash was itself a
  free check, and fixing the API takes it away. Thinking arm still running.

## Automatic facts in the full pipeline (2026-10-18 23:36 UTC; results/x3/analysis_autofacts.log; FF = fact program, thinking if it does not run;
FFR = thinking unless two fact programs run and agree)
| fact | Qwen3-8B FF | Qwen3-8B FFR | Qwen3-32B FF | Qwen3-32B FFR | Qwen3-32B always-think |
|---|---|---|---|---|---|
| none | 60.5% @ 3.9k | 66.4% @ 7.1k | 70.0% @ 1.3k | 70.4% @ 3.5k | 52.0% |
| snippet (hand-written) | 68.3% @ 2.5k | 72.9% @ 5.4k | 72.4% @ 1.3k | 75.2% @ 3.0k | 72.0% |
| name list (introspection) | 59.7% @ 3.3k | 62.1% @ 6.2k | 63.1% @ 1.7k | 65.4% @ 4.3k | 56.3% |
| own similar check-passing program | 60.0% @ 2.4k | 65.7% @ 4.9k | **70.8% @ 1.0k** | **75.8% @ 3.0k** | 71.4% |
| own shortest check-passing program | 61.7% @ 1.8k | 67.0% @ 4.7k | (running) | | |
- **VER-P2 holds for Qwen3-32B** (FF −1.6 points at 77% of the tokens; with the agreement check the automatic fact is +0.6 at equal
  tokens), refuted for Qwen3-8B (−6 to −8). The mined example also repairs Qwen3-32B's thinking (52.0% → 71.4%, like the snippet's 72.0%).
**Reading:** for the 32B model a fact mined automatically from its own check-passing programs on another benchmark replaces the
hand-written snippet; for the 8B model it falls 6 points short (it copies formulations, and its wrong programs run). Added now
(pre-registered): the shortest-program fact for Qwen3-32B (GPU0) and both automatic facts for Qwen3-14B-AWQ (3090-class; GPU3),
predicting Qwen3-14B lands between the 8B and 32B gaps (FFR within 4 points of its hand-written FFR).
- Pre-registered (2026-10-19 00:36 UTC): automatic facts for gpt-oss-20b (3090-class; low effort without thinking, medium with): mipv ≥ mipf − 2 (70.1%) and FFR with the mined example within 2 points of FFR with the snippet; GPU2 (queue_s2_x6ver.sh with POC_REASONING_EFFORT per arm → queue_s2_x6ver_oss20.sh).
- X6-AUTO, Qwen3.6 (2026-10-19 00:36 UTC): with the name list thinking drops to 47.2% (no fact 59.6%, snippet 79.1%); fact-first 73.2% @ 5.3k vs 78.2% @
  3.0k with the snippet. Raw: 408 runtime errors, 294 of them wrong argument types in low-level calls the list exposes
  (`solver.Constraint(lb, ub)`, `solver.Var(...)`, enum names passed as strings). Same mechanism in all three models: **a name list
  without usage points the model to calls it cannot use** — AUTO refuted for every model.
