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

**Addendum KK-3 (written 2026-11-18 11:4x UTC, before any Qwen3-32B or gpt-oss-120b K&K output exists; no KK score has been read).**
Same 700 puzzles, seed 1, same runner and settings: Qwen3-32B (AWQ) trc, trct, think; gpt-oss-120b trc (low effort), trct and think (high).
Ladders L-Q32 and L-O120 as KK-1. Third model for the label-free prediction: the other family's quick translation (gpt-oss-120b trc for
Qwen3-32B, Qwen3-32B trc for gpt-oss-120b).
- KK-3a: each ladder's utility − its own thinking ≥ 0 (interval lower bound above −2). Stronger thinkers leave less room, so the gain may be
  mostly tokens.
- KK-3b (decisive, as KK-2): blind hybrid prediction of each accuracy term, logged with the time before scoring; holds if within 2.0 points.

**KK-3b blind predictions (logged 2026-11-18 12:3x UTC, before any K&K score was read; `python3 results/tmp_kk_pred.py q32 oss120`,
which reads only count, ans and tokens).** Baselines: Qwen3-32B thinking 0 of 700 at the cap, 700 parsed, 2.5k tokens; gpt-oss-120b thinking
11 at the cap, 692 parsed, 3.6k tokens. Quick translations reach one solution on 645 (Qwen3-32B) and 699 (gpt-oss-120b) of 700.
- L-Q32: accepted 100%, third (gpt-oss-120b quick) answers 100% of them. **Predicted accuracy term −7.9** (rule A would say +11.1); token
  term +0.72; predicted ΔU −7.1.
- L-O120: accepted 100%, third (Qwen3-32B quick) answers 92%. **Predicted accuracy term +1.4** (rule A +2.4); token term +1.48;
  predicted ΔU +2.9.

**KK-3 result (2026-11-18 12:4x UTC; `python3 results/tmp_kk_score.py q32 oss120`, run after the predictions above were committed).**
- Qwen3-32B: thinking 98.6% at 2.49k; ladder 89.6% at 1.04k. **Measured accuracy term −9.0 (predicted −7.9); ΔU −8.3 [−10.7, −6.0].**
- gpt-oss-120b: thinking 98.6% at 3.58k; ladder 99.0% at 0.62k. **Measured accuracy term +0.4 (predicted +1.4); ΔU +1.9 [+0.7, +3.2].**
- **KK-3b holds in both cells** (errors 1.1 and 1.0). Rule A, which trusts the check, would have predicted +11.1 for Qwen3-32B: the hybrid
  saw a losing ladder before any label was read. **KK-3a holds for gpt-oss-120b and fails for Qwen3-32B.**
- Why Qwen3-32B loses: its quick translations reach one solution on 645 of 700 but 72 of those are wrong (precision 88.8%), against thinking
  that is near the ceiling (98.6%; 95–100% at every size). Typical error: the knave rule written as `k[s] != (stmt == k[s])`, which drops the
  speaker's truthfulness, and still leaves one assignment.
