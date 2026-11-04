# Tools, Facts, and Checks: When LLM-Written Geometry and Optimization Code Fails, and Which Fix to Use

*Graduate NLP course project proposal: computational geometry and combinatorial optimization*

> **About this file.** The single project document: proposal (Sections 1–4), limitations (Section 5), how to run (Appendix A), and worked examples (Appendix B). Only the results that matter for the project are kept here. The complete chronological log, including every control, harness check and correction, is [docs/FINDINGS.md](docs/FINDINGS.md); the previous long version of this file is archived in `results/archive/`.

## 1. Problem Statement

LLMs are routinely asked to solve algorithmic problems by writing programs: a convex hull, a point-in-polygon test, a solver model for TSP or vehicle routing. The programs often look right and still fail, and the common reflex is to add more to the prompt: more helper functions, more documentation, more reasoning tokens.

**Research question.** Which in-context additions make LLM-written programs for computational geometry (CG) and combinatorial optimization (CO) better or worse, why, and which cheap fix should be used for which failure, at what token cost?

1. **Tools.** Do correct but unneeded helper functions change the generated code? Through what mechanism? Can a *needed* tool also hurt?
2. **Facts.** For solver code, does stating the exact API usage beat a full manual, retrieval, or more reasoning?
3. **Fix selection.** When should one sample several programs and check them without labels, and when should one pay for reasoning? Can the robustness of a reasoning model be distilled into a fast model?

### 1.1 Why LLMs solve algorithmic problems by writing programs

An LLM can also answer directly ("the hull has 7 vertices", "visit the cities in this order"). In our pilot this fails badly, for structural reasons:

| Approach (no thinking) | Geometry: correct on all 8 versions | Geometry: same answer on equivalent inputs | Optimization: solved optimally |
|---|---|---|---|
| Direct answer (Qwen3-8B / 32B) | 22% / 23% | **0%** of instances | held-out problems: .06–.19 (Llama-70B .02) |
| Program, executed (Qwen3-8B) | **92–97%** | 50–100% per task (point in polygon lowest) | solver program with API snippet: .71–.97 |

1. **Exact computation is offloaded.** A next-token predictor is not a calculator: cross products of 10^9-scale coordinates or sums of 80 item values are easy to get wrong in text, and 21% of direct replies ran out of tokens doing arithmetic. Executed code computes them exactly.

   > *Example* (Qwen3-8B, an 8-vertex polygon whose doubled area is 436). Direct answers: 436 on the original (correct), but 2944 on a shifted copy, 392 rotated, 728 mirrored, and on the copy offset by 10^9 the reply hit the 2,048-token cap in the middle of the arithmetic. The executed shoelace program printed the right value on all 8 versions. Closest pair is worse: 79 of 160 direct replies ran out of tokens while listing pairwise distances.

2. **One program handles every input size.** Direct answers degrade with size (knapsack optimality gap 6% at 10 items → 48% at 80; TSP 9% at 8 cities → 139% at 20, infeasible at 40), the "curse of complexity" also seen in ZebraLogic. A correct algorithm costs the same to write for any size.

   > *Example* (Qwen3-8B, 0/1 knapsack). With 10 items the direct answer is optimal (162). With 80 items it picks items worth 1,997 when 2,697 is possible (26% short), and on a 20-item instance it claims 730 when the optimum is 669, i.e. its items exceed the capacity. The ~350-token OR-Tools program the same model writes has the same length at every size and reaches 2,697 at n = 80.

3. **Programs can be checked without labels.** Code can be run on transformed copies of the input (geometry) or checked for feasibility and objective value (optimization). Direct answers are not even consistent: no instance got the same answer on its 7 equivalent versions. That checkability is what makes verified sampling (F4) possible.

   > *Example* (a 10-point set with 6 hull vertices). Qwen3-8B's direct answers on the 8 equivalent copies: 4, 10, 4, 4, 6, 6, 6, 11 (Qwen3-32B: 9, 8, 9, 6, 6, 7, 6, 7). Without the label there is no way to tell which one is right. The 8B's program printed 6 on all 8; had it disagreed with itself, the disagreement alone would have flagged the bug.

4. **Solvers reuse decades of engineering.** For NP-hard problems the model only has to *formulate* the problem; CP-SAT or the routing library does the search. Programs with a hand-written heuristic instead are usually feasible but rarely beat a textbook greedy beyond small sizes (graph colouring with 40 nodes: 467% above optimal).

   > *Example* (Qwen3-8B, six 40-node graphs that need 4 colours). Direct colourings: none of the 6 is a valid colouring. Hand-written heuristic: 40 colours, one per node, on 3 of 6. CP-SAT model, after up to two repair rounds: the optimal 4 colours on 5 of 6.

5. **LLMs are trained on far more code than worked solutions**, and program-aided reasoning (PAL, Program-of-Thoughts, Logic-LM) is the established way to combine language understanding with exact execution.

The price is a new set of failure modes, which is what this project studies: the program must match the execution environment, use the solver API correctly, handle degenerate inputs, and choose a sound algorithm, and all of these are affected by what is put into the prompt.

## 2. Background (Related Work)

Checked per finding on 2026-10-13; the full table with verdicts and links is in `docs/notes/RELATED_WORK.md`.

