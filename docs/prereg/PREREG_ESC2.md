# PREREG_ESC2: skip the middle step only when it is confidently a loss, learned on seeds 1–3 and tested on fresh seeds 4–6, registered 2026-11-11 15:0x UTC, before any seed 4–6 run of these arms

**Why.** PREREG_ESC (registered and evaluated on the same runs, 2026-11-11 15:00 UTC) found two things:
- Choosing the escalation step from how the quick count failed gains on GridPuzzle for the gpt-oss models (+3.4 [+1.8, +4.9], +1.9 [+1.0, +2.7]).
- It loses where the middle step's value is near break-even, because the half-sample estimates flip sign (two intervals below 0, ESC-P1 fails).

This result suggests a rule that acts only on confident estimates. A clean test needs runs that neither rule has seen, so this file fixes the rule on the stored seeds 1–3 and tests it on new seeds 4–6.

**The rule (`python poc/gp_eval.py --esc2`, `esc2_main` as committed with this file).**
- For each translator, set and outcome of the failed quick count (no solution / several / no count), the middle step's value is computed on seeds 1–3, as in PREREG_ESC.
- The middle step is skipped for that outcome only when the upper end of its 95% bootstrap interval over puzzles is below 0. Nothing is tuned.
- Rules learned (fixed by this file; `--learn`):
  - gp  q8b    learned on seeds 1-3: skip middle step for nothing; value no count +4.2 [-6.5, +17.3] (n=72); none +1.5 [-4.1, +8.4] (n=158); several +3.1 [-3.6, +10.7] (n=170)
  - gp  q32a   learned on seeds 1-3: skip middle step for nothing; value no count -1.5 [-7.0, +4.4] (n=80); none +3.3 [-7.4, +15.6] (n=40); several -1.1 [-5.8, +4.6] (n=119)
  - gp  oss20  learned on seeds 1-3: skip middle step for several; value no count -6.4 [-13.1, +0.9] (n=86); none +2.0 [-7.8, +14.7] (n=35); several -15.4 [-19.1, -11.1] (n=114)
  - gp  oss120 learned on seeds 1-3: skip middle step for no count, several; value no count -9.0 [-12.6, -5.2] (n=27); none -4.0 [-10.9, +7.3] (n=26); several -9.2 [-13.2, -4.7] (n=101)
  - lgp q8b    learned on seeds 1-3: skip middle step for no count; value no count -4.8 [-7.7, -2.5] (n=26); none -2.0 [-8.2, +5.0] (n=61); several +0.9 [-9.6, +12.8] (n=45)
  - lgp q32a   learned on seeds 1-3: skip middle step for no count; value no count -2.3 [-4.1, -0.9] (n=21); none +15.1 [-3.8, +49.7] (n=6); several +5.3 [-5.5, +18.8] (n=29)
  - lgp oss20  learned on seeds 1-3: skip middle step for none; value no count -3.0 [-6.1, +0.4] (n=6); none -4.8 [-10.0, -0.5] (n=7); several -8.2 [-14.7, +0.5] (n=23)
  - lgp oss120 learned on seeds 1-3: skip middle step for no count, several; value no count -4.5 [-9.6, -1.8] (n=4); none -1.9 [-3.7, +1.6] (n=3); several -3.6 [-4.6, -2.8] (n=8)

**Fresh runs (seeds 4, 5, 6).**
- `gtr`, `gtrt` and `think` for Qwen3-8B, Qwen3-32B-AWQ, gpt-oss-20b and gpt-oss-120b on the GridPuzzle (215) and Mitra-Baral (94) test sets.
- Settings exactly as the stored seeds 1–3 runs; second server, all 8 GPUs.
- Scoring v2: the stored grid of program rows, and thinking answers re-read from their text, as `poc/gp_rescore.py`.
- Compared, paired by puzzle and seed: ESC2 ladder − fixed ladder, and ESC2 − think. 95% bootstrap over puzzles, a puzzle's seeds together.

**Predictions.**
- **ESC2-P1 (decides).** ESC2 − fixed ladder: the point is at or above −0.5 in all 8 cells, and the interval is above 0 for GridPuzzle with gpt-oss-20b and with gpt-oss-120b.
  - Derivation: the expected gain is the skipped share times the value. GridPuzzle gpt-oss-20b: 18% of puzzle-seeds × 15.4 ≈ +2.7. gpt-oss-120b: 20% × 9.2 ≈ +1.8.
  - The Qwen3 GridPuzzle rules skip nothing, so those cells are exactly 0.
  - Mitra-Baral skips touch fewer than 10% of puzzle-seeds, so their effect is at most about +0.5.
- **ESC2-P2.** GridPuzzle gpt-oss-120b, ESC2 − think: the point is above 0.

**Decision.**
- **P1 holds:** the paper's ladder becomes ESC2, the fixed ladder its ablation. The method statement becomes: after a failed count, the next step is chosen from how the count failed, using the model's own past runs, and only on confident evidence.
- **P1 fails:** the fixed ladder stays. The gpt-oss grid effect is reported as descriptive, and the escalation choice remains an open gap.

**Prior work.** As PREREG_ESC: FrugalGPT (2305.05176), AutoMix (2310.12963), and cascade routing (Dekoninck et al. 2410.10347). The confident-skip rule is the standard way to act on estimated cascade values under estimation error; the signal (an exact solver count and how it failed) is ours.

## Interim (2026-11-11 17:0x UTC): gpt-oss cells complete; both gain conditions of ESC2-P1 hold, and ESC2-P2 holds
Run in the container, since the thinking answers are re-read with `run_zebra.zl_extract`. The learned rules were re-derived after this hour's grid rescore (`fr_resc`) and are identical to the ones registered above.

