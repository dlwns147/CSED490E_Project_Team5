# Pre-registration N10: can the choice of tool / fix be made automatically, per problem, from the first failure?

Written 2026-10-16 08:33 UTC, before any run. Results go below this section; this section is not edited afterwards.

**Why.** The project's practical output is a failure → fix map (docs/notes/FIX_MAP.md), but the map is applied by hand. The one automatic
test so far (N7, contest problems) had only two fixes (repair, more effort) and found nothing to route. Here every failure type the map
names can occur, and the menu mixes *content* fixes (remove the tools, let the model choose its tools, show the literal input) with
*compute* fixes (sample + check, plan first / repair, thinking). Question: does a router that reads the first attempt's label-free
failure signal pick a fix well enough to beat the best single fix, and how close does it get to an oracle that knows which fix works?

**Prior art (checked 2026-10-16).** Failure-Aware Enhancements (arXiv 2602.02896): a hand-made decision framework mapping failure
patterns to methods (GitHub projects, no automatic router). Iterative self-repair across scales (2604.10508): repair rates depend on the
error type; suggests sampling for assertion failures. Adaptive-Solver (2310.01446): answer-consistency gate, then switch model / prompt /
decomposition (our N3-style cascade). Self-PR (AAAI 2026): learned selector over plans. Tool retrieval (DTDR 2512.17052, Tool RAG):
irrelevant tools mislead. Not covered: an automatic, label-free router over both content fixes and compute fixes, chosen on other tasks
(leave-one-task-out) and priced in tokens against an oracle, on tasks with exact answers.

**Design (Qwen3-32B-AWQ, no thinking unless the fix is thinking, T = 0.7, --stdlib).** All arms run on the same instances.
- Geometry: 9 tasks (hull, area2, pip, segs, close, lattice, rectunion, delaunay, diameter), 2 sizes × 6 instances = 108 items.
  First attempt = the realistic default: the needed helpers + 8 related extra helpers in the prompt (K8), seed 1.
- Optimization: 8 problems (knapsack, tsp, color, sched, binpack, vcover, cvrp, vrptw with the unambiguous header), 4 instances per size
  = 100 items. First attempt = the full OR-Tools reference sheet in the prompt, no repair, seed 1.
- Fix menu (general: none needs the answer or task-specific human knowledge):
  1. sample + check: seeds 2 and 3 of the first-attempt condition, choose by the label-free check (geometry: metamorphic consistency
     as poc/mr_select.py; optimization: feasible, then best objective);
  2. remove the context: no helpers / no documentation;
  3. let the model choose its tools: geometry `--autoscope` (the model picks helpers from the same pool); optimization BM25 top-3
     snippets (`--retrieve 3`);
  4. show the literal input (`--show_stdin`);
  5. geometry: plan first (`--self_hint`, the model names its algorithm, then codes); optimization: one repair round with the
     error / infeasibility feedback (`--repair 1`);
  6. thinking (16k cap).
  Reference arm, not in the menu (needs a human to know what is needed): needed helpers only (K0) / the problem's exact snippet.
- Scoring: geometry strict (correct on all 8 copies); optimization optimal. Tokens: all output tokens of every call used (tool-picking
  call, repair rounds, thinking included). The label-free check never sees the answer.

**Policies (computed offline once all arms exist; script poc/analyze_n10.py).**
- Always-fix-k and gated-fix-k (apply fix k only when the first attempt fails the check).
- Cascade: on a failed check, try fixes from cheapest to most expensive (mean tokens on the other tasks) until one passes the check.
- **Learned router (the method):** signal of the first attempt = passes / no code / Python exception type / timeout / unparseable
  output / check failed (metamorphic inconsistency or infeasible). Leave-one-task-out: for the held-out task, each signal is sent to the
  fix with the highest success rate on that signal in the other tasks of the same domain (≥ 5 training items, else the best gated fix;
  ties to the cheaper fix). Variant: if the routed fix also fails the check, continue with the next fix in that learned order.
- LLM router (second stage, run after the arms): the model sees the task, its program and the check feedback, and names one fix.
- Oracle: per failed item, the cheapest fix that is correct.

