# Pre-registration DT: putting the fact into the weights, with labels nowhere (direction 2)

Written 2026-10-23 23:5x UTC, before any training. RTX 3090 (LoRA on 2 GPUs). Results go below.

**Why.** The fact is the main lever (it raises the cheap program in 23 of 25 cells and thinking by up to +22.6), and the label-free library
supplies it at test time. The next step is to train it in: the recipe already produces label-free training data — programs that pass the
strict check (they run, print a value that is not 'No Best Solution', and two independent runs agree). A trained 4B specialist (STORM) led
our training-free recipe by 5.7 points on OptiBench at 8× the tokens; can label-free fine-tuning on our own checked programs close that?
And does training on a leaky check teach the model to be confidently wrong?

**Data (development sets only; nothing held out is used).** NL4OPT + IndustryOR (345) and MAMO (863): for each problem, one program that
passes the strict check, from the stored cheap runs of the seven development models (X6 `mipf` / `mip`, MAMO `mips` / `mip`; the program
most other models agree with, then the shortest; as `run_form.py`'s pool). Prompt = the solver-choice prompt (`P_FREE`) with no fact,
thinking off; target = that program in a Python block. No label is read anywhere (`poc/build_sft_data.py`).
**Training.** Qwen3-8B bf16, LoRA r = 16 / α = 32 on all attention and MLP projections, 2 epochs, lr 1e-4, max 3,072 tokens, loss on the
target only, 2 × RTX 3090 (`poc/sft_lora.py`); merged into `/SSD/huggingface/derived/Qwen3-8B-sft-checked` and served like Qwen3-8B (tag
`q8bsft`).
**Evaluation (held out, 3 seeds, as every other arm):** the `free` arm (no fact) on the OptiBench third, BWOR, LogiOR, OptMATH; the usage-
crash census and the leak (wrong among programs that run and print a value) from the same rows.
- **DT-P1:** the fine-tuned model *without* a fact is ≥ base Qwen3-8B *with* the label-free library (`formx`) on ≥ 3 of the 4 benchmarks.
- **DT-P2:** its usage-crash share falls below 5% on all four (the usage facts are in the weights).
- **DT-P3 (the risk):** the leak among its running programs rises by ≥ 5 points on ≥ 2 benchmarks (training on a leaky check teaches
  confident wrong programs).
**Decision.** P1 → label-free fine-tuning replaces the test-time fact for this model, and the next step is fact-first-then-think with the
fine-tuned model against thinking with the fact; P3 → the training data must be filtered by a stronger check (the solution checker).

*Training done (2026-10-24 00:3x UTC, job 1237676, 2 × RTX 3090): 1,127 examples (NL4OPT + IndustryOR 309, MAMO 818), 2 epochs, 142
steps, 36 minutes; train loss 0.137 (last steps ≈ 0.10). Merged model at /SSD/huggingface/derived/Qwen3-8B-sft-checked. Held-out
evaluation (the `free` arm, 3 seeds, tag `q8bsft`) submitted as job 1237729.*

### Results DT (2026-10-24 01:3x UTC; `python poc/analyze_dt.py`, 3 seeds, paired 95% intervals; usage crashes / leak = wrong among running programs)
| held-out benchmark | base, no fact | base + label-free library | **fine-tuned, no fact** | fine-tuned − base + library |
|---|---|---|---|---|
| OptiBench third (202) | 27.4% (crashes 24.6%, leak 39%) | 50.5% (6.4%, 32%) | **51.7%** (0.7%, 30%) | +1.2 [−5.4, +7.9] |
| OptiBench all (605) | 27.4% | 51.6% | **54.2%** (1.4%, 28%) | +2.6 [−1.2, +6.2] |
| BWOR (82) | 9.8% (16.3%, 75%) | 15.4% (15.4%, 69%) | **18.3%** (4.1%, 69%) | +2.8 [−3.7, +10.2] |
| LogiOR (92) | 9.4% (22.1%, 59%) | 15.6% (19.9%, 55%) | **16.7%** (12.3%, 61%) | +1.1 [−4.0, +6.2] |
| OptMATH (100) | 5.3% (13.0%, 70%) | 14.3% (14.3%, 70%) | 8.3% (10.0%, 72%) | **−6.0 [−11.3, −0.7]** |
Fine-tuned − base without a fact: +24.3 / +26.8 / +8.5 / +7.2 / +3.0 (the first four significant). Tokens unchanged (0.4–1.4k).
- **DT-P1 holds** (≥ base + library on 3 / 4: OptiBench, BWOR, LogiOR; all ties within their intervals; below it on OptMATH, −6.0).
- **DT-P2 refuted** (usage crashes < 5% on OptiBench and BWOR, not LogiOR 12.3% / OptMATH 10.0%: routing and large structured models need
  usages the development data rarely shows).
- **DT-P3 not observed** (the leak does not rise ≥ 5 points anywhere; it falls on OptiBench 39 → 30% and BWOR 75 → 69%): training on
  the strict check's programs did not teach confident wrong programs here.
- **Decision:** label-free fine-tuning on 1,127 of its own checked programs gives Qwen3-8B the library's gain without the library in the
  prompt (≈ +25 points on OptiBench), except on OptMATH, whose problem types the development sets do not cover. Next: fact-first-then-
  think with the fine-tuned model against thinking with the fact, and the fine-tuned model *with* the library (do they add?).

## Addendum DT2 (2026-10-24 01:3x UTC, before any run): the fine-tuned model inside the recipe
**Run** (tag `q8bsft`, 3 seeds): `formx` (cheap with the library) on the OptiBench third, BWOR, LogiOR; `formxt` (thinking with the library,
16k) on the same. Compared with base Qwen3-8B's THINK+F (HO-TF rows).
- **DT2-P1:** the library still adds on top of fine-tuning: fine-tuned + library ≥ fine-tuned free + 2 points on ≥ 2 of the 3.
- **DT2-P2:** FF with the fine-tuned model (its better cheap arm; its own thinking with the fact on a visible failure) ties or beats base
  THINK+F on ≥ 2 of the 3 (base FF+F lost on all three: −4.5 / −11.0 / −7.6).
- **DT2-P3:** fine-tuning on non-thinking programs leaves thinking intact: its THINK+F ≥ base THINK+F − 2 on ≥ 2 of the 3.

## Addendum DT-14 (2026-10-24 02:0x UTC, before any run): the same label-free fine-tuning on a second model
**Run.** Qwen3-14B (bf16; the AWQ copy cannot take LoRA here) fine-tuned exactly as DT (same 1,127 examples, LoRA r 16, 2 epochs), on 4 ×
RTX 3090; merged to /SSD/huggingface/derived/Qwen3-14B-sft-checked and served tensor-parallel on 2 × 3090 (tag `q14sft`). Baselines on
the same server setup: base Qwen3-14B bf16 (tag `q14b`) `free` and `formx`. Held-out OptiBench (all 605; the third reported as in DT),
BWOR, LogiOR, OptMATH, 3 seeds.
- **DT14-P1:** fine-tuned without a fact ≥ base with the library on ≥ 3 of the 4 (as DT-P1 for Qwen3-8B).
- **DT14-P2:** fine-tuned without a fact ≥ base without a fact + 10 points on OptiBench (the 8B gain was +26.8).
*DT-14 training done (2026-10-24 03:0x UTC, job 1237995, 4 × RTX 3090): 142 steps, 53 minutes, train loss 0.122; merged to
/SSD/huggingface/derived/Qwen3-14B-sft-checked; held-out `free` evaluation (tag `q14sft`, TP 2) submitted.*

### Results DT-14 (2026-10-24 03:4x UTC; `python poc/analyze_dt.py q14sft q14b`; Qwen3-14B bf16, 3 seeds)
| held-out | base, no fact | base + library | **fine-tuned, no fact** | fine-tuned − base + library |
|---|---|---|---|---|
| OptiBench third / all | 32.0% / 36.3% | 56.4% / 58.1% | **54.1% / 58.0%** (usage crashes 2.0%, leak 25 / 23%) | −2.3 [−8.9, +4.0] / −0.1 [−3.6, +3.2] |
| BWOR | 17.1% | 20.7% | **24.0%** (4.9%) | +3.3 [−2.4, +8.9] |
| LogiOR | 14.1% | 25.0% | 19.6% (6.9%) | −5.4 [−12.0, +1.1] |
| OptMATH | 8.7% | 14.0% | 9.3% (11.7%) | −4.7 [−10.7, +0.7] |
- **DT14-P1 refuted** (≥ base + library in 1 / 4 by point estimate; every difference is within its interval; on all 605 OptiBench
  problems a tie, −0.1). **DT14-P2 holds** (+22.1 over the base without a fact on the OptiBench third, +21.8 on all).
- **Reading (both models).** Label-free fine-tuning moves the *usage* part of the fact into the weights (usage crashes 16–28% → 2–7%;
  OptiBench +22 to +27 points with no fact), but the library's programs for similar problems still add on LogiOR / OptMATH, whose
  problem types the development data does not show. The leak does not rise (OptiBench 32–39% → 23–30%).

## Addendum DT3 (2026-10-24 03:5x UTC, before any run): label-free self-training on unlabeled problems
**Why.** Fine-tuning moved the usage fact into the weights but not the formulations of problem types the development data lacks (LogiOR,
OptMATH: −5 to −6 vs the library). Unlabeled problems of more types are available: 3,996 question texts (2,000 random from OptMATH-Train,
2,000 from OR-Instruct-3K; answers, code and completions dropped; 4 removed for ≥ 30% 8-gram overlap with a held-out problem;
`poc/build_unlabeled.py`). **Round 2:** the round-1 fine-tuned Qwen3-8B (`q8bsft`) writes a program for each, twice (`free`, seeds 1 and 2,
no thinking); the strict check keeps a problem's program when both run, print a value that is not 'No Best Solution', and agree. Base
Qwen3-8B is fine-tuned again from scratch on the development examples + these (same recipe) → `q8bsft2`, evaluated as DT (held-out `free`).
- **DT3-P1:** round 2 ≥ round 1 + 3 points on OptMATH or LogiOR (the types the new problems cover), at least one significant.
- **DT3-P2:** OptiBench and BWOR stay within ±3 of round 1.
- **DT3-P3:** the leak does not rise by ≥ 5 points on any benchmark.
**Decision.** P1 → label-free self-training on unlabeled problems extends the internalized fact to new problem types (no labels at any step).
*DT3 data (2026-10-24 05:2x UTC): the round-1 model solved 1,957 of the 3,996 unlabeled problems twice in agreement (OR-Instruct 1,129,
OptMATH-Train 828); with the development examples, 3,084 training examples (`build_sft_data.py --round2`). Round-2 training submitted.*

### Results DT2 (2026-10-24 06:1x UTC; `python poc/analyze_dt2.py` and the DT2-P1 table; 3 seeds; vs base Qwen3-8B thinking with the fact)
| | OptiBench (third) | BWOR | LogiOR |
|---|---|---|---|
| fine-tuned + library − fine-tuned free (cheap) | +3.8 [−1.2, +8.9] | −1.2 [−6.9, +4.9] | **−5.8 [−10.9, −0.4]** |
| fine-tuned THINK+F − base THINK+F | −3.3 [−6.9, +0.3] | +3.7 [−2.4, +9.8] | −4.0 [−10.1, +2.5] |
| FF with the fine-tuned model (free; own THINK+F on failure) − base THINK+F | −5.1 [−10.2, −0.0] @ 35% | **−10.2 [−17.5, −2.8]** @ 54% | **−14.5 [−21.7, −7.2]** @ 74% |
- **DT2-P1 refuted** (library adds ≥ 2 on 1 / 3; on LogiOR it now hurts). **DT2-P2 refuted** (FF ties base THINK+F on 0 / 3). **DT2-P3
  refuted** (thinking within 2 points on 1 / 3; −3.3 / −4.0 elsewhere, intervals include 0).
- **Reading.** Fine-tuning raises the cheap program to the level the library gave but does not fix the leaky check: on the hard benchmarks
  fact-first with the fine-tuned model still loses to thinking with the fact by 10–15 points. Training the fact in and choosing where to
  think are separate problems; the second still needs a stronger check (HO-VF) or the pilot.
*DT3 round-2 training done (2026-10-24 07:5x UTC, job 1238635): 3,084 examples, 386 steps, 2 h 25 min on 2 × RTX 3090, train loss 0.075;
merged to /SSD/huggingface/derived/Qwen3-8B-sft-r2; held-out `free` evaluation (tag `q8bsft2`) submitted.*

### Results DT3 (2026-10-24 09:0x UTC; round 2 = `q8bsft2`, round 1 = `q8bsft`, both without a fact; 3 seeds, paired 95% intervals)
| held-out | round 1 | round 2 | round 2 − round 1 | leak (wrong among running), round 1 → 2 |
|---|---|---|---|---|
| OptiBench third / all | 51.7% / 54.2% | 52.8% / 54.2% | +1.2 [−1.3, +3.6] / 0.0 [−1.4, +1.4] | 30 → 30% / 28 → 28% |
| BWOR | 18.3% | 15.0% | −3.3 [−6.1, +0.0] | **69 → 76%** |
| LogiOR | 16.7% | 14.5% | −2.2 [−6.5, +2.2] | 61 → 65% |
| OptMATH | 8.3% | 5.7% | −2.7 [−6.3, +0.7] | **72 → 82%** |
- **DT3-P1 refuted** (OptMATH −2.7, LogiOR −2.2; neither improves). **DT3-P2 refuted narrowly** (OptiBench unchanged; BWOR −3.3).
  **DT3-P3 refuted — the risk materialized:** the leak rises by 7 points on BWOR and 10 on OptMATH.
- **Reading.** Self-training on unlabeled problems of new types, filtered by the strict check (two runs agree), feeds the model its own
  consistent-but-wrong formulations: 1,957 of 3,996 problems passed, but on hard types agreement is a weak signal (the same leak that
  limits fact-first). Round 1 worked because its data came from seven models on the development sets; round 2's came from one model on
  harder, unfamiliar problems. **The check's leak bounds label-free self-training as it bounds the recipe**; a stronger filter (the
  solution checker, or agreement across different models) is the next test, and where the check is perfect (proofs) self-training has no
  such limit.

