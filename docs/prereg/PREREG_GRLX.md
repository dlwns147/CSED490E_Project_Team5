# PREREG_GRLX: do RL on the quick grid translation, and its label-free form, carry to another model family? Granite-4.1-8B, registered 2026-11-12 05:5x UTC, before any training round

**Why.**
- GRL and GRLLF were run on Qwen3-8B only. Spurious Rewards (Shao et al. 2506.10947, ICML 2026) find RL gains that are specific to Qwen models, and recommend testing other families.
- Our loop takes one on-policy step per round, so their clipping mechanism does not apply. Still, a claim that "the free check trains the cheap step" needs a second family.
- The check is less precise on the second family, which tests the label-free form where it is most at risk:

| Base quick step, seeds 4–6 | Right with one solution | Wrong with one solution | Right : wrong |
|---|---|---|---|
| Granite, GridPuzzle | 18.0% | 5.1% | 3.5 |
| Granite, Mitra-Baral | 32.3% | 10.6% | 3.0 |
| Qwen3-8B, GridPuzzle | 31.9% | 6.8% | 4.7 |
| Qwen3-8B, Mitra-Baral | 49.6% | 4.3% | 11.5 |

- Model choice. Llama-3.1-8B-Instruct was also tried (`l8b`, seed 4). Its base quick step is right 4% of the time on the first round, and its programs fail 62–66% of the time. With so few groups that contain both rewards, RL would have nothing to work with. It is reported, not trained.

**Method.** GRL's loop, folds, settings and prompt, with the base model `/SSD/huggingface/ibm-granite/granite-4.1-8b` (`poc/slurm/grl_lane.sh` with `GRL_BASE`). The trainer's forward pass now applies Granite's embedding and logit multipliers (`poc/cv_train.py`). Before this file was registered, its log-probability was checked against the model's own forward: −22.72 against −22.54 on a 20-token completion, a bf16-level difference (Qwen3-8B: −41.13 against −40.43).
- **gold:** GRL's reward (one solution and the gold grid). Tags `g8bgrlg0`, `g8bgrlg1`.
- **lf:** GRLLF's check-only reward (one solution). Tags `g8bgrllf0`, `g8bgrllf1`.
- **Evaluation.** Granite has no stored thinking ladder, so the measure is the quick step itself (arm `gtr`, 3 rounds), seeds 4–6, against base rows `g8b` on the same puzzle-seeds. Command: `python poc/gp_eval.py --quick g8b gold=g8bgrlg0+g8bgrlg1 lf=g8bgrllf0+g8bgrllf1`. The same command on Qwen3-8B's rows gives right count-1 +23.3 [+18.1, +28.8] (gold) and +25.9 [+20.7, +31.4] (lf) on GridPuzzle.

**Predictions** (GridPuzzle decides; Mitra-Baral reported).
- **X-P1.** gold − base, right count-1 share: interval above 0.
- **X-P2.** lf − base, right count-1 share: interval above 0.
- **X-P3 (no hacking at lower precision).** lf − base, wrong count-1 share: upper bound below +2.0 points.

**Decision.**
- **All hold:** RL on the cheap translation, and its label-free form, is stated for two model families.
- **X-P1 holds and X-P2 or X-P3 fails:** the label-free form is stated with its limit, a check precise enough (Qwen right : wrong 4.7 holds, Granite 3.5 does not). Gold-reward RL is stated for both families.
- **X-P1 fails:** the RL result is stated for Qwen3-8B only.

**Runs.** On the paper-extension server: lf fold 0, lf fold 1 and gold fold 0 in parallel, then gold fold 1.

## Result (2026-11-12 09:1x UTC)

`python poc/gp_eval.py --quick g8b gold=g8bgrlg0+g8bgrlg1 lf=g8bgrllf0+g8bgrllf1`, seeds 4–6, all four lanes complete.

| Granite quick step | Right count-1 | Wrong count-1 | Precision | ktok |
|---|---|---|---|---|
| GridPuzzle, base | 18.0% | 5.1% | 77.9% | 1.65 |
| GridPuzzle, gold | 40.8% | 5.3% | 88.6% | 1.39 |
| GridPuzzle, lf | 38.4% | 5.1% | 88.3% | 1.51 |
| Mitra-Baral, base | 32.3% | 10.6% | 75.2% | 0.76 |
| Mitra-Baral, gold | 50.4% | 8.9% | 85.0% | 0.62 |
| Mitra-Baral, lf | 49.3% | 10.6% | 82.2% | 0.61 |

- **X-P1 holds.** GridPuzzle gold − base, right count-1: +22.8 [+18.1, +27.4]. Mitra-Baral: +18.1 [+9.6, +26.6].
- **X-P2 holds.** GridPuzzle lf − base: +20.5 [+15.8, +25.3]. Mitra-Baral: +17.0 [+8.5, +25.2].
- **X-P3 fails as registered.** GridPuzzle lf − base, wrong count-1: +0.0 [−2.6, +2.6]; the upper bound is above +2.0. Mitra-Baral: −0.0 [−5.3, +5.3].
- lf − gold: GridPuzzle right count-1 −2.3 [−7.0, +2.3], wrong −0.2 [−2.8, +2.5]. Mitra-Baral right −1.1 [−6.4, +4.6], wrong +1.8 [−2.5, +6.0].

**Decision (as registered: X-P1 holds, X-P3 fails).** Gold-reward RL on the cheap translation is stated for two families. The label-free form is stated with its limit. On Granite, whose check is less precise (right : wrong 3.5), we cannot rule out a rise in wrong passes of up to 2.6 points. The point estimate is zero and precision rose from 77.9% to 88.3%, so this is a failure to bound, not observed hacking; the paper reports it as the bound that was not met.
