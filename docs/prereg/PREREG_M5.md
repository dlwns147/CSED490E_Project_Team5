# Pre-registration M5: M4 + voting (cheap context-diverse voting)

Written 2026-10-14 02:28 UTC, before any run below. Results are appended below without editing this section.

**Idea.** TroVE-style voting over programs written with and without the toolbox was the strongest method (M2–M4 results) because the two
contexts fail on different tasks, but it needs 4 programs. M4 already produces two programs from different contexts: the draft (no
helpers) and the rewrite (with helpers). Add one more program and vote.
**Data.** Re-run M4 (same settings as PREREG_M2_M4: Qwen3-8B and Qwen3-32B-AWQ, 7 tasks, seeds 1–2) now storing the draft
(`draft_code`); the third program is the stored all-helpers (K8) sample of the same instance and seed. Packaging-free scoring as before.
**Variants (label-free).** V1: majority answer on the given input over {draft, rewrite, K8 sample}; if all three differ, take the rewrite.
V2 (no extra program): if draft and rewrite agree on the given input, output the rewrite; otherwise the one consistent on the metamorphic
copies (rewrite if both or neither).
**Predictions.**
- M5-P1: V1 pooled ≥ TroVE-style 4-sample voting − 2 points (8B 91.2%, 32B 95.0%) for both models, at ≤ 70% of its tokens.
- M5-P2: V2 pooled ≥ M4 + 3 points, at M4's tokens (+ CPU checks).
- M5-P3: for 32B, V1 ≥ think-1,024 (90.0%).
Also reported: the M4 replication (pooled accuracy of the re-run vs the first run).


---
## Results (appended 2026-10-14 02:45 UTC; predictions above unedited)

`poc/analyze_m5.py`; packaging-free; 7 tasks × 2 seeds (840 per model); tokens per instance.

| | Qwen3-8B | tokens | Qwen3-32B | tokens |
|---|---|---|---|---|
| M4 re-run (rewrite) | 88.9% (first run 89.0%) | 961 | 85.2% (first run 85.2%) | 826 |
| draft alone (no helpers) | 69.6% | – | 77.3% | – |
| V1: vote over draft, rewrite, one all-helpers sample | 87.7% | 1,844 | 88.0% | 1,350 |
| **V2: draft vs rewrite, metamorphic check breaks disagreements** | 89.0% | 961 + checks | **91.5%** | **826** + checks |
| references: think-1,024 / TroVE-style 4-sample vote | 94.5% / 91.2% | 1,704 / ≈2,560 | 90.0% / 95.0% | 1,591 / ≈1,810 |

- M4 replicates exactly (89.0 → 88.9; 85.2 → 85.2).
- **M5-P1 not confirmed:** the 3-program vote is below TroVE (87.7 vs 91.2; 88.0 vs 95.0). With one all-helpers sample, two of the three
  programs carry the helpers, so steering errors can win the vote (8B core 566 vs 576 for the rewrite alone).
- **M5-P2 split:** V2 adds nothing for 8B (+0.1) but +6.3 for 32B (core 510 → 559): when draft and rewrite disagree, the 32B draft is often
  the consistent, correct one (the rewrite broke it).
- **M5-P3 not confirmed for V1, but V2 reaches it:** for 32B, V2 (91.5% at 826 tokens) beats think-1,024 (90.0% at 1,591) at about half
  the tokens; TroVE-style voting stays the most accurate (95.0% at ≈1.8k).
- Cost–accuracy frontier after all methods: 8B: all helpers 78.9% @ 0.9k → M4 / V2 89% @ 1.0k → think-1,024 94.5% @ 1.7k (TroVE is
  dominated). 32B: all helpers 79.4% @ 0.5k → **V2 91.5% @ 0.8k** → TroVE 95.0% @ 1.8k (think-1,024 is dominated).
