# PREREG_RULE3: keep a stated rule only if the quick translation, given it, reads the clue as the count admitted; fresh seeds 7–9, registered 2026-11-11 21:4x UTC, before any run

**Why.** PREREG_RULE2 carried the rules stated on the 250 dev puzzles into the unseen puzzles. That made the quick reading worse, not better.
- "N houses between" misread, from the first puzzle: 54% with the carried rules (107 of 198, 749 of 750 puzzle-seeds), 24% with rules learned from scratch on the same seeds, 13–16% with the hand fact.
- The errors go one way. "One house between" was written as a distance of 1 in 67 of 149 clues (from scratch: 36 of 170). "Two houses between" was written as 2 in 40 of 52 (from scratch: 33 of 74).
- **Root cause.** The dev library's first "between" rule is inverted: "a difference of 1 indicates one house between them, and a difference of 2 indicates two houses between them" (dev puzzle lgp-test-3x2-8, position 58). The pair it was stated from was right: the quick translation wrote `== 1`, the thinking translation `== 2`, and the count admitted the second. The rule writer, the same quick model without thinking, restated the pair in its own wrong reading. Right rules came later (position 117 on), so the carried library contradicts itself, and the quick translation follows the wrong one about half the time.
- In the seeds 1–6 runs from scratch, every first "between" rule was right. So the rule writer usually restates a pair correctly, but nothing checks that it did.
- **Diagnostic (`poc/rule_diag.py`, 2026-11-11 21:4x UTC, not registered).** The same 250 × 3 puzzles were translated again (first round only, same seeds) with four rule lists. "Between" clues misread:

| Rule list | Misread |
|---|---|
| as shown in trrw | 217/311 = 70% |
| without the one inverted rule | 144/332 = 43% |
| each rule text once | 208/311 = 67% |
| both changes | 188/319 = 59% |

  - The inverted rule is the main cause.
  - Length is not: removing repeats does not help, and it hurts once the inverted rule is gone, because the right rule's repeats are removed too. So no de-duplication is added.
  - Without the inverted rule, misreading still rises along the stream: 3/21 at positions 50–99, 74/142 at 200–249.

**The method (arms `trrv` and `trrvw`: `poc/run_zebra.py --zl <tag> trr <seed> --check [--warm q8b:1]`, as committed with this file).**
- As trr: when a puzzle's quick translation ends without a count of 1 and the thinking translation reaches one, the quick model states a rule for each clue the two read differently.
- **New, the check:** the rule is kept only if one quick translation of that same puzzle (first round, same prompt, the rules so far plus the new one) writes that clue as an expression that agrees with the thinking translation's on every assignment tried. This uses `grid_score.disagree`, the same evaluator that found the pair. Otherwise the rule is dropped (`rules_rejected`).
  - The check needs no label. Its reference is the reading the count admitted.
  - Its cost is one quick translation per stated rule, charged to the puzzle (`rule_tokens`).
- `trrvw`: the dev pass is `--zl q8b trr 1 --check` (the 250 dev puzzles, thinking rows `zl_q8b_trt_s1`), and the unseen runs start from its kept rules.
- `trrv`: the same check from an empty start, reported.

**Runs (Qwen3-8B, the 250 unseen main puzzles, `--skip 10`, fresh seeds 7, 8, 9).**
- `tr`, `trf`, `trt` and `think` (`--max_tokens 32000`) rerun on these seeds, settings as before; `trrv` and `trrvw`.
- Ladder: quick step → `trt` → `think`, every step paid; utility = 100·exact − 0.5·ktok; 95% bootstrap over puzzles, a puzzle's seeds together. `python poc/gp_eval.py --conv --rule3`.

**Predictions.**
- **RULE3-P0 (mechanism, checked on the dev pass before the unseen runs are read):** the kept dev library has no "between" rule that maps n houses between to a distance of n.
- **RULE3-P1 (decides):** ladder(`trrvw`) − ladder(`trf`): lower bound above −2.0 and point at or above 0, as RULE2-P1.
  - Derivation: from scratch, the rules sit at −0.2 and −0.3 against the fact (seeds 1–3 and 4–6), with about −1 of that from the cold start (RULE, positions 50–149). A library that is right from the first puzzle removes the cold start, and the check costs about 0.1–0.2 utility. That gives about +0.5.
  - Against that, the diagnostic leaves 43% first-round misreads without the inverted rule. In trrw, final programs misread at 0.8 times the first-round rate (56% against 70%), so about 35% is expected, above the fact's 19%. That pulls the estimate back toward −0.5.
  - Expected point between −0.5 and +0.5, interval half-width about 2. P1 is a close call.
