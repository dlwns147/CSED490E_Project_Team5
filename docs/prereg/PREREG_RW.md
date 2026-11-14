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
with the fixed reader as tag `q32fx` (same prompts, critics, seeds, 10 rounds, 32,000 tokens; second server, GPU 7 for seeds 4–5 and GPU 6 for seed 6 after the old lane was stopped at 282 rows), and **RW-P1 for
Qwen3-32B is decided on the rerun** (`python3 poc/gp_conj.py rwtrip --main q32 --modulo-tag q32fx`). The old rows are reported only as the
under-read version. gpt-oss-20b is not rerun: 28 of its 491 rounds stopped with no plan read, and it already passed 294 of 300.

**Second reader bug, before the rerun's verdict (written 2026-11-14 06:0x UTC).** The `q32fx` rerun ended at 05:xx (all 300): ours 73.0% vs
LLM-Modulo 62.7%, +20.7 [+12.3, +29.5] utility. Its stored round texts show a second form the reader missed: the plan wrapped in a dict,
`{"plan": [...]}`, in 215 rounds (152 of them first rounds); every such round went back as "no plan was given". Fixed in `np_extract` (a
plan-shaped list inside a dict is read). A replay of the stored rounds with the fix (`results/tmp_modreplay.py`: stop at the first re-read round
the critics pass; approximate, since later rounds followed a "no plan" message) gives LLM-Modulo 66.7% at 34.5k and ours − LLM-Modulo +14.5
[+6.2, +22.9] utility, +6.3 [+0.0, +13.0] accuracy. **RW-P1 for Qwen3-32B is decided on a second rerun with both fixes** (tag `q32fx2`, second
server GPUs 6–7, started 05:59); the replay is reported as the estimate until then. The thinking and direct arms have no dict-wrapped answers
(1 of all stored rows).

## Part B result, Qwen3-32B (written 2026-11-14 11:0x UTC; `python3 poc/gp_conj.py rwtrip --main q32 --modulo-tag q32fx2`, all 300 rows, both reader fixes)

| Arm (Qwen3-32B, seeds 4–6) | Accuracy | Tokens |
|---|---|---|
| Thinking only | 55.0% | 7.2k |
| Ours (`trc` → gpt-oss-120b `trc` → `trct` → `think`) | **73.0%** | 18.2k |
| LLM-Modulo (hand-written critics, up to 10 rounds) | 66.7% | 34.7k |

**RW-P1 (Qwen3-32B): ours − LLM-Modulo +14.5 [+6.7, +22.7] utility, +6.3 [+0.3, +12.3] accuracy** (predicted about +4 utility, interval
including 0). The critics passed 200 of 300 plans (all 200 right), 4.47 rounds on average; 3 of 1,550 rounds had no plan read, each an answer
saying no plan exists. The replay estimate (+14.5 [+6.2, +22.9]) matched.
**Decision, both models.** Qwen3-32B: ours ahead; gpt-oss-20b: LLM-Modulo ahead (−12.3 [−18.1, −6.6]). The report states both: a
hand-written domain verifier wins when the model can act on its critiques (gpt-oss-20b passes the critics on 294 of 300 in 1.6 rounds), and
our domain-free ladder wins when it cannot (Qwen3-32B passes on 200 of 300 in 4.5 rounds, at twice our tokens). Our check needs no domain code
either way; the grids, where prior work has no such verifier, carry the general claim.

## Part C: fresh-seed replication on trips, Qwen3-32B (written 2026-11-14 12:0x UTC, before any seed-17–19 row)

**Why.** Both trip verdicts for Qwen3-32B moved under the 11-13 / 11-14 answer-reader fixes (ladder − thinking +19.5 → +12.5; ours −
LLM-Modulo partial +16.3 → +14.5), and seeds 4–6 were read many times while the bugs were found. The report's trip numbers should come from
seeds no analysis has touched, with the final code. **Run:** seeds 17, 18, 19, Qwen3-32B `trc`, `trct`, `think`, `modulo`, gpt-oss-120b
`trc` (low effort), the same prompts and settings as seeds 4–6; second server GPUs 6–7. **Predictions (from seeds 4–6):** ladder − thinking
about +12 utility, interval above 0; ours − LLM-Modulo about +14, interval above 0. **Rule:** the report quotes seeds 17–19 as the trip
result for Qwen3-32B and seeds 4–6 as the development read; if either interval includes 0 on 17–19, the report says the trip result does
not replicate for that comparison.

**Part C, ladder half read (2026-11-14 16:0x UTC; `python3 poc/gp_conj.py peertrip --main q32 --seeds 17,18,19`).** Qwen3-32B: ladder 74.3% at
17.8k, thinking 52.7% at 7.2k (3 thinking rows with no plan read, 0 with the old reader's misses): **ladder − thinking +16.4 [+9.5, +23.7]
utility** (predicted about +12, above 0): replicates. The gpt-oss-120b quick step adds +5.2 [+0.9, +9.8]. LLM-Modulo on seeds 17–19 is still
running.
**Extension, written before any gpt-oss-20b seed-17–19 row:** the other half of the split verdict on the same fresh seeds. gpt-oss-20b `trc`
(low effort), `trct`, `think`, `modulo` (high effort), seeds 17–19, second server GPU 6; the gpt-oss-120b `trc` rows are shared. Prediction from
seeds 4–6: ours − LLM-Modulo about −12 utility, interval below 0. Same rule: an interval including 0 is reported as not replicated.

**Part C, Qwen3-32B LLM-Modulo read (2026-11-14 21:0x UTC; `rwtrip --main q32 --seeds 17,18,19`).** Ours 74.3% at 17.8k, LLM-Modulo 66.3% at
35.0k (critics passed 199 of 300, all right, 4.41 rounds; 8 of 1,322 rounds with no plan read). **Ours − LLM-Modulo +16.6 [+8.0, +25.6]
utility, +8.0 [+1.7, +14.7] accuracy** (predicted about +14, above 0): replicates. gpt-oss-20b half still running.
**Second extension, written before any row: a third model tests the stated mechanism.** If LLM-Modulo's edge is the model's ability to act on
the critics' list, gpt-oss-120b (stronger than gpt-oss-20b) should also pass the critics in few rounds and beat our plain ladder (`trc` →
`trct` → `think`, 86.0% at seeds 1–3). Run: gpt-oss-120b `modulo`, high effort, seeds 1–3 (the seeds of its stored ladder), second server GPU
7. Prediction: critics passed on at least 280 of 300 in under 2.5 rounds on average; ours − LLM-Modulo below 0. If gpt-oss-120b instead
needs many rounds or ours wins, the mechanism statement is withdrawn and the split is reported per model only. Read with
`rwtrip --main oss120 --peer none --seeds 1,2,3`.
