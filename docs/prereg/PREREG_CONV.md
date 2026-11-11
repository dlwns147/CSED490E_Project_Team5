# PREREG_CONV: the ladder's own escalations teach its quick translation a domain's reading conventions, registered 2026-11-11 11:2x UTC, before any run

**Why.** The headline ZebraLogic ladder of Qwen3-8B uses a hand-written fact in its quick translation (`run_zebra.ZL_FACT`: "There is one house between A and B" means a distance of 2). We wrote that fact after reading dev errors, which is domain knowledge a reader can fairly object to. Without it (Amonkar et al.'s setting, ZL-AM), the dominant error of the quick translation is that same phrase read off by one (FINDINGS 2026-11-11 10:1x). The count cannot see the misreading when it still leaves one solution, and no free text check catches it (FREE-ZL).

**What the stored runs show (read before this file; Qwen3-8B, ZL-AM, 3 seeds; gold used only to score clues, never in the method).**
- The quick translation (`tr`) misreads "N houses between" in 81 of 85 such clues (95%). The thinking translation (`trt`) misreads 8 of 150 (5%). The same model knows the convention when it thinks.
- When the quick translation ends without a count of 1, the ladder runs the thinking translation anyway. On the puzzles where that reaches a count of 1, the clues the two programs read differently (compared by evaluating both expressions on every assignment, without running them) give 115 pairs across the three seeds. The thinking expression agrees with the gold solution in all 115. The quick expression violates it in 67; it agrees in 18 (value naming); 30 could not be checked. The first such pair is a "between" clue at the first escalated puzzle in all three seeds.
- Of the 21 wrong count-1 quick programs, 15 come after the memory already holds a right reading of every clue form they misread.
- gpt-oss-20b gives no pairs. It rarely escalates, and never with a clue read differently, so its memory stays empty (no run needed).
- On GridPuzzle the pairs are also right (Qwen3-8B 312 of 318), but human-written clues rarely repeat a form, so no wrong count-1 program's misread clue had a matching form in memory. Grids are therefore not run here; the prediction there is no effect.
- The hand fact's own effect, on the 250 dev puzzles where it was written (seed 1): ladder with the fact − ladder without, utility +3.9 [+0.8, +7.3], count-1 precision 95.9% against 90.9%.

**The method (arm `trm`, `poc/run_zebra.py` and `poc/grid_score.clue_pairs` / `disagree` as committed with this file).**
- Puzzles are taken in order, one at a time.
- When a puzzle's quick translation ends without a count of 1, the ladder's next step is the thinking translation. If that reaches a count of 1, every clue the two programs read differently is stored as (clue text, the thinking program's expression).
- Clues are aligned by position, only when both programs have one expression per clue.
- "Read differently" means the two expressions name different values or disagree on some assignment of houses. Every assignment is tried when a clue names at most 3 values, otherwise 300 random ones. Expressions are read by a whitelisted interpreter, never executed.
- Every later puzzle's quick translation gets all stored pairs after the usual instruction: "On earlier puzzles of this set, these clues were read as below, and that reading made the solver find exactly one solution where another reading had not:", then one line per pair. A clue text already stored is not stored again.
- Nothing else changes: same prompt otherwise, 3 rounds with count feedback, same seeds, no template fact, no labels. The thinking translations come from the stored `trt` runs of the same seed, which is exactly what the ladder runs at that step, so the memory costs no model call.
- Parameters: none tuned. All pairs are shown, and the 300 random assignments only decide whether two expressions differ.

**Runs (Qwen3-8B, one GPU, seeds 1–3).**
- **Cell A, ZL-AM:** Amonkar et al.'s 100 puzzles, `--ids results/a_zl100_ids.txt`, tag `q8bam`, arm `trm`. Compared with the stored `tr`, `trt` and `think`.
- **Cell B, unseen main puzzles:** the 250 puzzles not seen when the fact was written (`--skip 10`), tag `q8bh`, arm `trm`, plus arm `tr` (no fact, no memory, which was never run on these). Compared with the stored `trf` (the fact), `trt` and `think`.
- **Ladder:** quick step (`tr`, `trf` or `trm`) → `trt` → `think`. Every step is paid; a count of 1 stops it. Utility = 100·exact − 0.5·(output tokens / 1000). Input tokens, which the memory adds, are reported but not priced, as in every other arm.
- **Scoring and intervals:** ZebraLogic exact grid (`zl_score`, as registered for ZL). 95% bootstrap over puzzles (10,000 resamples, a puzzle's three seeds kept together).

**Predictions.**
- **CONV-P1 (mechanism):** in `trm` programs with one expression per clue, the share of "N houses between" clues whose expression the gold solution violates is at most 30%, in each cell, counting puzzles after the memory first holds such a clue. `tr` in cell A: 95%. Gold is used only for this measurement.
- **CONV-P2:** `trm` count-1 precision is at least 95% in each cell. `tr` in cell A: 89%.
- **CONV-P3 (decides):** ladder(`trm`) − ladder(`tr`), utility, cell B: the interval is above 0. Cell A is reported with its own interval; its point estimate should be above 0.
- **CONV-P4 (replaces the hand fact):** ladder(`trm`) − ladder(`trf`), utility, cell B: the lower bound is above −2.0. The margin is half the fact's own measured effect (+3.9).

**Decision.**
- If P3 and P4 hold, the headline ZebraLogic ladder is restated without the hand-written fact. The claim becomes: the free count, together with the ladder's own escalations, supplies the convention.
- If P1 holds and P3 fails, the mechanism works but the gain is below this test's reach. I report that and make no claim.
- If P1 fails, the quick translation does not use the memory. Kill `trm`.
- Not claimed in any case: conventions that the thinking translation also misreads. These are "either A or B" on grids (thinking also reads it inclusively: 116 of 117 aligned either/or clues in `gtrt` count-1 programs, Qwen3-8B, seed 1) and the day window on trips. Memory from the ladder's own escalations cannot fix a reading its expensive step shares.

**Prior work.**
- **Dynamic Cheatsheet** (Suzgun et al., 2504.07952) keeps a test-time memory that the model curates itself, with no external check on what is stored.
- **Self-generated in-context examples** (Sarukkai et al., 2505.00234) store trajectories that succeeded by the environment's reward. ExpeL (2308.10144) is similar.
- **Self-ICL** (2305.15035) and **Auto-CoT** (2210.03493) use the model's own demonstrations without a check.
- **Semantic self-verification** (Raza and Milic-Frayling, 2501.16961) has the model write examples per constraint and checks them with a solver, but only within one problem.
- **Here:** an entry is admitted only by a free, label-free signal, a solution count of 1 where the cheap reading did not reach one. The teacher is the ladder's own expensive step on other problems, and it costs no additional call. A search found no prior work that stores solver-verified encoding conventions across problems.

## Result (2026-11-11 16:0x UTC): CONV-P1 fails, so trm is killed. P2, P3 and P4 fail as well.
Job 1382299, `python poc/gp_eval.py --conv`. Qwen3-8B, three seeds.
- **CONV-P1 fails.** "N houses between" clues that the gold solution violates, in trm programs once the memory holds such a clue: 50 of 82 (61%) in cell A and 123 of 144 (85%) in cell B. The limit was 30%. Without memory: 95% and 94%. With the hand-written fact (trf): 18%.
- **CONV-P2 fails.** trm count-1 precision is 90.7% in cell A and 91.9% in cell B.
- **CONV-P3 fails.** Ladder(trm) − ladder(tr): cell B −0.4 [−1.8, +1.1]; cell A +0.6 [−2.1, +3.0].
- **CONV-P4 fails.** Ladder(trm) − ladder(trf): −4.0 [−6.9, −1.2].
- **Why: the quick translation copies its own reading, even with right examples in front of it.** In seed 1 of cell B, the memory holds 30 "between" pairs by the end, every one written as a distance of 2 for "one house between". Yet late puzzles shown 21–27 lines of memory still write "There is one house between Eric and Alice" as `abs(p['Name:Eric'] - p['Name:Alice']) == 1` (six such cases in a row from lgp-test-5x4-12 on).
  - The same model follows a one-sentence explicit rule (trf: 18% misread). Worked examples of the phrase do not override its prior; a stated rule does.
- **Decision (as registered):** P1 fails, so the quick translation does not use the memory. trm is killed. The hand-written fact stays as stated in the ZebraLogic ladder, with its provenance (mined from dev errors) disclosed.
