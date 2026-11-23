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
- *OEIS-F set built (2026-11-23 11:5x UTC, by the registered rule):* 3,000 entries fetched; 644 easy and 59 hard pass the filter (hard OEIS entries
  rarely list ≥ 10 terms), so the set is 250 easy + 59 hard = 309 sequences. Generation: Slurm 1560557 (Qwen3-8B), 1560558 (gpt-oss-20b),
  1560559 (gpt-oss-120b), prog seeds 1–3; then DIFF v2.
## Addendum MC-SEQ (registered 2026-11-23 11:5x UTC, before running): buy MathConstruct samples one at a time
MC2 is accurate (62.8%) but pays for every sample (70k tokens); the cost-limited pool chosen afterwards was not significant. MC-SEQ
acquires samples sequentially (sources: progc and parsed think-then-program of the three families, seeds in order). After each
acquisition, the Dawid–Skene model (fitted label-free on the other half of problems, cross-fitted) gives each candidate's posterior of
being right using every verify() acquired so far. The next source s is bought only if its expected gain is positive:
100 · p_s · (1 − P_best) − λ · c_s, where p_s is the fitted rate at which s's candidates are right (label-free, from the posterior), P_best
the current best candidate's posterior, c_s its mean tokens, λ = 0.5 per ktok; otherwise return the best candidate. No hand threshold.
Test (poc/mcon_seq.py): MC-SEQ − own-verify ladder (gpt-oss-120b) and − gpt-oss-120b think-then-program alone, utility, paired
bootstrap over problems, Holm over two.
- *MC-SEQ result (2026-11-23 11:5x UTC; python3 poc/mcon_seq.py):* 63.6% accuracy (MC2's 62.8% at a third of its tokens: 24.0k vs 70.4k; 9.1 samples
  bought per problem), utility 51.6 vs the own-verify ladder 49.1: +2.53 [−4.16, +8.98] (p 0.23) and vs gpt-oss-120b think-then-program
  45.3: +6.37 [−0.53, +13.55] (p 0.037) — neither holds under Holm. Highest MathConstruct accuracy of any method here at the best
  utility, but not a shown utility win; it still buys about nine samples, because the myopic gain uses the source's average right-rate
  rather than the rate on problems like this one.
## Addendum JUDGE (registered 2026-11-23 11:5x UTC, before running): the recent-research baseline on the same pool
S* (arXiv 2502.14382) and LLMCodeChoice show the judge the candidates' outputs on a separating input and let it pick. JUDGE runs
exactly DIFF v2 (same pool, same most-informative index, same gpt-oss-120b, same 3 rounds) except that the prompt also lists the
candidates' values for that term (DIFF_JUDGE=1, tag _judge). Test: DIFF v2 − JUDGE, utility, paired over the 500 sequences, two-sided.
Hypothesis: showing the values anchors the judge on the plurality's (often shared) wrong value, so DIFF v2 ≥ JUDGE.
## Addendum MC-SEQ2 (registered 2026-11-23 11:5x UTC, before running): problem-specific right-rate in the stopping rule
MC-SEQ used each source family's average right-rate p_s, so it kept buying on problems where that family keeps failing. MC-SEQ2 gives
p_s a Beta prior per family whose mean and strength come from the fit half by the method of moments (mean and between-problem variance
of the per-problem posterior right-rate; no hand constant), and updates it on THIS problem with the posteriors of the family's
candidates already bought. Everything else as MC-SEQ. Test: MC-SEQ2 − {own-verify ladder, MC-SEQ}, utility, paired bootstrap.
- *MC-SEQ2 result (2026-11-23 11:5x UTC; SEQ2=1 python3 poc/mcon_seq.py):* worse — 63.6% at 40.9k tokens (11.3 samples), utility 43.2 vs ladder
  49.1 (−5.92 [−13.65, +1.54]) and vs MC-SEQ 51.6. The between-problem variance of the right-rate is large, so the fitted Beta prior is
  weak and a few uncertain posteriors on the first samples raise the estimated rate instead of lowering it; the stopping rule then buys
  more. Not adopted; MC-SEQ stays the MathConstruct line.
