# Tools, Facts, and Checks: When LLM-Written Geometry and Optimization Code Fails, and Which Fix to Use

*Graduate NLP course project proposal: computational geometry and combinatorial optimization*

> **About this file.** The compact project proposal. The full log, with every control and correction, is [results/FINDINGS.md](results/FINDINGS.md); the earlier full-length version is `results/archive/PROPOSAL_before_compact_2026-10-15.md`.

## 0. Primer: how LLMs solve geometry and optimization problems

**The problems.**
- **Computational geometry:** compute an exact answer from coordinates, such as the area of a polygon or the convex hull of a set of points.
- **Combinatorial optimization:** pick the best of very many options, such as the shortest delivery route or the fewest colours for a graph. Checking that an answer is valid is easy; proving that it is the best is hard.

**Six ways an LLM can solve them:**

| Approach | How it works | Example | Known from |
|---|---|---|---|
| 1. Answer directly | the model works the answer out in text | "Twice the area is 436." | chain-of-thought; reasoning models |
| 2. Improve guesses | the model proposes solutions, sees their scores, proposes better ones | "Tour 1-3-2-4 has length 120; give a shorter tour." | OPRO |
| 3. Write a program | the model writes code; the computer runs it | `print(abs(sum(x1*y2 - x2*y1 ...)))` (shoelace area) | PAL, AlphaCode |
| 4. Use a solver | the model writes the problem as solver code; the solver finds the best answer | `m.Add(c[a] != c[b])` for each edge, then `m.Minimize(k)` (graph colouring) | OptiMUS, ORLM |
| 5. Evolve a heuristic | many versions of a rule are tested; the best survive | evolve `priority(item, bins)`: which bin gets the next item | FunSearch, EoH |
| 6. Help a prover | the model suggests steps; a symbolic engine proves geometry theorems | "add the midpoint of AB", then the engine finishes the proof | AlphaGeometry |

Approaches 1 and 2 break down as problems grow, and 6 proves theorems instead of computing. In practice geometry is solved with 3 and optimization with 3 and 4, usually in a loop: write several programs, keep the ones that pass a check, fix the ones that fail.

**Example: geometry.** Twice the area of an 8-vertex polygon, asked as 8 equivalent copies (shifted, rotated, mirrored, …). Answering directly, Qwen3-8B gives 436 (correct), 2944, 392 and 728 on different copies; its program (the shoelace formula) is right on all 8.

**Example: optimization.** Colour 40-node graphs that need 4 colours. Direct answers: none valid. A hand-written heuristic: often 40 colours. A ten-line solver model: the optimal 4 on 5 of 6 graphs, after up to two repair rounds that fix a crash from misusing the solver (`max()` on solver variables).

**This project** studies approaches 3 and 4: when these programs fail, and which cheap fix works. On 311 real contest geometry problems, one program per problem still solves only 12–57%.

## 1. Problem

LLMs solve geometry and optimization problems mostly by **writing programs** (approaches 3 and 4 above). These programs often look right and still fail, and the usual reaction is to put more into the prompt: helper functions, documentation, more reasoning tokens.

**Research question.** Which additions to the prompt make LLM-written CG and CO programs better or worse, why, and which cheap fix suits which failure, at what token cost?

1. **Tools.** Do correct but unneeded helper functions change the program? Can a needed tool hurt?
2. **Facts.** For solver code, does the exact API usage beat a full manual, retrieval, or more reasoning?
3. **Fixes.** When should we sample several programs and check them without labels, and when should we pay for reasoning?

## 2. Related work

Prompt context that steers or misleads code (2606.04057; 2609.14157; CodeCrash 2504.14119); under-specified tool contracts (DRAFT 2410.08197; ContractEval 2510.12047); documentation for solver code (DRoC, ICLR 2025; CP-Bench 2506.06052); label-free selection and repair (CodeT, MBR-exec, AlphaCode filtering, Self-Debugging; Olausson et al., ICLR 2024); forgetting and self-replay in fine-tuning (2510.18874; SDFT). Details and verdicts per finding: `results/RELATED_WORK.md`.

**Gap.** These mechanisms are studied one at a time on general code. We compare them on CG and CO with exact references, change one fact at a time in the prompt, and price every fix in tokens.

## 3. Method

- **Tasks with exact answers.** Generated geometry tasks (hull, area, point in polygon, segment intersections, closest pair, Delaunay, lattice points, rectangle union, polygon clipping) and optimization tasks (knapsack, TSP, colouring, scheduling, bin packing, vertex cover, CVRP, VRPTW). Standard benchmarks: 311 Codeforces geometry problems (CodeContests, official tests), the 56 Solomon VRPTW instances (100 customers), 40 job-shop instances (la01–la40).
- **Scoring.** Geometry: each instance is posed as 8 equivalent copies (shifted, rotated, mirrored, relabelled, offset by 10⁹, degenerate); a program counts only if right on all 8. Optimization: share solved to the proven optimum, or feasibility and gap to the best-known solution.
- **Interventions.** Unneeded helper functions (0–10); helpers with a hidden condition; documentation (exact 5-line snippet, full manual, retrieval); one literal input; sampling with a label-free check; reasoning budgets; repair from errors; LoRA distillation.
- **Models.** Open-weight models served locally with vLLM: Qwen3 (1.7B–32B), Qwen3.8-27B, Llama-3.1-8B / 3.3-70B, R1-Distill-Llama-70B, gpt-oss-20b / 120b.
- **Rigor.** Predictions written before each run (`results/PREREG_*.md`); 2–3 seeds; paired bootstrap confidence intervals; raw programs read, not only scores; accuracy always reported with output tokens.

