# Pre-registration: the model checks the solver's grid, clue by clue (GC)

Written 2026-11-09 20:0x UTC. Idea 28 in `docs/notes/IDEAS_COMPUTATION.md`. No check has been run on test rows; the test translations of `PREREG_GP.md` are still running.

**Honest origin.** The idea came from `PREREG_GP.md`'s interim test numbers (count-1 precision under 95%), and was then tried on dev only. It is a secondary method, registered after GP's freeze; GP's own predictions are evaluated as written there, without the check.

**Why it should work.** The puzzle has one solution, so a wrong count-1 grid breaks at least one clue as written. Checking a clue against a filled table needs no search, which is where the 8B thinker fails on large grids. The gate then needs only that the checker reads clues differently enough from the translator.

**Prior work, read in full before this.** Semantic Self-Verification (Raza and Milic-Frayling, IJCAI 2025, 2501.16961; notes in `RELATED_WORK.md`). The model writes one satisfying and one breaking example per constraint, and the solver checks the program against them. With GPT-4, verified answers are right 98–100% of the time on 22–75% of questions; there are no token costs, logic grid puzzles or thinking-model baselines. Here the example is the solver's own answer and the model is the checker; the cost is one call on accepted steps only.

**Dev (q8bh programs, 179 count-1 programs, 20 wrong; `poc/gp_check.py`).**

| Checker | Wrong grids flagged | Right grids flagged | Check ktok | Checked ladder − plain ladder, seed 1 |
|---|---|---|---|---|
| `check` (no thinking, 2,048) | 17/20 | 21/159 | 0.3–0.5 | GP −1.4, MB +4.1 |
| `checkt` (thinking, 8,000) | 17/20 | 0/159 | 0.8–1.0 | GP +4.6 [−0.3, +11.8], MB +6.2 [−0.3, +14.7] |

`checkt` is registered; `check` is not run on test.

**Setup.** Qwen3-8B. `python poc/gp_check.py run q8b <gridpuzzle|lgp> checkt` on every count-1 program in GP's test rows (`gtr`, `gtrt`, seeds 1–3), once those rows are complete; the check's seed is fixed per program. Checked ladder: as GP's ladder, but a count-1 step whose grid gets a flag goes on to the next step; the check's tokens are paid on every count-1 step. Evaluated by `python poc/gp_eval.py q8b --check checkt` (written and tested on dev before this file). Utility 100·right − 0.5·ktok, bootstrap over puzzles, each puzzle's mean over seeds.

**Predictions.**
- **GC-P1:** unflagged count-1 precision, pooled over `gtr` and `gtrt` and seeds, is at least 95% on each set (GP-P2's bar).
- **GC-P2:** checked ladder minus plain ladder, utility interval above 0 on GridPuzzle.
- **GC-P3:** checked ladder minus `think`, utility interval above 0 on GridPuzzle (GP-P1 with the check).
- **GC-P4:** on Mitra-Baral, checked ladder accuracy at least `think` minus 2 points (lower bound above −2) and utility interval above 0.

**Decision.** GC-P1 and GC-P2 hold: the clue check becomes part of the gate on real text, and the AR-LSAT gate (`PREREG_LS.md`) is the next place to test it. GC-P1 fails: the checker shares the translator's misreadings on test (SSV's stated gap), and the reading of GP stands as registered. GC-P3 decides whether the method beats thinking alone on human-written grids; GC-P4 the same on small grids.