## Addendum DT4 (2026-10-24 09:0x UTC, before any run): a cross-model filter for self-training
DT3's filter (two runs of the same model agree) passed consistent wrong programs. HO-X found that a *different* model's program catches
the self-correlated errors. **Run:** gpt-oss-20b (low effort, `free`, one seed) on the same 3,996 unlabeled problems; keep a problem's
round-1-model program only if it runs, prints a value, agrees with its own second run **and** with gpt-oss-20b's value; retrain Qwen3-8B
from base on the development examples + these (`q8bsft3`), evaluate as DT.
- **DT4-P1:** fewer problems pass than in DT3 (< 1,957), and the leak does not rise over round 1 on any benchmark (≤ +2 points).
- **DT4-P2:** round 2b ≥ round 1 on OptMATH and LogiOR (point estimates), and ≥ round 2 (DT3) on BWOR / LogiOR / OptMATH.
**Decision.** P1 + P2 → cross-model agreement is the filter that makes label-free self-training safe; otherwise self-training on unfamiliar
problem types needs a perfect check (proofs).
*DT4 data (2026-10-24 09:3x UTC): gpt-oss-20b's value agrees with the round-1 model's agreed value on 1,348 of the 3,996 unlabeled
problems (DT3: 1,957; OR-Instruct 767, OptMATH-Train 581); with the development examples 2,475 training examples
(`build_sft_data.py --round2 --cross`). Training submitted (tag `q8bsft3`).*

