# Pre-registration H7: a cheap newer model, Qwen3.6-35B-A3B (MoE, ≈ 3B active, FP8), on the key benchmarks

Written 2026-10-16 07:58 UTC, before any run. Results appended below without editing this section.
**Why.** All cost claims so far use dense or 20–120B models; a mixture-of-experts model with ≈ 3B active parameters is the cheapest
modern option per token. Runs: contest geometry no-think (3 seeds, 28k cap, its no-think answers may be verbose like Qwen3.8);
Solomon plain / integer reader + robust (2 seeds, then V1 reuse on the 8 mining instances).
- H7-P1: contest no-think 25–45% (between Qwen3-32B 12% and Qwen3.8 48%); × 3 + example check adds ≥ 8 points.
- H7-P2: Solomon: plain ≤ 20% per instance; reader + robust ≥ 70% per instance; V1 reuse ≥ 94% on the 48 held-out instances.

## H7 results, part 1 (2026-10-16 08:32 UTC)
**Contest geometry, no thinking, 28k cap, seeds 1–3:** 41.8 / 43.7 / 42.1% → **42.6% @ 3.4k tokens** (10 of 933 hit the cap, none without
code); × 3 samples + the statement's examples check **54.0% @ 10.3k** (+11.4 points); any of 3: 58.5%. Same table: gpt-oss-120b low 46.1%
@ 3.2k (× 3 + check 53.4% @ 9.7k); Qwen3.8-27B no-think (16k cap) 33.0% @ 4.2k with 481 of 933 cut off. **H7-P1 holds** (in 25–45%; +11.4 ≥ 8).
Raw programs: like Qwen3.8, the no-think answer reasons inside long code comments, but finishes (1% at the cap).
**Solomon per instance (2 seeds):** plain 0 / 56 and 0 / 56; integer reader + robust snippet 21 / 56 and 20 / 56 (**37%**) at 1.8k tokens.
**H7-P2: plain ≤ 20% holds; reader + robust ≥ 70% refuted** (gpt-oss-120b low 100%, Qwen3.8 81% on the same prompt). Raw failures
(re-run): plain = the usual input / API errors (int('NUMBER') on the header, wrong RoutingIndexManager arguments, invented
`SetGlobalCostCoefficient`); with the reader: 36 crashes (depot / customer index shifts, invented `search_for_best_solution`), 23
time-window violations and 12 missing customers, mostly from scaling travel times by 10,000 but not the windows or service times, or
dropping the service time: varied modelling slips, the case where reuse should help. V1 reuse on the 8 mining instances: running.

## H7 results, part 2 (2026-10-16 08:59 UTC): V1 reuse (poc/analyze_reuse_curve.py, results/h3/reuse_curve_q36.log)
Reader + robust: 8 of 16 mining candidates feasible on ≥ 1 mining instance; reuse cost curve k = 1 / 2 / 4 / 8 / 16 candidates:
46 / 73 / 94 / 100 / 100% of the 48 held-out instances feasible at 2 / 3 / 7 / 13 / 26k tokens in total (a new program per
instance: 37%, ≈ 1.8k each). **H7-P2 reuse part holds (100% ≥ 94%).** Plain: 0 of 16 candidates feasible anywhere → 0% (reuse
needs one working candidate, as for Qwen3-32B). Distance gap of the reused program: results/h3/reuse_q36.log.
Reused program (results/h3/reuse_q36.log): feasible on 8 / 8 mining and 48 / 48 held-out instances, median gap 1.29% to the reference, 44 / 48 within 5%; 26k generation tokens in total.
