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

## Results of SIDE-GT-H, part 2: the registered check (written 2026-11-04 15:3x UTC; check job 1317210, `results/proof/gt_gteval_q36_tg_check.jsonl`)

- DDAR proves 8 translations on 5 problems. 2 of the 8 were judged unfaithful in part 1: USAMO 2006 P6 (partial goal) and ISL
  2014 G (the feet of H in place of the angle conditions). They do not count.
- **End to end (faithful and proved): 3 of 65 problems.**
  - Pan-African 2002 P5: 3 translations, 6 s each.
  - Romanian NMO 2006 grade 9 P3(b): 1 translation, 3 s.
  - ISL 2012 G (2012_16, the ECGD parallelogram and the reflection H, concyclic D, H, F, G): 2 translations, 12 s. Frontier
    natural-language proofs of it are right 0 of 8 times (OPC).
- **SIDE-GT-H-P1 refuted:** 3 of 65 = 4.6%, below the registered 6.7% (≥ 5 problems). It is inside the expected 3–8.
- **P2:**
  - faithful translations on 19 of 65 problems (29%; dev 25%);
  - DDAR proves 3 of those 19 (dev 4 of 6);
  - 12.5k tokens per translation, 50k per problem (k = 4).
- **P3:** 1 OPC problem proved where every graded frontier proof was wrong (ISL 2012 G, 0 of 8).
- No translation was trivial.
- One guarded translation (USAMO 2001 P2, sample 1) held on 0 of 8 diagrams in `check`, after holding on at least one in gen's
  guard. The diagram search is not fully determined by its seed; noted, not changed.

**Decision (registered):** P1 is refuted, and the pipeline is reported with the held-out rate, 3 of 65 problems end to end. The
registered next step, "the translator, not the prover", is contradicted by the data. Translation holds up: 29% of the problems are
translated faithfully, more than on dev. The prover is the bottleneck: 16 of 19 faithful problems are not proved by DDAR alone. The
auxiliary-point arm, registered before this check, is the test of that (job 1317291).

### Note SIDE-MC-H2 withdrawn (2026-11-04 17:4x UTC, before any grading; jobs 1316744 / 1316745 cancelled at 65 of 137 direct answers)
This run would only confirm that the main recipe's rule ("take the program's object, think on a visible failure") holds on one more
task. It cannot change the project's claim, so it is withdrawn under the project's rule against incremental runs. The 65 rows were
not graded. SIDE-MC-H's result stands as recorded: the gated cascade is refuted, and C0 is a secondary arm only.

## Results of SIDE-GT-H, part 3: the auxiliary-point arm (written 2026-11-04 18:4x UTC; job 1317291, `results/proof/gt_gteval_q36_tg_aux.jsonl`)

- 46 faithful translations were unproved by the primary check. The arm proves 18 of them on 7 problems:
  - 2 with DDAR alone, on another diagram;
  - 16 with one auxiliary point, after 4–41 tries at 148–2,486 s each.
- **End to end with the arm: 10 of 65 problems (15.4%), against 3 for DDAR alone. AUX-P1: +7, above the expected +1 to +5.**
- New problems:

  | problem | auxiliary point | OPC frontier proofs right |
  |---|---|---|
  | Pan-African 2004 P6 | reflection of B in AK | not in OPC |
  | USAMO 2008 P2 | reflection of D in M | not in OPC |
  | USAMO 2010 P1 | AO ∩ YQ | not in OPC |
  | CAMO 2020 P3 | reflection of B in Q | not in OPC |
  | ISL 2012 G (2012_18) | midpoint of DY | 0 of 8 |
  | ISL 2016 G (2016_23 a) | reflection of I_A'' in BP | 0 of 5 |
  | ISL 2017 G (2017_19) | reflection of A in HM | 0 of 5 |

- Among OPC's held-out shortlist problems, 4 are now proved where every graded frontier proof was wrong: 2012_16, 2012_18, 2016_23
  and 2017_19. P3 of the main arm counted 1.
- Faithful but still unproved (9): USAMO 2001 P2, ISL 2004 G8, USAMO 2005 P3, Indonesia 2007 P7, USAMO 2009 P5, USAMO 2012 P5,
  ISL 2012 (2012_22), ISL 2022 (2022_19), ISL 2023 (2023_21).
- Reading: the registered decision stands (P1, on DDAR alone, refuted). The arm shows what the prover gap costs. Random single
  points recover 7 of the 16 faithful problems DDAR alone missed. A proposer that chooses points, or two points, is the next method,
  not a further sweep of this one.

## SIDE-GT-AUXP: auxiliary points proposed by the model, against random ones (written 2026-11-04 18:5x UTC, before any proposal is generated)

**Why.** The prover is the geometry pipeline's bottleneck. Random single auxiliary points (64 tries) lift IMO-AG-30's references from
11 to 14 of 30, and the held-out problems from 3 to 10 of 65. Solvers do not add points at random; they add the point a solution
needs. HAGeo's heuristics reach 28 of 30.

**Related work.**
- Models trained to propose auxiliary points: AlphaGeometry (Nature 2024), AlphaGeometry2 (2502.03544), InternGeometry (2512.10534,
  an RL-trained agent), GenesisGeo (2509.21896, fine-tuned).
- Hand-engineered heuristics with no network: HAGeo (2512.00097).
- A training-free LLM in a symbolic loop, but writing analogical proofs rather than auxiliary points: 2505.14479.
- We found no test of an untrained general model proposing auxiliary points to DDAR under a grammar of the construction language.

**Method** (`geo_translate.py propose`, then `aux --prop`).
- Qwen3.6-27B-AWQ (thinking, medium effort) reads the statement (where we have it) and the translation, and reasons about a
  solution.
- One greedy turn then lists up to 8 auxiliary points under an input-dependent grammar: Newclid's 58 single-point constructions,
  with arguments drawn only from the translation's points, one or two constructions per point.
- 2 samples per translation. Proposals are tried in order, interleaved across samples, at 60 s per DDAR run, until one proves.

**Data.**
- The 26 IMO-AG-30-and-other reference translations that DDAR alone did not prove at 60 s (random points proved 4 of them).
- The 43 faithful held-out translations, on 16 problems, that DDAR alone did not prove in the auxiliary arm (random proved 7
  problems).
- Both sets were used by the random arm only; nothing in the proposer was tuned on them.

**Predictions** (problems; DDAR proofs are exact, so a count is not a noisy estimate of itself):
- **AUXP-P1 (decision):** the model's points prove at least one problem that 64 random points did not, on either set.
- **AUXP-P2 (reported):** problems proved by the model's points and by random points, and by each alone. DDAR calls per problem:
  at most 16 against 64.
- **Expected:** the model proves 3–8 of the 42 problems, 1–4 of them new. Its tokens are about 2 × 15k per translation.

**Decision.**
- **P1 holds** → the pipeline's auxiliary step becomes the model's proposals first, then random ones. The proposer's search (two
  points, feedback from what DDAR derived) is the next method.
- **P1 refuted** → an untrained general model does not know which point a solution needs in this language. The next step is a
  derived criterion, such as points that create new deductions, before any training.

## SIDE-GT-AGREE: a label-free faithfulness check from agreement between translations (written 2026-11-04 18:5x UTC, before the check runs on any held-out pair; three smoke pairs only)

**Why.** Every end-to-end proof so far rests on my reading of the translation. Without that reading, a translation that adds or
drops a hypothesis would count as a proof of the problem. Two translations of one statement that are both faithful describe the
same configuration and claim. So on a figure built from either one, the other's construction predicates and goal hold, at least
over the points both name. A translation with an added or dropped hypothesis breaks this in one direction.

**Check** (`geo_translate.py agree`, `one_agree`; numerical tolerance 1e-7, up to 4 diagrams):
- For an ordered pair (A, B), build A's figure.
- Evaluate B's predicates whose points A also names: each construction's predicates from Newclid's definitions, plus B's goal.
- "B holds on A" when all of them hold on some diagram.
- A translation is **corroborated** when some other translation of the same problem holds on it and it holds on that one.
- Smoke on held-out pairs: Indonesia 2007 T0/T1 (faithful) agree both ways at coverage 1.0, and so do ISL 2012_16 T1/T3. ISL 2001
  G1 T0/T3, two different unfaithful translations, fail both ways.

**Data.** The 59 guarded held-out translations of Qwen3.6-27B (SIDE-GT-H), with the blind verdicts of part 1 as labels (53 faithful,
6 unfaithful).

**Predictions.**
- **AGREE-P1 (decision):** no translation judged unfaithful is corroborated. Precision 1, because a false acceptance would count a
  false proof.
