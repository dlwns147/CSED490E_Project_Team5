# PREREG_M0 — a self-configuring ladder: choose the ladder or plain thinking from unlabeled items

Written 2026-11-19 06:1x UTC.

**Why.** Two results stand separately: the ladder pays exactly when its check accepts answers thinking gets wrong (ΔU = 100·a·(p − q) −
0.5·Δktok), and that gain can be estimated without labels (hybrid estimate: PREREG_LF, KK, FUTO; mean error 1.8 over nine blind cells).
The method does not use the second result. Here it does: on a new domain, run both routes on a small unlabeled calibration sample, estimate
ΔU, and deploy the ladder only if the estimate is above 0, otherwise plain thinking.

**Related work (checked 11-19).** Paradigm routers (e.g. Select-then-Solve, 2604.06753) and model routers learn the choice from labeled data;
label-free accuracy estimation uses confidence meta-models (Fu et al. 2305.14802) or agreement with a reference model (PEEM, ACL Findings
2024) or among several models (EM over agreements). New here: the estimate is exact in structure for a check-gated cascade (only the
accepted items carry an accuracy term, and only their disagreement with thinking matters), so one reference model and a few hundred
unlabeled items price the whole cascade, including its tokens, and decide whether to deploy it at all.

**Known before writing (offline, all stored cells; `results/tmp_m0.py`; the rule and the threshold 0 were fixed before this test, the
calibration share 30% was chosen without looking).** 22 cells (OEIS 9, trips 4, K&K 6, Futoshiki 3), 300 random 30/70 splits each: the
self-configuring ladder gains +6.50 utility per item over always-thinking on average, always-ladder +5.28, the per-cell oracle +6.75. It
avoids the K&K losses of Qwen3-8B (−11.3 → 0) and Qwen3-32B (−8.3, −9.6 → 0, −0.4) and keeps every large win; it misses gpt-oss-20b on K&K
(−1.5; the estimate +1.8 was optimistic).

**Prospective test (cells never run).** Knights and Knaves with 10 / 12 inhabitants for Qwen3-8B and gpt-oss-20b (tags q8bh, oss20h; third =
the other one's quick translation), and Futoshiki for Qwen3-8B (300 test puzzles; third = gpt-oss-20b quick translation). For each cell,
the rule's choice from a fixed 30% calibration split (first 30% of ids in sorted order) is logged before any score; then the remaining 70%
are scored.
- M0-1: in every cell the chosen configuration's realized ΔU on the 70% is within 2 points of the better fixed configuration (ladder or
  thinking).
- M0-2: summed over the three cells, the self-configuring choice beats always-ladder.
Decision: both hold → the self-configuring ladder becomes the method's deployment rule. Otherwise report where the estimate misled it.

**Choices logged (2026-11-19 08:0x UTC, before any score of these cells was read; `python3 results/tmp_m0_pro.py choose`).** Baselines:
Qwen3-8B thinking 0 of 200 at the cap, 200 parsed; gpt-oss-20b thinking 2 at the cap, 197 parsed. From the first 60 ids of each cell:
- K&K 10/12, Qwen3-8B: estimated ΔU −4.1 → **thinking**.
- K&K 10/12, gpt-oss-20b: estimated ΔU +7.9 → **ladder**.
Futoshiki Qwen3-8B still running.

**K&K cells scored (2026-11-19 08:0x UTC, on the other 140 ids each).** Qwen3-8B: ladder − thinking −17.3; the rule chose thinking (0):
**right**. gpt-oss-20b: ladder − thinking −2.6; the rule chose the ladder: **wrong by 2.6** (M0-1 fails in this cell; its estimate +7.9
from 60 items was optimistic, as it was for gpt-oss-20b on K&K at ≤ 8 inhabitants: +1.8 vs −1.5). So far the rule −2.6 vs always-ladder
−19.9 summed over the two cells. Futoshiki Qwen3-8B pending.
