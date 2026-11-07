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

## Addendum MT-SO-ENV-P5: a compounding model's prediction of the online gain (written 2026-11-04 17:4x UTC; MT-SO-ENV's six online jobs are running, and no U row has been read or graded)

**Model.** BFCL grades a conversation right only when every turn is right. So with per-turn success p_t given a right start, a
conversation of K turns succeeds with probability ∏_{t<K} p_t, and an arm's accuracy is the turn-count-weighted mean of that
product. There are no free parameters. Per-turn p_t comes from the offline pseudo-sets: T's rate for arm T, SEL3's for the choice;
turns ≥ 3 share one rate. The weights are the items' turn counts.

**Check on MT-SO, whose online result predates this model** (all 600 items):

| model | product model: T, S, S − T | online: T, S, S − T |
|---|---|---|
| Qwen3-8B | 37.0%, 52.5%, +15.5 | 30.8%, 48.8%, +17.9 |
| Qwen3.5-9B | 41.9%, 59.4%, +17.4 | 38.0%, 53.9%, +15.9 |

The model over-states both arms' levels by 4–6 points. The pseudo-sets keep only histories where N, P and T were all still right,
which are easier. The model gets the gain within 2.4 points, and the S/T ratio within 0.17 (1.42 against 1.58 and 1.42). The
registered expectation, +5 to +12, came from assuming a per-turn gain of +6, which is too small. The offline per-turn gains are
+6 to +10 points, and over 4–5 turns they multiply.

**Prediction for MT-SO-ENV.** On the 468 env-pure items, with the environment-split per-turn rates (`results/mtsoenv_offline.txt`):
- Qwen3-8B: U − T accuracy **+9.7** (additive form), +8.3 (ratio form: online T × (product ratio − 1));
- Qwen3.5-9B: **+10.4** (additive), +9.2 (ratio).

- **MT-SOENV-P5:** each model's online U − T accuracy interval contains the additive prediction.
- **Reported:** both forms' errors.

As a control, the same model with the scenario-split rates on these items gives +15.5 / +17.4, against online S − T of +16.5 /
+15.1.

## Addendum MT-PW: the within-set choice with the alternatives in view (written 2026-11-04 17:4x UTC, before any pairwise multi-turn training step or score)

**Why (derived, FINDINGS 2026-11-04 17:4x).** The compounding model puts the ceilings as follows.
- A perfect choice among the same N, P and T would lift whole conversations from SEL3's 52.5% / 59.4% (Qwen3-8B / Qwen3.5-9B) to
  63.7% / 71.2%, at no output tokens.
- A gate that skips the thinking rollout can gain at most +3.9 / +1.4 utility.
- In mixed sets, the pointwise verifier picks a wrong rollout 148 / 155 times (Qwen3-8B / Qwen3.5-9B) out of about 1,320 / 1,400.
  About half of those picks act where the right rollout makes fewer state-changing calls, mostly in the missing-parameter and
  missing-function categories.
- Telling "act" from "ask" is a comparison. A rollout that asks for a missing value only looks right next to ones that invent it.
  The pointwise verifier never sees the alternatives.

**Related work.**
- ToolRM (2510.26167) builds pairwise preference data on BFCL.
- Plan-RewardBench (2604.08178) has pairwise trajectory judges.
- MOSAIC (2603.03205) finds pairwise rewards teach refusal better than scalar ones, in a safety setting.
- Ours, SEL-PW-TC (single-turn tool calls): the pairwise verifier preferred a call to abstaining (380 of 386 disagreements), and
  did not pay.
- New here: the comparison within a live multi-turn choice set, whose training data holds many right non-actions (the miss_*
  categories).

**Run.**
1. `MT_SEL_TAG=mt_sel2 SEL_IDS=mt_sel2_ids_h<h>.txt tc_train.py $POC_DATA/cv/mtpw_h<h> --pw --mt --pairs 4 --batch 8 --epochs 4`:
   - the same requests and halves as `mtso_h<h>`;
   - for each request, up to 4 (right, wrong) rollout pairs per epoch, in both orders;
   - prompt `tc_pw_prompt` (the turn context, Response A, Response B; next token A or B).
2. `analyze_mtb.py --pw-build` writes `results/conf/sel_req_mt2pw_h<h>.jsonl`: every ordered pair of distinct texts in every
   pseudo-set of half h (sset mt2, kind pw). `cv_eval_lane.sh score-tc ... mtpw_h<1-h> sel_req_mt2pw_h<h>.jsonl mt2` scores them.
3. Each rollout's score is the mean over its rivals b of (s(a, b) − s(b, a)) / 2. It replaces the pointwise score in the
   set-choice fit, which is cross-fitted as in MT-SO.

**Predictions** (offline, pseudo-sets, the three models pooled, intervals over items):
- **MT-PW-P1 (decision):** per-turn choice accuracy, PW − SEL3 (pointwise mtso), lower bound > 0.
- **MT-PW-P2:** on the miss_param and miss_func sets, the share of wrong picks that act where the right rollout makes fewer calls
  falls.
- **MT-PW-P3 (reported):** within-set AUROC, PW against pointwise, and the compounding model's conversation-level gain.
- **Expected:** per-turn +1 to +3 points, conversation +2.5 to +7. The risk is SEL-PW-TC's preference for calls.

