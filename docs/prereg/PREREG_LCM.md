# Pre-registration LCM: the cascade derived, not hand-set — a model of every call's answer and the Bayes-optimal policy under it

Written 2026-10-31 21:4x UTC, before `poc/lcm.py` has been run on any real cell (the self-test on synthetic data, below, is the only result).

**Why (the goal: exactly right answers with the fewest tokens).** Every policy so far is hand-set: a fixed order (quick answer → free
check → a peer's quick answer → short think → think → retry), a fixed 2k budget, a peer chosen by "another family", a check that
gates by rule, and a 30-label pilot that picks among such rules. THESIS showed the rule's sign cannot be read from small labelled
samples (word problems 10 / 24), and the user ruled out heuristics. The principled object is the decision problem itself: a joint
model of what every call returns on a question, with the policy that maximises expected utility under it.

**Model** (`poc/lcm.py`; per question). A latent class z ~ Cat(π). Each call of type t ∈ {N quick, P peer's quick, SB short think,
T think} independently returns a right answer with prob a[t][z], nothing usable (no answer / an execution error) with prob x[t][z],
else a wrong answer. Right answers come in variants (BFCL's checker accepts several call forms: 12–19% of BFCL questions have two right
answers among the stored calls) following a CRP with concentration φ_z. Wrong answers follow a two-level Chinese restaurant franchise
(Teh et al., JASA 2006): each model (the answering model; the peer) reuses its own wrong answers with concentration θ1_z, and draws new
ones from a question-level pool shared by both models with concentration θ0_z — a model repeats its own mistakes more than another
model shares them (measured: a second sample of the same Qwen3 model repeats a wrong SQL answer 87–90% of the time, another model
52–62%), and a class with small θ0 is a trap where everyone lands on the same wrong answer. The free check passes with prob c[t][role].
The marginal likelihood of a labelled partition is exact (Stirling numbers per restaurant and dish, a CRP over tables per dish) and
projective, so the predictive of the next call is a likelihood ratio (checked: the predictive sums to 1).
**Fit.** EM over (z, which observed answers are right) on all 12 calls of every question of the fitting half (unlabelled), with k
questions whose right answers are revealed; θ0, θ1, φ by exact maximisation over log grids; K ∈ {1, 2, 3} by BIC.
**Policy.** For one seed's five calls (N, P, SB, T, the retry T) the Bayes-optimal adaptive policy by dynamic programming over
observation patterns (question-independent, solved once per fitted model): at every pattern either stop and return the answer most
likely right, or make the call whose expected value net of its cost (λ = 0.5 points per 1k tokens × the call type's mean tokens) is
largest. It may call in any order, skip the check's role entirely, or return the peer's answer: whatever the model says is best.

**Theory.** Under the model the policy is optimal among all adaptive policies over these five calls that return an observed answer,
so in expectation it is at least as good as every fixed policy (N, SB→T→T, T→T, N→T→T, the peer cascade) and the best of them chosen
with all labels. On real data it can lose only through misspecification (calls not independent given the class and the two
partitions; classes beyond K = 3), through estimation error, or through the cost model (expected tokens per call type; exact for the
expected cost). Self-test (`python lcm.py --synthetic` style, 600 questions from a known two-class model): BIC picked K = 2 and
recovered π, a, θ0, θ1 (e.g. a_N 0.73 / 0.22 vs 0.75 / 0.20; θ0 3.2 / 0.8 vs 3.2 / 0.4) with 0 or 30 labels; the fitted planner
realised +86.2 / +86.5 utility against +85.8 for the true-model planner and +83.1 for the best fixed policy (T→T).
Related work: Dawid–Skene assumes independent errors and fails when LLM judges share mistakes (Nine Judges, Two Effective Votes,
arXiv 2605.29800; partial identification without independence, 2606.15031; a beta-binomial latent class model for correlated repeated
judgments, 2510.23874); semi-supervised evaluation of classifiers with labelled + unlabelled data (2501.11866); the Bayes-optimal
deferral rule needs the true posterior, and confidence-based deferral matches it only under an ordering condition, failing when
errors are correlated (Jitkrittum et al., 2307.02764). None models wrong-answer coincidence across and within models for exact-answer
tasks, nor derives the call policy from such a model.

**Cells (31).** SQL: BIRD dev and the fresh BIRD questions × (Qwen3-8B ← Qwen3.5-9B, Qwen3-14B-AWQ ← Qwen3.5-9B, Qwen3.5-9B ←
Qwen3-8B, gpt-oss-20b ← Qwen3.5-9B); tool calls: BFCL non-live and live × the same four; word problems: OptiBench third, BWOR,
LogiOR, OptMATH × (Qwen3-8B ← gpt-oss-20b, Qwen3-14B-AWQ ← Qwen3.5-9B, Qwen3.5-9B ← Qwen3-8B, gpt-oss-20b ← Qwen3.5-9B; no OptMATH
think for gpt-oss). **Protocol.** Cross-fitting over the two halves of each cell's questions (crc32(id) mod 2): fit on one half
(k = 30 labelled questions drawn at random, 3 draws; also k = 0; also the independent-errors model, θ0 = θ1 = 1000, k = 30), act on the
other half's question-seeds with their stored calls; per question the mean utility over seeds and label draws; paired 95% bootstrap
intervals over all questions of the cell. Comparators on the same questions: the default peer cascade; the fixed policy a 30-label
pilot picks on the fitting half (the same label draws); the best fixed policy chosen with all labels of the evaluation half (oracle).

**Predictions.**
- **LCM-P1:** planner (k = 30) − default cascade: lower bound > 0 in ≥ 16 of 31 cells, upper bound < 0 in ≤ 3.
- **LCM-P2:** planner (k = 30) − the 30-label pilot's policy: lower bound > 0 in ≥ 16 of 31, upper bound < 0 in ≤ 3.
- **LCM-P3:** planner (k = 30) − the oracle fixed policy: lower bound > 0 in ≥ 8 of 31.
- **LCM-P4:** planner (k = 30) − the independent-errors planner (k = 30): lower bound > 0 in ≥ 10 of 31, upper bound < 0 in ≤ 3.
- Reported: k = 0 against the default and against k = 30; each planner's accuracy and tokens next to the oracle fixed policy's
  (dominance, at any λ, when both are better); the chosen K, θ0 / θ1 / φ per class; the token cost of the unlabelled fitting pool
  (all 12 calls per question); the planner's calibration (posterior of the returned answer vs its realised correctness).

**Decision.**
- P1 and P2 hold: the derived planner replaces the hand-set cascade and the label pilot as the method; PROJECT, REPORT and PROPOSAL
  are rewritten around it, and FINAL's Spider cells are run through it as a pre-registered addendum.
- P3 holds as well: the claim adds that it beats every fixed cascade, even one chosen with all labels.
- P1 or P2 refuted: not adopted; the report says where the model fails (calibration and fit per cell).
- P4 refuted: the shared-wrong-answer structure is not what the planner needs; reported.

**Run.** `bash poc/slurm/lcm_cells.sh` (8 CPU jobs, four cells each); per cell `results/lcm/<task>_<set>_<gen>_<peer>.json`; the
summary `python3.11 poc/analyze_lcm.py` (written before the cells finish).

## Results (written 2026-10-31 22:4x UTC; `results/lcm.txt`, `results/lcm/*.json`; 30 of the 31 cells — the 31st, OptMATH with Qwen3-8B ← gpt-oss-20b, stopped on a loader that wrongly required the peer's think rows, fixed and rerunning as job 1290450; it cannot change any verdict)

Process note: the first submission ran only one cell per job (background processes started outside the repository); the other 24
were resubmitted unchanged (jobs 1290217–1290222).

| prediction | better / worse (of 30) | verdict |
|---|---|---|
| LCM-P1 planner (k = 30) − default cascade | 4 / 13 | **refuted** |
| LCM-P2 planner − 30-label pilot | 10 / 5 | **refuted** (needed 16 / ≤ 3) |
| LCM-P3 planner − oracle fixed | 2 / 13 | **refuted** |
| LCM-P4 planner − independent-errors planner | 1 / 13 | **refuted** (the shared-error model is worse) |

By task: on SQL (8 cells) the planner loses to the default by 0.8–1.7 utility (worse in 7) and spends more tokens (e.g. Qwen3-8B dev
59.3% @ 2.51k against 59.9% @ 1.39k); on BFCL (8) it loses by 0.3–4.9 (worse in 6); on the word problems (14) it gains in 4
(LogiOR +4.3 / +5.7 / +10.4, OptiBench Qwen3-8B +2.4), loses in 1 (OptiBench gpt-oss-20b −2.4), the rest inconclusive. k = 0 is worse
than the default in 11 cells. At any λ (at least as accurate, no more tokens than the best fixed policy): 3 / 30.
**Diagnosis.** The fitted models have a class in which every call is almost never right and all calls share one wrong answer
(BFCL live, Qwen3-8B: π 0.66, a ≈ 0.00–0.06 for every call type, θ0 0.2). Unanimous agreement has likelihood Π_t a_t^{n_t} as a right
answer but tends to 1 as a shared wrong answer when θ0, θ1 → 0, so on unlabelled questions the model explains agreement as a trap; the
30 labelled questions sit in the other classes and never constrain it (unlabelled data degrading a misspecified generative model,
Cozman & Cohen, 2003). The independent-errors model cannot do this, which is why it does better (P4). Calibration of the returned
answers' posteriors on three cells is being computed (jobs 1290445–1290447) for the report.
**Decision (as pre-registered).** P1 / P2 refuted: not adopted. The failure is an identifiability failure of the dependence
parameters, addressed by LCM-2 (below), pre-registered separately.

## Addendum LCM-2: the dependence parameters where they are identified (written 2026-10-31 22:4x UTC, after the results above, before any LCM-2 run is read)

**Why and theory.** The roles of a labelled question's calls are known, so its partitions of wrong answers and of right variants
identify θ0, θ1 and φ directly; on unlabelled questions they are confounded with the right rates (the unanimity argument above).
LCM-2 estimates (θ0, θ1, φ) by maximum likelihood on the labelled questions only (shared by all classes), and π, a, x and the check
by EM on all questions, as before. A class can then produce a unanimous wrong answer only at the coincidence rate the labels show,
which removes the degenerate explanation; nothing else changes (planner, cross-fitting, label draws, comparators). Also run with
k = 100 labelled questions (reported). Because LCM-2 was designed after seeing LCM's 30 cells, the confirmatory test is on Spider's
test split (FINAL's untouched questions): Qwen3-8B, Qwen3-14B-AWQ, Qwen3.5-9B and gpt-oss-20b with their peers, once those rows exist.

**Predictions.**
- **L2-P1 (development cells, the same 31):** LCM-2 (k = 30) − default cascade: lower bound > 0 in ≥ 10, upper bound < 0 in ≤ 5.
- **L2-P2:** LCM-2 (k = 30) − LCM (k = 30): lower bound > 0 in ≥ 10, upper bound < 0 in ≤ 3.
- **L2-P3:** LCM-2 (k = 30) − the 30-label pilot: lower bound > 0 in ≥ 12.
- **L2-P4 (confirmatory, Spider):** LCM-2 (k = 30) − default cascade: lower bound > 0 in ≥ 3 of the 4 Spider cells, upper bound < 0
  in none.
- Reported: k = 100; calibration; the fitted θ0 / θ1 / φ; dominance at any λ.

**Decision.** L2-P1 and L2-P4 hold: the derived planner (LCM-2) replaces the hand-set cascade as the method (PROJECT, REPORT,
PROPOSAL). L2-P4 refuted: the method stays the cascade, and the report gives the identifiability result and where the derived policy
gains (the word problems) as a finding, not as the method.

**Run.** `LCM_VARIANTS=lcm2:30,lcm2:100 LCM_OUT=results/lcm2 python3 poc/lcm.py <cell>` for the 31 cells (`poc/slurm/lcm_cells.sh`
with those variables), then the same for the four Spider cells; summary `python3.11 poc/analyze_lcm.py --lcm2` (written before the
runs are read).

## Addendum LCM-3: where LCM-2 is still misspecified (written 2026-10-31 23:1x UTC; after reading 28 of LCM-2's 31 development cells and its calibration on three, before any LCM-3 run and before any Spider cell of LCM-2 or LCM-3 exists)

**What LCM-2 shows (development cells, partial; recorded in full with its results).** L2-P1 is already refuted (better than the default in 7,
worse in 12 of 28): BFCL improves over LCM (the degenerate class is gone; BFCL live Qwen3-8B confidence 0.90 vs realised 0.80, was
0.36 vs 0.74), SQL gets worse (−1.4 to −2.7). Stop patterns on BIRD dev, Qwen3-8B (`poc/lcm_patterns.py`, half 1, 2,301
question-seeds): quick, peer and short think agree (39%): posterior 0.99, right 0.87; quick and peer disagree, short think and think
agree on a third answer (5.6%): posterior 0.91, right 0.35; quick = peer, short think = think on another answer (3.7%): the planner
returns the thinks' answer at 0.94, right 0.46. Two misspecifications: (i) one set of dependence parameters for all classes cannot
represent hard questions whose wrong answers are shared far more often (traps); (ii) one restaurant for the whole answering model makes
the short think and the think — the same thinking mode, cut at 2k or not — as independent of each other as the quick answer is of the
think, so their agreement is over-trusted.

**LCM-3.** (i) The dependence parameters per class, estimated on the labelled questions only, each weighted by its class posterior
(identified: their roles are known; the unlabelled questions still cannot pull them into the degenerate direction); (ii) a three-level
franchise: question pool (θ0) → model (θ1) → mode (θ2), with the answering model's quick mode and its thinking mode (short think and
think share it) as separate mode restaurants and the peer as its own (exact marginal; checked: the probabilities of all labelled
partitions sum to 1, and θ2 → ∞ gives back the two-level franchise); (iii) K ∈ {1, …, 5} by BIC (every LCM / LCM-2 fit chose the
largest allowed, K = 3). Grids: θ0, θ1, θ2 ∈ {0.1, 0.4, 1.6, 6.4, 25.6, 1000}. Everything else as LCM-2 (planner, cross-fitting, the
same label draws, comparators); also k = 100.

**Predictions.**
- **L3-P1 (the 31 development cells):** LCM-3 (k = 30) − default: lower bound > 0 in ≥ 10, upper bound < 0 in ≤ 5.
- **L3-P2:** LCM-3 − LCM-2 (k = 30, paired on the same draws): lower bound > 0 in ≥ 10, upper bound < 0 in ≤ 3.
- **L3-P3 (the mechanism):** on BIRD dev and BFCL live with Qwen3-8B (`lcm_calib.py`), |mean posterior of the returned answer −
  realised right rate| ≤ 0.08 (LCM-2: 0.19 and 0.10).
- **L3-P4 (confirmatory, Spider's four cells):** LCM-3 − default: lower bound > 0 in ≥ 3 of 4, upper bound < 0 in none.

**Decision.** L3-P1 and L3-P4 hold: the derived planner (LCM-3) replaces the hand-set cascade as the method. Otherwise the cascade
stays; the identifiability result (unanimity cannot be told from a shared mistake without labels) and the measured misspecifications
are reported, with the derived planner's gains where its model holds (word problems) as a finding.

**Run.** `LCM_VARIANTS=lcm3:30,lcm2:30,lcm3:100 LCM_OUT=results/lcm3 bash poc/slurm/lcm_cells.sh`; the Spider cells after FINAL's lanes;
`python3.11 poc/analyze_lcm.py --lcm3`.

## Results LCM-2 (written 2026-10-31 23:4x UTC; `results/lcm2.txt`, `results/lcm2/*.json`; the first submission crashed after fitting on a branch condition and was rerun unchanged, jobs 1290477–1290484; Spider cells 1290636)

- **L2-P1 refuted:** better than the default in 7 of 31, worse in 14 (SQL −1.4 to −2.7, BFCL −0.7 to −7.0 except Qwen3.5-9B +1.4 / +3.3;
  word problems up to +10.1 on LogiOR).
- **L2-P2 refuted:** better than LCM in 8, worse in 6 (BFCL better in 6 of 8, SQL worse in 6 of 8).
- **L2-P3 holds:** better than the 30-label pilot in 12.
- **L2-P4 refuted (confirmatory, Spider):** better than the default in 0 of 4, worse in 3 (Qwen3-8B −1.80, Qwen3-14B-AWQ −1.91, Qwen3.5-9B
  −1.34; gpt-oss-20b −0.71 [−1.67, +0.25]); with 100 labels −1.62 to +0.30.
- Calibration (BIRD dev / BFCL live, Qwen3-8B): mean posterior of the returned answer 0.785 / 0.897 against 0.597 / 0.800 right (LCM:
  0.950 / 0.358 against 0.605 / 0.741): the degenerate class is gone, overconfidence on SQL remains.
**Decision (as pre-registered).** L2-P4 refuted: not adopted; the cascade stays unless LCM-3 (pre-registered above) holds.

## Addendum B: the information limit of the five calls (written 2026-10-31 23:4x UTC, after LCM-2's and LCM-3's Spider cells and 23 of LCM-3's development cells, before `poc/lcm_bound.py` has been run on any cell)

**Why.** Three derived planners (LCM, LCM-2, LCM-3) lose to the hand-set cascade on SQL and tool calls and gain on word problems.
Either the models are misspecified while there is room to gain (a better model is the work), or there is no room: the five calls
(quick, the peer's quick, short think, think, retry think) carry no adaptive information the cascade leaves unused, and no decision rule
can beat it with these calls (new signals are the work). The two are told apart by the best policy under the *known* joint law of the
calls' outcomes. **Estimator.** The supervised planner: on one half of a cell's questions, with all their labels, the empirical law of
every partial observation pattern (which calls were made, which answers coincide, the checks, which answers are right); the Bayes-
optimal stop / call policy under it by dynamic programming; executed on the other half (cross-fitted). Question-seeds reaching a
pattern unseen on the fitting half are scored with the cascade's outcome (reported; this pulls toward the cascade). Same cells (31
development + Spider's 4), λ, utility and paired intervals as LCM.

**Predictions.**
- **B-P1 (room on SQL and tool calls):** supervised planner − cascade: lower bound > 0 in ≥ 8 of the 16 SQL / BFCL development cells.
- **B-P2 (Spider):** lower bound > 0 in ≥ 2 of 4.
- **B-P3 (word problems):** lower bound > 0 in ≥ 4 of 15 (small sets, low power).

**Decision.** B-P1 holds while the LCM planners lose: the gap is misspecification, and its size is the target for a better-specified
model (reported). B-P1 refuted: on SQL and tool calls the cascade is at the information limit of its five calls — the derived-policy
line is closed there, and further gains need new signals, not a better decision rule.

### Results, addendum B (written 2026-10-31 23:4x UTC; `results/lcm_bound.log`; CPU job 1290661)

Supervised planner (the known joint law of the five calls, cross-fitted) − hand-set cascade, utility:

| task | cells with lower bound > 0 / upper bound < 0 | range of the difference |
|---|---|---|
| SQL development (8) | 1 / 1 | −1.05 to +1.42 (gpt-oss-20b dev +1.42 the only gain) |
| BFCL development (8) | 4 / 0 | −0.02 to +4.48 (Qwen3.5-9B +3.19 / +4.48; Qwen3-14B-AWQ +0.85 / +1.12) |
| Spider (4) | 2 / 0 | +0.50 to +0.91 |
| word problems (15) | 3 / 1 | −2.28 to +11.43 (LogiOR Qwen3-8B +11.43, OptMATH +6.63, OptiBench +4.12) |

Question-seeds reaching a pattern unseen on the fitting half (scored as the cascade): 11–58 per cell of 2,000–6,700.
- **B-P1 refuted** (5 of 16 SQL / BFCL cells, needed 8); **B-P2 holds** (2 of 4); **B-P3 refuted** (3 of 15).

**Decision (as pre-registered).** B-P1 refuted: on SQL the hand-set cascade sits at the information limit of its five calls — even a
planner that knows their joint law gains at most about one point (significant in 1 of 8 development cells and in 2 of 4 Spider cells,
+0.7 / +0.9); the derived-policy line is closed for SQL, and further SQL gains need new signals rather than a better decision rule.
The room that exists is where the cascade's fixed rule is badly matched to the model: Qwen3.5-9B's tool calls (+3.2 / +4.5, where
its pre-registered peer, Qwen3-8B, is the weak check) and the word problems (LogiOR, OptMATH, up to +11); there the LCM planners
recovered part of it (LCM-2 on Qwen3.5-9B BFCL +1.4 / +3.3; LogiOR +4.6 to +10.1). So the derived planners failed for two reasons:
misspecification (they reach none of the small SQL room and lose more), and on SQL there was little room to reach.

## Results LCM-3 (written 2026-11-01 00:4x UTC; `results/lcm3.txt`, `results/lcm3/*.json`; jobs 1290567–1290574, Spider 1290635)

- **L3-P1 refuted:** better than the default in 7 of 31, worse in 9 (SQL worse in 4 of 8, −0.4 to −2.2; BFCL better for Qwen3.5-9B
  +1.18 / +1.73, worse for Qwen3-8B and Qwen3-14B-AWQ; word problems better in 5: LogiOR +5.36 / +10.10, OptMATH +4.29 / +5.01,
  OptiBench +2.74; worse in 1, OptiBench gpt-oss-20b −2.02).
- **L3-P2 refuted:** better than LCM-2 in 8, worse in 4 (on Spider better in 3 of 4, +0.48 to +1.08).
- **L3-P3 refuted:** calibration gap 0.215 on BIRD dev (0.790 vs 0.575 right; K = 5), 0.009 on BFCL live (0.773 vs 0.782).
- **L3-P4 refuted (confirmatory, Spider):** better than the default in 0 of 4, worse in 2 (Qwen3-14B-AWQ −1.03, Qwen3.5-9B −0.86;
  gpt-oss-20b +0.07, Qwen3-8B −0.72).
**Decision (as pre-registered).** Not adopted; the cascade stays. With addendum B: on SQL there is at most about one point to gain
over the cascade with these five calls, and the derived planners do not reach it; on word problems and on Qwen3.5-9B's tool calls,
where the cascade's fixed rule fits badly and there is room (B: up to +11), they gain (LCM-3: five word-problem cells +2.7 to +10.1,
Qwen3.5-9B BFCL +1.2 / +1.7), which is reported as a finding, not adopted, since its confirmatory test (Spider) was on SQL.

## Addendum B2: does a new signal lift SQL's information limit? (written 2026-11-01 00:4x UTC, before `lcm_bound.py --peers` has been run)

**Why.** B says that on SQL no decision rule over the five calls gains much over the cascade; gains need new signals. The cheapest new
signals already stored are two more models' quick queries on the same questions and seeds (Qwen3-8B, Qwen3-14B-AWQ, Qwen3.5-9B,
gpt-oss-20b answer every SQL question at every seed). Earlier fixed rules that added a second peer lost (SQL-AND: a second check
halves the useful agreement), but a fixed rule is not the limit. **Test.** B's supervised planner over seven calls (N, the cascade's
peer, two more peers' quick queries, SB, T, retry T) against the same planner over the five, cross-fitted, on the 12 SQL cells
(four generators × BIRD dev, the fresh questions, Spider; every peer row exists).
**Predictions.**
- **B2-P1:** seven-call planner − five-call planner: lower bound > 0 in ≥ 6 of 12.
- **B2-P2:** seven-call planner − cascade: lower bound > 0 in ≥ 6 of 12.
**Decision.** B2-P1 holds: more peers carry information the cascade cannot use; a multi-peer policy (its size reported, with the extra
resident models as its cost) is the next method step. Refuted: quick queries of other models do not lift SQL's limit, and the cascade
with one peer is where these signals stop.

### Results, addendum B2 (written 2026-11-01 00:4x UTC; `results/lcm_bound_b2.log`; CPU job 1290891)
Seven-call planner (N, three peers' quick queries, SB, T, retry T) − five-call planner: −2.71 to +0.18; better in 0 of 12, worse in 6
(all four fresh-question cells, −1.8 to −2.7, and gpt-oss-20b dev −2.45, Qwen3-14B-AWQ Spider −0.87). Seven-call planner − cascade:
better in 1 of 12 (Spider Qwen3-8B +1.09 [+0.11, +2.08]), worse in 5. **B2-P1 and B2-P2 refuted.** Reading: the supervised planner is
estimated from the patterns of 1,300–1,700 labelled questions per half; with two more calls the patterns multiply and the estimate
gets worse out of sample, so whatever information the extra quick queries carry is not usable at these sample sizes (the same caveat
makes B an estimate of the limit, not the limit). **Decision (as pre-registered).** Other models' quick queries do not lift SQL's
limit here; the one-peer cascade is where these signals stop. A new signal for SQL has to be of another kind than one more quick answer.

## Addendum J: a signal of another kind — another model judging the quick query (written 2026-11-01 00:4x UTC, before any judge row exists)

**Why.** B and B2: on SQL the cascade is at the information limit of its calls and more quick answers do not lift it; a new signal must
be of another kind. A judge sees the question, the quick query and what running it returned, and says whether it answers the
question — verification instead of a second generation. Related: LLM judges of text-to-SQL correctness without gold reach AUROC
0.72–0.78 with GPT-4o-class models and 0.82 for a two-provider ensemble, beating self-consistency (What Predicts Correctness in
Text-to-SQL?, arXiv 2607.06799); it does not ask whether a judge adds to an execution check and a peer, at matched cost, nor bound it.
**Run.** Qwen3.5-9B as the judge (`poc/judge_sql.py`, thinking off, one token, P(yes) from the log-probs; only passing quick queries
are judged) of Qwen3-8B's and Qwen3-14B-AWQ's stored quick queries on BIRD dev and Spider (4 cells, 3 seeds). **Analysis.** B's
supervised planner over six calls (N, the peer's quick query, the judge's verdict on N as a non-answer observation, SB, T, retry T)
against the five (`lcm_bound.py --judge q35`); the judge's AUROC on passing N; the judge cascade (N if it passes and the judge says
yes, else SB→T→T). Costs: the judge's output is one token; its input (≈ the quick query's prompt plus the result) is reported.
**Predictions.**
- **J-P1:** six-call planner − five-call planner: lower bound > 0 in ≥ 2 of 4.
- **J-P2:** the judge's AUROC on passing quick queries ≥ 0.70 in ≥ 3 of 4.
- Reported: the judge cascade against the peer cascade; input tokens.
**Decision.** J-P1 holds: a judge is a new signal that lifts SQL's limit, and the cascade with a judge (its rule derived by the
planner) is pre-registered on Spider next. Refuted: at these model sizes a judge adds nothing usable to the execution check and the peer.

