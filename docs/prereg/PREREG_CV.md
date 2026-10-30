# PREREG CV-1: training the quick mode for the cascade's value (text-to-SQL, Qwen3-8B)

Written 2026-10-29 11:3x UTC, before any CV code ran, any BIRD train row was generated, or any dev row of a trained model exists.

## Why it could change the claim

Every result so far says the free check decides: where passing quick answers are often wrong, starting cheap loses accuracy (SQL-1:
41–43% of check-passing non-thinking queries are wrong, the check catches 30–36% of wrong ones; N→T −2.7 to −5.9 points against one
think), and every stronger check we built (self-review, solution checker, cross-mode agreement) costs about as much as the think it
saves. *Cheap Verifiers, Large Blind Spots* (2609.01345) measures the same blind spot between models. Each of our fixes changed the
check; none changed the generator. CV-1 trains the quick mode itself so that its silent errors become visible (it defers) and its right
answers are kept, with the whole cascade's value as the reward. Headroom (SQL-1, Qwen3-8B, computed 2026-10-29 10:5x UTC): with a
perfect check on the quick query, quick → think-with-retry reaches 62.8% at 1.23k tokens, against T→T 59.2% at 1.85k and the
no-label default SB→T→T 59.5% at 1.68k; the plain check gives N→T 52.2% at 0.60k.

## Prior work, and what is new here

- Cascade-Aware Training (2406.00060, Google 2024): the small model of a two-model cascade is trained with knowledge of its role
  (token-level loss; SuperGLUE / WMT / FLAN). TruthRL (2509.25760, ICML 2026): GRPO with a ternary reward, abstention neutral.
  Thinkless (2505.13379) / AdaptThink (2505.13417): RL chooses think / no-think *before* answering, rewarded for accuracy and length.
  Fast-Slow Thinking RM (2603.20212): a trigger token escalates a judge to slow thinking. RL for text-to-SQL (Reasoning-SQL 2503.23157,
  Think2SQL 2504.15077, Reward-SQL 2505.04671) maximises the query's own accuracy. Trained SQL verifiers (2606.30851, SQL-Checker,
  CHASE-SQL's selector 2410.01943) use labels at selection time. 2609.01345: fine-tuning a student on its verifier's rejections
  degrades it.
- New: RL on the quick (non-thinking) mode of one hybrid model where escalation is valued at *the same model's* think outcome and
  tokens on that question, and the quick mode decides after seeing its own query's execution result; no labels at inference; two
  controls that separate the cascade objective from RL itself (C1) and from a gate on frozen drafts (C2).

## Run

**Data.** Training: BIRD train (train.zip from bird-bench, 9,428 questions, 69 databases), prompts built exactly as SQL-1's (each
table's CREATE TABLE and 3 rows, evidence, question; `poc/prep_sql.py`'s format); kept if the gold query returns ≥ 1 row within 10 s
and the prompt is ≤ 4,000 tokens. Test: BIRD dev, SQL-1's 1,530 graded questions, never used in training or tuning.
**Escalation values.** Base Qwen3-8B thinking on every kept training question, as SQL-1's T arm (16k cap, harness sampling T 0.7), one
sample, plus a second think where the first one's query fails the check: v(x) = T→T right (0 / 1), c(x) = its tokens.
**Policy** (LoRA r 16, α 32, all linear layers, on Qwen3-8B; non-thinking; base weights frozen; thinking always the base model):
- turn 1: the SQL-1 prompt plus one line, "If you would need to think step by step to get it right, reply only DEFER." → a query or DEFER.
- the free check (runs, ≥ 1 row; 10 s in training, 30 s at test). Failed check → escalate.
- turn 2 (only after a passing check): the query's column names, row count and first 5 rows (values cut at 50 characters), "Does this
  result answer the question? Reply ACCEPT or DEFER." ACCEPT → the query is the answer; anything else → escalate.
