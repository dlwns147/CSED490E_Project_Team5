# Pre-registration FM: execution-verified fact mining for solver code (a method)

Written 2026-10-14 12:30 UTC, before any code or run. Results are appended below without editing this section.

**Why.** On the 56 Solomon instances, hand-written facts take gpt-oss-120b low from 1–6 to 56 of 56 feasible (H3b/H3c), and the three
facts needed (file layout, integers everywhere in OR-Tools, a first-solution strategy for tight windows) only work together. Can the
model find such facts itself from its own failures, cheaply, without the facts being given?
**Method.** Mining set: 8 instances (c101, c201, r101, r201, rc101, rc201, r105, rc105; three have tight windows); test set: the other
48. Round r: the model writes programs (plain arm with the 12-line example + the current fact sheet; 8 instances × 2 seeds) → run →
failure reports (last lines of the traceback with the code lines around the error, or the violated constraint). The same model proposes
2 candidate facts (general, one or two sentences, no instance-specific numbers, no whole program). **Verification:** each candidate is
added to the sheet and the 16 programs are regenerated with the same seeds; the better candidate is kept only if it adds ≥ 2 feasible
programs over the current sheet. Up to 5 rounds; stop early if all 16 are feasible. The final sheet is used on the 48 test instances ×
2 seeds. All mining tokens are counted and reported per test instance.
**Arms on the test set:** no facts (plain), verified sheet, unverified sheet (every proposed fact kept, Dynamic-Cheatsheet-style), the
hand-written facts (integer reader + robust snippet; upper reference), and one per-instance repair round (N2) for comparison.
**Models:** gpt-oss-120b low (two independent mining chains, seeds A / B, servers 8043 / 8044); transfer of chain A's sheet to
gpt-oss-20b low (8042).
**Prior art (checked before writing).** Dynamic Cheatsheet (Suzgun et al., EACL 2026): an evolving memory of insights curated by the model,
not verified by execution. ExploraCoder (ACL 2025): explores unseen APIs by executing snippets within one task, passing usage insights to
later subtasks. AutoManual / ExpeL: rules or insights from agent trajectories. OR systems (OptiMUS, LLMOPT, SAC-Opt, Opt-Verifier, ReLoop)
correct from solver feedback within one run; none stores cross-instance lessons. New here: each fact is admitted only after a
counterfactual re-run shows it fixes failures, and the sheet is tested on unseen instances against unverified memory and per-instance repair.
**Predictions.**
- FM-P1: the verified sheet raises gpt-oss-120b low on the 48 test instances from ≤ 10% (plain) to ≥ 50% feasible (both chains).
- FM-P2: the unverified sheet is ≥ 10 points below the verified sheet (wrong or instance-specific facts get in).
- FM-P3: verified sheet ≥ per-instance repair + 20 points, at lower total tokens per test instance (mining amortised over 48 × 2).
- FM-P4: chain A's sheet transfers to gpt-oss-20b low: ≥ +20 points over its plain arm (0 / 56).
- FM-P5: the mined facts include the file layout and the integer requirement in both chains (read from the sheets); the tight-window
  first-solution strategy is found by at most one chain.

## Results (2026-10-14 13:29 UTC; feasible of the 48 held-out instances, seed 1 / seed 2; gpt-oss-120b low unless noted)

| arm | feasible | tokens per test program |
|---|---|---|
| no facts (plain, H3) | 6 / 1 (7.3%) | 1.8k |
| one repair round per instance (N2) | 13 / 11 (25.0%) | 1.8k + repair |
| FM chain A, verified sheet (1 fact) | 11 / 8 (19.8%) | 1.6k + 2.9k mining |
| FM chain A, unverified sheet (10 facts) | 16 / 14 (31.3%) | |
| FM chain B, verified sheet (2 facts) | 12 / 22 (35.4%) | 1.6k + 3.0k mining |
| FM chain B, unverified sheet (10 facts) | 20 / 18 (39.6%) | |
| hand-written facts (integer reader + robust snippet) | 48 / 48 (100%) | 1.5k |
| chain A verified sheet on gpt-oss-20b low | 1 / 2 (plain 0 / 0) | |

Mined facts (both chains, read): the VEHICLE-section layout ("skip the NUMBER CAPACITY header, the next line has two integers") and
"AddDimension's third argument (slack) must be an integer"; the unverified sheets are 5 near-duplicate layout facts + 5 slack facts.
Never found: integers for *every* OR-Tools value, the None check, a first-solution strategy for tight windows.
- **FM-P1 refuted** (20–35%, not ≥ 50%). **FM-P2 refuted, reversed:** the unverified sheets are better (31 / 40 vs 20 / 35%).
  **FM-P3 refuted** (verified − repair: −5 / +10 points, not +20; mining costs 280–290k tokens per chain). **FM-P4 refuted** (+3 on 20b).
  **FM-P5 holds** for the integer fact (both chains) and the tight-window strategy (neither); the layout was kept only by chain B.
