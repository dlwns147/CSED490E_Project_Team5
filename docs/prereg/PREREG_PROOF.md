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

## Phase 2 pre-registration (2026-10-18 10:36 UTC, before running): facts first for proofs = a verified proof of a similar statement
For each statement, the most similar OTHER miniF2F statement (BM25 over statement tokens) that Goedel-Prover-V2 proved, with its
Lean-accepted proof, is shown before the task (run_lean.py --exemplar gpv2; leave-one-out: never the statement itself). Qwen3.6 without
thinking (tag q36_ex), 8 attempts, X4 prompt otherwise unchanged, GPU0 (poc/queues/queue_s2_proof6.sh). Prior art: retrieval of similar
proofs / premises (ReProver, LeanDojo; retrieval-augmented provers).
- PROOF-P8: Qwen3.6 proves ≥ 145 of 244 (without the example: 133), and invented names fall from 22% to ≤ 15% of failed attempts.
- Phase 3b result (2026-10-18 11:31 UTC): with a 30k budget gpt-oss-20b's proposals prove **1 of 18** (IMO 2014 P4; 143 valid of 288, 5 proving
  proposals; 16k budget: 0); with the construction definitions also 1 (133 valid, 4 proving). GEO-P3/P4 to be scored from the raw
  rows; the definitions did not reduce rejections (valid 133 vs 143). PROOF-P9 (pre-registered now): gpt-oss-20b low with the same
  verified similar proof (tag oss20_ex, GPU0, queue_s2_proof7.sh) proves ≥ 80 of 244 (without: 66).
- **Phase 2 result (2026-10-18 11:32 UTC): PROOF-P8 refuted.** With a Lean-verified proof of the most similar other statement in the prompt, Qwen3.6
  proves 133 of 244 — exactly as many as without (133) — and fewer at the first attempt (77 vs 94), at 1.25 × the tokens; invented names
  stay at 23% of failed attempts. A worked example of a *similar* proof is not the missing fact: what the provers have is broad knowledge
  of Lean 4 + Mathlib, not one example.
- PROOF-P9 refuted (2026-10-18 12:19 UTC): gpt-oss-20b low with a verified similar proof proves 65 of 244 (without: 66).

## Pre-registration (2026-10-18 12:36 UTC, before computing / running): a cheap model first, and repair from the compiler's errors
- PROOF-C (offline, stored attempts 1–8): cascade "Qwen3.6 without thinking, up to 2 attempts, then Goedel-Prover-V2 up to 8" (stop at
  the first proof that compiles) proves ≥ 178 of 244 (Goedel alone: 180) at ≤ 60% of Goedel's compute (active parameters × output
  tokens: Qwen3.6 3B, Goedel 8B). Same with gpt-oss-20b low (3.6B) as the first stage: ≥ 175 at ≤ 70%.
- PROOF-R (GPU0, queue_s2_proof8.sh): for the statements whose first Goedel attempt failed, one revision shown the failed proof and Lean's
  error lines (Goedel-Prover-V2 is trained for self-correction) solves ≥ 1.5 × as many as the stored fresh second attempt, at ≤ 1.2 × its
  tokens. Prior art: Goedel-Prover-V2 self-correction mode; our N9 / X4-P2 found repair ≈ fresh for general models.
- **PROOF-C refuted (2026-10-18 12:36 UTC; results/x4/proof_cascade.log):** a cheap first stage keeps the provers' accuracy (Qwen3.6 × 1 → Goedel:
  180 / 244; → DeepSeek: 166) but saves nothing (98–105% of the compute, 101–122% of the tokens). The provers' cost is dominated by the
  statements nobody proves (8 failed attempts × 7k tokens each), which a cheap first stage cannot skip; the statements a cheap model can
  prove, the prover also proves at its first attempt. The lever for cost is the attempt budget on hopeless statements (Goedel: 169 with
  4 attempts vs 180 with 8), not routing.
- PROOF-R addendum (2026-10-18 13:35 UTC, before running): the same revision test for DeepSeek-Prover-V2-7B (its failed first attempts; GPU2,
  queue_s2_proof9.sh), same prediction. And a larger geometry benchmark: DD+AR alone on JGEX-AG-231 (CPU, ≤ 6 h) as the baseline for
  later proposer runs.
- Phase 4, first look (offline, 2026-10-18 13:36 UTC): the 50 of 244 miniF2F statements whose conclusion is an inequality or bound (the competition
  form of an optimization proof) are proved as often as the rest by the provers (Goedel 72% vs 74%, DeepSeek 66% vs 68%) but less often
  by general models (Qwen3.6 48% vs 56%, gpt-oss-20b 10% vs 31%, Qwen3-14B thinking 2% vs 10%): bound proofs are where a general model
  most needs the specialized tool.

