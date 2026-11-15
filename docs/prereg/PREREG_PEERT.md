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

## Addendum A (registered 2026-11-13 06:1x UTC, before any gpt-oss-120b translation of seeds 7–9 exists): the stronger peer

**Why.** Across stored model pairs the peer step pays most when the peer is strong (grids above; on trip planning a weak peer even loses:
Qwen3-32B ← gpt-oss-20b −5.2, ← gpt-oss-120b +6.8, exploratory). On seeds 4–6 (stored, exploratory) gpt-oss-120b as the peer gives GridPuzzle
92.2% at 4.05k (U 90.2) against gpt-oss-20b's 89.3% at 6.08k (U 86.3); Mitra-Baral U 94.6 vs 93.2. The step's value should rise with the
precision of the peer's accepted grids, because each accepted grid replaces a 15–17k-token thinking translation.
**Run.** gpt-oss-120b `gtr`, seeds 7–9, both sets, reasoning effort low (as its stored seeds 1–6), one RTX PRO 6000 per set.
**Predictions.**
- **PEERT-A1 (decides which peer the method names):** ladder with gpt-oss-120b as peer − ladder with gpt-oss-20b as peer, GridPuzzle: interval
  above 0 → gpt-oss-120b; otherwise gpt-oss-20b stays (it fits 3090-class hardware). Predicted about +3.5.
- **PEERT-A2:** the gpt-oss-120b ladder − the ladder without a peer, GridPuzzle interval above 0 and Mitra-Baral lower bound above −2.0.

### Addendum A result (2026-11-13 06:4x UTC; `python poc/gp_conj.py peert --peer oss120`, gs15 lanes pt120_*, closure job ptcl120): A1 and A2 hold

