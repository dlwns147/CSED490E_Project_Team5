# PREREG_GRL: plain RL on the quick grid translation, cross-fitted over the human-written puzzles; GridPuzzle and Mitra-Baral, registered 2026-11-12 02:1x UTC, before any training round

**Why.**
- On puzzles written by people, prompting has run out. Two registered rule methods (RULE3G, RULE4) leave Mitra-Baral flat. On GridPuzzle the ladder buys accuracy with tokens: break-even price 1.0 for Qwen3-8B (FINDINGS 2026-11-11 07:5x).
- The ladder's cost on GridPuzzle comes from the puzzles the quick step does not finish. 60% of puzzle-seeds go on to the thinking translation and then to thinking, at 28.2 ktok and 62.7% accuracy (seeds 4–6).
- The quick step can do better on many of these. Over 18 stored runs, its first round is right with one solution on 20.8% of GridPuzzle runs per puzzle, but on 39.1% of puzzles at least once. Mitra-Baral: 35.6% and 56.4%. So the model already writes the right program for about twice as many puzzles as it does on a given run.
- RL with an exact reward sharpens toward what the model can already produce. That is what plain RL did for SQL and tool calls (CV-1, TC-RL), and what it partly did on word problems (WP-RL: +4.7 points quick right). This is §1's "what should be trained when prompting runs out", applied to the project's grid ladder.

**Prior work** (read 2026-11-12):
- **Schrader et al. 2512.17093** (Bosch). LLMs write ASP for grid puzzles. SFT (and DPO) on partial encodings that the clingo solver checks against the gold, built from Mitra-Baral's 50 training puzzles. They found 26 of them duplicated in the test set and removed them. Evaluated on Mitra-Baral and GridPuzzle with best-of-N search. Llama-3.3-70B reaches 55.4 on LogicPuzzles with SFT and 66.8 with search, and about 55.5 on GridPuzzle (prompt pipeline with search); 8B models needed the 70B model's data. There is no RL, no gate against thinking, and no token accounting.
- **SAT-RL, Sun and Meel 2610.14402.** RL (DAPO) teaches Qwen3.5-4B/9B multi-turn Z3 tool use on synthetic SAT-Bench problems. Reward: a logic-equivalence check plus answer correctness. 97.2% in domain, and Enigmata 33.9 → 59.9. The setting is thinking with tools, not a cheap translation gated by a count, and it has no human-written grids.
- **LogicPuzzleRL 2506.04821** trains direct solving with GRPO on generated puzzles, solvers only build the data.
- **Ours differs.** The quick no-thinking translation is trained with the exact reward (one solution, the gold grid), labels only in training. It is then used as the first step of the count-gated ladder against thinking, on human-written puzzles, with tokens counted.

**The method (`poc/gp_train.py`, `poc/slurm/grl_lane.sh`, as committed with this file).**
- WP-RL's loop: Qwen3-8B, LoRA r 16, GRPO without std normalisation, 8 samples per puzzle, 16 puzzles per round, one step per round, lr 2e-5, no KL, 4 epochs.
- Prompt: arm `gtr`'s first round. Reward 1 if the program has one solution and its grid is the gold (scoring v2), else 0.
- **Cross-fitting.** The 309 test puzzles of both sets (215 GridPuzzle, 94 Mitra-Baral) are split into two folds. Copies are joined first: puzzles whose value sets overlap by Jaccard ≥ 0.9, which covers Mitra-Baral's 25 dev–test and 3 test–test copies. The fold is crc32 of the component's smallest test id mod 2, giving 140 and 169 test puzzles.
- Fold f's model trains on every puzzle outside fold f's components: dev and the other fold's test puzzles of both sets, 246 and 216 puzzles. It is evaluated only on fold f's test puzzles, so no test puzzle is seen by the model that translates it.
- **Evaluation.**
  - Arm `gtr` with the fold's adapter, all 3 rounds as before, seeds 4–9 (tags `q8bgrl0`, `q8bgrl1`).
  - The ladder is trained `gtr` → base `gtrt` → base `think`, with the stored base rows of the same seeds. Every step is paid.
  - Utility differences per puzzle-seed, 95% bootstrap over puzzles, as RULE3G. Command: `python poc/gp_eval.py --grl` (to be added before the evaluation runs, reading these tags).

**Derivation (before any run).**
- A puzzle-seed that becomes a right quick pass skips the rest of the ladder. The rest is 62.7% right at 28.2 ktok on GridPuzzle (81.7% at 20.2 on Mitra-Baral), so it gains G = 100(1 − A) + 0.5k = 51.4 (28.4).
- A new wrong pass loses L = 100A − 0.5k = 48.6 (71.6).
- So Δutility ≈ G·Δright − L·Δwrong:
  - GridPuzzle, +5 points right and +1 wrong: +2.1. At +10 right: +4.6.
  - Mitra-Baral, +5 right and +1 wrong: +0.7.
- These assume the moved puzzles look like the escalated pool. They are likely easier than it, so G is an upper estimate.
- Interval half-widths (RULE4 with six seeds): about 2 on GridPuzzle and 2.5 on Mitra-Baral.

**Predictions.**
- **GRL-P1 (mechanism).** GridPuzzle, seeds 4–9 pooled: the trained quick step's right one-solution share (after its 3 rounds) rises by at least 5 points over base `gtr` (base, seeds 4–6: 31.9%). Count-1 precision falls by no more than 2 points.
- **GRL-P2 (decides).** GridPuzzle: ladder(trained `gtr`) − ladder(`gtr`), seeds 4–9, interval above 0.
- **GRL-P3.** Mitra-Baral: the same difference, lower bound above −2.0.
- **GRL-P4 (reported).** Ladder(trained) − `think`, accuracy and ktok separately, with the break-even price, on both sets.

