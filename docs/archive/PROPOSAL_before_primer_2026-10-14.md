# Tools, Facts, and Checks: When LLM-Written Geometry and Optimization Code Fails, and Which Fix to Use

*Graduate NLP course project proposal: computational geometry and combinatorial optimization*

> **About this file.** The single project document. The full chronological log, with every control and correction, is [docs/FINDINGS.md](docs/FINDINGS.md); longer earlier versions are in `results/archive/`.

## 1. Problem Statement

LLMs routinely solve algorithmic problems by writing programs: a convex hull, a point-in-polygon test, a vehicle-routing solver model. The programs often look right and still fail, and the common reflex is to add more to the prompt: helpers, documentation, reasoning tokens.

**Research question.** Which in-context additions make LLM-written programs for computational geometry (CG) and combinatorial optimization (CO) better or worse, why, and which cheap fix suits which failure, at what token cost?

1. **Tools.** Do correct but unneeded helper functions change the code, and how? Can a *needed* tool hurt?
2. **Facts.** For solver code, does the exact API usage beat a full manual, retrieval or more reasoning?
3. **Fix selection.** When to sample and check without labels, when to pay for reasoning? Can robustness be distilled into a fast model?

### 1.1 Why LLMs solve algorithmic problems by writing programs

An LLM can also answer directly ("the hull has 7 vertices"). In our pilot this fails badly:

| Approach (no thinking) | Geometry: correct on all 8 versions | Geometry: same answer on equivalent inputs | Optimization: solved optimally |
|---|---|---|---|
| Direct answer (Qwen3-8B / 32B) | 22% / 23% | **0%** of instances | held-out problems: .06–.19 (Llama-70B .02) |
| Program, executed (Qwen3-8B) | **92–97%** | 50–100% per task (point in polygon lowest) | solver program with API snippet: .71–.97 |

1. **Exact computation is offloaded.** 21% of direct replies ran out of tokens doing arithmetic; for a polygon with doubled area 436, Qwen3-8B answers 436, 2944, 392 and 728 on the original, shifted, rotated and mirrored copies; the executed program is right on all 8 versions.
2. **One program handles every input size.** Direct answers degrade with size (knapsack optimality gap 6% at 10 items → 48% at 80; TSP 9% at 8 cities → 139% at 20), the "curse of complexity" also seen in ZebraLogic; a ~350-token OR-Tools program costs the same at any size.
3. **Programs can be checked without labels**, enabling verified sampling (F4); direct answers are not even consistent (no instance got the same answer on its 7 equivalent versions; a 6-vertex hull gets 4, 10, 4, 4, 6, 6, 6, 11, while the program prints 6 on all 8).
4. **Solvers reuse decades of engineering**: the model only *formulates*. On six 40-node graphs that need 4 colours, no direct colouring is valid; the CP-SAT model finds the optimal 4 on 5 of 6.
5. **LLMs see far more code than worked solutions** in training; program-aided reasoning (PAL, Program-of-Thoughts, Logic-LM) is established.

The price, studied here, is new failure modes (environment mismatch, solver-API misuse, degenerate inputs, unsound algorithms), all shaped by the prompt.

## 2. Background (Related Work)

Checked per finding on 2026-10-13; full table with verdicts and links: `docs/notes/RELATED_WORK.md`.

