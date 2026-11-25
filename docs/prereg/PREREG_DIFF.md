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
## Addendum OEIS-B (registered 2026-11-23 16:0x UTC, before running): the MC-R lesson on OEIS
A gpt-oss-120b cheap program whose first 8 terms disagree with the same model's brute force gets ONE repair turn (term-by-term evidence);
the repair replaces the program if its first 8 terms then equal the brute force's. Brute-force tokens and repair tokens are paid on
every sequence / every repaired one. Original 500 sequences (the fresh set has no brute-force rows), seeds 1–2. Test
(poc/oeis_brute_repair.py score): program + check + repair − program alone, utility, paired. Prior: ALGO (brute-force oracle), Self-Debug.
## Comparison with published numbers (2026-11-23 16:1x UTC; descriptive — different models, metrics differ as noted)
- **OEIS** (O'Malley et al., 2411.04372 v3, contemporary half = our 500; 4 s limit; their "Avg. Score" gives partial credit per term):
  best published contemporary-easy scores o3 73.6, gemini-2.5-pro 72.3, o3-mini 70.5, o4-mini 70.3; contemporary-hard o3-mini 32.0, o4-mini
  31.8, o3 29.7. Ours on the same 500 in their metric: gpt-oss-120b program alone easy 67.2 / hard 21.7; gpt-oss-20b think 68.9 / 26.6.
  DIFF v2 under the STRICTER all-20-terms metric: easy 70.0% (a lower bound on its Avg. Score) — open-weight models with DIFF reach the
  o3-mini / o4-mini level on contemporary-easy at ~8k tokens per sequence. Hard: DIFF strict 4.0%, not comparable to their partial-credit
  hard scores (strict accuracy on hard is near zero for every source here).
- **MathConstruct** (Balunović et al., 2502.10197 v1: 121 problems, best model o3-mini ~60% average accuracy over variations): ours, one
  instance per problem, gpt-oss-120b ladder + repair (MC-R) 59.5% — the paper's best level, with a 120B open model; instance mixes differ.
- **Project Euler 943–992:** MathArena does not publish answers or per-model Euler scores, so no published comparison exists.
## Mapping the recent selection methods onto our baselines (2026-11-23 16:1x UTC)
- Semantic Voting / execution-fingerprint clustering (2605.08680): cluster candidates by their outputs on probe inputs, vote over clusters.
  On OEIS the 20 graded indices ARE the probe inputs and our "plurality" baseline is exactly that vote; DIFF beats it on both sets
  (+3.2 original, +2.1 fresh).
- S* (2502.14382) / LLMCodeChoice (ISSTA 2024): distinguishing input + LLM picks among outputs = our JUDGE arm; ties DIFF (+0.6, n.s.).
- ExPairT-LLM (2511.10855): pairwise equivalence / preference queries; with ≥ 2 classes per round it reduces to the JUDGE query on the
  separating index; not run separately (stated limit).
- Agentic Verifier (2602.04254): a trained input-search agent; not reproducible here without its training (stated limit).
- FUSE (2604.18547): label-free verifier ensembling = our MathConstruct Dawid–Skene cross-verification (MC); MC-R beats it in utility.
## OEIS-B result (2026-11-23 16:2x UTC; python3 poc/oeis_brute_repair.py score; original 500, gpt-oss-120b seeds 1–2)
gpt-oss-120b program alone 29.5% (U 29.1) → + own brute-force check + one repair **35.6% (U 34.2): +5.13 [+3.38, +6.99], p 0.0002.**
427 programs disagreed with the brute force; 161 repairs became consistent with it, 67 of those right (42%), while the brute-force check
itself costs every sequence its tokens. This beats the best single source by more than DIFF v2 did on this set (+3.9) at a fraction of
the pool's tokens — the MC-R lesson holds on OEIS: repair one sample with a free check before buying many.
## Addendum OEIS-B-F (registered 2026-11-23 16:2x UTC, before running): confirm on the fresh 309
gpt-oss-120b brute force (seeds 1–2, run_compute oeisf brute), then the same repair (OEISB_FRESH=1). Test: + check + repair − program
alone, utility, paired; and − DIFF v2 on the fresh set, descriptive.
## Hourly check 2026-11-23 16:3x UTC — MC-R gpt-oss-20b and POOL-F
- **MC-R gpt-oss-20b (descriptive line):** ladder U 28.9 → ladder + repair U 39.8, **+10.93 [+7.23, +14.62]**. The repair-before-thinking
  gain holds for the weaker family too (larger, since its first constructions fail more often).
- **POOL-F (fresh 309):** adding Qwen3.6 raises coverage (some sample right 55.0% → 56.3% with 12 programs) but its cheap programs
  cost 2.9k tokens each, so utility falls: 4 families × 2 seeds 46.0 (−3.02 vs the 9-program pool), × 3 seeds 43.6 (−5.38); the
  3-family pools stay best (6 programs 49.2, 9 programs 49.0). A new family pays only if its programs are as cheap as the others';
  coverage per token, not coverage, decides.
- Slurm OEIS-B-F pending in the queue; gs15 GPUs 6–7 idle → next registered step below.
## Result OEIS-B-F (2026-11-23 17:12 UTC; `OEISB_FRESH=1 python poc/oeis_brute_repair.py score`)
- **Confirmed on the fresh 309:** program alone U 44.97 → + brute check + repair U 48.12, **+3.15 [+1.36, +5.21]** (p = 0.0002; original
  set +5.13). Accuracy 44.0 → 48.5% (seed 1), 46.6 → 50.5% (seed 2); right → wrong 0 and 2.
- **The leak:** of the 100 repaired programs that agree with the brute force, 72 are wrong. The check is the same model's brute force,
  so the repair often converges on the brute force's own misreading of the definition: the two errors are correlated.
- **Against DIFF v2 on the same set (descriptive):** DIFF v2 U 49.01, so check + repair on one program comes within 0.9 of the whole pool.
- **Combining them does not pay (offline bound, so not run):** DIFF is wrong while a repaired program is consistent and right on only 2 of
  309 problems (+0.65 at most), while the brute force and repair cost 4.2k tokens per problem (−2.11). Repair fixes the problems where the
  pool already holds a right program; neither creates right programs where the pool has none, which is DIFF's failure (139 of 145).
## Addendum OEIS-E (registered 2026-11-23 17:14 UTC, before running): escalate to a thinking program where the referee rejects every candidate
**Why.** DIFF fails almost only where the pool has no right program, and the referee's "no class matches" signal finds those sequences
(fresh: 77 flagged, 71 wrong; original: 173 flagged, DIFF right on 1.2%). Repairing a pool program from referee terms failed (OEIS-R,
R2). The remaining action is a fresh program written with thinking, on the flagged sequences only. It pays iff
100 × (p_think − p_DIFF) > 0.5 × ktok_think on them; estimated on the original 500 from stored rows (gpt-oss-120b medium think, seed 2):
p_think 6.9%, 3.5k tokens, p_DIFF 1.2% → +4.0 per flagged sequence (+1.4 per sequence overall). The other stored thinking settings
(gpt-oss-120b high, gpt-oss-20b, Qwen3-8B) lose on the same estimate, so the setting is fixed now: gpt-oss-120b, medium, seed 2.
**Run.** run_compute oeisf oss120M think 2 on all 309 fresh sequences (a fresh thinking baseline as well), Slurm RTXPro6000.
**Test (fresh 309, decisive):** policy = DIFF v2; on flagged sequences replace its answer by the thinking program and pay its tokens.
DIFF + E − DIFF, utility, paired over 309. Prediction: mean > 0. Adopt if the 95% lower bound > 0; otherwise the generation gap is not
closable by escalation at this model's thinking accuracy on hard sequences (O'Malley et al. 2411.04372 report the same for o3-class).
## Competition answers at scale: MathArena's public runs (2026-11-23 17:21 UTC; descriptive, offline, no model call; poc/prep_matharena.py)
**Why.** The AIME addendum (oracle 53 vs plurality 50 of 60) had too little power. MathArena publishes every model's graded runs
(4 per problem) on post-cutoff competitions; 213 problems of AIME 2025, BRUMO 2025, HMMT Feb / Nov 2025, SMT 2025 and CMIMC 2025 have
gpt-oss-120b (high) runs; 183 also gpt-oss-20b (high), 143 also Qwen3-30B-A3B and Qwen3-235B-A22B. Tokens are their output tokens.
| policy (utility = 100 × right − 0.5 × ktok) | n | accuracy | utility |
|---|---|---|---|
| one gpt-oss-120b sample | 213 | 88% | **78.1** |
| plurality of its 4 samples (some sample right 96.2%) | 213 | 92.1% | 49.2 |
| plurality of 8 (gpt-oss-120b + 20b), some right 96.7% | 183 | 94.3% | −33.8 |
| plurality of 16 (+ Qwen3-30B, Qwen3-235B) | 143 | 92.7% | −88.9 |
- **Selection is not the lever on competition answers.** A high-effort sample costs 18–55k tokens (9–27 utility points), while the most any
  selector can add over one sample is the pool's coverage gap: 96.2 − 88 ≈ 8 points of accuracy for 3 more samples (−32). An oracle
  referee between the top answers (aime_diff.py) cannot pay for the pool it needs.
- **Nor does a second sample bought on a free signal.** Policy: one sample; if its length exceeds t, a second; if they disagree, a third
  and plurality. t chosen on AIME 2025 + BRUMO + HMMT Feb (90 problems), tested on SMT + CMIMC + HMMT Nov (123), averaged over run
  orders: utility rises monotonically in t on both halves, and the best t is "never" (dev 79.7, test 76.9 vs t = 50k: 73.3 / 73.5).
  Long outputs are more often wrong, but not enough to pay for a 20k-token second opinion.
- **Consequence for this set:** at this token price the competition-answer recipe is one gpt-oss-120b sample; what could still pay is
  a cheaper sample of the same accuracy (lower effort), not selection. Not run here: MathArena has only high-effort runs.
## Addendum MA-EFF (registered 2026-11-23 17:29 UTC, before running): the one lever left on competition answers — effort
The MathArena analysis above shows that on competition answers neither selection nor a second sample pays at our token price; the
recipe is one sample, so what remains is how much thinking that sample gets. Run (poc/ma_effort.py): gpt-oss-120b, one sample at low,
medium and high effort, seeds 1–2, temperature 1.0, 38k cap, on the 155 integer-answer problems of AIME 2025 / 2026, BRUMO, CMIMC,
HMMT Feb / Nov, SMT 2025 (AIME 2026 is after every model's cutoff), same server, so the effort is the only difference.
- MA-EFF-P1: medium − high utility (paired over problems, seed-averaged) > 0 with 95% lower bound > 0 (high's extra tokens cost more than
  its extra accuracy at λ = 0.5).
- MA-EFF-P2: low − medium < 0 (low effort loses more accuracy than it saves).
Decision: the competition-answer recipe is one sample at the effort with the best utility; reported per competition as well.
## Hourly check 2026-11-23 17:38 UTC
- OEIS-E (gs15 GPU 7; the Slurm copy was cancelled 2 s after it started, its container removed by a pinned job): 148 of 309 thinking programs.
- MA-EFF (Slurm 1563871, n95): server starting; low effort first.
- Done this hour: OEIS-B-F (+3.15, confirmed), the DIFF + repair bound (not run: +0.65 at most vs −2.11 cost), MathArena (selection and
  second samples do not pay on competition answers).
## OEIS-E result (2026-11-23 17:48 UTC; python poc/oeis_escalate.py; gs15 GPU 7)
- **Fresh 309 (decisive): +0.45 [−0.88, +1.93], p 0.28 — not shown.** On the 77 flagged sequences the thinking program is right on 9 (DIFF
  6). Original (the set the setting was chosen on): +1.39 [+0.14, +2.78]. Escalation does not close the generation gap either.
- **A missing baseline, found here:** one gpt-oss-120b medium thinking program *alone* is as good as the whole DIFF pipeline:
  fresh 48.43 vs 49.01 (−0.58 [−3.55, +2.09]), original 35.10 vs 32.95 (+2.15 [−0.45, +4.65]), at 2.8k / 3.4k tokens against the pool's
  6k + referee. They are right on mostly the same sequences (fresh: both 149, thinking only 5, DIFF only 15). DIFF's wins so far were
  against the best *cheap* single source; against a thinking program they are not shown. Constructive consequence: OEIS claims must be
  restated against this baseline, and the test below decides which recipe stands.
## Addendum OEIS-T (registered 2026-11-23 17:48 UTC, before running): DIFF v2 vs one thinking program, fresh seed
Seed 2 has been seen, so the decisive data is a new seed: gpt-oss-120b medium think, seed 3, fresh 309 (gs15). Test: think − DIFF v2,
utility, paired over sequences, seed 3 alone. Non-inferiority margin 2 points (one sequence in fifty): if the 95% lower bound > −2, the
OEIS recipe becomes the single thinking program (simpler, fewer tokens); if the upper bound < 0, DIFF stands with the claim restated
against this baseline; otherwise both are reported as equal within noise.
## OEIS-T result (2026-11-23 18:09 UTC; python poc/oeis_escalate.py think fresh 3)
Seed 3 (decisive): thinking program alone 50.8% at 2.9k tokens vs DIFF v2 53.1%; **think − DIFF +0.36 [−2.45, +3.13]** (seed 2: −0.58
[−3.55, +2.09]). Neither non-inferior by the 2-point margin nor worse: **equal within noise**, as registered. So on OEIS the claim is:
DIFF v2 beats every cheap single source (+5.3) and ties one medium thinking program at about twice the tokens. The thinking program is
the simpler recipe; DIFF's distinct value is that it needs no thinking model.
## Addendum OEIS-TB (registered 2026-11-23 18:09 UTC, before running): the brute-force check and one repair on the thinking program
OEIS-B-F showed check + repair adds +3.15 to a cheap program. The thinking program's errors are also mostly visible to the same model's
brute force: its first 8 terms disagree with it on 147 (seed 2) and 143 (seed 3) sequences, of which 132 / 125 are wrong (90% precision),
while only 23 / 27 wrong programs agree with it. Run: the same repair turn (poc/oeis_brute_repair.py, OEISB_PROG=oss120M_think), program
seed 2 with brute-force seed 2, program seed 3 with brute-force seed 1 (stored brute forces, their tokens charged), fresh 309, gs15.
Test: thinking program + check + repair − thinking program alone, utility, paired, seeds averaged. Prediction: > 0 with lower bound > 0.
Decision: holds → the OEIS recipe is "thinking program, own brute-force check, one repair" and is then compared with DIFF v2.
## OEIS-TB result (2026-11-23 18:33 UTC; OEISB_PROG=oss120M_think OEISB_BMAP=2:2,3:1 python poc/oeis_brute_repair.py score)
Thinking program 48.90 → + check + repair 49.48: **+0.58 [−0.95, +2.25], not shown** (accuracy 49.8 → 51.5% and 50.8 → 52.4%). Of 83
repaired programs that now agree with the brute force, 17 are right: the correlated-misreading leak (OEIS-B-F) is worse here, because the
thinking program and the brute force are written by the same model from the same reading. Against DIFF v2 (descriptive) +0.47 [−1.80, +2.57].
**Offline, original set (no run):** a different family's brute force decorrelates the check but is wrong more often itself: wrong
gpt-oss-120b programs pass gpt-oss-120b's brute force 23% of the time, gpt-oss-20b's 17%, Qwen3-8B's 10%; right programs pass 83%,
70%, 48%. No family gives a check that is both independent and accurate. **OEIS summary:** every generation-side method tried
(escalation, referee-guided repair, brute-force repair, thinking) lands within noise of 49–50 utility on the fresh set; the limit is the
model's reading of the definitions, which every check built by the same models shares.
## Addendum MC-R-F (registered 2026-11-23 18:33 UTC, before running): MC-R on fresh parameters
MC-R (+8.32 on 121 problems) used each problem's first variation in the paper's published results, whose objects appear in public model
outputs. MathConstruct's generators give new parameters: 137 instances of 70 held-out problems (side/construct.py, ids_mcfresh.txt; new
run_compute set "mconf"). Same recipe and settings as MC-R, gpt-oss-120b: progc (low, 8k), thinkp (medium, 16k), repair (medium), seeds
1–2, gs15. Test: ladder + repair − ladder, utility, paired over instances. Prediction: > 0 with 95% lower bound > 0.
## Hourly check 2026-11-23 18:38 UTC
- Scored this hour: OEIS-E (+0.45, not shown), OEIS-T (thinking program ties DIFF), OEIS-TB (+0.58, not shown).
- Running: MA-EFF (Slurm 1563871; low and medium done, high seed 1 running), MC-R-F (gs15 GPU 7; fresh MathConstruct progc seed 1).
## Hourly check 2026-11-23 19:37 UTC
- MC-R-F (gs15 GPU 7): progc and thinkp done for both seeds on the 137 fresh instances; repair seed 2 running. MA-EFF (Slurm 1563871):
  high effort seed 2 running (the last arm).
