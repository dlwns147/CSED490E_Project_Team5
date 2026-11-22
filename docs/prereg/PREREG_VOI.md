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

## Amendment 3 result on OEIS, and amendment 4 (2026-11-22 16:4x UTC)
- **VOI-SS on OEIS: the prediction failed.** Labels do not fix it: 5% 27.6, 10% 27.5, 25% 24.9, 100% 29.4 vs label-free VOI 28.0 and
  best single 29.0. Even with every fit-half label, VOI only ties the best single source, so the identifiability diagnosis (amendment 3)
  does not explain OEIS either.
- **What does:** OEIS's headroom is in choosing, not buying. Some sample is right on 44.0% of sequences (oracle utility 43.6 vs best
  single 29.0), but a vote over all 18 samples is right on only 35.8%: right programs are often unique among several wrong ones, and
  agreement cannot pick them. The registered OEIS sources had no discriminating check — the brute-force programs we store were left out.
- **Amendment 4 (OEIS development only):** each program / think sample carries a free check — its first 8 terms equal the same model's
  brute force of the same seed — with the brute force's tokens added to its cost and P(pass | right), P(pass | wrong) fitted (label-free).
  OEIS is now a development set for VOI (decided after three looks); the claim sets left are word problems (v2, scored) and Project Euler
  dev + fresh 943–992, whose statement checks were in the registered design from the start.
- *Amendment 4 result (2026-11-22 16:5x UTC, OEIS development):* own brute-force checks do not separate right from wrong enough: VOI 27.8 vs best
  single 28.7 (−0.9 [−3.6, +1.9]), label-fitted ladder 28.5; a vote over all samples with checks is right on 36.2% where some sample is
  right on 44.0%. The brute force shares the program's misreading (X56: 68% precise). *MATH + AIME semi-supervised (development):*
  every label fraction ties (92.1–92.2 vs best single 92.6); the set is saturated (some sample right on 98.9%).
## Amendment 5 (2026-11-22 16:5x UTC, OEIS development, before any score exists)
The OEIS bottleneck is choosing a lone right program among wrong ones; agreement and own brute force do not separate them. The signal
that does not share the program's error path is the reverse direction (Coder-Reviewer reranking, Zhang et al. 2023): log p(the
sequence's name | the program) under Qwen3-8B as a plain LM (poc/score_oeis_rev.py, Slurm 1551239). In VOI it enters as one more
label-free observation per answer class — the class's score minus the problem's mean score, Gaussian with mean m_R if the class is
the true answer and m_W otherwise, fitted in the same EM. Scoring is prefill only (no output tokens; reported in the in+out view).
OEIS stays development; if it separates right from wrong there, it is carried to Project Euler (the name → the statement) only by a new
registration.
- *Amendment 3 on word problems (2026-11-22 16:5x UTC):* labels add nothing — VOI-SS 5 / 10 / 25 / 100% at 70.8 / 70.1 / 70.7 / 70.5 vs label-free
  VOI 71.1 (all ≥ every baseline). The label-free fit is already as good as a supervised one where the sources are complementary.

## Fresh Project Euler result (v2, registered claim) and amendment 6 (2026-11-22 17:4x UTC, before any Project Euler dev VOI row is scored)
- **MathArena Project Euler 943–992 (50 fresh problems, 3 families × progc / thinkp × 3 seeds): VOI LOSES.** Best single source
  (gpt-oss-120b think-then-program) 14.0% at 10.4k, utility 8.8; VOI 14.0% at 22.0k, utility 3.0: −5.83 [−7.35, −4.45]. VOI beats
  self-consistency (+4.2 over SC@3 of the same source) but not the single best sample. Labels do not rescue it (VOI-SS 100% 5.2).
- **Label-free diagnosis (posterior predictive check, poc/voi.py fit half):** the model under-predicts how often two samples of the
  SAME source agree — words 0.78 observed vs 0.56 predicted (Qwen3-8B program), 0.85 vs 0.75 (gpt-oss-20b program); OEIS 0.45 vs 0.29;
  MATH 0.79 vs 0.57, 0.93 vs 0.79. A source's repeated samples are correlated beyond the difficulty class (its errors repeat across
  seeds), but the model treats each repeat as fresh evidence, so repeat samples and within-source agreement look worth more than they
  are — the over-buying seen on MATH, OEIS and fresh Euler.
