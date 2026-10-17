# Pre-registration X2: verify once, reuse on math word problems with numeric variants (GSM-Symbolic)

Written 2026-10-16 18:10 UTC, before any run. Results go below; this section is not edited afterwards.

**Why.** Our clearest win in optimization was "write one program, check it on a few instances, reuse it" (routing 7% → 94%). The
math analogue is a family of word problems that differ only in names, objects and numbers. GSM-Symbolic (Apple, 2024; 100
templates × 50 numeric variants of GSM8K problems) showed that per-instance accuracy varies across such variants; nobody (to our
knowledge) measured writing ONE checked solver per template and reusing it, priced in tokens.
**Prior art.** PAL / Program-of-Thoughts (one program per instance); GSM-Symbolic (variance across variants); template-based solvers
for math word problems (pre-LLM); our V1 for optimization.
**Design.** 100 templates, instances 0–19 each (results/math/gsmsym.json). text = per-instance answer in \boxed{} (no thinking, one
sample). solver = 4 candidate programs `solve(question: str)` written from instance 0, meant for every variant (they must read the
numbers from the text); keep the first candidate right on instances 1–3 (the labelled check), else the one right on most; reuse it on
instances 4–19. Both evaluated on instances 4–19 (1,600 per model). Tokens: per-instance output tokens vs the 4 candidates' tokens
spread over the template's 20 instances. Models: Qwen3-32B-AWQ, gpt-oss-20b low, Qwen3.6-35B-A3B (no thinking). poc/run_gsmsym.py.
- X2-P1: verify-once-reuse is within 2 points of per-instance text accuracy (or above it) at ≤ 25% of its tokens, for every model.
- X2-P2: when reuse fails, the program usually misreads the numbers in a variant (parsing), not the arithmetic (read ≥ 10 failures).
- X2-P3: ≥ 85% of templates get a candidate that is right on all three checks (cheap verification suffices).

**Harness bug (2026-10-16 19:06 UTC, before any result was read):** the solver runs crashed at once (`int` template ids passed to
`.encode()`); the per-instance text runs completed (2,000 per model). Fixed (`str(t)`); the solver mode is re-run on GPU 2
(poc/queue_s2_x2b.sh). Predictions unchanged.

## Results (2026-10-16 19:29 UTC; 100 templates, held-out instances 4–19 = 1,600 per model; results/x2/grade_*.log, hybrid.log)
| model | per-instance text (held-out) | verify-once-reuse as pre-registered | templates with a candidate right on all 3 checks | held-out accuracy of those verified programs |
|---|---|---|---|---|
| gpt-oss-20b low | 90.5% @ 210 tokens / instance | 60.4% @ 98 | 55 / 100 | 99.9% |
| Qwen3-32B | 91.9% @ 267 | 51.1% @ 38 | 47 / 100 | 100.0% |
| Qwen3.6 | 94.8% @ 534 | 70.6% @ 226 | 60 / 100 | 99.1% |
**X2-P1 refuted** (reuse 24–41 points below per-instance), **X2-P3 refuted** (47–60% of templates, not ≥ 85%). The pre-registered rule
falls back to the best *unverified* candidate when none passes the checks, and those fail. Raw candidates (Qwen3-32B, 400): 163 right
on the shown instance and all 3 checks, 99 wrong already on the shown instance (arithmetic / reading), 83 crash or return nothing on
the variants (number parsing), 55 right on the shown instance only (e.g. template 103: the shown instance has 77 miles = 77 miles,
the program returns the first number, a shortcut that fits the coincidence). **X2-P2 partly holds** (138 parsing / overfitting vs 99
arithmetic failures).
Exploratory (not pre-registered): reuse only verified programs, per-instance text elsewhere: 92.2 / 93.9 / 94.6% (per-instance
90.5 / 91.9 / 94.8%) at 188 / 158 / 437 tokens per instance (89% / 59% / 82% of per-instance). A program that passes 3 labelled checks
is ≈ 100% right on the other variants, so verification is reliable here; what fails is writing a variant-proof program at all
(only ≈ 40% of candidates are), and per-instance answers are already cheap and 91–95% right, so reuse saves little.
