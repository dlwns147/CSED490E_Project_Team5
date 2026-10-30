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

## Results, addendum 1 (2026-10-30 10:2x UTC; `python3.11 poc/analyze_pair.py --tc` > results/tcrl_pair.txt; 3,479 / 3,482 items × 3 seeds)

| | utility − default [95%] |
|---|---|
| Qwen3-4B: base quick calls → Qwen3.5-9B → Qwen3-4B's SB→T→T (85.5%) | −0.22 [−0.66, +0.19] |
| Qwen3-4B: C1tc-4B → Qwen3.5-9B → that default | +0.94 [+0.57, +1.33] |
| Qwen3-4B: C1tc-4B, no-call answers accepted without the peer | +1.08 [+0.34, +1.84] |
| Qwen3-8B's default (83.9%): N q8b → peer q4b / q4btcc1 / q35 | +0.18 / +1.62 / +0.85 |
| N q8btcc1 → peer q4b / q4btcc1 / q35 | +1.19 / **+2.60 [+1.90, +3.33]** / +1.35 |

- **TCRL-P4 holds:** quick calls right 73.0 → 82.0%, +9.0 [+7.7, +10.3].
- **TCRL-P5 holds:** +0.94 [+0.57, +1.33].
- **TCRL-P6 holds:** +1.16 [+0.80, +1.56] over the base 4B's cascade.
- **TCRL-P7 refuted:** interaction −0.03 [−0.54, +0.49]: the two trainings add (training N +1.01 with the base peer, training the peer
  +1.44 with the base N, both +2.42).
- **TCRL-P8 holds:** G(q8btcc1, q4btcc1) − G(q8btcc1, Qwen3.5-9B) = +1.25 [+0.61, +1.86].
- **TCRL-P8 theory holds:** the other-seed estimate is within 0.09 of the same-seed value in all four cells (and +0.10 / 0.00 with
  Qwen3.5-9B), so shared training data did not break conditional independence.
- **TCRL-P9 refuted:** +0.14 [−0.50, +0.78].

**Decision (pre-registered rules).** P4–P6 hold → the tool-call recipe holds on a second model (with CV-P14 / P15 pending, the SQL
side). P7 refuted → no cross term: training the peer is at most additive; the recipe is not changed to "train both" on a synergy
claim. P8 holds as stated: the pair of two trained quick models is the best measured system on BFCL (+2.60 over Qwen3-8B's default,
86.5% at 0.27k tokens), +1.25 over the previous best pair. The theory row holds. P9 refuted → the no-call rule was the 8B's.

**Raw reading.**
- *The 4B learned the same thing, more of it.* Quick calls right by category, base → C1tc-4B: live_irrelevance 53.3 → 86.8% (874
  items), irrelevance 65.8 → 90.1% (240); live_multiple 70.3 → 67.8, live_simple 82.9 → 77.3, live_relevance 97.9 → 62.5 (16 items);
  the rest within ±2. 436 question-seeds per seed move wrong → right (881 / 1,308 in live_irrelevance), 124 right → wrong (226 / 372 in
  live_multiple).
- *Why the no-call rule fails on the 4B.* C1tc-4B abstains on 1,080 items per seed (8B: 982; base 4B: 621) and 9.8% of its abstentions
  are wrong (8B 5.9%, base 4B 0.5%): it drops supported calls, e.g. `[Movies_3_FindMovies(directed_by="Hari Sama")]` → `[]`,
  `[calc_absolute_pressure(atm_pressure=1, gauge_pressure=2)]` → `[]` (214 / 324 wrong abstentions in live_multiple). The default
  is right on 88.5% of the items it abstains on, so accepting them unchecked gains 1.7 accuracy points where it lost 6.2 on the 8B.
