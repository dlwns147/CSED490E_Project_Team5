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
## Addendum PE (registered 2026-11-23 09:4x UTC, before any sweep): poc/pe_diff.py
Candidates: progc programs of three families × 3 seeds; those with a one-argument solve() are swept for n = 1..12 (sandbox, CPU job);
per problem whose final answers disagree, the smallest n where the swept classes differ is asked to the oracle (statement + argument
name + the asked call, "compute the answer for this small case"), up to 3 rounds; return the most frequent surviving final answer.
Oracle: gpt-oss-120b (medium). Test: accuracy and utility vs the plurality final answer, Project Euler dev and fresh 943–992 separately,
paired bootstrap. Stated limit: think-then-program answers (the strongest on fresh problems) have no solve() and are not candidates.

## OEIS result (2026-11-23 10:1x UTC; python3 poc/oeis_diff.py score; oracle gpt-oss-120b medium; 500 sequences)
| pool | DIFF | plurality | some sample right | tokens (pool + oracle) |
|---|---|---|---|---|
| cheap programs (3 families × prog × 3 seeds) | 36.2% | 32.2% | 39.2% | 4.9k + 3.2k |
| all samples (programs and thinks) | 40.4% | 36.8% | 45.0% | 173.6k + 4.0k |
**Registered test (cheap pool, utility at 0.5):** DIFF − best single source (gpt-oss-120b program, U 29.0) **+3.16 [+0.75, +5.68]**,
p 0.005; − VOI v2 **+4.15 [+1.97, +6.37]**, p 0.0005; − plurality **+2.41 [+0.26, +4.65]**, p 0.016 — all hold under Holm. The first
method that beats the best single source on OEIS. On the all-sample pool DIFF adds +3.6 points of accuracy but the pool's cost dominates
(+1.60 [−0.24, +3.45]). Oracle failures: no boxed integer on 28 of 1,011 queries; no class matched on 158.
Qwen3-8B as the oracle (lane running, partial: 168 sequences): cheap pool −0.80 [−5.70, +4.33], its oracle costs 4× more tokens.
## MathConstruct MC2 result (2026-11-23 10:1x UTC; MC2=1 python3 poc/mcon_xverify.py score)
Parsing the think-then-program answers into objects (405 of 1,073 parse) and checking them with the 9 progc verify(): DS over all
candidates **62.8%** vs the own-verify ladder 50.7% (+12.1 points accuracy) and vs most passing verifiers 59.5% (+3.31 [+0.83, +6.61]);
some candidate right on 71.9%. Cost: every sample is 70.4k tokens per problem, so utility loses badly to the ladder (49.1). A cheaper
pool chosen AFTER seeing this (descriptive only): gpt-oss-120b candidates (progc + think) checked by all 9 progc verifiers, 17.5k
tokens: 61.2%, U 52.4 vs ladder 49.1: +3.30 [−2.46, +9.06], not shown.

