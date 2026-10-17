# Pre-registration U1: three failure mechanisms with measurable signatures, and compute allocation by mechanism vs by difficulty

Written 2026-10-16 18:24 UTC, before any run. Results go below; this section is not edited afterwards.

**Why (the project's central claim, made testable).** Test-time compute (more samples, more reasoning) is the main lever for
making LLM-written programs correct, and the standard way to spend it is by *difficulty* (Snell et al., ICLR 2025: bin prompts by
difficulty, pick the strategy per bin). Our results so far suggest difficulty is the wrong axis for programs that use tools and
libraries: failures come from three mechanisms that need three different resources.
1. **Missing knowledge** (an API fact the model does not have): the model is *unsure* at the decisive token (invented OR-Tools names:
   log-prob AUROC 0.84–0.90), samples disagree, and more reasoning does not supply the fact (.03 vs .77–.90 with a 5-line snippet).
   Cure: the fact (cheaper than the compute; it even shortens programs).
2. **Context steering** (an offered tool that pulls the model to a wrong algorithm): the model is *confident* (helper-name log-prob
   AUROC 0.06–0.21: unneeded helpers are called more confidently than needed ones), samples agree, so resampling, self-consistency and
   symmetry checks are blind (they accept 24–36% of wrong programs). Cure: a second opinion whose errors are independent (the same
   model with the tool removed) and compute only on disagreement.
3. **Genuine reasoning difficulty** (contest problems): samples and models disagree; checks get leakier as the model gets stronger
   (examples accept 24% → 37% of wrong programs from low to medium effort; cf. blind spots rising with capability, Rajput et al.
   2609.01345; correlated errors, Kim et al. ICML 2025; Goel et al. ICML 2025). Cure: more reasoning, gated by a decorrelated check.
**Prior art.** Difficulty-based allocation (Snell et al. 2025); uncertainty-triggered retrieval (FLARE, Self-RAG, Adaptive-RAG);
epistemic vs aleatoric uncertainty for LLMs (semantic entropy, Farquhar et al. 2024; Yadkori et al. 2024); verifier blind spots and
correlated errors (above). Not covered: a *confident, consistent* failure class (steering) that defeats every sample-based
uncertainty signal and every same-model check, detected by changing the tool condition; and allocation of three different resources
(facts, decorrelated checks, reasoning) by the measured signature, priced in tokens on tasks with exact answers.

**Design.** Mixed suite: the N10 geometry suite (9 tasks, 108 items, K8 toolbox) and optimization suite (8 problems, 100 items, full
reference sheet). Models: Qwen3-32B-AWQ, Qwen3-8B, Qwen3.6-35B-A3B (no thinking; raw log-probs stored). Per item:
- base: 3 samples of the first-attempt condition with log-probs;
- three cures: FACT (geometry: the one-sentence algorithm hint, `--algo_hint`, where defined, else the needed helpers only;
  optimization: the exact snippet), DECORRELATE (geometry: no helpers; optimization: BM25 snippets), THINK (thinking on, 16k cap);
- signatures (label-free, from the base samples only): S_conf = min log-prob at tool/API-name tokens; S_cons = agreement of the 3
  samples' outputs on the instance; S_check = the label-free check (metamorphic / feasibility).
Policies at matched mean tokens per item (budget = that of "gated THINK"): uniform (gated THINK), DIFFICULTY (Snell-style: spend THINK
on the items with the lowest S_cons, i.e. predicted hardest, up to the budget), MECHANISM (low S_conf → FACT; S_cons high but the
check fails or the decorrelated program disagrees → DECORRELATE → THINK on disagreement; S_cons low → THINK), and the per-item oracle.
Thresholds chosen leave-one-task-out.
**Predictions.**
- U1-P1: the three mechanisms are separable by signature: among failing base programs, those fixed by FACT but not by THINK have lower
  S_conf than those fixed by THINK (AUROC ≥ 0.70); those fixed by DECORRELATE have higher S_cons than those fixed only by THINK (AUROC ≥ 0.65).
- U1-P2: at matched tokens, MECHANISM ≥ DIFFICULTY + 5 points (pooled over the two domains and three models), and ≥ 3 points in each domain.
- U1-P3: DIFFICULTY ≤ uniform + 2 points (difficulty is the wrong axis for these failures).
Runs (poc/queues/queue_s2_u1.sh) start after X2 on GPUs 0–3; analysis poc/analyze_u1.py (written before any result is read).

Analysis script poc/analyze_u1.py written 2026-10-16 22:31 UTC, before any U1 output was read. Runs started 22:28 (GPU0 Qwen3-32B, GPU2 Qwen3.6) and 22:29 (GPU3 Qwen3-8B, port 8056 after the port guard refused 8044, which the last X1 server still held).

**Incident (2026-10-17 00:29 UTC):** at 2026-10-16 23:51:25 all four vLLM servers on GPUs 0–3 terminated at the same second (NCCL
watchdog "Terminating the process" in every engine; a system-level event, not a run error). The U1 base / FACT / DECOR arms had
finished; the THINK arms were lost (geometry wrote rows only at the end; optimization had 15–44 of 100). Harness change: geometry now
writes each row as it completes. THINK arms re-run with identical settings from 00:29 (GPU0 Qwen3-32B, GPU2 Qwen3.6, GPU3 Qwen3-8B).

## Partial result, Qwen3-8B only (2026-10-17 03:23 UTC; results/u1_q8b.log; the other two models still running)
| Qwen3-8B | base (first sample) | uniform (THINK when the check fails) | DIFFICULTY (THINK on the least consistent items) | MECHANISM | oracle |
|---|---|---|---|---|---|
| geometry (108) | 65.7% | 88.0% @ 3.0k | 94.4% @ 5.7k | **95.4% @ 5.7k** | 100% |
| optimization (100) | 24.0% | 35.0% @ 8.1k | 27.0% @ 4.8k | **36.0% @ 4.9k** | 51.0% |
Pooled: MECHANISM 66.8% vs DIFFICULTY 62.0% vs uniform 62.5%. Signatures: optimization FACT-only fixes have lower API-name confidence than
THINK fixes (AUROC 0.81, but only 2 FACT-only items); geometry failures of this model are almost all fixed by THINK (36 / 37), so
there is little to route there. MECHANISM chose FACT on 49 of 100 optimization items. No verdict before the other two models finish.

Addendum (2026-10-17 03:29 UTC, before any Qwen3.6 U1 result is analysed): the Qwen3.6 THINK arm runs at a 28k cap and the first 5
finished geometry items all hit it (no program; 11 of 49 optimization items too). N10-M3 measured the same condition (same 108 items,
K8 toolbox, thinking, seed 1) at a 48k cap: 79 / 108 correct at a mean 32.6k tokens. The Qwen3.6 U1 analysis must therefore report
both: THINK outcomes from the 28k run as pre-registered, and a sensitivity analysis substituting the 48k run
(geocross_S2_N10m3_geo_think_s1 / co_S2_N10m3_co_think_s1). A mechanism-vs-difficulty win that holds only at the truncating cap
does not count for Qwen3.6.

## Results (2026-10-17 04:31 UTC; 3 models × 2 domains, 624 items; results/u1_all.log, u1_factfirst.log)
| model, domain | base | uniform (THINK when the check fails) | DIFFICULTY | MECHANISM | oracle |
|---|---|---|---|---|---|
| Qwen3-32B geometry | 63.0% | 87.0% @ 2.5k | 88.0% @ 4.8k | **94.4% @ 4.9k** | 100% |
| Qwen3-32B optimization | 57.0% | 70.0% @ 4.5k | 60.0% @ 2.3k | **72.0% @ 2.4k** | 85% |
| Qwen3-8B geometry | 65.7% | 88.0% @ 3.0k | 94.4% @ 5.7k | **95.4% @ 5.7k** | 100% |
| Qwen3-8B optimization | 24.0% | 35.0% @ 8.1k | 27.0% @ 4.8k | **36.0% @ 4.9k** | 51% |
| Qwen3.6 geometry | 97.2% | 98.1% @ 1.5k | 97.2% @ 3.4k | **99.1% @ 3.4k** | 99.1% |
| Qwen3.6 optimization | 70.0% | 81.0% @ 6.2k | 72.0% @ 3.4k | **95.0% @ 3.6k** | 99% |
Pooled: MECHANISM 82.5% vs DIFFICULTY 73.9% vs uniform 77.1%. **U1-P2 holds** (+8.6 pooled; geometry +3.1, optimization +14.7 at
matched tokens). **U1-P3 holds** (difficulty 3.2 points *below* uniform). **U1-P1:** FACT-only fixes have lower API / helper-name
confidence than THINK fixes in optimization (AUROC 0.70 / 0.81 / 0.76), uninformative in geometry (1 FACT-only item per model);
DECOR-only vs THINK-only consistency 0.38 / 0.50 (refuted).
**Exploratory baseline (after seeing the results; it changes the conclusion):** *always give the fact, think only when its check
fails* reaches **87.2% pooled**, above MECHANISM, at far fewer tokens in 5 of 6 cells (Qwen3-32B geometry 100% @ 1.6k vs 94.4% @ 4.9k;
Qwen3.6 optimization 98.0% @ 1.0k vs 95.0% @ 3.6k; Qwen3-8B optimization 46.0% @ 7.4k vs 36.0% @ 4.9k); always-FACT alone 79.3% at
0.3–0.6k. So MECHANISM's lead over DIFFICULTY comes from spending on *facts* at all, not from routing by signature: when the exact fact
is available, giving it to every item first and spending compute only where the check still fails is better and cheaper. The
signature only matters if facts are expensive. Caveat: FACT here is a human-written exact snippet / algorithm hint; in deployment it
must be retrieved (BM25 snippets recovered most of the gain in N10–N15).

## U1b pre-registration (2026-10-17 04:31 UTC, after the U1 results above were read, before these controls are computed)
Critique of U1's DIFFICULTY baseline: it may only spend THINK, while MECHANISM can also use the cheap FACT and DECORRELATE arms, so
"by mechanism vs by difficulty" is confounded with "has the fact arm". Two stronger controls (offline, same data):
- SNELL-BINNED (faithful to Snell et al.): bin items by the difficulty proxy S_cons (agreement of the 3 base samples: 0, 1/3, 2/3, 1);
  per bin choose the arm (base / FACT / DECORRELATE / THINK) with the best accuracy on the other tasks (leave-one-task-out; ties:
  fewer tokens); same arms as MECHANISM, no budget cap (report its tokens).
- ALWAYS-FACT: every item gets the FACT arm (one generation).
- U1b-P1: MECHANISM ≥ SNELL-BINNED + 3 points pooled (3 models × 2 domains) at ≤ its tokens.
- U1b-P2: MECHANISM ≥ ALWAYS-FACT + 3 points pooled; in optimization ALWAYS-FACT is within 3 points of MECHANISM at fewer tokens
  (the N16 result: giving the fact is both accurate and cheap there).

## U1 + U1b results (2026-10-17 04:33 UTC; results/u1_q8b.log, u1_q32b_q36.log, u1b_all.log; Qwen3.6 48k sensitivity u1_q36_think48k.log, u1b_q36_48k.log)
Accuracy @ mean output tokens per item (geometry 108 items, optimization 100; one seed of each cure arm):
| model / domain | base | uniform (gated THINK) | DIFFICULTY (THINK on low-agreement items) | SNELL-BINNED (best arm per difficulty bin) | ALWAYS-FACT | **MECHANISM** | oracle |
|---|---|---|---|---|---|---|---|
| Qwen3-8B geometry | 65.7% | 88.0% @ 3.0k | 94.4% @ 5.7k | 88.9% @ 8.7k | 80.6% @ 0.3k | **95.4% @ 5.7k** | 100% |
| Qwen3-8B optimization | 24.0% | 35.0% @ 8.1k | 27.0% @ 4.8k | 29.0% @ 7.5k | **41.0% @ 0.5k** | 36.0% @ 4.9k | 51% |
| Qwen3-32B geometry | 63.0% | 87.0% @ 2.5k | 88.0% @ 4.8k | 87.0% @ 6.6k | 83.3% @ 0.3k | **94.4% @ 4.9k** | 100% |
| Qwen3-32B optimization | 57.0% | 70.0% @ 4.5k | 60.0% @ 2.3k | 69.0% @ 2.1k | **74.0% @ 0.5k** | 72.0% @ 2.4k | 85% |
| Qwen3.6 geometry | 97.2% | 98.1% @ 1.5k | 97.2% @ 3.4k | 98.1% @ 3.5k | 98.1% @ 0.5k | **99.1% @ 3.4k** | 99.1% |
| Qwen3.6 optimization | 70.0% | 81.0% @ 6.2k | 72.0% @ 3.4k | **97.0% @ 2.8k** | **97.0% @ 0.6k** | 95.0% @ 3.6k | 99% |
| **pooled (624 items)** | | 77.1% | 73.9% | 78.7% @ 5.2k | 79.3% @ 0.44k | **82.5% @ 4.2k** | |
Qwen3.6 with the 48k thinking run: MECHANISM 96.6% vs DIFFICULTY 85.1% (its two domains); SNELL-BINNED and ALWAYS-FACT 97.6%.
- **U1-P2 holds** (MECHANISM 82.5% vs DIFFICULTY 73.9% pooled, +8.6; geometry +3.1, optimization +14.7). **U1-P3 holds** (DIFFICULTY
  73.9% ≤ uniform 77.1%: spending reasoning on the "hardest-looking" items is worse than spending it on items that fail the check).
- **U1-P1 mostly refuted**: FACT-only fixes barely exist in geometry (1 item per model), so P1a there rests on n = 1; in optimization
  S_conf separates FACT-only from THINK-fixed failures at AUROC 0.81 / 0.70 / 0.76 (Qwen3-8B / 32B / 3.6; 0.59 with the 48k run).
  P1b (DECORRELATE-only items more consistent) is 0.50 / 0.38 or undefined: not supported.
- **U1b-P1 holds** (MECHANISM 82.5% vs SNELL-BINNED 78.7%, at 80% of its tokens), except Qwen3.6 optimization, where SNELL picks the
  fact for every bin (97.0% vs 95.0%). **U1b-P2 holds narrowly** (+3.2 over ALWAYS-FACT) **and its second part holds strongly: in
  optimization ALWAYS-FACT beats every adaptive policy for all three models** (41 / 74 / 97% vs MECHANISM 36 / 72 / 95%) at 10–20 × fewer
  tokens.
**Reading (central claim):** allocating by mechanism beats allocating by difficulty, but its edge comes from routing failures to the
right *kind* of resource, and the cheapest resource dominates: when the missing fact is known, give it to everyone (79.3% at 0.44k
tokens is the best accuracy per token by far); compute (thinking) earns its cost only for the steering / reasoning failures of
geometry (+9 to +14 points for the Qwen3 models at ≈ 15 × the tokens). Caveat: one seed per cure arm; the FACT arms are hand-written
(an algorithm hint, an exact snippet). Replication with seeds 2–3 of the cure arms: U1r below.

## U1r pre-registration (2026-10-17 04:33 UTC, before running): seeds 2–3 of the cure arms (FACT, DECORRELATE, THINK), same base samples
Qwen3-32B (GPU0), Qwen3.6 (GPU2; THINK 28k as U1), Qwen3-8B (GPU3); poc/queues/queue_s2_u1r.sh; analysis = analyze_u1.py with U1_CURE_SEED=2|3.
- U1r-P1: MECHANISM > DIFFICULTY pooled on each cure seed (2 and 3).
- U1r-P2: ALWAYS-FACT ≥ MECHANISM in optimization for each model on each cure seed; MECHANISM > ALWAYS-FACT + 5 in geometry for the two Qwen3 models.
Coordination note (2026-10-17 04:34 UTC): the 04:31 "Results" section above and the 04:33 "U1 + U1b" section were written in parallel by
two sessions from the same files (same numbers). The 04:31 section's exploratory baseline (always give the fact, think only when its
check fails: 87.2% pooled) is the strongest policy found and sets the reading; U1b adds the Snell-faithful control (78.7%), which
MECHANISM also beats. U1r (seeds 2–3 of the cure arms, launched 04:33 on GPUs 0, 2, 3 by the experiment session) will also report
FACT-FIRST-THEN-THINK, with the U1r-P2 prediction extended: FACT-FIRST-THEN-THINK ≥ MECHANISM pooled on each cure seed.

