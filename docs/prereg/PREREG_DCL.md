# Pre-registration: the distinctness a disjunctive clue implies, added only when the literal reading leaves several solutions (DCL)

Written 2026-11-13 04:4x UTC. The rule below was found and first measured on the Qwen3-8B ladder of seeds 4–9 (`lf` → `gtrt` → `think`,
PREREG_CONJ, mechanism section); the runs named under **Held-out data** have not been scored with it.

**Why.** After RL on the count, the largest loss of the grid method is puzzle-seeds where both translations leave several solutions (13.7% on
GridPuzzle). PREREG_CONJ's mechanism run shows both translators drop the same thing: entities that a disjunctive or negative clue names are
different entities ("the 24 megapixel camera is either the $575 model or the Tela G5" also says the $575 model is not the Tela G5). Literally
"A or B" does not say A ≠ B; the exclusive, distinct reading is a pragmatic strengthening. The puzzle's one-solution guarantee says when the
literal reading is too weak: exactly when the program allows several solutions. So the strengthening is applied only then, and a program with
one solution is never changed.

**Related work.** LOGICPO (2506.18383) notes that models render the pragmatic exclusive "either … or" as logical OR when translating to
first-order logic; some translation rule sets map "either A or B" to inclusive OR unless "but not both" is stated (2601.02902); CLOVER
(2410.08047) compares candidate formulas with a SAT solver. None uses the problem's uniqueness guarantee to decide when to strengthen, and none
measures it against thinking at equal cost.

**Rule (fixed; `distinct_closure` in `poc/gp_conj.py`).** For a translation (quick or thinking step) whose count is 2 or more: for every clue
expression that is an `or`, an `in`, an exclusive or, or an `and` of `!=`, add `A != B` for every pair of named entities (`p['…']` keys of
different categories, and numbers of the first category) that no comparison in that expression equates; re-count under the unchanged
GP_SOLVE. Exactly one solution settles the step, as any count-1 step does. No tokens are added. Programs with count 0, 1 or an error are not
touched.

**Already seen (exploratory, not part of the test).** Qwen3-8B, seeds 4–9, ladder `lf` → `gtrt` → `think`: GridPuzzle +13.9 [+10.0, +18.1]
(87.3% at 9.07 ktok vs 75.8% at 14.00), Mitra-Baral +3.1 [+0.8, +6.1]. Applying the closure to every program (count 1 too) gave +14.6 and +4.7
but turned 5 of 746 and 26 of 734 right one-solution programs into no solution (34 of 437 base `gtrt` on Mitra-Baral), so it is not the rule.

**Held-out data** (stored runs, never scored with the rule; each ladder is quick `gtr` → thinking translation `gtrt` → `think`, the same
seed per step, scoring v2, all steps paid):
- H1, Qwen3-8B base, test seeds 1–3 (`q8b`): other runs than the ones the rule was read from, same test puzzles.
- H2, Qwen3-32B (`q32a`), test seeds 1–6.
- H3, gpt-oss-20b (`oss20`), test seeds 1–6.
- H4, gpt-oss-120b (`oss120`), test seeds 1–6.
- H5 (reported only, 40 puzzles): GridPuzzle dev split, Qwen3-8B `q8bh` gtr seeds 1–3 → `q8bh` gtrt seed 1 → `q8b` think seed 1.

Bootstrap over puzzles, each puzzle's mean over seeds. `python poc/gp_conj.py dcl` (CPU job, sandboxed) then `python poc/gp_conj.py dcleval`.

**Derivation of the prediction.** Gain ≈ (share of steps with count ≥ 2 settled right by the closure) × (value of settling them). On the
discovery ladder 127 of 228 `lf` and 204 of 374 `gtrt` count-2 programs became one right solution, 2 one wrong. Larger models write the
exclusive reading more often and leave fewer count-2 programs (Qwen3-32B and gpt-oss-120b quick steps are more precise, GP-120), so the gain
shrinks with model strength: H1 about +12 (base ladder, more count-2 programs than `lf`), H2 about +5, H3 about +6, H4 about +2.

