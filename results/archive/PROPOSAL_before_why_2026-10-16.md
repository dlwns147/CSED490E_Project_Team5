# Tools, Facts, and Checks: When LLM-Written Geometry and Optimization Code Fails, and Which Fix to Use

*Graduate NLP course project proposal*

> **About this file.** The project proposal in short. Full log of every run and correction: [results/FINDINGS.md](results/FINDINGS.md); earlier long versions: `results/archive/`.

## 0. Background: how LLMs solve geometry and optimization problems

**The problems.**
- **Computational geometry:** compute an exact answer from coordinates, such as the area of a polygon or the convex hull of a set of points.
- **Combinatorial optimization:** pick the best of very many options, such as the shortest delivery routes. Checking that an answer is valid is easy; proving it is the best is hard.

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

**Why programs.** Asked for twice the area of an 8-vertex polygon in 8 equivalent copies (shifted, rotated, mirrored, …), Qwen3-8B answering directly says 436 (correct), 2944, 392 and 728 on different copies. The program it writes is right on all 8:
```python
s = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]))
print(abs(s))   # exact integer arithmetic
```
Likewise, for 40-node graph colouring no direct answer is valid, while a ten-line solver model finds the optimal 4 colours on 5 of 6 graphs.

## 1. Question

LLM-written programs often look right and still fail. The usual reaction is to add more to the prompt: helper functions, documentation, more reasoning. **We ask what should go into the prompt, and which cheap fix works for which failure, at what token cost.**

1. **Tools:** can correct but unneeded helper functions hurt?
2. **Facts:** what does solver code need: a full manual, or one exact usage example?
3. **Fixes:** when should we sample several programs and check them, and when should we pay for more reasoning?

## 2. How we test

- **Tasks with exact answers:** 9 geometry tasks (hull, area, intersections, Delaunay, …) and 8 optimization problems (knapsack, TSP, vehicle routing, …) that we generate, plus three standard benchmarks: 311 Codeforces geometry problems, 56 Solomon routing instances (100 customers), 40 job-shop scheduling instances.
- **Strict scoring:** a geometry program must be right on 8 equivalent copies of each input (shifted, rotated, mirrored, …); an optimization program must reach the optimum, or a feasible plan close to the best known.
- **One change at a time:** add helpers, documentation, one example input, sampling, reasoning, repair, or fine-tuning, and compare with the same prompt without it.
- **Models:** open models run locally: Qwen3 (1.7B–32B), Qwen3.8-27B, Qwen3.6-35B-A3B, Llama 3, gpt-oss-20b / 120b.
- **Care:** predictions written before every run, 2–3 seeds, accuracy always reported with its token cost, and the programs themselves read, not only the scores.

## 3. Findings so far

**F1. Unneeded helpers change the algorithm.** With 8 correct but unneeded geometry helpers in the prompt, models build on them.
> *Example* (Qwen3-8B, convex hull). Without helpers it writes the standard monotone chain and is correct. With them it builds on the offered `polar_sort` and is wrong on all 8 copies:
> ```python
> sorted_points = polar_sort(points, left)   # the offered helper decides the algorithm
> ```

Two such helpers take convex hull from 97% to 8% correct. Reasoning fixes it at ≈6k tokens per program; a one-sentence hint ("use the monotone chain") fixes it at 0.6k (94%). On real contest problems the harm is small (−4 points for gpt-oss-20b, none for the other models).

**F2. A needed tool with a hidden condition is a trap.**
> *Example* (Qwen3-32B, counting lattice points in a polygon). The given helper returns a *signed* area, negative for clockwise polygons, and the model forgets `abs()`:
> ```python
> A = polygon_area2(poly) // 2        # negative for clockwise input
> I = A - boundary_points // 2 + 1    # Pick's formula, now wrong
> ```

Qwen3-32B drops from 44 to 9–15 of 60; fixing the helper restores 46–49, a warning in its comment does not (17–19). The same trap appears for a Delaunay helper that needs counter-clockwise triangles (1–3 of 120 solved with it, 106–109 with an orientation-free version). It holds on the Solomon benchmark too: given a travel-time helper that rounds to the nearest integer instead of up, gpt-oss-120b and Qwen3.8 are feasible on 69% / 60% instead of 95% / 94%, almost all failures being time-window violations, and a comment stating the problem does not help (64% / 65%).

**F3. Solver code needs the exact API fact.**
> *Example* (Qwen3-32B, vehicle routing with OR-Tools). Given the full manual, it invents a method that does not exist:
> ```python
> routing.RegisterUnaryLongLivingCallback(demand_callback)   # AttributeError
> ```
> Given a 5-line snippet with the right call, `routing.RegisterUnaryTransitCallback(demand_callback)`, it reaches the proven optimum.

Share of routing instances solved optimally: no documentation .23, full manual .07, exact snippet .77–.90, reasoning without documentation .03. On the 56 Solomon instances three facts are needed together: the file layout, "OR-Tools takes integers everywhere" (models write `1e7`), and a start strategy for tight time windows. Without them at most 6% of programs give a feasible plan at low reasoning effort; with them gpt-oss-120b reaches 100%.

**F4. Pick the fix by the type of error.**
> *Example* (Qwen3-8B, polygon area). One of 3 sampled programs reads the coordinates as floats (`x = float(data[idx])`) and fails only on the copy shifted by 10⁹. Our check runs each program on shifted, rotated and mirrored copies of the input and keeps one whose answers agree, so it drops the float program.