**Predictions.**
- N10-P1: the oracle beats the best single gated fix by ≥ 10 points in each domain (there is room to route).
- N10-P2 (main): the learned router beats the best single gated fix by ≥ 3 points, or matches it (± 1 point) with ≥ 25% fewer tokens,
  in each domain.
- N10-P3: the learned cascade comes within 5 points of the oracle at ≤ 2 × the oracle's tokens.
- N10-P4: the LLM router is no better than the learned router.
- N10-P5 (tool selection): letting the model choose its tools is no better than removing them, and ≥ 5 points below giving exactly the
  needed tools (replicates S5 / B4 on this suite).
Positive claims need the second seed: if P2 holds on seed 1, the first-attempt and fix arms are re-run with seed 4 before claiming it.

## Results (2026-10-16 08:59 UTC; seed 1; poc/analyze_n10.py → results/n10_analysis.log)
Fix 3 for geometry was first run with a bug (the helper catalog lacked `in_circle`, the run crashed); fixed in geo_distractors.catalog
and re-run before any analysis. Accuracy @ mean output tokens per item:
| policy | geometry (108 items, 9 tasks) | optimization (100 items, 8 problems) |
|---|---|---|
| first attempt only (K8 toolbox / full manual) | 65.7% @ 0.6k | 58.0% @ 0.5k |
| always remove the context | **80.6% @ 0.4k** | 45.0% @ 0.6k |
| always let the model choose its tools | 65.7% @ 0.4k | 70.0% @ 0.5k |
| always 3 samples + check | 73.1% @ 1.7k | 70.0% @ 1.6k |
| always thinking | **97.2% @ 6.1k** | 68.0% @ 6.0k |
| reference: exactly the needed tools (needs a human) | 66.7% @ 0.3k | **78.0% @ 0.5k** |
| best gated single fix (in hindsight) | think 89.8% @ 2.5k | choose 76.0% @ 0.8k |
| single fix chosen on the other tasks | 89.8% @ 2.5k | 76.0% @ 0.8k |
| **learned router (by signal, LOTO)** | 88.9% @ 2.5k | 73.0% @ 0.8k |
| learned router + cascade | 91.7% @ 2.5k | 84.0% @ 3.6k |
| cascade, cheapest fix first | 84.3% @ 1.0k | 84.0% @ 3.4k |
| oracle (cheapest correct fix per failed item) | 91.7% @ 1.0k | 85.0% @ 0.8k |
- **P1 refuted** (oracle − best gated fix: geometry +1.9, optimization +9.0; not ≥ 10 in each). In geometry the room is in tokens
  (same accuracy at 40% of the tokens), not accuracy.
- **P2 refuted** (learned router −0.9 / −3.0 points vs the best single fix at equal tokens). Reading the signals: the error type does
  not say which fix works. Geometry: 17 of 28 failures are "check failed" and 7 NameErrors; thinking fixes 16 / 17 and 7 / 7, so every
  signal routes to thinking. Optimization: the best fix is set by the problem, not by the error (the 11 OR-Tools overload errors
  are CVRP / VRPTW, fixed only by retrieved snippets, 3 of 11), so a router trained on the other problems sends them elsewhere.
- **P3 refuted on tokens**: the learned cascade reaches the oracle's accuracy (91.7%) / 1 point below it (84.0%), but at 2.5 × / 4.6 ×
  its tokens (it ends in thinking).
- **P5 mixed**: geometry: the model's own tool choice (65.7%) is no better than the toolbox (65.7%) and 15 points below removing it
  (it keeps `polar_sort` for hull, as in F1); the "needed" set includes the trapped helpers (lattice and Delaunay 0 / 12), so it is no
  ceiling here. Optimization: BM25-chosen snippets (70%) beat both the full manual (58%) and no manual (45%), 8 points below the exact snippet.
- The gate itself limits every gated policy in geometry: 9 wrong first attempts pass the metamorphic check (consistent wrong
  algorithms: hull built on `polar_sort`, rectangle union), so always-thinking (97.2%) beats every gated policy (≤ 91.7%).
