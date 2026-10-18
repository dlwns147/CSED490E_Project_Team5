# Pre-registration SIZE: does the cheapest fix depend on model size, and can a small model with the fact replace a large one?

Written 2026-10-17 10:10 UTC, before any run. Results go below; this section is not edited afterwards.

**Why.** The project's question is how to solve computational math problems accurately at the lowest cost. So far cost = output
tokens of one model, and the fix depends on the model: for Qwen3-32B thinking helps on NL4OPT / IndustryOR only with the API fact (it
invents a method without it), for Qwen3-8B thinking helps without it too; the cheap check costs the 8B model 3.9 points (X6). Smaller
models are cheaper per token, so "a small model + the fact + a check" may beat "a large model thinking" at equal compute.
Prior art: model cascades (FrugalGPT, Chen et al. 2023; RouteLLM, Ong et al. 2024) and MoT cascades (Yue et al., ICLR 2024: escalate from a
weak to a strong LLM when its text and program answers disagree). New here: the escalation trigger is an execution check after the
fact is given, and the comparison is by failure mechanism across a size ladder of one family.
**Design.** Qwen3-1.7B and Qwen3-4B (new; tags q17, q4b), compared with the existing Qwen3-8B and Qwen3-32B runs, same prompts, seeds 1–3:
- U1 suites (9 generated geometry tasks, 8 optimization problems): base (+ log-probs), FACT, DECORRELATE and THINK arms (16k cap), as in U1 / U1r;
- X6 (NL4OPT 245 + IndustryOR 100): mip, mipf, think, thinkf (16k cap).
Cost is reported as output tokens and as compute ≈ (parameters, in billions) × output tokens, so that models of different size compare.
The 1.7B model often fails to copy helper code (2026-10-12: 185 of 214 crashes); crashes are reported by type, and packaging failures
(no code, copy errors) separately from wrong programs.
**Predictions.**
- SIZE-P1: the gain of the fact without thinking grows as the model shrinks: (mipf − mip) and (ALWAYS-FACT − base) are larger for
  1.7B and 4B than for 32B.
- SIZE-P2: thinking without the fact helps every model ≤ 8B (think > mip on X6; THINK > base in U1).
- SIZE-P3: fact-first-then-think stays within 5 points of always-thinking (with the fact) for 4B and 8B, at ≤ 50% of its tokens.
- SIZE-P4 (cross-size cascade, X6): Qwen3-4B mipf, escalating to Qwen3-32B thinkf when the program fails the check, reaches ≥ Qwen3-32B
  always-thinkf − 3 points at ≤ 25% of its compute (params × tokens).
Runs: poc/queues/queue_s2_size.sh (starts on the first of GPUs 0–3 that is free; 1.7B, then 4B). Analysis: python poc/analyze_u1.py q17
q4b; python poc/analyze_x6.py q17 q4b; the compute and cascade numbers in poc/analyze_size.py (written before the results are read).

