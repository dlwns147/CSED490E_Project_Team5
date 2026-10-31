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

**Note on power (2026-10-31 09:0x UTC; computed after part 1, not part of any rule).** Per problem (seed means) the cascade − default difference has a
standard deviation of 9–13 utility points (Qwen3-8B 9.8, Qwen3.5-9B 12.9, Qwen3-14B-AWQ 11.6, Nemotron 9.0), because only the two rare
strata move accuracy and each move is ±100. An effect of +0.8 on 476 problems is 1.6 standard errors (power ≈ 35% at 95%): XP-P1 "not
shown" is what a true +0.8 would usually give, and the predictions above did not state power. The same numbers bound the recipe: 80%
power for a +1 effect needs 500–1,500 labelled problems (gpt-oss-20b vs the Qwen peer: 500–1,100), so a 30-label pilot (standard error
1.5–2.4) cannot choose the peer; the peer has to be a fixed rule validated on held-out problems, as XP-P3 / P4 / P6 / P7 do.

## Addendum B: the peer as the check of every program the default would accept (written 2026-10-31 10:1x UTC; the OptiBench and MAMO think lanes are still running and no fresh outcome has been read, only row counts)

**Why.** VER put the largest ceiling on gating the default's own short-think program, not the cheap one (labels as the check: VD − D
+4.4, VN − D +2.6, both +5.6), and its trained verifier failed there because its false accepts fall where thinking is right. The
peer's quick program, already paid for when N passes, can check SB's passing program too: **PND** = N → the peer prints the same value
→ N; else SB → SB passes and the peer prints the same value → SB; else T→T (the peer runs at most once per problem). **PD** = the same
gate on SB without the N step.

**Theory (stratified, as above).** Rejecting SB's passing program replaces it with T→T. Split SB's passing programs by (SB right,
T→T right); rejecting gains 100 × (T→T right − SB right) − λ × T→T's ktokens, so PD − D = Σ share × (1 − the peer's agreement) × gain −
λ × the peer's ktokens × P(SB passes and the peer is not yet paid). With a perfect check the ceiling is the (SB wrong, T→T right) and
(SB wrong, T→T wrong) strata: Qwen3-8B +3.4, Qwen3-14B-AWQ +3.5, Nemotron +2.3, Qwen3.5-9B +1.1 (its full thinks are 29k tokens, so
rejecting a wrong program that T→T also gets wrong costs 13.8). The two decisive strata are (SB wrong, T→T right), where the peer must
disagree, and (SB right, T→T wrong), where it must agree; the second is where SB beats the full think, so gating SB can pay only for a
model whose full think is better than its short think on the problems the short think passes (shares of problem-seeds: Qwen3-8B 4.6 vs
2.9%, Qwen3-14B-AWQ 4.6 vs 3.5%, Qwen3.5-9B 3.6 vs 4.3%, Nemotron 4.0 vs 4.7%; the same sign as T→T − D in accuracy: +1.6, +1.2, −0.8,
−0.7).

**Exploratory (post hoc on the 476 stored problems × 3 seeds; `python3.11 poc/analyze_xpeer.py --gate`, results/xpeer_gate.txt;
these cells chose the hypothesis).** Accuracy @ ktokens and utility differences (paired 95% intervals):

| N, peer gpt-oss-20b | D | T→T | PEER | PND | PND − D | PND − PEER | PND − T→T |
|---|---|---|---|---|---|---|---|
| Qwen3-8B | 53.2% @ 10.0k | 54.8% @ 12.6k | 54.4% @ 10.2k | 56.7% @ 12.6k | +2.31 [+0.88, +3.74] | +1.11 [−0.08, +2.28] | +1.95 [+1.00, +2.98] |
| Qwen3-14B-AWQ | 54.3% @ 8.6k | 55.5% @ 10.8k | 55.1% @ 8.5k | 57.0% @ 10.6k | +1.67 [+0.01, +3.26] | +0.84 [−0.40, +2.18] | +1.61 [+0.32, +2.88] |
| Qwen3.5-9B | 57.9% @ 20.2k | 57.1% @ 29.3k | 58.6% @ 19.1k | 58.7% @ 24.3k | −1.27 [−2.87, +0.35] | −2.53 [−3.77, −1.34] | +4.01 [+2.38, +5.61] |
| Nemotron-3-Nano | 59.6% @ 12.0k | 58.9% @ 16.2k | 59.8% @ 12.1k | 60.5% @ 16.2k | −1.16 [−2.82, +0.61] | −1.31 [−2.81, +0.36] | +1.64 [+0.26, +3.12] |

