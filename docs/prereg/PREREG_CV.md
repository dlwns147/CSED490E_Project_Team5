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