## 4. Preliminary results

| Finding | Evidence (selected) |
|---|---|
| **F1. Unneeded helpers steer the algorithm.** | 8 extra helpers: Qwen3-8B / 32B −14 / −13 points without thinking; one pair of helpers takes convex hull from 97% to 8% (the model builds on the offered `polar_sort`). Thinking removes it (≈6k tokens); so does a one-sentence algorithm hint (94% at 0.6k). On real contest problems the effect shrinks (gpt-oss-20b −4.3 points, other models none). |
| **F2. A needed tool with a hidden condition is a trap.** | A Delaunay helper that needs counter-clockwise triangles: Qwen3-8B / 32B solve 1 / 3 of 120 with it, 109 / 106 with an orientation-free version; a warning recovers 16% / 75% of the gap. |
| **F3. Solver code fails on missing API facts; only the exact fact fixes it.** | Vehicle routing (Qwen3-32B): no doc .23, full manual .07, exact snippet .77–.90, thinking without doc .03. On Solomon, three facts are needed together (file layout, integers for OR-Tools, a first-solution strategy for tight windows): without them 0–6% of programs are feasible at low reasoning effort; with them gpt-oss-120b reaches 100%. Job-shop with CP-SAT needs no facts (79–85%). |
| **F4. Choose the fix by error type.** | Errors that vary between samples: best-of-3 + check 100% at 0.9k tokens (thinking 91% at 5.5k). Errors repeated in every sample: reasoning wins. On 311 contest problems, one repair round from the failing example is the best step per token (gpt-oss-120b low 46 → 53% at 4.6k tokens); effort low / medium / high gives 46 / 57 / 66% (high: one seed so far, 30k tokens per problem). |
| **F5. Robustness can be distilled; self-replay protects other tasks.** | LoRA on verified programs: 77 → 98% under helpers at 0.35k tokens instead of 6k; adding the student's own programs keeps an unseen task (118 of 120 vs 48 without, 36 with teacher programs). It does not carry over to contest geometry. |

**Our methods** (prior art checked first). *Verify once, reuse* works: pick one program that works on 8 training routing instances and reuse it unchanged. gpt-oss-120b is then feasible on 94% of 48 unseen instances for 28k tokens in total, against 7% when writing a program per instance. The same programs stay feasible on 200- and 400-customer instances (60 of 60 each; gap ≈ 4% / ≈ 11%). Smaller wins: one repair round, escalating to more reasoning only when the examples fail, and a draft-then-refactor variant settled by the metamorphic check (Qwen3-32B 91.5% at 0.8k tokens). Negative or partial: likelihood and probe-based helper filters, symmetric test generation from examples (catches 6% of wrong programs), model-written oracles, retrieved exemplars, fact mining from failures (7% → 21–40%, high variance), distillation on contest problems.

![Real contest geometry: cost-accuracy frontier](figs/fig9_contest_frontier.png)

![Routing at benchmark scale: facts compose](figs/fig10_routing_facts.png)

![Verify once, reuse: cost curve](figs/fig12_reuse_cost.png)

## 5. Plan

1. **High reasoning effort.** Replicate gpt-oss-120b at high effort (66%, one seed) with 3 seeds (running).
2. **Hidden contracts on real tasks.** Test F2 directly on a standard benchmark, beyond the one natural case found (a reader returning floats broke OR-Tools' integer contract).
3. **Write-up.** A failure-to-fix map with token costs: which failure → which fix (exact snippet, literal input, hint, sampling + check, reasoning, repair, reuse).
4. **Optional.** A closed API model, if access is available.

## 6. Limitations

The main effects were found on generated tasks; on real benchmarks F3 and F4 hold and F1 shrinks. The fixes (snippets, hints) are hand-written, and automatic versions (retrieval, fact mining) reproduce them only partly. Only open-weight models were tested, and some secondary results use one seed.

## Appendix. Files

`poc/run_geo_cross.py` (geometry), `poc/run_co.py` (optimization), `poc/run_cc.py` (contest problems), `poc/run_solomon.py` (Solomon routing), `poc/run_jssp.py` (job-shop), `poc/sft_lora.py` (LoRA), `poc/make_figures*.py` (figures); pre-registrations with results in `results/PREREG_*.md`; the earlier full-length version of this document in `results/archive/PROPOSAL_before_compact_2026-10-15.md`.
