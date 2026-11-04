# Facts, Tools, and Checks: Why LLMs Write Wrong Geometry and Optimization Code, and How to Fix It Without Knowing the Task

*Graduate NLP course project proposal: computational geometry and combinatorial optimization*

> **About this file.** This is the single project document: the proposal (Sections 1–4), Appendix A (code, how to run it, status), and Appendix B (the tools provided and worked examples of correct and failing programs), Appendix C (more examples of problems, solutions and diagnostics), and Section 5 (a critical review of the pilot). The full chronological experiment log, with every pilot finding, correction and caveat, is [docs/FINDINGS.md](docs/FINDINGS.md); the final tables are at its end. The code and final results were copied from `/NAS/SJ/llm_algo_poc` on 2026-10-11, and paths inside the code point to this folder.

## 1. Problem Statement

Large language models (LLMs) are now routinely asked to solve algorithmic problems by writing programs: a convex hull, a point-in-polygon test, a knapsack or TSP model for an optimization solver. These programs often *look* right and still fail. Some crash on library calls that don't exist. Some break on degenerate inputs such as collinear points, duplicates, or a query point on an edge. Some are feasible but far from optimal.

The usual response is to put more into the prompt: more documentation, more helper functions, a "be robust" instruction, or more reasoning tokens. Little is known about which of these in-context additions help, which hurt, and why.

**Research question.** What information in the prompt makes LLM-written programs for computational geometry (CG) and combinatorial optimization (CO) fail? Which fixes work *without* hand-picking the right tools for each task?

We study four sub-questions:

1. **Failure sources.** How much do missing facts explain the failures, compared with genuine algorithmic errors? Missing facts include the execution environment (which libraries exist) and library/API contracts (solver status codes, callback conventions, argument types).
2. **Irrelevant tools.** Do correct but unneeded helper functions or API documentation degrade the generated code? If so, how does the harm scale with the number of extras, does it require the model to *use* them, and can an instruction ("most of these are not needed") remove it?
3. **Task-agnostic fixes.** Can two cheap interventions match hand-picked task-specific tools? (a) State the facts the model gets wrong. (b) Sample a few programs and keep one that passes a label-free check: metamorphic consistency for geometry, feasibility plus objective for optimization. When does each work?
4. **Who benefits.** How do these effects change with model size (1.7B–72B), model family, and thinking (reasoning) mode?

## 2. Background (Related Work)

**Irrelevant context hurts LLM reasoning.**
- Shi et al. (2023, GSM-IC) showed that adding irrelevant sentences to math word problems sharply reduces accuracy.
- Later controlled studies show accuracy falling roughly as a power law in the number of distractors ("How Is LLM Reasoning Distracted by Irrelevant Context?", EMNLP 2025).

These studies use natural-language reasoning. We ask the same question for *code-level* context: helper functions and API documentation that the model may copy into its program.

**Tool overload in LLM agents.** For function-calling agents, large tool catalogs reduce tool-selection accuracy. Proposed responses include:
- retrieving a small relevant subset (RAG-MCP; ToolRet, 2025);
- adapting how many tools are shown ("How Many Tools Should an LLM Agent See?", 2026);
- exposing a minimal causal tool frontier (ToolChoiceConfusion, 2026).

Related work measures spurious tool invocation when all tools are irrelevant, and a "tool-use tax" under semantic distractors. All of this concerns *which tool an agent calls*. We study tools *embedded into generated programs*, and we look for harm that occurs even when the extra tools are never called.

**Documentation-augmented code generation.** Jain et al. (2024) found that retrieved API documentation helps on rarely used APIs but cuts accuracy on frequently used ones when retrieval brings irrelevant documentation. Their fix is to retrieve only when needed. Our CO results show the complementary case: a short, problem-specific snippet beats a complete cheat sheet.

**LLMs with solvers and code.**
- Program-aided reasoning (PAL, Program-of-Thoughts) and solver-augmented reasoning (Logic-LM, SatLM, LINC) translate problems into code or solver models.
- NL4Opt and OptiMUS translate optimization problems into solver formulations.
- ZebraLogic (Lin et al., ICML 2025) shows that direct LLM reasoning collapses as the search space grows ("curse of complexity").

These works rarely isolate *API misuse* as a failure source. We show it can make solvers look worse than direct reasoning until it is fixed.

**Selection and verification.**
- Self-consistency (Wang et al., 2023) and test-based selection (e.g. CodeT) choose among sampled outputs.
- Metamorphic testing checks that outputs respect known relations between transformed inputs, so no ground-truth labels are needed.
- In computational geometry, robustness to degenerate inputs and exact arithmetic is a classic problem (Kettner et al., "Classroom examples of robustness problems in geometric computations", 2008).
- Studies of LLM code robustness find that most robustness gaps are missing condition checks.

We combine metamorphic testing with sampling as a label-free selector for geometry code.

**Gap.** No prior work, as far as we found, studies:
- in-context *helper functions and solver documentation* as distractors for algorithmic code;
- whether that harm requires the helpers to be used;
- how it differs between domains (geometry vs optimization);
- when task-agnostic fixes (stated facts vs verified sampling) can replace task-specific tool selection.

## 3. Motivation

1. **Practical.** Code assistants increasingly receive large tool catalogs, documentation dumps, and "helpful" utility libraries. If plausible but unneeded tools silently make programs worse, then "give the model everything" is the wrong default. Practitioners need to know what to include and what to leave out.
2. **Scientific.** Algorithmic code has exact, automatic correctness checks: exact geometric predicates, proven optima. Small variations in prompt content can therefore be measured precisely, at a scale and rigor rarely possible for open-ended NLP tasks.
3. **Our pilot study already found surprising, large effects** (Section 4.2):
   - One sentence stating the environment ("only the Python standard library is available") moved a 14B model from 79 to 100 and Llama-3.1-8B from 83 to 99 on our geometry suite.
   - Eight correct but unneeded geometry helpers cost 17–29 points at every model size.
   - Telling the model that most helpers are unnecessary did not remove the harm.
   - On the other hand, extra documentation had essentially no effect on optimization code. These domain differences call for explanation.
4. **Feasible and well scoped.** All experiments use open-weight models (Qwen3 1.7B–32B, Llama-3.1/3.3, Gemma-3, Granite) served locally with vLLM on four A100s. Problems and references are generated programmatically.

## 4. Experiment Design

### 4.1 Setup

**Tasks.**
- *Computational geometry* (5 core + 2 held-out tasks):
  - core: convex hull vertex count, twice polygon area, point-in-polygon, segment-intersection count, closest-pair distance;
  - held-out: convexity test, points strictly inside a triangle.

  Each instance has an exact integer oracle. Each is also given in **8 equivalent versions** (translated, rotated, mirrored, permuted, scaled, offset by about 10^9, plus a degenerate variant), so a program is counted correct only if it is right on all 8.
- *Combinatorial optimization* (4 core + 2 held-out problems):
  - core: 0/1 knapsack, TSP, graph coloring, makespan scheduling;
  - held-out: bin packing, minimum vertex cover.

  Exact or best-known references come from DP, Held–Karp and CP-SAT. The metric is the share of instances within 1% of the reference.

**Approaches.** The model writes a Python program, executed in a sandbox (CPU, memory and time limits). Optimization programs may use OR-Tools and get up to 2 repair rounds with error feedback. Direct (no-code) answers serve as a baseline.

