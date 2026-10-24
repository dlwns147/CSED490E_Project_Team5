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

### Results HO-L (2026-10-23 00:1x UTC; `python poc/analyze_hol.py`, 45 cells, k = 30, 1,000 pilots per cell, λ = 0.5)
| choice of FF vs THINK | mean regret | Qwen3-8B geometry (3 cells) | Qwen3-8B BWOR (3 cells) |
|---|---|---|---|
| label-free pilot (agreement of F, F2, T) | 1.71 | keeps FF in 97% of pilots, 11.23 | keeps FF in 93%, 2.58 |
| labelled pilot (30 labels) | **0.57** | 0.12 | 0.63 |
| always FF / always THINK | 1.41 / 5.46 | | |
- **HOL-P1 refuted** (1.71 > 0.57 + 0.5; worse even than always using FF). **HOL-P2 half holds:** on Qwen3-8B geometry it keeps FF, as
  predicted (regret 11.2); but on BWOR it also keeps FF (93%, regret 2.58 > 2), against the prediction.
- Why: the triplet estimate assumes independent errors, but the cheap program and its second sample come from the same model and prompt
  and fail the same way, so their agreement inflates the cheap program's estimated accuracy — the same self-correlation that makes the
  free check leak. Where the recipe clearly wins (Qwen3-14B-AWQ, Qwen3-8B on OptiBench) it is near-perfect (regret ≈ 0, below the noisy
  labelled pilot), so it fails exactly where the choice matters.
- **Decision:** no label-free pilot; the recipe's held-out claim keeps the 30 labelled problems (HO-P). Answer to "is there a label-free
  signal for when the recipe does not pay?": not from agreement between the model's own runs.

## Addendum HO-P2 (2026-10-23 16:5x UTC, before computing; offline): the pilot against the fact-matched thinking arm
HO-TF / HO-TF2 show that HO-P's word-problem cells used a thinking arm without the library. **Re-run of HO-P / HO-R** with THINK :=
thinking with the same fact (formxt; geometry thinkfact; OptMATH unchanged: thinks for the development models, formxt for Qwen3.5-9B) and
every escalation going to that arm; OptiBench on the HO-TF third. Five policies (CHEAP, FF, FFR, THINK, FF-R0), 60 cells, λ = 0.5.
- **P2-1:** the 30-label pilot keeps mean regret ≤ 1.0.
- **P2-2:** THINK becomes the best policy in more cells than in HO-R (5 of 60), concentrated in the Qwen3 models' OptiBench / BWOR cells.
**Reading.** P2-1 → the deployable claim ("recipe by default, 30 labels to see where thinking with the fact is worth its tokens") survives
the fair baseline; otherwise the pilot needs more labels.

### Results HO-P2 (2026-10-23 19:0x UTC; `python poc/analyze_hop.py --repair --fair oss20 q14a q8b q35`, 60 cells, λ = 0.5)
| | best policy in (of 60) | fixed regret | 30-label pilot |
|---|---|---|---|
| FF-R0 / FF / FFR / THINK (fact-matched) | 24 / 10 / 9 / 17 | 3.32 / 3.79 / 3.73 / 4.35 | **0.85** (k = 10: 3.00; k = 100: 0.04) |
- **P2-1 holds** (0.85 ≤ 1.0). **P2-2 holds:** THINK (with the fact) is now best in 17 cells (5 in HO-R): Qwen3-8B 10 (BWOR 3, geometry
  3, LogiOR 2, OptiBench 2), Qwen3-14B-AWQ 6 (BWOR 3, OptiBench 2, LogiOR 1), gpt-oss-20b 1, Qwen3.5-9B 0.
- Against the fair baseline no fixed policy is good everywhere (best fixed: repair-first, 3.32), while 30 labels cut the regret to 0.85:
  **the pilot, not a fixed default, is the deployable part of the claim.** In Qwen3-8B's geometry + BWOR cells it loses 0.39 vs 11.9 for FF.

## Addendum HO-P3 (2026-10-24 21:1x UTC, before computing; offline): the self-review gate as a pilot policy
**Why it could change the claim.** The claim's deployable part is the 30-label pilot over five policies (HO-P2); the self-review gate
(HO-VR / VR2 / VR3) removes the Qwen3 models' loss but costs tokens where the check is already good (Qwen3.5-9B: +18–37%), so it was left
as "a pilot option". Whether the pilot can actually use it — pick it where it pays, avoid it where it costs — decides whether the recipe's
menu is {repair-first, fact-first, two-sample, think} or includes the gate. **Run:** `python poc/analyze_hop.py --repair --fair --gate
q14a q8b q35`: HO-P2's cells restricted to those with review rows for all 3 seeds (Qwen3-14B-AWQ and Qwen3-8B: OptiBench third, BWOR,
LogiOR, OptMATH, geometry; Qwen3.5-9B: OptiBench third, BWOR, LogiOR; 39 cells), sixth policy FF-R+F (a passing program is the answer only
if the 2k-token review says CORRECT, else thinking with the fact; review tokens counted), λ = 0.5.
- **P3-1:** the 30-label pilot over six policies keeps mean regret (vs the best of six) ≤ 1.0.
- **P3-2:** adding the gate pays: the six-policy pilot's realized utility beats the five-policy pilot's by ≥ +0.5 points on average over
  the 39 cells, and the gate is the best policy in ≥ 10 of them.
- **P3-3:** always using the gate has regret ≥ 1.5 (it is not a universal default; the pilot is still needed).
**Decision.** P3-2 → the recipe's escalation menu includes the gate and the claim's pilot bullet is restated over six policies;
otherwise the gate stays a named option outside the pilot.

### Results HO-P3 (2026-10-24 21:2x UTC; `python poc/analyze_hop.py --repair --fair --gate q14a q8b q35`, 39 cells)
| λ | best policy in (of 39): gate / THINK / FF-R0 / FF / FFR | always the gate | best other fixed | 30-label pilot, 6 policies | 6-policy − 5-policy pilot | best of 6 − best of 5 |
|---|---|---|---|---|---|---|
| 0 (accuracy only) | 16 / 12 / 7 / 1 / 3 | 1.69 | THINK 2.79 | 1.24 | +0.44 | +0.66 |
| **0.5** | **9 / 12 / 11 / 5 / 2** | **2.52** | THINK 3.99 | **0.96** | **+0.28** (worse in 22 cells) | +0.44 |
| 2 | 2 / 11 / 8 / 10 / 3 | 6.38 | FF-R0 2.89 | 1.04 | +0.09 | +0.10 |
(HO-P2 on its 60 cells reproduces unchanged: pilot 0.85.)
- **P3-1 holds narrowly** (0.96 ≤ 1.0). **P3-2 refuted** (+0.28 < +0.5; the gate is best in 9 < 10 cells). **P3-3 holds** (always the
  gate: 2.52 ≥ 1.5).
- **Reading.** Where the gate exists it is the best *fixed* policy at λ ≤ 0.5 (2.52 vs 3.99 for always thinking with the fact), best in
  Qwen3 OptiBench / LogiOR / geometry-14B cells and never for Qwen3-8B geometry (thinking with the fact stays 6–9 points ahead). But on
  top of the five-policy pilot it adds only +0.28: the cells it wins are cells the pilot already handled with THINK or repair-first at a
  similar utility, and a sixth option adds pick noise (the 6-policy pilot is worse in 22 of 39 cells, by little). Decision as registered:
  **the gate stays a named option outside the pilot** — the default for a leaky model without labels (it beats every other fixed policy
  there), not an addition to the 30-label pilot.
