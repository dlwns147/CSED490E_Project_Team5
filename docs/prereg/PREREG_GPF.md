# Pre-registration GPF: the grid method as now composed, once on fresh seeds (GPF), and the closure as a check on one-solution quick translations (DCLC)

Written 2026-11-13 10:3x UTC, before any run of seeds 14–16 exists and before the closure is applied to any one-solution program of the
held-out ladders H1–H4.

## Part 1, GPF: every step was chosen on seeds 4–9; the composed method is tested once on seeds 14–16

**Why.** The course method's steps were each accepted by its own registered test (GRLLF, DCL, PEERT, addendum A), but the composed method's
headline number (GridPuzzle 92.9% at 4.6k tokens, seeds 7–9) is read from the same seeds on which addendum A chose gpt-oss-120b. A number for
the report that no choice has seen needs fresh seeds. Seeds 14–16 have never been run for any model on these sets.

**Method (frozen).** ① the RL-trained quick translation (`q8bgrllf0` / `q8bgrllf1`, cross-fitted folds as stored) → ② gpt-oss-120b quick
translation (reasoning effort low) → ③ Qwen3-8B thinking translation (`gtrt`) → ④ Qwen3-8B thinking (`think`, 32,000 tokens). A step is
accepted at exactly one solution; the distinctness closure (PREREG_DCL) is applied to any step with two or more. Every step is paid.
**Baseline:** Qwen3-8B thinking only (step ④ alone, same runs). GridPuzzle (215) and Mitra-Baral (94), seeds 14, 15, 16, scoring v2.
Runs: ① and ③/④ on one GPU of the second server and the Slurm RTX 3090s, ② on another GPU of that server. Evaluation: `python poc/gp_conj.py gpf`.

**Predictions (from seeds 7–9).**
- **GPF-P1 (decides):** method − thinking, utility, paired over puzzles (each puzzle's mean over seeds): interval above 0 on both sets.
  Predicted GridPuzzle +33.9 (seeds 7–9: 92.9% at 4.6k vs 62.5% at 11.6k), Mitra-Baral +10.8.
- **GPF-P2 (reported):** accuracy of the method within 3 points of seeds 7–9 (92.9%, 95.7%); a larger drop is read as selection on seeds 7–9.

**Decision.** P1 holds → the report's headline numbers for the grid method are those of seeds 14–16, with seeds 7–9 as the development
numbers. P1 fails on a set → the report states the method's numbers on that set as not confirmed.

## Part 2, DCLC: the closure as a check on one-solution quick translations

**Why (root cause, read 2026-11-13 10:2x UTC).** After DCL and the peer step, the largest loss of the grid method is the trained quick
translation accepting one wrong grid: 23 of 46 wrong puzzle-seeds on GridPuzzle and 11 of 12 on Mitra-Baral (seeds 7–9). Reading the gold grid
against each wrong one-solution program (`results/gp_goldbreak.json`, 34 puzzles) shows the commonest shape: the program reads "X is either A or
B" inclusively (A and B may be the same entity) **and** contains one constraint that no clue states ("Max Fusion != 2009", "$11 million !=
Nan Norman", "port == $28.99", "Indio != Greg", "wedding == 125", "Jorge != 1985"), which removes the other solutions. The wrong grid then has
A and B as the same entity. 6 of the 8 puzzles where thinking returns the same wrong grid have this shape. The puzzle's convention (DCL)
says A ≠ B. So the closure applied to a one-solution quick program leaves **no** solution exactly when that program's one grid breaks the
convention. Two more puzzles (gp-0718, gp-9390, 12 puzzle-seeds) are a misspelled name in an otherwise right program; that is a separate
issue and not part of this rule.

**Rule (frozen; `distinct_closure`, unchanged).** For a quick translation (steps ① and ②) with exactly one solution: re-count with the
closure's expressions added; if the count becomes 0, the step is treated as failed and the ladder moves on. Otherwise, nothing changes. The
thinking translation (③) is not checked: on the discovery data its flags are mostly right programs (GridPuzzle 26 right, 7 wrong), and by
idea 36's rule a flag pays only if the wrong share among flags exceeds (1 − A_next) + 0.5 k_next / 100, which ③'s next step (thinking,
61% right on the puzzles that reach it, 48k tokens) makes about 0.63.

**Already seen (discovery, decides nothing).** Seeds 4–9, ladder ① → ③ → ④ with DCL: the check flags 27 one-solution programs on GridPuzzle
(22 wrong) and 14 on Mitra-Baral (12 wrong); utility +0.7 [+0.2, +1.4] and +1.6 [+0.2, +3.5]. "More clue expressions than numbered clues" as
a flag was also tried (46 flags, 28 wrong) and is not part of the rule.

**Held-out data.** The four held-out ladders of PREREG_DCL (H1 Qwen3-8B seeds 1–3; H2 Qwen3-32B, H3 gpt-oss-20b, H4 gpt-oss-120b, seeds
1–6; quick `gtr` → `gtrt` → `think`, DCL on): the check on each model's own quick step. These programs have never been closed at count 1.
And Part 1's seeds 14–16 (steps ① and ②), reported.

**Derivation of the prediction.** Gain ≈ wrong flagged × (next steps' accuracy on them × 100 + saved nothing) − right flagged × (next
steps' extra tokens × 0.5/1000 + lost right answers). Base models' quick steps leave more several-solution programs and fewer one-solution
wrong ones, so the gain is smaller than on the trained translator: about +0.5 on GridPuzzle per model, about +1 on Mitra-Baral.

**Predictions.**
- **DCLC-P1 (decides):** pooled over H1–H4 (each puzzle's mean over model-seeds), check − no check on GridPuzzle: interval above 0.
- **DCLC-P2 (no harm):** Mitra-Baral pooled, lower bound above −1.0.
- **DCLC-P3:** among flagged one-solution quick programs (pooled H1–H4, both sets), at least half are wrong.
- **DCLC-P4 (reported):** per model; and on Part 1's seeds 14–16, the method with the check − without.

**Decision.** P1 and P2 hold → the check joins steps ① and ② (a free step, no tokens). P1 fails → it stays out, and the discovery numbers
are reported as exploratory.
