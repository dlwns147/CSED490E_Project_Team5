# Pre-registration B3: published fixes for distracting / under-specified helpers as baselines (F1, F2)

Written 2026-10-13 18:29 UTC, before any data below. Results are appended below without editing this section.

**Earlier in-project attempts (FINDINGS, 2026-10-09/10):** a "use only if needed" header cut helper use by 40–65% but recovered only
−3 to +5 points; letting the model pick its own helpers from a catalog (self-scoping) recovered +5.5 to +9.5 (precision-limited).

**Baselines (Qwen3-8B and Qwen3-32B-AWQ, no thinking, `--stdlib`, T = 0.7, seeds 1–2):**
1. **Scope sentence** (cf. 2609.14157, one sentence on tool scope): appended after the toolbox: "Most of these helper functions are not
   needed for this task: use a helper only if your solution really needs it, and do not let the available helpers change how you solve the task."
2. **System 2 Attention (S2A, Weston & Sukhbaatar 2023, 2311.11829):** step 1, the model rewrites the full prompt keeping only what is
   relevant ("the problem, the input / output format, and only those helper functions, copied unchanged, that a correct solution actually
   needs"); step 2, it writes the program from the rewritten prompt. Cost: one extra call (≈ prompt-length output).
3. **DRAFT-style doc rewriting (2410.08197), one round, for F2:** the model sees the needed `in_circle` helper with its terse comment,
   writes up to 6 probe calls, sees their printed outputs, and rewrites the comment; 3 independent rewrites per model (its own docs).
   Each rewritten helper is then used for the delaunay task (60 programs per rewrite, seed 1).
Cells: F1 = 5 core tasks with 8 extra helpers (K8, 300 programs per seed) and, for 32B, diameter with the LOW toolbox (E2's format
channel, 120). F2 = delaunay. References already measured on this stack: K0 / K8 (C1), E2 signed / doc / fixed.

**Predictions.**
- B3-P1: the scope sentence recovers less than half of the K8 harm (K8+scope − K8 < 0.5 × (K0 − K8)) for both models.
- B3-P2: S2A recovers more than the scope sentence but stays below K0, for both models.
- B3-P3: on diameter LOW (32B), S2A leaves ≤ 15 count-line failures of 120 (it drops the helpers); the scope sentence leaves ≥ 30.
- B3-P4 (uncertain): DRAFT-style docs reach at least the hand-written warning's accuracy for 32B (80/120) but not for 8B (18/120 → stays < 40%).


---
## Results (appended 2026-10-13 18:52 UTC; predictions above unedited)

`poc/analyze_b3.py`; correct on all 8 variants. Packaging-free re-scoring (helpers pre-defined) changes no conclusion (`poc/rescore_pf.py`).

**F1, 5 core tasks, 2 seeds × 300:**

| condition | Qwen3-8B | tokens | Qwen3-32B | tokens |
|---|---|---|---|---|
| K0 (needed helpers only) | 552/600 | 313 | 551/600 | 294 |
| K8 | 468 | 828 | 451 | 473 |
| K8 + scope sentence | 470 (+0.3 [−2.5, +3.3]) | 394 | 454 (+0.5 [−2.8, +3.8]) | 357 |
| K8 + System 2 Attention | **402** (−11.0 [−15.3, −6.7]) | 888 | **381** (−11.7 [−16.3, −7.0]) | 919 |

**F1 format channel, Qwen3-32B, diameter with the LOW toolbox (120):** no toolbox 110 (10 count-line failures); LOW 54 (64); LOW + scope
51 (69); **LOW + S2A 98 (0)** at 621 vs 255 tokens.

**F2, delaunay, seed 1 (60 per cell):** signed 1 / 1 (8B / 32B); hand-written warning 11 / 43; fixed helper 55 / 52; **DRAFT-style
self-written docs 6, 10, 4 (8B) and 0, 0, 27 (32B)**, pooled 20 / 180 and 27 / 180 (≈ 250–330 tokens per doc).

- **B3-P1 confirmed:** the scope sentence recovers 2–3% of the K8 harm, although it cuts the use of extra helpers by a third (8B 503 → 331
  programs calling one). Same as the earlier "use only if needed" header: telling the model to ignore the helpers does not undo the steering.
- **B3-P2 not confirmed: S2A makes things worse** (−11 points at both sizes). Read from the outputs: (8B) the rewritten task drops details,
  so programs print a float (`180.0`; 44 programs are numerically right and rescued by a lenient comparison, still −3.7 below K8) or a
  signed area (area2 failures move to the mirrored / reversed copies); (32B) 82 of 600 second-step replies contain no program at all.
- **B3-P3 confirmed:** S2A removes all count-line failures on diameter (64 → 0; 54 → 98 of 120), because the rewritten prompt drops the
  helpers and restates the input format; the scope sentence does not (69).
- **B3-P4 half:** 8B stays below 40% (✓), but for 32B the self-written docs are far below the hand-written warning (27 vs 80 of 120-equivalent;
  pooled 15% vs 72%). Why: every rewrite states "counter-clockwise" as a precondition but none says what happens otherwise, and **none of the
  6 probe snippets ever called the helper on a clockwise triangle** (the 32B probes used 18 literal triangles, all counter-clockwise). The
  model explores only the regime the existing doc describes, so self-exploration does not uncover the hidden contract.
