# Pre-registration H2c: execution agreement (MBR-exec) among the samples that pass the examples; then the full contest-geometry set

Written 2026-10-14 06:25 UTC, before any computation below. Results are appended below without editing this section.

**Why.** H2b: the statement's examples are a weak check for strong models (28 of 148 gpt-oss-120b samples that pass them are wrong).
The standard next step in the literature is to choose among the passing programs by agreement of their outputs on extra inputs
(AlphaCode clustering; MBR-exec, Shi et al. 2022; CodeT uses model-written tests). This is computed offline from the H2b samples.

**Part A (offline, the 31 problems, existing samples).** Selection inputs = CodeContests generated tests with index ≥ 30 (inputs only,
never their outputs; the evaluation uses public + private + generated 0–29, so selection and evaluation inputs are disjoint), at most 20 per
problem. Candidates = samples with code that pass the public examples (if none, all samples with code). Each candidate runs on every
selection input (5 s limit; failure = a unique output); score = number of (other candidate, input) pairs with equal output (the problem's
checker tolerance); pick the top score, ties by seed order. Compared with H2b's first-passing pick at the same k, same tokens (the
selection costs CPU only).
- H2c-P1: pooled over Qwen3-32B no-think k = 8, gpt-oss-20b low k = 8, gpt-oss-120b low k = 8, MBR-exec beats the first-passing pick by
  ≥ 5 points (≥ 5 more problems of 93).
- H2c-P2: gpt-oss-120b low k = 8 with MBR-exec ≥ 64.5% (H2b first-passing 61.3%; one medium attempt 65.6%), i.e. sampling closes most of the
  gap to medium effort but still at ≈ 4 × tokens, so P1 of H2b (effort dominates on cost) stands.
- H2c-P3 (risk): on problems where the passers share a misconception, agreement picks the wrong majority; expected on ≤ 3 problems.

**Part B (full set, after Part A).** All geometry-tagged CodeContests problems that pass reference validation (expected ≈ 250–300), with the
H2b frontier conditions: Qwen3-32B no-think, think-1,024, full thinking; gpt-oss-20b / 120b low and medium; 3 samples each; reported as
accuracy vs tokens per problem with bootstrap CIs, by rating band (≤ 1600, 1700–2200, ≥ 2300). Predictions written before Part B runs.

## Part A results (2026-10-14 06:33 UTC; poc/analyze_h2c.py, CPU only)

| condition (31 problems) | first passing the examples (H2b) | MBR-exec among passers | oracle any-of-k | tokens / problem |
|---|---|---|---|---|
| Qwen3-32B no-think, k = 8 | 29.0% | 29.0% | 32.3% | 5.5k |
| gpt-oss-20b low, k = 8 | 45.2% | **51.6%** | 61.3% | 12.6k |
| gpt-oss-120b low, k = 8 | 61.3% | **64.5%** | 67.7% | 24.9k |
| Qwen3-32B think-1,024, k = 3 | 38.7% | 38.7% | 41.9% | 10.1k |
| gpt-oss-20b medium, k = 3 | 64.5% | 64.5% | 64.5% | 26.2k |
| gpt-oss-120b medium, k = 3 | 71.0% | **74.2%** | 80.6% | 19.2k |

- **H2c-P1 refuted (narrowly):** +3 problems of 93 pooled over the k = 8 conditions (42 → 45; oracle 50), not ≥ 5.
- **H2c-P2 confirmed (at the threshold):** gpt-oss-120b low k = 8 + MBR-exec 64.5% vs one medium attempt 65.6%, at 3.8 × the tokens; effort
  still dominates on cost. Medium k = 3 + MBR-exec, 74.2% at 19.2k, is the new top of the frontier.
- **H2c-P3 confirmed:** MBR-exec never turned a right first pick into a wrong one (0 losses in 6 conditions).
- Why the rest of the gap stays (8 cases read): shared misconceptions (613_A: the 3 wrong Qwen programs agree with each other on all 20
  inputs, the right one is the outlier), selection inputs that do not hit the bug (851_B: 7 passers, 3 wrong, all identical on the 20
  inputs), and precision-only differences that the 1e-6 tolerance cannot separate (293_D, 73_F, 388_E: scores within 1–2 of each other).
  Agreement selection needs inputs that hit edge cases; a model-written edge-case input generator is the obvious next variant (CodeT-like),
  not run.

