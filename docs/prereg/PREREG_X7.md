# Pre-registration X7: the final recipe on a held-out benchmark (MAMO), with no hand-written fact

Written 2026-10-19 02:37 UTC, before any run. Results go below.

**Why.** Everything so far was developed on NL4OPT / IndustryOR and our generated suites. MAMO (Huang et al. 2024; EasyLP 652 + ComplexLP 211
optimization word problems, CardinalOperations/MAMO) has not been used. The recipe as it now stands, with no human-written component:
the fact = the model's own shortest program from NL4OPT / IndustryOR that passed the label-free check (runs and prints a value); write
the program with it (twice); think only unless both run and agree (FFR) — or only if it fails to run (FF). The hand-written snippet is
run alongside as the reference. Models: Qwen3-32B-AWQ (GPU0), Qwen3-14B-AWQ (GPU1), gpt-oss-20b (GPU2; low effort for the cheap
arms, medium for thinking), Qwen3-8B (GPU3, expected to lag); tag <model>_mamo (poc/queues/queue_s2_x7.sh).
Arms: mip s1 (no fact); mipf s1–2 + thinkf s1 (hand-written); mips s1–2 + thinks s1 (automatic).
- X7-P1: automatic FFR within 2 points of hand-written FFR for Qwen3-32B, Qwen3-14B-AWQ and gpt-oss-20b; ≥ 4 points below for Qwen3-8B.
- X7-P2: automatic FF ≥ always-thinks − 2 points at ≤ 40% of its tokens for those three models.
- X7-P3: picking the policy (CHEAP / FF / FFR / THINK) from 30 labelled MAMO items gives ≤ 1.5 points of regret (λ = 0.5) per model.

## Results, gpt-oss-20b (2026-10-19 03:36 UTC; results/x3/analysis_x7.log; MAMO 863 problems, seeds 1–2 for the cheap arms)
No fact 73.2%. Hand-written fact: CHEAP 76.1% @ 0.5k, FF 79.3% @ 0.6k, FFR 78.9% @ 1.7k, THINK 77.4% @ 2.5k. **Automatic fact: CHEAP 74.4%,
FF 77.3% @ 0.6k, FFR 78.8% @ 1.9k, THINK 76.0% @ 2.7k** (EasyLP / ComplexLP FFR 85.6 / 57.8%).
- **X7-P1 holds for gpt-oss-20b** (automatic FFR −0.1 points vs hand-written). **X7-P2 holds** (automatic FF 77.3% ≥ always-thinks 76.0% − 2,
  at 22% of its tokens). **X7-P3 holds** (pilot-of-30 regret 1.27 points; best policy FFR).
Addendum (before running): Qwen3.6 on MAMO, same arms, 80k thinking (T 1.0 / top_k 20), GPU2 — prediction: automatic FFR ≥ 3 points
below hand-written (as on X6).

## Results, Qwen3-14B-AWQ and Qwen3-8B (2026-10-19 05:36 UTC)
| model | no fact | hand: CHEAP / FF / FFR / THINK | automatic: CHEAP / FF / FFR / THINK | pilot-30 regret |
|---|---|---|---|---|
| Qwen3-14B-AWQ | 59.7% | 68.0 / 71.4 @ 0.9k / 71.4 @ 2.6k / 65.5 @ 6.5k | 68.4 / **70.7 @ 0.8k** / **71.7 @ 2.8k** / 68.8 @ 6.6k | 0.82 |
| Qwen3-8B | 45.5% | 57.5 / 70.2 @ 1.8k / 72.0 @ 4.5k / 69.2 @ 7.9k | **67.7** / 69.5 @ 1.0k / 71.0 @ 3.1k / 65.1 @ 7.7k | 1.35 |
- **X7-P1 holds for Qwen3-14B-AWQ** (+0.3); **refuted for Qwen3-8B in the good direction** (−1.0, not ≥ 4 below): on MAMO the 8B model's mined
  example is a *better* cheap fact than the snippet (67.7 vs 57.5%: 94% of its programs run vs 84%, pass-but-wrong 28% vs 30%).
- **X7-P2 holds** for both (automatic FF ≥ always-thinks − 2 at 12–13% of its tokens). **X7-P3 holds** (regret 0.82 / 1.35).
Replication (pre-registered now; our rule: positive claims need ≥ 3 seeds): cheap arms seed 3 and thinking seeds 2–3 for Qwen3-14B-AWQ
(GPU1) and gpt-oss-20b (GPU3) (queue_s2_x7rep.sh); prediction: the automatic-vs-hand FFR gap stays within ±2 points on each seed pair.
- **Replication, gpt-oss-20b, 3 seeds (2026-10-19 06:36 UTC):** automatic minus hand-written FFR = −0.1 / −0.8 / −1.2 points (78.8 / 78.6 / 78.4% vs 78.9 / 79.4 /
  79.6%), at the same tokens (1.8–1.9k); the ±2 prediction holds on every seed. Qwen3-14B-AWQ seeds running; Qwen3-32B / Qwen3.6 finishing.

