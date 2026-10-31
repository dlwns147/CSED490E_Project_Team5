# Pre-registration EXT: the cascade's peer check against the standard in-model confidence gate and against agreement alone

Written 2026-10-31 16:3x UTC, before any confidence score of the rows below exists (the scoring job, `poc/score_conf.py`, is submitted after
this file is committed). Known before writing: the peer's operating points and the break-even of every cell below
(`poc/analyze_breakeven.py`, already in FINDINGS 10-31), and C1 (10-13): on geometry programs, mean token log-prob separates right
from wrong programs with macro AUROC 0.66–0.69 on clean prompts and points the wrong way where the wrong program is the typical one.

**Purpose (the goal: exactly right answers with the fewest tokens).** The cascade that carries the SQL and tool-call claims is
N (non-thinking answer) → free check → a second model's N gives the same answer → keep N; else the default SB→T→T. The review
(docs/notes/CRITIQUE.md, 10-31 15:2x, points 3 and 6) found two gaps: the claim has been compared only with our own baselines, and
the second model is a deployment cost (a second resident model) that the utility does not count. The standard alternative needs no
second model: gate on the model's own token confidence (Gupta et al., ICLR 2024, arXiv 2404.10136; quantiles of token log-probs as
deferral features). Agreement without any execution check is ABC (Kolawole et al., arXiv 2407.02348); semantic agreement across
models is reported to beat token confidence as a deferral signal (Soiffer, Kolawole, Smith, EMNLP 2025 Industry, arXiv 2509.21837);
Zellinger & Thomson (TMLR 2025, arXiv 2501.09345) model the dependence of successive models' confidences with copulas. No paper we
found tests confidence and agreement together behind a free execution check, or with the stratified break-even.
Each outcome changes something: if confidence matches the peer, the cascade drops the second model; if it adds to the peer, the
method gains a filter; if neither, the peer is justified against the standard baseline, and the report says so with numbers.