- **Context that steers or misleads code.** Incidental prompt cues change which algorithm family a model writes (2606.04057), an available but unneeded tool hurts even when it is not called (2609.14157), plausible agent skills are over-trusted (2608.11888), and similar, buggy or misleading code context lowers code accuracy (2503.20589; 2306.03438; CodeCrash 2504.14119); irrelevant context in math (GSM-IC) and tool overload in agents (RAG-MCP, ToolRet) are the older versions. *Ours:* correct but unneeded helper code that the model copies collapses correctness (not only style), with token-level evidence of the route shift, a dose-response, immunity of reasoning models, and a second channel through input parsing.
- **Under-specified tools and contracts.** Tool descriptions are often incomplete and fuller ones repair only part of the misuse (2602.14878; DRAFT 2410.08197), and models rarely honour stated contracts (ContractEval 2510.12047). *Ours:* a matched test of the same helper with and without its orientation precondition, in which the needed helper is worse than none, across 4 models and 2 families.
- **Documentation for solver code.** OR-Tools routing code with decomposed documentation retrieval (DRoC, ICLR 2025), API docs that help CPMpy but not OR-Tools (CP-Bench 2506.06052), compact API specs and selective retrieval (Jain et al. 2024), near-miss documents that hurt (2401.14887). *Ours:* an exact snippet beats the full manual and reasoning at matched cost, and a near-miss snippet is as bad as none.
- **Priors over explicit specifications.** Reasoning models fall back on familiar patterns over stated conditions (2505.17225; 2507.14417), and redefined built-ins get worse with scale (2305.15507). *Ours, corrected:* our VRPTW case looked like this but was an ambiguous field name in our own format string (F3); what remains ours is the diagnosis method (counterfactual re-run, asking the model to restate the format) and the input-format failure that irrelevant helpers cause in geometry.
- **Selection, confidence and compute allocation.** Agreement-based selection on new inputs (MBR-exec, CodeT, S*, incoherence 2507.00057), prompt-side metamorphic testing (2406.06864), valid instance perturbations for optimization models (2607.16646); token confidence is poorly calibrated for code (2402.02047; 2610.11300) and favours repetitive programs (Coder-Reviewer); draft-agreement routing to thinking (DART 2606.23181) and brute-force oracles (ALGO; ExeCRE 2608.04439). *Ours:* selection by consistency of one program on transformed copies of the given instance; confidence inverted by misleading helpers; and a matched-token comparison in which check-gated routing loses to a fixed small thinking budget.
- **Forgetting and self-replay.** Training on a model's own outputs forgets less (2510.18874; 2601.19897; 2501.14315; SDFT; RL's Razor). *Ours:* a same-prompt contrast (the student's own programs vs the same-weights teacher's) on neighbouring unseen code tasks, with the idiom drift visible in the programs.
- **Failure taxonomies of LLM code** (2406.08731; 2407.06153; 2403.08937). *Ours:* geometry and optimization, behavioural labels with counterfactual re-runs, and a class-to-fix map against a re-sampling control.

**Gap.** What remains specific to this project is the combination: exact metamorphic scoring of geometry code, matched interventions that isolate one fact (a helper, a contract, an API call, an input field), and a fix-by-error-type comparison under token cost. Individually, most mechanisms have close relatives that must be cited.

## 3. Motivation

1. **Practical.** Code assistants receive tool catalogs, documentation dumps and utility libraries. If plausible tools silently change the algorithm a model writes, "give the model everything" is the wrong default.
2. **Measurable.** Algorithmic code has exact correctness checks (exact geometric oracles, proven optima), so small prompt changes can be measured precisely.
3. **The pilot already shows large, mechanistically clear effects** (Section 4.2): one helper that names another algorithm takes convex hull from 97% to 8%; a one-sentence hint brings it back to 94%; a 5-line API snippet takes vehicle routing from .23 to .90 where reasoning alone reaches .03.

## 4. Experiment Design

### 4.1 Setup

**Tasks.** All instances are generated programmatically with exact references.

| Domain | Core | Held-out (designed after the first findings) | Harder, multi-step |
|---|---|---|---|
| Geometry | convex hull vertex count, polygon area ×2, point in polygon, segment-intersection count, closest pair | convexity test, points in a triangle, convex-polygon overlap; pre-registered (E2): Delaunay check, farthest pair | lattice points inside a polygon (Pick), area of a union of rectangles (sweep line), polygon clipping (exact rational intersection area) |
| Optimization | 0/1 knapsack, TSP, graph colouring, makespan scheduling | bin packing, vertex cover | capacitated vehicle routing (CVRP), VRP with time windows (VRPTW) |

- **Geometry evaluation:** every instance comes in 8 equivalent versions (translated, rotated, mirrored, permuted, scaled, offset by 10^9, plus a degenerate case); a program counts as correct only if it is right on all 8.
- **Optimization evaluation:** share of instances solved to the proven optimum (DP, Held–Karp, exact CP-SAT models), solver arm with OR-Tools and up to 2 repair rounds.

**Interventions.** helper toolbox (needed helpers only = K0, plus K extra related helpers, K up to 10); a needed helper with or without a hidden contract; documentation (none, full OR-Tools sheet, problem-specific snippet, near-miss snippet, BM25 retrieval); one-sentence algorithm hints (hand-written, self-generated, retrieved); verified sampling (k programs, label-free selection: metamorphic consistency for geometry, feasibility + best objective for optimization); thinking mode, thinking budgets, reasoning effort; LoRA distillation.

**Models.** Qwen3 1.7B / 8B / 14B / 32B-AWQ; Llama-3.1-8B, Llama-3.3-70B; DeepSeek-R1-Distill-Llama-70B; OpenAI gpt-oss-20b / 120b (low / medium / high reasoning effort). Served locally with vLLM (A100s, vLLM 0.10.2; from 2026-10-13 on RTX PRO 6000 Blackwell GPUs with vLLM 0.22, where re-running earlier cells reproduced their exact counts, e.g. VRPTW 27/30, 21/30, 8/30, 18/30, 0/30 for four models; each comparison in this document uses one stack).