- *Why there is no cross term (bilinear decomposition, per-item answer distributions over 3 seeds, Qwen3-8B's default, utility
  points).* The interaction is Σ_i Σ_y ΔP_N ΔP_X (r(y) − r_D(i)) (+ the saved default tokens); its terms by answer class: both
  trainings move onto the same right abstention where the default is wrong +1.17; onto the same wrong abstention where the default is
  right −0.61; both remove the same shared wrong call where the default is right −0.82 (one trained member already breaks the
  agreement, so the second adds nothing: the main effects count it twice); the rest +0.33; total +0.08 (measured −0.03). The main
  effects: training N +0.93, training the peer +1.39, most of each from removing wrong calls the base pair shared where the default is
  right (+0.79 / +0.92).
- *Headroom (exploratory).* With the peer fixed, the best any N can do under the bilinear account is Σ_i max(0, max_y P_X(y|i)(r(y) −
  r_D(i))) (biased up: a max over 3-sample estimates): +3.70 with Qwen3.5-9B (q8btcc1 reaches +1.37), +6.90 with C1tc-4B (+2.66), +3.95 with the base 4B (+1.19); on BIRD
  +7.09 with Qwen3.5-9B (C1 +1.98). Plain RL trains toward the right answer whether or not the peer can confirm it and whether or not
  the default already has it; most of the headroom is left.

## Addendum 2 (2026-10-30 10:2x UTC): train one member for the cascade it is deployed in

Written before any row of the runs below exists, training-item rows included (the input jobs 1283524–1283526 were submitted at
10:2x UTC and are loading their servers), and before CV addendum 6's C1w (a two-weight version of the same idea on SQL) has a graded
dev row.

**Why it could change the claim.** Conditional independence held in all 20 cells measured, so with the peer X and the default D fixed
the deployed cascade's utility is linear in N's answer distribution: G = Σ_i Σ_y P_N(y|i) w(y, i), with
w(y, i) = P_X(y|i) (r(y) − r_D(i) + 0.005 kd(i)) (accepted only when X gives the same answer; kd = the default's ktokens that the
acceptance saves; utility = accuracy − 0.5 × ktokens in points; N's and X's own tokens are paid either way). Plain RL maximises
Σ P_N r instead: it rewards right answers the peer cannot confirm (worth nothing in the cascade) and right answers where the default is
already right (worth the saved tokens only), and it penalises a wrong answer the same whether or not the peer shares it where the
default is right (the only way the cascade loses accuracy). w is the cascade's exact per-sample reward, and because it is linear in
r_D and P_X, one default sample and K peer samples per training item estimate it without bias. Headroom (addendum 1): the best
response to Qwen3.5-9B is +3.70 (plain RL's C1tc +1.37), to C1tc-4B +6.90 (+2.66). If the exact reward moves N toward the best
response, the recipe becomes "train the quick answer for the cascade it is deployed in"; if not, plain RL is what transfers, and the
objective's extra terms do not survive the shift from ToolACE to BFCL.

**Prior work.** Cascade-aware training (2406.00060) masks the tokens both models get wrong in the small model's distillation loss and
defers by the small model's own likelihood: no agreement gate, no reward from the other model's answer distribution or the fallback's
correctness. Learning to defer (2006.01862) trains a classifier with a rejector to be right where the expert is not; negative
correlation learning (Liu & Yao 1999) penalises ensemble members' shared errors; joint training of deep ensembles fails through learner
collusion (Jeffares et al., NeurIPS 2023), so here the peer stays fixed and only one member is trained. LLM juries (2607.10139) name
training models "that fail differently" as future work. None trains a member against a fixed peer's per-item answer distribution and
the fallback's per-item correctness.

**Runs.** (1) Inputs on the 6,000 ToolACE items of tc_train.py's order (`/toolace/tc_train_ids.txt`): Qwen3-8B's SB, seed
1, and its T, seed 1, where SB fails the free check (tag taq8b, job 1283524); quick answers, seeds 1–4, of Qwen3.5-9B (taq35, 1283525)
and C1tc-4B (taq4btcc1, 1283526). `python3.11 poc/prep_tcbil.py taq8b <peer tag> 4` → `/toolace/tc_bil_<peer tag>.json`.
On training items the free check, agreement and correctness are poc/tc_reward.py's check / canon / right, the functions the trainer
calls. (2) Arms: Qwen3-8B, C1tc's loop, items, order and hyperparameters; only the reward changes, to c × [N passes the check] × w, with
c = 1 / the mean over the 6,000 items of max(0, max_y w) − min(0, min_y w) (the mean per-item reward range equals plain RL's 1, as C1w
normalises its weights). **B35:** peer Qwen3.5-9B (`--bil tc_bil_taq35.json`, tag q8btcb35). **B4t:** peer C1tc-4B
(`--bil tc_bil_taq4btcc1.json`, tag q8btcb4t). Each through tc_lane.sh: BFCL quick calls, seeds 1–3, grade_tc.py. C1tc-4B was trained
on these 6,000 items (one pass), so its P_X there is optimistic; BFCL is in neither training set. Analysis
`python3.11 poc/analyze_pair.py --bil`.

## Predictions (3,482 items × 3 seeds, paired 95% intervals over items, utility, Qwen3-8B's SB→T→T as the default)

- **TCRL-P10:** G(B35, Qwen3.5-9B) − G(C1tc, Qwen3.5-9B): lower bound > 0.
- **TCRL-P11:** G(B4t, C1tc-4B) − G(C1tc, C1tc-4B): lower bound > 0.
- **TCRL-P12 (mechanism, per arm against C1tc with the same peer):** the share of question-seeds accepted wrong where the default is
  right: upper bound < 0. Reported with it: accepted right where the default is wrong.
- Reported, not decided: each arm's quick calls right against C1tc's (the reward ignores right answers the peer cannot confirm, so
  quick accuracy may fall while the cascade gains); each G against the best-response bound (+3.70 / +6.90).

## Decision

- P10 and P11 hold → the recipe becomes: train the quick answer with the cascade's own reward (the peer's answers and the default's
  correctness on the training items; nothing labelled at test). PROJECT / REPORT / PROPOSAL; the SQL side next.
