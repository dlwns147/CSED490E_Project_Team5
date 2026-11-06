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
