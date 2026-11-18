# PREREG_KK — Knights and Knaves as a new domain; prospective test of the label-free gain estimate

Written 2026-11-18 10:3x UTC, before any K&K model output exists (runner poc/run_kk.py written this hour; data nlp_data/kk_dl, 700 test
puzzles, 2-8 inhabitants, 100 each; every puzzle has exactly one solution).
Why: two claims were only shown on domains our choices touched: (1) the ladder wins where a structural check exists; (2) its gain is
predictable without labels (hybrid rule, PREREG_LF: MAE 1.0 over 17 seen cells). K&K is untouched: no prompt, step or rule was chosen on it.
Runs (seed 1, all 700): Qwen3-8B trc, trct, think (30,000 tokens); gpt-oss-20b trc (low effort), trct and think (high effort).
Ladders: L-Q = Qwen3-8B trc -> trct -> think; L-O = gpt-oss-20b trc -> trct -> think; accept at the first step whose program has exactly
one consistent assignment. Utility = 100 x correct - 0.5 x ktok, paired bootstrap over the 700 puzzles.
Baseline rule (as PREREG_X56): if gpt-oss-20b high-effort thinking hits the cap on more than 10% of puzzles, also run medium effort and
use the better utility.
Predictions:

- KK-1: L-Q - Qwen3-8B thinking > 0 (interval above 0); L-O - gpt-oss-20b thinking > 0. Reason: K&K statements map one-to-one to boolean
  conditions, so the quick translation should be precise, and thinking spends many tokens on 6-8 inhabitants.

- KK-2 (the label-free rule, decisive): BEFORE reading any score, compute each ladder's accuracy term from unlabeled outputs with the hybrid
  (third = the other family's quick translation, its answer used where its count is 1, otherwise trust the accepted answer) and write the
  numbers below with the UTC time. Then score. Holds if |predicted - measured accuracy term| <= 2.0 points in both cells.
Decision: KK-2 holds -> the label-free rule stands on a domain it never saw. Fails -> state where it breaks (coverage, precision).

(Copied 2026-11-18 10:3x UTC from host/exp_log.txt, where it was written at 10:3x before any job started; text unchanged.)
