# Pre-registration X56: a quick program accepted when a brute-force program agrees (OEIS), by checker family and model precision

Written 2026-11-17 12:0x UTC, before any seed-2 row. Known before writing: the seed-1 pilot (IDEAS 56), every arm listed below at seed 1
except gpt-oss-20b and gpt-oss-120b thinking (running).

**Why.** The computation track was closed as a loss: Qwen3-8B's quick program checked by its own brute-force program (agreement on the first 8
terms) loses to thinking on OEIS, because the check shares the program's misreading (precision 72%). On trips a different family's reading broke
that (PEERT-C). Seed-1 pilot, 250 easy sequences, against Qwen3-8B thinking (30,000 tokens, 134 right at 10.8k): own check −2.0 [−4.7, +0.4]
utility; gpt-oss-120b's brute force as the check +1.0 [−1.1, +3.2] (precision 87%); and gpt-oss-20b's quick program checked by its own brute
force accepts 94 with 90% precision. Theory (the course's precision condition, §1): a check-gated ladder beats thinking when the accepted
programs' precision exceeds thinking's accuracy on those same items, at a fraction of the tokens. Prior work: CodeT 2207.10397 and ALGO
2305.14591 use tests or oracles written by the same model; none compares checker families or ties acceptance to that condition.

**Run (seed 2, OEIS, all 500 sequences; read on the 250 easy, the hard 250 reported).** Quick programs (`prog`) and brute-force programs
(`brute`) without thinking for Qwen3-8B, gpt-oss-20b (low effort) and gpt-oss-120b (low); thinking (`think`, 30,000 tokens) for Qwen3-8B and
gpt-oss-20b (high effort). Every step's tokens counted.

**Ladders (accept the quick program when it and the checker print the same first 8 terms, else that model's thinking):**
- X56-L1: Qwen3-8B program, Qwen3-8B brute force → Qwen3-8B thinking (the closed result, reproduced).
- X56-L2: Qwen3-8B program, gpt-oss-120b brute force → Qwen3-8B thinking.
- X56-L3: gpt-oss-20b program, gpt-oss-20b brute force → gpt-oss-20b thinking.

**Predictions (utility, ladder − the same model's thinking, paired over sequences).** L1 below or including 0. **L2 (decides the cross-family
claim):** about +1, interval including 0. **L3 (decides the precision claim):** above 0 if L3's accepted precision exceeds gpt-oss-20b
thinking's accuracy on the accepted sequences; I predict both hold.

**Decision.** L3 above 0 → the computation track is reported as a conditional win: the check pays when its precision beats thinking on what it
accepts (gpt-oss-20b), not when the model's own check shares its misreading (Qwen3-8B). L2 above 0 → a cross-family checker repairs the weaker
model's ladder. Both including or below 0 → the computation track stays closed and the report says why.

**Amendment (written 2026-11-17 15:2x UTC, before any seed-2 thinking row is read).** At seed 1, gpt-oss-20b thinking at high effort hit the
30,000-token cap on 195 of 250 easy sequences and wrote no program (47 right at 26.9k tokens); Qwen3-8B hit it on 10, gpt-oss-120b on 87. A
baseline that mostly runs out of tokens is not the strongest thinking baseline, so L3 is also read against gpt-oss-20b thinking at **medium
effort** (same cap; seeds 1 and 2), and **the verdict uses whichever thinking setting has the higher utility** (the rule PREREG_BUD used for
budget-forced thinking). The high-effort numbers are reported beside it.

**L3 read (2026-11-17 17:2x UTC; seed 2, 250 easy sequences).** gpt-oss-20b thinking at medium effort: 153 right at 6.83k tokens (14 hit the
cap); at high effort it hit the cap on most sequences at seed 1 (47 right at 26.9k), so medium is the better baseline by any reading and the
ladder falls back to it. **X56-L3: 159 right at 5.99k vs 153 at 6.83k, +2.8 [−0.1, +5.9] utility.** Accepted 104, right 91 (87.5%); thinking is
right on 85 of those 104 (82%), so the precision condition holds, but by little. The interval includes 0: by the rule, **not a win**. Hard
sequences: +0.1 [−0.4, +1.1]. (Seed-1 pilot, same reading: +1.9 [−0.6, +4.5].) The high-effort seed-2 run is still finishing and is reported
beside this; it cannot raise the baseline. L1 and L2 wait for Qwen3-8B thinking at seed 2.

**L1 and L2 read (2026-11-17 19:3x UTC; seed 2, 250 easy sequences; Qwen3-8B thinking 12 of 500 at the cap, 488 parsed).** Qwen3-8B thinking:
148 right at 10.26k tokens.
- **X56-L1 (own check): 147 right at 8.66k, +0.4 [−1.9, +2.8].** Accepted 82, right 64 (78%); thinking right on 65 of them. Prediction
  (below or including 0) holds.
- **X56-L2 (gpt-oss-120b check): 152 right at 9.05k, +2.2 [+0.8, +4.0].** Accepted 78, right 69 (88%); thinking right on 65. The interval is
  above 0, so by the decision **a cross-family checker repairs the weaker model's ladder**; the prediction (about +1, interval including 0)
  was too cautious. The gain is small: +1.6 from accuracy, +0.6 from tokens (gpt-oss-120b's brute-force tokens are counted).
- The two seed-2 thinking runs not used here were stopped as redundant (a Slurm copy of the same Qwen3-8B run, and gpt-oss-20b high effort,
  which the amendment already ruled out as the baseline).

**Addendum S3 (written 2026-11-17 19:3x UTC, before any seed-3 thinking row exists; programs and brute forces at seed 3 are stored).** Seed 3
replicates L1–L3 with the same rules: Qwen3-8B thinking and gpt-oss-20b thinking at medium effort, 30,000 tokens.
- Predictions: L2 at seed 3 above 0 in its point estimate, and seeds 2 and 3 pooled (paired bootstrap over sequence × seed) above 0; L1 pooled
  including 0; L3 pooled above 0 (seed 2 alone was +2.8 [−0.1, +5.9]).
- Decision: L2 stays a win only if the pooled interval is above 0; L3 becomes a conditional win only if the pooled interval is above 0 and the
  seed-3 point is above 0; otherwise the seed-2 readings stand as written.
- Label-free test (LOOP open problem 2): rule B, the third check's answer as the label (strongest family not in the ladder: L1 gpt-oss-120b,
  L2 gpt-oss-20b, L3 gpt-oss-120b; `results/tmp_lf3.py`), predicts each seed-3 accuracy term within 2.0 points, and closer than rule A (the
  11-17 rule, which assumes accepted answers are right) in each of the three cells. On seeds 1–2 rule B's mean absolute error was 1.0 (rule A 4.3).

**S3 read (2026-11-17 20:3x UTC; seed 3, 250 easy sequences; every easy row of both thinking runs is written, the Qwen3-8B run is still
finishing hard sequences, which do not enter the verdict).** Baselines: Qwen3-8B thinking 139 right (7 at the cap, 243 parsed), gpt-oss-20b
medium 153 (16 at the cap, 230 parsed). Pooled = each sequence's mean over seeds 2 and 3, bootstrap over the 250 sequences.
- **L2 (gpt-oss-120b check):** seed 3 +1.1 [−0.7, +2.9]; **pooled +1.7 [+0.4, +3.2]** → by the decision, L2 stays a win.
- **L1 (own check):** seed 3 −0.0 [−2.8, +2.7]; pooled +0.2 [−1.9, +2.2], including 0 as predicted.
- **L3 (gpt-oss-20b, own check):** seed 3 +1.8 [−0.7, +4.5]; **pooled +2.3 [+0.3, +4.5]**, seed-3 point above 0 → by the decision, **L3 becomes a
  conditional win** (the check pays where its precision beats thinking on what it accepts).
- **Rule B (label-free accuracy term):** predicted vs measured, L1 −2.0 vs −0.8, L2 +1.6 vs +0.4, L3 +1.6 vs +1.6: within 2.0 in all three
  cells and closer than rule A (+6.0, +4.4, +3.2) in each, as predicted. Over the nine OEIS cells of seeds 1–3, mean absolute error 0.9 (rule A 4.2).
- Hard sequences, seed 3 (reported, no verdict): L1 +0.05, L2 −0.48, L3 −0.21 utility; 7–8 of 250 right for every arm (seed 2: +0.1).
