# Tools, Facts, and Checks: When LLM-Written Geometry and Optimization Code Fails, and Which Fix to Use

*Graduate NLP course project proposal*

> **About this file.** The project proposal in short. Full log of every run and correction: [results/FINDINGS.md](results/FINDINGS.md); failure → fix map: [results/FIX_MAP.md](results/FIX_MAP.md); earlier long versions: `results/archive/`.

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

In practice geometry is solved with approach 3 and optimization with 3 and 4. Direct answers fail: asked for twice the area of one polygon in 8 equivalent copies (shifted, rotated, mirrored, …), Qwen3-8B says 436 (correct), 2944, 392 and 728; the program it writes is right on all 8.

## 1. Why this matters

1. **This code is used in real systems, and its errors are silent.** Coding assistants and agents now write route planners, schedulers and geometry routines (maps, CAD, robotics). A wrong program still runs and prints an answer. *Example:* a convex-hull program that is right on the original input but wrong on its mirror image; a delivery plan that reaches a customer just after its time window closes, because of a rounding error.
2. **The default practice is "give the model more", and it is not free.** Agents get large tool catalogs and documentation dumps (RAG, MCP servers), and reasoning models spend up to 30k tokens per problem. *Example:* on vehicle routing, giving Qwen3-32B the full OR-Tools manual makes it *worse* than no documentation (.07 vs .23 solved optimally), while 5 exact lines make it right (.77–.90).
3. **Token cost is now the main cost of using LLMs.** *Example:* on 311 real contest geometry problems, gpt-oss-120b solves 57% at medium effort (6.8k tokens per problem) and 66% at high effort (30k): 4.4× the cost for 9 more points. Knowing when a 1k-token fix does the job of a 30k-token one saves real money and time.

**Goal:** a practical map from *what went wrong* to *the cheapest fix that works*, measured with exact answers on standard benchmarks.

## 2. Question and how we test

**Question:** what should go into the prompt, and which cheap fix works for which failure, at what token cost? (1) Tools: can unneeded helpers hurt? (2) Facts: a full manual, or one exact usage example? (3) Fixes: sample and check, repair, or pay for reasoning?

- **Benchmarks with exact answers:** 311 Codeforces geometry problems (official tests), 56 Solomon vehicle-routing instances (100 customers), 40 + 42 job-shop scheduling instances, plus 13 geometry and 8 optimization tasks we generate for controlled tests.
- **Strict scoring:** geometry programs must be right on 8 equivalent copies of each input; routing and scheduling plans must be feasible and close to the best known.
- **One change at a time**, compared with the same prompt without it; predictions written before every run; 2–3 seeds; accuracy always reported with its token cost; programs read, not only scores.
- **Models:** open models run locally: Qwen3 (1.7B–32B), Qwen3.8-27B, Qwen3.6-35B-A3B, Llama 3, gpt-oss-20b / 120b.

## 3. Main results on real benchmarks

**R1. Solver code fails for missing facts, not missing intelligence.**
> *Example* (Qwen3-32B, OR-Tools routing). Given the full manual, it invents a method: `routing.RegisterUnaryLongLivingCallback(...)` → `AttributeError`. Given 5 lines with the right call, `RegisterUnaryTransitCallback`, it reaches the proven optimum.

On the 56 Solomon instances three facts are needed together: the file layout, "OR-Tools takes integers everywhere" (models write `1e7`), and a start strategy for tight time windows. Without them at most 6% of programs give a feasible plan at low effort; with them gpt-oss-120b reaches 100% (1.5k tokens). Reasoning cannot replace them (.03 on routing without documentation). A needed helper with a hidden flaw is a trap: a travel-time helper that rounds instead of rounding up drops feasibility from 95% to 69% (gpt-oss-120b), and a warning comment does not help (64%).