## Addendum (2026-10-17 10:13 UTC, before any SIZE run): the target is models that run on one RTX 3090 (24 GB) — user clarification
Fit on 24 GB (weights + KV cache for one 16k-token request; KV per token = layers × KV heads × head dim × 2 × 2 bytes):
| model | weights | KV for 16k tokens | fits a 3090? |
|---|---|---|---|
| Qwen3-1.7B (bf16) | 3.4 GB | 1.8 GB | yes |
| Qwen3-4B (bf16) | 7.6 GB | 2.4 GB | yes |
| Qwen3-8B (bf16) | 16 GB | 2.4 GB | yes (≈ 20 GB with runtime overhead) |
| Qwen3-14B-AWQ (4-bit) | ≈ 10 GB | 2.6 GB | yes (bf16 14B, 28 GB, does not) |
| gpt-oss-20b (MXFP4) | 13 GB | < 1 GB (half the layers use a 128-token window) | yes |
| Qwen3-32B-AWQ (4-bit) | 19 GB | 4.2 GB | no for 16k thinking; ≈ 8k context only |
| Qwen3.6-35B-A3B (FP8), gpt-oss-120b | 35 / 61 GB | | no |
Models added to SIZE: Qwen3-14B-AWQ (q14a; downloaded to /SSD/huggingface/Qwen/Qwen3-14B-AWQ) and gpt-oss-20b (oss20: low effort for the
no-thinking arms, medium for the thinking arms, as in X3), besides 1.7B and 4B; all U1 and X6 arms as above. Qwen3-32B-AWQ stays the
"large" reference (it fits a 3090 only without long thinking). Runs use the server's GPUs at full memory (accuracy does not depend on
memory); the fit is the table above. Each model lane waits for its own free GPU (poc/queues/queue_s2_size.sh).
Added predictions (before any of these rows exist):
- SIZE-P5: on X6, Qwen3-14B-AWQ thinkf ≥ Qwen3-32B thinkf − 2 points (72.0%), and gpt-oss-20b thinkf ≥ 72.0%.
- SIZE-P6: on the U1 optimization suite, no model ≤ 8B reaches Qwen3-32B's fact-first-then-think (79–85% over seeds); Qwen3-14B-AWQ
  is within 10 points of it.

## Results, part 1: gpt-oss-20b (2026-10-17 10:37 UTC; results/x3/analysis_x6_oss20.log, results/u1_oss20.log)
X6 (NL4OPT + IndustryOR, 345 × 3; mip / mipf / think reused from X3 at the same efforts; thinkf new, medium effort):
mip 67.4% @ 0.53k, mipf 70.1% @ 0.52k, think 71.0% @ 2.4k, **thinkf 74.9% @ 2.3k**; fact-first-then-think (mipf → thinkf) 73.0% @ 0.72k
(escalates 6%); thinkf → mipf 76.0% @ 2.3k. No invented `SetMaximize` at all (0 of 4,140 programs).
U1 suites (cure seeds 1 / 2 / 3): geometry base 100% (no helper steering for gpt-oss, as in earlier runs: the suite is at ceiling);
optimization base 81%, ALWAYS-FACT 93 / 89 / 90% @ 0.59k, FACT-FIRST-THEN-THINK 95 / 97 / 94% @ 0.8–1.1k, MECHANISM 96 / 92 / 90% @ 2.2k,
DIFFICULTY 82 / 85 / 86%, RETRIEVED-FIRST-THEN-THINK 90 / 97 / 95% @ 1.0k.
- **SIZE-P5 holds for gpt-oss-20b:** thinkf 74.9% ≥ Qwen3-32B thinkf 72.0%, at 42% of its output tokens and 5% of its compute (3.6B active
  parameters × 2.3k tokens vs 32.8B × 5.5k).
- Compared with Qwen3-32B in U1 optimization (fact-first-then-think 79–85% @ 2.6–3.0k), gpt-oss-20b is 12–15 points better at a third of
  the tokens.
**Reading:** the 3090-class mixture-of-experts model with the fact first and thinking only on a failed check is the most accurate
*and* the cheapest setting measured so far on both external word problems and the optimization suite.

