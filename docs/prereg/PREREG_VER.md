# Pre-registration VER: a learned check — a verifier trained with labels as the gate of the word-problem cascade

Written 2026-10-31 05:3x UTC, before any verifier row: the training set is built (`poc/ver_build.py v1`), the analysis is written and
tested on the stored labels used as a perfect verifier and on synthetic verifiers of known accuracy; no verifier has been trained or
has scored a program. Results go below.

**Why it could change the claim.** On word problems the leaky model's free check is the bottleneck, now measured three ways. (1) The
cheap path: with a perfect check on Qwen3-8B's quick program (accept it exactly when it is right) the peer cascade would beat the
default by +2.3 to +2.6 utility; the real peer check gains +0.0 (PREREG_TD.md note, HO-PA). (2) Inside the think: stopping at the first
right forced program would gain +5.8; every label-free stop signal recovers +0.4 to +1.2, n.s. (CONT, CONT-A), because passing
forced programs are right only 60–65% of the time. (3) The default itself accepts the cut think's passing program, which is wrong 35%
of the time (314 of 904 passing problem-seeds). Every label-free check tried — the free check, agreement with another model, agreement
within a think, a 2k-token self-review (HO-VR) — leaves most of this. Labels may be used in training (the recipe's SQL and tool-call
steps, CV-1 / TC-RL), so the check itself can be trained: if a verifier trained on OptMATH-Train programs discriminates well on
unseen benchmarks, the cascade can reject the leaks it now accepts, and cheap first can pay on word problems for the first time.

**Theory (stored rows of the four held-out sets, Qwen3-8B, 476 problems × 3 seeds; λ = 0.5).**
- *Gating the cut think's program (VD).* Of 904 passing cut programs, 590 are right, 314 wrong. Rejecting one (running T→T instead)
  gains +15.1 utility points on average when it is wrong (T→T is often right) and loses −10.8 when it is right (T→T's tokens and
  its own errors). A gate pays when (share of wrong programs it rejects) / (share of right ones it rejects) > 590·10.8 / (314·15.1)
  = 1.34: a low bar.
- *Gating the cheap program (VN, cheap first).* Of 801 passing quick programs, 427 are right, 374 wrong. Accepting one instead of
  running the default gains +10.0 when it is right and loses −24.8 when it is wrong, and the quick program costs ~0.4 utility on every
  problem. A gate pays when (share of right ones accepted) / (share of wrong ones accepted) > 374·24.8 / (427·10.0) = 2.17 and the
  surplus beats the quick program's cost: a high bar.
- *Ceilings (the stored labels as the verifier):* VN − D +2.61 [+1.69, +3.62], VD − D +4.37 [+2.86, +5.90], VND − D +5.59 [+3.90,
  +7.37] (60.6% at 13.8k tokens vs 53.2% at 10.0k).
- *Power (synthetic binormal verifiers through the same analysis):* AUC 0.77 on the test programs → VD − D ≈ +1.0, VN − D ≈ 0 (both
  n.s.); AUC 0.92 → VD − D ≈ +2.2, VND − D ≈ +2.9 (significant). P1 needs a test AUC of roughly 0.85 or more.

**Prior work (IDs opened 2026-10-31).** Trained verifiers that rank sampled solutions (Cobbe et al., 2110.14168); LEVER (2302.08468,
ICML 2023): a verifier over the question, the program and its execution result reranks sampled programs (SQL, table QA, math);
generative verifiers, verification as next-token prediction (2408.15240, ICLR 2025); answer verifiers as reward models
(CompassVerifier, EMNLP 2025); FrugalGPT (2305.05176): an LLM cascade that accepts a cheaper model's answer when a learned scorer
rates it high. Optimization modeling trains the generator from solver outcomes (2604.00442), not a verifier. In the project: an
in-model gate trained with RL on the cascade's own reward learns to defer everything and tells right from wrong at only 1.1–1.3 : 1
(CV-1, SQL); the label-free gates above. **New here:** a learned check used as the gate at every step of a token-priced think cascade
(the cheap program, the cut think's, the full think's), judged by utility against the default and the peer on four benchmarks it was
not trained on, with the break-even conditions and ceilings stated in advance; and whether supervised labels give the discrimination
that RL on the cascade's reward (CV-1) did not.