## Part B predictions (written 2026-10-14 06:37 UTC, before any Part B run; the full set has 355 geometry problems, median rating 2200 vs 2300 for the 31)

Conditions, 3 samples each over all validated problems: Qwen3-32B no-think, think-1,024, full thinking (16k cap); gpt-oss-20b / 120b low
and medium (16k cap). Selection: first sample passing the examples, and MBR-exec among the passers (Part A rule). Results reported
on all validated problems and without the flagged ones (a reference that runs prints different answers), by rating band.
- B-P1: every single-sample accuracy is within ± 8 points of its 31-problem estimate, and the order is gpt-oss-120b medium > gpt-oss-20b
  medium > gpt-oss-120b low > gpt-oss-20b low > Qwen3-32B think ≈ think-1,024 > Qwen3-32B no-think.
- B-P2 (H2b replication): Qwen3-32B think-1,024 with selection over 3 samples ≥ full thinking single sample, at fewer tokens.
- B-P3 (H2b replication): gpt-oss-120b one medium attempt ≥ 3 low attempts with selection, at fewer tokens.
- B-P4: MBR-exec ≥ first-passing in every condition (never lower by more than 1 point) and adds ≥ 2 points for the k = 3 gpt-oss conditions.
- B-P5: the ≥ 2300 band stays below 45% for every condition; the ≤ 1600 band is ≥ 80% for gpt-oss medium.

## Part B results (2026-10-14 10:41 UTC; poc/analyze_h2c.py with CC_SET=full; 311 validated problems; full thinking has k = 1, see FINDINGS 09:4x)

| condition | single (95% CI) | k | first passing the examples | MBR-exec | oracle any-of-k | tokens: single / all k |
|---|---|---|---|---|---|---|
| Qwen3-32B no-think | 12.1% [9.3, 15.1] | 3 | 21.2% | 20.6% | 21.9% | 0.7k / 2.1k |
| Qwen3-32B think-1,024 | 21.8% [18.0, 25.7] | 3 | **30.2%** | 29.9% | 32.2% | 2.9k / 8.8k |
| Qwen3-32B full thinking | 29.9% [25.1, 35.0] | 1 | – | – | – | 13.7k |
| gpt-oss-20b low | 37.7% [33.1, 42.6] | 3 | 47.9% | 48.9% | 51.1% | 1.5k / 4.5k |
| gpt-oss-20b medium | 47.1% [42.2, 52.0] | 3 | 56.3% | 57.2% | 60.5% | 8.7k / 26.2k |
| gpt-oss-120b low | 46.1% [41.3, 51.1] | 3 | 53.4% | 54.3% | 57.6% | 3.2k / 9.7k |
| gpt-oss-120b medium | **56.8%** [52.0, 61.7] | 3 | 61.1% | **62.4%** | 68.2% | 6.8k / 20.3k |

Without the 74 flagged problems every number rises 1–4 points; without flagged and image-dependent statements (159 problems) 1–5 points;
the order never changes. By rating band (single): ≤ 1600: 31–85%; 1700–2200: 12–71%; ≥ 2300: 2.7–34.5%.
- **B-P1 mostly holds:** six of seven singles within ± 8 points of the 31-problem estimates; gpt-oss-120b medium is 8.8 below (56.8 vs
  65.6), and Qwen full thinking is clearly above think-1,024 (29.9 vs 21.8), not "≈". The predicted order holds otherwise.
