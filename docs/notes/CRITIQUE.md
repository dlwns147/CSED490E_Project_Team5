# Constructive critique of the project (2026-10-16, requested by the user; checks run the same day)

Each item: the problem, the evidence (checked, not assumed), how much it matters, and the fix or test. Ordered by importance.

## 1. The story is a collection; the unifying claim is "the check is the bottleneck" (high)
Five findings, ten baselines and fourteen method tests read as a catalogue. Across them, one pattern decides almost every result:
every cheap fix (sample + check, repair, cascades, routing, reuse) is only as good as the label-free check behind it, and the check
misses consistent errors. Evidence: N10 / N11 (9 of 37 Qwen3-32B geometry failures pass the metamorphic check; routing loses to a
fixed default), N8 (examples-gated cascade −3.4 points vs always-high), V1A (label-free reuse only where the model can write an
oracle); and the positive side, N12 / N13 (a *different* second opinion, from another tool condition or a brute-force oracle,
recovers those points). **Fix:** make this the thesis; present the fix map as "which check can see which failure".

## 2. "Verify once, reuse" is not new as an idea (high, for the novelty claim)
Close 2026 preprints write one solver per problem family and run it on every instance (arXiv 2605.14141, 2608.27296; RL for reusable
solvers). **Fix:** claim only what is measured here (per-instance vs reuse gap 7% vs 94%, the answer-free check, the cost rule,
facts raising the working share, size transfer) and cite them; the compact proposal still lists reuse under "our methods"
(writing session's decision). Details: docs/notes/RELATED_WORK.md (2026-10-16 entry).

## 3. F1 (unneeded helpers hurt) is shrinking with newer models (high, for relevance)
Checked: with the K8 toolbox, gpt-oss-20b gets 98.1% and Qwen3.6-35B-A3B 98.1% of the 108 N10 geometry items (Qwen3-32B: 65.7%);
removing the toolbox does not help them (−0.9 / −8.3 points). The harm is a property of older / non-reasoning models.
**Fix:** state it in F1 ("strong for Qwen3 ≤ 32B and Llama without thinking; absent for gpt-oss and Qwen3.6"); the hidden-contract
trap (F2) is the model-independent part (it hit gpt-oss and Qwen3.8 on Solomon too) and should lead.

## 4. Cost counts output tokens only (medium)
Checked: the optimization prompt with BM25 top-3 snippets is 4.8k characters, 1.8 × the short reference sheet (2.7k) and 3.6 × no
documentation (1.3k); helper toolboxes and "show the input" also lengthen the prompt. Execution cost is not counted either: reuse runs
16 candidates × 8 instances with up to 90 s each (≈ 3 CPU-hours worst case), the metamorphic check 7 runs per program.
**Fix:** report input tokens (prefill) and CPU seconds next to output tokens in the main tables; conclusions that hinge on a few
hundred output tokens (snippets vs sheet) must be re-stated with both.

## 5. Small synthetic suites; differences of 1–4 items (medium)
N10 has 108 + 100 items (12 per task). Checked: N12 vs always-thinking on Qwen3-32B geometry is 3 vs 1 items (sign test p = 0.62):
the defensible claim is "same accuracy at 61% of the tokens", not "more accurate". **Fix:** paired tests and CIs in every
comparison table; seeds 2–3 (running) before any positive claim; more instances per task (cheap) for the policy comparisons.

## 6. Contest set: contamination cannot be excluded (medium)
All 311 problems are from contests ≤ 1622 (before 2022), older than every model's cutoff. Checked a proxy: no age gradient within
rating bands (rating < 2000: 81.1% for contests < 1200 vs 83.3% for ≥ 1200; ≥ 2000: 42.8% vs 37.8%; gpt-oss-120b medium, 3 seeds),
so no sign of memorisation, but no proof either. **Fix:** say so; a post-cutoff set would need hidden tests we do not have (the N5
oracles could serve as approximate tests for new problems, with their 7% false-alarm rate stated).

## 7. Pre-registered bounds missed "on tokens" four times today (process, medium)
N11, N12 (×3), N13 hit their accuracy targets but missed the token bounds. That is honest reporting, but the bounds were set without a
cost model. **Fix:** before each test, compute the token cost the policy needs from existing data (e.g. escalation rate × fix cost)
and set the bound from that; report the accuracy–token frontier, not a single pass / fail.

## 8. Process: estimated timestamps (low, fixed)
Several 10-16 entries carried clock times estimated up to 30 min late; corrected from queue_log. **Fix (applied):** take the time
from `date -u` when writing.

## 9. Single prompt template on the hard benchmarks (low)
Prompt paraphrases were tested on the synthetic tasks only. **Fix:** one paraphrase run of the key contest / Solomon arms before
the final write-up.

## What to test next (pre-register each)
1. N12 replication (seeds 2–3, running) and the Qwen3.6 thinking re-run (48k cap, running).
2. N13b: a cheaper oracle gate (write the oracle only when the medium program passes the examples; reuse one oracle across runs).
3. Reuse under a changed rule (CVRP → VRPTW, + max route length, job-shop + release dates): edit the verified program and re-check,
   vs write from scratch (read arXiv 2606.04816 in full first).
4. Report input tokens and CPU time in the N10–N13 tables (item 4).

## Update 2026-10-16 10:30 UTC: item 4 measured (Qwen3 tokenizer, instance 0 of every size)
Input tokens per prompt, optimization: no documentation 488, reference sheet 901, exact snippet 701, BM25 top-3 1,138, sheet + literal
input 1,089. Geometry: task text 107; the K8 toolbox adds 912, the needed helpers only 113, the literal input 70.
Effect on the conclusions: none reverses. BM25 snippets cost +237 input tokens over the sheet for +8 to +27 points; removing the
geometry toolbox also saves ≈ 0.9k input tokens per call (so "remove" is cheaper than the output-only tables show); the agreement gate
(N12) pays the input of two prompts per item. Input tokens are usually priced several times below output tokens and are cacheable
across instances of one problem, so output tokens stay the main cost axis; tables will list both from now on.

## Update 2026-10-16 11:30 UTC: new points from N12–N14c
10. **Fixes are model-specific, so the map must say for which model (high).** Thinking is the best expensive fix for Qwen3-32B
    (geometry 97–99%) and a fix to avoid for Qwen3.6 (27% of geometry items exceed 48k thinking tokens, no gain over 98.1% without
    it); a distant source program helps nothing for Qwen3-32B but HURTS gpt-oss-20b (TSP → CVRP 13 vs 24 / 36). **Fix:** every
    FIX_MAP row gets the models it was measured on; no row is stated model-free unless it held on ≥ 3 model families.
11. **The strongest new positive (N14c) rests on one rung and one rule type (medium).** Adapting a verified job-shop program to
    release dates works (Qwen3-32B 30 vs 4 / 80, gpt-oss-120b 80 vs 72 / 80), CVRP → VRPTW works only with the snippet, TSP → CVRP
    does not. The working rule ("transfer works when the new rule needs no API fact the program lacks") is a post-hoc reading of
    three rungs. **Fix:** pre-register it as a prediction on new rungs before claiming it (e.g. job-shop + due dates / tardiness
    objective = needs no new API; flexible job-shop = needs optional intervals, a new API fact).
12. **Edit discipline is an unmeasured confound in every repair / adapt result (medium).** Models rewrite verified lines (7 / 24 VRPTW,
    50 / 80 job-shop crashes). Repair results (N2, N9) may hide the same damage. **Fix:** N14d tests a minimal-edit instruction; a diff
    statistic (verified lines changed) should be reported for repair and adaptation runs.

## Update 2026-10-22 (Slurm side, review): items 4 and 5 on the held-out benchmarks
- Item 4 (input tokens) measured on all held-out cells (OptMATH, OptiBench, BWOR, LogiOR): counting input tokens, fact-first-then-think costs
  37–97% of always thinking's tokens (output only 28–91%); no comparison reverses (FINDINGS 2026-10-22 06:2x).
- Item 5 (uncertainty): analyze_ho.py prints paired bootstrap 95% CIs; several held-out "wins" are ties (OptMATH Qwen3 models, OptiBench
  Qwen3-8B without the library, BWOR / LogiOR for the two stronger models); significant: OptiBench gpt-oss-20b / Qwen3-14B-AWQ, the library
  recipe on OptiBench for all three models, Qwen3-14B-AWQ on LogiOR with the library; significantly worse: Qwen3-8B on BWOR and held-out geometry.
- Thinking baseline: Qwen3-14B-AWQ's weak thinking on OptiBench is invented API calls (real), not a harness artifact; cap hits handicap
  always-thinking only where it already wins (Qwen3-8B).
