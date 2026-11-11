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
