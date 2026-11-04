# Pre-registration MT: the free check at every step of an agent loop (multi-turn function calling)

Written 2026-10-31 12:2x UTC, before any main row (the two smokes below come first and are not part of the results). Results go below.

**Why it could change the claim.** The claim is "apply the free check at every step": a cheap answer, a check that costs nothing,
thinking only on a visible failure, and thinking again when the think's own answer visibly fails (HO-CM). Every task so far was
single-shot: one program, query or call per problem, checked once or twice. An agent loop is the setting the phrase describes literally:
many steps per task, each step's calls run in an environment that answers every one of them for free, and an error in step k changes
what step k+1 sees. Two things can happen that single-shot tasks could not show. (a) Thinking only after a visible failure keeps
always-thinking's accuracy at a fraction of its tokens: the recipe extends to agent loops. (b) It does not, because a wrong step that
runs without an error (a silent failure) poisons every later step and no later check recovers it: the boundary of the recipe is the
loop's silent failures, measured. The setting also asks a question the single-shot tasks could not: whether the model's own cheap
repair (a non-thinking step that sees the error, as every agent framework does by default) is as good as thinking after the error
(on word problems a cheap repair was not cheaper than thinking again, HO-TR).

**Theory (the stratified account, per item).** Arms differ only in which steps think. Split the cheap arm N's items by its outcome and
by whether its trajectory shows a visible failure — a call that returns an error, or a step that repeats the previous step's calls with
the same results (no progress): RV (right, with a visible failure), RS (right, silent), WV (wrong, visible), WS (wrong, silent). E thinks
only after a visible failure, so on RS / WS items E runs N's policy (with the same per-step seeds; outputs agree up to the
server's batch nondeterminism), and E − N lives on
RV / WV: + (share WV) × (rescue rate of a think after the failure) − (share RV) × (rate at which that think breaks a trajectory the
cheap repair would have finished). T − E lives mostly on WS: T can only beat E there by thinking at steps no check flags. So E reaches
T's accuracy when the visible share of N's failures is high and a think after the failure rescues as often as thinking throughout;
E's tokens are N's plus one think per visible failure. In the first smoke (Qwen3-14B-AWQ, 10 items) 4 of N's 7 failures ended in
no-progress loops at the 20-step limit and 2 more had errors before a silent final state; non-thinking steps cost ~15–25 tokens, a
think after an error 0.3–2.6k.

**Prior work (related-work check 2026-10-31 12 UTC; IDs opened).** Per-turn thinking budgets on BFCL v4 multi-turn: TAB (2604.05164,
a GRPO-trained Qwen3-4B budgeter sets each turn's budget for an L1-Qwen3-8B solver; up to 20% fewer tokens on agentic benchmarks; its
baselines are static budgets and LLM judges, not no-thinking, always-thinking or an error trigger). Reflection after a tool failure,
trained: Structured Reflection (2509.18847, BFCL v3 multi-turn), ReGRPO (2606.31392, a reflection trigger with a reflection-cost term;
GTA / GAIA). Step-level escalation to a stronger model: R2V-Agent (2605.16604, a trained process verifier flags risky steps),
TACIT-Switch (2608.27911); cascades cost more in agent loops because every step restarts from the cheap tier (2606.13241). In the
project: TC-1 (single-turn calls: thinking +3 to +17 points at 0.3k tokens; the schema check sees 9–25% of wrong answers), HO-TR, HO-CM.
**New here:** no training and no verifier — the environment's own answer (an error, or no progress) as the free check that switches
the same model's thinking on for one step, against never thinking, always thinking and thinking at each new request, with every
output token priced, on BFCL's multi-turn categories, with the silent-failure share measured.

