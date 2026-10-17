# Pre-registration H4: do unneeded helpers steer programs on real contest geometry (external validity of F1)?

Written 2026-10-14 11:32 UTC, before any run below. Results are appended below without editing this section.

**Why.** F1 (8 related but unneeded helpers collapse accuracy on some tasks, e.g. convex hull 97 → 8%) and its large-input version H1
(Qwen 70.8 → 40.4%) were shown on our synthetic tasks. On 31 contest problems the helpers changed little (Qwen3-32B no-think 7 vs 8 of
93), but that set is too small. This tests the claim on the 311 validated Codeforces geometry problems.
**Design.** run_cc.py --k8 with CC_SET=full: the statement plus 8 tested geometry helpers drawn per problem from the related pool (orient,
on_segment, segments_intersect, point_in_polygon, dist2, bbox, collinear, polar_sort, is_convex, polygon_area2, convex_hull,
closest_pair_sq; with their dependencies), "you may use these"; 3 seeds; Qwen3-32B no-think (8040) and gpt-oss-20b low (8042). Compared
with the same models without helpers (H2c Part B), paired per problem and seed; helper use read from the programs.
**Predictions.**
- H4-P1: net change within ± 3 points for both models (real failures are misreading and case analysis, not algorithm choice), but with
  flips in both directions: ≥ 10 problem-seeds lost and ≥ 10 gained per model.
- H4-P2: Qwen copies or calls a helper in ≥ 50% of programs, gpt-oss-20b in ≤ 30%; output tokens rise ≥ 20% for Qwen.
- H4-P3: among problem-seeds that flip from solved to unsolved, ≥ 50% of the helper-condition programs call a helper (steering), read from
  the programs.

## Results (2026-10-14 12:29 UTC; poc/analyze_h4.py; 311 problems × 3 seeds, paired with the no-helper runs)

| model | no helpers | 8 helpers | lost / gained (problem-seeds) | programs calling a helper | output tokens |
|---|---|---|---|---|---|
| Qwen3-32B no-think | 12.1% | 13.7% | 55 / 70 | 58% | 702 → 848 (+21%) |
| gpt-oss-20b low | 37.7% | **33.4%** | **96 / 56** (sign test p ≈ 0.002) | 23% | 1,513 → 1,390 (−8%) |

- **H4-P1 half:** Qwen within ± 3 (+1.6, not significant), gpt-oss-20b −4.3 (outside). Flips in both directions as predicted.
- **H4-P2 confirmed:** helper use 58% (Qwen) vs 23% (20b); Qwen tokens +21%.
- **H4-P3 refuted:** of the lost problem-seeds, only 23 / 55 (Qwen) and 26 / 96 (20b) call a helper. Read programs (62 lost 20b pairs
  without helper calls): the 20b model reasons less with the toolbox (median 1,168 vs 1,482 tokens on these pairs) and writes a different,
  wrong solution (e.g. 1195_F: normalises edge directions to one sign, which breaks the Minkowski-sum count). On real problems the toolbox
  acts as a distraction that shortens reasoning, not as steering through helper calls; and here the reasoning model is the one that is
  hurt, the reverse of our synthetic finding (F1: reasoning models immune), at low effort.

## H4b pre-registration (2026-10-14 16:32 UTC, before running): is it relevance, length or the instruction?
Arms on the 311 problems, 3 seeds: gpt-oss-20b low with (u) all 6 unrelated helpers (gcd, is_prime, fib, reverse_words, lower_bound,
lcs_len; ≈ 1.1k characters vs ≈ 2.4k for the related toolbox; same "you may (and should) use" header) and (m) the same 8 related helpers
with the header "Most of them are probably NOT needed for this task: use one only if it directly helps"; gpt-oss-120b low with the 8
related helpers (scale).
- H4b-P1: unrelated helpers cost gpt-oss-20b ≤ 1.5 points (related: −4.3): plausibility, not prompt length, drives the distraction.
- H4b-P2: the "may" header recovers at least half of the loss (≥ 35.5%).
- H4b-P3: gpt-oss-120b low loses ≤ 2 points with the related helpers and still shortens its reasoning by ≥ 5%.

## H4b results (2026-10-14 17:44 UTC; poc/analyze_h4.py; 311 problems × 3 seeds, paired, exact sign test on discordant pairs)

| arm | solved | lost / gained vs no helpers | sign p | programs calling a helper | output tokens |
|---|---|---|---|---|---|
| gpt-oss-20b low, no helpers | 37.7% | – | – | – | 1,513 |
| + 8 related helpers ("should use", H4) | 33.4% | 96 / 56 | 0.001 | 23% | 1,390 |
| + 6 unrelated helpers | 35.6% | 100 / 80 | 0.16 | 6% | 1,327 |
| + 8 related, "most are probably not needed" | 35.4% | 98 / 76 | 0.11 | 16% | 1,477 |
| gpt-oss-120b low, no helpers → + 8 related | 46.1% → 45.3% | 77 / 70 | 0.62 | 34% | 3,246 → 3,247 |
- **H4b-P1 refuted on the point estimate** (unrelated −2.1, predicted ≤ 1.5; not significant): unrelated helpers also shorten 20b's
  reasoning (−12% tokens) and add give-ups (no code 123 → 140), so part of the harm is any extra code in the prompt, not plausibility.
- **H4b-P2 narrowly refuted** (35.4% vs ≥ 35.5%; the "may" header recovers 2.0 of the 4.3 points, related "should" vs "may" p = 0.16).
- **H4b-P3 half:** gpt-oss-120b loses only 0.8 (n.s.), but its reasoning length does not change (0%).
- Reading: on real problems the helper harm is small and specific to the small model at low effort; only the original arm (8 related,
  "should use") is significant. Its mechanism is a shorter reasoning budget when any toolbox is present, a little worse when the helpers
  are plausible and the prompt says to use them. The large synthetic steering effects (F1) do not carry over to these problems.
