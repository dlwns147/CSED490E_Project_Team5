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
