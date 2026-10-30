# Solving Problems with LLMs, Accurately and Cheaply

*Tools, Facts, and Checks. Graduate NLP course project proposal (POSTECH CSED490E, Team 5).*

> **About this file.** The proposal in short; Korean version: [PROPOSAL_ko.md](PROPOSAL_ko.md). Every run, number and correction is in
> [docs/FINDINGS.md](docs/FINDINGS.md); each experiment's predictions and results in `docs/prereg/`; how to run everything in [README.md](README.md).

## 1. The problem

**The tasks.** Any task whose answer is exactly right or wrong and can be checked, at least in part, for free: by running it,
executing it, or testing it against the rules the task states. We started with computational math, where the answer is *computed*,
and widened to database queries, tool calls and instructions:

| Kind | Example | Answer | How hard, by a well-known yardstick |
|---|---|---|---|
| Geometry | How many corners does the tightest rubber band around these 10 points have? | 6 | textbook algorithms (convex hull, shoelace area), but exact on moved, turned and mirrored copies |
| Optimization | Plan delivery routes for 100 customers, each with an opening time window, using the fewest kilometres | a route plan | classic OR benchmarks (Solomon 1987); a simple greedy plan is 48% longer than the best known |
| Contest problems | *Make a triangle!* (Codeforces): sticks of 2, 5 and 3 cm; how many cm must be added before they form a triangle? | 1 | Codeforces players' ranks: median 2200 = Master; 46% at Grandmaster level (2400+); 18% solved by none of our 9 model setups |
| Word problems | Process A uses 3 gold and 2 wires to plate 5 coins; B uses 5 gold and 3 wires for 7. With 500 gold and 300 wires, how many coins at most? | 750 | undergraduate OR-course exercises (NL4OPT, a NeurIPS 2022 competition); the hard part is the solver's API |
| Competition math | AIME, MATH-500 | a number | AIME invites roughly the top 2.5–5% of AMC takers |
| Proofs (extension) | Prove a competition statement in Lean 4 (miniF2F), or a geometry theorem (IMO) | a proof the computer accepts | IMO-AG-30: an average IMO gold medallist solves 25.9 of 30 |
| Text-to-SQL | What is the average number of SAT test takers from Fresno schools that opened in 1980? (a database of California schools) | an SQLite query whose rows match the gold query's | BIRD (NeurIPS 2023): data engineers 93%; our 8–14B open models 57–61% with thinking |
| Tool calls | "What's the weather in Seoul in Celsius?", given a `get_weather(city, unit)` function | `get_weather(city="Seoul", unit="celsius")`, or no call when no function fits | BFCL (Berkeley Function-Calling Leaderboard), 3,482 items |
| Instructions | "Write a story in 3 paragraphs, all lowercase, without commas" | a text that meets every constraint | IFEval (Google, 2023): 25 kinds of checkable constraint |

![The problems and their difficulty](figs/ex_problems.png)

On computational problems an LLM can answer in four ways: answer in text, **write a program** and run it, write a program that **calls a solver library** (e.g. OR-Tools for routing), or **think longer** first (a reasoning mode that writes thousands of extra tokens). For computation, text is unreliable: asked for twice the area of one polygon in 8 equivalent copies (moved, rotated, mirrored), Qwen3-8B answers 436, 2944, 392 and 728; the program it writes is right on all 8.

Programs are the right tool when the answer must be computed. On short-answer competition math, text is as good or better (Qwen3.6 on MATH-500: text 98.3%, program 86.8%); there the program is most useful as a *second opinion*: when gpt-oss-20b's text answer and program agree, only 0.3% are wrong (two text answers that agree: 1.5%). On the other tasks the answer is already code-like (a query, a call, a constrained text), and the choice is between answering at once and thinking first.

But cheap answers fail **silently** (a wrong program still prints an answer, a wrong query still returns rows), and thinking is **expensive**: on 311 real contest problems, gpt-oss-120b solves 57% at medium effort (6.8k tokens per problem) and 66% at high effort (30k tokens), 4.4× the cost for 9 more points.

**Goal.** Get exactly right answers on these tasks **effectively** (right under strict checks) and **efficiently** (the fewest tokens, the smallest GPU). The questions are *where* extra effort should go, and how to tell, without labels, that a cheap answer is wrong.

**Why it matters.** Agents already write route planners, schedulers and geometry code, query databases and call tools; tokens are the cost and the waiting time; and many teams have one 24 GB GPU, not a 120B model.

**What we do.** We test each cheap fix (a missing fact, a free check, reuse) against thinking longer, on geometry, routing, scheduling, contest problems, word problems, competition math, proofs, text-to-SQL, tool calls and instruction following, with open models, scoring accuracy and tokens; then we combine the winners into one recipe.

## 2. Findings at a glance

Seven findings, each measured against the usual way (blue: the better way; grey: the usual way or a published method). Section 3 gives an example and the numbers for each; Section 4 turns them into one method, and Section 5 tests it (the "All together" and "Choosing the policy" panels).

![Findings at a glance](figs/fig21_results_glance.png)