With the Qwen peer instead, PND − D is +0.55 / +0.39 / −4.69 / −3.16 (n.s. for the Qwen3 models). gpt-oss-120b (a bound; not on one
RTX 3090): +2.69 [+1.35, +4.07] / +2.60 [+1.09, +4.18] / +1.33 / +0.00. The peer's agreement on SB's passing programs (gpt-oss-20b,
Qwen3-8B): SB wrong and T→T right 7.7% (65 problem-seeds), SB right and T→T wrong 59.5% (42), both right 86.1%, both wrong 46.2%.
PND is the most accurate policy in all four models (+0.6 to +3.5 points over D, +1.6 to +2.1 over T→T) at 1.2–1.35 × D's tokens; at
λ = 0.5 it pays for the two Qwen3 models and not for the two whose full think is not better than their short think. Also tried and
dropped: gating the full think's program too (else the second think): Qwen3-8B +1.59, Qwen3.5-9B −4.19.

Prior work (IDs opened 2026-10-31): agreement as the deferral rule at every level of a cascade (ABC, 2407.02348); a weaker model's
answer consistency (CoT vs program samples) as the gate to a stronger model (Yue et al., 2310.03094, ICLR 2024); cross-model consensus
as a selector, with a shared-error floor (LLM-jury, 2607.10139). In these the escalation is to a larger model. **New here:** the
escalation is a longer think of the same model, the check is one cheap cross-family program reused at two steps, and the stratified
account says in advance at which step and for which model the gate pays.

**Predictions (the fresh rows of XP-P3 / P4 / P6 / P7; nothing new is run; PND − D, utility, paired 95% intervals over problems).**
- **XP-P8:** Qwen3-8B, OptiBench's other 403 problems: lower bound > 0.
- **XP-P9:** Qwen3-8B, MAMO (863): lower bound > 0.
- **XP-P10:** Qwen3-14B-AWQ, OptiBench's other 403: lower bound > 0.
- **XP-P11:** Qwen3-14B-AWQ, MAMO: lower bound > 0.
- Reported: PD − D, PND − PEER, PND − T→T; SB's strata with the peer's agreement; PD − D predicted from the same model's agreement by
  stratum on the 476 stored problems; the Qwen3 peer; EasyLP and ComplexLP.

Power (per-problem SD of PND − D on the stored rows: Qwen3-8B 16.0, Qwen3-14B-AWQ 18.4): if the true effect is the exploratory one,
P8 has power 0.83 and P9 0.99 (P10 0.45, P11 0.76); if it is half of it, 0.30 / 0.56 (0.15 / 0.27).

**Decision (separate from the rules above, which stand for PEER).** P8 and P9 hold → for Qwen3-8B the word-problem default becomes PND:
the cheap path pays once a cross-family peer checks both cheap steps (the claim changes from "saves nothing" to "more accurate than
the default and than T→T"; the numbers as measured). P10 and P11 hold as well → stated for both Qwen3 models. The scope rule (gate the
short think only for a model whose full think beats it on its passing problems, on labelled development rows) is the theory's
condition, untested out of sample for Qwen3.5-9B and Nemotron. P8 or P9 refuted → PND is not shown out of sample and the default for
Qwen3-8B is decided by XP-P3 / P6 alone.

Expected (not a rule): P8 holds or inconclusive, P9 inconclusive (EasyLP: SB and T→T are mostly right, so the decisive strata are
small), P10 / P11 inconclusive.

**Note on addendum B (2026-10-31 10:1x UTC; computed after it was written, from stored SQL rows; not a test).** The scope condition was checked
on the other task with stored think rows, text-to-SQL (SQL-1 dev 1,530 and SQL-PA's fresh 1,338 BIRD-train questions; peer Qwen3.5-9B /
Qwen3-8B). There the full think is not better than the short think (T→T − D accuracy −0.4 to +0.8), the two decisive strata are equal
in size (Qwen3-8B fresh 2.9 vs 3.1% of question-seeds), and gating SB adds nothing to the peer cascade: PND − PEER +0.27 / +0.09 /
−0.93 (fresh; dev −0.24 / +0.25 / +0.36), as the condition says.

## Addendum C: gpt-oss-20b as the peer on text-to-SQL (written 2026-10-31 10:1x UTC, before any gpt-oss-20b SQL row exists)

