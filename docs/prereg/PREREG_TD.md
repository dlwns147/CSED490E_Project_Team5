# Pre-registration TD: put the thinking mode's programs into the quick mode

Written 2026-10-30 21:4x UTC, before any training-data row (`poc/td_gen.py`), any training, and any held-out row of the trained
models. Results go below.

**Why it could change the claim.** On optimization word problems the peer-check cascade saves nothing (HO-PA: +0.01 [−0.81, +0.81]
utility over SB→T→T) because Qwen3-8B's quick program is rarely right (30.1%). A perfect quick program would gain +5.83 [+4.33, +7.47]
with the same untrained peer; making the quick program reliably right wherever one of its 3 samples is right would gain only +0.92
[−0.12, +1.99] (PREREG_SHARP.md, seeds 1–3). The gap is the problems the quick mode does not solve and thinking does: on 23.9% of the
held-out word problems no quick sample is right and the default is right at some seed (19.1% on SQL, 12.4% on tool calls). Plain RL
on the quick answer mostly reweights answers the model already samples (Yue et al. 2504.13837; SHARP tests how far that holds here),
so it may not reach them; WP-RL (running) is that test. The other source of right quick programs is the model's own thinking mode. For
answers that need a chain of thought, distilling thinking into direct answers fails (Yu et al. 2407.06023: complex math did not
distill); a program is different, because the formulation the think worked out is written in the program itself. **Hypothesis:**
fine-tuning the non-thinking mode on the thinking mode's right programs makes it right on problems where it never was (coverage
expansion), which fine-tuning on its own right quick programs (rejection-sampling fine-tuning) cannot; and that is what lets the cheap
path pay on word problems.

**Prior work.** Distilling System 2 into System 1 (2407.06023: four System-2 methods into direct answers, the math case fails); RFT
(2308.01825) and STaR (2203.14465): fine-tune on one's own right samples; Qwen3's mode fusion (2505.09388) trains both modes on one
model; TNT (2601.04805) uses the thinking response's solution part to bound the non-thinking reward in RL; hybrid models' no-think mode
leaks reasoning (2510.12680). Ours: DT (label-free SFT on checked programs of seven models) moved the library-usage fact into the
weights but not new problem types' formulations. New here: the thinking mode's verified programs, distilled into the same model's
non-thinking mode, against RFT with the same number of examples, measured by coverage expansion beyond 16 base samples and by the
peer-check cascade's accuracy and tokens.

**Data.** The first 2,000 of WP-RL's training problems (OptMATH-Train, decontaminated against all seven test sets; WP-RL's own
Random(0) order, so RL also saw them). Per problem (`poc/td_gen.py`, tag q8b, P_FREE, one RTX 3090 per shard, 6 shards): 8 quick
programs (T 0.7, top-p 0.95, 1,536 tokens: WP-RL's rollouts); the cut think (2,000 tokens, budget forcing) then its program; the full
think (16,000 tokens) where the cut think's program is not right. Programs run and are graded as in WP-RL (labels in training only).
**SFT sets** (`poc/td_build.py`): td = per problem the right thinking program (cut think's, else full think's); rft = per problem the
first right quick program; both cut to the smaller set's size by a Random(0) sample; target = the program in a Python block (DT).
**Training** (`poc/slurm/td_lane.sh`, DT's recipe unchanged: LoRA r 16 / α 32, 2 epochs, lr 1e-4, thinking off, `poc/sft_lora.py`),
merged, then the held-out cheap arm formx (OptiBench third 202, BWOR 82, LogiOR 92, OptMATH 100), seeds 1–3, tags q8btd / q8brft.
Analysis `poc/analyze_td.py` (written before any held-out row): the cascade N → its free check → Qwen3.5-9B's formx prints the same
value → N, else Qwen3-8B's SB→T→T (HO-PA's `policies`, as WP-RL); base coverage = SHARP's seeds 1–16 of base formx.

## Predictions (476 problems × 3 seeds pooled; paired 95% intervals over problems; utility = accuracy − 0.5 × ktokens)

- **TD-P1 (expansion):** on the problems no base formx seed 1–16 answers right, q8btd's quick right − q8brft's: lower bound > 0.
- **TD-P2:** q8btd's quick right − q8brft's, all problems: lower bound > 0.
- **TD-P3 (the claim):** q8btd → peer → SB→T→T minus SB→T→T: utility lower bound > 0.
- **TD-P4:** the q8btd cascade minus the q8brft cascade: utility lower bound > 0.
- Reported, not decided: per benchmark; the set sizes and the coverage table of the training problems (both / quick only / thinking
  only / neither); the quick programs' tokens (reasoning leaking into the non-thinking answer); each against base and against WP-RL's
  q8bwp1 (not data-matched: RL had 4,000 problems and on-policy rollouts).

## Decision

- P1, P3 and P4 hold → the quick mode learns from the thinking mode what RL cannot give it, and that makes the cheap path pay on word
  problems: the recipe's training step becomes "fine-tune the quick program on the thinking mode's verified programs" (PROJECT /
  REPORT / PROPOSAL), and the same is tested on SQL and tool calls next.
