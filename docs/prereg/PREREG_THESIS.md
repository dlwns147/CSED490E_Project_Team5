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
