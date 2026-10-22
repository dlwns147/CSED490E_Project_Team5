# Final report: draft outline (2026-10-22, Slurm side; format, length and deadline still to be decided by the team)

Purpose: one argument for the course report, built from the held-out evidence, with every number given with its tokens and, for the
held-out comparisons, a 95% interval over problems. Details stay in PROPOSAL.md, FINDINGS.md and docs/prereg/.

## The claim (one sentence)
For computational problems solved by LLM-written programs on one 24 GB GPU, giving the missing fact first and paying for thinking only when a
free check visibly fails is as accurate as always thinking at a fraction of its tokens, as long as the check does not leak; the
check's leak, not problem difficulty, decides where thinking should go.

## Sections (proposed)
1. Problem and setup: computational geometry + optimization; models that fit one RTX 3090 (gpt-oss-20b, Qwen3-14B-AWQ, Qwen3-8B; larger
   ones only as references); accuracy with output (and input) tokens; strict graders.
2. The recipe (program → fact → free check → think on failure → reuse) and why each step: findings 1–5 in one paragraph each, with the
   example from PROPOSAL.md.
3. Development result: U1 — 87% @ 2.5k vs difficulty-based allocation 74% @ 4.1k (208 problems × 3 models × 3 seeds).
4. **Held-out tests (the core of the report).** Table below; then where it fails and why (check leak: geometry edge cases for Qwen3-8B,
   running-but-wrong programs on BWOR / LogiOR), and what does not rescue it (brute force, resampling, model-written edge-case tests).
5. Facts without a human: the label-free library (23 / 25 cells; up to +34 points on the first program); when a fact pays (usage-crash
   census; the "do not add" side untested).
6. Baselines on the same harness: STORM-4B, ORLM-8B, self-consistency, CodeT, DRoC, Snell-style allocation, AdaptThink.
7. Where the recipe stops: short-answer competition math (text + thinking, program as a check), formal proofs (a specialized prover),
   the weakest model's check leak.
8. Limits and threats: small margins (ties reported as ties), thinking budget caps, label noise (MAMO), our own generated tasks,
   contamination, one model family + gpt-oss, a 4-bit 14B.

## Held-out table (fact-first-then-think minus always thinking; seed means; 95% CI; FF output tokens as a share of always thinking's, then input + output)
| benchmark (problems) | gpt-oss-20b | Qwen3-14B-AWQ | Qwen3-8B |
|---|---|---|---|
| OptMATH (100), mined example | +5.7 [+0.3, +11.0], 68% / 81% | 0.0 [−3.7, +4.0], 83% / 93% | +1.7 [−1.3, +5.0], 88% / 97% |
| OptiBench (605), no fact | +1.8 [+0.3, +3.4], 56% / 64% | +11.0 [+8.7, +13.3], 52% / 56% | −0.4 [−2.3, +1.4], 64% / 67% |
| OptiBench, label-free library | +4.1 [+2.1, +6.1], 46% / 67% | +15.6 [+12.9, +18.3], 28% / 37% | +5.2 [+2.6, +7.6], 36% / 43% |
| BWOR (82), no fact | +1.2 [−4.5, +6.9], 53% / 61% | +1.2 [−4.9, +7.3], 75% / 80% | −8.1 [−13.4, −3.3], 74% / 78% |
| LogiOR (92), no fact | −1.1 [−6.9, +4.7], 63% / 71% | −2.2 [−5.4, +1.8], 88% / 92% | −2.9 [−6.5, +0.4], 91% / 94% |
| LogiOR, label-free library | −1.1 [−6.9, +4.0], 59% / 80% | +10.1 [+4.3, +15.9], 74% / 85% | −2.2 [−6.9, +2.5], 80% / 90% |
| held-out geometry (96 items), needed helpers + hint | +5.9 [+3.5, +8.7], 48% | +7.6 [+4.5, +11.5], 34% | −14.2 [−19.8, −9.4], 46% |
Sources: results/x3/ho*_analysis.log, results/x3/ho2_*_analysis.log, results/x3/input_tokens_analysis.log, PREREG_HOG.md / PREREG_HOGC.md.
Reading: the two stronger models never lose to always thinking (ties or wins) at 28–88% of its output tokens; Qwen3-8B wins only with the
library on OptiBench and loses where its free check leaks most (geometry edge cases; BWOR, where 75% of check-passing programs are wrong).

## Decisions for the team
- Format (course template? paper style, slides-only?), length, language (English / Korean), deadline.
- Whether proofs and competition math stay as a short "where it stops" section or go to an appendix.
- Whether to spend GPU time on the one open question that could change the claim: the "do not add a fact" side (needs a strong,
  rarely-crashing model on a new benchmark; gpt-oss-120b on an A100 / H200).