- P4 (LLM router) not run yet. Seed-4 replication not triggered (P2 failed).
**Conclusion for the fix map:** on this suite a per-problem *default* chosen by domain wins over per-failure routing: geometry → remove
the toolbox (80.6% at 0.4k) or think (97.2% at 6.1k); optimization → retrieve snippets (70% at 0.5k) and repair / resample on failure.
The error message is a poor guide to the fix; the problem type is a better one.

## N11 pre-registration (2026-10-16 09:00 UTC, before computing; offline on the N10 factorial): choose the fix per PROBLEM, by probing
N10 says the right fix follows the problem type, not the error. Policy "probe, then commit" (verify-once-reuse applied to the choice
of fix): for each problem type, run every whole-prompt option (first-attempt prompt, remove the context, model-chosen tools, literal
input, plan first / repair once, thinking, 3 samples + check) on a few probe instances (instance 0 of every size: 2 per geometry task,
3–4 per optimization problem); commit to the option with the highest label-free check pass rate on the probes (ties: fewer tokens);
use it on the remaining instances. Probe tokens are charged to the problem (spread over all its instances). Compared on the same
committed instances with every global default and with the per-problem oracle default (best option per problem in hindsight).
- N11-P1: geometry: within 2 points of always-thinking (97.2% overall) at ≤ 50% of its tokens; optimization: ≥ the best global
  default (70%) + 3 points at ≤ 2 × its tokens.
- N11-P2: within 5 points of the per-problem oracle default in each domain.

## N11 results (2026-10-16 09:01 UTC; results/n11_analysis.log)
| committed instances | geometry (90) | optimization (75) |
|---|---|---|
| **probe, then commit** (probe tokens charged) | 82.2% @ 3.2k | 74.7% @ 4.2k |
| per-problem oracle default | 98.9% @ 3.8k | 78.7% @ 1.5k |
| best global default | think 96.7% @ 6.2k (remove 78.9% @ 0.4k) | choose 72.0% @ 0.5k |
Picks: geometry remove × 5 (area2, hull, lattice, pip, rectunion), first, think (delaunay), input, choose; optimization choose × 4,
first × 2, sample, input. **N11-P1 refuted** (geometry 14.5 points below thinking; optimization +2.7 points at 8 × the tokens, the
probes themselves cost most: every option, thinking included, on 3–4 instances of a 12–16-instance problem). **N11-P2: refuted for
geometry (−16.7), holds for optimization (−4.0).** Why: two probes are too few and the check is blind to consistent errors (e.g.
rectangle union without helpers is correct on both probes but on only 2 of 10 committed instances, and 4 of the 8 wrong ones pass the
metamorphic check), so the cheap option wins the tie. The probe cost would shrink with more instances per problem (Solomon: 56);
the check blindness would not.
N10 stage 2 (P4, LLM router) started 09:02 UTC on GPU 1 (poc/queues/queue_s2_n10b.sh).

## N10-M2 pre-registration (2026-10-16 09:06 UTC, before running): does the per-domain default depend on the model?
Same factorial and analysis with gpt-oss-20b at low effort (the "thinking" fix = medium effort; 16k cap for every arm, since gpt-oss
reasons in every call). Tags S2_N10m2_geo_* / S2_N10m2_co_* (poc/queues/queue_s2_n10m2.sh, GPUs 0 and 2).
- M2-P1: unlike Qwen3-32B, removing the geometry toolbox gains < 5 points (gpt-oss ignores unneeded helpers, E2/O5).
- M2-P2: in optimization, retrieved snippets are again the best cheap default (≥ the full manual + 5 points).
- M2-P3: the learned router again does not beat the best single gated fix by ≥ 3 points (replicates N10-P2's failure).

## N10 stage 2 result (2026-10-16 09:04 UTC; results/n10_llm_router.log): the LLM router
Qwen3-32B reads its failed program and the check feedback and picks one fix: geometry 85.2% @ 1.7k (picks: think 15, input 10,
choose 3), optimization 69.0% @ 0.9k (picks: input 23, repair 18; never the retrieved snippets, the best fix there). **N10-P4 holds**:
below the learned router (88.9 / 73.0%) and the best single fix (89.8 / 76.0%). The model's own diagnosis favours "show the input"
and "repair", which rarely fix API-knowledge failures.

## N10-M3 pre-registration (2026-10-16 09:07 UTC, before running): a third model, Qwen3.6-35B-A3B-FP8 (no-think; thinking fix = thinking
on). 8k cap for the no-think arms (its no-think answers are long, H7), 16k for thinking. poc/queues/queue_s2_n10m3.sh, GPUs 1 and 3.
- M3-P1: the learned router does not beat the best single gated fix by ≥ 3 points (as N10-P2, M2-P3).
- M3-P2: retrieved snippets beat the full manual by ≥ 5 points in optimization.

