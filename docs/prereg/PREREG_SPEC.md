# PREREG_SPEC — does check-and-escalate add on top of a specialist? (registered 2026-11-22 07:40 UTC)

**Why (user 11-22: "are loop dealing testing suggesting important problems?").** On clean OptiBench a fine-tuned 14B specialist
(LLMOPT-14B, official checkpoint and prompts, PREREG_TYPED registration I) beats Qwen3-8B's full method, and on SQL published 7B
specialists lead by about 7 points. If the method only helps general models, its scope is narrow; if a free check plus escalation also
improves a specialist, the method is complementary to specialists. Prior work: FrugalGPT / AutoMix (cascades by a learned or
self-verified score, no execution evidence), LLMOPT's own self-correction (the same model judges itself). New here: a cross-family
execution-agreement check on a specialist's answer, escalation priced in tokens.

**Arms (offline on stored rows; no row of the combination has been computed; per-arm accuracies were seen in registration I).**
Held-out sets NL4OPT + IndustryOR, OptMATH (seed 1 own program), OptiBench, BWOR, LogIOR; seeds 1–3; peer = gpt-oss-20b.
- SPEC: LLMOPT-14B alone (its full pipeline with self-correction).
- FULL: our method for gpt-oss-20b (typed → own → repair → peer agreement with Qwen3-8B → thinking; PREREG_TYPED J).
- SPEC+C: LLMOPT's answer; accepted if it prints a value and gpt-oss-20b's quick program prints the same value; otherwise gpt-oss-20b
  thinking. Tokens: LLMOPT's + gpt-oss-20b's quick program + thinking when escalated.
- SPEC+C8: the same with Qwen3-8B (its quick program as the check, its thinking as the escalation), for the Qwen3-8B user.
**Predictions.** S-1: SPEC+C − SPEC > 0 in utility on the held-out pool (rate 0.5, output tokens). S-2: SPEC+C − FULL ≥ 0 on the pool
(the specialist's answer is a better first step than gpt-oss-20b's own program). S-3 (per set, descriptive): SPEC+C ≥ SPEC on every set.
**Decision rule.** S-1 holds (Holm over S-1, S-2, S-1 for SPEC+C8; clustered bootstrap by problem; raw AND audited labels both) → the
report states the method is complementary to the specialist and adds the SPEC+C row; S-1 fails on either label set → the report states
the method's scope as general models. Cost views 0.25–2 and size-weighted reported as sensitivity.

