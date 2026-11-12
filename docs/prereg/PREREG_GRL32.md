# PREREG_GRL32: does check-only RL on the quick grid translation hold at 4× the size? Qwen3-32B (full precision), registered 2026-11-12 08:1x UTC, before any training round

**Why.**
- All RL results on grids so far are 8B dense models (Qwen3-8B; Granite-4.1-8B in GRLX). The training-free ladder pays most with Qwen3-32B (AWQ, +11.0 over the best baseline on GridPuzzle), so the larger model is where a trained quick step matters most.
- A larger model is also a harder test of the claim. Its quick step is already right 60.6% of the time on GridPuzzle, with 97.0% count-1 precision (AWQ rows, seeds 4–6), so less is left to gain.
- The user asked for more models and architectures (2026-11-12). gpt-oss-20b, a mixture-of-experts model, follows once the trainer supports expert layers.

**Feasibility, checked before registering.** The trainer (`poc/cv_train.Policy`, bf16 with LoRA r 16) loads Qwen3-32B in 211 s at 61.5 GiB. One group of 8 completions of 1200 tokens after a 1000-token prompt, with its backward pass and step, peaks at 63.9 GiB on one 96 GB GPU.

**Method.**
- GRLLF's cross-fitted label-free run unchanged: same folds, loop, settings, prompt, reward (the program has exactly one solution), and `--reward count1`.
- The only change is the base: `/SSD/huggingface/Qwen/Qwen3-32B` in bf16 for both the vLLM sampler and the trainer.
- Base rows: `q32` (full precision, arm `gtr`, seeds 4–6, both sets; started before this file, as base rows only). Trained tags `q32grllf0`, `q32grllf1`.
- Evaluated as GRLX on the quick step, seeds 4–6, because there is no full-precision 32B ladder: `python poc/gp_eval.py --quick q32 lf=q32grllf0+q32grllf1`.

**Predictions** (GridPuzzle decides; Mitra-Baral reported).
- **B-P1.** lf − base, right count-1 share: interval above 0.
- **B-P2 (no hacking).** lf − base, wrong count-1 share: upper bound below +2.0 points.

**Decision.**
- **Both hold:** check-only RL on the cheap translation is stated at 8B and 32B.
- **B-P1 fails:** the method is stated for 8B models, where the quick step leaves more to gain. The 32B result is reported as the limit.
- **B-P2 fails:** reward hacking at scale is reported, with cases.

**Runs.** On the paper-extension server, two lanes (fold 0 and fold 1), each with a vLLM GPU and a trainer GPU, started as the GRLV lanes free their GPUs.