### Results DT4 (2026-10-24 12:1x UTC; round 2b = `q8bsft3` (cross-model filter); 3 seeds, paired 95% intervals; leak = wrong among running)
| held-out | round 1 | round 2 (DT3) | **round 2b** | 2b − 1 | 2b − 2 |
|---|---|---|---|---|---|
| OptiBench all | 54.2% (28%) | 54.2% (28%) | 53.8% (27%) | −0.4 [−1.8, +1.0] | −0.4 |
| BWOR | 18.3% (69%) | 15.0% (76%) | **20.7%** (67%) | +2.4 [−0.8, +6.1] | **+5.7 [+2.8, +8.9]** |
| LogiOR | 16.7% (61%) | 14.5% (65%) | 16.7% (65%) | 0.0 [−3.6, +3.6] | +2.2 [−2.2, +6.5] |
| OptMATH | 8.3% (72%) | 5.7% (82%) | 7.7% (73%) | −0.7 [−4.0, +2.3] | +2.0 [−1.7, +5.7] |
- **DT4-P1 half holds** (fewer pass: 1,348 vs 1,957; the leak stays within +2 of round 1 except LogiOR +4). **DT4-P2 half holds** (≥ round 2
  on BWOR / LogiOR / OptMATH; ≥ round 1 on LogiOR but not OptMATH, −0.7).
