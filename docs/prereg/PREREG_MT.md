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
