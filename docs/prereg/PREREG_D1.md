# Pre-registration D1: does F5 (distillation with self-replay) carry over to real contest geometry?

Written 2026-10-15 00:30 UTC, before building the data, training or evaluating. Results are appended below without editing this section.

**Why.** F5 (LoRA on verified programs; replaying the student's own programs protects other tasks) was shown only on our synthetic
tasks. Distilling a stronger model's verified programs into a fast no-think student is also a candidate cheap fix for the
generation-bound contest set (N2–N6 showed checks are not the bottleneck). Prior art: distillation for competitive programming
(OpenCodeReasoning, rStar-Coder; they distil reasoning traces at scale); forgetting and self-replay (references of F5).
**Design.** The 311 validated problems are split by zlib.crc32(name) % 3: test = remainder 0, train = the rest. Training examples:
up to 3 distinct correct programs per train problem from the teacher runs (gpt-oss-120b low / medium, gpt-oss-20b low / medium,
Qwen3-32B thinking, Qwen3.8), each paired with the exact run_cc prompt; assistant = the program only (no reasoning). Student: Qwen3-8B,
no thinking, LoRA r = 16, 2 epochs (poc/sft_lora.py, E4_DATA). Arms: base; A = teacher programs; B = A + the 300 E4 self-replay
programs (Qwen3-8B's own verified synthetic-task programs). Evaluation: test split, 3 seeds, no-think; collateral = the E4 battery
(hull clean / 8 helpers seeds 1–2, diameter, delaunay with the fixed helper).
**Predictions.**
- D1-P1: base Qwen3-8B no-think solves 7–13% of the test split; A adds ≤ 3 points (a few hundred programs without reasoning do not
  teach unseen hard problems); B within 1 point of A on the contest test split.
- D1-P2: A lowers clean-prompt hull (synthetic) by ≥ 10 points (the E4 damage pattern); B stays within 5 points of base.
- D1-P3: any contest gain of A falls on problems rated ≤ 1600.

## Results (2026-10-15 01:29 UTC; test split 105 problems × 3 seeds; train split 206 shown for reference)
| arm | test | train | output tokens | E4 battery: hull clean (of 120) / hull 8 helpers / diameter / delaunay-fixed (of 60) |
|---|---|---|---|---|
| base Qwen3-8B no-think | 12.1% | 10.5% | 999 | 109 (E4 base) / – / – / – |
| A: 431 teacher programs | **4.8%** | 8.1% | 476 | 77 / 10 / 59 / 41 |
| B: A + 300 self-replay programs | **3.5%** | 11.3% | 516 | 118 / 27 / 60 / 59 |
- **D1-P1:** base 12.1% (holds); "A adds ≤ 3" holds only because A *loses* 7.3 points; "B within 1 of A" narrowly refuted (−1.3).
  **D1-P2 holds:** A damages the synthetic hull task (109 → 77 of 120), self-replay protects it (118) and the other synthetic tasks.
  **D1-P3:** no gain anywhere.
- Mechanism (read): the trained students answer with the program alone and half the tokens (999 → 476): the base no-think model
  explains its approach before coding, the teacher data (programs from reasoning models whose reasoning is hidden) teach it to skip
  that, and accuracy falls even on the training problems. Self-replay protects the old synthetic skills but not the contest skill.

## D1b pre-registration (2026-10-15 01:29 UTC, before building data or training): explanation + code vs code only, same teacher answers
Teacher answers: the 201 correct gpt-oss-20b low answers on train problems whose stored text is complete (explanation + code; up to 3
per problem). Arms: A' = the same answers, code only; C = full answer text (explanation + code); D = Qwen3-8B's own 63 correct no-think
answers on train problems, full text (rejection-sampling fine-tuning, STaR-style). Same LoRA settings; test split, 3 seeds.
- D1b-P1: C ≥ A' + 4 points on the test split (keeping the explanation is what matters), and C ≥ base − 1.
- D1b-P2: D within ± 2 points of base (too few examples to matter), with output length unchanged (± 15%).

**Correction to the mechanism above (2026-10-15 01:30 UTC, measured before any D1b run).** Neither the base model's nor the teachers' answers contain
explanation text outside the code block (median 0 characters). What changes is the code: on the test split the base writes programs of
median 72 lines with 12 comment lines; students A / B write 50 / 52 lines with 5 comments; the teacher programs have 49 lines and 3
comments. The students adopt the teachers' terse style and lose the step-by-step comments that the no-think base writes while coding,
i.e. its in-code reasoning. **D1b as pre-registered above is withdrawn before running**: arm C would equal A' (the teacher answers are
code only).

## D1b′ pre-registration (2026-10-15 01:30 UTC, before any data or training): restore the comments
- E (SDFT-style): each of A's 431 teacher programs is rewritten by base Qwen3-8B (no-think) with the instruction to add explanatory comments
  before every step without changing the logic; a rewrite is kept only if it still passes all of the problem's tests (else the original
  is kept). Train as A.