- **Reading.** Agreement with a different model removes the harm of self-training (BWOR +5.7 over DT3, leaks back to round-1 levels) but
  does not add knowledge of the new problem types (round 2b ≈ round 1 everywhere). Label-free self-training on unfamiliar word problems is
  bounded by the check either way: a leaky filter teaches wrong formulations, a stricter one keeps only what the model already gets right.

## Addendum DT-P (2026-10-24 12:1x UTC, before any run): self-training where the check is perfect (proofs)
**Why.** DT3 / DT4: with a label-free but leaky check, self-training on unfamiliar problems learns the check's mistakes or nothing new.
In Lean a compiled proof is right, so self-training cannot learn wrong proofs; if the check is what bounds self-training, it should help
here. **Data (no label anywhere):** 2,000 random Lean Workbook statements (internlm/Lean-Workbook, its stored proofs dropped), minus any
sharing ≥ 30% of its 8-gram set with a miniF2F test statement (informal or formal); Qwen3-8B writes 4 cheap (non-thinking) proofs per
statement (X4 prompt, 8,192 cap); the Lean compiler keeps the compiled ones (one per statement, the shortest). Qwen3-8B is LoRA-fine-tuned
on them exactly as DT (tag `q8bprf`) and evaluated on miniF2F test with 8 cheap attempts per statement, batch-checked.
- **DTP-P1:** the fine-tuned model's cheap pass@8 on miniF2F test ≥ the base's + 5 statements (base: the expected pass@8 over its PL3
  32 cheap attempts).
