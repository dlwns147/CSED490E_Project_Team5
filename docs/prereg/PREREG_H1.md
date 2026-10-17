# Pre-registration H1: do the findings and fixes survive when the problem itself is hard (large inputs, time limit)?

Written 2026-10-14 03:27 UTC, before any run below. Results are appended below without editing this section.

**Why.** Our tasks are textbook problems on 6–20 points; reasoning models solve almost all of them, and any algorithm passes the time
limit. Here the same task statements get large inputs (n = 2,000 and 20,000 points, integer coordinates up to 10^7) and the prompt states
"n can be up to 20000; the program must finish within 10 seconds", so an O(n^2) program fails: the algorithm must also be efficient.
**Tasks** (same 8-variant scoring; exact O(n log n) references): hull vertex count (hullL), closest pair (closeL), farthest pair (diamL).
**Models / conditions** (2 seeds, 30 instances × 2 sizes per task): Qwen3-8B and Qwen3-32B-AWQ: no helpers, all helpers (K8), think-1,024 on
K8, M4 (algorithm first); gpt-oss-20b and gpt-oss-120b at low effort: no helpers and K8.
**Predictions.**
- H1-P1: the problems are hard: with no helpers, Qwen3-8B and 32B solve < 60% (pooled), and gpt-oss-20b low < 85%.
- H1-P2: helper steering still matters but can now go both ways: on diamL the offered convex_hull helps (K8 > no helpers for both Qwen
  models), while on hullL K8 < no helpers (polar_sort route).
- H1-P3: think-1,024 beats K8 by ≥ 10 points for both Qwen models; M4 lands between K8 and think-1,024.
On the question "should we generate problems with an LLM?": not tested here; see the note in FINDINGS.


---
## Results (appended 2026-10-14 04:29 UTC; predictions above unedited)

Correct on all 8 variants (fail-fast: the 7 copies are skipped once the original fails); 2 seeds × 120 programs; tokens per program.

| model | no helpers | all helpers (K8) | think-1,024 on K8 | M4 algorithm first |
|---|---|---|---|---|
| Qwen3-8B | 170/240 (hull 80 / closest 54 / farthest 36 of 80) @ 301 | **97** (14 / 31 / 52) @ 916 | **209** (70 / 77 / 62) @ 1,771 | 166 (75 / 54 / 37) @ 681 |
| Qwen3-32B | 166 (71 / 69 / 26) @ 459 | **83** (14 / 48 / 21) @ 496 | **203** (65 / 75 / 63) @ 1,710 | 148 (71 / 56 / 21) @ 958 |
| gpt-oss-20b low | 235 (80 / 76 / 79) @ 583 | 227 (79 / 78 / 70) @ 978 | – | – |
| gpt-oss-120b low | 220 (79 / 78 / 63) @ 1,851 | 234 (80 / 80 / 74) @ 1,450 | – | – |

- **H1-P1 not confirmed:** large inputs do not make these tasks hard: Qwen without helpers 69–71%, gpt-oss-20b low 97.9%. Reasoning
  models know the efficient algorithms; the Qwen failures are real implementation bugs (e.g. rotating calipers advanced with the wrong
  condition, float-based shortcuts on farthest pair; 32B farthest pair 26/80, 42 wrong answers on the original input).
- **H1-P2 half:** the helper steering on hull is stronger than at small sizes (8B 80 → 14, 32B 71 → 14 of 80); the offered `convex_hull`
  helps the 8B on farthest pair (36 → 52, +20.0 [+6.2, +33.8]) but not the 32B (26 → 21). Overall all-helpers costs 30–35 points (small
  inputs: 14–17).
- **H1-P3 confirmed:** think-1,024 beats all-helpers by 47–50 points; M4 lies between them (8B 69%, 32B 62%), but no better than no helpers.
- For gpt-oss the extras are nearly neutral (−3.3 for 20b; +5.8 for 120b, whose own farthest-pair programs improve with `convex_hull`).