## MC-R-F result (2026-11-23 19:40 UTC; MC_SET=mconf python poc/mcon_repair.py score; 137 fresh-parameter instances of 70 problems, gpt-oss-120b, seeds 1–2)
- **As registered (paired over instances): ladder 49.70 → ladder + repair 53.23, +3.53 [+0.30, +7.21], p 0.016 — holds.** Right
  instances: seed 1 68 → 72, seed 2 73 → 81 of 137.
- **But the instances are not independent** (two per problem on average). Clustered by problem (70): **+3.08 [−0.48, +6.96]**, which
  does not exclude 0. The registration should have named the problem as the unit; the honest reading is "same direction, less than half
  the original effect (+8.32), not shown at the problem level".
- Why smaller: on fresh parameters the cheap program is right less often (35 / 29 of 137) and its own verify() passes less (41 / 33),
  so more instances go straight to the thinking fallback, which is strong here (65 / 68); the repair competes with a better fallback.
  The original +8.32 used the paper's published variation, whose objects are in public outputs, so part of it may be recall.
## Addendum MC-R-F2 (registered 2026-11-23 19:41 UTC, before running): problem-level replication
MC-R-F holds per instance but not per problem. A new seed (3) on the same 137 fresh instances, gpt-oss-120b, same settings. Decision unit
fixed now: the problem (70), seed 3 alone, one-sided bootstrap clustered by problem; holds if the 95% lower bound > 0. The 3-seed
clustered estimate is reported as well (descriptive; it reuses looked-at seeds).
## MA-EFF result (2026-11-23 19:57 UTC; python poc/ma_effort.py score; 155 integer-answer problems × 2 seeds, gpt-oss-120b, one server)
| effort | accuracy | tokens | utility |
|---|---|---|---|
| low | 54.2% | 1.9k | 53.24 |
| medium | 75.5% | 5.9k | 72.55 |
| high | **85.2%** | 15.2k | **77.56** |
- **P1 fails: high is best.** medium − high −5.00 [−10.24, +0.06]; high leads on every competition (AIME 2026, after the cutoff: 78.9
  vs 75.2 vs 64.1). **P2 holds:** low − medium −19.31 [−25.68, −13.20]. At λ = 0.5 the extra accuracy of high thinking on competition
  answers is worth its tokens, unlike OEIS / word problems where cheap programs win; our high number (77.6) matches MathArena's own
  gpt-oss-120b high runs (78.1 on the overlapping competitions), so the serving is comparable.
- **A free failure signal remains:** 33 of 310 high samples hit the 38k cap with no answer. Offline on the stored samples (no new
  run): high, and on a capped high a medium sample, gives 81.32 / 79.66 (seed 1 / seed 2 first) vs 78.10 / 77.01 for high alone,
  about +3; a second high sample instead gives +1.3 / +1.6. This is the visible-failure retry already in the word-problem cascade
  (PREREG_ESCT), not new; the competition-answer recipe is one high sample, and a medium retry when it runs out of room.
## Addendum EFF (registered 2026-11-23 19:58 UTC, before running): does high effort pay on the computation sets too?
MA-EFF found high > medium on competition answers; the OEIS and Project Euler recipes use medium thinking. Same question there, same
model and server type: gpt-oss-120b high effort, 38k cap. (a) OEIS fresh 309, think mode (thinking, then the program), seeds 2–3, vs
the stored medium rows (oss120M_think s2–s3). (b) Project Euler fresh (eulert, 50), thinkp, seeds 1–2, vs stored medium thinkp s1–2.
Test per set: high − medium utility, paired, seed-averaged, clustered by problem. No direction predicted (MA-EFF says high; OEIS's
cheap-program results say tokens dominate); decision: the per-set recipe takes the effort with the higher utility only if the 95%
interval excludes 0, else keeps medium (fewer tokens).
## MC-R-F2 result (2026-11-23 20:22 UTC; seed 3, 137 fresh instances, clustered by problem)
- **Holds: seed 3 alone +7.73 [+1.94, +14.11], p 0.007** (70 problems, one-sided clustered bootstrap, as registered).
- Seeds 1–3 together, clustered (descriptive; seeds 1–2 were seen): **+4.63 [+0.84, +8.50]**.
- So the repair-before-thinking gain survives fresh parameters at the problem level; its size on fresh instances is about +4.6 per
  instance (seed spread +2 to +8), against +8.3 on the paper's published variations. MathConstruct's recipe stands: own verify(), one
  repair turn on a failure, thinking only after.
## Hourly check 2026-11-23 20:36 UTC
- Scored this hour: MA-EFF (high best on competition answers), MC-R-F (+3.53 per instance, holds as registered; not at problem level),
  MC-R-F2 (seed 3, problem level: +7.73, holds). Running: EFF (Slurm 1565258; Project Euler high seed 1).
## Hourly check 2026-11-23 21:35 UTC
- EFF (Slurm 1565258): Project Euler fresh, high effort, seed 1 finished: **4 / 50 right at 37.2k tokens per problem** (most at the
  38k cap; medium thinkp: 14% at ~10k). Seed 2 and OEIS high running; the scored test follows when they finish.
## Hourly check 2026-11-23 22:35 UTC
- EFF (Slurm 1565258): Project Euler fresh at high effort, seed 2: 2 / 50 at 37.6k tokens (seed 1: 4 / 50). OEIS high seed 2 running.
## Hourly check 2026-11-23 23:35 UTC
- EFF (Slurm 1565258): OEIS high seed 2 still running (started 21:57).
## Addendum WP-PLAN (registered 2026-11-24 00:32 UTC, before any oracle call): separate-and-ask on word problems, with plans
**Why.** OEIS's DIFF works because the disputed quantity (one term) can be checked from the definition. On optimization word problems
the stored pools carry only objective values, which the text cannot check. A plan can be: the freev programs print the decision
variables. Checking a plan against the text (are the stated conditions met? what objective does the text assign to it?) is easier than
formulating (verification, not search), and it has a derived decision rule: a plan that truly satisfies the text bounds the true
optimum, so among candidates whose plan passes and whose claimed value matches the oracle's evaluation, the best value wins (sense from
the oracle); otherwise the plurality stands. Baseline JUDGE (S*-style): the oracle sees the two most frequent candidates' programs and
picks one. Related: LLM-as-judge over solver code (ORLM / OptiBench evaluations), S* (2502.14382); none checks the candidates' plans.
**Pool:** gpt-oss-20b freev (low effort, 8k cap), seeds 1–3. **Oracle:** gpt-oss-120b medium, 12k cap, up to 3 classes per disputed
problem. **Sets:** fresh OptMATH-Train 300 (omtf; pool generated now) decisive; BWOR, LogIOR, OptMATH-Bench (stored pools) descriptive.
Plurality on the stored pools: 55.9 / 53.9 / 32.2 utility vs the some-right bound 62.0 / 58.2 / 38.2 (6.1 / 4.4 / 6.0 of room).
**Test (omtf):** PLAN − plurality, utility (pool + oracle tokens), paired by problem. Prediction: > 0 with 95% lower bound > 0. Also
PLAN − JUDGE (descriptive). Decision: holds → the word-problem pool step is plan-checking; fails → word problems keep plurality / cascade.
## Hourly check 2026-11-24 00:35 UTC
- WP-PLAN started on gs15 (GPU 6: gpt-oss-20b freev pool on omtf, then the oracle; GPU 7: the oracle on the stored BWOR / LogIOR /
  OptMATH pools). EFF: OEIS high effort seed 2 still running (since 21:57).
- WP-PLAN operations (2026-11-24 00:41 UTC): the omtf pool was written under tag "oss20" (run_nlopt names files by tag, not set), so the first oracle
  pass found no pool and wrote nothing; files renamed to opt_oss20_omtf_freev_s1–3 (900 rows; 218 / 223 / 215 of 300 right per seed),
  oracle re-queued. No row was scored before this.
## WP-PLAN, stored pools (descriptive; 2026-11-24 00:47 UTC; python poc/wp_plan.py score oss20 <set>)
| set | plurality | PLAN (ours) | JUDGE | bound | PLAN − plurality | JUDGE − plurality |
|---|---|---|---|---|---|---|
| BWOR (82) | 55.94 | 57.74 | 59.14 | 62.04 | +1.81 [−0.70, +5.51] | +3.20 [−0.39, +7.92] |
| LogIOR (92) | 53.87 | 53.48 | 56.95 | 58.22 | −0.39 [−3.63, +2.88] | +3.08 [−0.14, +7.37] |
| OptMATH (100) | 32.21 | 32.71 | 33.00 | 38.21 | +0.50 [−2.62, +4.27] | +0.79 [−2.26, +3.84] |
- **The judge beats the plan check on all three.** Why, from the 160 checked plans: the oracle accepts (feasible, value matches) 26 of
  42 right candidates (62%) but also 39 of 118 wrong ones (33%). The best-value rule is sound only for an exact feasibility check; with
  a third of wrong plans accepted it is biased toward *relaxations* — a formulation that drops a constraint has a better optimum, and if
  the oracle misses that constraint too, the wrong value wins by construction. The derivation's premise (a passed plan is truly
  feasible) is the part that fails. Checking plans costs 3.8k tokens per disputed problem, comparing programs about the same.