## Results (2026-10-18 15:36 UTC): repair from compiler errors; Qwen3.6 proposer with 80k
- **PROOF-R refuted for Goedel-Prover-V2-8B:** on the 107 statements whose first attempt failed, one revision shown the failed proof and
  Lean's error lines proves 11 (11.7k tokens each; 26 at the cap, 3 requests over the context), a fresh second attempt proves 22 (12.3k);
  either: 24. Caveat: our revision prompt is single-turn, not the model's own self-correction format (its card's pipeline script).
- **GEO-P5 holds** (Qwen3.6 thinking, 80k: 24 of 288 proposals without a clause = 8%; 184 valid; still 1 of 18 problems, IMO 2014 P4,
  at 35k tokens per proposal). General LLMs write valid auxiliary points but almost never the one that unlocks the proof.
**Pre-registered now:** GEO-J: on JGEX-AG-231 (DD+AR alone 187), gpt-oss-20b medium (30k cap) proposes 8 points for each of the 44
unsolved problems (GPU0, queue_s2_geoproof5.sh); prediction ≥ 5 more proved (these are easier than IMO problems).
DeepSeek-Prover revision run relaunched (its first launch crashed on over-long prompts before the fix).
- PROOF-R for DeepSeek-Prover-V2 (2026-10-18 16:36 UTC): revision 5 of 112 (4.2k tokens) vs fresh second attempt 13 (7.1k): **refuted for both provers**
  — per token too (Goedel 0.9 vs 1.8, DeepSeek 1.2 vs 1.8 proofs per 1k tokens). With our prompt, a fresh sample beats a repair.
**Phase 4b pre-registration (2026-10-18 16:36 UTC, before running): a fact sheet for bound proofs (the OR-Tools-snippet analogue).** The 50 inequality /
bound statements (results/x4/ineq50.txt); a hand-written 10-line "inequality toolkit" (results/x4/ineq_toolkit.txt: nlinarith with
squares, positivity, clearing denominators, sqrt / abs lemma names, omega / interval_cases) before the task; Qwen3.6 without thinking,
8 attempts (tag q36_ineqhint; LEAN_HINT + LEAN_ONLY), GPU2 (queue_s2_proof10.sh). Baseline: the stored Qwen3.6 attempts on the same 50
(24 proved).
- PROOF-P10: ≥ 29 of 50 proved (+5), and invented names fall below 15% of failed attempts (the sheet names real lemmas and tactics).
- **Phase 4b result (2026-10-18 17:36 UTC): PROOF-P10 refuted.** With the 10-line inequality toolkit Qwen3.6 proves 21 of the 50 bound statements
  (without: 24) at 1.26 × the tokens; invented names 22% (24%). Like the worked example (phase 2), a prompt-level fact does not help Lean.
- **GEO-J holds (2026-10-18 17:36 UTC):** on the 44 JGEX-AG-231 problems DD+AR cannot do alone, gpt-oss-20b's proposals (8 per problem, 30k cap) make
  13 provable (193 of 352 valid, 38 proving): DD+AR + LLM points 200 / 231 vs 187 alone. On easier problems an LLM's auxiliary point
  often suffices; on IMO problems (1 of 18) it rarely does.
- PROOF-P6 (2026-10-18 18:36 UTC): 24 more Goedel attempts on its 64 unsolved statements prove 7 more (180 → 183 at 16, 187 at 32 attempts) for 24.1M
  tokens — 3.4M tokens per extra proof vs 51k per proof in the first 8 attempts (67 ×). P6's "≥ 10 more" narrowly refuted; the cost part holds.
- PROOF-P7 refuted (2026-10-18 20:36 UTC): 24 more DeepSeek-Prover-V2 attempts on its 79 unsolved statements prove 4 more (165 → 167 at 16, 169 at 32) for 14.4M tokens (3.6M per extra proof); both provers' extra attempts cost ≈ 3.5M tokens per additional proof.

## Addendum PF (2026-10-23 21:1x UTC, before computing; offline on the stored phase-1 attempts): the recipe where the check is perfect
**Why (new direction 1, user 10-23).** On word problems and geometry the recipe's limit is the check's leak. In Lean the compiler is a
sound check (a compiled proof is right), so "cheap attempt → check → think only on failure" cannot lose accuracy to a leak; the question is
only how to spend tokens. Stored: miniF2F test (244), 8 attempts per statement for gpt-oss-20b at low effort (cheap) and medium effort
(thinking), and for Qwen3.6-35B-A3B without and with thinking.
**Policies** (attempts taken in a random order, stop at the first that compiles; 200 random orders; tokens = all attempts made):
CHEAP×k (k ≤ 8), THINK×j (j ≤ 8), FF(a, j) = up to a cheap attempts, then up to j thinking attempts.
- **PF-P1:** at the token budget of THINK×8, the best FF(a, j) solves ≥ THINK×8 + 5 statements, for both models.
- **PF-P2:** FF(8, 8) solves more statements than either mode alone (≥ max(CHEAP×8, THINK×8) + 3): the two modes solve different
  statements, so with a sound check they compose.