**Predictions.**
- **DCL-P1 (decides):** GridPuzzle, closure − plain ladder utility: interval above 0 on H1, and on at least two of H2–H4.
- **DCL-P2 (no harm):** Mitra-Baral, lower bound above −2.0 on each of H1–H4.
- **DCL-P3:** among count-2 programs that the closure brings to one solution, at least 95% are right (pooled over H1–H4 and both sets).
- **DCL-P4 (reported):** closure ladder − thinking per model; H5.

**Decision.**
- P1 and P2 hold → the closure joins the course method as a free step inside each translation step (with the trained translator, the
  discovery numbers become the method's: GridPuzzle 87.3%). The report states it as a stated convention of the puzzle family, licensed by the
  uniqueness guarantee, and lists the clue forms it covers.
- P1 holds only on H1 → it is a fix for the 8B model's reading, reported as such, still in the 8B method.
- P1 fails on H1 → it is not used; the discovery numbers are reported as exploratory only.

## Result (2026-11-13 04:5x UTC; `python poc/gp_conj.py dcleval`, job 1422156): P1, P2 and P3 hold on every held-out ladder. The closure joins the method

| Ladder (held out) | GridPuzzle plain → with closure | closure − plain | closure − thinking | Mitra-Baral closure − plain |
|---|---|---|---|---|
| H1 Qwen3-8B, seeds 1–3 | 72.4% at 18.34 ktok → **82.8% at 14.60** | **+12.3 [+8.7, +16.0]** | +15.7 [+10.8, +20.8] | +3.3 [+0.9, +6.3] |
| H2 Qwen3-32B, seeds 1–6 | 82.1% at 9.84 → **94.7% at 5.33** | **+14.9 [+10.9, +19.1]** | +25.6 [+21.2, +30.0] | +3.0 [+0.8, +5.8] |
| H3 gpt-oss-20b, seeds 1–6 | 84.7% at 19.04 → **91.0% at 12.56** | **+9.6 [+6.7, +12.7]** | +13.5 [+10.2, +17.0] | +2.0 [+0.6, +3.7] |
| H4 gpt-oss-120b, seeds 1–6 | 93.1% at 10.21 → **96.9% at 5.19** | **+6.3 [+4.0, +9.0]** | +6.5 [+4.3, +9.0] | +0.2 [+0.1, +0.4] |

- **DCL-P1 holds** (H1 and all of H2–H4 above 0). **DCL-P2 holds** (every Mitra-Baral lower bound above 0, not only above −2).
  **DCL-P3 holds:** count-2 programs the closure settles are right 996 of 1,017 times (97.9%), pooled over H1–H4 and both sets.
- **Predictions vs outcome:** H1 +12.3 (predicted +12), H2 +14.9 (predicted +5), H3 +9.6 (+6), H4 +6.3 (+2). The gain does not shrink with model
  strength as I derived: Qwen3-32B leaves as many several-solution translations as the 8B model (523 of 2,580 programs), all models drop the
  same implication, and settling a step also saves the next step's tokens, which are large for every model.
- **Thinking (P4):** the closure ladder beats thinking on GridPuzzle for every model, by +6.5 (gpt-oss-120b) to +25.6 (Qwen3-32B); on
  Mitra-Baral by +1.6 to +5.1 (intervals include 0 for Qwen3-8B and gpt-oss-20b).
- **Scoring note:** rows written before grids were kept are scored from the stored scoring-v2 tables (`<set>_<tag>_score2.json`), as every earlier
  verdict on these runs; the first run of this evaluation missed that and scored those rows wrong (plain ladders and thinking at 0.0% for Qwen3-8B seeds 1–3); the loader was fixed and the decision reads the fixed numbers. The grid a
  closed program gives is scored with `gp_score` (the closed program names values as the puzzle lists them).
- **Decision as registered:** the closure joins the course method as a free step inside each translation step. With the trained translator
  (discovery data, seeds 4–9): GridPuzzle 87.3% at 9.07 ktok (utility 82.8) against thinking 63.4% at 11.53 (57.6); Mitra-Baral 92.7% at 5.52.
- H5 (dev, reported only): pending a rescoring of the dev rows (job 1423108).