## Results, part 2: the no-thinking arms of every size (2026-10-17 11:32 UTC; thinking arms of 1.7B / 4B / 14B-AWQ still running)
X6 (345 × 3), accuracy @ mean output tokens (runtime errors of 1,035):
| model | mip | mipf (+ 6-line API fact) | fact gain |
|---|---|---|---|
| Qwen3-1.7B | 0.1% @ 0.71k (1,024) | 44.5% @ 0.47k (237) | **+44.4** |
| Qwen3-4B | 14.7% @ 0.53k (697) | 46.0% @ 0.46k (132) | **+31.3** |
| Qwen3-8B | 34.3% @ 0.53k (409) | 51.7% @ 0.45k (267) | +17.4 |
| Qwen3-14B-AWQ | 58.1% @ 0.38k (220) | 66.0% @ 0.40k (107) | +7.9 |
| Qwen3-32B-AWQ | 65.4% @ 0.38k (122) | 66.2% @ 0.35k (127) | +0.8 |
Raw: the 1.7B model's crashes are invented OR-Tools attributes on objects, classes and the module (294 / 191 / 119) and wrong argument
types (113); with the snippet most disappear. U1 suites (base pooled over 3 samples; FACT / DECORRELATE over cure seeds 1–3):
geometry base / fact 17 / 47% (1.7B), 69 / 74% (4B), 69 / 79% (8B), 65 / 76% (14B-AWQ), 58 / 82% (32B); optimization base / fact 5 / 1%
(1.7B), 4 / 38% (4B), 25 / 41% (8B), 39 / 75% (14B-AWQ), 56 / 75% (32B).
- **SIZE-P1 holds on X6 and strictly by size** (fact gain +44 → +31 → +17 → +8 → +1 from 1.7B to 32B). On the U1 suites it does not
  hold as stated (gains +30 / +5 / +10 / +11 / +24 in geometry; −4 / +34 / +16 / +36 / +19 in optimization): the generated suites need
  more than the API fact (an algorithm), and the 1.7B model cannot use the optimization snippet at all (1% with it).