- **PF-P3:** FF(1, 8) costs ≤ 60% of THINK×8's tokens for gpt-oss-20b (whose thinking is ~9× its cheap attempt).
**Reading.** P1–P3 → with a perfect check the recipe is a pure saving and the remaining question is the fact (premise / lemma names) and
the budget split; that is the plan for the Lean phase on the cluster (`poc/slurm/lean_setup.sh`).

### Results PF (2026-10-23 21:1x UTC; `python poc/analyze_pf.py`, 200 random attempt orders; solved statements of 244, tokens per statement)
| | CHEAP×8 | THINK×8 | FF(1, 8) | FF(8, 8) | best FF within THINK×8's budget |
|---|---|---|---|---|---|
| gpt-oss-20b (low / medium effort) | 66.0 @ 11.5k | 72.0 @ 108.9k | 72.7 @ 109.6k (101%) | **77.0** @ 117.0k | FF(8, 7) 76.2 (+4.2) @ 104.0k |
| Qwen3.6-35B-A3B (no thinking / thinking) | 133.0 @ 12.5k | 129.0 @ 50.4k | 131.9 @ 49.0k (97%) | **140.0** @ 55.8k | FF(8, 6) 138.9 (+9.9) @ 45.1k |
Best policy per budget (tokens per statement): ≤ 2k CHEAP×1, ≤ 4k CHEAP×2, ≤ 8k CHEAP×4–5, ≤ 16k CHEAP×8 (both models); only above
that does thinking enter, as FF(8, j).
- **PF-P1 half holds** (Qwen3.6 +9.9; gpt-oss-20b +4.2 < +5). **PF-P2 holds** (FF(8, 8) 77.0 vs 72.0; 140.0 vs 133.0: the modes solve
  different statements). **PF-P3 refuted** (FF(1, 8) costs 101% / 97% of THINK×8): one cheap attempt solves few statements, and every
  unsolved statement still burns 8 thinking attempts.
- **Reading.** With a sound check the right escalation is not "one cheap try, then think" but "cheap attempts until they stop paying,
  then think": at every budget up to 16k tokens per statement more cheap attempts beat thinking, and thinking adds statements only after
  the cheap attempts are exhausted (+4 / +7 at the same tokens as always thinking). The open question for the Lean phase is the fact
  (lemma names) and when to stop sampling cheap attempts.

