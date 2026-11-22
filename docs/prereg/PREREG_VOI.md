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
