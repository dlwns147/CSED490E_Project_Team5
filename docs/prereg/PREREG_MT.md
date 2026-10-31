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
cancelled jobs (checked on n20, n24, n25, n27; n26 pending).
