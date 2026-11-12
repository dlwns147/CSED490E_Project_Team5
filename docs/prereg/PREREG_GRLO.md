# PREREG_GRLO: does check-only RL on the quick grid translation work on a mixture-of-experts model? gpt-oss-20b, registered 2026-11-12 11:4x UTC, before any training round

**Why.**
- Label-free RL on the quick translation now holds for two dense families (Qwen3-8B, Granite-4.1-8B; PREREG_GRLLF, PREREG_GRLX) and two sizes (8B, 32B; PREREG_GRL32). All are dense transformers. The user asked for other architectures (2026-11-12).
- gpt-oss-20b is a mixture-of-experts model (32 experts, 4 active per token) from a third family. It reasons in a separate channel before it answers, even at low effort, so the trained policy is its analysis plus its program.
- RL on mixture-of-experts models is known to be less stable. The trainer and the sampler route tokens differently, which makes the trained policy differ from the sampled one (Rollout Routing Replay, 2510.11370; GSPO, 2507.18071). So this is a real test, not a formality.

**Feasibility, checked before registering** (one 96 GB GPU, `poc/cv_train.Policy`).
- The experts are dequantized from MXFP4 to bf16, with eager attention because of gpt-oss's attention sinks. LoRA r 16 sits on the attention projections only, because the experts are fused parameters, not linear layers. That is 8.0 M trainable parameters, and the model loads in 10 s at 39.0 GiB.
- The trainer's log-probabilities (prompt keys cached, then the completion; per-layer masks for the 128-token sliding window) agree with a plain full forward pass within the model's own noise. Over 300 completion tokens, the mean per-token difference is 0.061 nats against the trainer, and 0.054 between two plain forward passes that differ only in length. Qwen3-8B's noise in the same test is 0.010, so the mixture-of-experts model is about 5× noisier in bf16.
- Training uses the exact tokens vLLM sampled (`return_token_ids`; analysis and final channels), not a re-tokenized answer.

**Method.**
- GRLLF's cross-fitted label-free run: same folds, loop, settings, prompt (arm gtr's first round) and reward (`--reward count1`: the program has exactly one solution; no labels).
- Changes:
  - The base is `/SSD/huggingface/openai/gpt-oss-20b`, with reasoning effort low, as in gtr's rows.
  - The sampling cap is 2048 tokens instead of 1536, because gpt-oss's first rounds include its analysis: 95th percentile 1793 tokens on GridPuzzle.
  - LoRA sits on attention only, as above.
- Base rows: `oss20`, arm gtr, seeds 4–6, both sets, already collected with effort low. Quick step right with one solution: GridPuzzle 60.5%, Mitra-Baral 85.1%; wrong with one solution 2.3% and 3.2%.
- Trained tags `oss20grlo0` and `oss20grlo1`, evaluated with `python poc/gp_eval.py --quick oss20 lf=oss20grlo0+oss20grlo1`.

**Predictions** (GridPuzzle decides; Mitra-Baral reported).
- **O-P1.** lf − base, right count-1 share: interval above 0.
- **O-P2 (no hacking).** lf − base, wrong count-1 share: upper bound below +2.0 points.
- **Reported.** The training reward by epoch.

**Decision.**
- **Both hold:** check-only RL on the cheap translation is stated for dense and mixture-of-experts models.
- **O-P1 fails:** the method is stated for dense models. Mixture-of-experts is reported as a limit, with the trainer–sampler gap as the suspected cause. Two other differences are confounds: LoRA on attention only, and training on the analysis channel.
- **O-P2 fails:** reward hacking on this model is reported, with cases.

**Runs.** On the paper-extension server, two lanes (fold 0 and fold 1), each with a vLLM GPU and a trainer GPU, as the IFRL lanes free their GPUs. A two-round smoke run (`--smoke 32`) checks the loop end to end first; its adapter is discarded.
