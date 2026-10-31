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
