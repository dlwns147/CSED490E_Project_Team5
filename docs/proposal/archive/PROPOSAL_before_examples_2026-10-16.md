# Tools, Facts, and Checks: When LLM-Written Geometry and Optimization Code Fails, and Which Fix to Use

*Graduate NLP course project proposal*

> **About this file.** The project proposal in short. Full log of every run and correction: [docs/FINDINGS.md](docs/FINDINGS.md); failure → fix map: [docs/notes/FIX_MAP.md](docs/notes/FIX_MAP.md); how much cheap checks miss: [docs/notes/CHECKS.md](docs/notes/CHECKS.md); earlier long versions: `results/archive/`.

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

1. **This code runs in real systems, and its errors are silent.** Coding assistants and agents write route planners, schedulers and geometry routines (maps, CAD, robots). A wrong program still runs and prints an answer: a hull that is wrong only on the mirrored input, a delivery that arrives just after the customer's time window closes because of a rounding error.
2. **"Give the model more" is the default, and it can backfire.** Agents get large tool catalogs and documentation dumps. On vehicle routing, the full OR-Tools manual makes Qwen3-32B *worse* than no documentation (.07 vs .23 solved optimally); 5 exact lines make it right (.77–.90).
3. **Tokens are the main cost of using LLMs.** On 311 real contest geometry problems, gpt-oss-120b solves 57% at medium effort (6.8k tokens per problem) and 66% at high effort (30k): 4.4× the cost for 9 more points.

**Goal:** a practical map from *what went wrong* to *the cheapest fix that works*, measured with exact answers on standard benchmarks. In one picture:

![Which fix for which situation](figs/fig0_fix_flow.png)

## 2. Question and how we test

**Question:** what should go into the prompt, and which cheap fix works for which failure, at what token cost? (1) Tools: can unneeded helpers hurt? (2) Facts: a full manual, or one exact usage example? (3) Fixes: check, repair, reuse, or pay for reasoning?

- **Benchmarks with exact answers:** 311 Codeforces geometry problems (official tests), 56 Solomon vehicle-routing instances (100 customers), 40 + 42 job-shop scheduling instances, plus 13 geometry and 8 optimization tasks we generate for controlled tests.
- **Strict scoring:** geometry programs must be right on 8 equivalent copies of each input; routing and scheduling plans must be feasible and close to the best known.
- **One change at a time**, compared with the same prompt without it; predictions written before every run; 2–3 seeds per condition; accuracy always reported with its token cost; programs read, not only scores. Rewording the contest prompt moves accuracy by under 2 points, within seed noise.
- **Models:** open models run locally: Qwen3 (1.7B–32B), Qwen3.8-27B, Qwen3.6-35B-A3B, Llama 3, gpt-oss-20b / 120b.

## 3. Main results on real benchmarks

**R1. Solver code fails for missing facts, not missing intelligence.**
> *Example* (Qwen3-32B, OR-Tools routing). Given the full manual, it invents a method: `routing.RegisterUnaryLongLivingCallback(...)` → `AttributeError`. Given 5 lines with the right call, `RegisterUnaryTransitCallback`, it reaches the proven optimum.

On the 56 Solomon instances three facts are needed together: the file layout, "OR-Tools takes integers everywhere" (models write `1e7`), and a start strategy for tight time windows. Without them at most 6% of programs give a feasible plan at low effort; with them gpt-oss-120b reaches 100%. Reasoning cannot replace them (.03 without documentation), and a needed helper with a hidden flaw is a trap: a travel-time helper that rounds instead of rounding up drops feasibility from 95% to 69%.

![Routing at benchmark scale: the facts only work together](figs/fig10_routing_facts.png)

**R2. Write once, verify, reuse; when the problem changes, adapt the verified program.**
> *Example* (gpt-oss-120b, routing). Draw 16 programs, keep one that gives feasible plans on 8 training instances, run it unchanged on 48 new ones: 94% feasible, against 7% when writing a new program per instance, for 28k tokens in total.

The reused programs stay feasible on 200- and 400-customer instances (60 of 60 each) and on 42 larger job-shop instances (within 4.3% of a 120 s CP-SAT run). When the problem gains a rule (job-shop + release dates), editing the verified program beats starting over for every model; for Qwen3-32B, adding "change as few lines as possible" lifts it from 10% to 68%. Editing can hurt when the new rule changes the model's structure (flexible job-shop, gpt-oss-120b). Benchmarks that score a fresh program per instance therefore understate these models.

![Verify once, reuse: cost curve](figs/fig12_reuse_cost.png)

![Adapt a program that already works](figs/fig16_adapt_verified.png)

**R3. Checks never reject a correct program but miss many wrong ones; pay for reasoning only when a check fails.**
> *Example* (contest geometry). A program can print the right answer on the statement's 2 examples and still be wrong on the hidden tests: 24–37% of gpt-oss-120b's wrong programs pass the examples.

![Checking the output is not enough](figs/fig13_checks_leak.png)

So use the check to decide when to spend: escalate from medium to high effort only when the examples fail, or when a brute-force program on small inputs disagrees. This keeps the high-effort accuracy (66.3% vs 66.2%) at 82% of its tokens; one repair round is the best first step per token.

![Pay for reasoning only when a cheap check fails](figs/fig14_reasoning_policies.png)

A *second opinion* works when its mistakes are independent: Qwen3-32B writes one program with and one without the extra tools and reasons only when they disagree. That matches always reasoning in geometry (99% vs 98%) at 61–79% of the tokens, and beats it in optimization (83% vs 67%); the same holds for Qwen3-8B. It fails for gpt-oss-120b on contest problems, where both programs share the same mistakes.