- D (self, rejection-sampling fine-tuning / STaR-style): Qwen3-8B's own 63 correct no-think answers on train problems.
- D1b′-P1: E ≥ A + 4 points on the test split and E's programs have ≥ 8 comment lines (median); E ≥ base − 2.
- D1b′-P2: D within ± 2 points of base and keeps its comment density (median ≥ 10 comment lines).

## Data-hygiene finding and D1 results on the clean test split (2026-10-15 02:29 UTC)
37 statements are shared by two validated problems (Div. 1 / Div. 2 copies, e.g. 613_A / 614_C, 650_A / 651_C); 17 of the 105 test
problems have a statement identical to a train problem. Clean test split = 88 problems (all D1 numbers below; contest-level results
elsewhere count each copy, which weighs 37 problems twice but does not affect paired comparisons).
| arm (Qwen3-8B no-think) | clean test (88 × 3 seeds) | comment lines (median) | output tokens |
|---|---|---|---|
| base | 12.9% | 12 | 933 |
| A: 431 teacher programs | 5.3% | 5 | 567 |
| B: A + self-replay | 4.2% | 5 | 582 |
| D: its own 63 correct answers (STaR-style) | **15.2%** | 10 | 1,068 |
- **D1b′-P2 half:** D keeps the comment density (10) and is +2.3 points over base (predicted within ± 2): training on its own verified
  programs is the only arm that does not hurt, the F5 contrast (own vs teacher programs) reproduced on real problems. Arm E (teacher
  programs with the base's comments) failed on a lookup bug (statements shared by two problems; fixed) and is re-running.

## Arm E result (2026-10-15 03:29 UTC; clean test, 3 seeds, paired with base)
E (the 431 teacher programs, 294 of them rewritten by the base with explanatory comments and re-verified; training programs median 14
comment lines): 6.8% vs base 12.9% (lost 24 / gained 8, p = 0.007); A 5.3% (24 / 4, p < 0.001); D 15.2% (9 / 15, p = 0.31). E's programs
have the base's comment density (median 10 lines, 895 tokens) yet stay far below base. **D1b′-P1 refuted** (+1.5 over A, not +4): the
comments are not the cause. What remains: training on correct solutions to problems the student could not solve teaches it to write
confident solutions it cannot get right; the known "learnability gap" of distilling strong teachers into small students (Small Models
Struggle to Learn from Strong Reasoners, Li et al. 2025). Own data (D) is the only arm without harm.

## D2 pre-registration (2026-10-15 03:29 UTC, before generating data): self-training at a larger scale, and teacher data limited to learnable problems
Qwen3-8B no-think seeds 4–8 on all problems (with seeds 1–3: 8 samples). D2-S: up to 3 distinct own correct answers per train problem
(rejection-sampling fine-tuning / STaR, prior art). D2-L: the teacher programs (A's pool) only for train problems the student solves in
≥ 1 of its 8 samples ("learnable"). Same LoRA settings; clean test split (88), 3 seeds; paired sign tests vs base.
- D2-P1: S ≥ base + 3 points on the clean test split.
- D2-P2: L ≥ A + 5 points and L ≤ S + 1 (teacher programs help only where the student is already close).
(Prior-art note, 2026-10-15 03:29 UTC: Li et al., "Small Models Struggle to Learn from Strong Reasoners", Findings of ACL 2025 (2502.12143), report the
learnability gap for students ≤ 3B on math with long chains of thought and propose Mix Distillation (long + short chains, or large +
small teachers). Our student is 8B, the data are programs without reasoning, the domain is contest geometry: the gap appears there too.
D2-L (teacher data only where the student is close) and D2-S (own data) are the two halves of a mix; a mixed arm follows if either helps.)

## D2 results (2026-10-15 04:29 UTC; clean test 88 × 3 seeds, paired with base seeds 1–3; base over 8 seeds = 14.6%)
| arm | data | clean test | lost / gained vs base (p) | comment lines | tokens |
|---|---|---|---|---|---|
| S: own correct answers, ≤ 3 per train problem (8 samples) | 112 | 15.2% | 9 / 15 (0.31) | 13 | 977 |
| L: teacher programs only for the 50 train problems the student solves | 149 | **5.3%** | 24 / 4 (< 0.001) | 2 | 715 |
- **D2-P1 refuted:** S is +2.3 over base seeds 1–3 but +0.6 over the 8-seed base mean: self-training on 112 examples is neutral.
  **D2-P2 refuted:** limiting teacher programs to problems the student can solve does not help (5.3% = A).
- Read (1064_A, rated 800, which the base solves): the L-student writes the teachers' idiom (`sys.stdin.read()`, `solve()`, no
  comments) and a wrong loop (increments one stick until the triangle inequality holds), where the base reasons in comments and applies
  the inequality to the sorted sticks. The harm is the teacher's code distribution itself, not problem difficulty (L), not missing
  comments (E): the F5 idiom-drift finding, now on real problems and for an 8B student. Own data neither hurts nor helps at this size.

## D3 pre-registration (2026-10-15 04:29 UTC, before running): hinted self-solutions (STaR rationalization / SDFT on real problems)
For every train problem with a teacher program (159), the base student sees the statement and the teacher's correct program as a hint
and is asked to write its own solution in its usual style with comments; 2 samples; a solution is kept if it passes all tests (≤ 2 per
problem). D3 = these + S. Prior art: STaR rationalization (Zelikman et al. 2022), SDFT (Yang et al. 2024; our B2). Train as before.
- D3-P1: the hinted solutions cover ≥ 100 train problems and keep the student's style (median ≥ 10 comment lines); similarity to the
  teacher program (difflib ratio) median ≤ 0.6.
- D3-P2: D3 ≥ the 8-seed base mean (14.6%) + 3 points on the clean test split; if not, own-style data cannot transfer the teachers'
  solutions at this scale.

## D3 results (2026-10-15 05:28 UTC)
Hinted self-solutions: 219 verified on 128 train problems (median 8 comment lines, median difflib similarity to the hint 0.37); with S:
331 examples. Clean test 11.0% (11.4 / 10.2 / 11.4 per seed; lost 20 / gained 15 vs base, p = 0.50), 938 tokens, 10 comment lines.
**D3-P1 mostly holds** (coverage 128 ≥ 100, similarity 0.37 ≤ 0.6; comments 8 < 10). **D3-P2 refuted** (11.0% vs ≥ 17.6%).
**Distillation line closed (D1–D3):** on held-out contest geometry, LoRA on a few hundred verified programs never helps the 8B no-think
student: teacher programs hurt (5.3–6.8%), its own or its own-style programs are neutral (11.0–15.2% vs base 12.9–14.6%). F5's
protective self-replay holds on the synthetic tasks; the cheap-gain part of F5 does not transfer to hard problems.