**Cells (12).** A ∈ {Qwen3-8B, Qwen3-14B-AWQ, Qwen3.5-9B} with the pre-registered peers of HO-PA / SQL-PA (Qwen3-8B → Qwen3.5-9B,
Qwen3-14B-AWQ → Qwen3.5-9B, Qwen3.5-9B → Qwen3-8B) on BIRD dev (SQL-1 rows), the 1,338 fresh BIRD-train questions (SQL-PA rows), and
BFCL single-turn non-live and live (TC-1 rows); 3 seeds each; items, filters, the free check, "same answer", the default SB→T→T and
the utility (100 × right − 0.5 × ktokens, the peer's tokens counted) exactly as `poc/analyze_breakeven.py`. Word problems are
left out (their prompts carry a per-seed library fact).

**Confidence (no new samples).** Every stored N answer is teacher-forced under A after its exact prompt; the log-prob of each answer
token and of the end-of-turn token (vLLM prompt_logprobs, raw). Score c = mean log-prob over the answer tokens and the end token
(primary; length-normalised as in 2404.10136); secondary scores: the 10% quantile and the minimum of the same log-probs.

**Gates (each one: a failed check or a rejection → the default SB→T→T; N's tokens always paid).**
- PEER: as HO-PA (accept when the peer's N passes and gives the same answer; the peer's tokens paid on every passing N).
- CONF@r: accept the passing N whose c is in the top share r of the cell's passing N (pooled over seeds), r = the share PEER accepts
  in that cell. No labels, no second model; equal accept rate isolates which signal ranks better.
- CONF*: accept passing N with c ≥ τ; τ (grid: the 0, 5, …, 100% quantiles of the cell's passing c) maximises the cascade's utility
  on one half of the questions (crc32(id) mod 2) and is applied to the other half, both ways. Uses labels; an upper bound for a
  tuned confidence gate.
- AND20 (label-free): PEER and c above the 20% quantile of c among the cell's agreeing N.
- AND*: PEER and c ≥ τ′, τ′ tuned on the other half as CONF* (grid: quantiles of c among agreeing N).
- ABC: accept when A's N and the peer's N give the same answer, with no free check (SQL: the same result rows from two queries that
  ran without error, empty results included; BFCL: the same canonical calls, schema-valid or not).

**Measures.** Per cell: each gate − PEER in utility (paired 95% intervals over questions, seed means); the AUROC of c for right vs
wrong among passing N, and among passing N the peer agrees with (conditional); the peer's (FPR, TPR) against c's ROC; per gate the
accept rates in the two decisive strata (RW: N right, default wrong; WR: N wrong, default right).

**Theory (written before the scores).** The peer's operating points (TPR 72–84%, FPR 18–39% on right vs wrong passing N) correspond,
for an equal-variance binormal score, to d′ = z(TPR) − z(FPR) ≈ 1.2–1.6, AUROC ≈ 0.80–0.87. A score with C1's AUROC (≈ 0.68, d′ ≈ 0.66)
at the peer's FPR (≈ 0.28) has TPR ≈ Φ(0.66 − 0.58) ≈ 0.53, against the peer's ≈ 0.78; at equal accept rate that moves ≈ 10% of
passing N from accepted-right to accepted-wrong, about −1.5 to −3 utility (G ≈ 10, L ≈ 20–60 from the break-even table). Confidence
would need AUROC ≳ 0.83 among passing N to match the peer. Mechanism for the combination: the wrong answers a different model
reproduces are the typical ones (shared mistakes, arXiv 2502.04313; HO-PA's error coincidence), and C1 found confidence measures
typicality, so among agreeing answers confidence should separate right from wrong less well than overall.

**Predictions (each "in k of 12 cells").**
- EXT-P1: c's AUROC among passing N lies in [0.60, 0.82] in ≥ 9 of 12, and the peer's point lies above c's ROC (c's TPR at the
  peer's FPR is lower) in ≥ 9 of 12.
- EXT-P2: PEER − CONF@r has lower bound > 0 in ≥ 6 of 12 and upper bound < 0 in none.
- EXT-P3: the conditional AUROC (among agreeing passing N) is below the unconditional one in ≥ 9 of 12.
- EXT-P4: AND* − PEER has lower bound > 0 in ≤ 2 of 12; AND20 − PEER has lower bound > 0 in ≤ 2 of 12.
- EXT-P5 (non-inferiority, margin 0.5 utility): PEER − CONF* has lower bound > −0.5 in ≥ 8 of 12.
- EXT-P6: |ABC − PEER| ≤ 0.3 utility in ≥ 9 of 12 (agreement on executed answers already contains most of the free check).

**Decision rules.**
- CONF@r − PEER lower bound > 0 in ≥ 4 cells, or CONF* − PEER lower bound > 0 in ≥ 5 cells: the in-model gate replaces the peer in
  those task types (one resident model); the abstract's cascade claim is restated as "a confidence gate", with the peer only where it
  wins.
- AND20 − PEER lower bound > 0 in ≥ 4 cells: confidence becomes a second label-free filter of the method (then tested on the fresh
  word-problem cells); AND* alone in ≥ 4 cells: a 30-label variant, reported as needing labels.
- Otherwise: the peer stays, and the report cites this test as the comparison with the standard in-model gate (2404.10136) and
  with agreement alone (2407.02348).
- ABC − PEER lower bound > 0 or upper bound < 0 in ≥ 4 cells: the free check's contribution beyond agreement is reported with its
  sign; within ±0.3 in most cells: the report says the check adds little once answers are compared by execution.

**Run.** `poc/score_conf.py` on one RTX 3090 per model (Qwen3-8B, Qwen3-14B-AWQ, Qwen3.5-9B), SQL dev, SQL train-fresh and BFCL,
3 seeds each (≈ 35k teacher-forced answers per model; a 20-row smoke of SQL dev first, read before the rest is used; the job
reports the share of answers that re-tokenize to the stored token count, where a gap is mostly whitespace the stored answers lost). Analysis: `poc/analyze_ext.py` (written after this file, before the scores are read).

## Results (written 2026-10-31 20:1x UTC; `results/ext.txt`; jobs 1288814 / 1288815 / 1288886, every stored N answer scored, 98.6–99.9% re-tokenize to the stored count; analysis on a CPU node)

Score c = mean log-prob (primary). Gate − PEER in utility (paired 95% intervals over questions, seed means):

| cell | AUROC passing / agreeing | peer TPR / FPR vs c's TPR at that FPR | CONF@r | CONF* (labels) | AND20 | AND* (labels) | ABC |
|---|---|---|---|---|---|---|---|
| BIRD dev, Qwen3-8B | 0.62 / 0.52 | 79 / 25 vs 42 | −3.19 [−4.23, −2.19] | −0.99 [−1.87, −0.14] | −0.31 | −0.05 | −0.57 [−0.92, −0.29] |
| BIRD dev, Qwen3-14B-AWQ | 0.66 / 0.61 | 78 / 28 vs 52 | −2.63 [−3.67, −1.66] | −1.09 [−1.98, −0.22] | −0.55 | −0.58 | −0.56 [−0.91, −0.26] |
| BIRD dev, Qwen3.5-9B | 0.72 / 0.64 | 75 / 25 vs 58 | −0.82 [−1.73, +0.10] | −1.25 [−2.13, −0.39] | −0.05 | −0.19 | −0.64 [−0.99, −0.34] |
| BIRD fresh, Qwen3-8B | 0.63 / 0.56 | 84 / 33 vs 49 | −2.66 [−3.86, −1.45] | −1.96 [−2.89, −1.02] | −0.31 | −0.05 | −0.44 [−0.78, −0.15] |
| BIRD fresh, Qwen3-14B-AWQ | 0.61 / 0.55 | 84 / 39 vs 57 | −2.57 [−3.66, −1.58] | −1.75 [−2.73, −0.78] | −0.64 | −0.00 | −0.36 [−0.66, −0.11] |
| BIRD fresh, Qwen3.5-9B | 0.68 / 0.60 | 77 / 39 vs 66 | −0.28 [−1.26, +0.72] | −0.36 [−1.46, +0.70] | +0.01 | +0.08 | −0.22 [−0.46, −0.03] |
| BFCL non-live, Qwen3-8B | 0.62 / 0.49 | 78 / 33 vs 56 | −1.23 [−1.96, −0.51] | −0.15 [−0.65, +0.42] | −0.02 | −0.19 | −0.05 [−0.16, +0.05] |
| BFCL non-live, Qwen3-14B-AWQ | 0.71 / 0.60 | 79 / 26 vs 65 | −1.26 [−2.21, −0.30] | +0.45 [−0.31, +1.17] | +0.58 [+0.17, +1.01] | +0.70 [+0.13, +1.29] | −0.08 [−0.21, +0.00] |
| BFCL non-live, Qwen3.5-9B | 0.68 / 0.54 | 87 / 27 vs 58 | −2.04 [−2.85, −1.24] | −2.90 [−3.71, −2.12] | −0.53 | −0.09 | −0.11 [−0.40, +0.17] |
| BFCL live, Qwen3-8B | 0.71 / 0.56 | 68 / 16 vs 54 | −0.08 [−0.75, +0.62] | −0.07 [−0.71, +0.60] | −0.07 | −0.10 | −0.21 [−0.44, +0.02] |
| BFCL live, Qwen3-14B-AWQ | 0.68 / 0.52 | 69 / 17 vs 52 | −1.04 [−1.85, −0.26] | +0.52 [−0.07, +1.12] | +0.06 | +0.48 [+0.05, +0.89] | −0.37 [−0.62, −0.12] |
| BFCL live, Qwen3.5-9B | 0.56 / 0.41 | 80 / 16 vs 40 | −4.11 [−4.99, −3.23] | −0.91 [−1.43, −0.38] | −0.24 | −0.00 | −0.28 [−0.52, −0.06] |

- **EXT-P1 holds:** AUROC in [0.60, 0.82] in 11 / 12 (BFCL live Qwen3.5-9B 0.56); the peer's point lies above c's ROC in 12 / 12 (c's
  TPR at the peer's FPR 40–66% against the peer's 68–87%). The theory's numbers held: median AUROC 0.67 (C1: 0.66–0.69), c's TPR at
  the peer's FPR ≈ 0.54 (predicted 0.53).
- **EXT-P2 holds:** PEER − CONF@r lower bound > 0 in 9 / 12; CONF@r better in none.
- **EXT-P3 holds:** the AUROC among agreeing answers is below the unconditional one in 12 / 12, and below 0.5 in two (BFCL non-live
  Qwen3-8B 0.49, live Qwen3.5-9B 0.41): among answers two models agree on, the more confident ones are not more often right.
- **EXT-P4 holds:** AND* better in 2 / 12, AND20 in 1 / 12 (all Qwen3-14B-AWQ on BFCL).
- **EXT-P5 holds:** PEER − CONF* lower bound > −0.5 in 12 / 12; even with labels, the tuned confidence gate is never better and is
  worse in 6 / 12.
- **EXT-P6 refuted:** |ABC − PEER| ≤ 0.3 in 6 / 12; ABC is worse in 8 / 12 (−0.22 to −0.64), better in none.
- Secondary scores (10% quantile, minimum) give the same picture (results/ext.txt).
- Raw reading (BIRD dev, Qwen3-8B seed 1, passing queries; c's 10th / 90th percentiles −0.043 / −0.0004). The 15 confidently wrong
  queries the peer rejects are short, typical forms with a column-set or filter mismatch the model is certain of: "which player is the
  tallest" answered with name *and* height; "cards that cost more" ordered without the MAX filter; the higher-reputation user returned
  with the reputation column. The 44 unconfident right ones the peer accepts are right queries that copy rare literals from the question
  ('fine, you win :)', 'Poland Ekstraklasa'): low token log-prob from copying, not doubt. Confidence measures how typical the tokens
  are, as C1 found on geometry.

**Decision (as pre-registered).** No gate replaces the peer (CONF@r better in 0, CONF* in 0), confidence is not added as a filter
(AND20 better in 1 of the required 4) or as a labelled variant (AND* in 2 of 4): the peer stays, and the report cites this test as the
comparison with the standard in-model gate (2404.10136) and with agreement alone (2407.02348). ABC is worse in 8 cells: the free check
adds 0.2–0.6 utility beyond agreement on executed answers, reported with its sign. The second resident model (critique point 3) is
the price of a check that confidence cannot replace on these tasks.