## Hourly check 2026-11-23 12:4x UTC
- **Qwen3-8B as the referee (OEIS, complete):** cheap pool 34.2% vs plurality 32.2% (+2.0 accuracy) but its single-term reasoning costs
  14.2k tokens per sequence (gpt-oss-120b: 3.2k), so utility −5.09 [−7.36, −2.76]. The referee must be a model that computes one term
  cheaply; a weak model thinks at length and erases the gain.
- **OEIS-F (fresh):** the first Slurm submission had to be repaired — OEIS offsets came as text ("0,3"; fixed to the first integer),
  then the Qwen3-8B job failed on a GPU still held by the cancelled job's container, and the chained referee ran on a two-family pool;
  that output is set aside (oeisf_diff_cheap_split_2fam_INVALID.jsonl). gpt-oss-20b and gpt-oss-120b programs are done (seed means
  37.9% / 45.3% right); Qwen3-8B programs and the registered three-family referee run now on gs15 GPU 7 (lane of_fresh).
- JUDGE (S*-style) running on gs15 GPU 6 (77 / 500).
## OEIS-F result — registered fresh confirmation (2026-11-23 13:0x UTC; 309 sequences A389000–A391999, three families' cheap programs × 3 seeds, DIFF v2 with gpt-oss-120b)
DIFF 53.1% vs plurality 49.5% vs gpt-oss-120b program alone 44.0% (some sample right on 55.0%); tokens 5.2k pool + 2.9k referee.
**DIFF − best single source +5.34 [+1.82, +8.90], p 0.0005; DIFF − plurality +2.09 [+0.17, +4.26], p 0.015 — both hold (Holm over two).**
The OEIS result replicates on sequences added after every model's training data and after any decision here.
## Addendum REF20 (registered 2026-11-23 13:0x UTC): a cheaper referee
gpt-oss-120b referees for 2.9–3.2k tokens per sequence; Qwen3-8B cost 14k and lost. REF20: the same DIFF v2 on the original 500-sequence
cheap pool with gpt-oss-20b (medium) as the referee (tag _split20). Test: REF20 − best single source and − DIFF v2 (gpt-oss-120b),
utility, paired; reported with the referee's tokens.
## Project Euler selection bound (2026-11-23 13:3x UTC; stored thinkpc rows, labels used only for the bound)
gpt-oss-120b thinkpc: one sample right on 38.3% (dev) / 10.0% (fresh) at 7.5k / 10.6k tokens; any of its 3 seeds right on 47.5% / 18.0%;
any of 6 (adding gpt-oss-20b) on 48.3% / 20.0%. A PERFECT selector over 3 seeds gains at most +9.2 / +8.0 accuracy points for two more
samples (+15.0k / +21.2k tokens = 7.5 / 10.6 utility at 0.5 per ktok): at most +1.7 utility on dev and −2.6 on fresh. So at the course
rate no selection or verification method over extra samples can beat one strong sample on Project Euler by more than ~2 points; what is
left is making the single sample better (generation), not choosing among samples. This closes the selection line for Project Euler.
## Addendum PE-R (registered 2026-11-23 13:3x UTC, before running): make the single Project Euler sample better instead of choosing among samples
By the bound above, only generation can still gain on Project Euler. gpt-oss-120b thinkpc fails visibly on many rows (dev: 113 of 360
crash or time out, 92 fail a statement check). PE-R gives such a row ONE repair turn with the evidence (the error, or each failing
statement case as stated vs computed); the repaired answer replaces the original if the repaired program runs and passes its checks.
Tokens of the repair are paid only on failing rows. Prior work: Self-Debug (Chen et al. 2023), LDB, ALGO — a known mechanism (mark K);
the statement's own small cases serve as the free feedback. Test (poc/pe_repair.py score): thinkpc + repair − thinkpc, utility, paired
over problems (seeds averaged), dev and fresh separately, one-sided.
## JUDGE and REF20 results (2026-11-23 13:3x UTC; original 500-sequence cheap pool)
| referee | accuracy | referee tokens | utility |
|---|---|---|---|
| DIFF v2, gpt-oss-120b computes the term blind | 37.0% | 3.23k | 32.95 |
| JUDGE (S*-style), gpt-oss-120b sees the candidates' values | 36.8% | 3.85k | 32.44 |
| REF20, gpt-oss-20b computes the term | 35.4% | 7.32k | 29.30 |
- DIFF v2 − JUDGE +0.51 [−0.13, +1.27] (two-sided p 0.13): computing the term blind is as accurate as judging the shown values and a
  little cheaper; the anchoring hypothesis is not shown. The recent-research baseline is matched, not beaten.
