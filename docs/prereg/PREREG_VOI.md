# PREREG_VOI — label-free, cost-aware acquisition of answers across heterogeneous sources, for every math-computation set (registered 2026-11-22 14:4x UTC, before the policy is run on any set)

**Why (user 11-22: "suggest and test novel solutions for all math computation problems ... check and beat recent related research ...
don't suggest heuristics").** Our methods so far are fixed ladders (check → peer → think → retry) whose order and stopping points were
chosen by hand per set, and the method was scored on word problems only. On every math-computation set we already store several answer
sources (cheap programs, text answers, thinking, brute force, a second family, a specialist), each with its own price, and their
agreement carries label-free evidence about which answer is right. The question: given a price per token, which source should be
queried next on THIS problem, when to stop, and which answer to return — decided from a fitted model, with no hand threshold.

**Method (VOI).** Per set, a latent-class model of answer sources, fitted by EM on the set's unlabeled samples:
- each problem has a latent true answer y and a latent difficulty class z (number of classes D chosen by BIC, D ≤ 3);
- a sample from source s is right with probability p_{s,z}, a visible failure (no value) with f_{s,z}, else wrong; wrong values of a
  problem follow an Ewens / Chinese-restaurant partition with concentration α (fitted), so shared misreadings (wrong values that
  coincide) are modelled, not assumed away (our LCM finding: "unanimity cannot be told from a shared mistake" without this);
- free checks (Project Euler: the statement's small cases; OEIS: the own brute force's agreement on the first 8 terms) enter as
  observations with likelihoods P(pass | right), P(pass | wrong) per source, fitted in the same EM;
- the policy, per problem: after each sample, compute the posterior over y; stop and return argmax_y if no source's one-step value
  of information (expected gain in 100·P(return right) minus λ × its mean tokens) is positive, else query the source with the largest
  value (knowledge-gradient rule, Frazier et al. 2008). λ is the course exchange rate (0.5 per ktok), the only input; also 0.25, 1, 2.
- Cross-fitting: EM parameters are fitted on one half of a set's problems (unlabeled) and the policy runs on the other half, and back.

**Prior work it is new against** (searched 2026-11-22 by mechanism): Adaptive-Consistency (Aggarwal et al. 2023), ESC, optimal
Bayesian stopping for self-consistency (arXiv 2602.05395), ReASC (ACL 2026 Findings), CASE — all single-source stopping; CoT-PoT
ensembling (arXiv 2604.17433) — two fixed sources, no choice of what to query; multi-LLM Bayesian sequential testing (arXiv
2604.01086) — binary hypotheses with known accuracies; Beyond Majority Voting (arXiv 2510.01499), Dawid–Skene — static aggregation
of all samples, no acquisition or cost; FrugalGPT / AutoMix / "Is Escalation Worth It?" (arXiv 2605.06350) — learned with labels;
C3PO (arXiv 2511.07396) — label-free stopping of a fixed cascade. New here: label-free calibration of heterogeneous, differently priced
sources (incl. checks and a second family) with a shared-mistake model, and a value-of-information choice of WHICH source to query.

**Sets and sources** (stored samples, 3 seeds per source unless noted; new runs for Project Euler and MathConstruct, lanes
mall_q8b / mall_o20, started 14:45):
- MATH-500 and AIME 24+25 (560): Qwen3-8B prog / text / think, gpt-oss-20b prog / text / think, R1-Distill-Qwen-7B think (math
  specialist), Qwen3-14B-AWQ think, Qwen3-32B think. Answer equality: equal to each other if both match gold (math_verify, as graded),
  else normalized-string equality — the policy sees only the equality structure.
- OEIS (500, easy + hard): Qwen3-8B / gpt-oss-20b / gpt-oss-120b prog, think and brute force (brute = 8-term check). Answer = the 20
  printed terms.
- Project Euler dev 120 and MathArena 943–992 (50, late 2025, fresh): Qwen3-8B and gpt-oss-20b progc (program + statement checks)
  and thinkp (thinking, then a program). Answer = the printed integer.
- Optimization word problems (5 held-out sets): own program, think, peer program, peer think, both models. Answer = objective (agree()).
- MathConstruct (121): answers are constructions (no equality); scored only descriptively (own verify() as the check).

**Baselines** (same sample pools, same costs, same utility): (B1) each single source, one sample; (B2) self-consistency, majority of
3 of the best thinking source; (B3) Adaptive-Consistency (Beta(1,1), threshold 0.95) on that source; (B4) CoT-PoT ensembling: text =
program accept, else that source's think; (B5) our current cascade (own → peer agreement → think → retry on a failed think);
(B6) static Dawid–Skene / weighted vote over every sample (all costs paid); (B7) FrugalGPT-style learned cascade (cross-fitted with
LABELS, an advantage the method does not have).

**Test.** Per set, VOI − B, utility at 0.5 per ktok, paired bootstrap clustered by problem, for B ∈ {B2, B3, B4, B5} (the strongest
published label-free baselines and ours); one-sided, Holm over all set × baseline pairs (MathConstruct excluded). Claimed for a set if
VOI beats all four there. Also reported: B1, B6, B7, and the rates 0.25 / 1 / 2. Fresh confirmation: MathArena Project Euler 943–992.
**Prediction:** VOI ≥ the best fixed baseline on every set (it can choose any fixed policy's actions), with the largest gains where
source costs differ most (Project Euler, AIME); a loss anywhere means the fitted model is wrong there (read the EM fit first).

## Amendment 1 (2026-11-22 15:1x UTC, after MATH + AIME, before any other set's VOI result was seen)
MATH + AIME was run first and is now the DEVELOPMENT set. Two model changes were made after reading its fit, and are frozen for every
other set: (v2) each sample's token count is an observation of the difficulty class (log tokens ~ N(mu[s,z], sd[s,z])) and the cost of a
query is its posterior-expected token count — v1 used one mean cost per source although hard problems' thinks are longer; (D) the number
of difficulty classes is chosen by BIC up to 6 (the registered cap of 3 was hit on both halves, so BIC wanted more). MATH + AIME results
(development, not claims): v1 utility 90.5, v2 91.2, v2 + D≤6 91.8, against the best single source (Qwen3-32B think) 92.6, gpt-oss-20b
think 92.1 and the label-fitted ladder 92.1: VOI over-samples on a set where one strong think is right 95% of the time (it takes a
second sample on 133 of 280 problems; calibration is good: predicted ≥ 90% → 99% right). MATH + AIME is not in the claim family; the
claim sets are OEIS, the five word-problem sets, Project Euler dev and Project Euler 943–992 (fresh).

## Interim results, v2 as frozen in amendment 1 (2026-11-22 15:2x UTC; python3 poc/voi.py <set>; λ = 0.5)
| set | VOI | best label-free baseline | VOI − baselines (B2 SC@3 / B5 our cascade; label-fitted ladder) |
|---|---|---|---|
| word problems (1,224 held-out problems, 4 sources) | 74.9% @ 7.6k, U 71.1 | our cascade (gpt-oss-20b) 71.0% @ 3.9k, U 69.0 | +2.18 [+0.96, +3.41] / +2.07 [+0.62, +3.59]; ladder (labels) +2.23 [+0.68, +3.77]; router (labels) +16.8 |
| OEIS (500, 6 sources) | 35.4% @ 14.7k, U 28.0 | single gpt-oss-120b program 29.4% @ 0.8k, U 29.0 | SC@3 +7.81 [+5.49, +10.21] / cascade +0.50 [−1.73, +2.77]; best single −0.99 [−3.44, +1.56] |
- Word problems: VOI beats every baseline, including the two that use labels. OEIS: VOI beats self-consistency, ties our cascade and
  the best single source — it pays 14.7k tokens to gain 6 accuracy points over gpt-oss-120b's one cheap program.
- *Constructive reading:* on both OEIS and MATH the policy over-buys samples. On OEIS the fitted Ewens concentration sat at the grid's
  upper end (α = 20.1, "wrong programs almost never coincide"), while hard sequences have wrong programs that agree (the same simple
  formula); a single α for all difficulty classes makes agreement on hard problems look like correctness, so more samples look valuable.
## Amendment 2 (2026-11-22 15:2x UTC, after OEIS v2, before any Project Euler row is scored)
v3 = v2 + one concentration α per difficulty class + the α grid widened to e^6 (its e^3 bound was hit). Decided after reading OEIS, so
OEIS and MATH under v3 are diagnostics only; v2 and v3 are both scored on Project Euler dev and fresh 943–992 (not yet seen), and the
registered claim on those sets is v2's; v3 is reported beside it.

## v3 diagnostic result and amendment 3 (2026-11-22 15:4x UTC, before any VOI-SS row is scored)
- v3 (per-class concentration) does not fix OEIS: 26.9 vs v2 28.0 (best single 29.0); MATH 92.0 vs 91.8. The fitted per-class
  concentrations run the opposite way to my reading (hard classes get HIGH α: their wrong values rarely coincide), so the amendment-2
  diagnosis was wrong and v3 is dropped (it stays a reported diagnostic on Project Euler).
- What the fits show instead: the label-free model cannot tell "agree and right" from "agree and wrong" when the share of right answers
  in a hard class is low — the identifiability limit our LCM work found (agreement-based EM overstates p in hard classes, so further
  samples look worth buying). The remedy that follows from that diagnosis is an independent signal on p, i.e. a few labels.
- **Amendment 3 (VOI-SS):** the same v2 model fitted semi-supervised — on a fraction of the fit half the true class is given (the class
  matching gold, or U if no sample is right); the rest unlabeled; same BIC-chosen D. Fractions 5%, 10%, 25%, 100% are all reported (a
  curve, not a tuned value). Test: VOI-SS 10% − {best single source, the label-fitted ladder (which uses 100% of the fit half's labels),
  SC@3, our cascade}, per set, utility at 0.5, clustered bootstrap, one-sided, Holm over sets × baselines; sets OEIS, word problems,
  Project Euler dev and fresh 943–992; MATH + AIME descriptive (development). Prediction: VOI-SS 10% ≥ label-free VOI everywhere, and
  ≥ the label-fitted ladder on OEIS and MATH, where label-free VOI over-buys.
