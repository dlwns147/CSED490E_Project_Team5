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

## SIDE-ENV: does a generated environment reproduce BFCL's multi-turn regime? (written 2026-11-03 19:1x UTC, before any model ran on it; 40 scenarios generated, their ground truths replayed through BFCL's checker)

**Why.** The agent-loop results (MT-SEL; MT-SO running) are measured on BFCL v4's 8 environment classes, and the verifiers are trained
on the same classes. MT-SEL-ENV (PREREG_MT, running) holds out half of BFCL's classes, but they share BFCL's authors, style and
ground-truth conventions. A family of generated environments in BFCL's format, with ground truths computed by an algorithm, gives a
held-out test no verifier has seen, and is a self-contained algorithmic job for the second track (state machine, constraint policy,
resolver, scenario generator). This test decides only whether the first family is a valid test bed: whether it reproduces the regime
the methods were built for (thinking pays; failures exist that the environment does not show).

**Related work.** RandomWorld (Sullivan et al., EMNLP 2025, 2506.11045; code released) generates typed tools and single-instruction
trajectories for training, with tools whose outputs are memoised, not a shared mutable state over user turns. FuncBenchGen
(2509.26553) generates function-dependency DAGs to test multi-step calling; ToolSandbox (2408.04682) is stateful and conversational
but hand-written. None generates stateful multi-turn environments with algorithmic ground truth in BFCL's format.

**Environment** (`side/envs/package_manager.py`, `side/gen_pkg.py`, seed 0, 40 scenarios). A package manager: a random 3-layer
dependency DAG of 16 packages with 2–4 versions each, dependencies through windows of allowed versions; 6 functions (search_package,
list_installed, get_disk_space, install_package with as_dependency, remove_package, upgrade_package); a policy stated in every
function's description (missing dependencies first, newest version every needer allows, as_dependency=True; a named-version-free
install takes the newest installable version; removal also removes dependencies no longer needed; upgrade to the newest version every
dependent allows). Each scenario: an initial state from 2–3 policy installs, then 3 user turns drawn from install-version (29 turns),
install-newest (38), remove (46), upgrade (7); ground truth = the policy's mutating calls (3.04 per turn). Every call's result depends
only on the call and the state, so BFCL's checker accepts any order reaching the policy's state: the ground truths replay as valid in
40 / 40, one call per step 40 / 40, without as_dependency 0 / 40. Runs through the unchanged `run_mt.py` / `grade_mt.py`
(`MT_CLASSES=PackageManagerAPI=side.envs.package_manager MT_ITEMS=$POC_DATA/side/pkg_items.jsonl`).

**Runs.** Qwen3-8B (decides) and Qwen3.5-9B (reported), arms N, T, E, seed 1, as MT's (PREREG_MT; 20-step limit, 2,048 / 8,192-token
caps).

**Predictions** (anchored to BFCL's stored seed-1 rows of the same model: N 16.8%, T 29.7%, E 23.5%; 12.8% of N's failed
conversations show no visible failure, i.e. no error result, no repeated step, no force-quit):
- **SIDE-ENV-P1 (neither ceiling nor floor):** Qwen3-8B T right in [20%, 85%] (conversations).
- **SIDE-ENV-P2 (thinking pays):** Qwen3-8B T − N ≥ +5 points (point estimate; paired interval over the 40 scenarios reported).
- **SIDE-ENV-P3 (failures the environment does not show):** the silent share of Qwen3-8B's N failures ≥ BFCL's 12.8%.
- Reported: E between N and T as on BFCL; per turn kind, which requests fail.
- Expected: N 15–45%, T 35–75%, silent share 20–50% (a wrong version or a missing as_dependency returns no error).

**Decision.**
- P1–P3 hold → the family is a valid held-out test bed: next (pre-registered separately) the BFCL-trained MT-SEL verifiers score its
  turn-0 rollouts zero-shot, and the second track builds two more families through the same interface (`side/README.md`).
- P1 refuted at the ceiling → deeper DAGs and more conflicts (generator arguments), re-tested once on new seeds by the same rules; at
  the floor → fewer packages; P2 refuted → the family does not test what the methods are about (thinking does not change the outcome)
  and is redesigned; P3 refuted → the family tests only visible failures, where the free check suffices, and gets requests whose
  wrong plans run without errors.

## Results of SIDE-ENV (written 2026-11-03 19:4x UTC; jobs 1311251 / 1311252; rows `results/tc/mt_sidepkg_{q8b,q35}_{N,T,E}_s1.jsonl`, graded with `grade_mt.py`; raw-case replay `nlp_data/scratch/sidepkg_fail.py`; environment version 1 = commit 301ac98)

| model | N | T | E | silent share of N's failures |
|---|---|---|---|---|
| Qwen3-8B | 0 / 40 @ 0.20k | 1 / 40 @ 6.66k | 0 / 40 @ 2.65k | 5.0% |
| Qwen3.5-9B | 2 / 40 @ 0.32k | 0 / 40 @ 2.27k | 2 / 40 @ 0.82k | 18.4% |