## Project Euler result (2026-11-23 10:4x UTC; python3 poc/pe_diff.py score; oracle gpt-oss-120b)
DIFF finds no gain: dev 29.2% vs plurality 30.8% (−1.67 [−4.17, 0.00]); fresh 943–992 6.0% vs 6.0%. Why: a separating small case
existed on only 26 of 120 dev and 11 of 50 fresh problems (one-argument solve() on both sides, values computable for n ≤ 12), the oracle
matched a class in 19 / 8 of those rounds, and the progc pool itself is weak (some progc right on 40% / 10%; gpt-oss-120b's
think-then-program alone is 38% / 14% and has no solve() to sweep). Not shown.
## Addendum PE2 (registered 2026-11-23 10:4x UTC, before generation)
The strong Project Euler answers (think-then-program) cannot be separated because their programs have no solve(). PE2 asks the same
thinking models for the progc program after thinking (mode thinkpc: solve(...) + CHECKS + main, poc/run_compute.py), gpt-oss-120b and
gpt-oss-20b, dev 120 + fresh 50, seeds 1–3; then the DIFF sweep + oracle over progc ∪ thinkpc candidates (PE_MODES=progc,thinkpc).
Test: DIFF − {plurality of the same pool, gpt-oss-120b think-then-program alone (single best source)}, accuracy and utility, per set.
## Related work for addendum MC (searched 2026-11-23 11:1x UTC)
FUSE (arXiv 2604.18547) ensembles verifiers with zero labels under Dawid–Skene assumptions; "LLMs as a jury" (2607.10139) uses
cross-family panels; "Beyond Solving" (2512.02304, ICLR 2026) finds cross-family verification helps most. MC's label-free weighting of
verifiers is FUSE's mechanism; what differs is that the verifiers are executable verify() programs written by other samples and the
candidates are constructions checked by running them. Loop mark K.
## Addendum PE3 (registered 2026-11-23 11:1x UTC, before scoring): statement checks as the separating cases for multi-argument programs
Only 4 of the first 50 thinkpc programs take one argument, so the sweep reaches few problems. Every progc / thinkpc program already runs
the small cases the statement itself gives (CHECKS, values copied from the statement — a free, label-free check). PE3: candidates =
progc ∪ thinkpc of all families and seeds; keep those that pass all their statement checks; return the most frequent final answer among
the kept (if none is kept, the most frequent overall). Test (poc/pe_checkpool.py): PE3 − {gpt-oss-120b think-then-program alone,
the plurality of the same pool}, accuracy and utility at 0.5, dev and fresh separately, paired bootstrap.
## Addendum WP (registered 2026-11-23 11:1x UTC, before running): cross-family solution checking for word problems
HO3 (2026-10-22) had each model check its OWN printed solution with a checker written from the text: it flagged 66–97% of wrong
solutions but also 18–65% of right ones, "repeating the model's comprehension errors in the other direction". Cross-family verification
is reported to help most when solver and verifier differ (Beyond Solving, 2512.02304). WP: the OTHER family writes the checker
(VERIFY_SRC_MODEL; Qwen3-8B checks gpt-oss-20b's freev solutions and vice versa) on BWOR, LogIOR and OptMATH, seeds 1–3.
Test: false-alarm rate on right solutions and catch rate on wrong ones, own vs cross checker (paired over solutions); and the HO3 policy
FF-V with the cross checker − with the own checker, utility at 0.5, clustered bootstrap. Prediction: fewer false alarms.
## Amendment DIFF-v2 (registered 2026-11-23 11:1x UTC, before running): which term to ask
v1 asks the first index where classes differ, which often separates one rare class from the rest. v2 asks the index whose split of the
remaining classes, weighted by how many samples each class has, has the largest entropy (the most informative single question under
the sample-count prior); ties to the earliest index. Same oracle, same cheap pool, same 3 rounds (DIFF_SPLIT=1, tag _split). Test:
v2 − v1 (utility, paired over sequences) and v2 − best single source.
## Addendum AIME (registered 2026-11-23 11:1x UTC, before running): the one non-saturated part of MATH + AIME
On AIME 2024+2025 (60) some stored sample is right on 56, the plurality on 50, the best single source (Qwen3-32B think) on 47. For the
57 problems with ≥ 2 answers the oracle (gpt-oss-120b, medium) sees the problem and the two most frequent answers and decides (poc/
aime_diff.py). Test: oracle-resolved − plurality, accuracy (descriptive; n = 60 gives low power — reported as counts). Prior work: LLM
as judge between candidate answers (S*, ExPairT-LLM, "LLMs as a jury"); a known mechanism (mark K).
## Addendum WP result (2026-11-23 11:2x UTC; python3 poc/wp_xcheck.py; BWOR + LogIOR + OptMATH, seeds 1–3, 822 problem-seeds per solver)
| solver | checker | false alarms on right solutions | catches wrong solutions | FF-V utility |
|---|---|---|---|---|
| Qwen3-8B | own | 35 / 49 (71%) | 102 / 116 (88%) | 22.9 |
| Qwen3-8B | gpt-oss-20b (cross) | 30 / 49 (61%) | 102 / 116 (88%) | 23.2 (+0.26 [−0.57, +1.16]) |
| gpt-oss-20b | own | 78 / 282 (28%) | 119 / 216 (55%) | 47.5 |
| gpt-oss-20b | Qwen3-8B (cross) | 187 / 282 (66%) | 168 / 216 (78%) | 45.6 (−1.93 [−3.65, −0.16]) |
**Prediction failed.** Cross-family checking does not reduce false alarms in general: a stronger checker barely helps the weak solver,
and a weaker checker hurts the strong one (it rejects 66% of gpt-oss-20b's right solutions). What sets a checker's false-alarm rate is
the checker's own reading of the text, not whether it shares the solver's family — consistent with HO3's raw cases (misread
comparisons, invented constraints). Word problems keep the fixed cascade (PREREG_FRESH) as the method.
## DIFF-v2 and AIME results (2026-11-23 11:4x UTC)
- **OEIS v2 (most-informative term):** 37.0% vs v1 36.2%; utility v2 − v1 +0.77 [−0.67, +2.27] (not shown); v2 − best single source
  **+3.93 [+1.53, +6.49]**, p 0.002; v2 − plurality +3.19 [+1.12, +5.37]. Choosing the term by the entropy of the split is at least as
  good as the first difference and keeps the win over the best single source.
- **AIME (descriptive, 60 problems):** oracle-resolved 53 vs plurality 50 vs best single source 47, some sample right on 56; the oracle
  costs 4.9k tokens per problem on top of the pool. Direction as predicted, power too low to claim.
## Addendum PE2 / PE3 result (2026-11-23 11:4x UTC; python3 poc/pe_checkpool.py; gpt-oss-120b thinkpc 3 seeds; gpt-oss-20b thinkpc still generating)
gpt-oss-120b's think-then-parameterised-program (thinkpc) is right on 38.9% (dev) / 11.3% (fresh) at 7.5k / 10.6k tokens — as good as
its plain think-then-program (38.3% / 14.0%), so asking for solve() + CHECKS costs nothing in accuracy. PE3 (statement-check-filtered
plurality over all progc + thinkpc): dev utility 25.8 (accuracy 44.1%) vs gpt-oss-120b think-then-program alone 36.1 (38.3%):
−10.32 [−15.89, −4.62]; fresh −17.56 [−26.16, −8.31]; vs the pool's plurality +2.50 / +4.00 (not shown). **Not shown against the
single best source:** pooling raises accuracy (+5.8 points on dev) but pays for every sample (36.7k / 47.9k tokens). On Project Euler a
single strong think-then-program sample remains the best utility at 0.5 per ktok.
## Addendum OEIS-F (registered 2026-11-23 11:4x UTC, before any fresh row): confirm the OEIS win on sequences no model or decision has seen
Fresh set: OEIS entries A389000–A391999 (added after the 500-sequence set and after every model's training data), fetched with the OEIS
JSON API; kept if the keyword list has "easy" or "hard" (the benchmark's split, 2411.04372), not "dead", and ≥ 10 listed terms; the first
250 of each level by A-number (nlp_data/compute/oeis_fresh.json; graded on the first 20 listed terms as before). Runs: prog (cheap
programs) for Qwen3-8B, gpt-oss-20b (low) and gpt-oss-120b (low), seeds 1–3; DIFF v2 (most-informative term, gpt-oss-120b referee)
over that pool. Test: DIFF − best single source fixed in advance as gpt-oss-120b prog seed 1 (the winner on the original set), and −
plurality; utility at 0.5, clustered bootstrap, one-sided, Holm over two. Prediction: both positive.
