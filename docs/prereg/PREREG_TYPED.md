# PREREG_TYPED — typed translation: the model writes the data, a verified solver does the modelling

Written 2026-11-20 00:1x UTC, before any typed-translation output exists.

**Why.** On the computation track the cross-family cascade's remaining errors on audited MAMO ComplexLP are mostly programs every model
writes the same wrong way (30 of 54 errors, 3 seeds). On max flow (stored rows, `results/tmp_flow_closure.py`) the models read the data
right and model it wrong: a fixed max-flow algorithm on the capacity table the model wrote into its own program is right 27 of 36
(Qwen3-8B; its own programs 12 of 36), 18 vs 7 of 26 (gpt-oss-20b), 35 vs 17 of 42 (Qwen3-14B). The shared bug: the objective counts flow
out of the source while return edges into it are free. This is the puzzle method's split (the model translates, the solver searches)
applied to modelling.

**Related work (checked 11-20).** OptiMUS (2402.10172) separates the data from the description but still has the LLM write the constraints
and code; LLMOPT (2410.13213) fine-tunes a five-element formulation; ORLM (2405.17743) trains models to write the model and notes frequent
constraint errors. None hands a recognised template to a fixed solver and measures that modelling, not reading, causes the shared errors.

**Run.** MAMO ComplexLP problems of the two graph templates (31 max flow, 40 TSP; selected by wording, all 211 ComplexLP, not only the
audited subset), seeds 1–3, Qwen3-8B and gpt-oss-20b (low effort), no thinking: the model returns {type, edges, source, sink} as JSON;
`poc/run_typed.py` solves max flow (Edmonds–Karp) and TSP (enumeration). Compared, paired by problem-seed, with the same model's stored quick
program (`formx`) on the same problems.

**Predictions.**
- T-1: max flow: typed − own program accuracy ≥ +20 points for both models (scored against the exact max flow computed from the problem
  text, and also reported against the dataset label).
- T-2: TSP: typed ≥ own program − 5 points (no real loss), scored against the dataset label (two TSP labels are known wrong; reported).
**Decision.** T-1 holds → typed translation joins the word-problem method for recognised templates (the type is the model's own call; an
"other" falls back to the cascade). T-1 fails → modelling is not the bottleneck after all; report.