## Result (2026-11-22 07:41 UTC; python3 poc/analyze_spec.py, raw and OR_CLEAN=1)
Held-out pool (3,472 problem × seed rows raw; 2,728 audited), utility at rate 0.5, clustered by problem, Holm over three:
| test | raw labels | audited labels |
|---|---|---|
| S-1 SPEC+C − SPEC (gpt-oss-20b checks and escalates) | **+11.3 [+9.5, +13.1] holds** | **+11.0 [+8.9, +13.2] holds** |
| S-2 SPEC+C − FULL (gpt-oss-20b's own method) | +0.0 [−0.7, +0.8] not shown | −0.2 [−1.0, +0.6] not shown |
| S-1 SPEC+C8 − SPEC (Qwen3-8B checks and escalates) | −0.2 [−1.9, +1.5] not shown | −0.7 [−2.7, +1.2] not shown |
Accuracy / tokens (raw): LLMOPT 58.2% at 4.0k; LLMOPT + gpt-oss-20b check 70.6% at 6.2k; gpt-oss-20b full method 69.0% at 3.2k;
LLMOPT + Qwen3-8B check 61.3% at 10.6k. SPEC+C − SPEC is positive on every set with both label sets (audited OptiBench +4.0 [+1.6, +6.5])
and at every rate and cost view (+7.6 to +12.1). With Qwen3-8B the check helps on NL4OPT + IndustryOR, BWOR, LogIOR and hurts on
OptiBench (−5.7 raw, −8.1 audited): its thinking (10–12k tokens) is weaker than the specialist there.
**Verdict (registered rule).** The method is complementary to the specialist when the checker / escalation model is at least as strong
as the specialist off its training distribution (gpt-oss-20b): +11 utility over LLMOPT on both label sets. It is not complementary with
Qwen3-8B as checker. And the specialist is not a better first step than gpt-oss-20b's own program (S-2 ≈ 0): the gain over LLMOPT is the
check and gpt-oss-20b's thinking, not LLMOPT's answer.

## Addendum SQL (registered 2026-11-22 08:44 UTC, before any Arctic row): the same test on text-to-SQL with Arctic-Text2SQL-R1-7B
Specialist: Snowflake/Arctic-Text2SQL-R1-7B (arXiv 2505.20315; reports BIRD dev 68.9%, Spider test 88.8%), greedy, its own evaluation
inputs (OmniSQL's pre-processed prompts, seeklhy/OmniSQL-datasets data/dev_bird.json and data/test_spider.json), poc/run_spec_sql.py,
graded by poc/grade_sql.py on our items and gold. Sets: Spider test (all 2,147; never used for a decision, as in FINAL) and BIRD dev
(the 1,354 questions the 2025-11-06 correction left unchanged; the other 180 are skipped). Stored rows for the rest (FINAL tags).
Arms per checker m ∈ {Qwen3-8B, gpt-oss-20b}: SPEC = Arctic alone; SPEC+C = Arctic's query kept if it passes the free check (runs, ≥ 1
row) and m's quick query returns the same rows, else m's default (SB → T → T); FULL = m's FINAL cascade (quick query + peer, else default).
- **SQ-1** SPEC+C − SPEC > 0 (utility at rate 0.5) on Spider test, for each checker. **SQ-2** (descriptive) the same on BIRD dev's 1,354.
- **SQ-3** SPEC − FULL on Spider test (is the specialist ahead of our pipeline, as published numbers say?).
Holm over SQ-1 (two checkers) and SQ-3; clustered by question. Decision: SQ-1 holds for a checker → the report says the method adds to
the SQL specialist with that checker; fails → the specialist alone is the recommendation for SQL. Smoke: 20 questions, read failed rows.

### Addendum SQL result (2026-11-22 08:58 UTC; FINAL_SUFFIX=sp / "" python3 poc/analyze_spec_sql.py)
Harness: Arctic's 2,147 Spider-test queries all extracted and finished; 85.9% right on all of them (card 88.8%); failures are wrong
values (283 pass the check but are wrong) and empty results; BIRD dev unchanged questions 69.1%. Scored on the questions with FINAL rows
(Spider 1,741, BIRD 1,351), utility at rate 0.5, Holm over three:
| test | Spider test | BIRD dev (1,351, descriptive) |
|---|---|---|
| SQ-1 SPEC+C − SPEC, Qwen3-8B checks / escalates | **−7.70 [−9.31, −6.07] not shown** | −4.22 [−6.24, −2.21] |
| SQ-1 SPEC+C − SPEC, gpt-oss-20b checks / escalates | **−8.21 [−9.86, −6.53] not shown** | −6.38 [−8.64, −4.15] |
| SQ-3 SPEC − FULL (Qwen3-8B cascade) | **+9.84 [+8.03, +11.62] holds** | +5.85 [+3.59, +8.11] |
Accuracy / tokens (Spider): Arctic 86.7% at 0.54k; Arctic + Qwen3-8B check 79.3% at 1.02k; our Qwen3-8B cascade 76.9% at 0.47k.
**Verdict (registered rule): the method does not add to the SQL specialist; the specialist alone is the recommendation for SQL**, and it
beats our pipeline by +9.8 utility on Spider test. Mechanism: a disagreement sends the question to the general model's default, which is
weaker than Arctic on SQL (Arctic is kept on 71–75% of Spider questions; on the rest the escalation is right less often than Arctic was).
With the word-problem half: the check pays on top of a specialist only where the escalation model is stronger than the specialist on
that distribution (gpt-oss-20b off LLMOPT's training data: +11); where the specialist is stronger in-domain (SQL), escalating to a
general model costs 7–8 points.