### Results, addendum J (written 2026-11-01 01:3x UTC; `results/run_judge_q35.log`, `results/lcm_bound_judge.log`; jobs 1290913, CPU)

| cell | judge AUROC on passing N | six-call − five-call planner | judge cascade − peer cascade |
|---|---|---|---|
| BIRD dev, Qwen3-8B | 0.709 | −0.13 [−0.73, +0.48] | −2.61 [−3.58, −1.64] |
| BIRD dev, Qwen3-14B-AWQ | 0.721 | +0.08 [−0.56, +0.72] | −1.83 [−2.82, −0.91] |
| Spider, Qwen3-8B | 0.624 | −0.17 [−0.70, +0.36] | −2.44 [−3.38, −1.45] |
| Spider, Qwen3-14B-AWQ | 0.612 | −0.87 [−1.39, −0.36] | −1.95 [−2.83, −1.06] |

Judge says yes to 53–56% of passing quick queries on BIRD (2.5k input tokens per judgement) and 76–77% on Spider (0.9k).
- **J-P1 refuted** (0 of 4); **J-P2 refuted** (AUROC ≥ 0.70 in 2 of 4; on Spider 0.61–0.62, at the level 2607.06799 reports for
  fine-tuned verifiers on unseen schemas, 0.66, and below its GPT-4o-class judges).
**Decision (as pre-registered).** A 9B judge adds nothing usable to the execution check and the peer: as a gate it is worse than the
peer (−1.8 to −2.6), and as an extra signal it does not lift the limit. On SQL the information limit holds for a verification signal
too at these model sizes; the method's SQL part is final as the cascade (FINAL), and the remaining room in this project is where the
fixed rule fits the model badly (word problems, a weak peer; addendum B).

## Addendum LS: the derived policy on a new problem set with no label from it (written 2026-11-01 03:5x UTC, before `poc/lcm_shift.py` has scored any policy on any cell; the target loaders were run only to count questions: OptiBench's other 403 and MAMO's 863 for both models)

**What B's room is (exploratory, on B's own development cells, computed 2026-11-01 03:5x UTC; not evidence for what follows).** On the
three word cells where B's planner beats the cascade (Qwen3-8B ← gpt-oss-20b: LogiOR +11.4, OptMATH +6.6, OptiBench +4.1), the
in-sample planner calls the peer first and mostly answers with it: gpt-oss-20b's quick program is right more often than Qwen3-8B's
quick program and short think (LogiOR 43% vs 16% / 28%; OptiBench 67% vs 50% / 64%). The fixed policy "gpt-oss-20b's quick program if
it runs, else Qwen3-8B's SB→T→T" reaches B's planner there (planner − the best fixed policy chosen on the other half, now including that
one: +0.93 [−1.59, +3.63], +0.95 [−2.65, +4.76], −1.52 [−3.37, +0.27]; BWOR −5.26). So on these cells the room is which model of the
pair answers, not an adaptive use of the calls. Where the peer is weak (Qwen3.5-9B ← Qwen3-8B) the room is adaptive (planner − best of
the same fixed policies: BFCL live +4.48 [+3.49, +5.42], non-live +1.39 [+0.29, +2.47], LogiOR +4.49, OptMATH +5.51): it votes the
quick, peer and short-think answers before thinking and abstains where a 24k-token think rarely pays. Either way B's planner used every
label of the half it was fitted on; LCM showed that without labels the law it needs is not identified. This addendum tests whether
labels from *other* problem sets of the same kind can replace them.

**Method (derived; `poc/lcm_shift.py`).** Let c be a question-seed's correctness vector (which of N, P, SB, T, retry T are right) and o
its full observation (the checks and which answers coincide). Assumption (label shift): P(o | c) is the same on every problem set of a
kind; only the prior π(c) moves (a harder or easier set). Then π on a new set is identified from its unlabelled observations when the
columns P(· | c) are linearly independent (Saerens, Latinne & Decaestecker 2002, EM; Lipton, Wang & Smola 2018, BBSE), P(o | c) comes
from the labelled development sets, and the development rows reweighted by π_new(c) / π_dev(c) are a sample of the new set's joint law,
on which B's planner is solved (LS). LCM's no-label setting is not identified because it must learn P(o | c) itself; here it is
borrowed. Cross-fitted over halves of the target (crc32(id) mod 2): π and the calls' mean tokens from one half's unlabelled
question-seeds (all five calls run; their tokens are reported as the one-time cost of the estimation sample), policies act on the other.
Compared: the cascade (Qwen3-8B's adopted word default since XPEER), SB→T→T, T→T; *transfer* (the development rows unweighted, target
tokens); *reference* (B's planner on the target half's own labels, the limit LS tries to reach without them); *pseudo-labels* (B's
planner on the target half with "right" = T's answer, else the retry's: label-free, as C3PO, 2511.07396, uses the strongest model as
the reference); the fixed P→SB→T→T above (reported, post hoc). Related: label shift is identified from unlabelled data given
class-conditionals (Saerens 2002; Lipton 2018; Garg et al. 2020, RLLS); cascades and routers are fitted with target labels (FrugalGPT,
2305.05176; AutoMix, 2310.12963) or with the strongest model as the label (C3PO); none borrows the law of agreement patterns from
labelled sets of another source to fit a cascade on an unlabelled one, and none states when that is identified.

