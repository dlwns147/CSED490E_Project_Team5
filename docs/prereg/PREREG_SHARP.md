# Pre-registration SHARP: is training the quick answer a sharpening of what the base already samples?

Written 2026-10-30 20:4x UTC, before any base sample beyond seed 3 and before any held-out row of the trained word-problem model
(WP-RL, PREREG_WPRL.md). The seed-1–3 numbers below were computed first, offline, on stored rows (`python3.11 poc/analyze_sharp.py 3`);
they motivate the test and are not its result. Results go below.

**Why it could change the claim.** Plain RL on the non-thinking answer is the step that makes the peer-check cascade beat the default
on SQL (CV-1, +2.0 utility) and tool calls (TC-RL, +1.35). Two accounts of what that training does predict different things. (a)
*Sharpening*: RL with a verifiable reward reweights answers the base model already samples (Yue et al. 2504.13837: RL models lead at
small k, base models catch up at large k; "The Invisible Leash" 2507.14843: the trained support stays inside the base's). Then the
trained quick answer is right only where some base sample is, and since the cascade's gain G is linear in N's per-item answer
distribution (the bilinear account), training can give at most G(sharp_k), the cascade of the base fully sharpened onto its k-sample
coverage. That bound is computable *before training* from k base samples on a labelled dev split, so it would tell where training the
quick mode can pay (and where the quick mode needs answers it never samples: knowledge from the thinking mode, as distillation gives,
2504.13837). (b) *Expansion*: RL reaches answers the base does not sample (ProRL 2505.24864, prolonged RL). Then the cap is the oracle
(word problems: +5.83 [+4.33, +7.47] with the untrained peer) and no pre-training bound applies.

**What seeds 1–3 already say (exploratory).** Sharpening onto 3 base samples explains only 36% (SQL) and 33% (tool calls) of the
cascade gain from training: trained − sharp_3 cascade +0.90 [+0.15, +1.69] and +0.33 [+0.08, +0.59]; 14.2% / 7.2% of the trained
model's right samples are on items no base seed answers right. But the base's own coverage grows with k (2.7% / 0.8% of its right
samples are on items the other two seeds miss), so 3 samples cannot separate sharpening of low-probability answers from expansion.
On word problems, sharp_3 gives +0.92 [−0.12, +1.99] over SB→T→T (base +0.01), from quick right 30.1% to 39.5%.

**Run.** Base Qwen3-8B's quick answer at seeds 4–16 (k = 16 with the stored 1–3; the same prompts, T 0.7 / top-p 0.95 as the stored
rows and as the RL rollouts; per-item sampling seeds as every run): BIRD dev `SQL_ARMS=quick run_sql.py q8b <s>` (graded
`grade_sql.py q8b 4 … 16`), BFCL `TC_ARMS=quick run_tc.py q8b <s>` (`grade_tc.py q8b 4 … 16`), the four held-out word-problem sets
`run_form.py q8b formx <s>` (OptiBench third via `FORM_SUBSET=0/3`, BWOR, LogiOR, OptMATH); one RTX 3090 per job. Analysis
`python3.11 poc/analyze_sharp.py 16` (as above with K = 16; WP-RL's rows when they exist).

## Predictions (paired 95% intervals over items, seed means; utility = accuracy − 0.5 × ktokens)

- **SH-P1 (support):** on SQL and on tool calls, under 5% of the trained model's right samples (seeds 1–3) are on items no base seed
  1–16 answers right (seeds 1–3 only: 14.2% / 7.2%).
- **SH-P2 (the bound):** on SQL and on tool calls, trained cascade − sharp_16 cascade: lower bound ≤ 0 (training does not beat the
  base fully sharpened onto 16 samples).
- **SH-P3 (word problems, decided when WP-RL's evaluation lands):** the same two tests for q8bwp1. Before its rows exist, a dated note
  below states G(sharp_16) − SB→T→T on word problems as the predicted ceiling of WP-P2.
- Reported, not decided: base pass@1/3/8/16 per task; the share of training's gain that sharp_16 gives; the items the base never
  answers right in 16 samples where the default is right (what only thinking reaches; seeds 1–3: 19.1% SQL, 12.4% tool calls,
  23.9% word problems).

## Decision

- SH-P1 and SH-P2 hold on both → training the quick mode is a sharpening: its gain is bounded, before any training, by the base's
  k-sample coverage on labelled dev items (PROJECT / REPORT: a pre-training check for where the step pays). To go beyond it the
  quick mode needs answers it does not sample; the next test is distilling the default's right answers on the items outside the
  quick mode's coverage into it (the remaining headroom is the thinking-only share above).
- SH-P2 refuted on either (training beats sharp_16) → plain RL reaches quick answers 16 base samples do not show at this scale; the
  pre-training bound fails, the cap is the oracle's; reported with the share of new items.
- SH-P1 refuted, SH-P2 holds → new right items exist but carry little cascade value (they are where the default is already right).

Expected (not a rule): SH-P1 holds on tool calls, narrowly fails on SQL; SH-P2 holds on both, the bound giving 60–90% of training's
gain.