| Cell, fresh seeds 4–6 | ESC2 − fixed ladder | ESC2 − think | Fixed − think |
|---|---|---|---|
| GridPuzzle, gpt-oss-20b (645 puzzle-seeds) | +2.7 [+1.6, +3.9] | +6.6 [+3.4, +10.1] | +3.9 [+0.2, +7.7] |
| GridPuzzle, gpt-oss-120b | +2.1 [+1.3, +3.0] | +2.6 [+0.7, +4.6] | +0.5 [−1.7, +2.7] |
| Mitra-Baral, gpt-oss-20b | +0.0 [+0.0, +0.1] | −2.5 [−5.6, +0.4] | −2.5 [−5.6, +0.4] |
| Mitra-Baral, gpt-oss-120b | +0.2 [+0.1, +0.3] | +2.1 [+0.7, +3.8] | +1.9 [+0.5, +3.6] |

- The two derived gains were +2.7 and +1.8; the fresh seeds give +2.7 and +2.1.
- The Qwen3 GridPuzzle rules skip nothing, so those cells are 0 by construction.
- P1 now waits only on the Qwen3 Mitra-Baral cells. Partial so far: Qwen3-8B +0.8 [+0.2, +1.8] on 94 of 94 puzzles but 240 of 282 puzzle-seeds; Qwen3-32B-AWQ 2 puzzles.

## Result (2026-11-11 18:1x UTC): ESC2-P1 fails on Mitra-Baral with Qwen3-32B-AWQ, so the fixed ladder stays. ESC2-P2 holds.
`python poc/gp_eval.py --esc2` in the container, all fresh seeds 4–6 runs that decide P1 complete.

| Cell, fresh seeds 4–6 | ESC2 − fixed ladder | ESC2 − think | Fixed − think |
|---|---|---|---|
| GridPuzzle, Qwen3-8B (nothing skipped) | +0.0 | +1.9 [−2.7, +6.7] | +1.9 [−2.7, +6.7] |
| GridPuzzle, Qwen3-32B-AWQ (nothing skipped) | +0.0 | +17.5 [+9.1, +26.1] | +17.5 [+9.1, +26.1] |
| GridPuzzle, gpt-oss-20b | +2.7 [+1.6, +3.9] | +6.6 [+3.4, +10.1] | +3.9 [+0.2, +7.7] |
| GridPuzzle, gpt-oss-120b | +2.1 [+1.3, +3.0] | +2.6 [+0.7, +4.6] | +0.5 [−1.7, +2.7] |
| Mitra-Baral, Qwen3-8B | +0.8 [+0.2, +1.7] | −0.1 [−5.2, +5.4] | −0.9 [−6.1, +4.7] |
| **Mitra-Baral, Qwen3-32B-AWQ** | **−0.9 [−2.3, +0.1]** | +2.5 [−1.1, +6.1] | +3.4 [−0.5, +7.6] |
| Mitra-Baral, gpt-oss-20b | +0.0 [+0.0, +0.1] | −2.5 [−5.6, +0.4] | −2.5 [−5.6, +0.4] |
| Mitra-Baral, gpt-oss-120b | +0.2 [+0.1, +0.3] | +2.1 [+0.7, +3.8] | +1.9 [+0.5, +3.6] |

The Qwen3 GridPuzzle cells are 0 by construction; their remaining fresh runs only add puzzle-seeds to the last two columns (Qwen3-8B 500 of 645, Qwen3-32B-AWQ 187 of 645 at this time).

- **ESC2-P1 fails.** Mitra-Baral with Qwen3-32B-AWQ is −0.9, below the −0.5 floor. The two gain conditions hold (+2.7 and +2.1, derived +2.7 and +1.8).
- **ESC2-P2 holds.** GridPuzzle gpt-oss-120b, ESC2 − think +2.6 [+0.7, +4.6].
- **Decision (as registered):** the fixed ladder stays as the paper's method. The gpt-oss GridPuzzle gain of the confident skip is reported as descriptive, and the escalation choice remains an open gap.

**Root cause, read from the rows.** The middle step's value for a failed outcome has two parts: rare 100-point rescues (the middle step reaches count 1 and is right while thinking is wrong, or the reverse) and a token term (the middle step's extra tokens).
- In the failing cell, the learned skip was "no count". On seeds 1–3 it had 21 puzzle-seeds over 14 puzzles, with 0 rescues and a token term of −2.3. The bootstrap cannot draw an event it never saw, so its interval [−4.1, −0.9] described only the token cost.
- On seeds 4–6 the same outcome had 3 rescues in 23 puzzle-seeds (3 puzzles), so the middle step was worth +11.1 there.
- In the cells that gained, the skipped outcome ("several" for both gpt-oss models) had about 100 puzzle-seeds, few rescues (3 and 4) and a large token term (−15 and −11), and it repeated on the fresh seeds (−16.4 and −10.8).

**Post-hoc check, not registered (`poc/gp_eval.py --esc3`).** A valid bound for this value treats the rescue rate exactly: Clopper–Pearson on the number of puzzles with a rescue, plus the token term's bootstrap bound.
- Learned on seeds 1–3, it keeps only gpt-oss-20b's "several" skip (bound −0.7). On seeds 4–6 that gives +2.7 [+1.6, +3.9] with no cell below 0.
- Learned on seeds 1–6, it skips nothing. gpt-oss-20b's "several" bound becomes +0.7: the fresh seeds added puzzles with a rescue, and a puzzle's seeds do not add independent evidence. So there is nothing to test on seeds 7–9, and no run is made.
- Conclusion: with about 200 puzzles per set, a skip that is safe against rare rescues cannot be certified. The gain the bootstrap rule found is real on these two cells, but the rule that finds it is not safe elsewhere.
