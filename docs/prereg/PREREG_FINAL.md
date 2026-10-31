# Pre-registration FINAL: the SQL claim on an untouched benchmark, with a family-wise error correction

Written 2026-10-31 20:2x UTC, before any model has answered a Spider question. Known before writing: Spider's test split as prepared
(`SQL_SPLIT=spider python3.11 poc/prep_sql.py`: 2,147 questions on 40 databases; gold queries run without error on all, 54 return
no rows; prompts 0.3–1.8k tokens) and every BIRD result.

**Purpose (the goal: exactly right answers with the fewest tokens).** The review (docs/notes/CRITIQUE.md, 10-31, point 5) found many
tests, no multiplicity correction, and held-out sets reused for decisions: BIRD dev and the fresh BIRD-train questions informed
SQL-1, SQL-PA, CV-1, EXT, XG and more. The SQL claim — the quick query checked by another model's quick query (else the default
short think → think → retry) beats the default — is tested once more, on a benchmark never used here, as a fixed family of five
tests with Holm's correction. Spider (Yu et al., EMNLP 2018; databases from the pinned re-host HAL-9001/spider-databases, sha256
00636695…c85b121b, the authors' Yale release) is public, so contamination cannot be excluded; it would favour every arm, and the claim
is about the cascade against the default, both from the same model. Spider is easier than BIRD (no evidence line is needed, schemas
are small), so the test also asks whether the gain survives where thinking matters less.

**Tests (one-sided paired bootstrap p-values over questions, seed means, 10,000 resamples; cascade − default in utility, 100 × right −
0.5 × ktokens with the peer's tokens counted; Holm over F1–F5 at 0.05).** Items, prompt (BIRD's without the evidence line), free
check (runs, ≥ 1 row), "same answer" (the same result rows), default (SB→T→T, the retry at the next seed), seeds 1–3, peers and arms
exactly as on BIRD:
- **F1** Qwen3-8B, peer Qwen3.5-9B.
- **F2** Qwen3-14B-AWQ, peer Qwen3.5-9B.
- **F3** Qwen3.5-9B, peer Qwen3-8B.
- **F4** gpt-oss-20b (low-effort N; medium-effort SB and T, XG's harmony arms), peer Qwen3.5-9B.
- **F5** Qwen3-8B with CV-1's trained quick query (C1 adapter) as N, the base model's default, peer Qwen3.5-9B.
On BIRD dev the same analysis (`FINAL_SUFFIX= python3.11 poc/analyze_final.py`, the dry run) gives F1 +0.58 [−0.27, +1.43] (p 0.09),
F2 +1.00, F3 +1.23, F4 +1.99, F5 +1.99 (p ≤ 0.01): 4 of 5 after Holm.

**Theory (written before the rows).** The cascade's gain is the accept decisions on the decisive strata (quick right / default wrong,
and the reverse) plus the default's tokens saved on every accepted answer, minus the two quick answers' tokens. On an easier set both
decisive strata shrink, so the accuracy part shrinks with them, while the token part is the accepted share times the default's length.
With BIRD's per-model separation (peer ratio 2.2–3.5) and r* near 1.2–2.0, the accuracy part should stay positive but smaller; the
token part is about 0.5 × (accepted share ≈ 0.6–0.7) × (the default's ktokens, ≈ 0.5–1.5 on Spider) ≈ +0.15 to +0.5. Expected gains
+0.3 to +1.2 utility per test; with a per-question SD of 12–17 the standard error is 0.26–0.37, so each test has power of about
0.4–0.9 at its Holm threshold.

**Predictions.**
- **FINAL-P1:** at least 3 of F1–F5 hold after Holm.
- **FINAL-P2:** every test that holds has the sign the break-even predicts (peer TPR / FPR above r*) and a decisive-strata ratio
  within 30% of its all-passing ratio (as XG-P3 / P4).
- Reported: each generator's N, default, T→T, N→T→T and cascade (accuracy @ tokens); dominance or trade with its break-even λ; the
  strata; F1's comparison with BIRD dev, where it was not shown.

**Decision rules.**
- 4–5 hold: the SQL claim is confirmed on an untouched benchmark at a 5% family-wise error rate; PROJECT, REPORT and PROPOSAL cite
  the Spider numbers next to BIRD's.
- 2–3 hold: the claim names the generators for which it holds on Spider; the others are stated as BIRD-only.
- 0–1 hold: the SQL claim is restated as BIRD-specific, and the break-even accounting says which term changed on the easier set.
- F5 (the trained quick query) is the only test of training's transfer to another benchmark: if it fails while F1 holds, the CV-1
  claim is restated as BIRD-specific whatever the count.

**Run.** `bash poc/slurm/submit_final.sh` (written with this file): one job per model and seed with each model's BIRD server
settings (Qwen3-8B TP 2; Qwen3.5-9B with its card's thinking sampling; gpt-oss-20b as XG), the C1 adapter's quick queries in one job
(`CV_EVAL_SPLIT=spider`), grading in the lanes (`SQL_SPLIT=spider grade_sql.py`). Analysis: `python3.11 poc/analyze_final.py >
results/final.txt` (written and dry-run on BIRD dev before this file).
