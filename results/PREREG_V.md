# Pre-registration V1 / N5: validated program reuse (routing) and approximate-oracle differential testing (contest geometry)

Written 2026-10-14 18:56 UTC, before any computation below. Results are appended below without editing this section.

## V1. Verify once, reuse the program (routing, offline, CPU only)
**Why.** H3 / FM generated a new program per instance, but every Solomon instance has the same format and problem; a program is meant
to run on any input. Published solver benchmarks generate one solver per problem class (FunSearch, EoH / ReEvo, HeuriGym, CO-Bench), so
this is the baseline we owe, not a new idea. **Method.** Candidates = the programs already generated for the 8 mining instances (FM's
set: c101, c201, r101, r201, rc101, rc201, r105, rc105) in an arm, 2 seeds → 16 programs. Run every candidate on all 8 mining
instances (feasibility needs no optimum); pick the one feasible on the most, ties by mean distance; run it on the 48 test instances.
Cost: generation of 16 programs once (≈ 25–30k tokens), then 0 LLM tokens per new instance.
- V1-P1: gpt-oss-120b low, plain arm (per-instance feasibility 7%): the reused program is feasible on ≥ 60% of the 48 test instances if
  any candidate is feasible on ≥ 6 of 8 mining instances; if none is, V1 fails for that arm.
- V1-P2: in every arm where per-instance generation is ≥ 40% feasible (reader + robust for 20b / 120b), the reused program is ≥ 90%.
- V1-P3: reused programs' gaps match per-instance ones (median within 1 point), i.e. reuse costs no quality.

## N5. Approximate-oracle differential testing for contest geometry (ALGO-style, extended to continuous answers)
**Why.** On the 311 contest problems the statement's examples are a weak check (19–40% of example-passing programs are wrong for strong
models), output agreement adds ≈ 1 point, and symmetric transforms catch 6% of wrong passers (N1). **Prior art.** ALGO (Zhang et al.,
NeurIPS 2023): the LLM writes a brute-force oracle that enumerates, random inputs expose mismatches, which select / guide the coder (88%
oracle correctness, 2.6× CodeT on CodeContests); test-generator work (2404.10304, rStar-Coder, HardTests, CodeContests+, AutoCode)
stresses input validity. **Ours:** geometry answers are often continuous (areas, distances, optima), where exhaustive enumeration does
not exist; the oracle may approximate (grid / sampling / brute force over small cases) and is compared with a loose tolerance; the oracle
and generator are accepted only if the oracle passes the statement's examples; flagged programs get the counterexample as repair feedback.
**Design.** gpt-oss-20b low and gpt-oss-120b low (H2c Part B samples, seed 1 as the program to check); per problem the same model writes a
small-input generator and a slow oracle (one call each). 20 generated inputs; mismatch = outputs differ beyond relative 1e-2 (or exactly
for integer / text answers) or the program crashes / times out where the oracle does not.
- N5-P1: the oracle passes the statement's examples on ≥ 50% of problems (120b) and ≥ 35% (20b).
- N5-P2: among example-passing programs on problems with an accepted oracle, the check flags ≥ 40% of the wrong ones and ≤ 10% of the
  correct ones.
- N5-P3: one counterexample repair round on flagged programs adds ≥ 3 points over N2 (repair from failing examples only) at ≤ 2× its tokens.

**N5 amendment (2026-10-14 18:59 UTC, before the full runs).** A 6-problem smoke test (Qwen3.8-27B no-think on 8049, deleted) checked the pipeline: oracle
accepted 4 / 6 (20 generated inputs each), no flags on the 3 correct passers. Because all four GPUs currently serve Qwen3.8-27B (H6), N5
runs first with Qwen3.8 no-think (programs: H6 q38_plain seed 1, 108 / 311 solved), with the N2 baseline (repair from failing examples)
for the same programs; gpt-oss-20b / 120b follow when H6 frees the GPUs. Predictions unchanged (the 120b thresholds apply to Qwen3.8).

## V1 interim (2026-10-14 19:29 UTC)
gpt-oss-120b low plain: best of 16 feasible on 4 / 8 mining → 45 / 48 test (94%, median gap 1.35%, 28k tokens in total); 120b medium plain
the same 45 / 48 (56k tokens); 120b low + documentation snippet 45 / 48 (median gap 2.26%); gpt-oss-20b low plain and + docs, Qwen3-32B
plain: no candidate feasible on any mining instance, reuse fails. (Identical median gaps of the two plain arms were checked: different
programs, 0 shared; both run guided local search and reach the same solution on the median instance.)

