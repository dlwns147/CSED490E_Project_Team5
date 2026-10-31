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