- **Amendment 6 (OD):** each source's repeated samples on a problem are Dirichlet-multinomial (right / fail / wrong) with a
  concentration κ_s fitted by EM (κ → ∞ recovers v2); the policy's predictive for the next sample of s uses s's earlier samples on
  that problem. Test: Project Euler dev (120, not yet scored by any VOI version), VOI-OD − {best single, SC@3, label-fitted ladder,
  VOI v2}, utility at 0.5, clustered bootstrap, Holm over the four. Every other set under OD is a diagnostic (already seen).
- *Amendment 5 result (2026-11-22 17:4x UTC):* the reviewer score does not separate right from wrong OEIS programs: pairwise AUROC 0.53 over the
  188 sequences that have both, top-scored class right on 27% (3,296 programs scored, Slurm 1551239). Not added to VOI. OEIS selection
  has no label-free signal among agreement, own brute force and reviewer likelihood.

## Amendment 6 diagnostics and the Project Euler dev test (2026-11-22 18:3x UTC; results/voi_<set>_od.txt, voi_euler.txt, voi_euler_od.txt)
- OD fits strong within-source correlation (κ 1.6–12 for most sources) but barely changes the policy: fresh Euler 5.5 (v2 3.0; best
  single 8.8), words 70.0 (v2 71.1), OEIS 28.2 (28.0), MATH 92.1 (91.8).
- **Project Euler dev (120, 3 families, registered test of OD):** VOI-OD 44.2% @ 17.5k, utility 35.4; v2 35.7; best single (gpt-oss-120b
  think-then-program) 38.3% @ 7.4k, 34.6. OD − best single +0.81 [−3.24, +5.44], − SC@3 +2.05 [−0.40, +4.53] (p 0.04), − label-fitted
  ladder +2.56 [−1.69, +7.44], − v2 −0.3: **not shown** under Holm. v2 − SC@3 +2.33 [+1.49, +3.17] (p 0.0002).
## Summary of the 24-hour test so far (claim sets only)
| set | VOI (label-free) vs strongest baseline | verdict |
|---|---|---|
| word problems (1,224) | +2.1 over our cascade, +2.2 over SC@3, +2.2 over the label-fitted ladder | **wins** |
| Project Euler dev (120) | +1.1 [−3.7, +6.0] over the best single sample; +2.3 over SC@3 | tie with the best single; beats SC@3 |
| Project Euler 943–992 fresh (50) | −5.8 [−7.4, −4.5] vs the best single sample; +4.2 over SC@3 | **loses** to one strong sample |
| development: MATH+AIME, OEIS | ties (saturated; selection-limited) | — |
Reading: VOI beats self-consistency everywhere and beats every baseline where cheap sources are informative and complementary (word
problems); where one expensive source dominates and the rest add little (hard Project Euler), it over-buys. Five model changes
(token-aware, semi-supervised, brute checks, reviewer score, overdispersion) did not remove that; the cause left standing is that the
policy's predicted value of an extra sample exceeds its realized value on hard sets.

## Why VOI over-buys on hard sets: predicted vs realized value of one more sample (2026-11-22 19:3x UTC; poc/voi_calib.py, fit half)
| source | predicted gain | realized under the model | realized with labels |
|---|---|---|---|
| fresh Euler, gpt-oss-120b think | 16.2 | 15.0 | 3.0 |
| fresh Euler, gpt-oss-20b think | 1.6 | 0.5 | 0.0 |
| Euler dev, gpt-oss-120b think | 17.2 | 17.3 | 8.7 |
| Euler dev, gpt-oss-120b program | 12.5 | 15.6 | 10.1 |
| words, gpt-oss-20b think | 27.6 | 26.8 | 21.1 |
| words, Qwen3-8B program | 10.7 | 10.3 | 9.1 |
- The model is self-consistent (predicted ≈ realized under its own posterior: the label-free check passes), but its posterior
  probability that the returned answer is right is too high where right answers are rare: on fresh Euler the realized gain with labels
  is a fifth of the predicted one. That gap cannot be seen without labels — the same identifiability limit as before (agreement cannot
  tell a shared wrong answer from a right one when right answers are rare), and it is why VOI over-buys exactly on the hardest sets.
  On word problems the gap is small (21 vs 28) and VOI wins.
