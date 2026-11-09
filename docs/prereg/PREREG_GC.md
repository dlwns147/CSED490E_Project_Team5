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
