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

**B-1 / B-2 final (2026-11-19 17:1x UTC; same API card in every baseline prompt, `orbase_{q8bc,oss20c}_*`; failure categories read
first: the remaining crashes are the models' own coding errors, e.g. `Objective.SetMinimization`, `!=` in a linear constraint, a missing
key). Scored on SIRL's corrected labels; typed − baseline paired by problem-seed, 95% bootstrap CI.**

| Method (3 seeds) | Qwen3-8B max flow | Qwen3-8B TSP | gpt-oss-20b max flow | gpt-oss-20b TSP |
|---|---|---|---|---|
| **Typed translation (ours)** | **91.4%** (0.5k tok) | **95.0%** | **92.5%** (0.6k tok) | **96.7%** |
| Few-shot template | 28.0% (+63.4 [+53.8, +73.1]) | 35.0% | 79.6% (+12.9 [+5.4, +20.4]) | 89.2% (+7.5) |
| Self-Debug | 19.4% (+72.0) | 8.3% | 75.3% (+17.2 [+9.7, +24.7]) | 32.5% |
| Chain-of-Experts | 19.4% (+72.0) | 13.3% | 53.8% (+38.7) | 55.0% |
| OptiMUS-style staged | 18.3% (+73.1) | 12.5% | 55.9% (+36.6) | 49.2% |
| LLMOPT five elements | 4.3% (+87.1) | 11.7% | 53.8% (+38.7) | 24.2% |
| SIRL-Qwen2.5-7B-Gurobi (published RL model) | 48.4% | 4.2% | | |
| gpt-oss-120b / Qwen3-32B plain program | 59.1% / 34.4% | 77.5% / 47.5% | | |

- **B-1 holds for both models**: on max flow typed translation beats every related-work baseline, every CI above 0 (closest: gpt-oss-20b
  few-shot, +12.9 [+5.4, +20.4]). It also beats SIRL-7B (+43.0 [+32.3, +53.8] for Qwen3-8B) and the larger models' programs.
- **B-2 holds for both models**: the few-shot template is the strongest baseline. The API card did not change the ranking (gpt-oss-20b
  baselines moved −11 to +1 points; Qwen3-8B few-shot +8).
- Typed translation is also the cheapest arm (0.5–0.6k tokens vs 0.8–3.9k).

**Addendum D, a third template registered before any run (written 2026-11-19 17:17 UTC).** Why: the method's claim is general (the model
writes type + data, a fixed verified model does the modelling), but both tested templates are graph problems. Capacitated facility location
is the next-largest ComplexLP template (39 problems; 29 keep a label in SIRL's corrected set, the rest were removed as incomplete), and the
models' own programs already reach 64–68% there (thinking 82% for gpt-oss-20b), so the room is smaller and the errors may be reading, not
modelling. `run_typed.py --v3`: one prompt with a three-type menu (max_flow, tsp, facility_location: open_cost, capacity, demand,
ship_cost); a fixed MILP (binary open, continuous shipments, demand met, shipments ≤ capacity × open), checked on problem 139 (446011).
Same models, seeds 1–3, scored on SIRL's corrected labels. Baselines on the same facility problems: the five related-work arms with the API
card (`run_orbase.py --v3`, tags `q8bf`, `oss20f`), plus every stored arm (own program, thinking, ORLM, STORM).
- T-3: facility location: typed − own program (`formx`) ≥ +10 points for both models (paired by problem-seed, CI reported).
- T-4: graph templates under the three-type menu: typed v3 within 5 points of typed v2 on max flow and TSP (a larger menu does not hurt).
**Decision.** T-3 holds → the method generalises beyond graph templates; the typed menu becomes the first step of the word-problem method.
T-3 fails → report where the facility errors are (reading vs modelling, from the stored JSON) and keep typed translation to templates where
the closure diagnostic shows modelling errors.

**Addendum D result (2026-11-19 17:43 UTC; `results/tmp_typed_d.py`; failure categories read first).** Scoring tolerance: the project's
scorer (`run_nlopt.correct`) accepts a relative error ≤ 1e-3; my typed/baseline scripts used 1e-6. On the graph templates every number is
identical under both (exact solvers, integer data), so addenda B/C stand. On facility location it matters: SCIP's default MIP gap (1e-4)
stops short of the label on large objectives (e.g. 316301 vs 316282), in the baselines' programs and in my own facility solver (fixed:
gap 0; rescoring the stored readings changes 8 of 219). Facility numbers below use the project tolerance 1e-3 for every arm.

