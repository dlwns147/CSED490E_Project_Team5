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

## Run note (2026-11-09 21:1x UTC)
Job 1366023 ran nine client commands against one server; its KV cache stayed full with about 225 requests waiting, and the three Mitra-Baral `gtrt` commands died on the client's one-hour request timeout after 34, 3 and 9 of 94 rows (the other six finished). Those three were re-run from the start with the same frozen code and seeds, one lane per seed and a four-hour timeout (jobs 1368153–5). The partial rows are kept as `results/lgp_q8b_gtrt_s*.crashed_tgrest.jsonl` and are not used.

## Results, GridPuzzle part (2026-11-09 22:1x UTC; `python poc/gp_eval.py q8b`, all 645 puzzle-seeds)
Mitra-Baral (GP-P4, GP-P5) waits for the re-run `gtrt` seeds.

| Arm | Accuracy | ktok | Utility |
|---|---|---|---|
| `gtr` | 35.7 | 1.0 | 35.2 |
| `gtrt` | 64.0 | 17.5 | 55.3 |
| `think` | 63.7 | 11.4 | 58.0 |
| Ladder | 71.8 | 18.3 | 62.6 |

- **GP-P1 holds:** ladder − think utility +4.6 [+0.4, +8.9]; accuracy +8.1 [+4.0, +12.1] points.
- **GP-P2 fails:** count-1 precision `gtr` 206/245 = 84.1%, `gtrt` 365/387 = 94.3% (bar 95% each).
- **GP-P3 holds:** p − A on accepted puzzle-seeds +41.1 points on 4×5 and 4×6 (112) against −2.1 on 3×4 and 3×5 (234); difference +43.2 [+27.5, +58.9]. By size, ladder − think utility: 3×4 −5.6, 3×5 −0.9, 4×4 +4.3, 4×5 +5.3, 4×6 +33.2.

**Decision, as registered.** GP-P2 fails, so the registered reading is the template one: wrong translations of human text pass the count, and the claim stays limited to templated puzzles. gpt-oss-20b is not run (it needed P1, P2 and P3). Stated beside it, without changing the decision: the gate still pays on human text (P1) and its edge grows with size (P3), so search is part of the gain too; and the exploratory 32B pilot (rule fixed before output, `IDEAS_COMPUTATION.md` row 27) put count-1 precision without thinking at 96.3% on dev, so at 8B the shortfall is the model's. The follow-up that targets P2's failure is registered separately (`PREREG_GC.md`).

## Results, Mitra-Baral part (2026-11-10 00:1x UTC; all 282 puzzle-seeds, `gtrt` from the re-run)

| Arm | Accuracy | ktok | Utility |
|---|---|---|---|
| `gtr` | 53.5 | 0.5 | 53.3 |
| `gtrt` | 84.4 | 11.9 | 78.5 |
| `think` | 85.5 | 6.3 | 82.3 |
| Ladder | 90.1 | 9.8 | 85.2 |

- **GP-P2 on Mitra-Baral:** `gtr` 136/150 = 90.7% (fails), `gtrt` 224/226 = 99.1% (holds). With GridPuzzle, P2 fails as recorded above.
- **GP-P4 fails:** ladder − think accuracy +4.6 [−1.4, +10.6] (lower bound above −2, holds), utility +2.9 [−3.3, +9.2] (interval not above 0, fails).
- **GP-P5:** ladder accuracy 90.1%, beside Ishay et al.'s GPT-4 with ASP 92% and Logicia 71%, with an 8B model at 9.8k tokens a puzzle.

The registered decision stands as written in the GridPuzzle part: P2 fails, so the template reading is the registered one.

## Addendum GP-LOC (idea 33 on test), registered 2026-11-10 10:5x UTC before any test run

