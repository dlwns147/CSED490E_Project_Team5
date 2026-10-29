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