| Facility location (29 problems × 3 seeds) | Qwen3-8B | gpt-oss-20b |
|---|---|---|
| **Typed translation v3 (ours)** | **93.1%** | 93.1% |
| Own program (`formx`) | 81.6% (+11.5 [+5.7, +18.4]) | 86.2% (+6.9 [+1.1, +13.8]) |
| Thinking + API card (`thinkf`) | 65.5% (+27.6) | 88.5% (+4.6 [−2.3, +11.5]) |
| Self-Debug | 9.2% (+83.9) | **94.3%** (−1.1 [−5.7, +2.3]) |
| Few-shot (its worked program is the TSP one: no facility example was written) | 8.0% | 90.8% (+2.3 [−3.4, +8.0]) |
| Chain-of-Experts / OptiMUS-style / five elements | 1.1% / 1.1% / 10.3% | 88.5% / 83.9% / 78.2% |
| ORLM-8B | 81.6% (+11.5) | |

- **T-3 holds for Qwen3-8B (+11.5 [+5.7, +18.4]) and fails for gpt-oss-20b (+6.9 [+1.1, +13.8] < +10).** gpt-oss-20b already models
  facility location right (Self-Debug 94.3%, thinking 88.5%), so a fixed solver has little to add; on the graph templates it did not.
  Qwen3-8B's baseline programs run but drop the opening costs or the open/close link (read from the stored code), so their 1–10% is
  modelling, not crashes.
- Typed misses are 3 problems in all 6 runs: one reading error (154, the cost table read differently each run), one problem the models call
  "other" (207), one solver-gap miss (165, fixed).
- **T-4 holds:** the three-type menu costs nothing on the graphs (v3 − v2: −1.1, +2.5, 0.0, −0.8).
- **Decision (as registered for a T-3 failure: report where the errors are).** The errors are above. Typed translation still beats the
  model's own program in all six model × template cells (every CI above 0) and is not significantly worse than any baseline in any cell
  (worst: gpt-oss-20b facility vs Self-Debug, −1.1 [−5.7, +2.3]), at the lowest cost. So it stays the first step for recognised types; the
  size of the gain is what varies: large where the model's own modelling of the template is wrong (graphs for both models, facility for
  Qwen3-8B), small where it is right. Next: grow coverage only where a stored-data closure diagnosis shows modelling errors.

**Addendum E, the type field as the router on the whole benchmark (written 2026-11-19 17:4x UTC, before any run).** Addenda A–D ran only
on problems my wording selector picked. Deployed, the model's own type field decides: a recognised type goes to its fixed solver, "other"
falls back to the model's own program (`formx`, stored, same seeds). The selector also misses templates: 9 ComplexLP max-flow problems
with other wording (ids 102–137) were never run. `run_typed.py --v3 --all`: all 863 MAMO problems (ComplexLP 211, EasyLP 652), Qwen3-8B
and gpt-oss-20b, seeds 1–3. ComplexLP scored on SIRL's corrected labels, EasyLP on its own labels; tolerance 1e-3 (project scorer).
- E-1 (false typing is harmless): on ComplexLP problems outside the three selected templates and on EasyLP, pipeline − own program ≥ −2
  points for both models.
- E-2 (the router finds what the selector missed): on the 9 unselected max-flow problems, pipeline − own program ≥ +20 for both models.
- E-3 (whole benchmark): ComplexLP, pipeline − own program ≥ +15 points for both models, CI above 0; reported next to every stored and
  related-work baseline that covers all problems (thinking, ORLM, STORM, SIRL-7B where run).
**Decision.** E-1 and E-3 hold → the pipeline (typed menu → fixed solver, else own program) is the word-problem method's first step and the
reported MAMO numbers. E-1 fails → typing needs a check before it is trusted (the type's data must also satisfy its solver: feasible,
complete); report.

