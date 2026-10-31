# Pre-registration WP-RL: train the quick program for word problems, check it with a peer

Written 2026-10-30 14:3x UTC, before any training round beyond the engineering smoke (2 rounds, not part of the results) and before any
held-out row of a trained model. Results go below.

**Why it could change the claim.** The trained-cheap-path recipe (plain RL on the non-thinking answer, another model's agreement as the
gate, the no-label default SB→T→T otherwise) beats the default on text-to-SQL (CV-1, +2.0) and tool calls (TC-RL, +1.35); training for
the cascade's own reward instead loses on both (C1w; TCRL addenda 2/3). Both are short-answer tasks. On optimization word problems — the
project's main task family — the untrained peer cascade saves nothing (HO-PA: Qwen3-8B → Qwen3.5-9B → SB→T→T vs SB→T→T, pooled over
OptiBench's third, BWOR, LogiOR and OptMATH, +0.01 [−0.81, +0.81] utility), because Qwen3-8B's quick program is rarely right (pooled
30.1%; Qwen3.5-9B's 40.3%) while the default costs 5–14k tokens. With a default that expensive, each right quick program the peer
confirms saves 2.5–7 utility points, so a quick program trained to be right is the lever the bilinear account points to (gain =
Σ_i Σ_y P_N(y|i) P_X(y|i) (r(y) − r_D(i) + 0.005 kd(i)) − tokens). If it works, the recipe holds on all three task types; if the
quick program improves and the cascade does not, word problems' shared formulation errors (HO-PA's error coincidence) are the limit.

**Prior work.** RL with solver-verified rewards for optimization modelling: SIRL (2505.11792, NeurIPS 2025: outcome + LP-file
rewards), STORM / CALM (2510.04204: solver-corrected reasoning traces, then RL; STORM-Qwen3-4B, which we ran: MAMO 81.8% at 8.4k tokens);
SFT: ORLM (2405.17743), OptMATH (2502.11102; its training set is our data). All train one model for accuracy, most of them thinking
models. New here: the trained *non-thinking* program as the cheap member of a peer-check cascade whose fallback is the thinking default,
judged on accuracy and tokens together.

**Data.** OptMATH-Train (HF Aurora-Gem/OptMATH-Train, 201,071 synthetic problems with the optimal objective as the answer;
`poc/prep_wptrain.py`): the problem text without its gurobipy note; all answers numeric; 50,908 longer than 4,000 characters dropped;
35,975 dropped because they share a lower-cased word 13-gram with a problem of any of the seven test sets (NL4OPT, IndustryOR, MAMO,
OptMATH-Bench, OptiBench, BWOR, LogiOR); 114,188 kept; a Random(0) sample of 8,000 written, of which training uses the first 4,000 in its
Random(0) order (63 rounds) (`$POC_DATA/optmath_train/wp_train_items.jsonl`).

**Run.** `poc/wp_train.py` (job `wprl`, `poc/slurm/wp_lane.sh`): CV-1's C1 loop unchanged except the task — LoRA r 16 on Qwen3-8B,
GRPO without std normalisation, 8 samples per problem, 64 problems per round, one step per round, lr 2e-5, no KL — on the held-out sets'
cheap prompt (`run_nlopt.P_FREE`: a program with a solver of the model's choice), samples up to 1,536 tokens (rollouts on a
2-GPU tensor-parallel server, the trainer on a third GPU); reward 1 if the program,
run in the sandbox as `run_nlopt` does (60 s, 4 GB), prints the gold optimum within the grader's tolerance (`run_nlopt.correct`), else 0.
Test: HO-PA's four held-out benchmarks (OptiBench's third, 202; BWOR 82; LogiOR 92; OptMATH 100: 476 problems), the cheap arm formx
(P_FREE / P_MIP plus a program for the most similar other problem from the label-free pool, the same prompt as every stored formx row)
with the final adapter, seeds 1–3, tag q8bwp1. Policies (`poc/analyze_wprl.py`, HO-PA's `policies`): SB→T→T (Qwen3-8B's stored
formxtb2000 / formxt rows); N → its free check → Qwen3.5-9B's formx program prints the same value → N, else SB→T→T, with the base N
(stored q8b formx) and with the trained N.

Smoke (2 rounds, 128 problems; not part of the results): the base model's programs run on 58% and are right on 41% of the
training samples, 45–50% of the problems give a mixed group (a gradient); 12.5 minutes per round with the rollouts on one GPU.

