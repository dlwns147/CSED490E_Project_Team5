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

### Results SHARP (2026-10-30 22:4x UTC; `python3.11 poc/analyze_sharp.py 16 > results/sharp.txt`; base seeds 1–16 complete: BIRD dev 1,528 / BFCL 3,482 / word problems 476 items, no failed requests)
| | SQL (BIRD dev) | tool calls (BFCL) | word problems (4 sets) |
|---|---|---|---|
| base quick pass@1 / 3 / 8 / 16 | 46.0 / 49.5 / 51.7 / 52.9% | 76.6 / 78.2 / 79.3 / 79.8% | 30.6 / 39.9 / 47.6 / 52.3% |
| base-never items (0 of 16) where the default is right at some seed | 16.3% | 11.1% | 14.3% |
| trained quick right (base) | 50.7% (46.1%) | 81.7% (76.6%) | (WP-RL pending) |
| **SH-P1** trained right samples on base-never items | **11.7%** (271 / 2,324) | **6.4%** (547 / 8,539) | — |
| cascade − SB→T→T: base / sharp_3 / sharp_16 / trained | +0.58 / +1.09 / +1.47 / +1.99 | +0.85 / +1.02 / +1.19 / +1.35 | +0.01 / +0.92 / **+3.06 [+1.82, +4.44]** / — |
| **SH-P2** trained − sharp_16 | +0.52 [−0.20, +1.26] | +0.16 [−0.07, +0.41] | — |
- **SH-P1 refuted on both** (11.7% and 6.4% ≥ 5%). **SH-P2 holds on both** by its rule (lower bounds −0.20 / −0.07), point estimates above zero.
- **The pre-registered reading of this branch ("new right items carry little cascade value") is wrong, and SH-P2's "bound" is a coincidence of
  sizes, not a bound.** Splitting each cascade's gain over the base by item (added after the run, `analyze_sharp.decompose`; contribution
  to the all-item mean, 95% intervals):

| | SQL: covered (809) | SQL: base-never (719) | tool calls: covered (2,778) | tool calls: base-never (704) |
|---|---|---|---|---|
| quick right, base → trained | 87.0 → 84.6% (−2.39 [−4.61, −0.16]) | 0 → 12.6% | 96.0 → 95.9% (−0.12 [−0.76, +0.50]) | 0 → 25.9% |
| accepted right / accepted wrong (points of all items), base → trained | 36.45 / 0.37 → 36.08 / 0.81 | 0 / 8.16 → 3.18 / 7.18 | 55.00 / 0.19 → 54.40 / 0.11 | 0 / 3.19 → 1.08 / 2.66 |
| trained cascade − base cascade | −0.35 [−0.83, +0.11] | **+1.76 [+1.19, +2.37]** | +0.01 [−0.16, +0.18] | **+0.49 [+0.33, +0.67]** |
| sharp_16 cascade − base cascade | +0.89 [+0.56, +1.26] | 0 | +0.34 [+0.20, +0.50] | 0 |
- **Mechanism.** All of plain RL's cascade gain is on items the base never answers right in 16 samples — new right answers the peer
  confirms (+3.18 / +1.08 points accepted right) and fewer agreed wrong ones — and none of it on the items the base already solves,
  where the trained model is not more consistent (SQL slightly less). Sharpening would gain on exactly the other items. So RL here is
  not a sharpening of the base's 16-sample coverage (contrary to 2504.13837 / 2507.14843 at this scale; whether the base would reach
  these answers at much larger k is not separable with 16 samples, but at the cost that matters — one quick sample — they are new).
- **Decision.** No pre-training bound from base samples: G(sharp_k) does not predict training's gain (it measures a different set of
  items). The two mechanisms are complementary: training gains on the base-never items; making the quick answer consistent would gain
  +0.89 / +0.34 more on the covered ones, which RL leaves. For word problems this sets two tests: whether a consistent (modal) quick
  program is worth it there (GREEDY below), and whether the thinking mode's programs reach base-never items further than RL (TD).