**Addendum E result (2026-11-19 19:00 UTC; `results/tmp_typed_e.py`; failure categories read first; a Qwen3-8B lane hung on a max-flow
reading with source = sink, solver guarded and rerun).** All 863 MAMO problems × 3 seeds; ComplexLP on SIRL's corrected labels (203
problems), EasyLP on its own; project tolerance.
- **E-3 holds for both models.** ComplexLP, pipeline − own program: Qwen3-8B 76.5% vs 56.6%, **+19.9 [+16.1, +23.7]**; gpt-oss-20b
  82.8% vs 64.5%, **+18.2 [+14.9, +21.6]**.
- **E-1 holds as registered** (pooled ComplexLP-other + EasyLP: Qwen3-8B −1.0 [−1.5, −0.6], gpt-oss-20b 0.0; gpt-oss-20b types no EasyLP
  problem). **But Qwen3-8B loses −5.8 [−8.7, −3.3] on ComplexLP's non-template problems:** it types 70 of 276 of those rows as max flow or
  facility location, mostly the supply-redistribution template (e.g. node capacities as edges, source "source" not in the graph, value 0).
- **E-2 split:** unselected max-flow problems, Qwen3-8B +22.2 [+0.0, +44.4] (holds), gpt-oss-20b +14.8 [−3.7, +33.3] (fails): its misses are
  the largest graphs (9 nodes, ~72 edges) read incompletely (8 edges in some runs) or with a wrong capacity.
- **Post hoc, needs a prospective test:** the remedy named in the decision rule, a label-free validity check (max flow: source and sink are
  graph nodes, distinct, value > 0; facility: every customer and facility has shipping costs), keeps the gains and removes the loss:
  Qwen3-8B ComplexLP-other −5.8 → −0.4 [−1.1, 0.0], whole ComplexLP +22.4 [+18.9, +25.7]; gpt-oss-20b unchanged.
- **Against our strongest earlier method** (`forms`: retrieved programs of similar problems, the model's own; gpt-oss-20b 79.1% on
  ComplexLP), the pipeline with `forms` as its fallback reaches 84.2%, +5.1 [+3.0, +7.5]. For Qwen3-8B `forms` is weak (24.5%) and `formx`
  stays the fallback.

| ComplexLP, 203 problems × 3 seeds (corrected labels) | Qwen3-8B | gpt-oss-20b |
|---|---|---|
| **Typed menu → fixed solver, else fallback (with validity check)** | **78.9%** | **84.2%** (fallback `forms`) |
| Same, as registered (no check, fallback `formx`) | 76.5% | 82.8% |
| Own program, retrieved example from any model (`formx`) | 56.6% | 64.5% |
| Own program, retrieved example from itself (`forms`) | 24.5% | 79.1% |
| Thinking (`thinks` / `thinkf`) | 43.9% / 39.3% | 67.8% / 67.5% |
| ORLM-8B (published) | 34.2% | |
| Qwen3-32B best arm (`mips`) / Qwen3-14B best (`formo`) | 50.2% / 56.7% | |

**Decision:** E-1 and E-3 hold → the typed menu with fallback is the word-problem method's first step and our MAMO number. The validity
check is adopted only after a prospective test on a second source (next registration).

**Addendum F, prospective test of the validity check on five held-out sets (written 2026-11-19 19:0x UTC, before any run).** Sets: NL4OPT +
IndustryOR (345), OptMATH (100), OptiBench (605), BWOR (82), LogiOR (92); 1,224 problems, Qwen3-8B and gpt-oss-20b, seeds 1–3, the same
three-type menu (`run_typed.py --v3 --set ...`). Pipeline: a typed answer is used only if its type is one of the three and its data pass the
check fixed in addendum E (max flow: source and sink are distinct graph nodes, value > 0; facility: every customer and facility has
shipping costs; TSP: a tour exists); else the model's stored own program (`formx`, same seed). Each set's own labels, project tolerance.
- F-1 (the check makes the router safe on new data): pooled over the five sets, pipeline − own program ≥ −1 point for both models.
- F-2 (where it routes, it helps): on the rows routed to a solver, typed accuracy ≥ own program accuracy on the same rows, both models
  (counts per set reported; few rows are expected, as these sets hold few graph or facility problems).
