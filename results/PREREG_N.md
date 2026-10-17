# Methods for the hard benchmarks (N1–N3): pre-registration

Written 2026-10-14 09:36 UTC. N3 was computed before this file (exploratory, offline, reported as such); N1 and N2 are pre-registered here before any
run. Results are appended below without editing this section.

**Why these three.** The hard-benchmark runs show where the failures are: (i) contest geometry (H2c): most failing programs already fail
the statement's own examples (Qwen 217 / 268, gpt-oss-120b 129 / 179), and among programs that pass them 19–40% are still wrong (H2b);
(ii) Solomon routing (H3): programs crash reading the file or on invented solver calls, while the ones that run are within ≈ 3%. So the
missing pieces are a feedback signal the model can act on and a stronger label-free check than the examples.

## N1. Metamorphic example augmentation (MEA): new labelled tests from the statement's examples (new; a "check")
The model writes `transform(inp) -> list[str]`: inputs derived from a valid input whose correct output is *exactly the same* (reorder
independent items, translate / rotate by 90° / mirror coordinates, swap symmetric roles), only when the statement guarantees it, else [].
Applied to each public example, each derived input inherits the example's known output, so the new tests carry labels without any hidden
data or model-predicted outputs (unlike CodeT, which trusts outputs the model predicts). One extra call per problem (Qwen3-32B no-think).
*Prior art:* metamorphic testing with LLM-written relations (MR-Adopt, ASE 2024; Shin et al. 2401.17019; ChatGPT MT report 2310.19204);
CodeMetaAgent (2511.18249) uses MRs inside generation on HumanEval/MBPP/SWE-bench; our own MR-select used fixed, known relations. Not
found: example-inherited labels as a selector / repair signal for contest programs.
*Test (offline over all Part B samples that pass the examples, unflagged problems):* detection = share of wrong passers that fail an
augmented test; false alarm = share of correct passers that fail one.
- N1-P1: detection ≥ 25% of wrong passers; false alarms ≤ 5% of correct passers.
- N1-P2: as a selector at k = 3 (first sample passing examples + augmented tests), ≥ +1 point over the example check for every condition
  (the headroom to the oracle at k = 3 is only 1–3 points, so the check matters more as a repair trigger than as a selector).

## N2. One round of label-free feedback repair, typed by failure (a "fix by error type" test)
Contest geometry: if the program fails a public example (or crashes / has no code), the model gets its program plus the first failing
example (input, expected, its output or the error) and writes a corrected program; programs passing the examples are kept. Routing:
if the program crashes or the checker finds it infeasible on the actual instance (feasibility needs no optimum), it gets the traceback or
the violated constraint. Same model and mode as the first sample; costs counted in full.
Compared at matched tokens with a second independent sample + the same check (resampling), and with more reasoning (Qwen think-1,024,
gpt-oss medium). *Prior art:* Self-Debugging (Chen et al. 2023), Reflexion, AlphaCodium; Olausson et al. ICLR 2024 found self-repair gains
modest at matched compute, bottlenecked by feedback quality. Ours: the comparison split by failure type (crash vs wrong answer) and against
reasoning effort, on hard geometry and benchmark routing.
- N2-P1 (crashes): on routing (H3, plain arm), one repair round makes ≥ 30% of the crashed programs feasible, more than a second sample.
- N2-P2 (wrong answers): on contest geometry, repair beats a second sample + check by ≤ 3 points for gpt-oss-20b low and Qwen3-32B no-think
  (wrong answers carry less information than tracebacks), at ≈ the same tokens.
- N2-P3: neither beats more reasoning per token for Qwen (think-1,024 single 21.8% at 2.9k).

