# Pre-registration MODEL: when does "fact first, think only where the check fails" win, and can a small pilot tell?

Written 2026-10-18 17:36 UTC, before computing. Offline, on stored rows only. Results go below.

**Why.** Across many cells (model × benchmark × seed) the recipe sometimes matches always-thinking at a fraction of the tokens
(Qwen3-32B on X6), sometimes loses points (Qwen3-4B), sometimes wins (Qwen3-32B with the two-program check). A practitioner facing a new
task / model needs to know which policy to run without running everything. Exact decomposition: FF − always-think =
P(pass) × [P(fact program right | pass) − P(thinking right | pass)]: the recipe loses only on items the check passes, and only if
thinking would be right more often there than the cheap program. Both terms are estimable from a few labelled items.
**Cells.** X6 (NL4OPT + IndustryOR, 345 items): Qwen3-1.7B / 4B / 8B / 14B-AWQ / 32B-AWQ, gpt-oss-20b, Qwen3.6 (80k thinking) × seeds
1–3 = 21 cells; U1 suites (geometry 108, optimization 100): the same 7 models × 2 domains × cure seeds 1–3 = 42 cells.
Policies: CHEAP (fact program only), FF (fact program; thinking if its check fails), FFR (fact program; thinking unless it runs AND a
second fact sample agrees), THINK (always thinking). Utility = accuracy (points) − λ × output tokens (thousands), λ ∈ {0, 0.5, 2}.
**Pilot rule.** Label k random items of the cell (and run every policy on them), pick the policy with the best pilot utility, report
the regret = best full-cell utility − full-cell utility of the pick, averaged over 1,000 pilots. poc/analyze_policy_model.py.
- MODEL-P1 (identity check): the decomposition reproduces FF − THINK exactly in every cell (a harness sanity check).
- MODEL-P2: with k = 30 labelled items the mean regret is ≤ 1.0 point (λ = 0.5) over all 63 cells; with k = 10 it is ≤ 3 points.
- MODEL-P3: no single fixed policy is best in ≥ 80% of the cells at λ = 0.5 (the choice is task- and model-dependent).