**Run.** BFCL v4 (pip `bfcl-eval` 2026.3.23), categories multi_turn_base, multi_turn_miss_param, multi_turn_miss_func (600 items;
long_context left out: its states overflow a 3090's context), BFCL's prompt mode for open models (its default system prompt with the
involved classes' function docs; the held-out functions of miss_func arrive in BFCL's own user message at their turn), built with its
code (`poc/prep_mt.py` → `$POC_DATA/bfcl/mt_items.jsonl`). The loop (`poc/run_mt.py`) is BFCL's prompting loop: each step's answer is
decoded with BFCL's decoder (copied; identical to it on all 734 ground-truth turns), its calls run in BFCL's own environment classes
(`multi_turn_utils.execute_multi_turn_func_call`), each result returns as a tool message, the turn ends at an answer with no decodable
call, an item fails after 20 steps in a turn (BFCL's limit) or when the conversation outgrows the context. Graded by BFCL's own
`multi_turn_checker` (state and execution results after every turn; force-quit fails; `poc/grade_mt.py`; the ground truth replayed
as a trajectory passes 600 / 600). Arms (one run each; each is its own trajectory): **N** non-thinking every step (2,048-token cap);
**T** thinking every step (8,192-token cap); **E** non-thinking, thinking for the step after a visible failure of the previous step in
the same turn (an error result: BFCL's "Error during execution" or a JSON object with an "error" key; or a repeat of the previous step's
calls with the same results — added after the first smoke, where non-thinking loops ended 4 of 10 items); **F** thinking at the first
step of each turn (the new request), then as E. Sampling T 0.7, top-p 0.95 for every arm (the harness sampling; for Qwen3.5-9B the
card's general preset lowered tool-call thinks, SAMP); per-step seed fixed by (seed, item, turn, step), so N and E share every step
until E's first think. Models: Qwen3-14B-AWQ (one RTX 3090), Qwen3-8B (two RTX 3090s, tensor parallel, as LC-1: one 3090 holds too
little KV cache at 32k), Qwen3.5-9B (one 3090; `--language-model-only`); `--max-model-len 32768`; seeds 1–3; one job per model and
seed running N, E, F, T in that order. Utility per item = 100 × right − 0.5 × output ktokens of every step (the project's λ).

*Smokes (not part of the results; Qwen3-14B-AWQ, seed 1, tags q14asmoke / q14asmoke2). Job 1287665 (10 base items, then 30 items of
the three categories for F and T; cancelled at 19 / 30 T items once every arm had run) found the non-thinking loops and the first E
had only the error trigger; job 1287788 (30 items, N and E with the final check). Every request answered, no reply hit its cap, no
conversation outgrew 32k. On the 19 items every arm ran: N 5 / 19 right at 0.28k tokens per item, E 7 / 19 at 2.48k, F 7 / 19 at
3.07k, T 6 / 19 at 5.40k; 13 of N's 14 failures had a visible failure; thinking loops too (T: 7 of 19 items repeat a step). Fixed from
the smokes before any main row: the no-progress trigger, the overflow rule, the three categories (600 items), four clients per job
(6 items each) against one server.*

## Predictions (paired 95% intervals over items, seed means; utility as above; each needs ≥ 2 of 3 models)

- **MT-P1 (thinking pays in the loop):** T − N accuracy: lower bound > 0.
- **MT-P2 (the claim: check every step):** E − T utility: lower bound > 0.
- **MT-P3 (think after the failure, not the cheap repair):** E − N utility: lower bound > 0.
- **MT-P4 (think at each new request):** F − E utility: lower bound > 0.
- **MT-P5 (the mechanism):** of N's wrong items, the share with a visible failure ≥ 50%, and E − N accuracy on N's visible items >
  E − N on N's silent items (each model; pooled seeds; reported with intervals).
- Reported: every arm's accuracy @ tokens per category; BFCL's error types; think steps and tokens per item; the strata RV / RS / WV /
  WS of N with E's and T's accuracy in each; loops and errors per arm; T − E on N's silent items; raw trajectories of E's failures.

## Decision

- P2 holds → the recipe extends to agent loops: "the environment's answer is the free check at every step" goes into PROJECT /
  REPORT / PROPOSAL as the agent-loop row, with its tokens; the next step pre-registers the peer check per step for the silent
  failures (the stratified account says that is where T − E lives).
- P2 refuted, P3 holds → thinking after a visible failure beats the cheap repair but always thinking is better per token: the loop's
  silent failures are the boundary (reported with their share), as on tool calls (TC-1, a gain not a saving).
- P1 refuted → thinking does not pay in this loop; the recipe's default for agent loops is the cheap model with its own repair
  (reported; F and E judged against N only).
- P4 holds → the recipe thinks once per new request in agent loops (as the short think first on single-shot tasks).

Expected (not a rule, written after the smokes): T − N +3 to +10 accuracy points at 15–20 times N's tokens; E near T's accuracy at
about half its tokens, so P2 holds for one or two models and P3 for all three; P4 inconclusive; the visible share of N's failures
80–95% (the smokes: 13 / 14).

*Analysis (written 2026-10-31 12:3x UTC, tested on the smoke rows, before any main row was read): per model `/home1/leesangjun/venvs/bfcl/bin/python
poc/grade_mt.py <tag>`, then `python3.11 poc/analyze_mt.py > results/mt.txt` (MT-P1..P5 as above; items every arm has at every
seed). Main jobs 1287864–1287872 submitted 12:3x UTC.*

## Addendum (written 2026-10-31 13:5x UTC): input tokens — secondary analysis

**Why it could change the claim.** The primary utility prices output tokens only. In an agent loop every step sends the whole
conversation again, so the arms also differ in the input tokens they make the server read. In the smoke, replayed (below), the input
per item was 100–135k tokens against 0.3–5.4k output. N read the most (17.2 steps per item) and T the least (12.8). Counting every
token, T used fewer than N (105.6k against 135.2k on the 19 common items). If that holds on the main rows, "thinking costs tokens"
is wrong in agent loops for anyone who pays for input without a cache. The agent-loop row would then have to name its cost model.

**Theory.** Let S be the system prompt and c_k the history at step k, so step k's prompt is S + c_k. K steps then read
Σ_k (S + c_k) ≥ K·S input tokens, and the total grows quadratically in K because c_k grows with k (as in 2607.21503).

*Without a cache.* Suppose a think costs t output tokens and saves ΔK later steps whose mean prompt is p̄. It lowers the total
token count iff ΔK·p̄ > t. In the smoke p̄ ≈ 7.8k, so a 0.4–2.6k think pays if it saves 0.05–0.33 of a step.

*With a cache.* Price a cached input token at ρ_c and a new one at ρ, both in output-token units. A step then costs
ρ_c·p̄ + ρ·n̄, where n̄ ≈ 0.46k is the new input per step in the smoke. At ρ = 0.25 and ρ_c = 0.025 that is about 0.31k
output-equivalent tokens, so the same think pays only if it saves 1.3–8 steps.

So without a cache, thinking that ends loops lowers the cost. With a cache, output tokens carry the differences between arms, and
the primary verdicts should stand.

**Prior work (IDs opened 2026-10-31 13:5x UTC).**

| Paper | Relevance |
|---|---|
| Kapoor et al., "AI Agents That Matter" (2407.01502) | Agent evaluations should be cost-controlled, in dollars that include input |
| Cuadron et al. (2502.08235) | Reasoning models over-think in agentic tasks: fewer environment interactions, lower resolution. Here the opposite effect is asked: whether thinking ends loops |
| "How Do AI Agents Spend Your Money?" (2604.22750) | Cache reads are the largest cost of coding agents |
| 2607.21503 | Re-sending the history makes cumulative cost quadratic in the conversation length |
| 2608.22237 | Re-reading observations dominates agent token use |

None of these prices the free-check arms of one model against each other.

**Measure.** `poc/mt_cost.py replay <tag>` (grader venv) replays every trajectory: its calls run again in BFCL's environment
classes, and every step's prompt is counted with the Qwen3 chat template and tokenizer. The same unit is used for every model;
Qwen3.5-9B's own tokenizer is not on the login node. Two quantities are kept per step:
- P_k, the prompt;
- new_k = P_k − P_(k−1), the part a prefix cache over the previous request does not hold.

Answers are counted as follows:
- Non-thinking steps count their output tokens minus the stop token, which is exact.
- Thinking steps count the re-serialized calls. A thinking final text counts only its stored first 300 characters, so long final
  answers of thinking steps are undercounted. This undercount favours T and F by about 1–3% of input.

`poc/mt_cost.py report` gives every arm's input, new input and total, the tests below, and utilities at four price settings:

| ρ | ρ_c |
|---|---|
| 0.25 | 0.025 (cached) |
| 0.25 | 0.25 (no cache) |
| 0.1 | 0.01 (cached) |
| 0.5 | 0.05 (cached) |

Here ρ = 0.25 is a typical API ratio of input to output price, and ρ_c = ρ/10 is a typical cache-read discount. Tested on the smoke
rows: the replayed results matched the stored ones with 0 mismatches.

**Predictions (secondary).** Paired 95% intervals over items of seed means. Each prediction needs 2 of 3 models.
- **MT-S1:** T − N input tokens per item: upper bound < 0 (thinking shortens the loop).
- **MT-S2:** T − N input + output tokens per item: upper bound < 0. Counting every token, always thinking costs less than never
  thinking.
- **MT-S3:** E − T input tokens per item: lower bound > 0. The free check saves output tokens, and E re-reads more than T.
- **MT-S4:** with input priced at ρ = 0.25 and ρ_c = 0.025, the verdicts of MT-P2, MT-P3 and MT-P4 (lower bound > 0) are the same as
  under the primary utility, for all three tests of the model.

**Decision.**
- S2 holds: the agent-loop row reports both costs and states that, counting re-read input, thinking at every step costs fewer
  tokens than never thinking.
  - If S4 holds, the output-token verdicts stand for a reader with a prefix cache.
  - Either way, "fewest tokens" for agent loops is stated with its cost model. The claim's cost sentence changes in PROJECT and
    REPORT, and in PROPOSAL if the agent-loop row enters it.
- S2 refuted: output tokens stay the measure for agent loops, and input is reported.
- S4 refuted: the agent-loop verdict depends on the cost model, reported per model.

Expected (from the smoke; not a rule):
- S1 and S3 hold for all three models.
- S2 holds for 2 of 3, since T's ~5k extra output is set against a ~30k input saving.
- S4 holds.

*Disclosure.* This addendum was written after reading the q8b N main grades (13:4x UTC), which had finished for all three seeds:
- accuracy 16.7% at 0.50k output tokens and 15.8 steps per item;
- strata RV 10.3%, RS 6.4%, WV 71.1% and WS 12.2% of item-seeds, so 85% of N's wrong item-seeds show a visible failure;
- 36% of N's wrong item-seeds are force-quit at the 20-step limit.

No main E, F or T row had been graded or replayed. Simple free signals do not separate N's silent failures from its silent successes
(N rows only, exploratory):
- a "false" or "not found" status in a result: 11 of 220 WS against 10 of 115 RS;
- a turn ending in "[]" or empty text: 62 of 220 against 30 of 115.

The silent failures read so far are semantic: a wrong symbol, a missing tag prefix, a skipped last call. The main rows are replayed
on a CPU node when the runs finish, which takes about 10 minutes.

*Note (2026-10-31 15:1x UTC, infrastructure only):* the Qwen3-14B-AWQ and Qwen3.5-9B jobs were cancelled at 15:1x UTC after 2.5 h and resubmitted
on two GPUs each with tensor parallel 2, as Qwen3-8B (jobs 1288521–1288526). The reason was throughput:
- Qwen3-14B-AWQ's KV cache was 64k tokens and 83–99% full, with 31–41% prefix hits and 70–110 generated tokens/s.
- Qwen3.5-9B had 2.7 GiB of KV cache and 12% prefix hits; it ran 7 of 24 requests at 30–70 tokens/s.
- Their T arms were at 85 and 244 of 1,800 item-seeds.

Rows resume, and no row file had a torn last line. Items in flight were lost and rerun from their first step with the same per-step
seeds. Rows written on one GPU and on two may differ only as the server's batch nondeterminism already makes them differ. Nothing in
the analysis changes.

*Interim (written 2026-10-31 19:0x UTC; one model of three, no decision: every prediction needs 2 of 3 models).* Qwen3-8B, 600 items × 3
seeds, every row (`results/mt_q8b.txt`, `results/mt_cost_q8b.txt`): N 16.7% @ 0.50k output tokens, E 23.7% @ 3.62k, F 29.1% @ 5.21k,
T 30.8% @ 6.84k. MT-P1 T − N accuracy +14.17 [+11.00, +17.33] (holds); MT-P2 E − T utility −5.50 [−8.66, −2.29] (refuted, and E is
worse); MT-P3 E − N +5.50 [+3.43, +7.54] (holds); MT-P4 F − E +4.53 [+1.55, +7.41] (holds); MT-P5 holds (85.3% of N's wrong
item-seeds visible; E − N +8.33 on visible vs +1.49 on silent). Secondary: S1–S4 hold (T − N input −33.0k per item; input + output
−26.6k; E − T input +19.4k; the P2–P4 verdicts are the same with input priced, cached or not). Where E loses to T (N's strata,
item-seeds): on N's visible failures (WV, 1,280) E is right on 13.0% and T on 25.3%, on silent failures (WS, 220) 3.2% vs 24.5%,
while T breaks N's right trajectories more often (RS 115: E 98.3%, T 68.7%; RV 185: 76.2% vs 53.0%). Most of T − E comes from
visible failures, not from the silent ones the addendum expected: thinking after the environment reports an error recovers half as
often as thinking from the start.

*Infrastructure note (2026-10-31 19:0x UTC).* The six single-GPU jobs cancelled at 15:08 UTC (1287864/65/67/68/70/71) did not run job.sh's
cleanup: `scancel` ended the `docker exec` client, not the container, and one container (1287865, Qwen3.5-9B seed 1, node n27) kept
its server and four clients running outside Slurm until it was removed at 19:06 UTC (a job on that node, `docker rm -f`). Its rows
went into the same files as the resubmitted job 1288522 (done 17:37 UTC) from another node, and the NAS lost lines under the two
writers: Qwen3.5-9B seed 1 has 543–566 distinct items per arm (duplicates 72–138, torn lines 31–57; every other model-seed ≤ 4
duplicates and ≤ 1 torn line). Each surviving row is a complete trajectory under the same protocol and per-step seeds (the loader
keeps the last row of an item). The missing items are being rerun (job 1289417, rows resume). No other node held a container of the
cancelled jobs (checked on n20, n24, n25, n26, n27; n26 at 19:31 UTC).

## Results MT-P1..P5 (written 2026-10-31 20:0x UTC; Qwen3-8B and Qwen3.5-9B complete, every prediction is decided by them since each needs 2 of 3; Qwen3-14B-AWQ and S1–S3 follow)
`results/mt_q8b.txt`, `results/mt_q35.txt`, `results/mt_cost_q35.txt`; 600 items × 3 seeds per model, every row (Qwen3.5-9B seed 1
after the refill and the loader fix, infrastructure note above). Accuracy @ output tokens per item:

| model | N | E | F | T |
|---|---|---|---|---|
| Qwen3-8B | 16.7% @ 0.50k | 23.7% @ 3.62k | 29.1% @ 5.21k | 30.8% @ 6.84k |
| Qwen3.5-9B | 25.0% @ 0.43k | 29.5% @ 0.88k | 38.7% @ 1.73k | 38.0% @ 2.56k |

| test | Qwen3-8B | Qwen3.5-9B | verdict |
|---|---|---|---|
| MT-P1 T − N accuracy | +14.17 [+11.00, +17.33] | +13.00 [+10.00, +15.78] | **holds** |
| MT-P2 E − T utility | −5.50 [−8.66, −2.29] | −7.66 [−10.55, −4.63] | **refuted** (E is worse) |
| MT-P3 E − N utility | +5.50 [+3.43, +7.54] | +4.27 [+2.58, +6.03] | **holds** |
| MT-P4 F − E utility | +4.53 [+1.55, +7.41] | +8.74 [+6.05, +11.66] | **holds** |
| MT-P5 visible share of N's wrong; E − N visible vs silent | 85.3%; +8.33 vs +1.49 | 73.9%; +7.14 vs −1.03 (gap +8.17 [+5.23, +11.01]) | **holds** |

Reported: F − T (not pre-registered as a test) utility −0.96 [−3.52, +1.71] and +1.08 [−1.32, +3.30], at 76% and 68% of T's output
tokens. Where E loses to T, by N's strata (item-seeds × (T − E right)): Qwen3-8B visible failures WV +157, silent WS +47, N's right
trajectories RS −34 and RV −43; Qwen3.5-9B WV +127, WS +119, RS −48, RV −44. The addendum's expectation (T − E lives in the silent
failures) holds for Qwen3.5-9B only; for Qwen3-8B one thinking step after an error rarely repairs the turn (E right on 13.0% of WV,
T 25.3%). Turn-0 counterfactual of rolling the turn back and redoing it with thinking (exploratory, FINDINGS 10-31 19:3x): Qwen3-8B
68.6% @ 1.80k vs T 71.4% @ 2.09k; Qwen3.5-9B 70.5% @ 0.55k vs T 73.8% @ 0.81k and F 74.3% @ 0.55k: the rollback beats E and loses to
thinking from the first step in both. The checks pass wrong turns that thinking fixes (Qwen3.5-9B: 149 at turn 0 for the visible
failure, 172 for the peer).

**Decision (as pre-registered).** P2 refuted, P3 holds: thinking after a visible failure beats the cheap repair, but always thinking is
better per token. The agent-loop row reports this with its share of failures; its stated mechanism is corrected: the loss is on visible
and silent failures alike, because a turn repaired from a damaged state rarely recovers. P4 holds: in agent loops the recipe thinks
once per new request (F, the agent form of the short think first), which ties always thinking at 68–76% of its output tokens. P1 holds:
the cheap model with its own repair is not the default. No rollback arm is run (the FINDINGS rule: the turn-0 rollback loses to T for
both models). Goal link: for agent loops the fewest-token exact answer starts each request with thinking; the free check is a signal
to keep thinking, not to start.

## Results, Qwen3-14B-AWQ and the secondary predictions (written 2026-10-31 21:5x UTC; `results/mt_q14a.txt`, `results/mt_cost_q14a.txt`; 597 items with every arm at every seed)
Qwen3-14B-AWQ: N 12.1% @ 0.52k, E 17.0% @ 2.70k, F 21.9% @ 4.03k, T 31.0% @ 5.71k. MT-P1 +18.93 [+15.91, +22.11], MT-P2 −12.51
[−15.49, −9.66], MT-P3 +3.82 [+2.04, +5.65], MT-P4 +4.25 [+1.85, +6.80], MT-P5 86.8% visible, gap +6.23 [+3.97, +8.57]: the same
verdicts as the other two (P1, P3, P4, P5 hold in 3 / 3; P2 refuted in 3 / 3, E worse each time). Secondary: MT-S1 holds (T − N
input −43.8k per item; 2 of 3, Qwen3.5-9B refuted), MT-S2 holds (−38.6k; 2 / 3), MT-S3 holds (+41.1k; 2 / 3), MT-S4 holds (3 / 3).
Decision (as pre-registered, S2 holds): the agent-loop row states both costs; counting re-read input, thinking at every step costs
fewer tokens than never thinking for Qwen3-8B and Qwen3-14B-AWQ (not for Qwen3.5-9B, whose thinking does not shorten the loop), and
the output-token verdicts stand with a prefix cache (S4).

**Correction (same time).** The results above (20:0x UTC) added, as a reported comparison, that thinking once per new request (F)
"ties always thinking". For Qwen3-14B-AWQ it does not: F − T −8.11 [−10.68, −5.49] utility, −8.94 accuracy. The pre-registered P4
(F beats E) holds in 3 / 3; the statement that F is the agent-loop recipe is withdrawn. Among the fixed policies tested, always
thinking is the best or tied for every model, and no cheaper fixed rule matches it for all three; PROJECT §0 and REPORT §7 now say so.

## Addendum MT-B: is thinking at every step the information limit of a turn's signals? (written 2026-11-01 01:3x UTC, before the dump below exists)

**Why.** In agent loops every cheap-first rule lost to thinking at every step (P2 refuted 3 / 3; the rollback counterfactual lost for
all three models). Is that a property of the rules or of the signals? The SQL analysis (PREREG_LCM addendum B) answers the same
question with a planner that knows the joint law of the calls. At turn 0 every trajectory starts from the same state, so a turn's calls
are comparable: the quick turn (N), the peer's quick turn (Qwen3.5-9B; Qwen3-8B for Qwen3.5-9B), the thinking turn (T) and a second
thinking turn (T at the next seed), each with its end state (BFCL's instance comparison), its visible failure (an error or a repeat;
the free check) and whether it is right (BFCL's per-turn check). It assumes the environment can be reset to the turn's start (a
sandbox), as the rollback arm did. **Analysis.** `mt_peer0.py --dump` writes these four calls per item-seed; the supervised planner
(cross-fitted halves, all labels of the fitting half; end states as answers, "no visible failure" as the check; utility 100 × right −
0.5 × ktokens of turn 0) against always thinking at turn 0 (T), and the rules tested before.
**Prediction.** **MT-B1:** planner − T at turn 0: lower bound > 0 in ≥ 2 of the 3 models.
**Decision.** MT-B1 holds: there is room below always thinking that a derived per-turn policy could take (with a resettable
environment); its size is reported and it becomes the agent-loop method question. Refuted: at turn 0 thinking is at the information
limit of these signals, and "think at every step" is the agent-loop rule by that bound, not by habit.

### Results MT-B (written 2026-11-01 01:3x UTC; `results/mtb.txt`, `poc/analyze_mtb.py`; dumps `results/tc/mt_turn0_<tag>.json`)

| model (turn 0, 600 items × 3 seeds) | supervised planner | T | T→T | rollback | peer rule | planner − T |
|---|---|---|---|---|---|---|
| Qwen3-8B | 79.1% @ 2.96k | 71.4% @ 2.09k | 72.9% @ 3.43k | 68.6% @ 1.80k | 68.9% @ 1.68k | +7.18 [+5.19, +9.24] |
| Qwen3-14B-AWQ | 79.3% @ 3.10k | 71.0% @ 1.99k | 72.1% @ 3.33k | 64.0% @ 1.97k | 60.3% @ 1.58k | +7.81 [+5.81, +9.99] |
| Qwen3.5-9B | 82.1% @ 1.33k | 73.8% @ 0.81k | 74.7% @ 1.03k | 70.5% @ 0.54k | 69.4% @ 0.77k | +8.02 [+6.14, +9.90] |

- **MT-B1 holds** (3 of 3). What the planner does: it runs the quick turn and the peer's quick turn first and commits when their end
  states agree (Qwen3-8B: 41% of item-seeds stop there with the quick turn's state); otherwise it adds one or two thinking turns and
  commits the end state the calls share (e.g. "N P T2 → the state N and T2 share"). The gain is a vote over end states of turns run
  from the same start, not one better think (T→T gains only +0.5 to +0.8).
**Decision (as pre-registered).** There is room below always thinking (+7 to +8 utility at turn 0, more accurate at 1.4–1.6× the
output tokens of one think), for a per-turn policy that runs turns in a resettable copy of the environment and commits the end state
the calls agree on. That becomes the agent-loop method question; it is pre-registered as an online arm (every turn, not only the first)
before it is run.

## Addendum MT-V: the per-turn vote online (written 2026-11-01 02:0x UTC, after a 6-item smoke, before any main row)

**Method (arm V, `poc/run_mt.py`).** At every turn, rollouts of the quick turn (N), the peer's quick turn (P, another model's server),
the thinking turn (T) and a second thinking turn (T at the next seed) on sandbox copies of the committed environment (deep copies of
BFCL's instances), made and committed as MT-B's supervised planner says: the policy is solved on the turn-0 dumps of one half of the
items (`poc/mt_policy.py`, all their turn-0 labels) and applied to the items of the other half, at every turn (patterns the fitting
half never showed: the always-think baseline). The committed rollout's steps and environment continue the conversation; the row is
graded as any arm's (BFCL's per-turn state and response checks). Costs: every rollout's output tokens; input tokens reported (each
rollout re-reads the context, mostly a shared prefix). Assumes a resettable environment and a second resident model (two GPUs).
**Smoke (seed 1, 6 items, not part of the results):** every item ran; the policy committed the quick or the peer's turn on 19 of 21
turns; output tokens 24.6k per item against T's 10.2k on the same items (the policy was fitted on turn 0, where contexts are short).
**Run.** Qwen3-8B (peer Qwen3.5-9B) and Qwen3.5-9B (peer Qwen3-8B), all 600 items, seeds 1–3, one two-GPU job per model and seed
(`poc/slurm/vote_lane.sh`, 24 clients); compared with the stored T arm (same items, seeds and step seeds).
**Predictions (paired 95% intervals over items, seed means).**
- **MT-V1:** V − T utility (output tokens): lower bound > 0 for both models.
- **MT-V2:** V − T accuracy: lower bound > 0 for both models.
- Reported: tokens (output; input with ρ = 0.25 cached / not cached as MT-S); the share of turns committed without thinking; the
  fallback rate; per-category accuracy.
**Decision.** V1 holds for both: the agent-loop method becomes the per-turn vote over sandboxed rollouts with the derived policy
(PROJECT, REPORT). V2 holds but V1 not: a trade, reported with its break-even λ. V2 refuted: the turn-0 room does not carry into whole
trajectories; reported.

*MT-V secondary (written 2026-11-01 02:3x UTC, before it is computed): how many labelled items the vote policy needs, offline at turn 0.* The
supervised planner of MT-B fitted on k labelled items of the fitting half (k = 10, 30, 100, all ≈ 300; 5 random draws each, seeds
reported) and evaluated cross-fitted on the other half against always thinking (T). Reported, no rule; it says whether MT-V's policy
(fitted on ≈ 300 items' turn-0 labels) could be bought with a pilot of the size used elsewhere in the project (30).

*MT-V secondary, result (written 2026-11-01 02:3x UTC; `results/mtv_labels.txt`).* Turn-0 vote policy − always thinking, mean over 5 draws of the
labelled items: k = 10: +1.97 / +2.44 / +2.60 (Qwen3-8B / Qwen3-14B-AWQ / Qwen3.5-9B; 4 of 15 draws with a lower bound > 0); k = 30:
+4.76 / +5.15 / +5.53 (15 of 15 draws > 0); k = 100: +5.61 / +6.75 / +6.60; all ≈ 300: +7.18 / +7.81 / +8.02. A 30-item pilot buys
about two thirds of the gain; the policy is cheap in labels because the patterns it acts on (do the quick and the peer's end states
agree; which thinking rollouts share a state) are few and frequent.

## Results of addendum MT-V, and a correction to MT-B (written 2026-11-01 14:4x UTC; `results/mtv.txt`, `poc/analyze_mtv.py`; all 600 items × seeds 1–3 for both models; post-mortem `nlp_data/scratch/mtb_relabel.py`)

| model (peer) | V | T | V − T utility | V − T accuracy | quick rollout committed | turns with no thinking rollout | rollouts per turn |
|---|---|---|---|---|---|---|---|
| Qwen3-8B (Qwen3.5-9B) | 29.1% @ 8.89k | 30.8% @ 6.84k | −2.80 [−5.66, +0.25] | −1.78 [−4.61, +1.33] | 92.9% | 27.3% | 2.59 |
| Qwen3.5-9B (Qwen3-8B) | 35.2% @ 3.47k | 38.0% @ 2.56k | −3.24 [−5.96, −0.61] | −2.78 [−5.50, −0.17] | 90.0% | 2.0% | 2.71 |

- **MT-V1 refuted** (0 of 2), **MT-V2 refuted** (0 of 2). Per category, V − T accuracy: Qwen3-8B base −3.1, missing function +0.7,
  missing parameter −2.9; Qwen3.5-9B base −5.5, missing function −2.8, missing parameter 0.0. V costs 1.30× / 1.36× T's output tokens.
- The first printing of `analyze_mtv.py` called the share of turns whose committed rollout is the quick or the peer's "turns committed
  without thinking"; most of those turns also ran a thinking rollout (the vote commits the first rollout of the winning end state).
  Fixed: both shares are printed (table).
- **Why the turn-0 room did not carry: it was not there.** MT-B grouped calls by end state and counted a group right when *any* of
  its calls was right (`lcm_bound.full`, written for SQL and single-turn calls, where rightness is a function of the answer: 0 mixed
  groups in 37,633 checked on BIRD dev, Spider test, the fresh BIRD-train questions and BFCL live / non-live). In BFCL multi-turn it is not: the grader also checks each turn's
  execution responses and empty turns, and two rollouts that end in the same state (a read-only call changes no state) can be right
  and wrong. At turn 0, 22.4% / 29.3% / 23.8% of item-seeds (Qwen3-8B / Qwen3-14B-AWQ / Qwen3.5-9B) have an end state shared by a
  right and a wrong call (14–20% of same-state call pairs). Online, V commits one rollout of the group, the first in call order.
  Refitting and scoring MT-B's planner with the committed rollout's own label: planner − T at turn 0 −0.62 [−3.43, +2.38] / −9.43
  [−12.47, −6.21] / −3.88 [−6.10, −1.67] (was +7.18 / +7.81 / +8.02); with a group right only if all its calls are, −13 to −18.
  **MT-B1, correctly measured, is refuted (0 of 3)**, and by MT-B's own rule: at turn 0 thinking is at the information limit of these
  signals, and "think at every step" is the agent-loop rule by that bound. MT-V's online loss is the same fact over whole trajectories.
- **Decision (as pre-registered, V2 refuted):** reported; the agent-loop method stays "think at every step". The MT-V secondary
  (labels needed by the vote policy) was computed with the same grouping and is withdrawn.

## Addendum MT-SEL: a trained verifier as the turn's missing signal (written 2026-11-03 12:4x UTC, before any verifier is trained or any rollout is scored; the analysis was run only on random scores, where T reproduces MT-B's turn-0 row)

**Why.** Agent loops are the one task where the method still loses: every cheap-first rule lost to thinking at every step (MT-P2,
MT-V), and MT-B, correctly measured, put thinking at the information limit of the free signals (visible failure, agreement of end
states). On SQL and single tool calls the step that beat that limit was a verifier trained on the task's labels, choosing among the
answers already made (SEL, SEL-TC2-AB). The room at turn 0, with each rollout graded on its own (`mt_sel_rows.jsonl`, labels equal
to MT-B's dumps for 21,488 of the 21,492 (role, item-seed) pairs): an oracle choosing among N, the peer's N and T gains +14.1 / +14.1 / +14.3 utility over T
(Qwen3-8B / Qwen3-14B-AWQ / Qwen3.5-9B); a perfect gate on N alone gains +6.5 / +5.1 / +9.2. A binormal simulation of the choice among
N, P, T puts the gain at +5.6 / +4.0 / +5.9 for a within-set AUROC of 0.80 and +7.9 / +6.7 / +8.4 at 0.85; the gate at 0.85 gains only
+2.0 / +0.7 / +3.5 (`nlp_data/scratch`, this session's notes). So the choice, not the gate, is the arm with room.

**Related work.** Step-level escalation with a trained process verifier (R2V-Agent, 2605.16604); a process reward model for function
calls guiding beam search (ToolPRM, ACL 2026; BFCL single-turn); per-turn thinking budgets on BFCL multi-turn (TAB, 2604.05164). New
here: an outcome verifier on whole turn rollouts (calls and their results) choosing among the same model's quick turn, another model's
quick turn and its thinking turn, every output token priced, against thinking at every step.

**Run.**
1. `mt_peer0.py --sel-build`: the turn-0 rollouts of arms N, E, F, T of the three models, seeds 1–3, each graded on its own (BFCL's
   per-turn check from the turn's start), rendered as the verifier reads them (`render`: each step's calls and results, results cut at
   300 characters, at most 12 steps and 3,000 characters). 597 items, 15,529 distinct rollouts. The system prompt keeps the json docs of
   only the functions the item's rollouts call, then the other functions' names.
2. Two verifiers, cross-fitted by scenario: half = crc32 of the scenario index mod 2 (an item's three categories share a scenario);
   292 / 305 items, 270 / 255 with a right and a wrong rollout. `SEL_IDS=$POC_DATA/bfcl/mt_sel_ids_h<h>.txt tc_train.py
   $POC_DATA/cv/mtsel_h<h> --orm --mt --batch 8 --epochs 4` (SEL-TC's pairwise loss within a request, Qwen3-8B LoRA r 16, lr 5e-5, at
   most 8 rollouts per request per step); the final adapter, no checkpoint choice. Each scores the other half's rollouts
   (`cv_eval_lane.sh score-tc ... sel_req_mt_h<1-h>.jsonl mt`).
3. Reference: selab2_s450 (the single-turn ToolACE verifier, trained on neither half) scores every rollout.
4. `python3.11 poc/analyze_mtb.py --sel mtsel_h0,mtsel_h1 --ref selab2_s450` > results/mtsel.txt.

Arms at turn 0, per model:
- **SEL3:** run N, the peer's N and T, then choose by `sel_fit_cl` (log prior by the roles that produced the rollout + β_CL z).
- **SEL4:** SEL3 plus the next seed's T.
- **GATE:** run N; keep it when its score clears τ, otherwise run T.
- **T:** think, the method.

The selector and τ are fitted per model on one half, with scores from the verifier that did not train on it, and applied to the other
half. Every rollout's output tokens are counted. This assumes, as MT-V did, a resettable environment and a second resident model.

**Predictions** (paired 95% intervals over items, seed means; utility 100 × right − 0.5 × output ktokens of turn 0):
- **MT-SEL-P1 (decision):** SEL3 − T lower bound > 0 in ≥ 2 of 3 models.
- **MT-SEL-P2 (the signal):** within-set AUROC of the trained verifiers on SEL3's sets ≥ 0.75 in ≥ 2 of 3 models.
- **MT-SEL-P3:** GATE − T lower bound > 0 in ≥ 2 of 3 models.
- **MT-SEL-P4 (in-domain labels matter):** SEL3 with the trained verifiers − SEL3 with selab2_s450, lower bound > 0 in ≥ 2 of 3.
- **Expected:**
  - AUROC 0.70–0.85: 270 training scenarios is a small pool next to SEL-TC's 4,684 requests, but BFCL's conventions are the
    training data's own.
  - SEL3 − T +2 to +6; GATE − T 0 to +2.
  - selab2_s450 AUROC 0.6–0.7: it never saw a multi-step turn or an environment result.

**Decision.**
- **P1 holds** → the online arm is pre-registered next: at every turn, sandboxed rollouts N, P, T with the verifier choosing, run on
  MT-V's infrastructure, with the verifier retrained on turn-0 and later-turn rollouts.
- **P1 refuted** → the agent-loop method stays "think at every step". The claim adds that a verifier trained on the benchmark's own
  scenario-held-out labels did not find a signal beyond MT-B's limit.

### Results MT-SEL (written 2026-11-03 15:1x UTC; `results/mtsel.txt`; raw cases `nlp_data/scratch/mtsel_raw.py`)

Both verifiers trained to the final step (136 / 128 steps; training pair accuracy 0.94–1.0 in the last epoch), each scored all of the
other half's rollouts (7,840 / 7,689, none missing); selab2_s450 scored all 15,529.

| model (peer) | T | N | SEL3 | SEL4 | GATE | SEL3 with selab2_s450 | within-set AUROC | SEL3 − T | GATE − T | SEL3 trained − selab2_s450 |
|---|---|---|---|---|---|---|---|---|---|---|
| Qwen3-8B (Qwen3.5-9B) | 71.5% @ 2.09k | 57.5% @ 0.24k | 77.6% @ 2.48k | 78.7% @ 4.57k | 72.3% @ 1.98k | 74.4% | 0.838 [0.811, 0.865] | +5.89 [+3.62, +8.24] | +0.84 [−0.62, +2.27] | +3.18 [+1.56, +4.80] |
| Qwen3-14B-AWQ (Qwen3.5-9B) | 71.0% @ 1.99k | 40.6% @ 0.31k | 80.0% @ 2.44k | 81.5% @ 4.43k | 72.6% @ 2.06k | 75.0% | 0.912 [0.893, 0.930] | +8.77 [+6.66, +10.89] | +1.59 [+0.73, +2.50] | +4.91 [+3.29, +6.48] |
| Qwen3.5-9B (Qwen3-8B) | 73.9% @ 0.81k | 62.3% @ 0.14k | 79.7% @ 1.19k | 81.7% @ 2.00k | 75.7% @ 0.70k | 75.0% | 0.842 [0.816, 0.869] | +5.61 [+3.65, +7.59] | +1.84 [+0.56, +3.18] | +4.63 [+2.90, +6.37] |

- **MT-SEL-P1 holds** (3 of 3), **P2 holds** (0.838 / 0.912 / 0.842), **P3 holds** (2 of 3), **P4 holds** (3 of 3). SEL4 − T +5.96 /
  +9.33 / +7.28 at about twice SEL3's tokens. The score alone − the fitted selector −0.34 / −0.11 / −0.34 (n.s.); β_CL 1.1–2.3.
- Above the expected range: AUROC 0.84–0.91 (expected 0.70–0.85), SEL3 − T +5.6 to +8.8 (expected +2 to +6), and selab2_s450, which
  never saw a multi-step turn, already gains (its SEL3 74.4 / 75.0 / 75.0% against T's 71.5 / 71.0 / 73.9%).
- The gain is in every category (SEL3 − T accuracy, base / missing function / missing parameter): Qwen3-8B +4.7 / +7.5 / +6.1,
  Qwen3-14B-AWQ +10.9 / +8.0 / +8.1, Qwen3.5-9B +7.5 / +3.8 / +6.1.
- Where it comes from: of the item-seeds where the choice is right and T wrong (179 / 196 / 167), the chosen rollout is the peer's
  quick turn in 123 / 166 / 78 and the model's own quick turn in the rest; the reverse (T right, the choice wrong) 70 / 35 / 63. For
  Qwen3-14B-AWQ, whose own quick turn is weak (40.6%), the choice is mostly Qwen3.5-9B's quick turn.
- Raw: the verifier reads the results. It prefers a quick turn that recovered from an error and finished the request (zip codes looked
  up after "distance not found", then the distance) over a thinking turn that gave up ("Rivermist does not appear to be a valid
  city"), and a quick turn that placed the order at the looked-up price over a thinking turn that kept re-querying the order. Losses:
  a quick turn that also set navigation the user said not to set when unreachable (one extra call), "Reply: []" scored above a
  thinking turn that listed the files, and quick turns that over-ran (extra `cd`/`cat` steps) where thinking stopped.
- Caveat: halves are split by scenario; BFCL reuses environments (the file system, the vehicle, trading, messaging) across
  scenarios, so the verifier has seen other requests on the same environments. That is the deployment the method assumes (labels
  from the environment it acts in), not a held-out-environment claim.

**Decision (as registered, P1 holds):** the online arm is pre-registered next — at every turn, sandboxed rollouts N, P, T with the
verifier choosing, on MT-V's infrastructure, the verifier retrained on turn-0 and later-turn rollouts. Turn 0 alone does not change
the agent-loop method: MT-V showed turn-0 room that did not carry into whole trajectories, so the claim waits for the online arm.

## Addendum MT-SO: the verifier's choice at every turn, online (written 2026-11-03 15:2x UTC, before the retrained verifiers exist and before any online row)

**Why.** MT-SEL's choice among N, P and T beats thinking at turn 0 (+5.6 to +8.8 utility). MT-V had turn-0 room too and lost over whole
conversations, because its room was a grouping artifact. Here the turn-0 room is measured with each rollout's own label, but later
turns differ: the context is longer, the state is the committed one, and the verifier never saw a later turn. MT-SEL's decision
registered this arm.

**Related work.** Reward-model best-of-N for tool calls, including multi-turn BFCL (ToolRM, 2510.26167); process verifiers for
tool-using agents (2601.12294; ToolPRM, ACL 2026); per-turn thinking budgets on BFCL multi-turn (TAB, 2604.05164). New here: at every
turn, a choice among the same model's quick turn, another model's quick turn and the thinking turn, all output tokens priced, against
thinking at every step, with the verifier and the choice rule cross-fitted by scenario.

**Data (built 2026-11-03 15:2x UTC, `mt_peer0.py --sel-build2`).**
- Each stored trajectory (3 models × arms N, E, F, T × seeds 1–3) is graded turn by turn (`turn_track`, BFCL's per-turn checks).
  A turn whose ground truth is empty must leave the state unchanged, as MT-SEL's turn-0 labels; BFCL checks that only at the next
  turn's state, so for 367 of 21,492 trajectories (1.7%, all in the missing-function / missing-parameter categories) this is stricter
  than BFCL's grade (a guess at the empty turn that BFCL passes later); no trajectory is right here and wrong in BFCL.
- At turn k ≥ 1, the trajectories still right through turn k−1 (the ground truth's state) give rollouts of turn k, right when the
  trajectory is still right after it. The verifier's request: the earlier requests, then the current one (`turn_context`).
- Requests with a right and a wrong rollout, turn 0 / later: 525 / 978 (half 0: 270 / 494; half 1: 255 / 484).
- Pseudo-sets for later turns: per model and seed, N, the peer's N and T at turn k when those three trajectories are all still right
  through k−1 (3,719 over the three models). They come from different histories, so they are the online choice's sets only
  approximately.

**Run.**
1. Two verifiers `mtso_h<h>`: `MT_SEL_TAG=mt_sel2 SEL_IDS=$POC_DATA/bfcl/mt_sel2_ids_h<h>.txt tc_train.py $POC_DATA/cv/mtso_h<h> --orm
   --mt --batch 8 --epochs 4` (MT-SEL's recipe, final adapter). Each scores the other half's texts (`sel_req_mt2_h<1-h>.jsonl`, sset mt2).
2. Secondary: MT-SEL's turn-0 verifiers `mtsel_h<h>` score the same texts (does training on later turns matter?).
3. `python3.11 poc/analyze_mtb.py --sel2 mtso_h0,mtso_h1 --ref mtsel_h0,mtsel_h1`:
   - offline SEL3 − T per turn (0, 1, 2, ≥ 3) on the pseudo-sets;
   - writes the choice rule `results/tc/mt_so_fit_<model>.json`. For each test half it holds the set-choice fit (`sel_fit_cl`: log
     prior by roles + β_CL z) on the other half's turn-0 sets and later pseudo-sets, pooled, with the scores of the verifier not
     trained on that half.
4. Online arm S (`run_mt.py <tag> S <seed>`), at every turn:
   - rollouts N (quick, the generator), P (quick, the peer) and T (thinking, the generator) on sandbox copies of the committed
     environment, with MT-V's seeds and caps;
   - the verifier trained on the other half of the scenarios scores each distinct rollout (`render`, `turn_context`; system prompt:
     the json docs of the functions the three rollouts call, `short_system`), and the item half's fit chooses;
   - a structure the fit never saw commits T; the chosen rollout's steps and environment continue the conversation.

   Every rollout's output tokens count; the verifier's prefill is reported.
5. Qwen3-8B (peer Qwen3.5-9B) and Qwen3.5-9B (peer Qwen3-8B), all 600 items, seeds 1–3, one two-GPU job per model and seed
   (`vote_lane.sh`; the verifiers are LoRA adapters on the Qwen3-8B server). `grade_mt.py <tag> S`, then compared with the stored T arm
   (same items, seeds and step seeds): `MTV_ARM=S python3.11 poc/analyze_mtv.py q8b q35`.

**Predictions** (paired 95% intervals over items, seed means; utility 100 × right − 0.5 × output ktokens of the whole conversation):
- **MT-SO-P1 (decision):** S − T utility lower bound > 0 for both models.
- **MT-SO-P2:** S − T accuracy lower bound > 0 for both models.
- **MT-SO-P3 (later turns, offline):** on the later-turn pseudo-sets (turns ≥ 1, the three models pooled), SEL3 − T lower bound > 0.
- **MT-SO-P4 (secondary):** on the same sets, SEL3 with `mtso` − SEL3 with `mtsel` lower bound > 0 (training on later turns matters).
- **Expected:** S − T accuracy +5 to +12. If each turn's success given a right start rises from about 0.75 to 0.81, about four turns
  compound that to about +10 accuracy. The tokens cost 1.2–1.5× T's (about −1 utility), so utility +3 to +10. P3 holds with a smaller
  gain than turn 0's. P4 is uncertain: MT-SEL's verifiers already read results, and the later-turn context is new to them.

**Decision.**
- **P1 holds for both** → the agent-loop method becomes the verifier's choice among the quick, the peer's quick and the thinking turn
  at every turn (PROJECT, REPORT, PROPOSAL); next, whether the peer and the quick turn can be skipped when the verifier is sure (a
  gate, MT-SEL's P3).
- **P2 holds, P1 not** → a trade, reported with its break-even λ.
- **Both refuted** → the turn-0 gain does not carry, reported with the per-turn diagnostics (where the choice goes wrong); the method
  stays thinking at every step.

### Note MT-SO, reference arm first (2026-11-03 16:2x UTC)
The `mtsel_l` job finished (MT-SEL's verifiers scored all 42,079 later-turn texts, 0 failed), so the analysis was run once with
those verifiers in the SEL3 slot (`--sel2 mtsel_h0,mtsel_h1`; the fit files it wrote were moved aside, the registered run rewrites
them). Turn 0 reproduces MT-SEL (+5.84 / +8.99 / +5.39). On the later-turn pseudo-sets, the turn-0 verifiers already gain:
pooled **+3.44 [+1.05, +5.83]** (P3's test, here for the reference verifiers). Per model, turn 1 / 2 / 3+:

| | turn 1 | turn 2 | turn 3+ |
|---|---|---|---|
| Qwen3-8B: T acc, SEL3 acc, AUROC, SEL3 − T | 81.3%, 84.0%, 0.774, +2.83 [+0.06, +5.80] | 85.4%, 87.9%, 0.802, +3.57 [−0.64, +7.69] | 77.7%, 79.5%, 0.718, +0.20 [−5.76, +5.87] |
| Qwen3-14B-AWQ | 77.4%, 80.9%, 0.764, +4.72 [+0.69, +8.62] | 82.3%, 85.1%, 0.756, +2.86 [−1.43, +7.43] | 80.5%, 81.4%, 0.687, +6.11 [+0.09, +12.87] |
| Qwen3.5-9B | 84.5%, 86.7%, 0.813, +2.81 [+0.02, +5.67] | 85.8%, 85.8%, 0.698, −0.89 [−3.82, +1.66] | 81.3%, 83.2%, 0.739, +0.95 [−5.83, +7.82] |

Reading: AUROC falls from 0.84–0.91 at turn 0 to 0.69–0.81 later, and T is more often right later (77–86%), so there is less to
win. P3 holding for `mtso` will therefore not show that later-turn training matters; P4 (`mtso` − `mtsel` on these sets) does.
Predictions unchanged.

## Addendum MT-SEL-ENV: does the turn-0 choice hold in environments the verifier never saw? (written 2026-11-03 17:3x UTC, before any environment-split verifier is trained)

**Why.** MT-SEL's halves are split by scenario, and both halves use the same eight BFCL environments. A verifier could have learned
what a right file-system or trading turn looks like. This is the caveat recorded under MT-SEL. Any claim for agent loops needs the gain
to survive in unseen environments. It also tells us whether MT-SO, if it holds, needs a separate environment-held-out run.

**Split (computed, not chosen).** Each item uses one or two of the eight classes. Of the 127 two-group partitions of the classes
(GorillaFileSystem fixed in group 0), take the one that maximises the smaller group's count of items using only that group's classes:

| Group | Classes | Items |
|---|---|---|
| 0 | GorillaFileSystem, MathAPI, TwitterAPI, VehicleControlAPI | 228 |
| 1 | MessageAPI, TicketAPI, TradingBot, TravelAPI | 240 |

The 132 items that use both groups are dropped from training and test.

**Run.**
1. `python3.11 poc/analyze_mtb.py --sel-env-build` writes:
   - the group item lists `$POC_DATA/bfcl/mt_selenv_ids_h{0,1}.txt`;
   - the turn-0 request files `results/conf/sel_req_mtenv_h{0,1}.jsonl`, which are MT-SEL's requests restricted to each group.
2. Jobs `mtenv_h<g>`:
   - train with MT-SEL's recipe on group g's items only: `SEL_IDS=mt_selenv_ids_h<g>.txt tc_train.py $POC_DATA/cv/mtenv_h<g> --orm --mt
     --batch 8 --epochs 4 --save 1000`;
   - then score the other group's requests: `cv_eval_lane.sh score-tc ... mtenv_h<g> sel_req_mtenv_h<1-g>.jsonl mt`.
3. `MT_SEL_SPLIT=same python3.11 poc/analyze_mtb.py --sel mtsel_h0,mtsel_h1` gives MT-SEL's scenario split on the same 468 items, for
   comparison.
4. `MT_SEL_SPLIT=env python3.11 poc/analyze_mtb.py --sel mtenv_h0,mtenv_h1` gives the environment split. Verifier, selector fit
   (SEL-CL) and gate threshold all come from the other environment group. Output goes to `results/mtselenv.txt`.

**Predictions** (turn 0, three models, utility as MT-SEL, items × 3 seeds, 95% intervals over items):
- **MT-SEL-ENV-P1 (decision):** SEL3 − T lower bound > 0 in ≥ 2 of 3 models.
- **MT-SEL-ENV-P2:** within-set AUROC ≥ 0.75 in ≥ 2 of 3 models.
- **MT-SEL-ENV-P3 (cost of unseen environments):** on the same items, SEL3 with the environment split minus SEL3 with the scenario
  split, pooled over the three models. Reported with its interval.
- **Expected.**
  - AUROC 0.75–0.82, against MT-SEL's 0.84–0.91.
  - SEL3 − T +2 to +5.
  - P3 between −1 and −3.
  - Confound: each environment verifier trains on 228–240 items, against about 300 for each scenario half. A loss in P3 mixes unseen
    environments with less data.

**Decision.**
- **P1 holds** → MT-SEL's gain is not environment memorisation. If MT-SO holds, it gets an environment-held-out online run with these
  verifiers.
- **P1 refuted** → a size-matched scenario control tells less data from unseen environments: scenario verifiers trained on random
  228 / 240-item subsets. If the control keeps the gain, the agent-loop claim is scoped to "trained on the target environments", and
  new environments become the required test.

## Results of addendum MT-SEL-ENV (written 2026-11-03 19:2x UTC; `results/mtselenv.txt`, scenario split on the same items `results/mtselenv_same.txt`; jobs 1310879 / 1310880: 108 / 96 training steps, 6,017 / 6,056 turn-0 texts scored, none failed)

467 env-pure items (228 group 0, 239 group 1 with turn-0 sets) × 3 seeds; verifier, set-choice fit and gate threshold from the other
group.

| model | T | SEL3 env split | SEL3 − T env split | AUROC env | SEL3 − T scenario split (same items) | AUROC scenario | GATE − T env / scenario |
|---|---|---|---|---|---|---|---|
| Qwen3-8B | 72.7% @ 2.10k | 76.2% @ 2.45k | +3.40 [+1.41, +5.45] | 0.785 | +4.68 [+2.26, +7.24] | 0.841 | −4.06 / +0.78 |
| Qwen3-14B-AWQ | 72.1% @ 1.98k | 76.2% @ 2.41k | +3.86 [+1.36, +6.22] | 0.841 | +8.21 [+5.93, +10.57] | 0.911 | −11.32 / +1.39 |
| Qwen3.5-9B | 75.4% @ 0.80k | 78.6% @ 1.14k | +2.97 [+0.32, +5.47] | 0.808 | +4.97 [+2.75, +7.18] | 0.843 | −5.19 / +1.44 |

- **MT-SEL-ENV-P1 holds:** SEL3 − T lower bound > 0 in 3 of 3 models.
- **MT-SEL-ENV-P2 holds:** within-set AUROC 0.785 / 0.841 / 0.808, ≥ 0.75 in 3 of 3.
- **MT-SEL-ENV-P3:** environment split − scenario split, SEL3, pooled −2.55 [−3.62, −1.40], within the expected −1 to −3. It mixes
  unseen environments with 228–239 training items instead of about 300.
- Every prediction's expected range held, except Qwen3-14B-AWQ's AUROC (0.841, above 0.82).
- Reported: the gate does not transfer. Its threshold, fitted on the other group, loses −4 to −11 against thinking, against +0.8 to
  +1.4 with the scenario split. The fitted set choice (SEL-CL) holds its edge over the score alone (−0.57 / −0.93 / −1.21 for the
  score alone).

**Decision (registered):** MT-SEL's turn-0 gain is not environment memorisation. In environments the verifier never saw it keeps
about half of the scenario-split gain, +3.0 to +3.9 against thinking. If MT-SO holds, it gets an environment-held-out online run with
these verifiers. SIDE-ENV (PREREG_SIDE) is the test beyond BFCL's own classes.

## Results of addendum MT-SO, offline part (written 2026-11-03 20:1x UTC; `results/mtso_offline.txt`; jobs 1310314 / 1310315: 384 / 372 training steps, 21,363 / 20,716 texts scored, none failed; the fits `results/tc/mt_so_fit_{q8b,q14a,q35}.json`, β_CL 1.2–2.9)

SEL3 − T on the pseudo-sets, per turn (mtso = verifiers trained with later turns; ref = MT-SEL's turn-0 verifiers; AUROC within set):

| model | turn 0 | turn 1 | turn 2 | turn 3+ |
|---|---|---|---|---|
| Qwen3-8B mtso / ref | +8.85 (0.909) / +5.84 (0.843) | +6.25 (0.905) / +2.83 (0.774) | +7.97 (0.956) / +3.57 (0.802) | +5.68 (0.913) / +0.20 (0.718) |
| Qwen3-14B-AWQ | +9.83 (0.940) / +8.99 (0.914) | +9.93 (0.905) / +4.72 (0.764) | +8.31 (0.949) / +2.86 (0.756) | +11.25 (0.833) / +6.11 (0.687) |
| Qwen3.5-9B | +8.74 (0.916) / +5.39 (0.846) | +5.33 (0.914) / +2.81 (0.813) | +7.83 (0.948) / −0.89 (0.698) | +9.77 (0.880) / +0.95 (0.739) |

- **MT-SO-P3 holds:** later turns, three models pooled, SEL3 − T +9.10 [+6.65, +11.47].
- **MT-SO-P4 holds:** mtso − mtsel on the same later-turn sets +5.66 [+3.85, +7.55]. MT-SEL's turn-0 verifiers fall to AUROC
  0.69–0.81 on later turns, while the retrained ones keep 0.83–0.96. Their turn-0 gain is larger too (+8.7 to +9.8 against MT-SEL's
  +5.6 to +8.8), from twice the training requests.
- Against the expected "smaller gain than turn 0's", the later-turn gain is about as large as turn 0's. The pseudo-sets come from
  different histories, so the online run decides (P1, P2).

Online jobs submitted 2026-11-03 20:1x UTC: 1311508 / 1311510 / 1311512 `mtso_q8b_s{1,2,3}` and 1311509 / 1311511 / 1311513 `mtso_q35_s{1,2,3}`
(vote_lane.sh, LoRA mtso_h0 / mtso_h1 on the Qwen3-8B server; MT_VER=peer for Qwen3.5-9B).

## Results of addendum MT-SO, online part (written 2026-11-04 09:1x UTC; `results/mtso_online.txt`; jobs 1311508–1311513, 600 items × seeds 1–3 per model, graded by `grade_mt.py <tag> S`)

| model (peer) | S | T | S − T utility | S − T accuracy | turns committing N / P / T | structure unseen | verifier prefill per item |
|---|---|---|---|---|---|---|---|
| Qwen3-8B (Qwen3.5-9B) | 48.8% @ 8.31k | 30.8% @ 6.84k | **+17.21 [+14.33, +20.12]** | +17.94 [+15.11, +20.78] | 22.4 / 36.8 / 40.8% | 0.4% | 16.7k |
| Qwen3.5-9B (Qwen3-8B) | 53.9% @ 3.29k | 38.0% @ 2.56k | **+15.52 [+12.83, +18.52]** | +15.89 [+13.17, +18.89] | 29.0 / 20.3 / 50.8% | 0.2% | 16.8k |

Per seed: Qwen3-8B S 49.2 / 48.7 / 48.5%, Qwen3.5-9B S 53.3 / 55.0 / 53.3%. By category (accuracy), Qwen3-8B: base +17.50, missing
function +20.67, missing parameter +15.67; Qwen3.5-9B: +16.83, +17.17, +13.67; every interval above 0.

- **MT-SO-P1 holds** (utility lower bound > 0, 2 of 2) and **MT-SO-P2 holds** (accuracy, 2 of 2).
- Above the expected range (accuracy +5 to +12, utility +3 to +10): the tokens cost 1.21× / 1.29× T's (−0.7 / −0.4 utility), and
  the accuracy gain is +16 to +18. S is also above every other stored arm of both models: the best of them is Qwen3.5-9B's F at
  38.7%. Qwen3-8B with the choice (48.8%) beats its peer's own thinking (38.0%) by 10.8 points.
- Raw trajectories (Qwen3-8B seed 1, S right and T wrong: 152 items; the reverse: 35): T's failures there are a wrong end state
  (86), a wrong response (34), a turn left without calls (27) and forced stops (5). In the two read, S commits the peer's quick turn
  at turn 0 and then the thinking turn. In one, T calls nothing at turn 1. In the other, T books the flight twice at turn 0 and
  then uses the second booking's id.
- Scope: the verifier and the choice rule are cross-fitted by scenario. Both halves use BFCL's eight environment classes. The
  verifier's prefill (16.7k tokens per item, a LoRA on the Qwen3-8B server) is reported, not priced.

**Decision (registered):** the agent-loop method becomes the verifier's choice among the quick turn, the peer's quick turn and the
thinking turn at every turn (PROJECT, REPORT, PROPOSAL). Next, as registered:
1. An online run in environments the verifier never saw (MT-SEL-ENV's decision). Its verifiers must be trained with later turns:
   MT-SO-P4 showed turn-0 verifiers lose most of their later-turn separation.
2. The gate: skip the peer and the quick turn when the verifier is sure (MT-SEL's P3). MT-SEL-ENV found that the gate's threshold
   did not transfer across environments, so the gate is tested on the scenario split first.

## Addendum MT-SO-ENV: the choice at every turn, online, in environments the verifier never saw (written 2026-11-04 09:1x UTC, before any environment-split verifier with later turns is trained)

**Why.** MT-SO holds online with verifiers cross-fitted by scenario, but both halves use BFCL's eight environment classes. MT-SEL-ENV
showed that at turn 0 a verifier trained on the other four classes keeps about half the gain. MT-SEL-ENV's decision registered this
run for the case that MT-SO holds. Its verifiers must see later turns, because MT-SO-P4 showed that turn-0 verifiers lose most of their
separation there. The answer sets the scope of the agent-loop claim: "trained on the target environments", or "trained on other
environments".

**Split.** MT-SEL-ENV's environment groups (`analyze_mtb.env_half`):
- group 0: GorillaFileSystem, MathAPI, TwitterAPI, VehicleControlAPI (228 items);
- group 1: MessageAPI, TicketAPI, TradingBot, TravelAPI (240 items).

The 132 items that use both groups are dropped from training and test.

**Run.**
1. `python3.11 poc/analyze_mtb.py --so-env-build` writes, per group g:
   - `$POC_DATA/bfcl/mt_soenv_ids_h<g>.txt`, the turn-0 and later-turn request ids of mt_sel2 whose item is in group g;
   - `results/conf/sel_req_mt2env_h<g>.jsonl`, mt_sel2's texts of those items.
2. Jobs `mtsoenv_h<g>`:
   - train with MT-SO's recipe on group g only: `MT_SEL_TAG=mt_sel2 SEL_IDS=mt_soenv_ids_h<g>.txt tc_train.py $POC_DATA/cv/mtsoenv_h<g>
     --orm --mt --batch 8 --epochs 4`;
   - then score the other group's texts: `cv_eval_lane.sh score-tc ... mtsoenv_h<g> sel_req_mt2env_h<1-g>.jsonl mt2`.
3. `MT_SEL_SPLIT=env python3.11 poc/analyze_mtb.py --sel2 mtsoenv_h0,mtsoenv_h1` gives the offline per-turn table on the env-pure
   pseudo-sets. It writes the choice rule `results/tc/mt_soenv_fit_<model>.json`: for each group, the set-choice fit on the other
   group's sets, with the scores of the verifier not trained on that group.
4. The online arm U (`run_mt.py <tag> U <seed>`) is arm S with the item's group in place of its scenario half: verifier
   `mtsoenv_h<1-g>`, the fit of group g. It runs on the 468 env-pure items, for both models, seeds 1–3, with the same jobs, servers and
   peers as MT-SO. Then `grade_mt.py <tag> U` and `MTV_ARM=U python3.11 poc/analyze_mtv.py q8b q35` (U − T and U − S on the same items).

**Predictions** (paired 95% intervals over items, seed means; utility as MT-SO):
- **MT-SOENV-P1 (decision):** U − T utility lower bound > 0 for both models.
- **MT-SOENV-P2:** U − T accuracy lower bound > 0 for both models.
- **MT-SOENV-P3 (cost of unseen environments, reported):** U − S on the same items, per model, with its interval. As in MT-SEL-ENV
  this mixes unseen environments with less training data.
- **MT-SOENV-P4 (offline):** on the later-turn pseudo-sets of env-pure items, the three models pooled, SEL3 − T lower bound > 0.
- **Expected.**
  - Offline, the environment split kept 45–70% of the scenario split's turn-0 gain on the same items. So U − T +6 to +12 utility,
    against S − T's +15.5 to +17.2, and U − S −4 to −10.
  - Later-turn AUROC (offline) 0.75–0.85, against mtso's 0.83–0.96.

**Decision.**
- **P1 holds for both** → the agent-loop claim is stated for environments the verifier never saw, within BFCL (REPORT, PROPOSAL).
  Next: the gate, then SIDE-ENV (beyond BFCL's classes).
- **P1 refuted for either** → the claim is scoped to "a verifier trained on scenarios of the target environments", reported with
  the per-turn offline diagnostics and U − S.

## Results of addendum MT-SO-ENV, offline part (written 2026-11-04 13:4x UTC; `results/mtsoenv_offline.txt`; jobs 1315451 / 1315452: training on 560 / 611 requests with a right and a wrong rollout, then 19,273 / 13,982 texts scored, none failed; the fits `results/tc/mt_soenv_fit_{q8b,q14a,q35}.json`)

SEL3 − T on the env-pure pseudo-sets. Each set is scored by the verifier trained on the other environment group. Table cells give
the gain with the AUROC within sets in parentheses.

| model | turn 0 | turn 1 | turn 2 | turn 3+ |
|---|---|---|---|---|
| Qwen3-8B | +5.18 (0.847) | +2.28 (0.785) | +7.58 (0.915) | +3.40 (0.842) |
| Qwen3-14B-AWQ | +7.07 (0.907) | +4.10 (0.765) | +7.68 (0.848) | +9.70 (0.786) |
| Qwen3.5-9B | +5.04 (0.856) | +2.55 (0.801) | +5.29 (0.876) | +7.49 (0.814) |

- **MT-SOENV-P4 holds:** later turns, three models pooled, +4.03 [+1.20, +6.71]. The script prints it under MT-SO-P3's label; it is
  this addendum's P4.
- Later-turn AUROC is 0.765–0.915, against the expected 0.75–0.85; three cells are above the range. The turn-0 gain, +5.0 to +7.1,
  is above MT-SEL-ENV's turn-0-only verifiers (+3.0 to +3.9). The training with later turns helps at turn 0 too.
- The online arm U was submitted at 13:39 UTC by the chain: jobs 1316461 / 1316463 / 1316465 `mtsoenv_q8b_s{1,2,3}` and 1316462 /
  1316464 / 1316466 `mtsoenv_q35_s{1,2,3}` (vote_lane.sh, LoRAs mtsoenv_h0 / h1, `run_mt.py <m> U <s>`, 468 env-pure items).
