# Pre-registration XPEER: a peer from another family as the check of the word-problem cascade

Written 2026-10-31 08:5x UTC, before any row of the fresh run below and before the cascade outcome of any cell named in the predictions
has been computed (N's own rows were used for the predictions; the peer's agreement on those N was not printed). Results go below.

**Why it could change the claim.** On word problems the cheap path saves nothing: with another Qwen generation as the peer (HO-PA) the
cascade N → peer agrees → N, else SB→T→T is within ±0.6 utility of the default for every model, and training the quick program (WP-RL,
TD, RF) or the check (VER, scoring) has not changed that so far. The break-even accounting (`poc/analyze_breakeven.py`) puts the
limit on the check. If a peer that is cheap enough to run on one RTX 3090 makes the cascade beat the default on models and problems it
was not chosen on, the word-problem claim changes from "the cheap path saves nothing" to "it pays with the right peer", and the
project's three task types share one recipe.

**Exploratory (post hoc; these cells chose the hypothesis and are not evidence for it).** `python3.11 poc/analyze_xpeer.py --explore`
(results/xpeer_explore.txt): Qwen3-8B and Qwen3.5-9B as N, every model with stored quick programs on the 476 problems as the peer
(cascade − SB→T→T, utility, paired 95% intervals over problems, 3 seeds):

| N \ peer | Qwen3.5-9B / Qwen3-8B | Qwen3-14B-AWQ | Qwen3-32B-AWQ | Nemotron-3-Nano | Seed-OSS-36B | gpt-oss-20b | gpt-oss-120b |
|---|---|---|---|---|---|---|---|
| Qwen3-8B | +0.01 [−0.81, +0.81] | −0.38 | −0.23 | −0.16 | +0.01 | **+1.20 [+0.34, +2.06]** | **+1.33 [+0.61, +2.16]** |
| Qwen3.5-9B | +0.10 [−0.83, +1.00] | −0.23 | +0.34 | −0.58 | +0.01 | **+1.25 [+0.06, +2.39]** | **+2.08 [+0.74, +3.26]** |

Only the two gpt-oss models (another family, trained by another lab) clear the default, and with Qwen3-8B as N they are more accurate
too (+1.26 / +1.40 points), not only cheaper. 2 × 7 peers were tried, so selection inflates the best cell.

**Mechanism and theory (exploratory; the stratified break-even).** The uniform break-even r* (share of right vs wrong passing programs
a check lets through) assumes the check's accepts are spread evenly over N's right and wrong programs. They are not: split N's passing
programs by whether N and the default are right. Accepting N instead of running the default gains only tokens where both are right
(+1.5 utility per problem-seed for Qwen3-8B) or both wrong (+3.6), +103 where only N is right and −96 where only the default is right.
So the cascade's accuracy is set by two small strata, 2.5% (N right, default wrong) and 7.4% (N wrong, default right) of Qwen3-8B's
problem-seeds, and a peer pays when (agreement where only N is right) / (agreement where only the default is right) > 7.4 × 96 /
(2.5 × 103) ≈ 2.8 and the tokens are repaid. Qwen3-8B's peers there:

| peer | only N right | both right | both wrong | only default right | ratio of the two decisive strata |
|---|---|---|---|---|---|
| Qwen3.5-9B | 44.4% | 80.1% | 38.1% | 12.3% | 3.6 |
| Qwen3-14B-AWQ | 38.9% | 81.1% | 38.4% | 17.9% | 2.2 |
| Nemotron-3-Nano | 30.6% | 71.9% | 34.0% | 10.4% | 2.9 |
| Seed-OSS-36B | 41.7% | 79.5% | 31.0% | 11.3% | 3.7 |
| gpt-oss-20b | 63.9% | 89.5% | 34.3% | 4.7% | 13.6 |
| gpt-oss-120b | 63.9% | 92.1% | 33.2% | 2.8% | 22.8 |