- One of P10 / P11 holds → reported with the peer it holds for; the claim names it.
- Both refuted, P12 holds for an arm → the reward moves the cascade's errors where derived, but too little to show in utility.
- Both refuted, P12 refuted → the training-distribution reward does not transfer from ToolACE to BFCL; plain RL stays the recipe.

Expected (stated now, not a rule): P10 holds narrowly (+0.3 to +0.8; with Qwen3.5-9B C1tc's accepted-wrong share is already 0.5%, so
the gain must come from right answers the peer confirms where the default fails), P11 holds (C1tc's accepted-wrong share with C1tc-4B
is 1.6%), P12 holds for B4t; both arms' quick accuracy 1–3 points below C1tc's.

## Amendment to addendum 2 (2026-10-30 10:4x UTC, before any training round and any BFCL row of the arms): CV addendum 6's result, and a third arm

The input jobs were resharded for speed (1283524 / 1283525 cancelled at 839 / ~700 rows; the rest in 1283546–1283550, tags taq8bp<j>
/ taq35p<j>, merged into taq8b / taq35 before `prep_tcbil.py`; T on the SB-check failures as job tbil_q8bt). No reward file exists yet.

CV addendum 6 (b) came in meanwhile: C1w, a two-weight version of the cascade's gradient on SQL (C1's reward × 1.83 where the base
T→T fails, × 0.50 where it succeeds), lost to plain C1 (−0.44 [−0.93, −0.00]); it did not move right answers onto the questions the default
fails and it learned less of the conventions that transfer, on the questions the default already gets right. The exact reward w of
B35 / B4t also drops the reward for right answers there (it keeps only the saved tokens), so the same failure is possible; what w has
and C1w lacks is the penalty on wrong answers the peer shares where the default is right. The expectations above are revised (not a
rule): P10 refuted, P11 inconclusive, P12 holds for B4t.

