# Pre-registration TC-RL: train the quick tool calls for correctness, check them with a peer

Written 2026-10-30 06:5x UTC, before any training round or any BFCL row of a trained model. Results go below.

**Why it could change the claim.** On text-to-SQL (PREREG_CV.md addenda 4–5), plain RL on the non-thinking query plus another
model's agreement as the gate beat the no-label default by +2.0 utility, and still +1.8 over the default run with the same trained
weights; training the model to gate itself collapsed to always deferring. That is one task. Tool calls are the other task where the
peer check already pays (HO-PA: Qwen3-8B's N → Qwen3.5-9B agrees → N, else SB→T→T, +0.9 [+0.4, +1.3] over SB→T→T on BFCL). If plain RL
on open tool-calling data again moves right answers onto the items the default fails, the finding is a recipe — train the cheap path for
correctness, take the gate from outside the model — not a SQL fact.

**Prior work.** RL with rule-based rewards on tool calls is known to raise BFCL accuracy: ToolRL (2504.13958, GRPO, ~4k examples from
ToolACE / Hammer / xLAM), Nemotron-Research-Tool-N1 (2505.00024, binary format + correctness reward, GRPO). ToolACE (Team-ACE/ToolACE,
Apache-2.0) is the data. Agreement cascades are training-free (MoT 2310.03094, ABC 2407.02348, 2509.21837). New: the trained quick mode
inside a peer-check cascade, with the cascade's gain predicted from where training moves right answers (SQL-AND's decomposition).

**Run.** Data: ToolACE's single-turn dialogues in BFCL's prompt format (`poc/prep_tctrain.py`: 9,549 kept, 1,289 with no call;
function names that are not Python-style rewritten with "_"; requests identical to a BFCL request dropped: none). Reward
(`poc/tc_reward.py`, pure Python): the decoded calls equal the gold calls as a multiset (arguments equal to a documented default may be
omitted; numbers by value), or no call where the gold makes none; its call / no-call decoding agrees with BFCL's decoder on 99.8% of
Qwen3-8B's stored quick answers. Training (`poc/tc_train.py`): CV-1's C1 loop unchanged (LoRA r 16, 6,000 requests, 64 per round, 8
samples, one step per round, lr 2e-5, no KL, 512-token cap). Test: BFCL (TC-1's 3,482 items), quick calls only (`run_tc.py`,
`TC_ARMS=quick`, seeds 1–3, TC-1's per-item seeds), tag q8btcc1, graded by `grade_tc.py` (BFCL's AST checker; free check = schema
validation). Policies (`poc/analyze_tcrl.py`): SB→T→T (Qwen3-8B's no-label default, HO-PA's rows); N → peer (Qwen3.5-9B's quick
calls, TC-1's q35 rows) makes the same calls → N, else SB→T→T, with the base N and with C1tc's N. Smoke first (64 requests, no
evaluation; not part of the results).

## Predictions (3,482 items × 3 seeds, paired 95% intervals over items, utility = accuracy − 0.5 × ktokens)

- **TCRL-P1 (training transfers):** C1tc's quick calls right − the base's: lower bound > 0.
- **TCRL-P2:** utility C1tc's peer cascade − SB→T→T: lower bound > 0.
- **TCRL-P3 (training adds to the cascade):** − the base calls' peer cascade: lower bound > 0.
- **TCRL-P3 theory:** the decomposition's prediction (C1tc's strata, the base calls' agreement rates: RW 45.2%, WR 11.0%) inside P3's
  interval.
- Reported: quick-call accuracy by non-live / live; C1tc's agreement rates by stratum; the strata.

## Decision

- P1 and P3 hold → the SQL finding carries to tool calls: train the quick answer for correctness on open data, check it with a peer
  (claim widened in PROJECT / REPORT / PROPOSAL).
- P1 holds, P3 refuted → training raises the quick calls but not the cascade (its gains fall where the default is already right, or the
  peer stops agreeing); the decomposition says which; reported.
- P1 refuted → ToolACE-trained plain RL does not transfer to BFCL's quick calls for Qwen3-8B in 6,000 requests; reported.

Expected (stated now, not a rule): P1 holds (+1 to +3 points; ToolRL / Tool-N1), P2 holds, P3 holds narrowly (strata here: RW 3.6%,
WR 7.5%, so the room is small), the theory row holds.