## N3. Escalation cascade (exploratory, computed before this file; prior art: Model Cascading for Code 2405.15842, FrugalGPT)
Cheap mode first; accept if it passes the examples; else run the expensive mode. Offline on Part B (poc/analyze_cascade.py):
| cheap → expensive | cheap alone | expensive alone | cascade | escalated |
|---|---|---|---|---|
| Qwen3-32B no-think → think-1,024 | 12.1% @ 0.7k | 21.8% @ 2.9k | 23.7% @ 3.2k | 82% |
| gpt-oss-20b low → medium | 37.7% @ 1.5k | 47.1% @ 8.7k | **49.8% @ 7.6k** | 52% |
| gpt-oss-120b low → medium (2 seeds) | 46.0% @ 3.2k | 56.1% @ 6.8k | 56.4% @ 7.0k | 40% |
| gpt-oss-20b low → gpt-oss-120b medium | 38.6% @ 1.5k | 56.1% @ 6.8k | 55.0% @ 6.1k | 51% |
Reading: the cascade is never worse than the expensive mode and is +2.7 points at 13% fewer tokens for gpt-oss-20b, but the example check
escalates too rarely to save much for strong models; consistent with the prior art's 26% average saving.

## N1 results (2026-10-14 09:46 UTC; poc/mea_cc.py gen/eval q32b; transforms by Qwen3-32B no-think, 475 tokens per problem)

- Derived tests for 267 of 311 problems (7.1 per problem). As a check over all Part B example-passers (unflagged problems): wrong passers
  flagged 129 / 339 (38%), correct passers flagged 549 / 1,323 (41.5%): no better than chance. **N1-P1 refuted; N1-P2 refuted** (selector
  at k = 3: identical to the example check for 4 conditions, −0.4 for gpt-oss-20b medium).
- Setup or real negative? Checked with the C++ references (diagnosis only; they are hidden data): 74% of the derived tests keep their
  inherited output; only 108 of 204 problems have all derived tests valid, and one invalid test flags every correct program. But on those
  108 problems, where every derived test is valid, the check flags only 13 / 210 wrong passers (6%) and 13 / 752 correct ones (1.7%).
  So a better transform writer would not rescue it: programs that pass the examples but are wrong are wrong in ways that survive
  translation, rotation, mirroring and reordering. Unlike our synthetic contract traps (F2: orientation-dependent errors that MR checks
  catch), contest-level errors are mostly logic and case-analysis errors. N1 is closed as a real negative.

