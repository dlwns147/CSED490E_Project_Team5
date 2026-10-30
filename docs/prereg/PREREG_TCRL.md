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

## Results (2026-10-30 08:4x UTC)

Run: job 1282587. Training: 94 rounds × 64 = 6,000 ToolACE requests; training samples right 0.68 → 0.71 (first / last 10 rounds;
requests with calls 0.72 → 0.72, requests with no call 0.38 → 0.65). Test: BFCL quick calls with the final adapter (tag q8btcc1), 3,482
items × 3 seeds, all graded (`grade_tc.py`); `python3.11 poc/analyze_tcrl.py` → results/tcrl.txt.

| policy (Qwen3-8B, peer Qwen3.5-9B) | accuracy | ktokens | utility − SB→T→T |
|---|---|---|---|
| SB→T→T (no-label default) | 83.9% | 0.38 | — |
| base N → peer agrees → N, else SB→T→T | 84.8% | 0.28 | +0.9 [+0.4, +1.3] |
| C1tc N → peer agrees → N, else SB→T→T | 85.2% | 0.27 | +1.35 [+0.97, +1.76] |

- **TCRL-P1 holds:** quick calls right +5.1 [+4.3, +6.0] points (non-live 89.4 → 91.5%, live 69.5 → 76.4%).
- **TCRL-P2 holds:** +1.35 [+0.97, +1.76] utility over SB→T→T (accuracy +1.3 [+0.9, +1.7]).
- **TCRL-P3 holds:** +0.50 [+0.26, +0.76] over the base calls' peer cascade.
- **TCRL-P3 theory refuted:** predicted +1.06 (C1tc's strata RW 5.3%, WR 4.9% with the base's agreement rates) lies above the
  interval; C1tc's measured agreement on its RW items is 33.6% (base 45.2%), on WR 9.7% (11.0%).

**Decision (pre-registered rule):** P1 and P3 hold → the SQL finding carries to tool calls: train the quick answer for correctness on
open data (labels only in training), check it with another model's quick answer. Claim widened in PROJECT / REPORT / PROPOSAL. The
theory row is refuted; the reason, read from the raw rows, follows.

**Raw reading.**
- *What training changed: abstention.* Quick calls right by BFCL category, base → C1tc: live_irrelevance 63.7 → 82.2% (875 items),
  irrelevance 76.9 → 86.0% (240); every category that needs calls within ±1.3 (live_multiple 71.8 → 71.0, live_simple 78.3 → 77.6,
  simple 94.0 → 94.4, multiple 91.5 → 91.7, parallel 92.0 → 91.5, parallel_multiple 90.5 → 91.8; live_parallel(_multiple) +4 to +6 on
  16 / 24 items). C1tc makes no call on 83.0% of irrelevance items (base 66.6%) and on 3.0% of items that need calls (base 0.8%);
  its no-call answers are right 92.9% (base 97.4%). Typical fixes: `[Hotels_2_SearchHouse(where_to="City, State")]` (a placeholder for
  a place the request never names) → `[]`; `[Trains_1_FindTrains(_from="Your Starting City", ...)]` → `[]`. Typical breaks (54 per
  seed, 115 / 162 in live_multiple): `[Services_1_FindProvider(city="San Ramon, CA")]` → `[]`; "Chicago, IL" → "Chi-town, IL";
  `math.hcf` → `Math.hcf`; a call without its brackets.
- *Why the cascade keeps only a third of it.* The peer makes no call on 59.1% of irrelevance items (seed 1), so it disagrees with most of the
  abstentions training adds: on C1tc's new RW items (base wrong, C1tc right, default wrong: 68.7 per seed, 84% of them in
  live_irrelevance) the peer agrees 16.5% (it is right 26.7%); on the RW items the base already had, 43.7%. On SQL the same split is
  48.4% vs 58.0%, which is why CV-P8 / P12's transfer held there. The decomposition's assumption — agreement rates stay with the
  strata — fails when training's corrections are a behaviour the peer lacks: the two models' errors are correlated (Kim et al.,
  Correlated Errors in LLMs, 2506.07962; BFCL's irrelevance score only asks whether a call is made, When2Call 2504.18851).
  Post hoc, not a test: setting each moved item's rate to the peer's accuracy in its base stratum predicts tool calls (+1.33 vs +1.30
  measured) but not SQL (+0.96 vs +1.83): which items training fixes, not their stratum, sets the rate.
- *Identity and ceiling (algebra, no assumption).* The cascade accepts N only when N equals the peer's answer, so its change from
  training is Σ over items whose quick answer changed of [agree(new)·(r_new − r_D) − agree(old)·(r_old − r_D)], and no training of N
  can lift it above the default by more than P(peer right, default wrong): 4.60 points on BFCL, 6.78 on BIRD dev with Qwen3.5-9B. C1tc
  reaches 1.30 of 4.60, SQL's C1 1.83 of 6.78.
- *Agreement is conditionally independent given the item* (exploratory, stored rows): pairing N at seed s with the peer at the other
  two seeds instead of the same seed changes the cascade's gain by ≤ 0.1 points in all 16 pairs (BFCL and BIRD; N base or trained;
  peers Qwen3.5-9B, Qwen3-4B, Llama-3.1-8B, Qwen3-14B-AWQ). The gain is then bilinear in the two models' per-item answer distributions,
  G(N, X) = Σ_i Σ_y P_N(y|i) P_X(y|i) (r(y) − r_D(i)).
