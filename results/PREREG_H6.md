# Pre-registration H6: do the hard-benchmark findings hold for a newer model family? (Qwen3.8-27B-FP8, local)

Written 2026-10-14 17:46 UTC, before any run. Results are appended below without editing this section.

**Why.** No closed API model is available (E5). The newest open model on this server is Qwen3.8-27B (FP8, dense, hybrid thinking).
All hard-benchmark conclusions so far rest on Qwen3 (2025) and gpt-oss; a newer family tests whether they are about model generation.
**Conditions** (same harnesses and seeds): contest geometry 311 problems — no-think × 3 seeds, + 8 related helpers × 3 seeds (H4), full
thinking (16k cap) × 1 seed; Solomon 56 — plain (12-line example), documentation snippet, integer reader + robust snippet, × 2 seeds,
no-think.
**Predictions.**
- H6-P1: no-think contest ≥ 25% (Qwen3-32B 12.1%); full thinking ≥ 45% at ≤ 12k tokens.
- H6-P2: the example check over 3 no-think samples adds ≥ 6 points (as for every earlier model).
- H6-P3: 8 related helpers change no-think accuracy by ≤ ± 3 points (H4: only the low-effort 20b model was hurt).
- H6-P4: Solomon plain ≤ 30% feasible, documentation snippet ≤ 50%, integer reader + robust ≥ 80% (facts still needed and still compose).

## Interim results (2026-10-14 19:10 UTC)
- Solomon (feasible of 56, s1 / s2; no-think): plain 9 / 1 (8.9%), documentation snippet 29 / 23 (46.4%), integer reader + robust snippet
  47 / 44 (81.3%). **H6-P4 holds** on all three thresholds: the facts are still needed and still compose for the newest model, and unlike
  Qwen3-32B (≤ 5% with every arm) it copies the given API calls.
- Contest, no-think seed 1: 108 / 311 (34.7%; Qwen3-32B no-think 12.1%), ≈ 3k output tokens per problem. Seeds 2–3, helpers and
  thinking still running.

## Results (2026-10-14 20:29 UTC)
Contest (311 problems): no-think 33.0% single (108 / 102 / 98) at 4.2k output tokens; × 3 + example check 44.7% at 12.6k (oracle 46.3%);
+ 8 related helpers 33.0% (82 lost / 81 gained, tokens 4.7k); one repair round (N2) on seed 1: 34.7 → 42.8% at +2.85k; full thinking
(16k cap) 26.0%: 226 of 311 attempts run out of the cap with the reasoning unclosed (no answer), and the 85 that finish are 95% correct
(81 / 85), mean 13.5k tokens.
- **H6-P1 half:** no-think 33.0% ≥ 25% (Qwen3-32B 12.1%); full thinking refuted (26.0%, cap-bound: the model's default reasoning is
  longer than 16k tokens on most problems, and very accurate when it ends). **H6-P2 holds** (+11.7 points). **H6-P3 holds** (−0.0).
  **H6-P4 holds** (Solomon, above).
- Reading: the newest model is ≈ 3× stronger without thinking, writes ≈ 6× more tokens without thinking, and the cheap fixes behave as
  for the older models (example check over samples, one repair round; helpers do nothing at this strength).

## H6b pre-registration (2026-10-14 20:35 UTC, before running): Qwen3.8 thinking at lower effort (template reasoning_effort low / medium)
A probe (1620_B) shows the template control works: 2.9k (low), 4.6k (medium), 5.4k (default xhigh) thinking tokens. Contest set,
1 seed each, 16k cap, poc/llm.py POC_TEMPLATE_EFFORT.
- H6b-P1: effort low ≥ 45% at ≤ 8k tokens per problem (most attempts finish); effort medium ≥ 50%.
- H6b-P2: both beat no-think × 3 + example check (44.7% at 12.6k) per token.

## H6b results (2026-10-14 22:50 UTC; seed 1, 16k cap for thinking, 6k for no-think)
| Qwen3.8-27B | solved | output tokens / problem | attempts hitting the cap | solved among finished |
|---|---|---|---|---|
| no-think (6k cap) | 34.7% | 4.2k | 158 / 311 | 101 / 153 (66%) |
| thinking, effort low | **44.4%** | 10.8k | 150 / 311 | 138 / 161 (86%) |
| thinking, effort medium | 37.3% | 12.1k | 182 / 311 | 116 / 129 (90%) |
| thinking, default (xhigh) | 26.0% | 13.5k | 226 / 311 | 81 / 85 (95%) |
- **H6b-P1 half:** effort low 44.4% (≥ 45% narrowly missed) at 10.8k tokens (> 8k); effort medium 37.3% (≥ 50% refuted).
  **H6b-P2 refuted:** no-think × 3 + example check (44.7% at 12.6k) matches effort low per token.
- **Harness caveat, found here:** Qwen3.8 is so verbose that our caps bind everywhere: even without thinking, 158 of 311 answers hit
  the 6k cap (an explanation first, the code later), and with thinking, more effort means more unfinished attempts. Every Qwen3.8 number
  above is cap-limited; the finished attempts are 66–95% correct. Relative findings (example check, helpers, facts) are unaffected.

## H6c pre-registration (2026-10-14 22:50 UTC, before running): Qwen3.8 with a 28k cap (seed 1; GPUs 0 and 2 are free)
no-think and thinking-low with max_tokens 28,000 (context 32k).
- H6c-P1: no-think ≥ 50% (finished share ≥ 90%); thinking-low ≥ 60%; both at ≥ 1.5× the capped tokens.

## H6c results (2026-10-15 02:29 UTC; 28k cap, seed 1)
no-think 150 / 311 (48.2%) at 6.4k tokens, no attempt at the cap (6k cap: 34.7%); thinking-low 157 / 311 (50.5%) at 15.9k tokens, 113
attempts still at the cap, finished ones 79% correct. **H6c-P1:** no-think ≥ 50% narrowly refuted (48.2%), thinking-low ≥ 60% refuted
(50.5%); tokens ≥ 1.5× the capped runs (holds). Without the cap, Qwen3.8 no-think matches gpt-oss-120b medium (56.8% at 6.8k) only
partly: 48% at about the same tokens.

## H6d pre-registration (2026-10-15 06:49 UTC, before running): is Qwen3.8's no-think verbosity its reasoning?
Qwen3.8 no-think writes long explanations before the code (6.4k tokens per problem uncapped, 48.2%). D1 showed that a no-think student's
comments carry its reasoning. Arm: the same prompt plus "Reply with the program only: no explanation before or after the code block."
(28k cap, seed 1), vs the 28k-cap run. Prior art: concise-reasoning prompting (e.g. constrained / concise CoT) trades tokens for accuracy.
- H6d-P1: code-only cuts output tokens by ≥ 70% and lowers accuracy by ≥ 10 points (the explanation is the model's reasoning).

## H6d results (2026-10-15 07:48 UTC)
Code-only instruction: 143 / 311 (46.0%) vs 150 / 311 (48.2%) without it; output tokens mean 5,473 vs 6,361 (−14%). The model does not
comply: the median answer still has 4.0k characters of prose outside the code block (3.1k without the instruction) and the programs'
comment lines rise from 16 to 88 (median). **H6d-P1 refuted** (−14% tokens, −2.2 points). Read (279_A): the reply is step-by-step
reasoning in plain text ("But wait: (0,0) is the start …") followed by the code. Qwen3.8's "no-think" mode reasons in its visible answer,
and a prompt cannot switch that off; it moves into comments instead. Its no-think token cost is therefore reasoning cost.