- **DTP-P2:** its per-attempt success rate is ≥ 1.3 × the base's.
**Decision.** P1 → with a perfect check label-free self-training transfers to held-out statements, completing the contrast with DT3 / DT4:
the check, not the training, bounds self-improvement.
*DT-P withdrawn (2026-10-24 13:2x UTC, before any proof was checked): a related-work check showed Lean expert iteration with the compiler as
filter is established (Polu et al. 2022; DeepSeek-Prover; Goedel-Prover; STP, which reports plain expert iteration plateauing); the run
could not change our claim, so its 8 GPUs go to the open problem at the claim's weak point (docs/notes/RELATED_WORK.md).*

## Addendum DT5 (2026-10-24 14:3x UTC, before any run): does a better label-free check make self-training learn?
**Why it could change the claim / what is new.** DT3 / DT4: with self-consistency as the filter self-training learned the check's mistakes;
with cross-model agreement it learned nothing new. The 2k-token thinking-mode self-review (HO-VR) is a better label-free check (flags 65%
of wrong passing programs at 13% false alarms on word problems). Prior self-training filters are self-consistency, majority vote, a
teacher, or cross-model agreement (docs/notes/RELATED_WORK.md); a thinking-mode review of non-thinking outputs as the filter is not.
**Run.** Base Qwen3-8B, thinking cut at 2,000 tokens, reviews the round-1 model's seed-1 program for every unlabeled problem where it runs
(`run_review.py q8bsft 1 2000 free`, NLOPT_SET=unlabeled); keep a problem when the two round-1 runs agree **and** the review says CORRECT;
retrain from base on the development examples + these (`q8bsft4`); evaluate as DT.
- **DT5-P1:** fewer problems kept than DT3 (< 1,957); the leak stays within +2 points of round 1 on every benchmark.
- **DT5-P2:** round 2c ≥ round 1 + 3 points on OptMATH or LogiOR, at least one significant (it learns from new problem types).
**Decision.** P2 → a better label-free check turns self-training from harmful / neutral into useful; otherwise label-free self-training on
these problems stays bounded at round 1 whatever the filter, and the report says so.
*DT5 data (2026-10-24 17:3x UTC): base Qwen3-8B reviewed 3,106 runnable round-1 programs (accept 1,935, wrong 1,171, no verdict 0); 1,452
unlabeled problems pass both filters (DT3: 1,957; DT4: 1,348); 2,579 training examples. Training submitted (tag `q8bsft4`).*