- **B-P2 confirmed:** Qwen think-1,024 × 3 + example check 30.2% at 8.8k tokens = full thinking 29.9% at 13.7k.
- **B-P3 confirmed:** one gpt-oss-120b medium attempt (56.8% at 6.8k) beats three low attempts + selection (53.4–54.3% at 9.7k).
- **B-P4 half refuted:** MBR-exec never loses more than 0.6 points, but adds only +0.9 to +1.3 (predicted ≥ 2) for gpt-oss at k = 3.
- **B-P5 confirmed:** ≥ 2300 band at most 34.5% single (43.0% with MBR-exec); ≤ 1600 band 80.3% / 85.0% for gpt-oss medium.

## H2d pre-registration (2026-10-15 11:28 UTC, before running): the top of the reasoning-effort axis, gpt-oss-120b high
The contest frontier (Figure 9) has gpt-oss-120b low (46.1% at 3.2k tokens) and medium (56.8% at 6.8k; × 3 + MBR-exec 62.4% at 20.3k)
but no high effort. 3 seeds, 311 problems, max_tokens 30,000 (context 32k), three 120b servers (GPUs 0–2).
- H2d-P1: high-effort single attempts solve 60–66% at 12–18k tokens per problem, with ≤ 10% of attempts hitting the cap.
- H2d-P2: per token, high effort is dominated by medium × 3 + MBR-exec (62.4% at 20.3k) or roughly equal to it; the ≥ 2300 band rises
  above 40% only with high effort.

## H2d results (2026-10-15 14:29 UTC; 3 seeds, 30k cap)
gpt-oss-120b high: 148 / 149 / 150 of 311 (47.9%) at 20.8k tokens per problem — below medium (56.8% at 6.8k). Read: 418 of 933 attempts end
at the 30k cap with the reasoning unfinished and no program (404 without code); the 515 that finish are 86.8% correct (medium: 59.2% of
finished). By band: ≤ 1600 84.0%, 1700–2200 65.2%, ≥ 2300 20.1%. **H2d-P1 refuted** (cap-bound, not 60–66%); **H2d-P2 holds trivially**
(dominated per token). Our 32k context, not the model, limits high effort; the finished attempts suggest a large gain at a much larger cost.

## H2e pre-registration (2026-10-15 14:29 UTC, before running): high effort with a 64k cap (one seed, problems sharded over 3 servers)
- H2e-P1: ≥ 70% solved at 30–45k tokens per problem; ≤ 10% of attempts at the cap. Per token it stays far above medium × 3 + MBR-exec
  (62.4% at 20.3k) in cost.

## H2e results (2026-10-15 16:28 UTC; one seed, 64k cap, 311 problems)
gpt-oss-120b high: 206 / 311 (66.2%) at 29.9k tokens per problem (median 26.4k); 54 attempts (17%) still end at the 64k cap without a
program; finished attempts 80.2% correct. By band: ≤ 1600 87.3%, 1700–2200 75.8%, ≥ 2300 50.3% (medium: 85.0 / 71.4 / 34.5%). Paired with
medium seed 1: 49 gained, 13 lost. **H2e-P1 mostly refuted:** below 70%, 17% at the cap; tokens within the predicted 30–45k.
Cost–accuracy: one high attempt (66.2% at 29.9k) is the most accurate single attempt and the only setting above 40% on problems rated
≥ 2300; medium × 3 + MBR-exec reaches 62.4% at 20.3k (two thirds of the tokens), one medium attempt 56.8% at 6.8k (one quarter of the
tokens). High effort pays where problems are hard, at 4.4× the tokens of medium.

## H2e replication pre-registration (2026-10-15 17:28 UTC, before running): seeds 2 and 3 (the ≥ 3-seed rule for headline numbers)
Same settings (64k cap); each seed sharded over 2 servers (GPUs 0–3).
- H2e-r: the 3-seed mean is within ± 3 points of seed 1 (66.2%) and the ≥ 2300 band stays ≥ 45%.

## H2e replication results (2026-10-15 20:28 UTC)
Seeds 1 / 2 / 3: 206 / 204 / 208 of 311 (mean 66.2%) at 30.1k tokens per problem; 17% of attempts at the 64k cap; bands ≤ 1600 87.8%,
1700–2200 77.3%, ≥ 2300 49.2%. **H2e-r holds** (mean = seed 1; ≥ 2300 band ≥ 45%).
