# Pre-registration RW: prior methods re-run on our models and data, next to the published numbers

Written 2026-11-13 17:5x UTC. Part A is computed from stored runs (seeds 7–9) and decides nothing; part B is registered before any run.

**Why.** The course method has been compared with prior methods arm by arm (Amonkar et al.'s formalizer setting, Mixture-of-Thought,
budget-forced thinking, Schrader et al.'s per-clue search), but not with the two families a reader will ask about first: translate-and-solve
pipelines that refine on solver errors (Logic-LM, Pan et al. 2023; SatLM; LINC's majority vote) on grids, and LLM-Modulo (Gundawar et al.
2411.14484, critics plus re-prompting) on trips. Published numbers use other models and subsets (GridPuzzle paper: GPT-4 5.1% of 274;
NaturalPlan trips: Gemini 1.5 Pro 34.8%, LLM-Modulo GPT-4o 40.0%, Claude-3.5-Sonnet 47.0%; LLMPC GPT-4o 44.6%), so they are cited, not compared.

## Part A (stored runs, Qwen3-8B, seeds 7–9, exploratory)

Logic-LM as published: translate, refine only on execution errors (up to 3 rounds), answer the solver's first solution, and on no solution fall
back to chain of thought (here: thinking). LINC-style: majority over three quick translations (seeds 7–9 as the samples).

| Arm | GridPuzzle | Mitra-Baral |
|---|---|---|
| Thinking only | 62.5% at 11.6k | 87.6% at 6.2k |
| Logic-LM, quick translation | 54.3% at 5.0k | 80.1% at 2.3k |
| Logic-LM, thinking translation | 61.9% at 13.2k | 87.6% at 8.5k |
| LINC-style majority of 3 quick translations | 51.2% at 4.6k | 79.8% at 2.6k |
| **Ours (same seeds, development)** | **92.9% at 4.6k** | **95.7% at 1.0k** |
| **Ours (fresh seeds 14–16, PREREG_GPF)** | **93.3% at 4.6k** | **96.5% at 1.2k** |

Reading: answering the solver's first solution without counting is below thinking on both sets; the count (exactly one) and the ladder are
what make translation pay.

## Part B (registered): LLM-Modulo on trips, same models, same 100 trips, seeds 4–6

**Arm `modulo`** (`poc/run_plan.py q32|oss20 modulo <seed>`): thinking writes a plan; critics built from each task's structured constraints
(Amonkar et al.'s file, parsed from the task text; they pass all 100 gold plans) list every broken requirement in words (cities, start and end
day, shared flight day, stay lengths, direct flights, dated events); the list goes back and the model replans, up to 10 rounds (their setting).
This is a stronger check than ours: hand-written for the domain from the task's structure, where our check is the generic solution count.
Qwen3-32B-AWQ (one GPU of the second server) and gpt-oss-20b (reasoning effort high, Slurm 2 × RTX 3090), seeds 4, 5, 6.

**Prediction.** LLM-Modulo raises thinking a lot (published: GPT-4o 3.4% → 40.0%), at several thinking rounds' tokens. Qwen3-32B: about 70% at
about 25k tokens against our 72.0% at 18.2k, so ours − LLM-Modulo about +4 utility, interval including 0. gpt-oss-20b: about 85% at 25k against
our 82.3% at 26.6k, about +2 for LLM-Modulo.
- **RW-P1 (reported, paired over trips):** ours − LLM-Modulo, utility and accuracy, per model.
- **Decision.** Ours ≥ LLM-Modulo (interval above or including 0): the report states that a domain-free, label-free check matches a
  hand-written domain verifier on trips. LLM-Modulo ahead (interval below 0): the report states that a hand-written verifier beats the generic
  count on trips, and that our check's advantage is that it needs no domain code; the grids, where no such verifier exists in prior work, carry
  the claim.
