# PREREG_BUD: the count gate against budget-forced thinking on grids and trips, registered 2026-11-11 04:5x UTC, before any test-split run

**Why.** The paper's claim is that a cheap translation with a free count check, escalating only when the check fails, beats thinking at our utility (100 · right − 0.5 · ktok). Every comparison so far is against thinking at its full length. The obvious reply is to think less: cut the think at a budget and force the answer (budget forcing, s1, 2501.19393). Qwen3 documents the same mechanism as its thinking budget, with a fixed early-stopping sentence. NoThinking (Ma et al., 2504.09858) compares thinking and no-thinking at matched budgets this way. If a budget-forced think at a budget chosen on test matches the ladder, the ladder's gain is only a token saving that a budget gives for free.

**Prior work read for this.**
- s1 (2501.19393): budget forcing, which suppresses or forces the end of thinking at a token count.
- Qwen3 quickstart, "thinking budget": generate up to the budget; if the think has not ended, append "Considering the limited time by the user, I have to give the solution based on the thinking directly now." and close it.
- NoThinking (2504.09858): at matched budgets, no-thinking beats thinking at low budgets on maths. Our MoT `direct` arm is its no-thinking sample with a vote (PREREG_MOT).
- ZebraLogic (2502.01100): grid accuracy grows with reasoning tokens.
- Our own HO-TB (PREREG_HO): a 2k cut kept most accuracy on easy optimisation sets but lost 11–17 points on hard ones.
- None compares budget-forced thinking with a solver-checked translation.

**Bounds from the stored full thinks (no model call; computed before this file).** For budget B, an upper bound on the cut think's utility assumes a cut never loses a right answer and costs no answer tokens. A lower bound counts only thinks that ended within B as right and charges 4,096 answer tokens for each cut one. Ladder minus the upper bound, at the best B of 1k, 2k, 4k, 8k (the most the baseline could gain), and the share of thinks that ended within 4k:

| Cell | Ladder − full think | Ladder − upper bound, best B | Thinks ended within 4k |
|---|---|---|---|
| GridPuzzle, Qwen3-8B | +3.5 | −1.7 | 9% |
| GridPuzzle, Qwen3-32B-AWQ | +10.9 | +7.0 | 21% |
| GridPuzzle, gpt-oss-20b | +4.0 | −2.8 | 12% |
| Mitra-Baral, Qwen3-8B | +0.4 | −2.3 | 30% |
| Mitra-Baral, Qwen3-32B-AWQ | +0.8 | −0.8 | 65% |
| Mitra-Baral, gpt-oss-20b | +1.7 | −0.4 | 54% |
| Trips, Qwen3-8B | +6.8 | +2.2 | 0% |
| Trips, Qwen3-32B-AWQ | +15.4 | +12.4 | 41% |
| Trips, gpt-oss-20b | −1.0 | −7.6 | 14% |
| Trips, gpt-oss-120b | +5.7 | +1.8 | 22% |

(Plain ladder; means over problem-seeds, so they differ slightly from the registered per-puzzle means.)

So a cut that loses nothing would tie or beat the ladder in most cells; the question is how much a cut loses. On GridPuzzle at 4k, 79–91% of thinks are cut. The ladder keeps its lead there if those cut thinks lose more than about 2–3 points of accuracy in all.

**Setup.**
- Arm `thinkb` (run_zebra.py --gp, run_plan.py): the think prompt as `think`. One think runs to 8,000 tokens at the think arm's sampling (temperature 0.7, top-p 0.95; gpt-oss effort high). For each budget B in 1,000, 2,000, 4,000, 8,000:
  - the first B tokens are kept, the Qwen3 early-stopping sentence is appended, the think is closed, and the answer is generated (up to 4,096 tokens);
  - a think that ended by itself within B is answered once, and that answer is used for every such B.