- **SH-P3 note (before any WP-RL evaluation row; training at round ~31 of 63).** sharp_16 on word problems: +3.06 [+1.82, +4.44] over
  SB→T→T. Given the decomposition, it is not WP-P2's ceiling. Predicted for q8bwp1 (stated now, decided with the pre-registered SH-P3
  tests): its cascade gain over the base cascade lies on the base-never items (that part's lower bound > 0 if WP-P3 holds), and its
  covered-item part has lower bound ≤ 0, as on SQL and tool calls.

## Addendum GREEDY (2026-10-30 22:4x UTC, before any run): the modal quick program, at one sample's cost

**Why it could change the claim.** The cascade's gain is linear in N's per-item answer distribution, so replacing each sampled quick
answer by its mode changes G by Σ_i [G_i(mode) − E G_i(sample)]. From the 16 base samples (the most frequent passing answer, at one
sample's tokens; offline, `scratchpad` estimate reproduced by `analyze_wprl.py` once rows exist): SQL −0.01 [−0.30, +0.30], tool calls
−0.06 [−0.18, +0.05], **word problems +1.15 [+0.38, +2.05]** over the sampled cascade, and the modal cascade − SB→T→T +1.16 [+0.02,
+2.41]. The difference has a reason: word-problem programs are diverse (pass@1 30.6% vs pass@16 52.3%; SQL 46.0 vs 52.9, tool calls
76.6 vs 79.8), so the mode is right far more often than a sample (42.4% vs 30.1%); on SQL and tool calls the mode adds few right answers
and the peer already confirmed those. Greedy decoding approximates the mode at one sample's cost; for single-attempt program synthesis
lower temperature is known to be better (2108.07732, 2207.11280; MBPP+ greedy ≈ sampling in 2505.12185), but not inside an agreement
gate, where the two members' modes may coincide on wrong answers. If it holds, the cheap path beats the default on word problems
without any training — the one task where it saved nothing.
**Run.** `run_form.py` with `FORM_TEMP=0` (the cheap arm's temperature; default 0.7 unchanged): Qwen3-8B formx, tag q8bg, and the peer
Qwen3.5-9B formx, tag q35g, seeds 1–3 (greedy is near-deterministic in vLLM; the seeds measure that), OptiBench third / BWOR / LogiOR /
OptMATH. Analysis `python3.11 poc/analyze_wprl.py q8bg` (and `--peer q35g`).
- **GR-P1:** q8bg quick right − q8b (sampled): lower bound > 0.
- **GR-P2:** q8bg → Qwen3.5-9B (sampled) → SB→T→T minus SB→T→T: utility lower bound > 0.
- **GR-P3:** that cascade − the sampled-N cascade: utility lower bound > 0.
- Reported: both greedy (peer q35g) against GR-P2's cascade; greedy vs the offline mode estimate; tokens and unfinished programs
  (greedy repetition); per benchmark.
**Decision.** P2 and P3 → on word problems the cheap path pays with a greedy quick program and no training (PROJECT / REPORT /
PROPOSAL; trained models are then also evaluated greedily, as a secondary arm); P1 holds, P3 refuted → the mode's gain does not survive
the gate (coinciding modes); P1 refuted → greedy is not the mode here.
Expected (not a rule): P1 holds (+6 to +12), P3 holds, P2 holds narrowly or is inconclusive.
**Note (2026-10-30 23:5x UTC, before GREEDY's analysis; predictions unchanged).** Offline, from the 16 base samples (scratch script, 4 random draws
of k seeds per problem-seed): the modal passing value of k quick programs as N, with the peer and SB→T→T as above. At k × the tokens
(self-consistency) it loses: − SB→T→T −0.19 [−1.08, +0.74] (k 3), −0.96 [−1.92, +0.03] (k 5), −2.03 [−3.10, −0.96] (k 8); at one
sample's tokens (what greedy would give if it found the answer mode) +0.62 / +0.65 / +0.87 [−0.17, +1.96] (k 3 / 5 / 8; quick right 36.5
/ 38.3 / 40.4%). So the addendum's +1.16 needs the mode of all 16 samples; sampling the mode costs more than it gains, and greedy is the
only way it could pay. Greedy decodes the most likely token path, not the most frequent value over programs, so GR-P1 is not implied.
Seen before the analysis (one printout of seed 1's rows, read for repetition): greedy programs reach the 8,192-token cap in 16 of 476
rows (sampled: 4 of 879, OptiBench whole), and seed 1's right rates per set were on the same lines (q8bg 54.0 / 18.3 / 13.0 / 17.0%).
