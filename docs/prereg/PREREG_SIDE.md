# PREREG_SIDE: the second track's feasibility tests (written 2026-11-03 19:0x UTC)

The project's second track is for a teammate with an algorithms background who does not train or prompt models: algorithmic components
that plug into the existing cascade and verifier code, run on CPU, and are measured by the same pre-registered analyses. Each side
project gets one decisive test here before the teammate invests in it. Three earlier dev-set checks (SQL sub-database agreement, number
provenance in optimization programs, template reuse) found no room (FINDINGS 2026-11-03, exploratory).

## SIDE-W: does a distinguishing sub-database ("witness") help the pairwise SQL verifier? (written 2026-11-03 19:0x UTC, before any witness-prompt training step or score; witnesses being computed by CPU jobs 1311209 / 1311210, no label used by them)

**Why.** On SQL the room is at the fallback: two or three passing quick queries that return different rows (RV / RV2: +5 to +6
points if the right one were always chosen). PREREG_LCM B showed the cascade is at the information limit of its five calls, and B2 / J
that more quick queries or a 9B judge do not add information: the gain needs a new kind of signal. SEL-PW's pairwise verifier (AUROC
0.78–0.84, bound +1.7 to +3.2 of the room) sees each query and its first five result rows on the real database. It does not see *why*
the results differ: an aggregate over thousands of rows (50.0 vs 100.0) does not show which rows one query counts and the other does
not. A witness does: a small subset of the real database on which the two queries still return different row sets, with both results
on it. Finding it is a classic algorithm (delta debugging) and costs no model tokens.

**Related work.** Li & Xie 2024 (arXiv 2401.02115) sample ≤ 5-row databases from the real one and have GPT-4 predict each query's
expected result (Spider dev, +2.0 to +3.6 EX). DPC (2604.15163, ACL 2026) has LLM agents synthesise a "minimal distinguishing database"
and decides with a Python solution written by the model (+1.0 to +2.2 over self-consistency on BIRD mini-dev and Spider, ~3.8k tokens
per question). XData (Chandra et al., VLDB J. 2015), Cosette (Chu et al., CIDR 2017) and VeriEQL (He et al., OOPSLA 2024) build
counterexample databases by constraint solving to show two queries differ. None trains a verifier to read an algorithmic witness, and
none holds the candidates, backbone, data and loss fixed while adding the witness.

**Witness** (`poc/sql_witness.py`). For each unordered pair of distinct passing queries: the tables either query names are copied into
TEMP tables from their DDL (they shadow the real tables, so the queries run unchanged), filled with a deterministic row sample that grows
1/4096 → 1/512 → 1/64 → 1/8 → all until the results differ, with declared foreign keys closed (orphans removed to a fixpoint); then
ddmin's complement steps delete row ranges while the two results still differ as row sets and each keeps what the free check and a
reader see on the real database (non-empty; NULL cells or not). It stops at a 1-minimal witness or after 600 tests / 120 s ("budget").
Pairs whose difference vanishes once the keys are closed (the real database has orphans that make the difference) get a second pass
without the closure (`WIT_FK=0`). The prompt (`sql_witness.wtext`, after SEL-PW's two queries and results, before the question "Which
query answers the question? Reply A or B."): "A small part of the database on which the two queries return different results:", each
table with the columns either query names (else its first three) and up to 12 rows, values cut at 40 characters, then each query's
result on these rows (up to 5 rows). A pair without a witness keeps SEL-PW's prompt.

**Verifier.** SEL-PW's recipe with only the prompt changed: Qwen3-8B + LoRA r 16 (`cv_train.py pw`), SEL-PW's pool (`cv/selpw/pool.jsonl`;
1,320 BIRD-train questions with a right and a wrong passing result; witnesses for all 9,544 (right query, wrong query) combinations),
up to 4 pairs per question and epoch in both orders, batch 16, lr 5e-5, 2 epochs, adapters every 25 steps. Checkpoint: the highest
pooled within-question AUROC on the fresh held-out-database questions (`lcm_shift.py --sel-val-pw`, as SEL-PW). Reported, not decided:
SEL-PW's own s150 adapter with the witness prompt (no training on it, `selwitz`) and the untrained model with it.

**Cells and comparison.** SEL-PW's six: BIRD dev, Spider test, Spider dev × N base (Qwen3-8B) or trained (C1); P = Qwen3.5-9B; SB, T =
Qwen3-8B. Reference: SEL-PW's s150 without the witness on the same question-seeds (`SEL_PW_REF=selpw_s150 lcm_shift.py --sel-pw
<choice>`; the self-comparison gives 0.000 everywhere, checked 19:0x UTC). Output tokens unchanged; prefill reported.

**Predictions** (paired 95% intervals over questions):
- **SIDE-W-P1 (the witness separates better):** witness − SEL-PW within-question AUROC, three targets pooled, lower bound > 0 for both N
  types.
- **SIDE-W-P2 (decision):** witness selector − SEL-PW selector, three targets pooled per N type: lower bound > 0 for at least one N type
  and upper bound < 0 for none.
- **SIDE-W-P3 (mechanism):** on BIRD dev's (right, wrong) pairs, the ordering gain on pairs with the same number of output columns is at
  least the gain on pairs whose columns differ (the witness explains content differences; column-count differences are already
  visible), and ≥ +2 points with lower bound > 0.
- **SIDE-W-P4 (coverage):** a witness (1-minimal or budget) for ≥ 90% of the target pairs, median ≤ 6 rows.
- Expected: AUROC +0.00 to +0.04 (the verifier may already infer much of the difference from the first rows); choice −0.2 to +0.6; P2
  is uncertain. Coverage: the first 115 target pairs gave 102 1-minimal witnesses (median 3 rows) and 13 whose difference needs orphans.

**Decision.**
- P1 and P2 hold → the witness is the new signal SQL's fallback needed: the witness verifier replaces SEL-PW's at the fallback (PROJECT,
  REPORT, PROPOSAL updated), and the teammate's side project B is better witnesses, measured by this pipeline: constructed
  counterexamples (constraint solving, as VeriEQL) where the real data has none or only large ones, and the most readable witness among
  the 1-minimal ones.
- P1 holds, P2 refuted → the witness separates better but not enough to change the choice among two or three answers; stated, and the
  side project is scoped to the stratum P3 points at.
- P1 refuted → a trained 8B pairwise verifier gains nothing from a sub-database witness; side project B closes (constructed witnesses
  would add information only where the real data lacks a small witness, a minority by P4).