**Statistics and controls.** 300 programs per geometry condition (60 per task), 2–3 seeds for headline cells, paired bootstrap 95% CIs over instances. Helper effects are reported with helpers pre-defined at execution (so a model that calls a helper without copying it is not counted as a failure). A reference solution is pushed through every harness (480/480 on all tasks), and every new model family gets an output-extraction audit before its numbers are used.

### 4.2 Pilot findings

Each finding ends with a real example from the pilot runs (outputs shortened, `…` marks omitted lines). The F1, F4 and F5 examples use the same convex-hull instance (10 points, Qwen3-8B), so the fixes can be compared directly.

**F1. Extra helpers steer the algorithm choice. Thinking is one fix, but an expensive one, and not the only one.**

Change in % correct when 8 related but unneeded helpers are added (geometry, n = 300; every row scored with the offered helpers pre-defined, so a program that calls a helper without copying it is judged on its logic; `poc/rescore_figs.py`):

| Model | Without thinking | With thinking / reasoning |
|---|---|---|
| Qwen3-1.7B | +0.3, but opposite per task: hull −53, area2 −28, closest pair +47, segments +28 | −4.7 |
| Qwen3-8B | −14.3 (helpers pre-defined in the prompt too: −12.3) | −1.5 |
| Qwen3-14B | −7.7 | −0.5 |
| Qwen3-32B | −13.3 (helpers pre-defined in the prompt too: −15.0) | −3.0 |
| Llama-3.1-8B | −35.2 | – |
| Llama-3.3-70B | +0.8 | – |
| R1-Distill-Llama-70B | – | 0.0 |
| gpt-oss-20b / 120b | – | −0.7 to 0.0 (low and medium effort; at high effort 20b runs out of tokens in a quarter of programs) |

(Scored as measured, Qwen3-1.7B showed −35.7, but 185 of its 214 crashes were helpers called without being copied.)

![Where robustness to plausible helpers appears](figs/fig7_distractor_by_model.png)

Evidence for the mechanism (off-idiom drift):
- **The code changes algorithm.** With the extras, convex-hull programs switch from the monotone chain to a Graham scan built on the offered `polar_sort` in 44–75% of cases, and those are the failing programs.
- **One helper is enough** (pre-registered test, `docs/prereg/PREREG_E4.md`): offering `polar_sort` + `collinear` takes hull from 97% to 8% (8B) and 83% to 6% (32B). The registered prediction that "non-suggestive" helpers are harmless failed (they still cost 15–38 points, partly through their dependencies), so a priori similarity labels do not predict harm.
- **The choice is visible in the logits.** Scoring each model's own sampled programs under both prompts: the toolbox makes the helper-route program more likely by 0.40–0.71 nats per token, in 100% of 180 instances, shrinking with model size; the shift sits in the first ~10% of the program (imports and helper names).
- **Domain contrast.** In optimization, 8 unneeded API lines or other problems' snippets change nothing: the model writes a formulation it knows and ignores extra text.
- **The same mechanism can help.** On the lattice-point task the extras include `point_in_polygon`, which labels boundary points exactly; models switch to a brute-force count with it and Llama-70B goes from 0 to 45 of 60.
- **Pre-registered test on a new task (E2, farthest pair of points; `docs/prereg/PREREG_E2.md`).** Offered `convex_hull` + `polar_sort`, Qwen3-32B switches to hull-based code in 97% of programs and loses 21.7 points (CI [−31.7, −11.7]). But the helpers that suggest no other algorithm (`point_in_polygon`, `segments_intersect`) cost even more, 46.7 points, through a second channel: 64 of their 66 failures read every input line as a point and ignore the stated count line (they print the right answer once that line is removed), and 53 of the 66 call none of the helpers. Showing the instance's literal input in the prompt, the fix from F3, removes all of them (54 → 119 of 120). Qwen3-8B keeps its brute-force program under both toolboxes and is unaffected; gpt-oss −3.3. So extra helpers can derail the algorithm *or* the attention to the stated input format, and the registered prediction "only algorithm-suggesting helpers hurt" failed for 32B.
- **Published context fixes do not undo the steering (B3, pre-registered).** A one-sentence scope instruction (cf. 2609.14157) recovers 2–3% of the harm at 8B and 32B although it cuts helper use by a third. System 2 Attention (the model first rewrites the prompt) makes the core tasks 11 points *worse*, because the rewrite loses details (float outputs, signed areas) or, for 32B, leads to replies without a program, but it does fix the input-format channel (diameter 54 → 98 of 120). Removing unneeded helpers remains the only cheap fix that works.

**Is the conclusion just "use thinking"? No.** Thinking removes the harm because it lets the model choose its algorithm before writing; anything else that fixes the algorithm choice works too, at a fraction of the cost (8B):

| Fix for the same harm | Accuracy | Output tokens per program |
|---|---|---|
| none (8 extra helpers, no thinking) | 76–78% (hull with the 2 worst helpers: 7%) | ≈0.8–1.1k |
| full thinking | 97% | ≈6k (≈15k on the example instance) |
| one-sentence algorithm hint, no thinking (hull, 2 worst helpers, 3 seeds) | 94% | ≈0.6k |
| distilled LoRA, no thinking (F5) | 98% | ≈0.35k |
| simply not offering the extras | 92–97% | ≈0.3k |

And thinking does *not* protect against the other two failure types: a needed tool with a hidden contract (F2: the reasoning model R1 still falls in on the lattice task, and Qwen3-8B with thinking keeps most of the Delaunay trap) and a missing API fact (F3: thinking without documentation reaches .03). So F1's practical message is about **tool design**: offer only the helpers the task needs (unneeded ones can derail the algorithm or the input parsing), name the intended algorithm, and show one example input; reasoning is the fallback when you can't control the toolbox.

![Dose-response: harm grows with the number of extra helpers](figs/fig2_distractor_dose.png)

