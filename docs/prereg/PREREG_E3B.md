# Pre-registration: E3b, can a brute-force reference written by the same model catch the errors the metamorphic check misses?

Written 2026-10-13 16:25 UTC, before any brute-force program exists. Results are appended below without editing this section.

**Motivation (E3).** The metamorphic check accepts programs that are wrong on every transformed copy in the same way (Qwen3-8B: 28 of
264 accepted first programs under 8 extra helpers, 21 of 40 on the hard tasks), so a check-gated pipeline never escalates systematic
errors. Differential testing against a deliberately naive reference (cf. ALGO, Zhang et al. 2023: LLM-written brute-force oracles) might.

**Design.** Qwen3-8B, no thinking, T = 0.7, seed 1, `--stdlib`, no toolbox, the task prompt plus one sentence: "Write the simplest
brute-force program you can: correctness matters, speed does not (inputs are small)." (`run_geo_cross.py --brute`), on the same instances
as C1: the 5 core tasks (300) and the hard tasks lattice + rectunion (120). Candidates = the stored C1 seed-1 programs under K0, K8 and hard.
**Differential check:** run candidate and brute-force program on the given instance and its translate / rot90 / mirror / permute / scale
copies (no 10^9 copy: brute force may legitimately be too slow there); agree = same output on all 6 (scale relations as in the MR check).
A brute-force program that crashes or times out on the given instance gives "no verdict" = treated as disagreement (escalate).
**Gate:** accept the first program iff it passes the metamorphic check AND agrees with the brute-force program; otherwise escalate to one
program with budget-forced thinking (1,024; the stored E3 run). Cost = candidate + brute-force + escalation tokens.

**Predictions.**
- B1: of the stage-1 programs that pass the metamorphic check but are wrong (K8: 28, hard: 21), the differential check flags ≥ 60%.
- B2: false alarms: ≤ 15% of correct stage-1 programs are flagged (K0, K8 and hard separately).
- B3: under K8, the gated pipeline is within 3 points of always-think-1,024 (93.0%) at ≤ 0.8 × its tokens (1,555).
- B4 (uncertain): on the hard tasks the gated pipeline is within 5 points of always-think-1,024 (80.8%).


---
## Results (appended 2026-10-13 16:45 UTC; predictions above unedited)

Qwen3-8B; `poc/analyze_e3b.py`. The brute-force programs themselves are correct on all 8 variants for 279/300 core instances, but only
16/120 hard ones (lattice 1/60: the "simple" grid scan mis-handles boundary points; rectunion 15/60).

| condition | MR-accepted but wrong → flagged (B1) | correct programs flagged (B2) | MR-gated → think | **MR + brute-force gated → think** | always think 1,024 |
|---|---|---|---|---|---|
| K0 | 4/6 | 13/269 (5%) | 97.0% @ 422 | 98.3% @ 781 | 97.3% @ 1,311 |
| K8 | **24/28 (86%)** | 17/236 (7%) | 86.3% @ 1,020 | **92.3% @ 1,522** | 93.0% @ 1,555 |
| hard | **19/21 (90%)** | **16/19 (84%)** | 68.3% @ 1,752 | 80.0% @ 2,657 | 80.8% @ 1,735 |

- **B1 confirmed:** the naive reference catches 86–90% of the systematic errors the metamorphic check misses (hull under 8 helpers: 21 of 23).
- **B2 confirmed on the core tasks (5–7%), not on the hard tasks (84%):** there the brute-force program is itself wrong, so it flags
  nearly every candidate and the gate escalates 115 of 120 instances.
- **B3 half:** under K8 the gated pipeline reaches thinking-level accuracy (92.3 vs 93.0, −0.7 [−2.0, +0.7]) but saves nothing (0.98 × tokens):
  writing the brute-force reference costs about as much as a 1,024-token thinking budget. **B4** is met only trivially (80.0 vs 80.8 at
  1.53 × tokens), by escalating almost everything.
- Reading: differential testing against a naive reference does detect invariant errors, but for this model it is not cheaper than
  thinking a little, and it fails where the naive solution is itself hard to write (lattice points). E3's practical conclusion stands:
  a small fixed thinking budget is the cheapest robust default.