- P1 holds, P3 refuted → coverage expands but not enough to beat the default; reported with the cascade decomposition.
- P1 refuted → thinking's knowledge does not move into the non-thinking program here (as Yu et al. found for math); the quick mode's
  coverage is the limit, and on word problems the default stays.

Expected (not a rule): P1 holds narrowly, P2 holds, P3 inconclusive, P4 holds narrowly.

**Note (2026-10-30 22:4x UTC, before any TD training or held-out row; predictions unchanged).** SHARP's result changes the premise above:
on SQL and tool calls plain RL's whole cascade gain lies on items the base never answers right in 16 samples (+1.76 [+1.19, +2.37] /
+0.49 [+0.33, +0.67]), so RL does reach items the quick mode does not sample — it does not only reweight. TD still decides whether the
thinking mode's programs reach those items further than the model's own right quick programs (P1, P4); the comparison with RL (q8bwp1)
on the base-never items is reported, and rft, a sharpening method, is expected to gain on the covered items instead (reported).

**Data (2026-10-31 01:5x UTC, before any training or held-out row; predictions unchanged).** `poc/td_gen.py` finished on all 2,000 problems
(6 shards). Coverage of the training problems (8 quick programs; the cut think, else the full think): both right 1,045, quick only
236, thinking only 259, neither 460; quick samples right 5,756 / 16,000 (36.0%); the cut think's program right on 822. Sets: td 1,304
→ 1,281 by the Random(0) sample, rft 1,281 (the smaller); target length (characters) td mean 1,702 / p95 2,688, rft 2,008 / 3,047
(the thinking programs are shorter). The container writes `optmath_train/td/` as root, so the two sets are written one level up
(`$POC_DATA/optmath_train/sft_{td,rft}_q8b.jsonl`; `td_build.py` and `td_lane.sh` changed only in that path). Training and
held-out runs: jobs 1285851 (td) and 1285852 (rft).

## Results (2026-10-31 04:1x UTC; jobs 1285851 / 1285852; `python3.11 poc/analyze_td.py 16` → results/td.txt)

| | OptiBench third | BWOR | LogiOR | OptMATH | pooled (476) |
|---|---|---|---|---|---|
| quick right: base / td / rft | 50.5 / 47.2 / 61.1 | 15.4 / 16.7 / 17.5 | 15.6 / 15.9 / 14.5 | 14.3 / 12.0 / 17.0 | 30.1 / 28.5 / 35.3 |
| cascade − SB→T→T: base | +0.64 | −0.87 | −0.88 | +0.27 | +0.01 [−0.81, +0.81] |
| td | −0.28 | −1.04 | −0.79 | +0.21 | −0.41 [−1.12, +0.31] |
| rft | +1.75 | −0.17 | −0.29 | +1.03 | +0.87 [−0.08, +1.86] |

- **TD-P1 holds:** on the 227 problems no base sample of 16 answers right, td's quick right − rft's +1.47 [+0.59, +2.50] points
  (2.1% vs 0.6%: 14 vs 4 of 681 problem-seeds).
- **TD-P2 refuted** (the other way): td − rft −6.79 [−9.45, −4.20] points on all problems; td is below the base (−1.61 [−3.92, +0.84]).
- **TD-P3 refuted:** td cascade − SB→T→T −0.41 [−1.12, +0.31].
- **TD-P4 refuted** (the other way): td cascade − rft cascade −1.28 [−2.16, −0.41].
- Reported: quick tokens base 0.77k, td 0.90k, rft 0.82k. **Decomposition** of cascade − SB→T→T into the two kinds of problem (each
  part's contribution to the pooled mean): base-never base −0.66, td −0.73, rft −0.67 (the cheap path's cost; the new right answers do
  not change it); covered base +0.67, td +0.32, rft **+1.54 [+0.65, +2.47]**. On word problems the training gain that reaches the
  cascade is sharpening on the problems the base covers, unlike plain RL on SQL and tool calls (SHARP: all on base-never items).
- **Mechanism (raw programs, the 1,428 problem-seeds).** td's programs pass the check more often (916 vs base 801, rft 890) and are
  right less often when they pass (44.1% vs 53.3% / 56.2%): 512 passing wrong programs vs 374 / 390 — training on the thinking mode's
  programs raised the leak. The thinking programs of the training set use CP-SAT (588 of 1,281) and GLOP (197) where the quick
  programs use SCIP (rft set: CP-SAT 344, GLOP 1); the td model carries that choice to the held-out problems: GLOP in 212 programs
  (base 52, rft 9), 74 of them with integer variables, which GLOP solves as the LP relaxation, printing a wrong value that passes
  (read: optibench-360 prints 150 for 390 and optibench-285 19 for 20, both GLOP with IntVar where the base used SCIP; 53 of the 60
  OptiBench problem-seeds the base got right and td lost are passing wrong values). The quick mode copies the think's choice of solver
  without the reasoning that made it (the think decides integrality first) — the failure Yu et al. (2407.06023) report for math, here
  with its mechanism. WP-RL's q8bwp1 rows are not in yet (reported in PREREG_WPRL when they are).