## U1r results, Qwen3-8B (2026-10-17 05:36 UTC; results/u1r_q8b_cure{1,2,3}.log)
Pooled over geometry + optimization (208 items), cure seed 1 / 2 / 3:
MECHANISM 66.8 / 67.3 / 64.9% | DIFFICULTY 62.0 / 60.6 / 62.0% | uniform 62.5 / 61.5 / 61.5% | SNELL-BINNED 60.1 / 63.9 / 65.9% |
ALWAYS-FACT 61.5 / 60.1 / 60.6% @ 0.40k | **FACT-FIRST-THEN-THINK 73.6 / 72.6 / 72.1% @ 4.6 / 4.4 / 4.4k** (MECHANISM @ 5.3 / 5.1 / 6.7k).
U1r-P1 holds for Qwen3-8B on both new seeds (MECHANISM > DIFFICULTY by +6.7 / +2.9); the extended P2 holds (FACT-FIRST-THEN-THINK
is the best policy on every seed at fewer tokens than MECHANISM). SNELL-BINNED beats MECHANISM on seed 3 (65.9 vs 64.9). Raw: the
fact program fails its check on 20–25 geometry items (thinking fixes nearly all) and 53–57 optimization items (CVRP / VRPTW).
Qwen3-32B and Qwen3.6 cure seeds still running.