## N2 results so far (2026-10-14 10:41 UTC)
Contest geometry, one repair round (repair tokens per problem in parentheses): gpt-oss-20b low 125 → 140 (+733) and 115 → 139 (+794)
of 311; Qwen3-32B no-think 43 → 56 (+792) and 35 → 56 (+803). Matched alternative, second sample + example check: 20b 44.8% at +1.5k,
Qwen 17.3% at +0.7k (from N3's table). So repair ≈ resampling in accuracy (20b 44.8–45.0 vs 44.8; Qwen 18.0 vs 17.3) at about half the
extra tokens for 20b and the same for Qwen; **N2-P2 holds** (difference ≤ 3 points). **N2-P3 holds:** Qwen think-1,024 single (21.8% at
2.9k) is above repair (18.0% at 1.5k) but costs twice as much; per extra token repair is better.
Routing (H3 plain arm, crash or infeasible feedback): gpt-oss-20b low 0 → 7 and 0 → 3 of 56; Qwen3-32B 0 → 0 and 0 → 0. **N2-P1 refuted**
(≥ 30% of crashed programs feasible after one round): the crash messages are informative, but fixing one crash exposes the next (format,
then float arguments, then API signatures).

## N2b / N4 pre-registration (2026-10-14 10:41 UTC, before any of these runs or computations)
- N2b: one repair round for gpt-oss-120b low (2 seeds) and Qwen3-32B think-1,024 (seed 1, 1,024-token budget for the repair too) on the
  contest set. Prediction N2b-P1: gpt-oss-120b low + repair ≥ 52% (from 46.1%) at ≤ 4.5k tokens, below one medium attempt (56.8% at 6.8k).
  N2b-P2: Qwen think-1,024 + repair ≥ 26% at ≤ 4.5k.
- N4 (typed combination, offline over existing samples; new as a combination, ingredients published): accept the cheap sample if it passes
  the examples; else one repair round; if the repaired program still fails the examples, escalate to the expensive mode. Cost counts every
  call actually made. N4-P1: gpt-oss-20b low → repair → medium ≥ 49.8% (N3 cascade) at ≤ 90% of its tokens (≤ 6.8k). N4-P2: Qwen no-think →
  repair → think-1,024 ≥ 23.7% at ≤ 3.0k. N4-P3: gpt-oss-120b low → repair → medium ≥ 56.8% (medium alone) at ≤ 6.8k.

## N4 results (2026-10-14 10:46 UTC; poc/analyze_n4.py; seeds 1–2, 622 problem-seeds per row)
| cheap → expensive | cheap | expensive | N3 cascade | cheap + repair | N4 (repair, then escalate) |
|---|---|---|---|---|---|
| Qwen3-32B no-think → think-1,024 | 12.5% @ 0.7k | 21.5% @ 3.0k | 23.8% @ 3.2k | 18.0% @ 1.5k | 24.9% @ 3.8k |
| gpt-oss-20b low → medium | 38.6% @ 1.5k | 47.3% @ 8.7k | 50.3% @ 7.5k | 44.9% @ 2.3k | **51.6% @ 7.3k** |
- N4-P1 half: 51.6% ≥ 49.8% but 7.3k tokens, not ≤ 6.8k (3% below the cascade, not 10%). N4-P2 refuted on cost (3.8k > 3.0k; +1.1 points).
  Typing the fix adds about one point over the plain cascade; repair rescues too few failures to save the expensive call often.

## N2b and N4-P3 results (2026-10-14 11:33 UTC)
- gpt-oss-120b low + one repair round: 132 → 160 (+1.56k tokens) and 154 → 170 (+1.24k) of 311, i.e. 46.0 → 53.1% at 4.6k tokens.
  **N2b-P1 holds on accuracy (≥ 52%), misses the cost bound narrowly (4.6k vs ≤ 4.5k);** below one medium attempt (56.1% at 6.8k) as
  predicted. Wrong answers fixed 25 / 129 and 15 / 100, crashes 4 / 17.
- Qwen3-32B think-1,024 + one repair round (1,024-token budget): 69 → 85 (22.2 → 27.3%) at 2.9k + 1.5k = 4.4k. **N2b-P2 holds.** Crashes
  fixed 9 / 67, wrong answers 7 / 149.
- N4 for gpt-oss-120b (low → repair → medium): 57.7% at 7.6k vs medium alone 56.1% at 6.8k and the plain cascade 56.4% at 7.0k.
  **N4-P3 refuted on cost** (+1.6 points for +13% tokens).
- Across N2–N4: a repair round is the best *next* step after one cheap sample for every model (gpt-oss-120b: +7.1 points for +1.4k
  tokens; 20b: +6.3 for +0.8k; Qwen: +5.5 for +0.8k), better per token than a second sample or escalation, but it saturates after one
  round of wrong-answer feedback (15–19% of wrong answers fixed for gpt-oss, 5% for Qwen with thinking).

## N2m pre-registration (2026-10-15 07:28 UTC, before running): more repair rounds
gpt-oss-20b low, seed 1: rounds 2 and 3 of the same example-feedback repair on the programs that still fail the statement's examples
(round 1: 125 → 140 of 311 at +733 tokens per problem). Prior art: Olausson et al. (ICLR 2024) find diminishing returns per round.
- N2m-P1: round 2 adds ≥ 2 points and round 3 ≥ 1 point, each for ≤ 0.8k extra tokens per problem; after 3 rounds the gain is still
  below a second independent sample + check + its own repair (i.e. resampling stays competitive).

## N2m results (2026-10-15 08:25 UTC; gpt-oss-20b low, seed 1, 311 problems)
Rounds 1 / 2 / 3: 125 → 140 → 147 → 149 solved (+4.8 / +2.3 / +0.6 points) for +733 / +658 / +544 repair tokens per problem. After 3
rounds: 47.9% at 3.4k tokens per problem, equal to 3 independent samples + example check (47.9% at 4.5k). **N2m-P1 half:** round 2
≥ 2 points holds, round 3 ≥ 1 refuted (diminishing returns, as Olausson et al.); repair is slightly cheaper than resampling for the same
accuracy, not better.

## N7 pre-registration (2026-10-15 23:28 UTC, before computing; offline, CPU): the failure map as a policy (route each failure to its fix)
FIX_MAP says: crash / no program → give feedback and repair; wrong answer on the examples → more reasoning. Policy R (typed router):
low-effort sample; if it passes the statement's examples, accept; if it crashed, timed out or gave no program, one repair round, accept
if the repair passes the examples, else escalate to medium; if it gave a wrong answer, escalate to medium directly. Compared with N3
(escalate on any failure) and N4 (repair any failure, then escalate) on the same samples (seeds 1–2, gpt-oss-20b and gpt-oss-120b low →
medium; repair results from N2), all tokens counted.
- N7-P1: R matches N4's accuracy within 1 point at ≥ 10% fewer tokens (it skips repairs of wrong answers, which rarely succeed).
- N7-P2: R ≥ N3 + 0.5 points (repairing crashes is cheap and often succeeds).

## N7 results (2026-10-15 23:30 UTC; seeds 1–2, 622 problem-seeds per row)
| low → medium | N3 escalate on any failure | N4 repair any failure, then escalate | R typed router |
|---|---|---|---|
| gpt-oss-20b (failures on the examples: 225 wrong, 81 no program, 12 crash, 2 timeout) | 50.3% @ 7.5k | **51.6% @ 7.3k** | 50.3% @ 7.6k |
| gpt-oss-120b (230 wrong, 17 crash, 3 timeout) | 56.4% @ 7.0k | **57.7% @ 7.6k** | 56.4% @ 7.1k |
**N7-P1 and N7-P2 refuted.** Routing by failure type gains nothing over plain escalation: repairing crashes and give-ups rarely works,
and N4's extra point comes from repairing *wrong answers* (the failure type the map sent to reasoning). FIX_MAP corrected: on contest
problems, one repair round from the failing example is worth trying before escalating, whatever the failure type.

## N8 / N9 pre-registration (2026-10-16 07:57 UTC, before computing or running)
- N8 (offline, existing samples): a three-level cascade for gpt-oss-120b: low; if it fails the statement's examples, medium; if that fails,
  high (64k cap). Seeds 1–3 paired (low s_i, medium s_i, high s_i). Prediction N8-P1: ≥ 64% (within 2 points of always-high, 66.2%) at
  ≤ 50% of always-high's tokens (≤ 15k per problem).
- N9 (GPU): repair at a higher effort: the low attempt's failing example is fed back to gpt-oss-120b at MEDIUM effort (one round), vs a
  fresh medium attempt (N3) and vs a low-effort repair (N2). Seed 1. Prediction N9-P1: medium-effort repair ≥ fresh medium on the problems
  where low failed, at ≤ the same tokens (the failing example plus the old program is information a fresh attempt lacks).

## N8 results (2026-10-16 07:58 UTC; seeds 1–3 paired, 933 problem-seeds)
low 46.1% @ 3.2k | medium 56.8% @ 6.8k | high 66.2% @ 30.1k | low→medium 56.8% @ 7.1k | **low→medium→high 62.8% @ 19.0k** |
**medium→high 65.0% @ 20.2k**. **N8-P1 refuted** (62.8% at 19.0k, not ≥ 64% at ≤ 15k): escalating on the examples keeps wrong programs
that pass them, so the cascade loses 3.4 points; starting at medium loses only 1.2 points for 33% fewer tokens than always-high.

## N9 results (2026-10-16 08:32 UTC; seed 1, gpt-oss-120b, 311 problems; poc/analyze_n9.py)
On the 139 problems whose low-effort program fails the statement's examples:
| fix | correct | passes the examples | fix tokens per failed problem |
|---|---|---|---|
| one repair round at low effort (N2) | 28 (20.1%) | 42 | 3.5k |
| one repair round at medium effort (N9) | **41 (29.5%)** | 60 | 8.6k |
| a fresh medium attempt (N3) | 38 (27.3%) | 69 | 9.1k |
Paired, medium repair vs fresh medium: 15 vs 12 problems solved by only one of them (26 by both); sign test p ≈ 0.70.
**N9-P1 holds only nominally** (41 ≥ 38 at 6% fewer tokens; not significant, one seed). Pipelines (low first, the fix only when the
examples fail; every call counted): low + low repair 51.4% @ 4.8k; low + medium repair 55.6% @ 7.1k; low → fresh medium 54.7% @ 7.3k;
**low + medium repair, then a fresh medium attempt if the repair still fails the examples: 58.8% @ 9.6k** (fresh medium alone, seed 1:
54.7% @ 6.7k). Raw programs: the repairs are real algorithmic changes (e.g. 1366F extends Karp's DP to 2n steps; 1599G rewrites the line
finding), not example-specific patches; 15 of the 139 medium repairs hit the 16k cap (8 without code).
Reading: the failing example is worth about as much as a fresh medium sample; the two fail on different problems (15 vs 12), so
chaining them adds 4 points over either for +2.5k tokens. New frontier point between medium (56.8% @ 6.8k) and medium → high (65.0% @ 20.2k).
N9 replication started 08:36 UTC (seeds 2 and 3, same settings, poc/queue_s2_n9r.sh); the chained pipeline is claimed only if it holds
on all three seeds (≥ +3 points over fresh medium alone at ≤ 1.5 × its tokens).

## N9 replication results (2026-10-16 09:04 UTC; seeds 1–3, 933 problem-seeds; results/n9_analysis.log)
On the 381 problem-seeds whose low-effort program fails the examples: medium-effort repair 98 (25.7%) at 8.3k fix tokens vs a fresh
medium attempt 100 (26.2%) at 9.4k; paired 37 vs 39 (p = 1.00); low-effort repair (seeds 1–2) 44 / 250 (17.6%) at 3.5k.
**N9-P1 refuted over three seeds** (the seed-1 edge was noise): repairing at medium effort is worth the same as a fresh medium attempt,
for 12% fewer tokens. Pipelines: low + medium repair 56.6% @ 6.6k ≈ low → fresh medium 56.8% @ 7.1k ≈ fresh medium 56.8% @ 6.8k;
low + medium repair → fresh medium 59.9% @ 9.1k (+3.1 points at 1.34 × the tokens of fresh medium), but per seed +4.1 / +3.8 / +1.3:
**the replication criterion (≥ +3 on every seed) fails on seed 3, so the chained pipeline is not claimed** (reported as a frontier
point with that caveat).

## N13 pre-registration (2026-10-16 09:52 UTC, before computing; offline, CPU): a second, different opinion as the escalation gate
N8 lost 3.4 points against always-high because escalating only on the statement's examples keeps wrong programs that pass them.
Gate: escalate when the program fails the examples OR disagrees with the problem's approximate brute-force oracle on its small
generated inputs (the N5 oracles of gpt-oss-120b low, seed 1: 197 of 311 problems have accepted oracle cases; 2.9k tokens per problem
for generator + oracle, charged in full to every problem-seed). Programs: gpt-oss-120b low / medium / high (64k), seeds 1–3 paired
(933 problem-seeds). Disagreement = any oracle case where the program's output differs beyond relative 1e-2 (as N5). When the
escalated program also fails the gate, the last level's program is kept (as N8).
- N13-P1: medium → high with the oracle gate ≥ 66.0% (N8: 65.0%; always-high 66.2%) at ≤ 25k tokens per problem, oracle included.
- N13-P2: low → medium → high with the oracle gate ≥ 64.5% (N8: 62.8%) at ≤ 22k.
- N13-P3: the oracle flags ≥ 40% of the wrong example-passing medium programs at ≤ 8% false alarms on the correct ones.

## N13 results (2026-10-16 09:54 UTC; seeds 1–3, 933 problem-seeds; results/n13_analysis.log)
| policy (gpt-oss-120b) | accuracy | tokens per problem |
|---|---|---|
| always high (64k) | 66.2% | 30.1k |
| N8 medium → high, examples gate | 65.0% | 20.2k |
| **N13 medium → high, examples + oracle gate** | **66.3%** | 25.7k (2.9k of it the oracle) |
| N8 low → medium → high, examples gate | 62.8% | 19.0k |
| N13 low → medium → high, examples + oracle gate | 65.4% | 25.1k |
The oracle flags 42 / 86 wrong example-passing medium programs (49%) and 30 / 403 correct ones (7.4%). **N13-P3 holds; P1 and P2 hold
on accuracy and miss the token bounds** (25.7k > 25k; 25.1k > 22k). Reading: the different second opinion recovers the points the
examples gate lost (+1.3 / +2.6), so a cascade now matches always-high at 85% of its tokens; the oracle's own 2.9k tokens eat most
of the saving. Cheaper oracles (written once per problem and reused across runs, or only for problems where medium passes the
examples) are the obvious next step.

## N13b pre-registration (2026-10-16 09:58 UTC, before computing): write the oracle only when it can change the decision
Same as N13 medium → high, but the oracle (2.9k tokens) is generated and charged only for problem-seeds whose medium program passes
the examples (the others escalate anyway). Prediction N13b-P1: same accuracy as N13 (66.3%) at ≤ 24k tokens per problem.
**N13b result (2026-10-16 09:59 UTC): 66.3% @ 24.7k tokens per problem; P1 holds** (same accuracy as always-high, 66.2% @ 30.1k, at
82% of its tokens). Most of the remaining cost is the high-effort escalations themselves (medium fails the examples on 43% of
problem-seeds).

## N17 pre-registration (2026-10-16 16:29 UTC, before computing; offline): a second MODEL as the second opinion
N13 used an approximate brute-force oracle (2.9k tokens per problem) to catch wrong programs that pass the statement's examples.
Alternative: a program from a *different model family* that also passes the examples; disagreement on the oracle's small generated
inputs (inputs only, no oracle outputs) triggers escalation. Policy: gpt-oss-120b medium; escalate to high (64k) if it fails the
examples, OR if Qwen3.6's no-think program (same seed) passes the examples and the two programs disagree on any generated input
(relative 1e-2). Tokens: medium + Qwen3.6 program (3.4k, a 3B-active model) + high when escalated. Seeds 1–3, 933 problem-seeds; the
N5 inputs exist for 197 of 311 problems (no inputs → the examples gate alone).
- N17-P1: ≥ 66.0% (always-high 66.2%) at ≤ 26k tokens per problem (N13b: 66.3% @ 24.7k).
- N17-P2: the cross-model check flags ≥ 40% of medium's wrong example-passers at ≤ 10% false alarms (oracle: 49% / 7.4%).

## N18 pre-registration (2026-10-16 16:29 UTC, before running): do token log-probs tell right from wrong contest programs?
User request: look at log-probs, not only accuracy. Qwen3.6 no-think on the 311 contest problems, seeds 1–3, raw log-probs of every
answer token (`run_cc.py --logprobs`, GPUs 0–2). Program-level scores: mean log-prob over the code block, min, and the 5% quantile.
- N18-P1: AUROC (correct vs wrong among programs that pass the examples) ≤ 0.65 for every score (C1: confidence ≈ no selector).
- N18-P2: choosing among the 3 seeds' example-passing programs by the highest mean log-prob is no better than taking the first
  example-passer (within ±1 point).
- N18-P3 (descriptive): where the lowest-confidence tokens fall (numeric constants / formulas / control flow / I/O), wrong vs correct.

## N17 results (2026-10-16 16:31 UTC; results/n17_analysis.log)
medium → high when the examples fail or Qwen3.6's example-passing program disagrees on the generated inputs: **65.5% @ 25.2k** tokens
per problem (always-high 66.2% @ 30.1k; examples gate 65.0% @ 20.2k; N13b brute-force oracle 66.3% @ 24.7k). Where both programs pass
the examples and inputs exist (380 problem-seeds), the cross-model check flags 21 / 51 wrong medium programs (41%) at 29 / 329 false
alarms (8.8%). **N17-P1 refuted** (65.5 < 66.0), **P2 holds** (41% ≥ 40%, 8.8% ≤ 10%). A second model is a weaker second opinion than a
brute-force oracle: it only exists where that model also passes the examples, and it charges its 3.4k tokens on every problem (a 3B-
active model, so far cheaper in compute than the token count suggests).

## N18 results (2026-10-16 16:51 UTC; results/n18_analysis.log; Qwen3.6 no-think, 933 programs, 43.9% correct @ 3.4k tokens, 9 cap hits)
Among the 550 programs that pass the statement's examples (410 correct, 140 wrong), lower confidence goes with wrong programs only
weakly: AUROC mean 0.61, min **0.69**, 5% quantile 0.60 (all programs, failing the examples: 0.64). **N18-P1 refuted for the minimum
(0.69 > 0.65), holds for mean and q5.** Choosing among the 3 seeds' example-passers by the highest mean log-prob: 55.0% vs the first
example-passer 53.7% (any correct example-passer 58.5%): **N18-P2 narrowly refuted (+1.3 points)**. Where the doubt sits (P3): 76–83%
of each program's 20 least confident code-block tokens are inside *comments* (Qwen3.6 reasons in comments); exploratory, not
pre-registered: over non-comment code tokens only the AUROCs fall to 0.52 / 0.63 / 0.49. So the weak signal is the model's uncertainty
about its *approach*, written in the comments, not about the code it types. As a check it is free but weaker than the brute-force
oracle (49% caught at 7% false alarms) or a second model (41% / 9%).

## N12-M4 pre-registration (2026-10-16 16:51 UTC, before running): the agreement gate on a second model that helpers mislead
Qwen3-8B (no-think; strongly steered by the toolbox, F1 / M1), the N10 geometry suite (108 items), K8 toolbox vs no helpers vs
thinking (16k), seeds 1–3, poc/queue_s2_n12m4.sh on GPUs 0–2. Prediction N12-M4-P1: AGREE → thinking is within 2 points of
always-thinking at ≤ 70% of its tokens (Qwen3-32B: equal accuracy at 61–79%).

## N12-M4 results (2026-10-16 17:06 UTC; Qwen3-8B, results/n12m4_analysis.log)
| seed | AGREE → thinking | always thinking (16k) | K8 toolbox | no helpers | escalated | agreed but wrong |
|---|---|---|---|---|---|---|
| 1 | **99.1% @ 5.5k** | 97.2% @ 6.8k | 68.5% @ 0.85k | 61.1% @ 0.43k | 54 / 108 | 0 |
| 2 | **98.1% @ 5.1k** | 95.4% @ 7.1k | 70.4% | 63.9% | 47 / 108 | 2 |
| 3 | **97.2% @ 5.7k** | 94.4% @ 7.1k | 66.7% | 65.7% | 52 / 108 | 1 |
Thinking: 2 cap hits of 324, p90 11.3k tokens; its failures are logic / transform errors. **N12-M4-P1: accuracy part holds (AGREE is
1.9–2.8 points ABOVE always-thinking on every seed), token part narrowly refuted (71–81% of thinking's tokens, not ≤ 70%).** Unlike
Qwen3-32B, removing the helpers does not help Qwen3-8B (61–66% vs 67–70% with them), yet the two conditions fail on different items,
so their agreement is still an excellent gate. Two models now: the agreement gate matches or beats always-thinking at 61–81% of its tokens.

## N19 pre-registration (2026-10-16 17:06 UTC, before computing; offline): the tool-condition agreement gate on contest problems
gpt-oss-120b low without helpers (oss120_low) and with the K8 toolbox (oss120_low_k8, H4), seeds 1–3. Gate: accept the no-helper low
program if it passes the examples AND the K8 program also passes and the two agree on the N5 generated inputs (relative 1e-2); else
escalate to medium (fresh medium sample, same seed). Tokens: both low programs + medium when escalated.
- N19-P1: ≥ medium alone (56.8%) at ≤ 90% of the tokens of "low → medium on example failure" + the second low program (i.e. the gate
  beats the N3 cascade 56.8% @ 7.1k in accuracy at ≤ 1.5 × its tokens).

## N19 results (2026-10-16 17:09 UTC; results/n19_analysis.log)
low → medium when the examples fail or the no-helper and K8 low programs disagree on the generated inputs: **56.9% @ 11.8k** (N3
examples cascade 56.8% @ 7.1k; medium alone 56.8% @ 6.8k). **N19-P1 refuted** (no accuracy gain, 1.7 × the tokens). Exploratory (not
pre-registered): using the agreement only where inputs exist, 57.3% @ 9.7k. Why: where both programs pass the examples (383
problem-seeds), the agreement accepts 38 of the 66 wrong low programs (catches only 42%) and rejects 11 of 317 correct ones: gpt-oss-120b
ignores the helpers, so its programs with and without them make the SAME mistakes. A second opinion helps only when its errors are
independent of the first: tool conditions decorrelate errors for helper-steered models (Qwen3-8B / 32B geometry: 1–2 agreed-but-wrong
of ~40), not for gpt-oss; a brute-force oracle (49%) or another model (41%) decorrelates better there.
