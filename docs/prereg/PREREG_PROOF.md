# Pre-registration PROOF: from computed answers to proofs (formal proofs first; geometry and optimization proofs next)

Written 2026-10-17 18:12 UTC, before any run. Results go below; this section is not edited afterwards.

**Why (user, 2026-10-17: "extend on proof or other math problems including geometric / optimizations").** The recipe so far
(the right tool, the fact first, a cheap check, thinking only where the check fails) needs an exact check. For proofs written in
Lean 4 the compiler is a perfect check, so the same questions apply: which tool (a general model or a small specialized prover), which
facts (Mathlib lemma names), and where to spend more attempts or thinking. Earlier (X4): general models solve 31–133 of 244 miniF2F
statements with 8 attempts; failed attempts often name lemmas that do not exist (22–40%), and telling them which lemmas exist did not
help (2.7% vs a fresh attempt 3.2%).
**Plan.** Phase 1 (this file): specialized provers that fit one RTX 3090 vs general models, compile-gated sampling. Phase 2: facts
first (Mathlib premises retrieved before writing; prior art ReProver / LeanDojo). Phase 3, geometry proofs: LeanEuclid (Euclid's
Elements in Lean 4) or AlphaGeometry's IMO-AG-30 / JGEX-AG-231 with its symbolic engine as the tool and auxiliary constructions as the
model's job. Phase 4, optimization proofs: competition inequalities (the miniF2F algebra / imo subsets and a dedicated inequality set)
and optimality certificates for the LP word problems (the program prints the plan and dual multipliers; an exact rational checker
verifies feasibility and equal objective = a proof that the plan is optimal for the model's own formulation).
Natural-language proofs are left out until a grader validated against human labels is available.
**Phase 1 design.** miniF2F test (244 statements, Lean 4 v4.15.0 + Mathlib v4.15.0), 8 attempts per statement, our X4 prompt and checker.
New: Goedel-Prover-V2-8B (tag gpv2) and DeepSeek-Prover-V2-7B (dspv2), 16k output cap; Qwen3-14B-AWQ with thinking (q14a_think, 16k);
existing: gpt-oss-20b low (oss20), Qwen3-32B-AWQ (q32b), Qwen3.6 (q36), all without thinking. Analysis: poc/analyze_proof.py
(solved with 1 / 2 / 4 / 8 attempts, tokens of the compile-gated loop, invented-identifier share, solved by problem type).
- PROOF-P1: the 8B specialized provers solve the most: Goedel-Prover-V2-8B ≥ 70% and DeepSeek-Prover-V2-7B ≥ 55% of 244 with 8
  attempts, vs the best general model 54.5% (Qwen3.6, 133).
- PROOF-P2: invented identifiers are rarer for the provers (≤ 10% of failed attempts vs 22–40% for general models): Mathlib names
  are a fact they were trained on.
- PROOF-P3: the provers' advantage over Qwen3.6 is largest on competition statements (amc12 / aime / imo / algebra) and smallest on
  mathd_algebra.
- PROOF-P4 (cost): Qwen3-14B-AWQ with thinking solves more statements than every general model without thinking except Qwen3.6, but
  the provers solve more statements per output token (solved statements per 100k tokens of the compile-gated loop).

## Setup fix (2026-10-17 20:36 UTC, before any proof was checked): the provers get their own prompt and thinking
The first Goedel-Prover-V2-8B run used our X4 prompt with thinking switched off (564 attempts; kept as lean_gpv2ourprompt_test.jsonl).
Both provers' model cards use a different prompt ("Complete the following Lean 4 code … provide a detailed proof plan …") with the chat
template's default (thinking on for the Qwen3-based Goedel) and budgets of 32k (Goedel) / 8k (DeepSeek) tokens. Running them off-spec
would bias PROOF-P1 against them, so: gpv2 and dspv2 use --card_prompt --think with a 32k cap (server max-model-len 40,000); the general
models keep the X4 prompt. Predictions unchanged. poc/queues/queue_s2_proof.sh restarted with these settings.

## Phase-1 addendum (2026-10-18 05:01 UTC, before these runs): general models WITH reasoning
Two more arms, same 244 statements × 8 attempts, X4 prompt: Qwen3.6 with thinking (q36_think; T 1.0 / top_k 20, no presence penalty,
48k cap) and gpt-oss-20b at medium effort (oss20_medium, 32k cap), GPUs 0 / 1 (poc/queues/queue_s2_proof3.sh).
- PROOF-P5: Qwen3.6 thinking solves more than without (133) but fewer than Goedel-Prover-V2-8B (180); gpt-oss-20b medium solves more
  than at low effort (66) but fewer than DeepSeek-Prover-V2-7B (165).
- PROOF-P6 (more attempts on the hard tail, 2026-10-18 05:02 UTC, before running): Goedel-Prover-V2-8B, 24 more attempts (samples 9–32) on the 64
  statements unsolved after 8, GPU3 (queue_s2_proof4.sh): ≥ 10 more statements solved (its card reports 84.6% at 32 attempts), at
  ≥ 3 × the tokens per newly solved statement of the first 8 attempts.

## Phase-1 results, the specialized provers (2026-10-18 05:02 UTC; results/x4/proof_analysis.log via poc/analyze_proof.py; Qwen3-14B thinking still running)
| model (fits a 3090?) | solved with 1 / 2 / 4 / 8 attempts (of 244) | tokens per attempt | compile-gated loop, tokens per statement | failed attempts with invented names |
|---|---|---|---|---|
| **Goedel-Prover-V2-8B (yes)** | 137 / 159 / 169 / **180 (73.8%)** | 7.0k | 37.8k | 6% |
| **DeepSeek-Prover-V2-7B (yes)** | 132 / 145 / 158 / **165 (67.6%)** | 4.5k | 23.9k | 7% |
| Qwen3.6-35B-A3B, no thinking (no) | 94 / 109 / 121 / 133 (54.5%) | 1.9k | 12.5k | 22% |
| gpt-oss-20b low (yes) | 40 / 48 / 59 / 66 | 1.6k | 11.4k | 25% |
| Qwen3-32B-AWQ, no thinking (no) | 10 / 13 / 20 / 31 | 1.4k | 11.0k | 40% |
Solved by type, Goedel vs Qwen3.6: mathd_algebra 65 vs 54 of 70, mathd_numbertheory 52 vs 40 of 60, amc12 27 vs 13 of 45, aime 10 vs 4
of 15, imo 7 vs 4 of 20.
- **PROOF-P1 holds** (73.8% and 67.6% vs 54.5%). **P2 holds** (6–7% vs 22–40%: Mathlib names are a fact the provers know). **P3 mostly
  holds** (largest gains on amc12 +31 and aime +40 points; imo +15, mathd_algebra +16). **P4** pending (Qwen3-14B thinking).
**Reading:** for proofs the "right tool" is a specialized 8B prover that fits a 3090: it proves a third more statements than a general
35B model, almost never invents a lemma name, but spends 2–3 × the tokens per statement (it writes a long proof plan first).