## U2 pre-registration (2026-10-17 05:36 UTC, before running): does "facts before compute" survive when the fact must be RETRIEVED?
U1's FACT arms are hand-written (an algorithm hint plus exactly the needed helpers; the exact API snippet). Deployable version:
- optimization: BM25 top-3 documentation snippets (= U1's DECORRELATE arm, already run for seeds 1–3);
- geometry: the K8 toolbox kept (the system does not know which helpers are needed) + the BM25 top-1 note from a small algorithm
  library with near-misses (`--distract 8 --hint_retrieve`), seeds 1–3, 3 models (poc/queues/queue_s2_u2.sh; GPU3 now).
Policy RETRIEVED-FIRST-THEN-THINK: the retrieved program; THINK (same seed) only if it fails the label-free check.
- U2-P1: RETRIEVED-FIRST-THEN-THINK ≥ DIFFICULTY + 5 points pooled (3 models × 2 domains), on each cure seed.
- U2-P2: it is within 5 points of the hand-written FACT-FIRST-THEN-THINK pooled.
- U2-P3: in geometry the retrieved note helps less than the hand-written fact (near-misses retrieved for delaunay / diameter, which
  the library does not cover); the retrieved program passes the check less often than the hand-written one (more thinking spent).

## U2 results, Qwen3-8B (2026-10-17 05:46 UTC; results/u2_q8b.log; cure seeds 1 / 2 / 3; Qwen3-32B / Qwen3.6 still running)
| policy (accuracy @ output tokens per item) | geometry (108) | optimization (100) | pooled (208) |
|---|---|---|---|
| ALWAYS-RETRIEVED (K8 + BM25 note / BM25 top-3 snippets) | 63.0 / 65.7 / 67.6% @ 0.85k | 37 / 34 / 34% @ 0.48k | 50.5 / 50.5 / 51.4% @ 0.68k |
| **RETRIEVED-FIRST-THEN-THINK** | 93.5 / 87.0 / 89.8% @ 3.5 / 2.8 / 3.3k | **49 / 48 / 46%** @ 7.3 / 6.5 / 6.5k | **72.1 / 68.3 / 68.8%** @ 5.3 / 4.6 / 4.9k |
| FACT-FIRST-THEN-THINK (hand-written fact) | 99.1 / 97.2 / 96.3% @ 2.0 / 2.4 / 2.2k | 46 / 46 / 46% @ 7.4 / 6.6 / 6.7k | 73.6 / 72.6 / 72.1% @ 4.6 / 4.4 / 4.4k |
| DIFFICULTY | 94.4 / 91.7 / 90.7% | 27 / 27 / 31% | 62.0 / 60.6 / 62.0% |
- **U2-P1 holds for Qwen3-8B** (retrieved-first-then-think − DIFFICULTY = +10.1 / +7.7 / +6.8 pooled). **U2-P2 holds** (−1.5 / −4.3 / −3.3
  vs the hand-written fact). **U2-P3 holds**: in geometry the retrieved program fails its check more often (34 / 26 / 28 vs 20 / 25 / 22
  items) and the BM25 note is often a near-miss (hull → "Point in polygon: ray casting": hull 1/12 correct vs 12/12 with the hand-written
  hint, seed 2), so ALWAYS-RETRIEVED geometry (63–68%) is no better than the base program (65.7%); the gain over gated thinking from the
  base program (85–88%) is only +2 to +5 points. In optimization the retrieved snippets are worse alone (34–37% vs the hand-written
  snippet 41–42%) but the check sends their failures to thinking, so the retrieved policy ties or beats the hand-written one (46–49%).
**Reading:** a cheap check makes "facts first" robust to imperfect retrieval: a wrong retrieved fact mostly costs tokens (failures
go to thinking), not accuracy, when the check catches them (optimization: feasibility), and costs accuracy where the check is weak
(geometry: examples + symmetry miss some wrong hulls).
Check (05:48 UTC, raw rows): geometry retrieved programs that pass the label-free check but are wrong: 6 / 11 / 7 (hand-written fact: 1 / 0 / 1); thinking fails on 1 / 3 / 4 of the escalated ones (fact: 0 / 3 / 3): the geometry loss is the check's leak on wrong retrieved programs, as stated above.

## U1r + U2 results, all three models (2026-10-17 06:33 UTC; results/u1r_all_cure{1,2,3}.log; 624 items per cure seed)
Pooled accuracy @ mean output tokens per item, cure seed 1 / 2 / 3:
| policy | seed 1 | seed 2 | seed 3 |
|---|---|---|---|
| DIFFICULTY (think on low-agreement items, budget = MECHANISM's) | 73.9% | 74.0% | 75.5% |
| uniform (think when the base program fails its check) | 77.1% | 76.6% | 76.6% |
| ALWAYS-FACT (hand-written fact, no thinking) | 79.3% @ 0.44k | 78.8% @ 0.44k | 78.7% @ 0.45k |
| SNELL-BINNED | 78.7% @ 5.2k | 82.5% @ 5.5k | 80.9% @ 5.5k |
| MECHANISM | 82.5% @ 4.2k | 83.5% @ 4.2k | 82.2% @ 4.7k |
| **RETRIEVED-FIRST-THEN-THINK** (BM25 fact; deployable) | **84.1% @ 3.3k** | **84.1% @ 3.0k** | **83.5% @ 3.4k** |
| **FACT-FIRST-THEN-THINK** (hand-written fact) | **87.2% @ 2.5k** | **87.3% @ 2.4k** | **86.5% @ 2.6k** |
- **U1r-P1 holds** (MECHANISM > DIFFICULTY on every seed: +8.6 / +9.5 / +6.7). **U1r-P2 holds**: ALWAYS-FACT ≥ MECHANISM in optimization in
  9 / 9 model × seed cells (e.g. Qwen3-32B 74 / 76 / 75 vs 72 / 74 / 74), and MECHANISM > ALWAYS-FACT + 5 in geometry for both Qwen3 models on
  every seed (+11 to +18). **U2-P1 holds** (+10.2 / +10.1 / +8.0 over DIFFICULTY); **U2-P2 holds** (−3.1 / −3.2 / −3.0 vs the hand-written
  fact); **U2-P3 holds** (geometry: ALWAYS-RETRIEVED 61–71% for Qwen3-32B vs ALWAYS-FACT 81–83%; the retrieved policy spends more thinking
  tokens in geometry for every model, e.g. Qwen3-32B 2.3–3.0k vs 1.5–1.6k).
- Per cell, the retrieved policy ties or beats the hand-written one in Qwen3-8B optimization (49 / 48 / 46 vs 46 / 46 / 46%) and is 1–10 points
  below elsewhere (largest: Qwen3-8B geometry 87.0 vs 97.2%, seed 2). Thinking truncation is unchanged across seeds (Qwen3.6 geometry hits
  the 28k cap on 64–67 of 108 items per seed; Qwen3 models ≤ 4).
**Reading (now on 3 seeds, 3 models, 2 domains):** "facts before compute" is the best allocation: give every item the fact, spend
thinking only where a cheap check still fails (≈ 87% at ≈ 2.5k tokens, vs 82–84% at 4.2–4.7k for routing by failure mechanism and 74–76%
for routing by difficulty). With retrieved instead of hand-written facts it loses ≈ 3 points, still beats both routers at fewer tokens,
because the check sends wrong retrieved facts to thinking; the remaining loss is wrong retrieved programs that pass the check (geometry).
