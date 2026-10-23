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
