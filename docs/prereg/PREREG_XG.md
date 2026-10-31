# Pre-registration XG: the peer cascade with a generator from another family (gpt-oss-20b) on text-to-SQL and tool calls

Written 2026-10-31 18:4x UTC, before any of gpt-oss-20b's SB or T rows on BIRD or BFCL exists (two smoke jobs on 16 BIRD and 18 BFCL items under
separate tags, `oss20smk` / `oss20smk2`, checked formats; they are not part of the results). Known before writing: gpt-oss-20b's
low-effort quick queries on BIRD (XPEER addendum C, where it served as a peer: tags oss20 / oss20pa, graded) and every Qwen row.

**Purpose (the goal: exactly right answers with the fewest tokens).** The SQL and tool-call claims rest on three Qwen generators
(Qwen3-8B, Qwen3-14B-AWQ, Qwen3.5-9B); the review (docs/notes/CRITIQUE.md, 10-31, point 7) found no generator from another family.
If the cascade N → free check → a peer's quick answer agrees → N, else SB→T→T, is a Qwen property, the claim must say so. gpt-oss-20b
(OpenAI, one RTX 3090) is the other family the project runs end to end, and its cheap mode is different in kind: a low-effort think,
not a non-thinking answer (LC-OSS, PREREG_LC.md). **Prior work (checked 2026-10-31 18:2x UTC):** semantic-agreement cascades across model families
(Soiffer, Kolawole, Smith, EMNLP 2025 Industry, arXiv 2509.21837) defer on disagreement among small models without an execution check
and without SQL or tool calls; ABC (2407.02348); studies of gpt-oss's effort levels (model card 2508.10925; 2609.01867) compare
efforts, not an effort cascade gated by a check and a peer. No study found runs a low-effort → medium-effort cascade of gpt-oss behind
a free execution / schema check and a cross-family peer.

**Cells (4).** BIRD dev (1,530 questions after the gold filter), SQL-PA's 1,338 fresh BIRD-train questions, BFCL single-turn non-live
and live (TC-1 items); seeds 1–3. Generator gpt-oss-20b: N = low effort, the quick answer (SQL-1 / TC-1 prompts; on BIRD the stored
XC rows, chat endpoint, 2k cap including its reasoning); the default D = SB→T→T with SB = the medium-effort think cut at 2,000 tokens
and the final channel forced (`harmony_budget_chat`, as LC-OSS; 2k answer cap), T = the medium-effort think (the model's default;
16k cap), the retry T at the next seed (as for Qwen). On BFCL every arm is rendered by hand and answers in the forced final channel
(N: low effort, reasoning capped at 2,000; T: medium, capped at 16,000; SB as above): through the chat endpoint the smoke's quick and
thinking replies came back with empty content on 13 / 18 and 12 / 18 items. Diagnosis (second smoke, `poc/diag_oss_tc.py`, low effort,
6 items): on the 5 that need a call the reasoning ends by announcing it ("Need to call calculate_triangle_area.") and neither a final
message nor a parsed tool call follows (the model routes calls to its tool channel, which prompt mode does not declare); forced into
the final channel, every arm wrote calls in BFCL's format on all 18 smoke items (N 83%, T 78%, SB 72% right; seed 1, tag oss20smk2). No repair R and no "would thinking help?" answer S are run (gpt-oss has no
non-thinking mode to ask; D and the cascade use neither), so on SQL the failing N stay in (`analyze_cv.base(need_r=False)`).
Peers: Qwen3.5-9B (primary; the peer the method uses for the Qwen3 generators) and Qwen3-8B (reported), their stored quick rows.
Check, "same answer" (SQL: the same result rows of a passing query; BFCL: the same canonical calls of a passing reply), the default's
tokens, the peer's tokens paid on every passing N, and the utility 100 × right − 0.5 × ktokens exactly as `poc/analyze_breakeven.py`.

