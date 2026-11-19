# PREREG_TYPED — typed translation: the model writes the data, a verified solver does the modelling

Written 2026-11-19 15:1x UTC, before any typed-translation output exists.

**Why.** On the computation track the cross-family cascade's remaining errors on audited MAMO ComplexLP are mostly programs every model
writes the same wrong way (30 of 54 errors, 3 seeds). On max flow (stored rows, `results/tmp_flow_closure.py`) the models read the data
right and model it wrong: a fixed max-flow algorithm on the capacity table the model wrote into its own program is right 27 of 36
(Qwen3-8B; its own programs 12 of 36), 18 vs 7 of 26 (gpt-oss-20b), 35 vs 17 of 42 (Qwen3-14B). The shared bug: the objective counts flow
out of the source while return edges into it are free. This is the puzzle method's split (the model translates, the solver searches)
applied to modelling.

**Related work (checked 11-19).** OptiMUS (2402.10172) separates the data from the description but still has the LLM write the constraints
and code; LLMOPT (2410.13213) fine-tunes a five-element formulation; ORLM (2405.17743) trains models to write the model and notes frequent
constraint errors. None hands a recognised template to a fixed solver and measures that modelling, not reading, causes the shared errors.

**Run.** MAMO ComplexLP problems of the two graph templates (31 max flow, 40 TSP; selected by wording, all 211 ComplexLP, not only the
audited subset), seeds 1–3, Qwen3-8B and gpt-oss-20b (low effort), no thinking: the model returns {type, edges, source, sink} as JSON;
`poc/run_typed.py` solves max flow (Edmonds–Karp) and TSP (enumeration). Compared, paired by problem-seed, with the same model's stored quick
program (`formx`) on the same problems.

**Predictions.**
- T-1: max flow: typed − own program accuracy ≥ +20 points for both models (scored against the exact max flow computed from the problem
  text, and also reported against the dataset label).
- T-2: TSP: typed ≥ own program − 5 points (no real loss), scored against the dataset label (two TSP labels are known wrong; reported).
**Decision.** T-1 holds → typed translation joins the word-problem method for recognised templates (the type is the model's own call; an
"other" falls back to the cascade). T-1 fails → modelling is not the bottleneck after all; report.

**Result (2026-11-19 16:1x UTC; `results/tmp_typed_score.py`; failure categories read first: 69–71 of 71 rows per run returned a usable
typed answer).**
- **T-1 holds.** Max flow, against the exact max flow from the problem text: typed 86.4% vs own program 37.0% (Qwen3-8B), **+49.4
  [+38.3, +60.5]**; gpt-oss-20b 87.7% vs 46.9%, **+40.7 [+28.4, +53.1]**. Against the dataset label: +48.4 and +40.9.
- **T-2 fails as registered (against the dataset label: −52.5, −34.2), because the labels are wrong.** For 38 of the 39 TSP problems with a
  complete matrix, the MAMO label equals the minimum-cost *cycle cover* (subtours allowed), not the best tour; the two are equal in only 5.
  Independently of any model, a text parser recovers 10 matrices: their optimal tour equals the label once and gpt-oss-20b's typed answer 8
  times. The models' own programs reproduce the label's bug (no subtour elimination): Qwen3-8B's programs match the label on 64.9% but the
  optimal tour on 36.9% (gpt-oss-20b 45.9% / 47.7%), on the 37 problems where both models read the identical matrix. Typed translation
  returns the optimal tour on that matrix (not an independent check for seed 1, whose readings define it).
- **Decision:** typed translation joins the word-problem method for recognised templates. The report states that MAMO ComplexLP's TSP labels
  (and so every published accuracy on them) reward the missing subtour constraint; 11 of these TSP problems are in the audited subset.

**Baselines on the same problems (added 2026-11-19 16:3x UTC, user: "why don't we have baselines to compare?"; `results/tmp_typed_baselines.py`,
every stored MAMO arm, 3 seeds; max flow scored against the exact max flow from the text, TSP against the optimal tour on the matrix both
typed readings agree on, which is not independent of typed translation).**