- **Context that steers or misleads code** (2606.04057; 2609.14157; 2608.11888; 2503.20589; 2306.03438; CodeCrash 2504.14119; earlier GSM-IC, RAG-MCP, ToolRet): prompt cues, unneeded tools, plausible skills and misleading code degrade generated code. *Ours:* correct but unneeded helpers collapse accuracy, with logit evidence, a dose-response, reasoning-model immunity and an input-parsing channel.
- **Under-specified tools and contracts** (2602.14878; DRAFT 2410.08197; ContractEval 2510.12047). *Ours:* matched with and without its precondition, the needed helper is worse than none in 4 models from 2 families.
- **Documentation for solver code** (DRoC, ICLR 2025; CP-Bench 2506.06052; Jain et al. 2024; near-miss documents 2401.14887). *Ours:* an exact snippet beats the full manual and reasoning at matched cost.
- **Priors over explicit specifications** (2505.17225; 2507.14417; 2305.15507). *Ours, corrected:* our VRPTW case looked like this but was an ambiguous field name in our own format string (F3); what remains is the diagnosis method (counterfactual re-run, format restatement).
- **Selection, confidence and compute allocation** (MBR-exec, CodeT, S*, incoherence 2507.00057; metamorphic prompts 2406.06864; instance perturbations 2607.16646; token confidence 2402.02047, 2610.11300, Coder-Reviewer; DART 2606.23181; brute-force oracles ALGO, ExeCRE 2608.04439). *Ours:* consistency on transformed copies of the given instance; confidence inverted by helpers; check-gated routing that loses to a fixed thinking budget.
- **Forgetting and self-replay** (2510.18874; 2601.19897; 2501.14315; SDFT; RL's Razor). *Ours:* own vs same-weights teacher programs on the same prompts, with visible idiom drift.
- **Failure taxonomies of LLM code** (2406.08731; 2407.06153; 2403.08937). *Ours:* behavioural labels from counterfactual re-runs; a class-to-fix map.

**Gap.** Most mechanisms have close relatives that must be cited; new here is the combination of exact metamorphic scoring, matched one-fact interventions (helper, contract, API call, input field) and fix-by-error-type comparison under token cost.

## 3. Motivation

1. **Practical.** Code assistants receive tool catalogs and documentation dumps; if plausible tools silently change the algorithm, "give the model everything" is the wrong default.
2. **Measurable.** Exact oracles and proven optima make small prompt effects measurable.
3. **Large pilot effects** (Section 4.2): one helper takes convex hull from 97% to 8%; a 5-line API snippet takes vehicle routing from .23 to .90 (reasoning alone: .03).

## 4. Experiment Design

### 4.1 Setup

**Tasks**, all generated with exact references:

| Domain | Core | Held-out (designed after the first findings) | Harder, multi-step |
|---|---|---|---|
| Geometry | convex hull vertex count, polygon area ×2, point in polygon, segment-intersection count, closest pair | convexity test, points in a triangle, convex-polygon overlap; pre-registered (E2): Delaunay check, farthest pair | lattice points inside a polygon (Pick), area of a union of rectangles (sweep line), polygon clipping (exact rational intersection area) |
| Optimization | 0/1 knapsack, TSP, graph colouring, makespan scheduling | bin packing, vertex cover | capacitated vehicle routing (CVRP), VRP with time windows (VRPTW) |

- **Geometry evaluation:** 8 equivalent versions per instance (translated, rotated, mirrored, permuted, scaled, offset by 10^9, degenerate); a program is correct only if right on all 8.
- **Optimization evaluation:** share solved to the proven optimum (DP, Held–Karp, exact CP-SAT); OR-Tools solver arm with up to 2 repair rounds.

**Interventions.** helper toolbox (needed helpers = K0, plus K extra, K up to 10); hidden helper contracts; documentation variants and BM25 retrieval; hints; verified sampling; thinking; LoRA distillation.

**Models.** Qwen3 1.7B / 8B / 14B / 32B-AWQ; Llama-3.1-8B, Llama-3.3-70B; DeepSeek-R1-Distill-Llama-70B; gpt-oss-20b / 120b (low / medium / high effort). vLLM 0.10.2 on A100s; from 2026-10-13 vLLM 0.22 on RTX PRO 6000 Blackwell GPUs, which reproduced earlier cells' exact counts (e.g. VRPTW 27/30, 21/30, 8/30, 18/30, 0/30); each comparison uses one stack.

**Statistics and controls.** 300 programs per geometry condition (60 per task), 2–3 seeds for headline cells, paired bootstrap 95% CIs. Helpers are pre-defined at execution (an uncopied helper call is no failure); a reference solution passes every harness (480/480); each new model family gets an output-extraction audit.

### 4.2 Pilot findings

Each finding ends with a real, shortened example (`…` marks omitted lines); F1, F4 and F5 use the same convex-hull instance (10 points, Qwen3-8B).

**F1. Extra helpers steer the algorithm choice. Thinking is one fix, but an expensive one, and not the only one.**

Change in % correct with 8 related but unneeded helpers (geometry, n = 300; helpers pre-defined at execution; `poc/rescore_figs.py`):

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

Mechanism (off-idiom drift):
- **The algorithm changes:** 44–75% of hull programs switch from the monotone chain to a failing Graham scan on the offered `polar_sort`.
- **One helper is enough** (pre-registered, `docs/prereg/PREREG_E4.md`): `polar_sort` + `collinear` take hull from 97% to 8% (8B) and 83% to 6% (32B). The registered prediction that "non-suggestive" helpers are harmless failed (they cost 15–38 points).
- **Visible in the logits:** the toolbox makes each model's own helper-route programs 0.40–0.71 nats per token more likely in 100% of 180 instances, mostly at imports and helper names.
- **Domain contrast:** 8 unneeded API lines change nothing in optimization; on the lattice task the extra `point_in_polygon` even helps (Llama-70B 0 → 45 of 60).
- **Pre-registered new task (E2, farthest pair; `docs/prereg/PREREG_E2.md`).** With `convex_hull` + `polar_sort`, Qwen3-32B writes hull-based code in 97% of programs and loses 21.7 points (CI [−31.7, −11.7]). Helpers that suggest no algorithm cost more (46.7 points) through input parsing: 64 of their 66 failures read every input line, including the stated count line, as a point; showing the literal input (the F3 fix) removes them (54 → 119 of 120). The registered prediction "only algorithm-suggesting helpers hurt" failed for 32B.
- **Published context fixes do not undo it (B3, pre-registered):** a scope sentence (cf. 2609.14157) recovers 2–3% of the harm; System 2 Attention makes the core tasks 11 points *worse* and fixes only the parsing channel (54 → 98 of 120).
- **It grows with problem size (H1, pre-registered):** with 2,000–20,000 points and a 10-second limit, all helpers cost Qwen3-8B / 32B 30 / 35 points (hull 80 → 14 of 80), twice the small-input harm; gpt-oss at low effort still solves 92–98% with or without helpers.
- **It does not need pasted code (L1, pre-registered):** offered as an importable library described only by signatures and one-line docs, the same extras cost Qwen3-32B 19.3 points (hull 104 → 32 of 120, `polar_sort` imported in 84 of 120 hull programs). Qwen3-8B adds a new failure: it imports functions the library does not have (`from geomlib import convex_hull` in 53 of 54 failed hull programs). One sentence ("the module contains exactly these functions", L2) removes those imports (106 → 3 programs; hull 13 → 103 of 120) but not the steering (8B then loses 8.8 points with the extras, 32B 20.0).
- **Methods we built and tested (pre-registered; prior art checked first; `docs/prereg/PREREG_M1.md`, `PREREG_M2_M4.md`).** A likelihood filter (drop helpers that lower the probability of the model's own no-helper draft; M1) fails at calibration: it flags needed helpers as strongly as harmful ones. Writing the program *before* seeing the helpers and then refactoring it to use them (M4) is cheap and strong where the harm is steering (core tasks, 8B: 579 of 600 vs 468 with all helpers, at ≈0.8k tokens) but loses to a 1,024-token thinking budget overall (pooled 89.0 vs 94.5% for 8B, 85.2 vs 90.0% for 32B, at about half the tokens); the keep-the-algorithm sentence itself adds nothing. Probing each helper with its own program (M3) keeps `polar_sort`, whose wrong programs are consistent, and costs 6–10k tokens. The strongest method is published: TroVE-style voting over samples written with and without the toolbox (91.2 / 95.0% pooled), because the two contexts fail on different tasks. A cheap variant of ours (M5: when the M4 draft and rewrite disagree, keep the one that passes the metamorphic check) reaches 91.5% for 32B at ≈0.8k tokens, above the thinking budget (90.0% at 1.6k); for 8B it adds nothing.

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

> **Example F1** (Qwen3-8B, same instance, four conditions). *Needed helper only*: the textbook monotone chain, correct on all 8 versions.
> ```python
> points = sorted(set(points))
> for p in points:
>     while len(lower) >= 2 and orient(lower[-2], lower[-1], p) <= 0:
>         lower.pop()
>     lower.append(p)
> … (same for the upper hull)
> return lower[:-1] + upper[:-1]
> ```
> *8 extra helpers*: the model copies all 11 helper definitions and builds a Graham scan on `polar_sort` (start point left in the list, a spurious collinear pass); wrong on all 8.
> ```python
> left = min(points, key=lambda p: (p[0], p[1]))
> sorted_points = polar_sort(points, left)        # the offered helper decides the algorithm
> hull = [left, sorted_points[0]]                 # sorted_points still contains `left`
> …
> for i in range(len(hull)):                      # extra pass suggested by `collinear`
>     a, b, c = hull[i-2], hull[i-1], hull[i]
>     if orient(a, b, c) != 0:
>         final_hull.append(hull[i])
> ```
> *Same helpers + "Hint: Andrew's monotone chain …"*: monotone chain, correct, 563 tokens. *Same helpers + thinking*: the same at 15,168 tokens.

**F2. A needed tool with a hidden contract is a trap.**
- The lattice task's needed helper returns a *signed* area; models omit `abs`, and Pick's formula fails on clockwise input: Qwen3-32B drops from 44 to 9–15 of 60. Fixing the tool restores 46–49; a docstring warning does not (17–19).
- Reasoning reduces but does not remove it (Qwen3-8B with thinking 52 vs 60, signed vs unsigned; R1-Distill-70B with the toolbox 57 → 42). Without any helper, gpt-oss assumes counter-clockwise input in 35 of 45 clipping failures.
- **Pre-registered replication (E2, Delaunay check: count triangles whose circumcircle strictly contains a point).** The needed `in_circle` helper notes tersely that triangles must be counter-clockwise. Qwen3-8B / 32B solve 1 / 3 of 120 with it (32B with no helper: 55) and 109 / 106 with an orientation-free version; 92% / 97% of the failures are wrong only on mirrored or relabelled copies. A spelled-out warning recovers 16% (8B) / 75% (32B) of the gap. Llama-3.3-70B and Qwen3-14B fall in too (8 → 120, 4 → 120; no helper: 81, 76); gpt-oss-20b does not (118 vs 117). Thinking removes it at 32B (118 vs 120), only partly at 8B (51 vs 118), at 7.8–8.8k tokens vs ≈0.4k for fixing the helper. Self-written docs (DRAFT-style, B3) never probe a clockwise triangle (32B: 27 of 180). A verified behaviour sentence inserted by a harness-side probe ("mirroring the input negates the result"; M2) does not help either (0 / 10 of 120 vs 18 / 80 with the hand-written warning).

> **Example F2** (Qwen3-32B, lattice points, only the needed helper). Wrong on mirrored and reversed copies (negative signed area):
> ```python
> def polygon_area2(poly):        # twice the signed area (shoelace, exact)   <- the offered helper
> …
> area2 = polygon_area2(poly)     # negative for clockwise vertex order; no abs()
> A = area2 // 2
> I = A - boundary_points // 2 + 1
> print(I)
> ```
> With the warning "NEGATIVE for clockwise; use abs()" in the comment, 38 of 60 programs switch to a brute force that miscounts boundary points.

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

- The 5-line exact snippet beats the full manual at every size, also on held-out problems. **A near-miss reference is as bad as none:** the full sheet (TSP routing without capacities) leaves 32B at CVRP .07; the CVRP snippet gives 0 on VRPTW.
- **Correction (2026-10-13): the VRPTW "skipped field" was an ambiguous header in our own prompt.** We wrote `n capacity K service horizon`; gpt-oss-120b read `n capacity K horizon` in almost every program (0–3 of 30 parse `service`), so the horizon became 10 and the solver reported infeasible; with the field removed, 43 of 49 are optimal. Restating the fields, the model writes "… maximum route end time (service horizon)": one compound noun. With `n capacity K service_time horizon`, 120b low gets 30/30 and 30/30 optimal, 20b low 29/30, 29/30 (F3y): an ambiguity in our spec, not a prior overriding a clear specification. An audit of all 22 format strings (A1) finds only this header misread systematically (gpt-oss-120b, gpt-oss-20b, Qwen3-8B in 3 of 3 samples).
- **Showing the literal input disambiguates it, with fewer tokens:** with the snippet, 120b low goes 0 → .97–1.00 (4.8k → 1.7k tokens per instance), 120b medium .07 → 1.00 (10.7k → 3.7k), 20b low .07–.17 → .80–.97; field-skipping programs drop from 18–29 of 30 to 0–3. Asking for a restatement does not help (gpt-oss 0–2 of 30); DRoC-style retrieval (B4, pre-registered) beats plain top-3 (+.12 to +.15) but not the exact snippet (−.12 to −.40).
- **Reasoning cannot replace the fact:** thinking without documentation gives 14B / 32B / R1-Distill-70B .33 / .03 / .00 on CVRP at 11–19k tokens per program, vs .97 / .97 / .90 with the snippet. **Retrieval works when precise:** BM25 top-1 matches the hand-written snippet (32B .965 vs .956); top-3 adds near-misses (CVRP .78 → .55).

![Optimization documentation: exact snippet vs full sheet](figs/fig5_co_docs.png)

> **Example F3** (Qwen3-32B, CVRP with 8 customers, after 2 repair rounds). *Full sheet (no capacity dimension)*: a guessed capacity API.
> ```python
> manager = pywrapcp.RoutingIndexManager(num_locations, K, [0] * K, [0] * K)
> demand_callback_index = routing.RegisterUnaryLongLivingCallback(demand_callback)
> # AttributeError: 'RoutingModel' object has no attribute 'RegisterUnaryLongLivingCallback'
> ```
> *Thinking, no documentation* (another instance, ≈15k tokens): another invented name, `routing.RegisterUnaryCallback(demand_callback, True)`. *Exact snippet* (same instance as the full sheet): proven optimum.
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

- **Budgets:** about 1k thinking tokens recover most geometry accuracy (lattice 8B 12 → 58 of 60); optimization needs far more (TSP stays at 0 with 2k). gpt-oss-20b at low effort: ≈99% at ≈0.4–0.9k tokens; at high effort 27% of programs never finish within 24k.
- **Fixes compose** (polygon clipping, gpt-oss-20b at low effort): 14 → 44 of 60 with a one-sentence hint → **59** with hint + 3 checked samples (≈2.8k tokens in total).
- **Published label-free selectors (B1, pre-registered; same 3 candidates, Qwen3-8B)**, % correct picks (clean / 8 extra helpers / hard): metamorphic check 99.7 / 83.3 / 33.3; CodeT 96.0 / 82.7 / 26.7; vote on the given input 95.7 / 81.3 / 21.7; MBR-exec 93.7 / 80.3 / 21.7–25.0; DeepConf at most 95.3 / 80.0 / 15.0. Fresh random inputs miss the sign and orientation errors that mirrored copies of the given instance expose. Not leakage: scored on 5 fresh instances, 98.2 / 97.7 / 93.9 (8B / 14B / 32B) vs 98.7 / 97.7 / 94.3.
- **Confidence cannot replace the check (C1, pre-registered).** Log-probability separates right from wrong on clean prompts (AUROC 0.68), yet the most confident of 3 gains +1.0 [−1.1, +3.1] vs +7.0 for the check; under 8 extra helpers the wrong Graham scans are *more* probable (AUROC 0.43); on hard tasks it is anti-correlated with correctness (0.40). Qwen3-32B replicates (check 6.7–22.5 points better).
- **The check-gated pipeline loses on systematic errors (E3, pre-registered; `docs/prereg/PREREG_E3.md`).** One program; if the check fails, 3 samples + check; if none is consistent, a 1,024-token thinking budget. With needed helpers only (Qwen3-8B): 98.0% at 365 tokens per instance, matching best-of-3 + check (938 tokens), near full thinking (100% at 3,792). Under 8 extra helpers / on hard tasks only 84.7% / 53.3%, **below a fixed 1,024-token thinking budget for every instance** (93.0% / 80.8% at about the same 1.6k / 1.7k tokens): the check accepts programs wrong the same way on every copy (28 of 264 accepted first programs under K8, 21 of 40 on hard tasks). A same-model brute-force reference (E3b, pre-registered) catches 86–90% of these but costs as much as the budget and fails on the hardest task (lattice 1 of 60).

![Fixes under a broad toolbox](figs/fig8_fixes_under_distractors.png)

> **Example F4a: a slip, fixed by sampling** (Qwen3-8B, polygon area, clean prompt). One of 3 samples parses coordinates as floats:
> ```python
> x = float(data[idx]); y = float(data[idx + 1])     # products near 1e18 lose precision
> print(int(2 * area))
> ```
> It is wrong only on the copy shifted by 10^9; the 3 programs disagree on transformed copies of the *given* instance, and the check keeps an integer program (3 × ≈0.3k tokens).
>
> **Example F4b: a systematic error** (F1 instance, 8 extra helpers): all 3 samples take the `polar_sort` route; nothing correct to select.
>
> **Example F4c: hint + check compose** (gpt-oss-20b, polygon clipping). `cross(cp1, cp2, e) >= 0` keeps the right side only for a counter-clockwise clipping polygon:
>
> | identity | translate | rot90 | mirror | reversed order | scale ×3 | +10^9 | degenerate |
> |---|---|---|---|---|---|---|---|
> | ✓ | ✓ | ✓ | ✗ (prints 0) | ✗ (prints 0) | ✓ | ✓ | ✓ |
>
> The check rejects it on the mirrored copy (single sample 14 of 60 → checked 28); the hint "orient both polygons counter-clockwise first" gives 44, hint + check 59.

**F5. Robustness can be distilled into a fast model per task; replaying the student's own programs protects the other tasks.**
- LoRA on Qwen3-8B with 600 verified programs the same model wrote *with* thinking (0/4/8 extra helpers): under 8 extra helpers 77.0 → **98.0** (+21.0 [+17.8, +24.3], 2 seeds) at ≈350 tokens instead of ≈6k. Clean-prompt training gives no gain: the model learned to ignore helpers.
- **Collateral damage:** unseen tasks get slightly worse (58.6 → 52.2); an unseen fragile task can collapse even on clean prompts (hull 97 → 28–34; Example F5).
- **Self-replay removes the damage (E4, pre-registered; `docs/prereg/PREREG_E4_REPLAY.md`).** Leave-hull-out LoRA, clean-prompt hull: base 109/120, no replay 48, **+ 270 of the student's own verified no-thinking programs on 5 other tasks: 118**, + the thinking teacher's programs for the same 270 prompts: 36 (self − teacher +68.3 [+60.0, +76.7]); in-task robustness is kept (240/240). Base and self-replay models write the monotone chain in 120/120 hull programs, no-replay and teacher-replay students in 59 and 49. On the new Delaunay task both replay arms still drop (59 → 47 / 45 of 60).
- **Established remedies (B2, pre-registered):** WiSE-FT trades hull against the in-task gain (α 0.5: 119 / 222 of 240; α 0.75: 96 / 236); SDFT halves the damage (85); self-training alone gives 104 / 235; only self-replay keeps both (118 / 240). With hull trained and convex held out (E4b), self-replay keeps convex at base level under 8 helpers (81 → 80 of 120; no replay 55, teacher replay 42) while keeping the large in-task gain (236 → 295 of 300). A second training seed (R1) replicates both contrasts: self vs teacher replay 118 vs 28 (hull) and 85 vs 34 (convex).

> **Example F5** (the F1 instance, 8 extra helpers, no thinking). *Base Qwen3-8B* (1,067 tokens) copies all 11 helpers and builds the hull on `polar_sort`; wrong. *Distilled LoRA* (249 tokens) copies only what it needs and writes the monotone chain; correct.
> ```python
> def orient(a, b, c):
>     return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
>
> def convex_hull(points):
>     points = sorted(points)
>     …
>     return lower[:-1] + upper[:-1]
> ```
> *The other side*: the collapsed hull programs of a LoRA trained without hull data are mostly Graham-scan variants.

**E1. Where the failures come from, and which fix repairs which kind (all stored programs).** Each of the 14,822 failing programs (47,868 programs, 388 runs) got one class from behaviour only: which versions fail, the exception on re-run, counterfactual re-runs (e.g. the VRPTW header without the misread field). Reading 8 programs per class confirmed 127 of 128 geometry and 85 of 97 optimization labels (`poc/analyze_e1_taxonomy.py`, `docs/notes/E1_TAXONOMY_DRAFT.md`).

| | algorithmic (logic, orientation, degenerate, precision) | API / knowledge | input format | packaging / interface (helpers) | other |
|---|---|---|---|---|---|
| Geometry, 9,846 failures | **72%** (hard tasks 81–87% in every family) | – | 1% | 12% (52% for Qwen3 no-thinking when a toolbox is offered) | 16% |
| Optimization, 4,976 failures | 29% (modelling / logic) | **51%** (Qwen3 58%) | 8% (all VRPTW; gpt-oss's failures are 53% input format, caused by the ambiguous header, see F3) | – | 12% (6% output format) |

Fix map (same instance after one fix; re-sampling rescues 9–52%): **API fact → exact snippet** (618 of 1,042; thinking 91 of 240); **input format → one literal input** (75 of 94); **orientation → hint** (188 of 221); **logic → thinking** (476 of 544) or a hint (810 of 1,204), not sampling + check (204 of 914); **precision → sampling + check** (46 of 55); **degenerate cases → thinking** (23 of 27; the check rescues 0 of 70); **wrong helper signatures → one contract sentence** (61 of 83); **uncopied helpers → pre-define them** (329 of 630).

**Scoring choice.** 293 TSP failures return to the start city (`0 … 0`) against the requested "each city exactly once"; 281 are optimal. Accepting them would raise Qwen3-32B (no doc) from .70 to .83 and Llama-70B (no doc / full sheet / snippet) from .33 / .55 / .87 to .54 / .73 / .99; the F3 ordering holds.

### 4.3 Follow-up experiments (status 2026-10-13)

| # | Experiment | Question | Status |
|---|---|---|---|
| E1 | Failure taxonomy of all stored programs | Which share is algorithmic; which fix per class? | done: geometry 72% algorithmic, optimization 51% missing API knowledge (`docs/notes/E1_TAXONOMY_DRAFT.md`) |
| E2 | Pre-registered F1/F2 replication | Do the effects predict new tasks? | done: F2 strongly; F1 partly, plus an input-format channel (`docs/prereg/PREREG_E2.md`) |
| E3 | Check → sample → think pipeline | Can the check decide how much to spend? | done: only for slips; loses to a fixed small thinking budget (`docs/prereg/PREREG_E3.md`) |
| E4 | Distillation with replay | Robustness without damaging other tasks? | done: own programs protect the unseen task; the teacher's do not (`docs/prereg/PREREG_E4_REPLAY.md`) |
| C1 | Token confidence as selector (added) | Can log-probs replace the check? | done: no |
| B1–B4 | Published baselines (added) | Do they beat our fixes? | done: no; CodeT / MBR-exec / DeepConf, WiSE-FT / SDFT / self-SFT, scope sentence / S2A and DRoC-style retrieval all fall short (`docs/prereg/PREREG_B1.md`–`B4.md`) |
| E3b, E4b, R1, A1, L1, M1–M5 | Brute-force reference; replay with a large in-task gain; format-string audit (added) | | done (F4, F5, F3) |
| H1–H5, N1–N4, FM | Harder problems (added): 20,000-point inputs; 311 Codeforces geometry problems; 56 Solomon VRPTW; 40 job-shop; methods for them | Are the tasks too easy? Which cheap fix on hard ones? Can the model find the facts itself? | done (Section 4.4) |
| E5 | A closed API model | Do F1–F4 hold for frontier models? | not run (no API access) |

### 4.4 Hard benchmarks (added 2026-10-14; `docs/prereg/PREREG_H1.md`–`H5.md`, `PREREG_N.md`, `PREREG_FM.md`)

Our generated tasks are easy for reasoning models (H1: gpt-oss 92–98% even with 20,000-point inputs), so the main questions were re-tested on standard sets.

| Benchmark | Result |
|---|---|
| 311 Codeforces geometry problems (CodeContests, official tests, references re-validated; H2c) | Qwen3-32B no-think / think-1,024 / full thinking 12 / 22 / 30%; gpt-oss-20b low / medium 38 / 47%; gpt-oss-120b low / medium 46 / 57%; problems rated ≥ 2300 below 35% for every single attempt |
| 56 Solomon VRPTW instances, 100 customers (H3) | without facts 0–6% feasible (gpt-oss-120b medium 46–50%); with a correct reader + the robust solver snippet gpt-oss-120b 100% (median gap 1.5%), gpt-oss-20b 44–64%, Qwen3-32B ≤ 5% |
| 40 job-shop instances (la01–la40, CP-SAT; H5) | 79–85% feasible with no facts, optimal when feasible |

- **Fix selection (F4) holds.** The statement's examples are the cheap label-free check: with 3 samples they recover most of the gap to the best sample, and output agreement (MBR-exec) adds ≈ 1 point. For gpt-oss-20b, samples + the check or one repair round beat paying for medium effort; for gpt-oss-120b one medium attempt beats three low ones; Qwen's think-1,024 × 3 + check equals full thinking at 64% of the tokens (Figure 9).
- **Facts (F3) hold and compose.** The file layout, "OR-Tools takes integers everywhere" (models write `1e7`), and a first-solution strategy for tight windows are each needed; alone each does little (Figure 10). Qwen3-32B rewrites the given calls into signatures that do not exist. The textbook CP-SAT job shop needs no facts.
- **Helpers (F1) shrink.** gpt-oss-20b low loses 4.3 points with 8 related helpers (p = 0.001), mostly by reasoning less; unrelated helpers or a "most are not needed" header cost ≈ 2 (n.s.); Qwen3-32B and gpt-oss-120b are unaffected (Figure 11).
- **Methods.** New tests built from the examples by symmetry (N1, new) catch only 6% of wrong example-passing programs: contest errors survive symmetries. One repair round from the failing example (N2) is the best next step per token (gpt-oss-120b low 46.0 → 53.1% at 4.6k tokens); escalating only when the examples fail (N3, published idea) gives +2.7 points at 13% fewer tokens for gpt-oss-20b, repairing first (N4) ≈ 1 more. Execution-verified fact mining (FM, new; closest: Dynamic Cheatsheet) recovers the layout and integer facts and lifts gpt-oss-120b from 7% to 21–40% on held-out Solomon instances (one chain 65%), with large variance between chains, no help for gpt-oss-20b and no gain from pooling: a partial negative (16-program verification is too noisy; mined facts are prose patches, the hand facts are working code).

![Real contest geometry: cost-accuracy frontier](figs/fig9_contest_frontier.png)

![Routing at benchmark scale: facts compose](figs/fig10_routing_facts.png)

![Unneeded helpers on real problems](figs/fig11_helpers_real.png)

## 5. Limitations

1. **Synthetic tasks.** The main effects were found on generated tasks. On standard benchmarks (Section 4.4) F3 and F4 hold, F1 shrinks to a small effect for one model, and F2 was not re-tested directly (one natural instance: our own float-returning reader broke OR-Tools' integer contract).

2. **Partly post-hoc mechanism.** Off-idiom drift was formed after seeing the data; pre-registered tests confirmed its core but refuted the similarity-based predictions, and on a new task helpers that suggest no algorithm hurt through input parsing instead.
3. **Oracle fixes.** Snippets and hints are hand-written; retrieval matches them only when it fetches the exact page, and the deployable label-free check misses transformation-invariant errors (E3).
4. **Coverage.** Open-weight models only (three families; E5 not run); some secondary cells are single-seed.

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

Typical runs (vLLM server, OpenAI-compatible API at `POC_BASE_URL`):

```
python poc/run_geo_cross.py --model_tag X --stdlib --n_inst 30 --temperature 0.7 --seed 1 --distract 8 [--think | --algo_hint | --show_stdin | --logprobs]
python poc/run_geo_cross.py --model_tag X --stdlib --n_inst 30 --temperature 0.7 --seed 1 --tasks delaunay --distract 0 --incircle signed|doc|fixed
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
