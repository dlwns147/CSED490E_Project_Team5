# Pre-registration B2: established forgetting-mitigation baselines vs self-replay (E4)

Written 2026-10-13 17:42 UTC, before any data, training or evaluation below. Results are appended below without editing this section.

**Reference points (E4, results/PREREG_E4_REPLAY.md; Qwen3-8B, leave-hull-out LoRA r=16, 2 epochs):** base hull K0 109/120, trained-task
K8 225/240; A (no replay) hull K0 48, trained K8 236; **B (self-replay: + 270 of the student's own programs on 5 other tasks) hull K0 118,
trained K8 240**; C (teacher replay) hull K0 36.

**Baselines (same base model, same LoRA hyper-parameters and evaluation as E4):**
- **A′:** A retrained on this stack (replication; also the endpoint for WiSE-FT).
- **WiSE-FT (Wortsman et al. 2022):** weight interpolation θ = (1 − α)·θ_base + α·θ_A′ for α = 0.25, 0.5, 0.75 (no training).
- **SDFT (Yang et al. 2024):** the base student (no thinking) rewrites each of A's 600 teacher programs "in its own words" given the same
  prompt and the teacher program; rewrites that pass all 8 variants replace the teacher program, others keep it; then the same LoRA.
- **RFT / self-SFT:** no teacher: the student's own verified no-thinking programs on the same 4 trained tasks and the same K0/K4/K8
  training prompts (200 per K), same LoRA.
**Evaluation:** hull K0 and K8 (seeds 1–2, 120 each; hull is never trained), the 4 trained tasks under K8 (240), diameter and delaunay-fixed (60 each).

**Predictions.**
- B2-P1: on the WiSE-FT curve no α reaches both hull K0 ≥ 110 and trained K8 ≥ 236; B is not dominated by any α.
- B2-P2: SDFT protects hull better than A: hull K0 ≥ A′ + 30, with trained K8 within 3 points of A′.
- B2-P3: self-SFT does not damage hull (≥ 100/120) but gives little robustness: trained K8 ≤ base + 3 points (≤ 232/240).
- B2-P4: A′ replicates A within ±12 on hull K0 (48 ± 12).
Cost per arm: data generation tokens + training minutes, reported with the results.


---
## Results (appended 2026-10-13 18:08 UTC; predictions above unedited)

Qwen3-8B, leave-hull-out; correct on all 8 variants (k of n); `poc/analyze_b2.py`. Cost = extra generation + training.

| arm | hull K0 (unseen, 120) | hull K8 (unseen) | 4 trained tasks K8 (240) | diameter (60) | delaunay-fixed (60) | extra cost |
|---|---|---|---|---|---|---|
| base Qwen3-8B | 109 | 23 | 225 | 54 | 55 | – |
| A (E4) / **A′ (retrained)** | 48 / **53** | 25 / 29 | 236 / 237 | 60 / 60 | 59 / 56 | 600 teacher programs, 9 min LoRA |
| WiSE-FT α = 0.25 | 120 | 17 | 217 | **36** | 58 | none (weight averaging, CPU) |
| WiSE-FT α = 0.5 | 119 | 18 | 222 | 60 | 55 | none |
| WiSE-FT α = 0.75 | 96 | 29 | 236 | 60 | 59 | none |
| SDFT (student rewrites the teacher's programs; 537/600 verified) | 85 | **58** | 236 | 60 | 52 | ≈ 184k tokens of rewrites |
| self-SFT / RFT (student's own verified programs, no teacher) | 104 | 16 | 235 | 60 | 54 | ≈ 1,440 programs sampled |
| C: teacher replay (E4) | 36 | 14 | 240 | 60 | 45 | 270 teacher programs |
| **B: self-replay (E4)** | **118** | 31 | **240** | 60 | 47 | ≈ 3k student programs sampled for 270 verified |

- **B2-P1 confirmed:** WiSE-FT trades one goal for the other: α ≤ 0.5 keeps hull (119–120) but loses the in-task gain (217–222, below
  the base 225); α = 0.75 keeps the gain (236) but hull falls to 96. No α matches self-replay (118 and 240). α = 0.25 also breaks
  diameter: 24 of its 60 programs skip the stated count line (the base: 6), so averaging weights is not a monotone path.
- **B2-P2 confirmed (barely):** SDFT halves the damage (hull K0 85 vs 53; threshold 83) with the in-task gain kept (236). Unexpectedly it is
  the only arm that *improves* the unseen hull under 8 helpers (58 vs 23 base, 29–31 for A′ / self-replay): 92 of its 120 K8 hull programs
  keep the monotone chain and 53 are correct.
- **B2-P3 not confirmed:** self-SFT without any teacher gives almost the full in-task gain (235 vs 237 for A′) and little damage (104).
  The caveat this exposes: the 4 trained tasks have little K8 headroom (base 225/240); the task with large helper harm is hull, which is
  held out, so E4's main contrast is the damage on hull, not the in-task gain.
- **B2-P4 confirmed:** A′ 53 vs A 48.
- Delaunay-fixed: every training arm except WiSE-FT changes it by −11 to +4; self-replay is among the worst there (47), as in E4.
- Net: self-replay is the only method that keeps both the unseen task (118) and the in-task gain (240), at the price of sampling the
  student until it has enough verified programs on other tasks; SDFT is the best trade-off for robustness on the unseen task under helpers.