- **Decision (as pre-registered):** P1 holds, P3 refuted → coverage expands, not enough to beat the default (above, with the
  decomposition); P4 refuted → the thinking programs are not the better training target. The recipe's training step stays training on
  the model's own checked quick programs (RFT here, plain RL on SQL / tool calls); the thinking mode's programs as SFT targets
  weaken the free check.

**Note (2026-10-31 04:1x UTC, after the results; a bound, not a test).** Why new answers cannot pay much here: in the peer cascade a right quick
program is accepted only where the peer prints the same value, and Qwen3.5-9B's quick program is right on 12.6% of the 227
base-never problems (65.3% of the 249 covered ones). A perfect quick program (always right, base tokens) would contribute +2.11
[+1.06, +3.31] on the base-never problems and +3.71 [+2.56, +5.01] on the covered ones (sum +5.82 = the ceiling above). td reached
2.1% of the way on the base-never problems; RFT reached about a third of the covered ceiling (+1.54 − base +0.67 of +3.71 − 0.67).
With this peer, coverage expansion on word problems is capped by what the peer also answers: the bilinear account's term
P(N right) × P(peer right) is small where the peer is weak — the same cap as on tool calls (P(peer right, default wrong)).

## Addendum RF: RFT on WP-RL's 4,000 problems (written 2026-10-31 04:1x UTC, before any of its rows and before any WP-RL held-out row)

**Why it could change the claim.** TD's result: on word problems training pays by sharpening (RFT's cascade gain is all on the
problems the base covers, +1.54 [+0.65, +2.47]; total +0.87 [−0.08, +1.86] over the default, not significant). Two open questions
decide the recipe's training step: (a) does sharpening make the word-problem cascade pay (the claim says it saves nothing there)?
(b) is on-policy RL needed — WP-RL (plain RL, 63 rounds on 4,000 OptMATH-Train problems, 8 rollouts each, ~14 h on 3 GPUs) — or does
one round of RFT on the same problems and the same number of samples do as well (~3 h)? Prior work: RFT gains with more distinct
right samples (2308.01825); expert iteration (ReST-EM, 2312.06585, TMLR) and a rejection-sampling baseline trained only on rewarded
samples are competitive with GRPO / PPO, GRPO's edge coming mostly from dropping prompts with no right sample (RAFT++, 2504.11343);
in the project, plain RL on SQL / tool calls (CV-1, TC-RL). New here: the comparison inside a check-gated cascade, with the gain split
by base coverage (sharpening vs new answers) and the check's precision reported.

**Run.** 8 quick programs per problem for WP-RL's problems 2,001–4,000 (`TD_FROM=2000 TD_ARMS=quick poc/td_gen.py q8bq2 4000`, the
same prompt, sampling and grading as TD's quick programs); `python3.11 poc/td_build.py q8b --rft-all q8bq2` → sft_rft4k_q8b (per
problem the first right program of 8, all 4,000 problems, no size matching); the TD lane unchanged (DT's recipe; tag q8brft4k);
`python3.11 poc/analyze_rf.py` (written and tested before any row: with TD's rows standing in it reproduces TD's numbers).

**Predictions** (476 problems × 3 seeds, paired 95% intervals over problems, utility = accuracy − 0.5 × ktokens):
- **RF-P1 (the claim):** rft4k → peer → SB→T→T minus SB→T→T: lower bound > 0.
- **RF-P2 (scale):** rft4k cascade − rft cascade (2,000 problems): lower bound > 0.
- **RF-P3 (RL needed?):** rft4k cascade − WP-RL's q8bwp1 cascade: lower bound > −0.5 (non-inferior within 0.5 utility points,
  1,000 tokens per problem); if the lower bound is above 0, RFT wins.
- Reported: quick right, tokens, right | passes, per benchmark, the base-never / covered split for each arm.

**Decision.** P1 holds → the word-problem claim changes: with the quick program sharpened by one round of RFT, the peer cascade beats
the default on word problems too (PROJECT / REPORT / PROPOSAL). P3 holds (non-inferior) → the recipe's training step is one round of
RFT (cheaper than RL by about 5× in GPU time here); P3 refuted → on-policy RL is needed. P2 refuted → the 2,000-problem RFT is
already at its data plateau.

Expected (not a rule): P1 holds narrowly (+1.0 to +1.5), P2 inconclusive, P3 holds.