**R2. Write once, verify, reuse: one checked program beats a new program per instance.**
> *Example* (gpt-oss-120b, routing). Draw 16 programs, keep one that gives feasible plans on 8 training instances, run it unchanged on 48 new ones: 94% feasible (vs 7% when writing a new program per instance), for 28k tokens in total.

It works for job-shop too (32 of 32, and 42 of 42 larger OR-Library instances within 4.3% of a 120 s CP-SAT run), and the routing programs stay feasible on 200- and 400-customer instances (60 of 60 each). It needs one working candidate: the cost is about tokens per candidate ÷ share of working candidates. So benchmarks that score one program per instance understate what these models can do.

**R3. Pay for reasoning only when the cheap check fails.** On contest geometry the statement's examples are a free check, but a leaky one: they never reject a correct program, yet accept 24–37% of the wrong ones (gpt-oss-120b, 3 seeds; `results/CHECKS.md`), so a second, different check (a brute-force program on small inputs) recovers the last point.

| Policy (gpt-oss-120b, 311 problems) | Solved | Tokens per problem |
|---|---|---|
| low effort | 46% | 3.2k |
| low + one repair from the failed example | 53% | 4.6k |
| medium | 57% | 6.8k |
| medium, high only if the examples fail | 65% | 20.2k |
| medium, high if the examples fail or a brute-force check disagrees | 66% | 24.7k |
| always high | 66% | 30.1k |

One repair round is the best next step per token, and escalating only on failure keeps 98% of the high-effort result for two thirds of the tokens.

**R4. Choose the fix by the problem type, not by the error message.** For Qwen3-32B, picking the fix from the first failure's error signal is no better than the best single fix (geometry 88.9 vs 89.8%, optimization 73.0 vs 76.0%), and letting the model pick its own fix is worse (85.2 / 69.0%). Simple defaults win: in geometry, remove unneeded tools (80.6% at 0.4k tokens) or reason (97.2% at 6.1k); in optimization, give exact snippets (70% at 0.5k; Qwen3.6 91% vs 64% with the full manual). The solver library is a tool choice too: models use it by habit (CP-SAT, or the routing library for routing), and the best library differs by model and problem (Qwen3-32B bin packing: MIP 23 of 24 optimal vs CP-SAT 1 of 24); running all libraries per instance and keeping the best feasible plan, with no answer needed, beats every single library for all four models (e.g. Qwen3-32B 64.5% vs 41.5%, gpt-oss-120b 94.5% vs 81.0%) at about 4× the tokens; falling back to another library only when the plan is infeasible keeps 96–98% of that at 34–84% of the tokens.

## 4. Mechanisms on generated tasks (why the fixes work)

**M1. Unneeded helpers change the algorithm.**
> *Example* (Qwen3-8B, convex hull). With 8 unneeded helpers it builds on the offered one: `sorted_points = polar_sort(points, left)` → wrong on all 8 copies.

Two such helpers take convex hull from 97% to 8%; a one-sentence hint fixes it at 0.6k tokens (94%), reasoning at ≈6k. On real contest problems the effect is small (−4 points for gpt-oss-20b only).

**M2. A needed tool with a hidden condition is a trap.**
> *Example* (Qwen3-32B, lattice points). The helper returns a *signed* area and the model forgets `abs()`: `A = polygon_area2(poly) // 2` → negative for clockwise input.

Correct on 9–15 of 60 instead of 44; fixing the helper restores 46–49, a warning does not (17–19). R1's rounding helper is the same trap at benchmark scale.

**M3. Errors that vary are caught by checks; errors that repeat need reasoning.**
> *Example* (Qwen3-8B, polygon area). One of 3 programs reads coordinates as floats and fails only on the copy shifted by 10⁹; running each program on shifted, rotated and mirrored copies drops it.

3 samples + this check: 100% at 0.9k tokens (reasoning 91% at 5.5k). When all samples share the error (M1), checks cannot help.

