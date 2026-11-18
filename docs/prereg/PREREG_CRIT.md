# PREREG_CRIT — LLM-Modulo's critics as the trip check, and our cheap candidate as LLM-Modulo's first step

Written 2026-11-17 21:4x UTC, before any seed-34–36 row exists.

**Why.** The report's one loss to related work: on trips, LLM-Modulo (hand-written critics + re-planning, Gundawar et al. 2411.14484)
beats our ladder for gpt-oss (−9.6 for gpt-oss-120b, a tie for gpt-oss-20b on seeds 20–22), while ours wins for Qwen3 by +21. By the
decomposition (progress §7) a ladder gains only where its check accepts items the fallback gets wrong; gpt-oss thinking is already right on
85% of what our count check accepts, and LLM-Modulo's loop is a much stronger fallback for gpt-oss than for Qwen3 (by cities: gpt-oss-120b
LLM-Modulo 100% on 8-city trips vs thinking 62%; Qwen3-8B LLM-Modulo 18% vs 10%, at 82k tokens).

**Known before writing (exploratory, seeds 20–22, `results/tmp_pcm.py`, utility per trip, paired over 300 trips):**
- **CC→T** (accept gpt-oss-120b's quick plan if the critics find no violation; else the main model's thinking translation if its plan passes
  the critics; else thinking) vs our current ladder (the same steps with the count = 1 check): +4.0 / +3.1 / +3.9 / +5.7 (gpt-oss-20b /
  gpt-oss-120b / Qwen3-32B / Qwen3-8B), all intervals above 0. The critics accept 2 wrong peer plans in 300 per model; count = 1 accepts more.
- **C→M** (accept gpt-oss-120b's quick plan if the critics pass it; else the main model's LLM-Modulo run) vs LLM-Modulo alone: +2.5
  [+1.0, +4.2] / +1.1 [−0.5, +2.8] / +13.7 / +22.3.
- The critics are LLM-Modulo's, built from Amonkar et al.'s structured constraint file (`poc/run_plan.py modulo_critics`), not from labels.

**Run.** Fresh seeds 34, 35, 36 (never used for any task), the 100 trips each, settings as seeds 20–22: gpt-oss-120b `trc` (low effort);
for each main model `trct`, `think` and `modulo` (gpt-oss high effort; Qwen3 default), gpt-oss-120b also its own `trct`, `think`, `modulo`.
gpt-oss-120b's ladder starts with its own quick translation (it is the peer).

**Predictions (pooled over the three seeds, paired bootstrap over 300 trips, 95%).**
- **P1:** CC→T − current ladder above 0 for each of the four models (point predictions as above).
- **P2:** C→M − LLM-Modulo: above 0 for both Qwen3 models; for gpt-oss, point estimate above 0 and lower bound above −2 (no worse).

**Decision.**
- P1 holds for at least 3 of 4 models → the trip method's check becomes the critics (stated as LLM-Modulo's hand-written, domain-specific
  check; the count check stays the method for domains without one). Otherwise the count check stays.
- P2 holds → the report states that putting our cheap candidate first makes LLM-Modulo cheaper and no worse for every model, and
  better for Qwen3. Otherwise the gpt-oss loss to LLM-Modulo stands as written.

**Mechanism on the seen seeds (written 2026-11-17 22:4x UTC, after the predictions; seeds 20–22, no new run).** Plans that the count check
accepts but the critics reject are **0 of 41 right** across the five plan sources (gpt-oss-120b quick translation 0/4; thinking translations
of gpt-oss-20b 0/0, gpt-oss-120b 0/6, Qwen3-32B 0/8, Qwen3-8B 0/23): a misreading that leaves exactly one solution. Plans the critics accept
but the count check does not are 27 of 32 right (the program printed several plans or none, but its first plan meets every constraint).
Precision: count = 1 81–100%, critics 98.9–100%. So the critics fix the weakness the report already names (a misreading that still leaves
one solution) and add coverage; Qwen3-8B, whose count check is least precise (81%), should gain most (P1 predicted +5.7).

**gpt-oss-120b cell (2026-11-18 02:4x UTC; seeds 34–36, all four runs 100 rows each; `SEEDS=34,35,36 MAINS=oss120 python3 results/tmp_pcm.py`).**
LLM-Modulo 96.0% at 17.9k; our current ladder 84.3% at 17.7k (−11.6 [−16.1, −7.3], the stored loss replicates).
- **P1:** CC→T − current ladder **+4.0 [+1.8, +6.5]** (predicted +3.1): holds for this model.
- **P2:** C→M − LLM-Modulo **+1.2 [+0.1, +2.6]**, 96.7% at 16.9k (predicted +1.1): holds (above 0, lower bound above −2).
The other three models are still running; the verdict is read when all four are in.

**Qwen3-32B, P1 (2026-11-18 05:4x UTC; its `trct` and `think` runs and the gpt-oss-120b `trc` runs are complete; `modulo` still running).**
Current ladder 75.7% at 14.1k; CC→T 80.7% at 13.2k: **+5.4 [+3.0, +8.2]** (predicted +3.9). P1 holds for this model. P2 waits for its LLM-Modulo runs.

**gpt-oss-20b cell and Qwen3-8B P1 (2026-11-18 07:4x UTC; all runs of these cells 100 rows each).**
- gpt-oss-20b: current ladder 86.3% at 22.2k, LLM-Modulo 96.0% at 30.4k. **P1: CC→T +4.7 [+2.2, +7.5]**; **P2: C→M − LLM-Modulo +3.3
  [+1.6, +5.3]** (96.0% at 23.8k): both hold.
- Qwen3-8B: current ladder 66.3% at 17.8k; **P1: CC→T 72.3% at 17.0k, +6.4 [+3.7, +9.6]**: holds.

**P1 verdict: holds for all four models** (+4.7 / +4.0 / +5.4 / +6.4; predicted +4.0 / +3.1 / +3.9 / +5.7). By the decision the trip method's
check becomes LLM-Modulo's critics (a hand-written, domain-specific check; the count check stays the method where no such check exists).
P2 holds for both gpt-oss models (+3.3, +1.2); the Qwen3 cells wait for their LLM-Modulo runs.
- **Qwen3-32B P2 (2026-11-18 08:4x UTC):** LLM-Modulo 68.3% at 32.8k; C→M 80.3% at 23.0k, **+16.9 [+11.7, +22.4]** (predicted +13.7): holds.
- **Qwen3-8B P2 (2026-11-18 09:2x UTC):** LLM-Modulo 59.0% at 48.5k; C→M 74.7% at 31.5k, **+24.2 [+18.5, +30.4]** (predicted +22.3): holds.

**Verdict (2026-11-18 09:2x UTC). P1 holds for all four models; P2 holds for all four** (+3.3 / +1.2 / +16.9 / +24.2). Decisions: the trip
method's check becomes LLM-Modulo's critics; the report states that our critic-checked cheap candidate before LLM-Modulo beats LLM-Modulo for
every model. Not registered, reported as such: per model the better fallback differs (thinking for Qwen3: CC→T vs LLM-Modulo +22.1 / +29.1;
LLM-Modulo for gpt-oss: CC→T −0.9 / −7.6), matching the label-free choice by critic pass rate on seeds 20–22.