> **Example F1** (Qwen3-8B, the same 10-point convex-hull instance under four conditions).
>
> *Needed helper only*: the textbook monotone chain, correct on all 8 versions.
> ```python
> points = sorted(set(points))
> for p in points:
>     while len(lower) >= 2 and orient(lower[-2], lower[-1], p) <= 0:
>         lower.pop()
>     lower.append(p)
> … (same for the upper hull)
> return lower[:-1] + upper[:-1]
> ```
> *8 extra helpers*: the model copies all 11 helper definitions, switches to a Graham scan on `polar_sort`, keeps the start point inside the sorted list, and adds a spurious "remove collinear points" pass. Wrong on all 8 versions.
> ```python
> left = min(points, key=lambda p: (p[0], p[1]))
> sorted_points = polar_sort(points, left)        # the offered helper decides the algorithm
> hull = [left, sorted_points[0]]                 # sorted_points still contains `left`
> for p in sorted_points[1:]:
>     while len(hull) >= 2 and orient(hull[-2], hull[-1], p) <= 0:
>         hull.pop()
>     hull.append(p)
> …
> for i in range(len(hull)):                      # extra pass suggested by `collinear`
>     a, b, c = hull[i-2], hull[i-1], hull[i]
>     if orient(a, b, c) != 0:
>         final_hull.append(hull[i])
> ```
> *Same helpers + "Hint: Andrew's monotone chain …"*: monotone chain again; `polar_sort` is copied but never called. Correct, 563 tokens.
>
> *Same helpers + thinking*: monotone chain, correct, but 15,168 tokens.

**F2. A needed tool with a hidden contract is a trap.**
- The needed helper for the lattice task returns a *signed* area. Models use it without `abs`, and Pick's formula fails on clockwise input: Qwen3-32B drops from 44 to 9–15 of 60.
- Fixing the tool (return the absolute value) restores 46–49; writing the hazard in its docstring does not (17–19), because the model then abandons the helper for a buggy brute force.
- Reasoning reduces the hazard but does not remove it: Qwen3-8B with thinking 52 vs 60 (signed vs unsigned); R1-Distill-70B with the toolbox 57 → 42, every orientation failure a missing `abs`.
- The same hidden assumption appears without any helper: in polygon clipping, gpt-oss assumes counter-clockwise input in 35 of its 45 failures.
- **It replicates on a new, pre-registered task (E2, Delaunay check: count the triangles of a given triangulation whose circumcircle strictly contains a point).** The needed `in_circle` helper says in its comment, tersely, that the triangle must be counter-clockwise. With it, Qwen3-8B / 32B solve 1 / 3 of 120; with the same helper made orientation-free, 109 / 106 (+90 / +86 points). 92% / 97% of the failures are right on every orientation-preserving copy and wrong only on the mirrored or relabelled ones: the programs never orient the triangle. A spelled-out warning recovers 16% of the gap at 8B but 75% at 32B. For 32B the terse helper is far worse than no helper (3 vs 55 of 120); gpt-oss-20b (low effort) is unaffected (118 vs 117). A registered extension finds the same trap in Llama-3.3-70B and Qwen3-14B (8 → 120 and 4 → 120 of 120; both worse than with no helper, 81 and 76). Thinking removes it at 32B (118 vs 120) but only partly at 8B (51 vs 118), at 7.8–8.8k tokens per program against ≈0.4k for fixing the helper. Letting the model document the helper itself (DRAFT-style probing, B3) does not help: its probes never try a clockwise triangle, so its docs only restate the precondition (32B: 27 of 180 vs 43 of 60 with the hand-written warning).

> **Example F2** (Qwen3-32B, lattice points inside a polygon, only the needed helper offered). Correct on the original polygon, wrong on the mirrored and reversed copies, where the signed area is negative:
> ```python
> def polygon_area2(poly):        # twice the signed area (shoelace, exact)   <- the offered helper
> …
> area2 = polygon_area2(poly)     # negative for clockwise vertex order; no abs()
> A = area2 // 2
> I = A - boundary_points // 2 + 1
> print(I)
> ```
> With the helper changed to `return abs(sum(...))` the same model writes the same Pick's-theorem program and is correct on 46–49 of 60 instances; with the warning "NEGATIVE for clockwise; use abs()" added to the comment, 38 of 60 programs drop the helper and switch to a bounding-box brute force that miscounts boundary points.

**F3. Solver code fails on missing API facts; only the exact fact fixes it.**

| Optimization (share optimal; 6-problem row: within 1%) | no doc | full sheet | near-miss snippet | exact snippet | best-of-3 with snippet | thinking, no doc |
|---|---|---|---|---|---|---|
| 6 problems, Qwen3-8B / 14B / 32B | .26 / .61 / .70 | .35 / .81 / .93 | – | .71 / .96 / .97 | 14B, 32B: 1.00 | – |
| CVRP, Qwen3-32B | .23 | .07 | – | .77–.90 | 1.00 | .03 |
| CVRP, Llama-3.3-70B | .40 | .60 | – | .83–.93 | 1.00 | – |
| VRPTW, Llama-3.3-70B | 0 | 0 | 0 | .60–.77 | .93 | – |
| VRPTW, Qwen3-32B | 0 | 0 | 0 | .10–.27 | .47 | – |
| VRPTW, gpt-oss-20b low / medium | .10 / .33 | .07 / – | .07 / – | .07–.17 / .57–.70 | .37 / .90 | – |
| VRPTW, gpt-oss-120b low / medium | .07 / .13 | – | – | 0 / .03–.07 | 0 / – | – |
| VRPTW + literal input in prompt, gpt-oss-20b low / medium | .33 / .50 | – | – | **.80–.97 / .90–1.00** | **1.00 / 1.00** | – |
| VRPTW + literal input in prompt, gpt-oss-120b low / medium | .70 / .77 | – | – | **.97–1.00 / 1.00** | **1.00 / 1.00** | – |
| VRPTW + literal input in prompt, Qwen3-32B / Llama-70B | 0 / 0 | – | – | .37–.50 / .67–.77 | .83 / .97 | – |

