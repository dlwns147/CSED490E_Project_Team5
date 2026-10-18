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

## Phase 3a pre-registration (2026-10-18 06:38 UTC, before running): geometry proofs — the LLM proposes the auxiliary point, a symbolic engine proves
IMO-AG-30 (AlphaGeometry's 30 IMO geometry problems in its construction language). AlphaGeometry's engine DD+AR alone, no language model,
proves 12 (paper: 14). For each of the other 18, gpt-oss-20b (medium effort; fits a 3090) proposes ONE auxiliary point (16 samples per
problem, the 48 one-point constructions listed in the prompt); each proposal is inserted before the goal and DD+AR runs for ≤ 600 s
(poc/geoproof_gen.py, /SSD/lean_postech/ag/ddar_aux.py, poc/queues/queue_s2_geoproof.sh). The check is exact (the engine's proof).
Prior art: AlphaGeometry (Trinh et al., Nature 2024; a trained 150M model proposing constructions reaches 25 / 30; their GPT-4 baseline
adds little), AlphaGeometry2, TongGeometry.
- GEO-P1: with one proposed point, 13–18 of 30 are proved (1–6 more than DD+AR alone): general LLMs are weak at auxiliary constructions.
- GEO-P2: ≥ 30% of proposals are invalid (unknown or misused construction, reused name, impossible configuration): the construction
  language is a missing fact.

## Phase-1 result, Qwen3-14B-AWQ with thinking (2026-10-18 06:39 UTC) and an extractor fix
Raw check first: 606 of its 1,952 attempts had "no proof"; 320 of them wrote ':=' and 'by' on separate lines, which the extractor
missed (fixed: ':=\s*by'; all finished files re-checked: +11 proved attempts for Qwen3-14B, +0 for the other models). The rest are
real: 234 runs hit the 16k cap and 129 answers use Lean 3 syntax (begin … end), which Lean 4 rejects.
Qwen3-14B-AWQ thinking: 8 / 14 / 17 / **21** of 244 with 1 / 2 / 4 / 8 attempts at 9.1k tokens per attempt (71k per statement in the
compile-gated loop); invented names in 27% of failed attempts.
- **PROOF-P4 refuted:** Qwen3-14B with thinking solves fewer statements (21) than gpt-oss-20b (66) and Qwen3.6 (133) without thinking,
  at 6 × their tokens; per 100k tokens of the compile-gated loop: Goedel 1.9, DeepSeek 2.8, Qwen3.6 4.4, gpt-oss-20b 2.4, Qwen3-14B think 0.12.
**Reading:** for formal proofs, thinking does not substitute for knowing Lean 4 and Mathlib: a general 14B model that thinks for 9k
tokens mostly writes invalid Lean; the 8B prover trained on Lean proves 9 × more statements.
- Phase 3a addendum (2026-10-18 07:36 UTC, before any proposal was checked): 122 of gpt-oss-20b's 288 proposals stopped at the 16k cap without a
  clause (counted as invalid). Second proposer: Qwen3.6 with thinking (T 1.0 / top_k 20, no presence penalty, 30k cap; tag q36_think),
  same 18 problems × 16 samples, GPU2 (poc/queues/queue_s2_geoproof2.sh). GEO-P1 / P2 apply to it too.

## Phase 3a result, gpt-oss-20b (2026-10-18 08:36 UTC; results/geoproof/aux_oss20_medium.jsonl) and phase 3b pre-registration
288 proposals for the 18 problems DD+AR cannot prove alone: 122 stopped at the 16k cap without a clause, 62 were rejected by the engine
(33 'cannot unpack Point', 10 argument mismatch, 10 unknown point names, …), 104 valid; of the valid ones 62 finished without a proof
and 42 hit the 600 s limit. **Problems proved: 0 of 18.** **GEO-P1 refuted** (predicted 1–6 more); **GEO-P2 holds** (64% invalid).
Qwen3.6 with thinking: 129 / 244 Lean statements (no thinking: 133) at 4 × the tokens: **PROOF-P5 refuted for Qwen3.6** (thinking does
not help it on Lean either).
**Phase 3b (before running): give the construction language as a fact, and enough budget.** gpt-oss-20b medium, 30k cap (server
max-model-len 36,000), same 18 problems × 16 samples, two arms on GPU0 (poc/queues/queue_s2_geoproof3.sh): plain prompt (tag
oss20_medium30k) and + the definitions of all 48 constructions — what each requires and what it gives, from the engine's defs.txt
(tag oss20_defs30k, flag --defs).
- GEO-P3: the larger budget cuts proposals without a clause from 42% to ≤ 20%.
- GEO-P4: the definitions halve the engine's rejections among written clauses (argument mismatch, unknown points), but proved problems
  stay ≤ 3 of 18: knowing the language is not knowing which point unlocks the proof.

## Results (2026-10-18 09:36 UTC): gpt-oss-20b medium on Lean; Qwen3.6 thinking as the geometry proposer
- gpt-oss-20b medium: 47 / 55 / 67 / 72 of 244 (low: 66) at 14.5k tokens per attempt (9 × low; 320 runs at the 32k cap). **PROOF-P5 holds
  for gpt-oss-20b** (more than low, far fewer than the provers) — reasoning effort buys 6 statements for 9 × the tokens.
- Qwen3.6 thinking (30k cap) as the geometry proposer: **1 of 18** problems proved (IMO 2014 P4 with `d = midpoint d b c`, 55 s), 86 valid
  of 288 proposals; 151 proposals stopped at the 30k cap without a clause (Qwen3.6 thinks 20.6k tokens on average here).
**Pre-registered now (before running):**
- GEO-P5: Qwen3.6 thinking proposer with an 80k cap (tag q36_think80k, same 18 × 16; server max-model-len 90,000; GPU2;
  queue_s2_geoproof4.sh): ≤ 10% of proposals without a clause, and 1–4 problems proved.
- PROOF-P7: DeepSeek-Prover-V2-7B, attempts 9–32 on its 79 statements unsolved after 8 (GPU1, queue_s2_proof5.sh): ≥ 10 more proved
  (card: 75.6% at 32 attempts ≈ 184).
