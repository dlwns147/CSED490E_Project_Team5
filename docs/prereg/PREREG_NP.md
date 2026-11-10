# PREREG_NP: the count gate on trip planning (NaturalPlan), registered 2026-11-10 15:1x UTC before any run on the test sample

**Why.** The paper's claim is that a cheap translation plus a free solution-count check, escalating to thinking when the check fails, beats thinking alone. So far it is tested on logic grids (ZebraLogic, GridPuzzle, Mitra-Baral). The closest paper, Amonkar et al. (2505.13252, RELATED_WORK), finds LLM-as-formalizer below LLM-as-solver most consistently on NaturalPlan's Trip Planning ("on the more challenging Trip Planning dataset, LLM-as-formalizer consistently underperforms LLM-as-solver", their section 5.1). They never count solutions and never fall back to solving.

Trip Planning is a planning task, not a grid. NaturalPlan builds each trip "with enough constraints that there is only one solution" (Zheng et al. 2406.04520, section 2.1.1, read 2026-11-10). We checked this on Amonkar et al.'s 100 trips with their structured constraints, reading a dated event as lying inside that city's stay and parsing one-way flights ("from A to B") from the prompt: 95 have exactly one valid plan, 3 have two, 2 have three. (Reading a dated event as only overlapping the stay leaves 36 unique, so the "inside" reading is the task's.) This makes Trip Planning a second domain where the gate applies, and it is the domain where the closest paper's verdict is most negative.

An earlier note (RELATED_WORK, 2026-11-10 13:0x) said the count gate does not apply on NaturalPlan. That holds for Meeting Planning (maximize friends met, many plans) and not for Trip Planning.

**Interface (domain-general, `poc/run_plan.py`).** The model writes an OR-Tools CP-SAT model `m`, a dict `ANSWER` of the variables that decide the answer, and `plan(val)`, which renders the answer. The harness counts distinct rendered plans: it blocks each found assignment of `ANSWER` until a different plan appears or none is left. Nothing in the harness is specific to trips. The same three names fit any constraint problem with a unique answer.

**Data.**
- Test: Amonkar et al.'s exact 100 trips (github.com/rikhil-amonkar/llm-csp, data/trip_planning_100.json), 3–10 cities.
- Dev, for a format check only: the first 30 other NaturalPlan trips, Qwen3-8B, seed 1. No prompt change after the first test run.
- Prompt: NaturalPlan's 5-shot prompt as is. Its examples fix the day convention (a flight day counts for both cities). Our instruction follows the task.
- Amonkar et al. use a one-shot prompt that shows the format only. So their accuracies are context, not a matched baseline. Our comparison is within our runs, on the same prompt.

**Runs.** Seeds 1–3 each.
- Arms:
  - `tr`: no thinking, 4,096 tokens, up to 3 rounds, with generic count feedback ("allows no plan / more than one plan, so one constraint is wrong / missing").
  - `trt`: thinking, 16,000 tokens, up to 3 rounds.
  - `think`: thinking, 32,000 tokens, answers a JSON plan.
- Models:
  - Qwen3-8B (tag `q8b`, 1 × RTX 3090), first.
  - Qwen3-32B-AWQ (tag `q32`, 2 × RTX 3090), when the ZL-AM lane frees its GPUs.

**Ladder.** Run `tr`. If its count is not 1, run `trt`. If that count is not 1, answer with `think`. All tokens are paid. Utility = 100·right − 0.5·ktok, where right means the plan equals NaturalPlan's gold plan. We also report plans that satisfy every annotated constraint (Amonkar et al.'s metric) as a second column. Bootstrap over trips, 95%. Strata: 3–4, 5–6, 7–8 and 9–10 cities.

