# Pre-registration F2R: F2 (a needed tool with a hidden contract) on a standard benchmark — Solomon VRPTW

Written 2026-10-15 20:32 UTC, before any LLM run. Results are appended below without editing this section.

**Why.** F2 was shown on synthetic geometry (an orientation-dependent helper); the compact proposal's plan item (2) asks for it on a
standard benchmark. The one natural case so far (our float-returning reader) was confounded.
**Design.** Prompt = the task statement + the 12-line file example + the integer reader + the robust OR-Tools snippet with its scaling
advice removed and replaced by "Tint = Dint = travel_times(xy) (helper below)" + one helper the model "should use", in three versions:
- round: integer travel times rounded to the nearest integer (hidden contract: can underestimate a leg by up to 0.5);
- ceil: rounded up (safe: every integer-feasible schedule is feasible under exact times);
- roundwarn: round, with a two-line comment stating the contract.
Calibration (no LLM, done before writing this): our correct OR-Tools model with rounded times is feasible on 33 / 56 instances (23
time-window violations under exact checking), with ceil times on 56 / 56.
Models: gpt-oss-120b low and Qwen3.8-27B no-think; 2 seeds × 56 instances per arm.
**Predictions.**
- F2R-P1: ceil ≥ 90% feasible for both models; round ≤ 65% (the calibration's 59% plus a few programs that rescale or ignore the helper).
- F2R-P2: in the round arm, ≥ 70% of the infeasible results are time-window violations (the contract, not crashes).
- F2R-P3: the warning recovers ≥ half of the round → ceil gap for gpt-oss-120b (a reasoning model reads the comment) and < half for
  Qwen3.8 (as Qwen3 did with the Delaunay warning in F2).

## Results (2026-10-15 21:29 UTC; feasible of 112 = 56 instances × 2 seeds)
| helper | gpt-oss-120b low | Qwen3.8 no-think |
|---|---|---|
| ceil (safe) | 106 (95%) | 105 (94%) |
| round (hidden contract) | 77 (69%); infeasible: 31 time window, 4 crash | 67 (60%); 34 time window, 11 crash |
| round + warning comment | 72 (64%); 37 time window | 73 (65%); 31 time window |
Programs call the helper in 101–111 of 112 cases and copy it verbatim (the warning comment included); none of the round-arm programs
switches to rounding up (0 contain `ceil(`; 2 of 112 for Qwen3.8 with the warning). Output tokens 1.1–1.3k in every arm.
- **F2R-P1 half:** ceil ≥ 90% holds for both; round ≤ 65% holds for Qwen3.8 (60%), narrowly not for gpt-oss-120b (69%).
- **F2R-P2 holds:** 89% (120b) and 76% (Qwen3.8) of the round-arm failures are time-window violations.
- **F2R-P3 half:** the warning does not help gpt-oss-120b at all (64%, predicted ≥ half of the gap) and recovers 15% of the gap for
  Qwen3.8 (< half, as predicted).
- F2 replicates on a standard benchmark: a needed tool with a hidden contract costs 26–34 points of feasibility, fixing the tool removes
  the loss, and stating the contract in a comment does not, as in the synthetic lattice task (warning 17–19 vs fixed 46–49 of 60).
