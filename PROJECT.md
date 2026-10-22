# Project: goal, scope, rules and status

*Solving Computational Math with LLMs, Accurately and Cheaply — Tools, Facts, and Checks.* POSTECH CSED490E (Graduate NLP), Team 5
(Sangjun Lee, Seongbin Park).

This file holds what the project is for and how we work. How to install and run everything: `README.md` (the manual). The argument with
all numbers: `PROPOSAL.md` (Korean: `PROPOSAL_ko.md`). The lab log: `docs/FINDINGS.md`.

## 1. Goal

LLMs can solve computational problems — geometry, combinatorial optimization, contest and word problems — by writing a program.
Programs can be silently wrong, and thinking longer is expensive. **Goal: exactly right answers with the fewest tokens, on models that fit
one 24 GB GPU (RTX 3090).** Every result is accuracy *and* tokens.

**The recipe we test:** write a program → add the missing fact (a few lines of exact library usage, or the model's own checked program for
a similar problem, found with no labels) → run a free check (the program runs; its outputs on moved / rotated / mirrored copies agree; the
statement's examples pass) → think harder only when the check visibly fails → reuse a checked program when the problem repeats.

## 2. Main claim and where it stands

Held-out benchmarks, 3 seeds, 95% intervals over problems (full table: `docs/notes/REPORT_OUTLINE.md`):
- For gpt-oss-20b and Qwen3-14B-AWQ the recipe ties or beats always thinking on every unseen benchmark (OptMATH, OptiBench, BWOR, LogiOR,
  four held-out geometry tasks) at 28–88% of its output tokens (37–97% counting input tokens).
- For Qwen3-8B it wins only on OptiBench with the label-free library, and loses where its free check leaks most (geometry edge cases,
  BWOR). The check's leak, not problem difficulty, decides where thinking should go.
- The label-free library of checked programs raises the first program in 23 of 25 model × benchmark cells (up to +34 points).
- Where it stops: short-answer competition math (text + thinking is better; a program is useful as a second opinion) and formal proofs
  (a specialized 8B prover, not a fact).

## 3. Scope

- **In:** computational geometry (CG) and combinatorial optimization (CO) solved by LLM-written programs: generated geometry and
  optimization suites, OR word-problem benchmarks (NL4OPT, IndustryOR, MAMO, OptMATH, OptiBench, BWOR, LogiOR), Codeforces geometry,
  Solomon routing, job-shop scheduling.
- **Models:** gpt-oss-20b, Qwen3-14B-AWQ, Qwen3-8B (fit one RTX 3090). Larger models (Qwen3-32B-AWQ, Qwen3.6-35B-A3B, gpt-oss-120b) only
  as references; trained baselines (STORM-Qwen3-4B, ORLM-8B) run on the same harness.
- **Side tracks** (kept short in the report): competition math (MATH-500, AIME), Lean and geometry proofs, factual QA (PopQA).

## 4. Working rules

1. **Pre-register.** Before a run, write the predictions with numbers and a decision rule in `docs/prereg/PREREG_<id>.md`; append results
   below, never edit the predictions.
2. **Only runs that can change the main claim.** Ask first: could this result change what we claim? If not, skip it — no replications or
   baselines for their own sake.
3. **At least 3 seeds** for any positive claim; report seed means and, for comparisons, a 95% interval over problems; call a tie a tie.
4. **Accuracy with its cost:** output tokens per problem always; input tokens where prompts differ in length.
5. **Read the raw outputs**, not only scores; treat a surprising number as a harness bug until the raw programs say otherwise.
6. **Record:** a dated entry (UTC, from `date -u`) appended to `docs/FINDINGS.md` for every result; `PROPOSAL.md` and `PROPOSAL_ko.md`
   updated together, short, numbers edited in place. Slides (`*.pptx`, `poc/make_slides.js`) change only when asked.
7. **Git:** commit and push after each change. The repository is public: scan the staged diff for secrets, never commit raw outputs
   (`*.jsonl`, logs), server addresses or keys; no co-author lines — commits are by the team's account.
8. **Explain for a first-time reader:** what ran, how, the result with its cost, what is next.

## 5. Status and next steps (2026-10-22)

- Done: held-out tests on OptMATH, OptiBench, BWOR, LogiOR and four geometry tasks; the weakest model's check leak is a stated limit
  (a brute-force program, a second sample and model-written edge-case tests all failed to close it); the rule for when to add a fact was
  tested prospectively on its "add" side (right in 10 of 12 points).
- Open: the "do not add a fact" side (needs a strong, rarely-crashing model on a new benchmark); **the final report** — full draft in
  `docs/REPORT.md` (English; to be fitted to the course format, length and deadline the team decides).
- Done (2026-10-23): checks that see what the leaky free check misses. A solution checker written from the text helps on BWOR / LogiOR
  (HO3) but not on OptiBench / OptMATH (HO4, HO5); one cheap repair turn before thinking helps on all word-problem benchmarks for the
  stronger models (HO6, HO7) but not on geometry (HO-G-R); model-written relations, edge tests and a second model's program (HO-G-M/E,
  HO-X) do not close Qwen3-8B's geometry leak — 37 of its 64 leaks are wrong only on edge cases the given input does not contain.
- Day-to-day state (running jobs, environment, evidence table): `docs/SLURM_HANDOFF.md`.

## 6. Documents

| File | Contents |
|---|---|
| `PROJECT.md` | this file: goal, claim, scope, rules, status |
| `README.md` | the manual: setup, running, files, harness notes |
| `PROPOSAL.md`, `PROPOSAL_ko.md` | the argument with every number (English, Korean; kept in sync) |
| `docs/FINDINGS.md` | lab log, dated, append-only |
| `docs/prereg/PREREG_<id>.md` | one file per experiment: predictions, then results and verdicts (index: `docs/README.md`) |
| `docs/notes/` | REPORT_OUTLINE (final-report draft), CRITIQUE (self-review), RELATED_WORK, FIX_MAP |
| `docs/SLURM_HANDOFF.md` | state of the work on the Slurm cluster |
| `HANDOFF.md` | the old servers' status log (until 2026-10-20) |
