# Tools, Facts, and Checks: When LLM-Written Geometry and Optimization Code Fails, and Which Fix to Use

*Graduate NLP course project proposal: computational geometry and combinatorial optimization*

> **About this file.** The single project document. The full chronological log, with every control and correction, is [results/FINDINGS.md](results/FINDINGS.md); longer earlier versions are in `results/archive/`.

## 0. Primer: how LLMs solve geometry and optimization problems

**Two problem families.** **Computational geometry (CG)** computes exact answers from coordinates (convex hull, polygon area, segment crossings, point in polygon, Delaunay triangulation); the hard parts are degenerate inputs (collinear or repeated points) and orientation (clockwise vs counter-clockwise). **Combinatorial optimization (CO)** picks the best of exponentially many discrete choices (knapsack, the travelling salesman problem (TSP), vehicle routing with capacities and time windows (VRPTW), graph colouring, job-shop scheduling); most are NP-hard: checking that a solution is *feasible* is easy, proving it *optimal* is not.

**Six ways an LLM attacks these problems:**

| # | Approach (who computes) | Representative work | Weakness |
|---|---|---|---|
| 1 | direct answer, possibly after reasoning (the LLM) | chain-of-thought (Wei et al., NeurIPS 2022); reasoning models (o1, DeepSeek-R1, gpt-oss) | arithmetic slips; worse on larger inputs |
| 2 | solutions improved from their scores (the LLM) | OPRO (Yang et al., ICLR 2024; a TSP case study) | small instances only |
| 3 | a program (Python) | PAL (Gao et al., ICML 2023); Program-of-Thoughts (Chen et al., TMLR 2023); AlphaCode (Li et al., Science 2022) | plausible but wrong algorithm or edge case |
| 4 | a formulation in solver code (CP-SAT, MILP, OR-Tools) | Logic-LM (Pan et al., EMNLP Findings 2023); NL4Opt (NeurIPS 2022), Chain-of-Experts (ICLR 2024), OptiMUS (ICML 2024), ORLM (2405.17743); routing: DRoC (ICLR 2025) | solver-API misuse; mis-modelled constraint |
| 5 | an evolved heuristic (an evaluator keeps the best) | FunSearch (Nature 2024); EoH (ICML 2024); ReEvo (NeurIPS 2024); AlphaEvolve (2506.13131); HeuriGym (2506.07972) | thousands of LLM calls per problem class |
| 6 | constructions for a symbolic prover | AlphaGeometry (Trinh et al., Nature 2024): 25 of 30 IMO problems | proofs, not computation on coordinates |

Approaches 3–5 are usually wrapped in a **sample–check–repair loop**: draw several programs, keep those that pass a check (the statement's examples, agreement between programs, feasibility), feed errors back (self-consistency and CodeT, ICLR 2023; AlphaCode's filtering; Self-Debugging, ICLR 2024). In practice CG is solved with approach 3 and CO with approaches 3 and 4, the setting of this project; approach 6 proves olympiad theorems, and approach 2 falls behind simple heuristics as TSPs grow.

**Worked example A: geometry.** *Report twice the area of an 8-vertex polygon*, posed as 8 copies with the same answer (shifted, rotated, mirrored, relabelled, shifted by 10⁹). Answering directly without thinking, Qwen3-8B gives **436** on the original (correct), **2944** shifted, **392** rotated, **728** mirrored, and runs out of its 2,048-token budget on the 10⁹ copy. Its program, the shoelace formula, is right on **all 8**:
```python
s = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]))
print(abs(s))   # twice the area, exact in integer arithmetic
```
Programs still fail, and that is this project's subject (Examples F1, F4a).

**Worked example B: optimization.** *Colour a 40-node graph with as few colours as possible* (Qwen3-8B, six graphs that each need 4). No direct answer is valid, and a hand-written heuristic uses 40 colours, one per node, on 3 of 6; a ten-line CP-SAT model (`m.Add(c[a] != c[b])` per edge, minimise the largest colour) finds and proves the optimal 4 on 5 of 6 after up to two repair rounds. Its first attempts crash on `model.Minimize(max(colors))`, Python's `max` on solver variables: a missing API fact (F3).

**This project** studies approaches 3 and 4 with that loop. Both are far from solved: one program per problem solves 12–57% of 311 real Codeforces geometry problems (Section 4.4).

## 1. Problem Statement

LLMs routinely solve algorithmic problems by writing programs that often look right and still fail; the common reflex is to add more to the prompt (helpers, documentation, reasoning tokens). **Research question:** which in-context additions make LLM-written CG and CO programs better or worse, why, and which cheap fix suits which failure, at what token cost?

1. **Tools.** Do correct but unneeded helpers change the code? Can a *needed* tool hurt?
2. **Facts.** For solver code, does the exact API usage beat a full manual, retrieval or more reasoning?
3. **Fix selection.** When to sample and check without labels, when to pay for reasoning? Can robustness be distilled into a fast model?

