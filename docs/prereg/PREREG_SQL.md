# Pre-registration SQL: the recipe and its no-label default on text-to-SQL, a task type nothing was chosen on

Written 2026-10-29 01:3x UTC, before any run (the smoke below comes first and is not part of the results). Results go below.

**Why it could change the claim.** After PX / PX2 the project's practical rule is "the no-label default order (short think, full think
only on a visible failure, think again once) on every task; labels add noise", decided on cells the rule was partly built on, with one
known exception (contest code, where one plain think is better). Text-to-SQL is a new task type with its own free check (the query runs
and returns rows), its own missing fact (BIRD's evidence: the domain definitions the question needs) and a known leak (most text-to-SQL
errors are queries that run and return the wrong rows). It tests out of sample (i) whether the recipe saves tokens there, (ii) whether
the no-label default beats a 30-label pilot on an unseen task type, and (iii) a label-free switch built after PX.
**Prior work, and what is new here.** Execution feedback for text-to-SQL is established: execution-guided decoding (Wang et al.
1807.03100: drop candidates that fail to execute), Self-Debugging (2304.05128: repair from execution results on Spider), and an
accuracy–cost study of in-context text-to-SQL pipelines (2608.28432: execution-feedback refinement is the one module that pays on every
backbone at low cost). When to reason: a router trained by SFT + DPO to decide when to think (2607.22622: −14.7% output tokens on BIRD at
matched accuracy); reasoning-trained small models beat non-reasoning ones on BIRD dev (Think2SQL, 2504.15077). The prompt follows
Rajkumar et al. (2204.00498: CREATE TABLE + three rows per table). New: a training-free, check-gated cascade from the same model's
non-thinking query to its thinking, against the check-matched think, a non-thinking repair from the execution result, DART-style
agreement (2606.23181) and self-selection, with tokens counted — and the selection rules (fixed default, 30-label pilot, a
significance-gated pilot, a label-free token switch) scored on a task type none of them was built on.
**Run.** BIRD dev, corrected release 2025-11-06 (`birdsql/bird_sql_dev_20251106`, CC-BY-SA-4.0; 1,534 questions, 11 SQLite databases
from the dev.zip of 2024-06-27); every question; evidence always given (BIRD's standard setting: the fact is part of the input, not an
arm). Prompt (`poc/prep_sql.py`): the database's CREATE TABLE statements, each followed by its first three rows (values cut at 50
characters), the evidence, the question, and "Write one SQLite query that answers the question. Return only the query in a ```sql
block." Models: Qwen3-8B (q8b, 2 × 3090, tensor-parallel), Qwen3-14B-AWQ (q14a), Qwen3.5-9B (q35, its card's general thinking preset,
as LC-1's q35g), seeds 1–3. Per question and seed (`poc/run_sql.py`): **N** = non-thinking query (T 0.7, 2k cap); **S** = the model's
yes / no answer to "would thinking step by step first help you write a correct query?"; **R** = only where N fails the check, one
non-thinking rewrite given N's query and what the check saw (the error, or "the query returned no rows"), 2k cap; **T** = thinking (16k
cap); **SB** = thinking cut at 2,000 tokens (budget forcing), then the query (2k cap). **The free check** (no gold): the extracted query
runs on the database within 30 s without an error and returns at least one row. **Grade**: BIRD's execution accuracy — the set of
result rows equals the gold query's (30 s each; `poc/grade_sql.py`). **Agreement**: two queries' result-row sets are equal.
**Policies** (`poc/analyze_sql.py`; tokens = every call's output tokens; s' = seed s mod 3 + 1): N, T, SB, S; N→R; N→T; N→R→T (T where
R fails too); SB→T; **SB→T→T** (the default order: SB; T where SB fails the check; seed s' T where T fails too); T→T (the check-matched
think); 2N→T (N and seed s' N; N if they agree, else T); N→T|ag (T where N fails the check or disagrees with seed s' N). Utility =
accuracy − 0.5 × ktokens; paired 95% intervals over questions (seed means). Cells: 3 models (the claims), 9 model × seed cells (the
selection rules).
- **SQL-P1 (the check leaks):** ≥ 25% of the N queries that pass the check are wrong, for ≥ 2 of 3 models.
- **SQL-P2 (cheap first saves):** N→T ties or beats T (paired upper bound ≥ 0) at ≤ 90% of its tokens, for ≥ 2 of 3 models.
- **SQL-P3 (the default order saves):** SB→T→T ties or beats T→T at ≤ 90% of its tokens, for ≥ 2 of 3 models.
- **SQL-P4 (repair is the cheap fix):** N→R ties or beats N→T at ≤ 50% of its tokens, for ≥ 2 of 3 models.
- **SQL-P5 (agreement sees the leak):** N→T|ag is ≥ 1.0 point more accurate than N→T, for ≥ 2 of 3 models.
- **SQL-P6 (the no-label default against the pilot):** over the 9 cells, always using SB→T→T has a lower mean regret (λ = 0.5) than the
  argmax 30-label pilot over the whole menu (PX's procedure, 1,000 pilots per cell).
- **SQL-P7 (a label-free switch, built after PX):** on 30 random questions of a cell, keep SB→T→T unless it used more output tokens
  than T→T there, else use T→T (only tokens and check outcomes, no labels); its mean regret is ≤ always SB→T→T's + 0.1.
- Reported, no decision: the significance-gated pilot (PX2's rule), k = 10 / 100, λ = 0 / 2, accuracy by difficulty, the check's power
  and false alarms (against gold result sets that are empty), thinks at the cap, S's yes-rate, raw failures read.
**Expected (stated now, not a rule).** P1 holds (wrong-but-running queries dominate). P2 refuted unless thinking gains little: the
check passes most N queries, so N→T keeps N's leaks. P3 refuted if SQL thinks are short (a 2k cut then barely binds, and the default
pays an extra think on failures: the TC-1 pattern). P4 holds (2608.28432). P5 holds. P6 holds (PX, PX2). P7 holds.
**Decision.** P2 or P3 holds → the recipe's saving extends to text-to-SQL (REPORT, PROJECT §2; PROPOSAL / PROPOSAL_ko). Both refuted →
SQL joins tool calls and instructions as a task type where the check buys accuracy, not tokens (the boundary named: the check's power).
P4 holds and beats P2 → on SQL the visible failure goes to a non-thinking repair first (the word-problem rule, HO-R). P6 → the
no-label default is stated as holding on an unseen task type (or not). P7 holds → the default gets its label-free switch for tasks
where the short think does not save (the contest-code exception, PX), stated as tested once out of sample.
**Smoke (not part of the results).** q35, seed 1, every 30th question (52): the prompt fits, the query is extracted from every arm, the
check and the grade run, gold queries execute within 30 s; fixes to format or extraction only, then the rows are discarded.

*Smoke (2026-10-29 01:5x UTC; q35smoke, seed 1, 52 questions; rows discarded).* Every arm returned a query that the extraction found
(N 78 tokens on average, T 3.1k, max 12.7k, none at the 16k cap; SB cut at 2k on 28 / 52); the check and the grade ran (no gold query
failed; the client's check and the grader's agree on all 52 N rows). One setting is taken from LC-1's q35g, as the Run paragraph says:
Qwen3.5-9B's cut think runs at the card's general preset like its full think (`POC_BUDGET_CARD=1`; the smoke's ran at the harness
sampling). No prediction or rule changes. Full runs: jobs 1273839–1273853 (docs/SLURM_HANDOFF.md).

*Environment note (2026-10-29 03:2x UTC; before any policy is scored).* The container's SQLite (3.49.1, image nlp_project:261021) runs
both the client's check and the grader. It rejects double-quoted string literals (`name = "Ancestor's Chosen"` → "no such column"),
and three gold queries that take 0.1 s on SQLite 3.34.1 (the login node) pass 30 s there. So in Qwen3-8B seed 1, 4 of 1,534
questions are left out as the grader rule says (gold 359: the quoting; 518, 701, 1131: timeouts). The same SQLite also rejects model
queries on these grounds: of 4,875 graded queries, 3 had the quoting error and 12 timed out. The check and the grade see the same
SQLite (they differ on 1 of 1,530 N rows), so the policies are compared under one environment. Accuracy can be up to ~0.3 points
lower than under a SQLite that accepts double quotes. No prediction or rule changes.

## Results SQL-1 (2026-10-29 06:1x UTC; three models, 3 seeds, 1,530 questions each; `python3.11 poc/analyze_sql.py --pilot`)

Per model, seed means over 1,530 questions (4 gold queries fail in the container, environment note), tokens per question:

| model | N | T | SB | N→T | SB→T→T | T→T | N passes / leak / power | N→T − T | SB→T→T − T→T |
|---|---|---|---|---|---|---|---|---|---|
| Qwen3-8B | 46.0% @ 0.07k | 58.1% @ 1.60k | 57.6% @ 1.21k | 52.2% @ 0.60k | 59.5% @ 1.68k | 59.2% @ 1.85k | 81% / 42.9% / 36% | −5.9 [−7.5, −4.2] at 38% | +0.2 [−0.5, +1.0] at 91% |
| Qwen3-14B-AWQ | 49.4% @ 0.08k | 56.7% @ 1.49k | 56.0% @ 1.18k | 53.2% @ 0.45k | 57.3% @ 1.50k | 57.6% @ 1.67k | 85% / 41.8% / 30% | −3.5 [−5.2, −1.8] at 30% | −0.4 [−1.2, +0.4] at 89.7% |
| Qwen3.5-9B | 48.7% @ 0.08k | 57.2% @ 2.83k | 55.8% @ 1.49k | 54.5% @ 0.75k | 58.0% @ 2.19k | 58.8% @ 3.17k | 82% / 40.7% / 35% | −2.7 [−4.3, −1.1] at 27% | −0.7 [−1.5, +0.1] at 69% |

(leak = check-passing N queries that are wrong; power = wrong N queries the check fails; false alarms 0.0–0.1%.)
- **SQL-P1 holds (3 / 3):** 40.7–42.9% of the passing N queries are wrong; the check fails only 30–36% of the wrong ones. The
  thinking arms leak almost as much (T 36.6–38.8%, SB 36.1–38.9%).
- **SQL-P2 refuted (0 / 3):** cheap first is 2.7–5.9 points below one think, at 27–38% of its tokens.
- **SQL-P3 holds (2 / 3):** the default order ties the check-matched think at 69% (Qwen3.5-9B) and 89.7% (Qwen3-14B-AWQ) of its
  tokens; Qwen3-8B ties too (+0.2) but at 91%, just outside the rule.
- **SQL-P4 refuted (0 / 3):** one non-thinking repair from the error recovers 12–21% of the failed queries (R right on 28–58 of
  231–309 per seed) and stays 1.9–3.3 points below N→T.
- **SQL-P5 holds (2 / 3):** agreement with a second non-thinking query adds +2.4 [+1.8, +2.9] (Qwen3-8B) and +3.1 [+2.3, +4.0]
  (Qwen3.5-9B) over N→T (Qwen3-14B-AWQ +0.7), at 152–223% of its tokens, still below one think for Qwen3 (−3.5 / −2.8) and tying it
  for Qwen3.5-9B (+0.4 at 59%).
- **SQL-P6 holds:** over the 9 cells (λ = 0.5) always using SB→T→T loses 0.33 to each cell's best, the 30-label argmax pilot 2.25
  (k = 10 / 100: 4.05 / 0.90); the gated pilot (PX2) 0.35, switching in 1% of draws. Best fixed: T→T 0.26; best per cell SB→T→T 5,
  T→T 3, N→T|ag 1. λ = 0: T→T 0.11, default 0.41; λ = 2: the default is the best fixed policy (0.37).
- **SQL-P7 holds:** the token switch loses 0.34 (≤ 0.33 + 0.1). Here it had little to fix: the default is cheaper than T→T in every
  cell. In-sample on contest code (PX's cells, where the switch was motivated; not a test) it cuts the default's 3.07 to 2.40 (k = 30),
  still above one plain think (1.24) and T→T (1.42): it removes about 40% of the contest-code loss.
- Reported: S answers "yes" on 99.6–100% of questions (S = T plus one or two tokens). Thinks are short (T 1.5–1.6k for Qwen3, 2.8k for
  Qwen3.5-9B; none at the 16k cap); the 2k cut binds on 22–24% (Qwen3) and 50% (Qwen3.5-9B) of questions, which is where the saving
  comes from. By difficulty the default is within 2 points of T→T at every level (simple 68–70%, moderate 53–56%, challenging 26–32%).
- Raw outputs read. N's visible failures (all seeds): 46–49% name a column that does not exist, 23–38% return no rows, 7–21% are
  SQLite usage (unquoted names with spaces, YEAR()). Of 60 random leaks (Qwen3-14B-AWQ, seed 1): 30 return entirely different rows
  (wrong filter value, join or aggregate), 24 a different number of columns (6 of them contain gold's values, e.g. a full name in one
  column for forename and surname in two — false negatives of execution accuracy, as FLEX, 2409.19014, reports for BIRD), 6 differ
  in duplicates, NULLs or ties. Thinking loses a question N gets right on 4.7–7.1% of rows, e.g. `d.A3 = 'East Bohemia'` where the
  value is 'east Bohemia' (N wrote `LIKE 'EAST%'`): the count is 0 and passes the check. Post hoc, not used: 2.4–4.6% of passing
  queries return one row of only 0 / NULL and about 90% of them are wrong; rejecting those would raise the check's power by about 7
  points at < 1% false alarms.
- Related work: the trained think router of 2607.22622 saves 14.7% of output tokens at matched accuracy on BIRD; the training-free
  default here saves 9–31% of the check-matched think's tokens at a tie (paired intervals include 0).
**Decision.** P3 holds → the recipe's saving extends to text-to-SQL through its default order (short think first, full think only
on a failed check, think again once), not through cheap first: the check is too weak (power 30–36%) for N→T. P4 refuted → no
repair-first rule on SQL. P6 holds → the no-label default is stated as holding on an unseen task type (0.33 vs the pilot's 2.25).
P7 holds → the default gets its label-free token switch as tested once out of sample, with the caveat that on SQL it had little to
fix and in-sample it closes only about 40% of the contest-code gap. Recorded in REPORT §5.11, PROJECT §2 / §5, PROPOSAL / PROPOSAL_ko.
*Sensitivity (2026-10-29 06:2x UTC; in-sample, not a decision).* The same switch on the earlier cells (k = 30, λ = 0.5; default →
switch): contest code 3.07 → 2.40, tool calls 0.23 → 0.30, instructions 0.92 → 0.91, PX2's 33 word cells 0.72 → 0.86 (above SQL-P7's
0.1 bound), SQL 0.33 → 0.34; over all 90 cells 0.94 → 0.91. The switch trades word problems for contest code. Deviation from the
Decision line, stated: P7 holds on SQL, but because the same bound fails on PX2's word cells the switch is recorded as an option for
contest-like tasks, not added to the default.

## Addendum SQL-F: the fact on text-to-SQL

Written 2026-10-29 06:0x UTC, after SQL-1's results for Qwen3-14B-AWQ and Qwen3.5-9B (Qwen3-8B's last seed is still being
graded), before any SQL-F run.

**Why it could change the claim.** SQL-1: the free check catches 30–35% of wrong non-thinking queries, so cheap first loses to one
think (SQL-P2 refuted) while the default order saves (SQL-P3). On word problems the recipe's main lever was the missing fact (exact
library usage, or the model's own checked programs for similar problems): it raised the cheap program in 25 of 29 cells. On SQL, 46–49%
of N's visible failures name a column that does not exist, 7–21% are SQLite usage (syntax, functions such as YEAR()), 23–38% return no
rows; and 24 of 60 sampled leaks return other columns than gold (Qwen3-14B-AWQ, seed 1; Results). SQL-F asks whether the fact lever
transfers to a task type with no library, whose domain fact (BIRD's evidence) is already in the prompt, and whether it makes cheap
first a saving there.
**Prior work, and what is new here.** In-domain demonstrations for text-to-SQL: ODIS (Chang & Fosler-Lussier, EMNLP 2023, 2310.06302:
synthetic in-domain examples verified by execution, mixed with out-of-domain gold ones), SAFE-SQL (EMNLP 2025, 2502.11438:
self-generated examples filtered for relevance; unfiltered self-generated examples can hurt), DAIL-SQL (2308.15363: labelled examples
chosen by question and query similarity); SQL-Zero (2609.04697) trains on execution-only self-play. New: the model's own queries for the
other questions of the same database, filtered only by the free check (no labels, no new questions generated), plus a short SQLite card,
given to every arm, so that thinking is given the same fact, with tokens counted.
**Run.** As SQL-1 (questions, models, seeds, sampling, caps, check, grade, policies), with the fact between the schema and the evidence
(`poc/fact_sql.py`): the **card**, three comment lines of SQLite usage (quote names with spaces or symbols in backticks; string values in single
quotes; dates are text, so STRFTIME / SUBSTR, not YEAR() / MONTH(); CAST(x AS REAL) for ratios; return only the columns the question
asks for) — written from SQLite's dialect, but after reading SQL-1's errors, two of which it names — and the **library**: for each
question, the 3 other questions on its database with the highest word overlap (Jaccard) whose SQL-1 N query by the same model at seed
s' passed the check, each as its question and that query (about 320 tokens added at the median, at most about 2.5k). Tags q8bf / q14af /
q35f (SQL_FACT=both; all arms); for attribution, the cheap arm only: q8bc / q14ac / q35c (card only), q8bl / q14al / q35l (library only).
Analysis `poc/analyze_sqlf.py`, paired over the questions graded in both runs.
- **SQL-F1 (the fact raises the cheap query):** N with the fact ≥ N + 2.0 points, for ≥ 2 of 3 models.
- **SQL-F2 (cheap first saves, given the fact):** with the fact, N→T ties or beats T (paired upper bound ≥ 0) at ≤ 90% of its tokens,
  for ≥ 2 of 3 models.
- **SQL-F3 (the fact raises thinking):** T with the fact ≥ T + 1.0 point, for ≥ 2 of 3 models.
- **SQL-F4 (the fact pays in the default order):** SB→T→T with the fact minus without: paired lower bound > 0, for ≥ 2 of 3 models.
- **SQL-F5 (the fact narrows the leak):** the share of check-passing N queries that are wrong drops by ≥ 3 points, for ≥ 2 of 3 models.
- Reported, no decision: card only and library only against N; the other policies with and without the fact; tokens; raw failures
  read (copied example queries; what the remaining leaks return).
**Expected (stated now, not a rule).** F1 holds (the library shows the database's join paths and value formats). F2 refuted (the leak
stays: most wrong-but-running queries are not usage errors). F3 holds, with a smaller gain than N's. F4 holds narrowly or not. F5
refuted, except through the columns line.
**Decision.** F1 and F2 hold → the fact makes cheap first a saving on SQL: the recipe's first step transfers to a task type with no
library (REPORT, PROJECT §2; PROPOSAL / PROPOSAL_ko). F1 holds, F2 refuted → the fact raises the cheap end and the check's power bounds
it (SQL stays a type where cheap first is a trade, stated with the fact given). F1 refuted → the fact lever does not transfer where the
task already supplies the domain fact; "the fact is the main lever" is scoped to tasks with a library or an API. F4 holds → the default
on SQL is stated with the fact.

## Results SQL-F (2026-10-29 16:0x UTC; three models, 3 seeds, 1,530 questions each; `python3.11 poc/analyze_sqlf.py`)

With the fact (card + library) against SQL-1's rows of the same model, seed means, tokens per question; in brackets the paired
difference with its 95% interval:

| model | N | T | SB→T→T | T→T | N passes / leak / power | N→T − T | SB→T→T − T→T | N, card only | N, library only |
|---|---|---|---|---|---|---|---|---|---|
| Qwen3-8B | 48.8% (+2.8 [+0.9, +4.6]) | 56.0% @ 1.42k (−2.1 [−3.5, −0.7]) | 57.2% @ 1.46k (−2.2 [−3.7, −0.8]) | 56.8% @ 1.60k (−2.4 [−3.8, −1.0]) | 81→87% / 42.9→43.7% / 36→26% | −3.9 [−5.4, −2.6] at 28% | +0.4 [−0.3, +1.1] at 91% | −1.4 [−2.7, −0.1] | +2.5 [+0.6, +4.3] |
| Qwen3-14B-AWQ | 52.7% (+3.3 [+1.5, +5.1]) | 55.7% @ 1.26k (−1.0 [−2.4, +0.4]) | 57.2% @ 1.29k (−0.1 [−1.5, +1.4]) | 56.5% @ 1.39k (−1.2 [−2.5, +0.2]) | 85→89% / 41.8→40.9% / 30→23% | −1.2 [−2.7, +0.3] at 24% | +0.7 [−0.1, +1.5] at 92% | −0.4 [−1.5, +0.7] | +3.0 [+1.1, +4.8] |
| Qwen3.5-9B | 52.4% (+3.7 [+2.2, +5.2]) | 59.2% @ 3.25k (+1.9 [+0.6, +3.2]) | 58.9% @ 2.38k (+0.9 [−0.3, +2.0]) | 60.1% @ 3.61k (+1.3 [−0.0, +2.6]) | 82→88% / 40.7→40.2% / 35→26% | −3.2 [−4.5, −1.7] at 20% | −1.2 [−2.0, −0.3] at 66% | −1.8 [−3.0, −0.7] | +3.4 [+2.0, +4.9] |

- **SQL-F1 holds (3 / 3):** the fact raises the non-thinking query by 2.8–3.7 points; the library alone gives it (+2.5 to +3.4), the
  card alone costs 0.4–1.8.
- **SQL-F2 refuted (1 / 3):** with the fact, cheap first still loses to one think with the fact (−3.9 / −1.2 / −3.2 at 20–28% of its
  tokens; only Qwen3-14B-AWQ's interval reaches 0).
- **SQL-F3 refuted (1 / 3):** the fact raises Qwen3.5-9B's think (+1.9) and lowers the Qwen3 thinks (−2.1, −1.0).
- **SQL-F4 refuted (0 / 3):** the default order with the fact minus without: −2.2, −0.1, +0.9, no lower bound above 0.
- **SQL-F5 refuted (0 / 3):** the leak moves by −0.9 to +0.8 points. The fact makes 4–6% more queries run, wrong as often as the
  rest, so the check's power falls from 30–36% to 23–26%: the library turns visible failures into silent ones as often as into right
  queries.
- **Decision (rule above):** F1 holds, F2 refuted: the fact raises the cheap end and the check's power bounds it; text-to-SQL stays a
  type where cheap first is a trade, also with the fact given. F4 refuted: the default on SQL is stated without the fact.
- Expected (stated before): F1 holds, F2 refuted, F3 holds, F4 narrowly or not, F5 refuted. F3 was wrong for the Qwen3 models.
- **Why (post hoc, uses gold; analysis only).** The library is filtered by the same weak check, so 57% (Qwen3) / 61% (Qwen3.5-9B) of
  its queries are right. The fact's effect rises with how many of a question's 3 library queries are right (question-seeds per bin
  567–1,720; paired within the bin):

  | library right | Qwen3-8B T / N | Qwen3-14B-AWQ T / N | Qwen3.5-9B T / N |
  |---|---|---|---|
  | 0 of 3 | −3.9 / +0.0 | −3.3 / −2.4 | −1.4 / −0.5 |
  | 1 of 3 | −5.9 / −0.6 | −3.5 / +2.2 | +0.3 / +1.5 |
  | 2 of 3 | −1.0 / +4.1 | −0.6 / +4.1 | +3.3 / +4.1 |
  | 3 of 3 | +1.1 / +5.7 | +2.3 / +6.5 | +2.9 / +6.6 |

  The bins also sort difficulty (T without the fact 28% → 72%), so this is not causal by itself; the raw outputs agree. Of 8 random
  thinks lost to the fact (Qwen3-8B, seed 1; all pass the check), 3 take a wrong library pattern: a join through `attendance` instead
  of `budget` (the library query for a similar question joins that way), two columns where gold has one (the library query for "the
  atoms' elements that form bond …" returns two), COUNT(*) for "how many … List out the card id" (the library's "how many" query);
  the other 5 are ordinary variance (a dropped filter, an extra column, SUBSTR(date, 5, 2) for the month). Exact copies are rare
  (0.7–1.2% of queries); 9–13% are close to a library query (token Jaccard ≥ 0.8), and those are right more often (61–73% vs 49–59%).
- So a library admitted by a check inherits the check's leak: unverified examples raise the cheap query but cost the Qwen3 thinks
  1–2 points, and pay for thinking only when all three are right. This matches SAFE-SQL (2502.11438: unfiltered self-generated
  examples can hurt; it filters them for relevance) and ODIS (2310.06302: synthetic examples kept only if they execute — the same
  check here, which BIRD shows to be too weak), and differs from Min et al. (2202.12837), where wrong labels in demonstrations barely
  matter for classification: in SQL generation the copied part is the structure (join path, output columns), and a wrong one is wrong.

## Addendum SQL-FA: does the library's precision decide what the fact does? (written 2026-10-29 16:2x UTC, before any SQL-FA row)

**Why it could change the claim.** SQL-F's explanation — the check-admitted library is 57–61% right and the fact's effect rises
with how many of a question's three examples are right — is now a sentence of PROPOSAL, but it rests on bins that also sort
difficulty (T without the fact: 28% in the 0-of-3 bin, 72% in the 3-of-3 bin). If difficulty alone explains the bins, changing which
queries enter the library changes nothing; if precision is the cause, the bins predict each library's effect from its composition.
**Model (from SQL-F only, before any new row).** Effect of the fact (card + library) on arm a for a question whose library has k of 3
right: δ_a(k), SQL-F's per-bin paired effect (Results SQL-F). A library with composition w_k predicts Σ_k w_k δ_a(k). Libraries
(same construction: the 3 most similar other questions on the database, SQL-1's non-thinking queries of seed s' that passed the check),
differing only in which passing queries may enter (`SQL_LIB_ADMIT`, poc/fact_sql.py):
- **agree** (label-free): the query also returns the same rows as SQL-1's short-think query of the same seed, which passed too
  (precision 0.79 / 0.78 for Qwen3-8B / Qwen3-14B-AWQ, against 0.57 for check alone; mean question similarity 0.29 vs 0.32);
- **right** / **wrong** (gold-admitted; analysis-only conditions that set precision to 1 / 0; similarity 0.29 / 0.27).

| model | library | precision | predicted N vs no fact | predicted T vs no fact |
|---|---|---|---|---|
| Qwen3-8B | check (SQL-F, observed) | 0.57 | +2.8 | −2.1 |
| Qwen3-8B | agree | 0.79 | +4.3 | −0.5 |
| Qwen3-8B | right | 1.00 | +5.7 | +1.1 |
| Qwen3-8B | wrong | 0.00 | +0.0 | −3.9 |
| Qwen3-14B-AWQ | check (SQL-F, observed) | 0.57 | +3.3 | −1.0 |
| Qwen3-14B-AWQ | agree | 0.78 | +4.9 | +0.4 |
| Qwen3-14B-AWQ | right | 1.00 | +6.5 | +2.3 |
| Qwen3-14B-AWQ | wrong | 0.00 | −2.4 | −3.3 |

The difficulty-only alternative predicts every library's effect equal to the check library's.
**Prior work.** COSP (2305.14106) builds zero-shot demonstrations from the model's own outputs selected by self-consistency;
SQLPrompt (2311.02883) uses execution-based consistency over mixed prompts to select queries; SAFE-SQL (2502.11438) filters
self-generated examples for relevance; ODIS (2310.06302) keeps examples that execute. None varies the admission rule's precision with
the rest of the library fixed, or gives the same examples to thinking. New: the dose-response in precision, with a prediction fixed
from SQL-F, and a label-free admission (agreement across modes) tested against the check alone, for thinking and non-thinking.
**Run.** Qwen3-8B (TP 2, one job per seed) and Qwen3-14B-AWQ (two shards per seed), the two models whose thinks lost to the fact;
seeds 1–3; SQL-1's questions, sampling, caps and grading; SQL_FACT=both (card + library, as SQL-F's q8bf / q14af, so only the
admission differs); arms N and T only (`SQL_ARMS=cheap,think`); tags q8bfg / q8bfr / q8bfw and q14afg / q14afr / q14afw (shards
p0 / p1 merged). Submitted at low priority behind CV-1 (`bash poc/slurm/submit_sqlfa.sh`). Analysis `python3.11 poc/analyze_sqlfa.py`,
paired over the questions graded in all five conditions (no fact, check, agree, right, wrong).
**Predictions.**
- **SQL-FA1 (wrong examples hurt, right ones help):** right minus wrong library, paired lower bound > 0, for N and for T, in 2 / 2
  models.
- **SQL-FA2 (precision, not difficulty):** T with the right library minus T with the check library, lower bound > 0, in 2 / 2 models
  (predicted +3.2 / +3.3; the difficulty-only alternative predicts 0).
- **SQL-FA3 (the composition model's numbers):** observed effect vs no fact within ±2.0 points of the table, in ≥ 9 of the 12 cells
  (2 models × 3 libraries × N / T).
- **SQL-FA4 (label-free remedy):** T with the agreement library minus T with the check library, pooled over both models (bootstrap
  over model × question), lower bound > 0; and T with the agreement library not below T without the fact (paired upper bound ≥ 0)
  in 2 / 2 models.
- Reported, no decision: tokens; the leak of N with each library; raw thinks lost with the right library and won with the wrong one.
**Expected (stated now, not a rule).** FA1 holds. FA2 holds for T, with a smaller gap than predicted (difficulty explains part of the
bins). FA3 6–9 of 12. FA4 borderline (predicted +1.5, about the width of one model's interval).
**Decision.** FA1 and FA2 hold → "a fact the model builds itself is only as good as the check that admits it" is causal: PROPOSAL
keeps it as tested (REPORT §5.11). FA1 holds, FA2 refuted → wrong examples cost thinking, but SQL-F's loss is mostly difficulty:
PROPOSAL says "wrong examples cost thinking" without "in proportion". FA1 refuted → the sentence is withdrawn from PROPOSAL / PROPOSAL_ko.
FA4 holds → the recipe's SQL entry admits library queries by agreement with the short think (REPORT §5.11, PROJECT; PROPOSAL if
thinking with the agreement library beats thinking without the fact, lower bound > 0, in 2 / 2).

## Results SQL-FA (2026-10-29 22:2x UTC; Qwen3-8B and Qwen3-14B-AWQ, 3 seeds, 1,530 questions in all five conditions; `python3.11 poc/analyze_sqlfa.py`)

Seed means; in brackets the paired difference to no fact with its 95% interval; N's pass rate / leak (share of passing queries that
are wrong) pooled over seeds:

| model | library (precision) | N | T | T tokens | N pass / leak |
|---|---|---|---|---|---|
| Qwen3-8B | none | 46.0% | 58.1% | 1.60k | 80.5 / 42.9% |
| Qwen3-8B | check (0.57) | 48.8% (+2.8 [+0.9, +4.6]) | 56.0% (−2.1 [−3.5, −0.7]) | 1.42k | 86.5 / 43.7% |
| Qwen3-8B | agree (0.79) | 49.1% (+3.1 [+1.3, +4.9]) | 58.1% (+0.0 [−1.3, +1.4]) | 1.41k | 83.4 / 41.1% |
| Qwen3-8B | right (1.00) | 50.4% (+4.4 [+2.5, +6.2]) | 59.0% (+0.9 [−0.3, +2.3]) | 1.43k | 83.7 / 39.8% |
| Qwen3-8B | wrong (0.00) | 44.7% (−1.3 [−3.2, +0.6]) | 54.2% (−3.9 [−5.4, −2.5]) | 1.44k | 84.3 / 47.0% |
| Qwen3-14B-AWQ | none | 49.4% | 56.7% | 1.49k | 84.8 / 41.8% |
| Qwen3-14B-AWQ | check (0.57) | 52.7% (+3.3 [+1.5, +5.1]) | 55.7% (−1.0 [−2.4, +0.4]) | 1.26k | 89.1 / 40.9% |
| Qwen3-14B-AWQ | agree (0.78) | 54.4% (+5.0 [+3.2, +6.8]) | 57.2% (+0.5 [−0.8, +1.8]) | 1.28k | 88.6 / 38.6% |
| Qwen3-14B-AWQ | right (1.00) | 55.1% (+5.7 [+4.0, +7.4]) | 59.6% (+2.9 [+1.6, +4.2]) | 1.28k | 87.2 / 36.8% |
| Qwen3-14B-AWQ | wrong (0.00) | 48.9% (−0.5 [−2.1, +1.2]) | 53.4% (−3.3 [−4.7, −1.9]) | 1.31k | 88.0 / 44.4% |

- **SQL-FA1 holds (2 / 2 for N and for T):** right minus wrong library, N +5.8 [+3.9, +7.5] / +6.2 [+4.4, +7.9], T +4.9 [+3.4, +6.4]
  / +6.2 [+4.7, +7.6].
- **SQL-FA2 holds (2 / 2):** T with the right library minus T with the check library +3.0 [+1.8, +4.3] / +3.9 [+2.7, +5.2]
  (predicted +3.2 / +3.3; the difficulty-only alternative predicts 0).
- **SQL-FA3 holds (12 / 12 cells within ±2.0):** mean absolute error 0.67 points (T cells 0.23, at most 0.6; N cells 1.1, at most 1.9:
  Qwen3-14B-AWQ's wrong library, −0.5 vs −2.4). Qwen3-8B's N gains run 1.2–1.3 points below the prediction for all three libraries.
- **SQL-FA4 holds:** T with the agreement library minus the check library +2.1 [+1.0, +3.2] / +1.5 [+0.5, +2.5], pooled +1.8 [+1.1,
  +2.6]; T with it is not below T without the fact (+0.0 [−1.3, +1.4], +0.5 [−0.8, +1.8]).
- Expected (stated before): FA1 holds; FA2 with a smaller gap than predicted; FA3 6–9 of 12; FA4 borderline. FA2 and FA3 were
  underestimated: the bins' difficulty sorting explains none of SQL-F's effect.
- Reported, no decision. Tokens: with any library the thinks are 10–15% shorter (1.41–1.44k vs 1.60k; 1.26–1.31k vs 1.49k),
  whatever its precision, so the agreement library gives thinking the no-fact accuracy at 88% / 86% of its tokens. The leak of N
  follows the library's precision (right 39.8 / 36.8%, agree 41.1 / 38.6%, check 43.7 / 40.9%, wrong 47.0 / 44.4%).
- Raw thinks (Qwen3-8B, seed 1; 109 lost with the right library, 84 won with the wrong one; 4 random of each). Lost with right
  examples: 3 of 4 copy a structure that is right for the example's question but not for this one — COUNT(*) alone for "state the code
  numbers of the top 3 youngest drivers; how many … among them" (library: three "How many …" queries), MIN(time) on a text column for
  the fastest lap (library: MIN(fastestLapTime)), an added DISTINCT (library: SELECT DISTINCT element …); the fourth takes
  CreationDate from the comment examples onto posts, which has none (a visible failure). Won with wrong examples: 3 of 4 copy a
  structure that is right here although the example is wrong for its own question — ORDER BY … DESC LIMIT 1 for "the patient with the
  highest LDH in the normal range" (the example ranks another column with a wrong range), forename and surname as separate columns
  (the example returns time instead of url), the lowercase watermark pattern for 'boros' (the 'abzan' example lacks DISTINCT); the
  fourth is variance ('Normal' / 'Abnormal' instead of 'Yes' / 'No'). What transfers is the structure; whether the example's own query
  is right is a proxy for whether its structure fits, exact on average and loose per case.
- **Decision (rule above):** FA1 and FA2 hold, so "a fact the model builds itself is only as good as the check that admits it" is
  causal: PROPOSAL keeps it, now as tested (REPORT §5.11). FA4 holds, so the recipe's SQL entry admits library queries by agreement
  with the short think (REPORT §5.11, PROJECT); thinking with that library does not beat thinking without the fact (lower bounds −1.3,
  −0.8), so PROPOSAL states no gain from it.
- Prior work: Yoo et al. (2205.12685) found that ground-truth labels in demonstrations matter more than Min et al. (2202.12837)
  reported, depending on the setup; here, for generation with retrieved similar questions, right vs wrong examples move the think by
  5–6 points, and a model weighting SQL-F's per-precision effects predicts each library within 2 points. COSP (2305.14106) and
  SQLPrompt (2311.02883) select demonstrations by consistency within one mode; agreement across the quick and short-think modes is
  the cross-mode version, measured here against gold-precision endpoints.

## Addendum SQL-PA: another model's quick query as the check (written 2026-10-29 19:4x UTC, before any SQL-PA row)

**Why it could change the claim.** On SQL the cheap-first cascade is a trade because the free check leaks (41–43% of passing
non-thinking queries are wrong), and every stronger check built so far costs about as much as the think it saves (PREREG_CV.md).
**Exploratory (post hoc, on SQL-1's stored dev rows, 2026-10-29; `python3.11 poc/analyze_sqlpa.py --dev`).** Accepting model A's passing
non-thinking query (N) only when another model's N on the same question returns the same rows, else A's T→T:
| A ← peer | accuracy @ tokens | vs T→T accuracy (tokens) | vs SB→T→T utility |
|---|---|---|---|
| Qwen3-8B ← Qwen3.5-9B | 59.7% @ 1.53k | +0.5 [−0.4, +1.3] (83%) | +0.3 [−0.7, +1.4] |
| Qwen3-8B ← Qwen3-14B-AWQ (same generation) | 58.2% @ 1.45k | −1.0 [−2.1, +0.0] (78%) | −1.1 [−2.3, +0.0] |
| Qwen3-14B-AWQ ← Qwen3.5-9B | 58.4% @ 1.35k | +0.8 [−0.1, +1.7] (81%) | +1.2 [+0.1, +2.3] |
| Qwen3-14B-AWQ ← Qwen3-8B (same generation) | 57.5% @ 1.30k | −0.2 [−1.3, +0.9] (78%) | +0.3 [−1.0, +1.5] |
| Qwen3.5-9B ← Qwen3-8B | 60.0% @ 2.31k | +1.2 [+0.3, +2.1] (73%) | +1.9 [+0.8, +2.9] |

(SQL-1: N→T→T is 3.7–6.5 below T→T; the default SB→T→T ties T→T.) The peer's query costs 59–70 tokens; A's own short think, as a check of the
same kind (agreeing with N), keeps about as many wrong queries at 1.1–1.4k tokens.
**Theory.** Per question-seed, A's N is right with p (every right query passes), wrong but passing with w; T→T is right with v and
costs c. The peer agrees with a right query iff it is right too (one right result set): a = P(peer right | A right); with a wrong
passing query iff it is wrong and passing with the same rows: b = P(peer wrong, passing | A wrong, passing) · ρ, ρ = the *error
coincidence* (same rows given both wrong and passing). Against T→T: ΔA = E[p·a·(1 − v)] − E[w·b·v] and ΔK = k_A + E[(p + w)·k_peer]
− E[(p·a + w·b)·c]. The gain term needs a peer that is right where A is right; the loss term needs one that is wrong *differently*.
On dev the gain is the same for every peer (+2.4 to +3.0 points: A right, kept, T→T wrong) and the peer changes only the loss
(−1.8 / −1.9 with the other generation, −3.0 / −3.4 with the same generation), through ρ:
| A | own N, next seed | own SB | same generation | other generation |
|---|---|---|---|---|
| Qwen3-8B | 83% | 45% | 52% | 41% |
| Qwen3-14B-AWQ | 86% | 52% | 52% | 45% |
| Qwen3.5-9B | 60% | 44% | — | 41 / 45% |

A second sample of the same model shares its wrong answer 83–86% of the time (Qwen3), so self-consistency of quick queries is no check
here; models alike in training share wrong answers (Goel et al., 2502.04313: similar models make similar mistakes). Prediction from
this: a peer from another family coincides less still.
**Prior work.** Agreement-based cascading (ABC, 2407.02348) and semantic-agreement cascades (2509.21837) defer to a larger model when
an ensemble of smaller ones disagrees; EllieSQL (2503.22402) routes text-to-SQL by predicted complexity with a trained router;
CHASE-SQL (2410.01943) generates candidates from several paths and selects among them (accuracy, not cost). In this project HO-X
used gpt-oss-20b, a much stronger model, as the second opinion (better to switch models), HO-LF the same model's short think. New:
a peer of equal accuracy as the check before the same model's think, on executed results; which peer works is predicted by error
coincidence (self sample > same generation ≈ own think > other generation > other family); against a trained in-model gate (CV-1).
**Run.** Fresh questions: the 1,338 kept BIRD-train questions outside CV-1's think subset (`$POC_DATA/bird/pa_ids.txt`; 66 databases,
none of them in dev; not used to train CV-1). Qwen3-8B (TP 2), Qwen3-14B-AWQ and Qwen3.5-9B (two shards each), all SQL-1 arms, SQL-1's
prompts, sampling, caps and grading, seeds 1–3 (tags q8bpa, q14apa, q35pa). Nemotron-3-Nano-30B-A3B (another family; 4 × 3090,
TP 4, its non-thinking mode) runs the cheap arm only, on the fresh questions (n3npa) and on dev (n3n; exploratory, not part of a
decision). Peers fixed now: Qwen3-8B and Qwen3-14B-AWQ ← Qwen3.5-9B, Qwen3.5-9B ← Qwen3-8B. Tokens include the peer's. Analysis
`python3.11 poc/analyze_sqlpa.py` (`bash poc/slurm/submit_sqlpa.sh`; grading `SQL_SPLIT=train $P poc/grade_sql.py <tag>`).
**Predictions** (fresh questions, paired 95% intervals over questions, seed means).
- **SQL-PA1 (a saving against one fixed order):** with its peer, accuracy vs A's T→T upper bound ≥ 0 at ≤ 90% of T→T's tokens, in
  ≥ 2 of 3 models.
- **SQL-PA2 (beats the no-label default):** utility (λ = 0.5) vs A's SB→T→T, lower bound > 0, in ≥ 2 of 3 models.
- **SQL-PA3 (error coincidence orders the checks):** for Qwen3-8B and Qwen3-14B-AWQ, ρ(own N, next seed) − ρ(own SB) and ρ(same
  generation) − ρ(other generation), bootstrap over questions, lower bound > 0: 4 of 4.
- **SQL-PA4 (another family):** ρ(Nemotron) − ρ(the fixed peer), upper bound < 0, in ≥ 2 of 3 models.
- Reported, no decision: Nemotron as the peer in the cascade; the gain / loss decomposition; raw rows of wrong queries both models
  share (what kind of mistake two models make alike).
**Expected (stated now, not a rule).** PA1 holds (2–3 of 3; tokens 75–85%). PA2 2 of 3, the dev margins shrinking toward zero
(selection). PA3 holds. PA4 1–2 of 3: Nemotron coincides less but may also be right less often (smaller a).
**Decision.** PA1 and PA2 hold → the claim changes on SQL: with an equal model's quick query as the check, cheap first is a
label-free saving (PROJECT §2, REPORT §5.11, PROPOSAL / PROPOSAL_ko); the recipe's check list gains "an equal model's quick answer
where answers are exact and short"; next, the same check on stored word-problem / contest rows of equal-accuracy model pairs (offline,
pre-registered then). PA1 holds, PA2 refuted → a saving against T→T, not better than the default: reported as an option. PA1 refuted →
the dev result was selection: SQL stays a trade. PA3 holds → recorded as the mechanism that orders every check tried (HO-LF, HO-X,
SQL-FA's agreement library, CV-1's gate): a check is worth what it does not share with the generator's wrong answers.

## Results SQL-PA (2026-10-29 22:5x UTC; fresh BIRD-train questions, 1,337–1,338 per model, 3 seeds; `python3.11 poc/analyze_sqlpa.py`; PA4 waits for Nemotron's rows)

| A ← peer | T→T | SB→T→T | N→T→T | N→peer→T→T | vs T→T accuracy (tokens) | vs SB→T→T utility |
|---|---|---|---|---|---|---|
| Qwen3-8B ← Qwen3.5-9B | 59.5% @ 1.44k | 59.8% @ 1.36k | 56.1% @ 0.35k | 61.2% @ 0.99k | +1.6 [+0.7, +2.6] (69%) | +1.5 [+0.3, +2.7] |
| Qwen3-8B ← Qwen3-14B-AWQ (same generation) | | | | 59.8% @ 0.90k | +0.3 [−0.7, +1.5] (63%) | +0.3 [−1.0, +1.6] |
| Qwen3-14B-AWQ ← Qwen3.5-9B | 59.9% @ 1.30k | 60.1% @ 1.20k | 58.2% @ 0.27k | 60.9% @ 0.82k | +1.0 [+0.1, +1.9] (63%) | +1.0 [−0.2, +2.1] |
| Qwen3-14B-AWQ ← Qwen3-8B (same generation) | | | | 59.9% @ 0.80k | +0.0 [−1.0, +1.1] (62%) | +0.0 [−1.2, +1.2] |
| Qwen3.5-9B ← Qwen3-8B | 61.1% @ 2.48k | 61.4% @ 1.67k | 60.5% @ 0.61k | 61.6% @ 1.57k | +0.5 [−0.2, +1.3] (63%) | +0.2 [−0.8, +1.2] |

Error coincidence (same rows among both-wrong passing pairs; n pairs 882–1,376):

| A | own N, next seed | own SB | Qwen3-8B N | Qwen3-14B-AWQ N | Qwen3.5-9B N |
|---|---|---|---|---|---|
| Qwen3-8B | 87% | 60% | — | 62% | 52% |
| Qwen3-14B-AWQ | 90% | 63% | 62% | — | 59% |
| Qwen3.5-9B | 75% | 63% | 52% | 59% | — |

- **SQL-PA1 holds (3 / 3):** with its peer, cheap first is not below T→T in any model (+0.5 to +1.6) at 63–69% of its tokens. On
  SQL-1's dev rows the same cascade without a peer was 3.7–6.5 points below T→T.
- **SQL-PA2 refuted (1 / 3):** utility vs SB→T→T +1.5 [+0.3, +2.7] (Qwen3-8B), +1.0 [−0.2, +2.1], +0.2 [−0.8, +1.2]. The cascade is
  more accurate and cheaper than the default in all three (73%, 68%, 94% of its tokens), significantly only for Qwen3-8B.
- **SQL-PA3 refuted (3 / 4):** own N next seed − own SB +27.8 [+23.5, +32.3] / +27.3 [+23.2, +31.5]; same − other generation +10.4
  [+5.7, +15.0] (Qwen3-8B) but +3.0 [−1.9, +8.1] (Qwen3-14B-AWQ). Self-consistency is no check (87–90% of wrong answers repeated);
  the generation ordering holds for one of two models, and with a same-generation peer the cascade also ties T→T here (+0.3, +0.0 at
  62–63%), unlike on dev (−1.0, −0.2).
- Gain / loss against T→T (A's query right and kept where T→T is wrong / wrong and kept where T→T is right): +2.9 / −1.3, +2.8 /
  −1.8, +2.1 / −1.5 points; the peer agrees on 55–60% of question-seeds (dev: 45–48%).
- Raw shared wrong queries (Qwen3-8B and Qwen3.5-9B return the same wrong rows, seed 1: 152 questions; 6 random read): all 6 are
  label or evidence noise, not shared reasoning errors — gold 'Name = PHL' where the evidence says CountryCode = 'PHL' (both models
  follow the evidence); gold adds LIMIT 1 to "sort the listing"; gold adds an unasked s_acctbal < 0 filter; gold counts joined rows
  instead of recipes; gold's 'rotavirus  monovalent' has a double space the evidence lacks; "which book … list these books" where gold
  returns titles only and both models add the royalty column. BIRD's train labels are noisy (Wretblad et al., 2402.12243), so
  measured coincidence here includes answers that are right and graded wrong: on train it is higher than on dev (other generation
  52–59% vs 41–45%), and the cascade's true loss is smaller than measured.
- Expected (stated before): PA1 holds with tokens 75–85% (observed 63–69%: more agreement on train), PA2 2 of 3 (1 of 3), PA3 holds
  (3 of 4).
- **Decision (rule above):** PA1 holds, PA2 refuted → with an equal model's quick query as the check, cheap first is a saving against
  the check-matched think on SQL, but not significantly better than the no-label default: reported as an option (REPORT §5.11,
  PROJECT); SQL's default stays SB→T→T, and the word-problem / contest test tied to PA2 is not run as that rule's next step.
- **Exploratory (post hoc; chosen after seeing these rows, so not a result):** sending a disagreement to the default instead of to
  T→T (N → peer agrees → answer, else SB→T→T) beats SB→T→T in utility for all three models on these questions (+1.7 [+0.8, +2.7],
  +1.2 [+0.3, +2.2], +0.9 [+0.1, +1.6], at 64–70% of its tokens, accuracy ≥ T→T) and in 2 of 3 on dev (+0.6 [−0.3, +1.4], +1.0
  [+0.1, +1.9], +1.2 [+0.4, +2.1]). Tested out of sample in addendum HO-PA below.
- Prior work: Kim et al. (2506.07962) measure across 350+ models that two models agree on 60% of the items where both err, more with a
  shared architecture or provider; here, on executed results, the same structure appears (same generation 52–62%, other 41–59%), and
  a second sample of the same model repeats 75–90% of its wrong answers, which is why DART-style self-agreement (2606.23181) cannot
  check Qwen3's quick queries.

- **SQL-PA4 refuted (0 / 3; 2026-10-29 23:3x UTC, Nemotron's rows graded):** coincidence with Nemotron-3-Nano's quick query minus with the fixed
  peer −2.6 [−6.6, +1.8], −4.0 [−8.6, +0.3], +0.7 [−3.9, +5.2] (Nemotron 49 / 55 / 52%). Another family repeats about as many wrong
  answers as another Qwen generation here, while being right less often (N 45.1% vs 51.4–55.7% on these questions; dev 40.4%): as the
  peer it ties T→T at 68–73% of its tokens and ties the default (utility +0.0, +0.0, −0.3). Expected was 1–2 of 3.

## Addendum HO-PA: the peer check, then the default, on word problems and tool calls (written 2026-10-29 22:5x UTC, offline, before computing any HO-PA policy)

**Why it could change the claim.** SQL-PA made cheap first a saving against T→T with a peer's quick answer as the check, but not
better than the default SB→T→T. Sending a disagreement to the default instead of to T→T beat SB→T→T in all three models on SQL —
chosen after seeing those rows, so it needs data it was not chosen on. The project's main claim is that, against the check-matched
think, cheap first is a trade and the best no-label order starts with a short think (PROJECT §2; HO-CM, HO-P4); if a peer's cheap
answer lets the cheap program through only where it is right, that order changes on the task types where it was established.
**What is already known (seen before; no HO-PA policy computed).** On these cells (HO-CM's rows) T→T costs 7–40k tokens and SB→T→T
5–32k, the cheap program with the library 0.4–3k; the cheap program with the fact is 4–20 points below T→T on BWOR / LogiOR /
OptMATH for the leaky models because its free check lets wrong programs through. The same model's quick and short-think programs
agreeing are right 78% of the time on word problems, disagreeing 16% (HO-CC). Cheap accuracies of the four models (OptiBench third
/ BWOR / LogiOR / OptMATH): Qwen3-8B 50.5 / 15.4 / 15.6 / 14.3, Qwen3-14B-AWQ 57.4 / 24.4 / 22.1 / 10.0, Qwen3.5-9B 61.1 / 28.0 / 25.7 /
21.7, Nemotron-3-Nano 52.6 / 15.9 / 15.9 / 9.7. Tool calls: N 76.6 / 70.7 / 68.5%. 
**Theory (SQL-PA's).** Against the default D = SB→T→T, accepting A's passing cheap answer when the peer's agrees changes accuracy by
E[p·a·(1 − v_D)] − E[w·b·v_D] (p, w: A right / wrong and passing; a, b: the peer agrees given each; v_D the default's accuracy on the
item) and tokens by k_A + E[(p + w)·k_peer] − E[(p·a + w·b)·c_D]. Where the default is expensive (word problems: c_D 5–32k) every
accepted item saves several k, so at λ = 0.5 the policy gains utility unless the loss term exceeds the gain term by more than the
saving; on tool calls c_D is small and the accuracy terms decide.
**Policies** (poc/analyze_hopa.py; every row stored; peers fixed now, as SQL-PA: Qwen3-8B and Qwen3-14B-AWQ ← Qwen3.5-9B, Qwen3.5-9B
← Qwen3-8B, Nemotron-3-Nano ← Qwen3.5-9B): N→peer→T→T and N→peer→SB→T→T (a failed check or a disagreement goes to T→T / to
SB→T→T); also reported: the same with the same generation, with Nemotron (Qwen models, word problems), and with the model's own
next-seed cheap answer. Word problems: cheap = the library program (formx), think = thinking with the library (formxt), short think =
formxtb2000; check = runs and prints a value; same answer = within the grader's tolerance (HO-X); OptiBench's 202-item third, BWOR 82,
LogiOR 92, OptMATH 100. Tool calls (BFCL, non-live / live, 3 models): cheap N, think T, short think SB; check = schema validation; same
answer = the same canonical calls. 3 seeds; tokens include the peer's; utility = accuracy − 0.5 × ktokens.
**Predictions** (paired 95% intervals; per model pooled over its cells, items weighted equally; word problems 4 models, tool calls 3).
- **HO-PA1 (saving against the check-matched think):** N→peer→T→T accuracy vs T→T upper bound ≥ 0 at ≤ 90% of T→T's tokens: word
  problems ≥ 3 of 4 models; tool calls ≥ 2 of 3.
- **HO-PA2 (better than the no-label default):** N→peer→SB→T→T utility vs SB→T→T lower bound > 0 and accuracy vs SB→T→T lower bound
  > −2.0 points (non-inferiority): word problems ≥ 3 of 4 models; tool calls ≥ 2 of 3.
- **HO-PA3 (self-agreement is the weakest check):** error coincidence of the model's own next-seed cheap answer minus its peer's,
  lower bound > 0, in every model (4 + 3).
- Reported, no decision: per-cell results (cells where N→peer→SB→T→T is above / below SB→T→T); same-generation / Nemotron /
  own-resample variants; error coincidence of the own short think; raw shared wrong programs.
**Expected (stated now, not a rule).** HO-PA1 2 of 4 on word problems (ties on OptiBench, losses on BWOR / LogiOR where wrong
formulations are shared), 2–3 of 3 on tool calls. HO-PA2 3 of 4 on word problems (the token saving dominates at λ = 0.5; the
non-inferiority bound may fail on LogiOR-heavy models), 1–2 of 3 on tool calls. HO-PA3 holds.
**Decision.** HO-PA2 holds on word problems (≥ 3 of 4) → the no-label default on word problems becomes the cheap program checked by
a served peer, then the short-think order (PROJECT §2, REPORT, PROPOSAL / PROPOSAL_ko), and the same policy is pre-registered on fresh
SQL questions (where it was chosen post hoc) before it becomes SQL's default. HO-PA2 holds on tool calls (≥ 2 of 3) → the same for
tool calls. HO-PA1 holds but HO-PA2 does not → the peer check is reported as a saving against T→T across task types that does not
improve the default (REPORT). Neither → the peer check is a SQL observation; the error-coincidence tables say why. HO-PA3 holds →
recorded with SQL-PA: a second sample of the same model is the weakest check on every type.

## Results HO-PA (2026-10-29 23:0x UTC; `python3.11 poc/analyze_hopa.py`, output results/hopa.txt)

Two fixes to the script before the numbers below, neither changing a pre-registered quantity: the paired utility used accuracy as a
fraction with the token price in points (100 × too heavy; the first run printed utility differences of −10 to −30 on word
problems), and HO-PA2's accuracy non-inferiority clause had not been coded. Both seen in a first run, corrected, then rerun.

Per model, pooled over its cells (paired 95% intervals over items, seed means):

| type | A ← peer | N→peer→T→T vs T→T accuracy (tokens) | N→peer→SB→T→T vs SB→T→T utility | its accuracy | its tokens |
|---|---|---|---|---|---|
| word problems (476 items) | Qwen3-8B ← Qwen3.5-9B | +0.1 [−0.8, +0.9] (95%) | +0.0 [−0.8, +0.8] | +0.2 [−0.6, +1.0] | 104% |
| | Qwen3-14B-AWQ ← Qwen3.5-9B | +0.2 [−0.7, +1.1] (96%) | +0.0 [−0.9, +1.0] | +0.2 [−0.7, +1.1] | 104% |
| | Qwen3.5-9B ← Qwen3-8B | −0.1 [−1.1, +0.9] (88%) | +0.1 [−0.8, +1.0] | +0.2 [−0.6, +1.1] | 101% |
| | Nemotron-3-Nano ← Qwen3.5-9B | −0.6 [−1.7, +0.6] (98%) | −0.7 [−1.6, +0.3] | −0.4 [−1.3, +0.6] | 105% |
| tool calls (3,482 items) | Qwen3-8B ← Qwen3.5-9B | +0.8 [+0.4, +1.3] (73%) | +0.9 [+0.5, +1.3] | +0.8 [+0.4, +1.2] | 73% |
| | Qwen3-14B-AWQ ← Qwen3.5-9B | −0.3 [−0.7, +0.2] (76%) | −0.3 [−0.8, +0.1] | −0.4 [−0.8, +0.1] | 77% |
| | Qwen3.5-9B ← Qwen3-8B | +3.4 [+2.9, +4.0] (67%) | +2.0 [+1.5, +2.5] | +1.9 [+1.4, +2.5] | 71% |

Per cell (N→peer→SB→T→T vs SB→T→T utility, at its share of SB→T→T's tokens): OptiBench +0.4 to +1.0 at 87–92% (no interval above
0); BWOR −0.9 to −2.6, LogiOR −1.3 to +0.7, OptMATH −1.4 to +1.8, all at 104–112% (losses in BWOR Qwen3.5-9B, LogiOR Qwen3-8B and
Qwen3.5-9B); tool calls non-live +0.1 / −0.6 / +2.8, live +1.3 / −0.2 / +1.5 (3 of 6 above 0, none below).

Error coincidence (same answer among both-wrong passing pairs, pooled over cells): word problems — own next-seed cheap 75 / 75 / 79
/ 59%, own short think 57 / 63 / 73 / 59%, another model 56–67%; tool calls — own next-seed 80 / 79 / 53%, own short think 46 / 48 /
53%, another model 33–39%.

- **HO-PA1:** word problems 1 of 4 (refuted; only Qwen3.5-9B under 90% of the tokens); tool calls 3 of 3 (holds).
- **HO-PA2:** word problems 0 of 4 (refuted); tool calls 2 of 3 (holds: Qwen3-8B, Qwen3.5-9B; Qwen3-14B-AWQ −0.3 [−0.8, +0.1]).
- **HO-PA3:** 6 of 7 (refuted as stated): every Qwen model's own resample coincides more than its peer (+8.0 to +47.6), Nemotron's does
  not (−2.7 [−8.9, +3.9]: its two cheap samples differ as much as two models do).
- Why the word problems give nothing (theory above, with these cells' numbers): the default is long (5–31k), but the cheap program and
  the peer's cost 1–6k together, and on BWOR / LogiOR / OptMATH they pass and agree on too few items for the saving to cover them
  (tokens 104–112% of the default); on OptiBench, where they agree often, the policy is at 87–92% of the default's tokens with the
  same accuracy. And different models' wrong programs coincide 56–67% of the time (tool calls 33–39%), so agreement keeps many wrong
  answers. Of 6 random shared wrong answers (Qwen3-8B and Qwen3.5-9B, seed 1, 71 cases), 3–4 are gold problems, not shared mistakes:
  two copies of the fire-station problem with gold 0 stations, an "LP" whose gold is the integer optimum (both models print the LP
  value 47.78; gold 50), a bakery problem whose gold (7.575) is not the stated objective's scale; two OptMATH ones are unclear.
- Expected (stated before): HO-PA1 2 of 4 / 2–3 of 3 (1 / 3); HO-PA2 3 of 4 / 1–2 of 3 (0 / 2). The word-problem expectation was
  wrong: it assumed the token saving would dominate, and the cheap programs' own cost was left out.
- **Decision (rule above):** on word problems neither holds → no change there. On tool calls HO-PA2 holds → the no-label default on
  tool calls becomes the cheap answer checked by a served peer's cheap answer, then the short-think order (N → the peer makes the same
  calls → answer, else SB→T→T; PROJECT §2, REPORT §5.9, PROPOSAL / PROPOSAL_ko). The word-problem condition that would have sent the
  policy to a fresh SQL test did not hold; SQL keeps SB→T→T as its default with the peer check as an option (SQL-PA).
- Prior work: DART (2606.23181) uses two cheap answers of the same model; on tool calls a second sample of Qwen3 repeats 79–80% of its
  wrong calls, another Qwen generation 33–39%, which is why the peer pays where self-agreement did not (TC-1). ABC (2407.02348) defers
  when an ensemble of smaller models disagrees; here the ensemble is one equal model and the deferral goes to the same model's
  short-think order, and the theory says where it pays: short answers, low cross-model coincidence, an escalation not much longer
  than the two cheap answers' overhead covers.

## Addendum SQL-DV: where does a check's independence come from — the same model seen differently, or another model? (written 2026-10-29 23:1x UTC, before any SQL-DV row)

**Why it could change the claim.** SQL-PA and HO-PA place the peer check: it pays where answers are short and two models' wrong
answers rarely coincide, and on tool calls it is now the no-label default — but it needs a second model served next to the first.
The theory says only the coincidence of wrong answers (and the check's cost) matters, not where the second answer comes from. If the
same model, shown the question differently, coincides with itself as little as another model does, no second model is needed; if
only another model does, the recipe must say how small it can be and from which family.
**What is known.** A second sample of the same model repeats 75–90% of its wrong answers (Qwen3, SQL / tool calls / word problems);
the model's own 2k-token short think 46–63%; another Qwen generation 33–62%. Kim et al. (2506.07962): errors correlate more within
an architecture or provider and among more accurate models. MCS-SQL (2405.07467) diversifies candidates with several prompts
(including the schema's table order); mixture-of-thought cascades (2310.03094) take agreement between two representations of the
same weak model as the signal to escalate. Neither measures how much a given variation decorrelates wrong answers, or compares it
with a second model as the check of a cascade.
**Run** (all quick answers only, `SQL_ARMS=quick` / `TC_ARMS=quick`: the non-thinking answer, 2k cap, temperature 0.7, SQL-1's /
TC-1's per-item seeds 1–3; BIRD dev 1,534 questions and BFCL 3,482 items). Views of each A (Qwen3-8B, Qwen3-14B-AWQ, Qwen3.5-9B):
**s** = the schema's tables / the function docs in a per-item random order (`SQL_VIEW` / `TC_VIEW=shuffle`; a no-op on the 1,623 tool
items with one function); **p** = a one-line plan before the answer (SQL: `-- plan: <tables> -> <output columns>` inside the query
block; tool calls: `# plan: …`, removed before decoding; `=plan`). Other models, plain prompt: Llama-3.1-8B-Instruct (another family,
same size), Llama-3.2-3B-Instruct (another family, small), Qwen3-4B (Qwen3, small). Tags q8bvs / q8bvp, q14avs / q14avp, q35vs /
q35vp, l8, l3, q4b; graded with grade_sql.py / grade_tc.py. Analysis `python3.11 poc/analyze_dv.py` (written and dry-run on the
existing tags before any SQL-DV row): per A and check X, X's error coincidence with A and the cascade N → X agrees → A's answer, else
A's SB→T→T (X's tokens counted), against SB→T→T and against the fixed peer's cascade (SQL-PA's peers).
**Predictions** (paired 95% intervals over items; coincidence differences bootstrapped over items).
- **SQL-DV1 (permuting the input does not decorrelate):** coincidence of A's next-seed answer minus view s, upper bound < 15 points,
  for the two Qwen3 models on both types (4 of 4).
- **SQL-DV2 (a plan line decorrelates partly):** coincidence of A's next-seed answer minus view p lower bound > 0, and view p minus the
  fixed peer lower bound > 0, for the two Qwen3 models on both types (both differences, ≥ 3 of 4).
- **SQL-DV3 (does the same model suffice?):** view p's cascade minus the peer's cascade, utility lower bound > −0.5 (non-inferior),
  in ≥ 2 of 3 models on tool calls.
- **SQL-DV4 (does a small model of another family suffice?):** Llama-3.2-3B's cascade minus the peer's cascade, utility lower bound
  > −0.5, in ≥ 2 of 3 models on tool calls.
- **SQL-DV5 (family over size):** coincidence with Qwen3-4B minus with Llama-3.2-3B, lower bound > 0, for the two Qwen3 models on
  both types (4 of 4).
- Reported, no decision: everything on SQL dev (where the peer check is an option) and for Qwen3.5-9B; Llama-3.1-8B; accuracy and
  tokens of each quick answer; raw shared wrong answers of the closest self-view.
**Expected (stated now, not a rule).** DV1 holds; DV2 holds (plan between resample and peer); DV3 refuted (the same model stays too
close to itself); DV4 1–2 of 3 (a 3B model agrees with right answers less often, so fewer are accepted); DV5 holds.
**Decision.** DV3 holds → the tool-call default needs no second model: its check becomes the model's own plan-view quick answer
(PROJECT, REPORT §5.9, PROPOSAL / PROPOSAL_ko). DV3 refuted, DV4 holds → the second model can be a small one from another family,
stated in the recipe (same places). Both refuted → the check needs an equal model, stated as the peer check's cost. DV1 and DV2 →
REPORT, with SQL-PA's coincidence table (what decorrelates: other training > other mode > other wording > another sample). DV5 holds →
the recipe picks the peer from another family before a larger one of the same family.

### Results SQL-DV (written 2026-10-30 02:3x UTC)
All 12 runs complete (per tag: BIRD dev 1,534 × 3 seeds, BFCL 3,482 × 3 seeds); `python3.11 poc/analyze_dv.py` (results/dv.txt, not
committed). Utility differences are against the fixed peer's cascade; paired 95% intervals over items.
- **SQL-DV1 (permuting the input does not decorrelate): holds 4 / 4 as pre-registered, not credited.** Own next seed − view s: SQL
  +11.2 [+7.9, +14.4], +11.2 [+8.3, +14.1]; tool calls +1.6 [−1.5, +4.6], −4.2 [−6.9, −1.3]. Every run uses the same per-item sampling
  seed (seed × 1000 + crc32(id) mod 997), so the shuffled view at A's own seed reuses A's random draws: its text equals A's 37–44% of
  the time on SQL (31–38% at A's next seed) and 85–87% on tool calls (78–79%); Qwen3.5-9B 39% vs 19% and 79% vs 46%. On the 47% of
  tool items with one function the shuffle is a no-op, so there the view is A's answer. For the plan view and across models with the
  same tokenizer (Qwen3-4B, Qwen3-14B-AWQ against Qwen3-8B) the identical-text rate is the same at the own and the next seed (within
  0.6 points), so DV2–DV5 and SQL-PA's / HO-PA's cross-model numbers are unaffected. Post hoc, every check at A's next seed
  (`--next`): SQL +14.4 [+11.6, +17.3], +14.7 [+12.2, +17.5]; tool calls +11.0 [+8.7, +13.4], +9.1 [+7.3, +11.0] (2 / 4, refuted);
  tool items with ≥ 2 functions (`--multi --next`) +18.6 [+14.9, +22.3], +18.2 [+15.1, +21.4]. A shuffle removes 9–19 points of the
  resample's 79–86% coincidence and leaves 63–71% (Qwen3).
- **SQL-DV2 (a plan line decorrelates partly): holds 4 / 4** (both differences; the same with `--next`). Own next seed − view p: SQL
  +34.4 [+30.3, +38.7], +29.6 [+25.8, +33.5]; tool calls +28.3 [+24.7, +31.9], +32.0 [+28.9, +35.2]. View p − peer: SQL +8.0 [+2.9,
  +12.8], +11.2 [+6.6, +15.8]; tool calls +19.3 [+15.2, +23.6], +12.9 [+9.2, +16.6].
- **SQL-DV3 (the same model suffices): refuted, 0 / 3.** View p's cascade − the peer's on tool calls: −1.6 [−2.1, −1.1] (Qwen3-8B),
  −2.2 [−2.8, −1.6] (Qwen3-14B-AWQ), −0.1 [−0.6, +0.3] (Qwen3.5-9B). SQL (reported): −1.7, −1.5, −0.3 [−1.1, +0.4].
- **SQL-DV4 (a small model of another family suffices): refuted, 0 / 3.** Llama-3.2-3B − peer on tool calls: −1.0 [−1.4, −0.6],
  −0.3 [−0.7, +0.1], −0.9 [−1.3, −0.6]. SQL: −0.3 [−1.0, +0.5], −1.0 [−1.8, −0.2], −0.9 [−1.7, −0.1].
- **SQL-DV5 (family over size): holds 4 / 4.** Coincidence with Qwen3-4B − with Llama-3.2-3B: SQL +18.1 [+13.1, +23.2], +12.6 [+7.0,
  +18.3]; tool calls +12.2 [+8.4, +16.2], +10.9 [+7.5, +14.4] (the same with `--next`).
- **Reported.** Error coincidence at independent seeds, SQL / tool calls (Qwen3-8B, Qwen3-14B-AWQ, Qwen3.5-9B): own resample 83 / 86 /
  60% and 80 / 79 / 53%; shuffle 69 / 71 / 52% and 69 / 70 / 51%; plan 49 / 56 / 38% and 52 / 47 / 48%; Qwen3-4B 46 / 47 / 40% and 41 /
  35 / 32%; the fixed peer 41 / 45 / 41% and 33 / 34 / 33%; Llama-3.2-3B 29 / 33 / 32% and 30 / 24 / 27%; Llama-3.1-8B 35 / 34 / 35% and
  25 / 23 / 26%. Llama-3.1-8B (another family, same size) ties the peer as the check: tool calls −0.2 [−0.6, +0.1], +0.3 [−0.1,
  +0.7], −0.4 [−0.7, +0.0]; SQL +0.0, −0.5, −0.5 (all intervals include 0). Quick-answer accuracy: Qwen3.5-9B with the plan line
  makes 79.5% right tool calls against 68.5% plain (of the 554 calls it fixes at seed 1, 258 are irrelevance items where the plan
  concludes no function fits, many others stop copying the prompt's `func_name=` template literally); on SQL the plan line lowers
  every model's quick query (−3 to −7 points); the Qwen3 models' tool calls −1 to −8.
- **Theory check (post hoc, the existing ΔA / ΔK model).** A check X enters the cascade only through its operating point —
  r = P(X agrees | A's passing answer is right), e = P(X agrees | it is wrong) — and its tokens. If acceptance is independent of the
  default's outcome given A's correctness, the gain over SB→T→T is linear in (r, e) with coefficients from A's own rows alone. Over
  the 42 cascades (7 checks × 3 models × 2 types) it predicts the measured gain within 0.66 points on average (tool calls ≤ 0.9; SQL
  overpredicts by up to 1.8: there the check accepts easier items, where the default is right anyway). The peer sits at r 72–83%,
  e 18–28%; the plan view at r 70–85%, e 26–44% (accepts too many wrong answers); Llama-3.2-3B at r 44–67%, e 12–21% (accepts too few
  right ones: it is right 26% / 59% of the time); iso-utility slope dr/de 1.3–4.9.
- **Raw shared wrong answers of the plan view** (Qwen3-8B, SQL, seed 1: 185 of 381 both-wrong passing pairs return the same rows): the
  same reading of the question, which the plan line restates instead of re-examining (1264: "blood clots in veins" as Thrombosis = 1
  although the evidence says APS; 665: per-month counts for "average monthly number"), and the same output shape (1351, 68: extra
  columns under BIRD's exact match).
- **Related work (IDs checked).** Kim et al. 2506.07962 (errors correlate more within a provider / architecture and among more accurate
  models) — DV5 and the peer's position agree. MCS-SQL 2405.07467 shuffles the schema for candidate diversity; here a shuffle removes
  9–19 points of a model's self-coincidence and leaves it far above another model's. The Gumbel-max structural view of sampling
  (Chatzi et al. 2409.17027; Ravfogel et al. 2411.07180) is the mechanism of the DV1 confound: a fixed seed fixes the noise, so a
  slightly changed prompt yields a counterfactual of the same sample, not an independent one.
- **Decision.** DV3 and DV4 refuted → the check needs an equal model: the peer check's cost is a second model of about the same
  accuracy served next to the first (PROJECT, REPORT §5.9, PROPOSAL / PROPOSAL_ko). DV5 holds → the recipe takes the peer from another
  family before a larger one of the same family (Llama-3.1-8B ties the Qwen3.5 peer). DV1 (not credited; refuted at independent
  seeds) and DV2 → REPORT: what decorrelates wrong answers — another model (23–47%) > the model's plan view (38–56%) > its shuffled
  input (51–71%) > another sample (53–86%). Method rule for every agreement check: never reuse the generator's sampling seed.

## Addendum SQL-AND: two checks from different families (written 2026-10-30 02:3x UTC, offline on stored rows, before any joint agreement is computed)

**Why it could change the claim.** SQL-DV reduced a check to its operating point: r = P(it agrees | A's passing answer is right),
e = P(it agrees | the answer is wrong), and its tokens; the gain over SB→T→T is linear in (r, e) (42 cascades within 0.66 points).
On SQL one peer accepts too many wrong answers (e 25–39%) for the cascade to beat the default (SQL-PA2 1 / 3). Requiring a second
check from yet another family multiplies e down if the two checks share A's wrong answers independently, at the price of r. If that
trade pays, SQL gets a cascade that beats its default without labels; if not, one peer is the end of the agreement route.
**What is known.** Single-check rates (printed by `python3.11 poc/analyze_and.py --predict` before this addendum; joint agreement not
computed): SQL train (1,338 fresh questions) Qwen3-8B with Qwen3.5-9B r 84.1 e 32.7 and Nemotron-3-Nano r 72.9 e 33.5; Qwen3-14B-AWQ
84.1 / 38.8 and 70.6 / 37.7; Qwen3.5-9B with Qwen3-8B 77.6 / 38.9 and Nemotron 69.7 / 36.4. Tool calls (BFCL) Qwen3-8B with
Qwen3.5-9B 72.1 / 19.0 and Llama-3.1-8B 68.9 / 17.4; Qwen3-14B-AWQ 73.5 / 18.4 and 72.4 / 14.9; Qwen3.5-9B with Qwen3-8B 82.6 / 17.8
and Llama-3.1-8B 69.4 / 15.7. Kim et al. (2506.07962): errors correlate across providers too, more among accurate models, so
independence is optimistic for e and pessimistic for r. Ensembles of verifiers / multi-model agreement (MoT cascades 2310.03094 use one
model's two views; MCS-SQL 2405.07467 votes over one model's candidates) do not measure what a second, independent check adds to a
first in a cascade.
**Rule** (`poc/analyze_and.py`, fixed now). A's passing quick answer → the first check (the fixed peer of SQL-PA / HO-PA) agrees →
the second check (another family: Nemotron-3-Nano on SQL train, Llama-3.1-8B on tool calls and SQL dev) agrees → answer; any
disagreement or a failed free check → A's SB→T→T. The second check is asked only after the first agrees; every check's tokens count.
Decision data: SQL train (tags q8bpa / q14apa / q35pa / n3npa) and tool calls (BFCL, 3 seeds); SQL dev reported.
**Theory prediction** (independent agreement given A's correctness: r1 r2, e1 e2; linear model with A's own coefficients): two checks
minus the first alone, SQL train +0.64 / +0.39 / +0.14 utility (Qwen3-8B / Qwen3-14B-AWQ / Qwen3.5-9B), tool calls +0.32 / +1.60 /
+0.30; SQL dev +0.80 / +0.39 / −0.15.
**Predictions** (paired 95% intervals over items, seed means).
- **SQL-AND1 (the second family's shared errors are not nested in the first's):** joint e ≤ half the smaller single e, 6 of 6
  decision cells.
- **SQL-AND2 (SQL):** two checks − the single peer, utility lower bound > 0, and two checks − SB→T→T, lower bound > 0, each in ≥ 2 of 3
  models on SQL train.
- **SQL-AND3 (tool calls):** two checks − the single peer, lower bound > 0, in ≥ 2 of 3 models.
- **SQL-AND4 (the theory's sign):** the measured sign of two checks − the single peer matches the predicted sign in ≥ 5 of 6 cells.
**Expected (stated now, not a rule).** AND1 holds; AND2 refuted against the peer (predicted gains +0.1 to +0.6, smaller than the
intervals); AND3 1 of 3 (Qwen3-14B-AWQ, where the peer leaks most per point of r); AND4 holds.
**Decision.** AND2 holds (both parts) → SQL's no-label default becomes N → two checks of other families agree → answer, else SB→T→T
(PROJECT, REPORT §5.11, PROPOSAL / PROPOSAL_ko). AND3 holds → tool calls' default takes a second check when a third model is served
(same places). Otherwise reported: a second check costs more right answers than it saves wrong ones, and the single peer stays the
agreement route's end.

### Results SQL-AND (written 2026-10-30 02:3x UTC)
`python3.11 poc/analyze_and.py` (results/and.txt, not committed). Script fix after a first run, before deciding: the per-item utility
was in points while the interval helper multiplies by 100, so the printed differences were 100× too large (signs, interval positions
and every decision unchanged).
- **SQL-AND1 refuted (1 / 6).** Joint e on SQL train 20.5 / 23.8 / 24.3% (half the smaller single e: 16.4 / 18.9 / 18.2; independence:
  11.0 / 14.6 / 14.2); tool calls 9.0 / 7.4 / 8.4% (8.7 / 7.5 / 7.9; independence 3.3 / 2.7 / 2.8).
- **SQL-AND2 refuted.** Two checks − the single peer on SQL train: −0.93 [−1.52, −0.30], −0.41 [−1.02, +0.20], −0.85 [−1.46, −0.28]
  (0 / 3); two checks − SB→T→T +0.80 [+0.19, +1.48], +0.79 [+0.08, +1.48], +0.02 [−0.39, +0.43] (2 / 3).
- **SQL-AND3 refuted (1 / 3).** Tool calls: −0.24 [−0.53, +0.02], +0.59 [+0.27, +0.93] (Qwen3-14B-AWQ), −0.40 [−0.71, −0.06].
- **SQL-AND4 refuted (1 / 6).** Predicted positive in all six; measured positive only for Qwen3-14B-AWQ on tool calls. SQL dev
  (reported): +0.20, −0.40, −0.35 (n.s.) against the peer; +0.78, +0.60, +0.87 against SB→T→T (all lower bounds > 0).
- **Why (exact decomposition, post hoc).** Accepting a passing quick answer changes accuracy only on discordant items: +1 where A is
  right and the default wrong (2.8–6.6% of items), −1 where A is wrong and the default right (7.1–14.0%); on the rest it changes
  tokens only. So the accuracy gain is exactly π_RW · r_RW − π_WR · e_WR (agreement rates within those two strata), and no check can
  lift the cascade's accuracy above the default's by more than π_RW. Agreement depends on difficulty for every check together: the
  peer agrees with A's right answers 74–88% where the default is also right but 34–64% where the default fails, and with A's wrong
  answers 25–44% where the default also fails but 11–26% where it succeeds. Averaged (r, e) therefore overstate a check's value
  (SQL-DV's linear model overpredicted SQL by up to 1.8), and two checks are not independent. The second check roughly halves both
  discordant rates (r_RW → 9–42%, e_WR → 4–12%); on SQL that removes more gain than loss (Qwen3-8B, train: accuracy gain +1.50 →
  +0.67 points) and, by accepting fewer answers, saves fewer tokens.
- **Raw costly leaks read** (Qwen3-8B, SQL train; A wrong, default right, both checks agree: 28 of 3,975 item-seeds; 6 read): 3 output
  shape conventions ("full name" concatenated where the evidence defines it as two columns), 1 ambiguous question (percentage of tied
  games), 2 genuine shared errors (a date literal in another format than the database's; CAST(date AS DATE) compared with a year).
- **Related work.** ABC (2407.02348) defers on disagreement within an ensemble at each tier; here a one-peer agreement is the useful
  part and a second member costs more right answers than it saves wrong ones, because agreement on both falls with difficulty
  together (consistent with Kim et al. 2506.07962: errors are correlated across providers, more so among accurate models).
- **Decision.** AND2 and AND3 refuted → reported only: the single peer stays the agreement route's end. The theory is restated on
  discordant items (REPORT §5.11): a check's value is set by its agreement where the quick answer and the default differ in
  correctness, and the accuracy upside of any accept rule is bounded by π_RW.