**M4. Robustness can be trained into a small model; mixing in its own programs protects other tasks.**
> *Example* (Qwen3-8B, hull with 8 helpers). Before LoRA: 1,067 tokens, wrong. After LoRA on its own verified programs: 249 tokens, correct.

77 → 98% at 0.35k tokens instead of 6k; an unseen task survives with the model's own programs mixed in (118 of 120) but not with teacher programs (36). On contest problems fine-tuning did not help.

![Real contest geometry: accuracy against token cost](figs/fig9_contest_frontier.png)

![Routing at benchmark scale: the facts only work together](figs/fig10_routing_facts.png)

## 5. Baselines from related work and our methods (all measured here)

| Published baseline | Measured on our tasks |
|---|---|
| CodeT, MBR-exec, majority vote, DeepConf (pick 1 of 3 programs) | 96.0 / 93.7 / 95.7 / 94.7% on clean prompts (Qwen3-8B); our symmetry check 99.7% |
| Scope sentence (2609.14157), System 2 Attention | recover 2–3% of the helper harm / 11 points worse |
| DRAFT (self-written tool docs) | 11–15% vs fixed helper 87–92% (Delaunay) |
| DRoC-style retrieval | .12–.40 below the exact snippet (routing) |
| TroVE-style voting | most accurate against helper harm (91.2 / 95.0%) at ≈2.6k / 1.8k tokens |
| WiSE-FT, SDFT, self-training | unseen task kept: SDFT 85, self-training 104, WiSE-FT 119 of 120 but with a smaller in-task gain; self-replay 118 with the full gain |
| AlphaCode filter, Self-Debugging, FrugalGPT-style cascade | used in R3: examples check, one repair (+5–7 points), escalation (+2.7 points at 13% fewer tokens, gpt-oss-20b) |
| Dynamic Cheatsheet-style memory | 31–40% of unseen routing instances (no facts 7%) |

| Our method | Result | Verdict |
|---|---|---|
| Verify once, reuse | R2 | works |
| Draft, then refactor, settled by the symmetry check | Qwen3-32B 91.5% at 0.8k tokens | small win |
| Verified fact mining from failures | 21–40% on unseen routing, unstable | partial |
| Helper filters, symmetry tests from examples, model-written oracles, retrieved examples, contest fine-tuning, choosing the fix from the error message | no gain | negative |

## 6. Related work, plan and limitations

**Related work.** Prompt context that misleads code (2606.04057; 2609.14157; CodeCrash 2504.14119); tools with unclear contracts (DRAFT; ContractEval 2510.12047); documentation for solver code (DRoC, ICLR 2025; CP-Bench 2506.06052); label-free selection and repair (CodeT, MBR-exec, AlphaCode; Self-Debugging; Olausson et al., ICLR 2024); one program for all instances (FunSearch, HeuriGym; one solver per problem family: 2605.14141, 2608.27296). **New here:** these effects compared on geometry and optimization with exact answers, one fact at a time, every fix priced in tokens.

**Plan.** Finish the failure → fix map (`results/FIX_MAP.md`); a label-free gate that escalates only when two prompt variants disagree looks promising (Qwen3-32B geometry: 99.1% on 3 seeds at 61–79% of the tokens of always reasoning); adapting a verified program to a new rule helps every model when the change is local, and a model that cannot write the new problem itself on every rule tried, but hurts a strong model when the change restructures the solver model (flexible job-shop, gpt-oss-120b: 36 vs 67 of 80 feasible) (job-shop + release dates: Qwen3-32B 54 of 80 feasible with a minimal-edit instruction vs 4 of 80 from scratch; gpt-oss-120b 80 vs 72 of 80, and one adapted program covers all 32 held-out instances; CVRP → VRPTW with the snippet: 18 of 24 optimal vs 7 of 24 with the snippet alone); a closed API model if access is available.

**Limitations.** The mechanisms (Section 4) were found on generated tasks, and the helper effect shrinks on real problems. The facts in R1 are hand-written; automatic fact mining recovers only part of them. Only open models were tested.