### Results DT5 (2026-10-24 21:0x UTC; round 2c = `q8bsft4`, review-filtered; no fact; 3 seeds, paired 95% intervals vs round 1)
| held-out | round 1 (leak) | round 2 self-consistency | round 2b cross-model | **round 2c + review** | 2c − round 1 | tokens 1 → 2c |
|---|---|---|---|---|---|---|
| OptiBench all | 54.2% (28%) | 54.2% (28%) | 53.8% (27%) | 53.6% (28%) | −0.7 [−2.1, +0.7] | 371 → 494 |
| BWOR | 18.3% (69%) | 15.0% (76%) | 20.7% (67%) | 20.7% (67%) | +2.4 [−0.8, +6.1] | 921 → 1,008 |
| LogiOR | 16.7% (61%) | 14.5% (65%) | 16.7% (65%) | 14.9% (67%) | −1.8 [−5.8, +2.2] | 1,137 → 1,101 |
| OptMATH | 8.3% (72%) | 5.7% (82%) | 7.7% (73%) | 8.7% (70%) | +0.3 [−3.0, +3.7] | 1,424 → 1,579 |
- **DT5-P1 half holds** (1,452 kept < 1,957; the leak stays within +2 of round 1 on OptiBench, BWOR, OptMATH, not LogiOR: +6).
  **DT5-P2 refuted** (OptMATH +0.3, LogiOR −1.8; neither significant; base + library stays far ahead on OptMATH: 14.3%).
- **Raw.** The LogiOR programs that round 1 got right and 2c gets wrong (4 vs 1 the other way, seed 1) are ordinary formulation slips —
  a capacity bound used as the variable bound only, a data table referenced but never defined, a cost dictionary with colliding keys —
  not a harness effect.
- **Reading (DT3–DT5).** Three label-free filters of increasing quality (self-consistency; agreement with another model; agreement plus
  a thinking-mode review) take self-training from harmful to neutral, never to useful: round 2 stays at round 1 on every held-out
  benchmark, and the unseen problem types (LogiOR, OptMATH) stay where only the library of similar problems helps. On these word problems
  label-free self-training is bounded by what the model already solves; the review removes wrong programs but adds no new formulations.

## Addendum DT6 (2026-10-25 10:4x UTC, before any run): distil the short think into the non-thinking program, filtered by the check
**Why it could change the claim / what is new.** DT2: label-free fine-tuning on non-thinking checked programs moves the usage fact into
the weights but not the check (the leak stays); DT3–DT5: self-training on the fine-tuned model's own non-thinking programs never gets past
round 1. HO-SB: a 2k-token think before the program is what the leaky models lack. If training on the *short-think* programs (code only,
no reasoning text) lowers the non-thinking program's leak, the thinking step can move into the weights; if not, it must stay at inference.
Related work: System-2 distillation (Yu et al., 2024; distils System-2 outputs into System-1 with self-consistency filtering, works for
some tasks, not for math chain of thought), self-distillation for code without a verifier (2604.01193), execution-gated self-distillation
(2607.09709); none measures the effect on a free check's leak. **Run.** Base Qwen3-8B writes programs for the 3,996 unlabeled problems with
a 2,000-token think (`run_nlopt.py q8b_unlabeled free <seed> --think_budget 2000`, seeds 1–2, no fact); keep a problem when both runs
pass the free check and agree (the DT3 filter); retrain from base on the DT development examples + these (code-only targets, the
non-thinking prompt; tag `q8bsft5`); evaluate as DT (`free`, no fact, 3 seeds).
- **DT6-P1:** the leak (wrong among running programs) falls ≥ 5 points below round 1 (`q8bsft`: BWOR 69%, LogiOR 61%, OptMATH 72%) on
  ≥ 2 of the three.
- **DT6-P2:** accuracy ≥ round 1 + 3 points on OptMATH or LogiOR, at least one significant.
**Decision.** P1 → part of the thinking step moves into the weights without labels (reported with Direction 2); otherwise the short
think stays at inference and the report says distillation of it does not fix the leak.