- The omtf test runs as registered (decisive); this diagnosis was made on the stored pools before any omtf row was scored.
## Addendum MC-R-F20 (registered 2026-11-24 00:47 UTC, before running; descriptive): the MathConstruct recipe for gpt-oss-20b on fresh parameters
Same 137 fresh instances and settings as MC-R-F, gpt-oss-20b (progc low 8k, thinkp medium 16k, repair medium), seeds 1–2, gs15 GPU 7.
Reported clustered by problem: ladder + repair − ladder (original instances: +10.93). Descriptive: it tells whether the recipe carries
to the smaller family on parameters it cannot have seen.
## WP-PLAN result, fresh OptMATH-Train 300 (decisive; 2026-11-24 00:52 UTC; python poc/wp_plan.py score oss20 omtf)
| arm | utility |
|---|---|
| one gpt-oss-20b freev program (seed mean) | 72.51 |
| plurality of 3 | 80.20 |
| JUDGE (oracle compares the two leading programs) | 80.03 |
| **PLAN (oracle checks each candidate's plan)** | **81.06** |
| some right (bound) | 81.87 |
- **Prediction not shown:** PLAN − plurality **+0.85 [−0.22, +2.30], p 0.09** (65 disputed problems). It recovers half of the 1.7 points
  of room, and beats the S*-style judge (+1.03 [−0.01, +2.41]), the reverse of the stored pools, but the registered bound is missed.
- **The larger finding is the baseline:** three cheap gpt-oss-20b programs and a plurality vote reach 80.2 on these fresh problems at
  ~2.3k tokens — about the level of PREREG_FRESH's full cascade for the same model (82.6% at 3.72k, utility ~80.7), which beat
  LLMOPT-14B by +32. On OptMATH-style fresh problems the pool is near its ceiling (bound 81.9), so no selector can add much there; the
  room is on the harder held-out sets (BWOR / LogIOR / OptMATH-Bench), where the plan check's relaxation bias (above) is the obstacle.
- Scoring note: the first local score read only seed 3 of the pool (the renamed seed 1–2 files were older than the pull marker); the
  numbers above use all three seeds, the same pool the oracle saw.
## Addendum WP-PLAN2 (registered 2026-11-24 00:52 UTC, before running): the same test where there is room
On omtf the pool sat at its ceiling. optnew (SIRL's OptMATH-Bench problems outside our 100; 93 never-used problems, harder, PREREG_TYPED
H) gives room. Same pool recipe (gpt-oss-20b freev, low, 3 seeds; files tagged oss20_optnew) and oracle; decision on optnew alone:
PLAN − plurality > 0 with 95% lower bound > 0; PLAN − JUDGE reported. Given the relaxation bias seen on the stored pools, no direction is
assumed for PLAN − JUDGE.
## WP-PLAN2 result, optnew 93 (decisive; 2026-11-24 01:03 UTC)
single 20.54 · plurality 30.43 · JUDGE 32.30 · **PLAN 32.04** · bound 39.03. **PLAN − plurality +1.60 [−4.08, +7.90], not shown**;
PLAN − JUDGE −0.26 [−4.60, +4.09]. On the harder set with room (8.6 points), both oracle selectors recover about a fifth of it and are
indistinguishable from each other and from plurality at n = 93.
**Word-problem summary for this window:** across five sets the plan check and the program judge each add 0–3 points over plurality,
never shown; plurality of three cheap programs is the strong, cheap baseline (fresh omtf 80.2, near its ceiling). The obstacle for
plan checking is measured (the oracle accepts a third of wrong plans, which biases the best-value rule toward relaxations); a
constraint-level dispute question (does the text require the constraint one program has and the other lacks?) is the next form to
test, not run in this window.
## MC-R-F20 result (2026-11-24 01:33 UTC; descriptive; gpt-oss-20b, 137 fresh instances, seeds 1–2, clustered by problem)
Accuracy 25.5% → 34.7%; utility **+7.66 [+4.30, +11.31]** (original instances: +10.93). The repair-before-thinking recipe carries to
the smaller family on parameters it cannot have seen, with a larger gain than for gpt-oss-120b (+4.6), because its first constructions
fail more often and its thinking fallback is weaker.
- EFF interim (Slurm 1565258): OEIS fresh, high effort, seed 2: 142 / 309 right (46.0%) at 23.7k tokens per sequence, against medium's
  49.8% at 2.8k; seed 3 running.
## Addendum WP-CDIS (registered 2026-11-24 01:35 UTC, before running): the constraint-level dispute
The plan check failed by accepting wrong plans (relaxation bias); the program judge compares formulations as wholes. The narrowest
question between two formulations is each *difference* between them: a constraint, bound, domain or objective term one has and the other
lacks, settled by the sentence of the text that decides it; the program the text contradicts loses (CDIS prompt in poc/wp_plan.py).
Same pools, oracle and disputed problems as WP-PLAN / WP-PLAN2. Decision on optnew (the set with room): CDIS − plurality > 0 with 95%
lower bound > 0, and CDIS − JUDGE reported. No direction is assumed.
## Addendum MA-RETRY (registered 2026-11-24 01:55 UTC, before running): confirm the retry-on-cap rule with fresh samples
MA-EFF's offline estimate (high, and a medium sample when the high one hits the cap with no answer: +3.2 / +2.7) used the same stored
samples it was read from. New samples, seed 3: gpt-oss-120b high and medium on the 155 integer-answer problems (gs15). Test on seed 3
alone: (high; medium on a capped high) − high alone, utility, paired by problem. Prediction: > 0 with 95% lower bound > 0.
## WP-CDIS result (2026-11-24 01:58 UTC; python poc/wp_plan.py score oss20 <set>)
| set | plurality | JUDGE | CDIS | CDIS − plurality | CDIS − JUDGE |
|---|---|---|---|---|---|
| **optnew (decisive)** | 30.43 | 32.30 | 29.01 | **−1.42 [−6.78, +2.98]** | −3.29 [−8.57, +1.01] |
| omtf | 80.20 | 80.03 | 78.92 | −1.28 [−2.99, +0.39] | −1.11 [−2.43, −0.10] |
| BWOR | 55.94 | 59.14 | 57.94 | +2.01 | −1.19 |
| LogIOR | 53.87 | 56.95 | 52.48 | −1.39 | −4.46 |
| OptMATH | 32.21 | 33.00 | 34.87 | +2.65 | +1.86 |
- **Fails as registered** (optnew −1.42). Itemising the differences and settling each from the text does not beat the plain comparison;
  it is worse on three of five sets: telling the judge *where* to look does not add to letting it compare.
- **Word problems close for this window:** plurality of three cheap programs is the recipe; every oracle selector (plan check, whole
  comparison, constraint dispute) stays within noise of it on the five sets.
## Hourly check 2026-11-24 02:35 UTC
- Scored this hour: WP-CDIS (fails; word problems closed). Running: MA-RETRY (gs15; medium seed 3 done 155 / 155, high seed 3 81 / 155),
  EFF OEIS high seed 3 (Slurm 1565258).
## MA-RETRY result (2026-11-24 02:55 UTC; fresh seed 3, 155 integer-answer problems)
High alone 77.42 (85.2% right); with a medium sample on a capped high 80.55: **+3.13 [+0.50, +6.28], p 0.008 — holds.** 19 of 155 high
samples hit the cap with no answer; the medium retry is right on 6 of them. Competition-answer recipe confirmed on new samples: one
high-effort sample, and a medium one when it runs out of room (no pool, no selector).
## Hourly check 2026-11-24 03:35 UTC
- Scored this hour: MA-RETRY (holds, +3.13). Running: EFF OEIS high seed 3 (Slurm 1565258).
## Hourly check 2026-11-24 04:35 UTC
- EFF OEIS high seed 3 running (Slurm 1565258).
## EFF result (2026-11-24 05:35 UTC; gpt-oss-120b high vs medium, seed-averaged, paired by problem)
| set | high: accuracy @ tokens | medium: accuracy @ tokens | high − medium utility |
|---|---|---|---|
| Project Euler fresh (50) | 6.0% @ 37.4k | 14.0% @ 10.1k | **−21.66 [−30.83, −14.16]** |
| OEIS fresh (309) | 46.1% @ 24.1k | 50.3% @ 2.8k | **−14.83 [−18.14, −11.72]** |
- **Both exclude 0 the other way: medium stays.** High effort is *less* accurate here, not just dearer: on Project Euler most high
  samples hit the 38k cap before writing the program (the answer comes from running code, so a long think that never reaches the code
  scores 0); on OEIS the extra thinking does not fix the reading of the definition. Contrast MA-EFF (competition answers, where the
  answer is the end of the thought): high > medium. **The effort that pays depends on where the answer comes from** — thinking to an
  answer rewards more effort; thinking to a program rewards stopping early and running it.
## Hourly check 2026-11-24 05:36 UTC
- Scored: EFF (medium beats high on OEIS and Project Euler).
## Hourly check 2026-11-24 06:37 UTC
- gs15 GPUs free.
## Window summary — math computation (written 2026-11-24 06:37 UTC; the second 24-hour window, 11-23 10:50 → 11-24 10:50)
Per set, what stands (registered tests; fresh / held-out data where marked), and what was tried and did not.
| set | recipe that stands | evidence | tried, not shown or worse |
|---|---|---|---|
| OEIS | two medium thinking programs + the DIFF referee on their disagreements (third window: +2.37 over one, fresh); one thinking program ties or beats DIFF over cheap programs; a cheap program + own brute-force check + one repair | DIFF +5.3 vs best cheap source (fresh); OEIS-T tie (+0.36); OEIS-B-F +3.15 [+1.36, +5.21] (fresh) | referee repair (−0.12, −1.94), escalation (+0.45), think + check (+0.58), 4th family, high effort (−14.8) |
| MathConstruct | own verify(), one repair turn, then think | +8.3 (published variations); fresh: seed 3 +7.73 [+1.94, +14.11] by problem; gpt-oss-20b fresh +7.66 | — |
| Project Euler | think-then-program, medium | PE-R dev +3.64; selection bound +1.7 | PE-R fresh +0.53 (n.s.); high effort −21.7 |
| Competition answers (MathArena, 155–213) | one sample at the highest effort that rarely hits the cap (gpt-oss-120b: high; gpt-oss-20b: medium); a medium retry when it hits the cap | MA-EFF high best; MA-RETRY +3.13 [+0.50, +6.28] (fresh seed) | pools / plurality / referee (−29 to −89 vs one sample); second sample on length |
| Word problems | plurality of three cheap programs (fresh: 80.2, near its ceiling) | WP-PLAN baselines | plan check (+0.85, +1.60), program judge, constraint dispute (−1.42): all within noise |
**What carries across sets (and what does not).**
1. *Repair pays when the free check returns a value that contradicts the attempt* (verify() on the object, the statement's small case,
   brute-force terms): MathConstruct, OEIS, Project Euler dev. It does not when the check shares the attempt's misreading (OEIS: 72% of brute-force-consistent repairs are wrong).
2. *The effort that pays depends on where the answer comes from:* thinking to an answer rewards more effort (competition answers: high);
   thinking to a program rewards medium — high runs out of room before the code on OEIS / Project Euler (−15 / −22), low under-thinks
   (MathConstruct −22), and on MathConstruct high is more accurate (+8 points) but only ties medium in utility (MC-EFF, MC-EFF2 corrected
   a broader first wording of this line).
3. *A narrower question helps only where the dispute is checkable.* One disputed OEIS term (DIFF) is computable from the definition; a
   plan's feasibility under the text or an itemised constraint difference is not more checkable than the whole formulation — both
   stayed within noise of plain comparison on word problems.
4. *Selection is near its ceiling wherever a cheap pool exists* (OEIS, word problems on fresh data); the open gap is generation, i.e. the
   model's reading of the problem, which every check built by the same models shares.- Note (2026-11-24 06:40 UTC): references to proof-part work (a Lean effort test, proof-selection records) were removed from this file under the user's rule that proof progress stays off git; in WP-CDIS's registration a sentence citing that record was replaced by "No direction is assumed". No prediction, design or decision rule was changed.
## Addendum MC-EFF (registered 2026-11-24 06:40 UTC, before running): testing the "where the answer comes from" reading on a new set
EFF / MA-EFF suggest: when the answer is a program the harness runs, more thinking effort does not pay. Prediction on MathConstruct's
thinking fallback (thinkp, the answer is the constructed object printed by code): gpt-oss-120b thinkp at **low** effort on the 137 fresh
instances, seeds 1–2, vs the stored medium thinkp rows (same prompt, 16k cap). Test: low − medium utility, paired, clustered by problem.
Prediction: >= 0 (low effort loses no more accuracy than its token saving is worth). Falsified if the 95% upper bound < 0.
## MC-EFF result (2026-11-24 06:50 UTC; 137 fresh MathConstruct instances, seeds 1–2, clustered by problem)
Low effort 24.8% at 0.9k tokens vs medium 48.5% at 3.0k: **low − medium −22.21 [−29.72, −14.79]. Prediction falsified.** The reading in
the window summary was too broad: for program answers it is *high* effort that does not pay (it runs out of room before the code); low
effort under-thinks the construction and loses half the accuracy, far more than its tokens save. Corrected statement of lesson 2:
**medium is the effort for program answers (OEIS, Project Euler, MathConstruct); high only for answers reasoned to directly
(competition answers).** Both ends were tested: high on OEIS / Project Euler (−15 / −22), low on MathConstruct (−22).
## Addendum OEIS-T2 and MC-EFF2 (registered 2026-11-24 06:50 UTC, before running; descriptive)
- OEIS-T2: a new seed (3) of gpt-oss-120b medium think on the original 500, think − DIFF v2 (orig seed 2 gave +2.15 [−0.45, +4.65]),
  to see whether the tie with DIFF also holds on the second set.
- MC-EFF2: thinkp at high effort (38k) on the 137 fresh MathConstruct instances, seed 1, completing the effort grid there (low / medium
  / high). Expected from EFF: high − medium < 0.
## OEIS-T2 result (2026-11-24 07:37 UTC; descriptive)
Original 500, seed 3: one medium thinking program 37.8% at 3.3k tokens vs DIFF v2 37.0%: **think − DIFF +3.21 [+0.95, +5.50]** (seed 2:
+2.15 [−0.45, +4.65]). On the original set the single thinking program is *ahead* of the whole pool + referee; on the fresh set they
tie (+0.36, −0.58). Together: DIFF never beats one medium thinking program, and on one of two sets loses to it by ~3 utility. The OEIS
claim for the report is therefore "one medium thinking program (with its own brute-force check and repair as an option) is the
recipe; DIFF is the method when only cheap no-thinking models are available".
## MC-EFF2 result (2026-11-24 08:26 UTC; descriptive; fresh MathConstruct, seed 1, thinkp)
| effort | right | tokens | capped |
|---|---|---|---|
| low | 27.7% | 0.95k | 0 |
| medium | 47.4% | 3.0k | 0 |
| high | **55.5%** | 23.0k | 43 / 137 |
High − medium utility **−0.75 [−11.92, +10.01]**: unlike OEIS and Project Euler, high effort *is* more accurate here (+8 points) and
the gain about pays for its tokens. So the "program answers" half of lesson 2 needs a qualifier: where the program is a construction the
model must design (MathConstruct), more thinking improves it; where the program follows from reading a definition or statement (OEIS,
Project Euler), more thinking does not. Medium stays the cheaper equal choice for MathConstruct at λ = 0.5.
- MC-EFF2 add-on (08:26 UTC): seed 2 of thinkp high queued (gs15 GPU 7) to reduce the noise on the high ≈ medium utility tie.
## Hourly check 2026-11-24 08:36 UTC
- Scored this hour: OEIS-T2 (one thinking program beats DIFF by ~3 on the original set), MC-EFF2 (high ties medium in utility on
  MathConstruct, +8 points accuracy). Running: MathConstruct thinkp high, seed 2 (gs15 GPU 7, 12 / 137).
## Hourly check 2026-11-24 09:35 UTC
- MathConstruct thinkp high seed 2: 97 / 137 (gs15 GPU 7). No other runs.
## MC-EFF2, two seeds (2026-11-24 09:56 UTC; descriptive)
High 58.8% at 22.9k tokens vs medium 48.5% at 3.0k; high − medium utility **+1.12 [−8.20, +10.50]** (274 instance-seeds, clustered by
problem). Confirms seed 1: on MathConstruct high effort is ~10 points more accurate and its gain just pays for the tokens (a tie in
utility); high is the choice when accuracy matters, medium at this token price.
## Addendum MA-RETRY20 (registered 2026-11-24 09:58 UTC, before running; descriptive): the competition-answer recipe for gpt-oss-20b
Same 155 problems, gpt-oss-20b, seed 1: high (38k) and medium samples (gs15 GPUs 6 and 7, MA_TAG=oss20). Reported: high alone vs
high + medium on a capped high, and medium alone — does the recipe carry to the smaller model?
## MA-RETRY20 result (2026-11-24 10:39 UTC; descriptive; gpt-oss-20b, 155 problems, seed 1)
| policy | accuracy | tokens | utility |
|---|---|---|---|
| high | 65.2% | 24.3k | 53.00 (53 of 155 capped) |
| high, medium on a capped high | | | 63.55 (+10.56 [+5.52, +16.09] over high) |
| **medium** | **70.3%** | 11.1k | **64.76** (high − medium −11.77 [−19.69, −4.13]) |
**The effort choice is model-dependent.** For gpt-oss-20b high effort hits the cap on a third of the problems and is *less* accurate
than medium; the retry rescues most of that, but medium alone is best. So the competition-answer recipe is "the highest effort that
rarely hits the cap" — high for gpt-oss-120b (12% capped), medium for gpt-oss-20b (34% capped at high) — with the medium retry on a cap
as the guard either way.
## Window closed (2026-11-24 10:51 UTC)
The second 24-hour window (11-23 10:50 → 11-24 10:50 UTC) is over; every run registered in it is scored above, the summary table is
current, and no job of this window is running.
# Third window (from 2026-11-24 10:54 UTC): the same two goals for another 24 hours (user)
## Addendum OEIS-TP (registered 2026-11-24 10:54 UTC, before running): DIFF over thinking programs
The second window's OEIS recipe is one medium thinking program; DIFF so far ran only over cheap programs. A second thinking program
(another seed) raises "some program right" from 49.8% to 55.0% (fresh) and 36.8% to 41.0% (original) for ~3k more tokens, so DIFF's
referee — near its ceiling on cheap pools — could turn two thinking programs into more than one. Pool: gpt-oss-120b medium think,
seeds 2 and 3 (stored); DIFF v2 (entropy index, 3 rounds, gpt-oss-120b medium referee), same code (poc/oeis_diff.py, pool "all" over a
directory holding only these two files). Test (fresh 309, decisive): DIFF-over-2-thinking − one thinking program (seed mean), utility,
paired. Prediction: > 0 with 95% lower bound > 0. Original 500 reported.
## OEIS-TP result (2026-11-24 11:18 UTC; DIFF v2 over two gpt-oss-120b medium thinking programs)
| set | one thinking program (seed mean) | DIFF over two | DIFF − one |
|---|---|---|---|
| **fresh 309 (decisive)** | 48.90 | **51.27** (54.7% right; some program right 55.0%) | **+2.37 [+0.78, +3.97], p 0.002 — holds** |
| original 500 | 35.63 | 35.89 (39.8%; bound 41.0%) | +0.25 [−0.92, +1.47] |
DIFF sits at the two-program ceiling on both sets (54.7 of 55.0, 39.8 of 41.0): the referee resolves almost every disagreement between
the two thinking programs. Whether the second program pays depends on how much it adds: on fresh sequences +5.2 points of coverage for
~2.9k tokens (pays), on the original set +4.2 for ~3.3k plus referee calls (breaks even). **OEIS recipe update:** two medium thinking
programs + DIFF's referee on their disagreements (fresh: +2.4 over one program); on the original set the single program is as good.
## Addendum WP-TP (registered 2026-11-24 12:01 UTC, before running): OEIS-TP's pattern on word problems
OEIS-TP: two thinking programs + a referee on their disagreements beat one (+2.37, fresh). Word problems' hardest fresh set (optnew, 93;
plurality of three cheap gpt-oss-20b programs 30.43, bound 39.03) has room. Run: gpt-oss-120b medium, thinking, the free-solver
prompt (run_nlopt thinkfree), seeds 1–2, on optnew and omtf (300); referee = the program JUDGE (poc/wp_plan.py, WP_MODE=thinkfree),
called only where the two disagree. Decision on optnew: two thinking + JUDGE − cheap plurality > 0 with 95% lower bound > 0; also
reported: − one thinking program (seed mean), and omtf (near its ceiling with cheap programs, so a check that the recipe does not lose).
## WP-TP result (2026-11-24 13:02 UTC; gpt-oss-120b medium thinking, free-solver prompt, seeds 1–2; judge on disagreements)
| set | cheap plurality (3 × gpt-oss-20b) | one thinking program | **two thinking + judge** | two − cheap | two − one |
|---|---|---|---|---|---|
| **optnew 93 (decisive)** | 30.43 | 35.77 (37.1% right) | **46.74** | **+16.31 [+4.47, +28.08] — holds** | +10.97 [+6.73, +15.30] |
| omtf 300 | 80.20 | 80.38 | 81.71 | +1.51 [−1.48, +4.51] | +1.33 [+0.19, +2.55] |
- **Where the gain comes from (constructive check):** on optnew one of the two programs prints no value in 26 of 93 problems (both in
  23) and they disagree in only 8; most of the +11 over one program is the second program standing in when the first fails visibly,
  not the judge. That is the free failure signal the word-problem cascade already uses, here bought with a second thinking program.