- Why verification hurt: the round logs show candidate counts of 0–5 feasible of 16, and facts compose (H3): fixing the slack type does
  not make a program feasible while it still misreads the file, so end-to-end feasibility on 16 programs rejects facts that are right
  (chain A rejected the layout facts in rounds 1–4). Why the facts fall short of the hand facts: remaining test failures are a long tail
  (int() on header text despite the layout fact, invented attributes, KeyError, solver failures): prose facts are weaker than the exact
  code the hand facts give (as in F3: only the exact snippet fixes it).

## FM2 pre-registration (2026-10-14 13:29 UTC, before any FM2 run): verification by the targeted failure, and facts as short code
Two changes, everything else as FM (8 mining instances, 2 seeds, 5 rounds, 2 candidates, same test set): (1) a fact may be a short code
snippet (≤ 15 lines) or prose; (2) acceptance targets the failure the round was asked about: failures are grouped by signature (last
error line with literals masked, or the violated constraint); a candidate is accepted if the number of programs with the round's most common
signature falls by ≥ 50% and the feasible count does not fall by more than 1 (the best accepted candidate is kept). Chains C / D (seeds as
A / B), gpt-oss-120b low.
- FM2-P1: at least one chain ≥ 50% on the test set, and both chains ≥ their FM unverified counterpart + 10 points (A 31.3 → C ≥ 41.3;
  B 39.6 → D ≥ 49.6).
- FM2-P2: at least one final sheet contains a code-level reader for the file.
- FM2-P3: both stay ≥ 30 points below the hand facts (no chain finds the tight-window strategy).

## FM2 results (2026-10-14 14:15 UTC; 48 held-out instances, seed 1 / seed 2; gpt-oss-120b low)

| arm | feasible | median gap (feasible) | mining feasible of 16 by round | mining tokens |
|---|---|---|---|---|
| chain C, verified (5 facts) | 13 / 10 (24.0%) | 2.0 / 1.9% | 2, 2, 2, 1, 3, 4 | 293k |
| chain C, unverified (10 facts) | 5 / 5 (10.4%) | | | |
| chain D, verified (3 facts) | **31 / 31 (64.6%)** | 1.5 / 1.2% (25–26 within 5%) | 1, 5, 6, 6, 6, 7 | 319k |
| chain D, unverified (10 facts) | 3 / 0 (3.1%) | | | |
(references: no facts 7.3%, one repair round 25.0%, FM verified 19.8 / 35.4%, hand facts 100%.)
- **FM2-P1 half:** chain D 64.6% ≥ 50% and +25 over its FM counterpart; chain C 24.0% is below its counterpart (31.3%).
  **FM2-P2 refuted:** no code-level reader; the code facts are OR-Tools calls (AddDimension with integer horizon). **FM2-P3 holds.**
- With code facts allowed, verification is now essential: the unverified sheets collapse (3–10%) because wrong proposals get in (D's
  unverified sheet has a RoutingIndexManager keyword that does not exist: 23 of 48 crashes). Chain D's three verified facts: skip the
  title lines of the file, integers for AddDimension's arguments *and* for every time callback, never add disjunctions for customers.
- Chain C admitted a harmful fact: its targeted TypeError fell, but its "integer horizon + CumulVar bounds" advice produces 12–18
  time-window violations per test seed under exact checking. The final mining score separates the chains (C 4 / 16, D 7 / 16), so
  choosing the chain with the higher mining score (no test labels) gives 64.6%. Still no chain finds the tight-window strategy (0 of 3
  tight test instances).
- Cost: ≈ 300k mining tokens per chain, ≈ 3.3k per test program amortised over 96 programs (less with more instances), plus 1.8k per
  program; vs repair (1.8k + ≈ 1.5k) at 25%.

## FM2 replication pre-registration (2026-10-14 14:15 UTC, before running): how variable is the mined sheet?
Four more FM2 chains (E, F, G, H; new generation and proposal seeds), verified sheets tested on the 48 held-out instances × 2 seeds.
- FM2r-P1: at least 2 of the 4 new chains reach ≥ 50%.
- FM2r-P2: over all 6 FM2 chains, the final mining score (feasible of 16) correlates positively with the test score (Spearman ≥ 0.5),
  and picking the higher-mining-score chain of each pair reaches ≥ 50% in at least two thirds of the 15 pairs.

