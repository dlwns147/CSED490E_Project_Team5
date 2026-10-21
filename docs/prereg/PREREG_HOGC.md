# Pre-registration HO-G-C: does a brute-force view close the check leak that breaks the recipe for Qwen3-8B on held-out geometry?

Written 2026-10-21 18:5x UTC (Slurm server), before any brute-force program exists. Results are appended below without editing this section.

**Why.** On the four held-out geometry tasks (PREREG_HOG.md) "fact first, think only if the free check fails" (FF) beats always thinking
for gpt-oss-20b and Qwen3-14B-AWQ but not for Qwen3-8B (59.7% @ 4.55k vs THINK 74.0% @ 9.82k): 64 of its fact programs are consistently
wrong, so every transformed copy reproduces the same wrong answer and the metamorphic check (MR) accepts them (convex 19, tri 27, clip 18;
Qwen3-14B-AWQ 7, gpt-oss-20b 1). This is the one place on held-out data where the recipe fails. If a second, label-free view catches these
programs cheaply, the recipe holds for all three 24 GB models; if not, the limit stays as stated (for the weakest model, always think).
E3b (PREREG_E3B.md, dev tasks, Qwen3-8B) found that a brute-force program by the same model flags 86–90% of the programs MR misses, with
5–7% false alarms on simple tasks but 84% on hard ones (its own brute force was wrong), and saved nothing against a 1,024-token thinking
budget. Here the fallback is full thinking (≈ 9.8k tokens for Qwen3-8B), so a ~0.5k-token second program has more room to pay.

**New arm (the only GPU run):** `brute` = `poc/run_geo_cross.py --brute --stdlib`, the task prompt plus E3b's sentence "Write the simplest
brute-force program you can: correctness matters, speed does not (inputs are small).", **no toolbox and no algorithm hint** (a view
independent of the fact's helpers and algorithm), same instances and settings as HO-G (n_inst 12, T 0.7, seeds 1–3, max_tokens 4096;
gpt-oss-20b low effort, Qwen3 thinking off). Lane `poc/slurm/hogc_brute.sh`, tag `SL_HOGC_<model>_geo_brute_s<seed>`, on RTX 3090. The fact
(F) and thinking (THINK) rows are the stored HO-G rows of the old server; every policy pairs rows of the same item and seed.
**Agreement** (label-free): two programs agree if their outputs are equal (as numbers where both parse as fractions) on each of six inputs:
the given instance and its translate / rot90 / mirror / permute / scale copies (no 10^9 copy, where a brute force may be legitimately slow);
a crash, timeout or empty output = disagreement.
**Policies** (offline, `poc/analyze_hogc.py`; tokens = every cheap program written + thinking where escalated; correct = right on all 8
variants, as before):
- FF (HO-G): accept F if it passes MR, else THINK.
- STRICT (differential check): accept F only if F passes MR **and** agrees with the brute-force program B; else THINK.
- TWO-VIEW (two cheap views): accept F if F and B both pass MR and agree; if exactly one passes MR, accept that one; THINK if neither passes
  or both pass and disagree.
- RESAMPLE (no new run): accept F only if it passes MR and agrees with a second fact sample (the same item's fact row of the next seed:
  s1↔s2, s2↔s3, s3↔s1); its tokens are added.
- THINK (always).

**Predictions** (seed means over 96 items × 3 seeds unless stated):
- HOGC-P1 (the leak is visible): for Qwen3-8B, STRICT flags ≥ 60% of the fact programs that pass MR but are wrong, and ≤ 15% of the correct
  MR-passing ones on overlap / convex / tri; on clip (exact rational area, no natural brute force) its false alarms are ≥ 30%.
- HOGC-P2 (accuracy): STRICT for Qwen3-8B ≥ THINK − 3 (≥ 71.0%; FF 59.7%).
- HOGC-P3 (the handoff's decision rule = HOG-P1): STRICT ≥ THINK − 1 at ≤ 60% of THINK's tokens for Qwen3-8B. **Predicted to fail on
  tokens** (expected ≈ 70%: FF already escalates 41% of items at ≈ 9.8k each, and each newly flagged item adds another thinking run).
- HOGC-P4 (uncertain): TWO-VIEW meets HOG-P1 for Qwen3-8B (≥ THINK − 1 at ≤ 60% of its tokens), because the brute-force program replaces
  thinking where F visibly fails but B passes MR; this holds only if B is right on most such items.
- HOGC-P5 (no harm without a leak): for gpt-oss-20b and Qwen3-14B-AWQ, STRICT and TWO-VIEW are within 1.5 points of FF, and HOG-P1 still
  holds for both (≥ THINK − 1 at ≤ 60% of THINK's tokens).
- HOGC-P6: RESAMPLE flags < 40% of Qwen3-8B's leaked programs (consistent wrong logic repeats across samples, as for Qwen3-4B in SIZE-CHK).

**Decision rule.** (a) If STRICT or TWO-VIEW meets HOG-P1 for Qwen3-8B on the seed means and on ≥ 2 of 3 seeds, and HOGC-P5 holds: the free
check on geometry becomes "metamorphic copies + a brute-force view", and "the recipe holds on held-out geometry" extends to all three 24 GB
models (PROPOSAL finding 6, §7 'Checks leak', both languages). (b) If only accuracy is recovered (≥ THINK − 3) at > 60% of THINK's tokens:
the limit is restated with the measured saving. (c) Otherwise the limit stays: for Qwen3-8B on geometry, always think.
Also reported (labels used only for these notes): brute-force correctness per task, its tokens / finish reasons / crashes / timeouts, and
≥ 10 flagged leaked programs and ≥ 5 false alarms read in full.
