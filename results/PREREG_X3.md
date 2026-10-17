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
re-run frees it (GPU3 went to U2 at 05:36; poc/queue_s2_x6.sh). Existing arms mip / mipf / text / think are reused. Label-free check = the program runs and prints a value.
- X6-P1 (mechanism): invented `SetMaximize` / `SetMinimize` calls drop from 314 to ≤ 30 and runtime errors from 343 to ≤ 114 (3 seeds).
- X6-P2 (fact makes compute pay): thinkf ≥ mipf on NL4OPT (78.2%) and ≥ mipf + 5 on IndustryOR (36.7% → ≥ 41.7%); thinkf > think by ≥ 10
  points on NL4OPT.
- X6-P3 (policy): FACT-FIRST-THEN-THINK (mipf; thinkf only when the check fails) reaches ≥ always-thinkf − 2 points (pooled 345 × 3) at
  ≤ 40% of its output tokens; and it beats THINK-FIRST policies (always think; think, then mipf on failure) at equal or fewer tokens.
Report accuracy @ mean output tokens per item for every arm and policy, by source; crash types and invented names from raw programs.