- escalate = T→T of the base model (think; think again if its query fails the check).
**Reward** per trajectory (accuracy units, λ = 0.005 per 1k tokens = SQL-1's 0.5 utility points per 1k): ACCEPT: right − λ·k_quick;
escalate: v(x) − λ·(k_quick + c(x)). GRPO without std normalisation (advantage = reward − group mean), 8 turn-1 samples per question,
one turn-2 sample each, 128 questions per round, PPO-clip 0.2 over 4 mini-batches per round, lr 2e-5, no KL term; gradient through
the prompt's keys and values is stopped (its log-probs use the current adapter). Rounds until 6,000 training questions are seen.
Engineering settings may change in the smoke (recorded as an amendment), never after a dev row of a trained model exists.
**Arms (three trainings, same loop and data):**
- **CV** — both turns trained, DEFER allowed in turn 1.
- **C1 (plain RL)** — turn 1 only, no DEFER, reward = the query right (standard RLVR); deployed as quick → check → T→T.
- **C2 (gate on frozen drafts)** — turn 1 is the base model (no gradient, no DEFER), turn 2 trained with CV's reward.
**Test.** Dev, seeds 1–3, turn 1 at T 0.7 with SQL-1's per-question seeds, turn 2 greedy. Escalations reuse SQL-1's q8b think rows
(T at seed s, its retry from seed s mod 3 + 1, as `poc/analyze_sql.py`): the base model's thinking is unchanged by the adapter.
Paired 95% intervals over questions (seed means), output tokens per question (all turns, the checks' prompts not counted).

## Predictions (each over 1,530 dev questions, 3 seeds)

- **CV-P1 (a saving against the best fixed order):** CV − T→T accuracy: paired upper bound ≥ 0, at ≤ 75% of T→T's tokens.
- **CV-P2 (beats the no-label default):** utility (λ = 0.5) CV − SB→T→T: paired lower bound > 0.
- **CV-P3 (the objective, not RL itself):** utility CV − C1: paired lower bound > 0.
- **CV-P4 (training the generator too, not only a gate):** utility CV − C2: paired lower bound > 0.
- **CV-P5 (the blind spot shrinks):** of the questions CV answers itself (ACCEPT), ≤ 20% are wrong (SQL-1 q8b: 42.9% of check-passing
  N), and it answers itself ≥ 40% of questions.
- Reported, no decision: the accuracy–token frontier from thresholding P(ACCEPT); turn-1 DEFER rate; the quick query's own accuracy
  for CV, C1 and the base (does CV degrade the drafts, as 2609.01345 found for corrective fine-tuning?); by difficulty; raw
  turn-2 decisions read for right-but-deferred and wrong-but-accepted queries.

**Expected (stated now, not a rule).** P5 partly (the wrong share among accepted falls to 25–30%: the result preview shows empty,
NULL-only and wrong-shape results, not wrong filters). P1 holds narrowly. P3 uncertain (plain RL also raises the quick query). P4
holds weakly. The main risk is the shared blind spot (2607.13918): the quick mode may not see its own wrong-but-plausible results.

## Decision

- P1, P2 and P5 hold → training the quick mode for the cascade turns SQL's trade into a saving with no labels at inference: the
  claim changes (PROJECT §2, REPORT, PROPOSAL / PROPOSAL_ko); next, the same loop on word problems (OptiBench), pre-registered then.
- P1 holds, P3 refuted → plain RL on SQL explains the gain (known: Reasoning-SQL, Think2SQL); the cascade objective adds nothing; reported.
- P4 refuted → a gate on frozen drafts is enough; the generator need not be trained; reported, and the gate is the method.
- P5 refuted → the quick mode cannot learn to see its own errors from its result: the blind spot is shared, as the correlated-verifier
  theory predicts; next, a decorrelated gate (another family) on the same reward.

## Note (2026-10-29 11:4x UTC, after writing `poc/analyze_cv.py`, before any CV row): what a perfect gate reaches

Checking `poc/analyze_cv.py` with an oracle gate on SQL-1's base queries (ACCEPT exactly the right ones; turn 2 counted as 1 token;
escalation T→T): 63.5% at 1.46k tokens, +4.2 [+3.4, +5.1] over T→T at 79% of its tokens (SQL-1's 19% failed checks and the 35%
wrong-but-passing queries escalate). So CV-P1's token bound (≤ 75% of T→T's tokens) cannot be met by a gate on unchanged drafts,
even a perfect one: it needs the quick query itself to fail less or defer earlier (fewer escalations after a wasted query does not
lower the bound; more right first queries does). The prediction is unchanged; C2 (a gate only) cannot satisfy P1 by construction.

## Addendum (2026-10-29 11:5x UTC, before any CV row): theory of the cascade, a new prediction, and a correction to the note above