![New results](figs/fig22_new_results.png)

## 3. Findings

**Finding 1. Give the fact, not the manual: it beats thinking.**
> *Example* (Qwen3-32B, delivery routes with OR-Tools). With a long OR-Tools reference sheet (routing, but not the capacity rule) it calls a method that does not exist, `RegisterUnaryLongLivingCallback`, and crashes. With 11 lines of exact usage showing the right call, `RegisterUnaryTransitCallback`, it finds the optimal plan (30 problems: 23% with nothing, 3% thinking longer, 7% with the sheet, 77–90% with the exact usage over 3 seeds).

![Finding 1: the exact usage vs a long reference sheet](figs/ex_finding1.png)

Thinking cannot supply a fact the model lacks, and it can make things worse: on word problems (NL4OPT, IndustryOR) thinking *lowers* Qwen3-32B from 65.4% to 52.0%, because while reasoning it invents `Objective().SetMaximize`; with a 6-line snippet thinking helps instead (72.0%). On the 56 Solomon routing benchmarks, three facts together (file layout, "OR-Tools needs integers", a start strategy) take gpt-oss-120b from at most 6% to 100% valid plans. **Less is also more for tools:** 8 helper functions the task does not need lower Qwen3-32B on geometry from 77% to 59%, because it builds its method on an offered helper.

**Finding 2. One fact helps small models most.**
> *Example* (Qwen3-1.7B, word problems). Without the fact its programs check `status == pywraplp.Solver.SUCCESS` or use `solver.INFINITY`, names that do not exist, and almost all of them crash (0.1% solved). The 6-line snippet shows `pywraplp.Solver.OPTIMAL` and `s.infinity()`, and it solves 45%.

The smaller the model, the bigger the gain (Qwen3-32B: 65% → 66%):

![One fact helps small models most](figs/fig20_fact_by_size.png)

**Finding 3. A free check catches mistakes, and two different versions catch more.**
> *Example* (Qwen3-14B, real output). "How many corners does the rubber band around these 10 points have?" Prompt A gives only the task: the program prints 6, correct. Prompt B adds 8 helper functions the task does not need: the program builds on `polar_sort` and prints 0. The two answers differ, so only this problem gets thinking. What a check can miss: on the contest problem *Find Color* a program passes all 3 examples in the statement and still fails hidden test 11.

![Finding 3: two versions of the program](figs/ex_finding3.png)

The examples in a problem statement never reject a correct program, but 24–37% of gpt-oss-120b's *wrong* contest programs pass them too. Checks that look at the problem differently catch more: two programs written with and without the extra tools, or a text answer against a program, make different mistakes. Writing the geometry program with and without the extra tools and thinking only when the two disagree gives 99% at 4.3k tokens, vs 98% at 5.9k for always thinking (Qwen3-32B, 3 seeds). It fails when both versions share the same mistake (gpt-oss-120b's two contest programs).

**Finding 4. Think harder only when a check fails.**
> *Example* (gpt-oss-120b). *Make a triangle!* (rated 800): the quick medium-effort program passes the examples, so it is submitted, correct, at no extra cost. *Arrow* (rated 2000): the quick program prints the wrong corners on the example, so only this problem gets high effort (4k + 13k tokens), and the new program is correct.

![Finding 4: think harder only when the examples fail](figs/ex_finding4.png)

