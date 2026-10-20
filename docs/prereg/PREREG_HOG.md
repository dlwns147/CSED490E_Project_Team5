# Pre-registration HO-G: does the recipe hold on held-out geometry tasks? (the geometry half of the held-out test)

Written 2026-10-20 03:5x UTC, before running. Results are appended below without editing this section.

**Why.** The optimization half of the recipe now holds on two unseen benchmarks (OptMATH, OptiBench; PREREG_HO.md). The geometry half rests on
the U1 suite (9 tasks: hull, area2, pip, segs, close, lattice, rectunion, delaunay, diameter), on which the policy was found. This tests it on
four geometry tasks never used in any recipe test: `overlap` (do two convex polygons share a point), `convex` (is a polygon convex,
collinear vertices allowed), `tri` (points strictly inside a triangle) and `clip` (exact twice-area of the intersection of two convex
polygons). They were defined earlier as held-out tasks for the distractor studies (E2 / held-out section), with exact reference solvers and the
same 8 metamorphic variants (poc/run_geo.py); the per-task facts (needed helpers; for clip the Sutherland-Hodgman hint) were written then.
**Setup** (poc/queues/queue_s2_hog.sh; U1 / SIZE settings): --stdlib, n_inst 12, T 0.7, seeds 1–3; models that fit one 24 GB GPU:
gpt-oss-20b (low; thinking = medium), Qwen3-14B-AWQ, Qwen3-8B. Arms: base (the 8-helper toolbox offered, as U1), fact (only the needed
helpers + the algorithm hint where defined), think (toolbox + thinking, 16k). Correct = right on all 8 variants. Free check = the program runs
on its own instance and its outputs on the metamorphic variants are consistent (no answers; analyze_n10.geo_check). Policies: BASE, FACT,
THINK, FF (fact first; think only if the check fails). Tokens = output tokens.
**Predictions** (from U1: FF 86.7–87.5% pooled, the best policy at 2.5–2.7k):
- HOG-P1 (core rule): FF ≥ THINK − 1 point at ≤ 60% of THINK's tokens, for each model (seed means).
- HOG-P2: FACT ≥ BASE + 5 points for both Qwen3 models; ≤ +3 for gpt-oss-20b (it rarely misuses helpers).
- HOG-P3: FF is the best fixed policy (utility = accuracy − 0.5 × ktokens) for each model.

## Interim, gpt-oss-20b (2026-10-20 03:45 UTC; poc/analyze_hog.py; 96 items × 3 seeds; Qwen3 thinking arms running)
BASE (8-helper toolbox) 81.2% @ 1.13k; FACT (needed helpers / hint) 95.5% @ 0.68k; THINK 93.1% @ 1.69k; **FF 99.0% @ 0.82k** (100 / 100 / 96.9%).
HOG-P1 holds for gpt-oss-20b (FF above THINK at 49% of its tokens); HOG-P2 refuted in the good direction (FACT − BASE = +14.3, predicted ≤ +3:
on these tasks the 8-helper toolbox hurts gpt-oss-20b, as in H4); HOG-P3 holds (FF best utility).

## Results, all three models (2026-10-20 04:24 UTC; results/hog_analysis.log; 96 items × 3 seeds)
| held-out geometry | BASE (8-helper toolbox) | FACT (needed helpers / hint) | THINK | **FF** (fact; think if the check fails) |
|---|---|---|---|---|
| gpt-oss-20b | 81.2% @ 1.13k | 95.5% @ 0.68k | 93.1% @ 1.69k | **99.0% @ 0.82k** |
| Qwen3-14B-AWQ | 48.6% @ 0.96k | 80.6% @ 0.62k | 76.7% @ 8.58k | **84.4% @ 2.92k** |
| Qwen3-8B | 42.4% @ 1.30k | 45.8% @ 0.56k | **74.0% @ 9.82k** | 59.7% @ 4.55k |
- **HOG-P1 holds for gpt-oss-20b and Qwen3-14B-AWQ** (FF above THINK at 49% / 34% of its tokens) and is **refuted for Qwen3-8B** (FF 14.3 points
  below THINK). **HOG-P2 holds for Qwen3-14B-AWQ** (+32.0) and gpt-oss-20b (+14.3, above the predicted ≤ 3), **refuted for Qwen3-8B** (+3.4).
  **HOG-P3** (FF best utility) holds for gpt-oss-20b and Qwen3-14B-AWQ, not for Qwen3-8B (THINK 69.1 vs FF 57.4).
- Why Qwen3-8B fails: its check leaks. 64 of its 216 fact programs pass the metamorphic check yet are wrong (convex 19, tri 27, clip 18) —
  consistent but wrong logic that every transformed copy reproduces — and FF keeps them; for Qwen3-14B-AWQ 7, for gpt-oss-20b 1. Seeds checked:
  thinking programs differ across seeds (5 / 96 identical code), so the equal per-seed counts (71 / 71 / 71) are a coincidence.
**Reading:** on held-out geometry the recipe holds for the two stronger 24 GB models; for the weakest one the free check leaks
(consistent wrong programs) and always thinking is better — the same limit as 'checks leak' on word problems, here decisive.