**Model.** Per question x: the quick query is right with probability p(x) (on SQL-1 every right quick query passes the check); a wrong
one passes the check with q(x); the gate accepts a right passing query with 1 − α, a wrong passing one with β; the escalation (T→T) is
right with v(x) and costs c(x) tokens; the quick query costs k(x). Then
- (1) accuracy A = E[ v + p(1−α)(1−v) − (1−p)·q·β·v ];
- (2) tokens K = E[ k + c·(p·α + (1−p)(1 − q·β)) ].
Against always escalating (T→T: A = E v, K = E c) the cascade gains p(1−α)(1−v) — the quick query right where the think is wrong
(*complementarity*) — and loses (1−p)qβv — the quick query wrong, check and gate blind, the think would be right (*the blind spot*); it
saves c on every question it does not escalate.
- (3) ∂A/∂p(x) = (1−α)(1−v) + qβv and ∂K/∂p(x) = −c(1 − α − qβ). Plain RL (C1) weights every question 1; the cascade objective weights a
  question by how often the think fails on it (plus the leak while the gate is blind) and its token term by the think's cost there.
  With a good gate, making the quick query right where the think is right buys only tokens, no accuracy.

**Ceilings on SQL-1's base queries** (Qwen3-8B, 4,590 question-seeds, realised v ∈ {0, 1}; computed with `poc/analyze_cv.py`'s base()):
- P(quick right ∧ T→T wrong) = 4.2%: no gate on these queries can add more than +4.2 points over T→T (the oracle: 63.5%).
- Escalating exactly the wrong queries costs 79% of T→T's tokens because the questions the quick query gets right are the think's
  cheap ones: 46.0% of the questions, 24.9% of T→T's tokens (mean 1,001 vs 1,851); the quick queries add 3.9%. In general a cascade
  that escalates every wrong quick answer spends ≥ 1 − S + k̄/c̄ of the think's tokens, S = the think-token share of the questions the
  quick answer gets right.