**Predictions (each model separately; Qwen3-32B decides).**
- NP-P1 (gate validity): count-1 precision of the translations (`tr` and `trt` passes pooled) at least 95%.
- NP-P2: ladder − think utility, interval above 0.
- NP-P3: on trips of 7–10 cities, ladder − think accuracy, lower bound above 0.
- NP-P4 (Amonkar et al.'s verdict, replicated in our setup): `trt` alone, scored as is (count 1 gives its plan, otherwise wrong), has accuracy at most think's + 2 points.

**Decision.**
- P1 and P2 hold → the claim "a count gate plus escalation turns formalization from a loss into a win" carries to planning, on the closest paper's own sample and its most negative domain. It goes in the report as the second domain beside ZL-AM.
- P4 also holding → the win comes from the gate and the escalation, not from a better formalizer.
- P1 fails → translations pass the count while wrong on this task. The gate does not carry, and we report the domain as a negative result.
- P2 fails with P1 holding → thinking alone is enough here, and the claim is limited to the domains where it holds.

## Addendum NP-HW, written 2026-11-10 17:1x UTC, before any test-sample run

- **Hardware.** The runs move to gs15 (RTX PRO 6000 Blackwell, 96 GB, one GPU per model; user 2026-11-11). The image and vLLM version are the same as on Slurm. Qwen3-32B stays the AWQ checkpoint, as registered, on one GPU.
- **Dev pilot fix (format only).** The first pilot programs indexed `val[name]` and left out the import. The harness now accepts both `val(name)` and `val[name]`, and imports cp_model before the program. The prompts are unchanged.
- **Reported rows, not deciding.** These rows test whether the gate still pays for stronger reasoning models: Amonkar et al.'s formalizer loses most against strong reasoners.
  - Models: gpt-oss-20b (tag `oss20`) and gpt-oss-120b (tag `oss120`).
  - Reasoning effort: low for `tr`, high for `trt` and `think`.
  - Read with the same ladder and P1–P4 lines.

## Addendum NP-DAY, written 2026-11-10 17:3x UTC, after the dev pilots and before any test-sample translation

**Dev pilot, Qwen3-8B, 30 trips spread over 3–10 cities.** In both interfaces, the quick translation reached exactly one plan on 0 of 30 trips:
- CP-SAT interface: 17 trips had no plan, 11 programs crashed, 2 had several plans.
- Declarations interface (`trc`, below): 5 had no plan and 9 crashed.

**Root cause, read in the programs** (`tmp/why0.py` on gs15: run each zero-plan program's checks on the gold plan):
- In 5 of 5 zero-plan declarations every check is true on the gold plan, but the candidate generator never yields it. The generator starts the next city on the day after the previous stay ends. NaturalPlan's convention is that the flight day counts for both cities, and the prompt shows it only through the five worked examples.
- In the CP-SAT programs, the quick model also fixes the city order in its head (Amonkar et al.'s "hard-coded" failure).

**Changes, the same for every arm, thinking included:**
1. **The convention is stated in the task.** One sentence follows the task's last line: "A day on which you fly from one city to another counts as a day in both cities, so the next city's stay starts on the day the previous stay ends."
   - The 8 test-sample thinking runs already started under the old prompt are kept apart as `think0` and are not used.
2. **Ladder steps change.** The ladder's translation steps become `trc` (quick) and `trct` (thinking, 16,000 tokens).
   - Each step is a declarations-only translation. `candidates()` yields every answer of the right form, and `constraints` holds one check per stated requirement. The harness enumerates the answers and counts those that pass. Nothing in it is trip-specific.
   - The CP-SAT arms `tr` / `trt` are dropped.
   - `constraints` may also be a function that returns the list.
3. **Predictions P1–P4 are unchanged**, with `trc` / `trct` in place of `tr` / `trt`.

**Before the test translations:** a second dev pilot on the same 30 trips (tag `q8b3`, and `oss20` for format) runs under these changes. The test translations start after it is read for format and crashes only.

## Addendum NP-DP, written 2026-11-10 18:5x UTC, before any `trct` test run finished (Qwen3-8B and Qwen3-32B at 33–49 of 100 trips) and before any number below was computed, except the one disclosed

**Why.** Draft-and-Prune (2603.17233, RELATED_WORK 2026-11-10 18:5x) publishes the closest mechanism: several formalizations, keep those with exactly one answer, majority vote, fall back to chain-of-thought. A reviewer will ask whether our one-translation ladder beats it, and whether it beats self-consistency of thinking at its tokens.

**Reported rows, not deciding (P1–P4 and the decision rules are unchanged):**
- **D&P-3:** for each trip, the three seeds' `trct` runs; keep those with count 1; majority of their plans (ties: lowest seed); if none survives, thinking seed 1. Tokens: all three `trct` runs, plus thinking when used. Compared with the ladder of each seed and with `think`, utility and accuracy, bootstrap over trips.
- **SC-3:** majority of the three `think` plans (ties: lowest seed), tokens of all three. **Disclosure:** SC-3 accuracy was computed once, exploring, at 18:4x UTC, before this addendum: Qwen3-8B 37%, Qwen3-32B 59%, gpt-oss-20b 87%, gpt-oss-120b 80% (single `think` 33.3, 47.0, 71.3, 76.7%).
- D&P's own setting (k = 10–20 drafts conditioned on plans) is not run. At our token price, k translations at Qwen3-32B's `trct` cost (7.5k tokens each) cost 0.5 · 7.5 · k = 3.75k utility points per trip, about 37 points at k = 10, so it cannot beat the ladder on utility unless it is about 37 points more accurate. We report this arithmetic, not a run.

## Addendum NP-FIX, written 2026-11-10 19:5x UTC: two harness faults found in the test runs, fixed; affected rows rerun

1. **A false-pass bug in the declarations harness** (addendum NP-DAY allowed `constraints` to be a function). When `constraints(answer)` takes the answer and *returns* the list of checks, the harness took the function as one check, and a non-empty list counts as true, so every candidate passed. Re-running every stored final program under the fixed harness (`run_plan.py --rescore`, no model call, results/np_rescore.jsonl): only gpt-oss-20b's quick translation is affected (count-1 rows 115 → 59; 56 of its 65 wrong passes were this bug); no other model's or arm's count changes. The three `oss20 trc` runs are set aside as `trcbug` and rerun with the fixed harness (repair rounds depend on the counts, so re-scoring alone is not enough).
2. **Context overflow in repair rounds.** Two Qwen3-8B `trct` runs (seeds 1 and 2) stopped at 81 and 69 of 100 trips when a repair round's history passed the 40,960-token context. As on the grids, a failed request now ends that trip's rounds (the last count stands); the missing trips run with `--resume`, which keeps the rows already written.
Predictions, arms and decision rules are unchanged. The harness now also records how many candidates each program enumerated (`n`).
