# Pre-registration THESIS: does the break-even rule predict the peer cascade's sign across every stored cell?

Written 2026-10-31 20:4x UTC, while `poc/analyze_thesis.py` runs (CPU job 1289720) and before its output is read. Offline, stored rows only.

**Purpose.** The review's first point (docs/notes/CRITIQUE.md, 10-31): the project's findings read as a catalogue; the thesis that
unifies them is the break-even rule — a cheap answer pays only if its check accepts (quick right, default wrong) at least r* times as
often as (quick wrong, default right), r* = (n_W / n_R)(L / G), and the default's tokens saved outweigh the two quick answers'. Every
earlier test of it was in one task at a time and partly in sample (the accounting is exact on the rows it is computed on). Here it is
tested out of sample across all tasks at once.

**Cells.** Every stored generator (Qwen3-8B, Qwen3-14B-AWQ, Qwen3.5-9B, gpt-oss-20b) × every stored peer (the same four, not itself) ×
set: BIRD dev, the fresh BIRD questions, BFCL non-live and live, OptiBench third, BWOR, LogiOR, OptMATH (Spider when graded); cells
whose rows are missing are skipped. Each cell's questions are split in two halves (crc32(id) mod 2).

**Predictor and outcome.** On one half: x = log2((peer TPR / FPR on all passing quick answers) / r*), needing the quick answers' and the
default's labels on that half only. On the other half: the cascade's gain over the default (utility, peer's tokens counted, paired 95%
interval over questions). Both directions.

**Predictions.**
- **TH-P1:** among cell-halves whose other-half interval excludes 0, the sign of x matches the sign of the gain in ≥ 85%.
- **TH-P2:** the mismatches are cells where the two quick answers cost about as much as the accept decisions gain (word problems
  with a short default, e.g. gpt-oss-20b answering, XG-W), not cells where x > 0 and the accept decisions lose.
- **TH-P3:** TH-P1 holds within each task type with at least 5 such cell-halves.

**Decision.** P1 and P3 hold: REPORT and PROJECT lead with the break-even rule as the thesis, with this figure (x against the
other half's gain, every cell) and the task-type tables in an appendix. P1 refuted: the rule stays a per-task accounting, and the
report says where it fails to predict.

## Results (written 2026-10-31 20:4x UTC; `results/thesis.txt`, `results/thesis_cells.json`; CPU jobs 1289723 / 1289734)

Process note: the first run (1289720) stopped after 7 cells on a negative r* (L < 0: accepting a wrong passing answer never lost on
that half); the predictor is now clamped (x = +5 for r* ≤ 0 or a peer that never confirms a wrong answer, −5 for the reverse) — a fix
made after those 7 cells' full-sample lines had been printed, before any out-of-sample line. The second run printed TH-P1 / P3 but not
TH-P2's breakdown, which the third run (code added, nothing else changed) prints.

90 cells (4 generators × 3 peers × 8 sets; Spider not yet graded), 180 cell-halves, 73 with the other half's interval excluding 0.
- **TH-P1 refuted:** the predictor's sign matches the other half's gain in 57 / 73 (78%; required 85%). In sample: 37 / 40.
- **TH-P3 refuted:** SQL 19 / 20, tool calls 28 / 29, word problems 10 / 24.
- **TH-P2 refuted:** of the 16 mismatches, 5 are cost-driven as predicted (x > 0, the accept decisions still gain on the other half,
  the two quick programs' 0.7–1.4 utility outweighs them), 10 are not (x > 0 and the accept decisions themselves lose on the other
  half), 1 is pessimistic (x < 0, a gain). All but one mismatch are on word problems; the other is BIRD dev with Qwen3-14B-AWQ as the peer.
- Exploratory (not pre-registered): by the size of the half the predictor is estimated on, 47 / 49 (96%) with ≥ 1,000 question-seeds
  (BIRD, BFCL) against 10 / 24 below (OptiBench third 6 / 7, BWOR 2 / 5, LogiOR 2 / 10, OptMATH 0 / 2: 82–202 problems per set). Five of
  the ten accept-driven mismatches have x clamped or ≥ +0.95 from halves of 41–46 problems, where r* rests on a handful of problems in
  each decisive stratum.

**Decision (as pre-registered).** P1 refuted: the break-even rule stays a per-task accounting, not the report's thesis, and the report
says where it fails to predict: it predicts the sign out of sample on SQL and tool calls (47 / 49 on the large halves), and not on the
word-problem sets of 80–200 problems, where half a set does not estimate the decisive strata (exploratory reading of the failure).