- **SIDE-ENV-P1 refuted at the floor:** Qwen3-8B T 2.5%. **P2 refuted:** T − N +2.5 points. **P3 refuted:** 5.0% silent against
  BFCL's 12.8% (by the registered whole-conversation definition; see the raw cases).
- **Raw cases** (each trajectory replayed turn by turn against the policy's state; the first diverging turn):
  - 16–19 of 40 conversations first diverge at a removal. The model removes the named package and leaves its dependencies
    installed, against the policy's clean-up. This is a silent step.
  - 10–17 first diverge at an install that is right except for the as_dependency flag.
  - 1–4 diverge on a version choice and 1–2 on a missing dependency.
  - Thinking changes neither of the two main causes. The later errors in the registered definition ("already installed",
    "needed by") are downstream of a silent first divergence, which is why the silent share comes out low.
- Reading: the floor is two conventions that live only in the function docs, which no model follows with or without thinking. It is
  not the size of the graph, so the registered remedy for the floor (fewer packages) would not touch the cause. BFCL's own requests
  state what they imply ("Make sure to create the directory").

## SIDE-ENV-2: the same environment with every request stating its rule (written 2026-11-03 19:4x UTC, before any model ran on version 2)

**Change (the one retry SIDE-ENV allowed, aimed at the cause the raw cases show instead of the registered "fewer packages"):**
- No as_dependency flag and no record of what the user asked for.
- Every request states its rule in its own words:
  - install: "install its missing dependencies first, each at the newest version that every package needing it allows";
  - install-newest: "the newest version that can be installed without changing any installed package";
  - removal: "then remove every package it depended on, directly or indirectly, that no remaining installed package needs";
  - upgrade: "the newest version that every installed package depending on it allows".
- The policy left in the docs is only what the tools enforce.
- What remains for the model is the algorithm: the dependency closure, the intersection of allowed versions, the orphans after a
  removal.
- Generator seed 1, 40 scenarios: remove 58 turns, install-newest 34, install-version 18, upgrade 10; 2.98 ground-truth calls per
  turn.
- Ground truths replay as valid in 40 / 40, and in 40 / 40 with one call per step.
- Negative variants: without the clean-up 1 / 40 still valid; the requested package alone 4 / 40.

**Runs, predictions and decision:** as SIDE-ENV (Qwen3-8B decides, Qwen3.5-9B reported; N, T, E, seed 1; P1–P3 with the same
anchors). In addition, P3 is reported on the first diverging turn: its share with no error result and no repeated step.
- Expected: N 10–35%, T 30–65%.
- If P1–P3 hold, SIDE-ENV's "hold" branch applies.
- If not, the family is closed and SIDE-ENV's lesson is recorded: a generated environment has to state its conventions in the
  request. The second track then starts from another family through the same interface.

## Results of SIDE-ENV-2 (written 2026-11-03 20:4x UTC; jobs 1311368 / 1311369; rows `results/tc/mt_sidepkg2_{q8b,q35}_{N,T,E}_s1.jsonl`)

| model | N | T | E | T − N (paired 95%) | silent share of N's failures (registered) | first diverging turn silent, N / T |
|---|---|---|---|---|---|---|
| Qwen3-8B | 1 / 40 @ 0.22k | 7 / 40 @ 13.05k | 3 / 40 @ 3.66k | +15.0 [+3.8, +26.2] | 5.1% | 58% / 73% |
| Qwen3.5-9B | 2 / 40 @ 1.14k | 8 / 40 @ 11.47k | 1 / 40 @ 1.44k | +15.0 [+1.8, +28.2] | 73.7% | 82% / 53% |

- **SIDE-ENV-P1 refuted narrowly:** Qwen3-8B T 17.5%, below 20%.
- **P2 holds:** +15.0 against the +5 needed, with lower bound > 0.
- **P3 refuted by the registered definition:** 5.1%. Counted at the first diverging turn instead, 58% of Qwen3-8B's failures are
  silent. The registered definition counts the later "already installed" / "needed by" errors that follow a silent divergence.
- Qwen3.5-9B, reported only, would pass all three.
- **Raw cases (Qwen3-8B):** installs and upgrades now come out right in most turns (install 15–16 of 17–20, upgrade 7–8 of 8–9).
  Removal with clean-up is the bottleneck: 58 of 120 turns. N gets 2 of 36 reached removal turns right, T 11 of 38. Errors leave
  dependencies installed or, for Qwen3.5-9B, remove unrelated packages nothing depends on.
- **Decision (registered):** the package-manager family is closed. Thinking now pays (+15), but whole conversations are capped by
  the one request kind that makes up half of the turns.
- **Lessons carried to the next family** ():
  - state each rule in the request (version 1);
  - keep every request kind at no more than a third of the turns;
  - count silent failures at the first diverging turn. This replaces the whole-conversation definition, which counts downstream
    errors as visible.