**Why.** Idea 33's dev rule (IDEAS row 33, fixed 05:3x) passed both steps by point estimate: step 1 (gtrl vs gtr) +0.6 [−2.9, +4.3] over 259 puzzle-seeds, step 2 (gtrtl vs gtrt) +0.5 [−5.3, +6.4] over 87. Both intervals hold 0, so dev cannot tell; the registered rule sends it here. Prior work (Sarkar 2026, 2608.14771) found minimal-core repair no better than generic repair (89.6% vs 88.3%).
**Runs.** Qwen3-8B, tag `q8bl`, test split, both sets: `gtrl` seeds 1–3; `gtrtl` seed 1. Same prompts, token limits (4096 / 16000) and rounds as the `q8b` test runs of `gtr` / `gtrt` / `think`, which serve as the generic arms.
**Measure.** Per puzzle-seed, ladder utility (100·right − 0.5·ktok). Step 1: gtrl (seed s) → gtrt (`q8b`, seed s) → think (`q8b`, seed s) minus gtr (`q8b`, seed s) → same; seeds 1–3. Step 2: gtr (`q8b` s1) → gtrtl (s1) → think (s1) minus gtr → gtrt → think, seed 1. Bootstrap over puzzles, 95%, pooled over both sets and per set.
**Predictions.** GP-LOC-P1: step 1 pooled interval contains 0 (no gain). GP-LOC-P2: step 2 pooled interval contains 0. GP-LOC-P3 (mechanism): gtrl's own accuracy is not above gtr's (dev: 30.8 vs 33.3, 43.1 vs 50.7), so any step-1 gain comes from fewer wrong count-1 stops, not more right ones.
**Decision.** A step's localized feedback replaces the generic one in the registered ladder only if its pooled utility interval lies above 0; otherwise the generic feedback stays and idea 33 is closed as a tie with Sarkar's finding.

**GP-LOC step 1 result, 2026-11-10 11:5x UTC** (`python poc/gp_eval.py --loc --test`; jobs 1372759 done, step 2 job 1372760 running). gtrl 35.5% vs gtr 35.7% (GridPuzzle), 53.5% vs 53.5% (Mitra-Baral), same 1.0 / 0.5 ktok. Step 1 ladder utility, localized minus generic: GridPuzzle −1.6 [−3.8, +0.6], Mitra-Baral −1.7 [−3.9, +0.6], **pooled −1.64 [−3.34, −0.01] over 927 puzzle-seeds → generic feedback stays.** GP-LOC-P1 (interval contains 0) fails narrowly, on the losing side. GP-LOC-P3 (gtrl accuracy not above gtr's) holds, but its stated mechanism is wrong: count-1 precision falls (212/273 = 77.7% vs 206/245 = 84.1%; Mitra-Baral 145/170 vs 136/150), so the localized arm stops wrongly more often, not less.

**GP-LOC step 2 result, 2026-11-10 19:5x UTC** (`python poc/gp_eval.py --loc --test`; job 1372760 done). gtrtl 61.9% vs gtrt 64.0% (GridPuzzle, seed 1), 83.0% vs 84.4% (Mitra-Baral) at 17.1 / 11.7 vs 17.5 / 11.9 ktok. Step 2 ladder utility, localized minus generic: GridPuzzle −1.7 [−5.1, +1.6], Mitra-Baral −2.1 [−6.9, +2.2], **pooled −1.80 [−4.59, +0.79] over 309 puzzle-seeds → generic feedback stays.** GP-LOC-P2 (interval contains 0) holds. With step 1, localized feedback does not help at either step; the thinking translation's count-1 precision stays high under it (121/131, 73/74), so step 2's loss is fewer right stops, not more wrong ones.

## Scoring correction (2026-11-11 03:3x UTC; FINDINGS same time)

`gp_score` failed right answers on format alone ("blu-ray" for "blu-ray player", 5.5 for "$5.50", "78 million" as 78000000) and passed "B-" for "B+". Thinking answers are hit more than programs, which copy the listed names. Scoring v2 (`poc/grid_score.py`): a cell is right when it names the gold value and no other listed value. Rows rescored by `poc/gp_rescore.py` (programs re-run in the container; no count changed); read with `--score2`.

| Ladder − think, utility | As registered | Scoring v2 |
|---|---|---|
| Qwen3-8B, GridPuzzle (GP-P1) | +4.6 [+0.4, +8.9] | **+3.5 [−0.7, +7.7]** |
| Qwen3-8B, Mitra-Baral | +2.9 [−3.3, +9.2] | +0.4 [−5.6, +6.7] |
| Qwen3-32B-AWQ, GridPuzzle | +11.3 [+7.4, +15.3] | +11.0 [+7.1, +14.9] |
| Qwen3-32B-AWQ, Mitra-Baral | +0.4 [−2.9, +3.7] | +0.8 [−2.5, +4.0] |
| gpt-oss-20b, GridPuzzle | +5.5 [+1.8, +9.3] | +3.9 [+0.5, +7.5] |
| gpt-oss-20b, Mitra-Baral | +3.5 [+1.0, +6.2] | **+1.8 [−0.5, +4.1]** |

GP-P1 no longer holds for Qwen3-8B under v2: its interval now includes 0. The plain ladder's lead on GridPuzzle stands for the two larger models. gpt-oss-20b's plain-ladder win on Mitra-Baral (FINDINGS 2026-11-10 16:1x) becomes a tie. Scoring v2 is used from here on.