- A 5-line snippet of the exact OR-Tools calls beats a full manual at every size, also on held-out problems.
- **A near-miss reference is as bad as none or worse:** the full sheet shows TSP routing without capacities and 32B invents the rest (CVRP .07); the CVRP snippet without the time dimension gives 0 on VRPTW.
- **A skipped input field, caused by an ambiguous format string (corrected 2026-10-13).** On VRPTW our prompt stated the header as `n capacity K service horizon`; gpt-oss-120b (low and medium effort) read it as `n capacity K horizon` in almost every program (0–3 of 30 parse `service`), so the horizon became 10 and the solver reported infeasible. Re-running those programs with the field removed makes 43 of 49 optimal: the routing model was right, and repair with the traceback never finds the cause. Asked to restate the fields, the model writes "`n capacity K horizon` … maximum route end time (service horizon)": it reads *service horizon* as one compound noun. Written unambiguously as `n capacity K service_time horizon`, the same prose prompt gives 30/30 and 30/30 optimal for 120b low and 29/30, 29/30 for 20b low (F3y). So this was an ambiguity in our spec, resolved more consistently by the larger model, not a prior overriding a clear specification. A behavioural audit of all 22 format strings (each model writes a parse-only program for each format; A1) finds no other ambiguous one: only the old VRPTW header is misread systematically (gpt-oss-120b, gpt-oss-20b and Qwen3-8B in 3 of 3 samples).
- **Showing the instance's literal input disambiguates it, for every gpt-oss setting and at a fraction of the tokens.** With the snippet, 120b low goes from 0 to .97–1.00 (4.8k → 1.7k tokens per instance), 120b medium from .07 to 1.00 (10.7k → 3.7k), 20b low from .07–.17 to .80–.97, 20b medium from .57–.70 to .90–1.00; programs that skip the field drop from 18–29 of 30 to 0–3 (counterfactual re-run with the field removed). Qwen3-32B and Llama-70B rarely skip the field; for them the example adds .10–.23, because their failures are API errors that only the snippet fixes (without it they stay at 0, while gpt-oss reaches .50–.77). The same fix works in geometry (F1, E2): it removes the count-line failures that irrelevant helpers cause in Qwen3-32B. Asking the model to restate the fields does not help (gpt-oss 0–2 of 30; it restates its own misreading), and DRoC-style decomposed retrieval over a routing documentation base (B4, pre-registered) beats plain top-3 retrieval (+.12 to +.15) but not the exact snippet (−.12 to −.40; on VRPTW .03 vs .23–.63), because the models splice argument patterns across the retrieved chunks. Format fact → show an input (and write unambiguous field names); API fact → show the assembled snippet; the two compose.
- **Reasoning cannot replace the fact:** with thinking but no documentation, 14B / 32B / R1-Distill-70B reach .33 / .03 / .00 on CVRP at 11–19k tokens per program, versus .97 / .97 / .90 with the snippet.
- **Retrieval works when it is precise.** BM25 over a titled snippet library: top-1 matches the hand-written snippet (32B .965 vs .956, 2 seeds); top-3 adds near-misses and costs up to 26 points on single problems (bin packing .89 → .59, CVRP .78 → .55). A strong model (gpt-oss-20b) is not hurt by extra chunks.

![Optimization documentation: exact snippet vs full sheet](figs/fig5_co_docs.png)

> **Example F3** (Qwen3-32B, CVRP with 8 customers; final programs after 2 repair rounds with the error message; the full-sheet and snippet programs are for the same instance).
>
> *Full sheet (TSP routing, no capacity dimension)*: the model guesses the capacity API and fails even after repair.
> ```python
> manager = pywrapcp.RoutingIndexManager(num_locations, K, [0] * K, [0] * K)
> demand_callback_index = routing.RegisterUnaryLongLivingCallback(demand_callback)
> # AttributeError: 'RoutingModel' object has no attribute 'RegisterUnaryLongLivingCallback'
> ```
> *Thinking, no documentation* (another instance, ≈15k tokens per program): a different invented name.
> ```python
> demand_callback_index = routing.RegisterUnaryCallback(demand_callback, True)
> # AttributeError: 'RoutingModel' object has no attribute 'RegisterUnaryCallback'
> ```
> *Exact snippet* (5 lines showing `RegisterUnaryTransitCallback` + `AddDimensionWithVehicleCapacity`): proven optimum.
> ```python
> demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
> routing.AddDimensionWithVehicleCapacity(demand_callback_index, 0, [Q] * K, True, "Load")
> ```

**F4. Choose the fix by error type (efficiency).**

| Situation | Sampling + label-free check | Thinking | Verdict |
|---|---|---|---|
| Geometry, clean prompt (8B) | best-of-3: **100** at ≈0.9k tokens | 91 at 5.5k | errors vary between samples → sample and check |
| Geometry, 8 extra helpers (8B) | best-of-3: 84 at 2.5k | 1k budget: 87 at 1.6k; full: 97 at 5.8k | same error in every sample → reason |
| Hard geometry, lattice + rectunion (8B, of 120) | best-of-3: 44 at ≈1.7k | 1k budget: 97 at ≈1.8k | systematic → reason |
| Optimization (8B) | best-of-3: .72 | .87 at 5.9k | systematic API misconceptions → reason or state the fact |
| Optimization (14B / 32B) | best-of-3: 1.00 at ≈⅓ of thinking's tokens | .98–1.00 | independent slips → sample |

