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
