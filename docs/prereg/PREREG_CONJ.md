# Pre-registration: conjoin the two translations the ladder already paid for (CONJ)

Written 2026-11-13 04:2x UTC. No solution set has been listed and no shared grid computed. The bucket sizes and thinking's accuracy in it
(below) were counted from the stored rows before writing this.

**Why.** The course method is the ladder trained quick translation (`lf`) → thinking translation (`gtrt`) → thinking (PREREG_GCLF). Its largest
remaining loss on GridPuzzle is the puzzle-seeds where both translations allow two or more solutions: 177 of 1,290 (13.7%), all sent to
thinking, which is right on only 54 of them (31%) at 14.8 ktok. Thinking fails there at search, not at reading (idea 34). The two translations
usually weaken a clue rather than misread one (idea 35: 155 of 170 several-solution thinking translations have no misread clue), so the right
grid is usually in both solution sets; two different translators weaken different clues, so the grids both allow may be exactly one. Taking it
costs no tokens, and the puzzle's one-solution guarantee is the same free check every other step uses.

**Related work.** Schrader et al. (2512.17093) choose one sampled reading per clue with the solver; Draft-and-Prune (2603.17233) drops
contradictory or ambiguous formalizations before voting on answers; LINC (2310.15164) votes over whole translations' answers. None intersects
the solution sets of translations that are each ambiguous. Our killed ideas differ: 29 checked each listed grid with the model (paid tokens),
38 chose one reading per clue among new samples (paid tokens, `gts`).

**Setup.** No model call. `poc/gp_conj.py run` (CPU job, sandboxed) lists up to 20,000 solutions of each count-2 `lf` and `gtrt` program of seeds
4–9 under the unchanged GP_SOLVE, maps every grid to the puzzle's own names (as `gp_score` compares them; checked on all 1,225 count-1 `lf`
rows: 0 mismatches with the stored scores) and keeps the grids in both sets. A set above the cap, or a program that fails to list, gives no
conjunction. Ladder: `lf` → `gtrt` → (both at count 2 and exactly one shared grid: accept it) → `think`; scoring v2; `python poc/gp_conj.py eval`;
bootstrap over puzzles, each puzzle's mean over seeds.

**Derivation of the prediction.** Let g = share of the bucket with gold in both sets, u = share with exactly one shared grid given gold in both.
From idea 35, g ≈ 0.75 (the trained translator may misread more than `gtrt`). u is the chance two weakened programs leave only gold in common;
compound clues are weakened by both models (idea 35), so u ≈ 0.35. A wrong single shared grid needs one program to exclude gold and still
share exactly one grid with the other; about 0.05 of the bucket. Per accepted right grid the ladder gains 100 × (1 − 0.31) + 0.5 × 14.8 ≈ 76;
per wrong one it loses 100 × 0.31 − 7.4 ≈ 23. GridPuzzle: 177 × (0.26 × 76 − 0.05 × 23) / 1,290 ≈ **+2.5** utility per puzzle-seed.
Mitra-Baral has only 19 such puzzle-seeds (of 564), so about +0.5.

**Predictions.**
- **CONJ-P1 (decides):** with − without the conjunction step, ladder utility: interval above 0 on GridPuzzle and lower bound above −2.0 on
  Mitra-Baral. I predict it holds on GridPuzzle (about +2.5).
- **CONJ-P2:** precision of the accepted shared grids at least 85% on GridPuzzle (at 31% thinking accuracy, the break-even precision is
  about 23%; 85% keeps the method's precision story). Reported with the number of thinking-right puzzle-seeds the step replaces.
- **CONJ-P3 (mechanism, reported):** gold in the `lf` set, in the `gtrt` set and in both; the share with exactly one shared grid; sets above
  the cap.

**Decision.**
- P1 holds → the conjunction step joins the course method (it costs no tokens); P2 failing is reported as its limit.
- P1 fails → the step stays out. If gold is in both sets but more than one grid is shared, the two translators weaken the same clues and a
  third reading is the next question; if gold is often missing from a set, the bucket is misreading, not weakness, and idea 35 does not carry
  over to the trained translator.

## Result (2026-11-13 04:2x UTC; `python poc/gp_conj.py eval`, job 1419495): P1 fails. The two translations drop the same constraint

| Seeds 4–9 | GridPuzzle (177 of 1,290 puzzle-seeds with both at count 2) | Mitra-Baral (19 of 564) |
|---|---|---|
| Gold in the `lf` set / the `gtrt` set / both | 133 / 168 / **128** | 14 / 16 / 14 |
| Shared grids: none / exactly one / two or more | 13 / **1** / 163 | 2 / 0 / 17 |
| **CONJ-P1:** with − without | **+0.0 [+0.0, +0.0]** (fails) | +0.0 |
| CONJ-P2: precision of accepted grids | 1/1 (thinking also right there) | none accepted |

- **Decision as registered:** the step stays out of the method.
- **What the derivation got right and wrong:** gold is in both sets as predicted (128 of 177 = 72%, predicted 75%), but the chance that only gold is
  shared was 1 of 128, not 0.35. The sets are nested: in 126 of the 128 the shared set equals the smaller set, and the two sets are often equal.
  The trained quick translator and the base thinking translator leave the same freedom, so a third reading from the same model family is unlikely
  to help either.
- **Not a property of the puzzles:** 47 of the 52 puzzles involved have a right one-solution translation in some stored run, so the puzzles are
  unique under a right reading; both translators drop the same constraint. Which one is read next (mechanism run, `python poc/gp_conj.py why`).