- Consequence for the method: label-free VOI is safe where the sources are right often enough to calibrate one another; on sets where
  the best source is right on under ~40% of problems it needs labels to calibrate (VOI-SS 100% raised fresh Euler from 3.0 to 5.2 with
  only 25 labelled problems per half) or should not be used.

## MathConstruct (registered descriptive; 2026-11-22 19:4x UTC; results/x44/mcon_<m>_{progc,thinkp}_s1-3.jsonl, 121 problems × 3 seeds)
Constructions cannot be compared for agreement, so VOI does not apply; the set's free check is the model's own verify(). Precision of a
passing verify(): Qwen3-8B 27% (15 / 55), gpt-oss-20b 67% (60 / 89), gpt-oss-120b 81% (115 / 142). Own-verify ladder (construction
accepted if verify() passes, else think-then-program) vs think alone, utility at 0.5: Qwen3-8B 8.4 vs 7.3 (14.7% vs 14.1%), gpt-oss-20b
28.9 vs 21.1 (31.1% vs 23.4%), gpt-oss-120b 49.1 vs 45.3 (50.7% vs 46.8%). The check pays in proportion to its precision.

## Amendment 7 (2026-11-22 19:4x UTC, before running): calibrate on labelled problems of the same kind, apply to fresh ones
The calibration diagnostic says hard sets need labels; fresh Euler had only 25 per half. Test: fit the model (same D by BIC, all 120
Project Euler dev problems, semi-supervised with 100% labels, then also label-free for comparison) and run the policy on the 50 fresh
943–992 problems, whose labels are never used. VOI-transfer − {best single source, SC@3, label-fitted ladder transferred the same way},
utility at 0.5, clustered bootstrap, Holm over three (poc/voi_transfer.py).
- *Amendment 7 result (2026-11-22 19:4x UTC, poc/voi_transfer.py):* calibrating on all 120 labelled dev problems does not rescue fresh Euler:
  VOI-transfer 16.0% @ 23.9k, U 4.1 vs the best single source 14.0% @ 10.4k, U 8.8: −4.76 [−7.85, −0.27]; it beats SC@3 (+5.3) and ties
  the transferred ladder (−2.3 [−7.1, +4.0]). The fresh problems are much harder than dev (best single 14% vs 38%), so dev's
  calibration over-states fresh accuracy as well. Not shown.

## Amendment 8 (2026-11-22 20:4x UTC, before running): confirm the word-problem win on problems no decision has seen
The one claim set VOI won (word problems, held-out pool) has been looked at by every earlier word-problem decision. PREREG_FRESH's 300
fresh OptMATH-Train problems already have the same four sources stored (Qwen3-8B / gpt-oss-20b own program freef and thinkfree, 3 seeds),
never used by VOI. Test: python3 poc/voi.py words --fresh (v2, frozen settings), VOI − {our cascade (gpt-oss-20b), SC@3 gpt-oss-20b
think, label-fitted ladder}, utility at 0.5, clustered bootstrap, Holm over three. Prediction: VOI ≥ each (as on the held-out pool).
- *Amendment 8 result (2026-11-22 20:4x UTC):* **the word-problem win does not replicate on fresh problems.** VOI 82.7% @ 6.5k, U 79.4; our
  cascade (gpt-oss-20b) 83.3% @ 3.7k, U 81.5: −2.06 [−4.27, +0.12]; SC@3 −0.28 [−2.01, +1.31]; label-fitted ladder −0.09 [−2.73, +2.63].
  Not shown. On easier fresh problems (best single 78%) the fixed cascade's cheap agreement already captures what VOI's extra samples buy.