## Addendum PL1 (2026-10-23 22:5x UTC, before any run): how far does cheap sampling pay before thinking, with a perfect check?
PF found the best policy up to 16k tokens per statement is always more cheap attempts, with only 8 available. **Run** (miniF2F test, 244,
X4 prompt, `run_lean.py gen`, checked with the batched checker once it agrees with the stored per-attempt results): gpt-oss-20b at low
effort extended from 8 to 32 attempts (samples 9–32; medium effort keeps its 8); gpt-oss-120b on 4 × RTX 3090, 32 attempts at low effort
and 8 at medium effort (32k cap, as gpt-oss-20b's). Policies and frontier as in PF.
- **PL1-P1:** cheap sampling keeps paying: CHEAP×32 − CHEAP×8 ≥ +8 statements for both models.
- **PL1-P2:** at THINK×8's token budget, the best policy is cheap-only or FF(k, j ≤ 2): thinking adds ≤ 3 statements over the best
  cheap-only policy at that budget.
- **PL1-P3:** FF(32, 8) solves ≥ CHEAP×32 + 3: thinking still finds statements that 32 cheap attempts miss.
**Decision.** P1 + P2 → with a sound check the escalation rule is "sample cheaply up to the budget, think only after"; P3 says what
thinking is for (statements cheap sampling never reaches).
*PL1 settings (fixed before any attempt was generated): cheap = low effort with a 16,000-token cap (as the stored gpt-oss-20b X4 rows),
thinking = medium effort with a 32,000-token cap; a first submission with an 8,192 cap was cancelled before generating anything.*
*Batched checker validated (2026-10-23 23:5x UTC, job 1237592; `run_lean.py bvalidate`): 800 / 800 random stored attempts (400 Qwen3.6, 400
gpt-oss-20b; 222 of them proofs) get the same verdict as the original one-file-per-attempt check. PL1 attempts are checked with
`run_lean.py bcheck` (16 attempts per Lean process).*

### Results PL1 (2026-10-24 04:0x UTC; `python poc/analyze_pf.py oss20:oss20_medium oss120:oss120_medium`, 100 random orders; statements of 244)
| | CHEAP×8 | CHEAP×32 | THINK×8 | FF(32, 8) | best within THINK×8's budget (best cheap-only there) |
|---|---|---|---|---|---|
| gpt-oss-20b (low / medium) | 62.0 @ 11.5k | **74.0** @ 43.7k | 72.0 @ 109.0k | **80.0** @ 147.7k | FF(31, 5) 77.7 (74.0) @ 107.8k |
| gpt-oss-120b (low / medium, 4 × RTX 3090) | 69.6 @ 11.5k | **83.0** @ 43.2k | 81.0 @ 34.7k | **91.0** @ 75.7k | FF(19, 2) 83.1 (81.1) @ 34.6k |
Frontier: gpt-oss-20b is cheap-only at every budget up to 32k tokens per statement (CHEAP×1 … ×23); gpt-oss-120b, whose thinking is
cheap (4.3k per attempt vs 14.5k), mixes in 1–2 thinking attempts from 8k on (FF(2, 1), FF(8, 1), FF(17, 2)).
- **PL1-P1 holds** (+12.0 / +13.4 statements from 8 to 32 cheap attempts). **PL1-P2 half holds** (thinking adds +3.7 over cheap-only at
  THINK×8's budget for gpt-oss-20b, +2.0 for gpt-oss-120b). **PL1-P3 holds** (+6 / +8 statements beyond 32 cheap attempts).
- **Reading.** With a perfect check the budget goes mostly to cheap attempts; thinking is worth a few attempts when it is cheap relative to
  a cheap attempt, and its distinct value is the statements cheap sampling never reaches (+6 to +8). The escalation rule for proofs: sample
  cheaply until attempts stop adding statements, then think — the word-problem recipe with "one cheap try" replaced by "many".

## Addendum PL2 (2026-10-24 04:0x UTC, before computing; offline on the PL1 attempts): can 30 labelled statements pick the budget split?
Policies FF(a, j) (a ≤ 32 cheap, j ≤ 8 thinking, attempts in a random order, stop at the first that compiles); utility per statement =
100 × solved − λ × ktokens, λ = 0.5 (as the word-problem pilot). Pilot: label 30 random statements, pick the FF(a, j) with the best pilot
utility; regret = best full-set utility − the pick's full-set utility; 300 pilots per model.
- **PL2-P1:** the 30-label pilot's mean regret is ≤ 2 points for both models (vs the best single (a, j) per model).
- **PL2-P2:** the pilot's pick uses ≥ 8 cheap attempts in ≥ 80% of pilots for both models (cheap sampling first is the robust choice).

### Results PL2 (2026-10-24 04:1x UTC; `python poc/analyze_pl2.py oss20:oss20_medium oss120:oss120_medium`, λ = 0.5)
| | best fixed split (utility) | CHEAP×32 | THINK×8 | 30-label pilot regret (90th pct) | pilot picks with ≥ 8 cheap |
|---|---|---|---|---|---|
| gpt-oss-20b | FF(6, 0) 19.9 | 8.5 | −25.0 | **0.55** (1.25) | 29% |
| gpt-oss-120b | FF(4, 1) 23.0 | 12.4 | 15.9 | **0.90** (2.05) | 21% |
- **PL2-P1 holds** (regret ≤ 2). **PL2-P2 refuted:** with tokens priced at λ = 0.5 the best split is a few cheap attempts (4–6) and at
  most one thinking attempt, not ≥ 8 cheap ones; the token penalty, not the check, now decides how far to sample. The 30-label pilot finds
  it within a point — the same deployable rule as on word problems.

## Addendum PL3 (2026-10-24 06:1x UTC, before any run): a Qwen model on the proof frontier
PL1 used gpt-oss models only. **Run:** Qwen3-8B on miniF2F test (244), X4 prompt, 32 attempts without thinking (8,192 cap, as Qwen3.6's
phase-1 cheap arm) and 8 with thinking (16,000 cap, as Qwen3-14B-AWQ's), RTX 3090 (thinking split over 4 jobs by statement), batch-checked
on a CPU node. Same frontier analysis (`analyze_pf.py q8b:q8b_think`).
- **PL3-P1:** CHEAP×32 solves ≥ THINK×8 statements.
- **PL3-P2:** FF(32, 8) ≥ CHEAP×32 + 3.
- **PL3-P3:** up to 16k tokens per statement the best policy is cheap-only (as for gpt-oss-20b).