| Method (stored arm) | Max flow (29) | TSP (37) | Tokens (max flow) |
|---|---|---|---|
| **Typed translation, gpt-oss-20b / Qwen3-8B (ours)** | **87.7% / 86.4%** | **100% / 100%** | 0.6k / 0.5k |
| STORM (published OR reasoning model, full agent) | 75.9% | 40.5% | 13.9k |
| gpt-oss-20b thinking + API fact (`thinkf`) | 74.7% | 42.3% | 2.9k |
| Qwen3.6 thinking + API fact | 72.4% | 70.3% | 41.7k |
| gpt-oss-20b quick program, best prompt (`forms`) | 58.6% | 95.5% | 0.7k |
| Qwen3-14B thinking program (`formxt`) | 52.9% | 32.4% | 7.3k |
| Qwen3-8B thinking program (`formxt`) | 49.4% | 31.5% | 8.6k |
| Qwen3-32B thinking (`thinks`) | 34.5% | 47.7% | 8.6k |
| Qwen3-8B quick program (`formx`, the cascade's first step) | 34.5% | 36.9% | 0.8k |
| ORLM-LLaMA-3-8B (published, fine-tuned for OR) | 19.5% | 27.9% | 1.9k |

On max flow typed translation beats every baseline, including the published specialist models and thinking at 15–70× the tokens. On TSP
the comparison is against our own reference (no independent labels exist); gpt-oss-20b's quick program with a stated-example prompt
already reaches 95.5% there. Not run: multi-stage agent pipelines such as OptiMUS and Chain-of-Experts.

**Addendum B, related-work baselines run in our harness (written 2026-11-19 16:3x UTC, before any of these rows exists; user: "why don't we
have related research as baselines?").** Same 71 problems × seeds 1–3; `poc/run_orbase.py`:
- Self-Debug (Chen et al. 2304.05128): program + execution feedback, up to 3 rounds.
- OptiMUS-style staged prompting (2402.10172), single model: parameters as JSON → formulation in math → code → one debugging round.
- LLMOPT's five-element formulation (2410.13213) as a prompt (no fine-tuning).
- Few-shot template: one correct program of the same template for another instance (our own, with the right max-flow objective and MTZ
  subtour elimination) — the "teach the convention" baseline.
- Stronger models, plain program: gpt-oss-120b and Qwen3-32B.
Already stored: ORLM-LLaMA-3-8B and STORM (published OR models), thinking at several settings. Chain-of-Experts (Xiao et al., ICLR 2024) added 16:3x as arm `coe` (single model playing its experts: terminology interpreter → modeling expert → programming expert → evaluator with one reflection round).
Models for the prompted methods: Qwen3-8B and gpt-oss-20b (low effort), as for typed translation.
- B-1: on max flow (exact answers) typed translation beats every one of these baselines for the same model.
- B-2: the few-shot template is the strongest prompted baseline (it states the convention the others miss); report its gap to typed.

**Addendum C, recent related work (written 2026-11-19 16:4x UTC, user: "don't we have recent related research?").** Checked 2025–2026:
SIRL (2505.11792; RL with solver feedback, released 7B/32B weights, reported state of the art among open models), Step-Opt (2506.17637),
OptiTree (2510.22192; tree search over modelling sub-problems), an error-localising modeller (2602.11164), StarOR (2606.15197; tree search
+ test-time RL), OptiSkill (2609.22987; skill bank). **The TSP label error is already known:** the SIRL team corrected MAMO ComplexLP in
2025-09 (35 TSP answers recomputed by enumeration on LLM-extracted, expert-checked cost matrices; CFLP problems removed or revised), so our
TSP finding is a rediscovery, and their fix uses the same idea as typed translation for labels. Max-flow answers were not changed there.
Added baseline: **SIRL-Qwen2.5-7B-Gurobi** with its own prompt (arm `sirl`, gurobipy in the sandbox), same 71 problems, seeds 1–3.
- C-1: typed translation (Qwen3-8B, gpt-oss-20b) beats SIRL-7B on max flow (exact answers).
Not run (no released code or weights we can use in time, or 32B+ only): OptiTree, StarOR, the error-localising modeller, Step-Opt, SIRL-32B.

**Addendum B/C results, partial (2026-11-19 16:47 UTC; `results/tmp_orbase_score.py`, `results/tmp_orbase_sirlref.py`).** Scored against
**SIRL's corrected labels** (independent of our typed reading; all 31 max-flow and 40 TSP problems matched by question text; on max flow they
equal the MAMO labels, and on one problem (mamo_complex-112) they overturn our text parser's reference, so they replace it here). Paired
typed − baseline per problem-seed, 95% bootstrap CI.

| gpt-oss-20b (low effort), 3 seeds | Max flow | TSP | Tokens (max flow) |
|---|---|---|---|
| **Typed translation (ours)** | **92.5%** | **96.7%** | 0.6k |
| Few-shot template | 84.9% (+7.5 [+2.2, +14.0]) | 92.5% (+4.2 [+0.0, +8.3]) | 0.8k |
| Self-Debug | 74.2% (+18.3 [+9.7, +28.0]) | 45.8% (+50.8) | 1.1k |
| Chain-of-Experts | 66.7% (+25.8 [+16.1, +35.5]) | 61.7% (+35.0) | 2.7k |
| OptiMUS-style staged | 62.4% (+30.1 [+20.4, +39.8]) | 43.3% (+53.3) | 1.9k |
| LLMOPT five elements | 53.8% (+38.7 [+28.0, +49.5]) | 30.8% (+65.8) | 1.3k |
| gpt-oss-120b plain program | 59.1% | 77.5% | 1.3k |
| Qwen3-32B plain program | 34.4% | 47.5% | 1.0k |

- **B-1 holds for gpt-oss-20b**: typed beats every related-work baseline on max flow, each CI above 0; the closest is the few-shot template
  (+7.5 [+2.2, +14.0]). It also beats the 6× and 4× larger models' plain programs.
- **B-2 holds for gpt-oss-20b**: the few-shot template is the strongest prompted baseline; it shows the convention (net outflow, MTZ) is most
  of what the other methods miss. Typed translation still wins, at lower tokens, and needs no worked program per template.
- **Qwen3-8B: not scored yet.** Its few-shot and five-element programs fail to run on 52 and 77 of 81 max-flow rows (runtime errors),
  which may be OR-Tools API misuse under our prescribed library rather than modelling; rows did not store the error text. The runner now
  stores error, code and output per round; a diagnostic rerun (seed 1, few-shot and five elements) is queued. Until its failure categories
  are read, Qwen3-8B baseline rows are not used as evidence.
- C-1 (SIRL-7B): running.

**C-1 result (2026-11-19 17:0x UTC).** SIRL-Qwen2.5-7B-Gurobi, its own system prompt, seeds 1–3, scored on SIRL's corrected labels; the
answer is the program's last printed line, as for every arm (a first reader took Gurobi's log line "Best objective …, gap 0.0000%" and
read 0 on every TSP; rescored from the stored output, `orbase_sirl3_*`).
- **C-1 holds.** Max flow: SIRL-7B 48.4% vs typed translation 91.4% (Qwen3-8B) / 92.5% (gpt-oss-20b), same problem-seeds.
- TSP: SIRL-7B 4.2%. Its programs keep the in/out-degree constraints and drop subtour elimination; 37 of 120 answers equal MAMO's original
  cycle-cover label. The published RL-trained model reproduces the label's modelling error that its own team later corrected in the data.
- Qwen3-8B's related-work baselines (addendum B): the crashes were OR-Tools API misuse (`solver.Constraint(expr, expr)`, a generator as a
  coefficient), and our baseline prompts lacked the pywraplp API card our own stored program arms always had. All five baselines are rerun
  for both models with the same card (`ORB_CARD=1`, tags `q8bc`, `oss20c`); the card-free rows stay as recorded above but the card rows
  decide B-1/B-2.
