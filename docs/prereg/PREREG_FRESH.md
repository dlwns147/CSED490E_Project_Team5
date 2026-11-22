# PREREG_FRESH — the final word-problem method vs LLMOPT-14B on problems never looked at (registered 2026-11-22 07:2x UTC, before any row)

**Why.** The one held-out cell where Qwen3-8B's method lost to the official LLMOPT-14B (OptiBench) moved −5.0 (W3) → −2.1 (J, repair
turn) → −3.9 (audited labels) → +2.4 (ESCT, retry), each change chosen after reading that loss on the same problems (LOOP §1b S8). Every
held-out set has now informed a decision, so no number on them is a held-out result for the final method. This test uses problems no
decision has seen. It is a confirmation (loop mark V), not a method change.

**Problems.** 300 OptMATH-Train problems (Aurora-Gem/OptMATH-Train, solver-computed optimal objective as the label):
`python poc/prep_wptrain.py 8000 --fresh 300` → `nlp_data/optmath_train/omtf_items.jsonl`, the 300 after the 8,000 training items of the
same filtered, decontaminated (13-gram vs all seven test sets) Random(0) order; ids `omtf-<line>`. None is in any training file, pool or
stored run here. The ReSocratic-29k pool (OptiBench's own generator) would match OptiBench better but its repository is private now.
Caveat stated in advance: OptMATH-Train labels come from generated gurobipy code and are unaudited; scoring uses the project scorer
(tolerance max(1e-2, 1e-3·|gold|)) for every arm.

**Arms** (3 seeds, Qwen3-8B and gpt-oss-20b; gpt-oss-20b cheap arms low effort, thinking medium; Qwen3-8B thinking on, 16k):
- FULL = PREREG_ESCT's final method, as scored by poc/analyze_frontier.py `--nopool`: typed menu (run_typed.py --v3 --set omtf; valid
  and grounded readings routed to the fixed solver) → own program (freef, the general solver card: the set has nonlinear problems) → one
  repair on a visible failure (run_repair.py freef) → cross-family peer agreement (the other model's freef) → thinking (thinkfree) → on a
  visibly failed think one retry (Qwen3-8B: gpt-oss-20b's think; gpt-oss-20b: its next seed's think).
- If PREREG_ADJ holds for a model before these rows are scored, FULL+ADJ is scored too (its escalated thinks run with thinkadj), as a
  second, descriptive line.
- LLMOPT = ant-opt/LLMOPT-Qwen2.5-14B with its official prompts and self-correction (run_llmopt.py, tag llm14f, same sandbox as W3).

**Test.** Per model, FULL − LLMOPT, utility at 0.5 per ktok (output tokens; LLMOPT's own tokens), one-sided bootstrap clustered by problem,
Holm over the two models (poc/analyze_fresh.py). HOLDS if Holm p < 0.05. Also reported: accuracy, tokens, size-weighted cost view.
**Reading fixed in advance:** if Qwen3-8B's test does not hold, the OptiBench "+2.4" is reported as a forking-path result and the report
says the final method ties or trails LLMOPT on fresh problems for Qwen3-8B.