- **Budgets:** about 1k thinking tokens recover most of the accuracy on geometry (lattice 8B 12 → 58 of 60); optimization needs far more (TSP stays at 0 with 2k; bin packing reaches .87 only with ≈6k).
- **Fixes compose on the hardest task** (polygon clipping, gpt-oss-20b at low effort): 14 → 44 with a one-sentence hint → **59 of 60** with hint + 3 checked samples, at ≈2.8k tokens in total. The check never picked a wrong program. Non-reasoning Qwen/Llama solve 0–2 of 180 in any condition.
- **Natively reasoning models move the frontier.** gpt-oss-20b at low effort: ≈99% at ≈0.4–0.9k tokens, with or without helpers. High effort backfires: 27% of programs never finish within 24k tokens.
- **Against published label-free selectors (B1, pre-registered; same 3 candidates per instance, Qwen3-8B):** the metamorphic check picks a correct program in 99.7 / 83.3 / 33.3% of instances (clean / 8 extra helpers / hard tasks), CodeT (model-written tests with expected outputs) 96.0 / 82.7 / 26.7, a plain vote on the given input 95.7 / 81.3 / 21.7, MBR-exec on model-written or fresh random inputs 93.7 / 80.3 / 21.7–25.0, and token-confidence selectors (DeepConf) at most 95.3 / 80.0 / 15.0. Fresh inputs from the same distribution miss sign and orientation errors that the mirrored and scaled copies of the given instance expose, and the check costs no generation tokens.
- **The verified-sampling gain is not leakage:** selecting on the given instance and scoring on 5 fresh instances gives 98.2 / 97.7 / 93.9 (8B / 14B / 32B) vs 98.7 / 97.7 / 94.3 in-instance.
- **The model's own confidence cannot replace the check (C1, pre-registered; Qwen3-8B, 3 samples per instance).** The mean log-probability of a program's tokens comes free with generation. On clean prompts it does separate right from wrong programs (AUROC 0.68), but taking the most confident of 3 programs gains only +1.0 point [−1.1, +3.1] over one sample, against +7.0 for the metamorphic check. Under 8 extra helpers the wrong hull programs (Graham scans on the offered `polar_sort`) are *more* probable than the right ones (AUROC 0.43), as the logit probe predicts; on the hard tasks confidence is anti-correlated with correctness (0.40) and picking the most confident program loses 3.6 points (the most confident wrong programs are repetition loops and boiler-plate brute force). Qwen3-32B replicates it (most-confident vs one sample +0.0 to +1.9, n.s.; the check beats confidence by 6.7–22.5 points), with the confident-wrong case moving to the task where 32B is hurt by the helpers (area2, AUROC 0.33). Confidence measures how typical a program is for the model, not whether it is right, and it fails exactly on the systematic errors where sampling + checking also struggles.
- **A check-gated pipeline is efficient for slips but blind to systematic errors (E3, pre-registered; `docs/prereg/PREREG_E3.md`).** One program; only if the metamorphic check fails, 3 samples + check; only if none is consistent, one program with a 1,024-token thinking budget. With needed helpers only (Qwen3-8B): 98.0% at 365 output tokens per instance, the accuracy of best-of-3 + check (938 tokens) and close to full thinking (100% at 3,792). Under 8 extra helpers / on the hard tasks it reaches only 84.7% / 53.3%, below simply giving every instance a 1,024-token thinking budget (93.0% / 80.8% at about the same tokens, 1.6k / 1.7k). The reason is the check's blind spot: it accepts programs that are wrong on every transformed copy in the same way (28 of 264 accepted first programs under K8, 21 of 40 on the hard tasks), and a wrong algorithm is usually wrong invariantly. The check routes random slips, not systematic errors; for those, a small fixed thinking budget is the cheap default. A brute-force reference written by the same model (E3b, pre-registered) does catch 86–90% of the errors the check misses, but writing it costs as much as the thinking budget and it is itself wrong on the hardest task (lattice points 1 of 60), so it saves nothing.

![Fixes under a broad toolbox](figs/fig8_fixes_under_distractors.png)

> **Example F4a: a random slip, fixed by sampling** (Qwen3-8B, polygon area, clean prompt, 3 samples). Two samples use integer arithmetic and are correct; one parses coordinates as floats:
> ```python
> x = float(data[idx]); y = float(data[idx + 1])     # products near 1e18 lose precision
> print(int(2 * area))
> ```
> It is right on 7 versions and wrong only on the copy shifted by 10^9. Running the three programs on shifted / rotated / mirrored copies of the *given* instance exposes the inconsistency without knowing the answer, so the check keeps an integer program. Cost: 3 × ≈0.3k tokens.
>
> **Example F4b: a systematic error, not fixed by sampling** (Qwen3-8B, the F1 hull instance with 8 extra helpers). All 3 samples take the `polar_sort` route (two wrong everywhere, one wrong on the degenerate case), so there is no consistent correct program to select. Thinking writes the monotone chain and is correct (15k tokens); the one-sentence hint does the same at 0.6k.
>
> **Example F4c: hint + check compose** (gpt-oss-20b, polygon clipping). The program clips with `cross(cp1, cp2, e) >= 0`, which keeps the right side only if the clipping polygon is counter-clockwise:
>
> | identity | translate | rot90 | mirror | reversed order | scale ×3 | +10^9 | degenerate |
> |---|---|---|---|---|---|---|---|
> | ✓ | ✓ | ✓ | ✗ (prints 0) | ✗ (prints 0) | ✓ | ✓ | ✓ |
>
> The check rejects it because the mirrored copy disagrees with the original (single sample 14 of 60 → checked 28). The hint "orient both polygons counter-clockwise first" removes most of these bugs (44), and hint + check gives 59.

