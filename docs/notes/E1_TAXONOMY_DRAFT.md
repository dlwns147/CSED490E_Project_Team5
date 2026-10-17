# E1. Failure taxonomy: why LLM-written geometry and optimization programs fail, and which fix addresses each kind of failure (draft)

*Draft results section for PROPOSAL §4.3 E1, written 2026-10-13. Code: `poc/analyze_e1_taxonomy.py` (re-runnable; prints every table). Data: `results/e1_manifest.json` (which runs), `results/e1_taxonomy.json` (per-run class counts, every failing program's label, class × fix transitions, validation verdicts).*

**Question.** When a program written by the model fails, *why* does it fail? Is it the algorithm (wrong logic, a clockwise polygon, a degenerate case, float precision), or something around the algorithm: a solver API the model does not know, an input it reads in the wrong layout, a helper function it was given but did not copy? And which of the cheap fixes from F1–F5 (stating a fact, a hint, a different toolbox, thinking, sampling with a label-free check) repairs which kind of failure?

**Approach in one paragraph.** We took every stored program of the headline runs (47,868 programs, 14,822 of them failing) and gave each failing program exactly one class, using only its behaviour: which of the 8 geometry versions it gets wrong, what exception it raises when re-run, and three counterfactual re-runs (the same input in another layout, the VRPTW header without the skipped field, the offered helpers pre-defined). Then, for every pair of stored runs that differ only by one fix (same instances), we counted how many failures of each class are solved after the fix. We compared that with a control in which the same condition is simply sampled again. Finally, we read 8 random programs per class to check the labels.

## 1. Main results

**Table 1a. Geometry, all runs in the manifest** (failures = k of n programs; each class column = k of the failures)

| model family | failures | algorithmic | packaging/interface | input format | output format | API/environment | generation | other runtime |
|---|---|---|---|---|---|---|---|---|
| Qwen3, no thinking | 5,359/14,640 | 3,781 (71%) | 838 (16%) | 66 (1%) | 28 (1%) | 8 (0%) | 47 (1%) | 591 (11%) |
| Qwen3 +think | 206/2,880 | 159 (77%) | 24 (12%) | 0 | 7 (3%) | 0 | 6 (3%) | 10 (5%) |
| Llama | 3,547/7,500 | 2,651 (75%) | 332 (9%) | 0 | 30 (1%) | 0 | 16 (0%) | 518 (15%) |
| reasoning models (R1-Distill, gpt-oss) | 734/7,500 | 464 (63%) | 0 | 0 | 1 (0%) | 0 | 213 (29%) | 56 (8%) |

**Table 1b. Geometry, the F1 setting: 5 core tasks with a toolbox (K0 or K8), copy-in header** (failures = k of n programs; each class column = k of the failures)

| model family | failures | algorithmic | packaging/interface | input format | output format | API/environment | generation | other runtime |
|---|---|---|---|---|---|---|---|---|
| Qwen3, no thinking | 1,146/4,200 | 383 (33%) | 601 (52%) | 41 (4%) | 26 (2%) | 0 | 3 (0%) | 92 (8%) |
| Qwen3 +think | 97/1,800 | 64 (66%) | 24 (25%) | 0 | 1 (1%) | 0 | 2 (2%) | 6 (6%) |
| Llama | 781/3,000 | 446 (57%) | 178 (23%) | 0 | 20 (3%) | 0 | 5 (1%) | 132 (17%) |
| reasoning models (R1-Distill, gpt-oss) | 198/5,000 | 22 (11%) | 0 | 0 | 0 | 0 | 167 (84%) | 9 (5%) |

**Table 1c. Geometry, hard tasks (lattice, rectangle union, polygon clipping, hull with 2 misleading helpers)** (failures = k of n programs; each class column = k of the failures)

| model family | failures | algorithmic | packaging/interface | input format | output format | API/environment | generation | other runtime |
|---|---|---|---|---|---|---|---|---|
| Qwen3, no thinking | 3,519/5,340 | 2,967 (84%) | 58 (2%) | 13 (0%) | 0 | 8 (0%) | 39 (1%) | 434 (12%) |
| Qwen3 +think | 109/1,080 | 95 (87%) | 0 | 0 | 6 (6%) | 0 | 4 (4%) | 4 (4%) |
| Llama | 2,485/3,000 | 2,018 (81%) | 73 (3%) | 0 | 1 (0%) | 0 | 11 (0%) | 382 (15%) |
| reasoning models (R1-Distill, gpt-oss) | 530/2,400 | 436 (82%) | 0 | 0 | 1 (0%) | 0 | 46 (9%) | 47 (9%) |

**Table 1d. Optimization, all runs in the manifest** (failures = k of n programs; each class column = k of the failures)

| model family | failures | API/knowledge | input format | output format | modelling/logic | generation | other runtime |
|---|---|---|---|---|---|---|---|
| Qwen3, no thinking | 3,682/10,206 | 2,153 (58%) | 14 (0%) | 216 (6%) | 1,088 (30%) | 56 (2%) | 155 (4%) |
| Qwen3 +think | 223/924 | 118 (53%) | 14 (6%) | 1 (0%) | 58 (26%) | 18 (8%) | 14 (6%) |
| Llama | 419/1,266 | 164 (39%) | 8 (2%) | 87 (21%) | 138 (33%) | 0 | 22 (5%) |
| reasoning models (R1-Distill, gpt-oss) | 652/2,952 | 111 (17%) | 343 (53%) | 4 (1%) | 159 (24%) | 12 (2%) | 23 (4%) |

**Table 1e. Optimization without VRPTW** (failures = k of n programs; each class column = k of the failures)

| model family | failures | API/knowledge | input format | output format | modelling/logic | generation | other runtime |
|---|---|---|---|---|---|---|---|
| Qwen3, no thinking | 3,341/9,846 | 1,889 (57%) | 0 | 216 (6%) | 1,049 (31%) | 50 (1%) | 137 (4%) |
| Qwen3 +think | 166/864 | 104 (63%) | 0 | 1 (1%) | 39 (23%) | 13 (8%) | 9 (5%) |
| Llama | 298/1,086 | 101 (34%) | 0 | 86 (29%) | 94 (32%) | 0 | 17 (6%) |
| reasoning models (R1-Distill, gpt-oss) | 168/2,262 | 82 (49%) | 0 | 4 (2%) | 65 (39%) | 9 (5%) | 8 (5%) |

Geometry *algorithmic* = logic + orientation + degenerate + precision + variant-dependent; *packaging/interface* = helper not copied + helper called with wrong argument shapes; *generation* = no code, token cap, syntax error; *other runtime* = other exceptions, timeouts, empty output. Optimization *modelling/logic* = suboptimal + infeasible printed solution + infeasible model + no solution. "Llama" is Llama-3.1-8B and Llama-3.3-70B in geometry, Llama-3.3-70B only in optimization. Exact rules in §3.

**What share of failures is algorithmic?**
- **Geometry: mostly algorithmic.** 7,055 of 9,846 failures (72%) are algorithmic: wrong on the original input (*logic*, 5,846), an orientation assumption (519), a missed degenerate case (288), float precision with coordinates near 10^9 (236), or a latent edge case that only a rotated or permuted copy exposes (166). On the hard tasks and clipping, 81–87% of failures are algorithmic in every model family (Table 1c).
- **The exception is a toolbox in the prompt.** With helpers offered (5 core tasks, K0/K8, copy-in header), *packaging/interface* failures take over for some models: Qwen3-14B 44 of 49 failures at K0 and 185 of 262 at K8; Qwen3-1.7B 192 of 231 at K8. For Qwen3-8B the K8 failures stay algorithmic (146 of 206; packaging/interface 29). Re-running the same program with the helpers pre-defined separates the two: 125 of Qwen3-14B's 162 packaging failures become correct (copying was the only problem), but only 22 of 78 for Qwen3-32B and 3 of 12 for Qwen3-8B (those programs were wrong anyway).
- **Optimization: mostly knowledge, not algorithm.** 2,546 of 4,976 failures (51%) are *API/knowledge*: invented or misused OR-Tools calls. Modelling/logic (feasible but suboptimal, infeasible printed solution, a model that can never be satisfied, no solution found) is 1,443 (29%). Input format is 379 (8%), all VRPTW and mostly gpt-oss (343). Output format is 308 (6%), and 293 of those are TSP tours printed with the return to the start city (see §1.2).
- **By family.** Qwen3 (no thinking): CO failures 58% API. Llama-3.3-70B: 39% API, 33% modelling, 21% output format. The reasoning models (gpt-oss, R1-Distill): 53% input format (the skipped VRPTW field), 17% API. In geometry, the reasoning models' failures are algorithmic on clipping (orientation) and otherwise mostly runaway generations at high effort (gpt-oss-20b high: 191 programs never finish within 24k tokens).

**Which fix addresses which class?** (k of n = failures of that class in the "before" run whose instance is solved after the fix; the control is the same condition with another sampling seed)

| failure class | control: re-sample | fixes that clearly beat the control | weaker or no gain |
|---|---|---|---|
| packaging (helper not copied) | 38/100 | thinking 104/119; same program with helpers pre-defined 329/630 (Qwen3-14B 125/162) | API-contract sentence 4/30; prelude header as a fresh sample 46/91 (the semantic errors remain) |
| interface (wrong argument shapes) | 42/91 | API-contract sentence 61/83 (Qwen3-14B K0: 39/44); thinking 48/49 | prelude header 48/135 |
| orientation (assumes counter-clockwise) | 28/80 | one-sentence hint 188/221; more reasoning effort 170/197; thinking 44/48; MR-select 57/94; unsigned area helper 55/100 | – |
| degenerate case | 33/63 | thinking 23/27 | hint 20/34; **MR-select 0/70** (its label-free check never runs a degenerate copy, by construction) |
| precision (10^9 offset) | 22/42 | MR-select 46/55 (the 10^9 copy is one of its relations) | prelude 6/32 |
| logic (wrong on the original) | 223/1,022 | thinking 476/544; hint 810/1,204; removing the 8 extra helpers 267/725 | MR-select 204/914 (= control) |
| CO API / knowledge | 104/682 | exact snippet 618/1,042 (from no doc), 357/794 (from full sheet) | thinking 91/240; best-of-3 121/544; near-miss → exact 18/75 (VRPTW stays hard) |
| CO input format (VRPTW field) | 8/85 | **literal input in the prompt 75/94** | snippet 8/71; best-of-3 14/85; more effort 44/178 (snippet runs: gpt-oss-20b 32/58, gpt-oss-120b 4/84) |
| CO suboptimal | 111/311 | exact snippet 326/350; thinking 56/75; best-of-3 140/269 | – |
| CO infeasible printed solution | 23/65 | exact snippet 116/139 | – |

In one line: **API facts → the exact snippet; interface → a contract sentence; input format → a literal example of the input; orientation and logic → a hint or reasoning; precision → metamorphic selection; degenerate cases → reasoning (selection is blind to them); packaging → pre-define the helpers (it only matters for models whose logic is otherwise right).**

### 1.1 Per model and condition
The tables in §6 give the class split for every model × condition. A few rows that carry the story:

- Qwen3-14B, 5 core tasks, K0: 49 failures of 300, 44 of them *interface* (8 scalars passed to `segments_intersect`). With the one-sentence API contract: 18 failures, 5 interface (42 of the 49 failed instances solved).
- gpt-oss-120b, VRPTW, exact snippet: 86–90 failures of 90 (low/medium effort), 81–84 of them *input format*. With the `service` field removed, 97 of 129 (low) and 105 of 112 (medium) of its failing VRPTW programs (all doc conditions) give an optimal solution.
- Polygon clipping, gpt-oss-20b low: 104 of 137 failures are *orientation* (mirror and/or reversed copy wrong). With the hint, 32 of 45 failed instances are solved (orientation 22/35); at medium effort, 38/45.
- Polygon clipping, Qwen3-8B/32B: 0 of 60 failed instances are solved by the hint and 20–24 of 60 by thinking. Their failures are *logic* (138 and 90 of 180) and crashes, not orientation: the hint describes an algorithm they cannot implement.
- Hard tasks, Llama-3.3-70B: 592 of 597 failures are algorithmic (no Pick's theorem, an ad hoc ray casting). MR-select rescues 2 of 120 failed instances; the hint solves 73 of 120.

### 1.2 Counterfactual checks (same program, changed input or environment)
- **VRPTW, `service` field removed** (1,000 failing VRPTW programs re-run). Afterwards optimal / feasible but not optimal: gpt-oss-120b medium 105/2 of 112, gpt-oss-120b low 97/14 of 129, gpt-oss-20b low 75/21 of 190, gpt-oss-20b medium 17/12 of 51, Qwen3-32B 13/15 of 188, Llama-70B 5/3 of 121, Qwen3-8B 0 of 209. The skipped field is mainly a gpt-oss failure; Qwen3-32B does it occasionally too (28 programs, 14 of them with thinking).
- **"Infeasible model" on VRPTW is mostly the same misread plus a second bug.** 69 of the 88 VRPTW programs that raise `CP Solver fail` get past that point once the field is removed and then fail on something else (a time dimension with zero slack, an invalid search parameter). Showing the literal input solves 15 of 23 of them.
- **Geometry, other input layouts.** 66 programs are correct on all 7 non-degenerate versions once the count lines are dropped (they parse every line as a point). Another 96 "other crash" programs run to completion in another layout but are still wrong (a misread plus a logic error).
- **TSP tour with the closing city (output format), a scoring choice to decide.** The TSP prompt asks for "each city exactly once", and 293 programs print `0 … 0`. 281 of these tours are optimal. They typically come from the routing idiom `tour.append(mgr.IndexToNode(index))  # add the last node`. Accepting the closing city would change published CO numbers: Qwen3-32B no doc .701 → .828, Llama-70B no doc / full sheet / snippet .33 / .55 / .87 → .54 / .73 / .99 (4 core problems), Qwen3-32B snippet .970 → .995. The ordering of the F3 conditions does not change, but the gaps shrink.

## 2. Data
- **Manifest:** 388 result files (223 geometry, 165 optimization). The final run saw 972 `geocross_*`/`co_*` files, so 584 were skipped: out-of-scope ablations (budget sweeps, auto-scoping, RAG, E5 LoRA, prompt paraphrases, neutral header, size sweeps, early pilots), gpt-oss K8 runs superseded after the extractor fixes, and the `S2_` VRPTW runs still being written by the current session. Zebra files and `results/archive/` are excluded by design. Each entry records model, effort, condition, seed, temperature, token cap and the queue script (`poc/queues/queue_*.sh`) that launched it.
- **Coverage:** geometry 32,520 programs (9,846 failing): the 5 core tasks K0/K8 for Qwen3 1.7B/8B/14B/32B, Llama-3.1-8B, Llama-3.3-70B, R1-Distill-Llama-70B and gpt-oss-20b/120b at low/medium/high effort; the prelude header; thinking; the API contract; the hard tasks (lattice, rectangle union) with and without helpers, hint and thinking; the signed/unsigned area helper; hull with the 2 worst helpers ± hint; polygon clipping ± hint/thinking. Optimization 15,348 programs (4,976 failing): the 6 problems with no doc / full sheet / exact snippet / thinking, CVRP, and VRPTW with the near-miss snippet and the literal input, for all model families.

## 3. Method

### 3.1 What counts as a failure
- **Geometry:** a program that is not correct on all 8 versions of its instance (identity, translated, rotated by 90°, mirrored, permuted, scaled ×3, shifted by about 10^9, and a degenerate version). One program is written per instance, from the identity prompt, and run on all 8 versions (`poc/run_geo_cross.py`).
- **Optimization:** the final program after up to 2 repair rounds does not reach the reference: within 1% for the six small problems (knapsack, TSP, colouring, scheduling, bin packing, vertex cover), the proven optimum for CVRP and VRPTW. Only the final program is stored.

### 3.2 How each failing program gets one class
Each failing program gets exactly one class: the first rule below that applies (the tables list the rules in that order). The rules use only behaviour: the stored per-version results, a re-run of the stored program, and counterfactual re-runs. None of them pattern-match the program text. Re-runs use the project sandbox (`poc/sandbox.py`, same time limits as the harness: 10 s geometry, 40 s optimization). The program runs inside a small wrapper that records the exception type, message and traceback frame names; it does not change behaviour.

**Geometry** (in rule order):

| class | rule | in plain words |
|---|---|---|
| no code | no Python block could be extracted | the reply contained no program |
| runaway | generation hit the token cap (`finish = length` or output tokens ≥ cap) and there is no runnable program | ran out of tokens before finishing |
| input format | correct on all 7 non-degenerate versions when the same instances are fed in another plain layout: (a) the single-number count lines removed, or (b) every number on one line | read the input in a layout other than the stated one (e.g. ignored the count line `n`) |
| syntax | `SyntaxError` / `IndentationError` | the program does not parse |
| environment | `ImportError` / `ModuleNotFoundError` | imports a library that is not installed (shapely, scipy, sympy) or a removed API (`fractions.gcd`) |
| packaging | `NameError` on the name of an offered helper | called a helper it was given but did not copy into the program. Same-program check: re-run with the offered helpers defined in front of it (as `poc/rescore_prelude.py`). If it is then correct on all 8 versions, copying was the only problem |
| interface | the exception is raised inside an offered helper (innermost frame of the program), or Python's call-signature error names an offered helper | called a given helper with the wrong argument shapes (8 numbers instead of 4 points) |
| other crash | any other exception on the identity version (type recorded) | an ordinary bug that crashes |
| timeout | > 10 s on the identity version | |
| no output | runs, prints nothing | |
| crash not reproduced | stored as a crash, runs fine now | harness flake (e.g. a timeout under load) |
| output format | wrong string but the same value: `8.0` vs `8`, `inside`/`False` vs `yes`/`no`, `19750/32` vs `9875/16` | |
| logic | wrong answer on the identity version | wrong algorithm or a bug that shows on the original input |
| orientation | right on identity; every failing version reverses orientation | assumes counter-clockwise (or one chirality) |
| degenerate | right on every version except the degenerate one | collinear / duplicate / touching case missed |
| precision | failing versions ⊆ {shifted by 10^9, scaled ×3} | floats lose precision with large coordinates |
| variant-dependent, other | any other set of failing versions | a latent edge case that only a rotated or permuted copy exposes |

Which versions change orientation (from `run_geo.variants`): **mirror** (x → −x) always reverses the orientation of every polygon and the sign of every orientation test. **permute** reverses orientation only for some instances: for polygons it applies a cyclic shift plus, with probability ½ per polygon, a reversal of the vertex order (clip/overlap may also swap A and B), and for the triangle of the `tri` task it applies a random permutation of the 3 vertices. The analysis checks each instance and counts permute as orientation-changing exactly when it reversed a polygon's signed area or the triangle's orientation. For point sets, segments and rectangles, permute only shuffles, and translate, rot90, scale and the 10^9 shift preserve orientation.

**Optimization** (in rule order):

| class | rule | in plain words |
|---|---|---|
| no code / runaway | no program (runaway if the last generation hit the token cap) | |
| input format (VRPTW) | re-run on the same instance with the `service` field removed from the header `n capacity K service horizon`: the printed routes are feasible on the true instance | the program skipped a stated input field; its routing model is fine |
| suboptimal | feasible, not optimal | the search stopped early or the objective is wrong |
| timeout | > 40 s | |
| syntax | `SyntaxError` / `IndentationError` (e.g. a repair answer that is only a fragment) | |
| infeasible model | OR-Tools raises `Exception: CP Solver fail`. For VRPTW the label records whether the program gets past this point once the `service` field is removed | a posted constraint can never hold |
| API / knowledge | the exception is raised inside OR-Tools (a Python frame in the `ortools` package, or a native `Check failed` abort); or it is an `AttributeError` on an OR-Tools object or module, or on another object but for a distinctive OR-Tools method name (e.g. the bool returned by `AddDimension` used as a dimension); or a failed import from `ortools`; or the message names an OR-Tools class. Class and method names are collected from the installed OR-Tools modules; method names must be CamelCase or contain `_`, so generic words such as `value` or `size` cannot match | wrong or invented solver API |
| other crash | any other exception | |
| output format | the stdout read another way is feasible: each line on its own, all lines joined, or a sequence whose last index repeats the first (a tour printed with its return to the start) | e.g. one route per line while the harness reads only the last line, or a TSP tour `0 … 0` where the prompt asks for each city exactly once |
| no solution | runs and prints text without a solution ("No solution found."), or uses the empty solver result (`AttributeError` on `None` for an OR-Tools method) | the model is infeasible or the search found nothing (the `None` case is checked before the API rule) |
| no output | runs, prints nothing | |
| infeasible output | the printed solution violates a constraint | modelling or logic error |
| not reproduced | the re-run gives a feasible solution although the stored run failed | time-limit or load dependent |

**Super-classes used in the summary tables.** Geometry: *algorithmic* = logic, orientation, degenerate, precision, variant-dependent; *packaging/interface* = packaging, interface; *input format*; *output format*; *API/environment* = environment; *generation* = no code, runaway, syntax; *other runtime* = other crash, timeout, no output, not reproduced. Optimization: *API/knowledge*; *input format*; *output format*; *modelling/logic* = infeasible model, no solution, infeasible output, suboptimal; *generation*; *other runtime*.

### 3.3 Which fix addresses which class
Paired designs already in `results/`: the same instances (same generator keys), with condition A ("before") and condition B ("after", the fix). For every failing program in A, its class is known; the analysis then asks whether the program written for the same instance under B is correct. Each condition is a fresh sample, so this measures "how often does the fix turn this kind of failure into a correct program for that instance", not a repair of the same program. To separate a fix from luck, the same count is made for a **control**: the same condition re-sampled with another seed (seed 1 → seed 2). A fix addresses a class only if its rescue rate is clearly above the control's.

Fixes (each in a phrase):
- **pre-define helpers (prelude):** the offered helpers are already defined when the program runs, so nothing has to be copied.
- **API-contract sentence:** one line saying that every point argument is one `(x, y)` tuple, plus example calls.
- **remove the 8 extra helpers:** K8 → K0 (only the needed helpers).
- **one-sentence algorithm hint:** e.g. "Andrew's monotone chain …", "Orient both polygons counter-clockwise; Sutherland–Hodgman …".
- **unsigned area helper:** `polygon_area2` returns `abs(...)` instead of a signed value.
- **thinking:** Qwen3 thinking mode (20k-token cap).
- **more reasoning effort:** gpt-oss low → medium.
- **label-free selection over 3 seeds:** geometry: MR-select exactly as `poc/mr_select.py` (run every sample on transformed copies of the *given* instance, keep the samples whose outputs satisfy the metamorphic relations, majority-vote the identity output); optimization: the feasible sample with the best objective. "Before" is the seed-1 sample.
- **exact snippet:** the 5–10-line problem-specific OR-Tools snippet instead of no doc, the full cheat sheet, or the near-miss (CVRP) snippet.
- **show the literal input:** the instance's literal stdin appended to the prompt (`--show_stdin`).

### 3.4 Validation
- **Reading.** For every class, 8 programs were drawn with a fixed seed per class (all of them if the class has fewer) and read together with their per-version results, re-run output and exception. Geometry: **127 of 128** labels confirmed (the one miss: a wrong inclusion–exclusion that only the degenerate version exposes, labelled *degenerate*). Optimization: **85 of 97** confirmed. The misses are in two small classes. *Infeasible model* (2 of 8; 6 of 8 also skipped the VRPTW field, see §1.2) and *other crash* (3 of 8; the others are 2 API misconceptions such as `solver.Value()` used while building the model, 1 invented method, and 2 header misreads the counterfactual does not cover). Together these classes hold 236 of 4,976 CO failures, so at most ~5% of CO failures are labelled less specifically than they could be. The per-class notes are in `e1_taxonomy.json` → `validation_manual`.
- **Reproduction.** The stored result reproduces on re-run for 2,501 of 2,502 geometry crashes, all 5,912 programs wrong on identity, and 3,955 of 3,969 CO failures. The one geometry exception is a stored crash that now runs: a load-induced timeout, labelled *crash not reproduced*.
- **Instance reconstruction.** Instances are rebuilt from their keys (`run_geo.base_instance/variants`, `run_co.gen`). For each of the 341 files that contain a success, the first successful program still succeeds on the rebuilt instances: on all 8 versions in geometry, and feasibly in CO. No failures.
- **Agreement with FINDINGS.** The MR-select transitions reproduce the published K8 numbers exactly (8B 232 → 244 of 300 = 81.3%, 14B 84.3%, 32B 84.0%, clean-prompt 8B 98.7%), and the 14B mechanism split matches (about 30 NameErrors and 32+ `segments_intersect` misuses at K8).

## 4. Examples (real stored programs)

**Example 1: interface, fixed by one sentence of API contract** (Qwen3-14B, segment intersections, K0 = only the needed helpers, instance `segs-6-7`). The program copies `segments_intersect(a, b, c, d)` correctly and then calls it with 8 numbers:
```python
a, b = segments[i]
c, d = segments[j]
if segments_intersect(a[0], a[1], b[0], b[1], c[0], c[1], d[0], d[1]):
# TypeError: segments_intersect() takes 4 positional arguments but 8 were given   (crash on all 8 versions)
```
With the added line "every point argument is ONE (x, y) tuple, e.g. …", the same model writes the same program for the same instance except for one line, `if segments_intersect(a, b, c, d):`, and it is correct on all 8 versions. Over the 14B K0 run the sentence solves 39 of 44 interface failures. Pre-defining the helpers does not help this class (48 of 135 overall, below the control).

**Example 2: packaging, where "pre-define the helpers" is the whole fix** (Qwen3-14B, convex hull, K8, instance `hull-10-5`). A textbook monotone chain that calls the offered `orient` but never copies it:
```python
while len(lower) >= 2 and orient(lower[-2], lower[-1], p) <= 0:   # NameError: name 'orient' is not defined
```
Re-run with the offered helpers defined in front of it, the same program is correct on all 8 versions. So are 124 more of Qwen3-14B's 162 packaging failures, versus 22 of 78 for Qwen3-32B, whose uncopied-helper programs are mostly wrong anyway.

**Example 3: orientation, even with the "orient counter-clockwise" hint** (gpt-oss-20b, low effort, polygon clipping with the hint, instance `clip-6-29`). The model follows the hint, but its orientation test can never fire:
```python
def shoelace_twice_area(poly): ... return abs(s)      # always >= 0
def area(poly): return shoelace_twice_area(poly) / 2
if area(polyA) < 0: polyA.reverse()                   # never true
if area(polyB) < 0: polyB.reverse()
def inside(p, a, b): return cross(a, b, p) >= 0       # "left of the edge" = inside only for a CCW clip polygon
```
| identity | translate | rot90 | mirror | permute (reversed here) | scale | +10^9 | degenerate |
|---|---|---|---|---|---|---|---|
| ✓ | ✓ | ✓ | ✗ | ✗ | ✓ | ✓ | ✓ |

Both failing versions reverse the orientation, so the classifier labels it *orientation*. Of all orientation failures, the hint solves 188/221, medium effort 170/197, and MR-select 57/94, because the mirrored copy disagrees with the original without needing a label.

**Example 4: input format in geometry** (Qwen3-1.7B, closest pair, K0, instance `close-20-25`). A correct brute force that ignores the stated first line `n`:
```python
for line in sys.stdin:
    ...
    x, y = map(int, line.split())   # the first line is "20" -> ValueError: not enough values to unpack
```
Fed the same 8 versions without the count line, it is correct on all 8. This class is 30 of the 124 failures of Qwen3-1.7B at K0 (66 programs across all geometry runs). Thinking solves all 10 of them in the paired 100-instance run.

**Example 5: two optimization failures that are not about optimization** (gpt-oss-120b low, VRPTW with the exact snippet, instance `vrptw-8-0`, header `8 25 3 10 411` = `n capacity K service horizon`):
```python
SERVICE_TIME = 10  # service duration for every customer      <- hard-coded instead of read
n = int(next(it)); capacity = int(next(it)); vehicle_cnt = int(next(it))
horizon = int(next(it))         # latest return time           <- actually the service field: horizon = 10
...
time_dim.CumulVar(index).SetRange(tw_start[node], tw_end[node])   # Exception: CP Solver fail
```
The routing model is right: with the field removed from the header, the program prints the optimal routes. Two repair rounds with the traceback never find this; showing the literal stdin in the prompt does (gpt-oss-20b low: 54 of 58 input-format failures solved across the three snippet seeds). A Qwen3-8B program on the same task fails on knowledge instead: `time_dimension = routing.AddDimension(...)` returns a bool, so `time_dimension.CumulVar(node)` raises `AttributeError: 'bool' object has no attribute 'CumulVar'`. Thinking solves none of Qwen3-8B's 30 VRPTW snippet failures. The output-format counterpart is a Llama-70B TSP program whose last line `tour.append(mgr.IndexToNode(index))  # add the last node` turns an optimal tour into an "infeasible" `0 13 6 … 15 0`.

## 5. Limitations
1. **Fresh samples, not repairs.** Except for the three counterfactuals, "rescued by fix X" compares two independently sampled programs for the same instance. The control row (re-sampling the same condition, 28% of geometry and 23% of CO failures solved) is the baseline to compare against. Per-pair numbers rest on 1–3 seeds.
2. **Only the final CO program is stored.** Classes describe the program after ≤ 2 repair rounds, so failures that repair already fixed are invisible. Repair as a fix cannot be evaluated from stored data.
3. **One class per program.** A program with two bugs gets the first matching class (e.g. a misread header *and* zero slack → *infeasible model*). §1.2 shows the size of this for VRPTW. The same holds for packaging: only 329 of 630 packaging failures are packaging-only.
4. **The input-format check covers what we could perturb.** Geometry: two layouts (no count lines, one line). CO: only the VRPTW `service` field. Other misreads (a 3-field VRPTW header, an off-by-one offset) end in *other crash* or *logic*.
5. **API detection uses OR-Tools' own vocabulary.** The vocabulary is OR-Tools class names and distinctive attribute names (CamelCase or snake_case), collected from the installed modules, plus exceptions raised inside OR-Tools code or its native CHECKs. Misconceptions that surface as plain Python errors (`UnboundLocalError: solver`, an invented method on a bool) stay in *other crash*.
6. **Missing metadata in older runs.** Older runs do not store `finish` or output tokens, so a token-cap hit cannot be told apart from *no code* there (5 programs). Two gpt-oss-120b K0 *no code* rows predate the extractor fixes and may be extraction artifacts. The gpt-oss-120b high-effort runs were made after the first extractor fix only; their 8 failures are all token-cap runaways, which the second fix does not affect.
7. **Resource limits.** CO timeouts use the harness limits (40 s wall, about 41 CPU-seconds via RLIMIT_CPU). A multi-threaded CP-SAT program can therefore hit the CPU limit before 40 s of wall time; 33 CO failures are timeouts in total. Re-runs used the same limits, under different machine load.
8. **The MR-select row inherits `poc/mr_select.py`'s tie-break.** Among consistent candidates it keeps the first (seed 1). Its 0/70 on degenerate failures is real (the check cannot see them) but is also why it never trades a degenerate failure for a different one.

## 6. Full tables

Generated by `poc/analyze_e1_taxonomy.py` (also stored in `results/e1_taxonomy.json` → `markdown_tables`). Per-pair transitions (which run → which run, per class) are printed by the script and stored under `fix_transitions`.

**Geometry, 5 core tasks, needed helpers only (K0) vs. 8 extra helpers (K8), copy-in header, no thinking (seeds pooled)** (failures = k of n programs; each class column = k of the failures)

| model | condition | failures | algorithmic | packaging/interface | input format | output format | API/environment | generation | other runtime |
|---|---|---|---|---|---|---|---|---|---|
| Qwen3-8B | K0 | 25/300 | 16 (64%) | 7 (28%) | 0 | 0 | 0 | 0 | 2 (8%) |
| Qwen3-8B | K8 | 206/900 | 146 (71%) | 29 (14%) | 0 | 5 (2%) | 0 | 0 | 26 (13%) |
| Qwen3-14B | K0 | 49/300 | 5 (10%) | 44 (90%) | 0 | 0 | 0 | 0 | 0 |
| Qwen3-14B | K8 | 262/900 | 62 (24%) | 185 (71%) | 0 | 0 | 0 | 0 | 15 (6%) |
| Qwen3-32B | K0 | 24/300 | 8 (33%) | 8 (33%) | 3 (12%) | 0 | 0 | 2 (8%) | 3 (12%) |
| Qwen3-32B | K8 | 225/900 | 124 (55%) | 72 (32%) | 7 (3%) | 0 | 0 | 0 | 22 (10%) |
| Qwen3-1.7B | K0 | 124/300 | 12 (10%) | 64 (52%) | 30 (24%) | 14 (11%) | 0 | 0 | 4 (3%) |
| Llama-3.1-8B | K0 | 144/600 | 76 (53%) | 15 (10%) | 0 | 14 (10%) | 0 | 0 | 39 (27%) |
| Llama-3.3-70B | K0 | 125/900 | 108 (86%) | 12 (10%) | 0 | 5 (4%) | 0 | 0 | 0 |
| R1-Distill-Llama-70B | K0 | 1/100 | 0 | 0 | 0 | 0 | 0 | 1 (100%) | 0 |
| gpt-oss-20b (low) | K0 | 6/600 | 2 (33%) | 0 | 0 | 0 | 0 | 0 | 4 (67%) |
| gpt-oss-20b (medium) | K0 | 6/600 | 2 (33%) | 0 | 0 | 0 | 0 | 3 (50%) | 1 (17%) |
| gpt-oss-20b (high) | K0 | 80/300 | 0 | 0 | 0 | 0 | 0 | 80 (100%) | 0 |
| gpt-oss-120b (low) | K0 | 2/300 | 1 (50%) | 0 | 0 | 0 | 0 | 1 (50%) | 0 |
| gpt-oss-120b (medium) | K0 | 1/300 | 0 | 0 | 0 | 0 | 0 | 1 (100%) | 0 |
| gpt-oss-120b (high) | K0 | 2/300 | 0 | 0 | 0 | 0 | 0 | 2 (100%) | 0 |
| Qwen3-1.7B | K8 | 231/300 | 10 (4%) | 192 (83%) | 1 (0%) | 7 (3%) | 0 | 1 (0%) | 20 (9%) |
| Llama-3.1-8B | K8 | 380/600 | 199 (52%) | 84 (22%) | 0 | 1 (0%) | 0 | 5 (1%) | 91 (24%) |
| Llama-3.3-70B | K8 | 132/900 | 63 (48%) | 67 (51%) | 0 | 0 | 0 | 0 | 2 (2%) |
| R1-Distill-Llama-70B | K8 | 1/100 | 1 (100%) | 0 | 0 | 0 | 0 | 0 | 0 |
| gpt-oss-20b (low) | K8 | 10/600 | 9 (90%) | 0 | 0 | 0 | 0 | 0 | 1 (10%) |
| gpt-oss-20b (medium) | K8 | 6/600 | 4 (67%) | 0 | 0 | 0 | 0 | 1 (17%) | 1 (17%) |
| gpt-oss-20b (high) | K8 | 72/300 | 0 | 0 | 0 | 0 | 0 | 72 (100%) | 0 |
| gpt-oss-120b (low) | K8 | 4/300 | 3 (75%) | 0 | 0 | 0 | 0 | 0 | 1 (25%) |
| gpt-oss-120b (medium) | K8 | 1/300 | 0 | 0 | 0 | 0 | 0 | 0 | 1 (100%) |
| gpt-oss-120b (high) | K8 | 6/300 | 0 | 0 | 0 | 0 | 0 | 6 (100%) | 0 |

**Geometry, same tasks with thinking (Qwen3, n = 100 per seed)** (failures = k of n programs; each class column = k of the failures)

| model | condition | failures | algorithmic | packaging/interface | input format | output format | API/environment | generation | other runtime |
|---|---|---|---|---|---|---|---|---|---|
| Qwen3-8B | K0 +think | 3/200 | 3 (100%) | 0 | 0 | 0 | 0 | 0 | 0 |
| Qwen3-14B | K0 +think | 1/200 | 1 (100%) | 0 | 0 | 0 | 0 | 0 | 0 |
| Qwen3-32B | K0 +think | 0/200 | – | – | – | – | – | – | – |
| Qwen3-1.7B | K0 +think | 33/300 | 24 (73%) | 9 (27%) | 0 | 0 | 0 | 0 | 0 |
| Qwen3-8B | K8 +think | 6/200 | 4 (67%) | 0 | 0 | 0 | 0 | 1 (17%) | 1 (17%) |
| Qwen3-14B | K8 +think | 2/200 | 1 (50%) | 1 (50%) | 0 | 0 | 0 | 0 | 0 |
| Qwen3-32B | K8 +think | 6/200 | 1 (17%) | 3 (50%) | 0 | 0 | 0 | 1 (17%) | 1 (17%) |
| Qwen3-1.7B | K8 +think | 46/300 | 30 (65%) | 11 (24%) | 0 | 1 (2%) | 0 | 0 | 4 (9%) |

**Geometry, hard tasks (lattice + rectangle union) and polygon clipping, no toolbox, no hint** (failures = k of n programs; each class column = k of the failures)

| model | condition | failures | algorithmic | packaging/interface | input format | output format | API/environment | generation | other runtime |
|---|---|---|---|---|---|---|---|---|---|
| Qwen3-8B | hard | 491/600 | 440 (90%) | 0 | 0 | 0 | 0 | 8 (2%) | 43 (9%) |
| Qwen3-8B | hard +think | 2/120 | 1 (50%) | 0 | 0 | 0 | 0 | 0 | 1 (50%) |
| Qwen3-14B | hard | 335/360 | 311 (93%) | 0 | 0 | 0 | 0 | 0 | 24 (7%) |
| Qwen3-14B | hard +think | 1/120 | 1 (100%) | 0 | 0 | 0 | 0 | 0 | 0 |
| Qwen3-32B | hard | 260/600 | 233 (90%) | 0 | 1 (0%) | 0 | 2 (1%) | 0 | 24 (9%) |
| Qwen3-32B | hard +think | 4/120 | 0 | 0 | 0 | 4 (100%) | 0 | 0 | 0 |
| Llama-3.3-70B | hard | 597/600 | 592 (99%) | 0 | 0 | 0 | 0 | 0 | 5 (1%) |
| Llama-3.1-8B | hard | 360/360 | 272 (76%) | 0 | 0 | 0 | 0 | 3 (1%) | 85 (24%) |
| R1-Distill-Llama-70B | hard | 9/120 | 8 (89%) | 0 | 0 | 1 (11%) | 0 | 0 | 0 |
| gpt-oss-20b (low) | hard | 3/120 | 2 (67%) | 0 | 0 | 0 | 0 | 0 | 1 (33%) |
| gpt-oss-20b (medium) | hard | 1/120 | 1 (100%) | 0 | 0 | 0 | 0 | 0 | 0 |
| gpt-oss-120b (low) | hard | 6/120 | 6 (100%) | 0 | 0 | 0 | 0 | 0 | 0 |
| gpt-oss-120b (medium) | hard | 0/120 | – | – | – | – | – | – | – |
| gpt-oss-20b (high) | hard | 40/120 | 1 (2%) | 0 | 0 | 0 | 0 | 39 (98%) | 0 |
| Qwen3-8B | clip | 180/180 | 138 (77%) | 0 | 0 | 0 | 0 | 4 (2%) | 38 (21%) |
| Qwen3-32B | clip | 180/180 | 95 (53%) | 0 | 0 | 0 | 0 | 8 (4%) | 77 (43%) |
| Llama-3.3-70B | clip | 179/180 | 132 (74%) | 0 | 0 | 1 (1%) | 0 | 0 | 46 (26%) |
| gpt-oss-20b (low) | clip | 137/180 | 127 (93%) | 0 | 0 | 0 | 0 | 0 | 10 (7%) |
| Qwen3-8B | clip +think | 40/60 | 36 (90%) | 0 | 0 | 0 | 0 | 1 (2%) | 3 (8%) |
| Qwen3-32B | clip +think | 36/60 | 35 (97%) | 0 | 0 | 0 | 0 | 1 (3%) | 0 |
| gpt-oss-20b (medium) | clip | 27/180 | 23 (85%) | 0 | 0 | 0 | 0 | 1 (4%) | 3 (11%) |
| gpt-oss-120b (low) | clip | 99/180 | 97 (98%) | 0 | 0 | 0 | 0 | 0 | 2 (2%) |
| gpt-oss-120b (medium) | clip | 23/180 | 1 (4%) | 0 | 0 | 0 | 0 | 0 | 22 (96%) |

**Optimization, by documentation (seeds pooled; 6 problems = knapsack, TSP, colouring, scheduling, bin packing, vertex cover)** (failures = k of n programs; each class column = k of the failures)

| model | condition | failures | API/knowledge | input format | output format | modelling/logic | generation | other runtime |
|---|---|---|---|---|---|---|---|---|
| Qwen3-8B | 6 problems: no doc | 750/972 | 490 (65%) | 0 | 1 (0%) | 217 (29%) | 12 (2%) | 30 (4%) |
| Qwen3-8B | 6 problems: full sheet | 668/1080 | 429 (64%) | 0 | 0 | 210 (31%) | 7 (1%) | 22 (3%) |
| Qwen3-8B | 6 problems: exact snippet | 352/1080 | 237 (67%) | 0 | 3 (1%) | 103 (29%) | 4 (1%) | 5 (1%) |
| Qwen3-14B | 6 problems: no doc | 387/972 | 173 (45%) | 0 | 40 (10%) | 170 (44%) | 0 | 4 (1%) |
| Qwen3-14B | 6 problems: full sheet | 278/1080 | 107 (38%) | 0 | 14 (5%) | 149 (54%) | 4 (1%) | 4 (1%) |
| Qwen3-14B | 6 problems: exact snippet | 114/1080 | 47 (41%) | 0 | 15 (13%) | 47 (41%) | 0 | 5 (4%) |
| Qwen3-32B | 6 problems: no doc | 307/972 | 110 (36%) | 0 | 101 (33%) | 60 (20%) | 13 (4%) | 23 (7%) |
| Qwen3-32B | 6 problems: full sheet | 159/1080 | 74 (47%) | 0 | 19 (12%) | 49 (31%) | 4 (3%) | 13 (8%) |
| Qwen3-32B | 6 problems: exact snippet | 43/1080 | 13 (30%) | 0 | 21 (49%) | 4 (9%) | 1 (2%) | 4 (9%) |
| Llama-3.3-70B | 6 problems: no doc | 109/192 | 36 (33%) | 0 | 17 (16%) | 47 (43%) | 0 | 9 (8%) |
| R1-Distill-Llama-70B | 6 problems: no doc | 42/84 | 33 (79%) | 0 | 0 | 5 (12%) | 4 (10%) | 0 |
| Llama-3.3-70B | 6 problems: full sheet | 88/192 | 39 (44%) | 0 | 16 (18%) | 29 (33%) | 0 | 4 (5%) |
| R1-Distill-Llama-70B | 6 problems: full sheet | 7/84 | 1 (14%) | 0 | 2 (29%) | 3 (43%) | 1 (14%) | 0 |
| Llama-3.3-70B | 6 problems: exact snippet | 60/552 | 5 (8%) | 0 | 50 (83%) | 4 (7%) | 0 | 1 (2%) |
| R1-Distill-Llama-70B | 6 problems: exact snippet | 4/84 | 3 (75%) | 0 | 1 (25%) | 0 | 0 | 0 |
| gpt-oss-20b (low) | 6 problems: no doc | 16/240 | 4 (25%) | 0 | 0 | 9 (56%) | 0 | 3 (19%) |
| gpt-oss-20b (low) | cvrp: no doc | 22/60 | 5 (23%) | 0 | 0 | 15 (68%) | 0 | 2 (9%) |
| gpt-oss-20b (low) | 6 problems: exact snippet | 3/240 | 0 | 0 | 0 | 3 (100%) | 0 | 0 |
| gpt-oss-20b (low) | cvrp: exact snippet | 2/60 | 2 (100%) | 0 | 0 | 0 | 0 | 0 |
| gpt-oss-20b (medium) | 6 problems: no doc | 10/240 | 3 (30%) | 0 | 1 (10%) | 5 (50%) | 0 | 1 (10%) |
| gpt-oss-20b (medium) | cvrp: no doc | 12/60 | 2 (17%) | 0 | 0 | 10 (83%) | 0 | 0 |
| gpt-oss-20b (medium) | 6 problems: exact snippet | 0/240 | – | – | – | – | – | – |
| gpt-oss-20b (medium) | cvrp: exact snippet | 0/60 | – | – | – | – | – | – |
| gpt-oss-120b (low) | 6 problems: no doc | 6/120 | 0 | 0 | 0 | 5 (83%) | 1 (17%) | 0 |
| gpt-oss-120b (low) | cvrp: no doc | 4/30 | 0 | 0 | 0 | 4 (100%) | 0 | 0 |
| gpt-oss-120b (low) | 6 problems: exact snippet | 0/120 | – | – | – | – | – | – |
| gpt-oss-120b (low) | cvrp: exact snippet | 0/30 | – | – | – | – | – | – |
| gpt-oss-120b (medium) | 6 problems: no doc | 0/120 | – | – | – | – | – | – |
| gpt-oss-120b (medium) | cvrp: no doc | 1/30 | 0 | 0 | 0 | 1 (100%) | 0 | 0 |
| gpt-oss-120b (medium) | 6 problems: exact snippet | 0/120 | – | – | – | – | – | – |
| gpt-oss-120b (medium) | cvrp: exact snippet | 0/30 | – | – | – | – | – | – |
| gpt-oss-20b (low) | 6 problems: full sheet | 4/120 | 1 (25%) | 0 | 0 | 3 (75%) | 0 | 0 |
| gpt-oss-20b (low) | cvrp: full sheet | 2/30 | 1 (50%) | 0 | 0 | 1 (50%) | 0 | 0 |
| Qwen3-8B | cvrp: no doc | 30/30 | 28 (93%) | 0 | 0 | 0 | 0 | 2 (7%) |
| Qwen3-8B | cvrp: full sheet | 30/30 | 27 (90%) | 0 | 0 | 0 | 0 | 3 (10%) |
| Qwen3-8B | cvrp: exact snippet | 86/90 | 81 (94%) | 0 | 2 (2%) | 0 | 0 | 3 (3%) |
| Qwen3-14B | cvrp: no doc | 24/30 | 14 (58%) | 0 | 0 | 6 (25%) | 1 (4%) | 3 (12%) |
| Qwen3-14B | cvrp: full sheet | 24/30 | 5 (21%) | 0 | 0 | 13 (54%) | 0 | 6 (25%) |
| Qwen3-14B | cvrp: exact snippet | 23/90 | 1 (4%) | 0 | 0 | 18 (78%) | 0 | 4 (17%) |
| Qwen3-32B | cvrp: no doc | 23/30 | 22 (96%) | 0 | 0 | 1 (4%) | 0 | 0 |
| Qwen3-32B | cvrp: full sheet | 28/30 | 21 (75%) | 0 | 0 | 0 | 3 (11%) | 4 (14%) |
| Qwen3-32B | cvrp: exact snippet | 15/90 | 10 (67%) | 0 | 0 | 2 (13%) | 1 (7%) | 2 (13%) |
| Llama-3.3-70B | cvrp: no doc | 18/30 | 13 (72%) | 0 | 1 (6%) | 3 (17%) | 0 | 1 (6%) |
| Llama-3.3-70B | cvrp: full sheet | 12/30 | 7 (58%) | 0 | 2 (17%) | 3 (25%) | 0 | 0 |
| Llama-3.3-70B | cvrp: exact snippet | 11/90 | 1 (9%) | 0 | 0 | 8 (73%) | 0 | 2 (18%) |
| R1-Distill-Llama-70B | cvrp: exact snippet | 3/30 | 0 | 0 | 0 | 1 (33%) | 1 (33%) | 1 (33%) |
| R1-Distill-Llama-70B | cvrp: no doc | 30/30 | 27 (90%) | 0 | 0 | 0 | 2 (7%) | 1 (3%) |
| Qwen3-8B | vrptw: no doc | 30/30 | 27 (90%) | 0 | 0 | 0 | 1 (3%) | 2 (7%) |
| Qwen3-8B | vrptw: full sheet | 30/30 | 30 (100%) | 0 | 0 | 0 | 0 | 0 |
| Qwen3-8B | vrptw: near-miss snippet | 30/30 | 27 (90%) | 0 | 0 | 1 (3%) | 1 (3%) | 1 (3%) |
| Qwen3-8B | vrptw: exact snippet | 90/90 | 80 (89%) | 0 | 0 | 10 (11%) | 0 | 0 |
| Qwen3-32B | vrptw: no doc | 30/30 | 26 (87%) | 0 | 0 | 0 | 0 | 4 (13%) |
| Qwen3-32B | vrptw: full sheet | 30/30 | 26 (87%) | 0 | 0 | 0 | 1 (3%) | 3 (10%) |
| Qwen3-32B | vrptw: near-miss snippet | 30/30 | 27 (90%) | 0 | 0 | 0 | 1 (3%) | 2 (7%) |
| Qwen3-32B | vrptw: exact snippet | 71/90 | 21 (30%) | 14 (20%) | 0 | 28 (39%) | 2 (3%) | 6 (8%) |
| Llama-3.3-70B | vrptw: no doc | 30/30 | 19 (63%) | 0 | 0 | 11 (37%) | 0 | 0 |
| Llama-3.3-70B | vrptw: full sheet | 30/30 | 23 (77%) | 0 | 1 (3%) | 5 (17%) | 0 | 1 (3%) |
| Llama-3.3-70B | vrptw: near-miss snippet | 30/30 | 20 (67%) | 2 (7%) | 0 | 6 (20%) | 0 | 2 (7%) |
| Llama-3.3-70B | vrptw: exact snippet | 31/90 | 1 (3%) | 6 (19%) | 0 | 22 (71%) | 0 | 2 (6%) |
| gpt-oss-20b (low) | vrptw: no doc | 27/30 | 7 (26%) | 9 (33%) | 0 | 10 (37%) | 0 | 1 (4%) |
| gpt-oss-20b (low) | vrptw: full sheet | 28/30 | 3 (11%) | 9 (32%) | 0 | 12 (43%) | 0 | 4 (14%) |
| gpt-oss-20b (low) | vrptw: near-miss snippet | 28/30 | 1 (4%) | 14 (50%) | 0 | 12 (43%) | 0 | 1 (4%) |
| gpt-oss-20b (low) | vrptw: exact snippet | 79/90 | 1 (1%) | 58 (73%) | 0 | 16 (20%) | 0 | 4 (5%) |
| gpt-oss-20b (medium) | vrptw: no doc | 20/30 | 3 (15%) | 9 (45%) | 0 | 6 (30%) | 2 (10%) | 0 |
| gpt-oss-20b (medium) | vrptw: exact snippet | 33/90 | 3 (9%) | 20 (61%) | 0 | 7 (21%) | 1 (3%) | 2 (6%) |
| gpt-oss-120b (low) | vrptw: no doc | 28/30 | 0 | 27 (96%) | 0 | 1 (4%) | 0 | 0 |
| gpt-oss-120b (low) | vrptw: exact snippet | 90/90 | 0 | 84 (93%) | 0 | 6 (7%) | 0 | 0 |
| gpt-oss-120b (medium) | vrptw: no doc | 26/30 | 0 | 26 (100%) | 0 | 0 | 0 | 0 |
| gpt-oss-120b (medium) | vrptw: exact snippet | 86/90 | 1 (1%) | 81 (94%) | 0 | 4 (5%) | 0 | 0 |

**Optimization with thinking or the literal input** (failures = k of n programs; each class column = k of the failures)

| model | condition | failures | API/knowledge | input format | output format | modelling/logic | generation | other runtime |
|---|---|---|---|---|---|---|---|---|
| Qwen3-8B | 6 problems: exact snippet +think | 18/192 | 10 (56%) | 0 | 0 | 6 (33%) | 1 (6%) | 1 (6%) |
| Qwen3-14B | 6 problems: exact snippet +think | 2/192 | 0 | 0 | 1 (50%) | 1 (50%) | 0 | 0 |
| Qwen3-32B | 6 problems: exact snippet +think | 2/84 | 1 (50%) | 0 | 0 | 1 (50%) | 0 | 0 |
| Qwen3-8B | 6 problems: full sheet +think | 31/108 | 8 (26%) | 0 | 0 | 14 (45%) | 8 (26%) | 1 (3%) |
| Qwen3-14B | 6 problems: full sheet +think | 7/108 | 4 (57%) | 0 | 0 | 3 (43%) | 0 | 0 |
| Qwen3-8B | cvrp: exact snippet +think | 25/30 | 20 (80%) | 0 | 0 | 4 (16%) | 1 (4%) | 0 |
| Qwen3-8B | cvrp: no doc +think | 30/30 | 25 (83%) | 0 | 0 | 0 | 3 (10%) | 2 (7%) |
| Qwen3-14B | cvrp: exact snippet +think | 1/30 | 0 | 0 | 0 | 0 | 0 | 1 (100%) |
| Qwen3-14B | cvrp: no doc +think | 20/30 | 7 (35%) | 0 | 0 | 9 (45%) | 0 | 4 (20%) |
| Qwen3-32B | cvrp: exact snippet +think | 1/30 | 1 (100%) | 0 | 0 | 0 | 0 | 0 |
| Qwen3-32B | cvrp: no doc +think | 29/30 | 28 (97%) | 0 | 0 | 1 (3%) | 0 | 0 |
| Qwen3-8B | vrptw: exact snippet +think | 30/30 | 12 (40%) | 0 | 0 | 12 (40%) | 2 (7%) | 4 (13%) |
| Qwen3-32B | vrptw: exact snippet +think | 27/30 | 2 (7%) | 14 (52%) | 0 | 7 (26%) | 3 (11%) | 1 (4%) |
| gpt-oss-20b (low) | vrptw: no doc +literal input | 20/30 | 9 (45%) | 1 (5%) | 0 | 10 (50%) | 0 | 0 |
| gpt-oss-120b (low) | vrptw: no doc +literal input | 11/30 | 0 | 0 | 0 | 8 (73%) | 0 | 3 (27%) |
| gpt-oss-20b (low) | vrptw: exact snippet +literal input | 8/90 | 1 (12%) | 5 (62%) | 0 | 2 (25%) | 0 | 0 |

**Class x fix, geometry** (k/n = failures of that class in the 'before' condition whose instance is solved after the fix; all paired runs and models pooled; classes with < 10 paired failures in total omitted)

| fix | all classes | runaway | syntax | packaging | interface | input_format | crash_other | timeout | no_output | output_format | logic | orientation | degenerate | precision | variant_other |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| control: re-sample the same condition (seed 1 -> 2) | 480/1724 (28%) | 4/9 | 1/6 | 38/100 | 42/91 | 3/3 | 51/226 | 7/25 | 3/6 | 11/14 | 223/1022 | 28/80 | 33/63 | 22/42 | 14/37 |
| API contract sentence | 80/145 (55%) | – | – | 4/30 | 61/83 | – | 1/4 | 0/1 | 0/1 | – | 12/24 | 1/1 | 1/1 | – | – |
| label-free selection over 3 seeds (metamorphic check, MR-select) | 484/1530 (32%) | 2/7 | 1/5 | 30/65 | 61/87 | 4/4 | 52/173 | 3/12 | 5/5 | 6/7 | 204/914 | 57/94 | 0/70 | 46/55 | 13/32 |
| more reasoning effort (low -> medium) | 234/267 (88%) | – | – | – | – | – | 18/19 | – | – | – | 37/41 | 170/197 | 4/4 | 1/1 | 3/4 |
| one-sentence algorithm hint | 1174/1703 (69%) | 4/8 | 1/3 | 4/4 | 7/16 | 1/1 | 115/174 | 6/8 | – | – | 810/1204 | 188/221 | 20/34 | 1/4 | 16/25 |
| pre-define offered helpers (prelude) | 180/610 (30%) | – | 1/6 | 46/91 | 48/135 | 1/3 | 10/44 | 1/6 | 3/5 | 1/4 | 44/246 | 3/7 | 13/23 | 6/32 | 3/8 |
| remove the 8 extra helpers (K8 -> K0) | 717/1607 (45%) | 0/4 | 5/17 | 212/397 | 80/128 | 0/3 | 79/189 | 8/21 | 9/11 | 9/10 | 267/725 | 9/23 | 25/44 | 6/20 | 7/13 |
| thinking | 815/932 (87%) | 6/7 | 6/7 | 104/119 | 48/49 | 14/14 | 76/93 | 5/7 | 4/4 | 3/3 | 476/544 | 44/48 | 23/27 | 3/4 | 2/5 |
| unsigned (abs) area helper | 120/459 (26%) | – | 1/1 | – | – | 1/1 | 6/21 | – | – | – | 57/336 | 55/100 | – | – | – |

**Class x fix, co** (k/n = failures of that class in the 'before' condition whose instance is solved after the fix; all paired runs and models pooled; classes with < 10 paired failures in total omitted)

| fix | all classes | runaway | syntax | api | input_format | output_format | infeasible_model | no_solution | infeasible_output | suboptimal | crash_other | timeout | no_output |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| control: re-sample the same condition (seed 1 -> 2) | 299/1322 (23%) | – | 1/16 | 104/682 | 8/85 | 34/67 | 4/17 | 5/25 | 23/65 | 111/311 | 2/37 | 2/11 | 5/6 |
| exact snippet (full sheet -> snippet) | 837/1418 (59%) | 3/3 | 10/17 | 357/794 | 0/9 | 42/54 | 1/11 | 17/21 | 37/67 | 341/378 | 17/44 | 6/11 | 6/9 |
| exact snippet (near-miss -> exact) | 30/118 (25%) | – | 0/2 | 18/75 | 4/16 | – | 3/9 | 2/6 | – | 1/4 | 2/6 | – | – |
| exact snippet (no doc -> snippet) | 1369/1982 (69%) | 7/8 | 24/27 | 618/1042 | 8/71 | 129/161 | 1/10 | 84/87 | 116/139 | 326/350 | 29/58 | 9/11 | 17/17 |
| label-free selection over 3 seeds (feasible + best objective) | 380/1112 (34%) | – | 3/13 | 121/544 | 14/85 | 43/66 | 5/17 | 9/22 | 34/53 | 140/269 | 5/32 | 3/7 | 3/4 |
| more reasoning effort (low -> medium) | 92/254 (36%) | – | – | 11/16 | 44/178 | – | 14/27 | 0/2 | – | 16/22 | 2/4 | 2/2 | 2/2 |
| show the literal input (--show_stdin) | 99/134 (74%) | – | – | 3/8 | 75/94 | – | 15/23 | – | – | 1/4 | 4/4 | – | 1/1 |
| thinking | 183/380 (48%) | – | 4/8 | 91/240 | 1/4 | 10/11 | 1/3 | 4/5 | 13/17 | 56/75 | 1/14 | 2/2 | 0/1 |
