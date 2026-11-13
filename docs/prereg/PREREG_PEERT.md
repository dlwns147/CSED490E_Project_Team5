# Pre-registration: a cross-family quick translation as the second step of the grid ladder (PEERT)

Written 2026-11-13 05:4x UTC, before any gpt-oss-20b translation of seeds 7–9 exists.

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

## Result (2026-11-13 06:1x UTC; `python poc/gp_conj.py peert`, jobs 1424668–1424669, closure job 1425009): P1 and P2 hold. The peer step joins the method

| Seeds 7–9 (held out) | GridPuzzle (645 puzzle-seeds) | Mitra-Baral (282) |
|---|---|---|
| `lf` → `gtrt` → `think` (closure on) | 87.8% at 8.99 ktok, U 83.3 | 93.6% at 5.87 ktok, U 90.7 |
| `lf` → gpt-oss-20b quick → `gtrt` → `think` | **91.0% at 6.00 ktok, U 88.0** | **95.7% at 2.12 ktok, U 94.7** |
| **PEERT-P1:** with − without | **+4.7 [+2.8, +7.0]** (predicted +4) | **+4.0 [+1.7, +6.9]** (predicted +3) |
| PEERT-P2: the peer's accepted grids right | 91/95 (95.8%) | 51/52 |
| Thinking only | 62.5% at 11.55 ktok | 87.6% at 6.22 ktok |
| Full method − thinking | +31.3 [+26.1, +36.8] | +10.2 [+4.2, +16.4] |

- **Decision as registered:** the cross-family quick translation joins the course method as step ②; the thinking translation moves to ③.
- **Other model pairs (exploratory, stored seeds 1–6 or 1–3, closure on):** main ← peer, GridPuzzle: Qwen3-8B ← gpt-oss-20b +9.2 [+6.6, +12.0],
  gpt-oss-20b ← Qwen3-32B +5.5 [+3.9, +7.4], Qwen3-32B ← gpt-oss-20b +1.4 [+0.4, +2.4], gpt-oss-20b ← Qwen3-8B +0.6 [−0.9, +2.1]; Mitra-Baral
  +0.2 to +4.7. The step never loses and always saves tokens; it pays most when the main model is weak and the peer at least as strong.

## Addendum A (registered 2026-11-13 06:3x UTC, before any gpt-oss-120b translation of seeds 7–9 exists): the stronger peer

**Why.** Across stored model pairs the peer step pays most when the peer is strong (grids above; on trip planning a weak peer even loses:
Qwen3-32B ← gpt-oss-20b −5.2, ← gpt-oss-120b +6.8, exploratory). On seeds 4–6 (stored, exploratory) gpt-oss-120b as the peer gives GridPuzzle
92.2% at 4.05k (U 90.2) against gpt-oss-20b's 89.3% at 6.08k (U 86.3); Mitra-Baral U 94.6 vs 93.2. The step's value should rise with the
precision of the peer's accepted grids, because each accepted grid replaces a 15–17k-token thinking translation.
**Run.** gpt-oss-120b `gtr`, seeds 7–9, both sets, reasoning effort low (as its stored seeds 1–6), one RTX PRO 6000 per set.
**Predictions.**
- **PEERT-A1 (decides which peer the method names):** ladder with gpt-oss-120b as peer − ladder with gpt-oss-20b as peer, GridPuzzle: interval
  above 0 → gpt-oss-120b; otherwise gpt-oss-20b stays (it fits 3090-class hardware). Predicted about +3.5.
- **PEERT-A2:** the gpt-oss-120b ladder − the ladder without a peer, GridPuzzle interval above 0 and Mitra-Baral lower bound above −2.0.
