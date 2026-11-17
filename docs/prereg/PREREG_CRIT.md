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
