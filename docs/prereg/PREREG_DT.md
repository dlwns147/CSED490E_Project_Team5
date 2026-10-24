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
