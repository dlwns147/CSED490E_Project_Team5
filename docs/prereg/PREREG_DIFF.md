# PREREG_DIFF — choose among disagreeing programs by asking for single terms where they differ (registered 2026-11-23 08:3x UTC, before any oracle call)

**Why.** OEIS's headroom is selection: on 468 of 500 sequences the stored programs (Qwen3-8B, gpt-oss-20b, gpt-oss-120b; prog and think;
3 seeds) print two or more different 20-term answers; some sample is right on 44% of sequences, the plurality answer on 30% (149 / 500).
Agreement, own brute force and reviewer likelihood do not separate right from wrong (PREREG_VOI amendments 4–5). Computing ONE term
a(N) of a definition is easier than writing a program that is right for all N.

**Method (DIFF).** Per sequence with ≥ 2 answer classes: take the smallest index where the remaining classes disagree, ask an oracle
model for that single term a(N) from the definition (gpt-oss-120b, medium reasoning, answer in \boxed{}), keep the classes whose term
matches; repeat up to 3 rounds while ≥ 2 classes remain; return the most frequent surviving class (if none survives, the plurality class).
Oracle tokens are paid. Prior work: ExPairT-LLM (arXiv 2511.10855; pairwise equivalence queries on distinguishing inputs), CodeT, ALGO
(brute-force oracle). New here: the oracle is a single-term computation from the natural-language definition, applied to a pool of
programs from three families, on contemporary OEIS sequences.

**Test** (poc/oeis_diff.py): DIFF − {plurality vote over all samples, best single source (gpt-oss-120b program), VOI v2}, accuracy and
utility at 0.5 per ktok (all samples' tokens + oracle tokens for DIFF and the vote; one sample for the single source), clustered
bootstrap over sequences, one-sided, Holm over three. Prediction: DIFF raises accuracy above the plurality (≤ +14 points of headroom);
whether it wins in utility depends on the cost of buying every sample, so a second line reports DIFF on top of the cheap programs only
(3 families × prog × 3 seeds).