- **Correction to the note above** (it said a gate on unchanged queries cannot meet CV-P1's token bound): a gate that also keeps the
  wrong queries on questions where the think is wrong too loses nothing and reaches the same 63.5% at 0.94k, 51% of T→T's tokens.
  19.5% of the quick queries fail the check; their questions hold 37.9% of T→T's tokens and T→T is right on only 34.3% of them. The
  token lever is predicting where the think fails, not only whether the quick query is right; C2 can meet P1 if its gate learns that.
  With λ = 0.005 per 1k tokens, keeping a wrong query gains only λc ≈ 0.01 where the think fails and loses 1 where it would succeed, so
  a trained gate keeps one only when nearly sure the think fails (expected: tokens well above 51%).

**New prediction from (3)** (no other prediction changes):
- **CV-P6 (complementarity):** on dev, CV's quick query gains more over C1's on the questions where SQL-1's T→T is wrong than on those
  where it is right: mean (CV − C1) quick-query accuracy on T→T-wrong question-seeds minus on T→T-right ones, bootstrap over questions,
  lower bound > 0. Reported with it: each gate's accept rate on passing wrong queries split by T→T right / wrong.

## Amendment (2026-10-29 13:0x UTC, engineering, from the smoke; before any dev row of an arm)

- Rounds of 64 questions with one optimizer step each (on-policy, so no PPO clipping) instead of 128 questions and 4 clipped
  mini-batches; 6,000 questions = 94 steps.
- Turn 2 is not sampled in training: its loss is its exact expected reward over {ACCEPT, DEFER} (both outcomes are known for every
  passing query, a zero-variance estimator), and a passing query's turn-1 value is that expected reward; at test turn 2 is greedy.
- Quick queries are capped at 512 tokens in training (test: 2,048, as SQL-1); one sequence per gradient chunk (on one 24 GB GPU, SDPA
  keeps each sequence's GQA-repeated prompt keys and values for the backward pass); result-preview lines are cut at 300 characters
  (training and test). Turn 1 counts as DEFER when the reply has no query and contains DEFER.
- Smokes: 1276741 ran out of GPU memory (four completions per chunk); 1276869 ran 3 rounds of 32 questions with dummy escalation values
  (v = 0.5 everywhere), per round about 25 s sampling, 60 s running the queries, 90 s training, adapters loaded into vLLM each round;
  its dev rows (tag q8bcvsmoke, every 50th question) were read only for format and are discarded.

## Amendment 2 (2026-10-29 16:1x UTC, engineering; before any dev row of an arm)

- The first trainings (1277124 cv / 1277125 c1 / 1277126 c2, from about 15:2x UTC) were stopped: cv ran out of GPU memory in its
  first round, in the turn-1 backward pass on a long-schema question (SDPA keeps each layer's GQA-repeated prompt keys / values and
  every layer's activations: over 23.5 GiB for a ~3.9k-token prompt with a 512-token query); c1 (2 rounds) and c2 (1 round) run the same
  code and would have failed on the same kind of question, so all three restart together. Their logs are kept as `*_oom1`; their
  rounds are not used.
- Change (the gradients are the same; only memory differs): each decoder layer is recomputed in the backward pass (activation
  checkpointing), the prompt's keys / values (no gradient) are handed to each layer directly, the vocabulary log-softmax is taken in
  chunks of 128 positions, and the gate uses only the two logits it needs (ACCEPT, "DE"). Check (job 1277919, Qwen3-8B with a random
  non-zero adapter): log-probs equal the previous code's to 4 decimals (−305.6608 both), the gate's P(ACCEPT) to 5 (0.93991), LoRA
  gradients cosine 0.99993 / 0.99987 (bf16); peak memory on the longest training prompt (3,870 tokens) with a 512-token query 16.7 GiB.
- Nothing else changes (questions, order, rewards, λ, rounds, learning rate, evaluation).

## Addendum 3 (2026-10-29 19:4x UTC, before any dev row of an arm): an untrained, decorrelated gate as a comparator

Seen before writing this: the three trainings' logs to round 20 (cv), 59 (c1), 27 (c2) on training questions, and SQL-1's stored dev
rows of the other models (PREREG_SQL.md addendum SQL-PA). In training rounds 16–27, c2's gate keeps 71–78% of right passing queries
and 47–55% of wrong ones (cv: 78% / 55% in rounds 16–20; the base gate kept all). On dev, accepting Qwen3-8B's passing query only when
Qwen3.5-9B's quick query (≈ 63 tokens) returns the same rows keeps 79% / 25%: the trained in-model gate shares more of the quick
query's wrong answers than an untrained peer does (SQL-PA's error coincidence).
- **CV-P7 (an untrained decorrelated gate against the trained one):** on SQL-1's base queries, utility of N → peer agrees → answer,
  else T→T (the peer's tokens counted) minus c2's: paired lower bound > 0. Reported with it: peer minus cv.
- Decision: P7 holds → the gate's limit is the model's own blind spot, and a peer's quick query is the gate (no training; with P5's
  branch, "a decorrelated gate", answered by SQL-PA). P7 refuted → training the gate is worth more than a peer; reported.
- Computed by `python3.11 poc/analyze_cv.py` (block CV-P7, written now). Nothing else changes.

## Results (2026-10-30 04:2x UTC; `python3.11 poc/analyze_cv.py` > results/cv.txt, 1,530 dev questions × 3 seeds in every arm)

| policy | accuracy | tokens | utility |
|---|---|---|---|
| T (one think) | 58.1% | 1.60k | 57.3 |
| T→T | 59.2% | 1.85k | 58.3 |
| SB→T→T (no-label default) | 59.5% | 1.68k | 58.6 |
| base N→T→T | 52.7% | 0.77k | 52.3 |
| **CV** | 59.2% | 1.93k | 58.3 |
| **C1** (plain RL, N→T→T) | 57.6% | 0.78k | 57.2 |
| **C2** (gate on frozen drafts) | 59.2% | 1.92k | 58.3 |
| peer gate (N → Qwen3.5-9B's N same rows → N, else T→T) | 59.7% | 1.53k | 59.0 |

- **CV-P1 refuted:** CV − T→T accuracy +0.0 [+0.0, +0.0] at 104% of its tokens (bound: ≤ 75%).
- **CV-P2 refuted:** utility CV − SB→T→T −0.3 [−1.1, +0.4].
- **CV-P3 refuted:** utility CV − C1 +1.1 [−0.6, +2.7] (accuracy +1.7 [−0.0, +3.3], at 247% of C1's tokens).
- **CV-P4 refuted:** CV − C2 +0.0 [+0.0, +0.0]: the two trained gates end identical.
- **CV-P5 refuted:** CV answers 0% of questions itself (needs ≥ 40%).
- **CV-P6 refuted:** (CV − C1) quick-query accuracy on T→T-wrong minus T→T-right −2.3 [−5.3, +0.7].
- **CV-P7 refuted:** utility peer − C2 +0.7 [−0.2, +1.5] (accuracy +0.5 [−0.4, +1.3]); peer − CV the same.

**Both trained gates collapsed to "always defer".** On all 3,690 (CV) and 3,705 (C2) passing dev queries, ACCEPT is not among the 20
most likely first tokens (`cv_eval.py` then records P(ACCEPT) = 0), so the frontier over τ = 0.1–0.9 is one point (59.2% at 1.93k),
and CV is T→T plus a wasted quick query. In training, C2's gate accepted 90% of passing queries in round 1, 69% in round 13, 38% in
round 31, 28% in round 37 (88% of them right), 20% in round 49 (92%), 5% in round 55 (100%), and none from round 85; CV's the same
(none in rounds 91–94). No turn-1 DEFER in any round or on dev.

**Reported.** The quick query's own accuracy: CV 46.1%, C1 50.6%, base 46.0% (CV did not degrade the drafts, as 2609.01345 found
for corrective fine-tuning; it did not change them). Length: base 72.2, CV 74.8, C1 68.9 tokens. Accept rate on passing wrong queries:
0% for both gates whether T→T is right (n 471 / 496) or wrong (n 1,090 / 1,088).

**Raw reading.** With no ACCEPT, every right passing query is deferred; the costly ones are those where T→T is wrong (68 question-seeds
of seed 1). Read, they are mostly convention cases where the gold follows the literal reading and the think's more careful one
differs: the think joins on `substr(CDSCode, 2)` (q 39), drops DISTINCT (232), counts DISTINCT where the gold counts rows (363), counts
posts with `Tags LIKE '%careers%'` where the gold counts the tag row (696). Nothing in the quick query's result marks them.

**Theory (post hoc, from the pre-registered model above and SQL-AND's decomposition, PREREG_SQL.md).**
- *The gate.* Turn 2's loss is its exact expected reward, so its gradient on a passing query is σ'(z)·Δ with Δ = right − v + λc:
  +1 + λc where the query is right and T→T wrong (RW, 4.2% of dev question-seeds), −1 + λc where it is wrong and T→T right (WR,
  10.8%), only λc ≈ 0.005–0.02 on RR (41.7%) and WW (23.7%). The gate is trained as a classifier of RW against WR, and any gate pays
  only if its acceptance rates satisfy π_RW·a_RW > π_WR·a_WR − (the token term, ≤ 0.5 utility points per 1k tokens saved), i.e.
  a_RW / a_WR > π_WR / π_RW = 2.5 on Qwen3-8B's dev queries. The untrained peer reaches 55.4% / 17.3% = 3.2 (hence its +0.5 points); the
  in-model gates, by round 16–27, kept 71–78% of right and 47–55% of wrong passing queries in training (ratio about 1.5 over all right
  and wrong; RW are mostly the convention cases above, invisible in the result). With no region above the ratio and no KL term, the
  logit runs to always defer, the Bayes response. Whether an earlier checkpoint had a profitable region: addendum 4 (CV-P10 / P11).
- *The generator.* Equation (3) with α = 1, β = 0 gives ∂A/∂p = 0 and ∂K/∂p = 0: once the gate defers everything, the quick query's
  correctness earns nothing, and only its own length (λk ≈ 0.0004) is left; a turn-1 DEFER saves the same λk. Predicted: CV's quick
  query stays at the base's accuracy and turn-1 DEFER never appears; measured 46.1% vs 46.0% (C1, rewarded for correctness alone:
  50.6%) and 0%. This is the learning-to-defer failure where the predictor gets no signal on deferred points: Mozannar & Sontag's
  consistent surrogate (2006.01862) trains the classifier on every point for that reason; Madras et al. (1711.06664) set up the joint
  problem; Mozannar et al. (2301.06197) show joint surrogates failing even when a zero-error pair exists. Gatekeeper (2502.19335) tunes
  the small model's confidence with a fixed trade-off weight instead of a joint value reward. New here: the collapse quantified by the
  ratio π_WR / π_RW, which the in-model gate does not reach and a peer does.

**Decision (by the rules above).** P1, P2, P5 refuted: training the quick mode for the cascade's value does not turn SQL's trade into
a saving; the claim does not change. The P4 and P7 rows read "a gate on frozen drafts is enough" and "training the gate is worth more
than a peer"; both presuppose a working gate, and here both trained gates are T→T, so neither reading holds: no trained arm does
anything T→T does not, and the untrained peer is +0.7 [−0.2, +1.5] above them. P5's row ("next, a decorrelated gate") is answered
by the peer (CV-P7, SQL-PA, SQL-DV): its ratio clears 2.5, but the accuracy any gate can add over T→T is at most π_RW = 4.2 points.

## Addendum 4 (2026-10-30 04:2x UTC, before any checkpoint row and before C1's agreement with the peer is computed)

Seen before writing this: the results above, and `python3.11 poc/analyze_cvpeer.py --predict` (C1's strata against SB→T→T; no
C1–peer agreement). Two questions, one offline and one on the GPU:

**(a) Plain RL's quick query with the peer check (offline).** C1 raised the quick query from 46.0% to 50.6% but loses to the default
(57.2 vs 58.6) because nothing gates its 37% wrong accepted queries; the peer is the gate that clears the ratio. Policy: C1's quick
query → check → Qwen3.5-9B's quick query (SQL-1's q35 rows, same seed) returns the same rows → C1's query, else SB→T→T (SQL-DV's
peer cascade with C1 in place of the base query). Theory (SQL-AND): against the default, accuracy changes by π_RW·a_RW − π_WR·a_WR.
C1's strata against SB→T→T are RR 44.1%, RW 6.6%, WR 8.3%, WW 21.1%, fail 20.0% (base: 41.5 / 4.5 / 11.0 / 23.5 / 19.5): RL moved
right answers onto the questions where the default fails and off those where it succeeds. With the base query's agreement rates
(RR 81.9%, RW 54.3%, WR 18.4%, WW 27.6%) the model predicts **+2.24 utility** over SB→T→T (accuracy +2.04, −0.39k tokens); the base
query's peer cascade: +0.62 (measured +0.6 [−0.3, +1.4], SQL-DV).
- **CV-P8:** utility C1's peer cascade − SB→T→T: paired lower bound > 0.
- **CV-P9:** utility C1's peer cascade − the base query's peer cascade: paired lower bound > 0.
- **CV-P8 theory:** the transferred prediction (+2.24) lies inside CV-P8's paired 95% interval.
- Reported: the peer at the next seed (s mod 3 + 1); T→T as the fallback; C1's measured agreement rates per stratum.
- Decision: P8 and P9 hold → plain RL on the quick mode with a decorrelated peer check beats the no-label default on SQL, where every
  untrained cascade tied: the claim changes (PROJECT §2, REPORT, PROPOSAL / PROPOSAL_ko: train the generator for correctness, take the
  check from outside the model). P8 refuted, P9 holds → RL helps the peer cascade, not significantly past the default; reported.
  P9 refuted → C1's gains fall where the peer cascade already did as well; reported. The theory row fails → the agreement rates do
  not transfer to a changed generator (C1's new right answers are ones the peer does not share); reported with the measured rates.
- `python3.11 poc/analyze_cvpeer.py` (written now).

**(b) C2's gate along training (GPU, 1 job).** Does any checkpoint have a profitable accept region, or is the collapse the Bayes
response throughout? C2's saved adapters r10, r20, …, r90 (`$POC_DATA/cv/c2/adapter_r<k>`), evaluated on dev seeds 1–3 exactly as
C2's final one (`poc/slurm/cv_eval_lane.sh c2 q8bcvc2r<k> <adapter> 1 2 3`; turn 1 = SQL-1's base query; τ = 0.5).
- **CV-P10:** for none of the nine checkpoints is utility − T→T's paired lower bound > 0.
- **CV-P11:** at every checkpoint that accepts ≥ 1% of passing queries, a_RW / a_WR < π_WR / π_RW (2.54, strata against T→T).
- Reported: per checkpoint the accept rate by stratum, utility against the peer gate, the frontier over τ.
- Decision: P10 and P11 hold → at no point of training does the in-model gate separate RW from WR at the ratio a gate needs; the
  collapse is the Bayes response to the shared blind spot, not an optimizer artefact, and the check must come from outside the model.
  P10 refuted → the collapse is runaway (no KL term, no stopping rule): a stopping rule chosen on training questions or a KL term
  makes the in-model gate a method; next, CV-2 with that fix, pre-registered then. P11 refuted with P10 holding → the gate separates
  RW from WR at some point but too little of it to show at this sample size; reported.
- `python3.11 poc/analyze_cvck.py` (written now).

Expected (stated now, not a rule): P8 holds narrowly (the peer shares fewer of C1's new right answers, which are harder questions),
P9 holds, the theory row holds; P10 and P11 hold (training ratio ≤ 1.5).