Every peer confirms about a third of the wrong programs on problems the default also fails (cheap false accepts: the default would
not have fixed them). The gpt-oss peers differ in the two strata that matter: they confirm N's right answers where thinking fails
almost twice as often, and N's wrong answers where thinking succeeds a third as often. The uniform account misses this (it
"predicts" +0.4 for the gpt-oss peer on OptiBench's third, where the exact value is +1.65). Prior work: errors of LLMs are correlated,
more so within a provider and architecture and among more accurate models (Kim et al., Correlated Errors in Large Language Models,
2506.07962, ICML 2025); similar models share mistakes and this weakens model-on-model oversight (CAPA; Goel et al., 2502.04313);
agreement between models as the deferral rule of a cascade (ABC, 2407.02348, TMLR 2025). In the project: on SQL another family
(Nemotron) was not a less correlated peer (SQL-PA4). **New here:** which peer makes a check-gated cascade pay is decided by its
agreement in the two strata where the cheap answer and the default disagree in correctness, not by overall error coincidence; a test
of that on models and problems not used to find it.

**Predictions of the stratified account (made from N's own rows: strata shares and gains, N's tokens; gpt-oss-20b's agreement per
stratum and its tokens per call (614) taken from Qwen3-8B).** Qwen3-14B-AWQ +1.5, Nemotron-3-Nano +0.84. Development check on a seen
cell: for Qwen3.5-9B the same transfer predicts +3.10 against the realised +1.25, because gpt-oss-20b agrees with 27.9% of Qwen3.5-9B's
wrong programs where its default is right (4.7% for Qwen3-8B): the agreement rates are a property of the pair, so these predictions are
uncertain and are not the decision rule.

**Run.** (a) Stored rows, no generation: N = Qwen3-14B-AWQ and Nemotron-3-Nano, peer gpt-oss-20b, 476 problems × 3 seeds
(`python3.11 poc/analyze_xpeer.py --models`). (b) Fresh problems: OptiBench's other 403 problems (`FORM_SUBSET=1/3` and `2/3`; the third
used everywhere so far is `0/3`), Qwen3-8B and Qwen3-14B-AWQ, the short think (`run_form.py <tag> formx <s> --think_budget 2000`) and
the think (`--tarm --think`, 16k), seeds 1–3, tags q8bob / q14aob, the same prompts, facts and per-problem seeds as the stored arms
(`poc/slurm/lane.sh`, one RTX 3090 per model × seed). N's and the peers' quick programs on those problems are already stored (605-problem
formx rows of every model). `python3.11 poc/analyze_xpeer.py --fresh q8b:q8bob,q14a:q14aob` (gpt-oss-20b and the pre-registered
Qwen peer, Qwen3.5-9B). gpt-oss-20b runs on one 24 GB GPU; its tokens (reasoning included) are counted as the peer's.

## Predictions (paired 95% intervals over problems, seed means; utility = accuracy − 0.5 × ktokens; cascade = N → gpt-oss-20b's quick program prints the same value → N, else N's SB→T→T)

- **XP-P1 (another model, stored rows):** Qwen3-14B-AWQ cascade − its SB→T→T: lower bound > 0.
- **XP-P2 (another family as N):** Nemotron-3-Nano cascade − its SB→T→T: lower bound > 0.
- **XP-P3 (fresh problems, the cell that chose it):** Qwen3-8B on OptiBench's other 403 problems: lower bound > 0.
- **XP-P4 (fresh problems, another model):** Qwen3-14B-AWQ on the same 403 problems: lower bound > 0.
- **XP-P5 (mechanism):** in each of the four cells, gpt-oss-20b's agreement where only the default is right is below Qwen3.5-9B's (the
  pre-registered peer), and its ratio of the two decisive strata is above it (point estimates; reported with counts).
- Reported: accuracy and token share of the default; the exact decomposition (`acct`); the stratified prediction against the realised
  value; gpt-oss-120b as the peer (does not fit one RTX 3090; a bound); raw programs where gpt-oss-20b confirms a wrong program that the
  default gets right.

## Decision