**F5. Robustness can be distilled into a fast model per task; replaying the student's own programs protects the other tasks.**
- LoRA on Qwen3-8B, trained on 600 verified programs written by the same model *with* thinking, on prompts with 0/4/8 extra helpers: under 8 extra helpers, 77.0 → **98.0** (+21.0 [+17.8, +24.3], 2 seeds), thinking-level accuracy at ≈350 tokens instead of ≈6k. The gain survives unseen prompt formats (other headers, 10 helpers).
- Training on clean prompts only (same size) gives no gain under helpers: the model learned to ignore helpers, not just better code.
- **No transfer, and collateral damage:** on unseen tasks the distilled model is slightly worse (58.6 → 52.2), training on 4 or 9 other tasks does not help, and an unseen fragile task can collapse even on clean prompts (hull 97 → 28–34). Lighter training removes the damage only by removing the gain.
- **Replaying the student's own programs removes the damage (E4, pre-registered; `docs/prereg/PREREG_E4_REPLAY.md`).** Leave-hull-out LoRA, hull on clean prompts: base 109/120, no replay 48, **+ 270 of the student's own verified no-thinking programs on 5 other tasks: 118**, + the thinking teacher's programs for exactly the same 270 prompts: 36 (self − teacher replay +68.3 [+60.0, +76.7]). The in-task robustness is kept (240/240 under 8 helpers). The programs show why: the base model and the self-replay student write the monotone chain in 120/120 hull programs, the no-replay and teacher-replay students in 59 and 49. Distilling from a teacher moves the student off its own idioms on tasks it never trained on; its own programs anchor them. Not everything is protected: on the new Delaunay task both replay arms drop (59 → 47 / 45 of 60), so tasks outside both data sources still need re-validation. Against established remedies (B2, pre-registered): averaging the tuned and base weights (WiSE-FT) keeps hull only by giving up the in-task gain (α 0.5: 119 / 222 of 240) or vice versa (α 0.75: 96 / 236); SDFT (the student rewrites the teacher's programs) halves the damage (85) and is the only method that helps hull under 8 helpers (58 vs 23–31); self-training on the student's own programs alone gives 104 / 235. Self-replay is the only one that keeps both (118 / 240). Because those trained tasks had little headroom (base 225 / 240), E4b (pre-registered) trains hull as well and holds out convex: the in-task gain is large (5 tasks under 8 helpers 236 → 295 of 300, hull 11 → 55 of 60) and self-replay keeps the unseen convex task at the base level under helpers (81 → 80 of 120), while no replay drops it to 55 and teacher replay to 42.

> **Example F5** (the F1 hull instance with 8 extra helpers, no thinking).
>
> *Base Qwen3-8B* (1,067 tokens): copies all 11 offered helpers (`point_in_polygon`, `polar_sort`, `dist2`, `is_convex`, …) and builds the hull on `polar_sort`; wrong.
>
> *Distilled LoRA* (249 tokens): copies only what it needs and writes the monotone chain; correct on all 8 versions.
> ```python
> def orient(a, b, c):
>     return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
>
> def convex_hull(points):
>     points = sorted(points)
>     …
>     for p in points:
>         while len(lower) >= 2 and orient(lower[-2], lower[-1], p) <= 0:
>             lower.pop()
>         lower.append(p)
>     …
>     return lower[:-1] + upper[:-1]
> ```
> *The other side*: a LoRA trained the same way but *without* any hull data turns the clean-prompt hull task from 97% into 28–34% correct; most of its failures are Graham-scan variants and improvised loops instead of the monotone chain it wrote before fine-tuning.

**E1. Where the failures come from, and which fix repairs which kind (all stored programs).** Each of the 14,822 failing programs of the headline runs (47,868 programs, 388 runs) got exactly one class from its behaviour only: which of the 8 versions it gets wrong, the exception it raises when re-run, and counterfactual re-runs (another input layout, the VRPTW header without the skipped field, the offered helpers pre-defined). Reading 8 random programs per class confirmed 127 of 128 geometry labels and 85 of 97 optimization labels (`poc/analyze_e1_taxonomy.py`, `docs/notes/E1_TAXONOMY_DRAFT.md`).