**Cells.** Primary (the confirmatory test): Qwen3-8B and Qwen3-14B-AWQ, peer gpt-oss-20b, development sets OptiBench's third, BWOR,
LogiOR, OptMATH (pooled), targets OptiBench's other 403 problems and MAMO's 863 (XPEER's fresh runs; neither was used by LCM, B, or the
observation above): 4 cells. Reported, not decided: tool calls (BFCL live from non-live and back) and SQL (Spider from BIRD dev +
fresh), the four generators with their pre-registered peers (12 cells).

**Predictions** (paired 95% intervals over problems, seed means, utility = 100 × right − 0.5 × ktokens):
- **LS-P1:** LS − cascade: lower bound > 0 in ≥ 3 of the 4 primary cells.
- **LS-P2:** LS − transfer: lower bound > 0 in ≥ 2 of 4.
- Reported: reference − cascade (the room with labels) and the share of it LS reaches; pseudo-labels; the EM diagnostics (rank of
  [P(o | c)], target observations never seen in development, log-likelihood with the adapted vs the development prior); the 12
  secondary cells.

**Decision.** LS-P1 holds → a derived policy needs no label from a new problem set: labels from other sets of the same kind plus the
new set's unlabelled calls; PROJECT §2 / REPORT replace "a fitted policy needs labels" with that, stated with the label-shift
assumption and the estimation sample's cost; LS-P2 says whether the prior adaptation is part of it or plain transfer suffices.
LS-P1 refuted → on new sets the room is not reached without their labels; the derived-policy claim stays "needs labels of the target",
with the room it leaves (reference − cascade) reported.

Expected (not a rule): LS-P1 2–3 of 4 (MAMO is easy, so the cascade leaves little there); LS-P2 refuted (the role of the peer, the
main room, transfers without adaptation).

### Results, addendum LS (written 2026-11-01 04:0x UTC; `results/lcm_shift.log`, `results/lcm_shift/*.json`; CPU job 1291404)

| target cell (peer gpt-oss-20b) | cascade | LS − cascade | LS − transfer | reference − cascade (target's own labels) | LS − P→SB→T→T |
|---|---|---|---|---|---|
| OptiBench other 403, Qwen3-8B | 70.84 | +0.27 [−0.85, +1.30] | +0.05 [−0.63, +0.75] | −0.26 [−1.42, +0.90] | −0.30 [−1.63, +0.97] |
| MAMO 863, Qwen3-8B | 78.74 | **+1.28 [+0.55, +2.04]** | +0.38 [−0.03, +0.79] | +0.28 [−0.74, +1.25] | −0.37 [−1.23, +0.53] |
| OptiBench other 403, Qwen3-14B-AWQ | 71.05 | +0.77 [−0.22, +1.82] | +0.81 [−0.11, +1.91] | +1.40 [+0.37, +2.50] | −0.20 [−1.64, +1.23] |
| MAMO 863, Qwen3-14B-AWQ | 78.04 | **+0.62 [+0.15, +1.19]** | −0.20 [−1.18, +0.78] | +0.45 [−0.72, +1.61] | −1.37 [−2.64, −0.17] |

- **LS-P1 refuted** (2 of 4; never worse). **LS-P2 refuted** (0 of 4).
- **Little room on the fresh sets, even with their labels.** The reference (B's planner on half of the target's own labels) beats the
  cascade by −0.26 to +1.40 (significant once), against +4.1 to +11.4 on B's development cells. B's word-problem room belonged to the
  hard development sets (LogiOR, OptMATH), not to the pair: "up to +10" does not generalise.
- **Without a target label, the planner does as well as with half of them.** LS − reference: +0.54, +1.00, −0.63, +0.17; plain transfer
  likewise. Labels from other sets of the same kind were worth about as much as the target's own here.
- **The prior adaptation adds nothing, and hurts where the assumption fails.** LS − transfer within ±0.8 on word problems, and −0.75 to
  −1.02 in 4 of the 8 BFCL cells: non-live and live differ in P(o | c), not only in π. The adapted log-likelihood gains 0.2–0.6 nats
  per observation on the word sets and only 0.1–0.2 on BFCL. The matrix [P(o | c)] had full rank (32) in every cell; 0–5% of target
  observations were never seen in development.
- **Reported cells (not decided):** plain transfer beats the cascade in 8 of 12 and loses in 1 (Qwen3-8B BFCL live, −0.89). Spider from
  BIRD's labels gains in 4 of 4 (+0.69 to +1.10), as much as half of Spider's own labels give (+0.50 to +0.91). Qwen3.5-9B's tool calls
  (the weak-peer room) gain in both directions (+3.66 from non-live to live, +4.25 back; references +4.48 / +3.19). LS gains in 6 of 12.
  Spider's test split was FINAL's confirmatory set and is now used a third time, so none of this is a claim.
- **Pseudo-labels** (T's answer as the label, as C3PO uses its strongest model) lose to the cascade in 9 of 16 cells (−0.4 to −5.2): a
  think's answer is a poor label for when to skip thinking.
- **Post hoc:** "gpt-oss-20b's program first" (P→SB→T→T) is at or above LS on all four fresh word cells (+0.2 to +1.4): the observation
  in this addendum's preamble holds on new sets as a property of this pair. It is a hand-chosen rule and is not adopted.

**Decision (as pre-registered).** LS-P1 refuted: the label-shift planner is not shown to beat the cascade on new word-problem sets, and
the prior adaptation is not part of any method. Two corrections follow. B's "up to +10 on hard word problems" is withdrawn as a general
claim, because two fresh sets show almost no room. And labels from other sets of the same task did about as well as half of the
target's own (plain transfer at or within 0.2 of the reference in 13 of 16 cells, 0.8–1.5 below in three), so "a fitted policy needs
labels *of the target*" is not supported either. Whether plain transfer beats the cascade on a
new benchmark is the next confirmatory question (addendum TR).

## Addendum TR: one policy per task, fitted on labelled benchmarks, on a benchmark never used (written 2026-11-01 04:0x UTC, before any Spider-dev row exists; the items were built from Spider's dev.json and nothing else was read)

**Why.** LS: a planner fitted on other sets' labels matches one fitted on half of the target's own (13 of 16 cells). In reported cells
it beats the hand-set cascade in 8 of 12, including Spider test from BIRD's labels in 4 of 4 (+0.7 to +1.1, about the room Spider's own
labels give). Those cells reuse Spider test. The question is whether a policy fitted on the task's labelled benchmarks beats the
cascade on a benchmark never used. If so, the policy is derived once per task rather than per deployment. SQL's method would then move
from the hand-set cascade to the derived policy at B's information limit, with no label of the new benchmark. Tool calls and word
problems have no fresh set with all five calls stored; Spider dev costs about 12 lanes of 45 minutes.

**Run.** Spider's dev split (1,034 questions on 20 databases, disjoint from Spider test's 40; from the official `spider_data.zip`,
`SQL_SPLIT=spiderdev`, ids sd<i>). SQL-1's arms exactly as FINAL: `FINAL_SPLIT=spiderdev bash poc/slurm/submit_final.sh`, tags
<m>sd, for Qwen3-8B, Qwen3-14B-AWQ, Qwen3.5-9B and gpt-oss-20b, seeds 1–3. Each generator's pre-registered peer comes from the same runs
(q8b←q35, q14a←q35, q35←q8b, oss20←q35). Analysis: `python3 poc/lcm_shift.py --tr`. B's supervised planner is fitted on every labelled
row of BIRD dev, the fresh BIRD questions and Spider test (each generator with its peer), using those sets' mean tokens per call;
nothing from Spider dev enters. It is then executed on Spider dev. A pattern it never saw takes the cascade's outcome (counted).

**Predictions** (paired 95% intervals over questions, seed means, utility = 100 × right − 0.5 × ktokens):
- **TR-P1:** transfer − cascade, utility: lower bound > 0 in ≥ 3 of the 4 generators. Holm-adjusted one-sided p-values over the four
  are reported.
- Reported: accuracy and tokens of both; transfer − SB→T→T; the reference (Spider dev's own labels, cross-fitted: the room with labels);
  LS; unseen patterns; gold queries the container's SQLite rejects (as in FINAL).
- **Power.** On Spider test the gains were +0.7 to +1.1, with half-widths ≈ 0.5 on 1,741 questions. On ≈ 1,000 questions the half-width
  is ≈ 0.7, so a true +0.9 clears 0 with probability ≈ 0.7 per cell, and TR-P1 has ≈ 0.65 power if all four effects are +0.9.

**Decision.**
- **TR-P1 holds:** SQL's method becomes the planner derived from the task's labelled public benchmarks, deployed with no label of the new
  benchmark. PROJECT §2, REPORT and PROPOSAL restate "a fitted policy needs labels" as "labels once per task, from public benchmarks". The
  cascade stays as the planner's readable approximation, and what the planner does differently is reported.
- **TR-P1 refuted:** the cascade stays SQL's method. The Spider-test gains are read as the third use of an already-used set.

Expected (not a rule): TR-P1 holds, 3–4 of 4.

## Addendum TR-C1: the trained quick query on Spider dev (written 2026-11-01 05:1x UTC, before any Spider-dev row of the trained adapter exists)

**Why.** SQL's strongest result is CV-1's trained quick query in the peer cascade (FINAL F5, Spider test: +3.80 over the default).
TR asks whether a policy fitted on the task's labelled benchmarks beats the hand-set cascade on a benchmark never used, but only for
the base generators. If TR-P1 holds, SQL's method would be "trained quick query + fitted policy", and that combination has not been
tested on an untouched set. Spider dev is untouched for the trained adapter too, so one more lane (the adapter's quick query, about 60
tokens per question) gives (1) F5 on a second untouched benchmark and (2) TR with the trained quick query.

**Run.** `cv_eval_lane.sh` with C1's adapter on Spider dev (`CV_EVAL_SPLIT=spiderdev`, tag q8bcvc1sd, seeds 1–3; the `tr_c1` line of
`poc/slurm/submit_final.sh`), graded in the container as every TR row. Cell as F5: N = C1's quick query, SB and T = base Qwen3-8B
(q8bsd), P = Qwen3.5-9B's quick query (q35sd). The planner is fitted on the labelled C1 rows of BIRD dev and Spider test (not the fresh
BIRD-train questions, which are C1's training pool) with those sets' mean tokens per call. Analysis: `python3 poc/lcm_shift.py --tr-c1`
(`--dqs`: the double-quote sensitivity, as FINAL).

**Exploration on an already used set (sets the expectation, decides nothing; `results/lcm_tr_c1_explore.log`).** Fitted on BIRD dev's
C1 rows only and run on Spider test: transfer − cascade +0.35 [−0.15, +0.86]; the reference (Spider test's own labels, cross-fitted)
− cascade +0.81 [+0.17, +1.49]; cascade − SB→T→T +3.80 [+2.83, +4.77]. With the trained quick query the room above the cascade is
small, as on the base generators.

**Predictions** (paired 95% intervals over questions, seed means, utility = 100 × right − 0.5 × ktokens):
- **TR-C1-P1** (F5 on a second untouched benchmark): cascade − SB→T→T, lower bound > 0.
- **TR-C1-P2:** transfer − cascade, lower bound > 0.
- Reported: accuracy and tokens; transfer − SB→T→T; the reference; the double-quote sensitivity.
- **Power.** About 820 gradable questions (215 of 1,034 gold queries fail in the container's SQLite). P1: a true +3.8 with a
  half-width ≈ 1.4 clears 0 with probability > 0.99. P2: a true +0.35 with a half-width ≈ 0.75 clears 0 with probability ≈ 0.2, so
  P2 is expected to fail even if the planner's small gain is real; it can pass only if the gain on Spider dev is ≈ 0.8 or more.

**Decision.**
- **P1 holds:** the trained quick query's gain is confirmed on two untouched benchmarks (Spider test and dev); PROJECT §2, REPORT and
  PROPOSAL cite both. **P1 refuted:** F5 is reported as one benchmark only.
- **P2 holds (with TR-P1):** SQL's method is the trained quick query with the fitted policy. **P2 refuted:** with the trained quick
  query the hand-set cascade stays the method (its room above the cascade is within the noise of an ~800-question set), whatever TR-P1
  decides for the base generators.

Expected (not a rule): P1 holds; P2 refuted.

### Results, addenda TR and TR-C1 (written 2026-11-01 06:3x UTC; `results/lcm_tr.log`, `results/lcm_tr_dqs.log`, `results/lcm_tr_c1.log`, `results/lcm_tr_c1_dqs.log`; GPU jobs 1291449–1291460 and 1291632, analysis CPU jobs 1291940–1291942; no failed request)

**A grading bug found and fixed before these verdicts.** Reading the raw grades: identical result sets were graded right in one seed
and wrong in another (sd1000, "How many singers are there?"). `grade_sql.py` cached the gold rows by the gold query string only, and
Spider repeats a gold string on several databases (`singer` and `concert_singer` both have a `singer` table), so a worker could
compare a query with another database's gold rows. It affects 4 Spider-dev and 7 Spider-test questions and no BIRD question. The cache
is now keyed by database too; those questions were graded again in every Spider tag (`SQL_REGRADE=shared`), and every Spider analysis
was rerun (pre-fix logs kept as `*_prefix`). Every number below is after the fix. FINAL's verdicts are unchanged (its correction is
appended to PREREG_FINAL). LS's reported Spider cells move by ≤ 0.1 (transfer − cascade +1.01 / +0.60 / +0.81 / +0.69), and B on
Spider by ≤ 0.1 (+0.46 to +0.81).

Spider dev: 819 of 1,034 questions graded (the container's SQLite rejects 215 gold queries' double-quoted literals; the sensitivity
grades 1,032).

| generator ← peer | transfer − cascade | transfer vs cascade | reference − cascade | transfer − SB→T→T | sensitivity: transfer − cascade |
|---|---|---|---|---|---|
| Qwen3-8B ← Qwen3.5-9B | +0.20 [−0.63, +1.04] | 74.8% @ 0.98k vs 74.4% @ 0.57k | −0.66 [−1.63, +0.32] | +1.13 [−0.12, +2.46] | −0.10 [−0.89, +0.61] |
| Qwen3-14B-AWQ ← Qwen3.5-9B | +0.02 [−0.82, +0.83] | 76.0% @ 0.91k vs 75.8% @ 0.47k | −0.69 [−1.67, +0.34] | +1.45 [+0.07, +2.94] | −0.15 [−0.91, +0.56] |
| Qwen3.5-9B ← Qwen3-8B | +0.60 [−0.44, +1.67] | 75.6% @ 1.61k vs 74.4% @ 0.44k | −0.64 [−1.40, +0.14] | +1.83 [+0.77, +2.94] | +0.12 [−0.82, +1.02] |
| gpt-oss-20b ← Qwen3.5-9B | +0.20 [−0.49, +0.92] | 74.8% @ 0.30k vs 74.5% @ 0.21k | −0.63 [−1.36, +0.15] | +1.51 [+0.46, +2.52] | +0.28 [−0.34, +0.89] |
| C1 (trained quick query) ← Qwen3.5-9B | +0.99 [+0.23, +1.83] | 77.2% @ 0.91k vs 76.0% @ 0.54k | −0.10 [−1.07, +0.84] | +3.53 [+2.21, +4.99] | +0.69 [+0.05, +1.29] |

- **TR-P1 refuted:** transfer − cascade has a lower bound > 0 in 0 of 4 (Holm-adjusted one-sided p 0.87 / 0.87 / 0.55 / 0.87), and
  none is worse. The fitted policy spends more tokens for at most a point of accuracy (Qwen3.5-9B +1.2 points at 3.7× the tokens).
  Even a policy fitted on half of Spider dev's own labels does not beat the cascade (reference −0.6 to −0.7 in all four).
- **TR-C1-P1 holds:** with CV-1's trained quick query the cascade beats the default, +2.53 [+1.44, +3.69] (76.0% at 0.54k vs 73.8%
  at 1.13k: more accurate and cheaper; sensitivity +2.51 [+1.54, +3.54]). This is F5 on a second untouched benchmark, smaller than on
  Spider test (+3.73).
