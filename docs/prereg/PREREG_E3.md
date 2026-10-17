# Pre-registration: E3, a deployable "check, then sample, then think" pipeline

Written 2026-10-13 12:20 UTC, before the escalation runs below exist. Results are appended below without editing this section.

**Question (PROPOSAL 4.3, E3).** F4 says: random slips → sample and check; systematic errors → reason. A deployed system does not know
which error it faces. Can the label-free metamorphic (MR) check itself decide how much to spend, and reach thinking-level accuracy at a
fraction of thinking's tokens?

**Pipeline (fixed rule, no tuning):** per instance, (1) one no-thinking program; run the MR check on the given instance (6 transformed
copies); if consistent, output it. (2) Otherwise sample 2 more programs and MR-select among the 3 (consistent candidates, majority vote on
the original-input output). (3) If none of the 3 is consistent (the error repeats: likely systematic), escalate to ONE program written
with budget-forced thinking (1,024 thinking tokens) and output it (a second variant escalates to a self-generated hint instead: the model
first names the standard algorithm, then codes). Cost = output tokens actually spent per instance (checks are CPU, ms each).

**Data.** Qwen3-8B, `--stdlib`, T = 0.7, the three C1 conditions: main 5 tasks with K0 and with K8 helpers (300 instances each), hard
tasks lattice + rectunion (120). Stages 1–2 use the stored C1 seeds 1 / 2 / 3; stage 3 and the baselines use new runs on the same
instances (seed 1): `--think_budget 1024`, `--self_hint`, and full thinking (`--think`, 16k max tokens). Stages are independent samples,
so simulating the pipeline from these runs is exact in distribution.

**Baselines.** single program; always best-of-3 + MR-select; always budget-thinking (1,024); always full thinking.

**Predictions.**
- E3-P1: pipeline accuracy ≥ always best-of-3 + MR in all three conditions.
- E3-P2: pipeline tokens ≤ 0.5 × always-full-thinking tokens in all three conditions.
- E3-P3 (uncertain): under K8 and on the hard tasks, pipeline accuracy within 5 points of always-full-thinking.
- E3-P4: under K0, pipeline accuracy within 1 point of best-of-3 + MR at ≤ 0.5 × its tokens (most instances stop at stage 1).


---
## Results (appended 2026-10-13 13:00 UTC; predictions above unedited)

Qwen3-8B; accuracy = correct on all 8 variants; tokens = mean output tokens spent per instance; `poc/analyze_e3.py`.

| condition | single | best-of-3 + MR | **pipeline** (escalate: think 1,024) | pipeline (escalate: self-hint) | always think 1,024 | always full thinking | stopped at stage 1 / 2 / 3 |
|---|---|---|---|---|---|---|---|
| K0 (300) | 89.7% @ 314 | 98.0% @ 938 | **98.0% @ 365** | 98.0% @ 365 | 97.3% @ 1,311 | 100% @ 3,792 | 275 / 25 / 0 |
| K8 (300) | 78.7% @ 826 | 82.0% @ 2,481 | **84.7% @ 1,120** | 83.7% @ 1,097 | **93.0% @ 1,555** | 97.0% @ 5,571 | 264 / 24 / 12 |
| hard (120) | 15.8% @ 584 | 32.5% @ 1,656 | **53.3% @ 1,816** | 45.0% @ 1,480 | **80.8% @ 1,735** | 99.2% @ 8,463 | 40 / 47 / 33 |

- **E3-P1 confirmed:** pipeline ≥ best-of-3 + MR everywhere (+0.0, +2.7 [+1.0, +4.7], +20.8 [+14.2, +28.3]).
- **E3-P2 confirmed:** pipeline tokens are 0.10 / 0.20 / 0.21 of always-full-thinking.
- **E3-P4 confirmed:** under K0 the pipeline equals best-of-3 + MR (98.0) at 39% of its tokens; 275 of 300 instances stop after one program.
- **E3-P3 not confirmed:** under K8 the pipeline is 12.3 points below full thinking, on the hard tasks 45.8 below. And a *fixed* small
  thinking budget (1,024) beats the pipeline at about the same token cost (93.0 vs 84.7 under K8; 80.8 vs 53.3 on the hard tasks).
- **Why: the check is blind to errors that do not depend on the transformation.** Stage 1 accepts a program when its outputs on the 6
  transformed copies agree. Among accepted stage-1 programs, 6 of 275 (K0), 28 of 264 (K8; 23 of them hull) and 21 of 40 (hard) are
  wrong, almost all wrong on every copy in the same way (a wrong algorithm gives a wrong but transformation-invariant answer). So the
  pipeline never escalates exactly the systematic errors that need reasoning. The metamorphic check routes random slips well and cannot
  route systematic errors; deciding when to think needs another signal (or simply a small fixed thinking budget).