**Third arm, P4t:** the quick answer's own accuracy plus the cascade's utility, both in accuracy units and with no scale: reward
r(y) + w(y, i) (`--bil tc_bil_taq4btcc1.json --plus`, peer C1tc-4B, tag q8btcp4t, job tcp4t, out `/cv/tc_p4t`). It keeps
plain RL's signal on every item and adds the cascade's terms (more reward for right answers the peer confirms where the default fails,
less for wrong answers the peer shares where the default is right).

- **TCRL-P13:** G(P4t, C1tc-4B) − G(C1tc, C1tc-4B): lower bound > 0 (utility, paired over items, Qwen3-8B's SB→T→T as the default).
- Reported with it, as P12: accepted wrong where the default is right, accepted right where it is wrong, quick calls right.
- **Decision:** P13 holds → the recipe adds the cascade's own reward to plain RL's (PROJECT / REPORT / PROPOSAL); with P11 refuted it
  is the plain signal that carries the transfer and the cascade term that aims it. P13 refuted → plain RL stays the recipe; reported
  with the mechanism.

Expected (not a rule): P13 holds narrowly (+0.2 to +0.7).

## Note (2026-10-30 11:5x UTC, before any training round): the reward inputs

Built by `prep_tcbil.py` on the 6,000 training requests (all have Qwen3-8B's SB, seed 1, and 4 quick samples of each peer; T seed 1 on
the 110 whose SB fails the free check). The default (SB→T) is right on 70.6% of them (BFCL: 83.9%). Peer Qwen3.5-9B: quick calls right
60.6%, no call 4.8%; an answer with w > 0.01 on 6.7% of the requests, one with w < −0.01 on 12.8%; mean per-request range of w 0.106,
scale c = 9.39 (B35). Peer C1tc-4B: right 70.4%, no call 12.7%; w > 0.01 on 8.2%, w < −0.01 on 6.6%; range 0.124, c = 8.06 (B4t; P4t
uses w unscaled). So B35's reward is mostly the veto (twice as many requests where a shared answer loses to the default as where one
gains), and B4t's is balanced. Jobs: tcb35 1283750, tcb4t 1283751, tcp4t 1283752.

## Addendum 3 (2026-10-30 11:5x UTC, before any held-out row; the three trainings at round ~5 of 94): where the cascade reward works — the training distribution vs BFCL

**Why.** P10, P11 and P13 are tested on BFCL, while the reward is computed on ToolACE. A refuted P13 would not say whether the reward
fails to steer the quick answer at all (one pass of GRPO; only 6.6–12.8% of the training requests carry a w beyond ±0.01) or steers it
where it was trained and does not transfer. The two failures call for different next steps (the optimiser vs the source of the
reward), so the arms are also measured on requests from the training distribution that no arm trained on.

**Set.** The 3,549 requests of tc_train_items.jsonl after tc_train.py's first 6,000 in its order (`$POC_DATA/toolace/tc_ho_ids.txt`;
disjoint from the training ids, checked). Qwen3-8B's default from one sample (SB seed 1, T seed 1 where SB fails the free check; tag
hoq8b), K = 4 quick samples of each N (base hoq8b, C1tc hoq8btcc1, B35 hoq8btcb35, B4t hoq8btcb4t, P4t hoq8btcp4t) and of each peer
(Qwen3.5-9B hoq35, C1tc-4B hoq4btcc1). `poc/analyze_tcho.py`: every N sample paired with every peer sample (independent, so unbiased);
an N answer that fails the check goes to the default, one that passes is accepted with the share of peer samples that pass and make
the same calls, else the default; G = the cascade's utility minus the default's (accuracy − 0.5 × ktokens, points); paired 95%
bootstrap intervals over requests. Smoke on the training requests (stand-in arms): it runs, and G is symmetric in N and X as it must be.

