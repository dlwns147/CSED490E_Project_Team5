# What the report draft is missing (checked 2026-11-12)

`docs/REPORT.md` was last changed on 2026-11-07. Since then several of its claims were withdrawn or restated, and the strongest
computation results were never added. This list compares the draft with `PROJECT.md` §2 and `docs/FINDINGS.md`. It changes nothing in
the draft; the rewrite waits for the team's decision.

## Claims in the draft that are out of date

| Where | The draft says | Current record |
|---|---|---|
| Abstract, §2b | Multi-turn agents are the main result: 48.8% vs 30.8% for thinking (+17.2 utility) | Withdrawn (MT-FC, 11-07): our prompt format weakened thinking. In BFCL's native function-calling form the gain over the base model's best form is +7.1 [+3.3, +10.9], and the public EnvScaler-8B checkpoint with plain thinking beats our method by +5.4 [+1.7, +9.1]. Selection does not add to a good trained checkpoint (MT-FCS) |
| Abstract, proofs | Proof counts withdrawn pending a rerun | Settled: every counted row is a kernel-checked Lean theorem. HAGeo-409: 263 rows (HAGeo: 263 at K = 2,048, 287 at K = 8,192). IMO-AG-30: 27 (AG2 and TongGeometry 30). Held out: 22 of 65. MechGeo's 44 IMO problems: 13 per arm, possibly 20 and 21 after task 1 (side/README.md, 11-12) |

## Results the draft does not contain

- **Logic grid puzzles: a solver's count of solutions as the free check** (ideas 14, 24–38 in `IDEAS_COMPUTATION.md`; PREREG_ZL, GP, GC, MOT).
  - ZebraLogic: the ladder is more accurate and cheaper than thinking, so it wins at every token price. Qwen3-8B: +11.9 points at 4.3k fewer tokens on 750 runs. gpt-oss-20b: +22.6 points at 7.2k fewer.
  - GridPuzzle (human-written clues): more accurate than thinking (+6.0 to +11.3 points over three models), but it costs more tokens. Its utility lead holds up to a price of about 1 point per thousand tokens (Qwen3-32B-AWQ: 15.7).
  - Mitra-Baral: ties, except with the clue check (+5.6 [+0.9, +10.9]).
  - Against an agreement cascade (Mixture-of-Thought): the count wins on GridPuzzle, ties on Mitra-Baral.
  - Thinking fails large grids at search, not reading (idea 34). That is why a solver helps there.
- **RL on the quick grid translation** (PREREG_GRL, GRLK, GRLLF; 11-12).
  - Trained ladder minus base ladder: GridPuzzle +7.0 [+4.0, +10.2], Mitra-Baral +3.8 [+0.3, +7.4].
  - Trained ladder minus thinking on GridPuzzle: +9.8 [+5.7, +14.1]. The break-even price rises from 0.91 to 3.95 points per thousand tokens.
  - Rewarding only the free check, with no labels, trains as well as gold labels.
- **Token price** (FINDINGS 11-11 07:5x): the claim splits in two. On ZebraLogic the ladder is better and cheaper. On grids and trips it buys accuracy with tokens.
- **What failed since 11-07,** for the "did not work" list: localized solver feedback (GP-LOC), jointly chosen clue readings (idea 38), rules stated by the model and carried over to human-written puzzles (RULE3G, RULE4), and the escalation step chosen from the failed count (ESC, ESC2).

## Questions for the team before the rewrite

1. Which claim leads? The candidates are the programs recipe (§1–5) and the grid ladder with its free check.
2. Template, length, language and deadline (open since `REPORT_OUTLINE.md`).
3. Does the proof section use the 13 per arm, or the task-1 count if it is ready in time?
