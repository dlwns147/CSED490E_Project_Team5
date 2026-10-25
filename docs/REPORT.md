# Facts First, Think on Failure: Solving Computational Math with LLM-Written Programs

*Draft of the final report, POSTECH CSED490E Team 5 (Sangjun Lee, Seongbin Park). Started 2026-10-23 from `PROPOSAL.md`, the
pre-registrations in `docs/prereg/` and `docs/notes/REPORT_OUTLINE.md`; format and length to be fitted to the course template.*

## Abstract

Language models can solve computational problems — geometry, scheduling, routing, optimization word problems — by writing a program, but
programs fail silently and "thinking longer" (long reasoning before answering) is expensive. We ask where a fixed token budget should go,
for open models from 8B to 120B on RTX 3090s. The recipe: write a program, add the missing fact (a few lines of exact library usage, or a
checked program for a similar problem found without labels), run a free check (the program runs and prints a value; outputs on
transformed copies agree), and spend more thinking only where the check visibly fails. The fact is the main lever: the label-free
library raises the cheap program in 25 of 29 model × benchmark cells and raises thinking by up to 23 points. The comparison must be
matched in the fact *and* in the check: one think that ignores its own visible failures is a weak baseline (it is never the best policy
over 54 cells), and giving thinking the check — think again when its program visibly fails — adds +2.5 to +12.3 points on hard word
problems. Against that baseline the recipe is a frontier, not a free lunch: a non-thinking program first costs 37–51% of the tokens and
matches it where the check holds (Qwen3.5-9B, geometry), but trails it on the hardest word problems (2–10 points, even for gpt-oss). For
models whose free check leaks (Qwen3, Nemotron-3-Nano: passing non-thinking programs are wrong 33–79% of the time), writing the first
program after a short think (2,000 tokens with the fact) never loses to one full think in 14 cells it was not chosen on (−0.3 to +10.1),
saves 8–51% of the tokens on word problems and closes the last losing cell (Qwen3-8B geometry: −16.7 → −0.3). Without labels the best
fixed order over 54 cells of four hybrid-thinking models is short think → full think → retry on a visible failure (1.74 utility points
below each cell's best; one think: 7.64); 30 labelled problems choose per cell within 1.35. Where the check is perfect (Lean proofs) the
rule becomes "sample cheaply, then think"; where it leaks, it bounds label-free self-training as it bounds the recipe.

## 1. Introduction

A program is the natural answer format for a problem whose answer must be computed: the model writes the algorithm, the computer does the
arithmetic. Asked for twice the area of one polygon in eight equivalent copies (moved, rotated, mirrored), Qwen3-8B answers in text 436,
2944, 392 and 728; the program it writes is right on all eight. But programs fail in two ways that text answers hide less well: they crash
on a library call that does not exist, or they run and print a wrong number. The usual remedy is to let the model think longer before it
writes the program, at several times the tokens.

We ask a cost question: **for a given model and problem, where should extra effort go?** Our answer is a recipe built from controlled
experiments, then tested on held-out benchmarks:

1. **Write a program** for anything that needs exact computation.
2. **Add the missing fact**: the few lines of exact usage the model lacks, or the model's own checked program for a similar problem
   (no human, no labels) — not a long manual, not extra tools.
3. **Run a free check**: the program runs and prints a value; its outputs on transformed copies agree; the statement's examples pass.
   For a model whose free check leaks, add a short self-review in thinking mode (≤ 2k tokens) of the passing program (chosen by the
   30-label pilot: on a model whose check is already good it costs 18–37% more tokens for little accuracy).
4. **Think harder — given the same fact — only when the check fails**; on word problems after one cheap repair turn shown the error.
5. **Reuse** a checked program when the same problem returns with new data.

Contributions: (i) every method is compared in one harness with accuracy *and* tokens, against thinking given the same fact — the
comparison most cascade and when-to-think evaluations leave confounded; (ii) an exact decomposition that predicts, per model and
benchmark, whether thinking only on failure is a pure saving or a trade, and a 2k-token self-review gate that turns the trade into a saving
or a tie for the Qwen3 models; (iii) facts without a human or labels: other runs' checked programs for similar problems, and the same
programs as fine-tuning data; (iv) held-out evaluation on five unseen benchmarks and an unseen model, with 95% intervals and pre-registered
predictions, including the refuted ones. What is established elsewhere (cascades between models, sampling with a verifier on proofs,
self-training and its collapse) is marked as such (§6.5).

![The recipe](../figs/fig18_recipe.png)

## 2. Setup

**Problems.** Development: 13 generated geometry tasks (convex hull, polygon area, point in polygon, segment intersections, closest pair,
lattice points, rectangle union, Delaunay check, diameter, ...) and 8 generated optimization problems (knapsack, TSP, colouring, scheduling,
bin packing, vertex cover, CVRP, VRPTW); NL4OPT + IndustryOR word problems (345); 311 Codeforces geometry problems with official tests; 56
Solomon routing instances; job-shop instances. Held out (never used to design the recipe): MAMO (863), OptMATH (100), OptiBench (605),
BWOR (82), LogiOR (92), and four geometry tasks (polygon overlap, convexity, points in a triangle, convex clipping; 96 instances).

**Models.** gpt-oss-20b (MXFP4), Qwen3-14B-AWQ (4-bit), Qwen3-8B — all fit one 24 GB GPU; Qwen3.5-9B (bf16, one RTX 3090) as a model
never used in development (§5.4); Qwen3-32B-AWQ, Qwen3.6-35B-A3B and gpt-oss-120b as references; trained baselines STORM-Qwen3-4B and ORLM-LLaMA-3-8B. Served with vLLM 0.22; cheap programs without thinking (gpt-oss at
low effort), thinking with a 16k-token budget (gpt-oss at medium effort).

**Grading.** Geometry: right on all eight copies of each input (moved, rotated, mirrored, permuted, scaled, shifted by 10^9, degenerate).
Word problems: the objective within 1e-2 absolute or 1e-3 relative ('No Best Solution' counts as a value). Contests: all official and
generated tests. Routing / scheduling: every constraint satisfied, compared with the best known solution.

**Cost and protocol.** Cost = output tokens per problem (input tokens reported where prompts differ). Every experiment was pre-registered
with numerical predictions and a decision rule before running (`docs/prereg/`), run with 3 seeds, and refuted predictions are reported
as such. Held-out comparisons carry paired bootstrap 95% intervals over problems.

## 3. Why each step: development findings

**Facts beat thinking when the model lacks knowledge.** Qwen3-32B routing deliveries with OR-Tools: with nothing 23%, thinking longer 3%,
a long reference sheet 7%, eleven lines of exact usage 77–90% (3 seeds). Thinking cannot supply an API fact the model lacks and can invent
more (`Objective().SetMaximize`); on word problems thinking lowers Qwen3-32B from 65.4% to 52.0%, while thinking with a 6-line snippet
reaches 72.0%. Unneeded tools hurt too: eight helper functions the task does not need lower Qwen3-32B on geometry from 77% to 59%.

**One fact helps small models most.** Qwen3-1.7B on word problems: 0.1% → 45% with the 6-line snippet (its programs check
`Solver.SUCCESS`, a name that does not exist); Qwen3-32B: 65% → 66%.

![One fact helps small models most](../figs/fig20_fact_by_size.png)

**A free check catches mistakes; different views catch more.** Writing the geometry program with and without the extra tools and thinking
only when the two disagree gives 99% at 4.3k tokens vs 98% at 5.9k for always thinking (Qwen3-32B). The check leaks when both views share a
mistake: 24–37% of gpt-oss-120b's wrong contest programs pass the statement's examples.

**Think harder only when the check fails.** On 311 contest problems gpt-oss-120b at medium effort solves 56.8% at 6.8k tokens and at high
effort 66.2% at 30.1k; escalating to high effort only when the examples fail or a quick brute-force program disagrees gives 66.3% at 24.7k.

**Reuse a checked program.** Solomon routing (48 new instances): a new program per instance gives a valid plan on 7%; writing 16 programs
once, keeping the one valid on 8 past instances and reusing it gives 94% (28k tokens in total).

## 4. Development result: where to spend thinking

On the geometry (108) and optimization (100) suites, three models (Qwen3-32B-AWQ, Qwen3-8B, Qwen3.6-35B-A3B) × 3 seeds:

| policy | solved | output tokens per problem |
|---|---|---|
| first program, no help | 63% | 0.7k |
| think on the hardest-looking problems (difficulty-based, as in compute-optimal scaling) | 74% | 4.1k |
| think when the check fails (no fact) | 77% | 4.2k |
| choose the fix by failure type | 83% | 4.2k |
| **fact first, think only when the check fails** | **87%** | **2.5k** |
| same, facts retrieved automatically (BM25) | 84% | 3.3k |

Difficulty is the wrong signal: thinking where a cheap check fails beats thinking where problems look hard, and adding the fact first
makes it both more accurate and cheaper. Choosing among four policies from 30 labelled problems of a new task loses 0.6 points of utility
on average; using fact-first as a fixed default loses 1.4. The thinking arms of this table think without the fact (on the optimization
suite; the geometry thinking arm has the helpers); the held-out tests (§5.1) compare against thinking given the same fact, which is the
harder baseline.

![Cost vs accuracy](../figs/fig19_cost_accuracy.png)

## 5. Held-out tests

### 5.1 The core rule on unseen benchmarks
Fact first, think only on a visible failure (FF: the cheap program with the fact; thinking — given the same fact — only if it crashes,
prints nothing or prints 'No Best Solution'; on geometry, if the metamorphic check fails) minus **always thinking with the same fact**,
seed means, paired 95% interval over problems, and FF's output tokens as a share of always thinking's. Facts: geometry the needed helpers
+ the algorithm hint; OptiBench (a fixed third, 202 problems), BWOR, LogiOR the label-free library; OptMATH the mined usage example
(Qwen3.5-9B: the library).

| model | geometry (96) | OptiBench (202) | BWOR (82) | LogiOR (92) | OptMATH (100) |
|---|---|---|---|---|---|
| gpt-oss-20b | **+3.1** [+1.0, +5.6], 59% | **+2.5** [+0.5, +4.8], 48% | −1.2 [−6.9, +4.5], 46% | −0.7 [−5.1, +3.3], 63% | **+5.7** [+0.3, +11.3], 68% |
| Qwen3-14B-AWQ | +2.4 [−0.3, +5.6], 39% | **−4.3** [−7.8, −0.8], 33% | **−12.2** [−20.3, −4.5], 56% | −1.8 [−6.2, +2.5], 75% | 0.0 [−4.0, +4.0], 83% |
| Qwen3-8B | **−16.7** [−21.9, −11.5], 53% | **−4.5** [−8.1, −1.0], 39% | **−11.0** [−16.7, −5.7], 65% | **−7.6** [−11.6, −3.6], 82% | +1.7 [−1.3, +5.0], 88% |
| Qwen3.5-9B (§5.4) | −0.3 [−3.1, +2.4], 30% | **+4.0** [+1.0, +6.9], 30% | 0.0 [−4.9, +4.9], 66% | **+7.6** [+3.6, +12.0], 78% | +2.7 [−3.3, +8.7], 60% |

The fact is the main lever: it raises thinking as well (+3.5 to +22.6 points over thinking without it; Qwen3-14B-AWQ on OptiBench 44.1% →
66.7%). Given the fact, thinking only on a visible failure ties or beats always thinking on every benchmark for gpt-oss-20b and Qwen3.5-9B
at 30–78% of its tokens, and for Qwen3-14B-AWQ on geometry, LogiOR and OptMATH. For Qwen3-14B-AWQ on OptiBench / BWOR and for Qwen3-8B on
four of five, thinking with the fact is 4–17 points more accurate: there the recipe trades accuracy for tokens (§5.2 explains why).
Without any fact on either side the earlier comparison holds (OptiBench +1.8 / +11.0 / −0.4, BWOR +1.2 / +1.2 / −8.1, LogiOR −1.1 /
−2.2 / −2.9 for the three development models). Counting input tokens shrinks the savings but reverses none.

![Held-out benchmarks: the recipe vs always thinking](../figs/fig23_heldout.png)

*Each pair: always thinking with the same fact (orange) and the recipe (blue) on one held-out benchmark, seed means; a pair pointing up-left means more accurate and cheaper. Facts: OptMATH the mined usage example, OptiBench / BWOR / LogiOR the label-free library, geometry the needed helpers + hint. Right panel: Qwen3.5-9B, never used in development (§5.4; OptMATH with the library, thinking at a 32k budget); OptiBench on its fixed third (`poc/make_figure_heldout.py`).*

### 5.2 Why it fails: the check leaks
Exactly, FF − always thinking = P(check passes) × [P(cheap program right | passes) − P(thinking with the fact right | passes)]: the recipe
can lose only on problems its check lets through. Against the fact-matched arm the second factor decides every cell: where FF wins or
ties, the passing cheap programs are about as often right as thinking with the fact would be on them (gpt-oss-20b OptiBench 80% vs 77%;
Qwen3.5-9B LogiOR 74% vs 52%; geometry 95–100% vs 94–96% for the three stronger models); where it loses, thinking with the fact solves far
more of them (Qwen3-14B-AWQ BWOR 42% vs 64%, Qwen3-8B BWOR 31% vs 55%, Qwen3-8B geometry 67% vs 92%). The leak alone does not decide it:
62% of Qwen3.5-9B's passing OptMATH programs are wrong, but thinking with the fact is no better on them (34%), so FF ties.

Where FF loses, its free check lets wrong programs through. On BWOR and LogiOR the cheap programs are right on only 7–42% of problems and
38–75% of the programs that run and print a number are wrong (Qwen3-8B on BWOR: 75%). On held-out geometry 64 of Qwen3-8B's 216 fact
programs pass the metamorphic check yet are wrong; reading them, 37 answer the given instance correctly and fail only the degenerate copy —
a convexity test that crashes when the first three vertices are collinear, a point-in-triangle test that counts points on an edge — edge
cases the statement names but the given input does not contain, so no check on the given input can see them.

We tried three label-free second views against this leak (pre-registered, 3 seeds): a brute-force program by the same model, a second
sample, and edge-case tests the model writes once per task from the statement. The first two catch 41–45% of the leaked programs (the
brute force copies the same textbook snippet); the tests see the leaks (59 of 64) but compute the same boundary cases wrong, flagging 67% of
correct programs. A fourth view — invariances the model states from the statement without computing any answer ("a point added exactly on an edge does not change the count") — catches the right failures (23 of the 37 edge-case leaks) but its relations are often wrong too (54% false alarms), reaching 67.7% at 7.2k. None lets FF reach always-thinking for Qwen3-8B (74.0% at 9.8k).

Nor does one repair turn on the flagged programs (only 13% of its repairs pass the check), nor a program from a different model: requiring gpt-oss-20b's fact program to agree catches 26 of the 27 leaks that are wrong on the given input and none of the 37 edge-case-only ones (63.2% at 6.5k) — the self-correlated part of the leak is removable, the edge-case part is invisible to any check on the given input; and gpt-oss-20b alone solves 99.0% at 0.8k, so a stronger second model is a reason to switch, not a check. Even handing a differential test the benchmark's own edge inputs (agreement
with a second sample there) catches 32 of the 37 edge-case leaks but reaches only 71.9% at 78% of always-thinking's tokens. On BWOR / LogiOR,
requiring two cheap programs to agree recovers always-thinking's accuracy in every cell but costs 91–120% of its tokens. **The saving of the recipe is
bounded by its check's leak.**

On BWOR / LogiOR a stronger check helps accuracy: a solution checker the model writes from the text (it tests every stated constraint on the printed solution and recomputes the objective) catches 66–97% of running-but-wrong programs (but flags 18–65% of right ones) and turns the recipe into a significant gain over always thinking (without the fact, as in HO3) for gpt-oss-20b (+3.7, +4.3) and Qwen3-14B-AWQ on BWOR (+3.3), at 102–110% of its tokens. On OptiBench, where cheap programs are usually right, the same checker does not pay: the plain recipe with the library already beats always thinking by +5.0 / +15.0 / +7.2 points at 36–55% of its tokens, and the checker's false alarms cost what its catches gain. Nor does it carry over to OptMATH (−1.4 to −2.3 points), whose solutions contain auxiliary formulation variables that the checker must re-interpret: a check helps only where it is a genuinely independent view.

**One cheap repair before thinking.** A cheaper first escalation helps where checks cannot save tokens: one short repair turn shown the error (no thinking) before thinking is never worse than the plain recipe and adds +0.7 to +4.0 points on OptiBench and OptMATH for all three models at equal or lower cost — where a repair runs, it is right more often than thinking on the same items. On the unseen Qwen3.5-9B it adds +2.0 to +6.2 points on all four word benchmarks at 73–88% of the plain recipe's tokens (pre-registered, HO-N3), so it is the recipe's first escalation on word problems. On BWOR / LogiOR it again helps the stronger development models but not Qwen3-8B, whose repaired programs run but are mostly wrong there (exploratory); on held-out geometry it adds little (+0.7 / +1.7 for the stronger models), because "these copies disagree" is less actionable evidence than a Python error.

Agreement with gpt-oss-20b's program is a better check on BWOR / LogiOR than a self-written checker (+1.4 to +3.3 points over it for both Qwen models, half the false alarms), but again dominated by using gpt-oss-20b.

**A cost model** (against thinking without the fact, as these analyses were run). A perfect check bounds what any check can do: on held-out geometry it lifts Qwen3-8B only to 75.0% at 70% of always-thinking's tokens (its fact programs are wrong too often), while gpt-oss-20b and Qwen3-14B-AWQ reach 99.0% at 49% and 84.4% at 38%; on BWOR / LogiOR a perfect check saves no tokens (83–103%) but raises accuracy above always thinking (e.g. gpt-oss-20b BWOR 69.5% vs 59.3%). The recipe's token saving is capped by how often the cheap program is right; the check's leak decides how much of the possible accuracy it keeps.

### 5.3 Facts without a human
The label-free library — for each problem, the program for the most similar other problem of the same benchmark that passed a strict check
(two runs agree, not 'No Best Solution') in any of the three models' runs — raises the first program in 25 of 29 model × benchmark cells
(e.g. OptiBench +7 / +17 / +24 points for gpt-oss-20b / Qwen3-14B-AWQ / Qwen3-8B; BWOR and LogiOR +5.7 to +14.9); it hurt only the gpt-oss
models on OptMATH, whose failures are formulation and data errors, not usage, and did not help Nemotron-3-Nano on BWOR / LogiOR (−1.6,
−2.2; +16.3 on OptiBench). On held-out MAMO the model's own mined program matches the
hand-written snippet (gpt-oss-20b 78.8% vs 78.9%; Qwen3-32B 75.3% vs 70.7%).

**When does a fact pay?** The share of first programs that crash with a usage exception predicts the gain (r = 0.60 over 58 points; mean
+10.9 points where ≥ 5% crash this way, +2.1 below). A rule fixed from 46 points ("add a fact unless usage crashes < 5% and other failures
≥ 25%") was right in 18 of 20 new points (BWOR / LogiOR for the three development models; four benchmarks for Qwen3.5-9B), all on its
"add" side. It does not transfer: on the label-free fine-tuned models, the first to reach its "do not add" region, it was right on 2 of 5
"do not add" and 3 of 6 "add" points (WF5), and on Nemotron-3-Nano, a model from another family, on 3 of 8 (HO-N4). The pattern is by kind
of fact: after fine-tuning the usage card pays nowhere (−6.9 to +2.8) while the library of similar problems' programs still adds +4 to +7
on 5 of 6 points — the usage fact is in the weights, the formulations of other problem types are not — and a usage-crash census sees only
the first. On Nemotron-3-Nano neither fact helps on BWOR / LogiOR (its failures there are formulations; the card even pushes it onto one
solver and into API mix-ups, LogiOR −6.9). The census is a description of where usage facts paid on the development models; the choice
of fact is left to the pilot. A hand-written usage card fails where it misses the library the model reaches for (Qwen3-8B on routing problems
writes `from ortools.constraint_solver import pywraplp`), while working code of a similar problem transfers.

### 5.4 A model the recipe was never developed with
All rules above were fixed on gpt-oss-20b and the Qwen3 models. On Qwen3.5-9B (a newer generation, bf16 on one RTX 3090; thinking with the
model card's sampling and a 32k budget), pre-registered before any run: fact first, think on a visible failure beats always thinking without the fact on all
five held-out benchmarks (OptiBench 68.3% vs 44.7%, +23.5 [+20.8, +26.3] at 30% of its tokens; +3.8 to +14.3 elsewhere), and ties or
beats always thinking *given the same fact* on all five (OptiBench +4.0 [+1.0, +6.9], LogiOR +7.6 [+3.6, +12.0], the others ties; 30–78%
of its tokens; HO-TF2). Its thinking fails
by library misuse (14–25% of programs) and unfinished reasoning (6–32% at 32k): the fact, not the effort, is what it lacks. The census
called "add a fact" on all four word benchmarks and both facts paid (+3.7 to +19.7; 8 / 8 calls right).

**A model from another family** (HO-N4): NVIDIA-Nemotron-3-Nano-30B-A3B, a hybrid Mamba-Transformer mixture of experts, on 4 × RTX 3090,
everything pre-registered from the rules above. It behaves like the Qwen3 models, not like gpt-oss or Qwen3.5: its passing non-thinking
programs are wrong in 33–79% of word-problem cases, so fact-first loses to thinking with the same fact on OptiBench (−5.9 [−9.4, −2.5]),
BWOR (−11.8) and LogiOR (−9.8) and ties only on OptMATH (−3.0 at 72% of the tokens) and geometry (0.0 at 66%, 5% leak). The self-review
gate transfers: it ties or beats thinking with the fact in all 5 cells (LogiOR +2.2 [+0.7, +4.0], geometry +1.7 [+0.3, +3.8]), but at
94–109% of the tokens (221% on geometry, where it raises false alarms on 64% of right programs). The library pays on OptiBench (+16.3)
but not on BWOR / LogiOR, the census was right on 3 of 8 calls, and the 30-label pilot loses 1.05 points (best fixed policy: two
agreeing cheap programs, 0.80). What transfers across families is the decomposition — the leak decides the side — and the gate's
accuracy; the token saving belongs to models whose free check does not leak.

### 5.5 Knowing when not to use it
The recipe's losses are detectable before deployment. Label 30 random problems of a new model × benchmark cell, run the four policies on
them (the cheap program alone, fact first, fact first with two agreeing programs, always thinking) and keep the best by accuracy − 0.5 ×
ktokens. Over the 45 held-out cells (3 models × 3 seeds × five benchmarks, each with the recipe's fact) the pick is 0.87 points from the
cell's best on average (10 labels: 2.81; always using fact-first: 1.80; always thinking: 5.86); on the unseen Qwen3.5-9B, 0.81 over 15 cells. With repair-first as a fifth policy over all 60 held-out cells the pilot's regret is 0.94, and always repairing first (1.22 on the 48 word cells) beats always using the plain recipe (2.85), though it loses accuracy on BWOR for all three development models (HO-R). Against the fact-matched thinking arm no fixed policy is good everywhere (best fixed regret 3.32) and the pilot matters most: 30 labels keep the regret at 0.85, choosing thinking with the fact in the 17 of 60 cells where it is best (HO-P2). In Qwen3-8B's geometry and BWOR cells, where
the recipe loses, the 30 labels pick thinking: 0.74 points of regret instead of 7.83 (pre-registered, `PREREG_MODEL.md`, addendum HO-P). The labels are needed: estimating accuracies from how often the cheap program, a second sample and thinking agree (no labels) keeps fact-first in exactly those cells (regret 1.71 overall, 11.2 on Qwen3-8B geometry), because a model's cheap programs share their mistakes and vouch for each other (HO-L). Where no labels are available, the 2k-token
self-review gate (§5.6) is the best fixed policy for the leaky Qwen models: over the 39 cells with reviews it loses 2.52 points to each
cell's best, against 3.99 for always thinking with the fact and 5.17 for repair-first; given 30 labels, adding it to the pilot gains only
+0.28 (regret 0.96), because the pilot already finds a near-equal policy in the cells the gate wins (HO-P3). Short thinking first
(§5.6) changes this: over 54 cells of the four hybrid-thinking models it is the best policy in 28 and the three-step cascade (non-thinking
program, then short thinking, then full) in 12; always using short thinking first loses 1.47 to each cell's best, where the best other
fixed policy loses 5.8, and adding the two to the 30-label pilot raises its utility by +2.1 per cell (regret 1.19; HO-P4).

### 5.6 Larger models, stronger checks, shorter thinking
- **gpt-oss-120b** (4 × RTX 3090, tensor parallel): fact-first ties thinking with the same fact on OptiBench, BWOR and LogiOR (−1.0, +3.7,
  0.0) at 50–63% of its tokens (HO-LG).
- **A stronger check where the plain one leaks**: accepting the library program only if a solution checker written from the text passes
  its printed solution closes the Qwen3 models' gap to thinking with the fact in all five losing cells (−4 to −12 → −1.6 to +1.0), but saves
  tokens only on OptiBench (71–79%); on BWOR / LogiOR it escalates almost everything (HO-VF).
- **A short self-review as the gate** (HO-VR): the same Qwen3 model, thinking for at most 2k tokens, reviews its passing program and
  answers CORRECT / WRONG; escalating on WRONG makes fact-first tie or beat thinking with the fact in all six Qwen3 cells (−1.1 to +2.9),
  at 70–73% of its tokens on OptiBench and ~100% on BWOR / LogiOR, where even a perfect check saves at most 12%. The review flags 65% of
  wrong passing programs with 13% false alarms. On OptMATH and geometry (HO-VR2) it ties or beats thinking with the fact in 3 of 4 more
  cells and cuts Qwen3-8B's geometry loss from −16.7 to −6.6: reading the statement, it catches 20 of the 37 edge-case-only leaks that
  every check on the given input missed (§5.2), at 31% false alarms.
- **Shorter thinking with the fact** (budget forcing): 2k tokens keep all but 2–4 points on OptiBench at ~40% of the tokens but lose 11–17
  on BWOR / LogiOR; escalating to a budgeted think does not rescue fact-first for the Qwen3 models (HO-TB).
- **Short thinking first** (HO-SB, SB2, SB3; found in HO-TB's stored runs, then tested on 14 cells it was not chosen on): write the first
  program after thinking with the fact for at most 2,000 tokens, and think fully only if that program visibly fails. It never loses to
  always thinking with the fact (−0.3 to +10.1): Nemotron-3-Nano OptiBench +3.8 [+1.8, +5.9] at 72% of the tokens, BWOR +5.3 at 79%,
  LogiOR +3.3 at 92%, OptMATH +6.3 [+1.0, +12.0] at 73% — more accurate and cheaper than the review gate in all four; Qwen3 OptMATH +2.3
  / +3.3 at 85–90%; Qwen3-8B geometry −0.3 [−2.8, +2.1], where fact-first loses 16.7 and the gate 6.6. Where its gain comes from, in the
  raw runs: problems on which full thinking's own program crashes, prints nothing or runs out at 32k, while the forced-short think
  finishes. It costs where full thinking is already short (Nemotron geometry, 1.7k: 137%) and, on Qwen3.5-9B, whose non-thinking programs
  are right when they pass, it is more accurate than the plain recipe (+2 to +8) but dearer (+4 to +66% tokens). A thinking first step
  is what the leaky models lack; the non-thinking program first brings the leak back (exploratory: −5 to −17).

### 5.6b The baseline matched in the check (HO-CM)
Every comparison above gives always-thinking the same fact but lets it ignore its own visible failures. Given the same free check — a
second think when its program crashes, prints nothing or prints 'No Best Solution' — thinking gains +2.5 to +12.3 points on all 16 word
cells of the four hybrid-thinking models at 119–164% of its tokens, and +0 to +10 for the gpt-oss models (105–143%). Over 54 cells (λ =
0.5) one think is never the best policy (always using it loses 7.64 utility points to each cell's best); the best fixed policy is short
think → full think → retry (1.74), then short think first (3.00) and thinking with a retry (3.40). Against the check-matched think the
cheap-first policies stay within one point in 37 of 54 cells (registered ≥ 40: refuted): ahead where the check holds (Qwen3.5-9B +2 to
+12, Nemotron OptMATH +8, Qwen3-14B-AWQ geometry +2), behind on the leaky models' hardest word problems (−2 to −4); gpt-oss-20b, a pure
saving against one think, trails the check-matched think on BWOR (−10.2 [−16.7, −4.1]) and LogiOR (−8.0) at 37–44% of its tokens. The
free check is worth applying to every step; which end of the frontier to take depends on the price of a token, and the pilot can choose.

### 5.7 Putting the fact into the weights, with no labels
Qwen3-8B and Qwen3-14B were LoRA-fine-tuned (36 / 53 minutes on 2–4 RTX 3090s) on 1,127 programs from the development sets that pass the
strict check — no label anywhere. Without any fact in the prompt, the fine-tuned models write programs about as good as the base models
*given* the label-free library on OptiBench (Qwen3-8B 54.2% vs 51.6%, base without a fact 27.4%; Qwen3-14B 58.0% vs 58.1%, base 36.3%) and
BWOR (+2.8, +3.3), with usage crashes falling from 16–28% to 1–7%; the leak does not rise (OptiBench 32–39% → 23–30%). On LogiOR /
OptMATH, whose problem types the development data lacks, the library's similar-problem programs still help (−1 to −6 for the fine-tuned
models). Fine-tuning internalizes the usage fact, not the formulations of unseen problem types.

Self-training on 3,996 unlabeled OR problems (the round-1 model writes programs; a label-free filter keeps some; retrain from base) never
gets past round 1 (DT3–DT5, 3 seeds, held-out): with self-consistency as the filter it learns the check's mistakes (BWOR 18.3 → 15.0%,
leak 69 → 76%; OptMATH 8.3 → 5.7%); with agreement across two models (DT4) or agreement plus the 2k-token thinking-mode review (DT5,
1,452 problems kept) it is neutral (OptiBench −0.4 / −0.7, BWOR +2.4, LogiOR 0.0 / −1.8, OptMATH −0.7 / +0.3; no interval excludes 0).
A better label-free check removes the harm but adds no new formulations; on the unseen types only the library of similar problems helps
(base + library OptMATH 14.3%). Prior work reports the same plateau for self-training with imperfect filters (§6.5).

### 5.8 Proofs: where the check is perfect
In Lean 4 a compiled proof is correct, so the check cannot leak. On miniF2F (244 statements), 32 cheap (non-thinking) attempts solve more
than 8 thinking attempts (gpt-oss-20b 74 vs 72; gpt-oss-120b 83 vs 81), thinking afterwards adds the statements cheap sampling never reaches
(80, 91), and up to always-thinking's budget the best policy is mostly cheap attempts (PF, PL1). One cheap try before thinking saves
nothing (97–103% of the tokens): with a perfect check the escalation rule is "sample cheaply until it stops paying, then think". With tokens
priced, the best split is short (4–6 cheap attempts, at most one thinking attempt), and 30 labelled statements pick it within a point (PL2).

## 6. Baselines on the same harness

| task | baseline | its result | ours |
|---|---|---|---|
| OptiBench (605) | STORM-Qwen3-4B (SFT + RL, official tool-integrated inference) | 78.7% @ 7.9k | gpt-oss-20b library + FF 73.0% @ 0.96k; cheap program + STORM on failure 76.3% @ 2.3k |
| OptMATH (100) | STORM-Qwen3-4B | 40.3% @ 14.1k | gpt-oss-20b FF 38.3% @ 3.7k; + STORM on failure 43.3% @ 7.0k |
| MAMO (863) | ORLM-LLaMA-3-8B (fine-tuned) | 69.5% @ 1.1k | Qwen3-8B, no training, 69.5% @ 1.0k |
| OptiBench, gpt-oss-20b | majority of 3 thinking runs (self-consistency) | 75.0% @ 6.3k | FF with that vote as fallback 74.6% @ 1.9k |
| picking 1 of 3 geometry programs (Qwen3-8B) | CodeT / majority vote / MBR-exec | 96.0 / 95.7 / 93.7% | symmetry check 99.7% |
| CVRP library usage (Qwen3-32B) | BM25 docs / DRoC | 48% / 72% | exact snippet 77% |

A trained 4B specialist leads our best training-free 24 GB recipe on OptiBench by 5.7 points at 8× the tokens; the two compose (cheap
program first, the specialist only on a visible failure).

## 6.5 Relation to prior work (what is new here)
Escalating from a cheap answer to a stronger one when a check fails is established for cascades *between models* (answer consistency,
ICLR 2024; AutoMix's self-verification, NeurIPS 2024; self-generated tests for code), and learned "when to think" switches exist
(AdaptThink, Thinkless, AutoThink); false positives of an imperfect verifier are known to cap resampling (Limits of Inference Scaling
Through Resampling, ICLR 2026). What this work adds: (i) the comparison against thinking *given the same fact*, which removes the
fact/policy confound present in most cascade and when-to-think evaluations; (ii) an exact decomposition that predicts, per model and
benchmark, whether thinking only on failure is a pure saving or a trade; (iii) the evidence on OR word problems and geometry with open
models on 24 GB GPUs. The proof results (cheap attempts before thinking under a perfect check) confirm Reasoning Models Can Be Effective
Without Thinking (2504.09858) and repeated-sampling scaling (Large Language Monkeys) on general hybrid models. Label-free fine-tuning on
self-consistent programs is self-improvement / context distillation (LLMs Can Self-Improve; STaR; ReST-EM); its collapse under self-
agreement and the cross-model fix are known (Co-rewarding, Multiagent Finetuning) — our contribution there is the program-level version on
OR problems and the observation that the cross-model filter removes the harm but adds no new knowledge. Full list: `docs/notes/RELATED_WORK.md`.

## 7. Where the recipe stops

- **Short-answer competition math** (MATH-500, AIME): a program is 17–20 points below a text answer; thinking is needed for AIME (Qwen3-14B-AWQ:
  text 26.1%, thinking 73.3%). Text–program agreement is a reliable check (0.3–0.9% of agreeing pairs wrong on MATH-500) and saves 20–23% of
  thinking tokens there for the Qwen models, but nothing on AIME.
- **Formal proofs** (miniF2F, Lean 4): a specialized 8B prover proves 180 of 244 statements (Goedel-Prover-V2-8B) vs 133 for Qwen3.6 and
  66 for gpt-oss-20b; facts (a verified similar proof, a lemma toolkit) and repair from compiler errors do not help.
- **The weakest model's check leak** (Section 5.2).

## 8. Limitations

Several held-out margins are ties within their intervals (reported as such). Always-thinking runs at a 16k-token budget (what fits beside the model on a 24 GB GPU); 0.3–7.6% of the stronger models' thinking rows hit it (Qwen3-8B 3–24%). Even counting every capped wrong row as right, no tie or win of the stronger models becomes a significant loss (largest shift −3.4 points; gpt-oss-20b's OptMATH win becomes a tie), and Qwen3-8B's losses only deepen. The development geometry and optimization
suites, and the held-out geometry tasks, were generated by us; contest problems predate the models' training cutoffs; about half of MAMO's
leaked problems have disputed labels. Models are two open families (Qwen3 / Qwen3.5, gpt-oss); a Gemma-4 test was withdrawn because our serving stack does not load it; the 14B model is 4-bit. Cost counts tokens, not
wall-clock time or CPU time of the checks.

## 9. Conclusion

For computational problems on a single 24 GB GPU, the missing fact is the cheapest lever: a few lines of exact usage or a checked program
for a similar problem, found without labels, improve both cheap programs and thinking. Paying for thinking only where a free check visibly
fails — not where problems look hard — keeps the accuracy of always thinking with the fact at 30–78% of its tokens for gpt-oss-20b and for
a model the recipe was never developed with (Qwen3.5-9B); on word problems one cheap repair from the error should come before thinking. Its limit is the check: where a model's wrong programs look right (the Qwen3 models on the hardest word problems, Qwen3-8B on geometry),
thinking only on visible failures saves tokens by losing accuracy, and 30 labelled problems of a new task are enough to see that and
think instead. Making checks see what the given input does not
contain is the open problem. Two extensions point past it: where the check is perfect (formal proofs) the rule becomes
"sample cheaply, then think", and the fact itself can be trained into the model from the recipe's own checked programs, with no labels.

*Sources: `PROPOSAL.md`; held-out numbers `results/x3/ho*_analysis.log`, `results/x3/ho2_*_analysis.log`,
`results/x3/input_tokens_analysis.log`, `results/hogc_analysis.log`; predictions and verdicts `docs/prereg/PREREG_{U1,HO,HOG,HOGC,HON,MODEL,X7,N,X1,PROOF}.md`; analyses `poc/analyze_{ho,ho3,ho7,hogc,hox,hod_gate,budget,hop,hol,hon}.py`.*