| | algorithmic (logic, orientation, degenerate, precision) | API / knowledge | input format | packaging / interface (helpers) | other |
|---|---|---|---|---|---|
| Geometry, 9,846 failures | **72%** (hard tasks 81–87% in every family) | – | 1% | 12% (52% for Qwen3 no-thinking when a toolbox is offered) | 16% |
| Optimization, 4,976 failures | 29% (modelling / logic) | **51%** (Qwen3 58%) | 8% (all VRPTW; gpt-oss's failures are 53% input format, caused by the ambiguous header, see F3) | – | 12% (6% output format) |

Pairing each failure with the same instance after one fix (control: the same condition re-sampled, which rescues 9–52% depending on the class) gives a fix map: **API fact → the exact snippet** (618 of 1,042 rescued; thinking 91 of 240); **input format → one literal input** (75 of 94; more effort 44 of 178); **orientation → a one-sentence hint** (188 of 221) or more reasoning effort; **logic → thinking** (476 of 544) or a hint (810 of 1,204), where sampling + check is no better than re-sampling (204 of 914); **precision → sampling + metamorphic check** (46 of 55); **degenerate cases → thinking** (23 of 27), while the check rescues 0 of 70 because it never runs the degenerate copy; **wrong helper call signatures → one API-contract sentence** (61 of 83); **uncopied helpers → pre-define them** (the same program then succeeds in 329 of 630 cases, 125 of 162 for Qwen3-14B but 3 of 12 for 8B, whose programs were wrong anyway).

One scoring choice matters: 293 TSP failures print the tour with the return to the start city (`0 … 0`), against the requested "each city exactly once"; 281 of those tours are optimal. Accepting them would raise e.g. Qwen3-32B without documentation from .70 to .83 and Llama-70B (no doc / full sheet / snippet) from .33 / .55 / .87 to .54 / .73 / .99. The F3 ordering does not change; the gaps shrink. The numbers in this document use the stated format.

### 4.3 Follow-up experiments (status 2026-10-13)

| # | Experiment | Question | Status |
|---|---|---|---|
| E1 | Failure taxonomy over all stored programs (API/knowledge, input format, algorithmic: logic, orientation, degenerate cases) per model and condition | What share of failures is algorithmic, and which fix addresses each class? | done: geometry failures are 72% algorithmic, optimization failures 51% missing API knowledge; a class → fix map (E1 above; `docs/notes/E1_TAXONOMY_DRAFT.md`) |
| E2 | Pre-registered replication of F1/F2 on new tasks (Delaunay check, farthest pair) | Do steering and hidden-contract effects predict new tasks? | done: F2 replicates strongly; F1 partly, with a second (input-format) channel (F1, F2; `docs/prereg/PREREG_E2.md`) |
| E3 | Deployable pipeline: check first, sample if the check fails, think if no sample is consistent | Can the label-free check decide how much to spend? | done: yes for random slips, no for systematic errors (F4; `docs/prereg/PREREG_E3.md`) |
| E4 | Distillation with replay data from other tasks | Can per-task robustness be learned without damaging other tasks? | done: replaying the student's own programs protects the unseen task, the teacher's do not (F5; `docs/prereg/PREREG_E4_REPLAY.md`) |
| C1 | Token confidence as a label-free selector (added) | Can log-probs replace the executable check? | done: no (F4) |
| B1–B4 | Published methods as baselines (added after the related-work check) | Do existing methods do better than our fixes? | done: CodeT / MBR-exec / DeepConf below the metamorphic check; WiSE-FT / SDFT / self-SFT below self-replay; scope sentence and S2A do not undo helper steering; DRoC-style retrieval below the exact snippet (`docs/prereg/PREREG_B1.md`–`B4.md`) |
| E3b, E4b, A1 | Brute-force reference; replay with a large in-task gain; audit of all format strings (added) | | done (F4, F5, F3) |
| E5 | A closed API model (if budget allows) | Do F1–F4 hold for frontier models? | not run (no API access in this environment) |

## 5. Limitations

1. **Synthetic tasks.** Problems are generated with exact references; realistic multi-step tasks (clipping, VRPTW) replicate the main effects, but real codebases have larger, less specified contexts.
2. **Partly post-hoc mechanism.** Off-idiom drift was formed after seeing the data. Two pre-registered tests confirmed its core (one algorithm-naming helper flips the hull algorithm; the hidden-contract trap replicates on a new task) but refuted similarity-based predictions, and on a new task helpers that suggest no algorithm hurt through input parsing instead.
3. **Oracle fixes.** Snippets and hints are hand-written; retrieval matches them only when it fetches the exact page, and self-generated hints help only when the model already knows the algorithm. The label-free check that a deployed system can use misses errors that are invariant under the transformations (E3).
4. **Coverage.** Open-weight models only (three families; E5 not run); some secondary cells are single-seed. Runs after 2026-10-13 used a newer serving stack; re-runs of earlier cells reproduced their exact counts, and no comparison mixes the two stacks.

## Appendix A. Code and How to Run

```
poc/run_geo.py, run_geo_cross.py   geometry tasks, variants, oracles, harness
poc/geo_distractors.py             helper pool, toolbox construction
poc/run_co.py                      optimization problems, references, solver harness, retrieval
poc/mr_select.py, fresh_eval.py    label-free selection (metamorphic check)
poc/logit_probe2.py                token-level probe of sampled programs
poc/sft_lora.py                    LoRA distillation
poc/sanity_check.py                reference passthrough for every geometry task
poc/rescore_figs.py, make_figures.py   packaging-free re-scoring, figures
poc/analyze_vrptw_stdin.py         VRPTW input-format counterfactual (field removed from the header)
poc/analyze_c1.py, analyze_e2.py, analyze_e3.py, analyze_e4.py   confidence selector, new tasks, pipeline, replay
docs/FINDINGS.md                full log;  docs/prereg/PREREG_*.md  pre-registrations (with appended results)
```

Typical runs (a vLLM server with OpenAI-compatible API at `POC_BASE_URL`):

```
python poc/run_geo_cross.py --model_tag X --stdlib --n_inst 30 --temperature 0.7 --seed 1 --distract 8 [--think | --algo_hint | --show_stdin | --logprobs]
python poc/run_geo_cross.py --model_tag X --stdlib --n_inst 30 --temperature 0.7 --seed 1 --tasks delaunay --distract 0 --incircle signed|doc|fixed
python poc/run_co.py --model_tag X --arms solver --probs cvrp --n_inst 10 --repair 2 --api_doc --api_doc_task [--retrieve 1]
MR_PREFIX=X_geox python poc/mr_select.py <model> 1 base@1,base@2,base@3
```

## Appendix B. Example Prompt

The examples for each finding are in Section 4.2. Below is the prompt format of the geometry runs (convex hull with 8 extra helpers; only `orient` is needed).

```text
Points: (20,-40) (-26,-18) (-18,-12) (-50,38) (-18,42) (58,16) (-30,-26) (6,58) (52,-36) (50,14)
How many vertices does the convex hull of these points have? Points lying on a hull edge (collinear)
are not vertices; duplicate points count once.
Write a Python 3 program that solves this problem for any input in the following stdin format: …
You may (and should) use these tested helper functions; copy the ones you use into your program unchanged:
  on_segment, closest_pair_sq, point_in_polygon, polar_sort, bbox, is_convex,
  segments_intersect, dist2, orient, collinear        (full definitions shown in the prompt)
```