On all 311 contest problems the examples alone give 65.0% at 20.2k tokens (always high effort: 66.2% at 30.1k); also escalating when a quick brute-force program disagrees on small inputs keeps the accuracy of always using high effort (66.3% vs 66.2%) with 18% fewer tokens (24.7k vs 30.1k). On general contest code (LiveCodeBench, 182 problems from 2025, four open models) the non-thinking program first, thinking only when it fails the examples, ties one full think for Qwen3-8B and Qwen3.5-9B (−1.3 points each, at 87–88% of the tokens) and loses for Qwen3-14B and gpt-oss-20b; thinking again when the think's program fails is 3.7–5.5 points more accurate than cheap first, at 1.6× its tokens. On text-to-SQL (BIRD dev, 1,530 questions, three Qwen models), where the free check is only that the query runs and returns rows, 41–43% of the non-thinking queries that pass it are wrong, so the non-thinking query first loses 2.7–5.9 points to one think; the default order (a 2,000-token think first, the full think when its query fails, one more think if that fails) ties the think that is retried on a failure at 69–90% of its tokens. Giving the fact there (a SQLite card and the model's own check-passing queries for similar questions on the same database) raises the non-thinking query by 2.8–3.7 points but does not make it a saving, and lowers the Qwen3 thinks by 1–2 points: only 57–61% of those queries are right, and the fact helps in proportion — a fact the model builds itself is only as good as the check that admits it. This is causal: changing only which queries may enter the library (gold-right, gold-wrong, or agreeing with the model's short think) moves the think by 5–6 points between wrong and right examples, and the precision-weighted model fixed beforehand predicts all 12 cells within 2 points. A second model's quick answer is a better check than the model's own second try where their errors differ: a second sample of the same Qwen3 model repeats 79–90% of its wrong answers on SQL and tool calls, another Qwen generation 33–62%. On tool calls (BFCL, 3,482 items, three models) taking the cheap answer only when the other model's cheap answer makes the same calls, else the default order, is more accurate and cheaper than the default for two of three models (+0.8 / +1.9 points at 71–73% of its tokens) and becomes the default there; on SQL it ties the think retried on failure at 63–69% of its tokens but does not beat the default; on word problems, where two models' wrong programs coincide 56–67% of the time, it saves nothing. The second model has to be about as accurate and come from other training: the same model with a one-line plan before its answer still repeats 38–56% of its wrong answers, and a 3B model of another family agrees too rarely with right answers; both lose to the peer, while an 8B model of another family ties it. On SQL the quick query has to improve as well, and training it does that with labels used only in training (Qwen3-8B, 6,000 BIRD training questions). Rewarded only for being right, its quick queries rise from 46.0% to 50.6%, and taken only when the other model's quick query returns the same rows, else the default order, they beat the default: 61.3% at 1.36k tokens against 59.5% at 1.68k. The gain was predicted beforehand from where the trained query is right, and it is the cascade's, not only the training's: run with the same trained weights, the default gains under a point, and the cascade still beats it by 1.8 points (62.0% at 1.32k tokens). Rewarded instead for the cascade's own value (deciding itself, after seeing its query's result, whether to answer or think), the model learns to think on every question: a check pays only if it keeps right answers where the default fails at least 2.5 times as often as wrong answers where the default succeeds, and the model's view of its own result does not get there, while the other model does. The same training carries to tool calls (6,000 open ToolACE requests, none from the test benchmark): Qwen3-8B's quick calls on BFCL rise by 5.1 points, almost all of it by learning when not to call, and taken only when the other model's quick calls agree, else the default order, they beat the default: 85.2% at 0.27k tokens against 83.9% at 0.38k. The other model itself calls where it should not, so it confirms only a sixth of the newly learned abstentions; with a fixed partner the cascade can gain at most the share of questions that partner gets right and the default gets wrong (4.6 points on BFCL, 6.8 on SQL), so we also trained the partner. The recipe holds for a second model (Qwen3-4B: +0.94 over its own default), and training the partner helps as much as training the answering model: two trained quick models (Qwen3-8B answering, Qwen3-4B checking) reach 86.5% at 0.27k tokens, 2.6 points above the default and 1.25 above the best untrained partner. The two trainings simply add up, with no extra gain from training both, because what both models learn in common includes the same new mistakes. We are now testing training the quick model directly for the cascade it is deployed in: rewarding answers the partner can confirm where the default fails, and penalising wrong answers the partner shares where the default is right.

