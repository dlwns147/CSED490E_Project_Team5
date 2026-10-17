# Pre-registration E4b: self-replay when the in-task gain is large (answering the B2 caveat)

Written 2026-10-13 21:28 UTC, before any training or evaluation below. Results are appended below without editing this section.

**Why.** In E4 / B2 the held-out task was hull, so the trained tasks had little headroom under 8 helpers (base 225/240) and the
comparison rested on the unseen task alone. Here hull IS trained (its K8 robustness gain was large in E5: 15 → 90%), and the unseen
task is **convex** (polygon convexity test), which E5 found damaged under 8 helpers (68 → 34–39%).
**Arms (Qwen3-8B LoRA, same hyper-parameters as E4):** A5 = the E5 "mixed" data (600 verified thinking-teacher programs on the 5 core
tasks, K0/K4/K8 thirds); B5 = A5 + 210 of the student's own verified no-thinking programs on tri, overlap, rectunion, lattice (the E4
self-replay set without convex); C5 = A5 + the thinking teacher's programs for exactly the same 210 prompts.
**Evaluation (no thinking, T = 0.7, `--stdlib`):** convex K0 and K8 (seeds 1–2, 120 each; base measured on this stack); the 5 core tasks
under K8 (seed 1, 300) for the in-task gain.

**Predictions.**
- E4b-P1: A5 damages convex under K8 by ≥ 15 points vs the base; B5 stays within 5 points of the base.
- E4b-P2: B5 − C5 on convex K8 ≥ +15 points.
- E4b-P3: in-task: B5 within 3 points of A5 on the 5 core tasks under K8, and both ≥ base + 15 points.


---
## Results (appended 2026-10-13 21:45 UTC; predictions above unedited)

Correct on all 8 variants; differences paired, 95% bootstrap CI.

| arm | convex K0 (unseen, 120) | **convex K8 (unseen, 120)** | 5 core tasks K8 (300) | of which hull K8 (60) |
|---|---|---|---|---|
| base Qwen3-8B | 89 | 81 | 236 | 11 |
| A5: no replay | 71 | **55** (−21.7 [−30.8, −11.7]) | **296** (+20.0) | 57 |
| B5: + student's own programs | 76 | **80** (−0.8 [−8.3, +6.7]) | **295** (+19.7) | 55 |
| C5: + teacher's programs, same prompts | 66 | **42** (−32.5) | 294 (+19.3) | 54 |

- **E4b-P1 confirmed:** without replay the unseen convex task loses 21.7 points under 8 helpers; with self-replay it loses 0.8.
- **E4b-P2 confirmed:** B5 − C5 = +31.7 [+21.7, +41.7] on convex K8; teacher replay is again worse than no replay.
- **E4b-P3 confirmed:** the large in-task gain survives self-replay (core K8 236 → 295 vs 296 without replay; hull 11 → 55 of 60).
- Not registered: on clean convex prompts (K0) some damage remains in every arm (base 89 → 71 / 76 / 66; B5 −10.8 [−22.5, +0.8]).
- Failure types under K8: A5 and C5 failures are mostly wrong on the original input (logic 39 / 43) and degenerate cases (14 / 29); B5's
  look like the base model's (variant-dependent 20, logic 17).
- This answers the B2 caveat: with a large in-task gain at stake, self-replay keeps both the gain and the unseen task.
