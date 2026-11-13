# Pre-registration: the clue check on top of the check-trained translator (GCLF)

Written 2026-11-13 02:1x UTC. No check has been run on these programs. The plain-ladder numbers below are already known (PREREG_GRLLF); the check rows are not.

**Why.** The grid method has two parts that were tested apart. RL with the count as reward (PREREG_GRLLF, tag `lf`) trains the quick translation; the clue check (PREREG_GC) re-reads each one-solution grid against the clues. The course report must state one method, so the two must be measured together. The open question is whether training on the count already removes the errors the clue check catches. RL keeps a misreading only when it still gives one solution on many puzzles, so its remaining errors may be readings the checker shares.

**What is known before the run.**
- Plain ladder with `lf` (seeds 4–9): GridPuzzle 75.8% at 14.00 ktok (utility 68.8), Mitra-Baral 90.2% at 6.85 (86.8). Thinking: 63.4% at 11.53 (57.6) and 87.1% at 6.31 (83.9).
- `lf` count-1 precision 93.0% (GridPuzzle, 802 programs, about 56 wrong) and 94.3% (Mitra-Baral, 423, about 24 wrong).
- The clue check on base programs (PREREG_GC, seeds 1–3): wrong quick translations flagged 28/39 (GridPuzzle) and 12/14 (Mitra-Baral); wrong thinking translations only 6/22 and 1/2; right ones flagged 9/571 (GridPuzzle, both steps) and 1/360 (Mitra-Baral). About 0.86 ktok per check.

**Setup.** Qwen3-8B, PREREG_GC's whole-grid thinking check unchanged (8,000 tokens, temperature 0.7, seed fixed per program).
- `python poc/gp_check.py run q8bgrllf0|q8bgrllf1 <gridpuzzle|lgp> checkt --seeds 4,5,6,7,8,9`: every count-1 `lf` program.
- `python poc/gp_check.py run q8b <gridpuzzle|lgp> checkt --seeds 4,5,6,7,8,9 --trs gtrt --label checkt_s49`: every count-1 base `gtrt` program of those seeds.
- Checked ladder: `lf` → base `gtrt` → `think`; a count-1 step whose grid gets a flag goes on; every step and every check paid; scoring v2. `python poc/gp_eval.py --gclf`. Bootstrap over puzzles, each puzzle's mean over seeds.

**Derivation of the prediction.** Gain ≈ (wrong count-1 rate) × (catch rate) × (chance the next steps are right) − (check tokens on every count-1 step) − (escalation tokens). GridPuzzle: 4.3% × about 0.5 × about 0.5 ≈ +1.1 accuracy points; about 0.85 checks per puzzle-seed × 0.86 ktok × 0.5 ≈ −0.4; escalation about −0.2. Net about **+0.5**, against an interval half-width near 1. The same check on 32B's precise translators tied on GridPuzzle (GC32: +0.5 [−0.7, +1.6]).

**Predictions.**
- **GCLF-P1 (decides):** checked − plain ladder utility, interval above 0 on GridPuzzle and lower bound above −2.0 on Mitra-Baral. *I predict it fails on GridPuzzle* (point about +0.5, interval including 0).
- **GCLF-P2 (mechanism):** the share of wrong `lf` count-1 programs the check flags is below base `gtr`'s 28/39 (72%) on GridPuzzle; I predict about 45%, between base `gtr` (72%) and base `gtrt` (27%). Reported with an exact binomial interval; compared with base `gtr` by Fisher's exact test.
- **GCLF-P3:** precision of answers accepted before thinking, checked ladder, at least 95% on each set (reported).
- **GCLF-P4:** checked ladder − thinking, reported on both sets.

**Decision.**
- P1 holds → the course method is the trained translator with the clue check; that number replaces the GridPuzzle row of the report.
- P1 fails → the method is the trained translator alone and the check stays an option for untrained translators (PREREG_GC). If P2 also holds, the reason is that RL on the count leaves errors the same model's check shares.

## Result (2026-11-13 03:1x UTC; `python poc/gp_eval.py --gclf`, jobs 1415914–1415915, 2,447 checks): P1 fails as predicted, P2 holds. The method is the trained translator alone

| Seeds 4–9 | GridPuzzle (1,290 puzzle-seeds) | Mitra-Baral (564) |
|---|---|---|
| Ladder with `lf` | 75.8% at 14.00 ktok, utility 68.8 | 90.2% at 6.85, 86.8 |
| Same ladder with the clue check | 76.7% at 15.46, 69.0 | 92.7% at 7.92, 88.8 |
| Thinking | 63.4% at 11.53, 57.6 | 87.1% at 6.31, 83.9 |
| **GCLF-P1:** checked − plain | **+0.2 [−0.4, +0.9]** (fails) | +1.9 [+0.2, +4.6] |
| **GCLF-P2:** wrong `lf` count-1 flagged | **22/56 = 39% [26, 53]** vs base `gtr` 28/39 = 72%, Fisher p = 0.003 (holds) | 12/24 = 50% [29, 71] vs 12/14, p = 0.04 |
| Right `lf` count-1 flagged | 6/746 | 0/399 |
| GCLF-P3: precision accepted before thinking | 92.1% → 94.9% (just under 95%) | 94.0% → 96.7% |
| GCLF-P4: checked ladder − thinking | +11.4 [+7.6, +15.4] | +4.9 [+1.0, +9.2] (plain: +2.9 [−1.8, +7.8]) |

- **Decision as registered:** P1 fails on GridPuzzle, so the course method is the trained translator alone; the clue check stays an option for untrained translators (PREREG_GC). On Mitra-Baral the check still pays and turns a tie with thinking into a win; this is reported, not used to change the decision.
- **Why (P2):** after RL on the count, the check catches 39% of wrong one-solution translations against 72% before training. RL removes the errors the same model can see when re-reading; the ones left are readings it shares.
- **What the remaining errors are (exploratory, read after the result):** half of `lf`'s wrong one-solution programs have more expressions than the puzzle has clues (28/56 GridPuzzle, 14/24 Mitra-Baral), against 18/746 and 8/399 of right ones. The extra expression is a constraint no clue states, which pins the count to 1 (gp-12703: `p['pieces:coffee table'] == p['woods:mahogany']`; gp-3720: `p['years:1921'] == p['paintings:Orange Sky']`, which clue 6 forbids). The base translator does this too, in 29/88 wrong and 24/412 right. Rejecting such programs at the gate does not pay (ladder −0.9 [−2.1, +0.2] and −1.0 [−3.0, +0.7]; with the clue check −1.2 and −1.5): of 46 flagged GridPuzzle programs, 10 wrong ones become right further down but 12 right ones become wrong, because an extra expression is as often a correct deduction as an invented one, and the later steps fail on these puzzles. The fix belongs in training: a reward that also requires one expression per clue (free, label-free) would stop the count reward from paying for invented constraints. Related: FormaRL (check-only autoformalization rewards are hacked unless a consistency check is added).
