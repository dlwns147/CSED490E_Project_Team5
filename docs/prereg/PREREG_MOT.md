# PREREG_MOT: the count gate against an agreement cascade on logic grids, registered 2026-11-11 03:1x UTC, before any sample has run

**Why.** The paper's claim is that a cheap answer with a free check, escalating to thinking only when the check fails, beats always thinking. The standard training-free way to decide when to escalate is agreement: sample the cheap mode several times and escalate when the samples disagree. The closest published method is the Mixture-of-Thought cascade (Yue et al., ICLR 2024, 2310.03094). It samples K chain-of-thought answers and K program answers from the weak model, accepts the majority when enough of them agree, and otherwise calls the strong model. A reviewer will ask whether the count is better than that, or only cheaper. Trips already have equal-setting baselines (SC-3 and D&P-3, FINDINGS 2026-11-10 21:1x). Grids have only thinking. This file adds the agreement cascade there, with the same model's thinking as the strong step.

**Prior work read for this.**
- Yue et al. 2310.03094: MoT cascade, CoT + PoT samples, vote or verify, threshold τ swept; escalation is to a stronger model, and there is no solver check.
- Agreement cascades without training: ABC (2407.02348), semantic agreement (2509.21837).
- JointThinking (2508.03363) uses agreement between thinking and no-thinking answers, but always runs thinking, so it buys accuracy, not tokens. It is not a cost baseline.
- SatLM (2305.09656) abstains on UNSAT/AMBIG. Logic-LM (2305.12295) repairs on solver errors and accepts the solver's answer. Exact-cover zebra solving (ICLR 2026 workshop on logical reasoning, outstanding paper) refines under- and over-constrained encodings by uniqueness. None of them compares against a thinking model at equal tokens.

**Reported rows, computed before this file from the stored runs (scratch script, no model call; not predictions).** Here "SatLM gate" means: first-round translation, accept a count of 1, else think. "Logic-LM gate" means: accept any first-round solution (count ≥ 1), else think. Ladder minus each gate, utility, three seeds, puzzle bootstrap:

| Translator, set | Ladder − think | Ladder − SatLM gate | Ladder − Logic-LM gate |
|---|---|---|---|
| Qwen3-8B, GridPuzzle | +4.6 [+0.4, +8.9] | +2.7 [−0.6, +6.3] | +10.9 [+6.2, +15.8] |
| Qwen3-8B, Mitra-Baral | +2.9 [−3.3, +9.2] | −1.4 [−5.5, +2.9] | +5.6 [+0.4, +11.1] |
| Qwen3-32B-AWQ, GridPuzzle | +11.3 [+7.4, +15.3] | +2.9 [+0.7, +5.3] | +4.9 [+0.9, +8.9] |
| Qwen3-32B-AWQ, Mitra-Baral | +0.4 [−2.9, +3.7] | +1.6 [−0.4, +4.1] | +8.5 [+2.7, +14.5] |
| gpt-oss-20b, GridPuzzle | +5.5 [+1.8, +9.3] | −1.3 [−3.6, +1.2] | +2.5 [−2.3, +7.3] |
| gpt-oss-20b, Mitra-Baral | +3.5 [+1.0, +6.2] | +0.6 [−0.6, +1.8] | +4.2 [+0.7, +7.8] |

Reading: what carries the ladder is escalating on a count other than 1; the repair rounds and the middle step add little (as on trips). Accepting any solution, as Logic-LM does, loses up to 11 points. So the uniqueness part of the check is what pays.

**Setup.**
- Same puzzles as PREREG_GP (GridPuzzle test 215, Mitra-Baral test 94) and translators `q8b`, `q32a`, `oss20` (gpt-oss: effort low for both quick arms).
- Quick program samples: `run_zebra.py --gp <tag> gtr <seed> --rounds 1`, the PoT sample (first round only, no feedback); its answer is the solver's first solution whatever the count.
- Quick chain-of-thought samples: `run_zebra.py --gp <tag> direct <seed>`, the thinking prompt with thinking off (4,096 tokens).
- Three replicates k = 1, 2, 3, each with seeds 10k+1, 10k+2, 10k+3 for both arms. Replicate k escalates to the stored `think` run of seed k and is paired with the registered ladder of seed k.
- **MoT cascade (CoT + PoT, K = 3 + 3).** Answers are compared after the normalization of `gp_score` (case, punctuation, plural s, numbers by their digits). A sample with no answer (crash, no solution, no parsable JSON) counts as a vote for nothing. Let a be the most common answer and c its share of the 6 samples. If c ≥ τ, answer a; else think. All 6 samples are paid, plus thinking when it runs.
- **PoT vote (K = 3).** The same with the 3 program samples only.
- **τ.** Every value the share can take (1/6 … 6/6; 1/3 … 3/3) is computed. The headline uses the best τ on the same set and translator: an oracle choice that favours the baseline. Also reported: τ picked on the other set (GridPuzzle ↔ Mitra-Baral) and the whole curve.

**Predictions** (utility, plain registered ladder minus the baseline, paired by puzzle and seed, 10,000-draw puzzle bootstrap):
- **M1.** GridPuzzle, MoT cascade at its best τ: point estimate above 0 for all three translators, interval above 0 for at least two.
  - Derivation: without thinking, a full grid answer is rarely right (GPT-4-Turbo with CoT: 14 of 274 on GridPuzzle). So CoT samples seldom agree with the program samples, a high τ rarely accepts, and a low τ accepts majorities of correlated wrong programs. The count rejects a program that allows several grids even when other samples share its first solution; the vote cannot. The vote also pays 6 samples every time.
- **M2.** GridPuzzle, PoT vote at its best τ: point estimate at or above 0 for all three translators.
  - Derivation: at τ = 1 the PoT vote accepts only when all three programs agree, which costs 3 translations and covers fewer puzzles than a count of 1 in one round (first-round count-1 shares 0.30 / 0.48 / 0.46).
- **M3.** Mitra-Baral (small grids, where CoT answers are more often right): point estimates of both differences at or above −2. A tie is reported as a tie.

**Decision.**
- If M1 holds: the paper states that the count beats an agreement cascade on grids even with the cascade's τ chosen on test.
- If M1 fails for two or more translators: the claim narrows to "the count matches agreement at lower cost" or less, by the numbers.
- M2 failing means the program vote is the stronger gate. The paper then reports the vote as the gate to use and the count as a cheaper approximation.

**Also reported:** coverage and precision of each gate at the chosen τ; the number of accepted wrong answers where two or more program samples share the same wrong grid (correlated misreadings, the mechanism behind the false accepts); direct-arm accuracy and tokens.

**Run.** On the paper-extension GPU server, one lane per translator and set. Evaluation: `python poc/gp_eval.py --mot <tag>`, written before the samples come back.
