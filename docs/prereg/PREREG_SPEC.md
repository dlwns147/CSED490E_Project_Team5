# PREREG_SPEC — does check-and-escalate add on top of a specialist? (registered 2026-11-22 07:40 UTC)

**Why (user 11-22: "are loop dealing testing suggesting important problems?").** On clean OptiBench a fine-tuned 14B specialist
(LLMOPT-14B, official checkpoint and prompts, PREREG_TYPED registration I) beats Qwen3-8B's full method, and on SQL published 7B
specialists lead by about 7 points. If the method only helps general models, its scope is narrow; if a free check plus escalation also
improves a specialist, the method is complementary to specialists. Prior work: FrugalGPT / AutoMix (cascades by a learned or
self-verified score, no execution evidence), LLMOPT's own self-correction (the same model judges itself). New here: a cross-family
execution-agreement check on a specialist's answer, escalation priced in tokens.

**Arms (offline on stored rows; no row of the combination has been computed; per-arm accuracies were seen in registration I).**
Held-out sets NL4OPT + IndustryOR, OptMATH (seed 1 own program), OptiBench, BWOR, LogIOR; seeds 1–3; peer = gpt-oss-20b.
- SPEC: LLMOPT-14B alone (its full pipeline with self-correction).
- FULL: our method for gpt-oss-20b (typed → own → repair → peer agreement with Qwen3-8B → thinking; PREREG_TYPED J).
- SPEC+C: LLMOPT's answer; accepted if it prints a value and gpt-oss-20b's quick program prints the same value; otherwise gpt-oss-20b
  thinking. Tokens: LLMOPT's + gpt-oss-20b's quick program + thinking when escalated.
- SPEC+C8: the same with Qwen3-8B (its quick program as the check, its thinking as the escalation), for the Qwen3-8B user.
**Predictions.** S-1: SPEC+C − SPEC > 0 in utility on the held-out pool (rate 0.5, output tokens). S-2: SPEC+C − FULL ≥ 0 on the pool
(the specialist's answer is a better first step than gpt-oss-20b's own program). S-3 (per set, descriptive): SPEC+C ≥ SPEC on every set.
**Decision rule.** S-1 holds (Holm over S-1, S-2, S-1 for SPEC+C8; clustered bootstrap by problem; raw AND audited labels both) → the
report states the method is complementary to the specialist and adds the SPEC+C row; S-1 fails on either label set → the report states
the method's scope as general models. Cost views 0.25–2 and size-weighted reported as sensitivity.
