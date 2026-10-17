# Pre-registration VIEWS: when can a model catch its own mistakes? Error correlation between a model's "views" predicts it

Written 2026-10-16 18:34 UTC, before any analysis or run. Results go below; this section is not edited afterwards.

**Question (research, not a fix).** Test-time scaling increasingly relies on a model checking itself: self-consistency, best-of-n with
a self-verifier, agreement gates, LLM judges. Recent work shows this fails because errors are correlated (Kim et al., ICML 2025; Goel
et al., ICML 2025; "self-consistent errors", arXiv 2505.17656; "Consensus is not verification", arXiv 2603.06612; verifier blind spots
rising with capability, arXiv 2609.01345), mostly *across models*. Our runs show the same model can produce *decorrelated* views by
changing how it solves a problem (with vs without offered tools, a different solver library, text vs program), and that this works
for some models / tasks and not others (Qwen geometry: 1–2 agreed-but-wrong of ~40 wrong; gpt-oss contest: 38 of 66 wrong accepted;
competition math: text–program agreement wrong 0.3% vs text–text 1.5%). We ask: (1) does the measured error correlation between two
views predict how much a check built from them gains (its leak and the accuracy-per-token of the gated policy)? (2) which errors are
shared across views? Hypothesis: views decorrelate errors whose cause the view changes (context-induced, format-induced) but not
errors from missing knowledge or a wrong idea of the algorithm, which every view of the same model shares.
**Measure.** For each (model, task, view A, view B) setting with exact labels: error consistency κ (Geirhos et al. 2020: agreement on
which items are wrong beyond chance), the leak λ = P(answers agree and are wrong | answers agree), and the gain of the gate
"accept when A and B agree, else escalate" over always-escalating, at matched tokens.
**Settings already measured (offline, stored outputs):** geometry K8 vs no helpers (Qwen3-32B, Qwen3-8B; 3 seeds), contest low vs
low + K8 and medium vs Qwen3.6 (gpt-oss-120b), optimization library pairs (4 models, N15), job-shop default vs no library (4 models),
competition math text vs program and text vs text (gpt-oss-20b, Qwen3-32B, Qwen3.6), and same-view seed pairs as the reference.
**Beyond computation (new runs after U1):** factual QA with exact answers (PopQA, local), views = answer directly / answer after
recalling related facts / answer in another language; prediction: knowledge errors are shared across views (κ high), so
self-verification cannot catch them, unlike format- or tool-induced errors.
**Predictions.**
- VIEWS-P1: across ≥ 15 settings, Spearman correlation between κ and λ ≥ 0.7; between κ and the gate's gain ≤ −0.6.
- VIEWS-P2: a simple model fitted on half of the settings (λ from κ and the two views' accuracies) predicts λ on the other half within
  5 points (mean absolute error).
- VIEWS-P3: same-view pairs (two samples of the same condition) have higher κ than different-view pairs of the same model in ≥ 80% of
  model–task cells.
- VIEWS-P4 (mechanism): items whose error is shared across views are enriched for knowledge / algorithm errors (contest problems
  rated ≥ 2,000; invented-API crashes shared by both views) relative to items whose error is view-specific.
- VIEWS-P5 (factual QA): κ between views ≥ 0.6 and the agreement gate gains ≤ 2 points: self-verification does not catch missing knowledge.

## Results, offline meta-analysis (2026-10-16 23:47 UTC; results/views_analysis.log; 56 settings from X1, X3, N12, N15)
Error kappa (how often two views are wrong on the same items, beyond chance) and leak (P(first view wrong | the two answers agree)):
| family | same view resampled: kappa | different views: kappa | leak, same view → different view (same first view) |
|---|---|---|---|
| competition math, MATH-500 (3 models) | text–text 0.41–0.57 | text–program 0.12–0.26 | 1.5% → 0.3%, 3.4% → 0.9%, 0.5% → 0.5% |
| competition math, AIME (3 models) | text–text 0.56–0.68 | text–program 0.14–0.38 | 13.5% → 6.8%, 45.8% → 18.8%, 2.8% → 2.1% |
| verbal optimization, IndustryOR (2 models) | mip–mip 0.59–0.71 | mip–CP-SAT 0.45–0.61; mip–text 0.20–0.36 | mip–mip 30.8% → mip–text 12.3%; 29.6% → 13.5% |
| verbal optimization, NL4OPT (2 models) | mip–mip 0.71–0.73 | mip–CP-SAT 0.47–0.53; mip–text 0.24–0.28 | 13.6% → 10.0%; 11.2% → 7.7% |
| geometry with a toolbox (Qwen3-32B / 8B) | K8–K8 0.54 / 0.79 | K8–no helpers 0.19 / 0.34 | 18.9% → 12.7%; 13.3% → 4.8% |
| optimization libraries (4 models) | free–free 0.24–0.72 | free–MIP / none −0.03–0.50 | ≈ 0% everywhere (wrong plans rarely coincide) |
- **VIEWS-P1 refuted** across all 56 settings (Spearman kappa–leak 0.36, kappa–catch −0.38): the leak also depends on the first view's
  error rate and on how often two *wrong* answers coincide, which differs by domain (≈ 0 for optimization plans, high for verbal
  problems where a shared misreading gives the same wrong value).
- **VIEWS-P2 narrowly refuted** (one fitted coincidence rate, r = 0.10, predicts held-out leaks with MAE 6.2 points, not ≤ 5).
- **VIEWS-P3:** in 16 / 16 model–family cells the most correlated resampled pair is more error-correlated than every different-view pair; requiring
  *every* same-view pair to beat *every* different-view pair, 11 / 16 (69%): holds in the first reading, not the strict one.
- Exploratory (after seeing the table): holding the first view fixed, the less correlated second view gives the less leaky check in
  13 of 14 comparisons with a non-zero leak (the exception ties at 0.5%). Two solver formulations of a verbal problem are the
  exception: they are almost as correlated as resampling (kappa 0.45–0.61 vs 0.59–0.73) and almost as leaky.
- VIEWS-P4 / P5 (mechanism enrichment, factual QA) not run yet.
**Reading:** a second view helps exactly as much as it decorrelates errors from the first; what decorrelates is a change in *how the
model reasons* (text vs program, with vs without the misleading tools), not a change of library or formulation over the same reading.
Absolute leak levels are domain-specific (answer coincidences), so error kappa ranks second opinions for a given first view but does
not predict leaks across domains.

## VIEWS-P4 results (2026-10-17 02:56 UTC; results/views_p4.log)
Shared errors = both views wrong with the same answer; view-specific = exactly one view wrong.
- Competition math (text vs program): shared errors are on harder problems for all three models: mean level 4.83 vs 4.25 (gpt-oss-20b,
  AIME share 50% vs 16%), 4.42 vs 3.99 (Qwen3-32B, 25% vs 11%), 4.75 vs 4.32 (Qwen3.6, 25% vs 21%); but only 6–12 shared errors per model.
- Verbal optimization (IndustryOR, mip vs text): the opposite: shared errors are on *Easy* problems (57–60% Easy, 0% Hard; view-specific
  26–29% Hard). Raw items: industryor-90 (gold 409.09, every model and view says 408: the gold treats units as continuous, the models
  as integers), industryor-24 (an ambiguous multi-period investment): many "shared errors" here are ambiguities of the problem
  statement or the gold value, which every view resolves the same way.
**VIEWS-P4: holds for competition math (small n), refuted for verbal optimization**, where shared "errors" largely reflect label /
specification ambiguity, so the IndustryOR leaks above overstate true leaks.

## VIEWS-P5 design addendum (2026-10-17 03:24 UTC, before running): factual QA beyond math and computation
PopQA, 1,500 questions (5 subject-popularity bins × 300; results/x5/popqa_sample.json); Qwen3-8B; views: direct short answer (seeds 1, 2),
recall-first (write 2–3 facts about the subject, then answer), thinking on (the expensive mode). Correct = an accepted alias occurs in
the answer. Gate: accept the direct answer when direct and recall agree (one contains the other, case-insensitive), else thinking.
Predictions as VIEWS-P5: error kappa(direct, recall) ≥ 0.6 (close to direct–direct); gate ≤ +2 points over always-direct; thinking
≤ +2 points over direct (compute does not add facts); the share of errors shared by both views is highest in the least popular bins.

## VIEWS-P5 results (2026-10-17 03:30 UTC; PopQA 1,500, Qwen3-8B; results/x5/analysis.log, analysis_strict.log)
Accuracy: direct 20.7% (seed 2: 20.8%) @ 6 output tokens, recall-first 21.2% @ 100, thinking 22.5% @ 426; by popularity bin (least →
most popular) direct 21 / 10 / 12 / 18 / 41%, thinking 20 / 8 / 12 / 22 / 51%. Strict scoring (aliases of ≤ 2 characters must match
exactly) changes every number by ≤ 0.2 points.
Errors are shared across views: kappa direct–direct **0.91**, direct–recall **0.75** (math text–program 0.12–0.38). When the two views
agree, the answer is still wrong **63%** (direct–direct) / **38%** (direct–recall) of the time (math: 0.3–19%). Gate (direct ==
recall → accept, else thinking): 23.7% vs always-direct 20.7% (escalates 1,154 of 1,500) vs always-thinking 22.5%.
- **VIEWS-P5 kappa part holds** (0.75 ≥ 0.6); **thinking ≤ +2 holds** (+1.8); **gate ≤ +2 narrowly refuted** (+3.0, but it escalates 77%
  of items, i.e. it is almost always-thinking plus 1.2 points); shared errors are not concentrated in the least popular bins
  ([34, 24, 25, 22, 25]); view-specific errors are concentrated in the most popular bin (45 of 124).
**Reading (across the ladder):** errors that come from missing knowledge are shared by every view of a model (kappa 0.75–0.91; a
self-check passes 38–63% wrong answers), errors that come from format, tools or a reasoning path are not (kappa 0.12–0.38 for text vs
program in math; 0.3–19% leak). Self-verification and extra thinking buy little where the model lacks the fact.

VIEWS-P5 replication (2026-10-17 03:31 UTC, before running): Qwen3.6-35B-A3B on the same 1,500 PopQA questions, same views (thinking cap
4,096 tokens as for Qwen3-8B), same predictions (kappa direct–recall ≥ 0.6; thinking ≤ +2 points). poc/queues/queue_s2_x5b.sh, GPU 3.

## VIEWS-P5 replication results (2026-10-17 04:35 UTC; Qwen3.6-35B-A3B, PopQA 1,500; results/x5/analysis_q36.log)
Accuracy: direct 28.9% (seed 2: 29.3%) @ 5 output tokens, recall-first 32.5% @ 85, thinking 33.9% @ 1,073 (37 of 1,500 thinking runs hit
the 4,096 cap, all wrong, so thinking is understated by at most 2.5 points); by popularity bin direct 24 / 14 / 17 / 33 / 56%, thinking
24 / 17 / 22 / 41 / 66%. Error kappa direct–direct **0.84**, direct–recall **0.74**; leak among agreeing answers 46.4% / 34.7%. Gate
(direct == recall → accept, else thinking): 33.7%, escalating 958 of 1,500 (64%) — no better than always-thinking (33.9%).
- **Kappa ≥ 0.6 holds again** (0.74). **Thinking ≤ +2 refuted for Qwen3.6** (+5.0 points at ≈ 200 × the tokens). Shared errors *are*
  concentrated in the least popular bins this time ([45, 41, 34, 31, 32]; view-specific [20, 32, 22, 45, 46]).
- Where thinking helps (direct wrong → thinking right, minus the reverse), by popularity bin least → most popular: Qwen3-8B
  11−14, 7−15, 11−11, 21−10, 38−10 (net −3, −8, 0, +11, +28); Qwen3.6 9−10, 18−10, 23−8, 33−8, 42−14 (net −1, +8, +15, +25, +28).
**Reading:** extra compute retrieves facts the model holds weakly (popular subjects: +28 net in the top bin for both models) and does
nothing for facts it lacks (net −3 / −1 in the least popular bin); a second view of the same model is wrong on the same items (kappa
0.74–0.91), so self-checks pass a third to two thirds of wrong answers. For missing knowledge the fix is a source of facts (retrieval),
not a self-check or more thinking — the same conclusion as U1's "facts before compute".