## N10-M2 results (2026-10-16 09:30 UTC; gpt-oss-20b low; results/n10m2_analysis.log, n11m2_analysis.log)
| policy | geometry (108) | optimization (100) |
|---|---|---|
| first attempt (K8 toolbox / full manual) | 98.1% @ 0.9k | 80.0% @ 0.6k |
| always remove the context | 97.2% @ 0.5k | 69.0% @ 0.7k |
| always BM25 snippets / model-chosen helpers | 96.3% @ 0.5k | **88.0% @ 0.6k** |
| always 3 samples + check | 100% @ 2.6k | 93.0% @ 1.9k |
| always medium effort | 99.1% @ 1.3k | 84.0% @ 1.9k |
| best gated single fix | 100% @ 0.9k (any) | snippets 91.0% @ 0.8k; repair once 90.0% @ 0.7k |
| learned router (LOTO) | 100% @ 0.9k | 88.0% @ 0.8k |
| oracle | 100% @ 0.9k | 93.0% @ 0.7k |
| probe, then commit (N11) | 97.8% @ 2.1k | 88.0% @ 3.2k |
**M2-P1 holds** (gpt-oss ignores the toolbox: removing it changes −0.9 points; only 2 of 108 first attempts fail the check).
**M2-P2 holds** (snippets 88% vs full manual 80%, no manual 69%). **M2-P3 holds** (router 88.0% vs best gated single fix 91.0%).
No truncation (all 16k-cap calls finished). The per-domain default differs by model in geometry (Qwen3-32B: remove the toolbox or
think; gpt-oss: nothing needed), and is the same in optimization (retrieve the snippets; then repair or resample on failure).

## N12 pre-registration (2026-10-16 09:31 UTC, before computing; offline on the N10 factorials): agreement between tool conditions as the gate
N10 / N11 failed because the label-free check passes consistent wrong programs (9 of 37 Qwen3-32B geometry failures). Programs written
under DIFFERENT tool conditions tend to make different mistakes (hull with the toolbox builds on `polar_sort`, without it uses the
monotone chain). Policy AGREE: write program A under the first-attempt condition (toolbox / full manual) and program B under the cheap
alternative (no helpers / BM25 snippets); accept when both pass the check and give the same answer on the instance (geometry: same
output; optimization: both feasible with the same objective); otherwise escalate to thinking (the general expensive fix); if thinking
fails the check, keep a check-passing program among A, B (B first). Secondary: escalate to 3 samples + check instead. Prior art: the
mixture-of-thought cascade (Yue et al., ICLR 2024) gates escalation to a stronger LLM on agreement between CoT and program answers;
TroVE / MBR-exec vote across samples. Here: agreement across tool conditions gates more reasoning, priced in tokens.
- N12-P1 (Qwen3-32B geometry): ≥ 95% at ≤ 50% of always-thinking's tokens (97.2% @ 6.1k).
- N12-P2 (Qwen3-32B optimization): ≥ the best gated single fix + 3 points (76.0% → ≥ 79%) at ≤ 2 × its tokens.
- N12-P3 (gpt-oss-20b, Qwen3.6-35B-A3B): within 1 point of always-thinking at ≤ 50% of its tokens in each domain.
Positive claims need seeds 2–3 of A, B and thinking for Qwen3-32B (queued now: poc/queues/queue_s2_n12r.sh).

