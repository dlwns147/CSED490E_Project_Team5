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

## Related work found after registration (searched 2026-11-23 08:4x UTC by mechanism) and the plan for every set
Choosing among disagreeing programs by inputs that separate them is established for code generation: S* (arXiv 2502.14382; the LLM
picks between outputs on distinguishing inputs), LLMCodeChoice (ISSTA 2024), ExPairT-LLM (2511.10855), Agentic Verifier (2602.04254),
Semantic Voting (2605.08680). DIFF on OEIS is that mechanism carried to math sequences — a known mechanism (loop mark K); what differs
is the oracle (one term from the natural-language definition, not a choice between outputs). Per set:
- **OEIS:** DIFF as registered (running: gpt-oss-120b and Qwen3-8B oracles on gs15).
- **MathConstruct (addendum MC, below):** constructions cannot be compared for equality, so the separating question is each OTHER
  sample's verify(): every program's construct() is checked by the verify() functions written by the other samples (3 families × 3 seeds).
- **Project Euler (addendum PE, next):** candidate programs with a one-argument solve(n) are run for small n; the smallest n where
  they disagree is asked to the oracle (the problem at that size).
- **Word problems / MATH+AIME:** not covered — the stored word-problem answers carry no solution vector to query (only objective values),
  and MATH+AIME is saturated (98.9% some sample right; the plurality is already right on almost all of those).
## Addendum MC (registered 2026-11-23 08:4x UTC, before any cross-verification run)
Candidates: the 9 progc constructions per problem (Qwen3-8B, gpt-oss-20b, gpt-oss-120b × seeds 1–3). Each candidate is checked by the
verify() of every other progc sample (poc/mcon_xverify.py, sandbox, CPU job). Selection: a Dawid–Skene model of the verifiers (each
verifier family has its own P(pass | right), P(pass | wrong), fitted by EM without labels; conditional independence across families)
gives each candidate a posterior of being right; return the candidate with the highest posterior. No extra model calls (zero extra
output tokens; CPU only). Test: accuracy vs (a) the best single family's progc sample, (b) own-verify acceptance then think (the
descriptive ladder, gpt-oss-120b), (c) majority-of-passing-verifiers; one-sided paired bootstrap over problems, Holm over three.

## Addendum MC result (2026-11-23 09:1x UTC; python3 poc/mcon_xverify.py score; 121 problems, 9 progc samples each, 4,229 cross-checks)
Label-free verifier fit: P(pass | right) 0.80 / 0.88 / 0.87, P(pass | wrong) 0.18 / 0.04 / 0.03 (Qwen3-8B / gpt-oss-20b / gpt-oss-120b
verifiers). DS cross-verify 46.3% vs best single progc (gpt-oss-120b) 32.5%: **+13.8 [+7.7, +19.8]**, p 0.0002; vs most passing
verifiers 43.8%: +2.5 [+0.0, +5.8], p 0.046; vs the own-verify ladder (gpt-oss-120b progc, else think-then-program) 50.7%: **loses**
(−4.4 points accuracy, and 8.1k tokens for all 9 programs against the ladder's ~2.6k). Holm over three: holds vs the single source
only. Some progc sample is right on 57.0%.
## Addendum MC2 (registered 2026-11-23 09:1x UTC, before running)
The ladder wins because think-then-program constructions are better (gpt-oss-120b 46.8% alone) and DS could not see them (no
construct()). MC2 parses every think-then-program boxed answer with the problem's own parser into an object, adds it as a candidate,
and checks it with all 9 progc verify() functions; same DS fit. Test: DS over all 18 candidates − own-verify ladder (accuracy and
utility at 0.5 with every sample's tokens), one-sided paired bootstrap.