**Decision.**
- **P1 holds** → an online arm (MT-SO's S with the pairwise score) on the same items and seeds, decided on conversation utility.
- **P1 refuted** → the comparison format does not fix the act-or-ask error here. Next is the training signal: on-policy sets from
  the online S arm.

## Results of addendum MT-SO-ENV, online part (written 2026-11-04 22:3x UTC; `results/mtsoenv_online.txt`; jobs 1316461–1316466, 468 env-pure items × seeds 1–3)

| model | U (unseen classes) | T | U − T utility | U − T accuracy | U − S (same items) | P5 prediction (additive / ratio) |
|---|---|---|---|---|---|---|
| Qwen3-8B | 40.2% @ 8.00k | 32.1% @ 6.74k | **+7.56 [+4.52, +10.91]** | +8.19 [+5.13, +11.54] | −8.33 [−10.97, −5.63] | +9.7 inside / +8.3 inside |
| Qwen3.5-9B | 44.9% @ 3.37k | 37.8% @ 2.52k | **+6.63 [+3.73, +9.62]** | +7.05 [+4.13, +10.04] | −8.05 [−10.68, −5.34] | +10.4 just outside / +9.2 inside |

- **MT-SOENV-P1 and P2 hold** for both models. U − S of −8.3 / −8.1 is inside the expected −4 to −10.
- **P5:** the registered additive form holds for Qwen3-8B. For Qwen3.5-9B it misses: +10.4 against an upper bound of +10.04. The
  ratio form is inside for both. So the compounding model, fed the offline per-turn rates, predicts the online gain in unseen
  environments within 2.2 to 3.3 points (additive) or 0.1 to 2.2 (ratio).
- By category, missing parameters carries the least: Qwen3.5-9B +0.64 [−5.56, +6.20], Qwen3-8B +5.34. This is the act-or-ask choice
  MT-PW targets.
- 1.5% of turns had a set structure the fit never saw (T committed), against 0.2–0.4% in the scenario split.

**Decision (registered):** the agent-loop claim holds in environment classes the verifier never saw, within BFCL. A verifier
trained on the other four classes still beats thinking at every step by +7.6 / +6.6 utility; one trained on the same classes does
so by +17.2 / +15.5. The gate registered next was dropped by derivation (FINDINGS 11-04 17:4x). The test beyond BFCL's classes
remains SIDE-ENV's.

## Results of addendum MT-PW (written 2026-11-05 01:0x UTC; `results/mtpw_offline.txt`; jobs 1317909 / 1317910: 384 / 370 training steps, 22,222 / 24,924 ordered pairs scored, none failed; fits `results/tc/mt_sopw_fit_<model>.json`)

Per-turn choice accuracy on the pseudo-sets, SEL3 (pointwise mtso) → PW (pairwise mtpw):

| model | turn 0 | turn 1 | turn 2 | turn 3+ |
|---|---|---|---|---|
| Qwen3-8B | 80.5 → 81.4 | 87.2 → 87.5 | 92.3 → 91.0 | 84.5 → 85.9 |
| Qwen3-14B-AWQ | 81.0 → 82.4 | 87.2 → 87.8 | 93.0 → 91.6 | 86.5 → 87.4 |
| Qwen3.5-9B | 82.8 → 83.5 | 89.7 → 89.1 | 92.5 → 92.2 | 89.1 → 89.1 |

- **MT-PW-P1 holds, barely:** PW − SEL3 = **+0.89 [+0.02, +1.72]** points per turn, pooled. This is below the expected +1 to +3.
- **P2 holds:** in mixed sets, three models pooled (argmax of each score), picks that act where the right rollout acts less fall
  from 152 to 131 in the miss_* categories and from 27 to 16 in base. All wrong picks fall from 389 to 343.
- **P3:** within-set AUROC rises at turn 0 (0.909 → 0.922 for Qwen3-8B) and at turn 3+, and falls at turn 2. The compounding
  model turns the per-turn rates into a conversation-level change of **+1.1 (Qwen3-8B) and −0.1 (Qwen3.5-9B) points** of
  accuracy.

**Decision (amended before any online row, with the reason).** The registered rule sent P1 → an online arm. But the compounding
model predicts +1.1 / −0.1 points online, while the online test's interval is about ±3 points (MT-SO-ENV: half-widths 2.9–3.4). The
arm could not tell the pairwise verifier from the pointwise one, so by rule 2 it cannot change the claim, and it is not run. The
online method keeps the pointwise verifier.

What MT-PW shows: seeing the alternatives fixes about a seventh of the act-or-ask errors and closes about 1 of the 11 points
between SEL3 and a perfect choice. The comparison format is not where the remaining room is.

## Addendum MT-SD: show the verifier what each rollout changed in the environment (written 2026-11-05 02:0x UTC, before any state diff is computed)

**Why (derived, FINDINGS 11-05 01:0x).**
- A per-turn label is "the environment's state and the responses match the ground truth after the turn".
- The verifier reads each rollout's calls and their returned results (`render`), but not the state they leave behind.
- Its remaining wrong picks are confident: the 10% smallest-margin sets hold only 8% of them. So better calibration, the comparison
  format (MT-PW, +0.9 per turn) or on-policy data will not reach them.
- One candidate for what it lacks is the label's own subject: the state change. A rollout that acts where it should ask, or acts
  twice, changes the state in a way its result strings show only indirectly ("None", a message id).

**Method.**
1. `mt_peer0.py --state-diff` replays every stored trajectory turn by turn on BFCL's instances, as `turn_track` does. It records
   each turn's change of every involved instance's public attributes: added, removed and changed paths with short values, at most
   40 lines, with parent links skipped.
2. Each pseudo-set rollout's text becomes `render` + "State changes:" + its diff (from the first source trajectory of that text).
3. The same pointwise recipe as mtso, with the same halves and requests: `MT_SEL_TAG=mt_sd ... tc_train.py --orm --mt`, then scoring
   with the other half's verifier, then `analyze_mtb.py --sel2` on the rows with the new texts.

**Predictions** (offline, pseudo-sets, three models pooled, intervals over items):
- **MT-SD-P1 (decision):** per-turn choice accuracy, SD − SEL3, lower bound > 0.
- **MT-SD-P2:** the act-where-the-right-one-asks wrong picks in miss_* fall by more than MT-PW's 14%.
- **Diagnostic, before training:** among the 388 wrong picks of SEL3 in mixed sets, the share where the chosen and the right
  rollout leave different state changes. If the share is small, the state is not the missing information, and the training is not
  run.
- **Expected:** per-turn +0.5 to +2. The compounding model's conversation gain is about 2.6 times the per-turn gain.

**Decision.** An online arm needs a conversation gain the online test can see. Its half-width is about 3 points, which needs about
+1.2 per turn. With P1 holding and a per-turn gain of at least that, the arm runs; otherwise the result is offline only.

### Note MT-SD, the registered diagnostic before training (2026-11-05 02:0x UTC)
- `mt_peer0.py --state-diff` (login node) replayed 18,568 trajectories with no failure. It produced 42,079 rollout texts; 19,752 of
  them change the state and 22,327 do not.
- Of SEL3's 389 wrong picks in mixed sets, **282 (72%) leave a state change different from every right rollout's**. In the other 107
  the difference lies in the response alone.
- Examples:
  - the chosen rollout changes nothing where the right one adds QUAS to the watch list;
  - the chosen rollout writes content where the right one creates an empty file;
  - the chosen rollout books nothing where the right one books and charges the card.
- The state carries the label's information in most errors, so the training runs, as registered: jobs `mtsd_h<h>`.

## Results of addendum MT-SD (written 2026-11-05 07:5x UTC; `results/mtsd_offline.txt`; jobs 1320257 / 1320258, then 21,363 / 20,716 texts scored, none failed)

Per-turn choice accuracy, SEL3 → SD (the verifier that reads each rollout's state change):

| model | turn 0 | turn 1 | turn 2 | turn 3+ |
|---|---|---|---|---|
| Qwen3-8B | 80.5 → 80.5 | 87.2 → 88.0 | 92.3 → 90.3 | 84.5 → 84.5 |
| Qwen3-14B-AWQ | 81.0 → 80.4 | 87.2 → 87.2 | 93.0 → 93.0 | 86.5 → 86.0 |
| Qwen3.5-9B | 82.8 → 83.3 | 89.7 → 90.8 | 92.5 → 91.1 | 89.1 → 89.1 |

- **MT-SD-P1 refuted:** SD − SEL3 = +0.06 [−0.78, +0.94] points per turn, pooled.
- **P2 refuted:** in the miss_* categories, picks that act where the right rollout acts less rise from 152 to 158 (base 27 → 42).
  All wrong picks rise from 389 to 405.
- So the state change is in front of the verifier now, and it still does not help. In 72% of the old wrong picks the state
  changes differ, but telling which change is right needs knowing which change the request asked for. That is the verifier's
  knowledge, not its view.

**Decision (registered):** offline only, no online arm. The verifier line on this benchmark closes for now. Three fixes left the
choice unchanged within about 1 point per turn: the comparison format (MT-PW, +0.9), the state view (MT-SD, +0.1), and calibration
(errors are confident). The remaining 10 points need a judge that knows more, at its full cost on every turn, and are left open.

## Addendum MT-JG: a judge that reasons before choosing (written 2026-11-05 07:5x UTC, before any judge call)

**Why (derived).**
- The choice's remaining 10 points are not about what the verifier sees (MT-SD: +0.1) or how it compares (MT-PW: +0.9).
- They are not about calibration either: its errors are confident.
- What is left is what the judge knows about the right action for the request. Thinking is the model's way to bring more of it to
  bear.
- The cost side: a judge's thinking tokens are paid on every turn, so the compounding model prices it. A judge that adds Δ points
  per turn adds about 2.6 Δ conversation points. It costs about 0.5 × (thinking k-tokens per turn) × 4.4 utility per conversation.

**Related.** Reasoning reward models for tool calls (ToolRM-4B-Thinking) lost to our trained verifier in single-turn selection
(SEL-RM: −5.9 to −9.5 utility), mostly by preferring a call to no call. New here: a general model thinking over the multi-turn
choice set, judged on the turns where it matters.

**Run** (offline, `mt_peer0.py --judge`).
- Qwen3-8B, thinking, max 4k tokens.
- On every pseudo-set with a right and a wrong distinct rollout (all three models; about 4,100 sets), the judge reads the short
  system prompt, the turn context and the distinct rollouts labelled A/B/C (rendered as the verifier sees them, in random order),
  then names the response that correctly handles the latest request.

**Predictions.**
- **MT-JG-P1:** the judge's choice accuracy on mixed sets exceeds SEL3's on the same sets (lower bound > 0, pooled, intervals
  over items).
- **MT-JG-P2 (decision):** a choice that uses the judge's letter is the fitted choice with the judge's pick as an extra feature,
  cross-fitted as SEL3. It beats SEL3 per turn by at least the break-even Δ = 0.5 × k × 4.4 / (2.6 × 100), where k is the judge's
  mean thinking k-tokens per turn. That is about 0.9 points at 1k tokens.
- **Expected:** the judge alone is below SEL3 (a general model against a trained one, as SEL-RM). The combination gains +0.5 to +2
  per turn, so P2 is uncertain.

**Decision.**
- **P2 holds** → an online arm with the judge on every turn.
- **P2 refuted** → the choice stays the verifier's, and the agent-loop method is final for this project.

## Results of addendum MT-JG (written 2026-11-05 09:2x UTC; `results/mtjg_offline.txt`; job 1322863; the first job 1322810 failed on import before any call)

Qwen3-8B thinking, 4,098 mixed sets, 0.87k tokens per set (97 capped, 7 without a letter); random choice 52.5%.

| rollouts of | SEL3 | judge alone | SEL3 + judge's pick (fitted) |
|---|---|---|---|
| Qwen3-8B | 88.9% | 82.5% | 88.2% |
| Qwen3-14B-AWQ | 92.6% | 84.7% | 92.6% |
| Qwen3.5-9B | 89.9% | 83.3% | 89.2% |

- **MT-JG-P1 refuted:** judge − SEL3 on mixed sets −6.75 [−8.86, −4.72].
- **MT-JG-P2 refuted:** combination − SEL3 per turn −0.37 [−0.80, +0.07], against a break-even of +0.74. The fitted weight is small
  (γ 0.2–0.8), and it still loses on held-out halves.

**Decision (registered):** the choice stays the verifier's, and the agent-loop verifier is final for this project. Format, state view,
calibration and a thinking judge have all been tried. Thinking does not bring what the trained verifier lacks.

## Addendum MT-RN: better candidates instead of a better judge: a quick turn trained on open data (written 2026-11-05 09:2x UTC, before any rollout of the trained model on BFCL multi-turn)

**Why (derived).**
- The verifier line is closed, but the compounding model names a second ceiling: the choice can only pick among what the set holds.
  In 5–14% of Qwen3-8B's pseudo-sets (by turn) no candidate is right. Even a perfect choice stops at 63.7%.
- SHARP (10-30) showed that plain RL's gain lies on items no base sample answers right: it adds answers.
- The trained quick calls (C1tc, trained on 6,000 open ToolACE requests, none from BFCL) mainly learned when not to call. That is the
  act-or-ask choice behind the verifier's errors and many none-right sets on the miss_* categories.
- A quick turn costs about a tenth of a thinking turn, so swapping it in costs almost no tokens.

**Related.** TRUST (2606.06976) and 2606.00135 train tool-calling models with RL and report gains on BFCL's multi-turn split. New
here: the trained turn as one candidate in a verifier's choice set, valued in advance by the compounding model.

**Run.**
- Qwen3-8B with `$POC_DATA/cv/tc1/adapter_final`, arm N (`run_mt.py q8btc N <s>`), 600 items, seeds 1–3, tensor parallel on two
  GPUs. Graded with `grade_mt.py q8btc N`.
- `mt_peer0.py --rn q8btc`: per-turn labels by `turn_track`; on Qwen3-8B's pseudo-sets of the same item, seed and turn, where the
  trained trajectory is still right through k−1, Δo = oracle{N, P, T, N_tr} − oracle{N, P, T}. Intervals over items.

**Predictions.**
- **MT-RN-P1:** the trained turn's whole-conversation accuracy exceeds the base N's (about 16.7%).
- **MT-RN-P2 (decision):** an online arm can see a conversation gain of about 3 points. The gain is about 2.6 × (the verifier's share
  of oracle gains, about 0.6) × Δo, so the bar is **Δo ≥ 1.9 points per turn**, with the lower bound > 0.
- **Expected:** P1 holds (a +3 to +8 gain, mostly on miss_*). Δo +1 to +3, so P2 is uncertain.

**Decision.**
- **P2 holds** → an online arm: S with the trained turn as a fourth candidate, the existing verifier unchanged.
- **P2 refuted** → training for single calls does not add the answers conversations lack. Training on multi-turn rollouts
  themselves (labels by scenario half) is the next candidate.

## Results of addendum MT-RN (written 2026-11-05 10:3x UTC; `results/mtrn_offline.txt`; job 1323864, 600 items × 3 seeds)

- **MT-RN-P1 refuted:** the trained quick turn is right on 15.8% of whole conversations, against the base N's 16.7%. By category:
  base 20.3% vs 26.2%, missing parameter 14.3% vs 10.7%, missing function 12.7% vs 13.2%. It learned not to act, which helps
  where asking is right and costs where acting is. 0.36k tokens per conversation.
- **Oracle of the set, per turn, on the sets where its trajectory is right through k−1** (N, P, T → with the trained turn): turn 0
  85.8 → 87.4, turn 1 91.6 → 92.9, turn 2 95.5 → 96.4, turn 3+ 89.1 → 89.5. Rescues at turn 0: base 0.0%, missing function 2.0%,
  missing parameter 2.9%.
- **MT-RN-P2 as coded:** +1.95 [+1.24, +2.79], mean over items, just over the 1.9 bar. Pooled over sets it is +1.4, because items
  with few sets (those that fail early) have more rescues. The item-weighted figure is what the code printed; the bar was derived
  from the per-turn rates.
- **Conversation level, the quantity the bar stood for:** the compounding model gives the oracle 64.6% → 67.7%. The verifier
  realises 56% of oracle gains over T, so the choice gains about **+1.7 points**, against a detectable gain of about 3.

**Decision (amended before any online row, with the reason).** The registered rule reads P2 → online arm. But P2 passes only under
item weighting, by 0.05, and the conversation gain it stood for is +1.7, inside the online test's noise; the arm would also need a
fourth role in the fit. As with MT-PW, by rule 2 it is not run. A quick turn trained for single calls does not add the answers
conversations lack.

## Addendum MT-RF: a quick turn trained on multi-turn right rollouts (written 2026-11-05 10:3x UTC, before any training step)

**Why.** MT-RN's registered next step. Training for single calls (ToolACE) taught abstention, and conversation accuracy did not rise.
The set's oracle (64–71% over whole conversations) is a ceiling no judge can pass; candidates must get better. The stored rollouts
already hold, per scenario, which turns were right, with their results. Half the scenarios can teach the quick turn for the other
half, labels only in training. If the quick turn gets much better, the choice also commits it more often, and the tokens fall.

**Related.** RL on tool-calling models with BFCL-style rewards: TRUST (2606.06976), 2606.00135. RFT on the model's own right answers:
the project's WP-RF and TD, where the quick mode's own right programs beat thinking programs as targets. New here: a trained
quick turn as the candidate in the per-turn choice, valued in advance by the compounding model.

**Run.**
1. `mt_peer0.py --rf-build`: for each request (turn given a right start) of half h, the right rollouts of mt_sel2's pool. Each step
   becomes a row: the conversation so far (the source trajectory's own right history, tool results replayed in full) → the step's
   text. A step whose calls returned an error is not a target.
2. `tc_train.py <out> --sft-mt <rows of h>`: Qwen3-8B LoRA (r 16), 2 epochs, one sampled right rollout per request per epoch, loss =
   mean negative log-probability of the target given a no-gradient prompt, lr 5e-5, batch 8 rows.
3. `run_mt.py q8brf N <s>` with `MT_N_LORA=mtrf_h`: each item uses the adapter trained on the other half. 600 items, seeds 1–3.
4. `grade_mt.py q8brf N`, `mt_peer0.py --rn q8brf`.

**Predictions** (paired, intervals over items).
- **MT-RF-P1:** the trained turn's conversation accuracy − base N's (16.7%), lower bound > 0.
- **MT-RF-P2 (decision):** with the trained turn replacing N in the set, the compounding model (per-turn rates pooled over sets, the
  verifier's 0.56 share of oracle gains) gives a conversation gain ≥ 3 points, the size the online test can see.
- **Expected:** P1 +5 to +15 (scenario-specific habits: environment usage, when to stop). P2 uncertain.

**Decision.**
- **P2 holds** → an online arm: S with the trained N, verifier and fit refitted on its rollouts.
- **P2 refuted** → the agent-loop method is final for this project, and candidates stay as they are.

### Results of MT-RF (written 2026-11-05 20:5x UTC; rollouts job 1330121, `results/mtrf_offline.txt`)

- **MT-RF-P1 holds.** The trained quick turn gets 24.5% of conversations right against base N's 16.7%, +7.83 [+5.00, +10.72], at 0.31k tokens (3 seeds, 600 items, adapter trained on the other half of the scenarios). By category: base 26.2 → 31.7, missing function 13.2 → 22.3, missing parameter 10.7 → 19.5. Within the expected +5 to +15.
- **MT-RF-P2 refuted.** With the trained turn replacing N, the set's oracle over conversations goes from 64.0% to 68.7%, which at the verifier's 0.56 share is +2.6 points, below the bar of 3.
- **Decision, as registered:** no online arm. The agent-loop method is final for this project, and candidates stay as they are.
- **Not registered, for the record:** added as a fourth candidate instead of replacing N, the same calculation gives +4.8 points. I saw this number before thinking about that design, so it decides nothing here.
- **Raw rollouts.** Forced termination falls from 545 to 192 of 1,800 runs, and empty turns rise from 114 to 219: it learned to stop, and it abstains somewhat more. On `multi_turn_base_113` it looks up the stock symbol before adding it to the watchlist, where base N skips the lookup and the state ends wrong, which is the environment habit we hoped for. It sometimes repeats a lookup three times within a step.


## Addendum MT-FC: is our baseline the benchmark's baseline? (written 2026-11-06 22:5x UTC, before any native-form row; item file and loop mode only)

**Why.** Reading the agent-loop claim as a reviewer (rule 9), I read EnvACE (2608.06197, Table 1 and Table 3) in full. It runs the same base model on the same benchmark with public weights, under BFCL's "official protocol":

| Model (BFCL v4 multi-turn, mean of four categories, Avg@4) | Published |
|---|---|
| Qwen3-8B | 42.09 |
| Arctic-AWM-8B | 42.81 |
| EnvACE-8B (base 47.5, miss func 45.5, miss param 35.0, long context 39.5 in its own Table 3 run) | 45.29 |
| AWM-14B | 49.06 |
| EnvScaler-8B | 52.25 |

Ours on three of those categories: Qwen3-8B thinking at every step 30.8 (base 37.3, miss param 24.2, miss func 31.0); MT-SO 48.8 (54.8, 39.8, 51.7). So the same model at the same setting sits about 11 points lower here, and a trained 8B model is published above our method. **Our statement "an open 8B model above published training-only results" is therefore unproven and possibly false, and "+18 over thinking" may be measured against a baseline weakened by our prompt format.** Surprising numbers are bugs until shown otherwise (rule 5).

**What differs.** We use BFCL's *prompt* mode: its default system prompt, function docs as text, calls as Python syntax, reasoning dropped from the context between steps, temperature 0.7. Those checkpoints were trained on the *native* form: tools in the chat template, calls as `<tool_call>` JSON (their cards: "drop into any standard Qwen3 tool-calling client"). BFCL's own local handler for Qwen3 (`QwenFCHandler`) keeps the reasoning of the current request's earlier steps in the context.

**Run.** `poc/prep_mt.py --fc` writes `mt_fc_items.jsonl`: all four categories (800 items), no default system prompt, functions as OpenAI tools through BFCL's `convert_to_tool`, holdout turns with BFCL's user message as its local handlers do. `poc/run_mt.py` with `MT_FC=1`: tools through the chat template, decoded as `QwenFCHandler`, reasoning kept as the template keeps it, 20-step limit, thinking cap 8,192, temperature 0.6 and top-p 0.95 (EnvACE's stated setting; top_k not set). Graded by BFCL's checker with the same `poc/grade_mt.py`. These change three things at once on purpose: this tests whether the official form reproduces the published number, and only if it does is there a reason to separate them. Lanes: T and N on Qwen3-8B; T on EnvScaler-Qwen3-8B, EnvACE-Qwen3-8B, Arctic-AWM-8B, all from public weights, on two RTX 3090s, seed 1 first. An overflow at 32,768 counts as a failure, as in BFCL.

**Predictions (seed 1; 95% intervals over items; "mean of four" as the papers report it).**

- **MT-FC-P1:** Qwen3-8B T, mean of four = 40 (range 36 to 46; published 42.09).
- **MT-FC-P2 (decision):** on our 600 items, Qwen3-8B T in native form minus T in prompt mode (seed 1, paired): lower bound > 0.
- **MT-FC-P3:** published checkpoints, mean of four: EnvScaler-8B 50 (46 to 55), EnvACE-8B 45 (41 to 49), AWM-8B 43 (39 to 47). A checkpoint below its range would mean our loop differs from theirs in a way I have not found.
- **MT-FC-P4 (reported):** Qwen3-8B N in native form against N in prompt mode (16.7), because N is one of MT-SO's three candidates.

**Decision.**

1. P2 holds: the prompt format was weakening our baseline. "+18 over thinking" is withdrawn as the method's gain, and the main claim is restated against the best form of the base model and the best public checkpoint on the same items. Next, per-turn selection is rerun in native form, since candidates from a stronger form change the compounding prediction (registered after the per-turn numbers exist, before any online row).
2. P2 fails: the format is not the reason. Then long context and their seed count are read first, and BFCL's own CLI path (`bfcl generate`) settles whether the published number reproduces at all.
3. Either way, if the best public checkpoint's interval on the 600 items lies above MT-SO's 48.8, then our method is not the best open 8B result, and the claim says so.

### MT-FC results (2026-11-07 02:3x UTC; seed 1; Qwen3-8B and EnvScaler-8B done, EnvACE-8B and AWM-8B still running)

| Arm (native form unless stated) | Base | Miss func | Miss param | Long context | Mean of four | Our 600 items | Tokens on the 600 |
|---|---|---|---|---|---|---|---|
| Qwen3-8B N | 22.5 | 16.0 | 15.5 | 14.0 | 17.0 | 18.0 | 0.47k |
| Qwen3-8B T | 46.5 | 43.5 | 35.0 | 27.0 | **38.0** | 41.7 | 5.93k |
| EnvScaler-8B T | 67.0 | 57.5 | 38.0 | 40.0 | **50.6** | 54.2 [50.2, 58.2] | 7.60k |
| Prompt mode: Qwen3-8B T (3 seeds) | 37.3 | 31.0 | 24.2 | | | 30.8 | 6.84k |
| Prompt mode: MT-SO (3 seeds) | 54.8 | 51.7 | 39.8 | | | 48.8 [45.4, 52.2] | 8.31k |

- **P1 holds:** 38.0, in 36–46 and below the expected 40. Published 42.09 (four-run average). Long context is the weakest category (27.0).
- **P2 holds, decisively:** native T minus prompt T, seed 1, paired on the 600: **+12.0 [+7.6, +16.4]**; against the three prompt seeds +10.8 [+7.0, +14.7]. All three categories rise (+10.0, +15.5, +10.5).
- **P3, EnvScaler holds:** 50.6 in 46–55 (published 52.25). EnvACE and AWM pending.
- **P4:** native N against prompt N, +1.2 [−2.5, +4.8]: a tie. The form helps thinking, not the quick turn. N on the base category is lower (−4.0, not significant).

**Decision, by rule 1 and rule 3.**

1. **"+18 over thinking" is withdrawn as the method's gain.** Most of the baseline's weakness was our prompt format. Against the same model in its best form, MT-SO in prompt mode gains **+7.1 points [+3.3, +10.9]**, at 8.31k tokens against 5.93k, utility **+5.9 [+2.1, +9.8]**. That comparison crosses forms, and the native form of MT-SO has not been run.
2. **Our method is not the best open 8B result.** EnvScaler-8B with plain thinking in native form beats MT-SO on the same items: **+5.4 points [+1.7, +9.1]**, at fewer tokens, utility +5.7 [+2.0, +9.5]. Its interval [50.2, 58.2] lies above 48.8. Training on generated environments (a published method) does more than selection over the base model in the prompt form.
3. **Next, as registered:** per-turn selection in native form. Its prediction is written after the per-turn numbers exist and before any online row.

**A reviewer's reading.** What stands is the mechanism (per-turn sandboxed choice compounds over a conversation; the model predicted the gain within 2.4 points) and the result on unseen environment classes, both measured in prompt mode. What falls is the size of the gain and the comparison with training-only results. The open question that decides whether the method has a place: does selection add to the best checkpoint, in its best form? Interim per-turn data bound it. At turn 0 (the only turn where independent runs share a state): EnvScaler T 82.9, Qwen3-8B T 75.4, oracle over the two 86.5; Qwen3-8B N with EnvScaler T 86.4. In prompt mode the same oracle gain was about 14 points; here it is 3.6.

### MT-FC correction and addendum MT-FC-KEEP (written 2026-11-07 02:3x UTC, before any row with the reasoning kept)

**A correction to what I wrote above.** The addendum says the reasoning of a request's earlier steps stays in the context, as BFCL's handler keeps it. Reading the code to port the loop, I found it did not: `chat_msgs` strips the reasoning before `answer_fc` sees the reply, so every native row so far (Qwen3-8B N and T, EnvScaler T, EnvACE T, AWM T) ran with reasoning dropped between steps. The numbers above are right for what ran, and "native form" in them means tools in the template and `<tool_call>` JSON, without kept reasoning. That doesn't change the decision (P2's lower bound is already above 0), but "the base model's best form" and "EnvScaler's published setting" have not been measured yet.

**Run.** `MT_KEEP=1` keeps the raw reply in the context, and Qwen3's template shows the reasoning for steps after the last user message and drops it for earlier ones, as `QwenFCHandler` does. Tag `esfk`: EnvScaler-8B T, seed 1, 800 items, otherwise as above. Then the same for Qwen3-8B (`q8bfk`).

**Predictions.**
- **KEEP-P1 (decision):** EnvScaler T with kept reasoning minus without, paired on the 800, seed 1: +2 points (range −2 to +6). The gap to the published mean of four is 1.65, which is within noise, so I expect little.
- **KEEP-P2 (reported):** more overflow failures at the 32,768 context, mostly in long context, and more tokens are not expected, since a step's cap is unchanged.

**Decision.** The lower bound above 0: kept reasoning becomes the native form for every later row, and the arms that matter are rerun. Otherwise (a tie or worse): the rows stand as they are, and the form is reported as tested both ways.

### MT-FC: EnvACE-8B (2026-11-07 02:4x UTC; seed 1, reasoning dropped as above)

EnvACE-8B T: base 46.5, miss func 40.5, miss param 38.5, long context 29.5, **mean of four 38.8**, 7.00k tokens. **P3 fails for this checkpoint:** below its range (41–49; published 45.29; its Table 3 run: 47.5, 45.5, 35.0, 39.5). As registered, this means our loop differs from theirs in a way I have not found. The largest gap is long context, −10. The known difference is the dropped reasoning, which MT-FC-KEEP tests on EnvScaler (job 1344657); EnvACE is rerun if that test moves.

Per turn, tracked by `turn_track` on the 800 (exploratory; only turn 0 starts from a shared state, later rates are conditional on each arm's own history):

| Arm | Turn 0 | 1 | 2 | 3+ | Whole |
|---|---|---|---|---|---|
| EnvScaler T | 82.9 | 81.5 | 87.8 | 86.1 | 48.8 |
| EnvACE T | 77.8 | 76.9 | 79.9 | 82.1 | 36.8 |
| Qwen3-8B T | 75.4 | 77.7 | 80.7 | 83.2 | 36.6 |
| Qwen3-8B N | 57.6 | 62.7 | 67.0 | 76.2 | 16.2 |

Oracles over EnvScaler T with others: turn 0, 82.9 → 87.6 (with EnvACE T), 86.5 (Qwen3-8B T), 86.4 (Qwen3-8B N), 89.9 (all four). Conversations right by at least one arm, independent runs: 48.8 → 54.2, 54.2, 51.9, 58.8. So the upper bound on what selection can add to the best checkpoint is real, about 10 points over conversations with four arms, and it needs the arms to be different models. The compounding prediction waits for EnvScaler's own quick turn and AWM.

### MT-FC: a second fault found, in long context (2026-11-07 03:4x UTC)

Reading EnvScaler's evaluation section: it runs at 64K context "to match the Long-Context subset". Our lanes run at 32,768. **In long context, 43 of 200 conversations overflow in every arm and count as failures.** The registered 600 items contain no long context, so P2 and both decisions stand. The means of four (P1, P3) and EnvACE's miss below its range are affected. Before EnvACE's miss is read as an unknown difference, the overflowing items are rerun at 65,536 for the arms that have them, with results reported as a correction next to the registered numbers (`mt_fc_over.jsonl`, tags `<arm>64`). All later long-context rows run at 65,536.

### MT-FC: Arctic-AWM (2026-11-07 04:2x UTC; seed 1, reasoning dropped, 32,768 context)

AWM-8B T: base 50.0, miss func 41.5, miss param 30.5, long context 27.0, mean of four **37.2**, 5.59k tokens. **P3 fails for this checkpoint too** (39–47; published 42.81). So three of the four run below their published number by 1.7 to 6.5, with the context fault as the first suspect. EnvScaler's quick turn: 27.6% whole conversations at 1.30k tokens, against Qwen3-8B's 16.2%.

## Addendum MT-FCS: does per-turn selection add to the best checkpoint? (written 2026-11-07 04:2x UTC, before any native verifier or online row)

**Why.** The registered next step of MT-FC. The method's place depends on this: selection on top of the best public checkpoint, in its best form, on the same items.

**Numbers it rests on** (`turn_track`, seed 1, 800 items; only turn 0 starts from a shared state):

| Set around EnvScaler T | Turn 0 right, oracle (alone 82.9) | Conversations right by at least one, independent runs (alone 48.8) | Output tokens per conversation |
|---|---|---|---|
| A: + EnvScaler N | 86.6 | 53.5 | 8.6k |
| **B: + EnvScaler N, Qwen3-8B T** | **89.0** | **57.0** | 14.3k |
| C: + EnvScaler N, EnvACE T | 89.8 | 57.4 | 15.6k |
| D: + EnvScaler N, EnvACE T, Qwen3-8B T | 90.5 | 59.6 | 21.3k |

**Derivation.** Per-turn gains multiply. If a set removes a fraction 1 − f of EnvScaler's turn errors at every turn, with f taken from turn 0, a conversation of L turns succeeds with Π(1 − f(1 − r_k)), r_k being EnvScaler's rates at turn k (82.9, 81.5, 87.8, 86.1 for 3+). With f = 1 this gives 50.7 against an actual 48.8. Compounded oracles: A 59.3, B 65.3, C 67.3, D 69.3. The verifier realised 0.54 of the compounded oracle gain in prompt mode ((48.8 − 30.8) / (64.0 − 30.8)). So the predicted gains are A +4.6, B +7.8, C +8.9, D +10.0, and net of tokens in utility A +4.0, B +4.3, C +4.8, D +3.0. **The choice:** these nets are within noise of each other, so I take B for its hardware, since the verifier's LoRA loads on the Qwen3-8B peer and the set needs only two servers, and because accuracy, which the project is after, is second-highest there among the nets above +4. **Assumptions not tested:** f constant over turns, and the share carrying over from prompt mode. The share is the risky one: EnvScaler's errors are fewer, and they may be harder to see.

**Run.**
1. `FC_ARMS` = EnvScaler T, N, Qwen3-8B T, N, EnvACE T, AWM T (seed 1) and EnvScaler T seed 2 when ready; `FC_ROLES=N=esfc:N,P=q8bfc:T,T=esfc:T`; `mt_peer0.py --fc-build`, which also feeds the four categories into MT-SO's cross-fit by scenario half.
2. Two verifiers `mtfcs_h<h>` on base Qwen3-8B, MT-SO's recipe (`MT_SEL_TAG=mt_fcs tc_train.py --orm --mt --batch 8 --epochs 4`). Each scores the other half.
3. Offline: `MT_SEL_TAG=mt_fcs MT_SEL_SSET=mtfcs MT_SEL_MODELS=esfc analyze_mtb.py --sel2 mtfcs_h0,mtfcs_h1`.
4. Online, arm S in native form on 800 items: `vote_lane` with EnvScaler (gen) and Qwen3-8B with the two LoRAs (peer), `MT_VER=peer MT_SPEC=N:gen:0,P:peer:1,T:gen:1 MT_VER_PREFIX=mtfcs_h`, at 65,536 context. Native form as MT-FC-KEEP decides.

**Predictions.**
- **FCS-P1 (gate):** offline, the verifier's chosen rollout on the pseudo-sets minus EnvScaler T's, at turn 0: at least 3.0 of turn 0's 6.1-point oracle gain would match 0.54 (3.3). If the share over all turns implies a compounded gain below 3 points, the online arm isn't run, as MT-RF.
- **FCS-P2 (decision):** online B minus EnvScaler T, paired on the 800, seed 1: **+7.8** (range +3 to +12), lower bound above 0.
- **FCS-P3 (reported):** utility B minus EnvScaler T: +4.3 (range 0 to +9).

**Decision.**
1. P2 holds: selection adds to the best checkpoint. Seeds 2 and 3 run; the claim becomes "per-turn selection over a trained checkpoint", compared on one harness with EnvScaler, EnvACE and AWM. CrEST's weights, if public, join them.
2. P2 fails, or the gate stops it: **selection doesn't add to a good trained checkpoint.** That closes the line. The agent-loop result in the report is then the format fault, the checkpoint comparison and the compounding model, reported as negative for selection.

### MT-FC-KEEP results (2026-11-07 05:0x UTC; EnvScaler T, seed 1, 800 items, 32,768 context; paired)

Kept reasoning against dropped: **51.5 vs 50.6, +0.9 [−1.8, +3.5]**; base −2.5, long context −1.5, miss func +1.0, miss param +6.5 [+0.6, +12.4]. Overflows 44 vs 43.

- **KEEP-P1:** in the expected range, and the lower bound is not above 0. **By the registered decision, the rows stand, and later native rows stay with reasoning dropped,** which is also EnvScaler's stated setting. MT-FCS's online arm runs that way, matching its verifier's data.
- **KEEP-P2 was wrong in a useful way:** tokens fall, not stay: **−1.58k [−1.96k, −1.20k] per conversation, 5.69k against 7.27k (−22%)**, utility +1.67 [−0.99, +4.32]. A model that keeps its reasoning doesn't rethink at each step. So kept reasoning gives the same accuracy at a fifth fewer tokens on this checkpoint, on one seed. I did not register this. It is a candidate for a cheaper form once the selection question settles, and is not adopted now.

Also: the 65,536 rerun's first submission failed in 51 s (job 1345258), because vLLM refuses a length above the configured 40,960 positions without `VLLM_ALLOW_LONG_MAX_MODEL_LEN=1`. Resubmitted as 1345397. MT-FCS's verifiers are training (1345398, 1345399).
