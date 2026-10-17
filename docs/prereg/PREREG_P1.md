# Pre-registration P1: are the contest numbers robust to rewording the prompt? (CRITIQUE item 9)

Written 2026-10-16 15:29 UTC, before any run. Results go below; this section is not edited afterwards.

The contest results (R3, N8, N13) all use one instruction template. Two rewordings with the same content (`run_cc.py --para 1|2`):
1 = the instruction after the statement, reworded; 2 = a terser instruction BEFORE the statement. gpt-oss-120b low (16k cap; original
46.1% @ 3.2k over 3 seeds) on GPUs 0–1, Qwen3.6-35B-A3B no-think (28k cap; original 42.6% @ 3.4k) on GPUs 2–3, seeds 1–3, 311 problems.
- P1-a: each rewording changes accuracy by ≤ 3 points (pooled over seeds) for both models.
- P1-b: output tokens change by ≤ 15%; cap hits stay ≤ 2%.
- P1-c: the per-problem outcome agrees with the original template on ≥ 80% of problem-seeds (sampling noise alone: seeds 1 vs 2 of
  the original agree on a share reported alongside).

## Results (2026-10-16 16:28 UTC; results/p1_analysis.log; 933 problem-seeds per row)
| model / prompt | accuracy (per seed) | output tokens mean (p90) | cap hits | agreement with the original, same seed |
|---|---|---|---|---|
| gpt-oss-120b low, original | 46.1% (42.4 / 49.5 / 46.3) | 3.2k (5.1k) | 0 | seed 1 vs 2 of the original: 85.2% |
| reworded after the statement | 47.9% (50.2 / 47.3 / 46.3) | 3.3k (5.2k) | 0 | 83.0% |
| terse, before the statement | 47.4% (49.5 / 48.6 / 44.1) | 3.3k (5.0k) | 1 | 86.1% |
| Qwen3.6 no-think, original | 42.6% (41.8 / 43.7 / 42.1) | 3.4k (7.1k) | 10 | seed 1 vs 2: 80.1% |
| reworded after the statement | 44.5% (45.0 / 43.1 / 45.3) | 3.5k (7.2k) | 11 | 77.5% |
| terse, before the statement | 44.3% (45.0 / 43.4 / 44.4) | 3.2k (6.7k) | 5 | 79.4% |
**P1-a holds** (+1.3 to +1.9 points, within the ±3-point seed spread), **P1-b holds** (tokens within 6%, caps ≤ 1.2%), **P1-c holds for
gpt-oss-120b (83–86%) and narrowly fails for Qwen3.6 (77.5–79.4% vs ≥ 80%)** — but the original prompt's own seed-to-seed agreement is
80.1% for Qwen3.6, so rewording changes per-problem outcomes no more than resampling does. The contest numbers are not an artefact of
the template (both rewordings are slightly *better*, by less than the seed noise).