- P3 holds and P1 or P2 holds → the word-problem claim changes: the cheap path pays on word problems with a peer from another family;
  the recipe's word-problem default becomes N → gpt-oss-20b agrees → N, else SB→T→T (PROJECT / REPORT / PROPOSAL), and the break-even
  law is restated in its stratified form (the peer's agreement where the cheap answer and the default disagree in correctness).
- P3 holds, P1 and P2 refuted → the gain is specific to Qwen3-8B with this peer (reported; the peer is chosen per model by a labelled
  pilot, which then needs its own pre-registered test).
- P3 refuted → the exploratory gain was selection on the test problems; the word-problem claim is unchanged.
- P5 refuted where the cascade pays → the stratified account does not explain the gain (reported).

Expected (not a rule): P1 holds (+0.5 to +1.5), P2 inconclusive, P3 holds narrowly (OptiBench's third gave +1.65 [+0.26, +3.29]),
P4 inconclusive, P5 holds.

## Results, part 1: stored rows (XP-P1, XP-P2; 2026-10-31 08:5x UTC; `results/xpeer_models.txt`)

| N | cascade − SB→T→T, peer gpt-oss-20b | predicted | with Qwen3.5-9B as the peer | verdict |
|---|---|---|---|---|
| Qwen3-14B-AWQ | +0.83 [−0.24, +1.89] (accuracy +0.77) | +1.50 | +0.04 [−0.87, +0.97] | XP-P1 refuted (not shown) |
| Nemotron-3-Nano | +0.15 [−0.60, +0.97] (accuracy +0.21) | +0.84 | −0.65 [−1.55, +0.27] | XP-P2 refuted (not shown) |

The stratified transfer overpredicts by 0.67 / 0.69 (by 1.85 on the development cell Qwen3.5-9B). Agreement by stratum (problem-seeds;
gpt-oss-20b vs Qwen3.5-9B): Qwen3-14B-AWQ only N right (40) 65.0 vs 37.5%, only the default right (137) 10.9 vs 8.8%, ratio 6.0 vs 4.3;
Nemotron-3-Nano (29 / 177) 44.8 vs 41.4%, 5.6 vs 9.6%, ratio 8.0 vs 4.3. XP-P5 so far: the ratio is higher with gpt-oss-20b in both
cells, its agreement where only the default is right is lower for Nemotron and not for Qwen3-14B-AWQ (P5 fails there). Reported, not
decided: in all four models gpt-oss-20b as the peer is 0.8–1.2 utility above Qwen3.5-9B / Qwen3-8B as the peer (point estimates; this
comparison was not pre-registered). XP-P3 / P4 (fresh problems) are decided when jobs 1287120–1287125 land.

## Addendum MAMO (written 2026-10-31 09:0x UTC, before any think row on MAMO; the OptiBench fresh rows are still being generated, none read)

**Why.** XP-P1 / P2 were not shown, so under the rules above the claim can change only for Qwen3-8B, and the only fresh test is on
OptiBench, the easiest set. A second fresh set from another source decides whether the gpt-oss-20b peer is a property of Qwen3-8B on
OptiBench-like problems or of the cascade. MAMO (EasyLP 652 + ComplexLP 211; 2405.13144) was used to develop the label-free library
(FORM) but never in the peer analyses; N's quick programs (formx) and gpt-oss-20b's are stored (3 seeds each), and the library fact the
think arms will receive is the stored one (the selector reproduces the stored fact source for all 863 × 3 models checked).

**Run.** Qwen3-8B and Qwen3-14B-AWQ, the short think (`NLOPT_SET=mamo run_form.py <m> formx <s> --think_budget 2000`) and the think
(`--tarm --think`, 16k), seeds 1–3, all 863 problems (tags q8b / q14a: rows opt_<m>_mamo_formx{tb2000,t}_s<s>.jsonl, new files). Analysis
`python3.11 poc/analyze_xpeer.py --mamo` (peers gpt-oss-20b and the other Qwen3 model; there are no Qwen3.5-9B quick programs on MAMO).
(Text restored 09:0x UTC: a shell heredoc had dropped the three commands in backquotes from the first commit of this addendum; nothing
else changed, no MAMO think row existed.)

- **XP-P6:** Qwen3-8B → gpt-oss-20b → SB→T→T minus SB→T→T on MAMO (863 problems): lower bound > 0.
- **XP-P7:** the same for Qwen3-14B-AWQ: lower bound > 0.
- Reported: EasyLP and ComplexLP separately; the strata and their agreement rates; the Qwen3 peer.

**Decision (added; the rules above stand).** P3 and P6 hold → for Qwen3-8B the word-problem claim changes on two fresh problem sets
(the recipe's word-problem default for Qwen3-8B becomes N → gpt-oss-20b agrees → N, else SB→T→T), stated as model-specific because P1
was not shown. P4 and P7 hold → the same for Qwen3-14B-AWQ, and with P3 / P6 the claim is stated for both Qwen3 models. P3 or P6
refuted → the Qwen3-8B gain is not shown out of sample and the word-problem claim stays.

Expected (not a rule): P6 inconclusive (EasyLP is mostly solved by every arm, so gains come from tokens; ComplexLP is small), P7
inconclusive.