## ORLM same-harness baseline, pre-registration (2026-10-19 07:36 UTC, before running)
ORLM-LLaMA-3-8B (fine-tuned for optimization modeling; its model-card template, coptpy, greedy decoding = seed 1, plus sampled seeds 2–3 at
T 0.7) on NL4OPT + IndustryOR (tag orlm) and MAMO (tag orlm_mamo); the objective is read from the solver (Model.solve wrapped), graded with
the same tolerance as every other arm (poc/run_orlm.py; poc/queues/queue_s2_orlm.sh, first free GPU).
- ORLM-P1: greedy MAMO Easy / Complex within ±4 points of the reported 82.3 / 37.4%.
- ORLM-P2: our training-free recipe (automatic fact, two agreeing programs, else think) with Qwen3-8B is within 3 points of ORLM on MAMO overall
  (same model size, no training); with gpt-oss-20b it is ≥ 5 points above.
- ORLM-P3 (cost): ORLM's single greedy program is cheaper per problem than our FFR (fewer output tokens), so per token ORLM wins; per accuracy
  at a 3090 budget gpt-oss-20b wins.

## ORLM results (2026-10-19 08:39 UTC; results/x3/opt_orlm*_orlm_s*.jsonl; 17 programs that began with a 'pip install' line re-run without it — no change)
ORLM-LLaMA-3-8B, greedy (seed 1) / sampled (2, 3): **MAMO Easy / Complex 80.5 / 35.5%** (77.8 / 22.3, 77.3 / 29.4); overall 69.5% (64.2, 65.6) at
1.1k output tokens; NL4OPT / IndustryOR 78.8 / 27.0% (75.5 / 29.0, 75.1 / 29.0).
- **ORLM-P1 holds** (greedy within ±4 of the reported 82.3 / 37.4%).
- **ORLM-P2 holds:** our training-free recipe (automatic fact, two agreeing programs, else think) on MAMO overall — Qwen3-8B 71.0% @ 3.1k (+1.5
  over ORLM greedy; plain fact-first 69.5% @ 1.0k = ORLM at the same tokens), Qwen3-14B-AWQ 71.7% @ 2.8k, gpt-oss-20b 78.8% @ 1.9k (+9.3),
  Qwen3-32B 76.9% @ 0.5k (fact-first; its best policy).
- **ORLM-P3 refuted:** ORLM is not cheaper than our plain fact-first at equal accuracy (Qwen3-8B 69.5% @ 1.0k vs ORLM 69.5% @ 1.1k).
**Reading:** a fine-tuned 8B specialist is matched, with no training, by a general 8B model given its own mined example and a cheap check.
**STORM-Qwen3-4B (pre-registered now):** the strongest public small specialist (SFT + RL, tool-integrated reasoning; reported MAMO 86.3 / 70.3% on
its cleaned 100-problem subsets with a 5% tolerance after rounding). Run with its official inference code (cloned; vLLM 0.22; 3 samples,
T 0.6) on our full MAMO and NL4OPT + IndustryOR, graded with our tolerance (and with theirs, for reference) (queue_s2_storm.sh, GPU0).
Prediction: STORM ≥ our best training-free 3090-class result on MAMO (gpt-oss-20b 78.8%) under our grader, at ≥ 3 × the tokens.
- **Replication, Qwen3-14B-AWQ, 3 seeds (2026-10-19 10:44 UTC):** automatic minus hand-written FFR = +0.3 / +1.6 / +0.2 points (71.7 / 73.5 / 72.4% vs
  71.4 / 71.8 / 72.2%) at the same tokens (2.6–2.8k); the ±2 prediction holds on every seed. Plain automatic fact-first 70.7–71.8% @ 0.7–0.8k vs
  always thinking with the hand snippet 65.4–65.5% @ 6.5k. Qwen3-8B seeds 2–3 and Qwen3.6 still running.
- **Replication, Qwen3-8B, 3 seeds (2026-10-19 12:37 UTC):** automatic minus hand-written FFR = −0.9 / +1.6 / +2.2 points (71.0 / 72.2 / 73.1% vs 72.0 / 70.6 / 70.9%),
  and cheaper (3.1–3.2k vs 4.5–4.6k tokens: the hand snippet's `solver.Objective().Minimize()` crash appears 91 times in seeds 2–3 vs 39 with
  the mined program, and each crash buys a thinking run). The ±2 prediction holds on seeds 1–2; seed 3 misses it by 0.2 in the automatic
  fact's favour. Plain automatic fact-first 68.8–71.1% @ 0.9–1.0k vs always thinking with the hand snippet 67.3–69.2% @ 7.7–7.9k.