**Finding 5. Repeated problems need only one checked program.**
> *Example* (gpt-oss-120b, Solomon routing: think of each instance as one day's orders). Writing a new program every day gives a valid plan on 7% of 48 days (≈ 86k tokens). Writing 16 programs once, keeping the one that is valid on 8 past days and reusing it gives a valid plan on 94% (28k tokens in total).

![Finding 5: one checked program for 48 days](figs/ex_finding5.png)

The reused programs also work on 4× larger instances (60 of 60). When the rules change (job-shop scheduling gains release dates), asking the model to *edit* the working program with "change as few lines as possible" beats starting over (Qwen3-32B: 10% → 68% valid schedules).

**Finding 6. The fact can be found without a human.**
> *Example* (Qwen3-8B, MAMO). "Products X, Y, Z cost $10, $15 and $20; X + Y ≤ 5000, Y + Z ≤ 4000, X + Z ≥ 2000. What is the minimum cost?" (answer 20000). Without a fact the program calls `solver.Objective().Minimize()`, which does not exist, and crashes. The fact is picked automatically: the model's own program for another problem (vans and trucks) that passed the free check, which calls `solver.Minimize(v)`. With it, both programs write `solver.Minimize(10*x + 15*y + 20*z)` and print 20000; they agree, so no thinking is needed (0.6k tokens; thinking alone took 5.3k).

![Finding 6: the model's own checked program as the fact](figs/ex_finding6.png)

We tested this on a benchmark we never used before: MAMO (863 optimization word problems) was held out until the end. The fact is mined automatically: the model's own shortest program that passed the free check on the other word-problem benchmarks. With it, writing the program twice and thinking only when the two disagree matches the hand-written fact: gpt-oss-20b 78.8% vs 78.9% (within 1.2 points on 3 seeds), Qwen3-32B 75.3% vs 70.7% (better on all 3 seeds), Qwen3-14B 71.7% vs 71.4% (within 1.6 points on 3 seeds), Qwen3-8B 71.0% vs 72.0% (−0.9 to +2.2 on 3 seeds, at a third fewer tokens; no fact: 73%, 60%, 46%). Giving this fact first beats always thinking at 12–22% of its tokens. This works within one kind of problem: a program borrowed from a different problem type misleads (14–21 points below the hand-written fact on the optimization suite), and a bare list of the library's names hurts (Qwen3-32B 66.2% → 56.1%). The same kind of fact also fixes *formulation* errors that repeat across a problem type: gpt-oss-20b writes every MAMO travelling-salesman problem so that it has no solution (0 of 34); thinking repeats the mistake (4% at 3.6k tokens), and a sentence describing the right formulation is misapplied (9%) — so is the same note written as code (5%) — but the complete checked program of a similar problem fixes it (52% at 0.6k). Showing every problem the checked program of its most similar other problem (no labels) raises the whole recipe on MAMO by 1–7 points at 17–33% fewer tokens (3 models × 3 seeds); for the Qwen3 models most of the gain comes from other models' programs. It keeps most of this gain when problems arrive one by one (+0.4 to +3.9 points), but not on NL4OPT + IndustryOR, whose problems rarely repeat (−0.5 to −1.4 points, at fewer tokens). **On OptMATH, a harder benchmark never used before** (100 problems, 3 seeds), the core rule generalises: thinking only when the cheap program visibly fails is at least as accurate as always thinking at 62–90% of its tokens for all three 24 GB-GPU models (gpt-oss-20b 38% @ 3.7k vs 33% @ 5.4k), within 1–2 points of the trained STORM-4B (40% @ 14.1k) at a quarter of its tokens; with STORM as the fallback it beats STORM alone (43% @ 7.0k). The usage example mined from easy problems and the two-agreeing-programs check do not carry over to OptMATH, whose failures are formulation and data errors. **On a second unseen benchmark, OptiBench** (605 problems, 3 seeds), the rule holds again (gpt-oss-20b 71% @ 1.2k vs 69% @ 2.1k always thinking; Qwen3-14B 59% @ 3.4k vs 48% @ 6.5k; Qwen3-8B ties at 64% of the tokens), and here, where the small models' failures are usage errors, the fact pays: with the checked program of the most similar other problem as the fact (no labels), Qwen3-14B reaches 64% @ 1.8k and Qwen3-8B 63% @ 2.7k. The trained STORM-4B leads here (79% @ 7.9k vs gpt-oss-20b's 73% @ 1.0k); our cheap program with STORM only on a visible failure gets 76% @ 2.3k. Against the standard test-time baseline, majority voting over three thinking runs (75% @ 6.3k for gpt-oss-20b), thinking only on a visible failure with that vote as the fallback matches it at a third of the tokens (75% @ 1.9k). Across 29 model × benchmark cells (including two more unseen benchmarks, BWOR and LogiOR, and a model from another family, Nemotron-3-Nano), the label-free library of checked programs raised the first program in 25 (up to +34 points; not on BWOR / LogiOR for Nemotron-3-Nano, whose failures there are formulations). **On four held-out geometry tasks** the rule holds for gpt-oss-20b (99% @ 0.8k vs 93% @ 1.7k always thinking) and Qwen3-14B (84% @ 2.9k vs 77% @ 8.6k), but not for Qwen3-8B (60% vs 74%): a third of its programs pass the free check yet are wrong, mostly on edge cases the given input never contains (a collinear vertex, a point on an edge), and a second program by the same model, brute force or resampled, repeats them (it catches 41–45%; at best 66% @ 6.5k); edge-case tests the model writes from the statement see them but get the same boundary cases wrong, so they send almost every problem to thinking (73% @ 9.1k); relations the model states without computing answers catch the right failures but are often wrong too (68% @ 7.2k). Even a perfect check would reach only 75% @ 70% of always-thinking's tokens for this model: its fact programs are wrong too often. **On two more unseen benchmarks, BWOR and LogiOR** (174 harder problems; the cheap program is right on 7–42%), thinking only on a visible failure ties always thinking for gpt-oss-20b and Qwen3-14B (within ±2 points, 95% intervals include zero) at 53–88% of its tokens, and loses for Qwen3-8B (BWOR −8 points): 38–75% of the programs that pass the free check are wrong there. Requiring two programs to agree, or checking the printed solution against every constraint of the text with a checker the model writes, recovers or beats always-thinking's accuracy (the checker: +3 to +4 points for gpt-oss-20b and Qwen3-14B; it does not carry over to OptMATH, whose solutions need the formulation to be checked) but no longer saves tokens — on problems this hard, no check can; one short repair turn with the error before thinking adds +1 to +4 points at no extra cost (all models, OptiBench and OptMATH); the label-free library still pays (Qwen3-14B on LogiOR +10 points over always thinking at 74% of its tokens).

**Finding 7. Proofs need a specialized model, not a fact.**
> *Example* (miniF2F). Prove: if x < 100 and 9x mod 100 = 1, then x = 89. Qwen3-32B's 8 attempts cite lemmas that do not exist (e.g. `Nat.ModEq_iff_modEq`) and all fail. Goedel-Prover-V2-8B writes `interval_cases x <;> norm_num at h₁ ⊢ <;> omega`, which simply checks all 100 values, and Lean accepts it.

![Finding 7: a specialized prover vs a general model](figs/ex_finding7.png)

In Lean (miniF2F, 244 statements, 8 attempts) a specialized prover that fits one 24 GB GPU proves the most: Goedel-Prover-V2-8B 180 (74%), DeepSeek-Prover-V2-7B 165, vs general models Qwen3.6 133, gpt-oss-20b 66, Qwen3-32B 31. For general models none of our steps helps: a verified proof of a similar statement (133 vs 133), thinking (129), a 10-line inequality toolkit (21 vs 24 of 50 bounds). Even for the provers, repairing a failed proof from Lean's error messages proves half as many as a fresh attempt (Goedel: 11 vs 22 of 107). Geometry proofs: AlphaGeometry's symbolic engine alone proves 187 of 231 JGEX problems and 12 of 30 IMO problems; auxiliary points proposed by gpt-oss-20b add 13 JGEX problems, but only one IMO problem (2014 P4, with the point "the midpoint of BC") is unlocked by any model.

## 4. Our method: a recipe built from the findings

![The recipe](figs/fig18_recipe.png)

1. **Write a program** for anything that needs exact computation (Section 1).
2. **Add the missing fact** (findings 1–2): a few lines of exact usage, not a long manual and not extra tools; written by hand, or mined automatically from the model's own checked programs (finding 6).
3. **Run a free check** (finding 3): the examples in the problem statement, or two different versions that should agree.
4. **Think harder only when the check fails** (finding 4); on word problems, first one cheap repair turn shown the error (held out: more accurate than going straight to thinking on OptiBench and OptMATH for all four models tested, e.g. +6.0 points on OptMATH for Qwen3.5-9B, at fewer tokens; on BWOR / LogiOR it hurt Qwen3-8B, whose repaired programs run but are wrong).
5. **When the same problem returns with new data, reuse the program that passed** (finding 5).

**One real problem through the recipe** (Qwen3-8B, the MAMO problem of finding 6): without the fact the program crashes; with it, two versions both print 20000 and agree, so no thinking is needed: 0.6k tokens instead of 5.3k. The free check needs no answers and depends on the kind of problem (bottom row).

![Our method on one real problem](figs/ex_method.png)

## 5. Does the whole recipe pay off?

We compared ways to spend the same budget on the geometry suite (108 problems) and the optimization suite (100 problems: routing, scheduling, packing), each solved by 3 models (624 runs), on 3 seeds. Contest problems, word problems and proofs are tested separately (Sections 3 and 6):

![Cost vs accuracy of each policy](figs/fig19_cost_accuracy.png)

| Policy | solved | tokens per problem |
|---|---|---|
| first program, no help | 63% | 0.7k |
| think on the hardest-looking problems (the usual "compute by difficulty") | 74% | 4.1k |
| think when the check fails | 77% | 4.2k |
| choose the fix by failure type | 83% | 4.2k |
| **fact first, think only when the check fails** | **87%** | **2.5k** |
| same, with automatically retrieved facts (BM25) | 84% | 3.3k |

The recipe is both the most accurate and among the cheapest, on every seed. Difficulty is the wrong signal: spending thinking on the hardest-looking problems is worse than spending it where a check fails.

**Which policy for a new task?** How it works: label 30 problems of the new task, run four policies on them (one cheap program; fact first; fact first with two versions; always think) and keep the one with the best accuracy after a token penalty. Over 63 model × task × seed cells, "fact first, think on failure" is the best fixed default (it loses 1.4 points on average to the best policy of each cell; always thinking loses 8.4, counting 0.5 points per 1k tokens); labelling 30 problems of a new task and picking the best policy on them cuts the loss to 0.6 points (on the held-out MAMO: 0.8–1.4; on 45 cells of five more held-out benchmarks: 0.87, and in Qwen3-8B's cells where the recipe loses, geometry and BWOR, the 30 labels pick thinking: 0.74 instead of 7.8). Held out, always thinking must get the same fact (it helps thinking too, by up to +22.6 points): then fact first ties or beats it on all five benchmarks for gpt-oss-20b and for Qwen3.5-9B, a model the recipe was never developed with (at 30–78% of the tokens), while for the Qwen3 models on OptiBench / BWOR thinking with the fact is 4–12 points more accurate — unless a 2k-token self-review in thinking mode gates the cheap program, which makes them tie or win in all six cells (saving 27–30% on OptiBench); no fixed policy is best everywhere (regret ≥ 3.3), and 30 labels pick within 0.85 points over 60 cells. On a model from another family, Nemotron-3-Nano-30B-A3B, the recipe behaves like on Qwen3: fact first loses 6–12 points on OptiBench / BWOR / LogiOR (33–70% of its passing programs are wrong), the self-review gate ties or beats thinking with the fact in all five cells but saves no tokens (94–109%), and 30 labels pick within 1.05 points. What fixes a leaky model is a thinking first step: write the first program after thinking with the fact for at most 2,000 tokens and think fully only if it visibly fails. Over 14 cells it was not chosen on this never loses to always thinking with the fact (−0.3 to +10.1 points), saves 8–51% of the tokens on word problems (Nemotron-3-Nano: +3.3 to +6.3 at 72–92%), and closes the last losing cell (Qwen3-8B geometry: −16.7 → −0.3); as a fixed default without labels it loses only 1.47 points to each cell's best over 54 cells of four models. One caveat changes how all of this reads: the baseline was one think that ignores its own visible failures. Given the same free check (think again when its program visibly fails), thinking gains +2.5 to +12.3 points on the hard word problems and is more accurate than every cheap-first policy there, even for gpt-oss-20b (BWOR −10.2 at 37% of the tokens). The recipe is the cheap end of a frontier, not a free saving: the free check is worth applying to every step, and without labels the best order is short think, then full think, then a retry on a visible failure (1.74 points below each cell's best over 54 cells; one think: 7.64). The same order fixes gpt-oss-20b, whose first program came from low reasoning effort (0.7–0.8k tokens): with a medium-effort think cut at 2,000 tokens as the first step, short think → think → retry ties the think-with-retry on BWOR (−2.0 points) and LogiOR (+3.3) at 69–83% of its tokens and beats it on OptiBench (+2.0). It also holds unchanged on a larger model, Qwen3-32B (2 × RTX 3090): short think → think → retry is the best policy on OptiBench, BWOR and LogiOR, and a program without thinking still trails by 5–12 points there, so the leak does not shrink with size. The short think needs 2–4k tokens (at 1k Qwen3-8B loses 3–6 points on OptiBench / LogiOR). And there is now a label-free signal for when a passing cheap program is wrong: run the short-think program too and compare. On 311 Codeforces geometry problems with hidden tests, a sample-passing non-thinking program that agrees with the short-think program on every test input is right 93–97% of the time, one that disagrees 19–34% (word problems: 78% vs 16%); it fails only where both modes share a wrong formulation (OptMATH). It flags single programs but does not replace the 30 labels: labelling the pilot by the majority answer of its programs (both modes) picks the policy worse than the fixed order (2.00 vs 1.74 points below each cell's best; 30 labels: 1.35), because programs that share a mistake outvote the truth (Qwen3-8B geometry, OptMATH). On three task types the pilot was not developed on (contest code, tool calls, instructions; 48 cells) the 30 labels do not beat the no-label default "short think first, full think only when the check fails" except on contest code (pilot 1.29 / 1.96 / 1.77 points below each cell's best, the default 3.07 / 0.23 / 0.92): choosing among ten close policies from 30 labels costs about two points of noise, so labels mainly tell a contest-like task, where one full think should go first, from the rest. On text-to-SQL, a fifth task type tested before any of its results were seen, the default again beats the 30 labels (0.33 vs 2.25 points below each cell's best).

**Small GPUs.** Once they get the fact, models that fit one 24 GB GPU (e.g. RTX 3090) match or beat Qwen3-32B. Optimization suite with the recipe: gpt-oss-20b 94–97%, Qwen3-14B (4-bit) 87–92%, Qwen3-32B 79–85%. Word problems: gpt-oss-20b with the recipe 73.0% at 0.7k tokens, Qwen3-32B with the fact and always thinking 72.0% at 5.5k. Competition math: Qwen3-14B (4-bit) thinking 97.3% / 73.3% on MATH-500 / AIME (Qwen3-32B: 97.4% / 77.2%). Contest geometry: gpt-oss-20b, escalating from low to medium effort when the examples fail, solves 54.6% at 11k tokens (gpt-oss-120b at medium: 56.8%). Below 14B the optimization suite stays at 47% or less whatever we add; geometry is solved from 4B up.

## 6. Related research and how we compare

### 6.1 Where this work sits

| Theme | Closest work | What they do | What we add |
|---|---|---|---|
| Programs instead of text | PAL, Program-of-Thoughts; Mixture-of-Thought cascade (ICLR 2024) | the model writes code; MoT escalates when a text answer and a program disagree | when a program helps (computation) and when it does not (competition math); text–program agreement as a free check |
| Library facts for solver code | DRoC (ICLR 2025), CP-Bench (2506.06052), CloudAPIBench (2407.09726), DRAFT | retrieve or rewrite documentation for API / solver code | an exact snippet beats the manual *and* thinking; near-miss documents ≈ no document; the fact can be mined from the model's own checked programs |
| Misleading context and tools | "Invisible Lottery" (2606.04057), unneeded tools (2609.14157), CodeCrash, System 2 Attention | prompt cues steer or hurt generated code | the effect on exact geometry (77% → 59%), and a fix that turns it into a check (two versions) |
| Choosing a program without labels | CodeT, MBR-exec, AlphaCode's example filter, DeepConf, S* | pick the best of several sampled programs | one program checked on moved copies of the given input (99.7% vs CodeT 96.0%) |
| Spending test-time compute | compute-optimal scaling (Snell et al. 2025), FrugalGPT / AutoMix cascades, DART; Thinkless and AdaptThink (RL-trained switch) | more compute for harder problems; a learned think / no-think switch | difficulty is the wrong signal; a fact first and an execution check decide, with no training (87% vs 74%); on AdaptThink's own base model (MATH-500) the learned switch is cheaper (91.7% @ 1.9k vs our gate 93.0% @ 3.9k), and our check on its skipped answers adds 2.2 points |
| LLMs for optimization modeling | ORLM, STORM / CALM, EVOM, OR-R1 (fine-tuned); OptiMUS, OptiSkill (agents, skill banks from teacher programs checked against answers) | train a modeling model, or build agents | training-free and label-free; on held-out MAMO a 24 GB-GPU model with the recipe matches the fine-tuned ORLM-8B (below) |
| One program for many instances | FunSearch, HeuriGym, ARS, 2605.14141, 2608.27296 | write a solver once per problem family | the measured gap (7% vs 94%), choosing the program without answers, editing a verified program when the rules change |
| Proofs | Goedel-Prover-V2, DeepSeek-Prover-V2, AlphaGeometry | specialized provers; a symbolic engine plus constructions from a language model | the recipe's facts and checks do not carry over to proofs: a specialized 8B prover is the right tool |

### 6.2 Same problems, same harness

All measured here, with the same problems, models and checks; accuracy @ output tokens per problem.

| Task (model) | Published method | Its result | Ours, same problems |
|---|---|---|---|
| Where to spend thinking (208 geometry and optimization problems × 3 models) | think on the hardest-looking problems (compute-optimal scaling, Snell et al. 2025) | 74% @ 4.1k (best fix per difficulty bin: 79% @ 5.2k) | **fact first, think on failure: 87% @ 2.5k** |
| | think whenever the check fails, no fact (FrugalGPT-style cascade) | 77% @ 4.2k | |
| Contest geometry (gpt-oss-120b, 311) | always high effort (reasoning-model default) | 66.2% @ 30.1k | **66.3% @ 24.7k** (examples + brute-force check) |
| | keep programs passing the examples, else high effort (AlphaCode filter + cascade) | 65.0% @ 20.2k | |
| | one repair round from the error (Self-Debugging), from low effort | 53.1% @ 4.6k | |
| Picking 1 of 3 programs (Qwen3-8B, geometry, 300) | CodeT (model-written tests) | 96.0% (+340 tokens) | **symmetry check: 99.7%** (no extra tokens) |
| | majority vote (self-consistency) / DeepConf (confidence) / MBR-exec | 95.7% / 94.7% / 93.7% | |
| Library documentation (Qwen3-32B, CVRP) | a long reference sheet (routing without the capacity rule) | 7% | **exact snippet: 77% @ 1.7k** |
| | BM25 retrieval / DRoC (decompose, retrieve per constraint; ICLR 2025) | 48% @ 2.3k / 72% @ 2.1k | |
| Unneeded tools (Qwen3-32B, 5 geometry tasks) | scope sentence "use a helper only if needed" (2609.14157) / System 2 Attention | 76% / 64% (no fix: 75%) | **only the needed tools: 92%** |
| Daily routing (gpt-oss-120b, 48 new Solomon instances) | a new program per instance (standard practice) / + one repair round | 7% / 25% | **reuse one checked program: 94%** (28k in total); hand-written facts: 100% |
| | model-written lessons notebook (Dynamic Cheatsheet) | 31–40% | |
| Word problems (Qwen3-32B, NL4OPT + IndustryOR) | always think before writing the program, no fact (reasoning-model default) | 52.0% | **fact first, think on failure: 72.4% @ 1.3k** (always think + fact: 72.0% @ 5.5k) |
| Word problems and competition math (Qwen3-32B) | majority vote of 3 samples (self-consistency) | word problems: 3 programs 68.4% @ 1.1k, 3 thinking runs 79.4% @ 16.4k; MATH-500: 3 text answers 89.2% @ 2.3k | **72.4% @ 1.3k** (fact first) / **97.2% @ 3.4k** (text = program, else think) |
| Lean proofs (Goedel-Prover-V2-8B, 107 failed statements) | repair from the compiler's error messages (Self-Debugging-style) | 11 proved | a fresh attempt: 22 (same tokens) |
| Word problems, held-out MAMO (863) | ORLM-LLaMA-3-8B, a fine-tuned modeling specialist | 69.5% @ 1.1k | **Qwen3-8B, no training: 69.5% @ 1.0k** (71.0% with the two-version check); **gpt-oss-20b 78.8% @ 1.9k** |
| Competition math (Qwen3-32B, MATH-500) | accept when text and program agree, else think (Mixture-of-Thought cascade, ICLR 2024) | 97.2% at 77% of always-thinking's tokens (97.4% @ 5.4k); on AIME it costs more than always thinking | used as a check (step 3) |

### 6.3 Numbers reported in papers (different harnesses and graders; for orientation)

| Benchmark | Reported in the paper or model card | Ours |
|---|---|---|
| MAMO Easy / Complex | ORLM-LLaMA-3-8B 82.3 / 37.4% (fine-tuned); STORM-Qwen3-4B 86.3 / 70.3% (SFT + RL); OptiSkill with frontier models 90.8–94.3 / 56.8–64.0% | no training: Qwen3-14B 82.8 / 37.4%, gpt-oss-20b 85.6 / 57.8%; ORLM-8B in our harness 80.5 / 35.5%; STORM-4B in our harness 85.7 / 69.5% (81.8% overall) at 8.4k tokens, 4.4× gpt-oss-20b's |
| miniF2F, 32 tries | Goedel-Prover-V2-8B 84.6% | the same model in our harness: 76.6% |
| IMO-AG-30 geometry | AlphaGeometry 25 / 30; its symbolic engine alone 14 | the engine alone 12 in our setup; with points proposed by our models 13 |

**What is new here.** (1) Every method is compared on exact-answer benchmarks in one harness, with accuracy *and* tokens. (2) *Facts before compute*: one exact fact plus a free execution check beats spending thinking by difficulty. (3) The fact needs no human and no answers: the model's own checked programs work within a problem family. (4) Training-free models on one 24 GB GPU reach a fine-tuned specialist (ORLM-8B) on a held-out benchmark.

## 7. Where the recipe stops

- **Proofs** need a specialized prover, not a fact (finding 7).
- **Missing knowledge.** For factual questions (PopQA), thinking adds only 1.8–5 points at 70–200× the tokens, and only for well-known facts.
- **Checks leak.** A wrong program that passes the check is never sent to thinking; that caps every policy above. On word problems 12–16% of problems leak, but a perfect check would add only 0.8–2.6 points for 14B+ models (5.6 for Qwen3-8B): thinking solves only 7–16% of the leaked problems, and some are wrong labels. On held-out geometry most of Qwen3-8B's leaked programs are right on the given input and wrong only on edge cases it does not contain, so a check has to exercise the edge cases the statement names: even a program from a different model (gpt-oss-20b) catches 26 of the 27 leaks wrong on the given input and none of the 37 edge-case-only ones — and that model alone is far better (99.0% at 0.8k tokens).
- **Automatic facts stay within a problem family** (finding 6): the model copies another type's library and formulation. Mining one fact per problem type is next; BM25 retrieval keeps most of the gain meanwhile (84% vs 87%).
- **Thinking settings matter.** With our sampling settings Qwen3.6 ran out of its 28k-token budget on 213 of 1,680 math problems; with the model card's settings and an 80k budget only 4 did, and thinking rose from 91.7 / 47.8% to 99.6 / 94.4% (MATH-500 / AIME), above text without thinking (98.3 / 68.3%). Most of the gain is the budget; the sampling adds about 3 points.
- Open models only; mechanisms were first found on generated tasks.

## 8. Setup

- **Strict scoring.** Geometry: right on all 8 copies of each input. Routing and scheduling: every rule satisfied, length compared with the best known. Contest problems: all official tests. Math and word problems: the exact answer.
- **Fair comparisons.** One change at a time, predictions written before each run, 3 seeds per claim, and accuracy always reported with its token cost (output tokens; counting the prompt too, the held-out savings shrink — e.g. the library recipe on OptiBench from 46% to 67% of always thinking's tokens for gpt-oss-20b — but never reverse: 37–97% across all held-out cells). Held-out comparisons carry 95% intervals over problems.
- **Models** (open, run locally): Qwen3 1.7B–32B, Qwen3.6-35B-A3B, gpt-oss-20b and 120b; for proofs Goedel-Prover-V2-8B and DeepSeek-Prover-V2-7B.
- **Benchmarks:** 13 generated geometry tasks; 8 generated optimization problems; 311 Codeforces geometry problems (CodeContests); 56 Solomon routing instances; 82 job-shop instances (OR-Library and larger); NL4OPT + IndustryOR (345 word problems); MAMO (863 word problems, held out); MATH-500 + AIME 2024/2025 (560); miniF2F (244 Lean proofs); IMO-AG-30 and JGEX-AG-231 (geometry proofs); PopQA (1,500 questions).

## 9. Plan

Done since the last version: contest geometry and competition math on 24 GB GPUs; Qwen3.6 with the model card's settings (headline unchanged: 86.7–87.5%); automatic facts and the held-out MAMO test; choosing the policy from 30 labels; proofs (Lean, geometry).

1. MAMO replication done on 3 seeds for gpt-oss-20b, Qwen3-14B, Qwen3-8B and Qwen3-32B (Qwen3.6: one seed). Baselines on our harness done (ORLM, STORM, AdaptThink). Next: on MAMO about half of the errors left after the recipe are disputed labels (7.6% of problems); the rest are mostly one wrong formulation repeated across a problem type (TSP order constraints, supply balances written as equalities) that a repair turn and thinking do not fix; testing whether one fact does. (STORM's no-thinking mode is broken, so the recipe cannot sit on top of it.)
2. Automatic facts across problem types: mine one fact per problem type instead of borrowing another type's program.
3. Final report and slides; a closed API model, if access is available.

*Figures:* `poc/make_figures_frame.py` (figs 18–22), `poc/make_figures_explain.py` (fig 14), `poc/make_figures_hard.py` (fig 12).