**Theory (written before the rows).** `analyze_breakeven` splits cascade − D exactly: accepting a right passing N instead of running
D gains G on average (100 × P(D wrong | N right, passing) plus D's tokens saved), accepting a wrong one loses L (100 × P(D right | N
wrong, passing) minus D's tokens), and the peer's accepts pay iff its TPR / FPR on passing N exceeds the break-even r* = (n_W / n_R) ·
(L / G), less the peer's and N's tokens (≈ 0.05). Known now, pooled over both BIRD sets: 58.3% of gpt-oss-20b's passing quick queries
are right (n_W / n_R = 0.71), and Qwen3.5-9B agrees with 79.1% of the right and 27.5% of the wrong ones (ratio 2.87; dev 74.9 / 22.7%,
fresh 83.8 / 33.0%) — the separation it has on Qwen3-8B's queries (pooled 82 / 29%, ratio 2.9), where the cascade gains +1.11. So the
cascade gains on SQL iff L / G < 2.87 / 0.71 ≈ 4.0, i.e. unless gpt-oss's medium think rescues far more of its wrong passing queries
than it breaks right ones. For the Qwen generators L / G is 2.6 (Qwen3-8B), 2.2 (Qwen3-14B-AWQ), 1.9 (Qwen3.5-9B): with
G ≈ 10, the bound is crossed only if D is right on more than about 40% of the questions where the passing quick answer is wrong (Qwen:
22–29%). The ratio here is on all passing N, but the gain is made in the decisive strata, RW (N right, D wrong) and WR (the reverse),
so the step needs the peer's ratio there to match the overall one. For the Qwen pairs (dry run of `analyze_xg.py`), decisive / overall
is 1.11, 0.99, 0.80 on SQL and 1.08, 0.98, 1.30 on BFCL. On BFCL the gap of D over N decides it: Qwen3-14B-AWQ's quick calls are 14.9
points below its default (r* = 4.9 > the peer's 4.0), and its cascade loses (−0.35 [−0.79, +0.10]); for Qwen3-8B (7.3 points) and
Qwen3.5-9B (11.6) it gains. gpt-oss-20b's BFCL rows do not exist yet, so for tool calls the theory gives only this condition.

**Predictions (paired 95% intervals over questions, seed means; utility).**
- **XG-P1 (SQL transfers):** BIRD dev and fresh pooled (≈ 2,868 questions), N → Qwen3.5-9B → D minus D: lower bound > 0.
- **XG-P2 (tool calls transfer):** BFCL non-live and live pooled (3,482 items), the same: lower bound > 0.
- **XG-P3 (the theory's step from all passing N to the decisive strata):** in each of the two pooled tasks, the peer's agreement
  ratio in the decisive strata (RW / WR) is within ±30% of its TPR / FPR on all passing N (as for the six Qwen pairs, 0.80–1.30).
- **XG-P4 (the sign follows the break-even):** in each pooled task, cascade − D has the sign of (peer TPR / FPR − r*) when the
  interval excludes 0 (with an inconclusive interval P4 is not scored for that task).
- Reported, no rule: per cell; the Qwen3-8B peer; accuracy and ktokens of N, D, T→T, N→T→T (check only) and the cascade; each
  cascade − D labelled dominance (accuracy not lower and tokens not higher, point estimates) or a trade with its break-even λ; the
  strata (π, G, L, a, r*); empty or capped replies per arm; models resident (gpt-oss-20b ≈ 13 GB + Qwen3.5-9B ≈ 18 GB: two 24 GB GPUs,
  against one for D) and sequential calls (N, then the peer, then D's one to three calls).

Power: the per-question SD of cascade − D for the Qwen generators is 15–17 (SQL, 2,867 questions) and 12–16 (BFCL, 3,482), so the
standard error is ≈ 0.3 and +1.0 is detected with power about 0.9, +0.6 with about 0.5.

**Decision rules.**
- P1 and P2 hold: the SQL and tool-call claims name two generator families (Qwen3 / 3.5 and gpt-oss), PROJECT / REPORT / PROPOSAL say
  so, and critique point 7 is closed for these tasks.
- One holds: the claim names the generator family per task, and the other task's strata say which term failed (π_WR / π_RW, the
  ratio, or tokens).
- Neither holds: the cascade is stated as measured on Qwen generators only; the break-even rule (cheap-first pays only when the
  check's accept ratio in the decisive strata exceeds r*), not the cascade, is the transferable statement, with gpt-oss-20b as the case
  where it predicts no gain.
- Any task with an upper bound < 0: the cascade is not the default for gpt-oss there, and the report names the condition.

Expected (not a rule): P1 holds or is inconclusive (+0.3 to +1.0: the separation matches Qwen3-8B's, D's rescue rate is the
unknown); P2 inconclusive (the BFCL sign depends on the gap of D over N, which ranged 7–15 points over the Qwen generators); P3 holds.

**Run.** gpt-oss-20b on one RTX 3090 per seed (`--max-model-len 24576`), one job per seed running, in order: SQL dev SB and T (tag
oss20), fresh SB and T (oss20pa), BFCL N (low effort) and SB / T (tag oss20), then the SQL grading; BFCL graded on the login node
(`grade_tc.py oss20`). Commands in docs/SLURM_HANDOFF.md. Analysis: `python3.11 poc/analyze_xg.py` (written before this file; dry run
on Qwen3-8B with `XG_A=q8b XG_PEERS=q35,q14a`).

## Results (written 2026-10-31 20:1x UTC; `results/xg.txt`; jobs 1289314–1289316, no failed request; fresh BIRD graded on a CPU node, 1289485)

gpt-oss-20b as the generator, Qwen3.5-9B as the peer; accuracy @ ktokens per question-seed (the peer's tokens counted):

| cell | N (low effort) | D = SB→T→T (medium) | T→T | cascade | cascade − D utility | accuracy | ktokens |
|---|---|---|---|---|---|---|---|
| BIRD dev | 53.0 @ 0.14 | 55.9 @ 0.53 | 55.8 @ 0.54 | 58.0 @ 0.60 | +1.99 [+1.32, +2.71] | +2.03 | +0.07 |
| BIRD-train fresh | 54.4 @ 0.11 | 58.3 @ 0.38 | 56.8 @ 0.37 | 59.6 @ 0.39 | +1.26 [+0.64, +1.91] | +1.27 | +0.02 |
| **SQL pooled** | 53.6 @ 0.13 | 57.0 @ 0.46 | 56.3 @ 0.46 | 58.7 @ 0.50 | **+1.65 [+1.20, +2.14]** | +1.67 | +0.05 |
| BFCL non-live | 88.0 @ 0.06 | 90.9 @ 0.22 | 90.4 @ 0.21 | 91.6 @ 0.18 | +0.74 [+0.20, +1.31] | +0.73 | −0.04 |
| BFCL live | 76.4 @ 0.05 | 80.0 @ 0.23 | 79.5 @ 0.23 | 81.0 @ 0.22 | +1.03 [+0.63, +1.45] | +1.03 | −0.01 |
| **BFCL pooled** | 80.5 @ 0.05 | 83.9 @ 0.23 | 83.4 @ 0.22 | 84.8 @ 0.21 | **+0.93 [+0.62, +1.26]** | +0.92 | −0.02 |

- **XG-P1 holds** (SQL +1.65 [+1.20, +2.14]); **XG-P2 holds** (BFCL +0.93 [+0.62, +1.26]).
- **XG-P3 holds:** decisive-strata ratio / all-passing ratio 3.48 / 2.87 (SQL, +21%) and 3.09 / 3.32 (BFCL, −7%).
- **XG-P4 holds:** peer TPR / FPR above r* in both tasks (SQL 2.9 vs 1.17; BFCL 3.3 vs 1.24) and both gains positive.
- Labels: on BFCL dominance in every cell (more accurate, fewer tokens); on SQL a trade only in name: the cascade pays 0.05k more
  tokens for 1.67 points, so it loses only above λ = 36.6 points per 1k tokens (73 times the utility's price).
- Peer Qwen3-8B (reported): SQL +0.81 [+0.30, +1.31], BFCL +1.58 [+1.20, +1.98]; every cell positive, the fresh SQL questions
  inconclusive (+0.32 [−0.40, +1.04]).
- Theory: the unknown was D's rescue rate on the wrong passing quick queries; it is L ≈ 15.6 (D right on about 16% of them,
  Qwen generators 22–29%), so L / G = 1.6, far under the bound of 4.0. gpt-oss's medium think adds little over its low effort on
  SQL (+3.4 points; Qwen 6.5–11) and BFCL (+3.4), so WR is barely larger than RW (SQL 518 vs 428 question-seeds), and the peer
  accepts 52% of RW against 15% of WR: +224 − 78 = +146 question-seeds, the +1.7 points of accuracy.
- Arms: SB's think reached the 2,000 cut on 83 / 4,602 dev and 4 / 4,014 fresh question-seeds; capped or empty SQL replies ≤ 1 per
  arm. On BFCL, empty final messages (no call) are almost all irrelevance items, where no call is right (N 22 / 22, T 322 / 331,
  SB 337 / 345); 8–9 call-needed items per arm got an empty answer.
- Raw reading (BIRD dev seed 1, the first 5 question-seeds where gpt-oss's quick query is wrong, the default right and Qwen3.5-9B
  returns the same rows): the shared errors are typical shortcuts — COUNT(*) over a join where the question counts distinct
  entities (1283, 1052; 199 counts atoms, not molecules), an extra count column next to the asked-for id (250), and "didn't have any
  publisher" read as NULL against the evidence's publisher.id = 1 (799). The medium think writes COUNT(DISTINCT …) and follows the
  evidence.
- Models resident: gpt-oss-20b (≈ 13 GB) + Qwen3.5-9B (≈ 18 GB), two 24 GB GPUs against one for D; sequential calls N, the peer, then
  D's one to three on a rejection.

**Decision (as pre-registered).** P1 and P2 hold: the SQL and tool-call claims name two generator families, Qwen3 / 3.5 and gpt-oss
(PROJECT, REPORT, PROPOSAL), and critique point 7 is closed for these tasks. The break-even rule predicted the sign in both (P4), and
the step from all passing answers to the decisive strata held within 21% (P3): the peer's ratio on passing quick answers, measurable
with N's labels alone, sufficed here.

## Addendum W: the word problems, offline (written 2026-10-31 20:1x UTC, before `analyze_xg.py --word` has been run on gpt-oss-20b)

**Why.** The word-problem peer claim was measured in one direction only: Qwen3-8B answering, gpt-oss-20b checking (XPEER). gpt-oss-20b's
own word-problem arms are stored (HO-OSB: N = low effort, SB = medium effort cut at 2,000, T = medium; OptiBench third, BWOR,
LogiOR; no OptMATH think), so the reverse direction needs no run: gpt-oss-20b answering, Qwen3.5-9B's stored quick program as the
check (Qwen3-8B reported). Cascade, default (SB→T→T), "same answer" (both pass and print the same value) and utility as XPEER
(`analyze_hopa.policies`, `same_word`); 376 problems × 3 seeds.

**Known now (N's labels and the peer's agreement only; no default outcome read).** 75.4% of gpt-oss-20b's passing low-effort
programs are right (n_W / n_R = 0.33); Qwen3.5-9B agrees with 77.7% of the right and 40.2% of the wrong ones (ratio 1.94; OptiBench
1.54 with 55% of wrong programs confirmed, BWOR 4.78, LogiOR 29.7), so the cascade gains iff L / G < 5.9 (Qwen3-8B as peer: 1.89, < 5.8).
Unlike SQL, gpt-oss's think is worth much on the hard sets (HO-OSB: the 2k think first +6.5 / +8.3 points over low effort first on
BWOR / LogiOR), so L is large there, while G carries the default's 2–6k tokens saved per accepted program.

**Predictions.**
- **XG-W1:** N → Qwen3.5-9B → D minus D, pooled over the three sets: lower bound > 0.
- **XG-W2:** its sign follows the break-even (peer TPR / FPR vs r*), scored only if the interval excludes 0.
Power: with 376 problems the interval is about ±1.8 wide, so only a gain above ~+1.8 is likely to show. Expected (not a rule):
inconclusive, positive point estimate (OptiBench carries 54% of the problem-seeds and its default is only 3 points above low effort).

**Decision.** W1 holds: the word-problem claim states the peer check in both directions (a gpt-oss answer checked by a Qwen quick
program). Upper bound < 0: the word-problem peer check is direction-specific and the claim says so. Otherwise: reported, no change.

### Results, addendum W (written 2026-10-31 20:1x UTC; `results/xg_word.txt`)
gpt-oss-20b answering, pooled over 376 problems × 3 seeds: N 57.5% @ 0.67k, D 70.9% @ 3.43k, T→T 69.5% @ 4.28k; the cascade with
Qwen3.5-9B 70.9% @ 4.14k, cascade − D −0.36 [−1.08, +0.38] utility: **XG-W1 refuted (not shown)**; XG-W2 not scored. Qwen3-8B as the
peer: 70.8% @ 3.95k, −0.35 [−0.85, +0.20]. Per set (Qwen3.5-9B): OptiBench third 76.7% @ 2.18k vs 76.9% @ 2.26k, BWOR 66.7% @ 5.39k vs
67.1% @ 3.93k, LogiOR 62.0% @ 7.35k vs 61.2% @ 5.54k. The accept decisions gain as the break-even said they would (peer ratio 2.4 >
r* 1.94: +0.39), and the costs take it back: the peer's quick program (0.42 utility, ≈ 0.8k tokens) and N's (0.34) cost as much,
because gpt-oss's default is short (3.4k against Qwen3-8B's 9.1k on the same sets) and accuracy-neutral here. Decision (as
pre-registered): reported, no change; the word-problem peer claim stays in its measured direction (a Qwen answer checked by
gpt-oss-20b), and the break-even's cost terms are what close the reverse one.