## N12 results, seed 1 (2026-10-16 09:32 UTC; poc/analyze_n12.py; escalation-to-sampling variant computed with the same rules)
| accuracy @ tokens per item | Qwen3-32B geometry | Qwen3-32B optimization | gpt-oss-20b geometry | gpt-oss-20b optimization |
|---|---|---|---|---|
| always A (toolbox / full manual) | 65.7% @ 0.6k | 58.0% @ 0.5k | 98.1% @ 0.9k | 80.0% @ 0.6k |
| always B (no helpers / BM25 snippets) | 80.6% @ 0.4k | 70.0% @ 0.5k | 97.2% @ 0.5k | 88.0% @ 0.6k |
| always thinking (gpt-oss: medium effort) | 97.2% @ 6.1k | 68.0% @ 6.0k | 99.1% @ 1.3k | 84.0% @ 1.9k |
| best gated single fix (N10) | 89.8% @ 2.5k | 76.0% @ 0.8k | 100% @ 0.9k | 91.0% @ 0.8k |
| oracle routing (N10) | 91.7% @ 1.0k | 85.0% @ 0.8k | 100% @ 0.9k | 93.0% @ 0.7k |
| **AGREE → thinking** | **99.1% @ 3.7k** (40 escalated) | 82.0% @ 5.2k (48) | 100% @ 1.5k (5) | 93.0% @ 2.1k (24) |
| AGREE → 3 samples + check | 82.4% @ 1.5k | 80.0% @ 1.8k | 100% @ 1.5k | **95.0% @ 1.6k** |
Programs that agreed across the two tool conditions were wrong on 1 + 0 + 0 + 1 of 208 + 208 items, against 9 + 1 wrong programs
that pass the metamorphic / feasibility check alone (Qwen3-32B): agreement catches the consistent errors the check misses.
- **N12-P1 refuted on tokens** (99.1% ≥ 95%, but at 61% of always-thinking's tokens, not ≤ 50%); it is still the only policy above
  always-thinking in accuracy, and above the per-item oracle of N10 (91.7%), which was limited by the check.
- **N12-P2 refuted on tokens** (82.0% ≥ 79%, at 6.2 × the best gated fix's tokens; escalating to sampling: 80.0% at 2.1 ×).
- **N12-P3 refuted on tokens** for gpt-oss (AGREE is 0.9 and 9.0 points above medium effort, but at 1.14–1.16 × its tokens, since
  medium effort is cheap for gpt-oss); Qwen3.6 pending (N10-M3 running).
Reading: agreement between tool conditions is the best label-free gate found so far (accuracy above every other policy, including
the check-based oracle), but it spends tokens on the second program and on escalations (40–48% of Qwen3-32B items disagree).
Replication (seeds 2–3) running.

## N10-M3 results, part 1 (2026-10-16 09:34 UTC; Qwen3.6-35B-A3B no-think; results/n10m3_analysis.log, n11m3_analysis.log)
**Setup failure found in the raw outputs:** the thinking arm hit the 16k cap on 102 / 108 geometry items (no program; "always
thinking 5.6%") and 52 / 100 optimization items. Not a negative: the arm is re-running at a 48k cap (poc/queues/queue_s2_n10m3t.sh; old
files kept as *_think_s1_cap16k.jsonl). Rows below that do not involve thinking:
| policy | geometry (108) | optimization (100) |
|---|---|---|
| first attempt (K8 toolbox / full manual) | 98.1% @ 1.0k | 64.0% @ 0.8k |
| always remove the context | 89.8% @ 0.7k | 48.0% @ 1.0k |
| always BM25 snippets / model-chosen helpers | 97.2% @ 0.7k | **91.0% @ 0.7k** |
| always repair once (optimization) | – | 83.0% @ 1.1k |
| always 3 samples + check | 99.1% @ 3.2k | 78.0% @ 2.3k |
| reference: exactly the needed tools | 99.1% @ 0.6k | 93.0% @ 0.7k |
| best gated single fix | 99.1% @ 1.0k | snippets 90.0% @ 1.1k |
| learned router (LOTO) | 99.1% @ 1.1k | 93.0% @ 1.1k |
| oracle | 99.1% @ 1.0k | 94.0% @ 1.0k |
| probe, then commit (N11) | 97.8% @ 5.5k | 89.3% @ 7.0k |
Geometry: like gpt-oss, Qwen3.6 is not hurt by the toolbox (98.1%; removing it costs 8 points), so nothing is left to route.
Optimization: snippets again the best cheap default (+27 points over the full manual, M3-P2 holds); the learned router is exactly
+3.0 points over the best gated single fix (93.0 vs 90.0%) at the same tokens, but only +2 over always using snippets (91.0% @ 0.7k,
which it does not beat on tokens); M3-P1 is decided after the thinking re-run (the router's menu includes thinking).

## N12 replication, geometry (2026-10-16 10:03 UTC; Qwen3-32B, seeds 2–3)
| seed | AGREE → thinking | always thinking | escalated | agreed but wrong |
|---|---|---|---|---|
| 1 | 99.1% @ 3.7k | 97.2% @ 6.1k | 40 / 108 | 1 |
| 2 | 99.1% @ 4.7k | 99.1% @ 5.9k | 57 / 108 | 1 |
| 3 | 99.1% @ 4.5k | 97.2% @ 5.8k | 54 / 108 | 1 |
Replicated claim: AGREE matches always-thinking's accuracy (99.1% on every seed vs 97.2–99.1%; the seed-1 gap is 3 vs 1 items,
p = 0.62) at 61–79% of its tokens. The saving is modest because the cheap pair disagrees on 37–53% of items (the toolbox program
is wrong on 43–46% of them for Qwen3-32B). Optimization seeds 2–3: thinking arms still running.

## N12 replication, optimization (2026-10-16 10:29 UTC; Qwen3-32B seeds 2–3)
AGREE → thinking: 82.0 / 85.0 / 81.0% (seeds 1–3) at 5.2 / 5.7 / 5.8k tokens; always thinking 68.0 / 67.0 / 67.0% at 6.0–6.5k;
always BM25 snippets 70.0 / 69.0 / 72.0% at 0.5k; no program that agreed across the two conditions was wrong (0 / 300).
Replicated: AGREE is 13–18 points above always-thinking at 88–91% of its tokens, and 11–16 points above the cheap default at 11 × its
tokens; the cheaper escalation (3 samples + check, seed 1: 80.0% @ 1.8k) is the better cost point.

## N10-M3 results, part 2 (2026-10-16 10:29 UTC): Qwen3.6 thinking re-run at 48k
Raw outputs: all 79 finished geometry answers are correct; all 29 failures are cut off at 48k (close 10, hull 8, diameter 7, …);
mean 32.6k tokens per item (no-think: 1.0k, 98.1% correct). Optimization: 8 / 100 cut off, mean 20.1k, 65.0% (no-think 64.0%).
For this model thinking is 20–30 × the tokens for no gain: a fix to avoid, not one to escalate to.
| policy | geometry | optimization |
|---|---|---|
| always thinking (48k) | 73.1% @ 32.6k | 65.0% @ 20.1k |
| gated thinking | 99.1% @ 1.2k | 78.0% @ 8.1k |
| learned router (LOTO) | 99.1% @ 1.1k | 93.0% @ 1.1k |
| best gated single fix | 99.1% @ 1.0k | snippets 90.0% @ 1.1k |
| always snippets (ungated) | – | 91.0% @ 0.7k |
| oracle | 99.1% @ 1.0k | 94.0% @ 1.0k |
| AGREE → thinking (N12) | 98.1% @ 5.3k | 90.0% @ 9.2k |
**M3-P1 refuted by the margin** (the learned router is exactly +3.0 points over the best gated single fix, at the same tokens), but
it does not beat simply always using snippets (91.0% at 0.7k, 1 item fewer at 60% of the tokens). **N12-P3 for Qwen3.6:** AGREE is
far above always-thinking (thinking is bad here), but it is dominated by the cheap default in both domains: the agreement gate
only pays when the fix it escalates to is good for the model (thinking for Qwen3-32B, not for Qwen3.6).