- **TR-C1-P2 holds:** transfer − cascade +0.99 [+0.23, +1.83], one-sided p 0.006 (Holm over the five TR tests 0.031); sensitivity
  +0.69 [+0.05, +1.29] (p 0.015). What the policy does differently (traced per question-seed, post hoc):
  - The gain comes from the question-seeds where the trained quick query passes and the peer returns other rows (7% of all). There the
    cascade runs the default, which takes the base model's short think when it passes. The policy instead runs one full think and
    keeps the quick query if the think agrees (+0.56 of the +0.99).
  - Where the quick query fails, the policy keeps the peer's query if the think agrees with it (+0.25).
  - Why: on the question-seeds where the quick query passes and the peer disagrees, the base quick query is right 34.1% of the time,
    against 50.2% for the short think and 50.4% for the think, so falling back is right. The trained one is right 46.9%, against
    48.9% / 49.3%: as good as the fallback. Its answer is then worth a vote, and the think breaks the tie between the two quick
    answers instead of replacing them. Same pattern on Spider test (48.5% vs 46.4% / 48.6%; base 26.3%) and BIRD dev (34.7% vs 43.4% /
    43.0%; base 26.9%).
  - On Spider test, fitted on BIRD dev's C1 rows only, the same policy gained +0.24 [−0.27, +0.73] (exploration above), so the
    size of this gain is not settled.

**Decision (as pre-registered).**
- TR-P1 is refuted, so the hand-set cascade stays SQL's method for the base generators; the Spider-test gains of the transferred policy
  (+0.6 to +1.0, LS) were the third use of a used set and do not reappear on Spider dev. "A fitted policy needs labels" stays; "labels
  once per task" is not supported on SQL. With this, three tests agree that on SQL the cascade is at the information limit of its
  calls for base generators: B (BIRD dev, 1 of 8 cells), the Spider-dev reference (0 of 4) and TR (0 of 4).
- TR-C1-P1 holds: the trained quick query's gain is confirmed on two untouched benchmarks (Spider test +3.73, Spider dev +2.53);
  PROJECT §2, REPORT and PROPOSAL cite both.
- TR-C1-P2 holds, but the rule changed the method only "with TR-P1", which is refuted. So the cascade stays the method with the
  trained quick query too. The result is reported as what the derived policy does once the quick query is trained: the think becomes
  the referee between the two quick answers. Whether that fallback should replace SB→T→T for trained quick queries is a question for a
  benchmark not yet used (none is left on the cluster; KaggleDBQA, 272 questions, is too small for a one-point effect).

## Addendum TRT: does training the quick answer make the derived policy pay — tool calls, fitted on BFCL, run on held-out ToolACE (written 2026-11-01 06:4x UTC, before any new SB / T row of these requests exists)

