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
