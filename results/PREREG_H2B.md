# Pre-registration H2b: on hard contest geometry, does sampling + a label-free check beat paying for reasoning?

Written 2026-10-14 05:30 UTC, before any run below. Results are appended below without editing this section.

**Design.** The 31 problems of H2. Eight samples per problem (seeds 1–8; seeds 1–3 are the H2 runs) for Qwen3-32B without thinking and
gpt-oss-20b / 120b at low effort. **Label-free selection:** keep the samples whose program passes the statement's public example tests (the
model sees them in the statement; hidden tests are never used), and take the first such sample (seed order); if none passes, take seed 1.
Reported: single sample, public-test-filtered best-of-k (k = 3, 8), oracle any-of-k, tokens; compared with the single-attempt reasoning
conditions of H2 (Qwen full thinking / think-1,024; gpt-oss medium).
**Predictions.**
- H2b-P1: for gpt-oss-120b, filtered best-of-8 at low effort is within 5 points of a single medium-effort attempt (65.6%) but costs ≥ 3 × its
  tokens, so medium effort dominates on cost.
- H2b-P2: for Qwen3-32B, filtered best-of-8 without thinking (≈5.4k tokens) solves more than full thinking (30.1% at ≈13.9k tokens).
- H2b-P3: the public-test filter recovers ≥ 70% of the gap between a single sample and the oracle any-of-8 (pooled over the three models).

## Results (2026-10-14 06:24 UTC; analysis: poc/analyze_h2b.py; raw rows results/h2/cc_<cond>_s<seed>.jsonl)

| condition (31 problems) | single sample | public-test-filtered best-of-k | oracle any-of-k | output tokens / problem |
|---|---|---|---|---|
| Qwen3-32B no thinking, k = 8 | 10.1% | 29.0% | 32.3% | 5.5k |
| Qwen3-32B think-1,024, k = 3 | 25.8% (s1) / 22.6% (mean) | **38.7%** | 41.9% | 10.1k |
| Qwen3-32B full thinking, k = 1 / 3 | 30.1% (mean) | 38.7% (k = 3) | 38.7% | 14.0k / 41.6k |
| gpt-oss-20b low, k = 8 | 37.1% | 45.2% | 61.3% | 12.6k |
| gpt-oss-20b medium, k = 3 | 52.7% | **64.5%** | 64.5% | 26.2k |
| gpt-oss-120b low, k = 3 / 8 | 49.5 / 48.4% | 58.1 / 61.3% | 61.3 / 67.7% | 9.3k / 24.9k |
| gpt-oss-120b medium, k = 1 / 3 | 65.6% (mean) | 67.7 (s1) / **71.0%** | 67.7 / 80.6% | 6.5k / 19.2k |

- **H2b-P1 confirmed.** gpt-oss-120b filtered best-of-8 at low effort: 61.3%, 4.3 points below one medium attempt (65.6%), at 3.8 × its
  tokens (24.9k vs 6.5k). One medium attempt dominates; filtered best-of-3 at medium (71.0% at 19.2k) is the top of the frontier.
- **H2b-P2 refuted (narrowly).** Qwen3-32B filtered best-of-8 without thinking: 29.0% vs full thinking 30.1% (one problem apart), at 40%
  of the tokens (5.5k vs 14.0k). Not "more", but equal accuracy at much lower cost. The cheapest strong point is unplanned: think-1,024 with
  filtered best-of-3, 38.7% at 10.1k tokens, above both.
- **H2b-P3 refuted.** The filter recovers 85% (Qwen), 33% (gpt-oss-20b) and 67% (gpt-oss-120b) of the single → oracle-of-8 gap; pooled
  40 / 66 points = 61% (< 70%). The public examples are weak checks: of the samples that pass them, 17 / 42 (Qwen), 27 / 119 (20b) and
  28 / 148 (120b) fail a hidden test. Rerunning those 72 samples on the first failing test: 66 wrong answers, 1 timeout, 1 crash, 4
  numeric-precision misses (1 near the problem's 1e-6 limit, 3 on multi-answer 1271_C / 67_E with exact checking). So the filter's misses are
  real logic errors, not checker artifacts; most fall on five problems rated 1900–2900 (536_C, 592_E, 703_C, 73_F, 1575_B).
- Reading: on hard problems the cheapest gains come from a short reasoning budget plus a cheap check, not from more effort or more blind
  samples. The public-example check works where the model is weak (Qwen: most passing samples are right) and saturates where it is strong
  (the examples are passed by many wrong programs). n = 31: every difference here is ± 10–15 points; the full set (≈ 300 problems) is next.