## Predictions (476 problems × 3 seeds, pooled over the four benchmarks; paired 95% intervals over problems; utility = accuracy − 0.5 × ktokens)

- **WP-P1 (training transfers):** the trained quick program right − the base's (formx): lower bound > 0.
- **WP-P2 (the recipe holds on word problems):** trained N → Qwen3.5-9B → SB→T→T − SB→T→T: utility lower bound > 0.
- **WP-P3 (training is what moves it):** trained cascade − base cascade: utility lower bound > 0.
- Reported, not decided: each benchmark's numbers; the accepted-wrong share where the default is right and the accepted-right share
  where it is wrong; the error coincidence of the trained N's passing wrong programs with the peer's (HO-PA's measure).

## Decision

- P2 and P3 hold → the trained cheap path with a peer check is the recipe on all three task types (PROJECT / REPORT / PROPOSAL).
- P3 holds, P2 refuted → training moves the cascade but not past the default: word problems need a stronger check than one peer.
- P1 holds, P3 refuted → better quick programs do not move the cascade: shared formulation errors (the peer confirms the wrong ones)
  are the limit, as the error coincidence will show.
- P1 refuted → RL on OptMATH-Train does not transfer to these benchmarks; the recipe on word problems stays training-free.

Expected (not a rule): P1 holds (+5 to +15 points, mostly fewer crashing programs), P3 holds (+0.5 to +2), P2 inconclusive or holds
narrowly.

## Results (2026-10-31 06:3x UTC; `results/wprl.txt`, `results/sharp_wp.txt`)

63 rounds (4,000 problems; training rewards 62–79% right in the last rounds), final adapter, formx seeds 1–3 on the 476 problems.

| test | result (95% interval) | verdict |
|---|---|---|
| WP-P1 trained quick right − base | +4.69 [+2.66, +6.79] points (30.1% → 34.8%) | **holds** |
| WP-P2 trained N → Qwen3.5-9B → SB→T→T − SB→T→T | +0.59 [−0.32, +1.55] utility | refuted (not shown) |
| WP-P3 trained cascade − base cascade | +0.58 [−0.14, +1.29] utility | refuted (not shown) |

Per benchmark (trained cascade − SB→T→T): OptiBench third +2.09 [+0.17, +4.07] (quick right 50.5 → 59.6%), BWOR −1.30, LogiOR −0.63,
OptMATH +0.23; the training gain is on the easiest set (OptiBench), none on OptMATH (14.3% → 14.3%).

**Reported quantities.** The peer agrees with 77.0% of the base N's right passing programs and 30.7% of its wrong ones; with the trained
N's, 77.8% and 29.9%: training raises how many passing programs are right (427 → 495 of 1,428 problem-seeds) but not how well the peer
tells them apart. Accepted wrong where the default is right: 0.91 → 0.84 points; accepted right where the default is wrong: 1.12 →
1.61. Error coincidence of passing wrong programs with the peer's: 62.2% → 60.1% (HO-PA's measure). Where the gain sits: on the 227
problems no base sample of 16 answers right, the trained cascade − SB→T→T is −0.54 (base −0.66, the quick program's cost); on the
covered problems +1.13 (base +0.67): the small gain is sharpening, as RFT's (+1.54 there, PREREG_TD.md). Only 8 of 497 trained right
samples (1.6%) are on base-never problems (SH-P3, PREREG_SHARP.md).

**Theory check.** Accepting a passing quick program instead of running the default gains +10.0 utility when it is right and loses
−24.8 when it is wrong (stored rows), so an accept rule pays only above a 2.17 : 1 ratio of right to wrong accepts per program, and
must also repay the peer's tokens (~1.7k on every passing N). The peer runs at 77.8 / 29.9 = 2.6 : 1 — just past the break-even, so
the cascade gains little whichever N it checks. With the trained N a perfect check would gain +3.23 [+2.19, +4.43] (base +2.33): the
training moved the ceiling by +0.9 and the realised gain by +0.6 (n.s.).

**Decision (as pre-registered).** P1 holds, P3 refuted → better quick programs do not move the cascade, and the limit is the check,
not the quick program: one peer confirms a third of the wrong passing programs (the shared formulation errors), and that ratio does not
change with training. The recipe on word problems stays training-free; the check is what is now tested (VER, a trained verifier, whose
break-even is the same 2.17 : 1 but at one generated token instead of the peer's ~1.7k). RF-P3 (RFT on the same 4,000 problems against
this run) is decided when its evaluation lands; RFT on 2,000 problems already sits at +0.87 [−0.08, +1.86], level with WP-RL.