**Why.** TR and TR-C1 split cleanly by whether the quick answer is trained. For untrained generators a policy fitted on public
benchmarks adds nothing over the hand-set cascade (TR 0 of 4; even the target's own labels give no room). With CV-1's trained quick
query it gains (+0.99 [+0.23, +1.83]). The traced mechanism: where the quick answer passes its check and the peer disagrees, an
untrained quick answer is far less accurate than the fallback thinks, so replacing it is right. A trained one is about as accurate
(Spider dev 46.9% vs 48.9% / 49.3%), so it is worth a vote, and the policy lets a full think break the tie. On tool calls (BFCL,
already used, exploration only, `results/tc_trained_explore.log`) the same holds:
- In that stratum, the untrained quick calls are right 53.5% of the time on live against SB 67.0% / T 66.4%, and the trained ones
  65.7% against 66.5% / 66.6%.
- The policy fitted on non-live and run on live gains over the cascade only with the trained quick calls: +0.98 [+0.30, +1.68]
  (reference +1.52), against −0.83 [−1.58, −0.12] untrained.
- Non-live is near its ceiling for both (+0.2).
If this holds on a second task on requests never used for it, the claim changes: training the quick answer moves the best call policy
from "replace on disagreement" (the cascade) to "vote", and a policy fitted once on the task's public benchmarks captures it.

**Set.** The 3,549 held-out ToolACE requests of TC-RL addendum 3 (`$POC_DATA/toolace/tc_ho_ids.txt`; training distribution of the
trained adapter, never trained on). They were used only to compare training rewards by the cascade's value (TCRL-P14..P16), never
for a call policy. Stored: quick calls of Qwen3-8B base (hoq8b), of TC-RL's trained adapter (hoq8btcc1) and of Qwen3.5-9B (hoq35),
seeds 1–4; Qwen3-8B's SB seed 1. **New runs:** Qwen3-8B's SB seeds 2–3 and T seeds 1–3 on all requests (`TC_ITEMS=…/toolace/
tc_train_items.jsonl TC_IDS=…/tc_ho_ids.txt TC_ARMS=think,sb run_tc.py hoq8b <seed>`, TP 2 as the held-out runs, max length 20,480 for
T's 16k cap). Seeds 1–3 of every call; graded with `tc_reward` (check, canonical calls, right) as `analyze_tcho.py`; loader `lcm.load_tcho`.

**Policy.** B's supervised planner fitted on every BFCL row (non-live + live, all labels) of the same call set, with BFCL's mean
tokens per call, nothing from ToolACE; run on the held-out requests (`python3 poc/lcm_shift.py --trt`). Compared with the cascade
(N passes and P makes the same calls → N, else SB→T→T) and SB→T→T.

**Predictions** (paired 95% intervals over requests, seed means, utility = 100 × right − 0.5 × ktokens):
- **TRT-P1 (trained quick calls, C1tc ← Qwen3.5-9B):** transfer − cascade, lower bound > 0.
- **TRT-P2 (base quick calls, Qwen3-8B ← Qwen3.5-9B):** transfer − cascade, lower bound > 0. Expected refuted.
- Reported: accuracy and tokens; the reference (own labels, cross-fitted); the stratum accuracies (N passes, P differs: N vs SB vs
  T), with the mechanism's direction expected: the trained quick calls within 3 points of SB, the base ones more than 5 below.
- **Power.** BFCL live's half-width was ≈ 0.7 on 2,242 requests; on 3,549 ≈ 0.55. A true +1.0 clears 0 with probability ≈ 0.9; a
  true +0.5 with ≈ 0.4.

**Decision.**
- **P1 holds:** with TR-C1-P2 (SQL, Spider dev) this makes two tasks on data never used for the question. The claim: once the quick
  answer is trained, the best call policy is no longer the hand-set cascade, and a policy fitted once on the task's public benchmarks
  captures the change. The method for trained quick answers becomes that policy, with the cascade kept for untrained ones. PROJECT
  §2, REPORT and PROPOSAL change.
- **P1 refuted:** the trained-quick finding stays one cell on SQL; the cascade stays the method everywhere.
- P2 is read only as the untrained control: it holding would mean the split by training is not the mechanism.

Expected (not a rule): P1 holds (+0.5 to +1.5), P2 refuted.

### Results of addendum TRT (written 2026-11-01 08:3x UTC; `results/lcm_trt.log`, all 3,549 requests × seeds 1–3)

| quick calls (N) | transfer − cascade | transfer | cascade | SB→T→T | reference − cascade | stratum: N / SB / T right |
|---|---|---|---|---|---|---|
| trained (C1tc) | **+0.54 [+0.14, +0.96]**, p 0.0036 | 72.7% @ 0.74k | 72.0% @ 0.39k | 70.8% @ 0.48k | +0.16 [−0.26, +0.58] | 41.2% / 44.6% / 42.2% (3,824) |
| base | −0.29 [−0.66, +0.08], p 0.93 | 71.4% @ 0.83k | 71.5% @ 0.39k | 70.8% @ 0.48k | −0.94 [−1.37, −0.52] | 31.0% / 44.0% / 42.2% (3,830) |

- **TRT-P1 holds** (+0.54 [+0.14, +0.96]). The size is about half the BFCL exploration's (+0.98) and below the +1.0 the power was
  computed for; it buys 0.7 points of accuracy at 1.9× the cascade's tokens.
- **TRT-P2 refuted**, as expected (−0.29 [−0.66, +0.08]).
- Mechanism, reported: where N passes and P differs, the base quick calls are 13 points below SB (more than 5, as expected); the
  trained ones are 3.4 below SB (the expectation was within 3) and 1.0 below T. The direction holds; the trained gap is just outside the
  stated band.
- The target's own labels (reference, cross-fitted on half the requests) do not beat the cascade for either (+0.16 / −0.94): the room
  here is about half a point, and the BFCL-fitted policy reaches it.
- Cascade − SB→T→T: +1.25 [+0.80, +1.69] trained, +0.76 [+0.26, +1.26] base: on held-out training-distribution requests the peer
  cascade beats the default for both, as on BFCL.

**Decision (by the rule above).** P1 holds. With TR-C1-P2 (SQL, Spider dev, +0.99 [+0.23, +1.83]) the split by training is now seen
on two tasks on data never used for the question. The method for trained quick answers becomes the policy fitted once on the task's
public labelled benchmarks; the cascade stays the method for untrained ones. Stated with it: the gain is small (+0.5 to +1.0 utility,
0.7–1.2 points of accuracy) and costs 1.7–1.9× the cascade's tokens; on Spider test, fitted on BIRD dev alone, it was +0.24 n.s.
PROJECT §2, REPORT and PROPOSAL change.

## Addendum TL: does the fitted policy need benchmark labels, or do the training split's own held-out labels suffice? (written 2026-11-01 08:4x UTC, before any trained quick query on the fresh BIRD-train questions exists and before any TL cell is computed)

**Why.** TRT made the fitted policy the method for trained quick answers, fitted "once on the task's public labelled benchmarks". That
needs the deployed model's quick, short-think and think calls on a labelled benchmark, and both confirmations (Spider dev, held-out
ToolACE) were fitted on benchmarks near the target. Whoever trains the quick answer already holds labelled questions of the training
split. If the policy fitted on held-out questions of that split carries to the task's benchmarks, the recipe needs no labels beyond the
training set: train the quick answer on part of it, fit the call policy on the rest, deploy anywhere on the task. Jitkrittum et al.
(NeurIPS 2023) name distribution shift between where a post-hoc deferral rule is fitted and where it runs as a case where it fails;
training split → benchmark is exactly that shift (BIRD train → Spider; ToolACE → BFCL), so the outcome is open.

**Sets.**
- Fitting (training split, held out from training): SQL, the 1,338 fresh BIRD-train questions (`$POC_DATA/bird/pa_ids.txt`; none of
  C1's 6,000 training questions, overlap checked 0; TR-C1's text called them "C1's training pool", meaning the split); tool calls,
  the 3,549 held-out ToolACE requests (TRT's set).
- Targets (the task's benchmarks): BIRD dev (1,530), Spider test (2,147), Spider dev (1,034), BFCL (non-live + live, 3,482, one set).
- **New run:** C1's quick query on the fresh questions (`CV_EVAL_SPLIT=train SQL_IDS=…/pa_ids.txt cv_eval_lane.sh c1 q8bcvc1pa
  <C1 adapter> 1 2 3`, graded `SQL_SPLIT=train grade_sql.py q8bcvc1pa <s>`); `cv_eval.py` gains the `SQL_IDS` filter. Every other call
  is stored (base Qwen3-8B q8bpa / SB / T, Qwen3.5-9B q35pa; the targets' rows of TR-C1, FINAL and TRT). No pa question shares its gold
  string with another database, so the grader fix does not touch the stored pa grades.

**Policy.** B's supervised planner fitted on every labelled row of the fitting set (N, P, SB, T of seeds 1–3) with that set's mean
tokens per call, nothing from the target; run on each target (`python3 poc/lcm_shift.py --tl`; `--dqs` for Spider's double-quote
sensitivity). Cell as TR-C1 / TRT: N = the trained quick answer (C1 on SQL, C1tc on tool calls) or the base one, P = Qwen3.5-9B's quick
answer, SB and T = base Qwen3-8B.

**Predictions** (paired 95% intervals over questions, seed means, utility = 100 × right − 0.5 × ktokens; four primary cells: BIRD dev,
Spider test, Spider dev, BFCL):
- **TL-P1 (trained quick answers):** transfer − cascade, lower bound > 0 in at least 2 of the 4 cells and upper bound < 0 in none.
- **TL-P2 (base quick answers):** the same. Expected refuted (TR, TRT-P2): the control for the split by training.
- Reported: accuracy and tokens; the reference (each target's own labels, cross-fitted); the double-quote sensitivity on Spider.
- **Power.** Half-widths about 0.6 (BIRD dev), 0.5 (Spider test), 0.8 (Spider dev), 0.4 (BFCL). At the +0.5 to +1.0 seen when fitted
  on benchmarks, each cell clears 0 with probability about 0.4–0.9, so a true carry-over passes 2 of 4 with probability ≈ 0.7; a policy
  hurt by the shift shows as cells below 0.

**Decision.**
- **P1 holds:** the recipe for trained quick answers needs no labels beyond the training split's: the call policy is fitted on its
  held-out questions and deployed on the task's benchmarks. PROJECT §2, REPORT and PROPOSAL state the recipe that way.
- **P1 refuted:** the fitted policy needs labelled calls from data near the deployment (a public benchmark of the task), stated as a
  cost of the method; with any cell below 0, the shift from the training split is named as the reason, as Jitkrittum et al. predict.

### Results of addendum TL (written 2026-11-01 09:3x UTC; `results/lcm_tl.log`, `results/lcm_tl_dqs.log`; C1's quick query on the 1,338 fresh questions, 3 seeds, all rows)

Fitted only on the training split's held-out questions; transfer (training-split tokens) − cascade, paired 95% intervals; Spider cells
as FINAL's primary grading (questions whose gold runs in the container: 1,741 / 819), the double-quote sensitivity in brackets.

| target | trained quick answer | base quick answer | reference − cascade (target's own labels), trained / base |
|---|---|---|---|
| BIRD dev (1,530) | −0.43 [−1.28, +0.31] (61.3% @ 2.27k vs 61.3% @ 1.36k) | −0.04 [−0.86, +0.79] | −0.34 / −0.55 |
| Spider test (1,741; dqs 2,147) | +0.39 [−0.04, +0.82] (dqs +0.31) | **+1.01 [+0.47, +1.56]** (dqs +0.88) | +0.70 / +0.81 |
| Spider dev (819; dqs 1,032) | +0.39 [−0.34, +1.20] (dqs +0.16) | +0.29 [−0.60, +1.23] (dqs −0.02) | −0.10 / −0.66 |
| BFCL (3,482) | **+1.04 [+0.60, +1.49]** (86.4% @ 0.43k vs 85.2% @ 0.27k) | −0.11 [−0.43, +0.21] | +1.01 / +0.23 |

- **TL-P1 refuted** (1 of 4 above 0, none below). **TL-P2 refuted** (1 of 4), as expected.
- By task, reported: on tool calls the training split's labels reach the room the target's own labels show (BFCL +1.04 vs reference
  +1.01), and the split by training holds a third time (base −0.11). On SQL no cell shows the trained quick answer's gain: BIRD dev has
  no room even for its own labels (−0.34), and where there is room (Spider test, +0.70 / +0.81) it is there for the base quick answer
  as much as for the trained one (the base cell is the one significant SQL cell, as LS's +0.6 to +1.0 on that set).
- The fitted model's diagnostics show the shift: on the fresh BIRD-train questions the trained quick query is right 59% of the time,
  on BIRD dev 40–43%; the policy fitted where it is reliable over-spends on BIRD dev (2.27k vs 1.36k tokens for the same accuracy).

**Decision (by the rule above).** P1 refuted: the fitted policy cannot be fitted on the training split alone in general; it needs
labelled calls from data near the deployment, stated as a cost of the method. No cell is below 0, so the shift is not named as a harm.
Stated with it, from all fits so far: on tool calls the training split suffices (BFCL +1.04 here, held-out ToolACE +0.54 from BFCL in
TRT); on SQL the trained quick answer's gain from a fitted policy is one significant cell in five fit / target pairs (Spider dev +0.99
in TR-C1; +0.24 on Spider test from BIRD dev; −0.43 / +0.39 / +0.39 here), and SQL's small room above the cascade is a
property of the target set, not of training. The method statement is therefore narrowed: for trained quick answers on tool calls, the
policy fitted on the training split's held-out labels; on SQL, the cascade, with a fitted policy an option only where labelled calls
near the deployment exist.

## Addendum TL4: the tool-call recipe from one training set, with Qwen3-4B as the generator (written 2026-11-01 09:3x UTC, before any Qwen3-4B row on the held-out ToolACE requests except C1tc-4B's stored quick calls, and before any TL4 cell is computed)

**Why.** After TRT and TL the tool-call method is: train the quick calls with plain RL on ToolACE, check them with Qwen3.5-9B's quick
calls, and combine the calls with a policy fitted on held-out training requests — no labels beyond the training data. Every piece of
that rests on one generator (Qwen3-8B). TC-RL addendum 1 trained Qwen3-4B with the identical recipe (C1tc-4B), so the same test on a
second generator costs only Qwen3-4B's base calls on the held-out requests. If it fails there, the method statement is narrowed to
Qwen3-8B.

**Run.** Base Qwen3-4B's quick, short-think and think calls on the 3,549 held-out ToolACE requests, seeds 1–3 (`TC_ITEMS=…/toolace/
tc_train_items.jsonl TC_IDS=…/tc_ho_ids.txt run_tc.py hoq4b <seed>`, one GPU, max length 20,480, as TRT). Stored: C1tc-4B's quick
calls there (hoq4btcc1), Qwen3.5-9B's (hoq35), and on BFCL q4b (quick, SB, T), q4btcc1 (quick), q35.

**Cells.** N = C1tc-4B's quick calls (trained) or base Qwen3-4B's (base); P = Qwen3.5-9B's quick calls; SB, T = base Qwen3-4B.
Primary: the policy fitted on the held-out ToolACE requests (all labels, their mean tokens per call) and run on BFCL (non-live + live,
3,482). Reported: the reverse (fitted on BFCL, run on the held-out requests, as TRT), the references, the stratum accuracies.
Analysis `python3 poc/lcm_shift.py --tl4`.

**Predictions** (paired 95% intervals over requests, seed means, utility = 100 × right − 0.5 × ktokens):
- **TL4-P1 (trained):** transfer − cascade on BFCL, lower bound > 0.
- **TL4-P2 (base):** the same; expected refuted (the control).
- Mechanism, reported: where N passes and P differs, the trained quick calls within 3 points of SB, the base ones more than 5 below.
- Power: BFCL's half-width ≈ 0.45; at Qwen3-8B's +1.04 the test passes with probability ≈ 0.99, at +0.5 ≈ 0.5.

**Decision.**
- **P1 holds:** the tool-call recipe from one training set holds for two generators; PROJECT and REPORT say so.
- **P1 refuted:** the fitted call policy is stated for Qwen3-8B only; for Qwen3-4B the cascade stays, and the stratum accuracies are
  read to say whether the mechanism (a trained quick answer as accurate as the thinks where the peer disagrees) was absent or present
  without a gain.

## Addendum RV: telling apart two disagreeing passing answers by the channel score log p(question | answer) (written 2026-11-01 10:4x UTC, before any reviewer or coder score exists; `lcm_shift.py --rv-build` only listed the candidate texts, and `nlp_data/scratch/rv_bound.py` → `results/rv_bound.txt` used stored labels and no score)

**Why.** The exploratory oracle room (FINDINGS, 11-01 09:3x) puts 8–11 points above the cascade, mostly where N and P both pass and
differ. Where the cascade falls back after a passing quick answer, N, P and the fallback d (SB if it passes, else T, else the retry T),
all already paid for, give ≥ 2 distinct passing answers on 16–32% of question-seeds. Always choosing a right one there would add +5.0
(BIRD dev), +5.5 (Spider test), +5.7 (Spider dev), +4.6 / +6.7 (BFCL live, base / trained quick answer) at no output-token cost. Every
label-free signal tried so far gated one answer across questions (own confidence, EXT: AUROC 0.56–0.72; a 9B judge, J: 0.61–0.72) or
was trained (VER: no transfer). None contrasted two answers to the same question.

**Theory (derived before any score; `results/rv_bound.txt`).**
1. Within-question contrast. A score s(c, q) = f(q) + g(c, q): a gate is judged across questions, where the question term f
   (difficulty, length) dominates; choosing between two answers to the same question uses g only. A signal weak as a gate can still
   choose.
2. Why the channel direction. For one model, log p(c | q) = log p(q | c) + log p(c) − log p(q). Between two answers to one question the
   last term cancels, so the direct (coder) score = the channel (reviewer) score + the answer's typicality log p(c). EXT's raw reading:
   confidently wrong passing queries are typical forms with a column or filter mismatch, so wrong answers win on typicality. The channel
   score drops that term and asks whether the answer accounts for every part of the question (a missing filter makes the question's
   words less likely). This is the noisy-channel argument (Min et al., ACL 2022, for prompting) and Coder-Reviewer reranking (Zhang et
   al., ICML 2023: p(x | y) p(y | x) beats p(y | x) by up to 17 points on six code sets, among samples of one model). Related checks by
   back-translation (round-trip critique, VLDB 2025; GBV-SQL, 2509.12612) generate the question and ask a judge, which costs output
   tokens; none scores p(question | answer) between two models' answers inside a cascade, and none is on tool calls.
3. How good it must be. The fallback d is right on 62–89% of the two-answer mixed sets (it often agrees with N or P: two votes) and
   27–78% of the three-answer ones, so a choice must beat a strong prior. With an equal-variance Gaussian score of within-question
   AUROC A and, as a best case, the structural prior (which calls returned which answer) known per cell, the Bayes selector gains
   (points over all question-seeds) at A = 0.6 / 0.7 / 0.8: BIRD dev +0.1 / +0.7 / +1.8; Spider test +1.2 / +1.9 / +3.0; Spider dev
   +0.3 / +1.1 / +2.4; BFCL live +0.1 / +0.6 / +1.6 (base), +1.1 / +2.0 / +3.4 (trained); BFCL non-live < +0.6 at A ≤ 0.8. The
   parameter-free rule R1 (most votes among N, P, d; ties by the score) gains less: at A = 0.7, BIRD dev −0.03 / +0.3 (base / trained),
   Spider test +0.5 / +0.8, Spider dev +0.5 / +0.5, BFCL live −0.3 / +1.6; it needs A ≈ 0.8 for ≥ +0.9 on BIRD dev and BFCL live base.

**Scores (no new answers).** Qwen3-8B (the resident generator, no adapter), raw text without the chat template, Coder-Reviewer's
inverted prompt (`poc/score_conf.py rv`):
- rev (channel): SQL: the schema (with BIRD's external knowledge), "-- SQLite query:" and the candidate, "-- The question this query
  answers:", then the question; the summed log-prob of the question's tokens (the same tokens for every candidate of a question). Tool
  calls: the functions as JSON, "# Function calls made" and the graded calls one per line as name(arg=value, ...), "# The user request
  these calls answer:", then the request.
- cod (direct): the original order (schema or functions, the question or request, then the candidate); the mean log-prob of the
  candidate's tokens.
- An answer (agreement key: SQL's result rows, the tool calls) returned by several calls with different SQL texts gets the mean over
  its texts.
- 24,704 requests, one RTX 3090, max length 20,480.

**Cells.** 4 targets (BIRD dev, Spider test, Spider dev, BFCL = non-live + live) × N base (Qwen3-8B's quick answer) or trained (C1 /
C1tc); P = Qwen3.5-9B's quick answer; SB, T = Qwen3-8B. The question-seeds where N passed, P did not return N's answer, and N, P, d
give ≥ 2 distinct passing answers: 1,437 / 1,287, 936 / 807, 506 / 442, 2,833 / 2,892 (base / trained).

**Measures** (`python3 poc/lcm_shift.py --rv`).
- Within-question AUROC on the mixed sets (≥ 1 right and ≥ 1 wrong distinct answer): per question-seed the share of (right, wrong)
  pairs the score orders correctly (ties ½), averaged per question, CI by resampling questions; rev, cod and rev − cod.
- R1 − cascade (the primary policy): most votes among N, P, d, ties by rev; elsewhere the cascade. The cascade already makes all
  three calls on these question-seeds, so the output tokens are identical and the utility difference is 100 × the accuracy
  difference. The reviewer's prefill tokens are reported per question-seed.
- Reported: votes with ties by cod; rev alone; the cross-fitted Bayes selector (logit of the structural prior + β × standardized rev,
  fitted on one crc32 half and applied to the other) next to the Gaussian bound at the measured AUROC.

**Predictions** (paired 95% intervals over questions):
- **RV-P1 (channel vs direct):** rev − cod within-question AUROC, lower bound > 0 in ≥ 6 of 8 cells.
- **RV-P2b / RV-P2t (decision; base / trained):** R1 − cascade lower bound > 0 in ≥ 2 of 4 targets, upper bound < 0 in none.
- **RV-P3 (theory):** the cross-fitted Bayes gain lies within 0.7 points of the Gaussian bound at the measured AUROC in ≥ 6 of 8 cells.
- Expected from the gates measured so far (0.56–0.72 across questions): rev's within-question AUROC 0.60–0.75. With the bound, P2t
  holds only if A ≥ 0.7 on Spider and BFCL; P2b needs A ≈ 0.8 and is expected to be refuted.
- Power: R1 changes the answer only on the mixed sets (9–21% of question-seeds); half-widths ≈ 0.6–1.0 points per target.

**Decision.**
- P2 holds for an N type → R1 becomes the cascade's last step for that type (one prefill per extra candidate, no extra output);
  PROJECT, REPORT and PROPOSAL updated.
- P2 refuted and rev's AUROC ≥ 0.75 on ≥ 2 targets → the Bayes selector with priors fitted on the training split (as TL) is
  pre-registered next.
- rev's AUROC < 0.7 on every target → the selection direction is closed for label-free scoring by a model of this size: by the bound,
  the room above the cascade needs a within-question AUROC of 0.75–0.8 to give ≥ +1, and none of four signal families (own
  confidence, a judge, a transferred verifier, the channel score) reaches it; REPORT states the bound and the measured AUROCs.
- Otherwise (0.7–0.75, P2 refuted): stated as measured, no follow-up.

## Results of addendum TL4 (written 2026-11-01 11:4x UTC; `results/lcm_tl4.log`, reading `results/tl4_mech.txt`)

| N (Qwen3-4B) | BFCL, fitted on held-out ToolACE: transfer − cascade | accuracy @ tokens (cascade) | reverse: ToolACE held-out, fitted on BFCL | cascade − SB→T→T (BFCL) | stratum N passes, P differs: N / SB / T |
|---|---|---|---|---|---|
| trained (C1tc-4B) | **+0.81 [+0.39, +1.26]** (p 0.0001) | 87.3% @ 0.43k (86.4% @ 0.26k) | +0.50 [+0.18, +0.81] | +0.94 | 68.6 / 74.3 / 74.5% |
| base | **+1.18 [+0.68, +1.70]** (p < 0.0001) | 86.6% @ 0.66k (85.2% @ 0.27k) | +0.83 [+0.34, +1.29] | −0.22 | 52.2 / 75.2 / 75.6% |

- **TL4-P1 holds.** **TL4-P2, the control, also holds**, against the expectation. The mechanism prediction (trained within 3 points of
  SB) is refuted too: 5.7 below.
- Reading (exploratory, `nlp_data/scratch/tl4_mech.py`: the fitted policy against the cascade by stratum of the first two calls, in
  utility points over all BFCL question-seeds):
  - trained 4B: the gain is the vote where N and P differ (+0.51) and where P fails (+0.17), as for trained Qwen3-8B (+0.47, +0.52).
  - base 4B: the largest part is where N and P **agree** (+0.61). The fitted policy does not accept an agreement; it adds a think
    (P-N-T in 91%), lifting those question-seeds from 93.2% to 94.4% at +0.33k. Smaller parts: the vote where they differ (+0.32), N
    fails (+0.26).
  - base Qwen3-8B: no stratum gains (−0.15 to +0.09); its agreements are trusted as the cascade does (P-N 100%).
- So the gain does not come from training as such. It comes from wherever the hand-set cascade is wrong for that generator, which a
  policy fitted on the training split's labels finds: a trained quick answer is worth a vote (both generators), and an untrained 4B
  quick answer that agrees with the peer is still wrong often enough to be checked by a think. The second is the shared-error case
  (Kim et al., ICML 2025, "Correlated Errors in Large Language Models": models agree on the same wrong answer in most cases where both
  err). With Qwen3-4B as the answering model, the cascade does not even beat SB→T→T (−0.22).

**Decision (by the rule above).** P1 holds: the tool-call recipe from one training set (train the quick calls, check with the peer,
combine the calls with the policy fitted on held-out training requests) holds for two generators; PROJECT and REPORT say so. The
control's failure widens the statement: on tool calls the fitted policy replaces the cascade for trained and untrained quick answers.
Over the 8 fit / target pairs on tool calls (2 generators × trained / base × 2 directions) it is better in 6 and never significantly
worse (untrained Qwen3-8B: −0.11 BFCL, −0.29 held-out ToolACE). The "trained vs untrained" split stated after TRT / TL is a
Qwen3-8B fact, not the rule.

## Addendum RV2: the two resident models' channel scores together (written 2026-11-01 11:4x UTC, before any score of RV or RV2 has been read; the analysis code was run only on random scores)

**Why.** By RV's bound the room above the cascade needs a within-question AUROC of 0.75–0.8. The project's central measurement is that
another family's errors differ from the generator's own (a second sample of the same Qwen3 model repeats 79–90% of its wrong answers on
SQL and tool calls, another Qwen generation 33–62%). If two channel scores' errors are independent given which answer is right, their
standardized sum is sharper: with d'_k = √2 Φ⁻¹(A_k) and within-class correlation ρ, d'_sum = (d'_1 + d'_2) / √(2 + 2ρ) and
AUROC_sum = Φ(d'_sum / √2). Two scores of AUROC 0.70 give 0.77 at ρ = 0 and 0.73 at ρ = 0.5. Both models are already resident (the
generator and the peer), so the cost is one more prefill per candidate.

**Scores.** Qwen3.5-9B's rev on RV's requests (`RV_KINDS=rev RV_SUFFIX=_q35 score_conf.py rv`, one RTX 3090, `--language-model-only`,
max length 20,480). Per model z = (rev − the question's mean over its candidates) / the pooled within-question SD of the cell (no
label); sum = z(Qwen3-8B) + z(Qwen3.5-9B). Analysis: the same `lcm_shift.py --rv` (RV2 lines).

**Predictions** (same cells, intervals and rules as RV):
- **RV2-P1:** sum − Qwen3-8B rev, within-question AUROC lower bound > 0 in ≥ 6 of 8 cells.
- **RV2-P2b / RV2-P2t:** R1 with the sum (votes, ties by the sum) − cascade, lower bound > 0 in ≥ 2 of 4 targets, upper bound < 0 in
  none.
- **RV2-P3 (theory):** the sum's AUROC lies within 0.03 of the prediction from the two measured AUROCs and their within-class
  correlation in ≥ 6 of 8 cells.
- Expected: ρ 0.3–0.6 (two Qwen generations share pretraining data), so +0.01 to +0.04 AUROC over the better single score; P1 hinges
  on ρ.

**Decision.** RV2-P2 holds for an N type → R1 with the sum is the cascade's last step for that type (two prefills per extra candidate).
Otherwise RV's decision rule applies with the larger of rev's and the sum's AUROC.

## Results of addendum RV (written 2026-11-01 13:1x UTC; `results/lcm_rv.log`, all 24,664 requests scored, none failed; raw cases `nlp_data/scratch/rv_raw.py`)

| cell (base / trained N) | rev AUROC | cod AUROC | rev − cod | R1 − cascade | Bayes, cross-fitted | bound at rev's AUROC |
|---|---|---|---|---|---|---|
| BIRD dev, base | 0.510 [0.470, 0.551] | 0.510 | −0.001 [−0.061, +0.062] | −1.18 [−1.83, −0.52] | +0.00 [−0.13, +0.13] | +0.04 |
| BIRD dev, trained | 0.502 [0.459, 0.547] | 0.568 | −0.066 [−0.132, −0.000] | −0.70 [−1.35, −0.09] | −0.09 [−0.31, +0.11] | +0.14 |
| Spider test, base | 0.632 [0.585, 0.677] | 0.419 | +0.213 [+0.144, +0.281] | +0.33 [−0.08, +0.71] | +0.90 [+0.08, +1.72] | +1.39 |
| Spider test, trained | 0.591 [0.538, 0.641] | 0.497 | +0.093 [+0.019, +0.166] | +0.52 [+0.17, +0.88] | +1.07 [+0.38, +1.78] | +0.96 |
| Spider dev, base | 0.682 [0.620, 0.742] | 0.480 | +0.202 [+0.104, +0.300] | +0.20 [−0.45, +0.94] | +0.12 [−0.49, +0.77] | +1.02 |
| Spider dev, trained | 0.590 [0.520, 0.655] | 0.553 | +0.037 [−0.067, +0.135] | +0.45 [−0.16, +1.14] | +0.49 [−0.53, +1.59] | +0.65 |
| BFCL, base | 0.475 [0.442, 0.506] | 0.320 | +0.155 [+0.117, +0.194] | −2.09 [−2.63, −1.59] | −0.01 [−0.07, +0.03] | +0.08 |
| BFCL, trained | 0.487 [0.456, 0.518] | 0.363 | +0.124 [+0.089, +0.161] | −0.43 [−0.85, −0.02] | −0.21 [−0.62, +0.21] | +0.32 |

- **RV-P1 refuted** (rev − cod lower bound > 0 in 5 of 8: all of Spider test and BFCL, Spider dev base). **RV-P2b refuted** (0 above,
  2 below), **RV-P2t refuted** (1 above, 2 below). **RV-P3 holds** (7 of 8 within 0.7; Spider dev base 0.90 off): the Gaussian bound
  predicts what a selector at a measured within-question AUROC gains. No cell reaches rev AUROC 0.75 (highest 0.682); rev is below
  0.7 on every target.
- **Raw cases.** BFCL: 1,138 of the 2,163 (right, wrong) pairs are a right abstention (rendered as the one token `none`) against a
  wrong call. rev ranks the abstention first in 33% of them, cod in none (−6 to −15 nats per token): a wrong call that copies the
  request's values (`mult(number1=25, number2=7)` on an irrelevance request) explains the request better than no call. Call against
  call: rev 0.55, cod 0.58. BIRD dev: the wrong passing query answers the same question in words and differs by a convention the
  question does not fix — extra output columns (`c.name, c.location, c.country` for a circuit's name), `OR` without parentheses
  before an `AND`, the date taken from another table (`yearmonth` instead of `transactions_1k`). Reconstructing the question cannot
  see these; on Spider, whose questions name their outputs more literally, rev reaches 0.59–0.68.
- **Decision:** deferred to RV2 by its rule ("RV's decision rule applies with the larger of rev's and the sum's AUROC").

## Addendum SEL: a verifier trained for the within-question contrast, at the SQL cascade's fallback (written 2026-11-01 13:1x UTC, before any candidate of the training pool exists, before any training step, and before RV2's scores are complete)

**Why.** RV: label-free scoring by a model of the generator's size does not separate disagreeing passing answers (rev 0.48–0.68),
and RV-P3 confirmed that the bound predicts a selector's gain from its within-question AUROC (7 of 8 within 0.7). By the bound the
room (+5.0 BIRD dev, +5.5 Spider test, +5.7 Spider dev) needs AUROC ≈ 0.75–0.8 for +1.2 to +3. The raw cases say what is missing: on
BIRD the wrong passing query differs by conventions (output columns, precedence, which table holds a date) that a question's
likelihood cannot see but that labels can teach. The project's rule is labels only in training (C1).
Prior trained checks here failed for other reasons: VER (word problems) was trained as a gate across questions and did not transfer
across benchmarks (train-dev AUC 0.987, held-out 0.728); CV-1's in-model gate was trained on the cascade's reward and learned to
defer. Neither was trained for the within-question contrast, which is the quantity the bound needs (RV theory 1: a score
f(q) + g(c, q) chooses with g only).
Related: GradeSQL (arXiv 2606.30851; Qwen2.5-7B + LoRA yes / no outcome reward model on ~30k balanced BIRD-train candidates, N = 32
samples of OmniSQL-7B: BIRD dev +1.95 and Spider test +2.00 over majority voting); LEVER (2302.08468, a verifier with execution
results); CHASE-SQL (2410.01943, a fine-tuned pairwise selector); ToolRM (2509.11963, Bradley–Terry outcome reward models for tool
calls; Qwen3-8B best-of-32 on BFCL +2.5 over greedy but below majority voting). None places the verifier only where a cheap
agreement check failed, prices it in tokens, or predicts its gain from its AUROC before the test.

**Training pool** (labels of BIRD train only). Questions: CV-1's 6,000 training questions minus those on 16 held-out databases (the
first databases in crc32 order until they hold ≥ 25% of the 1,338 fresh questions): 4,431 questions on 50 databases
(`bird/sel_train_ids.txt`). Candidates: Qwen3-8B quick query × seeds 1–4 and SB × seed 1 (tag q8bpool), Qwen3.5-9B quick query ×
seeds 1–4 (stored: tag tsq35, the SQL cascade-reward inputs of 10-30), the stored Qwen3-8B thinks (q8btrain seeds 1, 2); run (10 s, as CV-1), right = the result equals the gold
result. Used: questions with ≥ 1 right and ≥ 1 wrong distinct passing result; per result one query (drawn per epoch), at most 8
results per question.

**Verifier.** Qwen3-8B + LoRA (r 16, CV-1's `Policy`). Context = the question's prompt, the query as the assistant's answer (the
extracted SQL in a ```sql block), then CV-1's turn 2 (row count, columns, first 5 rows; "Does this result answer the question? Reply
ACCEPT or DEFER."). Score s = logit(ACCEPT) − logit(DE) of the next token. Loss per question: the mean over its (right, wrong) result
pairs of log(1 + exp(s_wrong − s_right)), the smooth surrogate of the within-question AUROC (Bradley–Terry); questions weigh equally.
Batch 16 questions, lr 5e-5, 2 epochs, adapters every 25 steps. **Checkpoint choice (labels of training data only):** the highest
within-question AUROC on the cascade's mixed fallback sets of the 343 fresh questions on the 16 held-out databases
(`bird/sel_val_ids.txt`; N base and trained pooled). These databases are unseen in training, as BIRD dev's and Spider's are.

**Selector.** On each question-seed where N passed, P did not match and N, P, d give ≥ 2 distinct passing answers (RV's cells):
argmax over the candidates of logit π(calls | set structure) + β z, z = (s − the question's mean) / the pooled within-question SD of
the fitting cell; π and β fitted on the fresh questions (π on all 1,338, β by likelihood on the 343 held-out-database questions) of the
same N type, as TL fits the call policy on the training split. Elsewhere the cascade. Output tokens unchanged (all candidates are
already paid for); the verifier's prefill tokens per question-seed reported.

**Cells.** BIRD dev, Spider test, Spider dev × N base (Qwen3-8B) or trained (C1); P = Qwen3.5-9B; SB, T = Qwen3-8B (RV's SQL cells).

**Predictions** (paired 95% intervals over questions):
- **SEL-P1 (labels teach what reconstruction misses):** verifier AUROC − rev AUROC on BIRD dev, lower bound > 0 for both N types.
- **SEL-P2b / SEL-P2t (decision; base / trained):** the fresh-fitted selector − cascade, lower bound > 0 in ≥ 2 of 3 targets, upper
  bound < 0 in none.
- **SEL-P3 (theory):** the cross-fitted Bayes gain (RV's, fitted on one half of the target) lies within 0.7 of the bound at the
  verifier's measured AUROC in ≥ 4 of 6 cells.
- **SEL-P4 (honest validation):** BIRD dev's AUROC lies within 0.05 of the held-out-database fresh AUROC for both N types.
- Expected: AUROC 0.68–0.78 on BIRD dev (unseen databases, the benchmark of the training data), 0.62–0.72 on Spider (no Spider
  training data, unlike GradeSQL); bound gains +0.6 to +1.7 on BIRD dev, +1.0 to +2.3 on Spider. P2 is uncertain on Spider, where
  the fresh BIRD prior may not fit (TL: SQL refits held in 1 of 5).

**Decision.**
- SEL-P2 holds for an N type → the trained verifier's selection becomes the SQL cascade's last step for that type (one prefill per
  candidate, schema shared, no extra output); PROJECT, REPORT and PROPOSAL updated; the same recipe on tool calls (ToolACE pool,
  BFCL target) is pre-registered next.
- SEL-P2 refuted but the cross-fitted Bayes lower bound > 0 on ≥ 2 targets → the verifier separates but the training-split prior does
  not transfer; stated, and the prior's transfer is the next question (no new training).
- SEL-P2 refuted and BIRD dev AUROC < 0.7 → a verifier trained on 50 BIRD-train databases does not reach what the bound needs at
  the cascade's two or three candidates; selection at the fallback is closed at this model size on SQL, and REPORT states the
  measured AUROCs with GradeSQL's contrast (its gain comes from 32 samples per question, not from three).

## Results of addendum RV2, and RV's decision (written 2026-11-01 14:2x UTC; `results/lcm_rv2.log`, all 12,346 Qwen3.5-9B requests scored after a resubmission, job 1293926; the first job 1293239 ran out of memory after 6 smoke requests, which are kept)

| cell (base / trained N) | Qwen3.5-9B rev AUROC | sum AUROC | sum − Qwen3-8B rev | within-class ρ | predicted sum | R1 with the sum − cascade |
|---|---|---|---|---|---|---|
| BIRD dev, base | 0.565 [0.526, 0.605] | 0.554 | +0.044 [+0.016, +0.074] | 0.82 | 0.539 | −1.05 [−1.70, −0.44] |
| BIRD dev, trained | 0.539 [0.497, 0.582] | 0.522 | +0.020 [−0.008, +0.050] | 0.81 | 0.522 | −0.76 [−1.42, −0.15] |
| Spider test, base | 0.633 [0.586, 0.678] | 0.639 | +0.007 [−0.024, +0.039] | 0.80 | 0.640 | +0.52 [+0.13, +0.90] |
| Spider test, trained | 0.590 [0.541, 0.636] | 0.607 | +0.016 [−0.016, +0.048] | 0.81 | 0.595 | +0.65 [+0.33, +1.03] |
| Spider dev, base | 0.699 [0.638, 0.756] | 0.704 | +0.022 [−0.020, +0.065] | 0.74 | 0.703 | +0.33 [−0.33, +1.06] |
| Spider dev, trained | 0.647 [0.584, 0.710] | 0.596 | +0.006 [−0.040, +0.052] | 0.77 | 0.626 | +0.49 [−0.16, +1.22] |
| BFCL, base | 0.379 [0.348, 0.409] | 0.457 | −0.018 [−0.036, +0.001] | 0.74 | 0.421 | −2.19 [−2.75, −1.68] |
| BFCL, trained | 0.387 [0.357, 0.417] | 0.466 | −0.021 [−0.039, −0.002] | 0.77 | 0.433 | −0.44 [−0.85, −0.04] |

- **RV2-P1 refuted** (1 of 8). **RV2-P2b / RV2-P2t refuted** (1 above, 2 below each: Spider test gains, BIRD dev and BFCL lose).
  **RV2-P3 refuted** (5 of 8 within 0.03; the misses are BFCL, where the scores are not Gaussian — a right abstention against a wrong
  call is a separate cluster — and Spider dev trained, 0.030).
- **The premise failed, not the formula:** the within-class correlation of the two models' channel scores is 0.74–0.82, not the
  expected 0.3–0.6. The two generations share far less of their answers' errors (another Qwen generation repeats 33–62% of the
  generator's wrong answers) than of their scores' errors: how well a candidate's text predicts the question is a property of the
  text that any language model of this size reads alike. At ρ ≈ 0.8 a second score adds at most ~0.02 AUROC, as measured.
- **RV's decision, by RV2's rule (the larger of rev's and the sum's AUROC):** the largest is 0.704 (Spider dev, base, the sum), so
  not every target is below 0.7, and with P2 refuted the branch is "stated as measured, no follow-up". Label-free selection at the
  fallback is not pursued further: the measured AUROCs (0.46–0.70) sit where the validated bound gives +0.0 to +1.0 on Spider and
  nothing on BIRD and BFCL. Addendum SEL (labels in training only) was pre-registered on the raw-case mechanism, not as this branch's
  follow-up.

## Addendum SEL-TC: the same verifier on tool calls (written 2026-11-01 14:5x UTC, before any SEL-TC training step or score; the Qwen3-8B quick-call pool on the ToolACE training requests is being generated)

**Why.** RV on BFCL: half of the (right, wrong) fallback pairs are a right abstention against a wrong call that copies the
request's values, and both label-free scores prefer the call (AUROC 0.48–0.49). Whether to call at all is what TC-RL's training
taught (live irrelevance +18.5), so labels can teach a verifier the same. ToolRM (2509.11963) trains Bradley–Terry outcome reward
models on tool calls (with irrelevance data): 82% pairwise accuracy on BFCL-derived pairs for its smallest model; in its best-of-32
on BFCL with Qwen3-8B the reward model gains +2.5 over greedy but stays below majority voting. Here it is tested where the cascade's
cheap agreement failed, at no extra output tokens, against the bound. Run in parallel with SEL (SQL), independent of its outcome.

**Training pool** (ToolACE training labels only). TC-RL's 6,000 training requests (`toolace/tc_train_ids.txt`); candidates: Qwen3-8B
quick calls × seeds 1–4 (tag taq8b, new) and its short think × seed 1 (taq8b, stored from TC-RL addendum 2), Qwen3.5-9B quick calls
× seeds 1–4 (taq35, stored); passing = `tc_reward.check`, answers keyed by `tc_reward.canon`, right = `tc_reward.right` (agrees with
BFCL's checker on 99.8%). Requests with a right and a wrong passing answer; per answer one text (drawn per epoch), ≤ 8 per request.

**Verifier.** As SEL (Qwen3-8B + LoRA r 16, `tc_train.py --orm`): context = BFCL's system prompt with the functions and the request,
the candidate's text as the answer, then "Are these function calls (or no call) the right response to the request? Reply ACCEPT or
DEFER."; s = logit(ACCEPT) − logit(DE); per-request mean over (right, wrong) pairs of log(1 + exp(s_w − s_r)); batch 16, lr 5e-5,
2 epochs, adapters every 25 steps. **Checkpoint:** the highest within-question AUROC on the cascade's mixed fallback sets of the 3,549
held-out ToolACE requests (TRT's set; N base and trained pooled).

**Selector.** As SEL: logit π(calls | set structure) + β z, π and β fitted on the held-out ToolACE fallback sets of the same N type
(TL's fitting set); elsewhere the cascade. **Cells:** BFCL (non-live + live, 3,482 requests) × N base (Qwen3-8B) or trained (C1tc).

**Predictions** (paired 95% intervals over requests):
- **SEL-TC-P1:** verifier AUROC − rev AUROC, lower bound > 0 for both N types.
- **SEL-TC-P2b / P2t (decision):** the fitted selector − cascade, lower bound > 0 (each N type on its own).
- **SEL-TC-P3 (theory):** the cross-fitted Bayes gain within 0.7 of the bound at the verifier's AUROC, both N types.
- **SEL-TC-P4:** BFCL's AUROC within 0.05 of the held-out ToolACE AUROC, both N types.
- Expected: AUROC 0.70–0.85 on held-out ToolACE, 0.65–0.80 on BFCL (other APIs and request styles); gains +0.3 to +2 (the room on
  BFCL is mostly live: +4.6 / +6.7).

**Decision.**
- SEL-TC-P2 holds for an N type and its point gain exceeds the fitted call policy's on BFCL for that type (TL: trained +1.04, base
  −0.11) → the verifier is added to the tool-call method; how it combines with the call policy (the verifier's score as one more
  observation of the planner) is pre-registered next. P2 holds but below TL → reported as an alternative, the method unchanged.
- P2 refuted with AUROC ≥ 0.75 → the prior from ToolACE does not transfer; stated (as SEL's second branch).
- P2 refuted with AUROC < 0.75 → a verifier trained on ToolACE does not reach the bound on BFCL at this size; stated with ToolRM's
  contrast.

## Results of addendum SEL (written 2026-11-01 17:5x UTC; `results/lcm_sel_val.log`, `results/lcm_sel.log`; training job 1294110, 166 steps on the 1,320 of 4,431 pool questions with a right and a wrong passing result, 3,397 results; scoring job 1294111, every candidate scored, none failed; raw cases `nlp_data/scratch/sel_raw.py`, `sel_cols.py`, the whole pipeline `sel_full.py`, extra samples `selk_cov.py`)

**Checkpoint** (held-out databases, pooled within-question AUROC over 98 questions): s25 0.572, s50 0.682, s75 0.707, s100 0.690,
**s125 0.752 [0.677, 0.819] (chosen)**, s150 0.740, final 0.736; the untrained Qwen3-8B 0.604.

| cell (N) | verifier AUROC | rev | verifier − rev | selector − cascade | cross-fitted Bayes | bound | verifier alone |
|---|---|---|---|---|---|---|---|
| BIRD dev, base | 0.819 [0.788, 0.849] | 0.510 | +0.309 [+0.257, +0.362] | **+1.18 [+0.54, +1.87]** | +1.24 [+0.76, +1.76] | +2.10 | +0.76 [−0.15, +1.70] |
| Spider test, base | 0.737 [0.693, 0.777] | 0.632 | +0.105 [+0.043, +0.166] | **+2.01 [+1.38, +2.62]** | +1.95 [+1.17, +2.74] | +2.31 | +1.78 [+0.90, +2.68] |
| Spider dev, base | 0.797 [0.742, 0.847] | 0.682 | +0.115 [+0.029, +0.197] | **+0.94 [+0.20, +1.75]** | +2.04 [+1.10, +3.13] | +2.65 | +2.12 [+0.81, +3.46] |
| BIRD dev, trained (C1) | 0.763 [0.726, 0.798] | 0.502 | +0.260 [+0.202, +0.319] | **+0.87 [+0.15, +1.57]** | +0.85 [+0.37, +1.31] | +1.39 | +0.07 [−0.96, +1.02] |
| Spider test, trained | 0.716 [0.671, 0.761] | 0.591 | +0.125 [+0.058, +0.193] | **+1.51 [+0.90, +2.18]** | +1.63 [+0.90, +2.37] | +2.05 | +1.63 [+0.80, +2.49] |
| Spider dev, trained | 0.785 [0.731, 0.839] | 0.590 | +0.194 [+0.106, +0.287] | **+2.04 [+1.14, +3.05]** | +2.20 [+1.18, +3.30] | +2.64 | +2.16 [+0.90, +3.42] |

(β 0.8 base / 0.7 trained, fitted on the held-out-database fresh questions; 0–8 question-seeds per cell with a structure the prior
never saw keep d; the verifier's prefill 2,085 / 1,943 tokens per question-seed on BIRD dev, 462–655 on Spider, no output tokens.)

- **SEL-P1 holds** (verifier − rev on BIRD dev +0.309 / +0.260). **SEL-P2b holds** (3 of 3 above, 0 below). **SEL-P2t holds** (3 of
  3, 0 below). **SEL-P3 holds** (5 of 6 within 0.7; the miss is BIRD dev base, cross-fitted +1.24 against the bound's +2.10; every
  cross-fitted gain lies below its bound). **SEL-P4 holds** (|0.819 − 0.770| = 0.049, |0.763 − 0.743| = 0.020; the base cell 0.001 inside
  the line). The expected AUROCs were exceeded on Spider (0.72–0.80 against 0.62–0.72) and for base N on BIRD dev (0.82 against
  0.68–0.78); the gains fell inside the expected ranges except Spider dev base (+0.94, below +1.0).
- **The whole SQL pipeline against the default SB→T→T** (computed from the same rows, not a registered prediction; paired over
  questions): base N 61.1% at 1.39k tokens vs 59.5% at 1.68k on BIRD dev, +1.75 [+0.65, +2.85] (the cascade alone +0.58 [−0.27,
  +1.43]); Spider test 78.9% at 0.47k vs 76.2% at 1.08k, +2.93 [+1.75, +4.07] (+0.92); Spider dev 75.4% at 0.57k vs 73.8% at 1.13k,
  +1.87 [+0.61, +3.21] (+0.93). Trained N: 62.2% at 1.36k, +2.86 [+1.73, +4.14] (+1.99, CV-1's P8 reproduced); 81.2% at 0.44k, +5.24
  [+4.02, +6.48] (+3.73); 78.1% at 0.54k, +4.57 [+3.17, +6.20] (+2.53). With the verifier the untrained quick query's peer cascade
  beats the default on SQL in 3 of 3 sets, which SQL-PA's PA2 (1 / 3) did not.
- **Where it changes the answer** (fresh-fitted selector against d): BIRD dev base 98 right for wrong, 44 wrong for right (80 / 35
  by choosing the peer's query); Spider test base 131 / 26; trained N 101 / 61 and 120 / 41 (mostly by keeping the trained N's query).
- **What it learned** (raw cases, `sel_cols.py`): on the 29–42% of (right, wrong) pairs whose queries return a different number of
  columns, the verifier orders 79–94% right and "fewer columns first" 71–98%: BIRD's convention of returning only what is asked
  (no helper COUNT or sort column), which Spider shares. On the 58–71% of pairs with the same columns it orders 71–75% right on BIRD
  dev and Spider dev and 61–62% on Spider test: content beyond the convention (the join key, a filter the question states, DISTINCT
  in a count), weaker on Spider's style. Its losses are logic it misses where it prefers the shorter query (COUNT(DISTINCT) in a
  percentage, INTERSECT read as OR, a join through the wrong key).
- **More candidates would not help** (stored rows, `selk_cov.py`): adding 13 more of Qwen3-8B's stored quick queries (seeds 4–16) to
  the 1,437 BIRD dev base cells raises the share holding a right passing query from 60.4% to 61.9% (+0.48 points of room at ~980
  output tokens per cell); the room is in the three answers the cascade already paid for. GradeSQL's gain from 32 samples of another
  generator has no counterpart at this generator.

**Decision (registered, SEL-P2 holds for both N types):** the trained verifier's selection becomes the SQL cascade's last step for
base and trained N: N → peer → SB→T→T, and where N passed, the peer differed and N, P and d give ≥ 2 distinct passing answers, the
answer with the highest logit π(calls | structure) + β z. One prefill per candidate (shared prompt), no output tokens; labels of BIRD
train only, the checkpoint and β from held-out training databases. PROJECT, REPORT and PROPOSAL updated. The tool-call recipe
(addendum SEL-TC) was pre-registered at 14:5x UTC and is running.

## Addendum SEL-W: the within-question verifier on word problems (written 2026-11-01 18:1x UTC, before any SEL-W training step or score; the 3,496 scoring requests are built from stored rows, and the analysis was run only on synthetic scores)

**Why.** SEL holds on SQL. The word-problem cascade (N → gpt-oss-20b's quick program agrees → N, else SB→T→T; Qwen3-8B's default since
XPEER) leaves room at the same place: where N passed, gpt-oss-20b printed another value and N, P and d give ≥ 2 distinct passing
values (9.6–31.7% of problem-seeds), a right value is among them in 43–75% of these cells and d is right in 19–65%: +2.6 / +3.8 points
on MAMO (Qwen3-8B / Qwen3-14B-AWQ), +2.7 / +2.2 on OptiBench's other 403 problems (stored rows, `nlp_data/scratch/fb_room.py`).
VER trained a pointwise verifier on Qwen3-8B's OptMATH-Train programs; as a gate across problems it did not transfer (held-out AUC
0.728, untrained 0.702). Read as a within-question selector on VER's stored scores (Qwen3-8B's N / SB / T programs on the four
development sets, 117 problems with a right and a wrong passing value) it is no better than the untrained model either: 0.736 vs 0.730
(`nlp_data/scratch/ver_within.py`). RV's theory 1: a score f(q) + g(c, q) chooses with g only; a pointwise loss spends the adapter on f
(which problems are hard — VER learned OptMATH-Train's generator), the pairwise within-question loss trains g alone. SEL's pairwise
verifier transferred from BIRD to Spider (0.72–0.80). SEL-W asks whether the objective, not the data, made that difference: VER's own
programs, SEL's loss. Related: GenRM (2408.15240) and LEVER (2302.08468) rank candidates with trained verifiers; optimization modeling
trains generators from solver outcomes (SIRL, 2505.11792; 2604.00442) rather than a selector; none compares pointwise and within-question
training of one verifier on the same programs for transfer, or uses it only where a cheap cross-model check failed.

**Arms.** V0: Qwen3-8B with VER's prompt, untrained (label-free). V1: VER's adapter (pointwise SFT on these programs,
`optmath_train/td/adapter_ver_v1`). V2: Qwen3-8B + LoRA r 16 trained as SEL on the stored Qwen3-8B OptMATH-Train programs of VER's
training problems (td rows q8b / q8bq2: 8 quick programs, the cut think's, the full think's; crc32(id) % 10 ≠ 0): passing programs
grouped by printed value (`run_nlopt.correct` either way), problems with a right and a wrong value (about 1,030), context = VER's
prompt, s = logit(yes) − logit(no), per problem the mean over (right, wrong) value pairs of log(1 + exp(s_w − s_r)), ≤ 8 values, one
program per value drawn per epoch; batch 16, lr 5e-5, 2 epochs, adapters every 25 steps (`wp_train.py --orm`). Every arm's score:
log P(yes) − log P(no) of the first answer token, case variants summed (VER's p_yes as log-odds; `score_conf.py sel`, task word).

**Choices on the development sets** (OptiBench's third, BWOR, LogiOR, OptMATH, whose labels made every earlier choice): V2's
checkpoint = the highest within-question AUROC on their fallback sets (both N types pooled); the method's arm = the highest of V0 / V1 /
V2 by that AUROC; π (the structural prior) and β fitted on the four development fallback sets of the same N type.

**Targets** (no choice uses them): OptiBench's other 403 problems (XPEER's fresh run) and MAMO (863) × N ∈ {Qwen3-8B, Qwen3-14B-AWQ};
P = gpt-oss-20b's quick program, d = N's SB→T→T (XPEER's cells), seeds 1–3. Output tokens unchanged; prefill reported.

**Predictions** (paired 95% intervals over problems):
- **SEL-W-P1 (the objective):** V2 − V1 within-question AUROC on the targets (per problem, both sets and N types pooled), lower bound > 0.
- **SEL-W-P2 (decision):** the chosen arm's selector − cascade, lower bound > 0 in ≥ 2 of 4 cells, upper bound < 0 in none.
- **SEL-W-P3 (theory):** the chosen arm's cross-fitted Bayes gain within 0.7 of the Gaussian bound at its measured AUROC in ≥ 3 of 4.
- **SEL-W-P4 (label-free):** V0's selector − cascade, lower bound > 0 in ≥ 2 of 4, upper bound < 0 in none.
- **SEL-W-P5 (the score's share):** the chosen arm's selector − the development prior alone (β = 0), both targets pooled per N type,
  lower bound > 0 for both N types.
- Expected: V0 and V1 0.68–0.76 on the targets, V2 0.74–0.82; the bound at AUROC 0.75 gives +1.1 / +1.3 (Qwen3-8B; ob403 / MAMO) and
  +0.9 / +2.1 (Qwen3-14B-AWQ). P2 is uncertain on ob403 (158–161 cells), and part of any gain may be the prior (who proposed the
  value), which LS found does not travel between word sets — P5 separates it.

**Decision.**
- P2 holds → the chosen arm's selection becomes the word cascade's last step for Qwen3-8B; for Qwen3-14B-AWQ (default SB→T→T) the
  default becomes cascade + selection only if pipeline − SB→T→T has a lower bound > 0 on both targets; PROJECT, REPORT and PROPOSAL
  updated (the selection step then holds on two task types).
- P2 refuted, P1 holds → the within-question objective transfers better than the pointwise one but not enough to pay at two or three
  candidates; stated.
- P1 refuted → on word problems the loss is not what limits transfer; with VER, the trained-verifier line on word problems closes,
  stated with SEL's contrast (SQL's wrong passing answers differ by conventions a verifier can learn).
- P4 holds → label-free selection pays on word problems (unlike SQL and tool calls, RV); if V0 is also the chosen arm, the step needs
  no training.

## Results of addendum SEL-TC (written 2026-11-01 18:4x UTC; `results/lcm_seltc_val.log`, `results/lcm_seltc.log`; training job 1294857, 160 steps on the 1,267 of 6,000 ToolACE training requests with a right and a wrong passing answer, 3,861 answers; scoring job 1294858, every candidate scored, none failed; whole pipeline and raw cases `nlp_data/scratch/seltc_full.py`)

**Checkpoint** (held-out ToolACE, pooled within-question AUROC over 791 requests): s25 0.707, s50 0.753, s75 0.779, s100 0.486, s125
0.771, **s150 0.793 [0.767, 0.817] (chosen)**, final 0.786; the untrained model 0.487. s100 is at chance between two checkpoints at
0.77–0.78 although its training pairs were ordered 84% right at that step and its scores are not truncated (10 of 6,104 zeros);
unexplained, and discarded by the registered choice.

| cell (N) | verifier AUROC | rev | verifier − rev | selector − cascade | cross-fitted Bayes | bound | verifier alone |
|---|---|---|---|---|---|---|---|
| BFCL, base | 0.837 [0.814, 0.859] | 0.475 | +0.362 [+0.322, +0.401] | **+1.08 [+0.78, +1.41]** | +1.02 [+0.73, +1.33] | +1.49 | +0.60 [+0.09, +1.13] |
| BFCL, trained (C1tc) | 0.800 [0.775, 0.824] | 0.487 | +0.313 [+0.272, +0.354] | **+1.68 [+1.17, +2.24]** | +1.63 [+1.10, +2.20] | +2.36 | +0.99 [+0.30, +1.68] |

(β 1.1 / 1.2; 2,833 / 2,892 fallback request-seeds; no unseen structure; prefill 808 / 822 tokens per request-seed, no output tokens.)

- **SEL-TC-P1 holds**, **SEL-TC-P2b holds**, **SEL-TC-P2t holds**, **SEL-TC-P4 holds** (|0.837 − 0.798| = 0.039, |0.800 − 0.784| = 0.016).
  **SEL-TC-P3 refuted** (1 of 2: base 0.47 from the bound, trained 0.73 — the bound overstates by 0.5–0.7 here as on SQL).
  AUROC on BFCL exceeded the expected 0.65–0.80; gains inside +0.3 to +2.
- **The whole pipeline against the default SB→T→T** (same rows, not a registered prediction): base 85.8% at 0.28k tokens vs 83.9% at
  0.38k, +1.94 [+1.41, +2.46] (the cascade alone +0.85); trained 86.9% at 0.27k, +3.04 [+2.34, +3.72] (the cascade alone +1.35). TL's
  fitted call policy reached 86.4% at 1.6–1.9× the cascade's tokens; two trained quick models 86.5% at 0.27k.
- **Where it changes the answer:** base 128 right for wrong, 15 wrong for right (82 of the 128 by choosing a right abstention); trained
  294 / 118 — abstentions 223 / 54, calls 71 / 64. The verifier learned when not to call: it rejects calls filled with placeholder values
  ("Your Starting City", "City, State") or values the request never gave; its losses are abstentions where a call passing the user's
  words on was right (`answer_question(statement=...)`) and calls differing in one optional argument, where it is at chance.
- Note: SEL's and SEL-TC's scoring jobs appended the untrained model's scores to one file at the same time; one line is malformed (one
  untrained score lost; the untrained model is only reported). Later jobs write in turn.

**Decision (registered):** SEL-TC-P2 holds for both N types and the point gains exceed the fitted call policy's on BFCL (base +1.08 vs
TL −0.11; trained +1.68 vs +1.04) → the verifier is added to the tool-call method; its combination with the call policy is pre-registered
next (addendum SEL-TC2).

## Addendum SEL-TC2: the call policy and the verifier together on tool calls (written 2026-11-01 18:4x UTC, before any new score; 15,356 scoring requests built, 11,519 already scored by SEL-TC; the analysis was run only on synthetic scores)

**Why.** The two act on different things. TL's planner (fitted on the held-out ToolACE requests' labels) decides which calls to make
— where the trained quick answer and the peer disagree it runs a full think to break the tie, at 1.6–1.9× the cascade's tokens — and
outputs the answer group its labels favour for the observed pattern; the verifier reads the answers. They combine as a Bayes rule at the
planner's stop: logit P_planner(group right | pattern) + β z. Whether the planner's extra calls still pay once the verifier chooses, and
whether the verifier adds to the planner, decides the tool-call method.

**Policy.** TL's transfer planner (`Supervised` on the 3,549 held-out ToolACE requests × 3 seeds, their mean tokens per call). Where it
stops with ≥ 2 passing answer groups and every one is scored: the group with the highest logit((r + 0.5) / (n + 1)) + β z (r, n the
planner's counts for the group and the pattern; z = the verifier's mean score over the group's calls, centred in the set, divided by the
pooled within-set SD of the held-out stop sets); β by likelihood on the held-out stop sets (grid 0–4). Elsewhere the planner's own
choice; a pattern the planner never saw takes SEL-TC's outcome (counted). Verifier: SEL-TC's checkpoint s150, no new training. New
scores: the 3,837 passing texts outside RV's cells (mostly the planner's extra thinks), job `seltc2`.

**Predictions** (BFCL, paired 95% intervals over requests):
- **SEL-TC2-P1 (the verifier adds to the planner):** combined − planner alone, lower bound > 0 for both N types.
- **SEL-TC2-P2t / P2b (the planner adds to the verifier):** combined − SEL-TC's pipeline (cascade + verifier), lower bound > 0, each N
  type on its own.
- Expected: P1 holds (+0.8 to +1.8, the verifier's gain at the planner's stop sets); P2t uncertain (0 to +0.8: the planner's vote for the
  trained quick answer overlaps with the selector's structural prior, and its extra thinks cost 0.15–0.2k tokens); P2b refuted (TL gained
  nothing for the untrained quick calls).

**Decision.** P2 holds for an N type → the tool-call method for it is the planner with the verifier at its stop; refuted → the cascade
with the verifier at its fallback (SEL-TC's pipeline), which needs no planner and no extra calls; PROJECT, REPORT and PROPOSAL state
the tool-call method accordingly.

## Addendum SEL-G: SEL's verifier at the other generators' SQL fallback (written 2026-11-01 18:5x UTC, before any of their candidates is scored; 17,698 requests built, 5,090 already scored by SEL; the analysis was run only on synthetic scores)

**Why.** SEL's verifier was trained on Qwen3-8B's and Qwen3.5-9B's candidates and tested where Qwen3-8B generates. The SQL claim
covers other generators (XG, FINAL: Qwen3-14B-AWQ, Qwen3.5-9B, gpt-oss-20b), whose fallback cells hold as much room (+4.2 to +7.8 points:
a right passing query among N, P, d that d misses; stored rows). Whether the selection step is part of the SQL method for any generator
or only Qwen3-8B's is the claim's scope; gpt-oss-20b writes queries in another family's style the verifier never saw.

**Cells.** Generators Qwen3-14B-AWQ (peer Qwen3.5-9B), Qwen3.5-9B (peer Qwen3-8B), gpt-oss-20b (peer Qwen3.5-9B) — the pre-registered
peers (PEER); N, SB, T the generator's own; BIRD dev, Spider test, Spider dev. Verifier: SEL's checkpoint s125, no new training. π on
the generator's 1,338 fresh BIRD-train questions (labels), β on its fallback cells of the 343 held-out-database ones, as SEL.

**Predictions** (paired 95% intervals over questions):
- **SEL-G-P1 (decision):** selector − cascade, lower bound > 0 in ≥ 2 of 3 targets and upper bound < 0 in none, for ≥ 2 of 3 generators.
- **SEL-G-P2:** BIRD dev within-question AUROC ≥ 0.70 for every generator.
- Expected: AUROC 0.72–0.82 for the Qwen generators, 0.65–0.80 for gpt-oss-20b; gains +1 to +3 (the room is larger than Qwen3-8B's).

**Decision.** P1 holds → the verifier step is part of the SQL method for any of these generators (scope stated per generator where
P1 fails for one); P1 refuted → the step is stated for Qwen3-8B only, with the generators where it fails and their AUROCs.

## Results of addendum SEL-TC2 (written 2026-11-01 18:5x UTC; `results/lcm_seltc2.log`; job 1296197, 3,837 new texts scored, none failed; raw reading `nlp_data/scratch/seltc2_raw.py`)

| BFCL, N | combined | planner alone | SEL-TC pipeline | cascade | default | combined − planner | combined − SEL-TC pipeline | combined − default |
|---|---|---|---|---|---|---|---|---|
| base | 86.6% @ 0.48k | 84.7% @ 0.48k | 85.8% @ 0.28k | 84.8% @ 0.28k | 83.9% @ 0.38k | +1.90 [+1.52, +2.27] | **+0.70 [+0.40, +1.02]** | +2.64 [+2.04, +3.23] |
| trained | 87.7% @ 0.43k | 86.4% @ 0.43k | 86.9% @ 0.27k | 85.2% @ 0.27k | 83.9% @ 0.38k | +1.38 [+0.97, +1.83] | **+0.73 [+0.41, +1.07]** | +3.77 [+3.03, +4.47] |

(β 1.0 / 1.1 from 3,132 / 3,146 held-out stop sets; unseen planner patterns 14 / 5 of 10,446 request-seeds; SEL-TC pipeline −
planner +1.20 / +0.64.)

- **SEL-TC2-P1 holds** (+1.90, +1.38). **SEL-TC2-P2t holds** (+0.73). **SEL-TC2-P2b holds** (+0.70), against the expectation: the
  planner alone gains nothing for the untrained quick calls (−0.1 against the cascade), but with the verifier choosing at its stop it does.
- **Mechanism:** the planner stops after N and P on 58% of request-seeds and runs a full think (T or the retry at another seed) on
  about 38% (base) / 27% (trained); the combined policy's gains over SEL-TC's pipeline are on those, almost all live requests (base: 62 + 47 + 18 right for wrong
  where it ran T / T2, against 24 + 24 + 5 the other way; trained 80 + 35 against 34 + 12). The planner's extra thinks add candidates the
  verifier can tell apart; alone the planner could only vote among them. They are complements: one gathers, the other chooses.
- The planner's values ignore the verifier (it plans as if its own vote decided), so the combination is not the policy that plans for
  the verifier.

**Decision (registered):** P2 holds for both N types → the tool-call method is TL's planner (fitted on held-out training requests) with
the verifier choosing at its stop, for trained and untrained quick calls: 87.7% / 86.6% at 0.43k / 0.48k tokens against the default's
83.9% at 0.38k. PROJECT, REPORT and PROPOSAL updated.

## Addendum SEL-TC3: a planner that plans for the verifier (written 2026-11-01 19:0x UTC, offline on SEL-TC2's scores, before the analysis has been run on them; run only on synthetic scores)

**Why.** SEL-TC2's planner values each call as if its own vote ended the request, so it calls a think where its vote gains, not where
the verifier would. With the verifier choosing at the stop, the stop's reward is the verifier's accuracy given what has been seen; the
Bayes planner over the same patterns with that reward values a call by what the verifier then does with the extra answer. Derivation:
in TL's planner (dynamic programming over observed patterns, value = P(right) − λ·tokens), replace the stop value of every pattern with ≥ 2
passing answers by the mean, over the fitting rows reaching that pattern, of whether the verifier's choice there is right (the
counts-based log-odds of each answer + β z, with the row's own label left out of the counts, else a rare pattern's label makes its
choice right in-sample and draws the planner to rare patterns). Nothing else changes: the same rows (held-out ToolACE), tokens, β and
SD as SEL-TC2, no new score.

**Prediction (BFCL, paired 95% intervals over requests).**
- **SEL-TC3-P1:** the verifier-aware planner − SEL-TC2's combination, lower bound > 0 for both N types.
- Expected: 0 to +0.5, at more tokens; uncertain, because the stop values are per-pattern means (tens to hundreds of rows) that the
  value recursion can exploit where they are noisy.

**Decision.** P1 holds → the tool-call planner becomes verifier-aware; refuted → SEL-TC2's combination stays (fewer tokens, no second
fit); stated either way.

## Results of addendum SEL-TC3 (written 2026-11-01 19:0x UTC; `results/lcm_seltc3.log`, offline)

| BFCL, N | verifier-aware planner | SEL-TC2's combination | default | verifier-aware − combination |
|---|---|---|---|---|
| base | 86.9% @ 0.78k | 86.6% @ 0.48k | 83.9% @ 0.38k | +0.07 [−0.27, +0.41] |
| trained | 87.7% @ 0.66k | 87.7% @ 0.43k | 83.9% @ 0.38k | −0.15 [−0.36, +0.06] |

- **SEL-TC3-P1 refuted** (0 of 2 above, 0 below). Planning for the verifier makes the planner think on more requests (+0.23k / +0.30k
  tokens per request-seed) for +0.3 / +0.0 accuracy points: the held-out patterns' verifier accuracies promise more than the extra
  answers deliver on BFCL, so the value recursion buys thinks on estimation noise, as the prediction's caveat said.
- **Decision (registered):** SEL-TC2's combination stays the tool-call method (fewer tokens, one fit).

## Addendum SEL2: the SQL call policy with the verifier at its stop (written 2026-11-01 19:0x UTC, before any new score; 13,889 requests built, about 4,900 new; the analysis was run only on synthetic scores)

**Why.** On tool calls the fitted call policy and the verifier are complements (SEL-TC2: the policy's extra thinks give the verifier
answers to choose from, +0.70 / +0.73 over the verifier at the cascade's fallback, although the policy alone gained nothing for the
untrained quick calls). On SQL the fitted policy alone was not reliable (TL: 1 of 5 fit / target pairs), and the bound B says the calls'
outcomes leave about a point above the cascade; whether the verifier turns the policy's extra calls into accuracy on SQL decides whether
the SQL method needs the policy.

**Policy.** TL's SQL planner (`Supervised` on the 1,338 fresh BIRD-train questions × 3 seeds, their mean tokens per call), with SEL's
verifier (s125) choosing at its stop where ≥ 2 passing results are seen (SEL-TC2's rule: the planner's log-odds + β z), β and SD from the
stop sets of the 343 held-out-database fresh questions (the other fresh questions sit on the verifier's training databases). A pattern
the planner never saw takes SEL's outcome. Compared with SEL's pipeline (the cascade with SEL's fresh-fitted selector at its fallback).

**Predictions** (paired 95% intervals over questions; BIRD dev, Spider test, Spider dev):
- **SEL2-P1b / P1t:** combined − SEL's pipeline, lower bound > 0 in ≥ 2 of 3 targets and upper bound < 0 in none, for the untrained /
  trained quick query.
- Expected: 0 to +0.8, at 1.5–1.7× SEL's tokens; uncertain (SQL's thinks are long, 1–2k tokens, so the policy's extra thinks cost more
  per answer than on tool calls).

**Decision.** P1 holds for an N type → the SQL method for it is the planner with the verifier at its stop; refuted → SEL's pipeline
(cascade + verifier at its fallback) stays.

## Results of addendum SEL-G (written 2026-11-01 19:2x UTC; `results/lcm_selg.log`; job 1296216, 12,608 new candidates scored, none failed)

| generator ← peer | target | AUROC | selector − cascade | pipeline vs SB→T→T | pipeline − SB→T→T (cascade alone) |
|---|---|---|---|---|---|
| Qwen3-14B-AWQ ← Qwen3.5-9B | BIRD dev | 0.790 | **+1.07 [+0.26, +1.87]** | 59.2% @ 1.19k vs 57.3% @ 1.50k | +2.07 [+0.86, +3.27] (+1.00) |
| | Spider test | 0.733 | **+1.61 [+0.98, +2.24]** | 79.8% @ 0.40k vs 77.0% @ 0.98k | +3.03 [+1.93, +4.13] (+1.42) |
| | Spider dev | 0.788 | **+1.10 [+0.24, +2.08]** | 76.9% @ 0.47k vs 74.6% @ 1.05k | +2.53 [+1.13, +3.96] (+1.43) |
| Qwen3.5-9B ← Qwen3-8B | BIRD dev | 0.828 | **+1.57 [+0.96, +2.20]** | 60.6% @ 1.69k vs 58.0% @ 2.19k | +2.80 [+1.74, +3.88] (+1.23) |
| | Spider test | 0.741 | **+1.36 [+0.84, +1.88]** | 79.8% @ 0.38k vs 79.1% @ 1.00k | +1.00 [+0.08, +1.91] (−0.36) |
| | Spider dev | 0.794 | **+1.14 [+0.41, +1.95]** | 75.6% @ 0.44k vs 73.5% @ 1.04k | +2.37 [+1.08, +3.64] (+1.23) |
| gpt-oss-20b ← Qwen3.5-9B | BIRD dev | 0.777 | **+2.40 [+1.26, +3.53]** | 60.4% @ 0.60k vs 55.9% @ 0.53k | +4.39 [+3.03, +5.81] (+1.99) |
| | Spider test | 0.762 | **+2.66 [+1.78, +3.56]** | 79.6% @ 0.18k vs 75.5% @ 0.21k | +4.13 [+2.93, +5.34] (+1.47) |
| | Spider dev | 0.760 | **+1.63 [+0.61, +2.73]** | 76.1% @ 0.21k vs 73.2% @ 0.22k | +2.94 [+1.60, +4.28] (+1.31) |

- **SEL-G-P1 holds** (3 of 3 generators, every cell above). **SEL-G-P2 holds** (BIRD dev 0.790 / 0.828 / 0.777). The verifier, trained
  on two Qwen models' candidates, orders another family's queries (gpt-oss-20b) at 0.76–0.78 and gains most there (+1.6 to +2.7: its
  fallback has the most room). Held-out-database fresh AUROCs (0.78–0.80) again match BIRD dev within 0.04.
- Where the peer cascade alone did not beat the default (Qwen3.5-9B on Spider test, −0.36; FINAL), the pipeline with the verifier does
  (+1.00 [+0.08, +1.91]).
- **Decision (registered):** the verifier step is part of the SQL method for every generator tested (Qwen3-8B, Qwen3-14B-AWQ,
  Qwen3.5-9B, gpt-oss-20b); PROJECT, REPORT and PROPOSAL state the scope.
