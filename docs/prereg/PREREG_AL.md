# Pre-registration AL: a label-efficient pilot — label only the problems where the candidate policies' answers differ

Written 2026-10-31 10:4x UTC, before any pilot regret below has been computed: the simulator (`poc/analyze_al.py`) was smoke-tested on
label-free quantities only (the share of problems where the menus' answers differ, the exactness count); no regret was printed.
Results go below.

**Why it could change the claim.** The project's rule is that labels do not pay for choosing a policy: over 81 cells a 30-label pilot
loses 1.2–2.0 utility points to each cell's best by selection noise, more than the no-label default (PX, PX2, SQL-1), and 100 labels
are needed to get within 0.25–0.82. XPEER makes this the bottleneck of the recipe: which peer makes the cascade pay is a property of
the model pair and the task (gpt-oss-20b is the best peer for Qwen3-8B on word problems in exploration and the worst on SQL, XPEER-C),
neither lineage nor accuracy predicts it, and a +1 utility difference needs 500–1,500 random labels (XPEER power note). If 30 labels
can be placed so that they do the work of a few hundred, the pilot becomes the way to choose the peer and the policy, and the claim
"labels are only for telling contest-like tasks" changes.

**Theory.** On a task with an exact grader, two policies that give the same final answer on a problem are equally right on it. So the
accuracy differences among a menu of policies live only on the problems where some of their answers differ — share p of a pool of
unlabelled problems on which the arms have been run, known without labels — and the token costs are known without labels everywhere.
For two policies with per-problem correctness difference Δ_i ∈ {−1, 0, 1} (0 wherever the answers agree), k random labels estimate
mean Δ with variance ≈ E[Δ²]/k = p·E[Δ² | differ]/k; k labels drawn from the differing problems estimate it as p × their mean, with
variance ≈ p²·E[Δ² | differ]/k. The ratio is p: k targeted labels are worth k / p random ones, capped by the pool (labelling every
differing problem of a pool of M equals labelling all M). Exactness holds in the stored rows: 0 of 83,292 equal-answer pairs differ in
correctness (smoke test). Label-free shares p (problems, three seeds pooled): word problems, peer menu 14–52% of a cell (mean 33%),
broad menu 28–78% (mean 54%); SQL, peer menu 22%, broad 39–47% (Qwen3-8B; the others computed with the results). So the predicted gain
is 2–4.5× in effective labels: 30 targeted labels ≈ 60–140 random ones, where PX measured regret 0.25–0.82 at 100.

**Prior work (IDs opened 2026-10-31).** Choosing between two text generators by annotating the instances where their outputs differ,
clustered by the embedded difference (DiffUse, 2402.07891, ACL 2024); Bayesian active selection among a pool of classifiers from their
consensus and disagreement (CODA, 2507.23771, ICCV 2025); unbiased label-efficient test-loss estimation by importance sampling (Active
Testing, Kossen et al., 2103.05331, ICML 2021). **New here:** the menu is token-priced cascades that share their arms, so the
differing set is computed exactly from the arms' answers and the cost side needs no labels; the estimator is exact on the rest of the
pool because the grader is exact; and the target is the project's policy and peer choice, judged against the no-label default.

**Run (offline, stored rows; `python3.11 poc/analyze_al.py --word --sql`, results/al.txt).** Cells: word problems = 4 models
(Qwen3-8B, Qwen3-14B-AWQ, Qwen3.5-9B, Nemotron-3-Nano) × 4 benchmarks (OptiBench's third, BWOR, LogiOR, OptMATH; 82–202 problems);
SQL = 3 models (Qwen3-8B, Qwen3-14B-AWQ, Qwen3.5-9B) × 2 sets (BIRD dev 1,530, SQL-PA's fresh BIRD-train ~1,330). A problem's value
for a policy is its mean over the three seeds (one label grades every seed). Menus: word **peer** = {D = SB→T→T, N → the Qwen peer →
D, N → gpt-oss-20b → D, PND (gpt-oss-20b also checks SB's program)}, **broad** = peer + {T→T, N→T→T}; SQL **peer** = {D, N → p → D
for p in the two other Qwen models, Nemotron-3-Nano, gpt-oss-20b}, **broad** = peer + {T→T, N→T→T}. Pilots, k ∈ {10, 30, 100}:
**R** (PX's: the best utility on k random labelled problems, their tokens), **RP** (k random labels for accuracy, tokens from the
pool), **TG** (k labels uniform among the pool's differing problems, all of them if fewer; tokens from the pool). Primary: split-half
— each pilot's pool is a random half of the cell and it is scored on the other half (regret = that half's best utility − the pick's
there); secondary: in-sample (pool = scored set = the cell, PX's way). 1,000 pilots per cell; utility = accuracy − 0.5 × ktokens.
Also: always D.

## Predictions (split-half, k = 30, mean regret over cells)

- **AL-P1 (word, peer menu, 16 cells):** TG ≤ 0.75 × RP, and TG < RP in at least 12 of 16 cells.
- **AL-P2 (SQL, peer menu, 6 cells):** TG ≤ 0.75 × RP, and TG < RP in at least 5 of 6 cells.
- **AL-P3 (labels beat the default for the peer choice):** word peer menu, TG < always D.
- **AL-P4 (broad menus):** TG < RP on both tasks (mean over cells).
- **AL-P5 (fresh cells, when the XPEER lanes land):** Qwen3-8B and Qwen3-14B-AWQ on OptiBench's other 403 problems and on MAMO
  (`--fresh q8b:q8bob,q14a:q14aob --mamo`, word menus): TG < RP at k = 30 in at least 3 of the 4 cells (peer menu).
- Reported: R, k = 10 / 100, in-sample, p per cell, the best policy per cell, the exactness count.

## Decision

- P1 and P2 hold → the claim about labels changes: k labels placed on the problems where the candidates' answers differ do the work of
  about k / p random ones; the recipe's pilot becomes the targeted pilot (run the candidate arms on an unlabelled pool, label up to 30
  of the problems where they disagree, pick the best utility) and the XPEER power note is restated with its regret (PROJECT, REPORT,
  PROPOSAL). With P3, labels pay again over the no-label default for the choice of the peer on word problems.
- P1 or P2 refuted → the variance argument does not carry to regret at these menus (reported with p and the per-cell numbers); the
  no-label default stays the rule.
- P5 refuted while P1 holds → the gain is a property of the cells it was derived on (reported).

Expected (not a rule): P1 holds (TG/RP ≈ 0.6), P2 holds (≈ 0.5), P3 inconclusive (the default is the best word policy in about half
the cells), P4 holds, P5 holds.
