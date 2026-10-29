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

## Note (2026-10-29 12:2x UTC, after writing `poc/analyze_cv.py`, before any CV row): what a perfect gate reaches

Checking `poc/analyze_cv.py` with an oracle gate on SQL-1's base queries (ACCEPT exactly the right ones; turn 2 counted as 1 token;
escalation T→T): 63.5% at 1.46k tokens, +4.2 [+3.4, +5.1] over T→T at 79% of its tokens (SQL-1's 19% failed checks and the 35%
wrong-but-passing queries escalate). So CV-P1's token bound (≤ 75% of T→T's tokens) cannot be met by a gate on unchanged drafts,
even a perfect one: it needs the quick query itself to fail less or defer earlier (fewer escalations after a wasted query does not
lower the bound; more right first queries does). The prediction is unchanged; C2 (a gate only) cannot satisfy P1 by construction.