**Run.** Verifier = Qwen3-8B + LoRA (DT's recipe: r 16, lr 1e-4, effective batch 16; 1 epoch; `poc/sft_lora.py`, data-parallel over 4 ×
RTX 3090; `poc/slurm/ver_lane.sh v1`), thinking off. Training set `sft_ver_v1` (`poc/ver_build.py v1`): every program of Qwen3-8B on
OptMATH-Train (WP-RL's 4,000 problems, 13-gram decontaminated against the test sets) that passes the free check — its 8 quick programs
per problem (td_gen tags q8b / q8bq2) and its cut-think and full-think programs (q8b) — at most 4 per problem, 10,821 examples from
3,292 problems, 64.8% labelled yes. Prompt: the problem text, the program, the value it printed, and "Is <value> the correct optimal
objective value of the problem exactly as stated? … Answer with one word: yes or no." Train-dev: the 354 problems with crc32(id) % 10
== 0, never trained on (1,775 programs). Untrained baseline: base Qwen3-8B, same prompt. Score V = P(yes) / (P(yes) + P(no)) of the
first token. Scored: every passing program of the stored arms N (formx), SB (formxtb2000), T (formxt), seeds 1–3, OptiBench's third /
BWOR / LogiOR / OptMATH (`poc/ver_score.py`; rows results/x3/ver_<tag>_*). Tokens: the verifier generates one token per program
(counted); its prompt (~1.2k input tokens) is reported, not priced, as the project prices output tokens throughout.

**Policies** (`poc/analyze_ver.py`, offline on the stored rows; per problem and seed, s2 = s % 3 + 1): **D** = SB→T→T; **PEER** =
N → Qwen3.5-9B's quick program prints the same value → N, else D; **VN(t)** = N passes and V(N) ≥ t → N, else D; **VD(t)** = D with
every passing think program gated (SB passes and V ≥ t → SB; else think s passes and V ≥ t → it; else think s2's end if it passes;
if nothing was accepted, the passing program with the highest V, else wrong); **VND(t)** = VN, then VD (N joins the fallback).
**t_dev**: the threshold (0.05 … 0.95) that maximises VN's utility on the train-dev problems (labels in training only), one threshold
for every gate; reported: t = 0.5 and per-policy cross-fitted thresholds (test halves by crc32(id) % 2).

## Predictions (paired 95% intervals over problems, seed means; utility = accuracy − 0.5 × ktokens)

- **VER-P1 (the learned check catches the default's leaks):** VD(t_dev) − D: lower bound > 0.
- **VER-P2 (cheap first pays on word problems):** VN(t_dev) − D: lower bound > 0.
- **VER-P3:** VND(t_dev) − D: lower bound > 0.
- **VER-P4 (training gives discrimination):** AUC of V over the passing programs of N, SB and T (test sets pooled), trained −
  untrained: lower bound > 0 (bootstrap over problems).
- **VER-P5 (the training is the cause):** VND(t_dev) with the trained verifier − with the untrained one (its own t_dev): lower bound > 0.
- Reported: AUC per arm and on train-dev; calibration (mean V vs the share right, per arm); the accept rate and right | accepted;
  per benchmark; t = 0.5; the cross-fitted thresholds; PEER; the verifier's input tokens; raw programs the verifier accepts wrongly.

## Decision

- P1 or P3 holds → the recipe's word-problem default gains a trained check on every program it would accept (PROJECT / REPORT /
  PROPOSAL: "the check can be learned"; labels in training only, as the SQL / tool-call training step), and the same verifier is
  pre-registered on SQL (BIRD train, where the free check leaks 41–43%) and as the stop signal inside the think (CONT's exits).
- P2 holds → cheap first with a learned check pays on word problems: the claim "on word problems the cheap path saves nothing"
  changes.
- P4 holds, P1–P3 refuted → the verifier discriminates but not enough to pay at these break-evens: report the AUC the gates need
  (theory above) and stop the verifier line on word problems. P4 refuted → supervised training on this data does not teach the check;
  reported with CV-1 (the same conclusion from RL).
- P5 refuted while P1 / P3 hold → the gain is the prompt's, not the training's (reported; the untrained verifier is the recipe's).

Expected (not a rule): train-dev AUC 0.80–0.88, test AUC 0.70–0.80 (the test problems are harder and from other sources: right |
passes 53% vs 69% on train-dev); P1 inconclusive (+0.5 to +1.5), P2 refuted (about 0), P3 inconclusive, P4 holds (+0.05 to +0.15),
P5 inconclusive.
