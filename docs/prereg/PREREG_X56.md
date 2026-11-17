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