### 1.1 Why programs rather than direct answers

| Approach (no thinking) | Geometry: correct on all 8 versions | Geometry: same answer on equivalent inputs | Optimization: solved optimally |
|---|---|---|---|
| Direct answer (Qwen3-8B / 32B) | 22% / 23% | **0%** of instances | held-out problems: .06–.19 (Llama-70B .02) |
| Program, executed (Qwen3-8B) | **92–97%** | 50–100% per task (point in polygon lowest) | solver program with API snippet: .71–.97 |

Programs offload exact computation (21% of direct replies ran out of tokens doing arithmetic) and handle any input size: direct answers degrade (knapsack optimality gap 6% at 10 items → 48% at 80; TSP 9% at 8 cities → 139% at 20; cf. ZebraLogic's "curse of complexity"), while a ~350-token OR-Tools program costs the same at any size. Programs can be checked without labels (F4); direct answers are not even consistent (a 6-vertex hull gets 4, 10, 4, 4, 6, 6, 6, 11 on 8 equivalent versions). Solvers add decades of engineering (Example B), and LLMs see far more code than worked solutions (program-aided reasoning: PAL, Program-of-Thoughts, Logic-LM). The price is new failure modes (environment mismatch, solver-API misuse, degenerate inputs, unsound algorithms), all shaped by the prompt.

## 2. Background (Related Work)

Checked per finding on 2026-10-13 (verdicts and links: `results/RELATED_WORK.md`).

- **Context that steers or misleads code:** 2606.04057, 2609.14157, 2608.11888, 2503.20589, 2306.03438, CodeCrash 2504.14119; earlier GSM-IC, RAG-MCP, ToolRet.
- **Under-specified tools and contracts:** 2602.14878, DRAFT 2410.08197, ContractEval 2510.12047.
- **Documentation for solver code:** DRoC (ICLR 2025), CP-Bench 2506.06052, Jain et al. 2024, near-miss documents 2401.14887.
- **Priors over explicit specifications:** 2505.17225, 2507.14417, 2305.15507 (our VRPTW case looked like this but was an ambiguous field name in our own format string; F3).
- **Selection, confidence, compute allocation:** MBR-exec, CodeT, S*, incoherence 2507.00057, metamorphic prompts 2406.06864, instance perturbations 2607.16646, token confidence 2402.02047, 2610.11300, Coder-Reviewer, DART 2606.23181, brute-force oracles ALGO, ExeCRE 2608.04439.
- **Forgetting and self-replay:** 2510.18874, 2601.19897, 2501.14315, SDFT, RL's Razor. **Failure taxonomies:** 2406.08731, 2407.06153, 2403.08937.

**Gap.** Most mechanisms have close relatives; new here is the combination of exact metamorphic scoring, matched one-fact interventions (helper, contract, API call, input field) and fix-by-error-type comparison under token cost, plus logit evidence for helper steering, confidence inverted by helpers, own vs same-weights teacher replay, and behavioural failure labels from counterfactual re-runs.

## 3. Motivation

Code assistants receive tool catalogs and documentation dumps; if plausible tools silently change the algorithm, "give the model everything" is the wrong default. Exact oracles and proven optima make prompt effects measurable, and they are large: one helper takes convex hull from 97% to 8% (F1); a 5-line API snippet takes vehicle routing from .23 to .90 (F3).

## 4. Experiment Design

### 4.1 Setup

**Tasks**, all generated with exact references:

| Domain | Core | Held-out (designed after the first findings) | Harder, multi-step |
|---|---|---|---|
| Geometry | convex hull vertex count, polygon area ×2, point in polygon, segment-intersection count, closest pair | convexity test, points in a triangle, convex-polygon overlap; pre-registered (E2): Delaunay check, farthest pair | lattice points inside a polygon (Pick), area of a union of rectangles (sweep line), polygon clipping (exact rational intersection area) |
| Optimization | 0/1 knapsack, TSP, graph colouring, makespan scheduling | bin packing, vertex cover | capacitated vehicle routing (CVRP), VRPTW |

**Scoring.** Geometry: 8 equivalent versions per instance (translated, rotated, mirrored, permuted, scaled, offset by 10^9, degenerate), correct only if right on all 8. Optimization: share solved to the proven optimum (DP, Held–Karp, exact CP-SAT); OR-Tools solver arm with up to 2 repair rounds.

**Interventions.** Helper toolbox (needed helpers = K0, plus K extra, K up to 10; "K8" = 8 extras); hidden helper contracts; documentation variants and BM25 retrieval; hints; verified sampling; thinking; LoRA distillation.

**Models.** Qwen3 1.7B / 8B / 14B / 32B-AWQ; Llama-3.1-8B, Llama-3.3-70B; DeepSeek-R1-Distill-Llama-70B; gpt-oss-20b / 120b (low / medium / high effort). vLLM 0.10.2 on A100s, from 2026-10-13 vLLM 0.22 on RTX PRO 6000 Blackwell GPUs, which reproduced earlier cells' exact counts (e.g. VRPTW 27/30, 21/30, 8/30, 18/30, 0/30); one stack per comparison.

**Statistics and controls.** 300 programs per geometry condition (60 per task), 2–3 seeds for headline cells, paired bootstrap 95% CIs; helpers pre-defined at execution; a reference solution passes every harness (480/480); an output-extraction audit per model family. "Pre-registered": predictions written before the run (`results/PREREG_*.md`).

### 4.2 Pilot findings

Examples are real and shortened; F1, F4 and F5 use the same convex-hull instance (10 points, Qwen3-8B).

**F1. Extra helpers steer the algorithm choice. Thinking is one fix, but an expensive one, and not the only one.**

Change in % correct with 8 related but unneeded helpers (geometry, n = 300; helpers pre-defined at execution; `poc/rescore_figs.py`):

| Model | Without thinking | With thinking / reasoning |
|---|---|---|
| Qwen3-1.7B | +0.3, opposite per task: hull −53, area2 −28, closest pair +47, segments +28 (as measured −35.7: 185 of 214 crashes were uncopied helper calls) | −4.7 |
| Qwen3-8B / 14B / 32B | −14.3 / −7.7 / −13.3 (helpers also pre-defined in the prompt: 8B −12.3, 32B −15.0) | −1.5 / −0.5 / −3.0 |
| Llama-3.1-8B / 3.3-70B | −35.2 / +0.8 | – |
| R1-Distill-Llama-70B; gpt-oss-20b / 120b | – | 0.0; −0.7 to 0.0 (low, medium effort; at high effort 20b runs out of tokens in a quarter of programs) |

![Where robustness to plausible helpers appears](figs/fig7_distractor_by_model.png)

Mechanism (off-idiom drift; tests pre-registered):
- **The algorithm changes:** 44–75% of hull programs switch from the monotone chain to a failing Graham scan on the offered `polar_sort`; the toolbox makes the model's own helper-route programs 0.40–0.71 nats per token more likely in 100% of 180 instances, mostly at imports and helper names.
- **One helper is enough** (`results/PREREG_E4.md`): `polar_sort` + `collinear` take hull from 97% to 8% (8B) and 83% to 6% (32B); "non-suggestive" helpers, predicted harmless, cost 15–38 points. Unneeded API lines change nothing in optimization, and on lattice an extra `point_in_polygon` helps (Llama-70B 0 → 45 of 60).
- **New task (E2, farthest pair; `results/PREREG_E2.md`):** `convex_hull` + `polar_sort` cost Qwen3-32B 21.7 points (CI [−31.7, −11.7]); helpers that suggest no algorithm cost 46.7 through input parsing (64 of 66 failures read the count line as a point), fixed by showing the literal input (54 → 119 of 120).
- **Robust (B3, H1, L1):** a scope sentence (cf. 2609.14157) recovers 2–3% of the harm and System 2 Attention makes the core tasks 11 points *worse*; 2,000–20,000-point inputs double the harm (Qwen3-8B / 32B −30 / −35; gpt-oss at low effort 92–98% either way); an importable library described only by signatures still costs Qwen3-32B 19.3 points, even after a sentence (L2) stops Qwen3-8B importing functions the library lacks (8B −8.8, 32B −20.0).
- Our own methods against this harm (M1–M5): Section 4.4.

**Is the conclusion just "use thinking"? No.** Thinking works because the model picks its algorithm before writing; anything that fixes that choice works too, far cheaper (8B):

| Fix for the same harm | Accuracy | Output tokens per program |
|---|---|---|
| none (8 extra helpers, no thinking) | 76–78% (hull with the 2 worst helpers: 7%) | ≈0.8–1.1k |
| full thinking | 97% | ≈6k (≈15k on the example instance) |
| one-sentence algorithm hint, no thinking (hull, 2 worst helpers, 3 seeds) | 94% | ≈0.6k |
| distilled LoRA, no thinking (F5) | 98% | ≈0.35k |
| simply not offering the extras | 92–97% | ≈0.3k |

Thinking does *not* protect against hidden contracts (F2) or missing API facts (F3). The practical message is **tool design**: offer only needed helpers, name the intended algorithm, show one example input; reasoning is the fallback.

![Dose-response: harm grows with the number of extra helpers](figs/fig2_distractor_dose.png)

> **Example F1.** *Needed helper only*: the textbook monotone chain, correct on all 8 versions. *8 extra helpers*: the model copies all 11 helper definitions and builds a Graham scan on `polar_sort` (start point left in the list, a spurious collinear pass), wrong on all 8. *+ "Hint: Andrew's monotone chain …"*: correct at 563 tokens; *+ thinking*: correct at 15,168.

**F2. A needed tool with a hidden contract is a trap.**
- The lattice task's needed helper returns a *signed* area; models omit `abs` (`A = polygon_area2(poly) // 2`), so Pick's formula fails on clockwise input: Qwen3-32B drops from 44 to 9–15 of 60. Fixing the tool restores 46–49; a docstring warning does not (17–19; with "NEGATIVE for clockwise; use abs()", 38 of 60 programs switch to a brute force that miscounts boundary points). Thinking reduces but does not remove it (Qwen3-8B 52 vs 60, signed vs unsigned); without any helper, gpt-oss assumes counter-clockwise input in 35 of 45 clipping failures.
- **Replication (E2, pre-registered; Delaunay check: count triangles whose circumcircle strictly contains a point).** The needed `in_circle` helper notes tersely that triangles must be counter-clockwise. Qwen3-8B / 32B solve 1 / 3 of 120 with it and 109 / 106 with an orientation-free version; 92% / 97% of failures are wrong only on mirrored or relabelled copies. A spelled-out warning recovers 16% / 75% of the gap. Llama-3.3-70B and Qwen3-14B fall in too (8 and 4 of 120 with the helper), gpt-oss-20b does not (118 vs 117). Thinking removes it at 32B (118 vs 120), partly at 8B (51 vs 118), at 7.8–8.8k tokens vs ≈0.4k for fixing the helper. Neither self-written docs (B3) nor a verified behaviour sentence (M2) helps.

**F3. Solver code fails on missing API facts; only the exact fact fixes it.**

| Optimization (share optimal; 6-problem row: within 1%) | no doc | full sheet | exact snippet | best-of-3 with snippet |
|---|---|---|---|---|
| 6 problems, Qwen3-8B / 14B / 32B | .26 / .61 / .70 | .35 / .81 / .93 | .71 / .96 / .97 | 14B, 32B: 1.00 |
| CVRP, Qwen3-32B | .23 | .07 | .77–.90 | 1.00 |
| CVRP, Llama-3.3-70B | .40 | .60 | .83–.93 | 1.00 |
| VRPTW, Llama-3.3-70B | 0 | 0 | .60–.77 | .93 |
| VRPTW, Qwen3-32B | 0 | 0 | .10–.27 | .47 |
| VRPTW, gpt-oss-20b low / medium | .10 / .33 | .07 / – | .07–.17 / .57–.70 | .37 / .90 |
| VRPTW, gpt-oss-120b low / medium | .07 / .13 | – | 0 / .03–.07 | 0 / – |
| + literal input, gpt-oss-20b low / medium | .33 / .50 | – | **.80–.97 / .90–1.00** | **1.00 / 1.00** |
| + literal input, gpt-oss-120b low / medium | .70 / .77 | – | **.97–1.00 / 1.00** | **1.00 / 1.00** |
| + literal input, Qwen3-32B / Llama-70B | 0 / 0 | – | .37–.50 / .67–.77 | .83 / .97 |

- The 5-line exact snippet beats the full manual at every size, also on held-out problems. **A near-miss reference is as bad as none:** with the full sheet (TSP routing without capacities) Qwen3-32B invents `RegisterUnaryLongLivingCallback` (CVRP .07) where the snippet's `RegisterUnaryTransitCallback` reaches the optimum; the CVRP snippet gives VRPTW 0 (Llama-70B, Qwen3-32B) and .07 (gpt-oss-20b low).
- **Correction (2026-10-13): the VRPTW "skipped field" was an ambiguous header in our own prompt.** We wrote `n capacity K service horizon`; gpt-oss-120b read `n capacity K horizon` (0–3 of 30 programs parse `service`; restating the fields, it treats "service horizon" as one compound noun), so the horizon became 10 and the solver reported infeasible. With the field removed, 43 of 49 are optimal; with `n capacity K service_time horizon`, 120b low gets 30/30 and 30/30, 20b low 29/30, 29/30 (F3y): an ambiguity in our spec, not a prior overriding a clear specification. An audit of all 22 format strings (A1) finds only this header misread systematically (gpt-oss-120b, gpt-oss-20b, Qwen3-8B in 3 of 3 samples).
- **Showing the literal input disambiguates it, with fewer tokens:** with the snippet, 120b low goes 0 → .97–1.00 (4.8k → 1.7k tokens per instance), 120b medium .07 → 1.00 (10.7k → 3.7k), 20b low .07–.17 → .80–.97; field-skipping programs drop from 18–29 of 30 to 0–3. Asking for a restatement does not help (gpt-oss 0–2 of 30).
- **Reasoning cannot replace the fact:** thinking without documentation gives 14B / 32B / R1-Distill-70B .33 / .03 / .00 on CVRP at 11–19k tokens per program (vs .97 / .97 / .90 with the snippet). **Retrieval works only when precise:** BM25 top-1 matches the hand-written snippet (32B .965 vs .956), top-3 adds near-misses (CVRP .78 → .55); DRoC-style retrieval (B4) beats plain top-3 (+.12 to +.15) but not the snippet (−.12 to −.40).
- *Scoring check:* accepting the 293 TSP failures that return to the start city (281 optimal) would raise Qwen3-32B (no doc) .70 → .83 and Llama-70B (no doc / full sheet / snippet) .33 / .55 / .87 → .54 / .73 / .99; the ordering holds.

![Optimization documentation: exact snippet vs full sheet](figs/fig5_co_docs.png)

**F4. Choose the fix by error type (efficiency).** Tests pre-registered.

| Situation | Sampling + label-free check | Thinking | Verdict |
|---|---|---|---|
| Geometry, clean prompt (8B) | best-of-3: **100** at ≈0.9k tokens | 91 at 5.5k | errors vary between samples → sample and check |
| Geometry, 8 extra helpers (8B) | best-of-3: 84 at 2.5k | 1k budget: 87 at 1.6k; full: 97 at 5.8k | same error in every sample → reason |
| Hard geometry, lattice + rectunion (8B, of 120) | best-of-3: 44 at ≈1.7k | 1k budget: 97 at ≈1.8k | systematic → reason |
| Optimization (8B) | best-of-3: .72 | .87 at 5.9k | systematic API misconceptions → reason or state the fact |
| Optimization (14B / 32B) | best-of-3: 1.00 at ≈⅓ of thinking's tokens | .98–1.00 | independent slips → sample |

- **Budgets:** ≈1k thinking tokens recover most geometry accuracy (lattice 8B 12 → 58 of 60); optimization needs far more (TSP stays at 0 with 2k). gpt-oss-20b at low effort reaches ≈99% at ≈0.4–0.9k tokens; at high effort 27% of programs never finish within 24k.
- **Published selectors (B1):** among the same 3 candidates (Qwen3-8B; clean / 8 extra helpers / hard), our metamorphic check picks a correct program 99.7 / 83.3 / 33.3% of the time, CodeT 96.0 / 82.7 / 26.7, and a vote on the given input, MBR-exec and DeepConf less: fresh random inputs miss the sign and orientation errors that mirrored copies of the given instance expose (no leakage: the same on 5 fresh instances).
- **Confidence cannot replace the check (C1):** the most confident of 3 gains +1.0 [−1.1, +3.1] vs +7.0 for the check; log-probability prefers the wrong Graham scans under helpers (AUROC 0.43; clean 0.68, hard 0.40); Qwen3-32B replicates (check 6.7–22.5 points better).
- **A check-gated pipeline loses on systematic errors (E3, `results/PREREG_E3.md`):** one program, then 3 samples + check if it fails, then a 1,024-token thinking budget. With needed helpers only (Qwen3-8B): 98.0% at 365 tokens per instance (full thinking 100% at 3,792); under 8 extra helpers / on hard tasks only 84.7% / 53.3%, **below a fixed 1,024-token budget** (93.0% / 80.8% at about the same 1.6k / 1.7k tokens): the check accepts programs wrong the same way on every copy. A same-model brute-force reference (E3b) catches 86–90% of these at the budget's cost but fails on the hardest task (lattice 1 of 60).

![Fixes under a broad toolbox](figs/fig8_fixes_under_distractors.png)

> **Example F4a: a slip** (Qwen3-8B, polygon area, clean prompt): one of 3 samples parses coordinates with `float()` (products near 1e18 lose precision), wrong only on the copy shifted by 10^9; the samples disagree on transformed copies of the *given* instance, so the check keeps an integer program (3 × ≈0.3k tokens). **F4b: systematic** (F1 instance, 8 extra helpers): all 3 samples take the `polar_sort` route; nothing correct to select. **F4c: fixes compose** (gpt-oss-20b low, polygon clipping): `cross(cp1, cp2, e) >= 0` assumes a counter-clockwise clipping polygon, so the program prints 0 on mirrored and reversed copies; one sample solves 14 of 60, the check 28, the hint "orient both polygons counter-clockwise first" 44, hint + 3 checked samples **59** (≈2.8k tokens in total).

**F5. Robustness can be distilled into a fast model per task; replaying the student's own programs protects the other tasks.** Tests pre-registered.
- LoRA on Qwen3-8B with 600 verified programs it wrote *with* thinking (0/4/8 extra helpers): under 8 extra helpers 77.0 → **98.0** (+21.0 [+17.8, +24.3], 2 seeds) at ≈350 tokens instead of ≈6k (Example F1: monotone chain in 249 tokens vs the base's wrong `polar_sort` hull in 1,067); clean-prompt training gives no gain. **Collateral damage:** unseen tasks get slightly worse (58.6 → 52.2); an unseen fragile task can collapse even on clean prompts (hull 97 → 28–34, mostly Graham-scan variants).
- **Self-replay removes the damage (E4, `results/PREREG_E4_REPLAY.md`):** leave-hull-out LoRA, clean-prompt hull: base 109/120, no replay 48, **+ 270 of the student's own verified no-thinking programs on 5 other tasks: 118**, + the thinking teacher's programs for the same 270 prompts: 36 (self − teacher +68.3 [+60.0, +76.7]); in-task robustness kept (240/240); monotone chain in 120/120 hull programs (no replay 59, teacher replay 49). On the new Delaunay task both replay arms still drop (59 → 47 / 45 of 60).
- **Established remedies (B2):** WiSE-FT trades hull against the in-task gain, SDFT halves the damage (85), self-training alone gives 104 / 235; only self-replay keeps both (118 / 240). It replicates with convex held out (E4b: 81 → 80 of 120; teacher replay 42) and with a second training seed (R1: self vs teacher replay, hull 118 vs 28, convex 85 vs 34).

**E1. Where the failures come from, and which fix repairs which kind.** Each of the 14,822 failing programs (47,868 programs, 388 runs) got one class from behaviour only (which versions fail, the exception on re-run, counterfactual re-runs); reading 8 programs per class confirmed 127 of 128 geometry and 85 of 97 optimization labels (`poc/analyze_e1_taxonomy.py`, `results/E1_TAXONOMY_DRAFT.md`).

| | algorithmic (logic, orientation, degenerate, precision) | API / knowledge | input format | packaging / interface (helpers) | other |
|---|---|---|---|---|---|
| Geometry, 9,846 failures | **72%** (hard tasks 81–87% in every family) | – | 1% | 12% (52% for Qwen3 no-thinking when a toolbox is offered) | 16% |
| Optimization, 4,976 failures | 29% (modelling / logic) | **51%** (Qwen3 58%) | 8% (all VRPTW; gpt-oss's failures are 53% input format, caused by the ambiguous header, see F3) | – | 12% (6% output format) |

Fix map (same instance after one fix; re-sampling rescues 9–52%): **API fact → exact snippet** (618 of 1,042; thinking 91 of 240); **input format → one literal input** (75 of 94); **orientation → hint** (188 of 221); **logic → thinking** (476 of 544) or a hint (810 of 1,204), not sampling + check (204 of 914); **precision → sampling + check** (46 of 55); **degenerate cases → thinking** (23 of 27; the check rescues 0 of 70); **wrong helper signatures → one contract sentence** (61 of 83); **uncopied helpers → pre-define them** (329 of 630).

### 4.3 Experiment status (2026-10-15)

| Experiments | Status |
|---|---|
| E1–E4, C1, E3b, E4b, R1, A1, L1 | done (Section 4.2) |
| B1–B4: published baselines (CodeT, MBR-exec, DeepConf, WiSE-FT, SDFT, self-SFT, scope sentence, S2A, DRoC-style retrieval) | done: none beats our fixes (`results/PREREG_B1.md`–`B4.md`) |
| H1–H6 (harder problems); M1–M5, N1–N6, FM, V1–V3, D1–D3 (methods) | done (Section 4.4) |
| E5: a closed API model | not run (no API access) |

### 4.4 Hard benchmarks (added 2026-10-14; `results/PREREG_H1.md`–`H6.md`)

Generated tasks are easy for reasoning models (H1: gpt-oss 92–98% even with 20,000-point inputs), so we re-tested on standard sets.

| Benchmark | Result |
|---|---|
| 311 Codeforces geometry problems (CodeContests, official tests, references re-validated; H2c) | Qwen3-32B no-think / think-1,024 / full thinking 12 / 22 / 30% (corrected: 29.3% under strict answer extraction); gpt-oss-20b low / medium 38 / 47%; gpt-oss-120b low / medium 46 / 57%; problems rated ≥ 2300 below 35% for every single attempt |
| 56 Solomon VRPTW instances, 100 customers (H3) | without facts 0–6% feasible (gpt-oss-120b medium 46–50%); with a correct reader + the robust solver snippet gpt-oss-120b 100% (median gap 1.5%), gpt-oss-20b 44–64%, Qwen3-32B ≤ 5% |
| 40 job-shop instances (la01–la40, CP-SAT; H5) | 79–85% feasible with no facts, optimal when feasible (after fixing a CPU-time-limit bug in our sandbox that had reported multi-threaded CP-SAT as timeouts) |
| Newest local model, Qwen3.8-27B (H6) | contest no-think 33%, thinking (effort low) 44%, both cap-limited (48% / 51% with a 28k cap); × 3 + example check 45%; helpers no effect; Solomon 9 / 46 / 81% (none / docs / reader + robust): the same picture; its no-think answers reason in plain text, and asked for code only it moves the reasoning into comments (−14% tokens, −2 points) |

- **Fix selection (F4) holds.** The statement's examples are the cheap label-free check (3 samples recover most of the gap to the best sample; MBR-exec adds ≈ 1 point). For gpt-oss-20b, samples + check or one repair round beat medium effort; for gpt-oss-120b one medium attempt beats three low ones; Qwen's think-1,024 × 3 + check equals full thinking at 64% of the tokens (Figure 9).
- **Facts (F3) hold and compose.** The file layout, "OR-Tools takes integers everywhere" (models write `1e7`) and a first-solution strategy for tight time windows are each needed and alone do little (Figure 10); the textbook CP-SAT job shop needs no facts.
- **Helpers (F1) shrink.** gpt-oss-20b low loses 4.3 points with 8 related helpers (p = 0.001), mostly by reasoning less; unrelated helpers or a "most are not needed" header cost ≈ 2 (n.s.); Qwen3-32B and gpt-oss-120b are unaffected (Figure 11).

**Methods tested (all pre-registered; prior art checked first).** M1–M5 target the helper harm (synthetic tasks, Qwen3-8B / 32B, pooled over 7 tasks); N1–N6 and D1–D3 contest geometry; FM routing. Files: `results/PREREG_M1.md`, `PREREG_M2_M4.md`, `PREREG_M5.md`, `PREREG_N.md`, `PREREG_FM.md`, `PREREG_V.md`, `PREREG_D1.md`.

| Method | Idea | Closest prior art | Result with cost | Verdict |
|---|---|---|---|---|
| M1 likelihood filter | drop helpers that lower the no-helper draft's likelihood | ContextCite | needed `orient` scores as low as harmful `polar_sort` | negative (calibration fails) |
| M2 contract probe | add an execution-verified behaviour sentence per helper | DRAFT | Delaunay 0 / 10 of 120 (8B / 32B) vs hand-written warning 18 / 80 | negative |
| M3 per-helper probe | keep helpers whose single-helper program is consistent | TroVE | keeps `polar_sort` (consistent but wrong); 8B 80.0% at 6–10k tokens | negative |
| M4 algorithm first | write without helpers, then refactor to use them | De-Hallucinator | core 8B 579 vs 468 of 600 at ≈0.8k tokens; pooled 89.0 / 85.2% vs think-1,024 94.5 / 90.0% at half the tokens; keep-the-algorithm sentence: no effect | helps; thinking better |
| M5-V2 | if M4's draft and rewrite disagree, keep the one passing the metamorphic check | TroVE-style vote (91.2 / 95.0% at ≈2.6k / 1.8k, strongest) | 32B 91.5% at ≈0.8k vs think-1,024 90.0% at 1.6k; 8B no gain | small win (32B) |
| Self-replay (F5) | add the student's own programs to LoRA data | replay, SDFT | held-out hull 118 of 120 (no replay 48, teacher replay 36) | works (synthetic) |
| N1 example augmentation | derive labelled tests from examples by symmetry | MR-Adopt | catches 6% of wrong example-passers; 475 tokens per problem | negative (contest errors survive symmetries) |
| N2 one repair round | return the first failing example once | Self-Debugging | gpt-oss-120b low 46.0 → 53.1% at 4.6k tokens; +5.5 to +7.1 points for +0.8–1.4k; rounds 2 / 3 add +2.3 / +0.6 (gpt-oss-20b; 3 rounds = 3 samples + check, 47.9%, at 76% of the tokens) | works: best per token |
| N3 cascade | escalate only when examples fail | FrugalGPT | gpt-oss-20b +2.7 points at 13% fewer tokens than medium | works (exploratory) |
| N4 repair, then escalate | N2, then N3 | N2 + N3 | ≈1 point above N3 (gpt-oss-20b 51.6% at 7.3k) | marginal |
| N5 approximate oracle | model-written slow oracle flags mismatches | ALGO | flags 53–68% of wrong example-passers at ≈4% false alarms; < 1 point as selector or repair trigger; oracle 1.5–2.9k tokens per problem | negative (bottleneck: producing a correct program) |
| N6 retrieved exemplar | add one retrieved solved problem | SolveRank | 3 seeds: gpt-oss-120b +1.2 points (p = 0.39), gpt-oss-20b −2.0 (p = 0.14) | negative; corrected: seed 1 (132 → 147, p = 0.03) did not replicate |
| FM / FM2 / FM3 fact mining | keep model-proposed facts that execution verifies | Dynamic Cheatsheet | gpt-oss-120b, held-out Solomon 7% → 21–40% (one chain 65%), ≈300k mining tokens per chain; no help for 20b or from pooling | partial negative (noisy verification; prose, not code) |
| V1 verify once, reuse | choose one program on training instances, reuse it | FunSearch, HeuriGym | routing (8 training instances): gpt-oss-120b 45 of 48 held-out (94%, gap 1.4%), 28k tokens in total vs 7% per instance at 1.8k each; reader + robust: both gpt-oss 48 of 48; 20b without facts needs 64 candidates (94%, 107k); Qwen3-32B none. Job-shop: both gpt-oss 32 of 32 (15k / 28k tokens). Synthetic (V1G, 8 helpers, 5 instances with known answers): hull 17–21% per instance → 100% on 55 held-out; a wrong closest-pair program passed the 5 checks (78%), breaking ties by output agreement on 10 unlabelled inputs gives 100% on all 10 task-model pairs | works if one candidate works |
| V2 / V3 repair, then reuse | repair on training failures first | OptiMUS | 20b 0 → 94% once, not recurring; Qwen3.8 "repaired" into a greedy heuristic (routes 56% longer); a quality guard (V3) finds nothing better | negative (feasibility-only check rewards giving up) |
| V1A model-written oracle | label-free choice by the model's brute-force oracle | ALGO + V1 | hull: Qwen3-32B oracle correct, reuse 100%; Qwen3-8B oracle wrong (prints 3 everywhere), reuse 0% (5 known answers: both 100%; metamorphic choice: 8B 0%) | needs a correct oracle |
| D1–D3 contest distillation | LoRA Qwen3-8B on verified teacher, own or hinted-own programs | STaR; Li et al. 2025 | 431 teacher programs (206 problems): 12.1 → 4.8% held-out (self-replay 3.5%); clean 88-problem split (base 12.9–14.6%): comments restored 6.8% (p = 0.007), solvable problems only 5.3%, own 63 answers 15.2%, hinted own (D3) 11.0% | negative: idiom drift (12 → 5 comment lines) |

**In short:** V1 reuse works whenever one candidate works and a reliable selector exists (so per-instance generation understates these models), as do N2 repair, the N3 cascade, M5-V2 (small, 32B only) and self-replay (F5); M1–M3, N1, N5, N6, V2/V3 and contest distillation are negative, fact mining partially, V1A only for the stronger model.

![Real contest geometry: cost-accuracy frontier](figs/fig9_contest_frontier.png)

![Routing at benchmark scale: facts compose](figs/fig10_routing_facts.png)

![Unneeded helpers on real problems](figs/fig11_helpers_real.png)

## 5. Limitations

1. **Synthetic tasks.** The main effects were found on generated tasks; on standard benchmarks (Section 4.4) F3 and F4 hold, F1 shrinks to a small effect for one model, and F2 was not re-tested directly (one natural instance: our float-returning reader broke OR-Tools' integer contract).
2. **Partly post-hoc mechanism.** Off-idiom drift was formed after seeing the data; pre-registered tests confirmed its core but refuted the similarity-based predictions.
3. **Oracle fixes.** Snippets and hints are hand-written; retrieval matches them only when it fetches the exact page, and the label-free check misses transformation-invariant errors (E3).
4. **Coverage.** Open-weight models only (three families; E5 not run); some secondary cells are single-seed.

## Appendix A. Code and How to Run

```
poc/run_geo.py, run_geo_cross.py   geometry tasks, variants, oracles, harness
poc/geo_distractors.py             helper pool, toolbox
poc/run_co.py                      optimization problems, references, solver harness, retrieval
poc/mr_select.py, fresh_eval.py    label-free selection (metamorphic check)
poc/logit_probe2.py                token-level probe
poc/sft_lora.py                    LoRA distillation
poc/sanity_check.py                reference passthrough
poc/rescore_figs.py, make_figures.py   packaging-free re-scoring, figures
poc/analyze_vrptw_stdin.py         VRPTW input-format counterfactual
poc/analyze_c1.py, analyze_e2.py, analyze_e3.py, analyze_e4.py   C1, E2, E3, E4 analyses
results/FINDINGS.md                full log;  results/PREREG_*.md  pre-registrations with results
```

Typical runs (vLLM server, OpenAI-compatible API at `POC_BASE_URL`):

```
python poc/run_geo_cross.py --model_tag X --stdlib --n_inst 30 --temperature 0.7 --seed 1 --distract 8 [--think | --algo_hint | --show_stdin | --logprobs]
python poc/run_geo_cross.py ... --tasks delaunay --distract 0 --incircle signed|doc|fixed
python poc/run_co.py --model_tag X --arms solver --probs cvrp --n_inst 10 --repair 2 --api_doc --api_doc_task [--retrieve 1]
MR_PREFIX=X_geox python poc/mr_select.py <model> 1 base@1,base@2,base@3
```

## Appendix B. Example Prompt

Prompt format of the geometry runs (convex hull with 8 extra helpers; only `orient` is needed):

```text
Points: (20,-40) (-26,-18) (-18,-12) (-50,38) (-18,42) (58,16) (-30,-26) (6,58) (52,-36) (50,14)
How many vertices does the convex hull of these points have? Points lying on a hull edge (collinear)
are not vertices; duplicate points count once.
Write a Python 3 program that solves this problem for any input in the following stdin format: …
You may (and should) use these tested helper functions; copy the ones you use into your program unchanged:
  on_segment, closest_pair_sq, point_in_polygon, polar_sort, bbox, is_convex,
  segments_intersect, dist2, orient, collinear        (full definitions shown in the prompt)
```