- **Word-problem recipe update:** on hard problems, two medium thinking programs (take the one that prints a value; judge if both do
  and disagree) beat both cheap plurality (+16) and a single thinking program (+11); on easy fresh problems the cheap plurality is
  already at its ceiling and the two-program recipe only matches it. Published reference to add: SIRL / OptMATH models' accuracy on
  OptMATH-Bench (the source of optnew) — not yet tabulated here.
## Addendum MC-RS (registered 2026-11-24 13:02 UTC, before computing; offline on stored rows): repair vs a fresh resample — the missing baseline
MC-R was compared with "fall back to thinking"; the natural competitor is a fresh cheap program when verify()
fails. Policies per seed pair (a, b): REPAIR = progc_a; if its verify fails, the repair of progc_a; if that fails, thinkp_a.
RESAMPLE = progc_a; if its verify fails, progc_b (an independent cheap sample); if that fails, thinkp_a. Tokens charged as used.
Sets: fresh mconf (seeds 1–3, gpt-oss-120b; pairs (1,2), (2,3), (3,1)) decisive, original mcon reported. Test: REPAIR − RESAMPLE,
utility, clustered by problem. Prediction: > 0 (verify()'s failure is value evidence, unlike a compiler error). Decision: if not
shown, the MathConstruct recipe's repair step is reported as "as good as resampling", not as a gain from repair.
### MC-RS result (2026-11-24 13:03 UTC)
- **Holds: repair beats a fresh resample.** Fresh (70 problems): accuracy 56.2% vs 50.6%, **REPAIR − RESAMPLE +4.63 [+1.53, +7.79],
  p 0.002**; original (121): 59.5% vs 52.6%, +6.55 [+3.47, +10.08]. So the MathConstruct gain is from the repair itself, not just
  from a second try — consistent with lesson 1: verify()'s failure on a concrete object tells the model what is wrong.
## Baseline ASC (2026-11-24 13:03 UTC; offline on the stored gpt-oss-120b high seeds 1–3 and medium seeds 1–3, all 6 orders averaged)
Adaptive self-consistency (Aggarwal et al. 2023; ESC, Li et al. 2024): draw two high samples, stop if they agree, else a third and the
plurality. Utility 73.35 vs our recipe (one high sample, a medium one on a cap) 80.93: **ASC − ours −7.58 [−10.52, −5.00]**. The
published way of making self-consistency cheap still spends a second 20k-token sample on every problem; the recipe stands against it.
## Addendum XM (registered 2026-11-24 13:07 UTC, before running): the recipes with a newer model family (user: why not recent models?)
Every recipe of the last two windows was measured with gpt-oss (and Qwen3-8B / Qwen3.6 as cheap pool members). The newest open model on
the server is **Qwen3.8-27B (FP8; qwen3_5 architecture)**; it fits one GPU. Runs (gs15): (a) OEIS fresh 309, think mode (thinking, then
the program), 16k cap, seed 1; (b) the 155 integer-answer competition problems, thinking, 38k cap, seed 1. Reported against the
gpt-oss-120b rows already stored: (a) one thinking program each, and a **cross-family pair** (gpt-oss-120b s2 + Qwen3.8) under the DIFF
referee vs the same-family pair of OEIS-TP — the test of lesson 4 (does a different family misread differently?); (b) one sample each,
and the retry-on-cap rule. Predictions: (a) cross-family pair coverage > same-family pair coverage (55.0%); (b) no direction.
## Addendum XM2 (registered 2026-11-24 13:41 UTC, before running): two more recent families, accuracy and tokens reported separately
Qwen3.6-27B (FP8) and Gemma 4 26B-A4B (4B active), downloaded to the cluster model store. Same runs as XM, Slurm RTXPro6000, one GPU
each: OEIS fresh 309 (think mode, 16k cap, seed 1) and the 155 integer-answer competition problems (thinking, 38k cap, seed 1).
Reported per model: accuracy, output tokens per problem, utility, against gpt-oss-120b's stored rows; a recipe change follows only if a
model is better on accuracy at no more tokens, or equal on accuracy at fewer tokens (the Pareto rule the user asked for).
## Baseline CodeT on OEIS (registered 2026-11-24 14:03 UTC, before computing; offline)
CodeT (Chen et al. 2022, 2207.10397): rank programs by dual agreement — the size of a program's output class times the number of
generated test cases it passes. On OEIS the model's own brute-force programs are the generated tests (each gives the first 8 terms):
tests = gpt-oss-120b brute force seeds 1–2 (16 (n, a(n)) pairs); candidates = the same 9-program cheap pool DIFF v2 used; pick the class
with the largest class size × tests passed (ties: larger class). Tokens: pool + both brute forces. Compared with DIFF v2 (same pool),
fresh 309 decisive, utility paired.
### CodeT result (2026-11-24 14:03 UTC)
Fresh 309: CodeT 46.97 vs DIFF v2 49.01, **DIFF − CodeT +2.04 [+0.07, +4.21]**; original 500: 31.96 vs 32.95, +1.00 [−0.60, +2.70].
DIFF's one targeted referee term beats CodeT's untargeted generated tests (the model's own brute-force terms share the programs'
misreading, so they confirm wrong classes too — the same leak as OEIS-B). Same pool, same tokens for the pool (5.2k).
## Published reference rows for word problems (2026-11-24 14:04 UTC; SIRL, arXiv 2505.11792 v2, Table 2, pass@1; * = numbers that paper took from others)
OptMATH-Bench (193; our optmath = STORM's 100 of them, optnew = the other 93): DeepSeek-V3 32.6%*, **SIRL-Qwen2.5-7B 29.0%**,
OptMATH-Qwen2.5-7B 24.4%*, OptiMUS 20.2%*, GPT-4 16.6%*, LLMOpt-14B 12.5%*, ORLM-LLaMA-3-8B 2.6%*. Ours on optnew (93; not the same
subset, so descriptive): gpt-oss-20b cheap plurality 32.3%, one gpt-oss-120b thinking program 37.1%, **two thinking programs + judge
49.5%** (accuracy; 5.3k tokens + judge). IndustryOR / NL4OPT / MAMO rows from the same table are the references for the older sets
(SIRL-7B 33.0 / 96.3 / 90.0 & 62.1). Not run by us: SIRL-32B (writes COPT / Gurobi code; neither solver is in our sandbox).
## Addendum XM3 (registered 2026-11-24 14:33 UTC, before running): Mistral Small 4 (the token-efficiency candidate)
Mistral Small 4 (119B, 6B active, NVFP4; Mistral reports shorter outputs at gpt-oss-120b's level). Slurm RTXPro6000, 2 GPUs (tensor
parallel, as the model card recommends), reasoning_effort high: OEIS fresh 309 (think, 16k cap) and the 155 competition problems (38k
cap), seed 1. Same reporting and Pareto rule as XM2. If the image's vLLM cannot load the Mistral-format checkpoint the run is reported as
not run (no substitute).
## XM result (2026-11-24 15:03 UTC; Qwen3.8-27B FP8, seed 1)
| set | Qwen3.8-27B | gpt-oss-120b (stored) | Pareto |
|---|---|---|---|
| OEIS fresh 309 (think, 16k cap) | 6.5% at 15.4k tokens; **286 of 309 hit the cap** before writing a program | medium: 50.3% at 2.8k | dominated |
| Competition 155 (38k cap) | 83.2% at 17.0k (23 no answer), U 74.72 | high: 85.8% at 15.4k, U 78.10; medium: 77.4% at 5.7k | dominated by high |
- **Cross-family pair prediction fails:** coverage of {gpt-oss-120b s2, Qwen3.8} 49.8% vs the same-family pair 55.0% — Qwen3.8 adds almost
  no sequence the first program misses, because under this cap it rarely finishes. The test of lesson 4 (does another family misread
  differently?) is therefore not informative with this model; it needs a family that finishes within the budget.
- Constructive reading: on these tasks the newer Qwen spends its budget thinking (the token problem the user raised); "newer" is not
  "better per token". Recipes unchanged by the Pareto rule. XM2 (Qwen3.6-27B, Gemma 4) and XM3 (Mistral Small 4) are queued on Slurm.
## Updated goal (user, 2026-11-24 15:24 UTC): measure recent research as baselines and compare with ours
## Addendum SELB (registered 2026-11-24 15:24 UTC, before running): ExPairT-LLM and S* against DIFF on OEIS, same pool and oracle
DIFF v2 is a close variant of two recent selection methods, so they are its baselines, run on the same 9-program cheap pool with the
same oracle (gpt-oss-120b medium): **ExPairT-LLM** (AAAI 2026, 2511.10855: cluster by outputs on inputs I = first 10 indices, round-robin
pairwise membership queries, Copeland; equivalence queries not run — a stated deviation) and **S\*** (EMNLP Findings 2025: knockout with
one execution-found distinguishing input per match, both outputs shown, the oracle picks). poc/oeis_sel_baselines.py. Test (fresh 309,
decisive): DIFF v2 − each, utility paired, plus accuracy and oracle tokens separately. No direction predicted (ExPairT reports large
gains on code with o1-mini; DIFF asks the oracle to compute a term, they ask it to choose between shown values).
### SELB: S* result, fresh 309 (2026-11-24 16:24 UTC; ExPairT-LLM still running)
| method (same 9-program pool, gpt-oss-120b oracle) | accuracy | tokens / sequence (pool + oracle) | utility |
|---|---|---|---|
| **DIFF v2** (oracle computes the one most-disputed term) | **53.1%** | **8.1k** | **49.01** |
| S\* (knockout; oracle picks between two shown values at the distinguishing index) | 51.1% | 13.4k (3.4 oracle calls) | 44.44 |
**DIFF − S\* +4.57 [+2.39, +6.86]; DIFF is better on both accuracy and tokens (Pareto).** Asking the oracle to *compute* the disputed
term once, at the index that splits the classes most, beats a knockout of *pick-one-of-two* questions, which needs a call per match.
- S\* on the original 500 (2026-11-24 17:13 UTC): DIFF 37.0% at 8.1k vs S\* 36.0% at 12.0k; **DIFF − S\* +2.95 [+1.36, +4.58]** — the same direction on
  both sets, and again better on accuracy and tokens.
- XM2 operations (2026-11-24 17:23 UTC): **Gemma 4 not run** — the server image's Transformers does not recognise the `gemma4` architecture (vLLM
  refuses the checkpoint); no substitute, as registered. Qwen3.6-27B moved to gs15 GPU 7 (free now) instead of waiting behind ExPairT.
### SELB: ExPairT-LLM result, fresh 309 (2026-11-24 18:16 UTC)
| method | accuracy | tokens / sequence | oracle calls | utility |
|---|---|---|---|---|
| **DIFF v2** | **53.1%** | **8.1k** | ≤ 3 | **49.01** |
| ExPairT-LLM (round-robin membership queries, Copeland) | 53.1% | 34.7k | 9.5 | 35.73 |
| S\* (knockout, pick between shown values) | 51.1% | 13.4k | 3.4 | 44.44 |
**DIFF − ExPairT +13.29 [+11.10, +15.53]: the same accuracy at a quarter of the tokens (DIFF dominates).** ExPairT's round-robin asks
about every pair of output clusters; DIFF asks one question per round at the term that splits the classes most. On this task the two
recent methods buy no accuracy over DIFF and cost 1.6–4.3× its tokens. ExPairT's original-set pass was stopped to free the GPU for the
newer-model runs (the fresh set was the registered decision). **Summary of the OEIS selection baselines:** DIFF is ahead of CodeT
(+2.04), S\* (+4.57 fresh, +2.95 original) and ExPairT-LLM (+13.29), and is Pareto-better than S\* and ExPairT.
- XM3 (2026-11-24 18:18 UTC): **Mistral Small 4 not run** — the NVFP4 checkpoint loads but vLLM 0.22's FP4 kernels have no build for these GPUs'
  architecture ("No supported CUDA architectures found for major versions [12]"); the BF16 original (≈238 GB) does not fit our GPUs.
  No substitute, as registered. Newer-model status: Qwen3.8 dominated; Gemma 4 and Mistral Small 4 not loadable in our image;
  Qwen3.6-27B running.
## Hourly check 2026-11-24 18:23 UTC
- Running: Qwen3.6-27B on OEIS fresh (gs15 GPU 7), GenSelect proof-selection baseline (GPU 6); Leanstral (Slurm 1574885) pending.
- XM2, Qwen3.6-27B on OEIS fresh (2026-11-24 19:07 UTC): 19.7% at 14.2k tokens, 222 of 309 at the 16k cap (gpt-oss-120b medium 50.3% at 2.8k) —
  dominated, the same failure as Qwen3.8 (it thinks past the budget before writing the program). Cross-family pair coverage with
  gpt-oss-120b s2: 52.8% vs the same-family pair 55.0% — no decorrelation gain. Competition run in progress.
## Addendum TP-COND (registered 2026-11-24 19:08 UTC, before computing; offline on stored rows): buy the second thinking program only on a free failure signal
OEIS-TP's two programs + referee is a trade-off (+4.4 points for +4.0k tokens). Policy: run one thinking program (seed 2); call the
second (seed 3) and the referee only if the first prints nothing or its first 8 terms disagree with the same model's brute force
(seed 1, cost charged). Uses the stored OEIS-TP referee outcome on those sequences. Fresh 309 decisive. Reported: accuracy and tokens
vs one program and vs two + referee. Prediction: accuracy within 1 point of two + referee at <= 60% of its tokens.
### TP-COND result (2026-11-24 19:08 UTC)
| set | one program | conditional second (ours) | two + referee |
|---|---|---|---|
| fresh 309 | 49.8% @ 2.8k | **54.4% @ 6.2k** (second called on 144) | 54.7% @ 6.8k |
| original 500 | 36.8% @ 3.4k | 39.6% @ 6.2k (called on 207) | 39.8% @ 7.8k |
Accuracy within 0.3 points of two + referee (prediction holds there) but tokens are 90% / 79% of it, not <= 60% (**prediction fails**):
the brute force is paid on every sequence and flags 47% / 41% of first programs, so the second program is still bought often. Utility
equal to two + referee (+0.01 / +0.63, n.s.), above one program (+2.86 [+0.73, +5.12] fresh). A modest token saving, not a Pareto
change; the brute-force check is too loose a filter here (it shares the misreading, OEIS-B-F).
## Hourly check 2026-11-24 20:07 UTC
- Qwen3.6-27B competition run 49 / 155 (gs15 GPU 7; Qwen thinks long, ~2 h left). Nothing else of the computation track running.
## XM2 result, Qwen3.6-27B (2026-11-24 21:13 UTC; competition 155, 38k cap)
72.3% at 29.1k tokens (42 of 155 with no answer at the cap), U 57.69 — vs gpt-oss-120b high 85.8% at 15.4k (U 78.10) and medium 77.4%
at 5.7k (U 74.58): **dominated by both gpt-oss settings.** With OEIS (19.7% at 14.2k) and Qwen3.8 (6.5% / 83.2%):
**newer-model summary (Pareto rule):** of four recent general models tried, two ran and both are dominated by gpt-oss-120b on accuracy *and*
tokens (they think past the budget); two could not be loaded in our server image (Gemma 4: unknown architecture; Mistral Small 4:
no FP4 kernels for these GPUs). No recipe changes. A newer vLLM image is the prerequisite for testing Gemma 4 / Mistral Small 4.
## Hourly check 2026-11-24 23:06 UTC
- Both gs15 GPUs on the proof part's last model round (no computation run this hour). Computation track: all registered tests scored;
  next window's open items: a newer vLLM image (to test Gemma 4 / Mistral Small 4), and a method that wins on both accuracy and tokens
  where the current recipes are trade-offs (OEIS two programs, MathConstruct repair).
## Addendum GATE (registered 2026-11-25 00:06 UTC, before computing; offline on stored rows): spend thinking only where cheap programs disagree
Aim: a recipe that wins on both accuracy and tokens against OEIS-TP (two thinking programs + referee, 54.7% at 6.8k on fresh). Policy:
three cheap programs, one per family (gpt-oss-120b, gpt-oss-20b, Qwen3-8B; seed 1; ~2k tokens); if all three print the same terms,
answer with them; otherwise run OEIS-TP (stored rows) and charge its tokens on top. No threshold: unanimity of independent families is
the gate. Fresh 309 decisive. Prediction: accuracy >= 54.0% at <= 5.5k tokens (better on tokens, within 0.7 on accuracy).
### GATE result (2026-11-25 00:07 UTC)
Fresh: gate 54.7% at 8.0k vs two thinking + referee 54.7% at 6.8k (gate − two −0.58 [−0.67, −0.47]); original: 39.6% at 9.1k vs 39.8%
at 7.8k. **Prediction fails (more tokens, not fewer).** The three cheap families agree on only 74 of 309 fresh sequences (precision
94.6% there), so the gate's ~2k tokens are paid on every sequence and save the thinking programs on only a quarter. A gate pays only
if it is cheaper than what it saves times how often it fires; here 2k × 1 > 6.8k × 0.24. No win-on-both recipe found for OEIS beyond
two thinking programs + referee.
## Addendum MC-RL (registered 2026-11-25 01:06 UTC, before running): make MathConstruct's repair a win on both
MC-R is a trade-off on fresh parameters (+6.1 points for +1.7k tokens). The repair turn runs at medium effort; the same turn at **low**
effort costs a fraction of the tokens. Run: gpt-oss-120b, low effort, the same repair prompt, on the 137 fresh instances whose own
verify() fails, seeds 1–2 (gs15). Policy as MC-R (progc; repair on a failure; thinking only if the repair also fails). Reported against
the ladder (no repair) and MC-R (medium repair): accuracy and tokens separately. Prediction: accuracy within 1 point of MC-R at fewer
tokens than the ladder (a win on both over the ladder).
### MC-RL result (2026-11-25 01:27 UTC; fresh 137 instances, seeds 1–2, clustered by problem)
| policy | accuracy | tokens / instance | utility |
|---|---|---|---|
| ladder (no repair) | 51.5% | 3.5k | 49.70 |
| **repair at low effort** | 53.6% | 3.9k | 51.71 |
| repair at medium effort (MC-R) | 55.8% | 5.2k | 53.23 |
**Prediction fails on both counts:** low-effort repair is 2.2 points below medium (not within 1) and costs 0.4k more than the ladder
(not fewer). It sits between the two (low − ladder +2.31 [−0.88, +5.58]; low − medium −0.77 [−4.45, +3.15]): a cheaper trade-off,
not a win on both. A low-effort repair fixes fewer constructions, so more instances still fall through to thinking. MC-R (medium)
stays the recipe; no win-on-both variant found.
## Hourly check 2026-11-25 02:06 UTC
- Scored this hour: GATE (fails on tokens), MC-RL (cheaper trade-off, not a win on both). gs15 GPUs idle; no further registered
  computation step this window — remaining open items are listed in the window summary.
## Window 4 header (2026-11-25 02:57 UTC goal re-set; to 2026-11-26 03:00 UTC)
Same goal: novel recipes for the computation sets, recent research measured as baselines on our sets, accuracy and tokens separately.
## Addendum SIRL-B (registered 2026-11-25 03:02 UTC, before running): a specialised optimisation-modelling model as the word-problem baseline
The word-problem table so far compares our recipe only with our own baselines plus a published number (SIRL-7B 29.0% on OptMATH-Bench,
not our split). Run the strongest public specialised model ourselves: **SIRL-Qwen2.5-32B-COPT** (Chen et al., arXiv 2505.11792;
solver-informed RL; model card: OptMATH_166 39.8%, IndustryOR 41.0%, OptiBench 64.1%), with its own recipe (poc/wp_sirl.py: the repo's
COPT prompt, extract_code_block / extract_obj, the notebook's decode — n = 1, temperature 0.5, top_p 0.9, repetition_penalty 1.02,
16,384 tokens, 200 s per program; coptpy with its size-limited pip licence, a refused solve counts as wrong). Seed 1 (n = 1 is their
setting). Sets: optnew 93 (decisive; it is part of SIRL's own OptMATH-Bench test set), omtf 300, and the stored bwor 82 / logior 92 /
optmath 100 (descriptive). Whether SIRL's training data overlaps OptMATH-Train (omtf) is unknown; stated, not corrected.
**Primary score:** first run graded by run_nlopt.correct (no gold used). Their notebook's checker (re-run with variable types swapped
when the first result mismatches the gold) is reported second as an upper bound.
**Test (optnew):** our recipe (two medium gpt-oss-120b thinking programs + judge, WP-TP) − SIRL, utility, paired by problem, 95%
bootstrap; accuracy and tokens reported separately and labelled by the Pareto rule (win on both / trade-off with break-even price).
Prediction: ours more accurate (> +5 points), SIRL cheaper in tokens; utility difference > 0 with lower bound > 0.
- **ORLM-B (added 2026-11-25 03:05 UTC, before running; same test and sets):** the earlier specialised model **ORLM-LLaMA-3-8B** (Huang et al.,
  Operations Research 2025) with its own recipe (poc/wp_sirl.py run orlm: the README completion template, greedy, first python block,
  eval/execute.py's appended objective print, 600 s; deviation: 6,144 output tokens instead of the full context). It is on gs15 already,
  so it runs first (GPU 7) while SIRL downloads. Prediction: below SIRL and below our recipe on optnew; cheapest in tokens.
### ORLM-B result (2026-11-25 03:16 UTC; ORLM-LLaMA-3-8B, its recipe, greedy, one program per problem; python poc/wp_sirl.py score orlm <set>)
| set | ORLM-8B accuracy | tokens | utility | ours (utility): recipe |
|---|---|---|---|---|
| **optnew 93 (decisive)** | 7.5% | 1.3k | 6.86 | **46.74**: two thinking gpt-oss-120b programs + judge (WP-TP) |
| omtf 300 | 57.3% | 1.2k | 56.75 | 80.20: plurality of 3 cheap gpt-oss-20b programs (~2.3k tokens) |
| BWOR 82 | 17.1% | 1.2k | 16.47 | 55.94: same plurality |
| LogIOR 92 | 15.2% | 1.3k | 14.57 | 53.87 |
| OptMATH 100 | 6.0% | 1.6k | 5.22 | 32.21 |
- **Prediction holds (below ours, cheapest).** A trade-off by the Pareto rule (ORLM spends ~1.1k fewer tokens than the cheap plurality),
  but its break-even price is absurd: on omtf the plurality's +24 points cost 1.1k tokens, so ORLM wins only if 1k tokens are worth
  more than ~22 accuracy points (our price: 0.5). On optnew 46 of 93 programs crash (non-existent coptpy calls such as coptpy.max /
  coptpy.maximum, syntax errors) and 5 have no code: the 2024-era specialised 8B model fails mostly on code validity, not on modelling.
- COPT's size-limited pip licence refused 3 of 667 solves (counted wrong); it does not explain the gap.
## Diagnosis (descriptive, 2026-11-25 03:25 UTC; poc/wp_nbs_diag.py, CPU job 1582931): why the word-problem thinking programs print "No Best Solution"
optnew has no infeasible gold, yet 32 / 27 of 93 gpt-oss-120b thinking programs (WP-TP, seeds 1 / 2) print it. Re-running the 59 with the
CP-SAT status printed after Solve: 7 INFEASIBLE, 11 other libraries, and **41 never reach Solve** — they read the data from stdin, find it
empty and print "No Best Solution" in their input-parsing branch. Counting by code: programs that read stdin are 25 / 27 of 93 on optnew
and 33 / 31 of 300 on omtf (gpt-oss-120b thinking), 6–9 of 300 for gpt-oss-20b, ~0 for the Qwen models; 1–2 of them are right. The
harness gives empty stdin, and the prompt never says so: a specification gap, not a modelling error, and it sits inside WP-TP's numbers
(it is most of "one of the two prints no value in 26 of 93"). The October INFEAS repair targeted a different class (true over-strict models).
## Addendum WP-NOIN (registered 2026-11-25 03:25 UTC, before running): state the harness in the prompt
Change: the free-solver prompt gains one sentence, "The program receives no input (stdin is empty): write every number given in the
problem into the program itself." (run_nlopt mode thinkfreen). Run exactly as WP-TP otherwise: gpt-oss-120b medium thinking, 16k,
seeds 1–2, optnew and omtf; judge on disagreements (wp_plan.py, WP_MODE=thinkfreen, WP_SFX=_tpn).
**Test (optnew, decisive):** WP-NOIN two thinking + judge − WP-TP two thinking + judge, utility, paired by problem, 95% bootstrap.
Prediction: > 0 with lower bound > 0, and stdin-reading programs ≤ 3 of 93 per seed; accuracy and tokens reported separately (tokens
expected within ±10%). Also reported: one thinking program (seed mean) new − old, and the same on omtf.
## WP-NOIN result (2026-11-25 03:52 UTC; python poc/wp_noin_score.py <set>; gs15)
| set | cheap plurality (3 × gpt-oss-20b) | WP-TP two thinking + judge | **WP-NOIN two thinking + judge** | WP-NOIN one program (seed mean) |
|---|---|---|---|---|
| **optnew 93** | 32.3% · 3.65k · 30.43 | 49.5% · 5.44k · 46.74 | 50.5% · 5.52k · **47.78** | 46.2% · 2.62k · 44.93 |
| omtf 300 | 81.3% · 2.26k · 80.20 | 83.7% · 3.90k · 81.71 | 84.0% · 4.19k · 81.91 | 82.2% · 2.02k · 81.16 |
(accuracy · tokens per problem · utility). Programs reading stdin: 25 / 27 → **0 / 0** of 93 (optnew), 33 / 31 → 0 / 0 of 300 (omtf).
- **Registered test fails:** WP-NOIN two − WP-TP two **+1.03 [−7.65, +9.72]** (optnew); omtf +0.19 [−1.54, +1.97]. The stdin rule holds.
- **What the fix does change: the single program.** One thinking program, new − old, **+9.16 [+2.16, +16.69]** on optnew (37.1% → 46.2%
  right at the same tokens); omtf +0.77 [−1.24, +2.78]. The two-program recipe gained little because its second program was already
  covering for the first one's stdin failure: WP-TP's "+11 of two over one" was mostly that bug, as the diagnosis suspected.
- **Corrected comparison:** with the prompt fixed, two programs + judge − one program **+2.85 [−1.43, +7.06]** (optnew; +4.3 points of
  accuracy for +2.9k tokens, i.e. pays only while 1k tokens are worth < 1.5 points), omtf +0.75 [−0.43, +2.01]. Not shown; the
  word-problem recipe for hard problems becomes **one medium thinking program with the corrected prompt** (vs cheap plurality +14.5 on
  optnew at −1.0k tokens: a win on both), the second program a registered trade-off, not a shown gain.
- Lesson for every set: a free signal ("the program reads input that the harness never gives") was hiding in the baseline numbers; the
  check that finds it is reading the status behind "No Best Solution", which the scorer had folded into "no value".
- **WP-NOIN-HO (added 2026-11-25 03:52 UTC, descriptive, before running):** the corrected one-program recipe (gpt-oss-120b medium thinking, thinkfreen,
  seeds 1–2) on BWOR 82 / LogIOR 92 / OptMATH 100, so SIRL-B / ORLM-B have our recipe on every set (WP-TP never ran there).
## SIRL-B result (2026-11-25 05:06 UTC; python poc/wp_sirl_compare.py <sets>; SIRL-Qwen2.5-32B-COPT, its recipe, n = 1)
| set | SIRL-32B | ORLM-8B | cheap plurality (3 × gpt-oss-20b) | **ours: one thinking program (WP-NOIN, seed mean)** | ours-one − SIRL (utility; 95%) |
|---|---|---|---|---|---|
| **optnew 93** | 38.7% · 2.62k · 37.40 | 7.5% · 1.32k · 6.86 | 32.3% · 3.65k · 30.43 | 46.2% · 2.62k · **44.93** | +7.53 [−2.29, +17.23] |
| omtf 300 | 83.7% · 1.27k · **83.03** | 57.3% · 1.16k · 56.75 | 81.3% · 2.26k · 80.20 | 82.2% · 2.02k · 81.16 | −1.88 [−4.36, +0.62] |
| BWOR 82 | 43.9% · 1.28k · 43.26 | 17.1% · 1.20k · 16.47 | 57.3% · 2.76k · 55.94 | 70.1% · 3.24k · **68.50** | +25.24 [+14.32, +35.55] |
| LogIOR 92 | 43.5% · 1.46k · 42.75 | 15.2% · 1.30k · 14.57 | 55.4% · 3.13k · 53.87 | 62.5% · 2.98k · **61.01** | +18.26 [+9.11, +27.51] |
| OptMATH 100 | 34.0% · 2.27k · 32.86 | 6.0% · 1.57k · 5.22 | 34.0% · 3.57k · 32.21 | 47.0% · 2.35k · **45.83** | +12.96 [+0.45, +25.46] |
(accuracy · output tokens per problem · utility; BWOR corrected the same hour: the first pass graded our rows through the plurality's
numeric-only reader, which drops a printed "No Best Solution" on BWOR's two infeasible problems, while SIRL's rows counted it — a
scorer asymmetry against us, fixed.) SIRL's gold-consulting checker adds 0–1.2 points (BWOR 45.1%). COPT's size limit
refused 5 LogIOR solves. SIRL reproduces its published level (OptMATH-166 39.8% in its card; here 34.0–38.7% on OptMATH-Bench problems).
- **Registered test (optnew): fails as registered.** Two thinking programs + judge − SIRL: WP-TP **+9.35 [−2.61, +21.22]**, WP-NOIN
  +10.38 [−1.22, +21.18]; the lower bound is below 0 (93 problems). The token half of the prediction also fails: SIRL is not cheaper on
  optnew (2.62k, the same as one of our thinking programs).
- **By the Pareto rule:** on the four held-out sets our one thinking program is more accurate (+7.5 to +23.8 points); tokens are equal on
  optnew / OptMATH (win on accuracy, tie on tokens) and +1.5–2.0k higher on BWOR / LogIOR (trade-off, break-even ~10 points per ktok,
  far above our 0.5). **On omtf SIRL wins on both** in point estimate (+1.5 points, −0.76k tokens [−0.91, −0.61]): the only set where a
  public specialist beats our recipe, and it is OptMATH-Train-style synthetic data (training-data overlap with SIRL unknown, stated).
- Constructive reading: SIRL's errors on the hard sets are wrong values from running programs (optnew: 50 of 93), so its value is as a
  cheap, different-family program, not as a solver of the hard band.
## Addendum SPEC-PEER (registered 2026-11-25 05:06 UTC, before computing; offline on stored rows — every arm's accuracy above is already seen, so this is
a forking-path estimate; a fresh-problem confirmation is required before it is quoted as a gain)
Cascade with SIRL as the cross-family peer (prior work: FrugalGPT / AutoMix cascades; our own cross-family peer cascade, X-series; here
the peer is a public specialist). Policy: run SIRL (n = 1) and one cheap gpt-oss-20b freev program (seed 1); if their values agree
(run_nlopt.correct tolerance), answer it; otherwise one gpt-oss-120b thinking program (WP-NOIN, seed 1; seed 2 as the replicate, mean
of the two reported). Tokens = SIRL + cheap + thinking when escalated. Compared with ours-one (always think) per set, accuracy and
tokens separately. Prediction: omtf win on both (≤ 85% of ours-one's tokens, accuracy ≥ ours-one − 0.5); on the four hard sets
utility ≥ ours-one − 1.
### SPEC-PEER result (2026-11-25 05:07 UTC; python poc/wp_specpeer.py <sets>; offline, seeds 1–2 of the thinking program averaged)
| set | ours-one (always think) | SPEC-PEER (SIRL + cheap agree → answer, else think) | cascade − ours-one | escalated |
|---|---|---|---|---|
| optnew | 46.2% · 2.62k · 44.93 | 48.4% · 5.97k · 45.40 | +0.47 [−1.70, +3.44] | 77 / 93 |
| omtf | 82.2% · 2.02k · 81.16 | 84.2% · 2.61k · 82.86 | +1.71 [+0.54, +3.10] | 83 / 300 |
| BWOR | 70.1% · 3.24k · 68.50 | 70.7% · 4.69k · 68.39 | −0.11 [−3.75, +3.58] | 58 / 82 |
| LogIOR | 62.5% · 2.98k · 61.01 | 63.0% · 4.31k · 60.89 | −0.12 [−3.41, +3.04] | 54 / 92 |
| OptMATH | 47.0% · 2.35k · 45.83 | 46.0% · 5.51k · 43.24 | −2.58 [−6.09, +0.06] | 86 / 100 |
- **Prediction fails:** on omtf the cascade is more accurate (+2.0) but costs MORE tokens (2.61k vs 2.02k; predicted ≤ 85%), and on
  OptMATH it loses 2.6 (predicted ≥ −1). A trade-off on omtf, no gain elsewhere.
- Why (the GATE lesson again): the two cheap programs cost ~2.5k together, about one thinking program, and they agree on only 14–41% of
  the hard-set problems, so the thinking program is still bought on 58–86% of them. A pre-check pays only when it is much cheaper than
  what it saves times how often it fires. Not pursued; the word-problem recipe stays one thinking program with the corrected prompt.
## Addendum WP-NOIN-F (registered 2026-11-25 05:07 UTC, before running): the prompt fix and the SIRL comparison on a set no decision has used
WP-NOIN was found and tested on optnew / omtf, the sets whose failures motivated it (a forking path). OptiBench (605; ICLR 2025) has
never been run with gpt-oss-120b thinking or with SIRL. Run: gpt-oss-120b medium thinking, seed 1, the old prompt (thinkfree, GPU 6) and
the corrected one (thinkfreen, GPU 7), then SIRL-32B (its recipe, n = 1). Tests, paired by problem, 95% bootstrap: (1) new − old one
program, utility: prediction > 0; old-prompt stdin readers ≥ 3% of 605, new ≤ 0.5%. (2) new one program − SIRL, accuracy and tokens
separately (Pareto rule); SIRL's card reports 64.1% on OptiBench, so the prediction is "ours more accurate, SIRL cheaper" (a trade-off).
### WP-NOIN-F result, part 1 (2026-11-25 05:27 UTC; OptiBench 605, gpt-oss-120b medium thinking, seed 1)
| prompt | accuracy | tokens | utility | programs reading stdin | "No Best Solution" | no value |
|---|---|---|---|---|---|---|
| old (thinkfree) | 71.2% | 1.65k | 70.41 | 1 | 46 | 23 |
| corrected (thinkfreen) | 71.4% | 1.78k | 70.52 | 0 | 36 | 27 |
- **Prediction fails:** new − old **+0.10 [−2.71, +2.94]**; only 1 of 605 old programs read stdin (predicted ≥ 3%). The stdin failure is
  specific to the OptMATH-generated texts (optnew, omtf): they are long and data-heavy (mean 3.1k / 2.6k characters; > 40 numbers in
  80% / 82% of problems) against OptiBench's short ones (0.7k; 2%), and on such texts the model writes a data reader instead of
  embedding the data (a reading of the counts, not a tested mechanism). OptiBench does not trigger it. The fix costs nothing where the failure is absent (+0.13k tokens, accuracy
  tied), so it stays in the prompt, but its gain is a property of the OptMATH-style sets, not a general one: the +9.16 on optnew is
  quoted with that scope.
### WP-NOIN-F result, part 2 (2026-11-25 06:02 UTC; OptiBench 605; python poc/wp_sirl_compare.py optibench)
| arm | accuracy | tokens | utility |
|---|---|---|---|
| SIRL-32B (its recipe, n = 1) | 62.6% | 0.83k | 62.23 |
| ours: one thinking program (corrected prompt, seeds 1–2) | 72.3% | 1.77k | 71.43 |
- **Prediction holds (a trade-off):** ours − SIRL accuracy **+9.67 [+5.70, +13.31]** points, tokens +0.95k [+0.89, +1.01]; utility
  +9.20 [+5.20, +12.83]. SIRL loses only if 1k tokens are worth more than ~10 accuracy points (our price 0.5). SIRL's 62.6% matches its
  card (64.1%; their checker 63.5% here), so the harness runs it faithfully. On the set no decision used, the word-problem recipe
  stands against the strongest public specialist; its only win remains omtf (synthetic OptMATH-Train style).
## Addendum WP-NOIN-F2 (registered 2026-11-25 06:03 UTC, before generating the set): the two scope claims on new OptMATH-style problems
Two claims now rest on sets that were looked at: (a) the stdin failure is a property of OptMATH-style texts (seen on optnew / omtf, absent
on OptiBench); (b) SIRL wins on both on OptMATH-Train-style problems (omtf only). New set omtf2: the next 300 problems of the same
decontaminated shuffle (poc/prep_wptrain.py 8300 --fresh 300 --out omtf2_items.jsonl; disjoint from the 8,000 training items and omtf).
Run: gpt-oss-120b medium thinking, old and corrected prompts, seed 1 each; SIRL-32B (its recipe). Tests (paired, 95%): (a) old-prompt
stdin readers ≥ 5% of 300 and corrected ≤ 0.5%; new − old one program, utility ≥ 0 (omtf: +0.77). (b) SIRL − ours-one (corrected),
utility: prediction ≥ 0 (omtf: +1.88) with SIRL's tokens below ours (omtf: −0.76k).
## Window summary — math computation (written 2026-11-25 06:08 UTC; third window 11-24 10:54 → 11-25 02:57, plus the first hours of the fourth)
Per set: the recipe that stands, its evidence, and the recent-research baselines run on our sets with their own recipes
(accuracy and tokens reported separately; claims rest on wins on both, trade-offs carry their break-even price).
| set | recipe that stands | evidence (95%) | recent-research baselines on our sets | tried, not shown |
|---|---|---|---|---|
| OEIS (fresh 309) | two medium thinking programs + the DIFF referee on their disagreements | +2.37 over one program (OEIS-TP); 54.7% @ 6.8k | DIFF v2 − CodeT +2.04, − S* +4.57, − ExPairT-LLM +13.29 (same pool, same oracle) | gate on cheap agreement (more tokens), conditional second program (more tokens) |
| MathConstruct (fresh parameters) | own verify(), one medium repair turn, then think | MC-R +7.73 [+1.94, +14.11] by problem; repair − fresh resample +4.63 [+1.53, +7.79] | (the benchmark has no published method beyond direct answers) | low-effort repair (cheaper trade-off), high effort (ties) |
| Project Euler | think-then-program, medium effort | PE-R dev +3.64 (fresh n.s.) | — | high effort −21.7 |
| Competition answers (155) | one high-effort sample; a medium retry when it hits the cap | MA-RETRY +3.13 [+0.50, +6.28] | adaptive self-consistency −7.58 [−10.52, −5.00]; DeepConf not run: it needs ≥ 16 full warm-up traces, more than ASC's minimum, which already loses | pools, selectors, second sample on length |
| Word problems | one medium thinking program with the corrected (no-input) prompt | vs cheap plurality optnew +14.5 at −1.0k tokens (win on both); the fix: +9.16 [+2.16, +16.69] on optnew, +0.10 on OptiBench (OptMATH-style texts only) | SIRL-32B: ours +7.5 (optnew, n.s.) / +25.2 / +18.3 / +13.0 / +9.2 (OptiBench, fresh; trade-off at ~10 points per ktok); SIRL wins on omtf (−1.88 n.s., −0.76k tokens) and on omtf2 (−3.70 [−6.66, −1.02], −0.74k; row updated after WP-NOIN-F2); ORLM-8B far below everywhere | two programs + judge (+2.85 n.s. over one), SIRL as peer (more tokens), plan / constraint judges |
**What changed in what we know this window.** (1) A harness-specification gap (programs reading an input that is never given) sat
inside a reported gain; reading the status behind "no value" found it (now a loop checklist rule). (2) The strongest public
specialist for word problems, run with its own recipe, is behind our recipe on every hard set and on the fresh OptiBench, and ahead on
synthetic OptMATH-Train-style problems (being re-tested on a new 300, WP-NOIN-F2). (3) Every cheap pre-check (agreement gates, peers)
failed for the same arithmetic: it must cost much less than what it saves times how often it fires.
## Census (descriptive, 2026-11-25 06:10 UTC): what the corrected word-problem programs get wrong when they print a number
Wrong numeric values of gpt-oss-120b's corrected-prompt programs (seeds 1–2), by direction against the gold for the problem's sense:
optnew 43 worse / 28 better of 71; OptMATH **54 worse** / 11 better of 65; BWOR 18 / 12; LogIOR 14 / 12; OptiBench 85 / 85. On optnew /
OptMATH the "worse" ones are mostly CP-SAT programs that set their own time limit (max_time_in_seconds 30 or 60) and print the incumbent
on status FEASIBLE: 23 of 43 (optnew) and 32 of 54 (OptMATH). Such a value is one the solver has not proven optimal; the program says so
itself (the status), and the harness throws that away.
## Addendum POR (registered 2026-11-25 06:10 UTC, before any re-run): proven-optimal re-run (zero tokens)
Policy (poc/wp_optcert.py): every stored program whose code sets a CP-SAT time limit is re-run with the limit raised to 300 s (wall
360 s), the solver status logged; its value replaces the stored one when it prints one. No model call: cost = CPU seconds (reported).
Not a heuristic threshold: the program's own status says whether its value is proven; the re-run only removes the program's own cap.
Prior work: none found that uses the solver's optimality status this way in LLM optimisation-modelling pipelines (SIRL / ORLM /
OptiMUS grade the printed objective; SIRL's re-run swaps variable types after a gold mismatch) — to be searched before quoting novelty.
**Tests:** decisive on the two sets no word-problem decision has used for this question — omtf2 (corrected prompt, seed 1, when it ends)
and OptiBench (corrected prompt, seeds 1–2): new − old accuracy ≥ 0 with gained > lost, at 0 tokens. Descriptive: optnew, OptMATH
(census sets; prediction ≥ +3 points each), BWOR, LogIOR, omtf.
### POR result (2026-11-25 06:26 UTC; python poc/wp_optcert.py score <set> oss120 thinkfreen; Slurm CPU, 436 programs re-run)
**Null on every set: gained 0, lost 0** (optnew, OptMATH, BWOR, LogIOR, omtf, OptiBench; seeds 1–2). The re-runs reach OPTIMAL in
seconds (mean wall 0–17 s; 398 OPTIMAL, 15 INFEASIBLE, 1 FEASIBLE, 1 MODEL_INVALID, 22 runtime errors / timeouts — the same as stored).
**The census inference was wrong:** a program that *accepts* FEASIBLE and sets a 30 s cap is not a program whose run *ended* FEASIBLE;
the 'worse than gold' values are proven optima of the programs' own models, i.e. modelling errors (over-constrained or mis-specified),
not search cut short. Prediction (≥ +3 on optnew / OptMATH) fails; nothing to adopt. Lesson: a census by code pattern is a guess about
behaviour; the status must be read from a run before a mechanism is registered (it cost ~10 CPU-min, not GPU time, here).
## Hand audit of the hard band (descriptive, 2026-11-25 06:34 UTC; OptMATH, the 17 problems where both corrected-prompt programs print the SAME wrong value)
43 OptMATH problems are wrong in both seeds; in 17 the two programs agree on a value (SIRL prints that value too on 5). Read in full
(short texts) or in part: of the 7 read in full that could be classified from the text alone,
- **6 lack data the answer needs:** optmath-10, 30, 33, 63, 79 are job shops whose text never says which operations share a machine
  (gold makespans 5, 5, 6, 3, 3 are not derivable); optmath-74 gives no shift demands or availability.
- **1 gold is provably wrong:** optmath-93 puts five unit operations ((1,0), (1,1), (2,1), (3,1), (5,1)) on one machine, so every
  schedule needs makespan ≥ 5; the gold is 3 (both our programs print 5).
The other 10 of the 17 were read only up to 1,700–2,600 characters (66, 76, 97, 98, 46, 50, 61, 77, 23, 31) and are NOT classified; 23
looks like a genuine reading error (the text lists benefits in both directions, ours used one), 31 likewise ambiguous.
**What it bounds:** at least 7 of the 100 OptMATH problems cannot be solved from their text (a floor, not an estimate of the whole set),
for every method in the table alike. A model answer on such items is a guess: SIRL prints the gold on 30 and 63 (of the five
under-specified job shops; ours on none), which no reader of the text could derive, so its accuracy there is not evidence of modelling.
It does not change any paired comparison recorded above (all arms see the same items), but it caps what "the hard band" can yield and
says that better formulation is not the only missing piece.
### WP-NOIN-F2 result (2026-11-25 07:11 UTC; omtf2, 300 new OptMATH-Train-style problems; seed 1; python poc/wp_sirl_compare.py omtf2)
| arm | accuracy | tokens | utility | programs reading stdin |
|---|---|---|---|---|
| old prompt, one thinking program | 80.3% | 1.65k | 79.51 | 41 |
| corrected prompt, one thinking program (ours-one) | 81.3% | 2.01k | 80.33 | 0 |
| **SIRL-32B** | **84.7%** | **1.28k** | **84.03** | — |
- **(a) holds as registered:** old-prompt stdin readers 41 of 300 (13.7%, ≥ 5%), corrected 0; utility new − old +0.82 [−1.85, +3.50]
  (≥ 0 in point estimate, not significant; tokens **+0.36k**, which the earlier "costs nothing" wording for OptiBench hid: the corrected
  prompt costs +6% to +22% tokens on omtf / OptiBench / omtf2 and −1% on optnew). The scope claim stands: the stdin failure is specific to OptMATH-style texts.
- **(b) holds, and now significant:** ours-one − SIRL **−3.70 [−6.66, −1.02]** utility (accuracy −3.33 [−6.33, −0.67]; SIRL −0.74k tokens
  [−0.91, −0.58]). On OptMATH-Train-style problems SIRL wins on both, replicated on new problems. The table's statement is corrected:
  "SIRL wins on OptMATH-Train-style problems (omtf, omtf2)"; on the four other sets it loses. Our own recipe is not the best choice there.
- **Training overlap (checked, not resolved; poc/sirl_overlap.py):** the SIRL repo publishes a training SAMPLE (4,181 rows, described as a
  lightweight example set); its rows carry data_source "OptMATH". No problem of omtf / omtf2 / OptMATH-Bench / OptiBench is covered even 10%
  by any one sample row, and the share of items sharing any 13-gram with the sample is 11 / 300 (omtf), 15 / 300 (omtf2), 6 / 193
  (OptMATH-Bench), 9 / 600 (OptMATH-Train control), 0 / 605 (OptiBench): the OptMATH-family texts share generator phrases with each other,
  no duplicates. A sample cannot rule out overlap with the full training set (not published); the data_source label and the family-shaped
  phrases are consistent with SIRL being trained on this generator's style. Stated as: SIRL is in distribution on omtf / omtf2.
## Addendum PICK (registered 2026-11-25 07:12 UTC, before computing; offline on stored rows; every arm's accuracy was seen, so this is a first look only)
Question from WP-NOIN-F2: the best word-problem model depends on the set (SIRL on omtf / omtf2, ours elsewhere). Can the choice be made
WITHOUT labels, from how the arms' answers agree on the set's own problems? Method: the one-coin Dawid–Skene latent-truth model (Dawid &
Skene 1979) fitted by EM per set, on the printed numeric values of four arms from different families — SIRL-32B (seed 1), gpt-oss-120b
thinking with the corrected prompt (seed 1), gpt-oss-20b freev (seed 1; where stored), ORLM-8B — equal values (run_nlopt tolerance) are one
class, a missing value is an abstention; it returns an estimated accuracy per arm and no tuned constant. The set's arm = the one with
the highest estimated utility (100 × estimated accuracy − 0.5 × its mean ktok). Prior work: label-free model selection by agreement
(e.g. Platanios et al. 2017; MoE / router literature) — not claimed as new; the test is whether it recovers the per-set choice.
**Score per set:** the chosen arm's true utility against always-ours, always-SIRL and the per-set best (oracle); sets: omtf, omtf2 (the
two where SIRL wins), optnew, optmath, BWOR, LogIOR, OptiBench. Prediction: it picks SIRL on omtf and omtf2 and ours on ≥ 4 of the other
5, and its mean utility over sets is ≥ always-ours + 0.5. Risk stated: SIRL and ORLM share the OptMATH/COPT lineage (correlated errors),
which inflates both.
### PICK result (2026-11-25 07:27 UTC; python poc/wp_pick.py <sets>; the two missing arms were run first, so all seven sets have four arms)
Picks SIRL on omtf and omtf2 and ours-one on optnew / OptMATH / BWOR / LogIOR / OptiBench: the per-set best on 7 of 7; mean utility over
the sets **66.62 against always-ours 65.80 (+0.82) and always-SIRL 55.08**; the registered prediction holds on this first look.
Constructive reading, before any claim: (i) the arms' accuracies had been seen when the sets were chosen; (ii) the seven decisions contain
two distinct answers, and omtf / omtf2 are one distribution, so this is effectively one success against a rule ("always ours") that is
right on 5 of 7 anyway; (iii) the estimated accuracies are far from the truth (ours-one 0.76 vs 0.48 on optnew), only the order is right;
(iv) **the probe cost is not charged**: all four arms were run on every problem. (iv) is tested next.
## Addendum PICK-COST (registered 2026-11-25 07:27 UTC, before computing; offline, same rows)
Deployable version: on a set of N problems, run all four arms on m randomly drawn problems (their tokens charged), fit the same model
on those m, answer the probe problems with the picked arm's answer (its tokens already counted) and the other N − m with the picked arm
alone. Baselines: always-ours, always-SIRL (no probe). m ∈ {10, 20, 30, 50}, 300 random draws each, per set; utility per problem
(mean over draws) − always-ours; also the share of draws that pick the per-set best. Prediction: the pick recovers the best arm in ≥ 80%
of draws at m = 30 on every set, AND the mean over the seven sets of (PICK-COST − always-ours) is > 0 at some m. The second half is the
one that decides whether PICK is usable; by the arithmetic of the earlier checks (a cheap check must save more than it costs) I expect
it to fail on the small sets.
### PICK-COST result (2026-11-25 07:27 UTC; python poc/wp_pick_cost.py <sets>; 300 draws per cell)
| set | N | best arm | m = 10 | m = 20 | m = 30 | m = 50 |
|---|---|---|---|---|---|---|
| omtf | 300 | SIRL | 58% · −0.89 | 64% · +0.66 | 62% · +0.92 | 61% · +0.94 |
| omtf2 | 300 | SIRL | 74% · +1.51 | 79% · +2.51 | 84% · +2.91 | 91% · +3.01 |
| optnew | 93 | ours | 73% · −3.13 | 87% · −1.82 | 93% · −1.54 | 99% · −1.45 |
| OptMATH | 100 | ours | 74% · −4.44 | 83% · −2.88 | 91% · −2.06 | 97% · −1.73 |
| BWOR | 82 | ours | 61% · −9.81 | 79% · −5.68 | 85% · −4.37 | 95% · −2.38 |
| LogIOR | 92 | ours | 67% · −7.87 | 83% · −4.46 | 90% · −2.95 | 100% · −1.12 |
| OptiBench | 605 | ours | 61% · −4.15 | 78% · −2.47 | 87% · −1.35 | 96% · −0.48 |
(share of draws that pick the per-set best · net utility against always-ours, probe tokens charged.) Mean over the seven sets:
−4.11 (m = 10), −2.02, −1.21, −0.46 (m = 50).
- **Prediction fails on both halves:** at m = 30 the pick is the best arm in only 62% of draws on omtf, and the mean net gain is negative at
  every m. The label-free choice gains 1–3 points on the two sets where SIRL wins and pays 0.5–10 elsewhere, in probe tokens and
  wrong picks; "always ours" is the better rule over this mixture of sets. It closes PICK: the same arithmetic as GATE and SPEC-PEER.
- Useful part: at m = 50 the agreement estimate ranks the arms correctly in 91–100% of draws on six of the seven sets (omtf: 61%), so it
  tells *which* arm is better for a user who already runs several arms and has no labels; it does not pay as an automatic router here.
## MathConstruct failure census (2026-11-25 07:27 UTC; descriptive; poc/mc_census.py, CPU job 1584780; fresh-parameter 137, gpt-oss-120b seed 1)
| program | 're' (no output), re-run with stderr | 'tle' (60 s), re-run at 600 s |
|---|---|---|
| cheap (progc) | 50: 49 still 're', 1 tle; **0 right** | 40: 36 still tle, 3 finish, 1 re; **3 right** |
| thinking (thinkp) | 19: 19 still 're'; **0 right** | 23: 20 still tle, 3 finish; **1 right** |
The errors are the programs' own (RuntimeError "No suitable n found within the search limit", failed assertions, index / key errors): the
listed causes cover 44 of the 50 cheap 're' and contain no import, memory or sandbox error (the other 6 were not itemised). A 10× time
limit rescues 3 of 40 cheap and 1 of 23 thinking timeouts (at most 2.2 and 0.7 points of 137). **No hidden harness gap found; not adopted.**
## Addendum CLEAN (registered 2026-11-25 07:31 UTC, before any run): the word-problem recipes on an independently audited benchmark, against two newer models
**Why.** Found by search this hour (OptiMind, arXiv 2509.22979, Microsoft Research; read through an automatic page extraction, so its numbers below are not checked against the PDF): its authors report errors in 50% of IndustryOR's and
41% of OptMATH's original test problems, spent a month of expert cleaning, and released cleaned versions (github.com/microsoft/OptiGuide,
optimind/data). Their cleaning independently touched most of this morning's hand audit: the nearest cleaned counterparts (8-gram Jaccard 0.50–0.71) of optmath-10,
30, 33, 63, 79, 93 carry different answers from ours (6, 4, 5, 5, 5, 5 against 5, 5, 6, 3, 3, 3; the nearest item may be a sibling of the
same template, so this is indicative, not a match), and 74 has no counterpart. All earlier word-problem tables used the uncleaned labels.
**Sets:** optc (OptMATH cleaned, 128 with an answer), indc (IndustryOR cleaned, 99), mamoc (Mamo-Complex cleaned, 210). The originals of
these problems were used in earlier decisions, so this is an audit of labels, not fresh problems; the recipe was fixed before this section.
**Arms (each with its own recipe; one reader run_nlopt.correct for all; refused size-limited solves counted wrong and reported):**
(1) ours-one: gpt-oss-120b medium thinking, corrected prompt, seeds 1–2; (2) cheap plurality of 3 gpt-oss-20b freev programs; (3)
gpt-oss-20b medium thinking, corrected prompt, seed 1 — the same base as OptiMind, so it separates the fine-tune from the base; (4)
**OptiMind-SFT** (gpt-oss-20b fine-tune; the model card's system prompt, temperature 0.9, top_p 1.0, 30,000 tokens, gurobipy, no
hints / self-correction / majority voting: the K = 1 row of its paper), seed 1; (5) SIRL-32B-COPT, its recipe.
**Tests (paired by problem, 95% bootstrap; accuracy and tokens separately, Pareto rule):** ours-one − OptiMind and ours-one − SIRL on each
set and pooled over 437. **Predictions:** ours-one's accuracy ≥ OptiMind's − 3 points on each set (its paper's K = 1 rows without hints are 68.97 / 85.77 / 84.82
for IndustryOR / Mamo-Complex / OptMATH; a check of our run of it) with fewer tokens pooled; ours-one more accurate than SIRL on all
three; the same-base gpt-oss-20b below OptiMind (its paper: 66.23 / 65.03 / 74.87 for the base). If the predictions about OptiMind fail, it replaces our recipe as the
word-problem standard in the summary (a public model that wins on both is the recipe, whoever trained it).
- **Not run in CLEAN (2026-11-25 07:31 UTC):** SOLID-StepORLM (arXiv 2609.09957, Qwen3-8B, the newest open checkpoint found): its own card reports pass@1
  18.25 on OptMATH, 66.43 on Mamo-Complex and 39.81 on IndustryOR (labels as published there), below SIRL's on OptMATH; a fifth 8B model would
  not change the comparison. StepORLM (ICLR 2026, arXiv 2509.22558) likewise. Only OptiMind-SFT is downloaded.
