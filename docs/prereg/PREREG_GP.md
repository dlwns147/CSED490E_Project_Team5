# Pre-registration: the gate on logic grid puzzles written by people (GP)

Written 2026-11-09 09:4x UTC, before any test-split output exists. Idea 27 in `docs/notes/IDEAS_COMPUTATION.md`.

**Why.** On ZebraLogic the gate wins clearly (Qwen3-8B +14.6 utility, gpt-oss-20b +28.9; `PREREG_ZL.md`), but on AR-LSAT it ties (`PREREG_LS.md`). Two explanations fit both results, and they predict different things on grid puzzles written by people:

- **Templates.** ZebraLogic's clues come from a few templates, so translation is easy there and hard on real text. Prediction: on human-written grid puzzles, wrong translations get accepted (count-1 precision falls well under 95%), and the gate does not pay at any size.
- **Search.** Thinking fails on ZebraLogic mostly while searching large grids, which the solver does for free, while on AR-LSAT it fails while reading the rules, which the translation shares. Prediction: count-1 precision stays high on human text, and the gate's edge grows with grid size.

**Prior work, read before this.** Ishay, Yang, Lee (KR 2023, 2307.07699): GPT-4 writes answer set programs for Mitra and Baral's Puzzle Baron puzzles, solving 92 of 100 test puzzles against 21 zero-shot. The count of answer sets is only a flag for a human, with no feedback to the model, no token cost and no thinking model. GridPuzzle (2407.14790): GPT-4-Turbo with chain of thought solves 14 of 274, no solver baseline. ZPS (2407.03956): GPT-4 to SMT-LIB with Z3 feedback on 114 zebra puzzles, no uniqueness check. Logic.py, SatLM and Logic-LM as in `PREREG_ZL.md`. So translating human grid clues already works at GPT-4 scale; what is tested here is the count as a cost gate at 8B, against a current thinking model, and its dependence on size.

**Data.**
- GridPuzzle test split: 215 puzzles (3×4 to 4×6), `poc/gp_prep.py`; 40 dev puzzles were read while writing the prompts.
- Mitra-Baral test: 94 of Ishay et al.'s 100 test puzzles (6 do not parse), all 3×4; their 48 train puzzles are dev (`gp_prep.py --lgp`). 2 of the 94 share clues with GridPuzzle.

**Setup.** Qwen3-8B, seeds 1, 2, 3, temperature 0.7, `run_zebra.py --gp` (with `--set lgp` for Mitra-Baral).
- `gtr`: translate without thinking, 4,096 tokens a round, up to 3 rounds with label-free count feedback.
- `gtrt`: translate with thinking, 16,000 tokens a round, up to 3 rounds.
- `think`: thinking, 32,000 tokens.
- **Ladder:** `gtr`; if its count is not 1, `gtrt`; if not 1, `think`. Every step paid is counted. Composed offline on the same puzzle and seed.
- Scoring: whole-grid exact match, loose on format only (`gp_score`: "10 day" = 10).
- The translation prompt and harness are frozen at the commit of the first test translation run; changes before it use dev outputs only. The think arm does not depend on them and starts first.

Utility per puzzle = 100·right − 0.5·ktok. Intervals: bootstrap over puzzles, 95%, each puzzle's mean over seeds.

**Predictions.**
- **GP-P1 (search):** on GridPuzzle, ladder utility exceeds `think`, interval above 0.
- **GP-P2 (the discriminating one):** count-1 precision is at least 95% for `gtr` and for `gtrt` on each set (pooled over seeds; point estimate). The dev pilot gave 32 of 33 before the interface fixes.
- **GP-P3 (search, size):** on GridPuzzle, the gate's edge on accepted puzzles, p − A (precision minus thinking's accuracy on the same puzzle-seeds), is larger on 4×5 and 4×6 (73 puzzles) than on 3×4 and 3×5 (98 puzzles); the difference interval is above 0. Dev thinking: 8/8 on 3×4 at 5.2k tokens, 2/8 on 4×6 at 19.0k.
- **GP-P4 (small puzzles):** on Mitra-Baral, ladder accuracy is at least `think` minus 2 points (interval lower bound above −2), and ladder utility exceeds `think` (interval above 0), through tokens.
- **GP-P5 (reported):** ladder accuracy on the 94 Mitra-Baral test puzzles, beside Ishay et al.'s GPT-4 92% and Logicia's 71%.

**Decision.**
- P1, P2 and P3 hold: the ZebraLogic gain does not need templates. Run gpt-oss-20b on both sets, and state the search explanation as supported on three benchmarks.
- P2 fails: wrong translations of human text pass the count. The template explanation is supported, and the claim stays limited to templated puzzles.
- P1 holds but P3 fails: the gate pays on human text, but not by size. The search explanation is not supported as stated.

**Limits stated now.** The 3×4 to 4×6 grids are smaller than ZebraLogic's largest (6×6), so the size range is narrow. GridPuzzle's puzzle text carries an answer-format block meant for the original chain-of-thought prompt; it stays in, the same for every arm. Utility prices all tokens alike and ignores solver seconds.

## Freeze (2026-11-09 14:5x UTC)

The translation prompt and harness are frozen at commit f223d46. The test translation runs are jobs 1366020-2 (translation with thinking on GridPuzzle, seeds 1-3) and 1366023 (translation without thinking on both sets, and with thinking on Mitra-Baral).

Changes made on dev before the freeze:
- Value names are matched on format only.
- A bare string value stands for its slot.
- Clues compare the first category's numbers directly.
- Months use their month number.
- Retry rounds send back only the program.

Last dev pilot (q8bh), right when the solver found exactly one solution:

| Arm | GridPuzzle | Mitra-Baral |
|---|---|---|
| Without thinking (three seeds pooled) | 38 of 46 | 64 of 73 |
| With thinking (seed 1) | 7 of 7 (8 of 40 puzzles done) | 33 of 35 |

Two candidate checks were rejected on dev:
- Agreement of 2 of 3 seeds: 4 of the 23 agreed grids were wrong.
- Rejecting programs whose number of clue expressions differs from the puzzle's: it would drop 6 right programs to catch 4 wrong ones.