**Interventions (independent variables).**
- environment fact (standard-library line);
- helper toolbox: none, task-matched (encapsulating) predicates, or task-matched plus K ∈ {0, 2, 4, 8} related or unrelated distractors;
- delivery of helpers: copy-in vs pre-defined;
- toolbox header wording ("should use" vs "most are not needed");
- API-contract sentence;
- documentation: none, full OR-Tools cheat sheet, or problem-specific snippet (± K unneeded API lines, ± other problems' snippets);
- verified sampling with k ∈ {1…5}: metamorphic-consistency filter plus vote for geometry; feasibility plus best objective for optimization;
- thinking mode on/off.

**Models.** Qwen3 1.7B / 8B / 14B / 32B-AWQ; Qwen2.5-72B; Llama-3.1-8B; Llama-3.3-70B; Gemma-3-27B; Granite-4.1-8B.

**Statistics.**
- greedy decoding plus T=0.7 with 2–3 seeds;
- 300 programs per geometry condition, 252 optimization instances (108 held-out);
- paired cluster-bootstrap 95% confidence intervals over instances;
- every anomaly sanity-checked by re-running stored programs, which caught several harness confounds.

### 4.2 Toy (pilot) experiments, already run

**T1. Environment fact** (geometry, greedy, programs correct on all 8 versions out of 100):

| model | without the standard-library line | with it |
|---|---|---|
| Qwen3-14B | 79 | **100** |
| Llama-3.1-8B | 83 | **99** |

The failures without the line were imports of an uninstalled geometry library (shapely).

![T1: environment fact](figs/fig1_environment_fact.png)

**T2. Irrelevant-helper dose-response** (geometry, n = 300, T=0.7). Change when adding 8 related but unneeded helpers:
- 8B: **−17.7** [−23.0, −12.7]
- 14B: **−29.0** [−34.3, −23.7]
- 32B: **−17.0** [−22.7, −11.7]
- Qwen3-1.7B: **−35.7** [−41.7, −29.7]; Llama-3.1-8B (2 seeds): **−39.3** [−43.8, −34.7], the largest harm measured.
- Llama-3.3-70B (3 seeds, 900 paired programs): −0.8 [−3.8, +2.1].
- So the harm tracks **capability, not model family**: weaker models (Qwen3 8B–32B, Llama 8B) are hurt; the strongest model tested ignores irrelevant helpers.
- **A small thinking budget suffices:** forcing at most 1,024 thinking tokens restores 92–95 with 8 extra helpers (0 tokens: 62–75; 4,096 tokens ≈ full thinking).
- **Reasoning removes it** (2 seeds, 200 paired programs each): the same Qwen3 models with thinking lose only −1.5 [−4.5, +1.5] (8B), −0.5 [−2.5, +1.0] (14B) and −3.0 [−5.5, −1.0] (32B), Even Qwen3-1.7B with thinking loses only −4.3 [−9.3, +0.7] (3 seeds; −35.7 without thinking), and the reasoning-distilled DeepSeek-R1-Distill-Llama-70B loses 0.0 [−3.0, +3.0]. Robustness to irrelevant in-context tools comes with reasoning or high capability.

![Where robustness to plausible helpers appears](figs/fig7_distractor_by_model.png)

Findings:
- The harm grows steadily with K (8B: 98 → 87 → 81 → 74.5).
- Six *unrelated* helpers of similar length cost only 4–7 points and are almost never called.
- With helpers pre-defined, so they never need copying, the harm stays (8B −12.3, 32B −15.0). It is semantic: over-engineered hull, area and closest-pair logic. For 14B most of the raw drop (incl. the −29.0 above) is copy failure: re-scored with helpers pre-defined it is −7.7 ("should use") and −0.3 (neutral header).
- A "most are not needed" header cuts helper use by 40–65% but recovers accuracy by only 0–5 points.
- Worked examples of the prompt, the helpers and the failing programs are in Appendix B; the mechanism analysis (why plausible helpers hurt) is in Appendix B.4.

![T2: dose-response](figs/fig2_distractor_dose.png)

![T2: mechanism, copy-in vs pre-defined helpers](figs/fig3_mechanism.png)

**T3. Domain contrast** (optimization). Adding 8 unneeded OR-Tools lines, or the other problems' snippets, changes accuracy by −2.4 to +0.6 points (confidence intervals include 0). Optimization code is robust to extra documentation; geometry code is not.

![T3: domain contrast](figs/fig4_domain_contrast.png)

**T4. Stating facts** (optimization, 252 instances, 3 seeds). Problem-specific snippet vs full cheat sheet:
- 8B: **+.36** [+.31, +.42]
- 14B: **+.15** [+.11, +.19]
- 32B: **+.04** [+.02, +.07]

On held-out problems the snippet still wins at every size (+.11 / +.16 / +.26). Single sentences fix systematic misconceptions:
- the OPTIMAL-status line takes a 14B solver from .60 to .96;
- an argument-type sentence takes 14B segment intersection from 16 to 55 of 60.

![T4: optimization documentation](figs/fig5_co_docs.png)

**Realistic check (capacitated vehicle routing, 30 instances, exact references):** with no documentation 14B/32B reach the optimum on .20/.23; the full sheet, which shows TSP routing but not the capacity constraint, gives .20/.07 (32B invents non-existent API calls); the CVRP snippet gives .73–.80 / .77–.90, and best-of-3 with a label-free choice reaches 1.00 for both. 8B fails on API errors in every condition (≤ .17 even with thinking). Llama-3.3-70B shows the same pattern (.40 / .60 / .83–.93, best-of-3 1.00). **Thinking does not replace the fact:** with thinking but no documentation, 14B / 32B / R1-Distill-Llama-70B reach only .33 / .03 / .00 (11–19k tokens per program), versus .97 / .97 / .90 with the snippet.

**T5. Verified sampling** (k = 3, label-free):
- **Geometry:** 98.7 / 97.7 / 94.3 for 8B / 14B / 32B, equal to or better than one sample with hand-picked helpers (95.0 / 97.0 / 93.3).
- **Optimization:** best-of-3 on top of the snippet reaches 1.00 at 14B and 32B.
- **Where it fails:** it adds almost nothing when every sample shares the same API misconception (8B TSP, 0 in all samples).

![T5: verified sampling](figs/fig6_verified_sampling.png)

**Fallback when a broad toolbox can't be trimmed** (8 plausible extra helpers, n = 300):

| model | one sample | 3 samples + check | thinking | needed helpers only (one sample) |
|---|---|---|---|---|
| Qwen3-8B | 77.1 | 81.3 | 97.0 | 95.0 |
| Qwen3-14B | 71.0 | 84.3 | 99.0 | 97.0 |
| Qwen3-32B | 75.0 | 84.0 | 97.0 | 93.3 |

Sampling recovers only part of the loss, because every sample over-engineers the same way, so the errors are systematic. Thinking recovers all of it, at 5–10× the tokens. Order of preference: trim irrelevant tools ≳ think ≫ sample-and-check under a broad toolbox.

![Fixes under a broad toolbox](figs/fig8_fixes_under_distractors.png)

Sampling and stated facts are therefore complementary:
- sampling fixes *independent* errors (geometry degenerate cases);
- stated facts fix *systematic* errors (API misconceptions).

**T6. Thinking mode** (with the helpers and documentation fixed as in T4/T5; see T2 for thinking under distractors).
- Roughly neutral for geometry (±3 points). The remaining errors are degenerate-case bugs.
- For optimization it is the only lever that breaks 8B's TSP floor (0 → .58).
- On the held-out problems it fixes bin packing: with the snippet, 8B goes .17 → .87 and 14B .48 → .96 (overall .58 → .94 and .74 → .98).
- The snippet still matters under thinking at 8B (.94 vs .71 with the full sheet).
- Thinking is therefore the lever for *systematic* errors in small models. Verified sampling handles *independent* errors more cheaply.

**T7. Harder, realistic geometry tasks** (added for review item 3; no thinking, 60 programs per task, correct on all 8 variants):
- `lattice` (count integer points strictly inside a polygon; Pick's theorem or a boundary-aware brute force) and `rectunion` (area of a union of rectangles; sweep line). Both are hard without thinking: 8B/14B score 1–12 of 60, 32B 22–44.
- **A correct but signed helper is a trap.** The needed helper `polygon_area2` returns the *signed* area. Given it, models use it without `abs`, and Pick's formula then fails on clockwise inputs. 32B drops from 44 to 9 of 60; every transform-only failure is this bug.
- **A "distractor" can be the best tool.** Among the 8 extras, `point_in_polygon` labels boundary points exactly. Most programs switch to a brute-force count with it, and accuracy jumps (8B 2 → 47, 14B 1 → 37–46). Whether a helper is irrelevant depends on the task: it is harmful when it pulls the model off an idiom it knows, and helpful when it supplies a primitive the model would get wrong.
- On `rectunion`, where no helper helps, the harm reappears at 32B (22–29 → 7–12).
- Verified sampling (3 samples + metamorphic check) still helps: 32B 62–72 → 96 of 120. At low accuracy the check mostly abstains instead of picking a wrong program.
- **Causal test of the trap:** making the helper return the absolute value restores 32B to 46–49 of 60 (8B 2 → 15). A docstring warning ("negative for clockwise; use abs()") is not enough at 32B (17–19): the model abandons the "tricky" helper for a buggy brute force. Fix the contract in the tool rather than documenting the hazard.
- **Thinking solves both hard tasks** (8B/14B/32B: 56–60 of 60, vs 1–44 without thinking), also with the 8 extra helpers (≤ 3 lost), at about 8k tokens per program.
- **Polygon clipping (exact rational intersection area), the hardest task:** non-reasoning Qwen/Llama solve 0–2 of 180 programs in any condition; gpt-oss-20b at low effort solves 14 of 60, and the fixes compose: + a one-sentence hint 44, + hint + 3 samples with the label-free metamorphic check **59 of 60** at ≈2.8k tokens in total (the check never picked a wrong program). The dominant bug is assuming counter-clockwise input, which the hint names and the check detects.
- **Reasoning across families:** DeepSeek-R1-Distill-Llama-70B solves both hard tasks without help (57 and 54 of 60), where Llama-3.3-70B scores 0–1. But with the toolbox it falls into the signed-area trap (lattice 57 → 42; all 16 orientation failures are the missing `abs`): reasoning protects against unneeded helpers, not reliably against a needed helper with a hidden contract. Qwen3 with thinking mostly handles it (32B 59 vs 59 of 60 signed vs unsigned; 8B 52 vs 60); the unsigned helper removes it for every model.
- **Another family:** Llama-3.3-70B, robust on the easy tasks (−0.8), scores 0–1 of 60 on both hard tasks without help, and jumps to 45–46 on `lattice` when the boundary-exact `point_in_polygon` is among the extras. Capability on easy tasks does not imply robustness or skill on harder ones.

**T8. Does retrieval (RAG) or a text hint fix it?**
- **Optimization, BM25 retrieval over a titled snippet library:** top-1 retrieval matches the hand-written snippet (32B .97 vs .96; Llama-70B .85 vs .87; 8B .68 vs .67). Retrieving 3 chunks adds near-misses and costs up to 26 points on single problems (32B bin packing .93 → .67, CVRP .83 → .57). Even a weak, code-only retriever beats no documentation (8B .21 → .61, 32B .67 → .90).
- **Geometry, a one-sentence algorithm hint instead of helper code:** Pick's theorem takes the lattice count to 55–59 of 60 (Llama-70B 0 → 55). Naming "Andrew's monotone chain" next to the harmful helpers brings Qwen 8B/32B hull from 4/3 back to 58/52 of 60 (3 seeds: 7 → 94 and 5 → 88%, +83 to +87 points), and `polar_sort` is no longer called. That is causal evidence that the helpers hurt by changing the algorithm choice. Llama-70B keeps following the helpers (28 → 33).
- **Non-oracle hints:** letting the model name its own algorithm first helps only when it knows the right one (Qwen names Pick's theorem: lattice 8B 12 → 44, 32B 44 → 55; Llama-70B doesn't: 0 → 0). It can also lock in the fragile choice (32B plans a Graham scan for hull, so `polar_sort` keeps hurting). A *wrong* retrieved hint is destructive (BM25 retrieves "ray casting" for lattice: 32B 44 → 3), while a correct retrieved one matches the hand-written hint (rectunion 8B 8 → 38). Retrieval quality decides the sign.

### 4.3 Extension: LLM efficiency × CG/CO (pilot running)

The user-suggested combination with LLM efficiency fits the findings directly. Our fixes trade compute (samples, thinking tokens) or precision for correctness, so the natural question is **where to spend a fixed inference budget**:

| ID | Question | Design (pilot) |
|---|---|---|
| X1 | **Compute-optimal fixes:** at equal tokens, is it better to sample k programs + check, think with a budget B, or use a bigger model? | **Pilot (8B, 8 extra helpers, token-accounted):** budgeted thinking dominates best-of-k at equal tokens (≈1.6k tokens: 87 vs 81; ≈2.5k: ≳90 vs 84; full thinking 97 at 5.8k). With systematic errors, extra samples repeat the mistake. **On clean prompts the order flips:** MR best-of-3 = 100 at ≈0.9k tokens vs full thinking 91 at 5.5k (budget 256/1024: 88/87). Rule: independent errors → sample + check; systematic, prompt-induced errors → reasoning. **Optimization agrees:** 8B (systematic API misconceptions) best-of-3 .72 vs thinking .87; 14B/32B best-of-3 reaches 1.00/.99 at ≈⅓ of thinking's tokens. But optimization needs far more thinking than geometry: with budgets of 256/1k/2k tokens, TSP stays at 0 and bin packing reaches only .11/.37/.59 (full thinking .87 at ≈6k). Hard geometry (T7) behaves like easy geometry: ≈1k thinking tokens take 8B/14B from 1–12 to 58 of 60 on the lattice count, beating best-of-3 sampling at equal tokens (97 vs 44 of 120). A natively reasoning model moves the whole frontier: gpt-oss-20b at low effort reaches ≈99% at ≈0.4–0.9k tokens (helpers or not), while high effort runs away (27% of programs exceed 24k tokens). |
| X2 | **Does low precision break algorithmic code more than perplexity suggests?** | **Pilot:** fp8 weights match bf16 everywhere (geometry 272 vs 272, with distractors 227 vs 228, optimization .714 vs .702, held-out optimization with thinking .935 vs .935). fp8 KV cache isn't runnable in this vLLM build. Next: 4-bit/3-bit weights (AWQ/GPTQ, e.g. with the team's quantization tooling) and KV quantization via a HF-transformers path. |
| X3 | **Small model + verifier vs large model:** cost per correct solution | Qwen3-1.7B/8B with sampling + a label-free check vs 32B single-shot, accounting for tokens and memory. |
| X4 | **Robustness under compression:** does quantization make models *more* sensitive to plausible distractors (lower "capability" → larger harm, Section 4.2 T2)? | Dose-response (K = 0/8) at fp8 / 4-bit vs bf16. |

### 4.4 Planned experiments (team work for the full project)

| ID | Experiment | Purpose |
|---|---|---|
| E1 | Replicate T1–T5 on more model families. Pilot on Llama-3.3-70B: the optimization snippet replicates strongly (held-out bin packing .96 vs .07 with the full sheet) and so does verified sampling, but the **geometry distractor harm is absent** (−0.8 [−3.8, +2.1] over 900 paired programs). Llama-3.1-8B shows the largest harm (−39.3), so the effect tracks capability, not family. Next: a capability curve with more sizes (and Mistral/Gemma after an environment fix, plus one closed API model) **Third family (OpenAI gpt-oss 20b/120b, natively reasoning):** robust to the 8 extra helpers at every effort level and both sizes (20b and 120b: −1.0 to +0.7 points over 2 seeds, after fixing a code-extraction bug that had made 120b look hurt; ≈430–880 tokens per program at low effort), solves the hard tasks (56–60 of 60) and avoids the signed-area trap; it knows OR-Tools well without docs (.93–1.00), and the snippet still lifts it to 1.00 (CVRP .67–.87 → .93–1.00). | Which parts of the recipe are universal, and where does robustness to irrelevant tools emerge? |
| E2 | Expand held-out tasks designed *after* the findings. Pilot `overlap` (do two convex polygons intersect; touching counts) replicates every geometry claim: encapsulating predicates 8B 58 → 100 and 32B 47 → 100; verified sampling with the metamorphic filter above voting; distractor harm (32B −15.0); thinking 100% with 8 extras. Next: 2–3 more geometry tasks and 2 more optimization problems (bin packing and vertex cover were already replicated, Section 4.2) | Is the result a generalization or overfitting to our task suite? |
| E3 | Automatic tool scoping. Pilot: model self-selection recovers about half of the gap; naive lexical retrieval finds the encapsulating predicate when the task name matches it (point-in-polygon 20/20) but one wrong pick wrecks a task (hull 1–2/20). So precision is the bottleneck. Compare embedding retrieval with abstention, and metamorphic-check selection over candidate toolsets | A deployable alternative to hand-picked tools |
| E4 | Mechanism analysis: which helper tokens are copied or attended to; does harm correlate with helper–task semantic similarity? | Explain *why* plausible helpers hurt geometry but not optimization |
| E5 (stretch) | LoRA-finetune a small model (Qwen3-1.7B/8B) on distractor-laden prompts with verified solutions | Can robustness to irrelevant tools be *learned*? **Pilot done:** self-distillation from the thinking model (600 verified programs, LoRA r=16) brings no-think 8B under 8 extra helpers from 76.0 to **97.7** (+21.7 [+17, +26]), thinking-level accuracy at ≈350 tokens instead of ≈6k; a clean-prompt LoRA of equal size gains nothing (−0.7), so distractor-laden prompts are required. But it does not transfer: on held-out tasks K8 58.6 → 52.2 (2 seeds, −6.4 [−12.2, −0.6]), and leave-one-task-out LoRAs barely help the unseen task under K8 (pooled 77.0 → 80.8) while sometimes **damaging it on clean prompts** (hull 97 → 34: the model drifts off the monotone chain to Graham scans and ad hoc loops). Robustness is learned per task, and narrow fine-tuning can cost accuracy elsewhere. Training on 9 tasks instead of 4 does not fix this (unseen hull 97 → 28 on clean prompts; convex K8 68 → 34). Within the trained tasks, the gain survives unseen prompt formats (neutral header +19, 10 helpers +21, pre-defined helpers +18). Lighter training removes the damage but also the gain (r=4: hull intact, in-task 81 vs 91 base); no setting gave one without the other. |

**Expected contributions.**
1. A controlled measurement of in-context distractor effects on algorithmic code, with a dose-response, a delivery-mode control, and a domain contrast.
2. A practical, task-agnostic recipe with evidence for when each part applies: state environment and API facts → keep the tool surface minimal → sample about 3 programs and select with a label-free check. Where tools can't be trimmed, reasoning mode makes even small models (Qwen3 1.7B–32B) nearly immune to plausible but irrelevant helpers.
3. A methodology lesson: several apparent "capability" gaps in our own pilot turned out to be harness confounds. These were a missing library, sandbox thread limits, repair-feedback wording, and a server port clash.

**Risks and mitigations.**
- *Effects specific to Qwen.* Mitigated by E1 (pilot Llama checks already agree once the environment fact is stated).
- *Small task suites.* Mitigated by E2 and by n = 300 programs per condition.
- *"Prompt engineering" criticism.* Mitigated by framing around controlled variables (dose, delivery mode, domain) and mechanism (E4) rather than a single best prompt.
- *Compute contention on shared GPUs.* Mitigated by small, resumable runs (each ≤ 1 hour).

## 5. Critical Review of the Pilot (constructive criticism)

Problems we see in our own pilot, ordered by how much they could change a conclusion. Each comes with a planned fix.

| # | Concern | Why it matters | What we checked already | Fix for the full project |
|---|---|---|---|---|
| 1 | **Selection and evaluation share transforms.** The metamorphic check uses copies of the *same* instance that the 8-variant score also uses. | Verified sampling could look better than it is. | **Resolved:** the chosen program scored on 5 *fresh* instances × 8 variants (never seen by the check) reaches 98.2 / 97.7 / 93.9 (8B / 14B / 32B) vs one sample 91.7 / 96.2 / 85.4 and task-matched predicates 95.0 / 97.0 / 93.7. No leakage. | Keep fresh-instance evaluation as the default metric for any selection method. |
| 2 | **The toolbox header says "should use".** | Part of the harm may come from obeying the instruction, not from the helpers. | **Resolved (corrected 06:40):** with a neutral header the raw drop looked larger (8B −12.7, 14B −18.3, 32B −29.0), but much of it was **copy failures**: the neutral header doesn't say "copy the helpers", so models call them undefined (NameError). Re-running every stored program with the offered helpers pre-defined (`poc/rescore_prelude.py`): **should-use** 8B −14.3, 14B −7.7, 32B −13.3; **neutral** 8B −11.7, 14B −0.3, 32B −16.3. The semantic harm does not depend on the instruction for 8B/32B; 14B's is mostly packaging. | Use the neutral header with pre-defined helpers (prelude) as the default, so copy failures and semantic harm are separated. |
| 3 | **Small, synthetic task suites.** 5 + 3 geometry tasks (n ≤ 20 points), 4 + 2 optimization problems (≤ 80 items). | Effects may not transfer to realistic code. | **Partly resolved:** at 5× larger instances (50–100 points, 40–70-vertex polygons) every claim replicates: predicates 32B 82.5 → 99.5; verified sampling 93–99; plausible helpers −11 to −29. Held-out tasks designed after the findings also replicate. **T7:** two harder multi-step tasks (lattice count, rectangle union): the mechanism (helpers pick the algorithm) holds, but the sign is task-relative: an exact primitive the model lacks helps (8B 2 → 47), a needed helper with a subtle contract (signed area) hurts (32B 44 → 9). | Optimization side: capacitated vehicle routing (CVRP, exact references): the problem-specific snippet is decisive (14B .20 → .73–.80, 32B .23 → .77–.90; best-of-3 1.00), and an incomplete reference (TSP routing without capacities) is worse than none at 32B (.07 vs .23). **Added since:** polygon clipping (fixes compose: gpt-oss-20b 14 → 59 of 60 with hint + verified sampling; non-reasoning models 0–2 of 180) and VRP with time windows (only the exact snippet works: Llama-70B 0 → .60–.77, best-of-3 .93; the near-miss CVRP snippet and the full sheet give 0). Still open: Delaunay check. |
| 4 | **Many cells are single-seed with n = 60–100.** | Wide CIs (e.g. overlap 14B Δ −8.3 [−23.3, +6.7]); per-task numbers swing ±10 pts. | Headline effects were replicated with 2–3 seeds and n = 300 (geometry) / 252 (optimization) with paired CIs. | Pre-register the main contrasts; run ≥ 3 seeds everywhere; cluster bootstrap over instances *and* seeds; correct for multiple comparisons. |
| 5 | **Narrow model coverage, mostly quantized.** Qwen3 (1.7B–32B-AWQ), Llama 8B/70B-w4a16, R1-Distill-70B-w4a16, Qwen2.5-72B; no closed models. | Quantization or family idiosyncrasies (14B's header sensitivity) could drive some effects. | The capability pattern holds across families (Llama-8B −39, Llama-70B −1). | Add full-precision runs for at least one size, Mistral/Gemma (after the flash_attn fix) and one closed API model. |
| 6 | **Prompt sensitivity.** Qwen3-14B swings 84 ↔ 98 with header wording and misuses helper signatures. | Results may partly reflect one prompt template. | An API-contract sentence fixes the signature misuse (16 → 55/60 segs). **Resolved:** 3 instruction templates × neutral header, n=300, scored with helpers pre-defined (copy failures removed): 8B −35 / −59 / −52 and 32B −49 / −62 / −69 of 300 across the 3 templates; 14B −1 / −2 / +11 (its raw drop was copy failures). Templates also shift the clean baseline (14B 240 vs 222). | Report the spread over templates for every headline cell. |
| 7 | **Harness confounds were frequent.** Missing library, sandbox thread crashes, a port clash, repair-feedback wording, a broken pipeline-parallel server. | More may remain undetected. | Each was found because a number looked anomalous, then fixed and re-run. **Partly resolved:** `poc/sanity_check.py` pushes a reference solution through every geometry harness (480/480 on all 10 tasks; 0 metamorphic false alarms). It found one more defect: most "simple" polygons in area2/pip/convex self-intersect. Labels are rule-independent there (pip even-odd = winding on 960/960 queries; convex labels them "no"; area2 = shoelace), so the numbers stand, but the prompt claim is false. | Add automatic checks: re-run a fixed reference solution through every harness; log import errors and timeouts as separate classes; pin library versions. |
| 8 | **The mechanism story is partly post hoc.** "Off-idiom drift" was formed after seeing the data. | Risk of fitting a narrative. | Supported by four independent measurements: program structure, the algorithm switch, logit shifts, and thinking traces. | Pre-register E4 predictions (e.g. harm grows with helper–task similarity) and test them on new tasks. **Done (docs/prereg/PREREG_E4.md):** the core prediction held on hull (an algorithm-naming helper: 97 → 8 / 83 → 6, HIGH−LOW −50 points), but 2 of 4 predictions failed: "non-suggestive" helpers also hurt 32B by 15–27 points (via dependencies), and area2 reversed. Mechanism confirmed, a priori similarity labels not predictive. |
| 9 | **Logit probe limits.** It scores 3 handwritten programs, and the whole-program score includes copying helper text. | Magnitudes overstate the "preference"; teacher forcing differs from sampling. | The shift localizes to the program prefix; the algorithm-part scores barely move. | Score many sampled programs, measure decision-point entropy over the first tokens, and use length-normalised scores. **Done (logit probe v2, 180 sampled programs × 3 models):** per-token preference shift +0.40 to +0.71 nats, positive in 100% of instances and shrinking with size; it sits in the first 10% of tokens (imports such as `functools`, helper names), copied helper text is separated out, and the toolbox makes the helper route *more* certain (lower entropy). |
| 10 | **The "fixes" are partly oracle.** "Keep only the needed tools" assumes we know them; the snippet is hand-written per problem. | Not deployable as-is. | Self-scoping recovers about half; lexical retrieval is all or nothing; thinking (≈1–4k tokens) needs no oracle. | E3: a precision-first selector (abstain unless confident), or retrieval plus a verification gate. |
| 11 | **Novelty framing.** "Irrelevant context hurts" is known (GSM-IC, tool overload). | Reviewers may see incremental prompt engineering. | Our new angles: code-level helpers, harm without use, a domain contrast (CO immune), capability/reasoning gating. | Lead with the mechanism and the geometry-vs-optimization contrast, not the accuracy table. |
| 12 | **Thinking comparisons mix cost and capability.** Thinking uses far more tokens and a different decoding path. | "Thinking fixes it" might be "more compute fixes it". | Budget forcing shows about 1k thinking tokens suffice. **Resolved (X1):** at equal tokens, under distractors thinking beats best-of-k (87 vs 81 at ≈1.6k); on clean prompts best-of-3 beats thinking (100 at 0.9k vs 91 at 5.5k). Same in optimization: 8B systematic errors → thinking (.87 vs best-of-3 .72); 14B/32B → best-of-k at ⅓ the tokens. | Compare against token-matched non-thinking baselines (e.g. best-of-k at equal tokens). |
| 13 | **Scope drift.** Pilots also covered logic puzzles, Mastermind and tutoring hints. | Dilutes the course project. | Main text is now geometry + optimization; logic puzzles are an optional extension. | Keep the write-up to CG + CO; move everything else to an appendix or drop it. |

**Overall assessment.** The core findings are well supported for the models tested:
- the environment fact;
- the harm from plausible helpers, its mechanism, and the capability/reasoning gate;
- the problem-specific snippet in optimization;
- verified sampling on clean prompts.

The weakest points are (1) the evaluation–selection overlap for verified sampling, (3) the toy scale of the tasks, and (10) the oracle nature of the best fix. These are where the team's full project should put its effort.

## Appendix A. Code, Data, and Status

### A.1 Folder layout

- `figs/`: the six proposal figures, regenerated by `/opt/conda/bin/python poc/make_figures.py` (numbers from `docs/FINDINGS.md`; the CO distractor CIs are recomputed from `results/co_D_*`).
- `poc/`: all pilot code.
  - **Geometry:** `run_geo.py` defines the tasks, the 8 variants and the exact oracles. `run_geo_cross.py` runs code-mode experiments, with flags:
    - `--stdlib`: environment fact;
    - `--primitives --prims_task`: needed predicates;
    - `--distract K --distract_kind --tb_head {should,may,prelude} --tb_usage`: distractors, header wording, delivery mode, API contract;
    - `--autoscope`: model picks its own helpers;
    - `--temperature --seed --n_inst --think`.

    Also: `geo_distractors.py` (helper pools), `mr_select.py` (metamorphic-consistency selection), `mr_kcurve.py`.
  - **Optimization:** `run_co.py` has the problems, references, greedy baselines and prompts, with flags:
    - `--api_doc`: full cheat sheet;
    - `--api_doc_task`: problem-specific snippet;
    - `--doc_extra K`, `--doc_others`: distractor documentation;
    - `--shim`: tolerant OR-Tools layer from `api_shim.py`;
    - `--probs binpack,vcover`: held-out problems;
    - `--repair --temperature --seed --n_inst --think`.

    Also: `run_co_meta.py` (metamorphic invariance for optimization).
  - **Logic puzzles (optional):** `run_zebra.py` (`--api_doc --doc_status --doc_extra`).
  - **Analysis:** `analyze_final_geo.py`, `analyze_final_co.py`, `analyze_final_zebra.py`, `analyze_xfam.py`, `analyze_distract.py`.
  - **Infrastructure:**
    - `serve_gpu.sh`, `start_server.sh` and `start_server_retry.sh`: vLLM on a chosen GPU and port, with a port guard;
    - `pick_gpu.sh`: picks a GPU;
    - `sandbox.py`: runs programs under resource limits;
    - `llm.py`: OpenAI-compatible client.
  - `queue_*.sh` scripts: exact records of each experiment batch, kept for reproducibility.
- `results/`:
  - `FINDINGS.md`: the master log;
  - final result files: `geocross_F_*`, `co_F_*`, `zebra_F_*`, held-out `co_H_*`, distractor `co_D_*`, thinking `*_T_*`, cross-family `*_X_*`;
  - `co_refs.json`: optimization references;
  - `zebra_puzzles.json`: puzzle cache.

### A.2 How to run (on this server)

```bash
cd /NAS/SJ/POSTECH/nlp
P=/root/venvs/llm_algo_poc/bin/python            # venv with openai, numpy, ortools
S=$(poc/start_server_retry.sh /SSD/huggingface/Qwen/Qwen3-8B 8044 my_tag 9>&-)   # vLLM server (ports 8040-8099 for this project)
export POC_BASE_URL=http://127.0.0.1:8044/v1
$P poc/run_geo_cross.py --model_tag demo --stdlib --n_inst 10          # geometry, no helpers
$P poc/run_co.py --model_tag demo --arms solver --api_doc_task --repair 2
kill $S
```

**Environment notes:**
- vLLM 0.10.2 lives in `/dev/shm/pylib_vllm`.
- Models are in `/SSD/huggingface`.
- On this CIFS mount, never use `sed -i` or in-place editors; rewrite files with Python.
- `ss` isn't installed, so `start_server.sh` probes ports with curl.
- Another session uses ports 8100+.

### A.3 Optional constraint-satisfaction extension
Logic-grid ("zebra") puzzles, 144 instances. The problem-specific CP-SAT snippet plus the OPTIMAL-status line plus best-of-3 solves every puzzle at 14B/32B without thinking. Direct answers with thinking reach .90–.92. Translating to a solver needs ≥14B. Kept out of the main scope (CG + CO); code in `poc/run_zebra.py`.

### A.4 Caveats and status

- The earlier geometry runs lacked the standard-library line. The final tables use it. Earlier numbers at 14B/72B were partly a shapely artifact (corrected in FINDINGS.md).
- The 14B model is sensitive to toolbox header wording; report it per task.
- The Qwen2.5-72B run with the standard-library line never ran (a foreign job held a GPU). A pipeline-parallel attempt produced invalid output and is quarantined (`*_pp3_INVALID`).
- **Cross-family replication (Llama-3.3-70B, done):**
  - the optimization snippet ≫ full sheet (.87 vs .55);
  - verified sampling works (k = 3: 92.7, metamorphic filter +6.7 over voting);
  - **but** the geometry distractor harm is small and not significant (−4.0), so distractor sensitivity is model-dependent.
  - Granite-4.1-8B (base model without a chat template) and Gemma-3-27B (flash_attn build incompatible with vLLM) could not be run here.
- These are **pilot** results. For the course project, the team should understand the harness, re-run the final experiments, and carry out the planned extensions (E1–E5 in Section 4.4).

## Appendix B. Tool Inventory and Worked Examples

All examples below are real model outputs from the pilot runs. They are shortened, with `…` marking omitted lines.

### B.1 What is provided

**Geometry helper pool** (`poc/geo_distractors.py`). These are tested, exact helper functions pasted into the prompt for the model to copy into its program:

| Helper | What it does |
|---|---|
| `orient(a, b, c)` | sign of the cross product: left turn / right turn / collinear |
| `on_segment(a, b, p)` | point p lies on segment ab |
| `segments_intersect(a, b, c, d)` | closed segments ab and cd share a point |
| `point_in_polygon(poly, q)` | `'inside'` / `'outside'` / `'boundary'` (exact winding number) |
| `dist2(a, b)` | squared distance |
| `bbox(points)` | bounding box |
| `collinear(a, b, c)` | three points on one line |
| `polar_sort(points, o)` | sort by angle around o (exact, no atan2) |
| `is_convex(poly)` | polygon is convex |
| `polygon_area2(poly)` | twice the signed area |
| `convex_hull(points)` | hull vertices (monotone chain) |
| `closest_pair_sq(points)` | smallest squared pairwise distance |

**Per task.** The needed helpers are always given. Helpers that would solve the task outright are never offered. Distractors are drawn from the rest.

| Task | Needed (always given) | Never offered | Distractor pool |
|---|---|---|---|
| convex hull | `orient` | `convex_hull` | other 10 |
| polygon area ×2 | none | `polygon_area2` | other 11 |
| point in polygon | `orient`, `on_segment`, `point_in_polygon` | none | other 9 |
| segment intersections | `orient`, `on_segment`, `segments_intersect` | none | other 9 |
| closest pair | none | `closest_pair_sq` | other 11 |
| held-out: convexity / points in triangle / polygon overlap | `orient` / `orient` / all 4 predicates | `is_convex` / `point_in_polygon` / none | rest |

**Unrelated control.** `gcd`, `is_prime`, `fib`, `reverse_words`, `lower_bound`, `lcs_len`: correct and similar in length, but not geometry.

**Optimization documentation conditions** (`poc/run_co.py`):

| Condition | Content | Effect (8B / 14B / 32B, within 1%) |
|---|---|---|
| no doc | — | .26 / .61 / .70 |
| full cheat sheet | general CP-SAT + routing reference | .35 / .81 / .93 |
| **problem-specific snippet** | only the calls one problem needs | **.71 / .96 / .97** |
| snippet + 8 unneeded API lines | reified constraints, AddElement, automata, … | no change |
| snippet + the other problems' snippets | plausible but wrong patterns | no change |

Example problem-specific snippet (scheduling), shown here exactly as given in the prompt:

```text
OR-Tools CP-SAT (correct usage):
  from ortools.sat.python import cp_model
  m = cp_model.CpModel(); s = cp_model.CpSolver(); s.parameters.max_time_in_seconds = 20
  x = [[m.NewBoolVar(f"x{j}_{q}") for q in range(M)] for j in range(n)]; m.AddExactlyOne(x[j])  # per job
  load_q = sum(p[j] * x[j][q] for j in range(n)); z = m.NewIntVar(0, sum(p), "z"); m.Add(load_q <= z)  # per machine
  m.Minimize(z)
  st = s.Solve(m); if st in (cp_model.OPTIMAL, cp_model.FEASIBLE): read values with s.Value(v)
```

### B.2 Example prompt (convex hull, 8 extra helpers)

```text
Points: (20,-40) (-26,-18) (-18,-12) (-50,38) (-18,42) (58,16) (-30,-26) (6,58) (52,-36) (50,14)

How many vertices does the convex hull of these points have? Points lying on a hull edge (collinear)
are not vertices; duplicate points count once.

Do not compute the answer by hand. Write a Python 3 program that solves this problem for any input in the
following stdin format: first line n, then n lines `x y`. Print only the answer. … Only the Python standard
library is available (no third-party packages such as shapely or numpy).

You may (and should) use these tested helper functions; copy the ones you use into your program unchanged:
  on_segment, closest_pair_sq, point_in_polygon, polar_sort, bbox, is_convex,
  segments_intersect, dist2, orient, collinear        (full definitions shown in the prompt)
```

Only `orient` is needed. The other nine are distractors.

### B.3 Geometry examples

**(1) Needed helper only, correct** (Qwen3-8B, hull). The model writes the textbook monotone chain using `orient`:

```python
points = sorted(set(points))
lower = []
for p in points:
    while len(lower) >= 2 and orient(lower[-2], lower[-1], p) <= 0:
        lower.pop()
    lower.append(p)
# … same for the upper half …
return lower[:-1] + upper[:-1]
```

**(2) Over-engineering around a distractor plus a missing dependency** (Qwen3-32B, hull, prompt B.2). The model switches to a Graham scan built on the offered `polar_sort`, with the wrong turn test in its pop condition (it keeps clockwise turns). It also copies `polar_sort` without the `dist2` it depends on, so it crashes on every variant:

```python
def polar_sort(points, o):             # copied from the toolbox
    …  return -1 if c > 0 else (1 if c < 0 else dist2(o, p) - dist2(o, q))   # dist2 never copied -> NameError
def convex_hull(points):
    leftmost = min(points, key=lambda p: (p[0], p[1]))
    sorted_points = polar_sort(points, leftmost)
    …  while len(hull) > 1 and not (orient(hull[-2], hull[-1], p) < 0 or on_segment(hull[-2], hull[-1], p)):
            hull.pop()
```

**(3) A plausible helper changes the algorithm** (Llama-3.1-8B, polygon area, 8 extras). Offered `convex_hull`, the model computes the area of the polygon's *convex hull* instead of the polygon itself. The result is wrong for every non-convex polygon, so it fails all 8 variants:

```python
hull = convex_hull(points)        # the polygon is simple but not convex
area = polygon_area(hull)
print(2 * area)
```

**(4) Misusing a needed helper's signature** (Qwen3-14B, segment intersections, no extras). It passes 8 numbers instead of 4 points and crashes with `TypeError: segments_intersect() takes 4 positional arguments but 8 were given`:

```python
if segments_intersect(a[0], a[1], b[0], b[1], c[0], c[1], d[0], d[1]):
    count += 1
```

*Fix:* one API-contract sentence ("every point argument is ONE (x, y) tuple", plus example calls) raises 14B segment intersection from 16 to 55 of 60.

**(5) One retrieved distractor is enough** (word-matching selection). For hull, the name match retrieves `collinear` as the single helper. The models then add elaborate collinear-point handling and drop real vertices, scoring 1–2 of 20, while point-in-polygon, where retrieval finds `point_in_polygon`, scores 20 of 20.

**(6) A low-level primitive alone can mislead.**
- Llama-3.1-8B with only `orient` abandons the monotone chain for a hand-written gift-wrapping loop that never terminates (17 timeouts in 60 hull programs).
- Qwen3-32B on the held-out triangle task tests `orient(a,b,p) > 0 and orient(b,c,p) > 0 and orient(c,a,p) > 0`. That assumes a counter-clockwise triangle and fails the mirrored variant.

**(7) The same distractors with thinking.** With the same 8 extra helpers, Qwen3-14B with thinking gets 39 of 40 hull programs right; without thinking it gets 28 of 60.

| Hull programs | `polar_sort` used | `collinear` used | monotone-chain structure |
|---|---|---|---|
| with thinking | 3 of 40 (8%) | 10 of 40 (25%) | 37 of 40 |
| without thinking | 27 of 60 (45%) | 35 of 60 (58%) | 30 of 60 |

Reasoning keeps the model on its well-practised algorithm.

### B.4 Why do plausible extra helpers hurt? (mechanism analysis)

Each candidate explanation was tested with a control experiment. Data: geometry, Qwen3 8B/14B/32B unless noted.

| Hypothesis | Test | Result | Verdict |
|---|---|---|---|
| **Longer prompt / attention dilution** | 6 *unrelated* helpers of similar length (gcd, fib, …) | −4 to −7 pts, almost never called (≤1%) vs −17 to −29 for related helpers | ❌ not the main cause |
| **Packaging**: the model calls a helper but forgets to copy it in | helpers pre-defined at execution, so copy failures are impossible | harm unchanged at 8B (−12.3) and 32B (−15.0); only 14B's harm disappears | ❌ minor (only 14B) |
| **Explicit use**: the model calls a helper where it doesn't belong | count calls in failing vs passing programs (2,700 programs) | related helpers called by 36–81% of programs. Hull: `collinear` in 64% of failing vs 42% of passing; closest pair: `orient` 46% vs 25%, `collinear` 42% vs 16%, `on_segment` 34% vs 19% | ✅ part of it |
| **Priming without use**: seeing degenerate-case helpers makes the model over-handle degenerate cases | a "most are probably NOT needed" header | helper use drops 40–65%, accuracy recovers only 0–5 pts; 22 of 33 failing 8B programs call *no* extra helper but still add spurious "remove collinear points" passes | ✅ a large part |
| **One especially bad helper** | accuracy with vs without each helper present, per model × task | every single helper's effect is small (−3.3 to +2.7 pts); no one helper explains the loss | ❌ it's the *set*, though one retrieved `collinear` alone wrecks hull (1–2/20) |
| **Logit-level preference shift** | teacher-forced log-prob of fixed programs (monotone chain vs Graham/polar-sort vs collinear pass) under 0 vs 8 helpers | with 8 helpers the helper-based programs gain 130–230 nats (Graham) and 40–90 nats (collinear pass) relative to the monotone chain; the "not needed" header moves them back only 7–10 nats; the shift sits in the program *prefix* (choosing to copy/use helpers), not in the algorithm continuation | ✅ helpers change the model's prior over solution routes |
| **Program structure** | code length, branches, special-case code, algorithm family of 3,000+ stored programs | 8 helpers: 1.4–2.6× longer code, 1.7–3.5× more branches, 2–3.7× more special cases; hull switches from monotone chain (100%) to Graham scan (44–75%); failing programs are the most special-cased | ✅ over-engineering is measurable |
| **Off-idiom drift**: helpers pull the model away from the algorithm it knows well | algorithm structure of hull programs | with thinking: 37/40 keep the monotone chain and 8% use `polar_sort`; without: 30/60 and 45%, and the polar-sort Graham scans are where the bugs are | ✅ the core mechanism |
| **Capability / reasoning gate** | other models and thinking mode | Llama-70B −0.8, R1-Distill-70B 0.0, Qwen3 with thinking −0.5 to −4.3; Qwen3-1.7B −35.7, Llama-8B −39.3 | ✅ weaker, non-reasoning generation is affected |
| **Domain**: is it any extra documentation? | optimization: + 8 unneeded OR-Tools lines or other problems' snippets | no measurable change | geometry-specific: functions to *embed*, not API text to read |

**Synthesis.** An offered helper acts as a hint about *how* to solve the task. `polar_sort` suggests a Graham scan, `collinear`/`on_segment` suggest explicit collinear handling, `convex_hull` suggests "compute the hull first". The prompt says the helpers should be used, and standard (non-reasoning) generation follows those hints. It leaves the well-practised algorithm (monotone chain, shoelace, all-pairs scan) for less-practised code, where it makes the actual errors: wrong turn tests, wrong decomposition (hull area instead of polygon area), helpers copied without their dependencies, misapplied validity checks.

This is the same failure as two earlier observations:
- the "be robust, handle degenerate cases" instruction *lowered* accuracy (8B 96 → 84, 32B 89 → 73);
- 10^9 coordinates pushed point-in-polygon programs off float ray-casting into buggy integer logic.

Reasoning lets the model first judge which helpers are relevant, so it keeps its idiom. Larger models (Llama-70B) seem to do this implicitly. In optimization the model writes a standard formulation it knows well and ignores extra text.

**Not yet analyzed (E4):**
- attention or token-level evidence of where the helpers are copied from;
- whether harm scales with a helper's semantic similarity to the task (lower K dose levels give more presence/absence contrast than K=8, where most helpers are present).

### B.5 Optimization examples: misconceptions that only a stated fact fixes

| Misconception (real model code) | Effect | One-sentence fix stated in the prompt | Result |
|---|---|---|---|
| `if status != cp_model.FEASIBLE: print("No solution found")`. A solved model returns OPTIMAL, so correct models print "no solution" (14B, logic-grid puzzles) | 3x3 puzzles 0/8 | "a solved model returns OPTIMAL; test `st in (OPTIMAL, FEASIBLE)`" | 14B .60 → .96 |
| `routing.SetArcCostEvaluatorOfAllVehicles(transit_callback)`, passing the function instead of the registered index (8B TSP) | crash every time | the routing recipe in the snippet; thinking | TSP 0 → .58 (thinking) |
| `model.Add(makespan >= load[q] for q in range(m))`, passing a generator to `Add` (8B/32B scheduling) | TypeError | the snippet's per-machine pattern (or the `api_shim.py` tolerance layer) | 8B scheduling 0 → 1.00 (snippet) |
| `CpModel.Not(...)`, boolean use of a linear expression (held-out bin packing, 14B) | crash / wrong model | the bin-packing snippet; thinking | bin packing with snippet + thinking: 8B .17 → .87, 14B .48 → .96 |

## Appendix C. More Examples: Problems, Solutions, and Diagnostics

### C.1 Environment problem → fact fix (Llama-3.1-8B, point in polygon)

*Problem.* Without the stdlib sentence, the model imports a library that isn't installed, and calls a method that doesn't exist even in that library:

```python
from shapely.geometry import Polygon
...
polygon = Polygon(vertices)
point = polygon.point_on_path(qx, qy)     # ModuleNotFoundError (and no such method)
```

*Solution.* Add one sentence: "Only the Python standard library is available". Llama-3.1-8B greedy goes from 83 to 99. Its programs become plain ray casting or winding number.

### C.2 Off-idiom problem: floats at 10^9 (Qwen3-8B, polygon area)

*Problem.* The program parses integers as floats. The shoelace sum then loses precision on the 10^9-offset variant only (base answer 920, wrong on `big`):

```python
x = float(x_str); y = float(y_str)          # integers read as floats
area += (x1 * y2) - (x2 * y1)               # products ~1e18 exceed float precision
print(int(2 * area))
```

*Solution.* Either an exact-integer instruction, or **verified sampling**. The metamorphic check flags this program as inconsistent on `big`, and the other two samples (integer arithmetic) agree, so the selector returns a correct program.

### C.3 Verified sampling, a success and a limitation (Qwen3-32B, point in polygon)

Three samples for the same instance. Outputs on the 8 variants (truth: `yes` everywhere except `degen` = `no`):

| sample | identity | translate | rot90 | mirror | permute | scale | big | degen | metamorphic check |
|---|---|---|---|---|---|---|---|---|---|
| 1 (float ray casting with an epsilon) | yes | yes | **no** | **no** | yes | yes | yes | no | ❌ rejected (inconsistent) |
| 2 | **no** | **no** | **no** | **no** | **no** | **no** | **no** | **yes** | ✅ consistent, but wrong everywhere |
| 3 | yes | yes | yes | yes | yes | yes | yes | no | ✅ consistent and correct |

- **Success:** sample 1's rotation and mirroring bugs are caught without any label.
- **Limitation:** sample 2 is *invariant but wrong*, so the check can't see its error. With 2 consistent candidates that disagree, the vote is a tie. More samples, or a second check (e.g. a brute-force reference on tiny inputs), are needed. This is why the metamorphic filter adds less once crash-type errors are gone (Section 4.2, T5).

### C.4 Optimization: the full cheat sheet drops the objective; the snippet restores it (Qwen3-8B, graph colouring)

With the full cheat sheet, the program is a pure feasibility model. It uses 6 colours where the optimum is 4:

```python
colors = [model.NewIntVar(0, n-1, f'color_{i}') for i in range(n)]
model.Add(colors[a] != colors[b])            # per edge
status = solver.Solve(model)                 # no objective: any proper colouring is accepted
```

With the problem-specific snippet, the program minimizes the largest colour and reaches the optimum (4):

```python
max_color = model.NewIntVar(0, n - 1, 'max_color')
model.AddMaxEquality(max_color, colors)
model.Minimize(max_color)
```

### C.5 Thinking trace with 8 extra helpers (Qwen3-32B, hull; the prompt of B.2)

Excerpt of the model's reasoning before it writes code. The full trace is in `results/example_thinking_32b_hull_k8.txt`:

> "First, I remember that the convex hull can be computed using algorithms like Graham's scan, Andrew's monotone chain algorithm, or Jarvis's march. … Looking at the helper functions provided, there's a polar_sort function which sorts points around a given origin. Also, there's the orient function … These might be useful … Let me think about Andrew's monotone chain algorithm … during this process, colinear points that are in the middle of the line are removed … So maybe the standard convex hull algorithm already takes care of that … `if … cross(lower[-2], lower[-1], p) <= 0: lower.pop()` … if cross is 0, then the three points are colinear. In that case, the condition is true (<=0), so the previous point is removed."

The model notices the distractor (`polar_sort`), weighs the alternatives, then **chooses the algorithm it knows well** and reasons explicitly about why `<= 0` already handles collinear points. Without thinking, that step is skipped: 45% of 32B hull programs go straight to the polar-sort scan, and over-handle collinear points (Appendix B.3–B.4).

### C.6 One wrong helper is enough (selection example)

For convex hull, lexical retrieval scores helpers by word overlap with the task text ("…points lying on a hull edge (**collinear**)…") and returns `collinear` as the single helper. The resulting programs add a dedicated collinear-removal pass and drop real vertices: 1–2 of 20 correct. For point in polygon, the same retriever returns `point_in_polygon` and scores 20 of 20.
