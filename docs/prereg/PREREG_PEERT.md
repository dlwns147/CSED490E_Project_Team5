# Pre-registration: a cross-family quick translation as the second step of the grid ladder (PEERT)

Written 2026-11-13 05:3x UTC, before any gpt-oss-20b translation of seeds 7–9 exists.

**Why.** With the distinctness closure (PREREG_DCL) the course grid ladder is trained quick translation (`lf`, Qwen3-8B) → thinking
translation (`gtrt`, 15–17k tokens) → thinking. Its cost is mostly the thinking translation, and both Qwen3-8B translators drop the same
readings (PREREG_CONJ). A quick translation from another model family is cheap and reads differently: on word problems the cross-family peer
paid where same-family ones did not (XPEER). Grids are computation in the same sense as word problems (text → constraints → exact solver).

**Seen before this registration (exploratory, seeds 4–6, stored rows):** inserting gpt-oss-20b's quick translation (`oss20` `gtr`, reasoning
effort low, closure applied when it has several solutions) after `lf`: GridPuzzle 86.8% at 9.14k → 89.3% at 6.08k tokens, +4.0 [+2.3, +5.9];
Mitra-Baral 91.8% at 5.17k → 94.0% at 1.45k, +4.0 [+0.9, +8.1].

**Held-out run.** gpt-oss-20b `gtr`, seeds 7, 8, 9, both sets, the same command as the stored seeds 1–6 (`run_zebra.py --gp oss20 gtr <seed>
--set <set>`, POC_REASONING_EFFORT=low). `lf` (q8bgrllf0/1), `gtrt` and `think` (q8b) of seeds 7–9 are stored. Closure (`distinct_closure`)
on every step with two or more solutions, all tokens of every step paid (the peer's included). Bootstrap over puzzles, seed means.

**Predictions.**
- **PEERT-P1 (decides):** ladder `lf` → peer → `gtrt` → `think` minus `lf` → `gtrt` → `think`: GridPuzzle interval above 0, Mitra-Baral lower
  bound above −2.0. Predicted +4 and +3.
- **PEERT-P2:** precision of the peer's accepted grids at least 95% (GridPuzzle; seen 91 of 95).
- **Decision:** P1 holds → the peer step joins the course method; else it stays out.