## FM2 model-generality pre-registration (2026-10-14 14:29 UTC, before running): gpt-oss-20b low
(a) transfer: chain D's verified sheet (mined by gpt-oss-120b) given to gpt-oss-20b low on the 48 test instances × 2 seeds;
(b) self-mining: an FM2 chain run entirely by gpt-oss-20b low (chain I), verified sheet tested the same way.
References for 20b on the 48 test instances: no facts 0 / 0, hand facts (integer reader + robust snippet) ≈ 60–65% (36 / 32 of 56 overall).
- FM2g-P1: transfer ≥ 25% (the three mined facts are model-independent; FM chain A's 1-fact sheet gave only 1 / 2 of 48).
- FM2g-P2: self-mining ≥ 15% but below transfer (the 20b model proposes weaker facts).

## FM2 replication and model-generality results (2026-10-14 15:30 UTC)

| chain (gpt-oss-120b low unless noted) | mining feasible of 16 at the end | test (48 held-out × 2 seeds) | verified facts |
|---|---|---|---|
| C | 4 | 24.0% | 5 |
| D | 7 | **64.6%** | 3 |
| E | 3 | 22.9% | 5 |
| F | 2 | 39.6% | 4 |
| G | 4 | 27.1% | 2 |
| H | 3 | 16.7% | 3 |
| I (mined and tested by gpt-oss-20b) | 0 | 0.0% | 4 |
| D's sheet given to gpt-oss-20b | – | 4.2% (3 / 1) | 3 |
- **FM2r-P1 refuted:** 0 of the 4 new chains reach 50%; across the six 120b chains the test score is 16.7–64.6% (mean 32.5%), so D was the
  outlier. **FM2r-P2 refuted:** Spearman(mining score, test score) = 0.38; the higher-mining-score chain of a pair reaches ≥ 50% in 5 of 15
  pairs. **FM2g-P1 / P2 refuted:** the mined facts do not lift gpt-oss-20b (4.2% with D's sheet; 0% self-mined, its mining never got a
  feasible program, so no fact could be verified on feasibility and the targeted-failure rule admitted four facts that did not help).
- What every 120b chain finds: the VEHICLE/NUMBER CAPACITY layout and "AddDimension's slack must be an integer". What only D found:
  "never add disjunctions for customers" (others' programs drop customers via penalties). Mined facts are local patches, one error at a
  time; the hand facts are complete working code (reader + exact solver snippet), which is why they reach 100%.
- Verdict so far: execution-verified fact mining lifts gpt-oss-120b from 7% to 32.5% on average (17–65%), about the same as keeping every
  proposed fact (FM: 31–40%) and above one repair round per instance (25%); it is not yet a reliable method, and it does not help a weaker
  model. Next: pool the six chains' verified facts and prune by leave-one-out on the mining set (FM3, below).

## FM3 pre-registration (2026-10-14 15:30 UTC, before running): pool the chains, then prune
Pool = the verified facts of chains C–H (22 facts). Evaluate the pool on the mining set (16 programs, same seeds); then one pass of
backward elimination in a fixed random order: drop a fact if the mining feasible count without it is ≥ the count with it. Test the pool
and the pruned sheet on the 48 held-out instances × 2 seeds (gpt-oss-120b low). All tokens counted (chains + pool + pruning).
- FM3-P1: the pruned sheet ≥ 50% on the test set (pooling recovers the facts only some chains found, pruning removes harmful ones).
- FM3-P2: the raw pool ≤ pruned − 10 points (harmful facts such as C's horizon advice are in the pool).
- FM3-P3: the pruned sheet keeps the layout, the integer-slack fact and the no-disjunction fact.

## FM3 results (2026-10-14 16:33 UTC)
Pool of the six chains' 22 verified facts: 3 of 16 feasible on the mining set; one pass of leave-one-out pruning dropped 4 facts (mining
evaluations swing 0–6 of 16 from one fact to the next), keeping 18. Test (48 held-out × 2 seeds): pruned sheet 12 / 8 (20.8%), raw pool
13 / 13 (27.1%). **FM3-P1, P2 refuted; P3 holds trivially** (18 facts kept, the three named ones among them). Total tokens: 1.86M (chains)
+ 0.72M (pool and pruning).
**Closing the fact-mining line (FM, FM2, FM3) as a partial negative.** Self-mined, execution-verified facts lift gpt-oss-120b from 7% to
21–40% on average (one chain 64.6%) on held-out Solomon instances, about as much as keeping every proposed fact and a little above one
repair round per instance, with large chain-to-chain variance, no help for a weaker model, and no benefit from pooling. Two reasons, both
measured: (1) the verification signal (16 programs) is too noisy to rank facts (counts swing 0–6 between near-identical sheets); (2)
facts are found one error at a time and as prose, while the hand facts that reach 100% are complete working code. Longer sheets also
hurt (the 22-fact pool is below most single chains).
