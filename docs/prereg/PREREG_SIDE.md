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