## Results, GridPuzzle part (2026-11-09 23:1x UTC; `python poc/gp_eval.py q8b --check checkt`, job 1368261, 632 count-1 programs)
Mitra-Baral (GC-P1's second set, GC-P4) waits for GP's re-run `gtrt` seed 1.

- Wrong grids flagged 34/61 (dev 17/20): `gtr` 28/39, `gtrt` 6/22. Right grids flagged 9/571 (`gtr` 1, `gtrt` 8). Check 0.87 ktok; none unparsed.
- **GC-P1 (GridPuzzle) holds, barely:** unflagged count-1 precision 562/589 = 95.4%.
- **GC-P2 holds:** checked ladder − plain ladder +2.0 [+0.3, +4.0] utility.
- **GC-P3 holds:** checked ladder − think +6.6 [+2.9, +10.6] utility (plain ladder +4.6 [+0.4, +8.9]); accuracy 74.7% vs 63.7%, +11.0 [+7.8, +14.6] points; 20.2 vs 11.4 ktok.
- By size, checked ladder − think utility: 3×4 +0.3, 3×5 −1.7, 4×4 +8.4, 4×5 +6.7, 4×6 +30.6.

Reading: the check catches most wrong quick translations (72%) but only 27% of wrong thinking translations, as SSV's stated gap predicts: what survives the model's own thinking translation is mostly a misreading the same model repeats when it checks. The precision bar is cleared by 0.4 points.

**Run note (2026-11-10 01:2x UTC).** The first Mitra-Baral test run (job 1368632) stopped before any check: the file glob also matched the partial `*.crashed_tgrest.jsonl` files kept from the PREREG_GP rerun. `gp_check.py` now skips files whose names do not end in `_s<seed>.jsonl`. Nothing else changed, and the run was resubmitted as job 1368860.

## Results, Mitra-Baral part (2026-11-10 02:2x UTC; `python poc/gp_eval.py q8b --check checkt`, job 1368860, 376 count-1 programs)

- Wrong grids flagged 13/16 (`gtr` 12/14, `gtrt` 1/2). Right grids flagged 1/360. Check 0.86 ktok; none unparsed.
- **GC-P1 (Mitra-Baral) holds:** unflagged count-1 precision 359/362 = 99.2%.
- **GC-P4 holds:** checked ladder − think, accuracy +8.2 [+3.5, +13.1] points (lower bound above −2), utility +5.6 [+0.9, +10.9]. Checked ladder 93.6% at 11.4 ktok, think 85.5% at 6.3 ktok. (The plain ladder tied: +2.9 [−3.3, +9.2].)
- Checked − plain ladder on this set: +2.7 [−0.2, +6.2] (GC-P2 was registered on GridPuzzle only).
- Beside prior work: 93.6% against GPT-4 writing ASP, 92% (Ishay et al. 2023).

**Decision, as registered.** GC-P1 and GC-P2 hold, so the clue check is part of the gate on human-written grids, and the AR-LSAT gate is named as the next place to test it. Before running it, I bounded what any check could do there. On the AR-LSAT test runs of `PREREG_LS.md` (690 question-seeds, think rescored with the `\boxed{}` fix), a perfect check costing 0.9 ktok sends all 15 wrong one-mark answers to thinking and none of the 145 right ones. That gives ladder − think +0.3 [−0.4, +1.2], still a tie. No real check can beat a perfect one, so a check cannot change LS-P1's verdict, and the AR-LSAT run is not made. The reason AR-LSAT differs: the gate there covers only 23% of questions and is wrong on just 15. On grids, the gate covers most puzzles and thinking fails on large ones.

## Addendum: a second model size, Qwen3-32B (GC32)

Written 2026-11-10 02:2x UTC, before any test output from Qwen3-32B exists. Only its dev translation pilot has been read: `gtr` count-1 precision 80/85 on GridPuzzle and 104/106 on Mitra-Baral.

**Why.** All results above use Qwen3-8B. If the ladder's edge comes from thinking failing at search on large grids (GridPuzzle 4×6: think 23.1%, checked ladder 57.7%), then a stronger thinker should narrow it. The open question is whether it closes. A paper claim needs to know whether the method works only because the 8B thinker is weak.

**Setup.** As above, with Qwen3-32B-AWQ (2 × RTX 3090, tensor parallel) as translator, checker and thinker. Tag `q32a`. Both test sets, seeds 1, 2, 3, arms `gtr`, `gtrt`, `think` (32,000 tokens), then `gp_check.py run q32a <set> checkt`. Read with `python poc/gp_eval.py q32a --check checkt`. Utility and intervals as above.

**Predictions.**
- **GC32-P1:** unflagged count-1 precision at least 95% on each set.
- **GC32-P2:** on GridPuzzle, checked ladder − think utility interval above 0.
- **GC32-P3:** on Mitra-Baral, accuracy lower bound above −2 and utility interval above 0.
- **GC32-P4 (mechanism, reported):** on GridPuzzle 4×5 and 4×6 grids together, checked ladder − think accuracy has its lower bound above 0, and is smaller than Qwen3-8B's on the same grids.

**Decision.** If GC32-P1 and GC32-P2 hold, the claim covers two sizes of Qwen3, and a second family is the next test. If P1 holds and P2 fails, the edge comes from the 8B thinker's weakness, and the claim is stated for 8B only, with this as its limit. If P1 fails, the check does not carry to the larger model.

**GC32 results, GridPuzzle part, 2026-11-10 10:5x UTC** (`python poc/gp_eval.py q32a --check checkt`; Mitra-Baral check, job 1372744, still to run). Checked ladder 82.6% at 10.5 ktok, thinking 70.1% at 8.9 ktok. GC32-P1 on GridPuzzle: unflagged count-1 precision 836/846 = 98.8%, holds. GC32-P2: checked ladder − think utility +11.7 [+8.1, +15.6], holds. GC32-P4 (reported): 4×5 and 4×6 accuracy gain +26.0 [+18.7, +33.3] over 73 puzzles, against Qwen3-8B's +21.9 [+14.2, +30.1]; lower bound above 0 holds, "smaller than 8B's" fails.

**GC32 results, complete, 2026-11-10 11:5x UTC.** Mitra-Baral (job 1372744): checked ladder 96.1% at 4.1 ktok, thinking 93.3% at 4.2 ktok; unflagged count-1 precision 473/474 = 99.8% (GC32-P1 holds on both sets); ladder − think accuracy +2.8 [+0.4, +5.7], utility +2.9 [+0.6, +5.5] (GC32-P3 holds). The check pays on Mitra-Baral (+2.4 [+0.3, +5.5] over the plain ladder; 8 of 9 flags hit wrong grids) and ties on GridPuzzle (+0.5 [−0.7, +1.6]). **Decision as registered: P1 and P2 hold, so the claim covers two sizes of Qwen3, and a second family is the next test (GC-OSS below).**

## Addendum: a second model family, gpt-oss-20b (GC-OSS)

Written 2026-11-10 11:5x UTC, before any grid output from gpt-oss-20b exists (its earlier rows in this project are ZebraLogic and other tasks, not these sets).

**Why.** Every grid result so far is Qwen3 (8B, 32B). A claim about checks against thinking needs a second family; gpt-oss-20b is a different maker, training recipe and reasoning format (no off switch, only reasoning effort), and fits one RTX 3090.
**Setup.** As GC32 with `openai/gpt-oss-20b` as translator, checker and thinker, tag `oss20`; the quick mode is reasoning effort low, the thinking modes are effort high: `gtr` (low, 4,096 tokens), `gtrt` (high, 16,000), `think` (high, 32,000), `gp_check.py run oss20 <set> checkt` (high). Both test sets, seeds 1, 2, 3. A dev `gtr` seed-1 pilot on both sets runs first and is read for crashes and format only. Read with `python poc/gp_eval.py oss20 --check checkt`.
**Predictions.** GC-OSS-P1: unflagged count-1 precision at least 95% on each set. GC-OSS-P2: GridPuzzle checked ladder − think utility interval above 0. GC-OSS-P3: Mitra-Baral accuracy lower bound above −2 and utility interval above 0. GC-OSS-P4 (mechanism, reported): GridPuzzle 4×5 and 4×6 accuracy gain lower bound above 0.
**Decision.** P1 and P2 hold → the claim is stated for two families. P1 holds, P2 fails → the claim is stated for Qwen3 only, and the gpt-oss numbers are reported as its limit. P1 fails → the free check does not carry across families.

## Scoring correction (2026-11-11 03:3x UTC; see PREREG_GP's section of the same name)

Checked ladder − think, utility, as registered → scoring v2 (`python poc/gp_eval.py <tag> --check checkt --score2`):

| Translator | GridPuzzle | Mitra-Baral |
|---|---|---|
| Qwen3-8B | +6.6 [+2.9, +10.6] → +5.5 [+1.8, +9.4] | +5.6 [+0.9, +10.9] → **+3.8 [−0.6, +8.8]** |
| Qwen3-32B-AWQ | +11.7 [+8.1, +15.6] → +11.4 [+7.9, +15.3] | +2.9 [+0.6, +5.5] → +3.2 [+1.2, +5.7] |
| gpt-oss-20b | +5.4 [+1.8, +9.1] → +3.8 [+0.5, +7.3] | +3.9 [+1.8, +6.3] → +2.1 [+0.4, +4.1] |

- GC-P1 holds under v2: unflagged precision is 95.8% and 99.2% for Qwen3-8B.
- GC-P2 and GC-P3 hold under v2.
- GC-P4's utility half fails under v2 for Qwen3-8B, whose interval now includes 0. Its accuracy half holds: +6.4 [+2.1, +11.0].
- Checked − plain is unchanged except Qwen3-8B on Mitra-Baral (+2.7 → +3.4 [+0.4, +7.0]).
