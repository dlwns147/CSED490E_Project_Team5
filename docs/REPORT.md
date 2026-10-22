# Facts First, Think on Failure: Solving Computational Math with LLM-Written Programs on One 24 GB GPU

*Draft of the final report, POSTECH CSED490E Team 5 (Sangjun Lee, Seongbin Park). Started 2026-10-23 from `PROPOSAL.md`, the
pre-registrations in `docs/prereg/` and `docs/notes/REPORT_OUTLINE.md`; format and length to be fitted to the course template.*

## Abstract

Language models can solve computational problems — geometry, scheduling, routing, optimization word problems — by writing a program, but
programs fail silently and "thinking longer" (long reasoning before answering) is expensive. We ask where a fixed budget of tokens should go
for models that fit one 24 GB GPU (gpt-oss-20b, Qwen3-14B-AWQ, Qwen3-8B). We test a training-free recipe: write a cheap program, add the
missing fact (a few lines of exact library usage, or a checked program for a similar problem found without labels), run a free check, and
think only when the check visibly fails. On our development suites the recipe solves 87% of 208 problems at 2.5k output tokens, against 74%
at 4.1k for spending thinking on the hardest-looking problems. On five benchmarks never used in development, for gpt-oss-20b and
Qwen3-14B-AWQ the recipe ties or beats always thinking at 28–88% of its output tokens; for Qwen3-8B it wins only with the label-free
library and loses where its free check lets many wrong programs through. The library of checked programs raises the first program in 23 of
25 model × benchmark cells. The deciding quantity is the check's leak, not problem difficulty, and it is detectable: labelling 30
problems of a new cell picks a policy within 0.87 points of the best on 45 held-out cells, and where the recipe loses it costs 0.74
points instead of 7.8.

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
4. **Think harder only when the check fails.**
5. **Reuse** a checked program when the same problem returns with new data.

Contributions: (i) every method is compared in one harness with accuracy *and* tokens, on models that fit one RTX 3090; (ii) facts before
compute — a short exact fact plus a free execution check beats spending thinking by difficulty; (iii) the fact can be found without a human
or labels: other runs' checked programs for similar problems; (iv) a held-out evaluation on five unseen benchmarks with 95% intervals, which
locates the recipe's limit: when the free check leaks, thinking only on visible failures stops paying.

![The recipe](../figs/fig18_recipe.png)

## 2. Setup

**Problems.** Development: 13 generated geometry tasks (convex hull, polygon area, point in polygon, segment intersections, closest pair,
lattice points, rectangle union, Delaunay check, diameter, ...) and 8 generated optimization problems (knapsack, TSP, colouring, scheduling,
bin packing, vertex cover, CVRP, VRPTW); NL4OPT + IndustryOR word problems (345); 311 Codeforces geometry problems with official tests; 56
Solomon routing instances; job-shop instances. Held out (never used to design the recipe): MAMO (863), OptMATH (100), OptiBench (605),
BWOR (82), LogiOR (92), and four geometry tasks (polygon overlap, convexity, points in a triangle, convex clipping; 96 instances).