- Raw completions in each model's chat format (Qwen3; gpt-oss harmony). Tokens charged = kept think tokens + answer tokens.
- Translators and sets as PREREG_MOT: GridPuzzle (215) and Mitra-Baral (94) test sets with `q8b`, `q32a`, `oss20`; Amonkar et al.'s 100 trips with `q8b`, `q32`, `oss20`, `oss120`. Seeds 1, 2, 3, paired with the registered ladder and full think of the same seed.
- Scoring v2 on grids; the gold plan on trips.
- **Baseline at its best:** the budget among 1k, 2k, 4k, 8k and the stored full think that does best against the ladder on the same set (an oracle choice that favours the baseline). Evaluation: `python poc/gp_eval.py --bud <tag> --score2` (grids), `--bud <tag> --np` (trips), written before any test run.
- A dev pilot (Qwen3-8B and gpt-oss-20b, GridPuzzle dev, 8 dev trips, seed 1) runs first and is read for crashes and format only.

**Predictions** (utility, ladder minus the baseline at its best, paired by problem and seed, 10,000-draw problem bootstrap):
- **BUD-P1.** GridPuzzle: point estimate above 0 for all three translators, interval above 0 for at least two.
  - Derivation: grid thinking is search over assignments, and 79–91% of thinks are still searching at 4k. A cut there leaves a partial or guessed grid, so it loses far more than the 2–3 points the ladder can spare (HO-TB lost 11–17 points at 2k on hard sets). At 8k, about 60% are cut and the tokens saved are smaller, so the upper bound is already below the ladder for Qwen3-32B-AWQ and close to it for the others.
- **BUD-P2.** Trips: point estimate above 0 for Qwen3-8B, Qwen3-32B-AWQ and gpt-oss-120b. Derivation: the upper bound is above 0 for all three.
- **BUD-P3.** Mitra-Baral: point estimates at or above −2 for all three translators. Thinks there are short, so a budget saves little.
- **BUD-P4.** gpt-oss-20b on trips (where full thinking already ties the ladder): no prediction, reported as measured.

**Also reported:** accuracy, tokens and cut share at each budget; whether any cut beats full thinking in accuracy (the overthinking check).

**Decision.**
- BUD-P1 and BUD-P2 hold: the paper states that the ladder beats thinking at any budget we tried, with the budget chosen on test.
- BUD-P1 fails for two or more translators: the paper's baseline becomes budget-forced thinking. The ladder's gain is stated only where it survives. A ladder whose last step is the budget-forced think is the next registered test.

## Pilot read (2026-11-11 05:0x UTC, format only)
Qwen3-8B and gpt-oss-20b, dev, seed 1: every cut answer parsed (grids and trips), cuts happened at every budget below the think's own end, and tokens were charged as registered. A cut think often keeps reasoning in its answer (Qwen3-8B, 1k budget: up to 2.5k answer tokens); that is budget forcing as specified and is charged. No change to the setup. Test lanes started on seven GPUs.

## Interim result (2026-11-11 06:0x UTC): trips complete, BUD-P2 holds; gpt-oss-20b grids complete
Ladder − budget-forced think, utility, three seeds (`gp_eval.py --bud`). Cut accuracy at 1k / 2k / 4k / 8k, against full thinking:
- **Trips.** Qwen3-8B 13 / 13 / 15 / 28% (full 33%); Qwen3-32B-AWQ 25 / 28 / 43 / 48% (full 47%); gpt-oss-20b 14 / 18 / 32 / 51% (full 71%); gpt-oss-120b 16 / 25 / 41 / 60% (full 77%).
- **Best baseline:** full thinking for Qwen3-8B (+6.8 [+0.9, +12.8]), gpt-oss-20b (−1.1 [−6.8, +4.9], tie; BUD-P4) and gpt-oss-120b (+5.8 [+1.0, +10.9]). For Qwen3-32B-AWQ it is the 8k cut, whose accuracy matches full thinking at fewer tokens (+13.9 [+6.4, +21.4]). **BUD-P2 holds.**
- **gpt-oss-20b grids** (P1 and P3 wait for the Qwen3 lanes): GridPuzzle cuts 18 / 26 / 40 / 56% (full 79%); the best baseline is full thinking, +3.9 [+0.5, +7.5]. Mitra-Baral cuts 16 / 49 / 81 / 92% (full 96.5%); full thinking again, +1.8 [−0.5, +4.1].
- **Harness check.** Thinks that ended by themselves within 8k are right as often as stored full thinks of the same length (GridPuzzle 95.8% against 95.6%; Mitra-Baral 98.8 / 97.0; trips 78 / 76, 71 / 67, 97 / 92, 92 / 93). So the raw-completion path is not what lowers the cut accuracy; the cut is.
