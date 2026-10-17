# Pre-registration H2: real contest geometry (CodeContests, Codeforces "geometry" tag)

Written 2026-10-14 03:32 UTC, before any model run below. Results are appended below without editing this section.

**Data.** The 31 Codeforces geometry problems in the locally available CodeContests shards (ratings 800–3400), with their public,
private and up to 30 generated tests. Harness validation (no model): a C++ reference solution passes every kept test for all 31 problems
under our checker (exact tokens or a numeric tolerance of 1e-6 / 1e-4 chosen per problem by the reference).
**Conditions.** The statement + "Write a Python 3 program …" (10 s per test). Qwen3-8B and Qwen3-32B-AWQ: no thinking; no thinking with 8
generic geometry helpers appended (K8); budget-forced thinking 1,024; full thinking (16k). gpt-oss-20b and gpt-oss-120b: low and medium
effort. Seeds 1–3 (93 attempts per condition). Solved = every kept test correct.
**Predictions.**
- H2-P1: the problems are hard: solved ≤ 20% for Qwen3-8B without thinking, ≤ 30% for 32B without thinking, ≤ 60% for gpt-oss-120b medium.
- H2-P2: solve rate falls with rating: problems rated ≤ 1700 are solved at least twice as often as problems rated ≥ 2300 (pooled).
- H2-P3: the generic helpers lower the Qwen solve rate (point estimate below no-helpers for both sizes).
- H2-P4: full thinking gives Qwen the largest gain of its conditions; gpt-oss medium > low for both sizes.


---
## Results (appended 2026-10-14 05:30 UTC; predictions above unedited)

Solved = all kept tests pass; 3 seeds × 31 problems; tokens = output tokens per attempt; truncated = hit the token cap.

| condition | solved (of 93) | rating ≤ 1700 / ≥ 2300 | tokens | truncated |
|---|---|---|---|---|
| Qwen3-8B, no thinking | 9 (9.7%) | 6/27 / 3/48 | 989 | 2 |
| Qwen3-8B, + 8 generic helpers | 7 (7.5%) | 5/27 / 2/48 | 1,308 | 3 |
| Qwen3-8B, think-1,024 | 16 (17.2%) | 9/27 / 4/48 | 4,100 | 31 |
| Qwen3-8B, full thinking (16k cap) | 29 (31.2%) | 12/27 / 7/48 | 13,948 | 54 |
| Qwen3-32B, no thinking | 7 (7.5%) | 5/27 / 1/48 | 669 | 0 |
| Qwen3-32B, + 8 generic helpers | 8 (8.6%) | 4/27 / 3/48 | 836 | 1 |
| Qwen3-32B, think-1,024 | 21 (22.6%) | 10/27 / 7/48 | 3,379 | 16 |
| Qwen3-32B, full thinking (16k cap) | 28 (30.1%) | 15/27 / 3/48 | 13,867 | 55 |
| gpt-oss-20b low / medium | 32 (34.4%) / 49 (52.7%) | 12/27, 20/27 / 8/48, 18/48 | 1,497 / 8,740 | 0 / 22 |
| gpt-oss-120b low / medium | 46 (49.5%) / **61 (65.6%)** | 20/27, 25/27 / 14/48, 22/48 | 3,087 / 6,412 | 0 / 2 |

- **H2-P1 confirmed for Qwen** (≤ 10% without thinking), **not for gpt-oss-120b medium** (65.6% > 60%). These problems are genuinely hard:
  5 of 31 (rated 2100–3400) are never solved by any condition; even the strongest setting fails a third.
- **H2-P2 confirmed:** e.g. gpt-oss-120b medium 25/27 (≤ 1700) vs 22/48 (≥ 2300).
- **H2-P3 not confirmed:** generic geometry helpers change little (8B 9 → 7, 32B 7 → 8); unlike our tasks, these helpers rarely
  name an alternative algorithm for these problems.
- **H2-P4 confirmed:** full thinking is Qwen's best condition (30–31%), but 54–55 of 93 attempts hit the 16k cap; gpt-oss medium > low.
- Harness checks: every problem's C++ reference passes all kept tests; reading failures on easy problems shows real wrong answers (e.g.
  "NO" where "YES"). 7 problems allow several valid answers (reference solutions disagree, or the statement says so); excluding them
  gives the same picture (e.g. gpt-oss-120b medium 65.3%, Qwen3-8B 12.5%). Not checked: 10 gpt-oss-20b-low attempts ended normally without
  an extractable Python block (raw text was not stored; `run_cc.py` now stores it).