When errors differ between samples, 3 samples + this check reach 100% at 0.9k tokens (reasoning: 91% at 5.5k). When every sample makes the same mistake (as in F1), checking cannot help and reasoning wins. On the 311 contest problems, one repair round from the failed example is the best next step per token (gpt-oss-120b 46 → 53% at 4.6k tokens); more reasoning effort helps more but costs more (low / medium / high 46 / 57 / 66%; high at 30k tokens per problem, 3 seeds: 66.2%; on problems rated ≥ 2300, 49% vs 35% at medium).

**F5. Robustness can be trained into a small model, and mixing in its own programs protects other tasks.**
> *Example* (Qwen3-8B, convex hull with 8 helpers). Before fine-tuning: 1,067 tokens, copies all helpers, wrong. After LoRA fine-tuning on its own verified programs: 249 tokens, the monotone chain, correct.

With helpers, accuracy rises from 77% to 98% at 0.35k tokens instead of 6k. Fine-tuning alone breaks an unseen task (hull 109 → 48 of 120); adding 270 of the model's own programs from other tasks keeps it (118), while the same number of teacher programs does not (36). On real contest problems, fine-tuning did not help.

![Real contest geometry: accuracy against token cost](figs/fig9_contest_frontier.png)

![Routing at benchmark scale: the facts only work together](figs/fig10_routing_facts.png)

## 4. Baselines from related work and our methods (all measured on our tasks)

**Published methods, re-run here:**

| Baseline (source) | What we measured | Result |
|---|---|---|
| CodeT, MBR-exec, majority vote, DeepConf | pick a correct program among 3 (Qwen3-8B; clean / 8 helpers / hard tasks) | CodeT 96.0 / 82.7 / 26.7%, MBR-exec 93.7 / 80.3 / 25.0%, vote 95.7 / 81.3 / 21.7%, DeepConf 94.7 / 79.3 / 13.3%; our symmetry check 99.7 / 83.3 / 33.3% |
| Scope sentence (2609.14157), System 2 Attention | undo the helper harm (8 helpers) | scope sentence recovers 2–3% of the harm; S2A is 11 points worse; a one-sentence algorithm hint reaches 94% |
| DRAFT (self-written tool docs) | fix the hidden-condition helper (Delaunay) | 11–15% vs a hand-written warning 18–72% and a fixed helper 87–92% |
| DRoC-style retrieval | documentation for routing code | beats plain top-3 retrieval by .12–.15 but stays .12–.40 below the exact snippet |
| TroVE-style voting | vote over programs written with and without the helpers | the most accurate fix (Qwen3-8B / 32B 91.2 / 95.0%) at ≈2.6k / 1.8k tokens |
| WiSE-FT, SDFT, self-training | keep an unseen task after fine-tuning (hull, of 120) | SDFT 85, self-training 104, WiSE-FT trades away the in-task gain; our self-replay keeps 118 and the full gain |
| AlphaCode filter + MBR-exec | choose among 3 programs for a contest problem | the statement's examples recover most of the gap to the best program; MBR-exec adds ≈1 point |
| Self-Debugging (one repair round) | fix a failed contest program once | best next step per token: +5 to +7 points for +0.8–1.4k tokens |
| FrugalGPT-style cascade | low effort first, more effort only when the examples fail | gpt-oss-20b +2.7 points with 13% fewer tokens |
| Dynamic Cheatsheet-style memory | keep every fact the model proposes (routing) | 31–40% of unseen instances feasible (no facts: 7%) |

**Our methods** (prior art checked before each):

| Method | Idea | Result | Verdict |
|---|---|---|---|
| Verify once, reuse | choose one program that works on 8 training instances; reuse it everywhere | routing: gpt-oss-120b feasible on 94% of 48 unseen instances for 28k tokens in total (a new program per instance: 7%); still feasible on 200- and 400-customer instances; job-shop: 32 of 32 held-out and 42 of 42 larger OR-Library instances (≤ 4.3% from a 120 s CP-SAT run) | works |
| Draft, then refactor | write without helpers, then add them; keep the version that passes the check | Qwen3-32B 91.5% at 0.8k tokens (above a 1k reasoning budget, below TroVE voting) | small win |
| Verified fact mining | the model writes facts from its own errors; keep only those a re-run confirms | 21–40% of unseen routing instances, unstable between runs; no better than keeping every fact | partial |
| Helper filters, symmetry tests from examples, model-written oracles, retrieved examples, fine-tuning on contest problems, choosing the fix from the error message | various | no gain | negative |

## 5. Related work

Closest findings: prompt context that misleads code (2606.04057; 2609.14157; CodeCrash 2504.14119), tools with unclear contracts (DRAFT; ContractEval 2510.12047), documentation for solver code (DRoC, ICLR 2025; CP-Bench 2506.06052), label-free selection and repair (CodeT, MBR-exec, AlphaCode; Self-Debugging; Olausson et al., ICLR 2024), forgetting during fine-tuning (2510.18874; SDFT). **What is new here:** these effects compared on geometry and optimization with exact answers, one fact changed at a time, and every fix priced in tokens (details: `results/RELATED_WORK.md`).

## 6. Plan and limitations

**Plan.** (1) Done: the high-effort result holds over 3 seeds (66.2%; 206 / 204 / 208 of 311). (2) Done: F2 holds on Solomon routing (above). (3) Map from failure type to fix with token costs: draft in `results/FIX_MAP.md`. (4) Add a closed API model if access is available.

**Limitations.** The main effects were found on generated tasks; on real benchmarks F3 and F4 hold and F1 shrinks. The fixes (snippets, hints) are hand-written, and automatic versions recover them only partly. Only open models were tested.

*Code:* `poc/run_geo_cross.py` (geometry), `poc/run_co.py` (optimization), `poc/run_cc.py` (contest problems), `poc/run_solomon.py` (routing), `poc/run_jssp.py` (job-shop); pre-registrations with results: `results/PREREG_*.md`.
