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
  - Training makes the quick query as accurate as the base model's short think and full think (on Spider dev 74.1% vs 73.6% and
    73.8%), so falling back to the short think when the peer disagrees throws away an answer as good as the fallback. The full think
    serves better as a referee between the two quick answers.
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