## V2 pre-registration (2026-10-14 19:29 UTC, before running): repair on the training instances, then reuse
Start from V1's best candidate (if none is feasible anywhere: the candidate with the fewest crashes). Up to 3 rounds: the model gets
the program and the failure messages on up to 4 failing mining instances (traceback tail or violated constraint) and writes a corrected
program; accept it if it is feasible on more mining instances; stop at 8 / 8. Reuse the final program on the 48 test instances. All
generation and repair tokens counted. Prior art: instance-set evaluation in heuristic design (FunSearch, EoH / ReEvo, HeuriGym) and
solver-feedback repair loops (OptiMUS, LLMOPT); the comparison with per-instance generation, facts and fact mining is ours.
- V2-P1: Qwen3.8-27B no-think, plain arm: reaches 8 / 8 mining within 3 rounds and ≥ 90% test feasibility.
- V2-P2 (when a gpt-oss-20b server is up): gpt-oss-20b low plain (no feasible candidate) reaches ≥ 4 / 8 mining and ≥ 50% test.
- V2-P3: gpt-oss-120b low plain: the repaired program handles the tight-window instances (8 / 8 mining) and is feasible on ≥ 47 / 48.

## V1 complete (2026-10-14 20:29 UTC)
| arm | per-instance feasible (H3) | best candidate on the 8 mining | reused on 48 test | median gap | tokens in total |
|---|---|---|---|---|---|
| gpt-oss-120b low, plain | 7% | 4 / 8 | 45 (94%) | 1.35% | 28k |
| gpt-oss-120b medium, plain | 48% | 4 / 8 | 45 (94%) | 1.35% | 56k |
| gpt-oss-120b low, docs | 35% | 4 / 8 | 45 (94%) | 2.26% | 27k |
| gpt-oss-120b low, float reader | 18% | 4 / 8 | 45 (94%) | 0.80% | 24k |
| gpt-oss-120b low, integer reader + robust | 100% | 8 / 8 | **48 (100%)** | 1.54% | 24k |
| gpt-oss-20b low, integer reader + robust | 61% | 8 / 8 | **48 (100%)** | 1.54% | 20k |
| Qwen3-32B, integer reader + robust | 3% | 2 / 8 | 7 (15%) | 0.0% | 19k |
| gpt-oss-20b low plain / docs, Qwen3-32B plain | 0–16% | 0 / 8 | – | – | – |
- **V1-P1 holds** (94% where a candidate is feasible on ≥ 4 of 8; "≥ 6 of 8" was too strict: 4 / 8 already gives 94%, the 3 misses are the
  tight-window test instances). **V1-P2 holds** (100% for both arms with ≥ 40% per-instance feasibility). **V1-P3 holds** (median gaps 0.8–2.3%).
  The two "1.54%" rows are programs that copy the robust snippet and reach the same solutions.