**Decision.**
- **P2 and P3 hold:** plain RL on the quick translation, cross-fitted, is stated as the grid method for human-written puzzles. The trained translator becomes the ladder's quick step, and the paper reports it as labels used in training only.
- **P1 holds but P2 fails:** RL raised the quick step, but not enough to move the ladder. The training-free ladder stays, and the shortfall is read against the derivation (G overestimated, or wrong passes).
- **P1 fails:** RL does not sharpen this translation (WP-RL's pattern). The ladder stays training-free.

**Runs.** On the paper-extension server. Fold 0 and fold 1 run in parallel, each with a vLLM GPU and a trainer GPU. Base `gtr`, `gtrt` and `think` for seeds 4–9 are the RULE4 runs (seeds 7–9 still finishing).

## Result (2026-11-12 03:1x UTC): P1, P2 and P3 hold; the RL-trained translator becomes the quick step

**What ran.** Both folds trained to the end (fold 0: 62 rounds, 246 puzzles × 4 epochs; fold 1: 54 rounds). Each fold's final adapter ran arm `gtr` on its own held-out test puzzles, seeds 4–9, both sets. The base `gtr`, `gtrt` and `think` rows for seeds 4–9 are complete. Command: `python poc/gp_eval.py --grl`.

| Seeds 4–9 | Ladder with base `gtr` | Ladder with trained `gtr` | Think alone |
|---|---|---|---|
| GridPuzzle (1290 puzzle-seeds) | 69.6% at 18.31 ktok, utility 60.5 | **74.7% at 14.37 ktok, utility 67.5** | 63.4% at 11.53 ktok, utility 57.6 |
| Mitra-Baral (564) | 88.5% at 9.71 ktok, utility 83.6 | **90.8% at 6.73 ktok, utility 87.4** | 87.1% at 6.31 ktok, utility 83.9 |

- **P1 holds.** GridPuzzle quick step right with one solution: 31.9% → 55.2% (+23.3 points; at least +5 predicted). Count-1 precision rises, 82.4% → 91.8% (no more than 2 points down was allowed). Mitra-Baral: 49.6% → 69.5%, precision 92.1% → 94.9%. The quick step costs 1.12 ktok against 1.01.
- **P2 holds.** GridPuzzle ladder(trained) − ladder(base): utility **+7.0 [+4.0, +10.2]**, accuracy +5.0 points, −3.93 ktok.
- **P3 holds.** Mitra-Baral: **+3.8 [+0.3, +7.4]** (lower bound above −2.0), accuracy +2.3, −2.98 ktok.
- **P4 (reported).** Against thinking: GridPuzzle +9.8 [+5.7, +14.1], +11.2 points at +2.85 ktok, break-even price 3.95 per ktok (the base ladder: +2.8 [−1.0, +6.7], break-even 0.91). Mitra-Baral +3.5 [−0.4, +7.8], +3.7 points at +0.41 ktok, break-even 8.99 (base ladder −0.3).
- **Against the derivation.** It predicted +4.6 at +10 points right on GridPuzzle. The gain is +23 points right with fewer wrong passes, so +7.0 is below the linear reading. As expected, the moved puzzles are easier than the escalated pool, so G was an upper estimate.

**Checks that the gain is not leakage or a trick** (scratch analyses, not registered):
- **Per fold.** GridPuzzle 32.8% → 56.9% and 31.2% → 53.8%; Mitra-Baral 43.0% → 70.2% and 55.2% → 69.0%.
- **Same story template in training or not.** Many puzzles share a story with other puzzles (same first sentence, other names and clues). On GridPuzzle test puzzles with such a sibling in the fold's training set (123): 29.5% → 52.6%. Without one (92): 35.1% → 58.7%. Mitra-Baral: 56.0% → 73.0% with, 42.4% → 65.5% without. The gain does not need a sibling.
- **No pinned answers.** Trained programs still write one entry per clue (1.05 entries per puzzle clue against 1.07 for the base; none below 0.8). They fix fewer cells to constants than the base (0.32 against 0.52 per program). The count stays a check of the translation, not of a guessed grid.
- **Coverage.** At matched k (6 runs each, after 3 rounds), GridPuzzle pass@6 is 46.0% for the base and 69.3% trained. Of the 116 puzzles the base never got right in 6 runs, the trained model got 58 at least once; it lost 8 that the base got. Whether this holds at large k is registered as PREREG_GRLK.

**Prior work, compared.** Schrader et al. (2512.17093) fine-tune with SFT on solver-checked ASP from Mitra-Baral's training puzzles. They report about 55 on GridPuzzle and 55.4 (66.8 with search) on LogicPuzzles for Llama-3.3-70B. Their numbers use their own pipeline and scoring, so they are not directly comparable. Our run of their search with Qwen3-8B (gts, FINDINGS 2026-11-10 11:5x) reached 50.4% at 4.3 ktok on GridPuzzle and 56.0% at 1.6 ktok on Mitra-Baral. The trained quick step alone reaches 55.2% at 1.12 ktok and 69.5% at 0.59 ktok.

**Decision (as registered).** P2 and P3 hold. Plain RL on the quick translation, cross-fitted, is the grid method for human-written puzzles. The trained translator becomes the ladder's quick step, and labels are used in training only.