![A second opinion decides when to reason](figs/fig15_agreement_gate.png)

**R4. Choose the fix by problem type, not by the error message.** For Qwen3-32B, picking the fix from the first failure's error message is no better than the best single fix (geometry 88.9 vs 89.8%, optimization 73.0 vs 76.0%), and letting the model pick is worse (85.2 / 69.0%). Simple defaults win: in geometry, drop unneeded tools or reason; in optimization, give exact snippets (Qwen3.6: 91% vs 64% with the full manual). The solver library is a tool choice too: models pick one by habit, the best one differs by model and problem, and trying all of them per instance (keep the best feasible plan) beats any single library for every model, at ≈4× tokens; trying another library only when the plan is infeasible keeps 96–98% of its accuracy at 34–84% of the tokens.

![The solver library is a tool choice too](figs/fig17_library_portfolio.png)

## 4. Mechanisms on generated tasks (why the fixes work)

- **M1. Unneeded helpers change the algorithm.** *Example* (Qwen3-8B, hull): with 8 unneeded helpers it builds on the offered `polar_sort(points, left)` and is wrong on all 8 copies (97% → 8% with two such helpers); a one-sentence hint fixes it at 0.6k tokens (94%), reasoning at ≈6k. On real contest problems the effect is small (−4 points, gpt-oss-20b only), and it is invisible in the model's token confidence.
- **M2. A needed tool with a hidden condition is a trap.** *Example* (Qwen3-32B, lattice points): the helper returns a *signed* area and the model forgets `abs()`: 9–15 of 60 correct instead of 44; fixing the helper restores 46–49, a warning does not (17–19). R1's rounding helper is the same trap at benchmark scale.
- **M3. Varied errors are caught by checks; repeated errors need reasoning.** *Example* (Qwen3-8B, area): one of 3 programs reads coordinates as floats and fails only on the copy shifted by 10⁹; the symmetry check drops it (3 samples + check: 100% at 0.9k tokens; reasoning 91% at 5.5k).
- **M4. Robustness can be trained into a small model.** *Example* (Qwen3-8B, hull with helpers): before LoRA 1,067 tokens and wrong, after LoRA on its own verified programs 249 tokens and correct (77 → 98%); mixing in its own programs protects an unseen task (118 of 120 vs 36 with teacher programs). On contest problems fine-tuning did not help.

## 5. Baselines from related work and our methods (all measured here)

| Published baseline | Measured on our tasks |
|---|---|
| CodeT, MBR-exec, majority vote, DeepConf (pick 1 of 3 programs) | 96.0 / 93.7 / 95.7 / 94.7% on clean prompts (Qwen3-8B); our symmetry check 99.7% |
| Scope sentence (2609.14157), System 2 Attention | recover 2–3% of the helper harm / 11 points worse |
| DRAFT (self-written tool docs) | 11–15% vs fixed helper 87–92% (Delaunay) |
| DRoC-style retrieval | .12–.40 below the exact snippet (routing) |
| TroVE-style voting | most accurate against helper harm (91.2 / 95.0%) at ≈2.6k / 1.8k tokens |
| WiSE-FT, SDFT, self-training | keep less of an unseen task (SDFT 85, self-training 104 of 120) or of the in-task gain (WiSE-FT); our self-replay keeps both (118, full gain) |
| AlphaCode filter, Self-Debugging, FrugalGPT-style cascade | used in R3 (examples check, one repair, escalation) |
| Dynamic Cheatsheet-style memory | 31–40% of unseen routing instances (no facts 7%) |

| Our method | Verdict |
|---|---|
| Verify once and reuse; adapt the verified program to a new rule (R2) | works (all models, 3 seeds) |
| Escalate on disagreement between two tool conditions (R3) | works when the two programs' errors are independent (Qwen3), not for gpt-oss |
| Escalate when the examples or a brute-force check disagree (R3) | high-effort accuracy at 82% of the tokens |
| Library portfolio, or fallback to another library when infeasible (R4) | works (4 models) |
| Draft without helpers, then refactor, settled by the symmetry check | small win (Qwen3-32B 91.5% at 0.8k tokens) |
| Verified fact mining from failures | partial (21–40%, unstable) |
| Helper filters, symmetry tests from examples, model-written oracles, retrieved examples, contest fine-tuning, fix chosen from the error message or by the model, docs triggered by low token confidence | no gain |

## 6. Related work, plan and limitations

**Related work.** Prompt context that misleads code (2606.04057; 2609.14157; CodeCrash 2504.14119); tools with unclear contracts (DRAFT; ContractEval 2510.12047); documentation for solver code (DRoC, ICLR 2025; CP-Bench 2506.06052); label-free selection and repair (CodeT, MBR-exec, AlphaCode; Self-Debugging; Olausson et al., ICLR 2024); one program for all instances (FunSearch, HeuriGym; 2605.14141, 2608.27296). **New here:** these effects compared on geometry and optimization with exact answers, one fact at a time, every fix priced in tokens.

**Plan.** Finish the failure → fix map (`docs/notes/FIX_MAP.md`); test whether a second opinion from a *different* model makes the agreement gate work for gpt-oss (a first test flags 41% of its wrong programs at 9% false alarms); a closed API model if access is available.

**Limitations.** The mechanisms (Section 4) were found on generated tasks, and the helper effect shrinks on real problems. The facts in R1 are hand-written; automatic fact mining recovers only part of them. Only open models were tested.

*Figures:* `poc/make_figures_explain.py` (figs 0, 13–17), `poc/make_figures_hard.py` (figs 10, 12).
