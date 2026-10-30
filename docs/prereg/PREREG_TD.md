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
