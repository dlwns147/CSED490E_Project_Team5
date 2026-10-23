# Pre-registration MODEL: when does "fact first, think only where the check fails" win, and can a small pilot tell?

Written 2026-10-18 17:36 UTC, before computing. Offline, on stored rows only. Results go below.

**Why.** Across many cells (model × benchmark × seed) the recipe sometimes matches always-thinking at a fraction of the tokens
(Qwen3-32B on X6), sometimes loses points (Qwen3-4B), sometimes wins (Qwen3-32B with the two-program check). A practitioner facing a new
task / model needs to know which policy to run without running everything. Exact decomposition: FF − always-think =
P(pass) × [P(fact program right | pass) − P(thinking right | pass)]: the recipe loses only on items the check passes, and only if
thinking would be right more often there than the cheap program. Both terms are estimable from a few labelled items.
**Cells.** X6 (NL4OPT + IndustryOR, 345 items): Qwen3-1.7B / 4B / 8B / 14B-AWQ / 32B-AWQ, gpt-oss-20b, Qwen3.6 (80k thinking) × seeds
1–3 = 21 cells; U1 suites (geometry 108, optimization 100): the same 7 models × 2 domains × cure seeds 1–3 = 42 cells.
Policies: CHEAP (fact program only), FF (fact program; thinking if its check fails), FFR (fact program; thinking unless it runs AND a
second fact sample agrees), THINK (always thinking). Utility = accuracy (points) − λ × output tokens (thousands), λ ∈ {0, 0.5, 2}.
**Pilot rule.** Label k random items of the cell (and run every policy on them), pick the policy with the best pilot utility, report
the regret = best full-cell utility − full-cell utility of the pick, averaged over 1,000 pilots. poc/analyze_policy_model.py.
- MODEL-P1 (identity check): the decomposition reproduces FF − THINK exactly in every cell (a harness sanity check).
- MODEL-P2: with k = 30 labelled items the mean regret is ≤ 1.0 point (λ = 0.5) over all 63 cells; with k = 10 it is ≤ 3 points.
- MODEL-P3: no single fixed policy is best in ≥ 80% of the cells at λ = 0.5 (the choice is task- and model-dependent).