## Diagnosis (descriptive, 2026-11-25 09:26 UTC; poc/wp_nbs_diag.py): what "No Best Solution" means on Mamo-Complex
In the CLEAN first pass (table to be recorded after its 2 failed SIRL rows are re-asked) ours loses 15 points to OptiMind-SFT on Mamo-Complex; most of it is the diet problems (ours 20 of 44 right,
OptiMind 40, gpt-oss-20b 36). Re-running all 40 of our "No Best Solution" programs there (seeds 1–2) with the CP-SAT status and validation message printed after Solve:
**33 MODEL_INVALID** ("var domain do not fall in [-kint64max / 2, kint64max / 2]", from bounds set to cp_model.INT_MAX), 4 INFEASIBLE, 3 other libraries. (My first reading from one program, "the sums
overflow", was wrong in the detail: the single variable's domain is rejected.) The formulations are not the cause: nothing was solved, and the program's
branch "else: print No Best Solution" folds a rejected model into an infeasible one. The same diagnosis of gpt-oss-20b's 29 such rows gives 20 INFEASIBLE, 9 other, no invalid model.
It is an interaction of this OR-Tools version with a constant the model writes, so it is a property of our stack (OptiMind uses Gurobi) and not a statement about the models' reasoning.
## Addendum VALID (registered 2026-11-25 09:26 UTC, before any run): give the solver's own rejection back for one repair
Trigger: the solver status of a re-run of the stored program is MODEL_INVALID or UNKNOWN (poc/wp_valid.py; no rule on the program text, no threshold; INFEASIBLE is never repaired).
V = one repair turn (gpt-oss-120b, medium thinking) with the problem, the program, the status and model.Validate()'s message; R = a fresh thinking program for the
problem (the resample baseline of MC-RS); N = the stored answer. Tokens of V / R are added to the triggered rows only. Prior work: solver / interpreter feedback repair (Self-Debug,
OptiMUS's debugging loop) is known; the test is whether a *rejected* model, told apart from an infeasible one by the solver's own status, is worth a repair (the October INFEAS repair
of truly infeasible programs fixed 8–33%).
**Data:** mamoc is where it was found, so it is descriptive only. **Decisive: easyc (MAMO EasyLP as corrected by SIRL's authors, 642) and nl4c (NL4OPT, 245, with 17 true "No Best
Solution" answers), pooled 887** — no gpt-oss-120b thinking program has been run on either; gpt-oss-120b medium, corrected prompt, seed 1. These two sets were used in October for other
questions by other models.
**Predictions:** (1) MODEL_INVALID is at least 1% of the 887 programs; (2) of the triggered programs V is right on ≥ 60%; (3) V − N pooled accuracy > 0 with 95% lower bound > 0;
(4) V − R utility ≥ 0. If (1) fails the repair has nothing to act on outside Mamo-Complex and is reported as a property of that set only. **Decision:** adopt V only if (3) and (4) hold.
### VALID result (2026-11-25 10:01 UTC; python poc/wp_valid.py score easyc nl4c oss120 thinkfreen 1; gpt-oss-120b medium, seed 1)
| set (rows) | MODEL_INVALID | of the triggered: stored right | V (repair) right | R (fresh program) right |
|---|---|---|---|---|
| easyc (642) | 51 (7.9%) | 0 | **46** | 27 |
| nl4c (245) | 8 (3.3%) | 2 | 7 | 6 |
| *mamoc (210, where it was found)* | *20 (9.5%)* | *0* | *20* | *7* |
Pooled decisive 887: N 85.6% · 1.86k · 84.64; **V 91.3% · 1.95k · 90.34**; R 89.1% · 2.00k · 88.07. **V − N accuracy +5.75 [+4.28, +7.33]**, utility +5.70 [+4.25, +7.27];
**V − R utility +2.28 [+1.37, +3.29]**. All four registered predictions hold (59 of 887 triggered = 6.7%; V right on 53 of 59 = 90%). The repair is also cheaper than the resample (1.4k vs 2.1k tokens per triggered row).
**Not adopted yet — criticism first:** (i) every trigger is MODEL_INVALID (no UNKNOWN), and every validation message printed for mamoc names the same cause (a domain of INT_MAX): the repair may be fixing ONE
library constant, at 1.4k tokens a time; (ii) a zero-token competitor exists and was not in the registration: an environment that accepts the constant; (iii) V − R is a fair comparison only against resampling,
which also re-rolls the same constant.
## Addendum ENV (registered 2026-11-25 10:01 UTC, before running): the zero-token competitor of V
Policy: run the stored program unchanged in an environment where cp_model.INT_MAX / INT_MIN are the largest domain this OR-Tools version accepts, ±(2^62 − 1) (the documented kint64max / 2; not a chosen number), by a two-line
prefix; no model call, no new tokens. Applied to the same triggered rows, graded the same way. Anything that stays invalid (e.g. overflowing sums) keeps the stored answer.
**Prediction:** ENV recovers ≥ 80% of what V recovers; then V − ENV ≤ +1 point and the right action is to fix the environment (a harness correction, reported as such, applied to every CP-SAT row of every
set), with V kept only for what the fix leaves. If ENV recovers < 50%, V is the recipe step. **Adoption rule:** the cheaper of the two that does not lose accuracy (paired 95%: lower bound of V − ENV > 0 → V).
### ENV result (2026-11-25 10:03 UTC; python poc/wp_env.py easyc nl4c): 0 of 59 recovered (mamoc 0 of 20) — and why that is not a fair competitor
The prefix took effect (78 of the 79 triggered programs use cp_model.INT_MAX; the 79th has an empty domain), but at ±(2^62 − 1) every model is still MODEL_INVALID for another reason: 53 "sum of all variable domains do
not fit on an int64", 25 "possible integer overflow in constraint". The registered ENV value (the largest *accepted single domain*) leaves no room for sums; it was my misreading of what "accepts" means.
## Addendum ENV32 (registered 2026-11-25 10:03 UTC, before running): the same competitor with the library's 32-bit maximum
As ENV, with INT_MAX / INT_MIN = ±cp_model.INT32_MAX (2^31 − 1, a constant of the same library that a program can write; still no tuned number). Same adoption rule: the cheaper of V and ENV32 that does not lose
accuracy (V adopted only if the 95% lower bound of V − ENV32 is > 0; otherwise the zero-token environment fix is the action). Additional check, because a box can hide a better optimum: the number of triggered rows
on which ENV32 and V both print a number and disagree. This is the second competitor after seeing V and ENV, so its result is quoted with that count.