- **TCRL-P14:** G_H(B35, Qwen3.5-9B) − G_H(C1tc, Qwen3.5-9B): lower bound > 0.
- **TCRL-P15:** G_H(B4t, C1tc-4B) − G_H(C1tc, C1tc-4B): lower bound > 0.
- **TCRL-P16:** G_H(P4t, C1tc-4B) − G_H(C1tc, C1tc-4B): lower bound > 0.
- Reported, not decided: G_H(C1tc) − G_H(base) with each peer (plain RL's own gain where it trained); for each arm, its BFCL difference
  (P10 / P11 / P13) over its held-out one (the share that transfers); accepted wrong where the default is right.

**Decision (with P10 / P11 / P13 of the same arm).**
- Held-out holds, BFCL holds → the recipe of addendum 2's decision; the transfer share is reported with it.
- Held-out holds, BFCL refuted → the reward steers the cascade where it is computed and the gain does not carry to BFCL: the claim
  says the cascade reward is specific to the distribution it is computed on, and the next test computes it on requests closer to the
  deployment (the source of r_D and P_X, not the optimiser).
- Held-out refuted → one pass of GRPO does not follow the cascade reward even in distribution: the next test is the optimiser (the
  requests that carry w, more passes), not the transfer.

Expected (not a rule): P15 and P16 hold (+0.5 to +1.5 on held-out, at least twice their BFCL difference); P14 holds narrowly.

## Note (2026-10-30 13:0x UTC, before any BFCL or held-out row of the three arms): the training logs, and why an item's cascade value is not its weight

**Logs** (each round samples 64 requests not seen before, so a window's means are on-policy estimates on new requests; rounds 1–15 →
76–90; C1tc's log for comparison, which has no w):

| arm | quick right | right on no-call requests | w per sample | peer agrees |
|---|---|---|---|---|
| C1tc (plain) | 0.670 → 0.683 | 0.38 → 0.72 (0.84–0.88 in mid rounds) | — | — |
| B35 | 0.669 → 0.647 | 0.37 → 0.40 | +0.0056 → +0.0138 | 0.63 → 0.61 |
| B4t | 0.669 → 0.644 | 0.37 → 0.41 | +0.0018 → +0.0137 | 0.70 → 0.70 |
| P4t (rounds → 86) | 0.669 → 0.664 | 0.38 → 0.72 | +0.0018 → +0.0155 (0.019 at 61–75) | 0.70 → 0.73 |

All three raise their own w (by about one utility point per request); the B arms do not learn abstention, which was most of C1tc's
gain on BFCL, and P4t learns it as C1tc did and raises w more than B4t, which follows w alone.

**Why (derivation).** One update moves the parameters by η Σ_i ∇J_i over the training requests (J_i = Σ_y P(y|i) R_i(y)), and the
cascade's value on a test request j by η Σ_i ⟨∇G_j, ∇J_i⟩. Along a behaviour the model generalises as a whole, f (abstain when no
function fits), the gradients factor: ⟨∇G_j, ∇J_i⟩ ≈ Δ_f w_j · Δ_f R_i, so the test gain from f is proportional to (Σ_j Δ_f w_j)(Σ_i
Δ_f R_i): the *training* reward summed along f, times its *test* value. With R = w the first factor is the cascade value of f on the
training requests, small where the default already abstains correctly (w = P_X · 0.005 kd there): f is learned only as far as the
training default fails at it, whatever its value at test. With R = r the factor is f's accuracy gain, large whenever f is right. So the
item's own cascade value is the right weight only for what the model learns item by item; for a shared behaviour the right weight is its
value on the test distribution, which on BFCL (default right 83.9%, vs 70.6% on ToolACE) differs. This is C1w's failure on SQL in
general form, and it predicts that the B arms' deficit against C1tc is larger on BFCL than on held-out ToolACE, where the training
weights are the test weights.

Expected now (not a rule, replacing the earlier expectations): P10 and P11 refuted; P13 inconclusive or holds narrowly; on held-out,
P16 holds, P15 inconclusive, P14 refuted or inconclusive; each B arm's BFCL difference below its held-out difference.