- REF20 − best single +0.28 [−2.43, +3.03]; − DIFF v2 −3.65 [−4.98, −2.45]: the smaller referee reasons twice as long for less accuracy.
  Across three referees, the method needs a referee that computes one term cheaply (gpt-oss-120b: 3.2k; gpt-oss-20b: 7.3k; Qwen3-8B 14.2k).
## Addendum JUDGE-F (registered 2026-11-23 13:3x UTC, before running): DIFF v2 vs the S*-style judge on the fresh 309 sequences
Same pool and referee as OEIS-F; JUDGE variant (DIFF_JUDGE=1). Test: DIFF v2 − JUDGE, utility, two-sided, paired; pooled with the
original 500 as a second, descriptive line.
- *PE-R also for gpt-oss-20b thinkpc (2026-11-23 13:3x UTC, descriptive second line; lane perep20 on gs15 GPU 7).*
## Hourly check 2026-11-23 13:4x UTC
- PE-R gpt-oss-120b (Slurm 1561672) running since 13:33, no errors. PE-R gpt-oss-20b (gs15 GPU 7): first 16 repaired dev rows (seed 1)
  — 11 run, 5 right; one right repair (pe26) still fails a stated check, so the registered acceptance rule (checks must pass) will not
  take it — the rule is kept as registered.
