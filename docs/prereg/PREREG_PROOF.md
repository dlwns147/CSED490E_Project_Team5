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
