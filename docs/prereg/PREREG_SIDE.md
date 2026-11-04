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

## Results of SIDE-W (written 2026-11-04 02:2x UTC; job 1311549 `selwit`: training 166 steps, checkpoint, target scoring; `results/lcm_selwit.log`, `results/lcm_selwit_val.log`; the log's "pairwise" is the witness verifier selwit_s150, its "pointwise" the reference selpw_s150)

- **Coverage (P4) holds:** a witness for 7,124 of 7,239 target pairs (98.4%; 64 at the budget), median 3 rows (90th percentile 6).
  115 pairs got none; they keep SEL-PW's prompt.
- **Checkpoint:** selwit_s150, pooled held-out-database AUROC 0.785 [0.710, 0.853] (SEL-PW's s150: 0.811 [0.742, 0.879]).

| within-question AUROC, witness vs SEL-PW | BIRD dev | Spider test | Spider dev |
|---|---|---|---|
| N base | 0.837 vs 0.837 | 0.797 vs 0.804 | 0.832 vs 0.834 |
| N trained (C1) | 0.798 vs 0.791 | 0.790 vs 0.782 | 0.810 vs 0.827 |

- **SIDE-W-P1 refuted:** witness − SEL-PW AUROC, targets pooled: base −0.002 [−0.014, +0.009], trained +0.003 [−0.010, +0.016].
- **SIDE-W-P2 refuted:** selector, targets pooled: base +0.05 [−0.11, +0.20], trained −0.02 [−0.20, +0.18]; no lower bound > 0 and
  no upper bound < 0.
- **SIDE-W-P3 refuted:** BIRD dev (right, wrong) pairs with the same output columns +0.45 [−1.12, +2.04] points (1,510 pairs),
  different columns +0.05 [+0.00, +0.14] (551).
- **Reported:**
  - SEL-PW's s150 adapter shown the witness without training on it (selwitz): AUROC −0.014 [−0.027, −0.001] (base) and −0.009
    [−0.022, +0.005] (trained); selector +0.06 / +0.07, n.s.; same-column pairs −2.38 [−4.45, −0.50].
  - The untrained model with the witness prompt: held-out-database AUROC 0.471, chance.
- **Raw:**
  - The witnesses are right and readable. In BIRD dev 514 the witness shows the one banned card that only the query without
    `status = 'Legal'` keeps. In 1492 it shows a KAM customer without transactions, for whom the query that joins transactions
    returns NULL.
  - The verifier hardly moves with them. On the 14,248 requests with a witness its scores correlate 0.966 with SEL-PW's, and the
    preferred query flips in 9.4%. On the 230 requests without a witness, where the two prompts are identical, it flips in 13.0%:
    the witness changes the choice less than retraining does.
  - A witness adds a median of 119 prompt tokens.
- **Decision (registered):** P1 refuted → a trained 8B pairwise verifier gains nothing from a sub-database witness, and side project
  B closes. Constructed witnesses would add information only where the real data has no small witness, 1.6% of pairs by P4. The
  word-problem analogue (an LP difference shown to the verifier) is not started.

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
- **Lessons carried to the next family** (`side/README.md`):
  - state each rule in the request (version 1);
  - keep every request kind at no more than a third of the turns;
  - count silent failures at the first diverging turn. This replaces the whole-conversation definition, which counts downstream
    errors as visible.

## SIDE-ENV-3: a second family, a team calendar with rooms (written 2026-11-03 20:4x UTC, before any model ran on it)

**Why.** SIDE-ENV-2 closed the package manager. SIDE-ENV's question stands: can a generated family give the agent-loop methods a test
outside BFCL? This family is built with the three lessons:
- every request states its rule;
- each request kind is a third of the turns;
- silent failures are counted at the first diverging turn.
Its algorithmic core is interval scheduling: the earliest common free slot of several calendars and a room, and the meetings that
overlap a window.

**Environment** (`side/envs/team_calendar.py`, `side/gen_cal.py`, seed 0, 40 scenarios).
- **Tools (8):** find_meeting, get_schedule, get_room_schedule, list_rooms, book_meeting, move_meeting, cancel_meeting, block_time.
- **State:** 5 people, 4 rooms with capacities 2–8, 9–14 meetings over three days, 3–6 blocked times.
- **Each conversation has one turn of each kind**, in random order:
  - book: for 2–4 people, the earliest half-hour start when all are free, the smallest free room that fits, ties by name; a
    request whose answer is 09:00 with nobody busy is redrawn;
  - move: an existing meeting, found by title, to another day by the same rule;
  - cancel: a person's new appointment; cancel every meeting they attend that overlaps it, then block the time with the stated label.
- Ground truth: the rule's calls (1.37 per turn).
- Replay: valid 40 / 40, and 40 / 40 one call per step. Without the block 0 / 40 still valid; with the largest room instead of the
  rule's 0 / 40.

**Runs, predictions, decision:** as SIDE-ENV (Qwen3-8B decides, Qwen3.5-9B reported; N, T, E, seed 1). P1 is T in [20%, 85%]; P2
is T − N ≥ +5. P3 is the silent share of Qwen3-8B's N failures at the first diverging turn, ≥ 12.8%; the whole-conversation share is
reported too.
- Expected: N 10–40%, T 30–70%, silent share 40–80% (a later or wrong-room booking succeeds without an error).
- P1–P3 hold → SIDE-ENV's "hold" branch: the BFCL-trained MT-SEL verifiers score this family's turn-0 rollouts zero-shot, which is
  pre-registered next.
- Refuted → stated. The second track's environment work continues only through a family the teammate designs.

## Results of SIDE-ENV-3 (written 2026-11-04 00:2x UTC; jobs 1311813 / 1311814; rows `results/tc/mt_sidecal_{q8b,q35}_{N,T,E}_s1.jsonl`, graded with `grade_mt.py`; analysis `side/analyze_env.py`; raw cases `nlp_data/scratch/sidecal_raw.py`, `sidecal_err.py`)

| model | N | T | E | T − N right (paired 95%) | T − N utility | silent share of N's failures: first diverging turn / whole conversation |
|---|---|---|---|---|---|---|
| Qwen3-8B | 0 / 40 @ 0.66k | 6 / 40 @ 28.38k | 3 / 40 @ 15.77k | +15.0 [+3.8, +26.2] | +1.1 [−10.9, +13.1] | 12.5% (5 / 40) / 0.0% |
| Qwen3.5-9B | 0 / 40 @ 1.09k | 20 / 40 @ 6.56k | 0 / 40 @ 1.40k | +50.0 [+34.3, +65.7] | +47.3 [+31.5, +63.1] | 97.5% / 60.0% |

- **SIDE-ENV-3-P1 refuted:** Qwen3-8B T 15.0%, below 20%. **P2 holds:** +15.0. **P3 refuted narrowly:** 12.5% against 12.8%
  (one conversation).
- **Decision (registered):** the calendar family is closed as a test bed. The second track's environment work continues only through
  a family the teammate designs; the zero-shot MT-SEL test is not run on this family.
- **Raw cases:**
  - The visible-failure signal carries no information here, and that is why P3 fails. Counted on every turn up to the first
    divergence, an error result appears in Qwen3-8B N's right turns 9 of 9 and its wrong turns 35 of 40. For T it is 26 of 38 right
    and 21 of 34 wrong.
    - The errors come from calls issued in the same step as the reads they depend on: guessed meeting ids ("No meeting with id"),
      guessed room names ("No room named"), and repeated bookings ("A meeting titled ... already exists").
    - A check that escalates on an error would escalate nearly every turn. The registered P3 counts such failures as "shown by the
      environment", so it measures the share of silent failures where the property that matters is separation.
    - Qwen3.5-9B T separates somewhat: errors in 10 of 20 wrong turns and 21 of 74 right turns.
  - **Qwen3-8B T:**
    - Book: 10 of 34 reached booking turns pick a wrong start in the right room.
    - Cancel: 15 of 34 first divergences, 10 of them cancelling a meeting the person does not attend or that does not overlap the
      window. The cancels are issued in the same step as `get_schedule`, from ids seen in earlier turns.
    - Its thinking costs 28k output tokens per conversation, so T − N utility is +1.1.
  - **Qwen3.5-9B N** never makes the booking or move call (0 of 40 turns each), so it fails on the protocol, not on the
    algorithm. In 18 booking turns and 11 move turns no call decodes, usually because `list_rooms` is written without parentheses
    (16 and 8 of them). BFCL's decoder then reads the step as text. In the other turns it reads the calendars and then writes its
    slot reasoning as the reply, which ends the turn. E inherits this: the turn shows no error, so E never thinks (0.45 thinking steps
    per conversation).
- **Lesson for the teammate's families** (`side/README.md`): pre-register P3 as separation, not as a share of silent failures. A
  family tests the verifier methods when an error in the turn does not tell a right turn from a wrong one. Compare the error rate of
  right and wrong turns up to the first divergence. Check it against BFCL's stored rows before the run, as P1's anchors are.
- **Correction to SIDE-ENV-2's results** (same date): `side/analyze_env.py`, the family-agnostic replay, gives Qwen3-8B N's first
  diverging turn silent in 23 / 38 (60.5%), not the 58% recorded from `sidepkg_fail.py`; T 72.7% and Qwen3.5-9B's numbers match. The
  decision does not change.

## SIDE-MC-H: constructions held out: a thinking program first, the thinking answer only when the program's object fails a free check (written 2026-11-04 12:0x UTC, before any generation on the 147 held-out instances)

**Why.** The computation way of the side work: a constructive problem is solved by an object, and a human-written verifier
decides it. The dev results (FINDINGS 2026-11-04 09:0x and 11:3x; 79 instances of 40 problems, Qwen3-8B) are as follows.
- Thinking at a 30k cap: a direct answer is right on 19 (22.0k tokens). A program that builds or searches is right on 18 (18.1k).
  They overlap on only 10.
- The main recipe's order: the thinking program first, and the thinking answer only when the program's output does not parse or
  none of 4 quick self-written checkers accepts it. This gave 27 right, the union of both, at 36.5k tokens. Utility +15.93 against
  +13.05 for the direct answer alone, +2.88 [−5.01, +11.84] clustered by problem.
- The rule, the order and the 4 checkers were chosen on dev, so dev numbers are not evidence. This test fixes them and runs on the
  held-out instances.

**Related work.** MathConstruct (2502.10197) scores each model directly and with brute-force code, separately. CodeT (2207.10397)
ranks programs by agreement with generated tests. We found no use of a self-written checker as the escalation gate between a
program and a direct answer for constructions.

**Data.** `$POC_DATA/construct/ids_mceval.txt`: 147 instances, 2 variations each of 75 problems (`construct.py build`, split by
`random.Random(0)` over problem names, none in dev).

**Run** (Qwen3-8B, lane.sh, two GPUs with tensor parallelism and a 32k context for the 30k arms; tags `mceval_q8b_*`):
1. `gen mceval_q8b_dt30 --arm direct --think --max_tokens 30000`, `gen mceval_q8b_pt30 --arm program --think --max_tokens 30000`,
   `gen mceval_q8b_cn8 --arm checker --k 4` (quick checkers, 4 samples).
2. `grade mceval_q8b_dt30 mceval_q8b_pt30 --checkers mceval_q8b_cn8` (MathConstruct's verifiers).
3. Arms, per instance:
   - **D**: dt30 alone;
   - **P**: pt30 alone;
   - **C** (the rule): pt30's object when it parses and at least one of the 4 checkers accepts it, else dt30's. Tokens are
     pt30's plus the checkers', plus dt30's when escalated;
   - **C0**: the same with parsing as the only check (no checker).

**Predictions** (paired, 95% bootstrap intervals over problems; utility 100 × right − 0.5 × output ktokens):
- **SIDE-MC-H-P1 (decision):** C − D accuracy lower bound > 0.
- **SIDE-MC-H-P2:** C − D utility, reported with its interval. Expected about +3, interval including 0: C costs about 1.7× D.
- **SIDE-MC-H-P3:** C − C0 accuracy ≥ 0 (the checkers keep more than they lose). Reported with its interval.
- **Reported:** the checkers' accept rates on right and wrong parsed objects, and the overlap of P's and D's right objects.
- **Expected:** D 20–28% (dev 24%), C 28–38% (dev 34%).

**Decision.**
- **P1 holds** → for constructions the side work's computation recipe is "thinking program, quick self-written check, thinking
  answer on failure" (side/README section D), stated as a trade if P2's interval includes 0.
- **P1 refuted** → the overlap on dev was noise, and the recipe is the direct thinking answer with the full budget.

## SIDE-GT-H: geometry held out: exact proofs from the statement by an open model translating and a CPU engine proving (written 2026-11-04 13:1x UTC, before any translation of the 65 held-out problems)

**Why.** Dev (FINDINGS 2026-11-04 13:1x; 24 problems): Qwen3.6-27B-AWQ translates 6 problems faithfully, and DDAR proves 4 end to
end (IMO 2010 P4, 2014 P4, 2015 P4, 2017 P4). This test checks whether that rate carries to problems never used for any decision.
The 11 dev problems with an IMO-AG-30 reference were put first, and IMO-AG-30 is DDAR-friendly, so the held-out rate may be lower.

**Related work.** NL2AGBench (2608.28481) measures translation alone: executable rates, open models weak. AlphaGeometry 1 and 2
(2502.03544) translate with Gemini and prove with a trained model plus DDAR. HAGeo (2512.00097) proves from given formal
statements, using heuristic auxiliary points. We found no end-to-end result from natural language with an open model and a
symbolic engine only.

**Data.** `$POC_DATA/geo/ids_gteval.txt`: 65 problems, none in dev. 15 are from OPC; frontier natural-language proofs of those
are right in 2 of 79 graded attempts, and 14 of the 15 have none right.

**Run.**
1. Translate with `gen gteval_q36_tg ids_gteval.txt --think --k 4 --repair 2 --grammar`.
   - Qwen3.6-27B-AWQ on two 3090s, tensor parallel, `POC_TEMPLATE_EFFORT=medium`.
   - `GT_TRIVIAL=1`, so the repair turn is told when a goal is trivial. This is the only change from dev 4.
2. **Faithfulness first, blind to DDAR.**
   - Before any `check` runs, I list every translation whose last round is `guarded` and read each against its statement.
   - A translation is **faithful** when two things hold. Every hypothesis of the statement is present, up to an equivalent
     encoding. And none is added: a special position, a fixed ratio, or a chosen intersection the statement leaves open are
     added hypotheses; picking one of two intersections where the statement names it is not. The goal must be the statement's
     claim, or for "if and only if" one direction with the other side as hypothesis.
   - The list and the verdicts are written to `results/proof/gteval_faithful.json` and committed in this file's results section
     before step 3.
3. `check gteval_q36_tg --timeout 300` (guard, trivial test, DDAR).
4. **End-to-end count:** problems with at least one faithful translation that DDAR proves.

**Predictions.**
- **SIDE-GT-H-P1 (decision):** the held-out end-to-end rate is at least 6.7%, dev's Wilson 95% lower bound. On 65 problems that is
  ≥ 5 problems.
- **SIDE-GT-H-P2 (reported):** the faithful-translation rate (dev 6 of 24), DDAR's rate given a faithful translation (dev 4 of
  6), and tokens per problem.
- **SIDE-GT-H-P3 (reported):** among the 15 OPC problems, the number proved where every graded frontier proof was wrong.
- **Expected:** 3–8 problems end to end, below dev's 17% because dev started with the IMO-AG-30 problems.

**Decision.**
- **P1 holds** → SIDE-GT is documented in side/README as a working pipeline for the teammate, with the held-out rate. Next comes
  an auxiliary-point search for the faithful translations DDAR cannot prove (HAGeo-style, on Newclid).
- **P1 refuted** → dev's rate came from the IMO-AG-30 problems. The pipeline is reported with the held-out rate, and the next
  step is the translator, not the prover.

## Results of SIDE-MC-H (written 2026-11-04 14:3x UTC; `results/mch_eval.txt`, `python3 side/construct.py cascade mceval_q8b_dt30+mceval_q8b_pt30 --direct mceval_q8b_dt30 --program mceval_q8b_pt30 --checkers mceval_q8b_cn8`; jobs 1315962 / 1315963)

147 instances of 75 problems, Qwen3-8B, graded by MathConstruct's verifiers; intervals by bootstrap over problems.

| arm | right | tokens | utility |
|---|---|---|---|
| D: direct, thinking at 30k | 34 (23.1%) | 22.2k | +12.04 |
| P: program, thinking at 30k | 27 (18.4%) | 17.9k | +9.43 |
| C: P's object if it parses and one of 4 quick checkers accepts it, else D | 41 (27.9%) | 38.7k | +8.52 |
| C0: P's object if it parses, else D | 44 (29.9%) | 31.9k | +14.00 |

- **SIDE-MC-H-P1 refuted:** C − D accuracy +4.76 [−0.68, +10.27]; the lower bound misses 0.
- **P2:** C − D utility −3.52 [−9.09, +2.69].
- **P3 refuted:** C − C0 accuracy −2.04 [−5.56, +1.36], utility −5.48 [−9.42, −1.88]. The quick checkers accept 44 of 61 right
  parsed objects and 15 of 95 wrong ones. Rejecting 17 right objects costs more than catching 80 wrong ones gains.
- The complementarity is not noise. P and D are right on 27 and 34 instances, 13 in common, union 48 (dev: 18, 19, 10, 27). The
  parse-only gate C0, registered as a secondary arm, gains accuracy +6.80 [+0.68, +13.51] at 1.4× D's tokens. Its utility ties,
  +1.96 [−4.55, +9.09].
- Expected ranges: D 20–28% held (23.1%); C 28–38% missed (27.9%).

**Decision (registered):** P1 is refuted, so the computation recipe for constructions stays the direct thinking answer with the
full budget. The registered reason, "the overlap on dev was noise", is contradicted: the overlap holds, and the gate is what fails.
C0's accuracy gain is a result of a secondary arm, not a decision. Using it needs a fresh test (new variations of the problems).
The self-written quick checker is not a usable free check for an 8B model on constructions: it rejects 28% of right objects.

## SIDE-MC-H2: the parse-only gate on fresh variations (written 2026-11-04 14:3x UTC, before any generation on the new instances)

**Why.** SIDE-MC-H refuted the checker-gated cascade. Its secondary arm C0 gained accuracy over the direct thinking answer:
+6.80 [+0.68, +13.51] at 1.4× the tokens. C0 takes the thinking program's object when the program prints one that parses, else
the thinking answer. It was not the decision arm, so it is tested here on instances no decision has seen. This is the main
recipe's rule ("think again only on a visible failure") with the program's output as the visible check.

**Data.** `construct.py build --more` appends variations 2 and 3 of every problem to `instances.jsonl`.
`generate_multiple` is prefix-stable, so variations 0 and 1 are unchanged; duplicates of earlier statements are dropped.
`ids_mcfresh.txt` holds the 137 new instances of the 75 held-out problems. They are new parameters of problems SIDE-MC-H used, so
the problems are not independent of it, but the instances are.

**Run.** Qwen3-8B, the same jobs as SIDE-MC-H: `gen mcfresh_q8b_dt30 --arm direct --think --max_tokens 30000` and
`gen mcfresh_q8b_pt30 --arm program --think --max_tokens 30000`; `grade mcfresh_q8b_dt30 mcfresh_q8b_pt30 --checkers <none>`.
Then `construct.py cascade` (D, P, C0; intervals by bootstrap over problems).

**Predictions.**
- **SIDE-MC-H2-P1 (decision):** C0 − D accuracy lower bound > 0.
- **P2 (reported):** C0 − D utility, expected about +2 with an interval including 0.
- **Expected:** D 20–28%, C0 27–35%.

**Decision.**
- **P1 holds** → the computation recipe for constructions becomes "thinking program first, the thinking answer only when the
  program prints no parseable object" (side/README section D). It is stated as an accuracy gain at about 1.4× the tokens, a tie
  in utility unless P2's interval excludes 0.
- **P1 refuted** → it stays the direct thinking answer.


## Results of SIDE-GT-H, part 1: faithfulness, judged before any check (written 2026-11-04 15:2x UTC; job 1316296, 260 translations at 12.5k tokens; verdicts `results/proof/gteval_faithful.json`, faithful ids `$POC_DATA/geo/ids_gteval_faithful.txt`)

Statuses of the last round: unexpressible 130, guarded 59 (on 23 problems), goal fails 35, build error 34, no translation 2. No
`check` has run on this tag.

The protocol is as registered, with two readings made explicit:
- Positional and configuration conditions that the language cannot state do not count as missing hypotheses: betweenness,
  acuteness, convexity, a line disjoint from a circle. IMO-AG-30's references omit them too.
- A translation that names one of several objects the statement leaves open states a stronger claim and counts as faithful. An
  example is "a median" written as the A-median.

| problem | faithful samples | unfaithful samples | reading |
|---|---|---|---|
| hf_2001_imo_shortlist_problems_g1 | - | 0,3 | T0 takes A1 as the midpoint of the square's top side, not its centre; T3 replaces A1 by the centre of the square on BC (a homothety step of the solution) |
| hf_2001_usamo_problems_problem_2 | 0,1,2,3 | - | incenter2 gives D1 on BC, E1 on CA; CD2 = BD1, CE2 = AE1; Q one of the two intersections, as the statement names it |
| hf_2002_pan_african_mo_problems_problem_5 | 0,1,3 | - | circle on diameter AB, tangents at E and F as perpendiculars to the radii |
| hf_2004_imo_shortlist_problems_g8 | 0 | - | AN/BN = AM/BM by eqratio6; N one of the two intersections (N != M named) |
| hf_2004_pan_african_mo_problems_problem_6 | 0,1,2,3 | - | one direction of the iff: N the midpoint, goal IK perp JN |
| hf_2005_indonesia_mo_problems_problem_7 | - | 2,3 | the statement text is garbled ("the intersection of A2 and B1B2"); the squares are placed on the sides AB, BC, ... which the text does not say |
| hf_2005_usamo_problems_problem_3 | 3 | - | the text says 'APC_1 is cyclic' (garbled); the translation reads APBC1 and APCB1, USAMO 2005 P3 as posed |
| hf_2006_romanian_nmo_problems_grade_9_problem_3 | 0 | - | part (b): CB = BP = PA = AB by circles, D the second point of line CP on the circle, goal PD = r |
| hf_2006_usamo_problems_problem_6 | - | 1 | AE/ED = BF/FC encoded through parallels (equivalent), but the goal is one circle (TCF) through the common point of two; the claim needs (TDE) as well |
| hf_2007_indonesia_mo_problems_problem_7 | 0,1,2,3 | - | part (a): tangents at C and D, Q and R as stated, goal P, Q, R collinear |
| hf_2008_usamo_problems_problem_2 | 0,1,2,3 | - | D, E on the perpendicular bisectors and on AM, F = BD x CE |
| hf_2009_usamo_problems_problem_5 | 3 | - | isosceles trapezoid (AB parallel CD, inscribed); one direction: G on the bisector of CBD, goal PQRS cyclic |
| hf_2010_usamo_problems_problem_1 | 2 | - | half of angle XOZ written as the inscribed angle XAZ (A on the circle), the language's only way to state a half angle |
| hf_2012_usamo_problems_problem_5 | 0,1,2 | - | the reflected lines by angle_mirror or by reflecting A in the line PQ |
| hf_2020_camo_problems_problem_3 | 0,1,2,3 | - | X on EF with BX parallel AC, Y with CY parallel AB, M, N point reflections |
| opc_IMOSL_2012_16 | 1,3 | - | parallelogram c e d g gives G = C + D - E, the ECGD of the statement; H the reflection of E in AD |
| opc_IMOSL_2012_18 | 0,3 | - | X on AO and the perpendicular at D, Y on AD and the perpendicular at E |
| opc_IMOSL_2012_22 | 0,1,2,3 | - | the line given by two free points (disjointness from the circle is a configuration condition the language cannot state); the generic case of the conclusion: the second common point of two circles lies on the third |
| opc_IMOSL_2014_20 | - | 1 | the angle conditions on S and T are replaced by S, T the feet from H (added hypotheses) |
| opc_IMOSL_2016_23 | 0,1 | - | part (a): A- and B-excentres, reflections in BC / CA, the reflected lines through reflections of points in AI / BI |
| opc_IMOSL_2017_19 | 0,1,2,3 | - | the goal names the A-median, which implies 'a median' |
| opc_IMOSL_2022_19 | 0,1,2,3 | - | X, Y the second intersections with DX = DA, EY = EA (by eqdistance or by intersection_cc) |
| opc_IMOSL_2023_21 | 0,1,2,3 | - | l_a through the reflections of B in CH and C in BH, and so on; T's vertices as pairwise intersections |

**Faithful: 53 of 59 guarded translations, on 19 of the 65 problems** (dev: 6 of 24). The other 4 problems with guarded
translations have none faithful:
- ISL 2001 G1;
- Indonesia 2005 P7, whose statement text is garbled;
- USAMO 2006 P6, whose goal is only part of the claim;
- ISL 2014 G (2014_20).

## Addendum to SIDE-GT-H: the auxiliary-point arm (written 2026-11-04 15:2x UTC, with the verdicts above and before any check)

- **Primary (P1), unchanged:** `check gteval_q36_tg --timeout 300`, with DDAR on diagram seed 0.
- **Arm AUX, secondary.** Command: `GT_DDAR_SEEDS=0,1,2,3 aux gteval_q36_tg --ids ids_gteval_faithful.txt --k 64 --timeout 60`.
  - It runs on the faithful translations that the primary check leaves guarded and unproved.
  - It adds one auxiliary point at a time: a construction type drawn uniformly, then its arguments. The types are midpoint, point
    reflection, circumcentre, foot, line reflection, and intersection of two lines. It stops at the first proof.
  - It counts the problems proved by DDAR alone or with one auxiliary point.
  - The procedure was fixed on IMO-AG-30's references (job 1316470, still running). So far it has found 4 more proofs, among them
    IMO 2010 P2.
- **AUX-P1 (reported):** +1 to +5 problems over the primary count.