- *Training N helps with every peer* (exploratory, accuracy points over Qwen3-8B's default, no intervals): BFCL Qwen3.5-9B +0.50,
  Qwen3-4B +1.01, Llama-3.1-8B +0.32, Llama-3.2-3B +0.39, Qwen3-14B-AWQ +0.79; BIRD +1.39, +1.55, +0.83 (no Llama-3.2-3B row), +1.85.
- *Training lowers the ratio a gate needs* (π_WR / π_RW): 2.08 → 0.93 on BFCL, 2.43 → 1.26 on BIRD. Exploratory gates (BFCL
  cross-fitted over two halves of the items, so in-sample for the benchmark): accepting a no-call quick answer without the peer gains
  +2.36 accuracy points over the default vs the peer gate's +1.36 for C1tc (base +1.47 vs +0.86); on BIRD no answer class beats the
  peer gate; agreement among three quick samples of N is a weak gate everywhere (a_RW / a_WR 1.2–1.5, the peer 2.6–4.1).

## Addendum 1 (2026-10-30 08:5x UTC): a second model, and train the peer too

Written after the results above and before any training round of Qwen3-4B on ToolACE, any BFCL row of it, or any SB / T row of
Qwen3-4B on BFCL.

**Why it could change the claim.** (a) One model is not a recipe: Qwen3-4B, trained the same way, either repeats P1–P3 or does not.
(b) The results above show the cascade keeps about a third of training's gain because the untrained peer does not share the corrections;
with a fixed peer no training of N can exceed P(peer right, default wrong). Agreement is conditionally independent given the item in
all 16 stored pairs, so the cascade's gain is bilinear in the two models' per-item answer distributions,
G(N, X) = Σ_i Σ_y P_N(y|i) P_X(y|i) (r(y) − r_D(i)); training both members then adds the cross term Σ_i Σ_y ΔP_N ΔP_X (r(y) − r_D(i)),
positive when both trainings move probability onto the same right answers where the default fails. Both models learn from the same
data, so on BFCL both should learn the same abstentions. If the cross term is positive, the recipe becomes "train both quick answers";
if training the same data into both makes them share new errors, the theory says it shows up as a broken independence (the other-seed
estimate departs from the same-seed value). (c) The no-call rule found in sample above (accept a no-call quick answer without the peer)
needs a test on a model it was not found on.

**Prior work.** Agreement cascades use fixed members (MoT 2310.03094, ABC 2407.02348, 2509.21837); error correlation across LLMs is
measured (2506.07962) but not used to decide which member to train. Cascade-aware training (2406.00060) trains the small model of a
deferral cascade, not both members of an agreement gate.

**Runs.** (1) Qwen3-4B with the identical recipe (`tc_lane.sh` with TC_BASE=Qwen3-4B, `--base` the same; 6,000 ToolACE requests, the
same order and hyperparameters), BFCL quick calls, seeds 1–3, tag q4btcc1. (2) Qwen3-4B's SB and T on BFCL, seeds 1–3 (tag q4b, its
quick rows exist), for its own SB→T→T. Grading `grade_tc.py`; analysis `python3.11 poc/analyze_pair.py --tc`.

## Predictions (3,482 items × 3 seeds, paired 95% intervals over items, utility)

- **TCRL-P4:** q4btcc1's quick calls right − q4b's: lower bound > 0.
- **TCRL-P5:** utility of N(q4btcc1) → Qwen3.5-9B agrees → N, else Qwen3-4B's SB→T→T, minus that SB→T→T: lower bound > 0.
- **TCRL-P6:** the same cascade minus the one with N(q4b): lower bound > 0.
- **TCRL-P7 (train both; the cross term):** with Qwen3-8B's SB→T→T as the default, N ∈ {q8b, q8btcc1} × peer ∈ {q4b, q4btcc1}: the
  interaction G(trained, trained) − G(trained, base peer) − G(base, trained peer) + G(base, base peer): lower bound > 0.
- **TCRL-P8:** G(q8btcc1, peer q4btcc1) − G(q8btcc1, peer Qwen3.5-9B) (the current best pair): lower bound > 0.
- **TCRL-P8 theory (independence):** in each of the four 2×2 cells the other-seed estimate is within 0.2 utility points of the
  same-seed value.
- **TCRL-P9 (no-call rule, fixed now):** for N(q4btcc1) → Qwen3.5-9B → Qwen3-4B's SB→T→T, accepting a no-call quick answer without the
  peer, minus the plain peer gate: lower bound > 0.

## Decision

- P4–P6 hold → the tool-call recipe holds on a second model (with CV-P14 / P15, two models × two tasks); P4 holds, P6 refuted → the
  4B's gain does not reach the cascade, reported with the decomposition.
- P7 and P8 hold → the recipe becomes "train both quick answers with plain RL; accept when they agree" (PROJECT / REPORT / PROPOSAL).
  P7 holds, P8 refuted → training the peer adds, but a different-family untrained peer is still the better partner; reported. P7
  refuted → no cross term: training the peer is at most additive.
- Theory row refuted in a trained-peer cell → shared training breaks conditional independence; the bilinear account stops there.
- P9 holds → for tool calls the gate is per answer class (no-call answers bypass the peer); refuted → the in-sample gain was this
  benchmark's, reported.

Expected (stated now, not a rule): P4 holds (+4 to +8; the 4B starts lower on irrelevance), P5 and P6 hold, P7 holds narrowly (shared
abstentions), P8 open, the theory row holds in the untrained cells and is the risk in the trained-trained cell, P9 holds.
