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
*(2026-11-13 19:5x UTC, before any gpt-oss-20b row: the Slurm job had not started after 2 h, so gpt-oss-20b runs on the second server's other GPU
instead; same model, effort, prompts and seeds.)*

**Prediction.** LLM-Modulo raises thinking a lot (published: GPT-4o 3.4% → 40.0%), at several thinking rounds' tokens. Qwen3-32B: about 70% at
about 25k tokens against our 72.0% at 18.2k, so ours − LLM-Modulo about +4 utility, interval including 0. gpt-oss-20b: about 85% at 25k against
our 82.3% at 26.6k, about +2 for LLM-Modulo.
- **RW-P1 (reported, paired over trips):** ours − LLM-Modulo, utility and accuracy, per model.
- **Decision.** Ours ≥ LLM-Modulo (interval above or including 0): the report states that a domain-free, label-free check matches a
  hand-written domain verifier on trips. LLM-Modulo ahead (interval below 0): the report states that a hand-written verifier beats the generic
  count on trips, and that our check's advantage is that it needs no domain code; the grids, where no such verifier exists in prior work, carry
  the claim.

## Part B result, gpt-oss-20b (written 2026-11-13 22:0x UTC; `python3 poc/gp_conj.py rwtrip --main oss20`, all 300 rows)

| Arm (gpt-oss-20b, seeds 4–6) | Accuracy | Tokens |
|---|---|---|
| Thinking only | 74.0% (73.0% before the 23:1x answer-reading fix) | 14.2k |
| Ours (`trc` → gpt-oss-120b `trc` → `trct` → `think`) | 82.3% | 26.6k |
| LLM-Modulo (hand-written critics, up to 10 rounds) | **96.0%** | 29.3k |

**RW-P1 (gpt-oss-20b): ours − LLM-Modulo −12.3 [−18.1, −6.6] utility, −13.7 [−18.3, −9.3] accuracy.** LLM-Modulo is ahead; I predicted about
+2 for it. Its critics passed 294 of 300 plans and 288 of those were right; 1.64 rounds on average, 7 runs used all 10. The mechanism: a plan
that passes critics written from every requirement is the trip's one plan, so LLM-Modulo turns thinking into a verified search, while our
count check verifies the model's own reading. Qwen3-32B's rows are still running; the decision waits for both models.

**Rerun of LLM-Modulo on Qwen3-32B with the fixed answer reader (written 2026-11-14 00:3x UTC, before any rerun row).** The Qwen3-32B
`modulo` lane started at 17:52, before the 23:1x reader fix, so a re-plan that ends with the plan's objects and no brackets was read as no
plan and sent back as "no plan was given". In the 280 rows written by 00:20, 145 rounds stopped normally with no plan read, in 102 rows,
and 51 of those 102 never passed the critics (of 84 that never passed). The partial read at 00:2x (ours 76.8% vs LLM-Modulo 70.0%, +16.3
[+7.2, +25.8] utility) therefore under-reads LLM-Modulo. The rows store no answer text, so they cannot be re-read: all 300 trip-seeds rerun
with the fixed reader as tag `q32fx` (same prompts, critics, seeds, 10 rounds, 32,000 tokens; second server, GPU 7), and **RW-P1 for
Qwen3-32B is decided on the rerun** (`python3 poc/gp_conj.py rwtrip --main q32 --modulo-tag q32fx`). The old rows are reported only as the
under-read version. gpt-oss-20b is not rerun: 28 of its 491 rounds stopped with no plan read, and it already passed 294 of 300.