- **AGREE-P2 (reported):** the share of faithful translations corroborated. It is limited to problems with ≥ 2 guarded translations.
- **Expected:** P1 may fail on Indonesia 2005 P7, whose two translations share one reading of a garbled statement (a shared
  misreading is the check's blind spot). P2 about 85%.

**Decision.**
- **P1 holds** → corroboration replaces hand reading for counting end-to-end proofs in later geometry runs, with hand reading as an
  audit.
- **P1 refuted** → the failure cases are reported. Corroboration is a necessary condition, not a sufficient one, and hand reading
  stays.

## Results of SIDE-GT-AGREE (written 2026-11-04 18:5x UTC; `results/proof/gt_gteval_q36_tg_agree.jsonl`, 130 ordered pairs on 23 problems, login node)

| blind verdict | corroborated | not corroborated |
|---|---|---|
| faithful (53) | 47 | 6 |
| unfaithful (6) | 0 | 6 |

- **AGREE-P1 holds:** no unfaithful translation is corroborated.
  - Indonesia 2005 P7's two translations share the garbled statement, yet disagree. They name the squares' vertices in opposite
    orders, so their figures differ.
  - ISL 2001 G1's two unfaithful translations disagree too.
- **AGREE-P2:** 47 of the 48 faithful translations on problems with ≥ 2 guarded ones are corroborated (98%). The miss is USAMO
  2012 P5 sample 2, which names its reflected points differently from the others (coverage 0). The other 5 faithful
  translations are alone on their problems.
- **Problems:** 14 have a corroborated translation, and all 14 are faithful by the blind reading.
- **End to end without hand reading** (corroborated and proved, by DDAR or with one auxiliary point): **8 of 65 problems**. Hand
  reading gives 10; the 2 missing (Romanian NMO 2006, USAMO 2010 P1) each had a single guarded translation. All 4 OPC shortlist
  problems whose frontier proofs all failed are among the 8.

**Decision (registered):** corroboration replaces hand reading for counting end-to-end proofs in later geometry runs, with hand
reading as an audit. It needs at least two guarded translations per problem, so k (samples per problem) now also buys
certification. The check's blind spot stays as predicted: a misreading shared by every sample.

## Results of SIDE-GT-AUXP (written 2026-11-05 00:3x UTC; proposals job 1318352, DDAR job 1319460; `results/proof/gt_{refs,gteval_q36_tg}_auxp.jsonl`)

| set | problems | random (64 tries) | model (≤ 16 proposals) | model only | random only |
|---|---|---|---|---|---|
| references | 26 | 4 | 2 | 0 | 2 (IMO 2010 P2, IMO 2014 P4) |
| held out (faithful) | 16 | 7 | 5 | 0 | 2 (USAMO 2010 P1, ISL 2016_23) |

- **AUXP-P1 refuted:** the model's points prove no problem that random points miss.
- **AUXP-P2:**
  - Where both prove a problem, the model finds the point sooner: fewest tries per problem 1, 1, 2, 4, 9 on the held-out set,
    against 4, 5, 12, 19, 41 for random. USAMO 2008 P2 falls on its first proposal, the circumcentre of ABC.
  - DDAR calls in total: 695 for the model, 3,514 for random.
  - The model spends 26–31k tokens per translation.
- **Reading:** the model proposes the textbook points (circumcentres, feet, the second intersection with the circumcircle). The four
  problems only random points prove need a less obvious point, such as the reflection of A in OK for IMO 2010 P2, which breadth
  finds and the model does not propose.

**Decision (registered):** an untrained general model does not know which point a solution needs in this language beyond the
obvious ones. The pipeline keeps random points; model proposals would only save CPU. The next step is a derived criterion for
choosing points, before any training. Example: rank candidates by the new facts a short DDAR run derives about the goal's points.

## SIDE-GT-POOL: pooling what single auxiliary points prove, instead of adding points together (written 2026-11-05 11:5x UTC, before any pooled run; one smoke run on problems single points already prove)

**Why.** The prover is the geometry pipeline's bottleneck, and 31 problems resist one random point (22 references, 9 held out). Their
proofs need more than one point. Adding m points together is the usual way (HAGeo: 6 points per attempt, K = 4096 attempts on IMO-AG-30,
DDAR rerun for each). That search is costly twice over: pairs alone grow as k², and DDAR's candidate search is polynomial in the number
of points. At 60 s, most of our single-point runs already hit the limit (about 53 s per run on these problems).

**Derivation.** Let H be the translation, Cl the fixed point of DDAR's rules, and L(x) the facts in Cl(H + x) that mention only H's own
points.
1. Every fact in L(x) is a theorem about H's figure: x is built from H's points, so it exists wherever its construction does, and it
   appears nowhere in the statement of the fact. So L(x) can be added to H without changing what is true.
2. DDAR is monotone: more facts can only derive more. So Cl(H + L(x) + L(y)) contains every proof that uses x and y *only through facts
   about H's points*.
3. For k candidates, that closure costs k + 1 runs with at most |H| + 1 points each. Running the pairs costs k(k−1)/2 runs with |H| + 2
   points. Pairs do cover one kind of proof that pooling cannot: one where x and y interact directly, through a fact that mentions both.
   That is the testable limit of this theory. A second round (each point again, with the pool as lemmas) reaches some of those, since
   y's run can use what x's facts gave.
4. A consequence to check: a pooled proof that uses lemmas from only one point is already in that point's own closure, so it can
   appear only if that point's single run hit the time limit.

No threshold, ranking or hand-set order is involved. The pool is every fact, from every candidate.

**Related work.**
- AlphaGeometry2 (2502.03544) has this mechanism inside SKEST: when a node fails, it writes down the facts the engine proved, keeping those
  relevant to the original problem, and other nodes and trees can use them. There the nodes' points come from trained language models.
  The paper reports no ablation and no number for the sharing itself ("this boosts the overall performance"), and no run of it without a
  language model.
- HAGeo (2512.00097; code at github.com/boduan1/HAGeo, so our earlier note that it is unreleased is out of date) needs no network but
  accumulates points inside an attempt. Its paper describes DDAR as rerun per attempt, and describes no reuse of a failed attempt's facts.
- So what is new here is a measurement: what sharing alone adds, with random points and no model, on one CPU budget.

**Method** (`geo_translate.py pool`, `one_lem`).
- The same 64 candidates as the single-point arm (`aux_candidates`, seed 0), 60 s per DDAR run, diagram seeds 0, 1, 2 on failure.
- Round 1: each point runs alone. Facts over H's points that the base run does not hold join the pool. Then H plus the pool, no point.
- Round 2, if the goal has not fallen and the pool grew: each point again with the pool as lemmas, then H plus the larger pool. It stops
  early at a fixed point.
- A lemma is dropped if it fails numerically on the receiving figure (a step with two intersections can take the other one); the
  number dropped is reported.
- **Comparison, same DDAR calls:** 64 random pairs of the same candidates, added together, one round's worth (`pool --pairs`).
- **Confirmation:** each pooled proof names the points whose lemmas it used. Plain DDAR then runs with those points added together, up
  to 600 s, with no lemmas. A proof it reproduces is an ordinary DDAR proof. One it does not reproduce rests on the lemmas' own
  derivations, and is reported separately.

**Data.** The 46 translations of the 31 problems no single point proved: 22 references (1 translation each), and 24 faithful held-out
translations of 9 problems. These were used only by the random and proposal arms; nothing here is tuned on them. The smoke runs on
problems that single points already prove, which are not in this set.

**Predictions** (problems; DDAR proofs are exact, so a count is not a noisy estimate of itself):
- **POOL-P1 (decision):** pooling proves at least one of the 31 problems.
- **POOL-P2 (reported):** problems proved by pooling and by the 64 random pairs, and by each alone, with the seconds per DDAR run for each.
- **POOL-P3 (theory check, step 4):** every pooled proof uses lemmas from at least two points, or from one point whose single run hit the
  limit or failed.
- **Expected:** pooling proves 1–4 of the 31, and pairs 0–2. Most pooled proofs come in round 1. Their confirmation at 600 s succeeds
  on about half, since joint DDAR is the slow route the theory avoids.

**Decision.**
- **P1 holds** → pooling replaces single random points in the pipeline's auxiliary step, and the record of which points' lemmas proofs use
  becomes the data for the next method: ordering candidates by chance of success per second, the optimal order for all-or-none search
  (Simon and Kadane, 1975).
- **P1 refuted** → these proofs need points that interact, so facts over H's points do not compose. The next step is a candidate generator
  derived from what the goal lacks: DDAR's rules read backward from the goal, naming the missing premises.

### SIDE-GT-POOL: faults found during the first run, and the restart (written 2026-11-05 13:3x UTC; predictions above unchanged)

The first run (jobs 1324967, 1324968) was stopped partway, 26 translations in. Its rows are kept outside the repository and count for nothing. Reading them showed:

1. **Not as registered.** Round 1 passed each run the lemmas of earlier runs in the same round. The registered form runs each point alone.
2. **My injection crashed runs.** Newclid deep-copies the proof state at the start of a run, and with lemmas injected that often exceeds Python's recursion limit. Most runs on several hard problems failed this way (62–64 of 64), so they barely tested pooling. Each run now has a large stack.
3. **The confirmation was too weak.** It added only the points the last step's lemmas named, not those that those lemmas rested on. It was also held to Newclid's default limit of 10,000 steps, which stops a run at 30–80 s whatever the time limit.
4. **A candidate bug in IMO 2008 P6.** That reference fixes some coordinates (`x@4.96_-0.13`), and half the candidates used the full string as a point name and failed to build. So the single-point arm under-tested that one problem. The pair arm still running has the same bug for this problem.

**The step limit, for reading every earlier geometry count.** At 60 s per run it costs little: a run reaches 10,000 steps at about the same time as the limit. Longer time limits, such as the 300 s and 600 s runs, did not buy what they appeared to. With no step limit, DDAR alone still does not prove IMO 2011 P6 or IMO 2008 P6 in 300 s (34,954–66,922 steps, not saturated).

**Restart.**
- **Arm A, the registered form:** `pool --alone` (jobs 1327629, 1327630). This one decides POOL-P1 and POOL-P3.
- **Arm C, the accumulating variant:** `pool --cert` (jobs 1327631, 1327632), reported as a variant.
- **Comparison:** the pair arm (jobs 1324969, 1324970) continues unchanged. Its DDAR is the same up to the point-name bug.
- **Each proof is now checked** by the steps in Method's confirmation, and also by replaying each step with only the lemmas it needs and by testing those lemmas on 8 fresh diagrams.

## SIDE-GT-SOUND: Newclid derives false facts; a numerical guard on every derived fact (written 2026-11-05 14:4x UTC, before any rerun of the pipeline under the guard; the guard has been tried only on re-runs of the 68 recorded proofs)

**Why.** Reading a proof of ISL 2004 G8 from SIDE-GT-POOL's first run, I found CE = DE listed as a premise and AB ∥ CD derived from it. Neither holds in general. Newclid 2.0.2 checks the goal numerically and has an option, off by default, to check an added statement. So a false fact can stay, spread, and "prove" a true goal, and our guard (the goal holds on the figure) cannot see that. **Every geometry count recorded so far assumed DDAR's proofs were exact.**

**Audit** (`geo_translate.py audit`, `one_audit`; `results/proof/gt_audit2.jsonl`). Each of the 68 recorded proofs was rerun, up to 6 diagrams at 120 s. Every statement a proof uses was tested on its own figure, where a sound derivation cannot fail. "False" means false at 1e-4, well above rounding.

| | rows | reproved | a statement false on its own figure | a reason-free statement that is not a construction fact |
|---|---|---|---|---|
| plain Newclid | 68 | 57 | 16 | 5 |
| with the guard | 68 | 47 | 0 | 1 (IMO 2000 P1, `cong e q p e`, true on all 8 fresh figures; to read) |

- False proofs are often cascades, with 14–84 false statements out of 91–221, such as "a, b, c are collinear" for a triangle's vertices.
- Plain Newclid raised errors in 20 of the 68 rows, such as a circle through three "collinear" points. With the guard, none did. So those crashes were mostly a symptom of the false facts.
- A rerun is not the same run as the original, because Newclid's order is not deterministic, so these rows do not relabel the original counts one by one.

**The guard** (`GT_SOUND=1`, `patch_newclid`). A rule's conclusion or an algebraic derivation is kept only if it holds on the run's own figure, and so is each statement it adds, and each merge of two symbols. Rejecting a fact only loses deductions. A fact that holds on one generic figure could still be a coincidence, which is why the audit's fresh figures stay in place.

**Related work.** HAGeo (2512.00097) has an appendix on a fallacious AlphaGeometry proof of IMO 2020 P1, and Newclid's manual records a bug shared with AlphaGeometry on IMO 2004 P1. So invalid proofs in this family of engines are known. What we measure here is how often they occur on our own pipeline's proofs, and that a per-fact numerical guard removes them.

**Rerun** under the guard (output in `results/proof/sound/`, 60 s per run, the same 64 candidates):
- DDAR alone on the dev and held-out translations, and on the references;
- one random point at a time;
- SIDE-GT-POOL's arms A (registered form) and C (variant), and the 64 random pairs, on whichever problems no single point now proves;
- the audit on every proof found.

**Predictions.** I have seen the audit above, so these are not blind about it.
- **SOUND-P1 (decision):** no proof found in the rerun uses a statement false on its own figure.
- **SOUND-P2 (reported):** faithful held-out problems proved end to end, against the 10 of 65 recorded, with DDAR alone and with one point. **Expected:** 5–8 in all, with DDAR alone near its recorded 3. The auxiliary arm loses the most. IMO-AG-30 references, recorded at 14 of 30: expected 12–14.
- **SOUND-P3 (reported):** the share of DDAR runs that raise an error, against plain Newclid. **Expected:** near zero.
- **POOL-P1 to P3 are decided here, on the recomputed set.** The first run is already known to me: arm A proved USAMO 2005 P3, and plain DDAR confirmed the Indonesia 2007 proofs from arm C, whose lemmas hold on fresh figures. So P1 is likely to hold, and the informative results are P2 (against pairs) and P3.

**Decision.**
- **P1 holds** → guarded DDAR replaces plain Newclid everywhere in the geometry track, and every geometry claim is restated from this rerun.
- **P1 refuted** → the guard is not enough, and geometry claims are withdrawn until proofs are read by hand.

### SIDE-GT-SOUND: a fault in the guard and the audit, and a second rerun (written 2026-11-05 17:0x UTC; predictions above unchanged)

**First rerun, as registered.** Held out 7 of 65 (3 by DDAR alone, 4 with one point); IMO-AG-30 12 of 30 (9 and 3). Its audit (43 proofs, job 1329373): all 43 reran, none raised an error, one statement flagged false on its own figure (`perp f g o x`, IMO 2015 P4), one root with no reason (`cong p e q e`, IMO 2000 P1), and five rows with statements flagged on fresh figures.

**The fault.** I read the flagged statements. All are `para` or `perp`, and all are true: on each flagged figure the sine or cosine between the two lines is at most 1e-10. Newclid tests these two predicates by comparing an unnormalized product with an absolute 1e-12 (5e-12 for `perp`), in `numerical.geometries`, a module my tolerance setting did not reach. So:
- the audit's one "false on own figure" and all its "false on fresh" flags are false alarms;
- the guard rejected true `para` and `perp` facts on rounding alone (9 of 219 conclusions in a quick sample), which loses deductions, so the first rerun's counts are lower bounds;
- the earlier audit of plain Newclid (16 of 57 use a false statement) is overstated: 3 of the 16 are flagged only on `para` or `perp`.

**The fix.** `num_holds`: `para` and `perp` are tested on the normalized sine or cosine, at the same 1e-7 as every other predicate in the guard, and 1e-4 in the audit. Used by the guard, the audit, the goal test and the lemma tests. The agreement test (SIDE-GT-AGREE) is unchanged, because its result is registered.

**Second rerun.** The whole pipeline again, in `results/proof/sound2/`: check, one point, pooling arms A and C, and pairs, then the audit. The first rerun's pooling and pair jobs were cancelled before any proof. The earlier audit list is also re-audited under plain Newclid.

**Predictions, written before the second rerun.**
- **SOUND-P1** is decided on the second rerun's audit, by the same rule.
- **SOUND-FIX-P2:** with true facts no longer rejected, held out 7–9 of 65 and IMO-AG-30 12–14 of 30: equal or slightly more than the first rerun, because few facts were rejected.
- **SOUND-FIX-P3:** plain Newclid's re-audit gives at most 13 of 57 with a false statement.
- POOL-P1 to P3 stand as registered and are decided on the second rerun.

### SIDE-GT-SOUND: a second fault in the same test, and a third rerun (written 2026-11-05 19:1x UTC; predictions above unchanged)

**Second rerun, first stage.** Held out 7 of 65 (the same 3 and 4 problems). IMO-AG-30 12 of 30 (10 by DDAR alone and 2 with one point); IMO 2013 P4 now falls to DDAR alone and IMO 2016 P1 is new, while IMO 2004 P1 is lost. SOUND-FIX-P2 (7–9 and 12–14) holds at its lower end on this rerun.

**The fault.** The plain Newclid re-audit flagged 27 of 56 proofs, against the "at most 13" I predicted (SOUND-FIX-P3). I read the rows with few flags: they are statements like `para c p c k1` and `para a e a d`, where the two lines are one line. Newclid uses these to say that three points are collinear, so they are true. I had kept Newclid's exclusion of a line from being parallel to itself, which in its own check rarely fired because of rounding; on the normalized test it always fires. So the second rerun's guard rejected those true facts.

**The fix.** `para` now tests only that the two directions agree.

**Check before rerunning.** I logged every rejection in a guarded sample of the audit list, about 80 s in all (`nlp_data/geo/lem9.py`), tolerance 1e-7: tens of thousands of checks, 2 rejections (an `eqangle` and an `eqratio`), and both still fail at 1e-3. So on this sample the guard rejects only facts that are false by far more than rounding.

**Third rerun.** The whole pipeline in `results/proof/sound3/`, and a re-audit of plain Newclid. SOUND-P1 and POOL-P1 to P3 are decided on it. Earlier reruns' pooling runs are cancelled and count for nothing.

**Predictions, written before the third rerun.** SOUND-FIX-P2 and P3 stand as written.

**Result, SOUND-FIX-P3 (written 2026-11-05 20:1x UTC; job 1330096, `results/proof/gt_audit5.jsonl`):** plain Newclid, same list and seeds as the first audit, fixed test: 54 of 68 reran, 10 use a statement false on their own figure, 19 rows raise an error. At most 13: holds. The first audit's 16 of 57 is replaced by 10 of 54.


## Results of SIDE-GT-SOUND and SIDE-GT-POOL, third rerun (written 2026-11-06 06:2x UTC; `results/proof/sound3/`, audit `gt_audit_pool3.jsonl`, job 1334295)

**SOUND-P1 holds, so guarded DDAR replaces plain Newclid in the geometry track.** Across the 44 proofs of the first stage and the pooling and pair proofs that reran, no statement is false on its own figure or on 8 fresh figures.

**SOUND-P2.** Held out: 8 of 65 (4 by DDAR alone, 3 with one point, 1 from pooling), within the expected 5–8. IMO-AG-30: 13 of 30, within 12–14. The withdrawn counts were 10 and 14.

| | Pooling, arm A | Pooling, arm C | 64 random pairs |
|---|---|---|---|
| Held out (9 problems) | Indonesia 2007 P7 (4 translations) | Indonesia 2007 P7 (4), USAMO 2005 P3 (1, not confirmed) | none |
| References (23 translations) | none | none | IMO 2010 P2 (1 translation, not the IMO-AG-30 row) |
| Seconds per DDAR call | 43 held out, 50 references | 40, 52 | 41, 49 |

**POOL-P1 holds as written, on one problem.** It proves Indonesia 2007 P7. **POOL-P2:** pooling 1 problem (2 with USAMO 2005 P3, which did not rerun on 6 seeds, and whose certificate fails), pairs 1. **POOL-P3 holds, but says little:** Indonesia's proofs use lemmas from one point, whose single run failed. Both counts are inside what I expected (1–4 and 0–2).

**How to read that.** Pooling has not shown what it was for, facts from different points adding up:
- Indonesia's lemma is the goal restated, and plain DDAR with that one point proved it in 47 s during the pooling run. So this is a single point missed once, not a composition.
- Neither plain confirmation reran in the audit (6 seeds, 600 s each). Newclid's order is not deterministic, and this proof depends on it.
- The one proof that composes two points, USAMO 2005 P3, is the one that fails its certificate.

**Decision, as registered:** P1 holds, so pooling would replace single points, and the next method would order candidates by chance of success per second (Simon and Kadane, 1975). **I withdraw both.** Ordering needs success rates per candidate type, and pooling gives one problem's worth of data, so it could only be a guess. Pooling cost 3,000 to 4,500 DDAR calls per arm for that one problem. SIDE-GT-CLOSE below contains pooling by monotonicity, and replaces it if it holds.

**A correction.** My SIDE-GT-POOL note that HAGeo's code is at github.com/boduan1/HAGeo is wrong in substance. On 2026-11-06 that repository holds only a README and figures, and says the full code awaits review. Its benchmark, HAGeo-409, is released.

## SIDE-GT-CLOSE: one closure over a whole pool of points, instead of a search over which points to add (written 2026-11-06 06:2x UTC, before the full runs)

**Why.** The prover is the geometry pipeline's bottleneck. Everything tried so far (one point, pairs, pooling) runs Newclid once per attempt. So the budget buys few attempts, and HAGeo's result needs thousands of them (K = 4096, 6 points each).

**Derivation.**
1. DDAR is monotone. The closure of H plus a pool of points contains every proof that uses any subset of the pool. So which points to add is a question only because DDAR on many points is slow. With a fast enough closure, there is no search over subsets at all.
2. DDAR is slow because it matches rules over all point tuples. A sound rule concludes only facts true on the figure, so go the other way: compute what is true, numerically, and test each true instance's premises.
3. Angle and length chasing are membership in a linear span. Keep one value per line direction and per log-length, drawn at random mod a 61-bit prime and updated so that every relation evaluates to 0. Then testing a fact costs a few additions, and a wrong "yes" has probability about 2^-61 per test.
4. A circle is linear too: a chord (x, y) has direction t_x + t_y, and a radius to x has direction 2 t_x. This absorbs the inscribed-angle, central-angle, tangent-chord, Thales-circle and parallel-chord rules of Newclid's 43.
5. Constants are dropped: a conclusion is drawn only when true on the figure, which fixes the constant. The price is a known one: a chase with a fractional coefficient (2θ = 0, so θ = 0) picks its branch from the figure. Those chases are counted, and the fresh figures test them.

**Related work.**
- AlphaGeometry 2 (2502.03544) uses numerics to speed up matching of similar triangles and cyclic quadrilaterals, and then still adds points from language models and runs DDAR per node.
- HAGeo (2512.00097) adds batches of 6 and reruns.
- Chou, Gao and Zhang's deductive database (2000) uses numeric diagrams and forward chaining, with heuristics to limit growth.
- I found no paper that closes over a whole candidate pool at once to replace the search over points, in two rounds of search. That does not settle it.

**Already seen, so not blind.**
- Reproduction: 42 of the 44 recorded proofs, in about 0.01 s each against Newclid's seconds to a minute (seeds 0, 1, 2 give 42 each). The misses are USAMO 2006 P6 and IMO 2004 P1.
- Negative controls, on the same 44: with no construction facts it proves 0, with half of them 1.
- K = 0 on the 59 rows below: 7 translations, namely IMO 2016 P1, IMO 2003 P4, IMO 2002 P2a, and Indonesia 2007 P7 (4).
- A timing test of K = 64, 256 and 1000 on 5 rows: K = 256 proves IMO 2018 P1 and ISL 2012 (opc_IMOSL_2012_19) in about 35 s, with 8 of 8 fresh figures. K = 1000 did not finish in 60 s. I read those proofs' statements only in part.

**Method** (`side/geo_closure.py`). The 59 translations of problems that no single point proved in the third rerun (`close_rows.jsonl`: 23 references, 36 faithful held-out translations of 12 problems). Arms K = 0, 64, 256, and every one-step candidate (K = all, up to 1,800 s each). The candidates come from the same generator and seed as the random arms, so K = 64 is the same pool. All candidates go in at once.

**What counts.** A proof counts if its log reads back to the goal and every step holds on every fresh figure tried (8 figures). It is first reduced to the smallest set of points found. Plain guarded Newclid is then run on those points, up to 600 s, as a separate check.

**Predictions** (problems proved, of those in the list):
- **CLOSE-P1 (decision):** K = 256 proves more problems than pooling and pairs together (2), using less CPU than those arms' 13,000 to 19,000 s per translation. Expected: 12 problems, range 7–18.
- **CLOSE-P2 (reported):** K = 64 proves 6 (4–9). K = all proves 16 (9–24), with many time limits.
- **CLOSE-P3 (soundness):** every proof's steps hold on every fresh figure. A proof that fails is withheld and read.
- **CLOSE-P4 (reported):** plain guarded Newclid reproduces at least half of the proofs within 600 s. The rest are reported as found by the closure only, and at least one such proof is read by hand.

**Decision.**
- **P1 and P3 hold** → the closure replaces single points, pairs and pooling. Every geometry count is restated with it, with proofs read by hand first for the headline problems. The hardest gap then is the pool's vocabulary: points built from other auxiliary points.
- **P1 refuted** → the closure is only a faster engine. Next is a candidate generator derived from what the goal lacks, the alternative already registered under SIDE-GT-POOL.
- **P3 refuted** → the engine's rules are wrong somewhere, and its counts are withdrawn until that is found.

**Correction to CLOSE-P1 (written 2026-11-06 06:2x UTC, before any full-run result).** The CPU figure I gave for the comparison was wrong. The recorded CPU per translation is 5,400 s (held out) and 6,500 s (references) for pooling arm A, and 2,600 s and 3,100 s for the pairs, so about 8,000 s and 9,600 s for those two arms together. The prediction itself is unchanged. The comparison is against those figures, and a closure run's limit is 1,800 s.

### SIDE-GT-CLOSE: a stricter check, and one arm stopped (written 2026-11-06 07:3x UTC, after the arms with pools of 0, 64 and 256 and before any Newclid check)

**Results so far, as run.** Pool of 0: 4 problems. Pool of 64: 11. Pool of 256: 23 of 31, against my 12 (7–18), so I treat this as a possible bug until the checks below finish. Every step of all 44 proofs holds on 8 of 8 fresh figures.

**Why a stricter check.** Fresh figures show that each step is true, not that it follows from the steps before it. Whole-proof Newclid runs (CLOSE-P4) may time out on many points and would not say which step is at fault.

**Method** (`geo_closure.py certify`, one translation per problem, its fewest points). Newclid replays a proof one conclusion at a time. Each DDAR run gets the translation, the proof's points, and as lemmas only the conclusions this step's premises were chased from. It has to reach the step's conclusion within 120 s. So another engine checks both the rules and the arithmetic, one step at a time.

**CLOSE-P5 (reported, predicted before any full replay; I saw one proof at 20 s, where the 12 isosceles steps pass and the 3 similar-triangle steps and the goal do not).** At least 80% of steps reproduce. Failures concentrate in steps where Newclid has to do long chases or check a similar-triangle goal, because of its time limits and goal tests rather than a wrong step. Every proof with a failing step is reported, and I read the failing steps of each headline proof. A proof counts as certified only if all its steps reproduce or the failing ones are read by hand and valid; a step I find invalid withdraws that proof and starts a search for the same fault in all the others.

**The arm with every candidate is stopped** (job 1334653, after 10 rows). Pools of 1,100 or more hit the 1,800 s limit, three runs ended with no output, which is probably memory, and it proved nothing the pool of 256 had not. CLOSE-P2's K = all stays undecided. A larger pool needs a faster engine, and that is not the first gap until the proofs are trusted.

---

### Addendum to SIDE-GT-CLOSE: halved angles, and a strict arm (written 2026-11-06 08:3x UTC, before any strict result)

**Why.** Directed angles live modulo π, so 2a = 2b gives a = b or a = b + π/2. The closure's span is over the rationals and its constants are dropped, so a chase with a coefficient 1/2 picks that branch from the figure. I had this down as a later check. I have now counted it: **37 of the 44 proofs at K = 256 use at least one halved angle relation; all those fractions are in the angle system** (halving a log-length is sound, since lengths are positive). Fresh figures test the conclusion, not the deduction, so they can't settle it. Plain Newclid so far reproduces 3 of 22 problems within 600 s on 40 of the 44 rows. A fraction is not always a real branch: the log keeps only relations independent over the rationals, so an integer route can go unlogged because it was "not new".

**Design.** `GT_STRICT=1` replaces the angle span by one over the integers (`LinZ` in `geo_closure.py`): exact integer elimination on a coefficient ±1 only. A relation whose reduced form has a common factor g > 1 says only that g·x = 0, so it is not added, and x stays unproved. A relation with no ±1 coefficient and no common factor is also skipped and counted. This gives a sound lower bound on what integer chasing proves: a relation of the group is only used as an integer combination of relations true modulo π, whose constant is fixed exactly by its premises, and the figure then reads that constant. Same 59 translations, same pools, K = 64 and K = 256. Rules, the 8 fresh figures and the length system are unchanged. Output: `results/proof/sound3/gt_strict_k{64,256}.jsonl`.

**Predictions.**
- **CLOSE-P6 (decision):** strict K = 256 proves more than 2 problems, the pooling and pairs total that CLOSE-P1 compared against. Expected 14 of the 31, range 8–20. A real branch is likely on incentre problems (ISL 2016_23, IMO 2019 P6), and many other fractions look like circle rows with an unlogged integer route.
- **CLOSE-P7 (internal check):** no strict proof has a fractional coefficient in an angle chase. One violation is a bug, and the strict counts wait until it is found.
- **CLOSE-P8 (reported):** strict K = 64 proves 7 problems (4–11, the full arm's count).

**Decision.**
- CLOSE-P6 holds: the headline geometry counts use strict proofs only. Proofs that need a halved angle are reported separately as "proved given a branch read from the figure", and are never added to the headline.
- CLOSE-P6 refuted: the closure's gain is branch choice, CLOSE-P1 is withdrawn, and the next gap is proving the branch (running both cases of each halving), ahead of a larger candidate vocabulary.

**Correction to the strict design (2026-11-06 08:4x UTC, after the first strict K = 64 test; the predictions above stay as written).** Skipping a relation with a common factor is wrong. A proof with integer coefficients can use 2(a − b) = 0 directly, and with that relation gone the engine loses it: K = 64 fell to 2 problems, and IMO 2016 P1, whose recorded proof has only integer coefficients, was among the losses. So that number measures my shortcut, and it is not a result. Replacement: the rational span stays as a fast filter, and an exact integer lattice with torsion (`ZSpan`: unit eliminations plus an integer echelon form of the rest) runs beside it. Every rule's angle premises and the goal must be exact members of the lattice, and every relation that is new to the lattice is logged, including those the rational span already holds. Proof read-back gives each chase's exact integer combination by replaying the log. CLOSE-P8 was written before this and is scored on the replacement, knowing the shortcut's 2.

---

## SIDE-GT-DECL: statements with no construction order (written 2026-11-06 09:5x UTC, before any model translation in this language)

**Why.** With the closure, the translator is the limit: 19 of 65 held-out problems have a faithful translation. AlphaGeometry's language builds each point from earlier points, and half of the 260 translations came back UNEXPRESSIBLE. On 30 of the 65 problems every translation did; 5 more never got past build errors and 7 more failed the guard. Reading the statements, many of these 42 are out of reach of any deductive chase (inequalities, areas, three dimensions, counting). But some are ordinary configurations the language can't write, because a point is fixed by conditions on later points: IMO 2007 P2 (EF = EG = EC), ISL 2006 G2 (P, Q on KL by angle conditions), ISL 2008 (opc_IMOSL_2008_16), ISL 2013 (opc_IMOSL_2013_18). The closure takes only a figure and facts, so it does not need a construction. No one has joined these, as far as I found: Krueger, Han and Selsam (2012.02590) solve declarative statements numerically for diagrams with no prover; LeanEuclid formalises declaratively, with its own checker; AlphaGeometry and Newclid need constructions.

**Design.** `side/geo_decl.py`: a statement is points, hypotheses and one goal, with order conditions that only select the figure. Figures come from least squares from 80 random starts, with distinct names staying distinct. Of the solutions, those with the fewest chance collinear triples are kept, since a generic point of the solution set has fewest. Guard: the goal holds on every kept figure. An unsigned angle equality becomes a directed one with the figure's orientation, and the kept figures must share it, so the fact set is one. The goal must also be true on the figure, a test the closure now always makes. Translator: Qwen3.6-27B-AWQ, the same as SIDE-GT-H: `GT_DECL=1 gen <tag> <ids> --think --k 4 --repair 2 --grammar`. Dev first on the 24 dev problems, where the language and prompt may change. Then held out once on the 65, with faithfulness judged before any closure run, by SIDE-GT-H's protocol.

**A limit I already know.** A hand-written control: P inside triangle ABC, PB = PC, AP bisecting angle A, prove AB = AC. Without "inside" this is false (P can be the arc midpoint), and the closure proves it from directed facts that hold in both cases. It does so at a similar-triangles step from three side ratios, whose orientation (same or mirror) is read from the figure. Newclid and AlphaGeometry do the same with their numerical sameclock test, so a proof is valid for the figure's configuration. I report this limit with the counts and do not call these proofs configuration-free.

**Predictions.**
- **DECL-P1 (decision):** held out, problems with a faithful statement rise above 19. Expected 32, range 24–40.
- **DECL-P2 (reported):** problems whose every translation is UNEXPRESSIBLE fall from 30. Expected 20 (15–25).
- **DECL-P3 (decision):** end to end (faithful, proved by the strict closure at K = 256, on all fresh figures), more problems than the constructive translations give under the same engine, including at least one the constructive language had no faithful translation for. Expected +6 (+2 to +12).
- **DECL-P4 (reported):** tokens per translation stay near 12.5k.

**Decision.** P1 and P3 hold: the declarative form replaces the construction language for the pipeline, and the agreement check is rebuilt on it (each statement's hypotheses and goal on the other's figures). P1 holds and P3 fails: the new problems are beyond the engine, which is then the gap again. P1 fails: reading the statements decides between the model and the language.

**Dev result rule.** On dev I may change the prompt and language. Nothing from the held-out 65 is read for that, beyond what is already written above. Disclosure: writing this, I read the statements of the 46 held-out problems without a faithful translation, and hand-wrote three of them (IMO 2007 P2, ISL 2006 G2, opc_IMOSL_2008_16) to test the solver and closure. The prompt's examples are my own and none of them. The closure proved IMO 2007 P2 from my hand statement with 5 points. That is not counted: only the model's statements count.


**Results of the strict arm (2026-11-06 10:4x UTC; job 1337021 at K = 256, K = 64 on the login node; step replay still running).**

A correction to my own counts first. I reported 23 of 31 problems at K = 256. Four row ids are second names of IMO-AG-30 problems (hf_2010, hf_2015, opc_IMOSL_2008_14, opc_IMOSL_2012_19), and two more among the unproved (hf_2020, hf_2021), and I had merged only some of them. Distinct problems: **21 of 29** for the rational arm at K = 256, not 23 of 31. K = 64's 11 was right. All counts below are distinct problems.

| Arm | K = 64 | K = 256 |
|---|---|---|
| Rational span (halves an angle using the figure) | 11 | 21 |
| Strict integer lattice | 10 | 20 (+ IMO 2002 P2a, which times out at K = 256 and is proved at K = 64: 21 together) |

- **CLOSE-P6 holds:** 20 problems, above the 2 of pooling and pairs, at the top of my range (8–20). CPU per translation: 105 s mean, against about 8,000 s held out and 9,600 s on the references for the pooling and pairs arms. So the halved angles cost almost nothing. ISL 2016_23, lost at K = 64, comes back at K = 256 with more points, so my guess that it needed a real branch was wrong.
- **CLOSE-P7 holds:** none of the 43 strict proofs has a fractional angle coefficient.
- **CLOSE-P8:** 10, in the range (4–11), above the 7 expected.
- **CLOSE-P3 holds on the strict proofs:** every step on 8 of 8 fresh figures. This shows truth on the figures, not the deduction.
- **CLOSE-P4 refuted:** plain guarded Newclid reproduces 3 of the 21 problems (4 of 44 rows, 2 rows stopped unfinished after over an hour), not half.
- **CLOSE-P1 stands, as decided by P6.** The closure replaces single points, pairs and pooling, once the proofs are certified.
- **Counts if the certificate holds:** IMO-AG-30 **24 of 30** (13 + 11; the row ids match the benchmark's names), unproved: 2008 P1b, 2008 P6, 2011 P6, 2019 P2, 2020 P1, 2021 P3. Held out, end to end, **17 of 65** out of 19 faithful (7 + 10, each with a translation judged faithful before any proof). These are proofs for the figure's configuration: a similar-triangles step from side ratios reads its orientation from the figure, as Newclid's and AlphaGeometry's sameclock test does.
- **Step replay (CLOSE-P5), first run: not usable for similar triangles.** 810 steps, 512 reproduced, and no proof fully. Isosceles 203 of 203, lines 81 of 86, inscribed 57 of 60, midline 34 of 34, perpendicular bisector 42 of 42. But 275 of 298 similar-triangle steps failed, 201 of them with an IndexError, because Newclid can't take simtri as a goal here. That is the replay's fault and says nothing of the step. Fixed: a similar pair is replaced by its angle and ratio statements, as goal and as lemma. Rerun on 21 strict proofs, one per problem (job 1337470).
- **Hand reading:** IMO 2016 P1 (no extra points): triangles ABF, ACD, ADE similar, then A, B, D, E, M concyclic, MB = MF from the right median, and B, F, M, Y and D, M, X, Y concyclic carry it to the collinearity. This is the shape of the known solution. With IMO 2000 P6 and IMO 2018 P1, three are read at the level of key lemmas.

---

## SIDE-GT-SAT: a pool the closure grows itself (written 2026-11-06 10:4x UTC, before any run)

**Why.** Six IMO-AG-30 problems and two faithful held-out ones stay unproved. A random pool of one-step points can't reach points built on auxiliary points, and pools over 1,100 points run out of time and memory. A point that adds no relation among the existing points can't contribute through linear chasing, so the pool needs only points that add something.

**Design.** Round by round from the statement's points: draw a budget of 2,000 one-step candidates over the current points, seeded by the round. For each, run the strict closure on the current points plus that one candidate, and test whether the relations among the current points grew: the rank of their direction and log-length variables, computed exactly mod P. Keep every candidate that adds one, promote them all to points at once (closure is monotone, so this can't lose a proof), and repeat. Stop when the goal falls, no candidate adds anything, or the time limit (1,200 s) comes. Then read the proof back and keep only the points it needs and their parents. Fresh figures as before. Limit: two points each useless alone but useful together are missed unless something else makes one productive. Same 59 translations. Output \`results/proof/sound3/gt_sat.jsonl\`.

**Related work.** Chou, Gao and Zhang (2000) add points inside a deductive database and AG2 (2502.03544) and HAGeo (2512.00097) choose points by language model or heuristics, then search. I found none that keep points by a measured rank gain.

**Predictions.**
- **SAT-P1 (decision):** proves at least one of the 8 problems the strict closure leaves unproved at K = 256 (2002 P2a excluded, which K = 64 proves). Expected 2, range 0–4.
- **SAT-P2 (reported):** of the 21 proved, it proves 15 (10–21), at less CPU per translation than K = 256's 105 s on average.
- **SAT-P3:** every step on every fresh figure.

**Decision.** SAT-P1 holds and the new proof certifies: saturation replaces the random pool, and the counts are restated. It fails: the remaining gap is not points. The unproved problems' known solutions are then read for what the engine lacks (rules, or inequalities and order), and that is the next step.

**Change to SIDE-GT-SAT's design (2026-11-06 10:4x UTC, before any run on the 8 unproved problems; the predictions above stay, and one is added).** A smoke test on proved rows refuted the keep-if-it-adds rule. For IMO 2018 P1, none of 279 candidates adds a relation among the existing points alone, because its two needed points only help together. Counting relations that involve the new point instead, against the two closures apart (the statement's, and the candidate's own definition's), needed points have a gain above 0 in 83 of 110 cases and random candidates in 598 of 1,124. That is too many to keep them all, but a needed point's gain is often large (IMO 2000 P6: 54).

New design: **greedy on gain.** In a round, each of 2,000 one-step candidates over the current points is scored by its gain, and the best one becomes a point, so later rounds can build on earlier points. Stop when the goal falls, no gain is above 0, or at 1,800 s. Why greedy: the rank of linear relations is submodular, so this is the greedy algorithm for a monotone submodular objective (Nemhauser, Wolsey, Fisher 1978), when the other rules add nothing. They do add, so this motivates the method and doesn't guarantee anything.

What I saw before writing this, at a budget of 300 on 8 rows already proved at K = 256 (IMO 2018 P1, 2009 P2, 2012 P5, 2019 P6, 2015 P3, 2000 P6, ISL 2022_19, USAMO 2009 P5): all 8 are proved, by 1 to 10 points, in 2.5 to 82 s, with no fractional angle and every step on 8 of 8 fresh figures. IMO 2018 P1 takes 2.7 s with two reflections. That is above SAT-P2's range on its small sample, so I add **SAT-P4 (reported, made now):** at the full budget, at least 18 of the 21 are proved, at a mean under 105 s per translation.

Same rows and output. SAT-P1 and its decision stand, and the new proofs of the 8 problems go to the step replay and to reading by hand before any count changes.

---

## SIDE-GT-SQ: squared lengths as a third linear system (registered 2026-11-06 11:5x UTC)

**Why.** SAT's first rows show two separate things (it is still running, and those rows are the only evidence read so far). IMO 2020 P1 is proved, by the points of the textbook solution. IMO 2011 P6 is "proved" by a false proof: a reflection fell 7e-5 from an existing point in the one figure, so facts about that near-coincident pair passed the numeric test, gained 71 relations, and every fresh figure rejected the result. Maximising gain selects exactly such accidents. Reading what the unproved problems lack gives a third thing: the engine chases angles and log lengths, and nothing additive. IMO 2008 P1b has a known proof by Pythagoras that needs neither.

**Theory.** For any four points of the plane, ab ⟂ cd holds exactly when ac² − ad² − bc² + bd² = 0. It is an identity in the dot product, so it is linear in squared lengths and has no branch or orientation. Equal lengths are s_ab = s_cd. A midpoint m of ab gives, for every x, 2·xm² + 2·ma² = xa² + xb², and ab² = 4·ma². So squared lengths form a third linear system with membership tested the same way, with two-way bridges: a perpendicular proved in angles enters squares, one proved in squares enters angles, and likewise equal lengths. Chou, Gao and Zhang's Pythagoras differences (1993–94) use these quantities by elimination in a constructive order; I found no account of one as a span inside a forward closure, and Newclid's Pythagorean rules are single rule instances. That search was short, so this is not a claim of priority.

**Derivation for IMO 2008 P1b (done by hand, before any run).** With O the circumcentre and D the midpoint of BC: OA1² = OD² + DA1² (OD ⟂ BC) = OD² + DH²; OD² = R² − BC²/4 by the median identity at O; DH² = (HB² + HC²)/2 − BC²/4 by the median identity at H. So OA1² = R² + (HB² + HC² − BC²)/2. This is the same for each side exactly when HB² − HA² = BC² − CA², which is the four-point identity for CH ⟂ AB. So the proof is linear in squares, and takes one point, the circumcentre.

**Design.** Same rows and output format as SIDE-GT-SAT, on the strict engine (`GT_STRICT=1 GT_SQ=1`), with two changes to the greedy:
- **Two figures (`GT_TWOFIG=1`):** a candidate that would lead a round has its gain recomputed on a second independent figure, and the lower counts; the goal must fall on both. This uses no distance threshold.
- **Second intersections (`GT_SECOND=1`):** the candidate language lacked them. A line through a point of a circle meets it again; two circles through a point meet again. Each has one root and no branch. Known solutions use them often, for example IMO 2019 P2.

**Predictions.**
- **SQ-P1 (decision):** IMO 2008 P1b is proved, with a proof that uses the squares system. This is a derivation, so failure means the engine or the translation is wrong.
- **SQ-P2:** IMO 2011 P6 is no longer proved. Every proof holds on 8 of 8 fresh figures.
- **SQ-P3:** of the other 6 unproved problems (2008 P6, 2019 P2, 2021 P3, 2011 P6, USAMO 2005 P3, ISL 2012_22), 1 is proved, range 0–2. 2019 P2 is the likeliest. 2008 P6 and 2011 P6 are not.
- **SQ-P4:** no problem SAT proves in under 1,800 s is lost, except through the second figure rejecting an accident.

**Decision.** SQ-P1 holds and the proof reads as derived: the squares system stays in the engine, and the counts are restated with it, each new proof being read first. SQ-P1 fails: read why before anything else runs on it. If SQ-P3 gives 0 although hand-added points prove those problems, the gap is search, and the greedy's drift (below) is next. If hand-added points do not prove them, the gap is theories or order.

**Open, and not part of this test:** on all 8 timed-out rows the gain rises by round (for example 7, 10, 7, ..., 45 on IMO 2019 P2). Rank among new points grows on its own, so the score drifts away from the goal, which fails the diminishing returns the greedy's motivation assumed.

**Hand checks, 2026-11-06 11:5x UTC, made after the text above and before reading the run (job 1337925).** With the circumcentre given, IMO 2008 P1b is proved at once, with no fractional coefficient and every step on 8 of 8 fresh figures. The proof is simpler than my derivation: no median identity, only midlines and six four-point identities. So SQ-P1's engine half is already seen; the test that remains is the greedy finding that point itself. With the two second intersections of the known solution given (A2 on AA1, B2 on BB1), IMO 2019 P2 is proved in one round. So its gap was the candidate language, not the rules.

### Results of SIDE-GT-SAT and the step replay (2026-11-06 12:3x UTC)

- **SAT-P1 holds, pending the check below:** 1 of the 8 (IMO 2020 P1), expected 2, range 0–4. Its points are the known solution's X and Y. A second "proof" (IMO 2011 P6) is false: every fresh figure rejects it.
- **SAT-P2:** 18 of the 21, in range, but not at less CPU: the mean over all rows is 566 s against 105 s, because 18 rows run to the 1,800 s limit. On rows it proves it usually takes seconds. So greedy and pool are complementary, and it loses USAMO 2012 P5, CAMO 2020 P3 and ISL 2004 G8. "Replaces the random pool" stands only for what it proves; counts are the union of arms.
- **SAT-P3 refuted:** the false proof above. **SAT-P4:** 18 of 21 holds, the mean under 105 s does not.
- **CLOSE-P5 refuted by 0.2 points:** 490 of 614 steps reproduce (79.8%), and only 2 of the 21 proofs reproduce whole (Indonesia 2007 P7, IMO 2009 P2). Similar triangles fail 96 of 237. Failures are mostly Newclid stopping without the goal, not timeouts. By the registered rule, the other 19 are not certified until their failing steps are read.

## SIDE-GT-CHECK: an independent checker instead of reading 124 failing steps (registered 2026-11-06 12:3x UTC)

**Why.** Newclid's failure to reproduce a step says little, since it fails on steps I can verify by hand, and 124 steps cannot be read reliably. The rule's purpose is that an independent party confirms each step. So: `side/geo_check.py`, which imports nothing from the engine and uses exact fractions. It checks three things for every row: the relation is what the rule's conclusion says, including its constant (0 or π/2 for directions, multiples of log 2 for log lengths), which the engine drops; the premises and conclusion fit the rule's statement; each premise and the goal are exact combinations of earlier rows, integer for directions. A fact about an auxiliary point must be what its construction states.

**What it does not check.** Non-degeneracy, the statement's own facts (they come from Newclid's construction language), and rules that read a configuration from the figure, which it counts per proof: similar triangles from sides, and side-angle-side, since a directed angle mod π does not fix an interior angle; Thales' converse; the trapezoid rule. Its trust base is about 20 classical lemmas stated in code that a reader can check.

**Seen before registering:** three proofs pass (IMO 2018 P1, with one similar-from-sides step; IMO 2008 P1b; IMO 2019 P2, both with no configuration step). Mutating those certificates 800 times, all changes to coefficients, relations and constants are rejected; those that pass change only a tag or a dropped row on a circle's chord that nothing uses.

**Predictions, on every proof of the strict, greedy and squares runs.**
- **CHECK-P1 (decision):** at least 95% of proofs pass. A failure is read: if the proof step is wrong, the proof is withdrawn and the same fault searched for; if my checker lacks a form, that is fixed and reported.
- **CHECK-P2:** the false IMO 2011 P6 proof is rejected or rests on a configuration step. If it passes clean, the checker's guarantee is weaker than stated, and this is the most important result of the run.
- **CHECK-P3:** at most half of the proofs of the 27 problems use a configuration step.

**Decision.** A proof counts as certified if it passes this checker and holds on 8 of 8 fresh figures; its configuration steps are reported with it. This replaces, for certification, the requirement that Newclid reproduce each step. The replay's numbers remain reported as they are.

Correction to the paragraph above: the mutation count was 891, not 800.

### Results of SIDE-GT-SQ (2026-11-06 13:3x UTC; job 1337925; the checker's verdict is still to come)

- **SQ-P1 holds:** the greedy finds the circumcentre and proves IMO 2008 P1b in 4 s, by the squares system.
- **SQ-P2 holds:** IMO 2011 P6 is no longer proved, and all 43 proved rows hold on 8 of 8 fresh figures.
- **SQ-P3 holds at 1:** IMO 2019 P2, in 28 s; its two points reach the known solution's points on the circumcircle by other constructions. Unproved: IMO 2008 P6, 2011 P6, 2021 P3, USAMO 2005 P3, ISL 2012_22.
- **22 problems proved,** one more of them over SAT than the predictions counted: ISL 2004 G8, which SAT lost, is back at 149 s. USAMO 2012 P5 and CAMO 2020 P3 stay lost; only the pool of 256 proves them.

## SIDE-GT-LUBY: restarts, because a single greedy chain has a heavy tail (registered 2026-11-06 13:3x UTC)

**Why.** The run times are heavy-tailed: proved rows mostly take seconds (median below), and the rest run to the limit with gain rising, because the chain has drifted and each round gets slower as points are added. USAMO 2012 P5 and CAMO 2020 P3 show the cost: a random pool proves them and the chain does not.

**Theory.** Gomes and Selman (1998) showed that restarts remove heavy tails in randomised search. Luby, Sinclair and Zuckerman (1993) give a universal schedule 1, 1, 2, 1, 1, 2, 4, ...: with no knowledge of the distribution, its expected time is within a logarithmic factor of the best fixed cut-off. So no cut-off is chosen by hand. The unit only changes a constant.

**Design.** Same 59 rows, 1,800 s, with the engine of SIDE-GT-SQ. Run j stops after luby(j) × 300 candidates and restarts from the statement with a fresh sample, so a run of unit 2^i can reach 2^i rounds. The budget of 300 per round is the one used in the smoke test, and a larger one only makes each round's choice more exacting: it is not tuned on the outcome rows.

**Predictions.**
- **LUBY-P1 (decision):** it proves at least one of USAMO 2012 P5, CAMO 2020 P3 with no loss among the 22 problems SIDE-GT-SQ proves. Expected: both. Loss of up to one problem is allowed only in the prediction below.
- **LUBY-P2:** of USAMO 2005 P3 and ISL 2012_22, it proves 1, range 0–2. IMO 2008 P6, 2011 P6 and 2021 P3 stay unproved: they lack theories, not search.
- **LUBY-P3:** mean time on the rows both arms prove is no worse than twice SQ's, as the bound's log factor allows.

**Decision.** LUBY-P1 holds: restarts become the default search, and the counts are restated from the union with the checker. It fails: drift is not what separates those rows, and the score itself is the next thing to replace, for example by counting only relations among the statement's own points.

Note to SIDE-GT-LUBY's "Why": the proved rows of SIDE-GT-SQ have median 4.5 s, mean 22.3 s and maximum 257 s. Job change (2026-11-06 15:0x UTC): the CPU queue offered a start 2 days away, so `clluby` runs as job 1339457 with 4 workers on a GPU node's CPUs instead of 8. The time limit per row (1,800 s) is unchanged. No results had been read.

### Results of SIDE-GT-CHECK (2026-11-06 15:0x UTC; `results/proof/sound3/gt_check_*.jsonl`; run on the login node, about 1 s per proof, because the CPU queue offered a start a day away)

- **CHECK-P1 holds:** 150 of 151 proofs pass (99.3%, bar 95%). Four proofs failed at first on a fault of the checker's: a chord premise is written `tdiff <circle>` in the row and `tdiff` in its combination, so the lookup missed it. Fixed, and the fix also requires the combination to be on the named circle. All four then pass.
- **CHECK-P2 holds, in its strong form:** the false IMO 2011 P6 proof is rejected, with no configuration step involved: "row 76: premise para pc _x3 _x2 _x3 has constant -1/2, not 0". The exact combination proves those lines perpendicular, and the proof uses them as parallel. The engine drops constants and takes them from the figure, where a nearly coincident point (7e-5) made the wrong one look true. So the checker catches what the engine's numerical truth test misses, and no other proof of the 151 has this fault.
- **CHECK-P3 refuted:** 137 of the 150 passing proofs use a configuration step (91%, predicted at most half), nearly all similar triangles by side-angle-side. By problem, 20 of the 27 of IMO-AG-30 have no proof without one. Such a proof holds for the figure's configuration, not for every configuration, and is reported that way. No proof needs a fractional direction coefficient or a constant from the figure.

**Decision applied: certified = passes the checker and holds on 8 of 8 fresh figures.** The earlier guarded counts rested on Newclid's proofs, which the checker cannot read, so their 44 rows were rerun through the closure: 33 with no new point (at most 0.02 s), 6 by the greedy (at most 73 s), 5 by the greedy after removing a fixed auxiliary point the search could not parse (at most 3.3 s). All 44 pass the checker and hold on 8 of 8 fresh figures. Totals, 195 proofs: 194 pass, 176 with a configuration step.

| Count | Certified | Before |
|---|---|---|
| IMO-AG-30, from reference translations | **27 of 30** (unproved: 2008 P6, 2011 P6, 2021 P3); 7 with a proof free of configuration steps | 13 |
| Held out, end to end, translations judged faithful by hand | **17 of 65**, of 19 faithful (unproved: USAMO 2005 P3, ISL 2012_22); 3 free of configuration steps | 8 |
| Held out, end to end, no human (corroborated by SIDE-GT-AGREE) | **13 of 65** | withdrawn 8 |

Comparison: HAGeo reports 28 of IMO-AG-30 (2512.00097). Its code is not public, and we do not know how its proofs treat configurations, so this is not a like-for-like comparison. Each of our numbers depends on the checker's trust base: about 20 classical lemmas, the construction facts from Newclid's language, and non-degeneracy, none of which it proves.

Correction to the comparison in SIDE-GT-CHECK's results (2026-11-06 16:4x UTC): naming only HAGeo was too narrow. On IMO-AG-30, AG2 and TongGeometry report 30, HAGeo 28, Wu with AG1 27, and random points in HAGeo's engine 25. HAGeo-409 is the harder public benchmark. Details: `docs/notes/RELATED_WORK.md`.

### Results of SIDE-GT-LUBY (2026-11-06 17:0x UTC; job 1339457, `results/proof/sound3/gt_luby.jsonl`)

59 rows, 47 proved, against 43 for SIDE-GT-SQ. All 47 pass the checker after one fix, and all hold on 8 of 8 fresh figures.

- **LUBY-P1 holds, at its low end:** it proves CAMO 2020 P3 on all 4 translations (390–1,088 s, up to 31 restarts) and loses none of the 22 problems. It does not prove USAMO 2012 P5, which only a random pool does. I expected both.
- **LUBY-P2:** USAMO 2005 P3 and ISL 2012_22 stay unproved (predicted 1, range 0–2: in range, below the point). IMO 2008 P6, 2011 P6 and 2021 P3 stay unproved, as predicted.
- **LUBY-P3 fails:** mean time on the 43 rows both prove is 65.0 s against 22.3 s, 2.9 times (limit 2). This run had 4 workers on another node against 8, so the ratio is rough.
- **A checker fault, fixed:** three CAMO 2020 P3 proofs failed at a step uniting collinear triples, because my merge stopped before reaching a fixed point. Read by hand: the chain from the premises reaches the conclusion. All proof sets were rechecked with the fix, with no change in any other verdict.

**Decision applied: restarts become the default search.** The counts do not change: USAMO 2012 P5 and CAMO 2020 P3 were already in the union, by random pools. What restarts add is that the same search finds CAMO 2020 P3 with no pool. This says little against prior work: HAGeo finds random points already strong at scale, so the comparison that matters is HAGeo-409.

## SIDE-GT-H409: the closure with restarts on HAGeo-409 (registered 2026-11-06 17:0x UTC)

**Why.** IMO-AG-30 is saturated and easy: AG2 and TongGeometry report 30, and random points in HAGeo's engine reach 25. HAGeo-409 (Duan et al., 2512.00097, public) is harder (mean difficulty 3.47 against 2.85) and carries difficulty scores. Whether our engine and search compete has to be answered there.

**Published results, of 409.** AG1 with beam (16, 64, 8): 177. Random points in HAGeo's engine: 204 at K = 2,048, 218 at K = 8,192. HAGeo: 263 at K = 2,048, 287 at K = 8,192. Their conditions: up to 6 points per attempt, 60 s per DDAR run, a 64-core machine. Proofs on HAGeo-409 are not reported as checked by hand; on IMO-30 they are. HAGeo's code is not public, so its numbers are cited, not rerun.

**Design.** The dataset's AlphaGeometry statements, which its authors corrected by hand; the point's own name is added where its clauses omit it (`nlp_data/geo/hageo409/conv.py`). 399 build a figure within 4 s on seed 0; 5 time out in that test and 5 fail, 4 of them for a construction (`eq_trapezoid`) our language lacks. Failures count as unproved. Engine as in SIDE-GT-LUBY, the search by its decision: strict lattice, squared lengths, two-figure gain, second intersections, restarts, 1,800 s per problem on one core. **A problem counts only if its proof passes `geo_check.py` and holds on 8 of 8 fresh figures,** a stricter bar than the published numbers, and on far less CPU than K = 8,192 attempts of up to 60 s.

**Predictions.**
- **H409-P1 (decision):** 234 of 409, range 190–280. By band: [1,3) 140 of 161; [3,4) 70 of 112; [4,5) 20 of 71; [5,6) 4 of 43; [6,7] 0 of 22.
- **H409-P2:** at least 99% of proofs pass the checker. Any failure is read as in SIDE-GT-CHECK.
- **H409-P3:** on the problems proved, the median is below 60 s, because proved rows of SIDE-GT-SQ have median 4.5 s and these are easier on average than those 59 rows, which were selected as hard.

**Decision.**
- **At least 263 (HAGeo at K = 2,048):** the engine and search compete with published work, with certificates. The next step is the same benchmark end to end from its natural-language statements.
- **218 to 262 (above random at K = 8,192):** the search is doing something, but less than HAGeo's construction rules. Next: run the same engine with uniformly random points, the published baseline's design, so that the greedy's own value is measured on the same engine and CPU.
- **Below 218:** the engine is the limit. Next: read the unproved problems below difficulty 3, where HAGeo proves 92.5%, and find which rules or theories are missing.

### SIDE-GT-DECL dev: first read (2026-11-06 17:3x UTC; job 1337117, `results/proof/gt_gtdecl_dev.jsonl`; dev problems only)

Same model, same 24 problems, 4 translations each, against the construction language.

| Last status | Declarative | Construction |
|---|---|---|
| Passes the guard | 43 | 15 |
| Problems with one that passes | 15 of 24 | 7 of 24 |
| Build error | 0 | 35 |
| No figure | 16 | 0 |
| Goal fails | 5 | 11 |
| Unexpressible | 32 | 34 |
| Tokens per translation | 20.1k | 19.2k |

Passing the guard is not faithfulness: one translation of ISL 2017 G18 states a different figure, and hand reading is still to come. USAJMO 2012 P1, unexpressible or a build error in the construction language, goes through the guard, the closure (24 s, one point) and the checker. Tokens run well above DECL-P4's 12.5k, as they do for the construction run on this set. Running: the closure on the 43 statements (job 1341956), and whether 5 times the starts finds figures for the 16 without one.

### SIDE-GT-DECL dev: proofs and the step to held out (2026-11-06 18:1x UTC)

The closure with restarts proves 42 of the 43 statements, all 15 problems with a passing statement, mostly within 60 s. Certificates are running (job 1342110). **I treat this number as suspect until the raw statements are read, and I read them.** What I saw:
- **Faithful as far as I can read:** USAJMO 2012 P1, IMO 2014 P4 (the two with a point X), IMO 2010 P2, ISL 2012 G19, ISL 2008 G14, ISL 2011 G11, Romanian NMO 2006 P2 (goal: only the midpoint half).
- **Half of an "if and only if":** USAMO 2003 P4 and ISL 2010 G17. Each proof is one direction.
- **Changed problem:** Canadian 2006 P2 asks for a locus, and the statement picks a claim; IMO 2007 P4 asks about areas, and the statement gives a ratio.
- **Fewer hypotheses:** IMO 2020 P1 drops the 1 : 2 : 3 ratios. A proof from fewer hypotheses still proves the problem, if the configuration matches, and the fresh figures hold.
- **Wrong:** one translation of ISL 2017 G18 copies the prompt's own example. A goal changed like this should fail agreement with the others; it does not fall to the guard.

So 42 of 43 is what a sound engine does on true statements, and it counts for nothing until faithfulness is settled. The registered rule stands: faithfulness on the held-out set is judged before any closure run on it.

**Changes from dev, frozen now:** figures from 240 starts instead of 80, because 400 starts found figures for about half of the 16 statements that had none. Nothing else changes. **Held out: job submitted now, same prompt and model, tag `gtdecl_eval`, 65 problems × 4.**

### SIDE-GT-DECL: agreement rebuilt, and how held-out statements will be judged (2026-11-06 19:2x UTC; before reading any held-out statement)

**Agreement (`geo_decl.py agree`).** Statement b holds on a's figures when, on every figure of a that meets b's order conditions, all b's facts and its goal are true, with at least one such figure. Points match by name; the rest by trying assignments. Two statements corroborate each other when each holds on the other. On the 43 dev statements: 36 are corroborated, on 11 of 15 problems. The copied prompt example (ISL 2017 G18 T3) is rejected against all three others, and T0 is not corroborated either. **It does not catch shared changes.** All four USAMO 2003 P4 statements agree, though each states one direction of an "if and only if", and IMO 2007 P4's two ratio statements agree with each other.

**Verdicts, fixed now, each translation read before any closure on it:**
- **Faithful:** every hypothesis is stated, or dropping it only makes the claim stronger; the goal is the claim asked. Naming one of several open objects counts, as registered in SIDE-GT-AGREE.
- **Half:** one direction of an "if and only if", or one part of a claim with several. Reported apart, and not counted in the faithful or the end-to-end count. In the 19 faithful constructive problems, the same rule is applied by rereading those verdicts, and any change is reported.
- **Changed:** the goal is the model's own reformulation, or a locus or value question turned into a chosen claim. Not faithful.
- **Wrong:** anything else.

### SIDE-GT-DECL held out: translations and verdicts (2026-11-06 21:5x UTC; job 1342116; verdicts written before any closure or agreement run on these statements, `results/proof/gtdecl_eval_faithful.json`)

65 problems × 4. Last status: 97 pass the guard (on 29 problems), 114 unexpressible, 27 goal fails, 20 no figure, 2 syntax errors. 17.3k tokens per translation. I judged the 97 by hand: 65 faithful, 25 half, 5 changed, 2 wrong.

| Problems | Declarative | Construction |
|---|---|---|
| At least one faithful translation, whole claim | **20** | 14 |
| Faithful for one part of the claim only (half) | 7 | 5 |
| Total, the count DECL-P1 was registered on | **27** | 19 |
| Every translation unexpressible | 24 | 30 |

- **DECL-P1 holds:** 27 against 19, in the range 24–40 and below the expected 32. New with a whole-claim translation: ISL 2001 G1, ISL 2004 G2, ISL 2006 G2, IMO 2007 P2, ISL 2008 G16, USAMO 2009 P1, ISL 2013 G18. Lost: USAMO 2001 P2.
- **DECL-P2 holds:** 24 (expected 20, range 15–25).
- **DECL-P4 fails:** 17.3k tokens against a predicted 12.5k.
- **A correction to the earlier counts, by the rule fixed above.** Rereading my construction verdicts' notes, 5 of the 19 "faithful" problems were one direction or one part: Pan African 2004 P6, Romanian NMO 2006 grade 9 P3, Indonesia 2007 P7, USAMO 2009 P5, ISL 2016 G23. All five are among the 17 reported as proved end to end. **So 17 of 65 end to end means 12 whole problems and 5 parts.** The no-human 13 is restated when agreement is rebuilt.
- **Two judgment calls, reported:** I count USAMO 2010 P1's goal as faithful (XAZ for half of XOZ, one inscribed-angle step, as I did before); and order conditions narrower than the statement, such as "inside triangle ABC" for "inside ABCD" in ISL 2008 G16, as a sub-case of a figure, since a proof holds for its figure's configuration anyway.

Closure on all 97 (job 1343465) and agreement (job 1343466) are now running. DECL-P3 is read from them.

### SIDE-GT-DECL: agreement read against the verdicts (2026-11-06 23:0x UTC; job 1343466, `results/proof/gt_gtdecl_eval_agree.jsonl`, 254 ordered pairs; verdicts were fixed before this ran)

| Verdict | Statements | Corroborated |
|---|---|---|
| Faithful | 65 | 57 (88%) |
| Half | 25 | 25 |
| Changed | 5 | 4 |
| Wrong | 2 | 1 |

**The rebuilt agreement check fails as a certificate: precision is not 1.** AGREE-P1 held on the construction language; here 5 of 7 unfaithful statements pass. On one problem every statement is unfaithful: USAMO 2006 P6 asks that four circles pass through a common point, and each translation assumes three of them concur (`cyclic s a e p; cyclic s b f p; cyclic t c f p`), one with the empty goal `cong p p p p`. They agree because they share the error. The other is USAMO 2012 P5, sample 0. Half translations pass by construction: all of a problem's translations drop the same direction. So in this language the no-human count cannot use agreement alone. Eight faithful statements fail agreement, mostly on ISL 2001 G1 and ISL 2017 G19, not yet read.

### SIDE-GT-H409: interim (2026-11-06 23:0x UTC; shard 0 done; two shards running; **not the registered reading**)

374 of 409 rows done: 261 proved, 257 with 8 of 8 fresh figures; by band [1,3) 139 of 160, [3,4) 84 of 111, [4,5) 29 of 68, [5,6) 5 of 28, [6,7] 0 of 7. Median proved 1.8 s. Checker on 259 certificates: 252 pass, 7 rejected, 97.3% (P2 predicted at least 99%, final reading pending). Four rejections have a chord premise with constant ±1/2, the same fault as the false IMO 2011 P6. I read one, USA TST 2013 P2: C and T are antipodal, so t(C) − t(T) = 1/2, but the engine accepts equal chords as if the difference were 0, which assumes the theorem's key step. **That is an engine soundness fault, and the checker is what catches it.** The fix (the premise's constant must be 0) waits for the running jobs; rejected rows are then rerun and reported apart.

## SIDE-GT-REDUCE: a hypothesis the others imply becomes a goal (written 2026-11-07 01:2x UTC, before any reduction run; the statements it first runs on have verdicts I have already read)

**Why.** Agreement between translations can't support a no-human claim: it passes 5 of 7 changed or wrong statements, and all four translations of USAMO 2006 P6 assume three of the circles concur, which is the claim. Reading prior work (`docs/notes/RELATED_WORK.md`, today) found no reference-free check for this.

**Derivation.** Let H be the hypotheses and g the goal. If H without h implies h, and H implies g, then H without h implies g. So a redundant hypothesis need not be rejected or judged. It can be dropped and proved, which gives a stronger statement that assumes less, with the same certificates. If a translation assumes a claim the rest implies, this puts the claim back among the goals, whatever the source said. A faithful statement with a harmless repeat costs one more proof, not a rejection.

**Test for redundancy.** Jacobian rank of the hypothesis equations at solved figures (Michelucci and Foufou, ADG 2006, §4.5, for CAD constraints; no use on translated statements found, search in RELATED_WORK, which does not make it new). A hypothesis is a candidate when its equations lie in the span of the others at every one of three figures. A candidate that fails on some figure of the remaining hypotheses selects a branch, and stays. One basis per first choice; a statement counts as reduced when every obligation of some basis has a certified proof.

**What it can't do, stated first.** It does nothing for half translations (no equation is dependent), for a claim that replaces a definition (rank stays full), or for added hypotheses that are independent. ISL 2014 G20's two bad statements are expected to pass unflagged.

**Exploratory reading already done (97 statements, verdicts known, not evidence).** With duplicates removed, at one figure: 13 of 53 faithful statements with a figure have a dependent equation, 8 of 21 half, and 4 of 6 changed or wrong (USAMO 2006 P6 samples 0, 1, 3; USAMO 2012 P5 sample 0, where the redundancy is one angle sum and doesn't explain the change).

**Run.** `side/geo_decl.py reduce` on the 97, then the closure at K = −300 on the obligations, as the DECL closure run, with certificates. Exploratory, on read statements, to find out if the proofs exist at all. A registered claim needs statements not yet read, and predictions go here before that run.

**Predictions for this exploratory run (fixed now).**
- **REDUCE-E1:** USAMO 2006 P6 has at least one sample with every obligation proved and certified, which would put that problem's claim back among the goals. I put this at 40%: the assumed-concurrency proofs took about 2 minutes, and the honest claim has one more circle to reach.
- **REDUCE-E2:** of the faithful statements with candidates, at least 70% of those with a certified original proof reduce fully. Harmless redundancy should be near-trivial to prove.

**Decision.** E2 fails: redundancy on faithful statements is hard to discharge, so reduction costs proofs, and the method stops as a default. E2 holds: reduction becomes the pipeline's default and is registered on a fresh statement set, with the verdict rule read before any proof.

### SIDE-GT-REDUCE: reading (written 2026-11-07 09:5x UTC; job 1346385; the 97 statements' verdicts were known, so this is exploratory)

- **REDUCE-E1 holds (I put it at 40%).** Sample 3 of USAMO 2006 P6, a `changed` statement that assumes P lies on circle TCF, has a basis that drops exactly that hypothesis. The closure proves it from the other hypotheses in 118 s, the checker passes it, and it holds on 8 of 8 fresh figures. With the certified original proof, H without h now proves both h and g: P on circles SAE and SBF implies P on TCF and on TDE, which is the problem's claim. Sample 1 does the same (8 of 8). I read the proof: it is the textbook one. P is the centre of a spiral similarity (PAE to PBF), the ratio AE/ED = BF/FC then gives PED similar to PFC, and an inscribed angle gives the circle. It uses the ratio, and it needs 8 non-collinear triples and reads 3 configurations from the figure. Not every basis closes: dropping circle SBF timed out at 1,800 s on all three samples, so "reduces" here means that the basis that matters closed.
- **REDUCE-E2 fails as registered: 3 of 6, against at least 70%. The three failures are a fault of ours, not hard obligations.** All six unproved obligations on those statements are `circle o x y` goals, the closure raised IndexError on a three-point circle goal, and they are trivial: `midp o a b` gives `circle o a b`, and `circle o1 x y r s` contains `circle o1 x y`. No proof was attempted on them.
- **Fix, before rerunning.** `reduce_one` writes such a goal as `cong o x o y`. The six obligations rerun through the closure and the checker (job below). I report both readings: 3 of 6 as registered, and the count after the fix. The decision uses the count after the fix only if every failure is shown to be this fault, which the rerun tests; if any of the six still fails, E2 stands as failed.
- **Other readings:** 106 of 115 obligations proved, all 106 pass the checker; 3 timeouts; 6 IndexError. One proved obligation of sample 3 (`cyclic s a e p`) failed on 1 of 3 fresh figures, so it holds for a configuration only. It isn't one the claim needs.

### SIDE-GT-REDUCE: E2 after the fix (written 2026-11-07 10:0x UTC; job 1347198)

All six rerun obligations are proved in one step and pass the checker, so every failure was the goal form, as the rule above required. **REDUCE-E2 reads 6 of 6 after the fix (3 of 6 as registered). By the decision, reduction becomes the pipeline's default, and the fresh test follows.** Fresh figures were 0 of 0 on two of those rows, which changes nothing here: each is one step from a hypothesis.

Six statements is a small sample, and all of these obligations are trivial duplicates, so the reading says only that harmless redundancy costs no proofs. It says nothing about statements where the redundancy is the claim; that is the fresh test.

## SIDE-GT-REDUCE-F: reduction on statements not yet read (written 2026-11-07 10:0x UTC, before any MechGeo translation exists)

**Why.** REDUCE repaired USAMO 2006 P6, one problem I had already read. The hard gap is faithfulness without a human, and one repaired example on read statements doesn't show that the repair happens when nobody knows the answer.

**Set.** The guarded statements of SIDE-GT-MG (arms MG-NL and MG-LEAN), which job 1345808 hasn't started. 12 of the 44 problems are in our dev or eval sets, and their rows are reported apart; the counts below use the other 32.

**Order.** (1) Translations. (2) I read each statement against the audited Lean statement and write its verdict, and for each `changed` or `wrong` statement whether it assumes part of the claim. (3) Only then `reduce`, the closure on the obligations, and the checker. (4) For each statement every closed basis gives a theorem, H without h proves h and g. All are output, because the pipeline has no way to prefer one. Then I read those theorems and write verdicts.

**Automatic rule.** A statement is repaired if it was not faithful and one of its closed theorems is. The system cannot say which theorem is the faithful one, so I report how many theorems each statement yields.

**Predictions.**
- **RF-P1 (reported):** statements with a basis: 20% of guarded statements (10–35%). On the 97 it was 18%.
- **RF-P2 (decision):** at least one problem outside dev and eval gets a repaired statement, in either arm. I put this at 45%: P6 is the only case among 65 held-out problems, but IMO statements with concurrency or "assume the conclusion" forms are common, and MechGeo's 14 unfaithful statements show how much room there is.
- **RF-P3 (guard):** a closed theorem is never read as less faithful than the statement it came from. Dropping a hypothesis can only strengthen it. Prediction: none.
- **RF-P4 (reported):** of faithful statements with a basis and a certified original proof, at least 70% reduce fully.

**Decision.** P2 holds: reduction is reported as a reference-free repair, with its rate over statements assuming part of the claim. P2 fails: it stays as the default, since it costs nothing, and the claim is limited to P6 as one exploratory case. P3 fails: a bug, stop and find it.

### SIDE-GT-DECL held out: end-to-end reading (2026-11-07 02:3x UTC; closure job 1343465, certificates jobs before and 1344245; verdicts fixed before any proof)

Counted: judged faithful, proved, passes `geo_check.py`, and holds on all fresh figures. Run with restarts at K = −300, the default by SIDE-GT-LUBY's decision, not the K = 256 registered, because restarts replaced it before this ran.

| Problems of 65 | Declarative | Construction | Union |
|---|---|---|---|
| Whole claim | **16** | 12 | 18 |
| One direction or part | 7 | 5 | 7 |
| Total | **23** | 17 | 25 |

- **DECL-P3 holds:** +6 against an expected +6 (range +2 to +12). New with a whole claim, none with a faithful constructive translation: ISL 2004 G2, ISL 2006 G2, IMO 2007 P2, ISL 2008 G16, USAMO 2009 P1, ISL 2013 G18. New as a part: Romanian 2006 grade 7 P3, USAMO 2011 P5. Lost: USAMO 2001 P2 (no faithful declarative translation), USAMO 2012 P5 (unproved).
- **Two weak fresh tests, reported:** ISL 2008 G16 has no fresh figure (0 of 0), so its fresh test is empty, and ISL 2023 G21 has one. Without ISL 2008 G16: 15 whole, 22 in all, and P3 still holds.
- **Checker:** 83 of 84 pass. The rejection is USAMO 2006 P6 sample 0, whose goal is the empty `cong p p p p`, correctly. Unfaithful statements were also proved and certified (5 of 6 proved rows), so **a certificate says nothing about faithfulness**.
- **Unproved whole problems with a faithful statement:** ISL 2001 G1, USAMO 2005 P3, ISL 2012 G22.
- **Decision (P1 and P3 hold):** the declarative form replaces the construction language in the pipeline. The registered follow-up, agreement rebuilt on it, has already run and fails (it passes 5 of 7 unfaithful statements and all 25 half ones). **So these counts rest on my reading, and the no-human count of 13 applies only to the construction language.** Faithfulness without a human is now the track's open gap: SIDE-GT-REDUCE attacks hypotheses the others imply; half translations are unattacked.

### SIDE-GT-H409 results (2026-11-07 02:3x UTC; 409 rows; jobs 1341669–70, certificates 1344459)

| Difficulty | Counted (ours) | Predicted | HAGeo at K = 8,192 | Of |
|---|---|---|---|---|
| [1, 3) | **140** | 140 | 149 | 161 |
| [3, 4) | **84** | 70 | 93 | 112 |
| [4, 5) | **28** | 20 | 36 | 71 |
| [5, 6) | **7** | 4 | 7 | 43 |
| [6, 7] | **2** | 0 | 2 | 22 |
| Total | **261** | 234 | 287 (263 at K = 2,048; random points 218 at K = 8,192; AG1 177) | 409 |

- **H409-P1 holds:** 261 in 190–280, above the expected 234. Engine proofs before the checker: 267; on 8 of 8 fresh figures: 263.
- **H409-P2 fails on the first pass, and the failures are ours:** 259 of 266 passed (97.4%, bar 99%). Seven rejections, two faults, both now fixed in `side/geo_closure.py`:
  - **Four: an unsound rule step.** Equal chords was accepted when the angle variables agreed up to a constant of 1/2 and the lengths agreed on the figure only by the other sign. This is the fault behind the false IMO 2011 P6 proof. The engine now requires the constant 0 on the figure, for the sign it uses. On re-export, two of the four prove on the same points without it (2020 RMM P1, 2023 EuropeanMCupS P2), and two no longer fall on those points (2011 APMO P3, 2013 USA TST P2).
  - **Three: certificate export, not the proofs.** The lattice's integer coefficients can exceed the 2^30 that rational reconstruction modulo 2^61 − 1 recovers, and the certificate carried garbage. It now writes the exact integers, and all three pass.
  - After the fixes, 264 of 264 certificates pass. The checker earned its place: it found a soundness fault a run of 266 proofs would otherwise carry.
- **H409-P3 holds:** median 1.81 s on proved rows (90th percentile 285 s). Mean over all rows 663 s against a limit of 1,800 s on one core.
- **Not counted, as registered:** six rows failed to build (four for `eq_trapezoid`, which our language lacks, difficulty 1.0, 1.6, 2.1, 3.3; two with an IndexError). **Reported apart, on the fixed engine (job 1344462): 2011 APMO P3 and 2013 USA TST P2 prove again, in 45 s and 10 s, on 8 of 8 fresh figures, and pass the checker: 263 with them, the registered threshold exactly.** The registered count stays 261 and I read the decision from it, because a threshold reached by rerunning rows I had seen is not a clean pass. The two errors repeat (2019 KoMaL A736, 2020 POGCHAMP P2).
- **Decision (218–262):** the search does something, and less than HAGeo at its largest budget. Next, as registered: the same engine with uniformly random points, so that the greedy's value is measured on the same engine and CPU.
- **A reviewer's reading.** Against HAGeo at K = 2,048 we are 2 short, with every proof certified by an independent exact checker and tested on 8 fresh figures, at a CPU budget orders of magnitude lower (HAGeo: up to 2,048 attempts of 60 s, on 64 cores). The bands [5, 7] match its largest budget. We lose 9 each at [1, 3) and [3, 4), which is where its construction rules or our language still matter. HAGeo's code is not public, so this is citation, not a rerun. Our proofs read a configuration from the figure, as AlphaGeometry's and HAGeo's do.

### SIDE-GT-H409-RAND: what the greedy adds (registered 2026-11-07 02:3x UTC, before any row)

**Why.** The registered decision for 261 of 409. HAGeo's random baseline reaches 218 in HAGeo's engine; ours reaches 261 with a greedy on the relations a point adds. Whether that gap comes from the greedy or from the engine is not known until both run on one engine.

**Design.** `GT_RANDOM=1`: at each restart, up to 6 points in turn, each uniform over the same one-step constructions (type first, then arguments, the sampler SIDE-GT-SAT uses), no gain and no second figure, the closure run after each point. All other settings, including 1,800 s on one core, the fixed engine, and the counting rule (checker and 8 of 8 fresh figures), as SIDE-GT-H409. The 409 rows are the same. The greedy's side of the comparison: the same fixed engine, its 261 plus the two rows reported apart, 263.

**Predictions.**
- **RAND-P1 (decision):** greedy minus random, paired over the 409, lower bound above 0. Expected random 225, range 190–255.
- **RAND-P2 (reported):** rows the random arm proves and the greedy doesn't: at most 15. Below that, the greedy dominates; above it, they are complementary and restarts between them would pay.

**Decision.** P1 holds: the greedy is credited with its gain, and the method stands. P1 fails: the count comes from the engine, the greedy is dropped for random points, which are simpler, and the report credits the closure.

### SIDE-GT-H409-RAND results (2026-11-07 18:0x UTC; all 409 rows, same engine, same 1,800 s, same counting rule)

- **Random points: 226 of 409** counted (228 proved, 2 lose on fresh figures, all 228 certificates pass; 174 timeouts against 136). Greedy: 263 on the same rule, the registered 261 plus the two rows fixed afterwards.
- **RAND-P1 holds:** greedy minus random is +37, 95% interval [+23, +51], paired over the 409 (45 rows greedy only, 8 random only). Random landed on the expected 225, inside 190–255. Dropping the two fixed rows from the greedy leaves the lower bound above 0.
- **RAND-P2 holds:** 8 rows random proves and the greedy doesn't, within the limit of 15. The greedy dominates; restarts between them would add at most 8.
- **Decision:** the greedy is credited with its gain and stands. The interim 196 against 176 at 274 rows understated the gap only slightly; what changed is that the hard rows came last.
- **A reviewer's reading.** About 86% of the count (226 of 263) needs no choice of points beyond random, so most of it comes from the closure. Our random arm at 226 sits near HAGeo's own random baseline of 218 in its engine, so the engines are close and the greedy is what closes the gap to HAGeo at K = 2,048. One seed of random choices.


## SIDE-GT-NDG: degenerate figures the checks never look at (written 2026-11-07 06:1x UTC, before any run on real statements)

**Why.** MechGeo (2608.02295, read in full, `docs/notes/RELATED_WORK.md`) found that 14 of 43 machine-formalized IMO statements are false as written, with Lean-checked counterexamples, mostly for a missing non-degeneracy or order condition. Worse for us: of 157 statements three experts called faithful, 22 were refuted. My verdicts are one reader's, and my pipeline cannot see this kind of error. `solve` in `side/geo_decl.py` keeps only the figures with the fewest chance coincidences, so a statement false only on a degenerate figure passes the guard, the closure and the fresh figures. The checker's own list of what it does not check starts with non-degeneracy. So the counted 23 problems may contain false statements, and I don't know how many. MechGeo names automating these checks as future work: its 14 repairs were by experts.

**Design.** `ndg_one`: for each collinear triple that the statement neither states nor excludes, add it as a hypothesis, solve from 40 starts, drop figures on which a cyclic hypothesis lies on a line, and test the goal. Distinct names stay distinct points, the language's convention, so MechGeo's IMO 2007 P2 counterexample (B = C) is out of scope by that convention, and I report this. It covers collinear degeneracies only; concyclic and parallel ones are not searched. Time limit 600 s per statement, with triples in random order, so a stopped statement reports its coverage. Run on all 97 held-out statements, whose verdicts are fixed. A two-statement smoke test on the login node: a parallelogram given by two parallel pairs is refuted on the collinear figure, as it should be, and the isosceles-median statement is not.

The classical route to these conditions is Wu's method, which outputs them as initials of a triangular set (Wu 1986; Chou 1988). A numerical search finds only failures it reaches, so "none found" is not a proof that none exist.

**Predictions.**
- **NDG-P1 (reported):** of the 23 counted problems, at least one counted statement has a counterexample I accept on reading in 20% (range 5–35%). MechGeo's rate is 33% on IMO problems; the convention and the guard over branches should remove some.
- **NDG-P2 (decision):** at least one counted problem has an accepted counterexample.
- **NDG-P3 (reported):** adding `ncoll` for each failing triple leaves the closure proof intact on every such statement, since the proof already ran on a generic figure.

**Decision.** P2 holds: the search becomes a stage before a row is counted, with the repair automatic, and every count of ours restated with the statements repaired and reproved. The stage is then tested for what MechGeo left to experts, on the IMO statements of SIDE-GT-MG. If the text doesn't imply the added condition, the row leaves the count. P2 fails: the convention plus the guard is enough on these statements, reported as such, with the coverage figures, and the search stays as a check on the MG statements only.

**Results (2026-11-07 11:5x UTC).** The search ran on all 97 statements. It finished 17 inside 600 s and tried 2,407 of 9,882 triples (24%), so "none found" is weak for the rest.
- **NDG-P1:** 1 of 23 counted problems (4%), below the predicted range (5–35%). The search reached a quarter of the triples, so this is a lower bound.
- **NDG-P2 (decision) holds.** ISL 2016 part (a) fails on 9 figures across its four translations. I read them: every one has a, b, p on a line (|sin| at most 9e-5) with a, c, I_A' and b, c, I_B' on lines too. That is the triangle on which l_A and l_B are both line AB, so "P on both lines" leaves P free. The text says "the intersection point of l_A and l_B", so it excludes this figure, and `ncoll a b p` is implied by the text. The row stays in the count, repaired.
- **NDG-P3 holds, 4 of 4.** With `ncoll a b p` added, all four statements are proved again (107–121 s), pass the checker and hold on every fresh figure.

By the rule: the stage stays before counting, the repair is automatic, and the count is restated. **It stays 23 (16 whole, 7 parts), with ISL 2016 repaired.** The stage is next tested on the MG statements.

## SIDE-GT-NDGP: the non-degeneracy conditions a proof needs, read from its certificate (written 2026-11-07 08:3x UTC, before the decisive run)

**Why.** SIDE-GT-NDG forces every collinear triple, about 115 per statement. It finished only 20–80% of them in 600 s on most statements, and a triple it never reached says nothing. The proof already knows what it needs. Each rule is true only away from a degenerate figure: two directed angles give a similar pair or a circle only on real triangles, and an auxiliary point has to exist and be apart from the points it is paired with. So a certified proof shows more than "the goal holds": H, distinct names and the conditions its rows use imply the goal, for the configuration the proof read. A figure where H holds and the goal fails has to break one of those conditions or that configuration. The search over the proof's own list is therefore complete in a sense the triple search is not, up to what a finite number of numerical starts can reach.

**Prior work.** Wu's method outputs such conditions as initials of a triangular set (Wu 1986; Chou 1988). The area method attaches a condition to each construction and elimination step (Chou, Gao, Zhang 1994; Janičić, Narboux, Quaresma 2012). Newclid (2411.11938) added `ncoll` to rules AlphaGeometry stated without it, and checks such conditions on the figure. Euclean (2607.19374) has the model write guards, which Lean then forces it to discharge. Larus (2401.11898) finds missing hypotheses by abduction in coherent logic, by constraint solving, not from a finished certificate. One standard search on each of two queries found no work that reads conditions from a deductive-database certificate; that is a thin search, and the idea is the area method's bookkeeping moved to our rules. I claim a tool and a measurement here, not a new idea.

**Design.** `conditions(c)` in `geo_check.py` walks the rows the goal depends on and emits, by the rule's statement: `ncoll` for both triangles of `similar`, the angle of `inscribed`, and `base_angles`, `parallelogram_mid`, `bisector`, `thales`, `trapezoid`; for each auxiliary point, `same` for each point it is paired with in a relation, `para` for an intersection of two lines, `tangent` for a second intersection. `pcond` in `geo_decl.py` then writes the statement on the figures where the condition fails, solves from 40 starts, and tests the goal, as SIDE-GT-NDG does. Run on the 84 certificates of the held-out declarative set, 1,800 s each.

**Seen before writing this.** The median list has 13 conditions (0 to 225). On one certificate of ISL 2016 (sample 3) the list contains `a b p`, the triple the old search failed on, and the new search reproduces that failure.

**Predictions.**
- **NDGP-P1 (test of the derivation):** every failing figure the triple search found, on a statement with a certified proof, breaks a condition on that proof's list, or a configuration the proof read. Prediction: all of them. An escape means a rule's statement in the list is incomplete or a rule is false.
- **NDGP-P2 (reported):** every condition is tested within the limit on at least 90% of the 84 certificates (range 75–100%). The triple search finished 17% of its first 48 statements.
- **NDGP-P3 (reported):** on the proofs of the 23 counted problems, at least one condition that is not stated has a figure on 60% of problems (30–90%).
- **NDGP-P4 (reported):** failures found among those reach at least every counted problem the triple search flagged, and add at least one it did not reach.

**Decision.** P1 and P2 hold: the proof's list replaces the triple search as the stage before a row is counted, and each counted row states the conditions that are neither in the problem's text nor shown empty. P1 fails: fix the list and rerun; a second escape after the fix means the list is not trusted, and the triple search stays. Empty means no figure from 40 starts, which is evidence, not a proof that the condition follows.

**Results (2026-11-07 11:5x UTC).** All 84 certificates ran.
- **NDGP-P1 holds:** 9 of 9 failing figures break a listed condition (tolerance 1e-4, because figures are stored to 5 decimals), 0 escapes. This is a small test: all nine are one degenerate family on one problem.
- **NDGP-P2 fails as registered:** 77 of 84 (92%) finished inside the limit, but 7 of those hold a condition I can't write in the language (two circles tangent at their meeting point), so every condition was tested on 70 of 84 (83%), inside the predicted range but under the 90% the rule asks for. Of the 62 conditions marked untested, 26 are impossible by distinct names, which is a result, and 28 duplicate a tangency tested under its own name unless the point comes from two circles.
- **NDGP-P3:** 7 of 23 counted problems (30%) have an unstated condition with a figure, at the bottom of the range (predicted 60%). On six of the seven the goal still holds on those figures. The proof doesn't cover them, but they are not counterexamples.
- **NDGP-P4:** half. The failures reach ISL 2016 and add no new problem. They add two conditions on that problem (`c i p`, `_x0 o p`), both on the same family.

**Decision.** The rule needs P1 and P2, so the list does not replace the triple search. Both stay before counting until circle tangency can be written. SIDE-GT-LEAN below replaces this numerical reading of the rules with proofs of them.

## SIDE-GT-MG: the pipeline on MechGeo's audited IMO statements (written 2026-11-07 06:1x UTC, before any run)

**Why.** Rule 9. MechGeoBench (github.com/MechMath/MechGeoBench) has 44 human-audited Lean statements of IMO geometry from 2000 to 2026, with proofs. It is the closest public comparison to our pipeline, and it has what the proof track lacks: a faithfulness reference that isn't my reading. Only 12 of the 44 are in our dev or held-out sets.

**The comparison, stated first.** MechGeo without a human: 29 of 43 proved, with Claude Opus 4.8 translating and GPT-5.6-Sol proving, two hours per problem (one took 2 h 6 min), plus IMO 2026 P2. With experts repairing 14 statements, all 44. Its proofs are checked by Lean's kernel on the full statement, order conditions included. Ours are checked by a small exact checker that does not cover non-degeneracy or the rules that read a configuration from the figure. Our translator is an open 27B model and our prover is the closure, with no model. So equal counts would not mean equal claims. Coverage favours MechGeo; cost is what we can claim, if anything.

**Design.** Problem texts: official IMO papers (imo-official.org) or the text already in `imo_geometry.parquet`, in `nlp_data/geo/mg_problems.jsonl`. Two arms, both frozen as SIDE-GT-DECL (Qwen3.6-27B-AWQ, thinking, four samples, two repair rounds, 240 starts, closure at 1,800 s, checker, 8 of 8 fresh figures):
- **MG-NL:** the problem text alone. The whole pipeline.
- **MG-LEAN:** the problem text and the audited Lean statement. This separates the translator from the prover, because the model has the audited hypotheses in front of it.

I read each guarded statement against the audited Lean statement and write the verdicts (faithful, half, changed, wrong) before any closure run. A problem counts whole if a faithful statement of all its claims is proved, certified and holds on 8 of 8 fresh figures, as before.

**Predictions.**
- **MG-P1 (reported):** problems with a guarded statement: NL 20 of 44 (12–26), LEAN 28 (20–36). Held out, it was 29 of 65.
- **MG-P2 (reported):** whole problems: NL 9 (5–14), LEAN 15 (9–22). MechGeo's no-human count is 29 of 43.
- **MG-P3 (decision):** LEAN minus NL, paired over the 44 problems, lower bound above 0.

**Decision.** P3 holds: at IMO level the translator is the limit, and the next method goes there, with the audited statements as the reference for a faithfulness test that needs no human reading. P3 fails: the prover and the language are the limit, and the next method goes to what the LEAN arm could not prove or express. Either way the comparison is reported as a row with both claims stated. If NL reaches 29 or more, I'll claim coverage comparable to MechGeo's for an open 27B model and no prover model; otherwise only cost, in tokens and seconds per problem, and only against numbers MechGeo reports, which do not include tokens.

## SIDE-GT-LEAN: every proof as a Lean theorem, with what it assumes stated (written 2026-11-07 11:5x UTC, before any certificate is exported)

**Why.** Our "certified" means a 490-line Python checker says so. The checker trusts each rule's statement, and does not cover non-degeneracy or the rules that read a configuration from the figure. MechGeo's proofs pass Lean's kernel, so SIDE-GT-MG had to say that equal counts would not mean equal claims. Euclean's Appendix E and the Lean Zulip thread it cites make the same objection to AlphaGeometry's whole family: orientation read from a numerical figure, side conditions checked outside any logic. NDGP tested the side conditions numerically. This replaces that with proofs.

**Prior work.** Huỳnh Trần Khanh said on the Lean Zulip (July to August 2025) that they were translating Newclid's proofs into Lean with complex numbers, and that orientation was the hard part. I found no release or result in two searches. Euclean (2607.19374) and MechGeo (2608.02295) prove in Lean directly and use no deductive-database engine. GeoCoq and Narboux's area method in Coq are decades-old formalizations of other methods. So the idea is not new, and I claim only what runs: how many of our proofs reach the kernel, and what they then assume.

**Design.** `side/lean/`: points are real coordinate pairs. A direction is a real number with equality modulo π, through the isomorphism with the unit circle; a log length and a squared length are real numbers. `GeoBase.lean` proves that each polynomial fact and the engine's linear relation say the same thing. `GeoRules`, `GeoSim` and `GeoCircle` prove each rule of `geo_check.py`, with non-collinearity as a hypothesis where the rule needs it, and each reading as a hypothesis (`Read`, `Read2`, `ReadT`, `ReadZ`). A circle group becomes a centre and a squared radius, and its variable t a real function of the point. `side/geo_lean.py` writes one theorem per certificate, over the rows the goal depends on: for all points, the statement's facts it uses, distinct names it uses, the conditions and readings imply the goal. Auxiliary points are quantified with their construction facts. Lean 4.15 and Mathlib, `#print axioms` on each theorem, and no `sorry`.

**Seen before writing this.** The rule library is written and compiles, with no `sorry`. So every rule is proved, which is the first reading: `thales` needs no non-collinearity, so the list has one condition too many, and `similar` from two angles needs one real triangle, not two. Verdict files show 14 of 83 and 48 of 264 certificates with no reading over all rows, and 2 of 84 with a constant read from the figure, which cannot be exported. No certificate has been exported.

**Predictions.** Set: the 84 held-out declarative certificates and the 266 certificates of HAGeo-409, 350 in all.
- **LEAN-P1 (decision):** Lean accepts at least 90% of the 350 (predicted 92%, range 75–98%). What falls out should be the two figure constants, the two `aconst` statements, and time.
- **LEAN-P2 (test of the checker):** at least one certificate the checker passes cannot be exported because a step is not justified. Candidates from reading the checker: a union of circles sharing fewer than three points, and an equal-chords step with coefficients other than ±1. Predicted 60%.
- **LEAN-P3 (reported):** certificates with no reading over the rows the goal uses: 25% (18–40%).
- **LEAN-P4 (reported):** median compile time per theorem 30 s (5–300 s).

**Decision.** P1 holds: a kernel-checked theorem replaces the checker's verdict as the definition of a counted row, and each row reports its conditions and readings as hypotheses. The MechGeo comparison is then restated: same kernel, weaker statements where readings or conditions remain. The next gap is discharging readings. P1 fails: report what stops it, fix what is a bug, keep the checker. Any step P2 finds is a checker fault: fix, rerun the checker, restate affected counts.

**Results (2026-11-07 13:3x UTC).** 340 of 350 certificates pass Lean's kernel with only `propext`, `Classical.choice` and `Quot.sound`, and no `sorry`: 79 of 84 held out, 261 of 266 on HAGeo-409.
- **LEAN-P1 (decision) holds:** 97.1% (predicted 92%, range 75–98%). The ten that did not pass: 2 use a constant read from the figure, 8 ran out the 1,200 s compile limit. Those eight are rerun with 4 hours. No step was rejected.
- **LEAN-P2 did not read as predicted:** no certificate the checker passes failed for an unjustified step, among the 340. The two suspected circle unions were an exporter fault of mine, and the checker's loose test in `parallelogram_mid` never mattered. Every rule was also proved, so on these sets the checker's trust was warranted. One condition was unneeded (`thales`).
- **LEAN-P3:** 63 of 340 (18.5%) have no reading, at the bottom of the range (predicted 25%).
- **LEAN-P4:** median 22 s per theorem (predicted 30 s, 5–300 s).

**By problem.** Held out: 22 of the 23 counted problems have a kernel-checked statement (16 whole, 6 parts). The other, a part (Romanian NMO grade 7 P3), rests on a figure constant in both counted statements. Only 3 of the 23 have a reading-free statement. HAGeo-409: of the 263 rows with 8 of 8 fresh figures (261 counted plus the two reported apart), 259 are kernel-checked, 4 are in the rerun, and 48 have no reading.

**Decision.** A counted row now means a kernel-checked theorem. **The held-out count becomes 22 (16 whole, 6 parts).** Each theorem assumes the distinct names, conditions and readings written in its statement, so this is what the count claims. Against MechGeo the kernel is now the same and the statements are weaker wherever a hypothesis remains. The rule library and the exporter replace the checker as the definition; the checker stays as a fast first pass.

### SIDE-GT-LEAN-NR: proofs that read nothing from the figure (registered 2026-11-07 12:2x UTC, before any run)

**Why.** A kernel-checked theorem that assumes `Read` is weaker than the statement. The readings are the objection the Zulip thread and Euclean raise, and the hard part the unfinished translation named. The first compile shows they are common: on the held-out set 79 of 84 certificates compile, and only 15 of those 79 have no reading. Each reading says two triangles have the same orientation, or two points the same side, and nothing proves it from the hypotheses.

**Design.** `GT_NOREAD=1` turns off the four rules that read a configuration: similar by three ratios, similar by two sides and an angle, Thales' converse, and the trapezoid from a ratio. Two directed angles still give a similar pair. Everything else as frozen for each set, including restarts and auxiliary points, so the search can look for a different proof. Rows: the 84 proved held-out statements and the 267 proved rows of HAGeo-409, 1,800 s each. Then checker, export and compile.

**Seen before writing this.** The held-out compile (15 reading-free of 79). No run of the flag.

**Predictions.**
- **NR-P1 (decision):** on HAGeo-409, rows with a kernel-checked reading-free proof: 170 of 264 (120–220). HAGeo's 263 at K = 2,048 stands for a count with no such guarantee, so anything here is a stronger claim on fewer rows.
- **NR-P2 (reported):** of the 23 counted held-out problems, those with a reading-free proof of a counted statement: 12 (7–18).
- **NR-P3 (reported):** median proof length grows by at least 20% among rows proved both ways: predicted yes, 70%.

**Decision.** If NR-P1 reaches at least 170, the reported count splits in two, readings assumed and readings absent, and the no-reading engine becomes the default for the MG comparison, since those theorems are what compares with MechGeo. Below 170 the readings stay as stated hypotheses, and the next method is discharging them from the statement's order conditions, as a sign proved in Lean or by a case split on the two orientations.


**Withdrawn in part (2026-11-07 16:0x UTC).** The user moved proofs to testing and analysis for the teammate, so the HAGeo half stopped before it ran and NR-P1 is unread. On the 84 held-out statements the engine without those rules proves 69 (15 time out at 1,800 s), covering 20 of 25 problem ids, so most proofs survive. These are closure proofs; they weren't certified or compiled, so NR-P2 is unread as well. With lifting available the question matters less: it keeps every proof.
### SIDE-GT-LEAN-RD: can a reading fail on the statement? (registered 2026-11-07 13:0x UTC, before the run)

**Why.** A theorem with `Read` as a hypothesis says nothing on the figures where the reading fails. Removing the hypothesis is a question about the statement, so ask it directly. If no figure of the statement breaks a reading, the reading is probably implied by its order conditions. If some figure breaks it and the goal holds there, the proof is incomplete, though the statement may be true. If the goal fails there, the statement is false as written, and only the reading the engine took from its figure saved it. That is the error MechGeo refuted statements for, and no stage of ours can see it: the guard and the fresh figures share the configuration of the first figure.

**Design.** `rread` in `geo_decl.py`: each reading of each certificate that exports, negated as an order condition (`flip`, `flip2`, `flipt`, `flipz`), with the auxiliary points it mentions and their constructions; 40 starts as in `pcond`, then the goal tested. Set: the 84 held-out certificates, 1,800 s each. On one certificate in a smoke test (ISL 2012, two readings) no figure exists.

**Predictions.**
- **RD-P1 (reported):** 35% of readings have a figure where they fail (15–60%). Statements with order conditions pin many of them down.
- **RD-P2 (decision):** at least one counted statement has a broken reading with the goal false on the figure, accepted on reading. Predicted 40%.
- **RD-P3 (reported):** counted problems with at least one counted statement whose readings all have no failing figure: 12 of 23 (7–18).

**Decision.** RD-P2 holds: the stage goes before counting, as NDG does. If the text implies the missing order condition, it is added and the row is reproved; if not, the row leaves the count, and every count is restated. RD-P2 fails: readings are hypotheses that no figure found broke, and each row reports how many have figures.

**Result (2026-11-07 14:4x UTC, on the 84 statements as first written; the read is not final until the repaired rows are in).** 82 certificates read, 2 stop on a figure constant; 67 have readings, 15 have none; 273 readings, 271 with no figure at all. **RD-P1 fails, far below range: 2 of 273 (0.7%) against 35% (15–60%).** Both failing figures are on ISL 2016 (rows 2 and 3), the goal is false on both, and in both a, b, p are collinear to 1e-6: that is the degenerate family SIDE-GT-NDG already found, not a new failure. The counted ISL rows are the repaired ones with `ncoll a b p`, so RD-P2 waits for `rread` on those four. A number this far from the prediction is treated as a bug until the control below says otherwise.

**Repaired rows (2026-11-07 14:5x UTC).** `rread` on the four ISL 2016 statements with `ncoll a b p`: 23 readings, no figure. **RD-P2 fails on the counted statements:** the only broken readings were the degenerate family the NDG stage had already removed. Under the rule, no row leaves the count, and readings stay as hypotheses that no figure broke, subject to the control below.

### SIDE-GT-LEAN-RC: is "no figure" a result or a blind search? (registered 2026-11-07 14:4x UTC, before the run)

**Why.** 271 of 273 readings having no flipped figure could mean the statements fix their readings, or that the search can't reach a flipped figure. If it is real, it also says what a proof of the reading has to use: order conditions of the statement, or nothing.

**Design.** `rctl` in `geo_decl.py`, same 84 certificates, 40 starts, 1,800 s each. For each reading: (a) the statement with the auxiliary points and no negation: starts solved, and the reading's sign on those figures; (b) the negated reading with the statement's order conditions removed (`between` kept as `coll`, `ncoll` kept): figures, and how many break the goal. Three planted statements already behave: side-side-side pairs with either orientation broken give 39 of 40 figures, the midline triangle gives none.

**Predictions.**
- **RC-P1 (decision):** at least 90% of readings have 4 or more of 40 starts solved in (a), and no reading is flipped on a figure of (a) outside ISL 2016.
- **RC-P2 (decision):** on rows with order conditions, 40% of readings have a flipped figure once those conditions go (15–70%).
- **RC-P3 (reported, method):** of readings with such figures, the goal holds on all of them for 60% (30–85%). There a proof could split on the reading and needs no order fact; elsewhere it must use the order conditions.

**Decision.** RC-P1 holds and RC-P2 is at least 10%: the search reaches flipped figures when they exist, and the RD result stands as evidence. RC-P1 fails: readings with few solved starts count as untested, and RD-P1 is restated on the rest. RC-P2 below 10%: order conditions aren't what fixes the readings, the control has shown no power on real statements, and the RD result is reported as unconfirmed.

**Result (2026-11-07 17:0x UTC).** 84 certificates, 2 stopped on a figure constant, 3 ran out of time: 246 of 273 readings tried. **RC-P1 fails: 48 of 246 (20%) have 4 or more of 40 starts solved, median 0, and 127 have none.** The search rarely finds even an unflipped figure once the auxiliary points are written out, so "no figure" means little for most readings. **RC-P2 fails below the bar: 16 of 185 (8.6%).** **RC-P3 fails: the goal holds on all figures for 0 of 16.** By the rule, readings with few solved starts count as untested and the RD result is reported as unconfirmed. Restated: of 48 readings the search could test, the only flips are three on ISL 2016 in the degenerate family. SIDE-GT-LEAN-RD's 271 of 273 should not be cited.

**A hidden reading, found by this control.** 11 of the 16 flipped readings are not hypotheses of the lifted theorems, though the goal fails on their figures. A kernel theorem can't fail on a figure that meets its hypotheses, so I read one (ISL 2013). The statement says `uangle p b a a c b`, unsigned; the theorem assumes `EqA`, directed, with the sign taken from the figure (`geo_decl.py`, `_turn`). The flipped figure meets the unsigned form and not the directed one. So a statement with `uangle` carries a figure-derived fact in a hypothesis that isn't called a reading: 26 of 82 held-out theorems, and 10 of the 46 with no `Read`.

### SIDE-GT-LEAN-LIFT: prove the reading instead of assuming it (registered 2026-11-07 14:5x UTC, before the full compile)

**Why.** Only 3 of 22 counted problems have theorems without readings, so most of what the kernel checked assumes a fact about the figure. SIDE-GT-LEAN-NR removes the rules that need readings and loses proofs. This keeps the proofs and removes the hypotheses.

**Method.** A row of the closure holds modulo π, so it forgets which way a line points. Take the direction `Th a b` of the vector ab, modulo 2π. Then (1) the double of any row modulo π holds modulo 2π; (2) some rules know more and give a relation modulo 2π outright: similar triangles (equal angles at each vertex), the isosceles triangle, a midpoint, the midline, the parallelogram, a radius, and reversal `Th b a = Th a b + π`. A reading says exactly that two angles equal modulo π are equal modulo 2π. So a reading is a theorem whenever its relation lies in the integer lattice generated by (1) and (2), which is a linear question: reduce by integer row operations, in proof order, using only rows already proved, and treat an unproved reading as a hypothesis that later ones can use. `side/lean/GeoLift.lean` proves each rule of (2) and `read_lift`/`read2_lift`, with no `sorry`. `geo_lean.py --lift` writes the combination into the theorem; Lean checks it with `ring`.

**Nearest prior work.** Todd, *A Method for the Automated Discovery of Angle Theorems* (arXiv 2201.00543, read in full): directions of directed lines as a sparse linear system modulo 2π, a statement proved when it lies in the row space, with a numerical sketch arbitrating the multiples of 2π. It has only relations modulo 2π; there is no mixed modulus and the sketch stays in the loop. Chou, Gao and Zhang's full angles work modulo π and are diagram independent, but can't express orientation. AlphaGeometry and Newclid check orientation on a numerical diagram; the Lean Zulip thread on their foundations names this as unrigorous. Searches for a parity or mixed-modulus treatment found nothing, which proves nothing about novelty; the search terms are in `RELATED_WORK.md`.

**Design.** Certificates: the 82 held-out that export, 4 repaired ISL 2016, the 266 HAGeo-409. Compile with the 1,200 s limit. Count: readings proved, readings left, theorems with no reading, and problems with a counted theorem with no reading. Export so far, before any full compile: held out 220 proved, 53 left, 46 of 82 theorems free, and no relation came out with the wrong constant. Two theorems (ISL 2012) compile with no `Read` in the statement.

**Predictions.**
- **LIFT-P1 (decision):** at least 95% of the certificates that compiled without lifting also compile with it.
- **LIFT-P2 (decision):** HAGeo-409 rows with a kernel-checked theorem and no reading: 140 of 263 (100–190), from 48.
- **LIFT-P3 (reported):** held-out problems with such a theorem: 10 of 22 (6–15), from 3.
- **LIFT-P4 (bug check):** no relation has the wrong constant on any certificate. One that does means a rule of the exporter is wrong, because the figure satisfies the reading.

**Decision.** LIFT-P1 holds and LIFT-P2 is at least 100: lifting becomes the default export, the count is split into theorems with and without readings, and the next gap is the readings left, by which relation blocks them. Below 100: the same split, and the blocked relations are read before anything else.

**Interim (2026-11-07 17:0x UTC).** Held out: 78 of 82 compile (3 timeouts at 1,200 s, 1 fails at Lean's recursion limit in a `simp`). Repaired ISL 2016: 4 of 4. HAGeo fix: 2 of 2. HAGeo: 83 of 86 so far. LIFT-P4 holds so far: no wrong constant. Three failures are `maximum recursion depth`, in long combinations, a limit of the written proof and not a rejected step.

**Results (2026-11-07 19:4x UTC; all sets compiled at 1,200 s).**
- **LIFT-P1 holds:** at the same 1,200 s limit, 333 of the 344 certificates that compiled without lifting compile with it, 96.8% (held out 78 of 79, repaired 4 of 4, HAGeo 251 of 261). Adding the 8 that needed the 4-hour limit unlifted, none of which lifted passes, it's 333 of 352, 94.6%, so the rule holds only like for like.
- **LIFT-P2 holds:** of the 263 counted HAGeo-409 rows, **126 have a kernel-checked theorem with no reading**, from 48 (predicted 140, range 100–190). All 263 are kernel-checked with or without lifting, so a lifted failure costs the reading, not the row.
- **LIFT-P3 holds:** on statements read as faithful, **11 held-out problems** have such a theorem, from 2 on the same count (predicted 10, range 6–15). Counting unsigned angles as readings, as they should be, it's 8. My registered denominator of 22 includes rows outside `gtdecl_eval_faithful.json`, which holds 20 problems, and "from 3" there is 2 here; 15 of the 20 keep a lifted theorem.
- **LIFT-P4 holds:** no relation has the wrong constant on any certificate (0 of 652 lifted relations on HAGeo).
- **Hidden readings.** None of HAGeo-409's statements has an unsigned angle, so the 126 stands as it is. Held out, 10 of the 46 theorems with no `Read` carry one.
- **Failures.** None is a rejected step. Five HAGeo certificates don't export: the integer combination grows past 4,300 digits, because the row reduction doesn't control coefficient size, a fault of the exporter. On compile, HAGeo has 7 at the recursion limit and 3 at the time limit, held out 1 and 3. Those rows keep their unlifted theorems.
- **Decision:** lifting becomes the default export, and counts are split into theorems with and without readings. The next gap is the readings left, by relation; the tally on HAGeo is running.
- **A reviewer's reading.** About half of HAGeo's counted theorems now assume nothing read from a figure beyond the statement's own conditions. AlphaGeometry-style engines don't give that; MechGeo's Lean proofs do, by another route, so this is no first. The other half keep a median of 1 to 2 readings, written as hypotheses. The lattice is close to Todd's; the difference is the mixed modulus and dropping the sketch, and I haven't searched further than Todd and Chou's full angles for this, so I claim no novelty.

### SIDE-GT-MG verdicts, written 2026-11-08 09:0x UTC before any closure run

Every guarded statement (86 NL, 93 LEAN) read against the audited Lean theorem; file `results/proof/gtmg_faithful.json` (not committed, raw output). Read with a helper agent and spot-checked by me.

| | NL | LEAN |
|---|---|---|
| problems with a guarded statement (MG-P1) | 29 | 29 |
| problems with a faithful statement | 23 | 24 |
| problems with a faithful or half statement | 25 | 27 |
| statements faithful / half / changed / wrong | 70 / 6 / 10 / 0 | 74 / 9 / 7 / 3 |

- **Half:** a goal is one fact, so an iff gives one direction (2003 P4, 2004 P5 in both arms).
- **Changed, most often a missing case selection:** points free to swap on a circle (2015 P4, NL), a point fixed only by a ratio that the other homothety centre also meets (2008 P6, NL), a convex pentagon cut to two quadrilaterals (2022 P4), a convex hexagon cut to four of its points (2005 P1, LEAN; NL wrote the order along each side and is faithful). Assumed goals: 2004 P1 nl:0 has `between b p c` as a hypothesis and `coll p b c` as the goal; 2002 P2 proves J on one bisector only, which holds without the claim.
- **Wrong:** 2020 P1 (LEAN) turned the angle ratios 1:2:3 into equalities; 2023 P2 lean:3's goal has the degenerate line `t t`, so it holds on every figure.
- **Checker fault found and fixed.** `geo_decl.parse` accepted a line or segment given by one repeated point, so `eqangle b a t t a c t a` and `cong p p p p` held on every figure and passed the guard. Rejected now, with a message the model can read. Among all recorded statements three guarded goals had this; all three were already read as wrong or are dev rows, so no counted row changes.
- **Judgement calls (in the file's notes):** a missing condition that symmetry (2004 P5, 2018 P6, 2015 P3, 2025 P2) or continuity (2010 P2, 2021 P3, 2013 P4, 2023 P2, 2000 P1) only selects is counted faithful; directed-angle goals (2018 P6, 2024 P4) match the unsigned claim only under the figure's orientation.

Closure and certificates on all 179 guarded statements: CPU jobs 1354571 (NL) and 1354572 (LEAN), frozen settings (K = −300, 1,800 s).

### SIDE-GT-MG results, 2026-11-08 11:5x UTC

Closure and certificates finished for both arms (jobs 1354571, 1354572). Counting rule as registered: a faithful statement, proved, certificate accepted by the checker, goal held on 8 of 8 fresh figures.

| | NL | LEAN |
|---|---|---|
| guarded statements proved (closure, 1,800 s) | 78 of 86 (8 time out) | 82 of 93 (9 time out, 2 crash) |
| certificates accepted | 73 of 78 | 78 of 82 |
| problems with a faithful statement | 23 | 24 |
| ... also proved and certified | 20 | 21 |
| ... also 8 of 8 fresh figures: **whole problems (MG-P2)** | **13** (predicted 9, 5–14) | **13** (predicted 15, 9–22) |
| whole or part (faithful or half) | 15 | 15 |
| translator output tokens per problem, mean (median) | 79k (71k) | 61k (53k) |
| closure CPU seconds per problem, mean (median) | 495 (113) | 630 (166) |

- **MG-P2:** both inside their ranges. NL is above my point prediction, LEAN below it.
- **MG-P3 fails:** LEAN − NL = 0 of 44, 95% interval [−0.09, +0.09] per problem. NL alone has 2000 P1 and 2013 P4; LEAN alone has 2002 P2 and 2024 P4.
- **Where problems are lost (both arms):** 15 have no guarded statement, 5 to 6 no faithful one, 3 lose at the prover, and **8 lose only at the fresh-figure rule**. Every faithful proved and certified statement held on every fresh figure that was built; the solver just built fewer than 8 (9 statements per arm got none). Without that rule the count is NL 20, LEAN 21. This is a sensitivity row, not the registered count.
- **Two LEAN rows have no closure result** (2000 P6 lean:1, 24 points; 2023 P2 lean:3): the child process exited with no output and no error text, so the runner recorded an IndexError. Both are read as half or wrong, so no count changes. Cause not yet known.
- **Decision (P3 fails):** at IMO level the audited hypotheses don't change what is proved, so the translator's reading is not the limit. The limit is what one statement can express (15 problems) and the figure solver (8). The next method goes there. NL reaches 13, below 29, so against MechGeo only cost is claimed: one open 27B model on one GPU, 79k output tokens and about 8 CPU minutes of closure per problem, against MechGeo's two hours per problem with two frontier models. MechGeo reports no token counts, and its proofs are kernel-checked on the full statement while ours pass our checker, so the counts are not equal claims.

## SIDE-GT-H409-CPU: the same engine at a larger CPU budget on HAGeo-409 (task 2, checkpoint 0; written 2026-11-13 10:2x UTC, before any row)

**Why.** Task 2's target (`side/README.md`) is more than HAGeo's 287 of 409, each row certified, at no more CPU than HAGeo's setting. Our 263
used 1,800 s on one core per row, and 136 rows timed out; HAGeo's 287 used up to 8,192 attempts of up to 60 s each, on 64 cores. Before
any new idea is credited, the curve of rows counted against CPU for the unchanged engine must be known: a lever is worth only what it adds
over that curve at the same CPU. This is the reference run for the teammate's checkpoint (0); the teammate's own runs go through the same kit.

**Design.** The 146 rows not counted by SIDE-GT-H409 (`nlp_data/geo/h409cpu/`, 37 shards), the frozen engine and settings of that run
(K = −300, GT_SOUND, GT_STRICT, GT_SQ, GT_SECOND, GT_LUBY), one core per row, **28,800 s per row (16 times the reference budget)**. The
search is deterministic (restart seeds are fixed), so one run gives the count at 2, 4, 8 and 16 times the budget from each row's time to
proof. Counting through the task-2 kit (`side/kit_h409.py score`): the certificate is bound to the frozen statement, passes
`geo_check.py`, and every step and the goal hold on 8 of 8 fresh figures. CPU jobs on the Slurm CPU partitions.

**Derivation of the prediction.** In the reference run, proofs per doubling of time were 9, 13, 8 and 8 over [128, 256), [256, 512),
[512, 1,024) and [1,024, 1,800) s, about 10 per doubling with no clear decline. Four more doublings at that rate give +40; the rows left are
the hardest, so I expect the rate to fall by about half: **+25** (range +10 to +45), 288 in all. At 1 times the budget it should give back
about 0 (the same search, cut at the same time).

**Predictions.**
- **CPU-P1 (decision):** rows counted at 28,800 s, added to the 263: 288, range 273–308.
- **CPU-P2 (reported):** counted at 2, 4 and 8 times the budget; rows counted by band.
- **CPU-P3:** the kit's soundness control (tampered certificates) counts 0, and the kit reproduces the reference 263.

**Decision.**
- More than 287 counted: the unchanged engine passes HAGeo with about 6% of HAGeo's maximal CPU per row (28,800 against 491,520 core-s).
  Compute is then not the teammate's contribution: every lever is scored at matched CPU against this curve, and the target moves to the
  rows still left and the CPU to reach 287.
- 287 or fewer: the remaining gap is the room for levers 1–3 (HAGeo's candidate rule, a faster closure, the algebraic fallback), each
  measured at matched CPU against this curve.

### SIDE-GT-H409-CPU, CPU-P3 (2026-11-13 14:4x UTC): holds
The task-2 kit reproduces the reference count exactly (263; the same 3 proved rows lost at the fresh-figure rule) and its control counts
0 of 737 tampered certificates. CPU-P1/P2 wait for the 37 shards (28,800 s per row).
- **Scope cut (2026-11-13 15:4x UTC, before any shard finished):** the 12 shards still waiting (25–36) were cancelled to stop a second
  8-hour wave on the CPU partitions; CPU-P1/P2 are read on the 109 rows of shards 0–24 (rows sorted by difficulty and dealt round-robin,
  so every band is in). The 37 rows left are for the teammate's run through the kit, at a smaller budget if the curve is flat.