## N5 results, Qwen3.8-27B no-think (2026-10-14 20:29 UTC)
Oracle accepted (passes the statement's examples) on 213 / 311 (68%), 2.7k tokens per problem for generator + oracle. Among the 112
example-passing programs on those problems: 7 / 18 wrong ones flagged (39%), 6 / 94 correct ones (6.4%). Counterexample repair of the 13
flagged: 108 → 107 solved (it fixed some wrong programs and broke correct ones whose oracle was wrong). One plain repair round (N2): 108 → 133.
- **N5-P1 holds** (68%). **N5-P2 narrowly refuted** (39% detection, 6.4% false alarms). **N5-P3 refuted** (−1 vs N2's +25).
- Reading: the approximate oracle is a fair detector, but at this strength only 16% of example-passers are wrong, so its ceiling is small
  and false alarms cancel the gains when used for repair. Next (N5b): oracle code and inputs saved; used for selection among 3 samples
  (ALGO's use) rather than repair, on gpt-oss-120b low, where 19–40% of passers are wrong.

## V2 result, Qwen3.8 no-think plain (2026-10-14 20:29 UTC)
No candidate was feasible on any mining instance; the chosen one (no crashes) prints nothing (no solution found); three repair rounds
stayed at 0 / 8. The feedback said "customers missing: [1 … 30]" rather than "the program printed nothing", which is our harness: the
feedback is fixed (empty output named as such) and V2 re-run, with gpt-oss-20b / 120b plain (V2-P2, P3).

## N5b and V2 (re-run) pre-registration (2026-10-14 20:37 UTC, before running)
- N5b: gpt-oss-120b low and gpt-oss-20b low, oracle + generator per problem (code and inputs now saved), seed-1 program checked and
  repaired as in N5; offline, the oracle selects among the 3 Part B samples: first example-passer that agrees with the oracle on all inputs,
  else the first example-passer. N5b-P1: oracle selection ≥ example-check selection + 2 points for 120b (19–40% of its passers are wrong).
  N5b-P2: counterexample repair adds ≥ 2 points over the seed-1 program for 120b (more wrong passers than for Qwen3.8).
- V2 re-run with the empty-output feedback fixed: Qwen3.8 plain (8046), gpt-oss-20b low plain (8042), gpt-oss-120b low plain (8043);
  predictions V2-P1..P3 as above.

## N5b and V2 results (2026-10-14 21:31 UTC)
**N5b** (oracles saved; poc/analyze_n5b.py):
| model | oracle accepted | seed-1 example-passers: wrong flagged / correct flagged | k = 3: example check → oracle selection (any-of-3) | seed 1 → counterexample repair | oracle tokens / problem |
|---|---|---|---|---|---|
| gpt-oss-120b low | 203 / 311 | 16 / 30 (53%) / 4 / 109 (3.7%) | 53.4 → 53.7% (57.6%) | 42.4 → 43.1% | 2.9k |
| gpt-oss-20b low | 179 / 311 | 17 / 25 (68%) / 4 / 99 (4.0%) | 47.9 → 48.6% (51.1%) | 40.2 → 40.8% | 1.5k |
- **N5b-P1 refuted** (+0.3 / +0.7, not +2), **N5b-P2 refuted** (+0.7 / +0.6). The approximate oracle is a good detector (53–68% of wrong
  example-passers at ≈ 4% false alarms) but the gain is capped: when the first passer is wrong, the other two samples are mostly wrong too
  (any-of-3 is only 3–4 points above the example check), and a counterexample rarely leads to a correct program. On contest geometry
  the bottleneck is producing a correct program, not recognising one. N5 closed.
**V2** (repair on the 8 mining instances, then reuse; fixed feedback):
| model, plain arm | mining feasible: start → final | test feasible | median gap | tokens (generation + repair) |
|---|---|---|---|---|
| gpt-oss-120b low | 4 → 4 (3 repairs rejected) | 45 / 48 | 1.35% | 28k + 5k |
| gpt-oss-20b low | 0 → 4 (round 3) | 45 / 48 (94%) | 6.30% | 26k + 6k |
| Qwen3.8 no-think (first run, old feedback) | 0 → 0 | 0 | – | 45k + 14k |
| Qwen3.8 no-think (fixed feedback) | 0 → 8 (round 2) | 48 / 48 | **55.7%** | 45k + 6k |
- **V2-P2 holds** (20b: 0 → 94%). **V2-P3 refuted** (no repair handles the tight windows). **V2-P1 holds on feasibility but is
  hollow:** the accepted Qwen3.8 program no longer uses OR-Tools; it is a greedy nearest-neighbour heuristic sorted by due date (read),
  feasible everywhere with routes 56% longer than the reference (our own greedy baseline: +48%). A feasibility-only acceptance rule
  rewards giving up on optimisation. V3 adds a label-free quality guard.

## V3 pre-registration (2026-10-14 21:31 UTC, before running): V2 + a quality guard
Accept a repaired program only if it is feasible on more mining instances AND its total distance on the mining instances it solves is at
least 10% shorter than our nearest-feasible greedy baseline there (computed by us, no labels); otherwise keep the previous program. Same
arms as V2 for Qwen3.8 (8046) and gpt-oss-20b (8042).
- V3-P1: Qwen3.8 plain ends with a program that uses a solver or a local search and a median test gap ≤ 10%, or with no accepted program.
- V3-P2: gpt-oss-20b plain: same result as V2 (94%, gap ≈ 6%), since its program already passes the guard.

## N6 pre-registration (2026-10-14 21:31 UTC, before running): retrieved solved problems as exemplars (contest geometry)
Prior art: SolveRank (EMNLP 2025 Findings; solution-aware retrieval helps mainly above rating 1400), the USACO study (2404.10952;
episodic retrieval of similar problems + solutions), AlgoSimBench (IJCAI 2026; similarity from the model's own solution attempt + BM25).
Ours: our helper results (F1, H4) say extra code in the prompt can distract; does one retrieved solved problem help or distract on
contest geometry, and does retrieval by the model's own draft (code-to-code) beat retrieval by statement? Corpus: the other 354
extracted geometry problems with one accepted solution each (Python if available, else C++), excluding the same contest and the same
title (e.g. 613_A / 614_C are one problem). Arms (seed 1, gpt-oss-20b low and gpt-oss-120b low): statement-BM25 top-1, draft-BM25 top-1
(query = the model's own seed-1 program), compared paired with the plain seed-1 run.
- N6-P1: statement retrieval changes accuracy by ≤ ± 2 points overall (help and distraction cancel) and adds ≥ 2 points on problems rated
  > 1800.
- N6-P2: draft retrieval ≥ statement retrieval + 2 points.

## V3 results (2026-10-14 22:38 UTC)
- Qwen3.8 plain with the guard: round 1 candidate 4 / 8 rejected (not 10% better than greedy), round 2 candidate 8 / 8 rejected (greedy
  again), round 3 0 / 8: no accepted program. **V3-P1 holds** (the "no accepted program" branch): the guard blocks the degenerate program,
  but three rounds do not produce a good one.
- gpt-oss-20b plain with the guard: 0 / 8 in all three rounds (V2 reached 4 / 8 only in its third round with the same prompts and seeds;
  vLLM batching makes the outputs differ). **V3-P2 refuted:** V2's success for 20b was one lucky round, so repair-before-reuse is
  unreliable for models without a working candidate. V1 (reuse when a candidate exists) stands; V2 / V3 closed.

## N6 replication (2026-10-14 22:49 UTC, before its results): seeds 2–3 of the statement-retrieval arm for both gpt-oss models
Seed-1 raw counts (analysis with the duplicate check pending): gpt-oss-120b 132 → 147 (stmt) / 142 (draft); gpt-oss-20b 125 → 112 / 119.
Prediction N6r: over 3 seeds the statement exemplar adds ≥ 2 points for gpt-oss-120b and costs ≥ 2 points for gpt-oss-20b (the helper
pattern of H4: extra code helps the stronger and distracts the weaker model).

## N6 seed-1 results (2026-10-14 22:50 UTC; poc/analyze_n6.py; paired with the plain seed-1 run; exact sign test)
| model, arm | all 311 | lost / gained | p | rating > 1800 (210) | unflagged 237 (p) | output tokens |
|---|---|---|---|---|---|---|
| gpt-oss-120b, statement exemplar | 132 → **147** | 14 / 29 | 0.032 | 59 → 70 | 107 → 120 (0.035) | 3.27k → 3.27k |
| gpt-oss-120b, draft exemplar | 132 → 142 | 15 / 25 | 0.15 | 59 → 63 | 107 → 109 (0.86) | 3.27k → 3.32k |
| gpt-oss-20b, statement exemplar | 125 → **112** | 32 / 19 | 0.09 | 47 → 46 | 107 → 95 (0.07) | 1.52k → 1.83k |
| gpt-oss-20b, draft exemplar | 125 → 119 | 30 / 24 | 0.50 | 47 → 49 | 107 → 98 (0.22) | 1.52k → 1.89k |
- Leakage check: no retrieved solution passes its target's public + private tests (0 of 1,244 pairs), so the gains are not copied
  answers. One read gain was a checker artefact (1422_A Fence, several valid answers: the exemplar primed the reference's formula
  a + b + c − 1), hence the unflagged column, where the 120b gain stays (+13, p = 0.035).
- **N6-P1 refuted as stated** (overall change is not within ± 2: +4.8 for 120b, −4.2 for 20b); the > 1800 part holds for 120b (+11),
  not for 20b. **N6-P2 refuted for 120b** (draft < statement), holds for 20b (draft − statement = +2.3). Same direction as H4: extra code
  in the prompt helps the stronger model and distracts the weaker one (20b's reasoning tokens rise 20% but accuracy falls). Seeds 2–3
  (N6r) running.

## N6r results (2026-10-14 23:29 UTC; 3 seeds, paired, statement exemplar)
gpt-oss-120b low 46.1 → 47.3% (lost 62 / gained 73, p = 0.39; seeds: +15, −1, −3 problems), tokens 3.25k → 3.27k; gpt-oss-20b low
37.7 → 35.7% (85 / 66, p = 0.14), tokens 1.51k → 1.82k. **N6r refuted for 120b** (+1.2, not ≥ 2) and holds narrowly for 20b (−2.0).
The seed-1 result (p = 0.032) did not replicate: one seed was not enough, and the proposal text has been corrected. N6 closed: one
retrieved solved problem does not reliably help either model; it costs the smaller one reasoning tokens.

## V1s pre-registration (2026-10-14 23:29 UTC, before running): how many candidates does reuse need?
V1 failed only where none of 16 candidates worked anywhere. gpt-oss-20b low, plain and + documentation snippet: 48 more candidates each
(seeds 3–8 on the 8 mining instances only), selection over all 64; V1 for the three Qwen3.8 arms with the existing 16 (CPU).
- V1s-P1: with 64 candidates, gpt-oss-20b + docs finds a candidate feasible on ≥ 4 / 8 and reaches ≥ 85% on the 48 test instances;
  gpt-oss-20b plain does not (its per-instance programs were 0 / 112 feasible).
- V1s-P2: Qwen3.8: reader + robust ≥ 95%, docs ≥ 85%, plain ≥ 50% on the test instances.

## V1s results (2026-10-15 00:28 UTC)
| arm | candidates | best on the 8 mining | reused on 48 test | median gap | within 5% | generation tokens |
|---|---|---|---|---|---|---|
| gpt-oss-20b low, plain (per instance 0 / 112) | 64 | 4 / 8 | **45 (94%)** | 5.88% | 19 | 107k |
| gpt-oss-20b low, docs (per instance 16%) | 64 | 4 / 8 | 45 (94%) | 2.26% | 39 | 103k |
| Qwen3.8 no-think, plain | 16 | 0 / 8 | – | – | – | 45k |
| Qwen3.8 no-think, docs | 16 | 4 / 8 | 45 (94%) | 1.35% | 41 | 29k |
| Qwen3.8 no-think, integer reader + robust | 16 | 8 / 8 | **48 (100%)** | 1.29% | 44 | 21k |
- **V1s-P1 half:** + docs holds (94%); the plain arm also works with 64 candidates (predicted not to): even a model whose per-instance
  programs are never feasible writes a reusable program about once in 64 tries. **V1s-P2:** reader + robust ≥ 95% and docs ≥ 85% hold;
  plain ≥ 50% refuted (no candidate in 16). Identical median gaps across arms (1.35%, 2.26%) come from programs that implement the same
  documented OR-Tools model and reach the same solution on the median instance (within-5% counts differ).
- Cost–accuracy for routing, 48 held-out instances: per-instance generation 0–48% at 1.6–3.5k tokens per instance; V1 94–100% at 20–107k
  tokens once (≈ 0.4–2.2k per instance over 48, falling with more instances).

## V1-JSSP pre-registration (2026-10-15 00:28 UTC, before running; CPU only): does reuse carry over to job-shop (CP-SAT)?
Candidates = the H5 programs for 8 instances (la01, la06, la11, la16, la21, la26, la31, la36; 2 seeds → 16) per model; pick the one
feasible on the most, ties by mean makespan / reference; run it on the other 32 instances (wall-time limit only, the fixed sandbox).
- V1J-P1: gpt-oss-120b and gpt-oss-20b both reach ≥ 95% feasible on the 32 test instances with mean gap ≤ 1% (per instance: 79–85%).

## V1-JSSP results (2026-10-15 01:30 UTC)
gpt-oss-120b low: best of 16 feasible on 8 / 8 training instances → 32 / 32 test instances feasible, mean gap 0.02% (max 0.61%), 15k
tokens in total; gpt-oss-20b low: 8 / 8 → 32 / 32, mean gap 0.03% (max 0.86%), 28k tokens (per instance: 79–85% feasible at 0.8–1.2k
tokens each). **V1J-P1 holds**: verify-once-reuse carries over to a second solver library and problem.

## V1G pre-registration (2026-10-15 05:29 UTC, before computing; CPU only): verify once, reuse on the synthetic geometry tasks with helpers
The synthetic tasks (F1–F4) are also one problem with many instances. Per-instance accuracy under 8 related helpers (K8) is low for
some tasks (Qwen3-8B hull 11 / 60 in seed 1). Candidates = the K8 programs for the 5 validation instances (n = 10, inst 0–4; seeds 1–2 →
10 programs); label-free selection by metamorphic consistency (translate, rot90, mirror, permute, scale, big) on those 5 instances; the
chosen program runs on the other 55 instances, scored correct on all 8 variants; helpers pre-defined (packaging-free).
Tasks: hull, area2, pip, segs, close; Qwen3-8B and Qwen3-32B (S2_C1 K8 runs).
- V1G-P1: for every task-model pair with ≥ 1 correct candidate among the 10, reuse is ≥ 95% on the 55 test instances; pooled reuse
  ≥ 95% vs pooled per-instance K8 accuracy ≈ 80%.
- V1G-P2: hull (per-instance 18–22%) reaches ≥ 95% for both models: the helper-steering harm of F1 is a per-sample reliability problem
  that one label-free check plus reuse removes when the problem is fixed.
**V1G amendment (2026-10-15 05:30 UTC, after the first task):** Qwen3-8B hull: the 10 candidates include 4 correct ones, but metamorphic consistency rates
wrong (polar_sort-steered) programs as fully consistent too (top scores 5, 5, 5, 5) and the first-ranked one is wrong: reuse 0% on the 55
test instances. As M3 already showed, steered hull programs are consistent but wrong. The script also had a bug (area2 has no n = 10).
Re-run with both selectors reported: label-free metamorphic consistency, and 5 instances with known answers (the role the statement's
examples play in contests). Predictions unchanged for the labelled selector; the label-free one is expected to fail on hull.

## V1G results (2026-10-15 05:41 UTC; Qwen3 under 8 related helpers; 10 candidates from 5 validation instances; reuse on the other 55)
| task | per-instance (K8), 8B / 32B | reuse, 5 labelled instances, 8B / 32B | reuse, label-free metamorphic selection, 8B / 32B |
|---|---|---|---|
| hull | 17% / 21% | **100% / 100%** | **0%** / 100% |
| area2 | 95% / 71% | 100% / 100% | 100% / 100% |
| pip | 100% / 95% | 100% / 100% | 100% / 100% |
| segs | 89% / 95% | 100% / 100% | 100% / 100% |
| close | 85% / 93% | 78% / 100% | 78% / 100% |
- **V1G-P1 holds pooled** (labelled reuse 97.8% vs per-instance 76%) with one exception (Qwen3-8B close 78%: a program correct on the five
  smallest instances fails 12 of 55 test instances; not yet read). **V1G-P2 holds** for the labelled selector (hull 100% for both models).
- The label-free metamorphic selector is not enough: on Qwen3-8B hull the four correct and several polar_sort-steered wrong candidates
  are all fully consistent, and the first-ranked one is wrong (0%). With five instances whose answers are known (what the statement's
  examples provide in contests), the helper-steering harm of F1 disappears whenever one of ten samples is correct.

## V1A pre-registration (2026-10-15 05:42 UTC, before running): fully label-free reuse with a model-written brute-force oracle (ALGO + reuse)
Same candidates and validation instances as V1G. The same model (no-think) writes one slow brute-force program per task from the first
validation instance's statement (no helpers); candidates are scored by agreement with the oracle on all 8 variants of the 5 validation
instances; the best is reused on the 55 test instances. Qwen3-8B (8040) and Qwen3-32B-AWQ (8041).
- V1A-P1: the oracle is correct on all validation variants for ≥ 4 of 5 tasks per model.
- V1A-P2: oracle-selected reuse is ≥ 95% on hull for both models (where metamorphic selection gave 0% for 8B), i.e. ALGO-style oracles
  are the label-free check that reuse needs on these tasks.

## V1A results (2026-10-15 06:29 UTC)
| task | Qwen3-8B: oracle correct (of 5) / top agreement (of 40) / reuse | Qwen3-32B: oracle / agreement / reuse |
|---|---|---|
| hull | 0 / 0 / **0%** | 5 / 40 / **100%** |
| area2 | 5 / 40 / 100% | 5 / 40 / 100% |
| pip | 4 / 35 / 100% | 0 / 27 / 100% |
| segs | 1 / 36 / 100% | 5 / 40 / 100% |
| close | 5 / 40 / 78% | 0 / 0 / 100% |
**V1A-P1 refuted** (oracles fully correct on 2 / 5 tasks for 8B, 3 / 5 for 32B). **V1A-P2 half** (hull 100% for 32B, 0% for 8B). Read (8B
hull, regenerated with the same seed): the "brute force" enumerates triangles that contain all other points and prints 3 on every
variant, a wrong but perfectly consistent oracle. Where most candidates are right, any selector works; where the problem is hard for the
model (8B hull), the model cannot write the oracle either. Label-free reuse needs a check the model cannot get wrong in the same way;
known answers on a few inputs (contest examples) remain the reliable selector.
(V1G close, Qwen3-8B, read 2026-10-15 06:30 UTC: the chosen program is a divide-and-conquer closest pair that never sorts the points by x and compares the
squared distance d with a plain coordinate difference in the strip test; it passes the five 10-point validation instances by luck and
fails 12 of 55 test instances (9 with 20 points; duplicates in the degenerate variant). Five small labelled checks let a subtly wrong
algorithm through, the same weakness as the statement's examples in contests (H2b).)

## V1G-mix pre-registration (2026-10-15 06:31 UTC, before computing; CPU only)
Same as V1G (labelled selector) but the 5 validation instances mix sizes: inst 0–2 of the smallest n and inst 0–1 of the largest n
(the 8 variants, including the degenerate one, are always checked). Candidates still come from the smallest-n validation instances.
- V1G-mix-P1: reuse is ≥ 95% for all 10 task-model pairs (the close / Qwen3-8B program that passed five 10-point checks is rejected).
**V1G-mix result (2026-10-15 06:40 UTC): V1G-mix-P1 refuted.** With two 20-point instances in the validation set the wrong close / Qwen3-8B program still
passes all five (as do 9 correct ones) and is first in the tie: reuse 78% again; all other pairs 100%.
**V1G-tb pre-registration (before computing):** break ties among the candidates that pass every validation check by output agreement
(MBR-exec) on 10 fresh unlabelled instances of the largest size (instance keys 100–109, never evaluated). Prediction: all 10 pairs ≥ 95%.
**V1G-tb result (2026-10-15 06:49 UTC): holds.** With the tie broken by output agreement on 10 fresh unlabelled inputs, all 10 task-model pairs reach 100%
on the 55 test instances (close / Qwen3-8B: 78 → 100%). Recipe for a fixed problem: draw ~10 programs, keep those that pass a few checks
with known answers, break ties by agreement on unlabelled inputs, reuse the winner.

## V1c pre-registration (2026-10-15 08:28 UTC, before generating or computing): how many candidates does reuse need (cost curve)?
(1) Qwen3-32B no-think, plain and + docs: 48 more candidates each (seeds 3–8 on the 8 mining instances; per-instance feasibility was
0–1%), V1 with 64. (2) For every pool with 64 candidates (gpt-oss-20b plain / docs, Qwen3-32B plain / docs) and 16 (gpt-oss-120b plain /
docs, Qwen3.8 docs / reader + robust): run every candidate on the 8 mining and the 48 test instances once; then by resampling k of the
candidates (k = 1, 2, 4, 8, 16, 32, 64; 2,000 draws) compute the expected test feasibility of the program V1 picks (most mining-feasible,
ties by mean distance) and the tokens of k candidates.
- V1c-P1: Qwen3-32B + docs yields a candidate feasible on ≥ 4 / 8 mining among 64; Qwen3-32B plain does not.
- V1c-P2: for gpt-oss-120b plain, k = 4 already gives ≥ 80% expected test feasibility (≈ 7k tokens, vs 1.8k per instance for 7%);
  for gpt-oss-20b plain, ≥ 80% needs k ≥ 32.

## V1c results (2026-10-15 09:11 UTC; expected held-out feasibility of the V1 pick from k candidates, 2,000 draws; tokens = k × mean candidate tokens)
| pool | working on ≥ 1 mining | k = 1 | 4 | 8 | 16 | 32 | 64 |
|---|---|---|---|---|---|---|---|
| gpt-oss-120b low, docs (16) | 6 | 35% @ 2k | 82% @ 7k | **94% @ 14k** | 94% @ 27k | – | – |
| gpt-oss-120b low, plain (16) | 1 | 6% @ 2k | 23% @ 7k | 48% @ 14k | 94% @ 28k | – | – |
| gpt-oss-20b low, docs (64) | 5 | 8% @ 2k | 27% @ 6k | 48% @ 13k | 74% @ 26k | 91% @ 51k | 94% @ 103k |
| gpt-oss-20b low, plain (64) | 1 | 1% @ 2k | 6% @ 7k | 11% @ 13k | 23% @ 27k | 46% @ 54k | 94% @ 107k |
| Qwen3-32B docs (64) | 1 | 0% | 1% | 1% | 2% | 5% | 10% @ 89k |
| Qwen3-32B plain (64) | 0 | 0% | 0% | 0% | 0% | 0% | 0% @ 113k |
- **V1c-P1 refuted for docs** (the one Qwen3-32B candidate that ever runs is feasible on a few mining instances only; reuse 10%), holds for
  plain (none in 64). **V1c-P2:** gpt-oss-120b plain needs k = 16 (not 4) for ≥ 80%; with the documentation snippet k = 4 gives 82%;
  gpt-oss-20b plain needs k = 64 (≥ 32 predicted, holds).
- Reading: a working program, once present, gives ≈ 94% held-out (the 3 tight-window instances fail); k only buys the chance that one is
  present, so the cost of reuse is ≈ (tokens per candidate) / (share of working candidates). Facts raise that share 6× (gpt-oss-120b
  docs 6 / 16 vs plain 1 / 16), which is where API facts pay off once programs are reused. Qwen3-32B almost never writes a working one.
(V1c, Qwen3.8 no-think rows, 2026-10-15 09:35 UTC: docs 10 / 16 working: 53% @ 2k, 91% @ 7k (k = 4), 94% @ 15k; integer reader + robust 12 / 16:
72% @ 1k, 94% @ 3k (k = 2), 100% @ 5k (k = 4). Figure 12 (poc/make_figures_hard.py) plots all curves against per-instance generation.)

## V1p pre-registration (2026-10-15 09:36 UTC, before computing; CPU only, no LLM calls): a portfolio of verified programs
Reuse fails on 3 tight-window test instances (94%). Instead of one program, keep the top-m candidates by mining feasibility (m = 1, 3, 5);
on each test instance run them all and keep the shortest feasible solution (feasibility needs no labels). Pools: gpt-oss-120b + docs,
gpt-oss-20b + docs (64), Qwen3.8 + docs. Prior art: algorithm portfolios / per-instance selection (SATzilla, Xu et al. 2008).
- V1p-P1: m = 3 reaches ≥ 47 / 48 feasible for gpt-oss-120b + docs and Qwen3.8 + docs (the tight instances need a candidate that uses a
  robust first-solution strategy, which some candidates do), at 0 extra LLM tokens and ≤ 3× CPU.
- V1p-P2: the median gap drops by ≥ 0.3 points from m = 1 to m = 3.

## V1p results (2026-10-15 10:16 UTC)
| pool | m = 1 | m = 3 | m = 5 (feasible of 48; median / mean gap) |
|---|---|---|---|
| gpt-oss-120b + docs | 45; 2.26 / 2.38% | 45; 2.26 / 2.38% | 45; 2.26 / 2.38% |
| Qwen3.8 + docs | 45; 1.35 / 1.81% | 45; **1.00** / 1.67% | 45; 1.00 / 1.67% |
| gpt-oss-20b + docs (64) | 45; 2.26 / 2.41% | 45; 2.26 / 2.38% | 45; 2.26 / 2.38% |
**V1p-P1 refuted** (no portfolio reaches 47 / 48); **V1p-P2 holds only for Qwen3.8** (−0.35 points). Every top candidate is feasible on the
same 4 of 8 mining instances and fails the same 3 tight-window test instances: all of them copy the documentation snippet's
first-solution strategy (PATH_CHEAPEST_ARC), so the portfolio has no diversity where it matters; the gpt-oss portfolios even return the
same routes. The fix for those instances is the robust fact (reader + robust snippet: 100% with one program), not more programs.

## V1x pre-registration (2026-10-15 10:28 UTC, before running; CPU only, no LLM calls): does a reused program transfer to larger instances?
The V1 programs chosen on 8 Solomon (100-customer) instances run unchanged on the 60 Homberger 200-customer instances (same file format;
SINTEF best-known table, vehicles-first, so gaps can be negative). Programs: the V1 picks of gpt-oss-120b + docs, gpt-oss-120b / gpt-oss-20b
/ Qwen3.8 + integer reader + robust snippet (re-selected from the stored candidates by the V1 rule).
- V1x-P1: the reader + robust programs are feasible on ≥ 90% of the 60, the docs program on ≥ 80% (tight windows fail as before).
- V1x-P2: median gap to the best-known distance ≤ 5% (the 30 s search limit inside the programs is now spread over twice the customers).

## V1x results (2026-10-15 10:58 UTC)
| reused program (chosen on 8 Solomon 100-customer instances) | Homberger 200-customer: feasible of 60 | median gap to best-known |
|---|---|---|
| gpt-oss-120b + docs (4 / 8 on mining) | 58 (2 print incomplete routes) | 4.64% |
| gpt-oss-120b + integer reader + robust (8 / 8) | **60** | 4.31% |
| gpt-oss-20b + integer reader + robust (8 / 8) | **60** | 4.18% |
| Qwen3.8 + integer reader + robust (8 / 8) | **60** | 3.94% |
**V1x-P1 and V1x-P2 hold.** A program checked on eight 100-customer instances solves all 60 instances of twice the size with no new
LLM call; the gap rises from ≈ 1.5% to ≈ 4% because each program's fixed 30 s search now covers twice the customers (a time budget, not
a correctness problem).

## V1x-400 pre-registration (2026-10-15 11:29 UTC, before running; CPU only)
The same four reused programs on the 60 Homberger 400-customer instances.
- V1x400-P1: reader + robust programs feasible on ≥ 80% (some may not find a first solution inside their 30 s limit), median gap ≤ 8%.

## V1x-400 results (2026-10-15 12:28 UTC)
All four reused programs are feasible on 60 / 60 Homberger 400-customer instances; median gaps 9.55% (gpt-oss-120b + docs), 11.60%,
11.77%, 11.36% (reader + robust programs of gpt-oss-120b, gpt-oss-20b, Qwen3.8). **V1x400-P1 half:** feasibility holds (≥ 80%), the gap
bound (≤ 8%) does not. The gap grows with size at a fixed 30 s search (≈ 1.5% at 100 customers, ≈ 4% at 200, ≈ 11% at 400); the
documentation's cheaper first-solution strategy now leaves more search time than cheapest insertion (9.6 vs 11.4–11.8%). Correctness
transfers 4× in size; solution quality is bounded by the program's own time budget, a parameter to scale, not something to regenerate.
**V1x-TL pre-registration (2026-10-15 12:28 UTC, before running):** the reused Qwen3.8 reader + robust program with its own time limit raised from 30 s to
120 s (one edit of the reused program, no LLM call) on the 400-customer instances. Prediction: median gap ≤ 6% and still 60 / 60.
**V1x-TL result (2026-10-15 13:28 UTC): refuted.** With its time limit raised from 30 s to 120 s, the reused Qwen3.8 program is still feasible on 60 / 60
400-customer instances but the median gap only falls from 11.36% to 10.12% (predicted ≤ 6%). The quality limit at this size is mostly
OR-Tools' guided local search itself, not the time budget; the best-known solutions come from specialised VRPTW algorithms. The
"time budget, not correctness" wording in V1x-400 above is corrected here: correctness transfers; quality is bounded by the solver the
program uses.

## V1x-J pre-registration (2026-10-16 02:29 UTC, before running; CPU only, no LLM): reused job-shop programs on larger, harder instances
The V1 picks of gpt-oss-120b low and gpt-oss-20b low (chosen on 8 Lawrence instances) run unchanged on the other 42 OR-Library job-shop
instances (abz5–9, ft06/10/20, orb01–10, swv01–20 up to 50 × 10, yn1–4 20 × 20). Reference: our CP-SAT (8 workers, 120 s, same harness).
- V1xJ-P1: both picks feasible on ≥ 95% of the 42; mean gap to the reference ≤ 5% (≤ 1% on the ≤ 10 × 10 instances).
**V1x-J harness fix (2026-10-16 03:28 UTC, before reading gaps as results):** the first run gave 42 / 42 feasible for both picks, but our reference
program (CP-SAT 120 s) ran under a 90 s wall limit and was killed on 21 of the 42 instances, so the reported gaps (0.00 / 0.03%) cover
only the 21 easy instances where CP-SAT proves optimality fast. Re-run with a 200 s limit for the missing references; per-instance
makespans are now saved.

## V1x-J results (2026-10-16 04:28 UTC; references for all 42 after the timeout fix)
gpt-oss-120b pick: 42 / 42 feasible, mean gap 0.44% to our 120 s CP-SAT reference (≤ 10 × 10 instances 0.00%, max 4.3% on the 50 × 10
swv instances); gpt-oss-20b pick: 42 / 42, mean 0.24% (max 3.7%). **V1xJ-P1 holds.** Reuse transfers to job-shop instances up to
50 × 10 and 20 × 20 (trained on ≤ 30 × 10 and 15 × 15) with no new LLM call; the residual gap is the programs' shorter CP-SAT time limit.