## SIZE-CC pre-registration (2026-10-17 13:44 UTC, before running): can a 3090-class model with check-gated escalation do real contest geometry?
Benchmark: the 311 validated Codeforces geometry problems (CodeContests, official tests). Existing gpt-oss-20b runs: low 40.2 / 37.0 /
36.0% @ 1.5k tokens; medium 46.9 / 47.6 / 46.6% @ 8.7k, but 85–93 of 311 medium runs stopped at the 16k cap (a setup limit). Reference
gpt-oss-120b (does not fit a 3090): medium 54.7–58.2% @ 6.8k, high (64k) 65.6–66.9% @ 30k. New: gpt-oss-20b medium and high with a 62k
cap (tags oss20_medium64k, oss20_high64k; server max-model-len 65536), seeds 1–3, GPU2 (poc/queues/queue_s2_sizecc.sh). Analysis:
CC_SET=full N8_MODEL=oss20 N8_MEDIUM=medium64k python poc/analyze_n8.py (escalate when the statement's example tests fail).
- SIZE-CC-P1 (setup): medium64k hits the cap on ≤ 3% of runs and gains ≥ 5 points over medium at 16k.
- SIZE-CC-P2: gpt-oss-20b high64k ≥ gpt-oss-120b medium (≈ 57%).
- SIZE-CC-P3 (policy): gpt-oss-20b low → medium64k → high64k, escalating only when the examples fail, is within 2 points of always-high64k
  at ≤ 60% of its tokens.

## Results, part 3: all sizes (2026-10-17 14:36 UTC; results/size_analysis.log, results/u1_{q17,q4b,q14a,oss20}.log, results/x3/analysis_x6_*.log)
X6 (NL4OPT + IndustryOR, 345 × 3), accuracy @ output tokens (compute = active B params × tokens, per item):
| model (fits a 3090?) | mipf | thinkf | fact-first-then-think | thinkf → mipf |
|---|---|---|---|---|
| Qwen3-1.7B (yes) | 44.5% @ 0.47k | 38.2% @ 7.1k | 50.1% @ 2.6k | 56.2% @ 7.3k |
| Qwen3-4B (yes) | 46.0% @ 0.46k | 69.3% @ 6.7k (26.8k) | 51.5% @ 1.6k | 71.9% @ 6.8k |
| Qwen3-8B (yes) | 51.7% @ 0.45k | 72.2% @ 7.2k (58.8k) | 68.3% @ 2.5k | 72.9% @ 7.2k |
| Qwen3-14B-AWQ (yes) | 66.0% @ 0.40k | **76.0% @ 5.6k (82.4k)** | 70.7% @ 1.3k | **77.6% @ 5.6k** |
| gpt-oss-20b (yes) | 70.1% @ 0.52k | 74.9% @ 2.3k (**8.2k**) | 73.0% @ 0.72k | 76.0% @ 2.3k |
| Qwen3-32B-AWQ (no) | 66.2% @ 0.35k | 72.0% @ 5.5k (179.4k) | 72.4% @ 1.3k | 76.8% @ 5.5k |
Cross-size cascade (small model's mipf; Qwen3-32B thinkf only when the program fails the check), vs Qwen3-32B always-thinkf 72.0% @
179.4k compute: from 1.7B 58.1% (30% of the compute), 4B 52.6% (19%), 8B 69.5% (30%), 14B-AWQ 70.4% (19%), gpt-oss-20b **73.2% (8%)**.
U1 suites, fact-first-then-think (geometry / optimization, cure seeds 1–3): 1.7B ≈ 76 / ≤ 6% (pooled 42–45%); 4B 95–100 / 45–47%;
8B 96–99 / 46%; **14B-AWQ 99–100 / 87–92%**; gpt-oss-20b 100 / 94–97%; 32B 97–100 / 79–85%.
- **SIZE-P2 holds** except where nothing works (1.7B optimization suite, ≤ 5% with any arm).
- **SIZE-P3 half holds:** fact-first-then-think is within 5 points of always-thinkf for 8B (−3.9) but not for 4B (−17.8 on X6: its fact
  programs run and print wrong values that thinking would fix); in the U1 suites it beats always-think for every size.
- **SIZE-P4 refuted** for the pre-registered pair (4B → 32B: 52.6% vs 72.0%); it holds for 14B-AWQ → 32B (−1.6 at 19% of the compute)
  and gpt-oss-20b → 32B (+1.2 at 8%).
- **SIZE-P5 holds** (14B-AWQ thinkf 76.0%, gpt-oss-20b 74.9% ≥ 72.0% for Qwen3-32B). **SIZE-P6 holds** (4B / 8B ≤ 47% vs 32B 79–85% on the
  optimization suite) and is exceeded by 14B-AWQ (87–92%, above the 32B model).
**Reading (for one RTX 3090):** with the fact first and thinking only on a failed check, Qwen3-14B-AWQ and gpt-oss-20b match or beat
Qwen3-32B on both the external word problems and the optimization suite; gpt-oss-20b does so at 5% of its compute. Below 14B the
optimization suite is out of reach whatever the fix (≤ 47%), while geometry is solved from 4B up. Cost-accuracy pick per budget:
gpt-oss-20b fact-first (73.0% @ 0.7k tokens, 3.6B active) ≥ Qwen3-14B-AWQ thinkf → mipf (77.6% @ 5.6k) when accuracy matters most.

## SIZE-CHK pre-registration (2026-10-17 15:32 UTC, before computing; offline on the X6 rows): a better cheap check for small models
Part 3 showed fact-first-then-think loses where the fact program runs and prints a wrong value (Qwen3-4B −17.8, Qwen3-8B −3.9 vs
always-thinkf). Two label-free checks that cost one more cheap program, computed from the stored X6 rows (same item, other seed /
other arm): **RESAMPLE** — accept mipf only if it runs and equals a second mipf sample (the next seed's row); **CROSS-VIEW** — accept
only if it equals the mip program (no fact). Otherwise thinkf (same seed). Tokens include both cheap programs. poc/analyze_size_chk.py.
- SIZE-CHK-P1: for Qwen3-4B and Qwen3-8B, RESAMPLE closes ≥ half of the gap to always-thinkf (4B: to ≥ 60.4%; 8B: to ≥ 70.3%) at ≤ 50% of
  always-thinkf's tokens.
- SIZE-CHK-P2: among items the check accepts, the wrong share is lower for CROSS-VIEW than for RESAMPLE, for every model (different views
  decorrelate errors, VIEWS), but CROSS-VIEW escalates more for models ≤ 8B (their mip programs mostly crash).

## SIZE-CHK results (2026-10-17 15:33 UTC; results/x3/analysis_size_chk.log)
Accuracy @ output tokens per item (share of items the check accepts; wrong share among accepted):
| model | always thinkf | FF (runs + prints) | RESAMPLE (two fact programs agree) | CROSS-VIEW (fact program = no-fact program) |
|---|---|---|---|---|
| Qwen3-1.7B | 38.2% @ 7.1k | 50.1% @ 2.7k (77%; 41.9%) | 50.7% @ 5.4k (47%; 25.2%) | 38.2% @ 8.3k (0%: its no-fact programs never run) |
| Qwen3-4B | 69.3% @ 6.7k | 51.5% @ 1.6k (87%; 47.1%) | 57.8% @ 4.1k (63%; 38.1%) | 66.3% @ 6.7k (17%; 31.1%) |
| Qwen3-8B | 72.2% @ 7.2k | 68.3% @ 2.5k (74%; 30.2%) | **72.4% @ 5.1k** (48%; 17.7%) | 71.4% @ 6.3k (29%; 17.9%) |
| Qwen3-14B-AWQ | 76.0% @ 5.6k | 70.7% @ 1.3k (90%; 26.4%) | **75.6% @ 2.9k** (74%; 16.6%) | 75.6% @ 3.5k (62%; 14.3%) |
| gpt-oss-20b | 74.9% @ 2.3k | 73.0% @ 0.7k (94%; 25.8%) | 74.9% @ 1.9k (78%; 17.2%) | 74.9% @ 1.9k (76%; 17.4%) |
| Qwen3-32B-AWQ | 72.0% @ 5.5k | 72.4% @ 1.3k (88%; 24.6%) | **74.8% @ 2.6k** (73%; 17.0%) | 74.2% @ 2.9k (70%; 15.0%) |
- **SIZE-CHK-P1 half holds:** for Qwen3-8B RESAMPLE closes the whole gap (72.4% vs 72.2%) but at 71% of always-thinkf's tokens (not ≤ 50%);
  for Qwen3-4B it closes 35% of the gap (57.8%): its fact programs are often wrong *consistently*, so two samples agree on a wrong value.
- **SIZE-CHK-P2 mostly holds:** CROSS-VIEW accepts fewer wrong programs than RESAMPLE for 4B, 14B-AWQ and 32B (31 vs 38%, 14 vs 17%,
  15 vs 17%), ties for 8B and gpt-oss-20b, and escalates far more for ≤ 8B (it accepts 0–29% of items).
**Reading:** a second cheap program is a better check than "it runs": with it, fact-first-then-think reaches always-thinking accuracy
for 8B / 14B-AWQ / gpt-oss-20b and *exceeds* it for Qwen3-32B (74.8% vs 72.0% at 48% of the tokens, because a thinking run sometimes
breaks what the fact program had right). For the 4B model no cheap check rescues the fact program; it needs thinking on most items.

## SIZE-CC results (2026-10-18 05:02 UTC; results/h2/sizecc_analysis.log; 311 contest geometry problems × 3 seeds)
gpt-oss-20b (fits a 3090): low 37.7% @ 1.5k; medium (16k) 47.0% @ 8.7k (268 / 933 runs at the cap); **medium (62k) 52.4% @ 12.7k** (14 at
the cap); high (62k) 37.9% @ 47.5k (470 / 933 at the cap). Escalating when the statement's example tests fail: low → medium 54.6% @ 11.0k;
low → medium → high 56.3% @ 25.8k. Reference gpt-oss-120b (no 3090): medium 56.8% @ 6.8k, high (64k) 66.2% @ 30.1k.
- **SIZE-CC-P1 holds** (1.5% at the cap; +5.4 points over the 16k cap). **P2 refuted:** at high effort the 20B model thinks past 62k on half
  the problems (37.9%), so its high effort cannot be used on one GPU at this budget. **P3 holds** but only because always-high is cut:
  low → medium → high is +18.4 points over always-high at 54% of its tokens.
**Reading:** on real contest geometry the 3090-class model with check-gated escalation (low → medium, 54.6% @ 11k) comes within 2.2 points
of the 120B model at medium; the 120B's high effort (66%) stays out of reach.