**Replication, Qwen3-32B-AWQ (pre-registered now, 2026-10-19 12:37 UTC; queue_s2_x7rep_q32b.sh, GPU3):** cheap arms seed 3, thinking seeds 2–3.
Predictions: (a) automatic minus hand FFR within ±2 points on each seed pair; (b) automatic FF ≥ hand FF on each seed (seed 1: 76.9 vs 74.0%).

## STORM results (2026-10-19 13:41 UTC; poc/analyze_storm.py; its official TIR inference, 3 samples, T 0.6, 32k per call)
STORM-Qwen3-4B on all 863 MAMO problems, graded with our tolerance: **81.8%** (Easy 85.7 / Complex 69.5%) at **8.4k tokens per sample**
(its own grader: 83.5%; pass@3 87.3%). **Prediction holds** (≥ 78.8% at ≥ 3× the tokens: +3.0 points at 4.4× gpt-oss-20b's FFR tokens).
Cascade, offline (our model's two cheap programs agree → accept, else STORM's sample of the same seed): gpt-oss-20b 79.5–80.4% @ 3.0–3.1k,
Qwen3-14B-AWQ 77.3–79.7% @ 2.9–3.2k, Qwen3-8B 74.9–76.1% @ 2.9–3.1k (3 seeds) — below STORM alone, because the cheap programs' agreeing-but-wrong
answers are kept: STORM's first sample is right on 28–49% of those leaked problems. Raw reading of 12 of gpt-oss-20b's leaked problems that STORM
gets right: 'the difference between A and B cannot exceed c' written as |A − B| ≤ c where the label means A − B ≤ c (3); a balance written as an
equality, so the surplus cannot stay and the model is infeasible (2); 'minimum returns' maximised (1); a per-unit cost applied to a quantity
limit, infeasible (1); answer left in thousands (1); the sign of a 'loss' bound (1); int() truncating 17.9999 to 17 (1); one wrong label that
STORM matches (mamo_complex-68: brute force gives 175 = ours, label 158); one problem whose bounds are missing from the text (easy-606).
MAMO has no infeasible labels, yet 21–29 leaked pairs per model agree on 'infeasible'; counting 'infeasible' as a failed check adds +0.1 to +1.6
points (Qwen3-8B +1.3 to +1.6) at +0.1–0.4k tokens on MAMO, −0.3 to +0.9 on NL4OPT + IndustryOR (which has 14 infeasible labels).

## STORM-RECIPE pre-registration (2026-10-19 13:41 UTC, before running): our recipe on top of the specialist (queue_s2_stormrecipe.sh, GPU1)
STORM always thinks with tools (8.4k tokens). Cheap arm = STORM writing one OR-Tools program WITHOUT thinking (no-think template), with the
hand snippet (mipf) or its own mined program (mips); escalation = its official TIR sample of the same seed. 3 seeds, MAMO + NL4OPT/IndustryOR.
- SR-P1: STORM's no-think program runs and prints a value on ≥ 80% of MAMO problems (its RL training may have broken the no-think mode).
- SR-P2 (main): STORM-FFR (two cheap programs agree → accept, else its TIR) within 2 points of STORM TIR alone (81.8%) at ≤ 50% of its
  tokens, on each seed.
- SR-P3: STORM's cheap programs leak less than gpt-oss-20b's (agreeing-but-wrong share of agreeing pairs ≤ 12% vs 15%).
**Qwen3.6 on MAMO (seed 1, 2026-10-19 13:41 UTC):** automatic FFR 75.0% @ 8.6k vs hand-written 73.6% @ 9.1k (+1.4); automatic FF 75.0% @ 3.2k vs always thinking
70.7–71.8% @ 27–29k. **Prediction refuted in the good direction** (expected automatic ≥ 3 below hand). On MAMO thinking hurts Qwen3.6 (−3.2 vs
fact-first at 9× the tokens); pilot-of-30 regret 1.25 (best policy FF). One seed only: not used for claims.

## What the leak is made of (2026-10-19 13:44 UTC, offline) and INFEAS pre-registration (before running)
On 66 MAMO problems (7.6%) at least 14 of our 20 programs (5 models × 2 seeds × 2 facts, ≥ 4 models) agree on an answer that differs from the
label; STORM, trained separately, gives our answer on 60 of them (167 of 198 samples) and the label's on 10. The 3 we read are wrong or
ill-posed labels (easy-71: the text gives 3000, label 1340; easy-157: the text as written gives 0; easy-2: two contradictory effectiveness
definitions). Split of the leaked problems (two cheap programs agree, wrong; seed 1): gpt-oss-20b 106 = 51 disputed labels + 29 'infeasible'
+ 26 other; Qwen3-14B-AWQ 127 = 60 + 24 + 43; Qwen3-8B 158 = 57 + 29 + 72; Qwen3-32B 103 = 55 + 21 + 27; Qwen3.6 128 = 59 + 5 + 64.
Without the 66 disputed problems STORM scores 87.7% and gpt-oss-20b's cheap automatic-fact program 80.1%. So for the strong models the
largest catchable class of real errors is the over-strict (infeasible) model, which our check accepts and thinking fixes only 17–45% of.
**INFEAS (poc/run_infeas.py; queue_s2_infeas.sh, GPU2):** every cheap program that printed 'No Best Solution' gets ONE repair turn without
thinking: its program and a generic message (the solver says infeasible; the problem has a solution; find the constraint written more
strictly than the text). gpt-oss-20b (low), Qwen3-14B-AWQ, Qwen3-8B; MAMO (automatic fact, mips) and NL4OPT + IndustryOR (hand fact, mipf);
seeds 1–3. Policy compared offline: FFR where 'infeasible' fails the check and goes to (a) thinking or (b) the repair, then thinking only if
the repaired program still fails.
- IF-P1: on MAMO the repair makes ≥ 40% of the infeasible programs correct, per model and seed (thinking: 17–45% of the agreeing ones).
- IF-P2: policy (b) ≥ policy (a) + 0.5 points on MAMO at fewer tokens, each model and seed.
- IF-P3: on NL4OPT + IndustryOR (14 true 'No Best Solution' labels) the gain of (b) over (a) is at most half of MAMO's.

## STORM-RECIPE stopped; INFEAS partial; FORM pre-registration (2026-10-19 13:54 UTC, before running)
**STORM-RECIPE stopped after 93 MAMO rows** (by PID; GPU1 released): STORM's no-think mode is broken — 55% of its programs hit the 8,192-token cap
(all 35 replies without code are cap hits: it keeps reasoning in text), the rest crash often; 20% correct. **SR-P1 refuted**; a recipe on top of
STORM would need its own cheap mode, which RL training removed.
**INFEAS, gpt-oss-20b and Qwen3-14B-AWQ (3 seeds; Qwen3-8B running):** the generic repair turn makes 8–14% (gpt-oss-20b) and 24–33% (Qwen3-14B-AWQ)
of the infeasible MAMO programs correct at 0.8–1.1k tokens; thinking makes 17–21% / 22–35% correct at 3.5–9.3k. Most repaired programs stay
infeasible (gpt-oss-20b: 29–41 of 43–53). Policy (b) vs (a): MAMO +0.0 to +0.2 (gpt-oss-20b), +0.5 to +0.7 (Qwen3-14B-AWQ) at slightly fewer
tokens; NL4OPT + IndustryOR −1.8 to +0.3 (the repair turns true 'No Best Solution' answers into numbers). IF-P1 refuted; IF-P2 holds for
Qwen3-14B-AWQ only; IF-P3 holds. Raw reading: the programs that stay infeasible repeat the same formulation — a TSP with Miller-Tucker-Zemlin
order constraints that include the start city (gpt-oss-20b: 29 of its 53 infeasible programs; 0% on the 34 MAMO TSPs vs 49–62% for the Qwen3
models), and a supply redistribution written as an equality so the surplus cannot stay (16 problems; 0–38% for every model).
**FORM (poc/run_form.py; queue_s2_form.sh, GPU1 then GPU2):** is a systematic formulation error missing knowledge that one fact fixes, when
repair and thinking do not? (a) formh: the mips prompt + one hand-written formulation sentence, only on the 34 TSP and 16 redistribution
problems (mechanism test); (b) formx, label-free: instead of the other benchmark's example, the program of the most similar OTHER MAMO
problem (BM25), from all five models' programs that pass the strict check (two seeds run, agree, not 'No Best Solution'), preferring the
answer most models share. (Checked with labels only for this note: the selected source programs are right on their own problems 81% of the
time; TSP 24 / 34, redistribution 13 / 16.) gpt-oss-20b (low), Qwen3-14B-AWQ, Qwen3-8B; seeds 1–3.
- FORM-P1 (mechanism): formh lifts gpt-oss-20b on the TSPs from 0% to ≥ 60%, and every model on the redistribution problems to ≥ 60%.
- FORM-P2 (label-free): formx lifts gpt-oss-20b on the TSPs to ≥ 50%, and the cheap program's MAMO accuracy by ≥ +2 points (gpt-oss-20b)
  and ≥ +1 (Qwen3 models) over mips, per seed, with no problem type losing more than 2 points.
- FORM-P3: on these two types the fact beats the repair turn and thinking (from existing rows) in accuracy at ≤ 30% of thinking's tokens.