Also reported: the same pipeline without the check.
**Decision.** F-1 holds → the check is part of the method. F-1 fails → the typed menu is restricted to problems whose data also pass a
second reading (both seeds' JSON agree), tested next.

**Addendum F result (2026-11-19 19:17 UTC; `results/tmp_typed_f.py`).** Five held-out sets, 1,224 problems × 3 seeds, fallback = own program.
- gpt-oss-20b: **F-1 holds** (+0.5 [+0.3, +0.8]); **F-2 holds** (58 routed rows: typed right 39, own program 19; OptMATH TSP 18/18 vs 2/18).
- Qwen3-8B: **F-1 holds** (−0.5 [−1.0, −0.1] ≥ −1); **F-2 fails** (231 routed rows: typed right 42, own program 62). Reading the rows: it
  forces non-graph problems into an invented graph (an investment knapsack as max flow from node 0 to node 5; a ferry/rail trip count as
  max flow from "source" to "sink"), consistently across seeds.
- Registered next test for a failed check (two readings agree): post hoc on these rows it keeps the gains but still routes consistent
  inventions (Qwen3-8B OptiBench: 33 routed, typed 0 vs own 10). Root cause is invention, not noise.

**Addendum G, a grounding check, registered before its prospective run (written 2026-11-19 19:17 UTC).** Principle: a fixed solver can only
be trusted on data copied from the text. A typed reading passes if (i) addendum E's validity check passes, (ii) every node / facility /
customer label appears in the question (case-insensitive, `_` read as a space, a number label as a standalone number), and (iii) every
numeric value appears among the question's numbers (commas removed), or is 0. Designed on seeds 1–3 (post hoc: Qwen3-8B held-out routed
rows 114, typed 36 vs own 14, pooled +0.6 [+0.3, +1.0]; MAMO ComplexLP unchanged). Prospective run: fresh readings, seeds 4–6, all of MAMO
and the five held-out sets, both models; fallback = stored own program of seed s − 3; `results/tmp_typed_g.py` fixed now.
- G-1: held-out pooled, grounded pipeline − own program: point estimate ≥ 0 and CI lower bound ≥ −0.5, both models.
- G-2: on rows the grounded pipeline routes, typed right ≥ own program right, both models, and in each set with ≥ 10 routed rows.
- G-3: MAMO ComplexLP (corrected labels) gain ≥ +15 for both models.
**Decision.** All hold → the method is: typed menu → validity + grounding check → fixed solver, else the fallback. Any fails → report the
failing set's rows and keep the method to the recognised-and-grounded cases only where it held.

**Addendum G result (2026-11-19 19:28 UTC; `SEEDS=4,5,6 python3 results/tmp_typed_g.py`; fresh readings, fallback = own program s − 3).**
- **G-1 holds for both models:** held-out pooled, grounded pipeline − own program: Qwen3-8B +0.6 [+0.2, +1.0], gpt-oss-20b +0.5 [+0.2, +0.8].
- **G-3 holds for both:** MAMO ComplexLP (corrected labels) Qwen3-8B 56.6% → 79.3% (+22.7 [+19.2, +26.2]), gpt-oss-20b 64.5% → 83.3% (+18.7
  [+15.4, +22.2]); EasyLP unchanged (Qwen3-8B −0.1, gpt-oss-20b 0.0).
- **G-2 holds pooled and fails in one set.** Routed rows: Qwen3-8B typed right 37 vs own program 15 (101 rows), gpt-oss-20b 34 vs 15 (46 rows);
  per set with ≥ 10 routed rows it holds in BWOR, LogiOR, OptMATH (18 vs 5) and NL4OPT + IndustryOR (9 vs 5 / 8 vs 8), and **fails for
  Qwen3-8B on OptiBench (15 routed rows: typed 1 vs own 4).** Reading the 15 rows: 9 are one warehouse problem duplicated three times in
  OptiBench (ids 78, 97, 321) and a set-covering problem whose label is 0 (both arms wrong on all of them); the 3 real losses are small
  integer programs read as max flow (fish boats and canoes, a two-plant shipment), grounded because their names and numbers are in the text.