- **RULE3-P2:** ladder(`trrvw`) − ladder(`tr`): interval above 0.
- **RULE3-P3:** "between" clues misread in `trrvw` programs, from the first puzzle: at most 30%. The same limit as RULE and RULE2; expected about 35%, so this may fail.

**Decision.**
- **P1 and P2 hold:** the ZebraLogic headline is restated without the hand-written fact. The quick translation reads with rules it stated itself, each kept only when it reproduces a reading the count admitted. The fact becomes an ablation.
- **P0 fails:** the check does not catch inverted rules, and the warm result is not interpreted.
- **P1 fails with P0 holding:** the hand fact stays, disclosed as dev-mined. The check is reported as a fix for inverted rules, together with what still separates the rules from the fact.

**Prior work.**
- HtT (2310.07064) keeps an induced rule when its predictions match labelled answers often enough.
- AutoManual (2405.16247) lets a builder agent manage rules from environment feedback, with case-conditioned prompting against hallucinated rules.
- RIMRULE (2601.00086, ACL 2026) proposes rules from failures and consolidates them under an MDL objective.
- Here the reference is a reading that the solver count admitted. The check asks whether the rule makes the cheap model reproduce that reading, so neither labels nor rewards are used.

**RULE3-P0 result (2026-11-11 22:4x UTC, the dev pass `zl_q8b_trrv_s1`, read before the unseen runs): holds.**
- The rule writer stated 35 rules on the 250 dev puzzles; the check kept 5 and rejected 30.
- Kept: four copies of "one house between means a difference of 2, not 1" (positions 58, 62, 94, 190) and one "two houses between means a difference of 3, not 2" (153). All right; no inverted rule.
- No inverted rule was stated at all in this pass, so the check did not have to catch one. Position 58, where the RULE2 dev pass stated the inverted rule, now states the right one; the rule list before it differs (position 31's rule was rejected), so the prompt differs.
- What the check did reject:
  - 22 of 30 are "between" rules. 18 of these were stated for a clue that has no "between" in it ("The person who has blonde hair is Arnold."), so giving the rule cannot change that clue's reading. The rule writer attaches the same generic rule to unrelated pairs.
  - 4 right "between" rules for real "between" clues (positions 210, 230 twice, 236) were rejected because the quick translation still misread the clue with the rule given.
  - The rest are restatements of what the quick reading already did ("X is Y" means equality, "directly left" means a difference of 1).
- Check cost on the dev pass: 13,920 tokens over 250 puzzles, about 0.03 utility per puzzle.
- So the check's observed work here is removing misattributed and ineffective rules. Whether it rejects an inverted rule when one is stated is read on the unseen runs (`rules_rejected` in `trrv`, `trrvw`).

## Result (2026-11-11 23:1x UTC): P0, P1, P2 and P3 hold. The ZebraLogic headline drops the hand-written fact.
`python poc/gp_eval.py --conv --rule3`, the 250 unseen main puzzles, fresh seeds 7–9, 750 puzzle-seeds.

| Quick step | Ladder accuracy | ktok | Quick count-1 precision | "Between" misread |
|---|---|---|---|---|
| `tr` (no fact, no rules) | 91.7% | 3.10 | 441/480 = 91.9% | 157/166 = 95% |
| `trf` (hand fact) | 94.3% | 2.26 | 558/583 = 95.7% | 46/271 = 17% |
| `trrv` (checked rules, from empty) | 95.5% | 2.30 | 572/590 = 96.9% | 42/244 = 17% |
| `trrvw` (checked rules, from the checked dev library) | 95.2% | 2.29 | 569/589 = 96.6% | 22/277 = 8% |

- **P1 holds:** `trrvw` − `trf` = +0.9 [−0.9, +3.0]. The point is above 0 and the lower bound above −2.0. This is non-inferiority within the registered margin, not a win over the fact.
- **P2 holds:** `trrvw` − `tr` = +3.9 [+1.4, +6.5].
- **P3 holds:** 8% misread, under 30% (I expected about 35%).
- **Reported:** `trrv` − `trf` = +1.2 [−1.0, +3.4]; `trrv` − `tr` = +4.1 [+1.9, +6.5].
- Rule calls, including the check, cost 0.10–0.11 ktok per puzzle. The check rejected 102 (`trrv`) and 152 (`trrvw`) stated rules.
- **No inverted rule was stated in any run** (dev pass or the six unseen runs). So the check was never asked to catch one. What these runs show is that the checked rules match the fact. They do not show that the check is what removed RULE2's failure, because RULE2's inverted rule may be a rare event.
- **Decision as registered:** the ZebraLogic headline is restated without the hand-written fact. The quick translation reads with rules it stated itself, each kept only when it reproduces a reading that the count admitted. The fact becomes an ablation.

## Addendum (2026-11-11 23:1x UTC, before running): ablation of the check on the same seeds
The result above leaves open whether the check matters. Two arms run without the check on seeds 7–9, with everything else unchanged:
- `trr`: from empty, as in PREREG_RULE.
- `trrw`: from the unchecked dev library `zl_q8b_trr_s1`, which holds the inverted rule (as in RULE2).

Predictions (paired, same seeds; `python poc/gp_eval.py --conv --rule3` prints them):
- **RULE3-A1:** `trrvw` − `trrw`: "between" misread at least 40% in `trrw` (RULE2: 56%), against 8% in `trrvw`. Utility point estimate above 0. RULE2 → RULE3 moved −0.4 → +0.9 against the fact, so I expect about +1.3 with a half-width of about 2. The interval may include 0, and that alone does not decide anything.
- **RULE3-A2:** `trrv` − `trr`: point at or above 0. Expected 0 to +1.5: from empty, the check removes misattributed rules, and RULE2's cold `trr` misread 27% against 17% here.

**Use.**
- If A1's misread prediction holds, the check is stated as the component that protects a carried library from a wrong rule, with the utility difference as measured.
- If `trrw` misreads under 40% on these seeds, the inverted rule is not reproduced, and the check is reported as a filter of misattributed rules only.

## Ablation result (2026-11-11 23:5x UTC): A1 holds, A2 fails. The check protects a carried library; from an empty start it adds nothing.
Same seeds 7–9, 750 puzzle-seeds.

| Quick step | Ladder accuracy | ktok | "Between" misread | Rules shown (mean) |
|---|---|---|---|---|
| `trr` (unchecked, from empty) | 95.6% | 2.15 | 35/270 = 13% | 13.0 |
| `trrv` (checked, from empty) | 95.5% | 2.30 | 42/244 = 17% | 7.3 |
| `trrw` (unchecked, from the unchecked dev library) | 94.0% | 2.75 | 100/200 = 50% | 48.8 |
| `trrvw` (checked, from the checked dev library) | 95.2% | 2.29 | 22/277 = 8% | 7.8 |

- **RULE3-A1 holds.**
  - The unchecked dev library misreads "between" in 50% of clues (at least 40% predicted), against 8% with the checked one. RULE2's failure reproduces on fresh seeds.
  - Utility: `trrvw` − `trrw` = +1.4 [−0.9, +3.7], point above 0. The interval includes 0.
  - As registered, the check is stated as the component that keeps a carried library from a wrong rule.
- **RULE3-A2 fails.** From empty, `trrv` − `trr` = −0.2 [−1.6, +1.1], and the point is below 0. Without a carried library, the check adds nothing measurable here.
- **Cold, unchecked rules on these seeds:** +1.4 [−0.7, +3.7] against the fact and +4.3 [+2.3, +6.6] against no fact. On seeds 1–3 and 4–6 the same arm was −0.2 and −0.3 against the fact, so across nine seeds the cold rules are level with the fact.
- **What the check changes in the dev library.** The unchecked library carries 40 lines, 14 distinct, one of them inverted. The checked one carries 5 lines, all right. With the unchecked library, the quick prompt shows 49 rules on average; with the checked one, 8.
