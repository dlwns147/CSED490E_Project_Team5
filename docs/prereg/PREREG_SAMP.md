# Pre-registration SAMP: is Qwen3.5-9B's result the short think, or how each arm is sampled?

Written 2026-10-27 14:3x UTC, before any run; design revised 14:4x UTC after the related-work check (below), still before any run.
Results go below.

**Why it could change the claim.** Reading TC-1's raw rows showed that the arms of Qwen3.5-9B are not sampled alike: the full think
(`llm.chat(think=True)`) runs at the model card's *general* thinking preset (temperature 1.0, top-p 0.95, top-k 20, presence penalty
1.5; POC_THINK_SAMPLING), while the 2,000-token cut think (`budget_chat`, raw completions) and the non-thinking answer run at the harness
sampling (temperature 0.7, top-p 0.95, no top-k, no penalty). This has held since HO-N for every short-think arm of Qwen3.5-9B and
Nemotron-3-Nano (card: temperature 1.0, top-p 1.0 for reasoning); HO-4K's "model-card thinking sampling" for the budget arm was wrong
(both budgets ran at the harness sampling, so HO-4K's own comparison is matched). On tool calls Qwen3.5-9B's full think is 4.6 points
*below* its non-thinking answer on non-live and 3.3–4.1 below its cut think (TC-1), copying BFCL's format template (`[func_name1=…]`,
`params_name1=…`) in 16% of thinking outputs vs 12% of the others. On the word problems the recipe's claim for Qwen3.5-9B is a saving:
short think → think → retry matches the check-matched think (+0.0 to +1.4 points) at 49–81% of its tokens. Two things could be wrong:
the cut think's edge may be its lower temperature and missing penalty, and the full-think baseline may be handicapped by a preset the
card does not recommend for code.
**Prior work (related-work check, 14:4x UTC).** The Qwen3.5-9B card gives thinking presets per task: general T 1.0 / top-p 0.95 / top-k 20
/ presence 1.5, and for *precise coding* T 0.6 / top-p 0.95 / top-k 20 / presence 0 (non-thinking general: T 0.7 / top-p 0.8 / top-k 20 /
presence 1.5); it warns that a higher presence penalty "may occasionally result in language mixing and a slight decrease in model
performance". The Qwen3 report (2505.09388 §4.6) evaluates thinking at T 0.6 / top-p 0.95 / top-k 20, presence 1.5 only for creative
writing. Nemotron-3-Nano's card: T 1.0 / top-p 1.0 for reasoning, T 0.6 / top-p 0.95 for tool calling. In vLLM the presence penalty
counts only generated tokens, so names written in the think are penalized in the answer while the prompt's template placeholders are
not (our inference). Sampling moves reasoning accuracy a lot: temperature 0 → 1 by up to 15 points, top-p by up to 8 (A Sober Look,
2504.07086), different temperatures solve different problems (2510.02611); a repetition penalty cut HumanEval 0.301 → 0.092
(2505.10402, a multiplicative penalty). Budget-forcing studies mostly match decoding across arms (Coupling Tax 2605.07686 and HRBench
2605.28398 greedy in both modes; ThinkBrake official settings for all), but DART (2606.23181) drafts at T 0.6 and thinks greedily,
unremarked; none reports the mismatch as a confound. No study of models copying BFCL's placeholders was found.
**Run.** (a) Word problems, every thinking arm of Qwen3.5-9B at the card's precise-coding preset (T 0.6, top-p 0.95, top-k 20, no
presence penalty; tag q35c): the 2,000-token cut think with the fact (`POC_BUDGET_CARD=1`, both of its calls; mode formxtb2000c) and the
full think with the fact (formxt, 32k), on BWOR and LogiOR (the benchmarks with the most tokens at stake), seeds 1–3, one RTX 3090 per
benchmark and seed (`hon_lane.sh codepreset <set> <seed>`, 6 jobs); the cheap rows are q35's. Analysis `python3.11 poc/analyze_ho32.py
--samp`: SB→T→T vs T→T at the coding preset, T→T at the coding vs the general preset, the first program and the full think alone.
Extension rule fixed now: if P1 holds on one benchmark and not the other, OptiBench third and OptMATH run the same way. (b) Tool calls,
a 2 × 2 of mode (full think / cut think) × sampling (card general / harness) for Qwen3.5-9B on the 3,482 TC-1 items, seeds 1–3: the two
new cells are Th = the full think at the harness sampling (tag q35h, `hon_lane.sh tch bfcl <seed>`) and SBc = the cut think at the
card's general preset (tag q35sbc, `hon_lane.sh tcsbc bfcl <seed>`); graded as TC-1; `python3.11 poc/analyze_tc.py --samp`. λ = 0.5,
paired 95% intervals over problems / items.
- **SAMP-P1 (the saving survives an on-card matched preset):** at the coding preset, SB→T→T is within 1.0 point of T→T's accuracy (or
  above) at ≤ 85% of its tokens, on both BWOR and LogiOR.
- **SAMP-P2 (the baseline was not handicapped):** T→T at the coding preset is at most 2.0 points more accurate than T→T at the general
  preset, on both benchmarks.
- **SAMP-P3 (tool calls, harness sampling: the mode does not matter):** |Th − SB| ≤ 1.0 point on both splits.
- **SAMP-P4 (tool calls, card sampling: the mode does not matter):** |SBc − T| ≤ 1.0 point on both splits.
- Reported, no decision: template copies per cell of the 2 × 2; tokens of each arm; the first program's accuracy at each preset.
**Decision.** P1 and P2 → Qwen3.5-9B's word-problem result stands at an on-card matched preset; the REPORT's methods state each arm's
sampling, nothing else changes. P1 refuted → the recipe's saving for Qwen3.5-9B depends on the cut think's sampling: the claim for this
model is restated, and Nemotron-3-Nano (the same mismatch) is tested the same way on 4 × RTX 3090 with its card's presets (pre-registered
now, same predictions). P2 refuted → the full-think baseline for Qwen3.5-9B was handicapped by the general preset; every Qwen3.5-9B
comparison against thinking is restated with the coding preset (and the coding preset becomes the default thinking sampling for code).
P3 and P4 → on tool calls Qwen3.5-9B's "thinking is worse than not thinking" is the sampling, not the mode (TC-1's statement for it is
corrected); P3 or P4 refuted → the mode matters at matched sampling, reported with the template copies.
**Smoke.** None: every arm reuses code that ran in TC-1 / HO-SB; the first rows of each job are read (sampling parameters reach the
server, the fact matches q35's `fact_from`) before the results are used.

*Submitted 2026-10-27 14:4x UTC: samp_{bwor,logior}_s{1,2,3} (1261670–1261675), samp_tch (1261676), samp_tcsbc (1261677), `-x n19`.*
*First rows read (2026-10-27 14:5x UTC, before any result is used): the coding-preset full thinks carry the same fact as q35's rows
(`fact_from` identical in 43 of 43); with the client replaced by a recorder, `budget_chat` (both calls) and `llm.chat(think=True)` send
temperature 0.6, top-p 0.95, top-k 20 and no presence penalty under the codepreset environment; the cut-think rows come later because the
server queues them behind the 32k thinks (4 running, KV 89%). Tool-call cells: 2.5k / 2.3k of 10.4k rows after 15 minutes, 0 failures.*


### Results SAMP (b), tool calls (2026-10-27 17:1x UTC; `python3.11 poc/analyze_tc.py --samp` after `grade_tc.py q35h` / `q35sbc`; 3,482 items × 3 seeds, all rows, 0 failed requests)
| split | N (harness) | SB (cut, harness) | Th (full, harness) | SBc (cut, card) | T (full, card) | template copies N / SB / Th / SBc / T |
|---|---|---|---|---|---|---|
| non-live (1,240) | 81.5% | 80.2% | 79.8% | 77.1% | 76.9% | 8.4 / 11.5 / 12.0 / 12.9 / 15.1% |
| live (2,242) | 61.4% | 71.3% | 72.1% | 68.8% | 67.2% | 13.3 / 12.5 / 12.4 / 14.6 / 16.8% |
- **SAMP-P3 holds (2 / 2):** at the harness sampling the mode does not matter: Th − SB −0.5 [−1.5, +0.5] non-live, +0.8 [−0.1, +1.7] live.
- **SAMP-P4 refuted (1 / 2):** at the card's general preset the cut think stays ahead on live: SBc − T +0.2 [−1.1, +1.5] non-live, **+1.7
  [+0.7, +2.7]** live.
- What moves accuracy is the sampling: the card's general preset (T 1.0, top-k 20, presence penalty 1.5) costs the full think 2.9
  [+1.7, +4.2] (non-live) and 4.9 [+3.9, +6.0] (live) points and the cut think 3.2 / 2.5 against the harness sampling (T 0.7, top-p 0.95).
  At matched harness sampling thinking vs not thinking is −1.7 [−3.4, +0.3] on non-live (TC-1 reported −4.6 with the mismatch) and +10.7
  [+8.9, +12.4] on live. Tokens barely move (full think 0.32k card / 0.34k harness; cut think 0.29k / 0.30k).
- Raw rows: where the two presets disagree on the full think, the harness one is right on 1,105 items and the card one on 666; on the
  1,105, the card's answer copies BFCL's template (`func_name1=`, `params_name1`) in 640 and 584 of them do not decode at all; on the 666
  the harness answer copies it in 295. Copying the placeholders is the main way either preset fails; the general preset does it more
  (15.1 / 16.8% vs 12.0 / 12.4%). This fits the presence-penalty reading (the penalty counts the think's own tokens, including the real
  function names, not the prompt's placeholders) but the run does not separate the penalty from the temperature.
- **Decision as registered (P3 holds, P4 refuted):** the mode matters at matched sampling only at the card's preset on live (+1.7 for the
  cut think), reported with the template copies; at the harness sampling it does not. TC-1's description of Qwen3.5-9B is corrected in
  the REPORT: most of its "thinking is worse" (non-live −4.6) is the card's general preset, not the mode (−1.7 [−3.4, +0.3] at matched
  sampling). TC-1's registered verdicts stand as scored (they compare policies, each with its arms' sampling as run).
- Related work: the size of the effect (3–5 points from the preset, more than the mode's) is in the range A Sober Look (2504.07086)
  reports for temperature and top-p on reasoning benchmarks, and agrees with the Qwen3.5-9B card's own warning that a higher presence
  penalty can lower performance; the Qwen3 report evaluates thinking at T 0.6 without a presence penalty except for creative writing.
  No prior report of models copying BFCL's prompt-mode placeholders was found; we report it, not its cause. Part (a) (word problems)
  is still running.

### Results SAMP (a), word problems (2026-10-27 19:4x UTC; `python3.11 poc/analyze_ho32.py --samp`; BWOR 82 / LogiOR 92 problems × 3 seeds, all rows, 0 failed requests)
| benchmark | SB→T→T, coding preset | T→T, coding preset | difference (tokens) | T→T, general preset (as run) | T→T coding − general | full think alone coding − general | full thinks at the 32k cap, coding / general |
|---|---|---|---|---|---|---|---|
| BWOR | 54.5% @ 22.3k | 49.2% @ 33.0k | **+5.3 [+0.8, +9.8]** (68%) | 53.7% @ 30.7k | −4.5 [−12.6, +3.3] | −5.7 [−11.8, +0.4] | 95 / 44 of 246 |
| LogiOR | 52.2% @ 31.7k | 44.9% @ 42.8k | **+7.2 [+2.9, +12.3]** (74%) | 51.1% @ 39.0k | −6.2 [−13.0, +0.7] | −6.9 [−13.0, −1.1] | 149 / 90 of 276 |
- **SAMP-P1 holds (2 / 2):** at an on-card preset matched across every thinking arm, short think → think → retry is above the
  check-matched think (+5.3, +7.2) at 68–74% of its tokens.
- **SAMP-P2 holds (2 / 2):** the general preset did not handicap the baseline; the coding preset is *worse* for the full think (−4.5 /
  −6.2 for T→T, −5.7 / −6.9 for one think).
- Mechanism, from the rows: at the coding preset (T 0.6, no presence penalty) the full think runs to the 32k cap without a program about
  twice as often (95 vs 44, 149 vs 90); the runs that finish are not worse. The card itself says the presence penalty is there "to reduce
  endless repetitions" (Qwen3.5-9B README, verified). The short-think-first policy is unmoved by the preset (54.5 vs 54.9%, 52.2 vs
  52.5% as run before), and the first program at the coding preset is as good or slightly better (42.3 vs 39.0%, 39.1 vs 37.3%).
- **Decision as registered (P1 and P2):** Qwen3.5-9B's word-problem result stands at a matched on-card preset; the REPORT's methods state
  each arm's sampling. The comparison the report makes (against the general-preset think) is the conservative one: it is the stronger
  baseline. Nemotron's conditional test is not triggered.
- Across both halves: the preset matters in opposite directions by task — on 0.3k-token tool-call thinks the general preset (presence
  penalty 1.5) costs 3–5 points through copied placeholders; on 20–30k-token program-writing thinks the coding preset (no penalty) costs
  5–7 through capped thinks — while the recipe's cascade is robust to it. Related: A Sober Look (2504.07086) on sampling sensitivity;
  HO-CAP (a capped full think flatters a short think first) — here the general preset is the one with fewer caps. Consequence for LC-1
  (Qwen3.5-9B was set to the coding preset): amended, PREREG_LC.md.