- **Decision (as registered for a failure):** the method is typed menu → validity + grounding check → fixed solver, else the fallback. It
  holds pooled and in four of five held-out sets; the residual failure is max flow invented for small trip-count integer programs.

**Addendum H, the grounded pipeline on problems it never saw (written 2026-11-19 19:29 UTC, before any run).** Source: SIRL's OptMATH-Bench
193 minus the 100 OptMATH problems used above = 93 fresh problems (`NLOPT_SET=optnew`), its labels. Qwen3-8B and gpt-oss-20b, seeds 1–3:
typed menu (`run_typed.py --v3 --set optnew`) and, as the fallback and comparison, the model's own program with the API card (`run_nlopt.py
<m>_optnew mipf`; no retrieval pool exists for these problems). Check and scorer frozen: `valid` + `grounded` of `results/tmp_typed_g.py`.
- H-1: grounded pipeline − own program ≥ 0 (point estimate), CI lower bound ≥ −2, both models.
- H-2: on routed rows, typed right ≥ own program right, both models.
**Decision.** Both hold → the grounding check is adopted as part of the method (first test on unseen problems). Either fails → it stays a
MAMO-only result and the report says so.

**Addendum H result (2026-11-19 19:38 UTC; `results/tmp_typed_h.py`, frozen before the run; failure categories read first: Qwen3-8B's own
programs crash on 139 of 279 rows (its own code, with the API card), 85 of its typed replies are not valid JSON (54 hit the 4k cap on
large "other" problems) and fall back; gpt-oss-20b clean).** 93 unseen OptMATH problems × 3 seeds:
- **H-1 holds for both models:** grounded pipeline − own program: Qwen3-8B 14.0% vs 11.1%, +2.9 [+0.7, +5.4]; gpt-oss-20b 28.3% vs 25.1%,
  +3.2 [+1.4, +5.4].
- **H-2 holds for both:** routed rows, typed right 12 vs own program 4 (22 rows), and 12 vs 3 (12 rows; all TSP).
- **Decision:** the grounding check is adopted. The method is: typed menu → validity + grounding check → fixed solver, else the fallback.

## Baseline registration I (2026-11-20 13:32 UTC, CRITIQUE PLAN P2): the official LLMOPT checkpoint, before any row exists
Runner poc/run_llmopt.py: ant-opt/LLMOPT-Qwen2.5-14B (ICLR 2025) with the official repository's prompts copied verbatim
(poc/llmopt_prompts.py) and the paper's self-correction loop (≤ 12 generations; the repository ships the prompt, not the loop); Pyomo
with HiGHS (a missing solver binary is served by HiGHS at gap 0). Sets: MAMO (863), NL4OPT + IndustryOR, OptMATH (100), OptiBench, BWOR,
LogIOR, unseen OptMATH (93); seeds 1–3; every call's tokens counted. Scored with poc/analyze_frontier.py's scorer (SIRL-corrected
ComplexLP labels, project tolerance), utility at rates 0.25–2.
- **Prediction.** Its model card reports (original labels) MAMO ComplexLP 85.8%, OptiBench 66.4%, OptMATH 40.0%, IndustryOR 44.0%,
  NL4OPT 97.3%. Our full method (typed → cascade, pool-free) has OptiBench 63.1 / 70.6%, OptMATH 20 / 36% (Qwen3-8B / gpt-oss-20b).
  We predict LLMOPT beats the full method in accuracy on NL4OPT + IndustryOR and OptMATH for Qwen3-8B, and loses on the ComplexLP
  templates (TSP labels that reward subtours no longer count).
- **Decision rule.** Each set × model cell is reported as full − LLMOPT utility at rate 0.5 with its 95% CI and the sign at the other
  rates and cost views. A cell whose CI is below 0 is a loss of the method on that set and is stated as one; no cell is dropped. Sets
  that may be in LLMOPT's training data (all but MAMO, by its card) are marked.

### Baseline registration I result (2026-11-21 21:00 UTC; poc/analyze_claims.py, 16 claims, Holm, problem-clustered)
LLMOPT-14B, three seeds, sandbox with real solvers (rows that hit the earlier solver crash rerun in full: 199 / 78 / 63). Its accuracy:
MAMO EasyLP 87.0%, ComplexLP 40.5% (SIRL-corrected labels), NL4OPT + IndustryOR 66.5%, OptMATH 18.7%, OptiBench 66.1% (its card:
66.4%, so the harness reproduces it there), BWOR 24.4%, LogIOR 20.3%, unseen OptMATH 15.4%.
Full method − LLMOPT, utility at rate 0.5:
| set | Qwen3-8B | gpt-oss-20b |
|---|---|---|
| NL4OPT + IndustryOR | +5.1 [+1.9, +8.3] holds | +9.1 [+5.6, +12.7] holds |
| OptMATH (100, seed 1 own program) | +5.7 [−4.9, +15.6] not shown | +24.7 [+14.2, +35.0] holds |
| OptiBench | **−5.0 [−7.5, −2.4]: a loss** | +4.5 [+2.0, +7.1] holds |
| BWOR | +9.4 [+3.3, +15.9] holds | +35.5 [+26.5, +45.2] holds |
| LogIOR | +16.9 [+9.9, +24.1] holds | +33.3 [+25.7, +41.2] holds |
Prediction check: wrong for Qwen3-8B on NL4OPT + IndustryOR and OptMATH (predicted LLMOPT ahead; it is behind or tied); right on the
templates. The registered rule makes Qwen3-8B on OptiBench a loss of the method. Where it comes from (by OptiBench type): linear
problems without a table, LLMOPT 81.9% vs full method 76.7% (Qwen3-8B's own program 47.3%, so the cascade's thinking does the work at
6.3k tokens vs LLMOPT's 2.4k); on nonlinear problems the two tie (49.1 / 50.1; 16.7 / 18.0). With gpt-oss-20b the full method is ahead
on every type.

## Related work found after the results (2026-11-21 21:39 UTC) — what typed translation is new against
- **BIND / Text2Opt-Bench** (Gao et al., "Models Can Model, But Can't Bind", COLM 2026, arXiv 2605.21751, code SprocketLab/Text2Opt-Bench):
  splits text-to-optimization into modelling and binding (copying data); its two-phase template evaluation (a binder writes instance
  JSON, a deterministic template solver for transportation / job-shop solves it) is the same mechanism as our typed translation and
  predates it. What remains ours: the model chooses the type from a menu (or "other"), a validity + grounding check decides whether the
  fixed solver is trusted, and anything else falls back to the cascade; tested on public natural-language benchmarks with corrected
  labels. The failure is the opposite of BIND's headline: on MAMO's small graphs the models bound the data right and modelled it wrong
  (BIND's binding limit grows with instance size; our graphs have ≤ 10 nodes). BIND is not runnable as a baseline here: its inference-
  time method reads instance data serialized by the benchmark's own generator (an oracle our sets lack), and its trained binder is not
  released.
- **Template / experience libraries for optimization modelling** (COMPASS, arXiv 2611.12060: a DAG of templates with a learned retrieval
  policy; AlphaOpt: a self-improving experience library) and **tool induction** (LATM, CRAFT, TroVE, ReGAL) cover the general route of
  inducing types automatically. A general typed schema (the model writes the whole LP as records, a fixed compiler solves) is BIND's
  phase-1 schema and LLMOPT's five-element pipeline. Decision: no further typed-translation method experiment; the report presents
  typed translation as a template-specific instance of BIND's two-phase idea plus our routing check.

## Addendum J (registered 2026-11-21 23:40 UTC, before any row): the full method with the recipe's repair turn, against LLMOPT-14B
Why: W3's full method (typed → cascade) left out the established recipe's cheap repair turn (HO7: one non-thinking turn shown a visible
failure — crash, no value, 'No Best Solution' — before escalating). Qwen3-8B's pool-free own programs crash on 377 of 1,026 linear
OptiBench rows, 280 of them on one API misuse (`solver.Constraint(expr, ub)`), so its cascade pays for thinking where a repair might do.
Prior work: self-repair from execution feedback (Self-Debug, Chen et al. 2024; our HO7); not a new method, the method as defined.
Run: poc/run_repair.py on the pool-free own programs (freef on OptiBench / BWOR / LogIOR, mipf on NL4OPT + IndustryOR, OptMATH (seed 1),
unseen OptMATH), Qwen3-8B and gpt-oss-20b, seeds 1–3. Full method J = typed menu (valid + grounded) → own program → on a visible
failure, one repair → peer agreement → thinking; repair tokens paid.
- **J-1.** Qwen3-8B on OptiBench: full J − LLMOPT utility interval includes or exceeds 0 (closes the W3 loss).
- **J-2.** J − W3's full method ≥ 0 on the held-out pool, both models (the repair does not cost utility).
Decision: J-1 holds → the report's word-problem method includes the repair and the OptiBench loss is closed; fails → it stays a loss.
Scored with analyze_claims-style clustered bootstrap, Holm over J-1 and J-2 (both models).

### Addendum J result (2026-11-22 23:58 UTC; python3 poc/analyze_claims.py, family J, Holm over 4)
Repair rows: Qwen3-8B 1,808 visible failures repaired (596 now print a value, 445 right; 726 tokens each), gpt-oss-20b 764 (306, 196).
- **J-1 Qwen3-8B, OptiBench: full method with repair − LLMOPT −2.1 [−4.5, +0.4] → holds as registered (the interval reaches 0); the W3
  loss (−5.0) is no longer shown, and it is not a win (inconclusive).** gpt-oss-20b: +4.8 [+2.3, +7.4].
- **J-2 holds for both models:** repair − no repair on the held-out pool +1.8 [+1.4, +2.4] (Qwen3-8B), +0.3 [+0.1, +0.5] (gpt-oss-20b).
- Descriptive, every held-out set (full method with repair − LLMOPT): Qwen3-8B NL4OPT + IndustryOR +5.6, OptMATH +5.0 [−5.6, +15.1],
  OptiBench −2.1, BWOR +11.2, LogIOR +17.7; gpt-oss-20b +9.5, +24.5, +4.8, +36.1, +33.1.
Decision (registered): the report's word-problem method includes the repair turn; Qwen3-8B on OptiBench is reported as inconclusive
against LLMOPT (−2.1 [−4.5, +0.4]), not as a win. The repair's remaining Qwen3-8B crashes are the same API misuse (122 rows).

### Sensitivity on expert-audited labels (2026-11-22 00:42 UTC; OR_CLEAN=1 python3 poc/analyze_claims.py; Xiao et al. 2025 subsets of MAMO, OptiBench 403 / 605, NL4OPT)
The OptiBench verdicts move against us once bad labels go: Qwen3-8B full method with repair − LLMOPT **−3.9 [−6.8, −1.1], a loss again**
(J-1 holds only on the raw labels); gpt-oss-20b +1.7 [−1.2, +4.7], inconclusive (raw: +4.8). Qwen3-8B on NL4OPT + IndustryOR +4.0
[+0.7, +7.4], Holm p 0.053 (raw: holds). Unchanged in sign and still holding: W1 both models (+25.5 / +8.6), W2 both (+4.2 / +1.2), BWOR,
LogIOR, gpt-oss-20b NL4OPT + IndustryOR and OptMATH, J-2 both. The report states both label sets; on audited OptiBench the method loses
to LLMOPT-14B for Qwen3-8B and is inconclusive for gpt-oss-20b.
*Cost-view check (2026-11-22 01:42 UTC):* on audited OptiBench the Qwen3-8B loss to LLMOPT holds at every rate (0.25–2) and in every cost
view (output tokens; tokens × active parameters, LLMOPT at 14B; output + 0.25 × input): from −3.0 [−5.9, −0.1] (size, 0.25) to −7.4
[−10.5, −4.3] (output, 2). gpt-oss-20b is inconclusive in most views and ahead only where LLMOPT's 14B tokens are priced by size at
rate ≥ 1 (+3.8 [+0.8, +6.8]).