- JUDGE-F (gs15 GPU 6): 10 / 309.
## JUDGE-F result (2026-11-23 13:5x UTC)
Fresh 309: DIFF v2 53.1% (U 49.0) vs S*-style judge 52.8% (U 48.4): +0.63 [−0.79, +2.19], two-sided p 0.41. Pooled with the original 500
(809 sequences, descriptive): +0.56 [−0.12, +1.25], p 0.11. **Computing the term blind and judging the shown values tie on both sets**;
DIFF is consistently a little cheaper (fewer referee tokens) but not significantly better. Constructive reading: the contribution over S*
is not the referee prompt but carrying separate-and-ask to math sequences with a most-informative-term choice; against the strongest
simple baselines (best single source, plurality) the method wins on both sets.
## Addendum POOL (registered 2026-11-23 13:5x UTC, before running): how many cheap programs to buy
DIFF v2 on the fresh 309 with pools of 3 (one seed per family) and 6 (two seeds) programs instead of 9 (DIFF_SEEDS=1 / 1,2; tags _s1,
_s12). Reported as a curve (accuracy, tokens, utility) with paired intervals against the 9-program pool and the best single source;
the pool size is a design choice to report, not to tune on this set.
## PE-R result, gpt-oss-120b (2026-11-23 14:0x UTC; python3 poc/pe_repair.py score)
| set | thinkpc | + one repair on visible failure | utility difference |
|---|---|---|---|
| Project Euler dev (120 × 3 seeds) | 38.9%, U 35.1 | 44.4%, U 38.8 | **+3.64 [+1.12, +6.61]**, p 0.0015 |
| Project Euler fresh 943–992 (50 × 3) | 11.3%, U 6.0 | 14.7%, U 6.6 | +0.53 [−2.04, +3.41], p 0.37 |
Repaired rows: 184 / 360 and 103 / 150. **Holds on dev, not shown on the fresh set** (+3.4 accuracy points there, but repairs cost as much as
they gain when right answers are this rare). Thinkpc + repair (U 38.8) is also above the earlier best single source on dev (gpt-oss-120b
think-then-program, U 36.1). Unlike selection, which the bound caps at +1.7, improving the single sample moves Project Euler.
## Where the OEIS method still fails (stored DIFF v2 rows)
Of the sequences DIFF gets wrong, the right answer is absent from the pool in 304 of 315 (original) and 139 of 145 (fresh); the referee
misses a present right class in only 11 / 6. Selection is essentially solved on OEIS; the remaining gap is generation.
## Addendum OEIS-R (registered 2026-11-23 14:0x UTC, before running): use the referee's term to repair when it rejects every candidate
When the referee's term matches no class (194 of 500 original, 87 of 309 fresh sequences; the pool truly has no right program in 95% /
89% of them), give ONE repair turn to the most frequent class's program with the evidence "a careful computation gives a(N) = v, your
program prints w" (gpt-oss-120b, medium); the repaired program replaces DIFF's answer if it now prints v at N (free consistency check).
Repair tokens are paid. Prior work: Self-Debug / LDB (repair from feedback), ALGO (oracle-checked programs) — here the feedback is the
referee's single term. Test (poc/oeis_repair.py score): DIFF + repair − DIFF, utility, paired; fresh set decisive, original reported.
## Related work for the OEIS line (searched 2026-11-23 14:2x UTC)
The OEIS task and grading follow O'Malley et al. (arXiv 2411.04372, NeurIPS 2025 datasets track): name + comments in, a program out,
20-term unit tests, lookup-table detection. Their reported finding is that reasoning models (o3, o4-mini, Gemini 2.5 Pro) beat
non-reasoning ones and hard sequences stay poor; no gpt-oss or Qwen3 numbers and no selection or referee method were found for it. Our
fresh set (A389000–A391999) extends their "contemporary" idea past every model's cutoff.
## OEIS-R result (2026-11-23 14:2x UTC; python3 poc/oeis_repair.py score)
| set | repairs | consistent with the referee's term | right | accuracy | utility vs DIFF v2 |
|---|---|---|---|---|---|
| fresh 309 (decisive) | 77 | 34 | 6 | 53.1% → 53.4% | −0.12 [−1.18, +0.93] |
| original 500 | 173 | 72 | 13 | 37.0% → 39.0% | +1.45 [+0.23, +2.85], p 0.009 |
**Not shown on the fresh set** (registered decisive). A repaired program that matches the referee's single term is right only 18% /
18% of the time (13 / 72, 6 / 34): one term is a weak acceptance test for a whole 20-term sequence, and the repairer mostly patches the
program to hit that one value. The referee's term is a good detector of a wrong pool (89–95%) but not a sufficient guide for repairing it.
## Addendum OEIS-R2 (registered 2026-11-23 14:2x UTC, before running): three referee terms as feedback and as the acceptance test
OEIS-R's single term let the repairer patch the program to hit one value (18% of consistent repairs right). R2: on the same triggered
sequences, the referee also computes the two most-disputed other terms (entropy of the candidates' values, sample-weighted); the repair
sees all three (stated vs printed) and is accepted only if it prints all three. Test: R2 − DIFF v2, utility, paired, fresh decisive.
## POOL result and hourly check (2026-11-23 14:3x UTC; fresh 309)
| cheap programs (families × seeds) | accuracy | some sample right | tokens | utility | vs best single source | vs 9-program pool |
|---|---|---|---|---|---|---|
| 3 (3 × 1) | 48.5% | 49.5% | 3.5k | 46.8 | +3.13 [+0.95, +5.66] | −2.21 [−4.92, +0.42] |
| 6 (3 × 2) | 52.1% | 53.4% | 5.9k | 49.2 | +5.50 [+2.48, +8.70] | +0.15 [−1.76, +2.07] |
| 9 (3 × 3) | 53.1% | 55.0% | 8.1k | 49.0 | +5.34 [+1.82, +8.90] | — |
Every pool size beats the best single source; utility saturates at 6 programs (the 9th program costs about what it adds). With selection
near the "some sample right" ceiling at every size (48.5 vs 49.5, 52.1 vs 53.4, 53.1 vs 55.0), the curve is the pool's coverage curve.
Hourly: PE-R gpt-oss-20b lane had stopped with partial rows and no error in its log; resubmitted (it resumes). OEIS-R2 running (Slurm).
## Addendum POOL-F (registered 2026-11-23 14:4x UTC, before running): a fourth family instead of more seeds
POOL shows that selection sits at the pool's coverage ceiling, so coverage per token decides utility. POOL-F adds Qwen3.6-35B-A3B
(FP8, 3B active; a newer family) cheap programs on the fresh 309 (3 seeds, no thinking), then DIFF v2 over (a) the 12-program pool of four
families and (b) the 8-program pool of seeds 1–2 of all four families; reported as coverage / accuracy / tokens / utility next to POOL.
## OEIS-R2 result (2026-11-23 15:1x UTC; OEIS_R2=1 python3 poc/oeis_repair.py score)
Worse than one term: fresh −1.94 [−2.41, −1.50], original −1.47 [−2.22, −0.56]. The three-term test rejects most repairs (consistent
10 / 77 fresh, 38 / 173 original) — including 8 right repairs per set whose program disagrees with one of the referee's extra terms:
the REFEREE is wrong on some of those terms. One referee term at the most-disputed index is accurate enough to choose among candidates,
but repairing a program needs several trustworthy terms, and each extra referee term adds its own error and two more thinking calls.
Conclusion for the OEIS generation gap: referee-guided repair does not close it at this referee's accuracy; the selection result
(DIFF v2) stands as the OEIS method.
## Addendum MC-R (registered 2026-11-23 15:1x UTC, before running): repair before thinking on MathConstruct
PE-R showed that improving the single sample pays where selection cannot. MC-R inserts ONE repair turn into the own-verify ladder: a
progc construction whose own verify() fails (or that crashes) is repaired with that evidence; the repaired construction is used if its
verify() passes, else the ladder falls back to think-then-program as before. Repair tokens are paid. Prior work: Self-Debug / LDB
(known mechanism, mark K). Test (poc/mcon_repair.py score): ladder + repair − ladder, utility, paired over problems (seeds averaged),
gpt-oss-120b (registered) and gpt-oss-20b (descriptive).
## Hourly check 2026-11-23 15:3x UTC
- PE-R gpt-oss-20b (descriptive line) complete: dev +1.05 [−0.10, +2.68], fresh +0.41 [−0.43, +1.86]. It was never stuck: only 36% of
  gpt-oss-20b's thinkpc replies contain a program at all (16k cap reached while thinking), so just 48 rows were repair-eligible. For the
  weaker family the bottleneck is producing any program, not fixing one.
- POOL-F: the Qwen3.6 programs are done (3 × 309), but the referee lane's command was mis-escaped and did not run; rewritten and
  requeued (gs15 GPU 6, lane poolf2). MC-R (Slurm 1562504) pending in the queue.
## MC-R result (2026-11-23 16:0x UTC; python3 poc/mcon_repair.py score; gpt-oss-120b, 121 problems × 3 seeds)
Own-verify ladder 50.7% at 3.20k tokens (U 49.1) → ladder + one repair turn **59.5% at 4.19k (U 57.4): +8.32 [+5.24, +11.60], p 0.0002.**
221 programs failed their own verify(); the repair's verify() passed on 92, and 82 of those are right (89% precise), so most repaired
constructions skip the 3.2k-token think. This is the best MathConstruct utility of every method here (MC-SEQ 51.6, think alone 45.3),
at about a sixth of MC-SEQ's tokens. Constructive reading: on MathConstruct the model's own checker is precise enough to drive a cheap
fix, and improving one sample beats choosing among many — the same lesson as Project Euler (PE-R +3.6 on dev).