**Why.** The word-problem result says a peer from another lab agrees far less often with the cheap answer's wrong outputs where the
default is right (4.7% vs 12.3%). If that is a property of the peer's lineage and not of word problems, it holds on the task where the
peer cascade already pays with a Qwen peer (SQL-PA, CV-1), and the recipe's check becomes one rule across tasks: another lab's cheap
model. On SQL the evidence so far points the other way: Nemotron-3-Nano (another lab) was a worse peer than Qwen3.5-9B (pooled over
the two sets, Qwen3-8B as N: −1.44 [−2.01, −0.90]; `python3.11 poc/analyze_xpeer.py --sql n3n`, the analysis below run with Nemotron in
place of gpt-oss-20b as its smoke test).

**Theory (stratified account on SQL; Qwen3-8B, both sets pooled, 8,575 question-seeds).** Accepting N's passing query instead of
SB→T→T gains +100.9 where only N is right (4.9% of question-seeds), −99.4 where only the default is right (10.2%), about +0.5 elsewhere.
Qwen3.5-9B agrees with 54.2% and 17.1% of those (ratio 3.2; break-even 10.2 × 99.4 / (4.9 × 100.9) = 2.05 plus tokens). If gpt-oss-20b
agreed on SQL as it does on Qwen3-8B's word problems (63.9 / 4.7%), N → gpt-oss-20b → D would gain about +1.6 over N → Qwen3.5-9B → D
(+0.5 from the first stratum, +1.3 from the second, −0.15 for its longer reasoning at about 400 tokens); with Nemotron's rates
(38.0 / 23.1%) it would lose about 1.4.

**Run.** gpt-oss-20b, low reasoning effort, the quick query only (`SQL_ARMS=quick`: SQL-1's prompt, 2k cap including reasoning, the
same per-question seeds), BIRD dev (1,530, tag oss20) and SQL-PA's fresh BIRD-train questions (1,338, tag oss20pa), seeds 1–3; one RTX
3090 job per seed: `sbatch -J xsql_s<s> -x n19,n22 poc/slurm/job.sh poc/slurm/lane.sh --seq --vllm '--max-model-len 24576'
openai/gpt-oss-20b xsql_s<s> 'POC_REASONING_EFFORT=low SQL_ARMS=quick $P poc/run_sql.py oss20 <s>' 'SQL_SPLIT=train
SQL_IDS=/NAS/SJ/POSTECH/nlp_data/bird/pa_ids.txt POC_REASONING_EFFORT=low SQL_ARMS=quick $P poc/run_sql.py oss20pa <s>' '$P
poc/grade_sql.py oss20 <s>' 'SQL_SPLIT=train $P poc/grade_sql.py oss20pa <s>'`. Analysis `python3.11 poc/analyze_xpeer.py --sql`.
N = Qwen3-8B, Qwen3-14B-AWQ (Qwen peer: Qwen3.5-9B) and Qwen3.5-9B (Qwen peer: Qwen3-8B), their stored N / SB / T rows; cascade =
N → the peer's quick query returns the same rows → N, else SB→T→T; the peer's tokens (reasoning included) counted when N passes.

**Predictions (both sets pooled, 2,867–2,868 questions; paired 95% intervals over questions, seed means; utility).**
- **XC-P1:** Qwen3-8B, N → gpt-oss-20b → D minus N → Qwen3.5-9B → D: lower bound > 0.
- **XC-P2:** Qwen3-14B-AWQ, the same: lower bound > 0.
- **XC-P3:** Qwen3.5-9B, N → gpt-oss-20b → D minus N → Qwen3-8B → D: lower bound > 0.
- **XC-P4 (mechanism):** in each of the three, gpt-oss-20b agrees less often than the Qwen peer where only the default is right
  (point estimates, counts reported).
- Reported: each cascade − D; per set (dev, fresh); the strata; the peer's tokens and its truncated (2k) replies; gpt-oss-20b's own
  accuracy and leak.

Power (per-question SD of a peer-vs-peer difference on these sets 14–18): standard error ≈ 0.30, so +1.0 is detected with power about
0.9 and +0.6 with about 0.5.

**Decision.** At least 2 of XC-P1..P3 hold → on SQL the recipe's peer becomes gpt-oss-20b; with XP-P3 the claim "the check is a cheap
model from another lab" holds on two task types (PROJECT / REPORT / PROPOSAL), and the same peer is pre-registered on tool calls
(BFCL). 0–1 hold → the Qwen peer stays on SQL, and whatever gpt-oss-20b does on word problems is task-specific (reported with the
strata: which stratum differs).

Expected (not a rule): XC-P1..P3 inconclusive (the Nemotron result says lineage alone does not lower the costly agreement on SQL;
gpt-oss-20b's reasoning may), XC-P4 holds in 2 of 3.