## Results (2026-10-18 17:40 UTC; results/policy_model.log; 63 cells: 21 X6 + 42 U1)
- **MODEL-P1 holds** (decomposition reproduces FF − THINK to 0.000000 points in every cell).
- Best policy per cell (λ = 0 / 0.5 / 2 points per 1k tokens): FF 33 / 35 / 34 cells, FFR 17 / 16 / 7, THINK 8 / 4 / 3, CHEAP 5 / 8 / 19.
- **MODEL-P3 holds** (no policy is best in ≥ 80% of cells; FF in 56%).
- Regret (points of utility lost to each cell's best policy), λ = 0.5: always CHEAP 9.9, **always FF 1.36**, always FFR 1.48, always THINK 8.42
  (λ = 0: FF 1.75, THINK 5.75 — always thinking is far from best even when tokens are free).
- **MODEL-P2 holds:** picking the policy on k labelled items: k = 10 → 2.04, **k = 30 → 0.61**, k = 100 → 0.10 (λ = 0.5); similar at λ = 0 / 2.
  (The pilot's own cost — labels and running every policy on k items — is not counted.)
**Reading:** "fact first, think only where the check fails" is the best single default across models, tasks and seeds (regret 1.4
points, vs 8.4 for always thinking); the decomposition says when it loses (on items the check passes, if thinking is right there more
often than the cheap program), and 30 labelled problems of a new task are enough to choose the right variant with 0.6 points of regret.

## Addendum HO-P (2026-10-22 23:1x UTC, before computing; offline): does the 30-label pilot hold on the held-out benchmarks?
**Why.** The recipe loses for Qwen3-8B on held-out geometry and BWOR. The claim a practitioner can use is "run the recipe, unless a small
labelled pilot says otherwise"; MODEL-P2 (regret 0.61 points with k = 30) was measured on development cells only (MAMO: 0.8–1.4).
**Cells** (45): gpt-oss-20b, Qwen3-14B-AWQ, Qwen3-8B × seeds 1–3 × the recipe's arm per held-out benchmark — OptMATH (mined example
`mips`, THINK `thinks`), OptiBench / BWOR / LogiOR (label-free library `formx`, THINK `thinkfree`), geometry (helpers + hint, MR check,
THINK `think`). Same policies (CHEAP, FF, FFR with the next seed's cheap program as the second sample; geometry FFR = both pass MR and
agree on the six inputs), same pilot rule and λ ∈ {0, 0.5, 2}. `poc/analyze_hop.py`.
- **HOP-P1:** mean regret of the k = 30 pilot ≤ 1.0 point at λ = 0.5 (k = 10: ≤ 3).
- **HOP-P2:** in Qwen3-8B's geometry and BWOR cells the k = 30 pilot avoids the recipe's loss: its mean regret there ≤ 2 points, while
  always using FF loses ≥ 5.
- **HOP-P3:** FF stays the best single fixed policy at λ = 0.5 (lowest mean regret of the four).
**Decision:** P1 + P2 → the claim becomes "the recipe by default; 30 labelled problems of a new task tell when to think instead", with the
held-out regret; otherwise the losing cells stay a stated limit without a remedy.

### Results HO-P (2026-10-22 23:1x UTC; `python poc/analyze_hop.py`, 45 held-out cells, 1,000 pilots per cell)
| λ | best policy per cell (FF / FFR / THINK / CHEAP) | pilot regret k = 10 / 30 / 100 | always FF / FFR / THINK / CHEAP | Qwen3-8B geometry + BWOR: k = 30 pilot vs always FF |
|---|---|---|---|---|
| 0 | 20 / 20 / 5 / 0 | 3.16 / 0.88 / 0.08 | 2.55 / 1.56 / 5.11 / 14.07 | 0.94 vs 10.17 |
| **0.5** | 25 / 13 / 7 / 0 | 2.81 / **0.87** / 0.05 | **1.80** / 2.09 / 5.86 / 11.38 | **0.74 vs 7.83** |
| 2 | 34 / 3 / 4 / 4 | 2.35 / 1.11 / 0.07 | 0.60 / 4.72 / 9.14 / 4.33 | 1.32 vs 1.86 |
- **HOP-P1 holds** (k = 30: 0.87 ≤ 1.0; k = 10: 2.81 ≤ 3). **HOP-P2 holds** (Qwen3-8B's losing cells: 0.74 ≤ 2 with the pilot, 7.83 ≥ 5
  always using FF). **HOP-P3 holds** (FF has the lowest fixed regret at λ = 0.5: 1.80; at λ = 0 the two-program check FFR is lower, 1.56).
- THINK is the best policy in 7 of 45 cells at λ = 0.5 — all six Qwen3-8B geometry / BWOR cells and one more (Qwen3-8B LogiOR seed 3).
- **Decision:** the claim becomes "the recipe by default; 30 labelled problems of a new task tell when to think instead" — on the
  held-out benchmarks this choice costs 0.87 points of utility on average and removes Qwen3-8B's losses (0.74 vs 7.83).

## Addendum HO-L (2026-10-23 00:1x UTC, before computing; offline): can the pilot choose without labels?
**Why.** HO-P needs 30 labelled problems. The user's open question is a *label-free* signal for when the recipe or a fact does not pay.
The pilot already runs thinking on its 30 items; the answers of three runs (cheap program F, a second cheap sample F2, thinking T) can
estimate each run's accuracy from agreement alone (triplet method: if wrong answers rarely coincide, P(X = Y) ≈ a_X·a_Y, so
a_F = √(A_FF2·A_FT / A_F2T), a_T = √(A_FT·A_F2T / A_FF2); Platanios et al. 2014, Fu et al. 2020).
**Rule (label-free pilot, choice FF vs THINK).** On k = 30 random items of a cell, on the items whose cheap program passes its free check
(share p), compute the three agreement rates (answers equal within the grader's tolerance; geometry: equal outputs on the six inputs; a
missing answer agrees with nothing), estimate a_F and a_T (clipped to [0, 1]; any agreement rate 0 → FF), and pick FF iff
100·p·(a_F − a_T) + λ·(mean THINK tokens − mean FF tokens)/1000 ≥ 0 (tokens observed on the pilot, no labels). λ = 0.5.
Compared with the labelled pilot restricted to {FF, THINK}, always FF and always THINK; regret against the better of FF and THINK on the
full cell; 1,000 pilots per cell; the 45 HO-P cells. `poc/analyze_hol.py`.
- **HOL-P1:** mean regret of the label-free pilot ≤ the labelled pilot's + 0.5 points.
- **HOL-P2 (expected failure):** in Qwen3-8B's geometry cells it mostly keeps FF (regret ≥ 5): its leaked programs are right on the given
  input, so they agree with thinking there; in Qwen3-8B's BWOR cells (wrong numbers rarely coincide) it picks THINK (regret ≤ 2).
**Reading.** P1 + P2 → a label-free pilot works where wrong answers disagree (word problems) and fails exactly where the free check
leaks by construction (edge cases absent from the input), so labels are needed only there; P1 failing → keep the 30 labels.
