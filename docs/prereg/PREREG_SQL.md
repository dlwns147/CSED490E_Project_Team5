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