**Models.** gpt-oss-20b (MXFP4), Qwen3-14B-AWQ (4-bit), Qwen3-8B — all fit one 24 GB GPU; Qwen3-32B-AWQ, Qwen3.6-35B-A3B and gpt-oss-120b
as references; trained baselines STORM-Qwen3-4B and ORLM-LLaMA-3-8B. Served with vLLM 0.22; cheap programs without thinking (gpt-oss at
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
on average; using fact-first as a fixed default loses 1.4.

![Cost vs accuracy](../figs/fig19_cost_accuracy.png)

## 5. Held-out tests

### 5.1 The core rule on unseen benchmarks
Fact-first-then-think (FF: cheap program; think only if it crashes, prints nothing or prints 'No Best Solution'; on geometry: if the
metamorphic check fails) minus always thinking, seed means, paired 95% interval over problems; FF's output tokens as a share of always
thinking's, then input + output:

| benchmark (problems) | gpt-oss-20b | Qwen3-14B-AWQ | Qwen3-8B |
|---|---|---|---|
| OptMATH (100), mined usage example | +5.7 [+0.3, +11.0], 68% / 81% | 0.0 [−3.7, +4.0], 83% / 93% | +1.7 [−1.3, +5.0], 88% / 97% |
| OptiBench (605), no fact | +1.8 [+0.3, +3.4], 56% / 64% | +11.0 [+8.7, +13.3], 52% / 56% | −0.4 [−2.3, +1.4], 64% / 67% |
| OptiBench, label-free library | +4.1 [+2.1, +6.1], 46% / 67% | +15.6 [+12.9, +18.3], 28% / 37% | +5.2 [+2.6, +7.6], 36% / 43% |
| BWOR (82), no fact | +1.2 [−4.5, +6.9], 53% / 61% | +1.2 [−4.9, +7.3], 75% / 80% | −8.1 [−13.4, −3.3], 74% / 78% |
| LogiOR (92), no fact | −1.1 [−6.9, +4.7], 63% / 71% | −2.2 [−5.4, +1.8], 88% / 92% | −2.9 [−6.5, +0.4], 91% / 94% |
| LogiOR, label-free library | −1.1 [−6.9, +4.0], 59% / 80% | +10.1 [+4.3, +15.9], 74% / 85% | −2.2 [−6.9, +2.5], 80% / 90% |
| held-out geometry (96), needed helpers + hint | +5.9 [+3.5, +8.7], 48% | +7.6 [+4.5, +11.5], 34% | −14.2 [−19.8, −9.4], 46% |

![Held-out benchmarks: the recipe vs always thinking](../figs/fig23_heldout.png)

*Each pair: always thinking (orange) and the recipe (blue) on one held-out benchmark, seed means; a pair pointing up-left means more accurate and cheaper. Facts: OptMATH the mined usage example, OptiBench / BWOR / LogiOR the label-free library, geometry the needed helpers + hint (`poc/make_figure_heldout.py`).*

For the two stronger models the recipe never loses to always thinking (wins on OptiBench and geometry, ties elsewhere) at 28–88% of its
output tokens. For Qwen3-8B it wins only with the library on OptiBench and loses on geometry and BWOR. Counting input tokens shrinks the
savings (the library adds 0.3–0.7k tokens per cheap prompt) but reverses none.

### 5.2 Why it fails: the check leaks
Where FF loses, its free check lets wrong programs through. On BWOR and LogiOR the cheap programs are right on only 7–42% of problems and
38–75% of the programs that run and print a number are wrong (Qwen3-8B on BWOR: 75%). On held-out geometry 64 of Qwen3-8B's 216 fact
programs pass the metamorphic check yet are wrong; reading them, 37 answer the given instance correctly and fail only the degenerate copy —
a convexity test that crashes when the first three vertices are collinear, a point-in-triangle test that counts points on an edge — edge
cases the statement names but the given input does not contain, so no check on the given input can see them.

We tried three label-free second views against this leak (pre-registered, 3 seeds): a brute-force program by the same model, a second
sample, and edge-case tests the model writes once per task from the statement. The first two catch 41–45% of the leaked programs (the
brute force copies the same textbook snippet); the tests see the leaks (59 of 64) but compute the same boundary cases wrong, flagging 67% of
correct programs. A fourth view — invariances the model states from the statement without computing any answer ("a point added exactly on an edge does not change the count") — catches the right failures (23 of the 37 edge-case leaks) but its relations are often wrong too (54% false alarms), reaching 67.7% at 7.2k. None lets FF reach always-thinking for Qwen3-8B (74.0% at 9.8k). Nor does one repair turn on the flagged programs (only 13% of its repairs pass the check), nor a program from a different model: requiring gpt-oss-20b's fact program to agree catches 26 of the 27 leaks that are wrong on the given input and none of the 37 edge-case-only ones (63.2% at 6.5k) — the self-correlated part of the leak is removable, the edge-case part is invisible to any check on the given input; and gpt-oss-20b alone solves 99.0% at 0.8k, so a stronger second model is a reason to switch, not a check. On BWOR / LogiOR, requiring two
cheap programs to agree recovers always-thinking's accuracy in every cell but costs 91–120% of its tokens. **The saving of the recipe is
bounded by its check's leak.**

On BWOR / LogiOR a stronger check helps accuracy: a solution checker the model writes from the text (it tests every stated constraint on the printed solution and recomputes the objective) catches 66–97% of running-but-wrong programs (but flags 18–65% of right ones) and turns the recipe into a significant gain over always thinking for gpt-oss-20b (+3.7, +4.3) and Qwen3-14B-AWQ on BWOR (+3.3), at 102–110% of its tokens. On OptiBench, where cheap programs are usually right, the same checker does not pay: the plain recipe with the library already beats always thinking by +5.0 / +15.0 / +7.2 points at 36–55% of its tokens, and the checker's false alarms cost what its catches gain. Nor does it carry over to OptMATH (−1.4 to −2.3 points), whose solutions contain auxiliary formulation variables that the checker must re-interpret: a check helps only where it is a genuinely independent view. A cheaper first escalation helps where checks cannot save tokens: one short repair turn shown the error (no thinking) before thinking is never worse than the plain recipe and adds +0.7 to +4.0 points on OptiBench and OptMATH for all three models at equal or lower cost — where a repair runs, it is right more often than thinking on the same items. On BWOR / LogiOR it again helps the stronger models but not Qwen3-8B, whose repaired programs run but are mostly wrong there (exploratory); on held-out geometry it adds little (+0.7 / +1.7 for the stronger models), because "these copies disagree" is less actionable evidence than a Python error. Agreement with gpt-oss-20b's program is a better check on BWOR / LogiOR than a self-written checker (+1.4 to +3.3 points over it for both Qwen models, half the false alarms), but again dominated by using gpt-oss-20b.

**A cost model.** A perfect check bounds what any check can do: on held-out geometry it lifts Qwen3-8B only to 75.0% at 70% of always-thinking's tokens (its fact programs are wrong too often), while gpt-oss-20b and Qwen3-14B-AWQ reach 99.0% at 49% and 84.4% at 38%; on BWOR / LogiOR a perfect check saves no tokens (83–103%) but raises accuracy above always thinking (e.g. gpt-oss-20b BWOR 69.5% vs 59.3%). The recipe's token saving is capped by how often the cheap program is right; the check's leak decides how much of the possible accuracy it keeps.

### 5.3 Facts without a human
The label-free library — for each problem, the program for the most similar other problem of the same benchmark that passed a strict check
(two runs agree, not 'No Best Solution') in any of the three models' runs — raises the first program in 23 of 25 model × benchmark cells
(e.g. OptiBench +7 / +17 / +24 points for gpt-oss-20b / Qwen3-14B-AWQ / Qwen3-8B; BWOR and LogiOR +5.7 to +14.9); it hurt only the gpt-oss
models on OptMATH, whose failures are formulation and data errors, not usage. On held-out MAMO the model's own mined program matches the
hand-written snippet (gpt-oss-20b 78.8% vs 78.9%; Qwen3-32B 75.3% vs 70.7%).

**When does a fact pay?** The share of first programs that crash with a usage exception predicts the gain (r = 0.60 over 58 points; mean
+10.9 points where ≥ 5% crash this way, +2.1 below). A rule fixed from 46 points ("add a fact unless usage crashes < 5% and other failures
≥ 25%") was right in 10 of 12 new points on BWOR / LogiOR, but all new cells were on its "add" side; whether it predicts when *not* to add
a fact remains untested. A hand-written usage card fails where it misses the library the model reaches for (Qwen3-8B on routing problems
writes `from ortools.constraint_solver import pywraplp`), while working code of a similar problem transfers.

### 5.4 Knowing when not to use it
The recipe's losses are detectable before deployment. Label 30 random problems of a new model × benchmark cell, run the four policies on
them (the cheap program alone, fact first, fact first with two agreeing programs, always thinking) and keep the best by accuracy − 0.5 ×
ktokens. Over the 45 held-out cells (3 models × 3 seeds × five benchmarks, each with the recipe's fact) the pick is 0.87 points from the
cell's best on average (10 labels: 2.81; always using fact-first: 1.80; always thinking: 5.86). In Qwen3-8B's geometry and BWOR cells, where
the recipe loses, the 30 labels pick thinking: 0.74 points of regret instead of 7.83 (pre-registered, `PREREG_MODEL.md`, addendum HO-P).

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
leaked problems have disputed labels. Models are one open family (Qwen3) plus gpt-oss; the 14B model is 4-bit. Cost counts tokens, not
wall-clock time or CPU time of the checks.

## 9. Conclusion

For computational problems on a single 24 GB GPU, the cheapest reliable way to exact answers is to give the model the missing fact first
and pay for thinking only where a free check visibly fails — not where problems look hard. The recipe holds on unseen benchmarks for the
stronger small models; its limit is the check: where a model's wrong programs look right, thinking only on visible failures saves tokens
by losing accuracy. Making checks see what the given input does not contain is the open problem.

*Sources: `PROPOSAL.md`; held-out numbers `results/x3/ho*_analysis.log`, `results/x3/ho2_*_analysis.log`,
`results/x3/input_tokens_analysis.log`, `results/hogc_analysis.log`; predictions and verdicts `docs/prereg/PREREG_{U1,HO,HOG,HOGC,X7,N,X1,PROOF}.md`.*