| Seeds 7–9 | GridPuzzle | Mitra-Baral |
|---|---|---|
| No peer | 87.8% at 8.99 ktok, U 83.3 | 93.6% at 5.87 ktok, U 90.7 |
| gpt-oss-20b peer | 91.0% at 6.00, U 88.0 | 95.7% at 2.12, U 94.7 |
| **gpt-oss-120b peer** | **92.9% at 4.55, U 90.6** (peer's grids 121/125 right) | **95.7% at 0.97, U 95.3** (61/62) |
| **A1:** 120b peer − 20b peer | **+2.6 [+0.5, +4.7]** (predicted +3.5) | +0.6 [−0.3, +1.6] |
| **A2:** 120b peer − no peer | +7.3 [+4.8, +10.1] | +4.6 [+2.1, +7.6] |
| 120b-peer method − thinking only | +33.9 [+28.5, +39.3] | +10.8 [+4.8, +17.1] |

- **Decision as registered:** the method names gpt-oss-120b as the peer. With 3090-class GPUs only, gpt-oss-20b is the peer (+4.7 / +4.0, the
  main result above).

## Addendum B (registered 2026-11-13 06:4x UTC, before any seed 4–6 trip run exists): the peer step on trip planning

**Why.** The grid result should carry to the second computation domain only when the peer's one-solution answers are precise. Stored trip runs
(seeds 1–3, exploratory): Qwen3-32B ladder (`trc` → `trct` → `think`) with gpt-oss-120b's quick translation inserted after `trc`:
68.3% at 18.9k → 74.0% at 16.5k, +6.8 [+2.7, +11.0]; with gpt-oss-20b as the peer −5.2 [−8.5, −2.1] (its one-solution plans are less precise).
**Run.** NaturalPlan trip planning (100), seeds 4, 5, 6: Qwen3-32B-AWQ `trc`, `trct`, `think` (as its stored seeds), gpt-oss-120b `trc`
(reasoning effort low). gs15 GPUs 6 and 7. No closure (it is a grid rule).
**Prediction.** **PEERT-B1:** Qwen3-32B ladder with gpt-oss-120b's quick translation as step ② − without, interval above 0 → the peer step is
part of the method on trips as well; otherwise grids only. Predicted +5.

**Result (2026-11-13 10:3x UTC; `python poc/gp_conj.py peertrip`, seeds 4–6, 300 problem-seeds): PEERT-B1 holds.** Qwen3-32B ladder
69.0% at 19.08k tokens → with gpt-oss-120b's quick translation as step ② **72.0% at 18.22k**, +3.4 [+0.7, +6.2] (predicted +5); thinking
only 47.0% at 7.23k, so the ladder with the peer − thinking is +19.5 [+13.4, +25.7]. **Decision as registered:** the peer step is part of
the method on trips too, with a peer whose one-solution plans are precise (gpt-oss-120b; gpt-oss-20b lost −5.2 on seeds 1–3).

## Addendum B2 (registered 2026-11-13 07:1x UTC, before any gpt-oss-20b trip run of seeds 4–6 exists): a second main model on trips

Stored seeds 1–3 (exploratory): gpt-oss-20b ladder with gpt-oss-120b's quick translation as step ②: 79.0% at 31.5k → 79.3% at 24.4k,
+3.8 [+1.3, +6.7]. **Run:** gpt-oss-20b `trc` (effort low), `trct` and `think` (effort high), seeds 4–6, Slurm (2 × RTX 3090 per seed);
the peer rows are addendum B's gpt-oss-120b `trc`. **PEERT-B2:** with − without, interval above 0 (predicted +3), reported beside B1.

**Result (2026-11-13 10:3x UTC; `peertrip --main oss20 --peer oss120`, seeds 4–6): PEERT-B2 holds.** gpt-oss-20b ladder → with
gpt-oss-120b's quick translation as step ②: 82.3% at 26.60k tokens, +3.3 [+1.1, +5.6] (predicted +3). Against gpt-oss-20b thinking only
(73.0% at 14.16k): +3.1 [−2.2, +8.6], a tie: on trips the gpt-oss-20b ladder buys accuracy with tokens, and at this price the two are even.

**Correction, 2026-11-13 23:1x UTC (answer reading, FINDINGS 23:1x).** Bracket-less thinking plans are now read. Addendum B, Qwen3-32B: with
the peer 73.0% at 18.2k (was 72.0%), without 70.0%; B1 unchanged at +3.4 [+0.7, +6.2]; against thinking only (55.0%, was 47.0%) **+12.5
[+6.6, +18.6]** utility. B2 (gpt-oss-20b): thinking only 74.0% (was 73.0%), the ladders unchanged.

## Addendum C: peer first, without the main model's own quick translation (written 2026-11-15 06:0x UTC, before any seed-20–22 row)

**Why (exploratory read of stored rows, `results/tmp_agree.py` and FINDINGS 06:0x).** The trip ladder's wrong answers are mostly quick
one-plan programs it accepts: on seeds 17–19 the main model's own `trc` is right on 67 of 89 accepted programs for gpt-oss-20b and 11 of 13 for
Qwen3-32B, against the gpt-oss-120b `trc` 145 of 158 and the thinking translation `trct` 220 of 222 / 177 of 183. Dropping the main model's own
quick step (ladder: gpt-oss-120b `trc` → main `trct` → main `think`) on the stored rows: gpt-oss-20b +5.7 [+3.3, +8.2] (seeds 4–6) and +6.4
[+3.8, +9.1] (17–19) utility over the current ladder; Qwen3-32B +1.6 [+0.3, +2.9] (17–19). The order was chosen on these seeds, so it needs
fresh ones. (An agreement gate, accepting a quick plan only when two quick translations agree, was right 376 of 376 times but cost more than it
saved: −3.4 to +2.1; not pursued.)
**Run.** Fresh seeds 20, 21, 22: gpt-oss-120b `trc` (low effort), Qwen3-32B `trc`, `trct`, `think`, gpt-oss-20b `trc` (low), `trct`,
`think` (high), the settings of seeds 17–19; second server GPUs 6–7.
**Predictions.** **PEERT-C1:** peer-first − current, gpt-oss-20b, about +6 utility, interval above 0. **PEERT-C2:** Qwen3-32B about +1.5,
interval above 0. **PEERT-C3 (reported):** peer-first − thinking for gpt-oss-20b (the current ladder ties thinking: −3.0 on 17–19).
**Decision.** C1 or C2 above 0: the trip method becomes gpt-oss-120b `trc` → main `trct` → main `think` for that model (and the report says the
main model's own quick translation is dropped on trips); both above 0: for every model. Interval including 0: the current ladder stays.
*(07:0x UTC, before any seed-20–22 ladder row was read: seeds 21 and 22 already had `trc` and `direct` trip rows from 11-11 (another study's
runs; not used to choose this ladder order). The new runs overwrite them on the second server; the 11-11 rows are kept in
`results/np_s2122_1111/`. The test stands as registered; the report notes that seeds 21–22 were not new seeds for the trip prompts.)*

**Addendum C, Qwen3-32B read (2026-11-15 10:0x UTC; `python3 poc/gp_conj.py peerfirst --main q32 --seeds 20,21,22`).** Current 77.0% at 17.1k,
peer first 79.7% at 14.1k, thinking only 56.3% at 6.8k. **PEERT-C2: peer first − current +4.2 [+2.6, +6.0] utility** (predicted +1.5, above
0): holds. Peer first − thinking +19.7 [+12.8, +27.0]. gpt-oss-20b (C1) still running. (Replay, not registered: Qwen3-8B on seeds 1–3 with the
gpt-oss-120b step, peer first − current +4.3 [+2.5, +6.3].)

**Addendum C, gpt-oss-20b read and decision (2026-11-15 11:0x UTC; `peerfirst --main oss20 --seeds 20,21,22`).** Current 86.0% at 25.4k, peer
first 90.0% at 24.5k, thinking only 79.7% at 13.8k. **PEERT-C1: peer first − current +4.4 [+2.0, +7.0] utility** (predicted +6, above 0):
holds. **PEERT-C3:** peer first − thinking +5.0 [−0.2, +10.4] (the current ladder: −3.0 on seeds 17–19). **Decision (both C1 and C2 above 0):
the trip method for every model is gpt-oss-120b `trc` → main `trct` → main `think`;** the main model's own quick translation is dropped on
trips. The report states the reason measured on seeds 17–19: the main model's quick one-plan programs are the ladder's least precise accepts.

**Addendum C2, Qwen3-8B (written 2026-11-15 11:0x UTC, before any Qwen3-8B seed-20–22 row).** The stored-row replay on seeds 1–3 gave peer first
− current +4.3 [+2.5, +6.3]. Run: Qwen3-8B `trc`, `trct`, `think`, seeds 20–22 (the gpt-oss-120b `trc` rows are shared), second server GPU 6.
Prediction: about +4, interval above 0; if not, the report says the trip order is tested on Qwen3-32B and gpt-oss-20b only. (A replay on the
grid sets without closures found no clear gain for peer first: −0.0 to +4.3, every interval including 0; grids keep their order.)

**Addendum C2 read, Qwen3-8B (2026-11-15 14:0x UTC; `peerfirst --main q8b --seeds 20,21,22`; seed 22 ran on GPU 7 as `q8bp` and was copied to
the `q8b` names; the duplicate on GPU 6 was stopped at its first row).** Current 63.7% at 21.1k, peer first 67.3% at 18.1k, thinking only
34.0% at 10.4k. **Peer first − current +5.2 [+3.0, +7.5] utility** (predicted about +4, above 0): holds. Peer first − thinking +29.5 [+22.1,
+37.0]. The trip order holds for three models.
